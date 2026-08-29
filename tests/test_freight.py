from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import (
    AddCard,
    AddResource,
    AssignFreightCard,
    BuildHall,
    BuildFreightFacility,
    CancelFreightCardAssignment,
    CommandBus,
    ExpandFreightFacility,
    InstallCardInHall,
    InstallFreightCard,
    RemoveFreightCard,
    SelectMachineProduction,
    SellResource,
    SetResourceCapacity,
    UpdateFreightReserve,
)
from production_zero.core.contracts import DAILY, REGULAR, WEEKLY, ActiveContract, ContractOffer, accept_contract, deliver_available_to_contract, initialize_contracts
from production_zero.core.crafting import craft_rarity_card
from production_zero.core.definitions import FreightDefinition, MachineDefinition
from production_zero.core.enums import CardKind, FreightFamily, Rarity
from production_zero.core.freight import OutboundFreightShipment, freight_stats, start_outbound_shipments, total_facility_capacity
from production_zero.core.recycling import recycle_cards
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _install_freight_card(
    state: GameState,
    bus: CommandBus,
    definitions,
    *,
    card_id: str = "truck-1",
    definition_id: str = "freight.truck.class1",
    facility_id: str = "garage_depot",
    slot_index: int = 0,
) -> None:
    if facility_id in {"garage_depot", "rail_station", "harbor", "airport"}:
        facility_id = _ensure_facility(state, bus, facility_id)
    card = create_card_instance(card_id, definition_id, CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(card))
    bus.dispatch(InstallFreightCard(facility_id, slot_index, card.card_id, definitions))


def _assign(
    state: GameState,
    bus: CommandBus,
    card_id: str,
    resource_id: str,
    destination_kind: str,
    reserve_percent: float = 100.0,
) -> None:
    bus.dispatch(AssignFreightCard(card_id, resource_id, destination_kind, reserve_percent))


def _select_default_machine_production(state: GameState, bus: CommandBus, definitions, card_id: str) -> None:
    card = state.cards[card_id]
    definition = definitions[card.definition_id]
    assert isinstance(definition, MachineDefinition)
    production = definition.production_option(definition.default_production_id_for_card_definition(card.definition_id))
    bus.dispatch(SelectMachineProduction(card_id, production.production_id, production.output_resource))


def _ensure_facility(state: GameState, bus: CommandBus, facility_type: str) -> str:
    for facility_id, facility in state.freight.facilities.items():
        if facility.facility_type == facility_type:
            return facility_id
    state.cash.add(10_000)
    bus.dispatch(BuildFreightFacility(facility_type))
    return next(reversed(state.freight.facilities))


def _set_active_contract(
    state: GameState,
    kind: str,
    contract_id: str,
    resource_id: str,
    amount: float,
    *,
    reward_cash: float = 0.0,
    reward_xp: float = 0.0,
) -> None:
    state.contracts.active[kind] = ActiveContract(
        ContractOffer(
            contract_id=contract_id,
            kind=kind,
            name=contract_id,
            requirements={resource_id: amount},
            reward_cash=reward_cash,
            reward_xp=reward_xp,
            period_index=0,
        )
    )
    if kind == DAILY:
        state.contracts.daily_period_index = 0
    elif kind == WEEKLY:
        state.contracts.weekly_period_index = 0


def test_freight_definitions_cover_all_families_and_classes() -> None:
    definitions = _definitions()
    freight = [definition for definition in definitions.values() if isinstance(definition, FreightDefinition)]

    assert {definition.family for definition in freight} == {
        FreightFamily.TRUCK,
        FreightFamily.TRAIN,
        FreightFamily.SHIP,
        FreightFamily.AIRCRAFT,
    }
    assert {definition.class_label for definition in freight} == {"Class I"}
    assert definitions["freight.truck.class1"].name == "Freight Truck · Class I"
    assert definitions["freight.ship.class1"].facility_name == "Harbor"


def test_freight_state_has_default_facilities_and_slots() -> None:
    state = GameState(rng_seed=1)

    assert set(state.freight.facilities) == {"garage-1"}
    assert state.freight.facilities["garage-1"].name == "Garage 1"
    assert state.freight.facilities["garage-1"].facility_type == "garage_depot"
    assert len(state.freight.facilities["garage-1"].slots) == 3
    assert state.freight.outbound_shipments == {}


def test_freight_state_only_accepts_outbound_shipments() -> None:
    state = GameState(rng_seed=10)
    shipment = OutboundFreightShipment(
        shipment_id="shipment-1",
        destination_kind="market",
        resource_id="steel",
        quantity=25.0,
    )

    state.freight.outbound_shipments[shipment.shipment_id] = shipment

    assert state.freight.outbound_shipments["shipment-1"].destination_kind == "market"
    assert not hasattr(shipment, "source_id")
    assert not hasattr(shipment, "destination_id")
    with pytest.raises(ValueError, match="Unsupported outbound freight destination"):
        OutboundFreightShipment(shipment_id="internal", destination_kind="hall")


