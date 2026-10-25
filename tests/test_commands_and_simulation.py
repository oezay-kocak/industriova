from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from production_zero.core.cards import CardInstance, create_card_instance
from production_zero.core.company import xp_required_for_next_level
from production_zero.core.commands import AcceptContract, AddCard, AddCash, AddResource, AssignFreightCard, BuildHall, CommandBus, ConfigureAutoSell, DeliverAvailableToContract, ExpandInventoryStorage, InstallCardInHall, InstallFreightCard, PurchaseHall, RemoveCardFromHall, RenameHall, SelectMachineProduction, SellResource, SetResourceCapacity, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.contracts import (
    CONTRACT_COMPANY_XP,
    CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE,
    DAILY,
    REGULAR,
    WEEKLY,
    ContractOffer,
    contract_capacity_estimate,
    contract_requirements_for_selection,
    contract_production_value_budgets,
    generate_contract_offers,
    initialize_contracts,
    refresh_contracts,
)
from production_zero.core.definitions import EnergyDefinition, MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility, expand_freight_facility
from production_zero.core.production_values import contract_required_amount, eligible_contract_products, production_value_for_resource
from production_zero.core.progression import initialize_production_progress
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
            (facility_ids["airport"], "freight.aircraft"),
            (facility_ids["garage_depot"], "freight.truck"),
            (facility_ids["harbor"], "freight.ship"),
            (facility_ids["rail_station"], "freight.train"),
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


def _prepare_flexible_contract_resource(
    state: GameState,
    definitions,
    offer,
    resource_id: str = "iron_ore",
    stock_ratio: float = 1.0,
) -> float:
    # This helper exercises legacy fixed-PV delivery/expiry snapshots. P8's
    # reachable quantity generation has its own complete powered-chain cases.
    if offer.balance_version:
        offer = replace(offer,balance_version=0,capacity_signature="")
        state.contracts.offers[offer.kind] = [offer]
    initialize_production_progress(state, definitions)
    production_ids = {
        "iron": "recipe.processor.iron",
        "steel": "recipe.processor.steel",
        "cargo_aircraft": "recipe.assembler.cargo_aircraft",
    }
    if resource_id in production_ids:
        state.production_progress.unlocked_production_ids.add(production_ids[resource_id])
    required_count = {REGULAR: 2, DAILY: 3, WEEKLY: 4}[offer.kind]
    candidates = [resource_id, *(
        candidate for candidate in ("iron_ore", "coal", "copper_ore", "bauxite", "quartz")
        if candidate != resource_id
    )]
    for candidate in candidates[:required_count]:
        state.ensure_resource(candidate).capacity = 100_000
        state.ensure_resource(candidate).amount = max(1.0, state.ensure_resource(candidate).amount)
    assert any(product.resource_id == resource_id for product in eligible_contract_products(state, definitions, offer.production_value_budget or 0.0))
    refresh_contracts(state, definitions)
    from production_zero.core.contracts import contract_requirements_for_selection
    requirements = contract_requirements_for_selection(state, offer, definitions, resource_id)
    for candidate, required in requirements.items():
        state.ensure_resource(candidate).capacity = required * 3
        state.ensure_resource(candidate).amount = required * stock_ratio
    state.warehouse_capacity = max(state.warehouse_capacity, sum(stock.amount for stock in state.resources.values()) + 100_000)
    return requirements[resource_id]


def _install_contract_capacity_machine(
    state: GameState,
    bus: CommandBus,
    definitions,
    card_id: str,
    definition_id: str,
    production_id: str,
    output_resource: str,
    slot_index: int,
) -> None:
    if "hall-1" not in state.halls:
        bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)))
    bus.dispatch(AddCard(create_card_instance(card_id, definition_id, CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", slot_index, card_id))
    state.production_progress.unlocked_production_ids.add(production_id)
    bus.dispatch(SelectMachineProduction(card_id, production_id, output_resource))
    from tests.contract_capacity_fixture import provide_logistics
    provide_logistics(state,definitions)



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
                definition_id="energy.solar_array",
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
                definition_id="machine.extractor",
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
    assert state.history.values_for("resource.iron_ore") == ()  # Unused zero series stay implicit.
    assert state.tick == 1

    totals = engine.advance_time(state, 5.0)

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
                definition_id="energy.solar_array",
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
                "machine.extractor",
                CardKind.MACHINE,
                Rarity.LEGENDARY,
                bonus_tenths=200,
            )
        )
    )
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-legendary"))
    _select_default_machine_production(state, bus, definitions, "drill-legendary")

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

    assert totals.outputs == {"iron_ore": 14.399999999999999}
    assert state.energy.consumed == 6.6000000000000005


