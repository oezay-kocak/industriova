from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.inventory import CardInventoryRow
from production_zero.core.state import GameState
from production_zero.data.definitions import load_card_definitions
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryView


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = ROOT / "artifacts" / "card_visual_sheets"
SHEET_PATH = ARTIFACT_DIR / "card_visual_correction_sheet.png"

GROUPS = (
    (
        "ENERGY",
        (
            "energy.solar_array",
            "energy.wind_turbine",
            "energy.coal_power_plant",
            "energy.gas_power_plant",
            "energy.nuclear_power_plant",
        ),
    ),
    (
        "MACHINE",
        (
            "machine.extractor",
            "machine.processor",
            "machine.fabricator",
            "machine.assembler",
        ),
    ),
    (
        "FREIGHT",
        (
            "freight.truck",
            "freight.train",
            "freight.ship",
            "freight.aircraft",
        ),
    ),

)


def _kind_for_definition_id(definition_id: str) -> CardKind:
    if definition_id.startswith("energy."):
        return CardKind.ENERGY
    if definition_id.startswith("freight."):
        return CardKind.FREIGHT
    if definition_id.startswith("recipe."):
        raise ValueError("Recipe cards are retired")
    return CardKind.MACHINE


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    definitions = load_card_definitions(ROOT / "src" / "production_zero" / "data" / "game_definitions.json")
    inventory = InventoryView(GameState(rng_seed=1), definitions)

    margin = 28
    label_height = 30
    gap = 18
    row_height = label_height + INVENTORY_CARD_HEIGHT
    max_columns = max(len(definition_ids) for _label, definition_ids in GROUPS)
    width = margin * 2 + max_columns * INVENTORY_CARD_WIDTH + (max_columns - 1) * gap
    height = margin * 2 + len(GROUPS) * row_height + (len(GROUPS) - 1) * gap
    sheet = QImage(width, height, QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#080d11"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    font = QFont("Segoe UI", 13)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#edf6f2"))

    for row_index, (label, definition_ids) in enumerate(GROUPS):
        y = margin + row_index * (row_height + gap)
        painter.drawText(margin, y, width - margin * 2, label_height, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        for column, definition_id in enumerate(definition_ids):
            definition = definitions[definition_id]
            card = create_card_instance(f"visual-{definition_id}", definition_id, _kind_for_definition_id(definition_id), Rarity.COMMON)
            row = CardInventoryRow(card, definition, quantity=1, status="Available")
            widget = inventory._build_inventory_card(row, selected=False)
            widget.resize(INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
            widget.ensurePolished()
            x = margin + column * (INVENTORY_CARD_WIDTH + gap)
            widget.render(painter, QPoint(x, y + label_height))

    painter.end()
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(str(SHEET_PATH))
    print(SHEET_PATH)


if __name__ == "__main__":
    main()
