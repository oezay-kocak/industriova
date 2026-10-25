"""Offscreen capture for inline Contract product-slot polish."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QPushButton, QTabWidget

from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "contracts-slot-polish"


def settle(app):
    for _ in range(10):
        app.processEvents()


def capture(window, app, name):
    settle(app)
    path = OUTPUT / name
    assert window.grab().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=True)
    window.resize(1600, 900)
    window.show()
    captures = []
    contracts = window.findChild(ContractsView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    tabs.setCurrentWidget(contracts)
    contracts._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    contracts._state.ensure_resource("steel").amount = 1
    contracts.refresh()
    contracts.findChild(QPushButton, "contractProductSlot").click()
    settle(app)
    contracts._product_picker.product_selected.emit(str(contracts._product_picker.tiles[0].property("resourceId")))
    captures.append(capture(window, app, "contracts_product_slots.png"))
    window.close()
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
