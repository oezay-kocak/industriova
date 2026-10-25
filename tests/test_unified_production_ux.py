"""Interaction and persistence checks for the unified production pass."""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QScrollArea, QApplication
from test_ui_polish_interactions import app, window, board, click, install
from production_zero.ui.factory_view_v2 import FactoryV2LockedLine, FactoryV2BuildSlot
from production_zero.ui.game_ui import GameButton
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.core.commands import PauseProductionScope, PauseFreightScope
from production_zero.core.production_pause import effective_card_paused
from test_ui_polish_interactions import modal, press_dialog
from production_zero.ui.freight_view import FreightView


@pytest.mark.parametrize('size', [(1366,768),(1600,980),(1920,1080)])
@pytest.mark.parametrize('name', ['Resources','Factory','Energy'])
def test_last_expansion_fully_visible_without_runtime_scroll_jump(window, size, name):
    window.resize(*size); b=board(window,name); QTest.qWait(30)
    scroll=b.findChild(QScrollArea,'factoryV2Scroll')
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum()); QTest.qWait(20)
    last=b.findChildren(FactoryV2LockedLine)[-1]
    button=last._unlock_button
    bottom=button.mapTo(scroll.viewport(),button.rect().bottomRight()).y()
    assert bottom < scroll.viewport().height()-6
    old=scroll.verticalScrollBar().value(); b.refresh_runtime(); QTest.qWait(20)
    assert scroll.verticalScrollBar().value()==old


def test_building_pause_preserves_manual_line_and_machine_flags(window):
    b=board(window,'Factory'); one=install(window,b,0)
    b._unlock_line(b._units[b._selected_hall_id].production_lines[1].line_id)
    # Let the existing 0/50/150-ms cached scroll restoration finish before
    # making a new explicit scroll gesture, including high-DPI layout work.
    QTest.qWait(220)
    index=b._units[b._selected_hall_id].production_lines[1].slot_indexes[0]
    b._factory_v2_scroll.ensureWidgetVisible(next(x for x in b.findChildren(FactoryV2BuildSlot) if x.isVisible() and x._release_slot_index==index)); QTest.qWait(30); two=install(window,b,index)
    hall=b._units[b._selected_hall_id]; line=hall.production_lines[1]
    b._command_bus.dispatch(PauseProductionScope('factory',hall.hall_id,True,line.line_id))
    assert effective_card_paused(b._state,two) and not effective_card_paused(b._state,one)
    click(window,b.findChild(GameButton,'buildingPauseButton'))
    assert effective_card_paused(b._state,one) and line.paused
    click(window,b.findChild(GameButton,'buildingPauseButton'))
    assert not effective_card_paused(b._state,one) and effective_card_paused(b._state,two)
    assert not b._state.cards[two].paused
    loaded=deserialize_game_state(serialize_game_state(b._state))
    assert loaded.halls[hall.hall_id].production_lines[1].paused
    assert effective_card_paused(loaded,two) and not effective_card_paused(loaded,one)


def test_pause_new_schema_defaults_preserve_existing_machine_pause(window):
    b=board(window,'Energy'); cid=install(window,b)
    p=serialize_game_state(b._state);p['state_schema_version']=5
    for units in ('halls','resource_sites','energy_plants'):
        for unit in p[units].values():
            unit.pop('paused',None)
            for line in unit['production_lines']:line.pop('paused',None)
    for unit in p['freight']['facilities'].values():
        unit.pop('paused',None);unit.pop('paused_lines',None)
    loaded=deserialize_game_state(p)
    assert not effective_card_paused(loaded,cid)
    assert not next(iter(loaded.freight.facilities.values())).paused


