"""Exercise real complete production chains within ten fully expanded halls."""
from collections import defaultdict
from dataclasses import replace
from importlib.resources import files
import json
from math import ceil, isfinite
from pathlib import Path
from time import perf_counter
from production_zero.core.cards import create_card_instance
from production_zero.core.definitions import MachineDefinition
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.freight import build_freight_facility, FreightAssignment
from production_zero.core.simulation import SimulationEngine
from production_zero.core.state import GameState, FactoryHall, MachineProductionState
from production_zero.data.definitions import load_card_definitions, load_resource_definitions

FACTORY_IDS = {"machine.processor", "machine.fabricator", "machine.assembler"}


def run():
    definitions = load_card_definitions(files("production_zero.data") / "game_definitions.json")
    options = {p.output_resource: (d, p) for d in definitions.values() if isinstance(d, MachineDefinition) for p in d.available_production_options}
    results = []
    for product in ("iron", "steel", "nuclear_fuel_assembly", "advanced_aircraft", "quantum_computing_module"):
        requirements = defaultdict(float)
        def expand(rid, amount):
            requirements[rid] += amount
            definition, option = options[rid]
            for resource, n in option.input_resources.items():
                expand(resource, amount * n / option.output_amount_for(definition))
        expand(product, 1.)
        from functools import lru_cache
        @lru_cache(None)
        def depth(rid):
            return 1 + max((depth(inp) for inp in options[rid][1].input_resources), default=-1)
        order = sorted(requirements, key=depth, reverse=True)
        final_definition, final_option = options[product]
        final_per_machine = final_option.output_amount_for(final_definition) / final_option.cycle_seconds_for(final_definition)
        def quantized_plan(final_machines):
            demand = defaultdict(float, {product: final_machines * final_per_machine})
            plan = {}
            for rid in order:
                definition, option = options[rid]
                duration = option.cycle_seconds_for(definition)
                per_machine = option.output_amount_for(definition) / duration
                plan[rid] = ceil(demand[rid] / per_machine - 1e-9)
                for resource, amount in option.input_resources.items():
                    demand[resource] += plan[rid] * amount / duration
            return plan
        low, high = 0, 501
        while low + 1 < high:
            candidate = (low + high) // 2
            plan = quantized_plan(candidate)
            needed = sum(n for rid, n in plan.items() if options[rid][0].definition_id in FACTORY_IDS)
            if needed <= 500:
                low = candidate
            else:
                high = candidate
        assert low > 0, "At least one complete production chain must fit in ten halls"
        counts = quantized_plan(low)
        power = sum(counts[rid] * options[rid][1].power_draw_for(options[rid][0]) for rid in counts)
        gas_definition, gas_option = options["natural_gas"]
        plants, fuel_drills = 0, 0
        for _ in range(100):
            plant_count = ceil((power + fuel_drills * gas_option.power_draw_for(gas_definition)) / definitions["energy.gas_power_plant"].base_power_output)
            drill_count = ceil(plant_count / 2)
            if (plant_count, drill_count) == (plants, fuel_drills):
                break
            plants, fuel_drills = plant_count, drill_count
        else:
            raise AssertionError("Energy/fuel closure did not converge")
        for level in (1, 20, 50, 99):
            state = GameState(rng_seed=42)
            state.company.level = 200
            state.production_progress.unlocked_production_ids.update(p.production_id for d, p in options.values())
            state.warehouse_capacity = 1e15
            for rid in options:
                state.ensure_resource(rid).amount = 1e7 if rid != product else 0.
            created = 0
            def place(did, amount, option=None):
                nonlocal created
                definition = definitions[did]
                board = "factory" if did in FACTORY_IDS else "energy" if definition.card_kind is CardKind.ENERGY else "resources"
                units = state.production_units(board)
                for _ in range(amount):
                    unit = next((u for u in units.values() if (board != "resources" or u.specialization == did) and any(s.card_id is None and s.index in u.unlocked_slot_indexes() for s in u.slots)), None)
                    if unit is None:
                        unit_id = f"{board}-{len(units) + 1}"
                        capacity, lines = (10, 5) if board == "factory" else (10, 3) if board == "resources" else (5, 3)
                        unit = FactoryHall(unit_id, unit_id, capacity * lines, board_kind=board, specialization=did if board == "resources" else None, max_lines=lines, max_slots_per_line=capacity, start_unlocked_lines=lines, start_slots_per_line=capacity)
                        units[unit_id] = unit
                    created += 1
                    cid = f"simulation-{created}"
                    state.cards[cid] = replace(create_card_instance(cid, did, definition.card_kind, Rarity.COMMON), mk_level=level)
                    next(s for s in unit.slots if s.card_id is None and s.index in unit.unlocked_slot_indexes()).card_id = cid
                    if option is not None:
                        state.machine_production[cid] = MachineProductionState(cid, option.output_resource, option.production_id)
            # Primary sources precede processing, then assembly; power is advanced first by the engine.
            for rid in sorted(counts, key=lambda resource: (options[resource][0].definition_id in FACTORY_IDS, options[resource][0].definition_id == "machine.assembler", options[resource][0].definition_id == "machine.fabricator", resource)):
                definition, option = options[rid]
                place(definition.definition_id, counts[rid], option)
            place("machine.drilling", fuel_drills, gas_option)
            place("energy.gas_power_plant", plants)
            assert len(state.halls) <= 10
            from production_zero.core.analytics import calculate_resource_flows
            planned = calculate_resource_flows(state, definitions)
            shortages = {rid: flow.net_per_minute for rid, flow in planned.items() if flow.net_per_minute < -1e-6}
            assert not shortages, f"Quantized steady-state input shortage: {shortages}"
            engine = SimulationEngine(definitions, utc_now=lambda: 1792324800.)
            total_output = 0.
            start = perf_counter()
            for _ in range(60):
                totals = engine.advance_time(state, 6.)
                total_output += totals.outputs.get(product, 0.)
                assert totals.gross_power + 1e-6 >= totals.used_power
                assert all(isfinite(stock.amount) and stock.amount >= -1e-8 for stock in state.resources.values())
            assert total_output > 0
            assert state.production_progress.lifetime_produced.get(product, 0.) == total_output
            result = dict(product=product, mk=level, factory_halls=len(state.halls), machines=created, resource_sites=len(state.resource_sites), energy_sites=len(state.energy_plants), gas_plants=plants, gas_drills=fuel_drills, final_output_360s=total_output, missing_input=sum(p.status == "missing_input" for p in state.machine_production.values()), no_power=sum(p.status == "no_power" for p in state.machine_production.values()), seconds=round(perf_counter() - start, 3))
            results.append(result)
            print(json.dumps(result), flush=True)
    Path("artifacts/industriova-release/endgame-simulation.json").write_text(json.dumps({"method": "Real SimulationEngine, 60 six-second steps per scenario; integer recipe counts propagated from actual consumer capacity within 500 factory slots; every planned resource balance verified non-negative, gas power/fuel closure; large seeded input buffers, no sales or Research/Rarity bonuses. This checks operation and scaling, not a start-to-end playthrough.", "results": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run()
