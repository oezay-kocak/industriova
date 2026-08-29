from __future__ import annotations

import os
import inspect
import re
from pathlib import Path
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import QEvent, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFrame, QLabel, QLineEdit, QListWidget, QPushButton, QProgressBar, QScrollArea, QSizePolicy, QSlider, QSpinBox, QStackedWidget, QTableView, QTableWidget, QTabWidget, QTreeWidget, QVBoxLayout, QWidget
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, AddIndustrialScrap, AddResource, AssignFreightCard, BuildFreightFacility, InstallCardInHall, InstallFreightCard, PurchaseHall, SelectMachineProduction, SellResource, SetResourceCapacity, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.contracts import DAILY, ActiveContract, ContractOffer
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import MachineType, Rarity
from production_zero.core.enums import CardKind
from production_zero.core.freight import MarketDeliveryResolution, build_freight_facility, expand_freight_facility
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState, HallSlot, MachineProductionState
from production_zero.core.storage_upgrades import inventory_storage_capacity, inventory_storage_upgrade_cost
import production_zero.ui.factory_view as factory_view_module
import production_zero.ui.event_feed as event_feed_module
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.event_feed import ENTRY_LIFETIME_SECONDS, EventFeedController, EventFeedWidget, FeedEvent
from production_zero.ui.factory_view import FactoryView, MachineSlotWidget
from production_zero.ui.freight_view import FreightView
from production_zero.ui.charts_view import ChartsView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame, InventoryView
from production_zero.ui.market_view import MarketView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.packs_view import BoosterPackTileFrame, PacksView
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.supply_view import COMMON_SUPPLY_CARD_HEIGHT, COMMON_SUPPLY_CARD_WIDTH, SupplyOfferCardFrame, SupplyView
from production_zero.ui.theme import APP_STYLESHEET, Theme
from production_zero.ui.game_ui.rendering.factory import _BLOCK_GLYPHS
from production_zero.ui.widget_lifecycle import clear_layout_safely
from production_zero.ui.window_geometry import clamp_window_geometry_to_available, clamp_window_size_to_available
from qt_top_level_guard import assert_no_visible_top_level_delta, drain_qt_events


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _style_block(selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\n\}}", APP_STYLESHEET, re.DOTALL)
    assert match is not None, f"Missing style selector: {selector}"
    return match.group("body")


def _flush_deferred_deletes() -> None:
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


def _visible_top_level_signature() -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (type(widget).__name__, widget.objectName())
            for widget in QApplication.topLevelWidgets()
            if widget.isVisible()
        )
    )


def _assert_factory_runtime_refs_valid(factory: FactoryView) -> None:
    if factory._kpi_strip is not None:
        assert is_qt_object_valid(factory._kpi_strip)
    if factory._resource_summary is not None:
        assert is_qt_object_valid(factory._resource_summary)
    assert all(is_qt_object_valid(widget) for widget in factory._slot_widgets.values())


def _slot_row_widgets(row: QWidget) -> list[QWidget]:
    layout = row.layout()
    assert layout is not None
    return [
        layout.itemAt(index).widget()
        for index in range(layout.count())
        if layout.itemAt(index).widget() is not None
    ]


def _inventory_cards_by_name(inventory_view: InventoryView) -> dict[str, QFrame]:
    return {
        card.findChild(QLabel, "inventoryCardName").text(): card
        for card in inventory_view.findChildren(QFrame, "inventoryCard")
    }


def _chart_resource_cards_by_name(charts: ChartsView) -> dict[str, QFrame]:
    return {
        card.findChild(QLabel, "chartResourceName").text(): card
        for card in charts.findChildren(QFrame, "chartResourceCard")
        if not card.isHidden()
    }


def _market_cards_by_name(market_view: MarketView) -> dict[str, QFrame]:
    return {
        card.findChild(QLabel, "marketCardName").text(): card
        for card in market_view.findChildren(QFrame, "marketCard")
    }


def _market_rows_by_name(market_view: MarketView) -> dict[str, QFrame]:
    return {
        row.findChild(QLabel, "marketRowResourceName").text(): row
        for row in market_view.findChildren(QFrame, "marketRow")
        if not row.isHidden()
    }


def _market_table_rows_by_name(market_view: MarketView) -> dict[str, int]:
    return {
        str(market_view._proxy_model.data(market_view._proxy_model.index(row, 0))): row
        for row in range(market_view._proxy_model.rowCount())
    }


def _market_table_text(market_view: MarketView, name: str, column: int) -> str:
    row = _market_table_rows_by_name(market_view)[name]
    return str(market_view._proxy_model.data(market_view._proxy_model.index(row, column)))


def _market_table_resource_id(market_view: MarketView, row: int) -> str:
    source_index = market_view._proxy_model.mapToSource(market_view._proxy_model.index(row, 0))
    return market_view._table_model.resource_id_at(source_index.row())


def _contract_cards_by_kind(contracts_view: ContractsView, kind: str) -> list[QFrame]:
    return [
        card
        for card in contracts_view.findChildren(QFrame, "contractCard")
        if card.property("kind") == kind
    ]


def _fund_contract_resources(contracts_view: ContractsView, requirements: dict[str, float], ratio: float = 1.0) -> None:
    for resource_id, required in requirements.items():
        stock = contracts_view._state.resources[resource_id]
        amount = required * ratio
        stock.capacity = max(stock.capacity, amount)
        stock.amount = amount


def _install_contract_test_freight(contracts_view: ContractsView) -> None:
    _install_ui_test_freight(
        contracts_view._state,
        contracts_view._command_bus,
        contracts_view._definitions,
        "ui-contract",
    )


def _install_ui_test_freight(state, bus, definitions, prefix: str) -> None:
    for facility_type in ("rail_station", "harbor", "airport"):
        build_freight_facility(state.freight, facility_type)
    facility_ids = {
        facility.facility_type: facility_id
        for facility_id, facility in state.freight.facilities.items()
    }
    for facility_type in ("rail_station", "harbor", "airport"):
        expand_freight_facility(state.freight.facilities[facility_ids[facility_type]])
    assignments = [
        ("steel", "market"),
        ("iron", "market"),
        ("iron_ore", "market"),
        ("coal", "market"),
        ("copper", "market"),
        ("copper_ore", "market"),
        ("iron_ore", "contract"),
        ("coal", "contract"),
        ("copper", "contract"),
        ("iron", "contract"),
        ("copper_ore", "contract"),
        ("steel", "contract"),
    ]
    assignment_index = 0
    for index in range(3):
        for facility_id, definition_id in (
            (facility_ids["airport"], "freight.aircraft.class1"),
            (facility_ids["garage_depot"], "freight.truck.class1"),
            (facility_ids["harbor"], "freight.ship.class1"),
            (facility_ids["rail_station"], "freight.train.class1"),
        ):
            card = create_card_instance(f"{prefix}-{facility_id}-{index}", definition_id, CardKind.FREIGHT, Rarity.COMMON)
            bus.dispatch(AddCard(card))
            bus.dispatch(InstallFreightCard(facility_id, index, card.card_id, definitions))
            resource_id, destination = assignments[assignment_index]
            assignment_index += 1
            bus.dispatch(AssignFreightCard(card.card_id, resource_id, destination))


def _advance_contract_freight(contracts_view: ContractsView) -> None:
    SimulationEngine(contracts_view._definitions).advance_time(contracts_view._state, 420)
    contracts_view.refresh()


def _deliver_contract_until_settled(contracts_view: ContractsView, kind: str, attempts: int = 8) -> None:
    for _ in range(attempts):
        active = contracts_view._state.contracts.active.get(kind)
        if active is None or active.status == "completed":
            return
        button = next(
            (button for button in contracts_view.findChildren(QPushButton, "deliverContractButton") if button.isEnabled()),
            None,
        )
        if button is None:
            return
        button.click()
        _advance_contract_freight(contracts_view)


def _common_supply_cards_by_name(supply_view: SupplyView) -> dict[str, QFrame]:
    return {
        card.findChild(QLabel, "supplyCardName").text(): card
        for card in supply_view.findChildren(QFrame, "commonSupplyCard")
        if not card.isHidden()
    }


def _visible_common_supply_cards(supply_view: SupplyView) -> list[QFrame]:
    return [card for card in supply_view._common_card_pool if not card.isHidden()]


def _daily_supply_cards(supply_view: SupplyView) -> list[QFrame]:
    return supply_view.findChildren(QFrame, "dailySupplyCard")


def _daily_freight_supply_cards(supply_view: SupplyView) -> list[QFrame]:
    return supply_view.findChildren(QFrame, "dailyFreightSupplyCard")


def _daily_machine_supply_cards(supply_view: SupplyView) -> list[QFrame]:
    return supply_view.findChildren(QFrame, "dailyMachineSupplyCard")


def _booster_pack_tiles(packs_view: PacksView) -> list[QFrame]:
    return [
        item.widget()
        for index in range(packs_view._grid.count())
        if (item := packs_view._grid.itemAt(index)) is not None
        and isinstance(item.widget(), QFrame)
        and item.widget().objectName() == "boosterPackTile"
    ]


def _pack_result_tiles(packs_view: PacksView) -> list[QFrame]:
    return [
        item.widget()
        for index in range(packs_view._result_grid.count())
        if (item := packs_view._result_grid.itemAt(index)) is not None
        and isinstance(item.widget(), QFrame)
        and item.widget().objectName() == "inventoryCard"
    ]


def _assert_icon_function_gap(card: QFrame, icon_name: str, function_name: str, minimum_gap: int = 3) -> None:
    if card.layout() is not None:
        card.layout().activate()
    card.updateGeometry()
    QApplication.processEvents()
    icon = card.findChild(ResourceIconWidget, icon_name)
    function = card.findChild(QLabel, function_name)
    assert icon is not None
    assert function is not None
    icon_bottom = icon.mapTo(card, icon.rect().bottomLeft()).y()
    function_top = function.mapTo(card, function.rect().topLeft()).y()
    assert function_top - icon_bottom >= minimum_gap


def _visible_extra_top_levels(main_window: MainWindow) -> list[QWidget]:
    return [
        widget
        for widget in QApplication.topLevelWidgets()
        if widget is not main_window
        and widget.isVisible()
        and not widget.objectName().startswith("pytest")
    ]


def _assert_no_visible_window_storm(main_window: MainWindow, baseline_visible: set[QWidget]) -> None:
    for _ in range(4):
        QApplication.processEvents()
    _flush_deferred_deletes()
    visible = {
        widget for widget in QApplication.topLevelWidgets()
        if widget is not main_window and widget.isVisible()
    }
    assert visible == baseline_visible


def _factory_selection_tiles(factory: FactoryView) -> list[QFrame]:
    return factory.findChildren(QFrame, "factoryCardSelectionTile")


def _factory_selection_tile_by_name(factory: FactoryView, card_name: str) -> QFrame:
    expected = card_name.lower()
    return next(
        tile
        for tile in _factory_selection_tiles(factory)
        if expected in tile.findChild(QLabel, "factoryCardSelectionTileName").text().lower()
    )


def _install_factory_card_from_selection(factory: FactoryView, card_name: str) -> None:
    tile = _factory_selection_tile_by_name(factory, card_name)
    assert tile.findChild(QPushButton, "installSelectedCardButton") is None
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _select_factory_default_production(factory: FactoryView, card_id: str) -> None:
    card = factory._state.cards[card_id]
    definition = factory._definitions[card.definition_id]
    assert isinstance(definition, MachineDefinition)
    production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
    factory._command_bus.dispatch(SelectMachineProduction(card_id, production.production_id, production.output_resource))
    factory.refresh_view()


def _open_production_selection_for_slot(factory: FactoryView, slot_index: int = 0) -> None:
    slot_widget = factory._slot_widgets[slot_index]
    assert slot_widget.findChild(QPushButton, "productionChangeButton") is None
    assert slot_widget.findChild(ResourceIconWidget, "resourceIcon") is not None
    slot_widget.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
        "position": lambda self: QPointF(20, 52),
    })())


def _production_selection_tiles(factory: FactoryView) -> list[QFrame]:
    return factory.findChildren(QFrame, "productionSelectionTile")


def _production_tile_names(factory: FactoryView) -> list[str]:
    return [
        tile.findChild(QLabel, "productionTileName").text().title()
        for tile in _production_selection_tiles(factory)
    ]


def _click_production_tile(factory: FactoryView, name: str) -> None:
    tile = next(tile for tile in _production_selection_tiles(factory) if tile.findChild(QLabel, "productionTileName").text().title() == name)
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _production_guide_tiles(factory: FactoryView) -> list[QFrame]:
    return factory.findChildren(QFrame, "productionGuideTile")


def _production_guide_tile_names(factory: FactoryView) -> list[str]:
    return [
        tile.findChild(QLabel, "productionGuideTileName").text().title()
        for tile in _production_guide_tiles(factory)
    ]


def _click_production_guide_tile(factory: FactoryView, name: str) -> None:
    tile = next(tile for tile in _production_guide_tiles(factory) if tile.findChild(QLabel, "productionGuideTileName").text().title() == name)
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _chain_stage_panels(factory: FactoryView) -> dict[str, QFrame]:
    return {
        panel.property("stage"): panel
        for panel in factory.findChildren(QFrame, "chainStagePanel")
    }


def _chain_stage_order(factory: FactoryView) -> list[str]:
    return [
        panel.property("stage")
        for panel in factory.findChildren(QFrame, "chainStagePanel")
    ]


def _chain_resource_names(panel: QFrame) -> set[str]:
    return {
        label.text()
        for label in panel.findChildren(QLabel, "chainResourceName")
    }


def _add_freight_inventory_card(freight_view: FreightView, card_id: str, definition_id: str) -> None:
    card = create_card_instance(card_id, definition_id, CardKind.FREIGHT, Rarity.COMMON)
    freight_view._command_bus.dispatch(AddCard(card))
    freight_view.refresh()


def _freight_slot_card(freight_view: FreightView, slot_index: int) -> QFrame:
    return next(
        card
        for card in freight_view.findChildren(QFrame, "freightSlotCard")
        if card.property("slotIndex") == slot_index
    )


def _freight_slot_grid_positions(freight_view: FreightView) -> dict[int, tuple[int, int]]:
    positions: dict[int, tuple[int, int]] = {}
    for card in freight_view.findChildren(QFrame, "freightSlotCard"):
        if card.property("slotState") == "locked":
            continue
        layout = card.parentWidget().layout()
        index = layout.indexOf(card)
        row, column, _row_span, _column_span = layout.getItemPosition(index)
        positions[card.property("slotIndex")] = (row, column)
    return positions


def _freight_slot_sizes(freight_view: FreightView) -> dict[int, tuple[int, int]]:
    return {
        card.property("slotIndex"): (card.width(), card.height())
        for card in freight_view.findChildren(QFrame, "freightSlotCard")
        if card.property("slotState") != "locked"
    }


def _freight_locked_slot_cards(freight_view: FreightView) -> list[QFrame]:
    return [
        card
        for card in freight_view.findChildren(QFrame, "freightSlotCard")
        if card.property("slotState") == "locked"
    ]


def _freight_facility_tree_item(freight_view: FreightView, facility_id: str) -> QTreeWidgetItem:
    tree = freight_view.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None
    for index in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(index)
        if item.data(0, Qt.ItemDataRole.UserRole) == facility_id:
            return item
    raise AssertionError(f"Missing freight facility item: {facility_id}")


def _select_freight_facility(freight_view: FreightView, facility_id: str) -> None:
    tree = freight_view.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None
    tree.setCurrentItem(_freight_facility_tree_item(freight_view, facility_id))


def _open_freight_drawer_for_slot(freight_view: FreightView, slot_index: int = 0) -> None:
    slot = _freight_slot_card(freight_view, slot_index)
    assert slot.findChild(QPushButton, "freightOpenDrawerButton") is None
    slot.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _freight_selection_cards(freight_view: FreightView) -> list[QFrame]:
    return freight_view.findChildren(QFrame, "freightSelectionCard")


def _freight_selection_card_by_id(freight_view: FreightView, card_id: str) -> QFrame:
    return next(card for card in _freight_selection_cards(freight_view) if card.property("cardId") == card_id)


def _install_freight_from_drawer(freight_view: FreightView, slot_index: int, card_id: str) -> None:
    _open_freight_drawer_for_slot(freight_view, slot_index)
    assert freight_view.findChild(QFrame, "freightCardSelectionView") is not None
    assert freight_view.findChild(QFrame, "freightCardSelectionDrawer") is None
    tile = _freight_selection_card_by_id(freight_view, card_id)
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _click_frame(frame: QFrame) -> None:
    frame.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _open_freight_assignment_view(freight_view: FreightView, card_id: str) -> None:
    panel = next(
        panel
        for panel in freight_view.findChildren(QFrame, "freightAssignmentPanel")
        if panel.property("cardId") == card_id
    )
    _click_frame(panel)
    assert freight_view.findChild(QFrame, "freightAssignmentSelectionView") is not None


def _freight_assignment_resource_tile(freight_view: FreightView, resource_id: str) -> QFrame:
    return next(
        tile
        for tile in freight_view.findChildren(QFrame, "freightAssignmentResourceTile")
        if tile.property("resourceId") == resource_id
    )


def _freight_destination_tile(freight_view: FreightView, destination_kind: str) -> QFrame:
    return next(
        tile
        for tile in freight_view.findChildren(QFrame, "freightDestinationTile")
        if tile.property("destinationKind") == destination_kind
    )


def _assign_freight_market_via_ui(freight_view: FreightView, card_id: str, resource_id: str, reserve: int = 100) -> None:
    _open_freight_assignment_view(freight_view, card_id)
    _click_frame(_freight_assignment_resource_tile(freight_view, resource_id))
    slider = freight_view.findChild(QSlider, "freightAssignmentReserveSlider")
    assert slider is not None
    slider.setValue(reserve)
    freight_view.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()


def test_main_window_has_expected_top_tabs() -> None:
    _app()
    window = MainWindow()

    tabs = window.findChild(QTabWidget, "mainTabs")

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Factory",
        "Freight",
        "Inventory",
        "Charts",
        "Market",
        "Contracts",
        "Industrial Supply",
        "Packs",
        "Leaderboard",
        "Dev",
    ]
    header = window.findChild(QFrame, "globalHeader")
    cash_amount = window.findChild(QLabel, "cashStatusAmount")
    energy_amount = window.findChild(QLabel, "energyStatusAmount")
    storage_amount = window.findChild(QLabel, "resourceStorageAmount")
    storage_button = window.findChild(QPushButton, "expandResourceStorageButton")
    progress_panel = window.findChild(QWidget, "companyProgressPanel")
    xp_bar = window.findChild(QProgressBar, "companyXpProgress")
    assert header is not None
    assert window.findChild(QFrame, "eventFeed") is not None
    assert cash_amount is not None
    assert cash_amount.text() == "$1,250"
    assert energy_amount is not None
    assert "MW" in energy_amount.text()
    assert storage_amount is not None
    assert " / " in storage_amount.text()
    assert storage_button is not None
    assert storage_button.text().startswith("Expand $")
    assert window.findChildren(QFrame, "topbarResourceChip")
    assert window.findChild(QFrame, "topbarEconomyCluster") is not None
    assert window.findChild(QFrame, "commandDeckTitlePanel") is not None
    assert window.findChild(QLabel, "commandDeckLabel").text() == "COMMAND DECK"
    assert window.findChild(QLabel, "cashStatusIcon").text() == "$"
    assert window.findChild(QLabel, "energyStatusIcon").text() == "MW"
    assert window.findChild(QLabel, "resourceStorageIcon").text() == "ST"
    assert progress_panel is not None
    assert xp_bar is not None
    assert window.findChild(QLabel, "companyLevelLabel").text() == "LEVEL 1 · FOUNDER"
    assert window.findChild(QLabel, "companyXpLabel").text().endswith("XP")