def test_new_extractor_starts_without_default_resource_and_produces_after_selection() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1236)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 5000))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Starter Hall", slot_count=2)))
    bus.dispatch(AddCard(create_card_instance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)))
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
    configured = engine.advance_time(state, 6.0)

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
    bus.dispatch(AddCard(create_card_instance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(AddCard(create_card_instance("furnace-2", "machine.processor", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "furnace-2"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.processor.copper", "copper"))

    engine = SimulationEngine(definitions)
    totals = engine.advance_time(state, 6.0)

    assert state.machine_production["furnace-1"].selected_production_id == "recipe.processor.copper"
    assert state.machine_production["furnace-2"].selected_production_id is None
    assert state.machine_production["furnace-2"].status == "unconfigured"
    assert totals.outputs == {"copper": 6.0}
    assert "iron" not in totals.outputs

    bus.dispatch(SelectMachineProduction("furnace-2", "recipe.processor.copper", "copper"))
    bus.dispatch(AddResource("copper_ore", 20))
    switched = engine.advance_time(state, 6.0)

    assert switched.outputs == {"copper": 12.0}
    assert state.machine_production["furnace-2"].selected_production_id == "recipe.processor.copper"


def test_wind_turbine_adds_power_without_fuel_consumption() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1301)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    _install_energy_card(state, bus, "hall-1", 0, "wind-1", "energy.wind_turbine")

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
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(AddResource("coal", 60))
    _install_energy_card(state, bus, "hall-1", 0, "coal-power-1", "energy.coal_power_plant")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 60
    assert powered.inputs == {"coal": 60.0}
    assert state.resources["coal"].amount == 0
    assert offline.gross_power == 0
    assert offline.inputs == {}
    assert state.resources["coal"].amount == 0


def test_gas_power_plant_consumes_natural_gas_and_goes_offline_without_gas() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1303)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    bus.dispatch(SetResourceCapacity("natural_gas", 100))
    bus.dispatch(AddResource("natural_gas", 60))
    _install_energy_card(state, bus, "hall-1", 0, "gas-power-1", "energy.gas_power_plant")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 180
    assert powered.inputs == {"natural_gas": 60.0}
    assert state.resources["natural_gas"].amount == 0
    assert offline.gross_power == 0


def test_nuclear_power_plant_definition_and_fuel_behavior() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    nuclear = definitions["energy.nuclear_power_plant"]
    assert isinstance(nuclear, EnergyDefinition)
    assert nuclear.base_power_output == 500
    assert nuclear.fuel_resource_id == "nuclear_fuel_assembly"
    assert nuclear.fuel_consumption_per_minute == 10
    state = GameState(rng_seed=1304)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Energy", slot_count=6)))
    bus.dispatch(SetResourceCapacity("nuclear_fuel_assembly", 10))
    bus.dispatch(AddResource("nuclear_fuel_assembly", 10))
    _install_energy_card(state, bus, "hall-1", 0, "nuclear-power-1", "energy.nuclear_power_plant")

    engine = SimulationEngine(definitions)
    powered = engine.advance_time(state, 60)
    offline = engine.advance_time(state, 60)

    assert powered.gross_power == 500
    assert powered.inputs == pytest.approx({"nuclear_fuel_assembly": 10.0},abs=1e-12)
    assert state.resources["nuclear_fuel_assembly"].amount == pytest.approx(0,abs=1e-12)
    assert offline.gross_power == 0


def test_energy_cards_add_and_fuel_loss_updates_power_capacity_dynamically() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1305)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Mixed", slot_count=6)))
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(AddResource("coal", 60))
    _install_energy_card(state, bus, "hall-1", 0, "solar-1", "energy.solar_array")
    _install_energy_card(state, bus, "hall-1", 1, "wind-1", "energy.wind_turbine")
    _install_energy_card(state, bus, "hall-1", 2, "coal-power-1", "energy.coal_power_plant")
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    no_fuel = engine.advance_time(state, 60)

    assert powered.gross_power == 115
    assert powered.inputs == {"coal": 60.0}
    assert no_fuel.gross_power == 55
    assert no_fuel.inputs == {}


def test_fuel_power_loss_uses_existing_machine_no_power_status() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=1306)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Fuel Hall", slot_count=6)))
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(SetResourceCapacity("iron_ore", 5000))
    state.warehouse_capacity = 5000
    bus.dispatch(AddResource("coal", 60))
    _install_energy_card(state, bus, "hall-1", 0, "coal-power-1", "energy.coal_power_plant")
    for index in range(3):
        card_id = f"drill-{index}"
        bus.dispatch(AddCard(CardInstance(card_id, "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0)))
        bus.dispatch(InstallCardInHall("hall-1", index + 1, card_id))
        _select_default_machine_production(state, bus, definitions, card_id)
    engine = SimulationEngine(definitions)

    powered = engine.advance_time(state, 60)
    no_fuel = engine.advance_time(state, 3)

    assert powered.gross_power == 60
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
                definition_id="machine.extractor",
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
    hall = FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6, max_lines=MAX_FACTORY_LINES)

    assert len(hall.slots) == 50
    assert hall.slot_count == 6
    assert len(hall.production_lines) == 5
    assert hall.production_lines[0].slot_indexes == [0, 1, 2]
    assert hall.production_lines[1].slot_indexes == [3, 4, 5]
    assert hall.production_lines[0].unlocked is True
    assert hall.production_lines[1].unlocked is True
    assert hall.production_lines[2].slot_indexes == []
    assert hall.production_lines[2].unlocked is False
    assert MAX_FACTORY_LINES == 5
    assert MAX_FACTORY_SLOTS_PER_LINE == 10


def test_multiple_halls_keep_independent_slots_and_lines() -> None:
    state = GameState(rng_seed=224)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(20_000))
    bus.dispatch(PurchaseHall())
    for card in (
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
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
    assert state.halls["hall-2"].slot_count == 3


def test_factory_slot_and_line_unlock_progression_is_hall_local_through_slot_ten() -> None:
    state = GameState(rng_seed=225)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(200_000))
    bus.dispatch(PurchaseHall())

    snapshots_before: dict[str, tuple[tuple[tuple[int, ...], ...], int]] = {}
    for hall_id in ("hall-1", "hall-2"):
        hall = state.halls[hall_id]
        for line_number in (1, 2):
            line = hall.production_lines[line_number - 1]
            if not line.unlocked:
                bus.dispatch(UnlockProductionLine(hall_id,line.line_id))
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
    assert state.halls["hall-3"].slot_count == 3
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
                definition_id="machine.extractor",
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
                definition_id="energy.solar_array",
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

    first = engine.advance_time(state, 6.0)
    blocked = engine.advance_time(state, 6.0)

    assert first.outputs == {"iron_ore": 12.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12

    state.resources["iron_ore"].consume(6)
    resumed = engine.advance_time(state, 6.0)

    assert resumed.outputs == {}
    assert state.resources["iron_ore"].amount == 6
    state.resources["iron_ore"].consume(6)
    resumed = engine.advance_time(state, 6.0)
    assert resumed.outputs == {"iron_ore": 12.0}


def test_inventory_storage_expansion_clears_storage_full_without_restart() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    resource_definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=340)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 12))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(250))
    for card in (
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)
    engine.advance_time(state, 6.0)

    blocked = engine.advance_time(state, 6.0)
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True
    assert state.resources["iron_ore"].amount == 12

    bus.dispatch(ExpandInventoryStorage(resource_definitions))
    resumed = engine.advance_time(state, 6.0)

    assert state.warehouse_capacity > 12
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
    bus.dispatch(AddCash(15_200))
    bus.dispatch(PurchaseHall())
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-2", 0, "drill-2"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    bus.dispatch(SelectMachineProduction("drill-2", "resource.coal", "coal"))

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

    assert totals.outputs == {"iron_ore": 12.0, "coal": 12.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["coal"].amount == 12
    assert state.energy.generated == 20
    assert state.energy.consumed == 12
    assert state.machine_production["drill-1"].target_resource_id == "iron_ore"
    assert state.machine_production["drill-2"].target_resource_id == "coal"


def test_auto_sell_ships_available_stock_during_simulation_tick() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=336)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 90))
    state.market.ensure_resource("iron_ore").current_price = 2.0

    totals = SimulationEngine(definitions).advance_time(state, 0.0)

    assert totals.auto_sold == {"iron_ore": 90.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.cash.amount == 0
    assert state.statistics.total_earnings == 0
    assert len(state.freight.outbound_shipments) == 1
    assert state.history.values_for("resource.iron_ore") == ()
    assert state.history.values_for("cash") == ()

    SimulationEngine(definitions).advance_time(state, 420)

    assert state.cash.amount == 90
    assert state.statistics.total_earnings == 90


def test_auto_sell_after_production_ships_available_cargo() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=337)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 68))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

    assert totals.outputs == {"iron_ore": 12.0}
    # Existing stock dispatches at second 1; the new batch completes at 6.
    assert totals.auto_sold == {"iron_ore": 68.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.cash.amount == 0
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.cash.amount == 68
    assert state.company.level == 1
    assert state.company_xp_progress.xp_by_source["market_sales"] > 0
    assert "continuity" not in state.company_xp_progress.xp_by_source


def test_auto_sell_uses_price_after_due_market_tick() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=339)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 90))

    totals = SimulationEngine(definitions).advance_time(state, 300.0)

    assert state.market.market_tick == 0
    assert totals.auto_sold == {"iron_ore": 90.0}
    assert state.freight.outbound_shipments == {}
    assert state.freight.completed_market_deliveries
    assert all(d.market_price == state.market.resources["iron_ore"].current_price for d in state.freight.completed_market_deliveries)
    assert state.cash.amount == 90
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.cash.amount == 90


