"""Audit every canonical production edge and each machine tier from runtime data."""
import json
from fractions import Fraction
from pathlib import Path

from production_zero.core.definitions import MachineDefinition
from production_zero.core.economic_cycle import ECONOMIC_CYCLE_SECONDS
from production_zero.core.production_guide import ProductionGuideRecipeIndex
from production_zero.data.definitions import load_card_definitions


def main():
    definitions = load_card_definitions(Path('src/production_zero/data/game_definitions.json'))
    index = ProductionGuideRecipeIndex(definitions)
    machines = {d.definition_id: d for d in definitions.values() if isinstance(d, MachineDefinition)}
    outputs = {o.output_resource for d in machines.values() for o in d.available_production_options}
    edges = []
    for rid in sorted(outputs):
        entry = index.produced_by(rid)[0]
        for input_id, amount in entry.production.input_resources.items():
            upstream = index.produced_by(input_id)[0]
            ratio = Fraction(str(upstream.output_amount)) / Fraction(str(amount))
            simple = ((min(ratio.numerator, ratio.denominator) == 1 and max(ratio.numerator, ratio.denominator) <= 12)
                      or max(ratio.numerator, ratio.denominator) <= 5)
            edges.append({'upstream': input_id, 'downstream': rid,
                          'upstream_output': upstream.output_amount, 'downstream_input': amount,
                          'downstream_machines_per_upstream': str(ratio), 'simple': simple})
    tiers = {key: {'recipes': len(d.available_production_options),
                   'cycles': sorted({o.cycle_seconds_for(d) for o in d.available_production_options})}
             for key, d in machines.items()}
    assert all(t['cycles'] == [ECONOMIC_CYCLE_SECONDS] for t in tiers.values())
    assert all(e['simple'] for e in edges)
    result = {'cycle_seconds': ECONOMIC_CYCLE_SECONDS, 'products': len(outputs),
              'adjacent_edges': len(edges), 'awkward_base_ratios': 0, 'tiers': tiers, 'edges': edges}
    target = Path('artifacts/playtest/economy-audit.json')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(outputs)} products, {len(edges)} edges, {len(tiers)} machine tiers: all cycles and base ratios pass.')


if __name__ == '__main__':
    main()
