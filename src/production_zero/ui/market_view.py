from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, QPointF, QRectF, QSize, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QStackedWidget,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from production_zero.core.market import active_market_event, remaining_event_seconds
from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.game_ui import Accent, GAME_UI_TOKENS, MaterialLevel, draw_game_panel, draw_inset_surface, draw_track_surface
from production_zero.ui.resource_icons import ResourceIconWidget, resource_accent_color, resource_accent_key, resource_icon_key
from production_zero.ui.theme import Theme
from production_zero.ui.widget_lifecycle import clear_layout_safely


MARKET_PERIOD_SAMPLES: dict[str, int | None] = {
    "24H": 288,
    "7D": 2_016,
    "30D": 8_640,
    "90D": 25_920,
    "ALL": None,
}

MARKET_COLUMNS = ("RESOURCE", "PRICE", "24H", "7D", "30D", "TREND", "ANCHOR", "EVENT")


class PriceSparkline(QWidget):
    def __init__(self, state: GameState, resource_id: str, title: str | None = None, range_id: str = "24H") -> None:
        super().__init__()
        self._state = state
        self._resource_id = resource_id
        self._title = title
        self._range_id = range_id
        self._last_y_range: tuple[float, float] = (0.0, 1.0)
        self._axes_drawn = False
        self.setObjectName("marketSparkline")
        self.setMinimumSize(110, 28)

    def set_resource(self, resource_id: str, title: str | None = None) -> None:
        self._resource_id = resource_id
        self._title = title
        self.update()

    def set_range(self, range_id: str) -> None:
        self._range_id = range_id
        self.update()

    def _visible_values(self) -> tuple[float, ...]:
        values = self._state.history.values_for(f"market.price.{self._resource_id}")
        sample_count = MARKET_PERIOD_SAMPLES.get(self._range_id)
        if sample_count is not None:
            values = values[-sample_count:]
        state = self._state.market.ensure_resource(self._resource_id)
        if len(values) < 2:
            values = (state.current_price - state.last_change, state.current_price)
        return values

    def _scaled_y_range(self, values: tuple[float, ...]) -> tuple[float, float]:
        state = self._state.market.ensure_resource(self._resource_id)
        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum
        if span <= 0.0001:
            padding = max(1.0, abs(state.current_price) * 0.03)
            return state.current_price - padding, state.current_price + padding
        padding = span * 0.08
        return minimum - padding, maximum + padding

    def _x_label(self, index: int, count: int) -> str:
        if self._range_id == "24H":
            return "Now" if index == count - 1 else f"-{count - index - 1}t"
        if self._range_id in ("7D", "30D", "90D"):
            return "Now" if index == count - 1 else f"-{count - index - 1}"
        return "Now" if index == count - 1 else "Past"

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(0, 0, self.width(), self.height()).adjusted(2, 2, -2, -2)
            detailed = self.objectName() == "marketDetailChart"
            if detailed:
                draw_game_panel(painter, rect, accent=Accent.CASH, level=MaterialLevel.INSET, radius=10)
            values = self._visible_values()
            y_min, y_max = self._scaled_y_range(values)
            self._last_y_range = (y_min, y_max)
            span = y_max - y_min or 1.0
            plot = rect.adjusted(58 if detailed else 0, 34 if self._title else 0, -14 if detailed else 0, -32 if detailed else 0)
            if detailed:
                draw_inset_surface(painter, plot.adjusted(-8, -7, 8, 8), accent=Accent.CASH, radius=7)
            if self._title:
                painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_secondary))
                painter.setFont(GAME_UI_TOKENS.typography.industrial_label())
                painter.drawText(rect.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, self._title.upper())
            if detailed:
                self._axes_drawn = True
                painter.setPen(QPen(QColor(Theme.GRID), 1))
                for step in range(5):
                    y = plot.top() + plot.height() * step / 4
                    painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
                    value = y_max - (span * step / 4)
                    painter.setPen(QColor(Theme.MUTED))
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(QRectF(rect.left(), y - 8, 50, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"${value:.2f}")
                    painter.setPen(QPen(QColor(Theme.GRID), 1))
                for step in range(4):
                    x = plot.left() + plot.width() * step / 3
                    painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
                    value_index = round((len(values) - 1) * step / 3)
                    painter.setPen(QColor(Theme.MUTED))
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.drawText(QRectF(x - 30, plot.bottom() + 6, 60, 16), Qt.AlignmentFlag.AlignCenter, self._x_label(value_index, len(values)))
                    painter.setPen(QPen(QColor(Theme.GRID), 1))
                painter.setPen(QPen(QColor(Theme.BORDER), 1.2))
                painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))
                painter.drawLine(QPointF(plot.left(), plot.top()), QPointF(plot.left(), plot.bottom()))
                anchor = self._state.market.ensure_resource(self._resource_id).anchor_price
                if y_min <= anchor <= y_max:
                    y = plot.bottom() - ((anchor - y_min) / span * plot.height())
                    pen = QPen(QColor(Theme.ENERGY), 1)
                    pen.setStyle(Qt.PenStyle.DashLine)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
                    painter.setPen(QColor(Theme.ENERGY))
                    painter.drawText(QRectF(plot.right() - 62, y - 16, 58, 14), Qt.AlignmentFlag.AlignRight, "ANCHOR")
            raw_values = self._state.history.values_for(f"market.price.{self._resource_id}")
            state = self._state.market.ensure_resource(self._resource_id)
            if detailed and len(raw_values) < 2 and abs(state.last_change) <= 0.001:
                painter.setPen(GAME_UI_TOKENS.colors.qcolor(GAME_UI_TOKENS.colors.text_muted))
                painter.setFont(GAME_UI_TOKENS.typography.status_label())
                painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "NO DATA YET")
                return
            points = [
                QPointF(
                    plot.left() + plot.width() * index / (len(values) - 1),
                    plot.bottom() - ((value - y_min) / span * plot.height()),
                )
                for index, value in enumerate(values)
            ]
            color = Theme.GOOD if values[-1] >= values[0] else Theme.BAD
            painter.setPen(QPen(QColor(color), 2.2 if detailed else 1.5))
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)
        finally:
            painter.end()


