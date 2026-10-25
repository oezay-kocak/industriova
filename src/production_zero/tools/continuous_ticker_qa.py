"""Two deterministic offscreen captures for the continuous Activity Ticker tape."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "continuous-ticker"


def _settle(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def _capture(window: MainWindow, app: QApplication, name: str) -> Path:
    _settle(app)
    path = OUTPUT / name
    assert window.grab().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT.glob("*.png"):
        stale.unlink()

    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(1600, 900)
    window.show()
    _settle(app)

    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert feed is not None
    events = (
        FeedEvent("cash", "Iron Shipment Delivered", 480),
        FeedEvent("xp", "Company Progress", 24),
        FeedEvent("unlock", "Copper Wire Unlocked"),
        FeedEvent("pack", "Full Pack"),
        FeedEvent("contract", "Contract Complete"),
    )
    for event in events:
        feed.push(event)
    feed.flush_pending()
    feed._marquee_timer.stop()
    assert feed.ticker_events == events
    assert len(feed._ticker_items) == len(events)

    for _ in range(1_200):
        feed._advance_ticker()
        feed._marquee_timer.stop()
        if len(feed.visible_ticker_events()) >= 3:
            break
    assert len(feed.visible_ticker_events()) >= 3
    tape_id = id(feed._ticker_tape)
    first_offset = feed.ticker_offset
    captures = [_capture(window, app, "01_three_events_visible.png")]

    for _ in range(72):
        feed._advance_ticker()
        feed._marquee_timer.stop()
    assert id(feed._ticker_tape) == tape_id
    assert feed.ticker_offset > first_offset
    assert feed.visible_ticker_events()
    captures.append(_capture(window, app, "02_same_tape_90px_later.png"))

    window.close()
    assert len(captures) == 2 and all(path.exists() for path in captures)
    print("\n".join(str(path.resolve()) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
