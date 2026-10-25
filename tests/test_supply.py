from __future__ import annotations

from pathlib import Path
from release_test_support import purchase_state

import pytest

from production_zero.core.commands import AddCard, AddCash, BuildHall, BuyCommonSupplyCard, BuyDailyFreightSupplyCard, BuyDailyMachineSupplyCard, InstallCardInHall, CommandBus, SelectMachineProduction
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.resources import create_resource_inventory
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import FactoryHall, GameState
from production_zero.core.supply import DAILY_SUPPLY_OFFER_COUNT, common_supply_offers, generate_daily_freight_uncommon_offers, generate_daily_machine_uncommon_offers, refresh_supply
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.persistence.sqlite_store import SQLiteSaveStore


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _resource_inventory():
    return create_resource_inventory(load_resource_definitions(Path("src/production_zero/data/resource_definitions.json")))


def test_common_supply_purchase_spends_cash_and_adds_common_card_to_inventory_stack() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=701)
    bus = CommandBus(state)
    offer = next(offer for offer in common_supply_offers(definitions) if offer.definition_id == "machine.processor")
    bus.dispatch(AddCash(offer.price_cash))

    bus.dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))

    assert state.cash.amount == 0
    cards = [card for card in state.cards.values() if card.definition_id == offer.definition_id]
    assert len(cards) == 1
    card = cards[0]
    assert card.card_id not in state.installed_card_ids() | state.installed_freight_card_ids()
    assert card.mk_level == 1
    assert card.rarity is Rarity.COMMON
    assert card.output_bonus_tenths == 0
    assert card.is_tradeable_by_rarity is False


def test_common_supply_purchase_requires_enough_cash() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=702)
    offer = common_supply_offers(definitions)[0]

    with pytest.raises(ValueError, match="Insufficient cash"):
        CommandBus(state).dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))

    assert state.cards == {}


def test_common_supply_includes_freight_cards_and_purchase_adds_freight_stack() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=712)
    bus = CommandBus(state)
    freight_offers = [offer for offer in common_supply_offers(definitions) if offer.card_kind is CardKind.FREIGHT]

    assert {offer.definition_id for offer in freight_offers} == {
        "freight.truck",
        "freight.train",
        "freight.ship",
        "freight.aircraft",
    }

    offer = next(offer for offer in freight_offers if offer.definition_id == "freight.truck")
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))

    cards = [card for card in state.cards.values() if card.definition_id == offer.definition_id]
    assert len(cards) == 1
    card = cards[0]
    assert card.card_id not in state.installed_card_ids() | state.installed_freight_card_ids()
    assert state.cash.amount == 0
    assert card.mk_level == 1
    assert card.card_kind is CardKind.FREIGHT
    assert card.rarity is Rarity.COMMON
    assert card.output_bonus_tenths == 0
    assert card.is_tradeable_by_rarity is False


def test_common_supply_includes_reliable_early_energy_card_without_pack_dependency() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=718)
    bus = CommandBus(state)
    energy_offers = [offer for offer in common_supply_offers(definitions) if offer.card_kind is CardKind.ENERGY]

    assert {offer.definition_id for offer in energy_offers} == {
        "energy.solar_array",
        "energy.wind_turbine",
        "energy.coal_power_plant",
        "energy.gas_power_plant",
        "energy.nuclear_power_plant",
    }
    assert state.packs.unopened == []

    offer = next(offer for offer in energy_offers if offer.definition_id == "energy.solar_array")
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))

    cards = [card for card in state.cards.values() if card.definition_id == offer.definition_id]
    assert len(cards) == 1
    card = cards[0]
    assert card.card_id not in state.installed_card_ids() | state.installed_freight_card_ids()
    assert state.cash.amount == 0
    assert card.mk_level == 1
    assert card.card_kind is CardKind.ENERGY
    assert card.rarity is Rarity.COMMON
    assert card.output_bonus_tenths == 0


def test_common_supply_energy_card_can_be_installed_and_increases_power_capacity_without_dev_tools() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=719)
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)))
    offer = next(offer for offer in common_supply_offers(definitions) if offer.definition_id == "energy.solar_array")
    bus.dispatch(AddCash(offer.price_cash))

    bus.dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))
    solar = next(card for card in state.cards.values() if card.definition_id == "energy.solar_array")
    assert solar.card_id not in state.installed_card_ids()
    bus.dispatch(InstallCardInHall("purchase-energy", 0, solar.card_id, "energy"))
    SimulationEngine(definitions).advance_time(state, 1.0)

    assert state.packs.unopened == []
    assert state.energy.generated == 20
    assert state.energy.consumed == 0


