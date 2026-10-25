"""Batch lookups must match independent per-vehicle checks and live mutations."""
from copy import deepcopy
from dataclasses import replace
import gc
from hashlib import sha256
from importlib.resources import files
import json
import weakref

import pytest

from production_zero.core import freight, contract_capacity
from production_zero.core.cards import create_card_instance
from production_zero.core.contracts import _capacity_plan
from production_zero.core.enums import Rarity
from production_zero.core.freight import (
    FreightFacility, FreightAssignment, OutboundFreightShipment,
    _FreightDispatchIndex, start_outbound_shipment_for_card, freight_stats,
)
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState, FactoryHall
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from test_phase8_contract_balance import company
from test_contract_priority_auto import fixed

D = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
NOW = 2_000_000_000.


def fleet():
    state = GameState(rng_seed=44, warehouse_capacity=1e9)
    state.freight.facilities.clear()
    for number, (definition_id, kind) in enumerate((('freight.ship', 'harbor'), ('freight.truck', 'garage_depot'),
                                                   ('freight.train', 'rail_station'), ('freight.aircraft', 'airport'))):
        fid = f'home-{3-number}'
        facility = FreightFacility(fid, fid, kind, slot_count=10)
        state.freight.facilities[fid] = facility
        for index, position in enumerate((0, 2, 8, 9)):
            cid = f'{fid}-vehicle-{index}'
            state.cards[cid] = replace(create_card_instance(cid, definition_id, D[definition_id].card_kind,
                                                           (Rarity.COMMON, Rarity.RARE)[index % 2]), mk_level=index + 1)
            facility.slots[position].card_id = cid
            state.freight.assignments[cid] = FreightAssignment(('iron_ore', 'coal')[index % 2],
                                                               ('market', 'contract', 'consortium')[index % 3])
    for rid in ('iron_ore', 'coal'):
        state.ensure_resource(rid).amount = 1e7
    return state


def depart_each(state, indexed):
    index = _FreightDispatchIndex(state.freight) if indexed else None
    ids = [slot.card_id for fid in sorted(state.freight.facilities)
           for slot in sorted(state.freight.facilities[fid].slots, key=lambda s: s.index) if slot.card_id]
    for cid in ids:
        assignment = state.freight.assignments.get(cid)
        card = state.cards.get(cid)
        if assignment is None or card is None:
            continue
        stock = state.ensure_resource(assignment.resource_id)
        quantity = min(stock.amount, freight_stats(card, D[card.definition_id], state.research).capacity)
        target = 'target' if assignment.destination_kind == 'contract' else 'guild|daily|target'
        shipment = start_outbound_shipment_for_card(state.freight, state.cards, D,
            card_id=cid, destination_kind=assignment.destination_kind, resource_id=assignment.resource_id,
            quantity=quantity, target_id=target if assignment.destination_kind != 'market' else None,
            contract_allocations={target: quantity} if assignment.destination_kind == 'contract' and quantity > 0 else None,
            research=state.research, **({'_dispatch_index': index} if indexed else {}))
        if shipment is not None:
            stock.consume(shipment.quantity)


@pytest.mark.parametrize('case', ['normal', 'card_pause', 'hall_pause', 'line_pause', 'locked', 'busy', 'inactive',
                                 'empty_stock', 'no_route', 'wrong_facility', 'duplicate', 'duplicate_paused',
                                 'dictionary_key_differs', 'research', 'reverse_order'])
