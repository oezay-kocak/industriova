"""Collect complete module runs; never discard failing first attempts."""
import json,shutil,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase4'
parser=argparse.ArgumentParser();parser.add_argument('--reruns',type=Path,action='append',default=[]);args=parser.parse_args()
first=OUT/'first-full-tests';records=json.loads((first/'results.json').read_text(encoding='utf8'))
results={r['module']:(r,first) for r in records}
for reruns in args.reruns:
    reruns=reruns.resolve()
    for r in json.loads((reruns/'results.json').read_text(encoding='utf8')):results[r['module']]=(r,reruns)
baseline=json.loads((ROOT/'artifacts/phase3/final-tests/results.json').read_text(encoding='utf8'))
assert len(results)==85, len(results)
for row in baseline:
    current=results[row['module']][0]
    assert current.get('tests')==row['tests'],(row['module'],current.get('tests'),row['tests'])
assert all(r['exit_code']==0 and r.get('failures')==0 and r.get('errors')==0 and r.get('skipped')==0 for r,p in results.values())
final=OUT/'final-tests';final.mkdir(exist_ok=True);provenance=[]
for module,(row,source) in sorted(results.items()):
    for suffix in ('.xml','.txt'):
        p=source/(Path(module).stem+suffix)
        assert p.is_file();shutil.copyfile(p,final/p.name)
    provenance.append(dict(module=module,source=str(source.relative_to(ROOT)),seconds=row['seconds']))
rows=[r for r,p in results.values()];(final/'results.json').write_text(json.dumps(sorted(rows,key=lambda r:r['module']),indent=2),encoding='utf8')
(final/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf8')
summary=dict(modules=len(rows),passed=sum(r['passed'] for r in rows),tests=sum(r['tests'] for r in rows),failures=0,errors=0,skipped=0,
             original_cases=sum(r['tests'] for r in baseline),new_cases=sum(r['tests'] for r in rows)-sum(r['tests'] for r in baseline),seconds=sum(r['seconds'] for r in rows))
(OUT/'final-test-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
