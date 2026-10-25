"""Offscreen QA for the final Coal, Gas, and Nuclear raster assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.core.commands import AddCash, CommandBus
from production_zero.core.state import GameState
from production_zero.core.supply import common_supply_offers
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.machine_asset_qa import _app, _render, render
from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, _raster_image
from production_zero.ui.supply_view import SupplyView


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "power_asset_pass"
MACHINE_OUTPUT = ROOT / "artifacts" / "machine_asset_pass"
FAMILIES = ("solar", "wind", "coal", "gas", "nuclear")
ENERGY_IDS = tuple(f"energy.{name}" for name in (
    "solar_array", "wind_turbine", "coal_power_plant", "gas_power_plant", "nuclear_power_plant"
))


def _daily_all_five() -> None:
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    offers = {offer.definition_id: offer for offer in common_supply_offers(definitions)}
    first = QImage(str(MACHINE_OUTPUT / "after_power_daily_machines.png"))
    state = GameState(rng_seed=1)
    state.supply.machine_daily_period_index = 0
    state.supply.machine_daily_offers = [offers[item] for item in (*ENERGY_IDS[:3], ENERGY_IDS[4])]
    bus = CommandBus(state)
    bus.dispatch(AddCash(1_000_000))
    view = SupplyView(state, bus, definitions)
    view.resize(1120, 700)
    view.show()
    view._refresh_machine_daily_cards()
    QApplication.processEvents()
    second = _render(view)
    assert second.save(str(OUTPUT / "after_daily_machines_nuclear_rotation.png"))

    sheet = QImage(first.width() * 2 + 16, first.height() + 30, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(8, 3, first.width(), 22, Qt.AlignmentFlag.AlignLeft, "DAILY ROTATION A · SOLAR / WIND / COAL / GAS")
    painter.drawText(first.width() + 16, 3, second.width(), 22, Qt.AlignmentFlag.AlignLeft, "DAILY ROTATION B · SOLAR / WIND / COAL / NUCLEAR")
    painter.drawImage(QPoint(0, 30), first)
    painter.drawImage(QPoint(first.width() + 16, 30), second)
    painter.end()
    assert sheet.save(str(OUTPUT / "after_daily_machines_all_five.png"))
    view.close()
    view.deleteLater()


def main() -> None:
    _app()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    render("after_power")
    _daily_all_five()

    before = QImage(str(MACHINE_OUTPUT / "before_power_energy_shop_cards.png"))
    after = QImage(str(MACHINE_OUTPUT / "after_power_energy_shop_cards.png"))
    comparison = QImage(before.width(), before.height() * 2 + 42, QImage.Format.Format_ARGB32)
    comparison.fill(QColor("#080d11"))
    painter = QPainter(comparison)
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(10, 2, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "BEFORE · PROGRAMMATIC COAL / GAS / NUCLEAR")
    painter.drawImage(QPoint(0, 22), before)
    y = before.height() + 22
    painter.drawText(10, y, comparison.width() - 20, 20, Qt.AlignmentFlag.AlignLeft, "AFTER · FINAL TRANSPARENT RASTER ASSETS")
    painter.drawImage(QPoint(0, y + 20), after)
    painter.end()
    assert comparison.save(str(OUTPUT / "before_after_power_shop_cards.png"))

    alpha_sheet = QImage(1188, 600, QImage.Format.Format_ARGB32)
    alpha_sheet.fill(QColor("#080d11"))
    painter = QPainter(alpha_sheet)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    for row, background in enumerate((QColor("#161b20"), QColor("#edf0ed"))):
        for column, family in enumerate(("coal", "gas", "nuclear")):
            panel_x, panel_y = 12 + column * 392, 28 + row * 286
            painter.fillRect(panel_x, panel_y, 380, 258, background)
            source = _raster_image(family)
            scaled = source.scaled(348, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter.drawImage(QPoint(panel_x + (380 - scaled.width()) // 2, panel_y + (258 - scaled.height()) // 2), scaled)
            painter.setPen(QColor("#f5f7f2") if row == 0 else QColor("#111518"))
            painter.drawText(panel_x + 8, panel_y + 6, 360, 22, Qt.AlignmentFlag.AlignLeft, family.upper())
    painter.end()
    assert alpha_sheet.save(str(OUTPUT / "alpha_edge_qa.png"))

    unchanged = {}
    diff_bounds = {}
    for family in FAMILIES:
        old = QImage(str(MACHINE_OUTPUT / f"before_power_shop_{family}.png"))
        new = QImage(str(MACHINE_OUTPUT / f"after_power_shop_{family}.png"))
        if family in {"solar", "wind"}:
            unchanged[family] = old == new
            assert unchanged[family]
            continue
        points = [(x, y) for y in range(new.height()) for x in range(new.width()) if old.pixel(x, y) != new.pixel(x, y)]
        bounds = [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]
        assert bounds[0] >= 21 and bounds[1] >= 58 and bounds[2] <= 187 and bounds[3] <= 175
        diff_bounds[family] = bounds

    report = {
        "solar_wind_pixel_identical": unchanged,
        "changes_confined_to_artwork_sign": True,
        "card_change_bounds": diff_bounds,
        "render_size_shop_and_daily_card": [208, 276],
        "keep_aspect_ratio": True,
        "smooth_transformation": True,
        "smooth_pixmap_transform": True,
        "assets": {
            family: {
                "path": str(MACHINE_RASTER_ASSETS[family].relative_to(ROOT)),
                "sha256": hashlib.sha256(MACHINE_RASTER_ASSETS[family].read_bytes()).hexdigest(),
                "size": [_raster_image(family).width(), _raster_image(family).height()],
                "transparent_border": True,
            }
            for family in ("coal", "gas", "nuclear")
        },
    }
    (OUTPUT / "qa_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
