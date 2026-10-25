"""Validate and integrate the complete Processor resource artwork set.

The supplied RGB pixels are preserved.  Processing is limited to creating an
alpha mask where the source has a baked background, aspect-preserving resize,
and transparent canvas padding.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = Path.home() / 'Desktop/PZ R/2'
ASSET_DIR = ROOT / "src" / "production_zero" / "assets" / "resources"
QA_DIR = ROOT / "artifacts" / "resource-assets" / "processor-pass"
ALIASES = {
    "aluminium": "aluminum",
}


@dataclass(frozen=True, slots=True)
class SourceMapping:
    resource_id: str
    ingame_name: str
    source: Path


def _slug(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.casefold())).strip("_")


def validated_mapping() -> tuple[SourceMapping, ...]:
    progression = json.loads((ROOT / "src/production_zero/data/resource_progression.json").read_text(encoding="utf-8"))
    definitions = json.loads((ROOT / "src/production_zero/data/resource_definitions.json").read_text(encoding="utf-8"))
    processor_ids = {
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "processor"
    }
    names = {entry["id"]: entry["name"] for entry in definitions["resources"]}
    sources = sorted(SOURCE_DIR.glob("*.png"))
    if len(processor_ids) != 68 or len(sources) != 68:
        raise RuntimeError(f"Processor/source count mismatch: {len(processor_ids)}/{len(sources)}")

    by_name = {_slug(names[resource_id]): resource_id for resource_id in processor_ids}
    mappings: list[SourceMapping] = []
    unknown: list[str] = []
    for source in sources:
        source_key = _slug(source.stem)
        resource_id = ALIASES.get(source_key, by_name.get(source_key))
        if resource_id is None or resource_id not in processor_ids:
            unknown.append(source.name)
            continue
        mappings.append(SourceMapping(resource_id, names[resource_id], source))

    mapped_ids = [mapping.resource_id for mapping in mappings]
    duplicates = sorted({resource_id for resource_id in mapped_ids if mapped_ids.count(resource_id) > 1})
    missing = sorted(processor_ids - set(mapped_ids))
    if unknown or duplicates or missing or len(mappings) != 68:
        raise RuntimeError(f"Invalid 68/68 mapping: unknown={unknown}, duplicates={duplicates}, missing={missing}")
    return tuple(sorted(mappings, key=lambda item: item.resource_id))


def _flood_outside(barrier: Image.Image) -> np.ndarray:
    flooded = barrier.copy()
    ImageDraw.floodfill(flooded, (0, 0), 128, thresh=0)
    return np.asarray(flooded) == 128


def _alpha_for_baked_background(rgb: np.ndarray) -> Image.Image:
    """Recover silhouettes bounded by the supplied artwork's outline."""
    luminance = (
        rgb[..., 0].astype(np.uint16) * 54
        + rgb[..., 1].astype(np.uint16) * 183
        + rgb[..., 2].astype(np.uint16) * 19
    ) // 256
    edge = np.concatenate((luminance[:12].ravel(), luminance[-12:].ravel(), luminance[:, :12].ravel(), luminance[:, -12:].ravel()))
    dark_background = int(np.median(edge)) < 20
    barrier_pixels = luminance > 10 if dark_background else luminance < 82
    barrier = Image.fromarray((barrier_pixels * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(7))
    solid = Image.fromarray((~_flood_outside(barrier) * 255).astype(np.uint8), "L").filter(ImageFilter.MinFilter(5))
    solid_array = np.asarray(solid) > 0
    # Restore the exact outline pixels after closing small gaps for the flood.
    mask = np.logical_or(solid_array, barrier_pixels)
    return Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7))


def _integrated_image(source: Path) -> tuple[Image.Image, bool]:
    with Image.open(source) as opened:
        had_alpha = opened.mode in {"RGBA", "LA", "PA"} or "transparency" in opened.info
        rgba = opened.convert("RGBA")
    if had_alpha and rgba.getchannel("A").getextrema()[0] < 255:
        alpha = rgba.getchannel("A")
        corrected = False
    else:
        rgb = np.asarray(rgba)[..., :3]
        alpha = _alpha_for_baked_background(rgb)
        rgba.putalpha(alpha)
        corrected = True
    bounds = alpha.getbbox()
    if bounds is None:
        raise RuntimeError(f"Empty alpha extraction: {source}")
    artwork = rgba.crop(bounds)
    artwork.thumbnail((440, 440), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.alpha_composite(artwork, ((512 - artwork.width) // 2, (512 - artwork.height) // 2))
    return canvas, corrected


def _contact_sheet(mappings: tuple[SourceMapping, ...]) -> None:
    columns, cell_width, cell_height = 7, 220, 190
    rows = (len(mappings) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), "#0b0f13")
    draw = ImageDraw.Draw(sheet)
    font_path = Path(r"C:\Windows\Fonts\arialbd.ttf")
    font = ImageFont.truetype(str(font_path), 14) if font_path.is_file() else ImageFont.load_default()
    for index, mapping in enumerate(mappings):
        row, column = divmod(index, columns)
        x, y = column * cell_width, row * cell_height
        light = (row + column) % 2 == 1
        panel_color = "#edf0f2" if light else "#151b21"
        label_color = "#172027" if light else "#f4c928"
        draw.rectangle((x + 6, y + 6, x + cell_width - 6, y + cell_height - 6), fill=panel_color)
        with Image.open(ASSET_DIR / f"{mapping.resource_id}.png") as opened:
            icon = opened.convert("RGBA")
        icon.thumbnail((158, 138), Image.Resampling.LANCZOS)
        sheet.paste(icon, (x + (cell_width - icon.width) // 2, y + 10 + (138 - icon.height) // 2), icon)
        label = mapping.resource_id.upper()
        bounds = draw.textbbox((0, 0), label, font=font)
        draw.text((x + (cell_width - (bounds[2] - bounds[0])) // 2, y + 158), label, fill=label_color, font=font)
    sheet.save(QA_DIR / "processor_icons_contact_sheet.png", optimize=True)


def main() -> int:
    mappings = validated_mapping()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, object]] = []
    for mapping in mappings:
        image, corrected = _integrated_image(mapping.source)
        target = ASSET_DIR / f"{mapping.resource_id}.png"
        image.save(target, optimize=True)
        alpha = image.getchannel("A")
        report.append(
            {
                "resource_id": mapping.resource_id,
                "ingame_name": mapping.ingame_name,
                "source_file": str(mapping.source),
                "target_asset": str(target.relative_to(ROOT)).replace("\\", "/"),
                "pixel_dimensions": [image.width, image.height],
                "alpha_present": True,
                "source_alpha_present": not corrected,
                "alpha_correction_applied": corrected,
                "visible_alpha_bounds": list(alpha.getbbox() or ()),
                "rendering_successful": True,
            }
        )
    (QA_DIR / "processor_resource_assets.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    _contact_sheet(mappings)
    print(f"Integrated {len(report)}/68 assets; alpha corrected: {sum(bool(row['alpha_correction_applied']) for row in report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
