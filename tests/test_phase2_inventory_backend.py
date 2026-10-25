"""P2 contracts: complete state comparisons for rejection and concrete ID actions."""
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files
import json

import pytest
from production_zero.core.cards import create_card_instance
from production_zero.core.commands import (CommandBus, BuyCommonSupplyCard, BuyDailyMachineSupplyCard,
    BuyDailyFreightSupplyCard, InstallCardInHall, InstallFreightCard, ReturnMachinesToInventory,
    SellMachines, RemoveCardFromHall, RemoveFreightCard)
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import Rarity
from production_zero.core.freight import FreightAssignment, OutboundFreightShipment, build_freight_facility
from production_zero.core.inventory import build_card_inventory_rows, build_placeable_inventory_stacks
from production_zero.core.machine_operations import resale_value
from production_zero.core.mk_upgrades import upgrade_cards
from production_zero.core.production_templates import MachineTemplate, PurchaseTemplates, copy_templates, quote_templates
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState, FactoryHall, MachineProductionState
from production_zero.core.supply import (buy_common_supply_cards, common_card_price, common_supply_max_quantity,
    refresh_supply, buy_common_supply_card)
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, SQLiteSaveStore
from production_zero.persistence.session_writer import snapshot_game_state, encode_snapshot


@pytest.fixture
def definitions():
    return load_card_definitions(files('production_zero.data')/'game_definitions.json')


def company(definitions):
    s=GameState(2026);s.cash.amount=1e9;s.warehouse_capacity=1e9
    s.halls['h']=FactoryHall('h','Factory',6,max_lines=5)
    s.resource_sites['r']=FactoryHall('r','Mine',6,board_kind='resources',specialization='machine.extractor')
    s.energy_plants['e']=FactoryHall('e','Power',6,board_kind='energy')
    s.production_progress.unlocked_production_ids.update(p.production_id for d in definitions.values()
        if isinstance(d,MachineDefinition) for p in d.available_production_options)
    return s


def install(s,definitions,cid,index=0):
    d=definitions[s.cards[cid].definition_id]
    if d.card_kind.value=='freight':
        facility=next((f for f in s.freight.facilities.values() if f.facility_type==d.facility_id),None)
        if facility is None:facility=build_freight_facility(s.freight,d.facility_id)
        InstallFreightCard(facility.facility_id,index,cid,definitions).apply(s)
    else:
        board,uid=('energy','e') if d.card_kind.value=='energy' else (('resources','r') if d.definition_id=='machine.extractor' else ('factory','h'))
        InstallCardInHall(uid,index,cid,board).apply(s)


def frozen(s):
    return json.loads(json.dumps(serialize_game_state(s)))


def rejected(s,command,errors=(ValueError,KeyError,IndexError)):
    bus=CommandBus(s);before=frozen(s);full=deepcopy(s)
    with pytest.raises(errors):bus.dispatch(command)
    assert frozen(s)==before and s==full and s.completed_card_operations==full.completed_card_operations
    assert bus.history==()


@pytest.mark.parametrize('quantity',(1,10,100,1000))
@pytest.mark.parametrize('did',('machine.processor','energy.solar_array','freight.truck'))
def test_regular_purchases_only_own_cards_without_any_building(definitions,quantity,did):
    s=GameState(1);s.freight.facilities.clear();s.cash.amount=1e9
    before=s.cash.amount;bus=CommandBus(s);bus.dispatch(BuyCommonSupplyCard(did,definitions,quantity))
    assert len(s.cards)==quantity and len(set(s.cards))==quantity
    assert not s.installed_card_ids()|s.installed_freight_card_ids()
    assert sum(stack.quantity for stack in s.inventory_card_stacks())==quantity
    assert s.cash.amount==before-quantity*common_card_price(definitions[did])
    assert len(s.history.series['cash'].values)==1 and len(bus.history)==1
    assert all(c.acquisition_cost==common_card_price(definitions[did]) and c.mk_level==1 and c.rarity is Rarity.COMMON for c in s.cards.values())


@pytest.mark.parametrize('quantity',(0,-1,1.5,True,False,10001,'10',None))
def test_invalid_purchase_is_wholly_atomic(definitions,quantity):
    s=company(definitions);rejected(s,BuyCommonSupplyCard('machine.processor',definitions,quantity))


