from __future__ import annotations

from PySide6.QtWidgets import QLayout, QWidget


def hide_detach_delete(widget: QWidget) -> None:
    widget.hide()
    _clear_object_names(widget)
    widget.deleteLater()


def _clear_object_names(widget: QWidget) -> None:
    widget.setObjectName("")
    for child in widget.findChildren(QWidget):
        child.setObjectName("")


def clear_layout_safely(layout: QLayout) -> None:
    while layout.count():
        child = layout.takeAt(0)
        widget = child.widget()
        child_layout = child.layout()
        if widget is not None:
            hide_detach_delete(widget)
        elif child_layout is not None:
            clear_layout_safely(child_layout)