def test_auto_sell_runs_after_processing_inputs_are_consumed() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=338)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(AddResource("iron_ore", 80))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

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
    for card_id, assignment in tuple(state.freight.assignments.items()):
        if assignment.destination_kind == "market":
            state.freight.assignments.pop(card_id)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=3)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("drill-2", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 6.0)
    bus.dispatch(AddResource("iron_ore", 488))
    for card_id in state.installed_freight_card_ids():
        if card_id not in state.freight.assignments:
            bus.dispatch(AssignFreightCard(card_id, "iron_ore", "market"))
    bus.dispatch(SellResource("iron_ore", 500, definitions))
    engine.advance_time(state, 420.0)
    bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))
    bus.dispatch(InstallCardInHall("hall-1", 3, "drill-2"))

    assert state.cash.amount == 1028
    assert state.halls["hall-1"].production_lines[0].slot_indexes == [0, 1, 2, 6]
    assert state.halls["hall-1"].slot_count == 7
    assert state.halls["hall-1"].slots[3].card_id == "drill-2"
    assert state.company.level == 1
    assert state.company_xp_progress.xp_by_source["market_sales"] > 0
    assert "continuity" not in state.company_xp_progress.xp_by_source


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
                definition_id="machine.extractor",
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
                definition_id="energy.solar_array",
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

    blocked = engine.advance_time(state, 6.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.energy.generated == 0
    assert state.energy.consumed == 0
    assert state.machine_production["drill-1"].is_no_power is True
    assert state.machine_production["drill-1"].progress_seconds == 0

    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-1"))
    resumed = engine.advance_time(state, 6.0)

    assert resumed.outputs == {"iron_ore": 12.0}
    assert state.energy.generated == 20
    assert state.energy.consumed == 6
    assert state.resources["iron_ore"].amount == 12

    bus.dispatch(RemoveCardFromHall("hall-1", 1))
    blocked_again = engine.advance_time(state, 6.0)

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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    iron_totals = engine.advance_time(state, 6.0)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    coal_totals = engine.advance_time(state, 6.0)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.copper_ore", "copper_ore"))
    copper_totals = engine.advance_time(state, 6.0)

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
    state.warehouse_capacity = 12
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 6.0)
    blocked = engine.advance_time(state, 6.0)

    assert first.outputs == {"coal": 12.0}
    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("drill-1",)
    assert state.machine_production["drill-1"].is_storage_full is True

    state.resources["coal"].consume(6)
    resumed = engine.advance_time(state, 6.0)

    assert resumed.outputs == {}
    assert state.resources["coal"].amount == 6
    state.resources["coal"].consume(6)
    resumed = engine.advance_time(state, 6.0)
    assert resumed.outputs == {"coal": 12.0}


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
                definition_id="energy.solar_array",
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
                definition_id="machine.processor",
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

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

    assert totals.outputs == {"iron": 6.0}
    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 6
    assert state.energy.generated == 20
    assert state.energy.consumed == 8
    # Six observed seconds include five idle seconds and the completed batch.
    assert state.history.values_for("rate.production.iron") == (60.,)
    assert state.history.values_for("rate.consumption.iron_ore") == (120.,)


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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("copper_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))
    engine = SimulationEngine(definitions)

    blocked = engine.advance_time(state, 6.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("furnace-1",)
    assert state.machine_production["furnace-1"].is_missing_input is True

    bus.dispatch(AddResource("copper_ore", 12))
    resumed = engine.advance_time(state, 6.0)

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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    engine = SimulationEngine(definitions)

    partial = engine.advance_time(state, 5.9)
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))
    switched_too_soon = engine.advance_time(state, 0.2)
    completed_after_reset = engine.advance_time(state, 5.8)

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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 12))
    bus.dispatch(AddResource("copper_ore", 12))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    partial = engine.advance_time(state, 5.9)
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))
    switched_too_soon = engine.advance_time(state, 0.2)
    completed_after_reset = engine.advance_time(state, 5.8)

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
                definition_id="energy.solar_array",
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
                definition_id="machine.processor",
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

    blocked = engine.advance_time(state, 6.0)

    assert blocked.outputs == {}
    assert blocked.blocked_cards == ("furnace-1",)
    assert state.machine_production["furnace-1"].is_missing_input is True
    assert state.machine_production["furnace-1"].progress_seconds == 0

    bus.dispatch(AddResource("iron_ore", 12))
    resumed = engine.advance_time(state, 6.0)

    assert resumed.outputs == {"iron": 6.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["iron"].amount == 6


def test_furnace_can_process_when_full_because_inputs_free_shared_storage() -> None:
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
                definition_id="energy.solar_array",
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
                definition_id="machine.processor",
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

    first = engine.advance_time(state, 6.0)
    second = engine.advance_time(state, 6.0)

    assert first.outputs == {"iron": 6.0}
    assert second.outputs == {"iron": 6.0}
    assert second.blocked_cards == ()
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["iron"].amount == 12


def test_drill_and_furnace_form_shared_storage_chain() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=558)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.extractor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "furnace-1"))
    _select_default_machine_production(state, bus, definitions, "drill-1")
    _select_default_machine_production(state, bus, definitions, "furnace-1")
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 6.0)
    blocked_until_ore_exists = engine.advance_time(state, 6.0)
    totals = engine.advance_time(state, 6.0)

    assert state.resources["iron_ore"].amount == 12
    assert state.resources["iron"].amount == 12
    assert blocked_until_ore_exists.outputs == {"iron_ore": 12.0, "iron": 6.0}
    assert totals.outputs == {"iron_ore": 12.0, "iron": 6.0}
    assert state.energy.generated == 20
    assert state.energy.consumed == 14
    assert state.machine_production["drill-1"].progress_seconds == 0


