from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AccountStatistics:
    total_earnings: float = 0.0

    def record_earnings(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Earnings cannot be negative.")
        self.total_earnings += amount
