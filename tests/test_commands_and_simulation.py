from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.commands import AcceptContract, AddCard, AddCash, AddResource, AssignFreightCard, BuildHall, CommandBus, ConfigureAutoSell, DeliverAvailableToContract, ExpandInventoryStorage, InstallCardInHall, InstallFreightCard, PurchaseHall, RemoveCardFromHall, RenameHall, SelectMachineProduction, SellResource, SetResourceCapacity, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.contracts import DAILY, REGULAR, WEEKLY, generate_contract_offers, initialize_contracts
from production_zero.core.definitions import EnergyDefinition, MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility, expand_freight_facility
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, MAX_FACTORY_LINES, MAX_FACTORY_SLOTS_PER_LINE
from production_zero.data.definitions import load_card_definitions, load_resource_definitions


def _select_default_machine_production(state: GameState, bus: CommandBus, definitions, card_id: str) -> None:
    card = state.cards[card_id]
    definition = definitions[card.definition_id]
    assert isinstance(definition, MachineDefinition)
    production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
    bus.dispatch(SelectMachineProduction(card_id, production.production_id, production.output_resource))


def _install_energy_card(state: GameState, bus: CommandBus, hall_id: str, slot_index: int, card_id: str, definition_id: str) -> None:
    bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall(hall_id, slot_index, card_id))


def _install_freight_fleet(state: GameState, bus: CommandBus, definitions) -> None:
    for facility_type in ("rail_station", "harbor", "airport"):
        build_freight_facility(state.freight, facility_type)
    facility_ids = {
        facility.facility_type: facility_id
        for facility_id, facility in state.freight.facilities.items()
    }
    for facility_type in ("airport", "harbor", "rail_station"):
        expand_freight_facility(state.freight.facilities[facility_ids[facility_type]])
    assignments = [
        ("steel", "market"),
        ("iron", "market"),
        ("iron_ore", "market"),
        ("coal", "market"),
        ("copper", "market"),
        ("copper_ore", "market"),
        ("iron_ore", "contract"),
        ("coal", "contract"),
        ("copper", "contract"),
        ("iron", "contract"),
        ("copper_ore", "contract"),
        ("steel", "contract"),
    ]
    assignment_index = 0
    for index in range(3):
        for facility_id, definition_id in (
            (facility_ids["airport"], "freight.aircraft.class1"),
            (facility_ids["garage_depot"], "freight.truck.class1"),
            (facility_ids["harbor"], "freight.ship.class1"),
            (facility_ids["rail_station"], "freight.train.class1"),
        ):
            card = create_card_instance(
                f"{facility_id}-{index}",
                definition_id,
                CardKind.FREIGHT,
                Rarity.COMMON,
            )
            bus.dispatch(AddCard(card))
            bus.dispatch(InstallFreightCard(facility_id, index, card.card_id, definitions))
            resource_id, destination = assignments[assignment_index]
            assignment_index += 1
            bus.dispatch(AssignFreightCard(card.card_id, resource_id, destination))


def _deliver_until_settled(state: GameState, bus: CommandBus, definitions, kind: str, attempts: int = 12) -> None:
    engine = SimulationEngine(definitions)
    for _ in range(attempts):
        if kind not in state.contracts.active or state.contracts.active[kind].status == "completed":
            return
        bus.dispatch(DeliverAvailableToContract(kind, definitions))
        if not state.freight.outbound_shipments:
            return
        engine.advance_time(state, 420)


def _set_market_reserve(state: GameState, bus: CommandBus, resource_id: str, reserve_percent: float) -> None:
    for card_id, assignment in tuple(state.freight.assignments.items()):
        if assignment.resource_id == resource_id and assignment.destination_kind == "market":
            bus.dispatch(AssignFreightCard(card_id, resource_id, "market", reserve_percent))


