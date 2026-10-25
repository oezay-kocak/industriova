"""Actual window navigation, communication ownership, prices and rename entry."""
import pytest
from PySide6.QtCore import Qt,QTimer,QPoint
from PySide6.QtWidgets import QApplication,QWidget,QTabWidget,QPushButton,QToolButton,QLabel
from PySide6.QtTest import QTest
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2,FactoryV2LinePlate,ProductionBoardViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.event_feed import EventFeedWidget,FeedEvent
from production_zero.persistence.sqlite_store import serialize_game_state,deserialize_game_state
from production_zero.core.modifiers import market_sale_price
from production_zero.core.market import market_price_for
from production_zero.ui.resource_prices import base_price_text,price_number

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([]);_load_qa_fonts();return app

@pytest.fixture
def window(app):
    w=MainWindow(development_mode=True)
    for timer in w.findChildren(QTimer):timer.stop()
    from contract_capacity_fixture import provide_capacity
    from test_phase8_contract_balance import D
    provide_capacity(w._session_state,D)
    w.resize(1366,768);w.show();app.processEvents()
    yield w
    w.close();app.processEvents()

def tabs(w):return w.findChild(QTabWidget,'mainTabs')
def board(w,kind):return next(v for v in w.findChildren(ProductionBoardViewV2) if v._board_config.board_kind==kind)

def test_storage_actions_and_communication_buttons_have_one_owner(window,app):
    h=window._global_header;storage=h.findChild(QWidget,'factoryV2StorageModule')
    resources=h.findChild(QWidget,'globalResourcesButton');expand=h.findChild(QWidget,'expandResourceStorageButton')
    assert storage.isAncestorOf(resources) and storage.isAncestorOf(expand)
    assert expand.y()<resources.y() and expand.x()>storage.width()/2
    feed=window.findChild(EventFeedWidget)
    assert h.isAncestorOf(feed._history_button) and h.isAncestorOf(feed._inbox_button)
    assert not feed.isAncestorOf(feed._history_button)
    assert len(window.findChildren(QWidget,'companyInboxButton'))==1
    before=window._session_state.inventory_storage_level
    window._session_state.cash.amount=1e9;h.refresh()
    def accept_expansion():
        from production_zero.ui.release_dialogs import IndustrialDialog
        d=QApplication.activeModalWidget();assert isinstance(d,IndustrialDialog);d.accept_button.click()
    QTimer.singleShot(0,accept_expansion);expand.click()
    assert window._session_state.inventory_storage_level==before+1
    resources.click();assert window._global_resources.isVisible()
    resources.click();assert not window._global_resources.isVisible()

def test_history_inbox_unread_and_ticker_share_existing_data(window,app):
    feed=window.findChild(EventFeedWidget);s=window._session_state
    s.communications.add_unlocks(['resource.iron_ore']);feed.refresh_communications()
    assert feed._inbox_button.property('unread') and '1' in feed._inbox_button.text()
    feed.push(FeedEvent('contract','P9 TEST COMPLETION',123))
    feed.flush_pending()
    history=feed.history
    feed._history_button.click();app.processEvents();assert feed._history_panel.isVisible()
    assert feed.history==history and s.communications.unread_count==1
    feed.close_panels();feed._inbox_button.click();app.processEvents()
    assert feed._inbox_panel.isVisible() and s.communications.unread_count==0
    assert not feed._inbox_button.property('unread')
    assert feed.history==history
    loaded=deserialize_game_state(serialize_game_state(s))
    assert len(loaded.communications.messages)==1 and loaded.communications.messages[0].read
    feed.close_panels();app.processEvents();feed.close_panels()
    feed._tick();assert feed.history==history

def test_empty_inbox_can_reopen_after_tab_switch(window,app):
    feed=window.findChild(EventFeedWidget)
    feed._inbox_button.click();app.processEvents();assert feed._inbox_panel.isVisible()
    from production_zero.core.player_profile import local_profile
    window.open_player_profile(local_profile(window._session_state))
    assert window._profile_view is not None
    tabs(window).setCurrentWidget(board(window,'factory'));app.processEvents()
    assert feed._inbox_panel is None
    assert window._profile_view is None
    feed._inbox_button.click();app.processEvents();assert feed._inbox_panel.isVisible()
    feed.close_panels()

