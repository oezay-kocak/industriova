"""Three offscreen captures for company-wide resource-flow consistency."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from production_zero.core.cards import CardInstance
from production_zero.core.commands import AddCard, InstallCardInHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import FactoryHall
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "resource-flow-consistency"


def _settle(app: QApplication, count: int = 10) -> None:
    for _ in range(count):
        app.processEvents()


def _save(window: MainWindow, app: QApplication, name: str) -> Path:
    _settle(app)
    path = OUTPUT / name
    assert window.grab().save(str(path))
    return path


def _install_machine(view, card_id: str, definition_id: str, unit_id: str, board_kind: str, slot: int, production_id: str, output: str) -> None:
    bus = view._command_bus
    bus.dispatch(AddCard(CardInstance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON, 0, 0)))
    bus.dispatch(InstallCardInHall(unit_id, slot, card_id, board_kind))
    bus.dispatch(SelectMachineProduction(card_id, production_id, output))


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT.glob("*.png"):
        stale.unlink()
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow()
    window.resize(1600, 900)
    window.show()
    _settle(app)

    tabs = window.findChild(QTabWidget, "mainTabs")
    resources = window.findChild(ResourcesViewV2)
    factory = window.findChild(FactoryViewV2)
    energy = window.findChild(EnergyViewV2)
    assert tabs is not None and resources is not None and factory is not None and energy is not None
    state = resources._state
    bus = resources._command_bus
    state.resource_sites["site-2"] = FactoryHall(
        "site-2", "Site 2", 1, board_kind="resources", max_lines=3,
        start_unlocked_lines=1, start_slots_per_line=1,
    )
    _install_machine(resources, "qa-oil-rig", "machine.drilling", "site-1", "resources", 0, "resource.crude_oil", "crude_oil")
    _install_machine(resources, "qa-gas-rig", "machine.drilling", "site-2", "resources", 0, "resource.natural_gas", "natural_gas")
    for index in range(5):
        _install_machine(
            resources, f"qa-bitumen-{index}", "machine.processor", "hall-1", "factory", index,
            "recipe.processor.bitumen", "bitumen",
        )
    bus.dispatch(AddCard(CardInstance("qa-gas-plant", "energy.gas_power_plant", CardKind.ENERGY, Rarity.COMMON, 0, 0)))
    bus.dispatch(InstallCardInHall("plant-1", 0, "qa-gas-plant", "energy"))
    state.resources["crude_oil"].amount = 240
    state.resources["natural_gas"].amount = 100

    captures: list[Path] = []
    for view, name in (
        (resources, "01_resources_global_crude_oil_flow.png"),
        (factory, "02_factory_same_crude_oil_flow.png"),
        (energy, "03_energy_global_natural_gas_fuel_flow.png"),
    ):
        tabs.setCurrentWidget(view)
        view.refresh_view()
        view._set_resources_drawer_open(True)
        captures.append(_save(window, app, name))
        view._set_resources_drawer_open(False)

    window.close()
    assert len(captures) == 3 and all(path.exists() for path in captures)
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