def test_event_feed_aggregates_same_events_and_keeps_types_separate() -> None:
    _app()
    feed = EventFeedWidget()

    for amount in (120, 800, 300, 450):
        feed.push(FeedEvent("cash", "Shipment", amount))
    feed.push(FeedEvent("xp", "Daily Contract", 450))
    feed.flush_pending()

    texts = feed.entry_texts()
    assert any("+$1,670" in text and "4 Shipments" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert len(texts) == 2


def test_event_feed_detects_cash_xp_contract_pack_and_header_feedback() -> None:
    _app()
    state = GameState(rng_seed=1)
    feed = EventFeedWidget()
    cash_highlights: list[tuple[float, float]] = []
    controller = EventFeedController(state, feed, lambda previous, current: cash_highlights.append((previous, current)))

    state.freight.completed_market_deliveries.append(MarketDeliveryResolution(
        delivery_id=0,
        shipment_id="shipment-1",
        resource_id="steel",
        delivered_amount=40,
        contract_amount=0,
        market_amount=40,
        market_price=8,
        market_earnings=320,
    ))
    state.freight.next_market_delivery_sequence = 1
    state.cash.add(320)
    state.statistics.record_earnings(320)
    controller.observe()

    offer = ContractOffer("daily-1", "daily", "Daily Steel", {"steel": 1}, 1200, 450, 0)
    state.contracts.active["daily"] = ActiveContract(offer)
    controller.observe()
    state.contracts.active["daily"].status = "completed"
    state.cash.add(1200)
    state.company.current_xp += 450
    grant_pack(state, DAILY_MINI_PACK, "contract:daily-1")
    controller.observe()
    feed.flush_pending()

    texts = feed.entry_texts()
    assert any("+$320" in text and "Steel Shipment" in text for text in texts)
    assert any("+$1,200" in text and "Contract Reward" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert any("DONE" in text and "Contract completed" in text for text in texts)
    assert any("+1" in text and "Pack" in text for text in texts)
    assert cash_highlights[-1] == (320, 1520)


def test_event_feed_reports_autorouted_market_delivery_split_without_double_sale() -> None:
    _app()
    state = GameState(rng_seed=2)
    feed = EventFeedWidget()
    controller = EventFeedController(state, feed)

    state.freight.completed_market_deliveries.append(MarketDeliveryResolution(
        delivery_id=0,
        shipment_id="partial-market-iron",
        resource_id="iron",
        delivered_amount=40,
        contract_amount=25,
        market_amount=15,
        market_price=3,
        market_earnings=45,
    ))
    state.freight.next_market_delivery_sequence = 1
    state.cash.add(45)
    state.statistics.record_earnings(45)

    controller.observe()
    feed.flush_pending()

    texts = feed.entry_texts()
    assert any("25 Iron to Contract" in text for text in texts)
    assert any("+$45" in text and "Iron Shipment" in text for text in texts)
    assert not any("+$120" in text for text in texts)
    assert not any("Income" in text for text in texts)


def test_main_window_runtime_market_route_autoroutes_contract_without_double_sale() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    freight = window.findChild(FreightView)
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert freight is not None
    assert feed is not None
    state = freight._state
    bus = freight._command_bus
    definitions = freight._definitions
    state.contracts.daily_period_index = 0
    state.contracts.active[DAILY] = ActiveContract(
        ContractOffer("runtime-iron", DAILY, "Runtime Iron", {"iron": 25}, 0, 0, 0)
    )
    _add_freight_inventory_card(freight, "runtime-market-truck", "freight.truck.class1")
    bus.dispatch(InstallFreightCard("garage-1", 0, "runtime-market-truck", definitions))
    bus.dispatch(AssignFreightCard("runtime-market-truck", "iron", "market", 0))
    bus.dispatch(SetResourceCapacity("iron", 100))
    bus.dispatch(AddResource("iron", 40))
    state.market.ensure_resource("iron").current_price = 3
    controller = EventFeedController(state, feed)
    starting_cash = state.cash.amount
    starting_earnings = state.statistics.total_earnings

    bus.dispatch(SellResource("iron", 40, definitions))
    assert next(iter(state.freight.outbound_shipments.values())).destination_kind == "market"
    SimulationEngine(definitions).advance_time(state, 60)
    controller.observe()
    feed.flush_pending()

    delivery = state.freight.completed_market_deliveries[-1]
    assert state.contracts.active[DAILY].delivered["iron"] == 25
    assert state.contracts.active[DAILY].status == "completed"
    assert delivery.contract_amount == 25
    assert delivery.market_amount == 15
    assert state.cash.amount == starting_cash + 45
    assert state.statistics.total_earnings == starting_earnings + 45
    assert state.freight.assignments["runtime-market-truck"].destination_kind == "market"
    assert state.freight.outbound_shipments == {}
    texts = feed.entry_texts()
    assert any("25 Iron to Contract" in text for text in texts)
    assert any("+$45" in text and "Iron Shipment" in text for text in texts)
    assert not any("+$120" in text for text in texts)


def test_event_feed_is_visual_only_tab_wide_and_entries_expire(monkeypatch) -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    feed = window.findChild(EventFeedWidget, "eventFeed")
    factory = window.findChild(FactoryView)
    assert tabs is not None
    assert feed is not None
    assert factory is not None
    starting_cash = factory._state.cash.amount
    starting_xp = factory._state.company.current_xp

    feed.push(FeedEvent("pack", "Full Pack"))
    feed.flush_pending()
    assert feed.entry_texts()
    tabs.setCurrentIndex(tabs.indexOf(window.findChild(MarketView)))
    assert window.findChild(EventFeedWidget, "eventFeed") is feed
    assert factory._state.cash.amount == starting_cash
    assert factory._state.company.current_xp == starting_xp

    entry = feed.findChild(QFrame, "eventFeedEntry")
    assert entry is not None
    monkeypatch.setattr(event_feed_module, "monotonic", lambda: 100.0 + ENTRY_LIFETIME_SECONDS + 1.0)
    entry.created_at = 100.0
    feed._tick()
    assert feed.entry_texts() == ()


def test_reward_feed_is_overlay_and_does_not_change_main_window_geometry() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert factory is not None
    assert tabs is not None
    assert feed is not None
    assert feed.parent() is window.centralWidget()

    central = window.centralWidget()
    before_window_size = window.size()
    before_minimum = window.minimumSize()
    before_minimum_hint = window.minimumSizeHint()
    before_central_geometry = central.geometry()
    before_tabs_geometry = tabs.geometry()

    controller = EventFeedController(factory._state, feed)
    offer = ContractOffer("daily-overlay", "daily", "Daily Overlay", {"steel": 1}, 1200, 450, 0)
    factory._state.contracts.active["daily"] = ActiveContract(offer)
    controller.observe()
    factory._state.contracts.active["daily"].status = "completed"
    factory._state.cash.add(1200)
    factory._state.company.current_xp += 450
    grant_pack(factory._state, DAILY_MINI_PACK, "contract:daily-overlay")
    controller.observe()
    feed.flush_pending()
    QApplication.processEvents()

    texts = feed.entry_texts()
    assert any("+$1,200" in text and "Contract Reward" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert any("DONE" in text and "Contract completed" in text for text in texts)
    assert any("+1" in text and "Pack" in text for text in texts)
    assert window.size() == before_window_size
    assert window.minimumSize() == before_minimum
    assert window.minimumSizeHint() == before_minimum_hint
    assert central.geometry() == before_central_geometry
    assert tabs.geometry() == before_tabs_geometry
    assert not feed.isWindow()


def test_freight_tab_facility_selection_and_factory_like_shell() -> None:
    from production_zero.ui.factory_view_v2 import FactoryV2ActiveIndicator, FactoryV2Board, FactoryV2HallOverview, FactoryV2LinePlate, FactoryV2TrackPanel

    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None

    tree = freight.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None
    assert [tree.topLevelItem(index).text(0) for index in range(tree.topLevelItemCount())] == ["Garage 1\n0 / 3 slots · 0 shipments"]
    assert freight.findChild(QLabel, "freightBayPlate").text() == "GARAGE"
    freight._state.cash.add(2_000)
    build_type = freight.findChild(QComboBox, "freightBuildFacilityType")
    build_type.setCurrentIndex(build_type.findData("rail_station"))
    freight.findChild(QPushButton, "buildFreightFacilityButton").click()
    tree = freight.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None
    assert [tree.topLevelItem(index).text(0) for index in range(tree.topLevelItemCount())] == [
        "Garage 1\n0 / 3 slots · 0 shipments",
        "Rail Station 1\n0 / 2 slots · 0 shipments",
    ]
    _select_freight_facility(freight, "rail_station-1")

    assert freight._selected_facility_id == "rail_station-1"
    assert freight.findChild(QFrame, "freightFacilityHeader").property("facilityTitle") == "RAIL STATION 1"
    assert freight.findChild(QFrame, "freightFacilityHeader").property("facilityMeta") == "0 / 2 slots   ·   0 active shipments"
    assert freight.findChild(QScrollArea, "freightSlotsScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert freight.findChild(QFrame, "freightKpiPanel") is None
    assert isinstance(freight.findChild(QFrame, "freightSlotsPanel"), FactoryV2Board)
    assert isinstance(freight.findChild(QFrame, "freightFacilityOverview"), FactoryV2HallOverview)
    assert isinstance(freight.findChild(QFrame, "freightBayTrack"), FactoryV2TrackPanel)
    assert isinstance(freight.findChild(QLabel, "freightBayPlate"), FactoryV2LinePlate)
    assert freight.findChild(QLabel, "freightBayPlate").text() == "RAIL STATION"
    assert freight.findChild(QFrame, "freightBayTrack").property("trackAccentActive") is False
    assert isinstance(freight.findChild(QFrame, "freightBayStatus"), FactoryV2ActiveIndicator)


def test_freight_facility_slots_are_horizontal_and_locked_slots_replace_expansion_row() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight.refresh()

    positions = _freight_slot_grid_positions(freight)
    assert positions == {0: (0, 0), 1: (0, 1), 2: (0, 2)}
    root_margins = freight.layout().contentsMargins()
    assert (root_margins.left(), root_margins.top(), root_margins.right(), root_margins.bottom()) == (0, 0, 0, 0)
    assert freight.layout().spacing() == 14
    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert freight.findChild(QFrame, "freightExpansionRow") is None
    assert freight.findChild(QPushButton, "expandFreightFacilityButton") is None
    locked = _freight_locked_slot_cards(freight)
    assert [card.property("slotIndex") for card in locked] == [3, 4, 5, 6, 7, 8]
    assert locked[0].property("unlockCost") == 300.0


def test_freight_empty_build_slot_matches_factory_slot_without_extra_labels() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    empty = _freight_slot_card(freight, 0)

    assert empty.property("slotState") == "empty"
    assert empty.width() == 166
    assert empty.height() == 264
    assert empty.findChild(QLabel, "freightSlotNumber") is None
    assert empty.findChild(QLabel, "freightEmptyAction") is None
    assert empty.findChild(QLabel, "freightEmptySlot") is None


def test_installed_freight_card_uses_factory_card_chassis_data_without_legacy_overlays() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-card-chassis-truck", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-card-chassis-truck")
    freight._command_bus.dispatch(AssignFreightCard("ui-card-chassis-truck", "steel", "market", 25))
    freight.refresh()

    card = _freight_slot_card(freight, 0)
    assert card.property("slotState") == "installed"
    assert card.property("cardTitle") == "TRUCK"
    assert card.property("cardMeta") == "MK1 · COMMON"
    assert card.property("cardDetail") == "CAPACITY 40"
    assert card.property("cardSecondary") == "ROUTE: STEEL > MARKET"
    assert card.property("cardStatusText") == "WAITING"
    assert card.property("shipmentActive") is False
    assert card.property("shipmentProgress") == 0.0
    for selector in (
        'QFrame#freightSlotCard[freightFamily="truck"]',
        'QFrame#freightSlotCard[freightFamily="train"]',
        'QFrame#freightSlotCard[freightFamily="ship"]',
        'QFrame#freightSlotCard[freightFamily="aircraft"]',
    ):
        assert "border-left" not in _style_block(selector)
    assert card.findChild(QLabel, "freightCardName").isHidden()
    assert card.findChild(QLabel, "freightStatusLabel").isHidden()
    assert card.findChild(QFrame, "freightRarityLine").isHidden()
    assert card.findChild(ResourceIconWidget, "freightTypeIcon").isHidden()
    assignment_panel = card.findChild(QFrame, "freightAssignmentPanel")
    assert assignment_panel.property("paintedFreightControl") is True
    assert assignment_panel.findChild(QLabel, "freightAssignmentResource").text() == "STEEL"
    assert assignment_panel.findChild(QLabel, "freightAssignmentResource").isHidden()
    remove = card.findChild(QPushButton, "freightRemoveButton")
    assert remove.text() == "CANCEL"
    assert remove.property("freightCardSecondary") is True
    assert remove.height() <= 18
    assignment_rect = QRect(assignment_panel.mapTo(card, assignment_panel.rect().topLeft()), assignment_panel.size())
    remove_rect = QRect(remove.mapTo(card, remove.rect().topLeft()), remove.size())
    assert assignment_rect.bottom() < remove_rect.top()


def test_installed_freight_truck_card_renders_transport_pictogram_in_art_stage() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-card-truck-icon", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-card-truck-icon")
    freight.refresh()

    card = _freight_slot_card(freight, 0)
    image = QImage(card.size(), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    card.render(image)

    dark_pixels = 0
    for y in range(88, 168):
        for x in range(36, 130):
            color = QColor(image.pixel(x, y))
            if color.alpha() > 120 and color.red() < 80 and color.green() < 80 and color.blue() < 80:
                dark_pixels += 1
    assert dark_pixels > 80


def test_all_freight_facilities_share_large_card_structure_and_vehicle_identity() -> None:
    from production_zero.ui.factory_view_v2 import FactoryV2LinePlate

    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight._command_bus.dispatch(AddCash(10_000))
    for facility_type in ("rail_station", "harbor", "airport"):
        freight._command_bus.dispatch(BuildFreightFacility(facility_type))
    freight.refresh()

    specs = {
        "garage-1": ("freight.truck.class1", "TRUCK", "GARAGE", 40),
        "rail_station-1": ("freight.train.class1", "TRAIN", "RAIL STATION", 180),
        "harbor-1": ("freight.ship.class1", "SHIP", "HARBOR", 600),
        "airport-1": ("freight.aircraft.class1", "AIRCRAFT", "AIRPORT", 24),
    }
    rendered_art_samples: dict[str, set[tuple[int, int]]] = {}
    card_ids: dict[str, str] = {}
    for facility_id, (definition_id, title, plate, capacity) in specs.items():
        card_id = f"ui-{title.lower()}-card"
        card_ids[facility_id] = card_id
        _add_freight_inventory_card(freight, card_id, definition_id)
        freight._command_bus.dispatch(InstallFreightCard(facility_id, 0, card_id, freight._definitions))
        freight.refresh()
        _select_freight_facility(freight, facility_id)
        QApplication.processEvents()
        _flush_deferred_deletes()
        scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
        assert scroll is not None and scroll.widget() is not None
        current_cards = scroll.widget().findChildren(QFrame, "freightSlotCard")
        card = next(card for card in current_cards if card.property("slotIndex") == 0)
        assert freight.findChild(QLabel, "freightBayPlate").text() == plate
        assert isinstance(freight.findChild(QLabel, "freightBayPlate"), FactoryV2LinePlate)
        assert card.property("slotState") == "installed"
        assert card.property("cardTitle") == title
        assert card.property("cardMeta") == "MK1 · COMMON"
        assert card.property("cardDetail") == f"CAPACITY {capacity}"
        assert card.property("cardSecondary") == "ASSIGN ROUTE >"
        assert card.property("shipmentActive") is False
        assert card.width() == 166
        assert card.height() == 264
        assert all((slot.width(), slot.height()) == (166, 264) for slot in current_cards)

        image = QImage(card.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        card.render(image)
        sample: set[tuple[int, int]] = set()
        for y in range(88, 168, 4):
            for x in range(36, 130, 4):
                color = QColor(image.pixel(x, y))
                if color.alpha() > 120 and color.red() < 80 and color.green() < 80 and color.blue() < 80:
                    sample.add((x, y))
        assert len(sample) > 8
        rendered_art_samples[title] = sample

    assert rendered_art_samples["TRAIN"] != rendered_art_samples["TRUCK"]
    assert rendered_art_samples["SHIP"] != rendered_art_samples["TRUCK"]
    assert rendered_art_samples["AIRCRAFT"] != rendered_art_samples["TRUCK"]

    resources_by_facility = {
        "garage-1": "steel",
        "rail_station-1": "iron",
        "harbor-1": "coal",
        "airport-1": "copper",
    }
    for facility_id, resource_id in resources_by_facility.items():
        card_id = card_ids[facility_id]
        freight._command_bus.dispatch(AssignFreightCard(card_id, resource_id, "market", 0))
        freight._command_bus.dispatch(SetResourceCapacity(resource_id, 1_000))
        freight._command_bus.dispatch(AddResource(resource_id, 250))
        freight._state.market.ensure_resource(resource_id).current_price = 8
        freight._command_bus.dispatch(SellResource(resource_id, 12, freight._definitions))
    SimulationEngine(freight._definitions).advance_time(freight._state, 10)

    for facility_id in specs:
        _select_freight_facility(freight, facility_id)
        freight.refresh_runtime()
        QApplication.processEvents()
        scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
        assert scroll is not None and scroll.widget() is not None
        card = next(card for card in scroll.widget().findChildren(QFrame, "freightSlotCard") if card.property("slotIndex") == 0)
        assert card.property("shipmentActive") is True
        assert 0.0 < card.property("shipmentProgress") < 1.0


def test_empty_and_installed_freight_slots_use_same_grid_geometry() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight.refresh()
    empty_positions = _freight_slot_grid_positions(freight)
    empty_sizes = _freight_slot_sizes(freight)
    assert empty_positions == {0: (0, 0), 1: (0, 1), 2: (0, 2)}

    for index in range(3):
        _add_freight_inventory_card(freight, f"ui-sync-truck-{index}", "freight.truck.class1")
        _install_freight_from_drawer(freight, index, f"ui-sync-truck-{index}")

    assert _freight_slot_grid_positions(freight) == empty_positions
    assert _freight_slot_sizes(freight) == empty_sizes


def test_mixed_freight_slots_keep_single_raster() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight.refresh()
    empty_sizes = _freight_slot_sizes(freight)
    _add_freight_inventory_card(freight, "ui-mixed-truck-0", "freight.truck.class1")
    _add_freight_inventory_card(freight, "ui-mixed-truck-2", "freight.truck.class1")

    _install_freight_from_drawer(freight, 0, "ui-mixed-truck-0")
    _install_freight_from_drawer(freight, 2, "ui-mixed-truck-2")

    assert _freight_slot_grid_positions(freight) == {0: (0, 0), 1: (0, 1), 2: (0, 2)}
    assert _freight_slot_sizes(freight) == empty_sizes
    assert _freight_slot_card(freight, 0).property("slotState") == "installed"
    assert _freight_slot_card(freight, 1).property("slotState") == "empty"
    assert _freight_slot_card(freight, 2).property("slotState") == "installed"


def test_freight_facility_expansion_adds_slots_right_then_wraps_without_scrollbar() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight._state.cash.add(10_000)
    freight.refresh()

    _click_frame(_freight_locked_slot_cards(freight)[0])
    assert len(freight._state.freight.facilities["garage-1"].slots) == 4
    assert _freight_slot_grid_positions(freight) == {
        0: (0, 0),
        1: (0, 1),
        2: (0, 2),
        3: (0, 3),
    }
    assert _freight_locked_slot_cards(freight)[0].property("slotIndex") == 4

    for _ in range(5):
        _click_frame(_freight_locked_slot_cards(freight)[0])
    assert len(freight._state.freight.facilities["garage-1"].slots) == 9
    positions = _freight_slot_grid_positions(freight)
    assert positions[0] == (0, 0)
    assert positions[4] == (0, 4)
    assert positions[5] == (0, 5)
    assert positions[8] == (0, 8)
    assert freight.findChild(QScrollArea, "freightSlotsScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert _freight_locked_slot_cards(freight) == []


def test_freight_locked_slot_unlocks_exactly_one_slot_at_a_time() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight._state.cash.add(10_000)
    freight.refresh()

    for _ in range(4):
        _click_frame(_freight_locked_slot_cards(freight)[0])

    facility = freight._state.freight.facilities["garage-1"]
    assert len(facility.slots) == 7
    locked_before = _freight_locked_slot_cards(freight)
    assert locked_before[0].property("slotIndex") == 7
    assert locked_before[1].property("slotIndex") == 8

    _click_frame(locked_before[0])

    assert len(facility.slots) == 8
    locked_after = _freight_locked_slot_cards(freight)
    assert [card.property("slotIndex") for card in locked_after] == [8]
    assert _freight_slot_grid_positions(freight)[7] == (0, 7)
    assert locked_after[0].parentWidget().layout().indexOf(locked_after[0]) >= 0


def test_installed_freight_card_keeps_horizontal_slot_position() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight.refresh()
    _add_freight_inventory_card(freight, "ui-horizontal-truck", "freight.truck.class1")

    _install_freight_from_drawer(freight, 0, "ui-horizontal-truck")

    positions = _freight_slot_grid_positions(freight)
    assert positions == {0: (0, 0), 1: (0, 1), 2: (0, 2)}
    assert _freight_slot_card(freight, 0).findChild(QLabel, "freightCardName").text() == "Freight Truck · Class I"


def test_freight_card_selection_view_filters_by_facility_family() -> None:
    _app()
    window = MainWindow()
    window.show()
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    _add_freight_inventory_card(freight, "ui-truck", "freight.truck.class1")
    _add_freight_inventory_card(freight, "ui-train", "freight.train.class1")

    _open_freight_drawer_for_slot(freight, 0)

    view = freight.findChild(QFrame, "freightCardSelectionView")
    assert view is not None
    assert freight.findChild(QFrame, "freightCardSelectionDrawer") is None
    assert freight.findChild(QListWidget, "freightCardSelectionList") is None
    assert freight.findChild(QScrollArea, "freightCardSelectionScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert any(card.property("cardId") == "ui-truck" for card in _freight_selection_cards(freight))
    assert all(card.property("cardId") != "ui-train" for card in _freight_selection_cards(freight))
    QApplication.processEvents()
    truck_card = next(card for card in _freight_selection_cards(freight) if card.property("cardId") == "ui-truck")
    _assert_icon_function_gap(truck_card, "freightTypeIcon", "freightSelectionFamily")

    freight.findChild(QLineEdit, "freightCardSearch").setText("truck")
    listed_after_search = _freight_selection_cards(freight)
    assert listed_after_search and all("truck" in card.property("freightFamily") for card in listed_after_search)


def test_freight_installation_targets_selected_facility_and_expanded_slot() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight._state.cash.add(1_500)
    build_type = freight.findChild(QComboBox, "freightBuildFacilityType")
    build_type.setCurrentIndex(build_type.findData("garage_depot"))
    freight.findChild(QPushButton, "buildFreightFacilityButton").click()
    garage_1 = freight._state.freight.facilities["garage-1"]
    garage_2 = freight._state.freight.facilities["garage-2"]
    _add_freight_inventory_card(freight, "ui-g1-truck", "freight.truck.class1")
    _add_freight_inventory_card(freight, "ui-g2-truck", "freight.truck.class1")
    _add_freight_inventory_card(freight, "ui-expanded-truck", "freight.truck.class1")
    _add_freight_inventory_card(freight, "ui-hidden-train", "freight.train.class1")

    _select_freight_facility(freight, "garage-1")
    _install_freight_from_drawer(freight, 0, "ui-g1-truck")

    assert garage_1.slots[0].card_id == "ui-g1-truck"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert _freight_slot_card(freight, 0).findChild(QLabel, "freightCardName").text() == "Freight Truck · Class I"
    assert _freight_slot_card(freight, 0).findChild(ResourceIconWidget, "freightTypeIcon") is not None
    assert _freight_slot_card(freight, 0).findChild(QFrame, "freightRarityLine") is not None
    assert "1 / 3" in _freight_facility_tree_item(freight, "garage-1").text(0)

    _select_freight_facility(freight, "garage-2")
    _install_freight_from_drawer(freight, 1, "ui-g2-truck")

    assert garage_2.slots[1].card_id == "ui-g2-truck"
    assert garage_1.slots[1].card_id is None

    freight._state.cash.add(500)
    _click_frame(_freight_locked_slot_cards(freight)[0])
    assert len(garage_2.slots) == 4
    _install_freight_from_drawer(freight, 3, "ui-expanded-truck")

    assert garage_2.slots[3].card_id == "ui-expanded-truck"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None

    _open_freight_drawer_for_slot(freight, 2)
    listed_ids = [card.property("cardId") for card in _freight_selection_cards(freight)]
    assert "ui-g1-truck" not in listed_ids
    freight.findChild(QPushButton, "freightCloseDrawerButton").click()
    assert freight.findChild(QFrame, "freightCardSelectionView") is None


def test_freight_drawer_selection_survives_refresh_before_install() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-refresh-truck", "freight.truck.class1")

    _open_freight_drawer_for_slot(freight, 2)
    assert _freight_selection_card_by_id(freight, "ui-refresh-truck") is not None

    freight.refresh()

    assert freight.findChild(QFrame, "freightCardSelectionView") is not None
    _freight_selection_card_by_id(freight, "ui-refresh-truck").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert freight._state.freight.facilities["garage-1"].slots[2].card_id == "ui-refresh-truck"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert _freight_slot_card(freight, 2).findChild(QLabel, "freightCardName").text() == "Freight Truck · Class I"


def test_freight_install_remove_and_assignment_controls() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-install", "freight.truck.class1")

    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-install").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-truck-install"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "UNASSIGNED"
    assert freight.findChild(QLabel, "freightAssignmentEmpty").text() == "ASSIGN ROUTE"

    _open_freight_assignment_view(freight, "ui-truck-install")
    assert freight.findChild(QScrollArea, "freightAssignmentResourceScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    freight.findChild(QLineEdit, "freightAssignmentSearch").setText("steel")
    resource_tiles = freight.findChildren(QFrame, "freightAssignmentResourceTile")
    assert resource_tiles
    assert all("steel" in tile.property("resourceId") for tile in resource_tiles)
    _click_frame(_freight_assignment_resource_tile(freight, "steel"))
    assert freight.findChild(QFrame, "freightDestinationTile") is None
    assert freight.findChild(QLabel, "freightAssignmentStepTitle").text() == "MARKET ROUTE · STEEL"
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    assert slider is not None
    slider.setValue(25)
    assert freight._state.freight.assignments.get("ui-truck-install") is None
    freight.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()

    assignment = freight._state.freight.assignments["ui-truck-install"]
    assert assignment.resource_id == "steel"
    assert assignment.destination_kind == "market"
    assert assignment.reserve_percent == 25
    assert freight.findChild(QFrame, "freightAssignmentSelectionView") is None
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "WAITING"
    assert freight.findChild(QLabel, "freightStatusLabel").property("detailStatus") == "WAITING · NO CARGO"
    assert freight.findChild(QLabel, "freightAssignmentResource").text() == "STEEL"
    assert freight.findChild(QLabel, "freightAssignmentDestination").text() == "MARKET"
    assert freight.findChild(QLabel, "freightReserveSummary").text() == "Reserve 25%"
    assert freight.findChild(QComboBox, "freightCargoSelect") is None
    assert freight.findChild(QComboBox, "freightDestinationSelect") is None

    freight.findChild(QPushButton, "freightRemoveButton").click()
    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-truck-install"
    assert "ui-truck-install" not in freight._state.freight.assignments
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "UNASSIGNED"
    assert freight.findChild(QLabel, "freightAssignmentEmpty").text() == "ASSIGN ROUTE"

    freight.findChild(QPushButton, "freightRemoveButton").click()
    assert freight._state.freight.facilities["garage-1"].slots[0].card_id is None
    assert "ui-truck-install" not in freight._state.freight.assignments


def test_freight_install_closes_drawer_before_single_structural_refresh(monkeypatch) -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-clean-install", "freight.truck.class1")

    _open_freight_drawer_for_slot(freight, 1)
    assert _freight_selection_card_by_id(freight, "ui-clean-install") is not None
    original_refresh = freight.refresh
    refresh_states = []

    def tracked_refresh() -> None:
        refresh_states.append((freight._drawer_open, freight._drawer_slot_index, freight._selected_card_id))
        original_refresh()

    monkeypatch.setattr(freight, "refresh", tracked_refresh)

    _freight_selection_card_by_id(freight, "ui-clean-install").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert refresh_states == [(False, None, None)]
    assert freight._state.freight.facilities["garage-1"].slots[1].card_id == "ui-clean-install"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert _freight_slot_card(freight, 1).findChild(QLabel, "freightCardName").text() == "Freight Truck · Class I"


def test_clearing_visible_embedded_widgets_does_not_make_them_top_level() -> None:
    _app()
    host = QFrame()
    host.setObjectName("lifecycleHost")
    layout = QVBoxLayout(host)
    child = QFrame(host)
    child.setObjectName("embeddedWidgetToClear")
    layout.addWidget(child)
    host.show()
    QApplication.processEvents()

    clear_layout_safely(layout)

    assert child.parentWidget() is host
    assert not child.isWindow()
    assert not child.isVisible()
    assert child.objectName() == ""
    _flush_deferred_deletes()
    host.close()


def test_freight_assign_route_does_not_create_visible_top_level_widgets() -> None:
    _app()
    window = MainWindow()
    window.setObjectName("mainWindow")
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    _add_freight_inventory_card(freight, "ui-route-top-level-truck", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-route-top-level-truck")
    before = _visible_top_level_signature()

    _open_freight_assignment_view(freight, "ui-route-top-level-truck")
    _click_frame(_freight_assignment_resource_tile(freight, "steel"))
    assert freight.findChild(QFrame, "freightDestinationTile") is None
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    assert slider is not None
    slider.setValue(25)
    freight.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()
    for _ in range(3):
        QApplication.processEvents()

    assert _visible_top_level_signature() == before
    _flush_deferred_deletes()
    assert freight.findChild(QFrame, "freightAssignmentSelectionView") is None
    assert freight._state.freight.assignments["ui-route-top-level-truck"].resource_id == "steel"


def test_freight_runtime_actions_do_not_create_visible_top_level_widgets() -> None:
    _app()
    window = MainWindow()
    window.setObjectName("mainWindow")
    window.resize(1280, 820)
    window.show()
    drain_qt_events()
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    freight._state.cash.add(5_000)
    freight.refresh()
    drain_qt_events()

    def expand_garage() -> None:
        _click_frame(_freight_locked_slot_cards(freight)[0])

    assert_no_visible_top_level_delta(expand_garage, allowed=(window,))
    assert len(freight._state.freight.facilities["garage-1"].slots) == 4

    _add_freight_inventory_card(freight, "ui-lifecycle-truck", "freight.truck.class1")

    def install_truck() -> None:
        _install_freight_from_drawer(freight, 0, "ui-lifecycle-truck")

    assert_no_visible_top_level_delta(install_truck, allowed=(window,))
    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-lifecycle-truck"

    def assign_route() -> None:
        _assign_freight_market_via_ui(freight, "ui-lifecycle-truck", "steel", 40)

    assert_no_visible_top_level_delta(assign_route, allowed=(window,))
    assert freight._state.freight.assignments["ui-lifecycle-truck"].resource_id == "steel"
    window.close()
    drain_qt_events()


def test_supply_truck_purchase_runtime_refresh_does_not_create_visible_top_level_widgets() -> None:
    _app()
    window = MainWindow()
    window.setObjectName("mainWindow")
    window.resize(1280, 820)
    window.show()
    drain_qt_events()
    supply = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert supply is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply)
    supply._bus.dispatch(AddCash(50_000))
    supply.refresh()
    supply.findChildren(QPushButton, "supplySectionButton")[1].click()
    supply.findChild(QComboBox, "supplyTypeFilter").setCurrentText("Freight")
    drain_qt_events()
    truck = next(
        card
        for card in _visible_common_supply_cards(supply)
        if card.findChild(QLabel, "supplyCardName").text() == "Freight Truck · Class I"
    )

    def buy_truck() -> None:
        truck.findChild(QPushButton, "buyCommonSupplyButton").click()

    before_cards = set(supply._state.cards)
    assert_no_visible_top_level_delta(buy_truck, allowed=(window,))
    new_cards = [card for card_id, card in supply._state.cards.items() if card_id not in before_cards]
    assert any(card.definition_id == "freight.truck.class1" for card in new_cards)
    window.close()
    drain_qt_events()


def test_freight_assignment_reserve_commits_only_when_applied() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-reserve-edit", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-reserve-edit")
    freight._command_bus.dispatch(AssignFreightCard("ui-reserve-edit", "steel", "market"))
    freight.refresh()
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 100

    _open_freight_assignment_view(freight, "ui-reserve-edit")
    assert freight.findChild(QFrame, "freightDestinationTile") is None
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    assert slider is not None
    slider.setValue(5)
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 5
    slider.setValue(50)
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 50
    slider.setFocus()

    freight.refresh_runtime()

    assert freight.findChild(QSlider, "freightAssignmentReserveSlider") is slider
    assert slider.value() == 50
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 50

    freight.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()

    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 50

    _open_freight_assignment_view(freight, "ui-reserve-edit")
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    slider.setValue(0)
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 0
    freight.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 0

    _open_freight_assignment_view(freight, "ui-reserve-edit")
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    slider.setValue(100)
    freight.findChild(QPushButton, "freightApplyMarketAssignmentButton").click()
    assert freight._state.freight.assignments["ui-reserve-edit"].reserve_percent == 100


def test_freight_facility_expansion_and_compact_cards() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight._state.cash.add(500)

    _click_frame(_freight_locked_slot_cards(freight)[0])

    assert len(freight._state.freight.facilities["garage-1"].slots) == 4
    _add_freight_inventory_card(freight, "ui-truck-compact", "freight.truck.class1")
    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-compact").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    card = freight.findChild(QFrame, "freightSlotCard")
    assert card.width() == 166
    assert card.height() == 264


def test_freight_factory_language_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    window.resize(1920, 1080)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    freight._command_bus.dispatch(AddCash(10_000))
    for facility_type in ("rail_station", "harbor", "airport"):
        freight._command_bus.dispatch(BuildFreightFacility(facility_type))
    preview_specs = {
        "garage-1": ("ui-preview-truck", "freight.truck.class1", "steel"),
        "rail_station-1": ("ui-preview-train", "freight.train.class1", "iron"),
        "harbor-1": ("ui-preview-ship", "freight.ship.class1", "coal"),
        "airport-1": ("ui-preview-aircraft", "freight.aircraft.class1", "copper"),
    }
    for facility_id, (card_id, definition_id, resource_id) in preview_specs.items():
        _add_freight_inventory_card(freight, card_id, definition_id)
        freight._command_bus.dispatch(InstallFreightCard(facility_id, 0, card_id, freight._definitions))
        freight._command_bus.dispatch(AssignFreightCard(card_id, resource_id, "market", 0))
        freight._command_bus.dispatch(SetResourceCapacity(resource_id, 1_000))
        freight._command_bus.dispatch(AddResource(resource_id, 250))
        freight._state.market.ensure_resource(resource_id).current_price = 8
        freight._command_bus.dispatch(SellResource(resource_id, 12, freight._definitions))
    SimulationEngine(freight._definitions).advance_time(freight._state, 10)
    _select_freight_facility(freight, "garage-1")
    freight.refresh()
    window.show()
    QApplication.processEvents()

    path = Path("artifacts") / "freight_factory_language_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = freight.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()
    for facility_id in preview_specs:
        _select_freight_facility(freight, facility_id)
        freight.refresh()
        QApplication.processEvents()
        facility_path = path.with_name(f"freight_factory_language_{facility_id.replace('-', '_')}_preview.png")
        facility_image = freight.grab().toImage()
        assert facility_image.save(str(facility_path))
        assert facility_path.exists()


def test_freight_waiting_below_reserve_status() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-waiting", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-truck-waiting")
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-waiting", "steel", "market"))
    freight._command_bus.dispatch(SetResourceCapacity("steel", 100))
    freight._command_bus.dispatch(AddResource("steel", 40))
    freight.refresh()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "WAITING"
    assert status.property("detailStatus") == "WAITING · BELOW RESERVE"


def test_freight_contract_assignment_has_no_reserve_and_waits_without_contract() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-contract-wait", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-truck-contract-wait")
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-contract-wait", "steel", "contract"))
    freight._command_bus.dispatch(SetResourceCapacity("steel", 100))
    freight._command_bus.dispatch(AddResource("steel", 40))
    freight.refresh()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "WAITING"
    assert status.property("detailStatus") == "WAITING · NO CONTRACT"
    assert freight.findChild(QSlider, "freightAssignmentReserveSlider") is None
    assert freight.findChild(QLabel, "freightAssignmentDestination").text() == "CONTRACT"
    assert freight.findChild(QLabel, "freightReserveSummary") is None


def test_freight_in_transit_locks_controls_and_reenables_after_arrival() -> None:
    _app()
    window = MainWindow()
    window.resize(1300, 900)
    window.show()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-transit", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-truck-transit")
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-transit", "steel", "market"))
    freight._command_bus.dispatch(SetResourceCapacity("steel", 100))
    freight._command_bus.dispatch(AddResource("steel", 10))
    freight._state.market.ensure_resource("steel").current_price = 8
    freight._command_bus.dispatch(SellResource("steel", 4, freight._definitions))

    SimulationEngine(freight._definitions).advance_time(freight._state, 30)
    freight.refresh()

    assert freight.findChild(QLabel, "freightStatusLabel").text() == "IN TRANSIT"
    assert freight.findChild(QFrame, "freightAssignmentPanel").property("clickEnabled") is True
    action = freight.findChild(QPushButton, "freightRemoveButton")
    progress = freight.findChild(QProgressBar, "freightShipmentProgress")
    transit_card = freight.findChild(QFrame, "freightSlotCard")
    assert action is not None
    assert progress is not None
    assert transit_card is not None
    assert action.text() == "CANCEL"
    assert action.isEnabled() is True
    assert progress.value() == 500
    assert transit_card.property("shipmentActive") is True
    assert transit_card.property("shipmentProgress") == pytest.approx(0.5)
    assert "Remaining: 30s" in [label.text() for label in freight.findChildren(QLabel, "freightMetaLabel")]
    _open_freight_assignment_view(freight, "ui-truck-transit")
    slider = freight.findChild(QSlider, "freightAssignmentReserveSlider")
    assert slider is not None
    assert slider.isEnabled()
    slider.setValue(20)
    assert freight._state.freight.assignments["ui-truck-transit"].reserve_percent == 20
    assert next(iter(freight._state.freight.outbound_shipments.values())).quantity == 4
    freight.findChild(QPushButton, "freightAssignmentBackButton").click()
    transit_card = freight.findChild(QFrame, "freightSlotCard")
    action = freight.findChild(QPushButton, "freightRemoveButton")
    progress = freight.findChild(QProgressBar, "freightShipmentProgress")
    assert action is not None
    assert progress is not None
    transit_card.layout().activate()
    QApplication.processEvents()
    progress_rect = QRect(progress.mapTo(transit_card, progress.rect().topLeft()), progress.size())
    action_rect = QRect(action.mapTo(transit_card, action.rect().topLeft()), action.size())
    assert progress_rect.bottom() < action_rect.top()
    assert transit_card.width() == 166
    assert transit_card.height() == 264
    assert transit_card.height() <= 300
    assert transit_card.findChild(QLabel, "freightCardName").text() == "Freight Truck · Class I"
    assert transit_card.findChild(QLabel, "freightCardClass").text() == "CLASS I"
    assert not transit_card.findChildren(QLabel, "freightStatLabel")

    action.click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "UNASSIGNED"
    assert status.property("detailStatus") == "UNASSIGNED"
    assert "ui-truck-transit" not in freight._state.freight.assignments
    assert freight._state.freight.outbound_shipments == {}
    assert freight.findChild(QLabel, "freightAssignmentEmpty").text() == "ASSIGN ROUTE"
    assert freight.findChild(QPushButton, "freightRemoveButton").text() == "REMOVE"

    freight._command_bus.dispatch(AssignFreightCard("ui-truck-transit", "copper", "market"))
    freight.refresh()
    assert freight._state.freight.assignments["ui-truck-transit"].resource_id == "copper"
    assert freight.findChild(QLabel, "freightAssignmentResource").text() == "COPPER"

    SimulationEngine(freight._definitions).advance_time(freight._state, 30)
    freight.refresh()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "WAITING"
    assert freight.findChild(QFrame, "freightAssignmentPanel").property("clickEnabled") is True
    assert freight.findChild(QPushButton, "freightRemoveButton").isEnabled() is True


def test_freight_tab_refreshes_shipment_progress_from_factory_simulation_tick(monkeypatch) -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert freight is not None
    assert tabs is not None
    factory.pause_simulation()
    _add_freight_inventory_card(freight, "ui-truck-live-progress", "freight.truck.class1")
    freight._command_bus.dispatch(InstallFreightCard("garage-1", 0, "ui-truck-live-progress", freight._definitions))
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-live-progress", "steel", "market", 70))
    freight._command_bus.dispatch(SetResourceCapacity("steel", 100))
    freight._command_bus.dispatch(AddResource("steel", 90))
    freight._state.market.ensure_resource("steel").current_price = 8
    tabs.setCurrentWidget(freight)
    freight.refresh()
    assignment_panel = freight.findChild(QFrame, "freightAssignmentPanel")
    assert assignment_panel is not None

    def fail_structural_refresh() -> None:
        raise AssertionError("Simulation ticks must not structurally refresh FreightView")

    monkeypatch.setattr(freight, "refresh", fail_structural_refresh)
    times = iter((101.0, 111.0, 161.0))
    monkeypatch.setattr(factory_view_module, "perf_counter", lambda: next(times))
    factory._last_update = 100.0

    factory._advance_simulation()

    assert freight.findChild(QFrame, "freightAssignmentPanel") is assignment_panel
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "IN TRANSIT"
    assert assignment_panel.property("clickEnabled") is True
    assert freight.findChild(QProgressBar, "freightShipmentProgress").value() == 0
    assert "Remaining: 1m 00s" in [label.text() for label in freight.findChildren(QLabel, "freightMetaLabel")]

    factory._advance_simulation()

    assert freight.findChild(QFrame, "freightAssignmentPanel") is assignment_panel
    assert assignment_panel.property("clickEnabled") is True
    assert freight.findChild(QProgressBar, "freightShipmentProgress").value() == 167
    assert "Remaining: 50s" in [label.text() for label in freight.findChildren(QLabel, "freightMetaLabel")]

    factory._advance_simulation()

    assert freight.findChild(QFrame, "freightAssignmentPanel") is assignment_panel
    assert assignment_panel.property("clickEnabled") is True
    assert freight._state.freight.assignments["ui-truck-live-progress"].resource_id == "steel"


def test_freight_assignment_view_survives_runtime_update_without_rebuild(monkeypatch) -> None:
    _app()
    window = MainWindow()
    window.show()
    factory = window.findChild(FactoryView)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert freight is not None
    assert tabs is not None
    factory.pause_simulation()
    _add_freight_inventory_card(freight, "ui-truck-assignment-live", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-truck-assignment-live")
    tabs.setCurrentWidget(freight)

    _open_freight_assignment_view(freight, "ui-truck-assignment-live")
    search = freight.findChild(QLineEdit, "freightAssignmentSearch")
    search.setText("steel")
    assignment_view = freight.findChild(QFrame, "freightAssignmentSelectionView")

    def fail_structural_refresh() -> None:
        raise AssertionError("Simulation ticks must not structurally refresh FreightView")

    monkeypatch.setattr(freight, "refresh", fail_structural_refresh)
    times = iter((101.0,))
    monkeypatch.setattr(factory_view_module, "perf_counter", lambda: next(times))
    factory._last_update = 100.0

    factory._advance_simulation()

    assert freight.findChild(QFrame, "freightAssignmentSelectionView") is assignment_view
    assert freight.findChild(QLineEdit, "freightAssignmentSearch") is search
    assert search.text() == "steel"


def test_dynamic_search_and_filter_rebuilds_do_not_spawn_visible_top_level_windows() -> None:
    _app()
    window = MainWindow()
    window.resize(1360, 860)
    window.show()
    QApplication.processEvents()
    baseline_visible = {
        widget for widget in QApplication.topLevelWidgets()
        if widget is not window and widget.isVisible()
    }

    freight = window.findChild(FreightView)
    factory = window.findChild(FactoryView)
    supply = window.findChild(SupplyView)
    inventory = window.findChild(InventoryView)
    market = window.findChild(MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert factory is not None
    assert supply is not None
    assert inventory is not None
    assert market is not None
    assert tabs is not None

    _add_freight_inventory_card(freight, "ui-search-storm-truck", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-search-storm-truck")
    tabs.setCurrentWidget(freight)
    _open_freight_assignment_view(freight, "ui-search-storm-truck")
    freight_search = freight.findChild(QLineEdit, "freightAssignmentSearch")
    freight_category = freight.findChild(QComboBox, "freightAssignmentCategoryFilter")
    assert freight_search is not None
    assert freight_category is not None
    for text in ("Copper", "Iron", "iron ore", "", "Steel", "Copper"):
        freight_search.setText(text)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(tile.parentWidget() is not None and not tile.isWindow() for tile in freight.findChildren(QFrame, "freightAssignmentResourceTile"))
    if freight_category.count() > 1:
        freight_category.setCurrentIndex(1)
        _assert_no_visible_window_storm(window, baseline_visible)
        freight_category = freight.findChild(QComboBox, "freightAssignmentCategoryFilter")
        assert freight_category is not None
        freight_category.setCurrentText("All")
        _assert_no_visible_window_storm(window, baseline_visible)

    factory._open_production_guide()
    guide_search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    guide_stage = factory.findChild(QComboBox, "productionGuideStageFilter")
    guide_category = factory.findChild(QComboBox, "productionGuideCategoryFilter")
    assert guide_search is not None
    assert guide_stage is not None
    assert guide_category is not None
    for text in ("Al", "Aluminum", "Iron", "", "Autonomous"):
        guide_search.setText(text)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(tile.parentWidget() is not None and not tile.isWindow() for tile in factory.findChildren(QFrame, "productionGuideTile"))
    guide_stage.setCurrentText("Processing")
    _assert_no_visible_window_storm(window, baseline_visible)
    guide_stage.setCurrentText("All")
    if guide_category.count() > 1:
        guide_category.setCurrentIndex(1)
        _assert_no_visible_window_storm(window, baseline_visible)
        guide_category.setCurrentText("All")

    tabs.setCurrentWidget(supply)
    supply_search = supply.findChild(QLineEdit, "supplySearch")
    supply_type = supply.findChild(QComboBox, "supplyTypeFilter")
    assert supply_search is not None
    assert supply_type is not None
    for text in ("Solar", "Freight", "Iron", "", "Processor"):
        supply_search.setText(text)
        QTest.qWait(220)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(card.parentWidget() is not None and not card.isWindow() for card in _visible_common_supply_cards(supply))
    supply_type.setCurrentText("Energy")
    _assert_no_visible_window_storm(window, baseline_visible)
    supply_type.setCurrentText("All")

    tabs.setCurrentWidget(inventory)
    inventory_search = inventory.findChild(QLineEdit, "inventorySearch")
    inventory_type = inventory.findChild(QComboBox, "inventoryTypeFilter")
    assert inventory_search is not None
    assert inventory_type is not None
    for text in ("Solar", "Truck", "Iron", ""):
        inventory_search.setText(text)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(card.parentWidget() is not None and not card.isWindow() for card in inventory.findChildren(QFrame, "inventoryCard"))
    inventory_type.setCurrentText("Energy")
    _assert_no_visible_window_storm(window, baseline_visible)

    tabs.setCurrentWidget(market)
    market_search = market.findChild(QLineEdit, "marketSearch")
    market_stage = market.findChild(QComboBox, "marketStageFilter")
    assert market_search is not None
    assert market_stage is not None
    for text in ("Copper", "Iron", "", "Steel"):
        market_search.setText(text)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(row.parentWidget() is not None and not row.isWindow() for row in market.findChildren(QFrame, "marketRow"))
    market_stage.setCurrentText("Processing")
    _assert_no_visible_window_storm(window, baseline_visible)


def test_freight_hover_info_updates_without_rebuild() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-hover", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "ui-truck-hover")
    slot = _freight_slot_card(freight, 0)

    freight._show_freight_hover("ui-truck-hover", slot)
    hover = freight.findChild(QFrame, "freightHoverInfo")
    assert hover is not None
    assert hover.isHidden() is False
    assert hover.parent() is freight
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert any(label.text() == "UNASSIGNED" for label in hover.findChildren(QLabel, "cardHoverValue"))

    freight._command_bus.dispatch(AssignFreightCard("ui-truck-hover", "steel", "market", 25))
    freight.refresh_runtime()

    assert freight.findChild(QFrame, "freightHoverInfo") is hover
    assert any("Steel -> Market" in label.text() for label in hover.findChildren(QLabel, "cardHoverValue"))
    assert any("Reserve 25%" in label.text() for label in hover.findChildren(QLabel, "cardHoverValue"))


def test_freight_card_selection_tiles_show_shared_hover_info() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-selection-hover", "freight.truck.class1")

    _open_freight_drawer_for_slot(freight, 0)
    tile = _freight_selection_card_by_id(freight, "ui-truck-selection-hover")
    freight._show_freight_hover("ui-truck-selection-hover", tile)

    hover = freight.findChild(QFrame, "freightHoverInfo")
    assert hover is not None
    assert hover.parent() is freight
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Freight Truck · Class I"
    values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert "Truck" in values
    assert "Class I" in values
    assert "Common" in values


def test_factory_view_can_install_and_remove_test_inventory_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    view = factory.findChild(QFrame, "factoryCardSelectionView")
    tiles = _factory_selection_tiles(factory)
    assert view is not None
    assert factory.findChild(QFrame, "cardSelectionDrawer") is None
    scroll = factory.findChild(QScrollArea, "factoryCardSelectionScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert len(tiles) == 3
    drill_tile = _factory_selection_tile_by_name(factory, "Extractor MK I")
    assert drill_tile.property("quantity") == 3
    assert drill_tile.findChild(ResourceIconWidget, "resourceIcon") is not None
    assert drill_tile.findChild(QFrame, "factoryCardSelectionRarityLine") is not None
    assert drill_tile.findChild(QLabel, "factoryCardSelectionTileFunction").text() == "EXTRACTOR"
    QApplication.processEvents()
    _assert_icon_function_gap(drill_tile, "resourceIcon", "factoryCardSelectionTileFunction")
    assert drill_tile.findChild(QLabel, "factoryCardSelectionTileCount").text() == "x3"
    assert drill_tile.findChild(QPushButton, "installSelectedCardButton") is None

    _install_factory_card_from_selection(factory, "Extractor MK I")

    assert factory._state.halls["hall-1"].slots[0].card_id == "test-drill-common-001"
    assert factory._state.inventory_card_stacks()[0].quantity == 2
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None

    factory._on_slot_clicked(0)

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert factory._state.inventory_card_stacks()[0].quantity == 3


def test_factory_runtime_installs_machine_without_default_resource_then_selects_production() -> None:
    _app()
    window = MainWindow()
    window.resize(1360, 860)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert tabs is not None
    tabs.setCurrentWidget(factory)
    factory.pause_simulation()
    starting_iron_ore = factory._state.resources["iron_ore"].amount

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    card_id = factory._state.halls["hall-1"].slots[0].card_id
    assert card_id == "test-drill-common-001"
    assert card_id not in factory._state.machine_production

    factory._simulation.advance_time(factory._state, 5.0)
    factory._refresh_runtime_widgets()
    state = factory._state.machine_production[card_id]
    slot_widget = factory._slot_widgets[0]
    assert state.selected_production_id is None
    assert state.target_resource_id == ""
    assert state.status == "unconfigured"
    assert slot_widget._primary_label() == "NO RESOURCE SELECTED"
    assert slot_widget._primary_value() == "Select"
    assert slot_widget._status_text() == "No Resource"
    assert factory._state.resources["iron_ore"].amount == starting_iron_ore

    _open_production_selection_for_slot(factory, 0)
    current = factory.findChild(QLabel, "productionCurrentLabel")
    assert current is not None
    assert current.text() == "Current: Not selected"
    assert "Iron Ore" in _production_tile_names(factory)
    _click_production_tile(factory, "Iron Ore")

    configured = factory._state.machine_production[card_id]
    assert configured.selected_production_id == "resource.iron_ore"
    assert configured.target_resource_id == "iron_ore"
    assert factory._slot_widgets[0]._primary_label() == "IRON ORE"


def test_factory_card_selection_tiles_show_shared_hover_info() -> None:
    _app()
    window = MainWindow()
    window.show()
    factory = window.findChild(FactoryView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert tabs is not None
    tabs.setCurrentWidget(factory)

    factory._on_slot_clicked(0)
    drill_tile = _factory_selection_tile_by_name(factory, "Extractor MK I")
    factory._show_card_selection_hover(drill_tile.property("cardId"), drill_tile)

    hover = factory.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    assert hover.isHidden() is False
    assert hover.parent() is factory
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Extractor MK I"
    values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert "Common" in values
    assert "Extractor" in values
    assert "3" in values


def test_card_tab_hovers_stay_embedded_without_extra_top_level_windows() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1360, 860)
    window.show()
    QApplication.processEvents()
    baseline_top_levels = set(app.topLevelWidgets())

    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryView)
    freight = window.findChild(FreightView)
    inventory = window.findChild(InventoryView)
    supply = window.findChild(SupplyView)
    packs = window.findChild(PacksView)
    assert tabs is not None
    assert factory is not None
    assert freight is not None
    assert inventory is not None
    assert supply is not None
    assert packs is not None

    def assert_no_new_visible_top_levels() -> None:
        for _ in range(4):
            QApplication.processEvents()
        _flush_deferred_deletes()
        new_visible_top_levels = [
            widget
            for widget in app.topLevelWidgets()
            if widget not in baseline_top_levels and widget is not window and widget.isVisible()
        ]
        assert new_visible_top_levels == []
        assert all(
            not widget.isVisible()
            for widget in app.topLevelWidgets()
            if widget not in baseline_top_levels and widget is not window
        )

    tabs.setCurrentWidget(factory)
    factory._on_slot_clicked(0)
    factory_tile = _factory_selection_tile_by_name(factory, "Extractor MK I")
    factory._show_card_selection_hover(factory_tile.property("cardId"), factory_tile)
    factory_hover = factory.findChild(QFrame, "cardHoverInfo")
    assert factory_hover is not None
    assert factory_hover.parent() is factory
    assert not factory_hover.isWindow()
    assert_no_new_visible_top_levels()

    _add_freight_inventory_card(freight, "hover-tab-truck", "freight.truck.class1")
    _install_freight_from_drawer(freight, 0, "hover-tab-truck")
    tabs.setCurrentWidget(freight)
    freight_slot = freight.findChild(QFrame, "freightSlotCard")
    assert freight_slot is not None
    freight._show_freight_hover("hover-tab-truck", freight_slot)
    freight_hover = freight.findChild(QFrame, "freightHoverInfo")
    assert freight_hover is not None
    assert freight_hover.parent() is freight
    assert not freight_hover.isWindow()
    assert_no_new_visible_top_levels()

    tabs.setCurrentWidget(inventory)
    inventory.refresh()
    inventory_card = inventory.findChild(QFrame, "inventoryCard")
    assert inventory_card is not None
    inventory_card.hovered.emit()
    inventory_hover = inventory.findChild(QFrame, "cardHoverInfo")
    assert inventory_hover is not None
    assert inventory_hover.parent() is inventory
    assert not inventory_hover.isWindow()
    assert_no_new_visible_top_levels()

    tabs.setCurrentWidget(supply)
    supply._apply_common_filter()
    supply_cards = _visible_common_supply_cards(supply)
    assert supply_cards
    supply._schedule_common_hover(supply_cards[0])
    supply._show_common_hover_for_current_card()
    supply_hover = supply.findChild(QFrame, "supplyCardHoverInfo")
    assert supply_hover is not None
    assert supply_hover.parent() is supply
    assert not supply_hover.isWindow()
    assert_no_new_visible_top_levels()

    grant_pack(packs._state, DAILY_MINI_PACK, "hover-tab-pack")
    packs._state.packs.last_opened_cards = [
        create_card_instance("hover-pack-truck", "freight.truck.class1", CardKind.FREIGHT, Rarity.COMMON)
    ]
    tabs.setCurrentWidget(packs)
    packs.refresh()
    pack_tiles = _pack_result_tiles(packs)
    assert pack_tiles
    pack_tiles[0].hovered.emit()
    pack_hover = packs.findChild(QFrame, "packResultCardHoverInfo")
    assert pack_hover is not None
    assert pack_hover.parent() is packs
    assert not pack_hover.isWindow()
    assert_no_new_visible_top_levels()


def test_factory_installed_machine_card_primary_layout_does_not_overlap_bottom_stats() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _select_factory_default_production(factory, "test-drill-common-001")
    slot_widget = factory._slot_widgets[0]
    slot_widget.resize(132, 132)
    QApplication.processEvents()

    icon_rect = slot_widget._primary_icon_rect()
    label_rect = slot_widget._primary_label_rect()
    bottom_stats = slot_widget._bottom_stats_rect()
    status_rect = slot_widget._status_rect()
    progress_rect = slot_widget._progress_rect()

    assert icon_rect.bottom() < label_rect.top()
    assert label_rect.bottom() < bottom_stats.top()
    assert bottom_stats.bottom() <= status_rect.top() + 1
    assert status_rect.bottom() <= progress_rect.top() + 1
    assert slot_widget._primary_icon is not None
    slot_widget._sync_primary_icon_geometry()
    assert slot_widget._primary_icon.geometry().bottom() <= round(label_rect.top())


def test_factory_card_selection_view_back_closes_immediately() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    assert factory.findChild(QFrame, "factoryCardSelectionView") is not None

    back = factory.findChild(QPushButton, "cardSelectionBackButton")
    assert back is not None
    back.click()

    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory._drawer_mode is None
    assert factory._drawer_slot_index is None
    assert factory._selected_card_id is None


def test_factory_removing_installed_card_does_not_open_drawer() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    assert factory._state.halls["hall-1"].slots[0].card_id is not None

    factory._on_slot_clicked(0)

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory.findChild(QFrame, "resourceDrawer") is None


def test_factory_removing_installed_card_clears_pending_selection_state() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")

    factory._on_slot_clicked(1)
    assert factory.findChild(QFrame, "factoryCardSelectionView") is not None
    assert factory._drawer_slot_index == 1

    factory._on_slot_clicked(0)

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory._drawer_mode is None
    assert factory._drawer_slot_index is None
    assert factory._selected_card_id is None


def test_factory_view_opens_visual_production_selection_view_for_extractor_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")

    assert factory.findChild(QComboBox, "productionSelect") is None
    _open_production_selection_for_slot(factory)

    view = factory.findChild(QFrame, "productionSelectionView")
    title = view.findChild(QLabel, "sectionLabel") if view is not None else None
    search = factory.findChild(QLineEdit, "productionSearchInput")
    category_filter = factory.findChild(QComboBox, "productionCategoryFilter")
    assert view is not None
    assert factory.findChild(QFrame, "productionSelectionDrawer") is None
    assert factory.findChild(QListWidget, "productionSelectionList") is None
    assert title is not None
    assert title.text() == "SELECT RESOURCE"
    assert search is not None
    assert category_filter is not None
    assert factory.findChild(QLabel, "productionCurrentLabel").text() == "Current: Not selected"
    option_names = _production_tile_names(factory)
    assert {"Iron Ore", "Coal", "Copper Ore", "Timber", "Wheat", "Natural Rubber"}.issubset(option_names)
    assert len(option_names) >= 49
    current_tiles = [tile for tile in _production_selection_tiles(factory) if tile.property("current") is True]
    assert current_tiles == []
    assert all(tile.findChild(ResourceIconWidget, "resourceIcon") is not None for tile in _production_selection_tiles(factory))

    search.setText("coal")
    assert _production_tile_names(factory) == ["Coal"]
    _click_production_tile(factory, "Coal")

    machine_state = factory._state.machine_production["test-drill-common-001"]
    assert machine_state.selected_production_id == "resource.coal"
    assert machine_state.target_resource_id == "coal"
    assert factory.findChild(QFrame, "productionSelectionView") is None


def test_factory_production_selection_grid_uses_available_width() -> None:
    _app()
    window = MainWindow()
    window.resize(1500, 900)
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _open_production_selection_for_slot(factory)

    host = factory.findChild(QWidget, "productionSelectionGridHost")
    assert host is not None
    host.resize(1320, 600)
    factory._on_production_grid_host_resized(host, None)

    grid = factory._production_selection_grid
    assert grid is not None
    positions = [grid.getItemPosition(index) for index in range(min(16, grid.count()))]
    columns = {position[1] for position in positions}
    rows = {position[0] for position in positions}
    assert factory._production_grid_columns() >= 6
    assert len(columns) >= 6
    assert len(rows) >= 2


def test_factory_view_opens_visual_recipe_selection_view_for_processor_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Processor MK I")

    _open_production_selection_for_slot(factory)

    view = factory.findChild(QFrame, "productionSelectionView")
    title = view.findChild(QLabel, "sectionLabel") if view is not None else None
    search = factory.findChild(QLineEdit, "productionSearchInput")
    assert view is not None
    assert factory.findChild(QFrame, "productionSelectionDrawer") is None
    assert title is not None
    assert title.text() == "SELECT RECIPE"
    assert search is not None
    option_names = _production_tile_names(factory)
    assert {"Iron", "Copper", "Steel", "Aluminum", "Polymer", "Flour"}.issubset(option_names)
    assert "Wheat" not in option_names

    search.setText("copper")
    assert "Copper" in _production_tile_names(factory)
    _click_production_tile(factory, "Copper")

    installed_card_id = factory._state.halls["hall-1"].slots[0].card_id
    assert installed_card_id is not None
    machine_state = factory._state.machine_production[installed_card_id]
    assert machine_state.selected_production_id == "recipe.processor.copper"
    assert machine_state.target_resource_id == "copper"
    assert factory.findChild(QFrame, "productionSelectionView") is None


def test_factory_production_selection_category_filter_and_back_keep_current_choice() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _open_production_selection_for_slot(factory)

    category_filter = factory.findChild(QComboBox, "productionCategoryFilter")
    assert category_filter is not None
    categories = {category_filter.itemText(index) for index in range(category_filter.count())}
    assert {"All", "Ores / Metals", "Minerals", "Oil & Gas", "Agriculture", "Forestry"}.issubset(categories)

    category_filter.setCurrentText("Oil & Gas")
    names = set(_production_tile_names(factory))
    assert {"Crude Oil", "Natural Gas"}.issubset(names)
    assert "Iron Ore" not in names

    installed_id = factory._state.halls["hall-1"].slots[0].card_id
    before = factory._state.machine_production.get(installed_id)
    back = factory.findChild(QPushButton, "productionSelectionBackButton")
    assert back is not None
    back.click()

    assert factory.findChild(QFrame, "productionSelectionView") is None
    assert factory._drawer_mode is None
    assert factory._production_drawer_card_id is None
    assert factory._state.machine_production.get(installed_id) == before


def test_factory_production_selection_view_limits_recipes_to_installed_machine_family() -> None:
    _app()
    for definition_id, expected_stage, expected_names, excluded_names in (
        ("machine.processor.mk1", MachineType.PROCESSOR, {"Steel", "Polymer", "Flour"}, {"Steel Components", "Industrial Equipment"}),
        ("machine.fabricator.mk1", MachineType.FABRICATOR, {"Steel Components", "Semiconductor Components", "Battery Components"}, {"Steel", "Industrial Equipment"}),
        ("machine.assembler.mk1", MachineType.ASSEMBLER, {"Industrial Equipment", "Microchip", "Packaged Food"}, {"Steel", "Semiconductor Components"}),
    ):
        window = MainWindow()
        factory = window.findChild(FactoryView)
        assert factory is not None
        card = create_card_instance(f"{definition_id}-test", definition_id, CardKind.MACHINE, Rarity.COMMON)
        factory._command_bus.dispatch(AddCard(card))
        factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, card.card_id))
        factory.refresh_view()

        _open_production_selection_for_slot(factory)
        assert factory.findChild(QFrame, "productionSelectionView") is not None
        names = set(_production_tile_names(factory))
        assert expected_names.issubset(names)
        assert excluded_names.isdisjoint(names)
        definition = factory._definitions[definition_id]
        assert isinstance(definition, MachineDefinition)
        assert definition.machine_type is expected_stage


def test_factory_production_guide_opens_with_search_stage_filter_and_icons() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    button = factory.findChild(QPushButton, "productionGuideButton")
    assert button is not None
    button.click()

    view = factory.findChild(QFrame, "productionGuideView")
    assert view is not None
    assert factory.findChild(QFrame, "factoryHallScroll") is None
    scroll = factory.findChild(QScrollArea, "productionGuideScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    names = set(_production_guide_tile_names(factory))
    assert {"Iron Ore", "Steel", "Steel Components", "Industrial Robot"}.issubset(names)
    assert all(tile.findChild(ResourceIconWidget, "resourceIcon") is not None for tile in _production_guide_tiles(factory)[:10])
    first_tile = _production_guide_tiles(factory)[0]
    assert first_tile.findChild(QPushButton) is None
    assert first_tile.findChild(ResourceIconWidget, "resourceIcon").width() >= 64
    assert first_tile.property("stageAccent") in {"extractor", "processor", "fabricator", "assembler"}

    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    assert search is not None
    search.setText("micro")
    assert "Microchip" in _production_guide_tile_names(factory)
    assert "Steel" not in _production_guide_tile_names(factory)

    search.setText("")
    stage_filter = factory.findChild(QComboBox, "productionGuideStageFilter")
    assert stage_filter is not None
    stage_filter.setCurrentText("Manufacturing")
    assert "Steel Components" in _production_guide_tile_names(factory)
    assert "Steel" not in _production_guide_tile_names(factory)


def test_factory_production_guide_button_opens_closes_and_survives_resize_events() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    assert factory is not None

    for width, height in ((1180, 780), (1440, 900), (980, 720)):
        button = factory.findChild(QPushButton, "productionGuideButton")
        assert button is not None
        button.click()
        QApplication.processEvents()
        guide = factory.findChild(QFrame, "productionGuideView")
        assert guide is not None
        assert factory.findChild(QWidget, "productionGuideGridHost") is not None
        window.resize(width, height)
        QApplication.processEvents()
        _flush_deferred_deletes()
        assert factory.findChild(QFrame, "productionGuideView") is guide
        back = factory.findChild(QPushButton, "productionGuideBackButton")
        assert back is not None
        back.click()
        QApplication.processEvents()
        _flush_deferred_deletes()
        assert factory.findChild(QFrame, "factoryHallScroll") is not None
        assert factory.findChild(QFrame, "productionGuideView") is None


def test_factory_production_guide_lifecycle_does_not_spawn_top_level_windows_or_resize_loop() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    assert factory is not None
    baseline_top_levels = set(QApplication.topLevelWidgets())
    baseline_visible_top_levels = {
        widget for widget in baseline_top_levels if widget.isVisible() and widget is not window
    }
    assert _visible_extra_top_levels(window) == []

    def settle_and_assert_stable() -> None:
        for _ in range(4):
            QApplication.processEvents()
        _flush_deferred_deletes()
        current_top_levels = set(QApplication.topLevelWidgets())
        unexpected_visible = {
            widget for widget in current_top_levels
            if widget not in baseline_top_levels and widget.isVisible()
        }
        assert unexpected_visible == set()
        assert {
            widget for widget in current_top_levels
            if widget.isVisible() and widget is not window
        } == baseline_visible_top_levels
        assert all(
            not widget.objectName().startswith(("productionGuide", "chainInspector"))
            for widget in current_top_levels
            if widget is not window
        )
        assert _visible_extra_top_levels(window) == []
        assert all(not widget.isWindow() for widget in factory.findChildren(QFrame, "productionGuideTile"))
        assert all(tile.parentWidget() is not None for tile in factory.findChildren(QFrame, "productionGuideTile"))

    for cycle in range(4):
        button = factory.findChild(QPushButton, "productionGuideButton")
        if button is not None:
            button.click()
        else:
            factory._open_production_guide()
        settle_and_assert_stable()

        guide = factory.findChild(QFrame, "productionGuideView")
        assert guide is not None
        search = factory.findChild(QLineEdit, "productionGuideSearchInput")
        stage_filter = factory.findChild(QComboBox, "productionGuideStageFilter")
        category_filter = factory.findChild(QComboBox, "productionGuideCategoryFilter")
        assert search is not None
        assert stage_filter is not None
        assert category_filter is not None
        search.setText("aluminum")
        settle_and_assert_stable()
        search.setText("")
        stage_filter.setCurrentText("Processing")
        settle_and_assert_stable()
        stage_filter.setCurrentText("All")
        if category_filter.count() > 1:
            category_filter.setCurrentIndex(1)
            settle_and_assert_stable()
            category_filter.setCurrentText("All")

        for width, height in ((1180, 760), (1500, 920), (1040, 760)):
            window.resize(width + cycle * 5, height)
            settle_and_assert_stable()

        _click_production_guide_tile(factory, "Aluminum Components")
        settle_and_assert_stable()
        assert factory.findChild(QFrame, "chainInspectorView") is not None
        assert "Processing" in _chain_stage_panels(factory)
        chain_back = factory.findChild(QPushButton, "chainInspectorBackButton")
        assert chain_back is not None
        chain_back.click()
        settle_and_assert_stable()
        assert factory.findChild(QFrame, "productionGuideView") is not None

        back = factory.findChild(QPushButton, "productionGuideBackButton")
        assert back is not None
        back.click()
        settle_and_assert_stable()
        assert factory.findChild(QFrame, "productionGuideView") is None
        assert factory.findChild(QFrame, "chainInspectorView") is None
        assert factory.findChildren(QFrame, "productionGuideTile") == []

    assert factory._guide_view_build_count <= 12
    assert factory._guide_grid_rebuild_count <= 80
    assert factory._guide_tile_create_count <= 12000
    assert factory._guide_grid_resize_count < 200
    assert _visible_extra_top_levels(window) == []
    window.close()
    app.processEvents()


def test_factory_chain_inspector_handles_extraction_processing_manufacturing_and_assembly_products() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._open_production_guide()

    cases = {
        "Iron Ore": {"Extraction"},
        "Steel": {"Extraction", "Processing"},
        "Steel Components": {"Extraction", "Processing", "Manufacturing"},
        "Industrial Robot": {"Extraction", "Processing", "Manufacturing", "Assembly"},
    }
    for product_name, expected_stages in cases.items():
        factory._open_production_guide()
        _click_production_guide_tile(factory, product_name)
        assert factory.findChild(QFrame, "chainInspectorView") is not None
        scroll = factory.findChild(QScrollArea, "chainInspectorScroll")
        assert scroll is not None
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert set(_chain_stage_panels(factory)) == expected_stages
        assert _chain_stage_order(factory) == [
            stage for stage in ["Extraction", "Processing", "Manufacturing", "Assembly"]
            if stage in expected_stages
        ]
        back = factory.findChild(QPushButton, "chainInspectorBackButton")
        assert back is not None
        back.click()
        assert factory.findChild(QFrame, "productionGuideView") is not None


def test_factory_chain_inspector_shows_multi_input_chain_and_machine_families() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Microchip")

    panels = _chain_stage_panels(factory)
    assert {"Extraction", "Processing", "Manufacturing", "Assembly"}.issubset(set(panels))
    connectors = factory.findChildren(QFrame, "chainFlowConnector")
    assert connectors
    assert all(connector.width() >= 30 for connector in connectors)
    extraction_names = _chain_resource_names(panels["Extraction"])
    assert {"Quartz", "Copper Ore", "Gold Ore"}.issubset(extraction_names)
    assert "High-Purity Silicon" in _chain_resource_names(panels["Processing"])
    assert "Semiconductor Components" in _chain_resource_names(panels["Manufacturing"])
    assert "Microchip" in _chain_resource_names(panels["Assembly"])

    families = {
        label.text()
        for label in factory.findChildren(QLabel, "chainMachineFamily")
    }
    assert {"Extractor", "Processor", "Fabricator", "Assembler"}.issubset(families)
    amount_labels = [label.text() for label in factory.findChildren(QLabel, "chainResourceAmount")]
    assert any("Input" in text for text in amount_labels)
    assert any("Output" in text for text in amount_labels)
    resource_boxes = factory.findChildren(QFrame, "chainResourceBox")
    assert len({box.width() for box in resource_boxes}) == 1
    assert {box.width() for box in resource_boxes} == {172}
    target_nodes = [
        node
        for node in factory.findChildren(QFrame, "chainResourceBox")
        if node.property("target") is True
    ]
    assert any(node.findChild(QLabel, "chainResourceName").text() == "Microchip" for node in target_nodes)


def test_factory_direct_hall_chain_navigation_preserves_production_selection_flow() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _select_factory_default_production(factory, "test-drill-common-001")
    slot_widget = factory._slot_widgets[0]
    slot_widget.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
        "position": lambda self: QPointF(slot_widget.width() - 14, 14),
    })())
    assert factory.findChild(QFrame, "chainInspectorView") is not None
    back = factory.findChild(QPushButton, "chainInspectorBackButton")
    assert back is not None
    back.click()
    assert factory.findChild(QFrame, "factoryHallScroll") is not None

    _open_production_selection_for_slot(factory)
    assert factory.findChild(QFrame, "productionSelectionView") is not None


def test_factory_hall_resource_summary_opens_chain_inspector_directly() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory.refresh_view()

    item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    button = item.findChild(QPushButton, "chainInfoButton")
    assert button is not None
    button.click()

    inspector = factory.findChild(QFrame, "chainInspectorView")
    assert inspector is not None
    assert "IRON ORE" in inspector.findChild(QLabel, "sectionLabel").text()
    back = factory.findChild(QPushButton, "chainInspectorBackButton")
    assert back is not None
    back.click()
    assert factory.findChild(QFrame, "factoryHallScroll") is not None


def test_factory_runtime_tick_keeps_production_guide_and_chain_state() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._open_production_guide()
    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    scroll = factory.findChild(QScrollArea, "productionGuideScroll")
    assert search is not None
    assert scroll is not None
    search.setText("steel")
    search.setCursorPosition(2)
    scroll.verticalScrollBar().setValue(1)
    guide_view = factory.findChild(QFrame, "productionGuideView")

    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()

    assert factory.findChild(QFrame, "productionGuideView") is guide_view
    assert search.text() == "steel"
    assert search.cursorPosition() == 2

    _click_production_guide_tile(factory, "Steel")
    chain_view = factory.findChild(QFrame, "chainInspectorView")
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    assert factory.findChild(QFrame, "chainInspectorView") is chain_view


def test_resource_icon_metadata_exists_for_all_active_resources_and_key_ores_differ() -> None:
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))

    assert resources
    for definition in resources.values():
        assert definition.icon_key
        assert definition.accent_key
        assert definition.category

    important = {
        "iron_ore": resources["iron_ore"].icon_key,
        "coal": resources["coal"].icon_key,
        "crude_oil": resources["crude_oil"].icon_key,
        "natural_gas": resources["natural_gas"].icon_key,
        "timber": resources["timber"].icon_key,
        "wheat": resources["wheat"].icon_key,
        "corn": resources["corn"].icon_key,
        "cotton": resources["cotton"].icon_key,
        "copper_ore": resources["copper_ore"].icon_key,
        "gold_ore": resources["gold_ore"].icon_key,
        "fruit": resources["fruit"].icon_key,
        "natural_rubber": resources["natural_rubber"].icon_key,
        "quartz": resources["quartz"].icon_key,
        "silica_sand": resources["silica_sand"].icon_key,
        "limestone": resources["limestone"].icon_key,
        "salt": resources["salt"].icon_key,
        "sulfur": resources["sulfur"].icon_key,
        "graphite": resources["graphite"].icon_key,
        "lithium_ore": resources["lithium_ore"].icon_key,
        "uranium_ore": resources["uranium_ore"].icon_key,
        "rare_earth_ore": resources["rare_earth_ore"].icon_key,
    }
    assert important == {
        "iron_ore": "ore_iron",
        "coal": "coal_chunk",
        "crude_oil": "oil_drop",
        "natural_gas": "flame",
        "timber": "log",
        "wheat": "wheat",
        "corn": "corn",
        "cotton": "cotton",
        "copper_ore": "ore_copper",
        "gold_ore": "ore_gold",
        "fruit": "fruit",
        "natural_rubber": "latex",
        "quartz": "crystal",
        "silica_sand": "sand",
        "limestone": "stone_block",
        "salt": "salt_crystal",
        "sulfur": "sulfur_crystal",
        "graphite": "graphite_block",
        "lithium_ore": "ore_lithium",
        "uranium_ore": "ore_uranium",
        "rare_earth_ore": "ore_rare_earth",
    }
    assert len(set(important.values())) == len(important)


