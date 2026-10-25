from __future__ import annotations

import os
import inspect
from release_test_support import legacy_component
import re
from pathlib import Path
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontInfo, QFontMetrics, QImage, QPainter, QResizeEvent, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPushButton, QProgressBar, QScrollArea, QSizePolicy, QSlider, QSpinBox, QStackedWidget, QTableView, QTableWidget, QTabWidget, QTreeWidget, QVBoxLayout, QWidget
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, AddIndustrialScrap, AddResource, AssignFreightCard, BuildFreightFacility, CommandBus, InstallCardInHall, InstallFreightCard, PurchaseHall, SelectMachineProduction, SellResource, SetResourceCapacity, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.contracts import DAILY, WEEKLY, ActiveContract, ContractOffer, receive_contract_delivery
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import MachineType, Rarity
from production_zero.core.enums import CardKind
from production_zero.core.freight import MarketDeliveryResolution, build_freight_facility, expand_freight_facility, freight_facility_build_cost, start_outbound_shipments
from production_zero.core.packs import DAILY_MINI_PACK, FULL_PACK, grant_pack
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, HallSlot, MachineProductionState
from production_zero.core.storage_upgrades import inventory_storage_capacity, inventory_storage_upgrade_cost
import production_zero.ui.factory_view as factory_view_module
import production_zero.ui.event_feed as event_feed_module
import production_zero.ui.game_ui.rendering.factory as factory_rendering_module
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.progression import record_lifetime_production
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.event_feed import EventFeedController, EventFeedWidget, FeedEvent
from production_zero.ui.factory_view_v2 import FactoryViewV2, FactoryV2CommandButton, FactoryCommandDeckWidget
from production_zero.ui.factory_view_v2 import FactoryV2ResourceDrawer
from production_zero.ui.freight_view import FREIGHT_SLOT_CARD_HEIGHT, FREIGHT_SLOT_CARD_WIDTH, FREIGHT_SLOT_GRID_SPACING, FreightView
from production_zero.ui.charts_view import ChartsView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame, InventoryView
from production_zero.ui.market_view import MarketView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2, EnergyViewV2
from production_zero.ui.main_tab_header import (
    MAIN_TAB_HEADER_HEIGHT,
    MAIN_TAB_HEADER_MARGINS,
    MAIN_TAB_HEADER_SPACING,
    MAIN_TAB_SUBTITLE_EMBOLDEN_OFFSET,
    MAIN_TAB_TITLE_EMBOLDEN_OFFSET,
    MAIN_TAB_TITLE_SPACING,
    MainTabHeaderLabel,
)
from production_zero.ui.packs_view import BoosterPackTileFrame, PacksView
from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.resource_tiles import (
    ElidedResourceLabel,
    RESOURCE_TILE_HEIGHT,
    RESOURCE_TILE_ICON_HOST_SIZE,
    RESOURCE_TILE_ICON_SIZE,
    RESOURCE_TILE_WIDTH,
    ResourceSelectionGridHost,
    ResourceSelectionTile,
    build_resource_selector_filter_panel,
)
from production_zero.ui.supply_view import COMMON_SUPPLY_CARD_HEIGHT, COMMON_SUPPLY_CARD_WIDTH, COMMON_SUPPLY_LEFT_PADDING, DAILY_SUPPLY_VISIBLE_CARDS, FEATURED_SUPPLY_CARD_HEIGHT, FEATURED_SUPPLY_CARD_WIDTH, SupplyOfferCardFrame, SupplyView
from production_zero.ui.theme import APP_STYLESHEET, Theme
from production_zero.ui.game_ui.rendering.factory import _BLOCK_GLYPHS
from production_zero.ui.widget_lifecycle import clear_layout_safely
from production_zero.ui.window_geometry import clamp_window_geometry_to_available, clamp_window_size_to_available
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView
from qt_top_level_guard import assert_no_visible_top_level_delta, drain_qt_events


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    if not app.property("productQaFontsLoaded"):
        from production_zero.tools.ui_contact_sheet import _load_qa_fonts
        _load_qa_fonts()
        app.setProperty("productQaFontsLoaded", True)
    return app


def _main_window_with_dev_tools() -> MainWindow:
    import production_zero.ui.main_window as main_window_module

    previous = main_window_module.DEVELOPMENT_MODE
    main_window_module.DEVELOPMENT_MODE = True
    try:
        return MainWindow()
    finally:
        main_window_module.DEVELOPMENT_MODE = previous


def _main_window_with_charts() -> MainWindow:
    return MainWindow(charts_enabled=True)


@pytest.fixture(autouse=True)
def _dispose_test_windows():
    app = _app()
    # Exercise real modal purchase dialogs. The former one-click tests otherwise
    # wait forever for a human. No command, cash or installation code is mocked.
    from production_zero.ui.release_dialogs import IndustrialDialog
    def answer_purchase():
        for dialog in app.topLevelWidgets():
            if isinstance(dialog, IndustrialDialog) and dialog.isVisible():
                if dialog.quantity is not None:
                    supply = dialog.parentWidget()
                    requested = supply._common_buy_quantity() if hasattr(supply, '_common_buy_quantity') else 1
                    dialog.quantity.setValue(requested)
                dialog.accept_button.click()
    driver = QTimer()
    driver.timeout.connect(answer_purchase)
    driver.start(10)
    yield
    driver.stop()
    if QApplication.instance() is not None:
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()


def _style_block(selector: str) -> str:
    exact = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\n\}}", APP_STYLESHEET, re.DOTALL)
    if exact is not None:
        return exact.group("body")
    requested = {part.strip() for part in selector.split(",")}
    matches = [block for block in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>.*?)\n\}", APP_STYLESHEET, re.DOTALL)
               if requested <= {part.strip() for part in block.group("selectors").split(",")}]
    assert matches, f"Missing style selector: {selector}"
    return matches[-1].group("body")


def _load_header_typography_probe_fonts() -> None:
    for font_path in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/bahnschrift.ttf"),
        Path("C:/Windows/Fonts/agencyr.ttf"),
        Path("C:/Windows/Fonts/agencyb.ttf"),
    ):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


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


def _assert_factory_runtime_refs_valid(factory: FactoryViewV2) -> None:
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
    # Contract UI fixtures use dedicated contract routes; market routes would now drain their eligibility stock.
    for card_id, assignment in tuple(contracts_view._state.freight.assignments.items()):
        if assignment.destination_kind == "market":
            contracts_view._state.freight.assignments.pop(card_id)


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
            (facility_ids["airport"], "freight.aircraft"),
            (facility_ids["garage_depot"], "freight.truck"),
            (facility_ids["harbor"], "freight.ship"),
            (facility_ids["rail_station"], "freight.train"),
        ):
            card = create_card_instance(f"{prefix}-{facility_id}-{index}", definition_id, CardKind.FREIGHT, Rarity.COMMON)
            bus.dispatch(AddCard(card))
            bus.dispatch(InstallFreightCard(facility_id, index, card.card_id, definitions))
            resource_id, destination = assignments[assignment_index]
            assignment_index += 1
            bus.dispatch(AssignFreightCard(card.card_id, resource_id, destination))


def _select_contract_product(card: QFrame, resource_id: str) -> None:
    selectors = card.findChildren(QComboBox, "contractProductSelect")
    assert selectors
    index = selectors[0].findData(resource_id)
    assert index >= 0
    selectors[0].setCurrentIndex(index)
    used = {resource_id}
    for selector in selectors[1:]:
        choice = next(
            item_index for item_index in range(1, selector.count())
            if selector.itemData(item_index) not in used
        )
        used.add(selector.itemData(choice))
        selector.setCurrentIndex(choice)
    QApplication.processEvents()


def _make_contract_product_eligible(contracts_view: ContractsView, resource_id: str, production_id: str) -> None:
    contracts_view._state.production_progress.unlocked_production_ids.add(production_id)
    stock = contracts_view._state.ensure_resource(resource_id)
    stock.capacity = max(stock.capacity, 10000)
    if stock.amount <= 0:
        stock.add(1)
    contracts_view.refresh()


def _advance_contract_freight(contracts_view: ContractsView) -> None:
    SimulationEngine(contracts_view._definitions).advance_time(contracts_view._state, 420)
    contracts_view.refresh()


def _deliver_contract_until_settled(contracts_view: ContractsView, kind: str, attempts: int = 80) -> None:
    for _ in range(attempts):
        active = contracts_view._state.contracts.active.get(kind)
        if active is None or active.status == "completed":
            return
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
    return supply_view.findChildren(QFrame, "dailyMachineSupplyCard")


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
    return [wrapper.front for wrapper in packs_view._reveal_cards]


def _finish_pack_reveal(packs_view: PacksView) -> None:
    # Advance Qt's own animations deterministically; timing is covered separately.
    packs_view._deal_timer.stop()
    while packs_view._deal_index < len(packs_view._reveal_cards):
        packs_view._deal_next()
    for wrapper in packs_view._reveal_cards:
        wrapper._deal.setCurrentTime(wrapper._deal.duration())
        wrapper.reveal()
        wrapper._flip.setCurrentTime(wrapper._flip.duration())
        wrapper._feedback.setCurrentTime(wrapper._feedback.duration())
    QApplication.processEvents()


def _assert_sparse_widget_group_centered(cards: list[QFrame], container: QWidget, expected_size: tuple[int, int]) -> None:
    if container.layout() is not None:
        container.layout().activate()
    container.updateGeometry()
    QApplication.processEvents()
    assert cards
    assert {(card.width(), card.height()) for card in cards} == {expected_size}
    ordered = sorted(cards, key=lambda card: card.mapTo(container, card.rect().topLeft()).x())
    left = ordered[0].mapTo(container, ordered[0].rect().topLeft()).x()
    right = ordered[-1].mapTo(container, ordered[-1].rect().topRight()).x()
    group_center = (left + right) / 2
    container_center = container.width() / 2
    assert abs(group_center - container_center) <= 8


def _assert_widget_group_right_aligned(cards: list[QFrame], container: QWidget, expected_size: tuple[int, int], *, tolerance: int = 14) -> None:
    if container.layout() is not None:
        container.layout().activate()
    container.updateGeometry()
    QApplication.processEvents()
    assert cards
    assert {(card.width(), card.height()) for card in cards} == {expected_size}
    ordered = sorted(cards, key=lambda card: card.mapTo(container, card.rect().topLeft()).x())
    right = ordered[-1].mapTo(container, ordered[-1].rect().topRight()).x()
    assert abs(container.rect().right() - right) <= tolerance


def _assert_widget_group_left_aligned(cards: list[QFrame], container: QWidget, expected_size: tuple[int, int]) -> None:
    container.layout().activate()
    QApplication.processEvents()
    assert cards
    assert {(card.width(), card.height()) for card in cards} == {expected_size}
    assert min(card.mapTo(container, card.rect().topLeft()).x() for card in cards) == 2


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
        and widget.graphicsProxyWidget() is None
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


class _TopLevelEventProbe(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[tuple[QEvent.Type, str, str, str, str | None, bool, tuple[int, int, int, int]]] = []

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            isinstance(watched, QWidget)
            and watched.isWindow()
            and event.type() in {QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Close}
        ):
            parent = watched.parentWidget()
            geometry = watched.geometry()
            self.events.append(
                (
                    event.type(),
                    type(watched).__name__,
                    watched.metaObject().className(),
                    watched.objectName(),
                    parent.objectName() if parent is not None else None,
                    watched.isVisible(),
                    (geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                )
            )
        return False


def _factory_selection_tiles(factory: FactoryViewV2) -> list[QFrame]:
    return factory.findChildren(QFrame, "factoryCardSelectionTile")


def _factory_selection_tile_by_name(factory: FactoryViewV2, card_name: str) -> QFrame:
    expected = card_name.lower()
    return next(
        tile
        for tile in _factory_selection_tiles(factory)
        if expected in tile.findChild(QLabel, "factoryCardSelectionTileName").text().lower()
    )


def _install_factory_card_from_selection(factory: FactoryViewV2, card_name: str) -> None:
    tile = _factory_selection_tile_by_name(factory, card_name)
    assert tile.findChild(QPushButton, "installSelectedCardButton") is None
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _select_factory_default_production(factory: FactoryViewV2, card_id: str) -> None:
    card = factory._state.cards[card_id]
    definition = factory._definitions[card.definition_id]
    assert isinstance(definition, MachineDefinition)
    production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
    factory._command_bus.dispatch(SelectMachineProduction(card_id, production.production_id, production.output_resource))
    factory.refresh_view()


def _open_production_selection_for_slot(factory: FactoryViewV2, slot_index: int = 0) -> None:
    slot_widget = factory._slot_widgets[slot_index]
    slot_widget.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
        "position": lambda self: slot_widget._resource_control_rect().center(),
    })())


def _production_selection_tiles(factory: FactoryViewV2) -> list[QFrame]:
    return factory.findChildren(QFrame, "productionSelectionTile")


def _production_tile_names(factory: FactoryViewV2) -> list[str]:
    return [
        tile.findChild(QLabel, "productionTileName").text().title()
        for tile in _production_selection_tiles(factory)
    ]


def _click_production_tile(factory: FactoryViewV2, name: str) -> None:
    tile = next(tile for tile in _production_selection_tiles(factory) if tile.findChild(QLabel, "productionTileName").text().title() == name)
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _production_guide_tiles(factory: FactoryViewV2) -> list[QFrame]:
    return factory.findChildren(QFrame, "productionGuideTile")


def _production_guide_tile_names(factory: FactoryViewV2) -> list[str]:
    return [
        tile.findChild(QLabel, "productionGuideTileName").text().title()
        for tile in _production_guide_tiles(factory)
    ]


def _click_production_guide_tile(factory: FactoryViewV2, name: str) -> None:
    # P1 materializes filtered results. Navigate through the real search rather
    # than clicking an eagerly created, hidden tile outside the active grid.
    if name not in _production_guide_tile_names(factory):
        factory.findChild(QLineEdit, "productionGuideSearchInput").setText(name)
    tile = next(tile for tile in _production_guide_tiles(factory) if tile.findChild(QLabel, "productionGuideTileName").text().title() == name)
    tile.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())


def _chain_canvas_content(factory: FactoryViewV2) -> QWidget:
    canvas = factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas")
    assert canvas is not None
    assert canvas.content_widget is not None
    return canvas.content_widget


def _chain_stage_groups(factory: FactoryViewV2) -> dict[str, QWidget]:
    content = _chain_canvas_content(factory)
    return {
        group.property("stage"): group
        for group in content.findChildren(QWidget, "chainStageGroup")
    }


def _chain_stage_order(factory: FactoryViewV2) -> list[str]:
    content = _chain_canvas_content(factory)
    return [
        group.property("stage")
        for group in content.findChildren(QWidget, "chainStageGroup")
    ]


def _chain_resource_names(group: QWidget) -> set[str]:
    return {
        label.text()
        for label in group.findChildren(QLabel, "chainResourceName")
    }


def _add_freight_inventory_card(freight_view: FreightView, card_id: str, definition_id: str) -> None:
    # Control this drawer fixture: the application separately tests its starter trucks.
    for starter in ("starter-truck-common-001", "starter-truck-common-002"):
        if starter not in freight_view._state.installed_freight_card_ids():
            freight_view._state.cards.pop(starter, None)
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
        from production_zero.core.production_pause import freight_line_number
        unit = freight_view._state.freight.facilities[freight_view._selected_facility_id]
        positions[card.property("slotIndex")] = (freight_line_number(unit, card.property("slotIndex")) + row, column)
    return positions


def _freight_slot_sizes(freight_view: FreightView) -> dict[int, tuple[int, int]]:
    return {
        card.property("slotIndex"): (card.width(), card.height())
        for card in freight_view.findChildren(QFrame, "freightSlotCard")
        if card.property("slotState") != "locked"
    }


def _freight_locked_slot_cards(freight_view: FreightView):
    # Unified rows use slot previews plus a separate next-line purchase action.
    from production_zero.ui.game_ui import GameButton
    cards = [card for card in freight_view.findChildren(QFrame, "freightSlotCard") if card.property("slotState") == "locked"]
    cards += freight_view.findChildren(GameButton, "unlockFreightLineButton")
    return sorted(cards, key=lambda card: card.property("slotIndex"))


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
    QTest.mouseClick(frame, Qt.MouseButton.LeftButton, pos=frame.rect().center())


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


def _assign_freight_market_via_ui(freight_view: FreightView, card_id: str, resource_id: str) -> None:
    freight_view._state.ensure_resource(resource_id).amount = max(1, freight_view._state.ensure_resource(resource_id).amount)
    _open_freight_assignment_view(freight_view, card_id)
    _click_frame(_freight_assignment_resource_tile(freight_view, resource_id))
    freight_view._choose_assignment_destination('market')
    freight_view._confirm_assignment()
    assert freight_view.findChild(QSlider, "freightAssignmentReserveSlider") is None
    assert freight_view.findChild(QPushButton, "freightApplyMarketAssignmentButton") is None


def test_main_window_has_expected_top_tabs() -> None:
    _app()
    window = MainWindow(development_mode=False)

    tabs = window.findChild(QTabWidget, "mainTabs")

    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Resources",
        "Factory",
        "Energy",
        "Freight",
        "Industrial Supply",
        "Inventory",

            "Contracts",
            "Consortium",
            "Research",
        "Leaderboard",
    ]
    assert window.findChild(DevToolsView) is None
    assert window.findChild(ChartsView) is None


def test_charts_tab_requires_explicit_opt_in() -> None:
    _app()
    window = _main_window_with_charts()
    tabs = window.findChild(QTabWidget, "mainTabs")

    assert tabs is not None
    assert "Charts" in [tabs.tabText(index) for index in range(tabs.count())]
    assert window.findChild(ChartsView) is not None


def test_disabled_charts_are_not_constructed(monkeypatch) -> None:
    _app()
    import production_zero.ui.main_window as main_window_module

    def fail_if_constructed(*_args, **_kwargs):
        raise AssertionError("ChartsView must not be constructed while Charts is disabled")

    monkeypatch.setattr(main_window_module, "ChartsView", fail_if_constructed)
    window = MainWindow(charts_enabled=False)

    assert window.findChild(QTabWidget, "mainTabs") is not None


def test_dev_tab_is_available_only_when_development_mode_is_explicit() -> None:
    _app()
    window = _main_window_with_dev_tools()
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert tabs is not None
    assert tabs.tabText(tabs.count() - 1) == "Dev"
    assert window.findChild(DevToolsView) is not None
    assert isinstance(window._global_header, FactoryCommandDeckWidget)
    assert isinstance(tabs.widget(1), FactoryViewV2)
    assert window.findChild(QFrame, "eventFeed") is not None
    assert window.findChild(QLabel, "factoryV2CashValue").text() == "$1,250"
    assert "MW" in window.findChild(QLabel, "factoryV2EnergyValue").text()