class MarketTableModel(QAbstractTableModel):
    def __init__(self, state: GameState, resources: dict[str, ResourceDefinition]) -> None:
        super().__init__()
        self._state = state
        self._resources = resources
        self._resource_ids = [resource_id for resource_id in resources if resource_id in state.market.resources]
        self._timeframe = "24H"

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._resource_ids)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(MARKET_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return MARKET_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        resource_id = self.resource_id_at(index.row())
        definition = self._resources[resource_id]
        market = self._state.market.ensure_resource(resource_id)
        column = index.column()
        if role == Qt.ItemDataRole.UserRole:
            return resource_id
        if role == Qt.ItemDataRole.UserRole + 1:
            return self._stage_for_resource(definition)
        if role == Qt.ItemDataRole.UserRole + 2:
            return definition.category
        if role == Qt.ItemDataRole.UserRole + 3:
            return resource_id in active_market_event(self._state.market).affected_resources
        if role == Qt.ItemDataRole.UserRole + 4:
            return self._change_status(self.period_change(resource_id, self._timeframe))
        if role == Qt.ItemDataRole.UserRole + 5:
            return definition.name
        if role == Qt.ItemDataRole.UserRole + 6:
            return resource_icon_key(resource_id), resource_accent_key(resource_id)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignLeft if column == 0 else Qt.AlignmentFlag.AlignRight)
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if column == 0:
            return definition.name
        if column == 1:
            return f"${market.current_price:.2f}"
        if column == 2:
            return self.format_change(resource_id, "24H")
        if column == 3:
            return self.format_change(resource_id, "7D")
        if column == 4:
            return self.format_change(resource_id, "30D")
        if column == 5:
            return self.trend_label(self._change_status(self.period_change(resource_id, self._timeframe)))
        if column == 6:
            return f"${market.anchor_price:.2f}"
        if column == 7:
            return active_market_event(self._state.market).name if resource_id in active_market_event(self._state.market).affected_resources else ""
        return ""

    def resource_id_at(self, row: int) -> str:
        return self._resource_ids[row]

    def set_timeframe(self, timeframe: str) -> None:
        if timeframe == self._timeframe:
            return
        self._timeframe = timeframe
        self.emit_all_changed()

    def emit_all_changed(self) -> None:
        if not self._resource_ids:
            return
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(len(self._resource_ids) - 1, len(MARKET_COLUMNS) - 1),
            [],
        )

    def period_values(self, resource_id: str, period: str) -> tuple[float, ...]:
        values = self._state.history.values_for(f"market.price.{resource_id}")
        sample_count = MARKET_PERIOD_SAMPLES.get(period)
        if sample_count is None:
            return values
        return values[-sample_count:]

    def period_change(self, resource_id: str, period: str) -> float:
        market = self._state.market.ensure_resource(resource_id)
        values = self.period_values(resource_id, period)
        if len(values) >= 2:
            return market.current_price - values[0]
        if period == "24H":
            return market.last_change
        return 0.0

    def period_stats(self, resource_id: str, period: str) -> tuple[float, float, float]:
        market = self._state.market.ensure_resource(resource_id)
        values = self.period_values(resource_id, period)
        if not values:
            values = (market.current_price,)
        return max(values), min(values), sum(values) / len(values)

    def change_percent_for_delta(self, resource_id: str, delta: float) -> float:
        market = self._state.market.ensure_resource(resource_id)
        previous = market.current_price - delta
        if previous == 0:
            return 0.0
        return delta / previous * 100.0

    def format_change(self, resource_id: str, period: str) -> str:
        delta = self.period_change(resource_id, period)
        percent = self.change_percent_for_delta(resource_id, delta)
        if abs(delta) <= 0.001:
            return f"0.00 ({abs(percent):.1f}%)"
        return f"{delta:+.2f} ({percent:+.1f}%)"

    def trend_label(self, status: str) -> str:
        if status == "positive":
            return "Rising"
        if status == "negative":
            return "Falling"
        return "Neutral"

    def _change_status(self, change: float) -> str:
        if change > 0.001:
            return "positive"
        if change < -0.001:
            return "negative"
        return "neutral"

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


class MarketFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, model: MarketTableModel) -> None:
        super().__init__()
        self._model = model
        self.search = ""
        self.stage = "All"
        self.category = "All"
        self.event_filter = "All"
        self.trend = "All"
        self.setSourceModel(model)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        index = self._model.index(source_row, 0, source_parent)
        resource_id = self._model.data(index, Qt.ItemDataRole.UserRole)
        name = self._model.data(index, Qt.ItemDataRole.UserRole + 5)
        if self.search and self.search not in f"{name} {resource_id}".lower():
            return False
        if self.stage not in ("", "All", self._model.data(index, Qt.ItemDataRole.UserRole + 1)):
            return False
        if self.category not in ("", "All", self._model.data(index, Qt.ItemDataRole.UserRole + 2)):
            return False
        affected = self._model.data(index, Qt.ItemDataRole.UserRole + 3)
        if self.event_filter == "Event Affected" and not affected:
            return False
        if self.event_filter == "No Active Event" and affected:
            return False
        status = self._model.data(index, Qt.ItemDataRole.UserRole + 4)
        if self.trend == "Rising" and status != "positive":
            return False
        if self.trend == "Falling" and status != "negative":
            return False
        if self.trend == "Neutral" and status != "neutral":
            return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        left_resource = self._model.resource_id_at(left.row())
        right_resource = self._model.resource_id_at(right.row())
        column = left.column()
        if column == 1:
            return self._model._state.market.ensure_resource(left_resource).current_price < self._model._state.market.ensure_resource(right_resource).current_price
        if column == 2:
            return self._model.period_change(left_resource, "24H") < self._model.period_change(right_resource, "24H")
        if column == 3:
            return self._model.period_change(left_resource, "7D") < self._model.period_change(right_resource, "7D")
        if column == 4:
            return self._model.period_change(left_resource, "30D") < self._model.period_change(right_resource, "30D")
        return self._model._resources[left_resource].name < self._model._resources[right_resource].name


class MarketTableDelegate(QStyledItemDelegate):
    def __init__(self, model: MarketTableModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._icon_cache: dict[str, QPixmap] = {}

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:  # noqa: N802
        return QSize(96, 64)

    def _resource_icon(self, resource_id: str) -> QPixmap:
        pixmap = self._icon_cache.get(resource_id)
        if pixmap is not None:
            return pixmap
        pixmap = QPixmap(30, 30)
        pixmap.fill(Qt.GlobalColor.transparent)
        widget = ResourceIconWidget(resource_id, resource_icon_key(resource_id), resource_accent_key(resource_id), size=30)
        widget.render(pixmap)
        self._icon_cache[resource_id] = pixmap
        return pixmap

    def _elided(self, painter: QPainter, text: str, width: int) -> str:
        return QFontMetrics(painter.font()).elidedText(text, Qt.TextElideMode.ElideRight, max(12, width))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        try:
            source_index = index.model().mapToSource(index) if hasattr(index.model(), "mapToSource") else index
            resource_id = self._model.data(source_index, Qt.ItemDataRole.UserRole)
            rect = QRectF(option.rect)
            hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
            selected = bool(option.state & QStyle.StateFlag.State_Selected)
            row_rect = rect.adjusted(4, 4, -4, -4)
            if source_index.column() == 0:
                row_fill = QLinearGradient(row_rect.topLeft(), row_rect.bottomLeft())
                row_fill.setColorAt(0.0, QColor(35, 42, 41, 226 if not hovered else 242))
                row_fill.setColorAt(0.54, QColor(13, 19, 19, 236 if not hovered else 250))
                row_fill.setColorAt(1.0, QColor(5, 8, 8, 248))
                painter.setPen(QPen(QColor(142, 154, 150, 84 if not selected else 132), 1))
                painter.setBrush(row_fill)
                painter.drawRoundedRect(row_rect.adjusted(0, 0, len(MARKET_COLUMNS) * 120, 0), 7, 7)
            if source_index.column() == 0:
                icon_shell = QRectF(rect.left() + 11, rect.center().y() - 22, 44, 44)
                painter.setPen(QPen(QColor(255, 210, 31, 70), 1))
                painter.setBrush(QColor(255, 255, 255, 9))
                painter.drawRoundedRect(icon_shell, 6, 6)
                icon_rect = QRectF(icon_shell.left() + 7, icon_shell.top() + 7, 30, 30)
                painter.drawPixmap(icon_rect.toRect(), self._resource_icon(resource_id))
                name_rect = rect.adjusted(66, 9, -8, -32)
                meta_rect = rect.adjusted(66, 32, -8, -7)
                painter.setPen(QColor(Theme.TEXT))
                painter.setFont(GAME_UI_TOKENS.typography.card_title())
                painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._elided(painter, str(self._model.data(source_index, Qt.ItemDataRole.DisplayRole) or ""), int(name_rect.width())))
                category = self._model.data(source_index, Qt.ItemDataRole.UserRole + 2) or self._model.data(source_index, Qt.ItemDataRole.UserRole + 1)
                painter.setPen(QColor(Theme.MUTED))
                painter.setFont(GAME_UI_TOKENS.typography.micro_label())
                painter.drawText(meta_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._elided(painter, str(category), int(meta_rect.width())))
                painter.setPen(QPen(QColor(132, 151, 145, 38), 1))
                painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
                return
            else:
                text_rect = rect.adjusted(10, 0, -10, 0)
            text = str(self._model.data(source_index, Qt.ItemDataRole.DisplayRole) or "")
            color = Theme.TEXT if source_index.column() in (0, 1) else Theme.MUTED
            if source_index.column() in (2, 3, 4):
                period = ("24H", "7D", "30D")[source_index.column() - 2]
                status = self._model._change_status(self._model.period_change(resource_id, period))
                color = Theme.GOOD if status == "positive" else Theme.BAD if status == "negative" else Theme.MUTED
            if source_index.column() == 5:
                status = self._model.data(source_index, Qt.ItemDataRole.UserRole + 4)
                color = Theme.GOOD if status == "positive" else Theme.BAD if status == "negative" else Theme.MUTED
            if source_index.column() == 7 and text:
                color = Theme.ENERGY
            if source_index.column() == 5:
                pill_rect = rect.adjusted(12, 13, -10, -13)
                status = self._model.data(source_index, Qt.ItemDataRole.UserRole + 4)
                base = QColor(Theme.GOOD if status == "positive" else Theme.BAD if status == "negative" else Theme.MUTED)
                painter.setPen(QPen(QColor(base.red(), base.green(), base.blue(), 130), 1))
                painter.setBrush(QColor(base.red(), base.green(), base.blue(), 30))
                painter.drawRoundedRect(pill_rect, 7, 7)
                painter.setPen(base)
                painter.setFont(GAME_UI_TOKENS.typography.status_label())
                painter.drawText(pill_rect.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignCenter, self._elided(painter, text, int(pill_rect.width() - 12)))
                painter.setPen(QPen(QColor(132, 151, 145, 38), 1))
                painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
                return
            painter.setPen(QColor(color))
            painter.setFont(GAME_UI_TOKENS.typography.status_label() if source_index.column() != 1 else GAME_UI_TOKENS.typography.section_title())
            alignment = Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignLeft if source_index.column() == 0 else Qt.AlignmentFlag.AlignRight)
            painter.drawText(text_rect, alignment, self._elided(painter, text, int(text_rect.width())))
            painter.setPen(QPen(QColor(132, 151, 145, 38), 1))
            painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
        finally:
            painter.restore()