def test_key_resource_icons_render_distinct_shapes() -> None:
    _app()
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))

    def pixels(resource_id: str) -> tuple[tuple[int, int, int, int], ...]:
        definition = resources[resource_id]
        icon = ResourceIconWidget(resource_id, definition.icon_key, definition.accent_key, size=64)
        image = icon.grab().toImage()
        return tuple(
            image.pixelColor(x, y).getRgb()
            for y in range(0, image.height(), 4)
            for x in range(0, image.width(), 4)
        )

    rendered = {
        resource_id: pixels(resource_id)
        for resource_id in (
            "iron_ore",
            "copper_ore",
            "gold_ore",
            "coal",
            "crude_oil",
            "natural_gas",
            "timber",
            "wheat",
            "corn",
            "cotton",
            "fruit",
            "natural_rubber",
            "silica_sand",
            "limestone",
            "salt",
            "sulfur",
            "graphite",
            "uranium_ore",
        )
    }

    assert len(set(rendered.values())) == len(rendered)


def test_factory_runtime_tick_keeps_open_production_selection_view_state_and_updates_simulation() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._on_slot_clicked(1)
    _install_factory_card_from_selection(factory, "Solar Array MK I")
    _open_production_selection_for_slot(factory)

    view = factory.findChild(QFrame, "productionSelectionView")
    search = factory.findChild(QLineEdit, "productionSearchInput")
    scroll = factory.findChild(QScrollArea, "productionSelectionScroll")
    assert view is not None
    assert search is not None
    assert scroll is not None
    search.setText("iron")
    search.setCursorPosition(2)
    scroll.verticalScrollBar().setValue(1)
    search.setFocus()

    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()

    assert factory.findChild(QFrame, "productionSelectionView") is view
    assert factory.findChild(QLineEdit, "productionSearchInput") is search
    assert factory.findChild(QScrollArea, "productionSelectionScroll") is scroll
    assert search.text() == "iron"
    assert search.cursorPosition() == 2
    assert factory._state.machine_production["test-drill-common-001"].progress_seconds > 0


def test_factory_runtime_refs_reconnect_after_structural_refresh_and_tick() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    old_kpi = factory._kpi_strip
    assert old_kpi is not None
    factory.refresh_view()
    _flush_deferred_deletes()

    assert not is_qt_object_valid(old_kpi)
    assert factory._kpi_strip is not None
    assert is_qt_object_valid(factory._kpi_strip)
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)


def test_factory_runtime_refs_survive_selection_views_and_hall_switches() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._on_slot_clicked(0)
    _flush_deferred_deletes()
    assert factory._kpi_strip is None
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._close_drawer()
    _flush_deferred_deletes()
    assert factory._kpi_strip is not None
    assert is_qt_object_valid(factory._kpi_strip)

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    _open_production_selection_for_slot(factory)
    _flush_deferred_deletes()
    assert factory._kpi_strip is None
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._close_drawer()
    factory._command_bus.dispatch(AddCash(1000))
    factory._purchase_hall()
    factory._selected_hall_id = "hall-2"
    factory._refresh_content()
    _flush_deferred_deletes()
    assert factory._kpi_strip is not None
    assert is_qt_object_valid(factory._kpi_strip)
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)


def test_factory_runtime_refs_reconnect_after_slot_and_line_expansion() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    factory._unlock_slot("hall-1.line-1")
    _flush_deferred_deletes()
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._unlock_line("hall-1.line-3")
    _flush_deferred_deletes()
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)


