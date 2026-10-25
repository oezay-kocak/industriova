"""Offscreen QA sheet for the first resource raster batch."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.resource_art import RESOURCE_RASTER_ASSETS, draw_resource_raster


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "resource-assets" / "batch-01"
RESOURCE_IDS = tuple(RESOURCE_RASTER_ASSETS)


def _events(app: QApplication, count: int = 8) -> None:
    for _ in range(count):
        app.processEvents()


def _preview_sheet() -> None:
    width, height = 1480, 920
    sheet = QImage(width, height, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#0a0f13"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    for index, resource_id in enumerate(RESOURCE_IDS):
        row, column = divmod(index, 4)
        x = 20 + column * 360
        y = 20 + row * 440
        for offset, background in ((0, QColor("#171d22")), (172, QColor("#e7e9e4"))):
            panel = QRectF(x, y + offset, 340, 160)
            painter.fillRect(panel, background)
            draw_resource_raster(painter, panel.adjusted(12, 12, -12, -12), resource_id)
        painter.setPen(QColor("#f4c928"))
        painter.drawText(QRectF(x, y + 338, 230, 30), Qt.AlignmentFlag.AlignLeft, resource_id.upper())
        painter.setPen(QColor("#d8e0e5"))
        painter.drawText(QRectF(x + 235, y + 338, 55, 30), Qt.AlignmentFlag.AlignRight, "42 px")
        draw_resource_raster(painter, QRectF(x + 295, y + 332, 42, 42), resource_id)
    painter.end()
    sheet.save(str(OUTPUT / "contact_sheet_dark_light_and_ui_size.png"))


def _resource_browser(app: QApplication) -> None:
    window = MainWindow()
    window.resize(1600, 980)
    window.show()
    _events(app)
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    assert tabs is not None and factory is not None
    tabs.setCurrentWidget(factory)
    factory._open_production_guide()
    _events(app)
    window.grab().toImage().save(str(OUTPUT / "production_guide_resource_browser.png"))
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _preview_sheet()
    _resource_browser(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
