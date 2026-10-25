from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard
from production_zero.core.enums import CardKind, Rarity
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "artifacts" / "resource_selection_ui"
SIZES = (
    ("1366x768", 1366, 768),
    ("1600x980", 1600, 980),
    ("1920x1080", 1920, 1080),
)


class _ClickEvent:
    def button(self):
        return Qt.MouseButton.LeftButton

    def position(self):
        return QPointF(20, 52)


def _drain(app: QApplication) -> None:
    for _ in range(6):
        app.processEvents()


def _load_fonts() -> None:
    for font_path in (
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/bahnschrift.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))


def _open_factory_resource_selection(factory: FactoryViewV2) -> None:
    tile = next(
        tile
        for tile in factory.findChildren(QFrame, "factoryCardSelectionTile")
        if "EXTRACTOR" in tile.findChild(QLabel, "factoryCardSelectionTileName").text()
    )
    tile.mousePressEvent(_ClickEvent())
    card_id = factory._state.halls["hall-1"].slots[0].card_id
    if card_id is None:
        raise RuntimeError("Failed to install starter extractor for Factory capture.")
    factory._open_production_drawer(card_id)


def _add_freight_capture_card(freight: FreightView) -> str:
    card = create_card_instance("qa-capture-truck", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    freight._command_bus.dispatch(AddCard(card))
    freight.refresh()
    return card.card_id


def _open_freight_resource_selection(freight: FreightView, card_id: str) -> None:
    freight._open_drawer(0)
    card_tile = next(tile for tile in freight.findChildren(QFrame, "freightSelectionCard") if tile.property("cardId") == card_id)
    card_tile.mousePressEvent(_ClickEvent())
    freight._open_assignment_view(card_id)


def _select_tab(tabs: QTabWidget, label: str) -> None:
    for index in range(tabs.count()):
        if tabs.tabText(index) == label or label.lower() in tabs.tabText(index).lower():
            tabs.setCurrentIndex(index)
            return
    raise RuntimeError(f"Tab not found: {label}")


def _grab_current_tab(tabs: QTabWidget, stem: str, label: str) -> None:
    current = tabs.currentWidget()
    if current is None:
        raise RuntimeError(f"No current widget for {stem}.")
    current.grab().save(str(OUTPUT_DIR / f"{stem}_{label}.png"))


def _open_common_supply(window: MainWindow, tabs: QTabWidget) -> None:
    _select_tab(tabs, "Supply")
    buttons = window.findChildren(QPushButton, "supplySectionButton")
    if len(buttons) < 2:
        raise RuntimeError("Common Supply selector not found.")
    buttons[1].click()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _load_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for label, width, height in SIZES:
        window = MainWindow()
        window.findChild(FactoryViewV2).pause_simulation()
        window.resize(width, height)
        window.show()
        _drain(app)

        factory = window.findChild(FactoryViewV2)
        freight = window.findChild(FreightView)
        tabs = window.findChild(QTabWidget, "mainTabs")
        if factory is None or freight is None or tabs is None:
            raise RuntimeError("Factory or Freight view not found.")

        _select_tab(tabs, "Factory")
        factory._on_slot_clicked(0)
        _drain(app)
        factory.findChild(QFrame, "factoryCardSelectionView").grab().save(str(OUTPUT_DIR / f"factory_card_selection_{label}.png"))
        _open_factory_resource_selection(factory)
        _drain(app)
        factory.findChild(QFrame, "productionSelectionView").grab().save(str(OUTPUT_DIR / f"factory_resource_selection_{label}.png"))
        factory._close_drawer()
        factory._open_production_guide()
        _drain(app)
        factory.findChild(QFrame, "productionGuideView").grab().save(str(OUTPUT_DIR / f"production_guide_{label}.png"))

        _select_tab(tabs, "Freight")
        card_id = _add_freight_capture_card(freight)
        freight._open_drawer(0)
        _drain(app)
        freight.findChild(QFrame, "freightCardSelectionView").grab().save(str(OUTPUT_DIR / f"freight_card_selection_{label}.png"))
        _open_freight_resource_selection(freight, card_id)
        _drain(app)
        freight.findChild(QFrame, "freightAssignmentSelectionView").grab().save(str(OUTPUT_DIR / f"freight_resource_selection_{label}.png"))

        _open_common_supply(window, tabs)
        _drain(app)
        _grab_current_tab(tabs, "common_supply", label)

        for tab_label, stem in (("Charts", "charts"), ("Market", "market"), ("Contracts", "contracts")):
            _select_tab(tabs, tab_label)
            _drain(app)
            _grab_current_tab(tabs, stem, label)
        window.close()
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
