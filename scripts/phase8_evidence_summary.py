"""Assemble accepted P8 evidence, preserving failed/development runs separately."""
import collections,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf8')
def cases(p):return collections.Counter((t.get('classname'),t.get('name')) for t in ET.parse(p).getroot().iter('testcase'))
old=R/'artifacts/phase7/final-accepted-tests';new=O/'final-regression'
rows=[]
for p in sorted(old.glob('*.xml')):
    previous=cases(p);current=cases(new/p.name)
    rows.append(dict(module=p.name,previous=sum(previous.values()),current=sum(current.values()),missing=list((previous-current).elements())))
tests=read(new/'results.json')
regression=dict(modules=len(tests),tests=sum(r['tests'] for r in tests),passed=sum(r['passed'] for r in tests),failures=sum(r['failures'] for r in tests),errors=sum(r['errors'] for r in tests),skipped=sum(r['skipped'] for r in tests),legacy_modules=len(rows),legacy_cases=sum(r['previous'] for r in rows),legacy_retained=all(not r['missing'] for r in rows),retention=rows)
fuel=read(O/'optional-fuel-solar-equivalence.json')
assert fuel['all_identical'] and len(fuel['fixtures'])==15
assert fuel['after_capacity_sha256']==hashlib.sha256((R/'src/production_zero/core/contract_capacity.py').read_bytes()).hexdigest()
assert regression['legacy_modules']==91 and regression['legacy_cases']==1779
assert regression['legacy_retained'] and regression['passed']==regression['tests'] and not regression['skipped']
write(O/'regression-summary.json',regression)
single={stage:read(O/f'{stage}-matched/contract-balance-simulation.json') for stage in ('before','after')}
group={stage:read(O/f'consortium-{stage}-matched/consortium-balance-simulation.json') for stage in ('before','after')}
assert all(len(data['scenarios'])==45 for data in single.values())
assert all(len(data['scenarios'])==34 for data in group.values())
for data in (*single.values(),*group.values()):
    for row in data['scenarios']:
        if 'minimum_stock' in row:assert row['minimum_stock']>=-1e-8,row
        if 'roundtrip_terms_and_contributions' in row:assert row['roundtrip_terms_and_contributions'],row
        if 'peak_goods' in row:assert row['peak_goods']<=row['storage']+1e-6,row
        if 'member_peak_goods' in row:
            assert all(peak<=meta['storage']+1e-6 for peak,meta in zip(row['member_peak_goods'],row['company_metadata'])),row
assert all(r.get('completed') for r in single['after']['scenarios'])
uncached=read(O/'after-matched/uncached-contract-balance-simulation.json')
assert uncached['scenarios']==single['after']['scenarios'],'Offline immutable-work cache changed actual outcomes'
oracle={ (r['stage'],r['kind'],r['mk']):r for r in single['before']['scenarios']}
partial=[]
for line in (O/'before-matched-interrupted.log').read_text(encoding='utf8').splitlines():
    if not line.startswith('{'):continue
    r=json.loads(line);expected=oracle[(r['stage'],r['kind'],r['mk'])]
    assert all(expected[k]==v for k,v in r.items()),r
    partial.append(r)
equivalence=dict(full_after_scenarios_identical=45,uncached_before_completed_or_censored_summaries_identical=len(partial),immutable_value_proof=single['after']['offline_work_cache_proof'],before_value_proof=single['before']['offline_work_cache_proof'],scope='Only the offline Company-XP work calculator constructor is reused; real transition rules unchanged. Both versions and benchmarks use their actual source. Benchmark asserts the production constructor remains the original class.')
old_group=O/'consortium-before-matched/uncached-consortium-balance-simulation.json'
if old_group.is_file():
    assert read(old_group)['scenarios']==group['before']['scenarios']
    equivalence['full_before_consortium_scenarios_identical']=34
write(O/'offline-cache-equivalence.json',equivalence)
for data in single.values():
    for row in data['scenarios']:
        row['contract_rp_per_hour']=row['rp']*60/row['elapsed_minutes'] if row['completed'] else None
for data in group.values():
    for row in data['scenarios']:
        if row.get('feasible') is False:continue
        minutes=row['elapsed_minutes'];receipts=row['reward_receipts']
        row['receipt_xp_per_minute']=sum(r['company_xp'] for r in receipts.values())/minutes if row['completed'] else None
        row['receipt_rp_per_hour']=sum(r['research_points'] for r in receipts.values())*60/minutes if row['completed'] else None
        row['freight_continuous_minimum_minutes']=sum(row['requirements'].values())/sum(row['member_freight_per_minute']) if sum(row['member_freight_per_minute'])>0 else None
        rates={rid:sum(values.get(rid,0) for values in row['reference_member_production_rates'].values()) for rid in row['requirements']}
        row['serial_reference_production_plan_minutes']=sum(q/rates[rid] for rid,q in row['requirements'].items()) if all(rates.values()) else None
        row['member_reward_rates']={cid:dict(cash_per_minute=r['cash']/minutes,xp_per_minute=r['company_xp']/minutes,rp_per_hour=r['research_points']*60/minutes) for cid,r in receipts.items()}
write(O/'contract-balance-simulation.json',dict(single_player=single,consortium=group,source_hashes='final-source-sha256.json',final_optional_fuel_equivalence='optional-fuel-solar-equivalence.json',semantic_provenance='The final fuel-only edge correction preserves the complete planning body for every solar-only matrix/capture fixture; all final source passes the full 1869-case regression. Individual run fingerprints retain their actual source at execution.',baseline='before-tree; complete P7 working-tree backup',development_runs='Other candidate, final, reproduced and consortium-final folders are diagnostic history, not the accepted matched comparison.'))
before=read(O/'performance/before-matched/results.json');after=read(O/'performance/after-matched/results.json')
performance=[]
for name,b in before['results'].items():
    a=after['results'][name]
    performance.append(dict(operation=name,before_ms=b['median_ms'],after_ms=a['median_ms'],change_percent=(a['median_ms']/b['median_ms']-1)*100,before_max_ms=b['max_ms'],after_max_ms=a['max_ms']))
write(O/'performance/comparison.json',dict(results=performance,raw_before='before-matched/results.json',raw_after='after-matched/results.json',assumptions=after['assumptions']))
research=read(R/'src/production_zero/data/research_definitions.json')
nodes=research['nodes'];specialization=research['specialization']
write(O/'progression-summary.json',dict(nodes=len(nodes),node_rp_total=sum(n['cost'] for n in nodes),specialization_slots=len(specialization['slots']),specialization_rp_total=sum(n['cost'] for n in specialization['slots']),assumptions='Mutually exclusive specialization choices and prerequisites remain authoritative. This total describes the catalog budget, not an organically achievable all-tree loadout.',scenarios=[dict(stage=r['stage'],mk=r['mk'],kind=r['kind'],minutes=r['elapsed_minutes'],xp=r['xp'],xp_per_hour=r['xp_per_minute']*60 if r['xp_per_minute'] is not None else None,xp_share_next_level=r['xp_share_next_level'],contract_rp=r['rp'],levelup_rp=r['levelup_rp'],contract_rp_per_hour=r['rp']*60/r['elapsed_minutes'],total_earned_rp=r['total_rp_after']) for r in single['after']['scenarios']]))
print(json.dumps({k:v for k,v in regression.items() if k!='retention'},indent=2))