@pytest.mark.parametrize('kind',['resources','factory','energy'])
def test_main_tab_entry_restores_board_without_economic_action(window,app,kind):
    view=board(window,kind);t=tabs(window);t.setCurrentWidget(view);app.processEvents()
    view._open_production_guide()
    assert view._drawer_mode is not None
    before=serialize_game_state(window._session_state)
    t.setCurrentWidget(window.findChild(FreightView));t.setCurrentWidget(view);app.processEvents()
    assert view._drawer_mode is None and serialize_game_state(window._session_state)==before

def test_freight_route_draft_is_discarded_on_main_navigation(window,app):
    f=window.findChild(FreightView);t=tabs(window);t.setCurrentWidget(f);app.processEvents()
    cid=next(iter(f._state.installed_freight_card_ids()));f._open_assignment_view(cid)
    f._select_assignment_resource('iron_ore');f._choose_assignment_destination('market')
    before=serialize_game_state(f._state)
    t.setCurrentWidget(board(window,'resources'));t.setCurrentWidget(f);app.processEvents()
    assert f._assignment_card_id is None and f._drawer_slot_index is None
    assert serialize_game_state(f._state)==before

def test_contract_picker_draft_and_consortium_subtab_reset_on_entry(window,app):
    t=tabs(window);personal=window.findChild(ContractsView);t.setCurrentWidget(personal);app.processEvents()
    offer=personal._state.contracts.offers['daily'][0]
    personal._open_product_picker('daily',offer.contract_id,0)
    t.setCurrentWidget(board(window,'resources'));t.setCurrentWidget(personal);app.processEvents()
    assert personal._product_picker is None and personal._board_scroll.isVisible()
    conso=window.findChild(ConsortiumView);conso._service.create('P9 Navigation Group')
    t.setCurrentWidget(conso);app.processEvents();conso.member_tabs.setCurrentIndex(2)
    t.setCurrentWidget(personal);t.setCurrentWidget(conso);app.processEvents()
    assert conso.member_tabs.currentIndex()==0

@pytest.mark.parametrize('kind',['resources','factory','energy','freight'])
def test_pencil_uses_existing_rename_path(window,app,monkeypatch,kind):
    view=window.findChild(FreightView) if kind=='freight' else board(window,kind)
    tabs(window).setCurrentWidget(view);app.processEvents()
    from production_zero.ui import interaction_polish
    if kind=="freight":
        assert "SELL" in view._facility_stage.toolTip().upper()
        assert "CONSORTIUM" in view._facility_stage.toolTip().upper()
    calls=[]
    def rename(parent,current,apply,**kwargs):calls.append(current);apply('P9 RENAMED FACILITY')
    monkeypatch.setattr(interaction_polish,'rename_building',rename)
    before=window._session_state.cash.amount
    pencil=next(p for p in view.findChildren(QToolButton,'renameBuildingButton') if p.isVisible())
    QTest.mouseClick(pencil,Qt.MouseButton.LeftButton);app.processEvents()
    assert len(calls)==1 and window._session_state.cash.amount==before
    current=view._state.freight.facilities[view._selected_facility_id] if kind=='freight' else view._units[view._selected_hall_id]
    assert current.name=='P9 RENAMED FACILITY'

@pytest.mark.parametrize('action',['new','load'])
@pytest.mark.parametrize('subview',['guide','route','inbox','contract'])
def test_session_replace_drops_open_subviews_and_foreign_references(window,app,action,subview):
    t=tabs(window);f=window.findChild(FreightView);v=board(window,'factory');p=window.findChild(ContractsView)
    if subview=='guide':t.setCurrentWidget(v);v._open_production_guide()
    elif subview=='route':t.setCurrentWidget(f);f._open_assignment_view(next(iter(f._state.installed_freight_card_ids())))
    elif subview=='inbox':window.findChild(EventFeedWidget)._inbox_button.click()
    else:
        t.setCurrentWidget(p);offer=p._state.contracts.offers['daily'][0];p._open_product_picker('daily',offer.contract_id,0)
    old_cards=window._session_state.cards;dev=window.findChild(DevToolsView)
    if action=='new':dev._reset_callback()
    else:dev._load_state_callback(deserialize_game_state(serialize_game_state(window._session_state)))
    for timer in window.findChildren(QTimer):timer.stop()
    app.processEvents()
    assert window._session_state.cards is not old_cards
    assert v._drawer_mode is None and f._assignment_card_id is None and p._product_picker is None
    feed=window.findChild(EventFeedWidget);assert feed._history_panel is None and feed._inbox_panel is None
    assert not window._global_resources.isVisible()