def test_machine_slot_card_details_and_paint_handle_machine_and_recipe_cards() -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    machine_card = create_card_instance(
        "machine-card",
        "machine.furnace.mk1",
        CardKind.MACHINE,
        Rarity.UNCOMMON,
        bonus_tenths=25,
    )
    machine_widget = MachineSlotWidget(
        HallSlot(0, machine_card.card_id),
        machine_card,
        definitions[machine_card.definition_id],
        MachineProductionState(machine_card.card_id, "iron", "recipe.furnace.iron", 1.0, "running"),
    )

    machine_details = machine_widget._card_details()
    machine_pixmap = machine_widget.grab()

    assert "Output" in machine_details
    assert "Power" in machine_details
    assert machine_widget.findChild(ResourceIconWidget, "resourceIcon") is not None
    icon = machine_widget.findChild(ResourceIconWidget, "resourceIcon")
    assert icon is not None
    assert icon.width() >= 50
    assert machine_widget.findChild(QPushButton, "productionChangeButton") is None
    assert machine_widget._primary_value().endswith("/min")
    assert "MW" in machine_widget._secondary_runtime_value()
    assert machine_widget.property("slotVisualState") == "installed"
    assert machine_widget.property("stageAccent") == "processor"
    assert machine_widget.property("rarity") == "uncommon"
    assert machine_widget._rarity_accent_color() != machine_widget._stage_accent_color()
    hover = machine_widget.findChild(QFrame, "factoryCardHoverInfo")
    assert hover is not None
    assert hover.isHidden()
    machine_widget.enterEvent(QEvent(QEvent.Type.Enter))
    assert not hover.isHidden()
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.width() > machine_widget.width()
    machine_widget.leaveEvent(QEvent(QEvent.Type.Leave))
    assert hover.isHidden()
    hover_text = " ".join(label.text() for label in hover.findChildren(QLabel))
    assert machine_widget.toolTip() == ""
    assert "MACHINE FAMILY" in hover_text
    assert "BASE OUTPUT" in hover_text
    assert "EFFECTIVE OUTPUT" in hover_text
    assert "POWER DEMAND" in hover_text
    assert "processor | MK" not in hover_text
    assert not machine_pixmap.isNull()

    recipe_card = create_card_instance(
        "recipe-card",
        "recipe.processor.iron",
        CardKind.RECIPE,
        Rarity.RARE,
        bonus_tenths=100,
    )
    recipe_widget = MachineSlotWidget(
        HallSlot(1, recipe_card.card_id),
        recipe_card,
        definitions[recipe_card.definition_id],
        None,
    )

    recipe_details = recipe_widget._card_details()
    recipe_pixmap = recipe_widget.grab()

    assert "Input: 12.6 Iron Ore -> 6.6 Iron" in recipe_details
    assert recipe_widget.findChild(ResourceIconWidget, "resourceIcon") is not None
    recipe_hover = recipe_widget.findChild(QFrame, "factoryCardHoverInfo")
    assert recipe_hover is not None
    recipe_hover_text = " ".join(label.text() for label in recipe_hover.findChildren(QLabel))
    assert "MACHINE FAMILY" in recipe_hover_text
    assert "Recipe" in recipe_hover_text
    assert not recipe_pixmap.isNull()


def test_unconfigured_machine_primary_label_fits_runtime_card_without_clipping() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    factory.refresh_view()
    QApplication.processEvents()

    widget = next(
        widget
        for widget in factory.findChildren(MachineSlotWidget)
        if widget._card is not None and widget._active_production() is None
    )
    assert widget._primary_label() == "NO RESOURCE SELECTED"
    label_rect = widget._primary_label_rect()
    metrics = QFontMetrics(QFont("Segoe UI", 8, QFont.Weight.Black))
    bounds = metrics.boundingRect(
        0,
        0,
        round(label_rect.width()),
        1000,
        int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
        widget._primary_label(),
    )
    assert bounds.width() <= label_rect.width()
    assert bounds.height() <= label_rect.height()
    assert label_rect.bottom() < widget._bottom_stats_rect().top()

    _select_factory_default_production(factory, widget._card.card_id)
    configured = factory._slot_widgets[0]
    assert configured._primary_label() != "NO RESOURCE SELECTED"
    assert configured._primary_value().endswith("/min")


def test_energy_card_uses_unified_factory_card_layout_and_tooltip() -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    energy_card = create_card_instance(
        "energy-card",
        "energy.solar_array.mk1",
        CardKind.ENERGY,
        Rarity.COMMON,
    )
    widget = MachineSlotWidget(
        HallSlot(0, energy_card.card_id),
        energy_card,
        definitions[energy_card.definition_id],
        None,
    )

    pixmap = widget.grab()

    assert widget.findChild(ResourceIconWidget, "resourceIcon") is not None
    icon = widget.findChild(ResourceIconWidget, "resourceIcon")
    assert icon is not None
    assert icon.width() >= 50
    assert widget.findChild(QPushButton, "productionChangeButton") is None
    assert widget._primary_value().endswith("MW")
    assert widget.property("stageAccent") == "energy"
    hover = widget.findChild(QFrame, "factoryCardHoverInfo")
    assert hover is not None
    hover_text = " ".join(label.text() for label in hover.findChildren(QLabel))
    assert widget.toolTip() == ""
    assert "POWER GENERATION" in hover_text
    assert "CURRENT STATUS" in hover_text
    assert "Online" in hover_text
    assert not pixmap.isNull()


def test_fuel_energy_card_shows_fuel_status_and_consumption_in_factory_card() -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=2501)
    card = create_card_instance("coal-energy-card", "energy.coal_power_plant.mk1", CardKind.ENERGY, Rarity.COMMON)
    state.cards[card.card_id] = card
    definition = definitions[card.definition_id]
    widget = MachineSlotWidget(
        HallSlot(0, card.card_id),
        card,
        definition,
        None,
        state=state,
    )

    assert widget._status_text() == "No Fuel"
    assert "Fuel Coal" in widget._card_details()
    hover = widget.findChild(QFrame, "factoryCardHoverInfo")
    assert hover is not None
    hover_text = " ".join(label.text() for label in hover.findChildren(QLabel))
    assert "NO FUEL" in hover_text.upper()
    assert "CONSUMPTION" in hover_text

    state.ensure_resource("coal", 10).amount = 1
    widget.set_data(HallSlot(0, card.card_id), card, definition, None, state)

    assert widget._status_text() == "Online"


def test_factory_hover_popup_stays_open_without_rebuild_during_runtime_updates(monkeypatch) -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    card = create_card_instance("hover-runtime-card", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)
    widget = MachineSlotWidget(
        HallSlot(0, card.card_id),
        card,
        definitions[card.definition_id],
        MachineProductionState(card.card_id, "iron", "recipe.furnace.iron", 1.0, "running"),
    )
    hover = widget.findChild(QFrame, "factoryCardHoverInfo")
    assert hover is not None
    widget.enterEvent(QEvent(QEvent.Type.Enter))
    assert not hover.isHidden()
    position = hover.pos()
    original_set_details = widget._hover_info.set_details
    rebuild_count = 0

    def counted_set_details(*args, **kwargs):
        nonlocal rebuild_count
        rebuild_count += 1
        return original_set_details(*args, **kwargs)

    monkeypatch.setattr(widget._hover_info, "set_details", counted_set_details)
    widget.set_data(
        HallSlot(0, card.card_id),
        card,
        definitions[card.definition_id],
        MachineProductionState(card.card_id, "iron", "recipe.furnace.iron", 2.0, "running"),
    )

    assert not hover.isHidden()
    assert hover.pos() == position
    assert rebuild_count == 0


def test_factory_hover_popup_updates_runtime_values_without_rebuilding(monkeypatch) -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    card = create_card_instance("hover-status-card", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)
    widget = MachineSlotWidget(
        HallSlot(0, card.card_id),
        card,
        definitions[card.definition_id],
        MachineProductionState(card.card_id, "iron", "recipe.furnace.iron", 1.0, "running"),
    )
    widget.enterEvent(QEvent(QEvent.Type.Enter))
    original_set_details = widget._hover_info.set_details

    def fail_rebuild(*args, **kwargs):
        raise AssertionError("Runtime hover updates must not rebuild the popup")

    monkeypatch.setattr(widget._hover_info, "set_details", fail_rebuild)
    widget.set_data(
        HallSlot(0, card.card_id),
        card,
        definitions[card.definition_id],
        MachineProductionState(card.card_id, "iron", "recipe.furnace.iron", 1.0, "storage_full"),
    )
    hover_text = " ".join(label.text() for label in widget._hover_info.findChildren(QLabel))
    assert "Storage Full" in hover_text
    monkeypatch.setattr(widget._hover_info, "set_details", original_set_details)


def test_factory_machine_progress_uses_real_cycle_and_pauses_when_stopped() -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    card = create_card_instance("progress-card", "machine.processor.mk1", CardKind.MACHINE, Rarity.COMMON)
    definition = definitions[card.definition_id]
    assert isinstance(definition, MachineDefinition)
    running = MachineSlotWidget(
        HallSlot(0, card.card_id),
        card,
        definition,
        MachineProductionState(card.card_id, "iron", "recipe.processor.iron", 1.5, "running"),
    )
    production = definition.production_option("recipe.processor.iron")

    assert running._cycle_progress_ratio() == pytest.approx(1.5 / production.cycle_seconds_for(definition))

    stopped = MachineProductionState(card.card_id, "iron", "recipe.processor.iron", 1.5, "missing_input")
    running.set_data(HallSlot(0, card.card_id), card, definition, stopped)
    paused_ratio = running._cycle_progress_ratio()
    running.set_data(HallSlot(0, card.card_id), card, definition, stopped)
    assert running._cycle_progress_ratio() == pytest.approx(paused_ratio)


def test_factory_machine_status_install_and_production_change_feedback_are_local() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    refreshes = 0
    original_refresh = factory._refresh_content

    def counted_refresh() -> None:
        nonlocal refreshes
        refreshes += 1
        original_refresh()

    factory._refresh_content = counted_refresh
    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    widget = factory._slot_widgets[0]
    assert widget._install_pulse_until > perf_counter()
    assert refreshes == 2

    before_widget = widget
    before_status = widget._last_status
    installed_card_id = factory._state.halls["hall-1"].slots[0].card_id
    assert installed_card_id is not None
    machine_state = factory._state.ensure_machine_production(installed_card_id, "iron_ore", "resource.iron_ore")
    machine_state.status = "storage_full"
    factory._refresh_runtime_widgets()
    assert factory._slot_widgets[0] is before_widget
    assert before_status != before_widget._last_status
    assert before_widget._status_pulse_until > perf_counter()

    _open_production_selection_for_slot(factory)
    _click_production_tile(factory, "Coal")
    changed = factory._slot_widgets[0]
    assert changed._production_pulse_until > perf_counter()
    assert changed._primary_label() == "COAL"


def test_factory_resource_summary_updates_amount_and_storage_bar_without_rebuild() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._command_bus.dispatch(SetResourceCapacity("iron_ore", 500))
    factory._state.resources["iron_ore"].amount = 157
    factory.refresh_view()

    item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    amount = item.findChild(QLabel, "hallResourceAmount")
    progress = item.findChild(QProgressBar, "hallResourceStorageProgress")
    assert amount is not None
    assert progress is not None

    factory._state.resources["iron_ore"].amount = 169
    factory._refresh_runtime_widgets()

    same_item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    assert same_item is item
    assert amount.text() == "169 / 500"
    assert progress.value() == 338
    assert item.property("previousAmount") == 157
    assert item.property("targetAmount") == 169
    assert item.property("amountTransitionMs") == 220


def test_factory_resource_summary_uses_clean_non_black_inner_surfaces() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory.refresh_view()

    item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    progress = item.findChild(QProgressBar, "hallResourceStorageProgress")

    assert progress is not None
    assert item.findChild(QLabel, "hallResourceName").text() == "IRON ORE"
    strip_selectors = (
        "QLabel",
        "QLabel#hallResourceName",
        "QLabel#hallResourceAmount",
        'QLabel#hallResourceNet[netState="positive"]',
        'QLabel#hallResourceNet[netState="negative"]',
        'QLabel#hallResourceNet[netState="neutral"]',
        "QPushButton#chainInfoButton",
        "QLabel#factoryHoverTitle",
        "QLabel#factoryHoverLabel",
        "QLabel#factoryHoverValue",
        "QLabel#title",
        "QLabel#subtitle",
        "QLabel#cashStatusTitle",
        "QLabel#cashStatusAmount",
        "QLabel#companyLevelLabel",
        "QLabel#companyXpLabel",
        "QLabel#supplyCardName",
        "QLabel#freightCardName",
        "QLabel#freightSelectionName",
        "QLabel#freightAssignmentTileName",
        "QLabel#inventoryCardName",
    )
    for selector in strip_selectors:
        block = _style_block(selector)
        assert "background: transparent" in block
        assert "background: #0" not in block
        assert "background: #10" not in block
        assert "background: #11" not in block
        assert "background: #12" not in block
        assert "background: #17" not in block
        assert "background: {Theme.PANEL" not in block
    assert "border: 1px solid rgba(143, 180, 255, 36);" in _style_block("QProgressBar#hallResourceStorageProgress")
    assert "border: 1px solid rgba(216, 240, 106, 42);" in _style_block("QProgressBar#companyXpProgress")
    assert "background: qlineargradient" in _style_block("QFrame#cashStatusPanel")
    assert "background: qlineargradient" in _style_block("QFrame#energyStatusPanel")
    assert "background: qlineargradient" in _style_block("QFrame#resourceStoragePanel")
    assert "background: rgba(255, 255, 255, 5);" in _style_block("QFrame#topbarEconomyCluster")
    assert "background: rgba(23, 33, 40, 238);" in _style_block("QFrame#factoryCardHoverInfo")


def test_visual_redesign_pass_defines_central_surfaces_navigation_and_button_states() -> None:
    assert Theme.SURFACE_0 != Theme.SURFACE_1 != Theme.SURFACE_2 != Theme.SURFACE_3
    assert Theme.SURFACE_INTERACTIVE != Theme.SURFACE_HOVER
    assert "background: qlineargradient" in _style_block("QFrame#globalHeader")
    selected_tab_block = _style_block("QTabBar::tab:selected")
    assert Theme.SAFETY_YELLOW in selected_tab_block
    assert "border-color: rgba(7, 8, 7, 230);" in selected_tab_block
    hover_tab_block = _style_block("QTabBar::tab:hover")
    assert "background: qlineargradient" in hover_tab_block
    assert "border-color: rgba(255, 210, 31, 112);" in hover_tab_block
    assert "QPushButton#expandResourceStorageButton" in APP_STYLESHEET
    assert "QPushButton#expandResourceStorageButton:hover" in APP_STYLESHEET
    assert "QPushButton#expandResourceStorageButton:pressed" in APP_STYLESHEET
    assert "QPushButton:disabled" in APP_STYLESHEET
    assert "background: qlineargradient" in _style_block("QFrame#lockedLinePanel")
    assert "background: qlineargradient" in _style_block("QFrame#lockedSlotPanel")
    assert "background: qlineargradient" in _style_block("QFrame#linePanel")
    assert "background: qlineargradient" in _style_block("QFrame#factoryHallCommandBoard")
    assert "background: qlineargradient" in _style_block("QFrame#factoryHallTitleShell")
    assert "background: qlineargradient" in _style_block("QFrame#factoryCommandDivider")
    assert "background: qlineargradient" in _style_block("QFrame#sidebar")
    assert "background: qlineargradient" in _style_block("QTreeWidget#hallTree")
    assert "background: qlineargradient" in _style_block("QPushButton#buildHallButton")
    assert "QLabel#lineNumberBadge" in APP_STYLESHEET
    assert "QLabel#lockedSlotHint" in APP_STYLESHEET


def test_card_title_wrapping_keeps_semantic_suffixes_together() -> None:
    from production_zero.ui.text_format import smart_card_title

    assert smart_card_title("Solar Array MK I") == "Solar Array\nMK I"
    assert smart_card_title("Freight Truck · Class I") == "Freight Truck\nClass I"
    assert smart_card_title("Autonomous Control System") == "Autonomous Control System"
    assert smart_card_title("High-Purity Silicon") == "High-Purity Silicon"


def test_factory_structural_refresh_and_hall_switch_close_hover_cleanly() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    widget = next(widget for widget in factory.findChildren(MachineSlotWidget) if widget._card is not None)
    hover = widget._hover_info
    assert hover is not None
    widget.enterEvent(QEvent(QEvent.Type.Enter))
    assert not hover.isHidden()

    factory._command_bus.dispatch(AddCash(2_000))
    factory._purchase_hall()
    factory._selected_hall_id = "hall-2"
    factory._refresh_content()
    _flush_deferred_deletes()

    assert not is_qt_object_valid(widget)
    assert not is_qt_object_valid(hover)


def test_factory_sixty_card_hall_runtime_update_keeps_widgets_stable() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(AddCash(100_000))
    hall = factory._state.halls["hall-1"]
    for line in hall.production_lines:
        if not line.unlocked:
            factory._command_bus.dispatch(UnlockProductionLine("hall-1", line.line_id))
        while len(line.slot_indexes) < 10:
            factory._command_bus.dispatch(UnlockProductionSlot("hall-1", line.line_id))
    factory.refresh_view()

    for slot_index in sorted(hall.unlocked_slot_indexes()):
        card = create_card_instance(f"mass-solar-{slot_index}", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)
        factory._command_bus.dispatch(AddCard(card))
        factory._command_bus.dispatch(InstallCardInHall("hall-1", slot_index, card.card_id))
    factory.refresh_view()
    widgets_before = dict(factory._slot_widgets)

    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()

    assert len(factory._slot_widgets) == 60
    assert factory._slot_widgets == widgets_before
    assert all(widget._primary_value().endswith("MW") for widget in factory._slot_widgets.values())


def test_factory_hall_summary_replaces_resource_drawer_and_keeps_compact_kpis() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    kpis = factory.findChild(QWidget, "hallKpiStrip")
    command_board = factory.findChild(QFrame, "factoryHallCommandBoard")
    title_shell = factory.findChild(QFrame, "factoryHallTitleShell")
    divider = factory.findChild(QFrame, "factoryCommandDivider")
    status_zone = factory.findChild(QFrame, "factoryStatusZone")
    header = factory.findChild(QFrame, "factoryHallHeader")
    command_label = factory.findChild(QLabel, "hallCommandLabel")
    summary = factory.findChild(QWidget, "hallResourceSummary")
    guide = factory.findChild(QPushButton, "productionGuideButton")
    slot_count = factory.findChild(QLabel, "hallSlotCount")
    assert command_board is not None
    assert title_shell is not None
    assert divider is not None
    assert divider.height() <= 2
    assert header is not None
    assert command_label is not None
    assert command_label.text() == "ACTIVE PRODUCTION HALL"
    assert status_zone is not None
    assert summary is not None
    assert summary.property("layoutMode") == "flow"
    assert guide is not None
    assert slot_count is not None
    assert "active lines" in slot_count.text()
    assert kpis is not None
    assert kpis.property("metrics") == "Energy|Revenue"
    assert kpis.maximumWidth() <= 310
    assert factory.findChild(QPushButton, "resourcesButton") is None
    assert factory.findChild(QFrame, "resourceDrawer") is None
    assert factory.findChildren(QPushButton, "sellResourceButton") == []
    assert factory.findChildren(QCheckBox, "autoSellEnabled") == []
    assert factory.findChildren(QSpinBox, "autoSellThreshold") == []


def test_factory_status_zone_resource_summary_wraps_without_horizontal_scrollbar() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 2, "test-furnace-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    _select_factory_default_production(factory, "test-furnace-common-001")
    factory.refresh_view()

    status_zone = factory.findChild(QFrame, "factoryStatusZone")
    summary = factory.findChild(QWidget, "hallResourceSummary")
    scroll = factory.findChild(QScrollArea, "factoryHallScroll")
    assert status_zone is not None
    assert summary is not None
    assert scroll is not None
    summary.resize(420, 140)
    QApplication.processEvents()

    items = factory.findChildren(QFrame, "hallResourceSummaryItem")
    assert len(items) >= 2
    assert summary.property("layoutMode") == "flow"
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_factory_navigation_shows_hall_slot_usage_and_remains_functional() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory.refresh_view()

    assert factory.findChild(QLabel, "factoryNavTitle").text() == "FACTORY"
    assert factory.findChild(QLabel, "factoryNavSubtitle").text() == "OPERATIONS / HALLS"
    tree = factory.findChild(QTreeWidget, "hallTree")
    assert tree is not None
    root = tree.topLevelItem(0)
    assert root is not None
    assert root.text(0) == "Factory"
    hall_item = root.child(0)
    assert hall_item is not None
    assert "1 / 6" in hall_item.text(0)

    factory._on_slot_clicked(0)

    root = tree.topLevelItem(0)
    hall_item = root.child(0)
    assert hall_item is not None
    assert "0 / 6" in hall_item.text(0)

    button = factory.findChild(QPushButton, "buildHallButton")
    assert button is not None
    assert "Build Hall" in button.text()


def test_factory_board_character_pass_uses_runtime_badges_and_upgrade_bays() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    line_badges = factory.findChildren(QLabel, "lineNumberBadge")
    assert line_badges
    assert line_badges[0].text() == "LINE 01"

    locked_slots = factory.findChildren(QFrame, "lockedSlotPanel")
    assert locked_slots
    locked_hints = [
        panel.findChild(QLabel, "lockedSlotHint")
        for panel in locked_slots
    ]
    assert all(hint is not None and hint.text() == "UPGRADE BAY" for hint in locked_hints)

    command_board = factory.findChild(QFrame, "factoryHallCommandBoard")
    title_shell = factory.findChild(QFrame, "factoryHallTitleShell")
    hall_tree = factory.findChild(QTreeWidget, "hallTree")
    assert command_board is not None
    assert title_shell is not None
    assert hall_tree is not None
    assert command_board.objectName() == "factoryHallCommandBoard"
    assert title_shell.parent() is not None


def test_factory_hall_summary_shows_only_resources_relevant_to_selected_hall() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-furnace-common-001"))
    _select_factory_default_production(factory, "test-furnace-common-001")
    factory.refresh_view()

    items = factory.findChildren(QFrame, "hallResourceSummaryItem")
    items_by_name = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in items
    }

    assert set(items_by_name) == {"IRON ORE", "IRON"}
    assert all(item.findChild(QProgressBar, "hallResourceStorageProgress") is not None for item in items)
    assert all(item.findChild(ResourceIconWidget, "resourceIcon") is not None for item in items)
    assert all(item.findChild(ResourceIconWidget, "resourceIcon").width() >= 40 for item in items)
    assert items_by_name["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "-180/min"
    assert items_by_name["IRON ORE"].property("netState") == "negative"
    assert items_by_name["IRON"].findChild(QLabel, "hallResourceNet").text() == "+90/min"
    assert items_by_name["IRON"].property("netState") == "positive"


def test_factory_hall_summary_net_change_states_and_values() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    neutral = create_card_instance("test-neutral-coal", "machine.neutral.coal", CardKind.MACHINE, Rarity.COMMON)
    factory._definitions["machine.neutral.coal"] = MachineDefinition(
        definition_id="machine.neutral.coal",
        name="Neutral Coal Tester",
        machine_type=MachineType.MINING,
        mk_level=1,
        base_output_per_tick=1,
        base_power_draw=0,
        cycle_seconds=1,
        input_resources={"coal": 1},
        output_resource="coal",
    )
    factory._command_bus.dispatch(AddCard(neutral))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-drill-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-furnace-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 2, neutral.card_id))
    _select_factory_default_production(factory, "test-drill-common-001")
    _select_factory_default_production(factory, "test-furnace-common-001")
    _select_factory_default_production(factory, neutral.card_id)
    factory.refresh_view()

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }

    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "+60/min"
    assert items["IRON ORE"].property("netState") == "positive"
    assert items["IRON"].findChild(QLabel, "hallResourceNet").text() == "+90/min"
    assert items["IRON"].property("netState") == "positive"
    assert items["COAL"].findChild(QLabel, "hallResourceNet").text() == "+0/min"
    assert items["COAL"].property("netState") == "neutral"


def test_factory_hall_summary_keeps_output_resource_visible_when_storage_is_full() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._command_bus.dispatch(SetResourceCapacity("iron_ore", 500))
    factory._command_bus.dispatch(AddResource("iron_ore", 500))

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-drill-common-001"].status == "storage_full"
    assert "IRON ORE" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceAmount").text() == "500 / 500"
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "+0/min"
    assert items["IRON ORE"].property("netState") == "neutral"


def test_factory_hall_summary_keeps_stopped_output_until_card_is_removed() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-drill-common-001"].status == "no_power"
    assert "IRON ORE" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "+0/min"

    factory._on_slot_clicked(1)

    names_after_remove = {
        item.findChild(QLabel, "hallResourceName").text()
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert "IRON ORE" not in names_after_remove


def test_factory_hall_summary_keeps_input_resource_visible_with_zero_consumption() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-furnace-common-001"))
    _select_factory_default_production(factory, "test-furnace-common-001")
    factory._command_bus.dispatch(SetResourceCapacity("iron_ore", 500))
    factory._state.resources["iron_ore"].amount = 0

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-furnace-common-001"].status == "missing_input"
    assert "IRON ORE" in items
    assert "IRON" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "+0/min"
    assert items["IRON ORE"].property("netState") == "neutral"
    assert items["IRON"].findChild(QLabel, "hallResourceNet").text() == "+0/min"


def test_factory_view_can_unlock_locked_production_line_with_cash() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    hall = factory._state.halls["hall-1"]
    locked_line = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-3"
    )

    locked_line.keyPressEvent(type("Event", (), {
        "key": lambda self: Qt.Key.Key_Return,
    })())

    assert factory._state.cash.amount == 500
    assert hall.production_lines[2].unlocked is True
    assert hall.slot_count == 9
    assert len(hall.slots) == 60
    assert hall.production_lines[2].slot_indexes == [6, 7, 8]
    assert not [
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-3"
    ]


def test_factory_line_headers_use_lightweight_rule_and_locked_badge() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    headers = factory.findChildren(QLabel, "lineHeader")
    assert headers
    assert headers[0].text() == "LINE 1"
    assert headers[0].property("locked") is False
    assert factory.findChildren(QFrame, "lineHeaderRule")
    locked_badges = factory.findChildren(QLabel, "lineLockedBadge")
    assert locked_badges
    assert locked_badges[0].text() == "LOCKED"
    locked_line = factory.findChild(QFrame, "lockedLinePanel")
    assert locked_line is not None
    assert locked_line.maximumHeight() < FACTORY_CARD_SIZE if "FACTORY_CARD_SIZE" in globals() else locked_line.maximumHeight() < 132
    assert locked_line.findChild(QLabel, "lockedLineName").text() == "LINE 3"
    assert "Expansion Bay" in locked_line.findChild(QLabel, "lockedLineDetail").text()
    assert locked_line.findChild(QPushButton, "unlockLineButton") is None


def test_factory_view_can_unlock_slots_and_locked_slot_does_not_open_selection() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    hall = factory._state.halls["hall-1"]

    locked_slot = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 4
    )
    assert locked_slot.findChild(QPushButton, "unlockSlotButton") is None
    assert locked_slot.findChild(QLabel, "lockedSlotIcon").text() == "LOCK"
    assert locked_slot.property("slotVisualState") == "locked"
    assert locked_slot.findChild(QLabel, "lockedSlotTitle").text() == "SLOT 4"
    assert locked_slot.findChild(QLabel, "lockedSlotPrice").text().startswith("$")
    assert locked_slot.findChild(QPushButton, "productionChangeButton") is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None

    locked_slot.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert hall.production_lines[0].slot_indexes == [0, 1, 2, 6]
    assert hall.slot_count == 7
    locked_slot_5 = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 5
    )
    locked_slot_5.keyPressEvent(type("Event", (), {
        "key": lambda self: Qt.Key.Key_Space,
    })())
    assert hall.production_lines[0].slot_indexes == [0, 1, 2, 6, 7]
    assert hall.slot_count == 8
    factory._on_slot_clicked(6)
    assert factory.findChild(QFrame, "factoryCardSelectionView") is not None


def test_factory_unlock_panels_enable_after_runtime_cash_refresh_without_hall_rebuild() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._state.cash.amount = 0
    factory.refresh_view()
    QApplication.processEvents()

    slot_panel = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 4
    )
    line_panel = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-3"
    )
    assert slot_panel.property("unlockEnabled") is False
    assert line_panel.property("unlockEnabled") is False

    factory._state.cash.add(100_000)
    factory._refresh_runtime_widgets()
    QApplication.processEvents()

    same_slot_panel = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 4
    )
    same_line_panel = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-3"
    )
    assert same_slot_panel is slot_panel
    assert same_line_panel is line_panel
    assert same_slot_panel.property("unlockEnabled") is True
    assert same_line_panel.property("unlockEnabled") is True

    same_slot_panel.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    assert factory._state.halls["hall-1"].slot_count == 7

    factory._command_bus.dispatch(PurchaseHall())
    factory._selected_hall_id = "hall-2"
    factory.refresh_view()
    factory._state.cash.amount = 0
    factory.refresh_view()
    hall2_slot_panel = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-2.line-1" and panel.property("slotNumber") == 4
    )
    assert hall2_slot_panel.property("unlockEnabled") is False
    factory._state.cash.add(100_000)
    factory._refresh_runtime_widgets()
    assert hall2_slot_panel.property("unlockEnabled") is True
    hall2_slot_panel.keyPressEvent(type("Event", (), {
        "key": lambda self: Qt.Key.Key_Space,
    })())
    assert factory._state.halls["hall-2"].slot_count == 7
    assert factory._state.halls["hall-1"].slot_count == 7


def test_factory_runtime_can_unlock_line_one_through_slot_ten_in_hall_one_and_two() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._state.cash.add(100_000)
    factory.refresh_view()

    for hall_id in ("hall-1", "hall-2"):
        if hall_id == "hall-2":
            factory._command_bus.dispatch(PurchaseHall())
            factory._state.cash.add(100_000)
        factory._selected_hall_id = hall_id
        factory.refresh_view()
        QApplication.processEvents()

        for slot_number in range(4, 11):
            panel = next(
                panel
                for panel in factory.findChildren(QFrame, "lockedSlotPanel")
                if panel.property("lineId") == f"{hall_id}.line-1" and panel.property("slotNumber") == slot_number
            )
            assert panel.property("unlockEnabled") is True
            panel.mousePressEvent(type("Event", (), {
                "button": lambda self: Qt.MouseButton.LeftButton,
            })())
            QApplication.processEvents()

        hall = factory._state.halls[hall_id]
        assert len(hall.production_lines[0].slot_indexes) == 10
        assert hall.slot_count == 13
        assert not [
            panel
            for panel in factory.findChildren(QFrame, "lockedSlotPanel")
            if panel.property("lineId") == f"{hall_id}.line-1" and panel.property("slotNumber") == 10
        ]

    factory._command_bus.dispatch(PurchaseHall())
    assert factory._state.halls["hall-1"].slot_count == 13
    assert factory._state.halls["hall-2"].slot_count == 13
    assert factory._state.halls["hall-3"].slot_count == 6


def test_factory_hall_view_uses_full_width_without_reserved_drawer_space() -> None:
    _app()
    window = MainWindow()
    window.resize(1800, 900)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory.refresh_view()
    QApplication.processEvents()

    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory.findChild(QFrame, "productionSelectionView") is None
    scroll = factory.findChild(QScrollArea, "factoryHallScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.width() >= factory._content.width() - 4


def test_factory_slot_rows_distribute_ten_square_slots_across_available_width() -> None:
    _app()
    window = MainWindow()
    window.resize(1800, 900)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryView)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory.refresh_view()
    QApplication.processEvents()

    row = factory.findChild(QWidget, "factorySlotRow")
    assert row is not None
    row.resize(1500, 180)
    QApplication.processEvents()
    widgets = _slot_row_widgets(row)
    assert len(widgets) == 10
    assert any(isinstance(widget, MachineSlotWidget) and widget._card is not None for widget in widgets)
    assert any(isinstance(widget, MachineSlotWidget) and widget._card is None for widget in widgets)
    assert any(widget.objectName() == "lockedSlotPanel" for widget in widgets)
    sizes = {widget.size().width() for widget in widgets}
    heights = {widget.size().height() for widget in widgets}
    assert len(sizes) == 1
    assert len(heights) == 1
    assert next(widget for widget in widgets if isinstance(widget, MachineSlotWidget) and widget._card is None).property("slotVisualState") == "empty"

    sizes = [(widget.width(), widget.height()) for widget in widgets]
    assert len(set(sizes)) == 1
    width, height = sizes[0]
    assert abs(width - height) <= 1
    assert width >= 96
    total_width = sum(widget.width() for widget in widgets) + 6 * (len(widgets) - 1)
    assert total_width <= row.width()


def test_factory_view_can_purchase_new_hall_from_sidebar() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    button = factory.findChild(QPushButton, "buildHallButton")
    assert button is not None
    assert button.isEnabled() is True

    button.click()

    assert set(factory._state.halls) == {"hall-1", "hall-2"}
    assert factory._selected_hall_id == "hall-2"
    assert factory._state.cash.amount == 250
    assert factory._state.halls["hall-2"].slot_count == 6
    assert factory._state.halls["hall-2"].production_lines[2].unlocked is False


