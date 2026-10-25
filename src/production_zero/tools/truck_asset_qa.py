"""Render the Truck SVG and its real Freight card without opening a GUI."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import CommandBus
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.freight_art import FREIGHT_ASSETS, draw_freight_art
from production_zero.ui.freight_view import FreightView
from production_zero.ui.theme import APP_STYLESHEET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "truck_reference_asset"
SIZES = (512, 128, 64)


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _render_asset(size: int) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    draw_freight_art(painter, QRectF(0, 0, size, size), family="truck")
    painter.end()
    return image


def _render_card() -> QImage:
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    state = GameState(rng_seed=1)
    card = create_card_instance("truck-reference-qa", "freight.truck", CardKind.FREIGHT, Rarity.COMMON)
    state.cards[card.card_id] = card
    view = FreightView(state, CommandBus(state), definitions, {})
    widget = view._build_slot_card(0, card.card_id)
    widget.ensurePolished()
    if widget.layout():
        widget.layout().activate()
    widget._position_installed_controls()
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("#080d11"))
    painter = QPainter(image)
    widget.render(painter, QPoint(0, 0))
    painter.end()
    widget.deleteLater()
    view.deleteLater()
    return image


def render(phase: str) -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        assert _render_asset(size).save(str(OUTPUT / f"{phase}_truck_{size}.png"))
    assert _render_card().save(str(OUTPUT / f"{phase}_truck_card_166x264.png"))


def compare() -> None:
    _app()
    sheet = QImage(388, 322, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Segoe UI", 11))
    painter.setPen(QColor("#e1e9e7"))
    for column, phase in enumerate(("before", "after")):
        x = 18 + column * 184
        painter.drawText(x, 10, 166, 28, Qt.AlignmentFlag.AlignCenter,
                         "VORHER" if phase == "before" else "NACHHER")
        image = QImage(str(OUTPUT / f"{phase}_truck_card_166x264.png"))
        assert not image.isNull()
        painter.drawImage(QPoint(x, 40), image)
    painter.end()
    assert sheet.save(str(OUTPUT / "comparison_truck_card_166x264.png"))

    scale_sheet = QImage(768, 570, QImage.Format.Format_ARGB32)
    scale_sheet.fill(QColor("#a8b5bd"))
    painter = QPainter(scale_sheet)
    painter.setFont(QFont("Segoe UI", 11))
    painter.setPen(QColor("#10202a"))
    x = 16
    for size in SIZES:
        image = QImage(str(OUTPUT / f"after_truck_{size}.png"))
        painter.drawText(x, 8, size, 24, Qt.AlignmentFlag.AlignCenter, f"{size} × {size}")
        painter.drawImage(QPoint(x, 38), image)
        x += size + 18
    painter.end()
    assert scale_sheet.save(str(OUTPUT / "truck_scale_contact_sheet.png"))


def verify() -> None:
    _app()
    report = {"renders": {}}
    for size in SIZES:
        image = QImage(str(OUTPUT / f"after_truck_{size}.png"))
        assert not image.isNull()
        pixels = [(x, y) for y in range(size) for x in range(size) if image.pixelColor(x, y).alpha()]
        assert pixels
        bounds = [min(x for x, y in pixels), min(y for x, y in pixels),
                  max(x for x, y in pixels), max(y for x, y in pixels)]
        assert bounds[0] > 0 and bounds[1] > 0 and bounds[2] < size - 1 and bounds[3] < size - 1
        assert len(pixels) > size * size * .12
        report["renders"][str(size)] = {"alpha_bounds": bounds, "visible_pixels": len(pixels)}

    before = QImage(str(OUTPUT / "before_truck_card_166x264.png"))
    after = QImage(str(OUTPUT / "after_truck_card_166x264.png"))
    assert before.size() == after.size()
    changed = [(x, y) for y in range(after.height()) for x in range(after.width())
               if before.pixel(x, y) != after.pixel(x, y)]
    art = QRectF(34, 79, 98, 80)
    assert changed and all(art.contains(x + .5, y + .5) for x, y in changed)
    report["card_166x264"] = {
        "changed_pixels": len(changed),
        "outside_art_changes": 0,
        "change_bounds": [min(x for x, y in changed), min(y for x, y in changed),
                          max(x for x, y in changed), max(y for x, y in changed)],
    }
    source = FREIGHT_ASSETS["truck"]
    image = QImage(str(source))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == "ef243c4bf902e28c2522fa4847bf3fdfb1637e0da6d1415cb89027ed3d5aa39e"
    assert image.size().toTuple() == (1721, 914) and image.hasAlphaChannel()
    report["source"] = {
        "path": str(source),
        "sha256": digest,
        "byte_identical_to_golden_sample": True,
        "dimensions": [image.width(), image.height()],
        "has_alpha": True,
        "aspect_ratio": image.width() / image.height(),
    }
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Truck QA passed: exact PNG verified, all sizes padded, card changes confined to artwork.")


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after", "compare", "verify"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    phase = args.phase
    OUTPUT = args.output_dir
    if phase == "compare":
        compare()
    elif phase == "verify":
        verify()
    else:
        render(phase)
    print(OUTPUT)


if __name__ == "__main__":
    main()