def test_early_game_can_buy_energy_before_machine_power_softlock() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=720, resources=_resource_inventory())
    bus = CommandBus(state)
    bus.dispatch(BuildHall(FactoryHall(hall_id="hall-1", name="Hall 1", slot_count=6)))
    drill = create_card_instance("early-drill", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)
    second_drill = create_card_instance("early-drill-2", "machine.extractor", CardKind.MACHINE, Rarity.COMMON)
    bus.dispatch(AddCard(drill))
    bus.dispatch(AddCard(second_drill))
    bus.dispatch(InstallCardInHall("purchase-extractor", 0, drill.card_id))
    bus.dispatch(InstallCardInHall("purchase-extractor", 1, second_drill.card_id))
    bus.dispatch(SelectMachineProduction(drill.card_id, "resource.iron_ore", "iron_ore"))
    bus.dispatch(SelectMachineProduction(second_drill.card_id, "resource.iron_ore", "iron_ore"))

    engine = SimulationEngine(definitions)
    blocked = engine.advance_time(state, 1.0)
    assert state.energy.generated == 0
    assert set(blocked.blocked_cards) == {"early-drill", "early-drill-2"}

    offer = next(offer for offer in common_supply_offers(definitions) if offer.definition_id == "energy.solar_array")
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyCommonSupplyCard(offer.definition_id, definitions))
    solar = next(card for card in state.cards.values() if card.definition_id == "energy.solar_array")
    assert solar.card_id not in state.installed_card_ids()
    bus.dispatch(InstallCardInHall("purchase-energy", 0, solar.card_id, "energy"))

    recovered = engine.advance_time(state, 1.0)
    assert state.packs.unopened == []
    assert recovered.blocked_cards == ()
    assert state.energy.generated == 20
    assert state.energy.consumed == 12


def test_daily_uncommon_rotation_has_four_distinct_deterministic_offers() -> None:
    definitions = _definitions()
    first = generate_daily_machine_uncommon_offers(703, 4, definitions)
    second = generate_daily_machine_uncommon_offers(703, 4, definitions)
    next_day = generate_daily_machine_uncommon_offers(703, 5, definitions)

    assert first == second
    assert first != next_day
    assert len(first) == DAILY_SUPPLY_OFFER_COUNT
    assert len({offer.definition_id for offer in first}) == DAILY_SUPPLY_OFFER_COUNT
    assert all(offer.rarity is Rarity.UNCOMMON for offer in first)
    assert all(10 <= offer.bonus_tenths <= 50 for offer in first)
    assert all(offer.card_kind in (CardKind.MACHINE, CardKind.ENERGY) for offer in first)


def test_daily_freight_rotation_has_four_distinct_deterministic_uncommon_freight_offers() -> None:
    definitions = _definitions()
    first = generate_daily_freight_uncommon_offers(713, 4, definitions)
    second = generate_daily_freight_uncommon_offers(713, 4, definitions)
    next_day = generate_daily_freight_uncommon_offers(713, 5, definitions)

    assert first == second
    assert first != next_day
    assert len(first) == DAILY_SUPPLY_OFFER_COUNT
    assert len({offer.definition_id for offer in first}) == DAILY_SUPPLY_OFFER_COUNT
    assert all(offer.card_kind is CardKind.FREIGHT for offer in first)
    assert all(offer.rarity is Rarity.UNCOMMON for offer in first)
    assert all(10 <= offer.bonus_tenths <= 50 for offer in first)


def test_daily_machine_rotation_has_four_distinct_machine_or_energy_offers() -> None:
    definitions = _definitions()
    first = generate_daily_machine_uncommon_offers(721, 4, definitions)
    second = generate_daily_machine_uncommon_offers(721, 4, definitions)
    next_day = generate_daily_machine_uncommon_offers(721, 5, definitions)

    assert first == second
    assert first != next_day
    assert len(first) == DAILY_SUPPLY_OFFER_COUNT
    assert len({offer.definition_id for offer in first}) == DAILY_SUPPLY_OFFER_COUNT
    assert all(offer.card_kind in {CardKind.MACHINE, CardKind.ENERGY} for offer in first)
    assert all(offer.rarity is Rarity.UNCOMMON for offer in first)
    assert all(10 <= offer.bonus_tenths <= 50 for offer in first)


def test_only_one_daily_uncommon_can_be_bought_per_game_day() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=704)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    first_offer, second_offer = state.supply.machine_daily_offers[:2]
    bus.dispatch(AddCash(first_offer.price_cash + second_offer.price_cash))

    bus.dispatch(BuyDailyMachineSupplyCard(first_offer.offer_id, definitions))

    assert state.supply.machine_daily_purchased_offer_id == first_offer.offer_id
    assert state.supply.machine_daily_purchased_period_index == state.supply.machine_daily_period_index
    card = next(card for card in state.cards.values() if card.definition_id == first_offer.definition_id)
    assert card.rarity is Rarity.UNCOMMON
    assert 10 <= card.output_bonus_tenths <= 50
    assert card.is_tradeable_by_rarity is False
    with pytest.raises(ValueError, match="already been used"):
        bus.dispatch(BuyDailyMachineSupplyCard(second_offer.offer_id, definitions))