def test_inventory_tab_shows_available_machine_stacks() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None

    tabs = inventory_view.findChild(QTabWidget, "inventorySubTabs")
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == ["Cards", "Crafting", "MK Upgrade"]
    assert tabs.currentIndex() == 0
    cards = _inventory_cards_by_name(inventory_view)

    assert len(cards) == 3
    extractor_card = cards["Extractor MK I"]
    assert extractor_card.findChild(QLabel, "inventoryCardMk").text() == "MK 1"
    assert extractor_card.findChild(QLabel, "inventoryCardRarity").text() == "Common"
    assert extractor_card.findChild(QLabel, "inventoryCardBonus").text() == "+0.0%"
    assert extractor_card.findChild(QLabel, "inventoryCardQuantity").text() == "Qty 3"
    assert extractor_card.findChild(QLabel, "inventoryCardStatus").text() == "Available"
    assert set(cards) == {
        "Extractor MK I",
        "Solar Array MK I",
        "Processor MK I",
    }
    assert inventory_view.findChild(QLabel, "inventoryTotalCardsLabel").text() == "6"
    assert inventory_view.findChild(QLabel, "inventoryStacksLabel").text() == "3"
    assert inventory_view.findChild(QLabel, "industrialScrapLabel").text() == "0"
    assert inventory_view.findChild(QLabel, "inventoryStorageLabel").text().startswith("303 / ")
    assert inventory_view.findChild(QLabel, "inventoryHeroTitle").text() == "INVENTORY"
    assert inventory_view.findChild(QLabel, "inventoryHeroSubtitle").text() == "CARD COLLECTION / MANAGEMENT"
    assert len(inventory_view.findChildren(QFrame, "inventoryKpi")) == 0
    assert inventory_view.findChild(QFrame, "inventoryScrapModule") is not None
    assert "rgba(127, 237, 24" not in _style_block("QFrame#inventoryScrapModule")
    assert "rgba(158, 190, 202" in _style_block("QFrame#inventoryScrapModule")
    assert "#b8d0d8" in _style_block("QLabel#industrialScrapLabel")
    assert inventory_view.findChild(QFrame, "inventoryCardsBrowserShell") is not None
    assert inventory_view.findChild(QLabel, "inventoryActionHint") is None
    assert inventory_view.findChild(QScrollArea, "cardInventoryScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert inventory_view.findChild(QTableWidget, "cardInventoryTable") is None


def test_topbar_resource_storage_expansion_updates_runtime_capacity() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    global_header = window.findChild(QFrame, "globalHeader")
    assert tabs is not None
    assert inventory_view is not None
    assert global_header is not None
    tabs.setCurrentWidget(inventory_view)
    QApplication.processEvents()
    resource_definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    starting_cash = inventory_view._state.cash.amount
    starting_capacity = inventory_view._state.resources["iron_ore"].capacity
    cost = inventory_storage_upgrade_cost(0)

    storage_label = inventory_view.findChild(QLabel, "inventoryStorageLabel")
    storage_info = inventory_view.findChild(QLabel, "inventoryStorageInfo")
    button = window.findChild(QPushButton, "expandResourceStorageButton")
    topbar_storage = window.findChild(QLabel, "resourceStorageAmount")
    cash_label = window.findChild(QLabel, "cashStatusAmount")
    assert storage_label is not None
    assert storage_info is not None
    assert button is not None
    assert topbar_storage is not None
    assert cash_label is not None
    assert inventory_view.findChild(QPushButton, "expandInventoryStorageButton") is None
    assert storage_info.text() == "Resource storage upgrades are in the topbar."
    assert button.text() == f"Expand ${cost:,.0f}"
    assert button.isEnabled() is True
    assert storage_label.text().endswith(f"/ {sum(stock.capacity for stock in inventory_view._state.resources.values()):.0f}")
    assert topbar_storage.text().endswith(f"/ {sum(stock.capacity for stock in inventory_view._state.resources.values()):.0f}")

    button.click()
    QApplication.processEvents()

    assert inventory_view._state.inventory_storage_level == 1
    assert inventory_view._state.cash.amount == starting_cash - cost
    assert inventory_view._state.resources["iron_ore"].amount == 145
    assert inventory_view._state.resources["iron_ore"].capacity == inventory_storage_capacity(
        resource_definitions["iron_ore"].default_capacity,
        1,
    )
    assert inventory_view._state.resources["iron_ore"].capacity > starting_capacity
    assert button.text() == f"Expand ${inventory_storage_upgrade_cost(1):,.0f}"
    assert cash_label.text() == f"${inventory_view._state.cash.amount:,.0f}"
    assert topbar_storage.text().endswith(f"/ {sum(stock.capacity for stock in inventory_view._state.resources.values()):.0f}")
    assert inventory_view._state.freight.facilities["garage-1"].slot_count == 3
    assert inventory_view._state.halls["hall-1"].slot_count == 6


def test_inventory_cards_use_visual_card_grid_components() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert inventory_view is not None
    assert tabs is not None
    inventory_view._command_bus.dispatch(
        AddCard(create_card_instance("ui-recipe-gap-test", "recipe.processor.iron", CardKind.RECIPE, Rarity.COMMON))
    )
    inventory_view.resize(1300, 800)
    inventory_view.refresh()
    window.show()
    tabs.setCurrentWidget(inventory_view)
    QApplication.processEvents()

    cards = _inventory_cards_by_name(inventory_view)
    extractor_card = cards["Extractor MK I"]
    recipe_card = cards["Iron Recipe"]
    energy_card = cards["Solar Array MK I"]
    assert extractor_card.findChild(ResourceIconWidget, "inventoryCardIcon") is not None
    assert type(extractor_card).__name__ == "InventoryCardFrame"
    assert extractor_card.objectName() == "inventoryCard"
    assert "background: transparent" in _style_block("QFrame#inventoryCard")
    assert "border: 0" in _style_block("QFrame#inventoryCard")
    assert "rgba(21, 29, 33" not in _style_block("QFrame#inventoryCard")
    filter_block = _style_block("QFrame#inventoryFilters")
    assert "qlineargradient" in filter_block
    assert "rgba(18, 23, 23, 246)" in filter_block
    assert "border: 1px solid rgba(142, 154, 150, 72)" in filter_block
    assert "QScrollArea#inventoryFilterScroll > QWidget > QWidget" not in APP_STYLESHEET
    inventory_card_type_block = _style_block('QFrame#inventoryCard[cardType="energy"], QFrame#inventoryCard[cardType="extractor"], QFrame#inventoryCard[cardType="processor"], QFrame#inventoryCard[cardType="fabricator"], QFrame#inventoryCard[cardType="assembler"], QFrame#inventoryCard[cardType="freight"]')
    assert "border-left" not in inventory_card_type_block
    assert "border: 0" in inventory_card_type_block
    search_block = _style_block("QLineEdit#inventorySearch")
    assert "rgba(4, 7, 7" not in search_block
    assert "rgba(255, 255, 255, 8)" in search_block
    title = extractor_card.findChild(QLabel, "inventoryCardName")
    mk = extractor_card.findChild(QLabel, "inventoryCardMk")
    rarity = extractor_card.findChild(QLabel, "inventoryCardRarity")
    assert title is not None
    assert mk is not None
    assert rarity is not None
    assert title.isHidden()
    assert mk.isHidden()
    assert rarity.isHidden()
    assert extractor_card.findChild(QFrame, "inventoryRarityLine") is None
    assert extractor_card.findChild(QLabel, "inventoryCardFunction").text() == "EXTRACTOR"
    assert recipe_card.findChild(QLabel, "inventoryCardFunction").text() == "PROCESSOR RECIPE"
    assert extractor_card.property("cardTitle") == "EXTRACTOR"
    assert extractor_card.property("cardMeta") == "MK1 / COMMON"
    assert energy_card.property("cardTitle") == "SOLAR ARRAY"
    assert energy_card.property("cardMeta") == "MK1 / COMMON"
    assert recipe_card.property("cardTitle") == "IRON RECIPE"
    assert "V" in _BLOCK_GLYPHS
    assert extractor_card.property("cardType") == "extractor"
    assert recipe_card.property("cardType") == "processor"
    assert energy_card.findChild(QLabel, "inventoryCardFunction").text() == "ENERGY"
    assert energy_card.property("cardType") == "energy"
    assert extractor_card.width() == energy_card.width()
    assert extractor_card.height() == cards["Processor MK I"].height()
    assert extractor_card.property("quantity") == 3
    assert extractor_card.property("statusText") == "Available"
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventoryMkFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventoryRarityFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventoryStatusFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventorySort").isHidden()
    chips = inventory_view.findChildren(QPushButton, "inventoryFilterChip")
    assert chips
    assert any(chip.property("filterGroup") == "inventoryTypeFilter" and chip.text() == "SOLAR" for chip in chips)
    assert inventory_view.findChild(QFrame, "cardDetailsDrawer") is None
    assert inventory_view.findChild(QFrame, "inventoryActionPanel").isHidden()


def test_inventory_card_grid_wraps_responsively_without_horizontal_scrollbar() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None
    for _ in range(5):
        index = _
        inventory_view._command_bus.dispatch(
            AddCard(create_card_instance(f"ui-grid-extra-{index}", "machine.extractor.mk1", CardKind.MACHINE, Rarity.UNCOMMON, 10 + index))
        )
    inventory_view.resize(1400, 800)
    inventory_view.refresh()

    positions = []
    for card in inventory_view.findChildren(QFrame, "inventoryCard"):
        layout = card.parentWidget().layout()
        index = layout.indexOf(card)
        row, column, _row_span, _column_span = layout.getItemPosition(index)
        positions.append((row, column))
    assert max(column for _row, column in positions) >= 2
    assert inventory_view.findChild(QScrollArea, "cardInventoryScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_inventory_cards_tab_uses_game_filter_chips_for_visible_filters() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None
    window.show()
    inventory_view.refresh()
    QApplication.processEvents()

    type_chip = next(
        chip
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "inventoryTypeFilter" and chip.property("filterValue") == "Solar"
    )
    type_chip.click()
    QApplication.processEvents()

    cards = _inventory_cards_by_name(inventory_view)
    assert list(cards) == ["Solar Array MK I"]
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").currentText() == "Solar"
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").isHidden()
    assert any(
        chip.property("filterGroup") == "inventoryTypeFilter"
        and chip.property("filterValue") == "Solar"
        and chip.property("active") is True
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
    )


def test_inventory_cards_redesign_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    assert tabs is not None
    assert inventory_view is not None
    window.resize(1700, 900)
    window.show()
    tabs.setCurrentWidget(inventory_view)
    inventory_view.refresh()
    QApplication.processEvents()

    path = Path("artifacts") / "inventory_cards_redesign_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = inventory_view.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()


def test_inventory_tab_filters_available_and_in_use_cards() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    inventory_view = window.findChild(InventoryView)
    assert factory is not None
    assert inventory_view is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor MK I")
    inventory_view.refresh()

    status_filter = inventory_view.findChild(QComboBox, "inventoryStatusFilter")
    assert status_filter is not None

    status_filter.setCurrentText("In Use")

    in_use_cards = _inventory_cards_by_name(inventory_view)
    assert list(in_use_cards) == ["Extractor MK I"]
    assert in_use_cards["Extractor MK I"].findChild(QLabel, "inventoryCardQuantity").text() == "Qty 1"
    assert in_use_cards["Extractor MK I"].findChild(QLabel, "inventoryCardStatus").text() == "In Use"

    status_filter.setCurrentText("Available")

    available_cards = _inventory_cards_by_name(inventory_view)
    extractor_card = available_cards["Extractor MK I"]
    assert extractor_card.findChild(QLabel, "inventoryCardStatus").text() == "Available"
    assert extractor_card.findChild(QLabel, "inventoryCardQuantity").text() == "Qty 2"


def test_inventory_tab_recycles_available_stack_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None

    _inventory_cards_by_name(inventory_view)["Extractor MK I"].mousePressEvent(None)
    action_panel = inventory_view.findChild(QFrame, "inventoryActionPanel")
    assert action_panel is not None
    quantity = action_panel.findChild(QSpinBox, "recycleQuantity")
    recycle_button = action_panel.findChild(QPushButton, "recycleCardButton")
    assert isinstance(quantity, QSpinBox)
    assert recycle_button is not None

    quantity.setValue(2)
    recycle_button.click()

    assert inventory_view._state.scrap.amount == 2
    extractor_stack = next(
        stack
        for stack in inventory_view._state.inventory_card_stacks()
        if stack.first_card.definition_id == "machine.extractor.mk1"
    )
    assert extractor_stack.quantity == 1
    assert inventory_view.findChild(QLabel, "industrialScrapLabel").text() == "2"


def test_inventory_cards_search_and_hover_show_effective_values() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None

    search = inventory_view.findChild(QLineEdit, "inventorySearch")
    assert search is not None
    assert inventory_view.findChild(QFrame, "cardDetailsDrawer") is None

    search.setText("solar")
    cards = _inventory_cards_by_name(inventory_view)
    assert list(cards) == ["Solar Array MK I"]

    inventory_view._show_card_hover(inventory_view._visible_card_rows[0], cards["Solar Array MK I"])
    hover = inventory_view.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    detail_values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert any("MW" in value for value in detail_values)
    assert "1" in detail_values
    assert hover.findChild(ResourceIconWidget) is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Solar Array MK I"


def test_inventory_tab_can_craft_selected_material_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert inventory_view is not None
    assert dev is not None

    dev._card_select.setCurrentText("Extractor")
    dev._card_rarity.setCurrentText("Uncommon")
    dev._card_bonus_tenths.setValue(30)
    dev._create_craft_set()
    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)

    target_grid = inventory_view.findChild(QWidget, "craftTargetGrid")
    material_grid = inventory_view.findChild(QWidget, "craftMaterialGrid")
    preview = inventory_view.findChild(QLabel, "craftOutputPreview")
    confirm = inventory_view.findChild(QCheckBox, "craftConfirm")
    button = inventory_view.findChild(QPushButton, "craftCardButton")
    assert target_grid is not None
    assert material_grid is not None
    assert preview is not None
    assert confirm is not None
    assert button is not None
    assert inventory_view.findChild(QComboBox, "craftTargetSelect") is None
    assert inventory_view.findChild(QTableWidget, "craftMaterialTable") is None
    assert "SELECT TARGET CARD" in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 0/5"

    target_cards = inventory_view.findChildren(QFrame, "craftTargetCard")
    assert target_cards
    assert all(not str(card.property("definitionId")).startswith("recipe.") for card in target_cards)
    assert any(card.findChild(ResourceIconWidget) is not None for card in target_cards)
    target = next(card for card in target_cards if card.property("definitionId") == "machine.processor.mk1")
    target.mousePressEvent(None)
    assert "SELECT MATERIALS" in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]

    for _ in range(5):
        material = next(
            card
            for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
            if card.property("definitionId") == "machine.extractor.mk1"
        )
        material.mousePressEvent(None)

    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 5/5"
    material = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
        if card.property("definitionId") == "machine.extractor.mk1"
    )
    assert material.property("selectedCount") == 5
    material.hovered.emit()
    hover = inventory_view.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Extractor MK I"
    assert "Target: Processor MK I" in preview.text()
    assert "Result Rarity: Rare" in preview.text()
    assert "Result Bonus: +8.0%" in preview.text()
    material_slots = inventory_view.findChildren(QFrame, "craftMaterialSlot")
    assert len(material_slots) == 5
    assert all(slot.property("filled") is True for slot in material_slots)
    material_slots[0].mousePressEvent(None)
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 4/5"
    material = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
        if card.property("definitionId") == "machine.extractor.mk1"
    )
    assert material.property("selectedCount") == 4
    material.mousePressEvent(None)
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 5/5"
    target_preview = inventory_view.findChild(QFrame, "craftTargetPreview")
    assert target_preview is not None
    target_preview.mousePressEvent(None)
    assert "SELECT TARGET CARD" in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]
    target = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
        if card.property("definitionId") == "machine.processor.mk1"
    )
    target.mousePressEvent(None)
    assert "SELECT MATERIALS" in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]
    assert button.isEnabled() is False
    confirm.setChecked(True)
    button.click()

    crafted = [
        card
        for card in inventory_view._state.cards.values()
        if card.definition_id == "machine.processor.mk1" and card.rarity is Rarity.RARE
    ]
    assert len(crafted) == 1
    assert crafted[0].output_bonus_tenths == 80


def test_inventory_crafting_tab_uses_game_shell_chips_and_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None
    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
    QApplication.processEvents()

    assert inventory_view.findChild(QFrame, "craftSelectionPanel") is not None
    assert inventory_view.findChild(QFrame, "craftPreviewPanel") is not None
    assert inventory_view.findChildren(QWidget, "craftFilterDeck")
    assert inventory_view.findChild(QComboBox, "craftTargetTypeFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "craftTargetMkFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "craftTargetRarityFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "craftTargetSort").isHidden()
    assert "background: transparent" in _style_block("QFrame#craftTargetCard, QFrame#craftMaterialCard")
    assert "border: 0" in _style_block("QFrame#craftTargetCard, QFrame#craftMaterialCard")
    craft_filter_block = _style_block("QWidget#craftFilterDeck")
    assert "qlineargradient" in craft_filter_block
    assert "rgba(18, 23, 23, 246)" in craft_filter_block
    assert "border: 1px solid rgba(142, 154, 150, 72)" in craft_filter_block

    target_chips = [
        chip
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "craftTargetTypeFilter"
    ]
    assert target_chips
    energy_chip = next(chip for chip in target_chips if chip.property("filterValue") == "Energy")
    energy_chip.click()
    QApplication.processEvents()
    assert inventory_view.findChild(QComboBox, "craftTargetTypeFilter").currentText() == "Energy"
    energy_target_ids = {
        card.property("definitionId")
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
    }
    assert "energy.solar_array.mk1" in energy_target_ids
    assert all(str(definition_id).startswith("energy.") for definition_id in energy_target_ids)

    energy_card = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
        if card.property("definitionId") == "energy.solar_array.mk1"
    )
    assert type(energy_card).__name__ == "InventoryCardFrame"
    assert energy_card.findChild(ResourceIconWidget, "inventoryCardIcon") is not None
    assert energy_card.property("cardTitle") == "SOLAR ARRAY"
    assert energy_card.property("cardMeta") == "MK1 / COMMON"


def test_inventory_crafting_redesign_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert tabs is not None
    assert inventory_view is not None
    assert dev is not None

    dev._card_select.setCurrentText("Extractor")
    dev._card_rarity.setCurrentText("Uncommon")
    dev._card_bonus_tenths.setValue(30)
    dev._create_craft_set()
    window.resize(1700, 900)
    window.show()
    tabs.setCurrentWidget(inventory_view)
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
    inventory_view.refresh()
    QApplication.processEvents()
    target = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
        if card.property("definitionId") == "machine.processor.mk1"
    )
    target.mousePressEvent(None)
    for _ in range(2):
        material = next(
            card
            for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
            if card.property("definitionId") == "machine.extractor.mk1"
        )
        material.mousePressEvent(None)
    QApplication.processEvents()

    path = Path("artifacts") / "inventory_crafting_redesign_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = inventory_view.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()


def test_inventory_tab_can_upgrade_available_card_mk() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert inventory_view is not None
    assert dev is not None

    dev._create_upgrade_test()
    inventory_view._state.cards["ui-max-mk"] = create_card_instance(
        "ui-max-mk",
        "machine.extractor.mk3",
        CardKind.MACHINE,
        Rarity.UNCOMMON,
        bonus_tenths=20,
    )
    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)

    grid = inventory_view.findChild(QWidget, "mkUpgradeCardGrid")
    scroll = inventory_view.findChild(QScrollArea, "mkUpgradeCardScroll")
    preview = inventory_view.findChild(QLabel, "mkUpgradePreview")
    current = inventory_view.findChild(QFrame, "mkUpgradeCurrentCard")
    target = inventory_view.findChild(QFrame, "mkUpgradeTargetCard")
    confirm = inventory_view.findChild(QCheckBox, "mkUpgradeConfirm")
    button = inventory_view.findChild(QPushButton, "mkUpgradeButton")
    assert inventory_view.findChild(QComboBox, "mkUpgradeCardSelect") is None
    assert grid is not None
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert preview is not None
    assert confirm is not None
    assert button is not None
    assert current is not None
    assert target is not None

    cards = inventory_view.findChildren(QFrame, "mkUpgradeSelectionCard")
    assert cards
    selected_card = next(
        card
        for card in cards
        if card.property("definitionId") == "machine.extractor.mk1"
        and card.findChild(QLabel, "inventoryCardRarity").text() == "Rare"
    )
    selected_card.hovered.emit()
    hover = inventory_view.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Extractor MK I"
    selected_card.mousePressEvent(None)

    assert preview.text() == "UPGRADE COST\n40 SCRAP\nAVAILABLE 100\nENOUGH"
    current_preview = current.findChild(QFrame, "mkUpgradePreviewCard")
    target_preview = target.findChild(QFrame, "mkUpgradePreviewCard")
    assert current_preview is not None
    assert target_preview is not None
    assert current_preview.findChild(QLabel, "inventoryCardName").text() == "Extractor MK I"
    assert target_preview.findChild(QLabel, "inventoryCardName").text() == "Extractor MK II"
    assert current_preview.property("cardTitle") == "EXTRACTOR"
    assert target_preview.property("cardTitle") == "EXTRACTOR"
    assert current_preview.property("cardMeta") == "MK1 / RARE"
    assert target_preview.property("cardMeta") == "MK2 / RARE"
    compare_values = [label.text() for label in inventory_view.findChildren(QLabel, "mkUpgradeCompareValue")]
    assert "1" in compare_values
    assert "2" in compare_values
    assert "13.128" in compare_values
    assert "32.82" in compare_values
    assert "6.282 MW" in compare_values
    assert "14.658 MW" in compare_values
    assert button.isEnabled() is False
    confirm.setChecked(True)
    button.click()

    upgraded = [
        card
        for card in inventory_view._state.cards.values()
        if card.definition_id == "machine.extractor.mk2" and card.rarity is Rarity.RARE
    ]
    assert len(upgraded) == 1
    assert inventory_view._state.scrap.amount == 60

    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)
    max_card = next(card for card in inventory_view.findChildren(QFrame, "mkUpgradeSelectionCard") if card.property("definitionId") == "machine.extractor.mk3")
    max_card.mousePressEvent(None)
    assert preview.text() == "MAX MK"
    assert button.isEnabled() is False
    assert upgraded[0].output_bonus_tenths == 94
    assert inventory_view._state.scrap.amount == 60


def test_inventory_mk_upgrade_tab_uses_game_shell_chips_cards_and_arrow() -> None:
    _app()
    window = MainWindow()
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert inventory_view is not None
    assert dev is not None
    dev._create_upgrade_test()
    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)
    QApplication.processEvents()

    assert inventory_view.findChild(QWidget, "mkUpgradeFilterDeck") is not None
    assert inventory_view.findChild(QComboBox, "mkUpgradeTypeFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "mkUpgradeMkFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "mkUpgradeRarityFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "mkUpgradeSort").isHidden()
    assert "background: transparent" in _style_block("QFrame#mkUpgradeSelectionCard, QFrame#mkUpgradePreviewCard")
    assert "border: 0" in _style_block("QFrame#mkUpgradeSelectionCard, QFrame#mkUpgradePreviewCard")
    mk_filter_block = _style_block("QWidget#mkUpgradeFilterDeck")
    assert "qlineargradient" in mk_filter_block
    assert "rgba(18, 23, 23, 246)" in mk_filter_block
    assert "border: 1px solid rgba(142, 154, 150, 72)" in mk_filter_block
    connector = inventory_view.findChild(QFrame, "mkUpgradeConnector")
    assert connector is not None
    assert type(connector).__name__ == "MkUpgradeConnectorSign"
    assert inventory_view.findChild(QLabel, "mkUpgradeConnectorArrow") is None
    assert inventory_view.findChild(QFrame, "mkUpgradeCostPanel") is not None
    assert inventory_view.findChild(QFrame, "mkUpgradeConfirmZone") is not None

    mk_chip = next(
        chip
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "mkUpgradeMkFilter" and chip.property("filterValue") == "1"
    )
    assert mk_chip.text() == "MK1"
    mk_chip.click()
    QApplication.processEvents()
    assert inventory_view.findChild(QComboBox, "mkUpgradeMkFilter").currentText() == "1"
    assert all(
        card.findChild(QLabel, "inventoryCardMk").text() == "MK 1"
        for card in inventory_view.findChildren(QFrame, "mkUpgradeSelectionCard")
    )

    selected_card = next(
        card
        for card in inventory_view.findChildren(QFrame, "mkUpgradeSelectionCard")
        if card.property("definitionId") == "machine.extractor.mk1"
        and card.findChild(QLabel, "inventoryCardRarity").text() == "Rare"
    )
    assert type(selected_card).__name__ == "InventoryCardFrame"
    selected_card.mousePressEvent(None)
    QApplication.processEvents()

    current = inventory_view.findChild(QFrame, "mkUpgradeCurrentCard")
    target = inventory_view.findChild(QFrame, "mkUpgradeTargetCard")
    assert current is not None and target is not None
    assert current.size() == target.size()
    current_preview = current.findChild(QFrame, "mkUpgradePreviewCard")
    target_preview = target.findChild(QFrame, "mkUpgradePreviewCard")
    assert type(current_preview).__name__ == "InventoryCardFrame"
    assert type(target_preview).__name__ == "InventoryCardFrame"
    assert current_preview.findChild(QLabel, "inventoryCardName").text() == "Extractor MK I"
    assert target_preview.findChild(QLabel, "inventoryCardName").text() == "Extractor MK II"
    assert current_preview.property("cardTitle") == "EXTRACTOR"
    assert target_preview.property("cardTitle") == "EXTRACTOR"
    preview = inventory_view.findChild(QLabel, "mkUpgradePreview")
    assert "UPGRADE COST" in preview.text()
    assert "40 SCRAP" in preview.text()
    assert "AVAILABLE 100" in preview.text()
    compare_values = [label.text() for label in inventory_view.findChildren(QLabel, "mkUpgradeCompareValue")]
    assert "13.128" in compare_values
    assert "32.82" in compare_values


def test_inventory_mk_upgrade_redesign_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert tabs is not None
    assert inventory_view is not None
    assert dev is not None
    dev._create_upgrade_test()
    window.resize(1600, 980)
    window.show()
    tabs.setCurrentWidget(inventory_view)
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)
    inventory_view.refresh()
    QApplication.processEvents()
    selected_card = next(
        card
        for card in inventory_view.findChildren(QFrame, "mkUpgradeSelectionCard")
        if card.property("definitionId") == "machine.extractor.mk1"
        and card.findChild(QLabel, "inventoryCardRarity").text() == "Rare"
    )
    selected_card.mousePressEvent(None)
    QApplication.processEvents()

    path = Path("artifacts") / "inventory_mk_upgrade_redesign_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = inventory_view.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()


def test_inventory_mk_upgrade_empty_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    dev = window.findChild(DevToolsView)
    assert tabs is not None
    assert inventory_view is not None
    assert dev is not None
    dev._create_upgrade_test()
    window.resize(1600, 980)
    window.show()
    tabs.setCurrentWidget(inventory_view)
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)
    inventory_view._mk_selected_card_id = None
    inventory_view.refresh()
    QApplication.processEvents()

    assert inventory_view.findChild(QFrame, "mkUpgradeConnector") is not None
    assert inventory_view.findChild(QLabel, "mkUpgradeConnectorArrow") is None
    assert inventory_view.findChild(QFrame, "mkUpgradeCostPanel") is not None

    path = Path("artifacts") / "inventory_mk_upgrade_empty_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = inventory_view.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()


def test_charts_tab_opens_resource_overview_with_resource_tile_grid() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    stack = charts.findChild(QStackedWidget, "chartsStack")
    search = charts.findChild(QLineEdit, "chartResourceSearch")
    sort = charts.findChild(QComboBox, "chartSortSelect")
    stage = charts.findChild(QComboBox, "chartStageFilter")
    category = charts.findChild(QComboBox, "chartCategoryFilter")
    activity = charts.findChild(QComboBox, "chartActivityFilter")
    range_select = charts.findChild(QComboBox, "chartRangeSelect")
    cash_card = charts.findChild(QFrame, "chartCashCard")
    scroll = charts.findChild(QScrollArea, "chartResourceScroll")
    resource_cards = _chart_resource_cards_by_name(charts)

    assert stack is not None
    assert stack.currentIndex() == 0
    assert search is not None
    assert search.placeholderText() == "Search resources..."
    assert sort is not None
    assert [sort.itemText(index) for index in range(sort.count())] == ["Name", "Amount", "Fill %", "Net Change"]
    assert stage is not None
    assert category is not None
    assert activity is not None
    assert [activity.itemText(index) for index in range(activity.count())] == ["All", "Active", "In Stock", "Producing", "Consuming"]
    assert range_select is not None
    assert [range_select.itemText(index) for index in range(range_select.count())] == ["10M", "1H", "6H", "24H", "ALL"]
    assert cash_card is None
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    scroll.viewport().resize(1400, 480)
    charts._force_overview_reflow()
    assert charts._resource_grid_columns() == 4
    assert charts._resource_list.isHidden() is False
    first_tiles = list(charts._resource_tiles.values())[:5]
    assert [tile.property("gridColumn") for tile in first_tiles[:4]] == [0, 1, 2, 3]
    assert first_tiles[4].property("gridRow") == 1
    assert first_tiles[4].property("gridColumn") == 0
    assert all(tile.width() == first_tiles[0].width() for tile in first_tiles[:4])
    reflow_count = charts._overview_reflow_count
    charts._refresh_overview()
    assert charts._overview_reflow_count == reflow_count
    scroll.viewport().resize(1050, 480)
    charts._force_overview_reflow()
    assert charts._resource_grid_columns() == 3
    scroll.viewport().resize(700, 480)
    charts._force_overview_reflow()
    assert charts._resource_grid_columns() == 2
    scroll.viewport().resize(210, 480)
    charts._force_overview_reflow()
    assert charts._resource_grid_columns() == 1
    scroll.viewport().resize(1400, 480)
    charts._force_overview_reflow()
    resource_cards = _chart_resource_cards_by_name(charts)
    assert {
        "Iron Ore",
        "Coal",
        "Copper Ore",
        "Iron",
        "Copper",
        "Steel",
        "Steel Components",
        "Timber",
        "Packaged Food",
        "AI Server",
    }.issubset(resource_cards)
    assert len(resource_cards) > 300
    iron_ore = resource_cards["Iron Ore"]
    assert iron_ore.findChild(ResourceIconWidget, "resourceIcon") is not None
    assert iron_ore.width() >= 190
    assert iron_ore.minimumHeight() >= 166
    assert iron_ore.findChild(QLabel, "chartResourceAmount").text() == "145 / 500"
    assert iron_ore.findChild(QWidget, "chartResourceSparkline") is not None
    assert iron_ore.findChild(QProgressBar, "chartResourceStorageProgress").value() == 290


