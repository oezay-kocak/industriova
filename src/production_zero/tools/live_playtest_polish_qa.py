"""Five offscreen captures for the live-playtest follow-up."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "live-playtest-polish"


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
    window.resize(1600, 900)
    window.show()
    _settle(app)
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert feed is not None
    captures = []

    captures.append(_save(window, app, "01_global_header_clean_energy_bolt.png"))

    feed.push(FeedEvent("cash", "Iron Shipment Delivered", 480))
    feed.flush_pending()
    for _ in range(135):
        feed._advance_ticker()
    captures.append(_save(window, app, "02_ticker_delivery_cash_semantic_green.png"))

    feed._ticker_offset = feed._ticker_viewport.width() + 100
    feed._advance_ticker()
    feed.push(FeedEvent("pack", "Full Pack", count=1))
    feed.flush_pending()
    for _ in range(135):
        feed._advance_ticker()
    captures.append(_save(window, app, "03_ticker_pack_semantic_gold.png"))

    feed.push(FeedEvent("xp", "Company Progress", 24))
    feed.push(FeedEvent("contract", "Contract completed"))
    feed.flush_pending()
    feed._show_history()
    history = getattr(feed, "_history_panel")
    captures.append(_save(history, app, "04_history_matched_rounded_panel.png"))
    history.close()

    feed._state.communications.add_unlocks(["resource.aluminum"])
    feed.refresh_communications()
    feed._show_inbox()
    inbox = getattr(feed, "_inbox_panel")
    captures.append(_save(inbox, app, "05_inbox_matched_rounded_panel.png"))
    inbox.close()

    window.close()
    assert len(captures) == 5 and all(path.exists() for path in captures)
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
