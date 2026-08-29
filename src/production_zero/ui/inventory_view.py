from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.cards import create_card_instance, effective_recipe_inputs, effective_recipe_outputs
from production_zero.core.commands import CommandBus, CraftRarityCard, RecycleCards, UpgradeCardMk
from production_zero.core.crafting import CRAFT_INPUT_COUNT, RARITY_CRAFT_UPGRADES, preview_crafted_card
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.enums import Rarity
from production_zero.core.inventory import CardInventoryRow, build_card_inventory_rows
from production_zero.core.mk_upgrades import mk_upgrade_scrap_cost, next_mk_definition
from production_zero.core.recycling import scrap_value_for_card
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup, HoverableCardFrame
from production_zero.ui.game_ui import Accent, GAME_UI_TOKENS, InteractionState, MaterialLevel, draw_game_panel, draw_track_surface
from production_zero.ui.game_ui.rendering import draw_machine_card_prototype
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.text_format import SmartCardTitleLabel
from production_zero.ui.widget_lifecycle import clear_layout_safely


INVENTORY_CARD_WIDTH = 166
INVENTORY_CARD_HEIGHT = 224
INVENTORY_CARD_SPACING = 10
INVENTORY_CARD_HEADER_HEIGHT = 54
INVENTORY_CARD_TITLE_HEIGHT = 30
CARD_TITLE_SUFFIX_RE = re.compile(
    r"\s*(?:[-–—]\s*)?(?:(?:MK|MARK)\s*(?:I|II|III|IV|V|VI|VII|VIII|IX|X|[1-9]\d*)|CLASS\s*(?:I|II|III|IV|V|VI|VII|VIII|IX|X|[1-9]\d*))\s*$",
    re.IGNORECASE,
)
FREIGHT_ICON_KEYS = {
    "truck": ("vehicle", "vehicle"),
    "train": ("rail", "rail"),
    "ship": ("ship", "ship"),
    "aircraft": ("aircraft", "aircraft"),
}


def _hidden_label(parent: QWidget, object_name: str, text: str) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName(object_name)
    label.hide()
    return label


