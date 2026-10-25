"""Infrastructure throughput rules derived from the existing recipe graph."""
from dataclasses import replace
from functools import lru_cache
from production_zero.core.definitions import MachineDefinition, EnergyDefinition, FreightDefinition

FREIGHT_TIERS = {
    "freight.truck": (40., 60.),
    "freight.train": (400., 120.),
    "freight.aircraft": (4000., 180.),
    "freight.ship": (16000., 240.),
}


def balance_definitions(definitions):
    options = {option.output_resource: (definition, option) for definition in definitions.values() if isinstance(definition, MachineDefinition) for option in definition.available_production_options}
    @lru_cache(None)
    def raw_units(resource_id, primary_id):
        if resource_id == primary_id:
            return 1.
        entry = options.get(resource_id)
        if entry is None:
            return 0.
        definition, option = entry
        return sum(amount * raw_units(rid, primary_id) for rid, amount in option.input_resources.items()) / option.output_amount_for(definition)
    for did, definition in tuple(definitions.items()):
        if isinstance(definition, FreightDefinition) and did in FREIGHT_TIERS:
            capacity, seconds = FREIGHT_TIERS[did]
            definitions[did] = replace(definition, base_capacity=capacity, base_transport_time_seconds=seconds,
                                       supply_price_cash=14955.0 if did=='freight.ship' else definition.supply_price_cash)
        elif isinstance(definition, EnergyDefinition) and definition.fuel_resource_id:
            primary = "uranium_ore" if definition.fuel_resource_id == "nuclear_fuel_assembly" else definition.fuel_resource_id
            entry = options.get(primary)
            if entry:
                source, option = entry
                per_minute = option.output_amount_for(source) * 60 / option.cycle_seconds_for(source)
                raw_per_fuel = raw_units(definition.fuel_resource_id, primary)
                if raw_per_fuel > 0:
                    definitions[did] = replace(definition, fuel_consumption_per_minute=per_minute / (2 * raw_per_fuel))
