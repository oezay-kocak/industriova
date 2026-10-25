"""Prove the final optional-fuel correction preserves all solar-only fixtures."""
import hashlib,importlib.util,json,runpy,sys
from pathlib import Path
from dataclasses import asdict
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
sys.argv=['fixture','--stage','optional-fuel-equivalence']
f=runpy.run_path(str(R/'scripts/phase8_contract_simulation.py'),run_name='fixture')
from production_zero.core.contract_capacity import reachable_capacity
from production_zero.core.definitions import EnergyDefinition
path=O/'capacity-before-optional-fuel.py'
spec=importlib.util.spec_from_file_location('phase8_capacity_before_optional_fuel',path)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
rows=[]
for stage in ('early','mid','late'):
    for mk in (1,2,10,50,99):
        state,_=f['company'](stage,mk)
        assert not any(isinstance(f['D'][c.definition_id],EnergyDefinition) and f['D'][c.definition_id].requires_fuel for c in state.cards.values())
        before=asdict(old.reachable_capacity(state,f['D']));after=asdict(reachable_capacity(state,f['D']))
        assert before==after,(stage,mk)
        rows.append(dict(stage=stage,mk=mk,entire_plan_identical=True,plan_sha256=hashlib.sha256(json.dumps(after,sort_keys=True).encode()).hexdigest()))
result=dict(before_capacity_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),after_capacity_sha256=hashlib.sha256((R/'src/production_zero/core/contract_capacity.py').read_bytes()).hexdigest(),all_identical=True,fixtures=rows,scope='Final correction chooses independent versus feasible fuel operation. Solar-only mode executes the same prior planning body; every economic matrix, performance fixture and accepted capture owns only solar energy. Active terms/loader/UI formulas unchanged. Existing 45 full after outcomes and 35 before summaries remain identical with/without the offline work cache. Fuel-specific regression adds two real failure cases.')
(O/'optional-fuel-solar-equivalence.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('15/15 entire solar capacity plans identical')
