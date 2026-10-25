"""Focused offscreen captures for the five 2026-09-10 Severity-C polish items."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QProgressBar, QPushButton, QTabWidget

from production_zero.core.cards import CardInstance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.packs import FULL_PACK, grant_pack
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.main_window import MainWindow
from production_zero.ui.packs_view import PACK_COMPOSITION_MAX_WIDTH, PacksView
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2
from production_zero.ui.unlock_tree_view import UnlockTreeView


OUTPUT = Path("artifacts/final_visual_c_cleanup_2026-09-10")


def _settle(app: QApplication, passes: int = 8) -> None:
    for _ in range(passes):
        app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _capture(window: MainWindow, app: QApplication, name: str) -> None:
    _settle(app)
    path = OUTPUT / f"{name}.png"
    if not window.grab().save(str(path)):
        raise RuntimeError(f"Could not save {path}")


def _single_card(state, card_id: str, definition_id: str, kind: CardKind) -> None:
    state.cards.clear()
    state.cards[card_id] = CardInstance(
        card_id=card_id,
        definition_id=definition_id,
        card_kind=kind,
        rarity=Rarity.COMMON,
        output_bonus_percent=0.0,
        power_bonus_percent=0.0,
    )


def _capture_resolution(app: QApplication, width: int, height: int) -> None:
    size = f"{width}x{height}"
    window = MainWindow(charts_enabled=False)
    window.resize(width, height)
    window.show()
    _settle(app)
    tabs = window.findChild(QTabWidget, "mainTabs")
    resources = window.findChild(ResourcesViewV2)
    factory = window.findChild(FactoryViewV2)
    energy = window.findChild(EnergyViewV2)
    packs = window.findChild(PacksView)
    if not all((tabs, resources, factory, energy, packs)):
        raise RuntimeError("Required focused-capture view is missing")
    factory.pause_simulation()

    tabs.setCurrentWidget(resources)
    resources.refresh_view()
    window._global_header.refresh()
    activity = window._global_header.findChild(QLabel, "factoryV2OperationsActivity")
    progress = window._global_header.findChild(QProgressBar, "factoryV2OperationsProgress")
    assert activity is not None and "ACTIVE SLOTS" in activity.text()
    assert progress is not None
    _capture(window, app, f"c05_production_network_{size}")

    tabs.setCurrentWidget(factory)
    factory._open_production_guide()
    unlock_button = factory.findChild(QPushButton, "productionGuideUnlockTreeButton")
    assert unlock_button is not None
    unlock_button.click()
    _settle(app)
    tree = factory.findChild(UnlockTreeView, "unlockTreeView")
    assert tree is not None
    assert max(edge.opacity() for edge in tree._edge_items if not edge._highlighted) <= 0.48
    _capture(window, app, f"c01_unlock_tree_default_{size}")

    factory._close_drawer()
    factory._open_chain_from_guide("microchip")
    _settle(app)
    assert factory._chain_canvas is not None
    assert factory._chain_canvas._scene_padding == 8.0
    _capture(window, app, f"c02_chain_microchip_{size}")
    factory._close_drawer()

    tabs.setCurrentWidget(packs)
    packs._state.packs.unopened.clear()
    packs.refresh(force=True)
    assert packs._grid_container.width() <= PACK_COMPOSITION_MAX_WIDTH
    _capture(window, app, f"c03_packs_empty_{size}")
    grant_pack(packs._state, FULL_PACK, "focused-c-polish")
    grant_pack(packs._state, FULL_PACK, "focused-c-polish")
    packs.refresh(force=True)
    _capture(window, app, f"c03_packs_populated_{size}")

    if width == 1920:
        board_cards = (
            (resources, "c04_resources_selection", "qa-resource", "machine.extractor", CardKind.MACHINE),
            (factory, "c04_factory_selection", "qa-factory", "machine.processor", CardKind.MACHINE),
            (energy, "c04_energy_selection", "qa-energy", "energy.solar_array", CardKind.ENERGY),
        )
        for board, name, card_id, definition_id, kind in board_cards:
            tabs.setCurrentWidget(board)
            _single_card(board._state, card_id, definition_id, kind)
            board.refresh_view()
            board._on_slot_clicked(0)
            _settle(app)
            count = board.findChild(QLabel, "factoryCardSelectionResultCount")
            assert count is not None and count.text() == "1 COMPATIBLE CARD AVAILABLE"
            _capture(window, app, f"{name}_{size}")
            board._close_drawer()

    window.close()
    window.deleteLater()
    _settle(app)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for width, height in ((1366, 768), (1920, 1080)):
        _capture_resolution(app, width, height)
    print(f"Captured 13 focused screens in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
