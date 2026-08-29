from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.commands import CommandBus, OpenPack
from production_zero.core.cards import CardInstance, effective_recipe_inputs, effective_recipe_outputs
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.inventory import CardInventoryRow
from production_zero.core.packs import FULL_PACK, PACK_CATEGORIES, PACK_TYPE_LABELS, PackInstance
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.ui.factory_view_v2 import _display_card_title
from production_zero.ui.game_ui.icons import GameIcon, draw_game_icon
from production_zero.ui.game_ui.rendering import draw_machine_card_prototype
from production_zero.ui.game_ui.tokens import Accent, GAME_UI_TOKENS
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.widget_lifecycle import clear_layout_safely


PACK_CARD_WIDTH = 220
PACK_CARD_HEIGHT = 340
PACK_GRID_SPACING = 18
PACK_RESULT_CARD_WIDTH = INVENTORY_CARD_WIDTH
PACK_RESULT_CARD_HEIGHT = INVENTORY_CARD_HEIGHT
PACK_RESULT_GRID_SPACING = 10
FREIGHT_ICON_KEYS = {
    "truck": ("vehicle", "vehicle"),
    "train": ("rail", "rail"),
    "ship": ("ship", "ship"),
    "aircraft": ("aircraft", "aircraft"),
}


class PackCategorySelectorButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("packCategorySelector")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(31)