def test_event_feed_aggregates_same_events_and_keeps_types_separate() -> None:
    _app()
    feed = EventFeedWidget()

    for amount in (120, 800, 300, 450):
        feed.push(FeedEvent("cash", "Shipment", amount))
    feed.push(FeedEvent("xp", "Daily Contract", 450))
    feed.flush_pending()

    texts = tuple(feed._event_text(event) for event in feed.history)
    assert any("+$1,670" in text and "Shipment ×4" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert len(texts) == 2


def test_event_feed_suppresses_zero_xp_and_preserves_fractional_rewards() -> None:
    _app(); feed=EventFeedWidget()
    feed.push(FeedEvent('xp','No Reward',0))
    feed.push(FeedEvent('xp','Market sales',.2))
    feed.push(FeedEvent('xp','Company Progress',10.2))
    feed.flush_pending()
    assert len(feed.history)==1 and feed.history[0].amount==pytest.approx(10.4)
    assert '+10.4 XP' in feed._event_text(feed.history[0])
    assert all('No Reward' not in text for text in feed.entry_texts())


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

    texts = tuple(feed._event_text(event) for event in feed.history)
    assert any("+$1,520" in text and "Income" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert any(event.event_type == "contract" and event.label == "Contract completed" for event in feed.history)
    assert any("+1 PACK" in text for text in texts)
    assert cash_highlights[-1] == (320, 1520)


def test_event_feed_reports_production_unlocks_once() -> None:
    _app()
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=2)
    feed = EventFeedWidget()
    controller = EventFeedController(state, feed, definitions=definitions)

    state.production_progress.pending_unlock_ids.append("recipe.processor.iron")
    controller.observe()
    controller.observe()
    feed.flush_pending()

    texts = tuple(feed._event_text(event) for event in feed.history)
    assert sum("NEW" in text and "Iron unlocked" in text for text in texts) == 1
    assert state.production_progress.pending_unlock_ids == []


def test_event_feed_reports_only_economic_summary_for_market_delivery() -> None:
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

    texts = tuple(feed._event_text(event) for event in feed.history)
    assert any("+$45" in text and "Iron Shipment" in text for text in texts)
    assert not any("Shipment Delivered" in text or "DONE" in text for text in texts)
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
    state.contracts.daily_period_index = state.company_xp_progress.utc_day_index
    state.contracts.active[DAILY] = ActiveContract(
            ContractOffer("runtime-iron", DAILY, "Runtime Iron", {"iron": 25}, 0, 0, state.contracts.daily_period_index)
    )
    _add_freight_inventory_card(freight, "runtime-market-truck", "freight.truck")
    bus.dispatch(InstallFreightCard("garage-1", 0, "runtime-market-truck", definitions))
    bus.dispatch(AssignFreightCard("runtime-market-truck", "iron", "market"))
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
    assert state.contracts.active[DAILY].delivered == {}
    assert state.contracts.active[DAILY].status == "active"
    assert delivery.contract_amount == 0
    assert delivery.market_amount == 40
    assert state.cash.amount == starting_cash + 160
    assert state.statistics.total_earnings == starting_earnings + 160
    assert state.freight.assignments["runtime-market-truck"].destination_kind == "market"
    assert state.freight.outbound_shipments == {}
    texts = tuple(feed._event_text(event) for event in feed.history)
    assert not any("Iron Delivered to Runtime Iron Contract" in text for text in texts)
    assert any("+$160" in text and "Iron Shipment" in text for text in texts)
    assert not any("+$120" in text for text in texts)


def test_market_shipments_aggregate_cash_and_count_without_generic_delivery_duplicate() -> None:
    _app()
    state = GameState(rng_seed=3)
    feed = EventFeedWidget()
    controller = EventFeedController(state, feed)
    for index, earnings in enumerate((100, 109, 118)):
        state.freight.completed_market_deliveries.append(MarketDeliveryResolution(
            delivery_id=index,
            shipment_id=f"copper-market-{index}",
            resource_id="copper_wire",
            delivered_amount=10,
            contract_amount=0,
            market_amount=10,
            market_price=earnings / 10,
            market_earnings=earnings,
        ))
        state.cash.add(earnings)
    controller.observe()
    feed.flush_pending()

    market_events = [event for event in feed.history if event.group_key == "market:copper_wire"]
    assert len(market_events) == 1
    assert market_events[0].amount == 327
    assert market_events[0].count == 3
    assert any("+$327" in text and "Copper Wire Shipment ×3" in text for text in feed.entry_texts())
    assert not any(event.event_type == "delivery" for event in feed.history)


def test_contract_deliveries_aggregate_by_resource_and_contract_identity() -> None:
    _app()
    state = GameState(rng_seed=4)
    state.contracts.active[DAILY] = ActiveContract(
        ContractOffer("daily-copper", DAILY, "Daily Copper", {"copper_wire": 100}, 0, 0, 0)
    )
    state.contracts.active[WEEKLY] = ActiveContract(
        ContractOffer("weekly-copper", WEEKLY, "Weekly Copper", {"copper_wire": 100}, 0, 0, 0)
    )
    feed = EventFeedWidget()
    controller = EventFeedController(state, feed)

    receive_contract_delivery(state, "daily-copper", "copper_wire", 10)
    controller.observe()
    receive_contract_delivery(state, "daily-copper", "copper_wire", 10)
    controller.observe()
    receive_contract_delivery(state, "weekly-copper", "copper_wire", 20)
    controller.observe()
    feed.flush_pending()

    deliveries = [event for event in feed.history if event.event_type == 'delivery']
    assert len(deliveries)==1 and deliveries[0].amount==40 and deliveries[0].count==3
    assert deliveries[0].label=='Freight deliveries' and not deliveries[0].resource_id


def test_event_feed_is_visual_only_tab_wide_and_stays_inside_band(monkeypatch) -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    feed = window.findChild(EventFeedWidget, "eventFeed")
    factory = window.findChild(FactoryViewV2)
    assert tabs is not None
    assert feed is not None
    assert factory is not None
    starting_cash = factory._state.cash.amount
    starting_xp = factory._state.company.current_xp

    feed.push(FeedEvent("pack", "Full Pack"))
    feed.flush_pending()
    assert feed.entry_texts()
    tabs.setCurrentIndex(tabs.indexOf(legacy_component(window, MarketView)))
    assert window.findChild(EventFeedWidget, "eventFeed") is feed
    assert factory._state.cash.amount == starting_cash
    assert factory._state.company.current_xp == starting_xp

    entry = feed._entries[0]
    assert entry is not None
    monkeypatch.setattr(event_feed_module, "monotonic", lambda: 1000.0)
    entry.created_at = 100.0
    feed._tick()
    assert feed.entry_texts() and feed._live_panel.parentWidget() is feed


def test_reward_feed_is_tab_row_ticker_and_does_not_change_main_window_geometry() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    feed = window.findChild(EventFeedWidget, "eventFeed")
    assert factory is not None
    assert tabs is not None
    assert feed is not None
    assert feed.parent() is window.findChild(QFrame, "mainNavigationRow")

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

    texts = tuple(feed._event_text(event) for event in feed.history)
    assert any("+$1,200" in text and "Contract Reward" in text for text in texts)
    assert any("+450 XP" in text and "Daily Contract" in text for text in texts)
    assert any(event.event_type == "contract" and event.label == "Contract completed" for event in feed.history)
    assert any("+1 PACK" in text for text in texts)
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
    assert freight.findChild(QLabel, "freightBayPlate").text() == "FLEET 01"
    freight._state.cash.add(8_000)
    _choose_freight_build_dialog("rail_station")
    freight.findChild(QPushButton, "buildFreightFacilityButton").click()
    tree = freight.findChild(QTreeWidget, "freightFacilityTreeV2")
    assert tree is not None
    assert [tree.topLevelItem(index).text(0) for index in range(tree.topLevelItemCount())] == [
        "Garage 1\n0 / 3 slots · 0 shipments",
        "Rail Depot 1\n0 / 2 slots · 0 shipments",
    ]
    _select_freight_facility(freight, "rail_station-1")

    assert freight._selected_facility_id == "rail_station-1"
    assert freight.findChild(QFrame, "freightFacilityHeader").property("facilityTitle") == "RAIL DEPOT 1"
    assert freight.findChild(QFrame, "freightFacilityHeader").property("facilityMeta") == "0/2 slots; 0 active shipments"
    assert freight.findChild(QScrollArea, "freightSlotsScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert freight.findChild(QFrame, "freightKpiPanel") is None
    assert isinstance(freight.findChild(QFrame, "freightSlotsPanel"), FactoryV2Board)
    assert isinstance(freight.findChild(QFrame, "freightFacilityOverview"), FactoryV2HallOverview)
    assert isinstance(freight.findChild(QFrame, "freightBayTrack"), FactoryV2TrackPanel)
    assert isinstance(freight.findChild(QLabel, "freightBayPlate"), FactoryV2LinePlate)
    assert freight.findChild(QLabel, "freightBayPlate").text() == "RAIL LINE 01"
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
    assert [bool(card.property("clickEnabled")) for card in locked] == [True, False, False, False, False, False]
    assert locked[0].property("unlockCost") == 60.0


def test_freight_initial_garage_grid_reflows_after_width_settles() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None

    freight.resize(640, 800)
    freight.refresh()
    assert _freight_slot_grid_positions(freight)[2][0] > 0

    tabs = window.findChild(QTabWidget, "mainTabs")
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    window.resize(1400, 800)
    window.show()
    QApplication.processEvents()
    QTest.qWait(20)
    QApplication.processEvents()

    assert _freight_slot_grid_positions(freight) == {0: (0, 0), 1: (0, 1), 2: (0, 2)}


def test_freight_slots_wrap_within_viewport_without_horizontal_clipping() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    freight = window.findChild(FreightView)
    assert tabs is not None
    assert freight is not None

    tabs.setCurrentWidget(freight)
    window.resize(1538, 900)
    window.show()
    QApplication.processEvents()
    freight.refresh()
    QApplication.processEvents()

    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll is not None and scroll.widget() is not None
    cards = sorted(scroll.widget().findChildren(QFrame, "freightSlotCard"), key=lambda card: card.property("slotIndex"))

    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert len(cards) == 8
    assert max(card.geometry().right() for card in cards) <= scroll.viewport().width()
    assert len({card.parentWidget() for card in cards}) == 1
    assert [card.property("slotIndex") for card in cards] == list(range(8))
    assert freight.findChild(__import__("production_zero.ui.game_ui", fromlist=["GameButton"]).GameButton, "unlockFreightLineButton") is not None


def test_expanded_freight_garage_truck_cards_wrap_without_being_cut_off() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    freight = window.findChild(FreightView)
    assert tabs is not None
    assert freight is not None

    garage = freight._state.freight.facilities["garage-1"]
    for _ in range(5):
        expand_freight_facility(garage)
    for index in range(8):
        card_id = f"ui-overflow-truck-{index}"
        freight._command_bus.dispatch(AddCard(create_card_instance(card_id, "freight.truck", CardKind.FREIGHT, Rarity.COMMON)))
        freight._command_bus.dispatch(InstallFreightCard("garage-1", index, card_id, freight._definitions))

    tabs.setCurrentWidget(freight)
    window.resize(1538, 900)
    window.show()
    QApplication.processEvents()
    freight.refresh()
    QApplication.processEvents()

    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll is not None and scroll.widget() is not None
    cards = sorted(scroll.widget().findChildren(QFrame, "freightSlotCard"), key=lambda card: card.property("slotIndex"))

    assert len(cards) == 8
    assert all(card.property("slotState") == "installed" for card in cards[:8])
    assert _freight_locked_slot_cards(freight)[0].property("slotIndex") == 8
    assert all((card.width(), card.height()) == (FREIGHT_SLOT_CARD_WIDTH, FREIGHT_SLOT_CARD_HEIGHT) for card in cards)
    assert max(card.geometry().right() for card in cards) <= scroll.viewport().width()
    assert max(card.geometry().bottom() for card in cards) <= scroll.widget().height()


def test_freight_slots_scroll_is_preserved_after_card_install() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    garage = freight._state.freight.facilities["garage-1"]
    for _ in range(5):
        expand_freight_facility(garage)
    _add_freight_inventory_card(freight, "ui-scroll-preserved-truck", "freight.truck")
    freight.resize(900, 420)
    freight.refresh()
    QApplication.processEvents()

    scroll = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll is not None
    assert scroll.verticalScrollBar().maximum() > 0
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    before = scroll.verticalScrollBar().value()

    _install_freight_from_drawer(freight, 0, "ui-scroll-preserved-truck")
    QApplication.processEvents()
    QTest.qWait(70)
    QApplication.processEvents()

    scroll_after = freight.findChild(QScrollArea, "freightSlotsScroll")
    assert scroll_after is not None
    assert scroll_after.verticalScrollBar().value() == min(before, scroll_after.verticalScrollBar().maximum())
    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-scroll-preserved-truck"


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
    _add_freight_inventory_card(freight, "ui-card-chassis-truck", "freight.truck")
    _install_freight_from_drawer(freight, 0, "ui-card-chassis-truck")
    freight._command_bus.dispatch(AssignFreightCard("ui-card-chassis-truck", "steel", "market"))
    freight.refresh()

    card = _freight_slot_card(freight, 0)
    assert card.property("slotState") == "installed"
    assert card.property("cardTitle") == "TRUCK"
    assert card.property("cardMeta") == "MK1 · COMMON"
    assert card.property("cardDetail") == "CAPACITY 40"
    assert card.property("cardSecondary") == "ROUTE: STEEL > SELL"
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
    _add_freight_inventory_card(freight, "ui-card-truck-icon", "freight.truck")
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
    freight._command_bus.dispatch(AddCash(200_000))
    for facility_type in ("rail_station", "harbor", "airport"):
        freight._command_bus.dispatch(BuildFreightFacility(facility_type))
    freight.refresh()

    specs = {
        "garage-1": ("freight.truck", "TRUCK", "FLEET 01", 40),
        "rail_station-1": ("freight.train", "TRAIN", "RAIL LINE 01", 400),
        "harbor-1": ("freight.ship", "SHIP", "SHIPPING LINE 01", 16000),
        "airport-1": ("freight.aircraft", "AIRCRAFT", "AIR ROUTE 01", 4000),
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
        freight._command_bus.dispatch(AssignFreightCard(card_id, resource_id, "market"))
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
        _add_freight_inventory_card(freight, f"ui-sync-truck-{index}", "freight.truck")
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
    _add_freight_inventory_card(freight, "ui-mixed-truck-0", "freight.truck")
    _add_freight_inventory_card(freight, "ui-mixed-truck-2", "freight.truck")

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
    freight._state.cash.add(100_000)
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

    for _ in range(4):
        _click_frame(_freight_locked_slot_cards(freight)[0])
    assert len(freight._state.freight.facilities["garage-1"].slots) == 8
    positions = _freight_slot_grid_positions(freight)
    assert positions[0] == (0, 0)
    assert positions[4] == (0, 4)
    assert positions[5] == (0, 5)
    assert positions[7] == (1, 1)
    assert freight.findChild(QScrollArea, "freightSlotsScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert len(_freight_locked_slot_cards(freight)) == 1


def test_freight_locked_slot_unlocks_exactly_one_slot_at_a_time() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight._state.cash.add(100_000)
    freight.refresh()

    for _ in range(4):
        _click_frame(_freight_locked_slot_cards(freight)[0])

    facility = freight._state.freight.facilities["garage-1"]
    assert len(facility.slots) == 7
    locked_before = _freight_locked_slot_cards(freight)
    assert locked_before[0].property("slotIndex") == 7

    _click_frame(locked_before[0])

    assert len(facility.slots) == 8
    locked_after = _freight_locked_slot_cards(freight)
    assert len(locked_after) == 1
    assert locked_after[0].property("slotIndex") == 8
    assert _freight_slot_grid_positions(freight)[7] == (1, 1)


@pytest.mark.parametrize(
    ("facility_type", "facility_id", "definition_id"),
    (
        ("garage_depot", "garage-1", "freight.truck"),
        ("rail_station", "rail_station-1", "freight.train"),
        ("harbor", "harbor-1", "freight.ship"),
        ("airport", "airport-1", "freight.aircraft"),
    ),
)
def test_active_freight_delivery_cash_refresh_enables_slot_without_removing_card(
    facility_type: str,
    facility_id: str,
    definition_id: str,
) -> None:
    app = _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    factory = window.findChild(FactoryViewV2)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None and freight is not None and tabs is not None
    factory.pause_simulation()
    tabs.setCurrentWidget(freight)
    if facility_type != "garage_depot":
        freight._state.cash.add(1_000_000)
        freight._command_bus.dispatch(BuildFreightFacility(facility_type))
        freight.refresh()
        _select_freight_facility(freight, facility_id)
    freight._state.cash.amount = 0
    card_id = f"qa-active-{facility_type}"
    _add_freight_inventory_card(freight, card_id, definition_id)
    freight._command_bus.dispatch(InstallFreightCard(facility_id, 0, card_id, freight._definitions))
    freight._command_bus.dispatch(AssignFreightCard(card_id, "steel", "market"))
    shipment = start_outbound_shipments(
        freight._state.freight,
        freight._state.cards,
        freight._definitions,
        destination_kind="market",
        resource_id="steel",
        quantity=1,
        market_price=1_000,
    )[0]
    freight.refresh()
    app.processEvents()
    locked = _freight_locked_slot_cards(freight)[0]
    assert locked.property("clickEnabled") is False

    freight._state.cash.add(1_000)
    freight.refresh_runtime()
    app.processEvents()

    assert shipment.active
    assert freight._state.freight.facilities[facility_id].slots[0].card_id == card_id
    assert locked.property("clickEnabled") is True
    before_cash = freight._state.cash.amount
    QTest.mouseClick(locked, Qt.MouseButton.LeftButton, pos=locked.rect().center())
    app.processEvents()
    assert len(freight._state.freight.facilities[facility_id].slots) == {
        "garage_depot": 4,
        "rail_station": 3,
        "harbor": 3,
        "airport": 3,
    }[facility_type]
    assert freight._state.cash.amount == before_cash - 60
    assert shipment.active

    freight._build_facility_type = facility_type
    freight._state.cash.amount = 0
    freight.refresh()
    app.processEvents()
    build = freight.findChild(QPushButton, "buildFreightFacilityButton")
    assert build is not None and build.isEnabled()  # Opens type choice; affordability is checked inside it.
    freight._state.cash.add(1_000_000)
    freight.refresh_runtime()
    cost = freight_facility_build_cost(freight._state.freight, facility_type)
    facility_count = len(freight._state.freight.facilities)
    before_cash = freight._state.cash.amount
    assert build.isEnabled()
    _choose_freight_build_dialog(facility_type)
    QTest.mouseClick(build, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert len(freight._state.freight.facilities) == facility_count + 1
    assert freight._state.cash.amount == before_cash - cost
    assert freight._state.freight.facilities[facility_id].slots[0].card_id == card_id
    assert shipment.active


def test_installed_freight_card_keeps_horizontal_slot_position() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight.resize(1400, 800)
    freight.refresh()
    _add_freight_inventory_card(freight, "ui-horizontal-truck", "freight.truck")

    _install_freight_from_drawer(freight, 0, "ui-horizontal-truck")

    positions = _freight_slot_grid_positions(freight)
    assert positions == {0: (0, 0), 1: (0, 1), 2: (0, 2)}
    assert _freight_slot_card(freight, 0).findChild(QLabel, "freightCardName").text() == "Freight Truck"


def test_freight_card_selection_view_filters_by_facility_family() -> None:
    _app()
    window = MainWindow()
    window.show()
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert tabs is not None
    tabs.setCurrentWidget(freight)
    _add_freight_inventory_card(freight, "ui-truck", "freight.truck")
    _add_freight_inventory_card(freight, "ui-train", "freight.train")

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
    assert isinstance(truck_card, InventoryCardFrame)
    assert truck_card.width() == INVENTORY_CARD_WIDTH
    assert truck_card.height() == INVENTORY_CARD_HEIGHT
    assert truck_card.property("cardTitle") == "FREIGHT"
    assert truck_card.property("cardMeta") == "COMMON"
    assert truck_card.findChild(QLabel, "freightSelectionFamily").text() == "TRUCK"

    freight.findChild(QLineEdit, "freightCardSearch").setText("truck")
    listed_after_search = _freight_selection_cards(freight)
    assert listed_after_search and all("truck" in card.property("freightFamily") for card in listed_after_search)


def _choose_freight_build_dialog(facility_type):
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from production_zero.ui.interaction_polish import BuildingChoiceDialog
    def choose():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, BuildingChoiceDialog)
        QTest.mouseClick(dialog.options[facility_type], Qt.MouseButton.LeftButton)
        QTest.mouseClick(dialog.accept_button, Qt.MouseButton.LeftButton)
    QTimer.singleShot(40, choose)


def test_freight_installation_targets_selected_facility_and_expanded_slot() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight._state.cash.add(100_000)
    freight.refresh()
    _choose_freight_build_dialog("garage_depot")
    freight.findChild(QPushButton, "buildFreightFacilityButton").click()
    garage_1 = freight._state.freight.facilities["garage-1"]
    garage_2 = freight._state.freight.facilities["garage-2"]
    _add_freight_inventory_card(freight, "ui-g1-truck", "freight.truck")
    _add_freight_inventory_card(freight, "ui-g2-truck", "freight.truck")
    _add_freight_inventory_card(freight, "ui-expanded-truck", "freight.truck")
    _add_freight_inventory_card(freight, "ui-hidden-train", "freight.train")

    _select_freight_facility(freight, "garage-1")
    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_cards(freight)[0].mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    truck_ids = {"ui-g1-truck", "ui-g2-truck", "ui-expanded-truck"}
    assert garage_1.slots[0].card_id in truck_ids
    installed_trucks = {garage_1.slots[0].card_id}
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert _freight_slot_card(freight, 0).findChild(QLabel, "freightCardName").text() == "Freight Truck"
    assert _freight_slot_card(freight, 0).findChild(ResourceIconWidget, "freightTypeIcon") is not None
    assert _freight_slot_card(freight, 0).findChild(QFrame, "freightRarityLine") is not None
    assert "1 / 3" in _freight_facility_tree_item(freight, "garage-1").text(0)

    _select_freight_facility(freight, "garage-2")
    _open_freight_drawer_for_slot(freight, 1)
    _freight_selection_cards(freight)[0].mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert garage_2.slots[1].card_id in truck_ids - installed_trucks
    installed_trucks.add(garage_2.slots[1].card_id)
    assert garage_1.slots[1].card_id is None

    freight._state.cash.add(500)
    _click_frame(_freight_locked_slot_cards(freight)[0])
    assert len(garage_2.slots) == 4
    _open_freight_drawer_for_slot(freight, 3)
    _freight_selection_cards(freight)[0].mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert garage_2.slots[3].card_id in truck_ids - installed_trucks
    assert freight.findChild(QFrame, "freightCardSelectionView") is None

    _open_freight_drawer_for_slot(freight, 2)
    listed_ids = [card.property("cardId") for card in _freight_selection_cards(freight)]
    assert truck_ids.isdisjoint(listed_ids)
    freight.findChild(QPushButton, "freightCloseDrawerButton").click()
    assert freight.findChild(QFrame, "freightCardSelectionView") is None


def test_freight_drawer_selection_survives_refresh_before_install() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-refresh-truck", "freight.truck")

    _open_freight_drawer_for_slot(freight, 2)
    assert _freight_selection_card_by_id(freight, "ui-refresh-truck") is not None

    freight.refresh()

    assert freight.findChild(QFrame, "freightCardSelectionView") is not None
    _freight_selection_card_by_id(freight, "ui-refresh-truck").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert freight._state.freight.facilities["garage-1"].slots[2].card_id == "ui-refresh-truck"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert _freight_slot_card(freight, 2).findChild(QLabel, "freightCardName").text() == "Freight Truck"


def test_freight_drawer_stacks_identical_trucks_and_updates_after_install() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    for index in range(3):
        _add_freight_inventory_card(freight, f"ui-stack-truck-{index}", "freight.truck")

    _open_freight_drawer_for_slot(freight, 0)

    cards = _freight_selection_cards(freight)
    assert len(cards) == 1
    assert cards[0].property("quantity") == 3
    assert cards[0].findChild(QLabel, "freightSelectionMeta").text() == "+0.0%"
    assert any(label.text() == "x3" for label in cards[0].findChildren(QLabel, "freightSelectionMeta"))

    cards[0].mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    installed_id = freight._state.freight.facilities["garage-1"].slots[0].card_id
    assert installed_id in {f"ui-stack-truck-{index}" for index in range(3)}

    _open_freight_drawer_for_slot(freight, 1)
    cards = _freight_selection_cards(freight)
    assert len(cards) == 1
    assert cards[0].property("quantity") == 2
    assert any(label.text() == "x2" for label in cards[0].findChildren(QLabel, "freightSelectionMeta"))


def test_freight_drawer_keeps_distinct_trucks_separate() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-common-truck", "freight.truck")
    freight._command_bus.dispatch(AddCard(create_card_instance("ui-rare-truck", "freight.truck", CardKind.FREIGHT, Rarity.RARE, bonus_tenths=80)))
    freight.refresh()

    _open_freight_drawer_for_slot(freight, 0)

    cards = _freight_selection_cards(freight)
    assert len(cards) == 2
    assert sorted(card.property("quantity") for card in cards) == [1, 1]
    assert {card.property("rarity") for card in cards} == {"common", "rare"}


def test_freight_install_remove_and_assignment_controls() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-install", "freight.truck")

    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-install").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-truck-install"
    assert freight.findChild(QFrame, "freightCardSelectionView") is None
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "UNASSIGNED"
    assert freight.findChild(QLabel, "freightAssignmentEmpty").text() == "ASSIGN ROUTE"

    freight._state.ensure_resource("steel").amount = 1
    _open_freight_assignment_view(freight, "ui-truck-install")
    assert freight.findChild(QScrollArea, "freightAssignmentResourceScroll").horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    freight.findChild(QLineEdit, "freightAssignmentSearch").setText("steel")
    resource_tiles = freight.findChildren(QFrame, "freightAssignmentResourceTile")
    assert resource_tiles
    assert all("steel" in tile.property("resourceId") for tile in resource_tiles)
    _click_frame(_freight_assignment_resource_tile(freight, "steel"))
    freight._choose_assignment_destination('market')
    freight._confirm_assignment()
    assert freight.findChild(QFrame, "freightDestinationTile") is None
    assert freight.findChild(QPushButton, "freightApplyMarketAssignmentButton") is None
    freight._state.ensure_resource("steel").amount = 0
    freight.refresh_runtime()

    assignment = freight._state.freight.assignments["ui-truck-install"]
    assert assignment.resource_id == "steel"
    assert assignment.destination_kind == "market"
    assert freight.findChild(QFrame, "freightAssignmentSelectionView") is None
    assert freight.findChild(QLabel, "freightStatusLabel").text() == "WAITING"
    assert freight.findChild(QLabel, "freightStatusLabel").property("detailStatus") == "WAITING · NO CARGO"
    assert freight.findChild(QLabel, "freightAssignmentResource").text() == "STEEL"
    assert freight.findChild(QLabel, "freightAssignmentDestination").text() == "SELL"
    assert freight.findChild(QLabel, "freightReserveSummary") is None
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
    _add_freight_inventory_card(freight, "ui-clean-install", "freight.truck")

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
    assert _freight_slot_card(freight, 1).findChild(QLabel, "freightCardName").text() == "Freight Truck"


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
    _add_freight_inventory_card(freight, "ui-route-top-level-truck", "freight.truck")
    _install_freight_from_drawer(freight, 0, "ui-route-top-level-truck")
    before = _visible_top_level_signature()

    freight._state.ensure_resource("steel").amount = 1
    _open_freight_assignment_view(freight, "ui-route-top-level-truck")
    _click_frame(_freight_assignment_resource_tile(freight, "steel"))
    freight._choose_assignment_destination('market')
    freight._confirm_assignment()
    assert freight.findChild(QFrame, "freightDestinationTile") is None
    assert freight.findChild(QSlider, "freightAssignmentReserveSlider") is None
    assert freight.findChild(QPushButton, "freightApplyMarketAssignmentButton") is None
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

    _add_freight_inventory_card(freight, "ui-lifecycle-truck", "freight.truck")

    def install_truck() -> None:
        _install_freight_from_drawer(freight, 0, "ui-lifecycle-truck")

    assert_no_visible_top_level_delta(install_truck, allowed=(window,))
    assert freight._state.freight.facilities["garage-1"].slots[0].card_id == "ui-lifecycle-truck"

    def assign_route() -> None:
        _assign_freight_market_via_ui(freight, "ui-lifecycle-truck", "steel")

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
    supply._type_filter.setCurrentText("Freight")
    drain_qt_events()
    truck = next(
        card
        for card in _visible_common_supply_cards(supply)
        if card.findChild(QLabel, "supplyCardName").text() == "Freight Truck"
    )

    def buy_truck() -> None:
        truck.findChild(QPushButton, "buyCommonSupplyButton").click()

    before_cards = set(supply._state.cards)
    assert_no_visible_top_level_delta(buy_truck, allowed=(window,))
    new_cards = [card for card_id, card in supply._state.cards.items() if card_id not in before_cards]
    assert any(card.definition_id == "freight.truck" for card in new_cards)
    window.close()
    drain_qt_events()




def test_freight_facility_expansion_and_compact_cards() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    freight._state.cash.add(500)

    _click_frame(_freight_locked_slot_cards(freight)[0])

    assert len(freight._state.freight.facilities["garage-1"].slots) == 4
    _add_freight_inventory_card(freight, "ui-truck-compact", "freight.truck")
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
    freight._command_bus.dispatch(AddCash(200_000))
    for facility_type in ("rail_station", "harbor", "airport"):
        freight._command_bus.dispatch(BuildFreightFacility(facility_type))
    preview_specs = {
        "garage-1": ("ui-preview-truck", "freight.truck", "steel"),
        "rail_station-1": ("ui-preview-train", "freight.train", "iron"),
        "harbor-1": ("ui-preview-ship", "freight.ship", "coal"),
        "airport-1": ("ui-preview-aircraft", "freight.aircraft", "copper"),
    }
    for facility_id, (card_id, definition_id, resource_id) in preview_specs.items():
        _add_freight_inventory_card(freight, card_id, definition_id)
        freight._command_bus.dispatch(InstallFreightCard(facility_id, 0, card_id, freight._definitions))
        freight._command_bus.dispatch(AssignFreightCard(card_id, resource_id, "market"))
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


def test_freight_ready_with_any_available_cargo() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-waiting", "freight.truck")
    _install_freight_from_drawer(freight, 0, "ui-truck-waiting")
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-waiting", "steel", "market"))
    freight._command_bus.dispatch(SetResourceCapacity("steel", 100))
    freight._command_bus.dispatch(AddResource("steel", 40))
    freight.refresh()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "READY"
    assert status.property("detailStatus") == "READY"


def test_freight_contract_assignment_has_no_reserve_and_waits_without_contract() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-contract-wait", "freight.truck")
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
    _add_freight_inventory_card(freight, "ui-truck-transit", "freight.truck")
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
    assert freight.findChild(QSlider, "freightAssignmentReserveSlider") is None
    assert next(iter(freight._state.freight.outbound_shipments.values())).quantity == 4
    freight.findChild(QWidget, "freightAssignmentBackButton").click()
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
    assert transit_card.findChild(QLabel, "freightCardName").text() == "Freight Truck"
    assert not transit_card.findChildren(QLabel, "freightStatLabel")

    action.click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    status = freight.findChild(QLabel, "freightStatusLabel")
    assert status.text() == "IN TRANSIT"
    assert "TRANSIT" in status.property("detailStatus")
    assert "ui-truck-transit" not in freight._state.freight.assignments
    assert len(freight._state.freight.outbound_shipments) == 1
    assert next(iter(freight._state.freight.outbound_shipments.values())).quantity == 4
    assert freight.findChild(QLabel, "freightAssignmentEmpty").text() == "ASSIGN ROUTE"
    assert freight.findChild(QPushButton, "freightRemoveButton").text() == "CANCEL"

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
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert freight is not None
    assert tabs is not None
    factory.pause_simulation()
    _add_freight_inventory_card(freight, "ui-truck-live-progress", "freight.truck")
    freight._command_bus.dispatch(InstallFreightCard("garage-1", 0, "ui-truck-live-progress", freight._definitions))
    freight._command_bus.dispatch(AssignFreightCard("ui-truck-live-progress", "steel", "market"))
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
    factory = window.findChild(FactoryViewV2)
    freight = window.findChild(FreightView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert freight is not None
    assert tabs is not None
    factory.pause_simulation()
    _add_freight_inventory_card(freight, "ui-truck-assignment-live", "freight.truck")
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
    factory = window.findChild(FactoryViewV2)
    supply = window.findChild(SupplyView)
    inventory = legacy_component(window, InventoryView)
    market = legacy_component(window, MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert freight is not None
    assert factory is not None
    assert supply is not None
    assert inventory is not None
    assert market is not None
    assert tabs is not None

    _add_freight_inventory_card(freight, "ui-search-storm-truck", "freight.truck")
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
    guide_stage = factory.findChild(QWidget, "productionGuideStageFilter")
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
    assert supply.findChild(QLineEdit, "supplySearch") is None
    supply_type = supply._type_filter
    assert supply_type is not None
    for category in ("Resources", "Factory", "Energy", "Freight", "Resources"):
        supply_type.setCurrentText(category)
        _assert_no_visible_window_storm(window, baseline_visible)
        assert all(card.parentWidget() is not None and not card.isWindow() for card in _visible_common_supply_cards(supply))

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
    _add_freight_inventory_card(freight, "ui-truck-hover", "freight.truck")
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

    freight._command_bus.dispatch(AssignFreightCard("ui-truck-hover", "steel", "market"))
    freight.refresh_runtime()

    assert freight.findChild(QFrame, "freightHoverInfo") is hover
    assert any("Steel -> Sell" in label.text() for label in hover.findChildren(QLabel, "cardHoverValue"))
    assert all("Reserve" not in label.text() for label in hover.findChildren(QLabel, "cardHoverValue"))


def test_freight_card_selection_tiles_show_shared_hover_info() -> None:
    _app()
    window = MainWindow()
    freight = window.findChild(FreightView)
    assert freight is not None
    _add_freight_inventory_card(freight, "ui-truck-selection-hover", "freight.truck")

    _open_freight_drawer_for_slot(freight, 0)
    tile = _freight_selection_card_by_id(freight, "ui-truck-selection-hover")
    freight._show_freight_hover("ui-truck-selection-hover", tile)

    hover = freight.findChild(QFrame, "freightHoverInfo")
    assert hover is not None
    assert hover.parent() is freight
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Freight Truck"
    values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert "Truck" in values
    assert "Common" in values


def test_factory_view_can_install_and_remove_test_inventory_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._on_slot_clicked(0)
    view = factory.findChild(QFrame, "factoryCardSelectionView")
    tiles = _factory_selection_tiles(factory)
    assert view is not None
    assert factory.findChild(QFrame, "cardSelectionDrawer") is None
    scroll = factory.findChild(QScrollArea, "factoryCardSelectionScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert len(tiles) == 1
    processor_tile = _factory_selection_tile_by_name(factory, "Processor")
    assert isinstance(processor_tile, InventoryCardFrame)
    assert processor_tile.width() == INVENTORY_CARD_WIDTH
    assert processor_tile.height() == INVENTORY_CARD_HEIGHT
    assert processor_tile.property("cardTitle") == "PROCESSOR"
    assert processor_tile.property("cardMeta") == "COMMON"
    assert processor_tile.property("quantity") == 2
    assert processor_tile.findChild(ResourceIconWidget, "resourceIcon") is not None
    assert processor_tile.findChild(QFrame, "factoryCardSelectionRarityLine") is not None
    assert processor_tile.findChild(QLabel, "factoryCardSelectionTileFunction").text() == "PROCESSOR"
    assert processor_tile.findChild(QLabel, "factoryCardSelectionTileCount").text() == "x2"
    assert processor_tile.findChild(QPushButton, "installSelectedCardButton") is None

    _install_factory_card_from_selection(factory, "Processor")

    installed_id = factory._state.halls["hall-1"].slots[0].card_id
    assert installed_id in {"test-furnace-common-001", "test-blast-furnace-common-001"}
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None

    factory._on_slot_clicked(0)
    cid = factory._units[factory._selected_hall_id].slots[0].card_id
    cash = factory._state.cash.amount
    from production_zero.core.machine_operations import resale_value
    proceeds = resale_value(factory._state.cards[cid], factory._definitions[factory._state.cards[cid].definition_id])
    factory._sell_selection(cid)
    assert factory._state.cash.amount == cash + proceeds

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert installed_id not in factory._state.installed_card_ids()


def test_factory_runtime_installs_machine_without_default_resource_then_selects_production() -> None:
    _app()
    window = MainWindow()
    window.resize(1360, 860)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(ResourcesViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert tabs is not None
    tabs.setCurrentWidget(factory)
    factory.pause_simulation()
    starting_iron_ore = factory._state.resources["iron_ore"].amount

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    card_id = factory._state.resource_sites["site-1"].slots[0].card_id
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
    assert slot_widget._primary_value_text() == "SELECT"
    assert slot_widget._primary_caption_text() == "NO RESOURCE SELECTED"
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
    factory = window.findChild(ResourcesViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None
    assert tabs is not None
    tabs.setCurrentWidget(factory)

    factory._on_slot_clicked(0)
    drill_tile = _factory_selection_tile_by_name(factory, "Extractor")
    factory._show_card_selection_hover(drill_tile.property("cardId"), drill_tile)

    hover = factory.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    assert hover.isHidden() is False
    assert hover.parent() is factory
    assert not hover.isWindow()
    assert not (hover.windowFlags() & Qt.WindowType.Tool)
    assert not (hover.windowFlags() & Qt.WindowType.ToolTip)
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Extractor"
    values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert "Common" in values
    assert "Extractor" in values
    labels = [label.text() for label in hover.findChildren(QLabel, "cardHoverLabel")]
    assert "OUTPUT" in labels
    assert "AVAILABLE" not in labels


def test_card_tab_hovers_stay_embedded_without_extra_top_level_windows() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1360, 860)
    window.show()
    QApplication.processEvents()
    baseline_top_levels = set(app.topLevelWidgets())

    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(ResourcesViewV2)
    freight = window.findChild(FreightView)
    inventory = legacy_component(window, InventoryView)
    supply = window.findChild(SupplyView)
    packs = legacy_component(window, PacksView)
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
    factory_tile = _factory_selection_tile_by_name(factory, "Extractor")
    factory._show_card_selection_hover(factory_tile.property("cardId"), factory_tile)
    factory_hover = factory.findChild(QFrame, "cardHoverInfo")
    assert factory_hover is not None
    assert factory_hover.parent() is factory
    assert not factory_hover.isWindow()
    assert_no_new_visible_top_levels()

    _add_freight_inventory_card(freight, "hover-tab-truck", "freight.truck")
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

    pack_id = grant_pack(packs._state, DAILY_MINI_PACK, "hover-tab-pack")
    tabs.setCurrentWidget(packs)
    packs.refresh()
    packs._open_pack(pack_id, "general")
    _finish_pack_reveal(packs)
    pack_tiles = _pack_result_tiles(packs)
    assert pack_tiles
    pack_tiles[0].hovered.emit()
    pack_hover = packs.findChild(QFrame, "packResultCardHoverInfo")
    assert pack_hover is not None
    assert pack_hover.parent() is packs
    assert not pack_hover.isWindow()
    assert_no_new_visible_top_levels()


def test_factory_card_selection_view_back_closes_immediately() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
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
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Processor")
    assert factory._state.halls["hall-1"].slots[0].card_id is not None

    factory._on_slot_clicked(0)
    cid = factory._units[factory._selected_hall_id].slots[0].card_id
    cash = factory._state.cash.amount
    from production_zero.core.machine_operations import resale_value
    proceeds = resale_value(factory._state.cards[cid], factory._definitions[factory._state.cards[cid].definition_id])
    factory._sell_selection(cid)
    assert factory._state.cash.amount == cash + proceeds

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory.findChild(QFrame, "resourceDrawer") is None


def test_factory_removing_installed_card_clears_pending_selection_state() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Processor")

    factory._on_slot_clicked(1)
    assert factory.findChild(QFrame, "factoryCardSelectionView") is not None
    assert factory._drawer_slot_index == 1

    factory._on_slot_clicked(0)
    cid = factory._units[factory._selected_hall_id].slots[0].card_id
    cash = factory._state.cash.amount
    from production_zero.core.machine_operations import resale_value
    proceeds = resale_value(factory._state.cards[cid], factory._definitions[factory._state.cards[cid].definition_id])
    factory._sell_selection(cid)
    assert factory._state.cash.amount == cash + proceeds

    assert factory._state.halls["hall-1"].slots[0].card_id is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory._drawer_mode is None
    assert factory._drawer_slot_index is None
    assert factory._selected_card_id is None


def test_resources_view_opens_visual_production_selection_view_for_extractor_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(ResourcesViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")

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
    assert {"Iron Ore", "Coal", "Copper Ore"}.issubset(option_names)
    assert {"Timber", "Wheat", "Crude Oil", "Natural Rubber"}.isdisjoint(option_names)
    unlocked_count = len(factory._state.production_progress.unlocked_production_ids.intersection(
        production.production_id
        for production in factory._definitions["machine.extractor"].available_production_options
    ))
    locked_tiles = [tile for tile in _production_selection_tiles(factory) if tile.property("locked") is True]
    # Current rules unlock every primary resource at company creation.
    assert unlocked_count == 37
    assert len(option_names) == unlocked_count
    assert locked_tiles == []
    assert all(tile.isEnabled() for tile in _production_selection_tiles(factory))
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
    factory = window.findChild(ResourcesViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
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
    assert len(rows) >= 1


def test_canonical_resource_selection_tile_has_fixed_geometry_for_long_names() -> None:
    _app()
    tile = ResourceSelectionTile(
        resource_id="advanced_semiconductor_equipment",
        title="Advanced Semiconductor Equipment With A Deliberately Long Name",
        subtitle="Electronics / Advanced Manufacturing",
        detail="12345 / 99999",
        status="Current",
        icon_key="microchip",
        accent_key="electronics",
    )
    tile.ensurePolished()

    icon_host = tile.findChild(QFrame, "resourceSelectionIconHost")
    icon = tile.findChild(ResourceIconWidget, "resourceIcon")

    assert tile.size().width() == RESOURCE_TILE_WIDTH
    assert tile.size().height() == RESOURCE_TILE_HEIGHT
    assert tile.sizeHint().width() == RESOURCE_TILE_WIDTH
    assert tile.sizeHint().height() == RESOURCE_TILE_HEIGHT
    assert icon_host is not None
    assert icon_host.size().width() == RESOURCE_TILE_ICON_HOST_SIZE
    assert icon_host.size().height() == RESOURCE_TILE_ICON_HOST_SIZE
    assert icon is not None
    assert icon.size().width() == RESOURCE_TILE_ICON_SIZE
    assert icon.size().height() == RESOURCE_TILE_ICON_SIZE


def test_elided_resource_label_tooltip_only_appears_when_text_is_clipped() -> None:
    _app()
    label = ElidedResourceLabel(
        "ADVANCED SEMICONDUCTOR EQUIPMENT",
        tooltip_text="Advanced Semiconductor Equipment",
    )

    label.resize(70, 20)
    label.refresh_elision_tooltip()

    assert label.toolTip() == "Advanced Semiconductor Equipment"

    label.resize(QFontMetrics(label.font()).horizontalAdvance(label.text()) + 8, 20)
    label.refresh_elision_tooltip()

    assert label.toolTip() == ""


def test_shared_resource_tiles_keep_canonical_name_tooltips_for_elided_titles() -> None:
    _app()
    tile = ResourceSelectionTile(
        resource_id="advanced_semiconductor_equipment",
        title="Advanced Semiconductor Equipment",
        subtitle="Electronics",
        detail="12345 / 99999",
        icon_key="microchip",
        accent_key="electronics",
    )
    title = tile.findChild(QLabel, "resourceSelectionTileName")
    assert isinstance(title, ElidedResourceLabel)

    title.resize(72, title.height() or 26)
    title.refresh_elision_tooltip()

    assert title.text() == "ADVANCED SEMICONDUCTOR EQUIPMENT"
    assert title.toolTip() == "Advanced Semiconductor Equipment"
    assert tile.toolTip() == "Advanced Semiconductor Equipment"


def test_factory_and_freight_resource_selectors_share_canonical_tile_geometry() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(ResourcesViewV2)
    freight = window.findChild(FreightView)
    assert factory is not None
    assert freight is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    _open_production_selection_for_slot(factory)
    factory_tiles = _production_selection_tiles(factory)
    assert factory_tiles

    _add_freight_inventory_card(freight, "ui-truck-canonical-resource", "freight.truck")
    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-canonical-resource").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    _open_freight_assignment_view(freight, "ui-truck-canonical-resource")
    freight_tiles = freight.findChildren(QFrame, "freightAssignmentResourceTile")
    assert freight_tiles

    sample_tiles = [factory_tiles[0], freight_tiles[0]]
    assert all(isinstance(tile, ResourceSelectionTile) for tile in sample_tiles)
    assert {tile.size().width() for tile in sample_tiles} == {RESOURCE_TILE_WIDTH}
    assert {tile.size().height() for tile in sample_tiles} == {RESOURCE_TILE_HEIGHT}
    assert all(tile.findChild(QFrame, "resourceSelectionIconHost").size().width() == RESOURCE_TILE_ICON_HOST_SIZE for tile in sample_tiles)
    assert all(tile.findChild(ResourceIconWidget).size().width() == RESOURCE_TILE_ICON_SIZE for tile in sample_tiles)
    assert factory_tiles[0].findChild(QLabel, "productionTileName") is not None
    assert freight_tiles[0].findChild(QLabel, "freightAssignmentTileName") is not None


def test_factory_freight_and_production_guide_titles_share_elided_tooltip_behavior() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    resources = window.findChild(ResourcesViewV2)
    freight = window.findChild(FreightView)
    assert factory is not None
    assert resources is not None
    assert freight is not None

    resources._on_slot_clicked(0)
    _install_factory_card_from_selection(resources, "Extractor")
    _open_production_selection_for_slot(resources)
    factory_title = _production_selection_tiles(resources)[0].findChild(QLabel, "productionTileName")

    _add_freight_inventory_card(freight, "ui-truck-tooltip", "freight.truck")
    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-tooltip").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    _open_freight_assignment_view(freight, "ui-truck-tooltip")
    freight_title = freight.findChildren(QFrame, "freightAssignmentResourceTile")[0].findChild(QLabel, "freightAssignmentTileName")

    factory._open_production_guide()
    guide_title = _production_guide_tiles(factory)[0].findChild(QLabel, "productionGuideTileName")

    for title in (factory_title, freight_title, guide_title):
        assert isinstance(title, ElidedResourceLabel)
        title.resize(34, title.height() or 26)
        title.refresh_elision_tooltip()
        assert title.toolTip()
        assert title.parentWidget().toolTip().startswith(title.toolTip())
        if title is not freight_title:
            assert "BASE SELL PRICE:" in title.parentWidget().toolTip()
        assert title.toolTip().upper() == title.text()


def test_factory_and_freight_resource_selectors_share_light_gallery_surface() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(ResourcesViewV2)
    freight = window.findChild(FreightView)
    assert factory is not None
    assert freight is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    _open_production_selection_for_slot(factory)

    _add_freight_inventory_card(freight, "ui-truck-shared-surface", "freight.truck")
    _open_freight_drawer_for_slot(freight, 0)
    _freight_selection_card_by_id(freight, "ui-truck-shared-surface").mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    _open_freight_assignment_view(freight, "ui-truck-shared-surface")

    assert factory.findChild(QScrollArea, "productionSelectionScroll") is not None
    assert freight.findChild(QScrollArea, "freightAssignmentResourceScroll") is not None
    assert isinstance(factory.findChild(QWidget, "productionSelectionGridHost"), ResourceSelectionGridHost)
    assert isinstance(freight.findChild(QWidget, "freightAssignmentResourceGridHost"), ResourceSelectionGridHost)
    assert freight.findChild(QFrame, "freightSelectionFilters") is None

    light_gallery = _style_block("QScrollArea#productionSelectionScroll, QScrollArea#freightAssignmentResourceScroll")
    assert "background: rgba(255, 255, 255, 7);" in light_gallery
    assert "rgba(8, 12, 12, 116)" not in light_gallery


def test_card_selection_wrappers_remain_transparent_around_rendered_cards() -> None:
    assert "background: transparent;" in _style_block("QFrame#inventoryCard")
    assert "border: 0;" in _style_block("QFrame#inventoryCard")
    assert "background: transparent;" in _style_block("QFrame#factoryCardSelectionTile")
    assert "border: 0;" in _style_block("QFrame#factoryCardSelectionTile")
    assert "background: transparent;" in _style_block("QFrame#freightSelectionCard")
    assert "border: 0;" in _style_block("QFrame#freightSelectionCard")
    assert "background: transparent;" in _style_block("QFrame#packOpenedCardTile")
    assert "border: 0;" in _style_block("QFrame#packOpenedCardTile")


def test_factory_view_opens_visual_recipe_selection_view_for_processor_card() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    record_lifetime_production(
        factory._state,
        {"iron_ore": 120, "copper_ore": 120, "coal": 120},
        factory._definitions,
    )

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Processor")

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
    assert {"Iron", "Copper", "Steel"}.issubset(option_names)
    # The two locked previews follow the current prerequisite/name ordering.
    assert {"Aluminum", "Ammonia"}.issubset(option_names)
    assert "Bitumen" not in option_names
    assert {"Polymer", "Flour"}.isdisjoint(option_names)
    locked_tiles = [tile for tile in _production_selection_tiles(factory) if tile.property("locked") is True]
    assert len(locked_tiles) == 2
    assert all(not tile.isEnabled() for tile in locked_tiles)
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
    factory = window.findChild(ResourcesViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    _open_production_selection_for_slot(factory)

    category_filter = factory.findChild(QComboBox, "productionCategoryFilter")
    assert category_filter is not None
    categories = {category_filter.itemText(index) for index in range(category_filter.count())}
    assert {"All", "Ores / Metals", "Minerals"}.issubset(categories)
    assert {"Oil & Gas", "Agriculture", "Forestry"}.isdisjoint(categories)

    installed_id = factory._state.resource_sites["site-1"].slots[0].card_id
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
        ("machine.processor", MachineType.PROCESSOR, {"Steel", "Polymer", "Flour"}, {"Steel Components", "Industrial Equipment"}),
        ("machine.fabricator", MachineType.FABRICATOR, {"Steel Components", "Semiconductor Components", "Battery Components"}, {"Steel", "Industrial Equipment"}),
        ("machine.assembler", MachineType.ASSEMBLER, {"Industrial Equipment", "Microchip", "Packaged Food"}, {"Steel", "Semiconductor Components"}),
    ):
        window = MainWindow()
        factory = window.findChild(FactoryViewV2)
        assert factory is not None
        card = create_card_instance(f"{definition_id}-test", definition_id, CardKind.MACHINE, Rarity.COMMON)
        factory._command_bus.dispatch(AddCard(card))
        factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, card.card_id))
        definition = factory._definitions[definition_id]
        assert isinstance(definition, MachineDefinition)
        factory._state.production_progress.unlocked_production_ids.update(
            option.production_id
            for option in definition.available_production_options
            if option.name in expected_names
        )
        factory.refresh_view()

        _open_production_selection_for_slot(factory)
        assert factory.findChild(QFrame, "productionSelectionView") is not None
        names = set(_production_tile_names(factory))
        assert expected_names.issubset(names)
        assert excluded_names.isdisjoint(names)
        assert definition.machine_type is expected_stage


def test_factory_production_guide_opens_with_search_stage_filter_and_icons() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    button = factory.findChild(FactoryV2CommandButton, "productionGuideButton")
    assert button is not None
    button.clicked.emit()

    view = factory.findChild(QFrame, "productionGuideView")
    assert view is not None
    assert Theme.PRODUCTION_GUIDE_CANVAS in view.styleSheet()
    assert Theme.GUIDE_CHASSIS_MID in view.styleSheet()
    assert Theme.SECONDARY_SHELL_GRADIENT != Theme.PRODUCTION_GUIDE_CANVAS
    title = factory.findChild(QLabel, "productionGuideTitle")
    subtitle = factory.findChild(QLabel, "productionGuideSubtitle")
    assert title is not None and title.text() == "PRODUCTION GUIDE"
    assert subtitle is not None and subtitle.text() == "Browse resources and production chains"
    assert title.font().weight() >= 800
    assert subtitle.font().weight() >= 600
    assert subtitle.font().weight() < title.font().weight()
    assert not factory.findChild(QFrame, "factoryV2Scroll").isVisibleTo(factory)
    scroll = factory.findChild(QScrollArea, "productionGuideScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.widget() is not None
    assert scroll.widget().objectName() == "productionGuideGridHost"
    assert scroll.widget().layout().contentsMargins().left() == 12
    assert factory.findChild(QWidget, "resourceBrowser") is not None
    assert factory.findChild(QScrollArea, "resourceCategoryRail") is not None
    names = {option.name.title() for option in factory._guide_option_index().values()}
    assert {"Iron Ore", "Steel", "Steel Components", "Industrial Robot"}.issubset(names)
    assert all(tile.findChild(ResourceIconWidget, "resourceIcon") is not None for tile in _production_guide_tiles(factory)[:10])
    first_tile = _production_guide_tiles(factory)[0]
    assert first_tile.findChild(QPushButton) is None
    assert first_tile.findChild(ResourceIconWidget, "resourceIcon").width() == RESOURCE_TILE_ICON_SIZE
    assert first_tile.property("stageAccent") in {"extractor", "processor", "fabricator", "assembler"}

    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    assert search is not None
    search.setText("micro")
    visible_names = {
        tile.findChild(QLabel, "productionGuideTileName").text().title()
        for tile in _production_guide_tiles(factory)
        if not tile.isHidden()
    }
    assert "Microchip" in visible_names
    assert "Steel" not in visible_names

    search.setText("")
    stage_filter = factory.findChild(QWidget, "productionGuideStageFilter")
    assert stage_filter is not None
    stage_filter.setCurrentText("Manufacturing")
    visible_names = {
        tile.findChild(QLabel, "productionGuideTileName").text().title()
        for tile in _production_guide_tiles(factory)
        if not tile.isHidden()
    }
    assert "Steel Components" in visible_names
    assert "Steel" not in visible_names


def test_production_guide_only_shows_tiles_owned_by_the_current_grid() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    app.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._open_production_guide()
    app.processEvents()

    host = factory.findChild(QWidget, "productionGuideGridHost")
    assert host is not None
    grid = host.layout()
    tiles = _production_guide_tiles(factory)
    visible = [tile for tile in tiles if not tile.isHidden()]
    assert visible
    assert all(tile.parentWidget() is host and grid.indexOf(tile) >= 0 for tile in visible)

    assert not any(tile.property("resourceId") == "workwear" for tile in tiles)

    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    assert search is not None
    search.setText("Workwear")
    app.processEvents()
    tiles = _production_guide_tiles(factory)
    workwear = next(tile for tile in tiles if tile.property("resourceId") == "workwear")
    visible = [tile for tile in tiles if not tile.isHidden()]
    assert visible == [workwear]
    assert grid.indexOf(workwear) == 0
    assert workwear.parentWidget() is host
    assert workwear.parentWidget() is host

    search.clear()
    app.processEvents()
    assert workwear.isHidden()
    assert grid.indexOf(workwear) == -1
    assert all(
        tile.parentWidget() is host and grid.indexOf(tile) >= 0
        for tile in tiles
        if not tile.isHidden()
    )


def test_factory_production_guide_marks_unlocked_next_and_later_progression() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    record_lifetime_production(
        factory._state,
        {"iron_ore": 120, "coal": 120, "steel": 12},
        factory._definitions,
    )

    factory._open_production_guide()
    factory.findChild(QLineEdit, "productionGuideSearchInput").setText("Industrial Equipment")
    tiles = {
        tile.findChild(QLabel, "productionGuideTileName").text().title(): tile
        for tile in _production_guide_tiles(factory)
    }

    assert tiles["Iron"].property("progressionState") == "unlocked"
    assert tiles["Steel Components"].property("progressionState") == "next"
    requirement = tiles["Steel Components"].findChild(QLabel, "productionGuideUnlock")
    assert requirement is not None
    assert requirement.text() == "STEEL 12 / 100"
    assert tiles["Industrial Equipment"].property("progressionState") == "later"


def test_factory_production_guide_button_opens_closes_and_survives_resize_events() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    for width, height in ((1180, 780), (1440, 900), (980, 720)):
        button = factory.findChild(FactoryV2CommandButton, "productionGuideButton")
        assert button is not None
        button.clicked.emit()
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
        assert factory.findChild(QFrame, "factoryV2Scroll") is not None
        assert not factory.findChild(QFrame, "productionGuideView").isVisible()


def test_factory_production_guide_lifecycle_does_not_spawn_top_level_windows_or_resize_loop() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
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
            if widget not in baseline_top_levels and widget.isVisible() and widget.graphicsProxyWidget() is None
        }
        assert unexpected_visible == set()
        assert {
            widget for widget in current_top_levels
            if widget.isVisible() and widget is not window and widget.graphicsProxyWidget() is None
        } == baseline_visible_top_levels
        assert all(
            not widget.objectName().startswith(("productionGuide", "chainInspector"))
            for widget in current_top_levels
            if widget is not window and widget.graphicsProxyWidget() is None
        )
        assert _visible_extra_top_levels(window) == []
        assert all(not widget.isWindow() for widget in factory.findChildren(QFrame, "productionGuideTile"))
        assert all(tile.parentWidget() is not None for tile in factory.findChildren(QFrame, "productionGuideTile"))
        assert all(
            isinstance(child, ElidedResourceLabel) or child.toolTip() == ""
            for tile in factory.findChildren(QFrame, "productionGuideTile")
            for child in tile.findChildren(QWidget)
        )

    for cycle in range(4):
        button = factory.findChild(FactoryV2CommandButton, "productionGuideButton")
        if button is not None:
            button.clicked.emit()
        else:
            factory._open_production_guide()
        settle_and_assert_stable()

        guide = factory.findChild(QFrame, "productionGuideView")
        assert guide is not None
        search = factory.findChild(QLineEdit, "productionGuideSearchInput")
        stage_filter = factory.findChild(QWidget, "productionGuideStageFilter")
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
        assert "Processing" in _chain_stage_groups(factory)
        chain_back = factory.findChild(QPushButton, "chainInspectorBackButton")
        assert chain_back is not None
        chain_back.click()
        settle_and_assert_stable()
        assert factory.findChild(QFrame, "productionGuideView") is not None

        back = factory.findChild(QPushButton, "productionGuideBackButton")
        assert back is not None
        back.click()
        settle_and_assert_stable()
        assert not factory.findChild(QFrame, "productionGuideView").isVisible()
        assert factory.findChild(QFrame, "chainInspectorView") is None
        assert not any(tile.isVisible() for tile in factory.findChildren(QFrame, "productionGuideTile"))

    assert factory._guide_view_build_count <= 12
    assert factory._guide_grid_rebuild_count <= 80
    assert factory._guide_tile_create_count <= 12000
    assert factory._guide_grid_resize_count < 200
    assert _visible_extra_top_levels(window) == []
    window.close()
    app.processEvents()


def test_factory_production_guide_open_does_not_show_status_labels_as_top_level_windows() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    baseline_top_levels = set(QApplication.topLevelWidgets())
    build_count = factory._guide_view_build_count
    grid_rebuild_count = factory._guide_grid_rebuild_count

    probe = _TopLevelEventProbe()
    app.installEventFilter(probe)
    try:
        button = factory.findChild(FactoryV2CommandButton, "productionGuideButton")
        assert button is not None
        button.clicked.emit()
        QTest.qWait(2200)
        QApplication.processEvents()

        guide = factory.findChild(QFrame, "productionGuideView")
        assert guide is not None
        assert factory._guide_view_build_count == build_count + 1
        assert factory._guide_grid_rebuild_count >= grid_rebuild_count + 1
        guide_identity = id(guide)
        assert _visible_extra_top_levels(window) == []
        assert all(tile.parentWidget() is not None for tile in factory.findChildren(QFrame, "productionGuideTile"))

        _click_production_guide_tile(factory, "Steel")
        QTest.qWait(200)
        QApplication.processEvents()
        used_in_button = factory.findChild(QPushButton, "guideUsedInOpenButton")
        if used_in_button is not None and used_in_button.isEnabled():
            used_in_button.clicked.emit()
            QTest.qWait(200)
            QApplication.processEvents()
            assert factory.findChild(QFrame, "usedInDetailView") is not None

        for width, height in ((1600, 980), (1280, 820), (1920, 1080)):
            window.resize(width, height)
            QTest.qWait(120)
            QApplication.processEvents()
            assert _visible_extra_top_levels(window) == []

        factory._open_production_guide()
        QApplication.processEvents()
        assert id(factory.findChild(QFrame, "productionGuideView")) == guide_identity
    finally:
        app.removeEventFilter(probe)
        window.close()
        app.processEvents()

    unexpected_status_windows = [
        event
        for event in probe.events
        if event[3] == "productionGuideUnlock"
    ]
    assert unexpected_status_windows == []
    assert {
        widget for widget in QApplication.topLevelWidgets()
        if widget not in baseline_top_levels and widget.isVisible()
    } == set()


def test_factory_production_guide_recipe_reflow_never_detaches_visible_rows_to_top_levels() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    assert "setParent(None)" not in inspect.getsource(factory_view_module.GuideRecipeGridHost._apply_columns)
    baseline_top_levels = set(QApplication.topLevelWidgets())

    factory._open_production_guide()
    for _ in range(20):
        app.processEvents()
    guide = factory.findChild(QFrame, "productionGuideView")
    assert guide is not None
    guide_identity = id(guide)
    _click_production_guide_tile(factory, "Steel")
    for _ in range(20):
        app.processEvents()
    chain = factory.findChild(QFrame, "chainInspectorView")
    assert chain is not None
    used_in_button = factory.findChild(QPushButton, "guideUsedInOpenButton")
    if used_in_button is not None and used_in_button.isEnabled():
        used_in_button.click()
        for _ in range(20):
            app.processEvents()
        assert factory.findChild(QFrame, "usedInDetailView") is not None
    for width, height in ((1360, 860), (1180, 760), (1600, 980), (1280, 820)):
        window.resize(width, height)
        for _ in range(24):
            app.processEvents()
        assert {
            widget for widget in QApplication.topLevelWidgets()
            if widget not in baseline_top_levels and widget.isVisible() and widget.graphicsProxyWidget() is None
        } == set()
        assert _visible_extra_top_levels(window) == []
    factory._open_production_guide()
    for _ in range(20):
        app.processEvents()
    assert id(factory.findChild(QFrame, "productionGuideView")) == guide_identity
    idle_guide = factory.findChild(QFrame, "productionGuideView")
    build_count = factory._guide_view_build_count
    grid_rebuild_count = factory._guide_grid_rebuild_count
    for _ in range(120):
        app.processEvents()
    assert factory.findChild(QFrame, "productionGuideView") is idle_guide
    assert factory._guide_view_build_count == build_count
    assert factory._guide_grid_rebuild_count == grid_rebuild_count
    assert _visible_extra_top_levels(window) == []
    window.close()
    app.processEvents()


def test_factory_chain_inspector_handles_extraction_processing_manufacturing_and_assembly_products() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._open_production_guide()

    cases = {
        "Iron Ore": {"Primary Production"},
        "Steel": {"Primary Production", "Processing"},
        "Steel Components": {"Primary Production", "Processing", "Manufacturing"},
        "Industrial Robot": {"Primary Production", "Processing", "Manufacturing", "Assembly"},
    }
    for product_name, expected_stages in cases.items():
        factory._open_production_guide()
        _click_production_guide_tile(factory, product_name)
        assert factory.findChild(QFrame, "chainInspectorView") is not None
        canvas = factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas")
        assert canvas is not None
        assert canvas.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert canvas.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert factory.findChild(QLabel, "chainInspectorNavLabel") is None
        assert factory.findChild(QPushButton, "chainInspectorScrollLeftButton") is None
        assert factory.findChild(QPushButton, "chainInspectorScrollRightButton") is None
        assert canvas.findChild(QFrame, "chainInspectorCanvasControls") is None
        assert canvas.findChild(QPushButton, "chainInspectorFitButton") is None
        assert canvas.findChild(QPushButton, "chainInspectorZoomOutButton") is None
        assert canvas.findChild(QPushButton, "chainInspectorZoomInButton") is None
        assert canvas.findChild(QLabel, "chainInspectorZoomLabel") is None
        assert set(_chain_stage_groups(factory)) == expected_stages
        assert _chain_stage_order(factory) == [
            stage for stage in ["Primary Production", "Processing", "Manufacturing", "Assembly"]
            if stage in expected_stages
        ]
        back = factory.findChild(QPushButton, "chainInspectorBackButton")
        assert back is not None
        assert back.property("primaryNavigation") is True
        assert factory.findChild(QLabel, "chainInspectorScrollHint") is None
        assert factory.findChild(QFrame, "chainSummaryRateBlock") is not None
        assert factory.findChild(QLabel, "chainSummaryRateValue") is not None
        assert factory.findChild(QLabel, "chainSummaryProgression") is None
        back.click()
        assert factory.findChild(QFrame, "productionGuideView") is not None


def test_factory_chain_inspector_shows_multi_input_chain_and_machine_families() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Microchip")

    groups = _chain_stage_groups(factory)
    content = _chain_canvas_content(factory)
    assert {"Primary Production", "Processing", "Manufacturing", "Assembly"}.issubset(set(groups))
    connectors = content.findChildren(QFrame, "chainFlowConnector")
    assert connectors
    assert all(connector.width() >= 30 for connector in connectors)
    assert all(connector.width() == 30 for connector in connectors)
    ordered_groups = sorted(groups.values(), key=lambda group: group.mapTo(content, QPoint()).x())
    ordered_connectors = sorted(connectors, key=lambda connector: connector.mapTo(content, QPoint()).x())
    assert len(ordered_connectors) == len(ordered_groups) - 1
    vertical_routes = []
    for source, connector, destination in zip(ordered_groups, ordered_connectors, ordered_groups[1:]):
        source_right = source.mapTo(content, source.rect().topRight()).x()
        destination_left = destination.mapTo(content, destination.rect().topLeft()).x()
        connector_center = connector.mapTo(content, connector.rect().center()).x()
        assert connector_center == pytest.approx((source_right + destination_left) / 2, abs=1)
        source_bounds = connector._node_group_bounds(source)
        destination_bounds = connector._node_group_bounds(destination)
        points = connector.connection_points()
        assert source_bounds is not None and destination_bounds is not None
        assert points[0].y() == pytest.approx(source_bounds.center().y(), abs=1)
        assert points[-1].y() == pytest.approx(destination_bounds.center().y(), abs=1)
        vertical_routes.append((points[0].y(), points[-1].y()))
    assert all(source_y != destination_y for source_y, destination_y in vertical_routes)
    assert len(set(vertical_routes)) == len(vertical_routes)
    for group in ordered_groups:
        title = group.findChild(QLabel, "chainStageTitle")
        node = group.findChild(QFrame, "chainResourceBox")
        assert title is not None and node is not None
        assert title.parentWidget() is node.parentWidget()
        assert title.mapTo(group, QPoint()).x() == node.mapTo(group, QPoint()).x()
    extraction_names = _chain_resource_names(groups["Primary Production"])
    assert {"Quartz", "Copper Ore", "Gold Ore"}.issubset(extraction_names)
    assert "High-Purity Silicon" in _chain_resource_names(groups["Processing"])
    assert "Semiconductor Components" in _chain_resource_names(groups["Manufacturing"])
    assert "Microchip" in _chain_resource_names(groups["Assembly"])

    families = {
        label.text()
        for label in content.findChildren(QLabel, "chainMachineFamily")
    }
    assert {"Extractor", "Processor", "Fabricator", "Assembler"}.issubset(families)
    input_labels = [
        button.text()
        for button in content.findChildren(QPushButton, "guideRecipeInputLink")
        if button.property("chainNodeInput") is True
    ]
    amount_labels = [label.text() for label in content.findChildren(QLabel, "chainResourceAmount")]
    assert input_labels
    assert all("INPUT" not in text and "/ cycle" not in text.lower() for text in input_labels)
    assert all("OUTPUT" not in text and text.endswith(" / CYCLE") for text in amount_labels)
    resource_boxes = content.findChildren(QFrame, "chainResourceBox")
    assert len({box.width() for box in resource_boxes}) == 1
    assert all(box.minimumWidth() == 264 for box in resource_boxes)
    target_nodes = [
        node
        for node in content.findChildren(QFrame, "chainResourceBox")
        if node.property("target") is True
    ]
    assert any(node.findChild(QLabel, "chainResourceName").text() == "Microchip" for node in target_nodes)


def test_factory_chain_inspector_unified_canvas_fits_zooms_and_pans() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 980)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    previous_canvas = None
    for resource_id in ("iron_ore", "steel", "microchip"):
        factory._open_chain_from_guide(resource_id)
        for _ in range(4):
            QApplication.processEvents()
        canvas = factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas")
        assert canvas is not None and canvas is not previous_canvas
        previous_canvas = canvas
        assert canvas.minimum_zoom <= canvas.zoom_factor <= 1.0
        assert canvas.fit_call_count >= 1
        content = canvas.content_widget
        assert content is not None
        assert not content.findChildren(QScrollArea)
        groups = content.findChildren(QWidget, "chainStageGroup")
        assert groups
        assert not content.findChildren(QFrame, "chainStagePanel")
        assert all(group.minimumWidth() == 264 for group in groups)
        assert all(box.width() >= 264 for box in content.findChildren(QFrame, "chainResourceBox"))

        fitted_zoom = canvas.zoom_factor
        canvas.zoom_by_steps(1)
        assert canvas.zoom_factor > fitted_zoom
        if resource_id == "microchip":
            canvas.set_zoom(canvas.maximum_zoom)
            center_before = canvas.mapToScene(canvas.viewport().rect().center())
            canvas.pan_by(QPointF(35, 20))
            center_after = canvas.mapToScene(canvas.viewport().rect().center())
            assert center_after != center_before
        canvas.fit_to_view()
        assert canvas.zoom_factor == pytest.approx(fitted_zoom, abs=0.02)

    canvas.set_zoom(99.0)
    assert canvas.zoom_factor == canvas.maximum_zoom
    canvas.set_zoom(0.01)
    assert canvas.zoom_factor == canvas.minimum_zoom
    window.close()


def test_factory_chain_inspector_processed_food_scene_is_complete_and_wheel_zoomable() -> None:
    _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._open_chain_from_guide("processed_food")
    for _ in range(8):
        QApplication.processEvents()

    canvas = factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas")
    assert canvas is not None
    content = canvas.content_widget
    assert content is not None
    assert [group.property("stage") for group in content.findChildren(QWidget, "chainStageGroup")] == [
        "Primary Production",
        "Processing",
        "Manufacturing",
        "Assembly",
    ]
    expected_nodes = sum(len(nodes) for nodes in factory._build_chain("processed_food").values())
    assert len(content.findChildren(QFrame, "chainResourceBox")) == expected_nodes
    item_rect = canvas.mapFromScene(canvas.scene().itemsBoundingRect()).boundingRect()
    assert canvas.viewport().rect().contains(item_rect)
    assert not content.findChildren(QScrollArea)

    before = canvas.zoom_factor
    wheel = QWheelEvent(
        QPointF(180, 120),
        QPointF(180, 120),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )
    canvas.wheelEvent(wheel)
    assert canvas.zoom_factor > before
    canvas.zoom_by_steps(-1)
    assert canvas.zoom_factor == pytest.approx(before, abs=0.01)
    canvas.zoom_by_steps(1)
    assert canvas.zoom_factor > before
    canvas.fit_to_view()
    assert canvas.zoom_factor == pytest.approx(before, abs=0.01)
    window.close()


def test_factory_chain_inspector_shows_compact_used_in_summary_with_count() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    factory._open_chain_from_guide("steel")
    assert factory.findChild(QFrame, "guideUsedInSummary") is None
    count = len(factory._guide_recipe_index.used_in("steel"))
    action = factory.findChild(QPushButton, "guideUsedInOpenButton")
    assert action.text() == f"USED IN\n{count} {'PRODUCT' if count == 1 else 'PRODUCTS'}  >"
    action.click()
    assert factory.findChild(QFrame, "usedInDetailView") is not None
    window.close()


def test_factory_chain_inspector_uses_compact_scrollable_recipe_sections() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    factory._open_chain_from_guide("steel_components")
    details = factory.findChild(QFrame, "guideRecipeDetails")
    assert details is not None
    assert details.property("chainSummary") is True
    assert details.findChild(QLabel, "chainSummaryProductName").text() == "STEEL COMPONENTS"
    assert details.findChild(QLabel, "chainSummaryMachineFamily").text() == "FABRICATOR"
    assert details.findChild(QLabel, "chainSummaryRateLabel").text() == "PRODUCTION RATE"
    assert " · " in details.findChild(QLabel, "chainSummaryRateValue").text()
    assert details.findChild(QLabel, "chainSummaryProgression") is None
    rate_label = details.findChild(QLabel, "chainSummaryRateLabel")
    rate_value = details.findChild(QLabel, "chainSummaryRateValue")
    rate_label.ensurePolished()
    rate_value.ensurePolished()
    assert rate_label.font().weight() == QFont.Weight.Black
    assert rate_label.font().pixelSize() == 11
    assert rate_value.font().weight() == QFont.Weight.Black
    assert rate_value.font().pixelSize() == 16
    assert not details.findChildren(QFrame, "guideRecipeRow")
    assert details.findChild(QLabel, "guideRecipeInputEmpty") is None
    assert factory.findChild(QFrame, "guideRecipeSection") is None
    assert details.findChild(QPushButton, "guideUsedInOpenButton") is not None
    assert factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas").minimumHeight() >= 190
    window.close()


def test_factory_chain_inspector_compact_content_preserves_runtime_rates_and_inputs() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_chain_from_guide("copper_ore")
    assert factory.findChild(QLabel, "chainSummaryProductName").text() == "COPPER ORE"
    assert factory.findChild(QLabel, "chainSummaryMachineFamily").text() == "EXTRACTOR"
    assert factory.findChild(QLabel, "chainSummaryRateValue").text() == "12 / 6s  ·  120 / MIN"
    content = _chain_canvas_content(factory)
    assert content.findChild(QFrame, "chainResourceInputs") is None
    assert content.findChild(QLabel, "chainResourceAmount").text() == "12 / CYCLE"
    assert factory.findChild(QLabel, "guideRecipeInputEmpty") is None

    factory._open_chain_from_guide("vanadium_alloy")
    assert factory.findChild(QLabel, "chainSummaryProductName").text() == "VANADIUM ALLOY"
    assert factory.findChild(QLabel, "chainSummaryMachineFamily").text() == "PROCESSOR"
    assert factory.findChild(QLabel, "chainSummaryRateValue").text() == "9 / 6s  ·  90 / MIN"
    content = _chain_canvas_content(factory)
    target = next(
        node
        for node in content.findChildren(QFrame, "chainResourceBox")
        if node.property("target") is True
    )
    assert [
        button.text()
        for button in target.findChildren(QPushButton, "guideRecipeInputLink")
    ] == [
        "12 Vanadium Ore",
        "12 Iron Ore",
    ]
    assert target.findChild(QLabel, "chainResourceAmount").text() == "9 / CYCLE"
    window.close()


def test_factory_used_in_detail_grid_uses_responsive_columns_and_row_major_flow() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Copper")

    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()

    detail = factory.findChild(QFrame, "usedInDetailView")
    assert detail is not None
    content = detail.findChild(QWidget, "usedInDetailGridHost")
    assert content is not None
    content.resize(850, content.sizeHint().height())
    QApplication.sendEvent(content, QResizeEvent(QSize(850, content.height()), content.size()))
    QApplication.processEvents()

    rows = detail.findChildren(QFrame, "guideRecipeRow")
    assert len(rows) >= 4
    assert content.property("guideRecipeColumns") == 3
    grid = content.layout()
    assert grid.itemAtPosition(0, 0).widget() is rows[0]
    assert grid.itemAtPosition(0, 1).widget() is rows[1]
    assert grid.itemAtPosition(0, 2).widget() is rows[2]
    assert grid.itemAtPosition(1, 0).widget() is rows[3]

    scroll = detail.findChild(QScrollArea, "usedInDetailScroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    window.close()


def test_factory_used_in_detail_grid_falls_back_to_one_column_when_narrow() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Copper")
    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()

    detail = factory.findChild(QFrame, "usedInDetailView")
    assert detail is not None
    content = detail.findChild(QWidget, "usedInDetailGridHost")
    assert content is not None
    content.resize(230, content.sizeHint().height())
    QApplication.sendEvent(content, QResizeEvent(QSize(230, content.height()), content.size()))
    QApplication.processEvents()

    rows = detail.findChildren(QFrame, "guideRecipeRow")
    assert rows
    assert content.property("guideRecipeColumns") == 1
    grid = content.layout()
    assert grid.itemAtPosition(0, 0).widget() is rows[0]
    assert grid.itemAtPosition(0, 1) is None
    assert grid.itemAtPosition(1, 0).widget() is rows[1]
    window.close()


def test_factory_used_in_detail_sparse_rows_are_left_aligned_without_resizing() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 860)
    window.show()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    for resource_id, expected_count in (("bauxite", 1), ("limestone", 2), ("iron", 3)):
        factory._open_chain_from_guide(resource_id)
        QApplication.processEvents()
        factory.findChild(QPushButton, "guideUsedInOpenButton").click()
        QApplication.processEvents()

        detail = factory.findChild(QFrame, "usedInDetailView")
        assert detail is not None
        content = detail.findChild(QWidget, "usedInDetailGridHost")
        assert content is not None
        if content.layout() is not None:
            content.layout().activate()
        QApplication.processEvents()

        rows = detail.findChildren(QFrame, "guideRecipeRow")
        assert len(rows) == expected_count
        assert all(row.maximumHeight() == 208 for row in rows)
        ordered = sorted(rows, key=lambda row: (row.y(), row.x()))
        left = ordered[0].mapTo(content, ordered[0].rect().topLeft()).x()
        assert left == content.layout().contentsMargins().left()
        assert content.layout().itemAtPosition(0, 0).widget() is ordered[0]
        assert all(row.width() == 268 for row in rows)
        columns = content.property("guideRecipeColumns")
        assert all(row.x() == (index % columns) * 282 for index, row in enumerate(ordered))
        assert all(row.y() == (index // columns) * 222 for index, row in enumerate(ordered))

    window.close()


def test_factory_chain_inspector_used_in_summary_zero_state_is_compact() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    factory._open_chain_from_guide("high_speed_network_system")
    action = factory.findChild(QPushButton, "guideUsedInOpenButton")
    assert action.text() == "USED IN\n0 PRODUCTS  >"
    action.click()
    assert factory.findChild(QLabel, "emptyStateTitle").text() == "NO DOWNSTREAM PRODUCTS"
    window.close()


def test_factory_used_in_detail_back_returns_to_same_chain_inspector() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Steel Components")
    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()

    assert factory.findChild(QFrame, "usedInDetailView") is not None
    back = factory.findChild(QPushButton, "usedInBackButton")
    assert back is not None
    back.click()
    QApplication.processEvents()

    assert factory.findChild(QFrame, "usedInDetailView") is None
    inspector = factory.findChild(QFrame, "chainInspectorView")
    assert inspector is not None
    title = next(label for label in factory.findChildren(QLabel, "sectionLabel") if "CHAIN INSPECTOR" in label.text())
    assert "STEEL COMPONENTS" in title.text()
    assert factory._chain_resource_id == "steel_components"
    window.close()


def test_factory_used_in_navigation_preserves_guide_filter_state_and_scroll() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    stage_filter = factory.findChild(QWidget, "productionGuideStageFilter")
    category_filter = factory.findChild(QComboBox, "productionGuideCategoryFilter")
    scroll = factory.findChild(QScrollArea, "productionGuideScroll")
    assert search is not None
    assert stage_filter is not None
    assert category_filter is not None
    assert scroll is not None
    search.setText("steel")
    stage_filter.setCurrentText("All")
    category_filter.setCurrentText("All")
    scroll.verticalScrollBar().setValue(3)
    expected_scroll = scroll.verticalScrollBar().value()

    _click_production_guide_tile(factory, "Steel Components")
    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()
    factory.findChild(QPushButton, "usedInBackButton").click()
    QApplication.processEvents()
    chain_back = factory.findChild(QPushButton, "chainInspectorBackButton")
    assert chain_back is not None
    chain_back.click()
    QApplication.processEvents()

    restored_search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    restored_stage = factory.findChild(QWidget, "productionGuideStageFilter")
    restored_category = factory.findChild(QComboBox, "productionGuideCategoryFilter")
    restored_scroll = factory.findChild(QScrollArea, "productionGuideScroll")
    assert restored_search is not None
    assert restored_stage is not None
    assert restored_category is not None
    assert restored_scroll is not None
    assert restored_search.text() == "steel"
    assert restored_stage.currentText() == "All"
    assert restored_category.currentText() == "All"
    assert restored_scroll.verticalScrollBar().value() == min(expected_scroll, restored_scroll.verticalScrollBar().maximum())
    window.close()


def test_factory_used_in_detail_link_navigates_to_target_chain_inspector() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Steel Components")
    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()
    before_builds = factory._guide_option_index_build_count
    link = next(
        button
        for button in factory.findChildren(QPushButton, "guideRecipeLink")
        if button.text() == "Industrial Equipment"
    )
    link.click()
    QApplication.processEvents()

    title = next(label for label in factory.findChildren(QLabel, "sectionLabel") if "CHAIN INSPECTOR" in label.text())
    assert "INDUSTRIAL EQUIPMENT" in title.text()
    assert factory._chain_resource_id == "industrial_equipment"
    assert factory._guide_option_index_build_count == before_builds
    assert factory.findChild(QFrame, "usedInDetailView") is None
    assert factory.findChild(QFrame, "chainInspectorView") is not None


def test_factory_v2_open_used_in_real_player_navigation_stays_on_detail_view() -> None:
    _app()
    state = GameState(rng_seed=42)
    state.halls["hall-1"] = FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    bus = CommandBus(state)
    factory = FactoryViewV2(state, bus, definitions)
    factory.resize(1320, 820)
    factory.show()
    QApplication.processEvents()

    guide_button = factory.findChild(QWidget, "productionGuideButton")
    assert guide_button is not None
    QTest.mouseClick(guide_button, Qt.MouseButton.LeftButton)
    QApplication.processEvents()

    assert factory.findChild(QFrame, "productionGuideView") is not None
    _click_production_guide_tile(factory, "Steel Components")
    QApplication.processEvents()

    inspector = factory.findChild(QFrame, "chainInspectorView")
    assert inspector is not None
    assert not factory.findChild(QFrame, "factoryV2Board").isVisibleTo(factory)

    open_button = factory.findChild(QPushButton, "guideUsedInOpenButton")
    assert open_button is not None and open_button.isEnabled()
    open_button.click()
    QApplication.processEvents()
    factory.refresh_view()
    QApplication.processEvents()

    detail = factory.findChild(QFrame, "usedInDetailView")
    assert detail is not None and detail.isVisible()
    assert not factory.findChild(QFrame, "factoryV2Board").isVisibleTo(factory)
    assert factory.findChild(QFrame, "chainInspectorView") is None
    rows = detail.findChildren(QFrame, "guideRecipeRow")
    assert rows

    target = rows[0]
    target.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    QApplication.processEvents()

    assert factory.findChild(QFrame, "usedInDetailView") is None
    assert factory.findChild(QFrame, "chainInspectorView") is not None
    assert not factory.findChild(QFrame, "factoryV2Board").isVisibleTo(factory)
    factory.close()


def test_factory_used_in_detail_row_click_navigates_to_target_chain_inspector() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Steel Components")
    factory.findChild(QPushButton, "guideUsedInOpenButton").click()
    QApplication.processEvents()
    before_builds = factory._guide_option_index_build_count
    row = next(
        row
        for row in factory.findChildren(QFrame, "guideRecipeRow")
        if row.property("resourceId") == "industrial_equipment"
    )
    assert row.cursor().shape() == Qt.CursorShape.PointingHandCursor
    row.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    QApplication.processEvents()

    title = next(label for label in factory.findChildren(QLabel, "sectionLabel") if "CHAIN INSPECTOR" in label.text())
    assert "INDUSTRIAL EQUIPMENT" in title.text()
    assert factory._chain_resource_id == "industrial_equipment"
    assert factory._guide_option_index_build_count == before_builds
    assert factory.findChild(QFrame, "usedInDetailView") is None


def test_factory_chain_inspector_input_link_navigates_to_input_product() -> None:
    _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._open_production_guide()
    _click_production_guide_tile(factory, "Microchip")
    content = _chain_canvas_content(factory)
    link = next(
        button
        for button in content.findChildren(QPushButton, "guideRecipeInputLink")
        if button.property("resourceId") == "semiconductor_components"
    )
    canvas = factory.findChild(ZoomPanGraphicsView, "chainInspectorCanvas")
    content_point = link.mapTo(content, link.rect().center())
    scene_point = canvas._proxy.mapToScene(QPointF(content_point))
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, pos=canvas.mapFromScene(scene_point))
    QApplication.processEvents()

    title = next(label for label in factory.findChildren(QLabel, "sectionLabel") if "CHAIN INSPECTOR" in label.text())
    assert "SEMICONDUCTOR COMPONENTS" in title.text()
    assert factory._chain_resource_id == "semiconductor_components"


def test_factory_direct_hall_chain_navigation_preserves_production_selection_flow() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(ResourcesViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._set_resources_drawer_open(True)
    item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    item.findChild(QPushButton, "chainInfoButton").click()
    assert factory.findChild(QFrame, "chainInspectorView") is not None
    back = factory.findChild(QPushButton, "chainInspectorBackButton")
    assert back is not None
    back.click()
    assert factory.findChild(QFrame, "factoryV2Scroll") is not None

    _open_production_selection_for_slot(factory)
    assert factory.findChild(QFrame, "productionSelectionView") is not None


def test_factory_hall_resource_summary_opens_chain_inspector_directly() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

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
    assert factory.findChild(QFrame, "factoryV2Scroll") is not None


def test_factory_runtime_tick_keeps_production_guide_and_chain_state() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
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
    factory = window.findChild(ResourcesViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._command_bus.dispatch(InstallCardInHall("plant-1", 0, "test-solar-common-001", "energy"))
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
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    old_kpi = factory._kpi_strip
    assert old_kpi is not None
    factory.refresh_view()
    _flush_deferred_deletes()

    assert factory._kpi_strip is old_kpi and is_qt_object_valid(old_kpi)
    # A genuinely changed board frame must still reconnect all runtime refs.
    factory._units[factory._selected_hall_id].name = "Changed structural frame"
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
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._on_slot_clicked(0)
    _flush_deferred_deletes()
    assert factory._kpi_strip is None or is_qt_object_valid(factory._kpi_strip)
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._close_drawer()
    _flush_deferred_deletes()
    assert factory._kpi_strip is not None
    assert is_qt_object_valid(factory._kpi_strip)

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Processor")
    _open_production_selection_for_slot(factory)
    _flush_deferred_deletes()
    assert factory._kpi_strip is None or is_qt_object_valid(factory._kpi_strip)
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._close_drawer()
    factory._command_bus.dispatch(AddCash(15_200))
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
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._unlock_slot("hall-1.line-1")
    _flush_deferred_deletes()
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)

    factory._unlock_line("hall-1.line-2")
    _flush_deferred_deletes()
    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()
    _assert_factory_runtime_refs_valid(factory)


def test_factory_resource_summary_updates_amount_and_storage_bar_without_rebuild() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory._command_bus.dispatch(SetResourceCapacity("iron_ore", 500))
    factory._state.resources["iron_ore"].amount = 157
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

    item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    amount = item.findChild(QLabel, "hallResourceAmount")
    progress = item.findChild(QProgressBar, "hallResourceStorageProgress")
    assert amount is not None
    assert progress is not None

    factory._state.resources["iron_ore"].amount = 169
    factory._refresh_runtime_widgets()

    same_item = next(item for item in factory.findChildren(QFrame, "hallResourceSummaryItem") if item.property("resourceId") == "iron_ore")
    assert same_item is item
    assert amount.text() == "169 STORED"
    assert progress.value() == round(factory._state.used_storage / factory._state.storage_capacity * 1000)
    assert item.property("previousAmount") == 157
    assert item.property("targetAmount") == 169
    assert item.property("amountTransitionMs") == 220


def test_factory_resource_summary_uses_clean_non_black_inner_surfaces() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

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


def test_shared_navigation_and_button_states_use_distinct_surfaces() -> None:
    assert Theme.SURFACE_0 != Theme.SURFACE_1 != Theme.SURFACE_2 != Theme.SURFACE_3
    assert Theme.SURFACE_INTERACTIVE != Theme.SURFACE_HOVER
    selected_tab_block = _style_block("QTabBar::tab:selected")
    assert Theme.SAFETY_YELLOW in selected_tab_block
    assert "border-color: rgba(7, 8, 7, 230);" in selected_tab_block
    hover_tab_block = _style_block("QTabBar::tab:hover")
    assert "background: qlineargradient" in hover_tab_block
    assert "border-color: rgba(255, 210, 31, 112);" in hover_tab_block
    assert "QPushButton:disabled" in APP_STYLESHEET


def test_selection_interfaces_use_factory_freight_industrial_styles() -> None:
    selection_shell_selector = "QFrame#factoryCardSelectionView, QFrame#productionSelectionView, QFrame#productionSelectionDrawer, QFrame#productionGuideView, QFrame#freightCardSelectionView, QFrame#freightAssignmentSelectionView"
    selection_scroll_selector = "QScrollArea#factoryCardSelectionScroll, QScrollArea#productionSelectionScroll, QScrollArea#productionGuideScroll, QScrollArea#freightCardSelectionScroll, QScrollArea#freightAssignmentResourceScroll"
    search_selector = "QLineEdit#cardSearchInput, QLineEdit#productionSearchInput, QLineEdit#productionGuideSearchInput, QLineEdit#freightCardSearch, QLineEdit#freightAssignmentSearch, QLineEdit#supplySearch, QLineEdit#chartResourceSearch, QLineEdit#marketSearch"

    assert "background: qlineargradient" in _style_block(selection_shell_selector)
    assert "rgba(8, 12, 12, 116)" in _style_block(selection_scroll_selector)
    assert "rgba(6, 9, 9, 178)" in _style_block(search_selector)
    assert "selection-background-color: rgba(255, 210, 31, 70);" in _style_block(search_selector)
    assert "QLineEdit#supplySearch:focus" in APP_STYLESHEET
    assert "QLineEdit#chartResourceSearch:focus" in APP_STYLESHEET
    assert "QLineEdit#marketSearch:focus" in APP_STYLESHEET
    assert "background: qlineargradient" in _style_block("QFrame#freightSelectionFilters, QFrame#productionGuideFilters")
    assert "QFrame#productionSelectionTile[stageAccent=\"processor\"]" in APP_STYLESHEET
    assert "QFrame#productionSelectionTile[current=\"true\"]" in APP_STYLESHEET
    assert "QFrame#productionGuideTile:hover, QFrame#productionGuideTile:focus" in APP_STYLESHEET
    assert "QFrame#chainInspectorView" in APP_STYLESHEET
    assert "QGraphicsView#chainInspectorCanvas" in APP_STYLESHEET
    assert "QScrollArea#guideRecipeSectionScroll" in APP_STYLESHEET
    assert "QFrame#freightAssignmentResourceTile[selected=\"true\"]" in APP_STYLESHEET
    assert "QComboBox#contractProductSelect" in APP_STYLESHEET
    assert "QScrollBar::handle:vertical:hover" in APP_STYLESHEET


def test_selector_surfaces_use_light_readable_labels_and_shared_filter_row() -> None:
    light_label_selector = (
        "QFrame#factoryCardSelectionView QLabel#sectionLabel,\n"
        "QFrame#productionSelectionView QLabel#sectionLabel,\n"
        "QFrame#productionGuideView QLabel#sectionLabel,\n"
        "QFrame#freightCardSelectionView QLabel#sectionLabel,\n"
        "QFrame#freightAssignmentSelectionView QLabel#sectionLabel,\n"
        "QWidget#supplyCommonPage QLabel#sectionLabel,\n"
        "QWidget#supplyDailyPage QLabel#sectionLabel"
    )
    light_label_style = _style_block(light_label_selector)
    chart_chip = _style_block("QPushButton#chartFilterChip")
    chart_active_chip = _style_block('QPushButton#chartFilterChip[active="true"]')
    supply_chip = _style_block("QPushButton#supplyFilterChip")
    supply_active_chip = _style_block('QPushButton#supplyFilterChip[active="true"]')
    freight_target = _style_block("QLabel#freightSelectionTarget")

    assert Theme.TEXT_ON_LIGHT_PRIMARY in light_label_style
    assert Theme.TEXT_ON_LIGHT_SECONDARY in freight_target
    assert Theme.FILTER_INACTIVE_TEXT in chart_chip
    assert Theme.FILTER_ACTIVE_TEXT in chart_active_chip
    assert Theme.FILTER_INACTIVE_TEXT in supply_chip
    assert Theme.FILTER_ACTIVE_TEXT in supply_active_chip
    resource_selector_panel = _style_block("QFrame#resourceSelectorFilterPanel")
    resource_selector_search = _style_block("QFrame#resourceSelectorFilterPanel QLineEdit")
    resource_selector_combo = _style_block("QFrame#resourceSelectorFilterPanel QComboBox")

    assert "ResourceBrowser" in inspect.getsource(factory_view_module.FactoryViewBase._build_production_selection_view)
    assert "ResourceBrowser" in inspect.getsource(FreightView._build_assignment_resource_picker)
    assert "freightSelectionFilters" not in inspect.getsource(FreightView._build_assignment_resource_picker)
    assert "background: qlineargradient" in resource_selector_panel
    assert Theme.TEXT_ON_LIGHT_PRIMARY in resource_selector_search
    assert Theme.TEXT_ON_LIGHT_PRIMARY in resource_selector_combo


def test_factory_resource_selection_selected_tile_keeps_dark_industrial_surface() -> None:
    selected_tile = _style_block('QFrame#productionSelectionTile[current="true"], QFrame#freightAssignmentResourceTile[selected="true"], QFrame#resourceSelectionTile[selected="true"]')
    assert "rgba(255, 210, 31, 24)" not in selected_tile
    assert "rgba(24, 34, 35, 238)" in selected_tile
    assert "border: 2px solid rgba(255, 210, 31, 202)" in selected_tile


def test_factory_v2_resources_overlay_uses_darker_translucent_chassis() -> None:
    assert "opacity_boost: int = 0" in inspect.getsource(factory_rendering_module.draw_utility_chassis)
    assert "opacity_boost=28" in inspect.getsource(FactoryV2ResourceDrawer.paintEvent)


def test_selector_dropdown_surfaces_use_shared_industrial_popup_styles() -> None:
    market_selector = _style_block("QPushButton#marketCategorySelectorButton, QPushButton#marketEventSelectorButton, QPushButton#marketTrendSelectorButton, QPushButton#marketSortSelectorButton")
    supply_selector = _style_block("QPushButton#supplyMachineSelector, QPushButton#supplySortSelector")
    shared_flyout = _style_block("QFrame#marketSelectorFlyout, QFrame#supplySelectorFlyout")
    shared_option = _style_block("QPushButton#marketSelectorOption, QPushButton#supplySelectorOption")
    shared_hover = _style_block("QPushButton#marketSelectorOption:hover, QPushButton#supplySelectorOption:hover")
    shared_active = _style_block('QPushButton#marketSelectorOption[active="true"], QPushButton#supplySelectorOption[active="true"]')
    combo_popup = _style_block("QComboBox QAbstractItemView")
    pack_flyout = _style_block("QFrame#packCategoryFlyout")
    pack_active = _style_block('QPushButton#packCategoryOption[active="true"]')

    assert "background: rgba(8, 12, 13" in market_selector
    assert Theme.TEXT in market_selector
    assert "background: rgba(8, 12, 13" in supply_selector
    assert "background: rgba(7, 10, 10, 248)" in shared_flyout
    assert "border: 1px solid rgba(159, 178, 173" in shared_flyout
    assert "background: rgba(16, 22, 22, 232)" in shared_option
    assert "border-color: rgba(37, 185, 232" in shared_hover
    assert "background: rgba(255, 210, 31, 212)" in shared_active
    assert "outline: 0" in combo_popup
    assert "selection-color: #15120a" in combo_popup
    assert "background: rgba(7, 10, 10, 248)" in pack_flyout
    assert "background: rgba(177, 135, 255, 188)" in pack_active


def test_chain_inspector_surfaces_and_used_in_action_use_final_polish_styles() -> None:
    header = _style_block("QFrame#productionGuideHeader, QFrame#chainInspectorHeader, QFrame#usedInDetailHeader")
    title = _style_block("QFrame#productionGuideView QLabel#sectionLabel,\nQFrame#chainInspectorView QLabel#sectionLabel,\nQFrame#usedInDetailView QLabel#sectionLabel")
    chain_canvas = _style_block("QGraphicsView#chainInspectorCanvas")
    recipe_section = _style_block("QFrame#guideRecipeSection")
    used_in_summary = _style_block("QFrame#guideUsedInSummary, QFrame#usedInIdentity")
    used_in_action = _style_block("QPushButton#guideUsedInOpenButton")
    used_in_hover = _style_block("QPushButton#guideUsedInOpenButton:hover")
    used_in_pressed = _style_block("QPushButton#guideUsedInOpenButton:pressed")
    used_in_back = _style_block("QPushButton#usedInBackButton")
    next_tile = _style_block('QFrame#productionGuideTile[progressionState="next"]')
    locked_tile = _style_block('QFrame#productionGuideTile[progressionState="later"]')
    next_unlock = _style_block('QLabel#productionGuideUnlock[progressionState="next"]')

    assert "rgba(255, 210, 31, 96)" in header
    assert "font-size: 28px" in title
    assert "rgba(5, 8, 8, 205)" in chain_canvas
    assert "QFrame#chainStagePanel" not in APP_STYLESHEET
    assert "QFrame#chainStageRule" not in APP_STYLESHEET
    assert "rgba(8, 12, 12, 202)" in recipe_section
    assert "223, 107, 47" in used_in_summary
    assert Theme.SAFETY_YELLOW in used_in_action
    assert "color: #11130b;" in used_in_action
    assert "#fff097" in used_in_hover
    assert "#c7960d" in used_in_pressed
    assert Theme.SAFETY_YELLOW not in used_in_back
    assert "223, 107, 47" in next_tile
    assert "rgba(13, 18, 20, 154)" in locked_tile
    assert "255, 210, 31" in next_unlock


def test_global_ui_consistency_pass_styles_remaining_secondary_views() -> None:
    packs_header = _style_block("QFrame#packsHeader")
    packs_metric = _style_block("QFrame#packsHeaderMetric")
    packs_scroll = _style_block("QScrollArea#boosterPackScroll, QWidget#packsPage QWidget#packsCanvasViewport")
    pack_result_scroll = _style_block("QScrollArea#packResultScroll")
    leaderboard_chip = _style_block("QPushButton#leaderboardMetricChip")
    leaderboard_active_chip = _style_block("QPushButton#leaderboardMetricChip[active=\"true\"]")
    leaderboard_row = _style_block("QFrame#leaderboardRow")

    assert "background: transparent" in packs_header
    assert "border: 0" in packs_header
    assert "background: qlineargradient" in packs_metric
    assert "background: transparent" in packs_scroll
    assert "border: 0" in packs_scroll
    assert "background: qlineargradient" in pack_result_scroll
    assert "border: 1px solid" in pack_result_scroll
    assert "QWidget#boosterPackGrid, QWidget#packResultGrid" in APP_STYLESHEET
    assert "font-family:" in leaderboard_chip
    assert "background: qlineargradient" in leaderboard_chip
    assert Theme.SAFETY_YELLOW in leaderboard_active_chip
    assert "background: qlineargradient" in leaderboard_row


def test_ui_contact_sheet_tool_captures_refreshed_tabs_at_supported_sizes() -> None:
    from production_zero.tools import ui_contact_sheet

    labels = {size_label for size_label, _width, _height in ui_contact_sheet.WINDOW_SIZES}
    assert {"narrow", "default", "large"} <= labels
    assert all(width >= 1280 and height >= 820 for _size_label, width, height in ui_contact_sheet.WINDOW_SIZES)
    assert ui_contact_sheet.CONTACT_SHEET_DIR.name == "ui_contact_sheets"
    assert ui_contact_sheet.NATIVE_DIR.name == "ui_native_screens"

    font_loader_source = inspect.getsource(ui_contact_sheet._load_qa_fonts)
    capture_source = inspect.getsource(ui_contact_sheet._capture_tabs)
    assert "QFontDatabase.addApplicationFont" in font_loader_source
    assert 'hasattr(current, "refresh")' in capture_source
    assert "_drain_events(app)" in capture_source
    assert "native_size_dir" in capture_source




def test_factory_fifty_card_hall_runtime_update_keeps_widgets_stable() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._command_bus.dispatch(AddCash(100_000))
    hall = factory._state.halls["hall-1"]
    for line in hall.production_lines:
        if not line.unlocked:
            factory._command_bus.dispatch(UnlockProductionLine("hall-1", line.line_id, "factory"))
        while len(line.slot_indexes) < 10:
            factory._command_bus.dispatch(UnlockProductionSlot("hall-1", line.line_id, "factory"))
    factory.refresh_view()

    for slot_index in sorted(hall.unlocked_slot_indexes()):
        card = create_card_instance(f"mass-processor-{slot_index}", "machine.processor", CardKind.MACHINE, Rarity.COMMON)
        factory._command_bus.dispatch(AddCard(card))
        factory._command_bus.dispatch(InstallCardInHall("hall-1", slot_index, card.card_id, "factory"))
    factory.refresh_view()
    widgets_before = dict(factory._slot_widgets)

    factory._simulation.advance_time(factory._state, 1.0)
    factory._refresh_runtime_widgets()

    assert len(factory._slot_widgets) == 50
    assert factory._slot_widgets == widgets_before
    assert all(widget._primary_value_text() == "SELECT" for widget in factory._slot_widgets.values())


def test_factory_navigation_shows_hall_slot_usage_and_remains_functional() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-furnace-common-001", "factory"))
    factory.refresh_view()

    assert factory.findChild(QLabel, "factoryV2NavTitle").text() == "FACTORY"
    assert factory.findChild(QLabel, "factoryV2NavSubtitle").text() == "OPERATIONS / HALLS"
    tree = factory.findChild(QTreeWidget, "hallTreeV2")
    assert tree is not None
    root = tree.topLevelItem(0)
    assert root is not None
    hall_item = root
    assert hall_item is not None
    assert "1 / 3" in hall_item.text(0)

    factory._on_slot_clicked(0)
    cid = factory._units[factory._selected_hall_id].slots[0].card_id
    cash = factory._state.cash.amount
    from production_zero.core.machine_operations import resale_value
    proceeds = resale_value(factory._state.cards[cid], factory._definitions[factory._state.cards[cid].definition_id])
    factory._sell_selection(cid)
    assert factory._state.cash.amount == cash + proceeds

    root = tree.topLevelItem(0)
    hall_item = root
    assert hall_item is not None
    assert "0 / 3" in hall_item.text(0)

    button = factory.findChild(QPushButton, "buildHallButtonV2")
    assert button is not None
    assert "Build Hall" in button.text()


def test_factory_hall_summary_shows_only_resources_relevant_to_selected_hall() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-furnace-common-001"))
    _select_factory_default_production(factory, "test-furnace-common-001")
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

    items = factory.findChildren(QFrame, "hallResourceSummaryItem")
    items_by_name = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in items
    }

    assert set(items_by_name) == {"IRON ORE", "IRON"}
    assert all(item.findChild(QProgressBar, "hallResourceStorageProgress") is not None for item in items)
    assert all(item.findChild(ResourceIconWidget, "resourceIcon") is not None for item in items)
    assert all(item.findChild(ResourceIconWidget, "resourceIcon").width() >= 40 for item in items)
    assert items_by_name["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "PROD +0.0 · USE -120.0 · NET -120.0/min"
    assert items_by_name["IRON ORE"].property("netState") == "negative"
    assert items_by_name["IRON"].findChild(QLabel, "hallResourceNet").text() == "PROD +60.0 · USE -0.0 · NET +60.0/min"
    assert items_by_name["IRON"].property("netState") == "positive"


def test_factory_hall_summary_net_change_states_and_values() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    neutral = create_card_instance("test-neutral-coal", "machine.neutral.coal", CardKind.MACHINE, Rarity.COMMON)
    factory._definitions["machine.neutral.coal"] = MachineDefinition(
        definition_id="machine.neutral.coal",
        name="Neutral Coal Tester",
        machine_type=MachineType.MINING,
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
    factory._set_resources_drawer_open(True)

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }

    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == "PROD +120.0 · USE -120.0 · NET +0.0/min"
    assert items["IRON ORE"].property("netState") == "neutral"
    assert items["IRON"].findChild(QLabel, "hallResourceNet").text() == "PROD +60.0 · USE -0.0 · NET +60.0/min"
    assert items["IRON"].property("netState") == "positive"
    assert items["COAL"].findChild(QLabel, "hallResourceNet").text() == "PROD +60.0 · USE -60.0 · NET +0.0/min"
    assert items["COAL"].property("netState") == "neutral"


def test_factory_hall_summary_keeps_output_resource_visible_when_storage_is_full() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")
    for stock in factory._state.resources.values():
        stock.amount = 0
    factory._state.warehouse_capacity = 500
    factory._command_bus.dispatch(AddResource("iron_ore", 500))

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-drill-common-001"].status == "storage_full"
    assert "IRON ORE" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceAmount").text() == "500 STORED"
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == 'PROD +120.0 · USE -0.0 · NET +120.0/min'
    assert items["IRON ORE"].property("netState") == "positive"


def test_factory_hall_summary_keeps_stopped_output_until_card_is_removed() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-drill-common-001"))
    _select_factory_default_production(factory, "test-drill-common-001")

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-drill-common-001"].status == "no_power"
    assert "IRON ORE" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == 'PROD +120.0 · USE -0.0 · NET +120.0/min'

    factory._on_slot_clicked(1)
    cid = factory._units[factory._selected_hall_id].slots[1].card_id
    cash = factory._state.cash.amount
    from production_zero.core.machine_operations import resale_value
    proceeds = resale_value(factory._state.cards[cid], factory._definitions[factory._state.cards[cid].definition_id])
    factory._sell_selection(cid)
    assert factory._state.cash.amount == cash + proceeds

    names_after_remove = {
        item.findChild(QLabel, "hallResourceName").text()
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert "IRON ORE" not in names_after_remove


def test_factory_hall_summary_keeps_input_resource_visible_with_zero_consumption() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory._state.resource_sites.clear(); factory._state.energy_plants.clear()
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 0, "test-solar-common-001"))
    factory._command_bus.dispatch(InstallCardInHall("hall-1", 1, "test-furnace-common-001"))
    _select_factory_default_production(factory, "test-furnace-common-001")
    factory._command_bus.dispatch(SetResourceCapacity("iron_ore", 500))
    factory._state.resources["iron_ore"].amount = 0

    SimulationEngine(factory._definitions).advance_time(factory._state, 1)
    factory.refresh_view()
    factory._set_resources_drawer_open(True)

    items = {
        item.findChild(QLabel, "hallResourceName").text(): item
        for item in factory.findChildren(QFrame, "hallResourceSummaryItem")
    }
    assert factory._state.machine_production["test-furnace-common-001"].status == "missing_input"
    assert "IRON ORE" in items
    assert "IRON" in items
    assert items["IRON ORE"].findChild(QLabel, "hallResourceNet").text() == 'PROD +0.0 · USE -120.0 · NET -120.0/min'
    assert items["IRON ORE"].property("netState") == "negative"
    assert items["IRON"].findChild(QLabel, "hallResourceNet").text() == "PROD +60.0 · USE -0.0 · NET +60.0/min"


def test_factory_view_can_unlock_locked_production_line_with_cash() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    hall = factory._state.halls["hall-1"]
    locked_line = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-2"
    )

    locked_line.keyPressEvent(type("Event", (), {
        "key": lambda self: Qt.Key.Key_Return,
    })())

    assert factory._state.cash.amount == 350
    assert hall.production_lines[1].unlocked is True
    assert hall.slot_count == 6
    assert len(hall.slots) == 50
    assert hall.production_lines[1].slot_indexes == [3, 4, 5]
    assert not [
        panel
        for panel in factory.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == "hall-1.line-2"
    ]


def test_factory_view_can_unlock_slots_and_locked_slot_does_not_open_selection() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    hall = factory._state.halls["hall-1"]

    locked_slot = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 4
    )
    assert locked_slot.findChild(QPushButton, "unlockSlotButton") is None
    assert locked_slot._slot_number == 4
    assert locked_slot.property("unlockCost") > 0


    assert locked_slot.findChild(QPushButton, "productionChangeButton") is None
    assert factory.findChild(QFrame, "factoryCardSelectionView") is None

    locked_slot.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())

    assert hall.production_lines[0].slot_indexes == [0, 1, 2, 3]
    assert hall.slot_count == 4
    locked_slot_5 = next(
        panel
        for panel in factory.findChildren(QFrame, "lockedSlotPanel")
        if panel.property("lineId") == "hall-1.line-1" and panel.property("slotNumber") == 5
    )
    locked_slot_5.keyPressEvent(type("Event", (), {
        "key": lambda self: Qt.Key.Key_Space,
    })())
    assert hall.production_lines[0].slot_indexes == [0, 1, 2, 3, 4]
    assert hall.slot_count == 5
    factory._on_slot_clicked(3)
    assert factory.findChild(QFrame, "factoryCardSelectionView") is not None


def test_factory_unlock_panels_enable_after_runtime_cash_refresh_without_hall_rebuild() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
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
        if panel.property("lineId") == "hall-1.line-2"
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
        if panel.property("lineId") == "hall-1.line-2"
    )
    assert same_slot_panel is slot_panel
    assert same_line_panel is line_panel
    assert same_slot_panel.property("unlockEnabled") is True
    assert same_line_panel.property("unlockEnabled") is True

    same_slot_panel.mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    assert factory._state.halls["hall-1"].slot_count == 4

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
    assert factory._state.halls["hall-2"].slot_count == 4
    assert factory._state.halls["hall-1"].slot_count == 4


def test_factory_runtime_can_unlock_line_one_through_slot_ten_in_hall_one_and_two() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
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
        assert hall.slot_count == 10
        assert not [
            panel
            for panel in factory.findChildren(QFrame, "lockedSlotPanel")
            if panel.property("lineId") == f"{hall_id}.line-1" and panel.property("slotNumber") == 10
        ]

    factory._command_bus.dispatch(PurchaseHall())
    assert factory._state.halls["hall-1"].slot_count == 10
    assert factory._state.halls["hall-2"].slot_count == 10
    assert factory._state.halls["hall-3"].slot_count == 3


def test_factory_hall_view_uses_full_width_without_reserved_drawer_space() -> None:
    _app()
    window = MainWindow()
    window.resize(1800, 900)
    window.show()
    QApplication.processEvents()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None
    factory.refresh_view()
    QApplication.processEvents()

    assert factory.findChild(QFrame, "factoryCardSelectionView") is None
    assert factory.findChild(QFrame, "productionSelectionView") is None
    scroll = factory.findChild(QScrollArea, "factoryV2Scroll")
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.width() >= factory._content.width() - 40


def test_factory_view_can_purchase_new_hall_from_sidebar() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    assert factory is not None

    factory._state.cash.add(14_200)
    factory.refresh_view()
    button = factory.findChild(QPushButton, "buildHallButtonV2")
    assert button is not None
    assert button.isEnabled() is True

    button.click()

    assert set(factory._state.halls) == {"hall-1", "hall-2"}
    assert factory._selected_hall_id == "hall-2"
    assert factory._state.cash.amount == 250
    assert factory._state.halls["hall-2"].slot_count == 3
    assert factory._state.halls["hall-2"].production_lines[2].unlocked is False


def test_inventory_tab_shows_available_machine_stacks() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    tabs = inventory_view.findChild(QTabWidget, "inventorySubTabs")
    assert tabs is not None
    assert [tabs.tabText(index) for index in range(tabs.count())] == ["Cards", "Crafting"]
    assert inventory_view.findChild(QFrame, "inventoryScrapPage") is None
    assert tabs.currentIndex() == 0
    cards = _inventory_cards_by_name(inventory_view)

    assert len(cards) == 4
    extractor_card = cards["Extractor"]
    assert extractor_card.findChild(QLabel, "inventoryCardRarity").text() == "Common"
    assert extractor_card.findChild(QLabel, "inventoryCardBonus").text() == "+0.0%"
    assert extractor_card.findChild(QLabel, "inventoryCardQuantity").text() == "Qty 3"
    assert extractor_card.findChild(QLabel, "inventoryCardStatus").text() == "Available"
    assert set(cards) == {
        "Extractor",
        "Solar Array",
        "Processor", "Freight Truck",
    }
    assert inventory_view.findChild(QLabel, "inventoryTotalCardsLabel").text() == "8"
    assert inventory_view.findChild(QLabel, "inventoryStacksLabel").text() == "4"
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


def test_inventory_empty_and_sparse_card_grid_use_shared_polished_composition() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    inventory_view._state.cards.clear()
    for hall in inventory_view._state.halls.values():
        for slot in hall.slots:
            slot.card_id = None
    inventory_view.refresh()
    QApplication.processEvents()

    empty = inventory_view.findChild(EmptyStatePanel, "inventoryEmptyState")
    assert empty is not None
    assert empty.property("emptyStatePanel") is True
    assert empty.findChild(QLabel, "emptyStateTitle").text() == "NO CARDS IN INVENTORY"
    assert inventory_view.findChildren(QFrame, "inventoryCard") == []

    scroll = inventory_view.findChild(QScrollArea, "cardInventoryScroll")
    assert scroll is not None
    card_specs = [
        ("sparse-inventory-machine", "machine.extractor", CardKind.MACHINE, Rarity.COMMON),
        ("sparse-inventory-energy", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON),
    ]
    for count in (1, 2):
        inventory_view._state.cards.clear()
        for card_id, definition_id, kind, rarity in card_specs[:count]:
            inventory_view._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, kind, rarity)))
        inventory_view.refresh()
        QApplication.processEvents()
        cards = list(_inventory_cards_by_name(inventory_view).values())
        assert len(cards) == count
        assert inventory_view.findChild(EmptyStatePanel, "inventoryEmptyState") is None
        _assert_widget_group_left_aligned(cards, inventory_view._card_grid_container, (INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT))
        assert scroll.horizontalScrollBar().maximum() == 0

    inventory_view.findChild(QLineEdit, "inventorySearch").setText("no-card-matches-this-filter")
    QApplication.processEvents()
    filtered_empty = inventory_view.findChild(EmptyStatePanel, "inventoryEmptyState")
    assert filtered_empty is not None
    assert filtered_empty.findChild(QLabel, "emptyStateTitle").text() == "NO CARDS FOUND"
    window.close()


def test_inventory_sparse_left_aligns_and_preserves_partial_final_rows_without_resizing() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    for hall in inventory_view._state.halls.values():
        for slot in hall.slots:
            slot.card_id = None
    card_specs = [
        ("right-inventory-extractor", "machine.extractor", CardKind.MACHINE, Rarity.COMMON),
        ("right-inventory-processor", "machine.processor", CardKind.MACHINE, Rarity.COMMON),
        ("right-inventory-solar", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON),
        ("right-inventory-wind", "energy.wind_turbine", CardKind.ENERGY, Rarity.COMMON),
        ("right-inventory-truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON),
        ("right-inventory-train", "freight.train", CardKind.FREIGHT, Rarity.COMMON),
        ("right-inventory-ship", "freight.ship", CardKind.FREIGHT, Rarity.COMMON),
        ("right-inventory-aircraft", "freight.aircraft", CardKind.FREIGHT, Rarity.COMMON),
        ("right-inventory-recipe", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON),
        ("right-inventory-furnace", "machine.processor", CardKind.MACHINE, Rarity.COMMON),
    ]

    inventory_view._state.cards.clear()
    for card_id, definition_id, kind, rarity in card_specs[:5]:
        inventory_view._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, kind, rarity)))
    inventory_view.refresh()
    QApplication.processEvents()

    sparse_cards = list(_inventory_cards_by_name(inventory_view).values())
    assert len(sparse_cards) == 5
    _assert_widget_group_left_aligned(sparse_cards, inventory_view._card_grid_container, (INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT))

    columns = inventory_view._inventory_grid_columns()
    inventory_view._state.cards.clear()
    partial_count = columns + 2
    if partial_count <= 5:
        partial_count = (columns * 2) + 1
    if partial_count % columns == 0:
        partial_count += 1
    for card_id, definition_id, kind, rarity in card_specs[:partial_count]:
        inventory_view._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, kind, rarity)))
    inventory_view.refresh()
    QApplication.processEvents()

    positions_by_card = {}
    for card in inventory_view.findChildren(QFrame, "inventoryCard"):
        index = inventory_view._cards_grid.indexOf(card)
        row, _column, _row_span, _column_span = inventory_view._cards_grid.getItemPosition(index)
        positions_by_card[card] = row
    final_row = max(positions_by_card.values())
    final_row_cards = [card for card, row in positions_by_card.items() if row == final_row]
    assert len(final_row_cards) == partial_count % columns
    first_row_cards = []
    for card in inventory_view.findChildren(QFrame, "inventoryCard"):
        index = inventory_view._cards_grid.indexOf(card)
        row, _column, _row_span, _column_span = inventory_view._cards_grid.getItemPosition(index)
        if row == 0:
            first_row_cards.append(card)
    final_right = max(card.mapTo(inventory_view._card_grid_container, card.rect().topRight()).x() for card in final_row_cards)
    grid_right = max(card.mapTo(inventory_view._card_grid_container, card.rect().topRight()).x() for card in first_row_cards)
    assert abs(final_right - grid_right) <= 4
    assert {(card.width(), card.height()) for card in final_row_cards} == {(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)}
    assert inventory_view.findChild(QScrollArea, "cardInventoryScroll").horizontalScrollBar().maximum() == 0
    window.close()