def test_buy_cash_max_changed_quote_and_same_command_retry(definitions):
    s=company(definitions);price=common_card_price(definitions['machine.processor']);s.cash.amount=price-.01
    assert common_supply_max_quantity(s,definitions,'machine.processor')==0
    rejected(s,BuyCommonSupplyCard('machine.processor',definitions))
    s.cash.amount=price*15
    assert common_supply_max_quantity(s,definitions,'machine.processor')==15
    s.cash.amount=price*10001
    assert common_supply_max_quantity(s,definitions,'machine.processor')==10000
    rejected(s,BuyCommonSupplyCard('machine.processor',definitions,1,price-1))
    changed=dict(definitions);changed['machine.processor']=replace(changed['machine.processor'],base_power_draw=999)
    rejected(s,BuyCommonSupplyCard('machine.processor',changed,1,price))
    command=BuyCommonSupplyCard('machine.processor',definitions,10,price);copy_before=deepcopy(command)
    CommandBus(s).dispatch(command);rejected(s,command);rejected(s,copy_before)
    # A separately created command is an intentional next purchase.
    CommandBus(s).dispatch(BuyCommonSupplyCard('machine.processor',definitions,10,price))
    assert len(s.cards)==20
    rejected(s,BuyCommonSupplyCard('missing',definitions))


@pytest.mark.parametrize('category,cls',(('machine',BuyDailyMachineSupplyCard),('freight',BuyDailyFreightSupplyCard)))
def test_daily_plan_failure_retry_rotation_and_limits(definitions,category,cls):
    s=GameState(6);s.freight.facilities.clear();refresh_supply(s,definitions)
    offers=getattr(s.supply,f'{category}_daily_offers');offer=offers[0];s.cash.amount=offer.price_cash-1
    rejected(s,cls(offer.offer_id,definitions))
    s.cash.amount=1e7;rejected(s,cls(offer.offer_id,definitions,offer.price_cash+1))
    command=cls(offer.offer_id,definitions,offer.price_cash);CommandBus(s).dispatch(command)
    assert len(s.cards)==1 and not s.installed_card_ids()|s.installed_freight_card_ids()
    c=next(iter(s.cards.values()));assert c.rarity==offer.rarity and c.output_bonus_tenths==offer.bonus_tenths
    assert c.acquisition_cost==offer.price_cash
    rejected(s,command);rejected(s,cls(offers[1].offer_id,definitions))
    s.market.elapsed_seconds=86400
    rejected(s,cls(offer.offer_id,definitions))  # stale request must not rotate live daily book
    refresh_supply(s,definitions)
    offer=getattr(s.supply,f'{category}_daily_offers')[0]
    CommandBus(s).dispatch(cls(offer.offer_id,definitions));assert len(s.cards)==2


def test_failed_daily_from_uninitialized_book_and_single_helper_are_atomic(definitions):
    s=GameState(7);rejected(s,BuyDailyMachineSupplyCard('missing',definitions))
    before=frozen(s)
    with pytest.raises(ValueError):buy_common_supply_card(s,definitions,'machine.processor')
    assert frozen(s)==before


@pytest.mark.parametrize('did',('machine.processor','machine.extractor','energy.solar_array','freight.truck'))
def test_install_return_and_reinstall_preserve_exact_card_configuration(definitions,did):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,did)[0]
    s.cards[cid]=replace(s.cards[cid],mk_level=50,rarity=Rarity.LEGENDARY,output_bonus_percent=18,
        power_bonus_percent=9,upgrade_investment=123456,paused=True)
    d=definitions[did]
    if isinstance(d,MachineDefinition):
        p=d.available_production_options[0];s.machine_production[cid]=MachineProductionState(cid,p.output_resource,p.production_id,2.5,'paused')
    if did=='freight.truck':
        s.ensure_resource('iron_ore');s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    before_card=s.cards[cid];before_production=deepcopy(s.machine_production);before_routes=deepcopy(s.freight.assignments);cash=s.cash.amount
    install(s,definitions,cid);ReturnMachinesToInventory((cid,)).apply(s)
    assert s.cards[cid] is before_card and s.machine_production==before_production and s.freight.assignments==before_routes
    rejected(s,ReturnMachinesToInventory((cid,)))
    install(s,definitions,cid)
    assert s.cards[cid] is before_card and s.cash.amount==cash and s.machine_production==before_production


