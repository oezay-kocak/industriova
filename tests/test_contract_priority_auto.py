"""P6 priorities, physical reservations and repeatable Contract lifecycles."""
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files
from itertools import product
from math import fsum
import json

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import (AssignFreightCard, InstallFreightCard, SellMachines,
    SetContractPriority, SetRegularContractAutoRepeat, DeliverAvailableToContract)
from production_zero.core.contracts import (ActiveContract, ContractBook, ContractOffer,
    CONTRACT_KINDS, REGULAR, DAILY, WEEKLY, accept_contract, cancel_contract,
    initialize_contracts, receive_contract_delivery, refresh_contracts)
from production_zero.core.contract_allocation import allocate_contract_cargo, pending_contract_deliveries
from production_zero.core.enums import Rarity
from production_zero.core.freight import OutboundFreightShipment, contract_shipment_allocations
from production_zero.core.modifiers import market_sale_price
from production_zero.core.progression import initialize_production_progress
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore
from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot
from test_phase8_contract_balance import company

D = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
NOW = 2_000_000_000.


def fixed(needs=(100., 100., 100.), trucks=1, now=NOW):
    s = GameState(6206, warehouse_capacity=1e6)
    initialize_production_progress(s, D); initialize_contracts(s, D, now_utc=now)
    for kind, need in zip(CONTRACT_KINDS, needs):
        offer = ContractOffer(kind, kind, kind.title(), {'iron_ore': need}, 100, 10, 0)
        s.contracts.active[kind] = ActiveContract(offer)
        s.contracts.offers[kind] = [offer]
    for i in range(trucks):
        cid = f'truck{i}'
        s.cards[cid] = create_card_instance(cid, 'freight.truck', D['freight.truck'].card_kind, Rarity.COMMON)
        InstallFreightCard('garage-1', i, cid, D).apply(s)
        AssignFreightCard(cid, 'iron_ore', 'contract').apply(s)
    s.ensure_resource('iron_ore').amount = 1000
    return s


@pytest.mark.parametrize('modes,expected', [
    ((0, 0, 0), (30, 30, 30)), ((1, 1, 1), (30, 30, 30)), ((2, 2, 2), (30, 30, 30)),
    ((2, 1, 0), (90, 0, 0)), ((0, 1, 2), (0, 0, 90)), ((1, 1, 0), (45, 45, 0)),
    ((0, 2, 2), (0, 45, 45)), ((2, 0, 2), (45, 0, 45))])
def test_priority_modes_have_literal_expected_shares(modes, expected):
    s = fixed()
    for kind, priority in zip(CONTRACT_KINDS, modes): SetContractPriority(kind, priority).apply(s)
    before = serialize_game_state(s)
    plan = allocate_contract_cargo(s, 'iron_ore', 90)
    assert tuple(plan.get(k, 0) for k in CONTRACT_KINDS) == pytest.approx(expected)
    assert serialize_game_state(s) == before


@pytest.mark.parametrize('modes', list(product(range(3), repeat=3)))
@pytest.mark.parametrize('quantity', (.001, 40., 250., 500.))
def test_every_priority_combination_conserves_cargo_and_finishes_higher_tiers_first(modes, quantity):
    s = fixed((10, 70, 200))
    s.contracts.priorities = dict(zip(CONTRACT_KINDS, modes))
    plan = allocate_contract_cargo(s, 'iron_ore', quantity)
    assert fsum(plan.values()) == pytest.approx(min(quantity, 280))
    for kind, need in zip(CONTRACT_KINDS, (10, 70, 200)):
        assert 0 <= plan.get(kind, 0) <= need
        if plan.get(kind, 0) > 0:
            for higher, higher_need in zip(CONTRACT_KINDS, (10, 70, 200)):
                if s.contracts.priorities[higher] > s.contracts.priorities[kind]:
                    assert plan.get(higher, 0) == higher_need


