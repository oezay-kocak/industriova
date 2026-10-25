"""Validate and integrate the supplied Fabricator resource artwork set unchanged."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from PySide6.QtGui import QImage


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = Path.home() / 'Desktop/PZ R/3'
ASSET_DIR = ROOT / "src" / "production_zero" / "assets" / "resources"
QA_DIR = ROOT / "artifacts" / "resource-assets" / "fabricator-pass"


def expected_ids() -> set[str]:
    progression = json.loads((ROOT / "src/production_zero/data/resource_progression.json").read_text(encoding="utf-8"))
    return {resource_id for resource_id, entry in progression["resources"].items() if entry["stage"] == "fabricator"}


def validated_sources() -> list[Path]:
    expected = expected_ids()
    sources = sorted(SOURCE_DIR.glob("*.png"))
    stems = [source.stem for source in sources]
    duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
    missing = sorted(expected - set(stems))
    unknown = sorted(set(stems) - expected)
    if len(expected) != 86 or len(sources) != 86 or duplicates or missing or unknown:
        raise RuntimeError(
            f"Invalid Fabricator mapping: definitions={len(expected)}, files={len(sources)}, "
            f"duplicates={duplicates}, missing={missing}, unknown={unknown}"
        )
    for source in sources:
        image = QImage(str(source))
        if image.isNull() or image.size().width() != 512 or image.size().height() != 512 or not image.hasAlphaChannel():
            raise RuntimeError(f"Invalid 512x512 RGBA PNG: {source}")
        if not any(image.pixelColor(x, y).alpha() < 255 for x, y in ((0, 0), (511, 0), (0, 511), (511, 511))):
            raise RuntimeError(f"No usable transparency: {source}")
    return sources


def main() -> int:
    sources = validated_sources()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    audit = []
    for source in sources:
        target = ASSET_DIR / source.name
        shutil.copyfile(source, target)
        audit.append({
            "resource_id": source.stem,
            "source_file": str(source),
            "target_asset": target.relative_to(ROOT).as_posix(),
            "pixel_dimensions": [512, 512],
            "rgba_png": True,
            "artwork_modified": False,
        })
    (QA_DIR / "fabricator_resource_assets.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Integrated {len(audit)}/86 Fabricator assets without modifying artwork")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
