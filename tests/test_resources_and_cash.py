from __future__ import annotations

from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, AddIndustrialScrap, AddResource, AssignFreightCard, BuildHall, CommandBus, ConfigureAutoSell, ConsumeResource, ExpandInventoryStorage, InstallFreightCard, PurchaseHall, SellResource, SetResourceCapacity, SpendCash, UnlockProductionLine, UnlockProductionSlot
from production_zero.core.economy import hall_purchase_price, sell_price_for
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.history import MetricHistory, MetricSeries
from production_zero.core.resources import create_resource_inventory
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState, MAX_FACTORY_LINES, MAX_FACTORY_SLOTS_PER_LINE
from production_zero.core.storage_upgrades import (
    MAX_INVENTORY_STORAGE_LEVEL,
    inventory_storage_capacity,
    inventory_storage_upgrade_cost,
)
from production_zero.data.definitions import load_card_definitions, load_resource_definitions


def _card_definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _install_truck(state: GameState, bus: CommandBus, definitions, resource_id: str) -> None:
    card = create_card_instance("truck-1", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(card))
    bus.dispatch(InstallFreightCard("garage-1", 0, card.card_id, definitions))
    bus.dispatch(AssignFreightCard(card.card_id, resource_id, "market"))


def test_initial_resource_inventory_uses_definition_capacities() -> None:
    definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    inventory = create_resource_inventory(definitions)

    assert {
        "iron_ore",
        "coal",
        "copper_ore",
        "iron",
        "copper",
        "steel",
        "steel_components",
        "timber",
        "wheat",
        "ai_server",
    }.issubset(inventory)
    assert len(inventory) > 300
    assert inventory["iron_ore"].amount == 0
    assert inventory["iron_ore"].capacity == 500


def test_resource_commands_respect_capacity_and_consumption() -> None:
    state = GameState(rng_seed=7)
    bus = CommandBus(state)

    bus.dispatch(SetResourceCapacity("coal", 10))
    bus.dispatch(AddResource("coal", 7))
    bus.dispatch(AddResource("coal", 99))
    bus.dispatch(ConsumeResource("coal", 4))

    assert state.resources["coal"].amount == 6
    assert state.resources["coal"].capacity == 10
    assert state.resources["coal"].fill_ratio == 0.6

    with pytest.raises(ValueError):
        bus.dispatch(ConsumeResource("coal", 7))


def test_inventory_storage_expansion_increases_capacity_and_spends_cash_once() -> None:
    definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=701, resources=create_resource_inventory(definitions))
    bus = CommandBus(state)
    bus.dispatch(AddCash(1_000))
    state.resources["iron_ore"].amount = 120
    state.resources["copper_ore"].amount = 45
    starting_cash = state.cash.amount
    starting_card_capacity = len(state.cards)
    cost = inventory_storage_upgrade_cost(0)

    bus.dispatch(ExpandInventoryStorage(definitions))

    assert state.inventory_storage_level == 1
    assert state.cash.amount == starting_cash - cost
    assert state.history.values_for("cash") == (starting_cash - cost,)
    assert state.resources["iron_ore"].capacity == inventory_storage_capacity(definitions["iron_ore"].default_capacity, 1)
    assert state.resources["copper_ore"].capacity == inventory_storage_capacity(definitions["copper_ore"].default_capacity, 1)
    assert state.resources["iron_ore"].amount == 120
    assert state.resources["copper_ore"].amount == 45
    assert len(state.cards) == starting_card_capacity
    assert state.freight.facilities["garage-1"].slot_count == 3
    assert state.halls == {}


def test_inventory_storage_expansion_requires_cash_without_mutating_state() -> None:
    definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=702, resources=create_resource_inventory(definitions))
    bus = CommandBus(state)
    before_capacities = {resource_id: stock.capacity for resource_id, stock in state.resources.items()}

    with pytest.raises(ValueError, match="Insufficient cash"):
        bus.dispatch(ExpandInventoryStorage(definitions))

    assert state.inventory_storage_level == 0
    assert state.cash.amount == 0
    assert {resource_id: stock.capacity for resource_id, stock in state.resources.items()} == before_capacities


def test_inventory_storage_upgrade_costs_rise_and_expansion_passes_legacy_limit() -> None:
    definitions = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=703, resources=create_resource_inventory(definitions))
    bus = CommandBus(state)
    costs = [inventory_storage_upgrade_cost(level) for level in range(25)]
    assert all(right > left for left, right in zip(costs, costs[1:]))
    bus.dispatch(AddCash(sum(costs)))
    previous = state.storage_capacity
    for level, cost in enumerate(costs):
        cash = state.cash.amount
        bus.dispatch(ExpandInventoryStorage(definitions))
        assert state.inventory_storage_level == level + 1
        assert state.cash.amount == pytest.approx(cash - cost)
        assert state.storage_capacity > previous
        previous = state.storage_capacity
    assert state.cash.amount == pytest.approx(0)
    assert state.inventory_storage_level == 25