class BoosterPackTileFrame(QFrame):
    def __init__(self, pack: PackInstance, open_callback: Callable[[str, str], None]) -> None:
        super().__init__()
        self._pack = pack
        self._open_callback = open_callback
        self._selected_category_id = "general"
        self._category_flyout: QFrame | None = None
        self.setObjectName("boosterPackTile")
        self.setProperty("packId", pack.pack_id)
        self.setProperty("packType", pack.pack_type)
        self.setFixedSize(PACK_CARD_WIDTH, PACK_CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._name_label = self._hidden_label("boosterPackName", PACK_TYPE_LABELS[pack.pack_type])
        self._type_label = self._hidden_label("boosterPackType", self._pack_type_text())
        self._count_label = self._hidden_label("boosterPackCardCount", f"{self._card_count()} Cards")
        self._source_label = self._hidden_label("boosterPackSource", self._source_text(pack.source))
        self._category_label = self._hidden_label("boosterPackCategoryLabel", "CATEGORY")
        self._category_info = self._hidden_label("boosterPackCategoryInfo", "Category: General")
        self._quantity_label = None

        self._icon = ResourceIconWidget(pack.pack_type, "package", "steel" if pack.pack_type == FULL_PACK else "chemical", size=1)
        self._icon.setObjectName("boosterPackIcon")
        self._icon.setParent(self)
        self._icon.hide()

        self._category_select = QComboBox(self)
        self._category_select.setObjectName("packCategorySelect")
        for option in PACK_CATEGORIES:
            self._category_select.addItem(option.name, option.category_id)
        self._category_select.setVisible(False)
        self._category_select.setEnabled(pack.pack_type == FULL_PACK)
        self._category_select.currentIndexChanged.connect(self._sync_selector_text)

        self._category_button = PackCategorySelectorButton(self)
        self._category_button.setVisible(pack.pack_type == FULL_PACK)
        self._category_button.clicked.connect(self._toggle_category_flyout)

        self._open_button = QPushButton("Open", self)
        self._open_button.setObjectName("openPackButton")
        self._open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_button.clicked.connect(lambda checked=False: self._open_selected_pack())

        self._sync_selector_text()
        self._position_controls()

    def _hidden_label(self, object_name: str, text: str) -> QLabel:
        label = QLabel(text, self)
        label.setObjectName(object_name)
        label.hide()
        return label

    def _card_count(self) -> int:
        return 6 if self._pack.pack_type == FULL_PACK else 3

    def _pack_type_text(self) -> str:
        if self._pack.pack_type == FULL_PACK:
            return "Full Pack / Category Choice"
        return "Daily Mini Pack / General"

    def _source_text(self, source: str) -> str:
        if source.strip().lower() in {"dev", "debug", "test"}:
            return ""
        return f"Source: {source}"

    def _accent(self) -> Accent:
        return Accent.RARE if self._pack.pack_type == FULL_PACK else Accent.STORAGE

    def _sync_selector_text(self) -> None:
        text = self._category_select.currentText() or "General"
        self._category_button.setText(f"{text.upper()}  >")
        self._selected_category_id = self._category_select.currentData() or "general"
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_controls()

    def _position_controls(self) -> None:
        rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        if self._pack.pack_type == FULL_PACK:
            self._category_button.setGeometry(int(rect.left() + 14), int(rect.bottom() - 80), int(rect.width() - 28), 31)
            self._open_button.setGeometry(int(rect.left() + 14), int(rect.bottom() - 43), int(rect.width() - 28), 30)
        else:
            self._category_button.setGeometry(0, 0, 1, 1)
            self._open_button.setGeometry(int(rect.left() + 14), int(rect.bottom() - 43), int(rect.width() - 28), 30)
        if self._category_flyout is not None:
            parent = self._category_flyout.parentWidget()
            if parent is not None:
                origin = self.mapTo(parent, QPoint(int(rect.left() + 14), int(rect.bottom() + 5)))
                self._category_flyout.setGeometry(origin.x(), origin.y(), int(rect.width() - 28), 91)

    def _toggle_category_flyout(self) -> None:
        if self._pack.pack_type != FULL_PACK:
            return
        if self._category_flyout is None:
            self._category_flyout = QFrame(self.parentWidget() or self)
            self._category_flyout.setObjectName("packCategoryFlyout")
            layout = QGridLayout(self._category_flyout)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setHorizontalSpacing(5)
            layout.setVerticalSpacing(5)
            for index in range(self._category_select.count()):
                option = QPushButton(self._category_select.itemText(index).upper(), self._category_flyout)
                option.setObjectName("packCategoryOption")
                option.setProperty("categoryId", self._category_select.itemData(index))
                option.setFixedHeight(22)
                option.clicked.connect(lambda checked=False, row=index: self._choose_category(row))
                layout.addWidget(option, index // 2, index % 2)
            self._position_controls()
        self._category_flyout.setVisible(not self._category_flyout.isVisible())
        self._category_flyout.raise_()

    def _choose_category(self, index: int) -> None:
        self._category_select.setCurrentIndex(index)
        if self._category_flyout is not None:
            self._category_flyout.hide()

    def _open_selected_pack(self) -> None:
        if self._category_flyout is not None:
            self._category_flyout.hide()
            self._category_flyout.setParent(self)
            self._category_flyout.deleteLater()
            self._category_flyout = None
        self._open_callback(self._pack.pack_id, self._category_select.currentData() or "general")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
            draw_machine_card_prototype(
                painter,
                rect,
                title=PACK_TYPE_LABELS[self._pack.pack_type].upper(),
                family="transport" if self._pack.pack_type == FULL_PACK else "energy",
                meta="CATEGORY CHOICE" if self._pack.pack_type == FULL_PACK else "DAILY · GENERAL",
                detail=f"{self._card_count()} CARDS",
                secondary="PACK READY",
                active=True,
                hover=self.underMouse(),
            )
            self._draw_pack_seal(painter, rect)
        finally:
            painter.end()
        super().paintEvent(event)

    def _draw_pack_seal(self, painter: QPainter, rect: QRectF) -> None:
        accent = GAME_UI_TOKENS.colors.accent(self._accent(), 225)
        stage = QRectF(rect.left() + 27, rect.top() + 72, rect.width() - 54, 105)
        glow = QRadialGradient(stage.center(), stage.width() * 0.66)
        glow.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 82))
        glow.setColorAt(0.72, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(stage.adjusted(-18, -18, 18, 18))
        body = QLinearGradient(stage.topLeft(), stage.bottomRight())
        body.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 198))
        body.setColorAt(0.55, QColor(accent.red(), accent.green(), accent.blue(), 116))
        body.setColorAt(1.0, QColor(8, 10, 10, 232))
        painter.setPen(QPen(QColor(2, 4, 4, 230), 2))
        painter.setBrush(body)
        painter.drawRoundedRect(stage, 8, 8)
        draw_game_icon(painter, GameIcon.PACKS, stage.adjusted(31, 20, -31, -20), accent=self._accent())
        painter.setPen(QPen(QColor(255, 255, 245, 56), 1))
        painter.drawLine(QPointF(stage.left() + 13, stage.top() + 11), QPointF(stage.right() - 13, stage.top() + 11))
        painter.setPen(QPen(QColor(0, 0, 0, 112), 1))
        painter.drawLine(QPointF(stage.left() + 13, stage.bottom() - 10), QPointF(stage.right() - 13, stage.bottom() - 10))

