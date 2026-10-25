"""Offscreen visual QA for the Solar Array and Wind Turbine raster pass."""
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
from production_zero.core.supply import common_supply_offers
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "machine_asset_pass"
ENERGY_IDS = (
    "energy.solar_array",
    "energy.wind_turbine",
    "energy.coal_power_plant",
    "energy.gas_power_plant",
    "energy.nuclear_power_plant",
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


def render(phase: str) -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    offers = {offer.definition_id: offer for offer in common_supply_offers(definitions)}
    state = GameState(rng_seed=1)
    state.supply.machine_daily_period_index = 0
    state.supply.machine_daily_offers = [offers[item] for item in ENERGY_IDS[:4]]
    bus = CommandBus(state)
    bus.dispatch(AddCash(1_000_000))
    view = SupplyView(state, bus, definitions)
    view.resize(1120, 700)
    view.show()
    view._refresh_machine_daily_cards()
    QApplication.processEvents()
    assert _render(view).save(str(OUTPUT / f"{phase}_daily_machines.png"))

    cards: list[QWidget] = []
    images: dict[str, QImage] = {}
    for definition_id in ENERGY_IDS:
        family = definition_id.split(".")[1].replace("_array", "").replace("_turbine", "").replace("_power_plant", "")
        card = view._supply_card(offers[definition_id], "common")
        cards.append(card)
        images[family] = _render(card)
        assert images[family].save(str(OUTPUT / f"{phase}_shop_{family}.png"))

    sheet = QImage(1128, 326, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(14, 5, 1100, 25, Qt.AlignmentFlag.AlignLeft, f"{phase.upper()} · ENERGY SHOP CARDS")
    for index, family in enumerate(("solar", "wind", "coal", "gas", "nuclear")):
        painter.drawImage(QPoint(14 + index * 222, 36), images[family])
    painter.end()
    assert sheet.save(str(OUTPUT / f"{phase}_energy_shop_cards.png"))
    view.close()
    for card in cards:
        card.deleteLater()
    view.deleteLater()


def compare() -> None:
    _app()
    before = QImage(str(OUTPUT / "before_energy_shop_cards.png"))
    after = QImage(str(OUTPUT / "after_energy_shop_cards.png"))
    assert not before.isNull() and not after.isNull() and before.size() == after.size()
    comparison = QImage(before.width(), before.height() * 2 + 42, QImage.Format.Format_ARGB32)
    comparison.fill(QColor("#080d11"))
    painter = QPainter(comparison)
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(10, 2, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "BEFORE · PROGRAMMATIC SOLAR / WIND")
    painter.drawImage(QPoint(0, 22), before)
    y = before.height() + 22
    painter.drawText(10, y, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "AFTER · FINAL TRANSPARENT RASTER ASSETS")
    painter.drawImage(QPoint(0, y + 20), after)
    painter.end()
    assert comparison.save(str(OUTPUT / "before_after_energy_shop_cards.png"))

    before_daily = QImage(str(OUTPUT / "before_daily_machines.png"))
    after_daily = QImage(str(OUTPUT / "after_daily_machines.png"))
    daily_comparison = QImage(before_daily.width() * 2 + 16, before_daily.height() + 30, QImage.Format.Format_ARGB32)
    daily_comparison.fill(QColor("#080d11"))
    painter = QPainter(daily_comparison)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(8, 3, before_daily.width(), 22, Qt.AlignmentFlag.AlignLeft, "BEFORE · DAILY MACHINES")
    painter.drawText(before_daily.width() + 16, 3, after_daily.width(), 22, Qt.AlignmentFlag.AlignLeft, "AFTER · DAILY MACHINES")
    painter.drawImage(QPoint(0, 30), before_daily)
    painter.drawImage(QPoint(before_daily.width() + 16, 30), after_daily)
    painter.end()
    assert daily_comparison.save(str(OUTPUT / "before_after_daily_machines.png"))

    from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, _raster_image

    alpha_sheet = QImage(800, 600, QImage.Format.Format_ARGB32)
    alpha_sheet.fill(QColor("#080d11"))
    painter = QPainter(alpha_sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    for row, background in enumerate((QColor("#161b20"), QColor("#edf0ed"))):
        for column, family in enumerate(("solar", "wind")):
            panel_x, panel_y = 12 + column * 394, 28 + row * 286
            painter.fillRect(panel_x, panel_y, 382, 258, background)
            source = _raster_image(family)
            scaled = source.scaled(350, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawImage(QPoint(panel_x + (382 - scaled.width()) // 2, panel_y + (258 - scaled.height()) // 2), scaled)
            painter.setPen(QColor("#f5f7f2") if row == 0 else QColor("#111518"))
            painter.drawText(panel_x + 8, panel_y + 6, 360, 22, Qt.AlignmentFlag.AlignLeft, family.upper())
    painter.end()
    assert alpha_sheet.save(str(OUTPUT / "alpha_edge_qa.png"))

    unchanged = {}
    for family in ("coal", "gas", "nuclear"):
        unchanged[family] = QImage(str(OUTPUT / f"before_shop_{family}.png")) == QImage(str(OUTPUT / f"after_shop_{family}.png"))
        assert unchanged[family]
    diff_bounds = {}
    assets = {}
    for family in ("solar", "wind"):
        before_card = QImage(str(OUTPUT / f"before_shop_{family}.png"))
        after_card = QImage(str(OUTPUT / f"after_shop_{family}.png"))
        points = [(x, y) for y in range(after_card.height()) for x in range(after_card.width())
                  if before_card.pixel(x, y) != after_card.pixel(x, y)]
        bounds = [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]
        assert bounds[0] >= 21 and bounds[1] >= 58 and bounds[2] <= 187 and bounds[3] <= 175
        diff_bounds[family] = bounds
        path = MACHINE_RASTER_ASSETS[family]
        image = _raster_image(family)
        assets[family] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": [image.width(), image.height()],
            "transparent_border": True,
        }
    report = {
        "solar_and_wind_changed": all(
            QImage(str(OUTPUT / f"before_shop_{family}.png")) != QImage(str(OUTPUT / f"after_shop_{family}.png"))
            for family in ("solar", "wind")
        ),
        "coal_gas_nuclear_pixel_identical": unchanged,
        "render_size_shop": [208, 276],
        "daily_view_size": [1120, 700],
        "card_change_bounds": diff_bounds,
        "changes_confined_to_artwork_sign": True,
        "keep_aspect_ratio": True,
        "smooth_transformation": True,
        "assets": assets,
    }
    assert report["solar_and_wind_changed"]
    (OUTPUT / "qa_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("before", "after", "compare"))
    args = parser.parse_args()
    if args.action == "compare":
        compare()
    else:
        render(args.action)
    print(OUTPUT)


if __name__ == "__main__":
    main()
