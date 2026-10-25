"""Step 1: one visible projection per tick, lazy resource rows and fresh UI values."""
from copy import deepcopy
import pytest
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QScrollArea, QLabel
from PySide6.QtTest import QTest
from test_phase9_navigation_ui import app, window, board, tabs
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.freight_view import FreightView
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state
from production_zero.ui.resource_prices import price_tooltip
from production_zero.core.analytics import calculate_resource_flows


@pytest.fixture(autouse=True)
def dispose(app):
    yield
    for w in app.topLevelWidgets(): w.close(); w.deleteLater()
    app.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()


def full_overview(window,app):
    for stock in window._session_state.resources.values(): stock.amount=100
    o=window._global_resources
    o.toggle();app.processEvents();o._refresh_timer.stop()
    return o,o.drawer.summary,o.drawer.findChild(QScrollArea)


def tick(window,monkeypatch):
    from production_zero.ui import factory_view
    f=board(window,'factory')
    monkeypatch.setattr(factory_view,'perf_counter',lambda:100.25)
    f._last_update=100
    f._advance_simulation()


@pytest.mark.parametrize('name',['Factory','Resources','Energy','Freight','Contracts','Industrial Supply','Inventory','Research','Leaderboard'])
def test_each_tick_refreshes_only_active_tab_once(window,app,monkeypatch,name):
    t=tabs(window);t.setCurrentIndex(next(i for i in range(t.count()) if t.tabText(i)==name));app.processEvents()
    calls={}
    for i in range(t.count()):
        v=t.widget(i);label=t.tabText(i)
        method='refresh_runtime' if label in {'Factory','Resources','Energy','Freight'} else 'refresh'
        if not hasattr(v,method):continue
        original=getattr(v,method)
        def record(*args,_name=label,_original=original,**kwargs):
            calls[_name]=calls.get(_name,0)+1
            return _original(*args,**kwargs)
        monkeypatch.setattr(v,method,record)
    f=board(window,'factory');original=f._refresh_runtime_widgets;factory_calls=[]
    monkeypatch.setattr(f,'_refresh_runtime_widgets',lambda:(factory_calls.append(1),original())[1])
    previous=window._session_state.tick
    tick(window,monkeypatch)
    assert window._session_state.tick==previous+1
    # Inventory has no periodic tick projection; ownership changes refresh it through commands.
    assert calls==({} if name=='Inventory' else {name:1})
    assert len(factory_calls)==(1 if name=='Factory' else 0)


def test_hidden_main_window_keeps_simulation_but_skips_all_board_work(window,app,monkeypatch):
    calls=[]
    for kind in ['resources','factory','energy']:
        monkeypatch.setattr(board(window,kind),'_refresh_runtime_widgets',lambda:calls.append('board'))
    monkeypatch.setattr(window.findChild(FreightView),'refresh_runtime',lambda:calls.append('freight'))
    monkeypatch.setattr(window._global_header,'refresh',lambda:calls.append('header'))
    window.hide();previous=window._session_state.tick
    tick(window,monkeypatch)
    assert window._session_state.tick==previous+1 and not calls


def test_visible_standalone_factory_retains_its_own_refresh_without_callback(app,monkeypatch):
    from test_factory_view_v2 import _state_defs_bus
    from production_zero.ui import factory_view
    s,d,bus=_state_defs_bus();v=FactoryViewV2(s,bus,d);v.pause_simulation();v.show();app.processEvents()
    calls=[];monkeypatch.setattr(v,'_refresh_runtime_widgets',lambda:calls.append(1))
    monkeypatch.setattr(factory_view,'perf_counter',lambda:100.25)
    v._last_update=100;previous=s.tick;v._advance_simulation()
    assert s.tick==previous+1 and calls==[1]
    v.hide();v._last_update=100;v._advance_simulation();assert calls==[1]


def test_local_resource_drawer_summary_refreshes_once_per_tick(window,app,monkeypatch):
    v=board(window,'resources');tabs(window).setCurrentWidget(v);v._set_resources_drawer_open(True);app.processEvents()
    summary=v._resource_summary;calls=[];original=summary.refresh
    monkeypatch.setattr(summary,'refresh',lambda:(calls.append(1),original())[1])
    tick(window,monkeypatch);assert calls==[1]