def test_commands_install_cards_and_simulation_uses_instances() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1234)
    bus = CommandBus(state)

    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=2)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="drill-1",
                definition_id="machine.mining_drill.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.UNCOMMON,
                output_bonus_percent=5,
                power_bonus_percent=5,
            )
        )
    )
    bus.dispatch(InstallCardInHall(hall_id="hall-1", slot_index=0, card_id="solar-1"))
    bus.dispatch(InstallCardInHall(hall_id="hall-1", slot_index=1, card_id="drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")

    engine = SimulationEngine(definitions)
    totals = engine.advance_time(state, 1.0)

    assert totals.gross_power == 20
    assert totals.used_power == pytest.approx(6.15)
    assert state.energy.generated == 20
    assert state.energy.consumed == pytest.approx(6.15)
    assert state.resources["iron_ore"].amount == 0
    assert state.machine_production["drill-1"].progress_seconds == 1.0
    assert state.history.values_for("resource.iron_ore") == (0.0,)
    assert state.tick == 1

    totals = engine.advance_time(state, 2.0)

    assert totals.outputs == {"iron_ore": 12.600000000000001}
    assert state.resources["iron_ore"].amount == 12.600000000000001
    assert state.machine_production["drill-1"].progress_seconds == 0.0


def test_machine_rarity_bonus_applies_full_output_and_half_power_demand() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1235)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=2)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            create_card_instance(
                "drill-legendary",
                "machine.mining_drill.mk1",
                CardKind.MACHINE,
                Rarity.LEGENDARY,
                bonus_tenths=200,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-legendary"))
    _select_default_machine_production(state, bus, definitions, "drill-legendary")

    totals = SimulationEngine(definitions).advance_time(state, 3.0)

    assert totals.outputs == {"iron_ore": 14.399999999999999}
    assert state.energy.consumed == 6.6000000000000005


def test_new_extractor_starts_without_default_resource_and_produces_after_selection() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1236)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 5000))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=2)))
    bus.dispatch(AddCard(create_card_instance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))

    engine = SimulationEngine(definitions)
    unconfigured = engine.advance_time(state, 10.0)

    assert state.machine_production["drill-1"].selected_production_id is None
    assert state.machine_production["drill-1"].target_resource_id == ""
    assert state.machine_production["drill-1"].status == "unconfigured"
    assert unconfigured.outputs == {}
    assert state.resources["iron_ore"].amount == 0

    bus.dispatch(SelectMachineProduction("drill-1", "resource.iron_ore", "iron_ore"))
    configured = engine.advance_time(state, 3.0)

    assert configured.outputs == {"iron_ore": 12.0}
    assert state.resources["iron_ore"].amount == 12.0
    assert state.machine_production["drill-1"].selected_production_id == "resource.iron_ore"


def test_new_processor_starts_without_default_recipe_and_existing_selection_survives() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1237)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 5000))
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(SetResourceCapacity("copper", 500))
    bus.dispatch(AddResource("copper_ore", 20))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=3)))
    bus.dispatch(AddCard(create_card_instance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("furnace-2", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "furnace-2"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.processor.copper", "copper"))

    engine = SimulationEngine(definitions)
    totals = engine.advance_time(state, 4.0)

    assert state.machine_production["furnace-1"].selected_production_id == "recipe.processor.copper"
    assert state.machine_production["furnace-2"].selected_production_id is None
    assert state.machine_production["furnace-2"].status == "unconfigured"
    assert totals.outputs == {"copper": 6.0}
    assert "iron" not in totals.outputs

    bus.dispatch(SelectMachineProduction("furnace-2", "recipe.processor.copper", "copper"))
    bus.dispatch(AddResource("copper_ore", 20))
    switched = engine.advance_time(state, 4.0)

    assert switched.outputs == {"copper": 12.0}
    assert state.machine_production["furnace-2"].selected_production_id == "recipe.processor.copper"


def test_wind_turbine_adds_power_without_fuel_consumption() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1301)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    _install_energy_card(state, bus, "hall-1", 0, "wind-1", "energy.wind_turbine.mk1")

    totals = SimulationEngine(definitions).advance_time(state, 60)

    assert totals.gross_power == 35
    assert totals.inputs == {}
    assert state.energy.generated == 35
    assert state.resources.get("coal") is None


def test_coal_power_plant_consumes_fuel_and_goes_offline_without_coal() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1302)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    bus.dispatch(SetResourceCapacity("coal", 10))
    bus.dispatch(AddResource("coal", 2))
    _install_energy_card(state, bus, "hall-1", 0, "coal-power-1", "energy.coal_power_plant.mk1")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 100
    assert powered.inputs == {"coal": 2.0}
    assert state.resources["coal"].amount == 0
    assert offline.gross_power == 0
    assert offline.inputs == {}
    assert state.resources["coal"].amount == 0


def test_gas_power_plant_consumes_natural_gas_and_goes_offline_without_gas() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1303)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    bus.dispatch(SetResourceCapacity("natural_gas", 10))
    bus.dispatch(AddResource("natural_gas", 2))
    _install_energy_card(state, bus, "hall-1", 0, "gas-power-1", "energy.gas_power_plant.mk1")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 180
    assert powered.inputs == {"natural_gas": 2.0}
    assert state.resources["natural_gas"].amount == 0
    assert offline.gross_power == 0


