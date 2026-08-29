from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from production_zero.core.cards import CardInstance


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    rank: int
    player_name: str
    company_level: int
    title: str
    total_earnings: float
    current_xp: float = 0.0
    is_current_player: bool = False


class MarketService(Protocol):
    def price_for(self, resource_id: str) -> float:
        """Return the current local market price for a resource."""


class InventoryService(Protocol):
    def add_card(self, card: CardInstance) -> None:
        """Add a card instance to the player's inventory."""

    def get_card(self, card_id: str) -> CardInstance:
        """Return a concrete card instance."""


class LeaderboardService(Protocol):
    def submit_local_score(self, score_name: str, value: float) -> None:
        """Store a local score candidate."""

    def ranking(self, ranking_id: str, limit: int) -> tuple[LeaderboardEntry, ...]:
        """Return a trusted or local prototype ranking."""

    def own_entry(self, ranking_id: str) -> LeaderboardEntry:
        """Return the current player's ranked entry."""


class CollectiblesService(Protocol):
    def can_trade(self, card: CardInstance) -> bool:
        """Return whether a card can be traded through a trusted authority."""
