"""Offscreen visual QA for the complete Extractor raster artwork pass."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QTabWidget

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "resource-assets" / "extractor-pass"


def _events(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def _factory_selection(factory: FactoryViewV2, app: QApplication) -> None:
    factory._on_slot_clicked(0)
    extractor = next(
        tile
        for tile in factory.findChildren(QFrame, "factoryCardSelectionTile")
        if "extractor" in tile.findChild(QLabel, "factoryCardSelectionTileName").text().lower()
    )
    extractor.mousePressEvent(type("Event", (), {"button": lambda self: Qt.MouseButton.LeftButton})())
    _events(app)
    slot_widget = factory._slot_widgets[0]
    slot_widget.mousePressEvent(
        type(
            "Event",
            (),
            {
                "button": lambda self: Qt.MouseButton.LeftButton,
                "position": lambda self: slot_widget._resource_control_rect().center(),
            },
        )()
    )
    _events(app)
    tiles = factory.findChildren(QFrame, "productionSelectionTile")
    assert len(tiles) >= 8
    assert sum(not tile.isHidden() for tile in tiles) >= 8


def _screenshots(app: QApplication) -> None:
    window = MainWindow()
    window.show()
    _events(app)
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    assert tabs is not None and factory is not None
    tabs.setCurrentWidget(factory)

    factory._open_production_guide()
    for width, height in ((1920, 1080), (1366, 768)):
        window.resize(width, height)
        _events(app)
        assert window.grab().toImage().save(str(OUTPUT / f"production_guide_{width}x{height}.png"))

    factory._close_drawer()
    _events(app)
    _factory_selection(factory, app)
    window.resize(1366, 768)
    _events(app)
    assert window.grab().toImage().save(str(OUTPUT / "factory_extractor_resource_selection_1366x768.png"))

    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _screenshots(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
