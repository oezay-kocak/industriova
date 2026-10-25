from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from production_zero.core.definitions import CardDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.progression import is_production_unlocked, production_options

if TYPE_CHECKING:
    from production_zero.core.state import GameState


@dataclass(frozen=True, slots=True)
class ProductionValue:
    production_id: str
    resource_id: str
    name: str
    machine_name: str
    value_per_unit: float
    output_per_minute: float
    own_value_per_unit: float
    direct_input_value_per_unit: float
    depth: int
    base_resource_count: int


@dataclass(frozen=True, slots=True)
class ContractProductOption:
    resource_id: str
    production_id: str
    name: str
    value_per_unit: float
    required_amount: float


class ProductionValueCalculator:
    def __init__(self, definitions: dict[str, CardDefinition]) -> None:
        self._definitions = definitions
        self._machines = {
            definition.definition_id: definition
            for definition in definitions.values()
            if isinstance(definition, MachineDefinition)
        }
        self._options: dict[str, tuple[MachineDefinition, ProductionOptionDefinition]] = {}
        self._producer_by_output: dict[str, tuple[MachineDefinition, ProductionOptionDefinition]] = {}
        for definition in self._machines.values():
            for option in definition.available_production_options:
                if option.production_id in self._options:
                    continue
                self._options[option.production_id] = (definition, option)
                self._producer_by_output.setdefault(option.output_resource, (definition, option))
        self._cache: dict[str, ProductionValue] = {}

    def values(self) -> dict[str, ProductionValue]:
        return {
            option.output_resource: self.value_for_option(definition, option)
            for definition, option in self._options.values()
        }

    def value_for_resource(self, resource_id: str) -> ProductionValue | None:
        producer = self._producer_by_output.get(resource_id)
        if producer is None:
            return None
        return self.value_for_option(*producer)

    def value_for_option(
        self,
        definition: MachineDefinition,
        option: ProductionOptionDefinition,
        stack: tuple[str, ...] = (),
    ) -> ProductionValue:
        if option.production_id in self._cache:
            return self._cache[option.production_id]
        if option.production_id in stack:
            cycle = " -> ".join((*stack, option.production_id))
            raise ValueError(f"Production cycle detected: {cycle}")

        output_amount = Fraction(str(option.output_amount_for(definition)))
        cycle_seconds = Fraction(str(option.cycle_seconds_for(definition)))
        output_per_minute = output_amount * Fraction(60) / cycle_seconds
        own_value = Fraction(1) / output_per_minute
        input_value = Fraction(0)
        depth = 0
        base_resources: set[str] = set()
        if not option.input_resources:
            base_resources.add(option.output_resource)

        for resource_id, amount in option.input_resources.items():
            input_value_result = self.value_for_resource(resource_id)
            if input_value_result is None:
                raise ValueError(f"No production value producer for input resource: {resource_id}")
            input_amount_per_unit = Fraction(str(amount)) / output_amount
            input_value += input_amount_per_unit * Fraction(str(input_value_result.value_per_unit))
            depth = max(depth, input_value_result.depth + 1)
            base_resources.update(self._base_resources_for(input_value_result.resource_id, (*stack, option.production_id)))

        result = ProductionValue(
            production_id=option.production_id,
            resource_id=option.output_resource,
            name=option.name,
            machine_name=definition.name,
            value_per_unit=float(own_value + input_value),
            output_per_minute=float(output_per_minute),
            own_value_per_unit=float(own_value),
            direct_input_value_per_unit=float(input_value),
            depth=depth,
            base_resource_count=len(base_resources),
        )
        self._cache[option.production_id] = result
        return result

    def _base_resources_for(self, resource_id: str, stack: tuple[str, ...]) -> set[str]:
        producer = self._producer_by_output.get(resource_id)
        if producer is None:
            return {resource_id}
        _, option = producer
        if not option.input_resources:
            return {option.output_resource}
        bases: set[str] = set()
        for input_id in option.input_resources:
            bases.update(self._base_resources_for(input_id, stack))
        return bases


def production_value_for_resource(
    definitions: dict[str, CardDefinition],
    resource_id: str,
) -> ProductionValue | None:
    return ProductionValueCalculator(definitions).value_for_resource(resource_id)


def contract_required_amount(production_value_budget: float, value_per_unit: float) -> float:
    if production_value_budget <= 0:
        raise ValueError("Contract production value budget must be positive.")
    if value_per_unit <= 0:
        raise ValueError("Production value per unit must be positive.")
    return round_contract_amount(production_value_budget / value_per_unit)


def round_contract_amount(raw_amount: float) -> float:
    if raw_amount <= 1:
        return 1.0
    if raw_amount < 20:
        step = 1.0
    elif raw_amount < 250:
        step = 5.0
    elif raw_amount < 1000:
        step = 10.0
    else:
        step = 100.0
    return max(1.0, round(raw_amount / step) * step)


def eligible_contract_products(
    state: GameState,
    definitions: dict[str, CardDefinition],
    production_value_budget: float,
    *,
    calculator: ProductionValueCalculator | None = None,
) -> tuple[ContractProductOption, ...]:
    calculator = calculator or ProductionValueCalculator(definitions)
    active_production_ids = _active_production_ids(state, definitions)
    options: list[ContractProductOption] = []
    for option in production_options(definitions):
        if not is_production_unlocked(state, option):
            continue
        has_stock = state.resources.get(option.output_resource) is not None and state.resources[option.output_resource].amount > 0
        is_active = option.production_id in active_production_ids
        if not has_stock and not is_active:
            continue
        value = calculator.value_for_resource(option.output_resource)
        if value is None:
            continue
        options.append(
            ContractProductOption(
                resource_id=option.output_resource,
                production_id=option.production_id,
                name=option.name,
                value_per_unit=value.value_per_unit,
                required_amount=contract_required_amount(production_value_budget, value.value_per_unit),
            )
        )
    return tuple(sorted(options, key=lambda item: (item.name, item.resource_id)))


def _active_production_ids(
    state: GameState,
    definitions: dict[str, CardDefinition],
) -> set[str]:
    installed_ids = state.installed_card_ids()
    active: set[str] = set()
    for card_id in installed_ids:
        card = state.cards.get(card_id)
        if card is None:
            continue
        definition = definitions.get(card.definition_id)
        if not isinstance(definition, MachineDefinition):
            continue
        machine_state = state.machine_production.get(card_id)
        if machine_state is None or machine_state.selected_production_id is None:
            continue
        selected_id = machine_state.selected_production_id
        production = definition.production_option(selected_id)
        active.add(production.production_id)
    return active
