import os
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AssignFreightCard, CommandBus, InstallCardInHall, InstallFreightCard
from production_zero.core.enums import Rarity
from production_zero.core.freight import FreightFacility, start_outbound_shipment_for_card
from production_zero.core.mk_upgrades import mk_upgrade_cost
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import serialize_game_state
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.game_ui import GameButton
from production_zero.ui.group_actions import fill_inventory_slots, install_snapshot
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2
from production_zero.ui.release_dialogs import IndustrialDialog


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


@pytest.fixture(autouse=True)
def cleanup(app, monkeypatch):
    messages = []
    for module in ("release_board", "freight_upgrade", "release_dialogs"):
        monkeypatch.setattr(f"production_zero.ui.{module}.inform", lambda *args: messages.append(args))
    yield messages
    for widget in app.topLevelWidgets():
        QTest.keyRelease(widget, Qt.Key.Key_Control)
        QTest.keyRelease(widget, Qt.Key.Key_Shift)
        widget.close()
        widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def board(definitions, kind, *, installed=2, inventory=4, machine=None, freight_type="garage_depot"):
    state = GameState(351)
    state.cash.amount = 1e12
    state.warehouse_capacity = 1e6
    did = machine or {"factory": "machine.processor", "resources": "machine.extractor",
                      "energy": "energy.solar_array", "freight": "freight.truck"}[kind]
    if kind == "freight":
        unit = FreightFacility("unit", "Unit", facility_type=freight_type, slot_count=8, line_capacity=4)
        state.freight.facilities = {"unit": unit}
    else:
        unit = FactoryHall("unit", "Unit", 10, board_kind=kind, max_lines=2, max_slots_per_line=5,
                           start_unlocked_lines=2, start_slots_per_line=5,
                           specialization=did if kind == "resources" else None)
        state.production_units(kind)["unit"] = unit
    for i in range(installed + inventory):
        cid = f"card-{i:02}"
        state.cards[cid] = create_card_instance(cid, did, definitions[did].card_kind, Rarity.COMMON)
        if i < installed:
            command = (InstallFreightCard("unit", i, cid, definitions) if kind == "freight"
                       else InstallCardInHall("unit", i, cid, kind))
            command.apply(state)
            if kind not in {"freight", "energy"}:
                state.ensure_machine_production(cid, "")
    if kind not in {"freight", "energy"}:
        state.production_progress.unlocked_production_ids.update(p.production_id for p in definitions[did].available_production_options)
    bus = CommandBus(state)
    if kind == "freight":
        resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
        view = FreightView(state, bus, definitions, resources)
    else:
        cls = {"factory": FactoryViewV2, "resources": ResourcesViewV2, "energy": EnergyViewV2}[kind]
        view = cls(state, bus, definitions)
    view.resize(1250, 850)
    view.show()
    QApplication.processEvents()
    return view, state, unit


def select(view, kind, indexes):
    if kind == "freight":
        view._slot_interaction.select_positions(indexes)
        view._slot_interaction.update_selection()
    else:
        view._select_slot_positions(indexes)
        view._update_selection_visuals()


def slot_widget(view, kind, index):
    if kind == "freight":
        return next(w for w in view._slot_interaction._cards() if w._freight_destination[1] == index)
    return view._slot_widgets[index]


@pytest.mark.parametrize("kind,machine,production", (
    ("factory", "machine.processor", "recipe.processor.iron"),
    ("resources", "machine.extractor", "resource.iron_ore"),
    ("resources", "machine.drilling", "resource.crude_oil"),
    ("resources", "machine.agriculture", "resource.wheat"),
))
def test_direct_resource_click_configures_entire_selection(definitions, kind, machine, production):
    view, state, unit = board(definitions, kind, machine=machine, installed=3)
    state.production_progress.unlocked_production_ids.add(production)
    select(view, kind, (0, 1))
    widget = slot_widget(view, kind, 0)
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=widget._resource_control_rect().center().toPoint())
    assert view._selected_machines == {"card-00", "card-01"}
    output = definitions[machine].production_option(production).output_resource
    view._apply_production_option(production, output)
    assert [state.machine_production[cid].selected_production_id for cid in ("card-00", "card-01")] == [production] * 2
    assert state.machine_production["card-02"].selected_production_id is None