def test_inventory_tab_displays_large_stack_quantities_without_capping() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    for index in range(247):
        inventory_view._command_bus.dispatch(
            AddCard(create_card_instance(f"ui-large-stack-{index:03d}", "machine.extractor", CardKind.MACHINE, Rarity.COMMON))
        )
    inventory_view.refresh()

    cards = _inventory_cards_by_name(inventory_view)
    extractor_card = cards["Extractor"]

    assert extractor_card.property("quantity") == 250
    assert extractor_card.findChild(QLabel, "inventoryCardQuantity").text() == "Qty 250"
    assert "while font.pointSize() > 5" in inspect.getsource(InventoryCardFrame._draw_quantity_badge)


def test_topbar_resource_storage_expansion_updates_runtime_capacity() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = legacy_component(window, InventoryView)
    global_header = window._global_header
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
    button = window.findChild(QWidget, "expandResourceStorageButton")
    topbar_storage = window.findChild(QLabel, "factoryV2StorageValue")
    cash_label = window.findChild(QLabel, "factoryV2CashValue")
    assert storage_label is not None
    assert storage_info is not None
    assert button is not None
    assert topbar_storage is not None
    assert cash_label is not None
    assert inventory_view.findChild(QPushButton, "expandInventoryStorageButton") is None
    assert storage_info.text() == "All physical resources share this warehouse capacity. Storage upgrades are in the topbar."
    assert button._text == "EXPAND"
    assert f"${cost:,.2f}" in button.toolTip()
    assert button.isEnabled() is True
    assert storage_label.text().endswith(f"/ {inventory_view._state.storage_capacity:.0f}")
    assert topbar_storage.text().endswith(f"/{inventory_view._state.storage_capacity:,.0f}")

    from PySide6.QtCore import QTimer
    QTimer.singleShot(0,lambda: QApplication.activeModalWidget().accept())
    button.clicked.emit()
    QApplication.processEvents()

    assert inventory_view._state.inventory_storage_level == 1
    assert inventory_view._state.cash.amount == starting_cash - cost
    assert inventory_view._state.resources["iron_ore"].amount == 145
    assert inventory_view._state.resources["iron_ore"].capacity == inventory_storage_capacity(
        resource_definitions["iron_ore"].default_capacity,
        1,
    )
    assert inventory_view._state.resources["iron_ore"].capacity > starting_capacity
    assert button._text == "EXPAND"
    assert f"${inventory_storage_upgrade_cost(1):,.2f}" in button.toolTip()
    assert cash_label.text() == f"${inventory_view._state.cash.amount:,.0f}"
    assert topbar_storage.text().endswith(f"/{inventory_view._state.storage_capacity:,.0f}")
    assert inventory_view._state.freight.facilities["garage-1"].slot_count == 3
    assert inventory_view._state.halls["hall-1"].slot_count == 3


