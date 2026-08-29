from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from production_zero.core.cards import create_card_instance, roll_rarity_bonus_tenths
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, RecipeDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.contracts import DAY_SECONDS

if TYPE_CHECKING:
    from production_zero.core.state import GameState


@dataclass(frozen=True, slots=True)
class SupplyOffer:
    offer_id: str
    definition_id: str
    card_kind: CardKind
    rarity: Rarity
    bonus_tenths: int
    price_cash: float
    period_index: int | None = None


@dataclass(slots=True)
class SupplyBook:
    daily_period_index: int = -1
    daily_offers: list[SupplyOffer] = field(default_factory=list)
    daily_purchased_period_index: int | None = None
    daily_purchased_offer_id: str | None = None
    freight_daily_period_index: int = -1
    freight_daily_offers: list[SupplyOffer] = field(default_factory=list)
    freight_daily_purchased_period_index: int | None = None
    freight_daily_purchased_offer_id: str | None = None
    machine_daily_period_index: int = -1
    machine_daily_offers: list[SupplyOffer] = field(default_factory=list)
    machine_daily_purchased_period_index: int | None = None
    machine_daily_purchased_offer_id: str | None = None


def refresh_supply(state: GameState, definitions: dict[str, CardDefinition]) -> None:
    daily_period = int(state.market.elapsed_seconds // DAY_SECONDS)
    if state.supply.daily_period_index != daily_period or not state.supply.daily_offers:
        state.supply.daily_period_index = daily_period
        state.supply.daily_offers = generate_daily_uncommon_offers(state.rng_seed, daily_period, definitions)
        state.supply.daily_purchased_period_index = None
        state.supply.daily_purchased_offer_id = None
    if state.supply.freight_daily_period_index != daily_period or not state.supply.freight_daily_offers:
        state.supply.freight_daily_period_index = daily_period
        state.supply.freight_daily_offers = generate_daily_freight_uncommon_offers(state.rng_seed, daily_period, definitions)
        state.supply.freight_daily_purchased_period_index = None
        state.supply.freight_daily_purchased_offer_id = None
    if state.supply.machine_daily_period_index != daily_period or not state.supply.machine_daily_offers:
        state.supply.machine_daily_period_index = daily_period
        state.supply.machine_daily_offers = generate_daily_machine_uncommon_offers(state.rng_seed, daily_period, definitions)
        state.supply.machine_daily_purchased_period_index = None
        state.supply.machine_daily_purchased_offer_id = None


def common_supply_offers(definitions: dict[str, CardDefinition]) -> tuple[SupplyOffer, ...]:
    return tuple(
        SupplyOffer(
            offer_id=f"common:{definition.definition_id}",
            definition_id=definition.definition_id,
            card_kind=definition.card_kind,
            rarity=Rarity.COMMON,
            bonus_tenths=0,
            price_cash=common_card_price(definition),
        )
        for definition in _unique_definitions(definitions)
        if _is_common_supply_definition(definition)
    )


def generate_daily_uncommon_offers(
    seed: int,
    period_index: int,
    definitions: dict[str, CardDefinition],
) -> list[SupplyOffer]:
    candidates = [
        definition
        for definition in _unique_definitions(definitions)
        if _is_standard_daily_supply_definition(definition)
    ]
    if len(candidates) < 3:
        raise ValueError("At least three supply card definitions are required.")
    rng = random.Random(f"{seed}:industrial-supply:{period_index}")
    selected = rng.sample(candidates, 3)
    offers: list[SupplyOffer] = []
    for index, definition in enumerate(selected):
        bonus_tenths = roll_rarity_bonus_tenths(Rarity.UNCOMMON, seed, f"supply:{period_index}:{definition.definition_id}")
        offers.append(
            SupplyOffer(
                offer_id=f"daily-uncommon-{period_index}-{index}",
                definition_id=definition.definition_id,
                card_kind=definition.card_kind,
                rarity=Rarity.UNCOMMON,
                bonus_tenths=bonus_tenths,
                price_cash=uncommon_card_price(definition, bonus_tenths),
                period_index=period_index,
            )
        )
    return offers


def generate_daily_freight_uncommon_offers(
    seed: int,
    period_index: int,
    definitions: dict[str, CardDefinition],
) -> list[SupplyOffer]:
    candidates = [
        definition
        for definition in _unique_definitions(definitions)
        if isinstance(definition, FreightDefinition)
    ]
    if len(candidates) < 3:
        raise ValueError("At least three freight supply card definitions are required.")
    rng = random.Random(f"{seed}:industrial-supply:freight:{period_index}")
    selected = rng.sample(candidates, 3)
    offers: list[SupplyOffer] = []
    for index, definition in enumerate(selected):
        bonus_tenths = roll_rarity_bonus_tenths(Rarity.UNCOMMON, seed, f"supply:freight:{period_index}:{definition.definition_id}")
        offers.append(
            SupplyOffer(
                offer_id=f"daily-freight-uncommon-{period_index}-{index}",
                definition_id=definition.definition_id,
                card_kind=definition.card_kind,
                rarity=Rarity.UNCOMMON,
                bonus_tenths=bonus_tenths,
                price_cash=uncommon_card_price(definition, bonus_tenths),
                period_index=period_index,
            )
        )
    return offers


def generate_daily_machine_uncommon_offers(
    seed: int,
    period_index: int,
    definitions: dict[str, CardDefinition],
) -> list[SupplyOffer]:
    candidates = [
        definition
        for definition in _unique_definitions(definitions)
        if isinstance(definition, (MachineDefinition, EnergyDefinition))
    ]
    if len(candidates) < 3:
        raise ValueError("At least three machine supply card definitions are required.")
    rng = random.Random(f"{seed}:industrial-supply:machine:{period_index}")
    selected = rng.sample(candidates, 3)
    offers: list[SupplyOffer] = []
    for index, definition in enumerate(selected):
        bonus_tenths = roll_rarity_bonus_tenths(Rarity.UNCOMMON, seed, f"supply:machine:{period_index}:{definition.definition_id}")
        offers.append(
            SupplyOffer(
                offer_id=f"daily-machine-uncommon-{period_index}-{index}",
                definition_id=definition.definition_id,
                card_kind=definition.card_kind,
                rarity=Rarity.UNCOMMON,
                bonus_tenths=bonus_tenths,
                price_cash=uncommon_card_price(definition, bonus_tenths),
                period_index=period_index,
            )
        )
    return offers


def buy_common_supply_card(
    state: GameState,
    definitions: dict[str, CardDefinition],
    definition_id: str,
) -> str:
    refresh_supply(state, definitions)
    definition = definitions[definition_id]
    if not _is_common_supply_definition(definition):
        raise ValueError(f"Card is not available in Industrial Supply: {definition_id}")
    price = common_card_price(definition)
    state.cash.spend(price)
    return _create_supply_card(state, definition, Rarity.COMMON, 0)


def buy_daily_uncommon_supply_card(
    state: GameState,
    definitions: dict[str, CardDefinition],
    offer_id: str,
) -> str:
    refresh_supply(state, definitions)
    if state.supply.daily_purchased_period_index == state.supply.daily_period_index:
        raise ValueError("Daily uncommon supply purchase has already been used.")
    offer = next((offer for offer in state.supply.daily_offers if offer.offer_id == offer_id), None)
    if offer is None:
        raise ValueError(f"Unknown daily supply offer: {offer_id}")
    definition = definitions[offer.definition_id]
    state.cash.spend(offer.price_cash)
    card_id = _create_supply_card(state, definition, offer.rarity, offer.bonus_tenths)
    state.supply.daily_purchased_period_index = state.supply.daily_period_index
    state.supply.daily_purchased_offer_id = offer.offer_id
    return card_id


def buy_daily_freight_supply_card(
    state: GameState,
    definitions: dict[str, CardDefinition],
    offer_id: str,
) -> str:
    refresh_supply(state, definitions)
    if state.supply.freight_daily_purchased_period_index == state.supply.freight_daily_period_index:
        raise ValueError("Daily freight supply purchase has already been used.")
    offer = next((offer for offer in state.supply.freight_daily_offers if offer.offer_id == offer_id), None)
    if offer is None:
        raise ValueError(f"Unknown daily freight supply offer: {offer_id}")
    definition = definitions[offer.definition_id]
    state.cash.spend(offer.price_cash)
    card_id = _create_supply_card(state, definition, offer.rarity, offer.bonus_tenths)
    state.supply.freight_daily_purchased_period_index = state.supply.freight_daily_period_index
    state.supply.freight_daily_purchased_offer_id = offer.offer_id
    return card_id


def buy_daily_machine_supply_card(
    state: GameState,
    definitions: dict[str, CardDefinition],
    offer_id: str,
) -> str:
    refresh_supply(state, definitions)
    if state.supply.machine_daily_purchased_period_index == state.supply.machine_daily_period_index:
        raise ValueError("Daily machine supply purchase has already been used.")
    offer = next((offer for offer in state.supply.machine_daily_offers if offer.offer_id == offer_id), None)
    if offer is None:
        raise ValueError(f"Unknown daily machine supply offer: {offer_id}")
    definition = definitions[offer.definition_id]
    state.cash.spend(offer.price_cash)
    card_id = _create_supply_card(state, definition, offer.rarity, offer.bonus_tenths)
    state.supply.machine_daily_purchased_period_index = state.supply.machine_daily_period_index
    state.supply.machine_daily_purchased_offer_id = offer.offer_id
    return card_id


def seconds_until_supply_daily_reset(state: GameState) -> float:
    elapsed = state.market.elapsed_seconds
    return max(0.0, (int(elapsed // DAY_SECONDS) + 1) * DAY_SECONDS - elapsed)


def common_card_price(definition: CardDefinition) -> float:
    if isinstance(definition, MachineDefinition):
        return round((120.0 + definition.base_output_per_tick * 14.0 + definition.base_power_draw * 9.0) / 5.0) * 5.0
    if isinstance(definition, EnergyDefinition):
        if definition.supply_price_cash is not None:
            return definition.supply_price_cash
        return round((100.0 + definition.base_power_output * 4.0) / 5.0) * 5.0
    if isinstance(definition, RecipeDefinition):
        input_value = sum(definition.input_resources.values())
        output_value = sum(definition.output_resources.values())
        return round((90.0 + input_value * 8.0 + output_value * 35.0) / 5.0) * 5.0
    if isinstance(definition, FreightDefinition):
        return round((140.0 + definition.base_capacity * 1.2 + definition.base_transport_time_seconds * 0.25) / 5.0) * 5.0
    raise ValueError(f"Unsupported supply definition: {definition.definition_id}")


def uncommon_card_price(definition: CardDefinition, bonus_tenths: int) -> float:
    bonus_percent = bonus_tenths / 10.0
    return round(common_card_price(definition) * (2.4 + bonus_percent * 0.28) / 5.0) * 5.0


def _create_supply_card(
    state: GameState,
    definition: CardDefinition,
    rarity: Rarity,
    bonus_tenths: int,
) -> str:
    card_id = _next_supply_card_id(state)
    state.cards[card_id] = create_card_instance(
        card_id=card_id,
        definition_id=definition.definition_id,
        card_kind=definition.card_kind,
        rarity=rarity,
        bonus_tenths=bonus_tenths,
    )
    state.history.append("cash", state.cash.amount)
    return card_id


def _next_supply_card_id(state: GameState) -> str:
    index = len(state.cards) + 1
    card_id = f"supply-card-{index:04d}"
    while card_id in state.cards:
        index += 1
        card_id = f"supply-card-{index:04d}"
    return card_id


def _is_common_supply_definition(definition: CardDefinition) -> bool:
    return isinstance(definition, (MachineDefinition, EnergyDefinition, RecipeDefinition, FreightDefinition))


def _is_standard_daily_supply_definition(definition: CardDefinition) -> bool:
    return isinstance(definition, RecipeDefinition)


def _unique_definitions(definitions: dict[str, CardDefinition]) -> tuple[CardDefinition, ...]:
    unique = {
        definition.definition_id: definition
        for definition in definitions.values()
    }
    return tuple(unique[definition_id] for definition_id in sorted(unique))