def test_blast_furnace_consumes_iron_ore_and_coal_to_produce_steel() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=559)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 200))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("coal", 6))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    bus.dispatch(SelectMachineProduction("blast-furnace-1", "recipe.processor.steel", "steel"))

    totals = SimulationEngine(definitions).advance_time(state, 6.0)

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
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    bus.dispatch(SelectMachineProduction("blast-furnace-1", "recipe.processor.steel", "steel"))
    engine = SimulationEngine(definitions)

    missing_both = engine.advance_time(state, 6.0)
    bus.dispatch(AddResource("iron_ore", 12))
    missing_coal = engine.advance_time(state, 6.0)
    bus.dispatch(AddResource("coal", 3))
    resumed = engine.advance_time(state, 6.0)

    assert missing_both.outputs == {}
    assert missing_both.blocked_cards == ("blast-furnace-1",)
    assert missing_coal.outputs == {}
    assert missing_coal.blocked_cards == ("blast-furnace-1",)
    assert state.machine_production["blast-furnace-1"].status == "running"
    assert resumed.outputs == {"steel": 4.0}
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["coal"].amount == 0
    assert state.resources["steel"].amount == 4


def test_blast_furnace_processing_frees_shared_storage() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=561)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 4))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(AddResource("iron_ore", 24))
    bus.dispatch(AddResource("coal", 6))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    bus.dispatch(SelectMachineProduction("blast-furnace-1", "recipe.processor.steel", "steel"))
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 6.0)
    second = engine.advance_time(state, 6.0)

    assert first.outputs == {"steel": 4.0}
    assert second.outputs == {"steel": 4.0}
    assert second.blocked_cards == ()
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["coal"].amount == 0
    assert state.resources["steel"].amount == 8


