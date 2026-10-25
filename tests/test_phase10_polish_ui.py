"""Actual widgets and clicks for the P10 interaction changes."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontMetricsF
from PySide6.QtWidgets import QApplication, QTabWidget, QComboBox, QLineEdit, QWidget
from PySide6.QtTest import QTest
from test_phase9_navigation_ui import app, window, board, tabs
from test_phase3_inventory_ui import setup, choose, answer
from test_phase5_freight_ui import setup as freight_setup
from production_zero.ui.game_ui import GameButton
from production_zero.ui.release_dialogs import IndustrialDialog
from production_zero.ui.event_feed import EventFeedWidget
from production_zero.core.commands import BuyCommonSupplyCard
from production_zero.persistence.sqlite_store import serialize_game_state


@pytest.mark.parametrize('kind',['resources','factory','energy','freight'])
@pytest.mark.parametrize('name',['X','MY VERY LARGE INDUSTRIAL COMPLEX ' * 5])
def test_pencil_tracks_visible_text_and_preserves_room_for_actions(window,app,kind,name):
    from production_zero.ui.freight_view import FreightView
    view=window.findChild(FreightView) if kind=='freight' else board(window,kind)
    tabs(window).setCurrentWidget(view)
    unit=view._state.freight.facilities[view._selected_facility_id] if kind=='freight' else view._units[view._selected_hall_id]
    unit.name=name;(getattr(view,'refresh_view',None) or view.refresh)();app.processEvents()
    stage=view._facility_stage if kind=='freight' else view.findChild(QWidget,'factoryV2HallStage')
    font,text,rect=stage.rename_title_layout();button=stage._rename_filter.pencil
    assert abs(button.x()-rect.x())<=1 and button.isVisible()
    assert button.x()+button.width()<=stage.width()
    assert text and name in stage.toolTip()
    if name=='X':assert button.x()<100
    else:assert len(text)<len(name)
    if kind=='freight':assert button.x()+32+4<=stage._header_geometry()[3] and stage.height()==64


def test_rename_dialog_is_name_only_and_cancel_is_safe(window,app):
    view=board(window,'resources');tabs(window).setCurrentWidget(view);raw=serialize_game_state(view._state)
    def inspect():
        dialog=QApplication.activeModalWidget();assert isinstance(dialog,IndustrialDialog)
        assert dialog.findChild(QComboBox,'resourceSiteType') is None
        assert len(dialog.findChildren(QLineEdit))==1
        assert 'TYPE CHANGE' not in dialog.message.text() and dialog.height()<400
        dialog.reject_button.click()
    QTimer.singleShot(0,inspect);view._rename_building()
    assert serialize_game_state(view._state)==raw


@pytest.mark.parametrize('accept',[False,True])
def test_storage_expand_ui_quoted_confirm_or_cancel(window,app,accept):
    header=window._global_header;s=window._session_state;s.cash.amount=1e9
    raw=serialize_game_state(s);old=s.storage_capacity
    def inspect():
        d=QApplication.activeModalWidget();assert isinstance(d,IndustrialDialog)
        assert d.windowTitle()=='Storage expansion' and 'Cost: $250.00' in d.message.text()
        assert 'Additional storage capacity:' in d.message.text()
        (d.accept_button if accept else d.reject_button).click()
    QTimer.singleShot(0,inspect);header._expand_resource_storage()
    if accept:assert s.storage_capacity>old and s.inventory_storage_level==1 and s.cash.amount==1e9-250
    else:assert serialize_game_state(s)==raw


def test_inbox_attention_uses_persistent_unread_and_only_button_paint(window,app):
    feed=window.findChild(EventFeedWidget);s=window._session_state
    s.communications.messages.clear();feed.refresh_communications()
    assert not feed._inbox_attention.isActive()
    s.communications.add_unlocks(['resource.iron_ore']);feed.refresh_communications()
    assert feed._inbox_button.property('unread') and feed._inbox_attention.isActive()
    assert feed._inbox_button.height()>=42 and feed._history_button.height()>=42
    before=serialize_game_state(s);feed._pulse_inbox()
    assert serialize_game_state(s)==before
    feed._show_inbox();app.processEvents()
    assert not feed._inbox_attention.isActive() and not feed._inbox_button.property('unread')
    feed.close_panels()


def test_supply_all_and_each_family_are_direct_reachable_without_dropdown(app,setup):
    s,d,b,inv,supply=setup;supply.resize(900,680);supply.show();supply._show_section(1);app.processEvents()
    selector=supply._type_filter
    assert not isinstance(selector,QComboBox) and selector.currentText()=='All'
    all_ids={v.definition_id for v in supply._filtered_common_data};seen=set()
    for category,button in selector.buttons.items():
        QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
        assert selector.currentText()==category and supply._filtered_common_data
        if category!='All':seen.update(v.definition_id for v in supply._filtered_common_data)
    assert seen==all_ids and any('assembler' in key for key in seen)


def test_inventory_right_click_preserves_multiple_stacks_and_quantity(app,setup):
    s,d,b,inv,supply=setup
    for did in ('machine.processor','machine.fabricator'):b.dispatch(BuyCommonSupplyCard(did,d,4))
    inv.refresh();rows=inv._workspace_rows
    inv._choose_workspace_card(rows[0]);inv._workspace_quantity_changed(3)
    inv._choose_workspace_card(rows[1],Qt.KeyboardModifier.ControlModifier)
    ids=set(inv._workspace_ids());assert len(ids)==4
    card=next(c for c in inv._workspace_pool if c.isVisible() and c._inventory_row==rows[0])
    QTest.mouseClick(card,Qt.MouseButton.RightButton);app.processEvents()
    menu=inv._workspace_menu;assert menu.isVisible() and set(inv._workspace_ids())==ids
    assert menu.findChild(GameButton,'inventoryContextSell') and menu.findChild(GameButton,'inventoryContextInstall')
    assert not menu.findChild(GameButton,'inventoryContextResetRoute')
    menu.reject();app.processEvents()
    assert not hasattr(inv,'_workspace_quantity') and not hasattr(inv,'_workspace_sell')
    assert not inv.findChild(QWidget,'inventoryCount')


@pytest.mark.parametrize('cancel',['cancel','escape','tab','reset'])
def test_delivery_dialog_disabled_targets_and_cancel_never_commit(window,app,cancel):
    f,u,ids,source=freight_setup(window);raw=serialize_game_state(f._state)
    f._open_assignment_view(ids[0],ids[:2]);f._select_assignment_resource('steel');app.processEvents()
    dialog=f._route_dialog;assert isinstance(dialog,IndustrialDialog) and dialog.isModal()
    assert not dialog.findChildren(QComboBox)
    assert dialog.targets['market'].isEnabled() and not dialog.targets['event'].isEnabled()
    f._choose_assignment_destination('market');assert f._route_confirm.isEnabled()
    if cancel=='cancel':dialog.reject_button.click()
    elif cancel=='escape':QTest.keyClick(dialog,Qt.Key.Key_Escape)
    elif cancel=='tab':tabs(window).setCurrentIndex(0)
    else:f.reset_for_state_change()
    app.processEvents();assert f._route_dialog is None and serialize_game_state(f._state)==raw


@pytest.mark.parametrize('action',['sell','install','quantity','reset'])
def test_inventory_actions_are_reachable_by_actual_context_clicks(app,setup,action):
    from production_zero.core.freight import FreightAssignment
    s,d,b,inv,supply=setup
    did='freight.truck' if action=='reset' else 'machine.processor'
    b.dispatch(BuyCommonSupplyCard(did,d,3));inv.refresh();cid=next(iter(s.cards))
    if action=='reset':s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    choose(app,inv,cid)
    cid=inv._workspace_ids()[0]
    if action=='reset':s.freight.assignments[cid]=FreightAssignment('iron_ore','market')
    card=next(c for c in inv._workspace_pool if c.isVisible() and cid in c._inventory_row.card_ids)
    QTest.mouseClick(card,Qt.MouseButton.RightButton);app.processEvents();menu=inv._workspace_menu
    key={'sell':'Sell','install':'Install','quantity':'SelectQuantity','reset':'ResetRoute'}[action]
    def decision(d):
        if action=='quantity':d.quantity.setValue(2)
        d.accept_button.click()
    answer(app,decision)
    QTest.mouseClick(menu.findChild(GameButton,'inventoryContext'+key),Qt.MouseButton.LeftButton)
    app.processEvents()
    if action=='sell':assert len(s.cards)==2 and cid not in s.cards
    elif action=='install':assert cid in s.installed_card_ids()
    elif action=='quantity':assert len(inv._workspace_ids())==2
    else:assert cid not in s.freight.assignments


@pytest.mark.parametrize('change',['installed','price','session'])
def test_inventory_sale_revalidates_availability_quote_and_session(app,setup,monkeypatch,change):
    from dataclasses import replace
    from production_zero.core.commands import InstallCardInHall
    s,d,b,inv,supply=setup;b.dispatch(BuyCommonSupplyCard('machine.processor',d));inv.refresh();cid=next(iter(s.cards));choose(app,inv,cid)
    def confirm(*args):
        if change=='installed':InstallCardInHall('h',0,cid,'factory').apply(s)
        elif change=='price':s.cards[cid]=replace(s.cards[cid],upgrade_investment=100)
        else:s.cards=dict(s.cards)
        return True
    monkeypatch.setattr('production_zero.ui.inventory_workspace.confirm',confirm)
    cash=s.cash.amount
    with pytest.raises(ValueError):inv._sell_workspace_cards()
    assert s.cash.amount==cash and cid in s.cards


def test_storage_dialog_cannot_commit_after_new_session(window,app,monkeypatch):
    s=window._session_state;s.cash.amount=1e9;cash=s.cash.amount
    def confirm(*args):s.cards=dict(s.cards);return True
    monkeypatch.setattr('production_zero.ui.release_dialogs.confirm',confirm)
    window._global_header._expand_resource_storage()
    assert s.inventory_storage_level==0 and s.cash.amount==cash
