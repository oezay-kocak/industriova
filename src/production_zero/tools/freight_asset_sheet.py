"""Render real Freight widgets without opening a window (before/after QA)."""
from __future__ import annotations

import argparse
import ast
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
from production_zero.ui.freight_view import FreightSelectionCard, FreightView
from production_zero.ui.theme import APP_STYLESHEET
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.game_ui.rendering import factory
from production_zero.ui.freight_art import FREIGHT_ASSETS, FREIGHT_SVG_ASSETS, _renderer, draw_freight_art

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "freight_asset_pass"
FAMILIES = ("truck", "train", "ship", "aircraft")


def render_cards(phase: str) -> None:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    app.setStyleSheet(APP_STYLESHEET)
    if phase == "before":
        # Use the exact working-tree drawing function captured before the pass,
        # not HEAD (which may predate the user's current card design).
        source = OUTPUT / "factory_before.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "_draw_prototype_pictogram")
        namespace = dict(vars(factory))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
        factory._draw_prototype_pictogram = namespace[node.name]
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    state = GameState(rng_seed=1)
    view = FreightView(state, CommandBus(state), definitions, {})
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for family in FAMILIES:
        definition_id = f"freight.{family}"
        card = create_card_instance(f"qa-{family}", definition_id, CardKind.FREIGHT, Rarity.COMMON)
        state.cards[card.card_id] = card
        widgets = {
            "installed": view._build_slot_card(0, card.card_id),
            "selection": FreightSelectionCard(card, definitions[definition_id], 1),
        }
        for kind, widget in widgets.items():
            widget.ensurePolished()
            if widget.layout():
                widget.layout().activate()
            if kind == "installed":
                widget._position_installed_controls()
            result = QImage(widget.size(), QImage.Format.Format_ARGB32)
            result.fill(QColor("#080d11"))
            painter = QPainter(result)
            widget.render(painter, QPoint(0, 0))
            painter.end()
            assert result.save(str(OUTPUT / f"{phase}_{kind}_{family}.png"))
            widget.deleteLater()
    view.deleteLater()


def comparison(before_phase: str = "before", after_phase: str = "after") -> None:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    for kind, height in (("installed", 264), ("selection", 224)):
        sheet = QImage(744, 2 * (height + 42) + 20, QImage.Format.Format_ARGB32)
        sheet.fill(QColor("#080d11"))
        painter = QPainter(sheet)
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor("#e1e9e7"))
        for row, phase in enumerate((before_phase, after_phase)):
            y = 12 + row * (height + 42)
            painter.drawText(16, y, 700, 26, Qt.AlignmentFlag.AlignLeft,
                             f"{'VORHER' if row == 0 else 'NACHHER'}  |  {kind}  |  166 × {height} px (1:1)")
            for col, family in enumerate(FAMILIES):
                source = QImage(str(OUTPUT / f"{phase}_{kind}_{family}.png"))
                assert not source.isNull(), (phase, kind, family)
                painter.drawImage(QPoint(16 + col * 180, y + 30), source)
        painter.end()
        assert sheet.save(str(OUTPUT / f"comparison_{kind}.png"))


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after", "compare", "verify",
                                         "approved", "corrected", "geometry_compare", "geometry_verify"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    phase = args.phase
    OUTPUT = args.output_dir
    if phase == "compare":
        comparison()
    elif phase == "geometry_compare":
        comparison("approved", "corrected")
    elif phase == "verify":
        verify()
    elif phase == "geometry_verify":
        verify("approved", "corrected")
    else:
        render_cards(phase)
    print(OUTPUT)


def verify(before_phase: str = "before", after_phase: str = "after") -> None:
    app = QApplication.instance() or QApplication([])
    report = {}
    for kind, card_rect in (("installed", QRectF(6, 12, 154, 242)),
                            ("selection", QRectF(3, 3, 160, 218))):
        art = QRectF(card_rect.left() + 28, card_rect.top() + 67,
                     card_rect.width() - 56, card_rect.height() * .42 - 22)
        report[kind] = {}
        for family in FAMILIES:
            before = QImage(str(OUTPUT / f"{before_phase}_{kind}_{family}.png"))
            after = QImage(str(OUTPUT / f"{after_phase}_{kind}_{family}.png"))
            assert not before.isNull() and before.size() == after.size()
            points = [(x, y) for y in range(before.height()) for x in range(before.width())
                      if before.pixel(x, y) != after.pixel(x, y)]
            assert points
            assert all(art.contains(x + .5, y + .5) for x, y in points), (kind, family)
            report[kind][family] = {"changed_pixels": len(points),
                                    "outside_art_changes": 0, "bounds": _bounds(points)}
    report["assets"] = {}
    preview = QImage(1280, 240, QImage.Format.Format_ARGB32)
    preview.fill(QColor("#a8b5bd"))
    painter = QPainter(preview)
    for col, family in enumerate(FREIGHT_ASSETS):
        image = QImage(320, 240, QImage.Format.Format_ARGB32)
        image.fill(0)
        p = QPainter(image)
        if family in FREIGHT_SVG_ASSETS:
            _renderer(family).render(p)
        else:
            draw_freight_art(p, QRectF(0, 0, 320, 240), family=family)
        p.end()
        points = [(x, y) for y in range(240) for x in range(320) if image.pixelColor(x, y).alpha()]
        bounds = _bounds(points)
        assert bounds[0] >= 10 and bounds[1] >= 10 and bounds[2] < 310 and bounds[3] < 230, (family, bounds)
        report["assets"][family] = {"alpha_bounds": bounds, "valid_qt_asset": True,
                                     "format": "svg" if family in FREIGHT_SVG_ASSETS else "png"}
        image.save(str(OUTPUT / f"asset_{family}.png"))
        painter.drawImage(col * 320, 0, image)
    painter.end()
    preview.save(str(OUTPUT / "assets_preview.png"))
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("All eight cards: zero changed pixels outside artwork; all SVGs have transparent padding.")


def _bounds(points):
    return [min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points), max(y for x, y in points)]


if __name__ == "__main__":
    main()