def test_freight_card_install_remove_and_facility_mapping() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=2)
    bus = CommandBus(state)
    card = create_card_instance("truck-1", "freight.truck.class1", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(card))
    rail_id = _ensure_facility(state, bus, "rail_station")

    with pytest.raises(ValueError, match="requires facility"):
        bus.dispatch(InstallFreightCard(rail_id, 0, card.card_id, definitions))

    bus.dispatch(InstallFreightCard("garage-1", 0, card.card_id, definitions))

    assert state.freight.facilities["garage-1"].slots[0].card_id == card.card_id
    assert state.installed_freight_card_ids() == {card.card_id}
    assert state.inventory_card_stacks() == ()

    bus.dispatch(RemoveFreightCard("garage-1", 0))

    assert state.freight.facilities["garage-1"].slots[0].card_id is None
    assert state.inventory_card_stacks()[0].first_card.card_id == card.card_id


def test_build_freight_facilities_allows_multiple_instances_per_type() -> None:
    state = GameState(rng_seed=32)
    bus = CommandBus(state)
    state.cash.add(2_000)

    bus.dispatch(BuildFreightFacility("garage_depot"))

    assert set(state.freight.facilities) == {"garage-1", "garage-2"}
    assert state.freight.facilities["garage-2"].name == "Garage 2"
    assert state.freight.facilities["garage-2"].facility_type == "garage_depot"
    assert state.cash.amount == 1_000


def test_build_freight_facility_requires_cash_and_creates_selected_type() -> None:
    state = GameState(rng_seed=33)
    bus = CommandBus(state)

    with pytest.raises(ValueError):
        bus.dispatch(BuildFreightFacility("rail_station"))

    state.cash.add(1_500)
    bus.dispatch(BuildFreightFacility("rail_station"))

    facility = state.freight.facilities["rail_station-1"]
    assert facility.name == "Rail Station 1"
    assert facility.facility_type == "rail_station"
    assert state.cash.amount == 0


def test_expand_freight_facility_adds_slot_and_spends_cash() -> None:
    state = GameState(rng_seed=34)
    bus = CommandBus(state)
    state.cash.add(6_000)

    bus.dispatch(ExpandFreightFacility("garage-1"))

    facility = state.freight.facilities["garage-1"]
    assert len(facility.slots) == 4
    assert facility.slots[-1].index == 3
    assert facility.expansion_level == 1
    assert state.cash.amount == 5_700

    for _ in range(5):
        bus.dispatch(ExpandFreightFacility("garage-1"))

    assert len(facility.slots) == 9
    assert facility.expansion_level == 6
    with pytest.raises(ValueError):
        bus.dispatch(ExpandFreightFacility("garage-1"))


@pytest.mark.parametrize(
    ("facility_type", "facility_id", "expected_counts"),
    [
        ("garage_depot", "garage-1", [3, 4, 5, 6, 7, 8, 9]),
        ("rail_station", "rail_station-1", [2, 3, 4, 5, 6, 7, 8]),
        ("harbor", "harbor-1", [2, 3, 4, 5]),
        ("airport", "airport-1", [2, 3, 4, 5]),
    ],
)
def test_freight_facility_type_capacity_progression(facility_type: str, facility_id: str, expected_counts: list[int]) -> None:
    state = GameState(rng_seed=341)
    bus = CommandBus(state)
    state.cash.add(20_000)
    if facility_type != "garage_depot":
        bus.dispatch(BuildFreightFacility(facility_type))

    facility = state.freight.facilities[facility_id]
    assert len(facility.slots) == expected_counts[0]
    for expected_count in expected_counts[1:]:
        bus.dispatch(ExpandFreightFacility(facility_id))
        assert len(facility.slots) == expected_count

    assert facility.expansion_level == expected_counts[-1] - expected_counts[0]
    with pytest.raises(ValueError):
        bus.dispatch(ExpandFreightFacility(facility_id))

    bus.dispatch(BuildFreightFacility(facility_type))
    same_type = [facility for facility in state.freight.facilities.values() if facility.facility_type == facility_type]
    assert len(same_type) == 2
    assert len(same_type[-1].slots) == expected_counts[0]


def test_freight_assignment_stores_resource_and_destination() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=26)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)

    bus.dispatch(AssignFreightCard("truck-1", "steel", "market"))

    assignment = state.freight.assignments["truck-1"]
    assert assignment.resource_id == "steel"
    assert assignment.destination_kind == "market"

    with pytest.raises(ValueError, match="Unsupported outbound freight destination"):
        bus.dispatch(AssignFreightCard("truck-1", "steel", "hall"))


def test_freight_rarity_capacity_and_transport_time_bonus() -> None:
    definitions = _definitions()
    definition = definitions["freight.train.class1"]
    assert isinstance(definition, FreightDefinition)
    card = create_card_instance("train-legendary", definition.definition_id, CardKind.FREIGHT, Rarity.LEGENDARY, bonus_tenths=200)

    stats = freight_stats(card, definition)

    assert stats.capacity == definition.base_capacity * 1.2
    assert stats.transport_time_seconds == definition.base_transport_time_seconds * 1.1
    assert card.is_tradeable_by_rarity is True


