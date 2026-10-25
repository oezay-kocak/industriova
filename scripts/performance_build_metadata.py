"""Fingerprint exactly the sources and assets used by the diagnostic build."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
paths = sorted(p for p in root.joinpath('src').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
paths += sorted(root.glob('scripts/*performance*'))
paths += [root / 'Industriova_Performance_Test.spec']
entries = {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
payload = {'build_kind': 'local-performance-playtest', 'built_utc': datetime.now(timezone.utc).isoformat(),
           'source_sha256': sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(),
           'file_count': len(entries), 'files': entries,
           'game_rules': 'Current source rules, prices and progression; Dev Tools enabled'}
destination = Path(sys.argv[1])
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(payload, indent=2), encoding='utf-8')
print(f'Fingerprint created for {len(entries)} files.')
