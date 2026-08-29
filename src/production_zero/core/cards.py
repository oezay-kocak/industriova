from __future__ import annotations

from dataclasses import dataclass
import random

from production_zero.core.enums import CardKind, Rarity, TradeState


RARITY_BONUS_RANGES_TENTHS: dict[Rarity, tuple[int, int]] = {
    Rarity.COMMON: (0, 0),
    Rarity.UNCOMMON: (10, 50),
    Rarity.RARE: (60, 100),
    Rarity.EPIC: (110, 150),
    Rarity.LEGENDARY: (160, 200),
}
TRADEABLE_RARITIES = frozenset((Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY))


@dataclass(frozen=True, slots=True)
class CardInstance:
    """A concrete owned card.

    The instance points to a static definition and carries player-owned state:
    rarity roll, bonus roll, trading state, and future collectible metadata.
    """

    card_id: str
    definition_id: str
    card_kind: CardKind
    rarity: Rarity
    output_bonus_percent: float
    power_bonus_percent: float
    trade_state: TradeState = TradeState.BOUND
    collectible_token_id: str | None = None

    @property
    def output_bonus_tenths(self) -> int:
        return round(self.output_bonus_percent * 10)

    @property
    def power_bonus_tenths(self) -> int:
        return round(self.power_bonus_percent * 10)

    @property
    def is_stackable(self) -> bool:
        return self.trade_state is TradeState.BOUND and self.collectible_token_id is None

    @property
    def is_tradeable_by_rarity(self) -> bool:
        return self.rarity in TRADEABLE_RARITIES

    @property
    def output_multiplier(self) -> float:
        return 1.0 + self.output_bonus_percent / 100.0

    @property
    def power_multiplier(self) -> float:
        if self.card_kind is CardKind.MACHINE:
            return 1.0 + self.output_bonus_percent * 0.5 / 100.0
        return 1.0 + self.power_bonus_percent / 100.0

    @property
    def freight_capacity_multiplier(self) -> float:
        if self.card_kind is not CardKind.FREIGHT:
            return 1.0
        return self.output_multiplier

    @property
    def freight_transport_time_multiplier(self) -> float:
        if self.card_kind is not CardKind.FREIGHT:
            return 1.0
        return 1.0 + self.output_bonus_percent * 0.5 / 100.0

    @property
    def recipe_input_multiplier(self) -> float:
        if self.card_kind is CardKind.RECIPE:
            return 1.0 + self.output_bonus_percent * 0.5 / 100.0
        return 1.0


def bonus_percent_from_tenths(tenths: int) -> float:
    return tenths / 10.0


def validate_rarity_bonus(rarity: Rarity, bonus_tenths: int) -> None:
    lower, upper = RARITY_BONUS_RANGES_TENTHS[rarity]
    if bonus_tenths < lower or bonus_tenths > upper:
        raise ValueError(
            f"{rarity.value} bonus must be between {bonus_percent_from_tenths(lower):.1f}% "
            f"and {bonus_percent_from_tenths(upper):.1f}%."
        )


def roll_rarity_bonus_tenths(rarity: Rarity, seed: int, salt: str) -> int:
    lower, upper = RARITY_BONUS_RANGES_TENTHS[rarity]
    if lower == upper:
        return lower
    return random.Random(f"{seed}:rarity:{rarity.value}:{salt}").randint(lower, upper)


def create_card_instance(
    card_id: str,
    definition_id: str,
    card_kind: CardKind,
    rarity: Rarity,
    bonus_tenths: int | None = None,
    seed: int = 0,
    salt: str | None = None,
) -> CardInstance:
    rolled_bonus = (
        roll_rarity_bonus_tenths(rarity, seed, salt or card_id)
        if bonus_tenths is None
        else bonus_tenths
    )
    validate_rarity_bonus(rarity, rolled_bonus)
    output_bonus = bonus_percent_from_tenths(rolled_bonus)
    power_bonus = output_bonus * 0.5 if card_kind in {CardKind.MACHINE, CardKind.FREIGHT} else 0.0
    return CardInstance(
        card_id=card_id,
        definition_id=definition_id,
        card_kind=card_kind,
        rarity=rarity,
        output_bonus_percent=output_bonus,
        power_bonus_percent=power_bonus,
    )


def effective_recipe_outputs(card: CardInstance, output_resources: dict[str, float]) -> dict[str, float]:
    if card.card_kind is not CardKind.RECIPE:
        raise ValueError("Recipe effects require a recipe card.")
    return {
        resource_id: amount * card.output_multiplier
        for resource_id, amount in output_resources.items()
    }


def effective_recipe_inputs(card: CardInstance, input_resources: dict[str, float]) -> dict[str, float]:
    if card.card_kind is not CardKind.RECIPE:
        raise ValueError("Recipe effects require a recipe card.")
    return {
        resource_id: amount * card.recipe_input_multiplier
        for resource_id, amount in input_resources.items()
    }


@dataclass(frozen=True, slots=True)
class CardStackKey:
    definition_id: str
    card_kind: CardKind
    rarity: Rarity
    output_bonus_tenths: int
    power_bonus_tenths: int

    @classmethod
    def from_card(cls, card: CardInstance) -> CardStackKey:
        return cls(
            definition_id=card.definition_id,
            card_kind=card.card_kind,
            rarity=card.rarity,
            output_bonus_tenths=card.output_bonus_tenths,
            power_bonus_tenths=card.power_bonus_tenths,
        )


@dataclass(frozen=True, slots=True)
class CardStack:
    key: CardStackKey | None
    cards: tuple[CardInstance, ...]

    @property
    def quantity(self) -> int:
        return len(self.cards)

    @property
    def first_card(self) -> CardInstance:
        return self.cards[0]
