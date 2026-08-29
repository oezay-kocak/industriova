from __future__ import annotations

from collections.abc import Callable
from time import monotonic, perf_counter
from typing import Mapping

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QFrame,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QGridLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.cards import CardInstance, CardStack, effective_recipe_inputs, effective_recipe_outputs
from production_zero.core.commands import CommandBus, InstallCardInHall, PurchaseHall, RemoveCardFromHall, RenameHall, SelectMachineProduction, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.analytics import ResourceFlow
from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition, ProductionOptionDefinition, RecipeDefinition
from production_zero.core.enums import MachineType, Rarity
from production_zero.core.inventory import build_placeable_inventory_stacks
from production_zero.core.economy import hall_purchase_price
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, HallSlot, MachineProductionState, ProductionLine, MAX_FACTORY_SLOTS_PER_LINE, factory_slot_unlock_cost
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.ui.resource_icons import ResourceIconWidget, resource_category, resource_icon_key, resource_accent_key
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.theme import Theme
from production_zero.ui.widget_lifecycle import clear_layout_safely, hide_detach_delete


FACTORY_CARD_SIZE = 132
FACTORY_CARD_MIN_SIZE = 96
FACTORY_CARD_MAX_SIZE = 168
FACTORY_SLOT_SPACING = 6


class ClickableCapacityPanel(QFrame):
    activated = Signal()

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setProperty("unlockEnabled", enabled)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.property("unlockEnabled"):
            self.activated.emit()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self.property("unlockEnabled") and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit()
            return
        super().keyPressEvent(event)


def _ui_feedback_time() -> float:
    return monotonic()


PRODUCTION_STAGE_ORDER = (
    MachineType.EXTRACTOR,
    MachineType.PROCESSOR,
    MachineType.FABRICATOR,
    MachineType.ASSEMBLER,
)
PRODUCTION_STAGE_LABELS = {
    MachineType.EXTRACTOR: "Extraction",
    MachineType.PROCESSOR: "Processing",
    MachineType.FABRICATOR: "Manufacturing",
    MachineType.ASSEMBLER: "Assembly",
}


def _format_io_summary(input_resources: Mapping[str, float], output_resources: Mapping[str, float] | str) -> str:
    output_text = (
        output_resources.replace("_", " ").title()
        if isinstance(output_resources, str)
        else _format_resource_amounts(output_resources)
    )
    if not input_resources:
        return f"Output: {output_text}"
    return f"Input: {_format_resource_amounts(input_resources)} -> {output_text}"


def _format_resource_amounts(resources: Mapping[str, float]) -> str:
    return ", ".join(
        f"{amount:g} {resource_id.replace('_', ' ').title()}"
        for resource_id, amount in resources.items()
    )


def _stage_accent_for_definition(definition: CardDefinition | None) -> QColor:
    if isinstance(definition, EnergyDefinition):
        return QColor(Theme.ENERGY)
    if isinstance(definition, MachineDefinition):
        colors = {
            MachineType.EXTRACTOR: QColor("#7fbf7f"),
            MachineType.PROCESSOR: QColor("#6db7d6"),
            MachineType.FABRICATOR: QColor("#c6a15b"),
            MachineType.ASSEMBLER: QColor("#b08cff"),
        }
        return colors.get(definition.machine_type, QColor(Theme.RESOURCE))
    return QColor(Theme.RESOURCE)


def _stage_name_for_definition(definition: CardDefinition | None) -> str:
    if isinstance(definition, EnergyDefinition):
        return "Energy"
    if isinstance(definition, MachineDefinition):
        return definition.machine_type.value.title()
    return "Card"


def _rarity_accent_for_card(card: CardInstance | None) -> QColor:
    if card is None:
        return QColor(Theme.BORDER)
    colors = {
        Rarity.COMMON: QColor(Theme.DIM),
        Rarity.UNCOMMON: QColor(Theme.GOOD),
        Rarity.RARE: QColor(Theme.ENERGY),
        Rarity.EPIC: QColor("#b98cff"),
        Rarity.LEGENDARY: QColor(Theme.WARN),
    }
    return colors.get(card.rarity, QColor(Theme.BORDER))


