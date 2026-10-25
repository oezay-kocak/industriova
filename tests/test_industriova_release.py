from dataclasses import replace
from importlib.resources import files
import math

import pytest

from production_zero.core.cards import create_card_instance, CardStackKey
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import GameState, FactoryHall, HallSlot, MachineProductionState
from production_zero.core.supply import buy_common_supply_cards, common_card_price
from production_zero.core.machine_operations import sell_machines, resale_value, pause_machines, move_machines, compatible_free_slots, copy_configuration, paste_configuration
from production_zero.core.mk_upgrades import mk_factor, upgrade_cards, mk_upgrade_cost, rarity_distribution, upgraded_card
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state


@pytest.fixture
def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def prepared():
    state = GameState(rng_seed=55)
    state.cash.amount = 1e30
    state.warehouse_capacity = 1e15
    state.halls["hall"] = FactoryHall("hall", "Factory", 6)
    state.resource_sites["mine"] = FactoryHall("mine", "Mining Complex", 3, board_kind="resources", specialization="machine.extractor")
    state.energy_plants["plant"] = FactoryHall("plant", "Plant", 6, board_kind="energy")
    return state


@pytest.mark.parametrize("level", range(1, 100))
def test_linear_mk_and_energy_scaling(level):
    card = replace(create_card_instance("x", "machine.processor", CardKind.MACHINE, Rarity.COMMON), mk_level=level)
    assert card.mk_multiplier == mk_factor(level) == 1 + .25 * (level - 1)
    assert card.output_multiplier == card.power_multiplier == mk_factor(level)


def test_bulk_purchase_owns_exact_quantity_and_rejects_without_changes(definitions):
    state = prepared()
    slots = len(compatible_free_slots(state, definitions["machine.extractor"]))
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        buy_common_supply_cards(state, definitions, "machine.extractor", 10001)
    assert serialize_game_state(state) == before
    state.cash.amount = 100000
    ids = buy_common_supply_cards(state, definitions, "machine.extractor", 3)
    assert len(set(ids)) == 3
    assert not set(ids) & state.installed_card_ids()
    assert all(state.cards[cid].mk_level == 1 and state.cards[cid].rarity is Rarity.COMMON for cid in ids)
    assert state.cash.amount == 100000 - 3 * common_card_price(definitions["machine.extractor"])


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, 10001])
def test_invalid_purchase_quantities_are_atomic(definitions, quantity):
    state = prepared()
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        buy_common_supply_cards(state, definitions, "machine.extractor", quantity)
    assert serialize_game_state(state) == before


def test_mk_upgrade_atomicity_progress_and_permanent_quality(definitions):
    state = prepared()
    ids = buy_common_supply_cards(state, definitions, "machine.processor", 2)
    state.machine_production[ids[0]] = MachineProductionState(ids[0], "iron", "recipe.smelt.iron", 3.5, "running")
    state.cards[ids[1]] = replace(state.cards[ids[1]], mk_level=99)
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        upgrade_cards(state, definitions, ids)
    assert serialize_game_state(state) == before
    state.cards[ids[0]] = replace(create_card_instance(ids[0], "machine.processor", CardKind.MACHINE, Rarity.EPIC, bonus_tenths=131), acquisition_cost=100)
    cost = mk_upgrade_cost(state.cards[ids[0]], definitions["machine.processor"])
    upgrade_cards(state, definitions, (ids[0],))
    card = state.cards[ids[0]]
    assert (card.mk_level, card.output_bonus_tenths, card.rarity, card.upgrade_investment) == (2, 131, Rarity.EPIC, cost)
    assert state.machine_production[ids[0]].progress_seconds == 3.5


def test_sale_never_profits_and_removes_exact_instance(definitions):
    state = prepared()
    state.cash.amount = 1000000000
    starting_cash = state.cash.amount
    cid = buy_common_supply_cards(state, definitions, "machine.extractor", 1)[0]
    upgrade_cards(state, definitions, (cid,))
    expected = resale_value(state.cards[cid], definitions["machine.extractor"])
    assert sell_machines(state, definitions, (cid,)) == expected
    assert state.cash.amount < starting_cash
    assert cid not in state.cards and cid not in state.installed_card_ids()
    with pytest.raises(KeyError):
        sell_machines(state, definitions, (cid,))


