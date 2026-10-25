from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
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
from production_zero.core.cards import CardInstance
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.inventory import CardInventoryRow
from production_zero.core.packs import FULL_PACK, PACK_CATEGORIES, PACK_TYPE_LABELS, PackInstance
from production_zero.core.state import GameState
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.factory_view_v2 import _display_card_title
from production_zero.ui.game_ui.tokens import Accent
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryCardFrame
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.resource_icons import ResourceIconWidget, card_resource_icon_signature
from production_zero.ui.pack_reveal import RevealCard, OpeningFocus, draw_pack_case, OPENING_TOTAL_MS
from production_zero.ui.widget_lifecycle import clear_layout_safely


PACK_CARD_WIDTH = 220
PACK_CARD_HEIGHT = 340
PACK_GRID_SPACING = 18
PACK_RESULT_CARD_WIDTH = INVENTORY_CARD_WIDTH
PACK_RESULT_CARD_HEIGHT = INVENTORY_CARD_HEIGHT
PACK_RESULT_GRID_SPACING = 10
PACK_COMPOSITION_MAX_WIDTH = 1120
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
        self._refresh_category_flyout_state()
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
        self._refresh_category_flyout_state()
        self._category_flyout.setVisible(not self._category_flyout.isVisible())
        self._category_flyout.raise_()

    def _choose_category(self, index: int) -> None:
        self._category_select.setCurrentIndex(index)
        if self._category_flyout is not None:
            self._category_flyout.hide()

    def _refresh_category_flyout_state(self) -> None:
        if self._category_flyout is None:
            return
        current = self._category_select.currentData() or "general"
        for option in self._category_flyout.findChildren(QPushButton, "packCategoryOption"):
            option.setProperty("active", option.property("categoryId") == current)
            option.style().unpolish(option)
            option.style().polish(option)

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
            accent = QColor("#59cce6" if self._pack.pack_type == FULL_PACK else "#ffd21f")
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0, QColor("#394147"))
            gradient.setColorAt(0.5, QColor("#181d21"))
            gradient.setColorAt(1, QColor("#090c0f"))
            painter.setBrush(gradient)
            painter.setPen(QPen(accent, 1.4))
            painter.drawRoundedRect(rect, 10, 10)
            painter.setPen(QPen(QColor("#5a6269"), 1))
            painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), 6, 6)
            font = painter.font()
            font.setPixelSize(17)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#edf0f1"))
            painter.drawText(QRectF(10, 20, 200, 28), Qt.AlignmentFlag.AlignCenter, PACK_TYPE_LABELS[self._pack.pack_type].upper())
            font.setPixelSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#aeb8c0"))
            painter.drawText(QRectF(10, 48, 200, 20), Qt.AlignmentFlag.AlignCenter, "CATEGORY CHOICE" if self._pack.pack_type == FULL_PACK else "DAILY · GENERAL")
            draw_pack_case(painter, QRectF(20, 78, 180, 132) if self._pack.pack_type == FULL_PACK else QRectF(33, 88, 154, 112), self._card_count(), accent)
            painter.setPen(accent)
            font.setPixelSize(18)
            painter.setFont(font)
            painter.drawText(QRectF(10, 214, 200, 26), Qt.AlignmentFlag.AlignCenter, f"{self._card_count()} CARDS")
            font.setPixelSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#b8c1c7"))
            painter.drawText(QRectF(10, 240, 200, 18), Qt.AlignmentFlag.AlignCenter, "PACK READY")
        finally:
            painter.end()


