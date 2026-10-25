from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt, Signal
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
    QVBoxLayout,
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
)
from shiboken6 import isValid as is_qt_object_valid

from production_zero.core.cards import CardInstance, CardStack
from production_zero.core.freight import freight_facility_expansion_cost, freight_expansion_problem
from production_zero.core.commands import AssignFreightCard, BuildFreightFacility, CancelFreightCardAssignment, CommandBus, ExpandFreightFacility, InstallFreightCard, RemoveFreightCard
from production_zero.core.definitions import CardDefinition, FreightDefinition
from production_zero.core.enums import CardKind
from production_zero.core.freight import (
    FREIGHT_FACILITY_EXPANSION_SLOTS,
    FREIGHT_FACILITY_START_SLOTS,
    FREIGHT_FACILITY_TYPES,
    OutboundFreightShipment,
    freight_facility_build_cost,
    freight_stats,
    is_freight_card_busy,
)
from production_zero.core.inventory import CardInventoryRow
from production_zero.ui.factory_view_v2 import (
    FactoryV2ActiveIndicator,
    FactoryV2Board,
    FACTORY_V2_CARD_HEIGHT,
    FACTORY_V2_CARD_WIDTH,
    FactoryV2HallOverview,
    FactoryV2LinePlate,
    FactoryV2TrackPanel,
)
from production_zero.ui.text_format import count_label
from production_zero.ui.game_ui.rendering import draw_build_slot, draw_locked_slot, draw_machine_card_prototype, draw_status_badge
from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup, card_hover_icon
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.secondary_views import ResourceBrowser, SecondaryViewHeader, secondary_action_button, style_secondary, retain_grid_tiles
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.resource_tiles import RESOURCE_TILE_WIDTH, ResourceSelectionGridHost, ResourceSelectionTile, configure_resource_selection_grid_host, configure_resource_selection_scroll
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.widget_lifecycle import clear_layout_safely


FACILITY_TYPE_ORDER = ("garage_depot", "rail_station", "airport", "harbor")
DESTINATION_LABELS = {"market": "Sell", "contract": "Contract", "consortium": "Consortium Contract", "event": "Event (coming later)"}
FREIGHT_ICON_KEYS = {
    "truck": ("vehicle", "vehicle"),
    "train": ("rail", "rail"),
    "ship": ("ship", "ship"),
    "aircraft": ("aircraft", "aircraft"),
}
FREIGHT_SLOT_CARD_WIDTH = 166
FREIGHT_SLOT_CARD_HEIGHT = 264
FREIGHT_SLOT_GRID_SPACING = 10


def _hidden_child_label(parent: QWidget, object_name: str, text: str) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    label.hide()
    return label