def test_keyboard_templates_buy_new_machines_and_do_not_capture_text_fields(window):
    from PySide6.QtWidgets import QLineEdit
    b=board(window,'Factory');cid=install(window,b);b._state.cash.amount=2000
    card=b._slot_widgets[0];click(window,card,pos=QPoint(10,10));card.setFocus()
    QTest.keyClick(card,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
    assert len(b._configuration_clipboard)==1
    line=b._units[b._selected_hall_id].production_lines[0]
    b._focused_line_id=line.line_id;cash=b._state.cash.amount
    modal(lambda d:press_dialog(d,d.accept_button))
    QTest.keyClick(card,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier);QTest.qWait(30)
    assert b._state.cash.amount==cash-275
    assert len([s for s in b._units[b._selected_hall_id].slots if s.card_id])==2
    field=QLineEdit(b);field.show();field.setText('editable text');field.selectAll();field.setFocus()
    saved=b._configuration_clipboard;QTest.keyClick(field,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
    assert b._configuration_clipboard==saved
    assert __import__('PySide6.QtWidgets',fromlist=['QApplication']).QApplication.clipboard().text()=='editable text'
    field.deleteLater()


def test_line_context_copies_actual_machines_and_paste_requires_confirmation(window):
    from PySide6.QtCore import QTimer
    from production_zero.ui.factory_view_v2 import FactoryV2TrackPanel
    from PySide6.QtWidgets import QApplication
    b=board(window,'Factory');one=install(window,b,0);two=install(window,b,1);b._state.cash.amount=2000
    hall=b._units[b._selected_hall_id]
    b._unlock_line(hall.production_lines[1].line_id)
    QTest.qWait(60)
    lines=b.findChildren(FactoryV2TrackPanel)
    modal(lambda d:press_dialog(d,next(x for x in d.findChildren(GameButton) if x.text()=='COPY LINE')))
    click(window,lines[0],button=Qt.MouseButton.RightButton,pos=QPoint(800,15))
    assert len(b._configuration_clipboard)==2
    b._factory_v2_scroll.ensureWidgetVisible(lines[1]);QTest.qWait(30)
    before=set(b._state.cards);cash=b._state.cash.amount
    def choose_paste(d):
        def approve():
            purchase=QApplication.activeModalWidget();assert '2 new machines' in purchase.message.text();press_dialog(purchase,purchase.accept_button)
        QTimer.singleShot(60,approve)
        press_dialog(d,next(x for x in d.findChildren(GameButton) if x.text()=='PASTE MACHINES'))
    modal(choose_paste);click(window,lines[1],button=Qt.MouseButton.RightButton,pos=QPoint(800,15))
    assert len(set(b._state.cards)-before)==2 and b._state.cash.amount==cash-550
    assert hall.slots[0].card_id==one and hall.slots[1].card_id==two


def test_first_recipe_unlock_repaints_the_existing_machine_card(window):
    from PySide6.QtCore import QObject,QEvent
    b=board(window,'Factory');install(window,b);card=b._slot_widgets[0]
    QTest.qWait(80)
    class Paints(QObject):
        count=0
        def eventFilter(self,obj,event):
            if event.type()==QEvent.Type.Paint:self.count+=1
            return False
    spy=Paints(card);card.installEventFilter(spy)
    assert not card._production_change_available()
    before=card.grab().toImage()
    b._state.production_progress.unlocked_production_ids.add('recipe.processor.iron')
    b.refresh_runtime();QTest.qWait(35)
    assert b._slot_widgets[0] is card and card._production_change_available()
    assert spy.count>0, 'A new recipe must repaint its existing card without a structural rebuild.'
    after=card.grab().toImage()
    assert before!=after, 'The cached card image must show the newly available recipe control.'
    click(window,card,pos=card._resource_control_rect().center().toPoint())
    assert b.findChild(__import__('PySide6.QtWidgets',fromlist=['QFrame']).QFrame,'productionSelectionView').isVisible()


def test_freight_lines_group_selection_routes_and_scope_pause(window):
    from production_zero.core.commands import InstallFreightCard, AssignFreightVehicles, ExpandFreightFacility
    from production_zero.ui.freight_lines import ordered_selection
    f=board(window,'Freight');s=f._state;s.cash.amount=100000
    ids=('starter-truck-common-001','starter-truck-common-002')
    for i,cid in enumerate(ids):f._command_bus.dispatch(InstallFreightCard('garage-1',i,cid,f._definitions))
    f.refresh();QTest.qWait(30)
    widgets=[x for x in f._slot_interaction._cards() if x._freight_vehicle]
    click(window,widgets[0],pos=QPoint(10,10));click(window,widgets[1],pos=QPoint(10,10),modifiers=Qt.KeyboardModifier.ControlModifier)
    assert ordered_selection(f)==ids and all(x.property('selected') for x in widgets)
    f._command_bus.dispatch(AssignFreightVehicles(ids,'iron_ore','market'))
    assert all(s.freight.assignments[cid].resource_id=='iron_ore' for cid in ids)
    click(window,f.findChild(GameButton,'sectorPauseButton'))
    assert s.freight.facilities['garage-1'].paused_lines=={0}
    click(window,f.findChild(GameButton,'buildingPauseButton'));click(window,f.findChild(GameButton,'buildingPauseButton'))
    assert s.freight.facilities['garage-1'].paused_lines=={0} and all(not s.cards[cid].paused for cid in ids)
    for _ in range(6):f._command_bus.dispatch(ExpandFreightFacility('garage-1'))
    f.refresh();QTest.qWait(20)
    assert f.findChild(GameButton,'unlockFreightLineButton') is not None
    assert len(f.findChildren(GameButton,'sectorPauseButton'))==2


def test_freight_context_routes_apply_to_exact_selected_group(window):
    from production_zero.core.commands import InstallFreightCard
    from production_zero.ui.freight_view import FreightAssignmentResourceTile
    f=board(window,'Freight');ids=('starter-truck-common-001','starter-truck-common-002')
    for i,cid in enumerate(ids):f._command_bus.dispatch(InstallFreightCard('garage-1',i,cid,f._definitions))
    f.refresh();QTest.qWait(25);cards=f._slot_interaction._cards()
    click(window,cards[0],pos=QPoint(10,10));click(window,cards[1],pos=QPoint(10,10),modifiers=Qt.KeyboardModifier.ControlModifier)
    modal(lambda d:press_dialog(d,next(x for x in d.findChildren(GameButton,'machineContextAction') if x.text()=='ROUTE / DELIVERY TARGET')))
    click(window,cards[0],button=Qt.MouseButton.RightButton,pos=QPoint(10,10))
    assert f._route_group==ids
    tile=next(x for x in f.findChildren(FreightAssignmentResourceTile) if x.isVisible())
    click(window,tile)
    assert not any(cid in f._state.freight.assignments for cid in ids)
    f._choose_assignment_destination('market')
    QTest.mouseClick(f._route_confirm,Qt.MouseButton.LeftButton);QApplication.processEvents()
    assert all(cid in f._state.freight.assignments for cid in ids)
    assert len({(f._state.freight.assignments[cid].resource_id,f._state.freight.assignments[cid].destination_kind) for cid in ids})==1


def test_freight_group_pointer_drag_moves_only_selected_vehicles(window):
    from production_zero.core.commands import InstallFreightCard,ExpandFreightFacility
    window.resize(1920,1080);f=board(window,'Freight');f._state.cash.amount=100000
    ids=('starter-truck-common-001','starter-truck-common-002')
    for i,cid in enumerate(ids):f._command_bus.dispatch(InstallFreightCard('garage-1',i,cid,f._definitions))
    for _ in range(3):f._command_bus.dispatch(ExpandFreightFacility('garage-1'))
    f.refresh();QTest.qWait(30)
    cards={x._freight_destination[1]:x for x in f._slot_interaction._cards()}
    click(window,cards[0],pos=QPoint(10,10));click(window,cards[1],pos=QPoint(10,10),modifiers=Qt.KeyboardModifier.ControlModifier)
    start=cards[0].mapTo(window,QPoint(20,30));end=cards[3].mapTo(window,QPoint(20,30))
    QTest.mousePress(window.windowHandle(),Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(window.windowHandle(),end,delay=20);QTest.mouseRelease(window.windowHandle(),Qt.MouseButton.LeftButton,pos=end);QTest.qWait(40)
    slots=f._state.freight.facilities['garage-1'].slots
    assert [slots[i].card_id for i in (0,1,3,4)]==[None,None,*ids]


@pytest.mark.parametrize('size',[(1366,768),(1600,980),(1920,1080)])
def test_largest_research_hover_uses_canonical_products_and_stays_inside_window(window,size):
    from production_zero.core.research import research_domains, research_catalog
    from production_zero.ui.research_hover import ResearchHover, hover_products
    from PySide6.QtWidgets import QLabel
    window.resize(*size);r=board(window,'Research')
    domains=research_domains();domain=max(set(domains.values()),key=lambda d:list(domains.values()).count(d));tid='industry.'+domain
    popup=ResearchHover(window);popup.display(r.navigation_buttons[tid],window._session_state,tid);QTest.qWait(25)
    assert {rid for rid,_,_ in hover_products(window._session_state,tid)}=={rid for rid,d in domains.items() if d==domain}
    assert window.rect().contains(popup.geometry())
    assert len(popup.findChildren(QLabel,'researchHoverProduct'))==list(domains.values()).count(domain)
    assert popup.findChild(QScrollArea,'researchHoverProducts').widgetResizable()
    popup.close();popup.deleteLater()
