"""Capture the working tree and consistent SQLite snapshots before release changes."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "artifacts" / "release-backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir(parents=True, exist_ok=False)
    manifest = {"source": str(root), "files": [], "saves": []}
    with ZipFile(destination / "working-tree.zip", "w", ZIP_DEFLATED) as archive:
        paths = [p for folder in ("src", "tests", "scripts", "docs", "tools") for p in (root / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        paths += [p for p in root.iterdir() if p.is_file()]
        for path in sorted(paths):
            data = path.read_bytes()
            name = path.relative_to(root).as_posix()
            archive.writestr(name, data)
            manifest["files"].append({"path": name, "sha256": hashlib.sha256(data).hexdigest()})
    save_roots = [root / "artifacts", Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Industriova" / "saves"]
    for save_root in save_roots:
        if not save_root.exists():
            continue
        for path in sorted(save_root.rglob("*")):
            if not path.is_file() or destination.parent in path.parents:
                continue
            if path.suffix not in {".sqlite", ".db"} and path.name != "dev_save.json":
                continue
            target = destination / "saves" / str(len(manifest["saves"])) / path.name
            target.parent.mkdir(parents=True)
            if path.suffix in {".sqlite", ".db"}:
                with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(target)) as copy:
                    source.backup(copy)
                    if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError(f"Backup integrity check failed: {path}")
            else:
                target.write_bytes(path.read_bytes())
            manifest["saves"].append({"source": str(path), "backup": str(target.relative_to(destination)), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"backup": str(destination), "files": len(manifest["files"]), "saves": len(manifest["saves"])}))


if __name__ == "__main__":
    main()
