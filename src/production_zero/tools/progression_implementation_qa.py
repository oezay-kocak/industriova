from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QTabWidget

from production_zero.core.commands import InstallCardInHall
from production_zero.core.progression import record_lifetime_production
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "company-xp-progression"


def _events(app: QApplication, count: int = 5) -> None:
    for _ in range(count):
        app.processEvents()


def _capture(window: MainWindow, name: str) -> tuple[str, QImage]:
    image = window.grab().toImage()
    image.save(str(OUTPUT / f"{name}.png"))
    return name.replace("_", " ").title(), image


def _search(factory: FactoryViewV2, text: str) -> None:
    search = factory.findChild(QLineEdit, "productionGuideSearchInput")
    stage = factory.findChild(QComboBox, "productionGuideStageFilter")
    category = factory.findChild(QComboBox, "productionGuideCategoryFilter")
    if stage is not None:
        stage.setCurrentText("All")
    if category is not None:
        category.setCurrentText("All")
    if search is not None:
        search.setText(text)


def _contact_sheet(captures: list[tuple[str, QImage]]) -> None:
    thumb = QSize(640, 392)
    margin = 18
    label_height = 30
    columns = 2
    rows = (len(captures) + columns - 1) // columns
    sheet = QImage(
        columns * thumb.width() + (columns + 1) * margin,
        rows * (thumb.height() + label_height) + (rows + 1) * margin,
        QImage.Format.Format_ARGB32,
    )
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setPen(QColor("#edf6f2"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    for index, (label, image) in enumerate(captures):
        row, column = divmod(index, columns)
        x = margin + column * (thumb.width() + margin)
        y = margin + row * (thumb.height() + label_height + margin)
        scaled = image.scaled(thumb)
        painter.drawImage(x, y, scaled)
        painter.drawText(x, y + thumb.height() + 22, label)
    painter.end()
    sheet.save(str(OUTPUT / "contact_sheet.png"))


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.resize(1600, 980)
    window.show()
    _events(app)
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    contracts = window.findChild(ContractsView)
    assert tabs is not None and factory is not None and contracts is not None
    tabs.setCurrentWidget(factory)

    captures: list[tuple[str, QImage]] = []
    factory._open_production_guide()
    _events(app)
    captures.append(_capture(window, "01_guide_early_game"))

    _search(factory, "Lithium Ore")
    _events(app)
    captures.append(_capture(window, "02_guide_level_lock"))

    record_lifetime_production(factory._state, {"iron_ore": 78}, factory._definitions)
    _search(factory, "Iron")
    _events(app)
    captures.append(_capture(window, "03_guide_lifetime_lock"))

    _search(factory, "Microchip")
    _events(app)
    captures.append(_capture(window, "04_guide_cross_family_lock"))

    factory._close_drawer()
    factory._command_bus.dispatch(
        InstallCardInHall("hall-1", 0, "test-drill-common-001")
    )
    factory._open_production_drawer("test-drill-common-001")
    _events(app)
    captures.append(_capture(window, "05_factory_unlocked_selection"))

    tabs.setCurrentWidget(contracts)
    contracts.refresh()
    _events(app)
    captures.append(_capture(window, "06_contract_fixed_xp"))

    tabs.setCurrentWidget(factory)
    factory._close_drawer()
    factory._refresh_content()
    _events(app)
    captures.append(_capture(window, "07_company_xp_display"))

    _contact_sheet(captures)
    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
