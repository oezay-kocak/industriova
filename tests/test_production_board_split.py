from __future__ import annotations

from importlib.resources import files

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QLineEdit, QPushButton, QScrollArea, QTabWidget, QWidget

from production_zero.core.cards import CardInstance
from production_zero.core.analytics import calculate_resource_flows
from production_zero.core.commands import AddCard, BuildHall, CommandBus, InstallCardInHall, PurchaseProductionUnit, SelectMachineProduction, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.infrastructure_prices import production_facility_price,unit_line_price
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, factory_slot_unlock_cost
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import deserialize_game_state, serialize_game_state
from production_zero.ui.main_window import MainWindow, _create_initial_state
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2
from production_zero.ui.factory_view_v2 import FactoryViewV2


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def _new_state():
    definitions = _definitions()
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    return _create_initial_state(resources, definitions), definitions


def _card(card_id: str, definition_id: str, kind: CardKind = CardKind.MACHINE) -> CardInstance:
    return CardInstance(card_id, definition_id, kind, Rarity.COMMON, 0, 0)


def test_primary_definitions_are_semantically_partitioned() -> None:
    definitions = _definitions()
    outputs = {
        family: {option.output_resource for option in definitions[f"machine.{family}"].available_production_options}
        for family in ("extractor", "drilling", "agriculture")
    }
    assert outputs["drilling"] == {"crude_oil", "natural_gas"}
    assert outputs["agriculture"] == {
        "timber", "wheat", "corn", "soybeans", "sugarcane", "cotton",
        "rapeseed", "potatoes", "fruit", "natural_rubber",
    }
    assert len(outputs["extractor"] | outputs["drilling"] | outputs["agriculture"]) == 49
    assert not (outputs["extractor"] & outputs["drilling"])
    assert not (outputs["extractor"] & outputs["agriculture"])


def test_new_game_capacities_are_intentional() -> None:
    state, _ = _new_state()
    hall = state.halls["hall-1"]
    site = state.resource_sites["site-1"]
    plant = state.energy_plants["plant-1"]
    assert (len(hall.production_lines), hall.max_slots_per_line, hall.slot_count) == (5, 10, 3)
    assert (len(site.production_lines), site.max_slots_per_line, site.slot_count) == (3, 10, 1)
    assert (len(plant.production_lines), plant.max_slots_per_line, plant.slot_count) == (3, 5, 1)
    assert hall.slot_count + site.slot_count + plant.slot_count == 5
    assert len(hall.slots) + len(site.slots) + len(plant.slots) == 95


def test_command_layer_enforces_board_ownership_and_primary_target_family() -> None:
    state, _ = _new_state()
    bus = CommandBus(state)
    for card in (
        _card("processor", "machine.processor"),
        _card("extractor", "machine.extractor"),
        _card("rig", "machine.drilling"),
        _card("farm", "machine.agriculture"),
        _card("solar", "energy.solar_array", CardKind.ENERGY),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "processor", "factory"))
    bus.dispatch(InstallCardInHall("site-1", 0, "extractor", "resources"))
    bus.dispatch(InstallCardInHall("plant-1", 0, "solar", "energy"))
    with pytest.raises(ValueError):
        bus.dispatch(InstallCardInHall("hall-1", 1, "extractor", "factory"))
    with pytest.raises(ValueError):
        bus.dispatch(InstallCardInHall("hall-1", 1, "extractor"))
    with pytest.raises(ValueError):
        bus.dispatch(InstallCardInHall("site-1", 0, "solar", "resources"))
    with pytest.raises(ValueError):
        bus.dispatch(InstallCardInHall("plant-1", 0, "processor", "energy"))
    with pytest.raises(ValueError):
        bus.dispatch(SelectMachineProduction("extractor", "resource.wheat", "wheat"))
    with pytest.raises(ValueError):
        bus.dispatch(SelectMachineProduction("rig", "resource.iron_ore", "iron_ore"))
    with pytest.raises(ValueError):
        bus.dispatch(SelectMachineProduction("farm", "resource.crude_oil", "crude_oil"))
    bus.dispatch(SelectMachineProduction("extractor", "resource.iron_ore", "iron_ore"))


