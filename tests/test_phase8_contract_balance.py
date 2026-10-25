from consortium_freight_fixture import freight_contribute, freight_receive
"""P8 economic boundaries: real capacity, immutable terms, cooperative fairness."""
from dataclasses import replace, asdict
from pathlib import Path
import math
import pytest
from tests.contract_capacity_fixture import remote_stock

from production_zero.data.definitions import load_card_definitions
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import GameState, FactoryHall, MachineProductionState
from production_zero.core.freight import FreightFacility, OutboundFreightShipment
from production_zero.core.contract_capacity import reachable_capacity, capacity_signature, requirements_for_rates
from production_zero.core.contracts import (initialize_contracts, refresh_contracts, accept_contract,
    contract_requirements_for_products, contract_reward_quote, receive_contract_delivery, ActiveContract, ContractOffer)
from production_zero.core.consortium import ConsortiumService, ConsortiumMember, ConsortiumContract, ConsortiumPersonalReward
from production_zero.core.modifiers import contract_cash_quote
from production_zero.core.progression import initialize_production_progress
from production_zero.core.simulation import SimulationEngine
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore

D = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
GOODS = ('iron_ore','coal','copper_ore','bauxite')


def company(*, mk=1, resources=GOODS, trucks=3, solar=2):
    state=GameState(8808,warehouse_capacity=75280)
    state.company.level=25
    state.freight.facilities.clear()
    initialize_production_progress(state,D)
    hall=FactoryHall('mine','Mine',len(resources),board_kind='resources',specialization='machine.extractor',max_lines=1,max_slots_per_line=len(resources),start_unlocked_lines=1,start_slots_per_line=len(resources))
    state.resource_sites[hall.hall_id]=hall
    for i,rid in enumerate(resources):
        cid='raw'+str(i)
        state.cards[cid]=replace(create_card_instance(cid,'machine.extractor',D['machine.extractor'].card_kind,Rarity.COMMON),mk_level=mk)
        hall.slots[i].card_id=cid
        state.machine_production[cid]=MachineProductionState(cid,rid,'resource.'+rid)
        state.ensure_resource(rid).amount=.001
    if solar:
        plant=FactoryHall('solar','Solar',solar,board_kind='energy',max_lines=1,max_slots_per_line=solar,start_unlocked_lines=1,start_slots_per_line=solar)
        state.energy_plants['solar']=plant
        for i in range(solar):
            cid='solar'+str(i)
            state.cards[cid]=replace(create_card_instance(cid,'energy.solar_array',D['energy.solar_array'].card_kind,Rarity.COMMON),mk_level=mk)
            plant.slots[i].card_id=cid
    if trucks:
        facility=FreightFacility('garage','Garage',slot_count=trucks)
        state.freight.facilities['garage']=facility
        for i in range(trucks):
            cid='truck'+str(i)
            state.cards[cid]=replace(create_card_instance(cid,'freight.truck',D['freight.truck'].card_kind,Rarity.COMMON),mk_level=mk)
            facility.slots[i].card_id=cid
    return state


def accepted(state, kind):
    initialize_contracts(state,D)
    offer=state.contracts.offers[kind][0]
    selected=GOODS[:{'regular':2,'daily':3,'weekly':4}[kind]]
    requirements=contract_requirements_for_products(state,offer,D,selected)
    quote=contract_reward_quote(state,offer,D,requirements)
    accept_contract(state,kind,offer.contract_id,D,selected_resource_ids=selected)
    return state.contracts.active[kind],quote


@pytest.mark.parametrize('kind,bonus,rp',[('regular',0.,0),('daily',.2,1),('weekly',.4,3)])
@pytest.mark.parametrize('research',[False,True])
def test_cash_preview_accept_completion_snapshot(kind,bonus,rp,research):
    s=company()
    if research:s.research.unlocked_node_ids.update({'company.general.s1.major','company.contracts.s1.major','industry.metals.s1.major'})
    active,quote=accepted(s,kind)
    required=dict(active.offer.requirements)
    assert active.offer.reward_cash==round(contract_cash_quote(s,required)*(1+bonus),2)
    assert (active.offer.reward_cash,active.offer.reward_xp)==quote
    assert active.offer.reward_rp==rp
    frozen=asdict(active.offer)
    s.research.unlocked_node_ids.clear();s.company.level=200
    s=deserialize_game_state(serialize_game_state(s))
    active=s.contracts.active[kind]
    assert asdict(active.offer)==frozen
    before=s.cash.amount
    for rid,qty in required.items():receive_contract_delivery(s,active.offer.contract_id,rid,qty,D)
    assert s.cash.amount==pytest.approx(before+quote[0])
    assert s.research.total_earned==rp
    assert s.company_xp_progress.xp_by_source[kind+'_contracts']==quote[1]
    for rid,qty in required.items():receive_contract_delivery(s,active.offer.contract_id,rid,qty,D)
    assert s.cash.amount==pytest.approx(before+quote[0])
    assert not s.packs.unopened


