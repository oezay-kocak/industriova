from __future__ import annotations

from dataclasses import dataclass

from production_zero.core.definitions import CardDefinition, MachineDefinition
from production_zero.core.state import GameState


ACTIVE_MACHINE_STATUSES = {"running", "idle"}


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
    mutable: dict[str, dict[str, float]] = {}

    for hall in state.halls.values():
        for slot in hall.slots:
            if slot.card_id is None:
                continue
            card = state.cards[slot.card_id]
            definition = definitions[card.definition_id]
            if not isinstance(definition, MachineDefinition):
                continue
            machine_state = state.machine_production.get(card.card_id)
            if machine_state is not None and machine_state.status not in ACTIVE_MACHINE_STATUSES:
                continue
            if machine_state is None or machine_state.selected_production_id is None:
                continue
            production = definition.production_option(
                machine_state.selected_production_id
            )
            if not definition.is_compatible_with(production):
                continue

            cycles_per_minute = 60.0 / max(0.001, production.cycle_seconds_for(definition))
            produced = production.output_amount_for(definition) * card.output_multiplier * cycles_per_minute
            _entry(mutable, production.output_resource)["produced"] += produced

            for resource_id, amount in production.input_resources.items():
                _entry(mutable, resource_id)["consumed"] += amount * cycles_per_minute

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
