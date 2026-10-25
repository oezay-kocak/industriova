"""P7 real widgets: responsive drawer, row drops, reward feed and tree values."""
from copy import deepcopy
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QMimeData, QEvent
from PySide6.QtGui import QDropEvent, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QScrollArea, QTabWidget
from test_phase9_navigation_ui import app, window, board, tabs
from production_zero.core.state import FactoryHall
from production_zero.core.freight import FreightFacility
from production_zero.ui.building_tree import MIME
from production_zero.ui.event_feed import FeedEvent, EventFeedController, LIVE_ENTRY_LIMIT, HISTORY_LIMIT, PENDING_LIMIT
from production_zero.ui.freight_view import FreightView
from production_zero.ui.resource_categories import research_category
from production_zero.ui.resource_prices import base_price_text, price_tooltip
from production_zero.ui.unlock_tree_view import UnlockTreeNodeItem, build_unlock_tree_graph
from production_zero.persistence.sqlite_store import serialize_game_state


@pytest.fixture(autouse=True)
def dispose_test_windows(app):
    yield
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def populate(window):
    s = window._session_state
    for rid in ('iron_ore', 'coal', 'copper_ore', 'flour', 'steel', 'crude_oil', 'wood', 'natural_gas'):
        s.ensure_resource(rid).amount = 100
    s.freight.delivery_statistics.advance(60)
    s.freight.delivery_statistics.record('v', 'f', resource_id='iron_ore', sell=17, contract=4, consortium=6)
    o = window._global_resources
    o.toggle(); o.drawer._set_inventory_mode(True)
    QTest.qWait(20)
    return o


