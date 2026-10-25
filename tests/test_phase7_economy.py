"""P7 quote identities, sparse Freight expansion, history and financial atomicity."""
from dataclasses import replace
from copy import deepcopy
import json
import pytest
from test_phase4_slot_permutations import definitions
from production_zero.core.state import GameState,FactoryHall
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.commands import (CommandBus,PurchaseProductionUnit,PurchaseHall,RenameHall,UnlockProductionLine,UnlockProductionSlot,
    BuildFreightFacility,ExpandFreightFacility,InstallFreightCard,MoveFreightVehicles,BuyDailyFreightSupplyCard,BuyCommonSupplyCard)
from production_zero.core.infrastructure_prices import (BOARD_LIMITS,production_facility_price,resource_retype_price,unit_line_price,unit_slot_price,facility_price)
from production_zero.core.freight import freight_facility_build_cost,freight_facility_expansion_cost,freight_stats,OutboundFreightShipment,FreightAssignment,start_outbound_shipment_for_card
from production_zero.core.supply import common_card_price,uncommon_card_price,refresh_supply,SupplyOffer
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.research import ResearchState,research_catalog
from production_zero.core.production_templates import MachineTemplate,quote_templates,PurchaseTemplates
from production_zero.core.machine_operations import resale_value,compatible_free_slots
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state,SQLiteSaveStore,STATE_SCHEMA_VERSION


def state():
    s=deserialize_game_state(serialize_game_state(GameState(197)));s.cash.amount=1e12;return s


def frozen(s):return json.dumps(serialize_game_state(s),sort_keys=True)


def build(s,board,target=None,quote=None):
    maximum,cap,start=BOARD_LIMITS[board]
    PurchaseProductionUnit(board,board,board,maximum,cap,2 if board=='factory' else 1,start,target,quote).apply(s)
    return next(reversed(s.production_units(board).values()))


@pytest.mark.parametrize('board',['factory','resources','energy'])
def test_new_facilities_have_one_start_line(board):
    s=state();u=build(s,board)
    assert sum(line.unlocked for line in u.production_lines)==1
    assert len(u.unlocked_slot_indexes())==BOARD_LIMITS[board][2]
    assert (u.max_lines,u.max_slots_per_line)==BOARD_LIMITS[board][:2]


@pytest.mark.parametrize('board,full,second,last,next_line',[
    ('factory',32600,15200,280,900),('resources',16650,4000,810,900),('energy',5500,2200,400,500)])
def test_complete_infrastructure_cash_and_marginal_capacity(board,full,second,last,next_line):
    s=state();u=build(s,board);initial=s.cash.amount;maximum,cap,start=BOARD_LIMITS[board]
    for i,line in enumerate(u.production_lines,1):
        if not line.unlocked:UnlockProductionLine(u.hall_id,line.line_id,board,unit_line_price(u,i)).apply(s)
        while len(line.slot_indexes)<cap:UnlockProductionSlot(u.hall_id,line.line_id,board,unit_slot_price(u,i,len(line.slot_indexes)+1)).apply(s)
    assert initial-s.cash.amount==full*u.expansion_tier**2
    assert len(u.unlocked_slot_indexes())==maximum*cap
    assert facility_price(board,1)==second
    assert next_line/start>last
    extras=sum(unit_slot_price(u,1,k) for k in range(start+1,cap+1))
    assert production_facility_price(s,board,u.specialization)+extras>=unit_line_price(u,maximum)+extras


@pytest.mark.parametrize('board',['factory','resources','energy'])
def test_next_line_can_be_bought_before_filling_previous(board):
    s=state();u=build(s,board);first=tuple(u.production_lines[0].slot_indexes);line=u.production_lines[1]
    cost=unit_line_price(u,2);cash=s.cash.amount
    UnlockProductionLine(u.hall_id,line.line_id,board,cost).apply(s)
    assert tuple(u.production_lines[0].slot_indexes)==first and line.unlocked
    assert len(line.slot_indexes)==u.start_slots_per_line and cash-s.cash.amount==cost