def test_indexed_departures_match_independent_checks_for_all_vehicle_types(case):
    state = fleet()
    home = state.freight.facilities['home-2']
    cid = home.slots[0].card_id
    if case == 'card_pause':
        state.cards[cid] = replace(state.cards[cid], paused=True)
    elif case == 'hall_pause':
        home.paused = True
    elif case == 'line_pause':
        home.paused_lines.add(1)
    elif case == 'locked':
        home.purchased_slot_indexes = {0, 2, 8}
    elif case in ('busy', 'inactive'):
        state.freight.outbound_shipments['existing'] = OutboundFreightShipment('existing', 'market', resource_id='iron_ore',
            quantity=2, freight_card_id=cid, remaining_seconds=0, active=case == 'busy')
    elif case == 'empty_stock':
        state.resources['iron_ore'].amount = 0
    elif case == 'no_route':
        state.freight.assignments.pop(cid)
    elif case == 'wrong_facility':
        home.facility_type = 'airport'
    elif case in ('duplicate', 'duplicate_paused'):
        home.slots[1].card_id = cid
        state.freight.facilities['home-3'].slots[1].card_id = cid
        if case == 'duplicate_paused':
            state.freight.facilities['home-3'].paused = True
    elif case == 'dictionary_key_differs':
        state.freight.facilities['other-key'] = state.freight.facilities.pop('home-2')
    elif case == 'research':
        from production_zero.core.research import research_catalog
        state.research.unlocked_node_ids.update(nid for nid, node in research_catalog()[1].items() if node.effect_type == 'freight_capacity')
    elif case == 'reverse_order':
        state.freight.facilities = dict(reversed(tuple(state.freight.facilities.items())))
        for facility in state.freight.facilities.values():
            facility.slots.reverse()
    independent, indexed = deepcopy(state), deepcopy(state)
    depart_each(independent, False)
    depart_each(indexed, True)
    assert serialize_game_state(indexed) == serialize_game_state(independent)


def test_new_departures_immediately_reserve_a_vehicle_in_the_batch():
    state = fleet()
    cid = 'home-2-vehicle-0'
    index = _FreightDispatchIndex(state.freight)
    kwargs = dict(card_id=cid, destination_kind='market', resource_id='iron_ore', quantity=1, _dispatch_index=index)
    assert start_outbound_shipment_for_card(state.freight, state.cards, D, **kwargs) is not None
    assert start_outbound_shipment_for_card(state.freight, state.cards, D, **kwargs) is None
    assert state.freight.next_shipment_sequence == 1


def test_normal_engine_dispatch_does_not_use_global_per_vehicle_searches(monkeypatch):
    state = fixed(needs=(1e9, 1e9, 1e9), trucks=3)
    state.freight.facilities['garage-1'] = FreightFacility('garage-1', 'Garage', slot_count=24)
    for n in range(24):
        cid = f'truck{n}'
        if cid not in state.cards:
            state.cards[cid] = create_card_instance(cid, 'freight.truck', D['freight.truck'].card_kind, Rarity.COMMON)
        state.freight.facilities['garage-1'].slots[n].card_id = cid
        state.freight.assignments[cid] = FreightAssignment('iron_ore', 'contract')
    state.ensure_resource('iron_ore').amount = 1e9
    contexts = []
    for method in ('_apply_freight_market_exports', '_apply_freight_contract_deliveries', '_apply_consortium_freight'):
        original = getattr(SimulationEngine, method)
        def record(*args, _original=original, **kwargs):
            contexts.append(kwargs['_dispatch_index'])
            return _original(*args, **kwargs)
        monkeypatch.setattr(SimulationEngine, method, record)
    def forbidden(*args, **kwargs):
        raise AssertionError('Per-vehicle global lookup used in a dispatch batch')
    for name in ('is_freight_card_busy', '_is_card_installed_in_matching_facility', 'freight_card_facility_id'):
        monkeypatch.setattr(freight, name, forbidden)
    count = []
    original_stats = freight.freight_stats
    monkeypatch.setattr(freight, 'freight_stats', lambda *args: (count.append(1), original_stats(*args))[1])
    SimulationEngine(D, utc_now=lambda: NOW).advance_time(state, 0)
    assert len(state.freight.outbound_shipments) == 24
    assert len(contexts) == 3 and all(index is contexts[0] for index in contexts)
    assert len(count) == 24  # Planner and departure share each vehicle's stats.


def test_batch_is_built_after_arrivals_and_busy_vehicles_do_not_depart_twice():
    state = fleet()
    cid = 'home-2-vehicle-0'
    state.freight.outbound_shipments = {
        'done': OutboundFreightShipment('done', 'market', resource_id='iron_ore', quantity=1, freight_card_id=cid, remaining_seconds=.1),
        'still-away': OutboundFreightShipment('still-away', 'market', resource_id='coal', quantity=1,
            freight_card_id='home-2-vehicle-3', remaining_seconds=50),
    }
    SimulationEngine(D, utc_now=lambda: NOW).advance_time(state, .25)
    assert sum(s.freight_card_id == cid for s in state.freight.outbound_shipments.values()) == 1
    assert sum(s.freight_card_id == 'home-2-vehicle-3' for s in state.freight.outbound_shipments.values()) == 1
    assert 'done' not in state.freight.outbound_shipments
    assert state.freight.outbound_shipments['still-away'].remaining_seconds == 49.75