def test_contract_offers_are_deterministic_and_distinct_per_kind_and_period() -> None:
    first = generate_contract_offers(1234, DAILY, 4, expires_at=5 * 24 * 60 * 60)
    second = generate_contract_offers(1234, DAILY, 4, expires_at=5 * 24 * 60 * 60)
    next_period = generate_contract_offers(1234, DAILY, 5, expires_at=6 * 24 * 60 * 60)

    assert first == second
    assert first != next_period
    assert len(first) == 1
    assert all(not offer.requirements for offer in first)
    assert len({offer.production_value_budget for offer in first}) == 1
    assert all(offer.reward_cash > 0 for offer in first)


def test_contract_eligible_products_require_unlock_and_economic_relevance() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=910)
    initialize_production_progress(state, definitions)
    offer = generate_contract_offers(910, REGULAR, 0)[0]

    state.ensure_resource("iron_ore").capacity = 5000
    state.ensure_resource("iron_ore").add(10)
    state.ensure_resource("copper_ore").capacity = 5000
    state.production_progress.unlocked_production_ids.add("recipe.processor.iron")
    state.ensure_resource("iron").capacity = 5000
    state.ensure_resource("iron").add(10)
    state.ensure_resource("steel").capacity = 5000
    state.ensure_resource("steel").add(10)

    products = {product.resource_id for product in eligible_contract_products(state, definitions, offer.production_value_budget or 0.0)}

    assert "iron_ore" in products
    assert "iron" in products
    assert "copper_ore" not in products
    assert "steel" not in products


def test_contract_eligible_products_include_active_unstocked_production() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=911)
    bus = CommandBus(state)
    initialize_production_progress(state, definitions)
    state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=1)))
    bus.dispatch(AddCard(create_card_instance("processor-1", "machine.processor", CardKind.MACHINE, Rarity.COMMON)))
    bus.dispatch(InstallCardInHall("hall-1", 0, "processor-1"))
    bus.dispatch(SelectMachineProduction("processor-1", "recipe.processor.steel", "steel"))
    offer = generate_contract_offers(911, REGULAR, 0)[0]

    products = {product.resource_id for product in eligible_contract_products(state, definitions, offer.production_value_budget or 0.0)}

    assert "steel" in products


def test_contract_budget_requires_more_basic_resource_than_complex_product() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    budget = 10.0
    iron_ore = production_value_for_resource(definitions, "iron_ore")
    cargo_aircraft = production_value_for_resource(definitions, "cargo_aircraft")

    assert iron_ore is not None
    assert cargo_aircraft is not None
    assert contract_required_amount(budget, iron_ore.value_per_unit) > contract_required_amount(
        budget,
        cargo_aircraft.value_per_unit,
    )