class KpiStripWidget(QWidget):
    def __init__(self, state: GameState) -> None:
        super().__init__()
        self._state = state
        self.setObjectName("hallKpiStrip")
        self.setProperty("metrics", "Energy|Revenue")
        self.setMinimumSize(250, 64)
        self.setMaximumWidth(310)
        self.setMaximumHeight(72)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        metrics = (
            ("Energy", f"{self._state.energy.consumed:.1f}/{self._state.energy.generated:.1f} MW", Theme.ENERGY),
            ("Revenue", "$0/min", Theme.CASH),
        )
        gap = 6
        width = (self.width() - gap * (len(metrics) - 1)) / len(metrics)
        for index, (label, value, color) in enumerate(metrics):
            rect = QRectF(index * (width + gap), 0, width, self.height() - 1)
            painter.setPen(QPen(QColor(color), 1))
            painter.setBrush(QColor(255, 255, 255, 8))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(rect.left() + 8, rect.top() + 7, 28, 2), 1, 1)
            painter.setPen(QColor(Theme.MUTED))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            painter.drawText(rect.adjusted(8, 12, -8, -5), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, label.upper())
            painter.setPen(QColor(color))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.drawText(rect.adjusted(8, 28, -8, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)

    def refresh(self) -> None:
        self.update()


class HallResourceSummaryItemWidget(QFrame):
    chain_requested = Signal(str)

    def __init__(self, state: GameState, flow: ResourceFlow) -> None:
        super().__init__()
        self._state = state
        self._resource_id = flow.resource_id
        self._amount_transition_started = _ui_feedback_time()
        self._amount_transition_ms = 220
        self.setObjectName("hallResourceSummaryItem")
        self.setProperty("resourceId", flow.resource_id)
        self.setFixedHeight(62)
        self.setMinimumWidth(172)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(7)

        icon = ResourceIconWidget(
            flow.resource_id,
            resource_icon_key(flow.resource_id),
            resource_accent_key(flow.resource_id),
            size=42,
        )
        icon.setCursor(Qt.CursorShape.PointingHandCursor)
        icon.mousePressEvent = lambda event, resource_id=flow.resource_id: self._emit_chain_request(event, resource_id)  # type: ignore[method-assign]
        layout.addWidget(icon)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        row = QHBoxLayout()
        self._name = QLabel(flow.resource_id.replace("_", " ").upper())
        self._name.setObjectName("hallResourceName")
        self._name.setCursor(Qt.CursorShape.PointingHandCursor)
        self._name.mousePressEvent = lambda event, resource_id=flow.resource_id: self._emit_chain_request(event, resource_id)  # type: ignore[method-assign]
        self._amount = QLabel()
        self._amount.setObjectName("hallResourceAmount")
        info = QPushButton("i")
        info.setObjectName("chainInfoButton")
        info.setFixedSize(18, 18)
        info.clicked.connect(lambda checked=False, resource_id=flow.resource_id: self.chain_requested.emit(resource_id))
        row.addWidget(self._name, 1)
        row.addWidget(info)
        text_layout.addLayout(row)

        amount_row = QHBoxLayout()
        amount_row.addWidget(self._amount)
        self._rate = QLabel()
        self._rate.setObjectName("hallResourceNet")
        amount_row.addWidget(self._rate)
        amount_row.addStretch(1)
        text_layout.addLayout(amount_row)

        self._progress = QProgressBar()
        self._progress.setObjectName("hallResourceStorageProgress")
        self._progress.setRange(0, 1000)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        text_layout.addWidget(self._progress)
        layout.addLayout(text_layout, 1)

        self.update_flow(flow)

    def update_flow(self, flow: ResourceFlow) -> None:
        stock = self._state.ensure_resource(flow.resource_id)
        previous_amount = self.property("targetAmount")
        previous_progress = self.property("targetStorageProgress")
        target_progress = round(stock.fill_ratio * 1000)
        if previous_amount is not None and round(float(previous_amount)) != round(stock.amount):
            self._amount_transition_started = _ui_feedback_time()
            self.setProperty("previousAmount", previous_amount)
            self.setProperty("amountTransitionMs", self._amount_transition_ms)
        if previous_progress is not None and int(previous_progress) != target_progress:
            self.setProperty("previousStorageProgress", previous_progress)
            self.setProperty("storageTransitionMs", self._amount_transition_ms)
        self.setProperty("targetAmount", stock.amount)
        self.setProperty("targetStorageProgress", target_progress)
        self.setProperty("netState", self._net_state(flow.net_per_minute))
        self.setProperty("storageState", self._storage_state(stock.fill_ratio))
        self._amount.setText(f"{stock.amount:.0f} / {stock.capacity:.0f}")
        self._rate.setText(f"{flow.net_per_minute:+.0f}/min")
        self._rate.setProperty("netState", self._net_state(flow.net_per_minute))
        self._progress.setValue(target_progress)
        self._progress.setProperty("storageState", self._storage_state(stock.fill_ratio))
        self.style().unpolish(self)
        self.style().polish(self)
        self._rate.style().unpolish(self._rate)
        self._rate.style().polish(self._rate)
        self._progress.style().unpolish(self._progress)
        self._progress.style().polish(self._progress)
        self.update()

    def _emit_chain_request(self, event, resource_id: str) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.chain_requested.emit(resource_id)

    def _net_state(self, value: float) -> str:
        if value > 0.001:
            return "positive"
        if value < -0.001:
            return "negative"
        return "neutral"

    def _storage_state(self, fill_ratio: float) -> str:
        if fill_ratio >= 0.995:
            return "full"
        if fill_ratio <= 0.05:
            return "empty"
        return "normal"


class HallResourceSummaryWidget(QWidget):
    chain_requested = Signal(str)
    item_widget_class = HallResourceSummaryItemWidget

    def __init__(self, state: GameState, definitions: dict[str, CardDefinition], hall: FactoryHall) -> None:
        super().__init__()
        self._state = state
        self._definitions = definitions
        self._hall = hall
        self.setObjectName("hallResourceSummary")
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(6)
        self._layout.setVerticalSpacing(6)
        self._items: dict[str, HallResourceSummaryItemWidget] = {}
        self._columns = 1
        self.refresh()

    def refresh(self) -> None:
        flows = self._hall_resource_flows()
        for resource_id in list(self._items):
            if resource_id not in flows:
                widget = self._items.pop(resource_id)
                self._layout.removeWidget(widget)
                hide_detach_delete(widget)
        for resource_id in sorted(flows):
            item = self._items.get(resource_id)
            if item is None:
                item = self.item_widget_class(self._state, flows[resource_id])
                item.chain_requested.connect(lambda requested_id: self.chain_requested.emit(requested_id))
                self._items[resource_id] = item
            item.update_flow(flows[resource_id])
        self._relayout_items()
        self.setProperty("layoutMode", "flow")

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._relayout_items()
        super().resizeEvent(event)

    def _relayout_items(self) -> None:
        if not self._items:
            return
        columns = max(1, self.width() // 190) if self.width() > 0 else self._columns
        self._columns = columns
        for index, resource_id in enumerate(sorted(self._items)):
            self._layout.addWidget(self._items[resource_id], index // columns, index % columns)

    def _hall_resource_flows(self) -> dict[str, ResourceFlow]:
        mutable: dict[str, dict[str, float]] = {}
        for slot in self._hall.slots:
            if slot.card_id is None:
                continue
            card = self._state.cards.get(slot.card_id)
            definition = self._definitions.get(card.definition_id) if card is not None else None
            if card is None or not isinstance(definition, MachineDefinition):
                continue
            machine_state = self._state.machine_production.get(card.card_id)
            if machine_state is None or machine_state.selected_production_id is None:
                continue
            production = definition.production_option(machine_state.selected_production_id)
            output_entry = self._flow_entry(mutable, production.output_resource)
            input_entries = {
                resource_id: self._flow_entry(mutable, resource_id)
                for resource_id in production.input_resources
            }
            if machine_state is not None and machine_state.status not in {"running", "idle"}:
                continue
            cycles_per_minute = 60.0 / max(0.001, production.cycle_seconds_for(definition))
            output_entry["produced"] += production.output_amount_for(definition) * card.output_multiplier * cycles_per_minute
            for resource_id, amount in production.input_resources.items():
                input_entries[resource_id]["consumed"] += amount * cycles_per_minute
        return {
            resource_id: ResourceFlow(resource_id, values["produced"], values["consumed"])
            for resource_id, values in mutable.items()
        }

    def _flow_entry(self, flows: dict[str, dict[str, float]], resource_id: str) -> dict[str, float]:
        if resource_id not in flows:
            flows[resource_id] = {"produced": 0.0, "consumed": 0.0}
        return flows[resource_id]

    def _net_state(self, value: float) -> str:
        if value > 0.001:
            return "positive"
        if value < -0.001:
            return "negative"
        return "neutral"

    def _clear_layout(self) -> None:
        clear_layout_safely(self._layout)


class FactoryCardHoverInfoPopup(CardHoverInfoPopup):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent, object_name="factoryCardHoverInfo", embedded=True)


class MachineSlotWidget(QWidget):
    clicked = Signal(int)
    production_change_requested = Signal(str)
    chain_requested = Signal(str)

    def __init__(
        self,
        slot: HallSlot,
        card: CardInstance | None,
        definition: CardDefinition | None,
        production_state: MachineProductionState | None,
        hover_parent: QWidget | None = None,
        state: GameState | None = None,
    ) -> None:
        super().__init__()
        self._state = state
        self._slot = slot
        self._card = card
        self._definition = definition
        self._production_state = production_state
        self._primary_icon: ResourceIconWidget | None = None
        self._primary_icon_signature: tuple[str, str, str] | None = None
        self._last_card_id = card.card_id if card is not None else None
        self._last_status = production_state.status if production_state is not None else None
        self._last_production_signature = self._production_signature()
        self._status_pulse_until = 0.0
        self._install_pulse_until = 0.0
        self._production_pulse_until = 0.0
        self._hover_info = FactoryCardHoverInfoPopup(hover_parent or self)
        self._hover_signature: tuple | None = None
        if hover_parent is not None and hover_parent is not self:
            self.destroyed.connect(lambda: hide_detach_delete(self._hover_info))
        self.setProperty("slotVisualState", "installed" if card is not None else "empty")
        self.setProperty("stageAccent", self._stage_accent_name())
        self.setProperty("rarity", card.rarity.value if card is not None else "")
        self.setFixedSize(FACTORY_CARD_SIZE, FACTORY_CARD_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self._refresh_primary_icon()
        self._refresh_hover_info()

    def set_data(
        self,
        slot: HallSlot,
        card: CardInstance | None,
        definition: CardDefinition | None,
        production_state: MachineProductionState | None,
        state: GameState | None = None,
    ) -> None:
        self._slot = slot
        previous_card_id = self._last_card_id
        previous_status = self._last_status
        previous_production_signature = self._last_production_signature
        self._card = card
        self._definition = definition
        self._production_state = production_state
        if state is not None:
            self._state = state
        self._last_card_id = card.card_id if card is not None else None
        self._last_status = production_state.status if production_state is not None else None
        self._last_production_signature = self._production_signature()
        self.setProperty("slotVisualState", "installed" if card is not None else "empty")
        self.setProperty("stageAccent", self._stage_accent_name())
        self.setProperty("rarity", card.rarity.value if card is not None else "")
        if previous_card_id is None and self._last_card_id is not None:
            self._install_pulse_until = _ui_feedback_time() + 0.35
        if self._last_status is not None and previous_status != self._last_status:
            self._status_pulse_until = _ui_feedback_time() + 0.4
        if previous_production_signature is not None and self._last_production_signature is not None and previous_production_signature != self._last_production_signature:
            self._production_pulse_until = _ui_feedback_time() + 0.3
        self._refresh_primary_icon()
        self._refresh_hover_info()
        self.update()

    def trigger_install_feedback(self) -> None:
        self._install_pulse_until = _ui_feedback_time() + 0.35
        self.update()

    def trigger_production_change_feedback(self) -> None:
        self._production_pulse_until = _ui_feedback_time() + 0.3
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._sync_primary_icon_geometry()
        self._position_hover_info()

    def enterEvent(self, event) -> None:  # noqa: N802
        if self._card is not None:
            self._refresh_hover_info()
            self._hover_info.show_for(self)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover_info.hide()
        super().leaveEvent(event)

    def _refresh_primary_icon(self) -> None:
        if self._card is None:
            if self._primary_icon is not None:
                hide_detach_delete(self._primary_icon)
                self._primary_icon = None
            self._primary_icon_signature = None
            return
        resource_id = self._primary_resource_id()
        icon_key = self._primary_icon_key()
        accent_key = self._primary_accent_key()
        signature = (resource_id, icon_key, accent_key)
        if self._primary_icon is not None and self._primary_icon_signature == signature:
            icon_rect = self._primary_icon_rect()
            self._primary_icon.setGeometry(
                round(icon_rect.left()),
                round(icon_rect.top()),
                round(icon_rect.width()),
                round(icon_rect.height()),
            )
            return
        if self._primary_icon is not None:
            hide_detach_delete(self._primary_icon)
            self._primary_icon = None
        self._primary_icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=60)
        self._primary_icon_signature = signature
        self._primary_icon.setParent(self)
        self._primary_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._primary_icon.show()
        icon_rect = self._primary_icon_rect()
        self._primary_icon.setGeometry(
            round(icon_rect.left()),
            round(icon_rect.top()),
            round(icon_rect.width()),
            round(icon_rect.height()),
        )

    def _active_production_id(self) -> str | None:
        if not isinstance(self._definition, MachineDefinition):
            return None
        if self._production_state is not None and self._production_state.selected_production_id is not None:
            return self._production_state.selected_production_id
        return None

    def _active_production(self):
        if not isinstance(self._definition, MachineDefinition):
            return None
        production_id = self._active_production_id()
        if production_id is None:
            return None
        return self._definition.production_option(self._active_production_id())

    def _request_production_change(self) -> None:
        if self._card is not None and isinstance(self._definition, MachineDefinition):
            self.production_change_requested.emit(self._card.card_id)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._hover_info.hide()
        if self._card is not None and self._active_production() is not None and self._chain_hit_rect().contains(event.position()):
            self.chain_requested.emit(self._primary_resource_id())
        elif self._production_change_available() and self._production_hit_rect().contains(event.position()):
            self._request_production_change()
        else:
            self.clicked.emit(self._slot.index)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            if self._card is None:
                self._draw_empty_slot(painter, rect)
            else:
                self._sync_primary_icon_geometry()
                self._draw_machine_card(painter, rect)
        finally:
            painter.end()

    def _draw_empty_slot(self, painter: QPainter, rect: QRectF) -> None:
        base = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base.setColorAt(0.0, QColor(20, 39, 48, 235))
        base.setColorAt(0.55, QColor(12, 23, 29, 220))
        base.setColorAt(1.0, QColor(9, 16, 21, 232))
        painter.setPen(QPen(QColor(98, 190, 232, 118), 1.2))
        painter.setBrush(base)
        painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), 7, 7)
        painter.setPen(QPen(QColor(98, 190, 232, 96), 1.1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(98, 190, 232, 14))
        pad = max(8, round(rect.width() * 0.09))
        painter.drawRoundedRect(rect.adjusted(pad, pad, -pad, -pad), 7, 7)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(98, 190, 232, 32))
        plus_shell = QRectF(rect.center().x() - 23, rect.top() + rect.height() * 0.2, 46, 46)
        painter.drawRoundedRect(plus_shell, 12, 12)
        painter.setBrush(QColor(216, 240, 106, 20))
        painter.drawEllipse(QRectF(plus_shell.center().x() - 13, plus_shell.center().y() - 13, 26, 26))
        painter.setPen(QColor(Theme.ENERGY))
        painter.setFont(QFont("Segoe UI", 25, QFont.Weight.Black))
        painter.drawText(plus_shell, Qt.AlignmentFlag.AlignCenter, "+")
        painter.setPen(QColor(Theme.TEXT))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(QRectF(rect.left(), rect.center().y() + 18, rect.width(), 18), Qt.AlignmentFlag.AlignCenter, "BUILD SLOT")
        painter.setPen(QColor(Theme.MUTED))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        painter.drawText(QRectF(rect.left() + 8, rect.center().y() + 33, rect.width() - 16, 16), Qt.AlignmentFlag.AlignCenter, "Install machine")

    def _draw_machine_card(self, painter: QPainter, rect: QRectF) -> None:
        assert self._card is not None
        accent = self._stage_accent_color()
        rarity_accent = self._rarity_accent_color()
        base = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base.setColorAt(0.0, QColor(27, 45, 54, 252))
        base.setColorAt(0.48, QColor(16, 27, 34, 250))
        base.setColorAt(1.0, QColor(8, 14, 19, 252))
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 170), 1.35))
        painter.setBrush(base)
        painter.drawRoundedRect(rect, 10, 10)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 8, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        header_rect = QRectF(rect.left() + 4, rect.top() + 4, rect.width() - 8, 36)
        header_gradient = QLinearGradient(header_rect.topLeft(), header_rect.bottomLeft())
        header_gradient.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 34))
        header_gradient.setColorAt(1.0, QColor(255, 255, 255, 10))
        painter.setBrush(header_gradient)
        painter.drawRoundedRect(header_rect, 8, 8)
        icon_stage = QRectF(rect.left() + 13, rect.top() + 45, rect.width() - 26, max(35, rect.height() * 0.34))
        stage_gradient = QLinearGradient(icon_stage.topLeft(), icon_stage.bottomRight())
        stage_gradient.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 30))
        stage_gradient.setColorAt(0.7, QColor(255, 255, 255, 7))
        stage_gradient.setColorAt(1.0, QColor(0, 0, 0, 20))
        painter.setBrush(stage_gradient)
        painter.drawRoundedRect(icon_stage, 9, 9)
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 52), 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(icon_stage.adjusted(3, 3, -3, -3), 7, 7)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 12))
        painter.drawRoundedRect(rect.adjusted(6, 43, -6, -8), 8, 8)
        painter.setBrush(rarity_accent)
        painter.drawRoundedRect(QRectF(rect.left() + 9, rect.top() + 6, rect.width() - 18, 3), 2, 2)
        painter.setPen(QColor(Theme.TEXT))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        name = self._definition.name if self._definition is not None else self._card.definition_id
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 12, rect.width() - 38, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name.upper())

        painter.setPen(QColor(Theme.MUTED))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        meta = self._card.rarity.value.upper()
        if hasattr(self._definition, "mk_level"):
            meta = f"MK {self._definition.mk_level} · {meta}"
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 27, rect.width() - 20, 11), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta)

        self._draw_chain_info(painter)
        self._draw_primary_area(painter, rect)
        self._draw_runtime_indicator(painter, rect)
        self._draw_feedback_pulse(painter, rect)

    def _draw_chain_info(self, painter: QPainter) -> None:
        info_rect = self._chain_hit_rect()
        painter.setPen(QPen(QColor(Theme.BORDER), 0.9))
        painter.setBrush(QColor(168, 182, 255, 18))
        painter.drawEllipse(info_rect)
        painter.setPen(QColor(Theme.RESOURCE))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(info_rect, Qt.AlignmentFlag.AlignCenter, "i")

    def _draw_primary_area(self, painter: QPainter, rect: QRectF) -> None:
        primary = self._production_hit_rect()
        label_rect = self._primary_label_rect()
        value_rect = self._bottom_stats_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 13))
        output_zone = QRectF(primary.left() + 2, max(primary.top() + primary.height() * 0.58, label_rect.top() - 4), primary.width() - 4, value_rect.bottom() - max(primary.top() + primary.height() * 0.58, label_rect.top() - 4) + 4)
        painter.drawRoundedRect(output_zone, 7, 7)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 0.7))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(output_zone.adjusted(1, 1, -1, -1), 6, 6)
        painter.setPen(QColor(Theme.RESOURCE))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Black))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._primary_label())

        painter.setPen(QColor(Theme.TEXT))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._primary_value())
        secondary = self._secondary_runtime_value()
        if secondary:
            painter.setPen(QColor(Theme.MUTED))
            painter.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            painter.drawText(value_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"PWR {secondary}")

    def _card_details(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return (
                    f"{self._definition.machine_type.value} | MK {self._definition.mk_level}\n"
                    f"Bonus +{self._card.output_bonus_percent:.1f}%\n"
                    "No production selected"
                )
            return (
                f"{self._definition.machine_type.value} | MK {self._definition.mk_level}\n"
                f"Bonus +{self._card.output_bonus_percent:.1f}%\n"
                f"Output {production.output_amount_for(self._definition) * self._card.output_multiplier:.1f} | "
                f"Power {production.power_draw_for(self._definition) * self._card.power_multiplier:.1f}"
            )
        if isinstance(self._definition, EnergyDefinition):
            fuel_text = self._energy_fuel_text()
            return (
                f"{self._definition.energy_type.value} | MK {self._definition.mk_level}\n"
                f"Generation {self._definition.base_power_output:.0f} MW\n"
                f"{fuel_text}"
            )
        if isinstance(self._definition, RecipeDefinition):
            inputs = effective_recipe_inputs(self._card, dict(self._definition.input_resources))
            outputs = effective_recipe_outputs(self._card, dict(self._definition.output_resources))
            return (
                f"recipe | ticks {self._definition.duration_ticks}\n"
                f"Bonus +{self._card.output_bonus_percent:.1f}%\n"
                f"{_format_io_summary(inputs, outputs)}"
            )
        return f"Bonus +{self._card.output_bonus_percent:.1f}%"

    def _refresh_hover_info(self) -> None:
        if self._card is None:
            self._hover_info.hide()
            self._hover_signature = None
            return
        title = self._definition.name if self._definition is not None else self._card.definition_id
        sections = self._hover_sections()
        signature = (
            title,
            tuple(label for label, _ in sections),
            self._primary_resource_id(),
            self._primary_icon_key(),
            self._primary_accent_key(),
        )
        if self._hover_signature != signature or self._hover_info.details_signature != signature:
            icon = ResourceIconWidget(
                self._primary_resource_id(),
                self._primary_icon_key(),
                self._primary_accent_key(),
                size=34,
            )
            self._hover_info.set_details(title, icon, sections, signature)
            self._hover_signature = signature
            self._position_hover_info()
        else:
            self._hover_info.update_values(sections)
        self.setToolTip("")

    def _hover_sections(self) -> list[tuple[str, str]]:
        if self._card is None:
            return []
        sections = [
            ("Rarity", self._card.rarity.value.title()),
            ("Bonus", f"+{self._card.output_bonus_percent:.1f}%"),
        ]
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            machine_sections = [
                ("Machine Family", self._definition.machine_type.value.title()),
                ("MK", str(self._definition.mk_level)),
            ]
            if production is None:
                machine_sections.extend(
                    [
                        ("Current Production", "Not selected"),
                        ("Current Status", self._status_text()),
                    ]
                )
            else:
                machine_sections.extend(
                    [
                        ("Base Output", f"{production.output_amount_for(self._definition):.1f}"),
                        ("Effective Output", f"{production.output_amount_for(self._definition) * self._card.output_multiplier:.1f}"),
                        ("Power Demand", f"{production.power_draw_for(self._definition) * self._card.power_multiplier:.1f} MW"),
                        ("Current Production", production.name),
                        ("Current Status", self._status_text()),
                    ]
                )
            sections.extend(machine_sections)
        elif isinstance(self._definition, EnergyDefinition):
            energy_sections = [
                ("Machine Family", self._definition.energy_type.value.title()),
                ("MK", str(self._definition.mk_level)),
                ("Power Generation", f"{self._definition.base_power_output * self._card.output_multiplier:.1f} MW"),
                ("Current Production", "Power"),
                ("Current Status", self._status_text()),
            ]
            if self._definition.requires_fuel and self._definition.fuel_resource_id is not None:
                energy_sections.extend(
                    [
                        ("Fuel", self._definition.fuel_resource_id.replace("_", " ").title()),
                        ("Consumption", f"{self._definition.fuel_consumption_per_minute:g}/min"),
                    ]
                )
            sections.extend(energy_sections)
        elif isinstance(self._definition, RecipeDefinition):
            sections.extend([("Machine Family", "Recipe"), ("Recipe", self._card_details())])
        return sections

    def _position_hover_info(self) -> None:
        if self._hover_info.isVisible():
            self._hover_info.show_for(self)

    def _primary_resource_id(self) -> str:
        production = self._active_production()
        if production is not None:
            return production.output_resource
        if isinstance(self._definition, RecipeDefinition) and self._definition.output_resources:
            return next(iter(self._definition.output_resources))
        if isinstance(self._definition, EnergyDefinition):
            return "power"
        return "factory_card"

    def _primary_icon_key(self) -> str:
        production = self._active_production()
        if production is not None and production.icon_key:
            return production.icon_key
        return resource_icon_key(self._primary_resource_id())

    def _primary_accent_key(self) -> str:
        production = self._active_production()
        if production is not None and production.accent_key:
            return production.accent_key
        if isinstance(self._definition, EnergyDefinition):
            return "battery"
        return resource_accent_key(self._primary_resource_id())

    def _primary_label(self) -> str:
        production = self._active_production()
        if production is not None:
            return production.name.upper()
        if isinstance(self._definition, MachineDefinition):
            if self._definition.machine_type.value == "extractor":
                return "NO RESOURCE SELECTED"
            return "NO RECIPE SELECTED"
        if isinstance(self._definition, EnergyDefinition):
            return "POWER"
        if isinstance(self._definition, RecipeDefinition) and self._definition.output_resources:
            return next(iter(self._definition.output_resources)).replace("_", " ").upper()
        return "CARD"

    def _primary_value(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return "Select"
            cycles_per_minute = 60.0 / max(0.001, production.cycle_seconds_for(self._definition))
            output_per_minute = production.output_amount_for(self._definition) * self._card.output_multiplier * cycles_per_minute
            return f"+{output_per_minute:.0f}/min"
        if isinstance(self._definition, EnergyDefinition):
            return f"+{self._definition.base_power_output * self._card.output_multiplier:.0f} MW"
        return ""

    def _energy_has_fuel(self) -> bool:
        if not isinstance(self._definition, EnergyDefinition) or not self._definition.requires_fuel:
            return True
        if self._state is None or self._definition.fuel_resource_id is None:
            return True
        return self._state.ensure_resource(self._definition.fuel_resource_id).amount > 0

    def _energy_fuel_text(self) -> str:
        if not isinstance(self._definition, EnergyDefinition) or not self._definition.requires_fuel:
            return "No fuel required"
        fuel = self._definition.fuel_resource_id.replace("_", " ").title() if self._definition.fuel_resource_id else "Fuel"
        return f"Fuel {fuel} | {self._definition.fuel_consumption_per_minute:g}/min"

    def _secondary_runtime_value(self) -> str:
        if isinstance(self._definition, MachineDefinition):
            production = self._active_production()
            if production is None:
                return ""
            power = production.power_draw_for(self._definition) * self._card.power_multiplier
            return f"{power:.0f} MW"
        return ""

    def _production_change_available(self) -> bool:
        return isinstance(self._definition, MachineDefinition) and len(self._definition.available_production_options) > 1

    def _production_signature(self) -> str | None:
        production = self._active_production()
        if production is None:
            return None
        return f"{production.production_id}:{production.output_resource}:{production.icon_key}:{production.accent_key}"

    def _primary_icon_rect(self) -> QRectF:
        primary = self._production_hit_rect()
        label_top = self._primary_label_rect().top()
        available = max(12, label_top - primary.top() - 6)
        min_size = 50 if self.width() >= FACTORY_CARD_SIZE else 14
        size = max(min_size, min(58, round(self.width() * 0.42), round(available)))
        return QRectF(primary.center().x() - size / 2, primary.top() + 4, size, size)

    def _sync_primary_icon_geometry(self) -> None:
        if self._primary_icon is None:
            return
        icon_rect = self._primary_icon_rect()
        self._primary_icon.setFixedSize(round(icon_rect.width()), round(icon_rect.height()))
        self._primary_icon.setGeometry(
            round(icon_rect.left()),
            round(icon_rect.top()),
            round(icon_rect.width()),
            round(icon_rect.height()),
        )

    def _primary_label_rect(self) -> QRectF:
        primary = self._production_hit_rect()
        stats_top = self._bottom_stats_rect().top()
        if isinstance(self._definition, MachineDefinition) and self._active_production() is None:
            label_height = 38
        else:
            label_height = 14 if self.width() < 112 else 20
        return QRectF(primary.left() + 4, stats_top - label_height - 2, primary.width() - 8, label_height)

    def _bottom_stats_rect(self) -> QRectF:
        top = self.height() - (29 if self.height() < 112 else 35)
        return QRectF(8, top, self.width() - 16, 13)

    def _status_rect(self) -> QRectF:
        top = self.height() - (16 if self.height() < 112 else 20)
        return QRectF(8, top, self.width() - 16, 11)

    def _progress_rect(self) -> QRectF:
        return QRectF(8, self.height() - 6, self.width() - 16, 3)

    def _production_hit_rect(self) -> QRectF:
        top = 30 if self.height() < 112 else 39
        return QRectF(8, top, self.width() - 16, max(54, self.height() - top - 38))

    def _chain_hit_rect(self) -> QRectF:
        return QRectF(self.width() - 23, 10, 15, 15)

    def _status_text(self) -> str:
        if isinstance(self._definition, EnergyDefinition):
            return "Online" if self._energy_has_fuel() else "No Fuel"
        if self._production_state is None:
            return "Idle"
        if self._production_state.is_unconfigured:
            if isinstance(self._definition, MachineDefinition) and self._definition.machine_type.value == "extractor":
                return "No Resource"
            return "No Recipe"
        if self._production_state.is_storage_full:
            return "Storage Full"
        if self._production_state.is_no_power:
            return "No Power"
        if self._production_state.is_missing_input:
            return "Missing Input"
        if self._production_state.status == "running":
            return "Running"
        return "Idle"

    def _status_color(self) -> QColor:
        if self._production_state is not None:
            if self._production_state.is_storage_full or self._production_state.is_no_power:
                return QColor(Theme.BAD)
            if self._production_state.is_missing_input:
                return QColor(Theme.WARN)
            if self._production_state.status == "running":
                return QColor(Theme.GOOD)
        if isinstance(self._definition, EnergyDefinition):
            return QColor(Theme.GOOD if self._energy_has_fuel() else Theme.WARN)
        return QColor(Theme.MUTED)

    def _feedback_intensity(self) -> float:
        remaining = max(self._status_pulse_until, self._install_pulse_until, self._production_pulse_until) - _ui_feedback_time()
        if remaining <= 0:
            return 0.0
        return min(1.0, remaining / 0.4)

    def _draw_feedback_pulse(self, painter: QPainter, rect: QRectF) -> None:
        intensity = self._feedback_intensity()
        if intensity <= 0:
            return
        accent = self._stage_accent_color()
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), round(90 * intensity)), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

    def _stage_accent_color(self) -> QColor:
        return _stage_accent_for_definition(self._definition)

    def _stage_accent_name(self) -> str:
        if isinstance(self._definition, EnergyDefinition):
            return "energy"
        if isinstance(self._definition, MachineDefinition):
            return self._definition.machine_type.value
        return "recipe"

    def _rarity_accent_color(self) -> QColor:
        return _rarity_accent_for_card(self._card)

    def _draw_runtime_indicator(self, painter: QPainter, rect: QRectF) -> None:
        status = self._status_text()
        status_color = self._status_color()
        footer = QRectF(rect.left() + 5, self._status_rect().top() - 4, rect.width() - 10, rect.bottom() - self._status_rect().top())
        painter.setPen(Qt.PenStyle.NoPen)
        footer_gradient = QLinearGradient(footer.topLeft(), footer.bottomLeft())
        footer_gradient.setColorAt(0.0, QColor(0, 0, 0, 28))
        footer_gradient.setColorAt(1.0, QColor(0, 0, 0, 76))
        painter.setBrush(footer_gradient)
        painter.drawRoundedRect(footer, 6, 6)
        dot = QRectF(self._status_rect().left(), self._status_rect().center().y() - 2.5, 5, 5)
        painter.setBrush(status_color)
        painter.drawEllipse(dot)
        painter.setPen(status_color)
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        text_rect = self._status_rect().adjusted(9, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, status.upper())

        if isinstance(self._definition, EnergyDefinition):
            bar = self._progress_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(Theme.ENERGY if self._energy_has_fuel() else Theme.WARN))
            painter.drawRoundedRect(bar, 3, 3)
            return
        if not isinstance(self._definition, MachineDefinition) or self._production_state is None:
            return
        bar = self._progress_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 16))
        painter.drawRoundedRect(bar, 3, 3)

        if self._production_state.is_storage_full:
            painter.setBrush(QColor(Theme.BAD))
            painter.drawRoundedRect(bar, 3, 3)
            return
        if self._production_state.is_no_power:
            painter.setBrush(QColor(Theme.BAD))
            painter.drawRoundedRect(bar, 3, 3)
            return
        if self._production_state.is_missing_input:
            painter.setBrush(QColor(Theme.WARN))
            painter.drawRoundedRect(bar, 3, 3)
            return

        production = self._active_production()
        if production is None:
            return
        progress = self._cycle_progress_ratio()
        fill = QRectF(bar.left(), bar.top(), bar.width() * progress, bar.height())
        painter.setBrush(self._stage_accent_color())
        painter.drawRoundedRect(fill, 3, 3)

    def _cycle_progress_ratio(self) -> float:
        if not isinstance(self._definition, MachineDefinition) or self._production_state is None:
            return 0.0
        production = self._active_production()
        if production is None:
            return 0.0
        return min(1.0, max(0.0, self._production_state.progress_seconds / max(0.001, production.cycle_seconds_for(self._definition))))


class FactorySlotRowWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("factorySlotRow")
        self._slot_widgets: list[QWidget] = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(FACTORY_SLOT_SPACING)

    def add_slot_widget(self, widget: QWidget) -> None:
        self._slot_widgets.append(widget)
        self._layout.addWidget(widget)
        self.setProperty("slotCount", len(self._slot_widgets))
        self._resize_slot_widgets()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._resize_slot_widgets()
        super().resizeEvent(event)

    def _resize_slot_widgets(self) -> None:
        if not self._slot_widgets:
            return
        available = max(0, self.width() - FACTORY_SLOT_SPACING * (len(self._slot_widgets) - 1))
        size = available // len(self._slot_widgets) if available else FACTORY_CARD_SIZE
        size = max(FACTORY_CARD_MIN_SIZE, min(FACTORY_CARD_MAX_SIZE, size))
        for widget in self._slot_widgets:
            widget.setFixedSize(size, size)
        self.setMinimumHeight(size)
        self.setMaximumHeight(size)


class FactoryCardSelectionTile(QFrame):
    selected = Signal(str)
    hovered = Signal(str)
    unhovered = Signal()

    def __init__(self, stack: CardStack, definition: CardDefinition | None) -> None:
        super().__init__()
        card = stack.first_card
        self._card_id = card.card_id
        self.setObjectName("factoryCardSelectionTile")
        self.setProperty("cardId", card.card_id)
        self.setProperty("definitionId", card.definition_id)
        self.setProperty("rarity", card.rarity.value)
        self.setProperty("quantity", stack.quantity)
        self.setProperty("stageAccent", _stage_name_for_definition(definition).lower())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(152, 152)
        self.setMaximumSize(176, 176)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(5)

        raw_name = definition.name if definition is not None else card.definition_id
        name = SmartCardTitleLabel(raw_name.upper())
        name.setObjectName("factoryCardSelectionTileName")
        name.setWordWrap(True)
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(name)

        rarity = QLabel(card.rarity.value.upper())
        rarity.setObjectName("factoryCardSelectionTileRarity")
        rarity.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(rarity)

        rarity_line = QFrame()
        rarity_line.setObjectName("factoryCardSelectionRarityLine")
        rarity_line.setProperty("rarity", card.rarity.value)
        rarity_line.setFixedHeight(2)
        rarity_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(rarity_line)

        accent = _stage_accent_for_definition(definition)
        icon = ResourceIconWidget(
            self._icon_resource_id(definition),
            self._icon_key(definition),
            self._accent_key(definition),
            size=58,
        )
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        layout.addLayout(icon_row)
        layout.addSpacing(3)

        function = QLabel(_stage_name_for_definition(definition).upper())
        function.setObjectName("factoryCardSelectionTileFunction")
        function.setAlignment(Qt.AlignmentFlag.AlignCenter)
        function.setProperty("accentColor", accent.name())
        function.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(function)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bonus = QLabel(f"+{card.output_bonus_percent:.1f}%")
        bonus.setObjectName("factoryCardSelectionTileBonus")
        bonus.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        count = QLabel(f"x{stack.quantity}")
        count.setObjectName("factoryCardSelectionTileCount")
        count.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        bottom.addWidget(bonus)
        bottom.addStretch(1)
        bottom.addWidget(count)
        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._card_id)
            return
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit(self._card_id)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.unhovered.emit()
        super().leaveEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.selected.emit(self._card_id)
            return
        super().keyPressEvent(event)

    def _icon_resource_id(self, definition: CardDefinition | None) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.output_resource
        if isinstance(definition, EnergyDefinition):
            return "power"
        return "factory_card"

    def _icon_key(self, definition: CardDefinition | None) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.icon_key or resource_icon_key(production.output_resource)
        if isinstance(definition, EnergyDefinition):
            return "battery"
        return resource_icon_key(self._icon_resource_id(definition))

    def _accent_key(self, definition: CardDefinition | None) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.accent_key or resource_accent_key(production.output_resource)
        if isinstance(definition, EnergyDefinition):
            return "battery"
        return resource_accent_key(self._icon_resource_id(definition))


