from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.cards import RARITY_BONUS_RANGES_TENTHS, create_card_instance
from production_zero.core.commands import CommandBus, CraftRarityCard, RecycleCards
from production_zero.core.crafting import CRAFT_INPUT_COUNT, RARITY_CRAFT_UPGRADES, preview_crafted_card
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.enums import MachineType, Rarity
from production_zero.core.inventory import CardInventoryRow, build_card_inventory_rows
from production_zero.core.recycling import scrap_value_for_card
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup, HoverableCardFrame
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.game_ui import Accent, GAME_UI_TOKENS, InteractionState, MaterialLevel, draw_game_panel, draw_track_surface
from production_zero.ui.game_ui.rendering import draw_hazard_stripes, draw_machine_card_prototype
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.resource_icons import ResourceIconWidget, card_resource_icon_signature, resource_accent_key, resource_icon_key
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.widget_lifecycle import clear_layout_safely
from production_zero.ui.inventory_workspace import InventoryWorkspaceMixin


INVENTORY_CARD_WIDTH = 166
INVENTORY_CARD_HEIGHT = 224
INVENTORY_CARD_SPACING = 10
INVENTORY_CARD_HEADER_HEIGHT = 54
INVENTORY_CARD_TITLE_HEIGHT = 30
def _hidden_label(parent: QWidget, object_name: str, text: str) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    label.hide()
    return label


class InventoryCardsHeader(MainTabHeader):
    def __init__(self) -> None:
        super().__init__(
            object_name="inventoryCardsHeader",
            title="INVENTORY",
            subtitle="CARD COLLECTION / MANAGEMENT",
            title_object_name="inventoryHeroTitle",
            subtitle_object_name="inventoryHeroSubtitle",
            accent=Accent.PROCESSOR,
        )


class InventoryCardFrame(HoverableCardFrame):
    def __init__(
        self,
        row: CardInventoryRow,
        *,
        title: str,
        family: str,
        meta: str,
        detail: str,
        selected: bool,
        disabled: bool = False,
        status_text: str | None = None,
        preview: bool = False,
    ) -> None:
        super().__init__()
        self._title = title
        self._family = family
        self._meta = meta
        self._detail = detail
        self._quantity = row.quantity
        self._status = status_text or row.status
        self._selected = selected
        self._disabled = disabled
        self._preview = preview
        self.setObjectName("inventoryCard")
        self.setProperty("rarity", row.rarity.value)
        self.setProperty("selected", selected)
        self.setProperty("cardType", family)
        self.setProperty("quantity", row.quantity)
        self.setProperty("statusText", row.status)
        self.setProperty("cardTitle", title)
        self.setProperty("cardMeta", meta)
        self.setProperty("cardDetail", detail)
        self.setProperty("cardStatusText", self._status)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        draw_machine_card_prototype(
            painter,
            rect,
            title=self._title,
            family=self._family,
            meta=self._meta,
            detail=self._detail,
            secondary=self._status.upper(),
            disabled=self._disabled,
            active=self._status == "In Use",
            hover=not self._preview and (self.underMouse() or self._selected),
        )
        self._draw_quantity_badge(painter, rect)
        if self._selected and not self._preview:
            painter.setPen(QPen(QColor(98, 190, 232, 190), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 10, 10)
        painter.end()

    def _draw_quantity_badge(self, painter: QPainter, rect: QRectF) -> None:
        text = f"x{self._quantity}"
        font = GAME_UI_TOKENS.typography.status_label()
        font.setPointSize(8)
        painter.setFont(font)
        max_width = max(34.0, rect.width() - 24.0)
        while font.pointSize() > 5 and painter.fontMetrics().horizontalAdvance(text) + 18.0 > max_width:
            font.setPointSize(font.pointSize() - 1)
            painter.setFont(font)
        width = min(max_width, max(34.0, painter.fontMetrics().horizontalAdvance(text) + 18.0))
        badge = QRectF(rect.right() - width - 12, rect.bottom() - 28, width, 18)
        body = QLinearGradient(badge.topLeft(), badge.bottomLeft())
        body.setColorAt(0.0, QColor(255, 255, 255, 30))
        body.setColorAt(0.55, QColor(8, 11, 11, 220))
        body.setColorAt(1.0, QColor(0, 0, 0, 180))
        painter.setPen(QPen(GAME_UI_TOKENS.colors.accent(Accent.STORAGE, 126), 1))
        painter.setBrush(body)
        painter.drawRoundedRect(badge, 5, 5)
        painter.setPen(QColor("#eff8f4"))
        painter.drawText(badge.adjusted(1, 0, -1, 0), Qt.AlignmentFlag.AlignCenter, text)


class CraftConnectorSign(QFrame):
    def __init__(self, *, crafting: bool = False) -> None:
        super().__init__()
        self._crafting = crafting
        self.setObjectName("craftConversionSign")
        self.setFixedSize(140, 176)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(5, 8, -5, -8)
        body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        body.setColorAt(0.0, QColor(219, 64, 43))
        body.setColorAt(0.45, QColor(171, 32, 24))
        body.setColorAt(1.0, QColor(92, 20, 16))
        painter.setPen(QPen(QColor(83, 28, 19), 1.5))
        painter.setBrush(body)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor(255, 240, 216, 74), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 5, 5)
        draw_hazard_stripes(
            painter, QRectF(rect.left() + 10, rect.top() + 8, rect.width() - 20, 6),
            primary=QColor(246, 240, 226), secondary=QColor(171, 32, 24), stripe_width=9, radius=1,
        )
        for x in (rect.left() + 7, rect.right() - 7):
            painter.setPen(QPen(QColor(72, 54, 38), 1))
            painter.setBrush(QColor(231, 220, 190))
            painter.drawEllipse(QPointF(x, rect.bottom() - 7), 2, 2)

        font = GAME_UI_TOKENS.typography.micro_label()
        font.setPointSize(12)
        font.setWeight(font.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor("#f4e7d8"))
        painter.drawText(rect.adjusted(4, 12, -4, -rect.height() * 0.56), Qt.AlignmentFlag.AlignCenter,
                         f"{CRAFT_INPUT_COUNT} → 1")

        arrow_rect = rect.adjusted(18, rect.height() * 0.34, -18, -48)
        arrow = QPolygonF([
            QPointF(arrow_rect.left(), arrow_rect.center().y() - arrow_rect.height() * 0.22),
            QPointF(arrow_rect.center().x(), arrow_rect.center().y() - arrow_rect.height() * 0.22),
            QPointF(arrow_rect.center().x(), arrow_rect.top()),
            QPointF(arrow_rect.right(), arrow_rect.center().y()),
            QPointF(arrow_rect.center().x(), arrow_rect.bottom()),
            QPointF(arrow_rect.center().x(), arrow_rect.center().y() + arrow_rect.height() * 0.22),
            QPointF(arrow_rect.left(), arrow_rect.center().y() + arrow_rect.height() * 0.22),
        ])
        painter.setPen(QPen(QColor(255, 216, 56, 210), 1.4))
        painter.setBrush(QColor(255, 195, 28, 230))
        painter.drawPolygon(arrow)
        painter.setPen(QColor("#fff2ce"))
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(QRectF(rect.left() + 5, rect.bottom() - 36, rect.width() - 10, 28),
                         Qt.AlignmentFlag.AlignCenter, "RARITY\nCONVERSION" if self._crafting else "ENHANCEMENT")
        painter.end()


class InventoryFilterScroll(QScrollArea):
    def __init__(self, content: QWidget, object_name: str, preferred_width: int) -> None:
        super().__init__()
        self._content = content
        self._preferred_width = preferred_width
        self.setObjectName(object_name)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWidget(content)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = self.widget().minimumSizeHint() if self.widget() is not None else super().minimumSizeHint()
        return QSize(160, hint.height() + 2)

    def sizeHint(self) -> QSize:  # noqa: N802
        hint = self.widget().sizeHint() if self.widget() is not None else super().sizeHint()
        return QSize(min(self._preferred_width, hint.width()), hint.height() + 2)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._sync_content_geometry()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._sync_content_geometry()

    def _sync_content_geometry(self) -> None:
        hint = self._content.minimumSizeHint()
        width = max(self.viewport().width(), hint.width())
        height = max(self.viewport().height(), hint.height())
        self._content.resize(width, height)