def test_flexible_contract_cash_uses_selected_market_value_and_xp_is_unchanged() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    offer = ContractOffer(
        "flexible-reward",
        REGULAR,
        "Flexible Reward",
        {},
        1500,
        25,
        0,
        production_value_budget=10,
    )

    states = []
    for resource_id, production_id in (("iron_ore", "resource.iron_ore"), ("cargo_aircraft", "recipe.assembler.cargo_aircraft")):
        state = GameState(rng_seed=912)
        state.contracts.offers[REGULAR] = [offer]
        _prepare_flexible_contract_resource(state, definitions, offer, resource_id, stock_ratio=0.01)
        CommandBus(state).dispatch(AcceptContract(REGULAR, offer.contract_id, definitions, resource_id))
        states.append(state)

    from production_zero.core.market import market_price_for
    for state in states:
        accepted = state.contracts.active[REGULAR].offer
        assert accepted.reward_cash == round(sum(market_price_for(state.market, rid) * amount for rid, amount in accepted.requirements.items()), 2)
    from math import sqrt, log1p
    from production_zero.core.production_values import ProductionValueCalculator
    calculator = ProductionValueCalculator(definitions)
    for state in states:
        accepted = state.contracts.active[REGULAR].offer
        work = sum(calculator.value_for_resource(rid).value_per_unit * amount for rid, amount in accepted.requirements.items())
        assert accepted.reward_xp == round(20 * sqrt(max(1., work)) * (1 + log1p(state.company.level) / 4), 2)
    assert states[0].contracts.active[REGULAR].offer.requirements != states[1].contracts.active[REGULAR].offer.requirements


def test_contract_amount_rounding_uses_readable_whole_units() -> None:
    assert contract_required_amount(10, 20) == 1
    assert contract_required_amount(10, 1.75) == 6
    assert contract_required_amount(10, 0.087917) == 115
    assert contract_required_amount(10, 0.004167) == 2400


def test_contract_budget_scaling_keeps_very_early_regular_contracts_short() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=913)
    bus = CommandBus(state)
    initialize_production_progress(state, definitions)
    _install_contract_capacity_machine(
        state,
        bus,
        definitions,
        "extractor-1",
        "machine.extractor",
        "resource.iron_ore",
        "iron_ore",
        0,
    )

    estimate = contract_capacity_estimate(state, definitions)
    regular = contract_production_value_budgets(REGULAR, state, definitions)
    daily = contract_production_value_budgets(DAILY, state, definitions)
    weekly = contract_production_value_budgets(WEEKLY, state, definitions)

    assert estimate.active_pv_per_minute == pytest.approx(1.0)
    assert regular == (6.0, 10.0, 16.0)
    assert regular[-1] / estimate.effective_pv_per_minute <= 16.0
    assert regular[-1] < daily[0] < daily[-1] < weekly[-1]


def test_contract_budget_scaling_grows_monotonically_with_factory_capacity() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    early = GameState(rng_seed=914)
    early_bus = CommandBus(early)
    initialize_production_progress(early, definitions)
    _install_contract_capacity_machine(
        early,
        early_bus,
        definitions,
        "extractor-1",
        "machine.extractor",
        "resource.iron_ore",
        "iron_ore",
        0,
    )

    later = GameState(rng_seed=915)
    later_bus = CommandBus(later)
    initialize_production_progress(later, definitions)
    for slot_index, (card_id, definition_id, production_id, resource_id) in enumerate(
        (
            ("extractor-1", "machine.extractor", "resource.iron_ore", "iron_ore"),
            ("extractor-2", "machine.extractor", "resource.coal", "coal"),
            ("extractor-3", "machine.extractor", "resource.copper_ore", "copper_ore"),
            ("processor-1", "machine.processor", "recipe.processor.steel", "steel"),
            ("fabricator-1", "machine.fabricator", "recipe.fabricator.steel_components", "steel_components"),
            ("assembler-1", "machine.assembler", "recipe.assembler.industrial_equipment", "industrial_equipment"),
        )
    ):
        _install_contract_capacity_machine(later, later_bus, definitions, card_id, definition_id, production_id, resource_id, slot_index)

    # Output growth also needs enough transport; a fixed early truck fleet
    # must no longer masquerade as a larger sustainable economy.
    for cid in later.installed_freight_card_ids():later.cards[cid]=replace(later.cards[cid],mk_level=10)
    early_regular = contract_production_value_budgets(REGULAR, early, definitions)
    later_regular = contract_production_value_budgets(REGULAR, later, definitions)
    later_daily = contract_production_value_budgets(DAILY, later, definitions)
    later_weekly = contract_production_value_budgets(WEEKLY, later, definitions)

    assert contract_capacity_estimate(later, definitions).effective_pv_per_minute > contract_capacity_estimate(early, definitions).effective_pv_per_minute
    assert later_regular[0] > early_regular[0]
    assert later_regular[2] > early_regular[2]
    assert later_regular[2] < later_daily[0] < later_daily[2] < later_weekly[2]


