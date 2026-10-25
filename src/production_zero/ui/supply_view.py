from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QRectF, QTimer, Qt
from PySide6.QtGui import QFont, QFontMetrics, QColor, QLinearGradient, QPainter, QPen
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

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import BuyCommonSupplyCard, BuyDailyFreightSupplyCard, BuyDailyMachineSupplyCard, CommandBus
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.freight import freight_stats
from production_zero.core.state import GameState
from production_zero.core.supply import SupplyOffer, common_supply_offers, refresh_supply, seconds_until_supply_daily_reset
from production_zero.ui.card_hover import CardHoverInfoPopup, card_hover_icon
from production_zero.ui.empty_state import EmptyStatePanel
from production_zero.ui.factory_view_v2 import _display_card_title, prototype_family_for_definition
from production_zero.ui.game_ui.rendering import draw_machine_card_prototype
from production_zero.ui.game_ui.tokens import Accent
from production_zero.ui.main_tab_header import MainTabHeader
from production_zero.ui.resource_icons import ResourceIconWidget, card_resource_icon_signature, resource_accent_key, resource_icon_key
from production_zero.ui.text_format import smart_card_title
from production_zero.ui.widget_lifecycle import clear_layout_safely, hide_detach_delete


COMMON_SUPPLY_CARD_WIDTH = 208
COMMON_SUPPLY_CARD_HEIGHT = 276
FEATURED_SUPPLY_CARD_WIDTH = 208
FEATURED_SUPPLY_CARD_HEIGHT = 276
SUPPLY_GRID_SPACING = 12
DAILY_SUPPLY_VISIBLE_CARDS = 4
DAILY_SUPPLY_GRID_COLUMNS = 4
DAILY_SUPPLY_GRID_ROWS = 1
DAILY_SUPPLY_CARD_GAP = 14
DAILY_SUPPLY_ROW_GAP = 18
DAILY_SUPPLY_GALLERY_HORIZONTAL_PADDING = 18
DAILY_SUPPLY_GALLERY_VERTICAL_PADDING = 22
DAILY_SUPPLY_MIN_CARD_WIDTH = 160
COMMON_SUPPLY_BUFFER_ROWS = 2
COMMON_SUPPLY_SEARCH_DEBOUNCE_MS = 180
COMMON_SUPPLY_HOVER_DELAY_MS = 300
COMMON_SUPPLY_TITLE_HEIGHT = 38
COMMON_SUPPLY_HEADER_HEIGHT = 64
COMMON_SUPPLY_LEFT_PADDING = 12


