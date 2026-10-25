"""Focused offscreen captures for the read-only Unlock Tree implementation."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QTabWidget

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.unlock_tree_view import UnlockTreeView


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "unlock-tree"


def _events(app: QApplication, count: int = 14) -> None:
    for _ in range(count):
        app.processEvents()


def _save(window: MainWindow, app: QApplication, filename: str, size: tuple[int, int]) -> Path:
    window.resize(*size)
    _events(app)
    assert (window.width(), window.height()) == size
    path = OUTPUT / filename
    assert window.grab().toImage().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale_capture in OUTPUT.glob("*.png"):
        stale_capture.unlink()
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    _events(app)
    factory = window.findChild(FactoryViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None and tabs is not None
    tabs.setCurrentWidget(factory)
    factory.pause_simulation()

    factory._open_production_guide()
    factory.findChild(QLineEdit, "productionGuideSearchInput").clear()
    factory._open_unlock_tree()
    _events(app)
    tree = factory.findChild(UnlockTreeView, "unlockTreeView")
    assert tree is not None
    captures = [_save(window, app, "01_unlock_tree_cleanup_default_1366x768.png", (1366, 768))]

    tree.stage_filter.select_value("MANUFACTURING")
    _events(app)
    captures.append(_save(window, app, "02_unlock_tree_cleanup_manufacturing_1366x768.png", (1366, 768)))

    tree.search.setText("Steel Components")
    captures.append(_save(window, app, "03_unlock_tree_cleanup_search_focus_1366x768.png", (1366, 768)))

    assert len(captures) == 3 and all(path.exists() for path in captures)
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
