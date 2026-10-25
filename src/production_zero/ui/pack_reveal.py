"""Pack-only painted case artwork and fixed-layout reveal animations."""
from __future__ import annotations

from dataclasses import dataclass
from math import sin, pi

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget


OPENING_ENTRANCE_MS = 250
OPENING_HOLD_MS = 700
OPENING_EXIT_MS = 250
OPENING_TOTAL_MS = OPENING_ENTRANCE_MS + OPENING_HOLD_MS + OPENING_EXIT_MS


@dataclass(frozen=True)
class RarityFeedback:
    duration_ms: int
    border_alpha: int
    glow_alpha: int
    border_width: float
    lift_px: float


RARITY_FEEDBACK = {
    'common': RarityFeedback(0, 0, 0, 0, 0),
    'uncommon': RarityFeedback(280, 90, 12, 1.5, 0),
    'rare': RarityFeedback(360, 150, 22, 2, 1),
    'epic': RarityFeedback(420, 195, 32, 2.5, 2),
    'legendary': RarityFeedback(480, 235, 44, 3, 3),
}


def draw_pack_case(painter: QPainter, rect: QRectF, count: int, accent: QColor, activation: float = 0) -> None:
    painter.save()
    painter.setPen(QPen(QColor('#59636c'), 2))
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0, QColor('#4a535c'))
    gradient.setColorAt(.4, QColor('#222930'))
    gradient.setColorAt(1, QColor('#10151a'))
    painter.setBrush(gradient)
    painter.drawRoundedRect(rect, 7, 7)
    viewport = rect.adjusted(13, 19, -13, -21)
    painter.setBrush(QColor('#070b0e'))
    painter.setPen(QPen(accent, 1 + activation))
    painter.drawRoundedRect(viewport, 3, 3)
    gap = 4
    slot_width = (viewport.width() - 12 - (count - 1) * gap) / count
    for index in range(count):
        card = QRectF(viewport.left() + 6 + index * (slot_width + gap), viewport.top() + 8, slot_width, viewport.height() - 16)
        painter.setBrush(QColor('#35414b'))
        painter.setPen(QPen(QColor('#7b8b98'), .8))
        painter.drawRoundedRect(card, 2, 2)
        painter.fillRect(card.adjusted(3, 5, -3, -card.height() + 9), accent)
    painter.setBrush(accent)
    painter.setPen(Qt.PenStyle.NoPen)
    for x in (rect.left() + 8, rect.right() - 19):
        painter.drawRect(QRectF(x, rect.top() + 5, 11, 5))
        painter.drawRect(QRectF(x, rect.bottom() - 10, 11, 5))
    painter.restore()


class OpeningFocus(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._progress = 0.
        self._count = 3
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(OPENING_TOTAL_MS)
        self._animation.setStartValue(0.)
        self._animation.setKeyValueAt(OPENING_ENTRANCE_MS / OPENING_TOTAL_MS, 1.)
        self._animation.setKeyValueAt((OPENING_ENTRANCE_MS + OPENING_HOLD_MS) / OPENING_TOTAL_MS, 1.)
        self._animation.setEndValue(0.)
        self._animation.valueChanged.connect(self._advance)

    def start(self, count: int) -> None:
        self._count = count
        self._progress = 0.
        self.show()
        self.raise_()
        self._animation.start()

    def _advance(self, value: float) -> None:
        self._progress = value
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._progress)
        # Transparent focal layer: retain the canvas material throughout activation.
        rect = QRectF((self.width() - 210) / 2, (self.height() - 140) / 2 - 12, 210, 140)
        accent = QColor('#59cce6' if self._count == 6 else '#ffd21f')
        draw_pack_case(painter, rect, self._count, accent, 2 * self._progress)
        painter.setPen(accent)
        painter.drawText(rect.adjusted(-20, 150, 20, 46), Qt.AlignmentFlag.AlignCenter, 'PACK UNSEALED')
        painter.end()


