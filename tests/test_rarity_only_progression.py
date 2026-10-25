from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import FreightAssignment, build_freight_facility
from production_zero.core.state import FactoryHall, GameState, HallSlot
from production_zero.data.definitions import load_card_definitions, normalize_legacy_card_definition_id
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def test_progression_definitions_are_canonical_and_rarity_only() -> None:
    definitions = _definitions()
    assert len(definitions) == 15
    assert set(definitions) == {
        "machine.extractor", "machine.drilling", "machine.agriculture",
        "machine.processor", "machine.fabricator", "machine.assembler",
        "energy.solar_array", "energy.wind_turbine", "energy.coal_power_plant",
        "energy.gas_power_plant", "energy.nuclear_power_plant",
        "freight.truck", "freight.train", "freight.ship", "freight.aircraft",
    }
    assert definitions["machine.extractor"].base_output_per_tick == 12
    assert definitions["freight.truck"].base_capacity == 40
    assert all(not hasattr(definition, "mk_level") for definition in definitions.values())
    assert all(not hasattr(definition, "class_level") for definition in definitions.values())


def test_legacy_family_ids_normalize_to_canonical_ids() -> None:
    assert normalize_legacy_card_definition_id("machine.extractor.mk3") == "machine.extractor"
    assert normalize_legacy_card_definition_id("machine.mining_drill.mk2") == "machine.extractor"
    assert normalize_legacy_card_definition_id("machine.blast_furnace.mk1") == "machine.processor"
    assert normalize_legacy_card_definition_id("freight.train.class3") == "freight.train"



@pytest.mark.parametrize("legacy_id", ["machine.extractor.mk1", "machine.extractor.mk2", "machine.extractor.mk3"])
def test_all_legacy_machine_tiers_use_the_permanent_base_values(legacy_id: str) -> None:
    state = GameState(rng_seed=7000)
    card = create_card_instance("legacy", "machine.extractor", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74)
    state.cards[card.card_id] = card
    payload = serialize_game_state(state)
    payload["cards"][card.card_id]["definition_id"] = legacy_id
    payload["cards"][card.card_id]["mk_level"] = int(legacy_id[-1])

    loaded = deserialize_game_state(payload)
    definition = _definitions()[loaded.cards[card.card_id].definition_id]
    assert loaded.cards[card.card_id].definition_id == "machine.extractor"
    assert loaded.cards[card.card_id].rarity is Rarity.RARE
    assert definition.base_output_per_tick == 12
    assert definition.base_output_per_tick * loaded.cards[card.card_id].output_multiplier == pytest.approx(12.888 * (1 + .25 * (int(legacy_id[-1]) - 1)))

def test_legacy_save_preserves_card_identity_rarity_installation_and_assignment() -> None:
    state = GameState(rng_seed=7001)
    machine = create_card_instance("legacy-machine", "machine.extractor", CardKind.MACHINE, Rarity.EPIC, bonus_tenths=137)
    freight = create_card_instance("legacy-freight", "freight.train", CardKind.FREIGHT, Rarity.RARE, bonus_tenths=74)
    state.cards[machine.card_id] = machine
    state.cards["legacy-machine-copy"] = create_card_instance("legacy-machine-copy", "machine.extractor", CardKind.MACHINE, Rarity.EPIC, bonus_tenths=137)
    state.cards[freight.card_id] = freight
    state.halls["hall"] = FactoryHall("hall", "Hall", 1, slots=[HallSlot(0, machine.card_id)])
    rail = build_freight_facility(state.freight, "rail_station")
    rail.slots[0].card_id = freight.card_id
    state.freight.assignments[freight.card_id] = FreightAssignment("steel", "market")
    payload = serialize_game_state(state)
    payload["cards"][machine.card_id]["definition_id"] = "machine.extractor.mk3"
    payload["cards"][machine.card_id]["mk_level"] = 3
    payload["cards"][freight.card_id]["definition_id"] = "freight.train.class2"
    payload["cards"][freight.card_id]["class_level"] = 2

    loaded = deserialize_game_state(payload)
    assert loaded.cards[machine.card_id].definition_id == "machine.extractor"
    assert loaded.cards[machine.card_id].rarity is Rarity.EPIC
    assert loaded.cards[machine.card_id].output_bonus_tenths == 137
    assert loaded.halls["hall"].slots[0].card_id is None
    assert any(slot.card_id == machine.card_id for site in loaded.resource_sites.values() for slot in site.slots)
    assert loaded.cards[freight.card_id].definition_id == "freight.train"
    assert loaded.cards[freight.card_id].rarity is Rarity.RARE
    assert loaded.freight.facilities[rail.facility_id].slots[0].card_id == freight.card_id
    assert loaded.freight.assignments[freight.card_id] == FreightAssignment("steel", "market")
    matching_stack = next(stack for stack in loaded.inventory_card_stacks() if stack.first_card.card_id in {machine.card_id, "legacy-machine-copy"})
    assert matching_stack.quantity == 1  # installed card is excluded; the owned copy remains available


def test_new_save_writes_no_progression_tier_fields() -> None:
    state = GameState(rng_seed=7002)
    state.cards["card"] = create_card_instance("card", "machine.extractor", CardKind.MACHINE, Rarity.UNCOMMON)
    payload = serialize_game_state(state)
    card_payload = payload["cards"]["card"]
    assert card_payload["definition_id"] == "machine.extractor"
    assert card_payload["mk_level"] == 1
    assert "class_level" not in card_payload