def test_freight_facility_total_capacity_sums_installed_cards() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=3)
    bus = CommandBus(state)
    common = create_card_instance("truck-common", "freight.truck.class1", CardKind.FREIGHT, Rarity.COMMON)
    rare = create_card_instance("truck-rare", "freight.truck.class1", CardKind.FREIGHT, Rarity.RARE, bonus_tenths=100)
    bus.dispatch(AddCard(common))
    bus.dispatch(AddCard(rare))
    bus.dispatch(InstallFreightCard("garage-1", 0, common.card_id, definitions))
    bus.dispatch(InstallFreightCard("garage-1", 1, rare.card_id, definitions))

    assert total_facility_capacity(state.freight, "garage-1", state.cards, definitions) == 40 + 44


def test_market_sell_creates_shipment_and_cash_arrives_later() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=20)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "market")
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))
    state.market.ensure_resource("steel").current_price = 9

    bus.dispatch(SellResource("steel", 4, definitions))

    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.destination_kind == "market"
    assert shipment.resource_id == "steel"
    assert shipment.quantity == 4
    assert shipment.market_price == 9
    assert shipment.freight_card_id == "truck-1"
    assert shipment.transport_capacity == 40
    assert shipment.transport_time_seconds == 60
    assert shipment.remaining_seconds == 60
    assert state.resources["steel"].amount == 6
    assert state.cash.amount == 0

    SimulationEngine(definitions).advance_time(state, 59)
    assert state.cash.amount == 0
    assert len(state.freight.outbound_shipments) == 1

    SimulationEngine(definitions).advance_time(state, 1)
    assert state.cash.amount == 36
    assert state.statistics.total_earnings == 36
    assert state.freight.outbound_shipments == {}


def test_truck_market_delivery_autoroutes_to_active_contract_before_selling_surplus() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=41)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "market")
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    offer.requirements.clear()
    offer.requirements["steel"] = 6
    accept_contract(state, DAILY, offer.contract_id)
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))
    state.market.ensure_resource("steel").current_price = 9

    bus.dispatch(SellResource("steel", 10, definitions))
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.destination_kind == "market"
    assert shipment.freight_type == "truck"

    SimulationEngine(definitions).advance_time(state, 60)

    active = state.contracts.active[DAILY]
    assert active.delivered["steel"] == 6
    assert active.status == "completed"
    assert state.cash.amount == offer.reward_cash + 36
    assert state.statistics.total_earnings == offer.reward_cash + 36
    assert state.freight.outbound_shipments == {}
    delivery = state.freight.completed_market_deliveries[-1]
    assert delivery.delivered_amount == 10
    assert delivery.contract_amount == 6
    assert delivery.market_amount == 4
    assert delivery.market_earnings == 36
    assert delivery.delivered_amount == delivery.contract_amount + delivery.market_amount


def test_market_delivery_without_contract_sells_full_amount_once() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=43)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron", "market")
    bus.dispatch(SetResourceCapacity("iron", 100))
    bus.dispatch(AddResource("iron", 40))
    state.market.ensure_resource("iron").current_price = 3

    bus.dispatch(SellResource("iron", 40, definitions))
    SimulationEngine(definitions).advance_time(state, 60)

    delivery = state.freight.completed_market_deliveries[-1]
    assert delivery.delivered_amount == 40
    assert delivery.contract_amount == 0
    assert delivery.market_amount == 40
    assert delivery.market_earnings == 120
    assert state.cash.amount == 120
    assert state.statistics.total_earnings == 120
    assert state.contracts.active == {}


def test_partial_contract_market_delivery_sells_only_surplus_without_double_payout() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=44)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron", "market")
    _set_active_contract(state, DAILY, "daily-iron", "iron", 25)
    bus.dispatch(SetResourceCapacity("iron", 100))
    bus.dispatch(AddResource("iron", 40))
    state.market.ensure_resource("iron").current_price = 3

    bus.dispatch(SellResource("iron", 40, definitions))
    SimulationEngine(definitions).advance_time(state, 60)

    active = state.contracts.active[DAILY]
    delivery = state.freight.completed_market_deliveries[-1]
    assert active.delivered["iron"] == 25
    assert active.status == "completed"
    assert delivery.delivered_amount == 40
    assert delivery.contract_amount == 25
    assert delivery.market_amount == 15
    assert delivery.market_earnings == 45
    assert delivery.delivered_amount == delivery.contract_amount + delivery.market_amount
    assert state.cash.amount == 45
    assert state.statistics.total_earnings == 45


def test_full_contract_market_delivery_creates_no_market_cash_or_sale_amount() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=45)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron", "market")
    _set_active_contract(state, DAILY, "daily-iron-full", "iron", 80)
    bus.dispatch(SetResourceCapacity("iron", 100))
    bus.dispatch(AddResource("iron", 40))
    state.market.ensure_resource("iron").current_price = 3

    bus.dispatch(SellResource("iron", 40, definitions))
    SimulationEngine(definitions).advance_time(state, 60)

    active = state.contracts.active[DAILY]
    delivery = state.freight.completed_market_deliveries[-1]
    assert active.delivered["iron"] == 40
    assert active.status == "active"
    assert delivery.delivered_amount == 40
    assert delivery.contract_amount == 40
    assert delivery.market_amount == 0
    assert delivery.market_earnings == 0
    assert state.cash.amount == 0
    assert state.statistics.total_earnings == 0