def test_nuclear_power_plant_definition_and_fuel_behavior() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    nuclear = definitions["energy.nuclear_power_plant.mk1"]
    assert isinstance(nuclear, EnergyDefinition)
    assert nuclear.base_power_output == 500
    assert nuclear.fuel_resource_id == "nuclear_fuel_assembly"
    assert nuclear.fuel_consumption_per_minute == 0.25
    state = GameState(rng_seed=1304)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    bus.dispatch(SetResourceCapacity("nuclear_fuel_assembly", 10))
    bus.dispatch(AddResource("nuclear_fuel_assembly", 0.25))
    _install_energy_card(state, bus, "hall-1", 0, "nuclear-power-1", "energy.nuclear_power_plant.mk1")

    engine = SimulationEngine(definitions)
    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 500
    assert powered.inputs == {"nuclear_fuel_assembly": 0.25}
    assert state.resources["nuclear_fuel_assembly"].amount == 0
    assert offline.gross_power == 0


def test_energy_cards_add_and_fuel_loss_updates_power_capacity_dynamically() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1305)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Mixed", slot_count=6)))
    bus.dispatch(SetResourceCapacity("coal", 10))
    bus.dispatch(AddResource("coal", 2))
    _install_energy_card(state, bus, "hall-1", 0, "solar-1", "energy.solar_array.mk1")
    _install_energy_card(state, bus, "hall-1", 1, "wind-1", "energy.wind_turbine.mk1")
    _install_energy_card(state, bus, "hall-1", 2, "coal-power-1", "energy.coal_power_plant.mk1")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    no_fuel = engine.advance_time(state, 60)

    assert powered.gross_power == 155
    assert powered.inputs == {"coal": 2.0}
    assert no_fuel.gross_power == 55
    assert no_fuel.inputs == {}


def test_fuel_power_loss_uses_existing_machine_no_power_status() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1306)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Fuel Hall", slot_count=6)))
    bus.dispatch(SetResourceCapacity("coal", 10))
    bus.dispatch(SetResourceCapacity("iron_ore", 5000))
    bus.dispatch(AddResource("coal", 2))
    _install_energy_card(state, bus, "hall-1", 0, "coal-power-1", "energy.coal_power_plant.mk1")
    for index in range(3):
        card_id = f"drill-{index}"
        bus.dispatch(AddCard(CardInstance(card_id, "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0)))
        bus.dispatch(InstallCardInHall("hall-1", index + 1, card_id))
        _select_default_machine_production(state, bus, definitions, card_id)
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    no_fuel = engine.advance_time(state, 3)

    assert powered.gross_power == 100
    assert powered.used_power == 18
    assert no_fuel.gross_power == 0
    assert no_fuel.used_power == 0
    assert set(no_fuel.blocked_cards) == {f"drill-{index}" for index in range(3)}
    assert all(state.machine_production[f"drill-{index}"].is_no_power for index in range(3))


def test_hall_can_be_renamed_and_card_can_be_removed_from_slot() -> None:
    state = GameState(rng_seed=222)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="drill-1",
                definition_id="machine.mining_drill.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )

    bus.dispatch(RenameHall("hall-1", "Ore Intake"))
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(RemoveCardFromHall("hall-1", 0))

    assert state.halls["hall-1"].name == "Ore Intake"
    assert state.halls["hall-1"].slots[0].card_id is None


def test_hall_starts_with_unlocked_and_locked_production_lines() -> None:
    hall = FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)

    assert len(hall.slots) == 60
    assert hall.slot_count == 6
    assert len(hall.production_lines) == 6
    assert hall.production_lines[0].slot_indexes == [0, 1, 2]
    assert hall.production_lines[1].slot_indexes == [3, 4, 5]
    assert hall.production_lines[0].unlocked is True
    assert hall.production_lines[1].unlocked is True
    assert hall.production_lines[2].slot_indexes == []
    assert hall.production_lines[2].unlocked is False
    assert MAX_FACTORY_LINES == 6
    assert MAX_FACTORY_SLOTS_PER_LINE == 10


def test_multiple_halls_keep_independent_slots_and_lines() -> None:
    state = GameState(rng_seed=224)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(2000))
    bus.dispatch(PurchaseHall())
    for card in (
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))

    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-2", 0, "drill-2"))
    bus.dispatch(RenameHall("hall-2", "Remote Mine"))
    bus.dispatch(UnlockProductionLine("hall-1", "hall-1.line-3"))

    assert state.halls["hall-1"].slots[0].card_id == "drill-1"
    assert state.halls["hall-2"].slots[0].card_id == "drill-2"
    assert state.halls["hall-2"].name == "Remote Mine"
    assert state.halls["hall-1"].production_lines[2].unlocked is True
    assert state.halls["hall-2"].production_lines[2].unlocked is False
    assert state.halls["hall-1"].slot_count == 9
    assert state.halls["hall-2"].slot_count == 6


