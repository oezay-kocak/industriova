from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
)

from production_zero.core.cards import CardInstance
from production_zero.core.commands import AssignFreightCard, BuildFreightFacility, CancelFreightCardAssignment, CommandBus, ExpandFreightFacility, InstallFreightCard, RemoveFreightCard, UpdateFreightReserve
from production_zero.core.definitions import CardDefinition, FreightDefinition
from production_zero.core.enums import CardKind
from production_zero.core.freight import (
    FREIGHT_FACILITY_EXPANSION_BASE_COST,
    FREIGHT_FACILITY_EXPANSION_COST_STEP,
    FREIGHT_FACILITY_EXPANSION_SLOTS,
    FREIGHT_FACILITY_START_SLOTS,
    FREIGHT_FACILITY_TYPES,
    OutboundFreightShipment,
    freight_facility_build_cost,
    freight_stats,
    is_freight_card_busy,
)
from production_zero.ui.factory_view_v2 import (
    FactoryV2ActiveIndicator,
    FactoryV2Board,
    FACTORY_V2_CARD_HEIGHT,
    FACTORY_V2_CARD_WIDTH,
    FactoryV2HallOverview,
    FactoryV2LinePlate,
    FactoryV2TrackPanel,
)
from production_zero.ui.game_ui.rendering import draw_build_slot, draw_locked_slot, draw_machine_card_prototype, draw_status_badge
from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.widget_lifecycle import clear_layout_safely


FACILITY_TYPE_ORDER = ("garage_depot", "rail_station", "harbor", "airport")
DESTINATION_LABELS = {"market": "Market", "contract": "Contract"}
FREIGHT_ICON_KEYS = {
    "truck": ("vehicle", "vehicle"),
    "train": ("rail", "rail"),
    "ship": ("ship", "ship"),
    "aircraft": ("aircraft", "aircraft"),
}
FREIGHT_SLOT_CARD_WIDTH = 166
FREIGHT_SLOT_CARD_HEIGHT = 264
FREIGHT_SLOT_GRID_SPACING = 10


class ClickableFreightSlotCard(QFrame):
    activated = Signal()
    hovered = Signal()
    unhovered = Signal()

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setProperty("clickEnabled", enabled)

    def paintEvent(self, event) -> None:  # noqa: N802
        slot_state = self.property("slotState")
        if slot_state in {"empty", "locked", "installed"}:
            painter = QPainter(self)
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
                if slot_state == "empty":
                    draw_build_slot(painter, rect, hover=self.underMouse(), pressed=False)
                    font = GAME_UI_TOKENS.typography.industrial_title()
                    font.setPointSize(13)
                    painter.setFont(font)
                    painter.setPen(QColor(GAME_UI_TOKENS.colors.safety_yellow))
                    painter.drawText(
                        QRectF(rect.left() + 10, rect.top() + rect.height() * 0.61, rect.width() - 20, 24),
                        Qt.AlignmentFlag.AlignCenter,
                        "BUILD SLOT",
                    )
                elif slot_state == "locked":
                    module = draw_locked_slot(painter, rect, enabled=bool(self.property("unlockEnabled")))
                    font = GAME_UI_TOKENS.typography.industrial_title()
                    font.setPointSize(17)
                    painter.setFont(font)
                    painter.setPen(QColor("#eff8f4"))
                    slot_number = int(self.property("slotIndex") or 0) + 1
                    painter.drawText(
                        QRectF(module.left() + 8, module.top() + module.height() * 0.54, module.width() - 16, 28),
                        Qt.AlignmentFlag.AlignCenter,
                        f"S{slot_number:02d}",
                    )
                    font = GAME_UI_TOKENS.typography.micro_label()
                    font.setPointSize(12)
                    font.setWeight(font.Weight.Black)
                    painter.setFont(font)
                    painter.setPen(QColor(GAME_UI_TOKENS.colors.warning_orange))
                    painter.drawText(
                        QRectF(module.left() + 8, module.top() + module.height() * 0.68, module.width() - 16, 24),
                        Qt.AlignmentFlag.AlignCenter,
                        f"${float(self.property('unlockCost') or 0):.0f}",
                    )
                else:
                    card_rect = rect.adjusted(5, 11, -5, -9)
                    draw_machine_card_prototype(
                        painter,
                        card_rect,
                        title=str(self.property("cardTitle") or "FREIGHT"),
                        family=str(self.property("freightFamily") or "transport"),
                        meta=str(self.property("cardMeta") or ""),
                        detail="",
                        secondary="",
                        active=str(self.property("cardStatus") or "").lower() in {"ready", "in_transit"},
                        hover=self.underMouse(),
                    )
                    self._draw_installed_freight_content(painter, card_rect)
                    status_rect, _utility_rect = self._installed_footer_rects(card_rect)
                    draw_status_badge(
                        painter,
                        status_rect,
                        text=str(self.property("cardStatusText") or "UNASSIGNED"),
                        accent=self.property("cardStatusAccent") or Accent.NEUTRAL,
                    )
            finally:
                painter.end()
            if slot_state != "installed":
                return
        super().paintEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.property("slotState") == "installed":
            self._position_installed_controls()

    def _position_installed_controls(self) -> None:
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2).adjusted(5, 11, -5, -9)
        action = self._installed_route_rect(rect).toRect()
        if panel := self.findChild(QFrame, "freightAssignmentPanel"):
            panel.setGeometry(action)
        if shipment := self.findChild(QFrame, "freightShipmentPanel"):
            shipment.setGeometry(0, 0, 1, 1)
        if remove := self.findChild(QPushButton, "freightRemoveButton"):
            _status_rect, utility_rect = self._installed_footer_rects(rect)
            remove.setGeometry(utility_rect.toRect())

    def _installed_art_rect(self, rect: QRectF) -> QRectF:
        return QRectF(rect.left() + 14, rect.top() + 54, rect.width() - 28, rect.height() * 0.43)

    def _installed_capacity_rect(self, rect: QRectF) -> QRectF:
        art = self._installed_art_rect(rect)
        return QRectF(rect.left() + 14, art.bottom() + 5, rect.width() - 28, 10)

    def _installed_route_rect(self, rect: QRectF) -> QRectF:
        art = self._installed_art_rect(rect)
        return QRectF(rect.left() + 7, art.bottom() + 20, rect.width() - 14, 18)

    def _installed_progress_rect(self, rect: QRectF) -> QRectF:
        route = self._installed_route_rect(rect)
        return QRectF(rect.left() + 14, route.bottom() + 8, rect.width() - 28, 9)

    def _installed_footer_rects(self, rect: QRectF) -> tuple[QRectF, QRectF]:
        footer_top = rect.bottom() - 28
        utility = QRectF(rect.right() - 58, footer_top + 1, 47, 17)
        status = QRectF(rect.left() + 8, footer_top, utility.left() - rect.left() - 14, 17)
        return status, utility

    def _draw_installed_freight_content(self, painter: QPainter, rect: QRectF) -> None:
        family = str(self.property("freightFamily") or "transport")
        family_color = {
            "truck": QColor(GAME_UI_TOKENS.colors.safety_yellow),
            "train": QColor(GAME_UI_TOKENS.colors.processor),
            "ship": QColor(GAME_UI_TOKENS.colors.storage),
            "aircraft": QColor("#9bb8ef"),
        }.get(family, QColor(GAME_UI_TOKENS.colors.storage))
        family_color.setAlpha(190)
        capacity = self._installed_capacity_rect(rect)
        font = GAME_UI_TOKENS.typography.micro_label()
        font.setPointSize(7)
        font.setWeight(font.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor("#dfe9e4"))
        painter.drawText(capacity, Qt.AlignmentFlag.AlignCenter, str(self.property("cardDetail") or "").upper())

        route = self._installed_route_rect(rect)
        body = QLinearGradient(route.topLeft(), route.bottomLeft())
        body.setColorAt(0.0, QColor(255, 255, 246, 24))
        body.setColorAt(0.46, QColor(7, 10, 10, 176))
        body.setColorAt(1.0, QColor(0, 0, 0, 138))
        painter.setPen(QPen(family_color, 1))
        painter.setBrush(body)
        painter.drawRoundedRect(route, 5, 5)

        route_font = GAME_UI_TOKENS.typography.micro_label()
        route_font.setPointSize(6)
        route_font.setWeight(route_font.Weight.Black)
        painter.setFont(route_font)
        painter.setPen(QColor("#eff8f4"))
        painter.drawText(route.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignCenter, str(self.property("cardSecondary") or "").upper())
        if bool(self.property("shipmentActive")):
            progress = self._installed_progress_rect(rect)
            painter.setPen(QPen(QColor(0, 0, 0, 190), 1))
            painter.setBrush(QColor(3, 5, 5, 160))
            painter.drawRoundedRect(progress, 3, 3)
            ratio = max(0.0, min(1.0, float(self.property("shipmentProgress") or 0.0)))
            if ratio > 0.0:
                fill = QRectF(progress.left() + 1, progress.top() + 1, max(2.0, (progress.width() - 2) * ratio), progress.height() - 2)
                fill_color = QColor(GAME_UI_TOKENS.colors.success)
                fill_color.setAlpha(205)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(fill_color)
                painter.drawRoundedRect(fill, 2.5, 2.5)
                painter.setPen(QPen(QColor(255, 255, 255, 48), 1))
                painter.drawLine(
                    QPointF(fill.left() + fill.width() * 0.06, fill.top() + fill.height() * 0.28),
                    QPointF(fill.left() + fill.width() * 0.94, fill.top() + fill.height() * 0.28),
                )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.property("clickEnabled") and event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self.property("clickEnabled") and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.unhovered.emit()
        super().leaveEvent(event)


