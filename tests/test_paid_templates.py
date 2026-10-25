from dataclasses import replace
from importlib.resources import files
import pytest
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity, CardKind
from production_zero.core.commands import CommandBus, ExpandFreightFacility, PauseFreightScope, AssignFreightVehicles
from production_zero.core.production_templates import MachineTemplate, copy_templates, quote_templates, PurchaseTemplates
from production_zero.core.production_pause import effective_card_paused
from production_zero.core.state import GameState, FactoryHall
from production_zero.core.freight import FreightSlot
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state


@pytest.fixture
def fixture():
    definitions=load_card_definitions(files('production_zero.data')/'game_definitions.json')
    state=GameState(rng_seed=71);state.cash.amount=100000
    state.halls['h']=FactoryHall('h','Factory',6)
    state.resource_sites['s']=FactoryHall('s','Mining',1,board_kind='resources',specialization='machine.extractor')
    state.energy_plants['p']=FactoryHall('p','Energy',1,board_kind='energy')
    return state,definitions


@pytest.mark.parametrize('quantity',[1,2,3])
def test_paid_template_mk50_legendary_produces_distinct_common_mk1(fixture,quantity):
    state,definitions=fixture;unit=state.halls['h'];line=unit.production_lines[0]
    template=tuple(MachineTemplate('machine.processor') for _ in range(quantity))
    source=replace(create_card_instance('old','machine.processor',CardKind.MACHINE,Rarity.LEGENDARY),mk_level=50,upgrade_investment=9000)
    state.cards['old']=source;unit.slots[unit.production_lines[1].slot_indexes[0]].card_id='old'
    copied=copy_templates(state,('old',));assert copied[0].definition_id==template[0].definition_id
    _,free,total,_=quote_templates(state,definitions,template,'factory','h',line.line_id)
    before=state.cash.amount;CommandBus(state).dispatch(PurchaseTemplates(template,'factory','h',line.line_id,definitions,total))
    new=[state.cards[unit.slots[i].card_id] for i in free[:quantity]]
    assert len({c.card_id for c in new})==quantity and all(c.card_id!='old' and c.mk_level==1 and c.rarity==Rarity.COMMON and c.upgrade_investment==0 and c.output_bonus_percent==0 for c in new)
    assert state.cash.amount==before-total and state.cards['old']==source
    loaded=deserialize_game_state(serialize_game_state(state));assert set(loaded.cards)==set(state.cards)


@pytest.mark.parametrize('problem',['money','slots','type','recipe','quote'])
def test_paste_rejection_is_atomic(fixture,problem):
    state,definitions=fixture;unit=state.halls['h'];line=unit.production_lines[0];templates=(MachineTemplate('machine.processor'),)
    _,_,price,_=quote_templates(state,definitions,templates,'factory','h',line.line_id)
    if problem=='money':state.cash.amount=0
    if problem=='slots':templates=templates*4;price*=4
    if problem=='type':templates=(MachineTemplate('machine.extractor'),)
    if problem=='recipe':templates=(MachineTemplate('machine.processor','missing-recipe'),)
    if problem=='quote':price+=1
    before=serialize_game_state(state)
    with pytest.raises(ValueError):CommandBus(state).dispatch(PurchaseTemplates(templates,'factory','h',line.line_id,definitions,price))
    assert serialize_game_state(state)==before


