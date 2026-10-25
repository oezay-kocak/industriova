from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QFontMetrics
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QTreeWidgetItem, QVBoxLayout, QWidget
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.cards import CardInstance
from production_zero.ui.release_board import ReleaseBoardMixin
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import EnergyType, MachineType
from production_zero.core.progression import production_options_for_machine
from production_zero.core.resources import ResourceDefinition
from production_zero.core.modifiers import research_multiplier
from production_zero.core.state import FactoryHall, GameState, HallSlot, MachineProductionState, ProductionLine, factory_slot_unlock_cost
from production_zero.core.infrastructure_prices import unit_line_price,unit_slot_price
from production_zero.core.storage_upgrades import MAX_INVENTORY_STORAGE_LEVEL, inventory_storage_upgrade_cost
from production_zero.core.commands import CommandBus, ExpandInventoryStorage
from production_zero.ui.factory_view import (
    ClickableCapacityPanel,
    FactoryViewBase,
    ProductionBoardConfig,
    HallResourceSummaryItemWidget,
    KpiStripWidget,
    HallResourceSummaryWidget,
)
from production_zero.ui.game_ui import (
    Accent,
    BuildSlotWidget,
    GAME_UI_TOKENS,
    GameButton,
    GameIcon,
    GameIconWidget,
    MachineIcon,
    MaterialLevel,
    StatusBadge,
    draw_game_panel,
    draw_track_surface,
)
from production_zero.ui.game_ui.rendering import (
    draw_build_slot,
    draw_command_chassis,
    draw_game_surface,
    draw_hall_control_assembly,
    draw_hazard_stripes,
    draw_industrial_base_surface,
    draw_locked_slot,
    draw_machine_card,
    draw_machine_card_prototype,
    draw_machine_icon_stage,
    draw_production_track,
    draw_selection_chassis,
    draw_status_led,
    draw_status_badge,
    draw_utility_chassis,
    draw_warning_plate,
)
from production_zero.ui.machine_art import machine_art_family_for_machine_type
from production_zero.ui.text_format import count_label


FACTORY_V2_RESOURCE_IDS = ("iron_ore", "iron", "copper_ore", "copper", "coal", "steel")
FACTORY_V2_CARD_WIDTH = 142
FACTORY_V2_CARD_HEIGHT = 226
FACTORY_V2_LOCKED_SLOT_WIDTH = FACTORY_V2_CARD_WIDTH
FACTORY_V2_LOCKED_SLOT_HEIGHT = FACTORY_V2_CARD_HEIGHT
FACTORY_V2_TRACK_HEIGHT = 274
PRIMARY_MACHINE_TYPES = frozenset({MachineType.EXTRACTOR, MachineType.DRILLING, MachineType.AGRICULTURE})


def _use_transparent_surface(widget: QWidget) -> None:
    widget.setAutoFillBackground(False)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    palette = widget.palette()
    palette.setColor(widget.backgroundRole(), QColor(0, 0, 0, 0))
    widget.setPalette(palette)


def _display_card_title(definition: CardDefinition | None, card: CardInstance | None = None) -> str:
    raw = definition.name if definition is not None else (card.definition_id if card else "Machine")
    return raw.upper()


def _compact_value(value):
    for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(value) >= threshold * .999995:
            return f"{value / threshold:.2f}".rstrip("0").rstrip(".") + suffix
    return f"{value:,.0f}"


class FactoryV2CommandModule(QFrame):
    def __init__(self, *, accent: Accent = Accent.ENERGY, compact: bool = False, rank: bool = False) -> None:
        super().__init__()
        self._accent = accent
        self._compact = compact
        self._rank = rank
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_command_chassis(
                painter,
                QRectF(1, 1, self.width() - 2, self.height() - 2),
                accent=self._accent,
                selected=self.underMouse(),
                compact=self._compact,
                rank=self._rank,
            )
        finally:
            painter.end()
        super().paintEvent(event)


class FactoryV2CommandButton(GameButton):
    def __init__(self, text: str, *, accent: Accent = Accent.BUILD) -> None:
        super().__init__(text, variant="primary", accent=accent)
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        if self.objectName() == "productionGuideButton":
            super().paintEvent(event)
            return
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_command_chassis(
                painter,
                QRectF(1, 1, self.width() - 2, self.height() - 2),
                accent=self.accent,
                selected=self.underMouse() or self.selected,
                compact=True,
            )
            if self.objectName() == "productionGuideButton":
                edge_alpha = 184 if self.underMouse() else 122
                painter.setPen(QPen(QColor(255, 210, 31, edge_alpha), 2))
                painter.drawLine(QPointF(18, self.height() - 8), QPointF(self.width() - 18, self.height() - 8))
            painter.setPen(QColor("#eff8f4") if self.isEnabled() else QColor("#6f837f"))
            font = GAME_UI_TOKENS.typography.industrial_title()
            font.setPointSize(9)
            font.setWeight(font.Weight.Black)
            font.setStretch(78)
            painter.setFont(font)
            painter.drawText(QRectF(10, 0, self.width() - 20, self.height()), Qt.AlignmentFlag.AlignCenter, self._text.upper())
        finally:
            painter.end()


class FactoryV2KpiStripWidget(KpiStripWidget):
    def __init__(self, state: GameState) -> None:
        super().__init__(state)
        self.setMinimumSize(250, 56)
        self.setMaximumHeight(60)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            metrics = (
                ("ENERGY", f"{self._state.energy.consumed:.1f}/{self._state.energy.generated:.1f} MW", Accent.ENERGY),
                ("REVENUE", "$0/min", Accent.CASH),
            )
            gap = 6
            width = (self.width() - gap * (len(metrics) - 1)) / len(metrics)
            for index, (label, value, accent) in enumerate(metrics):
                rect = QRectF(index * (width + gap), 0, width, self.height() - 1)
                draw_utility_chassis(painter, rect, accent=accent, active=index == 0)
                painter.setPen(QColor("#b1c4c0"))
                font = GAME_UI_TOKENS.typography.micro_label()
                painter.setFont(font)
                painter.drawText(rect.adjusted(11, 8, -11, -6), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)
                painter.setPen(QColor("#eff8f4"))
                font = GAME_UI_TOKENS.typography.card_title()
                painter.setFont(font)
                painter.drawText(rect.adjusted(11, 23, -11, -5), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)
        finally:
            painter.end()


def category_accent_for_resource_id(resource_id: str) -> Accent:
    normalized = resource_id.lower()
    if "coal" in normalized:
        return Accent.LOCKED
    if normalized.endswith("_ore") or "ore" in normalized:
        return Accent.EXTRACTOR
    if normalized in {"iron", "steel", "copper", "aluminum", "aluminum_components"}:
        return Accent.PROCESSOR
    if "power" in normalized or "energy" in normalized:
        return Accent.ENERGY
    return Accent.STORAGE


class FactoryV2HallResourceSummaryItemWidget(HallResourceSummaryItemWidget):
    def __init__(self, state: GameState, flow) -> None:
        super().__init__(state, flow)
        self.setProperty("factoryV2Utility", True)
        self.setFixedHeight(106)
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            net_state = self.property("netState")
            draw_utility_chassis(
                painter,
                QRectF(1, 1, self.width() - 2, self.height() - 2),
                accent=category_accent_for_resource_id(self._resource_id),
                active=net_state == "positive",
                warning=net_state == "negative",
            )
        finally:
            painter.end()


class FactoryV2HallResourceSummaryWidget(HallResourceSummaryWidget):
    item_widget_class = FactoryV2HallResourceSummaryItemWidget

    def __init__(self, state: GameState, definitions: dict[str, CardDefinition], hall: FactoryHall, *, vertical_list: bool = False) -> None:
        self._all_stored = False
        self._vertical_list = vertical_list
        super().__init__(state, definitions, hall)
        if vertical_list:
            self.setProperty("layoutMode", "vertical-list")

    def refresh(self) -> None:
        super().refresh()
        if self._vertical_list:
            self.setProperty("layoutMode", "vertical-list")

    def _resource_flows(self):
        flows = super()._resource_flows()
        if self._all_stored:
            from production_zero.core.analytics import ResourceFlow
            return {rid: flows.get(rid, ResourceFlow(rid, 0.0, 0.0))
                    for rid, stock in self._state.resources.items() if stock.amount > 0}
        return flows

    def _relayout_items(self) -> None:
        if not self._vertical_list:
            super()._relayout_items()
            return
        if not self._items:
            return
        self._columns = 1
        for row in range(self._layout.rowCount() + 1):
            self._layout.setRowStretch(row, 0)
        self._layout.setColumnStretch(0, 1)
        for index, resource_id in enumerate(sorted(self._items)):
            item = self._items[resource_id]
            item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._layout.addWidget(item, index, 0)
        self._layout.setRowStretch(len(self._items), 1)
        self.setProperty("layoutMode", "vertical-list")


