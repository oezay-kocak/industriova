from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QTreeWidgetItem, QVBoxLayout, QWidget

from production_zero.core.cards import CardInstance
from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import EnergyType, MachineType
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import FactoryHall, GameState, HallSlot, MachineProductionState, ProductionLine, MAX_FACTORY_SLOTS_PER_LINE, factory_slot_unlock_cost
from production_zero.core.storage_upgrades import MAX_INVENTORY_STORAGE_LEVEL, inventory_storage_upgrade_cost
from production_zero.core.commands import CommandBus, ExpandInventoryStorage
from production_zero.ui.factory_view import (
    ClickableCapacityPanel,
    FactoryView,
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


FACTORY_V2_ENABLED_ENV = "PRODUCTION_ZERO_FACTORY_VIEW_V2"
FACTORY_V2_RESOURCE_IDS = ("iron_ore", "iron", "copper_ore", "copper", "coal", "steel")
FACTORY_V2_CARD_WIDTH = 142
FACTORY_V2_CARD_HEIGHT = 226
FACTORY_V2_LOCKED_SLOT_WIDTH = FACTORY_V2_CARD_WIDTH
FACTORY_V2_LOCKED_SLOT_HEIGHT = FACTORY_V2_CARD_HEIGHT
FACTORY_V2_TRACK_HEIGHT = 286


def _use_transparent_surface(widget: QWidget) -> None:
    widget.setAutoFillBackground(False)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    palette = widget.palette()
    palette.setColor(widget.backgroundRole(), QColor(0, 0, 0, 0))
    widget.setPalette(palette)


def _display_card_title(definition: CardDefinition | None, card: CardInstance | None = None) -> str:
    raw = definition.name if definition is not None else (card.definition_id if card else "Machine")
    title = raw.upper()
    for suffix in (" MK I", " MK II", " MK III", " MK IV", " MK V", " MK 1", " MK 2", " MK 3", " MK 4", " MK 5"):
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


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
                selected=self.underMouse(),
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
                painter.drawText(rect.adjusted(11, 10, -11, -6), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label)
                painter.setPen(QColor("#eff8f4"))
                font = GAME_UI_TOKENS.typography.card_title()
                painter.setFont(font)
                painter.drawText(rect.adjusted(11, 27, -11, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)
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
        self.setFixedHeight(66)
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


class FactoryV2LinePlate(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setObjectName("factoryV2LineTitle")
        self.setMinimumSize(132, 34)
        self.setMaximumWidth(164)
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
        self.setFixedSize(94, 24)
        _use_transparent_surface(self)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            draw_status_led(painter, QRectF(0, 0, self.width(), self.height()), active=True)
        finally:
            painter.end()


class FactoryCommandDeckWidget(QFrame):
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
        self.setMinimumHeight(138)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        title = QVBoxLayout()
        title.setSpacing(6)
        deck = QLabel("COMMAND DECK")
        deck.setObjectName("factoryV2DeckLabel")
        name = QLabel("PRODUCTION ZERO")
        name.setObjectName("factoryV2DeckTitle")
        title.addWidget(deck)
        title.addWidget(name)
        title.addStretch(1)
        layout.addLayout(title, 2)

        systems = FactoryV2CommandModule(accent=Accent.STORAGE)
        systems.setObjectName("factoryV2PrimarySystems")
        systems.setMinimumHeight(96)
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
        self._storage_value = QLabel()
        self._storage_value.setObjectName("factoryV2StorageValue")
        storage_text.addWidget(storage_label)
        storage_text.addWidget(self._storage_value)
        storage_head.addLayout(storage_text, 1)
        storage_box.addLayout(storage_head)
        self._storage_button = GameButton("Expand", variant="primary", accent=Accent.BUILD)
        self._storage_button.setObjectName("expandResourceStorageButton")
        self._storage_button.setProperty("factoryV2StorageCta", True)
        self._storage_button.setMinimumSize(150, 34)
        self._storage_button.clicked.connect(self._expand_resource_storage)
        storage_box.addWidget(self._storage_button)
        systems_layout.addWidget(storage_module, 1)
        layout.addWidget(systems, 4)

        operations = FactoryV2CommandModule(accent=Accent.PROCESSOR)
        operations.setObjectName("factoryV2ResourceStrip")
        operations.setMinimumHeight(96)
        operations_layout = QVBoxLayout(operations)
        operations_layout.setContentsMargins(14, 12, 14, 12)
        operations_layout.setSpacing(5)
        operations_label = QLabel("GLOBAL OPERATIONS")
        operations_label.setObjectName("factoryV2OperationsLabel")
        operations_hint = QLabel("READY FOR FACTORY-WIDE SIGNALS")
        operations_hint.setObjectName("factoryV2OperationsHint")
        operations_hint.setWordWrap(True)
        operations_layout.addWidget(operations_label)
        operations_layout.addStretch(1)
        operations_layout.addWidget(operations_hint)
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
        self._level = QLabel()
        self._level.setObjectName("factoryV2Level")
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
        box.setMinimumWidth(202)
        box_layout = QHBoxLayout(box)
        box_layout.setContentsMargins(10, 8, 10, 8)
        box_layout.setSpacing(10)
        icon_widget = GameIconWidget(icon, accent=accent)
        icon_widget.setFixedSize(38, 38)
        text = QVBoxLayout()
        text.setSpacing(0)
        label_widget = QLabel(label)
        label_widget.setObjectName(f"factoryV2{label.title()}Label")
        value = QLabel()
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
        self._cash_value.setText(f"${self._state.cash.amount:,.0f}")
        self._energy_value.setText(f"{self._state.energy.consumed:.0f}/{self._state.energy.generated:.0f} MW")
        amount = sum(stock.amount for stock in self._state.resources.values())
        capacity = sum(stock.capacity for stock in self._state.resources.values())
        self._storage_value.setText(f"{amount:.0f}/{capacity:.0f}")
        if self._state.inventory_storage_level >= MAX_INVENTORY_STORAGE_LEVEL:
            self._storage_button.setEnabled(False)
            self._storage_button._text = "Max"
        else:
            cost = inventory_storage_upgrade_cost(self._state.inventory_storage_level)
            self._storage_button._text = f"Expand ${cost:.0f}"
            self._storage_button.setEnabled(self._state.cash.amount >= cost)
        self._storage_button.update()
        company = self._state.company
        required = company.xp_to_next_level
        self._level.setText(f"LEVEL {company.level}")
        self._rank_title.setText(company.current_title.upper())
        self._xp.setText(f"{company.current_xp:,.0f} / {required:,.0f} XP")
        self._xp_bar.setRange(0, max(1, round(required)))
        self._xp_bar.setValue(round(company.current_xp))

    def highlight_cash_gain(self, previous_cash: float, current_cash: float) -> None:
        self._cash_value.setText(f"${current_cash:,.0f}")

    def _expand_resource_storage(self) -> None:
        if self._command_bus is None or not self._resource_definitions:
            return
        self._command_bus.dispatch(ExpandInventoryStorage(self._resource_definitions))
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
        if definition.machine_type == MachineType.EXTRACTOR:
            return MachineIcon.EXTRACTOR
        if definition.machine_type == MachineType.PROCESSOR:
            return MachineIcon.PROCESSOR
        if definition.machine_type in (MachineType.ASSEMBLER, MachineType.FABRICATOR):
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
        if definition.machine_type == MachineType.EXTRACTOR:
            return Accent.EXTRACTOR
        if definition.machine_type == MachineType.PROCESSOR:
            return Accent.PROCESSOR
        if definition.machine_type == MachineType.ASSEMBLER:
            return Accent.RARE
    return Accent.STORAGE


def prototype_family_for_definition(definition: CardDefinition | None) -> str:
    if isinstance(definition, EnergyDefinition):
        return "energy"
    if isinstance(definition, MachineDefinition):
        if definition.machine_type == MachineType.EXTRACTOR:
            return "extractor"
        if definition.machine_type == MachineType.PROCESSOR:
            return "processor"
        if definition.machine_type in (MachineType.ASSEMBLER, MachineType.FABRICATOR):
            return "assembly"
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
        self.setMinimumHeight(140)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            header_panel = rect.adjusted(16, 14, -16, -14)
            bridge = QLinearGradient(rect.topLeft(), rect.topRight())
            bridge.setColorAt(0.0, QColor(255, 210, 31, 13))
            bridge.setColorAt(0.42, QColor(255, 255, 255, 3))
            bridge.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bridge)
            painter.drawRoundedRect(header_panel.adjusted(0, 7, -0, -header_panel.height() * 0.70), 4, 4)
            occupied = sum(1 for index in self._hall.unlocked_slot_indexes() if self._hall.slots[index].card_id is not None)
            active_lines = sum(1 for line in self._hall.production_lines if line.unlocked)
            font = GAME_UI_TOKENS.typography.brand_display()
            font.setPointSize(40)
            painter.setFont(font)
            painter.setPen(QColor("#eff8f4"))
            painter.drawText(header_panel.adjusted(20, 14, -18, -20), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._hall.name.upper())
            font = GAME_UI_TOKENS.typography.industrial_label()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(QColor("#9fb2ad"))
            painter.drawText(
                header_panel.adjusted(22, 74, -18, -12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                f"{occupied} / {self._hall.slot_count} slots   ·   {active_lines} active lines   ·   {self._state.energy.consumed:.0f}/{self._state.energy.generated:.0f} MW",
            )
        finally:
            painter.end()


class FactoryV2MachineCard(QWidget):
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

    def set_data(
        self,
        slot: HallSlot,
        card: CardInstance | None,
        definition: CardDefinition | None,
        production_state: MachineProductionState | None,
        state: GameState | None = None,
    ) -> None:
        self._slot = slot
        self._card = card
        self._definition = definition
        self._production_state = production_state
        if state is not None:
            self._state = state
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._card is not None and self._production_change_available() and self._resource_control_rect().contains(event.position()):
                self.production_change_requested.emit(self._card.card_id)
            else:
                self.clicked.emit(self._slot.index)
            return
        super().mousePressEvent(event)

    def _production_change_available(self) -> bool:
        return isinstance(self._definition, MachineDefinition) and len(self._definition.available_production_options) > 1

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
            return "NO RESOURCE SELECTED" if self._definition.machine_type == MachineType.EXTRACTOR else "NO RECIPE SELECTED"
        if isinstance(self._definition, EnergyDefinition):
            return f"+{self._definition.base_power_output * (self._card.output_multiplier if self._card else 1):.0f} MW"
        if isinstance(self._definition, RecipeDefinition) and self._definition.output_resources:
            return next(iter(self._definition.output_resources)).replace("_", " ").upper()
        return "MODULE"

    def _primary_value_text(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return "SELECT"
            output = production.output_amount_for(self._definition) * (self._card.output_multiplier if self._card else 1)
            return f"+{output:.0f}/cycle"
        if isinstance(self._definition, EnergyDefinition):
            return f"+{self._definition.base_power_output * (self._card.output_multiplier if self._card else 1):.0f} MW"
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
            return f"+{output:.0f}/cycle · {power:.0f} MW"
        if isinstance(self._definition, EnergyDefinition):
            return "Fuel required" if self._definition.requires_fuel else "No fuel"
        return ""

    def _status_text(self) -> str:
        if isinstance(self._definition, EnergyDefinition):
            return "ONLINE"
        if self._production_state is None:
            return "IDLE"
        if self._production_state.is_unconfigured:
            return "NO RESOURCE" if isinstance(self._definition, MachineDefinition) and self._definition.machine_type == MachineType.EXTRACTOR else "NO RECIPE"
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
        meta = ""
        if hasattr(self._definition, "mk_level"):
            meta = f"MK{self._definition.mk_level}"
        if self._card is not None:
            meta = f"{meta} · {self._card.rarity.value.upper()}".strip(" ·")
        return meta

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
            if self._definition.machine_type == MachineType.EXTRACTOR:
                return f"SELECT RESOURCE{chevron}" if self._production_change_available() else "NO RESOURCE"
            return f"SELECT RECIPE{chevron}" if self._production_change_available() else "NO RECIPE"
        if isinstance(self._definition, EnergyDefinition) and self._definition.requires_fuel and self._definition.fuel_resource_id:
            return self._definition.fuel_resource_id.replace("_", " ").upper()
        return ""

    def _prototype_disabled(self) -> bool:
        return self._status_text() == "NO POWER"

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
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
            if self.property("installFlash"):
                painter.setPen(QPen(QColor(216, 240, 106, 170), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 14, 14)
            footer = QRectF(rect.left() + 10, rect.bottom() - 27, rect.width() - 20, 18)
            progress = QRectF(rect.left() + 18, footer.top() - 7, rect.width() - 36, 4)
            self._draw_cycle_progress(painter, progress)
            self._draw_status_band(painter, footer)

        finally:
            painter.end()


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
            painter.drawText(QRectF(module.left() + 8, module.top() + 131, module.width() - 16, 22), Qt.AlignmentFlag.AlignCenter, f"${self._cost:.0f}")
        finally:
            painter.end()


class FactoryV2LockedLine(ClickableCapacityPanel):
    def __init__(self, line: ProductionLine, line_number: int, enabled: bool) -> None:
        super().__init__(enabled=enabled)
        self._line = line
        self._line_number = line_number
        self.setObjectName("lockedLinePanel")
        self.setProperty("factoryV2", True)
        _use_transparent_surface(self)
        self.setProperty("lineId", line.line_id)
        self.setProperty("unlockCost", line.unlock_cost)
        self.setMinimumHeight(104)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            draw_track_surface(painter, rect, accent=Accent.NEUTRAL, radius=16)
            painter.setPen(QColor("#f2c25b"))
            font = GAME_UI_TOKENS.typography.industrial_title()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(rect.adjusted(22, 18, -20, -10), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, f"EXPANSION LINE {self._line_number:02d}")
            font = GAME_UI_TOKENS.typography.secondary_label()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#eff8f4"))
            painter.drawText(rect.adjusted(22, 50, -20, -10), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, f"Unlock Production Line · ${self._line.unlock_cost:.0f}")
        finally:
            painter.end()


class FactoryV2HallOverview(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("factoryV2HallOverview")
        _use_transparent_surface(self)
        self.setMinimumHeight(168)

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


class FactoryViewV2(FactoryView):
    def __init__(self, state, command_bus, definitions) -> None:
        super().__init__(state, command_bus, definitions)
        self.setObjectName("factoryViewV2")
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

    def _refresh_build_hall_button(self) -> None:
        super()._refresh_build_hall_button()

    def _refresh_hall_tree(self) -> None:
        self._hall_tree.blockSignals(True)
        self._hall_tree.clear()
        for hall in self._state.halls.values():
            item = QTreeWidgetItem([self._hall_nav_label(hall)])
            item.setData(0, Qt.ItemDataRole.UserRole, hall.hall_id)
            self._hall_tree.addTopLevelItem(item)
            if hall.hall_id == self._selected_hall_id:
                self._hall_tree.setCurrentItem(item)
        self._hall_tree.blockSignals(False)
        self._refresh_build_hall_button()

    def _hall_nav_label(self, hall: FactoryHall) -> str:
        occupied = sum(1 for index in hall.unlocked_slot_indexes() if hall.slots[index].card_id is not None)
        active_lines = sum(1 for line in hall.production_lines if line.unlocked)
        return f"{hall.name}\n{occupied} / {hall.slot_count} slots · {active_lines} lines"

    def _refresh_content(self) -> None:
        self._hide_card_selection_hover()
        self._detach_runtime_widget_references()
        self._clear_layout(self._content_layout)

        hall = self._state.halls[self._selected_hall_id]
        if self._drawer_mode == "cards":
            self._content_layout.addWidget(self._build_factory_card_selection_view(hall), 1)
            return
        if self._drawer_mode == "production":
            self._content_layout.addWidget(self._build_production_selection_view(), 1)
            return
        if self._drawer_mode == "guide":
            self._content_layout.addWidget(self._build_production_guide_view(), 1)
            return
        if self._drawer_mode == "chain":
            self._content_layout.addWidget(self._build_chain_inspector_view(), 1)
            return

        board = FactoryV2Board()
        board_layout = QVBoxLayout(board)
        board_layout.setContentsMargins(16, 14, 16, 16)
        board_layout.setSpacing(14)

        overview = FactoryV2HallOverview()
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(14, 12, 14, 12)
        overview_layout.setSpacing(12)
        stage = FactoryV2HallStage(hall, self._state)
        overview_layout.addWidget(stage, 5)
        self._resource_summary = FactoryV2HallResourceSummaryWidget(self._state, self._definitions, hall)
        self._resource_summary.chain_requested.connect(self._open_chain_from_hall)
        overview_layout.addWidget(self._resource_summary, 4)
        right_stack = QVBoxLayout()
        right_stack.setContentsMargins(0, 8, 0, 0)
        right_stack.setSpacing(10)
        self._kpi_strip = FactoryV2KpiStripWidget(self._state)
        right_stack.addWidget(self._kpi_strip)
        guide = FactoryV2CommandButton("Production Guide", accent=Accent.BUILD)
        guide.setObjectName("productionGuideButton")
        guide.setMinimumWidth(190)
        guide.clicked.connect(lambda: self._open_production_guide())
        right_stack.addWidget(guide)
        right_stack.addStretch(1)
        overview_layout.addLayout(right_stack, 2)
        board_layout.addWidget(overview)

        scroll = QScrollArea()
        scroll.setObjectName("factoryV2Scroll")
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
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(14)
        for line in hall.production_lines:
            lines_layout.addWidget(self._build_line_panel(line, hall))
        lines_layout.addStretch(1)
        scroll.setWidget(lines)
        scroll.viewport().setObjectName("factoryV2ScrollViewport")
        _use_transparent_surface(scroll.viewport())
        scroll.viewport().setStyleSheet("background: transparent; border: 0;")
        board_layout.addWidget(scroll, 1)
        self._content_layout.addWidget(board, 1)

    def _build_line_panel(self, line: ProductionLine, hall: FactoryHall) -> QFrame:
        line_number = hall.production_lines.index(line) + 1
        if not line.unlocked:
            locked = FactoryV2LockedLine(line, line_number, self._state.cash.amount >= line.unlock_cost)
            locked.activated.connect(lambda line_id=line.line_id: self._unlock_line(line_id))
            return locked
        panel = FactoryV2TrackPanel(line_number, line.name)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 16)
        layout.setSpacing(6)
        header = QHBoxLayout()
        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        title = FactoryV2LinePlate(f"LINE {line_number:02d}")
        title_stack.addWidget(title)
        header.addLayout(title_stack)
        header.addStretch(1)
        header.addWidget(FactoryV2ActiveIndicator())
        layout.addLayout(header)
        slots = QHBoxLayout()
        slots.setSpacing(10)
        for slot_number in range(1, MAX_FACTORY_SLOTS_PER_LINE + 1):
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
                    widget.clicked.connect(self._on_slot_clicked)
                    widget.production_change_requested.connect(self._open_production_drawer)
                    widget.chain_requested.connect(self._open_chain_from_hall)
                    self._slot_widgets[slot_index] = widget
                    if slot_index in self._recent_install_slot_indexes:
                        widget.setProperty("installFlash", True)
                        QTimer.singleShot(170, lambda widget=widget: self._clear_v2_flash(widget))
                        self._recent_install_slot_indexes.discard(slot_index)
                slots.addWidget(widget)
            else:
                cost = factory_slot_unlock_cost(line_number, slot_number)
                locked_slot = FactoryV2LockedSlot(line.line_id, slot_number, cost, self._state.cash.amount >= cost)
                locked_slot.activated.connect(lambda line_id=line.line_id: self._unlock_slot(line_id))
                slots.addWidget(locked_slot)
        layout.addLayout(slots)
        slots.addStretch(1)
        return panel

    def _clear_v2_flash(self, widget: QWidget) -> None:
        if widget is None:
            return
        widget.setProperty("installFlash", False)
        widget.update()
