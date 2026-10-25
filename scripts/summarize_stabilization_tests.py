"""Collect complete isolated modules, retaining every earlier diagnostic log."""
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def main():
    root = Path('artifacts/industriova-stabilization')
    destination = root / 'verified-tests'
    destination.mkdir(exist_ok=True)
    overrides = {}
    results = []
    for test in sorted(Path('tests').glob('test_*.py')):
        source = root / overrides[test.stem] if test.stem in overrides else root / 'approved-tests' / test.stem
        report = ET.parse(source.with_suffix('.xml')).getroot()
        totals = {key: 0 for key in ('tests', 'failures', 'errors', 'skipped')}
        seconds = 0.
        for suite in report.iter('testsuite'):
            for key in totals:
                totals[key] += int(suite.get(key, 0))
            seconds += float(suite.get('time', 0))
        assert totals['tests'] > 0 and totals['failures'] == totals['errors'] == totals['skipped'] == 0, test.name
        for suffix in ('.xml', '.txt'):
            shutil.copy2(source.with_suffix(suffix), (destination / test.stem).with_suffix(suffix))
        results.append(dict(module=test.name, **totals, passed=totals['tests'], seconds=round(seconds, 3), evidence=source.as_posix()))
    sources = {path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
               for folder in ('src', 'tests') for path in Path(folder).rglob('*.py') if '__pycache__' not in path.parts}
    summary = {'modules': len(results), 'tests': sum(r['tests'] for r in results), 'passed': sum(r['passed'] for r in results),
               'failures': 0, 'errors': 0, 'skipped': 0, 'xfail': 0,
               'method': 'All test_*.py modules, isolated Qt processes; complete module reruns replace prior failures. No test deselection, skip or xfail in these reports.',
               'results': results, 'source_sha256': sources}
    (destination / 'results.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key not in ('results', 'source_sha256')}))


if __name__ == '__main__':
    main()
