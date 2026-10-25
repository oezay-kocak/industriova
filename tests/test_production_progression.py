from __future__ import annotations

from importlib.resources import files

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, BuildHall, CommandBus, InstallCardInHall, SelectMachineProduction
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.progression import (
    initial_production_ids,
    initialize_production_progress,
    production_options_for_machine,
    production_progress_state,
    record_lifetime_production,
    unlock_requirement_lines,
)
from production_zero.core.resources import create_resource_inventory
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def _state() -> GameState:
    resources = create_resource_inventory(load_resource_definitions(files("production_zero.data") / "resource_definitions.json"))
    state = GameState(rng_seed=101, resources=resources)
    initialize_production_progress(state, _definitions())
    return state


def test_new_game_starts_with_several_basic_branches_and_locks_later_catalog() -> None:
    definitions = _definitions()
    state = _state()
    extractor = definitions["machine.extractor"]
    drilling = definitions["machine.drilling"]
    agriculture = definitions["machine.agriculture"]
    processor = definitions["machine.processor"]
    assert isinstance(extractor, MachineDefinition)
    assert isinstance(processor, MachineDefinition)

    extractor_names = {
        option.name
        for definition in (extractor, drilling, agriculture)
        for option in production_options_for_machine(state, definition)
    }
    processor_names = {option.name for option in production_options_for_machine(state, processor)}

    assert {"Iron Ore", "Copper Ore", "Coal", "Bauxite", "Timber", "Wheat", "Crude Oil"}.issubset(extractor_names)
    assert "Natural Gas" in extractor_names
    assert "Tin Ore" in extractor_names
    assert len(extractor_names) == 49
    assert processor_names == set()
    assert state.production_progress.unlocked_production_ids == initial_production_ids()


def test_producing_prerequisite_crosses_threshold_once_and_survives_consumption() -> None:
    definitions = _definitions()
    state = _state()

    record_lifetime_production(state, {"iron_ore": 99}, definitions)
    assert "recipe.processor.iron" not in state.production_progress.unlocked_production_ids
    assert state.production_progress.pending_unlock_ids == []

    earned = record_lifetime_production(state, {"iron_ore": 1}, definitions)
    assert earned == ("recipe.processor.iron",)
    assert state.production_progress.lifetime_produced["iron_ore"] == 100
    assert "recipe.processor.iron" in state.production_progress.unlocked_production_ids
    assert state.production_progress.pending_unlock_ids == ["recipe.processor.iron"]

    state.ensure_resource("iron_ore").amount = 0
    earned_again = record_lifetime_production(state, {"iron_ore": 500}, definitions)
    assert earned_again == ()
    assert state.production_progress.pending_unlock_ids == ["recipe.processor.iron"]
    assert "recipe.processor.iron" in state.production_progress.unlocked_production_ids


def test_multi_input_products_require_each_relevant_branch() -> None:
    definitions = _definitions()
    state = _state()
    steel = next(
        option
        for option in definitions["machine.processor"].available_production_options
        if option.production_id == "recipe.processor.steel"
    )

    assert production_progress_state(state, steel) == "next"
    record_lifetime_production(state, {"iron_ore": 120}, definitions)
    assert "recipe.processor.steel" not in state.production_progress.unlocked_production_ids
    assert any("PRODUCE 100 MORE COAL" in line for line in unlock_requirement_lines(state, steel))

    record_lifetime_production(state, {"coal": 99}, definitions)
    assert "recipe.processor.steel" not in state.production_progress.unlocked_production_ids

    earned = record_lifetime_production(state, {"coal": 1}, definitions)
    assert earned == ("recipe.processor.steel",)
    assert "recipe.processor.steel" in state.production_progress.unlocked_production_ids


def test_simulation_records_accepted_outputs_as_lifetime_production() -> None:
    definitions = _definitions()
    state = _state()
    state.ensure_resource("iron_ore").capacity = 200
    state.ensure_resource("iron_ore").amount = 0
    state.ensure_resource("coal").capacity = 200
    state.ensure_resource("coal").amount = 0
    state.cash.amount = 0
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=3)))
    bus.dispatch(AddCard(create_card_instance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("extractor-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "extractor-1"))
    bus.dispatch(SelectMachineProduction("extractor-1", "resource.iron_ore", "iron_ore"))

    totals = SimulationEngine(definitions).advance_time(state, 30)

    assert totals.outputs["iron_ore"] == 60
    assert state.production_progress.lifetime_produced["iron_ore"] == 60
    SimulationEngine(definitions).advance_time(state, 30)
    assert "recipe.processor.iron" in state.production_progress.unlocked_production_ids


def test_production_progress_persists_and_legacy_payload_migrates_without_pending_unlocks() -> None:
    definitions = _definitions()
    state = _state()
    record_lifetime_production(state, {"iron_ore": 120, "copper_ore": 120}, definitions)

    loaded = deserialize_game_state(serialize_game_state(state))

    assert loaded.production_progress.lifetime_produced["iron_ore"] == 120
    assert {"recipe.processor.iron", "recipe.processor.copper"}.issubset(
        loaded.production_progress.unlocked_production_ids
    )

    legacy_payload = serialize_game_state(state)
    legacy_payload.pop("production_progress")
    legacy_payload["resources"]["iron_ore"]["amount"] = 145
    legacy_payload["machine_production"]["legacy-furnace"] = {
        "card_id": "legacy-furnace",
        "target_resource_id": "steel",
        "selected_production_id": "recipe.processor.steel",
        "progress_seconds": 0.0,
        "status": "idle",
    }
    migrated = deserialize_game_state(legacy_payload)

    assert migrated.production_progress.lifetime_produced["iron_ore"] == 145
    assert "recipe.processor.steel" in migrated.production_progress.unlocked_production_ids
    assert migrated.production_progress.pending_unlock_ids == []
