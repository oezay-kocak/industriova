"""Offscreen QA captures for communications, ticker, and Unlock Tree focus."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.tools.ui_contact_sheet import _load_qa_fonts

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "progression-communications"


def events(app, count=8):
    for _ in range(count):
        app.processEvents()


def save(window, app, name):
    events(app)
    path = OUTPUT / name
    assert window.grab().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    captures = []
    dev = MainWindow(development_mode=True)
    dev.resize(1600, 900)
    dev.show()
    feed = dev.findChild(EventFeedWidget, "eventFeed")
    resources = dev.findChild(ResourcesViewV2)
    assert feed is not None and resources is not None
    feed.push(FeedEvent("xp", "Company Progress", 8))
    feed.push(FeedEvent("cash", "Coal Delivery", 480))
    feed.flush_pending()
    captures.append(save(dev, app, "01_ticker_dev_visible.png"))

    state = resources._state
    state.communications.add_unlocks(["resource.aluminum", "resource.natural_gas", "resource.clay", "resource.quartz"])
    feed.refresh_communications()
    feed._show_inbox()
    events(app)
    inbox_path = OUTPUT / "02_company_inbox_unread_unlocks.png"
    assert feed._inbox_menu.grab().save(str(inbox_path))
    captures.append(inbox_path)
    feed._inbox_menu.close()
    feed._show_history()
    events(app)
    history_path = OUTPUT / "03_ticker_history.png"
    assert feed._history_menu.grab().save(str(history_path))
    captures.append(history_path)
    feed._history_menu.close()

    tabs = dev.findChild(QTabWidget, "mainTabs")
    tabs.setCurrentWidget(resources)
    resources._open_unlock_tree()
    tree = resources._cached_unlock_tree_panel
    assert tree is not None
    tree.focus_resource("aluminum")
    tree.stage_filter.select_value("ASSEMBLY")
    captures.append(save(dev, app, "04_unlock_tree_cross_stage_focus.png"))
    dev.close()

    release = MainWindow(development_mode=False)
    release.resize(1600, 900)
    release.show()
    captures.append(save(release, app, "05_ticker_release_expanded.png"))
    release.close()
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
