from __future__ import annotations
from release_test_support import legacy_component

import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QScrollArea, QTabWidget, QWidget

from production_zero.core.cards import CardStack, CardStackKey, create_card_instance
from production_zero.core.commands import CommandBus, UnlockProductionSlot
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.state import FactoryHall, GameState, factory_slot_unlock_cost
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.factory_view import FactoryCardSelectionTile
from production_zero.ui.factory_view_v2 import FactoryV2TrackPanel, FactoryViewV2, prototype_family_for_definition
from production_zero.ui.game_ui import GameButton
from production_zero.ui.inventory_view import InventoryFilterScroll, InventoryView
from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, machine_art_family_for_machine_type
from production_zero.ui.main_window import MainWindow
from production_zero.ui.production_board_views import EnergyViewV2


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_split_board_slot_prices_start_positive_and_progress_monotonically() -> None:
    for board,start_slots,maximum_slots,first in (('resources',1,10,90),('energy',1,5,100),('factory',3,10,40)):
        prices = [
            factory_slot_unlock_cost(1, slot, start_slots_per_line=start_slots,board_kind=board)
            for slot in range(start_slots + 1, maximum_slots + 1)
        ]
        assert prices
        assert prices[0] == first
        assert all(price > 0 for price in prices)
        assert prices == sorted(prices)

    state = GameState(rng_seed=1)
    state.cash.amount = 1_000
    state.resource_sites["site-1"] = FactoryHall(
        "site-1", "Site 1", 1, board_kind="resources", max_lines=3,
        max_slots_per_line=10, start_unlocked_lines=1, start_slots_per_line=1,
    )
    CommandBus(state).dispatch(UnlockProductionSlot("site-1", "site-1.line-1", "resources"))
    assert state.cash.amount == 910.0


def test_primary_machine_art_uses_explicit_runtime_type_mapping() -> None:
    _app()
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    expected = {
        MachineType.EXTRACTOR: ("extractor", "extractor.png"),
        MachineType.DRILLING: ("drilling", "drilling_rig.png"),
        MachineType.AGRICULTURE: ("agriculture", "agriculture.png"),
    }
    for machine_type, (family, filename) in expected.items():
        assert machine_art_family_for_machine_type(machine_type) == family
        assert MACHINE_RASTER_ASSETS[family].name == filename
        definition = next(
            item for item in definitions.values()
            if getattr(item, "machine_type", None) == machine_type
        )
        assert prototype_family_for_definition(definition) == family
        card = create_card_instance(f"qa-{family}", definition.definition_id, CardKind.MACHINE, Rarity.COMMON)
        tile = FactoryCardSelectionTile(CardStack(CardStackKey.from_card(card), (card,)), definition)
        assert tile.property("cardType") == family


def test_inventory_filter_overflow_has_a_visible_scroll_mechanism() -> None:
    _app()
    content = QWidget()
    layout = QHBoxLayout(content)
    wide_control = QLabel("ALL FILTER CONTROLS")
    wide_control.setMinimumWidth(900)
    layout.addWidget(wide_control)
    scroll = InventoryFilterScroll(content, "inventoryFilterScroll", 900)
    scroll.resize(420, 80)
    scroll.show()
    QApplication.processEvents()
    assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert scroll.horizontalScrollBar().maximum() > 0
    assert scroll.horizontalScrollBar().isVisible()


def test_disabled_primary_button_is_visually_neutral() -> None:
    _app()
    button = GameButton("UNLOCK $750", variant="primary")
    button.resize(180, 48)
    button.show()
    enabled = QColor(button.grab().toImage().pixelColor(18, 18))
    button.setEnabled(False)
    QApplication.processEvents()
    disabled = QColor(button.grab().toImage().pixelColor(18, 18))
    assert disabled.saturation() < enabled.saturation()
    assert disabled.saturation() < 40


def test_release_shell_hides_dev_and_tracks_continuation_state() -> None:
    _app()
    window = MainWindow(development_mode=False)
    window.resize(1366, 768)
    window.show()
    QApplication.processEvents()
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert tabs is not None
    assert "Dev" not in [tabs.tabText(index) for index in range(tabs.count())]
    factory = window.findChild(FactoryViewV2)
    tabs.setCurrentWidget(factory)
    for _ in range(4):
        QApplication.processEvents()
    cue = factory.findChild(QLabel, "factoryV2TrackContinuationCue")
    assert cue is not None
    has_overflow = factory.findChild(QScrollArea, "factoryV2Scroll").horizontalScrollBar().maximum() > 0
    assert cue.isVisible() is has_overflow


def test_crafting_cta_and_energy_tracks_use_compact_viewport_space() -> None:
    _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    inventory = legacy_component(window, InventoryView)
    assert tabs is not None and inventory is not None
    tabs.setCurrentWidget(inventory)
    inventory_filter = inventory.findChild(QScrollArea, "inventoryFilterScroll")
    QApplication.processEvents()
    assert inventory_filter is not None
    assert inventory_filter.horizontalScrollBar().maximum() > 0
    assert inventory_filter.horizontalScrollBar().isVisible()
    inventory.findChild(QTabWidget, "inventorySubTabs").setCurrentIndex(1)
    inventory._set_craft_selection_mode("workspace")
    QApplication.processEvents()
    craft_button = inventory.findChild(QWidget, "craftCardButton")
    workspace_scroll = inventory.findChild(QScrollArea, "inventoryWorkspaceScroll")
    assert craft_button is not None and workspace_scroll is not None
    button_rect = craft_button.rect().translated(craft_button.mapTo(workspace_scroll.viewport(), craft_button.rect().topLeft()))
    assert workspace_scroll.viewport().rect().intersects(button_rect)

    window.resize(1920, 1080)
    energy = window.findChild(EnergyViewV2)
    tabs.setCurrentWidget(energy)
    QApplication.processEvents()
    scroll = energy.findChild(QScrollArea, "factoryV2Scroll")
    tracks = energy.findChildren(FactoryV2TrackPanel, "factoryV2ProductionTrack")
    assert scroll is not None and tracks
    top_gap = tracks[0].mapTo(scroll.viewport(), tracks[0].rect().topLeft()).y()
    assert 0 <= top_gap <= 24