@pytest.mark.parametrize('case',('occupied','locked','wrong-board','wrong-site','already-installed','missing-card','missing-building','negative-slot','bool-slot'))
def test_production_install_rejections_preserve_everything(definitions,case):
    s=company(definitions);a,b=buy_common_supply_cards(s,definitions,'machine.processor',2)
    command=InstallCardInHall('h',0,a,'factory')
    if case=='occupied':install(s,definitions,b)
    elif case=='locked':command=replace(command,slot_index=59)
    elif case=='wrong-board':command=replace(command,hall_id='e',board_kind='energy')
    elif case=='wrong-site':command=replace(command,hall_id='r',board_kind='resources')
    elif case=='already-installed':install(s,definitions,a);command=replace(command,slot_index=1)
    elif case=='missing-card':command=replace(command,card_id='absent')
    elif case=='missing-building':command=replace(command,hall_id='absent')
    elif case=='negative-slot':command=replace(command,slot_index=-1)
    elif case=='bool-slot':command=replace(command,slot_index=True)
    rejected(s,command)


@pytest.mark.parametrize('case',('busy','reserved-unplaced','wrong-facility','occupied','missing','invalid-route'))
def test_freight_install_and_return_group_reservation_protection(definitions,case):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'freight.truck')[0]
    machine=buy_common_supply_cards(s,definitions,'machine.processor')[0];install(s,definitions,machine)
    command=InstallFreightCard('garage-1',0,cid,definitions)
    if case in ('busy','reserved-unplaced'):
        s.freight.outbound_shipments['trip']=OutboundFreightShipment('trip','contract',resource_id='iron_ore',quantity=5,freight_card_id=cid,remaining_seconds=20)
        if case=='busy':
            # Existing placement represents the vehicle that reserved the cargo.
            s.freight.facilities['garage-1'].slots[0].card_id=cid
            command=ReturnMachinesToInventory((machine,cid))
    elif case=='wrong-facility':
        f=build_freight_facility(s.freight,'rail_station');command=replace(command,facility_id=f.facility_id)
    elif case=='occupied':
        other=buy_common_supply_cards(s,definitions,'freight.truck')[0];install(s,definitions,other)
    elif case=='missing':command=replace(command,facility_id='absent')
    elif case=='invalid-route':s.freight.assignments[cid]=FreightAssignment('absent','market')
    rejected(s,command)
    if case in ('busy','reserved-unplaced'):rejected(s,SellMachines((machine,cid),definitions))


def test_partial_cycle_freezes_and_resumes_once_even_after_repeated_returns(definitions):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'machine.processor')[0]
    solar=buy_common_supply_cards(s,definitions,'energy.solar_array')[0];install(s,definitions,cid);install(s,definitions,solar)
    d=definitions['machine.processor'];p=next(p for p in d.available_production_options if p.input_resources)
    definitions=dict(definitions);definitions['energy.solar_array']=replace(definitions['energy.solar_array'],base_power_output=1e9)
    cycle=p.cycle_seconds_for(d);s.machine_production[cid]=MachineProductionState(cid,p.output_resource,p.production_id)
    for rid in p.input_resources:s.ensure_resource(rid).amount=1000
    engine=SimulationEngine(definitions,utc_now=lambda:1792324800.)
    engine.advance_time(s,cycle*.4);assert s.machine_production[cid].progress_seconds==pytest.approx(cycle*.4)
    before=s.resource_snapshot()
    for _ in range(5):
        ReturnMachinesToInventory((cid,)).apply(s);engine.advance_time(s,cycle*10)
        assert s.machine_production[cid].progress_seconds==pytest.approx(cycle*.4) and s.resource_snapshot()==before
        install(s,definitions,cid)
    totals=engine.advance_time(s,cycle*.6)
    assert totals.outputs[p.output_resource]==pytest.approx(p.output_amount_for(d))
    for rid,amount in p.input_resources.items():assert totals.inputs[rid]==pytest.approx(amount)
    assert s.machine_production[cid].progress_seconds==pytest.approx(0)
    assert not engine.advance_time(s,0).outputs