def test_market_delivery_routes_across_multiple_contracts_then_sells_remainder() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=46)
    _set_active_contract(state, REGULAR, "regular-copper", "copper", 30)
    _set_active_contract(state, DAILY, "daily-copper", "copper", 50)
    regular = state.contracts.active[REGULAR]
    daily = state.contracts.active[DAILY]
    shipment = OutboundFreightShipment(
        shipment_id="train-market-copper",
        destination_kind="market",
        resource_id="copper",
        quantity=100,
        market_price=2,
        freight_type="train",
    )

    SimulationEngine(definitions)._complete_outbound_shipments(state, (shipment,))

    delivery = state.freight.completed_market_deliveries[-1]
    assert regular.delivered["copper"] == 30
    assert daily.delivered["copper"] == 50
    assert delivery.contract_amount == 80
    assert delivery.market_amount == 20
    assert delivery.market_earnings == 40
    assert state.cash.amount == 40
    assert state.statistics.total_earnings == 40


def test_market_delivery_completes_contracts_once_and_continues_to_market_remainder() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=47)
    _set_active_contract(state, DAILY, "daily-copper-small", "copper", 10, reward_cash=200)
    _set_active_contract(state, WEEKLY, "weekly-copper-small", "copper", 5, reward_cash=100)
    daily = state.contracts.active[DAILY]
    weekly = state.contracts.active[WEEKLY]
    shipment = OutboundFreightShipment(
        shipment_id="market-copper-remainder",
        destination_kind="market",
        resource_id="copper",
        quantity=40,
        market_price=2,
    )

    SimulationEngine(definitions)._complete_outbound_shipments(state, (shipment,))

    delivery = state.freight.completed_market_deliveries[-1]
    assert daily.status == "completed"
    assert weekly.status == "completed"
    assert daily.delivered["copper"] == 10
    assert weekly.delivered["copper"] == 5
    assert delivery.contract_amount == 15
    assert delivery.market_amount == 25
    assert delivery.market_earnings == 50
    assert state.cash.amount == 350
    assert state.statistics.total_earnings == 350


def test_train_market_delivery_uses_same_contract_autorouting_path() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=42)
    bus = CommandBus(state)
    _install_freight_card(
        state,
        bus,
        definitions,
        card_id="train-1",
        definition_id="freight.train.class1",
        facility_id="rail_station",
    )
    _assign(state, bus, "train-1", "steel", "market")
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    offer.requirements.clear()
    offer.requirements["steel"] = 10
    accept_contract(state, DAILY, offer.contract_id)
    starting_cash = state.cash.amount
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))
    state.market.ensure_resource("steel").current_price = 9

    bus.dispatch(SellResource("steel", 10, definitions))
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.destination_kind == "market"
    assert shipment.freight_type == "train"

    SimulationEngine(definitions).advance_time(state, 150)

    active = state.contracts.active[DAILY]
    assert active.delivered["steel"] == 10
    assert active.status == "completed"
    assert state.cash.amount == starting_cash + offer.reward_cash
    assert state.statistics.total_earnings == offer.reward_cash
    assert state.freight.outbound_shipments == {}


def test_market_delivery_completion_is_not_truck_specific() -> None:
    source = inspect.getsource(SimulationEngine._complete_outbound_shipments)

    assert "freight.truck" not in source
    assert "FreightFamily.TRUCK" not in source
    assert ".freight_type" not in source


def test_market_sell_uses_only_matching_resource_assignment() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=27)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "coal", "market")
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))

    with pytest.raises(ValueError, match="No outbound freight capacity available"):
        bus.dispatch(SellResource("steel", 4, definitions))

    assert state.resources["steel"].amount == 10
    assert state.freight.outbound_shipments == {}


def test_market_sell_does_not_use_contract_assignment() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=28)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "contract")
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))

    with pytest.raises(ValueError, match="No outbound freight capacity available"):
        bus.dispatch(SellResource("steel", 4, definitions))

    assert state.resources["steel"].amount == 10
    assert state.freight.outbound_shipments == {}


def test_no_freight_blocks_outbound_shipment_but_not_production() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=21)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Main", slot_count=2)))
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    solar = create_card_instance("solar-no-freight", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)
    drill = create_card_instance("drill-no-freight", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON)
    bus.dispatch(AddCard(solar))
    bus.dispatch(AddCard(drill))
    bus.dispatch(InstallCardInHall("hall-1", 0, solar.card_id))
    bus.dispatch(InstallCardInHall("hall-1", 1, drill.card_id))
    _select_default_machine_production(state, bus, definitions, drill.card_id)

    SimulationEngine(definitions).advance_time(state, 3)

    assert state.resources["iron_ore"].amount == 12
    with pytest.raises(ValueError, match="No outbound freight capacity available"):
        bus.dispatch(SellResource("iron_ore", 1, definitions))
    assert state.resources["iron_ore"].amount == 12
    assert state.cash.amount == 0


def test_capacity_limit_keeps_unsent_resources_in_storage() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=22)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron_ore", "market")
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 60))

    bus.dispatch(SellResource("iron_ore", 60, definitions))

    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.quantity == 40
    assert state.resources["iron_ore"].amount == 20
    assert state.cash.amount == 0


