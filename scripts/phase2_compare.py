"""Aggregate raw P2 repeats without treating small samples as a p95 estimate."""
import json,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase2'
def stats(values):
    return dict(n=len(values),median_ms=statistics.median(values),max_ms=max(values)) if values else None
def read(path):return json.loads(path.read_text(encoding='utf8'))
result={}
for stage in ('before','after'):
    target=result[stage]={}
    for kind,name in (('ui','ui-baseline'),('actions','actions-baseline'),('rapid','rapid-ui-baseline')):
        records=[read(p) for p in sorted((OUT/stage/kind).glob(f'run-*/{name}.json'))]
        labels=sorted({k for r in records for k in r['measurements']})
        target[kind]={label:{field:stats([v for r in records for v in r['measurements'].get(label,{}).get(key,[])]) for field,key in (('total','samples_ms'),('callback','callback_samples_ms'),('queue','queued_event_delays_ms'))} for label in labels}
        if kind=='ui' and records:
            target['unlock_memory_mib']=[r['unlock']['working_set_delta_bytes']/2**20 for r in records]
            target['guide_objects']=[r['guide'] for r in records]
            target['picker_objects']=[r['picker'] for r in records]
            target['pinned_replaced']=[r['leaderboard']['changed_refresh_replaces_pinned'] for r in records]
        if kind=='rapid':
            target['rapid_bursts']={label:stats([r['measurements'][label]['total_ms'] for r in records]) for label in labels}
    target['active']={k:stats(v['samples_ms']) for p in (OUT/stage/'active').glob('run-*/active-samples.json') for k,v in read(p).items()}
    target['extended']={k:{'total':stats(v['samples_ms']),'queue':stats(v['queued_event_delays_ms'])} for p in (OUT/stage/'extended').glob('run-*/ui-actions.json') for k,v in read(p).items()}
(OUT/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
lines=[]
for kind in ('ui','actions','rapid','rapid_bursts','active','extended'):
    lines+=['',f'## {kind}','','| Messung | n vorher / nachher | Vorher Median / Max ms | Nachher Median / Max ms | Änderung Median |','| --- | --- | --- | --- | --- |']
    for label,b in result['before'][kind].items():
        a=result['after'][kind].get(label)
        if a is None:continue
        if kind not in ('active','rapid_bursts'):a,b=a['total'],b['total']
        if not a or not b:continue
        change=(a['median_ms']/b['median_ms']-1)*100
        lines.append(f"| {label} | {b['n']} / {a['n']} | {b['median_ms']:.2f} / {b['max_ms']:.2f} | {a['median_ms']:.2f} / {a['max_ms']:.2f} | {change:+.1f}% |")
(OUT/'comparison-tables.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print('\n'.join(lines))