@dataclass(frozen=True, slots=True)
class CommonSupplyCardDisplayData:
    offer: SupplyOffer
    definition: CardDefinition
    definition_id: str
    offer_id: str
    name: str
    type_label: str
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
        self._price_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
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
        signature = (data, source, state, button_text, can_buy)
        if getattr(self, "_binding_signature", None) == signature:
            return
        self._binding_signature = signature
        self._supply_data = data
        self._source = source
        self._state = state
        self.setProperty("state", state)
        self.setProperty("source", source)
        self.setProperty("cardKind", data.definition.card_kind.value)
        previous_freight_family = str(self.property("freightFamily") or "")
        freight_family = data.definition.family.value if isinstance(data.definition, FreightDefinition) else ""
        self.setProperty("freightFamily", freight_family)
        if freight_family != previous_freight_family:
            self.style().unpolish(self)
            self.style().polish(self)
            self._buy_button.style().unpolish(self._buy_button)
            self._buy_button.style().polish(self._buy_button)
        self.setProperty("definitionId", data.definition_id)
        self.setProperty("offerId", data.offer_id)
        self._name_label.setText(data.name)
        self._name_label.setProperty("displayText", _display_card_title(data.definition))
        self._rarity_label.setText(data.rarity_label)
        self._rarity_line.setProperty("rarity", data.rarity_key)
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
        scale = max(0.48, min(1.0, rect.width() / FEATURED_SUPPLY_CARD_WIDTH))
        footer = self._footer_rect(rect)
        side_inset = max(5, round(8 * scale))
        gap = max(5, round(7 * scale))
        button_width = max(64, round(78 * scale))
        available_width = int(footer.width()) - side_inset * 2
        price_width = max(30, available_width - gap - button_width)
        control_height = max(22, int(footer.height()) - 6)
        control_top = int(footer.top() + (footer.height() - control_height) / 2)
        font = self._price_label.font()
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.Black)
        while QFontMetrics(font).horizontalAdvance(self._price_label.text()) > price_width - 2 and font.pixelSize() > 6:
            font.setPixelSize(font.pixelSize() - 1)
        self._price_label.setFont(font)
        # A stylesheet font-size overrides setFont(). Apply the fitted size at
        # the same precedence, including after a recycled offer changes price.
        self._price_label.setStyleSheet(f"font-size: {font.pixelSize()}px;")
        self._price_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        price_left = int(footer.left()) + side_inset
        button_left = price_left + price_width + gap
        self._price_label.setGeometry(price_left, control_top, price_width, control_height)
        self._buy_button.setGeometry(button_left, control_top, button_width, control_height)
        if self._state == "locked":
            self._price_label.hide()
            self._buy_button.setGeometry(price_left, int(footer.top()), available_width, int(footer.height()))
        else:
            self._price_label.show()

    def _footer_rect(self, rect: QRectF) -> QRectF:
        scale = max(0.48, min(1.0, rect.width() / FEATURED_SUPPLY_CARD_WIDTH))
        horizontal_inset = max(7, round(10 * scale))
        bottom_inset = max(7, round(9 * scale))
        footer_height = max(30, round(34 * scale))
        return QRectF(
            rect.left() + horizontal_inset,
            rect.bottom() - bottom_inset - footer_height,
            rect.width() - horizontal_inset * 2,
            footer_height,
        )

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
                meta=data.rarity_label.upper(),
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
        footer = self._footer_rect(rect)
        body = QLinearGradient(footer.topLeft(), footer.bottomLeft())
        body.setColorAt(0.0, QColor(255, 255, 255, 18))
        body.setColorAt(0.45, QColor(7, 10, 10, 168))
        body.setColorAt(1.0, QColor(0, 0, 0, 128))
        painter.setPen(QPen(QColor(246, 244, 229, 34), 1))
        painter.setBrush(body)
        painter.drawRoundedRect(footer, 7, 7)


