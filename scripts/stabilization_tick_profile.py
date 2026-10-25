"""Longer real-engine samples separate short-run timing noise from code cost."""
from dataclasses import replace
from importlib.resources import files
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter, process_time

from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import FactoryHall, HallSlot, MachineProductionState
from production_zero.core.simulation import SimulationEngine
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.main_window import _create_initial_state

definitions = load_card_definitions(files('production_zero.data') / 'game_definitions.json')
resources = load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')
state = _create_initial_state(resources, definitions)
for name in ('cards', 'halls', 'resource_sites', 'energy_plants', 'machine_production'):
    getattr(state, name).clear()
state.warehouse_capacity = 1e15
definitions['energy.solar_array'] = replace(definitions['energy.solar_array'], base_power_output=1e12)
solar = create_card_instance('power', 'energy.solar_array', CardKind.ENERGY, Rarity.COMMON)
state.cards[solar.card_id] = solar
state.energy_plants['power'] = FactoryHall('power', 'Power', 1, slots=[HallSlot(0, solar.card_id)], board_kind='energy')
for index in range(500):
    cid = f'benchmark-{index}'
    state.cards[cid] = create_card_instance(cid, 'machine.extractor', CardKind.MACHINE, Rarity.COMMON)
    state.resource_sites[cid] = FactoryHall(cid, 'Benchmark', 1, slots=[HallSlot(0, cid)], board_kind='resources')
    state.machine_production[cid] = MachineProductionState(cid, 'iron_ore', 'resource.iron_ore')
engine = SimulationEngine(definitions, utc_now=lambda: 1792324800.)
for _ in range(10):
    engine.advance_time(state, 1.)
samples = []
for _ in range(5):
    wall, cpu = perf_counter(), process_time()
    for _ in range(100):
        engine.advance_time(state, 1.)
    samples.append(dict(wall_ms=(perf_counter() - wall) * 10, cpu_ms=(process_time() - cpu) * 10))
result = dict(cards=500, ticks=500, samples=samples, wall_ms=median(s['wall_ms'] for s in samples), cpu_ms=median(s['cpu_ms'] for s in samples))
Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
