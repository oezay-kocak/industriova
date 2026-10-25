"""P5 real Freight controls, stable selection, cancellation and single debit."""
from dataclasses import replace
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QApplication, QWidget, QTabWidget
from PySide6.QtTest import QTest
from test_ui_interaction_recovery import app, window
from test_phase4_drag_ui import freight_group
from test_freight import _set_active_contract
from production_zero.ui.freight_upgrade import upgrade_vehicles, FreightMkButton
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.commands import UpgradeMachines
from production_zero.core.freight import OutboundFreightShipment, FreightAssignment, FreightCardStats
from production_zero.persistence.sqlite_store import serialize_game_state


def setup(window):
    f,u,ids,source,target=freight_group(window)
    f._state.cash.amount=1e12
    f._state.ensure_resource('steel').amount=100
    f._state.ensure_resource('copper_ore').amount=100
    return f,u,ids,source


def sell(f):
    f._choose_assignment_destination('market')


@pytest.mark.parametrize('count',[1,2,3])
def test_cargo_then_target_then_single_confirm(window,count):
    f,u,ids,source=setup(window);before=serialize_game_state(f._state)
    selected=ids[:count]
    f._open_assignment_view(ids[0],selected)
    assert f._route_dialog is None
    f._select_assignment_resource('steel')
    assert f._route_dialog.isVisible()
    assert f._route_dialog.isModal()
    assert serialize_game_state(f._state)==before
    sell(f); assert f._route_confirm.isEnabled()
    history=len(f._command_bus.history)
    f._confirm_assignment();f._confirm_assignment()
    assert len(f._command_bus.history)==history+1
    assert all(f._state.freight.assignments[cid]==FreightAssignment('steel','market') for cid in selected)
    assert f._runtime_widgets[ids[0]]['card'] is source
    assert f._selected_vehicles==set(ids[:2])


@pytest.mark.parametrize('cancel',['back','esc','tab','reset','close','reopen'])
def test_draft_cancel_never_changes_domain(window,cancel):
    f,u,ids,source=setup(window);before=serialize_game_state(f._state)
    f._open_assignment_view(ids[0],ids);f._select_assignment_resource('steel');sell(f)
    if cancel=='back':f._close_assignment_view()
    elif cancel=='esc':QTest.keyClick(f,Qt.Key.Key_Escape)
    elif cancel=='tab':
        tabs=window.findChild(QTabWidget,'mainTabs');tabs.setCurrentIndex(0);QApplication.processEvents();tabs.setCurrentWidget(f)
    elif cancel=='reset':f.reset_for_state_change()
    elif cancel=='close':f.hide();QApplication.processEvents();f.show()
    elif cancel=='reopen':f._open_assignment_view(ids[1])
    assert serialize_game_state(f._state)==before
    if cancel!='reopen':assert f._assignment_card_id is None
    else:assert f._route_group==(ids[1],)


def test_mixed_group_and_contract_cargo_change_invalidates_target(window):
    f,u,ids,source=setup(window)
    f._state.freight.assignments[ids[0]]=FreightAssignment('steel','contract')
    f._state.freight.assignments[ids[1]]=FreightAssignment('copper_ore','market')
    _set_active_contract(f._state,'daily','manual','steel',500)
    f._open_assignment_view(ids[0],ids[:2])
    assert f._route_mixed and f._draft_resource is None and f._assignment_destination is None
    f._select_assignment_resource('steel')
    f._choose_assignment_destination('contract')
    assert f._route_confirm.isEnabled()
    f._select_assignment_resource('copper_ore')
    assert f._assignment_destination is None and not f._route_confirm.isEnabled()
    assert not f._route_dialog.targets['event'].isEnabled()
    f._choose_assignment_destination('contract')
    assert 'No active contract' in f._route_dialog.targets['contract'].toolTip() and not f._route_confirm.isEnabled()


@pytest.mark.parametrize('case',['move','remove','expired','new-session','no-stock'])
def test_stale_confirm_is_atomic_and_explained(window,case):
    f,u,ids,source=setup(window)
    _set_active_contract(f._state,'daily','manual','steel',500)
    f._open_assignment_view(ids[0],ids[:2]);f._select_assignment_resource('steel')
    f._choose_assignment_destination('contract')
    if case=='move':u.slots[0].card_id,u.slots[2].card_id=u.slots[2].card_id,u.slots[0].card_id
    if case=='remove':del f._state.cards[ids[1]]
    if case=='expired':f._state.contracts.active['daily'].offer=replace(f._state.contracts.active['daily'].offer,expires_at=1)
    if case=='new-session':f._state.cards=dict(f._state.cards)
    if case=='no-stock':f._state.resources['steel'].amount=0
    before=serialize_game_state(f._state);f._confirm_assignment()
    assert serialize_game_state(f._state)==before and f._route_error.text()
    assert not f._route_confirm.isEnabled()