class SupplyView(QWidget):
    def __init__(
        self,
        state: GameState,
        command_bus: CommandBus,
        definitions: dict[str, CardDefinition],
        on_state_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("supplyView")
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
        self._common_empty_state: EmptyStatePanel | None = None
        self._common_last_scroll_value = 0
        self._common_last_viewport_height = 0
        self._common_filter_apply_count = 0
        self._common_reflow_count = 0
        self._common_display_signature: tuple = ()
        self._common_filtered_signature: tuple = ()
        self._filter_chip_signatures: dict[QComboBox, tuple[str, tuple[str, ...]]] = {}
        self._selector_flyout_signatures: dict[QComboBox, tuple[str, ...]] = {}
        self._common_performance = {
            "initial_ms": 0.0,
            "filter_ms": 0.0,
            "visible_update_ms": 0.0,
            "pool_size": 0,
        }
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
        self._daily_offer_galleries: list[QScrollArea] = []
        self._daily_offer_bands: list[QFrame] = []
        self._daily_gallery_layouts: list[QGridLayout] = []
        self._daily_card_size = (FEATURED_SUPPLY_CARD_WIDTH, FEATURED_SUPPLY_CARD_HEIGHT)

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
        display_data = [self._display_data_for_offer(offer) for offer in self._common_offers]
        display_signature = tuple(
            (data.offer_id, data.definition_id, data.rarity_label, data.price_text)
            for data in display_data
        )
        common_structure_changed = display_signature != self._common_display_signature
        self._common_display_signature = display_signature
        self._common_display_data = display_data
        self._common_performance["initial_ms"] = (perf_counter() - start) * 1000
        self._refresh_store_header_metrics()
        self._refresh_freight_daily_cards()
        self._refresh_machine_daily_cards()
        self._refresh_common_purchase_buttons()
        if common_structure_changed:
            self._refresh_common_filters()
            self._apply_common_filter(reset_scroll=False)
        else:
            self._refresh_filter_widgets()
            self._apply_common_filter(reset_scroll=False)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            daily_viewports = []
            if hasattr(self, "_daily_scroll"):
                daily_viewports.append(self._daily_scroll.viewport())
            if hasattr(self, "_daily_offer_galleries"):
                daily_viewports.extend(gallery.viewport() for gallery in self._daily_offer_galleries)
            if any(watched is viewport for viewport in daily_viewports):
                event.accept()
                return True
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
        elif (
            hasattr(self, "_daily_scroll")
            and watched is self._daily_scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._layout_daily_modules()
        elif (
            hasattr(self, "_daily_offer_galleries")
            and event.type() == QEvent.Type.Resize
            and any(watched is gallery.viewport() for gallery in self._daily_offer_galleries)
        ):
            self._sync_daily_gallery_layouts()
        elif event.type() == QEvent.Type.Enter and isinstance(watched, SupplyOfferCardFrame):
            self._schedule_common_hover(watched)
        elif event.type() == QEvent.Type.Leave and isinstance(watched, SupplyOfferCardFrame):
            self._hide_common_hover(watched)
        return super().eventFilter(watched, event)

    def _build_store_header(self) -> QFrame:
        panel = MainTabHeader(
            object_name="supplyStoreHeader",
            title="INDUSTRIAL SUPPLY",
            subtitle="PROCUREMENT · DAILY ROTATIONS · PERMANENT SUPPLY",
            title_object_name="supplyStoreTitle",
            subtitle_object_name="supplyStoreSubtitle",
            accent=Accent.NEUTRAL,
        )
        for metric_key, label, value in (
            ("daily_reset", "DAILY RESET", self._format_duration(seconds_until_supply_daily_reset(self._state)).upper()),
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
            panel.add_status_module(module)
        return panel

    def _refresh_store_header_metrics(self) -> None:
        if not self._header_metric_values:
            return
        self._header_metric_values["daily_reset"].setText(self._format_duration(seconds_until_supply_daily_reset(self._state)).upper())

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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("supplyDailyScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.viewport().installEventFilter(self)
        self._daily_scroll = scroll
        content = QWidget()
        content.setObjectName("supplyDailyContent")
        self._daily_content = content
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(12)
        content_layout.setVerticalSpacing(12)
        self._daily_content_layout = content_layout
        freight_section, self._freight_daily_grid = self._daily_offer_section("DAILY FREIGHT", "supplyDailyFreightSection")
        machine_section, self._machine_daily_grid = self._daily_offer_section("DAILY MACHINES", "supplyDailyMachineSection")
        self._daily_sections = (freight_section, machine_section)
        self._daily_module_columns_used = 0
        self._layout_daily_modules()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return page

    def _layout_daily_modules(self) -> None:
        if not hasattr(self, "_daily_content_layout") or not hasattr(self, "_daily_sections"):
            return
        width = self._daily_scroll.viewport().width() if hasattr(self, "_daily_scroll") else self.width()
        height = self._daily_scroll.viewport().height() if hasattr(self, "_daily_scroll") else self.height()
        if hasattr(self, "_daily_content"):
            self._daily_content.setFixedHeight(max(1, height))
        columns = 2 if width >= 760 else 1
        if columns == self._daily_module_columns_used:
            self._sync_daily_gallery_layouts()
            return
        self._daily_module_columns_used = columns
        while self._daily_content_layout.count():
            item = self._daily_content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        for index, section in enumerate(self._daily_sections):
            self._daily_content_layout.addWidget(section, index // columns, index % columns)
        for column in range(3):
            self._daily_content_layout.setColumnStretch(column, 1 if column < columns else 0)
        rows = (len(self._daily_sections) + columns - 1) // columns
        for row in range(len(self._daily_sections) + 1):
            self._daily_content_layout.setRowStretch(row, 1 if row < rows else 0)
        self._sync_daily_gallery_layouts()

    def _sync_daily_gallery_widths(self, columns: int) -> None:
        self._sync_daily_gallery_layouts()

    def _sync_daily_gallery_layouts(self) -> None:
        aspect = FEATURED_SUPPLY_CARD_HEIGHT / FEATURED_SUPPLY_CARD_WIDTH
        for gallery, band, card_layout in zip(self._daily_offer_galleries, self._daily_offer_bands, self._daily_gallery_layouts, strict=False):
            viewport_width = gallery.viewport().width() or gallery.width()
            viewport_height = gallery.viewport().height() or gallery.height()
            if viewport_width <= 0:
                viewport_width = max(1, gallery.parentWidget().width() - 20 if gallery.parentWidget() is not None else FEATURED_SUPPLY_CARD_WIDTH)
            if viewport_height <= 0:
                viewport_height = FEATURED_SUPPLY_CARD_HEIGHT + DAILY_SUPPLY_GALLERY_VERTICAL_PADDING * 2
            # Leave a small rounding reserve so the four fixed-width cards never
            # create a hidden 1-2 px horizontal scroll range in QScrollArea.
            usable_width = max(1, viewport_width - DAILY_SUPPLY_GALLERY_HORIZONTAL_PADDING * 2 - 4)
            usable_height = max(1, viewport_height - DAILY_SUPPLY_GALLERY_VERTICAL_PADDING * 2)
            max_width = (usable_width - DAILY_SUPPLY_CARD_GAP * (DAILY_SUPPLY_GRID_COLUMNS - 1)) / DAILY_SUPPLY_GRID_COLUMNS
            max_height = (usable_height - DAILY_SUPPLY_ROW_GAP * (DAILY_SUPPLY_GRID_ROWS - 1)) / DAILY_SUPPLY_GRID_ROWS
            card_width = max(1, min(FEATURED_SUPPLY_CARD_WIDTH, int(max_width), round(max_height / aspect)))
            card_height = round(card_width * aspect)
            for index in range(card_layout.count()):
                widget = card_layout.itemAt(index).widget()
                if isinstance(widget, SupplyOfferCardFrame):
                    widget.setFixedSize(card_width, card_height)
            self._daily_card_size = (card_width, card_height)
            card_layout.activate()

    def _daily_offer_section(self, title_text: str, object_name: str) -> tuple[QFrame, QGridLayout]:
        section = QFrame()
        section.setObjectName(object_name)
        section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(1)
        title = QLabel(title_text)
        title.setObjectName("supplyDailySectionTitle")
        subtitle = QLabel(f"CHOOSE 1 OF {DAILY_SUPPLY_VISIBLE_CARDS}")
        subtitle.setObjectName("supplyDailySectionSubtitle")
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)
        layout.addLayout(header)
        gallery = QScrollArea(section)
        gallery.setObjectName("supplyDailyOfferScroll")
        gallery.setWidgetResizable(True)
        gallery.setFrameShape(QFrame.Shape.NoFrame)
        gallery.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        gallery.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        gallery.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        gallery.viewport().installEventFilter(self)
        band = QFrame()
        band.setObjectName("supplyDailyOfferBand")
        band.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grid = QGridLayout(band)
        grid.setContentsMargins(DAILY_SUPPLY_GALLERY_HORIZONTAL_PADDING, DAILY_SUPPLY_GALLERY_VERTICAL_PADDING, DAILY_SUPPLY_GALLERY_HORIZONTAL_PADDING, DAILY_SUPPLY_GALLERY_VERTICAL_PADDING)
        grid.setHorizontalSpacing(DAILY_SUPPLY_CARD_GAP)
        grid.setVerticalSpacing(DAILY_SUPPLY_ROW_GAP)
        grid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gallery.setWidget(band)
        self._daily_offer_galleries.append(gallery)
        self._daily_offer_bands.append(band)
        self._daily_gallery_layouts.append(grid)
        layout.addWidget(gallery, 1)
        return section, grid

    def _build_common_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("supplyCommonPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("supplyToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        from production_zero.ui.supply_categories import SupplyCategoryButtons
        from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
        self._type_filter = SupplyCategoryButtons(toolbar)
        self._type_filter.setObjectName("supplyCategoryButtons")
        self._type_filter.currentTextChanged.connect(self._on_common_type_changed)
        category_label = QLabel("CATEGORY")
        category_label.setObjectName("supplyCategoryHeading")
        font = GAME_UI_TOKENS.typography.industrial_title()
        font.setPointSize(22)
        font.setBold(True)
        category_label.setFont(font)
        category_label.setStyleSheet(f"color: #101713; background: transparent; font-family: '{font.family()}'; font-size: 24px; font-weight: 900;")
        toolbar_layout.addWidget(category_label)
        toolbar_layout.addWidget(self._type_filter, 1)
        self._common_status_label = None
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

    def show_common(self, category="All") -> None:
        """Open the reusable Common Supply page at a board's card category."""
        if category not in self._type_filter.categories:
            category = "All"
        self.refresh()
        self._type_filter.setCurrentText(category)
        self._show_section(1)

    def _sync_section_buttons(self, index: int) -> None:
        for button_index, button in enumerate(self._section_buttons):
            button.blockSignals(True)
            button.setChecked(button_index == index)
            button.setProperty("active", button_index == index)
            button.style().unpolish(button)
            button.style().polish(button)
            button.blockSignals(False)

    def _refresh_common_filters(self) -> None:
        # The four basic categories are stable; purchases never rebuild controls.
        pass

    def _set_options(self, combo: QComboBox, options: list[str]) -> bool:
        if [combo.itemText(index) for index in range(combo.count())] == options:
            return False
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        if current in options:
            combo.setCurrentText(current)
        combo.blockSignals(False)
        return True

    def _refresh_freight_daily_cards(self) -> None:
        self._refresh_daily_offer_cards(self._freight_daily_grid, self._state.supply.freight_daily_offers, "freight_daily")

    def _refresh_machine_daily_cards(self) -> None:
        self._refresh_daily_offer_cards(self._machine_daily_grid, self._state.supply.machine_daily_offers, "machine_daily")

    def _refresh_daily_offer_cards(self, layout: QGridLayout, offers: list[SupplyOffer], source: str) -> None:
        existing = [layout.itemAt(i).widget() for i in range(layout.count())]
        if [getattr(c, "_supply_data", None).offer for c in existing if isinstance(c, SupplyOfferCardFrame)] == offers:
            for card, offer in zip(existing, offers):
                state = self._offer_state(offer, source)
                card.bind_offer(self._display_data_for_offer(offer), source=source, state=state,
                                button_text=self._button_text(source, state), can_buy=self._can_buy(offer, source))
                self._set_purchase_hint(card, offer, source)
            self._sync_daily_gallery_layouts()
            return
        self._hide_common_hover()
        self._clear_layout(layout)
        for index, offer in enumerate(offers):
            card = self._supply_card(offer, source)
            layout.addWidget(card, index // DAILY_SUPPLY_GRID_COLUMNS, index % DAILY_SUPPLY_GRID_COLUMNS, Qt.AlignmentFlag.AlignCenter)
            card.show()
        self._sync_daily_gallery_layouts()

    def _on_common_type_changed(self, *args) -> None:
        self._apply_common_filter()

    def _apply_common_filter(self, *args, reset_scroll: bool = True) -> None:
        if not hasattr(self, "_common_grid_container"):
            return
        start = perf_counter()
        selected_type = self._type_filter.currentText()
        data = [
            item
            for item in self._common_display_data
            if selected_type == 'All' or self._supply_category(item.definition) == selected_type
        ]
        filtered = self._sort_display_data(data)
        filtered_signature = tuple(item.offer_id for item in filtered)
        structure_changed = filtered_signature != self._common_filtered_signature
        self._common_filtered_signature = filtered_signature
        self._filtered_common_data = filtered
        self._refresh_filter_widgets()
        self._common_filter_apply_count += 1
        self._common_performance["filter_ms"] = (perf_counter() - start) * 1000
        if reset_scroll and structure_changed:
            self._common_scroll.verticalScrollBar().setValue(0)
        if structure_changed:
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
        viewport_height = self._common_scroll.viewport().height() if hasattr(self, "_common_scroll") else 0
        if not self._filtered_common_data:
            height = max(260, viewport_height)
        else:
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
            self._show_common_empty_state()
            self._refresh_common_purchase_buttons()
            self._common_performance["visible_update_ms"] = (perf_counter() - start) * 1000
            return
        self._hide_common_empty_state()
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
        viewport_rows = viewport_height // row_pitch + 1
        stable_pool_size = min(
            len(self._filtered_common_data),
            columns * (viewport_rows + COMMON_SUPPLY_BUFFER_ROWS * 2 + 1),
        )
        self._ensure_common_card_pool(max(len(indexes), stable_pool_size))
        x_offset = self._common_sparse_x_offset(len(self._filtered_common_data), columns)
        active_cards = set()
        for pool_index, data_index in enumerate(indexes):
            card = self._common_card_pool[pool_index]
            self._bind_common_card_widget(card, data_index)
            row = data_index // columns
            column = data_index % columns
            x = x_offset + column * (COMMON_SUPPLY_CARD_WIDTH + SUPPLY_GRID_SPACING)
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
        self._refresh_common_purchase_buttons()
        self._common_performance["visible_update_ms"] = (perf_counter() - start) * 1000
        self._common_performance["pool_size"] = len(self._common_card_pool)

    def _refresh_common_purchase_buttons(self) -> None:
        button_text = "BUY"
        for card, data_index in tuple(self._common_card_bindings.items()):
            if data_index >= len(self._filtered_common_data) or not isinstance(card, SupplyOfferCardFrame):
                continue
            data = self._filtered_common_data[data_index]
            card.bind_offer(
                self._quantity_priced_data(data, "common"),
                source="common",
                state=self._offer_state(data.offer, "common"),
                button_text=button_text,
                can_buy=self._can_buy(data.offer, "common"),
            )
            self._set_purchase_hint(card, data.offer, "common")

    def _common_sparse_x_offset(self, item_count: int, columns: int) -> int:
        return COMMON_SUPPLY_LEFT_PADDING

    def _ensure_common_card_pool(self, target_count: int) -> None:
        while len(self._common_card_pool) < target_count:
            self._common_card_pool.append(self._create_common_card_widget())

    def _hide_common_card_pool(self) -> None:
        for card in self._common_card_pool:
            card.hide()
        self._common_card_bindings = {}
        self._common_visible_indexes = set()

    def _show_common_empty_state(self) -> None:
        if self._common_empty_state is None:
            self._common_empty_state = EmptyStatePanel(
                "No common supply cards",
                "No current offers in this category. Choose another category.",
                accent="supply",
                object_name="commonSupplyEmptyState",
                parent=self._common_grid_container,
            )
        width = self._common_grid_available_width()
        viewport_height = self._common_scroll.viewport().height() if hasattr(self, "_common_scroll") else 260
        panel_width = min(560, max(320, width - 48))
        panel_height = min(260, max(220, viewport_height - 48))
        x = max(16, (width - panel_width) // 2)
        y = max(16, (viewport_height - panel_height) // 2)
        self._common_empty_state.setGeometry(x, y, panel_width, panel_height)
        self._common_empty_state.show()
        self._common_empty_state.raise_()

    def _hide_common_empty_state(self) -> None:
        if self._common_empty_state is not None:
            self._common_empty_state.hide()

    def _supply_card(self, offer: SupplyOffer, source: str) -> QFrame:
        data = self._display_data_for_offer(offer)
        state = self._offer_state(offer, source)
        card = SupplyOfferCardFrame()
        card.installEventFilter(self)
        card.setObjectName(self._card_object_name(source))
        if source == "common":
            card.setFixedSize(COMMON_SUPPLY_CARD_WIDTH, COMMON_SUPPLY_CARD_HEIGHT)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        else:
            card.setFixedSize(*self._daily_card_size)
            card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        card._buy_button.setObjectName(self._button_object_name(source))  # type: ignore[attr-defined]
        card._buy_button.clicked.connect(lambda checked=False, current_offer=offer, current_source=source: self._buy_offer(current_offer, current_source))  # type: ignore[attr-defined]
        card.bind_offer(
            self._quantity_priced_data(data, source),
            source=source,
            state=state,
            button_text=self._button_text(source, state),
            can_buy=self._can_buy(offer, source),
        )
        self._set_purchase_hint(card, offer, source)
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
                self._quantity_priced_data(data, "common"),
                source="common",
                state=self._offer_state(data.offer, "common"),
                button_text="BUY",
                can_buy=self._can_buy(data.offer, "common"),
            )
            self._set_purchase_hint(card, data.offer, "common")
        if self._hover_card is card:
            self._hover_timer.stop()
            self._hide_common_hover(card)

    def _common_card_title_text(self, data: CommonSupplyCardDisplayData) -> str:
        return data.name

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
            icon = card_hover_icon(data.definition, size=42)
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
            ("Rarity", offer.rarity.value.title()),
            ("Bonus", f"+{offer.bonus_tenths / 10:.1f}%"),
        ]
        if isinstance(definition, FreightDefinition):
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
                ("Price", f"${offer.price_cash:,.2f}"),
                ("Owned", str(self._owned_count(offer))),
                ("State", self._offer_state(offer, "common").upper()),
            ]
        )
        return sections

    def _display_data_for_offer(self, offer: SupplyOffer) -> CommonSupplyCardDisplayData:
        key = (offer.definition_id, offer.rarity.value, offer.bonus_tenths, offer.price_cash)
        cached = self._common_display_cache.get(key)
        if cached is not None:
            # A later daily rotation can repeat the same quality and price.
            # Reuse its presentation without keeping the previous offer ID.
            if cached.offer != offer:
                cached = replace(cached, offer=offer, offer_id=offer.offer_id)
                self._common_display_cache[key] = cached
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
            rarity_label=offer.rarity.value.title(),
            rarity_key=offer.rarity.value,
            bonus_text=f"+{offer.bonus_tenths / 10:.1f}%",
            primary_text=primary,
            secondary_text=secondary,
            price_text=f"${offer.price_cash:.2f}",
            icon_resource_id=icon_resource_id,
            icon_key=icon_key,
            accent_key=accent_key,
            search_text=f"{definition.name} {offer.definition_id} {self._function_label(definition)}".lower(),
        )
        self._common_display_cache[key] = data
        return data

    def _quantity_priced_data(self, data: CommonSupplyCardDisplayData, source: str) -> CommonSupplyCardDisplayData:
        return data

    def _sort_display_data(self, data: list[CommonSupplyCardDisplayData]) -> list[CommonSupplyCardDisplayData]:
        return sorted(data, key=lambda item: item.name)

    @staticmethod
    def _supply_category(definition):
        from production_zero.core.machine_operations import SITE_TYPES
        if isinstance(definition, FreightDefinition): return "Freight"
        if isinstance(definition, EnergyDefinition): return "Energy"
        if definition.definition_id in SITE_TYPES: return "Resources"
        return "Factory"

    def _compact_values(self, offer: SupplyOffer, definition: CardDefinition) -> tuple[str, str]:
        return self._effective_values(offer, definition)

    def _elide_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[: max(0, max_chars - 1)].rstrip()}…"

    def _buy_offer(self, offer: SupplyOffer, source: str) -> None:
        from production_zero.ui.release_dialogs import inform
        from PySide6.QtWidgets import QDialog
        problem = self._purchase_problem(offer, source, 1)
        if problem:
            inform(self, *problem)
            return
        dialog = self._purchase_dialog(offer, source)
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self._commit_purchase(dialog)
        except (ValueError, KeyError) as error:
            inform(self, "Purchase to inventory", str(error))
        finally:
            dialog.deleteLater()

    def _purchase_dialog(self, offer, source):
        from production_zero.core.supply import common_supply_max_quantity
        from production_zero.ui.release_dialogs import InventoryPurchaseDialog
        maximum = common_supply_max_quantity(self._state, self._definitions, offer.definition_id) if source == "common" else int(self._state.cash.amount >= offer.price_cash)
        dialog = InventoryPurchaseDialog(self._definitions[offer.definition_id].name, offer.rarity.value,
            offer.price_cash, self._state.cash.amount, maximum, self, quantity_selectable=source == "common")
        dialog.offer = offer
        dialog.source = source
        return dialog

    def _commit_purchase(self, dialog):
        # Freeze one command per confirmed intent, including retries/double signals.
        if dialog.purchase_command is None:
            offer = dialog.offer
            quantity = dialog.quantity.value() if dialog.quantity is not None else 1
            if quantity < 1:
                raise ValueError("Insufficient cash: MAX is zero.")
            kwargs = dict(expected_unit_price=offer.price_cash, operation_id=dialog.operation_id)
            if dialog.source == "common":
                command = BuyCommonSupplyCard(offer.definition_id, self._definitions, quantity, **kwargs)
            elif dialog.source == "freight_daily":
                command = BuyDailyFreightSupplyCard(offer.offer_id, self._definitions, **kwargs)
            elif dialog.source == "machine_daily":
                command = BuyDailyMachineSupplyCard(offer.offer_id, self._definitions, **kwargs)
            else:
                raise ValueError("This offer is no longer available.")
            dialog.purchase_command = command
        self._bus.dispatch(dialog.purchase_command)
        self._notify_and_refresh()

    def _execute_offer_purchase(self, offer: SupplyOffer, source: str) -> None:
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
        return max(1, min(7, max(1, width - COMMON_SUPPLY_LEFT_PADDING * 2) // pitch))

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
        quantity = self._common_buy_quantity() if source == "common" else 1
        return self._purchase_problem(offer, source, quantity) is None

    def _set_purchase_hint(self, card, offer, source):
        problem = self._purchase_problem(offer, source, self._common_buy_quantity() if source == "common" else 1)
        message = ": ".join(problem) if problem is not None else "Purchase to inventory. Install manually when ready."
        card._buy_button.setToolTip(message)
        card.setToolTip(message if problem is not None else "")

    def _purchase_problem(self, offer, source, quantity):
        definition = self._definitions.get(offer.definition_id)
        if not isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition)):
            return "Machine Unavailable", "This machine is no longer available."
        if type(quantity) is not int or not 1 <= quantity <= 10000:
            return "Invalid Quantity", "Choose a whole quantity from 1 to 10000."
        if source in {"freight_daily", "machine_daily"}:
            prefix = "freight_daily" if source == "freight_daily" else "machine_daily"
            book = self._state.supply
            if getattr(book, prefix + "_purchased_period_index") == getattr(book, prefix + "_period_index"):
                return "Purchase Limit Reached", "This daily category has already been purchased. Wait for the next reset."
            if offer not in getattr(book, prefix + "_offers"):
                return "Machine Unavailable", "This offer has expired. Choose a current offer."
        elif source != "common":
            return "Machine Unavailable", "This offer is no longer available."
        total = offer.price_cash * quantity
        if self._state.cash.amount < total:
            return "Insufficient Cash", f"Required: ${total:,.2f}. Available: ${self._state.cash.amount:,.2f}."
        return None

    def _buy_common(self, definition_id: str) -> None:
        self._bus.dispatch(BuyCommonSupplyCard(definition_id, self._definitions, self._common_buy_quantity()))
        self._notify_and_refresh()

    def _common_buy_quantity(self) -> int:
        return getattr(self, "_pending_purchase_quantity", None) or 1

    def _on_buy_quantity_changed(self, *args) -> None:
        self._refresh_filter_widgets()
        self._refresh_common_purchase_buttons()

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
            if self.property("uiDirty"):
                # The originating purchase projection remains current even
                # when invoked programmatically from a hidden tab.
                self.refresh()
                self.setProperty("uiDirty", False)
        else:
            self.refresh()

    def _button_text(self, source: str, state: str) -> str:
        if source in {"daily", "freight_daily", "machine_daily"} and state == "purchased":
            return "PURCHASED"
        if source in {"daily", "freight_daily", "machine_daily"} and state == "locked":
            return "LOCKED\nUNTIL RESET"
        return "BUY"

    def _icon_signature(self, definition: CardDefinition) -> tuple[str, str, str]:
        icon_key, accent_key, resource_id = card_resource_icon_signature(definition)
        return resource_id, icon_key, accent_key

    def _function_label(self, definition: CardDefinition) -> str:
        if isinstance(definition, MachineDefinition):
            return definition.name
        if isinstance(definition, EnergyDefinition):
            return "Energy"
        if isinstance(definition, FreightDefinition):
            return definition.family.value.replace("_", " ").title()
        return definition.card_kind.value.title()

    def _owned_count(self, offer: SupplyOffer) -> int:
        return sum(
            1
            for card in self._state.cards.values()
            if card.definition_id == offer.definition_id
            and card.rarity == offer.rarity
            and card.output_bonus_tenths == offer.bonus_tenths
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
        pass

    def reset_for_state_change(self):
        self._hover_timer.stop()
        self._hide_common_hover()
        self._pending_purchase_quantity = None
        self._common_display_cache.clear()
        self._common_display_data.clear()
        self._filtered_common_data.clear()
        self._common_display_signature = ()
        self._common_filtered_signature = ()
        self._common_card_bindings.clear()
        self._hide_common_card_pool()
        for card in self._common_card_pool:
            card._supply_data = None
            card._binding_signature = None
        self._type_filter.blockSignals(True)
        self._type_filter.setCurrentIndex(0)
        self._type_filter.blockSignals(False)
        self._common_scroll.verticalScrollBar().setValue(0)
        self._show_section(0)
        self.refresh()

    def _refresh_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        options = tuple(combo.itemText(index) for index in range(combo.count()))
        signature = (group, options)
        chips = [layout.itemAt(index).widget() for index in range(layout.count())]
        if self._filter_chip_signatures.get(combo) != signature:
            self._clear_layout(layout)
            chips = []
            for option in options:
                chip = QPushButton(option.upper())
                chip.setObjectName("supplyFilterChip")
                chip.setProperty("filterGroup", group)
                chip.setProperty("filterValue", option)
                chip.setCursor(Qt.CursorShape.PointingHandCursor)
                chip.clicked.connect(lambda checked=False, value=option, target=combo: self._set_filter_value(target, value))
                layout.addWidget(chip)
                chips.append(chip)
            self._filter_chip_signatures[combo] = signature
        current = combo.currentText()
        for chip, option in zip(chips, options):
            active = option == current
            if chip.property("active") != active:
                chip.setProperty("active", active)
                chip.style().unpolish(chip)
                chip.style().polish(chip)
                chip.update()

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
        if isinstance(definition, FreightDefinition):
            stats = freight_stats(card, definition)
            return f"Transport Capacity {stats.capacity:g}", f"Transport Time {self._format_short_duration(stats.transport_time_seconds)}"
        return "-", "-"

    def _type_label(self, definition: CardDefinition) -> str:
        return definition.card_kind.value.title()

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
