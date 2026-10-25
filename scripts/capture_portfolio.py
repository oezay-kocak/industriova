"""Capture the actual application with synthetic QA data and no save store."""
from __future__ import annotations

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import json
from pathlib import Path
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.config import APP_VERSION
from production_zero.ui.main_window import MainWindow
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.core.machine_operations import buy_and_install, configure_machines
from production_zero.core.freight import FreightAssignment


def seed(window) -> None:
    board = window.findChild(FactoryViewV2)
    board.pause_simulation()
    state, definitions = window._session_state, board._definitions
    state.cash.amount = 1_000_000
    state.company.level = 20
    state.warehouse_capacity = 1_000_000
    state.production_progress.unlocked_production_ids.update(
        option.production_id for definition in definitions.values()
        if hasattr(definition, "available_production_options")
        for option in definition.available_production_options)
    for stock in state.resources.values():
        stock.amount = 100
    for did in ("machine.extractor", "machine.processor", "machine.fabricator",
                "machine.assembler", "energy.solar_array", "freight.truck"):
        from production_zero.core.supply import common_card_price
        definition = definitions[did]
        ids = buy_and_install(state, definition, 1, common_card_price(definition))
        if hasattr(definition, "available_production_options"):
            option = definition.available_production_options[0]
            configure_machines(state, definitions, ids, option.production_id)
        elif did == "freight.truck":
            state.freight.assignments[ids[0]] = FreightAssignment("iron_ore", "market")
    board._simulation.advance_time(state, 0.)
    tabs = window.findChild(QTabWidget, "mainTabs")
    for index in range(tabs.count()):
        view = tabs.widget(index)
        if hasattr(view, "refresh_view"):
            view.refresh_view()
        elif hasattr(view, "refresh"):
            view.refresh()
    window._global_header.refresh()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=False, save_store=None)
    window.resize(1600, 980)
    window.show()
    app.processEvents()
    seed(window)
    tabs = window.findChild(QTabWidget, "mainTabs")
    captures = []
    try:
        for title, filename in (("Factory", "factory.png"), ("Freight", "freight.png"), ("Research", "research.png")):
            matches = [i for i in range(tabs.count()) if tabs.tabText(i) == title]
            if len(matches) != 1:
                raise RuntimeError(f"Expected one {title} tab")
            tabs.setCurrentIndex(matches[0])
            for _ in range(8):
                app.processEvents()
            image = window.grab()
            if not image.save(str(output / filename)):
                raise RuntimeError(f"Could not save {filename}")
            captures.append({"file": filename, "tab": title, "width": image.width(), "height": image.height()})
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
    (output / "captures.json").write_text(json.dumps({
        "version": APP_VERSION, "platform": "offscreen", "fixture": "synthetic QA company",
        "save_store": None, "screenshots": captures,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Captured {len(captures)} application views")


if __name__ == "__main__":
    main()