class RevealCard(QWidget):
    revealed = Signal()

    def __init__(self, front: QWidget, rarity: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName('packRevealCard')
        self.setFixedSize(front.size())
        self.front = front
        front.setParent(self)
        front.move(0, 0)
        front.hide()
        self.rarity = rarity
        self.feedback = RARITY_FEEDBACK.get(rarity, RARITY_FEEDBACK['common'])
        self.is_revealed = False
        self.is_dealt = False
        self._flipping = False
        self._progress = 0.
        self._arrival = 0.
        self._pulse = 0.
        self._snapshot = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName('Unrevealed reward card')
        self._flip = QVariantAnimation(self)
        self._flip.setDuration(220)
        self._flip.setStartValue(0.)
        self._flip.setEndValue(1.)
        self._flip.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._flip.valueChanged.connect(self._advance_flip)
        self._flip.finished.connect(self._finish_flip)
        self._deal = QVariantAnimation(self)
        self._deal.setDuration(160)
        self._deal.setStartValue(0.)
        self._deal.setEndValue(1.)
        self._deal.valueChanged.connect(self._advance_deal)
        self._feedback = QVariantAnimation(self)
        self._feedback.setDuration(self.feedback.duration_ms)
        self._feedback.setStartValue(1.)
        self._feedback.setEndValue(0.)
        self._feedback.valueChanged.connect(self._advance_pulse)

    def deal(self) -> None:
        self.is_dealt = True
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._deal.start()

    def reveal(self) -> None:
        if not self.is_dealt or self._flipping or self.is_revealed:
            return
        self._flipping = True
        # One high-DPI snapshot, only for the width-transform portion of the flip.
        self._snapshot = self.front.grab()
        self._flip.start()

    def _advance_flip(self, value: float) -> None:
        self._progress = value
        self.update()

    def _advance_deal(self, value: float) -> None:
        self._arrival = value
        self.update()

    def _advance_pulse(self, value: float) -> None:
        self._pulse = value
        self.update()
        if value == 0:
            self.front.show()
            self._snapshot = None

    def _finish_flip(self) -> None:
        self._flipping = False
        self.is_revealed = True
        self.setAccessibleName(f'{self.rarity.title()} reward revealed')
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.feedback.duration_ms:
            self._feedback.start()
        else:
            self.front.show()
            self._snapshot = None
        self.revealed.emit()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.reveal()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return) and not event.isAutoRepeat():
            self.reveal()
        else:
            super().keyPressEvent(event)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        if not self.is_dealt or (self.is_revealed and self._pulse == 0):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._arrival)
        emphasis = sin(pi * self._pulse) if self.is_revealed else 0.
        lift = -self.feedback.lift_px * emphasis if self.is_revealed else (-2 if (self.underMouse() or self.hasFocus()) and not self._flipping else 0)
        painter.translate(self.width() / 2, 8 * (1 - self._arrival) + lift)
        scale = max(.015, abs(1 - 2 * self._progress)) if self._flipping else 1
        painter.scale(scale, 1)
        painter.translate(-self.width() / 2, 0)
        rect = QRectF(self.rect()).adjusted(4, 5, -4, -5)
        if self._progress >= .5 and self._snapshot is not None:
            painter.drawPixmap(0, 0, self._snapshot)
            if self._pulse:
                color = QColor({'uncommon': '#75c48e', 'rare': '#59cce6', 'epic': '#b087fa', 'legendary': '#f5bd50'}.get(self.rarity, '#bcc6cc'))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                color.setAlpha(int(self.feedback.glow_alpha * emphasis))
                painter.setPen(QPen(color, self.feedback.border_width + 4))
                painter.drawRoundedRect(rect, 7, 7)
                color.setAlpha(int(self.feedback.border_alpha * emphasis))
                painter.setPen(QPen(color, self.feedback.border_width))
                painter.drawRoundedRect(rect, 7, 7)
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0, QColor('#38424b'))
            gradient.setColorAt(.45, QColor('#192127'))
            gradient.setColorAt(1, QColor('#090e12'))
            painter.setBrush(gradient)
            painter.setPen(QPen(QColor('#ffd21f' if self.underMouse() or self.hasFocus() else '#687680'), 1.5))
            painter.drawRoundedRect(rect, 7, 7)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor('#4d5c68'), 1))
            painter.drawRoundedRect(rect.adjusted(7, 7, -7, -7), 3, 3)
            for offset in range(22, int(rect.height()) - 16, 12):
                painter.drawLine(int(rect.left() + 14), int(rect.top() + offset), int(rect.right() - 14), int(rect.top() + offset))
            badge = QRectF(rect.center().x() - 37, rect.center().y() - 28, 74, 56)
            painter.setBrush(QColor('#141c22'))
            painter.drawRoundedRect(badge, 3, 3)
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(24)
            painter.setFont(font)
            painter.setPen(QColor('#c1cbd1'))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, 'P / 0')
        painter.end()
