from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabBar, QWidget

from production_zero.core.communications import CompanyCommunications
from production_zero.core.state import GameState
from production_zero.persistence.sqlite_store import SQLiteSaveStore
from production_zero.ui.event_feed import HISTORY_LIMIT, PENDING_LIMIT, EventFeedController, EventFeedWidget, FeedEvent
from production_zero.ui.main_window import ResponsiveMainTabWidget
from production_zero.ui.main_window import MainWindow
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.unlock_tree_view import UnlockTreeView, build_unlock_tree_graph, node_requirement_lines
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.resources import create_resource_inventory
from production_zero.core.progression import initialize_production_progress
from importlib.resources import files


def _app():
    return QApplication.instance() or QApplication([])


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def _state():
    resources = create_resource_inventory(load_resource_definitions(files("production_zero.data") / "resource_definitions.json"))
    state = GameState(rng_seed=909, resources=resources)
    initialize_production_progress(state, _definitions())
    return state


def test_grouped_unlock_message_read_state_and_save_roundtrip(tmp_path) -> None:
    state = _state()
    message = state.communications.add_unlocks(["resource.aluminum", "resource.quartz", "resource.aluminum"])
    assert message is not None and message.item_ids == ("resource.aluminum", "resource.quartz")
    assert state.communications.unread_count == 1
    state.communications.mark_read(message.message_id)
    assert state.communications.unread_count == 0

    store = SQLiteSaveStore(tmp_path / "communications.sqlite3")
    store.initialize()
    store.save("slot", state)
    loaded = store.load("slot")
    assert loaded.communications.messages == state.communications.messages
    assert loaded.communications.unread_count == 0


def test_controller_groups_unlock_batch_and_inbox_open_marks_read() -> None:
    _app()
    state = _state()
    feed = EventFeedWidget(state=state, definitions=_definitions())
    controller = EventFeedController(state, feed, definitions=_definitions())
    state.production_progress.pending_unlock_ids[:] = ["resource.aluminum", "resource.quartz"]
    controller.observe()
    assert len(state.communications.messages) == 1
    assert state.communications.unread_count == 1
    assert "1" in feed._inbox_button.text()
    feed._show_inbox()
    assert state.communications.unread_count == 0
    assert feed._inbox_button.text() == "INBOX"


def test_ticker_aggregation_and_session_bounds() -> None:
    _app()
    feed = EventFeedWidget()
    for _ in range(8):
        feed.push(FeedEvent("xp", "Company Progress", 1))
    feed.flush_pending()
    assert feed.entry_texts() and feed.history[0].amount == 8
    for index in range(HISTORY_LIMIT + 8):
        feed.push(FeedEvent("cash", f"Delivery {index}", 1))
    assert len(feed._pending) <= PENDING_LIMIT
    feed.flush_pending()
    assert len(feed._pending) <= PENDING_LIMIT
    for index in range(HISTORY_LIMIT + 8):
        feed.push(FeedEvent("cash", "Bounded Delivery", 1))
        feed.flush_pending()
    assert len(feed.history) == HISTORY_LIMIT


def test_navigation_and_ticker_keep_same_width_when_dev_tab_is_hidden() -> None:
    app = _app()
    _load_qa_fonts()
    release = MainWindow(development_mode=False)
    release.resize(1600, 900)
    release.show()
    app.processEvents()
    release_width = release.findChild(EventFeedWidget, "eventFeed").width()
    release_navigation = release.findChild(QTabBar, "mainNavigationTabs")
    dev = MainWindow(development_mode=True)
    dev.resize(1600, 900)
    dev.show()
    app.processEvents()
    dev_navigation = dev.findChild(QTabBar, "mainNavigationTabs")
    assert dev.findChild(EventFeedWidget, "eventFeed").width() == release_width
    assert dev_navigation.width() == release_navigation.width()
    assert sum(release_navigation.tabRect(index).width() for index in range(release_navigation.count())) == release_navigation.width()
    assert max(release_navigation.tabRect(index).width() for index in range(release_navigation.count())) - min(
        release_navigation.tabRect(index).width() for index in range(release_navigation.count())
    ) <= 16


def test_unlock_requirements_hide_completed_only_and_click_focus_crosses_stages() -> None:
    app = _app()
    state = _state()
    graph = build_unlock_tree_graph(_definitions())
    iron = graph.nodes["iron"]
    state.production_progress.lifetime_produced["iron_ore"] = 99
    assert "99 / 100" in node_requirement_lines(state, graph, iron)[0]
    state.production_progress.lifetime_produced["iron_ore"] = 100
    assert all("IRON ORE" not in line for line in node_requirement_lines(state, graph, iron))

    view = UnlockTreeView(state, _definitions(), lambda: None)
    view.resize(1200, 680)
    view.show()
    app.processEvents()
    view.select_resource("aluminum")
    view.stage_filter.select_value("ASSEMBLY")
    app.processEvents()
    assert view._selected_resource_id == "aluminum"
    assert "aluminum" in view._node_items
    assert 'BASE SELL PRICE:' in view._node_items['aluminum'].toolTip()
    view.select_resource("copper")
    assert view._selected_resource_id == "copper"
    view.clear_selection()
    assert view._selected_resource_id is None