@pytest.mark.parametrize('mk',[1,2,10,50,99])
def test_reachable_capacity_respects_actual_freight_and_mk(mk):
    s=company(mk=mk)
    plan=reachable_capacity(s,D)
    assert plan.freight_per_minute==pytest.approx(120*(1+.25*(mk-1)))
    assert all(rate<=plan.freight_per_minute for rate in plan.rates.values())
    q=requirements_for_rates(plan.rates,{rid:1. for rid in GOODS},GOODS,240)
    assert sum(q[rid]/plan.rates[rid] for rid in GOODS)<=240+1


@pytest.mark.parametrize('problem',['power','freight','warehouse','locked'])
def test_structurally_missing_capacity_cannot_generate_demand(problem):
    s=company(solar=0 if problem=='power' else 2,trucks=0 if problem=='freight' else 3)
    if problem=='warehouse':s.warehouse_capacity=.1
    if problem=='locked':s.production_progress.unlocked_production_ids.clear()
    plan=reachable_capacity(s,D)
    assert not plan.rates
    initialize_contracts(s,D)
    with pytest.raises(ValueError):contract_requirements_for_products(s,s.contracts.offers['daily'][0],D,GOODS[:3])


def test_pause_stock_route_and_progress_cannot_shrink_or_reroll_offer():
    s=company();initialize_contracts(s,D)
    before=serialize_game_state(s)['contracts']['offers']
    signature=capacity_signature(s)
    for cid,card in tuple(s.cards.items()):s.cards[cid]=replace(card,paused=True)
    for unit in s.all_production_units():unit.paused=True
    for stock in s.resources.values():stock.amount=0
    for p in s.machine_production.values():p.progress_seconds=17
    s.freight.assignments.clear()
    refresh_contracts(s,D)
    assert capacity_signature(s)==signature
    assert serialize_game_state(s)['contracts']['offers']==before


def test_capacity_cache_reuses_and_invalidates_only_real_inputs(monkeypatch):
    from production_zero.core import contract_capacity
    s=company();initialize_contracts(s,D)
    calls=[];old=contract_capacity.reachable_capacity
    monkeypatch.setattr(contract_capacity,'reachable_capacity',lambda *args:(calls.append(1),old(*args))[1])
    for _ in range(15):refresh_contracts(s,D)
    assert calls==[]
    old_id=s.contracts.offers['daily'][0].contract_id
    s.cards['truck0']=replace(s.cards['truck0'],mk_level=2)
    refresh_contracts(s,D)
    assert calls==[1] and s.contracts.offers['daily'][0].contract_id!=old_id
    with pytest.raises(ValueError,match='Unknown contract'):accept_contract(s,'daily',old_id,D,selected_resource_ids=GOODS[:3])


def test_upstream_unlock_and_installed_capability_required_even_with_stock():
    s=company();s.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    s.ensure_resource('iron').amount=100000
    assert 'iron' not in reachable_capacity(s,D).rates


def test_no_intermediate_double_count_in_shared_time_budget():
    s=company()
    from tests.contract_capacity_fixture import provide_capacity
    provide_capacity(s,D)
    s.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    plan=reachable_capacity(s,D)
    prices={'iron_ore':1.,'iron':3.75}
    req=requirements_for_rates(plan.rates,prices,tuple(prices),60)
    assert sum(req[r]/plan.rates[r] for r in req)<=60.1
    assert plan.production_rates['iron']<=60*1.001


