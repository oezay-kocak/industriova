from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from math import floor, isfinite
from typing import TYPE_CHECKING

from production_zero.core.cards import create_card_instance, roll_rarity_bonus_tenths
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.contracts import DAY_SECONDS

if TYPE_CHECKING:
    from production_zero.core.state import GameState


DAILY_SUPPLY_OFFER_COUNT = 4


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
    _refresh_supply_book(state.supply, state.rng_seed, daily_period, definitions)


def _refresh_supply_book(book, seed, daily_period, definitions):
    for category, generate in (("freight", generate_daily_freight_uncommon_offers),
                               ("machine", generate_daily_machine_uncommon_offers)):
        prefix = f"{category}_daily_"
        if getattr(book, prefix + "period_index") != daily_period or not getattr(book, prefix + "offers"):
            offers = generate(seed, daily_period, definitions)
            setattr(book, prefix + "period_index", daily_period)
            setattr(book, prefix + "offers", offers)
            setattr(book, prefix + "purchased_period_index", None)
            setattr(book, prefix + "purchased_offer_id", None)
    # Pending offers are quotes, not historical acquisition values. Preserve IDs,
    # rarity, bonus and daily purchase rights while applying the current catalog.
    reprice_pending_freight_offers(book,definitions)


def reprice_pending_freight_offers(book,definitions):
    purchased = book.freight_daily_purchased_offer_id if book.freight_daily_purchased_period_index == book.freight_daily_period_index else None
    book.freight_daily_offers = [replace(offer, price_cash=uncommon_card_price(definitions[offer.definition_id], offer.bonus_tenths))
                                if offer.definition_id=='freight.ship' and offer.definition_id in definitions and offer.offer_id!=purchased else offer
                                for offer in book.freight_daily_offers]


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
    if len(candidates) < DAILY_SUPPLY_OFFER_COUNT:
        raise ValueError(f"At least {DAILY_SUPPLY_OFFER_COUNT} freight supply card definitions are required.")
    rng = random.Random(f"{seed}:industrial-supply:freight:{period_index}")
    selected = rng.sample(candidates, DAILY_SUPPLY_OFFER_COUNT)
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
    if len(candidates) < DAILY_SUPPLY_OFFER_COUNT:
        raise ValueError(f"At least {DAILY_SUPPLY_OFFER_COUNT} machine supply card definitions are required.")
    rng = random.Random(f"{seed}:industrial-supply:machine:{period_index}")
    selected = rng.sample(candidates, DAILY_SUPPLY_OFFER_COUNT)
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


MAX_SUPPLY_PURCHASE_QUANTITY = 10000


def _check_operation(state, operation_id):
    if operation_id is not None:
        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("Invalid purchase operation ID.")
        if operation_id in state.completed_card_operations:
            raise ValueError("Purchase command has already been committed.")


def _check_price(state, unit_price, quantity, expected_unit_price=None):
    if type(quantity) is not int or not 1 <= quantity <= MAX_SUPPLY_PURCHASE_QUANTITY:
        raise ValueError("Enter a whole purchase quantity from 1 to 10000.")
    if not isfinite(unit_price) or unit_price <= 0:
        raise ValueError("Invalid purchase price.")
    if expected_unit_price is not None and unit_price != expected_unit_price:
        raise ValueError("Purchase price changed. Review the quote again.")
    total = round(unit_price * quantity, 2)
    if not isfinite(total) or not isfinite(state.cash.amount):
        raise ValueError("Purchase exceeds the supported cash range.")
    if state.cash.amount < total:
        raise ValueError("Insufficient cash.")
    return total


def common_supply_max_quantity(state, definitions, definition_id):
    """Backend quote; physical storage and installed slots never limit cards."""
    definition = definitions.get(definition_id)
    if not _is_common_supply_definition(definition):
        raise ValueError("Card is not available in Common Supply.")
    price = common_card_price(definition)
    if not isfinite(price) or price <= 0 or not isfinite(state.cash.amount):
        raise ValueError("Invalid purchase price or cash balance.")
    return min(MAX_SUPPLY_PURCHASE_QUANTITY, max(0, floor(state.cash.amount / price)))


