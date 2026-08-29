from __future__ import annotations

from pathlib import Path

from production_zero.core.analytics import calculate_resource_flows
from production_zero.core.cards import CardInstance
from production_zero.core.commands import AddCard, AddResource, BuildHall, CommandBus, InstallCardInHall, SelectMachineProduction, SetResourceCapacity
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions


def test_resource_flows_show_chain_rates_and_shortage() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=900)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(AddResource("iron_ore", 120))
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
    bus.dispatch(SelectMachineProduction("drill-1", "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.processor.iron", "iron"))

    SimulationEngine(definitions).advance_time(state, 0.25)
    flows = calculate_resource_flows(state, definitions)

    assert flows["iron_ore"].produced_per_minute == 240
    assert flows["iron_ore"].consumed_per_minute == 180
    assert flows["iron_ore"].net_per_minute == 60
    assert flows["iron_ore"].has_shortage is False
    assert flows["iron"].produced_per_minute == 90


def test_resource_flows_flag_shortage_when_consumption_exceeds_production() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=901)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("iron", 300))
    bus.dispatch(AddResource("iron_ore", 240))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("solar-2", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
        CardInstance("furnace-2", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "solar-2"))
    bus.dispatch(InstallCardInHall("hall-1", 2, "drill-1"))
    bus.dispatch(InstallCardInHall("hall-1", 3, "furnace-1"))
    bus.dispatch(InstallCardInHall("hall-1", 4, "furnace-2"))
    bus.dispatch(SelectMachineProduction("drill-1", "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.processor.iron", "iron"))
    bus.dispatch(SelectMachineProduction("furnace-2", "recipe.processor.iron", "iron"))

    SimulationEngine(definitions).advance_time(state, 0.25)
    flows = calculate_resource_flows(state, definitions)

    assert flows["iron_ore"].produced_per_minute == 240
    assert flows["iron_ore"].consumed_per_minute == 360
    assert flows["iron_ore"].net_per_minute == -120
    assert flows["iron_ore"].has_shortage is True


def test_resource_flows_include_multi_input_blast_furnace_chain() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=902)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("iron_ore", 500))
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(SetResourceCapacity("steel", 200))
    bus.dispatch(AddResource("iron_ore", 60))
    bus.dispatch(AddResource("coal", 30))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("blast-furnace-1", "machine.blast_furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "blast-furnace-1"))
    bus.dispatch(SelectMachineProduction("blast-furnace-1", "recipe.processor.steel", "steel"))

    SimulationEngine(definitions).advance_time(state, 0.25)
    flows = calculate_resource_flows(state, definitions)

    assert flows["iron_ore"].produced_per_minute == 0
    assert flows["iron_ore"].consumed_per_minute == 144
    assert flows["iron_ore"].has_shortage is True
    assert flows["coal"].consumed_per_minute == 36
    assert flows["coal"].has_shortage is True
    assert flows["steel"].produced_per_minute == 48
    assert flows["steel"].net_per_minute == 48


def test_resource_flows_use_selected_mining_resource() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=903)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("coal", 500))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("drill-1", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "drill-1"))
    bus.dispatch(SelectMachineProduction("drill-1", "resource.coal", "coal"))

    SimulationEngine(definitions).advance_time(state, 0.25)
    flows = calculate_resource_flows(state, definitions)

    assert "iron_ore" not in flows
    assert flows["coal"].produced_per_minute == 240
    assert flows["coal"].net_per_minute == 240


def test_resource_flows_use_selected_furnace_recipe() -> None:
    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    state = GameState(rng_seed=904)
    bus = CommandBus(state)
    bus.dispatch(SetResourceCapacity("copper_ore", 500))
    bus.dispatch(SetResourceCapacity("copper", 300))
    bus.dispatch(AddResource("copper_ore", 120))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    for card in (
        CardInstance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON, 0, 0),
        CardInstance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON, 0, 0),
    ):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-1", 0, "solar-1"))
    bus.dispatch(InstallCardInHall("hall-1", 1, "furnace-1"))
    bus.dispatch(SelectMachineProduction("furnace-1", "recipe.furnace.copper", "copper"))

    SimulationEngine(definitions).advance_time(state, 0.25)
    flows = calculate_resource_flows(state, definitions)

    assert "iron_ore" not in flows
    assert "iron" not in flows
    assert flows["copper_ore"].consumed_per_minute == 180
    assert flows["copper"].produced_per_minute == 90
