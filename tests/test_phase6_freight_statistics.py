"""Real completion allocations, bounded simulation windows and schema migration."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import pytest
from test_phase4_slot_permutations import definitions
from test_freight import _set_active_contract
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState
from production_zero.core.freight import (FreightFacility, FreightAssignment, OutboundFreightShipment,
    start_outbound_shipment_for_card, advance_outbound_shipments, build_freight_facility)
from production_zero.core.freight_statistics import FreightDeliveryStatistics
from production_zero.core.simulation import SimulationEngine
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore


def company(definitions, did='freight.truck'):
    s=deserialize_game_state(serialize_game_state(GameState(197)));s.cash.amount=1e12
    kind=definitions[did].facility_id
    u=FreightFacility('origin','Origin',kind,slot_count=3);s.freight.facilities={u.facility_id:u}
    for i,slot in enumerate(u.slots):
        cid=f'truck-{i}';s.cards[cid]=create_card_instance(cid,did,definitions[did].card_kind,Rarity.COMMON);slot.card_id=cid
    s.ensure_resource('iron_ore').amount=10000
    return s,u


def depart(s,d, destination='market',quantity=40,target=None,cid='truck-0'):
    s.freight.assignments[cid]=FreightAssignment('iron_ore',destination)
    return start_outbound_shipment_for_card(s.freight,s.cards,d,card_id=cid,destination_kind=destination,
        resource_id='iron_ore',quantity=quantity,target_id=target,market_price=2)


def complete(s,d,shipment,elapsed=60):
    s.freight.delivery_statistics.advance(elapsed)
    shipment.remaining_seconds=0
    completed=advance_outbound_shipments(s.freight,0)
    engine=SimulationEngine(d)
    engine._complete_outbound_shipments(s,completed)
    return engine


@pytest.mark.parametrize('amount',[0.000001,7.5,40])
def test_sell_counts_only_processed_quantity(definitions,amount):
    s,u=company(definitions);q=depart(s,definitions,quantity=amount)
    assert s.freight.delivery_statistics.rate(facility_id=u.facility_id).total==0
    cash=s.cash.amount;engine=complete(s,definitions,q)
    r=s.freight.delivery_statistics.rate(card_id='truck-0')
    assert r.sell==amount and r.total==amount and s.cash.amount==pytest.approx(cash+amount*2)
    assert s.freight.delivery_statistics.rate(facility_id='origin')==r
    engine._complete_outbound_shipments(s,(q,))
    assert s.freight.delivery_statistics.rate(card_id='truck-0')==r and s.cash.amount==pytest.approx(cash+amount*2)


@pytest.mark.parametrize('status,needed',[('active',40),('active',13),('cancelled',40),('expired',40)])
def test_contract_final_allocation(definitions,status,needed):
    s,u=company(definitions);_set_active_contract(s,'daily','manual','iron_ore',needed)
    s.contracts.active['daily'].status=status
    q=depart(s,definitions,'contract',40,'manual');complete(s,definitions,q)
    r=s.freight.delivery_statistics.rate(card_id='truck-0')
    expected=needed if status=='active' else 0
    assert (r.sell,r.contract,r.consortium,r.total)==(40-expected,expected,0,40)


@pytest.mark.parametrize('case',['full','partial','expired','cancelled','membership','wrong-id'])
def test_consortium_final_allocation(definitions,case):
    from production_zero.core.consortium import ConsortiumService, ConsortiumContract, ConsortiumPersonalReward
    s,u=company(definitions);team=ConsortiumService(s,definitions).create('Delivery Team')
    contract=ConsortiumContract('manual','weekly','active',0,1e20,{'iron_ore':13 if case=='partial' else 40},ConsortiumPersonalReward(),0)
    team.contracts['weekly']=contract
    q=depart(s,definitions,'consortium',40,f'{team.consortium_id}|weekly|manual')
    if case=='expired':contract.expires_at=1
    if case=='cancelled':contract.status='cancelled'
    if case=='membership':team.members.clear()
    if case=='wrong-id':contract.contract_id='replacement'
    complete(s,definitions,q)
    r=s.freight.delivery_statistics.rate(card_id='truck-0');accepted=40 if case=='full' else 13 if case=='partial' else 0
    assert (r.sell,r.contract,r.consortium,r.total)==(40-accepted,0,accepted,40)


@pytest.mark.parametrize('seconds',[0,10,30,59,60,61,600,601,1e9])
def test_window_warmup_normalization_and_expiry(seconds):
    stats=FreightDeliveryStatistics();stats.record('c','f',sell=12)
    stats.advance(seconds);r=stats.rate(card_id='c')
    assert r.measuring==(seconds<60)
    assert r.total==pytest.approx(0 if seconds==0 or seconds>=60 else 12*60/seconds)
    assert len(stats.buckets)==(1 if seconds<600 else 0)


@pytest.mark.parametrize('instant',[0,0.1,9.999,10,29.5,59,59.999,60,599.999,600])
def test_bucket_boundaries_roundtrip(instant):
    stats=FreightDeliveryStatistics();stats.advance(instant);stats.record('c','f',sell=3,contract=4,consortium=5)
    loaded=FreightDeliveryStatistics.from_snapshot(json.loads(json.dumps(stats.snapshot())))
    assert loaded.snapshot()==stats.snapshot() and loaded.rate(card_id='c')==stats.rate(card_id='c')
    until=60-(instant%1);stats.advance(until);loaded.advance(until)
    assert stats.rate(card_id='c').total==0 and loaded.snapshot()==stats.snapshot()


@pytest.mark.parametrize('did',['freight.truck','freight.train','freight.aircraft','freight.ship'])
def test_real_engine_paused_facility_and_upgrade(definitions,did):
    s,u=company(definitions,did);q=depart(s,definitions,quantity=7);assert q.source_facility_id=='origin'
    frozen=deepcopy(q);u.paused=True;s.cards['truck-0']=replace(s.cards['truck-0'],paused=True,mk_level=20)
    engine=SimulationEngine(definitions)
    engine.advance_time(s,q.remaining_seconds)
    assert not s.freight.outbound_shipments
    assert s.freight.delivery_statistics.rate(card_id='truck-0').total==pytest.approx(7)
    assert (q.quantity,q.transport_capacity,q.transport_time_seconds)==(frozen.quantity,frozen.transport_capacity,frozen.transport_time_seconds)
    engine.advance_time(s,60)
    assert s.freight.delivery_statistics.rate(card_id='truck-0').total==0


@pytest.mark.parametrize('kinds',[('garage_depot','garage_depot'),('garage_depot','rail_station'),('airport','harbor')])
def test_facilities_never_mix_and_deleted_owners_expire(kinds):
    stats=FreightDeliveryStatistics();stats.advance(60)
    stats.record('c1','f1',sell=5);stats.record('c2','f1',contract=7);stats.record('c3','f2',consortium=11)
    assert stats.rate(facility_id='f1').total==12 and stats.rate(facility_id='f2').total==11
    assert stats.rate(card_id='c1').total+stats.rate(card_id='c2').total==stats.rate(facility_id='f1').total
    stats.advance(1);stats.record('c1','f2',sell=13)
    assert stats.rate(card_id='c1').total==18 and stats.rate(facility_id='f1').total==12 and stats.rate(facility_id='f2').total==24
    stats.advance(600);assert not stats.buckets and not stats._vehicles and not stats._facilities


def test_real_move_uses_departure_owner_and_sale_does_not_reassign(definitions):
    from production_zero.core.freight import move_freight_vehicle
    from production_zero.core.machine_operations import sell_machines
    s,u=company(definitions);second=build_freight_facility(s.freight,'garage_depot')
    q=depart(s,definitions,quantity=9);complete(s,definitions,q)
    move_freight_vehicle(s,definitions,'truck-0',second.facility_id,0)
    q=depart(s,definitions,quantity=11);assert q.source_facility_id==second.facility_id
    complete(s,definitions,q,1)
    assert s.freight.delivery_statistics.rate(facility_id=u.facility_id).total==9
    assert s.freight.delivery_statistics.rate(facility_id=second.facility_id).total==11
    sell_machines(s,definitions,('truck-0',))
    assert s.freight.delivery_statistics.rate(facility_id=second.facility_id).total==11


@pytest.mark.parametrize('point',['before','after','paused','expired'])
def test_sqlite_reload_exactly_once(definitions,tmp_path,point):
    s,u=company(definitions);q=depart(s,definitions,quantity=17)
    if point in {'after','expired'}:complete(s,definitions,q)
    if point=='expired':s.freight.delivery_statistics.advance(600)
    if point=='paused':u.paused=True
    store=SQLiteSaveStore(tmp_path/'save.sqlite');store.initialize()
    for _ in range(3):
        store.save('test',s);loaded=store.load('test')
        assert serialize_game_state(loaded)==serialize_game_state(s)
        s=loaded
    if point in {'before','paused'}:
        s.freight.facilities['origin'].paused=True
        SimulationEngine(definitions).advance_time(s,60)
    assert s.freight.delivery_statistics.rate(card_id='truck-0').total==(0 if point=='expired' else 17)
    expected=s.freight.delivery_statistics.snapshot()
    for _ in range(3):store.save('test',s);s=store.load('test')
    assert s.freight.delivery_statistics.snapshot()==expected


def test_schema6_active_shipment_preserved_and_counted_once(definitions,tmp_path):
    s,u=company(definitions);q=depart(s,definitions,quantity=19)
    old=serialize_game_state(s);old['state_schema_version']=6;old['freight'].pop('delivery_statistics')
    for ship in old['freight']['outbound_shipments'].values():
        ship.pop('source_facility_id');ship.pop('economic_processed')
    loaded=deserialize_game_state(old);new=serialize_game_state(loaded)
    assert new['state_schema_version']==9 and loaded.freight.delivery_statistics.seconds==0
    assert new['cards']==old['cards'] and new['halls']==old['halls'] and new['freight']['facilities']==old['freight']['facilities']
    ship=new['freight']['outbound_shipments'][q.shipment_id];assert ship.pop('source_facility_id')=='origin';assert ship.pop('economic_processed') is False
    assert ship==old['freight']['outbound_shipments'][q.shipment_id]
    loaded.freight.facilities['origin'].paused=True
    SimulationEngine(definitions).advance_time(loaded,60)
    assert loaded.freight.delivery_statistics.rate(facility_id='origin').total==19
    store=SQLiteSaveStore(tmp_path/'legacy.sqlite');store.initialize();store.save_payload('v6',json.dumps(old))
    store.load('v6');assert (tmp_path/'legacy.pre-industriova-v7.sqlite').exists()


def test_deleted_facility_id_is_not_reused_during_retention(definitions):
    s,u=company(definitions);s.freight.facilities.clear()
    s.freight.delivery_statistics.record('sold','garage-1',sell=12)
    unit=build_freight_facility(s.freight,'garage_depot');assert unit.facility_id!='garage-1'
    assert s.freight.delivery_statistics.rate(facility_id=unit.facility_id).total==0


def test_large_jump_keeps_true_arrival_time(definitions):
    s,u=company(definitions);depart(s,definitions,quantity=40);u.paused=True
    SimulationEngine(definitions).advance_time(s,1000)
    assert s.freight.delivery_statistics.rate(card_id='truck-0').total==0
    assert not s.freight.delivery_statistics.buckets


def test_bounded_aggregates_and_cache_roundtrip():
    stats=FreightDeliveryStatistics()
    for second in range(2000):
        stats.advance(1)
        for _ in range(20):stats.record('same-card','same-facility',sell=0.01)
    assert len(stats.buckets)==600 and len(stats._vehicles)==1 and len(stats._facilities)==1
    assert sum(len(b) for b in stats.buckets.values())==600
    assert stats.rate(card_id='same-card').total==pytest.approx(12)
    assert FreightDeliveryStatistics.from_snapshot(stats.snapshot()).rate(card_id='same-card').total==pytest.approx(stats.rate(card_id='same-card').total)
    stats.advance(600);assert not stats._vehicles and not stats.buckets


@pytest.mark.parametrize('invalid',[-1,float('inf'),float('nan')])
def test_invalid_time_does_not_mutate(invalid):
    stats=FreightDeliveryStatistics();before=stats.snapshot()
    with pytest.raises(ValueError):stats.advance(invalid)
    assert stats.snapshot()==before


def test_tiny_remaining_amount_is_not_erased_by_expiry():
    stats=FreightDeliveryStatistics();stats.record('c','f',sell=1e-10);stats.advance(1);stats.record('c','f',sell=1e-12)
    stats.advance(59);assert stats.rate(card_id='c').sell==pytest.approx(1e-12,abs=1e-20)


def test_snapshot_is_detached_and_save_failure_keeps_previous_delivery(definitions,tmp_path,monkeypatch):
    from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot
    s,u=company(definitions);q=depart(s,definitions,quantity=8);complete(s,definitions,q)
    frozen=snapshot_game_state(s);payload=json.loads(encode_snapshot(frozen))
    s.freight.delivery_statistics.record('truck-0','origin',sell=12)
    assert payload['freight']['delivery_statistics']!=s.freight.delivery_statistics.snapshot()
    store=SQLiteSaveStore(tmp_path/'failed-write.sqlite');store.initialize();store.save_payload('slot',json.dumps(payload))
    def fail(*a):raise OSError('simulated write failure')
    with monkeypatch.context() as m:
        m.setattr(store,'save_snapshot',fail)
        with pytest.raises(OSError):store.save('slot',s)
    restored=store.load('slot');assert restored.freight.delivery_statistics.rate(card_id='truck-0').total==8


@pytest.mark.parametrize('origin',['missing','ambiguous'])
def test_legacy_unknown_origin_never_guesses_facility(definitions,origin):
    s,u=company(definitions);q=depart(s,definitions,quantity=8)
    if origin=='missing':u.slots[0].card_id=None
    else:u.slots[1].card_id='truck-0'
    old=serialize_game_state(s);old['state_schema_version']=6;old['freight'].pop('delivery_statistics')
    old['freight']['outbound_shipments'][q.shipment_id].pop('source_facility_id')
    loaded=deserialize_game_state(old);ship=loaded.freight.outbound_shipments[q.shipment_id]
    assert ship.source_facility_id is None
    complete(loaded,definitions,ship)
    assert loaded.freight.delivery_statistics.rate(card_id='truck-0').total==8
    assert loaded.freight.delivery_statistics.rate(facility_id='origin').total==0


def test_dispatch_upgrade_and_pause_are_not_deliveries(definitions):
    from production_zero.core.commands import UpgradeMachines
    s,u=company(definitions);stats=s.freight.delivery_statistics;stats.advance(60)
    q=depart(s,definitions,quantity=40);UpgradeMachines(('truck-0',),definitions).apply(s)
    u.paused=True
    SimulationEngine(definitions).advance_time(s,30)
    assert q.active and stats.rate(card_id='truck-0').total==0
    assert stats.seconds==90 and not stats.buckets


def test_simultaneous_completions_conserve_facility_sum(definitions):
    s,u=company(definitions)
    for i in range(3):depart(s,definitions,quantity=(i+1)*5,cid=f'truck-{i}')
    u.paused=True;engine=SimulationEngine(definitions);engine.advance_time(s,60)
    stats=s.freight.delivery_statistics
    assert stats.rate(facility_id='origin').total==30
    assert sum(stats.rate(card_id=f'truck-{i}').total for i in range(3))==30
    engine.advance_time(s,0);assert stats.rate(facility_id='origin').total==30


def test_expired_contract_uses_existing_real_engine_fallback(definitions):
    s,u=company(definitions);_set_active_contract(s,'daily','expired','iron_ore',40)
    active=s.contracts.active['daily'];active.offer=replace(active.offer,expires_at=1)
    s.contracts.daily_period_index=-1  # Existing engine expires daily contracts at UTC period rollover.
    depart(s,definitions,'contract',40,'expired');u.paused=True
    SimulationEngine(definitions,utc_now=lambda:datetime(2026,10,22,tzinfo=timezone.utc)).advance_time(s,60)
    r=s.freight.delivery_statistics.rate(facility_id='origin')
    assert r.sell==40 and r.contract==0


def test_sold_facility_measurements_survive_until_expiry(definitions):
    from production_zero.core.infrastructure import sell_freight_building
    s,u=company(definitions);build_freight_facility(s.freight,'garage_depot')
    q=depart(s,definitions,quantity=9);complete(s,definitions,q)
    sell_freight_building(s,'origin',definitions,include_machines=True)
    assert 'origin' not in s.freight.facilities
    assert s.freight.delivery_statistics.rate(facility_id='origin').total==9
    loaded=deserialize_game_state(serialize_game_state(s))
    assert loaded.freight.delivery_statistics.rate(facility_id='origin').total==9
    loaded.freight.delivery_statistics.advance(600)
    assert 'origin' not in loaded.freight.delivery_statistics.retained_facility_ids()
