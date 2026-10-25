import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import CommandBus, InstallCardInHall
from production_zero.core.enums import Rarity
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.factory_view import FactoryCardSelectionTile
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def inventory():
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    state = GameState(351)
    for did in ("machine.extractor", "machine.drilling", "machine.agriculture", "machine.processor",
                "machine.fabricator", "machine.assembler", "energy.solar_array", "freight.truck"):
        for rarity in (Rarity.COMMON, Rarity.RARE):
            cid = f"{did}:{rarity.value}"
            state.cards[cid] = create_card_instance(cid, did, definitions[did].card_kind, rarity)
    for board in ("resources", "factory", "energy"):
        state.production_units(board)[board] = FactoryHall(
            board, board, 3, board_kind=board, max_lines=1, start_unlocked_lines=1,
        )
    return state, definitions


def dispose(widget):
    widget.close()
    widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("specialization", ("machine.extractor", "machine.drilling", "machine.agriculture"))
def test_resource_picker_only_shows_installable_site_cards(app, inventory, specialization):
    state, definitions = inventory
    site = state.resource_sites["resources"]
    site.specialization = specialization
    view = ResourcesViewV2(state, CommandBus(state), definitions)
    try:
        view._on_slot_clicked(0)
        tiles = view.findChildren(FactoryCardSelectionTile)
        ids = {tile._card_id for tile in tiles}
        expected = {f"{specialization}:common", f"{specialization}:rare"}
        assert ids == expected
        assert view._card_filter_options() == ["All", definitions[specialization].name]
        for cid in expected:
            InstallCardInHall("resources", 0, cid, "resources").apply(state)
            site.slots[0].card_id = None
    finally:
        dispose(view)


@pytest.mark.parametrize("occupant", (None, "machine.drilling", "machine.agriculture"))
def test_legacy_unspecialized_sites_follow_existing_installation_rules(app, inventory, occupant):
    state, definitions = inventory
    site = state.resource_sites["resources"]
    if occupant:
        site.slots[1].card_id = f"{occupant}:common"
    view = ResourcesViewV2(state, CommandBus(state), definitions)
    try:
        allowed = {stack.first_card.definition_id for stack in view._filtered_placeable_stacks()}
        assert allowed == ({occupant} if occupant else {
            "machine.extractor", "machine.drilling", "machine.agriculture",
        })
    finally:
        dispose(view)


def test_switching_sites_refreshes_compatibility_and_filters(app, inventory):
    state, definitions = inventory
    state.resource_sites["resources"].specialization = "machine.extractor"
    state.resource_sites["drilling"] = FactoryHall(
        "drilling", "Drilling Field", 3, specialization="machine.drilling", board_kind="resources",
    )
    view = ResourcesViewV2(state, CommandBus(state), definitions)
    try:
        assert {s.first_card.definition_id for s in view._filtered_placeable_stacks()} == {"machine.extractor"}
        view._selected_hall_id = "drilling"
        assert {s.first_card.definition_id for s in view._filtered_placeable_stacks()} == {"machine.drilling"}
        view._card_rarity_filter_text = "Rare"
        view._card_search_text = definitions["machine.drilling"].name
        assert [s.first_card.card_id for s in view._filtered_placeable_stacks()] == ["machine.drilling:rare"]
        view._card_search_text = definitions["machine.extractor"].name
        assert view._filtered_placeable_stacks() == ()
    finally:
        dispose(view)


def test_picker_is_empty_when_inventory_only_contains_other_site_families(app, inventory):
    state, definitions = inventory
    state.resource_sites["resources"].specialization = "machine.drilling"
    state.cards = {cid: card for cid, card in state.cards.items() if card.definition_id != "machine.drilling"}
    view = ResourcesViewV2(state, CommandBus(state), definitions)
    try:
        view._on_slot_clicked(0)
        assert view.findChildren(FactoryCardSelectionTile) == []
        assert view._card_filter_options() == ["All"]
        assert view.findChild(QWidget, "factoryCardSelectionEmpty") is not None
    finally:
        dispose(view)


@pytest.mark.parametrize("view_type,expected", (
    (FactoryViewV2, {"machine.processor", "machine.fabricator", "machine.assembler"}),
    (EnergyViewV2, {"energy.solar_array"}),
))
def test_other_boards_keep_their_existing_card_families(app, inventory, view_type, expected):
    state, definitions = inventory
    view = view_type(state, CommandBus(state), definitions)
    try:
        assert {s.first_card.definition_id for s in view._filtered_placeable_stacks()} == expected
    finally:
        dispose(view)
