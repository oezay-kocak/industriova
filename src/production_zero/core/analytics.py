from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.definitions import CardDefinition, EnergyDefinition, MachineDefinition
from production_zero.core.state import GameState
from production_zero.core.modifiers import research_multiplier


@dataclass(frozen=True, slots=True)
class ResourceFlow:
    resource_id: str
    produced_per_minute: float = 0.0
    consumed_per_minute: float = 0.0

    @property
    def net_per_minute(self) -> float:
        return self.produced_per_minute - self.consumed_per_minute

    @property
    def has_shortage(self) -> bool:
        return self.consumed_per_minute > self.produced_per_minute


def calculate_resource_flows(state: GameState, definitions: dict[str, CardDefinition]) -> dict[str, ResourceFlow]:
    """Return company-wide configured flow rates for every installed production unit.

    These are planned rates: configured machines and fuel-burning power plants are
    counted even when runtime input, power, or storage conditions temporarily block
    a cycle. Stock remains a separate runtime value.
    """
    mutable: dict[str, dict[str, float]] = {}

    for hall in state.all_production_units():
        for slot in hall.slots:
            if slot.card_id is None:
                continue
            card = state.cards[slot.card_id]
            if card.paused:
                continue
            definition = definitions[card.definition_id]
            if isinstance(definition, EnergyDefinition):
                if definition.requires_fuel and definition.fuel_resource_id is not None:
                    _entry(mutable, definition.fuel_resource_id)["consumed"] += definition.fuel_consumption_per_minute * card.mk_multiplier
                continue
            if not isinstance(definition, MachineDefinition):
                continue
            machine_state = state.machine_production.get(card.card_id)
            if machine_state is None or machine_state.selected_production_id is None:
                continue
            production = definition.production_option(
                machine_state.selected_production_id
            )
            if not definition.is_compatible_with(production):
                continue

            cycles_per_minute = 60.0 / max(0.001, production.cycle_seconds_for(definition)) * research_multiplier(state.research, "production_speed")
            produced = production.output_amount_for(definition) * card.output_multiplier * cycles_per_minute
            _entry(mutable, production.output_resource)["produced"] += produced

            for resource_id, amount in production.input_resources.items():
                _entry(mutable, resource_id)["consumed"] += amount * cycles_per_minute * card.mk_multiplier

    return {
        resource_id: ResourceFlow(
            resource_id=resource_id,
            produced_per_minute=values["produced"],
            consumed_per_minute=values["consumed"],
        )
        for resource_id, values in mutable.items()
    }


def _entry(flows: dict[str, dict[str, float]], resource_id: str) -> dict[str, float]:
    if resource_id not in flows:
        flows[resource_id] = {"produced": 0.0, "consumed": 0.0}
    return flows[resource_id]