class PacksView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("packsView")
        self._state = state
        self._bus = command_bus
        self._definitions = definitions
        self._on_state_changed = on_state_changed
        self._pack_grid_columns_used = 0
        self._category_choices = {}
        self._pack_grid_signature: tuple[str, ...] = ()
        self._result_grid_columns_used = 0
        self._flow_state = "idle"
        self._reveal_cards = []
        self._active_cards = ()
        self._deal_timer = QTimer(self)
        self._deal_timer.timeout.connect(self._deal_next)
        self._result_hover_popup: CardHoverInfoPopup | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
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
        if watched is getattr(self, "_result_container", None) and event.type() == QEvent.Type.Resize:
            self._position_confirm()
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
            if hasattr(self, "_focus"):
                self._focus.setGeometry(self._result_scroll.viewport().rect())
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
            if hasattr(self, "_focus"):
                self._focus.setGeometry(self._result_scroll.viewport().rect())
            columns = self._result_grid_columns()
            if columns != self._result_grid_columns_used:
                self._refresh_results(force=True)

    def _build_pack_grid_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("packsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self._pack_scroll = QScrollArea()
        self._pack_scroll.setObjectName("boosterPackScroll")
        self._pack_scroll.setWidgetResizable(True)
        self._pack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pack_scroll.viewport().setObjectName("packsCanvasViewport")
        self._pack_scroll.viewport().installEventFilter(self)
        self._grid_canvas = QWidget()
        self._grid_canvas.setObjectName("packsCompositionCanvas")
        canvas_layout = QVBoxLayout(self._grid_canvas)
        canvas_layout.setContentsMargins(12, 12, 12, 12)
        canvas_layout.setSpacing(0)
        self._grid_container = QWidget()
        self._grid_container.setObjectName("boosterPackGrid")
        self._grid_container.setMaximumWidth(PACK_COMPOSITION_MAX_WIDTH)
        self._grid_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(PACK_GRID_SPACING)
        canvas_layout.addWidget(self._grid_container, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        canvas_layout.addStretch(1)
        self._pack_scroll.setWidget(self._grid_canvas)
        self._grid_container.setAutoFillBackground(False)
        layout.addWidget(self._pack_scroll, 1)
        return page

    def _build_header(self) -> QFrame:
        header = MainTabHeader(
            object_name="packsHeader",
            title="PACKS",
            subtitle="OPEN PACKS · CHOOSE CATEGORY · EXPAND YOUR COLLECTION",
            title_object_name="packsHeaderTitle",
            subtitle_object_name="packsHeaderSubtitle",
            accent=Accent.NEUTRAL,
        )
        return header

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("packResultPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        header_panel = QFrame()
        header_panel.setObjectName("packResultHeader")
        header = QHBoxLayout(header_panel)
        header.setContentsMargins(12, 8, 12, 8)
        header.setSpacing(10)
        title = QLabel("PACK OPENED")
        title.setObjectName("packsSectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        layout.addWidget(header_panel)


        self._result_scroll = QScrollArea()
        self._result_scroll.setObjectName("packResultScroll")
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._result_scroll.viewport().setObjectName("packsCanvasViewport")
        self._result_scroll.viewport().installEventFilter(self)
        self._result_container = QWidget()
        self._result_container.setObjectName("packResultGrid")
        self._result_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._result_grid = QGridLayout(self._result_container)
        self._result_grid.setContentsMargins(0, 0, 0, 0)
        self._result_grid.setSpacing(PACK_RESULT_GRID_SPACING)
        self._result_scroll.setWidget(self._result_container)
        self._result_container.setAutoFillBackground(False)
        self._result_container.installEventFilter(self)
        layout.addWidget(self._result_scroll, 1)
        self._focus = OpeningFocus(self._result_scroll.viewport())
        self._focus.hide()
        self._confirm = QPushButton("CONFIRM && COLLECT", self._result_container)
        self._confirm.setAccessibleName("CONFIRM & COLLECT")
        self._confirm.setObjectName("confirmCollectButton")
        self._confirm.setFixedSize(260, 46)
        self._confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm.clicked.connect(self._confirm_collect)
        self._confirm.hide()
        return page

    def _refresh_pack_grid(self, force: bool = False) -> None:
        packs = self._pack_entries()
        columns = self._pack_grid_columns()
        signature = tuple(pack.pack_id for pack in packs)
        if not force and signature == self._pack_grid_signature and columns == self._pack_grid_columns_used:
            return
        for tile in self._grid_container.findChildren(BoosterPackTileFrame):
            self._category_choices[tile._pack.pack_id] = tile._selected_category_id
        self._category_choices = {key: value for key, value in self._category_choices.items() if key in signature}
        self._pack_grid_signature = signature
        for flyout in self._grid_container.findChildren(QFrame, "packCategoryFlyout"):
            flyout.hide()
            flyout.setParent(None)
            flyout.deleteLater()
        self._clear_layout(self._grid)
        for row in range(self._grid.rowCount()):
            self._grid.setRowStretch(row, 0)
        total_packs = len(packs)
        self._pack_grid_columns_used = columns
        composition_width = max(PACK_CARD_WIDTH + 32, self._pack_grid_available_width())
        self._grid_container.setFixedWidth(composition_width)
        if not packs:
            self._grid.setContentsMargins(16, 16, 16, 16)
            empty = EmptyStatePanel(
                "No unopened packs",
                "Complete contracts and claim supply rewards\nto receive new packs.",
                accent="packs",
                object_name="packsEmptyState",
                parent=self._grid_container,
            )
            icon = empty.findChild(ResourceIconWidget, "emptyStateIcon")
            empty.layout().removeWidget(icon)
            icon.hide()
            icon.deleteLater()
            empty.layout().setSpacing(16)
            empty.findChild(QLabel, "emptyStateTitle").setMinimumWidth(480)
            empty.findChild(QLabel, "emptyStateMessage").setMinimumWidth(480)
            self._grid.addWidget(empty, 0, 0)
            self._grid_container.setMinimumHeight(260)
            return
        side_margin = self._pack_grid_side_margin(columns, total_packs)
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
        tile = BoosterPackTileFrame(pack, self._open_pack)
        category = self._category_choices.get(pack.pack_id, "general")
        tile._category_select.setCurrentIndex(tile._category_select.findData(category))
        return tile

    def _pack_grid_columns(self) -> int:
        width = self._pack_grid_available_width()
        if width <= 0:
            width = 1100
        pitch = PACK_CARD_WIDTH + PACK_GRID_SPACING
        return max(1, min(6, width // pitch))

    def _pack_grid_side_margin(self, columns: int, item_count: int | None = None) -> int:
        width = self._pack_grid_available_width()
        visible_columns = max(1, min(columns, item_count if item_count is not None else columns))
        used = visible_columns * PACK_CARD_WIDTH + max(0, visible_columns - 1) * PACK_GRID_SPACING
        return max(0, (width - used) // 2)

    def _pack_grid_available_width(self) -> int:
        if not hasattr(self, "_pack_scroll"):
            return self.width()
        width = min(self._pack_scroll.viewport().width() - 24, PACK_COMPOSITION_MAX_WIDTH)
        return width - self._pack_scroll.verticalScrollBar().sizeHint().width()

    def _refresh_results(self, force: bool = False) -> None:
        # Reflow existing wrappers; never reconstruct cards during a reveal.
        columns = self._result_grid_columns()
        self._result_grid_columns_used = columns
        for index in reversed(range(self._result_grid.count())):
            self._result_grid.takeAt(index)
        for column in range(8):
            self._result_grid.setColumnMinimumWidth(column, 0)
            self._result_grid.setColumnStretch(column, 0)
        for row in range(8):
            self._result_grid.setRowStretch(row, 0)
        count = len(self._reveal_cards)
        margin = self._result_grid_side_margin(columns, count)
        self._result_grid.setContentsMargins(margin, 10, margin, 12)
        for index, tile in enumerate(self._reveal_cards):
            self._result_grid.addWidget(tile, index // columns, index % columns, Qt.AlignmentFlag.AlignTop)
        rows = (count + columns - 1) // columns
        # Reserve the internal action space from the first frame, even while hidden.
        self._result_container.setMinimumHeight(rows * (PACK_RESULT_CARD_HEIGHT + 10) + 94)
        self._result_grid.setRowStretch(rows, 1)
        self._result_grid.activate()
        self._position_confirm()
        if hasattr(self, "_focus"):
            self._focus.setGeometry(self._result_scroll.viewport().rect())

    def _position_confirm(self) -> None:
        if not hasattr(self, "_confirm") or not self._reveal_cards:
            return
        bottom = max(card.geometry().bottom() for card in self._reveal_cards)
        self._confirm.move((self._result_container.width() - self._confirm.width()) // 2, bottom + 25)

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
        self._add_hidden_result_label(tile, "inventoryCardType", self._card_meta(definition))
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
            return definition.energy_type.value
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return "processor"

    def _result_card_title(self, definition: CardDefinition) -> str:
        if isinstance(definition, FreightDefinition):
            return definition.family.value
        return _display_card_title(definition)

    def _result_card_meta(self, definition: CardDefinition, card: CardInstance) -> str:
        return card.rarity.value

    def _result_card_detail(self, card: CardInstance, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
            amount = production.output_amount_for(definition) * (1 + card.output_bonus_percent / 100)
            return f"+{amount:.0f}/cycle"
        if isinstance(definition, EnergyDefinition):
            return f"+{definition.base_power_output:.0f} MW"
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

    def _result_grid_side_margin(self, columns: int, item_count: int | None = None) -> int:
        width = self._result_grid_available_width()
        visible_columns = max(1, min(columns, item_count if item_count is not None else columns))
        used = visible_columns * PACK_RESULT_CARD_WIDTH + max(0, visible_columns - 1) * PACK_RESULT_GRID_SPACING
        return max(0, (width - used) // 2)

    def _result_grid_available_width(self) -> int:
        if not hasattr(self, "_result_scroll"):
            return self.width()
        return self._result_scroll.viewport().width() - self._result_scroll.verticalScrollBar().sizeHint().width()

    def _show_result_hover(self, card: CardInstance, source: QWidget) -> None:
        if not source.isVisible():
            return
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
        if self._flow_state != "idle":
            return
        pack = next((p for p in self._state.packs.unopened if p.pack_id == pack_id), None)
        if pack is None:
            return
        self._flow_state = "opening"
        try:
            self._bus.dispatch(OpenPack(pack_id, self._definitions, category_id))
        except Exception:
            self._flow_state = "idle"
            raise
        # OpenPack commits exactly once. Confirm only acknowledges this snapshot.
        self._active_cards = tuple(self._state.packs.last_opened_cards)
        self._hide_result_hover()
        self._confirm.hide()
        for card in self._active_cards:
            tile = RevealCard(self._result_card_tile(card), card.rarity.value, self._result_container)
            tile.revealed.connect(self._on_card_revealed)
            self._reveal_cards.append(tile)
        # Prepare the existing destination before exposing it. No intermediate
        # page/viewport geometry or inherited palette can be painted while switching.
        self._stack.setUpdatesEnabled(False)
        try:
            page = self._stack.widget(1)
            page.setGeometry(self._stack.contentsRect())
            page.layout().activate()
            self._refresh_results(force=True)
            self._focus.setGeometry(self._result_scroll.viewport().rect())
            self._focus.start(len(self._active_cards))
            self._stack.setCurrentIndex(1)
            page.layout().activate()
            self.refresh()
        finally:
            self._stack.setUpdatesEnabled(True)
        self._deal_index = 0
        self._deal_timer.start(OPENING_TOTAL_MS)
        if self._on_state_changed is not None:
            self._on_state_changed()

    def _deal_next(self) -> None:
        self._focus.hide()
        self._flow_state = "dealing"
        self._reveal_cards[self._deal_index].deal()
        self._deal_index += 1
        if self._deal_index == len(self._reveal_cards):
            self._deal_timer.stop()
            self._flow_state = "partially_revealed" if any(c.is_revealed for c in self._reveal_cards) else "cards_dealt"
        else:
            self._deal_timer.setInterval(100)

    def _on_card_revealed(self) -> None:
        if all(card.is_revealed for card in self._reveal_cards):
            self._flow_state = "ready_to_confirm"
            self._confirm.show()
        elif not self._deal_timer.isActive():
            self._flow_state = "partially_revealed"

    def _confirm_collect(self) -> None:
        if self._flow_state != "ready_to_confirm":
            return
        self._flow_state = "confirmed"
        self._hide_result_hover()
        self._confirm.hide()
        self._clear_layout(self._result_grid)
        self._reveal_cards.clear()
        self._active_cards = ()
        self._stack.setCurrentIndex(0)
        self._flow_state = "idle"
        self._refresh_pack_grid()

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
        return definition.card_kind.value.title()

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)

    def _card_type_key(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value
        if isinstance(definition, EnergyDefinition):
            return "energy"
        if isinstance(definition, FreightDefinition):
            return "freight"
        return "card"

    def _card_function_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.name
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.title()
        return "Card"

    def _icon_signature(self, card: CardInstance, definition: CardDefinition) -> tuple[str, str, str]:
        return card_resource_icon_signature(definition, card.definition_id)

    def _primary_stat(self, card: CardInstance, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return f"{definition.base_output_per_tick * card.output_multiplier:g} out"
        if isinstance(definition, EnergyDefinition):
            return f"{definition.base_power_output * card.output_multiplier:g} MW"
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"{stats.capacity:g} cap"
        return "-"

    def _hover_sections(self, card: CardInstance, definition: CardDefinition) -> list[tuple[str, str]]:
        sections = [
            ("Rarity", card.rarity.value.title()),
            ("Type", self._card_function_label(definition)),
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
                        ("Consumption", f"{definition.fuel_consumption_per_cycle:g}/cycle"),
                    ]
                )
            return tuple(pairs)
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
