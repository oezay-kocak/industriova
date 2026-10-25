"""Scoped physical PZ controls, using the Storage Expand material palette.

Primary, compact secondary, and resource badge share one surface painter.
Existing GameButton/Production Guide controls retain their established rendering.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QLabel, QPushButton


def paint_module_surface(painter, path, *, light=False):
    """Painted-metal/graphite inset face, clipped to the caller's chassis."""
    rect = path.boundingRect()
    painter.save()
    painter.fillPath(path.translated(0, 3), QColor(0, 0, 0, 100))
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    colors = ("#f2ece3", "#dcd6cd", "#bdb7ae", "#85817b") if light else ("#45494d", "#2d3236", "#24282c", "#15191c")
    for stop, color in zip((0, .16, .72, 1), colors):
        gradient.setColorAt(stop, QColor(color))
    painter.fillPath(path, gradient)
    painter.setClipPath(path)
    painter.setPen(QPen(QColor(255, 255, 255, 140 if light else 45), 1))
    painter.drawLine(rect.left() + 9, rect.top() + 3, rect.right() - 15, rect.top() + 3)
    painter.drawLine(rect.left() + 3, rect.top() + 10, rect.left() + 3, rect.bottom() - 12)
    painter.setPen(QPen(QColor(0, 0, 0, 85), 2))
    painter.drawLine(rect.left() + 14, rect.bottom() - 3, rect.right() - 3, rect.bottom() - 3)
    painter.drawLine(rect.right() - 3, rect.top() + 15, rect.right() - 3, rect.bottom() - 3)
    painter.restore()


def paint_raised_surface(painter, rect, variant, *, enabled=True, pressed=False, hovered=False):
    colors = {
        "primary": ("#fff06f", "#ffd21f", "#c88f00", "#111008"),
        "secondary": ("#737b83", "#454c53", "#2b3036", "#111417"),
        "destructive": ("#ef8476", "#c83a2b", "#8f241c", "#29100d"),
        "resource": ("#ffc180", "#df6b2f", "#a44220", "#24150e"),
    }[variant]
    if not enabled:
        colors = ("#82878c", "#656a70", "#43484e", "#24282c")
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    for stop, color in zip((0.0, 0.44, 0.78, 1.0), colors):
        value = QColor(color)
        gradient.setColorAt(stop, value.darker(125) if pressed else value.lighter(108) if hovered else value)
    painter.setPen(QPen(QColor("#111417"), 1))
    painter.setBrush(gradient)
    radius = 3 if rect.height() < 28 else 6
    painter.drawRoundedRect(rect, radius, radius)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(255, 242, 217, 38 if pressed else 95), 1))
    painter.drawRoundedRect(rect.adjusted(2, 2, -2, -3), max(1, radius - 2), max(1, radius - 2))
    inset = 3 if rect.height() < 28 else 5
    painter.setPen(QPen(QColor(255, 255, 255, 40 if pressed else 110), 1))
    painter.drawLine(rect.left() + 6, rect.top() + inset, rect.right() - 6, rect.top() + inset)
    painter.setPen(QPen(QColor(0, 0, 0, 150), 1))
    painter.drawLine(rect.left() + 6, rect.bottom() - (1 if pressed else 3), rect.right() - 6, rect.bottom() - (1 if pressed else 3))


class RaisedPZButton(QPushButton):
    def __init__(self, text="", *, variant="primary"):
        super().__init__(text)
        self.variant = variant
        self.setProperty("pzButtonVariant", variant)
        if variant == "primary":
            self.setMinimumHeight(36)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        highlighted = bool(self.property('unread')) and bool(self.property('attentionPhase'))
        variant = 'primary' if highlighted else self.variant
        paint_raised_surface(painter, rect, variant, enabled=self.isEnabled(),
                             pressed=self.isDown(), hovered=self.underMouse())
        color = "#b8bdc2" if not self.isEnabled() else "#111417" if variant == "primary" else "#f1f2f3"
        painter.setPen(QColor(color))
        painter.setFont(self.font())
        painter.drawText(rect.translated(0, 1 if self.isDown() else -1), Qt.AlignmentFlag.AlignCenter, self.text())
        if self.hasFocus():
            painter.setPen(QPen(QColor("#111417" if variant == "primary" else "#ffd21f"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 3, 3)
        painter.end()


class RaisedRPBadge(QLabel):
    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        paint_raised_surface(painter, rect, "resource")
        painter.setPen(QColor("#111417"))
        painter.setFont(self.font())
        painter.drawText(rect.adjusted(10, -1, -10, -1), Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()