def test_inventory_cards_use_visual_card_grid_components() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert inventory_view is not None
    assert tabs is not None
    inventory_view._command_bus.dispatch(
        AddCard(create_card_instance("ui-energy-stack-test", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON))
    )
    inventory_view.resize(1300, 800)
    inventory_view.refresh()
    window.show()
    tabs.setCurrentWidget(inventory_view)
    QApplication.processEvents()

    cards = _inventory_cards_by_name(inventory_view)
    extractor_card = cards["Extractor"]
    energy_card = cards["Solar Array"]
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
    search_group_block = _style_block("QWidget#inventorySearchGroup")
    assert "rgba(4, 7, 7" not in search_block
    assert "rgba(255, 255, 255, 8)" in search_block
    assert "background: transparent" in search_group_block
    assert "border: 0" in search_group_block
    title = extractor_card.findChild(QLabel, "inventoryCardName")
    rarity = extractor_card.findChild(QLabel, "inventoryCardRarity")
    assert title is not None
    assert rarity is not None
    assert title.isHidden()
    assert rarity.isHidden()
    assert extractor_card.findChild(QFrame, "inventoryRarityLine") is None
    assert extractor_card.findChild(QLabel, "inventoryCardFunction").text() == "EXTRACTOR"
    assert extractor_card.property("cardTitle") == "EXTRACTOR"
    assert extractor_card.property("cardMeta") == "COMMON"
    assert energy_card.property("cardTitle") == "SOLAR ARRAY"
    assert energy_card.property("cardMeta") == "COMMON"
    assert "V" in _BLOCK_GLYPHS
    assert extractor_card.property("cardType") == "extractor"
    assert energy_card.findChild(QLabel, "inventoryCardFunction").text() == "ENERGY"
    assert energy_card.property("cardType") == "energy"
    assert extractor_card.width() == energy_card.width()
    assert extractor_card.height() == cards["Processor"].height()
    assert extractor_card.property("quantity") == 3
    assert extractor_card.property("statusText") == "Available"
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventoryMkFilter") is None
    assert inventory_view.findChild(QComboBox, "inventoryRarityFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventoryStatusFilter").isHidden()
    assert inventory_view.findChild(QComboBox, "inventorySort").isHidden()
    chips = inventory_view.findChildren(QPushButton, "inventoryFilterChip")
    assert chips
    assert any(chip.property("filterGroup") == "inventoryTypeFilter" and chip.text() == "ENERGY" for chip in chips)
    assert inventory_view.findChild(QFrame, "cardDetailsDrawer") is None
    action_panel = inventory_view.findChild(QFrame, "inventoryActionPanel")
    assert action_panel is not None
    assert not action_panel.isHidden()
    assert action_panel.findChild(QPushButton, "scrapCardButton") is None