def test_cash_commands_keep_currency_single_and_explicit() -> None:
    state = GameState(rng_seed=8)
    bus = CommandBus(state)

    bus.dispatch(AddCash(250))
    bus.dispatch(SpendCash(40))

    assert state.cash.amount == 210
    assert state.statistics.total_earnings == 0
    with pytest.raises(ValueError):
        bus.dispatch(SpendCash(211))


def test_static_sell_prices_cover_current_economic_resources() -> None:
    assert sell_price_for("iron_ore") == 1.0
    assert sell_price_for("coal") > 0
    assert sell_price_for("copper_ore") > 0
    assert sell_price_for("iron") > sell_price_for("iron_ore")
    assert sell_price_for("copper") > sell_price_for("copper_ore")
    assert sell_price_for("steel") > sell_price_for("iron")


def test_hall_purchase_price_scales_with_existing_halls() -> None:
    assert hall_purchase_price(1) == 15200
    assert hall_purchase_price(2) == 86000
    assert hall_purchase_price(3) == 237000


def test_sell_resource_consumes_stock_adds_cash_and_records_history() -> None:
    definitions = _card_definitions()
    state = GameState(rng_seed=9)
    bus = CommandBus(state)
    _install_truck(state, bus, definitions, "steel")
    bus.dispatch(SetResourceCapacity("steel", 20))
    bus.dispatch(AddResource("steel", 10))

    bus.dispatch(SellResource("steel", 4, definitions))

    assert state.resources["steel"].amount == 6
    assert state.cash.amount == 0
    assert state.statistics.total_earnings == 0
    assert len(state.freight.outbound_shipments) == 1
    assert state.history.values_for("resource.steel") == (6.0,)
    assert state.history.values_for("cash") == ()

    SimulationEngine(definitions).advance_time(state, 60)

    assert state.cash.amount == 27
    assert state.statistics.total_earnings == 27
    assert state.history.values_for("cash") == (27.0, 27.0)

    with pytest.raises(ValueError):
        bus.dispatch(SellResource("steel", 7, definitions))


def test_sell_resource_uses_current_market_price() -> None:
    definitions = _card_definitions()
    state = GameState(rng_seed=15)
    bus = CommandBus(state)
    _install_truck(state, bus, definitions, "coal")
    bus.dispatch(SetResourceCapacity("coal", 20))
    bus.dispatch(AddResource("coal", 10))
    state.market.ensure_resource("coal").current_price = 2.5

    bus.dispatch(SellResource("coal", 4, definitions))

    assert state.resources["coal"].amount == 6
    assert state.cash.amount == 0

    SimulationEngine(definitions).advance_time(state, 60)

    assert state.cash.amount == pytest.approx(4.0)


def test_industrial_scrap_is_account_bound_and_not_sellable() -> None:
    state = GameState(rng_seed=16)
    bus = CommandBus(state)
    bus.dispatch(AddIndustrialScrap(12))

    with pytest.raises(ValueError, match="Resource cannot be sold"):
        bus.dispatch(SellResource("industrial_scrap", 1, _card_definitions()))
    with pytest.raises(ValueError, match="Resource cannot be auto-sold"):
        bus.dispatch(ConfigureAutoSell("industrial_scrap", True, 70))

    assert state.scrap.amount == 12
    assert "industrial_scrap" not in state.resources


def test_configure_auto_sell_stores_resource_threshold() -> None:
    state = GameState(rng_seed=14)
    bus = CommandBus(state)

    bus.dispatch(ConfigureAutoSell("iron_ore", True, 70))

    assert state.auto_sell["iron_ore"].enabled is True
    assert state.auto_sell["iron_ore"].threshold_percent == 70

    with pytest.raises(ValueError):
        bus.dispatch(ConfigureAutoSell("iron_ore", True, 101))
    with pytest.raises(ValueError):
        bus.dispatch(ConfigureAutoSell("unknown_resource", True, 50))


def test_unlock_production_line_spends_cash_and_adds_slots() -> None:
    state = GameState(rng_seed=10)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6, max_lines=MAX_FACTORY_LINES)))
    bus.dispatch(AddCash(3600))

    bus.dispatch(UnlockProductionLine("hall-1", "hall-1.line-3"))

    hall = state.halls["hall-1"]
    assert state.cash.amount == 0
    assert hall.production_lines[2].unlocked is True
    assert hall.production_lines[2].slot_indexes == [6, 7, 8]
    assert len(hall.slots) == 50
    assert hall.slot_count == 9
    assert state.history.values_for("cash") == (0.0,)