@pytest.mark.parametrize('width,columns', [(440,1), (750,2), (1080,3), (1320,3)])
def test_resource_cards_reflow_without_overlap_or_horizontal_scroll(window, app, width, columns):
    o = populate(window); o.resize(width, 620); app.processEvents()
    grid = o.drawer.summary
    assert grid._columns == columns
    cards = list(grid._items.values())
    for i, card in enumerate(cards):
        for other in cards[i+1:]: assert not card.geometry().intersects(other.geometry())
        assert card.width() >= 300 and card.height() == 244
        assert card.price.text() == base_price_text(card._resource_id, window._session_state, compact=True)
        assert research_category(card._resource_id).upper() in card.findChild(QLabel, 'resourceResearchCategory').text()
    scroll = o.drawer.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert scroll.verticalScrollBar().maximum() > 0
    scroll.verticalScrollBar().setValue(grid._resource_ids.index('iron_ore') // grid._columns * 252)
    app.processEvents()
    iron = grid._items['iron_ore']
    assert '17.0' in iron.freight.text() and '4.0' in iron.freight.text() and '6.0' in iron.freight.text()
    assert 'PLAN' in iron.production.text() and 'DELIVERED' in iron.freight.text()
    assert iron.property('deliveredPerMinute') == 27
    o.toggle(); o.toggle(); app.processEvents()
    assert o.width() == width


def test_overview_filters_use_research_domains_and_do_not_mutate_state(window, app):
    o = populate(window)
    before = serialize_game_state(window._session_state)
    o.search.setText('flour'); app.processEvents()
    assert set(o.drawer.summary._items) == {'flour'}
    assert research_category('flour') == 'Agriculture & Food'
    o.search.clear()
    o.category.setCurrentIndex(o.category.findData(research_category('flour')))
    assert o.drawer.summary._items and all(research_category(rid) == research_category('flour') for rid in o.drawer.summary._items)
    o.search.setText('not a resource')
    assert not o.drawer.summary._items and o.drawer.summary._empty.isVisible()
    assert serialize_game_state(window._session_state) == before


def test_resize_grip_changes_drawer_without_resizing_main_window(window, app):
    o = populate(window)
    before = window.size()
    grip = o.grip
    pos = grip.rect().center(); start = grip.mapToGlobal(pos)
    press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(pos), QPointF(start), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    move = QMouseEvent(QEvent.Type.MouseMove, QPointF(pos-QPoint(300,100)), QPointF(start-QPoint(300,100)), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(grip, press); app.sendEvent(grip, move); app.processEvents()
    assert o.width() == 780 and o.height() == 520
    assert window.size() == before
    assert o.drawer.summary._columns == 2
    window.resize(900,680); app.processEvents()
    assert o.geometry().right() < o.parentWidget().width() and o.geometry().bottom() < o.parentWidget().height()


@pytest.mark.parametrize('kind', ['resources', 'factory', 'freight'])
def test_row_drop_moves_only_presentation_order_and_survives_refresh(window, app, kind):
    s = window._session_state
    units = s.freight.facilities if kind == 'freight' else s.production_units(kind)
    for i in range(3):
        uid = f'p7-{i}'
        units[uid] = FreightFacility(uid, uid, 'garage_depot') if kind == 'freight' else FactoryHall(uid, uid, i)
    v = window.findChild(FreightView) if kind == 'freight' else board(window,kind)
    tabs(window).setCurrentWidget(v)
    v.refresh() if kind == 'freight' else v.refresh_view()
    app.processEvents()
    tree = v._facility_tree if kind == 'freight' else v._hall_tree
    original = tree.ids(); source = original[-1]
    mime = QMimeData(); mime.setData(MIME, (tree._token+':'+source).encode())
    target = tree.visualItemRect(tree.topLevelItem(0)).topLeft()+QPoint(5,2)
    before = serialize_game_state(s)
    event = QDropEvent(QPointF(target), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tree.dropEvent(event)
    assert event.isAccepted() and tree.ids() == (source,)+original[:-1]
    after = serialize_game_state(s)
    before['building_order'][kind] = list(tree.ids())
    assert after == before
    selected = v._selected_facility_id if kind == 'freight' else v._selected_hall_id
    v.refresh() if kind == 'freight' else v.refresh_view(); app.processEvents()
    tree = v._facility_tree if kind == 'freight' else v._hall_tree
    assert tree.ids() == (source,)+original[:-1]
    assert selected == (v._selected_facility_id if kind == 'freight' else v._selected_hall_id)
    # Foreign tree data and stale IDs cannot reorder this list.
    mime.setData(MIME, b'foreign:p7-0')
    bad = QDropEvent(QPointF(target), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    tree.dropEvent(bad); assert not bad.isAccepted()


def test_feed_shows_grouped_small_xp_cash_rp_inside_band(window, app, monkeypatch):
    import production_zero.ui.event_feed as module
    now=[100.0]; monkeypatch.setattr(module,'monotonic',lambda:now[0])
    f=window._event_feed; f.clear_events()
    before=serialize_game_state(window._session_state); geometry=window.centralWidget().geometry()
    for _ in range(50):
        f.push(FeedEvent('xp','Market sales',.25)); f.push(FeedEvent('cash','Market sales',2))
    f.push(FeedEvent('rp','Daily completion',1)); f.flush_pending()
    for _ in range(3):
        now[0]+=module.DISPLAY_INTERVAL_SECONDS; f._tick()
    QTest.qWait(450)
    assert len(f.history)==3 and len(f._entries)==3
    assert sum(e.amount for e in f.history if e.event_type=='xp')==12.5
    assert '+$100' in ' '.join(f.entry_texts()) and '+1 RP' in ' '.join(f.entry_texts())
    assert f._live_panel.parentWidget() is f
    assert all(e.y()==0 and f._live_panel.rect().contains(e.geometry()) for e in f._entries)
    assert window.centralWidget().geometry()==geometry
    assert serialize_game_state(window._session_state)==before
    now[0]+=600; f._tick(); assert len(f._entries)==3


def test_feed_bounded_clear_and_reward_observation_does_not_replay(window, app):
    from production_zero.core.research import grant_research_points
    from production_zero.core.company_xp import award_market_sale_xp
    f = window._event_feed; f.clear_events(); s=window._session_state
    c = EventFeedController(s, f)
    s.statistics.record_earnings(100)
    s.cash.amount -= 50  # Spending during the same observation must not hide income.
    grant_research_points(s,2,'Daily completion')
    award_market_sale_xp(s,100,board(window,'factory')._definitions)
    c.observe(); f.flush_pending()
    assert sum(e.amount for e in f.history if e.event_type=='cash') == 100
    assert sum(e.amount for e in f.history if e.event_type=='rp') == 2
    original = f.history; c.observe(); f.flush_pending(); assert f.history == original
    c.reset_baseline(); c.observe(); f.flush_pending(); assert f.history == original
    for i in range(200):
        f.push(FeedEvent('cash',str(i),1))
        f.push(FeedEvent('unlock',str(i)))
    assert len(f._pending) <= PENDING_LIMIT and len(f._entries) <= LIVE_ENTRY_LIMIT and len(f.history) <= HISTORY_LIMIT
    f.clear_events(); assert not f.history and not f._entries and not f._pending and not f._departing


def test_feed_overload_merges_amounts_instead_of_dropping_them(window):
    f=window._event_feed; f.clear_events()
    for i in range(200): f.push(FeedEvent('cash',f'Resource {i}',i+1))
    assert len(f._pending) <= PENDING_LIMIT
    f.flush_pending()
    assert sum(event.amount for event in f.history) == sum(range(1,201))
    assert len(f._entries) <= LIVE_ENTRY_LIMIT


def test_active_view_includes_freight_only_resource_then_expires(window, app):
    o=populate(window); s=window._session_state
    s.ensure_resource('iron_ore').amount=0
    o.drawer._set_inventory_mode(False)
    assert 'iron_ore' in o.drawer.summary._items
    assert o.drawer.summary._items['iron_ore'].property('deliveredPerMinute')==27
    s.freight.delivery_statistics.advance(60); o.refresh()
    assert 'iron_ore' not in o.drawer.summary._items


def test_all_resources_reflow_in_large_window_and_remain_scrollable(window, app):
    from production_zero.core.research import research_products
    window.resize(1920,1080)
    for rid in research_products(): window._session_state.ensure_resource(rid).amount=1
    o=window._global_resources; o.toggle(); o.resize(1800,900); app.processEvents()
    grid=o.drawer.summary
    assert len(grid._resource_ids)==len(research_products()) and grid._columns==5
    assert len(grid._items) <= 25
    o.resize(440,590); app.processEvents()
    assert grid._columns==1
    scroll=o.drawer.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum()==0 and scroll.verticalScrollBar().maximum()>0


def test_tree_prices_and_resource_categories_match_authoritative_data(window, app):
    from production_zero.core.research import research_products
    from production_zero.ui.resource_tiles import ResourceSelectionTile
    s=window._session_state; graph=build_unlock_tree_graph(board(window,'factory')._definitions)
    for rid,node in graph.nodes.items():
        item = UnlockTreeNodeItem(s,graph,node,context=False)
        assert item._price_text == base_price_text(rid,s,compact=True)
        assert price_tooltip(s,rid) in item.toolTip()
        assert research_category(rid) in item.toolTip()
    assert all(research_category(rid) for rid in research_products())
    tile=ResourceSelectionTile(resource_id='flour',title='Flour',subtitle='Materials',icon_key='flour',accent_key='resource')
    assert tile.property('researchCategory') == 'Agriculture & Food'
    assert tile.findChild(QLabel,'resourceSelectionTileSubtitle').text() == 'AGRICULTURE & FOOD'
    assert board(window,'factory').findChild(QWidget,'resourcesButton') is None
    for kind in ['resources','energy']:
        assert board(window,kind).findChild(QWidget,'resourcesButton') is not None
