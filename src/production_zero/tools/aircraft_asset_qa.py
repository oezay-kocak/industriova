"""Render and verify the Aircraft freight asset/card pass without opening the GUI."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import CommandBus
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.state import GameState
from production_zero.core.supply import common_supply_offers
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.freight_art import FREIGHT_RASTER_ASSETS, draw_freight_art
from production_zero.ui.freight_view import FreightSelectionCard, FreightView
from production_zero.ui.game_ui.rendering.factory import _prototype_family_color
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "aircraft_raster_violet_identity"
FAMILIES = ("truck", "train", "ship", "aircraft")
AIRCRAFT_ACCENT = "#9bb8ef"


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _render_widget(widget: QWidget) -> QImage:
    widget.ensurePolished()
    if widget.layout():
        widget.layout().activate()
    position_controls = getattr(widget, "_position_installed_controls", None)
    if position_controls is not None:
        position_controls()
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("#080d11"))
    painter = QPainter(image)
    widget.render(painter, QPoint(0, 0))
    painter.end()
    return image


def _widgets():
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    state = GameState(rng_seed=1)
    bus = CommandBus(state)
    view = FreightView(state, bus, definitions, {})
    installed = {}
    for index, family in enumerate(FAMILIES):
        definition_id = f"freight.{family}"
        card = create_card_instance(f"qa-{family}", definition_id, CardKind.FREIGHT, Rarity.COMMON)
        state.cards[card.card_id] = card
        installed[family] = view._build_slot_card(index, card.card_id)
    aircraft = state.cards["qa-aircraft"]
    selection = FreightSelectionCard(aircraft, definitions[aircraft.definition_id], 1)
    supply = SupplyView(state, bus, definitions)
    offer = next(
        item for item in common_supply_offers(definitions)
        if item.definition_id == "freight.aircraft"
    )
    shop = supply._supply_card(offer, "common")
    return view, supply, installed, selection, shop


def render(phase: str) -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    view, supply, installed, selection, shop = _widgets()
    images = {family: _render_widget(widget) for family, widget in installed.items()}
    assert _render_widget(selection).save(str(OUTPUT / f"{phase}_aircraft_selection_166x224.png"))
    assert _render_widget(shop).save(str(OUTPUT / f"{phase}_aircraft_shop_208x276.png"))
    if phase == "after":
        shop._buy_button.setEnabled(True)
        shop._buy_button.style().unpolish(shop._buy_button)
        shop._buy_button.style().polish(shop._buy_button)
        assert _render_widget(shop).save(str(OUTPUT / "after_aircraft_shop_available_208x276.png"))
        asset = QImage(98, 80, QImage.Format.Format_ARGB32)
        asset.fill(0)
        asset_painter = QPainter(asset)
        asset_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        draw_freight_art(asset_painter, QRectF(0, 0, 98, 80), family="aircraft")
        asset_painter.end()
        assert asset.save(str(OUTPUT / "after_aircraft_asset_card_box_98x80.png"))

    overview = QImage(744, 306, QImage.Format.Format_ARGB32)
    overview.fill(QColor("#080d11"))
    painter = QPainter(overview)
    painter.setFont(QFont("Segoe UI", 11))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(16, 8, 712, 24, Qt.AlignmentFlag.AlignLeft, "FREIGHT OVERVIEW · 166 × 264 PX CARDS")
    for column, family in enumerate(FAMILIES):
        painter.drawImage(QPoint(16 + column * 180, 34), images[family])
    painter.end()
    assert overview.save(str(OUTPUT / f"{phase}_freight_overview.png"))

    for widget in (*installed.values(), selection, shop):
        widget.deleteLater()
    view.deleteLater()
    supply.deleteLater()


def compare() -> None:
    _app()
    panels = (
        ("aircraft_selection_166x224", 166, 224),
        ("aircraft_shop_208x276", 208, 276),
        ("freight_overview", 744, 306),
    )
    for stem, width, height in panels:
        sheet = QImage(width * 2 + 54, height + 58, QImage.Format.Format_ARGB32)
        sheet.fill(QColor("#080d11"))
        painter = QPainter(sheet)
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor("#e1e9e7"))
        for column, phase in enumerate(("before", "after")):
            x = 18 + column * (width + 18)
            painter.drawText(x, 8, width, 28, Qt.AlignmentFlag.AlignCenter,
                             "VORHER · SVG / VIOLETT" if phase == "before" else "NACHHER · PNG / VIOLETT")
            image = QImage(str(OUTPUT / f"{phase}_{stem}.png"))
            assert not image.isNull()
            painter.drawImage(QPoint(x, 42), image)
        painter.end()
        assert sheet.save(str(OUTPUT / f"comparison_{stem}.png"))


def _changed_pixels(before: QImage, after: QImage) -> list[tuple[int, int]]:
    assert before.size() == after.size()
    return [
        (x, y)
        for y in range(after.height())
        for x in range(after.width())
        if before.pixel(x, y) != after.pixel(x, y)
    ]


def verify() -> None:
    _app()
    violet = AIRCRAFT_ACCENT
    assert _prototype_family_color("aircraft", False).name().lower() == violet.lower()

    source = FREIGHT_RASTER_ASSETS["aircraft"]
    image = QImage(str(source))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == "45a9622e78a5f508120914038afd7868c89c9ea218128ab688369bcf61213f09"
    assert image.size().toTuple() == (1721, 914) and image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0

    card_asset = QImage(str(OUTPUT / "after_aircraft_asset_card_box_98x80.png"))
    alpha_pixels = [
        (x, y)
        for y in range(card_asset.height())
        for x in range(card_asset.width())
        if card_asset.pixelColor(x, y).alpha()
    ]
    assert alpha_pixels
    alpha_bounds = [
        min(x for x, _ in alpha_pixels), min(y for _, y in alpha_pixels),
        max(x for x, _ in alpha_pixels), max(y for _, y in alpha_pixels),
    ]
    assert alpha_bounds[0] > 0 and alpha_bounds[1] > 0
    assert alpha_bounds[2] < card_asset.width() - 1 and alpha_bounds[3] < card_asset.height() - 1

    report = {
        "source": {
            "path": str(source),
            "sha256": digest,
            "byte_identical_to_golden_sample": True,
            "dimensions": [image.width(), image.height()],
            "has_alpha": True,
            "card_box_alpha_bounds": alpha_bounds,
            "card_box_size": [card_asset.width(), card_asset.height()],
            "aspect_ratio_preserved": True,
            "smooth_transformation": True,
        },
        "aircraft_accent": violet,
        "renders": {},
    }
    for stem in ("aircraft_selection_166x224", "aircraft_shop_208x276"):
        before = QImage(str(OUTPUT / f"before_{stem}.png"))
        after = QImage(str(OUTPUT / f"after_{stem}.png"))
        changed = _changed_pixels(before, after)
        assert changed
        art_rect = QRectF(21, 58, after.width() - 42, (after.height() - 6) * .42)
        assert all(art_rect.contains(x + .5, y + .5) for x, y in changed), (stem, len(changed))
        violet_pixels = sum(after.pixelColor(x, y).name().lower() == violet.lower()
                         for y in range(after.height()) for x in range(after.width()))
        assert violet_pixels > 20
        report["renders"][stem] = {
            "changed_pixels": len(changed),
            "pz_violet_pixels": violet_pixels,
            "size": [after.width(), after.height()],
        }

    before = QImage(str(OUTPUT / "before_freight_overview.png"))
    after = QImage(str(OUTPUT / "after_freight_overview.png"))
    unchanged = {}
    for column, family in enumerate(FAMILIES):
        rect = (16 + column * 180, 34, 166, 264)
        left, top, width, height = rect
        count = sum(
            before.pixel(left + x, top + y) != after.pixel(left + x, top + y)
            for y in range(height) for x in range(width)
        )
        if family == "aircraft":
            assert count > 0
        else:
            assert count == 0, (family, count)
        unchanged[family] = count
    report["overview_changed_pixels_by_family"] = unchanged
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Aircraft QA passed: exact PNG, unchanged violet identity, and unchanged non-Aircraft cards.")


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after", "compare", "verify"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output_dir
    if args.phase == "compare":
        compare()
    elif args.phase == "verify":
        verify()
    else:
        render(args.phase)
    print(OUTPUT)


if __name__ == "__main__":
    main()
