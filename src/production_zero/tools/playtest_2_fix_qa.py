from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, InstallCardInHall, RemoveCardFromHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.dev_tools_view import DevToolsView
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import ResourcesViewV2


OUTPUT = Path("artifacts/playtest-2-fix-pass")


def _drain(app: QApplication) -> None:
    for _ in range(6):
        app.processEvents()


def _save(window: MainWindow, app: QApplication, name: str) -> None:
    _drain(app)
    assert window.grab().save(str(OUTPUT / name))


def main() -> None:
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    window = MainWindow(development_mode=True)
    window.resize(1600, 980)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    dev = window.findChild(DevToolsView)
    contracts = window.findChild(ContractsView)
    resources = window.findChild(ResourcesViewV2)
    assert tabs is not None and dev is not None and contracts is not None and resources is not None

    tabs.setCurrentWidget(dev)
    _save(window, app, "01_dev_tab_restored.png")

    tabs.setCurrentWidget(contracts)
    offer_card = next(card for card in contracts.findChildren(QFrame, "contractCard") if card.property("kind") == "regular")
    used = set()
    for selector in offer_card.findChildren(QComboBox, "contractProductSelect"):
        index = next(index for index in range(1, selector.count()) if selector.itemData(index) not in used)
        used.add(selector.itemData(index))
        selector.setCurrentIndex(index)
    offer_card.findChild(QPushButton, "acceptContractButton").click()
    active = contracts._state.contracts.active["regular"]
    for resource_id, required in active.offer.requirements.items():
        active.delivered[resource_id] = required * 0.55
    contracts.refresh()
    _save(window, app, "02_contract_progress_in_place.png")

    tabs.setCurrentWidget(resources)
    for definition_id, production_id, alternate_id, filename in (
        ("machine.drilling", "resource.crude_oil", "resource.natural_gas", "03_drilling_rig_resource_control.png"),
        ("machine.agriculture", "resource.wheat", "resource.corn", "04_harvester_resource_control.png"),
    ):
        card_id = f"qa-{definition_id}"
        resources._command_bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)))
        resources._command_bus.dispatch(InstallCardInHall("site-1", 0, card_id, "resources"))
        resources._state.production_progress.unlocked_production_ids.update({production_id, alternate_id})
        resources._command_bus.dispatch(SelectMachineProduction(card_id, production_id, production_id.removeprefix("resource.")))
        resources.refresh_view()
        resources._open_production_drawer(card_id)
        _save(window, app, filename)
        resources._close_drawer()
        resources._command_bus.dispatch(RemoveCardFromHall("site-1", 0, "resources"))
    window.close()
    print(f"Captured 4 offscreen screenshots in {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
