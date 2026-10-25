from __future__ import annotations

import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QLabel, QLineEdit, QTabWidget, QWidget

from production_zero.core.packs import FULL_PACK, PackInstance
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.card_hover import CardHoverInfoPopup, card_hover_icon
import production_zero.ui.event_feed as event_feed_module
from production_zero.ui.event_feed import (
    AGGREGATION_SECONDS,
    ACTIVITY_PANEL_HEADER_HEIGHT,
    ACTIVITY_PANEL_SIZE,
    ActivityMessageCard,
    EventFeedController,
    EventFeedWidget,
    FeedEvent,
)
from production_zero.ui.game_ui.icons import energy_bolt_polygon
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET, Theme


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


@pytest.mark.parametrize(
    "definition_id,family",
    [
        ("energy.solar_array", "solar"),
        ("energy.coal_power_plant", "coal"),
        ("energy.gas_power_plant", "gas"),
        ("energy.wind_turbine", "wind"),
        ("freight.truck", "truck"),
        ("freight.ship", "ship"),
        ("freight.aircraft", "aircraft"),
        ("freight.train", "train"),
    ],
)
def test_card_hover_uses_canonical_family_raster(definition_id: str, family: str) -> None:
    _app()
    icon = card_hover_icon(_definitions()[definition_id])
    assert isinstance(icon, QLabel)
    assert icon.objectName() == "cardHoverIcon"
    assert icon.property("assetFamily") == family
    assert icon.property("assetPath").endswith(f"{family if family not in {'solar', 'wind', 'coal', 'gas'} else {'solar': 'solar_array', 'wind': 'wind_turbine', 'coal': 'coal_power_plant', 'gas': 'gas_power_plant'}[family]}.png")
    assert icon.pixmap() is not None and not icon.pixmap().isNull()


@pytest.mark.parametrize(
    "rarity,expected",
    [
        ("common", Theme.RARITY_COMMON),
        ("uncommon", Theme.RARITY_UNCOMMON),
        ("rare", Theme.RARITY_RARE),
        ("epic", Theme.RARITY_EPIC),
        ("legendary", Theme.RARITY_LEGENDARY),
    ],
)
def test_card_hover_cleans_metadata_and_colors_values(rarity: str, expected: str) -> None:
    app = _app()
    parent = QWidget()
    popup = CardHoverInfoPopup(parent, embedded=True)
    popup.set_details(
        "Test Card",
        ResourceIconWidget("iron", size=42),
        [
            ("Rarity", rarity.title()),
            ("Bonus", "+8.9%"),
            ("Quantity", "4"),
            ("Available", "3"),
            ("In Use", "1"),
            ("Generation", "20 MW"),
        ],
        (rarity,),
    )
    parent.show()
    popup.show()
    app.processEvents()
    labels = {label.text() for label in popup.findChildren(QLabel, "cardHoverLabel")}
    assert {"QUANTITY", "AVAILABLE", "IN USE"}.isdisjoint(labels)
    assert "GENERATION" in labels
    rarity_value = popup._value_labels["Rarity"]
    bonus_value = popup._value_labels["Bonus"]
    assert rarity_value.property("rarity") == rarity
    assert rarity_value.palette().color(QPalette.ColorRole.WindowText).name() == expected
    assert bonus_value.palette().color(QPalette.ColorRole.WindowText).name() == Theme.GOOD
    parent.close()