def test_legacy_paid_lines_and_future_compatibility_quotes_are_preserved():
    s=state();u=FactoryHall('legacy','Legacy',6,max_lines=5,building_investment=12345.67)
    u.production_lines[2].unlock_cost=750;s.halls[u.hall_id]=u
    old=serialize_game_state(s);old['state_schema_version']=7;old.pop('infrastructure_pricing_version')
    loaded=deserialize_game_state(old);saved=loaded.halls[u.hall_id]
    assert sum(line.unlocked for line in saved.production_lines)==2
    assert saved.building_investment==12345.67 and saved.production_lines[2].unlock_cost==750
    assert unit_line_price(saved,3)==3600
    initial=loaded.cash.amount;UnlockProductionLine('legacy',saved.production_lines[2].line_id,'factory',3600).apply(loaded)
    assert initial-loaded.cash.amount==3600 and saved.building_investment==15945.67


@pytest.mark.parametrize('target',['machine.extractor','machine.agriculture','machine.drilling'])
def test_resources_count_only_the_requested_type(target):
    s=state();s.resource_sites.clear()
    other=next(t for t in ('machine.extractor','machine.agriculture','machine.drilling') if t!=target)
    build(s,'resources',other);build(s,'resources',other)
    assert production_facility_price(s,'resources',target)==500
    first=build(s,'resources',target,500);assert first.specialization==target
    assert production_facility_price(s,'resources',target)==4000
    second=build(s,'resources',target,4000)
    assert second.building_investment==4000 and production_facility_price(s,'resources',target)==22700


def test_retype_is_quoted_and_does_not_credit_old_slot_investment():
    s=state();s.resource_sites.clear();a=build(s,'resources','machine.extractor');build(s,'resources','machine.agriculture')
    a.building_investment=100000;cost=resource_retype_price(s,a,'machine.agriculture');assert cost==4000
    before=frozen(s)
    with pytest.raises(ValueError,match='fixed at construction'):
        RenameHall(a.hall_id,'Agriculture','resources','machine.agriculture',cost,'machine.extractor').apply(s)
    assert frozen(s)==before and a.building_investment==100000 and a.specialization=='machine.extractor'
    assert production_facility_price(s,'resources','machine.extractor')==4000


@pytest.mark.parametrize('case',['cash','stale-price','stale-type','occupied','unknown-type','blank-name'])
def test_failed_retype_does_not_change_name_money_or_history(definitions,case):
    s=state();u=build(s,'resources','machine.extractor');cost=resource_retype_price(s,u,'machine.agriculture')
    target='machine.agriculture';expected='machine.extractor';name='Changed'
    if case=='cash':s.cash.amount=cost-1
    if case=='stale-price':cost+=1
    if case=='stale-type':expected='machine.drilling'
    if case=='unknown-type':target='unknown'
    if case=='blank-name':name=' '
    if case=='occupied':
        s.cards['c']=create_card_instance('c','machine.extractor',definitions['machine.extractor'].card_kind,Rarity.COMMON);u.slots[0].card_id='c'
    before=frozen(s)
    with pytest.raises(ValueError):RenameHall(u.hall_id,name,'resources',target,cost,expected).apply(s)
    assert frozen(s)==before


@pytest.mark.parametrize('kind',['garage_depot','rail_station','airport','harbor'])
def test_next_freight_line_requires_completing_previous_slots(definitions,kind):
    s=state();BuildFreightFacility(kind).apply(s);u=next(reversed(s.freight.facilities.values()))
    previous=set(u.unlocked_slot_indexes());cash=s.cash.amount
    before=frozen(s)
    with pytest.raises(ValueError,match='Complete all slots'):
        ExpandFreightFacility(u.facility_id,8).apply(s)
    assert frozen(s)==before
    for index in range(len(u.slots),8):ExpandFreightFacility(u.facility_id,index).apply(s)
    price=freight_facility_expansion_cost(u,slot_index=8);cash=s.cash.amount
    ExpandFreightFacility(u.facility_id,8,price).apply(s)
    assert set(u.unlocked_slot_indexes())==set(range(9)) and cash-s.cash.amount==price
    assert len(u.slots)==9 and u.slots[8].index==8
    loaded=deserialize_game_state(serialize_game_state(s));assert set(loaded.freight.facilities[u.facility_id].unlocked_slot_indexes())==set(range(9))
    assert loaded.freight.facilities[u.facility_id].slots==u.slots