def test_mixed_return_is_atomic_legacy_removers_preserve_progress_and_routes(definitions):
    s=company(definitions);a,b=buy_common_supply_cards(s,definitions,'machine.processor',2);install(s,definitions,a);install(s,definitions,b,1)
    for ids in ((a,'absent'),(a,a),()):rejected(s,ReturnMachinesToInventory(ids))
    s.machine_production[a]=MachineProductionState(a,'iron','recipe.processor.iron',2.2,'running')
    RemoveCardFromHall('h',0,'factory').apply(s);assert s.machine_production[a].progress_seconds==2.2
    install(s,definitions,a);ReturnMachinesToInventory((a,b)).apply(s)
    assert not s.installed_card_ids() and len(s.cards)==2
    truck=buy_common_supply_cards(s,definitions,'freight.truck')[0];install(s,definitions,truck)
    s.ensure_resource('iron_ore');s.freight.assignments[truck]=FreightAssignment('iron_ore','market')
    RemoveFreightCard('garage-1',0).apply(s);assert truck in s.freight.assignments


def test_inventory_sales_use_recorded_individual_investments_and_no_repeat_payout(definitions):
    s=company(definitions);ids=buy_common_supply_cards(s,definitions,'machine.processor',3)
    s.cards[ids[0]]=replace(s.cards[ids[0]],acquisition_cost=111,upgrade_investment=22)
    s.cards[ids[1]]=replace(s.cards[ids[1]],acquisition_cost=999)
    s.cards[ids[2]]=replace(s.cards[ids[2]],acquisition_cost=None,upgrade_investment=10)
    assert len(s.inventory_card_stacks())==3
    altered=dict(definitions);altered['machine.processor']=replace(definitions['machine.processor'],base_power_draw=12345)
    assert resale_value(s.cards[ids[2]],altered['machine.processor'])==8
    for selected in ((ids[0],'absent'),(ids[0],ids[0]),()):rejected(s,SellMachines(selected,definitions))
    value=sum(resale_value(s.cards[cid],altered['machine.processor']) for cid in ids);before=s.cash.amount
    command=SellMachines(ids,altered);CommandBus(s).dispatch(command)
    assert s.cash.amount==pytest.approx(before+value) and not s.cards
    rejected(s,command)
    cid=buy_common_supply_cards(s,definitions,'energy.solar_array')[0];upgrade_cards(s,definitions,(cid,))
    value=resale_value(s.cards[cid],definitions['energy.solar_array']);before=s.cash.amount
    SellMachines((cid,),definitions).apply(s);assert s.cash.amount==pytest.approx(before+value)


@pytest.mark.parametrize('count',(1,3))
@pytest.mark.parametrize('level,rarity',((1,Rarity.COMMON),(50,Rarity.LEGENDARY)))
def test_templates_remain_paid_direct_fresh_mk1_common_copies(definitions,count,level,rarity):
    s=company(definitions);source=buy_common_supply_cards(s,definitions,'machine.processor')[0];install(s,definitions,source)
    s.cards[source]=replace(s.cards[source],mk_level=level,rarity=rarity,upgrade_investment=888,paused=True)
    p=definitions['machine.processor'].available_production_options[0];s.machine_production[source]=MachineProductionState(source,p.output_resource,p.production_id,2.5,'paused')
    templates=copy_templates(s,(source,))*count;line=s.halls['h'].production_lines[1].line_id
    quote=quote_templates(s,definitions,templates,'factory','h',line)[2];before=set(s.cards);cash=s.cash.amount
    command=PurchaseTemplates(templates,'factory','h',line,definitions,quote);copy_before=deepcopy(command)
    CommandBus(s).dispatch(command);new=set(s.cards)-before
    assert len(new)==count and new<=s.installed_card_ids() and s.cash.amount==cash-quote
    assert all(s.cards[cid].mk_level==1 and s.cards[cid].rarity is Rarity.COMMON and s.cards[cid].paused
        and s.cards[cid].upgrade_investment==0 and s.machine_production[cid].progress_seconds==0 for cid in new)
    assert s.machine_production[source].progress_seconds==2.5
    rejected(s,command);rejected(s,copy_before)


