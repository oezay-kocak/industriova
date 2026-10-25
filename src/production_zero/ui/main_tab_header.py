from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from production_zero.ui.game_ui import Accent, MaterialLevel, draw_game_panel, draw_track_surface


MAIN_TAB_HEADER_HEIGHT = 116
MAIN_TAB_HEADER_MARGINS = (32, 25, 32, 24)
MAIN_TAB_HEADER_SPACING = 18
MAIN_TAB_TITLE_SPACING = 1
MAIN_TAB_TITLE_EMBOLDEN_OFFSET = 0.0
MAIN_TAB_SUBTITLE_EMBOLDEN_OFFSET = 0.0


from production_zero.ui.resource_tiles import ElidedResourceLabel


class MainTabHeaderLabel(ElidedResourceLabel):
    def __init__(self, text: str, *, embolden_offset: float, parent: QWidget | None = None) -> None:
        super().__init__(text)
        if parent is not None:
            self.setParent(parent)
        self._embolden_offset = embolden_offset

    def setText(self, text):
        super().setText(text)
        self.set_tooltip_text(text)

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._embolden_offset <= 0:
            return
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(QRectF(self.contentsRect()).translated(QPointF(self._embolden_offset, 0)), self.alignment(), self.text())
        painter.end()


class MainTabHeader(QFrame):
    def __init__(
        self,
        *,
        object_name: str,
        title: str,
        subtitle: str,
        title_object_name: str,
        subtitle_object_name: str,
        accent: Accent,
        monochrome: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._monochrome = monochrome
        self.setObjectName(object_name)
        self.setFixedHeight(MAIN_TAB_HEADER_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.header_layout = QHBoxLayout(self)
        self.header_layout.setContentsMargins(*MAIN_TAB_HEADER_MARGINS)
        self.header_layout.setSpacing(MAIN_TAB_HEADER_SPACING)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(MAIN_TAB_TITLE_SPACING)
        self.title_label = MainTabHeaderLabel(title, embolden_offset=MAIN_TAB_TITLE_EMBOLDEN_OFFSET)
        self.title_label.setObjectName(title_object_name)
        self.title_label.setMinimumWidth(0)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.subtitle_label = MainTabHeaderLabel(subtitle, embolden_offset=MAIN_TAB_SUBTITLE_EMBOLDEN_OFFSET)
        self.subtitle_label.setObjectName(subtitle_object_name)
        self.subtitle_label.setMinimumWidth(0)
        self.subtitle_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        title_column.addWidget(self.title_label)
        title_column.addWidget(self.subtitle_label)
        self.header_layout.addLayout(title_column, 1)

    def add_status_module(self, widget: QWidget) -> None:
        self.header_layout.addWidget(widget)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        draw_game_panel(painter, rect, accent=Accent.NEUTRAL, level=MaterialLevel.ELEVATED, radius=16)
        draw_track_surface(painter, rect.adjusted(14, 13, -14, -13), accent=self._accent, radius=11)
        if self._monochrome:
            painter.setPen(QColor("#555e65"))
            painter.setBrush(QColor("#343c42"))
            painter.drawRoundedRect(rect, 16, 16)
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0, QColor("#eceff0"))
            gradient.setColorAt(0.52, QColor("#a0a6ab"))
            gradient.setColorAt(1, QColor("#363c42"))
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect.adjusted(14, 13, -14, -13), 11, 11)
        painter.end()
        super().paintEvent(event)
