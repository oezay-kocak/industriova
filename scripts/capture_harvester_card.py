"""Capture the final Harvester machine card through the normal Inventory renderer."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.supply_view import SupplyView


OUTPUT_DIR = Path(os.environ.get("HARVESTER_CAPTURE_DIR", "artifacts/harvester_card"))
VIEWPORTS = ((1366, 768, "compact"), (1920, 1080, "desktop"))


def _settle(app: QApplication) -> None:
    for _ in range(12):
        app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    inventory = window.findChild(InventoryView)
    supply = window.findChild(SupplyView)
    tabs = window.findChild(QTabWidget, "mainTabs")
    if missing := [
        name
        for name, widget in (("Inventory", inventory), ("Industrial Supply", supply), ("mainTabs", tabs))
        if widget is None
    ]:
        raise RuntimeError(f"Missing capture widgets: {', '.join(missing)}")

    for card_id, definition_id in (
        ("harvester-visual-qa", "machine.agriculture"),
        ("drilling-visual-qa", "machine.drilling"),
    ):
        inventory._command_bus.dispatch(
            AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON))
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tabs.setCurrentWidget(inventory)
    inventory.refresh()
    inventory._type_filter.setCurrentText("Primary Production")

    for width, height, label in VIEWPORTS:
        window.resize(width, height)
        window.show()
        inventory.refresh()
        inventory._type_filter.setCurrentText("Primary Production")
        _settle(app)
        path = OUTPUT_DIR / f"harvester_inventory_{label}_{width}x{height}.png"
        if not window.grab().save(str(path)):
            raise RuntimeError(f"Could not save {path}")

        tabs.setCurrentWidget(supply)
        supply.refresh()
        supply._show_section(1)
        supply._type_filter.setCurrentText("Machine")
        supply._search.setText("Harvester")
        _settle(app)
        supply_path = OUTPUT_DIR / f"harvester_supply_{label}_{width}x{height}.png"
        if not window.grab().save(str(supply_path)):
            raise RuntimeError(f"Could not save {supply_path}")

        tabs.setCurrentWidget(inventory)

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
