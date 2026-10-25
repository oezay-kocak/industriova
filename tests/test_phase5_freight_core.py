"""P5 route confirmation and throughput with the existing economics/snapshots."""
from dataclasses import replace
from copy import deepcopy
from types import SimpleNamespace
import pytest
from test_phase4_slot_permutations import definitions, fixture
from test_freight import _set_active_contract
from production_zero.core.commands import AssignFreightVehicles, CommandBus, UpgradeMachines
from production_zero.core.freight import FreightCardStats, freight_stats, OutboundFreightShipment
from production_zero.core.freight_routes import target_problem
from production_zero.core.machine_operations import installed_slot_snapshot
from production_zero.core.enums import Rarity
from production_zero.core.cards import create_card_instance
from production_zero.core.research import ResearchState, research_catalog
from production_zero.ui.freight_view import theoretical_throughput_text
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state


def route_fixture(defs):
    s, u = fixture(defs, 'freight', 3)
    s.ensure_resource('steel').amount = 100
    s.cash.amount = 1e12
    return s, u


@pytest.mark.parametrize('case', ['missing-card','removed','moved','duplicate-id','duplicate-placement',
                                 'locked','wrong-family','unowned','no-cargo','unknown-resource',
                                 'event','missing-contract','expired-contract','wrong-product','reserved','no-membership'])
def test_route_rejections_are_atomic(definitions, case):
    s, u = route_fixture(definitions)
    ids, rid, dest = ('c0','c1'), 'steel', 'market'
    origins = installed_slot_snapshot(s, ids)
    if case == 'missing-card': del s.cards['c1']
    if case == 'removed': u.slots[1].card_id = None
    if case == 'moved': u.slots[1].card_id, u.slots[2].card_id = u.slots[2].card_id, u.slots[1].card_id
    if case == 'duplicate-id': ids = ('c0','c0')
    if case == 'duplicate-placement': u.slots[2].card_id = 'c1'
    if case == 'locked': u.slot_count = 1
    if case == 'wrong-family': s.cards['c1'] = replace(s.cards['c1'], definition_id='freight.ship')
    if case == 'unowned': s.cards['c1'] = replace(s.cards['c1'], card_id='other')
    if case == 'no-cargo': s.resources[rid].amount = 0
    if case == 'unknown-resource': rid = 'unknown'
    if case == 'event': dest = 'event'
    if case in {'missing-contract','expired-contract','wrong-product','reserved'}:
        dest = 'contract'
        if case != 'missing-contract':
            _set_active_contract(s,'daily','selected','copper' if case=='wrong-product' else rid,20)
        if case == 'expired-contract':
            active=s.contracts.active['daily']; active.offer=replace(active.offer,expires_at=1)
        if case == 'reserved':
            s.freight.outbound_shipments['s']=OutboundFreightShipment('s','contract',target_id='selected',resource_id=rid,quantity=20,freight_card_id='c2')
    if case == 'no-membership': dest = 'consortium'
    bus=CommandBus(s); before=serialize_game_state(s)
    with pytest.raises(ValueError):
        bus.dispatch(AssignFreightVehicles(ids,rid,dest,definitions,origins,True))
    assert serialize_game_state(s)==before and not bus.history


@pytest.mark.parametrize('destination', ['market','contract','consortium'])
def test_explicit_target_group_busy_snapshot_and_roundtrip(definitions, destination):
    s,u=route_fixture(definitions)
    if destination=='contract': _set_active_contract(s,'daily','manual','steel',500)
    if destination=='consortium':
        from production_zero.core.consortium import ConsortiumService, ConsortiumContract, ConsortiumPersonalReward
        consortium=ConsortiumService(s,definitions).create('P5 Test Team')
        consortium.contracts['weekly']=ConsortiumContract('manual','weekly','active',0,1e20,{'steel':500},ConsortiumPersonalReward(0,0,0),0)
    shipment=OutboundFreightShipment('busy','market',resource_id='iron_ore',quantity=8,freight_card_id='c0',transport_capacity=12,transport_time_seconds=60,remaining_seconds=24)
    s.freight.outbound_shipments['busy']=shipment
    snapshot=deepcopy(shipment)
    bus=CommandBus(s)
    bus.dispatch(AssignFreightVehicles(('c0','c1'),'steel',destination,definitions,installed_slot_snapshot(s,('c0','c1')),True))
    assert len(bus.history)==1 and s.freight.assignments['c0'].destination_kind==destination
    assert s.freight.assignments['c1'].resource_id=='steel'
    bus.dispatch(UpgradeMachines(('c0',),definitions))
    assert shipment==snapshot and s.cards['c0'].mk_level==51
    payload=serialize_game_state(s); loaded=deserialize_game_state(payload)
    assert loaded.freight.assignments==s.freight.assignments
    assert loaded.freight.outbound_shipments==s.freight.outbound_shipments
    assert loaded.cards['c0']==s.cards['c0']