def test_sparse_slots_are_rejected_by_moves_templates_and_legacy_install(definitions):
    from production_zero.core.freight import FreightSlot
    s=state();u=s.freight.facilities['garage-1']
    # A paid sparse line from the old rules remains a valid legacy fixture.
    u.slots=[FreightSlot(i) for i in range(9)];u.slot_count=9;u.purchased_slot_indexes={0,1,2,8}
    s.cards['truck']=create_card_instance('truck','freight.truck',definitions['freight.truck'].card_kind,Rarity.COMMON)
    InstallFreightCard(u.facility_id,0,'truck',definitions).apply(s)
    before=frozen(s)
    with pytest.raises(ValueError):MoveFreightVehicles(('truck',),u.facility_id,(4,),definitions).apply(s)
    assert frozen(s)==before
    _unit,free,_total,_plans=quote_templates(s,definitions,(MachineTemplate('freight.truck'),),'freight',u.facility_id,0)
    assert free==[1,2] and all(slot.index not in {3,4,5,6,7} for _unit,slot in compatible_free_slots(s,definitions['freight.truck']))


def test_second_fleet_is_cheaper_than_equivalent_new_garage():
    s=state();u=s.freight.facilities['garage-1']
    fleet=900+sum(60*i for i in range(1,8))+8*205
    new=freight_facility_build_cost(s.freight,'garage_depot')+sum(60*i for i in range(1,6))+8*205
    assert fleet==4220 and new==10540 and fleet<new


@pytest.mark.parametrize('mk',[1,2,10,50,99])
@pytest.mark.parametrize('rarity',[Rarity.COMMON,Rarity.RARE,Rarity.LEGENDARY])
@pytest.mark.parametrize('research',[False,True])
def test_comparable_ship_is_three_aircrafts_in_price_and_nominal_throughput(definitions,mk,rarity,research):
    r=ResearchState()
    if research:
        _,nodes=research_catalog();r.unlocked_node_ids.update(n.id for n in nodes.values() if n.effect_type=='freight_capacity')
    cards=[replace(create_card_instance(did,did,definitions[did].card_kind,rarity),mk_level=mk,output_bonus_percent=0 if rarity is Rarity.COMMON else 20) for did in ('freight.aircraft','freight.ship')]
    air,ship=[freight_stats(card,definitions[card.definition_id],r) for card in cards]
    assert ship.capacity/ship.transport_time_seconds==pytest.approx(3*air.capacity/air.transport_time_seconds)
    assert common_card_price(definitions['freight.ship'])==3*common_card_price(definitions['freight.aircraft'])==14955
    if mk<99:
        from decimal import Decimal
        ship_quote=Decimal(str(mk_upgrade_cost(cards[1],definitions['freight.ship'])))
        three_air=3*Decimal(str(mk_upgrade_cost(cards[0],definitions['freight.aircraft'])))
        assert three_air-Decimal('.02')<=ship_quote<=three_air


def test_common_daily_and_template_quotes_use_the_same_ship_basis(definitions):
    s=state();BuildFreightFacility('harbor').apply(s);u=next(reversed(s.freight.facilities.values()))
    common=common_card_price(definitions['freight.ship']);assert common==14955
    _unit,_free,total,_plans=quote_templates(s,definitions,(MachineTemplate('freight.ship'),),'freight',u.facility_id,0)
    assert total==common
    PurchaseTemplates((MachineTemplate('freight.ship'),),'freight',u.facility_id,0,definitions,total).apply(s)
    acquired=[c for c in s.cards.values() if c.definition_id=='freight.ship'];assert acquired[0].acquisition_cost==common
    refresh_supply(s,definitions);period=s.supply.freight_daily_period_index
    offer=SupplyOffer('old-ship','freight.ship',definitions['freight.ship'].card_kind,Rarity.UNCOMMON,25,999999,period)
    s.supply.freight_daily_offers=[offer];before=frozen(s)
    with pytest.raises(ValueError):BuyDailyFreightSupplyCard(offer.offer_id,definitions,999999).apply(s)
    assert frozen(s)==before
    cost=uncommon_card_price(definitions['freight.ship'],25)
    BuyDailyFreightSupplyCard(offer.offer_id,definitions,cost).apply(s)
    assert max(c.acquisition_cost for c in s.cards.values())==cost
    assert s.supply.freight_daily_purchased_offer_id==offer.offer_id


