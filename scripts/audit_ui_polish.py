"""Verify unchanged persistence/economy paths and retain all prior test functions."""
import ast,hashlib,json,zipfile
from pathlib import Path
root=Path.cwd();out=root/'artifacts/ui-polish';baseline=out/'20261019T112903Z'
old=json.loads((baseline/'manifest.json').read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
unchanged={name:digest(root/name)==old[name] for name in (
    'src/production_zero/app/__main__.py','src/production_zero/persistence/sqlite_store.py',
    'src/production_zero/persistence/session_writer.py','src/production_zero/persistence/dev_save_store.py',
    'src/production_zero/core/state.py','src/production_zero/core/simulation.py',
    'src/production_zero/core/cards.py','src/production_zero/core/mk_upgrades.py',
    'src/production_zero/core/machine_operations.py','src/production_zero/core/supply.py')}
assert all(unchanged.values()),unchanged
removed=[]
with zipfile.ZipFile(baseline/'working-tree.zip') as z:
    for name in old:
        if not name.startswith('tests/') or not name.endswith('.py'):continue
        def tests(text):
            return {node.name for node in ast.walk(ast.parse(text)) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_')}
        missing=tests(z.read(name).decode('utf-8-sig'))-tests((root/name).read_text(encoding='utf-8-sig'))
        removed.extend((name,n) for n in missing)
assert not removed,removed
package=root/'dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip'
package_hash=digest(package)
assert package_hash=='bd7d36da910866cd9565b2e1138de6a29262222244a34b50afa01a5070f58177'
result={'unchanged_systems':unchanged,'removed_existing_test_functions':removed,'existing_dev2_package_sha256':package_hash,
        'source_and_test_sha256':{str(p.relative_to(root)).replace('\\','/'):digest(p) for d in ('src','tests') for p in (root/d).rglob('*.py') if '__pycache__' not in p.parts}}
(out/'scope-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'unchanged_systems':len(unchanged),'removed_tests':len(removed),'previous_package_unchanged':True}))
