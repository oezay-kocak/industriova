"""Local row dragging without changing buildings or the selected board."""
from uuid import uuid4
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QFrame

MIME = 'application/x-industriova-building-order'


class BuildingTree(QTreeWidget):
    def __init__(self):
        super().__init__()
        self._token = uuid4().hex
        self._save_order = None
        self._drop_line = QFrame(self.viewport())
        self._drop_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._drop_line.setStyleSheet('background: #ffd21f; border: 0;')
        self._drop_line.hide()
        self.setRootIsDecorated(False)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setToolTip('Drag buildings up or down to change their order')

    def enable_reordering(self, callback):
        self._save_order = callback

    def ids(self):
        return tuple(self.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole) for i in range(self.topLevelItemCount()))

    def startDrag(self, supported_actions):  # noqa: N802
        if self._save_order is None or self.currentItem() is None:
            return
        uid = self.currentItem().data(0, Qt.ItemDataRole.UserRole)
        mime = QMimeData()
        mime.setData(MIME, (self._token + ':' + uid).encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def _drag_id(self, event):
        if self._save_order is None or not event.mimeData().hasFormat(MIME):
            return None
        text = bytes(event.mimeData().data(MIME)).decode('utf-8', errors='replace')
        prefix = self._token + ':'
        uid = text[len(prefix):] if text.startswith(prefix) else None
        return uid if uid in self.ids() else None

    def dragEnterEvent(self, event):  # noqa: N802
        self.dragMoveEvent(event)

    def dragMoveEvent(self, event):  # noqa: N802
        if self._drag_id(event) is not None:
            target = self.itemAt(event.position().toPoint())
            rect = self.visualItemRect(target) if target is not None else self.viewport().rect()
            y = rect.top() if target is not None and event.position().y() <= rect.center().y() else rect.bottom()
            self._drop_line.setGeometry(0, max(0, y - 1), self.viewport().width(), 2)
            self._drop_line.show()
            self._drop_line.raise_()
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            self._drop_line.hide()
            event.ignore()

    def dragLeaveEvent(self, event):  # noqa: N802
        self._drop_line.hide()
        event.accept()

    def dropEvent(self, event):  # noqa: N802
        self._drop_line.hide()
        uid = self._drag_id(event)
        if uid is None:
            event.ignore()
            return
        target = self.itemAt(event.position().toPoint())
        ids = list(self.ids())
        index = self.indexOfTopLevelItem(target) if target is not None else len(ids)
        if target is not None and event.position().y() > self.visualItemRect(target).center().y():
            index += 1
        old = ids.index(uid)
        ids.pop(old)
        ids.insert(index - (old < index), uid)
        if self.apply_order(tuple(ids)):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            event.ignore()

    def apply_order(self, ids):
        if self._save_order is None or len(ids) != len(self.ids()) or set(ids) != set(self.ids()):
            return False
        try:
            self._save_order(ids)
        except (ValueError, KeyError):
            return False
        selected = self.currentItem()
        self.blockSignals(True)
        items = {}
        while self.topLevelItemCount():
            item = self.takeTopLevelItem(0)
            items[item.data(0, Qt.ItemDataRole.UserRole)] = item
        for uid in ids:
            self.addTopLevelItem(items[uid])
        self.setCurrentItem(selected)
        self.blockSignals(False)
        return True
