from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.cards import CardInstance
from production_zero.core.enums import Rarity


SCRAP_VALUES: dict[Rarity, int] = {
    Rarity.COMMON: 1,
    Rarity.UNCOMMON: 3,
    Rarity.RARE: 10,
    Rarity.EPIC: 35,
    Rarity.LEGENDARY: 120,
}


@dataclass(slots=True)
class IndustrialScrapWallet:
    amount: int = 0

    def add(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot add a negative scrap amount.")
        self.amount += amount

    def spend(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("Cannot spend a negative scrap amount.")
        if amount > self.amount:
            raise ValueError("Insufficient Industrial Scrap.")
        self.amount -= amount


def scrap_value_for_card(card: CardInstance) -> int:
    return SCRAP_VALUES[card.rarity]


def recycle_cards(state, card_ids: tuple[str, ...]) -> int:
    if not card_ids:
        raise ValueError("At least one card is required for recycling.")
    installed = state.installed_card_ids() | state.installed_freight_card_ids()
    seen: set[str] = set()
    total_scrap = 0

    for card_id in card_ids:
        if card_id in seen:
            raise ValueError(f"Card listed more than once: {card_id}")
        seen.add(card_id)
        if card_id not in state.cards:
            raise ValueError(f"Unknown card: {card_id}")
        if card_id in installed:
            raise ValueError(f"Installed cards cannot be recycled: {card_id}")
        total_scrap += scrap_value_for_card(state.cards[card_id])

    for card_id in card_ids:
        state.machine_production.pop(card_id, None)
        del state.cards[card_id]
    state.scrap.add(total_scrap)
    state.history.append("industrial_scrap", state.scrap.amount)
    return total_scrap