def test_batches_are_discarded_instead_of_accumulating_in_the_engine(monkeypatch):
    from production_zero.core import simulation
    references = []
    class Index(_FreightDispatchIndex):
        def __init__(self, state):
            super().__init__(state)
            references.append(weakref.ref(self))
    monkeypatch.setattr(simulation, '_FreightDispatchIndex', Index)
    state = fleet()
    engine = SimulationEngine(D, utc_now=lambda: NOW)
    for _ in range(30):
        engine.advance_time(state, .25)
    gc.collect()
    assert len(references) == 30 and not any(ref() is not None for ref in references)


@pytest.mark.parametrize('change', ['move', 'pause', 'line', 'route', 'upgrade', 'remove', 'sell', 'load'])
def test_next_batch_observes_live_changes_without_invalidation_hooks(change):
    state = fleet()
    home = state.freight.facilities['home-2']
    cid = home.slots[0].card_id
    _FreightDispatchIndex(state.freight)  # A previous, discarded frame.
    if change == 'move':
        home.slots[1].card_id, home.slots[0].card_id = cid, None
    elif change == 'pause':
        home.paused = True
    elif change == 'line':
        home.paused_lines.add(0)
    elif change == 'route':
        state.freight.assignments[cid] = FreightAssignment('coal', 'market')
    elif change == 'upgrade':
        state.cards[cid] = replace(state.cards[cid], mk_level=99)
    elif change in ('remove', 'sell'):
        home.slots[0].card_id = None
        if change == 'sell':
            state.cards.pop(cid)
    elif change == 'load':
        state = deserialize_game_state(serialize_game_state(state))
        state.freight.facilities['home-2'].paused = True
    independent, indexed = deepcopy(state), deepcopy(state)
    depart_each(independent, False)
    depart_each(indexed, True)
    assert serialize_game_state(indexed) == serialize_game_state(independent)


def original_signature(state):
    """Pre-optimization wire identity: changing this would reroll offer IDs."""
    payload = (
        state.economy_version,
        sorted((c.card_id,c.definition_id,c.mk_level,c.output_bonus_percent,c.power_bonus_percent) for c in state.cards.values()),
        sorted((h.hall_id,h.board_kind,h.specialization,sorted(h.unlocked_slot_indexes())) for h in state.all_production_units()),
        sorted((f.facility_id,f.facility_type,sorted(f.unlocked_slot_indexes())) for f in state.freight.facilities.values()),
        sorted((cid,p.selected_production_id) for cid,p in state.machine_production.items()),
        sorted(state.production_progress.unlocked_production_ids),
        sorted(rid for rid,amount in state.production_progress.lifetime_produced.items() if amount>0),
        sorted(state.research.unlocked_node_ids),sorted(state.research.specializations.items()),
        state.storage_capacity,state.company.level,
    )
    return sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


@pytest.mark.parametrize('change', ['add', 'sell', 'upgrade', 'bonus', 'power', 'recipe', 'unlock', 'first_production',
                                  'research', 'specialization', 'storage', 'level', 'facility', 'economy'])
def test_capacity_cache_detects_lasting_changes_and_preserves_old_signatures(change):
    state = company()
    previous = _capacity_plan(state, D)
    if change == 'add':
        state.cards['extra'] = create_card_instance('extra', 'freight.truck', D['freight.truck'].card_kind, Rarity.COMMON)
    elif change == 'sell':
        state.cards.pop('truck0')
    elif change in ('upgrade', 'bonus', 'power'):
        key, value = {'upgrade': ('mk_level', 2), 'bonus': ('output_bonus_percent', 25), 'power': ('power_bonus_percent', 20)}[change]
        state.cards['truck0'] = replace(state.cards['truck0'], **{key: value})
    elif change == 'recipe':
        state.machine_production['raw0'].selected_production_id = 'resource.coal'
    elif change == 'unlock':
        state.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    elif change == 'first_production':
        state.production_progress.lifetime_produced['iron_ore'] = 1
    elif change == 'research':
        state.research.unlocked_node_ids.add('company.general.s1.major')
    elif change == 'specialization':
        state.research.specializations['some-slot'] = 'iron_ore'
    elif change == 'storage':
        state.warehouse_capacity += 100
    elif change == 'level':
        state.company.level += 1
    elif change == 'facility':
        state.freight.facilities['new'] = FreightFacility('new', 'New', 'rail_station', slot_count=3)
    elif change == 'economy':
        state.economy_version += 1
    cached = _capacity_plan(state, D)
    assert cached == contract_capacity.reachable_capacity(state, D)
    assert cached.signature == original_signature(state)
    assert cached.signature != previous.signature


