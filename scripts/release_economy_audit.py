"""Reproducible recipe economics, MK/Rarity, and ten-hall infrastructure audit."""
from __future__ import annotations
from dataclasses import replace
from functools import lru_cache
from importlib.resources import files
import json
from math import ceil
from pathlib import Path
from production_zero.core.cards import create_card_instance
from production_zero.core.definitions import MachineDefinition, EnergyDefinition, FreightDefinition
from production_zero.core.enums import Rarity
from production_zero.core.market import BASE_MARKET_PRICES, LEGACY_BASE_MARKET_PRICES
from production_zero.core.mk_upgrades import mk_factor, mk_upgrade_cost, base_net_profit_per_second, rarity_distribution, upgrade_payback_seconds
from production_zero.core.supply import common_card_price
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.core.storage_upgrades import global_storage_capacity, inventory_storage_upgrade_cost


def run():
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    resources = load_resource_definitions(files("production_zero.data") / "resource_definitions.json")
    options = {p.output_resource: (d, p) for d in definitions.values() if isinstance(d, MachineDefinition) for p in d.available_production_options}
    recipes = []
    for rid, (definition, option) in options.items():
        if not option.input_resources:
            continue
        output = option.output_amount_for(definition)
        duration = option.cycle_seconds_for(definition)
        inputs = sum(BASE_MARKET_PRICES[resource] * amount for resource, amount in option.input_resources.items())
        energy = option.power_draw_for(definition) * duration * LEGACY_BASE_MARKET_PRICES["coal"] * .01
        capital = common_card_price(definition) * duration / 36000
        freight = BASE_MARKET_PRICES[rid] * output * .02
        revenue = BASE_MARKET_PRICES[rid] * output
        recipes.append(dict(product=rid, inputs_value=inputs, revenue=revenue, energy_opportunity_cost=energy, capital_per_cycle=capital, transport_allowance=freight, net_per_second=(revenue - inputs - energy - capital - freight) / duration, price_change_percent=(BASE_MARKET_PRICES[rid] / LEGACY_BASE_MARKET_PRICES[rid] - 1) * 100))
    @lru_cache(None)
    def requirements(rid):
        definition, recipe = options[rid]
        output = recipe.output_amount_for(definition)
        own = recipe.cycle_seconds_for(definition) / output
        machines = {definition.definition_id: own}
        power = recipe.power_draw_for(definition) * own
        raw = {rid: 1.} if not recipe.input_resources else {}
        for inp, amount in recipe.input_resources.items():
            child_machines, child_power, child_raw = requirements(inp)
            ratio = amount / output
            for did, n in child_machines.items():
                machines[did] = machines.get(did, 0.) + n * ratio
            for resource, n in child_raw.items():
                raw[resource] = raw.get(resource, 0.) + n * ratio
            power += child_power * ratio
        return machines, power, raw
    infrastructure = []
    for rid in ("iron", "steel", "nuclear_fuel_assembly", "advanced_aircraft", "quantum_computing_module"):
        machines, power, raw = requirements(rid)
        factory_ids = {"machine.processor", "machine.fabricator", "machine.assembler"}
        factory_need = sum(n for did, n in machines.items() if did in factory_ids)
        target_per_sec = 500 / factory_need
        for level in (1, 20, 50, 99):
            factor = mk_factor(level)
            counts = {did: ceil(n * target_per_sec) for did, n in machines.items()}
            # Round factories up, then scale the true rate down to 500 slots.
            actual_factory_count = sum(n for did, n in counts.items() if did in factory_ids)
            if actual_factory_count > 500:
                target_per_sec *= 500 / actual_factory_count
                counts = {did: ceil(n * target_per_sec) for did, n in machines.items()}
            gross_demand = sum(counts[did] * max(p.power_draw_for(definitions[did]) for p in definitions[did].available_production_options if p.output_resource in options) for did in counts)
            # Conservative family maximum; a second figure uses the actual recipe graph.
            actual_power = power * target_per_sec
            gas_plant = definitions["energy.gas_power_plant"]
            fuel_source = definitions["machine.drilling"]
            fuel_option = next(p for p in fuel_source.available_production_options if p.output_resource == "natural_gas")
            plants = ceil(actual_power / (gas_plant.base_power_output - fuel_option.power_draw_for(fuel_source) / 2))
            gas_drills = ceil(plants / 2)
            sites = sum(ceil((n + (gas_drills if did == "machine.drilling" else 0)) / 30) for did, n in counts.items() if did not in factory_ids)
            if "machine.drilling" not in counts:
                sites += ceil(gas_drills / 30)
            amount = target_per_sec * factor
            freight_lines = ceil(amount / (definitions["freight.ship"].base_capacity / definitions["freight.ship"].base_transport_time_seconds * factor))
            buffer = amount * 120 * (1 + sum(raw.values()))
            storage_level = max(0, ceil((buffer / global_storage_capacity(resources, 0) - 1) / .25))
            infrastructure.append(dict(product=rid, mk=level, factory_halls=10, factory_machines=sum(n for did, n in counts.items() if did in factory_ids), primary_machines={did: n for did, n in counts.items() if did not in factory_ids}, gas_fuel_drills=gas_drills, resource_sites=sites, gas_plants=plants, energy_sites=ceil(plants / 15), power_demand_mw=actual_power * factor, final_units_per_second=amount, seaport_lines=freight_lines, storage_level_for_120s_raw_and_output_buffer=storage_level, maximum_family_power_bound_mw=gross_demand * factor))
    upgrades = []
    for definition in definitions.values():
        card = create_card_instance("economy", definition.definition_id, definition.card_kind, Rarity.COMMON)
        cumulative = 0.
        selected = []
        for level in range(1, 99):
            card = replace(card, mk_level=level)
            cost = mk_upgrade_cost(card, definition)
            cumulative += cost
            if level + 1 in (2, 3, 5, 10, 20, 50, 99):
                selected.append(dict(next_mk=level + 1, cost=cost, cumulative_upgrade_cost=cumulative, incremental_net_payback_seconds=cost / (.25 * base_net_profit_per_second(definition)), family_upper_profit_per_second=base_net_profit_per_second(definition)))
        upgrades.append(dict(machine=definition.definition_id, acquisition_cost=common_card_price(definition), levels=selected))
    report = dict(method="Fixed recipe input/output quantities; input resale opportunity costs, coal-equivalent energy opportunity cost, 10-hour capital allowance and 2% freight allowance. Infrastructure: 500 factory slots and gas power/fuel closure. No Research or Rarity bonus; same MK throughout. Continuous-rate plan, conservative ceilings; not a full idle-time simulation.", recipes=recipes, negative_margin_products=[r["product"] for r in recipes if r["net_per_second"] <= 0], rarity_after_98_upgrades=rarity_distribution(), upgrades=upgrades, infrastructure=infrastructure)
    target = Path("artifacts/industriova-release/economy-audit.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"recipes": len(recipes), "negative_margins": report["negative_margin_products"], "rarity": report["rarity_after_98_upgrades"], "infrastructure_scenarios": len(infrastructure)}))


if __name__ == "__main__":
    run()