class ProductionSelectionTile(QFrame):
    selected = Signal(str, str)

    def __init__(self, production, current_id: str, category: str) -> None:
        super().__init__()
        self._production = production
        self.setObjectName("productionSelectionTile")
        self.setProperty("productionId", production.production_id)
        self.setProperty("resourceId", production.output_resource)
        self.setProperty("category", category)
        self.setProperty("current", production.production_id == current_id)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(154, 128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 12)
        layout.setSpacing(6)

        top = QHBoxLayout()
        icon = ResourceIconWidget(
            production.output_resource,
            production.icon_key or resource_icon_key(production.output_resource),
            production.accent_key or resource_accent_key(production.output_resource),
            size=64,
        )
        top.addWidget(icon)
        text = QVBoxLayout()
        name = QLabel(production.name.upper())
        name.setObjectName("productionTileName")
        name.setWordWrap(True)
        text.addWidget(name)
        category_label = QLabel(category)
        category_label.setObjectName("productionTileCategory")
        text.addWidget(category_label)
        top.addLayout(text, 1)
        layout.addLayout(top)

        if production.production_id == current_id:
            current = QLabel("CURRENT")
            current.setObjectName("productionTileCurrent")
            layout.addWidget(current)
        else:
            spacer = QLabel("")
            spacer.setObjectName("productionTileCurrent")
            layout.addWidget(spacer)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._production.production_id, self._production.output_resource)


class ProductionGuideTile(QFrame):
    selected = Signal(str)

    def __init__(self, resource_id: str, name: str, stage: MachineType, category: str, icon_key: str, accent_key: str) -> None:
        super().__init__()
        self._resource_id = resource_id
        self.setObjectName("productionGuideTile")
        self.setProperty("resourceId", resource_id)
        self.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        self.setProperty("category", category)
        self.setProperty("stageAccent", stage.value)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(164, 156)
        self.setMaximumSize(210, 182)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 12)
        layout.setSpacing(6)

        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=68)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        layout.addLayout(icon_row)

        name_label = SmartCardTitleLabel(name.upper())
        name_label.setObjectName("productionGuideTileName")
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(name_label)

        stage_label = QLabel(PRODUCTION_STAGE_LABELS[stage])
        stage_label.setObjectName("productionGuideTileStage")
        stage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stage_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(stage_label)

        category_label = QLabel(category)
        category_label.setObjectName("productionGuideTileCategory")
        category_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        category_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(category_label)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._resource_id)
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.selected.emit(self._resource_id)
            return
        super().keyPressEvent(event)


class ResizingGridHost(QWidget):
    resized = Signal()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.resized.emit()


class ChainFlowConnector(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("chainFlowConnector")
        self.setFixedWidth(38)
        self.setMinimumHeight(150)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(112, 138, 132, 150)
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        center_y = self.height() // 2
        painter.drawLine(4, center_y, self.width() - 10, center_y)
        arrow = QPolygonF([
            QPointF(self.width() - 12, center_y - 5),
            QPointF(self.width() - 12, center_y + 5),
            QPointF(self.width() - 4, center_y),
        ])
        painter.setBrush(color)
        painter.drawPolygon(arrow)


class ChainResourceBox(QFrame):
    def __init__(
        self,
        resource_id: str,
        name: str,
        stage: MachineType,
        machine_family: str,
        required_amount: float,
        output_amount: float,
        icon_key: str,
        accent_key: str,
    ) -> None:
        super().__init__()
        self.setObjectName("chainResourceBox")
        self.setProperty("resourceId", resource_id)
        self.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        self.setProperty("machineFamily", machine_family)
        self.setProperty("stageAccent", stage.value)
        self.setProperty("target", required_amount <= 0 and output_amount > 0)
        self.setFixedWidth(172)
        self.setMinimumHeight(126)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 10, 11, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=48)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        header.addWidget(icon)
        text = QVBoxLayout()
        name_label = SmartCardTitleLabel(name)
        name_label.setObjectName("chainResourceName")
        name_label.setWordWrap(True)
        name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(name_label)
        family = QLabel(machine_family)
        family.setObjectName("chainMachineFamily")
        family.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(family)
        header.addLayout(text, 1)
        layout.addLayout(header)

        amounts = []
        if required_amount > 0:
            amounts.append(f"Input {required_amount:g}")
        if output_amount > 0:
            amounts.append(f"Output {output_amount:g}")
        amount_label = QLabel(" · ".join(amounts) if amounts else "Reference")
        amount_label.setObjectName("chainResourceAmount")
        amount_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(amount_label)


