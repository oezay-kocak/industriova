from __future__ import annotations

from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState


MAX_INVENTORY_STORAGE_LEVEL = 10
INVENTORY_STORAGE_STEP_RATIO = 0.25
INVENTORY_STORAGE_BASE_COST = 250.0
INVENTORY_STORAGE_COST_GROWTH = 1.65


def inventory_storage_multiplier(level: int) -> float:
    if level < 0:
        raise ValueError("Inventory storage level cannot be negative.")
    return 1.0 + level * INVENTORY_STORAGE_STEP_RATIO


def inventory_storage_capacity(default_capacity: float, level: int) -> float:
    return default_capacity * inventory_storage_multiplier(level)


def inventory_storage_upgrade_cost(level: int) -> float:
    if level < 0:
        raise ValueError("Inventory storage level cannot be negative.")
    if level >= MAX_INVENTORY_STORAGE_LEVEL:
        raise ValueError("Inventory storage is already at maximum level.")
    return round(INVENTORY_STORAGE_BASE_COST * (INVENTORY_STORAGE_COST_GROWTH ** level) / 10.0) * 10.0


def apply_inventory_storage_level(
    state: GameState,
    resource_definitions: dict[str, ResourceDefinition],
) -> None:
    level = state.inventory_storage_level
    for resource_id, definition in resource_definitions.items():
        stock = state.ensure_resource(resource_id, definition.default_capacity)
        target_capacity = inventory_storage_capacity(definition.default_capacity, level)
        stock.capacity = max(stock.capacity, stock.amount, target_capacity)
