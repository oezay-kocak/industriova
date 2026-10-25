from __future__ import annotations

import os
from importlib.resources import files

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from production_zero.core.analytics import ResourceFlow, calculate_resource_flows
from production_zero.core.cards import CardInstance
from production_zero.core.commands import AddCard, CommandBus, InstallCardInHall, SelectMachineProduction
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.resources import create_resource_inventory
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.production_board_views import EnergyViewV2, ResourcesViewV2


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _scenario() -> tuple[GameState, dict, CommandBus]:
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    state = GameState(rng_seed=2401, resources=create_resource_inventory(resources))
    state.halls["hall-1"] = FactoryHall("hall-1", "Hall 1", 6, board_kind="factory", max_lines=5)
    state.resource_sites["site-1"] = FactoryHall(
        "site-1", "Site 1", 1, board_kind="resources", max_lines=3, start_unlocked_lines=1, start_slots_per_line=1,
    )
    state.energy_plants["plant-1"] = FactoryHall(
        "plant-1", "Plant 1", 1, board_kind="energy", max_lines=3, max_slots_per_line=5,
        start_unlocked_lines=1, start_slots_per_line=1,
    )
    return state, definitions, CommandBus(state)


def _install_machine(
    state: GameState,
    bus: CommandBus,
    *,
    card_id: str,
    definition_id: str,
    unit_id: str,
    board_kind: str,
    slot_index: int,
    production_id: str,
    output_resource: str,
) -> None:
    bus.dispatch(AddCard(CardInstance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON, 0, 0)))
    bus.dispatch(InstallCardInHall(unit_id, slot_index, card_id, board_kind))
    bus.dispatch(SelectMachineProduction(card_id, production_id, output_resource))


def _install_energy(
    bus: CommandBus,
    *,
    card_id: str,
    definition_id: str,
    unit_id: str = "plant-1",
    slot_index: int = 0,
) -> None:
    bus.dispatch(AddCard(CardInstance(card_id, definition_id, CardKind.ENERGY, Rarity.COMMON, 0, 0)))
    bus.dispatch(InstallCardInHall(unit_id, slot_index, card_id, "energy"))


def _flow_tuple(flow: ResourceFlow) -> tuple[float, float, float]:
    return (flow.produced_per_minute, flow.consumed_per_minute, flow.net_per_minute)


def _view_flow_tuple(view_type, state: GameState, definitions: dict, resource_id: str) -> tuple[float, float, float]:
    view = view_type(state, CommandBus(state), definitions)
    view.resize(1280, 820)
    view.show()
    QApplication.processEvents()
    view._set_resources_drawer_open(True)
    QApplication.processEvents()
    item = view._resource_drawer.summary._items[resource_id]
    result = (
        float(item.property("producedPerMinute")),
        float(item.property("consumedPerMinute")),
        float(item.property("netPerMinute")),
    )
    assert "PROD" in item._rate.text() and "USE" in item._rate.text() and "NET" in item._rate.text()
    view.close()
    return result


def test_crude_oil_bitumen_flow_is_company_wide_in_resources_and_factory() -> None:
    _app()
    state, definitions, bus = _scenario()
    _install_machine(
        state, bus, card_id="oil-rig", definition_id="machine.drilling", unit_id="site-1", board_kind="resources",
        slot_index=0, production_id="resource.crude_oil", output_resource="crude_oil",
    )
    for index in range(5):
        _install_machine(
            state, bus, card_id=f"bitumen-{index}", definition_id="machine.processor", unit_id="hall-1",
            board_kind="factory", slot_index=index, production_id="recipe.processor.bitumen", output_resource="bitumen",
        )

    expected = (120.0, 600.0, -480.0)
    assert _flow_tuple(calculate_resource_flows(state, definitions)["crude_oil"]) == pytest.approx(expected)
    assert _view_flow_tuple(ResourcesViewV2, state, definitions, "crude_oil") == pytest.approx(expected)
    assert _view_flow_tuple(FactoryViewV2, state, definitions, "crude_oil") == pytest.approx(expected)


def test_natural_gas_flow_includes_energy_fuel_in_all_three_entry_points() -> None:
    _app()
    state, definitions, bus = _scenario()
    _install_machine(
        state, bus, card_id="gas-rig", definition_id="machine.drilling", unit_id="site-1", board_kind="resources",
        slot_index=0, production_id="resource.natural_gas", output_resource="natural_gas",
    )
    _install_energy(bus, card_id="gas-plant", definition_id="energy.gas_power_plant")

    expected = (120.0, 60.0, 60.0)
    assert _flow_tuple(calculate_resource_flows(state, definitions)["natural_gas"]) == pytest.approx(expected)
    for view_type in (ResourcesViewV2, FactoryViewV2, EnergyViewV2):
        assert _view_flow_tuple(view_type, state, definitions, "natural_gas") == pytest.approx(expected)


