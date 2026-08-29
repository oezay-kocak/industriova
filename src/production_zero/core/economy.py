from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.market import BASE_MARKET_PRICES


def hall_purchase_price(existing_hall_count: int) -> float:
    if existing_hall_count < 0:
        raise ValueError("Hall count cannot be negative.")
    return 1000.0 + max(0, existing_hall_count - 1) * 500.0


def sell_price_for(resource_id: str) -> float:
    return BASE_MARKET_PRICES.get(resource_id, 0.0)


@dataclass(slots=True)
class CashWallet:
    amount: float = 0.0

    def add(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Cannot add a negative cash amount.")
        self.amount += amount

    def spend(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Cannot spend a negative cash amount.")
        if amount > self.amount:
            raise ValueError("Insufficient cash.")
        self.amount -= amount


@dataclass(slots=True)
class EnergyState:
    generated: float = 0.0
    consumed: float = 0.0

    @property
    def surplus(self) -> float:
        return self.generated - self.consumed

    @property
    def load_ratio(self) -> float:
        if self.generated <= 0:
            return 0.0
        return min(1.0, max(0.0, self.consumed / self.generated))