def test_freight_paid_copy_has_no_shipments_or_historical_values(fixture):
    from production_zero.core.freight import FreightAssignment, OutboundFreightShipment
    from production_zero.core.resources import ResourceStock
    state,definitions=fixture;facility=state.freight.facilities['garage-1'];state.resources['iron_ore']=ResourceStock(100,1000)
    source=create_card_instance('old','freight.truck',CardKind.FREIGHT,Rarity.COMMON);state.cards['old']=replace(source,mk_level=50)
    facility.slots[0].card_id='old';state.freight.assignments['old']=FreightAssignment('iron_ore','market')
    state.freight.outbound_shipments['existing']=OutboundFreightShipment('existing','market',resource_id='iron_ore',quantity=12,freight_card_id='old',remaining_seconds=50)
    templates=copy_templates(state,('old',));_,_,price,_=quote_templates(state,definitions,templates,'freight','garage-1',0)
    CommandBus(state).dispatch(PurchaseTemplates(templates,'freight','garage-1',0,definitions,price))
    cid=facility.slots[1].card_id;assert cid!='old' and state.cards[cid].mk_level==1
    assert state.freight.assignments[cid].resource_id=='iron_ore'
    assert list(state.freight.outbound_shipments)==['existing'] and state.freight.outbound_shipments['existing'].quantity==12
    assert state.resources['iron_ore'].amount==100


def test_freight_lines_cost_curve_and_pause_persist_without_reordering(fixture):
    state,definitions=fixture;unit=state.freight.facilities['garage-1'];before=state.cash.amount
    for _ in range(6):CommandBus(state).dispatch(ExpandFreightFacility('garage-1'))
    assert state.cash.amount==before-(sum(60*n for n in range(1,6))+900)
    card=create_card_instance('truck','freight.truck',CardKind.FREIGHT,Rarity.COMMON);state.cards['truck']=card;unit.slots[8].card_id='truck'
    bus=CommandBus(state);bus.dispatch(PauseFreightScope('garage-1',True,1));bus.dispatch(PauseFreightScope('garage-1',True));bus.dispatch(PauseFreightScope('garage-1',False))
    assert unit.paused_lines=={1} and not card.paused and effective_card_paused(state,'truck')
    payload=serialize_game_state(state);loaded=deserialize_game_state(payload)
    assert [s.card_id for s in loaded.freight.facilities['garage-1'].slots]==[s.card_id for s in unit.slots]
    assert loaded.freight.facilities['garage-1'].paused_lines=={1}
    assert serialize_game_state(deserialize_game_state(serialize_game_state(loaded)))==serialize_game_state(loaded)


def test_schema5_freight_migration_keeps_all_vehicles_routes_cargo_and_investment(fixture):
    from production_zero.core.freight import FreightAssignment, OutboundFreightShipment
    state,definitions=fixture;unit=state.freight.facilities['garage-1']
    for _ in range(5):CommandBus(state).dispatch(ExpandFreightFacility('garage-1'))
    for i,slot in enumerate(unit.slots):
        cid=f'legacy-vehicle-{i}';state.cards[cid]=replace(create_card_instance(cid,'freight.truck',CardKind.FREIGHT,Rarity.RARE),mk_level=17)
        slot.card_id=cid;state.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    state.freight.outbound_shipments['delivery']=OutboundFreightShipment('delivery','market',resource_id='iron_ore',quantity=31,freight_card_id='legacy-vehicle-0',remaining_seconds=47)
    payload=serialize_game_state(state);payload['state_schema_version']=5
    for facility in payload['freight']['facilities'].values():
        for key in ('paused','paused_lines','line_capacity'):facility.pop(key,None)
    loaded=deserialize_game_state(payload);migrated=loaded.freight.facilities['garage-1']
    assert len(migrated.slots)==8 and migrated.line_capacity==8
    assert [s.card_id for s in migrated.slots]==[s.card_id for s in unit.slots]
    assert all(loaded.cards[cid]==card for cid,card in state.cards.items())
    assert loaded.freight.assignments==state.freight.assignments
    assert loaded.freight.outbound_shipments['delivery'].source_facility_id=='garage-1'
    assert loaded.freight.outbound_shipments['delivery']==replace(state.freight.outbound_shipments['delivery'],source_facility_id='garage-1')
    assert loaded.cash.amount==state.cash.amount and migrated.building_investment==unit.building_investment
    assert serialize_game_state(deserialize_game_state(serialize_game_state(loaded)))==serialize_game_state(loaded)
