"""Read-only release audit against the pre-dev3 working-tree snapshot."""
import ast
import hashlib
import json
import zipfile
from pathlib import Path

root = Path.cwd()
out = root / 'artifacts/dev3'
baseline = out / '20261019T121025Z'
manifest = json.loads((baseline / 'manifest.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
unchanged = [p for p in manifest if p.startswith('src/production_zero/core/') and p.endswith('.py')]
unchanged += ['src/production_zero/persistence/sqlite_store.py', 'src/production_zero/persistence/session_writer.py']
assert all(sha(root / p) == manifest[p] for p in unchanged)
retained = []
with zipfile.ZipFile(baseline / 'working-tree.zip') as archive:
    for name in archive.namelist():
        if not (name.startswith('tests/') and name.endswith('.py')):
            continue
        old = ast.parse(archive.read(name).decode('utf-8-sig'))
        new = ast.parse((root / name).read_text(encoding='utf-8-sig'))
        test_names = lambda tree: {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')}
        assert test_names(old) <= test_names(new), name
        assert 'xfail' not in (root / name).read_text(), name
        retained.append(name)
results = json.loads((out / 'regression/results.json').read_text())
assert len(results) == 76 and all(r['exit_code'] == 0 for r in results)
assert sum(r['passed'] for r in results) == 1200
assert sum(r['failures'] + r['errors'] + r['skipped'] for r in results) == 0
old_zip = root / 'dist/playtest/Industriova-0.2.0-ui-repaired-playtest-Windows.zip'
old_exe = root / 'dist/playtest/Industriova/Industriova.exe'
assert sha(old_zip) == 'bd7d36da910866cd9565b2e1138de6a29262222244a34b50afa01a5070f58177'
assert sha(old_exe) == '7a3692f467af6d9e2f212a5ef22a14210e0a274f9c920acf7755c30512363196'
for n in range(1, 4):
    assert (out / f'native/exit-{n}.txt').read_text().strip() == '0'
    assert (out / f'native/stderr-{n}.txt').stat().st_size == 0
result = {'passed': 1200, 'modules': 76, 'retained_old_test_files': len(retained), 'unchanged_core_and_persistence_files': len(unchanged), 'old_dev2_zip_and_exe_unchanged': True, 'native_exe_runs': 3, 'native_exit_codes': [0, 0, 0], 'native_stderr_bytes': 0}
(out / 'final-audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
(out / 'source-sha256.json').write_text(json.dumps({str(p.relative_to(root)): sha(p) for folder in ['src', 'tests'] for p in (root / folder).rglob('*.py')}, indent=2), encoding='utf-8')
print(json.dumps(result))