def test_auto_sell_uses_freight_and_waits_for_arrival() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=23)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "coal", "market", 70)
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(AddResource("coal", 90))
    state.market.ensure_resource("coal").current_price = 2

    totals = SimulationEngine(definitions).advance_time(state, 1)

    assert totals.auto_sold == {"coal": 20.0}
    assert state.resources["coal"].amount == 70
    assert state.cash.amount == 0
    assert len(state.freight.outbound_shipments) == 1

    SimulationEngine(definitions).advance_time(state, 60)

    assert state.cash.amount == 40
    assert state.statistics.total_earnings == 40


def test_auto_sell_dispatches_same_freight_card_across_multiple_cycles() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=35)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "coal", "market", 50)
    bus.dispatch(SetResourceCapacity("coal", 200))
    bus.dispatch(AddResource("coal", 170))
    state.market.ensure_resource("coal").current_price = 2
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 1)
    assert first.auto_sold == {"coal": 40.0}
    assert state.resources["coal"].amount == 130
    assert len(state.freight.outbound_shipments) == 1

    second = engine.advance_time(state, 60)

    assert state.cash.amount == 80
    assert second.auto_sold == {"coal": 30.0}
    assert state.resources["coal"].amount == 100
    assert len(state.freight.outbound_shipments) == 1
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.freight_card_id == "truck-1"
    assert shipment.quantity == 30

    engine.advance_time(state, 60)

    assert state.cash.amount == 140
    assert state.freight.outbound_shipments == {}


def test_auto_sell_shipment_progresses_over_multiple_simulation_ticks_and_restarts() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=36)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "coal", "market", 50)
    bus.dispatch(SetResourceCapacity("coal", 200))
    bus.dispatch(AddResource("coal", 170))
    state.market.ensure_resource("coal").current_price = 2
    engine = SimulationEngine(definitions)

    first = engine.advance_time(state, 1)

    assert first.auto_sold == {"coal": 40.0}
    assert state.cash.amount == 0
    assert len(state.freight.outbound_shipments) == 1
    first_shipment = next(iter(state.freight.outbound_shipments.values()))
    assert first_shipment.remaining_seconds == 60
    assert first_shipment.quantity == 40
    previous_remaining = first_shipment.remaining_seconds
    previous_progress = 1.0 - first_shipment.remaining_seconds / first_shipment.transport_time_seconds

    for _ in range(30):
        engine.advance_time(state, 1)
        shipment = next(iter(state.freight.outbound_shipments.values()))
        progress = 1.0 - shipment.remaining_seconds / shipment.transport_time_seconds
        assert shipment.remaining_seconds < previous_remaining
        assert progress > previous_progress
        previous_remaining = shipment.remaining_seconds
        previous_progress = progress

    assert previous_remaining == 30
    assert previous_progress == pytest.approx(0.5)
    assert state.cash.amount == 0

    for _ in range(30):
        engine.advance_time(state, 1)

    assert state.cash.amount == 80
    assert state.statistics.total_earnings == 80
    assert len(state.freight.outbound_shipments) == 1
    next_shipment = next(iter(state.freight.outbound_shipments.values()))
    assert next_shipment.shipment_id != first_shipment.shipment_id
    assert next_shipment.freight_card_id == "truck-1"
    assert next_shipment.quantity == 30
    assert next_shipment.remaining_seconds == 60
    assert state.resources["coal"].amount == 100


def test_auto_sell_can_start_parallel_shipments_for_matching_freight_assignments() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=37)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions, card_id="truck-1", slot_index=0)
    _install_freight_card(state, bus, definitions, card_id="truck-2", slot_index=1)
    _assign(state, bus, "truck-1", "iron_ore", "market", 50)
    _assign(state, bus, "truck-2", "iron_ore", "market", 50)
    bus.dispatch(SetResourceCapacity("iron_ore", 300))
    bus.dispatch(AddResource("iron_ore", 260))
    state.market.ensure_resource("iron_ore").current_price = 1

    totals = SimulationEngine(definitions).advance_time(state, 1)

    assert totals.auto_sold == {"iron_ore": 80.0}
    assert state.resources["iron_ore"].amount == 180
    assert len(state.freight.outbound_shipments) == 2
    assert {shipment.freight_card_id for shipment in state.freight.outbound_shipments.values()} == {"truck-1", "truck-2"}


@pytest.mark.parametrize(
    ("reserve_percent", "starting_amount", "expected_shipped", "expected_remaining"),
    (
        (0, 40, 40, 0),
        (25, 90, 40, 50),
        (100, 90, 0, 90),
    ),
)
def test_market_freight_assignment_respects_reserve_percent(
    reserve_percent: float,
    starting_amount: float,
    expected_shipped: float,
    expected_remaining: float,
) -> None:
    definitions = _definitions()
    state = GameState(rng_seed=38)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron_ore", "market", reserve_percent)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", starting_amount))

    totals = SimulationEngine(definitions).advance_time(state, 1)

    if expected_shipped > 0:
        assert totals.auto_sold == {"iron_ore": expected_shipped}
        assert next(iter(state.freight.outbound_shipments.values())).quantity == expected_shipped
    else:
        assert totals.auto_sold == {}
        assert state.freight.outbound_shipments == {}
    assert state.resources["iron_ore"].amount == expected_remaining