def test_factory_slot_and_line_unlock_progression_is_hall_local_through_slot_ten() -> None:
    state = GameState(rng_seed=225)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(100_000))
    bus.dispatch(PurchaseHall())

    snapshots_before: dict[str, tuple[tuple[tuple[int, ...], ...], int]] = {}
    for hall_id in ("hall-1", "hall-2"):
        hall = state.halls[hall_id]
        for line_number in (1, 2):
            line = hall.production_lines[line_number - 1]
            while len(line.slot_indexes) < MAX_FACTORY_SLOTS_PER_LINE:
                bus.dispatch(UnlockProductionSlot(hall_id, line.line_id))
            assert len(line.slot_indexes) == 10

        bus.dispatch(UnlockProductionLine(hall_id, f"{hall_id}.line-3"))
        assert hall.production_lines[2].unlocked is True
        assert len(hall.production_lines[2].slot_indexes) == 3
        assert hall.slot_count == 23
        snapshots_before[hall_id] = (
            tuple(tuple(line.slot_indexes) for line in hall.production_lines),
            hall.slot_count,
        )

    bus.dispatch(PurchaseHall())

    for hall_id, snapshot in snapshots_before.items():
        hall = state.halls[hall_id]
        assert (
            tuple(tuple(line.slot_indexes) for line in hall.production_lines),
            hall.slot_count,
        ) == snapshot
    assert state.halls["hall-3"].slot_count == 6
    assert state.halls["hall-3"].production_lines[2].unlocked is False


def test_factory_unlock_requires_cash_without_mutating_locked_progression() -> None:
    state = GameState(rng_seed=226)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    hall = state.halls["hall-1"]

    with pytest.raises(ValueError, match="Insufficient cash"):
        bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))
    with pytest.raises(ValueError, match="Insufficient cash"):
        bus.dispatch(UnlockProductionLine("hall-1", "hall-1.line-3"))

    assert hall.production_lines[0].slot_indexes == [0, 1, 2]
    assert hall.production_lines[2].unlocked is False
    assert hall.production_lines[2].slot_indexes == []
    assert hall.slot_count == 6


def test_machine_stops_when_storage_is_full_and_resumes_when_space_returns() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=333)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 12))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="drill-1",
                definition_id="machine.mining_drill.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 3.0)
    blocked = engine.advance_time(state, 3.0)

    assert first.outputs == {"iron_ore": 12.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12

    state.resources["iron_ore"].consume(6)
    resumed = engine.advance_time(state, 3.0)

    assert resumed.outputs == {"iron_ore": 6.0}
    assert state.resources["iron_ore"].amount == 12


def test_inventory_storage_expansion_clears_storage_full_without_restart() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resource_definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=340)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 12))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(250))
    for card in (
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)
    engine.advance_time(state, 3.0)

    blocked = engine.advance_time(state, 3.0)
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12

    bus.dispatch(ExpandInventoryStorage(resource_definitions))
    resumed = engine.advance_time(state, 3.0)

    assert state.resources["iron_ore"].capacity > 12
    assert resumed.outputs == {"iron_ore": 12.0}
    assert state.resources["iron_ore"].amount == 24
    assert state.machine_production["drill-1"].status == "running"