@pytest.mark.parametrize('case',('slots','cash','incompatible','recipe','price','cancel'))
def test_template_failures_do_not_leave_partial_inventory(definitions,case):
    s=company(definitions);templates=(MachineTemplate('machine.processor'),)*3;line=s.halls['h'].production_lines[0].line_id
    price=quote_templates(s,definitions,templates,'factory','h',line)[2]
    command=PurchaseTemplates(templates,'factory','h',line,definitions,price)
    if case=='slots':install(s,definitions,buy_common_supply_cards(s,definitions,'machine.processor')[0])
    elif case=='cash':s.cash.amount=price-1
    elif case=='incompatible':command=replace(command,templates=(MachineTemplate('freight.truck'),)*3)
    elif case=='recipe':command=replace(command,templates=(MachineTemplate('machine.processor','absent'),)*3)
    elif case=='price':command=replace(command,expected_total=price+1)
    elif case=='cancel':
        before=frozen(s);quote_templates(s,definitions,templates,'factory','h',line)
        assert frozen(s)==before;return
    rejected(s,command)


def test_schema6_sqlite_roundtrip_all_kinds_placed_unplaced_config_and_reserved_cargo(definitions,tmp_path):
    s=company(definitions)
    for did in ('machine.processor','energy.solar_array','freight.truck'):
        a,b=buy_common_supply_cards(s,definitions,did,2);install(s,definitions,a)
        for cid in (a,b):
            s.cards[cid]=replace(s.cards[cid],mk_level=50,rarity=Rarity.LEGENDARY,upgrade_investment=123,paused=True)
            if did=='machine.processor':
                p=definitions[did].available_production_options[0];s.machine_production[cid]=MachineProductionState(cid,p.output_resource,p.production_id,1.25,'paused')
            if did=='freight.truck':
                s.ensure_resource('iron_ore');s.freight.assignments[cid]=FreightAssignment('iron_ore','contract')
        if did=='freight.truck':s.freight.outbound_shipments['reserved']=OutboundFreightShipment('reserved','contract',quantity=5,resource_id='iron_ore',freight_card_id=a,remaining_seconds=12)
    expected=frozen(s);assert expected['state_schema_version']==9
    snap=snapshot_game_state(s);store=SQLiteSaveStore(tmp_path/'p2.sqlite');store.initialize();store.save_payload('company',encode_snapshot(snap))
    loaded=store.load('company');assert frozen(loaded)==expected
    assert frozen(deserialize_game_state(serialize_game_state(loaded)))==expected
    assert len(build_placeable_inventory_stacks(loaded,definitions))==3
    assert sum(r.quantity for r in build_card_inventory_rows(loaded,definitions))==6
    fresh=GameState(2026);assert not fresh.cards and not fresh.completed_card_operations
    assert not loaded.completed_card_operations  # session receipts are not save data


@pytest.mark.parametrize('count',(500,5000,10000))
def test_large_inventory_projection_and_snapshot_keep_every_concrete_id(definitions,count):
    s=GameState(1);s.cash.amount=1e10
    ids=buy_common_supply_cards(s,definitions,'machine.processor',count)
    stacks=s.inventory_card_stacks();assert len(stacks)==1 and stacks[0].quantity==count
    assert set(ids)=={card.card_id for card in stacks[0].cards}
    snap=snapshot_game_state(s);restored=deserialize_game_state(json.loads(encode_snapshot(snap)))
    assert restored.cards==s.cards and not restored.installed_card_ids()


def test_daily_energy_and_fresh_id_collision_reject_before_debit(definitions,monkeypatch):
    from production_zero.core.supply import SupplyOffer
    from types import SimpleNamespace
    s=company(definitions);refresh_supply(s,definitions);d=definitions['energy.solar_array']
    offer=SupplyOffer('daily-energy',d.definition_id,d.card_kind,Rarity.UNCOMMON,25,999,0)
    s.supply.machine_daily_offers=[offer]
    CommandBus(s).dispatch(BuyDailyMachineSupplyCard(offer.offer_id,definitions,999))
    card=next(iter(s.cards.values()));assert card.card_kind==d.card_kind and card.acquisition_cost==999
    monkeypatch.setattr('uuid.uuid4',lambda:SimpleNamespace(hex='collision'))
    s.cards['machine-collision']=replace(card,card_id='machine-collision')
    rejected(s,BuyCommonSupplyCard('machine.processor',definitions,10))


