"""Local drag feedback and scrolling; no domain writes or global event filter."""
from PySide6.QtCore import QObject, QEvent, QPoint, Qt, QTimer, QRect
from PySide6.QtGui import QCursor, QPainter, QColor, QPen
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget
from shiboken6 import isValid


def drag_pixmap(widget, count):
    pixmap = widget.grab()
    if count > 1:
        painter = QPainter(pixmap)
        painter.setPen(QColor('#17252b'))
        painter.fillRect(QRect(8, 8, 118, 28), QColor('#efc65b'))
        painter.drawText(QRect(8, 8, 118, 28), Qt.AlignmentFlag.AlignCenter, f'{count} CARDS')
        painter.end()
    return pixmap


class DropOutline(QWidget):
    def __init__(self, target, mode):
        super().__init__(target)
        self.setObjectName('cardDropOutline')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setStyleSheet('background: transparent; border: 0;')
        self.mode = mode
        self.setGeometry(target.rect())
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        color = {'move': '#63d79b', 'swap': '#efc65b', 'invalid': '#ef6d66'}[self.mode]
        painter.setPen(QPen(QColor(color), 3))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 6, 6)
        painter.fillRect(6, self.height() - 30, 112, 24, QColor('#17252b'))
        painter.setPen(QColor(color))
        painter.drawText(QRect(6, self.height() - 30, 112, 24), Qt.AlignmentFlag.AlignCenter,
                         {'move': 'MOVE', 'swap': 'SWAP', 'invalid': 'UNAVAILABLE'}[self.mode])


class BoardDragFeedback(QObject):
    EDGE = 64
    MAX_STEP = 26  # logical pixels / 16 ms, approximately 1600 px/s

    def __init__(self, owner, cancel, moved):
        super().__init__(owner)
        self.owner, self.cancel, self.moved = owner, cancel, moved
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.active = False
        self.scroll = self.ghost = self.outline = self.target = None
        self.position = QPoint()
        self.grip = QPoint()
        self.mode = None
        self._window = None
        self.source = None
        owner.installEventFilter(self)
        owner.destroyed.connect(self.stop)

    def start(self, source, grip, count=1, *, ghost=False):
        self.stop()
        self.active = True
        self.source = source
        source.installEventFilter(self)
        self.grip = QPoint(grip)
        self._window = self.owner.window()
        self._window.installEventFilter(self)
        # Only the nearest board viewport participates; never its outer page.
        parent = source.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        self.scroll = parent
        if self.scroll is not None:
            self.scroll.viewport().installEventFilter(self)
            self.scroll.viewport().setAcceptDrops(True)
        if ghost:
            self.ghost = QLabel(self._window)
            self.ghost.setObjectName('freightDragGhost')
            self.ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.ghost.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.ghost.setPixmap(drag_pixmap(source, count))
            self.ghost.adjustSize()
            self.ghost.show()
            self.ghost.raise_()
        self.update_position(source.mapToGlobal(grip))

    def update_position(self, position):
        if not self.active:
            return
        self.position = QPoint(position)
        if self.ghost is not None:
            self.ghost.move(self._window.mapFromGlobal(self.position - self.grip))
            self.ghost.raise_()
        if self._step():
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()

    def _step(self):
        if self.scroll is None or not isValid(self.scroll) or not self.scroll.isVisible():
            return 0
        viewport = self.scroll.viewport()
        point = viewport.mapFromGlobal(self.position)
        if not viewport.rect().contains(point):
            return 0
        edge = min(self.EDGE, viewport.height() // 3)
        if edge <= 0:
            return 0
        distance = point.y() if point.y() < edge else viewport.height() - 1 - point.y()
        if distance >= edge:
            return 0
        direction = -1 if point.y() < edge else 1
        bar = self.scroll.verticalScrollBar()
        if (direction < 0 and bar.value() == bar.minimum()) or (direction > 0 and bar.value() == bar.maximum()):
            return 0
        return direction * max(1, round(self.MAX_STEP * (1 - distance / edge) ** 1.4))

    def _tick(self):
        if not self.active or not self.owner.isVisible():
            self.cancel()
            return
        self.update_position(QCursor.pos())
        step = self._step()
        if step:
            bar = self.scroll.verticalScrollBar()
            bar.setValue(bar.value() + step)
        self.moved(self.position)

    def wheel(self, event):
        if not self.active or self.scroll is None or not isValid(self.scroll):
            return False
        delta = event.pixelDelta().y() or round(event.angleDelta().y() / 120 * 96)
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.value() - delta)
        self.moved(self.position)
        event.accept()
        return True

    def highlight(self, target=None, mode=None, reason=''):
        if target is self.target and mode == self.mode:
            return
        if self.outline is not None and isValid(self.outline):
            self.outline.hide()
            self.outline.deleteLater()
        if self.target is not None and isValid(self.target):
            self.target.setProperty('freightDropTarget', False)
            self.target.setProperty('cardDropState', None)
        self.target, self.mode, self.outline = target, mode, None
        if target is not None:
            target.setProperty('freightDropTarget', mode in ('move', 'swap'))
            target.setProperty('cardDropState', mode)
            self.outline = DropOutline(target, mode)
            self.outline.setToolTip(reason)

    def stop(self):
        self.active = False
        self.timer.stop()
        self.highlight()
        if self.ghost is not None and isValid(self.ghost):
            self.ghost.hide()
            self.ghost.deleteLater()
        self.ghost = None
        if self.source is not None and isValid(self.source):
            self.source.removeEventFilter(self)
        self.source = None
        if self.scroll is not None and isValid(self.scroll):
            self.scroll.viewport().removeEventFilter(self)
        if self._window is not None and isValid(self._window) and self._window is not self.owner:
            self._window.removeEventFilter(self)
        self.scroll = self._window = None

    def eventFilter(self, watched, event):
        if not self.active:
            return False
        kind = event.type()
        if watched in (self.owner, self._window, self.source) and kind in (QEvent.Type.Hide, QEvent.Type.Close, QEvent.Type.WindowDeactivate):
            self.cancel()
        elif kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.cancel()
            return True
        elif kind == QEvent.Type.Wheel:
            return self.wheel(event)
        elif kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            self.update_position(watched.mapToGlobal(event.position().toPoint()))
            self.moved(self.position)
            event.acceptProposedAction()
            return True
        elif kind == QEvent.Type.DragLeave:
            self.timer.stop()
            self.highlight()
        return False