def test_simulation_uses_all_halls_with_global_resources_and_energy() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=335)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(1000))
    bus.dispatch(PurchaseHall())
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-2", 0, "drill-2"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    bus.dispatch(SelectMachineProduction("drill-2", "resource.coal", "coal"))

    totals = SimulationEngine(definitions).advance_time(state, 3.0)

    assert totals.outputs == {"iron_ore": 12.0, "coal": 12.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["coal"].amount == 12
    assert state.energy.generated == 20
    assert state.energy.consumed == 12
    assert state.machine_production["drill-1"].target_resource_id == "iron_ore"
    assert state.machine_production["drill-2"].target_resource_id == "coal"


def test_auto_sell_sells_only_stock_above_threshold_during_simulation_tick() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=336)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 90))
    _set_market_reserve(state, bus, "iron_ore", 70)
    state.market.ensure_resource("iron_ore").current_price = 2.0

    totals = SimulationEngine(definitions).advance_time(state, 0.0)

    assert totals.auto_sold == {"iron_ore": 20.0}
    assert state.resources["iron_ore"].amount == 70
    assert state.cash.amount == 0
    assert state.statistics.total_earnings == 0
    assert len(state.freight.outbound_shipments) == 1
    assert state.history.values_for("resource.iron_ore") == (70.0,)
    assert state.history.values_for("cash") == (0.0,)

    SimulationEngine(definitions).advance_time(state, 420)

    assert state.cash.amount == 40
    assert state.statistics.total_earnings == 40


def test_auto_sell_after_production_keeps_configured_reserve() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=337)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 68))
    _set_market_reserve(state, bus, "iron_ore", 70)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")

    totals = SimulationEngine(definitions).advance_time(state, 3.0)

    assert totals.outputs == {"iron_ore": 12.0}
    assert totals.auto_sold == {"iron_ore": 10.0}
    assert state.resources["iron_ore"].amount == 70
    assert state.cash.amount == 0
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.cash.amount == 10
    assert state.company.level == 1
    assert state.company.current_xp == 0


def test_auto_sell_uses_price_after_due_market_tick() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=339)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 90))
    _set_market_reserve(state, bus, "iron_ore", 70)

    totals = SimulationEngine(definitions).advance_time(state, 300.0)

    assert state.market.market_tick == 1
    assert totals.auto_sold == {"iron_ore": 20.0}
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.market_price == state.market.resources["iron_ore"].current_price
    assert state.cash.amount == 0
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.cash.amount == 20 * shipment.market_price


def test_auto_sell_runs_after_processing_inputs_are_consumed() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=338)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(AddResource("iron_ore", 80))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")

    totals = SimulationEngine(definitions).advance_time(state, 4.0)

    assert totals.inputs == {"iron_ore": 12.0}
    assert totals.outputs == {"iron": 6.0}
    assert totals.auto_sold == {}
    assert state.resources["iron_ore"].amount == 68
    assert state.resources["iron"].amount == 6
    assert state.cash.amount == 0


def test_produce_sell_unlock_loop_adds_production_capacity() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=334)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=3)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 3.0)
    bus.dispatch(AddResource("iron_ore", 488))
    bus.dispatch(SellResource("iron_ore", 500, definitions))
    engine.advance_time(state, 420.0)
    bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))
    bus.dispatch(InstallCardInHall("hall-1", 3, "drill-2"))

    assert state.cash.amount == 380
    assert state.halls["hall-1"].production_lines[0].slot_indexes == [0, 1, 2, 6]
    assert state.halls["hall-1"].slot_count == 7
    assert state.halls["hall-1"].slots[3].card_id == "drill-2"
    assert state.company.level == 1
    assert state.company.current_xp == 0


def test_machine_waits_without_power_and_resumes_when_solar_is_installed() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=444)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="drill-1",
                definition_id="machine.mining_drill.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    blocked = engine.advance_time(state, 3.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.energy.generated == 0
    assert state.energy.consumed == 0
    assert state.machine_production["drill-1"].is_no_power is True
    assert state.machine_production["drill-1"].progress_seconds == 0

    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-1"))
    resumed = engine.advance_time(state, 3.0)

    assert resumed.outputs == {"iron_ore": 12.0}
    assert state.energy.generated == 20
    assert state.energy.consumed == 6
    assert state.resources["iron_ore"].amount == 12

    bus.dispatch(RemoveCardFromHall("hall-1", 1))
    blocked_again = engine.advance_time(state, 3.0)

    assert blocked_again.outputs == {}
    assert blocked_again.blocked_cards == ("drill-1",)
    assert state.energy.generated == 0
    assert state.energy.consumed == 0
    assert state.machine_production["drill-1"].is_no_power is True


