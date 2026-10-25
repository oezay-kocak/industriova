"""Render and assert the rarity-crafting workspace geometry, offscreen only."""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2


def main():
    app = QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    window.findChild(FactoryViewV2).pause_simulation()
    width, height = map(int, sys.argv[1:3])
    window.resize(width, height)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from release_test_support import legacy_component
    inventory = legacy_component(window, InventoryView)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(inventory)
    window.show()
    folder = Path("artifacts/inventory-workspaces")
    folder.mkdir(parents=True, exist_ok=True)
    inventory._tabs.setCurrentIndex(1)
    inventory._select_craft_target("machine.extractor")
    for _ in range(6):
        app.processEvents()
    scroll = inventory._craft_pages.widget(1)
    button = inventory._craft_button
    inventory.grab().save(str(folder / f"craft-main-{width}.png"))
    assert (window.width(), window.height()) == (width, height)
    assert scroll.horizontalScrollBar().maximum() == 0
    scroll.ensureWidgetVisible(button, 0, 0)
    app.processEvents()
    assert button.isVisible()
    point = button.mapTo(scroll.viewport(), QPoint(0, 0))
    assert scroll.viewport().rect().contains(point)
    assert scroll.viewport().rect().contains(point + QPoint(button.width() - 1, button.height() - 1))
    for index in range(4):
        card = create_card_instance(f"qa-material-{index}", "machine.extractor", CardKind.MACHINE, Rarity.UNCOMMON, bonus_tenths=30)
        inventory._command_bus.dispatch(AddCard(card))
        inventory._toggle_craft_material_group((card.card_id,))
    inventory._craft_confirm.setChecked(True)
    for _ in range(4):
        app.processEvents()
    assert button.isEnabled()
    inventory.grab().save(str(folder / f"craft-ready-main-{width}.png"))


if __name__ == "__main__":
    main()