class PacksView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._state = state
        self._bus = command_bus
        self._definitions = definitions
        self._on_state_changed = on_state_changed
        self._pack_grid_columns_used = 0
        self._pack_grid_signature: tuple[str, ...] = ()
        self._result_signature: tuple[str, ...] = ()
        self._result_grid_columns_used = 0
        self._result_hover_popup: CardHoverInfoPopup | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._stack = QStackedWidget()
        self._stack.setObjectName("packsStack")
        self._stack.addWidget(self._build_pack_grid_page())
        self._stack.addWidget(self._build_result_page())
        layout.addWidget(self._stack, 1)
        self.refresh(force=True)

    def refresh(self, force: bool = False) -> None:
        self._refresh_pack_grid(force=force)
        self._refresh_results(force=force)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if (
            hasattr(self, "_pack_scroll")
            and watched is self._pack_scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            columns = self._pack_grid_columns()
            if columns != self._pack_grid_columns_used:
                self._refresh_pack_grid(force=True)
        if (
            hasattr(self, "_result_scroll")
            and watched is self._result_scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            columns = self._result_grid_columns()
            if columns != self._result_grid_columns_used:
                self._refresh_results(force=True)
        return super().eventFilter(watched, event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_pack_scroll"):
            columns = self._pack_grid_columns()
            if columns != self._pack_grid_columns_used:
                self._refresh_pack_grid(force=True)
        if hasattr(self, "_result_scroll"):
            columns = self._result_grid_columns()
            if columns != self._result_grid_columns_used:
                self._refresh_results(force=True)

    def _build_pack_grid_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("packsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_unopened_header())

        self._pack_scroll = QScrollArea()
        self._pack_scroll.setObjectName("boosterPackScroll")
        self._pack_scroll.setWidgetResizable(True)
        self._pack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pack_scroll.viewport().installEventFilter(self)
        self._grid_container = QWidget()
        self._grid_container.setObjectName("boosterPackGrid")
        self._grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(PACK_GRID_SPACING)
        self._pack_scroll.setWidget(self._grid_container)
        layout.addWidget(self._pack_scroll, 1)
        return page

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("packsHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(12)
        icon = ResourceIconWidget("packs", "package", "steel", size=42)
        icon.setObjectName("packsHeaderIcon")
        copy = QVBoxLayout()
        copy.setSpacing(2)
        title = QLabel("PACKS")
        title.setObjectName("packsHeaderTitle")
        subtitle = QLabel("OPEN PACKS · CHOOSE CATEGORY · EXPAND YOUR COLLECTION")
        subtitle.setObjectName("packsHeaderSubtitle")
        copy.addWidget(title)
        copy.addWidget(subtitle)
        layout.addWidget(icon)
        layout.addLayout(copy, 1)
        self._unopened_metric = self._header_metric("UNOPENED", "0")
        self._ready_metric = self._header_metric("READY", "0")
        layout.addWidget(self._unopened_metric)
        layout.addWidget(self._ready_metric)
        return header

    def _header_metric(self, label: str, value: str) -> QFrame:
        metric = QFrame()
        metric.setObjectName("packsHeaderMetric")
        metric.setFixedSize(148, 54)
        layout = QVBoxLayout(metric)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(1)
        label_widget = QLabel(label)
        label_widget.setObjectName("packsHeaderMetricLabel")
        value_widget = QLabel(value)
        value_widget.setObjectName("packsHeaderMetricValue")
        value_widget.setProperty("metricKey", label.lower())
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return metric

    def _build_unopened_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("packsUnopenedHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        title = QLabel("UNOPENED PACKS")
        title.setObjectName("packsSectionTitle")
        self._pack_count_label = QLabel()
        self._pack_count_label.setObjectName("packsUnopenedCount")
        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self._pack_count_label)
        return header

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("PACK OPENED")
        title.setObjectName("packsSectionTitle")
        back = QPushButton("Back to Packs")
        back.setObjectName("backToPacksButton")
        back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back)
        layout.addLayout(header)

        self._results = QLabel()
        self._results.setObjectName("packResultsLabel")
        self._results.setWordWrap(True)
        layout.addWidget(self._results)

        self._result_scroll = QScrollArea()
        self._result_scroll.setObjectName("packResultScroll")
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._result_scroll.viewport().installEventFilter(self)
        self._result_container = QWidget()
        self._result_container.setObjectName("packResultGrid")
        self._result_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._result_grid = QGridLayout(self._result_container)
        self._result_grid.setContentsMargins(0, 0, 0, 0)
        self._result_grid.setSpacing(PACK_RESULT_GRID_SPACING)
        self._result_scroll.setWidget(self._result_container)
        layout.addWidget(self._result_scroll, 1)
        return page

    def _refresh_pack_grid(self, force: bool = False) -> None:
        packs = self._pack_entries()
        columns = self._pack_grid_columns()
        signature = tuple(pack.pack_id for pack in packs)
        if not force and signature == self._pack_grid_signature and columns == self._pack_grid_columns_used:
            return
        self._pack_grid_signature = signature
        for flyout in self._grid_container.findChildren(QFrame, "packCategoryFlyout"):
            flyout.hide()
            flyout.setParent(None)
            flyout.deleteLater()
        self._clear_layout(self._grid)
        total_packs = len(packs)
        self._pack_count_label.setText(f"{total_packs} unopened" if total_packs else "No unopened packs")
        for label in self.findChildren(QLabel, "packsHeaderMetricValue"):
            if label.property("metricKey") in {"unopened", "ready"}:
                label.setText(str(total_packs))
        self._pack_grid_columns_used = columns
        if not packs:
            empty = QLabel("No unopened packs available.")
            empty.setObjectName("packsEmptyState")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(empty, 0, 0)
            return
        side_margin = self._pack_grid_side_margin(columns)
        self._grid.setContentsMargins(side_margin, 10, side_margin, 12)
        rows = (len(packs) + columns - 1) // columns
        min_height = rows * PACK_CARD_HEIGHT + max(0, rows - 1) * PACK_GRID_SPACING + 16
        self._grid_container.setMinimumHeight(min_height)
        for index, pack in enumerate(packs):
            self._grid.addWidget(self._booster_pack_tile(pack), index // columns, index % columns)
        for column in range(columns):
            self._grid.setColumnStretch(column, 0)
        self._grid.setRowStretch(rows, 1)
        self._grid.activate()
        self._grid_container.updateGeometry()

    def _booster_pack_tile(self, pack: PackInstance) -> QFrame:
        return BoosterPackTileFrame(pack, self._open_pack)

    def _pack_grid_columns(self) -> int:
        width = self._pack_grid_available_width()
        if width <= 0:
            width = 1100
        pitch = PACK_CARD_WIDTH + PACK_GRID_SPACING
        return max(1, min(6, width // pitch))

    def _pack_grid_side_margin(self, columns: int) -> int:
        width = self._pack_grid_available_width()
        used = columns * PACK_CARD_WIDTH + max(0, columns - 1) * PACK_GRID_SPACING
        return max(0, (width - used) // 2)

    def _pack_grid_available_width(self) -> int:
        if not hasattr(self, "_pack_scroll"):
            return self.width()
        width = self._pack_scroll.viewport().width()
        return width - self._pack_scroll.verticalScrollBar().sizeHint().width()

    def _refresh_results(self, force: bool = False) -> None:
        signature = tuple(card.card_id for card in self._state.packs.last_opened_cards)
        if not force and signature == self._result_signature:
            return
        self._result_signature = signature
        self._clear_layout(self._result_grid)
        if self._state.packs.last_opened_cards:
            self._results.setText("Last opened:")
            columns = self._result_grid_columns()
            self._result_grid_columns_used = columns
            side_margin = self._result_grid_side_margin(columns)
            self._result_grid.setContentsMargins(side_margin, 6, side_margin, 12)
            rows = (len(self._state.packs.last_opened_cards) + columns - 1) // columns
            min_height = rows * PACK_RESULT_CARD_HEIGHT + max(0, rows - 1) * PACK_RESULT_GRID_SPACING + 18
            self._result_container.setMinimumHeight(min_height)
            for index, card in enumerate(self._state.packs.last_opened_cards):
                self._result_grid.addWidget(
                    self._result_card_tile(card),
                    index // columns,
                    index % columns,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                )
            for column in range(columns):
                self._result_grid.setColumnStretch(column, 0)
            self._result_grid.setRowStretch(rows, 1)
            self._result_grid.activate()
            self._result_container.updateGeometry()
        else:
            self._results.setText("No packs opened yet.")

    def _result_card_tile(self, card: CardInstance) -> QFrame:
        definition = self._definitions[card.definition_id]
        row = CardInventoryRow(card, definition, 1, "Received")
        tile = InventoryCardFrame(
            row,
            title=self._result_card_title(definition).upper(),
            family=self._result_card_family(definition),
            meta=self._result_card_meta(definition, card).upper(),
            detail=self._result_card_detail(card, definition).upper(),
            selected=False,
            status_text="Received",
        )
        tile.setProperty("definitionId", card.definition_id)
        tile.setProperty("cardType", self._card_type_key(definition))
        tile.hovered.connect(lambda result_card=card, source=tile: self._show_result_hover(result_card, source))
        tile.unhovered.connect(self._hide_result_hover)
        self._add_hidden_result_label(tile, "inventoryCardName", definition.name)
        self._add_hidden_result_label(tile, "inventoryCardMk", self._card_meta(definition))
        self._add_hidden_result_label(tile, "inventoryCardRarity", card.rarity.value.title())
        self._add_hidden_result_label(tile, "inventoryCardFunction", self._card_function_label(definition).upper())
        self._add_hidden_result_label(tile, "inventoryCardBonus", f"+{card.output_bonus_percent:.1f}%")
        self._add_hidden_result_label(tile, "inventoryCardQuantity", f"Qty 1")
        self._add_hidden_result_label(tile, "inventoryCardStatus", "Received")
        icon_key, accent_key, icon_resource_id = self._icon_signature(card, definition)
        icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=1)
        icon.setObjectName("inventoryCardIcon")
        icon.setParent(tile)
        icon.hide()
        rarity_line = QFrame(tile)
        rarity_line.setObjectName("inventoryRarityLine")
        rarity_line.setProperty("rarity", card.rarity.value)
        rarity_line.hide()
        return tile

    def _add_hidden_result_label(self, tile: QFrame, object_name: str, text: str) -> QLabel:
        label = QLabel(text, tile)
        label.setObjectName(object_name)
        label.hide()
        return label

    def _result_card_family(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return "energy"
        if isinstance(definition, RecipeDefinition):
            return definition.stage.value
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return "processor"

    def _result_card_title(self, definition: CardDefinition) -> str:
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return _display_card_title(definition)

    def _result_card_meta(self, definition: CardDefinition, card: CardInstance) -> str:
        if isinstance(definition, FreightDefinition):
            return f"{definition.class_label} / {card.rarity.value}"
        if isinstance(definition, RecipeDefinition):
            return card.rarity.value
        if isinstance(definition, (MachineDefinition, EnergyDefinition)):
            return f"MK{definition.mk_level} / {card.rarity.value}"
        return card.rarity.value

    def _result_card_detail(self, card: CardInstance, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
            amount = production.output_amount_for(definition) * (1 + card.output_bonus_percent / 100)
            return f"+{amount:.0f}/cycle"
        if isinstance(definition, EnergyDefinition):
            return f"+{definition.base_power_output:.0f} MW"
        if isinstance(definition, RecipeDefinition):
            output = next(iter(definition.output_resources), definition.definition_id)
            return output.replace("_", " ")
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"{stats.capacity:.0f} cap"
        return self._card_function_label(definition)

    def _result_grid_columns(self) -> int:
        width = self._result_grid_available_width()
        if width <= 0:
            width = 900
        pitch = PACK_RESULT_CARD_WIDTH + PACK_RESULT_GRID_SPACING
        return max(1, min(8, width // pitch))

    def _result_grid_side_margin(self, columns: int) -> int:
        width = self._result_grid_available_width()
        used = columns * PACK_RESULT_CARD_WIDTH + max(0, columns - 1) * PACK_RESULT_GRID_SPACING
        return max(0, (width - used) // 2)

    def _result_grid_available_width(self) -> int:
        if not hasattr(self, "_result_scroll"):
            return self.width()
        return self._result_scroll.viewport().width() - self._result_scroll.verticalScrollBar().sizeHint().width()

    def _show_result_hover(self, card: CardInstance, source: QWidget) -> None:
        definition = self._definitions[card.definition_id]
        if self._result_hover_popup is None:
            self._result_hover_popup = CardHoverInfoPopup(self, object_name="packResultCardHoverInfo", embedded=True)
        icon_key, accent_key, icon_resource_id = self._icon_signature(card, definition)
        sections = self._hover_sections(card, definition)
        signature = (
            card.card_id,
            card.definition_id,
            card.rarity.value,
            card.output_bonus_tenths,
            tuple(sections),
            icon_key,
            accent_key,
            icon_resource_id,
        )
        if self._result_hover_popup.details_signature != signature:
            icon = ResourceIconWidget(icon_resource_id, icon_key, accent_key, size=34)
            self._result_hover_popup.set_details(definition.name, icon, sections, signature)
        else:
            self._result_hover_popup.update_values(sections)
        self._result_hover_popup.show_for(source)

    def _hide_result_hover(self) -> None:
        if self._result_hover_popup is not None:
            self._result_hover_popup.hide()

    def _pack_entries(self) -> tuple[PackInstance, ...]:
        return tuple(sorted(self._state.packs.unopened, key=lambda pack: (pack.pack_type, pack.source, pack.pack_id)))

    def _open_pack(self, pack_id: str, category_id: str) -> None:
        self._bus.dispatch(OpenPack(pack_id, self._definitions, category_id))
        if self._on_state_changed is not None:
            QTimer.singleShot(0, self._on_state_changed)
        QTimer.singleShot(0, self._show_results_after_open)

    def _show_results_after_open(self) -> None:
        self.refresh()
        self._stack.setCurrentIndex(1)

    def _pack_type_text(self, pack: PackInstance) -> str:
        if pack.pack_type == FULL_PACK:
            return "Full Pack / Category Choice"
        return "Daily Mini Pack / General"

    def _source_text(self, source: str) -> str:
        if source.strip().lower() in {"dev", "debug", "test"}:
            return ""
        return f"Source: {source}"

    def _card_count(self, pack_type: str) -> int:
        return 6 if pack_type == FULL_PACK else 3

    def _card_meta(self, definition: CardDefinition) -> str:
        if isinstance(definition, FreightDefinition):
            return definition.class_label
        if isinstance(definition, (MachineDefinition, EnergyDefinition)):
            return f"MK {definition.mk_level}"
        if isinstance(definition, RecipeDefinition):
            return "Recipe"
        return ""

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)

    def _card_type_key(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return "energy"
        if isinstance(definition, RecipeDefinition):
            return definition.stage.value
        if isinstance(definition, FreightDefinition):
            return "freight"
        return "card"

    def _card_function_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value.title()
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, RecipeDefinition):
            return f"{definition.stage.value.title()} Recipe"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.title()
        return "Card"

    def _icon_signature(self, card: CardInstance, definition: CardDefinition) -> tuple[str, str, str]:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
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
        return ("default", "default", card.definition_id)

    def _primary_stat(self, card: CardInstance, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.base_output_per_tick * card.output_multiplier:g} out"
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output * card.output_multiplier:g} MW"
        if isinstance(definition, RecipeDefinition):
            outputs = effective_recipe_outputs(card, dict(definition.output_resources))
            return self._resources_text(outputs)
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"{stats.capacity:g} cap"
        return "-"

    def _hover_sections(self, card: CardInstance, definition: CardDefinition) -> list[tuple[str, str]]:
        sections = [
            ("Rarity", card.rarity.value.title()),
            ("Type", self._card_function_label(definition)),
            ("MK / Class", self._card_meta(definition)),
            ("Bonus", f"+{card.output_bonus_percent:.1f}%"),
            ("Status", "Received"),
        ]
        sections.extend(self._performance_pairs(card, definition))
        return sections

    def _performance_pairs(self, card: CardInstance, definition: CardDefinition) -> tuple[tuple[str, str], ...]:
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

    def _resources_text(self, resources: dict[str, float]) -> str:
        if not resources:
            return "-"
        return ", ".join(f"{resource_id.replace('_', ' ').title()} {amount:g}" for resource_id, amount in resources.items())
