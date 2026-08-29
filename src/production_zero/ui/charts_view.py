from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.history import TIME_RANGE_SAMPLES
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.game_ui import Accent, GAME_UI_TOKENS, MaterialLevel, draw_game_panel, draw_inset_surface, draw_track_surface
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_key, resource_icon_key
from production_zero.ui.theme import Theme
from production_zero.ui.widget_lifecycle import clear_layout_safely


@dataclass(frozen=True, slots=True)
class ChartSeries:
    title: str
    metric_id: str
    color: str


class LineChartWidget(QWidget):
    def __init__(self, state: GameState, series: ChartSeries, range_id: str = "ALL") -> None:
        super().__init__()
        self._state = state
        self._series = series
        self._range_id = range_id
        self.setObjectName("lineChart")
        self.setMinimumHeight(150)
        self.setProperty("chartRole", self._chart_role())

    def set_series(self, series: ChartSeries) -> None:
        self._series = series
        self.setProperty("chartRole", self._chart_role())
        self.update()

    def set_range(self, range_id: str) -> None:
        self._range_id = range_id
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(1, 1, -1, -1)
        accent = self._chart_accent()
        draw_game_panel(painter, rect, accent=accent, level=MaterialLevel.INSET, radius=10)
        plot_shell = rect.adjusted(12, 42, -12, -14)
        draw_inset_surface(painter, plot_shell, accent=accent, radius=7)

        painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
        painter.setFont(GAME_UI_TOKENS.typography.industrial_label())
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._series.title.upper())

        values = self._state.history.values_for_range(self._series.metric_id, self._range_id)
        if len(values) < 2:
            painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_muted))
            painter.setFont(GAME_UI_TOKENS.typography.status_label())
            painter.drawText(plot_shell, Qt.AlignmentFlag.AlignCenter, "NO DATA YET")
            return

        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum or 1.0
        plot = plot_shell.adjusted(10, 10, -10, -10)
        painter.setPen(QPen(QColor(Theme.GRID), 1))
        for step in range(1, 4):
            y = plot.top() + plot.height() * step / 4
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        points = [
            QPointF(
                plot.left() + plot.width() * index / (len(values) - 1),
                plot.bottom() - ((value - minimum) / span * plot.height()),
            )
            for index, value in enumerate(values)
        ]
        painter.setPen(QPen(QColor(self._series.color), 2.2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)

        painter.setPen(QColor(self._series.color))
        painter.setFont(GAME_UI_TOKENS.typography.status_label())
        painter.drawText(rect.adjusted(12, 8, -12, -8), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight, f"{values[-1]:.1f}")

    def _chart_role(self) -> str:
        title = self._series.title.lower()
        if "production" in title:
            return "production"
        if "consumption" in title:
            return "consumption"
        return "stock"

    def _chart_accent(self) -> Accent:
        role = self._chart_role()
        if role == "production":
            return Accent.SUCCESS
        if role == "consumption":
            return Accent.WARNING
        return Accent.STORAGE


class SparklineWidget(QWidget):
    def __init__(self, state: GameState, metric_id: str, color: str = Theme.RESOURCE) -> None:
        super().__init__()
        self._state = state
        self._metric_id = metric_id
        self._color = color
        self.setObjectName("chartResourceSparkline")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_metric(self, metric_id: str, color: str) -> None:
        self._metric_id = metric_id
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height()).adjusted(1, 2, -1, -2)
        painter.setPen(QPen(QColor(Theme.GRID), 1))
        center_y = rect.center().y()
        painter.drawLine(QPointF(rect.left(), center_y), QPointF(rect.right(), center_y))

        values = self._state.history.values_for_range(self._metric_id, "ALL")
        if len(values) < 2:
            painter.setPen(QPen(QColor(Theme.DIM), 1))
            painter.drawLine(QPointF(rect.left(), center_y), QPointF(rect.right(), center_y))
            return

        values = values[-32:]
        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum or 1.0
        points = [
            QPointF(
                rect.left() + rect.width() * index / (len(values) - 1),
                rect.bottom() - ((value - minimum) / span * rect.height()),
            )
            for index, value in enumerate(values)
        ]
        painter.setPen(QPen(QColor(self._color), 2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)


class ChartsHeader(QFrame):
    def __init__(self, state: GameState, resources: dict[str, ResourceDefinition]) -> None:
        super().__init__()
        self._state = state
        self._resources = resources
        self.setObjectName("chartsHeader")
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 25, 32, 24)
        layout.setSpacing(18)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(1)
        title = QLabel("CHARTS")
        title.setObjectName("chartsHeroTitle")
        subtitle = QLabel("RESOURCE FLOW / ANALYTICS")
        subtitle.setObjectName("chartsHeroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column, 1)
        self._tracked_value = self._metric("TRACKED", "0")
        self._active_value = self._metric("ACTIVE", "0")
        layout.addWidget(self._tracked_value[0])
        layout.addWidget(self._active_value[0])
        self.refresh()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=16)
        inset = rect.adjusted(14, 13, -14, -13)
        draw_track_surface(painter, inset, accent=Accent.STORAGE, radius=11)
        painter.end()
        super().paintEvent(event)

    def refresh(self) -> None:
        self._tracked_value[1].setText(str(len(self._resources)))
        active = sum(1 for resource_id, stock in self._state.resources.items() if resource_id in self._resources and stock.amount > 0)
        self._active_value[1].setText(str(active))

    def _metric(self, label_text: str, value_text: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("chartsHeaderMetric")
        tile.setMinimumSize(134, 58)
        tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        label = QLabel(label_text)
        label.setObjectName("chartsMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("chartsMetricValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return tile, value


class ChartFilterScroll(QScrollArea):
    def __init__(self, content: QWidget, object_name: str, preferred_width: int = 1180) -> None:
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
        self._content.resize(max(self.viewport().width(), hint.width()), max(self.viewport().height(), hint.height()))


class ChartsView(QWidget):
    def __init__(self, state: GameState, resources: dict[str, ResourceDefinition]) -> None:
        super().__init__()
        self._state = state
        self._resources = resources
        self._selected_resource_id: str | None = None
        self._resource_tile_pool: dict[str, QFrame] = {}
        self._resource_tiles: dict[str, QFrame] = {}
        self._overview_signature: tuple | None = None
        self._overview_reflow_count = 0
        self._detail_layout_signature: tuple[int] | None = None
        self._detail_reflow_count = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        self._header = ChartsHeader(state, resources)
        root.addWidget(self._header)

        self._stack = QStackedWidget()
        self._stack.setObjectName("chartsStack")
        root.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_overview_page())
        self._stack.addWidget(self._build_resource_detail_page())

        self._stock_chart = LineChartWidget(state, ChartSeries("Resource Stock", "resource.iron_ore", Theme.RESOURCE))
        self._production_chart = LineChartWidget(state, ChartSeries("Production Rate", "rate.production.iron_ore", Theme.GOOD))
        self._consumption_chart = LineChartWidget(state, ChartSeries("Consumption Rate", "rate.consumption.iron_ore", Theme.WARN))

        self._detail_charts = (self._stock_chart, self._production_chart, self._consumption_chart)
        self._layout_detail_charts()
        self._refresh_chart_series()
        self._refresh_overview()

    def refresh(self) -> None:
        self._header.refresh()
        self._refresh_overview()
        if self._stack.currentIndex() == 1 and self._selected_resource_id is not None:
            self._refresh_detail_header(self._selected_resource_id)
        for chart in (self._stock_chart, self._production_chart, self._consumption_chart):
            chart.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_overview()
        self._layout_detail_charts()

    def _force_overview_reflow(self) -> None:
        self._overview_signature = None
        self._refresh_overview()

    def _clear_layout_items_only(self, layout) -> None:
        while layout.count():
            layout.takeAt(0)

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        controls = QWidget()
        controls.setObjectName("chartFilterDeck")
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(14, 12, 14, 12)
        control_layout.setSpacing(12)
        self._resource_search = QLineEdit()
        self._resource_search.setObjectName("chartResourceSearch")
        self._resource_search.setPlaceholderText("Search resources...")
        self._resource_search.textChanged.connect(self._refresh_overview)
        self._sort_select = QComboBox(controls)
        self._sort_select.setObjectName("chartSortSelect")
        self._sort_select.addItems(["Name", "Amount", "Fill %", "Net Change"])
        self._sort_select.currentTextChanged.connect(self._refresh_overview)
        self._stage_filter = QComboBox(controls)
        self._stage_filter.setObjectName("chartStageFilter")
        self._stage_filter.addItems(["All", "Extraction", "Processing", "Manufacturing", "Assembly"])
        self._stage_filter.currentTextChanged.connect(self._refresh_overview)
        self._category_filter = QComboBox(controls)
        self._category_filter.setObjectName("chartCategoryFilter")
        self._category_filter.addItems(["All", *sorted({definition.category for definition in self._resources.values() if definition.category})])
        self._category_filter.currentTextChanged.connect(self._refresh_overview)
        self._activity_filter = QComboBox(controls)
        self._activity_filter.setObjectName("chartActivityFilter")
        self._activity_filter.addItems(["All", "Active", "In Stock", "Producing", "Consuming"])
        self._activity_filter.currentTextChanged.connect(self._refresh_overview)
        for combo in (self._stage_filter, self._category_filter, self._activity_filter, self._sort_select):
            combo.hide()
        control_layout.addWidget(self._labeled_control("SEARCH", self._resource_search), 0)
        self._stage_chip_layout = self._add_chip_group(control_layout, "STAGE", self._stage_filter)
        self._category_chip_layout = self._add_chip_group(control_layout, "CATEGORY", self._category_filter)
        self._activity_chip_layout = self._add_chip_group(control_layout, "ACTIVITY", self._activity_filter)
        self._sort_chip_layout = self._add_chip_group(control_layout, "SORT", self._sort_select)
        self._refresh_overview_chip_groups()
        layout.addWidget(ChartFilterScroll(controls, "chartFilterScroll", 1180))

        self._resource_scroll = QScrollArea()
        self._resource_scroll.setObjectName("chartResourceScroll")
        self._resource_scroll.setWidgetResizable(True)
        self._resource_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._resource_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._resource_list = QWidget()
        self._resource_list.setObjectName("chartResourceGrid")
        self._resource_list_layout = QGridLayout(self._resource_list)
        self._resource_list_layout.setContentsMargins(0, 0, 0, 0)
        self._resource_list_layout.setSpacing(10)
        self._resource_scroll.setWidget(self._resource_list)
        layout.addWidget(self._resource_scroll, 1)
        self._resource_tile_cache_host = QWidget(page)
        self._resource_tile_cache_host.setObjectName("chartResourceTileCache")
        self._resource_tile_cache_host.hide()
        self._overview_empty_label = QLabel("NO RESOURCES FOUND\nTry adjusting your search or filters.")
        self._overview_empty_label.setObjectName("chartEmptyState")
        self._overview_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overview_empty_label.hide()
        return page

    def _build_resource_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        controls = QFrame()
        controls.setObjectName("chartDetailHeader")
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(14, 12, 14, 12)
        control_layout.setSpacing(12)
        self._resource_back_button = QPushButton("BACK")
        self._resource_back_button.setObjectName("chartBackButton")
        self._resource_back_button.clicked.connect(self._show_overview)
        self._detail_icon_host = QFrame()
        self._detail_icon_host.setObjectName("chartDetailIconHost")
        self._detail_icon_layout = QHBoxLayout(self._detail_icon_host)
        self._detail_icon_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_title = QLabel("Resource Detail")
        self._detail_title.setObjectName("chartDetailTitle")
        self._detail_amount = QLabel()
        self._detail_amount.setObjectName("chartDetailAmount")
        self._detail_net = QLabel()
        self._detail_net.setObjectName("chartDetailNetChange")
        self._range_select = QComboBox(controls)
        self._range_select.setObjectName("chartRangeSelect")
        self._range_select.addItems(list(TIME_RANGE_SAMPLES))
        self._range_select.setCurrentText("ALL")
        self._range_select.currentTextChanged.connect(self._set_range)
        self._range_select.hide()
        control_layout.addWidget(self._resource_back_button)
        control_layout.addWidget(self._detail_icon_host)
        control_layout.addWidget(self._detail_title)
        control_layout.addWidget(self._detail_amount)
        control_layout.addWidget(self._detail_net)
        control_layout.addStretch(1)
        self._range_chip_layout = self._add_chip_group(control_layout, "RANGE", self._range_select)
        self._refresh_range_chip_group()
        layout.addWidget(controls)
        self._resource_chart_host = QWidget()
        self._resource_chart_host.setObjectName("chartDetailGrid")
        self._resource_chart_layout = QGridLayout(self._resource_chart_host)
        self._resource_chart_layout.setContentsMargins(0, 0, 0, 0)
        self._resource_chart_layout.setSpacing(10)
        layout.addWidget(self._resource_chart_host, 1)
        return page

    def _labeled_control(self, label_text: str, control: QWidget) -> QWidget:
        wrapper = QWidget()
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
        wrapper.setObjectName("chartChipGroup")
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

    def _refresh_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        self._clear_layout(layout)
        current = combo.currentText() or "All"
        for option in [combo.itemText(index) for index in range(combo.count())]:
            chip = QPushButton(option.upper())
            chip.setObjectName("chartFilterChip")
            chip.setProperty("filterGroup", group)
            chip.setProperty("filterValue", option)
            chip.setProperty("active", option == current)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked=False, value=option, target=combo: self._set_chip_filter_value(target, value))
            layout.addWidget(chip)

    def _set_chip_filter_value(self, combo: QComboBox, value: str) -> None:
        if combo.currentText() == value:
            return
        combo.setCurrentText(value)
        self._refresh_overview_chip_groups()
        if combo is self._range_select:
            self._refresh_range_chip_group()

    def _refresh_overview_chip_groups(self) -> None:
        if not hasattr(self, "_stage_chip_layout"):
            return
        self._refresh_chip_group(self._stage_chip_layout, self._stage_filter, self._stage_filter.objectName())
        self._refresh_chip_group(self._category_chip_layout, self._category_filter, self._category_filter.objectName())
        self._refresh_chip_group(self._activity_chip_layout, self._activity_filter, self._activity_filter.objectName())
        self._refresh_chip_group(self._sort_chip_layout, self._sort_select, self._sort_select.objectName())

    def _refresh_range_chip_group(self) -> None:
        if hasattr(self, "_range_chip_layout"):
            self._refresh_chip_group(self._range_chip_layout, self._range_select, self._range_select.objectName())

    def _refresh_overview(self, *args) -> None:
        if not hasattr(self, "_resource_list_layout"):
            return
        self._refresh_overview_chip_groups()
        rows = [definition for definition in self._resources.values() if self._matches_filters(definition)]
        rows = self._sort_resource_definitions(rows)
        columns, tile_width = self._resource_grid_geometry()
        signature = (
            tuple(definition.resource_id for definition in rows),
            self._resource_search.text(),
            self._stage_filter.currentText(),
            self._category_filter.currentText(),
            self._activity_filter.currentText(),
            self._sort_select.currentText(),
            columns,
            tile_width,
        )
        if signature != self._overview_signature:
            self._overview_signature = signature
            self._overview_reflow_count += 1
            self._clear_layout_items_only(self._resource_list_layout)
            self._overview_empty_label.hide()
            self._overview_empty_label.setParent(self._resource_tile_cache_host)
            self._resource_tiles = {}
            for tile in self._resource_tile_pool.values():
                tile.hide()
                tile.setParent(self._resource_tile_cache_host)
            for column in range(12):
                self._resource_list_layout.setColumnMinimumWidth(column, 0)
                self._resource_list_layout.setColumnStretch(column, 0)
            for column in range(columns):
                self._resource_list_layout.setColumnMinimumWidth(column, tile_width)
                self._resource_list_layout.setColumnStretch(column, 1)
            if not rows:
                self._resource_list_layout.addWidget(self._overview_empty_label, 0, 0)
                self._overview_empty_label.show()
            for index, definition in enumerate(rows):
                row_index = index // columns
                column_index = index % columns
                card = self._resource_tile_pool.get(definition.resource_id)
                if card is None:
                    card = self._resource_card(definition, tile_width)
                    self._resource_tile_pool[definition.resource_id] = card
                else:
                    card.setFixedWidth(tile_width)
                card.setProperty("gridRow", row_index)
                card.setProperty("gridColumn", column_index)
                self._resource_tiles[definition.resource_id] = card
                self._resource_list_layout.addWidget(
                    card,
                    row_index,
                    column_index,
                )
                self._update_resource_card(definition, card)
                card.show()
        else:
            for definition in rows:
                self._update_resource_card(definition, self._resource_tiles.get(definition.resource_id))

    def _resource_card(self, definition: ResourceDefinition, tile_width: int) -> QFrame:
        resource_id = definition.resource_id
        card = QFrame()
        card.setObjectName("chartResourceCard")
        card.setProperty("resourceId", resource_id)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda event, selected_resource_id=resource_id: self._show_resource_detail(selected_resource_id)
        card.setFixedWidth(tile_width)
        card.setMinimumHeight(166)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(7)
        top = QHBoxLayout()
        top.setSpacing(10)
        icon_host = QFrame()
        icon_host.setObjectName("chartResourceIconHost")
        icon_host.setFixedSize(58, 58)
        icon_layout = QHBoxLayout(icon_host)
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon = ResourceIconWidget(
            resource_id,
            definition.icon_key or resource_icon_key(resource_id),
            definition.accent_key or resource_accent_key(resource_id),
            size=48,
        )
        icon.setObjectName("resourceIcon")
        icon_layout.addWidget(icon)
        name = QLabel(definition.name)
        name.setObjectName("chartResourceName")
        name.setWordWrap(True)
        name.setMinimumHeight(42)
        top.addWidget(icon_host)
        top.addWidget(name, 1)
        layout.addLayout(top)
        amount = QLabel()
        amount.setObjectName("chartResourceAmount")
        net = QLabel()
        net.setObjectName("chartResourceNetChange")
        meta = QHBoxLayout()
        meta.addWidget(amount)
        meta.addStretch(1)
        meta.addWidget(net)
        layout.addLayout(meta)
        sparkline = SparklineWidget(self._state, f"resource.{resource_id}")
        layout.addWidget(sparkline)
        progress = QProgressBar()
        progress.setObjectName("chartResourceStorageProgress")
        progress.setTextVisible(False)
        progress.setRange(0, 1000)
        layout.addWidget(progress)
        self._update_resource_card(definition, card)
        return card

    def _update_resource_card(self, definition: ResourceDefinition, card: QFrame | None) -> None:
        if card is None:
            return
        resource_id = definition.resource_id
        stock = self._state.resources[resource_id]
        net_change = self._net_change(resource_id)
        status = self._status_for_net_change(net_change)
        card.setProperty("status", status)
        card.style().unpolish(card)
        card.style().polish(card)
        amount = card.findChild(QLabel, "chartResourceAmount")
        net = card.findChild(QLabel, "chartResourceNetChange")
        sparkline = card.findChild(SparklineWidget, "chartResourceSparkline")
        progress = card.findChild(QProgressBar, "chartResourceStorageProgress")
        if amount is not None:
            amount.setText(f"{stock.amount:g} / {stock.capacity:g}")
        if net is not None:
            net.setText(self._format_signed(net_change))
            net.setProperty("status", status)
            net.style().unpolish(net)
            net.style().polish(net)
        if sparkline is not None:
            sparkline.set_metric(f"resource.{resource_id}", self._sparkline_color(status))
        if progress is not None:
            progress.setValue(round(stock.fill_ratio * 1000))

    def _matches_filters(self, definition: ResourceDefinition) -> bool:
        search = self._resource_search.text().strip().lower() if hasattr(self, "_resource_search") else ""
        if search and search not in f"{definition.name} {definition.resource_id}".lower():
            return False
        if self._stage_filter.currentText() not in ("", "All", self._stage_for_resource(definition)):
            return False
        if self._category_filter.currentText() not in ("", "All", definition.category):
            return False
        activity = self._activity_filter.currentText()
        stock = self._state.resources[definition.resource_id]
        net_change = self._net_change(definition.resource_id)
        if activity == "Active":
            return stock.amount > 0 or abs(net_change) > 0.01
        if activity == "In Stock":
            return stock.amount > 0
        if activity == "Producing":
            return net_change > 0.01
        if activity == "Consuming":
            return net_change < -0.01
        return True

    def _sort_resource_definitions(self, rows: list[ResourceDefinition]) -> list[ResourceDefinition]:
        sort = self._sort_select.currentText()
        if sort == "Amount":
            return sorted(rows, key=lambda definition: (-self._state.resources[definition.resource_id].amount, definition.name))
        if sort == "Fill %":
            return sorted(rows, key=lambda definition: (-self._state.resources[definition.resource_id].fill_ratio, definition.name))
        if sort == "Net Change":
            return sorted(rows, key=lambda definition: (-abs(self._net_change(definition.resource_id)), definition.name))
        return sorted(rows, key=lambda definition: definition.name)

    def _stage_for_resource(self, definition: ResourceDefinition) -> str:
        category = definition.category.lower()
        if any(token in category for token in ("ore", "mineral", "oil", "gas", "agriculture", "forestry")):
            return "Extraction"
        if any(token in category for token in ("processed", "metal", "chemical", "material")):
            return "Processing"
        if any(token in category for token in ("component", "electronics", "vehicle", "medical")):
            return "Manufacturing"
        if any(token in category for token in ("assembly", "aerospace", "space", "telecom")):
            return "Assembly"
        return "Processing"

    def _resource_grid_columns(self) -> int:
        return self._resource_grid_geometry()[0]

    def _layout_detail_charts(self) -> None:
        if not hasattr(self, "_resource_chart_layout") or not hasattr(self, "_detail_charts"):
            return
        columns = self._detail_chart_columns()
        signature = (columns,)
        if signature == self._detail_layout_signature:
            return
        self._detail_layout_signature = signature
        self._detail_reflow_count += 1
        self._clear_layout_items_only(self._resource_chart_layout)
        for column in range(3):
            self._resource_chart_layout.setColumnStretch(column, 1 if column < columns else 0)
            self._resource_chart_layout.setColumnMinimumWidth(column, 0)
        for index, chart in enumerate(self._detail_charts):
            row = index // columns
            column = index % columns
            chart.setProperty("detailGridRow", row)
            chart.setProperty("detailGridColumn", column)
            chart.setMinimumHeight(240)
            chart.setMinimumWidth(0)
            chart.setMaximumWidth(16_777_215)
            chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self._resource_chart_layout.addWidget(chart, row, column)

    def _detail_chart_columns(self) -> int:
        width = self._detail_view_width()
        if width >= 1200:
            return 3
        elif width >= 760:
            return 2
        return 1

    def _detail_view_width(self) -> int:
        if hasattr(self, "_stack"):
            stack_width = self._stack.width()
            if stack_width > 100:
                return stack_width
        if hasattr(self, "_resource_chart_host"):
            host_width = self._resource_chart_host.width()
            if host_width > 100:
                return host_width
        width = self.width()
        return width if width > 0 else 1200

    def _resource_grid_geometry(self) -> tuple[int, int]:
        available_width = self._resource_viewport_width()
        if available_width >= 1400:
            columns = 4
        elif available_width >= 1050:
            columns = 3
        elif available_width >= 700:
            columns = 2
        else:
            columns = 1
        spacing = max(0, self._resource_list_layout.spacing() if hasattr(self, "_resource_list_layout") else 10)
        total_spacing = spacing * (columns - 1)
        tile_width = max(190, (available_width - total_spacing) // columns)
        return columns, tile_width

    def _resource_viewport_width(self) -> int:
        if hasattr(self, "_resource_scroll"):
            viewport_width = self._resource_scroll.viewport().width()
            if viewport_width > 100:
                return viewport_width
            scroll_width = self._resource_scroll.width()
            if scroll_width > 100:
                return scroll_width
        width = self.width()
        return width if width > 0 else 1400

    def _net_change(self, resource_id: str) -> float:
        production = self._last_value(f"rate.production.{resource_id}")
        consumption = self._last_value(f"rate.consumption.{resource_id}")
        return production - consumption

    def _last_value(self, metric_id: str) -> float:
        values = self._state.history.values_for(metric_id)
        return values[-1] if values else 0.0

    def _status_for_net_change(self, value: float) -> str:
        if value > 0.01:
            return "rising"
        if value < -0.01:
            return "falling"
        return "neutral"

    def _format_signed(self, value: float) -> str:
        return f"{value:+.1f}"

    def _sparkline_color(self, status: str) -> str:
        if status == "rising":
            return Theme.GOOD
        if status == "falling":
            return Theme.BAD
        return Theme.RESOURCE

    def _show_overview(self) -> None:
        self._stack.setCurrentIndex(0)
        self._refresh_overview()

    def _show_resource_detail(self, resource_id: str) -> None:
        self._selected_resource_id = resource_id
        self._refresh_chart_series()
        self._stack.setCurrentIndex(1)
        self._layout_detail_charts()

    def _set_range(self, range_id: str) -> None:
        for chart in (self._stock_chart, self._production_chart, self._consumption_chart):
            chart.set_range(range_id)
        self._refresh_range_chip_group()

    def _refresh_chart_series(self) -> None:
        resource_id = self._selected_resource_id or next(iter(self._resources), "iron_ore")
        name = self._resources[resource_id].name if resource_id in self._resources else resource_id.replace("_", " ").title()
        if hasattr(self, "_detail_title"):
            self._detail_title.setText(name)
            self._refresh_detail_header(resource_id)
        self._stock_chart.set_series(ChartSeries(f"{name} Stock", f"resource.{resource_id}", Theme.RESOURCE))
        self._production_chart.set_series(ChartSeries(f"{name} Production Rate", f"rate.production.{resource_id}", Theme.GOOD))
        self._consumption_chart.set_series(ChartSeries(f"{name} Consumption Rate", f"rate.consumption.{resource_id}", Theme.WARN))

    def _refresh_detail_header(self, resource_id: str) -> None:
        definition = self._resources.get(resource_id)
        stock = self._state.resources[resource_id]
        net_change = self._net_change(resource_id)
        self._detail_amount.setText(f"{stock.amount:g} / {stock.capacity:g}")
        self._detail_net.setText(f"{self._format_signed(net_change)} / min")
        self._detail_net.setProperty("status", self._status_for_net_change(net_change))
        self._detail_net.style().unpolish(self._detail_net)
        self._detail_net.style().polish(self._detail_net)
        self._clear_layout(self._detail_icon_layout)
        if definition is not None:
            self._detail_icon_layout.addWidget(
                ResourceIconWidget(
                    resource_id,
                    definition.icon_key or resource_icon_key(resource_id),
                    definition.accent_key or resource_accent_key(resource_id),
                    size=36,
                )
            )

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)
