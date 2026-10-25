"""Offscreen visual QA for the complete Fabricator raster artwork pass."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QTabWidget

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_art import FABRICATOR_RESOURCE_IDS, draw_resource_raster


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "resource-assets" / "fabricator-pass"


def _events(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def _contact_sheet() -> None:
    columns, cell_width, cell_height = 7, 220, 190
    rows = (len(FABRICATOR_RESOURCE_IDS) + columns - 1) // columns
    sheet = QImage(columns * cell_width, rows * cell_height, QImage.Format.Format_RGB32)
    sheet.fill(QColor("#0b0f13"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
    for index, resource_id in enumerate(FABRICATOR_RESOURCE_IDS):
        row, column = divmod(index, columns)
        panel = QRectF(column * cell_width + 6, row * cell_height + 6, cell_width - 12, cell_height - 12)
        light = (row + column) % 2 == 1
        painter.fillRect(panel, QColor("#edf0f2" if light else "#151b21"))
        draw_resource_raster(painter, QRectF(panel.left() + 25, panel.top() + 8, 158, 138), resource_id)
        painter.setPen(QColor("#172027" if light else "#f4c928"))
        painter.drawText(QPointF(panel.left() + 9, panel.bottom() - 11), resource_id.upper())
    painter.end()
    assert sheet.save(str(OUTPUT / "fabricator_icons_contact_sheet.png"))


def _screenshots(app: QApplication) -> None:
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    _events(app)
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    assert tabs is not None and factory is not None
    tabs.setCurrentWidget(factory)
    factory._open_production_guide()
    _events(app)
    stage_filter = factory.findChild(QComboBox, "productionGuideStageFilter")
    assert stage_filter is not None
    stage_filter.setCurrentText("Manufacturing")
    _events(app)
    assert window.grab().toImage().save(str(OUTPUT / "production_guide_fabricator_icons_1366x768.png"))
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _contact_sheet()
    _screenshots(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
