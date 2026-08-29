from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from production_zero.ui.resource_icons import ResourceIconWidget
from production_zero.ui.widget_lifecycle import hide_detach_delete


class HoverableCardFrame(QFrame):
    hovered = Signal()
    unhovered = Signal()

    def enterEvent(self, event) -> None:  # noqa: N802
        self.hovered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.unhovered.emit()
        super().leaveEvent(event)


class CardHoverInfoPopup(QFrame):
    def __init__(self, parent: QWidget, *, object_name: str = "cardHoverInfo", embedded: bool = False) -> None:
        flags = Qt.WindowType.Widget if embedded else Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        super().__init__(parent, flags)
        self.setObjectName(object_name)
        self._embedded = embedded
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.details_signature: tuple | None = None
        self.current_title = ""
        self._value_labels: dict[str, QLabel] = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 11)
        self._layout.setSpacing(6)

    def set_details(self, title: str, icon: ResourceIconWidget | None, sections: list[tuple[str, str]], signature: tuple) -> None:
        self.details_signature = signature
        self.current_title = title
        self._clear_layout()
        header = QHBoxLayout()
        if icon is not None:
            icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            header.addWidget(icon)
        title_label = QLabel(title)
        title_label.setObjectName("cardHoverTitle")
        title_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        self._layout.addLayout(header)

        for label, value in sections:
            row = QHBoxLayout()
            label_widget = QLabel(label.upper())
            label_widget.setObjectName("cardHoverLabel")
            label_widget.setFixedWidth(108)
            value_widget = QLabel(value)
            value_widget.setObjectName("cardHoverValue")
            value_widget.setWordWrap(True)
            row.addWidget(label_widget)
            row.addWidget(value_widget, 1)
            self._layout.addLayout(row)
            self._value_labels[label] = value_widget
        self.adjustSize()

    def update_values(self, sections: list[tuple[str, str]]) -> None:
        for label, value in sections:
            value_widget = self._value_labels.get(label)
            if value_widget is not None and value_widget.text() != value:
                value_widget.setText(value)

    def show_for(self, anchor: QWidget) -> None:
        self.adjustSize()
        width = max(260, min(340, self.sizeHint().width()))
        height = max(120, self.sizeHint().height())
        self.resize(width, height)
        if self._embedded:
            parent = self.parentWidget()
            if parent is None:
                return
            anchor_top_right = anchor.mapTo(parent, QPoint(anchor.width() + 10, max(0, anchor.height() // 5)))
            anchor_left = anchor.mapTo(parent, QPoint(-width - 10, max(0, anchor.height() // 5)))
            pos = anchor_top_right
            bounds = parent.rect().adjusted(8, 8, -8, -8)
            if pos.x() + width > bounds.right():
                pos = anchor_left
            if pos.x() < bounds.left():
                pos.setX(bounds.left())
            if pos.y() + height > bounds.bottom():
                pos.setY(max(bounds.top(), bounds.bottom() - height))
            if pos.y() < bounds.top():
                pos.setY(bounds.top())
            self.move(pos)
            self.show()
            self.raise_()
            return
        pos = anchor.mapToGlobal(QPoint(anchor.width() + 10, max(0, anchor.height() // 5)))
        screen = anchor.screen()
        if screen is not None:
            bounds = screen.availableGeometry()
            if pos.x() + width > bounds.right():
                pos = anchor.mapToGlobal(QPoint(-width - 10, max(0, anchor.height() // 5)))
            if pos.y() + height > bounds.bottom():
                pos.setY(max(bounds.top() + 8, bounds.bottom() - height - 8))
            if pos.y() < bounds.top():
                pos.setY(bounds.top() + 8)
            if pos.x() < bounds.left():
                pos.setX(bounds.left() + 8)
        self.move(pos)
        self.show()
        self.raise_()

    def _clear_layout(self) -> None:
        self._value_labels = {}
        while self._layout.count():
            child = self._layout.takeAt(0)
            widget = child.widget()
            child_layout = child.layout()
            if widget is not None:
                widget.setObjectName("")
                hide_detach_delete(widget)
            elif child_layout is not None:
                while child_layout.count():
                    nested = child_layout.takeAt(0)
                    nested_widget = nested.widget()
                    if nested_widget is not None:
                        nested_widget.setObjectName("")
                        hide_detach_delete(nested_widget)