def test_quality_distribution_and_seeded_first_hit():
    probabilities = rarity_distribution()
    assert sum(probabilities.values()) == pytest.approx(1)
    assert probabilities["legendary"] < .001
    assert .6 < 1 - probabilities["common"] < .85
    counts = {rarity.value: 0 for rarity in Rarity}
    for seed in range(3000):
        card = create_card_instance("sample", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)
        for _ in range(98):
            card = upgraded_card(card, 1., seed)
            if card.rarity is not Rarity.COMMON:
                break
        counts[card.rarity.value] += 1
    assert counts["common"] / 3000 == pytest.approx(probabilities["common"], abs=.035)
    assert counts["legendary"] < 8


@pytest.mark.parametrize("level", [1, 2, 20, 50, 99])
def test_real_recipe_input_output_and_power_scale_together(definitions, level):
    state = prepared()
    cid = buy_common_supply_cards(state, definitions, "machine.processor", 1)[0]
    from production_zero.core.commands import InstallCardInHall
    InstallCardInHall("hall", 0, cid, "factory").apply(state)
    card = replace(state.cards[cid], mk_level=level)
    state.cards[cid] = card
    definition = definitions[card.definition_id]
    recipe = next(o for o in definition.available_production_options if o.input_resources)
    state.machine_production[cid] = MachineProductionState(cid, recipe.output_resource, recipe.production_id)
    for rid in recipe.input_resources:
        state.ensure_resource(rid).amount = 1e9
    solar = create_card_instance("solar", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)
    state.cards[solar.card_id] = solar
    state.energy_plants["plant"].slots[0].card_id = solar.card_id
    definitions = dict(definitions)
    definitions[solar.definition_id] = replace(definitions[solar.definition_id], base_power_output=1e9)
    totals = SimulationEngine(definitions, utc_now=lambda: 1792324800.).advance_time(state, recipe.cycle_seconds_for(definition))
    assert totals.outputs[recipe.output_resource] == pytest.approx(recipe.output_amount_for(definition) * mk_factor(level))
    for rid, amount in recipe.input_resources.items():
        assert totals.inputs[rid] == pytest.approx(amount * mk_factor(level))
    assert totals.used_power == pytest.approx(recipe.power_draw_for(definition) * mk_factor(level))


def test_pause_and_move_preserve_production_and_reject_partial_move(definitions):
    state = prepared()
    ids = buy_common_supply_cards(state, definitions, "machine.processor", 2)
    from production_zero.core.commands import InstallCardInHall
    for i,cid in enumerate(ids):InstallCardInHall("hall", i, cid, "factory").apply(state)
    state.machine_production[ids[0]] = MachineProductionState(ids[0], "iron", "recipe.smelt.iron", 2.5, "running")
    pause_machines(state, ids, True)
    assert all(state.cards[cid].paused for cid in ids)
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        move_machines(state, ids, "factory", "hall", (3, 99))
    assert serialize_game_state(state) == before
    move_machines(state, ids, "factory", "hall", (3, 4))
    assert state.halls["hall"].slots[3].card_id == ids[0]
    assert state.machine_production[ids[0]].progress_seconds == 2.5


def test_save_restores_mk_and_specializes_sites_without_losing_cards(definitions):
    state = prepared()
    ids = buy_common_supply_cards(state, definitions, "machine.extractor", 2)
    from production_zero.core.commands import InstallCardInHall
    for i,cid in enumerate(ids):InstallCardInHall("mine", i, cid, "resources").apply(state)
    state.cards[ids[0]] = replace(state.cards[ids[0]], mk_level=50, paused=True, upgrade_investment=12000.)
    drilling = create_card_instance("legacy-drilling", "machine.drilling", CardKind.MACHINE, Rarity.RARE)
    state.cards[drilling.card_id] = drilling
    state.resource_sites["mine"].slots[2].card_id = drilling.card_id
    state.machine_production[drilling.card_id] = MachineProductionState(drilling.card_id, "crude_oil", "resource.crude_oil", 2., "running")
    payload = serialize_game_state(state)
    payload["state_schema_version"] = 4
    payload["cards"][ids[1]]["definition_id"] = "machine.extractor.mk3"
    payload["cards"][ids[1]].pop("mk_level")
    restored = deserialize_game_state(payload)
    assert restored.cards[ids[0]] == state.cards[ids[0]]
    assert restored.cards[ids[1]].mk_level == 3
    assert set(state.cards) == set(restored.cards)
    assert restored.installed_card_ids() == state.installed_card_ids()
    assert restored.machine_production[drilling.card_id].progress_seconds == 2.
    assert all(len({restored.cards[s.card_id].definition_id for s in site.slots if s.card_id}) <= 1 for site in restored.resource_sites.values())
    assert serialize_game_state(deserialize_game_state(serialize_game_state(restored))) == serialize_game_state(restored)