def test_contract_offer_rewards_are_budget_proportional_and_deterministic_with_state() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=916)
    bus = CommandBus(state)
    initialize_production_progress(state, definitions)
    _install_contract_capacity_machine(
        state,
        bus,
        definitions,
        "extractor-1",
        "machine.extractor",
        "resource.iron_ore",
        "iron_ore",
        0,
    )

    first = generate_contract_offers(916, DAILY, 2, state=state, definitions=definitions)
    second = generate_contract_offers(916, DAILY, 2, state=state, definitions=definitions)

    assert first == second
    sorted_offers = sorted(first, key=lambda offer: offer.production_value_budget or 0)
    assert [offer.reward_cash for offer in sorted_offers] == sorted(offer.reward_cash for offer in sorted_offers)
    for offer in first:
        assert offer.production_value_budget is not None
        assert offer.reward_cash == round(
            offer.production_value_budget * CONTRACT_REWARD_CASH_PER_PRODUCTION_VALUE[DAILY] / 5.0
        ) * 5.0
        assert offer.reward_xp == CONTRACT_COMPANY_XP[DAILY][("easy", "medium", "hard").index(offer.difficulty)]


def test_active_contract_materialization_is_immutable_after_factory_progression() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=917)
    bus = CommandBus(state)
    initialize_production_progress(state, definitions)
    _install_contract_capacity_machine(
        state,
        bus,
        definitions,
        "extractor-1",
        "machine.extractor",
        "resource.iron_ore",
        "iron_ore",
        0,
    )
    initialize_contracts(state, definitions)
    offer = state.contracts.offers[REGULAR][0]
    required = _prepare_flexible_contract_resource(state, definitions, offer, "iron_ore", stock_ratio=1.0)
    bus.dispatch(AcceptContract(REGULAR, offer.contract_id, definitions, "iron_ore"))
    active_before = state.contracts.active[REGULAR].offer

    for slot_index, (card_id, definition_id, production_id, resource_id) in enumerate(
        (
            ("extractor-2", "machine.extractor", "resource.coal", "coal"),
            ("extractor-3", "machine.extractor", "resource.copper_ore", "copper_ore"),
            ("processor-1", "machine.processor", "recipe.processor.steel", "steel"),
            ("fabricator-1", "machine.fabricator", "recipe.fabricator.steel_components", "steel_components"),
            ("assembler-1", "machine.assembler", "recipe.assembler.industrial_equipment", "industrial_equipment"),
        ),
        start=1,
    ):
        _install_contract_capacity_machine(state, bus, definitions, card_id, definition_id, production_id, resource_id, slot_index)
    state.market.elapsed_seconds = 60.0
    refresh_contracts(state, definitions)
    active_after = state.contracts.active[REGULAR].offer

    assert active_after.contract_id == active_before.contract_id
    assert active_after.production_value_budget == active_before.production_value_budget
    assert active_after.reward_cash == active_before.reward_cash
    assert active_after.reward_xp == active_before.reward_xp
    assert active_after.requirements == active_before.requirements
    assert len(active_after.requirements) == 2
    assert active_after.selected_resource_id == active_before.selected_resource_id


def test_regular_contract_accepts_partial_deliveries_and_regenerates_after_completion() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=901)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    for card_id, assignment in tuple(state.freight.assignments.items()):
        if assignment.destination_kind == "market":
            state.freight.assignments.pop(card_id)
    initialize_contracts(state)
    offer = state.contracts.offers[REGULAR][0]
    resource_id = "steel"
    required = _prepare_flexible_contract_resource(state, definitions, offer, resource_id, 0.5)

    bus.dispatch(AcceptContract(REGULAR, offer.contract_id, definitions, resource_id))
    offer = state.contracts.active[REGULAR].offer
    accepted_cash = offer.reward_cash
    bus.dispatch(DeliverAvailableToContract(REGULAR, definitions))

    active = state.contracts.active[REGULAR]
    assert active.delivered.get(resource_id, 0.0) == 0
    assert state.resources[resource_id].amount < required / 2
    assert state.cash.amount == 0

    SimulationEngine(definitions).advance_time(state, 420)

    active = state.contracts.active[REGULAR]
    assert active.delivered[resource_id] > 0

    for required_resource_id, required_amount in state.contracts.active[REGULAR].offer.requirements.items():
        bus.dispatch(AddResource(required_resource_id, required_amount))
    _deliver_until_settled(state, bus, definitions, REGULAR)

    assert REGULAR not in state.contracts.active
    assert state.cash.amount == accepted_cash
    assert state.statistics.total_earnings == accepted_cash
    total_xp = sum(xp_required_for_next_level(level) for level in range(1, state.company.level)) + state.company.current_xp
    assert total_xp == offer.reward_xp
    assert state.company.level == 1
    assert state.contracts.last_status[REGULAR].startswith("Completed")
    assert state.contracts.regular_generation == 1
    assert len(state.contracts.offers[REGULAR]) == 1
    assert state.contracts.offers[REGULAR][0].contract_id.startswith("regular-1-")