def test_closed_resource_overview_does_no_work_even_for_timer_signals(window,app,monkeypatch):
    o=window._global_resources;grid=o.drawer.summary;calls=[]
    monkeypatch.setattr(grid,'_resource_flows',lambda:(calls.append(1),{})[1])
    for stock in window._session_state.resources.values():stock.amount=1
    assert not o._refresh_timer.isActive() and not grid._items
    QTimer.singleShot(0,o.refresh);app.processEvents()
    grid.refresh();o.refresh()
    assert not calls and not grid._items
    assert o._refresh_timer.parent() is o
    assert not any(t.parent() is window and t.interval()==1000 for t in window.findChildren(QTimer))


def test_resource_timer_only_runs_while_open_and_stays_fresh_after_hidden_changes(window,app,monkeypatch):
    o=window._global_resources;grid=o.drawer.summary
    calls=[];original=grid._resource_flows
    monkeypatch.setattr(grid,'_resource_flows',lambda:(calls.append(1),original())[1])
    o.toggle();app.processEvents();assert calls and o._refresh_timer.isActive()
    o.hide();calls.clear();assert not o._refresh_timer.isActive()
    o.search.setText('iron ore');window._session_state.resources['iron_ore'].amount=321
    QTimer.singleShot(0,o.refresh);QTest.qWait(20);assert not calls
    o.toggle();app.processEvents()
    assert grid._resource_ids==('iron_ore',) and grid._items['iron_ore'].stock.text()=='321 STORED'
    o._refresh_timer.setInterval(5);assert o._refresh_timer.isActive()
    for _ in range(25):
        QTest.qWait(20)
        if len(calls)>1:break
    assert len(calls)>1
    o.hide();calls.clear();QTest.qWait(25);assert not calls


@pytest.mark.parametrize('size',[(440,590),(750,620),(1080,620),(1800,900)])
def test_lazy_rows_reach_entire_catalogue_without_unbounded_widgets(window,app,size):
    window.resize(1920,1080);o,g,scroll=full_overview(window,app);o.resize(*size);app.processEvents()
    logical=g._resource_ids;assert len(logical)==353
    visited=set();step=max(1,scroll.viewport().height()//2)
    for value in range(0,scroll.verticalScrollBar().maximum()+step,step):
        scroll.verticalScrollBar().setValue(value)
        app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
        visited.update(g._items)
        assert len(g._items)<=g._columns*((scroll.viewport().height()//252)+4)
        items=list(g._items.values())
        for i,item in enumerate(items):
            assert item.width()>=300
            for other in items[i+1:]:assert not item.geometry().intersects(other.geometry())
    assert visited==set(logical)
    assert scroll.horizontalScrollBar().maximum()==0
    assert len(g.findChildren(QWidget,'resourceOverviewCard'))==len(g._items)


def test_offscreen_stock_changes_are_current_when_scrolled_into_view(window,app):
    o,g,scroll=full_overview(window,app)
    rid=g._resource_ids[-1];assert rid not in g._items
    window._session_state.resources[rid].amount=456
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());app.processEvents()
    assert g._items[rid].stock.text()=='456 STORED'
    o.search.setText('iron ore');assert g._resource_ids==('iron_ore',)
    o.search.clear();assert len(g._resource_ids)==353
    assert len(g._items)<353


def test_unchanged_cards_skip_label_and_price_formatting(window,app,monkeypatch):
    import production_zero.ui.resource_overview as module
    o,g,scroll=full_overview(window,app);o.search.setText('iron ore')
    card=g._items['iron_ore'];calls=[]
    monkeypatch.setattr(module,'base_price_text',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('unchanged price formatted')))
    monkeypatch.setattr(module,'price_tooltip',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('unchanged tooltip formatted')))
    for name in ['stock','production','freight','price']:
        label=getattr(card,name);original=label.setText
        monkeypatch.setattr(label,'setText',lambda text,_name=name,_original=original:(calls.append(_name),_original(text))[1])
    o.refresh();o.refresh();assert not calls
    window._session_state.resources['iron_ore'].amount=101;o.refresh();assert calls==['stock']


def test_research_and_respec_update_cached_effective_price(window,app):
    o,g,scroll=full_overview(window,app);o.search.setText('iron ore');s=window._session_state
    card=g._items['iron_ore'];before=card.toolTip()
    s.research.unlocked_node_ids.add('industry.metals.s1.major');o.refresh()
    assert price_tooltip(s,'iron_ore') in card.toolTip() and card.toolTip()!=before
    s.research.unlocked_node_ids.clear();o.refresh();assert card.toolTip()==before
    # A card recreated after scrolling/filtering can reuse only the current price data.
    o.search.setText('coal');o.search.setText('iron ore')
    assert g._items['iron_ore'].toolTip()==before


