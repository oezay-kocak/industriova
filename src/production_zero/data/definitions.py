from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition, ProductionOptionDefinition, RecipeDefinition
from production_zero.core.enums import CardKind, EnergyType, FreightFamily, MachineType
from production_zero.core.resources import ResourceDefinition


def load_card_definitions(path: Path) -> dict[str, CardDefinition]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    definitions: dict[str, CardDefinition] = {}

    for item in raw["cards"]:
        definition = _parse_card_definition(item)
        definitions[definition.definition_id] = definition
        for alias in item.get("aliases", []):
            definitions[alias] = definition

    return definitions


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
            mk_level=int(item["mk_level"]),
            base_output_per_tick=float(item["base_output_per_tick"]),
            base_power_draw=float(item["base_power_draw"]),
            cycle_seconds=float(item.get("cycle_seconds", 3.0)),
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
                    cycle_seconds=(
                        None
                        if "cycle_seconds" not in option
                        else float(option["cycle_seconds"])
                    ),
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
            mk_level=int(item["mk_level"]),
            base_power_output=float(item["base_power_output"]),
            input_resources=dict(item.get("input_resources", {})),
            fuel_resource_id=item.get("fuel_resource_id"),
            fuel_consumption_per_minute=float(item.get("fuel_consumption_per_minute", 0.0)),
            supply_price_cash=(
                None
                if "supply_price_cash" not in item
                else float(item["supply_price_cash"])
            ),
        )
    if kind is CardKind.RECIPE:
        return RecipeDefinition(
            definition_id=item["id"],
            name=item["name"],
            duration_ticks=int(item["duration_ticks"]),
            input_resources=dict(item.get("input_resources", {})),
            output_resources=dict(item.get("output_resources", {})),
            stage=_parse_machine_type(item.get("stage", "processor")),
            icon_key=item.get("icon_key", next(iter(item.get("output_resources", {"recipe": 1})), "recipe")),
            accent_key=item.get("accent_key", next(iter(item.get("output_resources", {"recipe": 1})), "recipe")),
        )
    if kind is CardKind.FREIGHT:
        return FreightDefinition(
            definition_id=item["id"],
            name=item["name"],
            family=FreightFamily(item["family"]),
            class_level=int(item["class_level"]),
            class_label=item["class_label"],
            facility_id=item["facility_id"],
            facility_name=item["facility_name"],
            base_capacity=float(item["base_capacity"]),
            base_transport_time_seconds=float(item["base_transport_time_seconds"]),
        )
    raise ValueError(f"Unsupported card kind: {kind}")


def _parse_machine_type(value: str) -> MachineType:
    legacy = {
        "mining": "extractor",
        "smelting": "processor",
        "assembly": "assembler",
    }
    return MachineType(legacy.get(value, value))
