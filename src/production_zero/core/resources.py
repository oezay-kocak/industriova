from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    resource_id: str
    name: str
    default_capacity: float
    icon_key: str = ""
    accent_key: str = ""
    category: str = ""


@dataclass(slots=True)
class ResourceStock:
    amount: float = 0.0
    capacity: float = 0.0

    @property
    def free_capacity(self) -> float:
        return max(0.0, self.capacity - self.amount)

    @property
    def fill_ratio(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return min(1.0, max(0.0, self.amount / self.capacity))

    def add(self, amount: float) -> float:
        if amount < 0:
            raise ValueError("Cannot add a negative resource amount.")
        accepted = min(amount, self.free_capacity)
        self.amount += accepted
        return accepted

    def consume(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Cannot consume a negative resource amount.")
        if amount > self.amount:
            raise ValueError("Insufficient resource amount.")
        self.amount -= amount


def create_resource_inventory(definitions: dict[str, ResourceDefinition]) -> dict[str, ResourceStock]:
    return {
        resource_id: ResourceStock(amount=0.0, capacity=definition.default_capacity)
        for resource_id, definition in definitions.items()
    }
