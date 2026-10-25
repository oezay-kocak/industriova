from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QTabWidget

from production_zero.core.contracts import DAILY, REGULAR, WEEKLY
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.main_window import MainWindow


OUTPUT = Path("artifacts/global-storage-contracts")


def _drain(app: QApplication) -> None:
    for _ in range(6):
        app.processEvents()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    window = MainWindow()
    window.resize(1600, 980)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    contracts = window.findChild(ContractsView)
    inventory = window.findChild(InventoryView)
    if tabs is None or contracts is None or inventory is None:
        raise RuntimeError("Required QA views not found")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    state = contracts._state
    for resource_id, amount in {
        "iron_ore": 145,
        "coal": 70,
        "copper_ore": 88,
        "bauxite": 54,
    }.items():
        state.ensure_resource(resource_id).amount = amount
    contracts._eligible_product_cache.clear()
    contracts.refresh()
    window._global_header.refresh()

    tabs.setCurrentWidget(inventory)
    inventory.refresh()
    _drain(app)
    assert window.grab().save(str(OUTPUT / "global_storage_inventory.png"))

    tabs.setCurrentWidget(contracts)
    for kind in (REGULAR, DAILY, WEEKLY):
        card = next(
            card for card in contracts.findChildren(QFrame, "contractCard")
            if card.property("kind") == kind
        )
        used = set()
        for selector in card.findChildren(QComboBox, "contractProductSelect"):
            index = next(
                index for index in range(1, selector.count())
                if selector.itemData(index) not in used
            )
            used.add(selector.itemData(index))
            selector.setCurrentIndex(index)
    _drain(app)
    assert window.grab().save(str(OUTPUT / "contract_selectors_2_3_4.png"))

    for kind, count in ((REGULAR, 2), (DAILY, 3), (WEEKLY, 4)):
        card = next(card for card in contracts.findChildren(QFrame, "contractCard") if card.property("kind") == kind)
        assert len(card.findChildren(QComboBox, "contractProductSelect")) == count
    window.close()
    print(f"Captured 2 offscreen screenshots in {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