class FreightFacilityStage(QFrame):
    def __init__(self, facility, state: GameState) -> None:
        super().__init__()
        self._facility = facility
        self._state = state
        self.setObjectName("freightFacilityHeader")
        self.setMinimumHeight(140)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setProperty("facilityTitle", facility.name.upper())
        occupied = sum(1 for slot in facility.slots if slot.card_id is not None)
        active_shipments = sum(1 for shipment in state.freight.outbound_shipments.values() if shipment.active)
        self.setProperty("facilityMeta", f"{occupied} / {len(facility.slots)} slots   ·   {active_shipments} active shipments")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
            header_panel = rect.adjusted(16, 14, -16, -14)
            occupied = sum(1 for slot in self._facility.slots if slot.card_id is not None)
            active_shipments = sum(1 for shipment in self._state.freight.outbound_shipments.values() if shipment.active)
            self.setProperty("facilityTitle", self._facility.name.upper())
            self.setProperty("facilityMeta", f"{occupied} / {len(self._facility.slots)} slots   ·   {active_shipments} active shipments")

            font = GAME_UI_TOKENS.typography.brand_display()
            font.setPointSize(40)
            painter.setFont(font)
            painter.setPen(QColor("#eff8f4"))
            painter.drawText(
                header_panel.adjusted(20, 14, -18, -20),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                self.property("facilityTitle"),
            )

            font = GAME_UI_TOKENS.typography.industrial_label()
            font.setPointSize(12)
            painter.setFont(font)
            painter.setPen(QColor("#9fb2ad"))
            painter.drawText(
                header_panel.adjusted(22, 74, -18, -12),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                self.property("facilityMeta"),
            )
        finally:
            painter.end()


class FreightSelectionCard(QFrame):
    selected = Signal(str)
    hovered = Signal(str)
    unhovered = Signal()

    def __init__(self, freight_card: CardInstance, definition: FreightDefinition, quantity: int) -> None:
        super().__init__()
        self._card_id = freight_card.card_id
        self.setObjectName("freightSelectionCard")
        self.setProperty("cardId", freight_card.card_id)
        self.setProperty("freightFamily", definition.family.value)
        self.setProperty("rarity", freight_card.rarity.value)
        self.setProperty("quantity", quantity)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(164, 164)
        self.setMaximumSize(196, 196)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(4)
        name = SmartCardTitleLabel(definition.name, uppercase_display=True)
        name.setObjectName("freightSelectionName")
        name.setWordWrap(True)
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(name)
        rarity = QLabel(freight_card.rarity.value.upper())
        rarity.setObjectName("freightSelectionRarity")
        rarity.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(rarity)
        rarity_line = QFrame()
        rarity_line.setObjectName("freightRarityLine")
        rarity_line.setProperty("rarity", freight_card.rarity.value)
        rarity_line.setFixedHeight(2)
        rarity_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(rarity_line)
        icon_key, accent_key = FREIGHT_ICON_KEYS.get(definition.family.value, ("vehicle", "vehicle"))
        icon = ResourceIconWidget(definition.definition_id, icon_key, accent_key, size=58)
        icon.setObjectName("freightTypeIcon")
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        layout.addLayout(icon_row)
        layout.addSpacing(3)
        family = QLabel(definition.family.value.upper())
        family.setObjectName("freightSelectionFamily")
        family.setAlignment(Qt.AlignmentFlag.AlignCenter)
        family.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(family)
        bottom = QHBoxLayout()
        bonus = QLabel(f"+{freight_card.output_bonus_percent:.1f}%")
        bonus.setObjectName("freightSelectionMeta")
        bonus.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        count = QLabel(f"x{quantity}")
        count.setObjectName("freightSelectionMeta")
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


class ClickableAssignmentPanel(QFrame):
    activated = Signal()

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setProperty("clickEnabled", enabled)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.property("clickEnabled") and event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if self.property("clickEnabled") and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit()
            return
        super().keyPressEvent(event)