@pytest.mark.parametrize('kind',['regular','daily','weekly'])
def test_schema8_active_terms_survive_verbatim(kind):
    s=company()
    initialize_contracts(s,D)
    s.contracts.active[kind]=ActiveContract(ContractOffer('old-'+kind,kind,'Old',{GOODS[0]:5},123.45,67.89,0),{GOODS[0]:2})
    payload=serialize_game_state(s);payload['state_schema_version']=8
    for k in ('balance_version','capacity_rates','unit_prices','unit_cash','target_minutes','quoted_level','reward_rp','capacity_signature'):
        payload['contracts']['active'][kind]['offer'].pop(k)
    loaded=deserialize_game_state(payload);refresh_contracts(loaded,D)
    assert loaded.contracts.active[kind].offer.reward_cash==123.45
    assert loaded.contracts.active[kind].offer.reward_xp==67.89
    assert loaded.contracts.active[kind].delivered=={GOODS[0]:2}
    receive_contract_delivery(loaded,'old-'+kind,GOODS[0],3,D)
    assert loaded.cash.amount==123.45


@pytest.mark.parametrize('amount',[float('nan'),float('inf'),-1.,0.])
def test_invalid_delivery_is_rejected_without_progress(amount):
    s=company();active,_=accepted(s,'daily')
    before=serialize_game_state(s)
    with pytest.raises(ValueError):receive_contract_delivery(s,active.offer.contract_id,GOODS[0],amount,D)
    assert serialize_game_state(s)==before


def group(count=1, *, remote_mk=1, unknown=False, no_freight=False):
    s=company();clock=[1000.]
    api=ConsortiumService(s,D,clock=lambda:clock[0])
    guild=api.create('Capacity Cooperative')
    if count>10:
        from production_zero.core.consortium import MEMBER_CAPACITY_MILESTONES,consortium_xp_floor,member_capacity_for_level
        guild.level=next(level for level,capacity in MEMBER_CAPACITY_MILESTONES if capacity>=count)
        guild.consortium_xp=consortium_xp_floor(guild.level)
        guild.member_capacity=member_capacity_for_level(guild.level)
    for i in range(1,count):
        cid='member-'+str(i)
        guild.members[cid]=ConsortiumMember(cid,cid,25)
        if not unknown:
            remote=company(mk=remote_mk,trucks=0 if no_freight else 3)
            remote.consortium.current_company_id=cid
            api.update_capacity_snapshot(cid,remote)
    return s,api,guild,clock


def start(api,guild,kind='daily'):
    selected=GOODS[:3 if kind=='daily' else 4]
    q=api.preview_contract(guild.consortium_id,kind,selected)
    rewards=api.preview_contract_rewards(guild.consortium_id,kind)
    result=api.start_contract(guild.consortium_id,api.current_company_id,kind,selected,expected_contract_id=guild.contracts[kind].contract_id)
    assert result.requirements==q and (result.personal_reward,result.consortium_xp_reward)==rewards
    return result


@pytest.mark.parametrize('count',[1,2,5,10,50])
def test_combined_capability_scales_with_proof_within_existing_member_limit(count):
    s,api,guild,clock=group(count)
    contract=start(api,guild)
    local=reachable_capacity(s,D)
    assert contract.capacity_rates[GOODS[0]]==pytest.approx(local.rates[GOODS[0]]*count)
    assert contract.member_count_at_start==count
    assert sum(contract.requirements[r]/contract.capacity_rates[r] for r in contract.requirements)<=120.1


@pytest.mark.parametrize('kind',['daily','weekly'])
@pytest.mark.parametrize('condition',['unknown','no_freight'])
def test_unknown_members_add_no_output_and_no_freight_members_keep_direct_storage_capability(kind,condition):
    a=group(1);b=group(10,**{condition:True})
    ca=start(a[1],a[2],kind);cb=start(b[1],b[2],kind)
    if condition=='unknown':
        assert cb.requirements==ca.requirements
        assert cb.personal_reward==ca.personal_reward
    else:
        assert cb.requirements==ca.requirements
        assert cb.capacity_rates[GOODS[0]]==pytest.approx(120)