def test_transient_changes_do_not_repeat_signature_encoding_or_replan(monkeypatch):
    state = company()
    plan = _capacity_plan(state, D)
    def forbidden(*args, **kwargs):
        raise AssertionError('Unchanged lasting inputs were re-encoded or replanned')
    monkeypatch.setattr(contract_capacity, 'capacity_signature', forbidden)
    monkeypatch.setattr(contract_capacity, 'reachable_capacity', forbidden)
    for n in range(20):
        state.cash.amount += 1
        state.resources['iron_ore'].amount += 1
        state.cards['truck0'] = replace(state.cards['truck0'], paused=bool(n % 2))
        state.freight.assignments.clear()
        state.machine_production['raw0'].progress_seconds = n
        state.company.current_xp += 1
        assert _capacity_plan(state, D) is plan


def test_each_capacity_rebuild_scans_usable_cards_and_hashes_only_once(monkeypatch):
    state = company()
    for n in range(2):
        cid = 'fuel' + str(n)
        state.cards[cid] = create_card_instance(cid, 'energy.coal_power_plant', D['energy.coal_power_plant'].card_kind, Rarity.COMMON)
        unit = FactoryHall(cid, cid, 1, board_kind='energy')
        unit.slots[0].card_id = cid
        state.energy_plants[cid] = unit
    state.production_progress.lifetime_produced['coal'] = 1
    calls = {'cards': 0, 'signature': 0}
    for name, key in (('_usable_cards', 'cards'), ('capacity_signature', 'signature')):
        original = getattr(contract_capacity, name)
        def record(*args, _original=original, _key=key, **kwargs):
            calls[_key] += 1
            return _original(*args, **kwargs)
        monkeypatch.setattr(contract_capacity, name, record)
    _capacity_plan(state, D)
    assert calls == {'cards': 1, 'signature': 1}


def test_legacy_estimate_reuses_work_and_detects_returned_production():
    from production_zero.core.contracts import contract_capacity_estimate
    from production_zero.core.machine_operations import return_machines_to_inventory
    state = company()
    previous = contract_capacity_estimate(state, D)
    assert contract_capacity_estimate(state, D) is previous
    state.resources['iron_ore'].amount += 999
    state.freight.assignments.clear()
    assert contract_capacity_estimate(state, D) is previous
    return_machines_to_inventory(state, ('raw0',))
    current = contract_capacity_estimate(state, D)
    assert current is not previous
    state.contracts._capacity_estimate_key = None
    assert contract_capacity_estimate(state, D) == current


def test_saved_state_contains_no_dispatch_or_capacity_cache():
    state = company()
    from production_zero.core.contracts import contract_capacity_estimate
    contract_capacity_estimate(state, D)
    payload = serialize_game_state(state)
    assert not any(key.startswith('_capacity') for key in payload['contracts'])
    loaded = deserialize_game_state(payload)
    assert loaded.contracts._capacity_inputs is None
    assert loaded.contracts._capacity_estimate_key is None
    assert loaded.contracts._capacity_estimate is None


def test_estimate_does_not_confuse_reused_plan_object_ids(monkeypatch):
    from production_zero.core import contracts
    # Simulate Python reusing an old object's address after several plan rebuilds.
    monkeypatch.setattr(contracts, 'id', lambda value: 7, raising=False)
    state = company()
    previous = contracts.contract_capacity_estimate(state, D)
    state.cards['raw0'] = replace(state.cards['raw0'], mk_level=2)
    current = contracts.contract_capacity_estimate(state, D)
    assert current is not previous
    state.contracts._capacity_estimate_key = None
    assert contracts.contract_capacity_estimate(state, D) == current
