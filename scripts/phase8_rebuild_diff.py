"""Refresh the P8-only review diff after final report/tool authoring."""
import difflib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];O=R/'artifacts/phase8';BASE=O/'before-tree'
backup=Path((O/'backup-location.txt').read_text(encoding='utf8'))
known={e['path'] for e in json.loads((backup/'manifest.json').read_text(encoding='utf8'))['entries']}
result=json.loads((O/'protected-verification.json').read_text(encoding='utf8'));assert result['ok']
new=[]
for folder in ('src','tests','scripts','docs'):
    for p in sorted((R/folder).rglob('*')):
        name=p.relative_to(R).as_posix()
        if p.is_file() and p.suffix in {'.py','.md','.json','.csv'} and '__pycache__/' not in name and name not in known:new.append(name)
assert not any(p.startswith('src/') and p!='src/production_zero/core/contract_capacity.py' for p in new)
diff=[]
for name in result['changed_existing_source']:
    before=BASE/name;after=R/name
    if before.is_file() and after.suffix in {'.py','.md','.json','.csv'}:
        diff.extend(difflib.unified_diff(before.read_text(encoding='utf8').splitlines(True),after.read_text(encoding='utf8').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
for name in new:diff.extend(difflib.unified_diff([],(R/name).read_text(encoding='utf8').splitlines(True),fromfile='/dev/null',tofile='after/'+name))
result['new_files']=sorted(new)
(O/'protected-verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
(O/'implementation.diff').write_text(''.join(diff),encoding='utf8')
print('P8 diff refreshed; existing protection checks retained, new authorized files',len(new))
