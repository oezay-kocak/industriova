"""Read-only comparison against the pre-pass archive and final test evidence."""
import ast
import hashlib
import json
import zipfile
from pathlib import Path

root = Path.cwd()
out = root / 'artifacts/unified-ux'
backup = out / '20261019T142502Z'
manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
changed = [p for p, sha in manifest.items() if not (root / p).exists() or digest(root / p) != sha]
protected = ['core/cards.py', 'core/enums.py', 'core/economy.py', 'core/fixed_prices.py',
             'core/mk_upgrades.py', 'core/modifiers.py', 'core/supply.py', 'core/progression.py',
             'core/production_values.py', 'core/release_balance.py', 'core/contracts.py',
             'core/infrastructure.py', 'core/research.py', 'data/definitions.py',
             'persistence/paths.py', 'persistence/session_writer.py']
unchanged = {p: digest(root / 'src/production_zero' / p) == manifest['src/production_zero/' + p] for p in protected}
assert all(unchanged.values()), unchanged

def tests(source):
    tree = ast.parse(source)
    return {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')}

with zipfile.ZipFile(backup / 'working-tree.zip') as archive:
    retained = {}
    for name in archive.namelist():
        if name.startswith('tests/test_') and name.endswith('.py'):
            previous = tests(archive.read(name))
            current = tests((root / name).read_bytes())
            retained[name] = not (previous - current)
    assert all(retained.values())
results = json.loads((out / 'regression-verified/results.json').read_text())
assert len(results) == 78 and all(r['exit_code'] == 0 and r['skipped'] == 0 for r in results)
assert sum(r['passed'] for r in results) == 1231
old = root / 'dist/playtest/Industriova-0.2.0-dev3-Windows-Playtest.zip'
assert digest(old) == 'f6fda211eb8c99f1e27ff25ef313dd30430a24b94dfe1c7567b4a981473b14d7'
evidence = {'backup_files': len(manifest), 'backup_sha256': digest(backup / 'working-tree.zip'),
            'changed_existing_files': changed, 'protected_files_unchanged': unchanged,
            'previous_test_modules_retained': len(retained), 'previous_test_functions_retained': all(retained.values()),
            'modules': len(results), 'passed': sum(r['passed'] for r in results), 'skipped': 0,
            'previous_cases': sum(r['passed'] for r in results if r['module'] not in ('test_paid_templates.py', 'test_unified_production_ux.py')),
            'dev3_zip_unchanged_sha256': digest(old)}
(out / 'source-audit.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
print(json.dumps(evidence, indent=2))
