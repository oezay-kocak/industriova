"""Additional engine test of admissible player pause/resume, no game feature."""
from pathlib import Path
import ast,json,csv,sys
root=Path.cwd();sys.path.insert(0,str(root/'src'))
source=(root/'scripts/phase11c_economy.py').read_text(encoding='utf8')
exec(compile(source.split('BUDGETS=')[0],'phase11c catalog-only prefix','exec'))
module=ast.parse(source);function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='build_state')
exec(compile(ast.Module(body=[function],type_ignores=[]),'phase11c build_state','exec'))
from phase8_offline_work_cache import install
install(D)
from production_zero.core.simulation import SimulationEngine
from production_zero.core.commands import PauseMachines
engine=SimulationEngine(D,utc_now=lambda:datetime(2026,10,23,12,tzinfo=timezone.utc))
results=[]
for rid in ('biodiesel','microchip','industrial_equipment','ai_server'):
 plan=layout(rid,1.,1);s=build_state(plan)
 thresholds=defaultdict(float);cards=defaultdict(list)
 for cid,production in s.machine_production.items():
  cards[production.target_resource_id].append(cid)
  d,o=P[production.target_resource_id]
  for x,a in o.input_resources.items():thresholds[x]+=a*s.cards[cid].mk_multiplier
 for x in thresholds:thresholds[x]=max(thresholds[x]*3,float(META[x]['output_units_per_cycle'])*3)
 for second in range(1,7201):
  for x,ids in cards.items():
   if x==rid:continue
   pause=s.ensure_resource(x).amount>=thresholds[x]
   if any(s.cards[c].paused!=pause for c in ids):PauseMachines(tuple(ids),pause).apply(s)
  engine.advance_time(s,1)
  if second in (600,1800,3600,7200):
   units=s.statistics.total_earnings/A[rid]
   for model,prices in MODELS.items():results.append(dict(product_id=rid,model=model,seconds=second,delivered_units=units,cash=units*prices[rid],investment=plan['cost'],nominal_target_units_min=1,actual_units_min=units/(second/60),remaining_stock=s.used_storage,conditions='Existing PauseMachines every second; target three input batches; mature earned unlocks, zero initial stock; identical physical arrivals revalued exactly at each fixed shadow price'))
 print('controlled',rid,flush=True)
write_csv(OUT/'controlled-engine.csv',results)
