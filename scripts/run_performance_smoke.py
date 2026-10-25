"""Two actual launches, save/reload and export, in strictly isolated test storage."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from zipfile import ZipFile

root = Path(__file__).resolve().parents[1]
packaged = '--exe' in sys.argv
parent = root / 'artifacts' / 'performance-test-20261025'
parent.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='exe-smoke-' if packaged else 'source-smoke-', dir=parent))
if packaged:
    command = [str(root / 'dist/performance-test-20261025/Industriova_Performance_Test/Industriova_Performance_Test.exe')]
else:
    command = [sys.executable, '-B', '-c', "import runpy;runpy.run_path('scripts/performance_test_runtime_hook.py');runpy.run_path('scripts/performance_test_smoke_hook.py');from production_zero.app.__main__ import main;raise SystemExit(main())"]
reports = []
for number in (1, 2):
    env = dict(os.environ, LOCALAPPDATA=str(out / 'appdata'), QT_QPA_PLATFORM='offscreen',
               INDUSTRIOVA_PERFORMANCE_SMOKE_ROOT=str(out), INDUSTRIOVA_PERFORMANCE_SMOKE_PASS=str(number),
               PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root / 'src'))
    run = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True,
                         encoding='utf-8', errors='replace', timeout=120)
    (out / f'stdout-{number}.txt').write_text(run.stdout, encoding='utf-8')
    (out / f'stderr-{number}.txt').write_text(run.stderr, encoding='utf-8')
    error = out / f'error-{number}.txt'
    assert run.returncode == 0, (number, run.returncode, run.stderr, error.read_text() if error.exists() else '')
    report = json.loads((out / f'pass-{number}.json').read_text())
    assert report['frozen'] == packaged
    with ZipFile(report['report']) as archive:
        assert archive.testzip() is None
        assert {'company.sqlite', 'baseline.sqlite', 'session.json', 'summary.json', 'export.json', 'README.txt'} <= set(archive.namelist())
        summary = json.loads(archive.read('summary.json'))
        assert summary['closed'] and summary['samples'] > 0 and summary['logger_error'] is None
        records = [json.loads(line) for n in archive.namelist() if n.endswith('.jsonl')
                   for line in archive.read(n).decode().splitlines()]
        assert any(r['kind'] == 'user_marked_stutter' for r in records)
        assert any(r['kind'] == 'session_ended' for r in records)
        assert any(r['kind'] == 'slow_operation' and r['operation'] == 'ui_heartbeat_gap' for r in records)
        assert 'save_snapshot' in summary['timings'] and 'save_worker' in summary['timings']
        assert summary['last_game_summary']['production_cards_installed'] == 3
        assert not any(r['kind'] in ('summary_error', 'operation_error', 'diagnostic_export_error') for r in records)
        metadata = json.loads(archive.read('session.json'))
        if packaged:
            assert metadata['build']['source_sha256'] and metadata['build']['file_count'] > 300
    reports.append(report)
    print(f'PASS launch {number}; packaged={packaged}; report/save/marker/known pause verified', flush=True)
assert reports[0]['iron_produced'] == reports[1]['iron_produced']
assert reports[0]['earnings'] == reports[1]['earnings']
(out / 'results.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
(parent / ('exe-smoke.json' if packaged else 'source-smoke.json')).write_text(
    json.dumps({'folder': str(out), 'results': reports}, indent=2), encoding='utf-8')
print(f'Evidence: {out}', flush=True)
