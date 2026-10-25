"""Capture the Factory/Freight secondary V2 cohesion states offscreen."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton, QTabWidget, QWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.secondary_views import StageFilterBar


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "secondary-v2-cohesion"


def _events(app: QApplication, count: int = 12) -> None:
    for _ in range(count):
        app.processEvents()


def _save(window: MainWindow, app: QApplication, filename: str) -> None:
    _events(app)
    assert (window.width(), window.height()) == (1366, 768)
    assert window.grab().toImage().save(str(OUTPUT / filename))


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    _events(app)

    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    freight = window.findChild(FreightView)
    assert tabs is not None and factory is not None and freight is not None

    tabs.setCurrentWidget(factory)
    factory._open_production_guide()
    _events(app)
    stage_filter = factory.findChild(StageFilterBar, "productionGuideStageFilter")
    category_filter = factory.findChild(QComboBox, "productionGuideCategoryFilter")
    assert stage_filter is not None and category_filter is not None
    assert factory.findChild(QComboBox, "productionGuideStageFilter") is None
    assert [button.text() for button in stage_filter.buttons] == [
        "ALL", "EXTRACTOR", "PROCESSOR", "FABRICATOR", "ASSEMBLER"
    ]

    category_filter.setCurrentText("All")
    stage_filter.setCurrentText("All")
    _save(window, app, "01_production_guide_all_1366x768.png")
    stage_filter.setCurrentText("Extraction")
    _save(window, app, "02_production_guide_extractor_1366x768.png")
    stage_filter.setCurrentText("Processing")
    _save(window, app, "03_production_guide_processor_1366x768.png")
    stage_filter.setCurrentText("All")
    category_filter.setCurrentText("Oil & Gas")
    _save(window, app, "04_production_guide_sparse_oil_gas_1366x768.png")

    factory._open_chain_from_guide("crude_oil")
    _save(window, app, "05_chain_inspector_crude_oil_1366x768.png")
    factory._open_used_in_detail("crude_oil")
    _save(window, app, "06_used_in_crude_oil_1366x768.png")

    tabs.setCurrentWidget(freight)
    freight._command_bus.dispatch(AddCard(create_card_instance(
        "secondary-v2-qa-truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON
    )))
    freight.refresh()
    freight._open_drawer(0)
    _save(window, app, "07_freight_assign_card_1366x768.png")
    freight._install_card_from_selection("secondary-v2-qa-truck")
    freight._open_assignment_view("secondary-v2-qa-truck")
    _save(window, app, "08_freight_select_cargo_resource_1366x768.png")

    for timer in window.findChildren(QTimer):
        timer.stop()
    window.close()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    print(f"Saved secondary V2 QA screenshots to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