def test_activity_band_replaces_overlay_and_keeps_ordered_history(monkeypatch) -> None:
    app=_app(); clock=[100.0]
    monkeypatch.setattr(event_feed_module,'monotonic',lambda:clock[0])
    window=MainWindow(); window.resize(1366,768); window.show(); app.processEvents()
    feed=window.findChild(EventFeedWidget)
    events=(FeedEvent('cash','Iron Shipment',480),FeedEvent('xp','Company Progress',24),
            FeedEvent('unlock','Copper Wire Unlocked'),FeedEvent('pack','Full Pack'),FeedEvent('contract','Contract Complete'))
    for event in events:
        feed.push(event); feed.flush_pending(); clock[0]+=event_feed_module.DISPLAY_INTERVAL_SECONDS
        feed._tick()
    QTest.qWait(450)
    assert feed.history==tuple(reversed(events))
    assert len(feed._entries)==3 and feed._live_panel.parentWidget() is feed
    assert all(e.y()==0 and feed._live_panel.rect().contains(e.geometry()) for e in feed._entries)
    assert not feed.findChildren(QWidget,'activityFeedStack')
    clock[0]+=600; feed._tick(); assert len(feed._entries)==3
    window.close()


def test_history_and_inbox_use_message_cards_icons_and_preserve_unlock_navigation() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    app.processEvents()
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert feed is not None
    feed.push(FeedEvent("cash", "Iron Shipment", 120))
    feed.flush_pending()
    feed._show_history()
    app.processEvents()
    history = window.findChild(QFrame, "eventFeedHistoryPanel")
    history_cards = history.findChildren(ActivityMessageCard) if history is not None else []
    assert history is not None and history_cards
    assert history_cards[0].findChild(ResourceIconWidget, "activityMessageIcon") is not None
    history.close()

    feed._state.communications.add_unlocks(["resource.aluminum"])
    feed.refresh_communications()
    assert feed._state.communications.unread_count == 1
    feed._show_inbox()
    app.processEvents()
    inbox = window.findChild(QFrame, "companyInboxPanel")
    cards = inbox.findChildren(ActivityMessageCard) if inbox is not None else []
    assert inbox is not None and len(cards) == 1
    card = cards[0]
    icon = card.findChild(ResourceIconWidget, "activityMessageIcon")
    assert icon is not None and icon.resource_id == "aluminum"
    assert feed._state.communications.unread_count == 0
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    app.processEvents()
    resources = window.findChild(ResourcesViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert tabs.currentWidget() is resources
    assert resources._cached_unlock_tree_panel._selected_resource_id == "aluminum"
    window.close()


def test_history_and_inbox_share_exact_geometry_and_translucent_rounded_shell() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    app.processEvents()
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert feed is not None
    feed.push(FeedEvent("cash", "Iron Shipment", 120))
    feed.flush_pending()

    feed._show_history()
    app.processEvents()
    history = feed._history_panel
    history_geometry = history.geometry()
    history_header = history.findChild(QFrame, "activityPanelHeader")
    assert history.size() == ACTIVITY_PANEL_SIZE
    assert history_header is not None and history_header.height() == ACTIVITY_PANEL_HEADER_HEIGHT
    assert history.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert not history.autoFillBackground()
    assert history.grab().toImage().pixelColor(0, 0).alpha() == 0
    history.close()
    app.processEvents()

    feed._state.communications.add_unlocks(["resource.aluminum"])
    feed._show_inbox()
    app.processEvents()
    inbox = feed._inbox_panel
    inbox_header = inbox.findChild(QFrame, "activityPanelHeader")
    assert inbox.geometry() == history_geometry
    assert inbox.size() == ACTIVITY_PANEL_SIZE
    assert inbox_header is not None and inbox_header.height() == ACTIVITY_PANEL_HEADER_HEIGHT
    assert inbox.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert inbox.grab().toImage().pixelColor(0, 0).alpha() == 0
    window.close()


@pytest.mark.parametrize(
    "event,accent",
    [
        (FeedEvent("xp", "Company Progress", 24), Theme.RESOURCE),
        (FeedEvent("cash", "Iron Shipment", 120), Theme.CASH),
        (FeedEvent("unlock", "Aluminum unlocked"), Theme.SAFETY_YELLOW),
        (FeedEvent("pack", "Full Pack"), Theme.SAFETY_YELLOW),
        (FeedEvent("contract", "Contract completed"), Theme.GOOD),
        (FeedEvent("delivery", "40 Iron Shipment Delivered"), Theme.GOOD),
    ],
)
def test_feed_uses_restrained_semantic_event_color(event: FeedEvent, accent: str) -> None:
    _app()
    feed = EventFeedWidget()
    feed.push(event); feed.flush_pending()
    assert accent in feed._entries[0].findChild(QLabel,'eventFeedAmount').styleSheet()


def test_feed_aggregates_micro_xp_and_keeps_important_events_at_capacity() -> None:
    _app(); feed=EventFeedWidget()
    for _ in range(40): feed.push(FeedEvent('xp','Company Progress',1))
    assert len(feed._pending)==1
    feed.flush_pending()
    assert feed.history[0].amount==40
    for i in range(40): feed.push(FeedEvent('xp',str(i),1))
    feed.flush_pending(); feed.push(FeedEvent('contract','Contract completed')); feed.flush_pending()
    assert len(feed._entries)<=3
    assert feed.history[0].event_type=='contract'


def test_micro_xp_appears_as_one_sum_after_aggregation_window(monkeypatch) -> None:
    _app(); clock=[100.0]
    monkeypatch.setattr(event_feed_module,'monotonic',lambda:clock[0])
    feed=EventFeedWidget()
    for _ in range(5): feed.push(FeedEvent('xp','Company Progress',1))
    clock[0]=100+AGGREGATION_SECONDS-.01; feed._tick(); assert not feed.history
    clock[0]+=.02; feed._tick()
    assert len(feed.history)==1 and feed.history[0].amount==5


def test_unrelated_high_value_events_are_not_swallowed_by_pending_aggregation() -> None:
    _app(); feed=EventFeedWidget()
    feed.push(FeedEvent('xp','Company Progress',1))
    feed.push(FeedEvent('cash','Copper Wire Shipment',109,group_key='market:copper_wire'))
    for kind in ('unlock','pack','contract'): feed.push(FeedEvent(kind,kind))
    assert not feed.history
    feed.flush_pending()
    assert {event.event_type for event in feed.history}=={'xp','cash','unlock','pack','contract'}


def test_feed_contains_no_scrolling_ticker() -> None:
    _app(); feed=EventFeedWidget()
    assert not feed.findChildren(QWidget,'eventFeedTickerTape')


def test_pack_feed_uses_new_pack_identity_and_type_even_when_inventory_count_is_unchanged() -> None:
    _app()
    state = GameState(rng_seed=7)
    state.packs.unopened.append(PackInstance("pack-old", "daily_mini", "daily"))
    feed = EventFeedWidget(state=state)
    controller = EventFeedController(state, feed)

    state.packs.unopened.clear()
    state.packs.unopened.append(PackInstance("pack-new", FULL_PACK, "contract"))
    controller.observe()
    feed.flush_pending()

    assert any("+1 PACK" in text and "Full Pack" in text for text in feed.entry_texts())


def test_energy_header_bolt_is_a_clean_closed_silhouette() -> None:
    polygon = energy_bolt_polygon(QRectF(0, 0, 100, 100))
    assert polygon.count() == 6
    assert all(0 <= point.x() <= 100 and 0 <= point.y() <= 100 for point in polygon)
    signed_double_area = sum(
        polygon[index].x() * polygon[(index + 1) % polygon.count()].y()
        - polygon[(index + 1) % polygon.count()].x() * polygon[index].y()
        for index in range(polygon.count())
    )
    assert abs(signed_double_area) > 1000


def test_supply_count_is_absent_and_controls_remain() -> None:
    _app()
    window = MainWindow()
    supply = window.findChild(SupplyView)
    assert supply is not None
    supply._show_section(1)
    assert supply.findChild(QLabel, "supplyCommonStatus") is None
    assert supply.findChild(QLineEdit, "supplySearch") is None
    assert supply.findChild(QComboBox, "supplyBuyQuantity") is None
    assert supply.findChild(QWidget, "supplyCategoryButtons") is not None
    assert supply.findChild(QComboBox, "supplySortSelect") is None
    window.close()