@pytest.mark.parametrize('level',[1,2,10,98,99])
@pytest.mark.parametrize('cash',['enough','empty'])
def test_single_card_upgrade_matches_context_command_without_drag_or_selection(window,monkeypatch,level,cash):
    f,u,ids,source=setup(window);s=f._state
    # With an active group the direct button now upgrades that group. Keep this
    # test focused on its original no-selection, single-vehicle interaction.
    f._selected_vehicles.clear()
    s.cards[ids[0]]=replace(s.cards[ids[0]],mk_level=level)
    if cash=='empty':s.cash.amount=0
    f.refresh_runtime();button=source.findChild(FreightMkButton,'freightMkUpgrade')
    assert button is not None and button.isEnabled()==(level<99)
    assert ('Maximum' if level==99 else f'MK{level + 1}') in button.toolTip()
    monkeypatch.setattr('production_zero.ui.freight_upgrade.confirm',lambda *a:True)
    messages=[];monkeypatch.setattr('production_zero.ui.freight_upgrade.inform',lambda *a:messages.append(a))
    before=serialize_game_state(s);selected=set(f._selected_vehicles)
    expected=deepcopy(s)
    if level<99 and cash=='enough':UpgradeMachines((ids[0],),f._definitions).apply(expected)
    # Route through the actual window hit test, including the disabled MK99 shield.
    position=button.mapTo(window,button.rect().center())
    QTest.mouseClick(window.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,position)
    assert serialize_game_state(s)==serialize_game_state(expected)
    QTest.mouseDClick(window.windowHandle(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,position)
    upgrade_vehicles(f,(ids[0],))  # repeated confirmed intent while cooldown is held
    assert serialize_game_state(s)==serialize_game_state(expected)
    assert f._selected_vehicles==selected
    assert not f._slot_interaction.dragging and f._slot_interaction.start is None
    assert source is f._runtime_widgets[ids[0]]['card']
    if cash=='empty' and level<99:assert messages


@pytest.mark.parametrize('case',['cancel','card-change','session-change','cash-change','busy'])
def test_upgrade_modal_revalidation_and_busy_snapshot(window,monkeypatch,case):
    f,u,ids,source=setup(window);s=f._state;before=serialize_game_state(s)
    shipment=OutboundFreightShipment('active','market',resource_id='steel',quantity=4,freight_card_id=ids[0],transport_capacity=20,transport_time_seconds=60,remaining_seconds=20)
    s.freight.outbound_shipments['active']=shipment;snapshot=deepcopy(shipment)
    def confirm(*args):
        if case=='card-change':s.cards[ids[0]]=replace(s.cards[ids[0]],mk_level=8)
        if case=='session-change':s.cards=dict(s.cards)
        if case=='cash-change':s.cash.amount=0
        return case!='cancel'
    monkeypatch.setattr('production_zero.ui.freight_upgrade.confirm',confirm)
    monkeypatch.setattr('production_zero.ui.freight_upgrade.inform',lambda *a:None)
    cash=s.cash.amount;upgrade_vehicles(f,ids[:2])
    assert shipment==snapshot
    if case=='busy':
        assert all(s.cards[cid].mk_level==2 for cid in ids[:2]) and s.cash.amount<cash
    else:
        assert s.cards[ids[1]].mk_level==1
        assert s.cash.amount==(0 if case=='cash-change' else cash)


def test_hover_updates_theoretical_values_in_place(window,monkeypatch):
    f,u,ids,source=setup(window);f._show_freight_hover(ids[0],source)
    popup=f._hover_popup;signature=popup.details_signature
    assert 'THEORETICAL THROUGHPUT' in str(signature)
    s=f._state;s.cards[ids[0]]=replace(s.cards[ids[0]],mk_level=99,paused=True)
    f.refresh_runtime()
    assert f._hover_popup is popup and source is f._runtime_widgets[ids[0]]['card']
    from production_zero.core.freight import freight_stats
    from production_zero.core.research import research_catalog
    from production_zero.ui.freight_view import theoretical_throughput_text
    card=s.cards[ids[0]]
    assert popup._value_labels['THEORETICAL THROUGHPUT'].text()==theoretical_throughput_text(freight_stats(card,f._definitions[card.definition_id],s.research))
    s.research.unlocked_node_ids.update(n.id for n in research_catalog()[1].values() if n.effect_type=='freight_capacity')
    f.refresh_runtime()
    assert popup._value_labels['THEORETICAL THROUGHPUT'].text()==theoretical_throughput_text(freight_stats(card,f._definitions[card.definition_id],s.research))
    label=next(l for l in popup.findChildren(QWidget,'cardHoverLabel') if l.text()=='THEORETICAL THROUGHPUT')
    assert label.wordWrap()
    monkeypatch.setattr('production_zero.ui.freight_view.freight_stats',lambda *a:FreightCardStats(1,0))
    f._update_freight_hover(ids[0])
    assert f._hover_popup is popup


@pytest.mark.parametrize('level',[1,10,98])
def test_context_and_direct_upgrade_identical_command_and_quote(window,monkeypatch,level):
    from production_zero.ui.release_freight import vehicle_actions
    from production_zero.ui.game_ui import GameButton
    from production_zero.core.enums import Rarity
    f,u,ids,source=setup(window);s=f._state;cid=ids[0]
    s.cards[cid]=replace(s.cards[cid],mk_level=level,rarity=Rarity.COMMON)
    baseline=deepcopy(s);f._selected_vehicles={cid}
    monkeypatch.setattr('production_zero.ui.freight_upgrade.confirm',lambda *a:True)
    monkeypatch.setattr('production_zero.ui.freight_upgrade.inform',lambda *a:None)
    upgrade_vehicles(f,(cid,));direct=serialize_game_state(s)
    s.cards=deepcopy(baseline.cards);s.cash=deepcopy(baseline.cash);s.history=deepcopy(baseline.history)
    f._freight_upgrade_pending=False
    def choose():
        dialog=QApplication.activeModalWidget()
        button=next(b for b in dialog.findChildren(GameButton,'machineContextAction') if b.text()=='MK UPGRADE')
        button.click()
    QTimer.singleShot(30,choose)
    vehicle_actions(f,cid)
    assert serialize_game_state(s)==direct
    assert isinstance(f._command_bus.history[-1],UpgradeMachines)


def test_dragging_from_mk_control_never_captures_or_moves_card(window,monkeypatch):
    f,u,ids,source=setup(window)
    button=source.findChild(FreightMkButton,'freightMkUpgrade')
    monkeypatch.setattr('production_zero.ui.freight_upgrade.confirm',lambda *a:False)
    before=serialize_game_state(f._state);selected=set(f._selected_vehicles)
    QTest.mousePress(button,Qt.MouseButton.LeftButton)
    QTest.mouseMove(button,QPoint(-70,-70),20)
    QTest.mouseRelease(button,Qt.MouseButton.LeftButton,pos=QPoint(-70,-70))
    assert f._slot_interaction.start is None and not f._slot_interaction.feedback.active
    assert serialize_game_state(f._state)==before and f._selected_vehicles==selected


def test_missing_definition_disables_upgrade_without_runtime_crash(window):
    f,u,ids,source=setup(window)
    f._state.cards[ids[0]]=replace(f._state.cards[ids[0]],definition_id='missing.vehicle')
    f.refresh_runtime()
    button=source.findChild(FreightMkButton,'freightMkUpgrade')
    assert not button.isEnabled() and 'unavailable' in button.toolTip()


def test_target_popup_has_opaque_dark_background_and_readable_text(window):
    from production_zero.ui.game_ui import GameButton,Accent
    f,u,ids,source=setup(window)
    f._open_assignment_view(ids[0]);f._select_assignment_resource('steel');sell(f)
    QApplication.processEvents();dialog=f._route_dialog
    picture=dialog.grab().toImage();assert not picture.isNull()
    assert dialog.findChildren(GameButton) and dialog.accept_button.accent==Accent.BUILD
    assert dialog.reject_button.accent==Accent.DANGER
    assert not dialog.targets['event'].isEnabled() and dialog.targets['event'].toolTip()
    dialog.reject()
