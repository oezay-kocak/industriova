"""Validate economic invariants and publish matched scenario/performance data."""
from pathlib import Path
import json,hashlib
root=Path.cwd();out=root/'artifacts/phase9'
def read(p):return json.loads((out/p).read_text(encoding='utf8'))
jobs=read('postchecks.json');assert len(jobs)==7 and all(r['exit_code']==0 for r in jobs)
frozen=read('final-source-sha256.json');assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in frozen.items())
before=read('consortium-before/consortium-balance-simulation.json')['scenarios'];after=read('consortium-final/consortium-balance-simulation.json')['scenarios']
rows=[]
for b in after:
 a=next(a for a in before if (a['scenario'],a['kind'])==(b['scenario'],b['kind']))
 if b.get('feasible') is not False:
  assert b['completed'] and b['minimum_stock']>=-1e-8 and b['roundtrip_terms_and_contributions'] and b['outbound_after_drain']==0
  assert a['company_metadata']==b['company_metadata']
  assert all(peak<=meta['storage']+1e-6 for peak,meta in zip(b['member_peak_goods'],b['company_metadata']))
  assert sum(r['cash'] for r in b['reward_receipts'].values())<=b['pool_snapshot']['cash']+.01
  assert sum(r['company_xp'] for r in b['reward_receipts'].values())<=b['pool_snapshot']['company_xp']+.01
 rows.append(dict(scenario=b['scenario'],kind=b['kind'],before=a,after=b))
assert len(rows)==26 and sum(r['after'].get('completed',False) for r in rows)==24
(out/'economic-comparison.json').write_text(json.dumps(dict(scenarios=rows,before_completed=21,after_completed=24,after_no_freight_unavailable=2,actual_member_metadata_equal=True,storage_and_snapshot_invariants=True),indent=2),encoding='utf8')
comparison={}
for name in ('results.json','ui-results.json'):
 a=read('performance/before/'+name);b=read('performance/after/'+name)
 for key,x in a['results'].items():
  y=b['results'][key];assert len(x['samples_ms'])==len(y['samples_ms'])==7
  comparison[key]=dict(before=x,after=y,median_change_percent=(y['median_ms']/x['median_ms']-1)*100 if x['median_ms'] else None)
 if name=='results.json':
  assert a['cards']==b['cards']==500 and a['members']==b['members']==10 and a['catalog_products']==b['catalog_products']==353
 else:assert a['global_stored_rows']==b['global_stored_rows']==353 and a['stress_freight_cards']==b['stress_freight_cards']==500
(out/'performance-comparison.json').write_text(json.dumps(comparison,indent=2),encoding='utf8');print('26 scenarios and matched serial performance verified',flush=True)
