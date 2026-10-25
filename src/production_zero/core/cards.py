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
    mk_level: int = 1
    acquisition_cost: float | None = None
    upgrade_investment: float = 0.0
    paused: bool = False

    def __post_init__(self) -> None:
        from math import isfinite
        if type(self.mk_level) is not int or not 1 <= self.mk_level <= 99:
            raise ValueError("MK level must be an integer from 1 to 99.")
        for value in (self.acquisition_cost, self.upgrade_investment, self.output_bonus_percent, self.power_bonus_percent):
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError("Machine investment must be finite and non-negative.")

    @property
    def mk_multiplier(self) -> float:
        return 1.0 + .25 * (self.mk_level - 1)

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
        return self.mk_multiplier * (1.0 + self.output_bonus_percent / 100.0)

    @property
    def power_multiplier(self) -> float:
        if self.card_kind is CardKind.MACHINE:
            return self.mk_multiplier * (1.0 + self.output_bonus_percent * 0.5 / 100.0)
        return self.mk_multiplier * (1.0 + self.power_bonus_percent / 100.0)

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
    if not isinstance(card_kind, CardKind):
        raise ValueError(f"Unsupported collectible card kind: {card_kind}")
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






@dataclass(frozen=True, slots=True)
class CardStackKey:
    definition_id: str
    card_kind: CardKind
    rarity: Rarity
    output_bonus_tenths: int
    power_bonus_tenths: int
    mk_level: int = 1
    acquisition_cost: float | None = None
    upgrade_investment: float = 0.0
    paused: bool = False

    @classmethod
    def from_card(cls, card: CardInstance) -> CardStackKey:
        return cls(
            definition_id=card.definition_id,
            card_kind=card.card_kind,
            rarity=card.rarity,
            output_bonus_tenths=card.output_bonus_tenths,
            power_bonus_tenths=card.power_bonus_tenths,
            mk_level=card.mk_level,
            acquisition_cost=card.acquisition_cost,
            upgrade_investment=card.upgrade_investment,
            paused=card.paused,
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