class FactoryV2ResourceDrawer(QFrame):
    def __init__(self, state: GameState, definitions: dict[str, CardDefinition], hall: FactoryHall, *, summary_factory=None) -> None:
        super().__init__()
        self.setObjectName("factoryV2ResourceDrawer")
        self.setProperty("overlay", True)
        _use_transparent_surface(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        title = QLabel("RESOURCES")
        title.setObjectName("factoryV2DrawerTitle")
        title_font = GAME_UI_TOKENS.typography.industrial_title()
        title_font.setPointSize(17)
        title_font.setWeight(title_font.Weight.Black)
        title.setFont(title_font)
        title.setStyleSheet("color: #eff8f4; letter-spacing: 0px;")
        title.setFixedHeight(32)
        header.addWidget(title)
        header.addStretch(1)
        self.close_button = FactoryV2CommandButton("Close", accent=Accent.NEUTRAL)
        self.close_button.setObjectName("closeDrawerButton")
        self.close_button.setFixedSize(74, 32)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("factoryV2ResourceDrawerScroll")
        _use_transparent_surface(scroll)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setObjectName("factoryV2ResourceDrawerViewport")
        _use_transparent_surface(scroll.viewport())
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        self.summary = (summary_factory(scroll) if summary_factory is not None
                        else FactoryV2HallResourceSummaryWidget(state, definitions, hall, vertical_list=True))
        self.summary.setObjectName("factoryV2ResourceDrawerSummary")
        modes = QHBoxLayout()
        for text, all_stored in (("ACTIVE", False), ("ALL STORED", True)):
            button = FactoryV2CommandButton(text, accent=Accent.STORAGE)
            button.setSelected(not all_stored)
            button.clicked.connect(lambda checked=False, stored=all_stored: self._set_inventory_mode(stored))
            modes.addWidget(button)
        self._mode_buttons = modes
        layout.addLayout(modes)
        scroll.setWidget(self.summary)
        layout.addWidget(scroll, 1)

    def _set_inventory_mode(self, all_stored: bool) -> None:
        self.summary._all_stored = all_stored
        for index in range(self._mode_buttons.count()):
            self._mode_buttons.itemAt(index).widget().setSelected(bool(index) == all_stored)
        self.summary.refresh()

    def refresh(self) -> None:
        self.summary.refresh()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_utility_chassis(
                painter,
                QRectF(1, 1, self.width() - 2, self.height() - 2),
                accent=Accent.STORAGE,
                active=True,
                opacity_boost=28,
            )
        finally:
            painter.end()
        super().paintEvent(event)


class FactoryV2LinePlate(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setObjectName("factoryV2LineTitle")
        self.setMinimumSize(120, 28)
        font = GAME_UI_TOKENS.typography.industrial_title()
        font.setPointSize(15)
        self.setFixedWidth(max(154, QFontMetrics(font).horizontalAdvance(text) + 54))
        self.setToolTip(text)
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_warning_plate(painter, QRectF(0, 0, self.width(), self.height()), text=self.text())
        finally:
            painter.end()


class FactoryV2ActiveIndicator(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("factoryV2ActiveIndicator")
        self.setFixedSize(84, 20)
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_status_led(painter, QRectF(0, 0, self.width(), self.height()), active=not bool(self.property("scopePaused")))
        finally:
            painter.end()


class FittedMetricLabel(QLabel):
    """Keep live header amounts inside their existing command-deck module."""

    def _fit(self):
        key = (self.text(), self.width(), self.height())
        if getattr(self, '_fit_key', None) == key:
            return
        self._fit_key = key
        font = self.font()
        font.setPixelSize(22)
        while font.pixelSize() > 10:
            metrics = QFontMetrics(font)
            if metrics.horizontalAdvance(self.text()) <= self.width() and metrics.tightBoundingRect(self.text()).height() <= self.height():
                break
            font.setPixelSize(font.pixelSize() - 1)
        self.setStyleSheet(f"font-size: {font.pixelSize()}px;")

    def setText(self, text):
        if self.text() == text:
            return
        super().setText(text)
        self._fit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()


class StableStorageMetricLabel(FittedMetricLabel):
    """Reserve a stable number row; fit its font to width, never to live stock."""
    def __init__(self):
        super().__init__()
        self.setFixedHeight(28)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def reserve_number_width(self):
        # Establish the minimum before the parent lays out its Expand button.
        self.ensurePolished()
        font = QFont(self.font())
        font.setPixelSize(14)
        digit = max("0123456789", key=lambda d: QFontMetrics(font).horizontalAdvance(d))
        number = digit * 3 + "," + digit * 3
        self.setMinimumWidth(QFontMetrics(font).horizontalAdvance(number + "/" + number) + 2)

    def _fit(self):
        width = self.contentsRect().width()
        if getattr(self, "_storage_fit_width", None) == width or width <= 0:
            return
        self._storage_fit_width = width
        font = self.font()
        font.setPixelSize(22)
        # Below one million both numbers have at most six digits and a comma;
        # larger values already use the existing compact M/B/T notation.
        digit = max("0123456789", key=lambda d: QFontMetrics(font).horizontalAdvance(d))
        number = digit * 3 + "," + digit * 3
        sample = number + "/" + number
        while font.pixelSize() > 14 and QFontMetrics(font).horizontalAdvance(sample) > width:
            font.setPixelSize(font.pixelSize() - 1)
        self.setStyleSheet(f"font-size: {font.pixelSize()}px;")


class FactoryCommandDeckWidget(QFrame):
    profile_requested = Signal()
    resources_requested = Signal()

    def __init__(
        self,
        state: GameState,
        definition_count: int,
        resource_definitions: dict[str, ResourceDefinition],
        command_bus: CommandBus | None = None,
        on_state_changed=None,
    ) -> None:
        super().__init__()
        self._state = state
        self._definition_count = definition_count
        self._resource_definitions = resource_definitions
        self._command_bus = command_bus
        self._on_state_changed = on_state_changed
        self.setObjectName("factoryV2CommandDeck")
        self.setFixedHeight(134)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        # Keep the header within 1366 px with the supported Windows fonts.
        layout.setSpacing(8)

        title = QVBoxLayout()
        title.setSpacing(6)
        deck = QLabel("COMMAND DECK")
        deck.setObjectName("factoryV2DeckLabel")
        name = QLabel("INDUSTRIOVA")
        name.setObjectName("factoryV2DeckTitle")
        title.addWidget(deck)
        title.addWidget(name)
        title.addStretch(1)
        layout.addLayout(title, 2)

        systems = FactoryV2CommandModule(accent=Accent.STORAGE)
        systems.setObjectName("factoryV2PrimarySystems")
        systems.setMinimumHeight(90)
        systems_layout = QHBoxLayout(systems)
        systems_layout.setContentsMargins(14, 10, 14, 10)
        systems_layout.setSpacing(12)
        self._cash_value = self._system_metric(systems_layout, GameIcon.CASH, "CASH", Accent.CASH, "factoryV2CashValue")
        self._energy_value = self._system_metric(systems_layout, GameIcon.ENERGY, "ENERGY", Accent.ENERGY, "factoryV2EnergyValue")
        storage_module = FactoryV2CommandModule(accent=Accent.STORAGE, compact=True)
        storage_module.setObjectName("factoryV2StorageModule")
        storage_box = QVBoxLayout(storage_module)
        storage_box.setContentsMargins(10, 8, 10, 8)
        storage_box.setSpacing(6)
        storage_head = QHBoxLayout()
        storage_head.setContentsMargins(0, 4, 0, 0)
        storage_head.setSpacing(8)
        storage_icon = GameIconWidget(GameIcon.STORAGE, accent=Accent.STORAGE)
        storage_icon.setObjectName("factoryV2StorageIcon")
        storage_icon.setFixedSize(36, 36)
        storage_head.addWidget(storage_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        storage_text = QVBoxLayout()
        storage_text.setSpacing(1)
        storage_label = QLabel("STORAGE")
        storage_label.setObjectName("factoryV2StorageLabel")
        self._storage_value = StableStorageMetricLabel()
        self._storage_value.setObjectName("factoryV2StorageValue")
        self._storage_value.reserve_number_width()
        storage_text.addWidget(storage_label)
        storage_text.addWidget(self._storage_value)
        storage_head.addLayout(storage_text, 1)
        storage_box.addLayout(storage_head)
        self._storage_button = GameButton("Expand", variant="primary", accent=Accent.BUILD)
        self._storage_button.setObjectName("expandResourceStorageButton")
        self._storage_button.setProperty("factoryV2StorageCta", True)
        self._storage_button.setMinimumSize(98, 28)
        self._storage_button.clicked.connect(self._expand_resource_storage)
        storage_head.addWidget(self._storage_button, 0, Qt.AlignmentFlag.AlignTop)
        systems_layout.addWidget(storage_module, 1)
        layout.addWidget(systems, 4)

        operations = FactoryV2CommandModule(accent=Accent.PROCESSOR)
        operations.setObjectName("factoryV2ResourceStrip")
        operations.setMinimumHeight(96)
        operations_layout = QVBoxLayout(operations)
        operations_layout.setContentsMargins(14, 12, 14, 12)
        operations_layout.setSpacing(5)
        self._operations_label = QLabel("PRODUCTION NETWORK")
        self._operations_label.setObjectName("factoryV2OperationsLabel")
        self._operations_activity = QLabel()
        self._operations_activity.setObjectName("factoryV2OperationsActivity")
        self._operations_progress = QProgressBar()
        self._operations_progress.setObjectName("factoryV2OperationsProgress")
        self._operations_progress.setTextVisible(False)
        self._operations_progress.setFixedHeight(6)
        self._operations_hint = QLabel()
        self._operations_hint.setObjectName("factoryV2OperationsHint")
        self._operations_hint.setWordWrap(True)
        operations_layout.addWidget(self._operations_label)
        operations_layout.addWidget(self._operations_activity)
        operations_layout.addWidget(self._operations_progress)
        operations_layout.addWidget(self._operations_hint)
        self._resources_global_button = GameButton("Resources", variant="primary", accent=Accent.STORAGE)
        self._resources_global_button.setObjectName("globalResourcesButton")
        self._resources_global_button.clicked.connect(self.resources_requested.emit)
        self._operations_label.hide()
        self._operations_activity.hide()
        self._operations_progress.hide()
        self._operations_hint.hide()
        storage_box.addWidget(self._resources_global_button)
        self._communication_layout = operations_layout
        layout.addWidget(operations, 2)

        progress = FactoryV2CommandModule(accent=Accent.CASH, rank=True)
        progress.setObjectName("factoryV2ProgressionZone")
        progress.setMinimumHeight(96)
        progress_layout = QHBoxLayout(progress)
        progress_layout.setContentsMargins(11, 10, 11, 10)
        progress_layout.setSpacing(10)
        rank_emblem = FactoryV2CommandModule(accent=Accent.CASH, compact=True, rank=True)
        rank_emblem.setObjectName("factoryV2RankEmblem")
        rank_emblem.setFixedSize(82, 64)
        rank_icon = GameIconWidget(GameIcon.HALL, accent=Accent.CASH, parent=rank_emblem)
        rank_icon.setObjectName("factoryV2RankIcon")
        rank_icon.setGeometry(9, 10, 64, 44)
        progress_layout.addWidget(rank_emblem, 0, Qt.AlignmentFlag.AlignVCenter)
        rank_text = QVBoxLayout()
        rank_text.setContentsMargins(4, 5, 0, 0)
        rank_text.setSpacing(2)
        self._level = QPushButton()
        self._level.setObjectName("factoryV2Level")
        self._level.setCursor(Qt.CursorShape.PointingHandCursor)
        self._level.setToolTip("Open company profile")
        self._level.setAccessibleName("Open company profile")
        self._level.setStyleSheet("QPushButton { background: transparent; border: none; text-align: left; color: #ffd21f; font-size: 18px; font-weight: 900; padding: 0; } QPushButton:hover, QPushButton:focus { color: #fff3bd; text-decoration: underline; }")
        self._level.clicked.connect(self.profile_requested)
        self._rank_title = QLabel()
        self._rank_title.setObjectName("factoryV2RankTitle")
        self._xp = QLabel()
        self._xp.setObjectName("factoryV2Xp")
        self._xp_bar = QProgressBar()
        self._xp_bar.setObjectName("companyXpProgress")
        self._xp_bar.setTextVisible(False)
        rank_text.addWidget(self._level)
        rank_text.addWidget(self._rank_title)
        rank_text.addStretch(1)
        rank_text.addWidget(self._xp)
        rank_text.addWidget(self._xp_bar)
        progress_layout.addLayout(rank_text, 1)
        layout.addWidget(progress, 2)
        self.refresh()

    def _system_metric(self, layout: QHBoxLayout, icon: GameIcon, label: str, accent: Accent, value_object_name: str) -> QLabel:
        box = FactoryV2CommandModule(accent=accent, compact=True)
        box.setObjectName("factoryV2Metric")
        box.setMinimumWidth(180)
        box_layout = QHBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(10)
        icon_widget = GameIconWidget(icon, accent=accent)
        icon_widget.setFixedSize(38, 38)
        text = QVBoxLayout()
        text.setSpacing(0)
        label_widget = QLabel(label)
        label_widget.setObjectName(f"factoryV2{label.title()}Label")
        value = FittedMetricLabel()
        value.setObjectName(value_object_name)
        text.addStretch(1)
        text.addWidget(label_widget)
        text.addWidget(value)
        text.addStretch(1)
        box_layout.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)
        box_layout.addLayout(text, 1)
        layout.addWidget(box, 1)
        return value

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=18)
            draw_industrial_base_surface(painter, rect.adjusted(4, 4, -4, -4), strength=1, radius=14, role="command")
            draw_hazard_stripes(
                painter,
                QRectF(rect.left() + 18, rect.bottom() - 42, rect.width() * 0.16, 22),
                primary=QColor(200, 42, 32, 246),
                secondary=QColor(246, 240, 226, 218),
                stripe_width=18,
                reverse=True,
                radius=2,
            )
            painter.save()
            painter.setClipRect(rect.adjusted(18, 14, -18, -14))
            painter.setPen(QPen(QColor(142, 154, 150, 24), 1))
            painter.drawLine(rect.left() + rect.width() * 0.18, rect.top() + 14, rect.left() + rect.width() * 0.18, rect.bottom() - 14)
            painter.drawLine(rect.right() - rect.width() * 0.16, rect.top() + 14, rect.right() - rect.width() * 0.16, rect.bottom() - 14)
            painter.setPen(QPen(QColor(255, 255, 255, 13), 1))
            y = rect.top() + rect.height() * 0.72
            painter.drawLine(rect.left() + 18, y, rect.right() - 18, y)
            painter.restore()
        finally:
            painter.end()
        super().paintEvent(event)

    def refresh(self) -> None:
        self._cash_value.setText(f"${_compact_value(self._state.cash.amount)}")
        self._cash_value.setToolTip(f"${self._state.cash.amount:,.2f}")
        self._energy_value.setText(f"{self._state.energy.consumed:.0f}/{self._state.energy.generated:.0f} MW")
        self._storage_value.setText(f"{_compact_value(self._state.used_storage)}/{_compact_value(self._state.storage_capacity)}")
        self._storage_value.setToolTip(f"{self._state.used_storage:,.0f} / {self._state.storage_capacity:,.0f}")
        unit_count = len(self._state.all_production_units())
        module_count = len(self._state.installed_card_ids())
        unlocked_capacity = sum(unit.slot_count for unit in self._state.all_production_units())
        self._operations_activity.setText(f"{module_count} / {unlocked_capacity} ACTIVE SLOTS")
        self._operations_progress.setRange(0, max(1, unlocked_capacity))
        self._operations_progress.setValue(module_count)
        self._operations_hint.setText(
            f"{count_label(unit_count, 'UNIT').upper()} · {count_label(module_count, 'MODULE').upper()} ONLINE"
        )
        if self._state.inventory_storage_level >= MAX_INVENTORY_STORAGE_LEVEL:
            self._storage_button.setEnabled(False)
            self._storage_button._text = "Max"
        else:
            cost = inventory_storage_upgrade_cost(self._state.inventory_storage_level)
            self._storage_button._text = "EXPAND"
            self._storage_button.setToolTip(f"Expand Global Storage · ${cost:,.2f}")
            self._storage_button.setEnabled(self._state.cash.amount >= cost)
        self._storage_button.update()
        company = self._state.company
        required = company.xp_to_next_level
        self._level.setText(f"LEVEL {company.level}")
        self._rank_title.setText(company.current_title.upper())
        self._xp.setText(f"{company.current_xp:,.0f} / {required:,.0f} XP")
        self._xp_bar.setRange(0, 10000)
        self._xp_bar.setValue(round(min(1., company.current_xp / max(1., required)) * 10000))

    def highlight_cash_gain(self, previous_cash: float, current_cash: float) -> None:
        self._cash_value.setText(f"${_compact_value(current_cash)}")

    def _expand_resource_storage(self) -> None:
        if self._command_bus is None or not self._resource_definitions:
            return
        from production_zero.ui.release_dialogs import confirm, inform
        from production_zero.core.storage_upgrades import next_storage_capacity
        level = self._state.inventory_storage_level
        session = self._state.cards
        try:
            cost = inventory_storage_upgrade_cost(level)
            current = self._state.storage_capacity
            additional = next_storage_capacity(self._state, self._resource_definitions) - current
        except ValueError as error:
            inform(self, 'Storage expansion', str(error))
            return
        text = (f"Additional storage capacity: {additional:,.0f} units\n"
                f"Current capacity: {current:,.0f} → {current + additional:,.0f} units\nCost: ${cost:,.2f}")
        if not confirm(self, 'Storage expansion', text, 'YES – EXPAND'):
            return
        if session is not self._state.cards:
            return
        try:
            self._command_bus.dispatch(ExpandInventoryStorage(self._resource_definitions, level, cost))
        except ValueError as error:
            inform(self, 'Storage expansion', str(error))
            return
        self.refresh()
        if self._on_state_changed is not None:
            self._on_state_changed()


def machine_icon_for_definition(definition: CardDefinition | None) -> MachineIcon:
    if isinstance(definition, EnergyDefinition):
        if definition.energy_type == EnergyType.SOLAR:
            return MachineIcon.SOLAR_ARRAY
        if definition.energy_type == EnergyType.WIND:
            return MachineIcon.WIND_TURBINE
        if definition.energy_type == EnergyType.COAL:
            return MachineIcon.COAL_POWER
        if definition.energy_type == EnergyType.GAS:
            return MachineIcon.GAS_POWER
        if definition.energy_type == EnergyType.NUCLEAR:
            return MachineIcon.NUCLEAR_POWER
    if isinstance(definition, MachineDefinition):
        if definition.machine_type in PRIMARY_MACHINE_TYPES:
            return MachineIcon.EXTRACTOR
        if definition.machine_type == MachineType.PROCESSOR:
            return MachineIcon.PROCESSOR
        if definition.machine_type == MachineType.FABRICATOR:
            return MachineIcon.FABRICATOR
        if definition.machine_type == MachineType.ASSEMBLER:
            return MachineIcon.ASSEMBLER
    name = (definition.name if definition is not None else "").lower()
    if "solar" in name:
        return MachineIcon.SOLAR_ARRAY
    if "wind" in name:
        return MachineIcon.WIND_TURBINE
    if "coal" in name:
        return MachineIcon.COAL_POWER
    if "gas" in name:
        return MachineIcon.GAS_POWER
    if "nuclear" in name:
        return MachineIcon.NUCLEAR_POWER
    return MachineIcon.PROCESSOR


def accent_for_definition(definition: CardDefinition | None) -> Accent:
    if isinstance(definition, EnergyDefinition):
        if definition.energy_type == EnergyType.NUCLEAR:
            return Accent.LEGENDARY
        if definition.energy_type in (EnergyType.COAL, EnergyType.GAS):
            return Accent.WARNING
        return Accent.ENERGY
    if isinstance(definition, MachineDefinition):
        if definition.machine_type in PRIMARY_MACHINE_TYPES:
            return Accent.EXTRACTOR
        if definition.machine_type == MachineType.PROCESSOR:
            return Accent.PROCESSOR
        if definition.machine_type == MachineType.FABRICATOR:
            return Accent.WARNING
        if definition.machine_type == MachineType.ASSEMBLER:
            return Accent.RARE
    return Accent.STORAGE


def prototype_family_for_definition(definition: CardDefinition | None) -> str:
    if isinstance(definition, EnergyDefinition):
        return definition.energy_type.value
    if isinstance(definition, MachineDefinition):
        return machine_art_family_for_machine_type(definition.machine_type)
    if isinstance(definition, FreightDefinition):
        return definition.family.value
    name = (definition.name if definition is not None else "").lower()
    if any(token in name for token in ("solar", "wind", "coal", "gas", "nuclear", "power")):
        return "energy"
    if any(token in name for token in ("truck", "freight", "train", "ship", "logistics")):
        return "transport"
    return "processor"


def rarity_accent_for_card(card: CardInstance | None) -> Accent:
    if card is None:
        return Accent.NEUTRAL
    rarity = card.rarity.value
    if rarity == "uncommon":
        return Accent.UNCOMMON
    if rarity == "rare":
        return Accent.RARE
    if rarity == "epic":
        return Accent.EPIC
    if rarity == "legendary":
        return Accent.LEGENDARY
    return Accent.COMMON


class FactoryV2HallStage(QFrame):
    def __init__(self, hall: FactoryHall, state: GameState) -> None:
        super().__init__()
        self._hall = hall
        self._state = state
        self.setObjectName("factoryV2HallStage")
        _use_transparent_surface(self)
        self.setMinimumHeight(82)
        self.setToolTip(hall.name)

    def rename_title_layout(self):
        from production_zero.ui.interaction_polish import building_title_layout
        font = GAME_UI_TOKENS.typography.brand_display()
        font.setPointSize(26)
        rect = QRectF(31, 24, max(0, self.width() - 62), max(32, self.height() - 47))
        visible, pencil = building_title_layout(self._hall.name, font, rect)
        self.setToolTip(self._hall.name)
        return font, visible, pencil

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            header_panel = rect.adjusted(14, 10, -14, -10)
            bridge = QLinearGradient(rect.topLeft(), rect.topRight())
            bridge.setColorAt(0.0, QColor(255, 210, 31, 13))
            bridge.setColorAt(0.42, QColor(255, 255, 255, 3))
            bridge.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bridge)
            painter.drawRoundedRect(header_panel.adjusted(0, 5, -0, -header_panel.height() * 0.62), 4, 4)
            font, visible, _pencil = self.rename_title_layout()
            painter.setFont(font)
            painter.setPen(QColor("#eff8f4"))
            title_rect = QRectF(31, 24, max(0, self.width() - 62), max(32, self.height() - 47))
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, visible)
        finally:
            painter.end()


