"""Offscreen QA for Daily/Common Supply and Freight purchase cards."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from production_zero.core.commands import AddCash, CommandBus
from production_zero.core.state import GameState
from production_zero.core.supply import common_supply_offers
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.supply_view import SupplyView
from production_zero.ui.theme import APP_STYLESHEET


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "supply_regression_fix"
FAMILIES = ("truck", "train", "ship", "aircraft")


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
    state = GameState(rng_seed=1)
    bus = CommandBus(state)
    bus.dispatch(AddCash(1_000_000))
    view = SupplyView(state, bus, definitions)
    view.resize(1120, 700)
    view.show()
    QApplication.processEvents()
    assert _render(view).save(str(OUTPUT / f"{phase}_daily_supply.png"))

    view._show_section(1)
    QApplication.processEvents()
    assert _render(view).save(str(OUTPUT / f"{phase}_common_supply.png"))

    cards = []
    shop_images = {}
    for family in FAMILIES:
        offer = next(item for item in common_supply_offers(definitions)
                     if item.definition_id == f"freight.{family}")
        card = view._supply_card(offer, "common")
        cards.append(card)
        shop_images[family] = _render(card)
        assert shop_images[family].save(str(OUTPUT / f"{phase}_shop_{family}.png"))
    sheet = QImage(886, 316, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setFont(QFont("Segoe UI", 11))
    painter.setPen(QColor("#e1e9e7"))
    painter.drawText(14, 6, 858, 24, Qt.AlignmentFlag.AlignLeft, "FREIGHT SHOP CARDS · GLOBAL BUY ACTION")
    for index, family in enumerate(FAMILIES):
        painter.drawImage(QPoint(14 + index * 218, 34), shop_images[family])
    painter.end()
    assert sheet.save(str(OUTPUT / f"{phase}_freight_shop_cards.png"))
    view.close()
    for card in cards:
        card.deleteLater()
    view.deleteLater()


def verify() -> None:
    _app()
    definitions = load_card_definitions(ROOT / "src/production_zero/data/game_definitions.json")
    state = GameState(rng_seed=1)
    view = SupplyView(state, CommandBus(state), definitions)
    view.resize(1120, 700)
    view.show()
    QApplication.processEvents()
    outer = view.findChild(QScrollArea, "supplyDailyScroll")
    galleries = view.findChildren(QScrollArea, "supplyDailyOfferScroll")
    assert outer is not None and len(galleries) == 2
    for scroll in (outer, *galleries):
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.horizontalScrollBar().maximum() == 0
        assert scroll.verticalScrollBar().maximum() == 0
    common = view.findChild(QScrollArea, "commonSupplyScroll")
    assert common is not None and common.verticalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    before_common = QImage(str(OUTPUT / "before_common_supply.png"))
    after_common = QImage(str(OUTPUT / "after_common_supply.png"))
    assert before_common == after_common

    after_cards = {family: QImage(str(OUTPUT / f"after_shop_{family}.png")) for family in FAMILIES}
    button_rect = (111, 233, 79, 28)
    left, top, width, height = button_rect
    reference = after_cards["truck"].copy(left, top, width, height)
    for family in FAMILIES[1:]:
        assert after_cards[family].copy(left, top, width, height) == reference
    before_train = QImage(str(OUTPUT / "before_shop_train.png"))
    after_train = after_cards["train"]
    changed = [(x, y) for y in range(after_train.height()) for x in range(after_train.width())
               if before_train.pixel(x, y) != after_train.pixel(x, y)]
    assert changed
    assert all(left <= x < left + width and top <= y < top + height for x, y in changed)

    red = QColor("#c83a2b").rgb()
    assert any(after_train.pixel(x, y) == red for y in range(220) for x in range(after_train.width()))
    report = {
        "daily_scrolls": {"outer": "disabled", "freight": "disabled", "machines": "disabled"},
        "common_supply_pixel_changes": 0,
        "train_shop_changed_pixels": len(changed),
        "train_changes_confined_to_buy_button": True,
        "all_freight_buy_button_crops_identical": True,
        "train_red_card_accent_retained": True,
    }
    (OUTPUT / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    view.close()
    view.deleteLater()
    print("Supply regression QA passed.")


def main() -> None:
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after", "verify"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    OUTPUT = args.output_dir
    if args.phase == "verify":
        verify()
    else:
        render(args.phase)
    print(OUTPUT)


if __name__ == "__main__":
    main()