def test_unlock_production_line_requires_enough_cash() -> None:
    state = GameState(rng_seed=11)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(749))

    with pytest.raises(ValueError):
        bus.dispatch(UnlockProductionLine("hall-1", "hall-1.line-3"))

    hall = state.halls["hall-1"]
    assert state.cash.amount == 749
    assert hall.production_lines[2].unlocked is False
    assert hall.slot_count == 6


def test_unlock_production_slots_individually_up_to_eight_per_line() -> None:
    state = GameState(rng_seed=111)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(5_000))

    for _ in range(7):
        bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))

    hall = state.halls["hall-1"]
    assert hall.production_lines[0].slot_indexes == [0, 1, 2, 6, 7, 8, 9, 10, 11, 12]
    assert hall.slot_count == 13
    with pytest.raises(ValueError):
        bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))


def test_unlock_production_lines_three_to_six_and_full_hall_capacity() -> None:
    state = GameState(rng_seed=112)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6, max_lines=MAX_FACTORY_LINES)))
    bus.dispatch(AddCash(50_000))

    for line_number in range(3, MAX_FACTORY_LINES + 1):
        line_id = f"hall-1.line-{line_number}"
        bus.dispatch(UnlockProductionLine("hall-1", line_id))
        line = state.halls["hall-1"].production_lines[line_number - 1]
        assert line.unlocked is True
        assert len(line.slot_indexes) == 3

    hall = state.halls["hall-1"]
    assert len(hall.production_lines) == MAX_FACTORY_LINES

    for line in hall.production_lines:
        while len(line.slot_indexes) < MAX_FACTORY_SLOTS_PER_LINE:
            bus.dispatch(UnlockProductionSlot("hall-1", line.line_id))

    unlocked_indexes = hall.unlocked_slot_indexes()
    assert hall.slot_count == MAX_FACTORY_LINES * MAX_FACTORY_SLOTS_PER_LINE
    assert len(unlocked_indexes) == 50
    assert len(set(unlocked_indexes)) == 50
    assert all(len(line.slot_indexes) == MAX_FACTORY_SLOTS_PER_LINE for line in hall.production_lines)


def test_factory_halls_keep_independent_slot_expansions() -> None:
    state = GameState(rng_seed=113)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(20_000))
    bus.dispatch(PurchaseHall())

    bus.dispatch(UnlockProductionSlot("hall-1", "hall-1.line-1"))

    assert state.halls["hall-1"].slot_count == 7
    assert state.halls["hall-2"].slot_count == 3
    assert len(state.halls["hall-1"].production_lines[0].slot_indexes) == 4
    assert len(state.halls["hall-2"].production_lines[0].slot_indexes) == 3


def test_purchase_hall_spends_cash_and_creates_independent_hall() -> None:
    state = GameState(rng_seed=12)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(15_200))

    bus.dispatch(PurchaseHall())

    assert state.cash.amount == 0
    assert set(state.halls) == {"hall-1", "hall-2"}
    assert state.halls["hall-2"].name == "Hall 2"
    assert len(state.halls["hall-2"].slots) == 50
    assert state.halls["hall-2"].slot_count == 3
    assert state.halls["hall-2"].production_lines[0].slot_indexes == [0, 1, 2]
    assert state.halls["hall-2"].production_lines[1].slot_indexes == []
    assert state.halls["hall-2"].production_lines[2].slot_indexes == []
    assert state.halls["hall-2"].production_lines[2].unlocked is False
    assert state.history.values_for("cash") == (0.0,)


def test_purchase_hall_requires_enough_cash_and_scales_next_price() -> None:
    state = GameState(rng_seed=13)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Halle 1", slot_count=6)))
    bus.dispatch(AddCash(16_699))

    bus.dispatch(PurchaseHall())

    assert state.cash.amount == 1499
    assert "hall-2" in state.halls
    with pytest.raises(ValueError):
        bus.dispatch(PurchaseHall())

    assert state.cash.amount == 1499
    assert set(state.halls) == {"hall-1", "hall-2"}


def test_metric_series_keeps_recent_points_only() -> None:
    series = MetricSeries(metric_id="cash", max_points=3)

    for value in (1, 2, 3, 4, 5):
        series.append(value)

    assert series.snapshot() == (3.0, 4.0, 5.0)


def test_metric_history_returns_elapsed_time_windows_for_chart_ranges() -> None:
    history = MetricHistory()
    for value in range(700):
        history.elapsed_seconds = value
        history.append("cash", value, max_points=1_000)

    assert history.values_for_range("cash", "10M")[0] == 99.0
    assert len(history.values_for_range("cash", "10M")) == 601
    assert len(history.values_for_range("cash", "ALL")) == 700
