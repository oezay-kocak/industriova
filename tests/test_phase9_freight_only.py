"""P9: the economic arrival boundary is the only productive contribution path."""
from dataclasses import asdict,replace
from copy import copy
import pytest
from test_phase8_contract_balance import company,group,start,D,GOODS
from production_zero.core.commands import CommandBus,AssignFreightVehicles,ContributeToConsortiumContract
from production_zero.core.consortium import ConsortiumService,ConsortiumContract,ConsortiumPersonalReward
from production_zero.core.simulation import SimulationEngine
from production_zero.core.modifiers import market_sale_price
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state

def scenario(required=100.,version=0):
    s,api,guild,clock=group(2)
    c=ConsortiumContract('p9-frozen','daily','active',1000,100000,{'iron_ore':required},ConsortiumPersonalReward(123,50),25,started_at=1000,eligible_member_ids=(api.current_company_id,'member-1'),member_count_at_start=2)
    guild.contracts['daily']=c
    # Production pauses do not prevent transport of stock already owned.
    for cid,card in tuple(s.cards.items()):
        if not cid.startswith('truck'):s.cards[cid]=replace(card,paused=True)
    s.ensure_resource('iron_ore').amount=40
    return s,api,guild,c,clock

def dispatch(s,clock,qty=40,cid='truck0'):
    s.ensure_resource('iron_ore').amount=qty
    CommandBus(s).dispatch(AssignFreightVehicles((cid,),'iron_ore','consortium',D))
    engine=SimulationEngine(D,utc_now=lambda:clock[0]);engine.advance_time(s,0)
    return engine,next(q for q in s.freight.outbound_shipments.values() if q.freight_card_id==cid)

@pytest.mark.parametrize('path',['service','command','old_callback','fake_grant','boolean_grant','payload_grant'])
@pytest.mark.parametrize('legacy',[True,False])
def test_direct_actions_are_rejected_without_any_mutation(path,legacy):
    s,api,guild,c,clock=scenario()
    if not legacy:c.balance_version=1
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):
        if path=='service':api.contribute(guild.consortium_id,api.current_company_id,'daily','iron_ore',1,request_id='forged',company_state=s)
        elif path=='command':CommandBus(s).dispatch(ContributeToConsortiumContract(guild.consortium_id,api.current_company_id,'daily','iron_ore',1))
        elif path=='old_callback':api.receive_freight_delivery(guild.consortium_id,'daily',c.contract_id,'iron_ore',1,'forged')
        else:api._accept_freight_arrival({'fake_grant':object(),'boolean_grant':True,'payload_grant':{'is_freight':True}}[path])
    assert serialize_game_state(s)==before

def test_departure_reserves_goods_arrival_credits_once_and_route_change_preserves_snapshot():
    s,api,guild,c,clock=scenario();engine,q=dispatch(s,clock)
    frozen=asdict(q)
    assert s.resources['iron_ore'].amount==0 and c.delivered=={}
    CommandBus(s).dispatch(AssignFreightVehicles(('truck0',),'coal','market',D))
    assert asdict(q)==frozen
    engine.advance_time(s,q.remaining_seconds/2)
    assert c.delivered=={}
    engine.advance_time(s,q.remaining_seconds)
    assert c.delivered=={'iron_ore':40} and s.resources['iron_ore'].amount==0
    cash=s.cash.amount;xp=s.company.current_xp
    engine._complete_outbound_shipments(s,(q,q))
    assert c.delivered=={'iron_ore':40} and (s.cash.amount,s.company.current_xp)==(cash,xp)
    assert s.freight.delivery_statistics.rate(card_id='truck0').consortium>0

@pytest.mark.parametrize('invalid',['left','expired','completed','renewed','disbanded'])
def test_inflight_invalid_target_becomes_sell_only(invalid):
    s,api,guild,c,clock=scenario();engine,q=dispatch(s,clock)
    if invalid=='left':
        api.transfer_leadership(guild.consortium_id,api.current_company_id,'member-1');api.leave(guild.consortium_id,api.current_company_id)
    elif invalid=='expired':clock[0]=c.expires_at
    elif invalid=='completed':c.status='completed'
    elif invalid=='renewed':guild.contracts['daily']=replace(c,contract_id='replacement',delivered={},contributions={})
    else:api.disband(guild.consortium_id,api.current_company_id)
    before=s.cash.amount
    engine.advance_time(s,q.remaining_seconds)
    assert not c.delivered and s.resources['iron_ore'].amount==0
    assert s.cash.amount==pytest.approx(before+40*market_sale_price(s,'iron_ore'))
    r=s.freight.delivery_statistics.rate(card_id='truck0')
    assert r.consortium==0 and r.sell==r.total>0

def test_partial_acceptance_and_fallback_sum_exactly_to_cargo():
    from consortium_freight_fixture import freight_contribute
    from contract_capacity_fixture import remote_stock
    s,api,guild,c,clock=scenario();engine,q=dispatch(s,clock)
    freight_contribute(api,guild.consortium_id,'member-1','daily','iron_ore',94,company_state=remote_stock('member-1','iron_ore',94))
    before=s.cash.amount;engine.advance_time(s,q.remaining_seconds)
    assert c.delivered=={'iron_ore':100} and c.contributions[api.current_company_id]=={'iron_ore':6}
    r=s.freight.delivery_statistics.rate(card_id='truck0')
    assert r.consortium/r.total==pytest.approx(6/40)
    assert r.sell/r.total==pytest.approx(34/40)
    assert r.total==pytest.approx(r.sell+r.consortium+r.contract)
    assert s.cash.amount==pytest.approx(before+34*market_sale_price(s,'iron_ore')+123)
    assert s.resources['iron_ore'].amount==0