def test_only_one_daily_freight_card_can_be_bought_per_game_day() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=714)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    first_offer, second_offer = state.supply.freight_daily_offers[:2]
    bus.dispatch(AddCash(first_offer.price_cash + second_offer.price_cash))

    bus.dispatch(BuyDailyFreightSupplyCard(first_offer.offer_id, definitions))

    assert state.supply.freight_daily_purchased_offer_id == first_offer.offer_id
    assert state.supply.freight_daily_purchased_period_index == state.supply.freight_daily_period_index
    card = next(card for card in state.cards.values() if card.definition_id == first_offer.definition_id)
    assert card.card_kind is CardKind.FREIGHT
    assert card.rarity is Rarity.UNCOMMON
    assert 10 <= card.output_bonus_tenths <= 50
    assert card.is_tradeable_by_rarity is False
    with pytest.raises(ValueError, match="already been used"):
        bus.dispatch(BuyDailyFreightSupplyCard(second_offer.offer_id, definitions))


def test_daily_equipment_and_freight_purchases_are_independent() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=715)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    equipment_offer = state.supply.machine_daily_offers[0]
    freight_offer = state.supply.freight_daily_offers[0]
    bus.dispatch(AddCash(equipment_offer.price_cash + freight_offer.price_cash))

    bus.dispatch(BuyDailyMachineSupplyCard(equipment_offer.offer_id, definitions))
    bus.dispatch(BuyDailyFreightSupplyCard(freight_offer.offer_id, definitions))

    assert state.supply.machine_daily_purchased_offer_id == equipment_offer.offer_id
    assert state.supply.freight_daily_purchased_offer_id == freight_offer.offer_id
    assert {card.definition_id for card in state.cards.values()} == {
        equipment_offer.definition_id,
        freight_offer.definition_id,
    }




def test_daily_uncommon_rotation_resets_at_midnight_game_time() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=705)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    first_day_ids = [offer.offer_id for offer in state.supply.machine_daily_offers]
    offer = state.supply.machine_daily_offers[0]
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyDailyMachineSupplyCard(offer.offer_id, definitions))

    SimulationEngine(definitions).advance_time(state, 24 * 60 * 60)

    assert state.supply.machine_daily_period_index == 1
    assert state.supply.machine_daily_purchased_period_index is None
    assert [offer.offer_id for offer in state.supply.machine_daily_offers] != first_day_ids
    assert all(offer.offer_id.startswith("daily-machine-uncommon-1-") for offer in state.supply.machine_daily_offers)


def test_daily_freight_rotation_resets_at_midnight_game_time() -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=716)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    first_day_ids = [offer.offer_id for offer in state.supply.freight_daily_offers]
    offer = state.supply.freight_daily_offers[0]
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyDailyFreightSupplyCard(offer.offer_id, definitions))

    SimulationEngine(definitions).advance_time(state, 24 * 60 * 60)

    assert state.supply.freight_daily_period_index == 1
    assert state.supply.freight_daily_purchased_period_index is None
    assert [offer.offer_id for offer in state.supply.freight_daily_offers] != first_day_ids
    assert all(offer.offer_id.startswith("daily-freight-uncommon-1-") for offer in state.supply.freight_daily_offers)


def test_daily_freight_supply_selection_roundtrips_save_load(tmp_path) -> None:
    definitions = _definitions()
    state = purchase_state(rng_seed=717)
    bus = CommandBus(state)
    refresh_supply(state, definitions)
    offer = state.supply.freight_daily_offers[1]
    bus.dispatch(AddCash(offer.price_cash))
    bus.dispatch(BuyDailyFreightSupplyCard(offer.offer_id, definitions))

    store = SQLiteSaveStore(tmp_path / "save.sqlite3")
    store.initialize()
    store.save("slot-1", state)
    loaded = store.load("slot-1")

    assert loaded.supply.freight_daily_period_index == state.supply.freight_daily_period_index
    assert loaded.supply.freight_daily_purchased_period_index == state.supply.freight_daily_purchased_period_index
    assert loaded.supply.freight_daily_purchased_offer_id == offer.offer_id
    assert [offer.offer_id for offer in loaded.supply.freight_daily_offers] == [
        offer.offer_id for offer in state.supply.freight_daily_offers
    ]