def test_board_views_share_v2_language_with_board_specific_controls() -> None:
    _app()
    state, definitions = _new_state()
    bus = CommandBus(state)
    factory = FactoryViewV2(state, bus, definitions)
    resources = ResourcesViewV2(state, bus, definitions)
    energy = EnergyViewV2(state, bus, definitions)
    assert factory.findChild(QLabel, "factoryV2NavTitle").text() == "FACTORY"
    assert resources.findChild(QLabel, "factoryV2NavTitle").text() == "RESOURCES"
    assert energy.findChild(QLabel, "factoryV2NavTitle").text() == "ENERGY"
    assert resources.findChild(QPushButton, "buildHallButtonV2").text() == "BUILD SITE"
    assert energy.findChild(QPushButton, "buildHallButtonV2").text().startswith("Build Plant")
    assert factory.findChild(QWidget, "productionGuideButton") is not None
    assert resources.findChild(QWidget, "productionGuideButton") is not None
    assert energy.findChild(QWidget, "productionGuideButton") is not None
    assert resources.findChild(QWidget, "resourcesButton") is not None
    assert energy.findChild(QWidget, "resourcesButton") is not None


def test_board_headers_share_identical_right_side_control_order_and_geometry() -> None:
    app = _app()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    tabs = window.findChild(QTabWidget, "mainTabs")
    views = (
        window.findChild(ResourcesViewV2),
        window.findChild(FactoryViewV2),
        window.findChild(EnergyViewV2),
    )
    assert tabs is not None and all(view is not None for view in views)
    geometries = []
    try:
        for view in views:
            tabs.setCurrentWidget(view)
            for _ in range(8):
                app.processEvents()
            overview = view.findChild(QFrame, "factoryV2HallOverview")
            overview.layout().activate()
            app.processEvents()
            guide = overview.findChild(QWidget, "productionGuideButton")
            resources = overview.findChild(QWidget, "resourcesButton")
            kpi = overview.findChild(QWidget, "hallKpiStrip")
            assert guide is not None and kpi is not None
            assert (resources is None) == (view._board_config.board_kind == 'factory')
            assert kpi.property("metrics") == "Energy|Revenue"
            metric_width = (kpi.width() - 6) / 2
            energy = kpi.geometry().adjusted(0, 0, round(-metric_width - 6), 0)
            revenue = kpi.geometry().adjusted(round(metric_width + 6), 0, 0, 0)
            widgets = (guide, resources) if resources else (guide,)
            positions = [widget.mapTo(window, widget.rect().topLeft()).x() for widget in widgets]
            overview_left = overview.mapTo(window, overview.rect().topLeft()).x()
            positions.extend((overview_left + energy.left(), overview_left + revenue.left()))
            widths = tuple(widget.width() for widget in widgets) + (energy.width(), revenue.width())
            heights = tuple(widget.height() for widget in widgets) + (energy.height(), revenue.height())
            assert positions == sorted(positions)
            geometries.append(tuple(zip(positions, widths, heights)))
        assert geometries[0][-2:] == geometries[1][-2:] == geometries[2][-2:]
        assert geometries[0] == geometries[2]
    finally:
        window.close()


def test_energy_first_track_uses_the_shared_board_vertical_rhythm() -> None:
    app = _app()
    state, definitions = _new_state()
    views = (
        FactoryViewV2(state, CommandBus(state), definitions),
        ResourcesViewV2(state, CommandBus(state), definitions),
        EnergyViewV2(state, CommandBus(state), definitions),
    )
    try:
        gaps = []
        for view in views:
            view.resize(1366, 768)
            view.show()
            app.processEvents()
            board = view.findChild(QFrame, "factoryV2Board")
            overview = view.findChild(QFrame, "factoryV2HallOverview")
            track = view.findChild(QFrame, "factoryV2ProductionTrack")
            assert board is not None and overview is not None and track is not None
            track_top = track.mapTo(board, QPoint(0, 0)).y()
            gaps.append(track_top - overview.geometry().bottom())

        assert max(gaps) - min(gaps) <= 1
    finally:
        for view in views:
            view.close()