class FreightAssignmentResourceTile(QFrame):
    selected = Signal(str)

    def __init__(self, resource_id: str, resource: ResourceDefinition, stock_amount: float, stock_capacity: float) -> None:
        super().__init__()
        self._resource_id = resource_id
        self.setObjectName("freightAssignmentResourceTile")
        self.setProperty("resourceId", resource_id)
        self.setProperty("category", resource.category or "General")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(148, 148)
        self.setMaximumSize(190, 190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 10, 11, 10)
        layout.setSpacing(6)
        icon = ResourceIconWidget(resource_id, resource.icon_key or resource_icon_key(resource_id), resource.accent_key or resource_accent_key(resource_id), size=56)
        icon.setObjectName("freightAssignmentResourceIcon")
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        layout.addLayout(icon_row)
        name = QLabel(resource.name.upper())
        name.setObjectName("freightAssignmentTileName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(name)
        category = QLabel((resource.category or "General").upper())
        category.setObjectName("freightAssignmentTileMeta")
        category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        category.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(category)
        storage = QLabel(f"{stock_amount:.0f} / {stock_capacity:.0f}")
        storage.setObjectName("freightAssignmentTileMeta")
        storage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        storage.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(storage)

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


class FreightDestinationTile(QFrame):
    selected = Signal(str)

    def __init__(self, destination_kind: str, title: str, body: str) -> None:
        super().__init__()
        self._destination_kind = destination_kind
        self.setObjectName("freightDestinationTile")
        self.setProperty("destinationKind", destination_kind)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        label = QLabel(title.upper())
        label.setObjectName("freightDestinationTileTitle")
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        details = QLabel(body)
        details.setObjectName("freightDestinationTileBody")
        details.setWordWrap(True)
        details.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(label)
        layout.addWidget(details)
        layout.addStretch(1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self._destination_kind)
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.selected.emit(self._destination_kind)
            return
        super().keyPressEvent(event)


class FreightView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        resources: dict[str, ResourceDefinition],
    ) -> None:
        super().__init__()
        self._state = state
        self._command_bus = command_bus
        self._definitions = definitions
        self._resources = resources
        self._selected_facility_id = next(iter(state.freight.facilities), "garage-1")
        self._build_facility_type = "garage_depot"
        self._drawer_open = False
        self._drawer_slot_index: int | None = None
        self._selected_card_id: str | None = None
        self._search_text = ""
        self._class_filter = "All"
        self._rarity_filter = "All"
        self._assignment_card_id: str | None = None
        self._assignment_resource_id: str | None = None
        self._assignment_destination_kind: str | None = None
        self._assignment_search_text = ""
        self._assignment_category_filter = "All"
        self._assignment_reserve_percent = 100
        self._assignment_resource_grid: QGridLayout | None = None
        self._hover_card_id: str | None = None
        self._hover_popup: CardHoverInfoPopup | None = None
        self._kpi_values: dict[str, QLabel] = {}
        self._runtime_widgets: dict[str, dict[str, QWidget | None]] = {}
        self._selection_grid: QGridLayout | None = None
        self._facility_tree: QTreeWidget | None = None

        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(14)
        self.refresh()

    def refresh(self) -> None:
        self._hide_freight_hover()
        self._kpi_values = {}
        self._runtime_widgets = {}
        self._clear_layout(self._root)
        self._root.addWidget(self._build_facility_list(), 0)
        self._root.addWidget(self._build_slots_panel(), 1)

    def refresh_runtime(self) -> None:
        self._update_kpis()
        for card_id, widgets in list(self._runtime_widgets.items()):
            self._update_card_runtime(card_id, widgets)

    def _facility_usage_label(self, facility) -> str:
        installed = sum(1 for slot in facility.slots if slot.card_id is not None)
        return f"{installed} / {len(facility.slots)}"

    def _facility_nav_label(self, facility) -> str:
        active_shipments = sum(1 for shipment in self._state.freight.outbound_shipments.values() if shipment.active)
        return f"{facility.name}\n{self._facility_usage_label(facility)} slots · {active_shipments} shipments"

    def _facility_plate_label(self, facility) -> str:
        label = FREIGHT_FACILITY_TYPES.get(facility.facility_type)
        return (label or facility.name).upper()

    def _build_facility_list(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightFacilityPanel")
        panel.setFixedWidth(258)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        title = QLabel("FREIGHT")
        title.setObjectName("factoryV2NavTitle")
        subtitle = QLabel("FACILITIES")
        subtitle.setObjectName("factoryV2NavSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        tree = QTreeWidget()
        tree.setObjectName("freightFacilityTreeV2")
        tree.setHeaderHidden(True)
        tree.setRootIsDecorated(False)
        tree.setColumnCount(1)
        tree.setFixedWidth(238)
        for facility_id, facility in self._sorted_facilities():
            item = QTreeWidgetItem([self._facility_nav_label(facility)])
            item.setData(0, Qt.ItemDataRole.UserRole, facility_id)
            tree.addTopLevelItem(item)
            if facility_id == self._selected_facility_id:
                tree.setCurrentItem(item)
        tree.currentItemChanged.connect(lambda current, previous=None: self._select_facility_from_item(current))
        self._facility_tree = tree
        layout.addWidget(tree, 1)

        build_title = QLabel("BUILD FACILITY")
        build_title.setObjectName("sectionLabel")
        layout.addWidget(build_title)
        build_type = QComboBox()
        build_type.setObjectName("freightBuildFacilityType")
        for facility_type in FACILITY_TYPE_ORDER:
            build_type.addItem(FREIGHT_FACILITY_TYPES[facility_type], facility_type)
        self._set_combo_data(build_type, self._build_facility_type)
        build_type.currentIndexChanged.connect(lambda index, combo=build_type: self._set_build_facility_type(combo.currentData()))
        layout.addWidget(build_type)
        build = QPushButton(f"BUILD SITE (${freight_facility_build_cost(self._state.freight, self._build_facility_type):.0f})")
        build.setObjectName("buildFreightFacilityButton")
        build.clicked.connect(lambda checked=False: self._build_facility())
        layout.addWidget(build)
        return panel

    def _build_slots_panel(self) -> QFrame:
        if self._assignment_card_id is not None:
            return self._build_assignment_selection_view()
        if self._drawer_open:
            return self._build_card_selection_view()
        panel = FactoryV2Board()
        panel.setObjectName("freightSlotsPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        if self._selected_facility_id not in self._state.freight.facilities:
            self._selected_facility_id = next(iter(self._state.freight.facilities))
        facility = self._state.freight.facilities[self._selected_facility_id]
        overview = FactoryV2HallOverview()
        overview.setObjectName("freightFacilityOverview")
        overview_layout = QHBoxLayout(overview)
        overview_layout.setContentsMargins(14, 12, 14, 12)
        overview_layout.setSpacing(12)
        overview_layout.addWidget(FreightFacilityStage(facility, self._state), 1)
        layout.addWidget(overview)

        bay_panel = FactoryV2TrackPanel(1, "Bay")
        bay_panel.setObjectName("freightBayTrack")
        bay_panel.setProperty("trackAccentActive", False)
        bay_layout = QVBoxLayout(bay_panel)
        bay_layout.setContentsMargins(14, 12, 14, 14)
        bay_layout.setSpacing(6)
        bay_header = QHBoxLayout()
        bay_label = FactoryV2LinePlate(self._facility_plate_label(facility))
        bay_label.setObjectName("freightBayPlate")
        bay_status = FactoryV2ActiveIndicator()
        bay_status.setObjectName("freightBayStatus")
        bay_header.addWidget(bay_label)
        bay_header.addStretch(1)
        bay_header.addWidget(bay_status)
        bay_layout.addLayout(bay_header)
        scroll = QScrollArea()
        scroll.setObjectName("freightSlotsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("freightSlotGridHost")
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(FREIGHT_SLOT_GRID_SPACING)
        locked_slots = self._locked_slot_specs(facility)
        slot_count = len(facility.slots) + len(locked_slots)
        columns = max(1, slot_count)
        for column in range(columns):
            grid.setColumnMinimumWidth(column, FREIGHT_SLOT_CARD_WIDTH)
        for index, slot in enumerate(facility.slots):
            grid.addWidget(
                self._build_slot_card(slot.index, slot.card_id),
                index // columns,
                index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        for offset, spec in enumerate(locked_slots):
            index = len(facility.slots) + offset
            grid.addWidget(
                self._build_locked_slot_card(*spec),
                index // columns,
                index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        grid.setColumnStretch(columns, 1)
        scroll.setWidget(content)
        bay_layout.addWidget(scroll, 1)
        layout.addWidget(bay_panel, 1)
        return panel

    def _build_slot_card(self, slot_index: int, card_id: str | None) -> QFrame:
        card = ClickableFreightSlotCard(enabled=card_id is None)
        card.setObjectName("freightSlotCard")
        card.setProperty("slotIndex", slot_index)
        card.setProperty("slotState", "empty" if card_id is None else "installed")
        card.setFixedSize(FREIGHT_SLOT_CARD_WIDTH, FREIGHT_SLOT_CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if card_id is None:
            card.activated.connect(lambda idx=slot_index: self._open_drawer(idx))
            return card

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        freight_card = self._state.cards[card_id]
        definition = self._definitions.get(freight_card.definition_id)
        shipment = self._active_shipment_for(card_id)
        busy = shipment is not None
        assignment = self._state.freight.assignments.get(card_id)
        status = self._status_text(assignment, shipment)

        if isinstance(definition, FreightDefinition):
            card.setProperty("freightFamily", definition.family.value)
            card.setProperty("rarity", freight_card.rarity.value)
            stats = freight_stats(freight_card, definition)
            route_label = "ASSIGN ROUTE >"
            if assignment is not None:
                resource = self._resources.get(assignment.resource_id)
                resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
                route_label = f"ROUTE: {resource_name} > {DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind)}"
            card.setProperty("cardTitle", self._freight_card_title(definition))
            card.setProperty("cardMeta", f"{self._freight_card_tier_label(definition)} · {freight_card.rarity.value.upper()}")
            card.setProperty("cardDetail", f"CAPACITY {stats.capacity:.0f}")
            card.setProperty("cardSecondary", route_label.upper())
            card.setProperty("cardStatus", status.lower().replace(" ", "_"))
            card.setProperty("cardStatusText", self._compact_status_text(status))
            card.setProperty("cardStatusAccent", self._freight_status_accent(status))
            card.setProperty("cardUtilityText", "CANCEL" if busy or assignment is not None else "REMOVE")
            self._set_shipment_progress_properties(card, shipment)
            card.hovered.connect(lambda cid=card_id, widget=card: self._show_freight_hover(cid, widget))
            card.unhovered.connect(self._hide_freight_hover)
        raw_name = definition.name if isinstance(definition, FreightDefinition) else freight_card.definition_id
        name = SmartCardTitleLabel(raw_name)
        name.setObjectName("freightCardName")
        name.setWordWrap(True)
        name.setVisible(False)
        status_label = QLabel(self._compact_status_text(status))
        status_label.setObjectName("freightStatusLabel")
        status_label.setProperty("detailStatus", status)
        status_label.setProperty("status", status.lower().replace(" ", "_"))
        status_label.setVisible(False)
        header = QHBoxLayout()
        header.addWidget(name, 1)
        header.addWidget(status_label, 0)
        layout.addLayout(header)

        if isinstance(definition, FreightDefinition):
            rarity_line = QFrame()
            rarity_line.setObjectName("freightRarityLine")
            rarity_line.setProperty("rarity", freight_card.rarity.value)
            rarity_line.setFixedHeight(2)
            rarity_line.setVisible(False)
            layout.addWidget(rarity_line)
            icon_key, accent_key = FREIGHT_ICON_KEYS.get(definition.family.value, ("vehicle", "vehicle"))
            icon = ResourceIconWidget(definition.definition_id, icon_key, accent_key, size=36)
            icon.setObjectName("freightTypeIcon")
            icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            icon.setVisible(False)
            icon_row = QHBoxLayout()
            icon_row.addWidget(icon)
            meta = QVBoxLayout()
            class_label = QLabel(definition.class_label.upper())
            class_label.setObjectName("freightCardClass")
            class_label.setVisible(False)
            rarity_label = QLabel(freight_card.rarity.value.upper())
            rarity_label.setObjectName("freightCardRarity")
            rarity_label.setVisible(False)
            meta.addWidget(class_label)
            meta.addWidget(rarity_label)
            icon_row.addLayout(meta, 1)
            layout.addLayout(icon_row)

        assignment_panel = self._assignment_panel(card_id, assignment, True)
        assignment_panel.setParent(card)

        shipment_panel, shipment_widgets = self._shipment_panel(shipment)
        shipment_panel.setParent(card)

        remove = QPushButton("CANCEL" if busy or assignment is not None else "REMOVE")
        remove.setObjectName("freightRemoveButton")
        remove.setProperty("freightCardSecondary", True)
        remove.setFixedHeight(16)
        if busy or assignment is not None:
            remove.clicked.connect(lambda checked=False, cid=card_id: self._clear_card_assignment(cid))
        else:
            remove.clicked.connect(lambda checked=False, idx=slot_index: self._remove_card(idx))
        remove.setParent(card)
        card._position_installed_controls()
        self._runtime_widgets[card_id] = {
            "card": card,
            "status": status_label,
            "remove": remove,
            "assignment_panel": assignment_panel,
            **shipment_widgets,
        }
        return card

    def _build_locked_slot_card(self, slot_index: int, cost: float, enabled: bool, unlock_enabled: bool) -> QFrame:
        card = ClickableFreightSlotCard(enabled=enabled)
        card.setObjectName("freightSlotCard")
        card.setProperty("slotIndex", slot_index)
        card.setProperty("slotState", "locked")
        card.setProperty("unlockCost", cost)
        card.setProperty("unlockEnabled", unlock_enabled)
        card.setFixedSize(FREIGHT_SLOT_CARD_WIDTH, FREIGHT_SLOT_CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if enabled:
            card.activated.connect(lambda: self._expand_facility())
        return card

    def _locked_slot_specs(self, facility) -> list[tuple[int, float, bool, bool]]:
        unlockable_slots = sum(FREIGHT_FACILITY_EXPANSION_SLOTS.get(facility.facility_type, ()))
        start_slots = FREIGHT_FACILITY_START_SLOTS.get(facility.facility_type, 3)
        unlocked_extra_slots = max(0, len(facility.slots) - start_slots)
        specs: list[tuple[int, float, bool, bool]] = []
        slot_index = len(facility.slots)
        for extra_slot in range(unlocked_extra_slots, unlockable_slots):
            cost = FREIGHT_FACILITY_EXPANSION_BASE_COST + extra_slot * FREIGHT_FACILITY_EXPANSION_COST_STEP
            is_next_slot = extra_slot == unlocked_extra_slots
            can_buy_next = is_next_slot and self._state.cash.amount >= cost
            specs.append((slot_index, cost, can_buy_next, is_next_slot))
            slot_index += 1
        return specs

    def _slot_grid_columns(self, slot_count: int) -> int:
        available_width = self.width() - 260 if self.width() > 320 else 1180
        slot_pitch = FREIGHT_SLOT_CARD_WIDTH + FREIGHT_SLOT_GRID_SPACING
        columns = max(2, min(slot_count, available_width // slot_pitch))
        return max(1, columns)

    def _assignment_panel(self, card_id: str, assignment, enabled: bool) -> QFrame:
        panel = ClickableAssignmentPanel(enabled=enabled)
        panel.setObjectName("freightAssignmentPanel")
        panel.setProperty("cardId", card_id)
        panel.setProperty("paintedFreightControl", True)
        panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        panel.setAutoFillBackground(False)
        panel.activated.connect(lambda cid=card_id: self._open_assignment_view(cid))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if assignment is None:
            empty = QLabel("ASSIGN ROUTE")
            empty.setObjectName("freightAssignmentEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setVisible(False)
            layout.addWidget(empty, 1)
            return panel

        resource = self._resources.get(assignment.resource_id)
        resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
        route_row = QHBoxLayout()
        route_row.setContentsMargins(0, 0, 0, 0)
        route_row.setSpacing(4)
        resource_label = QLabel(resource_name.upper())
        resource_label.setObjectName("freightAssignmentResource")
        resource_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        resource_label.setVisible(False)
        reserve_label = QLabel(
            f"Reserve {assignment.reserve_percent:.0f}%"
            if assignment.destination_kind == "market"
            else ""
        )
        reserve_label.setObjectName("freightReserveSummary")
        reserve_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        reserve_label.setVisible(False)
        arrow = QLabel(">")
        arrow.setObjectName("freightAssignmentArrow")
        arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        arrow.setVisible(False)
        destination = QLabel(DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind).upper())
        destination.setObjectName("freightAssignmentDestination")
        destination.setVisible(False)
        route_row.addWidget(resource_label, 1)
        route_row.addWidget(arrow)
        route_row.addWidget(destination)
        layout.addLayout(route_row)
        if assignment.destination_kind == "market":
            layout.addWidget(reserve_label)
        return panel

    def _shipment_panel(self, shipment: OutboundFreightShipment | None) -> tuple[QFrame, dict[str, QWidget]]:
        panel = QFrame()
        panel.setObjectName("freightShipmentPanel")
        panel.setMinimumHeight(44)
        panel.setMaximumHeight(52)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(3)
        route = self._meta_label("")
        quantity = self._meta_label("")
        remaining = self._meta_label("")
        layout.addWidget(route)
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.addWidget(quantity)
        meta_row.addStretch(1)
        meta_row.addWidget(remaining)
        layout.addLayout(meta_row)
        progress = QProgressBar()
        progress.setObjectName("freightShipmentProgress")
        progress.setRange(0, 1000)
        progress.setFixedHeight(6)
        layout.addWidget(progress)
        widgets = {
            "shipment_panel": panel,
            "shipment_route": route,
            "shipment_quantity": quantity,
            "shipment_remaining": remaining,
            "shipment_progress": progress,
        }
        self._update_shipment_widgets(widgets, shipment)
        return panel, widgets

    def _build_assignment_selection_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightAssignmentSelectionView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("FREIGHT ASSIGNMENT")
        title.setObjectName("sectionLabel")
        target = QLabel(self._assignment_target_label())
        target.setObjectName("freightSelectionTarget")
        close = QPushButton("Back")
        close.setObjectName("freightAssignmentBackButton")
        close.clicked.connect(lambda checked=False: self._close_assignment_view())
        header.addWidget(title)
        header.addWidget(target)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        if self._assignment_resource_id is None:
            layout.addWidget(self._build_assignment_resource_picker(), 1)
        else:
            layout.addWidget(self._build_market_assignment_editor(), 1)
        return panel

    def _build_assignment_resource_picker(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        title = QLabel("SELECT CARGO RESOURCE")
        title.setObjectName("freightAssignmentStepTitle")
        layout.addWidget(title)

        filters = QFrame()
        filters.setObjectName("freightSelectionFilters")
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(8)
        search = QLineEdit()
        search.setObjectName("freightAssignmentSearch")
        search.setPlaceholderText("Search resources...")
        search.setText(self._assignment_search_text)
        search.textChanged.connect(self._set_assignment_search)
        filters_layout.addWidget(search, 2)
        category = QComboBox()
        category.setObjectName("freightAssignmentCategoryFilter")
        category.addItem("All")
        for value in self._assignment_categories():
            category.addItem(value)
        self._set_combo_text(category, self._assignment_category_filter)
        category.currentTextChanged.connect(self._set_assignment_category_filter)
        filters_layout.addWidget(category)
        layout.addWidget(filters)

        grid_host = QWidget()
        grid_host.setObjectName("freightAssignmentResourceGridHost")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._assignment_resource_grid = grid
        self._populate_assignment_resource_grid()
        scroll = QScrollArea()
        scroll.setObjectName("freightAssignmentResourceScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)
        return wrapper

    def _build_market_assignment_editor(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        resource = self._resources.get(self._assignment_resource_id or "")
        resource_name = resource.name if resource is not None else (self._assignment_resource_id or "Unknown")
        title_row = QHBoxLayout()
        title = QLabel(f"MARKET ROUTE · {resource_name.upper()}")
        title.setObjectName("freightAssignmentStepTitle")
        change = QPushButton("Change Resource")
        change.setObjectName("freightAssignmentChangeResourceButton")
        change.setEnabled(not self._assignment_card_is_busy())
        change.clicked.connect(lambda checked=False: self._reset_assignment_resource_step())
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(change)
        layout.addLayout(title_row)
        hint = QLabel("Ship excess cargo to Market. Matching contracts are filled automatically on delivery.")
        hint.setObjectName("freightAssignmentHint")
        layout.addWidget(hint)
        layout.addWidget(self._build_market_reserve_panel())
        layout.addStretch(1)
        return wrapper

    def _build_market_reserve_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightAssignmentReservePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("MARKET RESERVE")
        title.setObjectName("freightAssignmentStepTitle")
        value = QLabel(f"{self._assignment_reserve_percent}%")
        value.setObjectName("freightAssignmentReserveValue")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(value)
        layout.addLayout(header)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("freightAssignmentReserveSlider")
        slider.setRange(0, 100)
        slider.setValue(self._assignment_reserve_percent)
        slider.valueChanged.connect(lambda new_value, label=value: self._set_assignment_reserve(new_value, label))
        layout.addWidget(slider)
        help_text = QLabel("Keep this percentage in storage.\nOnly excess cargo is shipped to Market.")
        help_text.setObjectName("freightAssignmentHint")
        layout.addWidget(help_text)
        apply = QPushButton("Save Market Route" if self._state.freight.assignments.get(self._assignment_card_id or "") else "Assign Market Route")
        apply.setObjectName("freightApplyMarketAssignmentButton")
        apply.clicked.connect(lambda checked=False: self._apply_assignment("market"))
        layout.addWidget(apply)
        return panel

    def _build_contract_assignment_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightAssignmentContractPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        title = QLabel("MATCHING ACTIVE CONTRACTS")
        title.setObjectName("freightAssignmentStepTitle")
        layout.addWidget(title)
        contracts = self._matching_contracts_for_assignment()
        if not contracts:
            empty = QLabel("No active contract currently needs this resource.")
            empty.setObjectName("freightAssignmentEmptyState")
            layout.addWidget(empty)
            layout.addStretch(1)
            return panel
        for kind, active, remaining in contracts:
            tile = QFrame()
            tile.setObjectName("freightContractAssignmentTile")
            tile.setProperty("contractKind", kind)
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(10, 8, 10, 8)
            name = QLabel(f"{active.offer.name} · {kind.upper()}")
            name.setObjectName("freightContractAssignmentName")
            detail = QLabel(f"Remaining {remaining:.0f} · Reward ${active.offer.reward_cash:.0f}")
            detail.setObjectName("freightContractAssignmentDetail")
            button = QPushButton("Assign Contract Route")
            button.setObjectName("freightApplyContractAssignmentButton")
            button.clicked.connect(lambda checked=False: self._apply_assignment("contract"))
            tile_layout.addWidget(name, 2)
            tile_layout.addWidget(detail, 1)
            tile_layout.addWidget(button)
            layout.addWidget(tile)
        layout.addStretch(1)
        return panel

    def _build_card_selection_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightCardSelectionView")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("FREIGHT CARD SELECTION")
        title.setObjectName("sectionLabel")
        target = QLabel(f"Target Slot {self._drawer_slot_index + 1 if self._drawer_slot_index is not None else '-'}")
        target.setObjectName("freightSelectionTarget")
        close = QPushButton("Back")
        close.setObjectName("freightCloseDrawerButton")
        close.clicked.connect(lambda checked=False: self._close_drawer())
        header.addWidget(title)
        header.addWidget(target)
        header.addStretch(1)
        header.addWidget(close)
        layout.addLayout(header)

        filters_panel = QFrame()
        filters_panel.setObjectName("freightSelectionFilters")
        filters_layout = QHBoxLayout(filters_panel)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(8)
        search = QLineEdit()
        search.setObjectName("freightCardSearch")
        search.setPlaceholderText("Search freight cards...")
        search.setText(self._search_text)
        search.textChanged.connect(self._set_search)
        filters_layout.addWidget(search, 2)

        class_filter = QComboBox()
        class_filter.setObjectName("freightClassFilter")
        class_filter.addItem("All")
        for class_label in sorted({definition.class_label for definition in self._freight_definitions_for_selected_facility()}):
            class_filter.addItem(class_label)
        self._set_combo_text(class_filter, self._class_filter)
        class_filter.currentTextChanged.connect(self._set_class_filter)
        rarity_filter = QComboBox()
        rarity_filter.setObjectName("freightRarityFilter")
        for value in ("All", "Common", "Uncommon", "Rare", "Epic", "Legendary"):
            rarity_filter.addItem(value)
        self._set_combo_text(rarity_filter, self._rarity_filter)
        rarity_filter.currentTextChanged.connect(self._set_rarity_filter)
        filters_layout.addWidget(class_filter)
        filters_layout.addWidget(rarity_filter)
        layout.addWidget(filters_panel)

        grid_host = QWidget()
        grid_host.setObjectName("freightSelectionGridHost")
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._selection_grid = grid
        self._populate_selection_grid()
        scroll = QScrollArea()
        scroll.setObjectName("freightCardSelectionScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, 1)
        return panel

    def _populate_selection_grid(self) -> None:
        if self._selection_grid is None:
            return
        self._clear_layout(self._selection_grid)
        cards = self._filtered_drawer_cards()
        if not cards:
            empty = QLabel("No compatible freight cards available")
            empty.setObjectName("freightSelectionEmpty")
            self._selection_grid.addWidget(empty, 0, 0)
            return
        counts: dict[tuple[str, str, int], int] = {}
        for card in cards:
            key = (card.definition_id, card.rarity.value, card.output_bonus_tenths)
            counts[key] = counts.get(key, 0) + 1
        columns = self._selection_grid_columns()
        for index, freight_card in enumerate(cards):
            definition = self._definitions[freight_card.definition_id]
            if not isinstance(definition, FreightDefinition):
                continue
            key = (freight_card.definition_id, freight_card.rarity.value, freight_card.output_bonus_tenths)
            tile = FreightSelectionCard(freight_card, definition, counts[key])
            tile.selected.connect(self._install_card_from_selection)
            tile.hovered.connect(lambda card_id, widget=tile: self._show_freight_hover(card_id, widget))
            tile.unhovered.connect(self._hide_freight_hover)
            self._selection_grid.addWidget(tile, index // columns, index % columns)
        self._selection_grid.setRowStretch((len(cards) + columns - 1) // columns, 1)
        self._selection_grid.setColumnStretch(columns, 1)

    def _selection_grid_columns(self) -> int:
        width = self.width() if self.width() > 0 else 900
        return max(2, min(8, (width - 260) // 186))

    def _filtered_drawer_cards(self) -> list[CardInstance]:
        installed = self._state.installed_card_ids() | self._state.installed_freight_card_ids()
        search = self._search_text.lower().strip()
        result: list[CardInstance] = []
        for freight_card in self._state.cards.values():
            if freight_card.card_kind is not CardKind.FREIGHT or freight_card.card_id in installed:
                continue
            definition = self._definitions.get(freight_card.definition_id)
            facility = self._state.freight.facilities[self._selected_facility_id]
            if not isinstance(definition, FreightDefinition) or definition.facility_id != facility.facility_type:
                continue
            if self._class_filter != "All" and definition.class_label != self._class_filter:
                continue
            if self._rarity_filter != "All" and freight_card.rarity.value.title() != self._rarity_filter:
                continue
            if search and search not in f"{definition.name} {definition.class_label} {freight_card.rarity.value}".lower():
                continue
            result.append(freight_card)
        return sorted(result, key=lambda card: (self._definitions[card.definition_id].name, card.rarity.value, card.card_id))

    def _install_card_from_selection(self, card_id: str) -> None:
        if self._drawer_slot_index is None:
            return
        facility_id = self._selected_facility_id
        slot_index = self._drawer_slot_index
        self._reset_drawer_state()
        self._command_bus.dispatch(InstallFreightCard(facility_id, slot_index, card_id, self._definitions))
        self.refresh()

    def _remove_card(self, slot_index: int) -> None:
        self._command_bus.dispatch(RemoveFreightCard(self._selected_facility_id, slot_index))
        self.refresh()

    def _clear_card_assignment(self, card_id: str) -> None:
        self._command_bus.dispatch(CancelFreightCardAssignment(card_id))
        self.refresh()

    def _open_drawer(self, slot_index: int) -> None:
        self._drawer_open = True
        self._drawer_slot_index = slot_index
        self._selected_card_id = None
        self.refresh()

    def _close_drawer(self) -> None:
        self._reset_drawer_state()
        self.refresh()

    def _reset_drawer_state(self) -> None:
        self._drawer_open = False
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._selection_grid = None

    def _select_facility(self, facility_id: str) -> None:
        self._selected_facility_id = facility_id
        self._reset_drawer_state()
        self._reset_assignment_state()
        self.refresh()

    def _select_facility_from_item(self, item: QTreeWidgetItem | None) -> None:
        if item is None:
            return
        facility_id = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(facility_id, str) and facility_id != self._selected_facility_id:
            self._select_facility(facility_id)

    def _open_assignment_view(self, card_id: str) -> None:
        self._reset_drawer_state()
        self._assignment_card_id = card_id
        assignment = self._state.freight.assignments.get(card_id)
        self._assignment_resource_id = assignment.resource_id if assignment is not None else None
        self._assignment_destination_kind = "market"
        self._assignment_reserve_percent = round(assignment.reserve_percent) if assignment is not None else 100
        self._assignment_resource_grid = None
        self.refresh()

    def _close_assignment_view(self) -> None:
        self._reset_assignment_state()
        self.refresh()

    def _reset_assignment_state(self) -> None:
        self._assignment_card_id = None
        self._assignment_resource_id = None
        self._assignment_destination_kind = None
        self._assignment_resource_grid = None

    def _reset_assignment_resource_step(self) -> None:
        self._assignment_resource_id = None
        self._assignment_destination_kind = None
        self._assignment_resource_grid = None
        self.refresh()

    def _assignment_target_label(self) -> str:
        if self._assignment_card_id is None:
            return "No Freight Card"
        card = self._state.cards.get(self._assignment_card_id)
        definition = self._definitions.get(card.definition_id) if card is not None else None
        if isinstance(definition, FreightDefinition):
            return definition.name
        return self._assignment_card_id

    def _populate_assignment_resource_grid(self) -> None:
        if self._assignment_resource_grid is None:
            return
        self._clear_layout(self._assignment_resource_grid)
        resources = self._filtered_assignment_resources()
        if not resources:
            empty = QLabel("No resources found")
            empty.setObjectName("freightSelectionEmpty")
            self._assignment_resource_grid.addWidget(empty, 0, 0)
            return
        columns = self._assignment_grid_columns()
        for index, (resource_id, resource) in enumerate(resources):
            stock = self._state.ensure_resource(resource_id, resource.default_capacity)
            tile = FreightAssignmentResourceTile(resource_id, resource, stock.amount, stock.capacity)
            tile.selected.connect(self._select_assignment_resource)
            self._assignment_resource_grid.addWidget(tile, index // columns, index % columns)
        self._assignment_resource_grid.setRowStretch((len(resources) + columns - 1) // columns, 1)
        self._assignment_resource_grid.setColumnStretch(columns, 1)

    def _filtered_assignment_resources(self) -> list[tuple[str, ResourceDefinition]]:
        search = self._assignment_search_text.lower().strip()
        result: list[tuple[str, ResourceDefinition]] = []
        for resource_id, resource in sorted(self._resources.items(), key=lambda item: item[1].name):
            category = resource.category or "General"
            if self._assignment_category_filter != "All" and category != self._assignment_category_filter:
                continue
            if search and search not in f"{resource.name} {category} {resource_id}".lower():
                continue
            result.append((resource_id, resource))
        return result

    def _assignment_categories(self) -> list[str]:
        return sorted({resource.category for resource in self._resources.values() if resource.category})

    def _assignment_grid_columns(self) -> int:
        width = self.width() if self.width() > 0 else 1000
        return max(2, min(8, (width - 280) // 174))

    def _select_assignment_resource(self, resource_id: str) -> None:
        self._assignment_resource_id = resource_id
        existing = self._state.freight.assignments.get(self._assignment_card_id or "")
        if existing is None or existing.resource_id != resource_id:
            self._assignment_destination_kind = "market"
            self._assignment_reserve_percent = 100
        self.refresh()

    def _select_assignment_destination(self, destination_kind: str) -> None:
        self._assignment_destination_kind = destination_kind
        self.refresh()

    def _set_assignment_search(self, text: str) -> None:
        self._assignment_search_text = text
        self._populate_assignment_resource_grid()

    def _set_assignment_category_filter(self, text: str) -> None:
        self._assignment_category_filter = text
        self.refresh()

    def _set_assignment_reserve(self, value: int, label: QLabel) -> None:
        self._assignment_reserve_percent = max(0, min(100, int(value)))
        label.setText(f"{self._assignment_reserve_percent}%")
        if self._assignment_card_id is None:
            return
        assignment = self._state.freight.assignments.get(self._assignment_card_id)
        if assignment is None or assignment.destination_kind != "market":
            return
        self._command_bus.dispatch(UpdateFreightReserve(self._assignment_card_id, self._assignment_reserve_percent))
        self.refresh_runtime()

    def _apply_assignment(self, destination_kind: str) -> None:
        if self._assignment_card_id is None or self._assignment_resource_id is None:
            return
        destination_kind = "market"
        reserve = float(self._assignment_reserve_percent)
        existing = self._state.freight.assignments.get(self._assignment_card_id)
        if existing is not None and is_freight_card_busy(self._state.freight, self._assignment_card_id):
            if existing.resource_id != self._assignment_resource_id or existing.destination_kind != destination_kind:
                return
            self._command_bus.dispatch(UpdateFreightReserve(self._assignment_card_id, reserve))
        else:
            self._command_bus.dispatch(
                AssignFreightCard(self._assignment_card_id, self._assignment_resource_id, destination_kind, reserve)
            )
        self._reset_assignment_state()
        self.refresh()

    def _assignment_card_is_busy(self) -> bool:
        return self._assignment_card_id is not None and is_freight_card_busy(self._state.freight, self._assignment_card_id)

    def _matching_contracts_for_assignment(self) -> list[tuple[str, object, float]]:
        if self._assignment_resource_id is None:
            return []
        pending = sum(
            shipment.quantity
            for shipment in self._state.freight.outbound_shipments.values()
            if shipment.active
            and shipment.destination_kind == "contract"
            and shipment.resource_id == self._assignment_resource_id
        )
        matches = []
        for kind, active in self._state.contracts.active.items():
            if active.status != "active" or self._assignment_resource_id not in active.offer.requirements:
                continue
            remaining = active.remaining_amount(self._assignment_resource_id) - pending
            if remaining > 0:
                matches.append((kind, active, remaining))
        return matches

    def _set_build_facility_type(self, facility_type: str) -> None:
        self._build_facility_type = facility_type
        self.refresh()

    def _build_facility(self) -> None:
        self._command_bus.dispatch(BuildFreightFacility(self._build_facility_type))
        self._selected_facility_id = next(reversed(self._state.freight.facilities))
        self.refresh()

    def _expand_facility(self) -> None:
        self._command_bus.dispatch(ExpandFreightFacility(self._selected_facility_id))
        self.refresh()

    def _set_search(self, text: str) -> None:
        self._search_text = text
        self.refresh()

    def _set_class_filter(self, text: str) -> None:
        self._class_filter = text
        self.refresh()

    def _set_rarity_filter(self, text: str) -> None:
        self._rarity_filter = text
        self.refresh()

    def _active_shipment_for(self, card_id: str) -> OutboundFreightShipment | None:
        return next(
            (
                shipment
                for shipment in self._state.freight.outbound_shipments.values()
                if shipment.active and shipment.freight_card_id == card_id
            ),
            None,
        )

    def _freight_definitions_for_selected_facility(self) -> tuple[FreightDefinition, ...]:
        return tuple(
            definition
            for definition in self._definitions.values()
            if isinstance(definition, FreightDefinition)
            and self._selected_facility_id in self._state.freight.facilities
            and definition.facility_id == self._state.freight.facilities[self._selected_facility_id].facility_type
        )

    def _total_capacity(self) -> float:
        total = 0.0
        for card_id in self._state.installed_freight_card_ids():
            card = self._state.cards.get(card_id)
            definition = self._definitions.get(card.definition_id) if card is not None else None
            if card is not None and isinstance(definition, FreightDefinition):
                total += freight_stats(card, definition).capacity
        return total

    def _update_kpis(self) -> None:
        values = {
            "Installed Freight": str(len(self._state.installed_freight_card_ids())),
            "Active Shipments": str(len(self._state.freight.outbound_shipments)),
            "Total Transport Capacity": f"{self._total_capacity():.0f}",
        }
        for label, value in values.items():
            widget = self._kpi_values.get(label)
            if widget is not None:
                widget.setText(value)

    def _update_card_runtime(self, card_id: str, widgets: dict[str, QWidget | None]) -> None:
        assignment = self._state.freight.assignments.get(card_id)
        shipment = self._active_shipment_for(card_id)
        busy = shipment is not None
        status = self._status_text(assignment, shipment)
        card_widget = widgets.get("card")
        if isinstance(card_widget, QFrame):
            card = self._state.cards.get(card_id)
            definition = self._definitions.get(card.definition_id) if card is not None else None
            if card is not None and isinstance(definition, FreightDefinition):
                stats = freight_stats(card, definition)
                route_label = "ASSIGN ROUTE >"
                if assignment is not None:
                    resource = self._resources.get(assignment.resource_id)
                    resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
                    route_label = f"ROUTE: {resource_name} > {DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind)}"
                card_widget.setProperty("cardTitle", self._freight_card_title(definition))
                card_widget.setProperty("cardMeta", f"{self._freight_card_tier_label(definition)} · {card.rarity.value.upper()}")
                card_widget.setProperty("cardDetail", f"CAPACITY {stats.capacity:.0f}")
                card_widget.setProperty("cardSecondary", route_label.upper())
                card_widget.setProperty("cardStatus", status.lower().replace(" ", "_"))
                card_widget.setProperty("cardStatusText", self._compact_status_text(status))
                card_widget.setProperty("cardStatusAccent", self._freight_status_accent(status))
                card_widget.setProperty("cardUtilityText", "CANCEL" if busy or assignment is not None else "REMOVE")
                self._set_shipment_progress_properties(card_widget, shipment)
                if isinstance(card_widget, ClickableFreightSlotCard):
                    card_widget._position_installed_controls()
                card_widget.update()
        status_label = widgets.get("status")
        if isinstance(status_label, QLabel):
            status_label.setText(self._compact_status_text(status))
            status_label.setProperty("detailStatus", status)
            status_label.setProperty("status", status.lower().replace(" ", "_"))
            status_label.style().unpolish(status_label)
            status_label.style().polish(status_label)
        remove = widgets.get("remove")
        if isinstance(remove, QPushButton):
            remove.setText("CANCEL" if busy or assignment is not None else "REMOVE")
            remove.setEnabled(True)
        assignment_panel = widgets.get("assignment_panel")
        if isinstance(assignment_panel, ClickableAssignmentPanel):
            assignment_panel.setProperty("clickEnabled", True)
            assignment_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_shipment_widgets(widgets, shipment)
        if self._hover_card_id == card_id and self._hover_popup is not None:
            self._update_freight_hover(card_id)

    def _update_shipment_widgets(
        self,
        widgets: dict[str, QWidget | None],
        shipment: OutboundFreightShipment | None,
    ) -> None:
        panel = widgets.get("shipment_panel")
        route = widgets.get("shipment_route")
        quantity = widgets.get("shipment_quantity")
        remaining = widgets.get("shipment_remaining")
        progress = widgets.get("shipment_progress")
        if isinstance(panel, QFrame):
            panel.setVisible(False)
        if shipment is None:
            if isinstance(route, QLabel):
                route.setText("")
            if isinstance(quantity, QLabel):
                quantity.setText("")
            if isinstance(remaining, QLabel):
                remaining.setText("")
            if isinstance(progress, QProgressBar):
                progress.setValue(0)
            return
        resource = self._resources.get(shipment.resource_id)
        resource_name = resource.name if resource is not None else (shipment.resource_id or "Unknown")
        if isinstance(route, QLabel):
            route.setText(
                f"Shipment: {resource_name} -> {DESTINATION_LABELS.get(shipment.destination_kind, shipment.destination_kind.title())}"
            )
        if isinstance(quantity, QLabel):
            quantity.setText(f"Quantity: {shipment.quantity:.1f}")
        if isinstance(remaining, QLabel):
            remaining.setText(f"Remaining: {self._format_time(shipment.remaining_seconds)}")
        if isinstance(progress, QProgressBar):
            if shipment.transport_time_seconds > 0:
                done = 1.0 - shipment.remaining_seconds / shipment.transport_time_seconds
            else:
                done = 1.0
            progress.setValue(round(max(0.0, min(1.0, done)) * 1000))

    def _show_freight_hover(self, card_id: str, source: QWidget) -> None:
        self._hover_card_id = card_id
        if self._hover_popup is None:
            self._hover_popup = CardHoverInfoPopup(self, object_name="freightHoverInfo", embedded=True)
        self._update_freight_hover(card_id)
        self._hover_popup.show_for(source)

    def _hide_freight_hover(self) -> None:
        self._hover_card_id = None
        if self._hover_popup is not None:
            self._hover_popup.hide()

    def _update_freight_hover(self, card_id: str) -> None:
        card = self._state.cards.get(card_id)
        definition = self._definitions.get(card.definition_id) if card is not None else None
        if card is None or not isinstance(definition, FreightDefinition):
            self._hide_freight_hover()
            return
        stats = freight_stats(card, definition)
        assignment = self._state.freight.assignments.get(card_id)
        shipment = self._active_shipment_for(card_id)
        status = self._status_text(assignment, shipment)
        if assignment is None:
            assignment_text = "Unassigned"
        else:
            resource = self._resources.get(assignment.resource_id)
            resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
            destination = DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind.title())
            if assignment.destination_kind == "market":
                assignment_text = f"{resource_name} -> {destination} · Reserve {assignment.reserve_percent:.0f}%"
            else:
                assignment_text = f"{resource_name} -> {destination}"
        values = {
            "Freight Type": definition.family.value.title(),
            "Class": definition.class_label,
            "Rarity": card.rarity.value.title(),
            "Bonus": f"+{card.output_bonus_percent:.1f}%",
            "Capacity": f"{stats.capacity:.0f}",
            "Travel Time": self._format_time(stats.transport_time_seconds),
            "Assignment": assignment_text,
            "Status": status,
        }
        sections = list(values.items())
        signature = (
            card_id,
            definition.definition_id,
            tuple(label for label, _value in sections),
        )
        icon_key, accent_key = FREIGHT_ICON_KEYS.get(definition.family.value, ("vehicle", "vehicle"))
        if self._hover_popup is None:
            return
        if self._hover_popup.details_signature != signature:
            icon = ResourceIconWidget(definition.definition_id, icon_key, accent_key, size=34)
            self._hover_popup.set_details(definition.name, icon, sections, signature)
        else:
            self._hover_popup.update_values(sections)

    def _meta_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("freightMetaLabel")
        return label

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _set_combo_text(self, combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _format_time(self, seconds: float) -> str:
        total = max(0, round(seconds))
        minutes, secs = divmod(total, 60)
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"

    def _compact_status_text(self, status: str) -> str:
        if status.startswith("WAITING"):
            return "WAITING"
        return status

    def _freight_card_title(self, definition: FreightDefinition) -> str:
        return definition.family.value.replace("_", " ").upper()

    def _freight_card_tier_label(self, definition: FreightDefinition) -> str:
        class_label = definition.class_label.strip()
        roman_tiers = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}
        parts = class_label.upper().split()
        if len(parts) == 2 and parts[0] == "CLASS" and parts[1] in roman_tiers:
            return f"MK{roman_tiers[parts[1]]}"
        return class_label.upper()

    def _freight_status_accent(self, status: str) -> Accent:
        compact = self._compact_status_text(status)
        if compact in {"READY", "IN TRANSIT"}:
            return Accent.SUCCESS
        if compact == "WAITING":
            return Accent.WARNING
        return Accent.NEUTRAL

    def _set_shipment_progress_properties(self, card_widget: QFrame, shipment: OutboundFreightShipment | None) -> None:
        card_widget.setProperty("shipmentActive", shipment is not None)
        ratio = 0.0
        if shipment is not None:
            if shipment.transport_time_seconds > 0:
                ratio = 1.0 - shipment.remaining_seconds / shipment.transport_time_seconds
            else:
                ratio = 1.0
        card_widget.setProperty("shipmentProgress", max(0.0, min(1.0, ratio)))

    def _status_text(self, assignment, shipment: OutboundFreightShipment | None) -> str:
        if shipment is not None:
            return "IN TRANSIT"
        if assignment is None:
            return "UNASSIGNED"
        stock = self._state.ensure_resource(assignment.resource_id)
        if stock.amount <= 0:
            return "WAITING · NO CARGO"
        if assignment.destination_kind == "market":
            if stock.amount <= stock.capacity * assignment.reserve_percent / 100.0:
                return "WAITING · BELOW RESERVE"
        if assignment.destination_kind == "contract" and not self._has_matching_contract_need(assignment.resource_id):
            return "WAITING · NO CONTRACT"
        return "READY"

    def _has_matching_contract_need(self, resource_id: str) -> bool:
        pending = sum(
            shipment.quantity
            for shipment in self._state.freight.outbound_shipments.values()
            if shipment.active and shipment.destination_kind == "contract" and shipment.resource_id == resource_id
        )
        for active in self._state.contracts.active.values():
            if active.status != "active" or resource_id not in active.offer.requirements:
                continue
            if active.remaining_amount(resource_id) - pending > 0:
                return True
        return False

    def _sorted_facilities(self):
        order = {facility_type: index for index, facility_type in enumerate(FACILITY_TYPE_ORDER)}
        return sorted(
            self._state.freight.facilities.items(),
            key=lambda item: (order.get(item[1].facility_type, 99), item[1].name, item[0]),
        )

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