class FactoryV2MachineCard(QWidget):
    hovered = Signal(str)
    unhovered = Signal()

    def enterEvent(self, event) -> None:
        if self._card:
            self.hovered.emit(self._card.card_id)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.unhovered.emit()
        super().leaveEvent(event)

    clicked = Signal(int)
    production_change_requested = Signal(str)
    chain_requested = Signal(str)

    def __init__(
        self,
        slot: HallSlot,
        card: CardInstance | None,
        definition: CardDefinition | None,
        production_state: MachineProductionState | None,
        state: GameState | None = None,
    ) -> None:
        super().__init__()
        self._slot = slot
        self._card = card
        self._definition = definition
        self._production_state = production_state
        self._state = state
        self.setObjectName("factoryV2MachineCard")
        self.setFixedSize(FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self._upgrade_button = GameButton(">>", variant="secondary", accent=Accent.BUILD)
        self._upgrade_button.setParent(self)
        self._upgrade_button.setObjectName("machineMkUpgrade")
        self._upgrade_button._variant = "primary"
        self._upgrade_button._accent = Accent.SUCCESS
        self._upgrade_button.setText("⇈")
        self._upgrade_button.setFixedSize(36, 34)
        self._upgrade_button.move(self.width() - 42, 114)
        self._upgrade_button.setToolTip("Upgrade this machine to the next MK level")
        self._upgrade_button.clicked.connect(lambda: self._release_board._release_action(lambda: self._release_board._upgrade_selection(self._card.card_id)) if hasattr(self, "_release_board") else None)
        self._upgrade_button.setEnabled(card is not None and card.mk_level < 99)

    def set_data(
        self,
        slot: HallSlot,
        card: CardInstance | None,
        definition: CardDefinition | None,
        production_state: MachineProductionState | None,
        state: GameState | None = None,
    ) -> None:
        signature = (card, definition, production_state.selected_production_id if production_state else None,
                     production_state.status if production_state else None)
        self._slot = slot
        self._card = card
        self._definition = definition
        self._production_state = production_state
        if state is not None:
            self._state = state
        signature += (self._production_change_available(), self._status_text())
        if getattr(self, "_presentation_signature", None) != signature:
            self._presentation_signature = signature
            self._upgrade_button.setEnabled(card is not None and card.mk_level < 99)
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        board = getattr(self, "_release_board", None)
        if board is not None:
            if event.button() == Qt.MouseButton.RightButton:
                self._context_card_id = self._card.card_id
                return
            if event.button() == Qt.MouseButton.LeftButton:
                modifiers = event.modifiers() if hasattr(event, "modifiers") else Qt.KeyboardModifier.NoModifier
                if self._production_change_available() and self._resource_control_rect().contains(event.position()):
                    if not (self._card.card_id in board._selected_machines and not modifiers):
                        board._select_slot(self._slot.index, modifiers)
                    self.production_change_requested.emit(self._card.card_id)
                    return
                self._press_position = event.position().toPoint()
                self._drag_grip = self._press_position
                if not (self._card.card_id in board._selected_machines and not modifiers):
                    board._select_slot(self._slot.index, modifiers)
                return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._card is not None and self._production_change_available() and self._resource_control_rect().contains(event.position()):
                self.production_change_requested.emit(self._card.card_id)
            else:
                self.clicked.emit(self._slot.index)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        board = getattr(self, "_release_board", None)
        start = getattr(self, "_press_position", None)
        if board is not None and start is not None and event.buttons() & Qt.MouseButton.LeftButton:
            from PySide6.QtWidgets import QApplication
            if (event.position().toPoint() - start).manhattanLength() >= QApplication.startDragDistance():
                self._press_position = None
                board._begin_machine_drag(self)
                return
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._production_change_available():
            self.production_change_requested.emit(self._card.card_id)
            return
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        board = getattr(self, "_release_board", None)
        if board is not None and event.button() == Qt.MouseButton.RightButton:
            cid = getattr(self, "_context_card_id", None)
            if cid is not None:
                QTimer.singleShot(0, board, lambda: board._release_action(lambda: board._card_actions(cid)))
            return
        if board is not None and getattr(self, "_press_position", None) is not None and event.button() == Qt.MouseButton.LeftButton:
            if not event.modifiers():
                board._select_slot(self._slot.index, event.modifiers())
            self._press_position = None
            return
        super().mouseReleaseEvent(event)

    def _production_change_available(self) -> bool:
        if not isinstance(self._definition, MachineDefinition):
            return False
        if self._state is None:
            option_count = len(self._definition.available_production_options)
        else:
            option_count = len(production_options_for_machine(self._state, self._definition))
        if self._definition.machine_type in PRIMARY_MACHINE_TYPES:
            return option_count > 0
        return option_count > (1 if self._active_production() is not None else 0)

    def _active_production(self):
        if not isinstance(self._definition, MachineDefinition):
            return None
        if self._production_state is None or self._production_state.selected_production_id is None:
            return None
        return self._definition.production_option(self._production_state.selected_production_id)

    def _primary_label(self) -> str:
        production = self._active_production()
        if production is not None:
            return production.name.upper()
        if isinstance(self._definition, MachineDefinition):
            return "NO RESOURCE SELECTED" if self._definition.machine_type in PRIMARY_MACHINE_TYPES else "NO RECIPE SELECTED"
        if isinstance(self._definition, EnergyDefinition):
            return f"+{self._definition.base_power_output * (self._card.output_multiplier if self._card else 1) * research_multiplier(self._state.research if self._state else None, 'energy_output'):.0f} MW"
        return "MODULE"

    def _primary_value_text(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return "SELECT"
            output = production.output_amount_for(self._definition) * (self._card.output_multiplier if self._card else 1)
            return f"+{output:g}/cycle"
        if isinstance(self._definition, EnergyDefinition):
            return f"+{self._definition.base_power_output * (self._card.output_multiplier if self._card else 1) * research_multiplier(self._state.research if self._state else None, 'energy_output'):.0f} MW"
        return self._primary_label()

    def _primary_caption_text(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            return self._primary_label()
        if isinstance(self._definition, EnergyDefinition):
            return "Fuel required" if self._definition.requires_fuel else "No fuel"
        return self._detail_text()

    def _detail_text(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return "Select production"
            output = production.output_amount_for(self._definition) * (self._card.output_multiplier if self._card else 1)
            power = production.power_draw_for(self._definition) * (self._card.power_multiplier if self._card else 1)
            return f"+{output:g}/cycle · {power:.0f} MW"
        if isinstance(self._definition, EnergyDefinition):
            return "Fuel required" if self._definition.requires_fuel else "No fuel"
        return ""

    def _status_text(self) -> str:
        from production_zero.core.production_pause import production_slot_paused
        paused = bool(self._card and self._card.paused)
        if self._card is not None and self._state is not None and not paused:
            location = getattr(self, "_pause_location", None)
            if location is not None:
                unit, slot = location
                valid = (slot.card_id == self._card.card_id and
                         slot.index < len(unit.slots) and unit.slots[slot.index] is slot and
                         any(units.get(unit.hall_id) is unit for units in
                             (self._state.halls, self._state.resource_sites, self._state.energy_plants)))
            else:
                valid = False
            if not valid:
                location = next(((unit, slot) for unit in self._state.all_production_units()
                                 for slot in unit.slots if slot.card_id == self._card.card_id), None)
                self._pause_location = location
            if location is not None:
                paused = production_slot_paused(location[0], location[1].index)
            else:
                from production_zero.core.production_pause import effective_card_paused
                paused = effective_card_paused(self._state, self._card.card_id)
        if paused:
            return "PAUSED"
        if isinstance(self._definition, EnergyDefinition):
            return "ONLINE"
        if self._production_state is None:
            return "IDLE"
        if self._production_state.is_unconfigured:
            return "NO RESOURCE" if isinstance(self._definition, MachineDefinition) and self._definition.machine_type in PRIMARY_MACHINE_TYPES else "NO RECIPE"
        if self._production_state.is_storage_full:
            return "STORAGE FULL"
        if self._production_state.is_no_power:
            return "NO POWER"
        if self._production_state.is_missing_input:
            return "MISSING INPUT"
        if self._production_state.status == "running":
            return "RUNNING"
        return "IDLE"

    def _status_accent(self) -> Accent:
        text = self._status_text()
        if text in {"RUNNING", "ONLINE"}:
            return Accent.SUCCESS
        if text in {"NO POWER", "STORAGE FULL"}:
            return Accent.DANGER
        if text in {"MISSING INPUT", "NO RESOURCE", "NO RECIPE"}:
            return Accent.WARNING
        return Accent.NEUTRAL

    def _resource_control_rect(self) -> QRectF:
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        sign = QRectF(rect.left() + 14, rect.top() + 54, rect.width() - 28, rect.height() * 0.43)
        secondary_info = QRectF(rect.left() + 14, sign.bottom() + 24, rect.width() - 28, 11)
        return secondary_info.adjusted(-7, -4, 7, 5)

    def _title_text(self) -> str:
        return _display_card_title(self._definition, self._card)

    def _meta_text(self) -> str:
        return f"MK{self._card.mk_level} · {self._card.rarity.value.upper()}" if self._card is not None else ""

    def _cycle_progress_ratio(self) -> float:
        if not isinstance(self._definition, MachineDefinition) or self._production_state is None:
            return 0.0
        if self._production_state.status != "running":
            return 0.0
        production = self._active_production()
        if production is None:
            return 0.0
        return min(1.0, max(0.0, self._production_state.progress_seconds / max(0.001, production.cycle_seconds_for(self._definition))))

    def _shows_cycle_progress(self) -> bool:
        return (
            isinstance(self._definition, MachineDefinition)
            and self._production_state is not None
            and self._production_state.status == "running"
            and self._active_production() is not None
        )

    def _draw_fit_text(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        *,
        point_size: int,
        min_point_size: int,
        weight,
        color: QColor,
        flags=Qt.AlignmentFlag.AlignCenter,
    ) -> None:
        font = GAME_UI_TOKENS.typography.card_title()
        font.setPointSize(point_size)
        font.setWeight(weight)
        painter.setFont(font)
        while font.pointSize() > min_point_size and painter.fontMetrics().horizontalAdvance(text) > rect.width():
            font.setPointSize(font.pointSize() - 1)
            painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, flags, text)

    def _draw_machine_stage(self, painter: QPainter, rect: QRectF, accent: Accent) -> None:
        draw_machine_icon_stage(painter, rect, icon=machine_icon_for_definition(self._definition), accent=accent)

    def _draw_card_zone(self, painter: QPainter, rect: QRectF, *, accent: Accent, strength: int = 1) -> None:
        alpha_top = 22 + strength * 8
        alpha_bottom = 8 + strength * 6
        zone_gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        zone_gradient.setColorAt(0.0, QColor(255, 255, 255, alpha_top))
        zone_gradient.setColorAt(0.42, QColor(142, 154, 150, 4 + strength * 3))
        zone_gradient.setColorAt(1.0, QColor(0, 0, 0, alpha_bottom))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(zone_gradient)
        painter.drawRoundedRect(rect, 10, 10)

    def _draw_status_band(self, painter: QPainter, rect: QRectF) -> None:
        draw_status_badge(painter, rect, text=self._status_text(), accent=self._status_accent())

    def _draw_cycle_progress(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 76))
        painter.drawRoundedRect(rect, 2, 2)
        if not isinstance(self._definition, MachineDefinition) or self._production_state is None:
            return
        if self._production_state.is_no_power:
            fill_color = QColor("#f06f73")
            ratio = 1.0
        elif self._production_state.is_storage_full:
            fill_color = QColor("#f06f73")
            ratio = 1.0
        elif self._production_state.is_missing_input:
            fill_color = QColor("#f2c25b")
            ratio = 1.0
        elif self._shows_cycle_progress():
            fill_color = QColor("#65d88f")
            ratio = self._cycle_progress_ratio()
        else:
            return
        fill_rect = QRectF(rect.left(), rect.top(), rect.width() * ratio, rect.height())
        painter.setBrush(fill_color)
        painter.drawRoundedRect(fill_rect, 2, 2)
        painter.setPen(QPen(QColor(255, 255, 255, 34), 1))
        painter.drawLine(fill_rect.left() + 2, fill_rect.top() + 1, fill_rect.right() - 2, fill_rect.top() + 1)

    def _prototype_detail_text(self) -> str:
        value = self._primary_value_text()
        if value == "SELECT":
            return ""
        return value.replace("/cycle", "/CYCLE")

    def _prototype_secondary_text(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            chevron = " >" if self._production_change_available() else ""
            if production is not None:
                return f"{production.name.upper()}{chevron}"
            if self._definition.machine_type in PRIMARY_MACHINE_TYPES:
                return f"SELECT RESOURCE{chevron}" if self._production_change_available() else "NO RESOURCE"
            return f"SELECT RECIPE{chevron}" if self._production_change_available() else "NO RECIPE"
        if isinstance(self._definition, EnergyDefinition) and self._definition.requires_fuel and self._definition.fuel_resource_id:
            return self._definition.fuel_resource_id.replace("_", " ").upper()
        return ""

    def _prototype_disabled(self) -> bool:
        return self._status_text() == "NO POWER"

    def paintEvent(self, event) -> None:
        key = (self._card, self._production_state.selected_production_id if self._production_state else None,
               self._status_text(), self._prototype_secondary_text(), self.underMouse(), bool(self.property("selected")), bool(self.property("installFlash")),
               self._resource_control_rect().contains(self.mapFromGlobal(QCursor.pos())), self.size().width(), self.size().height(), self.devicePixelRatioF())
        if getattr(self, "_cached_paint_key", None) != key:
            self._cached_card_pixmap = self._render_card_pixmap()
            self._cached_paint_key = key
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cached_card_pixmap)
        painter.end()

    def _render_card_pixmap(self):
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(round(self.width() * ratio), round(self.height() * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_machine_card_prototype(
                painter,
                rect,
                title=self._title_text(),
                family=prototype_family_for_definition(self._definition),
                meta=self._meta_text(),
                detail=self._prototype_detail_text(),
                secondary=self._prototype_secondary_text(),
                secondary_control=self._production_change_available(),
                secondary_hover=self._production_change_available() and self._resource_control_rect().contains(self.mapFromGlobal(QCursor.pos())),
                disabled=self._prototype_disabled(),
                active=self._status_text() in {"RUNNING", "ONLINE"},
                hover=self.underMouse(),
            )
            if self.property("installFlash") or self.property("selected"):
                painter.setPen(QPen(QColor(216, 240, 106, 170), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 14, 14)
            footer = QRectF(rect.left() + 10, rect.bottom() - 27, rect.width() - 20, 18)
            progress = QRectF(rect.left() + 18, footer.top() - 7, rect.width() - 36, 4)
            # Machine cycle animation retired; Freight progress is independent.
            self._draw_status_band(painter, footer)

        finally:
            painter.end()
        return pixmap


class FactoryV2BuildSlot(BuildSlotWidget):
    def __init__(self, title: str = "Build Slot", subtitle: str = "Install machine") -> None:
        super().__init__(title, subtitle)
        self.setObjectName("factoryV2BuildSlot")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_build_slot(painter, rect, hover=self.underMouse(), pressed=False)

            font = GAME_UI_TOKENS.typography.industrial_title()
            font.setPointSize(13)
            painter.setFont(font)
            painter.setPen(QColor(GAME_UI_TOKENS.colors.safety_yellow))
            painter.drawText(QRectF(rect.left() + 10, rect.top() + rect.height() * 0.61, rect.width() - 20, 24), Qt.AlignmentFlag.AlignCenter, self._title.upper())
            if self.property("selected"):
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#ffd21f"), 2))
                painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 10, 10)
        finally:
            painter.end()


class FactoryV2LockedSlot(ClickableCapacityPanel):
    def __init__(self, line_id: str, slot_number: int, cost: float, enabled: bool) -> None:
        super().__init__(enabled=enabled)
        self._slot_number = slot_number
        self._cost = cost
        self.setObjectName("lockedSlotPanel")
        self.setProperty("lineId", line_id)
        self.setProperty("slotNumber", slot_number)
        self.setProperty("unlockCost", cost)
        self.setFixedSize(FACTORY_V2_LOCKED_SLOT_WIDTH, FACTORY_V2_LOCKED_SLOT_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            module = draw_locked_slot(painter, rect, enabled=bool(self.property("unlockEnabled")))
            font = GAME_UI_TOKENS.typography.industrial_title()
            font.setPointSize(15)
            painter.setFont(font)
            painter.setPen(QColor("#eff8f4"))
            painter.drawText(QRectF(module.left() + 8, module.top() + 101, module.width() - 16, 25), Qt.AlignmentFlag.AlignCenter, f"S{self._slot_number:02d}")
            font = GAME_UI_TOKENS.typography.micro_label()
            font.setPointSize(11)
            font.setWeight(font.Weight.Black)
            painter.setFont(font)
            painter.setPen(QColor(GAME_UI_TOKENS.colors.warning_orange))
            painter.drawText(QRectF(module.left() + 8, module.top() + 131, module.width() - 16, 22), Qt.AlignmentFlag.AlignCenter, f"${self._cost:.2f}")
        finally:
            painter.end()


class FactoryV2LockedLine(ClickableCapacityPanel):
    def __init__(self, line: ProductionLine, line_number: int, enabled: bool, track_label: str = "LINE", *, cost: float | None = None) -> None:
        super().__init__(enabled=enabled)
        self._line = line
        self._line_number = line_number
        self._track_label = track_label
        self._unlock_cost=line.unlock_cost if cost is None else cost
        self.setObjectName("lockedLinePanel")
        self.setProperty("factoryV2", True)
        _use_transparent_surface(self)
        self.setProperty("lineId", line.line_id)
        self.setProperty("unlockCost", self._unlock_cost)
        self.setMinimumHeight(112)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(5)
        heading = QHBoxLayout()
        identifier = FactoryV2LinePlate(f"{self._track_label} {self._line_number:02d}")
        identifier.setObjectName("expansionTrackIdentifier")
        identifier.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        heading.addWidget(identifier)
        heading.addStretch(1)
        indicator = FactoryV2ActiveIndicator()
        indicator.setProperty("scopePaused", True)
        heading.addWidget(indicator)
        layout.addLayout(heading)

        self._unlock_button = GameButton(
            f"UNLOCK  ${self._unlock_cost:,.2f}",
            variant="primary",
            accent=Accent.BUILD,
        )
        self._unlock_button.setObjectName("unlockTrackButton")
        self._unlock_button.setProperty("unlockCost", self._unlock_cost)
        self._unlock_button.setAccessibleName(f"UNLOCK ${self._unlock_cost:,.2f}")
        self._unlock_button.setFixedSize(186, 38)
        self._unlock_button.clicked.connect(self.activated.emit)
        layout.addWidget(self._unlock_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.set_unlock_enabled(enabled)

    def set_unlock_enabled(self, enabled: bool) -> None:
        self.setProperty("unlockEnabled", enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self._unlock_button.setEnabled(enabled)
        self._unlock_button.update()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_production_track(painter, rect, active=False, variant=self._line_number - 1)
        finally:
            painter.end()


class FactoryV2HallOverview(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("factoryV2HallOverview")
        _use_transparent_surface(self)
        self.setMinimumHeight(96)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_hall_control_assembly(painter, rect, variant=1)
        finally:
            painter.end()
        super().paintEvent(event)


class FactoryV2Board(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("factoryV2Board")
        _use_transparent_surface(self)
        self._resource_drawer: FactoryV2ResourceDrawer | None = None

    def set_resource_drawer(self, drawer: FactoryV2ResourceDrawer | None) -> None:
        self._resource_drawer = drawer
        if drawer is not None:
            drawer.setParent(self)
            self._position_resource_drawer()
            drawer.show()
            drawer.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._position_resource_drawer()
        super().resizeEvent(event)

    def _position_resource_drawer(self) -> None:
        if self._resource_drawer is None:
            return
        margin = 12
        width = min(420, max(330, self.width() // 3))
        height = max(160, self.height() - margin * 2)
        self._resource_drawer.setGeometry(self.width() - width - margin, margin, width, height)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_game_surface(painter, rect, accent=Accent.NEUTRAL, radius=18, depth=1, role="board")
        finally:
            painter.end()
        super().paintEvent(event)


class FactoryV2TrackPanel(QFrame):
    def __init__(self, line_number: int, line_name: str) -> None:
        super().__init__()
        self._line_number = line_number
        self._line_name = line_name
        self.setObjectName("factoryV2ProductionTrack")
        _use_transparent_surface(self)
        self.setMinimumHeight(FACTORY_V2_TRACK_HEIGHT)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_production_track(
                painter,
                rect,
                active=self.property("trackAccentActive") is not False,
                variant=self._line_number - 1,
            )
        finally:
            painter.end()
        super().paintEvent(event)


class ProductionBoardViewV2(ReleaseBoardMixin, FactoryViewBase):
    def __init__(self, state, command_bus, definitions, board_config: ProductionBoardConfig | None = None) -> None:
        self._resources_drawer_open = False
        self._resource_drawer: FactoryV2ResourceDrawer | None = None
        self._factory_v2_board: FactoryV2Board | None = None
        self._factory_v2_scroll: QScrollArea | None = None
        self._track_continuation_cue: QLabel | None = None
        self._resources_button: FactoryV2CommandButton | None = None
        self._structural_refresh_count = 0
        self._factory_v2_scroll_values: dict[str, tuple[int, int]] = {}
        self._factory_v2_scroll_restore_generation = 0
        super().__init__(state, command_bus, definitions, board_config)
        self.setObjectName(f"{self._board_config.board_kind}ViewV2")
        sidebar = self.findChild(QFrame, "sidebar")
        if sidebar is not None:
            sidebar.setObjectName("factoryV2Sidebar")
            nav_title = sidebar.findChild(QLabel, "factoryNavTitle")
            if nav_title is not None:
                nav_title.setObjectName("factoryV2NavTitle")
            nav_subtitle = sidebar.findChild(QLabel, "factoryNavSubtitle")
            if nav_subtitle is not None:
                nav_subtitle.setObjectName("factoryV2NavSubtitle")
        self._hall_tree.setObjectName("hallTreeV2")
        self._build_hall_button.setObjectName("buildHallButtonV2")
        self._hall_tree.setRootIsDecorated(False)
        from production_zero.ui.interaction_polish import bind_building_tree
        bind_building_tree(self._hall_tree, self._rename_building,
                           lambda uid: self._release_action(lambda: self._sell_building(uid)))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        QTimer.singleShot(0, self, self._update_track_continuation_cue)

    def _refresh_runtime_widgets(self) -> None:
        super()._refresh_runtime_widgets()
        if hasattr(self, "_selected_empty_slots"):
            self._release_setup()
            self._update_selection_visuals()
        for button in self.findChildren(GameButton):
            if hasattr(button, "refresh_pause"):
                button.refresh_pause()
            if hasattr(button, "refresh_quote"):
                button.refresh_quote()
        hall = self._units.get(self._selected_hall_id)
        if hall is not None:
            for indicator in self.findChildren(FactoryV2ActiveIndicator):
                line_id = indicator.property("lineId")
                line = next((line for line in hall.production_lines if line.line_id == line_id), None)
                indicator.setProperty("scopePaused", hall.paused or bool(line and line.paused))
                indicator.update()
    def _refresh_build_hall_button(self) -> None:
        super()._refresh_build_hall_button()
        if self._board_config.board_kind == "resources":
            self._build_hall_button.setText("BUILD SITE")
            self._build_hall_button.setEnabled(True)

    def _refresh_hall_tree(self) -> None:
        self._hall_tree.blockSignals(True)
        from production_zero.core.building_order import ordered_building_ids
        ids = ordered_building_ids(self._state, self._board_config.board_kind, self._units)
        if ids != getattr(self, '_hall_navigation_ids', None):
            self._hall_tree.clear()
            self._hall_navigation_ids = ids
            for hall_id in ids:
                item = QTreeWidgetItem()
                item.setData(0, Qt.ItemDataRole.UserRole, hall_id)
                self._hall_tree.addTopLevelItem(item)
        for index, hall_id in enumerate(ids):
            hall = self._units[hall_id]
            item = self._hall_tree.topLevelItem(index)
            label = self._hall_nav_label(hall)
            if item.text(0) != label:
                item.setText(0, label)
            if hall.hall_id == self._selected_hall_id:
                self._hall_tree.setCurrentItem(item)
        self._hall_tree.blockSignals(False)
        self._refresh_build_hall_button()

    def _hall_nav_label(self, hall: FactoryHall) -> str:
        occupied = sum(1 for index in hall.unlocked_slot_indexes() if hall.slots[index].card_id is not None)
        active_lines = sum(1 for line in hall.production_lines if line.unlocked)
        slots = count_label(hall.slot_count, "slot")
        tracks = count_label(active_lines, self._board_config.track_label.lower())
        return f"{hall.name}\n{occupied} / {slots} · {tracks}"

    def _refresh_content(self) -> None:
        header = getattr(self.window(), "_global_header", None)
        if header is not None:
            header.refresh()
        # Keep one board under informational drawers. These screens do not edit
        # its widgets; restoring it still validates current structure and data.
        if self._drawer_mode is None:
            self._restore_suspended_board()
        if self._refresh_existing_board():
            return
        self._cancel_machine_drag()
        self._structural_refresh_count += 1
        previous_scroll = self._capture_factory_scroll()
        self._hide_card_selection_hover()
        if self._drawer_mode in ("guide", "unlock_tree", "chain", "used_in") and self._valid_v2_board():
            names = ("_factory_v2_board", "_factory_v2_scroll", "_track_continuation_cue",
                     "_resources_button", "_resource_drawer", "_resource_summary", "_kpi_strip",
                     "_slot_widgets", "_release_selection_surface", "_line_panels",
                     "_line_panel_signatures", "_board_frame_signature")
            self._suspended_board = {name: getattr(self, name, None) for name in names}
            self._content_layout.removeWidget(self._factory_v2_board)
            self._factory_v2_board.hide()
        cached_guide = getattr(self, "_cached_guide_panel", None)
        if cached_guide is not None:
            self._content_layout.removeWidget(cached_guide)
            cached_guide.hide()
        cached_unlock_tree = getattr(self, "_cached_unlock_tree_panel", None)
        if cached_unlock_tree is not None:
            self._content_layout.removeWidget(cached_unlock_tree)
            cached_unlock_tree.hide()
        self._detach_runtime_widget_references()
        self._clear_layout(self._content_layout)

        hall = self._units[self._selected_hall_id]
        self._board_frame_signature = self._frame_signature(hall)
        self._line_panels = {}
        self._line_panel_signatures = {}
        if self._drawer_mode == "cards":
            self._content_layout.addWidget(self._build_factory_card_selection_view(hall), 1)
            return
        if self._drawer_mode == "production":
            self._content_layout.addWidget(self._build_production_selection_view(), 1)
            return
        if self._drawer_mode == "guide":
            self._content_layout.addWidget(self._build_production_guide_view(), 1)
            return
        if self._drawer_mode == "unlock_tree":
            self._content_layout.addWidget(self._build_unlock_tree_view(), 1)
            return
        if self._drawer_mode == "chain":
            self._content_layout.addWidget(self._build_chain_inspector_view(), 1)
            return
        if self._drawer_mode == "used_in":
            self._content_layout.addWidget(self._build_used_in_detail_view(), 1)
            return

        board = FactoryV2Board()
        self._factory_v2_board = board
        board_layout = QVBoxLayout(board)
        board_layout.setContentsMargins(14, 12, 14, 14)
        board_layout.setSpacing(10)

        overview = FactoryV2HallOverview()
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(12, 8, 12, 8)
        overview_layout.setSpacing(10)
        stage = FactoryV2HallStage(hall, self._state)
        from production_zero.ui.interaction_polish import TitleRenameFilter, pause_button
        from production_zero.core.commands import PauseProductionScope
        stage._rename_filter = TitleRenameFilter(stage, self._rename_building)
        overview_layout.addWidget(stage, 1)
        overview_layout.addWidget(pause_button(self, lambda: tuple(s.card_id for s in hall.slots if s.card_id),
                                  self._state, self._command_bus, self.refresh_runtime, scope=lambda: hall.paused,
                                  command=lambda paused: PauseProductionScope(self._board_config.board_kind, hall.hall_id, paused)))
        if self._board_config.board_kind in {"resources", "factory"}:
            from production_zero.ui.group_actions import BuildingMkButton
            overview_layout.addWidget(BuildingMkButton(
                self, lambda: tuple(s.card_id for s in hall.slots if s.card_id),
                lambda: self._release_action(self._upgrade_building),
            ))
        if self._board_config.production_guide_enabled:
            guide = FactoryV2CommandButton("Production Guide", accent=Accent.BUILD)
            guide.setObjectName("productionGuideButton")
            guide.setFixedSize(178, 42)
            guide.clicked.connect(lambda: self._open_production_guide())
            overview_layout.addWidget(guide)
        if self._board_config.resource_drawer_enabled and self._board_config.board_kind != 'factory':
            resources = FactoryV2CommandButton("Resources", accent=Accent.STORAGE)
            resources.setObjectName('resourcesButton')
            resources.setProperty('drawerOpen', self._resources_drawer_open)
            resources.setFixedSize(132, 42)
            resources.clicked.connect(lambda checked=False: self._toggle_resources_drawer())
            self._resources_button = resources
            overview_layout.addWidget(resources)
        self._kpi_strip = FactoryV2KpiStripWidget(self._state)
        overview_layout.addWidget(self._kpi_strip)
        board_layout.addWidget(overview)
        self._release_toolbar(board_layout)

        scroll = QScrollArea()
        scroll.setObjectName("factoryV2Scroll")
        self._factory_v2_scroll = scroll
        _use_transparent_surface(scroll)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().setObjectName("factoryV2ScrollViewport")
        _use_transparent_surface(scroll.viewport())
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        lines = QWidget()
        lines.setObjectName("factoryV2LinesContent")
        _use_transparent_surface(lines)
        lines_layout = QVBoxLayout(lines)
        lines_layout.setContentsMargins(0, 0, 0, 14)
        from PySide6.QtWidgets import QLayout
        lines_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        lines_layout.setSpacing(10)
        next_locked = next((line.line_id for line in hall.production_lines if not line.unlocked), None)
        for line in hall.production_lines:
            if line.unlocked or line.line_id == next_locked:
                panel = self._build_line_panel(line, hall)
                lines_layout.addWidget(panel)
                self._line_panels[line.line_id] = panel
                self._line_panel_signatures[line.line_id] = self._line_signature(hall, line)
        panels = [lines_layout.itemAt(i).widget() for i in range(lines_layout.count())]
        lines.setMinimumHeight(sum(max(p.minimumHeight(), p.minimumSizeHint().height(), p.sizeHint().height()) for p in panels)
                               + lines_layout.spacing() * max(0, len(panels)-1) + 14)
        lines_layout.addStretch(1)
        scroll.setWidget(lines)
        self._release_selection_surface = lines
        lines.installEventFilter(self)
        scroll.viewport().setObjectName("factoryV2ScrollViewport")
        _use_transparent_surface(scroll.viewport())
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        cue = QLabel("›", scroll.viewport())
        cue.setObjectName("factoryV2TrackContinuationCue")
        cue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cue.setFixedSize(26, 64)
        cue.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        cue.setStyleSheet(
            "background: rgba(8, 12, 12, 190); color: #ffd21f; "
            "border: 1px solid rgba(255, 210, 31, 120); border-radius: 8px; font-size: 24px; font-weight: 900;"
        )
        self._track_continuation_cue = cue
        horizontal = scroll.horizontalScrollBar()
        horizontal.rangeChanged.connect(lambda *_: self._update_track_continuation_cue())
        horizontal.valueChanged.connect(lambda *_: self._update_track_continuation_cue())
        QTimer.singleShot(0, self, self._update_track_continuation_cue)
        board_layout.addWidget(scroll, 1)
        self._resource_drawer = None
        if self._resources_drawer_open and self._board_config.resource_drawer_enabled:
            self._resource_drawer = FactoryV2ResourceDrawer(self._state, self._definitions, hall)
            self._resource_drawer.close_button.clicked.connect(lambda checked=False: self._close_resources_drawer())
            self._resource_drawer.summary.chain_requested.connect(self._open_chain_from_hall)
            board.set_resource_drawer(self._resource_drawer)
            self._resource_summary = self._resource_drawer.summary
        self._content_layout.addWidget(board, 1)
        self._restore_factory_scroll(previous_scroll)
        self._update_selection_visuals()

    def _restore_suspended_board(self) -> None:
        context = getattr(self, "_suspended_board", None)
        if context is None:
            return
        self._suspended_board = None
        board = context["_factory_v2_board"]
        if not is_qt_object_valid(board):
            return
        # Remove the drawer before reattaching the retained board. Session-owned
        # guide/tree panels keep their existing caches and QObject parent.
        for name in ("_cached_guide_panel", "_cached_unlock_tree_panel"):
            panel = getattr(self, name, None)
            if panel is not None and is_qt_object_valid(panel):
                self._content_layout.removeWidget(panel)
                panel.hide()
        self._clear_layout(self._content_layout)
        for name, value in context.items():
            setattr(self, name, value)
        self._content_layout.addWidget(board, 1)
        board.show()

    def _frame_signature(self, hall):
        return (id(hall), hall.hall_id, hall.name, hall.specialization,
                hall.max_lines, hall.max_slots_per_line, self._resources_drawer_open,
                tuple((line.line_id, line.unlocked) for line in hall.production_lines))

    @staticmethod
    def _line_signature(hall, line):
        return (line.name, line.unlocked, line.unlock_cost, line.paused,
                tuple(line.slot_indexes), tuple(hall.slots[i].card_id for i in line.slot_indexes))

    def _refresh_existing_board(self):
        if self._drawer_mode is not None or not self._valid_v2_board():
            return False
        hall = self._units[self._selected_hall_id]
        if getattr(self, "_board_frame_signature", None) != self._frame_signature(hall):
            return False
        previous_scroll = self._capture_factory_scroll()
        changed = False
        for line in hall.production_lines:
            old = self._line_panels.get(line.line_id)
            if old is None:
                continue
            signature = self._line_signature(hall, line)
            if signature == self._line_panel_signatures.get(line.line_id):
                continue
            self._hide_card_selection_hover()
            for index, widget in list(self._slot_widgets.items()):
                if old.isAncestorOf(widget):
                    self._slot_widgets.pop(index)
            panel = self._build_line_panel(line, hall)
            old.parentWidget().layout().replaceWidget(old, panel)
            panel.show()
            from production_zero.ui.widget_lifecycle import hide_detach_delete
            hide_detach_delete(old)
            self._line_panels[line.line_id] = panel
            self._line_panel_signatures[line.line_id] = signature
            changed = True
        if changed:
            lines = self._release_selection_surface
            layout = lines.layout()
            panels = list(self._line_panels.values())
            lines.setMinimumHeight(sum(max(p.minimumHeight(), p.minimumSizeHint().height(), p.sizeHint().height()) for p in panels)
                                   + layout.spacing() * max(0, len(panels)-1) + 14)
            # Mouse selection may follow a completed command before the next
            # event-loop pass. Commit replacement geometry synchronously.
            layout.invalidate()
            layout.activate()
            self._restore_factory_scroll(previous_scroll)
        self._refresh_runtime_widgets()
        self._update_selection_visuals()
        return True

    def show_frontscreen(self):
        self._close_resources_drawer()
        if self._drawer_mode is not None:
            self._close_drawer()
        self._hide_card_selection_hover()

    def _toggle_resources_drawer(self) -> None:
        self._set_resources_drawer_open(not self._resources_drawer_open)

    def _close_resources_drawer(self) -> None:
        self._set_resources_drawer_open(False)

    def _set_resources_drawer_open(self, open_: bool) -> None:
        if self._resources_drawer_open == open_:
            return
        if self._drawer_mode is not None or not self._valid_v2_board():
            self._resources_drawer_open = open_
            self._refresh_content()
            return
        self._resources_drawer_open = open_
        if self._resources_button is not None and is_qt_object_valid(self._resources_button):
            self._resources_button.setProperty("drawerOpen", self._resources_drawer_open)
            self._resources_button.style().unpolish(self._resources_button)
            self._resources_button.style().polish(self._resources_button)
            self._resources_button.update()
        if not open_:
            if self._resource_drawer is not None and is_qt_object_valid(self._resource_drawer):
                self._resource_drawer.hide()
                self._resource_drawer.setParent(None)
                self._resource_drawer.deleteLater()
            self._resource_drawer = None
            self._resource_summary = None
            return
        hall = self._units[self._selected_hall_id]
        self._resource_drawer = FactoryV2ResourceDrawer(self._state, self._definitions, hall)
        self._resource_drawer.close_button.clicked.connect(lambda checked=False: self._close_resources_drawer())
        self._resource_drawer.summary.chain_requested.connect(self._open_chain_from_hall)
        self._factory_v2_board.set_resource_drawer(self._resource_drawer)
        self._resource_summary = self._resource_drawer.summary

    def _valid_v2_board(self) -> bool:
        return self._factory_v2_board is not None and is_qt_object_valid(self._factory_v2_board)

    def _valid_v2_scroll(self) -> bool:
        return self._factory_v2_scroll is not None and is_qt_object_valid(self._factory_v2_scroll)

    def _capture_factory_scroll(self) -> tuple[int, int] | None:
        if not self._valid_v2_scroll():
            return None
        values = (
            self._factory_v2_scroll.horizontalScrollBar().value(),
            self._factory_v2_scroll.verticalScrollBar().value(),
        )
        self._factory_v2_scroll_values[self._selected_hall_id] = values
        return values

    def _restore_factory_scroll(self, values: tuple[int, int] | None) -> None:
        if values is None:
            values = self._factory_v2_scroll_values.get(self._selected_hall_id)
        if values is None or not self._valid_v2_scroll():
            return
        self._factory_v2_scroll_restore_generation += 1
        generation = self._factory_v2_scroll_restore_generation
        scroll = self._factory_v2_scroll
        self._restore_scroll_late(scroll, values, generation)
        for delay in (0, 16, 50):
            QTimer.singleShot(
                delay,
                scroll,
                lambda scroll=scroll, values=values, generation=generation: self._restore_scroll_late(scroll, values, generation),
            )

    def _restore_scroll_late(self, scroll: QScrollArea | None, values: tuple[int, int], generation: int) -> None:
        if generation != self._factory_v2_scroll_restore_generation:
            return
        if scroll is None or not is_qt_object_valid(scroll):
            return
        horizontal, vertical = values
        scroll.horizontalScrollBar().setValue(min(horizontal, scroll.horizontalScrollBar().maximum()))
        scroll.verticalScrollBar().setValue(min(vertical, scroll.verticalScrollBar().maximum()))
        self._update_track_continuation_cue()

    def _update_track_continuation_cue(self) -> None:
        if not self._valid_v2_scroll() or self._track_continuation_cue is None or not is_qt_object_valid(self._track_continuation_cue):
            return
        scroll = self._factory_v2_scroll
        bar = scroll.horizontalScrollBar()
        cue = self._track_continuation_cue
        cue.setVisible(bar.maximum() > 0 and bar.value() < bar.maximum())
        cue.move(scroll.viewport().width() - cue.width() - 5, max(8, (scroll.viewport().height() - cue.height()) // 2))
        cue.raise_()

    def _detach_runtime_widget_references(self) -> None:
        super()._detach_runtime_widget_references()
        self._resource_drawer = None
        self._factory_v2_board = None
        self._factory_v2_scroll = None
        self._track_continuation_cue = None
        self._resources_button = None

    def _build_line_panel(self, line: ProductionLine, hall: FactoryHall) -> QFrame:
        line_number = hall.production_lines.index(line) + 1
        if not line.unlocked:
            cost=unit_line_price(hall,line_number,self._board_config.board_kind)
            locked = FactoryV2LockedLine(line, line_number, self._state.cash.amount >= cost, self._board_config.track_label,cost=cost)
            locked.activated.connect(lambda line_id=line.line_id,cost=cost: self._release_action(lambda:self._unlock_line(line_id,cost)))
            return locked
        panel = FactoryV2TrackPanel(line_number, line.name)
        panel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        panel._template_line_id = line.line_id
        panel._release_rectangle_surface = True
        panel.installEventFilter(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(4)
        header = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        title = FactoryV2LinePlate(f"{self._board_config.track_label} {line_number:02d}")
        title_stack.addWidget(title)
        header.addLayout(title_stack)
        from production_zero.ui.interaction_polish import pause_button
        from production_zero.core.commands import PauseProductionScope
        pause_line = pause_button(self, lambda: tuple(hall.slots[i].card_id for i in line.slot_indexes if hall.slots[i].card_id),
                                  self._state, self._command_bus, self.refresh_runtime, name="sectorPauseButton", scope=lambda: line.paused,
                                  command=lambda paused: PauseProductionScope(self._board_config.board_kind, hall.hall_id, paused, line.line_id))
        header.addWidget(pause_line)
        header.addStretch(1)
        indicator = FactoryV2ActiveIndicator()
        indicator.setProperty("lineId", line.line_id)
        indicator.setProperty("scopePaused", hall.paused or line.paused)
        header.addWidget(indicator)
        layout.addLayout(header)
        slots = QHBoxLayout()
        slots.setSpacing(8)
        for slot_number in range(1, hall.max_slots_per_line + 1):
            if slot_number <= len(line.slot_indexes):
                slot_index = line.slot_indexes[slot_number - 1]
                slot = hall.slots[slot_index]
                card = self._state.cards.get(slot.card_id) if slot.card_id else None
                definition = self._definitions.get(card.definition_id) if card else None
                production_state = self._state.machine_production.get(card.card_id) if card else None
                if card is None:
                    widget = FactoryV2BuildSlot()
                    widget.setFixedSize(FACTORY_V2_CARD_WIDTH, FACTORY_V2_CARD_HEIGHT)
                    widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                    widget.clicked.connect(lambda slot_index=slot_index: self._on_slot_clicked(slot_index))
                else:
                    widget = FactoryV2MachineCard(slot, card, definition, production_state, self._state)
                    widget.hovered.connect(lambda card_id, source=widget: self._show_card_selection_hover(card_id, source))
                    widget.unhovered.connect(self._hide_card_selection_hover)
                    widget.clicked.connect(self._on_slot_clicked)
                    widget.production_change_requested.connect(self._open_production_drawer)
                    widget.chain_requested.connect(self._open_chain_from_hall)
                    if slot_index in self._recent_install_slot_indexes:
                        widget.setProperty("installFlash", True)
                        QTimer.singleShot(170, widget, lambda widget=widget: self._clear_v2_flash(widget))
                        self._recent_install_slot_indexes.discard(slot_index)
                self._slot_widgets[slot_index] = widget
                self._release_bind_widget(widget, slot_index)
                slots.addWidget(widget)
            else:
                from production_zero.core.infrastructure_prices import unit_slot_price
                cost = unit_slot_price(hall,line_number,slot_number,self._board_config.board_kind)
                is_next = slot_number == len(line.slot_indexes) + 1
                locked_slot = FactoryV2LockedSlot(line.line_id, slot_number, cost, is_next and self._state.cash.amount >= cost)
                locked_slot.setProperty("isNextUnlock", is_next)
                locked_slot.setToolTip(f"Unlock S{slot_number:02d} · ${cost:,.2f}" if is_next else f"Unlock S{slot_number - 1:02d} first")
                locked_slot.activated.connect(lambda line_id=line.line_id,cost=cost:self._release_action(lambda:self._unlock_slot(line_id,cost)))
                slots.addWidget(locked_slot)
        for i in range(slots.count()):
            widget = slots.itemAt(i).widget()
            if widget is not None:
                widget._template_line_id = line.line_id
        layout.addLayout(slots)
        slots.addStretch(1)
        return panel

    def _clear_v2_flash(self, widget: QWidget) -> None:
        if widget is None or not is_qt_object_valid(widget):
            return
        widget.setProperty("installFlash", False)
        widget.update()


class FactoryViewV2(ProductionBoardViewV2):
    """Industrial manufacturing board using the shared V2 operational chassis."""

    def __init__(self, state, command_bus, definitions) -> None:
        super().__init__(state, command_bus, definitions, ProductionBoardConfig())