def test_inventory_card_grid_wraps_responsively_without_horizontal_scrollbar() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None
    for _ in range(5):
        index = _
        inventory_view._command_bus.dispatch(
            AddCard(create_card_instance(f"ui-grid-extra-{index}", "machine.extractor", CardKind.MACHINE, Rarity.UNCOMMON, 10 + index))
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


def test_inventory_cards_tab_energy_filter_groups_all_energy_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None
    for card_id, definition_id in (
        ("inventory-filter-wind", "energy.wind_turbine"),
        ("inventory-filter-coal", "energy.coal_power_plant"),
        ("inventory-filter-gas", "energy.gas_power_plant"),
        ("inventory-filter-nuclear", "energy.nuclear_power_plant"),
    ):
        inventory_view._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.ENERGY, Rarity.COMMON)))
    window.show()
    inventory_view.refresh()
    QApplication.processEvents()

    type_values = [
        chip.property("filterValue")
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "inventoryTypeFilter"
    ]
    assert "Energy" in type_values
    assert "Solar" not in type_values
    type_chip = next(
        chip
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "inventoryTypeFilter" and chip.property("filterValue") == "Energy"
    )
    type_chip.click()
    QApplication.processEvents()

    cards = _inventory_cards_by_name(inventory_view)
    assert {
        "Coal Power Plant",
        "Gas Power Plant",
        "Nuclear Power Plant",
        "Solar Array",
        "Wind Turbine",
    } <= set(cards)
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").currentText() == "Energy"
    assert inventory_view.findChild(QComboBox, "inventoryTypeFilter").isHidden()
    assert any(
        chip.property("filterGroup") == "inventoryTypeFilter"
        and chip.property("filterValue") == "Energy"
        and chip.property("active") is True
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
    )