def test_strong_member_output_and_product_specialization_are_combined_individually():
    s,api,guild,clock=group(2,remote_mk=10)
    contract=start(api,guild)
    local=reachable_capacity(s,D)
    assert contract.capacity_rates[GOODS[0]]==pytest.approx(local.rates[GOODS[0]]*(1+3.25))
    s2=company(resources=('iron_ore',))
    s2.production_progress.unlocked_production_ids={'resource.iron_ore'}
    s2.consortium.current_company_id='member-1'
    api.update_capacity_snapshot('member-1',s2)
    candidates=api.contract_candidates(guild.consortium_id,'weekly')
    assert 'steel' not in candidates


@pytest.mark.parametrize('kind',['daily','weekly'])
def test_tiny_contribution_no_longer_clones_full_reward_pool(kind):
    s,api,guild,clock=group(2)
    contract=start(api,guild,kind)
    rid=next(iter(contract.requirements))
    freight_contribute(api,guild.consortium_id,'member-1',kind,rid,1.,request_id='tiny',company_state=remote_stock('member-1',rid,1.))
    for resource,qty in contract.requirements.items():
        needed=contract.remaining(resource)
        s.ensure_resource(resource).amount=needed
        if needed:freight_contribute(api,guild.consortium_id,api.current_company_id,kind,resource,needed)
    receipts=api.network.reward_receipts[contract.contract_id]
    assert receipts['member-1'].cash<contract.personal_reward.cash*.01
    assert receipts['member-1'].research_points==0
    assert receipts[api.current_company_id].cash>contract.personal_reward.cash*.99
    assert sum(round(r.cash*100) for r in receipts.values())<=round(contract.personal_reward.cash*100)
    assert sum(r.company_xp for r in receipts.values())<=contract.personal_reward.company_xp
    before=serialize_game_state(s)
    api.complete_contract(guild.consortium_id,kind)
    assert serialize_game_state(s)==before


@pytest.mark.parametrize('action',['leave','kick','late','transfer'])
def test_membership_and_role_changes_keep_snapshot_and_existing_rights(action):
    s,api,guild,clock=group(2)
    contract=start(api,guild)
    frozen=(dict(contract.requirements),contract.personal_reward,contract.consortium_xp_reward)
    rid=next(iter(contract.requirements))
    freight_contribute(api,guild.consortium_id,'member-1','daily',rid,1,company_state=remote_stock('member-1',rid,1))
    if action=='leave':api.leave(guild.consortium_id,'member-1')
    if action=='kick':api.remove(guild.consortium_id,api.current_company_id,'member-1')
    if action=='late':api.join(guild.consortium_id,'late','Late',25)
    if action=='transfer':api.transfer_leadership(guild.consortium_id,api.current_company_id,'member-1')
    assert (contract.requirements,contract.personal_reward,contract.consortium_xp_reward)==frozen
    if action in ('leave','kick'):
        api.join(guild.consortium_id,'member-1','Return',25)
        assert not api.reward_eligibility(guild.consortium_id,'daily','member-1')['reward_eligible']
    if action=='late':assert not api.reward_eligibility(guild.consortium_id,'daily','late')['eligible_at_start']


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1.,0.])
def test_invalid_consortium_contribution_cannot_corrupt_stock_or_progress(value):
    s,api,guild,clock=group(2);contract=start(api,guild)
    before=serialize_game_state(s)
    with pytest.raises(ValueError):freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],value)
    assert serialize_game_state(s)==before


def test_expiry_also_guards_direct_completion():
    s,api,guild,clock=group();contract=start(api,guild)
    contract.delivered=dict(contract.requirements)
    clock[0]=contract.expires_at
    with pytest.raises(ValueError):api.complete_contract(guild.consortium_id,'daily')
    assert not s.cash.amount and not api.network.reward_receipts


def test_stale_offer_and_ordinary_member_start_cannot_commit():
    s,api,guild,clock=group(2)
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):api.start_contract(guild.consortium_id,'member-1','daily',GOODS[:3])
    assert serialize_game_state(s)==before
    old=guild.contracts['daily'].contract_id
    api.join(guild.consortium_id,'new','New',25)
    with pytest.raises(ValueError,match='changed'):api.start_contract(guild.consortium_id,api.current_company_id,'daily',GOODS[:3],expected_contract_id=old)
    assert guild.contracts['daily'].status=='available'