@pytest.mark.parametrize('did',['freight.truck','freight.train','freight.aircraft','freight.ship'])
@pytest.mark.parametrize('mk,rarity,research',[(1,Rarity.COMMON,False),(2,Rarity.RARE,False),(10,Rarity.EPIC,True),(99,Rarity.LEGENDARY,True)])
@pytest.mark.parametrize('paused',[False,True])
def test_theoretical_formula_uses_effective_engine_stats(definitions,did,mk,rarity,research,paused):
    card=replace(create_card_instance('v',did,definitions[did].card_kind,rarity),mk_level=mk,paused=paused)
    r=ResearchState()
    if research:
        _,nodes=research_catalog()
        r.unlocked_node_ids.update(n.id for n in nodes.values() if n.effect_type=='freight_capacity')
    stats=freight_stats(card,definitions[did],r)
    expected=60*stats.capacity/stats.transport_time_seconds
    shown=float(theoretical_throughput_text(stats).split()[0].replace(',',''))
    assert shown==pytest.approx(expected,abs=.0051)
    assert shown>0


@pytest.mark.parametrize('capacity,seconds',[(1,0),(1,-1),(1,float('nan')),(float('inf'),1),(0,1),(-1,1),(1,float('inf')),(1e308,1e-308)])
def test_neutral_invalid_throughput(capacity,seconds):
    assert theoretical_throughput_text(FreightCardStats(capacity,seconds))=='Unavailable'


@pytest.mark.parametrize('capacity,seconds',[(1e20,5),(1e-5,100),(1e6,.1)])
def test_large_and_small_throughput(capacity,seconds):
    text=theoretical_throughput_text(FreightCardStats(capacity,seconds))
    assert text.endswith(' units/min')
    assert float(text.split()[0].replace(',',''))==pytest.approx(60*capacity/seconds,rel=.001)


@pytest.mark.parametrize('case',['expired','wrong-product','reserved','left','member-can-deliver'])
def test_consortium_current_membership_and_contract_needs(definitions,case):
    from production_zero.core.consortium import ConsortiumService, ConsortiumContract, ConsortiumPersonalReward
    s,u=route_fixture(definitions)
    team=ConsortiumService(s,definitions).create('P5 Contract Team')
    c=ConsortiumContract('manual','weekly','active',0,1e20,{'steel':500},ConsortiumPersonalReward(),0)
    team.contracts['weekly']=c
    if case=='expired':c.expires_at=1
    if case=='wrong-product':c.requirements={'copper':500}
    if case=='reserved':
        s.freight.outbound_shipments['pending']=OutboundFreightShipment('pending','consortium',target_id=f'{team.consortium_id}|weekly|manual',resource_id='steel',quantity=500)
    if case=='left':team.members.clear()
    if case=='member-can-deliver':team.members[s.consortium.current_company_id].role='member'
    before=serialize_game_state(s)
    command=AssignFreightVehicles(('c0','c1'),'steel','consortium',definitions,installed_slot_snapshot(s,('c0','c1')),True)
    if case=='member-can-deliver':
        command.apply(s)
        assert s.freight.assignments['c0'].destination_kind=='consortium'
    else:
        with pytest.raises(ValueError):command.apply(s)
        assert serialize_game_state(s)==before