def test_charts_startup_does_not_create_top_level_tile_or_visibility_loop() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1180, 760)
    window.show()
    for _ in range(8):
        QApplication.processEvents()

    charts = window.findChild(ChartsView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert charts is not None
    assert tabs is not None
    assert window.isVisible() is True
    assert window.isHidden() is False

    forbidden_top_levels = {"chartResourceCard", "chartResourceGrid", "chartEmptyState", "lineChart"}
    assert all(widget.objectName() not in forbidden_top_levels for widget in app.topLevelWidgets())
    overview_reflows = charts._overview_reflow_count
    detail_reflows = charts._detail_reflow_count

    for _ in range(8):
        QApplication.processEvents()

    assert window.isVisible() is True
    assert all(widget.objectName() not in forbidden_top_levels for widget in app.topLevelWidgets())
    assert charts._overview_reflow_count == overview_reflows
    assert charts._detail_reflow_count == detail_reflows

    tabs.setCurrentIndex(tabs.indexOf(charts))
    for _ in range(4):
        QApplication.processEvents()
    assert tabs.currentWidget() is charts
    assert window.isVisible() is True
    assert all(widget.objectName() not in forbidden_top_levels for widget in app.topLevelWidgets())

    tabs.setCurrentIndex(0)
    for _ in range(4):
        QApplication.processEvents()
    assert tabs.currentIndex() == 0
    assert window.isVisible() is True
    assert all(widget.objectName() not in forbidden_top_levels for widget in app.topLevelWidgets())


def test_main_window_startup_geometry_is_clamped_to_available_screen() -> None:
    available = QRect(40, 30, 900, 620)
    size = clamp_window_size_to_available(QSize(1180, 760), available)
    assert size.width() <= available.width()
    assert size.height() <= available.height()

    restored = clamp_window_geometry_to_available(QRect(1600, 1200, 1400, 1000), available)
    assert available.contains(restored)
    assert restored.width() <= available.width()
    assert restored.height() <= available.height()


def test_main_window_minimum_height_does_not_exceed_available_screen() -> None:
    app = _app()
    window = MainWindow()
    screen = app.primaryScreen()
    assert screen is not None
    assert window.minimumSizeHint().height() <= screen.availableGeometry().height()
    assert window.minimumSize().height() <= screen.availableGeometry().height()


def test_main_window_layout_minimums_fit_typical_1080p_work_area_with_mk_upgrade() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    assert tabs is not None
    assert inventory_view is not None
    tabs.setCurrentWidget(inventory_view)
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(2)
    inventory_view.refresh()
    window.resize(1280, 900)
    window.show()
    QApplication.processEvents()

    work_area = QSize(1920, 1000)
    assert window.centralWidget().minimumSizeHint().width() <= work_area.width() - 240
    assert window.centralWidget().minimumSizeHint().height() <= work_area.height() - 120
    assert tabs.minimumSizeHint().width() <= 1180
    assert tabs.minimumSizeHint().height() <= 650
    assert inventory_view.minimumSizeHint().width() <= 960
    assert inventory_view.minimumSizeHint().height() <= 720

    for object_name in (
        "inventoryFilterScroll",
        "craftTargetFilterScroll",
        "craftMaterialFilterScroll",
        "mkUpgradeFilterScroll",
    ):
        scroll = inventory_view.findChild(QScrollArea, object_name)
        assert scroll is not None
        assert scroll.minimumSizeHint().width() <= 180
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        if scroll.isVisible():
            assert scroll.widget() is not None
            assert scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
            assert scroll.widget().width() >= scroll.viewport().width()

    result_panel = inventory_view.findChild(QFrame, "mkUpgradeResultPanel")
    button = inventory_view.findChild(QPushButton, "mkUpgradeButton")
    assert result_panel is not None
    assert button is not None
    assert result_panel.minimumSizeHint().height() <= 540
    assert button.isVisible()


def test_inventory_filter_scrolls_keep_desktop_filterdeck_footprint_without_minimum_width() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    assert tabs is not None
    assert inventory_view is not None
    tabs.setCurrentWidget(inventory_view)
    sub_tabs = inventory_view.findChild(QTabWidget, "inventorySubTabs")
    sub_tabs.setCurrentIndex(0)
    inventory_view.refresh()
    window.resize(1600, 980)
    window.show()
    QApplication.processEvents()

    visible_filter_scrolls = (
        (0, "inventoryFilterScroll", "target", 1100, 1220),
        (1, "craftTargetFilterScroll", "target", 940, 1000),
        (1, "craftMaterialFilterScroll", "materials", 780, 900),
        (2, "mkUpgradeFilterScroll", "target", 940, 1000),
    )
    for subtab_index, object_name, craft_mode, minimum_desktop_width, maximum_desktop_width in visible_filter_scrolls:
        sub_tabs.setCurrentIndex(subtab_index)
        if subtab_index == 1:
            inventory_view._craft_selection_mode = craft_mode
        inventory_view.refresh()
        QApplication.processEvents()
        scroll = inventory_view.findChild(QScrollArea, object_name)
        assert scroll is not None
        assert scroll.isVisible()
        assert scroll.minimumSizeHint().width() <= 180
        assert minimum_desktop_width <= scroll.sizeHint().width() <= maximum_desktop_width
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.horizontalScrollBar().isVisible() is False
        assert scroll.widget() is not None
        assert scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        assert scroll.widget().width() >= scroll.viewport().width()


def test_inventory_desktop_splits_keep_pre_resize_visual_proportions() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = window.findChild(InventoryView)
    assert tabs is not None
    assert inventory_view is not None
    tabs.setCurrentWidget(inventory_view)
    sub_tabs = inventory_view.findChild(QTabWidget, "inventorySubTabs")
    window.resize(1700, 900)
    window.show()
    QApplication.processEvents()

    sub_tabs.setCurrentIndex(1)
    inventory_view.refresh()
    QApplication.processEvents()
    craft_selection = inventory_view.findChild(QFrame, "craftSelectionPanel")
    craft_preview = inventory_view.findChild(QFrame, "craftPreviewPanel")
    craft_target_filter = inventory_view.findChild(QScrollArea, "craftTargetFilterScroll")
    craft_material_filter = inventory_view.findChild(QScrollArea, "craftMaterialFilterScroll")
    craft_target_scroll = inventory_view.findChild(QScrollArea, "craftTargetScroll")
    assert craft_selection is not None
    assert craft_preview is not None
    assert craft_target_filter is not None
    assert craft_material_filter is not None
    assert craft_target_scroll is not None
    assert craft_target_filter.isVisible()
    assert not craft_material_filter.isVisible()
    assert craft_selection.width() > craft_preview.width()
    assert craft_selection.width() >= craft_preview.width() * 2
    assert craft_preview.width() <= 460
    assert craft_target_filter.width() >= craft_selection.width() - 40
    assert craft_target_scroll.geometry().top() - craft_target_filter.geometry().bottom() <= 16

    sub_tabs.setCurrentIndex(2)
    inventory_view.refresh()
    QApplication.processEvents()
    mk_selection = inventory_view.findChild(QFrame, "mkUpgradePanel")
    mk_result = inventory_view.findChild(QFrame, "mkUpgradeResultPanel")
    mk_filter = inventory_view.findChild(QScrollArea, "mkUpgradeFilterScroll")
    mk_card_scroll = inventory_view.findChild(QScrollArea, "mkUpgradeCardScroll")
    mk_current = inventory_view.findChild(QFrame, "mkUpgradeCurrentCard")
    mk_target = inventory_view.findChild(QFrame, "mkUpgradeTargetCard")
    mk_compare = inventory_view.findChild(QFrame, "mkUpgradeComparePanel")
    assert mk_selection is not None
    assert mk_result is not None
    assert mk_filter is not None
    assert mk_card_scroll is not None
    assert mk_current is not None
    assert mk_target is not None
    assert mk_compare is not None
    assert mk_selection.width() > mk_result.width()
    assert mk_selection.width() >= mk_result.width() * 2
    assert mk_result.width() <= 560
    assert mk_selection.width() >= 900
    assert mk_filter.width() >= mk_selection.width() - 40
    assert mk_card_scroll.geometry().top() - mk_filter.geometry().bottom() <= 16
    assert mk_current.geometry().size() == mk_target.geometry().size()
    assert mk_compare.geometry().top() > mk_current.geometry().bottom()
    assert mk_compare.geometry().top() > mk_target.geometry().bottom()
    assert inventory_view.minimumSizeHint().width() <= 960
    assert window.centralWidget().minimumSizeHint().width() <= 1680


def test_charts_overview_shows_rising_falling_and_neutral_status() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    charts._state.history.append("rate.production.iron_ore", 9)
    charts._state.history.append("rate.consumption.iron_ore", 3)
    charts._state.history.append("rate.production.coal", 2)
    charts._state.history.append("rate.consumption.coal", 8)
    charts._state.history.append("rate.production.copper", 4)
    charts._state.history.append("rate.consumption.copper", 4)
    charts.refresh()

    cards = _chart_resource_cards_by_name(charts)
    assert cards["Iron Ore"].property("status") == "rising"
    assert cards["Coal"].property("status") == "falling"
    assert cards["Copper"].property("status") == "neutral"
    assert cards["Iron Ore"].findChild(QLabel, "chartResourceNetChange").text() == "+6.0"
    assert "/ min" not in cards["Iron Ore"].findChild(QLabel, "chartResourceNetChange").text()


def test_charts_overview_search_filters_resources() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    search = charts.findChild(QLineEdit, "chartResourceSearch")
    assert search is not None
    search.setText("iron ore")

    assert list(_chart_resource_cards_by_name(charts)) == ["Iron Ore"]


def test_charts_overview_filters_and_sorts_resource_tiles() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    charts._state.history.append("rate.production.iron_ore", 3)
    charts._state.history.append("rate.consumption.iron_ore", 1)
    charts._state.history.append("rate.production.steel", 12)
    charts._state.history.append("rate.consumption.steel", 2)
    charts._state.resources["steel"].amount = 80
    charts._state.resources["coal"].amount = 20
    charts.refresh()

    sort = charts.findChild(QComboBox, "chartSortSelect")
    stage = charts.findChild(QComboBox, "chartStageFilter")
    category = charts.findChild(QComboBox, "chartCategoryFilter")
    activity = charts.findChild(QComboBox, "chartActivityFilter")
    assert sort is not None
    assert stage is not None
    assert category is not None
    assert activity is not None
    names_by_name = list(_chart_resource_cards_by_name(charts))
    assert names_by_name == sorted(names_by_name)

    activity.setCurrentText("Producing")
    assert {"Steel", "Iron Ore"}.issubset(_chart_resource_cards_by_name(charts))
    activity.setCurrentText("Consuming")
    assert "Coal" not in _chart_resource_cards_by_name(charts)
    charts._state.history.append("rate.production.coal", 1)
    charts._state.history.append("rate.consumption.coal", 4)
    charts.refresh()
    assert list(_chart_resource_cards_by_name(charts)) == ["Coal"]
    activity.setCurrentText("All")
    category.setCurrentText("Ores / Metals")
    assert "Iron Ore" in _chart_resource_cards_by_name(charts)
    stage.setCurrentText("Extraction")
    assert "Iron Ore" in _chart_resource_cards_by_name(charts)
    category.setCurrentText("All")
    stage.setCurrentText("All")
    sort.setCurrentText("Net Change")
    assert list(_chart_resource_cards_by_name(charts))[:3] == ["Steel", "Coal", "Iron Ore"]
    sort.setCurrentText("Amount")
    assert list(_chart_resource_cards_by_name(charts))[0] == "Iron Ore"


def test_charts_resource_detail_and_back_navigation() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    stack = charts.findChild(QStackedWidget, "chartsStack")
    assert stack is not None
    _chart_resource_cards_by_name(charts)["Steel"].mousePressEvent(None)

    assert stack.currentIndex() == 1
    assert charts.findChild(QLabel, "chartDetailTitle").text() == "Steel"
    assert charts.findChild(ResourceIconWidget) is not None
    assert charts.findChild(QLabel, "chartDetailAmount").text().endswith(" / 200")
    stack.resize(1400, 700)
    charts._detail_layout_signature = None
    charts._layout_detail_charts()
    chart_widgets = charts.findChildren(QWidget, "lineChart")
    assert charts._detail_chart_columns() == 3
    assert [chart.property("detailGridColumn") for chart in chart_widgets] == [0, 1, 2]
    assert [chart.property("detailGridRow") for chart in chart_widgets] == [0, 0, 0]
    assert len({chart.minimumHeight() for chart in chart_widgets}) == 1
    assert [charts._resource_chart_layout.columnStretch(index) for index in range(3)] == [1, 1, 1]
    assert all(chart.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding for chart in chart_widgets)
    assert all(chart.minimumWidth() == 0 for chart in chart_widgets)
    assert all(chart.maximumWidth() > 100_000 for chart in chart_widgets)
    detail_reflows = charts._detail_reflow_count
    charts._state.resources["steel"].amount = 95
    charts.refresh()
    assert charts._detail_reflow_count == detail_reflows
    assert [chart.property("detailGridColumn") for chart in chart_widgets] == [0, 1, 2]
    assert [chart.property("detailGridRow") for chart in chart_widgets] == [0, 0, 0]
    stack.resize(900, 700)
    charts._layout_detail_charts()
    assert charts._detail_chart_columns() == 2
    assert [chart.property("detailGridColumn") for chart in chart_widgets] == [0, 1, 0]
    assert [chart.property("detailGridRow") for chart in chart_widgets] == [0, 0, 1]
    stack.resize(620, 700)
    charts._layout_detail_charts()
    assert charts._detail_chart_columns() == 1
    assert [chart.property("detailGridColumn") for chart in chart_widgets] == [0, 0, 0]
    assert [chart.property("detailGridRow") for chart in chart_widgets] == [0, 1, 2]
    titles = [chart._series.title for chart in charts.findChildren(QWidget, "lineChart")]
    assert "Steel Stock" in titles
    assert "Steel Production Rate" in titles
    assert "Steel Consumption Rate" in titles
    range_select = charts.findChild(QComboBox, "chartRangeSelect")
    assert range_select is not None
    range_select.setCurrentText("1H")
    assert all(chart._range_id == "1H" for chart in chart_widgets)

    charts.findChild(QPushButton, "chartBackButton").click()

    assert stack.currentIndex() == 0


def test_charts_runtime_refresh_preserves_filter_and_detail_state() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    stack = charts.findChild(QStackedWidget, "chartsStack")
    search = charts.findChild(QLineEdit, "chartResourceSearch")
    assert stack is not None
    assert search is not None
    search.setText("iron ore")
    first_card = _chart_resource_cards_by_name(charts)["Iron Ore"]
    pool_size = len(charts._resource_tile_pool)
    reflow_count = charts._overview_reflow_count
    charts._state.resources["iron_ore"].amount = 200
    charts.refresh()
    assert search.text() == "iron ore"
    assert _chart_resource_cards_by_name(charts)["Iron Ore"] is first_card
    assert len(charts._resource_tile_pool) == pool_size
    assert charts._overview_reflow_count == reflow_count
    assert first_card.findChild(QLabel, "chartResourceAmount").text() == "200 / 500"

    first_card.mousePressEvent(None)
    assert stack.currentIndex() == 1
    charts._state.resources["iron_ore"].amount = 210
    charts.refresh()
    assert stack.currentIndex() == 1
    assert charts.findChild(QLabel, "chartDetailTitle").text() == "Iron Ore"
    assert charts.findChild(QLabel, "chartDetailAmount").text() == "210 / 500"


def test_charts_redesign_uses_header_chip_filters_and_modern_detail_controls() -> None:
    _app()
    window = MainWindow()
    charts = window.findChild(ChartsView)
    assert charts is not None

    header = charts.findChild(QFrame, "chartsHeader")
    assert header is not None
    assert header.findChild(QLabel, "chartsHeroTitle").text() == "CHARTS"
    assert header.findChild(QLabel, "chartsHeroSubtitle").text() == "RESOURCE FLOW / ANALYTICS"

    filter_scroll = charts.findChild(QScrollArea, "chartFilterScroll")
    assert filter_scroll is not None
    assert filter_scroll.minimumSizeHint().width() <= 180
    assert filter_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert filter_scroll.widget() is not None
    assert filter_scroll.widget().objectName() == "chartFilterDeck"
    assert filter_scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    sort = charts.findChild(QComboBox, "chartSortSelect")
    stage = charts.findChild(QComboBox, "chartStageFilter")
    category = charts.findChild(QComboBox, "chartCategoryFilter")
    activity = charts.findChild(QComboBox, "chartActivityFilter")
    assert all(combo is not None and not combo.isVisible() for combo in (sort, stage, category, activity))

    chips = charts.findChildren(QPushButton, "chartFilterChip")
    chip_groups = {chip.property("filterGroup") for chip in chips}
    assert {"chartSortSelect", "chartStageFilter", "chartCategoryFilter", "chartActivityFilter"}.issubset(chip_groups)
    active_chip = next(chip for chip in chips if chip.property("filterGroup") == "chartActivityFilter" and chip.property("filterValue") == "Active")
    active_chip.click()
    assert activity.currentText() == "Active"
    all_activity_chip = next(chip for chip in charts.findChildren(QPushButton, "chartFilterChip") if chip.property("filterGroup") == "chartActivityFilter" and chip.property("filterValue") == "All")
    all_activity_chip.click()

    iron_ore = _chart_resource_cards_by_name(charts)["Iron Ore"]
    assert iron_ore.findChild(QFrame, "chartResourceIconHost") is not None
    assert iron_ore.findChild(ResourceIconWidget, "resourceIcon") is not None

    _chart_resource_cards_by_name(charts)["Steel"].mousePressEvent(None)
    detail_header = charts.findChild(QFrame, "chartDetailHeader")
    range_select = charts.findChild(QComboBox, "chartRangeSelect")
    assert detail_header is not None
    assert range_select is not None and not range_select.isVisible()
    range_chips = [
        chip
        for chip in charts.findChildren(QPushButton, "chartFilterChip")
        if chip.property("filterGroup") == "chartRangeSelect"
    ]
    assert [chip.property("filterValue") for chip in range_chips] == ["10M", "1H", "6H", "24H", "ALL"]
    range_chips[1].click()
    assert range_select.currentText() == "1H"
    assert {chart.property("chartRole") for chart in charts.findChildren(QWidget, "lineChart")} == {"stock", "production", "consumption"}


def test_charts_redesign_offscreen_previews() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    charts = window.findChild(ChartsView)
    assert tabs is not None
    assert charts is not None

    tabs.setCurrentWidget(charts)
    window.resize(1600, 980)
    window.show()
    charts._state.resources["steel"].amount = 95
    for value in (40, 58, 73, 95):
        charts._state.history.append("resource.steel", value)
    for value in (8, 11, 14, 18):
        charts._state.history.append("rate.production.steel", value)
    for value in (2, 5, 6, 7):
        charts._state.history.append("rate.consumption.steel", value)
    charts.refresh()
    QApplication.processEvents()

    preview_dir = Path("artifacts")
    preview_dir.mkdir(exist_ok=True)

    overview_path = preview_dir / "charts_overview_redesign_preview.png"
    assert charts.grab().toImage().save(str(overview_path))

    charts._show_resource_detail("steel")
    QApplication.processEvents()
    detail_path = preview_dir / "charts_detail_redesign_preview.png"
    assert charts.grab().toImage().save(str(detail_path))

    charts._show_resource_detail("ai_server")
    QApplication.processEvents()
    empty_detail_path = preview_dir / "charts_detail_empty_redesign_preview.png"
    assert charts.grab().toImage().save(str(empty_detail_path))

    charts._show_overview()
    window.resize(860, 680)
    QApplication.processEvents()
    responsive_path = preview_dir / "charts_overview_responsive_filter_preview.png"
    assert charts.grab().toImage().save(str(responsive_path))

    for path in (overview_path, detail_path, empty_detail_path, responsive_path):
        assert path.exists()
        assert path.stat().st_size > 0


def test_market_tab_opens_overview_with_event_banner_and_watchlist_table() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert market_view is not None
    assert tabs is not None

    stack = market_view.findChild(QStackedWidget, "marketStack")
    event_panel = market_view.findChild(QFrame, "marketEventPanel")
    search = market_view.findChild(QLineEdit, "marketSearch")
    stage = market_view.findChild(QComboBox, "marketStageFilter")
    category = market_view.findChild(QComboBox, "marketCategoryFilter")
    event_filter = market_view.findChild(QComboBox, "marketEventFilter")
    trend = market_view.findChild(QComboBox, "marketTrendFilter")
    sort = market_view.findChild(QComboBox, "marketSortSelect")
    timeframe = market_view.findChild(QComboBox, "marketTimeframeSelect")
    rows = _market_table_rows_by_name(market_view)

    assert stack is not None
    assert stack.currentIndex() == 0
    assert event_panel is not None
    assert event_panel.findChild(QLabel, "marketEventName").text() == "Industrial Boom"
    assert "Affected:" in event_panel.findChild(QLabel, "marketEventAffected").text()
    assert "Remaining:" in event_panel.findChild(QLabel, "marketEventRemaining").text()
    assert search is not None
    assert search.placeholderText() == "Search market..."
    assert stage is not None
    assert [stage.itemText(index) for index in range(stage.count())] == ["All", "Extraction", "Processing", "Manufacturing", "Assembly"]
    assert category is not None
    assert event_filter is not None
    assert [event_filter.itemText(index) for index in range(event_filter.count())] == ["All", "Event Affected", "No Active Event"]
    assert trend is not None
    assert [trend.itemText(index) for index in range(trend.count())] == ["All", "Rising", "Falling", "Neutral"]
    assert sort is not None
    assert [sort.itemText(index) for index in range(sort.count())] == ["Name", "Price", "24h Change", "7d Change", "30d Change"]
    assert timeframe is not None
    assert [timeframe.itemText(index) for index in range(timeframe.count())] == ["24H", "7D", "30D", "90D"]
    table = market_view.findChild(QTableView, "marketTableView")
    assert table is not None
    assert table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert table.itemDelegate().__class__.__name__ == "MarketTableDelegate"
    assert table.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert {"Iron Ore", "Coal", "Copper Ore", "Iron", "Copper", "Steel", "AI Server"}.issubset(rows)
    assert len(rows) > 300
    assert _market_table_text(market_view, "Iron Ore", 1).startswith("$")
    assert _market_table_text(market_view, "Iron Ore", 6).startswith("$")
    assert market_view.findChild(QFrame, "marketCard") is None
    assert market_view.findChild(QFrame, "marketRow") is None
    assert market_view.findChild(QTableWidget, "marketTable") is None


def test_market_redesign_uses_header_filter_chips_and_hidden_state_anchors() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert market_view is not None
    assert tabs is not None

    header = market_view.findChild(QFrame, "marketHeader")
    assert header is not None
    assert header.findChild(QLabel, "marketHeroTitle").text() == "MARKET"
    assert header.findChild(QLabel, "marketHeroSubtitle").text() == "RESOURCE EXCHANGE / PRICING"
    assert [label.text() for label in header.findChildren(QLabel, "marketMetricLabel")] == ["ACTIVE EVENT", "REMAINING"]

    filter_scroll = market_view.findChild(QScrollArea, "marketFilterScroll")
    assert filter_scroll is not None
    assert filter_scroll.minimumSizeHint().width() <= 180
    assert filter_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert filter_scroll.widget() is not None
    assert filter_scroll.widget().objectName() == "marketFilterDeck"
    assert filter_scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    stage = market_view.findChild(QComboBox, "marketStageFilter")
    category = market_view.findChild(QComboBox, "marketCategoryFilter")
    event_filter = market_view.findChild(QComboBox, "marketEventFilter")
    trend = market_view.findChild(QComboBox, "marketTrendFilter")
    sort = market_view.findChild(QComboBox, "marketSortSelect")
    timeframe = market_view.findChild(QComboBox, "marketTimeframeSelect")
    assert all(combo is not None and not combo.isVisible() for combo in (stage, category, event_filter, trend, sort, timeframe))

    chips = market_view.findChildren(QPushButton, "marketFilterChip")
    chip_groups = {chip.property("filterGroup") for chip in chips}
    assert {
        "marketStageFilter",
        "marketEventFilter",
        "marketTrendFilter",
        "marketTimeframeSelect",
    }.issubset(chip_groups)

    category_chips = [chip for chip in chips if chip.property("filterGroup") == "marketCategoryFilter"]
    sort_chips = [chip for chip in chips if chip.property("filterGroup") == "marketSortSelect"]
    assert category_chips == []
    assert sort_chips == []
    category_button = market_view.findChild(QPushButton, "marketCategorySelectorButton")
    sort_button = market_view.findChild(QPushButton, "marketSortSelectorButton")
    assert category_button is not None
    assert category_button.text() == "ALL >"
    assert sort_button is not None
    assert sort_button.text() == "NAME >"
    tabs.setCurrentWidget(market_view)
    window.show()
    QApplication.processEvents()
    sort_button.click()
    QApplication.processEvents()
    sort_flyout = next(
        flyout
        for flyout in market_view.findChildren(QFrame, "marketSelectorFlyout")
        if flyout.property("selectorFor") == "marketSortSelect"
    )
    assert sort_flyout.isVisible()
    assert not sort_flyout.isWindow()
    price_option = next(option for option in sort_flyout.findChildren(QPushButton, "marketSelectorOption") if option.property("filterValue") == "Price")
    price_option.click()
    assert sort.currentText() == "Price"
    assert sort_button.text() == "PRICE >"
    assert not sort_flyout.isVisible()
    assert list(_market_table_rows_by_name(market_view))


def test_market_overview_search_filters_market_rows() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    assert market_view is not None

    search = market_view.findChild(QLineEdit, "marketSearch")
    assert search is not None
    search.setText("iron ore")

    assert list(_market_table_rows_by_name(market_view)) == ["Iron Ore"]


def test_market_overview_filters_and_sorts_watchlist_rows() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    assert market_view is not None

    market_view._state.market.resources["iron_ore"].current_price = 50_000.0
    market_view._state.market.resources["steel"].current_price = 100_000.0
    market_view._state.market.resources["coal"].last_change = 2_000.0
    market_view._state.market.resources["copper"].last_change = -2_000.0
    market_view._state.market.resources["copper_ore"].last_change = -1_500.0
    market_view.refresh()

    sort = market_view.findChild(QComboBox, "marketSortSelect")
    stage = market_view.findChild(QComboBox, "marketStageFilter")
    category = market_view.findChild(QComboBox, "marketCategoryFilter")
    event_filter = market_view.findChild(QComboBox, "marketEventFilter")
    trend = market_view.findChild(QComboBox, "marketTrendFilter")
    assert sort is not None
    assert stage is not None
    assert category is not None
    assert event_filter is not None
    assert trend is not None
    names_by_name = list(_market_table_rows_by_name(market_view))
    assert names_by_name == sorted(names_by_name)

    sort.setCurrentText("Price")
    assert list(_market_table_rows_by_name(market_view))[:2] == ["Steel", "Iron Ore"]

    sort.setCurrentText("24h Change")
    assert list(_market_table_rows_by_name(market_view))[0] == "Coal"

    stage.setCurrentText("Extraction")
    assert "Iron Ore" in _market_table_rows_by_name(market_view)
    category.setCurrentText("Ores / Metals")
    assert "Iron Ore" in _market_table_rows_by_name(market_view)
    event_filter.setCurrentText("Event Affected")
    assert all(_market_table_text(market_view, name, 7) for name in _market_table_rows_by_name(market_view))
    event_filter.setCurrentText("All")
    trend.setCurrentText("Falling")
    assert "Copper Ore" in _market_table_rows_by_name(market_view)


def test_market_overview_marks_changes_events_and_period_values() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    assert market_view is not None

    market_view._state.market.resources["iron"].last_change = 0.35
    market_view._state.market.resources["copper"].last_change = -0.25
    market_view._state.market.resources["wheat"].last_change = 0.0
    market_view._state.market.resources["steel"].current_price = 120.0
    market_view._state.history.append("market.price.steel", 90.0)
    market_view._state.history.append("market.price.steel", 100.0)
    market_view.refresh()

    assert market_view._table_model._change_status(market_view._table_model.period_change("iron", "24H")) == "positive"
    assert market_view._table_model._change_status(market_view._table_model.period_change("copper", "24H")) == "negative"
    assert market_view._table_model._change_status(market_view._table_model.period_change("wheat", "24H")) == "neutral"
    assert _market_table_text(market_view, "Iron", 2).startswith("+0.35")
    assert _market_table_text(market_view, "Steel", 3).startswith("+30.00")
    assert _market_table_text(market_view, "Iron", 7) == "Industrial Boom"
    assert _market_table_text(market_view, "Wheat", 7) == ""


def test_market_row_opens_resource_detail_and_runtime_refresh_preserves_state() -> None:
    _app()
    window = MainWindow()
    market_view = window.findChild(MarketView)
    assert market_view is not None

    stack = market_view.findChild(QStackedWidget, "marketStack")
    assert stack is not None
    search = market_view.findChild(QLineEdit, "marketSearch")
    sort = market_view.findChild(QComboBox, "marketSortSelect")
    timeframe = market_view.findChild(QComboBox, "marketTimeframeSelect")
    assert search is not None
    assert sort is not None
    assert timeframe is not None
    search.setText("steel")
    sort.setCurrentText("Price")
    timeframe.setCurrentText("30D")
    table = market_view.findChild(QTableView, "marketTableView")
    assert table is not None
    first_row = _market_table_rows_by_name(market_view)["Steel"]
    table.clicked.emit(market_view._proxy_model.index(first_row, 0))

    assert stack.currentIndex() == 1
    assert market_view.findChild(QLabel, "marketDetailTitle").text() == "Steel"
    assert market_view.findChild(ResourceIconWidget, "resourceIcon") is not None
    assert market_view.findChild(QLabel, "marketDetailPrice").text().startswith("$")
    for selector in (
        "QLabel#marketDetailTitle",
        "QLabel#marketDetailPrice",
        "QLabel#marketDetailChange",
    ):
        style = _style_block(selector)
        assert "background: transparent" in style
        assert "border: 0" in style
        assert "#000" not in style
        assert "black" not in style.lower()
    icon_host_style = _style_block("QFrame#marketDetailIconHost")
    assert "rgba(255, 255, 255, 8)" in icon_host_style
    assert "rgba(255, 210, 31, 84)" in icon_host_style
    summary = market_view.findChild(QFrame, "marketDetailSummary")
    assert summary is not None
    detail_labels = [label.text() for label in summary.findChildren(QLabel, "marketDetailMetricLabel")]
    detail_values = [label.text() for label in summary.findChildren(QLabel, "marketDetailMetric")]
    assert detail_labels == ["ANCHOR PRICE", "ACTIVE EVENT", "PERIOD HIGH", "PERIOD LOW", "PERIOD AVERAGE", "PERIOD CHANGE"]
    assert "Industrial Boom" in detail_values
    assert "background: transparent" in _style_block("QLabel#marketDetailMetricLabel")
    assert "background: transparent" in _style_block("QLabel#marketDetailMetric")
    detail_range = market_view.findChild(QComboBox, "marketDetailRangeSelect")
    assert detail_range is not None
    assert not detail_range.isVisible()
    assert [detail_range.itemText(index) for index in range(detail_range.count())] == ["24H", "7D", "30D", "90D", "ALL"]
    range_chips = [
        chip
        for chip in market_view.findChildren(QPushButton, "marketFilterChip")
        if chip.property("filterGroup") == "marketDetailRangeSelect"
    ]
    assert [chip.property("filterValue") for chip in range_chips] == ["24H", "7D", "30D", "90D", "ALL"]
    detail_chart = market_view.findChild(QWidget, "marketDetailChart")
    assert detail_chart is not None
    assert market_view.findChild(QFrame, "marketChartPanel") is not None
    assert detail_chart._scaled_y_range((180.0, 190.0))[0] > 0
    flat_min, flat_max = detail_chart._scaled_y_range((8.0, 8.0))
    assert flat_min < 8.0 < flat_max
    detail_chart.resize(640, 260)
    detail_chart.grab()
    assert detail_chart._axes_drawn is True
    delegate = market_view.findChild(QTableView, "marketTableView").itemDelegate()
    source_index = market_view._proxy_model.mapToSource(market_view._proxy_model.index(first_row, 0))
    assert market_view._table_model.data(source_index, Qt.ItemDataRole.UserRole) == "steel"
    assert "background: transparent" in _style_block("QLabel#marketDetailMetricLabel")
    assert "QTableView#marketTableView QHeaderView::section" in APP_STYLESHEET
    market_view._state.market.resources["steel"].current_price += 3.0
    structural_refresh_count = market_view._structural_refresh_count
    model = market_view._market_table.model()
    market_view.refresh()
    assert stack.currentIndex() == 1
    assert search.text() == "steel"
    assert sort.currentText() == "Price"
    assert timeframe.currentText() == "30D"
    assert market_view._structural_refresh_count == structural_refresh_count
    assert market_view._market_table.model() is model

    market_view.findChild(QPushButton, "marketBackButton").click()

    assert stack.currentIndex() == 0
    assert "Steel" in _market_table_rows_by_name(market_view)
    assert search.text() == "steel"


def test_market_redesign_offscreen_previews() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    market_view = window.findChild(MarketView)
    assert tabs is not None
    assert market_view is not None

    tabs.setCurrentWidget(market_view)
    window.resize(1600, 980)
    window.show()
    market_view._state.market.resources["steel"].current_price = 122.0
    for value in (90.0, 104.0, 114.0, 122.0):
        market_view._state.history.append("market.price.steel", value)
    market_view.refresh()
    QApplication.processEvents()

    preview_dir = Path("artifacts")
    preview_dir.mkdir(exist_ok=True)

    overview_path = preview_dir / "market_overview_redesign_preview.png"
    assert market_view.grab().toImage().save(str(overview_path))

    market_view._show_detail("steel")
    QApplication.processEvents()
    detail_path = preview_dir / "market_detail_redesign_preview.png"
    assert market_view.grab().toImage().save(str(detail_path))

    market_view._show_detail("ai_server")
    QApplication.processEvents()
    empty_detail_path = preview_dir / "market_detail_empty_redesign_preview.png"
    assert market_view.grab().toImage().save(str(empty_detail_path))

    market_view._show_overview()
    window.resize(860, 680)
    QApplication.processEvents()
    responsive_path = preview_dir / "market_overview_responsive_filter_preview.png"
    assert market_view.grab().toImage().save(str(responsive_path))

    for path in (overview_path, detail_path, empty_detail_path, responsive_path):
        assert path.exists()
        assert path.stat().st_size > 0


def test_contract_cards_show_sections_and_available_state_without_active_panels() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None
    _install_contract_test_freight(contracts_view)

    section_titles = [label.text() for label in contracts_view.findChildren(QLabel, "contractSectionTitle")]
    section_subtitles = [label.text() for label in contracts_view.findChildren(QLabel, "contractSectionSubtitle")]
    cards = contracts_view.findChildren(QFrame, "contractCard")
    accept_buttons = contracts_view.findChildren(QPushButton, "acceptContractButton")
    scroll = contracts_view.findChild(QScrollArea)

    assert section_titles == ["REGULAR CONTRACTS", "DAILY CONTRACTS", "WEEKLY CONTRACTS"]
    assert section_subtitles[0] == "Repeatable · No expiration"
    assert section_subtitles[1].startswith("Resets in")
    assert section_subtitles[2].startswith("Resets in")
    assert len(cards) == 9
    assert len(accept_buttons) == 9
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert all(card.property("state") == "available" for card in cards)
    assert all(button.isEnabled() for button in accept_buttons)
    assert all(card.findChild(QLabel, "contractCardTitle") is not None for card in cards)
    assert all(card.findChild(QLabel, "contractCardStatus") is not None for card in cards)
    assert all(card.findChildren(QWidget, "resourceIcon") for card in cards)
    assert all(card.findChildren(QFrame, "contractRewardChip") for card in cards)
    assert contracts_view.findChild(QFrame, "contractActivePanel") is None


def test_contracts_redesign_uses_header_three_column_board_and_compact_cards() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    contracts_view = window.findChild(ContractsView)
    assert tabs is not None
    assert contracts_view is not None

    tabs.setCurrentWidget(contracts_view)
    window.resize(1600, 980)
    window.show()
    QApplication.processEvents()

    header = contracts_view.findChild(QFrame, "contractsHeader")
    assert header is not None
    assert header.findChild(QLabel, "contractsHeroTitle").text() == "CONTRACTS"
    assert header.findChild(QLabel, "contractsHeroSubtitle").text() == "DELIVERY / OBJECTIVES"
    assert [label.text() for label in header.findChildren(QLabel, "contractsMetricLabel")] == ["ACTIVE", "DAILY RESET", "WEEKLY RESET"]

    board = contracts_view.findChild(QWidget, "contractsBoard")
    scroll = contracts_view.findChild(QScrollArea, "contractsBoardScroll")
    assert board is not None
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.verticalScrollBar().maximum() == 0

    panels = contracts_view.findChildren(QFrame, "contractPanel")
    assert [panel.property("kind") for panel in panels] == ["regular", "daily", "weekly"]
    assert len({panel.geometry().top() for panel in panels}) == 1
    assert all(panel.width() >= 300 for panel in panels)

    cards = contracts_view.findChildren(QFrame, "contractCard")
    assert len(cards) == 9
    assert len({card.height() for card in cards}) == 1
    assert all(card.maximumHeight() == 168 for card in cards)
    assert all(not card.findChildren(QProgressBar, "contractRequirementProgress") for card in cards)
    assert all(card.findChildren(QLabel, "contractRequirementAmount") for card in cards)
    multi_requirement_cards = [card for card in cards if len(card.findChildren(QFrame, "contractRequirementRow")) > 1]
    assert multi_requirement_cards
    for card in multi_requirement_cards:
        inline = card.findChild(QFrame, "contractRequirementsInline")
        assert inline is not None
        requirement_rows = inline.findChildren(QFrame, "contractRequirementRow")
        assert len(requirement_rows) > 1
        assert inline.layout().count() == len(requirement_rows)
        assert all(inline.layout().itemAt(index).widget() in requirement_rows for index in range(inline.layout().count()))
    assert all(card.findChildren(QFrame, "contractRewardChip") for card in cards)


def test_contract_mission_board_styles_have_no_black_child_boxes() -> None:
    for selector in (
        "QFrame#contractRequirements",
        "QFrame#contractRequirementsInline",
        "QFrame#contractRewards",
        "QFrame#contractActionFooter",
        "QFrame#contractRequirementRow",
        "QLabel#contractSectionTitle",
        "QLabel#contractSectionSubtitle",
        "QLabel#contractCardTitle",
        "QLabel#contractBlockTitle",
        "QLabel#contractRequirementLabel",
        "QLabel#contractRequirementAmount",
        "QLabel#contractRewardLabel",
        "QLabel#contractRewardIcon",
    ):
        style = _style_block(selector)
        assert "background: transparent" in style
        assert "#000" not in style
        assert "black" not in style.lower()


def test_contracts_redesign_offscreen_preview() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    contracts_view = window.findChild(ContractsView)
    assert tabs is not None
    assert contracts_view is not None

    tabs.setCurrentWidget(contracts_view)
    window.resize(1600, 980)
    window.show()
    QApplication.processEvents()

    path = Path("artifacts") / "contracts_redesign_preview.png"
    path.parent.mkdir(exist_ok=True)
    assert contracts_view.grab().toImage().save(str(path))
    assert path.exists()
    assert path.stat().st_size > 0


def test_contract_available_card_becomes_active_and_other_cards_disable() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None

    regular_cards = _contract_cards_by_kind(contracts_view, "regular")
    accepted_id = regular_cards[0].property("contractId")
    regular_cards[0].findChild(QPushButton, "acceptContractButton").click()

    regular_cards = _contract_cards_by_kind(contracts_view, "regular")
    active_card = next(card for card in regular_cards if card.property("contractId") == accepted_id)
    disabled_cards = [card for card in regular_cards if card.property("contractId") != accepted_id]

    assert active_card.property("state") == "active"
    assert active_card.findChild(QLabel, "contractCardStatus").text() == "ACTIVE"
    assert active_card.findChild(QPushButton, "deliverContractButton") is not None
    assert all(card.property("state") == "disabled" for card in disabled_cards)
    assert all(not card.findChild(QPushButton, "acceptContractButton").isEnabled() for card in disabled_cards)
    assert contracts_view.findChild(QFrame, "contractActivePanel") is None


def test_contract_active_card_shows_requirement_amounts_and_deliver_available() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None
    _install_contract_test_freight(contracts_view)

    first_card = _contract_cards_by_kind(contracts_view, "regular")[0]
    first_card.findChild(QPushButton, "acceptContractButton").click()
    active = contracts_view._state.contracts.active["regular"]
    _fund_contract_resources(contracts_view, active.offer.requirements, ratio=0.5)
    contracts_view.refresh()

    active_card = next(card for card in _contract_cards_by_kind(contracts_view, "regular") if card.property("state") == "active")
    amount_labels = active_card.findChildren(QLabel, "contractRequirementAmount")
    deliver = active_card.findChild(QPushButton, "deliverContractButton")

    assert active_card.findChildren(QProgressBar, "contractRequirementProgress") == []
    assert len(amount_labels) == len(active.offer.requirements)
    assert all(label.property("progressPermille") == 0 for label in amount_labels)
    assert deliver is not None
    assert deliver.isEnabled()

    deliver.click()
    active_card = next(card for card in _contract_cards_by_kind(contracts_view, "regular") if card.property("state") == "active")
    amount_labels = active_card.findChildren(QLabel, "contractRequirementAmount")
    assert all(label.property("progressPermille") == 0 for label in amount_labels)

    _advance_contract_freight(contracts_view)
    active_card = next(card for card in _contract_cards_by_kind(contracts_view, "regular") if card.property("state") == "active")
    amount_labels = active_card.findChildren(QLabel, "contractRequirementAmount")

    assert all(0 < label.property("progressPermille") <= 500 for label in amount_labels)


def test_regular_contract_completion_regenerates_offers_unchanged() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None
    _install_contract_test_freight(contracts_view)

    first_card = _contract_cards_by_kind(contracts_view, "regular")[0]
    accepted_id = first_card.property("contractId")
    first_card.findChild(QPushButton, "acceptContractButton").click()
    active = contracts_view._state.contracts.active["regular"]
    _fund_contract_resources(contracts_view, active.offer.requirements)
    contracts_view.refresh()

    _deliver_contract_until_settled(contracts_view, "regular")

    assert "regular" not in contracts_view._state.contracts.active
    assert contracts_view._state.cash.amount == 1250 + active.offer.reward_cash
    assert contracts_view._state.company.current_xp == active.offer.reward_xp
    assert all(
        contracts_view._state.resources[resource_id].amount == 0
        for resource_id in active.offer.requirements
    )
    regular_cards = _contract_cards_by_kind(contracts_view, "regular")
    assert len(regular_cards) == 3
    assert all(card.property("state") == "available" for card in regular_cards)
    assert all(card.property("contractId") != accepted_id for card in regular_cards)


def test_daily_completed_card_remains_visible_until_reset_with_rewards() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None
    _install_contract_test_freight(contracts_view)

    daily_card = _contract_cards_by_kind(contracts_view, "daily")[0]
    accepted_id = daily_card.property("contractId")
    daily_card.findChild(QPushButton, "acceptContractButton").click()
    active = contracts_view._state.contracts.active["daily"]
    _fund_contract_resources(contracts_view, active.offer.requirements)
    contracts_view.refresh()

    _deliver_contract_until_settled(contracts_view, "daily")

    daily_cards = _contract_cards_by_kind(contracts_view, "daily")
    completed_card = next(card for card in daily_cards if card.property("contractId") == accepted_id)
    amount_labels = completed_card.findChildren(QLabel, "contractRequirementAmount")
    rewards = [label.text() for label in completed_card.findChildren(QLabel, "contractRewardLabel")]

    assert contracts_view._state.contracts.active["daily"].status == "completed"
    assert completed_card.property("state") == "completed"
    assert completed_card.findChild(QLabel, "contractCardStatus").text() == "COMPLETED"
    assert completed_card.findChildren(QProgressBar, "contractRequirementProgress") == []
    assert all(label.property("progressPermille") == 1000 for label in amount_labels)
    assert all(label.property("fulfilled") is True for label in amount_labels)
    assert "Daily Mini Pack" in rewards
    assert all(card.property("state") == "disabled" for card in daily_cards if card.property("contractId") != accepted_id)


def test_weekly_completed_card_remains_visible_until_reset_with_full_pack_reward() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None
    _install_contract_test_freight(contracts_view)

    weekly_card = _contract_cards_by_kind(contracts_view, "weekly")[0]
    accepted_id = weekly_card.property("contractId")
    weekly_card.findChild(QPushButton, "acceptContractButton").click()
    active = contracts_view._state.contracts.active["weekly"]
    _fund_contract_resources(contracts_view, active.offer.requirements)
    contracts_view.refresh()

    _deliver_contract_until_settled(contracts_view, "weekly")

    completed_card = next(card for card in _contract_cards_by_kind(contracts_view, "weekly") if card.property("contractId") == accepted_id)
    rewards = [label.text() for label in completed_card.findChildren(QLabel, "contractRewardLabel")]

    assert contracts_view._state.contracts.active["weekly"].status == "completed"
    assert completed_card.property("state") == "completed"
    assert "Full Pack" in rewards


def test_industrial_supply_tab_shows_common_card_grid_and_daily_choices() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()

    daily_cards = _daily_supply_cards(supply_view)
    freight_daily_cards = _daily_freight_supply_cards(supply_view)
    machine_daily_cards = _daily_machine_supply_cards(supply_view)

    stack = supply_view.findChild(QStackedWidget, "supplySectionStack")
    section_buttons = supply_view.findChildren(QPushButton, "supplySectionButton")
    assert stack is not None
    assert stack.count() == 2
    assert [button.text() for button in section_buttons] == ["DAILY SUPPLY", "COMMON SUPPLY"]
    assert stack.currentWidget().objectName() == "supplyDailyPage"
    assert supply_view.findChild(QLabel, "supplyDailyStatus").text().startswith("RESET\n")
    assert supply_view.findChild(QFrame, "supplyStoreHeader") is not None
    assert supply_view.findChild(QLabel, "supplyStoreTitle").text() == "INDUSTRIAL SUPPLY"
    section_subtitles = [label.text() for label in supply_view.findChildren(QLabel, "supplySectionSubtitle")]
    daily_section_subtitles = [label.text() for label in supply_view.findChildren(QLabel, "supplyDailySectionSubtitle")]
    daily_section_titles = [label.text() for label in supply_view.findChildren(QLabel, "supplyDailySectionTitle")]
    assert daily_section_subtitles == ["CHOOSE 1 OF 3", "CHOOSE 1 OF 3", "CHOOSE 1 OF 3"]
    assert "ALWAYS AVAILABLE" in section_subtitles
    assert daily_section_titles == ["DAILY RECIPES", "DAILY FREIGHT", "DAILY MACHINES"]
    assert len(supply_view._common_display_data) > 280
    assert supply_view.findChild(QComboBox, "supplyTypeFilter").itemText(0) != "All"
    assert supply_view.findChild(QFrame, "supplyHeaderMetric") is not None
    assert len(daily_cards) == 3
    assert len(freight_daily_cards) == 3
    assert len(machine_daily_cards) == 3
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in daily_cards}) == 3
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in freight_daily_cards}) == 3
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in machine_daily_cards}) == 3
    assert all(card.property("cardKind") == "recipe" for card in daily_cards)
    assert all(card.property("cardKind") == "freight" for card in freight_daily_cards)
    assert all(card.property("cardKind") in {"machine", "energy"} for card in machine_daily_cards)
    assert all(card.findChild(ResourceIconWidget, "supplyCardIcon") is not None for card in daily_cards)
    assert all(card.findChild(ResourceIconWidget, "supplyCardIcon") is not None for card in freight_daily_cards)
    assert all(card.findChild(ResourceIconWidget, "supplyCardIcon") is not None for card in machine_daily_cards)
    assert all(card.findChild(QFrame, "supplyRarityLine") is not None for card in daily_cards + freight_daily_cards + machine_daily_cards)
    assert supply_view.findChild(QTableWidget, "commonSupplyTable") is None
    assert supply_view.findChild(QTableWidget, "dailySupplyTable") is None
    assert all(card.findChild(QLabel, "supplyCardRarity").text() == "Uncommon" for card in daily_cards)
    assert all(card.findChild(QLabel, "supplyCardRarity").text() == "Uncommon" for card in freight_daily_cards)
    assert all(card.findChild(QLabel, "supplyCardRarity").text() == "Uncommon" for card in machine_daily_cards)
    assert all(card.findChild(QPushButton, "buyDailySupplyButton") is not None for card in daily_cards)
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton") is not None for card in freight_daily_cards)
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton") is not None for card in machine_daily_cards)
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    assert not type_filter.isVisible()
    assert not supply_view.findChild(QComboBox, "supplyMkFilter").isVisible()
    assert not supply_view.findChild(QComboBox, "supplySortSelect").isVisible()
    assert supply_view.findChildren(QPushButton, "supplyFilterChip")
    assert supply_view.findChild(QPushButton, "supplyMachineSelector") is not None
    assert supply_view.findChild(QPushButton, "supplySortSelector") is not None
    type_filter.setCurrentText("Machine")
    QApplication.processEvents()
    extractor = next(card for card in _visible_common_supply_cards(supply_view) if card.findChild(QLabel, "supplyCardName").text() == "Extractor MK I")
    assert extractor.findChild(QLabel, "supplyCardMk").text() == "MK 1"
    assert extractor.findChild(QLabel, "supplyCardBonus").text() == "+0.0%"
    assert "Output" in extractor.findChild(QLabel, "supplyCardOutput").text()
    assert "Power Demand" in extractor.findChild(QLabel, "supplyCardPower").text()
    assert extractor.findChild(QLabel, "supplyCardPrice").text().startswith("$")
    type_filter.setCurrentText("Freight")
    QApplication.processEvents()
    truck = next(card for card in _visible_common_supply_cards(supply_view) if card.findChild(QLabel, "supplyCardName").text() == "Freight Truck · Class I")
    assert truck.findChild(QLabel, "supplyCardMk").text() == "Class I"
    assert truck.findChild(QLabel, "supplyCardBonus").text() == "+0.0%"
    assert "Transport Capacity" in truck.findChild(QLabel, "supplyCardOutput").text()
    assert "Transport Time" in truck.findChild(QLabel, "supplyCardPower").text()
    assert truck.findChild(ResourceIconWidget, "supplyCardIcon").accent_key == "truck"
    common_scroll = supply_view.findChild(QScrollArea, "commonSupplyScroll")
    assert common_scroll is not None
    assert common_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_industrial_supply_section_switching_uses_one_active_page() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None

    stack = supply_view.findChild(QStackedWidget, "supplySectionStack")
    section_buttons = supply_view.findChildren(QPushButton, "supplySectionButton")
    assert stack is not None

    section_buttons[1].click()
    assert stack.currentWidget().objectName() == "supplyCommonPage"
    assert section_buttons[1].property("active") is True
    assert section_buttons[0].property("active") is False


