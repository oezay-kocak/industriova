from __future__ import annotations

import os
import json
from pathlib import Path
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.ui.resource_art import (
    ASSEMBLER_RESOURCE_IDS,
    EXTRACTOR_RESOURCE_IDS,
    FABRICATOR_RESOURCE_IDS,
    PROCESSOR_RESOURCE_IDS,
    RESOURCE_RASTER_ASSETS,
    has_resource_raster,
    resource_raster_image,
)
from production_zero.ui.resource_icons import ResourceIconWidget


EXPECTED_EXTRACTOR_RASTERS = set(EXTRACTOR_RESOURCE_IDS)
EXPECTED_PROCESSOR_RASTERS = set(PROCESSOR_RESOURCE_IDS)
EXPECTED_FABRICATOR_RASTERS = set(FABRICATOR_RESOURCE_IDS)
EXPECTED_ASSEMBLER_RASTERS = set(ASSEMBLER_RESOURCE_IDS)
EXPECTED_RESOURCE_RASTERS = (
    EXPECTED_EXTRACTOR_RASTERS
    | EXPECTED_PROCESSOR_RASTERS
    | EXPECTED_FABRICATOR_RASTERS
    | EXPECTED_ASSEMBLER_RASTERS
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_mapping_contains_exactly_all_353_progression_resources() -> None:
    assert set(RESOURCE_RASTER_ASSETS) == EXPECTED_RESOURCE_RASTERS
    assert len(EXPECTED_EXTRACTOR_RASTERS) == 49
    assert len(EXPECTED_PROCESSOR_RASTERS) == 68
    assert len(EXPECTED_FABRICATOR_RASTERS) == 86
    assert len(EXPECTED_ASSEMBLER_RASTERS) == 150
    assert len(EXPECTED_RESOURCE_RASTERS) == 353
    assert all(has_resource_raster(resource_id) for resource_id in EXPECTED_RESOURCE_RASTERS)
    assert has_resource_raster("resource.copper_ore")
    assert has_resource_raster("limestone")
    assert has_resource_raster("steel")
    assert has_resource_raster("iron_components")
    assert has_resource_raster("advanced_semiconductor_equipment")
    assert not has_resource_raster("unknown_resource")


def test_mapping_matches_all_active_progression_stages_without_fallbacks() -> None:
    root = Path(__file__).resolve().parents[1]
    progression = json.loads((root / "src/production_zero/data/resource_progression.json").read_text(encoding="utf-8"))
    extractor_ids = {
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "extractor"
    }
    processor_ids = {
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "processor"
    }
    fabricator_ids = {
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "fabricator"
    }
    assembler_ids = {
        resource_id
        for resource_id, entry in progression["resources"].items()
        if entry["stage"] == "assembler"
    }
    migrated_ids = extractor_ids | processor_ids | fabricator_ids | assembler_ids
    assert EXPECTED_EXTRACTOR_RASTERS == extractor_ids
    assert EXPECTED_PROCESSOR_RASTERS == processor_ids
    assert EXPECTED_FABRICATOR_RASTERS == fabricator_ids
    assert EXPECTED_ASSEMBLER_RASTERS == assembler_ids
    assert set(RESOURCE_RASTER_ASSETS) == migrated_ids
    assert len(progression["resources"]) - len(migrated_ids) == 0


def test_migrated_assets_have_real_alpha_and_safe_transparent_padding() -> None:
    for resource_id, path in RESOURCE_RASTER_ASSETS.items():
        assert path.is_file(), resource_id
        image = resource_raster_image(resource_id)
        assert image.size().width() == image.size().height() == 512
        assert image.hasAlphaChannel()
        png_header = path.read_bytes()[:29]
        assert png_header[:8] == b"\x89PNG\r\n\x1a\n"
        assert png_header[12:16] == b"IHDR"
        assert struct.unpack(">IIBBBBB", png_header[16:29])[2:4] == (8, 6)
        # Same full-image threshold/count/bounds check in native image operations:
        # avoid 92 million Python/Qt calls and two huge coordinate lists.
        rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
        alpha = bytes(rgba.constBits())[3::4]
        mask = alpha.translate(bytes(1 if value > 8 else 0 for value in range(256)))
        assert mask.count(1) > 4_000, resource_id
        rows = [(y, mask[y * 512:(y + 1) * 512]) for y in range(512)]
        visible = [(y, row) for y, row in rows if b'\x01' in row]
        bounds = (min(row.find(b'\x01') for _, row in visible), visible[0][0],
                  max(row.rfind(b'\x01') for _, row in visible) + 1, visible[-1][0] + 1)
        assert bounds[0] >= 35 and bounds[2] - 1 <= 476, resource_id
        assert bounds[1] >= 35 and bounds[3] - 1 <= 476, resource_id
        assert all(image.pixelColor(x, y).alpha() == 0 for x, y in ((0, 0), (511, 0), (0, 511), (511, 511)))


def test_raster_resources_render_through_the_shared_icon_widget_at_ui_size() -> None:
    _app()
    for resource_id in EXPECTED_RESOURCE_RASTERS:
        widget = ResourceIconWidget(resource_id, "hex", "default", size=42)
        widget.ensurePolished()
        image = QImage(42, 42, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter(image)
        widget.render(painter, QPoint(0, 0))
        painter.end()
        visible_pixels = sum(
            image.pixelColor(x, y).alpha() > 8
            for y in range(image.height())
            for x in range(image.width())
        )
        assert visible_pixels > 100, resource_id