def test_multistage_chain_reports_inputs_intermediates_and_final_output_globally() -> None:
    _app()
    state, definitions, bus = _scenario()
    _install_machine(
        state, bus, card_id="oil-rig", definition_id="machine.drilling", unit_id="site-1", board_kind="resources",
        slot_index=0, production_id="resource.crude_oil", output_resource="crude_oil",
    )
    _install_machine(
        state, bus, card_id="bitumen", definition_id="machine.processor", unit_id="hall-1", board_kind="factory",
        slot_index=0, production_id="recipe.processor.bitumen", output_resource="bitumen",
    )
    _install_machine(
        state, bus, card_id="asphalt", definition_id="machine.fabricator", unit_id="hall-1", board_kind="factory",
        slot_index=1, production_id="recipe.fabricator.asphalt_components", output_resource="asphalt_components",
    )

    flows = calculate_resource_flows(state, definitions)
    assert _flow_tuple(flows["crude_oil"]) == pytest.approx((120.0, 120.0, 0.0))
    assert _flow_tuple(flows["bitumen"]) == pytest.approx((80.0, 80.0, 0.0))
    assert _flow_tuple(flows["asphalt_components"]) == pytest.approx((40.0, 0.0, 40.0))
    expected = _flow_tuple(flows["bitumen"])
    for view_type in (ResourcesViewV2, FactoryViewV2, EnergyViewV2):
        assert _view_flow_tuple(view_type, state, definitions, "bitumen") == pytest.approx(expected)


def test_multiple_producers_and_consumers_aggregate_without_tab_filtering() -> None:
    _app()
    state, definitions, bus = _scenario()
    state.resource_sites["site-2"] = FactoryHall(
        "site-2", "Site 2", 1, board_kind="resources", max_lines=3, start_unlocked_lines=1, start_slots_per_line=1,
    )
    for index, site_id in enumerate(("site-1", "site-2")):
        _install_machine(
            state, bus, card_id=f"oil-rig-{index}", definition_id="machine.drilling", unit_id=site_id,
            board_kind="resources", slot_index=0, production_id="resource.crude_oil", output_resource="crude_oil",
        )
    for index in range(3):
        _install_machine(
            state, bus, card_id=f"bitumen-{index}", definition_id="machine.processor", unit_id="hall-1",
            board_kind="factory", slot_index=index, production_id="recipe.processor.bitumen", output_resource="bitumen",
        )

    expected = (240.0, 360.0, -120.0)
    assert _flow_tuple(calculate_resource_flows(state, definitions)["crude_oil"]) == pytest.approx(expected)
    for view_type in (ResourcesViewV2, FactoryViewV2, EnergyViewV2):
        assert _view_flow_tuple(view_type, state, definitions, "crude_oil") == pytest.approx(expected)


def test_configured_flow_remains_nominal_when_runtime_status_is_blocked() -> None:
    state, definitions, bus = _scenario()
    _install_machine(
        state, bus, card_id="bitumen", definition_id="machine.processor", unit_id="hall-1", board_kind="factory",
        slot_index=0, production_id="recipe.processor.bitumen", output_resource="bitumen",
    )
    state.machine_production["bitumen"].status = "missing_input"

    flows = calculate_resource_flows(state, definitions)
    assert _flow_tuple(flows["crude_oil"]) == pytest.approx((0.0, 120.0, -120.0))
    assert _flow_tuple(flows["bitumen"]) == pytest.approx((80.0, 0.0, 80.0))


def test_assembler_inputs_and_output_are_part_of_the_same_flow_model() -> None:
    state, definitions, bus = _scenario()
    _install_machine(
        state, bus, card_id="assembler", definition_id="machine.assembler", unit_id="hall-1", board_kind="factory",
        slot_index=0, production_id="recipe.assembler.industrial_equipment", output_resource="industrial_equipment",
    )

    flows = calculate_resource_flows(state, definitions)
    assert _flow_tuple(flows["steel_components"]) == pytest.approx((0.0, 40.0, -40.0))
    assert _flow_tuple(flows["electrical_components"]) == pytest.approx((0.0, 20.0, -20.0))
    assert _flow_tuple(flows["iron_components"]) == pytest.approx((0.0, 20.0, -20.0))
    assert _flow_tuple(flows["industrial_equipment"]) == pytest.approx((20.0, 0.0, 20.0))