def test_mining_drill_can_select_and_switch_output_resource() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=445)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    iron_totals = engine.advance_time(state, 3.0)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    coal_totals = engine.advance_time(state, 3.0)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.copper_ore", "copper_ore"))
    copper_totals = engine.advance_time(state, 3.0)

    assert iron_totals.outputs == {"iron_ore": 12.0}
    assert coal_totals.outputs == {"coal": 12.0}
    assert copper_totals.outputs == {"copper_ore": 12.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["coal"].amount == 12
    assert state.resources["copper_ore"].amount == 12
    assert state.machine_production["drill-1"].selected_production_id == "resource.copper_ore"
    assert state.machine_production["drill-1"].target_resource_id == "copper_ore"


def test_selected_mining_resource_uses_storage_full_blocking_for_that_resource() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=446)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 12))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 3.0)
    blocked = engine.advance_time(state, 3.0)

    assert first.outputs == {"coal": 12.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True

    state.resources["coal"].consume(6)
    resumed = engine.advance_time(state, 3.0)

    assert resumed.outputs == {"coal": 6.0}
    assert state.resources["coal"].amount == 12


def test_furnace_consumes_iron_ore_and_produces_iron() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=555)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="furnace-1",
                definition_id="machine.furnace.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")

    totals = SimulationEngine(definitions).advance_time(state, 4.0)

    assert totals.outputs == {"iron": 6.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 6
    assert state.energy.generated == 20
    assert state.energy.consumed == 8
    assert state.history.values_for("rate.production.iron") == (90.0,)
    assert state.history.values_for("rate.consumption.iron_ore") == (180.0,)


def test_furnace_can_select_copper_recipe() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=562)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(SetResourceCapacity("copper", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("copper_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))

    totals = SimulationEngine(definitions).advance_time(state, 4.0)

    assert totals.inputs == {"copper_ore": 12.0}
    assert totals.outputs == {"copper": 6.0}
    assert state.resources["iron_ore"].amount == 24
    assert state.resources["copper_ore"].amount == 12
    assert state.resources["iron"].amount == 0
    assert state.resources["copper"].amount == 6
    assert state.machine_production["furnace-1"].selected_production_id == "recipe.processor.copper"


def test_furnace_waits_for_selected_copper_recipe_input() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=563)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(SetResourceCapacity("copper", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))
    engine = SimulationEngine(definitions)

    blocked = engine.advance_time(state, 4.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("furnace-1",)
    assert state.machine_production["furnace-1"].is_missing_input is True

    bus.dispatch(AddResource("copper_ore", 12))
    resumed = engine.advance_time(state, 4.0)

    assert state.resources["iron_ore"].amount == 24
    assert resumed.outputs == {"copper": 6.0}
    assert state.resources["copper_ore"].amount == 0


def test_machine_production_switch_resets_in_progress_cycle() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=564)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    partial = engine.advance_time(state, 2.9)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    switched_too_soon = engine.advance_time(state, 0.2)
    completed_after_reset = engine.advance_time(state, 2.8)

    assert partial.outputs == {}
    assert state.machine_production["drill-1"].progress_seconds == 0.0
    assert switched_too_soon.outputs == {}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["coal"].amount == 12
    assert completed_after_reset.outputs == {"coal": 12.0}


def test_furnace_recipe_switch_resets_in_progress_cycle() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=565)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(SetResourceCapacity("copper", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 12))
    bus.dispatch(AddResource("copper_ore", 12))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    partial = engine.advance_time(state, 3.9)
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))
    switched_too_soon = engine.advance_time(state, 0.2)
    completed_after_reset = engine.advance_time(state, 3.8)

    assert partial.outputs == {}
    assert state.machine_production["furnace-1"].progress_seconds == 0.0
    assert switched_too_soon.outputs == {}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 0
    assert completed_after_reset.outputs == {"copper": 6.0}
    assert state.resources["copper_ore"].amount == 0
    assert state.resources["copper"].amount == 6