def test_old_consortium_full_reward_snapshot_remains_unchanged():
    s,api,guild,clock=group(2)
    old=ConsortiumContract('legacy','daily','active',1000,100000,{'iron_ore':2},ConsortiumPersonalReward(123,50),25,started_at=1000,eligible_member_ids=(api.current_company_id,'member-1'),member_count_at_start=2)
    guild.contracts['daily']=old
    s.ensure_resource('iron_ore').amount=1
    freight_contribute(api,guild.consortium_id,'member-1','daily','iron_ore',1,company_state=remote_stock('member-1','iron_ore',1))
    s=deserialize_game_state(serialize_game_state(s));api=ConsortiumService(s,D,clock=lambda:1001)
    freight_contribute(api,guild.consortium_id,api.current_company_id,'daily','iron_ore',1)
    assert {r.cash for r in s.consortium.reward_receipts['legacy'].values()}=={123}


@pytest.mark.parametrize('invalid',['expired','left','completed'])
def test_late_consortium_freight_becomes_sell_and_actual_counts_once(invalid):
    s,api,guild,clock=group(2);contract=start(api,guild)
    target=f'{guild.consortium_id}|daily|{contract.contract_id}'
    shipment=OutboundFreightShipment('flight','consortium',target_id=target,resource_id=GOODS[0],quantity=20,freight_card_id='truck0',source_facility_id='garage',remaining_seconds=1)
    if invalid=='expired':contract.expires_at=0
    if invalid=='completed':contract.status='completed'
    if invalid=='left':
        api.transfer_leadership(guild.consortium_id,api.current_company_id,'member-1')
        api.leave(guild.consortium_id,api.current_company_id)
    engine=SimulationEngine(D,utc_now=lambda:1001)
    s.freight.outbound_shipments[shipment.shipment_id]=shipment
    from production_zero.core.freight import advance_outbound_shipments
    completed=advance_outbound_shipments(s.freight,1)
    engine._complete_outbound_shipments(s,completed+completed)
    assert s.cash.amount==20
    stats=s.freight.delivery_statistics.snapshot()
    assert 'buckets' in stats
    assert not contract.delivered


def test_schema9_uses_separate_backup_for_schema8_and_restores_new_snapshot(tmp_path):
    s=company();active,_=accepted(s,'daily')
    db=SQLiteSaveStore(tmp_path/'company.sqlite');db.initialize();db.save('company',s)
    import sqlite3,json
    with sqlite3.connect(db._path) as con:
        raw=serialize_game_state(s);raw['state_schema_version']=8
        con.execute('UPDATE saves SET state_json=? WHERE slot=?',(json.dumps(raw),'company'))
    loaded=db.load('company')
    assert db._path.with_suffix('.pre-industriova-v9.sqlite').exists()
    assert asdict(loaded.contracts.active['daily'].offer)==asdict(active.offer)


def test_fuel_chain_has_to_bootstrap_and_cannot_export_its_reserved_fuel():
    s=company(solar=0)
    plant=FactoryHall('fuel','Coal Power',1,board_kind='energy',max_lines=1,max_slots_per_line=1,start_unlocked_lines=1,start_slots_per_line=1)
    s.energy_plants['fuel']=plant
    d=D['energy.coal_power_plant']
    s.cards['fuel']=create_card_instance('fuel',d.definition_id,d.card_kind,Rarity.COMMON)
    plant.slots[0].card_id='fuel'
    assert not reachable_capacity(s,D).rates
    before=capacity_signature(s)
    s.production_progress.lifetime_produced['coal']=120
    assert capacity_signature(s)!=before
    plan=reachable_capacity(s,D)
    assert plan.rates.get('iron_ore',0)>0
    assert plan.rates.get('coal',0)==pytest.approx(120-d.fuel_consumption_per_minute)


