from __future__ import annotations

from production_zero.core.cards import CardInstance
from production_zero.core.company import title_for_level
from production_zero.core.enums import TradeState
from production_zero.core.market import MarketState, create_market_state, market_price_for
from production_zero.core.state import GameState
from production_zero.services.interfaces import LeaderboardEntry


class LocalMarketService:
    def __init__(self, market: MarketState | None = None) -> None:
        self._market = market or create_market_state()

    def price_for(self, resource_id: str) -> float:
        return market_price_for(self._market, resource_id)


class LocalInventoryService:
    def __init__(self) -> None:
        self._cards: dict[str, CardInstance] = {}

    def add_card(self, card: CardInstance) -> None:
        if card.card_id in self._cards:
            raise ValueError(f"Card already exists: {card.card_id}")
        self._cards[card.card_id] = card

    def get_card(self, card_id: str) -> CardInstance:
        return self._cards[card_id]


class LocalLeaderboardService:
    def __init__(
        self,
        state: GameState,
        player_name: str = "Your Company",
        mock_entries: tuple[LeaderboardEntry, ...] | None = None,
    ) -> None:
        self._state = state
        self._player_name = player_name
        self._mock_entries = mock_entries or _default_leaderboard_entries()
        self._scores: dict[str, float] = {}

    def submit_local_score(self, score_name: str, value: float) -> None:
        self._scores[score_name] = max(value, self._scores.get(score_name, value))

    def ranking(self, ranking_id: str, limit: int) -> tuple[LeaderboardEntry, ...]:
        return self._ranked_entries(ranking_id)[:limit]

    def own_entry(self, ranking_id: str) -> LeaderboardEntry:
        return next(entry for entry in self._ranked_entries(ranking_id) if entry.is_current_player)

    def _ranked_entries(self, ranking_id: str) -> tuple[LeaderboardEntry, ...]:
        entries = [*self._mock_entries, self._own_unranked_entry()]
        if ranking_id == "total_earnings":
            entries.sort(key=lambda entry: (-entry.total_earnings, -entry.company_level, entry.player_name))
        else:
            entries.sort(key=lambda entry: (-entry.company_level, -entry.current_xp, entry.player_name))
        return tuple(
            LeaderboardEntry(
                rank=index,
                player_name=entry.player_name,
                company_level=entry.company_level,
                title=entry.title,
                total_earnings=entry.total_earnings,
                current_xp=entry.current_xp,
                is_current_player=entry.is_current_player,
            )
            for index, entry in enumerate(entries, start=1)
        )

    def _own_unranked_entry(self) -> LeaderboardEntry:
        company = self._state.company
        return LeaderboardEntry(
            rank=0,
            player_name=self._player_name,
            company_level=company.level,
            title=company.current_title,
            total_earnings=self._state.statistics.total_earnings,
            current_xp=company.current_xp,
            is_current_player=True,
        )


class LocalCollectiblesService:
    def can_trade(self, card: CardInstance) -> bool:
        return card.trade_state is TradeState.COLLECTIBLE_VERIFIED and card.collectible_token_id is not None


def _default_leaderboard_entries() -> tuple[LeaderboardEntry, ...]:
    return (
        LeaderboardEntry(0, "Atlas Foundry", 37, title_for_level(37), 186_500, 7_200),
        LeaderboardEntry(0, "Northstar Steel", 28, title_for_level(28), 132_750, 2_900),
        LeaderboardEntry(0, "Copperline Works", 22, title_for_level(22), 98_400, 4_100),
        LeaderboardEntry(0, "Coal Harbor Inc.", 18, title_for_level(18), 75_250, 1_350),
        LeaderboardEntry(0, "Founders Union", 14, title_for_level(14), 54_300, 3_050),
        LeaderboardEntry(0, "Orepath Systems", 11, title_for_level(11), 42_800, 900),
        LeaderboardEntry(0, "Starter Grid", 6, title_for_level(6), 12_600, 1_100),
    )