def test_market_freight_restarts_when_storage_rises_above_reserve() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=39)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron_ore", "market", 25)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 65))
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 1)
    assert state.resources["iron_ore"].amount == 25
    engine.advance_time(state, 60)
    assert state.freight.outbound_shipments == {}

    bus.dispatch(AddResource("iron_ore", 20))
    totals = engine.advance_time(state, 1)

    assert totals.auto_sold == {"iron_ore": 20.0}
    assert state.resources["iron_ore"].amount == 25
    assert len(state.freight.outbound_shipments) == 1


def test_market_freight_reserve_can_change_during_transit_and_next_shipment_uses_it() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=92)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "iron_ore", "market", 50)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 100))
    engine = SimulationEngine(definitions)

    engine.advance_time(state, 1)
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.quantity == 40
    assert state.resources["iron_ore"].amount == 60

    bus.dispatch(UpdateFreightReserve("truck-1", 20))

    assert state.freight.assignments["truck-1"].reserve_percent == 20
    assert shipment.quantity == 40
    engine.advance_time(state, 60)
    next_shipment = next(iter(state.freight.outbound_shipments.values()))
    assert next_shipment.quantity == 40
    assert state.resources["iron_ore"].amount == 20


def test_train_market_reserve_update_uses_same_assignment_logic() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=93)
    bus = CommandBus(state)
    _install_freight_card(
        state,
        bus,
        definitions,
        card_id="train-1",
        definition_id="freight.train.class1",
        facility_id="rail_station",
    )
    _assign(state, bus, "train-1", "iron_ore", "market", 100)
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(AddResource("iron_ore", 100))

    assert SimulationEngine(definitions).advance_time(state, 1).auto_sold == {}

    bus.dispatch(UpdateFreightReserve("train-1", 0))
    totals = SimulationEngine(definitions).advance_time(state, 1)

    assert totals.auto_sold == {"iron_ore": 100.0}
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.freight_type == "train"
    assert shipment.quantity == 100
    assert state.resources["iron_ore"].amount == 0


def test_auto_sell_uses_only_matching_assignment() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=29)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "market")
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(AddResource("coal", 90))

    totals = SimulationEngine(definitions).advance_time(state, 1)

    assert totals.auto_sold == {}
    assert state.resources["coal"].amount == 90
    assert state.freight.outbound_shipments == {}


def test_contract_delivery_uses_freight_and_progresses_on_arrival() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=24)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions, definition_id="freight.ship.class1", facility_id="harbor")
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id, required = next(iter(offer.requirements.items()))
    _assign(state, bus, "truck-1", resource_id, "contract")
    bus.dispatch(SetResourceCapacity(resource_id, required * 2))
    bus.dispatch(AddResource(resource_id, required))
    accept_contract(state, DAILY, offer.contract_id)

    delivered_now = deliver_available_to_contract(state, DAILY, definitions)

    assert delivered_now[resource_id] == required
    assert state.contracts.active[DAILY].delivered == {}
    assert state.resources[resource_id].amount == 0
    assert next(iter(state.freight.outbound_shipments.values())).destination_kind == "contract"

    SimulationEngine(definitions).advance_time(state, 419)
    assert state.contracts.active[DAILY].delivered == {}

    SimulationEngine(definitions).advance_time(state, 1)
    assert state.contracts.active[DAILY].delivered[resource_id] == required
    assert state.contracts.active[DAILY].status == "completed"


def test_contract_assignment_automatically_dispatches_without_manual_delivery() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=40)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id = next(iter(offer.requirements))
    offer.requirements.clear()
    offer.requirements[resource_id] = 20
    _assign(state, bus, "truck-1", resource_id, "contract")
    bus.dispatch(SetResourceCapacity(resource_id, 100))
    bus.dispatch(AddResource(resource_id, 20))
    accept_contract(state, DAILY, offer.contract_id)
    engine = SimulationEngine(definitions)

    totals = engine.advance_time(state, 1)

    assert totals.auto_sold == {}
    assert state.resources[resource_id].amount == 0
    assert state.contracts.active[DAILY].delivered == {}
    assert len(state.freight.outbound_shipments) == 1
    shipment = next(iter(state.freight.outbound_shipments.values()))
    assert shipment.destination_kind == "contract"
    assert shipment.target_id == offer.contract_id
    assert shipment.quantity == 20

    engine.advance_time(state, 60)

    assert state.contracts.active[DAILY].delivered[resource_id] == 20
    assert state.contracts.active[DAILY].status == "completed"
    assert state.freight.outbound_shipments == {}


def test_contract_delivery_uses_only_matching_contract_assignment() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=30)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id, required = next(iter(offer.requirements.items()))
    wrong_resource = "steel" if resource_id != "steel" else "coal"
    _assign(state, bus, "truck-1", wrong_resource, "contract")
    bus.dispatch(SetResourceCapacity(resource_id, required * 2))
    bus.dispatch(AddResource(resource_id, required))
    accept_contract(state, DAILY, offer.contract_id)

    delivered_now = deliver_available_to_contract(state, DAILY, definitions)

    assert delivered_now == {}
    assert state.resources[resource_id].amount == required
    assert state.freight.outbound_shipments == {}

    bus.dispatch(AssignFreightCard("truck-1", resource_id, "market"))
    delivered_now = deliver_available_to_contract(state, DAILY, definitions)

    assert delivered_now == {}
    assert state.resources[resource_id].amount == required
    assert state.freight.outbound_shipments == {}


