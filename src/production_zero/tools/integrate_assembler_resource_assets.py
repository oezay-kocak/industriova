"""Validate and integrate the supplied Assembler resource artwork set unchanged."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil
import struct

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = Path(
    str(ROOT / "artifacts" / "asset-sources" / "assembler-icons")
)
MANIFEST = Path(
    str(ROOT / "artifacts" / "asset-sources" / "assembler-icon-manifest.csv")
)
ASSET_DIR = ROOT / "src" / "production_zero" / "assets" / "resources"
QA_DIR = ROOT / "artifacts" / "resource-assets" / "assembler-pass"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_rgba_png(path: Path) -> bool:
    data = path.read_bytes()[:29]
    return (
        data[:8] == b"\x89PNG\r\n\x1a\n"
        and data[12:16] == b"IHDR"
        and struct.unpack(">IIBBBBB", data[16:29])[2:4] == (8, 6)
    )


def _assembler_ids() -> list[str]:
    progression = json.loads(
        (ROOT / "src/production_zero/data/resource_progression.json").read_text(encoding="utf-8")
    )
    return [
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "assembler"
    ]


def validated_manifest() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    numerical_ids = [int(row["id"]) for row in rows]
    resource_ids = [row["filename"] for row in rows]
    source_ids = sorted(path.stem for path in SOURCE_DIR.glob("*.png"))
    progression_ids = _assembler_ids()
    if (
        len(rows) != 150
        or numerical_ids != list(range(204, 354))
        or len(set(numerical_ids)) != 150
        or len(set(resource_ids)) != 150
        or resource_ids != progression_ids
        or sorted(resource_ids) != source_ids
    ):
        raise RuntimeError("Assembler manifest, IDs, progression, and source files do not match exactly")
    for row in rows:
        source = SOURCE_DIR / f"{row['filename']}.png"
        image = QImage(str(source))
        if (
            image.isNull()
            or image.width() != 512
            or image.height() != 512
            or not image.hasAlphaChannel()
            or not _is_rgba_png(source)
        ):
            raise RuntimeError(f"Invalid 512x512 RGBA PNG: {source}")
        if not any(
            image.pixelColor(x, y).alpha() < 255
            for x, y in ((0, 0), (511, 0), (0, 511), (511, 511))
        ):
            raise RuntimeError(f"No usable transparency: {source}")
    return rows


def main() -> int:
    rows = validated_manifest()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    audit = []
    for row in rows:
        source = SOURCE_DIR / f"{row['filename']}.png"
        target = ASSET_DIR / source.name
        shutil.copyfile(source, target)
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if source_hash != target_hash:
            raise RuntimeError(f"Copied asset differs from source: {target}")
        audit.append(
            {
                "product_id": int(row["id"]),
                "resource_id": row["filename"],
                "display_name": row["display_name"],
                "source_file": str(source),
                "target_asset": target.relative_to(ROOT).as_posix(),
                "sha256": target_hash,
                "pixel_dimensions": [512, 512],
                "rgba_png": True,
                "artwork_modified": False,
            }
        )
    audit_path = QA_DIR / "assembler_resource_assets.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Integrated {len(audit)}/150 Assembler assets unchanged; audit: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
