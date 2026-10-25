from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from time import monotonic, perf_counter
from typing import Mapping

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QProgressBar, QScrollArea, QGridLayout, QSizePolicy, QTreeWidget, QVBoxLayout, QWidget
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.cards import CardInstance, CardStack, CardStackKey
from production_zero.core.commands import CommandBus, InstallCardInHall, PurchaseProductionUnit, RemoveCardFromHall, RenameHall, SelectMachineProduction, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.analytics import ResourceFlow, calculate_resource_flows
from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.enums import MachineType, Rarity
from production_zero.core.inventory import CardInventoryRow, build_placeable_inventory_stacks
from production_zero.core.economy import hall_purchase_price
from production_zero.core.infrastructure_prices import production_facility_price,unit_line_price,unit_slot_price
from production_zero.core.production_guide import GuideRecipeEntry, ProductionGuideRecipeIndex
from production_zero.core.progression import (
    initialize_production_progress,
    is_production_unlocked,
    production_option_for_id,
    production_options_for_machine,
    production_progress_state,
    progression_resources,
    unlock_requirement_lines,
)
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, ProductionLine
from production_zero.ui.card_hover import CardHoverInfoPopup, card_hover_icon
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame
from production_zero.ui.machine_art import machine_art_family_for_machine_type
from production_zero.ui.resource_icons import ResourceIconWidget, card_resource_icon_signature, resource_category, resource_icon_key, resource_accent_key
from production_zero.ui.secondary_views import ResourceBrowser, SecondaryViewHeader, StageFilterBar, UsedInNavigationButton, secondary_action_button, style_secondary, RecipeInputButton, browser_category, retain_grid_tiles
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.resource_tiles import RESOURCE_TILE_WIDTH, ResourceSelectionGridHost, ResourceSelectionTile, configure_resource_selection_grid_host, configure_resource_selection_scroll
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.theme import Theme
from production_zero.ui.resource_prices import base_price_text
from production_zero.ui.widget_lifecycle import clear_layout_safely, hide_detach_delete
from production_zero.ui.zoom_pan_view import ZoomPanGraphicsView
from production_zero.ui.unlock_tree_view import UnlockTreeView


FACTORY_CARD_SIZE = 132
FACTORY_CARD_MIN_SIZE = 96
FACTORY_CARD_MAX_SIZE = 168
FACTORY_SLOT_SPACING = 6
PRIMARY_MACHINE_TYPES = frozenset({MachineType.EXTRACTOR, MachineType.DRILLING, MachineType.AGRICULTURE})


@dataclass(frozen=True, slots=True)
class ProductionBoardConfig:
    board_kind: str = "factory"
    title: str = "FACTORY"
    unit_label: str = "Hall"
    unit_plural: str = "HALLS"
    unit_id_prefix: str = "hall"
    track_label: str = "LINE"
    purchase_label: str = "Build Hall"
    production_guide_enabled: bool = True
    resource_drawer_enabled: bool = True
    allowed_machine_types: frozenset[MachineType] = frozenset({MachineType.PROCESSOR, MachineType.FABRICATOR, MachineType.ASSEMBLER})
    allow_energy: bool = False
    max_lines: int = 5
    max_slots_per_line: int = 10
    start_unlocked_lines: int = 1
    start_slots_per_line: int = 3


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
    MachineType.DRILLING,
    MachineType.AGRICULTURE,
    MachineType.PROCESSOR,
    MachineType.FABRICATOR,
    MachineType.ASSEMBLER,
)
CHAIN_STAGE_ORDER = (
    MachineType.EXTRACTOR,
    MachineType.PROCESSOR,
    MachineType.FABRICATOR,
    MachineType.ASSEMBLER,
)
PRODUCTION_STAGE_LABELS = {
    MachineType.EXTRACTOR: "Primary Production",
    MachineType.DRILLING: "Primary Production",
    MachineType.AGRICULTURE: "Primary Production",
    MachineType.PROCESSOR: "Processing",
    MachineType.FABRICATOR: "Manufacturing",
    MachineType.ASSEMBLER: "Assembly",
}


def _player_progression_lines(progression_state: str, requirement_lines: tuple[str, ...]) -> tuple[str, ...]:
    """Remove XP/internal guide language while preserving actual unlock gates."""
    if progression_state == "unlocked":
        return ("UNLOCKED",)
    result: list[str] = []
    for line in requirement_lines:
        upper = line.upper()
        if upper.startswith("REQUIRES COMPANY LEVEL "):
            result.append(upper.replace("REQUIRES COMPANY LEVEL ", "LEVEL ", 1))
            continue
        if upper.startswith("REQUIRES UNLOCKED INPUT: "):
            result.append(upper.replace("REQUIRES UNLOCKED INPUT: ", "REQUIRES ", 1))
            continue
        match = re.match(r"PRODUCE [\d.]+ MORE (.+?) \(([\d.]+) / ([\d.]+)\)$", upper)
        if match:
            result.append(f"{match.group(1)} {match.group(2)} / {match.group(3)}")
    return tuple(result) or ("LOCKED",)


def _production_stage_group(stage: MachineType) -> MachineType:
    return MachineType.EXTRACTOR if stage in PRIMARY_MACHINE_TYPES else stage


def _machine_type_label(machine_type: MachineType) -> str:
    return {
        MachineType.DRILLING: "Drilling Rig",
        MachineType.AGRICULTURE: "Harvester",
    }.get(machine_type, machine_type.value.title())


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


def _hidden_child_label(parent: QWidget, object_name: str, text: str) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    label.hide()
    return label


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
        return definition.name
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
        self.setFixedHeight(102)
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
        from production_zero.ui.resource_tiles import ElidedResourceLabel
        self._name = ElidedResourceLabel(flow.resource_id.replace("_", " ").upper())
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
        amount_row.addStretch(1)
        text_layout.addLayout(amount_row)
        text_layout.addWidget(self._rate)
        self._price = ElidedResourceLabel("")
        self._price.setObjectName("resourceBaseSellPrice")
        self._price.setFixedHeight(18)
        text_layout.addWidget(self._price)

        self._progress = QProgressBar()
        self._progress.setObjectName("hallResourceStorageProgress")
        self._progress.setRange(0, 1000)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        text_layout.addWidget(self._progress)
        layout.addLayout(text_layout, 1)

        self.update_flow(flow)

    def update_flow(self, flow: ResourceFlow) -> None:
        from production_zero.ui.resource_prices import base_price_text, price_tooltip
        from production_zero.core.market import market_price_for
        self._price.setText(base_price_text(flow.resource_id,self._state))
        tooltip = price_tooltip(self._state,flow.resource_id)
        self._price.set_tooltip_text(tooltip)
        self.setToolTip(flow.resource_id.replace("_", " ").upper()+"\n"+tooltip)
        self._price.setAccessibleName(tooltip)
        self.setProperty("baseSellPrice",market_price_for(self._state.market,flow.resource_id))
        stock = self._state.ensure_resource(flow.resource_id)
        previous_amount = self.property("targetAmount")
        previous_progress = self.property("targetStorageProgress")
        global_fill = self._state.used_storage / self._state.storage_capacity if self._state.storage_capacity > 0 else 0.0
        target_progress = round(global_fill * 1000)
        if previous_amount is not None and round(float(previous_amount)) != round(stock.amount):
            self._amount_transition_started = _ui_feedback_time()
            self.setProperty("previousAmount", previous_amount)
            self.setProperty("amountTransitionMs", self._amount_transition_ms)
        if previous_progress is not None and int(previous_progress) != target_progress:
            self.setProperty("previousStorageProgress", previous_progress)
            self.setProperty("storageTransitionMs", self._amount_transition_ms)
        self.setProperty("targetAmount", stock.amount)
        self.setProperty("targetStorageProgress", target_progress)
        self.setProperty("producedPerMinute", flow.produced_per_minute)
        self.setProperty("consumedPerMinute", flow.consumed_per_minute)
        self.setProperty("netPerMinute", flow.net_per_minute)
        self.setProperty("netState", self._net_state(flow.net_per_minute))
        self.setProperty("storageState", self._storage_state(global_fill))
        self._amount.setText(f"{stock.amount:.0f} STORED")
        self._rate.setToolTip("Company-wide configured flow. Assumes full power and available inputs/storage; excludes Freight. Stock is shown separately.")
        self._rate.setText(
            f"PROD +{flow.produced_per_minute:.1f} · USE -{flow.consumed_per_minute:.1f} · NET {flow.net_per_minute:+.1f}/min"
        )
        self._rate.setProperty("netState", self._net_state(flow.net_per_minute))
        self._progress.setValue(target_progress)
        self._progress.setProperty("storageState", self._storage_state(global_fill))
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
        flows = self._resource_flows()
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

    def _resource_flows(self) -> dict[str, ResourceFlow]:
        return calculate_resource_flows(self._state, self._definitions)

    def _net_state(self, value: float) -> str:
        if value > 0.001:
            return "positive"
        if value < -0.001:
            return "negative"
        return "neutral"

    def _clear_layout(self) -> None:
        clear_layout_safely(self._layout)


