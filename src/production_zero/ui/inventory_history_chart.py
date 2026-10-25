"""Compact PZ stock chart with actual elapsed-play timestamps."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget
from production_zero.ui.game_ui import draw_inset_surface, Accent
from production_zero.ui.charts_view import LineChartWidget
from production_zero.ui.theme import Theme


class InventoryHistoryChart(QWidget):
    def __init__(self, points, now, current_amount):
        super().__init__()
        self.points = tuple(points)
        self.now = now
        self.current_amount = current_amount
        self.setMinimumHeight(190)
        self.setObjectName("inventoryHistoryChart")
        self.setToolTip("Observed global-storage quantities. Five-minute sampling; up to 72 hours of active play. NOW is current stock. Offline time is excluded.")

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            bounds = QRectF(self.rect()).adjusted(1, 1, -1, -1)
            draw_inset_surface(painter, bounds, accent=Accent.STORAGE)
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(Theme.TEXT))
            painter.drawText(bounds.adjusted(10, 4, -10, 0), Qt.AlignmentFlag.AlignTop, "STORED UNITS")
            if not self.points:
                painter.drawText(bounds.adjusted(14, 32, -14, -24), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                                 "No inventory history yet.\nObservations accumulate during play.")
                return
            points = list(self.points)
            if self.now > points[-1][0]:
                points.append((self.now, self.current_amount))
            else:
                points[-1] = (self.now, self.current_amount)
            plot = bounds.adjusted(54, 28, -16, -44)
            maximum = max(1.0, max(v for _, v in points) * 1.08)
            span = max(300.0, self.now - points[0][0])
            for step in range(4):
                y = plot.bottom() - plot.height() * step / 3
                painter.setPen(QPen(QColor(Theme.GRID), 1, Qt.PenStyle.DotLine))
                painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
                painter.setPen(QColor(Theme.TEXT))
                painter.drawText(QRectF(bounds.left(), y - 9, 47, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                                 LineChartWidget._format_axis_value(maximum * step / 3))
            for fraction in (0, .5, 1):
                label = "NOW" if fraction == 1 else f"{span * (1-fraction) / 3600:.2f}".rstrip("0").rstrip(".")
                x = plot.left() + fraction * plot.width()
                painter.drawText(QRectF(x - 28, plot.bottom() + 3, 56, 18), Qt.AlignmentFlag.AlignCenter, label)
            painter.drawText(QRectF(plot.left(), bounds.bottom() - 20, plot.width(), 18), Qt.AlignmentFlag.AlignCenter, "HOURS OF PLAY AGO")
            mapped = [QPointF(plot.right() - (self.now - t) / span * plot.width(), plot.bottom() - value / maximum * plot.height())
                      for t, value in points]
            painter.setPen(QPen(QColor(Theme.RESOURCE), 2))
            for start, end in zip(mapped, mapped[1:]):
                painter.drawLine(start, end)
            painter.setBrush(QColor(Theme.RESOURCE))
            for point in mapped if len(mapped) <= 3 else mapped[-1:]:
                painter.drawEllipse(point, 3, 3)
        finally:
            painter.end()
