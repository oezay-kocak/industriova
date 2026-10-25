from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, InstallCardInHall, InstallFreightCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.packs import FULL_PACK, grant_pack
from production_zero.tools.ui_contact_sheet import _load_qa_fonts, _save_contact_sheet
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.packs_view import PacksView
from production_zero.ui.supply_view import SupplyView

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts" / "rarity_only_progression"
TIER_TEXT = re.compile(r"(?:\bMK\s*(?:[123]|I{1,3})\b|\bCLASS\s+(?:I{1,3}|[123])\b)", re.IGNORECASE)


def _events(app: QApplication, count: int = 5) -> None:
    for _ in range(count):
        app.processEvents()


def _assert_no_visible_tier_text(window: MainWindow) -> None:
    offenders = []
    for widget_type in (QLabel, QPushButton):
        for widget in window.findChildren(widget_type):
            if widget.isVisibleTo(window) and TIER_TEXT.search(widget.text()):
                offenders.append(f"{widget.objectName()}: {widget.text()}")
    if offenders:
        raise AssertionError("Visible tier labels remain: " + "; ".join(offenders))


def _capture(app: QApplication, window: MainWindow, title: str, captures: list) -> None:
    _events(app)
    _assert_no_visible_tier_text(window)
    pixmap = window.grab()
    path = OUT / (title.lower().replace(" ", "_").replace("/", "_") + ".png")
    pixmap.save(str(path))
    captures.append((title, pixmap))


def _finish_reveal(view: PacksView, app: QApplication) -> None:
    view._deal_timer.stop()
    while view._deal_index < len(view._reveal_cards):
        view._deal_next()
    for wrapper in view._reveal_cards:
        wrapper._deal.setCurrentTime(wrapper._deal.duration())
        wrapper.reveal()
        wrapper._flip.setCurrentTime(wrapper._flip.duration())
        wrapper._feedback.setCurrentTime(wrapper._feedback.duration())
    _events(app)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    window.resize(1600, 980)
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    freight = window.findChild(FreightView)
    inventory = window.findChild(InventoryView)
    supply = window.findChild(SupplyView)
    packs = window.findChild(PacksView)
    assert all(item is not None for item in (tabs, factory, freight, inventory, supply, packs))
    factory.pause_simulation()
    window.show()
    captures = []

    tabs.setCurrentWidget(supply)
    supply._show_section(1)
    supply._type_filter.setCurrentText("Machine")
    _capture(app, window, "Industrial Supply Machines", captures)
    supply._type_filter.setCurrentText("Freight")
    _capture(app, window, "Industrial Supply Freight", captures)

    machine = create_card_instance("qa-installed-extractor", "machine.extractor", CardKind.MACHINE, Rarity.RARE, bonus_tenths=74)
    factory._command_bus.dispatch(AddCard(machine))
    factory._command_bus.dispatch(InstallCardInHall(factory._selected_hall_id, 0, machine.card_id))
    factory.refresh_view()
    tabs.setCurrentWidget(factory)
    _capture(app, window, "Factory Installed Cards", captures)

    truck = create_card_instance("qa-installed-truck", "freight.truck", CardKind.FREIGHT, Rarity.UNCOMMON, bonus_tenths=20)
    freight._command_bus.dispatch(AddCard(truck))
    freight._command_bus.dispatch(InstallFreightCard("garage-1", 0, truck.card_id, freight._definitions))
    freight.refresh()
    tabs.setCurrentWidget(freight)
    _capture(app, window, "Freight Installed Cards", captures)

    for index in range(4):
        card = create_card_instance(f"qa-craft-{index}", "machine.processor", CardKind.MACHINE, Rarity.UNCOMMON, bonus_tenths=30)
        inventory._command_bus.dispatch(AddCard(card))
    inventory.refresh()
    tabs.setCurrentWidget(inventory)
    inventory._tabs.setCurrentIndex(0)
    _capture(app, window, "Inventory Cards", captures)

    inventory._tabs.setCurrentIndex(1)
    inventory._select_craft_target("machine.processor")
    for index in range(4):
        inventory._toggle_craft_material_group((f"qa-craft-{index}",))
    _capture(app, window, "Rarity Crafting", captures)

    tabs.setCurrentWidget(factory)
    factory._on_slot_clicked(1)
    _capture(app, window, "Card Selection", captures)

    pack_id = grant_pack(packs._state, FULL_PACK, "rarity-only-qa")
    packs.refresh()
    tabs.setCurrentWidget(packs)
    packs._open_pack(pack_id, "general")
    _finish_reveal(packs, app)
    _capture(app, window, "Pack Reveal", captures)

    tabs.setCurrentWidget(supply)
    supply._show_section(0)
    _capture(app, window, "Daily Supply", captures)

    sheet = OUT / "rarity_only_offscreen_contact_sheet.png"
    _save_contact_sheet(captures, sheet)
    window.close()
    print(sheet)


if __name__ == "__main__":
    main()