def test_duplicate_placements_and_corrupt_freight_reference_reject_atomically(definitions):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'machine.processor')[0];install(s,definitions,cid)
    s.halls['h'].slots[1].card_id=cid
    rejected(s,ReturnMachinesToInventory((cid,)))
    s.halls['h'].slots[0].card_id=None;s.halls['h'].slots[1].card_id=None
    s.freight.outbound_shipments['corrupt']=OutboundFreightShipment('corrupt','market',freight_card_id=cid,quantity=5,remaining_seconds=10)
    rejected(s,InstallCardInHall('h',0,cid,'factory'))


def test_retained_partial_cycle_requires_inputs_power_and_space_after_reinstall(definitions):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'machine.processor')[0];install(s,definitions,cid)
    d=definitions['machine.processor'];p=next(p for p in d.available_production_options if p.input_resources)
    cycle=p.cycle_seconds_for(d);s.machine_production[cid]=MachineProductionState(cid,p.output_resource,p.production_id,cycle*.5,'running')
    ReturnMachinesToInventory((cid,)).apply(s);install(s,definitions,cid)
    engine=SimulationEngine(definitions,utc_now=lambda:1792324800.)
    for rid in p.input_resources:s.ensure_resource(rid)
    assert not engine.advance_time(s,cycle).outputs and s.machine_production[cid].progress_seconds==cycle*.5
    for rid in p.input_resources:s.resources[rid].amount=100
    assert not engine.advance_time(s,cycle).outputs and s.machine_production[cid].status=='no_power'
    solar=buy_common_supply_cards(s,definitions,'energy.solar_array')[0];install(s,definitions,solar)
    definitions=dict(definitions);definitions['energy.solar_array']=replace(definitions['energy.solar_array'],base_power_output=1e9)
    engine=SimulationEngine(definitions,utc_now=lambda:1792324800.)
    s.warehouse_capacity=1
    assert not engine.advance_time(s,cycle).outputs and s.machine_production[cid].progress_seconds==cycle*.5
    s.warehouse_capacity=1e9
    assert engine.advance_time(s,cycle*.5).outputs[p.output_resource]==pytest.approx(p.output_amount_for(d))


def test_unplaced_energy_consumes_no_fuel_and_reinstallation_resumes_normal_rate(definitions):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'energy.coal_power_plant')[0];install(s,definitions,cid)
    s.ensure_resource('coal').amount=1000;engine=SimulationEngine(definitions,utc_now=lambda:1792324800.)
    engine.advance_time(s,10);after_running=s.resources['coal'].amount
    assert after_running<1000
    ReturnMachinesToInventory((cid,)).apply(s);engine.advance_time(s,100)
    assert s.resources['coal'].amount==after_running
    install(s,definitions,cid);engine.advance_time(s,10)
    assert s.resources['coal'].amount==pytest.approx(2*after_running-1000)


def test_idle_freight_retains_route_but_only_installed_vehicle_can_depart(definitions):
    s=company(definitions);cid=buy_common_supply_cards(s,definitions,'freight.truck')[0];install(s,definitions,cid)
    s.ensure_resource('iron_ore');s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    ReturnMachinesToInventory((cid,)).apply(s);s.resources['iron_ore'].amount=100
    engine=SimulationEngine(definitions,utc_now=lambda:1792324800.);engine.advance_time(s,100)
    assert not s.freight.outbound_shipments and s.resources['iron_ore'].amount==100
    install(s,definitions,cid);engine.advance_time(s,0)
    assert len(s.freight.outbound_shipments)==1
    shipment=next(iter(s.freight.outbound_shipments.values()))
    assert shipment.freight_card_id==cid and shipment.quantity>0
    rejected(s,ReturnMachinesToInventory((cid,)))


def test_actual_shared_state_reset_clears_inventory_and_load_restores_it(definitions):
    from production_zero.ui.main_window import _copy_state
    s=company(definitions);bus=CommandBus(s)
    for did in ('machine.processor','energy.solar_array','freight.truck'):
        bus.dispatch(BuyCommonSupplyCard(did,definitions,2))
    saved=frozen(s);original_identity=id(s)
    assert len(s.cards)==6 and len(s.completed_card_operations)==3
    _copy_state(s,GameState(2026))
    assert id(s)==original_identity and not s.cards and not s.completed_card_operations and not s.machine_production
    _copy_state(s,deserialize_game_state(saved))
    assert id(s)==original_identity and frozen(s)==saved
    assert sum(stack.quantity for stack in s.inventory_card_stacks())==6
