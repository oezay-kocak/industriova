from __future__ import annotations

from collections.abc import Callable, Iterable

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget


def drain_qt_events(cycles: int = 8) -> None:
    for _ in range(cycles):
        QApplication.processEvents()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()


def describe_widget(widget: QWidget) -> str:
    parent = widget.parentWidget()
    parent_name = "<none>" if parent is None else f"{type(parent).__name__}#{parent.objectName()}"
    flags = int(widget.windowFlags())
    geometry = widget.geometry()
    return (
        f"{type(widget).__name__}#{widget.objectName()} "
        f"parent={parent_name} isWindow={widget.isWindow()} "
        f"visible={widget.isVisible()} flags={flags} "
        f"geometry={geometry.x()},{geometry.y()},{geometry.width()}x{geometry.height()}"
    )


def visible_top_level_widgets(exclude: Iterable[QWidget] = ()) -> list[QWidget]:
    excluded = {id(widget) for widget in exclude}
    return [
        widget
        for widget in QApplication.topLevelWidgets()
        if widget.isVisible() and id(widget) not in excluded
    ]


def assert_no_visible_top_level_delta(
    action: Callable[[], None],
    *,
    allowed: Iterable[QWidget] = (),
    cycles: int = 8,
) -> None:
    allowed_widgets = tuple(allowed)
    baseline = {id(widget) for widget in visible_top_level_widgets(allowed_widgets)}
    action()
    drain_qt_events(cycles)
    unexpected = [
        widget
        for widget in visible_top_level_widgets(allowed_widgets)
        if id(widget) not in baseline
    ]
    assert not unexpected, "\n".join(describe_widget(widget) for widget in unexpected)