@pytest.mark.parametrize('kind,bonus',[('daily',.15),('weekly',.25)])
def test_consortium_cash_preserves_each_members_research_sell_value_snapshot(kind,bonus):
    from production_zero.core.research import research_catalog
    from production_zero.core.modifiers import market_sale_price
    s,api,guild,clock=group(2)
    s.research.unlocked_node_ids.update(research_catalog()[1])
    contract=start(api,guild,kind)
    quoted_prices={rid:market_sale_price(s,rid) for rid in contract.requirements}
    s.research.unlocked_node_ids.clear()
    for rid,qty in contract.requirements.items():
        # Equal base-value contribution shares, different Research bonuses.
        freight_contribute(api,guild.consortium_id,'member-1',kind,rid,qty/2,company_state=remote_stock('member-1',rid,qty/2))
        s.ensure_resource(rid).amount=qty/2
        freight_contribute(api,guild.consortium_id,api.current_company_id,kind,rid,qty/2)
    receipts=api.network.reward_receipts[contract.contract_id]
    expected=sum(quoted_prices[rid]*qty/2 for rid,qty in contract.requirements.items())*(1+bonus)
    assert receipts[api.current_company_id].cash==pytest.approx(expected,abs=.011)
    assert receipts[api.current_company_id].cash>receipts['member-1'].cash
    assert receipts[api.current_company_id].company_xp==receipts['member-1'].company_xp
    assert sum(round(r.cash*100) for r in receipts.values())<=round(contract.personal_reward.cash*100)


def test_remote_contribution_requires_real_sender_storage_before_any_credit():
    s,api,guild,clock=group(2);contract=start(api,guild)
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],1)
    empty=remote_stock('member-1',GOODS[0],0)
    with pytest.raises(ValueError):freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],1,company_state=empty)
    assert serialize_game_state(s)==before
    sender=remote_stock('member-1',GOODS[0],5)
    freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],2,company_state=sender,request_id='remote')
    assert sender.resources[GOODS[0]].amount==3
    assert contract.contributions['member-1'][GOODS[0]]==2
    assert freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],2,company_state=sender,request_id='remote')==0
    assert sender.resources[GOODS[0]].amount==3


def test_members_can_use_same_request_id_without_suppressing_each_other():
    s,api,guild,clock=group(2);contract=start(api,guild)
    sender=remote_stock('member-1',GOODS[0],2)
    freight_contribute(api,guild.consortium_id,'member-1','daily',GOODS[0],1,company_state=sender,request_id='same')
    s.ensure_resource(GOODS[0]).amount=2
    freight_contribute(api,guild.consortium_id,api.current_company_id,'daily',GOODS[0],1,request_id='same')
    assert contract.delivered[GOODS[0]]==2


def test_service_uses_loaded_network_and_clears_same_id_draft_quotes():
    s,api,guild,clock=group(2)
    contract=start(api,guild)
    restored=deserialize_game_state(serialize_game_state(s))
    api._preview_requirements[contract.contract_id]={'old-resource':999}
    contract.status='expired'
    s.consortium=restored.consortium
    assert api.network is restored.consortium and not api._preview_requirements
    s.ensure_resource(GOODS[0]).amount=1
    assert freight_receive(api,guild.consortium_id,'daily',contract.contract_id,GOODS[0],1,'after-load')==1
    assert restored.consortium.consortiums[guild.consortium_id].contracts['daily'].delivered[GOODS[0]]==1
    assert contract.delivered=={}


def test_work_cache_invalidates_on_definition_replacement_and_new_game():
    from production_zero.core.contracts import contract_value_calculator
    s=company();definitions=dict(D)
    original=contract_value_calculator(s,definitions)
    before=original.value_for_resource('iron_ore').value_per_unit
    assert contract_value_calculator(s,definitions) is original
    d=definitions['machine.extractor']
    options=tuple(replace(o,output_amount=o.output_amount_for(d)*2) for o in d.available_production_options)
    definitions['machine.extractor']=replace(d,production_options=options)
    changed=contract_value_calculator(s,definitions)
    assert changed is not original
    assert changed.value_for_resource('iron_ore').value_per_unit==pytest.approx(before/2)
    assert contract_value_calculator(company(),definitions) is not changed


def test_rotation_never_reuses_contract_id_even_with_old_sequence_counter():
    s,api,guild,clock=group(2)
    old=start(api,guild)
    old.status='completed'
    s.consortium.reward_receipts[old.contract_id]={}
    guild.next_contract_sequence=int(old.contract_id.rsplit("-",2)[1])
    new=api.renew_contract_offer(guild.consortium_id,api.current_company_id,'daily')
    assert new.contract_id!=old.contract_id and old in guild.contract_history
    assert api.renew_contract_offer(guild.consortium_id,api.current_company_id,'daily') is new
    before=serialize_game_state(s)
    with pytest.raises(ValueError,match='changed'):
        freight_contribute(api,guild.consortium_id,api.current_company_id,'daily',GOODS[0],1,expected_contract_id=old.contract_id)
    assert serialize_game_state(s)==before


