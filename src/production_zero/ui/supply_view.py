from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.cards import create_card_instance, effective_recipe_inputs, effective_recipe_outputs
from production_zero.core.commands import BuyCommonSupplyCard, BuyDailyFreightSupplyCard, BuyDailyMachineSupplyCard, BuyDailyUncommonSupplyCard, CommandBus
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.state import GameState
from production_zero.core.supply import SupplyOffer, common_supply_offers, refresh_supply, seconds_until_supply_daily_reset
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.ui.factory_view_v2 import _display_card_title, prototype_family_for_definition
from production_zero.ui.game_ui.rendering import draw_machine_card_prototype
from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.text_format import smart_card_title
from production_zero.ui.widget_lifecycle import clear_layout_safely, hide_detach_delete


COMMON_SUPPLY_CARD_WIDTH = 208
COMMON_SUPPLY_CARD_HEIGHT = 276
FEATURED_SUPPLY_CARD_WIDTH = 208
FEATURED_SUPPLY_CARD_HEIGHT = 276
SUPPLY_GRID_SPACING = 12
COMMON_SUPPLY_BUFFER_ROWS = 2
COMMON_SUPPLY_SEARCH_DEBOUNCE_MS = 180
COMMON_SUPPLY_HOVER_DELAY_MS = 300
COMMON_SUPPLY_TITLE_HEIGHT = 38
COMMON_SUPPLY_HEADER_HEIGHT = 64


@dataclass(frozen=True, slots=True)
class CommonSupplyCardDisplayData:
    offer: SupplyOffer
    definition: CardDefinition
    definition_id: str
    offer_id: str
    name: str
    type_label: str
    secondary_label: str
    rarity_label: str
    rarity_key: str
    bonus_text: str
    primary_text: str
    secondary_text: str
    price_text: str
    icon_resource_id: str
    icon_key: str
    accent_key: str
    search_text: str


class TwoLineSupplyTitleLabel(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(COMMON_SUPPLY_TITLE_HEIGHT)
        self.setWordWrap(False)
        self._first_line_reserved_width = 0

    def set_first_line_reserved_width(self, width: int) -> None:
        self._first_line_reserved_width = max(0, width)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setFont(self.font())
            painter.setPen(self.palette().color(self.foregroundRole()))
            metrics = self.fontMetrics()
            lines = self._title_lines(metrics, max(1, self.width()))
            line_height = self.height() / 2
            for index, line in enumerate(lines[:2]):
                rect = self.rect()
                rect.setTop(round(index * line_height))
                rect.setHeight(round(line_height))
                if index == 0 and self._first_line_reserved_width:
                    rect.setRight(max(rect.left(), rect.right() - self._first_line_reserved_width))
                painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)
        finally:
            painter.end()

    def _title_lines(self, metrics, width: int) -> list[str]:
        text = str(self.property("displayText") or self.text()).strip()
        if not text:
            return []
        first_width = max(1, width - self._first_line_reserved_width)
        preferred = smart_card_title(text).splitlines()
        if len(preferred) == 2:
            first = metrics.elidedText(preferred[0], Qt.TextElideMode.ElideRight, first_width)
            second = metrics.elidedText(preferred[1], Qt.TextElideMode.ElideRight, width)
            return [line for line in (first, second) if line]
        if metrics.horizontalAdvance(text) <= first_width:
            return [text]
        words = text.split()
        first_words: list[str] = []
        remaining = words[:]
        while remaining:
            candidate_words = [*first_words, remaining[0]]
            candidate = " ".join(candidate_words)
            if first_words and metrics.horizontalAdvance(candidate) > first_width:
                break
            first_words.append(remaining.pop(0))
            if metrics.horizontalAdvance(" ".join(first_words)) > first_width:
                first = metrics.elidedText(" ".join(first_words), Qt.TextElideMode.ElideRight, first_width)
                return [first]
        first = " ".join(first_words) if first_words else metrics.elidedText(words[0], Qt.TextElideMode.ElideRight, first_width)
        second_source = " ".join(remaining)
        second = ""
        if second_source:
            second = metrics.elidedText(second_source, Qt.TextElideMode.ElideRight, width)
            for start in range(1, len(remaining)):
                suffix = " ".join(remaining[start:])
                if len(suffix.split()) >= 2 and metrics.horizontalAdvance(suffix) <= width:
                    second = suffix
                    break
        return [line for line in (first, second) if line]