def test_changing_research_specialization_invalidates_only_current_price_data(window,app):
    from production_zero.core.research import specialization_catalog
    o,g,scroll=full_overview(window,app);o.search.setText('iron ore');s=window._session_state
    slot=next(slot for slot in specialization_catalog().values() if slot.tree_id=='industry.metals')
    s.research.unlocked_node_ids.add(slot.major_node_id);o.refresh()
    card=g._items['iron_ore'];before=card.toolTip()
    s.research.specializations[slot.id]='iron_ore';o.refresh()
    assert card.toolTip()!=before and price_tooltip(s,'iron_ore') in card.toolTip()
    s.research.specializations[slot.id]='copper_ore';o.refresh();assert card.toolTip()==before


def test_visible_freight_values_follow_warmup_new_deliveries_and_expiry(window,app):
    o,g,scroll=full_overview(window,app);o.search.setText('iron ore')
    card=g._items['iron_ore'];stats=window._session_state.freight.delivery_statistics
    assert 'measuring' in card.freight.text()
    stats.advance(30);stats.record('v','f',resource_id='iron_ore',sell=3,contract=4,consortium=5)
    o.refresh();assert card.property('deliveredPerMinute')==24 and 'MARKET 6.0' in card.freight.text()
    stats.advance(30);o.refresh()
    assert card.property('deliveredPerMinute')==12 and 'measuring' not in card.freight.text()
    stats.advance(30);o.refresh();assert card.property('deliveredPerMinute')==0


@pytest.mark.parametrize('action',['new','load'])
def test_session_change_drops_stale_catalogue_values_when_reopened(window,app,action):
    o,g,scroll=full_overview(window,app);old_card=next(iter(g._items.values()))
    dev=window.findChild(DevToolsView)
    if action=='new':dev._reset_callback()
    else:
        s=deserialize_game_state(serialize_game_state(window._session_state))
        for rid,stock in s.resources.items():stock.amount=42 if rid=='iron_ore' else 0
        dev._load_state_callback(s)
    for timer in window.findChildren(QTimer):timer.stop()
    assert not o.isVisible() and not o._refresh_timer.isActive()
    o.toggle();app.processEvents()
    expected={rid for rid,stock in window._session_state.resources.items() if stock.amount>0}
    assert set(g._resource_ids)==expected
    assert all(item._state is window._session_state for item in g._items.values())
    for rid,item in g._items.items():assert item.stock.text()==f'{window._session_state.resources[rid].amount:,.0f} STORED'


def test_resource_browsing_is_read_only_and_flows_keep_their_existing_meaning(window,app):
    o,g,scroll=full_overview(window,app)
    before=serialize_game_state(window._session_state)
    expected=calculate_resource_flows(window._session_state,board(window,'factory')._definitions)
    for width in [440,1080,750]:
        o.resize(width,620);app.processEvents()
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum());o.refresh()
        for rid,item in g._items.items():
            if rid in expected:assert item.property('producedPerMinute')==expected[rid].produced_per_minute
    o.search.setText('ore');o.category.setCurrentIndex(1);o.hide();o.toggle()
    assert serialize_game_state(window._session_state)==before


def test_closed_overview_does_not_construct_and_discard_a_legacy_world_summary(window,app,monkeypatch):
    from production_zero.ui import factory_view_v2, resource_overview
    from production_zero.ui.global_resources import GlobalResourcesOverlay
    def forbidden(*args,**kwargs):raise AssertionError('Closed overview built a resource summary')
    monkeypatch.setattr(factory_view_v2.FactoryV2HallResourceSummaryWidget,'__init__',forbidden)
    monkeypatch.setattr(resource_overview,'calculate_resource_flows',forbidden)
    for stock in window._session_state.resources.values():stock.amount=1
    view=board(window,'factory')
    o=GlobalResourcesOverlay(window._session_state,view._definitions,window._global_resources._resources,window)
    assert not o.drawer.summary._items and not o._refresh_timer.isActive()
    o.deleteLater()


def test_overview_uses_small_cached_icons_instead_of_decoding_full_size_pngs(window,app,monkeypatch):
    from production_zero.ui import resource_art
    calls=[];original=resource_art.resource_raster_image
    def record(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(resource_art,'resource_raster_image',record)
    resource_art._cached_scaled_resource_raster.cache_clear()
    o,g,scroll=full_overview(window,app)
    for value in range(0,scroll.verticalScrollBar().maximum()+600,600):
        scroll.verticalScrollBar().setValue(value)
        app.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
    assert len(g._resource_ids)==353
    assert not calls