def test_inventory_cards_redesign_preview_renders_offscreen() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = legacy_component(window, InventoryView)
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
    factory = window.findChild(ResourcesViewV2)
    inventory_view = legacy_component(window, InventoryView)
    assert factory is not None
    assert inventory_view is not None

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Extractor")
    inventory_view.refresh()

    status_filter = inventory_view.findChild(QComboBox, "inventoryStatusFilter")
    assert status_filter is not None

    status_filter.setCurrentText("In Use")

    in_use_cards = _inventory_cards_by_name(inventory_view)
    assert list(in_use_cards) == ["Extractor"]
    assert in_use_cards["Extractor"].findChild(QLabel, "inventoryCardQuantity").text() == "Qty 1"
    assert in_use_cards["Extractor"].findChild(QLabel, "inventoryCardStatus").text() == "In Use"
    in_use_cards["Extractor"].mousePressEvent(None)
    assert not inventory_view.findChild(QFrame, "inventoryActionPanel").isHidden()
    assert inventory_view.findChild(QPushButton, "scrapCardButton") is None
    assert inventory_view.findChild(QPushButton, "confirmScrapButton") is None

    status_filter.setCurrentText("Available")

    available_cards = _inventory_cards_by_name(inventory_view)
    extractor_card = available_cards["Extractor"]
    assert extractor_card.findChild(QLabel, "inventoryCardStatus").text() == "Available"
    assert extractor_card.findChild(QLabel, "inventoryCardQuantity").text() == "Qty 2"


def test_inventory_tab_recycles_available_stack_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    _inventory_cards_by_name(inventory_view)["Extractor"].mousePressEvent(None)
    action_panel = inventory_view.findChild(QFrame, "inventoryActionPanel")
    assert action_panel is not None
    quantity = action_panel.findChild(QSpinBox, "scrapQuantity")
    scrap_button = action_panel.findChild(QPushButton, "scrapCardButton")
    assert isinstance(quantity, QSpinBox)
    assert scrap_button is not None

    quantity.setValue(2)
    reward = action_panel.findChild(QLabel, "inventoryScrapReward")
    assert reward.text() == "2 INDUSTRIAL SCRAP"
    scrap_button.click()

    assert inventory_view._state.scrap.amount == 0
    assert action_panel.findChild(QLabel, "inventoryActionTitle").text() == "CONFIRM SCRAP"
    assert action_panel.findChild(QLabel, "scrapConfirmationQuantity").text() == "Quantity: 2"
    assert action_panel.findChild(QLabel, "inventoryScrapReward").text() == "RECEIVE: 2 INDUSTRIAL SCRAP"
    assert action_panel.findChild(QPushButton, "cancelScrapButton") is not None
    confirm = action_panel.findChild(QPushButton, "confirmScrapButton")
    assert confirm is not None
    confirm.click()

    assert inventory_view._state.scrap.amount == 2
    extractor_stack = next(
        stack
        for stack in inventory_view._state.inventory_card_stacks()
        if stack.first_card.definition_id == "machine.extractor"
    )
    assert extractor_stack.quantity == 1
    assert inventory_view.findChild(QLabel, "industrialScrapLabel").text() == "2"


def test_inventory_cards_search_and_hover_show_effective_values() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None

    search = inventory_view.findChild(QLineEdit, "inventorySearch")
    assert search is not None
    assert inventory_view.findChild(QFrame, "cardDetailsDrawer") is None

    search.setText("solar")
    cards = _inventory_cards_by_name(inventory_view)
    assert list(cards) == ["Solar Array"]

    inventory_view._show_card_hover(inventory_view._visible_card_rows[0], cards["Solar Array"])
    hover = inventory_view.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    detail_values = [label.text() for label in hover.findChildren(QLabel, "cardHoverValue")]
    assert any("MW" in value for value in detail_values)
    assert "1" in detail_values
    assert hover.findChild(ResourceIconWidget) is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Solar Array"


def test_inventory_tab_can_craft_selected_material_cards() -> None:
    _app()
    window = _main_window_with_dev_tools()
    inventory_view = legacy_component(window, InventoryView)
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
    assert "SELECT TARGET CARD" not in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 0/4"

    target_cards = inventory_view.findChildren(QFrame, "craftTargetCard")
    assert target_cards
    assert all(not str(card.property("definitionId")).startswith("recipe.") for card in target_cards)
    assert any(card.findChild(ResourceIconWidget) is not None for card in target_cards)
    target = next(card for card in target_cards if card.property("definitionId") == "machine.processor")
    target.mousePressEvent(None)
    assert inventory_view._craft_pages.currentIndex() == 1

    for _ in range(4):
        slot = next(slot for slot in inventory_view.findChildren(QFrame, "craftMaterialSlot") if not slot.property("filled"))
        slot.mousePressEvent(None)
        assert inventory_view._craft_pages.currentIndex() == 0
        material = next(
            card
            for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
            if card.property("definitionId") == "machine.extractor"
        )
        material.mousePressEvent(None)

    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 4/4"
    material = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
        if card.property("definitionId") == "machine.extractor"
    )
    assert material.property("selectedCount") == 4
    material.hovered.emit()
    hover = inventory_view.findChild(QFrame, "cardHoverInfo")
    assert hover is not None
    assert hover.findChild(QLabel, "cardHoverTitle").text() == "Extractor"
    assert "Target: Processor" in preview.text()
    assert "Result Rarity: Rare" in preview.text()
    assert "Result Bonus: +8.0%" in preview.text()
    material_slots = inventory_view.findChildren(QFrame, "craftMaterialSlot")
    assert len(material_slots) == 4
    assert all(slot.property("filled") is True for slot in material_slots)
    material_slots[0].mousePressEvent(None)
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 3/4"
    material = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
        if card.property("definitionId") == "machine.extractor"
    )
    assert material.property("selectedCount") == 3
    material.mousePressEvent(None)
    assert inventory_view.findChild(QLabel, "craftMaterialCount").text() == "Materials 4/4"
    target_preview = inventory_view.findChild(QFrame, "craftTargetPreview")
    assert target_preview is not None
    target_preview.mousePressEvent(None)
    assert "SELECT TARGET CARD" not in [label.text() for label in inventory_view.findChildren(QLabel, "craftSectionTitle")]
    target = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
        if card.property("definitionId") == "machine.processor"
    )
    target.mousePressEvent(None)
    assert inventory_view._craft_pages.currentIndex() == 1
    assert button.isEnabled() is False
    confirm.setChecked(True)
    button.click()

    crafted = [
        card
        for card in inventory_view._state.cards.values()
        if card.definition_id == "machine.processor" and card.rarity is Rarity.RARE
    ]
    assert len(crafted) == 1
    assert crafted[0].output_bonus_tenths == 80


def test_inventory_crafting_tab_uses_game_shell_chips_and_cards() -> None:
    _app()
    window = MainWindow()
    inventory_view = legacy_component(window, InventoryView)
    assert inventory_view is not None
    inventory_view.refresh()
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
    QApplication.processEvents()

    assert inventory_view.findChild(QFrame, "craftSelectionPanel") is not None
    assert inventory_view.findChild(QFrame, "craftPreviewPanel") is not None
    assert not any(
        label.isVisible() and label.text() == "SELECT TARGET CARD"
        for label in inventory_view.findChildren(QLabel)
    )
    assert inventory_view.findChildren(QWidget, "craftFilterDeck")
    assert inventory_view.findChild(QComboBox, "craftTargetTypeFilter").isHidden()
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
    assert "energy.solar_array" in energy_target_ids
    assert all(str(definition_id).startswith("energy.") for definition_id in energy_target_ids)

    energy_card = next(
        card
        for card in inventory_view.findChildren(QFrame, "craftTargetCard")
        if card.property("definitionId") == "energy.solar_array"
    )
    assert type(energy_card).__name__ == "InventoryCardFrame"
    assert energy_card.findChild(ResourceIconWidget, "inventoryCardIcon") is not None
    assert energy_card.property("cardTitle") == "SOLAR ARRAY"
    assert energy_card.property("cardMeta") == "RARE"
    assert energy_card.property("rarity") == "rare"
    target_rarity_values = {
        chip.property("filterValue")
        for chip in inventory_view.findChildren(QPushButton, "inventoryFilterChip")
        if chip.property("filterGroup") == "craftTargetRarityFilter"
    }
    assert target_rarity_values == {"Rare", "Epic", "Legendary"}


def test_inventory_crafting_redesign_preview_renders_offscreen() -> None:
    _app()
    window = _main_window_with_dev_tools()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = legacy_component(window, InventoryView)
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
        if card.property("definitionId") == "machine.processor"
    )
    target.mousePressEvent(None)
    for _ in range(2):
        material = next(
            card
            for card in inventory_view.findChildren(QFrame, "craftMaterialCard")
            if card.property("definitionId") == "machine.extractor"
        )
        material.mousePressEvent(None)
    QApplication.processEvents()

    path = Path("artifacts") / "inventory_crafting_redesign_preview.png"
    path.parent.mkdir(exist_ok=True)
    image = inventory_view.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    assert image.save(str(path))
    assert path.exists()










def test_charts_tab_opens_resource_overview_with_resource_tile_grid() -> None:
    _app()
    window = _main_window_with_charts()
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
    assert iron_ore.minimumHeight() == 146
    assert iron_ore.findChild(QLabel, "chartResourceAmount").text() == "145 stored"
    assert iron_ore.findChild(QWidget, "chartResourceSparkline") is not None
    assert iron_ore.findChild(QProgressBar, "chartResourceStorageProgress").value() == 290


def test_charts_startup_does_not_create_top_level_tile_or_visibility_loop() -> None:
    app = _app()
    window = _main_window_with_charts()
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


def test_main_window_layout_minimums_fit_typical_1080p_work_area() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = legacy_component(window, InventoryView)
    assert tabs is not None
    assert inventory_view is not None
    tabs.setCurrentWidget(inventory_view)
    inventory_view.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
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
    ):
        scroll = inventory_view.findChild(QScrollArea, object_name)
        assert scroll is not None
        assert scroll.minimumSizeHint().width() <= 180
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        if scroll.isVisible():
            assert scroll.widget() is not None
            assert scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
            assert scroll.widget().width() >= scroll.viewport().width()


def test_inventory_filter_scrolls_keep_desktop_filterdeck_footprint_without_minimum_width() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory_view = legacy_component(window, InventoryView)
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
        assert scroll.sizeHint().width() <= maximum_desktop_width
        assert scroll.width() >= minimum_desktop_width
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert scroll.widget() is not None
        assert scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        assert scroll.widget().width() >= scroll.viewport().width()




def test_charts_overview_shows_rising_falling_and_neutral_status() -> None:
    _app()
    window = _main_window_with_charts()
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
    window = _main_window_with_charts()
    charts = window.findChild(ChartsView)
    assert charts is not None

    search = charts.findChild(QLineEdit, "chartResourceSearch")
    assert search is not None
    search.setText("iron ore")

    assert list(_chart_resource_cards_by_name(charts)) == ["Iron Ore"]


def test_charts_overview_filters_and_sorts_resource_tiles() -> None:
    _app()
    window = _main_window_with_charts()
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
    stage.setCurrentText("Primary Production")
    assert "Iron Ore" in _chart_resource_cards_by_name(charts)
    category.setCurrentText("All")
    stage.setCurrentText("All")
    sort.setCurrentText("Net Change")
    assert list(_chart_resource_cards_by_name(charts))[:3] == ["Steel", "Coal", "Iron Ore"]
    sort.setCurrentText("Amount")
    assert list(_chart_resource_cards_by_name(charts))[0] == "Iron Ore"


def test_charts_resource_detail_and_back_navigation() -> None:
    _app()
    window = _main_window_with_charts()
    charts = window.findChild(ChartsView)
    assert charts is not None

    stack = charts.findChild(QStackedWidget, "chartsStack")
    assert stack is not None
    _chart_resource_cards_by_name(charts)["Steel"].mousePressEvent(None)

    assert stack.currentIndex() == 1
    assert charts.findChild(QLabel, "chartDetailTitle").text() == "Steel"
    assert charts.findChild(ResourceIconWidget) is not None
    assert charts.findChild(QLabel, "chartDetailAmount").text() == "0 stored"
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
    window = _main_window_with_charts()
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
    assert first_card.findChild(QLabel, "chartResourceAmount").text() == "200 stored"

    first_card.mousePressEvent(None)
    assert stack.currentIndex() == 1
    charts._state.resources["iron_ore"].amount = 210
    charts.refresh()
    assert stack.currentIndex() == 1
    assert charts.findChild(QLabel, "chartDetailTitle").text() == "Iron Ore"
    assert charts.findChild(QLabel, "chartDetailAmount").text() == "210 stored"


def test_charts_passive_refresh_does_not_rebuild_filter_chips() -> None:
    _app()
    window = _main_window_with_charts()
    charts = window.findChild(ChartsView)
    assert charts is not None

    chips_before = {
        (chip.property("filterGroup"), chip.property("filterValue")): chip
        for chip in charts.findChildren(QPushButton, "chartFilterChip")
    }
    rebuild_count = charts._filter_chip_rebuild_count

    charts._state.resources["iron_ore"].amount = 205
    for _ in range(4):
        charts.refresh()
        charts._refresh_overview()

    chips_after = {
        (chip.property("filterGroup"), chip.property("filterValue")): chip
        for chip in charts.findChildren(QPushButton, "chartFilterChip")
    }
    assert charts._filter_chip_rebuild_count == rebuild_count
    assert chips_after == chips_before

    active_chip = chips_after[("chartStageFilter", "Primary Production")]
    active_chip.click()
    assert charts.findChild(QComboBox, "chartStageFilter").currentText() == "Primary Production"
    assert charts._filter_chip_rebuild_count == rebuild_count + 1