def test_equal_shares_redistribute_surplus_and_subtract_actual_target_reservations():
    s = fixed((10, 100, 100))
    assert allocate_contract_cargo(s, 'iron_ore', 90) == {REGULAR: 10, DAILY: 40, WEEKLY: 40}
    s.freight.outbound_shipments['reserved'] = OutboundFreightShipment('reserved', 'contract',
        resource_id='iron_ore', quantity=95, target_id=DAILY, remaining_seconds=60)
    assert allocate_contract_cargo(s, 'iron_ore', 40) == {DAILY: 5, REGULAR: 10, WEEKLY: 25}


@pytest.mark.parametrize('trucks', (1, 2, 3))
def test_one_vehicle_can_share_its_cargo_without_extra_capacity_or_extra_trips(trucks):
    s = fixed(trucks=trucks); s.resources['iron_ore'].amount = 90
    engine = SimulationEngine(D, utc_now=lambda: NOW)
    engine.advance_time(s, 0)
    shipments = list(s.freight.outbound_shipments.values())
    assert len(shipments) == trucks
    total = min(90, trucks * 40)
    assert fsum(q.quantity for q in shipments) == total
    assert s.resources['iron_ore'].amount == 90 - total
    assert all(q.quantity <= 40 and fsum(q.contract_allocations.values()) == pytest.approx(q.quantity) for q in shipments)
    pending = pending_contract_deliveries(s)
    assert all(pending[k, 'iron_ore'] == pytest.approx(total / 3) for k in CONTRACT_KINDS)
    # Re-running dispatch cannot use a busy vehicle a second time.
    engine.advance_time(s, 0); assert len(s.freight.outbound_shipments) == trucks
    engine.advance_time(s, 60)
    assert all(s.contracts.active[k].delivered['iron_ore'] == pytest.approx(total / 3) for k in CONTRACT_KINDS)
    assert s.freight.delivery_statistics.rate(facility_id='garage-1').contract == pytest.approx(total)
    assert not s.cash.amount and not s.company_xp_progress.xp_by_source


def test_priority_change_does_not_redirect_reserved_cargo_and_survives_reload():
    s = fixed(); engine = SimulationEngine(D, utc_now=lambda: NOW)
    engine.advance_time(s, 0)
    reserved = deepcopy(next(iter(s.freight.outbound_shipments.values())))
    SetContractPriority(WEEKLY, 2).apply(s)
    assert next(iter(s.freight.outbound_shipments.values())) == reserved
    s = deserialize_game_state(serialize_game_state(s)); engine.advance_time(s, 60)
    assert all(s.contracts.active[k].delivered['iron_ore'] == pytest.approx(40 / 3) for k in CONTRACT_KINDS)
    new = next(iter(s.freight.outbound_shipments.values()))
    assert new.contract_allocations == {WEEKLY: 40}


def test_explicit_delivery_uses_same_priority_planner():
    s = fixed(); SetContractPriority(WEEKLY, 2).apply(s)
    DeliverAvailableToContract(REGULAR, D).apply(s)
    shipment = next(iter(s.freight.outbound_shipments.values()))
    assert shipment.contract_allocations == {WEEKLY: 40}


def test_partial_cancellation_preserves_other_destinations_and_locked_sale_quote():
    from production_zero.core.research import research_catalog
    s = fixed(); s.contracts.active.pop(WEEKLY)
    engine = SimulationEngine(D, utc_now=lambda: NOW); engine.advance_time(s, 0)
    shipment = next(iter(s.freight.outbound_shipments.values()))
    original = dict(shipment.contract_allocations)
    s.research.unlocked_node_ids = {k for k, n in research_catalog()[1].items() if n.effect_type == 'value'}
    sale_price = market_sale_price(s, 'iron_ore')
    cancel_contract(s, REGULAR, D)
    assert shipment.destination_kind == 'contract' and shipment.contract_allocations == original
    assert shipment.cancelled_contract_prices[REGULAR] == sale_price
    assert (REGULAR, 'iron_ore') not in pending_contract_deliveries(s)
    s.research.unlocked_node_ids.clear()
    s = deserialize_game_state(serialize_game_state(s)); engine.advance_time(s, 60)
    assert s.contracts.active[DAILY].delivered['iron_ore'] == 20
    assert s.cash.amount == pytest.approx(20 * sale_price)
    assert s.company_xp_progress.xp_by_source['market_sales'] == pytest.approx(2 * sale_price)
    assert s.freight.delivery_statistics.rate(facility_id='garage-1').contract == 20
    assert s.freight.delivery_statistics.rate(facility_id='garage-1').sell == 20