class InventoryView(InventoryWorkspaceMixin, QWidget):
    def __init__(
        self,
        state: GameState,
        definitions: dict[str, CardDefinition],
        resource_definitions: dict[str, ResourceDefinition] | None = None,
        command_bus: CommandBus | None = None,
        on_state_changed=None,
        *,
        release_mode: bool = True,
    ) -> None:
        super().__init__()
        self._release_mode = release_mode
        self._state = state
        self._definitions = definitions
        self._resource_definitions = resource_definitions or {}
        self._command_bus = command_bus
        self._on_state_changed = on_state_changed
        self._rows: tuple[CardInventoryRow, ...] = ()
        self._visible_card_rows: tuple[CardInventoryRow, ...] = ()
        self._selected_card_row: CardInventoryRow | None = None
        self._scrap_confirmation_card_id: str | None = None
        self._scrap_confirmation_quantity = 1
        self._craft_target_definition_id: str | None = None
        self._selected_craft_material_ids: tuple[str, ...] = ()
        self._craft_selection_mode = "target"
        self._hover_row: CardInventoryRow | None = None
        self._hover_popup: CardHoverInfoPopup | None = None

        if release_mode:
            self._build_workspace()
            return

        # Retained only for explicit legacy-component compatibility checks.
        # The application and the default constructor use the card workspace.

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = InventoryCardsHeader()
        scrap_tile, self._scrap_label = self._build_kpi("Industrial Scrap", "industrialScrapLabel")
        scrap_tile.setObjectName("inventoryScrapModule")
        self._total_cards_label = QLabel(self)
        self._total_cards_label.setObjectName("inventoryTotalCardsLabel")
        self._total_cards_label.hide()
        self._stacks_label = QLabel(self)
        self._stacks_label.setObjectName("inventoryStacksLabel")
        self._stacks_label.hide()
        self._storage_label = QLabel(self)
        self._storage_label.setObjectName("inventoryStorageLabel")
        self._storage_label.hide()
        self._storage_info = QLabel(self)
        self._storage_info.setObjectName("inventoryStorageInfo")
        header.add_status_module(scrap_tile)
        self._storage_info.hide()
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("inventorySubTabs")
        self._tabs.addTab(self._build_cards_tab(), "Cards")
        self._tabs.addTab(self._build_crafting_panel(), "Crafting")
        self._tabs.currentChanged.connect(self._hide_card_hover)
        root.addWidget(self._tabs, 1)

        self._selection_scrolls = (
            (self._craft_target_scroll, self._refresh_craft_target_grid),
            (self._craft_material_scroll, self._refresh_craft_material_grid),
        )
        for scroll, _ in self._selection_scrolls:
            scroll.viewport().installEventFilter(self)

        self.refresh()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if self._release_mode:
            return self._workspace_event(watched, event) or super().eventFilter(watched, event)
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            if any(watched is scroll.viewport() for scroll, _ in self._selection_scrolls):
                QTimer.singleShot(0, self, self._refresh_selection_grid_geometry)
        return super().eventFilter(watched, event)

    def _refresh_selection_grid_geometry(self) -> None:
        for scroll, refresh in self._selection_scrolls:
            if scroll.isVisible() and scroll.property("gridColumns") != self._grid_columns_for_scroll(scroll):
                refresh()

    def _configure_selection_grid(self, grid: QGridLayout, scroll: QScrollArea) -> int:
        columns = self._grid_columns_for_scroll(scroll)
        for column in range(max(grid.columnCount(), columns + 1)):
            grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH if column < columns else 0)
            grid.setColumnStretch(column, 1 if column == columns else 0)
        scroll.setProperty("gridColumns", columns)
        return columns

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._release_mode:
            self._layout_workspace()
            return
        if hasattr(self, "_cards_grid"):
            self._refresh_cards_table()
        if hasattr(self, "_craft_target_grid"):
            self._refresh_crafting_panel()

    def _build_kpi(self, title: str, value_object_name: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("inventoryKpi")
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("inventoryKpiLabel")
        value = QLabel()
        tile.setMinimumWidth(150)
        value.setObjectName(value_object_name)
        layout.addWidget(title_label)
        layout.addWidget(value)
        return tile, value

    def refresh(self) -> None:
        if self._release_mode:
            self._refresh_workspace()
            return
        self._rows = build_card_inventory_rows(self._state, self._definitions)
        self._total_cards_label.setText(str(len(self._state.cards)))
        self._stacks_label.setText(str(len(self._state.inventory_card_stacks())))
        self._scrap_label.setText(str(self._state.scrap.amount))
        self._refresh_storage_status()
        self._refresh_filter_options()
        self._refresh_cards_table()
        self._refresh_action_panel()
        self._refresh_crafting_panel()

    def _refresh_storage_status(self) -> None:
        self._storage_label.setText(f"{self._state.used_storage:.0f} / {self._state.storage_capacity:.0f}")
        self._storage_info.setText("All physical resources share this warehouse capacity. Storage upgrades are in the topbar.")

    def _build_cards_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        shell = QFrame()
        shell.setObjectName("inventoryCardsBrowserShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(14, 14, 14, 14)
        shell_layout.setSpacing(12)

        toolbar = QFrame()
        toolbar.setObjectName("inventoryFilters")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(14)

        self._search = QLineEdit()
        self._search.setObjectName("inventorySearch")
        self._search.setPlaceholderText("Search cards")
        self._search.textChanged.connect(self._refresh_cards_table)
        self._type_filter = self._build_filter("inventoryTypeFilter")
        self._rarity_filter = self._build_filter("inventoryRarityFilter")
        self._status_filter = self._build_filter("inventoryStatusFilter")
        self._sort = self._build_filter("inventorySort")
        self._sort.addItems(["Name", "Rarity", "Quantity", "Status"])

        toolbar_layout.addWidget(self._labeled_filter("SEARCH", self._search, object_name="inventorySearchGroup"))
        self._type_chip_layout = self._add_chip_group(toolbar_layout, "TYPE")
        self._rarity_chip_layout = self._add_chip_group(toolbar_layout, "RARITY")
        self._status_chip_layout = self._add_chip_group(toolbar_layout, "STATUS")
        self._sort_chip_layout = self._add_chip_group(toolbar_layout, "SORT")
        toolbar_layout.addStretch(1)
        self._inventory_filter_scroll = InventoryFilterScroll(toolbar, "inventoryFilterScroll", 1180)
        shell_layout.addWidget(self._inventory_filter_scroll)

        self._card_scroll = QScrollArea()
        self._card_scroll.setObjectName("cardInventoryScroll")
        self._card_scroll.setWidgetResizable(True)
        self._card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._card_grid_container = QWidget()
        self._card_grid_container.setObjectName("cardInventoryGrid")
        self._cards_grid = QGridLayout(self._card_grid_container)
        self._cards_grid.setContentsMargins(2, 2, 2, 2)
        self._cards_grid.setSpacing(INVENTORY_CARD_SPACING)
        self._card_scroll.setWidget(self._card_grid_container)
        shell_layout.addWidget(self._card_scroll, 1)
        layout.addWidget(shell, 1)
        self._action_panel = QFrame()
        self._action_panel.setObjectName("inventoryActionPanel")
        self._action_panel.setMinimumHeight(76)
        self._action_panel.setMaximumHeight(88)
        self._action_layout = QHBoxLayout(self._action_panel)
        self._action_layout.setContentsMargins(14, 10, 14, 10)
        self._action_layout.setSpacing(12)
        layout.addWidget(self._action_panel)
        return tab

    def _build_filter(self, object_name: str) -> QComboBox:
        combo = QComboBox(self)
        combo.setObjectName(object_name)
        combo.hide()
        combo.currentTextChanged.connect(self._refresh_cards_table)
        return combo

    def _add_chip_group(self, parent_layout: QHBoxLayout, label_text: str) -> QHBoxLayout:
        wrapper = QWidget()
        wrapper.setObjectName("inventoryFilterGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(5)
        layout.addWidget(label)
        layout.addLayout(chips)
        parent_layout.addWidget(wrapper)
        return chips

    def _labeled_filter(self, label_text: str, control: QWidget, *, object_name: str = "") -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName(object_name or "inventoryFilterGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        layout.addWidget(control)
        return wrapper

    def _refresh_filter_options(self) -> None:
        self._set_options(self._type_filter, ["All", *sorted({self._row_type_filter_label(row) for row in self._rows})])
        self._set_options(self._rarity_filter, ["All", *[rarity.value.title() for rarity in Rarity]])
        self._set_options(self._status_filter, ["All", "Available", "In Use"])
        if hasattr(self, "_type_chip_layout"):
            self._refresh_chip_group(self._type_chip_layout, self._type_filter, self._type_filter.objectName())
            self._refresh_chip_group(self._rarity_chip_layout, self._rarity_filter, self._rarity_filter.objectName())
            self._refresh_chip_group(self._status_chip_layout, self._status_filter, self._status_filter.objectName())
            self._refresh_chip_group(self._sort_chip_layout, self._sort, self._sort.objectName())

    def _set_options(self, combo: QComboBox, options: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        if current in options:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _refresh_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        self._clear_layout(layout)
        current = combo.currentText() or "All"
        for option in [combo.itemText(index) for index in range(combo.count())]:
            chip = QPushButton(self._chip_display_text(group, option))
            chip.setObjectName("inventoryFilterChip")
            chip.setProperty("filterGroup", group)
            chip.setProperty("filterValue", option)
            chip.setProperty("active", option == current)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, value=option, target=combo: self._set_chip_filter_value(target, value))
            layout.addWidget(chip)

    def _chip_display_text(self, group: str, option: str) -> str:
        return option.upper()

    def _set_chip_filter_value(self, combo: QComboBox, value: str) -> None:
        if combo.currentText() == value:
            return
        combo.setCurrentText(value)
        self._refresh_filter_options()

    def _refresh_cards_table(self, *args) -> None:
        if not hasattr(self, "_cards_grid"):
            return
        rows = [row for row in self._rows if self._matches_filters(row)]
        rows = self._sort_rows(rows)
        current_card_id = self._selected_card_row.card.card_id if self._selected_card_row else None
        self._visible_card_rows = tuple(rows)
        self._clear_layout(self._cards_grid)
        selected_row = None
        columns = self._inventory_grid_columns()
        self._reset_inventory_grid_columns(columns + 3)
        sparse_columns = min(columns, len(rows)) if 0 < len(rows) <= 5 else columns
        if 0 < len(rows) <= 5:
            self._cards_grid.setContentsMargins(2, 12, 2, 12)
            self._cards_grid.setColumnStretch(sparse_columns, 1)
            for column in range(sparse_columns):
                self._cards_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
        else:
            side_margin = self._inventory_grid_side_margin(len(rows), columns)
            self._cards_grid.setContentsMargins(side_margin, 12, side_margin, 12)
            for column in range(columns):
                self._cards_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
        if not rows:
            empty = EmptyStatePanel(
                "No cards found" if self._rows else "No cards in inventory",
                "Adjust your filters to reveal more cards." if self._rows else "Packs, supply purchases, and contract rewards will appear here.",
                accent="storage",
                object_name="inventoryEmptyState",
                parent=self._card_grid_container,
            )
            self._cards_grid.addWidget(empty, 0, 0, 1, max(1, columns), Qt.AlignmentFlag.AlignCenter)
            self._cards_grid.setRowStretch(1, 1)
            if current_card_id is not None:
                self._selected_card_row = None
            self._refresh_action_panel()
            return
        for row_index, row in enumerate(rows):
            card = self._build_inventory_card(row, row.card.card_id == current_card_id)
            layout_column = row_index % sparse_columns
            layout_row = row_index // sparse_columns
            self._cards_grid.addWidget(
                card,
                layout_row,
                layout_column,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            if row.card.card_id == current_card_id:
                selected_row = row
        if len(rows) > 5:
            self._cards_grid.setColumnStretch(columns, 1)
        if current_card_id is not None and selected_row is None:
            self._selected_card_row = None
        elif selected_row is not None:
            self._selected_card_row = selected_row
        self._refresh_action_panel()

    def _inventory_grid_side_margin(self, item_count: int, columns: int) -> int:
        if item_count <= 0 or item_count > 5:
            return 2
        width = self._card_scroll.viewport().width() if hasattr(self, "_card_scroll") else self.width()
        visible_columns = max(1, min(columns, item_count))
        used = visible_columns * INVENTORY_CARD_WIDTH + max(0, visible_columns - 1) * INVENTORY_CARD_SPACING
        return max(2, (width - used) // 2)

    def _reset_inventory_grid_columns(self, minimum_columns: int) -> None:
        column_count = max(minimum_columns, self._cards_grid.columnCount() + 1)
        for column in range(column_count):
            self._cards_grid.setColumnMinimumWidth(column, 0)
            self._cards_grid.setColumnStretch(column, 0)

    def _build_inventory_card(self, row: CardInventoryRow, selected: bool) -> QFrame:
        family = self._card_game_family(row)
        card = InventoryCardFrame(
            row,
            title=self._card_game_title(row).upper(),
            family=family,
            meta=self._card_game_meta(row).upper(),
            detail=self._card_game_detail(row).upper(),
            selected=selected,
        )
        card.setProperty("cardType", self._card_type_key(row))
        card.mousePressEvent = lambda event, inventory_row=row: self._select_card_row(inventory_row)
        card.hovered.connect(lambda inventory_row=row, widget=card: self._show_card_hover(inventory_row, widget))
        card.unhovered.connect(self._hide_card_hover)
        _hidden_label(card, "inventoryCardName", row.definition.name)
        _hidden_label(card, "inventoryCardRarityMeta", row.rarity.value.title())
        _hidden_label(card, "inventoryCardRarity", row.rarity.value.title())
        _hidden_label(card, "inventoryCardFunction", self._card_function_label(row).upper())
        _hidden_label(card, "inventoryCardBonus", f"+{row.card.output_bonus_percent:.1f}%")
        _hidden_label(card, "inventoryCardQuantity", f"Qty {row.quantity}")
        _hidden_label(card, "inventoryCardStatus", row.status)
        icon_key, accent_key, icon_resource_id = self._icon_signature(row)
        icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=1)
        icon.setObjectName("inventoryCardIcon")
        icon.setParent(card)
        icon.hide()
        return card

    def _inventory_grid_columns(self) -> int:
        width = self._card_scroll.viewport().width() if hasattr(self, "_card_scroll") else self.width()
        width = max(width, self.width())
        if width < INVENTORY_CARD_WIDTH:
            width = 900
        pitch = INVENTORY_CARD_WIDTH + INVENTORY_CARD_SPACING
        return max(1, min(8, width // pitch))

    def _card_type_key(self, row: CardInventoryRow) -> str:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return "energy"
        if isinstance(definition, FreightDefinition):
            return "freight"
        return "card"

    def _card_game_family(self, row: CardInventoryRow) -> str:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return definition.energy_type.value
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return "processor"

    def _card_game_title(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, FreightDefinition):
            return row.definition.family.value
        return row.definition.name

    def _card_game_meta(self, row: CardInventoryRow) -> str:
        return row.rarity.value

    def _card_game_detail(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, MachineDefinition):
            production = row.definition.production_option(
                row.definition.default_production_id_for_card_definition(row.card.definition_id)
            )
            amount = production.output_amount_for(row.definition) * (1 + row.card.output_bonus_percent / 100)
            return f"+{amount:.0f}/cycle"
        if isinstance(row.definition, EnergyDefinition):
            return f"+{row.definition.base_power_output:.0f} MW"
        if isinstance(row.definition, FreightDefinition):
            stats = freight_stats(row.card, row.definition)
            return f"{stats.capacity:.0f} cap"
        return self._card_function_label(row)

    def _card_function_label(self, row: CardInventoryRow) -> str:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            return definition.name
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.title()
        return row.card_type.title()

    def _icon_signature(self, row: CardInventoryRow) -> tuple[str, str, str]:
        return card_resource_icon_signature(row.definition, row.card.definition_id)

    def _sort_rows(self, rows: list[CardInventoryRow]) -> list[CardInventoryRow]:
        sort = self._sort.currentText() if hasattr(self, "_sort") else "Name"
        if sort == "Rarity":
            order = {rarity: index for index, rarity in enumerate(Rarity)}
            return sorted(rows, key=lambda row: (order[row.rarity], row.definition.name, row.card.output_bonus_tenths))
        if sort == "Quantity":
            return sorted(rows, key=lambda row: (-row.quantity, row.definition.name))
        if sort == "Status":
            return sorted(rows, key=lambda row: (row.status, row.definition.name))
        return sorted(rows, key=lambda row: row.definition.name)

    def _select_card_row(self, row: CardInventoryRow) -> None:
        if self._selected_card_row is None or self._selected_card_row.card.card_id != row.card.card_id:
            self._scrap_confirmation_card_id = None
        self._selected_card_row = row
        self._refresh_cards_table()

    def _refresh_action_panel(self) -> None:
        if not hasattr(self, "_action_layout"):
            return
        self._clear_layout(self._action_layout)
        row = self._selected_card_row
        self._action_panel.show()
        if row is None:
            self._action_layout.addStretch(1)
            return
        if self._scrap_confirmation_card_id == row.card.card_id and row.status == "Available":
            self._build_scrap_confirmation(row)
            return
        self._scrap_confirmation_card_id = None

        summary = QFrame()
        summary.setObjectName("inventoryScrapCardSummary")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(12, 7, 12, 7)
        summary_layout.setSpacing(2)
        title = QLabel(row.definition.name.upper())
        title.setObjectName("inventoryActionTitle")
        summary_layout.addWidget(title)
        availability = QLabel(f"{row.status}: {row.quantity}")
        availability.setObjectName("inventoryScrapAvailability")
        summary_layout.addWidget(availability)
        self._action_layout.addWidget(summary)
        if row.status == "Available":
            quantity = QSpinBox()
            quantity.setObjectName("scrapQuantity")
            quantity.setRange(1, max(1, row.quantity))
            quantity.setAlignment(Qt.AlignmentFlag.AlignCenter)
            quantity.setFixedSize(62, 48)
            quantity.setToolTip("Scrap quantity")
            self._action_layout.addWidget(quantity)

            reward_block = QFrame()
            reward_block.setObjectName("inventoryScrapRewardBlock")
            reward_layout = QVBoxLayout(reward_block)
            reward_layout.setContentsMargins(12, 6, 12, 6)
            reward_layout.setSpacing(1)
            reward_label = QLabel("RECEIVE")
            reward_label.setObjectName("inventoryScrapRewardLabel")
            reward = QLabel()
            reward.setObjectName("inventoryScrapReward")
            update_reward = lambda value: reward.setText(
                f"{scrap_value_for_card(row.card) * value} INDUSTRIAL SCRAP"
            )
            quantity.valueChanged.connect(update_reward)
            update_reward(quantity.value())
            reward_layout.addWidget(reward_label)
            reward_layout.addWidget(reward)
            self._action_layout.addWidget(reward_block)
            button = QPushButton("SCRAP")
            button.setObjectName("scrapCardButton")
            button.setMinimumHeight(48)
            button.setEnabled(self._command_bus is not None)
            button.clicked.connect(
                lambda checked=False, inventory_row=row, spin=quantity: self._begin_scrap_confirmation(
                    inventory_row, spin.value()
                )
            )
            self._action_layout.addWidget(button)
            self._action_layout.addStretch(1)
        else:
            status = QLabel("INSTALLED / IN USE")
            status.setObjectName("inventoryScrapUnavailable")
            self._action_layout.addWidget(status)
            self._action_layout.addStretch(1)

    def _begin_scrap_confirmation(self, row: CardInventoryRow, quantity: int) -> None:
        if self._command_bus is None or row.status != "Available":
            return
        self._scrap_confirmation_card_id = row.card.card_id
        self._scrap_confirmation_quantity = min(max(1, quantity), row.quantity)
        self._refresh_action_panel()

    def _build_scrap_confirmation(self, row: CardInventoryRow) -> None:
        quantity = min(max(1, self._scrap_confirmation_quantity), row.quantity)
        title = QLabel("CONFIRM SCRAP")
        title.setObjectName("inventoryActionTitle")
        self._action_layout.addWidget(title)
        detail = QLabel(f"{row.definition.name} · {row.rarity.value.title()}")
        detail.setObjectName("scrapConfirmationCard")
        self._action_layout.addWidget(detail)
        quantity_label = QLabel(f"Quantity: {quantity}")
        quantity_label.setObjectName("scrapConfirmationQuantity")
        self._action_layout.addWidget(quantity_label)
        reward = QLabel(
            f"RECEIVE: {scrap_value_for_card(row.card) * quantity} INDUSTRIAL SCRAP"
        )
        reward.setObjectName("inventoryScrapReward")
        self._action_layout.addWidget(reward)
        self._action_layout.addStretch(1)
        cancel = QPushButton("CANCEL")
        cancel.setObjectName("cancelScrapButton")
        cancel.clicked.connect(self._cancel_scrap_confirmation)
        self._action_layout.addWidget(cancel)
        confirm = QPushButton("SCRAP")
        confirm.setObjectName("confirmScrapButton")
        confirm.clicked.connect(self._confirm_scrap)
        self._action_layout.addWidget(confirm)

    def _cancel_scrap_confirmation(self) -> None:
        self._scrap_confirmation_card_id = None
        self._refresh_action_panel()

    def _confirm_scrap(self) -> None:
        row = self._selected_card_row
        if (
            row is None
            or row.status != "Available"
            or row.card.card_id != self._scrap_confirmation_card_id
        ):
            self._cancel_scrap_confirmation()
            return
        quantity = min(max(1, self._scrap_confirmation_quantity), row.quantity)
        self._scrap_confirmation_card_id = None
        self._recycle(row, quantity)

    def _show_card_hover(self, row: CardInventoryRow, source: QWidget) -> None:
        self._hover_row = row
        if self._hover_popup is None:
            self._hover_popup = CardHoverInfoPopup(self, embedded=True)
        icon_key, accent_key, icon_resource_id = self._icon_signature(row)
        sections = self._hover_sections(row)
        signature = (
            row.card.card_id,
            row.quantity,
            row.status,
            tuple(label for label, _value in sections),
            icon_key,
            accent_key,
            icon_resource_id,
        )
        if self._hover_popup.details_signature != signature:
            icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=34)
            self._hover_popup.set_details(row.definition.name, icon, sections, signature)
        else:
            self._hover_popup.update_values(sections)
        self._hover_popup.show_for(source)

    def _hide_card_hover(self) -> None:
        self._hover_row = None
        if self._hover_popup is not None:
            self._hover_popup.hide()

    def _hover_sections(self, row: CardInventoryRow) -> list[tuple[str, str]]:
        sections = [
            ("Rarity", row.rarity.value.title()),
            ("Type", self._card_function_label(row)),
            ("Bonus", f"+{row.card.output_bonus_percent:.1f}%"),
            ("Quantity", str(row.quantity)),
            ("Status", row.status),
        ]
        if self._release_mode:
            sections.insert(0, ("MK", str(row.card.mk_level)))
        from production_zero.core.cards import CardStackKey
        key = CardStackKey.from_card(row.card)
        owned = [c for c in self._state.cards.values() if CardStackKey.from_card(c) == key]
        installed = self._state.installed_card_ids() | self._state.installed_freight_card_ids()
        used = sum(c.card_id in installed for c in owned)
        sections.extend([("Owned", str(len(owned))), ("Available", str(len(owned) - used)), ("In Use", str(used))])
        sections.extend(self._performance_pairs(row))
        return sections

    def _performance_pairs(self, row: CardInventoryRow) -> tuple[tuple[str, str], ...]:
        definition = row.definition
        card = row.card
        if isinstance(definition, MachineDefinition):
            return (
                ("Effective Output", f"{definition.base_output_per_tick * card.output_multiplier:g}"),
                ("Power Demand", f"{definition.base_power_draw * card.power_multiplier:g} MW"),
            )
        if isinstance(definition, EnergyDefinition):
            pairs = [("Generation", f"{definition.base_power_output * card.output_multiplier:g} MW")]
            if definition.requires_fuel and definition.fuel_resource_id is not None:
                pairs.extend(
                    [
                        ("Fuel", definition.fuel_resource_id.replace("_", " ").title()),
                        ("Consumption", f"{definition.fuel_consumption_per_cycle:g}/cycle"),
                    ]
                )
            return tuple(pairs)
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return (
                ("Transport Capacity", f"{stats.capacity:g}"),
                ("Transport Time", f"{stats.transport_time_seconds:g}s"),
                ("Full-load capacity", f"{stats.capacity_per_cycle:.2f}/cycle"),
                ("Facility", definition.facility_name),
            )
        return (("Value", "-"),)

    def _card_detail_text(self, row: CardInventoryRow) -> str:
        return (
            f"{row.definition.name}\n"
            f"Status: {row.status}\n"
            f"Rarity: {row.rarity.value.title()}\n"
            f"Bonus: +{row.card.output_bonus_percent:.1f}%\n"
            f"Quantity: {row.quantity}\n"
            f"Effective: {self._performance_text(row)}"
        )

    def _matches_filters(self, row: CardInventoryRow) -> bool:
        search = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        if search and search not in f"{row.definition.name} {row.card_type} {row.rarity.value}".lower():
            return False
        if self._type_filter.currentText() not in ("", "All", self._row_type_filter_label(row)):
            return False
        if self._rarity_filter.currentText() not in ("", "All", row.rarity.value.title()):
            return False
        if self._status_filter.currentText() not in ("", "All", row.status):
            return False
        return True

    def _row_type_filter_label(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, MachineDefinition) and row.definition.machine_type in {
            MachineType.EXTRACTOR,
            MachineType.DRILLING,
            MachineType.AGRICULTURE,
        }:
            return "Primary Production"
        return row.card_type.title()

    def _recycle(self, row: CardInventoryRow, quantity: int) -> None:
        if self._command_bus is None or row.status != "Available":
            return
        stack = next(
            stack
            for stack in self._state.inventory_card_stacks()
            if stack.first_card.card_id == row.card.card_id
        )
        selected = tuple(card.card_id for card in stack.cards[:quantity])
        self._command_bus.dispatch(RecycleCards(selected))
        self._selected_card_row = None
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _build_crafting_panel(self) -> QWidget:
        panel = QStackedWidget()
        self._craft_pages = panel

        selection_panel = QFrame()
        selection_panel.setObjectName("craftSelectionPanel")
        selection_layout = QVBoxLayout(selection_panel)
        selection_layout.setContentsMargins(14, 14, 14, 14)
        selection_layout.setSpacing(12)
        self._craft_material_back = self._workspace_back_button(
            "BACK TO ASSEMBLY", lambda: self._set_craft_selection_mode("workspace")
        )
        selection_layout.addWidget(self._craft_material_back, 0, Qt.AlignmentFlag.AlignLeft)
        self._craft_target_filters = QWidget()
        self._craft_target_filters.setObjectName("craftFilterDeck")
        target_filters = QHBoxLayout(self._craft_target_filters)
        target_filters.setContentsMargins(14, 12, 14, 12)
        target_filters.setSpacing(14)
        self._craft_target_search = QLineEdit()
        self._craft_target_search.setObjectName("craftTargetSearch")
        self._craft_target_search.setPlaceholderText("Search target cards...")
        self._craft_target_search.textChanged.connect(self._refresh_crafting_panel)
        self._craft_target_type = self._craft_filter("craftTargetTypeFilter", self._refresh_crafting_panel, hidden=True)
        self._craft_target_rarity = self._craft_filter(
            "craftTargetRarityFilter", self._on_craft_target_rarity_changed, hidden=True
        )
        self._craft_target_sort = self._craft_filter("craftTargetSort", self._refresh_crafting_panel, hidden=True)
        self._craft_target_sort.addItems(["Name", "Type"])
        target_filters.addWidget(self._labeled_filter("SEARCH", self._craft_target_search), 2)
        self._craft_target_type_chip_layout = self._add_chip_group(target_filters, "TYPE")
        self._craft_target_rarity_chip_layout = self._add_chip_group(target_filters, "RARITY")
        self._craft_target_sort_chip_layout = self._add_chip_group(target_filters, "SORT")
        target_filters.addStretch(1)
        self._craft_target_filter_scroll = InventoryFilterScroll(self._craft_target_filters, "craftTargetFilterScroll", 980)
        selection_layout.addWidget(self._craft_target_filter_scroll)

        self._craft_material_filters = QWidget()
        self._craft_material_filters.setObjectName("craftFilterDeck")
        material_filters = QHBoxLayout(self._craft_material_filters)
        material_filters.setContentsMargins(14, 12, 14, 12)
        material_filters.setSpacing(14)
        self._craft_material_search = QLineEdit()
        self._craft_material_search.setObjectName("craftMaterialSearch")
        self._craft_material_search.setPlaceholderText("Search material cards...")
        self._craft_material_search.textChanged.connect(self._refresh_crafting_panel)
        self._craft_material_type = self._craft_filter("craftMaterialTypeFilter", self._refresh_crafting_panel, hidden=True)
        self._craft_rarity = QComboBox(self)
        self._craft_rarity.setObjectName("craftInputRaritySelect")
        for rarity in RARITY_CRAFT_UPGRADES:
            self._craft_rarity.addItem(rarity.value.title(), rarity)
        self._craft_rarity.hide()
        self._craft_rarity.currentIndexChanged.connect(self._on_craft_rarity_changed)
        self._craft_material_sort = self._craft_filter("craftMaterialSort", self._refresh_crafting_panel, hidden=True)
        self._craft_material_sort.addItems(["Name", "Quantity", "Bonus"])
        material_filters.addWidget(self._labeled_filter("SEARCH", self._craft_material_search), 2)
        self._craft_material_type_chip_layout = self._add_chip_group(material_filters, "TYPE")
        self._craft_input_rarity_chip_layout = self._add_chip_group(material_filters, "INPUT RARITY")
        self._craft_material_sort_chip_layout = self._add_chip_group(material_filters, "SORT")
        material_filters.addStretch(1)
        self._craft_material_filter_scroll = InventoryFilterScroll(self._craft_material_filters, "craftMaterialFilterScroll", 860)
        selection_layout.addWidget(self._craft_material_filter_scroll)

        self._craft_target_scroll = QScrollArea()
        self._craft_target_scroll.setObjectName("craftTargetScroll")
        self._craft_target_scroll.setWidgetResizable(True)
        self._craft_target_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._craft_target_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._craft_target_grid_host = QWidget()
        self._craft_target_grid_host.setObjectName("craftTargetGrid")
        self._craft_target_grid = QGridLayout(self._craft_target_grid_host)
        self._craft_target_grid.setContentsMargins(2, 2, 2, 2)
        self._craft_target_grid.setSpacing(INVENTORY_CARD_SPACING)
        self._craft_target_scroll.setWidget(self._craft_target_grid_host)
        selection_layout.addWidget(self._craft_target_scroll, 1)

        material_header = QHBoxLayout()
        material_header.setContentsMargins(0, 0, 0, 0)
        self._craft_material_count = QLabel(f"Materials 0/{CRAFT_INPUT_COUNT}")
        self._craft_material_count.setObjectName("craftMaterialCount")
        material_header.addStretch(1)
        material_header.addWidget(self._craft_material_count)
        selection_layout.addLayout(material_header)
        self._craft_material_scroll = QScrollArea()
        self._craft_material_scroll.setObjectName("craftMaterialScroll")
        self._craft_material_scroll.setWidgetResizable(True)
        self._craft_material_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._craft_material_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._craft_material_grid_host = QWidget()
        self._craft_material_grid_host.setObjectName("craftMaterialGrid")
        self._craft_material_grid = QGridLayout(self._craft_material_grid_host)
        self._craft_material_grid.setContentsMargins(2, 2, 2, 2)
        self._craft_material_grid.setSpacing(INVENTORY_CARD_SPACING)
        self._craft_material_scroll.setWidget(self._craft_material_grid_host)
        selection_layout.addWidget(self._craft_material_scroll, 1)

        self._craft_preview_panel = QFrame()
        self._craft_preview_panel.setObjectName("craftPreviewPanel")
        self._craft_preview_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        preview_layout = QVBoxLayout(self._craft_preview_panel)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(8)
        preview_layout.addWidget(self._workspace_back_button(
            "BACK TO TARGETS", lambda: self._set_craft_selection_mode("target")
        ), 0, Qt.AlignmentFlag.AlignLeft)
        target_header = QLabel("TARGET")
        target_header.setObjectName("craftSectionTitle")
        self._craft_target_preview = QFrame()
        self._craft_target_preview.setObjectName("craftTargetPreview")
        self._craft_target_preview.setFixedSize(220, 294)
        self._craft_target_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self._craft_target_preview.mousePressEvent = lambda event: self._set_craft_selection_mode("target")
        self._craft_target_preview_layout = QVBoxLayout(self._craft_target_preview)
        self._craft_target_preview_layout.setContentsMargins(10, 10, 10, 10)
        material_header_label = QLabel("MATERIALS")
        material_header_label.setObjectName("craftSectionTitle")
        self._craft_material_slots = QFrame()
        self._craft_material_slots.setObjectName("craftMaterialSlots")
        self._craft_material_slots_layout = QGridLayout(self._craft_material_slots)
        self._craft_material_slots_layout.setContentsMargins(8, 8, 8, 8)
        self._craft_material_slots_layout.setSpacing(7)
        for column in range(2):
            self._craft_material_slots_layout.setColumnStretch(column, 1)
        result_header = QLabel("CRAFT RESULT")
        result_header.setObjectName("craftSectionTitle")
        self._craft_preview = QLabel()
        self._craft_preview.setObjectName("craftOutputPreview")
        self._craft_preview.setWordWrap(True)
        self._craft_confirm = QCheckBox(f"Confirm consuming {CRAFT_INPUT_COUNT} cards")
        self._craft_confirm.setObjectName("craftConfirm")
        self._craft_confirm.stateChanged.connect(self._refresh_craft_button)
        self._craft_button = QPushButton("Craft Card")
        self._craft_button.setObjectName("craftCardButton")
        self._craft_button.clicked.connect(self._craft_selected_cards)
        assembly = QHBoxLayout()
        assembly.setSpacing(10)
        materials = QVBoxLayout()
        materials.addWidget(material_header_label)
        materials.addWidget(self._craft_material_slots)
        materials.addStretch(1)
        assembly.addLayout(materials, 1)
        assembly.addWidget(CraftConnectorSign(crafting=True), 0, Qt.AlignmentFlag.AlignVCenter)
        target = QVBoxLayout()
        target.addWidget(target_header)
        target.addWidget(self._craft_target_preview)
        target.addStretch(1)
        assembly.addLayout(target)
        action_panel = QFrame()
        action_panel.setObjectName("craftActionPanel")
        actions = QVBoxLayout(action_panel)
        actions.setContentsMargins(10, 10, 10, 10)
        actions.setSpacing(8)
        actions.addWidget(result_header)
        actions.addWidget(self._craft_preview)
        actions.addStretch(1)
        actions.addWidget(self._craft_confirm)
        actions.addWidget(self._craft_button)
        assembly.addWidget(action_panel, 1)
        preview_layout.addLayout(assembly)
        preview_layout.addStretch(1)
        self._craft_button.setMinimumHeight(48)
        panel.addWidget(selection_panel)
        panel.addWidget(self._workspace_scroll(self._craft_preview_panel))
        return panel

    def _workspace_back_button(self, text: str, callback) -> QPushButton:
        button = QPushButton("← " + text)
        button.setObjectName("inventoryWorkspaceBack")
        button.setMinimumHeight(40)
        button.clicked.connect(callback)
        return button

    def _workspace_scroll(self, content: QWidget) -> QScrollArea:
        content.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        scroll = QScrollArea()
        scroll.setObjectName("inventoryWorkspaceScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _craft_filter(self, object_name: str, callback, *, hidden: bool = False) -> QComboBox:
        combo = QComboBox(self)
        combo.setObjectName(object_name)
        if hidden:
            combo.hide()
        combo.currentTextChanged.connect(callback)
        return combo

    def _refresh_crafting_panel(self, *args) -> None:
        if not hasattr(self, "_craft_material_grid"):
            return
        self._hide_card_hover()
        available_ids = {
            card.card_id
            for group in self._craft_material_groups(include_filters=False)
            for card in group["cards"]
        }
        selected = tuple(card_id for card_id in self._selected_craft_material_ids if card_id in available_ids)
        if selected != self._selected_craft_material_ids:
            self._selected_craft_material_ids = selected
            self._craft_confirm.setChecked(False)
        self._refresh_craft_target_filter_options()
        self._refresh_craft_material_filter_options()
        self._refresh_craft_selection_mode()
        self._refresh_craft_target_grid()
        self._refresh_craft_material_grid()
        self._refresh_craft_preview()

    def _refresh_craft_target_filter_options(self) -> None:
        definitions = self._craft_target_definitions(include_filters=False)
        type_options = ["All", *sorted({self._definition_type_label(definition) for definition in definitions})]
        rarity_options = [rarity.value.title() for rarity in self._craft_output_rarities()]
        self._set_options(self._craft_target_type, type_options)
        self._set_options(self._craft_target_rarity, rarity_options)
        if hasattr(self, "_craft_target_type_chip_layout"):
            self._refresh_chip_group(self._craft_target_type_chip_layout, self._craft_target_type, self._craft_target_type.objectName())
            self._refresh_chip_group(self._craft_target_rarity_chip_layout, self._craft_target_rarity, self._craft_target_rarity.objectName())
            self._refresh_chip_group(self._craft_target_sort_chip_layout, self._craft_target_sort, self._craft_target_sort.objectName())

    def _refresh_craft_material_filter_options(self) -> None:
        groups = self._craft_material_groups(include_filters=False)
        type_options = ["All", *sorted({self._definition_type_label(group["definition"]) for group in groups})]
        self._set_options(self._craft_material_type, type_options)
        if hasattr(self, "_craft_material_type_chip_layout"):
            self._refresh_chip_group(self._craft_material_type_chip_layout, self._craft_material_type, self._craft_material_type.objectName())
            self._refresh_combo_data_chip_group(self._craft_input_rarity_chip_layout, self._craft_rarity, self._craft_rarity.objectName())
            self._refresh_chip_group(self._craft_material_sort_chip_layout, self._craft_material_sort, self._craft_material_sort.objectName())

    def _refresh_combo_data_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        self._clear_layout(layout)
        current_index = combo.currentIndex()
        for index in range(combo.count()):
            option = combo.itemText(index)
            chip = QPushButton(option.upper())
            chip.setObjectName("inventoryFilterChip")
            chip.setProperty("filterGroup", group)
            chip.setProperty("filterValue", option)
            chip.setProperty("active", index == current_index)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, target_index=index, target=combo: self._set_chip_filter_index(target, target_index))
            layout.addWidget(chip)

    def _set_chip_filter_index(self, combo: QComboBox, index: int) -> None:
        if combo.currentIndex() == index:
            return
        combo.setCurrentIndex(index)
        self._refresh_crafting_panel()

    def _refresh_craft_selection_mode(self) -> None:
        target_mode = self._craft_selection_mode == "target"
        self._craft_pages.setCurrentIndex(1 if self._craft_selection_mode == "workspace" else 0)
        self._craft_material_back.setVisible(not target_mode)
        self._craft_target_filter_scroll.setVisible(target_mode)
        self._craft_target_filters.setVisible(target_mode)
        self._craft_target_scroll.setVisible(target_mode)
        self._craft_material_filter_scroll.setVisible(not target_mode)
        self._craft_material_filters.setVisible(not target_mode)
        self._craft_material_count.setVisible(not target_mode)
        self._craft_material_scroll.setVisible(not target_mode)

    def _set_craft_selection_mode(self, mode: str) -> None:
        if mode not in {"target", "materials", "workspace"}:
            raise ValueError(f"Unknown crafting view: {mode}")
        self._hide_card_hover()
        self._craft_confirm.setChecked(False)
        self._craft_selection_mode = mode
        self._refresh_crafting_panel()

    def _craft_target_definitions(self, include_filters: bool = True) -> tuple[CardDefinition, ...]:
        definitions = [
            definition
            for definition in {item.definition_id: item for item in self._definitions.values()}.values()
            if isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition))
        ]
        if include_filters:
            search = self._craft_target_search.text().strip().lower()
            selected_type = self._craft_target_type.currentText()
            selected_rarity = self._craft_target_rarity.currentText()
            output_rarity = self._selected_craft_output_rarity()
            filtered: list[CardDefinition] = []
            for definition in definitions:
                label = self._definition_type_label(definition)
                if search and search not in f"{definition.name} {label}".lower():
                    continue
                if selected_type not in ("", "All", label):
                    continue
                if selected_rarity not in ("", "All") and (
                    output_rarity is None or selected_rarity != output_rarity.value.title()
                ):
                    continue
                filtered.append(definition)
            definitions = filtered
        sort = self._craft_target_sort.currentText() if hasattr(self, "_craft_target_sort") else "Name"
        if sort == "Type":
            definitions.sort(key=lambda definition: (self._definition_type_label(definition), definition.name))
        else:
            definitions.sort(key=lambda definition: definition.name)
        return tuple(definitions)

    def _refresh_craft_target_grid(self) -> None:
        self._clear_layout(self._craft_target_grid)
        if self._craft_selection_mode != "target":
            return
        definitions = self._craft_target_definitions()
        columns = self._configure_selection_grid(self._craft_target_grid, self._craft_target_scroll)
        if not definitions:
            empty = QLabel("No target cards match the current filters.")
            empty.setObjectName("craftEmptyState")
            self._craft_target_grid.addWidget(empty, 0, 0)
            return
        for index, definition in enumerate(definitions):
            card = self._build_craft_target_card(definition)
            self._craft_target_grid.addWidget(
                card,
                index // columns,
                index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        self._craft_target_grid.setColumnStretch(columns, 1)

    def _refresh_craft_material_grid(self) -> None:
        self._clear_layout(self._craft_material_grid)
        if self._craft_selection_mode == "target":
            return
        groups = self._craft_material_groups()
        columns = self._configure_selection_grid(self._craft_material_grid, self._craft_material_scroll)
        if not groups:
            empty = QLabel("No available material cards for this rarity.")
            empty.setObjectName("craftEmptyState")
            self._craft_material_grid.addWidget(empty, 0, 0)
            return
        for index, group in enumerate(groups):
            card = self._build_craft_material_card(group)
            self._craft_material_grid.addWidget(
                card,
                index // columns,
                index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        self._craft_material_grid.setColumnStretch(columns, 1)

    def _build_craft_target_card(self, definition: CardDefinition) -> QFrame:
        quantity = sum(
            stack.quantity
            for stack in self._state.inventory_card_stacks()
            if stack.first_card.definition_id == definition.definition_id
        )
        row = self._preview_row_for_definition(
            definition, quantity, "Target", rarity=self._selected_craft_output_rarity()
        )
        card = self._build_game_craft_grid_card(
            row,
            object_name="craftTargetCard",
            selected=definition.definition_id == self._craft_target_definition_id,
            footer_left="Target",
            footer_right=f"Owned ×{quantity}",
            click=lambda target_id=definition.definition_id: self._select_craft_target(target_id),
        )
        card.setProperty("definitionId", definition.definition_id)
        return card

    def _build_craft_material_card(self, group: dict) -> QFrame:
        selected_count = group["selected_count"]
        quantity = len(group["cards"])
        row = CardInventoryRow(group["cards"][0], group["definition"], quantity, "Available")
        enabled = selected_count > 0 or len(self._selected_craft_material_ids) < CRAFT_INPUT_COUNT
        card = self._build_game_craft_grid_card(
            row,
            object_name="craftMaterialCard",
            selected=selected_count > 0,
            footer_left=f"Selected {selected_count}/{quantity}",
            footer_right="Material",
            click=lambda cards=group["cards"]: self._toggle_craft_material_group(tuple(card.card_id for card in cards)),
            enabled=enabled,
        )
        card.setProperty("definitionId", row.definition.definition_id)
        card.setProperty("selectedCount", selected_count)
        card.setProperty("quantity", quantity)
        return card

    def _build_game_craft_grid_card(
        self,
        row: CardInventoryRow,
        object_name: str,
        selected: bool,
        footer_left: str,
        footer_right: str,
        click,
        enabled: bool = True,
        preview: bool = False,
        meta: str | None = None,
        detail: str | None = None,
    ) -> QFrame:
        card = InventoryCardFrame(
            row,
            title=self._card_game_title(row).upper(),
            family=self._card_game_family(row),
            meta=meta or self._card_game_meta(row).upper(),
            detail=detail or self._craft_card_detail(row, footer_right),
            selected=selected,
            disabled=not enabled,
            status_text="SELECTED" if selected else row.status,
            preview=preview,
        )
        card.setObjectName(object_name)
        card.setProperty("enabled", enabled)
        card.setProperty("rarity", row.rarity.value)
        card.setProperty("selected", selected)
        card.setProperty("cardType", self._card_type_key(row))
        card.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        if enabled:
            card.mousePressEvent = lambda event: click()
        if preview:
            card.setFixedSize(200, 270)
            card.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            card.hovered.connect(lambda inventory_row=row, widget=card: self._show_card_hover(inventory_row, widget))
            card.unhovered.connect(self._hide_card_hover)
        icon_key, accent_key, icon_resource_id = self._icon_signature(row)
        icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=1)
        icon.setObjectName("inventoryCardIcon")
        icon.setParent(card)
        icon.hide()
        _hidden_label(card, "inventoryCardName", row.definition.name)
        _hidden_label(card, "inventoryCardRarityMeta", row.rarity.value.title())
        _hidden_label(card, "inventoryCardRarity", row.rarity.value.title())
        _hidden_label(card, "inventoryCardFunction", self._card_function_label(row).upper())
        _hidden_label(card, "inventoryCardBonus", footer_left)
        _hidden_label(card, "inventoryCardQuantity", footer_right)
        _hidden_label(card, "inventoryCardStatus", "SELECTED" if selected else row.status)
        return card

    def _craft_card_detail(self, row: CardInventoryRow, fallback: str) -> str:
        if fallback.lower().startswith("owned"):
            return fallback.replace("×", "x").upper()
        if fallback.lower() == "material":
            return f"x{row.quantity} MATERIAL"
        return self._card_game_detail(row).upper()

    def _build_craft_grid_card(
        self,
        row: CardInventoryRow,
        object_name: str,
        selected: bool,
        footer_left: str,
        footer_right: str,
        click,
        enabled: bool = True,
    ) -> QFrame:
        card = HoverableCardFrame()
        card.setObjectName(object_name)
        card.setProperty("rarity", row.rarity.value)
        card.setProperty("selected", selected)
        card.setProperty("cardType", self._card_type_key(row))
        card.setProperty("enabled", enabled)
        card.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        card.setFixedSize(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if enabled:
            card.mousePressEvent = lambda event: click()
        card.hovered.connect(lambda inventory_row=row, widget=card: self._show_card_hover(inventory_row, widget))
        card.unhovered.connect(self._hide_card_hover)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(11, 10, 11, 10)
        layout.setSpacing(5)
        header = self._build_inventory_card_header(row)
        layout.addWidget(header)

        rarity_line = QFrame()
        rarity_line.setObjectName("inventoryRarityLine")
        rarity_line.setProperty("rarity", row.rarity.value)
        rarity_line.setFixedHeight(2)
        layout.addWidget(rarity_line)

        icon_key, accent_key, icon_resource_id = self._icon_signature(row)
        icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=58)
        icon.setObjectName("inventoryCardIcon")
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        icon_row = QHBoxLayout()
        icon_row.addStretch(1)
        icon_row.addWidget(icon)
        icon_row.addStretch(1)
        layout.addLayout(icon_row)
        layout.addSpacing(3)

        function = QLabel(self._card_function_label(row).upper())
        function.setObjectName("inventoryCardFunction")
        function.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(function)

        footer = QHBoxLayout()
        left = QLabel(footer_left)
        left.setObjectName("inventoryCardBonus")
        right = QLabel(footer_right)
        right.setObjectName("inventoryCardQuantity")
        footer.addWidget(left)
        footer.addStretch(1)
        footer.addWidget(right)
        layout.addLayout(footer)

        status_row = QHBoxLayout()
        status = QLabel("SELECTED" if selected else row.status)
        status.setObjectName("inventoryCardStatus")
        status_row.addStretch(1)
        status_row.addWidget(status)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        return card

    def _build_inventory_card_header(self, row: CardInventoryRow) -> QFrame:
        header = QFrame()
        header.setObjectName("inventoryCardHeader")
        header.setFixedHeight(INVENTORY_CARD_HEADER_HEIGHT)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        name = SmartCardTitleLabel(row.definition.name)
        name.setObjectName("inventoryCardName")
        name.setFixedHeight(INVENTORY_CARD_TITLE_HEIGHT)
        header_layout.addWidget(name)

        top_meta = QHBoxLayout()
        top_meta.setContentsMargins(0, 0, 0, 0)
        top_meta.setSpacing(6)
        rarity = QLabel(row.rarity.value.title())
        rarity.setObjectName("inventoryCardRarity")
        rarity.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rarity.setFixedHeight(16)
        top_meta.addStretch(1)
        top_meta.addWidget(rarity)
        header_layout.addLayout(top_meta)
        return header

    def _preview_row_for_definition(
        self,
        definition: CardDefinition,
        quantity: int,
        status: str,
        *,
        rarity: Rarity = Rarity.COMMON,
    ) -> CardInventoryRow:
        card = create_card_instance(
            f"craft-target-preview-{definition.definition_id}",
            definition.definition_id,
            definition.card_kind,
            rarity,
            bonus_tenths=RARITY_BONUS_RANGES_TENTHS[rarity][0],
        )
        return CardInventoryRow(card, definition, quantity, status)

    def _craft_material_groups(self, include_filters: bool = True) -> tuple[dict, ...]:
        selected_rarity = self._current_craft_input_rarity()
        installed = self._state.installed_card_ids() | self._state.installed_freight_card_ids()
        groups: dict[tuple[str, Rarity, int], list] = {}
        search = self._craft_material_search.text().strip().lower() if include_filters else ""
        selected_type = self._craft_material_type.currentText() if include_filters else "All"
        for card in self._state.cards.values():
            definition = self._definitions.get(card.definition_id)
            if card.card_id in installed:
                continue
            if card.rarity is not selected_rarity:
                continue
            if not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
                continue
            label = self._definition_type_label(definition)
            if search and search not in f"{definition.name} {label} {card.rarity.value}".lower():
                continue
            if selected_type not in ("", "All", label):
                continue
            key = (card.definition_id, card.rarity, card.output_bonus_tenths)
            groups.setdefault(key, []).append(card)
        result = []
        for (_definition_id, _rarity, _bonus), cards in sorted(groups.items(), key=lambda item: item[0]):
            cards.sort(key=lambda card: card.card_id)
            definition = self._definitions[cards[0].definition_id]
            selected_count = sum(1 for card in cards if card.card_id in self._selected_craft_material_ids)
            result.append({"definition": definition, "cards": tuple(cards), "selected_count": selected_count})
        sort = self._craft_material_sort.currentText() if hasattr(self, "_craft_material_sort") else "Name"
        if sort == "Quantity":
            result.sort(key=lambda group: (-len(group["cards"]), group["definition"].name))
        elif sort == "Bonus":
            result.sort(key=lambda group: (-group["cards"][0].output_bonus_tenths, group["definition"].name))
        else:
            result.sort(key=lambda group: group["definition"].name)
        return tuple(result)

    def _select_craft_target(self, definition_id: str) -> None:
        self._craft_target_definition_id = definition_id
        self._set_craft_selection_mode("workspace")

    def _toggle_craft_material_group(self, card_ids: tuple[str, ...]) -> None:
        selected = list(self._selected_craft_material_ids)
        if len(selected) < CRAFT_INPUT_COUNT:
            for card_id in card_ids:
                if card_id not in selected:
                    selected.append(card_id)
                    break
        self._selected_craft_material_ids = tuple(selected[:CRAFT_INPUT_COUNT])
        self._set_craft_selection_mode("workspace")

    def _remove_craft_material(self, card_id: str) -> None:
        self._selected_craft_material_ids = tuple(
            selected_id for selected_id in self._selected_craft_material_ids if selected_id != card_id
        )
        self._craft_confirm.setChecked(False)
        self._refresh_crafting_panel()

    def _grid_columns_for_scroll(self, scroll: QScrollArea) -> int:
        width = scroll.viewport().width() if scroll is not None else self.width()
        width = max(width, INVENTORY_CARD_WIDTH)
        pitch = INVENTORY_CARD_WIDTH + INVENTORY_CARD_SPACING
        return max(1, min(8, width // pitch))

    def _definition_type_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.name
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, FreightDefinition):
            return "Freight"
        return "Card"

    def _current_craft_input_rarity(self) -> Rarity:
        data = self._craft_rarity.currentData()
        try:
            return data if isinstance(data, Rarity) else Rarity(data)
        except (TypeError, ValueError):
            return Rarity.UNCOMMON

    def _current_craft_output_rarity(self) -> Rarity | None:
        return RARITY_CRAFT_UPGRADES.get(self._current_craft_input_rarity())

    def _craft_output_rarities(self) -> tuple[Rarity, ...]:
        return tuple(dict.fromkeys(RARITY_CRAFT_UPGRADES.values()))

    def _selected_craft_output_rarity(self) -> Rarity:
        selected = self._craft_target_rarity.currentText() if hasattr(self, "_craft_target_rarity") else "All"
        for rarity in self._craft_output_rarities():
            if selected == rarity.value.title():
                return rarity
        return self._current_craft_output_rarity() or self._craft_output_rarities()[0]

    def _on_craft_target_rarity_changed(self, *args) -> None:
        selected_output = next(
            (
                rarity
                for rarity in self._craft_output_rarities()
                if self._craft_target_rarity.currentText() == rarity.value.title()
            ),
            None,
        )
        if selected_output is not None:
            input_rarity = next(
                rarity for rarity, output in RARITY_CRAFT_UPGRADES.items() if output == selected_output
            )
            index = next(
                (
                    item_index
                    for item_index in range(self._craft_rarity.count())
                    if self._craft_rarity.itemData(item_index) in (input_rarity, input_rarity.value)
                ),
                -1,
            )
            if index >= 0 and index != self._craft_rarity.currentIndex():
                self._craft_rarity.blockSignals(True)
                self._craft_rarity.setCurrentIndex(index)
                self._craft_rarity.blockSignals(False)
                self._selected_craft_material_ids = ()
                self._craft_confirm.setChecked(False)
        self._refresh_crafting_panel()

    def _on_craft_rarity_changed(self, *args) -> None:
        output_rarity = self._current_craft_output_rarity()
        if output_rarity is not None and hasattr(self, "_craft_target_rarity"):
            self._craft_target_rarity.blockSignals(True)
            self._craft_target_rarity.setCurrentText(output_rarity.value.title())
            self._craft_target_rarity.blockSignals(False)
        self._selected_craft_material_ids = ()
        self._craft_confirm.setChecked(False)
        self._refresh_crafting_panel()

    def _selected_craft_card_ids(self) -> tuple[str, ...]:
        return self._selected_craft_material_ids

    def _refresh_craft_preview(self, *args) -> None:
        selected_ids = self._selected_craft_card_ids()
        selected_count = len(selected_ids)
        self._craft_material_count.setText(f"Materials {selected_count}/{CRAFT_INPUT_COUNT}")
        self._clear_layout(self._craft_target_preview_layout)
        self._clear_layout(self._craft_material_slots_layout)

        target_id = self._craft_target_definition_id
        target_definition = self._definitions.get(target_id or "")
        if isinstance(target_definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            quantity = sum(
                stack.quantity
                for stack in self._state.inventory_card_stacks()
                if stack.first_card.definition_id == target_definition.definition_id
            )
            output_rarity = self._selected_craft_output_rarity()
            row = self._preview_row_for_definition(target_definition, 1, "Target", rarity=output_rarity)
            if selected_count == CRAFT_INPUT_COUNT:
                try:
                    result = preview_crafted_card(tuple(self._state.cards[card_id] for card_id in selected_ids), target_definition)
                    row = CardInventoryRow(result, target_definition, 1, "Result")
                except ValueError:
                    pass
            target_card = self._build_game_craft_grid_card(
                row,
                object_name="craftResultCard",
                selected=False,
                footer_left="Target",
                footer_right=f"Owned ×{quantity}",
                click=lambda: self._set_craft_selection_mode("target"),
                preview=True,
                meta=output_rarity.value.upper(),
                detail=f"+{row.card.output_bonus_percent:.1f}% BONUS" if row.status == "Result" else "BONUS PENDING",
            )
            target_card.setProperty("definitionId", target_definition.definition_id)
            self._craft_target_preview_layout.addWidget(target_card, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            target_label = QLabel("Select a target card.")
            target_label.setObjectName("craftPreviewHint")
            target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            target_label.setWordWrap(True)
            self._craft_target_preview_layout.addWidget(target_label)

        for index in range(CRAFT_INPUT_COUNT):
            slot = QFrame()
            slot.setObjectName("craftMaterialSlot")
            slot.setProperty("filled", index < selected_count)
            slot.setCursor(Qt.CursorShape.PointingHandCursor)
            slot.setMinimumSize(104, 104)
            slot_layout = QVBoxLayout(slot)
            slot_layout.setContentsMargins(6, 6, 6, 6)
            slot_layout.setSpacing(4)
            if index < selected_count:
                card = self._state.cards[selected_ids[index]]
                definition = self._definitions.get(card.definition_id)
                if isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
                    row = CardInventoryRow(card, definition, 1, "Selected")
                    icon_key, accent_key, icon_resource_id = self._icon_signature(row)
                    icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=30)
                    icon.setObjectName("inventoryCardIcon")
                    icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    icon_row = QHBoxLayout()
                    icon_row.addStretch(1)
                    icon_row.addWidget(icon)
                    icon_row.addStretch(1)
                    slot_layout.addLayout(icon_row)
                    text = definition.name
                else:
                    text = card.definition_id
                slot.mousePressEvent = lambda event, card_id=card.card_id: self._remove_craft_material(card_id)
                label = QLabel(f"{index + 1}\n{text}\n+{card.output_bonus_percent:.1f}%\nREMOVE")
            else:
                slot.mousePressEvent = lambda event: self._set_craft_selection_mode("materials")
                label = QLabel(f"+\nMATERIAL {index + 1}\nSELECT CARD")
            label.setObjectName("craftMaterialSlotLabel")
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            slot_layout.addWidget(label)
            self._craft_material_slots_layout.addWidget(slot, index // 2, index % 2)

        if selected_count != CRAFT_INPUT_COUNT or not isinstance(target_definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            target_name = target_definition.name if target_definition is not None else "None"
            self._craft_preview.setText(f"Target: {target_name}\nResult: Select {CRAFT_INPUT_COUNT} matching cards.")
            self._refresh_craft_button()
            return
        try:
            cards = tuple(self._state.cards[card_id] for card_id in selected_ids)
            preview = preview_crafted_card(cards, target_definition)
            self._craft_preview.setText(
                f"Target: {target_definition.name}\n"
                f"Result Rarity: {preview.rarity.value.title()}\n"
                f"Result Bonus: +{preview.output_bonus_percent:.1f}%\n"
                f"The {CRAFT_INPUT_COUNT} selected cards will be destroyed."
            )
        except ValueError as error:
            self._craft_preview.setText(str(error))
        self._refresh_craft_button()

    def _refresh_craft_button(self, *args) -> None:
        valid_recipe = False
        try:
            target = self._definitions.get(self._craft_target_definition_id or "")
            if target is not None and len(self._selected_craft_card_ids()) == CRAFT_INPUT_COUNT:
                preview_crafted_card(tuple(self._state.cards[card_id] for card_id in self._selected_craft_card_ids()), target)
                valid_recipe = True
        except (ValueError, KeyError):
            pass
        enabled = (
            self._command_bus is not None
            and valid_recipe
            and self._craft_confirm.isChecked()
        )
        self._craft_button.setEnabled(enabled)

    def _craft_selected_cards(self) -> None:
        if self._command_bus is None:
            return
        self._command_bus.dispatch(
            CraftRarityCard(
                self._selected_craft_card_ids(),
                self._craft_target_definition_id or "",
                self._definitions,
            )
        )
        self._selected_craft_material_ids = ()
        self._craft_target_definition_id = None
        self._craft_selection_mode = "target"
        self._craft_confirm.setChecked(False)
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _performance_text(self, row: CardInventoryRow) -> str:
        definition = row.definition
        card = row.card
        if isinstance(definition, MachineDefinition):
            return (
                f"{definition.base_output_per_tick * card.output_multiplier:g} / "
                f"{definition.base_power_draw * card.power_multiplier:g} MW"
            )
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output * card.output_multiplier:g} MW"
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"{stats.capacity:g} capacity / {stats.transport_time_seconds:g}s"
        return "-"

    def _base_values_text(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.base_output_per_tick:g} / {definition.base_power_draw:g} MW"
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output:g} MW"
        if isinstance(definition, FreightDefinition):
            return f"{definition.base_capacity:g} capacity / {definition.base_transport_time_seconds:g}s"
        return "-"

    def _resources_text(self, resources: dict[str, float]) -> str:
        return ", ".join(
            f"{amount:g} {resource_id.replace('_', ' ').title()}"
            for resource_id, amount in resources.items()
        )

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
