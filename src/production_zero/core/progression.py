from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files
from typing import TYPE_CHECKING, Iterable

from production_zero.core.definitions import CardDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.enums import MachineType

if TYPE_CHECKING:
    from production_zero.core.state import GameState


PROGRESSION_SCHEMA_VERSION = 3
PRODUCTION_UNLOCK_BASE_THRESHOLDS = {
    MachineType.PROCESSOR: 100.0,
    MachineType.FABRICATOR: 100.0,
    MachineType.ASSEMBLER: 100.0,
}


@dataclass(frozen=True, slots=True)
class ProductionUnlockRequirement:
    resource_id: str
    quantity: float


@dataclass(slots=True)
class ProductionProgress:
    schema_version: int = PROGRESSION_SCHEMA_VERSION
    lifetime_produced: dict[str, float] = field(default_factory=dict)
    unlocked_production_ids: set[str] = field(default_factory=set)
    pending_unlock_ids: list[str] = field(default_factory=list)
    first_produced_resource_ids: set[str] = field(default_factory=set)
    mastered_family_ids: set[str] = field(default_factory=set)


@lru_cache(maxsize=1)
def progression_plan() -> dict[str, object]:
    path = files("production_zero.data") / "resource_progression.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def progression_families() -> tuple[dict[str, object], ...]:
    return tuple(progression_plan()["families"])


def progression_resources() -> dict[str, dict[str, object]]:
    return progression_plan()["resources"]


def initial_production_ids() -> set[str]:
    return {
        str(entry["production_id"])
        for entry in progression_resources().values()
        if entry["stage"] == MachineType.EXTRACTOR.value
    }


def initialize_production_progress(
    state: "GameState",
    definitions: dict[str, CardDefinition],
    *,
    migrate_existing: bool = False,
) -> tuple[str, ...]:
    if migrate_existing:
        migrate_production_progress(state, definitions, legacy_without_progress=True)
        return ()
    state.production_progress.schema_version = PROGRESSION_SCHEMA_VERSION
    return update_production_unlocks(state, definitions, emit_pending=False)


def migrate_production_progress(
    state: "GameState",
    definitions: dict[str, CardDefinition],
    *,
    legacy_without_progress: bool = False,
) -> tuple[str, ...]:
    progress = state.production_progress
    grandfathered = set(progress.unlocked_production_ids)
    grandfathered.update(
        machine.selected_production_id
        for machine in state.machine_production.values()
        if machine.selected_production_id
    )
    grandfathered.update(
        str(entry["production_id"])
        for resource_id, entry in progression_resources().items()
        if progress.lifetime_produced.get(resource_id, 0.0) > 0
    )
    if legacy_without_progress:
        for resource_id, stock in state.resources.items():
            if stock.amount > 0:
                progress.lifetime_produced[resource_id] = max(
                    progress.lifetime_produced.get(resource_id, 0.0), stock.amount
                )
        grandfathered.update(
            str(entry["production_id"])
            for resource_id, entry in progression_resources().items()
            if progress.lifetime_produced.get(resource_id, 0.0) > 0
        )
    progress.unlocked_production_ids.update(grandfathered)
    progress.first_produced_resource_ids.update(
        resource_id for resource_id, amount in progress.lifetime_produced.items() if amount > 0
    )
    progress.schema_version = PROGRESSION_SCHEMA_VERSION
    update_production_unlocks(state, definitions, emit_pending=False)
    normalize_family_mastery(state)
    progress.pending_unlock_ids.clear()
    return tuple(sorted(grandfathered))


def record_lifetime_production(
    state: "GameState",
    produced: dict[str, float],
    definitions: dict[str, CardDefinition],
) -> tuple[str, ...]:
    for resource_id, amount in produced.items():
        if amount > 0:
            state.production_progress.lifetime_produced[resource_id] = (
                state.production_progress.lifetime_produced.get(resource_id, 0.0) + amount
            )
    return update_production_unlocks(state, definitions)


def update_production_unlocks(
    state: "GameState",
    definitions: dict[str, CardDefinition],
    *,
    emit_pending: bool = True,
) -> tuple[str, ...]:
    earned: list[str] = []
    options = production_options(definitions)
    # One synchronous pass owns the unlock mutations. Build this projection
    # once and update it with each earned recipe instead of rebuilding all 353
    # entries for every candidate on every second of offline catchup.
    unlocked_outputs = set(_unlocked_output_resources(state))
    changed = True
    while changed:
        changed = False
        for option in options:
            if option.production_id in state.production_progress.unlocked_production_ids:
                continue
            if _option_requirements_met(state, option, unlocked_outputs):
                state.production_progress.unlocked_production_ids.add(option.production_id)
                unlocked_outputs.add(option.output_resource)
                earned.append(option.production_id)
                changed = True
    if emit_pending:
        state.production_progress.pending_unlock_ids.extend(earned)
    return tuple(earned)


def production_options(definitions: dict[str, CardDefinition]) -> tuple[ProductionOptionDefinition, ...]:
    options: dict[str, ProductionOptionDefinition] = {}
    for definition in definitions.values():
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                options.setdefault(option.production_id, option)
    return tuple(options.values())


def production_options_for_machine(
    state: "GameState", definition: MachineDefinition
) -> tuple[ProductionOptionDefinition, ...]:
    return tuple(option for option in definition.available_production_options if is_production_unlocked(state, option))


