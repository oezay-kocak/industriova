"""Three offscreen captures for Activity Ticker aggregation and navigation fill."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabBar

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "activity-ticker-nav-polish"


def _settle(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def _save(widget, app: QApplication, name: str) -> Path:
    _settle(app)
    path = OUTPUT / name
    assert widget.grab().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT.glob("*.png"):
        stale.unlink()

    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(1920, 900)
    window.show()
    _settle(app)
    feed = window.findChild(EventFeedWidget, "eventFeed")
    navigation = window.findChild(QTabBar, "mainNavigationTabs")
    assert feed is not None and navigation is not None
    widths = [navigation.tabRect(index).width() for index in range(navigation.count())]
    assert sum(widths) == navigation.width()
    assert max(widths) - min(widths) <= 24

    release = MainWindow(development_mode=False)
    release.resize(1920, 900)
    release.show()
    _settle(app)
    release_feed = release.findChild(EventFeedWidget, "eventFeed")
    release_navigation = release.findChild(QTabBar, "mainNavigationTabs")
    assert release_feed.width() == feed.width()
    assert release_navigation.width() == navigation.width()
    release.close()

    captures = [_save(window, app, "01_navigation_equal_fill_dev.png")]

    for _ in range(5):
        feed.push(FeedEvent("xp", "Company Progress", 1))
    for earnings in (100, 109, 118):
        feed.push(FeedEvent("cash", "Copper Wire Shipment", earnings, group_key="market:copper_wire"))
    feed.push(FeedEvent("unlock", "Copper Wire Unlocked"))
    feed.flush_pending()
    feed._marquee_timer.stop()
    assert len(feed.ticker_events) == 3
    assert sum(event.amount for event in feed.ticker_events if event.event_type == "xp") == 5
    assert sum(event.amount for event in feed.ticker_events if event.event_type == "cash") == 327
    assert not any(event.event_type == "delivery" for event in feed.ticker_events)
    for _ in range(1_200):
        feed._advance_ticker()
        feed._marquee_timer.stop()
        if feed.ticker_offset >= 0:
            break
    assert feed.ticker_offset >= 0
    assert len(feed.visible_ticker_events()) == 3
    captures.append(_save(window, app, "02_aggregated_xp_market_unlock_ticker.png"))

    feed._show_history()
    history = feed._history_panel
    captures.append(_save(history, app, "03_aggregated_history.png"))
    history.close()
    window.close()

    assert len(captures) == 3 and all(path.exists() for path in captures)
    print("\n".join(str(path.resolve()) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
