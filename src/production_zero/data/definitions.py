from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, ProductionOptionDefinition
from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.enums import CardKind, EnergyType, FreightFamily, MachineType
from production_zero.core.resources import ResourceDefinition


LEGACY_CARD_FAMILY_IDS = {
    "machine.mining_drill": "machine.extractor",
    "machine.furnace": "machine.processor",
    "machine.blast_furnace": "machine.processor",
}

DRILLING_PRIMARY_RESOURCES = frozenset({"crude_oil", "natural_gas"})
AGRICULTURE_PRIMARY_RESOURCES = frozenset({
    "timber", "wheat", "corn", "soybeans", "sugarcane", "cotton",
    "rapeseed", "potatoes", "fruit", "natural_rubber",
})


def normalize_legacy_card_definition_id(definition_id: str) -> str:
    """Collapse legacy MK/Class definition ids to their permanent family id."""
    import re
    definition_id = re.sub(r"\.(?:mk|class)\d+$", "", definition_id, flags=re.IGNORECASE)
    return LEGACY_CARD_FAMILY_IDS.get(definition_id, definition_id)


def load_card_definitions(path: Path) -> dict[str, CardDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    definitions: dict[str, CardDefinition] = {}

    for item in raw["cards"]:
        if item.get("kind") == "recipe":  # Ignore retired cards in older data files.
            continue
        definition = _parse_card_definition(item)
        definitions[definition.definition_id] = definition
        for alias in item.get("aliases", []):
            definitions[alias] = definition

    _split_primary_production_families(definitions)
    from production_zero.core.release_balance import balance_definitions
    balance_definitions(definitions)

    return definitions


def primary_machine_type_for_resource(resource_id: str) -> MachineType:
    if resource_id in DRILLING_PRIMARY_RESOURCES:
        return MachineType.DRILLING
    if resource_id in AGRICULTURE_PRIMARY_RESOURCES:
        return MachineType.AGRICULTURE
    return MachineType.EXTRACTOR


def _split_primary_production_families(definitions: dict[str, CardDefinition]) -> None:
    original = definitions.get("machine.extractor")
    if not isinstance(original, MachineDefinition):
        return
    grouped: dict[MachineType, list[ProductionOptionDefinition]] = {
        MachineType.EXTRACTOR: [],
        MachineType.DRILLING: [],
        MachineType.AGRICULTURE: [],
    }
    for option in original.production_options:
        family = primary_machine_type_for_resource(option.output_resource)
        grouped[family].append(replace(option, stage=family))
    definitions["machine.extractor"] = replace(
        original,
        name="Extractor",
        machine_type=MachineType.EXTRACTOR,
        stage=MachineType.EXTRACTOR,
        production_options=tuple(grouped[MachineType.EXTRACTOR]),
    )
    definitions["machine.drilling"] = replace(
        original,
        definition_id="machine.drilling",
        name="Drilling Rig",
        machine_type=MachineType.DRILLING,
        stage=MachineType.DRILLING,
        production_options=tuple(grouped[MachineType.DRILLING]),
        icon_key="crude_oil",
        accent_key="crude_oil",
    )
    definitions["machine.agriculture"] = replace(
        original,
        definition_id="machine.agriculture",
        name="Harvester",
        machine_type=MachineType.AGRICULTURE,
        stage=MachineType.AGRICULTURE,
        production_options=tuple(grouped[MachineType.AGRICULTURE]),
        icon_key="wheat",
        accent_key="wheat",
    )


def load_resource_definitions(path: Path) -> dict[str, ResourceDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        item["id"]: ResourceDefinition(
            resource_id=item["id"],
            name=item["name"],
            default_capacity=float(item["default_capacity"]),
            icon_key=item.get("icon_key", item["id"]),
            accent_key=item.get("accent_key", item["id"]),
            category=item.get("category", ""),
        )
        for item in raw["resources"]
    }


def _parse_card_definition(item: dict[str, Any]) -> CardDefinition:
    kind = CardKind(item["kind"])
    if kind is CardKind.MACHINE:
        return MachineDefinition(
            definition_id=item["id"],
            name=item["name"],
            machine_type=_parse_machine_type(item["machine_type"]),
            base_output_per_tick=float(item["base_output_per_tick"]),
            base_power_draw=float(item["base_power_draw"]),
            cycle_seconds=ECONOMIC_CYCLE_SECONDS,
            input_resources=dict(item.get("input_resources", {})),
            output_resource=item["output_resource"],
            production_options=tuple(
                ProductionOptionDefinition(
                    production_id=option["id"],
                    name=option["name"],
                    input_resources=dict(option.get("input_resources", item.get("input_resources", {}))),
                    output_resource=option["output_resource"],
                    stage=_parse_machine_type(option.get("stage", item["machine_type"])),
                    icon_key=option.get("icon_key", option["output_resource"]),
                    accent_key=option.get("accent_key", option["output_resource"]),
                    output_amount=(
                        None
                        if "output_amount" not in option
                        else float(option["output_amount"])
                    ),
                    cycle_seconds=ECONOMIC_CYCLE_SECONDS,
                    power_draw=(
                        None
                        if "power_draw" not in option
                        else float(option["power_draw"])
                    ),
                    aliases=tuple(option.get("aliases", [])),
                )
                for option in item.get("production_options", [])
            ),
            stage=_parse_machine_type(item.get("stage", item["machine_type"])),
            icon_key=item.get("icon_key", item["output_resource"]),
            accent_key=item.get("accent_key", item["output_resource"]),
            alias_default_productions=dict(item.get("alias_default_productions", {})),
        )
    if kind is CardKind.ENERGY:
        return EnergyDefinition(
            definition_id=item["id"],
            name=item["name"],
            energy_type=EnergyType(item["energy_type"]),
            base_power_output=float(item["base_power_output"]),
            input_resources=dict(item.get("input_resources", {})),
            fuel_resource_id=item.get("fuel_resource_id"),
            fuel_consumption_per_minute=float(item.get("fuel_consumption_per_cycle", 0.0)) * 60.0 / ECONOMIC_CYCLE_SECONDS if "fuel_consumption_per_cycle" in item else float(item.get("fuel_consumption_per_minute", 0.0)),
            supply_price_cash=(
                None
                if "supply_price_cash" not in item
                else float(item["supply_price_cash"])
            ),
        )
    if kind is CardKind.FREIGHT:
        return FreightDefinition(
            definition_id=item["id"],
            name=item["name"],
            family=FreightFamily(item["family"]),
            facility_id=item["facility_id"],
            facility_name=item["facility_name"],
            base_capacity=float(item["base_capacity"]),
            base_transport_time_seconds=float(item["base_transport_time_seconds"]),
            supply_price_cash=float(item['supply_price_cash']) if item.get('supply_price_cash') is not None else None,
        )
    raise ValueError(f"Unsupported card kind: {kind}")


def _parse_machine_type(value: str) -> MachineType:
    legacy = {
        "mining": "extractor",
        "smelting": "processor",
        "assembly": "assembler",
    }
    return MachineType(legacy.get(value, value))