def test_furnace_waits_for_missing_input_and_resumes_when_ore_arrives() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=556)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="furnace-1",
                definition_id="machine.furnace.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    blocked = engine.advance_time(state, 4.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("furnace-1",)
    assert state.machine_production["furnace-1"].is_missing_input is True
    assert state.machine_production["furnace-1"].progress_seconds == 0

    bus.dispatch(AddResource("iron_ore", 12))
    resumed = engine.advance_time(state, 4.0)

    assert resumed.outputs == {"iron": 6.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["iron"].amount == 6


def test_furnace_waits_when_iron_storage_is_full_and_resumes_after_space_returns() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=557)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 6))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="solar-1",
                definition_id="energy.solar_array.mk1",
                card_kind=CardKind.ENERGY,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(
        AddCard(
            CardInstance(
                card_id="furnace-1",
                definition_id="machine.furnace.mk1",
                card_kind=CardKind.MACHINE,
                rarity=Rarity.COMMON,
                output_bonus_percent=0,
                power_bonus_percent=0,
            )
        )
    )
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 4.0)
    blocked = engine.advance_time(state, 4.0)

    assert first.outputs == {"iron": 6.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("furnace-1",)
    assert state.machine_production["furnace-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 6

    state.resources["iron"].consume(3)
    resumed = engine.advance_time(state, 4.0)

    assert resumed.outputs == {"iron": 3.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["iron"].amount == 6


def test_drill_and_furnace_form_shared_storage_chain() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=558)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 3.0)
    blocked_until_ore_exists = engine.advance_time(state, 4.0)
    totals = engine.advance_time(state, 4.0)

    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 12
    assert blocked_until_ore_exists.outputs == {"iron_ore": 12.0, "iron": 6.0}
    assert totals.outputs == {"iron_ore": 12.0, "iron": 6.0}
    assert state.energy.generated == 20
    assert state.energy.consumed == 14
    assert state.machine_production["drill-1"].progress_seconds == 2


def test_blast_furnace_consumes_iron_ore_and_coal_to_produce_steel() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=559)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 200))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.blast_furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("coal", 6))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    _select_default_machine_production(state, bus, definitions, "blast-furnace-1")

    totals = SimulationEngine(definitions).advance_time(state, 5.0)

    assert totals.inputs == {"iron_ore": 12.0, "coal": 3.0}
    assert totals.outputs == {"steel": 4.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["coal"].amount == 3
    assert state.resources["steel"].amount == 4
    assert state.energy.generated == 20
    assert state.energy.consumed == 12


def test_blast_furnace_waits_for_each_required_input_and_resumes() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=560)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 200))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.blast_furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    _select_default_machine_production(state, bus, definitions, "blast-furnace-1")
    engine = SimulationEngine(definitions)

    missing_both = engine.advance_time(state, 5.0)
    bus.dispatch(AddResource("iron_ore", 12))
    missing_coal = engine.advance_time(state, 5.0)
    bus.dispatch(AddResource("coal", 3))
    resumed = engine.advance_time(state, 5.0)

    assert missing_both.outputs == {}
    assert missing_both.blocked_cards == ("blast-furnace-1",)
    assert missing_coal.outputs == {}
    assert missing_coal.blocked_cards == ("blast-furnace-1",)
    assert state.machine_production["blast-furnace-1"].status == "running"
    assert resumed.outputs == {"steel": 4.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["coal"].amount == 0
    assert state.resources["steel"].amount == 4


def test_blast_furnace_waits_when_steel_storage_is_full_and_resumes_after_space_returns() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=561)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 4))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.blast_furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("coal", 6))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    _select_default_machine_production(state, bus, definitions, "blast-furnace-1")
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 5.0)
    blocked = engine.advance_time(state, 5.0)

    assert first.outputs == {"steel": 4.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("blast-furnace-1",)
    assert state.machine_production["blast-furnace-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["coal"].amount == 3
    assert state.resources["steel"].amount == 4

    state.resources["steel"].consume(2)
    resumed = engine.advance_time(state, 5.0)

    assert resumed.outputs == {"steel": 2.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["coal"].amount == 0
    assert state.resources["steel"].amount == 4


def test_contract_offers_are_deterministic_and_distinct_per_kind_and_period() -> None:
    first = generate_contract_offers(1234, DAILY, 4, expires_at=5 * 24 * 60 * 60)
    second = generate_contract_offers(1234, DAILY, 4, expires_at=5 * 24 * 60 * 60)
    next_period = generate_contract_offers(1234, DAILY, 5, expires_at=6 * 24 * 60 * 60)

    assert first == second
    assert first != next_period
    assert len(first) == 3
    assert len({tuple(offer.requirements) for offer in first}) == 3


def test_regular_contract_accepts_partial_deliveries_and_regenerates_after_completion() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=901)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)
    offer = state.contracts.offers[REGULAR][0]
    resource_id, required = next(iter(offer.requirements.items()))
    bus.dispatch(SetResourceCapacity(resource_id, required * 2))
    bus.dispatch(AddResource(resource_id, required / 2))

    bus.dispatch(AcceptContract(REGULAR, offer.contract_id))
    bus.dispatch(DeliverAvailableToContract(REGULAR, definitions))

    active = state.contracts.active[REGULAR]
    assert active.delivered.get(resource_id, 0.0) == 0
    assert state.resources[resource_id].amount == 0
    assert state.cash.amount == 0

    SimulationEngine(definitions).advance_time(state, 420)

    active = state.contracts.active[REGULAR]
    assert active.delivered[resource_id] == required / 2

    bus.dispatch(AddResource(resource_id, required))
    bus.dispatch(DeliverAvailableToContract(REGULAR, definitions))

    assert REGULAR in state.contracts.active
    SimulationEngine(definitions).advance_time(state, 420)

    assert REGULAR not in state.contracts.active
    assert state.cash.amount == offer.reward_cash
    assert state.statistics.total_earnings == offer.reward_cash
    assert state.company.current_xp == offer.reward_xp
    assert state.company.level == 1
    assert state.contracts.last_status[REGULAR].startswith("Completed")
    assert state.contracts.regular_generation == 1
    assert len(state.contracts.offers[REGULAR]) == 3
    assert state.contracts.offers[REGULAR][0].contract_id.startswith("regular-1-")


def test_contract_deliver_available_supports_multiple_resources() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=902)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)
    offer = next(offer for offer in state.contracts.offers[WEEKLY] if len(offer.requirements) > 1)

    for resource_id, required in offer.requirements.items():
        bus.dispatch(SetResourceCapacity(resource_id, required * 2))
        bus.dispatch(AddResource(resource_id, required))

    bus.dispatch(AcceptContract(WEEKLY, offer.contract_id))
    bus.dispatch(DeliverAvailableToContract(WEEKLY, definitions))

    active = state.contracts.active[WEEKLY]
    assert active.status == "active"
    assert active.delivered == {}
    SimulationEngine(definitions).advance_time(state, 420)
    _deliver_until_settled(state, bus, definitions, WEEKLY)

    active = state.contracts.active[WEEKLY]
    assert active.status == "completed"
    assert active.delivered == offer.requirements
    assert state.cash.amount == offer.reward_cash
    assert state.statistics.total_earnings == offer.reward_cash
    assert state.company.level > 1
    assert state.company.current_xp > 0
    assert all(state.resources[resource_id].amount == 0 for resource_id in offer.requirements)