def _acquire_supply_cards(state, definition, quantity, unit_price, *, rarity=Rarity.COMMON,
                          bonus_tenths=0, expected_unit_price=None, operation_id=None,
                          supply_book=None):
    from uuid import uuid4
    _check_operation(state, operation_id)
    total = _check_price(state, unit_price, quantity, expected_unit_price)
    cards = tuple(replace(create_card_instance("machine-" + uuid4().hex, definition.definition_id,
                        definition.card_kind, rarity, bonus_tenths=bonus_tenths),
                        acquisition_cost=unit_price) for _ in range(quantity))
    ids = tuple(card.card_id for card in cards)
    if len(set(ids)) != len(ids) or any(cid in state.cards for cid in ids):
        raise ValueError("Purchase requires fresh unique card IDs.")
    # All rejectable work is complete. Commit one debit and the prepared cards.
    state.cash.spend(total)
    state.cards.update((card.card_id, card) for card in cards)
    if supply_book is not None:
        state.supply = supply_book
    if operation_id is not None:
        state.completed_card_operations.add(operation_id)
    state.history.append("cash", state.cash.amount)
    return ids


def buy_common_supply_cards(state: GameState, definitions: dict[str, CardDefinition], definition_id: str,
                            quantity: int = 1, *, expected_unit_price=None, operation_id=None) -> tuple[str, ...]:
    definition = definitions.get(definition_id)
    if not _is_common_supply_definition(definition):
        raise ValueError("Card is not available in Common Supply.")
    return _acquire_supply_cards(state, definition, quantity, common_card_price(definition),
                                expected_unit_price=expected_unit_price, operation_id=operation_id)


def buy_common_supply_card(state, definitions, definition_id) -> str:
    return buy_common_supply_cards(state, definitions, definition_id, 1)[0]


def _buy_daily_supply_card(state, definitions, offer_id, category, expected_unit_price, operation_id):
    _check_operation(state, operation_id)
    # Rotation is planned on a detached book: a stale/failed purchase must not
    # consume daily rights, rotate live offers or alter history.
    book = replace(state.supply)
    period = int(state.market.elapsed_seconds // DAY_SECONDS)
    _refresh_supply_book(book, state.rng_seed, period, definitions)
    prefix = f"{category}_daily_"
    if getattr(book, prefix + "purchased_period_index") == period:
        raise ValueError(f"Daily {category} supply purchase has already been used.")
    offer = next((offer for offer in getattr(book, prefix + "offers") if offer.offer_id == offer_id), None)
    if offer is None or offer.period_index != period:
        raise ValueError(f"Unknown daily {category} supply offer: {offer_id}")
    definition = definitions.get(offer.definition_id)
    allowed = (FreightDefinition,) if category == "freight" else (MachineDefinition, EnergyDefinition)
    if not isinstance(definition, allowed) or definition.card_kind != offer.card_kind:
        raise ValueError("Offer requires a compatible supply definition.")
    setattr(book, prefix + "purchased_period_index", period)
    setattr(book, prefix + "purchased_offer_id", offer.offer_id)
    return _acquire_supply_cards(state, definition, 1, offer.price_cash, rarity=offer.rarity,
                bonus_tenths=offer.bonus_tenths, expected_unit_price=expected_unit_price,
                operation_id=operation_id, supply_book=book)[0]


def buy_daily_freight_supply_card(state, definitions, offer_id, *, expected_unit_price=None, operation_id=None) -> str:
    return _buy_daily_supply_card(state, definitions, offer_id, "freight", expected_unit_price, operation_id)


def buy_daily_machine_supply_card(state, definitions, offer_id, *, expected_unit_price=None, operation_id=None) -> str:
    return _buy_daily_supply_card(state, definitions, offer_id, "machine", expected_unit_price, operation_id)


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
    if isinstance(definition, FreightDefinition):
        if definition.supply_price_cash is not None:
            if not isfinite(definition.supply_price_cash) or definition.supply_price_cash <= 0:
                raise ValueError('Invalid freight supply price.')
            return definition.supply_price_cash
        return round((140.0 + definition.base_capacity * 1.2 + definition.base_transport_time_seconds * 0.25) / 5.0) * 5.0
    raise ValueError(f"Unsupported supply definition: {definition.definition_id}")


def uncommon_card_price(definition: CardDefinition, bonus_tenths: int) -> float:
    bonus_percent = bonus_tenths / 10.0
    return round(common_card_price(definition) * (2.4 + bonus_percent * 0.28) / 5.0) * 5.0


def _is_common_supply_definition(definition: CardDefinition) -> bool:
    return isinstance(definition, (MachineDefinition, EnergyDefinition, FreightDefinition))




def _unique_definitions(definitions: dict[str, CardDefinition]) -> tuple[CardDefinition, ...]:
    unique = {
        definition.definition_id: definition
        for definition in definitions.values()
    }
    return tuple(unique[definition_id] for definition_id in sorted(unique))