@pytest.mark.parametrize(
    ("view_type", "title", "subtitle", "board_kind", "unit_id"),
    (
        (ResourcesViewV2, "ASSIGN RESOURCE CARD", "Mining Complex 1 · Slot 1", "resources", "site-1"),
        (FactoryViewV2, "ASSIGN FACTORY CARD", "Hall 1 · Slot 1", "factory", "hall-1"),
        (EnergyViewV2, "ASSIGN ENERGY CARD", "Plant 1 · Slot 1", "energy", "plant-1"),
    ),
)
def test_production_board_card_assignment_matches_freight_secondary_hierarchy(
    view_type, title: str, subtitle: str, board_kind: str, unit_id: str,
) -> None:
    app = _app()
    state, definitions = _new_state()
    view = view_type(state, CommandBus(state), definitions)
    view.resize(1366, 768)
    view.show()
    app.processEvents()

    view._on_slot_clicked(0)
    app.processEvents()
    selection = view.findChild(QFrame, "factoryCardSelectionView")
    header = selection.findChild(QFrame, "secondaryViewHeader") if selection else None
    filters = selection.findChild(QFrame, "secondaryControlDeck") if selection else None
    results = selection.findChild(QFrame, "secondaryContentChassis") if selection else None
    scroll = selection.findChild(QScrollArea, "factoryCardSelectionScroll") if selection else None
    tiles = selection.findChildren(QFrame, "factoryCardSelectionTile") if selection else []

    assert selection is not None
    assert selection.property("secondaryShell") is True
    assert header is not None
    assert header.findChild(QLabel, "sectionLabel").text() == title
    assert header.findChild(QLabel, "cardSelectionTargetLabel").text() == subtitle
    assert header.findChild(QPushButton, "cardSelectionBackButton") is not None
    assert filters is not None
    assert filters.findChild(QLineEdit, "cardSearchInput") is not None
    assert results is not None
    assert scroll is not None
    assert tiles

    tiles[0].mousePressEvent(type("Event", (), {
        "button": lambda self: Qt.MouseButton.LeftButton,
    })())
    assert state.production_units(board_kind)[unit_id].slots[0].card_id is not None
    view.close()


@pytest.mark.parametrize(
    ("view_type", "empty_title", "empty_message"),
    (
        (
            ResourcesViewV2,
            "NO COMPATIBLE RESOURCE CARDS",
            "Acquire compatible Primary Production cards from Industrial Supply.",
        ),
        (
            FactoryViewV2,
            "NO COMPATIBLE FACTORY CARDS",
            "Acquire compatible production cards from Industrial Supply.",
        ),
        (
            EnergyViewV2,
            "NO COMPATIBLE ENERGY CARDS",
            "Acquire compatible energy cards from Industrial Supply.",
        ),
    ),
)
def test_production_board_card_assignment_uses_mature_empty_state(
    view_type, empty_title: str, empty_message: str,
) -> None:
    app = _app()
    state, definitions = _new_state()
    state.cards.clear()
    view = view_type(state, CommandBus(state), definitions)
    view.resize(1366, 768)
    view.show()
    app.processEvents()

    view._on_slot_clicked(0)
    app.processEvents()
    empty = view.findChild(QFrame, "factoryCardSelectionEmpty")

    assert empty is not None
    assert empty.findChild(QLabel, "emptyStateTitle").text() == empty_title
    assert empty.findChild(QLabel, "emptyStateMessage").text() == empty_message
    view.close()