def test_industrial_supply_redesign_previews_render_all_sections() -> None:
    _app()
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()

    previews = (
        (0, "industrial_supply_daily_supply_preview.png"),
        (1, "industrial_supply_common_supply_preview.png"),
    )
    for section_index, filename in previews:
        supply_view._show_section(section_index)
        QApplication.processEvents()
        assert supply_view.grab().toImage().save(str(artifacts / filename))

    supply_view._show_section(0)
    QApplication.processEvents()
    for object_name, filename in (
        ("supplyDailyRecipeSection", "industrial_supply_daily_recipes_preview.png"),
        ("supplyDailyFreightSection", "industrial_supply_daily_freight_preview.png"),
        ("supplyDailyMachineSection", "industrial_supply_daily_machines_preview.png"),
    ):
        section = supply_view.findChild(QFrame, object_name)
        assert section is not None
        assert section.grab().toImage().save(str(artifacts / filename))

    supply_view._show_section(1)
    QApplication.processEvents()
    supply_card = next(card for card in _visible_common_supply_cards(supply_view) if isinstance(card, SupplyOfferCardFrame))
    right = supply_card.grab().toImage()
    inventory_view = window.findChild(InventoryView)
    assert inventory_view is not None
    tabs.setCurrentWidget(inventory_view)
    QApplication.processEvents()
    inventory_card = inventory_view.findChild(QFrame, "inventoryCard")
    assert inventory_card is not None
    left = inventory_card.grab().toImage()
    comparison = QImage(left.width() + right.width() + 32, max(left.height(), right.height()), QImage.Format.Format_ARGB32)
    comparison.fill(QColor("#101414"))
    painter = QPainter(comparison)
    painter.drawImage(0, 0, left)
    painter.drawImage(left.width() + 32, 0, right)
    painter.end()
    assert comparison.save(str(artifacts / "industrial_supply_inventory_card_comparison_preview.png"))

    tabs.setCurrentWidget(supply_view)
    supply_view._show_section(0)
    supply_view._bus.dispatch(AddCash(20_000))
    supply_view.refresh()
    _daily_machine_supply_cards(supply_view)[0].findChild(QPushButton, "buyDailyMachineSupplyButton").click()
    QApplication.processEvents()
    assert supply_view.grab().toImage().save(str(artifacts / "industrial_supply_daily_supply_selected_preview.png"))

    window.resize(980, 760)
    supply_view._show_section(1)
    QApplication.processEvents()
    assert supply_view.minimumSizeHint().width() <= 980
    assert supply_view.grab().toImage().save(str(artifacts / "industrial_supply_common_filter_responsive_preview.png"))


def test_buying_daily_freight_card_does_not_create_visible_top_level_widgets() -> None:
    _app()
    window = MainWindow()
    window.setObjectName("mainWindow")
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    supply_view._state.cash.add(100_000)
    supply_view._show_section(1)
    supply_view.refresh()
    QApplication.processEvents()
    before = _visible_top_level_signature()

    freight_card = next(
        card
        for card in supply_view.findChildren(QFrame, "dailyFreightSupplyCard")
        if card.findChild(QPushButton, "buyDailyFreightSupplyButton").isEnabled()
    )
    definition_id = freight_card.property("definitionId")
    freight_card.findChild(QPushButton, "buyDailyFreightSupplyButton").click()
    for _ in range(3):
        QApplication.processEvents()

    assert _visible_top_level_signature() == before
    assert any(card.definition_id == definition_id for card in supply_view._state.cards.values())
    assert supply_view.findChild(QFrame, "dailyFreightSupplyCard") is not None


def test_industrial_supply_storefront_has_no_detail_overlay_and_no_black_child_boxes() -> None:
    _app()
    window = MainWindow()
    window.show()
    QApplication.processEvents()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()

    common_card = next(iter(_common_supply_cards_by_name(supply_view).values()))
    QTest.mouseClick(common_card, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert supply_view.findChild(QFrame, "supplyDetailOverlay") is None

    for selector in (
        "QFrame#supplyCardStats",
        "QFrame#supplyCardIconHost",
        "QFrame#supplyCardTitleRow",
        "QLabel#supplyStoreTitle",
        "QLabel#supplyStoreSubtitle",
        "QLabel#supplySectionTitle",
        "QLabel#supplySectionSubtitle",
        "QLabel#supplyDailyStatus",
        "QLabel#supplyFreightDailyStatus",
        "QLabel#supplyCommonStatus",
        "QLabel#supplyCardName",
        "QLabel#supplyCardMk",
        "QLabel#supplyCardFunction",
        "QLabel#supplyCardRarity",
        "QLabel#supplyCardBonus",
        "QLabel#supplyCardPrice",
    ):
        style = _style_block(selector)
        assert "background: transparent" in style
        assert "#000" not in style
        assert "black" not in style.lower()


def test_common_supply_grid_has_stable_geometry_without_overlap_or_horizontal_scroll() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    window.show()
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    type_filter.setCurrentText("Recipe")
    QApplication.processEvents()
    QApplication.processEvents()
    _flush_deferred_deletes()

    scroll = supply_view.findChild(QScrollArea, "commonSupplyScroll")
    assert scroll is not None
    cards = supply_view._common_card_pool
    assert 0 < len(cards) < len(supply_view._common_display_data)
    assert supply_view._common_grid_columns_used >= 5
    assert supply_view._common_grid_rows_used > 1
    assert scroll.horizontalScrollBar().maximum() == 0
    assert scroll.verticalScrollBar().maximum() > 0
    assert supply_view._common_grid_container.minimumHeight() > scroll.viewport().height()

    positions = set()
    for card, data_index in supply_view._common_card_bindings.items():
        row = data_index // supply_view._common_grid_columns_used
        column = data_index % supply_view._common_grid_columns_used
        assert (row, column) not in positions
        positions.add((row, column))

    visible_cards = _visible_common_supply_cards(supply_view)
    assert all(card is not None for card in visible_cards)
    assert all(card.height() > 200 for card in visible_cards)
    assert all(card.width() > 150 for card in visible_cards)
    assert len(visible_cards) <= 50
    for index, card in enumerate(visible_cards):
        for other in visible_cards[index + 1:]:
            assert not card.geometry().intersects(other.geometry())
        assert isinstance(card, SupplyOfferCardFrame)
        assert card.findChild(QFrame, "supplyCardIconHost") is None
        assert card.findChild(QFrame, "supplyCardHeader") is None
        assert card.findChild(ResourceIconWidget, "supplyCardIcon") is not None
        price = card.findChild(QLabel, "supplyCardPrice")
        button = card.findChild(QPushButton, "buyCommonSupplyButton")
        assert price is not None
        assert button is not None
        assert price.geometry().top() >= card.height() - 42
        assert button.geometry().top() >= card.height() - 42
        assert price.geometry().right() < button.geometry().left()
        if card.property("cardKind") == "recipe":
            assert "Recipe Inputs" not in card.findChild(QLabel, "supplyCardOutput").text()
            assert "Recipe Inputs" not in card.findChild(QLabel, "supplyCardPower").text()
            assert card.findChild(QLabel, "supplyCardPower").isHidden()
    before_pool_size = len(supply_view._common_card_pool)
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    QApplication.processEvents()
    QApplication.processEvents()
    supply_view._update_common_visible_cards()
    after_pool_size = len(supply_view._common_card_pool)
    assert after_pool_size == before_pool_size
    assert supply_view._common_performance["pool_size"] == before_pool_size


def test_common_supply_title_region_renders_two_lines_without_clipping_after_rebind() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    type_filter.setCurrentText("Recipe")
    QApplication.processEvents()

    long_index = next(
        index
        for index, item in enumerate(supply_view._filtered_common_data)
        if item.name in {
            "Advanced Industrial Robot Recipe",
            "Advanced Medical Equipment Recipe",
            "Advanced Protective Equipment Recipe",
            "Advanced Semiconductor Equipment Recipe",
        }
    )
    short_index = next(
        index
        for index, item in enumerate(supply_view._filtered_common_data)
        if len(item.name.split()) <= 3 and index != long_index
    )
    card = _visible_common_supply_cards(supply_view)[0]
    pool_size = len(supply_view._common_card_pool)

    for data_index in (long_index, short_index, long_index):
        supply_view._bind_common_card_widget(card, data_index)
        card.show()
        QApplication.processEvents()
        title = card.findChild(QLabel, "supplyCardName")
        rarity = card.findChild(QLabel, "supplyCardRarity")
        mk = card.findChild(QLabel, "supplyCardMk")
        rarity_line = card.findChild(QFrame, "supplyRarityLine")
        assert title is not None
        assert rarity is not None
        assert mk is not None
        assert rarity_line is not None
        assert isinstance(card, SupplyOfferCardFrame)
        assert card.objectName() == "commonSupplyCard"
        assert title.property("displayText")
        assert "MK" not in str(title.property("displayText"))
        assert "·" not in mk.text()
        assert rarity.text() in {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
        assert card.width() == COMMON_SUPPLY_CARD_WIDTH
        assert card.height() == COMMON_SUPPLY_CARD_HEIGHT

    assert len(supply_view._common_card_pool) == pool_size


def test_common_supply_header_keeps_title_mk_and_divider_separated() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    solar_index = next(
        index
        for index, item in enumerate(supply_view._filtered_common_data)
        if item.name == "Solar Array MK I"
    )
    card = supply_view._create_common_card_widget()
    card._supply_data = None
    supply_view._bind_common_card_widget(card, solar_index)
    card.show()
    QApplication.processEvents()

    title = card.findChild(QLabel, "supplyCardName")
    mk = card.findChild(QLabel, "supplyCardMk")
    rarity = card.findChild(QLabel, "supplyCardRarity")
    rarity_line = card.findChild(QFrame, "supplyRarityLine")
    assert title is not None
    assert mk is not None
    assert rarity is not None
    assert rarity_line is not None
    assert title.text() == "Solar Array MK I"
    assert title.property("displayText") == "SOLAR ARRAY"
    assert mk.text() == "MK 1"
    assert isinstance(card, SupplyOfferCardFrame)
    assert card.objectName() == "commonSupplyCard"
    assert card.findChild(QFrame, "supplyCardHeader") is None
    assert card.findChild(QFrame, "supplyCardTitleRow") is None
    assert card.findChild(QFrame, "supplyCardIconHost") is None
    assert "draw_machine_card_prototype" in inspect.getsource(SupplyOfferCardFrame.paintEvent)


def test_supply_cards_use_integrated_background_and_unclipped_common_rarity() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()

    common_style = _style_block("QFrame#commonSupplyCard")
    common_hover_style = _style_block("QFrame#commonSupplyCard:hover")
    daily_style = _style_block("QFrame#dailySupplyCard, QFrame#dailyFreightSupplyCard, QFrame#dailyMachineSupplyCard")
    header_style = _style_block("QFrame#supplyCardHeader")
    title_row_style = _style_block("QFrame#supplyCardTitleRow")
    assert "background: transparent" in common_style
    assert "border: 0" in common_style
    assert "background: transparent" in common_hover_style
    assert "background: transparent" in daily_style
    assert "background: transparent" in header_style
    assert "background: transparent" in title_row_style
    assert "draw_machine_card_prototype" in inspect.getsource(SupplyOfferCardFrame.paintEvent)
    assert "rgba(24, 33, 37" not in common_style
    assert "rgba(24, 33, 37" not in title_row_style
    assert "rgba(28, 39, 43" not in common_hover_style

    common_card = next(
        card
        for card in _visible_common_supply_cards(supply_view)
        if card.findChild(QLabel, "supplyCardRarity").text() == "Common"
    )
    assert isinstance(common_card, SupplyOfferCardFrame)
    assert common_card.objectName() == "commonSupplyCard"
    assert common_card.styleSheet() == ""
    assert common_card.autoFillBackground() is False
    assert common_card.findChild(QFrame, "supplyCardHeader") is None
    assert common_card.findChild(QFrame, "supplyCardTitleRow") is None
    assert common_card.findChild(QFrame, "supplyCardIconHost") is None
    assert common_card.findChild(QFrame, "supplyCardStats") is None
    rarity = common_card.findChild(QLabel, "supplyCardRarity")
    assert rarity is not None
    assert rarity.text() == "Common"


def test_common_supply_recipe_hover_shows_full_details_and_stays_embedded() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    type_filter.setCurrentText("Recipe")
    QApplication.processEvents()

    recipe_card = next(card for card in _visible_common_supply_cards(supply_view) if card.property("cardKind") == "recipe")
    data = recipe_card._supply_data
    assert data.definition.input_resources
    first_input = next(iter(data.definition.input_resources)).replace("_", " ").title()
    assert "Recipe Inputs" not in recipe_card.findChild(QLabel, "supplyCardOutput").text()
    assert recipe_card.findChild(QLabel, "supplyCardPower").isHidden()

    QApplication.sendEvent(recipe_card, QEvent(QEvent.Type.Enter))
    assert supply_view.findChild(QFrame, "supplyCardHoverInfo") is None
    QTest.qWait(330)
    QApplication.processEvents()

    hover = supply_view.findChild(QFrame, "supplyCardHoverInfo")
    assert hover is not None
    assert not hover.isHidden()
    assert hover.parent() is supply_view
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Window)
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.geometry().left() >= 0
    assert hover.geometry().right() <= supply_view.width()
    assert hover.geometry().top() >= 0
    assert hover.geometry().bottom() <= supply_view.height()
    labels = [label.text() for label in hover.findChildren(QLabel, "cardHoverLabel")]
    values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert "INPUTS" in labels
    assert "OUTPUTS" in labels
    assert any(first_input in value for value in values)
    assert any(data.name in label.text() for label in hover.findChildren(QLabel, "cardHoverTitle"))

    QApplication.sendEvent(recipe_card, QEvent(QEvent.Type.Leave))
    QApplication.processEvents()
    assert hover.isHidden()


def test_common_supply_hover_tracks_recycled_card_binding() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    supply_view.findChild(QComboBox, "supplyTypeFilter").setCurrentText("Recipe")
    QApplication.processEvents()

    scroll = supply_view.findChild(QScrollArea, "commonSupplyScroll")
    assert scroll is not None
    card = _visible_common_supply_cards(supply_view)[0]
    first_name = card._supply_data.name
    QApplication.sendEvent(card, QEvent(QEvent.Type.Enter))
    QTest.qWait(330)
    QApplication.processEvents()
    hover = supply_view.findChild(QFrame, "supplyCardHoverInfo")
    assert hover is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == first_name

    supply_view._bind_common_card_widget(card, len(supply_view._filtered_common_data) - 1)
    card.show()
    rebound_name = card._supply_data.name
    assert rebound_name != first_name
    assert not card.isHidden()
    supply_view._hide_detail_overlay()
    supply_view._hover_card = card
    supply_view._show_common_hover_for_current_card()

    assert supply_view.findChild(QFrame, "supplyCardHoverInfo") is hover
    assert len(supply_view.findChildren(QFrame, "supplyCardHoverInfo")) == 1
    assert not hover.isHidden()
    assert hover.current_title == rebound_name
    assert hover.details_signature[0] == card._supply_data.offer_id
    assert len(supply_view._common_card_pool) < len(supply_view._common_display_data)


def test_common_supply_card_click_does_not_open_detail_overlay_and_buy_refresh_hover_are_stable() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    factory = window.findChild(FactoryView)
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget)
    assert factory is not None
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    supply_view.findChild(QComboBox, "supplyTypeFilter").setCurrentText("Machine")
    QApplication.processEvents()
    supply_view._bus.dispatch(AddCash(50_000))
    offer = supply_view._filtered_common_data[0].offer
    existing = create_card_instance(
        "existing-common-supply-card",
        offer.definition_id,
        offer.card_kind,
        offer.rarity,
        bonus_tenths=offer.bonus_tenths,
    )
    supply_view._bus.dispatch(AddCard(existing))
    supply_view.refresh()
    QApplication.processEvents()

    card = _visible_common_supply_cards(supply_view)[0]
    owned_before = supply_view._owned_count(card._supply_data.offer)
    QTest.mouseClick(card, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert supply_view.findChild(QFrame, "supplyDetailOverlay") is None

    QApplication.sendEvent(card, QEvent(QEvent.Type.Enter))
    QTest.qWait(330)
    QApplication.processEvents()
    hover = supply_view.findChild(QFrame, "supplyCardHoverInfo")
    assert hover is not None
    assert not hover.isHidden()
    assert any(label.text() == "OWNED" for label in hover.findChildren(QLabel, "cardHoverLabel"))
    QApplication.sendEvent(card, QEvent(QEvent.Type.Leave))
    QApplication.processEvents()

    card.findChild(QPushButton, "buyCommonSupplyButton").click()
    QApplication.processEvents()
    supply_view.refresh()
    QApplication.processEvents()
    rebound = _visible_common_supply_cards(supply_view)[0]
    assert supply_view._owned_count(rebound._supply_data.offer) >= owned_before + 1
    for _ in range(3):
        factory._simulation.advance_time(factory._state, 1.0)
        supply_view.refresh()
        QApplication.processEvents()
        supply_view._show_common_hover_for_current_card()
    assert supply_view.findChild(QFrame, "supplyDetailOverlay") is None


def test_common_supply_filter_rebuilds_single_grid_without_duplicates() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    search = supply_view.findChild(QLineEdit, "supplySearch")
    assert search is not None
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    type_filter.setCurrentText("Machine")
    QApplication.processEvents()

    before_apply_count = supply_view._common_filter_apply_count
    search.setText("processor mk i")
    assert supply_view._common_filter_apply_count == before_apply_count
    QTest.qWait(220)
    QApplication.processEvents()
    _flush_deferred_deletes()
    assert len(supply_view._filtered_common_data) == 1
    assert supply_view._filtered_common_data[0].name == "Processor MK I"
    filtered_cards = _visible_common_supply_cards(supply_view)
    assert len(filtered_cards) == 1
    assert filtered_cards[0].findChild(QLabel, "supplyCardName").text() == "Processor MK I"

    search.setText("")
    QTest.qWait(220)
    QApplication.processEvents()
    type_filter.setCurrentText("Recipe")
    QApplication.processEvents()
    _flush_deferred_deletes()
    visible_cards = _visible_common_supply_cards(supply_view)
    definition_ids = [card.property("definitionId") for card in visible_cards]
    assert len(definition_ids) == len(set(definition_ids))
    assert len(visible_cards) < len(supply_view._filtered_common_data)
    assert len(supply_view._filtered_common_data) < len(supply_view._common_display_data)
    assert len(supply_view._common_card_pool) < len(supply_view._common_display_data)


def test_common_supply_search_type_mk_filter_and_sort() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None

    search = supply_view.findChild(QLineEdit, "supplySearch")
    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    mk_filter = supply_view.findChild(QComboBox, "supplyMkFilter")
    sort = supply_view.findChild(QComboBox, "supplySortSelect")
    assert search is not None
    assert type_filter is not None
    assert mk_filter is not None
    assert sort is not None
    assert search.placeholderText() == "Search cards..."
    assert [sort.itemText(index) for index in range(sort.count())] == ["Name", "Price"]
    assert "All" not in [type_filter.itemText(index) for index in range(type_filter.count())]

    type_filter.setCurrentText("Machine")
    QApplication.processEvents()
    search.setText("processor mk i")
    QTest.qWait(220)
    QApplication.processEvents()
    assert [item.name for item in supply_view._filtered_common_data] == ["Processor MK I"]

    search.setText("")
    QTest.qWait(220)
    QApplication.processEvents()
    type_filter.setCurrentText("Recipe")
    QApplication.processEvents()
    recipe_names = [item.name for item in supply_view._filtered_common_data]
    assert recipe_names
    assert all(item.definition.card_kind.value.title() == "Recipe" for item in supply_view._filtered_common_data)
    secondary_values = [mk_filter.itemText(index) for index in range(mk_filter.count())]
    assert "All" in secondary_values
    assert {"Processor", "Fabricator", "Assembler"} & set(secondary_values)

    type_filter.setCurrentText("Machine")
    QApplication.processEvents()
    mk_filter.setCurrentText("MK 2")
    QApplication.processEvents()
    assert [item.name for item in supply_view._filtered_common_data] == ["Extractor MK II"]

    mk_filter.setCurrentText("All")
    sort.setCurrentText("Price")
    prices = [
        item.offer.price_cash
        for item in supply_view._filtered_common_data
    ]
    assert prices == sorted(prices)


def test_common_supply_energy_filter_shows_reliable_solar_card() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget)
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()

    type_filter = supply_view.findChild(QComboBox, "supplyTypeFilter")
    assert type_filter is not None
    assert "Energy" in [type_filter.itemText(index) for index in range(type_filter.count())]
    type_filter.setCurrentText("Energy")
    QApplication.processEvents()

    cards = _visible_common_supply_cards(supply_view)
    assert {item.definition_id for item in supply_view._filtered_common_data} == {
        "energy.solar_array.mk1",
        "energy.wind_turbine.mk1",
        "energy.coal_power_plant.mk1",
        "energy.gas_power_plant.mk1",
        "energy.nuclear_power_plant.mk1",
    }
    assert cards
    solar = next(card for card in cards if card.findChild(QLabel, "supplyCardName").text() == "Solar Array MK I")
    assert solar.findChild(QLabel, "supplyCardOutput").text() == "Generation 20 MW"
    assert any(card.findChild(QLabel, "supplyCardPower").text().startswith("Fuel Coal") for card in cards)
    assert solar.findChild(QPushButton, "buyCommonSupplyButton").isEnabled() is True


