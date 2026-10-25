"""Reconcile complete module reruns with explicit source/test provenance."""
import json,hashlib,shutil,difflib,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase7'
def read(p):return json.loads(p.read_text(encoding='utf8'))
baseline={r['module']:r for r in read(ROOT/'artifacts/phase6/final-tests/results.json')}
first={r['module']:r for r in read(OUT/'accepted-tests/results.json')}
reruns={r['module']:r for r in read(OUT/'accepted-reruns/results.json')}
assert set(reruns)=={'test_sqlite_store.py','test_phase4_drag_ui.py','test_industriova_release_ui.py','test_phase7_economy_ui.py','test_ui_polish_interactions.py'}
rows={**first,**reruns}
assert len(rows)==91 and len(baseline)==89
assert sum(r['tests'] for r in baseline.values())==1670
assert all(rows[k]['tests']==v['tests'] for k,v in baseline.items())
assert all(r['exit_code']==0 and r['passed']==r['tests'] and all(r[k]==0 for k in ('failures','errors','skipped')) for r in rows.values())
frozen=read(OUT/'accepted-source-tests-freeze.json')
current={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.py','.json'}}
changed=[name for name in current if frozen.get(name)!=current[name]]
assert set(changed)=={'src/production_zero/ui/release_board.py','tests/test_industriova_release_ui.py','tests/test_sqlite_store.py'},changed
# Verify the only productive delta is the three presentation statements seen in
# the visual audit. Pricing/command/simulation/migration logic is byte-identical.
p=ROOT/'src/production_zero/ui/release_board.py';text=p.read_text(encoding='utf8')
added="            quote_label.setStyleSheet('color: #f4eedb; background: transparent; border: 0;')\n            quote_font=quote_label.font();quote_font.setPointSize(12);quote_label.setFont(quote_font)\n            quote_label.setMargin(4)\n"
assert added in text
assert hashlib.sha256(text.replace(added,'').replace('\n','\r\n').encode('utf8')).hexdigest()==frozen[p.relative_to(ROOT).as_posix()]
dest=OUT/'final-accepted-tests';dest.mkdir(exist_ok=True);provenance=[]
for name,row in sorted(rows.items()):
    source=OUT/('accepted-reruns' if name in reruns else 'accepted-tests')
    for suffix in ('.txt','.xml'):shutil.copyfile(source/(Path(name).stem+suffix),dest/(Path(name).stem+suffix))
    provenance.append(dict(module=name,source=source.relative_to(ROOT).as_posix(),tests=row['tests']))
(dest/'results.json').write_text(json.dumps(list(rows.values()),indent=2),encoding='utf8')
(dest/'provenance.json').write_text(json.dumps(dict(modules=provenance,final_delta=changed,reason='Full 91-module run, then five complete affected modules after fixture capital/history expectation corrections and the three-line local quote contrast fix. No pricing/command/simulation/migration code changed after the full-suite freeze; no partial-test counting.'),indent=2),encoding='utf8')
summary=dict(tests=sum(r['tests'] for r in rows.values()),passed=sum(r['passed'] for r in rows.values()),modules=len(rows),retained_baseline_tests=1670,added_core_tests=rows['test_phase7_economy.py']['tests'],added_ui_tests=rows['test_phase7_economy_ui.py']['tests'],failures=0,errors=0,skipped=0,workers=2,isolated_appdata_per_module=True)
assert summary['tests']==1779
(OUT/'final-test-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(OUT/'tested-source-sha256.json').write_text(json.dumps(current,indent=2),encoding='utf8')
print(json.dumps(summary),flush=True)
