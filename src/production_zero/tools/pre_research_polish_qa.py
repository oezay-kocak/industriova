"""Three offscreen captures for Rail scrolling and exact Activity icon identity."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QScrollArea, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, BuildFreightFacility, InstallFreightCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import ActivityMessageCard, EventFeedWidget, FeedEvent
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_icons import ResourceIconWidget


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "pre-research-polish"


def _settle(app: QApplication, count: int = 12) -> None:
    for _ in range(count):
        app.processEvents()


def _save(widget, app: QApplication, name: str) -> Path:
    _settle(app)
    path = OUTPUT / name
    assert widget.grab().save(str(path))
    return path


def _assert_history_icon(feed: EventFeedWidget, resource_id: str) -> None:
    card = feed._history_panel.findChildren(ActivityMessageCard)[0]
    icon = card.findChild(ResourceIconWidget, "activityMessageIcon")
    assert icon is not None and icon.resource_id == resource_id


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

    tabs = window.findChild(QTabWidget, "mainTabs")
    freight = window.findChild(FreightView)
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert tabs is not None and freight is not None and feed is not None
    tabs.setCurrentWidget(freight)
    freight._command_bus.dispatch(AddCash(10_000))
    freight._command_bus.dispatch(BuildFreightFacility("rail_station"))
    for index in range(2):
        card_id = f"qa-train-{index}"
        freight._command_bus.dispatch(
            AddCard(create_card_instance(card_id, "freight.train", CardKind.FREIGHT, Rarity.COMMON))
        )
        freight._command_bus.dispatch(
            InstallFreightCard("rail_station-1", index, card_id, freight._definitions)
        )
    freight._select_facility("rail_station-1")
    _settle(app)
    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll is not None and scroll.widget() is not None
    installed = [
        card
        for card in scroll.widget().findChildren(QFrame, "freightSlotCard")
        if card.property("slotState") == "installed"
    ]
    assert len(installed) == 2
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert not scroll.horizontalScrollBar().isVisible()
    assert not scroll.verticalScrollBar().isVisible()
    captures = [_save(window, app, "01_rail_station_two_trains_clean_1600x900.png")]

    feed.flush_pending()
    feed._history.clear()
    feed.push(
        FeedEvent(
            "cash",
            "Copper Wire Shipment",
            327,
            count=3,
            group_key="market:copper_wire",
            resource_id="copper_wire",
        )
    )
    feed.flush_pending()
    feed._show_history()
    _assert_history_icon(feed, "copper_wire")
    captures.append(_save(feed._history_panel, app, "02_copper_wire_market_exact_icon.png"))
    feed._history_panel.close()

    feed.push(
        FeedEvent(
            "delivery",
            "Iron Ore Delivered to Daily Mining Contract",
            40,
            group_key="contract:daily-mining:iron_ore",
            resource_id="iron_ore",
        )
    )
    feed.flush_pending()
    feed._show_history()
    _assert_history_icon(feed, "iron_ore")
    captures.append(_save(feed._history_panel, app, "03_iron_ore_contract_exact_icon.png"))
    feed._history_panel.close()

    window.close()
    assert len(captures) == 3 and all(path.exists() for path in captures)
    print("\n".join(str(path.resolve()) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
