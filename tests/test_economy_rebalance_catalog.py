from pathlib import Path
from importlib.resources import files
from fractions import Fraction
import json
import pytest
from production_zero.core.market import BASE_MARKET_PRICES
from production_zero.core.definitions import MachineDefinition
from production_zero.core.fixed_prices import build_fixed_prices
from production_zero.data.definitions import load_card_definitions

REF=json.loads((Path(__file__).parent/'fixtures/economy-n1-c2.json').read_text())
DEFS=load_card_definitions(files('production_zero.data')/'game_definitions.json')
RECIPES={o.output_resource:(d,o) for d in DEFS.values() if isinstance(d,MachineDefinition) for o in d.available_production_options}

@pytest.mark.parametrize('rid',tuple(REF))
def test_all_353_c2_prices_match_approved_p11e(rid):
    assert BASE_MARKET_PRICES[rid]==pytest.approx(REF[rid]['price'],rel=1e-12,abs=1e-12)
    d,o=RECIPES[rid];q=o.output_amount_for(d);seconds=o.cycle_seconds_for(d)
    expected=sum(a*BASE_MARKET_PRICES[x] for x,a in o.input_resources.items())/q
    if o.input_resources:expected+={'processor':120,'fabricator':40,'assembler':120}[d.machine_type.value]*seconds/(60*q)
    else:expected=1.
    assert BASE_MARKET_PRICES[rid]==pytest.approx(expected,rel=1e-12)

@pytest.mark.parametrize('rid',tuple(REF))
def test_exact_n1_recipe_and_unchanged_yield_identity_timing_power(rid):
    old,new=REF[rid]['old'],REF[rid]['new'];d,o=RECIPES[rid]
    assert dict(o.input_resources)==new['inputs']
    assert o.output_amount_for(d)==new['output']
    assert o.cycle_seconds_for(d)==old['seconds']==new['seconds']
    assert o.power_draw_for(d)==old['power']==new['power']
    assert set(old['inputs'])==set(new['inputs'])
    for x in old['inputs']:
        assert Fraction(str(old['inputs'][x]))/Fraction(str(old['output']))==Fraction(str(new['inputs'][x]))/Fraction(str(new['output']))

def test_catalog_graph_counts_and_old_anchors_are_irrelevant():
    assert len(RECIPES)==len(REF)==353
    assert sum(bool(o.input_resources) for d,o in RECIPES.values())==304
    assert sum(len(o.input_resources) for d,o in RECIPES.values())==708
    assert sum(v['old']!=v['new'] for v in REF.values())==178
    assert build_fixed_prices({r:1e99 for r in REF})==BASE_MARKET_PRICES