class InventoryCardsHeader(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("inventoryCardsHeader")
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=16)
        inset = rect.adjusted(14, 13, -14, -13)
        draw_track_surface(painter, inset, accent=Accent.PROCESSOR, radius=11)
        painter.end()
        super().paintEvent(event)


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
            hover=self.underMouse() or self._selected,
        )
        self._draw_quantity_badge(painter, rect)
        if self._selected:
            painter.setPen(QPen(QColor(98, 190, 232, 190), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 10, 10)
        painter.end()

    def _draw_quantity_badge(self, painter: QPainter, rect: QRectF) -> None:
        text = f"x{self._quantity}"
        font = GAME_UI_TOKENS.typography.status_label()
        font.setPointSize(8)
        painter.setFont(font)
        width = max(34.0, painter.fontMetrics().horizontalAdvance(text) + 18.0)
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


class MkUpgradeConnectorSign(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mkUpgradeConnector")
        self.setFixedSize(96, INVENTORY_CARD_HEIGHT + 34)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(5, 46, -5, -46)
        body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        body.setColorAt(0.0, QColor(145, 32, 24, 244))
        body.setColorAt(0.45, QColor(91, 16, 13, 248))
        body.setColorAt(1.0, QColor(38, 8, 7, 250))
        painter.setPen(QPen(QColor(236, 67, 43, 170), 1.5))
        painter.setBrush(body)
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QPen(QColor(255, 240, 216, 74), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(5, 5, -5, -5), 5, 5)

        font = GAME_UI_TOKENS.typography.micro_label()
        font.setPointSize(8)
        font.setWeight(font.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor("#f4e7d8"))
        painter.drawText(rect.adjusted(4, 12, -4, -rect.height() * 0.56), Qt.AlignmentFlag.AlignCenter, "UPGRADE")

        arrow_rect = rect.adjusted(18, rect.height() * 0.42, -18, -18)
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
        painter.end()


class InventoryFilterScroll(QScrollArea):
    def __init__(self, content: QWidget, object_name: str, preferred_width: int) -> None:
        super().__init__()
        self._content = content
        self._preferred_width = preferred_width
        self.setObjectName(object_name)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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


class InventoryView(QWidget):
    def __init__(
        self,
        state: GameState,
        definitions: dict[str, CardDefinition],
        resource_definitions: dict[str, ResourceDefinition] | None = None,
        command_bus: CommandBus | None = None,
        on_state_changed=None,
    ) -> None:
        super().__init__()
        self._state = state
        self._definitions = definitions
        self._resource_definitions = resource_definitions or {}
        self._command_bus = command_bus
        self._on_state_changed = on_state_changed
        self._rows: tuple[CardInventoryRow, ...] = ()
        self._visible_card_rows: tuple[CardInventoryRow, ...] = ()
        self._selected_card_row: CardInventoryRow | None = None
        self._craft_target_definition_id: str | None = None
        self._selected_craft_material_ids: tuple[str, ...] = ()
        self._craft_selection_mode = "target"
        self._hover_row: CardInventoryRow | None = None
        self._hover_popup: CardHoverInfoPopup | None = None
        self._mk_selected_card_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = InventoryCardsHeader()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 26, 32, 24)
        header_layout.setSpacing(18)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(2)
        title = QLabel("INVENTORY")
        title.setObjectName("inventoryHeroTitle")
        subtitle = QLabel("CARD COLLECTION / MANAGEMENT")
        subtitle.setObjectName("inventoryHeroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header_layout.addLayout(title_column, 1)
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
        header_layout.addWidget(scrap_tile)
        self._storage_info.hide()
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("inventorySubTabs")
        self._tabs.addTab(self._build_cards_tab(), "Cards")
        self._tabs.addTab(self._build_crafting_panel(), "Crafting")
        self._tabs.addTab(self._build_mk_upgrade_panel(), "MK Upgrade")
        root.addWidget(self._tabs, 1)

        self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
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
        self._rows = build_card_inventory_rows(self._state, self._definitions)
        self._total_cards_label.setText(str(len(self._state.cards)))
        self._stacks_label.setText(str(len(self._state.inventory_card_stacks())))
        self._scrap_label.setText(str(self._state.scrap.amount))
        self._refresh_storage_status()
        self._refresh_filter_options()
        self._refresh_cards_table()
        self._refresh_action_panel()
        self._refresh_crafting_panel()
        self._refresh_mk_upgrade_panel()

    def _refresh_storage_status(self) -> None:
        amount = sum(stock.amount for stock in self._state.resources.values())
        capacity = sum(stock.capacity for stock in self._state.resources.values())
        self._storage_label.setText(f"{amount:.0f} / {capacity:.0f}")
        self._storage_info.setText("Resource storage upgrades are in the topbar.")

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
        self._mk_filter = self._build_filter("inventoryMkFilter")
        self._rarity_filter = self._build_filter("inventoryRarityFilter")
        self._status_filter = self._build_filter("inventoryStatusFilter")
        self._sort = self._build_filter("inventorySort")
        self._sort.addItems(["Name", "Rarity", "Quantity", "Status", "MK"])

        toolbar_layout.addWidget(self._labeled_filter("SEARCH", self._search))
        self._type_chip_layout = self._add_chip_group(toolbar_layout, "TYPE")
        self._mk_chip_layout = self._add_chip_group(toolbar_layout, "MK")
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
        self._action_layout = QHBoxLayout(self._action_panel)
        self._action_layout.setContentsMargins(12, 10, 12, 10)
        self._action_layout.setSpacing(10)
        self._action_panel.hide()
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

    def _labeled_filter(self, label_text: str, control: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        layout.addWidget(control)
        return wrapper

    def _refresh_filter_options(self) -> None:
        self._set_options(self._type_filter, ["All", *sorted({row.card_type.title() for row in self._rows})])
        self._set_options(self._mk_filter, ["All", *[str(level) for level in sorted({row.mk_level for row in self._rows})]])
        self._set_options(self._rarity_filter, ["All", *[rarity.value.title() for rarity in Rarity]])
        self._set_options(self._status_filter, ["All", "Available", "In Use"])
        if hasattr(self, "_type_chip_layout"):
            self._refresh_chip_group(self._type_chip_layout, self._type_filter, self._type_filter.objectName())
            self._refresh_chip_group(self._mk_chip_layout, self._mk_filter, self._mk_filter.objectName())
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
        if group.lower().endswith("mkfilter") and option.isdigit():
            return f"MK{option}"
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
        for column in range(columns):
            self._cards_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
        for row_index, row in enumerate(rows):
            card = self._build_inventory_card(row, row.card.card_id == current_card_id)
            self._cards_grid.addWidget(
                card,
                row_index // columns,
                row_index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            if row.card.card_id == current_card_id:
                selected_row = row
        self._cards_grid.setColumnStretch(columns, 1)
        if current_card_id is not None and selected_row is None:
            self._selected_card_row = None
        elif selected_row is not None:
            self._selected_card_row = selected_row
        self._refresh_action_panel()

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
        _hidden_label(card, "inventoryCardMk", "-" if row.mk_level == 0 else f"MK {row.mk_level}")
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
        if isinstance(definition, RecipeDefinition):
            return definition.stage.value
        if isinstance(definition, FreightDefinition):
            return "freight"
        return "card"

    def _card_game_family(self, row: CardInventoryRow) -> str:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return "energy"
        if isinstance(definition, RecipeDefinition):
            return definition.stage.value
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return "processor"

    def _card_game_title(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, FreightDefinition):
            return row.definition.family.value
        return CARD_TITLE_SUFFIX_RE.sub("", row.definition.name).strip() or row.definition.name

    def _card_game_meta(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, FreightDefinition):
            return f"{row.definition.class_label} / {row.rarity.value}"
        if row.mk_level == 0:
            return row.rarity.value
        return f"MK{row.mk_level} / {row.rarity.value}"

    def _card_game_detail(self, row: CardInventoryRow) -> str:
        if isinstance(row.definition, MachineDefinition):
            production = row.definition.production_option(
                row.definition.default_production_id_for_card_definition(row.card.definition_id)
            )
            amount = production.output_amount_for(row.definition) * (1 + row.card.output_bonus_percent / 100)
            return f"+{amount:.0f}/cycle"
        if isinstance(row.definition, EnergyDefinition):
            return f"+{row.definition.base_power_output:.0f} MW"
        if isinstance(row.definition, RecipeDefinition):
            output = next(iter(row.definition.output_resources), row.definition.definition_id)
            return output.replace("_", " ")
        if isinstance(row.definition, FreightDefinition):
            stats = freight_stats(row.card, row.definition)
            return f"{stats.capacity:.0f} cap"
        return self._card_function_label(row)

    def _card_function_label(self, row: CardInventoryRow) -> str:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value.title()
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, RecipeDefinition):
            return f"{definition.stage.value.title()} Recipe"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.title()
        return row.card_type.title()

    def _icon_signature(self, row: CardInventoryRow) -> tuple[str, str, str]:
        definition = row.definition
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id_for_card_definition(row.card.definition_id))
            resource_id = production.output_resource or definition.output_resource
            return (
                production.icon_key or definition.icon_key or resource_icon_key(resource_id),
                production.accent_key or definition.accent_key or resource_accent_key(resource_id),
                resource_id,
            )
        if isinstance(definition, EnergyDefinition):
            return ("energy", "energy", definition.definition_id)
        if isinstance(definition, RecipeDefinition):
            output_resource = next(iter(definition.output_resources), definition.definition_id)
            return (
                definition.icon_key or resource_icon_key(output_resource),
                definition.accent_key or resource_accent_key(output_resource),
                output_resource,
            )
        if isinstance(definition, FreightDefinition):
            icon_key, accent_key = FREIGHT_ICON_KEYS.get(definition.family.value, ("vehicle", "vehicle"))
            return (icon_key, accent_key, definition.definition_id)
        return ("default", "default", row.card.definition_id)

    def _sort_rows(self, rows: list[CardInventoryRow]) -> list[CardInventoryRow]:
        sort = self._sort.currentText() if hasattr(self, "_sort") else "Name"
        if sort == "Rarity":
            order = {rarity: index for index, rarity in enumerate(Rarity)}
            return sorted(rows, key=lambda row: (order[row.rarity], row.definition.name, row.card.output_bonus_tenths))
        if sort == "Quantity":
            return sorted(rows, key=lambda row: (-row.quantity, row.definition.name))
        if sort == "Status":
            return sorted(rows, key=lambda row: (row.status, row.definition.name))
        if sort == "MK":
            return sorted(rows, key=lambda row: (row.mk_level, row.definition.name))
        return sorted(rows, key=lambda row: row.definition.name)

    def _select_card_row(self, row: CardInventoryRow) -> None:
        self._selected_card_row = row
        self._refresh_cards_table()

    def _refresh_action_panel(self) -> None:
        if not hasattr(self, "_action_layout"):
            return
        self._clear_layout(self._action_layout)
        row = self._selected_card_row
        if row is None:
            self._action_panel.hide()
            return
        self._action_panel.show()
        title = QLabel(row.definition.name)
        title.setObjectName("inventoryActionTitle")
        self._action_layout.addWidget(title)
        self._action_layout.addWidget(QLabel(f"{row.status} · Qty {row.quantity}"))
        if row.status == "Available":
            scrap = QLabel(f"Scrap Value: {scrap_value_for_card(row.card)}")
            scrap.setObjectName("cardDetailsActionText")
            self._action_layout.addWidget(scrap)
            quantity = QSpinBox()
            quantity.setObjectName("recycleQuantity")
            quantity.setRange(1, max(1, row.quantity))
            self._action_layout.addWidget(quantity)
            needs_confirmation = row.rarity in {Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY}
            confirm = QCheckBox("Confirm recycle")
            confirm.setObjectName("recycleRareConfirm")
            confirm.setVisible(needs_confirmation)
            self._action_layout.addWidget(confirm)
            button = QPushButton("Recycle")
            button.setObjectName("recycleCardButton")
            button.setEnabled(self._command_bus is not None and not needs_confirmation)
            if needs_confirmation:
                confirm.stateChanged.connect(
                    lambda state, recycle_button=button: recycle_button.setEnabled(
                        state == Qt.CheckState.Checked.value
                    )
                )
            button.clicked.connect(lambda checked=False, inventory_row=row, spin=quantity: self._recycle(inventory_row, spin.value()))
            self._action_layout.addWidget(button)
        self._action_layout.addStretch(1)

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
            ("MK / Class", "-" if row.mk_level == 0 else str(row.mk_level)),
            ("Bonus", f"+{row.card.output_bonus_percent:.1f}%"),
            ("Quantity", str(row.quantity)),
            ("Status", row.status),
        ]
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
                        ("Consumption", f"{definition.fuel_consumption_per_minute:g}/min"),
                    ]
                )
            return tuple(pairs)
        if isinstance(definition, RecipeDefinition):
            outputs = effective_recipe_outputs(card, dict(definition.output_resources))
            inputs = effective_recipe_inputs(card, dict(definition.input_resources))
            return (
                ("Recipe Inputs", self._resources_text(inputs)),
                ("Recipe Outputs", self._resources_text(outputs)),
            )
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return (
                ("Transport Capacity", f"{stats.capacity:g}"),
                ("Transport Time", f"{stats.transport_time_seconds:g}s"),
                ("Facility", definition.facility_name),
            )
        return (("Value", "-"),)

    def _card_detail_text(self, row: CardInventoryRow) -> str:
        return (
            f"{row.definition.name}\n"
            f"Status: {row.status}\n"
            f"MK: {'-' if row.mk_level == 0 else row.mk_level}\n"
            f"Rarity: {row.rarity.value.title()}\n"
            f"Bonus: +{row.card.output_bonus_percent:.1f}%\n"
            f"Quantity: {row.quantity}\n"
            f"Effective: {self._performance_text(row)}"
        )

    def _matches_filters(self, row: CardInventoryRow) -> bool:
        search = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        if search and search not in f"{row.definition.name} {row.card_type} {row.rarity.value}".lower():
            return False
        if self._type_filter.currentText() not in ("", "All", row.card_type.title()):
            return False
        if self._mk_filter.currentText() not in ("", "All", str(row.mk_level)):
            return False
        if self._rarity_filter.currentText() not in ("", "All", row.rarity.value.title()):
            return False
        if self._status_filter.currentText() not in ("", "All", row.status):
            return False
        return True

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
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        selection_panel = QFrame()
        selection_panel.setObjectName("craftSelectionPanel")
        selection_layout = QVBoxLayout(selection_panel)
        selection_layout.setContentsMargins(14, 14, 14, 14)
        selection_layout.setSpacing(12)
        self._craft_selection_title = QLabel("SELECT TARGET CARD")
        self._craft_selection_title.setObjectName("craftSectionTitle")
        selection_layout.addWidget(self._craft_selection_title)

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
        self._craft_target_mk = self._craft_filter("craftTargetMkFilter", self._refresh_crafting_panel, hidden=True)
        self._craft_target_rarity = self._craft_filter("craftTargetRarityFilter", self._refresh_crafting_panel, hidden=True)
        self._craft_target_sort = self._craft_filter("craftTargetSort", self._refresh_crafting_panel, hidden=True)
        self._craft_target_sort.addItems(["Name", "Type", "MK"])
        target_filters.addWidget(self._labeled_filter("SEARCH", self._craft_target_search), 2)
        self._craft_target_type_chip_layout = self._add_chip_group(target_filters, "TYPE")
        self._craft_target_mk_chip_layout = self._add_chip_group(target_filters, "MK")
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
        self._craft_material_count = QLabel("Materials 0/5")
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
        self._craft_preview_panel.setMaximumWidth(430)
        self._craft_preview_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        preview_layout = QVBoxLayout(self._craft_preview_panel)
        preview_layout.setContentsMargins(14, 14, 14, 14)
        preview_layout.setSpacing(12)
        target_header = QLabel("TARGET")
        target_header.setObjectName("craftSectionTitle")
        self._craft_target_preview = QFrame()
        self._craft_target_preview.setObjectName("craftTargetPreview")
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
        result_header = QLabel("CRAFT RESULT")
        result_header.setObjectName("craftSectionTitle")
        self._craft_preview = QLabel()
        self._craft_preview.setObjectName("craftOutputPreview")
        self._craft_preview.setWordWrap(True)
        self._craft_confirm = QCheckBox("Confirm consuming 5 cards")
        self._craft_confirm.setObjectName("craftConfirm")
        self._craft_confirm.stateChanged.connect(self._refresh_craft_button)
        self._craft_button = QPushButton("Craft Card")
        self._craft_button.setObjectName("craftCardButton")
        self._craft_button.clicked.connect(self._craft_selected_cards)
        preview_layout.addWidget(target_header)
        preview_layout.addWidget(self._craft_target_preview)
        preview_layout.addWidget(material_header_label)
        preview_layout.addWidget(self._craft_material_slots)
        preview_layout.addWidget(result_header)
        preview_layout.addWidget(self._craft_preview)
        preview_layout.addStretch(1)
        preview_layout.addWidget(self._craft_confirm)
        preview_layout.addWidget(self._craft_button)
        layout.addWidget(selection_panel, 3)
        layout.addWidget(self._craft_preview_panel, 1)
        return panel

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
        self._refresh_craft_target_filter_options()
        self._refresh_craft_material_filter_options()
        self._refresh_craft_selection_mode()
        self._refresh_craft_target_grid()
        self._refresh_craft_material_grid()
        self._refresh_craft_preview()

    def _refresh_craft_target_filter_options(self) -> None:
        definitions = self._craft_target_definitions(include_filters=False)
        type_options = ["All", *sorted({self._definition_type_label(definition) for definition in definitions})]
        mk_options = ["All", *[str(level) for level in sorted({self._definition_mk_level(definition) for definition in definitions})]]
        output_rarity = self._current_craft_output_rarity()
        rarity_options = ["All"]
        if output_rarity is not None:
            rarity_options.append(output_rarity.value.title())
        self._set_options(self._craft_target_type, type_options)
        self._set_options(self._craft_target_mk, mk_options)
        self._set_options(self._craft_target_rarity, rarity_options)
        if hasattr(self, "_craft_target_type_chip_layout"):
            self._refresh_chip_group(self._craft_target_type_chip_layout, self._craft_target_type, self._craft_target_type.objectName())
            self._refresh_chip_group(self._craft_target_mk_chip_layout, self._craft_target_mk, self._craft_target_mk.objectName())
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
        self._craft_selection_title.setText("SELECT TARGET CARD" if target_mode else "SELECT MATERIALS")
        self._craft_target_filter_scroll.setVisible(target_mode)
        self._craft_target_filters.setVisible(target_mode)
        self._craft_target_scroll.setVisible(target_mode)
        self._craft_material_filter_scroll.setVisible(not target_mode)
        self._craft_material_filters.setVisible(not target_mode)
        self._craft_material_count.setVisible(not target_mode)
        self._craft_material_scroll.setVisible(not target_mode)

    def _set_craft_selection_mode(self, mode: str) -> None:
        self._craft_selection_mode = "target" if mode == "target" else "materials"
        self._refresh_crafting_panel()

    def _craft_target_definitions(self, include_filters: bool = True) -> tuple[CardDefinition, ...]:
        definitions = [
            definition
            for definition in self._definitions.values()
            if isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition))
        ]
        if include_filters:
            search = self._craft_target_search.text().strip().lower()
            selected_type = self._craft_target_type.currentText()
            selected_mk = self._craft_target_mk.currentText()
            selected_rarity = self._craft_target_rarity.currentText()
            output_rarity = self._current_craft_output_rarity()
            filtered: list[CardDefinition] = []
            for definition in definitions:
                label = self._definition_type_label(definition)
                if search and search not in f"{definition.name} {label}".lower():
                    continue
                if selected_type not in ("", "All", label):
                    continue
                if selected_mk not in ("", "All", str(self._definition_mk_level(definition))):
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
        elif sort == "MK":
            definitions.sort(key=lambda definition: (self._definition_mk_level(definition), definition.name))
        else:
            definitions.sort(key=lambda definition: definition.name)
        return tuple(definitions)

    def _refresh_craft_target_grid(self) -> None:
        self._clear_layout(self._craft_target_grid)
        if self._craft_selection_mode != "target":
            return
        definitions = self._craft_target_definitions()
        columns = self._grid_columns_for_scroll(self._craft_target_scroll)
        for column in range(columns):
            self._craft_target_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
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
        columns = self._grid_columns_for_scroll(self._craft_material_scroll)
        for column in range(columns):
            self._craft_material_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
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
        row = self._preview_row_for_definition(definition, quantity, "Target")
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
    ) -> QFrame:
        card = InventoryCardFrame(
            row,
            title=self._card_game_title(row).upper(),
            family=self._card_game_family(row),
            meta=self._card_game_meta(row).upper(),
            detail=self._craft_card_detail(row, footer_right),
            selected=selected,
            disabled=not enabled,
            status_text="SELECTED" if selected else row.status,
        )
        card.setObjectName(object_name)
        card.setProperty("enabled", enabled)
        card.setProperty("rarity", row.rarity.value)
        card.setProperty("selected", selected)
        card.setProperty("cardType", self._card_type_key(row))
        card.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        if enabled:
            card.mousePressEvent = lambda event: click()
        card.hovered.connect(lambda inventory_row=row, widget=card: self._show_card_hover(inventory_row, widget))
        card.unhovered.connect(self._hide_card_hover)
        icon_key, accent_key, icon_resource_id = self._icon_signature(row)
        icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=1)
        icon.setObjectName("inventoryCardIcon")
        icon.setParent(card)
        icon.hide()
        _hidden_label(card, "inventoryCardName", row.definition.name)
        _hidden_label(card, "inventoryCardMk", "-" if row.mk_level == 0 else f"MK {row.mk_level}")
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
        mk = QLabel("-" if row.mk_level == 0 else f"MK {row.mk_level}")
        mk.setObjectName("inventoryCardMk")
        mk.setFixedHeight(16)
        rarity = QLabel(row.rarity.value.title())
        rarity.setObjectName("inventoryCardRarity")
        rarity.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        rarity.setFixedHeight(16)
        top_meta.addWidget(mk)
        top_meta.addStretch(1)
        top_meta.addWidget(rarity)
        header_layout.addLayout(top_meta)
        return header

    def _preview_row_for_definition(self, definition: CardDefinition, quantity: int, status: str) -> CardInventoryRow:
        card = create_card_instance(
            f"craft-target-preview-{definition.definition_id}",
            definition.definition_id,
            definition.card_kind,
            Rarity.COMMON,
            bonus_tenths=0,
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
        self._craft_selection_mode = "materials"
        self._refresh_crafting_panel()

    def _toggle_craft_material_group(self, card_ids: tuple[str, ...]) -> None:
        selected = list(self._selected_craft_material_ids)
        if len(selected) < CRAFT_INPUT_COUNT:
            for card_id in card_ids:
                if card_id not in selected:
                    selected.append(card_id)
                    break
        self._selected_craft_material_ids = tuple(selected[:CRAFT_INPUT_COUNT])
        self._refresh_crafting_panel()

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
            return definition.machine_type.value.title()
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, FreightDefinition):
            return "Freight"
        if isinstance(definition, RecipeDefinition):
            return "Recipe"
        return "Card"

    def _definition_mk_level(self, definition: CardDefinition) -> int:
        if isinstance(definition, FreightDefinition):
            return definition.class_level
        if isinstance(definition, RecipeDefinition):
            return 0
        return definition.mk_level

    def _current_craft_input_rarity(self) -> Rarity:
        data = self._craft_rarity.currentData()
        return data if isinstance(data, Rarity) else Rarity.UNCOMMON

    def _current_craft_output_rarity(self) -> Rarity | None:
        return RARITY_CRAFT_UPGRADES.get(self._current_craft_input_rarity())

    def _on_craft_rarity_changed(self, *args) -> None:
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
            row = self._preview_row_for_definition(target_definition, quantity, "Target")
            target_card = self._build_game_craft_grid_card(
                row,
                object_name="craftTargetCard",
                selected=True,
                footer_left="Target",
                footer_right=f"Owned ×{quantity}",
                click=lambda: self._set_craft_selection_mode("target"),
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
            slot.setCursor(Qt.CursorShape.PointingHandCursor if index < selected_count else Qt.CursorShape.ArrowCursor)
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
                label = QLabel(f"{index + 1}\n{text}\n+{card.output_bonus_percent:.1f}%")
            else:
                label = QLabel(f"Material {index + 1}")
            label.setObjectName("craftMaterialSlotLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            slot_layout.addWidget(label)
            self._craft_material_slots_layout.addWidget(slot, 0, index)

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
                "The 5 selected cards will be destroyed."
            )
        except ValueError as error:
            self._craft_preview.setText(str(error))
        self._refresh_craft_button()

    def _refresh_craft_button(self, *args) -> None:
        enabled = (
            self._command_bus is not None
            and len(self._selected_craft_card_ids()) == CRAFT_INPUT_COUNT
            and self._craft_target_definition_id in self._definitions
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
        self._craft_confirm.setChecked(False)
        if self._on_state_changed is not None:
            self._on_state_changed()
        self.refresh()

    def _build_mk_upgrade_panel(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        select_panel = QFrame()
        select_panel.setObjectName("mkUpgradePanel")
        select_layout = QVBoxLayout(select_panel)
        select_layout.setContentsMargins(14, 14, 14, 14)
        select_layout.setSpacing(12)
        title = QLabel("SELECT CARD")
        title.setObjectName("craftSectionTitle")
        select_layout.addWidget(title)
        filter_deck = QWidget()
        filter_deck.setObjectName("mkUpgradeFilterDeck")
        filters = QHBoxLayout(filter_deck)
        filters.setContentsMargins(14, 12, 14, 12)
        filters.setSpacing(14)
        self._mk_upgrade_search = QLineEdit()
        self._mk_upgrade_search.setObjectName("mkUpgradeSearch")
        self._mk_upgrade_search.setPlaceholderText("Search upgrade cards...")
        self._mk_upgrade_search.textChanged.connect(self._refresh_mk_upgrade_panel)
        self._mk_upgrade_type = self._craft_filter("mkUpgradeTypeFilter", self._refresh_mk_upgrade_panel, hidden=True)
        self._mk_upgrade_mk = self._craft_filter("mkUpgradeMkFilter", self._refresh_mk_upgrade_panel, hidden=True)
        self._mk_upgrade_rarity = self._craft_filter("mkUpgradeRarityFilter", self._refresh_mk_upgrade_panel, hidden=True)
        self._mk_upgrade_sort = self._craft_filter("mkUpgradeSort", self._refresh_mk_upgrade_panel, hidden=True)
        self._mk_upgrade_sort.addItems(["Name", "Type", "MK", "Rarity"])
        filters.addWidget(self._labeled_filter("SEARCH", self._mk_upgrade_search), 2)
        self._mk_upgrade_type_chip_layout = self._add_chip_group(filters, "TYPE")
        self._mk_upgrade_mk_chip_layout = self._add_chip_group(filters, "MK")
        self._mk_upgrade_rarity_chip_layout = self._add_chip_group(filters, "RARITY")
        self._mk_upgrade_sort_chip_layout = self._add_chip_group(filters, "SORT")
        filters.addStretch(1)
        self._mk_upgrade_filter_scroll = InventoryFilterScroll(filter_deck, "mkUpgradeFilterScroll", 980)
        select_layout.addWidget(self._mk_upgrade_filter_scroll)
        self._mk_upgrade_scroll = QScrollArea()
        self._mk_upgrade_scroll.setObjectName("mkUpgradeCardScroll")
        self._mk_upgrade_scroll.setWidgetResizable(True)
        self._mk_upgrade_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._mk_upgrade_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._mk_upgrade_grid_host = QWidget()
        self._mk_upgrade_grid_host.setObjectName("mkUpgradeCardGrid")
        self._mk_upgrade_grid = QGridLayout(self._mk_upgrade_grid_host)
        self._mk_upgrade_grid.setContentsMargins(2, 2, 2, 2)
        self._mk_upgrade_grid.setSpacing(INVENTORY_CARD_SPACING)
        self._mk_upgrade_scroll.setWidget(self._mk_upgrade_grid_host)
        select_layout.addWidget(self._mk_upgrade_scroll, 1)

        result_panel = QFrame()
        result_panel.setObjectName("mkUpgradeResultPanel")
        result_layout = QVBoxLayout(result_panel)
        result_layout.setContentsMargins(14, 14, 14, 14)
        result_layout.setSpacing(12)
        result_title = QLabel("UPGRADE RESULT")
        result_title.setObjectName("craftSectionTitle")
        result_layout.addWidget(result_title)
        card_compare = QHBoxLayout()
        card_compare.setSpacing(12)
        current_box = QVBoxLayout()
        current_box.setSpacing(6)
        current_title = QLabel("CURRENT")
        current_title.setObjectName("mkUpgradeSectionLabel")
        self._mk_current_card = QFrame()
        self._mk_current_card.setObjectName("mkUpgradeCurrentCard")
        self._mk_current_card.setFixedSize(INVENTORY_CARD_WIDTH + 34, INVENTORY_CARD_HEIGHT + 34)
        self._mk_current_card_layout = QVBoxLayout(self._mk_current_card)
        self._mk_current_card_layout.setContentsMargins(17, 17, 17, 17)
        current_box.addWidget(current_title)
        current_box.addWidget(self._mk_current_card, 0, Qt.AlignmentFlag.AlignCenter)
        connector = MkUpgradeConnectorSign()
        upgrade_box = QVBoxLayout()
        upgrade_box.setSpacing(6)
        upgrade_title = QLabel("UPGRADE")
        upgrade_title.setObjectName("mkUpgradeSectionLabel")
        self._mk_upgrade_card_preview = QFrame()
        self._mk_upgrade_card_preview.setObjectName("mkUpgradeTargetCard")
        self._mk_upgrade_card_preview.setFixedSize(INVENTORY_CARD_WIDTH + 34, INVENTORY_CARD_HEIGHT + 34)
        self._mk_upgrade_card_preview_layout = QVBoxLayout(self._mk_upgrade_card_preview)
        self._mk_upgrade_card_preview_layout.setContentsMargins(17, 17, 17, 17)
        upgrade_box.addWidget(upgrade_title)
        upgrade_box.addWidget(self._mk_upgrade_card_preview, 0, Qt.AlignmentFlag.AlignCenter)
        card_compare.addLayout(current_box, 1)
        card_compare.addWidget(connector, 0, Qt.AlignmentFlag.AlignBottom)
        card_compare.addLayout(upgrade_box, 1)
        result_layout.addLayout(card_compare)
        self._mk_compare_panel = QFrame()
        self._mk_compare_panel.setObjectName("mkUpgradeComparePanel")
        self._mk_compare_layout = QVBoxLayout(self._mk_compare_panel)
        self._mk_compare_layout.setContentsMargins(10, 10, 10, 10)
        self._mk_compare_layout.setSpacing(6)
        result_layout.addWidget(self._mk_compare_panel)
        self._mk_cost_panel = QFrame()
        self._mk_cost_panel.setObjectName("mkUpgradeCostPanel")
        mk_cost_layout = QVBoxLayout(self._mk_cost_panel)
        mk_cost_layout.setContentsMargins(10, 8, 10, 8)
        mk_cost_layout.setSpacing(0)
        self._mk_upgrade_preview = QLabel()
        self._mk_upgrade_preview.setObjectName("mkUpgradePreview")
        self._mk_upgrade_preview.setWordWrap(True)
        mk_cost_layout.addWidget(self._mk_upgrade_preview)
        result_layout.addWidget(self._mk_cost_panel)
        result_layout.addStretch(1)
        confirm_zone = QFrame()
        confirm_zone.setObjectName("mkUpgradeConfirmZone")
        confirm_layout = QVBoxLayout(confirm_zone)
        confirm_layout.setContentsMargins(10, 8, 10, 8)
        confirm_layout.setSpacing(4)
        self._mk_upgrade_confirm = QCheckBox("Confirm MK upgrade")
        self._mk_upgrade_confirm.setObjectName("mkUpgradeConfirm")
        self._mk_upgrade_confirm.stateChanged.connect(self._refresh_mk_upgrade_button)
        confirm_layout.addWidget(self._mk_upgrade_confirm)
        self._mk_upgrade_button = QPushButton("Upgrade MK")
        self._mk_upgrade_button.setObjectName("mkUpgradeButton")
        self._mk_upgrade_button.clicked.connect(self._upgrade_selected_mk_card)
        result_layout.addWidget(confirm_zone)
        result_layout.addWidget(self._mk_upgrade_button)

        layout.addWidget(select_panel, 3)
        layout.addWidget(result_panel, 1)
        return panel

    def _refresh_mk_upgrade_panel(self) -> None:
        if not hasattr(self, "_mk_upgrade_grid"):
            return
        self._refresh_mk_upgrade_filter_options()
        self._clear_layout(self._mk_upgrade_grid)
        rows = self._mk_upgrade_rows()
        if self._mk_selected_card_id is not None and all(row.card.card_id != self._mk_selected_card_id for row in rows):
            self._mk_selected_card_id = None
        columns = self._grid_columns_for_scroll(self._mk_upgrade_scroll)
        for column in range(columns):
            self._mk_upgrade_grid.setColumnMinimumWidth(column, INVENTORY_CARD_WIDTH)
        if not rows:
            empty = QLabel("No available cards match the current filters.")
            empty.setObjectName("craftEmptyState")
            self._mk_upgrade_grid.addWidget(empty, 0, 0)
        for index, row in enumerate(rows):
            card = self._build_mk_upgrade_selection_card(row)
            self._mk_upgrade_grid.addWidget(
                card,
                index // columns,
                index % columns,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
        self._mk_upgrade_grid.setColumnStretch(columns, 1)
        self._refresh_mk_upgrade_preview()

    def _refresh_mk_upgrade_filter_options(self) -> None:
        rows = self._mk_upgrade_rows(include_filters=False)
        self._set_options(self._mk_upgrade_type, ["All", *sorted({self._card_function_label(row) for row in rows})])
        self._set_options(self._mk_upgrade_mk, ["All", *[str(level) for level in sorted({row.mk_level for row in rows})]])
        self._set_options(self._mk_upgrade_rarity, ["All", *[rarity.value.title() for rarity in Rarity]])
        if hasattr(self, "_mk_upgrade_type_chip_layout"):
            self._refresh_chip_group(self._mk_upgrade_type_chip_layout, self._mk_upgrade_type, self._mk_upgrade_type.objectName())
            self._refresh_chip_group(self._mk_upgrade_mk_chip_layout, self._mk_upgrade_mk, self._mk_upgrade_mk.objectName())
            self._refresh_chip_group(self._mk_upgrade_rarity_chip_layout, self._mk_upgrade_rarity, self._mk_upgrade_rarity.objectName())
            self._refresh_chip_group(self._mk_upgrade_sort_chip_layout, self._mk_upgrade_sort, self._mk_upgrade_sort.objectName())

    def _mk_upgrade_rows(self, include_filters: bool = True) -> tuple[CardInventoryRow, ...]:
        rows: list[CardInventoryRow] = []
        search = self._mk_upgrade_search.text().strip().lower() if include_filters else ""
        selected_type = self._mk_upgrade_type.currentText() if include_filters else "All"
        selected_mk = self._mk_upgrade_mk.currentText() if include_filters else "All"
        selected_rarity = self._mk_upgrade_rarity.currentText() if include_filters else "All"
        for stack in self._state.inventory_card_stacks():
            card = stack.first_card
            definition = self._definitions.get(card.definition_id)
            if not isinstance(definition, (MachineDefinition, EnergyDefinition, RecipeDefinition, FreightDefinition)):
                continue
            row = CardInventoryRow(card, definition, stack.quantity, "Available")
            type_label = self._card_function_label(row)
            if search and search not in f"{definition.name} {type_label} {row.rarity.value}".lower():
                continue
            if selected_type not in ("", "All", type_label):
                continue
            if selected_mk not in ("", "All", str(row.mk_level)):
                continue
            if selected_rarity not in ("", "All", row.rarity.value.title()):
                continue
            rows.append(row)
        sort = self._mk_upgrade_sort.currentText() if hasattr(self, "_mk_upgrade_sort") else "Name"
        if sort == "Type":
            rows.sort(key=lambda row: (self._card_function_label(row), row.definition.name))
        elif sort == "MK":
            rows.sort(key=lambda row: (row.mk_level, row.definition.name))
        elif sort == "Rarity":
            order = {rarity: index for index, rarity in enumerate(Rarity)}
            rows.sort(key=lambda row: (order[row.rarity], row.definition.name))
        else:
            rows.sort(key=lambda row: row.definition.name)
        return tuple(rows)

    def _build_mk_upgrade_selection_card(self, row: CardInventoryRow) -> QFrame:
        selected = row.card.card_id == self._mk_selected_card_id
        try:
            next_mk_definition(row.card, self._definitions)
            footer_left = f"+{row.card.output_bonus_percent:.1f}%"
            status = "Available"
        except ValueError:
            footer_left = "MAX MK"
            status = "Max MK"
        display_row = CardInventoryRow(row.card, row.definition, row.quantity, status)
        card = self._build_game_craft_grid_card(
            display_row,
            object_name="mkUpgradeSelectionCard",
            selected=selected,
            footer_left=footer_left,
            footer_right=f"Owned ×{row.quantity}",
            click=lambda card_id=row.card.card_id: self._select_mk_upgrade_card(card_id),
        )
        card.setProperty("cardId", row.card.card_id)
        card.setProperty("definitionId", row.definition.definition_id)
        return card

    def _select_mk_upgrade_card(self, card_id: str) -> None:
        self._mk_selected_card_id = card_id
        self._mk_upgrade_confirm.setChecked(False)
        self._refresh_mk_upgrade_panel()

    def _build_mk_preview_card(self, row: CardInventoryRow, selected: bool) -> QFrame:
        return self._build_game_craft_grid_card(
            row,
            object_name="mkUpgradePreviewCard",
            selected=selected,
            footer_left=f"+{row.card.output_bonus_percent:.1f}%",
            footer_right="Current" if selected else "Upgrade",
            click=lambda: None,
            enabled=True,
        )

    def _mk_placeholder(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("mkUpgradePlaceholder")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setMinimumHeight(INVENTORY_CARD_HEIGHT)
        return label

    def _add_mk_compare_row(self, label: str, current_value: str, next_value: str) -> None:
        row = QFrame()
        row.setObjectName("mkUpgradeCompareRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        name = QLabel(label)
        name.setObjectName("mkUpgradeCompareLabel")
        current = QLabel(current_value)
        current.setObjectName("mkUpgradeCompareValue")
        arrow = QLabel("→")
        arrow.setObjectName("mkUpgradeCompareArrow")
        target = QLabel(next_value)
        target.setObjectName("mkUpgradeCompareValue")
        layout.addWidget(name, 2)
        layout.addWidget(current, 2)
        layout.addWidget(arrow)
        layout.addWidget(target, 2)
        self._mk_compare_layout.addWidget(row)

    def _mk_compare_pairs(
        self,
        card,
        current_definition: CardDefinition,
        next_definition: CardDefinition,
    ) -> tuple[tuple[str, str, str], ...]:
        if isinstance(current_definition, MachineDefinition) and isinstance(next_definition, MachineDefinition):
            return (
                (
                    "BASE OUTPUT",
                    f"{current_definition.base_output_per_tick * card.output_multiplier:g}",
                    f"{next_definition.base_output_per_tick * card.output_multiplier:g}",
                ),
                (
                    "POWER",
                    f"{current_definition.base_power_draw * card.power_multiplier:g} MW",
                    f"{next_definition.base_power_draw * card.power_multiplier:g} MW",
                ),
            )
        if isinstance(current_definition, EnergyDefinition) and isinstance(next_definition, EnergyDefinition):
            return (
                (
                    "GENERATION",
                    f"{current_definition.base_power_output * card.output_multiplier:g} MW",
                    f"{next_definition.base_power_output * card.output_multiplier:g} MW",
                ),
            )
        if isinstance(current_definition, RecipeDefinition) and isinstance(next_definition, RecipeDefinition):
            return (
                ("INPUTS", self._resources_text(dict(current_definition.input_resources)), self._resources_text(dict(next_definition.input_resources))),
                ("OUTPUTS", self._resources_text(dict(current_definition.output_resources)), self._resources_text(dict(next_definition.output_resources))),
            )
        if isinstance(current_definition, FreightDefinition) and isinstance(next_definition, FreightDefinition):
            current_stats = freight_stats(card, current_definition)
            next_stats = freight_stats(card, next_definition)
            return (
                ("CAPACITY", f"{current_stats.capacity:g}", f"{next_stats.capacity:g}"),
                ("TRANSPORT TIME", f"{current_stats.transport_time_seconds:g}s", f"{next_stats.transport_time_seconds:g}s"),
            )
        return (("BASE", self._base_values_text(current_definition), self._base_values_text(next_definition)),)

    def _refresh_mk_upgrade_preview(self, *args) -> None:
        self._clear_layout(self._mk_current_card_layout)
        self._clear_layout(self._mk_upgrade_card_preview_layout)
        self._clear_layout(self._mk_compare_layout)
        card_id = self._mk_selected_card_id
        if card_id is None or card_id not in self._state.cards:
            self._mk_current_card_layout.addWidget(self._mk_placeholder("SELECT CARD"))
            self._mk_upgrade_card_preview_layout.addWidget(self._mk_placeholder("UPGRADE PREVIEW LOCKED"))
            self._mk_upgrade_preview.setText("")
            self._refresh_mk_upgrade_button()
            return
        card = self._state.cards[card_id]
        current_definition = self._definitions.get(card.definition_id)
        if current_definition is None:
            self._mk_current_card_layout.addWidget(self._mk_placeholder("Unknown definition."))
            self._mk_upgrade_card_preview_layout.addWidget(self._mk_placeholder("MAX MK"))
            self._mk_upgrade_preview.setText("MAX MK")
            self._refresh_mk_upgrade_button()
            return
        current_row = CardInventoryRow(card, current_definition, 1, "Selected")
        self._mk_current_card_layout.addWidget(
            self._build_mk_preview_card(current_row, selected=True),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        try:
            next_definition = next_mk_definition(card, self._definitions)
        except ValueError as error:
            next_definition = None
            self._mk_upgrade_preview.setText(str(error))
        if next_definition is None:
            self._mk_upgrade_card_preview_layout.addWidget(self._mk_placeholder("MAX MK"))
            self._add_mk_compare_row("MK", str(self._mk_level(current_definition)), "MAX")
            self._add_mk_compare_row("RARITY", card.rarity.value.title(), card.rarity.value.title())
            self._add_mk_compare_row("BONUS", f"+{card.output_bonus_percent:.1f}%", f"+{card.output_bonus_percent:.1f}%")
            self._mk_upgrade_preview.setText("MAX MK")
            self._refresh_mk_upgrade_button()
            return
        next_card = create_card_instance(
            f"mk-preview-{card.card_id}",
            next_definition.definition_id,
            next_definition.card_kind,
            card.rarity,
            bonus_tenths=card.output_bonus_tenths,
        )
        next_row = CardInventoryRow(next_card, next_definition, 1, "Upgrade")
        self._mk_upgrade_card_preview_layout.addWidget(
            self._build_mk_preview_card(next_row, selected=False),
            0,
            Qt.AlignmentFlag.AlignCenter,
        )
        cost = mk_upgrade_scrap_cost(self._mk_level(current_definition), self._mk_level(next_definition))
        self._add_mk_compare_row("MK", str(self._mk_level(current_definition)), str(self._mk_level(next_definition)))
        for label, current_value, next_value in self._mk_compare_pairs(card, current_definition, next_definition):
            self._add_mk_compare_row(label, current_value, next_value)
        self._add_mk_compare_row("RARITY", card.rarity.value.title(), card.rarity.value.title())
        self._add_mk_compare_row("BONUS", f"+{card.output_bonus_percent:.1f}%", f"+{card.output_bonus_percent:.1f}%")
        scrap_state = "ENOUGH" if self._state.scrap.amount >= cost else "NOT ENOUGH"
        self._mk_upgrade_preview.setText(
            f"UPGRADE COST\n"
            f"{cost} SCRAP\n"
            f"AVAILABLE {self._state.scrap.amount}\n"
            f"{scrap_state}"
        )
        self._refresh_mk_upgrade_button()

    def _refresh_mk_upgrade_button(self, *args) -> None:
        card_id = self._mk_selected_card_id
        can_upgrade = False
        if card_id in self._state.cards:
            try:
                card = self._state.cards[card_id]
                current_definition = self._definitions.get(card.definition_id)
                next_definition = next_mk_definition(card, self._definitions)
                if current_definition is not None and next_definition is not None:
                    cost = mk_upgrade_scrap_cost(self._mk_level(current_definition), self._mk_level(next_definition))
                    can_upgrade = self._state.scrap.amount >= cost
            except ValueError:
                can_upgrade = False
        self._mk_upgrade_button.setEnabled(
            self._command_bus is not None
            and can_upgrade
            and self._mk_upgrade_confirm.isChecked()
        )

    def _upgrade_selected_mk_card(self) -> None:
        if self._command_bus is None:
            return
        card_id = self._mk_selected_card_id
        if card_id is None:
            return
        self._command_bus.dispatch(UpgradeCardMk(card_id, self._definitions))
        self._mk_selected_card_id = None
        self._mk_upgrade_confirm.setChecked(False)
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
        if isinstance(definition, RecipeDefinition):
            outputs = effective_recipe_outputs(card, dict(definition.output_resources))
            inputs = effective_recipe_inputs(card, dict(definition.input_resources))
            return f"{self._resources_text(inputs)} -> {self._resources_text(outputs)}"
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"{stats.capacity:g} capacity / {stats.transport_time_seconds:g}s"
        return "-"

    def _base_values_text(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.base_output_per_tick:g} / {definition.base_power_draw:g} MW"
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output:g} MW"
        if isinstance(definition, RecipeDefinition):
            return f"{self._resources_text(dict(definition.input_resources))} -> {self._resources_text(dict(definition.output_resources))}"
        if isinstance(definition, FreightDefinition):
            return f"{definition.base_capacity:g} capacity / {definition.base_transport_time_seconds:g}s"
        return "-"

    def _mk_level(self, definition: CardDefinition) -> int:
        if isinstance(definition, RecipeDefinition):
            return int(getattr(definition, "mk_level", 0))
        if isinstance(definition, FreightDefinition):
            return definition.class_level
        return definition.mk_level

    def _resources_text(self, resources: dict[str, float]) -> str:
        return ", ".join(
            f"{amount:g} {resource_id.replace('_', ' ').title()}"
            for resource_id, amount in resources.items()
        )

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