def test_assignment_is_locked_during_active_shipment_and_changeable_after_arrival() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=31)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "market")
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))
    bus.dispatch(SellResource("steel", 4, definitions))

    with pytest.raises(ValueError, match="currently transporting"):
        bus.dispatch(AssignFreightCard("truck-1", "coal", "market"))
    with pytest.raises(ValueError, match="currently transporting"):
        bus.dispatch(RemoveFreightCard("garage-1", 0))

    SimulationEngine(definitions).advance_time(state, 60)
    bus.dispatch(AssignFreightCard("truck-1", "coal", "market"))

    assert state.freight.assignments["truck-1"].resource_id == "coal"


def test_cancel_freight_assignment_removes_active_shipment_and_prevents_late_delivery() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=32)
    bus = CommandBus(state)
    _install_freight_card(state, bus, definitions)
    _assign(state, bus, "truck-1", "steel", "market")
    _set_active_contract(state, DAILY, "daily-steel-cancel", "steel", 4)
    bus.dispatch(SetResourceCapacity("steel", 100))
    bus.dispatch(AddResource("steel", 10))
    state.market.ensure_resource("steel").current_price = 8
    bus.dispatch(SellResource("steel", 4, definitions))

    assert len(state.freight.outbound_shipments) == 1
    assert state.resources["steel"].amount == 6
    bus.dispatch(CancelFreightCardAssignment("truck-1"))

    assert state.freight.outbound_shipments == {}
    assert "truck-1" not in state.freight.assignments
    SimulationEngine(definitions).advance_time(state, 120)
    assert state.cash.amount == 0
    assert state.freight.outbound_shipments == {}
    assert state.contracts.active[DAILY].delivered == {}
    assert state.freight.completed_market_deliveries == []

    bus.dispatch(AssignFreightCard("truck-1", "coal", "market"))
    bus.dispatch(SetResourceCapacity("coal", 100))
    bus.dispatch(AddResource("coal", 8))
    state.market.ensure_resource("coal").current_price = 5
    bus.dispatch(SellResource("coal", 3, definitions))
    SimulationEngine(definitions).advance_time(state, 60)

    assert state.cash.amount == 15
    assert state.freight.outbound_shipments == {}
    assert state.freight.assignments["truck-1"].resource_id == "coal"


def test_contract_delivery_without_freight_does_not_start_or_progress() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=25)
    bus = CommandBus(state)
    initialize_contracts(state)
    offer = state.contracts.offers[DAILY][0]
    resource_id, required = next(iter(offer.requirements.items()))
    bus.dispatch(SetResourceCapacity(resource_id, required * 2))
    bus.dispatch(AddResource(resource_id, required))
    accept_contract(state, DAILY, offer.contract_id)

    delivered_now = deliver_available_to_contract(state, DAILY, definitions)

    assert delivered_now == {}
    assert state.freight.outbound_shipments == {}
    assert state.resources[resource_id].amount == required
    assert state.contracts.active[DAILY].delivered == {}


def test_machine_inputs_remain_global_without_freight_cards() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=11)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Main Hall", slot_count=2)))
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(SetResourceCapacity("iron", 100))
    bus.dispatch(AddResource("iron_ore", 12))

    solar = create_card_instance("solar-1", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)
    furnace = create_card_instance("furnace-1", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)
    bus.dispatch(AddCard(solar))
    bus.dispatch(AddCard(furnace))
    bus.dispatch(InstallCardInHall("hall-1", 0, solar.card_id))
    bus.dispatch(InstallCardInHall("hall-1", 1, furnace.card_id))
    _select_default_machine_production(state, bus, definitions, furnace.card_id)

    SimulationEngine(definitions).advance_time(state, 4)

    assert state.freight.outbound_shipments == {}
    assert state.installed_freight_card_ids() == set()
    assert state.resources["iron_ore"].amount == 0
    assert state.resources["iron"].amount == 6


def test_production_between_halls_uses_global_storage_without_freight() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=12)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-a", name="Extraction", slot_count=2)))
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-b", name="Processing", slot_count=1)))
    bus.dispatch(SetResourceCapacity("iron_ore", 100))
    bus.dispatch(SetResourceCapacity("iron", 100))

    solar = create_card_instance("solar-a", "energy.solar_array.mk1", CardKind.ENERGY, Rarity.COMMON)
    drill = create_card_instance("drill-a", "machine.mining_drill.mk1", CardKind.MACHINE, Rarity.COMMON)
    furnace = create_card_instance("furnace-b", "machine.furnace.mk1", CardKind.MACHINE, Rarity.COMMON)
    for card in (solar, drill, furnace):
        bus.dispatch(AddCard(card))
    bus.dispatch(InstallCardInHall("hall-a", 0, solar.card_id))
    bus.dispatch(InstallCardInHall("hall-a", 1, drill.card_id))
    bus.dispatch(InstallCardInHall("hall-b", 0, furnace.card_id))
    _select_default_machine_production(state, bus, definitions, drill.card_id)
    _select_default_machine_production(state, bus, definitions, furnace.card_id)

    engine = SimulationEngine(definitions)
    engine.advance_time(state, 3)
    engine.advance_time(state, 1)

    assert state.installed_freight_card_ids() == set()
    assert state.freight.outbound_shipments == {}
    assert state.resources["iron"].amount == 6