def test_mixed_factory_selection_only_configures_compatible_machines(definitions):
    view, state, unit = board(definitions, "factory")
    state.cards["card-01"] = create_card_instance("card-01", "machine.fabricator", definitions["machine.fabricator"].card_kind, Rarity.COMMON)
    state.ensure_machine_production("card-01", "")
    view.refresh_view()
    select(view, "factory", (0, 1))
    view._open_production_drawer("card-00")
    assert "compatible machines only" in view.findChild(QLabel, "productionCurrentLabel").text()
    view._apply_production_option("recipe.processor.iron", "iron")
    assert state.machine_production["card-00"].selected_production_id == "recipe.processor.iron"
    assert state.machine_production["card-01"].selected_production_id is None


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_ctrl_and_shift_select_empty_and_occupied_slots(definitions, kind):
    view, state, unit = board(definitions, kind)
    first = slot_widget(view, kind, 2)
    QTest.mouseClick(first, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
    assert not (view._drawer_open if kind == "freight" else view._drawer_mode)
    assert view._selected_empty_slots == {2}
    QTest.mouseClick(slot_widget(view, kind, 4), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    assert view._selected_empty_slots == {2, 3, 4}
    QTest.mouseClick(slot_widget(view, kind, 3), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier)
    assert view._selected_empty_slots == {2, 4}
    assert slot_widget(view, kind, 2).property("selected")
    assert not slot_widget(view, kind, 3).property("selected")


@pytest.mark.parametrize("kind", ("factory", "resources", "energy", "freight"))
@pytest.mark.parametrize("available", (1, 2, 4))
def test_fill_selected_slots_left_to_right_without_touching_other_slots(definitions, kind, available):
    view, state, unit = board(definitions, kind, inventory=available)
    select(view, kind, (6, 4, 3, 2))
    if kind == "freight":
        view._open_drawer(2)
    else:
        view._on_slot_clicked(2)
    before_cash = state.cash.amount
    view._install_card_from_selection("card-02")
    expected = {2, 3, 4, 6}
    filled = set(sorted(expected)[:available])
    assert {i for i in expected if unit.slots[i].card_id} == filled
    assert unit.slots[0].card_id == "card-00" and unit.slots[1].card_id == "card-01"
    assert unit.slots[5].card_id is None
    assert view._selected_empty_slots == expected - filled
    assert state.cash.amount == before_cash
    assert len(state.installed_card_ids() | state.installed_freight_card_ids()) == 2 + available


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_fill_never_substitutes_other_rarity_or_mk(definitions, kind):
    view, state, unit = board(definitions, kind, inventory=2)
    state.cards["card-03"] = replace(state.cards["card-03"], mk_level=4)
    select(view, kind, (2, 3, 4))
    snapshot = install_snapshot(view, kind, unit, (2, 3, 4))
    assert fill_inventory_slots(view, snapshot, "card-02") == (2,)
    assert unit.slots[2].card_id == "card-02"
    assert unit.slots[3].card_id is None
    assert "card-03" not in state.installed_card_ids() | state.installed_freight_card_ids()


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
@pytest.mark.parametrize("change", ("occupied", "locked", "session", "building"))
def test_stale_inventory_targets_cannot_partially_install(definitions, kind, change):
    view, state, unit = board(definitions, kind)
    snapshot = install_snapshot(view, kind, unit, (2, 3))
    if change == "occupied":
        unit.slots[3].card_id = "card-05"
    elif change == "locked":
        if kind == "freight":
            unit.purchased_slot_indexes = set(range(8)) - {3}
        else:
            unit.production_lines[0].slot_indexes.remove(3)
    elif change == "session":
        state.cards = dict(state.cards)
    else:
        if kind == "freight":
            view._selected_facility_id = "other"
        else:
            view._selected_hall_id = "other"
    before = serialize_game_state(state)
    with pytest.raises(ValueError):
        fill_inventory_slots(view, snapshot, "card-02")
    assert serialize_game_state(state) == before


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
@pytest.mark.parametrize("scope", ("card", "building"))
def test_mk_actions_upgrade_group_once_and_skip_mk99(definitions, monkeypatch, kind, scope):
    view, state, unit = board(definitions, kind, installed=3)
    state.cards["card-01"] = replace(state.cards["card-01"], mk_level=99)
    if kind == "freight":
        view.refresh()
    else:
        view.refresh_view()
    select(view, kind, (0, 1))
    module = "freight_upgrade" if kind == "freight" else "release_board"
    quotes = []
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", lambda *args: quotes.append(args[2]) or True)
    ids = ("card-00", "card-02") if scope == "building" else ("card-00",)
    cost = round(sum(mk_upgrade_cost(state.cards[cid], definitions[state.cards[cid].definition_id]) for cid in ids), 2)
    before_cash = state.cash.amount
    button = (view.findChild(GameButton, "buildingMkUpgrade") if scope == "building" else
              slot_widget(view, kind, 1).findChild(GameButton, "freightMkUpgrade" if kind == "freight" else "machineMkUpgrade"))
    assert button.isEnabled()
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert [state.cards[f"card-{i:02}"].mk_level for i in range(3)] == ([2, 99, 2] if scope == "building" else [2, 99, 1])
    assert state.cash.amount == pytest.approx(before_cash - cost)
    assert len(quotes) == 1
    assert all(state.cards[f"card-{i:02}"].mk_level == 1 for i in range(3, 7))


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_building_upgrade_does_not_include_other_buildings_or_inventory(definitions, monkeypatch, kind):
    view, state, unit = board(definitions, kind, installed=3)
    other = deepcopy(unit)
    if kind == "freight":
        other.facility_id = "other"
        state.freight.facilities["other"] = other
    else:
        other.hall_id = "other"
        state.production_units(kind)["other"] = other
    for slot in other.slots:
        slot.card_id = None
    other.slots[0].card_id = "card-03"
    module = "freight_upgrade" if kind == "freight" else "release_board"
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", lambda *args: True)
    view.findChild(GameButton, "buildingMkUpgrade").click()
    assert [state.cards[f"card-{i:02}"].mk_level for i in range(4)] == [2, 2, 2, 1]


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
@pytest.mark.parametrize("case", ("cancel", "poor", "changed", "moved", "repeat"))
def test_upgrade_is_atomic_and_revalidates_confirmation(definitions, monkeypatch, cleanup, kind, case):
    view, state, unit = board(definitions, kind)
    select(view, kind, (0, 1))
    module = "freight_upgrade" if kind == "freight" else "release_board"
    if case == "poor":
        state.cash.amount = 0
    def confirm(*args):
        if case == "changed":
            state.cards["card-01"] = replace(state.cards["card-01"], mk_level=4)
        if case == "moved":
            unit.slots[0].card_id, unit.slots[2].card_id = None, "card-00"
        return case != "cancel"
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", confirm)
    before_cash = state.cash.amount
    view.findChild(GameButton, "buildingMkUpgrade").click()
    if case == "repeat":
        after = serialize_game_state(state)
        view.findChild(GameButton, "buildingMkUpgrade").click()
        assert serialize_game_state(state) == after
    else:
        assert state.cash.amount == before_cash
        assert state.cards["card-00"].mk_level == 1
        assert state.cards["card-01"].mk_level == (4 if case == "changed" else 1)


@pytest.mark.parametrize("kind", ("factory", "resources"))
def test_real_context_menu_has_working_group_mk_action(definitions, monkeypatch, kind):
    view, state, unit = board(definitions, kind)
    select(view, kind, (0, 1))
    monkeypatch.setattr("production_zero.ui.release_board.confirm", lambda *args: True)
    found = []
    def choose():
        dialog = next(w for w in QApplication.topLevelWidgets() if isinstance(w, IndustrialDialog) and w.isVisible())
        buttons = [w for w in dialog.findChildren(GameButton) if w.text() == "MK UPGRADE"]
        found.extend(buttons)
        if buttons:
            buttons[0].click()
        else:
            dialog.reject()
    QTimer.singleShot(0, choose)
    view._card_actions("card-00")
    assert found
    assert state.cards["card-00"].mk_level == state.cards["card-01"].mk_level == 2


def test_direct_freight_assignment_preserves_group_and_applies_route(definitions):
    view, state, unit = board(definitions, "freight", installed=3)
    state.ensure_resource("iron_ore").amount = 50
    select(view, "freight", (0, 1))
    panel = slot_widget(view, "freight", 0).findChild(QWidget, "freightAssignmentPanel")
    QTest.mouseClick(panel, Qt.MouseButton.LeftButton)
    assert view._route_group == ("card-00", "card-01")
    assert not state.freight.assignments
    view._select_assignment_resource("iron_ore")
    view._choose_assignment_destination("market")
    view._confirm_assignment()
    assert set(state.freight.assignments) == {"card-00", "card-01"}
    assert all(a.resource_id == "iron_ore" and a.destination_kind == "market" for a in state.freight.assignments.values())


def test_upgrading_freight_group_preserves_in_transit_cargo(definitions, monkeypatch):
    view, state, unit = board(definitions, "freight")
    AssignFreightCard("card-00", "iron_ore", "market").apply(state)
    shipment = start_outbound_shipment_for_card(state.freight, state.cards, definitions, card_id="card-00",
        destination_kind="market", resource_id="iron_ore", quantity=20, market_price=5)
    assert shipment is not None
    before = deepcopy(shipment)
    monkeypatch.setattr("production_zero.ui.freight_upgrade.confirm", lambda *args: True)
    view.findChild(GameButton, "buildingMkUpgrade").click()
    assert shipment == before
    assert state.cards["card-00"].mk_level == state.cards["card-01"].mk_level == 2


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_building_button_is_next_to_pause_and_disabled_for_empty_building(definitions, kind):
    view, state, unit = board(definitions, kind, installed=0)
    button = view.findChild(GameButton, "buildingMkUpgrade")
    assert button.text() == "⇈" and not button.isEnabled()
    layout = button.parentWidget().layout()
    index = layout.indexOf(button)
    assert "Pause" in layout.itemAt(index - 1).widget().objectName() or "pause" in layout.itemAt(index - 1).widget().objectName()


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_rectangle_selection_includes_empty_slots(definitions, kind):
    view, state, unit = board(definitions, kind)
    first, last = slot_widget(view, kind, 0), slot_widget(view, kind, 3)
    if kind == "freight":
        surface = first.parentWidget()
    else:
        surface = view._release_selection_surface
    start = first.mapTo(surface, QPoint(1, 1))
    end = last.mapTo(surface, last.rect().bottomRight())
    QTest.mousePress(surface, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(surface, end)
    QTest.mouseRelease(surface, Qt.MouseButton.LeftButton, pos=end)
    assert view._selected_empty_slots == {2, 3}
    selected = view._selected_vehicles if kind == "freight" else view._selected_machines
    assert selected == {"card-00", "card-01"}
    assert all(slot_widget(view, kind, i).property("selected") for i in range(4))


@pytest.mark.parametrize("facility,did", (("rail_station", "freight.train"), ("airport", "freight.aircraft"), ("harbor", "freight.ship")))
def test_bulk_fill_and_building_upgrade_work_for_each_freight_type(definitions, monkeypatch, facility, did):
    view, state, unit = board(definitions, "freight", machine=did, freight_type=facility, inventory=2)
    select(view, "freight", (2, 3, 4))
    view._open_drawer(2)
    view._install_card_from_selection("card-02")
    assert unit.slots[2].card_id == "card-02" and unit.slots[3].card_id == "card-03"
    assert unit.slots[4].card_id is None
    assert view._selected_vehicles == {"card-02", "card-03"}
    monkeypatch.setattr("production_zero.ui.freight_upgrade.confirm", lambda *args: True)
    view.findChild(GameButton, "buildingMkUpgrade").click()
    assert all(c.mk_level == 2 for c in state.cards.values())


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_clicking_unselected_card_upgrade_keeps_action_local(definitions, monkeypatch, kind):
    view, state, unit = board(definitions, kind, installed=3)
    select(view, kind, (0, 1))
    module = "freight_upgrade" if kind == "freight" else "release_board"
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", lambda *args: True)
    slot_widget(view, kind, 2).findChild(GameButton, "freightMkUpgrade" if kind == "freight" else "machineMkUpgrade").click()
    assert [state.cards[f"card-{i:02}"].mk_level for i in range(3)] == [1, 1, 2]


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_all_mk99_building_disables_button(definitions, kind):
    view, state, unit = board(definitions, kind)
    for cid in ("card-00", "card-01"):
        state.cards[cid] = replace(state.cards[cid], mk_level=99)
    if kind == "freight":
        view.refresh_runtime()
    else:
        view._refresh_runtime_widgets()
    assert not view.findChild(GameButton, "buildingMkUpgrade").isEnabled()


@pytest.mark.parametrize("kind", ("factory", "resources"))
def test_recipe_picker_rejects_moved_group(definitions, cleanup, kind):
    view, state, unit = board(definitions, kind)
    select(view, kind, (0, 1))
    view._open_production_drawer("card-00")
    unit.slots[1].card_id, unit.slots[2].card_id = None, "card-01"
    before = serialize_game_state(state)
    production, output = ("recipe.processor.iron", "iron") if kind == "factory" else ("resource.iron_ore", "iron_ore")
    view._apply_production_option(production, output)
    assert serialize_game_state(state) == before
    assert cleanup


def test_locked_freight_slot_still_unlocks_instead_of_opening_inventory(definitions):
    view, state, unit = board(definitions, "freight", installed=0)
    unit.purchased_slot_indexes = {0, 1, 2}
    view.refresh()
    locked = slot_widget(view, "freight", 3)
    assert locked.property("slotState") == "locked"
    QTest.mouseClick(locked, Qt.MouseButton.LeftButton)
    assert 3 in unit.unlocked_slot_indexes()
    assert not view._drawer_open


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_bulk_placement_and_upgrades_survive_save_load(definitions, monkeypatch, kind):
    from production_zero.persistence.sqlite_store import deserialize_game_state
    view, state, unit = board(definitions, kind)
    select(view, kind, (2, 3))
    if kind == "freight":
        view._open_drawer(2)
    else:
        view._on_slot_clicked(2)
    view._install_card_from_selection("card-02")
    module = "freight_upgrade" if kind == "freight" else "release_board"
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", lambda *args: True)
    view.findChild(GameButton, "buildingMkUpgrade").click()
    restored = deserialize_game_state(serialize_game_state(state))
    restored_unit = restored.freight.facilities["unit"] if kind == "freight" else restored.production_units(kind)["unit"]
    assert [s.card_id for s in restored_unit.slots] == [s.card_id for s in unit.slots]
    assert all(restored.cards[f"card-{i:02}"].mk_level == 2 for i in range(4))
    assert restored.cash.amount == state.cash.amount


@pytest.mark.parametrize("kind", ("factory", "resources", "freight"))
def test_direct_mk_button_upgrades_every_eligible_selected_card(definitions, monkeypatch, kind):
    view, state, unit = board(definitions, kind, installed=3)
    select(view, kind, (0, 1))
    module = "freight_upgrade" if kind == "freight" else "release_board"
    monkeypatch.setattr(f"production_zero.ui.{module}.confirm", lambda *args: True)
    button = slot_widget(view, kind, 0).findChild(
        GameButton, "freightMkUpgrade" if kind == "freight" else "machineMkUpgrade",
    )
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    assert [state.cards[f"card-{i:02}"].mk_level for i in range(3)] == [2, 2, 1]
    assert (view._selected_vehicles if kind == "freight" else view._selected_machines) == {"card-00", "card-01"}