def auto_company():
    s = company(resources=('iron_ore', 'coal'), trucks=3)
    initialize_contracts(s, D, now_utc=NOW)
    offer = s.contracts.offers[REGULAR][0]
    accept_contract(s, REGULAR, offer.contract_id, D, selected_resource_ids=('iron_ore', 'coal'), auto_repeat=True, now_utc=NOW)
    return s


def finish_regular(s):
    active = s.contracts.active[REGULAR]
    for rid, quantity in active.offer.requirements.items():
        receive_contract_delivery(s, active.offer.contract_id, rid, quantity, D, now_utc=NOW)
    return active


def test_repeat_retains_products_requotes_each_cycle_and_rewards_each_id_once():
    s = auto_company(); SetContractPriority(REGULAR, 2).apply(s)
    total_cash = total_xp = 0.
    for generation in range(1, 11):
        old = s.contracts.active[REGULAR]; total_cash += old.offer.reward_cash; total_xp += old.offer.reward_xp
        frozen = deepcopy(old.offer)
        finish_regular(s)
        current = s.contracts.active[REGULAR]
        assert old.status == 'completed' and old.offer == frozen
        assert current.offer.contract_id != old.offer.contract_id and s.contracts.regular_generation == generation
        assert tuple(current.offer.requirements) == ('iron_ore', 'coal')
        assert current.offer.quoted_level == s.company.level
        assert not current.delivered and s.contracts.priorities[REGULAR] == 2
        before = serialize_game_state(s)
        receive_contract_delivery(s, old.offer.contract_id, 'iron_ore', 100000, D, now_utc=NOW)
        assert serialize_game_state(s) == before
    assert s.cash.amount == pytest.approx(total_cash)
    assert s.company_xp_progress.xp_by_source['regular_contracts'] == pytest.approx(total_xp)
    assert not s.company_xp_progress.xp_by_source.get('market_sales', 0)


def test_turning_auto_off_keeps_the_current_contract_then_stops():
    s = auto_company(); old = s.contracts.active[REGULAR]
    SetRegularContractAutoRepeat(False, old.offer.contract_id).apply(s)
    assert s.contracts.active[REGULAR] is old
    finish_regular(s)
    assert REGULAR not in s.contracts.active and s.contracts.regular_generation == 1
    refresh_contracts(s, D, now_utc=NOW + 100)
    assert REGULAR not in s.contracts.active


def test_cancelling_regular_turns_repeat_off_instead_of_reaccepting():
    s = auto_company(); cancel_contract(s, REGULAR, D)
    refresh_contracts(s, D, now_utc=NOW + 100)
    assert not s.contracts.regular_auto.enabled and REGULAR not in s.contracts.active


def test_auto_pause_is_saved_does_not_spam_and_resumes_when_capacity_returns(tmp_path):
    s = auto_company()
    vehicles = {cid: c for cid, c in s.cards.items() if c.definition_id == 'freight.truck'}
    SellMachines(tuple(vehicles), D).apply(s)
    finish_regular(s)
    auto = s.contracts.regular_auto
    assert auto.enabled and auto.pause_reason and REGULAR not in s.contracts.active
    assert auto.resource_ids == ('iron_ore', 'coal')
    activity = list(s.communications.pending_activity)
    for _ in range(5): refresh_contracts(s, D, now_utc=NOW)
    assert s.communications.pending_activity == activity
    store = SQLiteSaveStore(tmp_path / 'auto.sqlite'); store.initialize(); store.save('company', s); s = store.load('company')
    assert s.contracts.regular_auto == auto
    s.cards.update(vehicles)
    for index, cid in enumerate(vehicles): InstallFreightCard('garage', index, cid, D).apply(s)
    refresh_contracts(s, D, now_utc=NOW)
    assert REGULAR in s.contracts.active and not s.contracts.regular_auto.pause_reason
    assert tuple(s.contracts.active[REGULAR].offer.requirements) == ('iron_ore', 'coal')