class SupplyOfferCardFrame(QFrame):
    """Shared modern card chassis with a compact Supply price/action footer."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._supply_data: CommonSupplyCardDisplayData | None = None
        self._source = "common"
        self._state = "available"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._name_label = self._hidden_label("supplyCardName")
        self._rarity_label = self._hidden_label("supplyCardRarity")
        self._mk_label = self._hidden_label("supplyCardMk")
        self._bonus_label = self._hidden_label("supplyCardBonus")
        self._function_label = self._hidden_label("supplyCardFunction")
        self._primary_label = self._hidden_label("supplyCardOutput")
        self._secondary_label = self._hidden_label("supplyCardPower")
        self._rarity_line = QFrame(self)
        self._rarity_line.setObjectName("supplyRarityLine")
        self._rarity_line.hide()
        self._icon_widget: ResourceIconWidget | None = None

        self._price_label = QLabel(self)
        self._price_label.setObjectName("supplyCardPrice")
        self._price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._price_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._price_label.setAutoFillBackground(False)

        self._buy_button = QPushButton("BUY", self)
        self._buy_button.setObjectName("buyCommonSupplyButton")
        self._buy_button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _hidden_label(self, object_name: str) -> QLabel:
        label = QLabel(self)
        label.setObjectName(object_name)
        label.setAutoFillBackground(False)
        label.hide()
        return label

    def bind_offer(
        self,
        data: CommonSupplyCardDisplayData,
        *,
        source: str,
        state: str,
        button_text: str,
        can_buy: bool,
    ) -> None:
        self._supply_data = data
        self._source = source
        self._state = state
        self.setProperty("state", state)
        self.setProperty("source", source)
        self.setProperty("cardKind", data.definition.card_kind.value)
        self.setProperty("definitionId", data.definition_id)
        self.setProperty("offerId", data.offer_id)
        self._name_label.setText(data.name)
        self._name_label.setProperty("displayText", _display_card_title(data.definition))
        self._rarity_label.setText(data.rarity_label)
        self._rarity_line.setProperty("rarity", data.rarity_key)
        self._mk_label.setText(data.secondary_label)
        self._bonus_label.setText(data.bonus_text)
        self._function_label.setText(data.type_label.upper())
        self._primary_label.setText(data.primary_text)
        self._secondary_label.setText(data.secondary_text)
        self._secondary_label.setVisible(False)
        self._price_label.setText(data.price_text)
        self._buy_button.setText(button_text.upper())
        self._buy_button.setEnabled(can_buy)
        self._sync_hidden_icon(data)
        self._position_footer()
        self.update()

    def _sync_hidden_icon(self, data: CommonSupplyCardDisplayData) -> None:
        if self._icon_widget is not None:
            self._icon_widget.setParent(None)
            self._icon_widget.deleteLater()
        self._icon_widget = ResourceIconWidget(data.icon_resource_id, data.icon_key, data.accent_key, size=1)
        self._icon_widget.setParent(self)
        self._icon_widget.setObjectName("supplyCardIcon")
        self._icon_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._icon_widget.hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_footer()

    def _position_footer(self) -> None:
        rect = QRectF(3, 3, max(1, self.width() - 6), max(1, self.height() - 6))
        footer_top = int(rect.bottom() - 38)
        self._price_label.setGeometry(int(rect.left() + 13), footer_top + 4, 58, 26)
        self._buy_button.setGeometry(int(rect.right() - 120), footer_top + 4, 106, 26)

    def paintEvent(self, event) -> None:  # noqa: N802
        data = self._supply_data
        if data is None:
            return
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.rect()).adjusted(3, 3, -3, -3)
            draw_machine_card_prototype(
                painter,
                rect,
                title=_display_card_title(data.definition),
                family=prototype_family_for_definition(data.definition),
                meta=f"{data.secondary_label} · {data.rarity_label.upper()}",
                detail=self._detail_text(data),
                secondary=self._secondary_text(data),
                disabled=self._state == "locked",
                active=self._state == "purchased",
                hover=self.underMouse(),
            )
            self._draw_supply_footer(painter, rect)
        finally:
            painter.end()
        super().paintEvent(event)

    def _detail_text(self, data: CommonSupplyCardDisplayData) -> str:
        text = data.primary_text
        for prefix in ("Output: ", "Generation "):
            if text.startswith(prefix):
                text = text[len(prefix) :]
        return text.upper()

    def _secondary_text(self, data: CommonSupplyCardDisplayData) -> str:
        text = data.secondary_text or data.type_label
        for prefix in ("Power Demand ", "Transport Time ", "Fuel "):
            if text.startswith(prefix):
                text = text[len(prefix) :]
        return text.upper()

    def _draw_supply_footer(self, painter: QPainter, rect: QRectF) -> None:
        footer = QRectF(rect.left() + 10, rect.bottom() - 43, rect.width() - 20, 34)
        body = QLinearGradient(footer.topLeft(), footer.bottomLeft())
        body.setColorAt(0.0, QColor(255, 255, 255, 18))
        body.setColorAt(0.45, QColor(7, 10, 10, 168))
        body.setColorAt(1.0, QColor(0, 0, 0, 128))
        painter.setPen(QPen(QColor(246, 244, 229, 34), 1))
        painter.setBrush(body)
        painter.drawRoundedRect(footer, 7, 7)

        font = GAME_UI_TOKENS.typography.micro_label()
        font.setPointSize(6)
        font.setWeight(font.Weight.Black)
        painter.setFont(font)
        painter.setPen(QColor("#82928d"))
        painter.drawText(footer.adjusted(10, 1, -126, -16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "PRICE")


class SupplyView(QWidget):
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
        self._common_offers: tuple[SupplyOffer, ...] = ()
        self._common_grid_columns_used = 0
        self._common_grid_rows_used = 0
        self._common_display_cache: dict[tuple[str, str, int, float], CommonSupplyCardDisplayData] = {}
        self._common_display_data: list[CommonSupplyCardDisplayData] = []
        self._filtered_common_data: list[CommonSupplyCardDisplayData] = []
        self._common_card_pool: list[QFrame] = []
        self._common_card_bindings: dict[QFrame, int] = {}
        self._common_visible_indexes: set[int] = set()
        self._common_last_scroll_value = 0
        self._common_last_viewport_height = 0
        self._common_filter_apply_count = 0
        self._common_reflow_count = 0
        self._common_performance = {
            "initial_ms": 0.0,
            "filter_ms": 0.0,
            "visible_update_ms": 0.0,
            "pool_size": 0,
        }
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(COMMON_SUPPLY_SEARCH_DEBOUNCE_MS)
        self._search_debounce.timeout.connect(self._apply_common_filter)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(COMMON_SUPPLY_HOVER_DELAY_MS)
        self._hover_timer.timeout.connect(self._show_common_hover_for_current_card)
        self._hover_card: QFrame | None = None
        self._hover_popup: CardHoverInfoPopup | None = None
        self._filter_chip_groups: dict[QComboBox, QHBoxLayout] = {}
        self._selector_buttons: dict[QComboBox, QPushButton] = {}
        self._selector_flyouts: dict[QComboBox, QFrame] = {}
        self._header_metric_values: dict[str, QLabel] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addWidget(self._build_store_header())
        layout.addWidget(self._build_section_selector())

        self._stack = QStackedWidget()
        self._stack.setObjectName("supplySectionStack")
        self._daily_page = self._build_daily_page()
        self._common_page = self._build_common_page()
        self._stack.addWidget(self._daily_page)
        self._stack.addWidget(self._common_page)
        self._stack.currentChanged.connect(self._sync_section_buttons)
        layout.addWidget(self._stack, 1)

        self.refresh()
        self._show_section(0)

    def refresh(self) -> None:
        refresh_supply(self._state, self._definitions)
        self._common_offers = common_supply_offers(self._definitions)
        start = perf_counter()
        self._common_display_data = [self._display_data_for_offer(offer) for offer in self._common_offers]
        self._common_performance["initial_ms"] = (perf_counter() - start) * 1000
        self._refresh_store_header_metrics()
        self._refresh_daily_cards()
        self._refresh_freight_daily_cards()
        self._refresh_machine_daily_cards()
        self._refresh_common_filters()
        self._apply_common_filter()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if (
            hasattr(self, "_common_scroll")
            and watched is self._common_scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            columns = self._common_grid_columns()
            viewport_height = self._common_scroll.viewport().height()
            if self._stack.currentWidget() is self._common_page and (
                columns != self._common_grid_columns_used
                or abs(viewport_height - self._common_last_viewport_height) >= COMMON_SUPPLY_CARD_HEIGHT
            ):
                self._layout_common_virtual_grid(columns)
                self._update_common_visible_cards()
        elif event.type() == QEvent.Type.Enter and watched in self._common_card_pool:
            self._schedule_common_hover(watched)
        elif event.type() == QEvent.Type.Leave and watched in self._common_card_pool:
            self._hide_common_hover(watched)
        return super().eventFilter(watched, event)

    def _build_store_header(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("supplyStoreHeader")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)
        icon = ResourceIconWidget("industrial_supply", "package", "steel", size=42)
        icon.setObjectName("supplyStoreIcon")
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel("INDUSTRIAL SUPPLY")
        title.setObjectName("supplyStoreTitle")
        subtitle = QLabel("Procurement · Daily Rotations · Permanent Supply")
        subtitle.setObjectName("supplyStoreSubtitle")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        layout.addWidget(icon)
        layout.addLayout(title_wrap, 1)
        for metric_key, label, value in (
            ("daily_reset", "DAILY RESET", self._format_duration(seconds_until_supply_daily_reset(self._state)).upper()),
            ("available", "AVAILABLE", str(len(common_supply_offers(self._definitions)))),
        ):
            module = QFrame()
            module.setObjectName("supplyHeaderMetric")
            module_layout = QVBoxLayout(module)
            module_layout.setContentsMargins(12, 8, 12, 8)
            module_layout.setSpacing(2)
            metric_label = QLabel(label)
            metric_label.setObjectName("supplyHeaderMetricLabel")
            metric_value = QLabel(value)
            metric_value.setObjectName("supplyHeaderMetricValue")
            module_layout.addWidget(metric_label)
            module_layout.addWidget(metric_value)
            self._header_metric_values[metric_key] = metric_value
            layout.addWidget(module)
        return panel

    def _refresh_store_header_metrics(self) -> None:
        if not self._header_metric_values:
            return
        available = (
            len(self._common_offers)
            + len(self._state.supply.daily_offers)
            + len(self._state.supply.freight_daily_offers)
            + len(self._state.supply.machine_daily_offers)
        )
        self._header_metric_values["daily_reset"].setText(self._format_duration(seconds_until_supply_daily_reset(self._state)).upper())
        self._header_metric_values["available"].setText(f"{available:,}")

    def _build_section_selector(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("supplySectionSelector")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self._section_buttons: list[QPushButton] = []
        for index, label in enumerate(("DAILY SUPPLY", "COMMON SUPPLY")):
            button = QPushButton(label)
            button.setObjectName("supplySectionButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=index: self._show_section(page))
            layout.addWidget(button)
            self._section_buttons.append(button)
        layout.addStretch(1)
        return panel

    def _build_daily_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("supplyDailyPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section_header("DAILY SUPPLY", "Daily procurement rotation", "supplyDailyStatus"))

        scroll = QScrollArea()
        scroll.setObjectName("supplyDailyScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("supplyDailyContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        recipe_section, self._daily_grid = self._daily_offer_section("DAILY RECIPES", "supplyDailyRecipeSection")
        freight_section, self._freight_daily_grid = self._daily_offer_section("DAILY FREIGHT", "supplyDailyFreightSection")
        machine_section, self._machine_daily_grid = self._daily_offer_section("DAILY MACHINES", "supplyDailyMachineSection")
        content_layout.addWidget(recipe_section)
        content_layout.addWidget(freight_section)
        content_layout.addWidget(machine_section)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return page

    def _daily_offer_section(self, title_text: str, object_name: str) -> tuple[QFrame, QGridLayout]:
        section = QFrame()
        section.setObjectName(object_name)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(1)
        title = QLabel(title_text)
        title.setObjectName("supplyDailySectionTitle")
        subtitle = QLabel("CHOOSE 1 OF 3")
        subtitle.setObjectName("supplyDailySectionSubtitle")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        layout.addLayout(grid)
        return section, grid

    def _build_common_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("supplyCommonPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section_header("COMMON SUPPLY", "Always available", "supplyCommonStatus"))

        toolbar = QFrame()
        toolbar.setObjectName("supplyToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        toolbar_layout.setSpacing(10)
        self._search = QLineEdit()
        self._search.setObjectName("supplySearch")
        self._search.setPlaceholderText("Search cards...")
        self._search.textChanged.connect(self._schedule_common_filter)
        self._type_filter = QComboBox(toolbar)
        self._type_filter.setObjectName("supplyTypeFilter")
        self._type_filter.hide()
        self._type_filter.currentTextChanged.connect(self._on_common_type_changed)
        self._mk_filter = QComboBox(toolbar)
        self._mk_filter.setObjectName("supplyMkFilter")
        self._mk_filter.hide()
        self._mk_filter.currentTextChanged.connect(self._apply_common_filter)
        self._sort = QComboBox(toolbar)
        self._sort.setObjectName("supplySortSelect")
        self._sort.addItems(["Name", "Price"])
        self._sort.hide()
        self._sort.currentTextChanged.connect(self._apply_common_filter)
        toolbar_layout.addWidget(self._labeled_control("SEARCH", self._search), 2)
        self._type_chip_layout = self._add_chip_group(toolbar_layout, "TYPE", self._type_filter)
        self._add_selector_group(toolbar_layout, "MACHINE / CLASS", self._mk_filter, "supplyMachineSelector")
        self._add_selector_group(toolbar_layout, "SORT", self._sort, "supplySortSelector")
        toolbar_layout.addStretch(1)
        layout.addWidget(toolbar)

        self._common_scroll = QScrollArea()
        self._common_scroll.setObjectName("commonSupplyScroll")
        self._common_scroll.setWidgetResizable(False)
        self._common_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._common_scroll.viewport().installEventFilter(self)
        self._common_scroll.verticalScrollBar().valueChanged.connect(self._update_common_visible_cards)
        self._common_grid_container = QWidget()
        self._common_grid_container.setObjectName("commonSupplyGrid")
        self._common_grid_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._common_scroll.setWidget(self._common_grid_container)
        layout.addWidget(self._common_scroll, 1)
        return page

    def _section_header(self, title_text: str, subtitle_text: str, status_object_name: str) -> QFrame:
        header = QFrame()
        header.setObjectName("supplySectionHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)
        title_wrap = QVBoxLayout()
        title_wrap.setSpacing(2)
        title = QLabel(title_text)
        title.setObjectName("supplySectionTitle")
        subtitle = QLabel(subtitle_text.upper())
        subtitle.setObjectName("supplySectionSubtitle")
        status = QLabel()
        status.setObjectName(status_object_name)
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        layout.addLayout(title_wrap, 1)
        layout.addWidget(status)
        if status_object_name == "supplyDailyStatus":
            self._daily_label = status
        elif status_object_name == "supplyFreightDailyStatus":
            self._freight_daily_label = status
        else:
            self._common_status_label = status
        return header

    def _show_section(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._sync_section_buttons(index)
        if self._stack.currentWidget() is self._common_page:
            self._layout_common_virtual_grid()
            self._update_common_visible_cards()
        self._hide_detail_overlay()
        self._hide_common_hover()

    def _sync_section_buttons(self, index: int) -> None:
        for button_index, button in enumerate(self._section_buttons):
            button.blockSignals(True)
            button.setChecked(button_index == index)
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
            button.blockSignals(False)

    def _refresh_common_filters(self) -> None:
        type_options = sorted({data.type_label for data in self._common_display_data})
        self._set_options(self._type_filter, type_options)
        if not self._type_filter.currentText() and type_options:
            self._type_filter.setCurrentText(type_options[0])
        self._refresh_common_secondary_filter()
        self._refresh_filter_widgets()

    def _refresh_common_secondary_filter(self) -> None:
        selected_type = self._type_filter.currentText()
        labels = sorted({data.secondary_label for data in self._common_display_data if data.type_label == selected_type})
        self._set_options(self._mk_filter, ["All", *labels])
        self._rebuild_selector_flyout(self._mk_filter)

    def _set_options(self, combo: QComboBox, options: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        if current in options:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _refresh_daily_cards(self) -> None:
        remaining = self._format_duration(seconds_until_supply_daily_reset(self._state))
        self._daily_label.setText(f"RESET\n{remaining.upper()}")
        self._clear_layout(self._daily_grid)
        for index, offer in enumerate(self._state.supply.daily_offers):
            card = self._supply_card(offer, "daily")
            self._daily_grid.addWidget(card, 0, index, Qt.AlignmentFlag.AlignHCenter)
            card.show()
            self._daily_grid.setColumnStretch(index, 1)

    def _refresh_freight_daily_cards(self) -> None:
        self._clear_layout(self._freight_daily_grid)
        for index, offer in enumerate(self._state.supply.freight_daily_offers):
            card = self._supply_card(offer, "freight_daily")
            self._freight_daily_grid.addWidget(card, 0, index, Qt.AlignmentFlag.AlignHCenter)
            card.show()
            self._freight_daily_grid.setColumnStretch(index, 1)

    def _refresh_machine_daily_cards(self) -> None:
        self._clear_layout(self._machine_daily_grid)
        for index, offer in enumerate(self._state.supply.machine_daily_offers):
            card = self._supply_card(offer, "machine_daily")
            self._machine_daily_grid.addWidget(card, 0, index, Qt.AlignmentFlag.AlignHCenter)
            card.show()
            self._machine_daily_grid.setColumnStretch(index, 1)

    def _schedule_common_filter(self, *args) -> None:
        self._search_debounce.start()

    def _on_common_type_changed(self, *args) -> None:
        self._refresh_common_secondary_filter()
        self._apply_common_filter()

    def _apply_common_filter(self, *args) -> None:
        if not hasattr(self, "_common_grid_container"):
            return
        start = perf_counter()
        selected_type = self._type_filter.currentText()
        selected_secondary = self._mk_filter.currentText()
        search = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        data = [
            item
            for item in self._common_display_data
            if item.type_label == selected_type
            and selected_secondary in ("", "All", item.secondary_label)
            and (not search or search in item.search_text)
        ]
        self._filtered_common_data = self._sort_display_data(data)
        self._common_status_label.setText(f"{len(self._filtered_common_data):,} cards")
        self._refresh_filter_widgets()
        self._common_filter_apply_count += 1
        self._common_performance["filter_ms"] = (perf_counter() - start) * 1000
        self._common_scroll.verticalScrollBar().setValue(0)
        self._layout_common_virtual_grid()
        self._update_common_visible_cards()

    def _layout_common_virtual_grid(self, columns: int | None = None) -> None:
        columns = columns or self._common_grid_columns()
        rows = (len(self._filtered_common_data) + columns - 1) // columns if self._filtered_common_data else 0
        if columns == self._common_grid_columns_used and rows == self._common_grid_rows_used:
            return
        self._common_grid_columns_used = columns
        self._common_grid_rows_used = rows
        spacing = SUPPLY_GRID_SPACING
        width = self._common_grid_available_width()
        height = rows * COMMON_SUPPLY_CARD_HEIGHT + max(0, rows - 1) * spacing
        self._common_grid_container.setMinimumSize(width, height)
        self._common_grid_container.resize(width, height)
        self._common_reflow_count += 1
        self._common_visible_indexes = set()
        self._common_card_bindings = {}

    def _update_common_visible_cards(self, *args) -> None:
        if not hasattr(self, "_common_scroll"):
            return
        start = perf_counter()
        if not self._filtered_common_data:
            self._hide_common_card_pool()
            self._hide_common_hover()
            self._common_performance["visible_update_ms"] = (perf_counter() - start) * 1000
            return
        columns = max(1, self._common_grid_columns_used or self._common_grid_columns())
        row_pitch = COMMON_SUPPLY_CARD_HEIGHT + SUPPLY_GRID_SPACING
        scroll_y = self._common_scroll.verticalScrollBar().value()
        viewport_height = self._common_scroll.viewport().height()
        first_row = max(0, scroll_y // row_pitch - COMMON_SUPPLY_BUFFER_ROWS)
        last_row = min(
            max(0, self._common_grid_rows_used - 1),
            (scroll_y + viewport_height) // row_pitch + COMMON_SUPPLY_BUFFER_ROWS,
        )
        indexes = [
            index
            for row in range(first_row, last_row + 1)
            for column in range(columns)
            for index in (row * columns + column,)
            if index < len(self._filtered_common_data)
        ]
        self._ensure_common_card_pool(len(indexes))
        active_cards = set()
        for pool_index, data_index in enumerate(indexes):
            card = self._common_card_pool[pool_index]
            self._bind_common_card_widget(card, data_index)
            row = data_index // columns
            column = data_index % columns
            x = column * (COMMON_SUPPLY_CARD_WIDTH + SUPPLY_GRID_SPACING)
            y = row * row_pitch
            card.move(x, y)
            card.show()
            active_cards.add(card)
            self._common_card_bindings[card] = data_index
        for card in self._common_card_pool:
            if card not in active_cards:
                if card is self._hover_card:
                    self._hide_common_hover(card)
                card.hide()
                self._common_card_bindings.pop(card, None)
        self._common_visible_indexes = set(indexes)
        self._common_last_scroll_value = scroll_y
        self._common_last_viewport_height = viewport_height
        self._common_performance["visible_update_ms"] = (perf_counter() - start) * 1000
        self._common_performance["pool_size"] = len(self._common_card_pool)

    def _ensure_common_card_pool(self, target_count: int) -> None:
        while len(self._common_card_pool) < target_count:
            self._common_card_pool.append(self._create_common_card_widget())

    def _hide_common_card_pool(self) -> None:
        for card in self._common_card_pool:
            card.hide()
        self._common_card_bindings = {}
        self._common_visible_indexes = set()

    def _supply_card(self, offer: SupplyOffer, source: str) -> QFrame:
        data = self._display_data_for_offer(offer)
        state = self._offer_state(offer, source)
        card = SupplyOfferCardFrame()
        card.setObjectName(self._card_object_name(source))
        if source == "common":
            card.setFixedSize(COMMON_SUPPLY_CARD_WIDTH, COMMON_SUPPLY_CARD_HEIGHT)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        else:
            card.setFixedSize(FEATURED_SUPPLY_CARD_WIDTH, FEATURED_SUPPLY_CARD_HEIGHT)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card._buy_button.setObjectName(self._button_object_name(source))  # type: ignore[attr-defined]
        card._buy_button.clicked.connect(lambda checked=False, current_offer=offer, current_source=source: self._buy_offer(current_offer, current_source))  # type: ignore[attr-defined]
        card.bind_offer(
            data,
            source=source,
            state=state,
            button_text=self._button_text(source, state),
            can_buy=self._can_buy(offer, source),
        )
        return card

    def _create_common_card_widget(self) -> QFrame:
        card = SupplyOfferCardFrame(self._common_grid_container)
        card.setObjectName("commonSupplyCard")
        card.setFixedSize(COMMON_SUPPLY_CARD_WIDTH, COMMON_SUPPLY_CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card.installEventFilter(self)
        card._buy_button.clicked.connect(lambda checked=False, widget=card: self._buy_common_from_widget(widget))  # type: ignore[attr-defined]
        card.hide()
        return card

    def _resize_common_card_title_row(self, row: QFrame, title: TwoLineSupplyTitleLabel, rarity: QLabel, event) -> None:
        title.setGeometry(0, 0, row.width(), row.height())
        rarity.setGeometry(max(0, row.width() - rarity.width()), 0, rarity.width(), row.height())

    def _bind_common_card_widget(self, card: QFrame, data_index: int) -> None:
        data = self._filtered_common_data[data_index]
        if getattr(card, "_supply_data", None) == data:
            return
        if self._hover_popup is not None:
            self._hover_popup.details_signature = None
            self._hover_popup.hide()
        if isinstance(card, SupplyOfferCardFrame):
            card.bind_offer(
                data,
                source="common",
                state=self._offer_state(data.offer, "common"),
                button_text="BUY",
                can_buy=self._can_buy(data.offer, "common"),
            )
        if self._hover_card is card:
            self._hover_timer.stop()
            self._hide_common_hover(card)

    def _common_card_title_text(self, data: CommonSupplyCardDisplayData) -> str:
        title = data.name
        suffixes = {data.secondary_label}
        if data.secondary_label.upper().startswith("MK "):
            level = data.secondary_label.split()[-1]
            roman = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V"}.get(level)
            if roman is not None:
                suffixes.add(f"MK {roman}")
        for suffix in sorted(suffixes, key=len, reverse=True):
            marker = f" {suffix}"
            if title.upper().endswith(marker.upper()):
                return title[: -len(marker)]
        return title

    def _replace_common_card_icon(self, card: QFrame, data: CommonSupplyCardDisplayData) -> None:
        layout = card._icon_layout  # type: ignore[attr-defined]
        old_icon = getattr(card, "_icon_widget", None)
        if old_icon is not None:
            layout.removeWidget(old_icon)
            hide_detach_delete(old_icon)
        icon = ResourceIconWidget(data.icon_resource_id, data.icon_key, data.accent_key, size=50)
        icon.setObjectName("supplyCardIcon")
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.insertWidget(1, icon)
        card._icon_widget = icon  # type: ignore[attr-defined]

    def _buy_common_from_widget(self, card: QFrame) -> None:
        data = getattr(card, "_supply_data", None)
        if data is not None:
            self._buy_offer(data.offer, "common")

    def _schedule_common_hover(self, card: QFrame) -> None:
        data = getattr(card, "_supply_data", None)
        if card.isHidden() or data is None:
            return
        if self._hover_popup is not None and self._hover_popup.details_signature is not None:
            previous_offer_id = self._hover_popup.details_signature[0]
            if previous_offer_id != data.offer_id:
                self._hover_popup.details_signature = None
        self._hover_card = card
        self._hover_timer.start()

    def _show_common_hover_for_current_card(self) -> None:
        card = self._hover_card
        if card is None or card.isHidden():
            return
        data = getattr(card, "_supply_data", None)
        if data is None:
            return
        if self._hover_popup is None:
            self._hover_popup = CardHoverInfoPopup(self, object_name="supplyCardHoverInfo", embedded=True)
        sections = self._hover_sections_for_offer(data.offer)
        signature = (
            data.offer_id,
            data.definition_id,
            data.rarity_key,
            data.offer.bonus_tenths,
            data.offer.price_cash,
            tuple(sections),
            data.icon_resource_id,
            data.icon_key,
            data.accent_key,
        )
        if self._hover_popup.details_signature != signature:
            icon = ResourceIconWidget(data.icon_resource_id, data.icon_key, data.accent_key, size=34)
            self._hover_popup.set_details(data.name, icon, sections, signature)
        else:
            self._hover_popup.update_values(sections)
        self._hover_popup.show_for(card)

    def _hide_common_hover(self, card: QFrame | None = None) -> None:
        if card is not None and self._hover_card is not card:
            return
        self._hover_timer.stop()
        self._hover_card = None
        if self._hover_popup is not None:
            self._hover_popup.hide()

    def _stats_panel(self, primary: str, secondary: str) -> QFrame:
        panel = QFrame()
        panel.setObjectName("supplyCardStats")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        primary_label = QLabel(primary)
        primary_label.setObjectName("supplyCardOutput")
        primary_label.setWordWrap(True)
        secondary_label = QLabel(secondary)
        secondary_label.setObjectName("supplyCardPower")
        secondary_label.setWordWrap(True)
        layout.addWidget(primary_label)
        layout.addWidget(secondary_label)
        return panel

    def _hide_detail_overlay(self) -> None:
        self._hide_common_hover()

    def _hover_sections_for_offer(self, offer: SupplyOffer) -> list[tuple[str, str]]:
        definition = self._definitions[offer.definition_id]
        card = create_card_instance(
            "preview",
            offer.definition_id,
            offer.card_kind,
            offer.rarity,
            bonus_tenths=offer.bonus_tenths,
        )
        sections = [
            ("Card Type", self._type_label(definition)),
            ("Tier", self._mk_label(definition)),
            ("Rarity", offer.rarity.value.title()),
            ("Bonus", f"+{offer.bonus_tenths / 10:.1f}%"),
        ]
        if isinstance(definition, RecipeDefinition):
            outputs = effective_recipe_outputs(card, dict(definition.output_resources))
            inputs = effective_recipe_inputs(card, dict(definition.input_resources))
            sections.extend(
                [
                    ("Recipe Type", self._function_label(definition)),
                    ("Outputs", self._resources_text(outputs)),
                    ("Inputs", self._resources_text(inputs)),
                ]
            )
        elif isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            sections.extend(
                [
                    ("Freight Type", definition.family.value.replace("_", " ").title()),
                    ("Capacity", f"{stats.capacity:g}"),
                    ("Transport Time", self._format_short_duration(stats.transport_time_seconds)),
                    ("Facility", definition.facility_name),
                ]
            )
        else:
            primary, secondary = self._effective_values(offer, definition)
            sections.extend([("Primary", primary), ("Secondary", secondary)])
        sections.extend(
            [
                ("Price", f"${offer.price_cash:,.0f}"),
                ("Owned", str(self._owned_count(offer))),
                ("State", self._offer_state(offer, "common").upper()),
            ]
        )
        return sections

    def _display_data_for_offer(self, offer: SupplyOffer) -> CommonSupplyCardDisplayData:
        key = (offer.definition_id, offer.rarity.value, offer.bonus_tenths, offer.price_cash)
        cached = self._common_display_cache.get(key)
        if cached is not None:
            return cached
        definition = self._definitions[offer.definition_id]
        icon_resource_id, icon_key, accent_key = self._icon_signature(definition)
        primary, secondary = self._compact_values(offer, definition)
        data = CommonSupplyCardDisplayData(
            offer=offer,
            definition=definition,
            definition_id=offer.definition_id,
            offer_id=offer.offer_id,
            name=definition.name,
            type_label=self._type_label(definition),
            secondary_label=self._secondary_filter_label(definition),
            rarity_label=offer.rarity.value.title(),
            rarity_key=offer.rarity.value,
            bonus_text=f"+{offer.bonus_tenths / 10:.1f}%",
            primary_text=primary,
            secondary_text=secondary,
            price_text=f"${offer.price_cash:.0f}",
            icon_resource_id=icon_resource_id,
            icon_key=icon_key,
            accent_key=accent_key,
            search_text=f"{definition.name} {offer.definition_id} {self._function_label(definition)} {self._secondary_filter_label(definition)}".lower(),
        )
        self._common_display_cache[key] = data
        return data

    def _sort_display_data(self, data: list[CommonSupplyCardDisplayData]) -> list[CommonSupplyCardDisplayData]:
        if self._sort.currentText() == "Price":
            return sorted(data, key=lambda item: (item.offer.price_cash, item.name))
        return sorted(data, key=lambda item: item.name)

    def _compact_values(self, offer: SupplyOffer, definition: CardDefinition) -> tuple[str, str]:
        if isinstance(definition, RecipeDefinition):
            card = create_card_instance(
                "preview",
                offer.definition_id,
                offer.card_kind,
                offer.rarity,
                bonus_tenths=offer.bonus_tenths,
            )
            outputs = effective_recipe_outputs(card, dict(definition.output_resources))
            return f"Output: {self._elide_text(self._resources_text(outputs), 24)}", ""
        return self._effective_values(offer, definition)

    def _elide_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[: max(0, max_chars - 1)].rstrip()}…"

    def _buy_offer(self, offer: SupplyOffer, source: str) -> None:
        if source == "common":
            self._buy_common(offer.definition_id)
        elif source == "freight_daily":
            self._buy_freight_daily(offer.offer_id)
        elif source == "machine_daily":
            self._buy_machine_daily(offer.offer_id)
        else:
            self._buy_daily(offer.offer_id)

    def _common_grid_columns(self) -> int:
        width = self._common_grid_available_width() if hasattr(self, "_common_scroll") else self.width()
        pitch = COMMON_SUPPLY_CARD_WIDTH + SUPPLY_GRID_SPACING
        return max(1, min(7, width // pitch))

    def _common_grid_available_width(self) -> int:
        if not hasattr(self, "_common_scroll"):
            return max(1, self.width())
        width = self._common_scroll.viewport().width()
        if width <= 0:
            width = 1100
        scrollbar_width = self._common_scroll.verticalScrollBar().sizeHint().width()
        return max(COMMON_SUPPLY_CARD_WIDTH, width - scrollbar_width - 2)

    def _offer_state(self, offer: SupplyOffer, source: str) -> str:
        if source == "daily":
            return self._daily_card_state(offer)
        if source == "freight_daily":
            return self._freight_daily_card_state(offer)
        if source == "machine_daily":
            return self._machine_daily_card_state(offer)
        return "available"

    def _daily_card_state(self, offer: SupplyOffer) -> str:
        if self._state.supply.daily_purchased_period_index != self._state.supply.daily_period_index:
            return "available"
        if self._state.supply.daily_purchased_offer_id == offer.offer_id:
            return "purchased"
        return "locked"

    def _freight_daily_card_state(self, offer: SupplyOffer) -> str:
        if self._state.supply.freight_daily_purchased_period_index != self._state.supply.freight_daily_period_index:
            return "available"
        if self._state.supply.freight_daily_purchased_offer_id == offer.offer_id:
            return "purchased"
        return "locked"

    def _machine_daily_card_state(self, offer: SupplyOffer) -> str:
        if self._state.supply.machine_daily_purchased_period_index != self._state.supply.machine_daily_period_index:
            return "available"
        if self._state.supply.machine_daily_purchased_offer_id == offer.offer_id:
            return "purchased"
        return "locked"

    def _can_buy(self, offer: SupplyOffer, source: str) -> bool:
        if self._state.cash.amount < offer.price_cash:
            return False
        if source == "daily":
            return self._state.supply.daily_purchased_period_index != self._state.supply.daily_period_index
        if source == "freight_daily":
            return self._state.supply.freight_daily_purchased_period_index != self._state.supply.freight_daily_period_index
        if source == "machine_daily":
            return self._state.supply.machine_daily_purchased_period_index != self._state.supply.machine_daily_period_index
        return True

    def _buy_common(self, definition_id: str) -> None:
        self._bus.dispatch(BuyCommonSupplyCard(definition_id, self._definitions))
        self._notify_and_refresh()

    def _buy_daily(self, offer_id: str) -> None:
        self._bus.dispatch(BuyDailyUncommonSupplyCard(offer_id, self._definitions))
        self._notify_and_refresh()

    def _buy_freight_daily(self, offer_id: str) -> None:
        self._bus.dispatch(BuyDailyFreightSupplyCard(offer_id, self._definitions))
        self._notify_and_refresh()

    def _buy_machine_daily(self, offer_id: str) -> None:
        self._bus.dispatch(BuyDailyMachineSupplyCard(offer_id, self._definitions))
        self._notify_and_refresh()

    def _notify_and_refresh(self) -> None:
        if self._on_state_changed is not None:
            self._on_state_changed()
        else:
            self.refresh()

    def _button_text(self, source: str, state: str) -> str:
        if source in {"daily", "freight_daily", "machine_daily"} and state == "purchased":
            return "PURCHASED"
        if source in {"daily", "freight_daily", "machine_daily"} and state == "locked":
            return "LOCKED UNTIL RESET"
        return "Buy" if source == "common" else "Choose"

    def _icon_signature(self, definition: CardDefinition) -> tuple[str, str, str]:
        if isinstance(definition, MachineDefinition):
            production = definition.production_option(definition.default_production_id)
            resource_id = production.output_resource or definition.output_resource
            return (
                resource_id,
                production.icon_key or definition.icon_key or resource_icon_key(resource_id),
                production.accent_key or definition.accent_key or resource_accent_key(resource_id),
            )
        if isinstance(definition, EnergyDefinition):
            return ("power", "battery", "battery")
        if isinstance(definition, RecipeDefinition):
            output_resource = next(iter(definition.output_resources), definition.definition_id)
            return (
                output_resource,
                definition.icon_key or resource_icon_key(output_resource),
                definition.accent_key or resource_accent_key(output_resource),
            )
        if isinstance(definition, FreightDefinition):
            freight_accent = {
                "truck": "truck",
                "train": "rail",
                "ship": "ship",
                "aircraft": "aircraft",
            }.get(definition.family.value, resource_accent_key(definition.name))
            return (
                definition.definition_id,
                resource_icon_key(definition.name),
                freight_accent,
            )
        return (definition.definition_id, resource_icon_key(definition.definition_id), resource_accent_key(definition.definition_id))

    def _function_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.machine_type.value.title()
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, RecipeDefinition):
            return f"{definition.stage.value.title()} Recipe"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.replace("_", " ").title()
        return definition.card_kind.value.title()

    def _owned_count(self, offer: SupplyOffer) -> int:
        return sum(
            stack.quantity
            for stack in self._state.inventory_card_stacks()
            if stack.first_card.definition_id == offer.definition_id
            and stack.first_card.rarity == offer.rarity
            and stack.first_card.output_bonus_tenths == offer.bonus_tenths
        )

    def _labeled_control(self, label_text: str, control: QWidget) -> QWidget:
        wrapper = QWidget()
        wrapper.setObjectName("supplyFilterGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        layout.addWidget(control)
        return wrapper

    def _add_chip_group(self, parent_layout: QHBoxLayout, label_text: str, combo: QComboBox) -> QHBoxLayout:
        wrapper = QWidget()
        wrapper.setObjectName("supplyFilterGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        chips = QHBoxLayout()
        chips.setContentsMargins(0, 0, 0, 0)
        chips.setSpacing(5)
        layout.addWidget(label)
        layout.addLayout(chips)
        parent_layout.addWidget(wrapper)
        self._filter_chip_groups[combo] = chips
        return chips

    def _add_selector_group(self, parent_layout: QHBoxLayout, label_text: str, combo: QComboBox, object_name: str) -> None:
        wrapper = QWidget()
        wrapper.setObjectName("supplyFilterGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        button = QPushButton(self._selector_text(combo))
        button.setObjectName(object_name)
        button.setProperty("selectorFor", combo.objectName())
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumWidth(112)
        button.clicked.connect(lambda checked=False, target=combo, anchor=button: self._toggle_selector_flyout(target, anchor))
        layout.addWidget(label)
        layout.addWidget(button)
        parent_layout.addWidget(wrapper)
        self._selector_buttons[combo] = button
        self._selector_flyouts[combo] = self._build_selector_flyout(combo, button)

    def _build_selector_flyout(self, combo: QComboBox, anchor: QPushButton) -> QFrame:
        flyout = QFrame(self)
        flyout.setObjectName("supplySelectorFlyout")
        flyout.setProperty("selectorFor", combo.objectName())
        flyout.hide()
        layout = QVBoxLayout(flyout)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self._populate_selector_flyout(combo, flyout)
        return flyout

    def _rebuild_selector_flyout(self, combo: QComboBox) -> None:
        flyout = self._selector_flyouts.get(combo)
        if flyout is None:
            return
        self._clear_layout(flyout.layout())
        self._populate_selector_flyout(combo, flyout)
        flyout.adjustSize()

    def _populate_selector_flyout(self, combo: QComboBox, flyout: QFrame) -> None:
        layout = flyout.layout()
        if layout is None:
            return
        for option in [combo.itemText(index) for index in range(combo.count())]:
            item = QPushButton(option.upper())
            item.setObjectName("supplySelectorOption")
            item.setProperty("filterGroup", combo.objectName())
            item.setProperty("filterValue", option)
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            item.clicked.connect(lambda checked=False, value=option, target=combo: self._select_flyout_value(target, value))
            layout.addWidget(item)

    def _toggle_selector_flyout(self, combo: QComboBox, anchor: QPushButton) -> None:
        flyout = self._selector_flyouts[combo]
        if flyout.isVisible():
            flyout.hide()
            return
        for other in self._selector_flyouts.values():
            other.hide()
        self._refresh_selector_flyout(combo)
        flyout.move(anchor.mapTo(self, QPoint(0, anchor.height() + 4)))
        flyout.resize(max(anchor.width(), flyout.sizeHint().width()), flyout.sizeHint().height())
        flyout.raise_()
        flyout.show()

    def _select_flyout_value(self, combo: QComboBox, value: str) -> None:
        self._set_filter_value(combo, value)
        if combo in self._selector_flyouts:
            self._selector_flyouts[combo].hide()

    def _selector_text(self, combo: QComboBox) -> str:
        return f"{(combo.currentText() or 'All').upper()} >"

    def _refresh_filter_widgets(self) -> None:
        if hasattr(self, "_type_chip_layout"):
            self._refresh_chip_group(self._type_chip_layout, self._type_filter, "type")
        for combo, button in self._selector_buttons.items():
            button.setText(self._selector_text(combo))
            button.style().unpolish(button)
            button.style().polish(button)
            self._refresh_selector_flyout(combo)

    def _refresh_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        self._clear_layout(layout)
        current = combo.currentText()
        for option in [combo.itemText(index) for index in range(combo.count())]:
            chip = QPushButton(option.upper())
            chip.setObjectName("supplyFilterChip")
            chip.setProperty("filterGroup", group)
            chip.setProperty("filterValue", option)
            chip.setProperty("active", option == current)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, value=option, target=combo: self._set_filter_value(target, value))
            layout.addWidget(chip)

    def _set_filter_value(self, combo: QComboBox, value: str) -> None:
        if combo.currentText() == value:
            return
        combo.setCurrentText(value)
        self._refresh_filter_widgets()

    def _refresh_selector_flyout(self, combo: QComboBox) -> None:
        flyout = self._selector_flyouts.get(combo)
        if flyout is None:
            return
        current = combo.currentText()
        for button in flyout.findChildren(QPushButton, "supplySelectorOption"):
            button.setProperty("active", button.property("filterValue") == current)
            button.style().unpolish(button)
            button.style().polish(button)

    def _effective_values(self, offer: SupplyOffer, definition: CardDefinition) -> tuple[str, str]:
        card = create_card_instance(
            "preview",
            offer.definition_id,
            offer.card_kind,
            offer.rarity,
            bonus_tenths=offer.bonus_tenths,
        )
        if isinstance(definition, MachineDefinition):
            output = f"Output {definition.base_output_per_tick * card.output_multiplier:g}"
            power_or_inputs = f"Power Demand {definition.base_power_draw * card.power_multiplier:g} MW"
            return output, power_or_inputs
        if isinstance(definition, EnergyDefinition):
            if definition.requires_fuel and definition.fuel_resource_id is not None:
                fuel = definition.fuel_resource_id.replace("_", " ").title()
                return (
                    f"Generation {definition.base_power_output * card.output_multiplier:g} MW",
                    f"Fuel {fuel} {definition.fuel_consumption_per_minute:g}/min",
                )
            return f"Generation {definition.base_power_output * card.output_multiplier:g} MW", "No Fuel Required"
        if isinstance(definition, RecipeDefinition):
            output = f"Recipe Output {self._resources_text(effective_recipe_outputs(card, dict(definition.output_resources)))}"
            inputs = f"Recipe Inputs {self._resources_text(effective_recipe_inputs(card, dict(definition.input_resources)))}"
            return output, inputs
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"Transport Capacity {stats.capacity:g}", f"Transport Time {self._format_short_duration(stats.transport_time_seconds)}"
        return "-", "-"

    def _type_label(self, definition: CardDefinition) -> str:
        return definition.card_kind.value.title()

    def _secondary_filter_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, RecipeDefinition):
            return definition.stage.value.title()
        return self._mk_label(definition)

    def _mk_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, FreightDefinition):
            return definition.class_label
        level = self._mk_level(definition)
        return "-" if level == 0 else f"MK {level}"

    def _mk_level(self, definition: CardDefinition) -> int:
        if isinstance(definition, FreightDefinition):
            return definition.class_level
        return int(getattr(definition, "mk_level", 0))

    def _format_duration(self, seconds: float) -> str:
        total_minutes = int(seconds // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h {minutes}m"

    def _format_short_duration(self, seconds: float) -> str:
        total_seconds = int(round(seconds))
        minutes, remaining_seconds = divmod(total_seconds, 60)
        if minutes:
            return f"{minutes}m {remaining_seconds:02d}s"
        return f"{remaining_seconds}s"

    def _card_object_name(self, source: str) -> str:
        if source == "daily":
            return "dailySupplyCard"
        if source == "freight_daily":
            return "dailyFreightSupplyCard"
        if source == "machine_daily":
            return "dailyMachineSupplyCard"
        return "commonSupplyCard"

    def _button_object_name(self, source: str) -> str:
        if source == "daily":
            return "buyDailySupplyButton"
        if source == "freight_daily":
            return "buyDailyFreightSupplyButton"
        if source == "machine_daily":
            return "buyDailyMachineSupplyButton"
        return "buyCommonSupplyButton"

    def _resources_text(self, resources: dict[str, float]) -> str:
        return ", ".join(
            f"{amount:g} {resource_id.replace('_', ' ').title()}"
            for resource_id, amount in resources.items()
        )

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
