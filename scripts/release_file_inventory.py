"""List actual task changes against the pre-overhaul working-tree manifest."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
baseline = json.loads((root / "artifacts/release-backups/20261018T185514851717Z/manifest.json").read_text(encoding="utf-8"))
original = {entry["path"]: entry["sha256"] for entry in baseline["files"]}
original.pop("scripts/backup_release.py", None)  # Created to take the initial snapshot itself.
current = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for folder in ("src", "tests", "scripts", "docs", "tools") for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
current.update({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()})
report = {"modified": sorted(name for name in original.keys() & current.keys() if original[name] != current[name]), "added": sorted(current.keys() - original.keys()), "removed": sorted(original.keys() - current.keys())}
(root / "artifacts/industriova-release/changed-files.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
