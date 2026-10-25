from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, InstallCardInHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow


OUTPUT = Path("artifacts/downstream-recipe-switch")


def main() -> None:
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    window.resize(1600, 980)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    factory = window.findChild(FactoryViewV2)
    assert tabs is not None and factory is not None

    machines = (
        (0, "qa-processor", "machine.processor", "recipe.processor.iron", "recipe.processor.copper", "iron"),
        (1, "qa-fabricator", "machine.fabricator", "recipe.fabricator.iron_components", "recipe.fabricator.copper_wire", "iron_components"),
        (2, "qa-assembler", "machine.assembler", "recipe.assembler.industrial_equipment", "recipe.assembler.heavy_machinery", "industrial_equipment"),
    )
    for slot, card_id, definition_id, production_id, alternate_id, resource_id in machines:
        factory._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)))
        factory._command_bus.dispatch(InstallCardInHall("hall-1", slot, card_id, "factory"))
        factory._state.production_progress.unlocked_production_ids.update({production_id, alternate_id})
        factory._command_bus.dispatch(SelectMachineProduction(card_id, production_id, resource_id))
    factory.refresh_view()
    tabs.setCurrentWidget(factory)
    for _ in range(6):
        app.processEvents()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "processor_fabricator_assembler_controls.png"
    assert window.grab().save(str(path))
    assert all(factory._state.halls["hall-1"].slots[index].card_id == card_id for index, card_id, *_ in machines)
    window.close()
    print(f"Captured 1 offscreen screenshot: {path.resolve()}")


if __name__ == "__main__":
    main()