def production_option_for_id(
    definitions: dict[str, CardDefinition], production_id: str
) -> ProductionOptionDefinition | None:
    for option in production_options(definitions):
        if option.production_id == production_id or production_id in option.aliases:
            return option
    return None


def is_production_unlocked(state: "GameState", option: ProductionOptionDefinition) -> bool:
    return option.production_id in state.production_progress.unlocked_production_ids


def unlock_requirements_for(option: ProductionOptionDefinition) -> tuple[ProductionUnlockRequirement, ...]:
    if not option.input_resources:
        return ()
    threshold = PRODUCTION_UNLOCK_BASE_THRESHOLDS[option.stage]
    return tuple(ProductionUnlockRequirement(resource_id, threshold) for resource_id in option.input_resources)


def production_progress_state(state: "GameState", option: ProductionOptionDefinition) -> str:
    if is_production_unlocked(state, option):
        return "unlocked"
    requirements = unlock_requirements_for(option)
    return "next" if not requirements or _requirements_visible(state, requirements) else "later"


def unlock_requirement_lines(
    state: "GameState",
    option: ProductionOptionDefinition,
    resource_names: dict[str, str] | None = None,
    *,
    unlocked_outputs: set[str] | None = None,
) -> tuple[str, ...]:
    entry = progression_resources()[option.output_resource]
    lines: list[str] = []
    names = resource_names or {}
    if unlocked_outputs is None:
        unlocked_outputs = _unlocked_output_resources(state)
    for requirement in unlock_requirements_for(option):
        name = names.get(requirement.resource_id, requirement.resource_id.replace("_", " ").title())
        produced = state.production_progress.lifetime_produced.get(requirement.resource_id, 0.0)
        if requirement.resource_id not in unlocked_outputs:
            lines.append(f"REQUIRES UNLOCKED INPUT: {name.upper()}")
        elif produced < requirement.quantity:
            remaining = requirement.quantity - produced
            lines.append(f"PRODUCE {remaining:g} MORE {name.upper()} ({produced:g} / {requirement.quantity:g})")
    if option.output_resource in state.production_progress.first_produced_resource_ids:
        lines.append("FIRST PRODUCTION COMPLETE")
    if option.stage is MachineType.EXTRACTOR:
        family_id = str(entry["family_id"])
        current, target = family_mastery_progress(state, family_id)
        if family_id in state.production_progress.mastered_family_ids:
            lines.append("FAMILY MASTERY COMPLETE")
        else:
            lines.append(f"FAMILY MASTERY {current:g} / {target:g}")
    return tuple(lines)


def compact_unlock_requirement_lines(lines: tuple[str, ...], maximum: int = 2) -> tuple[str, ...]:
    if len(lines) <= maximum:
        return lines
    return (*lines[:maximum], f"+{len(lines) - maximum} MORE REQUIREMENTS")


def family_names_for_entry(entry: dict[str, object]) -> tuple[str, ...]:
    by_id = {str(family["id"]): str(family["name"]) for family in progression_families()}
    return tuple(by_id[str(family_id)] for family_id in entry["extractor_family_ids"])


def family_mastery_progress(state: "GameState", family_id: str) -> tuple[float, float]:
    family = next(item for item in progression_families() if item["id"] == family_id)
    roots = tuple(str(resource_id) for resource_id in family["resources"])
    current = sum(min(120.0, state.production_progress.lifetime_produced.get(root, 0.0)) for root in roots)
    return current, 120.0 * len(roots)


def newly_mastered_families(state: "GameState") -> tuple[str, ...]:
    mastered = []
    for family in progression_families():
        family_id = str(family["id"])
        if family_id in state.production_progress.mastered_family_ids:
            continue
        if all(
            state.production_progress.lifetime_produced.get(str(root), 0.0) >= 120.0
            for root in family["resources"]
        ):
            mastered.append(family_id)
    return tuple(mastered)


def normalize_family_mastery(state: "GameState") -> None:
    state.production_progress.mastered_family_ids.update(newly_mastered_families(state))


def _option_requirements_met(state: "GameState", option: ProductionOptionDefinition, unlocked_outputs=None) -> bool:
    entry = progression_resources().get(option.output_resource)
    if entry is None:
        return False
    if not option.input_resources:
        return True
    if unlocked_outputs is None:
        unlocked_outputs = _unlocked_output_resources(state)
    # All branches now participate from level 1. Check the static input keys
    # directly instead of allocating requirement objects on every simulation tick.
    threshold = PRODUCTION_UNLOCK_BASE_THRESHOLDS[option.stage]
    return all(
        resource_id in unlocked_outputs
        and state.production_progress.lifetime_produced.get(resource_id, 0.0) >= threshold
        for resource_id in option.input_resources
    )


def _requirements_visible(state: "GameState", requirements: Iterable[ProductionUnlockRequirement]) -> bool:
    unlocked_outputs = _unlocked_output_resources(state)
    return all(requirement.resource_id in unlocked_outputs for requirement in requirements)


def _unlocked_output_resources(state: "GameState") -> set[str]:
    production_to_resource = {
        str(entry["production_id"]): resource_id for resource_id, entry in progression_resources().items()
    }
    return {
        production_to_resource[production_id]
        for production_id in state.production_progress.unlocked_production_ids
        if production_id in production_to_resource
    }