def test_charts_redesign_uses_header_chip_filters_and_modern_detail_controls() -> None:
    _app()
    window = _main_window_with_charts()
    charts = window.findChild(ChartsView)
    assert charts is not None

    header = charts.findChild(QFrame, "chartsHeader")
    assert header is not None
    assert header.findChild(QLabel, "chartsHeroTitle").text() == "CHARTS"
    assert header.findChild(QLabel, "chartsHeroSubtitle").text() == "RESOURCE FLOW / ANALYTICS"
    assert header.findChildren(QFrame, "chartsHeaderMetric") == []

    filter_scroll = charts.findChild(QScrollArea, "chartFilterScroll")
    assert filter_scroll is not None
    assert filter_scroll.minimumSizeHint().width() <= 180
    assert filter_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert filter_scroll.sizeHint().height() <= 76
    assert filter_scroll.widget() is not None
    assert filter_scroll.widget().objectName() == "chartFilterDeck"
    assert filter_scroll.widget().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    sort = charts.findChild(QComboBox, "chartSortSelect")
    stage = charts.findChild(QComboBox, "chartStageFilter")
    category = charts.findChild(QComboBox, "chartCategoryFilter")
    activity = charts.findChild(QComboBox, "chartActivityFilter")
    assert stage.isHidden()
    assert all(combo is not None and not combo.isHidden() for combo in (sort, category, activity))
    chips = charts.findChildren(QPushButton, "chartFilterChip")
    chip_groups = {chip.property("filterGroup") for chip in chips}
    assert "chartStageFilter" in chip_groups
    assert "chartActivityFilter" not in chip_groups
    activity.setCurrentText("Active")
    assert activity.currentText() == "Active"
    activity.setCurrentText("All")

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
    window = _main_window_with_charts()
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
    market_view = legacy_component(window, MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")
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
    assert event_panel is None
    info = market_view._header._event_info
    assert "Industrial Boom" in info
    assert "Affected resources" in info
    assert "Remaining:" in info
    assert search is not None
    assert search.placeholderText() == "Search market..."
    assert stage is not None
    assert [stage.itemText(index) for index in range(stage.count())] == ["Primary Production", "Processing", "Manufacturing", "Assembly", "All"]
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
    market_view = legacy_component(window, MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")
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
        "marketTimeframeSelect",
    }.issubset(chip_groups)

    category_chips = [chip for chip in chips if chip.property("filterGroup") == "marketCategoryFilter"]
    event_chips = [chip for chip in chips if chip.property("filterGroup") == "marketEventFilter"]
    trend_chips = [chip for chip in chips if chip.property("filterGroup") == "marketTrendFilter"]
    sort_chips = [chip for chip in chips if chip.property("filterGroup") == "marketSortSelect"]
    assert category_chips == []
    assert event_chips == []
    assert trend_chips == []
    assert sort_chips == []
    category_button = market_view.findChild(QPushButton, "marketCategorySelectorButton")
    event_button = market_view.findChild(QPushButton, "marketEventSelectorButton")
    trend_button = market_view.findChild(QPushButton, "marketTrendSelectorButton")
    sort_button = market_view.findChild(QPushButton, "marketSortSelectorButton")
    assert category_button is not None
    assert category_button.text() == "ALL >"
    assert event_button is not None
    assert event_button.text() == "ALL >"
    assert trend_button is not None
    assert trend_button.text() == "ALL >"
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


def test_market_filter_deck_fits_standard_gameplay_width_without_clipping() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 980)
    market_view = legacy_component(window, MarketView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")
    assert tabs is not None

    tabs.setCurrentWidget(market_view)
    window.show()
    QApplication.processEvents()

    filter_scroll = market_view.findChild(QScrollArea, "marketFilterScroll")
    assert filter_scroll is not None
    deck = filter_scroll.widget()
    assert deck is not None
    assert deck.minimumSizeHint().width() <= filter_scroll.viewport().width()

    layout = deck.layout()
    assert layout is not None
    right_edges = [
        layout.itemAt(index).widget().geometry().right()
        for index in range(layout.count())
        if layout.itemAt(index).widget() is not None
    ]
    assert right_edges
    assert max(right_edges) < filter_scroll.viewport().width()
    assert filter_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_market_light_filter_deck_search_and_event_banner_use_readable_styles() -> None:
    market_deck = _style_block("QWidget#marketFilterDeck")
    market_search = _style_block("QWidget#marketFilterDeck QLineEdit#marketSearch")
    market_chip = _style_block("QPushButton#marketFilterChip")
    market_active_chip = _style_block('QPushButton#marketFilterChip[active="true"]')
    market_selector = _style_block("QPushButton#marketCategorySelectorButton, QPushButton#marketEventSelectorButton, QPushButton#marketTrendSelectorButton, QPushButton#marketSortSelectorButton")
    event_panel = _style_block("QFrame#marketEventPanel")
    event_name_start = APP_STYLESHEET.index("\nQLabel#marketEventName {")
    event_name_end = APP_STYLESHEET.index("\n}", event_name_start)
    event_name = APP_STYLESHEET[event_name_start:event_name_end]
    event_affected = _style_block("QLabel#marketEventAffected")
    event_remaining = _style_block("QLabel#marketEventRemaining")

    assert "background: qlineargradient" in market_deck
    assert "rgba(21, 22, 19" not in market_deck
    assert Theme.TEXT_ON_LIGHT_PRIMARY in market_search
    assert "rgba(6, 9, 9, 178)" not in market_search
    assert Theme.FILTER_INACTIVE_TEXT in market_chip
    assert "color: #17191b" in market_active_chip
    assert "#ffd21f" in market_active_chip
    assert "#f5a623" in market_active_chip
    assert Theme.TEXT in market_selector
    assert "#876423" not in event_panel
    assert "rgba(42, 36, 18" not in event_panel
    assert Theme.TEXT_ON_LIGHT_PRIMARY in event_name
    assert Theme.TEXT_ON_LIGHT_SECONDARY in event_affected
    assert Theme.TEXT_ON_LIGHT_PRIMARY in event_remaining


def test_market_overview_search_filters_market_rows() -> None:
    _app()
    window = MainWindow()
    market_view = legacy_component(window, MarketView)
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")

    search = market_view.findChild(QLineEdit, "marketSearch")
    assert search is not None
    search.setText("iron ore")

    assert list(_market_table_rows_by_name(market_view)) == ["Iron Ore"]


def test_market_overview_filters_and_sorts_watchlist_rows() -> None:
    _app()
    window = MainWindow()
    market_view = legacy_component(window, MarketView)
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")

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

    stage.setCurrentText("Primary Production")
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
    market_view = legacy_component(window, MarketView)
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")

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
    market_view = legacy_component(window, MarketView)
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")

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
    table.clicked.emit(market_view._lane_model.index(first_row // 2, first_row % 2))

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
    assert "background: #333538" in icon_host_style
    assert "border: 1px solid #7b7b77" in icon_host_style
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
    assert flat_min < 6.75 < flat_max
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
    market_view = legacy_component(window, MarketView)
    assert tabs is not None
    assert market_view is not None
    market_view._stage_filter.setCurrentText("All")

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
    assert len(cards) == 3
    assert len(accept_buttons) == 3
    assert scroll is not None
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert sum(card.property("state") == "active" for card in cards) == 0
    assert not any(button.isEnabled() for button in accept_buttons)
    assert all(card.findChild(QLabel, "contractCardTitle") is not None for card in cards)
    assert all(card.findChild(QLabel, "contractCardStatus") is not None for card in cards)
    assert sum(len(card.findChildren(QFrame, "contractRequirementRow")) for card in cards) == 0
    assert sum(card.findChild(QComboBox, "contractProductSelect") is not None for card in cards) == 2
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
    assert [label.text() for label in header.findChildren(QLabel, "contractsMetricLabel")] == ["DAILY RESET", "WEEKLY RESET"]

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
    assert len(cards) == 3
    assert len({card.height() for card in cards}) == 1
    assert all(card.minimumHeight() >= 270 and card.maximumHeight() > 198 for card in cards)
    assert all(not card.findChildren(QProgressBar, "contractRequirementProgress") for card in cards)
    assert sum(bool(card.findChildren(QLabel, "contractRequirementAmount")) for card in cards) == 2
    product_selects = [card.findChild(QComboBox, "contractProductSelect") for card in cards]
    assert sum(select is not None and select.count() > 0 for select in product_selects) == 2
    assert all(card.findChildren(QFrame, "contractRewardChip") for card in cards)


def test_contract_cta_hierarchy_uses_gold_accept_and_red_cancel() -> None:
    accept_style = _style_block("QPushButton#acceptContractButton")
    cancel_style = _style_block("QPushButton#cancelContractButton")
    assert Theme.SAFETY_YELLOW in accept_style
    assert "#f5a623" in accept_style
    assert "#b32228" in cancel_style


def test_contract_header_uses_dark_title_text_and_recessed_status_modules() -> None:
    title_style = _style_block("QLabel#contractsHeroTitle")
    subtitle_style = _style_block("QLabel#contractsHeroSubtitle")
    metric_style = _style_block("QFrame#contractsHeaderMetric")

    assert "color: #161a17" in title_style
    assert "color: #9a2f22" in subtitle_style
    assert "rgba(38, 44, 42" in metric_style
    assert "border-left: 3px solid rgba(255, 210, 31, 150)" in metric_style
    assert "#e8ebe3" not in metric_style


def test_main_tab_headers_share_charts_chassis_and_typography() -> None:
    _app()
    _load_header_typography_probe_fonts()
    window = _main_window_with_charts()
    window.resize(1500, 950)
    window.show()
    try:
        QApplication.processEvents()
        for cls in (InventoryView, MarketView, PacksView):
            legacy_component(window, cls)
        headers = [
            window.findChild(QFrame, "inventoryCardsHeader"),
            window.findChild(QFrame, "chartsHeader"),
            window.findChild(QFrame, "marketHeader"),
            window.findChild(QFrame, "contractsHeader"),
            window.findChild(QFrame, "packsHeader"),
            window.findChild(QFrame, "supplyStoreHeader"),
            window.findChild(QFrame, "leaderboardPageHeader"),
        ]
        assert all(header is not None for header in headers)
        for header in headers:
            # Contracts intentionally adapts its height and vertical margins.
            if header.objectName() == "contractsHeader":
                assert header.height() in (84, 116)
                continue
            assert header.minimumHeight() == MAIN_TAB_HEADER_HEIGHT
            assert header.maximumHeight() == MAIN_TAB_HEADER_HEIGHT
            layout = header.layout()
            assert isinstance(layout, QHBoxLayout)
            assert layout.contentsMargins().left() == MAIN_TAB_HEADER_MARGINS[0]
            assert layout.contentsMargins().top() == MAIN_TAB_HEADER_MARGINS[1]
            assert layout.contentsMargins().right() == MAIN_TAB_HEADER_MARGINS[2]
            assert layout.contentsMargins().bottom() == MAIN_TAB_HEADER_MARGINS[3]
            assert layout.spacing() == MAIN_TAB_HEADER_SPACING
            title_column = layout.itemAt(0).layout()
            assert isinstance(title_column, QVBoxLayout)
            assert title_column.spacing() == MAIN_TAB_TITLE_SPACING

        title_style = _style_block(
            "QLabel#inventoryHeroTitle, QLabel#chartsHeroTitle, QLabel#marketHeroTitle,\n"
            "QLabel#contractsHeroTitle, QLabel#packsHeaderTitle, QLabel#supplyStoreTitle,\n"
            "QLabel#leaderboardHeroTitle"
        )
        subtitle_style = _style_block(
            "QLabel#inventoryHeroSubtitle, QLabel#chartsHeroSubtitle, QLabel#marketHeroSubtitle,\n"
            "QLabel#contractsHeroSubtitle, QLabel#packsHeaderSubtitle, QLabel#supplyStoreSubtitle,\n"
            "QLabel#leaderboardHeroSubtitle"
        )
        assert "font-size: 38px" in title_style
        assert 'font-family: "Segoe UI"' in title_style
        assert "font-weight: 900" in title_style
        assert "color: #161a17" in title_style
        assert "font-size: 12px" in subtitle_style
        assert 'font-family: "Segoe UI"' in subtitle_style
        assert "font-weight: 900" in subtitle_style
        assert "color: #9a2f22" in subtitle_style
        assert window.findChild(ResourceIconWidget, "packsHeaderIcon") is None
        assert window.findChild(ResourceIconWidget, "supplyStoreIcon") is None
        assert all(isinstance(header.layout().itemAt(0).layout().itemAt(0).widget(), MainTabHeaderLabel) for header in headers)
        assert all(header.layout().itemAt(0).layout().itemAt(0).widget()._embolden_offset == MAIN_TAB_TITLE_EMBOLDEN_OFFSET for header in headers)
        assert all(header.layout().itemAt(0).layout().itemAt(1).widget()._embolden_offset == MAIN_TAB_SUBTITLE_EMBOLDEN_OFFSET for header in headers)
        for label in [
            window.findChild(QLabel, "inventoryHeroTitle"),
            window.findChild(QLabel, "chartsHeroTitle"),
            window.findChild(QLabel, "marketHeroTitle"),
            window.findChild(QLabel, "contractsHeroTitle"),
            window.findChild(QLabel, "packsHeaderTitle"),
            window.findChild(QLabel, "supplyStoreTitle"),
            window.findChild(QLabel, "leaderboardHeroTitle"),
            window.findChild(QLabel, "inventoryHeroSubtitle"),
            window.findChild(QLabel, "chartsHeroSubtitle"),
            window.findChild(QLabel, "marketHeroSubtitle"),
            window.findChild(QLabel, "contractsHeroSubtitle"),
            window.findChild(QLabel, "packsHeaderSubtitle"),
            window.findChild(QLabel, "supplyStoreSubtitle"),
            window.findChild(QLabel, "leaderboardHeroSubtitle"),
        ]:
            assert label is not None
            font_info = QFontInfo(label.font())
            print(
                "main-tab font resolution:",
                label.objectName(),
                "requested_family=",
                label.font().family(),
                "requested_weight=",
                label.font().weight(),
                "resolved_family=",
                font_info.family(),
                "resolved_weight=",
                font_info.weight(),
                "resolved_style=",
                font_info.styleName(),
            )
            assert label.font().family() == "Segoe UI"
            assert label.font().weight() == 900
            assert font_info.family() == "Segoe UI"
            assert font_info.weight() >= 700
    finally:
        window.close()
        QApplication.processEvents()


def test_contracts_passive_refresh_and_hover_do_not_rebuild_board_or_mutate_data() -> None:
    _app()
    window = MainWindow()
    contracts_view = window.findChild(ContractsView)
    assert contracts_view is not None

    cards_before = {
        (card.property("kind"), card.property("contractId")): card
        for card in contracts_view.findChildren(QFrame, "contractCard")
    }
    signature_before = contracts_view._build_content_signature()
    rebuild_count = contracts_view._content_rebuild_count
    first_card = next(iter(cards_before.values()))

    for _ in range(4):
        QApplication.sendEvent(first_card, QEvent(QEvent.Type.Enter))
        QApplication.sendEvent(first_card, QEvent(QEvent.Type.Leave))
        contracts_view.refresh()
        QApplication.processEvents()

    cards_after = {
        (card.property("kind"), card.property("contractId")): card
        for card in contracts_view.findChildren(QFrame, "contractCard")
    }
    assert contracts_view._build_content_signature() == signature_before
    assert contracts_view._content_rebuild_count == rebuild_count
    assert cards_after == cards_before


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


def test_contract_automatically_activates_one_fixed_card_per_category() -> None:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    cards = _contract_cards_by_kind(view, "regular")
    assert len(cards) == 1
    card = cards[0]
    assert card.property("state") == "available"
    assert card.findChild(QLabel, "contractCardStatus").text() == "AVAILABLE"
    assert card.findChild(QPushButton, "cancelContractButton") is None
    assert not card.findChild(QPushButton, "acceptContractButton").isEnabled()
    count = view._content_rebuild_count
    snapshot = dict(view._state.contracts.offers["regular"][0].requirements)
    view.refresh()
    assert view._content_rebuild_count == count
    assert view._state.contracts.offers["regular"][0].requirements == snapshot == {}
    assert 'regular' not in view._state.contracts.active


def test_contract_active_card_shows_requirements_and_automatic_delivery() -> None:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    _install_contract_test_freight(view)
    view._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    for rid in ("iron_ore", "coal", "copper_ore", "steel"):
        view._state.ensure_resource(rid).amount = 1
    view.refresh()
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(view._state, view._definitions, 'regular')
    view.refresh()
    active = view._state.contracts.active['regular']
    original_id = active.offer.contract_id
    for other_kind, other in view._state.contracts.active.items():
        if other_kind != 'regular':
            other.status = "completed"  # controlled category fixture, no competing cargo demand
    _fund_contract_resources(view, active.offer.requirements, ratio=0.5)
    cash = view._state.cash.amount
    rp = view._state.research.total_earned
    level = view._state.company.level
    engine = SimulationEngine(view._definitions)
    engine.advance_time(view._state, 0)
    assert active.delivered == {} and view._state.cash.amount == cash
    assert view._state.freight.outbound_shipments
    from math import ceil
    capacities = {rid: sum(view._definitions[view._state.cards[cid].definition_id].base_capacity * view._state.cards[cid].output_multiplier
                          for cid, route in view._state.freight.assignments.items() if route.resource_id == rid)
                  for rid in active.offer.requirements}
    attempts = 2 + max(ceil(amount / max(1., capacities[rid])) for rid, amount in active.offer.requirements.items())
    for _ in range(attempts):
        engine.advance_time(view._state, 240)
        if active.status == "completed":
            break
    view.refresh()
    card = _contract_cards_by_kind(view, "regular")[0]
    assert active.status == "active"
    assert card.findChild(QPushButton, "deliverContractButton") is None
    assert card.findChild(QPushButton, "cancelContractButton").isEnabled()
    amounts = card.findChildren(QLabel, "contractRequirementAmount")
    assert len(amounts) == len(active.offer.requirements)
    assert all(0 < label.property("progressPermille") <= 500 for label in amounts)
    assert view._state.cash.amount == cash


def test_regular_contract_completion_regenerates_offers_unchanged() -> None:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    _install_contract_test_freight(view)
    view._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    for rid in ("iron_ore", "coal", "copper_ore", "steel"):
        view._state.ensure_resource(rid).amount = 1
    view.refresh()
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(view._state, view._definitions, 'regular')
    view.refresh()
    active = view._state.contracts.active['regular']
    original_id = active.offer.contract_id
    for other_kind, other in view._state.contracts.active.items():
        if other_kind != 'regular':
            other.status = "completed"  # controlled category fixture, no competing cargo demand
    _fund_contract_resources(view, active.offer.requirements, ratio=1.0)
    cash = view._state.cash.amount
    rp = view._state.research.total_earned
    level = view._state.company.level
    engine = SimulationEngine(view._definitions)
    engine.advance_time(view._state, 0)
    assert active.delivered == {} and view._state.cash.amount == cash
    assert view._state.freight.outbound_shipments
    from math import ceil
    capacities = {rid: sum(view._definitions[view._state.cards[cid].definition_id].base_capacity * view._state.cards[cid].output_multiplier
                          for cid, route in view._state.freight.assignments.items() if route.resource_id == rid)
                  for rid in active.offer.requirements}
    attempts = 2 + max(ceil(amount / max(1., capacities[rid])) for rid, amount in active.offer.requirements.items())
    for _ in range(attempts):
        engine.advance_time(view._state, 240)
        if active.status == "completed":
            break
    view.refresh()
    assert active.status == "completed"
    assert active.delivered == active.offer.requirements
    assert view._state.cash.amount == cash + active.offer.reward_cash
    assert view._state.company_xp_progress.xp_by_source['regular_contracts'] == active.offer.reward_xp
    assert view._state.packs.unopened == []
    assert view._state.research.total_earned == rp + 0 + view._state.company.level - level
    cards = _contract_cards_by_kind(view, 'regular')
    assert len(cards) == 1
    assert cards[0].property("contractId") != original_id
    assert cards[0].property("state") == "available"


def test_daily_completed_card_remains_visible_until_reset_with_rewards() -> None:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    _install_contract_test_freight(view)
    view._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    for rid in ("iron_ore", "coal", "copper_ore", "steel"):
        view._state.ensure_resource(rid).amount = 1
    view.refresh()
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(view._state, view._definitions, 'daily')
    view.refresh()
    active = view._state.contracts.active['daily']
    original_id = active.offer.contract_id
    for other_kind, other in view._state.contracts.active.items():
        if other_kind != 'daily':
            other.status = "completed"  # controlled category fixture, no competing cargo demand
    _fund_contract_resources(view, active.offer.requirements, ratio=1.0)
    cash = view._state.cash.amount
    rp = view._state.research.total_earned
    level = view._state.company.level
    engine = SimulationEngine(view._definitions)
    engine.advance_time(view._state, 0)
    assert active.delivered == {} and view._state.cash.amount == cash
    assert view._state.freight.outbound_shipments
    from math import ceil
    capacities = {rid: sum(view._definitions[view._state.cards[cid].definition_id].base_capacity * view._state.cards[cid].output_multiplier
                          for cid, route in view._state.freight.assignments.items() if route.resource_id == rid)
                  for rid in active.offer.requirements}
    attempts = 2 + max(ceil(amount / max(1., capacities[rid])) for rid, amount in active.offer.requirements.items())
    for _ in range(attempts):
        engine.advance_time(view._state, 240)
        if active.status == "completed":
            break
    view.refresh()
    assert active.status == "completed"
    assert active.delivered == active.offer.requirements
    assert view._state.cash.amount == cash + active.offer.reward_cash
    assert view._state.company_xp_progress.xp_by_source['daily_contracts'] == active.offer.reward_xp
    assert view._state.packs.unopened == []
    assert view._state.research.total_earned == rp + 1 + view._state.company.level - level
    cards = _contract_cards_by_kind(view, 'daily')
    assert len(cards) == 1
    assert cards[0].property("contractId") == original_id
    assert cards[0].property("state") == "completed"
    assert not cards[0].findChild(QPushButton, "claimContractButton").isEnabled()
    assert all(label.property("progressPermille") == 1000 for label in cards[0].findChildren(QLabel, "contractRequirementAmount"))


def test_weekly_completed_card_remains_visible_until_reset_with_full_pack_reward() -> None:
    _app()
    window = MainWindow()
    view = window.findChild(ContractsView)
    _install_contract_test_freight(view)
    view._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    for rid in ("iron_ore", "coal", "copper_ore", "steel"):
        view._state.ensure_resource(rid).amount = 1
    view.refresh()
    from tests.contract_acceptance_fixture import accept_fixture
    accept_fixture(view._state, view._definitions, 'weekly')
    view.refresh()
    active = view._state.contracts.active['weekly']
    original_id = active.offer.contract_id
    for other_kind, other in view._state.contracts.active.items():
        if other_kind != 'weekly':
            other.status = "completed"  # controlled category fixture, no competing cargo demand
    _fund_contract_resources(view, active.offer.requirements, ratio=1.0)
    cash = view._state.cash.amount
    rp = view._state.research.total_earned
    level = view._state.company.level
    engine = SimulationEngine(view._definitions)
    engine.advance_time(view._state, 0)
    assert active.delivered == {} and view._state.cash.amount == cash
    assert view._state.freight.outbound_shipments
    from math import ceil
    capacities = {rid: sum(view._definitions[view._state.cards[cid].definition_id].base_capacity * view._state.cards[cid].output_multiplier
                          for cid, route in view._state.freight.assignments.items() if route.resource_id == rid)
                  for rid in active.offer.requirements}
    attempts = 2 + max(ceil(amount / max(1., capacities[rid])) for rid, amount in active.offer.requirements.items())
    for _ in range(attempts):
        engine.advance_time(view._state, 240)
        if active.status == "completed":
            break
    view.refresh()
    assert active.status == "completed"
    assert active.delivered == active.offer.requirements
    assert view._state.cash.amount == cash + active.offer.reward_cash
    assert view._state.company_xp_progress.xp_by_source['weekly_contracts'] == active.offer.reward_xp
    assert view._state.packs.unopened == []
    assert view._state.research.total_earned == rp + 3 + view._state.company.level - level
    cards = _contract_cards_by_kind(view, 'weekly')
    assert len(cards) == 1
    assert cards[0].property("contractId") == original_id
    assert cards[0].property("state") == "completed"
    assert not cards[0].findChild(QPushButton, "claimContractButton").isEnabled()
    assert all(label.property("progressPermille") == 1000 for label in cards[0].findChildren(QLabel, "contractRequirementAmount"))


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
    assert supply_view.findChild(QFrame, "supplyStoreHeader") is not None
    assert supply_view.findChild(QLabel, "supplyStoreTitle").text() == "INDUSTRIAL SUPPLY"
    header_metric_labels = [label.text() for label in supply_view.findChildren(QLabel, "supplyHeaderMetricLabel")]
    assert header_metric_labels.count("DAILY RESET") == 1
    assert supply_view.findChild(QFrame, "supplySectionHeader") is None
    daily_section_subtitles = [label.text() for label in supply_view.findChildren(QLabel, "supplyDailySectionSubtitle")]
    daily_section_titles = [label.text() for label in supply_view.findChildren(QLabel, "supplyDailySectionTitle")]
    assert daily_section_subtitles == ["CHOOSE 1 OF 4", "CHOOSE 1 OF 4"]
    assert daily_section_titles == ["DAILY FREIGHT", "DAILY MACHINES"]
    assert supply_view._daily_module_columns_used == 2
    assert len(supply_view._common_display_data) == 15
    assert supply_view._type_filter.itemText(0) == "All"
    assert supply_view.findChild(QFrame, "supplyHeaderMetric") is not None
    assert len(daily_cards) == DAILY_SUPPLY_VISIBLE_CARDS
    assert len(freight_daily_cards) == DAILY_SUPPLY_VISIBLE_CARDS
    assert len(machine_daily_cards) == DAILY_SUPPLY_VISIBLE_CARDS
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in daily_cards}) == DAILY_SUPPLY_VISIBLE_CARDS
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in freight_daily_cards}) == DAILY_SUPPLY_VISIBLE_CARDS
    assert len({card.findChild(QLabel, "supplyCardName").text() for card in machine_daily_cards}) == DAILY_SUPPLY_VISIBLE_CARDS
    assert all(card.property("cardKind") in {"machine", "energy"} for card in daily_cards)
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
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton") is not None for card in daily_cards)
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton") is not None for card in freight_daily_cards)
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton") is not None for card in machine_daily_cards)
    bands = supply_view.findChildren(QFrame, "supplyDailyOfferBand")
    assert len(bands) == 2
    assert len({band.height() for band in bands}) == 1
    assert all(band.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding for band in bands)
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    type_filter = supply_view._type_filter
    assert type_filter is not None
    assert type_filter.isVisible()
    assert supply_view.findChild(QComboBox, "supplyMkFilter") is None
    assert supply_view.findChild(QComboBox, "supplySortSelect") is None
    assert not supply_view.findChildren(QPushButton, "supplyFilterChip")
    assert supply_view.findChild(QPushButton, "supplyMachineSelector") is None
    assert supply_view.findChild(QPushButton, "supplySortSelector") is None
    type_filter.setCurrentText("Resources")
    QApplication.processEvents()
    extractor = next(card for card in _visible_common_supply_cards(supply_view) if card.findChild(QLabel, "supplyCardName").text() == "Extractor")
    assert extractor.findChild(QLabel, "supplyCardBonus").text() == "+0.0%"
    assert "Output" in extractor.findChild(QLabel, "supplyCardOutput").text()
    assert "Power Demand" in extractor.findChild(QLabel, "supplyCardPower").text()
    assert extractor.findChild(QLabel, "supplyCardPrice").text().startswith("$")
    type_filter.setCurrentText("Freight")
    QApplication.processEvents()
    truck = next(card for card in _visible_common_supply_cards(supply_view) if card.findChild(QLabel, "supplyCardName").text() == "Freight Truck")
    assert truck.findChild(QLabel, "supplyCardBonus").text() == "+0.0%"
    assert "Transport Capacity" in truck.findChild(QLabel, "supplyCardOutput").text()
    assert "Transport Time" in truck.findChild(QLabel, "supplyCardPower").text()
    assert truck.findChild(ResourceIconWidget, "supplyCardIcon").accent_key == "truck"
    common_scroll = supply_view.findChild(QScrollArea, "commonSupplyScroll")
    assert common_scroll is not None
    assert common_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_industrial_supply_filter_chips_survive_refresh_and_activate_on_one_click() -> None:
    _app()
    window = MainWindow(); window.resize(1600,1000); window.show()
    supply = window.findChild(SupplyView)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(supply)
    supply._show_section(1); QApplication.processEvents()
    selector = supply._type_filter
    assert not supply.findChildren(QPushButton, "supplyFilterChip")
    for category in ("Resources", "Factory", "Energy", "Freight"):
        selector.setCurrentText(category); supply.refresh(); QApplication.processEvents()
        assert supply._type_filter is selector and selector.currentText()==category
        assert supply._filtered_common_data
        assert all(supply._supply_category(item.definition)==category for item in supply._filtered_common_data)
    window.close()


