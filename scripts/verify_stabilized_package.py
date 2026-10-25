"""Verify ZIP contents/CRC, EXE identity and source hashes after a successful build."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
from production_zero.ui.resource_art import RESOURCE_RASTER_ASSETS

root = Path(__file__).resolve().parents[1]
destination = root / 'artifacts/industriova-stabilization'
package = root / 'dist/playtest/Industriova-0.2.0-stabilized-playtest-Windows.zip'
required = ['Industriova/Industriova.exe', 'Industriova/LIESMICH.txt',
            'Industriova/_internal/PySide6/Qt6Core.dll', 'Industriova/_internal/PySide6/plugins/platforms/qwindows.dll']
assets = {'Industriova/_internal/' + path.relative_to(root / 'src').as_posix() for path in RESOURCE_RASTER_ASSETS.values()}
with ZipFile(package) as archive:
    names = set(archive.namelist())
    assert archive.testzip() is None
    assert set(required) <= names, set(required) - names
    assert assets <= names and len(assets) == 353
    saves = [name for name in names if Path(name).suffix.lower() in {'.db', '.sqlite', '.sqlite3'} or '/saves/' in name.lower() or name.lower().endswith('dev_save.json')]
    assert not saves, saves
    assert b'0.2.0.dev1' in archive.read('Industriova/LIESMICH.txt')
    assert archive.read('Industriova/Industriova.exe') == (root / 'dist/playtest/Industriova/Industriova.exe').read_bytes()
version = json.loads((destination / 'exe-version.json').read_text(encoding='utf-8-sig'))
assert version['ProductName'] == 'Industriova' and version['ProductVersion'] == version['FileVersion'] == '0.2.0.dev1'
assert version['OriginalFilename'] == 'Industriova.exe' and 'Playtest' in version['FileDescription']
verified = json.loads((destination / 'verified-tests/results.json').read_text(encoding='utf-8'))
for path, digest in verified['source_sha256'].items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, 'Changed after test approval: ' + path
report = dict(path=str(package), bytes=package.stat().st_size, sha256=hashlib.sha256(package.read_bytes()).hexdigest(),
              crc='ok', entries=len(names), resource_images=len(assets), personal_saves=saves, exe_version=version, tested_source_hashes_match=True)
(destination / 'package-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
