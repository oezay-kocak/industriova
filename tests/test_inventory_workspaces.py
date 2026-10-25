import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, CommandBus
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.theme import APP_STYLESHEET


@pytest.fixture
def view():
    app = QApplication.instance() or QApplication([])
    fonts = [QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{name}") for name in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf")]
    previous_style = app.styleSheet()
    app.setStyleSheet(APP_STYLESHEET)
    state = GameState(rng_seed=990)
    bus = CommandBus(state)
    for index in range(4):
        bus.dispatch(AddCard(create_card_instance(f"material-{index}", "machine.extractor", CardKind.MACHINE, Rarity.UNCOMMON, bonus_tenths=30)))
    widget = InventoryView(state, load_card_definitions(Path("src/production_zero/data/game_definitions.json")), command_bus=bus, release_mode=False)
    widget.resize(1280, 900)
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.setStyleSheet(previous_style)
    for font_id in fonts:
        if font_id >= 0:
            QFontDatabase.removeApplicationFont(font_id)


def test_craft_workspace_navigation_confirmation_and_removed_material(view):
    view._tabs.setCurrentIndex(1)
    view._craft_target_search.setText("extractor")
    view._select_craft_target("machine.extractor")
    assert view._craft_pages.currentIndex() == 1
    for index in range(4):
        slot = next(slot for slot in view.findChildren(QFrame, "craftMaterialSlot") if not slot.property("filled"))
        slot.mousePressEvent(None)
        assert view._craft_selection_mode == "materials"
        view._toggle_craft_material_group((f"material-{index}",))
        assert view._craft_pages.currentIndex() == 1
    view._craft_confirm.setChecked(True)
    assert view._craft_button.isEnabled()
    del view._state.cards["material-0"]
    view.refresh()
    assert len(view._selected_craft_material_ids) == 3
    assert not view._craft_confirm.isChecked()
    assert not view._craft_button.isEnabled()
    back = view._craft_preview_panel.findChild(QPushButton, "inventoryWorkspaceBack")
    back.click()
    assert view._craft_pages.currentIndex() == 0
    assert view._craft_target_search.text() == "extractor"


def test_target_grid_deduplicates_aliases_and_reflows_after_resize(view):
    view._tabs.setCurrentIndex(1)
    definitions = view._craft_target_definitions(include_filters=False)
    assert len(definitions) == len({definition.definition_id for definition in definitions})
    for width in (1600, 1000, 1400):
        view.resize(width, 760)
        for _ in range(4):
            QApplication.processEvents()
        columns = view._grid_columns_for_scroll(view._craft_target_scroll)
        grid = view._craft_target_grid
        assert max(grid.getItemPosition(index)[1] for index in range(grid.count())) == columns - 1
        assert view._craft_target_scroll.horizontalScrollBar().maximum() == 0


def test_target_cards_show_and_filter_by_runtime_output_rarities(view):
    view._tabs.setCurrentIndex(1)
    assert [view._craft_target_rarity.itemText(index) for index in range(view._craft_target_rarity.count())] == [
        "Rare",
        "Epic",
        "Legendary",
    ]
    assert "Common" not in [view._craft_target_rarity.itemText(index) for index in range(view._craft_target_rarity.count())]
    assert "Uncommon" not in [view._craft_target_rarity.itemText(index) for index in range(view._craft_target_rarity.count())]

    for output_name, input_rarity in (("Rare", Rarity.UNCOMMON), ("Epic", Rarity.RARE), ("Legendary", Rarity.EPIC)):
        view._craft_target_rarity.setCurrentText(output_name)
        QApplication.processEvents()
        cards = view.findChildren(QFrame, "craftTargetCard")
        assert cards
        assert all(card.property("cardMeta") == output_name.upper() for card in cards)
        assert all(card.property("rarity") == output_name.lower() for card in cards)
        assert view._current_craft_input_rarity() is input_rarity




@pytest.mark.parametrize("size", [(1000, 760), (1280, 610), (1600, 1000)])
def test_workspaces_render_without_card_clipping_or_hover(view, size):
    view.resize(*size)
    view._tabs.setCurrentIndex(1)
    view._select_craft_target("machine.extractor")
    view._toggle_craft_material_group(("material-0",))
    QApplication.processEvents()
    result = view.findChild(QFrame, "craftResultCard")
    assert view._craft_pages.widget(1).verticalScrollBar().maximum() == 0
    assert view._craft_pages.widget(1).horizontalScrollBar().maximum() == 0
    assert result.parentWidget().rect().contains(result.geometry())
    result.hovered.emit()
    assert view._hover_popup is None or not view._hover_popup.isVisible()
    folder = Path("artifacts/inventory-workspaces")
    folder.mkdir(parents=True, exist_ok=True)
    view.grab().save(str(folder / f"craft-{size[0]}.png"))

@pytest.mark.parametrize("size", [(1366, 768), (1920, 1080)])
def test_standard_main_window_workspaces_fit_with_reachable_actions(size):
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "scripts/validate_inventory_workspaces.py", *map(str, size)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
