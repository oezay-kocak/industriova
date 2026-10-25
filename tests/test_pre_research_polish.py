from __future__ import annotations

import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QScrollArea, QTabWidget, QTreeWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, BuildFreightFacility, InstallFreightCard
from production_zero.core.contracts import DAILY, ActiveContract, ContractOffer, receive_contract_delivery
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import MarketDeliveryResolution
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.event_feed import ActivityMessageCard, EventFeedController, EventFeedWidget, FeedEvent
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_art import has_resource_raster
from production_zero.ui.resource_icons import ResourceIconWidget


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


@pytest.mark.parametrize("size", [(1600, 900), (1366, 768)])
def test_rail_station_trains_keep_scroll_navigation_without_right_edge_control(size) -> None:
    app = _app()
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(*size)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    freight = window.findChild(FreightView)
    assert tabs is not None and freight is not None
    tabs.setCurrentWidget(freight)
    freight._command_bus.dispatch(AddCash(100_000))
    freight._command_bus.dispatch(BuildFreightFacility("rail_station"))
    from production_zero.core.commands import ExpandFreightFacility
    for _ in range(6):
        freight._command_bus.dispatch(ExpandFreightFacility("rail_station-1"))
    for index in range(8):
        card_id = f"rail-polish-train-{index}"
        freight._command_bus.dispatch(
            AddCard(create_card_instance(card_id, "freight.train", CardKind.FREIGHT, Rarity.COMMON))
        )
        freight._command_bus.dispatch(
            InstallFreightCard("rail_station-1", index, card_id, freight._definitions)
        )
    freight._select_facility("rail_station-1")
    app.processEvents()
    QTest.qWait(20)
    app.processEvents()

    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll is not None and scroll.widget() is not None
    cards = scroll.widget().findChildren(QFrame, "freightSlotCard")
    installed = [card for card in cards if card.property("slotState") == "installed"]
    assert len(installed) == 8
    assert all(card.property("freightFamily") == "train" for card in installed)
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert not scroll.horizontalScrollBar().isVisible()
    assert not scroll.verticalScrollBar().isVisible()
    assert max(card.geometry().right() for card in cards) <= scroll.viewport().width()

    vertical = scroll.verticalScrollBar()
    assert vertical.maximum() > 0
    vertical.setValue(vertical.maximum())
    assert vertical.value() == vertical.maximum()
    tree = freight.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None and tree.isVisible() and tree.topLevelItemCount() >= 2
    freight._select_facility("garage-1")
    assert freight._selected_facility_id == "garage-1"
    freight._select_facility("rail_station-1")
    assert freight._selected_facility_id == "rail_station-1"
    window.close()


def test_controller_and_history_preserve_exact_resource_ids_for_concrete_events() -> None:
    app = _app()
    definitions = _definitions()
    state = GameState(rng_seed=71)
    state.contracts.active[DAILY] = ActiveContract(
        ContractOffer("copper-wire-contract", DAILY, "Copper Wire", {"copper_wire": 100}, 0, 0, 0)
    )
    feed = EventFeedWidget(state=state, definitions=definitions)
    controller = EventFeedController(state, feed, definitions=definitions)

    state.freight.completed_market_deliveries.append(
        MarketDeliveryResolution(0, "iron-ore-market", "iron_ore", 12, 0, 12, 4, 48)
    )
    state.cash.add(48)
    receive_contract_delivery(state, "copper-wire-contract", "copper_wire", 20)
    state.production_progress.pending_unlock_ids.append("resource.copper")
    controller.observe()
    # Different unlock sources in the same aggregation window intentionally
    # become a resource-neutral summary. Flush between concrete event windows.
    feed.flush_pending()
    state.production_progress.pending_unlock_ids.append("resource.aluminum")
    controller.observe()
    feed.flush_pending()

    expected = {
        "Iron Ore Shipment": "iron_ore",
        "Copper Wire Delivered": "copper_wire",
        "Copper unlocked": "copper",
        "Aluminum unlocked": "aluminum",
    }
    for fragment, resource_id in expected.items():
        event = next(event for event in feed.history if fragment.lower() in event.label.lower())
        assert event.resource_id == resource_id
        assert has_resource_raster(resource_id)

    feed._show_history()
    app.processEvents()
    panel = feed._history_panel
    cards = panel.findChildren(ActivityMessageCard)
    for fragment, resource_id in expected.items():
        card = next(
            card
            for card in cards
            if fragment.upper() in card.findChild(QLabel, "activityMessageTitle").text()
        )
        icon = card.findChild(ResourceIconWidget, "activityMessageIcon")
        assert icon is not None
        assert icon.resource_id == resource_id
        assert icon.property("resourceId") == resource_id
    panel.close()
    feed.close()


def test_inbox_uses_exact_unlock_output_ids_and_semantic_fallbacks_remain_generic() -> None:
    app = _app()
    definitions = _definitions()
    state = GameState(rng_seed=72)
    state.communications.add_unlocks(["resource.copper", "resource.aluminum"])
    feed = EventFeedWidget(state=state, definitions=definitions)
    feed._show_inbox()
    app.processEvents()

    inbox_icons = feed._inbox_panel.findChildren(ResourceIconWidget, "activityMessageIcon")
    assert {icon.resource_id for icon in inbox_icons} == {"copper", "aluminum"}
    feed._inbox_panel.close()
    assert feed._semantic_icon("xp").resource_id == "company_progress"
    assert feed._semantic_icon("cash").resource_id == "cash"
    assert feed._semantic_icon("pack").resource_id == "pack"
    assert feed._semantic_icon("contract").resource_id == "contract"

    exact = FeedEvent("cash", "Copper Wire Shipment", 50, resource_id="copper_wire")
    feed.push(exact)
    feed.flush_pending()
    assert feed.history[0].resource_id == "copper_wire"
    assert feed._semantic_icon(exact.event_type, exact.resource_id).resource_id == "copper_wire"
    feed.close()