def test_contract_deliver_available_supports_multiple_resources() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=902)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    initialize_contracts(state)
    offer = ContractOffer("legacy-weekly", WEEKLY, "Legacy Weekly", {"iron_ore": 20, "coal": 20}, 1000, 1000, 0)
    state.contracts.offers[WEEKLY] = [offer]

    for resource_id, required in offer.requirements.items():
        bus.dispatch(SetResourceCapacity(resource_id, required * 2))
        bus.dispatch(AddResource(resource_id, required))

    bus.dispatch(AcceptContract(WEEKLY, offer.contract_id))
    accepted_cash = state.contracts.active[WEEKLY].offer.reward_cash
    bus.dispatch(DeliverAvailableToContract(WEEKLY, definitions))

    active = state.contracts.active[WEEKLY]
    assert active.status == "active"
    assert active.delivered == {}
    SimulationEngine(definitions).advance_time(state, 420)
    _deliver_until_settled(state, bus, definitions, WEEKLY)

    active = state.contracts.active[WEEKLY]
    assert active.status == "completed"
    assert active.delivered == offer.requirements
    assert state.cash.amount == accepted_cash
    assert state.statistics.total_earnings == accepted_cash
    assert state.company.level > 1
    assert state.company.current_xp > 0
    assert all(state.resources[resource_id].amount == 0 for resource_id in offer.requirements)


def test_contract_xp_is_awarded_only_after_full_completion() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=905)
    bus = CommandBus(state)
    _install_freight_fleet(state, bus, definitions)
    for card_id, assignment in tuple(state.freight.assignments.items()):
        if assignment.destination_kind == "market":
            state.freight.assignments.pop(card_id)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id = "steel"
    required = _prepare_flexible_contract_resource(state, definitions, offer, resource_id, 0.5)

    bus.dispatch(AcceptContract(DAILY, offer.contract_id, definitions, resource_id))
    offer = state.contracts.active[DAILY].offer
    for kind, other in state.contracts.active.items():
        if kind != DAILY:
            other.status = "completed"  # isolate this category from competing automatic routes
    accepted_cash = offer.reward_cash
    bus.dispatch(DeliverAvailableToContract(DAILY, definitions))

    assert state.company.current_xp == 0
    assert state.company.level == 1
    SimulationEngine(definitions).advance_time(state, 420)
    assert state.company.current_xp == 0

    for required_resource_id, required_amount in state.contracts.active[DAILY].offer.requirements.items():
        bus.dispatch(AddResource(required_resource_id, required_amount))
    assert state.cash.amount == 0
    _deliver_until_settled(state, bus, definitions, DAILY)

    assert state.cash.amount == accepted_cash
    total_xp = sum(xp_required_for_next_level(level) for level in range(1, state.company.level)) + state.company.current_xp
    assert total_xp == offer.reward_xp


def test_daily_contract_expires_and_resets_at_midnight_game_time() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=903)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    _prepare_flexible_contract_resource(state, definitions, offer)

    CommandBus(state).dispatch(AcceptContract(DAILY, offer.contract_id, definitions, "iron_ore"))
    base = state.company_xp_progress.utc_high_water_timestamp
    SimulationEngine(definitions, utc_now=lambda: base + 24 * 60 * 60).advance_time(state, 1)

    assert DAILY not in state.contracts.active
    assert state.contracts.offers[DAILY][0].contract_id != offer.contract_id
    assert state.contracts.daily_period_index > offer.period_index
    assert state.contracts.last_status[DAILY].startswith("Expired")
    assert state.contracts.offers[DAILY][0].contract_id.startswith(f"daily-{state.contracts.daily_period_index}-")


def test_weekly_contract_resets_on_next_monday_midnight_game_time() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=904)
    initialize_contracts(state)
    offer = state.contracts.offers[WEEKLY][0]
    _prepare_flexible_contract_resource(state, definitions, offer)

    CommandBus(state).dispatch(AcceptContract(WEEKLY, offer.contract_id, definitions, "iron_ore"))
    base = state.company_xp_progress.utc_high_water_timestamp
    SimulationEngine(definitions, utc_now=lambda: base + 7 * 24 * 60 * 60).advance_time(state, 1)

    assert WEEKLY not in state.contracts.active
    assert state.contracts.offers[WEEKLY][0].contract_id != offer.contract_id
    assert state.contracts.weekly_period_index > offer.period_index
    assert state.contracts.last_status[WEEKLY].startswith("Expired")
    assert state.contracts.offers[WEEKLY][0].contract_id.startswith(f"weekly-{state.contracts.weekly_period_index}-")