class MarketHeader(QFrame):
    def __init__(self, state: GameState) -> None:
        super().__init__()
        self._state = state
        self.setObjectName("marketHeader")
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 25, 32, 24)
        layout.setSpacing(18)
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(1)
        title = QLabel("MARKET")
        title.setObjectName("marketHeroTitle")
        subtitle = QLabel("RESOURCE EXCHANGE / PRICING")
        subtitle.setObjectName("marketHeroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        layout.addLayout(title_column, 1)
        self._event_value = self._metric("ACTIVE EVENT", "")
        self._remaining_value = self._metric("REMAINING", "")
        layout.addWidget(self._event_value[0])
        layout.addWidget(self._remaining_value[0])
        self.refresh()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=16)
        inset = rect.adjusted(14, 13, -14, -13)
        draw_track_surface(painter, inset, accent=Accent.CASH, radius=11)
        painter.end()
        super().paintEvent(event)

    def refresh(self) -> None:
        event = active_market_event(self._state.market)
        remaining = remaining_event_seconds(self._state.market)
        days = int(remaining // 86_400)
        hours = int((remaining % 86_400) // 3_600)
        self._event_value[1].setText(event.name.upper())
        self._remaining_value[1].setText(f"{days}D {hours}H")

    def _metric(self, label_text: str, value_text: str) -> tuple[QFrame, QLabel]:
        tile = QFrame()
        tile.setObjectName("marketHeaderMetric")
        tile.setMinimumSize(160, 58)
        tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        label = QLabel(label_text)
        label.setObjectName("marketMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("marketMetricValue")
        layout.addWidget(label)
        layout.addWidget(value)
        return tile, value


class MarketFilterScroll(QScrollArea):
    def __init__(self, content: QWidget, object_name: str, preferred_width: int = 1240) -> None:
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


class MarketView(QWidget):
    def __init__(self, state: GameState, resources: dict[str, ResourceDefinition]) -> None:
        super().__init__()
        self._state = state
        self._resources = resources
        self._selected_resource_id: str | None = None
        self._table_model = MarketTableModel(state, resources)
        self._proxy_model = MarketFilterProxyModel(self._table_model)
        self._structural_refresh_count = 0
        self._selector_buttons: dict[QComboBox, QPushButton] = {}
        self._selector_flyouts: dict[QComboBox, QFrame] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._header = MarketHeader(state)
        layout.addWidget(self._header)

        self._stack = QStackedWidget()
        self._stack.setObjectName("marketStack")
        layout.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_overview_page())
        self._stack.addWidget(self._build_detail_page())
        self.refresh()

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._event_panel = QFrame()
        self._event_panel.setObjectName("marketEventPanel")
        self._event_layout = QHBoxLayout(self._event_panel)
        self._event_layout.setContentsMargins(14, 12, 14, 12)
        self._event_layout.setSpacing(14)
        layout.addWidget(self._event_panel)

        controls = QWidget()
        controls.setObjectName("marketFilterDeck")
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(14, 12, 14, 12)
        control_layout.setSpacing(12)
        self._search = QLineEdit()
        self._search.setObjectName("marketSearch")
        self._search.setPlaceholderText("Search market...")
        self._search.textChanged.connect(self._refresh_market_rows)
        self._stage_filter = QComboBox(controls)
        self._stage_filter.setObjectName("marketStageFilter")
        self._stage_filter.addItems(["All", "Extraction", "Processing", "Manufacturing", "Assembly"])
        self._stage_filter.currentTextChanged.connect(self._refresh_market_rows)
        self._category_filter = QComboBox(controls)
        self._category_filter.setObjectName("marketCategoryFilter")
        self._category_filter.addItems(["All", *sorted({definition.category for definition in self._resources.values() if definition.category})])
        self._category_filter.currentTextChanged.connect(self._refresh_market_rows)
        self._event_filter = QComboBox(controls)
        self._event_filter.setObjectName("marketEventFilter")
        self._event_filter.addItems(["All", "Event Affected", "No Active Event"])
        self._event_filter.currentTextChanged.connect(self._refresh_market_rows)
        self._trend_filter = QComboBox(controls)
        self._trend_filter.setObjectName("marketTrendFilter")
        self._trend_filter.addItems(["All", "Rising", "Falling", "Neutral"])
        self._trend_filter.currentTextChanged.connect(self._refresh_market_rows)
        self._sort = QComboBox(controls)
        self._sort.setObjectName("marketSortSelect")
        self._sort.addItems(["Name", "Price", "24h Change", "7d Change", "30d Change"])
        self._sort.currentTextChanged.connect(self._refresh_market_rows)
        self._timeframe = QComboBox(controls)
        self._timeframe.setObjectName("marketTimeframeSelect")
        self._timeframe.addItems(["24H", "7D", "30D", "90D"])
        self._timeframe.currentTextChanged.connect(self._refresh_market_rows)
        for combo in (self._stage_filter, self._category_filter, self._event_filter, self._trend_filter, self._sort, self._timeframe):
            combo.hide()
        self._search.setFixedWidth(220)
        control_layout.addWidget(self._labeled_control("SEARCH", self._search), 0)
        self._stage_chip_layout = self._add_chip_group(control_layout, "STAGE", self._stage_filter)
        self._add_selector_group(control_layout, "CATEGORY", self._category_filter, "marketCategorySelectorButton")
        self._event_chip_layout = self._add_chip_group(control_layout, "EVENT", self._event_filter)
        self._trend_chip_layout = self._add_chip_group(control_layout, "TREND", self._trend_filter)
        control_layout.addStretch(1)
        self._add_selector_group(control_layout, "SORT", self._sort, "marketSortSelectorButton")
        self._timeframe_chip_layout = self._add_chip_group(control_layout, "RANGE", self._timeframe)
        self._refresh_overview_chip_groups()
        layout.addWidget(MarketFilterScroll(controls, "marketFilterScroll", 1240))

        self._market_table = QTableView()
        self._market_table.setObjectName("marketTableView")
        self._market_table.setModel(self._proxy_model)
        self._market_table.setItemDelegate(MarketTableDelegate(self._table_model, self._market_table))
        self._market_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._market_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._market_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._market_table.setShowGrid(False)
        self._market_table.setAlternatingRowColors(False)
        self._market_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._market_table.setSortingEnabled(False)
        self._market_table.setWordWrap(False)
        self._market_table.verticalHeader().hide()
        self._market_table.verticalHeader().setDefaultSectionSize(50)
        self._market_table.horizontalHeader().setFixedHeight(34)
        self._market_table.horizontalHeader().setStretchLastSection(False)
        self._market_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(MARKET_COLUMNS)):
            self._market_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._market_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._market_table.setMouseTracking(True)
        self._market_table.clicked.connect(self._on_table_row_clicked)
        layout.addWidget(self._market_table, 1)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("marketDetailHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(12)
        self._back_button = QPushButton("BACK")
        self._back_button.setObjectName("marketBackButton")
        self._back_button.clicked.connect(self._show_overview)
        self._detail_icon_host = QFrame()
        self._detail_icon_host.setObjectName("marketDetailIconHost")
        self._detail_icon_layout = QHBoxLayout(self._detail_icon_host)
        self._detail_icon_layout.setContentsMargins(0, 0, 0, 0)
        self._detail_title = QLabel("Resource Market Detail")
        self._detail_title.setObjectName("marketDetailTitle")
        self._detail_price = QLabel()
        self._detail_price.setObjectName("marketDetailPrice")
        self._detail_change = QLabel()
        self._detail_change.setObjectName("marketDetailChange")
        self._detail_range = QComboBox(header)
        self._detail_range.setObjectName("marketDetailRangeSelect")
        self._detail_range.addItems(["24H", "7D", "30D", "90D", "ALL"])
        self._detail_range.currentTextChanged.connect(self._refresh_detail)
        self._detail_range.hide()
        header_layout.addWidget(self._back_button)
        header_layout.addWidget(self._detail_icon_host)
        header_layout.addWidget(self._detail_title)
        header_layout.addWidget(self._detail_price)
        header_layout.addWidget(self._detail_change)
        header_layout.addStretch(1)
        self._detail_range_chip_layout = self._add_chip_group(header_layout, "RANGE", self._detail_range)
        self._refresh_detail_range_chip_group()
        layout.addWidget(header)

        self._detail_summary = QFrame()
        self._detail_summary.setObjectName("marketDetailSummary")
        self._detail_summary_layout = QGridLayout(self._detail_summary)
        self._detail_summary_layout.setContentsMargins(12, 12, 12, 12)
        self._detail_summary_layout.setHorizontalSpacing(18)
        self._detail_summary_layout.setVerticalSpacing(6)
        self._detail_stats: dict[str, QLabel] = {}
        for index, key in enumerate(("ANCHOR PRICE", "ACTIVE EVENT", "PERIOD HIGH", "PERIOD LOW", "PERIOD AVERAGE", "PERIOD CHANGE")):
            label = QLabel(key)
            label.setObjectName("marketDetailMetricLabel")
            value = QLabel()
            value.setObjectName("marketDetailMetric")
            row = index // 3
            column = (index % 3) * 2
            self._detail_summary_layout.addWidget(label, row, column)
            self._detail_summary_layout.addWidget(value, row, column + 1)
            self._detail_stats[key] = value
        layout.addWidget(self._detail_summary)

        self._detail_chart_panel = QFrame()
        self._detail_chart_panel.setObjectName("marketChartPanel")
        chart_layout = QVBoxLayout(self._detail_chart_panel)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        chart_layout.setSpacing(8)
        self._detail_chart = PriceSparkline(self._state, "iron_ore", "Price History")
        self._detail_chart.setObjectName("marketDetailChart")
        self._detail_chart.setMinimumHeight(220)
        chart_layout.addWidget(self._detail_chart, 1)
        layout.addWidget(self._detail_chart_panel, 1)
        return page

    def refresh(self) -> None:
        self._header.refresh()
        self._refresh_event_panel()
        self._refresh_market_rows()
        if self._selected_resource_id is not None:
            self._refresh_detail()

    def _refresh_event_panel(self) -> None:
        if not hasattr(self, "_event_layout"):
            return
        self._clear_layout(self._event_layout)
        event = active_market_event(self._state.market)
        remaining = remaining_event_seconds(self._state.market)
        days = int(remaining // 86_400)
        hours = int((remaining % 86_400) // 3_600)
        affected = " · ".join(resource.replace("_", " ").title() for resource in event.affected_resources)
        name = QLabel(event.name)
        name.setObjectName("marketEventName")
        affected_label = QLabel(f"Affected: {affected}")
        affected_label.setObjectName("marketEventAffected")
        remaining_label = QLabel(f"Remaining: {days}d {hours}h")
        remaining_label.setObjectName("marketEventRemaining")
        self._event_layout.addWidget(name)
        self._event_layout.addWidget(affected_label, 1)
        self._event_layout.addWidget(remaining_label)

    def _refresh_market_rows(self, *args) -> None:
        if not hasattr(self, "_market_table"):
            return
        self._refresh_overview_chip_groups()
        old_filter = (
            self._proxy_model.search,
            self._proxy_model.stage,
            self._proxy_model.category,
            self._proxy_model.event_filter,
            self._proxy_model.trend,
            self._timeframe.currentText(),
        )
        new_filter = (
            self._search.text().strip().lower(),
            self._stage_filter.currentText(),
            self._category_filter.currentText(),
            self._event_filter.currentText(),
            self._trend_filter.currentText(),
            self._timeframe.currentText(),
        )
        self._proxy_model.search = new_filter[0]
        self._proxy_model.stage = new_filter[1]
        self._proxy_model.category = new_filter[2]
        self._proxy_model.event_filter = new_filter[3]
        self._proxy_model.trend = new_filter[4]
        self._table_model.set_timeframe(new_filter[5])
        if new_filter != old_filter:
            self._proxy_model.invalidate()
        self._apply_market_sort()
        self._table_model.emit_all_changed()

    def _add_chip_group(self, parent_layout: QHBoxLayout, label_text: str, combo: QComboBox) -> QHBoxLayout:
        wrapper = QWidget()
        wrapper.setObjectName("marketChipGroup")
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

    def _add_selector_group(self, parent_layout: QHBoxLayout, label_text: str, combo: QComboBox, object_name: str) -> None:
        wrapper = QWidget()
        wrapper.setObjectName("marketSelectorGroup")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("sectionLabel")
        button = QPushButton(self._selector_text(combo))
        button.setObjectName(object_name)
        button.setProperty("selectorFor", combo.objectName())
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumWidth(108)
        button.clicked.connect(lambda checked=False, target=combo, anchor=button: self._toggle_selector_flyout(target, anchor))
        layout.addWidget(label)
        layout.addWidget(button)
        parent_layout.addWidget(wrapper)
        self._selector_buttons[combo] = button
        self._selector_flyouts[combo] = self._build_selector_flyout(combo, button)

    def _build_selector_flyout(self, combo: QComboBox, anchor: QPushButton) -> QFrame:
        flyout = QFrame(self)
        flyout.setObjectName("marketSelectorFlyout")
        flyout.setProperty("selectorFor", combo.objectName())
        flyout.hide()
        layout = QVBoxLayout(flyout)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        for option in [combo.itemText(index) for index in range(combo.count())]:
            item = QPushButton(option.upper())
            item.setObjectName("marketSelectorOption")
            item.setProperty("filterGroup", combo.objectName())
            item.setProperty("filterValue", option)
            item.setCursor(Qt.CursorShape.PointingHandCursor)
            item.clicked.connect(lambda checked=False, value=option, target=combo: self._select_flyout_value(target, value))
            layout.addWidget(item)
        flyout.adjustSize()
        return flyout

    def _toggle_selector_flyout(self, combo: QComboBox, anchor: QPushButton) -> None:
        flyout = self._selector_flyouts[combo]
        if flyout.isVisible():
            flyout.hide()
            return
        for other in self._selector_flyouts.values():
            other.hide()
        self._refresh_selector_flyout(combo)
        global_pos = anchor.mapTo(self, QPoint(0, anchor.height() + 4))
        flyout.move(global_pos)
        flyout.resize(max(anchor.width(), flyout.sizeHint().width()), flyout.sizeHint().height())
        flyout.raise_()
        flyout.show()

    def _select_flyout_value(self, combo: QComboBox, value: str) -> None:
        self._set_chip_filter_value(combo, value)
        self._selector_flyouts[combo].hide()

    def _selector_text(self, combo: QComboBox) -> str:
        text = combo.currentText() or "All"
        return f"{text.upper()} >"

    def _refresh_selector_flyout(self, combo: QComboBox) -> None:
        flyout = self._selector_flyouts.get(combo)
        if flyout is None:
            return
        current = combo.currentText()
        for button in flyout.findChildren(QPushButton, "marketSelectorOption"):
            button.setProperty("active", button.property("filterValue") == current)
            button.style().unpolish(button)
            button.style().polish(button)

    def _refresh_selector_buttons(self) -> None:
        for combo, button in self._selector_buttons.items():
            button.setText(self._selector_text(combo))
            button.style().unpolish(button)
            button.style().polish(button)
            self._refresh_selector_flyout(combo)

    def _refresh_chip_group(self, layout: QHBoxLayout, combo: QComboBox, group: str) -> None:
        self._clear_layout(layout)
        current = combo.currentText() or "All"
        for option in [combo.itemText(index) for index in range(combo.count())]:
            chip = QPushButton(option.upper())
            chip.setObjectName("marketFilterChip")
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
        if combo is self._detail_range:
            self._refresh_detail_range_chip_group()
        else:
            self._refresh_overview_chip_groups()

    def _refresh_overview_chip_groups(self) -> None:
        if not hasattr(self, "_stage_chip_layout"):
            return
        self._refresh_chip_group(self._stage_chip_layout, self._stage_filter, self._stage_filter.objectName())
        self._refresh_chip_group(self._event_chip_layout, self._event_filter, self._event_filter.objectName())
        self._refresh_chip_group(self._trend_chip_layout, self._trend_filter, self._trend_filter.objectName())
        self._refresh_chip_group(self._timeframe_chip_layout, self._timeframe, self._timeframe.objectName())
        self._refresh_selector_buttons()

    def _refresh_detail_range_chip_group(self) -> None:
        if hasattr(self, "_detail_range_chip_layout"):
            self._refresh_chip_group(self._detail_range_chip_layout, self._detail_range, self._detail_range.objectName())

    def _apply_market_sort(self) -> None:
        if not hasattr(self, "_market_table"):
            return
        sort = self._sort.currentText()
        column = {"Price": 1, "24h Change": 2, "7d Change": 3, "30d Change": 4}.get(sort, 0)
        order = Qt.SortOrder.DescendingOrder if column else Qt.SortOrder.AscendingOrder
        self._market_table.sortByColumn(column, order)

    def _on_table_row_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        source_index = self._proxy_model.mapToSource(index)
        self._show_detail(self._table_model.resource_id_at(source_index.row()))

    def _refresh_detail(self, *args) -> None:
        if self._selected_resource_id is None or not hasattr(self, "_detail_stats"):
            return
        self._refresh_detail_range_chip_group()
        resource_id = self._selected_resource_id
        definition = self._resources[resource_id]
        market = self._state.market.ensure_resource(resource_id)
        event = active_market_event(self._state.market)
        event_text = event.name if resource_id in event.affected_resources else "None"
        range_id = self._detail_range.currentText() if hasattr(self, "_detail_range") else "24H"
        delta = self._period_change(resource_id, range_id)
        percent = self._change_percent_for_delta(resource_id, delta)
        self._detail_title.setText(definition.name)
        self._detail_price.setText(f"${market.current_price:.2f}")
        self._detail_change.setText(f"{delta:+.2f} ({percent:+.2f}%)")
        self._detail_change.setProperty("change", self._change_status(delta))
        self._detail_change.style().unpolish(self._detail_change)
        self._detail_change.style().polish(self._detail_change)
        self._clear_layout(self._detail_icon_layout)
        self._detail_icon_layout.addWidget(
            ResourceIconWidget(
                resource_id,
                definition.icon_key or resource_icon_key(resource_id),
                definition.accent_key or resource_accent_key(resource_id),
                size=34,
            )
        )
        self._detail_chart.set_resource(resource_id, "Price History")
        self._detail_chart.set_range(range_id)
        high, low, average = self._period_stats(resource_id, range_id)
        values = {
            "ANCHOR PRICE": f"${market.anchor_price:.2f}",
            "ACTIVE EVENT": event_text,
            "PERIOD HIGH": f"${high:.2f}",
            "PERIOD LOW": f"${low:.2f}",
            "PERIOD AVERAGE": f"${average:.2f}",
            "PERIOD CHANGE": f"{percent:+.2f}%",
        }
        for key, text in values.items():
            self._detail_stats[key].setText(text)

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

    def _matches_filters(self, resource_id: str) -> bool:
        search = self._search.text().strip().lower() if hasattr(self, "_search") else ""
        definition = self._resources[resource_id]
        if search and search not in f"{definition.name} {resource_id}".lower():
            return False
        if self._stage_filter.currentText() not in ("", "All", self._stage_for_resource(definition)):
            return False
        if self._category_filter.currentText() not in ("", "All", definition.category):
            return False
        affected = self._is_event_affected(resource_id)
        if self._event_filter.currentText() == "Event Affected" and not affected:
            return False
        if self._event_filter.currentText() == "No Active Event" and affected:
            return False
        trend = self._trend_filter.currentText()
        status = self._change_status(self._period_change(resource_id, self._timeframe.currentText()))
        if trend == "Rising" and status != "positive":
            return False
        if trend == "Falling" and status != "negative":
            return False
        if trend == "Neutral" and status != "neutral":
            return False
        return True

    def _sort_rows(self, rows: list[str]) -> list[str]:
        sort = self._sort.currentText() if hasattr(self, "_sort") else "Name"
        if sort == "Price":
            return sorted(rows, key=lambda resource_id: (-self._state.market.ensure_resource(resource_id).current_price, self._resources[resource_id].name))
        if sort == "24h Change":
            return sorted(rows, key=lambda resource_id: (-self._period_change(resource_id, "24H"), self._resources[resource_id].name))
        if sort == "7d Change":
            return sorted(rows, key=lambda resource_id: (-self._period_change(resource_id, "7D"), self._resources[resource_id].name))
        if sort == "30d Change":
            return sorted(rows, key=lambda resource_id: (-self._period_change(resource_id, "30D"), self._resources[resource_id].name))
        return sorted(rows, key=lambda resource_id: self._resources[resource_id].name)

    def _period_values(self, resource_id: str, period: str) -> tuple[float, ...]:
        values = self._state.history.values_for(f"market.price.{resource_id}")
        sample_count = MARKET_PERIOD_SAMPLES.get(period)
        if sample_count is None:
            return values
        return values[-sample_count:]

    def _period_change(self, resource_id: str, period: str) -> float:
        market = self._state.market.ensure_resource(resource_id)
        values = self._period_values(resource_id, period)
        if len(values) >= 2:
            return market.current_price - values[0]
        if period == "24H":
            return market.last_change
        return 0.0

    def _period_stats(self, resource_id: str, period: str) -> tuple[float, float, float]:
        market = self._state.market.ensure_resource(resource_id)
        values = self._period_values(resource_id, period)
        if not values:
            values = (market.current_price,)
        return max(values), min(values), sum(values) / len(values)

    def _change_percent_for_delta(self, resource_id: str, delta: float) -> float:
        market = self._state.market.ensure_resource(resource_id)
        previous = market.current_price - delta
        if previous == 0:
            return 0.0
        return delta / previous * 100.0

    def _format_change(self, resource_id: str, period: str) -> str:
        delta = self._period_change(resource_id, period)
        return f"{delta:+.2f} ({self._change_percent_for_delta(resource_id, delta):+.1f}%)"

    def _change_status(self, change: float) -> str:
        if change > 0.001:
            return "positive"
        if change < -0.001:
            return "negative"
        return "neutral"

    def _trend_label(self, status: str) -> str:
        if status == "positive":
            return "Rising"
        if status == "negative":
            return "Falling"
        return "Neutral"

    def _period_from_label(self, object_name: str) -> str:
        if object_name == "marketRowChange7d":
            return "7D"
        if object_name == "marketRowChange30d":
            return "30D"
        return "24H"

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

    def _is_event_affected(self, resource_id: str) -> bool:
        return resource_id in active_market_event(self._state.market).affected_resources

    def _show_overview(self) -> None:
        self._stack.setCurrentIndex(0)
        self.refresh()

    def _show_detail(self, resource_id: str) -> None:
        self._selected_resource_id = resource_id
        self._refresh_detail()
        self._stack.setCurrentIndex(1)

    def _clear_layout(self, layout) -> None:
        clear_layout_safely(layout)

    def _clear_layout_items_only(self, layout) -> None:
        while layout.count():
            layout.takeAt(0)