@pytest.mark.parametrize('line',['RAIL LINE 01','SHIPPING LINE 01'])
def test_line_plate_contains_full_text_at_current_dpi(app,line):
    from PySide6.QtGui import QFontMetrics
    from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
    p=FactoryV2LinePlate(line);font=GAME_UI_TOKENS.typography.industrial_title();font.setPointSize(15)
    assert p.width()>=QFontMetrics(font).horizontalAdvance(line)+48
    assert p.toolTip()==line;p.deleteLater()

def test_resource_prices_use_central_base_and_current_research_values(window,app):
    view=board(window,'factory');tabs(window).setCurrentWidget(view);view._toggle_resources_drawer();app.processEvents()
    window._global_resources.toggle();app.processEvents()
    window._global_resources.drawer._set_inventory_mode(True)
    summary=window._global_resources.drawer.summary
    assert summary._items
    for rid,item in summary._items.items():
        assert item.property('baseSellPrice')==market_price_for(view._state.market,rid)
        assert item.price.text()==base_price_text(rid,view._state,compact=True)
        assert 'EFFECTIVE SELL PRICE' in item.toolTip()
    s=view._state;s.research.unlocked_node_ids.add('industry.metals.s1.major');summary.refresh()
    item=summary._items['iron_ore']
    assert f'${price_number(market_sale_price(s,"iron_ore"))}' in item.toolTip()
    assert item.property('baseSellPrice')==market_price_for(s.market,'iron_ore')

def test_guide_prices_fit_without_eliding_the_number(window,app):
    view=board(window,'factory');tabs(window).setCurrentWidget(view)
    view._open_production_guide();app.processEvents()
    from production_zero.ui.factory_view import ProductionGuideTile
    for tile in view.findChildren(ProductionGuideTile):
        if not tile.isVisible():continue
        label=tile.findChild(QLabel,'productionGuideTileCategory')
        assert label.text().startswith('BASE SELL $') and label.text().endswith('/U')
        assert label.fontMetrics().horizontalAdvance(label.text())<=label.width()
        assert 'BASE SELL PRICE:' in tile.toolTip()

@pytest.mark.parametrize('subview',['specialization','respec'])
def test_research_returns_to_tree_and_discards_unconfirmed_actions(window,app,subview):
    from production_zero.ui.research_view import ResearchView
    from test_research_specialization_ui import unlock
    view=window.findChild(ResearchView);t=tabs(window);t.setCurrentWidget(view)
    view.select_tree('industry.electronics');unlock(view._state,'industry.electronics',through=2);view.refresh()
    if subview=='specialization':
        view._open_specialization('industry.electronics.specialization.1')
        assert view.picker is not None
    else:
        view._review_respec();assert view.review.isVisible()
    s=view._state;before=(s.cash.amount,s.research.spent,dict(s.research.specializations),set(s.research.unlocked_node_ids))
    t.setCurrentWidget(board(window,'factory'));t.setCurrentWidget(view);app.processEvents()
    assert view.picker is None and not view.review.isVisible()
    assert view.pages.currentWidget() is view.scroll
    assert (s.cash.amount,s.research.spent,s.research.specializations,s.research.unlocked_node_ids)==before

def test_optional_charts_returns_to_existing_overview(app):
    from production_zero.ui.charts_view import ChartsView
    from production_zero.ui.main_window import _refresh_entered_view
    w=MainWindow(charts_enabled=True,development_mode=False)
    for timer in w.findChildren(QTimer):timer.stop()
    w.show();t=tabs(w);view=w.findChild(ChartsView);t.setCurrentWidget(view)
    view._show_resource_detail('iron_ore');assert view._stack.currentIndex()==1
    before=serialize_game_state(w._session_state)
    t.setCurrentWidget(board(w,'factory'));t.setCurrentWidget(view);app.processEvents()
    assert view._stack.currentIndex()==0 and serialize_game_state(w._session_state)==before
    w.close()

@pytest.mark.parametrize('value',[.000001,.01,1,1234567890123456])
def test_price_numbers_are_finite_readable_and_not_rounded_to_zero(value):
    assert price_number(value) and price_number(value)!='0'
