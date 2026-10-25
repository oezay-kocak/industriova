"""Real board drag protocols, feedback coordinates and cleanup, offscreen Qt."""
import json
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QMimeData, Qt
from PySide6.QtGui import QDrag, QDropEvent, QMouseEvent, QWheelEvent, QCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget
from test_ui_interaction_recovery import app, window, board, truck
from test_industriova_release_ui import populated_factory
from production_zero.ui.freight_view import FreightView
from production_zero.ui.factory_view_v2 import FactoryV2MachineCard
from production_zero.ui.release_board import MACHINE_MIME
from production_zero.core.commands import InstallCardInHall, InstallFreightCard, UnlockProductionSlot
from production_zero.core.supply import buy_common_supply_cards
from production_zero.core.freight import OutboundFreightShipment, FreightSlot
from production_zero.persistence.sqlite_store import serialize_game_state


def drop(b, target, data):
    mime = QMimeData(); mime.setData(MACHINE_MIME,json.dumps(data).encode())
    event = QDropEvent(QPointF(20,70),Qt.DropAction.MoveAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    b.eventFilter(target,event)
    return event


@pytest.mark.parametrize('name,did', [('Factory','machine.processor'),('Resources','machine.extractor'),('Energy','energy.solar_array')])
def test_real_production_group_occupied_drop_and_selection(window, name, did):
    b = board(window,name); s=b._state
    s.cash.amount=1e12
    hall=b._units[b._selected_hall_id]
    line=hall.production_lines[0]
    # Legal expansion through the same command used by the board button.
    while len(line.slot_indexes)<4:
        UnlockProductionSlot(hall.hall_id,line.line_id,b._board_config.board_kind).apply(s)
    indexes=[i for line in hall.production_lines if line.unlocked for i in line.slot_indexes]
    ids=buy_common_supply_cards(s,b._definitions,did,4)
    for cid,index in zip(ids,indexes):InstallCardInHall(hall.hall_id,index,cid,b._board_config.board_kind).apply(s)
    b.refresh_view();QApplication.processEvents();b._selected_machines=set(ids[:2])
    before=dict(s.cards);before_state=serialize_game_state(s)
    data=b._machine_drag_payload(ids[:2])
    event=drop(b,b._slot_widgets[indexes[2]],data)
    assert event.isAccepted()
    assert [hall.slots[i].card_id for i in indexes[:4]]==[ids[2],ids[3],ids[0],ids[1]]
    assert b._selected_machines==set(ids[:2])
    assert all(s.cards[cid] is card for cid,card in before.items())
    assert serialize_game_state(s)['cash']==before_state['cash']


@pytest.mark.parametrize('case', ['session','token','source','off-grid','missing-origins','cancelled','superseded'])
def test_stale_production_drop_is_rejected_without_changes(window,monkeypatch,case):
    b,ids=populated_factory(window);hall=b._units[b._selected_hall_id]
    data=b._machine_drag_payload(ids[:2]);target=b._slot_widgets[2]
    if case=='session':data['session']=0
    if case=='token':data['token']='old'
    if case=='source':hall.slots[0].card_id,hall.slots[2].card_id=hall.slots[2].card_id,hall.slots[0].card_id
    if case=='off-grid':
        indexes=[i for line in hall.production_lines if line.unlocked for i in line.slot_indexes]
        target=next(w for w in b.findChildren(QWidget) if getattr(w,'_release_slot_index',None)==indexes[-1])
    if case=='missing-origins':data.pop('origins')
    if case=='cancelled':b._cancel_machine_drag()
    if case=='superseded':b._machine_drag_payload(ids[:2])
    messages=[];monkeypatch.setattr('production_zero.ui.release_board.inform',lambda *args:messages.append(args))
    before=serialize_game_state(b._state)
    assert not drop(b,target,data).isAccepted()
    assert serialize_game_state(b._state)==before and messages


def test_production_hotspot_uses_original_grip_and_cleans_after_native_loop(window,monkeypatch):
    b,ids=populated_factory(window);w=b._slot_widgets[0];w._drag_grip=QPoint(27,85)
    b._selected_machines=set(ids[:2]);b._update_selection_visuals();seen=[]
    original=w.grab().toImage();ratio=original.devicePixelRatio()
    pixel=QPoint(round(w.width()/2*ratio),round(w.height()/2*ratio))
    b._machine_feedback.highlight(w,'swap');QApplication.processEvents()
    assert w.grab().toImage().pixelColor(pixel)==original.pixelColor(pixel)
    b._machine_feedback.stop()
    def run(drag,*args):
        seen.append((drag.hotSpot(),drag.pixmap().deviceIndependentSize(),json.loads(bytes(drag.mimeData().data(MACHINE_MIME)))))
        assert b._machine_feedback.active
        return Qt.DropAction.IgnoreAction
    monkeypatch.setattr(QDrag,'exec',run)
    b._begin_machine_drag(w)
    assert seen[0][0]==QPoint(27,85) and seen[0][2]['ids']==list(ids[:2])
    assert not b._machine_feedback.active and not b._machine_feedback.timer.isActive()
    assert b._machine_drag_data is None


def freight_group(window,count=3,slots=16):
    f=board(window,'Freight');s=f._state;u=s.freight.facilities[f._selected_facility_id]
    u.slots=[FreightSlot(i) for i in range(slots)];u.slot_count=slots
    ids=buy_common_supply_cards(s,f._definitions,'freight.truck',count)
    for index,cid in enumerate(ids):InstallFreightCard(u.facility_id,index,cid,f._definitions).apply(s)
    f.refresh();QApplication.processEvents()
    f._selected_vehicles=set(ids[:2]);f._slot_interaction.update_selection()
    source=next(w for w in f._slot_interaction._cards() if w._freight_vehicle==ids[0])
    target=next(w for w in f._slot_interaction._cards() if w._freight_destination[1]==2)
    return f,u,ids,source,target


def pointer_move(controller,widget,global_pos):
    point=widget.mapFromGlobal(global_pos)
    event=QMouseEvent(QEvent.Type.MouseMove,QPointF(point),QPointF(global_pos),Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
    controller.eventFilter(widget,event)


def start_freight(controller,source,target):
    QTest.mousePress(source,Qt.MouseButton.LeftButton,pos=QPoint(25,65))
    pointer_move(controller,source,target.mapToGlobal(QPoint(30,80)))
    assert controller.dragging and controller.feedback.ghost is not None


def release_freight(controller,source,position):
    event=QMouseEvent(QEvent.Type.MouseButtonRelease,QPointF(source.mapFromGlobal(position)),QPointF(position),Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier)
    controller.eventFilter(source,event)


def test_freight_group_ghost_follows_grip_and_swaps_occupied_and_empty(window):
    f,u,ids,source,target=freight_group(window)
    c=f._slot_interaction;before=serialize_game_state(f._state);start_freight(c,source,target)
    assert serialize_game_state(f._state)==before
    assert c.feedback.mode=='swap'
    ghost=c.feedback.ghost
    pos=target.mapToGlobal(QPoint(40,90));pointer_move(c,source,pos)
    assert c.feedback.ghost is ghost
    assert ghost.mapToGlobal(QPoint())==pos-QPoint(25,65)
    release_freight(c,source,pos)
    assert [slot.card_id for slot in u.slots[:4]]==[ids[2],None,ids[0],ids[1]]
    assert c.feedback.ghost is None and not c.feedback.timer.isActive() and not c.dragging
    assert f._selected_vehicles==set(ids[:2])
    QApplication.processEvents()


@pytest.mark.parametrize('action', ['escape','outside','deactivate','hide','reset','refresh','stale','busy-counterpart'])
def test_freight_cancellation_cleans_capture_ghost_timer_then_next_drag_works(window,monkeypatch,action):
    f,u,ids,source,target=freight_group(window);c=f._slot_interaction
    monkeypatch.setattr('production_zero.ui.freight_drag.inform',lambda *args:None)
    start_freight(c,source,target)
    before=serialize_game_state(f._state)
    if action=='escape':QTest.keyClick(source,Qt.Key.Key_Escape)
    elif action=='outside':release_freight(c,source,f.mapToGlobal(QPoint(-80,-80)))
    elif action=='deactivate':QApplication.sendEvent(f.window(),QEvent(QEvent.Type.WindowDeactivate))
    elif action=='hide':f.hide()
    elif action=='reset':f.reset_for_state_change()
    elif action=='refresh':f.refresh()
    elif action=='stale':
        f._state.cards=dict(f._state.cards);release_freight(c,source,target.mapToGlobal(QPoint(30,80)))
    else:
        f._state.freight.outbound_shipments['busy']=OutboundFreightShipment('busy','market',freight_card_id=ids[2],quantity=10,remaining_seconds=20)
        before=serialize_game_state(f._state);release_freight(c,source,target.mapToGlobal(QPoint(30,80)))
        f._state.freight.outbound_shipments.clear();before['freight']['outbound_shipments'].clear()
    assert not c.dragging and c.feedback.ghost is None and not c.feedback.timer.isActive()
    assert c.start is None and c.origin is None and not c.ids
    assert QWidget.mouseGrabber() is None
    assert serialize_game_state(f._state)==before
    f.show();f.refresh();QApplication.processEvents()
    source=next(w for w in c._cards() if w._freight_vehicle==ids[0]);target=next(w for w in c._cards() if w._freight_destination[1]==4)
    start_freight(c,source,target);c._finish_pointer_drag()
    QTest.mouseClick(source,Qt.MouseButton.LeftButton,pos=QPoint(25,65))
    assert ids[0] in f._selected_vehicles


@pytest.mark.parametrize('kind', ['production','freight'])
def test_actual_board_edge_scroll_both_directions_bounds_and_wheel(window,monkeypatch,kind):
    if kind=='production':
        from production_zero.core.state import FactoryHall
        b,ids=populated_factory(window)
        unit=b._units[b._selected_hall_id]
        for line in unit.production_lines:
            line.unlocked=True;line.slot_indexes=list(range(unit.production_lines.index(line)*unit.max_slots_per_line,(unit.production_lines.index(line)+1)*unit.max_slots_per_line))
        b.refresh_view();QApplication.processEvents();source=b._slot_widgets[0]
        feedback=b._machine_feedback;feedback.start(source,QPoint(20,80));scroll=b._factory_v2_scroll
    else:
        b,u,ids,source,target=freight_group(window,slots=48);start_freight(b._slot_interaction,source,target)
        feedback=b._slot_interaction.feedback;scroll=b._slots_scroll
    viewport=scroll.viewport();bar=scroll.verticalScrollBar();assert bar.maximum()>0
    assert feedback.scroll is scroll
    bottom=viewport.mapToGlobal(QPoint(viewport.width()//2,viewport.height()-2))
    monkeypatch.setattr(QCursor,'pos',lambda:bottom)
    feedback.update_position(bottom);assert feedback.timer.isActive()
    for _ in range(4):feedback._tick()
    assert bar.value()>0
    current=bar.value();bar.setValue(bar.maximum());feedback.update_position(bottom)
    assert not feedback.timer.isActive()
    top=viewport.mapToGlobal(QPoint(viewport.width()//2,1));monkeypatch.setattr(QCursor,'pos',lambda:top)
    feedback.update_position(top);feedback._tick();assert bar.value()<bar.maximum()
    bar.setValue(0);feedback.update_position(top);assert not feedback.timer.isActive()
    center=viewport.mapToGlobal(viewport.rect().center());feedback.update_position(center)
    event=QWheelEvent(QPointF(viewport.rect().center()),QPointF(center),QPoint(),QPoint(0,-120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
    assert feedback.wheel(event) and bar.value()>0 and event.isAccepted()
    feedback.stop();assert not feedback.wheel(event)


@pytest.mark.parametrize('action',['escape','deactivate','tab','reset','source-removed','new-cards'])
def test_production_lifetime_stops_feedback_and_preserves_next_gesture(window,monkeypatch,action):
    b,ids=populated_factory(window);w=b._slot_widgets[0]
    data=b._machine_drag_payload(ids[:2]);b._machine_drag_data=data
    b._machine_feedback.start(w,QPoint(21,75))
    if action=='escape':QTest.keyClick(window,Qt.Key.Key_Escape)
    elif action=='deactivate':QApplication.sendEvent(window,QEvent(QEvent.Type.WindowDeactivate))
    elif action=='tab':window.findChild(QTabWidget,'mainTabs').setCurrentIndex(0)
    elif action=='reset':
        b.reset_for_state_change()
        assert b._machine_drag_token!=data['token']
    elif action=='source-removed':
        b._units[b._selected_hall_id].slots[0].card_id=None;b._check_machine_drag_sources()
    else:
        b._state.cards=dict(b._state.cards);b._check_machine_drag_sources()
    assert not b._machine_feedback.active and not b._machine_feedback.timer.isActive()
    assert b._machine_drag_data is None and b._machine_feedback.outline is None
    b.show();b._machine_feedback.start(w,QPoint(20,80));b._cancel_machine_drag()
    assert not b._machine_feedback.active


@pytest.mark.parametrize('did,facility_type',[
    ('freight.truck','garage_depot'),('freight.train','rail_station'),('freight.aircraft','airport'),('freight.ship','harbor')])
def test_each_freight_facility_uses_same_occupied_pointer_swap(window,did,facility_type):
    from production_zero.core.freight import FreightFacility
    f=board(window,'Freight');s=f._state;s.cash.amount=1e12
    u=FreightFacility('p4','P4',facility_type,slot_count=3);s.freight.facilities['p4']=u;f._selected_facility_id='p4'
    ids=buy_common_supply_cards(s,f._definitions,did,2)
    for i,cid in enumerate(ids):InstallFreightCard('p4',i,cid,f._definitions).apply(s)
    f.refresh();QApplication.processEvents();c=f._slot_interaction
    source=next(w for w in c._cards() if w._freight_vehicle==ids[0]);target=next(w for w in c._cards() if w._freight_vehicle==ids[1])
    start_freight(c,source,target);assert c.feedback.mode=='swap'
    release_freight(c,source,target.mapToGlobal(QPoint(30,80)))
    assert [slot.card_id for slot in u.slots[:2]]==list(reversed(ids))


@pytest.mark.parametrize('kind',['production','freight'])
def test_wheel_event_reaches_nearest_board_viewport_and_recalculates_target(window,kind):
    if kind=='freight':
        b,u,ids,source,target=freight_group(window,slots=48)
        start_freight(b._slot_interaction,source,target);feedback=b._slot_interaction.feedback
    else:
        b,ids=populated_factory(window);u=b._units[b._selected_hall_id]
        for n,line in enumerate(u.production_lines):
            line.unlocked=True;line.slot_indexes=list(range(n*u.max_slots_per_line,(n+1)*u.max_slots_per_line))
        b.refresh_view();QApplication.processEvents();source=b._slot_widgets[0]
        feedback=b._machine_feedback;b._machine_drag_data=b._machine_drag_payload(ids[:2])
        feedback.start(source,QPoint(25,80))
    scroll=feedback.scroll;bar=scroll.verticalScrollBar();bar.setValue(0)
    position=source.mapToGlobal(QPoint(30,85));feedback.update_position(position);feedback.moved(position)
    first=feedback.target;assert first is not None
    event=QWheelEvent(QPointF(source.mapFromGlobal(position)),QPointF(position),QPoint(),QPoint(0,-120),
        Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
    QApplication.sendEvent(source,event)
    assert event.isAccepted() and bar.value()>0
    for _ in range(4):QApplication.sendEvent(source,event)
    assert feedback.target is not first
    if feedback.ghost is not None:assert feedback.ghost.mapToGlobal(QPoint())==position-feedback.grip
    if kind=='production':b._cancel_machine_drag()
    else:b._slot_interaction._finish_pointer_drag()


@pytest.mark.parametrize('action',['load','new-game'])
def test_actual_mainwindow_session_replacement_releases_all_drag_resources(app,action):
    from production_zero.ui.main_window import MainWindow,_create_initial_state
    from production_zero.ui.dev_tools_view import DevToolsView
    from production_zero.ui.factory_view_v2 import FactoryViewV2
    w=MainWindow(development_mode=True);w.resize(1366,768);w.show();QApplication.processEvents()
    b,ids=populated_factory(w);source=b._slot_widgets[0]
    data=b._machine_drag_payload(ids[:2]);b._machine_drag_data=data;b._machine_feedback.start(source,QPoint(25,80))
    dev=w.findChild(DevToolsView)
    if action=='new-game':dev._reset_callback()
    else:
        from production_zero.data.definitions import load_resource_definitions
        from importlib.resources import files
        resources=load_resource_definitions(files('production_zero.data')/'resource_definitions.json')
        dev._load_state_callback(_create_initial_state(resources,b._definitions))
    b.pause_simulation();QApplication.processEvents()
    assert b._machine_drag_token!=data['token'] and not b._machine_feedback.active
    assert b._machine_drag_data is None and not b._machine_feedback.timer.isActive()
    f=w.findChild(FreightView);assert not f._slot_interaction.dragging and f._slot_interaction.feedback.ghost is None
    assert QWidget.mouseGrabber() is None
    w.close();w.deleteLater();QApplication.processEvents()
