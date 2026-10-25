from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from production_zero.core.definitions import CardDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.enums import MachineType


_STAGE_ORDER = {
    MachineType.EXTRACTOR: 0,
    MachineType.DRILLING: 0,
    MachineType.AGRICULTURE: 0,
    MachineType.PROCESSOR: 1,
    MachineType.FABRICATOR: 2,
    MachineType.ASSEMBLER: 3,
}


@dataclass(frozen=True, slots=True)
class GuideRecipeEntry:
    production: ProductionOptionDefinition
    machine_definition_id: str
    machine_name: str
    output_amount: float
    cycle_seconds: float
    power_draw: float

    @property
    def output_per_minute(self) -> float:
        if self.cycle_seconds <= 0:
            return 0.0
        return self.output_amount * 60.0 / self.cycle_seconds

    def input_per_minute(self, resource_id: str) -> float:
        if self.cycle_seconds <= 0:
            return 0.0
        return self.production.input_resources.get(resource_id, 0.0) * 60.0 / self.cycle_seconds


class ProductionGuideRecipeIndex:
    """Runtime recipe lookup derived from machine production definitions."""

    def __init__(self, definitions: Mapping[str, CardDefinition]) -> None:
        produced_by: dict[str, list[GuideRecipeEntry]] = {}
        used_in: dict[str, list[GuideRecipeEntry]] = {}
        production_entries: dict[str, GuideRecipeEntry] = {}
        for definition in definitions.values():
            if not isinstance(definition, MachineDefinition):
                continue
            for option in definition.available_production_options:
                entry = GuideRecipeEntry(
                    production=option,
                    machine_definition_id=definition.definition_id,
                    machine_name=definition.name,
                    output_amount=option.output_amount_for(definition),
                    cycle_seconds=option.cycle_seconds_for(definition),
                    power_draw=option.power_draw_for(definition),
                )
                existing = production_entries.get(option.production_id)
                if existing is None:
                    production_entries[option.production_id] = entry
                    produced_by.setdefault(option.output_resource, []).append(entry)
                    for input_resource_id in option.input_resources:
                        used_in.setdefault(input_resource_id, []).append(entry)

        self._produced_by = {
            resource_id: tuple(sorted(entries, key=_entry_sort_key))
            for resource_id, entries in produced_by.items()
        }
        self._used_in = {
            resource_id: tuple(sorted(entries, key=_entry_sort_key))
            for resource_id, entries in used_in.items()
        }

    def produced_by(self, resource_id: str) -> tuple[GuideRecipeEntry, ...]:
        return self._produced_by.get(resource_id, ())

    def used_in(self, resource_id: str) -> tuple[GuideRecipeEntry, ...]:
        return self._used_in.get(resource_id, ())


def _entry_sort_key(entry: GuideRecipeEntry) -> tuple[int, str, str]:
    return (_STAGE_ORDER.get(entry.production.stage, 99), entry.production.name, entry.production.production_id)
