from __future__ import annotations

import os
import inspect
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.core.cards import RARITY_BONUS_RANGES_TENTHS, create_card_instance
from production_zero.core.commands import CommandBus
from production_zero.core.definitions import EnergyDefinition, MachineDefinition
from production_zero.core.enums import MachineType
from production_zero.core.enums import Rarity
from production_zero.core.inventory import CardInventoryRow
from production_zero.core.state import GameState
from production_zero.core.supply import SupplyOffer
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.factory_view_v2 import _display_card_title
from production_zero.ui.factory_view_v2 import machine_icon_for_definition, prototype_family_for_definition
from production_zero.ui.game_ui.rendering import factory as card_renderer
from production_zero.ui.game_ui.rendering.factory import _BLOCK_GLYPHS
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryView
from production_zero.ui.packs_view import PacksView
from production_zero.ui.resource_icons import KNOWN_ICON_KEYS, ResourceIconWidget, card_resource_icon_signature, energy_icon_signature
from production_zero.ui.supply_view import SupplyOfferCardFrame, SupplyView


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _definitions():
    return load_card_definitions(Path("src/production_zero/data/game_definitions.json"))


def _unique_definitions(definitions):
    return sorted({definition.definition_id: definition for definition in definitions.values()}.values(), key=lambda definition: definition.definition_id)


def _rarity_bonus(rarity: Rarity) -> int:
    lower, upper = RARITY_BONUS_RANGES_TENTHS[rarity]
    return (lower + upper) // 2


def _render_widget(widget, width: int, height: int) -> QImage:
    widget.resize(width, height)
    widget.ensurePolished()
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        widget.render(painter, QPoint(0, 0))
    finally:
        painter.end()
    return image


def _image_stats(image: QImage) -> tuple[int, int]:
    background = image.pixelColor(0, 0).rgba()
    unique = set()
    non_background = 0
    for y in range(image.height()):
        for x in range(image.width()):
            rgba = image.pixelColor(x, y).rgba()
            unique.add(rgba)
            if rgba != background:
                non_background += 1
    return non_background, len(unique)


def test_card_prototype_block_glyphs_cover_runtime_card_text() -> None:
    _app()
    definitions = _definitions()
    state = GameState(rng_seed=1)
    inventory = InventoryView(state, definitions, release_mode=False)
    supply = SupplyView(state, CommandBus(state), definitions)
    required = set()

    for definition in _unique_definitions(definitions):
        for rarity in Rarity:
            bonus = _rarity_bonus(rarity)
            card = create_card_instance(f"audit-{definition.definition_id}-{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus_tenths=bonus)
            row = CardInventoryRow(card, definition, quantity=12, status="Available")
            offer = SupplyOffer(f"audit:{definition.definition_id}:{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus, 100)
            data = supply._display_data_for_offer(offer)
            supply_card = SupplyOfferCardFrame()
            texts = (
                inventory._card_game_title(row).upper(),
                inventory._card_game_meta(row).upper(),
                inventory._card_game_detail(row).upper(),
                "AVAILABLE",
                _display_card_title(definition).upper(),
                data.rarity_label.upper(),
                supply_card._detail_text(data).upper(),
                supply_card._secondary_text(data).upper(),
            )
            for text in texts:
                required.update(char for char in text if char != " ")

    assert required <= set(_BLOCK_GLYPHS)


def test_every_runtime_card_resolves_renderable_icons_and_energy_semantics() -> None:
    _app()
    definitions = _definitions()
    state = GameState(rng_seed=2)
    inventory = InventoryView(state, definitions, release_mode=False)
    supply = SupplyView(state, CommandBus(state), definitions)

    for definition in _unique_definitions(definitions):
        card = create_card_instance(f"audit-{definition.definition_id}", definition.definition_id, definition.card_kind, Rarity.COMMON)
        row = CardInventoryRow(card, definition, quantity=1, status="Available")
        inventory_icon, inventory_accent, _ = inventory._icon_signature(row)
        _, supply_icon, supply_accent = supply._icon_signature(definition)
        assert inventory_icon in KNOWN_ICON_KEYS
        assert supply_icon in KNOWN_ICON_KEYS
        if isinstance(definition, EnergyDefinition):
            expected = energy_icon_signature(definition.energy_type.value)
            assert (inventory_icon, inventory_accent) == expected
            assert (supply_icon, supply_accent) == expected
            assert inventory._card_game_family(row) == definition.energy_type.value


def test_card_views_share_canonical_resource_icon_signature() -> None:
    _app()
    definitions = _definitions()
    state = GameState(rng_seed=4)
    inventory = InventoryView(state, definitions, release_mode=False)
    supply = SupplyView(state, CommandBus(state), definitions)
    packs = PacksView(state, CommandBus(state), definitions)

    for definition in _unique_definitions(definitions):
        card = create_card_instance(f"canonical-{definition.definition_id}", definition.definition_id, definition.card_kind, Rarity.COMMON)
        row = CardInventoryRow(card, definition, quantity=1, status="Available")
        icon_key, accent_key, icon_resource_id = card_resource_icon_signature(definition, card.definition_id)

        assert inventory._icon_signature(row) == (icon_key, accent_key, icon_resource_id)
        assert packs._icon_signature(card, definition) == (icon_key, accent_key, icon_resource_id)
        assert supply._icon_signature(definition) == (icon_resource_id, icon_key, accent_key)
        assert icon_key in KNOWN_ICON_KEYS


def test_recipe_and_machine_stage_visual_identity_is_resolved() -> None:
    _app()
    definitions = _definitions()

    for definition in _unique_definitions(definitions):
        if isinstance(definition, MachineDefinition) and definition.machine_type == MachineType.FABRICATOR:
            assert prototype_family_for_definition(definition) == "fabricator"
            assert machine_icon_for_definition(definition).value == "fabricator"


def test_card_visual_correction_removes_rail_badge_and_retired_recipe_pictograms() -> None:
    renderer_source = inspect.getsource(card_renderer.draw_machine_card_prototype)
    pictogram_source = inspect.getsource(card_renderer._draw_prototype_pictogram)

    assert "rarity_rail" not in renderer_source
    assert "stage_plate" not in renderer_source
    assert "_draw_prototype_block_text(painter, stage" not in renderer_source
    assert 'family.startswith("recipe_")' not in pictogram_source
    assert "schematic" not in renderer_source.lower()


def test_runtime_inventory_cards_render_nonblank_for_every_definition() -> None:
    _app()
    definitions = _definitions()
    state = GameState(rng_seed=3)
    inventory = InventoryView(state, definitions, release_mode=False)

    for definition in _unique_definitions(definitions):
        card = create_card_instance(f"audit-{definition.definition_id}", definition.definition_id, definition.card_kind, Rarity.COMMON)
        row = CardInventoryRow(card, definition, quantity=12, status="Available")
        widget = inventory._build_inventory_card(row, selected=False)
        non_background, unique_colors = _image_stats(_render_widget(widget, INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT))
        assert non_background >= 2000
        assert unique_colors >= 20


def test_resource_icon_renderer_covers_every_known_icon_key() -> None:
    _app()
    for icon_key in sorted(KNOWN_ICON_KEYS):
        icon = ResourceIconWidget(f"audit.{icon_key}", icon_key, "default", size=64)
        non_background, unique_colors = _image_stats(_render_widget(icon, 64, 64))
        assert non_background >= 350
        assert unique_colors >= 6