def test_industrial_supply_daily_cards_use_static_bands_without_stretching() -> None:
    _app()
    window = MainWindow()
    window.resize(1920, 1080)
    window.show()
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()

    recipe_section = supply_view.findChild(QFrame, "supplyDailyMachineSection")
    band = recipe_section.findChild(QFrame, "supplyDailyOfferBand")
    cards = recipe_section.findChildren(QFrame, "dailyMachineSupplyCard")
    assert band is not None
    assert len(cards) == DAILY_SUPPLY_VISIBLE_CARDS
    cards = sorted(cards, key=lambda card: (card.y(), card.x()))
    gallery = recipe_section.findChild(QScrollArea, "supplyDailyOfferScroll")
    assert gallery is not None
    assert gallery.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert gallery.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert gallery.horizontalScrollBar().maximum() == 0
    assert gallery.verticalScrollBar().maximum() == 0
    assert band.width() == gallery.viewport().width()
    assert band.height() == gallery.viewport().height()
    assert band.height() > FEATURED_SUPPLY_CARD_HEIGHT
    assert all(card.width() <= FEATURED_SUPPLY_CARD_WIDTH for card in cards)
    assert all(card.height() <= FEATURED_SUPPLY_CARD_HEIGHT for card in cards)
    assert {(card.width(), card.height()) for card in cards} == {(cards[0].width(), cards[0].height())}
    assert abs(cards[0].height() / cards[0].width() - FEATURED_SUPPLY_CARD_HEIGHT / FEATURED_SUPPLY_CARD_WIDTH) < 0.02
    assert all(card.geometry().bottom() <= band.height() for card in cards)
    visible_right = gallery.viewport().rect().right()
    assert all(card.mapTo(gallery.viewport(), card.rect().topRight()).x() <= visible_right for card in cards)
    rows = sorted({card.y() for card in cards})
    columns = sorted({card.x() for card in cards})
    assert len(rows) == 1
    assert len(columns) == 4
    assert sum(1 for card in cards if card.y() == rows[0]) == 4
    assert all(sum(1 for card in cards if card.x() == column) == 1 for column in columns)
    gaps = [
        cards[index + 1].mapTo(recipe_section, cards[index + 1].rect().topLeft()).x()
        - cards[index].mapTo(recipe_section, cards[index].rect().topRight()).x()
        for index in range(DAILY_SUPPLY_VISIBLE_CARDS - 1)
        if cards[index].y() == cards[index + 1].y()
    ]
    assert all(0 < gap <= 18 for gap in gaps)
    section_heights = [
        supply_view.findChild(QFrame, "supplyDailyMachineSection").height(),
        supply_view.findChild(QFrame, "supplyDailyFreightSection").height(),
        supply_view.findChild(QFrame, "supplyDailyMachineSection").height(),
    ]
    assert len(set(section_heights)) == 1
    window.close()


def test_train_purchase_button_uses_the_global_supply_action_style() -> None:
    assert '[freightFamily="train"] QPushButton#buyDailyFreightSupplyButton' not in APP_STYLESHEET
    assert '[freightFamily="train"] QPushButton#buyCommonSupplyButton' not in APP_STYLESHEET
    global_rule = _style_block(
        "QFrame#dailyFreightSupplyCard QPushButton#buyDailyFreightSupplyButton,\n"
        "QFrame#dailyMachineSupplyCard QPushButton#buyDailyMachineSupplyButton,\n"
        "QFrame#commonSupplyCard QPushButton#buyCommonSupplyButton"
    )
    assert Theme.SAFETY_YELLOW in global_rule


def test_industrial_supply_selector_and_header_use_modern_light_dark_hierarchy() -> None:
    header_style = _style_block("QFrame#supplyStoreHeader")
    metric_style = _style_block("QFrame#supplyHeaderMetric")
    tab_style = _style_block("QPushButton#supplySectionButton")
    active_tab_style = _style_block('QPushButton#supplySectionButton[active="true"]')

    assert "#806222" not in header_style
    assert "background: transparent" in header_style
    assert "border: 0" in header_style
    assert "rgba(38, 44, 42" in metric_style
    assert "color: #171c19" in tab_style
    assert "rgba(232, 231, 220, 168)" in tab_style
    assert "rgba(255, 210, 31, 145)" in active_tab_style
    assert Theme.TEXT in active_tab_style


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
        ("supplyDailyMachineSection", "industrial_supply_daily_recipes_preview.png"),
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
    inventory_view = legacy_component(window, InventoryView)
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
    for family in ("rail_station", "airport", "harbor"):
        build_freight_facility(supply_view._state.freight, family)
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
        "QLabel#supplyFreightDailyStatus",
        "QLabel#supplyCommonStatus",
        "QLabel#supplyCardName",
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
    type_filter = supply_view._type_filter
    assert type_filter is not None
    type_filter.setCurrentText("All")
    QApplication.processEvents()
    QApplication.processEvents()
    _flush_deferred_deletes()

    scroll = supply_view.findChild(QScrollArea, "commonSupplyScroll")
    assert scroll is not None
    cards = supply_view._common_card_pool
    assert 0 < len(cards) <= len(supply_view._common_display_data)
    assert supply_view._common_grid_columns_used >= 5
    assert supply_view._common_grid_rows_used >= 1
    assert scroll.horizontalScrollBar().maximum() == 0
    assert supply_view._common_grid_container.minimumHeight() >= COMMON_SUPPLY_CARD_HEIGHT

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
        assert price.geometry().top() >= card.height() - 44
        assert button.geometry().top() >= card.height() - 44
        assert price.geometry().right() < button.geometry().left()
        if card.property("cardKind") in {"machine", "energy"}:
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


def test_common_supply_empty_and_sparse_results_use_shared_polished_composition() -> None:
    _app()
    window=MainWindow();window.resize(1280,820);window.show()
    # This case supplies synthetic empty/sparse catalog projections. Keep the
    # live runtime timer from replacing that fixture during event processing.
    window.findChild(FactoryViewV2).pause_simulation()
    supply_view=window.findChild(SupplyView)
    window.findChild(QTabWidget,"mainTabs").setCurrentWidget(supply_view)
    supply_view._show_section(1);QApplication.processEvents()
    assert supply_view.findChild(QLineEdit,"supplySearch") is None
    scroll=supply_view._common_scroll
    original=list(supply_view._common_display_data)
    # A genuinely empty category, and sparse catalog fixtures: search is retired.
    supply_view._common_display_data=[];supply_view._apply_common_filter();QApplication.processEvents()
    empty=supply_view.findChild(EmptyStatePanel,"commonSupplyEmptyState")
    assert empty.isVisible() and empty.property("emptyStatePanel") is True
    assert empty.findChild(QLabel,"emptyStateTitle").text()=="NO COMMON SUPPLY CARDS"
    assert not _visible_common_supply_cards(supply_view)
    for name,category in (("Processor","Factory"),("Extractor","Resources")):
        supply_view._common_display_data=[item for item in original if item.name==name]
        supply_view._type_filter.setCurrentText(category);supply_view._apply_common_filter();QApplication.processEvents()
        cards=_visible_common_supply_cards(supply_view)
        assert len(cards)==1 and empty.isHidden()
        assert cards[0].x()==COMMON_SUPPLY_LEFT_PADDING
        assert (cards[0].width(),cards[0].height())==(COMMON_SUPPLY_CARD_WIDTH,COMMON_SUPPLY_CARD_HEIGHT)
        assert scroll.horizontalScrollBar().maximum()==0
    window.close()


def test_common_supply_uses_exclusive_x1_x4_chips_and_preserves_quantity_purchase() -> None:
    _app()
    window=MainWindow();window.resize(1366,768);window.show()
    supply_view=window.findChild(SupplyView)
    window.findChild(QTabWidget,"mainTabs").setCurrentWidget(supply_view)
    supply_view._show_section(1);supply_view._bus.dispatch(AddCash(50_000));supply_view.refresh();QApplication.processEvents()
    assert supply_view.findChild(QComboBox,"supplyBuyQuantity") is None
    assert not supply_view.findChildren(QPushButton,"supplyFilterChip")
    for category in ("Resources","Energy","Freight","Factory"):
        supply_view._type_filter.setCurrentText(category);QApplication.processEvents()
        cards=_visible_common_supply_cards(supply_view)
        assert cards and min(card.x() for card in cards)==COMMON_SUPPLY_LEFT_PADDING
    card=_visible_common_supply_cards(supply_view)[0];offer=card._supply_data.offer
    owned=supply_view._owned_count(offer)
    assert card._price_label.text()==supply_view._display_data_for_offer(offer).price_text
    # The existing modal driver chooses four inside the real purchase dialog.
    supply_view._pending_purchase_quantity=4
    card._buy_button.click();supply_view._pending_purchase_quantity=None;QApplication.processEvents()
    assert supply_view._owned_count(offer)==owned+4
    window.close()


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
    type_filter = supply_view._type_filter
    assert type_filter is not None
    type_filter.setCurrentText("All")
    QApplication.processEvents()

    from dataclasses import replace
    card = supply_view._common_card_pool[0]
    long_index, short_index = 0, 1
    supply_view._filtered_common_data[long_index] = replace(supply_view._filtered_common_data[long_index], name="Advanced Industrial Processing Machine")
    pool_size = len(supply_view._common_card_pool)

    for data_index in (long_index, short_index, long_index):
        supply_view._bind_common_card_widget(card, data_index)
        card.show()
        QApplication.processEvents()
        title = card.findChild(QLabel, "supplyCardName")
        rarity = card.findChild(QLabel, "supplyCardRarity")
        rarity_line = card.findChild(QFrame, "supplyRarityLine")
        assert title is not None
        assert rarity is not None
        assert rarity_line is not None
        assert isinstance(card, SupplyOfferCardFrame)
        assert card.objectName() == "commonSupplyCard"
        assert title.property("displayText")
        assert "MK" not in str(title.property("displayText"))
        assert rarity.text() in {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
        assert card.width() == COMMON_SUPPLY_CARD_WIDTH
        assert card.height() == COMMON_SUPPLY_CARD_HEIGHT

    assert len(supply_view._common_card_pool) == pool_size




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
    daily_style = _style_block("QFrame#dailyFreightSupplyCard, QFrame#dailyMachineSupplyCard")
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
    supply_view._type_filter.setCurrentText("All")
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
    assert len(supply_view._common_card_pool) <= len(supply_view._common_display_data)


def test_common_supply_card_click_does_not_open_detail_overlay_and_buy_refresh_hover_are_stable() -> None:
    _app()
    window = MainWindow()
    window.resize(1600, 1000)
    window.show()
    factory = window.findChild(FactoryViewV2)
    supply_view = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget)
    assert factory is not None
    assert supply_view is not None
    assert tabs is not None
    tabs.setCurrentWidget(supply_view)
    QApplication.processEvents()
    supply_view.findChildren(QPushButton, "supplySectionButton")[1].click()
    QApplication.processEvents()
    supply_view._type_filter.setCurrentText("All")
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
    window=MainWindow();window.resize(1366,768);window.show()
    supply_view=window.findChild(SupplyView)
    window.findChild(QTabWidget,"mainTabs").setCurrentWidget(supply_view)
    supply_view._show_section(1);QApplication.processEvents()
    assert supply_view.findChild(QLineEdit,"supplySearch") is None
    selector=supply_view._type_filter
    for category in ("Factory","Resources","Energy","Freight","Factory"):
        before=supply_view._common_filter_apply_count
        selector.setCurrentText(category);QApplication.processEvents();_flush_deferred_deletes()
        assert supply_view._common_filter_apply_count>=before
        cards=_visible_common_supply_cards(supply_view)
        ids=[card.property("definitionId") for card in cards]
        assert ids and len(ids)==len(set(ids))
        assert all(supply_view._supply_category(item.definition)==category for item in supply_view._filtered_common_data)
        assert len(cards)<=len(supply_view._filtered_common_data)<len(supply_view._common_display_data)
        assert len(supply_view._common_card_pool)<=len(supply_view._common_display_data)
    window.close()






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

    type_filter = supply_view._type_filter
    assert type_filter is not None
    assert "Energy" in [type_filter.itemText(index) for index in range(type_filter.count())]
    type_filter.setCurrentText("Energy")
    QApplication.processEvents()

    cards = _visible_common_supply_cards(supply_view)
    assert {item.definition_id for item in supply_view._filtered_common_data} == {
        "energy.solar_array",
        "energy.wind_turbine",
        "energy.coal_power_plant",
        "energy.gas_power_plant",
        "energy.nuclear_power_plant",
    }
    assert cards
    solar = next(card for card in cards if card.findChild(QLabel, "supplyCardName").text() == "Solar Array")
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
    daily_cards[0].findChild(QPushButton, "buyDailyMachineSupplyButton").click()

    daily_cards = _daily_supply_cards(supply_view)
    chosen = next(card for card in daily_cards if card.property("offerId") == chosen_offer_id)
    locked = [card for card in daily_cards if card.property("offerId") != chosen_offer_id]

    assert chosen.property("state") == "purchased"
    assert chosen.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "PURCHASED"
    assert not chosen.findChild(QPushButton, "buyDailyMachineSupplyButton").isEnabled()
    assert all(card.property("state") == "locked" for card in locked)
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "LOCKED\nUNTIL RESET" for card in locked)
    assert all(not card.findChild(QPushButton, "buyDailyMachineSupplyButton").isEnabled() for card in locked)
    assert supply_view._state.supply.machine_daily_purchased_offer_id == chosen_offer_id


def test_daily_freight_supply_purchase_marks_purchased_and_stays_independent_from_daily_supply() -> None:
    _app()
    window = MainWindow()
    supply_view = window.findChild(SupplyView)
    assert supply_view is not None
    for family in ("rail_station", "airport", "harbor"):
        build_freight_facility(supply_view._state.freight, family)
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
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton").text() == "LOCKED\nUNTIL RESET" for card in locked)
    assert all(not card.findChild(QPushButton, "buyDailyFreightSupplyButton").isEnabled() for card in locked)
    assert supply_view._state.supply.freight_daily_purchased_offer_id == chosen_offer_id

    daily_cards = _daily_supply_cards(supply_view)
    daily_card = next(card for card in daily_cards if card.property("offerId") == daily_offer_id)
    assert daily_card.property("state") == "available"
    assert daily_card.findChild(QPushButton, "buyDailyMachineSupplyButton").isEnabled()
    daily_card.findChild(QPushButton, "buyDailyMachineSupplyButton").click()
    assert supply_view._state.supply.machine_daily_purchased_offer_id == daily_offer_id


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
    _daily_supply_cards(supply_view)[0].findChild(QPushButton, "buyDailyMachineSupplyButton").click()
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
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "BUY" for card in reset_cards)
    assert reset_freight_ids != initial_freight_ids
    assert all(card.property("state") == "available" for card in reset_freight_cards)
    assert all(card.findChild(QPushButton, "buyDailyFreightSupplyButton").text() == "BUY" for card in reset_freight_cards)
    assert reset_machine_ids != initial_machine_ids
    assert all(card.property("state") == "available" for card in reset_machine_cards)
    assert all(card.findChild(QPushButton, "buyDailyMachineSupplyButton").text() == "BUY" for card in reset_machine_cards)


def test_packs_tab_shows_unopened_packs_and_open_results() -> None:
    _app()
    window = _main_window_with_dev_tools()
    window.resize(1400, 900)
    window.show()
    packs_view = legacy_component(window, PacksView)
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
    assert not packs_view.findChildren(QLabel, "packsHeaderMetricValue")
    assert packs_view.findChild(QFrame, "packsUnopenedHeader") is None
    assert packs_view.findChild(QLabel, "packsUnopenedCount") is None
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
    assert [option.property("active") for option in options].count(True) == 1
    assert next(option for option in options if option.property("active") is True).text() == "FREIGHT"
    assert packs_view.grab().toImage().save(str(artifacts / "packs_full_pack_category_flyout_preview.png"))

    open_button.click()
    QApplication.processEvents()
    _flush_deferred_deletes()

    assert stack.currentIndex() == 1
    assert packs_view.findChild(QFrame, "packResultHeader") is not None
    assert packs_view.grab().toImage().save(str(artifacts / "packs_open_results_preview.png"))
    assert len(_booster_pack_tiles(packs_view)) == 2
    assert all(tile.findChild(QLabel, "boosterPackQuantity") is None for tile in _booster_pack_tiles(packs_view))
    assert packs_view.findChild(QLabel, "packResultsLabel") is None
    assert all(not c.is_revealed for c in packs_view._reveal_cards)
    _finish_pack_reveal(packs_view)
    result_tiles = _pack_result_tiles(packs_view)
    assert len(result_tiles) == 6
    assert all(isinstance(tile, InventoryCardFrame) for tile in result_tiles)
    assert all(tile.width() == INVENTORY_CARD_WIDTH and tile.height() == INVENTORY_CARD_HEIGHT for tile in result_tiles)
    assert all(tile.objectName() == "inventoryCard" for tile in result_tiles)
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


def test_packs_empty_state_uses_intentional_recessed_module() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    packs_view = legacy_component(window, PacksView)
    assert packs_view is not None
    packs_view.refresh()
    QApplication.processEvents()

    empty = packs_view.findChild(EmptyStatePanel, "packsEmptyState")
    assert empty is not None
    assert empty.property("emptyStatePanel") is True
    assert empty.findChild(QLabel, "emptyStateTitle").text() == "NO UNOPENED PACKS"
    assert "Complete contracts" in empty.findChild(QLabel, "emptyStateMessage").text()
    _flush_deferred_deletes()
    assert empty.findChild(ResourceIconWidget, "emptyStateIcon") is None
    assert empty.minimumHeight() >= 220
    assert packs_view._grid_container.minimumHeight() >= 260
    style = _style_block("QWidget#packsView QFrame#packsEmptyState")
    title_style = _style_block("QFrame#packsEmptyState QLabel#emptyStateTitle")
    message_style = _style_block("QFrame#packsEmptyState QLabel#emptyStateMessage")
    assert "border: 0" in style
    assert "font-size: 23px" in title_style
    assert "font-size: 14px" in message_style
    window.close()


def test_packs_sparse_unopened_and_result_cards_center_without_resizing() -> None:
    _app()
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    packs_view = legacy_component(window, PacksView)
    assert packs_view is not None

    for count in (1, 2):
        packs_view._state.packs.unopened.clear()
        for index in range(count):
            grant_pack(packs_view._state, DAILY_MINI_PACK, f"sparse-pack-{count}-{index}")
        packs_view.refresh(force=True)
        QApplication.processEvents()
        tiles = _booster_pack_tiles(packs_view)
        assert len(tiles) == count
        _assert_sparse_widget_group_centered(tiles, packs_view._grid_container, (tiles[0].width(), tiles[0].height()))
        assert packs_view.findChild(EmptyStatePanel, "packsEmptyState") is None

        # Stored last-opened rewards are not replayed when returning to Packs.
        packs_view._refresh_results(force=True)
        assert not packs_view._reveal_cards

    window.close()


def test_packs_gallery_renders_single_pack_as_one_card_without_quantity_badge() -> None:
    _app()
    window = MainWindow()
    window.resize(1100, 820)
    window.show()
    packs_view = legacy_component(window, PacksView)
    assert packs_view is not None

    grant_pack(packs_view._state, DAILY_MINI_PACK, "daily-contract")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()
    artifacts = Path("artifacts")
    artifacts.mkdir(exist_ok=True)
    assert packs_view.grab().toImage().save(str(artifacts / "packs_daily_mini_preview.png"))

    tiles = _booster_pack_tiles(packs_view)
    assert packs_view.findChild(QLabel, "packsUnopenedCount") is None
    assert len(tiles) == 1
    assert packs_view.findChild(EmptyStatePanel, "packsEmptyState") is None
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
    packs_view = legacy_component(window, PacksView)
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
            elif card.card_kind is CardKind.ENERGY:
                assert function_text.endswith(" RECIPE")
            elif card.card_kind is CardKind.FREIGHT:
                assert function_text in {"TRUCK", "TRAIN", "SHIP", "AIRCRAFT"}
            elif card.card_kind is CardKind.MACHINE:
                assert function_text in {"EXTRACTOR", "DRILLING RIG", "HARVESTER", "PROCESSOR", "FABRICATOR", "ASSEMBLER"}

        _finish_pack_reveal(packs_view)
        packs_view._confirm.click()

    assert set(opened_kind_counts) == {CardKind.MACHINE, CardKind.ENERGY, CardKind.ENERGY, CardKind.FREIGHT}
    assert opened_kind_counts[CardKind.ENERGY] < sum(opened_kind_counts.values()) * 0.4


def test_packs_gallery_expands_identical_inventory_to_individual_cards() -> None:
    _app()
    window = MainWindow()
    window.resize(1500, 950)
    window.show()
    packs_view = legacy_component(window, PacksView)
    assert packs_view is not None

    for _ in range(3):
        grant_pack(packs_view._state, DAILY_MINI_PACK, "daily-contract")
        grant_pack(packs_view._state, FULL_PACK, "weekly-contract")
    packs_view.refresh()
    QApplication.processEvents()
    _flush_deferred_deletes()

    tiles = _booster_pack_tiles(packs_view)
    assert packs_view.findChild(QLabel, "packsUnopenedCount") is None
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
    packs_view = legacy_component(window, PacksView)
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
    assert packs_view.findChild(QLabel, "packsUnopenedCount") is None

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
    packs_view = legacy_component(window, PacksView)
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
    packs_view = legacy_component(window, PacksView)
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
    window = _main_window_with_dev_tools()
    dev = window.findChild(DevToolsView)
    assert dev is not None

    dev._advance_time(300)

    assert dev._state.tick == 300
    assert dev._state.market.market_tick == 0


def test_dev_tools_can_set_cash_fill_clear_resources_and_create_cards() -> None:
    _app()
    window = _main_window_with_dev_tools()
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
    window = _main_window_with_dev_tools()
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


def test_dev_created_energy_card_can_be_selected_and_installed_from_plant_inventory() -> None:
    _app()
    window = _main_window_with_dev_tools()
    factory = window.findChild(EnergyViewV2)
    dev = window.findChild(DevToolsView)
    assert factory is not None
    assert dev is not None

    dev._card_select.setCurrentText("Solar Array")
    dev._card_count.setValue(1)
    dev._create_cards()

    factory._on_slot_clicked(0)
    _install_factory_card_from_selection(factory, "Solar Array")

    installed_id = factory._state.energy_plants["plant-1"].slots[0].card_id
    assert installed_id is not None
    assert factory._state.cards[installed_id].definition_id == "energy.solar_array"
    assert any(stack.first_card.definition_id == "energy.solar_array" for stack in factory._state.inventory_card_stacks())


def test_production_boards_install_only_their_owned_card_types() -> None:
    _app()
    window = MainWindow()
    factory = window.findChild(FactoryViewV2)
    resources = window.findChild(ResourcesViewV2)
    energy = window.findChild(EnergyViewV2)
    assert factory is not None
    assert resources is not None
    assert energy is not None

    for board, card_name in ((resources, "Extractor"), (energy, "Solar Array"), (factory, "Processor")):
        board._on_slot_clicked(0)
        _install_factory_card_from_selection(board, card_name)

    installed_definitions = [
        factory._state.cards[factory._state.resource_sites["site-1"].slots[0].card_id].definition_id,
        factory._state.cards[factory._state.energy_plants["plant-1"].slots[0].card_id].definition_id,
        factory._state.cards[factory._state.halls["hall-1"].slots[0].card_id].definition_id,
    ]
    assert installed_definitions == [
        "machine.extractor",
        "energy.solar_array",
        "machine.processor",
    ]




def test_dev_tools_can_pause_resume_and_reset_state() -> None:
    _app()
    window = _main_window_with_dev_tools()
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
    assert dev._state.halls["hall-1"].slot_count == 3
    assert dev._state.halls["hall-1"].max_lines == 5
    assert dev._state.resource_sites["site-1"].slot_count == 1
    assert dev._state.energy_plants["plant-1"].slot_count == 1