def test_freight_stack_recycling_and_crafting_compatibility() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=4)
    bus = CommandBus(state)
    for index in range(5):
        bus.dispatch(
            AddCard(
                create_card_instance(
                    f"truck-uncommon-{index}",
                    "freight.truck.class1",
                    CardKind.FREIGHT,
                    Rarity.UNCOMMON,
                    bonus_tenths=30,
                )
            )
        )

    assert state.inventory_card_stacks()[0].quantity == 5

    crafted = craft_rarity_card(
        state,
        definitions,
        tuple(f"truck-uncommon-{index}" for index in range(5)),
        "freight.train.class1",
    )

    assert crafted.definition_id == "freight.train.class1"
    assert crafted.rarity is Rarity.RARE
    assert crafted.card_kind is CardKind.FREIGHT

    scrap = recycle_cards(state, (crafted.card_id,))

    assert scrap == 10
    assert crafted.card_id not in state.cards


def test_installed_freight_cards_cannot_be_recycled_or_crafted() -> None:
    definitions = _definitions()
    state = GameState(rng_seed=5)
    bus = CommandBus(state)
    installed = create_card_instance("installed", "freight.aircraft.class1", CardKind.FREIGHT, Rarity.RARE, bonus_tenths=80)
    bus.dispatch(AddCard(installed))
    material_ids = [installed.card_id]
    for index in range(4):
        card = create_card_instance(f"material-{index}", "freight.truck.class1", CardKind.FREIGHT, Rarity.RARE, bonus_tenths=80)
        bus.dispatch(AddCard(card))
        material_ids.append(card.card_id)
    airport_id = _ensure_facility(state, bus, "airport")
    bus.dispatch(InstallFreightCard(airport_id, 0, installed.card_id, definitions))

    with pytest.raises(ValueError, match="Installed cards cannot be recycled"):
        recycle_cards(state, (installed.card_id,))
    with pytest.raises(ValueError, match="Installed cards cannot be used for crafting"):
        craft_rarity_card(state, definitions, tuple(material_ids), "freight.truck.class1")


def test_freight_save_load_roundtrip(tmp_path) -> None:
    definitions = _definitions()
    state = GameState(rng_seed=6)
    bus = CommandBus(state)
    card = create_card_instance("ship-1", "freight.ship.class1", CardKind.FREIGHT, Rarity.EPIC, bonus_tenths=120)
    bus.dispatch(AddCard(card))
    harbor_id = _ensure_facility(state, bus, "harbor")
    state.cash.add(500)
    bus.dispatch(ExpandFreightFacility(harbor_id))
    bus.dispatch(InstallFreightCard(harbor_id, 2, card.card_id, definitions))
    bus.dispatch(AssignFreightCard(card.card_id, "steel", "contract"))
    truck = create_card_instance("truck-save", "freight.truck.class1", CardKind.FREIGHT, Rarity.COMMON)
    bus.dispatch(AddCard(truck))
    bus.dispatch(InstallFreightCard("garage-1", 0, truck.card_id, definitions))
    bus.dispatch(AssignFreightCard(truck.card_id, "iron_ore", "market", 25))
    state.freight.outbound_shipments["contract-delivery"] = OutboundFreightShipment(
        shipment_id="contract-delivery",
        destination_kind="contract",
        target_id="daily-1",
        resource_id="steel",
        quantity=15,
        freight_card_id=card.card_id,
        freight_definition_id=card.definition_id,
        freight_type="ship",
        transport_capacity=600,
        transport_time_seconds=420,
        remaining_seconds=210,
        active=True,
    )

    store = SQLiteSaveStore(tmp_path / "freight.sqlite3")
    store.initialize()
    store.save("slot", state)
    loaded = store.load("slot")

    assert loaded.cards[card.card_id].definition_id == "freight.ship.class1"
    assert loaded.freight.facilities[harbor_id].slots[2].card_id == card.card_id
    assert loaded.freight.outbound_shipments["contract-delivery"].destination_kind == "contract"
    assert loaded.freight.outbound_shipments["contract-delivery"].target_id == "daily-1"
    assert loaded.freight.outbound_shipments["contract-delivery"].remaining_seconds == 210
    assert loaded.freight.assignments[card.card_id].resource_id == "steel"
    assert loaded.freight.assignments[card.card_id].destination_kind == "contract"
    assert loaded.freight.assignments[truck.card_id].resource_id == "iron_ore"
    assert loaded.freight.assignments[truck.card_id].destination_kind == "market"
    assert loaded.freight.assignments[truck.card_id].reserve_percent == 25
    assert loaded.installed_freight_card_ids() == {card.card_id, truck.card_id}