def test_renewal_cannot_replace_an_active_contract_or_bypass_management():
    s,api,guild,clock=group(2);contract=start(api,guild)
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):api.renew_contract_offer(guild.consortium_id,'member-1','daily')
    with pytest.raises(ValueError):api.renew_contract_offer(guild.consortium_id,api.current_company_id,'daily')
    assert serialize_game_state(s)==before


def test_remote_capability_expires_for_new_offers_and_republication_restores_it():
    s,api,guild,clock=group(2)
    weekly=start(api,guild,'weekly');frozen=asdict(weekly)
    clock[0]+=86401
    api.contract_candidates(guild.consortium_id,'daily')
    assert guild.contracts['daily'].capacity_rates[GOODS[0]]==pytest.approx(120)
    assert asdict(weekly)==frozen
    remote=company();remote.consortium.current_company_id='member-1'
    api.update_capacity_snapshot('member-1',remote)
    api.contract_candidates(guild.consortium_id,'daily')
    assert guild.contracts['daily'].capacity_rates[GOODS[0]]==pytest.approx(240)
    assert asdict(weekly)==frozen


def test_rp_effort_snapshot_supports_unequal_companies_and_ignores_ghost_members():
    s,api,guild,clock=group(2,remote_mk=10)
    contract=start(api,guild,'weekly')
    _,other,expanded,_=group(2,remote_mk=10)
    for i in range(2,10):expanded.members[str(i)]=ConsortiumMember(str(i),str(i),100)
    other_contract=start(other,expanded,'weekly')
    for cid in (api.current_company_id,'member-1'):
        assert other_contract.rp_minimum_shares[cid]==pytest.approx(contract.rp_minimum_shares[cid])
    weak_share=1/4.25
    for rid,qty in contract.requirements.items():
        s.ensure_resource(rid).amount=qty*weak_share
        freight_contribute(api,guild.consortium_id,api.current_company_id,'weekly',rid,qty*weak_share)
        remainder=contract.remaining(rid)
        freight_contribute(api,guild.consortium_id,'member-1','weekly',rid,remainder,company_state=remote_stock('member-1',rid,remainder))
    receipts=s.consortium.reward_receipts[contract.contract_id]
    assert receipts[api.current_company_id].research_points==receipts['member-1'].research_points==1


def test_same_freight_id_from_different_companies_is_not_a_duplicate():
    s,api,guild,clock=group(2);contract=start(api,guild)
    original=api.current_company_id
    s.ensure_resource(GOODS[0]).amount=2
    assert freight_receive(api,guild.consortium_id,'daily',contract.contract_id,GOODS[0],1,'outbound-1')==1
    s.consortium.current_company_id='member-1'
    assert freight_receive(api,guild.consortium_id,'daily',contract.contract_id,GOODS[0],1,'outbound-1')==1
    assert freight_receive(api,guild.consortium_id,'daily',contract.contract_id,GOODS[0],1,'outbound-1')==0
    s.consortium.current_company_id=original
    loaded=deserialize_game_state(serialize_game_state(s));api=ConsortiumService(loaded,D,clock=lambda:1001)
    assert freight_receive(api,guild.consortium_id,'daily',contract.contract_id,GOODS[0],1,'outbound-1')==0
    assert loaded.consortium.consortiums[guild.consortium_id].contracts['daily'].delivered[GOODS[0]]==2


@pytest.mark.parametrize('kind',['regular','daily','weekly'])
def test_new_offers_never_automatically_fill_missing_manual_product_slots(kind,monkeypatch):
    from production_zero.core import company_xp
    monkeypatch.setattr(company_xp,'utc_timestamp',lambda now_utc=None:1792678460.)
    s=company();initialize_contracts(s,D);offer=s.contracts.offers[kind][0]
    before=serialize_game_state(s)
    with pytest.raises(ValueError,match='every Contract product'):
        accept_contract(s,kind,offer.contract_id,D,selected_resource_id=GOODS[0])
    assert serialize_game_state(s)==before