def test_old_ship_investment_active_cargo_and_p6_history_are_not_revalued(definitions):
    s=state();BuildFreightFacility('harbor').apply(s);u=next(reversed(s.freight.facilities.values()))
    card=replace(create_card_instance('old','freight.ship',definitions['freight.ship'].card_kind,Rarity.COMMON),acquisition_cost=48200,upgrade_investment=1234)
    s.cards['old']=card;u.slots[0].card_id='old';s.ensure_resource('iron_ore').amount=1e6
    s.freight.assignments['old']=FreightAssignment('iron_ore','market')
    q=OutboundFreightShipment('legacy','market',resource_id='iron_ore',quantity=1000,freight_card_id='old',transport_capacity=40000,transport_time_seconds=240,remaining_seconds=60,market_price=2,source_facility_id=u.facility_id)
    s.freight.outbound_shipments[q.shipment_id]=q;s.freight.delivery_statistics.advance(600);s.freight.delivery_statistics.record('old',u.facility_id,sell=40000)
    old=serialize_game_state(s);old['state_schema_version']=7;old.pop('infrastructure_pricing_version')
    for facility in old['freight']['facilities'].values():facility.pop('purchased_slot_indexes')
    loaded=deserialize_game_state(old)
    assert loaded.cards['old']==card and loaded.freight.outbound_shipments['legacy']==q
    assert loaded.freight.delivery_statistics.snapshot()==s.freight.delivery_statistics.snapshot()
    assert resale_value(loaded.cards['old'],definitions['freight.ship'])==pytest.approx((48200+1234)*.8)
    loaded.freight.facilities[u.facility_id].paused=True
    from production_zero.core.simulation import SimulationEngine
    engine=SimulationEngine(definitions);engine.advance_time(loaded,30)
    assert loaded.freight.delivery_statistics.rate(card_id='old').total==40000
    engine.advance_time(loaded,30);assert loaded.freight.delivery_statistics.rate(card_id='old').total==1000
    loaded.freight.facilities[u.facility_id].paused=False
    future=start_outbound_shipment_for_card(loaded.freight,loaded.cards,definitions,card_id='old',destination_kind='market',resource_id='iron_ore',quantity=100000)
    assert future.transport_capacity==16000 and future.transport_time_seconds==240


@pytest.mark.parametrize('command',['building','freight','line','slot','freight-slot'])
@pytest.mark.parametrize('failure',['stale','cash','nan'])
def test_financial_rejections_are_atomic(command,failure):
    s=state();u=build(s,'factory');line=u.production_lines[0]
    if command=='building':cost=production_facility_price(s,'factory');make=lambda expected:PurchaseHall(expected_cost=expected)
    if command=='freight':cost=freight_facility_build_cost(s.freight,'airport');make=lambda expected:BuildFreightFacility('airport',expected)
    if command=='line':cost=unit_line_price(u,2);make=lambda expected:UnlockProductionLine(u.hall_id,u.production_lines[1].line_id,'factory',expected)
    if command=='slot':cost=unit_slot_price(u,1,4);make=lambda expected:UnlockProductionSlot(u.hall_id,line.line_id,'factory',expected)
    if command=='freight-slot':cost=freight_facility_expansion_cost(s.freight.facilities['garage-1'],slot_index=8);make=lambda expected:ExpandFreightFacility('garage-1',8,expected)
    expected=cost+1 if failure=='stale' else cost
    if failure=='cash':s.cash.amount=cost-1
    if failure=='nan':expected=float('nan')
    before=frozen(s)
    with pytest.raises(ValueError):make(expected).apply(s)
    assert frozen(s)==before


def test_schema7_backup_and_future_schema_guard(tmp_path):
    s=state();store=SQLiteSaveStore(tmp_path/'company.sqlite');store.initialize()
    payload=serialize_game_state(s);payload['state_schema_version']=7;payload.pop('infrastructure_pricing_version')
    store.save_payload('old',json.dumps(payload));loaded=store.load('old')
    assert (tmp_path/'company.pre-industriova-v8.sqlite').exists()
    assert serialize_game_state(loaded)['state_schema_version']==9
    payload['state_schema_version']=10
    with pytest.raises(ValueError):deserialize_game_state(payload)
    from production_zero.core.infrastructure_prices import PRICING_VERSION
    payload['state_schema_version']=8;payload['infrastructure_pricing_version']=PRICING_VERSION+1
    with pytest.raises(ValueError):deserialize_game_state(payload)



@pytest.mark.parametrize('board',['resources','energy'])
def test_grandfathered_dimensions_keep_working_and_prices_match(board):
    s=state();u=FactoryHall('old','Old',6,board_kind=board)
    s.production_units(board)[u.hall_id]=u
    u=deserialize_game_state(serialize_game_state(s)).production_units(board)[u.hall_id]
    # Old saves can have wider areas than the current new-building configuration.
    assert u.max_slots_per_line==10
    assert unit_line_price(u,2)/u.start_slots_per_line > unit_slot_price(u,1,10)
    line=u.production_lines[0]
    while len(line.slot_indexes)<10:
        quote=unit_slot_price(u,1,len(line.slot_indexes)+1)
        s.production_units(board)[u.hall_id]=u;cash=s.cash.amount
        UnlockProductionSlot(u.hall_id,line.line_id,board,quote).apply(s)
        assert cash-s.cash.amount==quote


