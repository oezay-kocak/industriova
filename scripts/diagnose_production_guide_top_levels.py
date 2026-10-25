from __future__ import annotations

import os
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QTabWidget, QWidget
from shiboken6 import isValid as is_qt_object_valid

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "artifacts" / "production_guide_top_level_diagnostic.log"


@dataclass
class WidgetStats:
    first_seen: float
    show_count: int = 0
    hide_count: int = 0
    close_count: int = 0
    destroy_count: int = 0
    events: Counter[str] = field(default_factory=Counter)


class TopLevelProbe(QObject):
    def __init__(self, app: QApplication, log_path: Path) -> None:
        super().__init__()
        self.app = app
        self.started = time.perf_counter()
        self.log_path = log_path
        self.stats: dict[int, WidgetStats] = {}
        self.last_visible_ids: tuple[int, ...] = ()
        self.last_all_ids: tuple[int, ...] = ()
        self.lines: list[str] = []
        app.installEventFilter(self)

    def _elapsed(self) -> float:
        return time.perf_counter() - self.started

    def _describe(self, widget: QWidget) -> str:
        parent = widget.parentWidget()
        geometry = widget.geometry()
        return (
            f"id={id(widget)} py={type(widget).__name__} qt={widget.metaObject().className()} "
            f"name={widget.objectName()!r} title={widget.windowTitle()!r} "
            f"parent={type(parent).__name__ if parent else None}/{parent.objectName() if parent else None!r} "
            f"flags={int(widget.windowFlags())} visible={widget.isVisible()} "
            f"geom=({geometry.x()},{geometry.y()},{geometry.width()}x{geometry.height()})"
        )

    def log(self, message: str) -> None:
        self.lines.append(f"{self._elapsed():8.3f}s {message}")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(watched, QWidget) and watched.isWindow():
            stats = self.stats.setdefault(id(watched), WidgetStats(self._elapsed()))
            event_name = event.type().name if hasattr(event.type(), "name") else str(int(event.type()))
            stats.events[event_name] += 1
            if event.type() == QEvent.Type.Show:
                stats.show_count += 1
                self.log(f"SHOW {self._describe(watched)}")
            elif event.type() == QEvent.Type.Hide:
                stats.hide_count += 1
                self.log(f"HIDE {self._describe(watched)}")
            elif event.type() == QEvent.Type.Close:
                stats.close_count += 1
                self.log(f"CLOSE {self._describe(watched)}")
            elif event.type() == QEvent.Type.Destroy:
                stats.destroy_count += 1
                self.log(f"DESTROY {self._describe(watched)}")
        return super().eventFilter(watched, event)

    def sample(self, label: str) -> None:
        widgets = tuple(widget for widget in self.app.topLevelWidgets() if is_qt_object_valid(widget))
        all_ids = tuple(sorted(id(widget) for widget in widgets))
        visible = tuple(widget for widget in widgets if widget.isVisible())
        visible_ids = tuple(sorted(id(widget) for widget in visible))
        for widget in widgets:
            self.stats.setdefault(id(widget), WidgetStats(self._elapsed()))
        if all_ids != self.last_all_ids:
            self.log(f"TOP_LEVEL_SET {label} count={len(widgets)}")
            for widget in widgets:
                self.log(f"  {self._describe(widget)}")
            self.last_all_ids = all_ids
        if visible_ids != self.last_visible_ids:
            self.log(f"VISIBLE_SET {label} count={len(visible)}")
            for widget in visible:
                self.log(f"  {self._describe(widget)}")
            self.last_visible_ids = visible_ids

    def write(self) -> None:
        self.log("SUMMARY")
        for widget_id, stats in sorted(self.stats.items()):
            self.lines.append(
                f"SUMMARY id={widget_id} first={stats.first_seen:.3f}s show={stats.show_count} "
                f"hide={stats.hide_count} close={stats.close_count} destroy={stats.destroy_count} "
                f"events={dict(stats.events)}"
            )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.write_text("\n".join(self.lines), encoding="utf-8")


def _drain(app: QApplication, probe: TopLevelProbe, label: str, *, seconds: float = 0.0, cycles: int = 1) -> None:
    deadline = time.perf_counter() + seconds
    count = 0
    while count < cycles or time.perf_counter() < deadline:
        app.processEvents()
        probe.sample(f"{label}#{count}")
        count += 1
        if seconds > 0:
            time.sleep(0.01)


def _select_factory_tab(window: MainWindow) -> None:
    tabs = window.findChild(QTabWidget, "mainTabs")
    if tabs is None:
        raise RuntimeError("mainTabs not found")
    for index in range(tabs.count()):
        if tabs.tabText(index) == "Factory":
            tabs.setCurrentIndex(index)
            return
    raise RuntimeError("Factory tab not found")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    probe = TopLevelProbe(app, LOG_PATH)
    window = MainWindow()
    window.resize(1280, 820)
    window.show()
    _select_factory_tab(window)
    _drain(app, probe, "after-show", cycles=20)
    factory = window.findChild(FactoryViewV2)
    if factory is None:
        raise RuntimeError("FactoryViewV2 not found")
    button = window.findChild(QWidget, "productionGuideButton")
    if button is None:
        raise RuntimeError("productionGuideButton not found")
    probe.log("CLICK productionGuideButton")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    _drain(app, probe, "guide-open-idle", seconds=4.0, cycles=40)
    guide = factory.findChild(QWidget, "productionGuideView")
    probe.log(f"GUIDE identity={id(guide) if guide is not None else None} builds={factory._guide_view_build_count} grid={factory._guide_grid_rebuild_count} resize={factory._guide_grid_resize_count}")
    tiles = factory.findChildren(QWidget, "productionGuideTile")
    if tiles:
        probe.log(f"CLICK first productionGuideTile resource={tiles[0].property('resourceId')!r}")
        tiles[0].mousePressEvent(type("_Click", (), {"button": lambda self: Qt.MouseButton.LeftButton})())
        _drain(app, probe, "chain-open-idle", seconds=2.0, cycles=20)
    used_in = factory.findChild(QPushButton, "guideUsedInOpenButton")
    if used_in is not None and used_in.isEnabled():
        probe.log("CLICK guideUsedInOpenButton")
        used_in.click()
        _drain(app, probe, "used-in-open-idle", seconds=2.0, cycles=20)
    for width, height in ((1600, 980), (1280, 820), (1920, 1080), (1280, 820)):
        probe.log(f"RESIZE {width}x{height}")
        window.resize(width, height)
        _drain(app, probe, f"resize-{width}x{height}", seconds=0.7, cycles=10)
    window.close()
    _drain(app, probe, "after-close", cycles=20)
    probe.write()
    print(LOG_PATH)


if __name__ == "__main__":
    main()