def test_daily_supply_purchase_marks_purchased_and_locks_other_choices() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    supply_view._bus.dispatch(AddCash(10_000))
    supply_view.refresh()

    daily_cards = _daily_supply_cards(supply_view)
    chosen_offer_id = daily_cards[0].property("offerId")
    daily_cards[0].findChild(QPushButton, "buyDailySupplyButton").click()

    daily_cards = _daily_supply_cards(supply_view)
    chosen = next(card for card in daily_cards if card.property("offerId") == chosen_offer_id)
    locked = [card for card in daily_cards if card.property("offerId") != chosen_offer_id]

    assert chosen.property("state") == "purchased"
    assert chosen.findChild(QPushButton, "buyDailySupplyButton").text() == "PURCHASED"
    assert not chosen.findChild(QPushButton, "buyDailySupplyButton").isEnabled()
    assert all(card.property("state") == "locked" for card in locked)
    assert all(card.findChild(QPushButton, "buyDailySupplyButton").text() == "LOCKED UNTIL RESET" for card in locked)
    assert all(not card.findChild(QPushButton, "buyDailySupplyButton").isEnabled() for card in locked)
    assert supply_view._state.supply.daily_purchased_offer_id == chosen_offer_id


def test_daily_freight_supply_purchase_marks_purchased_and_stays_independent_from_daily_supply() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    supply_view._bus.dispatch(AddCash(20_000))
    supply_view.refresh()

    daily_offer_id = _daily_supply_cards(supply_view)[0].property("offerId")
    freight_cards = _daily_freight_supply_cards(supply_view)
    chosen_offer_id = freight_cards[0].property("offerId")
    freight_cards[0].findChild(QPushButton, "buyDailyFreightSupplyButton").click()

    freight_cards = _daily_freight_supply_cards(supply_view)
    chosen = next(card for card in freight_cards if card.property("offerId") == chosen_offer_id)
    locked = [card for card in freight_cards if card.property("offerId") != chosen_offer_id]

    assert chosen.property("state") == "purchased"
    assert chosen.findChild(QPushButton, "buyDailyFreightSupplyButton").text() == "PURCHASED"
    assert not chosen.findChild(QPushButton, "buyDailyFreightSupplyButton").isEnabled()
    assert all(card.property("state") == "locked" for card in locked)
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton").text() == "LOCKED UNTIL RESET" for card in locked)
    assert all(not card.findChild(QPushButton, "buyDailyFreightSupplyButton").isEnabled() for card in locked)
    assert supply_view._state.supply.freight_daily_purchased_offer_id == chosen_offer_id

    daily_cards = _daily_supply_cards(supply_view)
    daily_card = next(card for card in daily_cards if card.property("offerId") == daily_offer_id)
    assert daily_card.property("state") == "available"
    assert daily_card.findChild(QPushButton, "buyDailySupplyButton").isEnabled()
    daily_card.findChild(QPushButton, "buyDailySupplyButton").click()
    assert supply_view._state.supply.daily_purchased_offer_id == daily_offer_id


def test_daily_machine_supply_purchase_is_independent_from_recipe_and_freight() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    supply_view._bus.dispatch(AddCash(40_000))
    supply_view.refresh()

    recipe_offer_id = _daily_supply_cards(supply_view)[0].property("offerId")
    freight_offer_id = _daily_freight_supply_cards(supply_view)[0].property("offerId")
    machine_cards = _daily_machine_supply_cards(supply_view)
    chosen_offer_id = machine_cards[0].property("offerId")
    machine_cards[0].findChild(QPushButton, "buyDailyMachineSupplyButton").click()

    machine_cards = _daily_machine_supply_cards(supply_view)
    chosen = next(card for card in machine_cards if card.property("offerId") == chosen_offer_id)
    locked = [card for card in machine_cards if card.property("offerId") != chosen_offer_id]

    assert chosen.property("state") == "purchased"
    assert chosen.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "PURCHASED"
    assert all(card.property("state") == "locked" for card in locked)
    assert supply_view._state.supply.machine_daily_purchased_offer_id == chosen_offer_id

    recipe_card = next(card for card in _daily_supply_cards(supply_view) if card.property("offerId") == recipe_offer_id)
    freight_card = next(card for card in _daily_freight_supply_cards(supply_view) if card.property("offerId") == freight_offer_id)
    assert recipe_card.property("state") == "available"
    assert freight_card.property("state") == "available"
    recipe_card.findChild(QPushButton, "buyDailySupplyButton").click()
    freight_card = next(card for card in _daily_freight_supply_cards(supply_view) if card.property("offerId") == freight_offer_id)
    freight_card.findChild(QPushButton, "buyDailyFreightSupplyButton").click()
    assert supply_view._state.supply.daily_purchased_offer_id == recipe_offer_id
    assert supply_view._state.supply.freight_daily_purchased_offer_id == freight_offer_id


def test_daily_supply_reset_restores_new_available_choice_cards() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    supply_view._bus.dispatch(AddCash(10_000))
    supply_view.refresh()

    initial_ids = [card.property("offerId") for card in _daily_supply_cards(supply_view)]
    initial_freight_ids = [card.property("offerId") for card in _daily_freight_supply_cards(supply_view)]
    initial_machine_ids = [card.property("offerId") for card in _daily_machine_supply_cards(supply_view)]
    _daily_supply_cards(supply_view)[0].findChild(QPushButton, "buyDailySupplyButton").click()
    _daily_freight_supply_cards(supply_view)[0].findChild(QPushButton, "buyDailyFreightSupplyButton").click()
    _daily_machine_supply_cards(supply_view)[0].findChild(QPushButton, "buyDailyMachineSupplyButton").click()

    supply_view._state.market.elapsed_seconds = 24 * 60 * 60
    supply_view.refresh()

    reset_cards = _daily_supply_cards(supply_view)
    reset_ids = [card.property("offerId") for card in reset_cards]
    reset_freight_cards = _daily_freight_supply_cards(supply_view)
    reset_freight_ids = [card.property("offerId") for card in reset_freight_cards]
    reset_machine_cards = _daily_machine_supply_cards(supply_view)
    reset_machine_ids = [card.property("offerId") for card in reset_machine_cards]
    assert reset_ids != initial_ids
    assert all(card.property("state") == "available" for card in reset_cards)
    assert all(card.findChild(QPushButton, "buyDailySupplyButton").text() == "CHOOSE" for card in reset_cards)
    assert reset_freight_ids != initial_freight_ids
    assert all(card.property("state") == "available" for card in reset_freight_cards)
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton").text() == "CHOOSE" for card in reset_freight_cards)
    assert reset_machine_ids != initial_machine_ids
    assert all(card.property("state") == "available" for card in reset_machine_cards)
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "CHOOSE" for card in reset_machine_cards)


def test_packs_tab_shows_unopened_packs_and_open_results() -> None:
    _app()
    window = MainWindow()
    window.resize(1400, 900)
    window.show()
    packs_view = window.findChild(PacksView)
    dev = window.findChild(DevToolsView)
    tabs = window.findChild(QTabWidget)
    assert packs_view is not None
    assert dev is not None
    assert tabs is not None
    tabs.setCurrentWidget(packs_view)

    dev._grant_pack("full")
    dev._grant_pack("full")
    dev._grant_pack("full")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    assert packs_view.grab().toImage().save(str(artifacts / "packs_redesign_preview.png"))
    assert packs_view.grab().toImage().save(str(artifacts / "packs_full_pack_selector_preview.png"))
    stack = packs_view.findChild(QStackedWidget, "packsStack")
    tiles = _booster_pack_tiles(packs_view)
    assert stack is not None
    assert stack.currentIndex() == 0
    assert packs_view.findChild(QFrame, "packsHeader") is not None
    assert packs_view.findChild(QLabel, "packsHeaderTitle").text() == "PACKS"
    assert packs_view.findChild(QLabel, "packsHeaderSubtitle").text() == "OPEN PACKS · CHOOSE CATEGORY · EXPAND YOUR COLLECTION"
    assert [label.text() for label in packs_view.findChildren(QLabel, "packsHeaderMetricValue")] == ["3", "3"]
    assert packs_view.findChild(QFrame, "packsUnopenedHeader") is not None
    assert packs_view.findChild(QLabel, "packsUnopenedCount").text() == "3 unopened"
    assert packs_view.findChild(QScrollArea, "boosterPackScroll") is not None
    assert packs_view.findChild(QWidget, "boosterPackGrid") is not None
    assert packs_view.findChild(QTableWidget, "packsTable") is None
    assert len(tiles) == 3
    tile = tiles[0]
    assert isinstance(tile, BoosterPackTileFrame)
    assert tile.height() > tile.width()
    assert tile.width() == 220
    assert tile.height() == 340
    assert tile.findChild(QFrame, "boosterPackArt") is None
    assert tile.findChild(ResourceIconWidget, "boosterPackIcon") is not None
    assert tile.findChild(QLabel, "boosterPackName").text() == "Full Pack"
    assert tile.findChild(QLabel, "boosterPackType").text() == "Full Pack / Category Choice"
    assert tile.findChild(QLabel, "boosterPackCardCount").text() == "6 Cards"
    assert tile.findChild(QLabel, "boosterPackArtLabel") is None
    assert tile.findChild(QLabel, "boosterPackQuantity") is None
    assert tile.findChild(QLabel, "boosterPackSource").isHidden()
    assert len({tile.property("packId") for tile in tiles}) == 3
    category = tile.findChild(QComboBox, "packCategorySelect")
    assert category is not None
    assert category.isEnabled()
    assert category.isHidden()
    selector = tile.findChild(QPushButton, "packCategorySelector")
    assert selector is not None
    assert selector.isVisible()
    open_button = tile.findChild(QPushButton, "openPackButton")
    assert open_button is not None
    assert tile.findChild(QLabel, "boosterPackCategoryLabel").text() == "CATEGORY"
    assert "Freight" in [category.itemText(index) for index in range(category.count())]
    category.setCurrentText("Freight")
    assert selector.text().startswith("FREIGHT")
    selector.click()
    QApplication.processEvents()
    flyout = packs_view._grid_container.findChild(QFrame, "packCategoryFlyout")
    assert flyout is not None
    assert flyout.isVisible()
    assert not flyout.isWindow()
    assert flyout.parentWidget() is packs_view._grid_container
    assert not flyout.geometry().intersects(selector.geometry().translated(tile.pos()))
    assert not flyout.geometry().intersects(open_button.geometry().translated(tile.pos()))
    options = flyout.findChildren(QPushButton, "packCategoryOption")
    assert len(options) == category.count()
    assert all(option.height() >= 22 for option in options)
    assert packs_view.grab().toImage().save(str(artifacts / "packs_full_pack_category_flyout_preview.png"))

    open_button.click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    assert stack.currentIndex() == 1
    assert packs_view.grab().toImage().save(str(artifacts / "packs_open_results_preview.png"))
    assert len(_booster_pack_tiles(packs_view)) == 2
    assert all(tile.findChild(QLabel, "boosterPackQuantity") is None for tile in _booster_pack_tiles(packs_view))
    assert "Last opened:" in packs_view.findChild(QLabel, "packResultsLabel").text()
    result_tiles = _pack_result_tiles(packs_view)
    assert len(result_tiles) == 6
    assert all(isinstance(tile, InventoryCardFrame) for tile in result_tiles)
    assert all(tile.width() == INVENTORY_CARD_WIDTH and tile.height() == INVENTORY_CARD_HEIGHT for tile in result_tiles)
    assert all(tile.objectName() == "inventoryCard" for tile in result_tiles)
    assert all(tile.findChild(QLabel, "inventoryCardMk").text() == "Class I" for tile in result_tiles)
    assert all(tile.findChild(QLabel, "inventoryCardStatus").text() == "Received" for tile in result_tiles)
    assert all(tile.findChild(ResourceIconWidget, "inventoryCardIcon") is not None for tile in result_tiles)
    assert {tile.findChild(QLabel, "inventoryCardFunction").text() for tile in result_tiles} <= {"TRUCK", "TRAIN", "SHIP", "AIRCRAFT"}
    assert result_tiles[0].geometry().height() < 340
    result_positions = [packs_view._result_grid.getItemPosition(index)[:2] for index in range(packs_view._result_grid.count())]
    assert result_positions[:3] == [(0, 0), (0, 1), (0, 2)]
    assert len(packs_view._state.packs.last_opened_cards) == 6
    assert len({card.card_id for card in packs_view._state.packs.last_opened_cards}) == 6
    assert all(card.card_id in packs_view._state.cards for card in packs_view._state.packs.last_opened_cards)
    assert all(card.card_kind is CardKind.FREIGHT for card in packs_view._state.packs.last_opened_cards)

    result_tiles[0].hovered.emit()
    QApplication.processEvents()
    hover = packs_view.findChild(QFrame, "packResultCardHoverInfo")
    assert hover is not None
    assert hover.isVisible()
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert hover.findChild(QLabel, "cardHoverTitle").text() == result_tiles[0].findChild(QLabel, "inventoryCardName").text()
    assert any(label.text() == "TRANSPORT CAPACITY" for label in hover.findChildren(QLabel, "cardHoverLabel"))
    result_tiles[1].hovered.emit()
    QApplication.processEvents()
    assert packs_view.findChild(QFrame, "packResultCardHoverInfo") is hover
    assert hover.findChild(QLabel, "cardHoverTitle").text() == result_tiles[1].findChild(QLabel, "inventoryCardName").text()
    result_tiles[1].unhovered.emit()
    QApplication.processEvents()
    assert not hover.isVisible()


def test_packs_gallery_renders_single_pack_as_one_card_without_quantity_badge() -> None:
    _app()
    window = MainWindow()
    window.resize(1100, 820)
    window.show()
    packs_view = window.findChild(PacksView)
    assert packs_view is not None

    grant_pack(packs_view._state, DAILY_MINI_PACK, "daily-contract")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    assert packs_view.grab().toImage().save(str(artifacts / "packs_daily_mini_preview.png"))

    tiles = _booster_pack_tiles(packs_view)
    assert packs_view.findChild(QLabel, "packsUnopenedCount").text() == "1 unopened"
    assert len(tiles) == 1
    assert tiles[0].property("packType") == DAILY_MINI_PACK
    assert isinstance(tiles[0], BoosterPackTileFrame)
    assert tiles[0].findChild(QLabel, "boosterPackQuantity") is None
    assert tiles[0].findChild(QComboBox, "packCategorySelect").isHidden()
    assert tiles[0].findChild(QLabel, "boosterPackCategoryLabel").isHidden()
    assert tiles[0].findChild(QLabel, "boosterPackCategoryInfo").text() == "Category: General"
    assert tiles[0].findChild(QLabel, "boosterPackCardCount").text() == "3 Cards"
    assert tiles[0].findChild(QLabel, "boosterPackArtLabel") is None
    assert tiles[0].findChild(QLabel, "boosterPackCategoryInfo").isHidden()
    assert tiles[0].findChild(QPushButton, "packCategorySelector").isHidden()

    existing_card_ids = set(packs_view._state.cards)
    tiles[0].findChild(QPushButton, "openPackButton").click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    result_tiles = _pack_result_tiles(packs_view)
    assert len(result_tiles) == 3
    assert all(isinstance(tile, InventoryCardFrame) for tile in result_tiles)
    assert all(tile.width() == INVENTORY_CARD_WIDTH and tile.height() == INVENTORY_CARD_HEIGHT for tile in result_tiles)
    assert all(tile.findChild(QLabel, "inventoryCardName").text() for tile in result_tiles)
    assert all(tile.findChild(QLabel, "inventoryCardRarity").text() for tile in result_tiles)
    assert all(tile.findChild(QFrame, "inventoryRarityLine") is not None for tile in result_tiles)
    assert all(tile.findChild(QLabel, "packOpenedCardName") is None for tile in result_tiles)
    new_card_ids = set(packs_view._state.cards) - existing_card_ids
    assert len(new_card_ids) == 3
    assert {card.card_id for card in packs_view._state.packs.last_opened_cards} == new_card_ids


def test_general_pack_runtime_opens_mixed_reward_types_and_ui_labels_match_cards() -> None:
    _app()
    window = MainWindow()
    window.resize(1200, 860)
    window.show()
    packs_view = window.findChild(PacksView)
    tabs = window.findChild(QTabWidget)
    assert packs_view is not None
    assert tabs is not None
    packs_view._state.rng_seed = 811
    tabs.setCurrentWidget(packs_view)

    for index in range(20):
        grant_pack(packs_view._state, FULL_PACK, f"general-runtime-{index}")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()

    opened_kind_counts: dict[CardKind, int] = {}
    for pack in tuple(packs_view._state.packs.unopened):
        packs_view._open_pack(pack.pack_id, "general")
        drain_qt_events(cycles=4)
        result_tiles = _pack_result_tiles(packs_view)
        assert len(result_tiles) == 6
        assert len(packs_view._state.packs.last_opened_cards) == 6
        for tile, card in zip(result_tiles, packs_view._state.packs.last_opened_cards, strict=True):
            definition = packs_view._definitions[card.definition_id]
            opened_kind_counts[card.card_kind] = opened_kind_counts.get(card.card_kind, 0) + 1
            assert card.card_id in packs_view._state.cards
            assert tile.property("definitionId") == card.definition_id
            assert tile.property("cardType") == packs_view._card_type_key(definition)
            function_text = tile.findChild(QLabel, "inventoryCardFunction").text()
            if card.card_kind is CardKind.ENERGY:
                assert function_text == "ENERGY"
            elif card.card_kind is CardKind.RECIPE:
                assert function_text.endswith(" RECIPE")
            elif card.card_kind is CardKind.FREIGHT:
                assert function_text in {"TRUCK", "TRAIN", "SHIP", "AIRCRAFT"}
            elif card.card_kind is CardKind.MACHINE:
                assert function_text in {"EXTRACTOR", "PROCESSOR", "FABRICATOR", "ASSEMBLER"}

    assert set(opened_kind_counts) == {CardKind.MACHINE, CardKind.ENERGY, CardKind.RECIPE, CardKind.FREIGHT}
    assert opened_kind_counts[CardKind.RECIPE] < sum(opened_kind_counts.values()) * 0.4


def test_packs_gallery_expands_identical_inventory_to_individual_cards() -> None:
    _app()
    window = MainWindow()
    window.resize(1500, 950)
    window.show()
    packs_view = window.findChild(PacksView)
    assert packs_view is not None

    for _ in range(3):
        grant_pack(packs_view._state, DAILY_MINI_PACK, "daily-contract")
        grant_pack(packs_view._state, FULL_PACK, "weekly-contract")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()

    tiles = _booster_pack_tiles(packs_view)
    assert packs_view.findChild(QLabel, "packsUnopenedCount").text() == "6 unopened"
    assert len(tiles) == 6
    assert [tile.property("packType") for tile in tiles].count(DAILY_MINI_PACK) == 3
    assert [tile.property("packType") for tile in tiles].count(FULL_PACK) == 3
    assert all(tile.findChild(QLabel, "boosterPackQuantity") is None for tile in tiles)

    daily_tile = next(tile for tile in tiles if tile.property("packType") == DAILY_MINI_PACK)
    daily_tile.findChild(QPushButton, "openPackButton").click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    assert len(packs_view._state.packs.unopened) == 5
    assert [pack.pack_type for pack in packs_view._state.packs.unopened].count(DAILY_MINI_PACK) == 2
    assert [pack.pack_type for pack in packs_view._state.packs.unopened].count(FULL_PACK) == 3
    assert len(_booster_pack_tiles(packs_view)) == 5


def test_packs_gallery_grid_handles_many_packs_and_resizes_cleanly() -> None:
    _app()
    window = MainWindow()
    window.resize(1500, 950)
    window.show()
    packs_view = window.findChild(PacksView)
    assert packs_view is not None
    tabs = window.findChild(QTabWidget)
    assert tabs is not None
    tabs.setCurrentWidget(packs_view)

    for index in range(30):
        grant_pack(packs_view._state, FULL_PACK if index % 2 else DAILY_MINI_PACK, f"test-source-{index}")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()

    scroll = packs_view.findChild(QScrollArea, "boosterPackScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBar().maximum() == 0
    assert packs_view._pack_grid_columns_used >= 4
    assert scroll.verticalScrollBar().maximum() > 0
    assert packs_view.findChild(QLabel, "packsUnopenedCount").text() == "30 unopened"

    tiles = _booster_pack_tiles(packs_view)
    assert len(tiles) == 30
    assert all(tile.width() == tiles[0].width() and tile.height() == tiles[0].height() for tile in tiles)
    grid_positions = set()
    for index in range(packs_view._grid.count()):
        row, column, row_span, column_span = packs_view._grid.getItemPosition(index)
        assert row_span == 1
        assert column_span == 1
        assert (row, column) not in grid_positions
        grid_positions.add((row, column))
    assert {(0, column) for column in range(packs_view._pack_grid_columns_used)} <= grid_positions

    daily_tile = next(tile for tile in tiles if tile.property("packType") == DAILY_MINI_PACK)
    assert daily_tile.findChild(QComboBox, "packCategorySelect").isHidden()
    assert daily_tile.findChild(QLabel, "boosterPackCategoryInfo").isHidden()
    assert daily_tile.findChild(QPushButton, "packCategorySelector").isHidden()
    full_tile = next(tile for tile in tiles if tile.property("packType") == FULL_PACK)
    assert full_tile.findChild(QComboBox, "packCategorySelect").isHidden()
    assert not full_tile.findChild(QPushButton, "packCategorySelector").isHidden()
    assert full_tile.findChild(QLabel, "boosterPackCategoryInfo").isHidden()
    assert full_tile.findChild(QLabel, "boosterPackCardCount").text() == "6 Cards"
    assert full_tile.findChild(QLabel, "boosterPackArtLabel") is None
    assert daily_tile.findChild(QPushButton, "openPackButton").geometry().top() == full_tile.findChild(QPushButton, "openPackButton").geometry().top()

    wide_columns = packs_view._pack_grid_columns_used
    scroll.setFixedWidth(760)
    QApplication.processEvents()
    packs_view._refresh_pack_grid()
    QApplication.processEvents()
    assert packs_view._pack_grid_columns_used < wide_columns
    assert scroll.horizontalScrollBar().maximum() == 0
    resized_positions = set()
    for index in range(packs_view._grid.count()):
        row, column, row_span, column_span = packs_view._grid.getItemPosition(index)
        assert row_span == 1
        assert column_span == 1
        assert (row, column) not in resized_positions
        resized_positions.add((row, column))


def test_packs_gallery_rebuilds_do_not_create_native_top_level_windows() -> None:
    _app()
    window = MainWindow()
    window.resize(1300, 900)
    window.show()
    packs_view = window.findChild(PacksView)
    tabs = window.findChild(QTabWidget)
    assert packs_view is not None
    assert tabs is not None

    for index in range(12):
        grant_pack(packs_view._state, FULL_PACK if index % 2 else DAILY_MINI_PACK, f"window-test-{index}")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()

    baseline = set(QApplication.topLevelWidgets())
    assert _visible_extra_top_levels(window) == []

    tabs.setCurrentWidget(packs_view)
    QApplication.processEvents()
    for _ in range(4):
        packs_view._refresh_pack_grid()
        QApplication.processEvents()
        packs_view.resize(720, 820)
        QApplication.processEvents()
        packs_view.resize(1300, 900)
        QApplication.processEvents()
    _flush_deferred_deletes()

    tiles = _booster_pack_tiles(packs_view)
    assert tiles
    assert all(not tile.isWindow() for tile in tiles)
    assert all(tile.parentWidget() is packs_view._grid_container for tile in tiles)
    category = next(tile.findChild(QComboBox, "packCategorySelect") for tile in tiles if tile.property("packType") == FULL_PACK)
    category.setCurrentText("Freight")
    QApplication.sendEvent(tiles[0], QEvent(QEvent.Type.Enter))
    QApplication.sendEvent(tiles[0], QEvent(QEvent.Type.Leave))
    QApplication.processEvents()

    assert _visible_extra_top_levels(window) == []
    assert all(
        not widget.isVisible()
        for widget in QApplication.topLevelWidgets()
        if widget not in baseline and widget is not window
    )
    window.close()
    QApplication.processEvents()
    _flush_deferred_deletes()
    assert not window.isVisible()
    assert _visible_extra_top_levels(window) == []


def test_pack_open_runtime_refresh_does_not_create_visible_top_level_widgets() -> None:
    _app()
    window = MainWindow()
    window.setObjectName("mainWindow")
    window.resize(1300, 900)
    window.show()
    drain_qt_events()
    packs_view = window.findChild(PacksView)
    tabs = window.findChild(QTabWidget)
    assert packs_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(packs_view)
    grant_pack(packs_view._state, FULL_PACK, "lifecycle-test")
    packs_view.refresh()
    drain_qt_events()
    tile = _booster_pack_tiles(packs_view)[0]
    category = tile.findChild(QComboBox, "packCategorySelect")
    assert category is not None
    category.setCurrentText("Freight")

    def open_pack() -> None:
        tile.findChild(QPushButton, "openPackButton").click()

    assert_no_visible_top_level_delta(open_pack, allowed=(window,), cycles=12)
    assert packs_view.findChild(QStackedWidget, "packsStack").currentIndex() == 1
    assert len(_pack_result_tiles(packs_view)) == 6
    assert all(not tile.isWindow() for tile in _pack_result_tiles(packs_view))
    window.close()
    drain_qt_events()


def test_dev_tools_can_advance_real_simulation_and_market_time() -> None:
    _app()
    window = MainWindow()
    dev = window.findChild(DevToolsView)
    assert dev is not None

    dev._advance_time(300)

    assert dev._state.tick == 1
    assert dev._state.market.market_tick == 1


def test_dev_tools_can_set_cash_fill_clear_resources_and_create_cards() -> None:
    _app()
    window = MainWindow()
    dev = window.findChild(DevToolsView)
    assert dev is not None

    dev._cash_amount.setValue(777)
    dev._set_cash()
    assert dev._state.cash.amount == 777
    dev._scrap_amount.setValue(33)
    dev._add_scrap()
    assert dev._state.scrap.amount == 33

    dev._resource_select.setCurrentIndex(0)
    dev._fill_resource()
    assert dev._state.resources["iron_ore"].amount == dev._state.resources["iron_ore"].capacity
    dev._clear_resource()
    assert dev._state.resources["iron_ore"].amount == 0

    starting_cards = len(dev._state.cards)
    dev._card_select.setCurrentText("Processor")
    dev._card_count.setValue(2)
    dev._create_cards()

    assert len(dev._state.cards) == starting_cards + 2


def test_dev_tools_can_create_targeted_rarity_bonus_cards() -> None:
    _app()
    window = MainWindow()
    dev = window.findChild(DevToolsView)
    assert dev is not None

    dev._card_select.setCurrentText("Extractor")
    dev._card_rarity.setCurrentText("Rare")
    dev._card_bonus_tenths.setValue(74)
    dev._create_cards()

    card = dev._state.cards[f"dev-card-{len(dev._state.cards):04d}"]
    assert card.rarity is Rarity.RARE
    assert card.output_bonus_tenths == 74
    assert card.power_bonus_tenths == 37
    assert card.is_tradeable_by_rarity is True


def test_dev_created_energy_card_can_be_selected_and_installed_from_hall_inventory() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    dev = window.findChild(DevToolsView)
    assert factory is not None
    assert dev is not None

    dev._card_select.setCurrentText("Solar Array")
    dev._card_count.setValue(1)
    dev._create_cards()

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Solar Array MK I")

    installed_id = factory._state.halls["hall-1"].slots[0].card_id
    assert installed_id is not None
    assert factory._state.cards[installed_id].definition_id == "energy.solar_array.mk1"
    assert any(stack.first_card.definition_id == "energy.solar_array.mk1" for stack in factory._state.inventory_card_stacks())


def test_hall_inventory_can_install_multiple_placeable_card_types() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    for slot_index, card_name in ((0, "Extractor MK I"), (1, "Solar Array MK I"), (2, "Processor MK I")):
        factory._on_slot_clicked(slot_index)
        _install_factory_card_from_selection(factory, card_name)

    installed_definitions = [
        factory._state.cards[factory._state.halls["hall-1"].slots[index].card_id].definition_id
        for index in range(3)
    ]
    assert installed_definitions == [
        "machine.extractor.mk1",
        "energy.solar_array.mk1",
        "machine.processor.mk1",
    ]


def test_factory_card_selection_view_filters_placeable_cards() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryView)
    assert factory is not None

    freight_card = create_card_instance("freight-test", "freight.truck.class1", CardKind.FREIGHT, Rarity.COMMON)
    rare_processor = create_card_instance("rare-processor", "machine.processor.mk1", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74)
    mk2_extractor = create_card_instance("mk2-extractor", "machine.extractor.mk2", CardKind.MACHINE, Rarity.UNCOMMON, bonus_tenths=20)
    factory._command_bus.dispatch(AddCard(freight_card))
    factory._command_bus.dispatch(AddCard(rare_processor))
    factory._command_bus.dispatch(AddCard(mk2_extractor))

    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory.findChild(QListWidget, "cardSelectionList") is None
    factory._on_slot_clicked(0)

    search = factory.findChild(QLineEdit, "cardSearchInput")
    type_filter = factory.findChild(QComboBox, "cardSelectionTypeFilter")
    mk_filter = factory.findChild(QComboBox, "cardSelectionMkFilter")
    rarity_filter = factory.findChild(QComboBox, "cardSelectionRarityFilter")
    assert search is not None
    assert type_filter is not None
    assert mk_filter is not None
    assert rarity_filter is not None
    assert factory.findChild(QFrame, "cardSelectionDrawer") is None
    assert factory.findChild(QListWidget, "cardSelectionList") is None
    scroll = factory.findChild(QScrollArea, "factoryCardSelectionScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert {type_filter.itemText(index) for index in range(type_filter.count())} >= {
        "All",
        "Energy",
        "Extractor",
        "Processor",
        "Fabricator",
        "Assembler",
    }
    assert all("Freight" not in tile.findChild(QLabel, "factoryCardSelectionTileName").text() for tile in _factory_selection_tiles(factory))

    search.setText("definitely no matching card")
    assert _factory_selection_tiles(factory) == []
    empty = factory.findChild(QLabel, "factoryCardSelectionEmpty")
    assert empty is not None
    assert empty.text() == "No compatible cards available"

    search.setText("solar")
    tiles = _factory_selection_tiles(factory)
    assert len(tiles) == 1
    assert tiles[0].findChild(QLabel, "factoryCardSelectionTileName").text() == "SOLAR ARRAY MK I"
    assert tiles[0].findChild(ResourceIconWidget, "resourceIcon") is not None

    search.setText("")
    type_filter.setCurrentText("Processor")
    tiles = _factory_selection_tiles(factory)
    assert len(tiles) == 2
    assert all(tile.findChild(QLabel, "factoryCardSelectionTileFunction").text() == "PROCESSOR" for tile in tiles)

    rarity_filter.setCurrentText("Rare")
    tiles = _factory_selection_tiles(factory)
    assert len(tiles) == 1
    assert tiles[0].property("cardId") == "rare-processor"

    rarity_filter.setCurrentText("All")
    type_filter.setCurrentText("Extractor")
    mk_filter.setCurrentText("MK 2")
    tiles = _factory_selection_tiles(factory)
    assert len(tiles) == 1
    assert tiles[0].property("cardId") == "mk2-extractor"


def test_dev_tools_can_pause_resume_and_reset_state() -> None:
    _app()
    window = MainWindow()
    dev = window.findChild(DevToolsView)
    assert dev is not None

    dev._toggle_pause()
    assert dev._is_paused() is True
    dev._toggle_pause()
    assert dev._is_paused() is False

    dev._bus.dispatch(AddCash(500))
    assert dev._state.cash.amount > 1250
    dev._reset()
    assert dev._state.cash.amount == 1250
