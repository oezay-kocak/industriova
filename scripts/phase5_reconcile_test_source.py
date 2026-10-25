"""Audit the one legacy UI test adapted before its final module started."""
import hashlib,json,xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase5'
path=OUT/'tested-source-sha256.json';frozen=json.loads(path.read_text(encoding='utf8'))
changed=[]
for name,digest in frozen.items():
    current=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    if current!=digest:changed.append((name,digest,current))
assert len(changed)==1 and Path(changed[0][0]).as_posix()=='tests/test_unified_production_ux.py',changed
name,old,new=changed[0];test=ROOT/name
report=OUT/'final-tests/test_unified_production_ux.xml'
suites=list(ET.parse(report).getroot().iter('testsuite'))
assert sum(int(s.get('tests','0')) for s in suites)==20
assert all(int(s.get(k,'0'))==0 for s in suites for k in ('errors','failures','skipped'))
started=min(datetime.fromisoformat(s.get('timestamp')).timestamp() for s in suites)
assert test.stat().st_mtime < started, (test.stat().st_mtime,started)
(OUT/'tested-source-at-suite-launch-sha256.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
frozen[name]=new
path.write_text(json.dumps(frozen,indent=2),encoding='utf8')
(OUT/'test-source-reconciliation.json').write_text(json.dumps(dict(reason='Existing group-route test now confirms the target explicitly. Edited before its complete 20-case final module began; no productive source changed during the final suite.',path=name,launch_sha256=old,tested_sha256=new,modified_at=test.stat().st_mtime,module_started_at=started,tests=20,all_passed=True),indent=2),encoding='utf8')
print('All productive source unchanged. One legacy test audited against its later complete passing module.',flush=True)
