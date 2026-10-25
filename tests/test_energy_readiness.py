from copy import deepcopy
from dataclasses import replace
from importlib.resources import files

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state


@pytest.fixture(scope="module")
def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def install(state, definitions, definition_id, card_id, board="factory", production_id=None):
    unit = state.production_units(board).setdefault(
        board, FactoryHall(board, board, 10, board_kind=board, max_lines=1,
                           start_unlocked_lines=1, start_slots_per_line=10),
    )
    card = create_card_instance(card_id, definition_id, definitions[definition_id].card_kind, Rarity.COMMON)
    state.cards[card_id] = card
    next(slot for slot in unit.slots if slot.card_id is None).card_id = card_id
    if production_id:
        option = definitions[definition_id].production_option(production_id)
        state.ensure_machine_production(card_id, option.output_resource, option.production_id)
    return card


def processor_state(definitions):
    state = GameState(351)
    state.warehouse_capacity = 10_000
    install(state, definitions, "machine.processor", "processor", production_id="recipe.processor.steel")
    install(state, definitions, "energy.solar_array", "solar", "energy")
    state.ensure_resource("iron_ore").amount = 100
    state.ensure_resource("coal").amount = 100
    return state


@pytest.mark.parametrize("definition_id", (
    "machine.processor", "machine.fabricator", "machine.assembler",
    "machine.extractor", "machine.drilling", "machine.agriculture",
))
@pytest.mark.parametrize("has_machine_state", (False, True))
def test_unconfigured_machines_use_no_power(definitions, definition_id, has_machine_state):
    state = GameState(351)
    state.warehouse_capacity = 10_000
    board = "resources" if definition_id in {"machine.extractor", "machine.drilling", "machine.agriculture"} else "factory"
    install(state, definitions, definition_id, "idle", board)
    install(state, definitions, "energy.solar_array", "solar", "energy")
    if has_machine_state:
        state.ensure_machine_production("idle", "")
    engine = SimulationEngine(definitions)
    assert engine.preview_tick(state).used_power == 0
    totals = engine.advance_time(state, 6)
    assert totals.used_power == state.energy.consumed == 0
    assert totals.outputs == {}
    assert state.machine_production["idle"].status == "unconfigured"


@pytest.mark.parametrize("condition", (
    "ready", "missing_ore", "missing_coal", "no_power", "insufficient_power",
    "card_paused", "building_paused", "line_paused", "overfull_storage",
))
def test_preview_and_runtime_agree_on_processor_readiness(definitions, condition):
    state = processor_state(definitions)
    tuned = dict(definitions)
    if condition.startswith("missing_"):
        state.resources["iron_ore" if condition == "missing_ore" else "coal"].amount = 0
    elif condition == "no_power":
        state.energy_plants.clear()
    elif condition == "insufficient_power":
        tuned["energy.solar_array"] = replace(tuned["energy.solar_array"], base_power_output=11)
    elif condition == "card_paused":
        state.cards["processor"] = replace(state.cards["processor"], paused=True)
    elif condition == "building_paused":
        state.halls["factory"].paused = True
    elif condition == "line_paused":
        state.halls["factory"].production_lines[0].paused = True
    elif condition == "overfull_storage":
        state.warehouse_capacity = state.used_storage - 12
    engine = SimulationEngine(tuned)
    before = serialize_game_state(state)
    preview = engine.preview_tick(state)
    assert serialize_game_state(state) == before
    totals = engine.advance_time(state, 1)
    assert preview.gross_power == totals.gross_power
    assert preview.used_power == totals.used_power == (12 if condition == "ready" else 0)


def test_idle_processor_cannot_starve_a_configured_machine(definitions):
    state = GameState(351)
    state.warehouse_capacity = 10_000
    install(state, definitions, "machine.processor", "idle")
    install(state, definitions, "machine.processor", "working", production_id="recipe.processor.flour")
    install(state, definitions, "energy.solar_array", "solar", "energy")
    state.ensure_resource("wheat").amount = 24
    tuned = dict(definitions)
    tuned["energy.solar_array"] = replace(tuned["energy.solar_array"], base_power_output=5)
    engine = SimulationEngine(tuned)
    assert engine.preview_tick(state).used_power == 5
    totals = engine.advance_time(state, 6)
    assert totals.outputs == {"flour": 12}
    assert state.machine_production["idle"].status == "unconfigured"
    assert state.energy.consumed == 5


def test_preview_respects_total_power_and_mk_rarity_multipliers(definitions):
    state = processor_state(definitions)
    install(state, definitions, "machine.processor", "second", production_id="recipe.processor.steel")
    state.cards["processor"] = replace(
        create_card_instance("processor", "machine.processor", definitions["machine.processor"].card_kind,
                             Rarity.LEGENDARY, bonus_tenths=200), mk_level=2,
    )
    engine = SimulationEngine(definitions)
    preview = engine.preview_tick(state)
    totals = engine.advance_time(state, 1)
    assert preview.used_power == totals.used_power == pytest.approx(16.5)
    assert state.machine_production["second"].status == "no_power"


