"""Bounded offscreen release-polish captures; never starts the normal GUI entrypoint."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.packs import FULL_PACK, grant_pack
from production_zero.tools.ui_contact_sheet import _load_qa_fonts, _save_contact_sheet
from production_zero.ui.charts_view import ChartsView
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.market_view import MarketView
from production_zero.ui.packs_view import PacksView
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2
from production_zero.ui.supply_view import SupplyView


OUTPUT = Path("artifacts/final_visual_audit_fix_pass_2026-09-09")
VIEWPORTS = ((1366, 768), (1920, 1080))


def _settle(app: QApplication, passes: int = 8) -> None:
    for _ in range(passes):
        app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _capture(window: MainWindow, app: QApplication, name: str, captures: list) -> None:
    _settle(app)
    pixmap = window.grab()
    path = OUTPUT / f"{name}.png"
    if not pixmap.save(str(path)):
        raise RuntimeError(f"Could not save {path}")
    captures.append((name.replace("_", " "), pixmap))


def _install_selection_cards(resources: ResourcesViewV2) -> None:
    for family in ("drilling", "agriculture"):
        card_id = f"qa-selection-{family}"
        if card_id not in resources._state.cards:
            resources._command_bus.dispatch(AddCard(create_card_instance(
                card_id,
                f"machine.{family}",
                CardKind.MACHINE,
                Rarity.COMMON,
            )))


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    resources = window.findChild(ResourcesViewV2)
    factory = window.findChild(FactoryViewV2)
    energy = window.findChild(EnergyViewV2)
    inventory = window.findChild(InventoryView)
    charts = window.findChild(ChartsView)
    market = window.findChild(MarketView)
    freight = window.findChild(FreightView)
    supply = window.findChild(SupplyView)
    packs = window.findChild(PacksView)
    if not all((tabs, resources, factory, energy, inventory, charts, market, freight, supply, packs)):
        raise RuntimeError("Required capture view is missing")
    factory.pause_simulation()
    _install_selection_cards(resources)
    grant_pack(factory._state, FULL_PACK, "visual audit fix pass")
    grant_pack(factory._state, FULL_PACK, "visual audit fix pass")

    for width, height in VIEWPORTS:
        size = f"{width}x{height}"
        captures = []
        window.resize(width, height)
        window.show()

        tabs.setCurrentWidget(resources)
        resources.refresh_view()
        _capture(window, app, f"resources_board_{size}", captures)
        resources._on_slot_clicked(0)
        _capture(window, app, f"resources_card_selection_{size}", captures)
        resources._close_drawer()

        tabs.setCurrentWidget(energy)
        energy.refresh_view()
        _capture(window, app, f"energy_board_{size}", captures)

        tabs.setCurrentWidget(inventory)
        inventory.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(0)
        inventory.refresh()
        _capture(window, app, f"inventory_{size}", captures)
        inventory.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
        inventory._craft_target_definition_id = "machine.extractor"
        inventory._set_craft_selection_mode("workspace")
        inventory.refresh()
        _capture(window, app, f"crafting_{size}", captures)

        tabs.setCurrentWidget(charts)
        charts.refresh()
        _capture(window, app, f"charts_{size}", captures)
        tabs.setCurrentWidget(market)
        market.refresh()
        _capture(window, app, f"market_{size}", captures)
        tabs.setCurrentWidget(freight)
        freight.refresh()
        _capture(window, app, f"freight_{size}", captures)

        tabs.setCurrentWidget(factory)
        factory._open_production_guide()
        _capture(window, app, f"production_guide_{size}", captures)
        factory._close_drawer()

        previous_cash = factory._state.cash.amount
        factory._state.cash.amount = 0
        tabs.setCurrentWidget(resources)
        resources.refresh_view()
        window._global_header.refresh()
        _capture(window, app, f"unaffordable_actions_{size}", captures)
        factory._state.cash.amount = previous_cash
        window._global_header.refresh()

        tabs.setCurrentWidget(packs)
        packs.refresh()
        _capture(window, app, f"packs_{size}", captures)
        tabs.setCurrentWidget(supply)
        supply._show_section(1)
        supply.refresh()
        _capture(window, app, f"common_supply_{size}", captures)

        _save_contact_sheet(captures, OUTPUT / f"contact_sheet_{size}.png")

    window.close()
    print(f"Captured {len(VIEWPORTS) * 12} screens and {len(VIEWPORTS)} contact sheets in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