def test_poor_freight_cannot_buy_tiny_goals_then_bypass_them_with_direct_stock():
    s=company(mk=99,trucks=1)
    s.cards['truck0']=replace(s.cards['truck0'],mk_level=1)
    api=ConsortiumService(s,D,clock=lambda:1000);guild=api.create('Production Capacity Cooperative')
    contract=start(api,guild,'weekly')
    assert reachable_capacity(s,D).freight_per_minute==40
    assert contract.capacity_rates[GOODS[0]]==pytest.approx(40)
    assert sum(contract.requirements.values())<=40*480
    before=serialize_game_state(s)
    with pytest.raises(PermissionError):
        api.contribute(guild.consortium_id,api.current_company_id,'weekly',GOODS[0],1)
    assert serialize_game_state(s)==before


def test_verified_stock_donor_keeps_research_prices_without_current_production():
    from production_zero.core.research import research_catalog
    from production_zero.core.modifiers import market_sale_price
    s,api,guild,clock=group(2)
    donor=GameState(8810,warehouse_capacity=75280);donor.consortium.current_company_id='member-1'
    donor.research.unlocked_node_ids.update(research_catalog()[1])
    for rid in GOODS:donor.ensure_resource(rid).amount=100000
    api.update_capacity_snapshot('member-1',donor)
    contract=start(api,guild,'weekly')
    assert not guild.members['member-1'].capacity_rates
    for rid in contract.requirements:
        assert contract.member_unit_prices['member-1'][rid]==market_sale_price(donor,rid)


@pytest.mark.parametrize('operating_mode',('solar','coal'))
def test_unusable_optional_fuel_plant_keeps_independent_solar_contracts(operating_mode):
    s=company(solar=1 if operating_mode=='solar' else 0)
    if operating_mode=='coal':
        coal=D['energy.coal_power_plant'];cid='working-coal'
        hall=FactoryHall(cid,cid,1,board_kind='energy',max_lines=1,max_slots_per_line=1,start_unlocked_lines=1,start_slots_per_line=1)
        s.energy_plants[cid]=hall;s.cards[cid]=create_card_instance(cid,coal.definition_id,coal.card_kind,Rarity.COMMON);hall.slots[0].card_id=cid
        s.production_progress.lifetime_produced['coal']=120
    baseline=reachable_capacity(s,D)
    d=D['energy.gas_power_plant']
    hall=FactoryHall('optional-gas','Optional Gas',1,board_kind='energy',max_lines=1,max_slots_per_line=1,start_unlocked_lines=1,start_slots_per_line=1)
    s.energy_plants[hall.hall_id]=hall
    s.cards['optional-gas']=create_card_instance('optional-gas',d.definition_id,d.card_kind,Rarity.COMMON)
    hall.slots[0].card_id='optional-gas'
    assert not baseline.production_rates.get('natural_gas')
    plan=reachable_capacity(s,D)
    assert plan.production_rates==baseline.production_rates and plan.rates==baseline.rates
    active,_=accepted(s,'daily')
    assert active.offer.requirements and active.offer.balance_version==1


@pytest.mark.parametrize('operating_mode',('solar','coal'))
def test_optional_fuel_burn_exceeding_the_chain_keeps_solar_operating_mode(operating_mode):
    s=company(solar=1 if operating_mode=='solar' else 0)
    if operating_mode=='coal':
        d=D['energy.coal_power_plant'];cid='working-coal'
        hall=FactoryHall(cid,cid,1,board_kind='energy',max_lines=1,max_slots_per_line=1,start_unlocked_lines=1,start_slots_per_line=1)
        s.energy_plants[cid]=hall;s.cards[cid]=create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON);hall.slots[0].card_id=cid
        s.production_progress.lifetime_produced['coal']=120
    baseline=reachable_capacity(s,D)
    d=D['energy.coal_power_plant']
    count=math.ceil(baseline.production_rates['coal']/d.fuel_consumption_per_minute)+1
    for index in range(count):
        cid=f'optional-coal-{index}'
        hall=FactoryHall(cid,cid,1,board_kind='energy',max_lines=1,max_slots_per_line=1,start_unlocked_lines=1,start_slots_per_line=1)
        s.energy_plants[cid]=hall;s.cards[cid]=create_card_instance(cid,d.definition_id,d.card_kind,Rarity.COMMON);hall.slots[0].card_id=cid
    plan=reachable_capacity(s,D)
    assert plan.production_rates==baseline.production_rates and plan.rates==baseline.rates