@pytest.mark.parametrize('stage',['before','after'])
def test_save_load_preserves_cargo_snapshot_contributions_and_receipts(stage):
    s,api,guild,c,clock=scenario(40);engine,q=dispatch(s,clock)
    if stage=='after':engine.advance_time(s,q.remaining_seconds)
    before=serialize_game_state(s);loaded=deserialize_game_state(before)
    assert serialize_game_state(loaded)==before
    restored=loaded.consortium.consortiums[guild.consortium_id].contracts['daily']
    if stage=='before':
        assert asdict(next(iter(loaded.freight.outbound_shipments.values())))==asdict(q)
        SimulationEngine(D,utc_now=lambda:clock[0]).advance_time(loaded,q.remaining_seconds)
    assert restored.delivered=={'iron_ore':40} and restored.status=='completed'
    cash=loaded.cash.amount;receipts=copy(loaded.consortium.reward_receipts)
    SimulationEngine(D,utc_now=lambda:clock[0]).advance_time(loaded,60)
    assert loaded.cash.amount==cash and loaded.consortium.reward_receipts==receipts

def test_two_separate_companies_with_same_shipment_id_each_count_once():
    s,api,guild,c,clock=scenario(100)
    remote=company();remote.consortium=copy(s.consortium);remote.consortium.current_company_id='member-1'
    for cid,card in tuple(remote.cards.items()):
        if not cid.startswith('truck'):remote.cards[cid]=replace(card,paused=True)
    e1,q1=dispatch(s,clock);e2,q2=dispatch(remote,clock)
    assert q1.shipment_id==q2.shipment_id
    e1.advance_time(s,q1.remaining_seconds);e2.advance_time(remote,q2.remaining_seconds)
    assert c.delivered=={'iron_ore':80}
    assert c.contributions[api.current_company_id]['iron_ore']==40
    assert c.contributions['member-1']['iron_ore']==40
    e1._complete_outbound_shipments(s,(q1,));e2._complete_outbound_shipments(remote,(q2,))
    assert c.delivered=={'iron_ore':80}

@pytest.mark.parametrize('kind',['daily','weekly'])
def test_no_vehicles_has_no_quote_and_never_falls_back_to_direct_storage(kind):
    s=company(trucks=0);api=ConsortiumService(s,D,clock=lambda:1000);guild=api.create('No vehicles group')
    assert not api.contract_candidates(guild.consortium_id,kind)
    before=serialize_game_state(s)
    with pytest.raises(ValueError):api.start_contract(guild.consortium_id,api.current_company_id,kind,GOODS[:3 if kind=='daily' else 4])
    assert serialize_game_state(s)==before
    assert not s.installed_freight_card_ids()

@pytest.mark.parametrize('operation',['pause_card','pause_facility','pause_line','reroute','empty_stock'])
def test_operational_changes_do_not_shrink_quotes(operation):
    s,api,guild,clock=group(2)
    api.contract_candidates(guild.consortium_id,'daily')
    before=asdict(guild.contracts['daily'])
    if operation=='pause_card':
        for cid,card in tuple(s.cards.items()):s.cards[cid]=replace(card,paused=True)
    elif operation=='pause_facility':s.freight.facilities['garage'].paused=True
    elif operation=='pause_line':s.freight.facilities['garage'].paused_lines.add(0)
    elif operation=='reroute':CommandBus(s).dispatch(AssignFreightVehicles(('truck0',),'iron_ore','market',D))
    else:
        for stock in s.resources.values():stock.amount=0
    api.contract_candidates(guild.consortium_id,'daily')
    assert asdict(guild.contracts['daily'])==before

def test_old_remote_production_only_evidence_is_not_transport_proof():
    s,api,guild,clock=group(2)
    guild.members['member-1'].capacity_signature='old-p8-production'
    guild.members['member-1'].capacity_rates={'iron_ore':1e12}
    api.contract_candidates(guild.consortium_id,'daily')
    assert guild.contracts['daily'].capacity_rates['iron_ore']==pytest.approx(120)

@pytest.mark.parametrize('kind',['daily','weekly'])
def test_transport_upgrade_requotes_available_but_keeps_active_reward_and_rp(kind):
    s,api,guild,clock=group(2,remote_mk=10)
    active=start(api,guild,kind);frozen=asdict(active)
    for cid,card in tuple(s.cards.items()):
        if cid.startswith('truck'):s.cards[cid]=replace(card,mk_level=99,output_bonus_percent=25)
    api.contract_candidates(guild.consortium_id,'weekly' if kind=='daily' else 'daily')
    assert asdict(active)==frozen

def test_unfinished_freight_cannot_be_settled_early():
    s,api,guild,c,clock=scenario();engine,q=dispatch(s,clock)
    before=serialize_game_state(s)
    engine._complete_outbound_shipments(s,(q,))
    assert serialize_game_state(s)==before

@pytest.mark.parametrize('transition',['active','completed','rotated','left','loaded'])
def test_retained_receipt_replay_cannot_become_a_second_sale(transition):
    s,api,guild,c,clock=scenario(40 if transition!='active' else 100)
    engine,q=dispatch(s,clock);engine.advance_time(s,q.remaining_seconds)
    replay=replace(q,economic_processed=False)
    if transition=='rotated':api.renew_contract_offer(guild.consortium_id,api.current_company_id,'daily')
    if transition=='left':
        api.transfer_leadership(guild.consortium_id,api.current_company_id,'member-1');api.leave(guild.consortium_id,api.current_company_id)
    if transition=='loaded':s=deserialize_game_state(serialize_game_state(s))
    before=serialize_game_state(s)
    engine._complete_outbound_shipments(s,(replay,))
    assert replay.economic_processed and serialize_game_state(s)==before
