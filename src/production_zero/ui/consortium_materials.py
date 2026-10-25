"""Consortium-local material hierarchy using the existing PZ palette."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from production_zero.ui.material_frame import MaterialFrame
from production_zero.ui.game_ui import draw_inset_surface
from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS


class ConsortiumWorkspaceFrame(MaterialFrame):
    """Bright silver rim around a graphite recess, without inset edge falloff."""
    def paintEvent(self, event):
        colors = GAME_UI_TOKENS.colors
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        silver = QLinearGradient(rect.topLeft(), rect.bottomRight())
        silver.setColorAt(0, colors.qcolor(colors.chassis_light))
        silver.setColorAt(.5, colors.qcolor(colors.chassis_light).darker(104))
        silver.setColorAt(1, colors.qcolor(colors.chassis_light).darker(108))
        painter.setPen(QPen(colors.qcolor(colors.chassis_shadow), 1))
        painter.setBrush(silver)
        painter.drawRoundedRect(rect, 14, 14)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(colors.qcolor(colors.chassis_light), 1))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 12, 12)
        inside = rect.adjusted(6, 6, -6, -6)
        painter.setBrush(colors.qcolor(colors.surface_1))
        painter.setPen(QPen(colors.qcolor(colors.chassis_shadow), 1))
        painter.drawRoundedRect(inside, 9, 9)
        draw_inset_surface(painter, inside, radius=9)
        painter.end()


class ConsortiumStatFrame(MaterialFrame):
    """Light concrete object with the established secondary-shell palette."""
    def paintEvent(self, event):
        from production_zero.ui.theme import Theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0, QColor(Theme.SECONDARY_SHELL_LIGHT))
        fill.setColorAt(1, QColor(Theme.SECONDARY_SHELL_MID))
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(Theme.SECONDARY_SHELL_DARK), 1))
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()