def test_stale_auto_toggle_and_invalid_preferences_are_atomic():
    s = auto_company(); old_id = s.contracts.active[REGULAR].offer.contract_id; finish_regular(s)
    bad = [SetRegularContractAutoRepeat(True, old_id), SetRegularContractAutoRepeat('yes'),
           SetContractPriority(REGULAR, True), SetContractPriority(REGULAR, 3), SetContractPriority('unknown', 1)]
    for command in bad:
        before = serialize_game_state(s)
        with pytest.raises(ValueError): command.apply(s)
        assert serialize_game_state(s) == before


def test_replay_of_old_cargo_never_delivers_to_the_renewed_contract():
    s = auto_company(); old = s.contracts.active[REGULAR]
    late = OutboundFreightShipment('late', 'contract', resource_id='iron_ore', quantity=10,
        target_id=old.offer.contract_id, contract_allocations={old.offer.contract_id: 10}, active=False)
    finish_regular(s); current = s.contracts.active[REGULAR]
    cash = s.cash.amount
    engine = SimulationEngine(D, utc_now=lambda: NOW)
    engine._complete_outbound_shipments(s, [late])
    assert not current.delivered and s.cash.amount == cash + 10
    assert s.company_xp_progress.xp_by_source['market_sales'] == 1
    before = serialize_game_state(s); engine._complete_outbound_shipments(s, [late])
    assert serialize_game_state(s) == before


@pytest.mark.parametrize('dt', (1, 6, 60, 600, 1800))
def test_multiple_real_auto_completions_match_online_offline_and_reload(dt):
    def run(step, reload):
        s = auto_company()
        for i in range(3): AssignFreightCard(f'truck{i}', ('iron_ore', 'coal')[i % 2], 'contract').apply(s)
        clock = [NOW]; engine = SimulationEngine(D, utc_now=lambda: clock[0])
        for index in range(round(3600 / step)):
            clock[0] += step; engine.advance_time(s, step)
            if reload and index + 1 == round(1800 / step): s = deserialize_game_state(serialize_game_state(s))
        return s.contracts.regular_generation, s.cash.amount, s.company_xp_progress.xp_by_source, s.contracts.active[REGULAR].offer, s.contracts.active[REGULAR].delivered
    baseline = run(1, False)
    assert baseline[0] >= 2
    assert run(dt, False) == baseline and run(dt, True) == baseline


def test_snapshot_detaches_preferences_and_mixed_cargo():
    s = fixed(); SimulationEngine(D, utc_now=lambda: NOW).advance_time(s, 0)
    captured = snapshot_game_state(s); encoded = encode_snapshot(captured)
    SetContractPriority(WEEKLY, 2).apply(s)
    cancel_contract(s, REGULAR, D)
    assert encode_snapshot(captured) == encoded
    saved = json.loads(encoded)
    assert saved['contracts']['priorities'][WEEKLY] == 0
    assert not next(iter(saved['freight']['outbound_shipments'].values()))['cancelled_contract_prices']


