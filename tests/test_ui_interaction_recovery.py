"""Regression of real widget gestures; the native OLE run is logged separately."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import replace
import pytest
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QLabel, QLineEdit, QComboBox, QScrollArea
from PySide6.QtTest import QTest
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2, FactoryV2BuildSlot, FactoryV2LockedSlot
from production_zero.ui.factory_view import FactoryCardSelectionTile, ProductionSelectionTile
from production_zero.ui.freight_view import FreightView, FreightSelectionCard
from production_zero.ui.game_ui.widgets import GameButton
from production_zero.ui.supply_view import SupplyView
from production_zero.core.supply import common_supply_offers
from production_zero.core.freight import FreightFacility, OutboundFreightShipment, move_freight_vehicle
from production_zero.persistence.dev_save_store import serialize_game_state, deserialize_game_state

@pytest.fixture(scope="module")
def app():
    a=QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    return a

@pytest.fixture
def window(app):
    w=MainWindow(development_mode=False);w.resize(1366,768);w.show();QTest.qWait(50)
    for b in w.findChildren(ProductionBoardViewV2):b.pause_simulation()
    yield w
    w.close();w.deleteLater();QTest.qWait(20)

def click(w, widget, modifiers=Qt.KeyboardModifier.NoModifier, pos=None):
    point=widget.mapTo(w,pos or widget.rect().center())
    assert w.childAt(point) is not None
    QTest.mouseClick(w.windowHandle(),Qt.MouseButton.LeftButton,modifiers,point)
    QTest.qWait(20)

def board(w, name):
    tabs=w.findChild(QTabWidget,"mainTabs");i=next(i for i in range(tabs.count()) if tabs.tabText(i)==name)
    nav=tabs._navigation_bar;click(w,nav,pos=nav.tabRect(i).center())
    return tabs.currentWidget()

def install(w, b, index=0):
    target=next(c for c in b.findChildren(FactoryV2BuildSlot) if c.isVisible() and c._release_slot_index==index)
    click(w,target);tile=b.findChild(FactoryCardSelectionTile);cid=tile.property("cardId");click(w,tile)
    assert b._units[b._selected_hall_id].slots[index].card_id==cid
    return cid

def truck(w):
    f=board(w,"Freight")
    click(w,next(c for c in f.findChildren(QWidget,"freightSlotCard") if c.property("slotState")=="empty"))
    tile=f.findChild(FreightSelectionCard);click(w,tile)
    cid=next(s.card_id for u in f._state.freight.facilities.values() for s in u.slots if s.card_id)
    return f,cid

def test_open_picker_refreshes_on_matching_unlock_without_losing_filter_or_widgets(window):
    b=board(window,"Factory");cid=install(window,b)
    card = b._slot_widgets[0]
    def choose_recipe():
        d=QApplication.activeModalWidget()
        click(d,next(c for c in d.findChildren(GameButton,'machineContextAction') if c.text()=='Recipe'))
    QTimer.singleShot(60,choose_recipe)
    QTest.mouseClick(window.windowHandle(),Qt.MouseButton.RightButton,Qt.KeyboardModifier.NoModifier,card.mapTo(window,QPoint(10,10)))
    QTest.qWait(80)
    search=b.findChild(QLineEdit,"productionSearchInput");category=b.findChild(QComboBox,"productionCategoryFilter")
    search.setText("i");QTest.qWait(20)
    before={c.property("productionId"):c for c in b.findChildren(ProductionSelectionTile)}
    host=b._production_selection_grid_host
    # Isolated progression boundary, using the actual engine's production unlock pass.
    b._state.production_progress.lifetime_produced['iron_ore']=120
    b._simulation.advance_time(b._state,1)
    b.refresh_runtime();QTest.qWait(30)
    iron=next(c for c in b.findChildren(ProductionSelectionTile) if c.property("productionId")=="recipe.processor.iron")
    assert iron.isEnabled() and search.text()=="i" and category.currentText()=="All"
    assert b._production_selection_grid_host is host
    for key,c in before.items():
        if key in {t.property("productionId") for t in b.findChildren(ProductionSelectionTile)}:
            assert next(t for t in b.findChildren(ProductionSelectionTile) if t.property("productionId")==key) is c
    b.refresh_runtime();assert b._production_selection_grid_host is host
    click(window,iron)
    assert b._state.machine_production[cid].selected_production_id=='recipe.processor.iron'

@pytest.mark.parametrize('name',['Factory','Resources','Energy'])
def test_only_next_locked_slot_can_buy_even_after_cash_refresh(window,name):
    b=board(window,name);hall=b._units[b._selected_hall_id];line=hall.production_lines[0]
    start=len(line.slot_indexes)
    def tiles():return sorted([c for c in b.findChildren(FactoryV2LockedSlot) if c.isVisible() and c.property('lineId')==line.line_id],key=lambda c:c.property('slotNumber'))
    first,later=tiles()[:2];cash=b._state.cash.amount;indexes=list(line.slot_indexes)
    click(window,later);assert b._state.cash.amount==cash and line.slot_indexes==indexes
    b._state.cash.amount=1e6;b.refresh_runtime();first,later=tiles()[:2]
    assert first.property('unlockEnabled') and not later.property('unlockEnabled')
    cost=first.property('unlockCost');cash=b._state.cash.amount;click(window,first)
    assert b._state.cash.amount==cash-cost and len(line.slot_indexes)==start+1
    first,later=tiles()[:2];assert first.property('slotNumber')==start+2
    assert first.property('unlockEnabled') and not later.property('unlockEnabled')
    b._state.cash.amount=0;b.refresh_runtime();assert not first.property('unlockEnabled')
    b._state.cash.amount=1e6;b.refresh_runtime();assert first.property('unlockEnabled') and not later.property('unlockEnabled')

@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
@pytest.mark.parametrize('name',['Factory','Resources','Energy'])
def test_toolbar_is_single_compact_row(window,size,name):
    window.resize(*size);b=board(window,name)
    assert b.findChild(QWidget,'productionSelectionToolbar') is None
    buttons=b.findChildren(GameButton,'buildingPauseButton')
    assert buttons and all(x.width()==76 and x.height()==38 for x in buttons)
    assert all(x.mapTo(b,x.rect().bottomRight()).x()<b.width() for x in buttons)

@pytest.mark.parametrize('case,title',[('cash','Insufficient Cash'),('full',None),('facility',None),('quantity',None),('limit','Purchase Limit Reached')])
def test_supply_distinct_failure_reasons_and_no_mutations(window,case,title):
    v=window.findChild(SupplyView);state=v._state
    offer=next(o for o in common_supply_offers(v._definitions) if o.definition_id=='machine.extractor');source='common';qty=1
    if case=='cash':state.cash.amount=0
    elif case=='full':state.resource_sites['site-1'].slots[0].card_id='test-drill-common-001'
    elif case=='facility':state.resource_sites['site-1'].specialization='machine.drilling'
    elif case=='quantity':qty=2
    elif case=='limit':
        source='machine_daily';offer=state.supply.machine_daily_offers[0];state.supply.machine_daily_purchased_period_index=state.supply.machine_daily_period_index
    before=serialize_game_state(state)
    problem=v._purchase_problem(offer,source,qty)
    assert (problem[0] if problem else None)==title
    assert serialize_game_state(state)==before

@pytest.mark.parametrize('invalid',['occupied','wrong_facility','locked','busy'])
def test_freight_move_rejects_before_any_mutation(window,invalid):
    f,cid=truck(window);s=f._state;u=s.freight.facilities['garage-1'];target='garage-1';index=1
    if invalid=='occupied':u.slots[1].card_id='starter-truck-common-002'
    elif invalid=='wrong_facility':s.freight.facilities['rail-test']=FreightFacility('rail-test','Rail','rail_station');target='rail-test'
    elif invalid=='locked':index=99
    else:s.freight.outbound_shipments['busy']=OutboundFreightShipment('busy','market',freight_card_id=cid,remaining_seconds=30)
    before=serialize_game_state(s)
    if invalid=='occupied':
        # P4 deliberately permits compatible occupied destinations.
        counterpart=u.slots[1].card_id
        move_freight_vehicle(s,f._definitions,cid,target,index)
        assert u.slots[0].card_id==counterpart and u.slots[1].card_id==cid
        after=serialize_game_state(s)
        assert after['cards']==before['cards'] and after['cash']==before['cash']
        assert after['freight']['outbound_shipments']==before['freight']['outbound_shipments']
        return
    with pytest.raises(ValueError):move_freight_vehicle(s,f._definitions,cid,target,index)
    assert serialize_game_state(s)==before

def test_complete_qt_mouse_drag_preserves_vehicle_route_identity_and_save(window):
    f,cid=truck(window);state=f._state
    from production_zero.core.commands import AssignFreightCard
    f._command_bus.dispatch(AssignFreightCard(cid,'iron_ore','market'))
    original=state.cards[cid];assignment=state.freight.assignments[cid]
    source=next(c for c in f.findChildren(QWidget,'freightSlotCard') if getattr(c,'_freight_vehicle',None)==cid)
    target=next(c for c in f.findChildren(QWidget,'freightSlotCard') if c.property('slotIndex')==1)
    start=source.mapTo(window,QPoint(30,70));end=target.mapTo(window,target.rect().center())
    QTest.mousePress(window.windowHandle(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(window.windowHandle(),end,30)
    assert target.property('freightDropTarget')
    QTest.mouseRelease(window.windowHandle(),Qt.MouseButton.LeftButton,pos=end);QTest.qWait(30)
    assert state.freight.facilities['garage-1'].slots[0].card_id is None
    assert state.freight.facilities['garage-1'].slots[1].card_id==cid
    assert state.cards[cid] is original and state.freight.assignments[cid] is assignment
    loaded=deserialize_game_state(serialize_game_state(state))
    assert loaded.freight.facilities['garage-1'].slots[1].card_id==cid
    assert loaded.cards[cid]==original and loaded.freight.assignments[cid]==assignment

def test_freight_future_preview_is_bounded_and_sequential(window):
    from production_zero.ui.game_ui import GameButton
    f=board(window,'Freight');u=f._state.freight.facilities['garage-1'];f._state.cash.amount=20000;f.refresh_runtime()
    # The next line waits for every slot in the preceding row.
    line=f.findChild(GameButton,'unlockFreightLineButton');assert not line.isEnabled()
    cards=sorted([c for c in f.findChildren(QWidget,'freightSlotCard') if c.property('slotState')=='locked'],key=lambda c:c.property('slotIndex'))
    assert [c.property('slotIndex') for c in cards]==[3,4,5,6,7]
    assert [c.property('clickEnabled') for c in cards]==[True,False,False,False,False]
    QTest.qWait(80);f._slots_scroll.ensureWidgetVisible(cards[0]);QTest.qWait(30)
    cash=f._state.cash.amount;price=cards[0].property('unlockCost');click(window,cards[0])
    assert len(u.slots)==4 and f._state.cash.amount==cash-price
    cards=sorted([c for c in f.findChildren(QWidget,'freightSlotCard') if c.property('slotState')=='locked'],key=lambda c:c.property('slotIndex'))
    assert len(cards)==4 and cards[0].property('slotIndex')==4
    assert [c.property('clickEnabled') for c in cards]==[True,False,False,False]
    QTest.qWait(80);f._slots_scroll.ensureWidgetVisible(cards[-1]);QTest.qWait(30)
    cash=f._state.cash.amount;click(window,cards[-1]);assert f._state.cash.amount==cash



def test_cancelled_freight_drag_does_not_change_any_slot(window):
    f,cid=truck(window);before=serialize_game_state(f._state)
    source=next(c for c in f.findChildren(QWidget,'freightSlotCard') if getattr(c,'_freight_vehicle',None)==cid)
    start=source.mapTo(window,QPoint(30,70));end=start+QPoint(40,0)
    QTest.mousePress(window.windowHandle(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(window.windowHandle(),end,30)
    QTest.keyClick(source,Qt.Key.Key_Escape)
    QTest.mouseRelease(window.windowHandle(),Qt.MouseButton.LeftButton,pos=end)
    assert serialize_game_state(f._state)==before

def test_paused_delivery_finishes_once_and_runtime_overview_updates(window):
    f,cid=truck(window);s=f._state
    from production_zero.core.commands import AssignFreightCard,PauseMachines
    f._command_bus.dispatch(AssignFreightCard(cid,'iron_ore','market'))
    engine=next(b for b in window.findChildren(ProductionBoardViewV2) if b._board_config.board_kind=='factory')._simulation
    engine.advance_time(s,1);f.refresh_runtime();QTest.qWait(20)
    assert len(s.freight.outbound_shipments)==1
    f._command_bus.dispatch(PauseMachines((cid,),True))
    engine.advance_time(s,61);f.refresh_runtime();QTest.qWait(20)
    cash=s.cash.amount
    assert not s.freight.outbound_shipments
    stage=f.findChild(QWidget,'freightFacilityHeader');stage.grab()
    assert '0 active shipments' in stage.property('facilityMeta')
    card=next(c for c in f.findChildren(QWidget,'freightSlotCard') if getattr(c,'_freight_vehicle',None)==cid)
    assert card.property('cardStatusText')=='PAUSED'
    engine.advance_time(s,61);assert s.cash.amount==cash and not s.freight.outbound_shipments
    f._command_bus.dispatch(PauseMachines((cid,),False));engine.advance_time(s,1)
    assert len(s.freight.outbound_shipments)==1