class ClickableFreightSlotCard(QFrame):
    activated = Signal()
    hovered = Signal()
    unhovered = Signal()

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.set_click_enabled(enabled)

    def set_click_enabled(self, enabled: bool) -> None:
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.setProperty("clickEnabled", enabled)
        self.setProperty("unlockEnabled", enabled)
        self.update()

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
                        f"${float(self.property('unlockCost') or 0):.2f}",
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
                self._draw_interaction_outline()
                return
        super().paintEvent(event)
        self._draw_interaction_outline()

    def _draw_interaction_outline(self):
        if self.property("selected") or self.property("freightDropTarget"):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#7fe6b1" if self.property("freightDropTarget") else "#ffd21f"), 2))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(3, 3, -3, -3), 10, 10)
            painter.end()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.property("slotState") == "installed":
            self._position_installed_controls()

    def _position_installed_controls(self) -> None:
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2).adjusted(5, 11, -5, -9)
        if control := self.findChild(QWidget, "freightMkControl"):
            art = self._installed_art_rect(rect)
            control.move(round(art.right()) - 35, round(art.bottom()) - 33)
            control.raise_()
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
            "train": QColor(GAME_UI_TOKENS.colors.train),
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
    """One compact title row and a right-aligned, facility-local P6 group."""
    def __init__(self, facility, state: GameState) -> None:
        super().__init__()
        self._facility, self._state = facility, state
        self.setObjectName("freightFacilityHeader")
        self.setFixedHeight(64)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._delivery_signature = None
        self.refresh_statistics()

    def refresh_statistics(self) -> bool:
        from production_zero.ui.freight_statistics import compact_rate, overview_tooltip
        rate = self._state.freight.delivery_statistics.rate(facility_id=self._facility.facility_id)
        values = tuple(compact_rate(value) for value in (rate.sell, rate.contract, rate.consortium, rate.total))
        occupied = sum(bool(slot.card_id) for slot in self._facility.slots)
        ids = {slot.card_id for slot in self._facility.slots if slot.card_id}
        active = sum(shipment.active and (shipment.source_facility_id == self._facility.facility_id or
                     shipment.source_facility_id is None and shipment.freight_card_id in ids)
                     for shipment in self._state.freight.outbound_shipments.values())
        meta = f"{occupied}/{len(self._facility.unlocked_slot_indexes())} slots; {active} active shipments"
        tooltip = self._facility.name + '\n' + meta + '\n' + overview_tooltip(rate)
        signature = (values, tooltip)
        if signature == self._delivery_signature:
            return False
        self._delivery_signature = signature
        self.setProperty('facilityTitle', self._facility.name.upper())
        self.setProperty('facilityMeta', meta)
        for target, value in zip(('Sell', 'Contract', 'Consortium', 'Total'), values):
            self.setProperty('delivery' + target, value)
        self.setToolTip(tooltip)
        self.update()
        return True

    def _header_geometry(self):
        from PySide6.QtGui import QFontMetricsF
        font = GAME_UI_TOKENS.typography.industrial_label()
        font.setPointSize(10)
        texts = [target.upper() + ' ' + self.property('delivery' + target)
                 for target in ('Sell', 'Contract', 'Consortium', 'Total')]
        while font.pointSize() > 7 and sum(QFontMetricsF(font).horizontalAdvance(t) + 18 for t in texts) > self.width() - 150:
            font.setPointSize(font.pointSize() - 1)
        widths = [QFontMetricsF(font).horizontalAdvance(t) + 18 for t in texts]
        x = max(0, self.width() - 8 - sum(widths))
        return font, texts, widths, x

    def rename_title_layout(self):
        from production_zero.ui.interaction_polish import building_title_layout
        _font, _texts, _widths, stats_x = self._header_geometry()
        font = GAME_UI_TOKENS.typography.brand_display()
        font.setPointSize(22)
        rect = QRectF(12, 0, max(40, stats_x - 24), self.height())
        visible, pencil = building_title_layout(self._facility.name, font, rect)
        return font, visible, pencil

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            stats_font, texts, widths, x = self._header_geometry()
            font, visible, _pencil = self.rename_title_layout()
            painter.setFont(font)
            painter.setPen(QColor('#eff8f4'))
            painter.drawText(QRectF(12, 0, max(0, x - 24), self.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, visible)
            painter.setFont(stats_font)
            for text, width in zip(texts, widths):
                painter.drawText(QRectF(x, 0, width - 12, self.height()),
                                 Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
                x += width
        finally:
            painter.end()


class FreightSelectionCard(InventoryCardFrame):
    selected = Signal(str)
    hovered = Signal(str)
    unhovered = Signal()

    def __init__(self, freight_card: CardInstance, definition: FreightDefinition, quantity: int, research=None) -> None:
        row = CardInventoryRow(card=freight_card, definition=definition, quantity=quantity, status="Available")
        stats = freight_stats(freight_card, definition, research)
        super().__init__(
            row,
            title="FREIGHT",
            family=definition.family.value,
            meta=freight_card.rarity.value.upper(),
            detail=f"{stats.capacity:g} CAP / {stats.transport_time_seconds:g}s",
            selected=False,
            disabled=False,
            status_text="AVAILABLE",
        )
        self._card_id = freight_card.card_id
        self.setObjectName("freightSelectionCard")
        self.setProperty("cardId", freight_card.card_id)
        self.setProperty("freightFamily", definition.family.value)
        self.setProperty("rarity", freight_card.rarity.value)
        self.setProperty("quantity", quantity)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
        self._add_compatibility_children(freight_card, definition, quantity)

    def _add_compatibility_children(self, freight_card: CardInstance, definition: FreightDefinition, quantity: int, research=None) -> None:
        _hidden_child_label(self, "freightSelectionName", definition.name)
        _hidden_child_label(self, "freightSelectionRarity", f"MK{freight_card.mk_level} · {freight_card.rarity.value.upper()}")
        _hidden_child_label(self, "freightSelectionFamily", definition.family.value.upper())
        _hidden_child_label(self, "freightSelectionMeta", f"+{freight_card.output_bonus_percent:.1f}%")
        _hidden_child_label(self, "freightSelectionMeta", f"x{quantity}")
        rarity_line = QFrame(self)
        rarity_line.setObjectName("freightRarityLine")
        rarity_line.setProperty("rarity", freight_card.rarity.value)
        rarity_line.hide()
        icon_key, accent_key = FREIGHT_ICON_KEYS.get(definition.family.value, ("vehicle", "vehicle"))
        icon = ResourceIconWidget(definition.definition_id, icon_key, accent_key, size=1)
        icon.setParent(self)
        icon.setObjectName("freightTypeIcon")
        icon.hide()

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


class FreightAssignmentResourceTile(ResourceSelectionTile):
    selected = Signal(str)

    def __init__(self, resource_id: str, resource: ResourceDefinition, stock_amount: float, stock_capacity: float) -> None:
        self._resource_id = resource_id
        super().__init__(
            resource_id=resource_id,
            title=resource.name,
            subtitle=resource.category or "General",
            detail=f"{stock_amount:g} STORED",
            status="",
            icon_key=resource.icon_key or resource_icon_key(resource_id),
            accent_key=resource.accent_key or resource_accent_key(resource_id),
            object_name="freightAssignmentResourceTile",
            title_object_name="freightAssignmentTileName",
            subtitle_object_name="freightAssignmentTileMeta",
            detail_object_name="freightAssignmentTileStock",
            status_object_name="freightAssignmentTileStatus",
            icon_object_name="freightAssignmentResourceIcon",
        )
        self.setProperty("category", resource.category or "General")

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




from production_zero.ui.freight_assignment import FreightAssignmentMixin


class FreightView(FreightAssignmentMixin, QWidget):
    supply_requested = Signal(str)

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
        self._selected_vehicle_id = None
        self._selected_vehicles = set()
        self._selected_empty_slots = set()
        self._vehicle_selection_anchor = None
        self._slot_selection_anchor = None
        self._focused_freight_line = None
        self._freight_clipboard = ()
        self._reset_assignment_state()
        from production_zero.ui.freight_lines import FreightLineInput, copy_selection, paste_selection
        from production_zero.ui.production_templates import TemplateShortcuts
        self._line_input = FreightLineInput(self)
        self._template_shortcuts = TemplateShortcuts(self, lambda: copy_selection(self), lambda: paste_selection(self))
        from production_zero.ui.freight_drag import FreightSlotInteraction
        self._slot_interaction = FreightSlotInteraction(self)
        self._search_text = ""
        self._assignment_card_id: str | None = None
        self._cargo_snapshot = None
        self._assignment_search_text = ""
        self._assignment_category_filter = "All"
        self._assignment_resource_grid: QGridLayout | None = None
        self._assignment_resource_grid_host: QWidget | None = None
        self._hover_card_id: str | None = None
        self._hover_popup: CardHoverInfoPopup | None = None
        self._kpi_values: dict[str, QLabel] = {}
        self._runtime_widgets: dict[str, dict[str, QWidget | None]] = {}
        self._selection_grid: QGridLayout | None = None
        self._facility_tree: QTreeWidget | None = None
        self._slots_scroll: QScrollArea | None = None
        self._slot_scroll_values: dict[str, tuple[int, int]] = {}
        self._slot_scroll_restore_generation = 0
        self._slot_grid_column_count: int | None = None
        self._slot_reflow_pending = False

        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(14)
        self.refresh()

    def refresh(self) -> None:
        self._slot_interaction._finish_pointer_drag()
        facility = self._state.freight.facilities.get(self._selected_facility_id)
        if facility is not None:
            self._selected_empty_slots.intersection_update(i for i in facility.unlocked_slot_indexes() if facility.slots[i].card_id is None)
        if cached := getattr(self, "_assignment_board", None):
            from production_zero.ui.widget_lifecycle import hide_detach_delete
            self._assignment_board = None
            hide_detach_delete(cached)
        previous_scroll = self._capture_slot_scroll()
        self._hide_freight_hover()
        self._kpi_values = {}
        self._runtime_widgets = {}
        self._facility_stage = None
        self._slots_scroll = None
        self._slot_grid_column_count = None
        self._clear_layout(self._root)
        self._root.addWidget(self._build_facility_list(), 0)
        self._root.addWidget(self._build_slots_panel(), 1)
        self._restore_slot_scroll(previous_scroll)

    def reset_for_state_change(self) -> None:
        self._slot_selection_anchor = None
        self._slot_interaction._finish_pointer_drag()
        self._selected_vehicles.clear()
        self._selected_empty_slots.clear()
        self._vehicle_selection_anchor = None
        self._focused_freight_line = None
        self._freight_clipboard = ()
        self._route_group = ()
        self._slot_interaction.changed = False
        self._slot_interaction.block_reason = None
        self._selected_facility_id = next(iter(self._state.freight.facilities))
        self._selected_vehicle_id = None
        self._selected_card_id = None
        self._reset_assignment_state()
        self._cargo_snapshot = None
        self._drawer_open = False
        self._drawer_slot_index = None
        self._search_text = ""
        self._assignment_search_text = ""
        self._assignment_category_filter = "All"
        self._slot_scroll_values.clear()
        self._assignment_resource_grid = None
        self._assignment_resource_grid_host = None
        self._selection_grid = None
        self._slot_scroll_restore_generation += 1
        self._slots_scroll = None
        self.refresh()

    def refresh_runtime(self) -> None:
        self._slot_interaction.check_sources()
        from production_zero.ui.group_actions import BuildingMkButton
        for button in self.findChildren(BuildingMkButton):
            button.refresh_quote()
        self._update_kpis()
        stage = self._facility_stage
        facility = self._state.freight.facilities.get(self._selected_facility_id)
        if stage is not None and facility is not None:
            stage.refresh_statistics()
            signature = (facility.name, tuple(slot.card_id for slot in facility.slots),len(facility.unlocked_slot_indexes()),
                         sum(1 for shipment in self._state.freight.outbound_shipments.values() if shipment.active and
                             (shipment.source_facility_id == facility.facility_id or shipment.source_facility_id is None and
                              any(slot.card_id == shipment.freight_card_id for slot in facility.slots))))
            if getattr(stage, "_runtime_signature", None) != signature:
                stage._runtime_signature = signature
                stage.update()
                if self._facility_tree is not None:
                    for i in range(self._facility_tree.topLevelItemCount()):
                        item = self._facility_tree.topLevelItem(i)
                        unit = self._state.freight.facilities.get(item.data(0, Qt.ItemDataRole.UserRole))
                        if unit is not None:
                            item.setText(0, self._facility_nav_label(unit))
        self._refresh_expansion_affordability()
        if facility is not None:
            for indicator in self.findChildren(FactoryV2ActiveIndicator):
                indicator.setProperty("scopePaused", bool(indicator.property("lineLocked")) or facility.paused or indicator.property("lineNumber") in facility.paused_lines)
                indicator.update()
        if self._assignment_resource_grid is not None and self._cargo_snapshot != self._current_cargo_snapshot():
            self._populate_assignment_resource_grid()
            target = self.findChild(QLabel, "freightSelectionTarget")
            if target is not None:
                target.setText(self._assignment_target_label())
        self._update_assignment_targets()
        for card_id, widgets in list(self._runtime_widgets.items()):
            self._update_card_runtime(card_id, widgets)

    def _refresh_expansion_affordability(self) -> None:
        facility = self._state.freight.facilities.get(self._selected_facility_id)
        if facility is not None:
            specs = {slot_index: (cost, enabled, is_next) for slot_index, cost, enabled, is_next in self._locked_slot_specs(facility)}
            for card in self.findChildren(ClickableFreightSlotCard, "freightSlotCard"):
                if card.property("slotState") != "locked":
                    continue
                spec = specs.get(int(card.property("slotIndex")))
                if spec is None:
                    continue
                cost, enabled, is_next = spec
                card.setProperty("unlockCost", cost)
                card.setProperty("isNextUnlock", is_next)
                card.set_click_enabled(enabled)
        build = self.findChild(QPushButton, "buildFreightFacilityButton")
        if build is not None:
            build.setText("BUILD FACILITY")
            build.setEnabled(True)
        from production_zero.core.freight import FREIGHT_FACILITY_START_SLOTS
        for button in self.findChildren(QWidget, "unlockFreightLineButton"):
            cost=freight_facility_expansion_cost(facility,slot_index=int(button.property('slotIndex')))
            problem = freight_expansion_problem(facility, int(button.property('slotIndex')))
            enabled = not problem and self._state.cash.amount >= cost
            button.setEnabled(enabled);button.setProperty("clickEnabled",enabled)
            button.setToolTip(problem or f'Unlock next line · ${cost:,.2f}')
        for button in [*self.findChildren(QWidget, "buildingPauseButton"), *self.findChildren(QWidget, "sectorPauseButton")]:
            button.refresh_pause()

    def _facility_usage_label(self, facility) -> str:
        installed = sum(1 for slot in facility.slots if slot.card_id is not None)
        return f"{installed} / {len(facility.unlocked_slot_indexes())}"

    def _facility_nav_label(self, facility) -> str:
        card_ids = {slot.card_id for slot in facility.slots if slot.card_id}
        active_shipments = sum(1 for shipment in self._state.freight.outbound_shipments.values() if shipment.active and
                               (shipment.source_facility_id == facility.facility_id or
                                shipment.source_facility_id is None and shipment.freight_card_id in card_ids))
        slot_total = count_label(len(facility.unlocked_slot_indexes()), "slot")
        shipment_total = count_label(active_shipments, "shipment")
        installed = sum(1 for slot in facility.slots if slot.card_id is not None)
        return f"{facility.name}\n{installed} / {slot_total} · {shipment_total}"

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

        from production_zero.ui.building_tree import BuildingTree
        from production_zero.core.commands import ReorderBuildings
        tree = BuildingTree()
        tree.enable_reordering(lambda ids: self._command_bus.dispatch(ReorderBuildings('freight', ids)))
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
        from production_zero.ui.interaction_polish import bind_building_tree
        from production_zero.ui.release_freight import rename_facility, sell_facility
        bind_building_tree(tree, lambda uid: rename_facility(self, uid), lambda uid: self._facility_sale(uid))
        layout.addWidget(tree, 1)

        build = QPushButton("BUILD FACILITY")
        build.setObjectName("buildFreightFacilityButton")
        build.setEnabled(True)
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
        overview_layout.setContentsMargins(8, 4, 8, 4)
        overview_layout.setSpacing(12)
        from production_zero.ui.interaction_polish import TitleRenameFilter, pause_button
        from production_zero.core.commands import PauseFreightScope
        from production_zero.ui.release_freight import rename_facility
        stage = FreightFacilityStage(facility, self._state)
        self._facility_stage = stage
        stage._rename_filter = TitleRenameFilter(stage, lambda: rename_facility(self))
        overview_layout.addWidget(stage, 1)
        overview_layout.addWidget(pause_button(self, lambda: tuple(s.card_id for s in facility.slots if s.card_id),
                                  self._state, self._command_bus, self.refresh_runtime, scope=lambda: facility.paused,
                                  command=lambda paused: PauseFreightScope(facility.facility_id, paused)))
        from production_zero.ui.group_actions import BuildingMkButton
        from production_zero.ui.freight_upgrade import upgrade_vehicles
        overview_layout.addWidget(BuildingMkButton(
            self, lambda: tuple(s.card_id for s in facility.slots if s.card_id),
            lambda: upgrade_vehicles(self, tuple(s.card_id for s in facility.slots if s.card_id)),
        ))
        layout.addWidget(overview)

        from production_zero.ui.freight_lines import build_lines
        layout.addWidget(build_lines(self, facility), 1)
        return panel

    def _build_slot_card(self, slot_index: int, card_id: str | None) -> QFrame:
        card = ClickableFreightSlotCard(enabled=card_id is None)
        card.setObjectName("freightSlotCard")
        card.setProperty("slotIndex", slot_index)
        card.setProperty("slotState", "empty" if card_id is None else "installed")
        self._slot_interaction.bind(card, self._selected_facility_id, slot_index, card_id)
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
        from production_zero.ui.release_freight import vehicle_actions
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        card.customContextMenuRequested.connect(lambda position, cid=card_id: vehicle_actions(self, cid))
        definition = self._definitions.get(freight_card.definition_id)
        shipment = self._active_shipment_for(card_id)
        busy = shipment is not None
        assignment = self._state.freight.assignments.get(card_id)
        status = self._vehicle_status(freight_card, assignment, shipment)
        card.setToolTip("Paused: current delivery will finish; no new departures. Resume from the vehicle menu." if freight_card.paused else "Click to select; drag idle vehicles to move or swap compatible slots. Right-click for vehicle actions.")

        if isinstance(definition, FreightDefinition):
            card.setProperty("freightFamily", definition.family.value)
            card.setProperty("rarity", freight_card.rarity.value)
            stats = freight_stats(freight_card, definition, self._state.research)
            route_label = "ASSIGN ROUTE >"
            if assignment is not None:
                resource = self._resources.get(assignment.resource_id)
                resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
                route_label = f"ROUTE: {resource_name} > {DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind)}"
            card.setProperty("cardTitle", self._freight_card_title(definition))
            card.setProperty("cardMeta", f"MK{freight_card.mk_level} · {freight_card.rarity.value.upper()}")
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
            rarity_label = QLabel(f"MK{freight_card.mk_level} · {freight_card.rarity.value.upper()}")
            rarity_label.setObjectName("freightCardRarity")
            rarity_label.setVisible(False)
            meta.addWidget(rarity_label)
            icon_row.addLayout(meta, 1)
            layout.addLayout(icon_row)

        from production_zero.ui.freight_upgrade import FreightMkButton
        upgrade = FreightMkButton(self, card_id, card)
        assignment_panel = self._assignment_panel(card_id, assignment, True)
        assignment_panel.setParent(card)

        shipment_panel, shipment_widgets = self._shipment_panel(shipment)
        shipment_panel.setParent(card)

        remove = QPushButton("CANCEL" if busy or assignment is not None else "REMOVE")
        remove.setObjectName("freightRemoveButton")
        remove.setProperty("freightCardSecondary", True)
        remove.setFixedHeight(16)
        remove.clicked.connect(lambda checked=False, cid=card_id, idx=slot_index:
            self._clear_card_assignment(cid) if self._active_shipment_for(cid) is not None or cid in self._state.freight.assignments
            else self._remove_card(idx))
        remove.setParent(card)
        card._position_installed_controls()
        self._runtime_widgets[card_id] = {
            "card": card,
            "upgrade": upgrade,
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
        card.setProperty("isNextUnlock", unlock_enabled)
        card.setProperty("unlockEnabled", enabled)
        self._slot_interaction.bind(card, self._selected_facility_id, slot_index)
        card.setToolTip(f"Unlock S{slot_index + 1:02d} · ${cost:,.2f}" if unlock_enabled else f"Unlock S{slot_index:02d} first")
        card.setFixedSize(FREIGHT_SLOT_CARD_WIDTH, FREIGHT_SLOT_CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if unlock_enabled:
            fid=self._selected_facility_id
            card.activated.connect(lambda idx=slot_index,quote=cost,fid=fid:self._expand_facility(idx,quote,fid))
        return card

    def _locked_slot_specs(self, facility) -> list[tuple[int, float, bool, bool]]:
        owned=facility.unlocked_slot_indexes();capacity=facility.line_capacity
        count=(len(facility.slots)+capacity-1)//capacity;result=[]
        for line in range(count):
            missing=[i for i in range(line*capacity,(line+1)*capacity) if i not in owned]
            for index in missing:
                cost=freight_facility_expansion_cost(facility,slot_index=index)
                next_slot=index==missing[0] and line*capacity in owned
                result.append((index,cost,next_slot and self._state.cash.amount>=cost,next_slot))
        return result

    def _slot_grid_columns(self, slot_count: int) -> int:
        available_width = self.width() - 332 if self.width() > 360 else 1180
        slot_pitch = FREIGHT_SLOT_CARD_WIDTH + FREIGHT_SLOT_GRID_SPACING
        columns = max(2, min(slot_count, (available_width + FREIGHT_SLOT_GRID_SPACING) // slot_pitch))
        return max(1, columns)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._drawer_open or self._assignment_card_id is not None:
            return
        self._schedule_slot_reflow()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if getattr(self, "_assignment_hidden_cancelled", False):
            self._assignment_hidden_cancelled = False
            self.refresh()
        if self._drawer_open or self._assignment_card_id is not None:
            return
        self._schedule_slot_reflow()

    def _schedule_slot_reflow(self) -> None:
        if self._slot_reflow_pending:
            return
        self._slot_reflow_pending = True
        QTimer.singleShot(0, self, self._refresh_slots_if_column_count_changed)

    def _refresh_slots_if_column_count_changed(self) -> None:
        self._slot_reflow_pending = False
        if self._drawer_open or self._assignment_card_id is not None:return
        facility=self._state.freight.facilities.get(self._selected_facility_id)
        if facility is None:return
        from production_zero.core.freight import FREIGHT_FACILITY_START_SLOTS
        if self._slot_grid_columns(facility.line_capacity) != self._slot_grid_column_count:self.refresh()

    def _capture_slot_scroll(self) -> tuple[int, int] | None:
        if self._slots_scroll is None or not is_qt_object_valid(self._slots_scroll):
            return None
        values = (
            self._slots_scroll.horizontalScrollBar().value(),
            self._slots_scroll.verticalScrollBar().value(),
        )
        self._slot_scroll_values[self._selected_facility_id] = values
        return values

    def _restore_slot_scroll(self, values: tuple[int, int] | None) -> None:
        if values is None:
            values = self._slot_scroll_values.get(self._selected_facility_id)
        if values is None or self._slots_scroll is None or not is_qt_object_valid(self._slots_scroll):
            return
        self._slot_scroll_restore_generation += 1
        generation = self._slot_scroll_restore_generation
        scroll = self._slots_scroll
        self._restore_slot_scroll_late(scroll, values, generation)
        for delay in (0, 16, 50):
            QTimer.singleShot(
                delay,
                lambda scroll=scroll, values=values, generation=generation: self._restore_slot_scroll_late(
                    scroll,
                    values,
                    generation,
                ),
            )

    def _restore_slot_scroll_late(self, scroll: QScrollArea | None, values: tuple[int, int], generation: int) -> None:
        if generation != self._slot_scroll_restore_generation:
            return
        if scroll is None or not is_qt_object_valid(scroll):
            return
        horizontal, vertical = values
        scroll.horizontalScrollBar().setValue(min(horizontal, scroll.horizontalScrollBar().maximum()))
        scroll.verticalScrollBar().setValue(min(vertical, scroll.verticalScrollBar().maximum()))

    def _assignment_panel(self, card_id: str, assignment, enabled: bool) -> QFrame:
        panel = ClickableAssignmentPanel(enabled=enabled)
        panel._route_signature = (assignment.resource_id, assignment.destination_kind) if assignment else None
        panel.setObjectName("freightAssignmentPanel")
        panel.setProperty("cardId", card_id)
        panel.setProperty("paintedFreightControl", True)
        panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        panel.setAutoFillBackground(False)
        def open_assignment():
            from production_zero.ui.group_actions import action_targets
            from production_zero.ui.freight_lines import ordered_selection
            self._open_assignment_view(card_id, action_targets(card_id, self._selected_vehicles, ordered_selection(self)))
        panel.activated.connect(open_assignment)
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


    def _build_assignment_resource_picker(self) -> QWidget:
        wrapper = QFrame()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        search = QLineEdit()
        search.setObjectName("freightAssignmentSearch")
        search.setPlaceholderText("Search resources...")
        search.setText(self._assignment_search_text)
        search.textChanged.connect(self._set_assignment_search)
        category = QComboBox()
        category.setObjectName("freightAssignmentCategoryFilter")
        category.addItem("All")
        for value in self._assignment_categories():
            category.addItem(value)
        self._set_combo_text(category, self._assignment_category_filter)
        category.currentTextChanged.connect(self._set_assignment_category_filter)

        grid_host = ResourceSelectionGridHost()
        grid_host.setObjectName("freightAssignmentResourceGridHost")
        configure_resource_selection_grid_host(grid_host)
        grid_host.resizeEvent = lambda event, host=grid_host: self._on_assignment_grid_host_resized(host, event)
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        self._assignment_resource_grid_host = grid_host
        self._assignment_resource_grid = grid
        self._populate_assignment_resource_grid()
        scroll = QScrollArea()
        scroll.setObjectName("freightAssignmentResourceScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        configure_resource_selection_scroll(scroll)
        scroll.setWidget(grid_host)
        representatives = {r.category: rid for rid, r in self._resources.items()}
        layout.addWidget(ResourceBrowser(search, category, scroll, representatives), 1)
        return wrapper



    def _build_card_selection_view(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("freightCardSelectionView")
        style_secondary(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("ASSIGN FREIGHT CARD")
        title.setObjectName("sectionLabel")
        target = QLabel(f"{self._state.freight.facilities[self._selected_facility_id].name} · Slot {self._drawer_slot_index + 1 if self._drawer_slot_index is not None else '-'}")
        target.setObjectName("freightSelectionTarget")
        close = secondary_action_button("Back", "freightCloseDrawerButton")
        close.clicked.connect(lambda checked=False: self._close_drawer())
        layout.addWidget(SecondaryViewHeader(title, target, close))
        snapshot = getattr(self, "_inventory_target_snapshot", None)
        if snapshot and len(snapshot[3]) > 1:
            hint = QLabel(f"{len(snapshot[3])} empty slots selected · Fill left to right using the chosen Inventory stack; available cards only.")
            hint.setObjectName("groupInstallHint")
            hint.setWordWrap(True)
            layout.addWidget(hint)

        filters_panel = QFrame()
        filters_panel.setObjectName("freightSelectionFilters")
        filters_layout = QHBoxLayout(filters_panel)
        filters_layout.setContentsMargins(10, 8, 10, 8)
        filters_layout.setSpacing(8)
        search = QLineEdit()
        search.setObjectName("freightCardSearch")
        search.setPlaceholderText("SEARCH FREIGHT CARDS")
        search.setMaximumWidth(540)
        search.setText(self._search_text)
        search.textChanged.connect(self._set_search)
        filters_layout.addWidget(search, 2)
        filters_layout.addStretch(1)

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
        chassis = QFrame()
        chassis.setObjectName("secondaryContentChassis")
        chassis_layout = QVBoxLayout(chassis)
        chassis_layout.setContentsMargins(9, 9, 9, 9)
        chassis_layout.addWidget(scroll)
        layout.addWidget(chassis, 1)
        return panel

    def _populate_selection_grid(self) -> None:
        if self._selection_grid is None:
            return
        self._clear_layout(self._selection_grid)
        stacks = self._filtered_drawer_stacks()
        if not stacks:
            supply = secondary_action_button("OPEN INDUSTRIAL SUPPLY", "openIndustrialSupplyButton")
            supply.clicked.connect(lambda: self.supply_requested.emit("Freight"))
            empty = EmptyStatePanel("NO COMPATIBLE FREIGHT CARDS", "Acquire compatible freight cards from Industrial Supply.", action=supply)
            empty.findChild(QWidget, "emptyStateIcon").hide()
            empty.setObjectName("freightSelectionEmpty")
            self._selection_grid.addWidget(empty, 0, 0)
            return
        columns = self._selection_grid_columns()
        for index, stack in enumerate(stacks):
            freight_card = stack.first_card
            definition = self._definitions[freight_card.definition_id]
            if not isinstance(definition, FreightDefinition):
                continue
            tile = FreightSelectionCard(freight_card, definition, stack.quantity, self._state.research)
            tile.selected.connect(self._install_card_from_selection)
            tile.hovered.connect(lambda card_id, widget=tile: self._show_freight_hover(card_id, widget))
            tile.unhovered.connect(self._hide_freight_hover)
            self._selection_grid.addWidget(tile, index // columns, index % columns)
        self._selection_grid.setRowStretch((len(stacks) + columns - 1) // columns, 1)
        self._selection_grid.setColumnStretch(columns, 1)

    def _selection_grid_columns(self) -> int:
        width = self.width() if self.width() > 0 else 900
        return max(2, min(8, (width - 260) // 186))

    def _filtered_drawer_cards(self) -> list[CardInstance]:
        return [stack.first_card for stack in self._filtered_drawer_stacks()]

    def _filtered_drawer_stacks(self) -> list[CardStack]:
        installed = self._state.installed_card_ids() | self._state.installed_freight_card_ids()
        search = self._search_text.lower().strip()
        result: list[CardStack] = []
        for stack in self._state.inventory_card_stacks():
            freight_card = stack.first_card
            if freight_card.card_kind is not CardKind.FREIGHT or freight_card.card_id in installed:
                continue
            definition = self._definitions.get(freight_card.definition_id)
            facility = self._state.freight.facilities[self._selected_facility_id]
            if not isinstance(definition, FreightDefinition) or definition.facility_id != facility.facility_type:
                continue
            if search and search not in f"{definition.name} {freight_card.rarity.value}".lower():
                continue
            result.append(stack)
        return sorted(
            result,
            key=lambda stack: (
                self._definitions[stack.first_card.definition_id].name,
                stack.first_card.rarity.value,
                stack.first_card.output_bonus_tenths,
                stack.first_card.card_id,
            ),
        )

    def _install_card_from_selection(self, card_id: str) -> None:
        if self._drawer_slot_index is None:
            return
        from production_zero.ui.group_actions import fill_inventory_slots, install_snapshot
        facility = self._state.freight.facilities[self._selected_facility_id]
        snapshot = getattr(self, "_inventory_target_snapshot", None)
        if snapshot is None:
            snapshot = install_snapshot(self, "freight", facility, (self._drawer_slot_index,))
        try:
            installed = fill_inventory_slots(self, snapshot, card_id)
        except (ValueError, KeyError, IndexError) as error:
            from production_zero.ui.release_dialogs import inform
            inform(self, "Install cards", str(error))
            return
        self._selected_vehicles.update(facility.slots[i].card_id for i in installed)
        self._selected_empty_slots.difference_update(installed)
        self._reset_drawer_state()
        self.refresh()
        if callback := getattr(self, "_card_operation_changed", None):
            callback()

    def _remove_card(self, slot_index: int) -> None:
        self._command_bus.dispatch(RemoveFreightCard(self._selected_facility_id, slot_index))
        self.refresh()

    def _clear_card_assignment(self, card_id: str) -> None:
        self._state.freight.assignments.pop(card_id, None)
        self.refresh()

    def _open_drawer(self, slot_index: int) -> None:
        from production_zero.ui.group_actions import install_snapshot
        facility = self._state.freight.facilities[self._selected_facility_id]
        if slot_index not in self._selected_empty_slots:
            self._slot_interaction.select_position(slot_index)
        self._inventory_target_snapshot = install_snapshot(self, "freight", facility, self._selected_empty_slots)
        self._drawer_open = True
        self._drawer_slot_index = slot_index
        self._selected_card_id = None
        self.refresh()

    def _close_drawer(self) -> None:
        self._reset_drawer_state()
        self.refresh()

    def _reset_drawer_state(self) -> None:
        self._inventory_target_snapshot = None
        self._drawer_open = False
        self._drawer_slot_index = None
        self._selected_card_id = None
        self._selection_grid = None

    def _select_facility(self, facility_id: str) -> None:
        self._slot_selection_anchor = None
        self._selected_vehicles.clear()
        self._selected_empty_slots.clear()
        self._vehicle_selection_anchor = None
        self._focused_freight_line = None
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


    def _close_assignment_view(self) -> None:
        self._restore_assignment_board()



    def _assignment_target_label(self) -> str:
        if self._assignment_card_id is None:
            return "No Freight Card"
        card = self._state.cards.get(self._assignment_card_id)
        definition = self._definitions.get(card.definition_id) if card is not None else None
        if isinstance(definition, FreightDefinition):
            return definition.name + (" · In transit: cargo is locked until arrival" if self._assignment_card_is_busy() else "")
        return self._assignment_card_id

    def _populate_assignment_resource_grid(self) -> None:
        if self._assignment_resource_grid is None:
            return
        self._cargo_snapshot = self._current_cargo_snapshot()
        resources = self._filtered_assignment_resources()
        retained = retain_grid_tiles(self._assignment_resource_grid, {rid for rid, _ in resources})
        if not resources:
            owned = any(self._state.resources.get(rid) is not None and self._state.resources[rid].amount > 0 for rid in self._resources)
            empty = EmptyStatePanel(
                "NO AVAILABLE CARGO" if owned else "NO CARGO AVAILABLE",
                "No stored resources match these filters." if owned and self._assignment_search_text else
                "No stored resources in this category are available for shipment." if owned else
                "Produce or acquire resources before assigning freight cargo.",
                object_name="freightCargoEmpty",
            )
            empty.findChild(QWidget, "emptyStateIcon").hide()
            self._assignment_resource_grid.addWidget(empty, 0, 0)
            return
        columns = self._assignment_grid_columns()
        for index, (resource_id, resource) in enumerate(resources):
            stock = self._state.ensure_resource(resource_id, resource.default_capacity)
            tile = retained.get(resource_id)
            if tile is None:
                tile = FreightAssignmentResourceTile(resource_id, resource, stock.amount, stock.capacity)
                tile.set_selected(self._draft_resource == resource_id)
                tile.selected.connect(self._select_assignment_resource)
            tile.set_selected(self._draft_resource == resource_id)
            tile.setEnabled(True)
            tile.update_text("freightAssignmentTileStock", f"{stock.amount:g} STORED")
            self._assignment_resource_grid.addWidget(tile, index // columns, index % columns)
        self._assignment_resource_grid.setRowStretch((len(resources) + columns - 1) // columns, 1)
        self._assignment_resource_grid.setColumnStretch(columns, 1)

    def _current_cargo_snapshot(self):
        return (self._assignment_card_is_busy(), tuple(
            (rid, stock.amount, stock.capacity) for rid, stock in self._state.resources.items()
            if rid in self._resources and stock.amount > 0
        ))

    def _filtered_assignment_resources(self) -> list[tuple[str, ResourceDefinition]]:
        search = self._assignment_search_text.lower().strip()
        result: list[tuple[str, ResourceDefinition]] = []
        for resource_id, resource in sorted(self._resources.items(), key=lambda item: item[1].name):
            stock = self._state.resources.get(resource_id)
            if stock is None or stock.amount <= 0:
                continue
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
        width = self._assignment_resource_grid_host.width() if self._assignment_resource_grid_host is not None else self.width()
        return max(1, min(8, width // (RESOURCE_TILE_WIDTH + 10)))

    def _on_assignment_grid_host_resized(self, host: QWidget, event) -> None:
        previous = host.property("assignmentGridColumns")
        current = self._assignment_grid_columns()
        host.setProperty("assignmentGridColumns", current)
        if previous != current:
            self._populate_assignment_resource_grid()
        QWidget.resizeEvent(host, event)


    def _set_assignment_search(self, text: str) -> None:
        self._assignment_search_text = text
        self._populate_assignment_resource_grid()

    def _set_assignment_category_filter(self, text: str) -> None:
        self._assignment_category_filter = text
        self._populate_assignment_resource_grid()


    def _assignment_card_is_busy(self) -> bool:
        return self._assignment_card_id is not None and is_freight_card_busy(self._state.freight, self._assignment_card_id)


    def _set_build_facility_type(self, facility_type: str) -> None:
        self._build_facility_type = facility_type
        self.refresh()

    def _build_facility(self) -> None:
        from production_zero.ui.interaction_polish import BuildingChoiceDialog
        from production_zero.ui.release_dialogs import inform
        definitions = {"garage_depot": "freight.truck", "rail_station": "freight.train", "airport": "freight.aircraft", "harbor": "freight.ship"}
        choices = [(key, FREIGHT_FACILITY_TYPES[key], self._definitions[did], freight_facility_build_cost(self._state.freight, key)) for key, did in definitions.items()]
        quotes={key:cost for key,_label,_definition,cost in choices}
        dialog = BuildingChoiceDialog(self, "BUILD FACILITY", choices, self._state.cash.amount)
        if dialog.exec() and dialog.selected_type:
            try:
                self._command_bus.dispatch(BuildFreightFacility(dialog.selected_type,quotes[dialog.selected_type]))
                self._selected_facility_id = next(reversed(self._state.freight.facilities))
                self.refresh()
            except ValueError as error:
                inform(self, "Build Facility", str(error))

    def _facility_sale(self, facility_id):
        from production_zero.ui.release_freight import sell_facility
        from production_zero.ui.release_dialogs import inform
        try:
            sell_facility(self, facility_id)
        except ValueError as error:
            inform(self, "Freight", str(error))

    def _expand_facility(self, slot_index=None, expected_cost=None, facility_id=None) -> None:
        from production_zero.ui.release_dialogs import inform
        try:
            if facility_id is not None and facility_id!=self._selected_facility_id:
                raise ValueError('Facility changed. Reopen the expansion quote.')
            self._command_bus.dispatch(ExpandFreightFacility(self._selected_facility_id,slot_index,expected_cost))
            self.refresh()
        except (ValueError,KeyError) as error:inform(self,'Freight expansion',str(error))

    def _set_search(self, text: str) -> None:
        self._search_text = text
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
                total += freight_stats(card, definition, self._state.research).capacity
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
        vehicle = self._state.cards.get(card_id)
        if vehicle is not None:
            status = self._vehicle_status(vehicle, assignment, shipment)
        card_widget = widgets.get("card")
        if isinstance(card_widget, QFrame):
            card = self._state.cards.get(card_id)
            definition = self._definitions.get(card.definition_id) if card is not None else None
            if card is not None and isinstance(definition, FreightDefinition):
                stats = freight_stats(card, definition, self._state.research)
                route_label = "ASSIGN ROUTE >"
                if assignment is not None:
                    resource = self._resources.get(assignment.resource_id)
                    resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
                    route_label = f"ROUTE: {resource_name} > {DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind)}"
                card_widget.setProperty("cardTitle", self._freight_card_title(definition))
                card_widget.setProperty("rarity", card.rarity.value)
                card_widget.setProperty("cardMeta", f"MK{card.mk_level} · {card.rarity.value.upper()}")
                card_widget.setProperty("cardDetail", f"CAPACITY {stats.capacity:.0f}")
                card_widget.setProperty("cardSecondary", route_label.upper())
                card_widget.setProperty("cardStatus", status.lower().replace(" ", "_"))
                card_widget.setProperty("cardStatusText", self._compact_status_text(status))
                card_widget.setProperty("cardStatusAccent", self._freight_status_accent(status))
                card_widget.setProperty("cardUtilityText", "CANCEL" if busy or assignment is not None else "REMOVE")
                card_widget.setToolTip("Paused: current delivery will finish; no new departures. Resume from the vehicle menu." if card.paused else "Click to select; drag idle vehicles to move or swap compatible slots. Right-click for vehicle actions.")
                self._set_shipment_progress_properties(card_widget, shipment)
                if isinstance(card_widget, ClickableFreightSlotCard):
                    card_widget._position_installed_controls()
                card_widget.update()
        upgrade = widgets.get("upgrade")
        if upgrade is not None:
            upgrade.update_quote()
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
        route_signature = (assignment.resource_id, assignment.destination_kind) if assignment else None
        if isinstance(assignment_panel, ClickableAssignmentPanel) and assignment_panel._route_signature != route_signature:
            from production_zero.ui.widget_lifecycle import hide_detach_delete
            hide_detach_delete(assignment_panel)
            assignment_panel = self._assignment_panel(card_id, assignment, True)
            assignment_panel.setParent(card_widget)
            widgets["assignment_panel"] = assignment_panel
            card_widget._position_installed_controls()
            assignment_panel.show()
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

    def _vehicle_status(self, vehicle, assignment, shipment):
        from production_zero.core.production_pause import effective_card_paused
        if effective_card_paused(self._state, vehicle.card_id):
            return "PAUSED · FINISHING" if shipment is not None else "PAUSED"
        return self._status_text(assignment, shipment)

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
        from production_zero.ui.freight_statistics import actual_throughput_text
        card = self._state.cards.get(card_id)
        definition = self._definitions.get(card.definition_id) if card is not None else None
        if card is None or not isinstance(definition, FreightDefinition):
            self._hide_freight_hover()
            return
        stats = freight_stats(card, definition, self._state.research)
        assignment = self._state.freight.assignments.get(card_id)
        shipment = self._active_shipment_for(card_id)
        status = self._vehicle_status(card, assignment, shipment)
        if assignment is None:
            assignment_text = "Unassigned"
        else:
            resource = self._resources.get(assignment.resource_id)
            resource_name = resource.name if resource is not None else assignment.resource_id.replace("_", " ").title()
            destination = DESTINATION_LABELS.get(assignment.destination_kind, assignment.destination_kind.title())
            if assignment.destination_kind == "market":
                assignment_text = f"{resource_name} -> {destination}"
            else:
                assignment_text = f"{resource_name} -> {destination}"
        values = {
            "Freight Type": definition.family.value.title(),
            "Rarity": card.rarity.value.title(),
            "Bonus": f"+{card.output_bonus_percent:.1f}%",
            "Capacity": f"{stats.capacity:.0f}",
            "Travel Time": self._format_time(stats.transport_time_seconds),
            "Full-load capacity": self._safe_capacity_per_cycle(stats),
            "THEORETICAL THROUGHPUT": theoretical_throughput_text(stats),
            "ACTUAL THROUGHPUT": actual_throughput_text(
                self._state.freight.delivery_statistics.rate(card_id=card_id)),
            "Assignment": assignment_text,
            "Status": status,
        }
        sections = list(values.items())
        signature = (
            card_id,
            definition.definition_id,
            tuple(label for label, _value in sections),
        )
        if self._hover_popup is None:
            return
        if self._hover_popup.details_signature != signature:
            icon = card_hover_icon(definition, size=42)
            self._hover_popup.set_details(definition.name, icon, sections, signature)
            for label in self._hover_popup.findChildren(QLabel, "cardHoverLabel"):
                if label.text() in {"THEORETICAL THROUGHPUT", "ACTUAL THROUGHPUT"}:
                    label.setWordWrap(True)
                    label.setMinimumHeight(label.fontMetrics().lineSpacing() * 2)
        else:
            self._hover_popup.update_values(sections)
        if self._hover_popup.isVisible():
            source = self._runtime_widgets.get(card_id, {}).get("card")
            if source is not None:
                self._hover_popup.show_for(source)

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
        from math import isfinite
        if not isfinite(seconds) or seconds <= 0:
            return "Unavailable"
        total = max(0, round(seconds))
        minutes, secs = divmod(total, 60)
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"

    def _safe_capacity_per_cycle(self, stats):
        from math import isfinite
        if not all(isfinite(v) and v > 0 for v in (stats.capacity, stats.transport_time_seconds)):
            return "Unavailable"
        value = stats.capacity_per_cycle
        return f"{value:.2f}/cycle" if isfinite(value) else "Unavailable"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._assignment_card_id is not None:
            self._close_assignment_view()
            event.accept()
            return
        super().keyPressEvent(event)

    def show_frontscreen(self):
        if self._assignment_card_id is not None:
            self._close_assignment_view()
        if self._drawer_slot_index is not None:
            self._close_drawer()
        self._hide_freight_hover()

    def hideEvent(self, event):
        if self._assignment_card_id is not None:
            self._reset_assignment_state()
            self._assignment_hidden_cancelled = True
        super().hideEvent(event)

    def _compact_status_text(self, status: str) -> str:
        if status.startswith("PAUSED"):
            return "PAUSED"
        if status.startswith("WAITING"):
            return "WAITING"
        return status

    def _freight_card_title(self, definition: FreightDefinition) -> str:
        return definition.family.value.replace("_", " ").upper()

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
        if assignment.destination_kind == "contract" and not self._has_matching_contract_need(assignment.resource_id):
            return "WAITING · NO CONTRACT"
        return "READY"

    def _has_matching_contract_need(self, resource_id: str) -> bool:
        from production_zero.core.contract_allocation import allocate_contract_cargo
        return bool(allocate_contract_cargo(self._state, resource_id, 1.))

    def _sorted_facilities(self):
        from production_zero.core.building_order import ordered_building_ids
        order = {facility_type: index for index, facility_type in enumerate(FACILITY_TYPE_ORDER)}
        default = sorted(
            self._state.freight.facilities.items(),
            key=lambda item: (order.get(item[1].facility_type, 99), item[1].name, item[0]),
        )
        return [(uid, self._state.freight.facilities[uid]) for uid in
                ordered_building_ids(self._state, 'freight', (uid for uid, _ in default))]

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)


def theoretical_throughput_text(stats):
    from math import isfinite
    capacity, seconds = stats.capacity, stats.transport_time_seconds
    if not all(isfinite(v) and v > 0 for v in (capacity, seconds)):
        return "Unavailable"
    value = (capacity / seconds) * 60
    if not isfinite(value):
        return "Unavailable"
    if value >= 1e9 or value < .01:
        return f"{value:.3g} units/min"
    return f"{value:,.2f} units/min"