def test_expired_target_sells_only_its_reserved_share_at_arrival():
    midnight = (NOW // 86400 + 1) * 86400
    s = fixed(now=midnight - 30); s.contracts.active.pop(WEEKLY)
    expired = s.contracts.active[DAILY]
    clock = [midnight - 30]; engine = SimulationEngine(D, utc_now=lambda: clock[0])
    engine.advance_time(s, 0); clock[0] += 60; engine.advance_time(s, 60)
    assert expired.status == 'expired' and DAILY not in s.contracts.active
    assert s.contracts.active[REGULAR].delivered['iron_ore'] == 20
    assert s.cash.amount == 20 and s.company_xp_progress.xp_by_source['market_sales'] == 2


def test_cancelling_all_targets_still_sells_exactly_one_physical_load():
    s = fixed(); s.contracts.active.pop(WEEKLY)
    engine = SimulationEngine(D, utc_now=lambda: NOW); engine.advance_time(s, 0)
    cancel_contract(s, REGULAR, D); cancel_contract(s, DAILY, D)
    s = deserialize_game_state(serialize_game_state(s)); engine.advance_time(s, 60)
    assert s.cash.amount == 40 and s.company_xp_progress.xp_by_source['market_sales'] == 4
    assert not s.freight.outbound_shipments


def test_cancelled_share_never_delivers_to_a_reaccepted_offer_with_same_id():
    s = fixed(); s.contracts.active.pop(WEEKLY)
    engine = SimulationEngine(D, utc_now=lambda: NOW); engine.advance_time(s, 0)
    old = s.contracts.active[REGULAR].offer
    cancel_contract(s, REGULAR, D)
    accept_contract(s, REGULAR, old.contract_id, D, now_utc=NOW)
    assert (old.contract_id, 'iron_ore') not in pending_contract_deliveries(s)
    engine.advance_time(s, 60)
    assert not s.contracts.active[REGULAR].delivered
    assert s.contracts.active[DAILY].delivered['iron_ore'] == 20 and s.cash.amount == 20


def test_simultaneous_rewards_requote_auto_identically_after_json_key_sorting():
    s = auto_company(); old = s.contracts.active[REGULAR]
    old.offer = replace(old.offer, requirements={'iron_ore': 20., 'coal': 20.}, reward_cash=100, reward_xp=1)
    old.delivered['coal'] = 20
    daily = ContractOffer('daily', DAILY, 'Daily', {'iron_ore': 20.}, 100, 60000, 0)
    s.contracts.active[DAILY] = ActiveContract(daily); s.contracts.offers[DAILY] = [daily]
    shipment = OutboundFreightShipment('mixed', 'contract', resource_id='iron_ore', quantity=40,
        active=False, contract_allocations={old.offer.contract_id: 20, 'daily': 20})
    s.freight.outbound_shipments['mixed'] = shipment
    restored = deserialize_game_state(json.loads(json.dumps(serialize_game_state(s), sort_keys=True)))
    engine = SimulationEngine(D, utc_now=lambda: NOW)
    engine._complete_outbound_shipments(s, [shipment], now_utc=NOW)
    engine._complete_outbound_shipments(restored, [restored.freight.outbound_shipments['mixed']], now_utc=NOW)
    assert s.company.level > 25
    assert restored.company == s.company
    assert restored.contracts.active[REGULAR].offer == s.contracts.active[REGULAR].offer
    assert restored.contracts.active[REGULAR].offer.quoted_level == restored.company.level


def test_building_order_and_reload_do_not_change_contract_capacity_signature():
    from production_zero.core.contract_capacity import capacity_signature
    from production_zero.core.state import FactoryHall
    from production_zero.core.freight import FreightFacility
    s = auto_company()
    for uid in ('hall-2', 'hall-10'): s.halls[uid] = FactoryHall(uid, uid, 3, max_lines=5)
    for uid in ('fleet-2', 'fleet-10'): s.freight.facilities[uid] = FreightFacility(uid, uid)
    signature = capacity_signature(s)
    s.halls = dict(reversed(list(s.halls.items())))
    s.freight.facilities = dict(reversed(list(s.freight.facilities.items())))
    assert capacity_signature(s) == signature
    restored = deserialize_game_state(json.loads(json.dumps(serialize_game_state(s), sort_keys=True)))
    assert capacity_signature(restored) == signature


@pytest.mark.parametrize('allocation,cancelled', [
    ({'a': -1}, {}), ({'a': float('inf')}, {}), ({'a': 20}, {}),
    ({'a': 40}, {'missing': 1}), ({'a': 40}, {'a': float('nan')})])
def test_invalid_mixed_cargo_is_rejected(allocation, cancelled):
    with pytest.raises(ValueError):
        OutboundFreightShipment('bad', 'contract', quantity=40,
            contract_allocations=allocation, cancelled_contract_prices=cancelled)


@pytest.mark.parametrize('kind', (DAILY, WEEKLY))
def test_auto_repeat_cannot_be_enabled_for_another_contract_type(kind):
    s = auto_company(); offer = s.contracts.offers[kind][0]; before = serialize_game_state(s)
    with pytest.raises(ValueError): accept_contract(s, kind, offer.contract_id, D, auto_repeat=True, now_utc=NOW)
    assert serialize_game_state(s) == before


@pytest.mark.parametrize('did,kind', [('freight.truck', 'garage_depot'), ('freight.train', 'rail_station'),
    ('freight.aircraft', 'airport'), ('freight.ship', 'harbor')])
@pytest.mark.parametrize('mk', (1, 99))
def test_mixed_loads_obey_each_vehicle_types_real_capacity_and_travel_time(did, kind, mk):
    from production_zero.core.freight import FreightFacility, freight_stats
    s = fixed(trucks=0)
    s.freight.facilities = {'vehicle-home': FreightFacility('vehicle-home', 'Home', kind, slot_count=1)}
    card = replace(create_card_instance('carrier', did, D[did].card_kind, Rarity.COMMON), mk_level=mk)
    s.cards['carrier'] = card; InstallFreightCard('vehicle-home', 0, 'carrier', D).apply(s)
    AssignFreightCard('carrier', 'iron_ore', 'contract').apply(s)
    stats = freight_stats(card, D[did]); quantity = stats.capacity * .9
    for active in s.contracts.active.values():
        active.offer = replace(active.offer, requirements={'iron_ore': stats.capacity})
    s.resources['iron_ore'].amount = quantity
    engine = SimulationEngine(D, utc_now=lambda: NOW); engine.advance_time(s, 0)
    assert len(s.freight.outbound_shipments) == 1
    shipment = next(iter(s.freight.outbound_shipments.values()))
    assert shipment.quantity == pytest.approx(quantity)
    assert shipment.transport_time_seconds == stats.transport_time_seconds
    assert all(v == pytest.approx(quantity / 3) for v in shipment.contract_allocations.values())
    engine.advance_time(s, stats.transport_time_seconds)
    assert all(a.delivered['iron_ore'] == pytest.approx(quantity / 3) for a in s.contracts.active.values())
    assert not s.freight.outbound_shipments and not s.cash.amount


def test_replaying_accept_cannot_undo_an_explicit_auto_stop():
    s = auto_company(); active = s.contracts.active[REGULAR]
    SetRegularContractAutoRepeat(False, active.offer.contract_id).apply(s)
    before = serialize_game_state(s)
    accept_contract(s, REGULAR, active.offer.contract_id, D,
        selected_resource_ids=('iron_ore', 'coal'), auto_repeat=True, now_utc=NOW)
    assert serialize_game_state(s) == before and not s.contracts.regular_auto.enabled


def test_daily_reset_preserves_active_regular_terms_and_its_offer_row():
    s = auto_company(); frozen = deepcopy(s.contracts.active[REGULAR].offer)
    s.company.level += 1  # The next quote could differ, but this one stays fixed.
    midnight = (NOW // 86400 + 1) * 86400
    clock = [midnight - 30]; engine = SimulationEngine(D, utc_now=lambda: clock[0])
    refresh_contracts(s, D, now_utc=clock[0])
    clock[0] += 60; engine.advance_time(s, 60)
    assert s.contracts.active[REGULAR].offer == frozen
    assert s.contracts.offers[REGULAR][0].contract_id == frozen.contract_id
    assert s.contracts.regular_auto.enabled and s.contracts.regular_generation == 0


def test_previous_production_xp_ruleset_is_not_imported():
    payload = serialize_game_state(auto_company()); payload['game_ruleset'] = 'production-sales-xp-v1'
    payload['contracts'].pop('priorities'); payload['contracts'].pop('regular_auto')
    with pytest.raises(ValueError, match='new company'): deserialize_game_state(payload)