class FactoryCardSelectionTile(InventoryCardFrame):
    selected = Signal(str)
    hovered = Signal(str)
    unhovered = Signal()

    def __init__(self, stack: CardStack, definition: CardDefinition | None) -> None:
        card = stack.first_card
        if definition is None:
            raise ValueError(f"Missing card definition for selection tile: {card.definition_id}")
        row = CardInventoryRow(card=card, definition=definition, quantity=stack.quantity, status="Available")
        stage_name = _stage_name_for_definition(definition)
        family = (
            definition.energy_type.value
            if isinstance(definition, EnergyDefinition)
            else machine_art_family_for_machine_type(definition.machine_type)
        )
        super().__init__(
            row,
            title=definition.name.upper() if isinstance(definition, EnergyDefinition) else stage_name.upper(),
            family=family,
            meta=self._card_meta(row, definition),
            detail=self._card_detail(definition),
            selected=False,
            disabled=False,
            status_text="AVAILABLE",
        )
        self._card_id = card.card_id
        self.setObjectName("factoryCardSelectionTile")
        self.setProperty("cardId", card.card_id)
        self.setProperty("definitionId", card.definition_id)
        self.setProperty("rarity", card.rarity.value)
        self.setProperty("quantity", stack.quantity)
        self.setProperty("stageAccent", stage_name.lower())
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
        self._add_compatibility_children(row, definition)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._card_id)
            return
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit(self._card_id)
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.unhovered.emit()
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.selected.emit(self._card_id)
            return
        super().keyPressEvent(event)

    def _add_compatibility_children(self, row: CardInventoryRow, definition: CardDefinition) -> None:
        _hidden_child_label(self, "factoryCardSelectionTileName", definition.name.upper())
        _hidden_child_label(self, "factoryCardSelectionTileRarity", row.rarity.value.upper())
        _hidden_child_label(self, "factoryCardSelectionTileFunction", _stage_name_for_definition(definition).upper())
        _hidden_child_label(self, "factoryCardSelectionTileBonus", f"+{row.card.output_bonus_percent:.1f}%")
        _hidden_child_label(self, "factoryCardSelectionTileCount", f"x{row.quantity}")
        rarity_line = QFrame(self)
        rarity_line.setObjectName("factoryCardSelectionRarityLine")
        rarity_line.setProperty("rarity", row.rarity.value)
        rarity_line.hide()
        icon = ResourceIconWidget(
            self._icon_resource_id(definition),
            self._icon_key(definition),
            self._accent_key(definition),
            size=1,
        )
        icon.setParent(self)
        icon.setObjectName("resourceIcon")
        icon.hide()

    def _card_meta(self, row: CardInventoryRow, definition: CardDefinition) -> str:
        return row.rarity.value.upper()

    def _card_detail(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.base_output_per_tick:g} OUTPUT / {definition.base_power_draw:g} MW"
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output:g} MW GENERATION"
        return "SELECT CARD"

    def _icon_resource_id(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.output_resource
        if isinstance(definition, EnergyDefinition):
            return card_resource_icon_signature(definition, definition.definition_id)[2]
        return "factory_card"

    def _icon_key(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.icon_key or resource_icon_key(production.output_resource)
        if isinstance(definition, EnergyDefinition):
            return card_resource_icon_signature(definition, definition.definition_id)[0]
        return resource_icon_key(self._icon_resource_id(definition))

    def _accent_key(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            return production.accent_key or resource_accent_key(production.output_resource)
        if isinstance(definition, EnergyDefinition):
            return card_resource_icon_signature(definition, definition.definition_id)[1]
        return resource_accent_key(self._icon_resource_id(definition))


class ProductionSelectionTile(ResourceSelectionTile):
    selected = Signal(str, str)

    def __init__(self, production, current_id: str, category: str, *, locked_reason: str = "") -> None:
        self._production = production
        is_current = production.production_id == current_id
        super().__init__(
            resource_id=production.output_resource,
            title=production.name,
            subtitle=category,
            detail=base_price_text(production.output_resource,compact=True),
            status=("CURRENT" if is_current else locked_reason),
            icon_key=production.icon_key or resource_icon_key(production.output_resource),
            accent_key=production.accent_key or resource_accent_key(production.output_resource),
            object_name="productionSelectionTile",
            title_object_name="productionTileName",
            subtitle_object_name="productionTileCategory",
            detail_object_name="productionTileStage",
            status_object_name="productionTileCurrent",
        )
        self.setProperty("productionId", production.production_id)
        self.findChild(QLabel,"productionTileName")._forward_tooltip_to_parent = False
        self.findChild(QLabel,"productionTileStage").set_tooltip_text(base_price_text(production.output_resource))
        self.setToolTip("\n".join((production.name,category,base_price_text(production.output_resource))))
        self.setProperty("category", category)
        self.setProperty("stageAccent", production.stage.value)
        self.setProperty("current", is_current)
        self.setProperty("locked", bool(locked_reason))
        self.setEnabled(not locked_reason)
        if locked_reason:
            self.setCursor(Qt.CursorShape.ForbiddenCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._production.production_id, self._production.output_resource)


class ProductionGuideTile(ResourceSelectionTile):
    selected = Signal(str)

    def __init__(
        self,
        resource_id: str,
        name: str,
        stage: MachineType,
        category: str,
        icon_key: str,
        accent_key: str,
        progression_state: str = "unlocked",
        requirement_lines: tuple[str, ...] = (),
    ) -> None:
        self._resource_id = resource_id
        super().__init__(
            resource_id=resource_id,
            title=name,
            subtitle=PRODUCTION_STAGE_LABELS[stage],
            detail=base_price_text(resource_id,compact=True),
            status=self._unlock_text(progression_state, requirement_lines),
            icon_key=icon_key,
            accent_key=accent_key,
            object_name="productionGuideTile",
            title_object_name="productionGuideTileName",
            subtitle_object_name="productionGuideTileStage",
            detail_object_name="productionGuideTileCategory",
            status_object_name="productionGuideUnlock",
        )
        self.setProperty("resourceId", resource_id)
        self.findChild(QLabel,"productionGuideTileName")._forward_tooltip_to_parent = False
        self.findChild(QLabel,"productionGuideTileCategory").set_tooltip_text(base_price_text(resource_id))
        self.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        self.setProperty("category", category)
        self.setProperty("stageAccent", stage.value)
        self.setProperty("progressionState", progression_state)
        self.setToolTip("\n".join((name,category,base_price_text(resource_id),*requirement_lines)))
        if unlock := self.findChild(QLabel, "productionGuideUnlock"):
            unlock.setProperty("progressionState", progression_state)

    def _unlock_text(self, progression_state: str, requirement_lines: tuple[str, ...]) -> str:
        return requirement_lines[0] if requirement_lines else "LOCKED"

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


class GuideRecipeGridHost(QWidget):
    def __init__(
        self,
        rows: tuple[QWidget, ...],
        *,
        minimum_column_width: int = 220,
    ) -> None:
        super().__init__()
        self.setObjectName("guideRecipeSectionContent")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._rows = rows
        self._minimum_column_width = minimum_column_width
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(14)
        self._grid.setVerticalSpacing(14)
        self._apply_columns(self._target_columns())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_columns(self._target_columns(event.size().width()))

    def _target_columns(self, width: int | None = None) -> int:
        width = self.width() if width is None else width
        spacing = self._grid.horizontalSpacing()
        return max(1, (width + spacing) // (self._minimum_column_width + spacing))

    def _apply_columns(self, columns: int) -> None:
        columns = max(1, columns)
        if columns == self._columns:
            return
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if widget in self._rows:
                widget.hide()
            else:
                widget.hide()
                widget.deleteLater()
        for column in range(self._grid.columnCount() + 3):
            self._grid.setColumnMinimumWidth(column, 0)
            self._grid.setColumnStretch(column, 0)
        for row_index in range(self._grid.rowCount()):
            self._grid.setRowStretch(row_index, 0)
        if not self._rows:
            empty = EmptyStatePanel("NO DOWNSTREAM PRODUCTS", "This product has no direct downstream recipes.")
            empty.findChild(QWidget, "emptyStateIcon").hide()
            empty.setObjectName("guideRecipeEmpty")
            self._grid.addWidget(empty, 0, 0)
        else:
            for index, row in enumerate(self._rows):
                row.setFixedWidth(self._minimum_column_width)
                self._grid.addWidget(row, index // columns, index % columns, Qt.AlignmentFlag.AlignLeft)
                row.show()
            for column in range(min(columns, len(self._rows))):
                self._grid.setColumnMinimumWidth(column, self._minimum_column_width)
            self._grid.setColumnStretch(min(columns, len(self._rows)), 1)
        self._grid.setRowStretch((len(self._rows) + columns - 1) // columns, 1)
        self.setProperty("guideRecipeColumns", columns)
        self._columns = columns


class ChainFlowConnector(QFrame):
    def __init__(self, source_group: QWidget, destination_group: QWidget) -> None:
        super().__init__()
        self._source_group = source_group
        self._destination_group = destination_group
        self.setObjectName("chainFlowConnector")
        self.setFixedWidth(30)
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def _node_group_bounds(self, stage_group: QWidget):
        bounds = None
        for node in stage_group.findChildren(QFrame, "chainResourceBox"):
            node_bounds = node.rect().translated(node.mapTo(self, node.rect().topLeft()))
            bounds = node_bounds if bounds is None else bounds.united(node_bounds)
        return bounds

    def connection_points(self) -> tuple[QPointF, QPointF, QPointF, QPointF]:
        source_bounds = self._node_group_bounds(self._source_group)
        destination_bounds = self._node_group_bounds(self._destination_group)
        source_y = float(source_bounds.center().y()) if source_bounds is not None else self.height() / 2
        destination_y = float(destination_bounds.center().y()) if destination_bounds is not None else self.height() / 2
        elbow_x = self.width() / 2
        return (
            QPointF(0, source_y),
            QPointF(elbow_x, source_y),
            QPointF(elbow_x, destination_y),
            QPointF(self.width() - 4, destination_y),
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(112, 138, 132, 150)
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        source, source_elbow, destination_elbow, destination = self.connection_points()
        painter.drawLine(source, source_elbow)
        painter.drawLine(source_elbow, destination_elbow)
        painter.drawLine(destination_elbow, QPointF(destination.x() - 6, destination.y()))
        arrow = QPolygonF([
            QPointF(destination.x() - 8, destination.y() - 5),
            QPointF(destination.x() - 8, destination.y() + 5),
            destination,
        ])
        painter.setBrush(color)
        painter.drawPolygon(arrow)


class ChainResourceBox(QFrame):
    resource_selected = Signal(str)

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
        input_resources: Mapping[str, float] | None = None,
        input_names: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("chainResourceBox")
        self.setProperty("resourceId", resource_id)
        self.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        self.setProperty("machineFamily", machine_family)
        self.setProperty("stageAccent", stage.value)
        self.setProperty("target", required_amount <= 0 and output_amount > 0)
        self.setFixedWidth(264)
        self.setMinimumHeight(92 if not input_resources else 116)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=38)
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
        family.setProperty("secondaryTextRole", "metadata")
        family.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        text.addWidget(family)
        header.addLayout(text, 1)
        layout.addLayout(header)

        if input_resources:
            inputs_host = QFrame()
            inputs_host.setObjectName("chainResourceInputs")
            inputs_layout = QVBoxLayout(inputs_host)
            inputs_layout.setContentsMargins(0, 0, 0, 0)
            inputs_layout.setSpacing(0)
            for input_id, amount in input_resources.items():
                input_name = (input_names or {}).get(input_id, input_id.replace("_", " ").title())
                input_link = QPushButton(f"{amount:g} {input_name}")
                input_link.setObjectName("guideRecipeInputLink")
                input_link.setProperty("resourceId", input_id)
                input_link.setProperty("chainNodeInput", True)
                input_link.setFixedHeight(16)
                input_link.setCursor(Qt.CursorShape.PointingHandCursor)
                input_link.clicked.connect(
                    lambda checked=False, rid=input_id: self.resource_selected.emit(rid)
                )
                inputs_layout.addWidget(input_link)
            layout.addWidget(inputs_host)
        layout.addStretch(1)
        divider = QFrame()
        divider.setObjectName("chainResourceDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        amount_label = QLabel(f"{output_amount:g} / CYCLE" if output_amount > 0 else "—")
        amount_label.setWordWrap(True)
        amount_label.setObjectName("chainResourceAmount")
        amount_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(amount_label)


class GuideRecipeRow(QFrame):
    resource_selected = Signal(str)

    def __init__(
        self,
        *,
        resource_id: str,
        resource_name: str,
        detail: str,
        meta: str,
        icon_key: str,
        accent_key: str,
        progression_state: str = "unlocked",
    ) -> None:
        super().__init__()
        self._resource_id = resource_id
        self.setObjectName("guideRecipeRow")
        self.setProperty("resourceId", resource_id)
        self.setProperty("progressionState", progression_state)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(208)
        self.setMinimumWidth(268)
        self.setMaximumWidth(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        icon = ResourceIconWidget(resource_id, icon_key, accent_key, size=48)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QPushButton(resource_name)
        title.setObjectName("guideRecipeLink")
        title.setProperty("progressionState", progression_state)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        title.clicked.connect(lambda checked=False: self.resource_selected.emit(self._resource_id))
        text.addWidget(title)
        meta_label = QLabel(meta)
        meta_label.setObjectName("guideRecipeMeta")
        meta_label.setProperty("secondaryTextRole", "metadata")
        meta_label.setProperty("progressionState", progression_state)
        text.addWidget(meta_label)
        layout.addLayout(text)

        detail_label = QLabel(detail)
        detail_label.setObjectName("guideRecipeDetail")
        detail_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        detail_label.setWordWrap(True)
        layout.addWidget(detail_label)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.resource_selected.emit(self._resource_id)
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.resource_selected.emit(self._resource_id)
            return
        super().keyPressEvent(event)




class FactoryViewBase(QWidget):
    """Shared runtime and subviews; the concrete production screen is FactoryViewV2."""
    supply_requested = Signal(str)

    def __init__(self, state: GameState, command_bus: CommandBus, definitions: dict[str, CardDefinition], board_config: ProductionBoardConfig | None = None) -> None:
        if type(self) is FactoryViewBase:
            raise TypeError("Use FactoryViewV2; this is shared runtime code, not a screen")
        super().__init__()
        self._state = state
        self._board_config = board_config or ProductionBoardConfig()
        self._units = state.production_units(self._board_config.board_kind)
        self._command_bus = command_bus
        self._definitions = definitions
        initialize_production_progress(state, definitions)
        self._simulation = SimulationEngine(definitions)
        self._last_update = perf_counter()
        self._simulation_advanced_callback: Callable[[], None] | None = None
        self._selected_hall_id = next(iter(self._units))
        self._selected_card_id: str | None = None
        self._drawer_mode: str | None = None
        self._drawer_slot_index: int | None = None
        self._card_search_text = ""
        self._card_type_filter_text = "All"
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
        self._guide_scroll_value = 0
        self._guide_option_index_build_count = 0
        self._guide_option_index_cache = self._build_guide_option_index()
        self._guide_recipe_index = ProductionGuideRecipeIndex(self._definitions)
        self._guide_items_cache_signature: tuple[tuple[str, ...], tuple[tuple[str, float], ...]] | None = None
        self._guide_items_cache: list[ProductionOptionDefinition] = []
        self._guide_items_cache_rebuild_count = 0
        self._chain_resource_id: str | None = None
        self._chain_back_mode: str = "hall"
        self._chain_canvas: ZoomPanGraphicsView | None = None
        self._cached_unlock_tree_panel: UnlockTreeView | None = None
        self._recent_install_slot_indexes: set[int] = set()
        self._recent_production_change_card_ids: set[str] = set()
        self._slot_widgets: dict[int, QWidget] = {}
        self._kpi_strip: KpiStripWidget | None = None
        self._resource_summary: HallResourceSummaryWidget | None = None
        self._selection_hover_card_id: str | None = None
        self._selection_hover_popup: CardHoverInfoPopup | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        from production_zero.ui.building_tree import BuildingTree
        self._hall_tree = BuildingTree() if self._board_config.board_kind in {'resources', 'factory'} else QTreeWidget()
        if self._board_config.board_kind in {'resources', 'factory'}:
            from production_zero.core.commands import ReorderBuildings
            self._hall_tree.enable_reordering(lambda ids: self._command_bus.dispatch(
                ReorderBuildings(self._board_config.board_kind, ids)))
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
        sidebar_label = QLabel(self._board_config.title)
        sidebar_label.setObjectName("factoryNavTitle")
        sidebar_subtitle = QLabel(f"OPERATIONS / {self._board_config.unit_plural}")
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
        if self._board_config.board_kind == "factory":
            self._timer.start()


    def _refresh_build_hall_button(self) -> None:
        board=self._board_config.board_kind
        try:
            cost = min(production_facility_price(self._state,board,target) for target in ('machine.extractor','machine.agriculture','machine.drilling')) if board=='resources' else production_facility_price(self._state,board)
        except ValueError:
            self._build_hall_button.setProperty('quotedCost', None)
            self._build_hall_button.setText(f"{self._board_config.purchase_label} (price unavailable)")
            self._build_hall_button.setEnabled(False)
            return
        self._build_hall_button.setProperty('quotedCost',cost)
        self._build_hall_button.setText(f"{self._board_config.purchase_label} (${cost:.2f})")
        self._build_hall_button.setEnabled(self._state.cash.amount >= cost)


    def _detach_runtime_widget_references(self) -> None:
        self._slot_widgets = {}
        self._kpi_strip = None
        self._resource_summary = None

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)


    def _line_number(self, hall: FactoryHall, line: ProductionLine) -> int:
        return hall.production_lines.index(line) + 1


    def _build_production_guide_view(self) -> QFrame:
        cached = getattr(self, "_cached_guide_panel", None)
        if cached is not None:
            self._guide_grid_host = cached.findChild(ResizingGridHost, "productionGuideGridHost")
            self._guide_grid = self._guide_grid_host.layout()
            signature = self._guide_progress_signature()
            if signature != self._cached_guide_progress:
                self._populate_guide_grid()
                self._cached_guide_progress = signature
            cached.show()
            return cached
        self._guide_view_build_count += 1
        panel = QFrame()
        panel.setObjectName("productionGuideView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        header_panel = QFrame()
        header_panel.setObjectName("productionGuideHeader")
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(14, 10, 14, 10)
        header.setSpacing(12)
        title = QLabel("PRODUCTION GUIDE")
        title.setObjectName("sectionLabel")
        back = secondary_action_button("Back", "productionGuideBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back)
        guide_title = QLabel("PRODUCTION GUIDE")
        guide_title.setObjectName("productionGuideTitle")
        guide_subtitle = QLabel("Browse resources and production chains")
        guide_subtitle.setObjectName("productionGuideSubtitle")
        header_actions = QWidget()
        header_actions.setObjectName("productionGuideHeaderActions")
        header_action_layout = QHBoxLayout(header_actions)
        header_action_layout.setContentsMargins(0, 0, 0, 0)
        header_action_layout.setSpacing(8)
        unlock_tree = secondary_action_button("Unlock Tree", "productionGuideUnlockTreeButton")
        unlock_tree.setProperty("primaryNavigation", True)
        unlock_tree.clicked.connect(lambda checked=False: self._open_unlock_tree())
        header_action_layout.addWidget(unlock_tree)
        header_action_layout.addWidget(back)
        layout.addWidget(SecondaryViewHeader(guide_title, guide_subtitle, header_actions))
        header_panel.deleteLater()

        search = QLineEdit()
        search.setObjectName("productionGuideSearchInput")
        search.setPlaceholderText("Search products...")
        search.setText(self._guide_search_text)
        search.textChanged.connect(self._on_guide_search_changed)

        stage_filter = StageFilterBar(
            [
                ("ALL", "All"),
                ("PRIMARY PRODUCTION", "Primary Production"),
                ("PROCESSOR", "Processing"),
                ("FABRICATOR", "Manufacturing"),
                ("ASSEMBLER", "Assembly"),
            ],
            self._guide_stage_filter_text,
            self._on_guide_stage_filter_changed,
        )

        category_filter = QComboBox()
        category_filter.setObjectName("productionGuideCategoryFilter")
        for option in self._guide_category_options():
            category_filter.addItem(option)
        category_filter.setCurrentText(self._guide_category_filter_text if self._guide_category_filter_text in self._guide_category_options() else "All")
        category_filter.currentTextChanged.connect(self._on_guide_category_filter_changed)

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
        self._guide_grid.setContentsMargins(12, 12, 12, 12)
        self._guide_grid.setSpacing(12)
        grid_host.setProperty("guideGridColumns", self._guide_grid_columns())
        self._populate_guide_grid()
        scroll.setWidget(grid_host)
        QTimer.singleShot(0, scroll, lambda scroll=scroll: scroll.verticalScrollBar().setValue(self._guide_scroll_value))
        representatives = {browser_category(rid, option.stage.value): rid for rid, option in self._guide_option_index().items()}
        layout.addWidget(ResourceBrowser(search, category_filter, scroll, representatives, stage_filter), 1)
        self._cached_guide_panel = panel
        self._cached_guide_progress = self._guide_progress_signature()
        return panel

    def _build_unlock_tree_view(self) -> UnlockTreeView:
        cached = self._cached_unlock_tree_panel
        if cached is not None and is_qt_object_valid(cached):
            cached.refresh_state()
            cached.show()
            QTimer.singleShot(0, cached.focus_default_region)
            return cached
        panel = UnlockTreeView(self._state, self._definitions, self._back_from_unlock_tree)
        self._cached_unlock_tree_panel = panel
        return panel

    def _build_chain_inspector_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("chainInspectorView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        resource_id = self._chain_resource_id or ""
        option = self._guide_option_index().get(resource_id)
        header_panel = QFrame()
        header_panel.setObjectName("chainInspectorHeader")
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(14, 10, 14, 10)
        header.setSpacing(12)
        back = secondary_action_button("Back", "chainInspectorBackButton")
        back.setProperty("primaryNavigation", True)
        back.clicked.connect(lambda checked=False: self._back_from_chain_inspector())
        title = QLabel(f"CHAIN INSPECTOR · {self._resource_display_name(resource_id).upper()}")
        title.setObjectName("sectionLabel")
        header.addWidget(back)
        header.addWidget(title)
        header.addStretch(1)
        layout.addWidget(SecondaryViewHeader(title, "Production requirements and upstream flow", back))
        header_panel.deleteLater()

        if option is None:
            empty = QLabel("No production chain data available for this product.")
            empty.setObjectName("chainInspectorEmpty")
            layout.addWidget(empty)
            layout.addStretch(1)
            return panel

        technical_chassis = QFrame()
        technical_chassis.setObjectName("secondaryTechnicalChassis")
        technical_layout = QVBoxLayout(technical_chassis)
        technical_layout.setContentsMargins(10, 10, 10, 10)
        technical_layout.setSpacing(10)
        technical_layout.addWidget(self._build_guide_recipe_details(resource_id))

        chain = self._build_chain(resource_id)
        flow_shell = QFrame()
        flow_shell.setObjectName("chainInspectorFlowShell")
        flow_shell.setStyleSheet(panel.styleSheet())
        flow_layout = QVBoxLayout(flow_shell)
        flow_layout.setContentsMargins(10, 10, 10, 10)
        flow_layout.setSpacing(0)
        host = QWidget()
        host.setObjectName("chainInspectorStageHost")
        host_layout = QHBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(8)
        stack_height = max(
            (
                sum(116 if node["input_resources"] else 92 for node in nodes)
                + max(0, len(nodes) - 1) * 6
            )
            for nodes in chain.values()
        )
        stage_height = 28 + stack_height
        stage_groups: list[QWidget] = []
        for stage in CHAIN_STAGE_ORDER:
            nodes = chain.get(stage, [])
            if not nodes:
                continue
            stage_group = self._build_chain_stage_group(stage, nodes)
            stage_group.setFixedHeight(stage_height)
            stage_groups.append(stage_group)
        for index, stage_group in enumerate(stage_groups):
            host_layout.addWidget(stage_group, 0, Qt.AlignmentFlag.AlignTop)
            if index < len(stage_groups) - 1:
                host_layout.addWidget(ChainFlowConnector(stage_group, stage_groups[index + 1]))
        flow_layout.addWidget(host)
        canvas = ZoomPanGraphicsView(object_prefix="chainInspector", scene_padding=8.0)
        canvas.setMinimumHeight(190)
        canvas.set_content_widget(flow_shell)
        self._chain_canvas = canvas
        technical_layout.addWidget(canvas, 1)
        layout.addWidget(technical_chassis, 1)
        return panel

    def _build_guide_recipe_details(self, resource_id: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("guideRecipeDetails")
        panel.setProperty("chainSummary", True)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(14)
        entries = self._guide_recipe_index.produced_by(resource_id)
        if entries:
            entry = entries[0]
            product = QFrame()
            product.setObjectName("chainSummaryProduct")
            product_layout = QVBoxLayout(product)
            product_layout.setContentsMargins(0, 0, 0, 0)
            product_layout.setSpacing(1)
            name = QLabel(self._resource_display_name(resource_id).upper())
            name.setObjectName("chainSummaryProductName")
            family = QLabel(entry.machine_name.upper())
            family.setObjectName("chainSummaryMachineFamily")
            product_layout.addWidget(name)
            product_layout.addWidget(family)
            layout.addWidget(product, 2)

            rate = QFrame()
            rate.setObjectName("chainSummaryRateBlock")
            rate.setFixedWidth(230)
            rate_layout = QVBoxLayout(rate)
            rate_layout.setContentsMargins(12, 6, 12, 6)
            rate_layout.setSpacing(1)
            rate_label = QLabel("PRODUCTION RATE")
            rate_label.setObjectName("chainSummaryRateLabel")
            rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_value = QLabel(
                f"{entry.output_amount:g} / {entry.cycle_seconds:g}s  ·  "
                f"{entry.output_per_minute:g} / MIN"
            )
            rate_value.setObjectName("chainSummaryRateValue")
            rate_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rate_layout.addWidget(rate_label)
            rate_layout.addWidget(rate_value)
            layout.addWidget(rate)
        layout.addStretch(1)
        count = len(self._guide_recipe_index.used_in(resource_id))
        action = UsedInNavigationButton(count)
        action.setFixedSize(142, 68)
        action.clicked.connect(lambda checked=False: self._open_used_in_detail(resource_id))
        layout.addWidget(action)
        return panel


    def _build_used_in_detail_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("usedInDetailView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(13)

        resource_id = self._chain_resource_id or ""
        entries = self._guide_recipe_index.used_in(resource_id)
        header_panel = QFrame()
        header_panel.setObjectName("usedInDetailHeader")
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(14, 10, 14, 10)
        header.setSpacing(12)
        back = secondary_action_button("Back", "usedInBackButton")
        back.clicked.connect(lambda checked=False: self._back_from_used_in_detail())
        title = QLabel(f"USED IN · {self._resource_display_name(resource_id).upper()}")
        title.setObjectName("sectionLabel")
        count = QLabel(f"{len(entries)} downstream product{'s' if len(entries) != 1 else ''}")
        count.setObjectName("usedInDetailCount")
        layout.addWidget(SecondaryViewHeader(title, count, back))
        header_panel.deleteLater()

        rows = self._used_in_rows(resource_id)
        scroll = QScrollArea()
        scroll.setObjectName("usedInDetailScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = GuideRecipeGridHost(rows, minimum_column_width=268)
        content.setObjectName("usedInDetailGridHost")
        scroll.setWidget(content)
        chassis = QFrame()
        chassis.setObjectName("secondaryContentChassis")
        chassis_layout = QVBoxLayout(chassis)
        chassis_layout.setContentsMargins(9, 9, 9, 9)
        chassis_layout.addWidget(scroll)
        layout.addWidget(chassis, 1)
        return panel



    def _build_produced_by_row(self, entry: GuideRecipeEntry, inputs: tuple[QPushButton, ...]) -> QFrame:
        panel = QFrame()
        panel.setObjectName("guideRecipeRow")
        panel.setProperty("resourceId", entry.production.output_resource)
        progression_state = production_progress_state(self._state, entry.production)
        panel.setProperty("progressionState", progression_state)
        panel.setMinimumHeight(92)
        panel.setMaximumHeight(166)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        top = QHBoxLayout()
        name = QLabel(entry.production.name)
        name.setObjectName("guideRecipeName")
        top.addWidget(name, 1)
        rate = QLabel(f"{entry.output_per_minute:g}/min")
        rate.setObjectName("guideRecipeDetail")
        rate.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(rate)
        layout.addLayout(top)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(5)
        meta = QLabel(f"{entry.machine_name} ·")
        meta.setObjectName("guideRecipeMeta")
        meta.setProperty("secondaryTextRole", "metadata")
        meta.setProperty("progressionState", progression_state)
        production_rate = QLabel(f"{entry.output_amount:g} per {entry.cycle_seconds:g}s")
        production_rate.setObjectName("guideRecipeRate")
        production_rate.setProperty("progressionState", progression_state)
        meta_row.addWidget(meta)
        meta_row.addWidget(production_rate)
        meta_row.addStretch(1)
        layout.addLayout(meta_row)

        if progression_state != "unlocked":
            requirement_lines = _player_progression_lines(
                progression_state,
                unlock_requirement_lines(
                    self._state,
                    entry.production,
                    {resource_id: self._resource_display_name(resource_id) for resource_id in self._guide_option_index()},
                ),
            )
            requirements = QLabel("\n".join(requirement_lines))
            requirements.setObjectName("productionGuideUnlock")
            requirements.setProperty("progressionState", progression_state)
            requirements.setWordWrap(True)
            requirements.setToolTip("\n".join(requirement_lines))
            layout.addWidget(requirements)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        input_label = QLabel("Inputs")
        input_label.setObjectName("guideRecipeInputLabel")
        input_row.addWidget(input_label)
        if inputs:
            for button in inputs:
                input_row.addWidget(button)
        else:
            base = QLabel("Base product")
            base.setObjectName("guideRecipeInputEmpty")
            input_row.addWidget(base)
        input_row.addStretch(1)
        layout.addLayout(input_row)
        return panel

    def _guide_recipe_input_buttons(self, entry: GuideRecipeEntry) -> tuple[QPushButton, ...]:
        buttons: list[QPushButton] = []
        for input_resource_id, amount in entry.production.input_resources.items():
            button = RecipeInputButton(f"{amount:g} {self._resource_display_name(input_resource_id)}")
            button.setObjectName("guideRecipeInputLink")
            button.setFixedHeight(34)
            button.setProperty("resourceId", input_resource_id)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, rid=input_resource_id: self._open_chain_from_guide(rid))
            buttons.append(button)
        return tuple(buttons)

    def _used_in_rows(self, resource_id: str) -> tuple[QWidget, ...]:
        rows: list[QWidget] = []
        for entry in self._guide_recipe_index.used_in(resource_id):
            amount = entry.production.input_resources[resource_id]
            input_rate = entry.input_per_minute(resource_id)
            progression_state = production_progress_state(self._state, entry.production)
            status = _player_progression_lines(
                progression_state,
                unlock_requirement_lines(
                    self._state,
                    entry.production,
                    {rid: self._resource_display_name(rid) for rid in self._guide_option_index()},
                ),
            )[0].title()
            row = GuideRecipeRow(
                resource_id=entry.production.output_resource,
                resource_name=entry.production.name,
                detail=f"OUTPUT  {entry.output_amount:g} / {entry.cycle_seconds:g}s · {entry.output_per_minute:g}/min\nINPUT  {amount:g}/cycle · {input_rate:g}/min",
                meta=f"{entry.machine_name} · {status}",
                icon_key=entry.production.icon_key or resource_icon_key(entry.production.output_resource),
                accent_key=entry.production.accent_key or resource_accent_key(entry.production.output_resource),
                progression_state=progression_state,
            )
            row.resource_selected.connect(self._open_chain_from_guide)
            rows.append(row)
        return tuple(rows)

    def _build_chain_stage_group(self, stage: MachineType, nodes: list[dict[str, object]]) -> QWidget:
        group = QWidget()
        group.setObjectName("chainStageGroup")
        group.setProperty("stage", PRODUCTION_STAGE_LABELS[stage])
        group.setFixedWidth(264)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        host = QWidget()
        host.setObjectName("chainStageNodeHost")
        node_layout = QVBoxLayout(host)
        node_layout.setContentsMargins(0, 0, 0, 0)
        node_layout.setSpacing(6)
        title = QLabel(PRODUCTION_STAGE_LABELS[stage].upper())
        title.setObjectName("chainStageTitle")
        title.setProperty("stageAccent", stage.value)
        node_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignLeft)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        columns = 1
        for index, node in enumerate(nodes):
            grid.addWidget(
                resource_box := ChainResourceBox(
                    str(node["resource_id"]),
                    str(node["name"]),
                    stage,
                    str(node["machine_family"]),
                    float(node["required_amount"]),
                    float(node["output_amount"]),
                    str(node["icon_key"]),
                    str(node["accent_key"]),
                    node["input_resources"],
                    {
                        str(input_id): self._resource_display_name(str(input_id))
                        for input_id in node["input_resources"]
                    },
                ),
                index // columns,
                index % columns,
            )
            resource_box.resource_selected.connect(self._open_chain_from_guide)
        grid.setColumnStretch(columns, 1)
        node_layout.addLayout(grid)
        layout.addWidget(host, 0, Qt.AlignmentFlag.AlignTop)
        return group

    def _build_production_selection_view(self) -> QFrame:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            self._reset_drawer_state()
            empty = QFrame()
            empty.setObjectName("productionSelectionView")
            return empty

        panel = QFrame()
        panel.setObjectName("productionSelectionView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("SELECT RESOURCE" if definition.machine_type in PRIMARY_MACHINE_TYPES else "SELECT RECIPE")
        title.setObjectName("sectionLabel")
        current = self._active_production_option(card, definition)
        current_label = QLabel(f"Current: {current.name if current is not None else 'Not selected'}")
        current_label.setObjectName("productionCurrentLabel")
        current_label.setProperty("iconKey", current.icon_key if current is not None else "")
        current_label.setProperty("accentKey", current.accent_key if current is not None else "")
        back = QPushButton("Back")
        back.setObjectName("productionSelectionBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        layout.addWidget(SecondaryViewHeader(title, current_label, back))

        search = QLineEdit()
        search.setObjectName("productionSearchInput")
        search.setPlaceholderText("Search production...")
        search.setText(self._production_search_text)
        search.textChanged.connect(self._on_production_search_changed)

        category_filter = QComboBox()
        category_filter.setObjectName("productionCategoryFilter")
        category_filter.blockSignals(True)
        category_filter.addItems(self._production_category_filter_options())
        if self._production_category_filter_text in self._production_category_filter_options():
            category_filter.setCurrentText(self._production_category_filter_text)
        category_filter.blockSignals(False)
        category_filter.currentTextChanged.connect(self._on_production_category_filter_changed)

        grid_host = ResourceSelectionGridHost()
        grid_host.setObjectName("productionSelectionGridHost")
        configure_resource_selection_grid_host(grid_host)
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
        configure_resource_selection_scroll(scroll)
        scroll.setWidget(grid_host)
        representatives = {browser_category(p.output_resource, definition.machine_type.value): p.output_resource for p in definition.production_options}
        layout.addWidget(ResourceBrowser(search, category_filter, scroll, representatives), 1)
        return panel

    def _build_factory_card_selection_view(self, hall: FactoryHall) -> QFrame:
        panel = QFrame()
        panel.setObjectName("factoryCardSelectionView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        assignment_kind = {
            "resources": "RESOURCE",
            "factory": "FACTORY",
            "energy": "ENERGY",
        }[self._board_config.board_kind]
        title = QLabel(f"ASSIGN {assignment_kind} CARD")
        title.setObjectName("sectionLabel")
        slot_label = QLabel(
            f"{hall.name} · Slot "
            f"{self._drawer_slot_index + 1 if self._drawer_slot_index is not None else '-'}"
        )
        slot_label.setObjectName("cardSelectionTargetLabel")
        back = secondary_action_button("Back", "cardSelectionBackButton")
        back.clicked.connect(lambda checked=False: self._close_drawer())
        layout.addWidget(SecondaryViewHeader(title, slot_label, back))

        filters_panel = QFrame()
        filters_panel.setObjectName("secondaryControlDeck")
        filters = QHBoxLayout(filters_panel)
        filters.setContentsMargins(10, 8, 10, 8)
        filters.setSpacing(8)

        search = QLineEdit()
        search.setObjectName("cardSearchInput")
        search.setPlaceholderText(f"SEARCH {assignment_kind} CARDS")
        search.setMaximumWidth(540)
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

        rarity_filter = QComboBox()
        rarity_filter.setObjectName("cardSelectionRarityFilter")
        rarity_filter.blockSignals(True)
        rarity_filter.addItems(self._card_rarity_filter_options())
        if self._card_rarity_filter_text in self._card_rarity_filter_options():
            rarity_filter.setCurrentText(self._card_rarity_filter_text)
        rarity_filter.blockSignals(False)
        rarity_filter.currentTextChanged.connect(self._on_card_rarity_filter_changed)
        filters.addWidget(rarity_filter)
        filters.addStretch(1)
        layout.addWidget(filters_panel)

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
        chassis = QFrame()
        chassis.setObjectName("secondaryContentChassis")
        chassis_layout = QVBoxLayout(chassis)
        chassis_layout.setContentsMargins(9, 9, 9, 9)
        chassis_layout.addWidget(scroll)
        layout.addWidget(chassis, 1)
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

        title = QLabel("SELECT RESOURCE" if definition.machine_type in PRIMARY_MACHINE_TYPES else "SELECT RECIPE")
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
        types = {"All"}
        for stack in build_placeable_inventory_stacks(self._state, self._definitions):
            definition = self._definitions.get(stack.first_card.definition_id)
            if not self._definition_allowed(definition):
                continue
            if isinstance(definition, MachineDefinition):
                types.add(definition.name)
            elif isinstance(definition, EnergyDefinition):
                types.add("Energy")
        return ["All", *sorted(types - {"All"})]

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
            if not self._definition_allowed(definition):
                continue
            name = definition.name if definition is not None else card.definition_id
            card_type = "Card"
            if isinstance(definition, MachineDefinition):
                card_type = definition.name
            elif isinstance(definition, EnergyDefinition):
                card_type = "Energy"
            if self._card_type_filter_text not in ("", "All", card_type):
                continue
            if self._card_rarity_filter_text not in ("", "All", card.rarity.value.title()):
                continue
            haystack = f"{name} {card_type} {card.rarity.value}".lower()
            if search and search not in haystack:
                continue
            stacks.append(stack)
        return tuple(stacks)

    def _definition_allowed(self, definition: CardDefinition | None) -> bool:
        if isinstance(definition, EnergyDefinition):
            return self._board_config.allow_energy
        if not isinstance(definition, MachineDefinition) or definition.machine_type not in self._board_config.allowed_machine_types:
            return False
        if self._board_config.board_kind == "resources":
            from production_zero.core.machine_operations import site_accepts
            site = self._units[self._selected_hall_id]
            return site_accepts(self._state, site, definition.definition_id)
        return True

    def _populate_card_selection_grid(self) -> None:
        if self._card_selection_grid is None:
            return
        self._clear_layout(self._card_selection_grid)
        stacks = self._filtered_placeable_stacks()
        if not stacks:
            empty_copy = {
                "resources": (
                    "NO COMPATIBLE RESOURCE CARDS",
                    "Acquire compatible Primary Production cards from Industrial Supply.",
                ),
                "factory": (
                    "NO COMPATIBLE FACTORY CARDS",
                    "Acquire compatible production cards from Industrial Supply.",
                ),
                "energy": (
                    "NO COMPATIBLE ENERGY CARDS",
                    "Acquire compatible energy cards from Industrial Supply.",
                ),
            }[self._board_config.board_kind]
            category = {"resources": "Resources", "factory": "Factory", "energy": "Energy"}[self._board_config.board_kind]
            supply = secondary_action_button("OPEN INDUSTRIAL SUPPLY", "openIndustrialSupplyButton")
            supply.clicked.connect(lambda checked=False, category=category: self.supply_requested.emit(category))
            empty = EmptyStatePanel(*empty_copy, action=supply)
            empty.findChild(QWidget, "emptyStateIcon").hide()
            empty.setObjectName("factoryCardSelectionEmpty")
            self._card_selection_grid.addWidget(empty, 0, 0)
            return
        columns = self._card_selection_grid_columns()
        row_offset = 0
        if len(stacks) <= 2:
            noun = "CARD" if len(stacks) == 1 else "CARDS"
            result_count = QLabel(f"{len(stacks)} COMPATIBLE {noun} AVAILABLE")
            result_count.setObjectName("factoryCardSelectionResultCount")
            result_count.setMaximumWidth(340)
            self._card_selection_grid.addWidget(result_count, 0, 0, 1, columns)
            row_offset = 1
        for index, stack in enumerate(stacks):
            tile = self._build_card_selection_tile(stack)
            self._card_selection_grid.addWidget(tile, row_offset + index // columns, index % columns)
        self._card_selection_grid.setRowStretch(
            row_offset + (len(stacks) + columns - 1) // columns,
            1,
        )
        self._card_selection_grid.setColumnStretch(columns, 1)

    def _build_guide_option_index(self) -> dict[str, ProductionOptionDefinition]:
        self._guide_option_index_build_count += 1
        indexed: dict[str, ProductionOptionDefinition] = {}
        for definition in self._definitions.values():
            if not isinstance(definition, MachineDefinition):
                continue
            for option in definition.available_production_options:
                if option.stage not in PRODUCTION_STAGE_ORDER:
                    continue
                existing = indexed.get(option.output_resource)
                if existing is None or PRODUCTION_STAGE_ORDER.index(option.stage) > PRODUCTION_STAGE_ORDER.index(existing.stage):
                    indexed[option.output_resource] = option
        return indexed

    def _guide_option_index(self) -> dict[str, ProductionOptionDefinition]:
        return self._guide_option_index_cache

    def _guide_progress_signature(self) -> tuple:
        progress = self._state.production_progress
        return (
            tuple(sorted(progress.unlocked_production_ids)),
            tuple(sorted((resource_id, round(amount, 6)) for resource_id, amount in progress.lifetime_produced.items())),
            self._state.company.level,
            frozenset(progress.first_produced_resource_ids),
            frozenset(progress.mastered_family_ids),
        )

    def _guide_items(self) -> list[ProductionOptionDefinition]:
        signature = self._guide_progress_signature()
        if self._guide_items_cache_signature == signature:
            return list(self._guide_items_cache)
        order = {"unlocked": 0, "next": 1, "later": 2}
        self._guide_items_cache_signature = signature
        self._guide_items_cache_rebuild_count += 1
        self._guide_items_cache = sorted(
            self._guide_option_index().values(),
            key=lambda option: (
                order[production_progress_state(self._state, option)],
                PRODUCTION_STAGE_ORDER.index(option.stage),
                option.name,
            ),
        )
        return list(self._guide_items_cache)

    def _guide_category_options(self) -> list[str]:
        categories = {
            browser_category(option.output_resource, option.stage.value)
            for option in self._guide_items()
        }
        return ["All", *sorted(categories)]

    def _filtered_guide_items(self) -> list[ProductionOptionDefinition]:
        search = self._guide_search_text.strip().lower()
        items = []
        later_count = 0
        for option in self._guide_items():
            stage_label = PRODUCTION_STAGE_LABELS[option.stage]
            category = browser_category(option.output_resource, option.stage.value)
            if self._guide_stage_filter_text not in ("", "All", stage_label):
                continue
            if self._guide_category_filter_text not in ("", "All", category):
                continue
            haystack = f"{option.name} {option.output_resource} {stage_label} {category}".lower()
            if search and search not in haystack:
                continue
            if not search and self._guide_stage_filter_text in ("", "All") and self._guide_category_filter_text in ("", "All"):
                if production_progress_state(self._state, option) == "later":
                    later_count += 1
                    if later_count > 18:
                        continue
            items.append(option)
        return items

    def _populate_guide_grid(self) -> None:
        if self._guide_grid is None:
            return
        self._guide_grid_rebuild_count += 1
        items = self._filtered_guide_items()
        while self._guide_grid.count():
            widget = self._guide_grid.takeAt(0).widget()
            if widget is not None:
                widget.hide()
                if not isinstance(widget, ProductionGuideTile):
                    widget.deleteLater()
        retained = {
            str(tile.property("resourceId")): tile
            for tile in self._guide_grid_host.findChildren(ProductionGuideTile)
        }
        # Tiles are cached so search/filter changes do not recreate all 353
        # widgets.  Every cached child must remain explicitly hidden until it is
        # inserted into this rebuild's grid; otherwise Qt shows parented,
        # non-layout children at (0, 0), stacked in creation order.
        for tile in retained.values():
            tile.hide()
        if not items:
            empty = QLabel("No products found")
            empty.setObjectName("productionGuideEmpty")
            self._guide_grid.addWidget(empty, 0, 0)
            return
        columns = self._guide_grid_columns()
        resource_names = {resource_id: self._resource_display_name(resource_id) for resource_id in self._guide_option_index()}
        signature = self._guide_progress_signature()
        if signature != getattr(self, "_guide_requirements_signature", None):
            self._guide_requirements_signature = signature
            self._guide_requirements_cache = {}
            from production_zero.core.progression import _unlocked_output_resources
            self._guide_unlocked_outputs = _unlocked_output_resources(self._state)
        for option in items:
            category = browser_category(option.output_resource, option.stage.value)
            progress_state = production_progress_state(self._state, option)
            cached_lines = self._guide_requirements_cache.get(option.output_resource)
            if cached_lines is None:
                cached_lines = _player_progression_lines(progress_state,
                    unlock_requirement_lines(self._state, option, resource_names,
                                             unlocked_outputs=self._guide_unlocked_outputs))
                self._guide_requirements_cache[option.output_resource] = cached_lines
            player_requirement_lines = cached_lines
            tile = retained.get(option.output_resource)
            if tile is None:
                self._guide_tile_create_count += 1
                tile = ProductionGuideTile(
                    option.output_resource,
                    option.name,
                    option.stage,
                    category,
                    option.icon_key or resource_icon_key(option.output_resource),
                    option.accent_key or resource_accent_key(option.output_resource),
                    progress_state,
                    player_requirement_lines,
                )
                tile.selected.connect(self._open_chain_from_guide)
                tile.setParent(self._guide_grid_host)
                tile.hide()
                retained[option.output_resource] = tile
            tile.setProperty("progressionState", progress_state)
            tile.update_text("productionGuideUnlock", tile._unlock_text(progress_state, player_requirement_lines))
            tile.setToolTip("\n".join((option.name,category,base_price_text(option.output_resource),*player_requirement_lines)))
        for index, option in enumerate(items):
            tile = retained[option.output_resource]
            tile.show()
            self._guide_grid.addWidget(tile, index // columns, index % columns)
        self._guide_grid.setRowStretch((len(items) + columns - 1) // columns, 1)
        self._guide_grid.setColumnStretch(columns, 1)

    def _guide_grid_columns(self) -> int:
        width = self._guide_grid_host.width() if self._guide_grid_host is not None else self.width()
        return max(2, min(8, max(1, width - 24) // (RESOURCE_TILE_WIDTH + 12)))

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
        stages: dict[MachineType, dict[str, dict[str, object]]] = {stage: {} for stage in CHAIN_STAGE_ORDER}
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
            stage_nodes = stages[_production_stage_group(option.stage)]
            node = stage_nodes.setdefault(
                current_resource_id,
                {
                    "resource_id": current_resource_id,
                    "name": option.name,
                    "machine_family": _machine_type_label(option.stage),
                    "required_amount": 0.0,
                    "output_amount": option.output_amount or 0.0,
                    "icon_key": option.icon_key or resource_icon_key(current_resource_id),
                    "accent_key": option.accent_key or resource_accent_key(current_resource_id),
                },
            )
            node["required_amount"] = float(node["required_amount"]) + required_amount
            entry = self._guide_recipe_index.produced_by(current_resource_id)[0]
            node["input_resources"] = dict(entry.production.input_resources)
            node["output_amount"] = entry.output_amount
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
            ("Bonus", f"+{card.output_bonus_percent:.1f}%"),
        ]
        if isinstance(definition, MachineDefinition):
            machine = self._state.machine_production.get(card_id)
            production = definition.production_option(machine.selected_production_id) if machine and machine.selected_production_id else None
            sections.extend([
                ("Resource", production.name if production else "No resource selected"),
                ("Output", f"{(production.output_amount_for(definition) if production else definition.base_output_per_tick) * card.output_multiplier:g}/cycle"),
                ("Power", f"{(production.power_draw_for(definition) if production else definition.base_power_draw) * card.power_multiplier:g} MW"),
            ])
            if production and production.input_resources:
                sections.append(("Inputs / cycle", _format_resource_amounts({rid: amount * card.mk_multiplier for rid, amount in production.input_resources.items()})))
        elif isinstance(definition, EnergyDefinition):
            from production_zero.core.modifiers import research_multiplier
            sections.append(("Generation", f"{definition.base_power_output * card.output_multiplier * research_multiplier(self._state.research, 'energy_output'):g} MW"))
            if definition.requires_fuel:
                sections.append(("Fuel / cycle", f"{definition.fuel_consumption_per_cycle * card.mk_multiplier:g} {definition.fuel_resource_id}"))
        title = definition.name if definition is not None else card.definition_id
        resource_id, icon_key, accent_key = self._selection_hover_icon_signature(definition)
        signature = (card_id, tuple(label for label, _value in sections))
        if self._selection_hover_popup.details_signature != signature:
            icon = card_hover_icon(definition, size=42) if definition is not None else ResourceIconWidget(resource_id, icon_key, accent_key, size=42)
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
            if stack.key is not None and stack.key == CardStackKey.from_card(card):
                return stack.quantity
            if any(c.card_id == card.card_id for c in stack.cards):
                return stack.quantity
        return 0

    def _selection_hover_icon_signature(self, definition: CardDefinition | None) -> tuple[str, str, str]:
        if definition is None:
            return ("factory_card", resource_icon_key("factory_card"), resource_accent_key("factory_card"))
        icon_key, accent_key, resource_id = card_resource_icon_signature(definition)
        return (resource_id, icon_key, accent_key)

    def _card_selection_grid_columns(self) -> int:
        width = self._content.width() if self._content.width() > 0 else self.width()
        return max(2, min(8, width // 186))

    def _on_card_selection_grid_host_resized(self, host: QWidget, event) -> None:
        self._populate_card_selection_grid()
        QWidget.resizeEvent(host, event)

    def _card_tile_meta(self, card: CardInstance, definition: CardDefinition | None) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.name
        if isinstance(definition, EnergyDefinition):
            return "Energy"
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
        for production in self._production_picker_options(definition):
            haystack = f"{production.name} {production.output_resource} {' '.join(production.input_resources)}".lower()
            if search and search not in haystack:
                continue
            category = browser_category(production.output_resource, definition.machine_type.value)
            if self._production_category_filter_text not in ("", "All", category):
                continue
            options.append(production)
        return tuple(options)

    def _production_picker_options(self, definition: MachineDefinition) -> tuple[ProductionOptionDefinition, ...]:
        unlocked = list(production_options_for_machine(self._state, definition))
        locked = [option for option in definition.available_production_options if not is_production_unlocked(self._state, option)]
        locked.sort(key=lambda option: (
            0 if production_progress_state(self._state, option) == "next" else 1,
            len(option.input_resources),
            option.name,
        ))
        return tuple([*unlocked, *locked[:2]])

    def _locked_production_reason(self, production: ProductionOptionDefinition) -> str:
        if is_production_unlocked(self._state, production):
            return ""
        lines = unlock_requirement_lines(self._state, production)
        return lines[0] if lines else "LOCKED"

    def _production_category_filter_options(self) -> list[str]:
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return ["All"]
        categories = {
            browser_category(production.output_resource, definition.machine_type.value)
            for production in self._production_picker_options(definition)
        }
        preferred = (
            ["Ores / Metals", "Minerals", "Oil & Gas", "Agriculture", "Forestry"]
            if definition.machine_type in PRIMARY_MACHINE_TYPES
            else ["Materials", "Components", "Electronics", "Energy", "Transport", "Food & Agriculture", "Chemicals", "Medical"]
        )
        ordered = [category for category in preferred if category in categories]
        ordered.extend(sorted(categories - set(ordered)))
        return ["All", *ordered]

    def _populate_production_selection_grid(self) -> None:
        if self._production_selection_grid is None:
            return
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return
        current = self._active_production_option(card, definition)
        current_id = current.production_id if current is not None else None
        self._production_options_signature = self._available_production_signature(definition)
        options = self._filtered_production_options()
        retained = retain_grid_tiles(self._production_selection_grid, {p.output_resource for p in options})
        if not options:
            empty = QLabel("No unlocked production options · Open Production Guide for the next requirement")
            empty.setObjectName("productionSelectionEmpty")
            empty.setWordWrap(True)
            self._production_selection_grid.addWidget(empty, 0, 0)
            return
        columns = self._production_grid_columns()
        for index, production in enumerate(options):
            category = browser_category(production.output_resource, definition.machine_type.value)
            tile = retained.get(production.output_resource)
            if tile is None:
                tile = ProductionSelectionTile(
                    production, current_id, category,
                    locked_reason=self._locked_production_reason(production),
                )
                tile.selected.connect(self._apply_production_option)
            locked_reason = self._locked_production_reason(production)
            tile.setEnabled(not locked_reason)
            tile.setProperty("locked", bool(locked_reason))
            tile.setProperty("current", production.production_id == current_id)
            tile.setCursor(Qt.CursorShape.ForbiddenCursor if locked_reason else Qt.CursorShape.PointingHandCursor)
            status = "CURRENT" if production.production_id == current_id else locked_reason
            tile.update_text("productionTileCurrent", status)
            tile.findChild(QLabel, "productionTileCurrent").setVisible(bool(status))
            self._production_selection_grid.addWidget(tile, index // columns, index % columns)
        self._production_selection_grid.setRowStretch((len(options) + columns - 1) // columns, 1)
        self._production_selection_grid.setColumnStretch(columns, 1)

    def _available_production_signature(self, definition):
        return frozenset(option.production_id for option in production_options_for_machine(self._state, definition))

    def _refresh_open_production_options(self) -> None:
        if self._drawer_mode != "production" or self._production_selection_grid is None:
            return
        card, definition = self._production_drawer_card()
        if card is None or not isinstance(definition, MachineDefinition):
            return
        signature = self._available_production_signature(definition)
        if signature == getattr(self, "_production_options_signature", None):
            return
        scroll = self.findChild(QScrollArea, "productionSelectionScroll")
        position = scroll.verticalScrollBar().value() if scroll is not None else 0
        self._populate_production_selection_grid()
        category = self.findChild(QComboBox, "productionCategoryFilter")
        if category is not None:
            category.blockSignals(True)
            selected = category.currentText()
            category.clear()
            category.addItems(list(dict.fromkeys(["All", selected, *self._production_category_filter_options()])))
            category.setCurrentText(selected)
            category.blockSignals(False)
        if scroll is not None:
            scroll.verticalScrollBar().setValue(position)

    def _production_grid_columns(self) -> int:
        width = self._production_selection_grid_host.width() if self._production_selection_grid_host is not None else self.width()
        return max(2, min(8, width // (RESOURCE_TILE_WIDTH + 10)))

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
        self._command_bus.dispatch(RenameHall(self._selected_hall_id, name, self._board_config.board_kind))
        self._refresh_hall_tree()

    def _purchase_hall(self) -> None:
        before = set(self._units)
        quoted=self._build_hall_button.property('quotedCost')
        if quoted is None:quoted=production_facility_price(self._state,self._board_config.board_kind)
        self._command_bus.dispatch(PurchaseProductionUnit(
            self._board_config.board_kind, self._board_config.unit_label, self._board_config.unit_id_prefix,
            self._board_config.max_lines, self._board_config.max_slots_per_line,
            self._board_config.start_unlocked_lines, self._board_config.start_slots_per_line,
            expected_cost=quoted,
        ))
        created = [hall_id for hall_id in self._units if hall_id not in before]
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
        if hall_id != self._selected_hall_id:
            self._reset_drawer_state()
        self._selected_hall_id = hall_id
        self._refresh_content()

    def _advance_simulation(self) -> None:
        now = perf_counter()
        elapsed = now - self._last_update
        self._last_update = now
        self._simulation.advance_time(self._state, elapsed)
        if self._simulation_advanced_callback is not None:
            self._simulation_advanced_callback()
        elif self.isVisible():
            self._refresh_runtime_widgets()

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

    def reset_for_state_change(self) -> None:
        """Drop session-owned references after New Game or a manual load."""
        from uuid import uuid4
        if hasattr(self, '_cancel_machine_drag'):
            self._cancel_machine_drag()
            self._machine_drag_token = uuid4().hex
        context = getattr(self, "_suspended_board", None)
        if context is not None:
            board = context["_factory_v2_board"]
            if is_qt_object_valid(board):
                board.hide()
                board.deleteLater()
            self._suspended_board = None
        self._units = self._state.production_units(self._board_config.board_kind)
        self._selected_hall_id = next(iter(self._units))
        self._reset_drawer_state()
        self._selected_machines = set()
        self._selected_empty_slots = set()
        self._card_search_text = ""
        self._card_type_filter_text = "All"
        self._card_rarity_filter_text = "All"
        self._production_search_text = ""
        self._production_category_filter_text = "All"
        self._guide_search_text = ""
        self._guide_stage_filter_text = "All"
        self._guide_category_filter_text = "All"
        self._selection_anchor = None
        self._configuration_clipboard = ()
        self._focused_line_id = None
        self._rubber_origin = None
        rubber = getattr(self, "_rubber_band", None)
        if rubber is not None and is_qt_object_valid(rubber):
            rubber.hide()
            rubber.deleteLater()
        self._hide_card_selection_hover()
        for name in ("_cached_guide_panel", "_cached_unlock_tree_panel"):
            widget = getattr(self, name, None)
            if widget is not None and is_qt_object_valid(widget):
                self._content_layout.removeWidget(widget)
                widget.hide()
                widget.deleteLater()
            setattr(self, name, None)
        self._cached_guide_progress = None
        self._guide_requirements_signature = None
        self._guide_requirements_cache = {}
        self._guide_items_cache_signature = None
        self._guide_items_cache = []
        self._guide_scroll_value = 0
        self._chain_resource_id = None
        self._recent_install_slot_indexes.clear()
        self._recent_production_change_card_ids.clear()
        self._factory_v2_scroll_values.clear()
        self._factory_v2_scroll_restore_generation += 1
        self._factory_v2_scroll = None
        self._factory_v2_board = None
        self._resource_drawer = None
        self._resources_drawer_open = False
        self._last_update = perf_counter()
        self.refresh_view()

    def refresh_runtime(self) -> None:
        if hasattr(self, '_check_machine_drag_sources'):
            self._check_machine_drag_sources()
        self._refresh_runtime_widgets()

    def _refresh_runtime_widgets(self) -> None:
        self._refresh_open_production_options()
        if self._drawer_mode == "guide" and self._guide_grid is not None:
            signature = self._guide_progress_signature()
            if signature != getattr(self, "_cached_guide_progress", None):
                self._populate_guide_grid()
                self._cached_guide_progress = signature
        hall = self._units[self._selected_hall_id]
        for slot_index, widget in list(self._slot_widgets.items()):
            if not is_qt_object_valid(widget):
                self._slot_widgets.pop(slot_index, None)
                continue
            slot = hall.slots[slot_index]
            card = self._state.cards.get(slot.card_id) if slot.card_id else None
            definition = self._definitions.get(card.definition_id) if card else None
            production_state = self._state.machine_production.get(card.card_id) if card else None
            if hasattr(widget, "set_data"):
                widget.set_data(slot, card, definition, production_state, self._state)
        if self._kpi_strip is not None and is_qt_object_valid(self._kpi_strip):
            self._kpi_strip.refresh()
        elif self._kpi_strip is not None:
            self._kpi_strip = None
        if self._resource_summary is not None and is_qt_object_valid(self._resource_summary):
            self._resource_summary.refresh()
        elif self._resource_summary is not None:
            self._resource_summary = None
        if self._cached_unlock_tree_panel is not None and is_qt_object_valid(self._cached_unlock_tree_panel) and self._cached_unlock_tree_panel.isVisible():
            self._cached_unlock_tree_panel.refresh_state()
        self._refresh_unlock_panels()
        self._refresh_build_hall_button()

    def _refresh_unlock_panels(self) -> None:
        for panel in [*self.findChildren(QFrame, "lockedSlotPanel"), *self.findChildren(QFrame, "lockedLinePanel")]:
            if not isinstance(panel, ClickableCapacityPanel):
                continue
            cost = float(panel.property("unlockCost") or 0.0)
            enabled = self._state.cash.amount >= cost and panel.property("isNextUnlock") is not False
            if hasattr(panel, "set_unlock_enabled"):
                panel.set_unlock_enabled(enabled)
            else:
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
        hall = self._units[self._selected_hall_id]
        slot = hall.slots[slot_index]
        if slot.card_id is not None:
            self._reset_drawer_state()
            self._command_bus.dispatch(RemoveCardFromHall(self._selected_hall_id, slot_index, self._board_config.board_kind))
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
        if not self._board_config.production_guide_enabled:
            return
        self._drawer_mode = "guide"
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._chain_resource_id = None
        self._chain_back_mode = "hall"
        self._refresh_content()

    def _open_chain_from_guide(self, resource_id: str) -> None:
        self._capture_guide_scroll_value()
        self._drawer_mode = "chain"
        self._chain_resource_id = resource_id
        self._chain_back_mode = "guide"
        self._refresh_content()

    def _open_unlock_tree(self) -> None:
        self._capture_guide_scroll_value()
        self._drawer_mode = "unlock_tree"
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._refresh_content()

    def _back_from_unlock_tree(self) -> None:
        self._drawer_mode = "guide"
        self._refresh_content()

    def _open_used_in_detail(self, resource_id: str) -> None:
        self._drawer_mode = "used_in"
        self._chain_resource_id = resource_id
        self._chain_back_mode = "chain"
        self._refresh_content()

    def _back_from_used_in_detail(self) -> None:
        self._drawer_mode = "chain"
        self._chain_back_mode = "guide"
        self._refresh_content()

    def _capture_guide_scroll_value(self) -> None:
        scroll = self.findChild(QScrollArea, "productionGuideScroll")
        if scroll is not None:
            self._guide_scroll_value = scroll.verticalScrollBar().value()

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
            InstallCardInHall(self._selected_hall_id, installed_slot_index, card_id, self._board_config.board_kind)
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
        card, definition = self._production_drawer_card()
        if not isinstance(definition, MachineDefinition):
            return
        production = production_option_for_id(self._definitions, production_id)
        if production is None or not definition.is_compatible_with(production):
            return
        if not is_production_unlocked(self._state, production):
            return
        self._command_bus.dispatch(SelectMachineProduction(card_id, production_id, target_resource_id))
        self._recent_production_change_card_ids.add(card_id)
        self._reset_drawer_state()
        self._refresh_content()

    def _unlock_line(self, line_id: str, expected_cost=None) -> None:
        hall=self._units[self._selected_hall_id]
        line=next(line for line in hall.production_lines if line.line_id==line_id)
        quoted=unit_line_price(hall,hall.production_lines.index(line)+1,self._board_config.board_kind) if expected_cost is None else expected_cost
        self._command_bus.dispatch(UnlockProductionLine(self._selected_hall_id, line_id, self._board_config.board_kind,quoted))
        self._refresh_hall_tree()
        self._refresh_content()

    def _unlock_slot(self, line_id: str, expected_cost=None) -> None:
        hall=self._units[self._selected_hall_id]
        line=next(line for line in hall.production_lines if line.line_id==line_id)
        quoted=unit_slot_price(hall,hall.production_lines.index(line)+1,len(line.slot_indexes)+1,self._board_config.board_kind) if expected_cost is None else expected_cost
        self._command_bus.dispatch(UnlockProductionSlot(self._selected_hall_id, line_id, self._board_config.board_kind,quoted))
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
                f"Type: {definition.name}\n"
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
                f"Rarity: {card.rarity.value.title()}\n"
                f"Bonus: +{card.output_bonus_percent:.1f}%\n"
                f"Power Output: {definition.base_power_output:.0f}\n"
                f"Fuel: none"
            )
        return self._card_list_text(card)
