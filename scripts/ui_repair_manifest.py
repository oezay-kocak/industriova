"""Freeze the tested code and retain a reviewable diff against the repair backup."""
import json,hashlib,zipfile,difflib,ast
from pathlib import Path
root=Path.cwd();out=root/'artifacts/industriova-ui-repair';backup=root/'artifacts/release-backups/20261018T221255021770Z'
results=json.loads((out/'approved-tests/results.json').read_text())
assert len(results)==74 and all(r['exit_code']==0 and r['failures']==r['errors']==r['skipped']==0 for r in results)
assert sum(r['passed'] for r in results)==1161
hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
changed=[];diff=[];removed_tests=[]
with zipfile.ZipFile(backup/'working-tree.zip') as z:
    oldnames=set(z.namelist())
    for name in hashes:
        old=z.read(name) if name in oldnames else b'';new=(root/name).read_bytes()
        if old!=new:
            changed.append({'path':name,'change':'modified' if old else 'added'})
            if name.endswith('.py'):
                diff.extend(difflib.unified_diff(old.decode('utf-8-sig').replace('\r\n','\n').splitlines(True),new.decode('utf-8-sig').replace('\r\n','\n').splitlines(True),fromfile='before/'+name,tofile='after/'+name))
        if name.startswith('tests/') and name.endswith('.py') and old:
            names=lambda data:{n.name for n in ast.walk(ast.parse(data.decode('utf-8-sig'))) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
            removed_tests.extend(name+':'+n for n in names(old)-names(new))
assert not removed_tests,removed_tests
(out/'tested-source.json').write_text(json.dumps({'tests':1161,'modules':74,'source_sha256':hashes,'existing_test_functions_removed':removed_tests,'backup':str(backup)},indent=2),encoding='utf-8')
(out/'changed-files.json').write_text(json.dumps(changed,indent=2),encoding='utf-8')
(out/'repair-source.diff').write_text(''.join(diff),encoding='utf-8')
print(json.dumps({'tests':1161,'modules':74,'changed_source_and_tests':len(changed),'removed_existing_test_functions':0}))
