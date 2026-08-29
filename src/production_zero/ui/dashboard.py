from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState
from production_zero.ui.theme import Theme


@dataclass(frozen=True, slots=True)
class SparklineData:
    label: str
    values: tuple[float, ...]
    color: str


class DashboardWidget(QWidget):
    """Single custom-painted dashboard surface for cheap, dense status rendering."""

    def __init__(self, state: GameState, resources: dict[str, ResourceDefinition]) -> None:
        super().__init__()
        self._state = state
        self._resources = resources
        self.setMinimumSize(900, 560)

    def set_state(self, state: GameState) -> None:
        self._state = state
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(Theme.BACKGROUND))

        content = self.rect().adjusted(18, 18, -18, -18)
        top_height = 128
        left_width = max(360, int(content.width() * 0.42))
        gap = 14

        cash_rect = QRectF(content.left(), content.top(), left_width, top_height)
        energy_rect = QRectF(cash_rect.right() + gap, content.top(), content.width() - left_width - gap, top_height)
        resource_rect = QRectF(content.left(), cash_rect.bottom() + gap, left_width, content.height() - top_height - gap)
        chart_rect = QRectF(resource_rect.right() + gap, energy_rect.bottom() + gap, energy_rect.width(), resource_rect.height())

        self._draw_cash_panel(painter, cash_rect)
        self._draw_energy_panel(painter, energy_rect)
        self._draw_resource_panel(painter, resource_rect)
        self._draw_chart_panel(painter, chart_rect)

    def _draw_panel(self, painter: QPainter, rect: QRectF, title: str) -> None:
        painter.setPen(QPen(QColor(Theme.BORDER), 1))
        painter.setBrush(QColor(Theme.PANEL))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(Theme.MUTED))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.drawText(rect.adjusted(14, 10, -14, -10), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, title.upper())

    def _draw_cash_panel(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_panel(painter, rect, "Command Ledger")
        painter.setPen(QColor(Theme.CASH))
        painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        painter.drawText(rect.adjusted(14, 34, -14, -36), Qt.AlignmentFlag.AlignLeft, f"${self._state.cash.amount:,.0f}")
        painter.setPen(QColor(Theme.DIM))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(rect.adjusted(16, 90, -16, -12), Qt.AlignmentFlag.AlignLeft, f"Tick {self._state.tick:06d} | Offline local state")

    def _draw_energy_panel(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_panel(painter, rect, "Power Grid")
        generated = self._state.energy.generated
        consumed = self._state.energy.consumed
        ratio = self._state.energy.load_ratio
        label = f"{consumed:.1f} / {generated:.1f} MW"
        color = Theme.GOOD if ratio < 0.75 else Theme.WARN if ratio < 1.0 else Theme.BAD

        bar = rect.adjusted(16, 58, -16, -44)
        self._draw_bar(painter, bar, ratio, color)
        painter.setPen(QColor(Theme.TEXT))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(rect.adjusted(16, 28, -16, -68), Qt.AlignmentFlag.AlignLeft, label)
        painter.setPen(QColor(Theme.MUTED))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(rect.adjusted(16, 88, -16, -12), Qt.AlignmentFlag.AlignLeft, f"Surplus {self._state.energy.surplus:.1f} MW")

    def _draw_resource_panel(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_panel(painter, rect, "Storage")
        row_top = rect.top() + 44
        row_height = 34
        for index, definition in enumerate(self._resources.values()):
            stock = self._state.ensure_resource(definition.resource_id, definition.default_capacity)
            y = row_top + index * row_height
            row = QRectF(rect.left() + 16, y, rect.width() - 32, 22)
            painter.setPen(QColor(Theme.TEXT))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.drawText(QRectF(row.left(), row.top() - 1, 132, row.height()), Qt.AlignmentFlag.AlignLeft, definition.name)
            self._draw_bar(painter, QRectF(row.left() + 138, row.top() + 3, row.width() - 238, 12), stock.fill_ratio, Theme.RESOURCE)
            painter.setPen(QColor(Theme.MUTED))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(row.right() - 92, row.top() - 1, 92, row.height()), Qt.AlignmentFlag.AlignRight, f"{stock.amount:.0f}/{stock.capacity:.0f}")

    def _draw_chart_panel(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_panel(painter, rect, "Trend Lines")
        charts = [
            SparklineData("Cash", self._state.history.values_for("cash"), Theme.CASH),
            SparklineData("Energy Use", self._state.history.values_for("energy.consumed"), Theme.ENERGY),
            SparklineData("Iron Ore", self._state.history.values_for("resource.iron_ore"), Theme.RESOURCE),
        ]
        chart_top = rect.top() + 44
        chart_height = max(74, (rect.height() - 62) / len(charts))
        for index, chart in enumerate(charts):
            chart_rect = QRectF(rect.left() + 16, chart_top + index * chart_height, rect.width() - 32, chart_height - 14)
            self._draw_sparkline(painter, chart_rect, chart)

    def _draw_bar(self, painter: QPainter, rect: QRectF, ratio: float, color: str) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(Theme.PANEL_ALT))
        painter.drawRoundedRect(rect, 3, 3)
        fill = QRectF(rect.left(), rect.top(), rect.width() * min(1.0, max(0.0, ratio)), rect.height())
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(fill, 3, 3)

    def _draw_sparkline(self, painter: QPainter, rect: QRectF, chart: SparklineData) -> None:
        painter.setPen(QPen(QColor(Theme.GRID), 1))
        painter.drawRect(rect)
        painter.setPen(QColor(Theme.MUTED))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.drawText(rect.adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, chart.label)
        values = chart.values[-120:]
        if len(values) < 2:
            painter.setPen(QColor(Theme.DIM))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "waiting for samples")
            return

        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum or 1.0
        plot = rect.adjusted(8, 24, -8, -8)
        points: list[QPointF] = []
        for index, value in enumerate(values):
            x = plot.left() + (plot.width() * index / (len(values) - 1))
            y = plot.bottom() - ((value - minimum) / span * plot.height())
            points.append(QPointF(x, y))

        painter.setPen(QPen(QColor(chart.color), 2))
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)