def test_contract_xp_is_awarded_only_after_full_completion() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=905)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id, required = next(iter(offer.requirements.items()))
    bus.dispatch(SetResourceCapacity(resource_id, required * 2))
    bus.dispatch(AddResource(resource_id, required / 2))

    bus.dispatch(AcceptContract(DAILY, offer.contract_id))
    bus.dispatch(DeliverAvailableToContract(DAILY, definitions))

    assert state.company.current_xp == 0
    assert state.company.level == 1
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.company.current_xp == 0

    bus.dispatch(AddResource(resource_id, required))
    bus.dispatch(DeliverAvailableToContract(DAILY, definitions))

    assert state.cash.amount == 0
    SimulationEngine(definitions).advance_time(state, 420)

    assert state.cash.amount == offer.reward_cash
    assert state.company.current_xp == offer.reward_xp


def test_daily_contract_expires_and_resets_at_midnight_game_time() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=903)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]

    CommandBus(state).dispatch(AcceptContract(DAILY, offer.contract_id))
    SimulationEngine(definitions).advance_time(state, 24 * 60 * 60)

    assert DAILY not in state.contracts.active
    assert state.contracts.daily_period_index == 1
    assert state.contracts.last_status[DAILY].startswith("Expired")
    assert state.contracts.offers[DAILY][0].contract_id.startswith("daily-1-")


def test_weekly_contract_resets_on_next_monday_midnight_game_time() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=904)
    initialize_contracts(state)
    offer = state.contracts.offers[WEEKLY][0]

    CommandBus(state).dispatch(AcceptContract(WEEKLY, offer.contract_id))
    SimulationEngine(definitions).advance_time(state, 7 * 24 * 60 * 60)

    assert WEEKLY not in state.contracts.active
    assert state.contracts.weekly_period_index == 1
    assert state.contracts.last_status[WEEKLY].startswith("Expired")
    assert state.contracts.offers[WEEKLY][0].contract_id.startswith("weekly-1-")