def test_quick_build_retry_cannot_reuse_the_previous_quote():
    s=state();command=PurchaseHall(expected_cost=facility_price('factory',0))
    command.apply(s);before=frozen(s)
    with pytest.raises(ValueError,match='price changed'):command.apply(s)
    assert frozen(s)==before
    assert len(s.halls)==1 and len(next(iter(s.halls.values())).unlocked_slot_indexes())==3


def test_actual_finite_cash_start_reaches_both_new_resource_branches(definitions):
    from production_zero.ui.main_window import _create_initial_state
    from production_zero.data.definitions import load_resource_definitions
    from importlib.resources import files
    from production_zero.core.commands import SelectMachineProduction,InstallCardInHall
    from production_zero.core.simulation import SimulationEngine
    from production_zero.core.state import MachineProductionState
    s=_create_initial_state(load_resource_definitions(files('production_zero.data')/'resource_definitions.json'),definitions)
    assert s.cash.amount==1250
    for _ in range(2):UnlockProductionSlot('site-1','site-1.line-1','resources').apply(s)
    UnlockProductionSlot('plant-1','plant-1.line-1','energy').apply(s)
    existing=set(s.cards);BuyCommonSupplyCard('energy.solar_array',definitions).apply(s)
    solar=next(iter(set(s.cards)-existing));existing=set(s.cards)
    BuyCommonSupplyCard('freight.truck',definitions).apply(s);truck=next(iter(set(s.cards)-existing))
    def machine(cid,uid,index,board,rid):
        InstallCardInHall(uid,index,cid,board).apply(s)
        option=next(o for o in definitions[s.cards[cid].definition_id].available_production_options if o.output_resource==rid)
        # This audit measures material/capital feasibility using the stated recipes.
        s.production_progress.unlocked_production_ids.add(option.production_id)
        SelectMachineProduction(cid,option.production_id,rid).apply(s)
    for i,rid in enumerate(('iron_ore','coal','iron_ore')):machine(f'test-drill-common-00{i+1}','site-1',i,'resources',rid)
    for i,cid in enumerate(('test-furnace-common-001','test-blast-furnace-common-001')):machine(cid,'hall-1',i,'factory','iron')
    for i,cid in enumerate(('test-solar-common-001',solar)):InstallCardInHall('plant-1',i,cid,'energy').apply(s)
    for i,cid in enumerate(('starter-truck-common-001','starter-truck-common-002',truck)):
        InstallFreightCard('garage-1',i,cid,definitions).apply(s);s.freight.assignments[cid]=FreightAssignment('iron','market')
    assert s.cash.amount==495
    engine=SimulationEngine(definitions);pending=['machine.agriculture','machine.drilling'];milestones=[]
    for second in range(1,601):
        engine.advance_time(s,1)
        if not pending:continue
        did=pending[0];cost=common_card_price(definitions[did])
        if did=='machine.drilling':cost+=unit_slot_price(s.energy_plants['plant-1'],1,3)+common_card_price(definitions['energy.solar_array'])
        if s.cash.amount<cost:continue
        unit=next(u for u in s.resource_sites.values() if u.specialization==did);old=set(s.cards);BuyCommonSupplyCard(did,definitions).apply(s);cid=next(iter(set(s.cards)-old))
        rid=next(o.output_resource for o in definitions[did].available_production_options if not o.input_resources)
        machine(cid,unit.hall_id,0,'resources',rid)
        if did=='machine.drilling':
            UnlockProductionSlot('plant-1','plant-1.line-1','energy').apply(s);old=set(s.cards)
            BuyCommonSupplyCard('energy.solar_array',definitions).apply(s);extra=next(iter(set(s.cards)-old));InstallCardInHall('plant-1',2,extra,'energy').apply(s)
        milestones.append(second);pending.pop(0)
        assert s.cash.amount>=0
    assert not pending and milestones[1]<=360
    assert s.statistics.total_earnings>0 and s.used_storage<=s.storage_capacity
    assert all(stock.amount>=0 for stock in s.resources.values())