@pytest.mark.parametrize(
    ("view_type", "board_kind", "unit_id", "track_number", "identifier"),
    (
        (FactoryViewV2, "factory", "hall-1", 2, "LINE 02"),
        (ResourcesViewV2, "resources", "site-1", 2, "SECTOR 02"),
        (EnergyViewV2, "energy", "plant-1", 2, "BLOCK 02"),
    ),
)
def test_shared_locked_track_uses_strong_heading_and_runtime_price_button(
    view_type, board_kind: str, unit_id: str, track_number: int, identifier: str,
) -> None:
    _app()
    state, definitions = _new_state()
    bus = CommandBus(state)
    view = view_type(state, bus, definitions)
    panel = next(
        panel for panel in view.findChildren(QFrame, "lockedLinePanel")
        if panel.property("lineId") == f"{unit_id}.line-{track_number}"
    )
    heading = panel.findChild(QLabel, "expansionHeading")
    track = panel.findChild(QLabel, "expansionTrackIdentifier")
    button = panel.findChild(QWidget, "unlockTrackButton")
    cost = state.production_units(board_kind)[unit_id].production_lines[track_number - 1].unlock_cost
    assert heading is None
    assert track.text() == identifier
    from production_zero.ui.factory_view_v2 import FactoryV2LinePlate
    assert isinstance(track, FactoryV2LinePlate)
    assert button._text == f"UNLOCK  ${cost:.2f}"
    assert button.property("unlockCost") == cost
    assert button.isEnabled()
    button.clicked.emit()
    assert state.production_units(board_kind)[unit_id].production_lines[track_number - 1].unlocked


@pytest.mark.parametrize("view_type", (FactoryViewV2, ResourcesViewV2, EnergyViewV2))
def test_shared_locked_track_button_tracks_runtime_affordability(view_type) -> None:
    _app()
    state, definitions = _new_state()
    state.cash.amount = 0
    view = view_type(state, CommandBus(state), definitions)
    panel = view.findChild(QFrame, "lockedLinePanel")
    button = panel.findChild(QWidget, "unlockTrackButton")
    assert panel.property("unlockEnabled") is False
    assert button.isEnabled() is False
    state.cash.amount = 100_000
    view.refresh_runtime()
    assert panel.property("unlockEnabled") is True
    assert button.isEnabled() is True


def test_navigation_exposes_operational_boards_in_locked_order() -> None:
    _app()
    window = MainWindow()
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert [tabs.tabText(i) for i in range(4)] == ["Resources", "Factory", "Energy", "Freight"]


def test_simulation_combines_resource_factory_and_energy_boards() -> None:
    state, definitions = _new_state()
    bus = CommandBus(state)
    state.resources["iron_ore"].capacity = 1000
    for card in (
        _card("extractor", "machine.extractor"),
        _card("solar", "energy.solar_array", CardKind.ENERGY),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("site-1", 0, "extractor", "resources"))
    bus.dispatch(InstallCardInHall("plant-1", 0, "solar", "energy"))
    bus.dispatch(SelectMachineProduction("extractor", "resource.iron_ore", "iron_ore"))
    totals = SimulationEngine(definitions).advance_time(state, 6)
    assert totals.gross_power == 20
    assert totals.outputs["iron_ore"] == 12