@pytest.mark.parametrize("fuel", (0, 0.5, 1, 1.5, 2, 4.9, 5, 10))
def test_preview_accounts_for_shared_fuel_consumption(definitions, fuel):
    state = processor_state(definitions)
    state.energy_plants.clear()
    state.resources["coal"].amount = fuel
    install(state, definitions, "energy.coal_power_plant", "coal1", "energy")
    install(state, definitions, "energy.coal_power_plant", "coal2", "energy")
    engine = SimulationEngine(definitions)
    before = serialize_game_state(state)
    preview = engine.preview_tick(state)
    assert serialize_game_state(state) == before
    totals = engine.advance_time(state, 1)
    assert preview.gross_power == totals.gross_power == min(2, int(fuel)) * 60
    assert preview.used_power == totals.used_power == (12 if fuel >= 5 else 0)


@pytest.mark.parametrize("full", (False, True))
def test_preview_respects_storage_and_actual_production_order(definitions, full):
    state = GameState(351)
    state.warehouse_capacity = 12
    install(state, definitions, "machine.extractor", "first", "resources", "resource.iron_ore")
    install(state, definitions, "machine.extractor", "second", "resources", "resource.iron_ore")
    install(state, definitions, "energy.solar_array", "solar", "energy")
    for machine in state.machine_production.values():
        machine.progress_seconds = 5
    if full:
        state.ensure_resource("iron_ore").amount = 12
    engine = SimulationEngine(definitions)
    before = serialize_game_state(state)
    preview = engine.preview_tick(state)
    assert serialize_game_state(state) == before
    totals = engine.advance_time(state, 1)
    assert preview.used_power == totals.used_power == (0 if full else 6)
    assert totals.outputs == ({} if full else {"iron_ore": 12})


def test_full_storage_allows_processing_that_releases_enough_space(definitions):
    state = processor_state(definitions)
    state.warehouse_capacity = state.used_storage
    state.machine_production["processor"].progress_seconds = 5
    engine = SimulationEngine(definitions)
    assert engine.preview_tick(state).used_power == 12
    assert engine.advance_time(state, 1).outputs == {"steel": 4}
    assert state.used_storage == 189


def test_preview_never_changes_missing_or_paused_machine_state(definitions):
    state = processor_state(definitions)
    state.cards["processor"] = replace(state.cards["processor"], paused=True)
    install(state, definitions, "machine.processor", "unconfigured")
    state.machine_production["processor"].status = "running"
    engine = SimulationEngine(definitions)
    before = serialize_game_state(state)
    for _ in range(3):
        assert engine.preview_tick(state).used_power == 0
        assert serialize_game_state(state) == before


@pytest.mark.parametrize("scope", ("card", "building", "line"))
def test_paused_power_plants_provide_no_energy_and_burn_no_fuel(definitions, scope):
    state = processor_state(definitions)
    state.energy_plants.clear()
    install(state, definitions, "energy.coal_power_plant", "coal_plant", "energy")
    plant = state.energy_plants["energy"]
    if scope == "card":
        state.cards["coal_plant"] = replace(state.cards["coal_plant"], paused=True)
    elif scope == "building":
        plant.paused = True
    else:
        plant.production_lines[0].paused = True
    engine = SimulationEngine(definitions)
    preview = engine.preview_tick(state)
    actual = engine.advance_time(state, 1)
    assert preview.gross_power == actual.gross_power == 0
    assert preview.used_power == actual.used_power == 0
    assert state.resources["coal"].amount == 100


def test_missing_inputs_resume_without_reconfiguring_or_resetting_progress(definitions):
    state = processor_state(definitions)
    state.machine_production["processor"].progress_seconds = 5
    state.resources["coal"].amount = 2
    engine = SimulationEngine(definitions)
    assert engine.preview_tick(state).used_power == 0
    assert engine.advance_time(state, 1).used_power == 0
    assert state.machine_production["processor"].progress_seconds == 5
    state.resources["coal"].amount = 3
    assert engine.preview_tick(state).used_power == 12
    assert engine.advance_time(state, 1).outputs == {"steel": 4}


@pytest.mark.parametrize("elapsed", (1, 6, 30))
def test_unconfigured_machine_is_energy_neutral_across_save_load_and_catchup(definitions, elapsed):
    from production_zero.persistence.sqlite_store import deserialize_game_state
    state = processor_state(definitions)
    install(state, definitions, "machine.processor", "idle")
    state = deserialize_game_state(serialize_game_state(state))
    without_idle = deepcopy(state)
    without_idle.halls["factory"].slots[1].card_id = None
    engine = SimulationEngine(definitions, utc_now=lambda: 1_792_756_800)
    actual = engine.advance_time(state, elapsed)
    control = engine.advance_time(without_idle, elapsed)
    assert actual.used_power == control.used_power
    assert actual.outputs == control.outputs
    assert actual.inputs == control.inputs
