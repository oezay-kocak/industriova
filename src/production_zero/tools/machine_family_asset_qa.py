"""Offscreen QA for the Extractor, Processor, Fabricator, and Assembler art pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from production_zero.core.commands import AddCash, CommandBus
from production_zero.core.state import GameState
from production_zero.core.enums import Rarity
from production_zero.core.supply import SupplyOffer, common_card_price, common_supply_offers
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "machine_family_asset_pass"
TARGETS = (
    ("extractor", "machine.extractor"),
    ("fabricator", "machine.fabricator"),
    ("processor", "machine.processor"),
    ("assembler", "machine.assembler"),
)
EXTRACTOR_IDS = ("machine.extractor",)
CONTROLS = (
    ("solar", "energy.solar_array"),
    ("wind", "energy.wind_turbine"),
    ("coal", "energy.coal_power_plant"),
    ("gas", "energy.gas_power_plant"),
    ("nuclear", "energy.nuclear_power_plant"),
    ("truck", "freight.truck"),
    ("train", "freight.train"),
    ("ship", "freight.ship"),
    ("aircraft", "freight.aircraft"),
)


def _app() -> QApplication:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    app.setStyleSheet(APP_STYLESHEET)
    return app


def _render(widget: QWidget) -> QImage:
    widget.ensurePolished()
    if widget.layout():
        widget.layout().activate()
    QApplication.processEvents()
    image = QImage(widget.size(), QImage.Format.Format_ARGB32)
    image.fill(QColor("#080d11"))
    painter = QPainter(image)
    widget.render(painter, QPoint())
    painter.end()
    return image


def _sheet(title: str, images: list[tuple[str, QImage]], columns: int) -> QImage:
    rows = (len(images) + columns - 1) // columns
    sheet = QImage(14 + columns * 222, 36 + rows * 294, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(14, 5, sheet.width() - 28, 25, Qt.AlignmentFlag.AlignLeft, title)
    for index, (_label, image) in enumerate(images):
        painter.drawImage(QPoint(14 + (index % columns) * 222, 36 + (index // columns) * 294), image)
    painter.end()
    return sheet


def render(phase: str) -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    offers = {offer.definition_id: offer for offer in common_supply_offers(definitions)}
    for definition_id in EXTRACTOR_IDS:
        if definition_id not in offers:
            definition = definitions[definition_id]
            offers[definition_id] = SupplyOffer(
                offer_id=f"qa:{definition_id}",
                definition_id=definition_id,
                card_kind=definition.card_kind,
                rarity=Rarity.COMMON,
                bonus_tenths=0,
                price_cash=common_card_price(definition),
            )
    state = GameState(rng_seed=1)
    state.supply.machine_daily_period_index = 0
    state.supply.machine_daily_offers = [offers[definition_id] for _family, definition_id in TARGETS]
    bus = CommandBus(state)
    bus.dispatch(AddCash(1_000_000))
    view = SupplyView(state, bus, definitions)
    view.resize(1120, 700)
    view.show()
    view._refresh_machine_daily_cards()
    QApplication.processEvents()
    assert _render(view).save(str(OUTPUT / f"{phase}_daily_machine_families.png"))

    cards: list[QWidget] = []
    target_images = []
    for family, definition_id in TARGETS:
        card = view._supply_card(offers[definition_id], "common")
        cards.append(card)
        image = _render(card)
        target_images.append((family, image))
        assert image.save(str(OUTPUT / f"{phase}_common_{family}.png"))
    assert _sheet(f"{phase.upper()} · COMMON SUPPLY MACHINE CARDS", target_images, 4).save(
        str(OUTPUT / f"{phase}_common_machine_cards.png")
    )

    mk_images = []
    for definition_id in EXTRACTOR_IDS:
        card = view._supply_card(offers[definition_id], "common")
        cards.append(card)
        mk_images.append((definition_id, _render(card)))
    assert _sheet(f"{phase.upper()} · EXTRACTOR FAMILY", mk_images, 3).save(
        str(OUTPUT / f"{phase}_extractor_mks.png")
    )

    control_images = []
    for family, definition_id in CONTROLS:
        card = view._supply_card(offers[definition_id], "common")
        cards.append(card)
        image = _render(card)
        control_images.append((family, image))
        assert image.save(str(OUTPUT / f"{phase}_control_{family}.png"))
    assert _sheet(f"{phase.upper()} · UNCHANGED ENERGY / FREIGHT CONTROLS", control_images, 5).save(
        str(OUTPUT / f"{phase}_control_cards.png")
    )
    view.close()
    for card in cards:
        card.deleteLater()
    view.deleteLater()


def compare() -> None:
    _app()
    before = QImage(str(OUTPUT / "before_common_machine_cards.png"))
    after = QImage(str(OUTPUT / "after_common_machine_cards.png"))
    comparison = QImage(before.width(), before.height() * 2 + 42, QImage.Format.Format_ARGB32)
    comparison.fill(QColor("#080d11"))
    painter = QPainter(comparison)
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(10, 2, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "BEFORE · PROGRAMMATIC MACHINE ART")
    painter.drawImage(QPoint(0, 22), before)
    y = before.height() + 22
    painter.drawText(10, y, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "AFTER · FINAL TRANSPARENT RASTER ART")
    painter.drawImage(QPoint(0, y + 20), after)
    painter.end()
    assert comparison.save(str(OUTPUT / "before_after_machine_families.png"))

    from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, _raster_image

    diffs = {}
    buttons = []
    for family, _definition_id in TARGETS:
        old = QImage(str(OUTPUT / f"before_common_{family}.png"))
        new = QImage(str(OUTPUT / f"after_common_{family}.png"))
        points = [(x, y) for y in range(new.height()) for x in range(new.width()) if old.pixel(x, y) != new.pixel(x, y)]
        bounds = [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]
        assert bounds[0] >= 21 and bounds[1] >= 58 and bounds[2] <= 187 and bounds[3] <= 175
        diffs[family] = bounds
        buttons.append(new.copy(111, 233, 79, 28))
    assert all(button == buttons[0] for button in buttons[1:])

    controls = {}
    for family, _definition_id in CONTROLS:
        controls[family] = QImage(str(OUTPUT / f"before_control_{family}.png")) == QImage(str(OUTPUT / f"after_control_{family}.png"))
        assert controls[family]

    alpha_sheet = QImage(900, 680, QImage.Format.Format_ARGB32)
    alpha_sheet.fill(QColor("#080d11"))
    painter = QPainter(alpha_sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    for index, (family, _definition_id) in enumerate(TARGETS):
        source = _raster_image(family)
        for row, background in enumerate((QColor("#161b20"), QColor("#edf0ed"))):
            x, y = 10 + (index % 2) * 445, 10 + (index // 2) * 330 + row * 155
            painter.fillRect(x, y, 435, 145, background)
            scaled = source.scaled(405, 130, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawImage(QPoint(x + (435 - scaled.width()) // 2, y + (145 - scaled.height()) // 2), scaled)
    painter.end()
    assert alpha_sheet.save(str(OUTPUT / "alpha_edge_qa.png"))

    report = {
        "changes_confined_to_artwork_sign": True,
        "card_change_bounds": diffs,
        "energy_and_freight_controls_pixel_identical": controls,
        "global_buy_buttons_pixel_identical": True,
        "keep_aspect_ratio": True,
        "smooth_transformation": True,
        "smooth_pixmap_transform": True,
        "assets": {
            family: {
                "path": str(MACHINE_RASTER_ASSETS[family].relative_to(ROOT)),
                "sha256": hashlib.sha256(MACHINE_RASTER_ASSETS[family].read_bytes()).hexdigest(),
                "size": [_raster_image(family).width(), _raster_image(family).height()],
            }
            for family, _definition_id in TARGETS
        },
    }
    (OUTPUT / "qa_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("before", "after", "compare"))
    args = parser.parse_args()
    compare() if args.action == "compare" else render(args.action)
    print(OUTPUT)


if __name__ == "__main__":
    main()
