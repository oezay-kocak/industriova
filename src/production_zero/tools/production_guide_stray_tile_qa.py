"""Offscreen regression captures for Production Guide grid ownership."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QTabWidget

from production_zero.ui.factory_view import ProductionGuideTile
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "production-guide-stray-workwear-fix"


def _events(app: QApplication, count: int = 8) -> None:
    for _ in range(count):
        app.processEvents()


def _assert_grid_ownership(factory: FactoryViewV2) -> None:
    host = factory._guide_grid_host
    grid = factory._guide_grid
    assert host is not None and grid is not None
    tiles = host.findChildren(ProductionGuideTile)
    assert len(tiles) == 353
    assert all(grid.indexOf(tile) >= 0 for tile in tiles if not tile.isHidden())
    workwear = next(tile for tile in tiles if tile.property("resourceId") == "workwear")
    assert workwear.isHidden() and grid.indexOf(workwear) == -1


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    _events(app)
    factory = window.findChild(FactoryViewV2)
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert factory is not None and tabs is not None
    tabs.setCurrentWidget(factory)
    factory._open_production_guide()

    for width, height in ((1920, 1080), (1366, 768)):
        window.resize(width, height)
        _events(app)
        _assert_grid_ownership(factory)
        window.grab().toImage().save(str(OUTPUT / f"production_guide_{width}x{height}.png"))

    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    assert search is not None
    search.setText("Workwear")
    _events(app)
    workwear = next(
        tile
        for tile in factory._guide_grid_host.findChildren(ProductionGuideTile)
        if tile.property("resourceId") == "workwear"
    )
    assert not workwear.isHidden()
    assert factory._guide_grid.indexOf(workwear) == 0
    window.grab().toImage().save(str(OUTPUT / "workwear_regular_search_result_1366x768.png"))

    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
