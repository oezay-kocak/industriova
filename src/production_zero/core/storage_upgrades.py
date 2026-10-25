from __future__ import annotations
from math import isfinite

from production_zero.core.resources import ResourceDefinition
from production_zero.core.state import GameState


MAX_INVENTORY_STORAGE_LEVEL = float("inf")
INVENTORY_STORAGE_STEP_RATIO = 0.25
INVENTORY_STORAGE_BASE_COST = 250.0
INVENTORY_STORAGE_COST_GROWTH = 1.65


def inventory_storage_multiplier(level: int) -> float:
    if type(level) is not int or level < 0:
        raise ValueError("Inventory storage level cannot be negative.")
    try:
        multiplier = (1.0 + INVENTORY_STORAGE_STEP_RATIO) ** level
    except OverflowError:
        raise ValueError("Storage capacity exceeds the supported numeric range.") from None
    return _finite_capacity(multiplier)


def _finite_capacity(value):
    if not isfinite(value) or value < 0:
        raise ValueError("Storage capacity exceeds the supported numeric range.")
    return value


def inventory_storage_capacity(default_capacity: float, level: int) -> float:
    return _finite_capacity(default_capacity * inventory_storage_multiplier(level))


def global_storage_base_capacity(resource_definitions: dict[str, ResourceDefinition]) -> float:
    return _finite_capacity(sum(definition.default_capacity for definition in resource_definitions.values()))


def global_storage_capacity(resource_definitions: dict[str, ResourceDefinition], level: int) -> float:
    return _finite_capacity(global_storage_base_capacity(resource_definitions) * inventory_storage_multiplier(level))


def inventory_storage_upgrade_cost(level: int) -> float:
    if type(level) is not int or level < 0:
        raise ValueError("Inventory storage level cannot be negative.")
    try:
        return _finite_capacity(round(INVENTORY_STORAGE_BASE_COST * (1.0 + level) ** 3 / 10.0) * 10.0)
    except (OverflowError, ValueError):
        raise ValueError("Storage upgrade price exceeds the supported numeric range.") from None


def storage_base_capacity_at_level(state, resource_definitions, level):
    previous_target = global_storage_capacity(resource_definitions, max(0, level - 1))
    target = global_storage_capacity(resource_definitions, level)
    current = _finite_capacity(state.warehouse_capacity or previous_target)
    return _finite_capacity(max(target, current + (target - previous_target)))


def next_storage_capacity(state, resource_definitions):
    from production_zero.core.modifiers import research_multiplier
    base = storage_base_capacity_at_level(state, resource_definitions, state.inventory_storage_level + 1)
    return _finite_capacity(base * research_multiplier(state.research, 'storage_capacity'))


def migrate_storage_growth(state, resource_definitions):
    level = state.inventory_storage_level
    base = global_storage_base_capacity(resource_definitions)
    target = global_storage_capacity(resource_definitions, level)
    legacy_target = base * (1.0 + level * INVENTORY_STORAGE_STEP_RATIO)
    current = state.warehouse_capacity or sum(stock.capacity for stock in state.resources.values())
    state.warehouse_capacity = _finite_capacity(current + max(0.0, target - legacy_target))


def apply_inventory_storage_level(
    state: GameState,
    resource_definitions: dict[str, ResourceDefinition],
) -> None:
    level = state.inventory_storage_level
    state.warehouse_capacity = storage_base_capacity_at_level(state, resource_definitions, level)
    for resource_id, definition in resource_definitions.items():
        stock = state.ensure_resource(resource_id, definition.default_capacity)
        # Retained only as legacy serialization metadata; gameplay uses warehouse_capacity.
        stock.capacity = max(stock.capacity, inventory_storage_capacity(definition.default_capacity, level))
