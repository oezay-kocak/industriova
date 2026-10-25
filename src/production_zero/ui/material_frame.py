"""Layout-neutral frame using the established PZ material painter."""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame
from production_zero.ui.game_ui import Accent, GamePanel, MaterialLevel, draw_game_panel, draw_inset_surface


class MaterialFrame(QFrame):
    def __init__(self, *, level=MaterialLevel.PANEL, parent=None):
        super().__init__(parent)
        self.material_level = level
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet("MaterialFrame { background: transparent; border: 0; }")

    def resizeEvent(self, event):
        from PySide6.QtGui import QPainterPath, QRegion
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_game_panel(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1),
                        accent=Accent.NEUTRAL, level=self.material_level)
        if self.material_level == MaterialLevel.INSET:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#121719"))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(5, 5, -5, -5), 8, 8)
            draw_inset_surface(painter, QRectF(self.rect()).adjusted(5, 5, -5, -5))
        painter.end()


class RecessedPanel(GamePanel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_game_panel(painter, QRectF(self.rect()).adjusted(1, 1, -1, -1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#121719"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(5, 5, -5, -5), 8, 8)
        draw_inset_surface(painter, QRectF(self.rect()).adjusted(5, 5, -5, -5))
        painter.end()
