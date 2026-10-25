from dataclasses import replace
from fractions import Fraction
from release_test_support import purchase_state
from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import CommandBus, BuyCommonSupplyCard
from production_zero.core.contracts import (
    CONTRACT_KINDS, ActiveContract, ContractOffer, accept_contract,
    initialize_contracts, receive_contract_delivery,
)
from production_zero.core.definitions import MachineDefinition
from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.enums import Rarity
from production_zero.core.freight import freight_stats
from production_zero.core.inventory import build_card_inventory_rows
from production_zero.core.production_guide import ProductionGuideRecipeIndex
from production_zero.core.resources import ResourceStock
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore, serialize_game_state, deserialize_game_state


@pytest.fixture
def definitions():
    return load_card_definitions(Path('src/production_zero/data/game_definitions.json'))


def install(state, definitions, definition_id, resource=None):
    hall = state.halls.setdefault('hall', FactoryHall('hall', 'Hall', 6))
    card_id = str(len(state.cards))
    definition = definitions[definition_id]
    card = create_card_instance(card_id, definition_id, definition.card_kind, Rarity.COMMON)
    state.cards[card_id] = card
    hall.slots[int(card_id)].card_id = card_id
    if resource:
        option = next(o for o in definition.available_production_options if o.output_resource == resource)
        state.ensure_machine_production(card_id, resource, option.production_id)
    return card


def test_all_base_recipes_have_whole_inputs_and_simple_adjacent_ratios(definitions):
    import json
    reference=json.loads((Path(__file__).parent/'fixtures/economy-n1-c2.json').read_text())
    index = ProductionGuideRecipeIndex(definitions)
    entries = {o.output_resource: index.produced_by(o.output_resource)[0]
               for d in definitions.values() if isinstance(d, MachineDefinition)
               for o in d.available_production_options}
    assert len(entries) == 353
    edges = 0
    for entry in entries.values():
        assert entry.cycle_seconds == ECONOMIC_CYCLE_SECONDS
        assert entry.output_amount.is_integer()
        for rid, amount in entry.production.input_resources.items():
            assert float(amount).is_integer()
            ratio = Fraction(str(entries[rid].output_amount)) / Fraction(str(amount))
            approved=reference[entry.production.output_resource]['new']
            expected=Fraction(str(reference[rid]['new']['output']))/Fraction(str(approved['inputs'][rid]))
            assert ratio==expected
            edges += 1
    assert edges == 708
    for d in definitions.values():
        if isinstance(d, MachineDefinition):
            assert d.cycle_seconds == 6
            assert all(o.cycle_seconds_for(d) == 6 for o in d.available_production_options)


@pytest.mark.parametrize('resource', ['copper', 'copper_wire', 'industrial_equipment', 'high_speed_network_system'])
def test_guide_recipe_matches_one_simulated_cycle(definitions, resource):
    entry = ProductionGuideRecipeIndex(definitions).produced_by(resource)[0]
    state = GameState(11)
    install(state, definitions, 'energy.nuclear_power_plant')
    install(state, definitions, entry.machine_definition_id, resource)
    state.resources['nuclear_fuel_assembly'] = ResourceStock(100, 10000)
    for rid, amount in entry.production.input_resources.items():
        state.resources[rid] = ResourceStock(amount * 10, 10000)
    state.resources[resource] = ResourceStock(0, 10000)
    before = {rid: state.resources[rid].amount for rid in entry.production.input_resources}
    totals = SimulationEngine(definitions).advance_time(state, 6)
    assert totals.outputs[resource] == entry.output_amount
    for rid, amount in entry.production.input_resources.items():
        assert state.resources[rid].amount == pytest.approx(before[rid] - amount)


def test_one_coal_extractor_sustains_two_plants_over_hour(definitions):
    state = GameState(12)
    install(state, definitions, 'energy.coal_power_plant')
    install(state, definitions, 'energy.coal_power_plant')
    install(state, definitions, 'machine.extractor', 'coal')
    state.resources['coal'] = ResourceStock(24, 10000)
    engine = SimulationEngine(definitions)
    for _ in range(3600):
        engine.tick(state)
    assert state.resources['coal'].amount == pytest.approx(24)
    assert state.energy.generated == 120
    assert state.energy.consumed == 6


@pytest.mark.parametrize('kind', CONTRACT_KINDS)
def test_contract_cash_frozen_at_accept_and_roundtrips(definitions, tmp_path, kind):
    state = GameState(13)
    initialize_contracts(state, definitions)
    state.contracts.active.pop(kind, None)
    from production_zero.core.modifiers import contract_cash_quote
    quoted = round(contract_cash_quote(state, {"copper": 40}) * {"regular":1.,"daily":1.2,"weekly":1.4}[kind], 2)
    offer = ContractOffer('test', kind, 'Copper', {'copper': 40}, quoted, 5, 0)
    state.contracts.offers[kind] = [offer]
    state.market.ensure_resource('copper').current_price = 3.5
    accept_contract(state, kind, 'test', definitions)
    assert state.contracts.active[kind].offer.reward_cash == quoted
    state.market.ensure_resource('copper').current_price = 100
    store = SQLiteSaveStore(tmp_path / 'save.db')
    store.initialize(); store.save('test', state)
    restored = store.load('test')
    assert restored.contracts.active[kind].offer.reward_cash == quoted
    receive_contract_delivery(restored, 'test', 'copper', 40)
    assert restored.cash.amount == quoted


def test_old_accepted_reward_and_machine_assignment_are_preserved(definitions):
    state = GameState(14)
    card = install(state, definitions, 'machine.processor', 'steel')
    state.machine_production[card.card_id].progress_seconds = 2.5
    offer = ContractOffer('old', 'regular', 'Legacy', {'copper': 40}, 105, 5, 0)
    state.contracts.active['regular'] = ActiveContract(offer, {'copper': 20})
    restored = deserialize_game_state(serialize_game_state(state))
    assert restored.contracts.active['regular'].offer.reward_cash == 105
    assert restored.machine_production[card.card_id].selected_production_id == 'recipe.processor.steel'
    assert restored.machine_production[card.card_id].progress_seconds == 2.5


def test_common_multibuy_is_atomic_and_inventory_cards_stack(definitions):
    state = purchase_state(15)
    bus = CommandBus(state)
    state.cash.amount = 1
    with pytest.raises(ValueError):
        bus.dispatch(BuyCommonSupplyCard('machine.extractor', definitions, 4))
    assert not state.cards and state.cash.amount == 1
    state.cash.amount = 10000
    bus.dispatch(BuyCommonSupplyCard('machine.extractor', definitions, 4))
    assert len(state.cards) == 4
    assert not state.installed_card_ids()
    rows = build_card_inventory_rows(state, definitions)
    assert {(r.status, r.quantity) for r in rows} == {('Available', 4)}


def test_freight_planning_preserves_transit_and_rarity(definitions):
    for definition_id, capacity, duration in [('freight.truck', 40, 60), ('freight.train', 400, 120)]:
        d = definitions[definition_id]
        card = create_card_instance('test', definition_id, d.card_kind, Rarity.COMMON)
        stats = freight_stats(card, d)
        assert stats.capacity == capacity and stats.transport_time_seconds == duration
        assert stats.capacity_per_cycle == pytest.approx(capacity * 6 / duration)
        rare = replace(card, output_bonus_percent=10)
        stats = freight_stats(rare, d)
        assert stats.capacity_per_cycle == pytest.approx(capacity * 1.1 * 6 / (duration * 1.05))
