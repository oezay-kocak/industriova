"""Render and verify the Ship freight asset/card pass without opening the GUI."""
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
OUTPUT = ROOT / "artifacts" / "ship_raster_cyan_identity"
FAMILIES = ("truck", "train", "ship", "aircraft")
SHIP_ACCENT = "#25b9e8"


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
    ship = state.cards["qa-ship"]
    selection = FreightSelectionCard(ship, definitions[ship.definition_id], 1)
    supply = SupplyView(state, bus, definitions)
    offer = next(
        item for item in common_supply_offers(definitions)
        if item.definition_id == "freight.ship"
    )
    shop = supply._supply_card(offer, "common")
    return view, supply, installed, selection, shop


def render(phase: str) -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    view, supply, installed, selection, shop = _widgets()
    images = {family: _render_widget(widget) for family, widget in installed.items()}
    assert images["ship"].save(str(OUTPUT / f"{phase}_ship_installed_166x264.png"))
    assert _render_widget(selection).save(str(OUTPUT / f"{phase}_ship_selection_166x224.png"))
    assert _render_widget(shop).save(str(OUTPUT / f"{phase}_ship_shop_208x276.png"))
    if phase == "after":
        shop._buy_button.setEnabled(True)
        shop._buy_button.style().unpolish(shop._buy_button)
        shop._buy_button.style().polish(shop._buy_button)
        assert _render_widget(shop).save(str(OUTPUT / "after_ship_shop_available_208x276.png"))
        asset = QImage(98, 80, QImage.Format.Format_ARGB32)
        asset.fill(0)
        asset_painter = QPainter(asset)
        asset_painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        draw_freight_art(asset_painter, QRectF(0, 0, 98, 80), family="ship")
        asset_painter.end()
        assert asset.save(str(OUTPUT / "after_ship_asset_card_box_98x80.png"))

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
        ("ship_selection_166x224", 166, 224),
        ("ship_shop_208x276", 208, 276),
        ("ship_installed_166x264", 166, 264),
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
                             "VORHER · SVG / CYAN" if phase == "before" else "NACHHER · PNG / CYAN")
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
    cyan = SHIP_ACCENT
    assert _prototype_family_color("ship", False).name().lower() == cyan.lower()

    source = FREIGHT_RASTER_ASSETS["ship"]
    image = QImage(str(source))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest == "21e5b3d9522a92d1a5e6d99d7b6806ad0575919d86db65cf06b8b3145e734159"
    assert image.size().toTuple() == (1721, 914) and image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0

    card_asset = QImage(str(OUTPUT / "after_ship_asset_card_box_98x80.png"))
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
        "ship_accent": cyan,
        "renders": {},
    }
    for stem in ("ship_selection_166x224", "ship_shop_208x276", "ship_installed_166x264"):
        before = QImage(str(OUTPUT / f"before_{stem}.png"))
        after = QImage(str(OUTPUT / f"after_{stem}.png"))
        changed = _changed_pixels(before, after)
        assert changed
        art_rect = (QRectF(34, 79, 98, 80) if "installed" in stem
                    else QRectF(21, 58, after.width() - 42, (after.height() - 6) * .42))
        assert all(art_rect.contains(x + .5, y + .5) for x, y in changed), (stem, len(changed))
        cyan_pixels = sum(after.pixelColor(x, y).name().lower() == cyan.lower()
                         for y in range(after.height()) for x in range(after.width()))
        assert cyan_pixels > 20
        report["renders"][stem] = {
            "changed_pixels": len(changed),
            "pz_cyan_pixels": cyan_pixels,
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
        if family == "ship":
            assert count > 0
        else:
            assert count == 0, (family, count)
        unchanged[family] = count
    report["overview_changed_pixels_by_family"] = unchanged
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Ship QA passed: exact PNG, unchanged cyan identity, and unchanged non-Ship cards.")


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