def test_all_production_boards_expand_during_active_runtime_without_disturbing_cards() -> None:
    state, definitions = _new_state()
    bus = CommandBus(state)
    state.cash.amount = 100_000
    cards = (
        _card("qa-running-extractor", "machine.extractor"),
        _card("qa-running-processor", "machine.processor"),
        _card("qa-running-solar", "energy.solar_array", CardKind.ENERGY),
    )
    for card in cards:
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("site-1", 0, "qa-running-extractor", "resources"))
    bus.dispatch(InstallCardInHall("hall-1", 0, "qa-running-processor", "factory"))
    bus.dispatch(InstallCardInHall("plant-1", 0, "qa-running-solar", "energy"))
    bus.dispatch(SelectMachineProduction("qa-running-extractor", "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("qa-running-processor", "recipe.processor.iron", "iron"))
    SimulationEngine(definitions).advance_time(state, 6)
    assert state.machine_production["qa-running-extractor"].status == "running"
    assert state.machine_production["qa-running-processor"].status == "running"
    installed_before = state.installed_card_ids()
    selections_before = {
        card_id: machine.selected_production_id
        for card_id, machine in state.machine_production.items()
        if card_id.startswith("qa-running-")
    }

    board_specs = (
        ("resources", "site-1", "Site", "site", 3, 10, 1, 1),
        ("factory", "hall-1", "Hall", "hall", 5, 10, 2, 3),
        ("energy", "plant-1", "Plant", "plant", 3, 5, 1, 1),
    )
    for board_kind, unit_id, unit_label, prefix, max_lines, max_slots, start_lines, start_slots in board_specs:
        unit = state.production_units(board_kind)[unit_id]
        first_line = unit.production_lines[0]
        slot_number = len(first_line.slot_indexes) + 1
        slot_cost = factory_slot_unlock_cost(1, slot_number, start_slots_per_line=unit.start_slots_per_line,board_kind=board_kind)
        cash_before = state.cash.amount
        bus.dispatch(UnlockProductionSlot(unit_id, first_line.line_id, board_kind))
        assert state.cash.amount == cash_before - slot_cost

        locked_line = next(line for line in unit.production_lines if not line.unlocked)
        line_cost = unit_line_price(unit,unit.production_lines.index(locked_line)+1)
        cash_before = state.cash.amount
        bus.dispatch(UnlockProductionLine(unit_id, locked_line.line_id, board_kind))
        assert state.cash.amount == cash_before - line_cost

        unit_cost = production_facility_price(state,board_kind)
        cash_before = state.cash.amount
        bus.dispatch(PurchaseProductionUnit(
            board_kind,
            unit_label,
            prefix,
            max_lines,
            max_slots,
            start_lines,
            start_slots,
        ))
        assert state.cash.amount == cash_before - unit_cost

    assert state.installed_card_ids() == installed_before
    assert {
        card_id: machine.selected_production_id
        for card_id, machine in state.machine_production.items()
        if card_id.startswith("qa-running-")
    } == selections_before
    totals = SimulationEngine(definitions).advance_time(state, 6)
    assert totals.gross_power == 20
    assert totals.outputs["iron_ore"] > 0
    assert totals.outputs["iron"] > 0


def test_fuel_energy_on_energy_board_consumes_global_resource_stock() -> None:
    state, definitions = _new_state()
    bus = CommandBus(state)
    coal_plant = _card("coal-plant", "energy.coal_power_plant", CardKind.ENERGY)
    bus.dispatch(AddCard(coal_plant))
    state.resources["coal"].amount = 10
    bus.dispatch(InstallCardInHall("plant-1", 0, coal_plant.card_id, "energy"))
    totals = SimulationEngine(definitions).advance_time(state, 1)
    assert totals.gross_power > 0
    assert totals.inputs["coal"] == pytest.approx(1)
    assert state.resources["coal"].amount == pytest.approx(9)


def test_analytics_and_installed_card_stacks_span_all_three_boards() -> None:
    state, definitions = _new_state()
    bus = CommandBus(state)
    cards = (
        _card("raw", "machine.extractor"),
        _card("processing", "machine.processor"),
        _card("power", "energy.solar_array", CardKind.ENERGY),
    )
    for card in cards:
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("site-1", 0, "raw", "resources"))
    bus.dispatch(InstallCardInHall("hall-1", 0, "processing", "factory"))
    bus.dispatch(InstallCardInHall("plant-1", 0, "power", "energy"))
    bus.dispatch(SelectMachineProduction("raw", "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("processing", "recipe.processor.iron", "iron"))
    state.machine_production["raw"].status = "running"
    state.machine_production["processing"].status = "running"
    flows = calculate_resource_flows(state, definitions)
    assert flows["iron_ore"].produced_per_minute > 0
    assert flows["iron_ore"].consumed_per_minute > 0
    assert flows["iron"].produced_per_minute > 0
    assert {"raw", "processing", "power"} <= state.installed_card_ids()
    assert not ({"raw", "processing", "power"} & {
        stack.first_card.card_id for stack in state.inventory_card_stacks()
    })


def test_legacy_save_migration_is_lossless_and_preserves_primary_state() -> None:
    state = GameState(rng_seed=9)
    bus = CommandBus(state)
    hall = FactoryHall("hall-1", "Hall 1", 6)
    hall.production_lines[5].unlocked = True
    hall.production_lines[5].slot_indexes = [50]
    hall.slot_count += 1
    bus.dispatch(BuildHall(hall))
    for card in (
        _card("farm", "machine.extractor"),
        _card("solar", "energy.solar_array", CardKind.ENERGY),
        _card("assembler", "machine.assembler"),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "farm"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar"))
    hall.slots[50].card_id = "assembler"
    state.ensure_machine_production("farm", "wheat", "resource.wheat").progress_seconds = 4.5
    payload = serialize_game_state(state)
    payload.pop("state_schema_version")
    payload.pop("resource_sites")
    payload.pop("energy_plants")

    migrated = deserialize_game_state(payload)

    assert len(migrated.halls) == 1
    assert len(migrated.halls["hall-1"].production_lines) == 5
    assert migrated.cards["farm"].definition_id == "machine.agriculture"
    assert migrated.machine_production["farm"].selected_production_id == "resource.wheat"
    assert migrated.machine_production["farm"].progress_seconds == 4.5
    assert "farm" in migrated.installed_card_ids()
    assert "solar" in migrated.installed_card_ids()
    assert "assembler" in migrated.installed_card_ids()
    assert {"farm", "solar", "assembler"} == set(migrated.cards)


def test_migration_overflow_returns_cards_to_inventory_without_deletion() -> None:
    state = GameState(rng_seed=10)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall("hall-1", "Hall 1", 6)))
    for index in range(2):
        card = _card(f"extractor-{index}", "machine.extractor")
        bus.dispatch(AddCard(card))
        bus.dispatch(InstallCardInHall("hall-1", index, card.card_id))
        bus.dispatch(SelectMachineProduction(card.card_id, "resource.iron_ore", "iron_ore"))
    payload = serialize_game_state(state)
    payload.pop("state_schema_version")
    payload.pop("resource_sites")
    payload.pop("energy_plants")
    migrated = deserialize_game_state(payload)
    assert set(migrated.cards) == {"extractor-0", "extractor-1"}
    assert len(migrated.installed_card_ids()) == 1
    assert sum(stack.quantity for stack in migrated.inventory_card_stacks()) == 1


def test_migration_preserves_multiple_halls_and_noncontiguous_valid_slots() -> None:
    state = GameState(rng_seed=11)
    bus = CommandBus(state)
    for index in range(1, 5):
        hall = FactoryHall(f"hall-{index}", f"Hall {index}", 6)
        hall.production_lines[0].slot_indexes = [0, 3, 9]
        hall.slot_count = 6
        bus.dispatch(BuildHall(hall))
        card = _card(f"processor-{index}", "machine.processor")
        bus.dispatch(AddCard(card))
        hall.slots[9].card_id = card.card_id
    payload = serialize_game_state(state)
    payload.pop("state_schema_version")
    payload.pop("resource_sites")
    payload.pop("energy_plants")
    migrated = deserialize_game_state(payload)
    assert list(migrated.halls) == ["hall-1", "hall-2", "hall-3", "hall-4"]
    assert all(hall.production_lines[0].slot_indexes == [0, 3, 9] for hall in migrated.halls.values())
    assert {f"processor-{index}" for index in range(1, 5)} <= migrated.installed_card_ids()


def test_split_board_serialization_round_trip_preserves_topology() -> None:
    state, _ = _new_state()
    loaded = deserialize_game_state(serialize_game_state(state))
    assert loaded.halls["hall-1"].max_lines == 5
    assert loaded.resource_sites["site-1"].max_slots_per_line == 10
    assert loaded.energy_plants["plant-1"].max_slots_per_line == 5


def test_current_save_load_repairs_malformed_cross_board_placements_without_loss() -> None:
    state, _ = _new_state()
    state.halls["hall-1"].slots[0].card_id = "test-solar-common-001"
    state.halls["hall-1"].slots[1].card_id = "test-drill-common-001"
    loaded = deserialize_game_state(serialize_game_state(state))
    assert "test-solar-common-001" not in {
        slot.card_id for hall in loaded.halls.values() for slot in hall.slots
    }
    assert "test-drill-common-001" not in {
        slot.card_id for hall in loaded.halls.values() for slot in hall.slots
    }
    assert {"test-solar-common-001", "test-drill-common-001"} <= loaded.installed_card_ids()
    assert set(loaded.cards) == set(state.cards)