class FactoryView(QWidget):
    def __init__(self, state: GameState, command_bus: CommandBus, definitions: dict[str, CardDefinition]) -> None:
        super().__init__()
        self._state = state
        self._command_bus = command_bus
        self._definitions = definitions
        self._simulation = SimulationEngine(definitions)
        self._last_update = perf_counter()
        self._simulation_advanced_callback: Callable[[], None] | None = None
        self._selected_hall_id = next(iter(state.halls))
        self._selected_card_id: str | None = None
        self._drawer_mode: str | None = None
        self._drawer_slot_index: int | None = None
        self._card_search_text = ""
        self._card_type_filter_text = "All"
        self._card_mk_filter_text = "All"
        self._card_rarity_filter_text = "All"
        self._card_detail_label: QLabel | None = None
        self._install_button: QPushButton | None = None
        self._card_selection_list: QListWidget | None = None
        self._card_selection_grid: QGridLayout | None = None
        self._production_drawer_card_id: str | None = None
        self._production_search_text = ""
        self._production_category_filter_text = "All"
        self._selected_production_id: str | None = None
        self._production_selection_list: QListWidget | None = None
        self._production_selection_grid: QGridLayout | None = None
        self._production_selection_grid_host: QWidget | None = None
        self._production_select_button: QPushButton | None = None
        self._guide_search_text = ""
        self._guide_stage_filter_text = "All"
        self._guide_category_filter_text = "All"
        self._guide_grid: QGridLayout | None = None
        self._guide_grid_host: QWidget | None = None
        self._guide_view_build_count = 0
        self._guide_grid_rebuild_count = 0
        self._guide_grid_resize_count = 0
        self._guide_tile_create_count = 0
        self._chain_resource_id: str | None = None
        self._chain_back_mode: str = "hall"
        self._recent_install_slot_indexes: set[int] = set()
        self._recent_production_change_card_ids: set[str] = set()
        self._slot_widgets: dict[int, MachineSlotWidget] = {}
        self._kpi_strip: KpiStripWidget | None = None
        self._resource_summary: HallResourceSummaryWidget | None = None
        self._selection_hover_card_id: str | None = None
        self._selection_hover_popup: CardHoverInfoPopup | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._hall_tree = QTreeWidget()
        self._hall_tree.setObjectName("hallTree")
        self._hall_tree.setHeaderHidden(True)
        self._hall_tree.setFixedWidth(238)
        self._hall_tree.itemSelectionChanged.connect(self._on_hall_selection_changed)

        self._build_hall_button = QPushButton()
        self._build_hall_button.setObjectName("buildHallButton")
        self._build_hall_button.clicked.connect(self._purchase_hall)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        sidebar_label = QLabel("FACTORY")
        sidebar_label.setObjectName("factoryNavTitle")
        sidebar_subtitle = QLabel("OPERATIONS / HALLS")
        sidebar_subtitle.setObjectName("factoryNavSubtitle")
        sidebar_layout.addWidget(sidebar_label)
        sidebar_layout.addWidget(sidebar_subtitle)
        sidebar_layout.addWidget(self._hall_tree, 1)
        sidebar_layout.addWidget(self._build_hall_button)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)

        layout.addWidget(sidebar)
        layout.addWidget(self._content, 1)

        self._refresh_hall_tree()
        self._refresh_content()

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._advance_simulation)
        self._timer.start()

    def _refresh_hall_tree(self) -> None:
        self._hall_tree.blockSignals(True)
        self._hall_tree.clear()
        root = QTreeWidgetItem(["Factory"])
        root.setExpanded(True)
        self._hall_tree.addTopLevelItem(root)
        for hall in self._state.halls.values():
            item = QTreeWidgetItem([self._hall_nav_label(hall)])
            item.setData(0, Qt.ItemDataRole.UserRole, hall.hall_id)
            root.addChild(item)
            if hall.hall_id == self._selected_hall_id:
                self._hall_tree.setCurrentItem(item)
        self._hall_tree.blockSignals(False)
        self._refresh_build_hall_button()

    def _hall_nav_label(self, hall: FactoryHall) -> str:
        occupied = sum(1 for index in hall.unlocked_slot_indexes() if hall.slots[index].card_id is not None)
        return f"{hall.name}   {occupied} / {hall.slot_count}"

    def _refresh_build_hall_button(self) -> None:
        cost = hall_purchase_price(len(self._state.halls))
        self._build_hall_button.setText(f"Build Hall (${cost:.0f})")
        self._build_hall_button.setEnabled(self._state.cash.amount >= cost)

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

        command_board = QFrame()
        command_board.setObjectName("factoryHallCommandBoard")
        command_layout = QVBoxLayout(command_board)
        command_layout.setContentsMargins(14, 12, 14, 12)
        command_layout.setSpacing(10)

        header_panel = QFrame()
        header_panel.setObjectName("factoryHallHeader")
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(14)
        title_shell = QFrame()
        title_shell.setObjectName("factoryHallTitleShell")
        title_shell_layout = QVBoxLayout(title_shell)
        title_shell_layout.setContentsMargins(12, 9, 12, 9)
        title_shell_layout.setSpacing(3)
        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(3)
        hall_label = QLabel("ACTIVE PRODUCTION HALL")
        hall_label.setObjectName("hallCommandLabel")
        hall_name = QLineEdit(hall.name)
        hall_name.setObjectName("hallNameEdit")
        hall_name.editingFinished.connect(lambda: self._rename_hall(hall_name.text()))
        guide_button = QPushButton("Production Guide")
        guide_button.setObjectName("productionGuideButton")
        guide_button.clicked.connect(lambda checked=False: self._open_production_guide())
        hall_name.setProperty("factoryHeader", True)
        active_lines = sum(1 for line in hall.production_lines if line.unlocked)
        occupied = sum(1 for index in hall.unlocked_slot_indexes() if hall.slots[index].card_id is not None)
        slot_count = QLabel(f"{occupied} / {hall.slot_count} slots · {active_lines} active lines")
        slot_count.setObjectName("hallSlotCount")
        title_block.addWidget(hall_label)
        title_block.addWidget(hall_name)
        title_block.addWidget(slot_count)
        title_shell_layout.addLayout(title_block)
        header.addWidget(title_shell, 1)
        header.addStretch(1)
        header.addWidget(guide_button)
        command_layout.addWidget(header_panel)
        command_divider = QFrame()
        command_divider.setObjectName("factoryCommandDivider")
        command_divider.setFixedHeight(2)
        command_layout.addWidget(command_divider)

        status_zone = QFrame()
        status_zone.setObjectName("factoryStatusZone")
        status_layout = QHBoxLayout(status_zone)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(12)
        self._kpi_strip = KpiStripWidget(self._state)
        status_layout.addWidget(self._kpi_strip)
        self._resource_summary = HallResourceSummaryWidget(self._state, self._definitions, hall)
        self._resource_summary.chain_requested.connect(self._open_chain_from_hall)
        status_layout.addWidget(self._resource_summary, 1)
        command_layout.addWidget(status_zone)
        self._content_layout.addWidget(command_board)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        lines_container = QWidget()
        lines_layout = QVBoxLayout(lines_container)
        lines_layout.setContentsMargins(0, 0, 0, 0)
        lines_layout.setSpacing(10)
        for line in hall.production_lines:
            line_panel = self._build_line_panel(line, hall)
            lines_layout.addWidget(line_panel)
        lines_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("factoryHallScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(lines_container)
        body.addWidget(scroll, 1)
        drawer = self._build_context_drawer()
        if drawer is not None:
            body.addWidget(drawer, 0)
        self._content_layout.addLayout(body, 1)

    def _detach_runtime_widget_references(self) -> None:
        self._slot_widgets = {}
        self._kpi_strip = None
        self._resource_summary = None

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)

    def _build_line_panel(self, line: ProductionLine, hall: FactoryHall) -> QFrame:
        panel = QFrame()
        panel.setObjectName("linePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        if not line.unlocked:
            line_number = self._line_number(hall, line)
            layout.setContentsMargins(10, 6, 10, 6)
            locked_panel = ClickableCapacityPanel(enabled=self._state.cash.amount >= line.unlock_cost)
            locked_panel.setObjectName("lockedLinePanel")
            locked_panel.setProperty("lineId", line.line_id)
            locked_panel.setProperty("lineNumber", line_number)
            locked_panel.setProperty("unlockCost", line.unlock_cost)
            locked_panel.setMinimumHeight(42)
            locked_panel.setMaximumHeight(54)
            locked_panel.activated.connect(lambda line_id=line.line_id: self._unlock_line(line_id))
            locked_layout = QHBoxLayout(locked_panel)
            locked_layout.setContentsMargins(10, 8, 10, 8)
            locked_layout.setSpacing(10)

            name = QLabel(line.name.upper())
            name.setObjectName("lockedLineName")
            name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            badge = QLabel("LOCKED")
            badge.setObjectName("lineLockedBadge")
            badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            detail = QLabel(f"Expansion Bay · ${line.unlock_cost:.0f}")
            detail.setObjectName("lockedLineDetail")
            detail.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            action = QLabel("Unlock Line")
            action.setObjectName("lockedLineAction")
            action.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

            locked_layout.addWidget(name)
            locked_layout.addWidget(badge)
            locked_layout.addWidget(detail)
            locked_layout.addStretch(1)
            locked_layout.addWidget(action)
            layout.addWidget(locked_panel)
            return panel

        header_row = QHBoxLayout()
        line_number = self._line_number(hall, line)
        line_badge = QLabel(f"LINE {line_number:02d}")
        line_badge.setObjectName("lineNumberBadge")
        header = QLabel(line.name.upper())
        header.setObjectName("lineHeader")
        header.setProperty("locked", not line.unlocked)
        header_rule = QFrame()
        header_rule.setObjectName("lineHeaderRule")
        header_rule.setFrameShape(QFrame.Shape.HLine)
        header_row.addWidget(line_badge)
        header_row.addWidget(header)
        if not line.unlocked:
            badge = QLabel("LOCKED")
            badge.setObjectName("lineLockedBadge")
            header_row.addWidget(badge)
        header_row.addWidget(header_rule, 1)
        layout.addLayout(header_row)

        row = FactorySlotRowWidget()
        for slot_number in range(1, MAX_FACTORY_SLOTS_PER_LINE + 1):
            if slot_number <= len(line.slot_indexes):
                slot_index = line.slot_indexes[slot_number - 1]
                slot = hall.slots[slot_index]
                card = self._state.cards.get(slot.card_id) if slot.card_id else None
                definition = self._definitions.get(card.definition_id) if card else None
                production_state = self._state.machine_production.get(card.card_id) if card else None
                slot_widget = MachineSlotWidget(slot, card, definition, production_state, self, state=self._state)
                slot_widget.clicked.connect(self._on_slot_clicked)
                slot_widget.production_change_requested.connect(self._open_production_drawer)
                slot_widget.chain_requested.connect(self._open_chain_from_hall)
                self._slot_widgets[slot_index] = slot_widget
                if slot_index in self._recent_install_slot_indexes:
                    slot_widget.trigger_install_feedback()
                    self._recent_install_slot_indexes.discard(slot_index)
                if card is not None and card.card_id in self._recent_production_change_card_ids:
                    slot_widget.trigger_production_change_feedback()
                    self._recent_production_change_card_ids.discard(card.card_id)
                row.add_slot_widget(slot_widget)
            else:
                row.add_slot_widget(self._build_locked_slot_panel(line, line_number, slot_number))
        layout.addWidget(row)
        return panel

    def _line_number(self, hall: FactoryHall, line: ProductionLine) -> int:
        return hall.production_lines.index(line) + 1

    def _build_locked_slot_panel(self, line: ProductionLine, line_number: int, slot_number: int) -> QFrame:
        cost = factory_slot_unlock_cost(line_number, slot_number)
        panel = ClickableCapacityPanel(enabled=self._state.cash.amount >= cost)
        panel.setObjectName("lockedSlotPanel")
        panel.setProperty("lineId", line.line_id)
        panel.setProperty("slotNumber", slot_number)
        panel.setProperty("slotIndex", None)
        panel.setProperty("slotVisualState", "locked")
        panel.setProperty("unlockCost", cost)
        panel.setFixedSize(FACTORY_CARD_SIZE, FACTORY_CARD_SIZE)
        panel.activated.connect(lambda line_id=line.line_id: self._unlock_slot(line_id))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        lock = QLabel("LOCK")
        lock.setObjectName("lockedSlotIcon")
        lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        title = QLabel(f"SLOT {slot_number}")
        title.setObjectName("lockedSlotTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        detail = QLabel(f"${cost:.0f}")
        detail.setObjectName("lockedSlotPrice")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hint = QLabel("UPGRADE BAY")
        hint.setObjectName("lockedSlotHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addStretch(1)
        layout.addWidget(lock)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(detail)
        layout.addStretch(1)
        return panel

    def _build_context_drawer(self) -> QFrame | None:
        if self._drawer_mode == "cards":
            return None
        if self._drawer_mode == "production":
            return None
        return None

    def _build_production_guide_view(self) -> QFrame:
        self._guide_view_build_count += 1
        panel = QFrame()
        panel.setObjectName("productionGuideView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("PRODUCTION GUIDE")
        title.setObjectName("sectionLabel")
        back = QPushButton("Back")
        back.setObjectName("productionGuideBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back)
        layout.addLayout(header)

        filters_panel = QFrame()
        filters_panel.setObjectName("productionGuideFilters")
        filters = QHBoxLayout()
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setSpacing(8)
        search = QLineEdit()
        search.setObjectName("productionGuideSearchInput")
        search.setPlaceholderText("Search products...")
        search.setText(self._guide_search_text)
        search.textChanged.connect(self._on_guide_search_changed)
        filters.addWidget(search, 2)

        stage_filter = QComboBox()
        stage_filter.setObjectName("productionGuideStageFilter")
        for option in ["All", *[PRODUCTION_STAGE_LABELS[stage] for stage in PRODUCTION_STAGE_ORDER]]:
            stage_filter.addItem(option)
        stage_filter.setCurrentText(self._guide_stage_filter_text)
        stage_filter.currentTextChanged.connect(self._on_guide_stage_filter_changed)
        filters.addWidget(stage_filter)

        category_filter = QComboBox()
        category_filter.setObjectName("productionGuideCategoryFilter")
        for option in self._guide_category_options():
            category_filter.addItem(option)
        category_filter.setCurrentText(self._guide_category_filter_text if self._guide_category_filter_text in self._guide_category_options() else "All")
        category_filter.currentTextChanged.connect(self._on_guide_category_filter_changed)
        filters.addWidget(category_filter)
        filters_panel.setLayout(filters)
        layout.addWidget(filters_panel)

        scroll = QScrollArea()
        scroll.setObjectName("productionGuideScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        grid_host = ResizingGridHost()
        grid_host.setObjectName("productionGuideGridHost")
        grid_host.resized.connect(self._on_guide_grid_host_resized)
        self._guide_grid_host = grid_host
        self._guide_grid = QGridLayout(grid_host)
        self._guide_grid.setContentsMargins(0, 0, 0, 0)
        self._guide_grid.setSpacing(10)
        grid_host.setProperty("guideGridColumns", self._guide_grid_columns())
        self._populate_guide_grid()
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)
        return panel

    def _build_chain_inspector_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("chainInspectorView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        resource_id = self._chain_resource_id or ""
        option = self._guide_option_index().get(resource_id)
        header = QHBoxLayout()
        back = QPushButton("Back")
        back.setObjectName("chainInspectorBackButton")
        back.clicked.connect(lambda checked=False: self._back_from_chain_inspector())
        title = QLabel(f"CHAIN INSPECTOR · {self._resource_display_name(resource_id).upper()}")
        title.setObjectName("sectionLabel")
        header.addWidget(back)
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        if option is None:
            empty = QLabel("No production chain data available for this product.")
            empty.setObjectName("chainInspectorEmpty")
            layout.addWidget(empty)
            layout.addStretch(1)
            return panel

        chain = self._build_chain(resource_id)
        scroll = QScrollArea()
        scroll.setObjectName("chainInspectorScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        host.setObjectName("chainInspectorStageHost")
        host_layout = QHBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(10)
        for index, stage in enumerate(PRODUCTION_STAGE_ORDER):
            nodes = chain.get(stage, [])
            if not nodes:
                continue
            stage_panel = self._build_chain_stage_panel(stage, nodes)
            host_layout.addWidget(stage_panel)
            if index < len(PRODUCTION_STAGE_ORDER) - 1 and any(chain.get(later) for later in PRODUCTION_STAGE_ORDER[index + 1:]):
                host_layout.addWidget(ChainFlowConnector())
        host_layout.addStretch(1)
        scroll.setWidget(host)
        layout.addWidget(scroll, 1)
        return panel

    def _build_chain_stage_panel(self, stage: MachineType, nodes: list[dict[str, object]]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("chainStagePanel")
        panel.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        panel.setMinimumWidth(390)
        panel.setMaximumWidth(430)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        title = QLabel(PRODUCTION_STAGE_LABELS[stage].upper())
        title.setObjectName("chainStageTitle")
        title.setProperty("stageAccent", stage.value)
        header_rule = QFrame()
        header_rule.setObjectName("chainStageRule")
        header_rule.setProperty("stageAccent", stage.value)
        header = QHBoxLayout()
        header.addWidget(title)
        header.addWidget(header_rule, 1)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        columns = 2
        for index, node in enumerate(nodes):
            grid.addWidget(
                ChainResourceBox(
                    str(node["resource_id"]),
                    str(node["name"]),
                    stage,
                    str(node["machine_family"]),
                    float(node["required_amount"]),
                    float(node["output_amount"]),
                    str(node["icon_key"]),
                    str(node["accent_key"]),
                ),
                index // columns,
                index % columns,
            )
        grid.setColumnStretch(columns, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        return panel

    def _build_production_selection_view(self) -> QFrame:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            self._reset_drawer_state()
            empty = QFrame()
            empty.setObjectName("productionSelectionView")
            return empty

        panel = QFrame()
        panel.setObjectName("productionSelectionView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("SELECT RESOURCE" if definition.machine_type.value == "extractor" else "SELECT RECIPE")
        title.setObjectName("sectionLabel")
        current = self._active_production_option(card, definition)
        current_label = QLabel(f"Current: {current.name if current is not None else 'Not selected'}")
        current_label.setObjectName("productionCurrentLabel")
        current_label.setProperty("iconKey", current.icon_key if current is not None else "")
        current_label.setProperty("accentKey", current.accent_key if current is not None else "")
        back = QPushButton("Back")
        back.setObjectName("productionSelectionBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        title_row.addWidget(title)
        title_row.addWidget(current_label)
        title_row.addStretch(1)
        title_row.addWidget(back)
        layout.addLayout(title_row)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        search = QLineEdit()
        search.setObjectName("productionSearchInput")
        search.setPlaceholderText("Search production...")
        search.setText(self._production_search_text)
        search.textChanged.connect(self._on_production_search_changed)
        filters.addWidget(search, 2)

        category_filter = QComboBox()
        category_filter.setObjectName("productionCategoryFilter")
        category_filter.blockSignals(True)
        category_filter.addItems(self._production_category_filter_options())
        if self._production_category_filter_text in self._production_category_filter_options():
            category_filter.setCurrentText(self._production_category_filter_text)
        category_filter.blockSignals(False)
        category_filter.currentTextChanged.connect(self._on_production_category_filter_changed)
        filters.addWidget(category_filter)
        layout.addLayout(filters)

        grid_host = QWidget()
        grid_host.setObjectName("productionSelectionGridHost")
        grid_host.resizeEvent = lambda event, host=grid_host: self._on_production_grid_host_resized(host, event)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._production_selection_grid_host = grid_host
        self._production_selection_grid = grid
        self._populate_production_selection_grid()

        scroll = QScrollArea()
        scroll.setObjectName("productionSelectionScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)
        return panel

    def _build_factory_card_selection_view(self, hall: FactoryHall) -> QFrame:
        panel = QFrame()
        panel.setObjectName("factoryCardSelectionView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("CARD SELECTION")
        title.setObjectName("sectionLabel")
        slot_label = QLabel(f"Target Slot {self._drawer_slot_index + 1 if self._drawer_slot_index is not None else '-'}")
        slot_label.setObjectName("cardSelectionTargetLabel")
        back = QPushButton("Back")
        back.setObjectName("cardSelectionBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        header.addWidget(title)
        header.addWidget(slot_label)
        header.addStretch(1)
        header.addWidget(back)
        layout.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(8)

        search = QLineEdit()
        search.setObjectName("cardSearchInput")
        search.setPlaceholderText("Search cards...")
        search.setText(self._card_search_text)
        search.textChanged.connect(self._on_card_search_changed)
        filters.addWidget(search, 2)

        type_filter = QComboBox()
        type_filter.setObjectName("cardSelectionTypeFilter")
        type_filter.blockSignals(True)
        type_filter.addItems(self._card_filter_options())
        if self._card_type_filter_text in self._card_filter_options():
            type_filter.setCurrentText(self._card_type_filter_text)
        type_filter.blockSignals(False)
        type_filter.currentTextChanged.connect(self._on_card_type_filter_changed)
        filters.addWidget(type_filter)

        mk_filter = QComboBox()
        mk_filter.setObjectName("cardSelectionMkFilter")
        mk_filter.blockSignals(True)
        mk_filter.addItems(self._card_mk_filter_options())
        if self._card_mk_filter_text in self._card_mk_filter_options():
            mk_filter.setCurrentText(self._card_mk_filter_text)
        mk_filter.blockSignals(False)
        mk_filter.currentTextChanged.connect(self._on_card_mk_filter_changed)
        filters.addWidget(mk_filter)

        rarity_filter = QComboBox()
        rarity_filter.setObjectName("cardSelectionRarityFilter")
        rarity_filter.blockSignals(True)
        rarity_filter.addItems(self._card_rarity_filter_options())
        if self._card_rarity_filter_text in self._card_rarity_filter_options():
            rarity_filter.setCurrentText(self._card_rarity_filter_text)
        rarity_filter.blockSignals(False)
        rarity_filter.currentTextChanged.connect(self._on_card_rarity_filter_changed)
        filters.addWidget(rarity_filter)
        layout.addLayout(filters)

        grid_host = QWidget()
        grid_host.setObjectName("factoryCardSelectionGridHost")
        grid_host.resizeEvent = lambda event, host=grid_host: self._on_card_selection_grid_host_resized(host, event)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._card_selection_grid = grid
        self._populate_card_selection_grid()

        scroll = QScrollArea()
        scroll.setObjectName("factoryCardSelectionScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)
        return panel

    def _build_production_selection_drawer(self) -> QFrame:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            self._reset_drawer_state()
            empty = QFrame()
            empty.setObjectName("productionSelectionDrawer")
            return empty

        panel = QFrame()
        panel.setObjectName("productionSelectionDrawer")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("SELECT RESOURCE" if definition.machine_type.value == "extractor" else "SELECT RECIPE")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)

        current = self._active_production_option(card, definition)
        current_label = QLabel(f"Current: {current.name if current is not None else 'Not selected'}")
        current_label.setObjectName("productionCurrentLabel")
        current_label.setProperty("iconKey", current.icon_key if current is not None else "")
        current_label.setProperty("accentKey", current.accent_key if current is not None else "")
        layout.addWidget(current_label)

        search = QLineEdit()
        search.setObjectName("productionSearchInput")
        search.setPlaceholderText("Search production...")
        search.setText(self._production_search_text)
        search.textChanged.connect(self._on_production_search_changed)
        layout.addWidget(search)

        list_widget = QListWidget()
        list_widget.setObjectName("productionSelectionList")
        list_widget.currentItemChanged.connect(self._on_production_selection_changed)
        list_widget.itemDoubleClicked.connect(lambda item: self._apply_selected_production())
        self._production_selection_list = list_widget
        self._populate_production_selection_list()
        layout.addWidget(list_widget, 1)

        actions = QHBoxLayout()
        select = QPushButton("Select")
        select.setObjectName("selectProductionButton")
        select.clicked.connect(self._apply_selected_production)
        self._production_select_button = select
        close = QPushButton("Close")
        close.setObjectName("closeProductionDrawerButton")
        close.clicked.connect(lambda checked=False: self._close_drawer())
        actions.addWidget(select)
        actions.addWidget(close)
        layout.addLayout(actions)
        return panel

    def _card_filter_options(self) -> list[str]:
        types = {"All", "Energy", "Extractor", "Processor", "Fabricator", "Assembler"}
        for stack in build_placeable_inventory_stacks(self._state, self._definitions):
            definition = self._definitions.get(stack.first_card.definition_id)
            if isinstance(definition, MachineDefinition):
                types.add(definition.machine_type.value.title())
            elif isinstance(definition, EnergyDefinition):
                types.add("Energy")
        return ["All", *sorted(types - {"All"})]

    def _card_mk_filter_options(self) -> list[str]:
        levels = {"All"}
        for stack in build_placeable_inventory_stacks(self._state, self._definitions):
            definition = self._definitions.get(stack.first_card.definition_id)
            mk_level = getattr(definition, "mk_level", None)
            if mk_level is not None:
                levels.add(f"MK {mk_level}")
        return ["All", *sorted(levels - {"All"})]

    def _card_rarity_filter_options(self) -> list[str]:
        return ["All", *[rarity.value.title() for rarity in Rarity]]

    def _filtered_placeable_stacks(self) -> tuple[CardStack, ...]:
        stacks = []
        search = self._card_search_text.strip().lower()
        for stack in build_placeable_inventory_stacks(self._state, self._definitions):
            card = stack.first_card
            definition = self._definitions.get(card.definition_id)
            if not isinstance(definition, (MachineDefinition, EnergyDefinition)):
                continue
            name = definition.name if definition is not None else card.definition_id
            card_type = "Card"
            if isinstance(definition, MachineDefinition):
                card_type = definition.machine_type.value.title()
            elif isinstance(definition, EnergyDefinition):
                card_type = "Energy"
            if self._card_type_filter_text not in ("", "All", card_type):
                continue
            mk_level = getattr(definition, "mk_level", None)
            if self._card_mk_filter_text not in ("", "All") and self._card_mk_filter_text != f"MK {mk_level}":
                continue
            if self._card_rarity_filter_text not in ("", "All", card.rarity.value.title()):
                continue
            haystack = f"{name} {card_type} {card.rarity.value}".lower()
            if search and search not in haystack:
                continue
            stacks.append(stack)
        return tuple(stacks)

    def _populate_card_selection_grid(self) -> None:
        if self._card_selection_grid is None:
            return
        self._clear_layout(self._card_selection_grid)
        stacks = self._filtered_placeable_stacks()
        if not stacks:
            empty = QLabel("No compatible cards available")
            empty.setObjectName("factoryCardSelectionEmpty")
            self._card_selection_grid.addWidget(empty, 0, 0)
            return
        columns = self._card_selection_grid_columns()
        for index, stack in enumerate(stacks):
            tile = self._build_card_selection_tile(stack)
            self._card_selection_grid.addWidget(tile, index // columns, index % columns)
        self._card_selection_grid.setRowStretch((len(stacks) + columns - 1) // columns, 1)
        self._card_selection_grid.setColumnStretch(columns, 1)

    def _guide_option_index(self) -> dict[str, ProductionOptionDefinition]:
        indexed: dict[str, ProductionOptionDefinition] = {}
        for definition in self._definitions.values():
            if not isinstance(definition, MachineDefinition):
                continue
            for option in definition.available_production_options:
                existing = indexed.get(option.output_resource)
                if existing is None or PRODUCTION_STAGE_ORDER.index(option.stage) > PRODUCTION_STAGE_ORDER.index(existing.stage):
                    indexed[option.output_resource] = option
        return indexed

    def _guide_items(self) -> list[ProductionOptionDefinition]:
        return sorted(self._guide_option_index().values(), key=lambda option: (PRODUCTION_STAGE_ORDER.index(option.stage), option.name))

    def _guide_category_options(self) -> list[str]:
        categories = {
            resource_category(option.output_resource, option.stage.value)
            for option in self._guide_items()
        }
        return ["All", *sorted(categories)]

    def _filtered_guide_items(self) -> list[ProductionOptionDefinition]:
        search = self._guide_search_text.strip().lower()
        items = []
        for option in self._guide_items():
            stage_label = PRODUCTION_STAGE_LABELS[option.stage]
            category = resource_category(option.output_resource, option.stage.value)
            if self._guide_stage_filter_text not in ("", "All", stage_label):
                continue
            if self._guide_category_filter_text not in ("", "All", category):
                continue
            haystack = f"{option.name} {option.output_resource} {stage_label} {category}".lower()
            if search and search not in haystack:
                continue
            items.append(option)
        return items

    def _populate_guide_grid(self) -> None:
        if self._guide_grid is None:
            return
        self._guide_grid_rebuild_count += 1
        self._clear_layout(self._guide_grid)
        items = self._filtered_guide_items()
        if not items:
            empty = QLabel("No products found")
            empty.setObjectName("productionGuideEmpty")
            self._guide_grid.addWidget(empty, 0, 0)
            return
        columns = self._guide_grid_columns()
        for index, option in enumerate(items):
            category = resource_category(option.output_resource, option.stage.value)
            self._guide_tile_create_count += 1
            tile = ProductionGuideTile(
                option.output_resource,
                option.name,
                option.stage,
                category,
                option.icon_key or resource_icon_key(option.output_resource),
                option.accent_key or resource_accent_key(option.output_resource),
            )
            tile.selected.connect(self._open_chain_from_guide)
            self._guide_grid.addWidget(tile, index // columns, index % columns)
        self._guide_grid.setRowStretch((len(items) + columns - 1) // columns, 1)
        self._guide_grid.setColumnStretch(columns, 1)

    def _guide_grid_columns(self) -> int:
        width = self._guide_grid_host.width() if self._guide_grid_host is not None else self.width()
        return max(2, min(8, width // 188))

    def _on_guide_grid_host_resized(self) -> None:
        self._guide_grid_resize_count += 1
        if self._guide_grid_host is None or self._guide_grid is None:
            return
        previous = self._guide_grid_host.property("guideGridColumns")
        current = self._guide_grid_columns()
        self._guide_grid_host.setProperty("guideGridColumns", current)
        if previous != current:
            self._populate_guide_grid()

    def _resource_display_name(self, resource_id: str) -> str:
        option = self._guide_option_index().get(resource_id)
        if option is not None:
            return option.name
        return resource_id.replace("_", " ").title()

    def _build_chain(self, resource_id: str) -> dict[MachineType, list[dict[str, object]]]:
        option_index = self._guide_option_index()
        stages: dict[MachineType, dict[str, dict[str, object]]] = {stage: {} for stage in PRODUCTION_STAGE_ORDER}
        visiting: set[str] = set()

        def visit(current_resource_id: str, required_amount: float = 0.0) -> None:
            if current_resource_id in visiting:
                return
            option = option_index.get(current_resource_id)
            if option is None:
                return
            visiting.add(current_resource_id)
            for input_resource_id, amount in option.input_resources.items():
                visit(input_resource_id, amount)
            stage_nodes = stages[option.stage]
            node = stage_nodes.setdefault(
                current_resource_id,
                {
                    "resource_id": current_resource_id,
                    "name": option.name,
                    "machine_family": option.stage.value.title(),
                    "required_amount": 0.0,
                    "output_amount": option.output_amount or 0.0,
                    "icon_key": option.icon_key or resource_icon_key(current_resource_id),
                    "accent_key": option.accent_key or resource_accent_key(current_resource_id),
                },
            )
            node["required_amount"] = float(node["required_amount"]) + required_amount
            if not node["output_amount"]:
                node["output_amount"] = option.output_amount or 0.0
            visiting.remove(current_resource_id)

        visit(resource_id)
        return {
            stage: list(nodes.values())
            for stage, nodes in stages.items()
            if nodes
        }

    def _build_card_selection_tile(self, stack: CardStack) -> QFrame:
        card = stack.first_card
        definition = self._definitions.get(card.definition_id)
        tile = FactoryCardSelectionTile(stack, definition)
        tile.selected.connect(self._install_card_from_selection)
        tile.hovered.connect(lambda card_id, widget=tile: self._show_card_selection_hover(card_id, widget))
        tile.unhovered.connect(self._hide_card_selection_hover)
        return tile

    def _show_card_selection_hover(self, card_id: str, source: QWidget) -> None:
        card = self._state.cards.get(card_id)
        if card is None:
            return
        definition = self._definitions.get(card.definition_id)
        if self._selection_hover_popup is None:
            self._selection_hover_popup = CardHoverInfoPopup(self, embedded=True)
        sections = [
            ("Rarity", card.rarity.value.title()),
            ("Type", _stage_name_for_definition(definition)),
            ("MK", str(getattr(definition, "mk_level", "-"))),
            ("Bonus", f"+{card.output_bonus_percent:.1f}%"),
            ("Available", str(self._card_selection_available_count(card))),
        ]
        if isinstance(definition, MachineDefinition):
            sections.extend(
                [
                    ("Output", f"{definition.base_output_per_tick * card.output_multiplier:g}"),
                    ("Power", f"{definition.base_power_draw * card.power_multiplier:g} MW"),
                ]
            )
        elif isinstance(definition, EnergyDefinition):
            sections.append(("Generation", f"{definition.base_power_output * card.output_multiplier:g} MW"))
        title = definition.name if definition is not None else card.definition_id
        resource_id, icon_key, accent_key = self._selection_hover_icon_signature(definition)
        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=34)
        signature = (card_id, tuple(label for label, _value in sections))
        if self._selection_hover_popup.details_signature != signature:
            self._selection_hover_popup.set_details(title, icon, sections, signature)
        else:
            self._selection_hover_popup.update_values(sections)
        self._selection_hover_card_id = card_id
        self._selection_hover_popup.show_for(source)

    def _hide_card_selection_hover(self) -> None:
        self._selection_hover_card_id = None
        if self._selection_hover_popup is not None:
            self._selection_hover_popup.hide()

    def _card_selection_available_count(self, card: CardInstance) -> int:
        for stack in build_placeable_inventory_stacks(self._state, self._definitions):
            if stack.first_card.card_id == card.card_id:
                return stack.quantity
        return 1

    def _selection_hover_icon_signature(self, definition: CardDefinition | None) -> tuple[str, str, str]:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return (
                production.output_resource,
                production.icon_key or resource_icon_key(production.output_resource),
                production.accent_key or resource_accent_key(production.output_resource),
            )
        if isinstance(definition, EnergyDefinition):
            return ("power", "battery", "battery")
        return ("factory_card", resource_icon_key("factory_card"), resource_accent_key("factory_card"))

    def _card_selection_grid_columns(self) -> int:
        width = self._content.width() if self._content.width() > 0 else self.width()
        return max(2, min(8, width // 186))

    def _on_card_selection_grid_host_resized(self, host: QWidget, event) -> None:
        self._populate_card_selection_grid()
        QWidget.resizeEvent(host, event)

    def _card_tile_meta(self, card: CardInstance, definition: CardDefinition | None) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.machine_type.value.title()} · MK {definition.mk_level}"
        if isinstance(definition, EnergyDefinition):
            return f"Energy · MK {definition.mk_level}"
        return card.card_kind.value.title()

    def _populate_card_selection_list(self) -> None:
        if self._card_selection_list is None:
            return
        list_widget = self._card_selection_list
        current_card_id = self._selected_card_id
        list_widget.blockSignals(True)
        list_widget.clear()
        selected_item = None
        for stack in self._filtered_placeable_stacks():
            card = stack.first_card
            item = QListWidgetItem(self._card_stack_list_text(stack))
            item.setData(Qt.ItemDataRole.UserRole, card.card_id)
            list_widget.addItem(item)
            if card.card_id == current_card_id:
                selected_item = item
        if selected_item is not None:
            list_widget.setCurrentItem(selected_item)
        else:
            self._selected_card_id = None
        list_widget.blockSignals(False)
        if self._card_detail_label is not None:
            self._card_detail_label.setText(self._selected_card_detail())
        if self._install_button is not None:
            self._install_button.setEnabled(self._selected_card_id is not None)

    def _production_drawer_card(self) -> tuple[CardInstance | None, CardDefinition | None]:
        if self._production_drawer_card_id is None:
            return None, None
        card = self._state.cards.get(self._production_drawer_card_id)
        definition = self._definitions.get(card.definition_id) if card is not None else None
        return card, definition

    def _active_production_id(self, card: CardInstance, definition: MachineDefinition) -> str | None:
        machine_state = self._state.machine_production.get(card.card_id)
        if machine_state is not None and machine_state.selected_production_id is not None:
            return machine_state.selected_production_id
        return None

    def _active_production_option(self, card: CardInstance, definition: MachineDefinition):
        production_id = self._active_production_id(card, definition)
        if production_id is None:
            return None
        return definition.production_option(production_id)

    def _filtered_production_options(self) -> tuple:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return ()
        search = self._production_search_text.strip().lower()
        options = []
        for production in definition.available_production_options:
            haystack = f"{production.name} {production.output_resource} {' '.join(production.input_resources)}".lower()
            if search and search not in haystack:
                continue
            category = resource_category(production.output_resource, definition.machine_type.value)
            if self._production_category_filter_text not in ("", "All", category):
                continue
            options.append(production)
        return tuple(options)

    def _production_category_filter_options(self) -> list[str]:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return ["All"]
        categories = {
            resource_category(production.output_resource, definition.machine_type.value)
            for production in definition.available_production_options
        }
        preferred = (
            ["Ores / Metals", "Minerals", "Oil & Gas", "Agriculture", "Forestry"]
            if definition.machine_type.value == "extractor"
            else ["Materials", "Components", "Electronics", "Energy", "Transport", "Food & Agriculture", "Chemicals", "Medical"]
        )
        ordered = [category for category in preferred if category in categories]
        ordered.extend(sorted(categories - set(ordered)))
        return ["All", *ordered]

    def _populate_production_selection_grid(self) -> None:
        if self._production_selection_grid is None:
            return
        self._clear_layout(self._production_selection_grid)
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return
        current = self._active_production_option(card, definition)
        current_id = current.production_id if current is not None else None
        options = self._filtered_production_options()
        if not options:
            empty = QLabel("No production options found")
            empty.setObjectName("productionSelectionEmpty")
            self._production_selection_grid.addWidget(empty, 0, 0)
            return
        columns = self._production_grid_columns()
        for index, production in enumerate(options):
            category = resource_category(production.output_resource, definition.machine_type.value)
            tile = ProductionSelectionTile(production, current_id, category)
            tile.selected.connect(self._apply_production_option)
            self._production_selection_grid.addWidget(tile, index // columns, index % columns)
        self._production_selection_grid.setRowStretch((len(options) + columns - 1) // columns, 1)
        self._production_selection_grid.setColumnStretch(columns, 1)

    def _production_grid_columns(self) -> int:
        width = self._production_selection_grid_host.width() if self._production_selection_grid_host is not None else self.width()
        return max(2, min(8, width // 170))

    def _on_production_grid_host_resized(self, host: QWidget, event) -> None:
        previous = host.property("productionGridColumns")
        current = self._production_grid_columns()
        host.setProperty("productionGridColumns", current)
        if previous != current:
            self._populate_production_selection_grid()

    def _populate_production_selection_list(self) -> None:
        if self._production_selection_list is None:
            return
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return
        current = self._active_production_option(card, definition)
        current_id = current.production_id if current is not None else None
        selected_id = self._selected_production_id or current_id
        list_widget = self._production_selection_list
        list_widget.blockSignals(True)
        list_widget.clear()
        selected_item = None
        for production in self._filtered_production_options():
            prefix = "CURRENT · " if production.production_id == current_id else ""
            item = QListWidgetItem(f"{prefix}{production.name}")
            item.setData(Qt.ItemDataRole.UserRole, (production.production_id, production.output_resource))
            item.setData(Qt.ItemDataRole.UserRole + 1, production.icon_key)
            item.setData(Qt.ItemDataRole.UserRole + 2, production.accent_key)
            list_widget.addItem(item)
            if production.production_id == selected_id:
                selected_item = item
        if selected_item is not None:
            list_widget.setCurrentItem(selected_item)
        elif list_widget.count() > 0:
            list_widget.setCurrentRow(0)
        list_widget.blockSignals(False)
        current_item = list_widget.currentItem()
        data = current_item.data(Qt.ItemDataRole.UserRole) if current_item is not None else None
        self._selected_production_id = data[0] if data is not None else None
        if self._production_select_button is not None:
            self._production_select_button.setEnabled(self._selected_production_id is not None)

    def _rename_hall(self, name: str) -> None:
        self._command_bus.dispatch(RenameHall(self._selected_hall_id, name))
        self._refresh_hall_tree()

    def _purchase_hall(self) -> None:
        before = set(self._state.halls)
        self._command_bus.dispatch(PurchaseHall())
        created = [hall_id for hall_id in self._state.halls if hall_id not in before]
        if created:
            self._selected_hall_id = created[0]
        self._refresh_hall_tree()
        self._refresh_content()

    def _on_hall_selection_changed(self) -> None:
        item = self._hall_tree.currentItem()
        if item is None:
            return
        hall_id = item.data(0, Qt.ItemDataRole.UserRole)
        if hall_id is None:
            return
        self._selected_hall_id = hall_id
        self._refresh_content()

    def _advance_simulation(self) -> None:
        now = perf_counter()
        elapsed = now - self._last_update
        self._last_update = now
        self._simulation.advance_time(self._state, elapsed)
        self._refresh_runtime_widgets()
        if self._simulation_advanced_callback is not None:
            self._simulation_advanced_callback()

    def set_simulation_advanced_callback(self, callback: Callable[[], None]) -> None:
        self._simulation_advanced_callback = callback

    def pause_simulation(self) -> None:
        self._timer.stop()

    def resume_simulation(self) -> None:
        self._last_update = perf_counter()
        self._timer.start()

    def is_simulation_paused(self) -> bool:
        return not self._timer.isActive()

    def refresh_view(self) -> None:
        self._refresh_hall_tree()
        self._refresh_content()

    def _refresh_runtime_widgets(self) -> None:
        hall = self._state.halls[self._selected_hall_id]
        for slot_index, widget in list(self._slot_widgets.items()):
            if not is_qt_object_valid(widget):
                self._slot_widgets.pop(slot_index, None)
                continue
            slot = hall.slots[slot_index]
            card = self._state.cards.get(slot.card_id) if slot.card_id else None
            definition = self._definitions.get(card.definition_id) if card else None
            production_state = self._state.machine_production.get(card.card_id) if card else None
            widget.set_data(slot, card, definition, production_state, self._state)
        if self._kpi_strip is not None and is_qt_object_valid(self._kpi_strip):
            self._kpi_strip.refresh()
        elif self._kpi_strip is not None:
            self._kpi_strip = None
        if self._resource_summary is not None and is_qt_object_valid(self._resource_summary):
            self._resource_summary.refresh()
        elif self._resource_summary is not None:
            self._resource_summary = None
        self._refresh_unlock_panels()
        self._refresh_build_hall_button()

    def _refresh_unlock_panels(self) -> None:
        for panel in [*self.findChildren(QFrame, "lockedSlotPanel"), *self.findChildren(QFrame, "lockedLinePanel")]:
            if not isinstance(panel, ClickableCapacityPanel):
                continue
            cost = float(panel.property("unlockCost") or 0.0)
            enabled = self._state.cash.amount >= cost
            panel.setProperty("unlockEnabled", enabled)
            panel.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
            panel.style().unpolish(panel)
            panel.style().polish(panel)

    def _on_inventory_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        self._selected_card_id = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        if self._card_detail_label is not None:
            self._card_detail_label.setText(self._selected_card_detail())
        if self._install_button is not None:
            self._install_button.setEnabled(self._selected_card_id is not None)

    def _on_slot_clicked(self, slot_index: int) -> None:
        hall = self._state.halls[self._selected_hall_id]
        slot = hall.slots[slot_index]
        if slot.card_id is not None:
            self._reset_drawer_state()
            self._command_bus.dispatch(RemoveCardFromHall(self._selected_hall_id, slot_index))
            self._refresh_hall_tree()
        else:
            self._drawer_mode = "cards"
            self._drawer_slot_index = slot_index
            self._selected_card_id = None
        self._refresh_content()

    def _open_production_drawer(self, card_id: str) -> None:
        self._drawer_mode = "production"
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._production_drawer_card_id = card_id
        self._production_search_text = ""
        self._production_category_filter_text = "All"
        self._selected_production_id = None
        self._refresh_content()

    def _open_production_guide(self) -> None:
        self._drawer_mode = "guide"
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._chain_resource_id = None
        self._chain_back_mode = "hall"
        self._refresh_content()

    def _open_chain_from_guide(self, resource_id: str) -> None:
        self._drawer_mode = "chain"
        self._chain_resource_id = resource_id
        self._chain_back_mode = "guide"
        self._refresh_content()

    def _open_chain_from_hall(self, resource_id: str) -> None:
        self._drawer_mode = "chain"
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._chain_resource_id = resource_id
        self._chain_back_mode = "hall"
        self._refresh_content()

    def _back_from_chain_inspector(self) -> None:
        if self._chain_back_mode == "guide":
            self._drawer_mode = "guide"
            self._chain_resource_id = None
            self._refresh_content()
            return
        self._close_drawer()

    def _install_selected_card(self) -> None:
        if self._selected_card_id is None or self._drawer_slot_index is None:
            return
        self._install_card_from_selection(self._selected_card_id)

    def _install_card_from_selection(self, card_id: str) -> None:
        if self._drawer_slot_index is None:
            return
        installed_slot_index = self._drawer_slot_index
        self._command_bus.dispatch(
            InstallCardInHall(self._selected_hall_id, installed_slot_index, card_id)
        )
        self._recent_install_slot_indexes.add(installed_slot_index)
        self._reset_drawer_state()
        self._refresh_hall_tree()
        self._refresh_content()

    def _close_drawer(self, refresh: bool = True) -> None:
        self._reset_drawer_state()
        if refresh:
            self._refresh_content()

    def _reset_drawer_state(self) -> None:
        self._drawer_mode = None
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._card_selection_list = None
        self._card_selection_grid = None
        self._card_detail_label = None
        self._install_button = None
        self._production_drawer_card_id = None
        self._production_selection_grid = None
        self._production_selection_grid_host = None
        self._selected_production_id = None
        self._production_selection_list = None
        self._production_select_button = None
        self._guide_grid = None
        self._guide_grid_host = None
        self._chain_resource_id = None
        self._chain_back_mode = "hall"

    def _on_card_search_changed(self, text: str) -> None:
        self._card_search_text = text
        self._populate_card_selection_grid()

    def _on_card_type_filter_changed(self, text: str) -> None:
        self._card_type_filter_text = text
        self._populate_card_selection_grid()

    def _on_card_mk_filter_changed(self, text: str) -> None:
        self._card_mk_filter_text = text
        self._populate_card_selection_grid()

    def _on_card_rarity_filter_changed(self, text: str) -> None:
        self._card_rarity_filter_text = text
        self._populate_card_selection_grid()

    def _on_production_search_changed(self, text: str) -> None:
        self._production_search_text = text
        self._populate_production_selection_grid()

    def _on_production_category_filter_changed(self, text: str) -> None:
        self._production_category_filter_text = text
        self._populate_production_selection_grid()

    def _on_guide_search_changed(self, text: str) -> None:
        self._guide_search_text = text
        self._populate_guide_grid()

    def _on_guide_stage_filter_changed(self, text: str) -> None:
        self._guide_stage_filter_text = text
        self._populate_guide_grid()

    def _on_guide_category_filter_changed(self, text: str) -> None:
        self._guide_category_filter_text = text
        self._populate_guide_grid()

    def _on_production_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        data = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        self._selected_production_id = data[0] if data is not None else None
        if self._production_select_button is not None:
            self._production_select_button.setEnabled(data is not None)

    def _apply_selected_production(self) -> None:
        if self._production_drawer_card_id is None or self._production_selection_list is None:
            return
        item = self._production_selection_list.currentItem()
        if item is None:
            return
        production_id, target_resource_id = item.data(Qt.ItemDataRole.UserRole)
        self._apply_production_option(production_id, target_resource_id)

    def _apply_production_option(self, production_id: str, target_resource_id: str) -> None:
        if self._production_drawer_card_id is None:
            return
        card_id = self._production_drawer_card_id
        self._command_bus.dispatch(SelectMachineProduction(card_id, production_id, target_resource_id))
        self._recent_production_change_card_ids.add(card_id)
        self._reset_drawer_state()
        self._refresh_content()

    def _unlock_line(self, line_id: str) -> None:
        self._command_bus.dispatch(UnlockProductionLine(self._selected_hall_id, line_id))
        self._refresh_hall_tree()
        self._refresh_content()

    def _unlock_slot(self, line_id: str) -> None:
        self._command_bus.dispatch(UnlockProductionSlot(self._selected_hall_id, line_id))
        self._refresh_hall_tree()
        self._refresh_content()

    def _installed_card_ids(self) -> set[str]:
        return self._state.installed_card_ids()

    def _card_list_text(self, card: CardInstance) -> str:
        definition = self._definitions.get(card.definition_id)
        name = definition.name if definition is not None else card.definition_id
        return f"{name}  |  {card.rarity.value.title()}  |  +{card.output_bonus_percent:.1f}%"

    def _card_stack_list_text(self, stack: CardStack) -> str:
        suffix = f"  ×{stack.quantity}" if stack.quantity > 1 else ""
        return f"{self._card_list_text(stack.first_card)}{suffix}"

    def _selected_card_detail(self) -> str:
        if self._selected_card_id is None:
            return "No card selected"
        card = self._state.cards[self._selected_card_id]
        definition = self._definitions.get(card.definition_id)
        if isinstance(definition, MachineDefinition):
            production = definition.production_option()
            return (
                f"{definition.name}\n\n"
                f"Type: {definition.machine_type.value.title()}\n"
                f"MK: {definition.mk_level}\n"
                f"Rarity: {card.rarity.value.title()}\n"
                f"Bonus: +{card.output_bonus_percent:.1f}%\n"
                f"Base Output: {production.output_amount_for(definition) * card.output_multiplier:.1f}\n"
                f"Power Demand: {production.power_draw_for(definition) * card.power_multiplier:.1f}\n"
                f"{_format_io_summary(production.input_resources, production.output_resource)}"
            )
        if isinstance(definition, EnergyDefinition):
            return (
                f"{definition.name}\n\n"
                f"Type: {definition.energy_type.value.title()}\n"
                f"MK: {definition.mk_level}\n"
                f"Rarity: {card.rarity.value.title()}\n"
                f"Bonus: +{card.output_bonus_percent:.1f}%\n"
                f"Power Output: {definition.base_power_output:.0f}\n"
                f"Fuel: none"
            )
        return self._card_list_text(card)
