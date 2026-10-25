from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QFrame, QWidget

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from production_zero.core.cards import RARITY_BONUS_RANGES_TENTHS, create_card_instance
from production_zero.core.commands import CommandBus
from production_zero.core.definitions import CardDefinition, EnergyDefinition, FreightDefinition, MachineDefinition
from production_zero.core.enums import Rarity
from production_zero.core.inventory import CardInventoryRow
from production_zero.core.state import GameState
from production_zero.core.supply import SupplyOffer
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.factory_view_v2 import _display_card_title, prototype_family_for_definition
from production_zero.ui.game_ui.rendering.factory import _BLOCK_GLYPHS, _PROTOTYPE_FAMILY_COLORS
from production_zero.ui.inventory_view import INVENTORY_CARD_HEIGHT, INVENTORY_CARD_WIDTH, InventoryView
from production_zero.ui.resource_icons import ACCENT_COLORS, KNOWN_ICON_KEYS, ResourceIconWidget, energy_icon_signature, resource_accent_key, resource_icon_key
from production_zero.ui.supply_view import COMMON_SUPPLY_CARD_HEIGHT, COMMON_SUPPLY_CARD_WIDTH, SupplyOfferCardFrame, SupplyView


OUT_DIR = ROOT / "artifacts" / "card_audit"
DEFINITIONS_PATH = ROOT / "src" / "production_zero" / "data" / "game_definitions.json"


@dataclass(frozen=True)
class RenderVariant:
    renderer: str
    definition_id: str
    rarity: str
    image_path: str
    non_background_pixels: int
    unique_colors: int


def unique_definitions(definitions: dict[str, CardDefinition]) -> list[CardDefinition]:
    return sorted({definition.definition_id: definition for definition in definitions.values()}.values(), key=lambda item: item.definition_id)


def rarity_bonus(rarity: Rarity) -> int:
    lower, upper = RARITY_BONUS_RANGES_TENTHS[rarity]
    return (lower + upper) // 2


def image_stats(image: QImage) -> tuple[int, int]:
    background = image.pixelColor(0, 0).rgba()
    unique: set[int] = set()
    non_background = 0
    for y in range(image.height()):
        for x in range(image.width()):
            rgba = image.pixelColor(x, y).rgba()
            unique.add(rgba)
            if rgba != background:
                non_background += 1
    return non_background, len(unique)


def render_widget(widget: QWidget, width: int, height: int) -> QImage:
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


def render_resource_icon(icon_key: str, accent_key: str = "default") -> tuple[int, int]:
    widget = ResourceIconWidget(f"audit.{icon_key}", icon_key, accent_key, size=64)
    return image_stats(render_widget(widget, 64, 64))


def render_atlas(images: list[tuple[str, QImage]], prefix: str, *, columns: int = 8, rows_per_page: int = 10) -> list[Path]:
    if not images:
        return []
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cell_width = max(image.width() for _, image in images) + 22
    cell_height = max(image.height() for _, image in images) + 34
    per_page = columns * rows_per_page
    paths: list[Path] = []
    for page_index in range(0, len(images), per_page):
        chunk = images[page_index : page_index + per_page]
        page = QImage(columns * cell_width, rows_per_page * cell_height, QImage.Format.Format_ARGB32)
        page.fill(QColor("#101515"))
        painter = QPainter(page)
        try:
            painter.setPen(QColor("#dbe6df"))
            for index, (label, image) in enumerate(chunk):
                column = index % columns
                row = index // columns
                x = column * cell_width + 11
                y = row * cell_height + 8
                painter.drawImage(QPoint(x, y), image)
                painter.drawText(
                    QRectF(x, y + image.height() + 4, image.width(), 24),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label[:34],
                )
        finally:
            painter.end()
        path = OUT_DIR / f"{prefix}_{page_index // per_page + 1:02d}.png"
        page.save(str(path))
        paths.append(path)
    return paths


def audit_definitions(definitions: dict[str, CardDefinition]) -> tuple[list[str], list[str]]:
    raw = json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))
    raw_ids = [item["id"] for item in raw["cards"]]
    issues: list[str] = []
    warnings: list[str] = []
    for definition_id, count in Counter(raw_ids).items():
        if count > 1:
            issues.append(f"duplicate card id in game_definitions.json: {definition_id}")
    for definition in unique_definitions(definitions):
        if not definition.definition_id.strip():
            issues.append("card with empty definition_id")
        if not definition.name.strip():
            issues.append(f"{definition.definition_id}: missing display name")
        if isinstance(definition, MachineDefinition):
            for option in definition.available_production_options:
                if option.icon_key not in KNOWN_ICON_KEYS:
                    issues.append(f'{definition.definition_id}/{option.production_id}: unknown production icon_key {option.icon_key!r}')
                if option.accent_key not in ACCENT_COLORS and resource_accent_key(option.accent_key) == 'default':
                    warnings.append(f'{definition.definition_id}/{option.production_id}: generic production accent_key {option.accent_key!r}')
    return issues, warnings


def audit_symbols(definitions: dict[str, CardDefinition], inventory: InventoryView, supply: SupplyView) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    ambiguous: list[str] = []
    seen_icons: dict[str, list[str]] = defaultdict(list)
    for definition in unique_definitions(definitions):
        card = create_card_instance(f"audit-{definition.definition_id}", definition.definition_id, definition.card_kind, Rarity.COMMON)
        row = CardInventoryRow(card=card, definition=definition, quantity=1, status="Available")
        inventory_icon, inventory_accent, inventory_resource = inventory._icon_signature(row)
        supply_resource, supply_icon, supply_accent = supply._icon_signature(definition)
        for context, icon_key, accent_key in (
            ("inventory", inventory_icon, inventory_accent),
            ("supply", supply_icon, supply_accent),
        ):
            if icon_key not in KNOWN_ICON_KEYS:
                issues.append(f"{definition.definition_id}: {context} icon_key {icon_key!r} is not renderable")
            if accent_key not in ACCENT_COLORS:
                issues.append(f"{definition.definition_id}: {context} accent_key {accent_key!r} is not known")
        seen_icons[f"inventory:{inventory_icon}"].append(definition.definition_id)
        seen_icons[f"supply:{supply_icon}"].append(definition.definition_id)
        if isinstance(definition, EnergyDefinition):
            expected_icon, expected_accent = energy_icon_signature(definition.energy_type.value)
            if (inventory_icon, inventory_accent) != (expected_icon, expected_accent):
                issues.append(
                    f"{definition.definition_id}: inventory energy icon {(inventory_icon, inventory_accent)} "
                    f"does not match expected {(expected_icon, expected_accent)}"
                )
            if (supply_icon, supply_accent) != (expected_icon, expected_accent):
                issues.append(
                    f"{definition.definition_id}: supply energy icon {(supply_icon, supply_accent)} "
                    f"does not match expected {(expected_icon, expected_accent)}"
                )
            if inventory._card_game_family(row) != definition.energy_type.value:
                issues.append(f"{definition.definition_id}: visible inventory prototype family {inventory._card_game_family(row)!r} is not energy type {definition.energy_type.value!r}")
            if prototype_family_for_definition(definition) != definition.energy_type.value:
                issues.append(f"{definition.definition_id}: visible supply prototype family {prototype_family_for_definition(definition)!r} is not energy type {definition.energy_type.value!r}")
        if isinstance(definition, MachineDefinition) and definition.machine_type.value == "fabricator":
            if prototype_family_for_definition(definition) != "fabricator":
                issues.append(f"{definition.definition_id}: visible machine prototype family is not fabricator")
        if inventory_resource == definition.definition_id and inventory_icon == "hex":
            ambiguous.append(f"{definition.definition_id}: inventory icon falls back to generic hex")
        if supply_resource == definition.definition_id and supply_icon == "hex":
            ambiguous.append(f"{definition.definition_id}: supply icon falls back to generic hex")
    for key, ids in sorted(seen_icons.items()):
        if key.endswith(":hex") and len(ids) > 5:
            ambiguous.append(f"{key} is shared by {len(ids)} cards, first examples: {', '.join(ids[:8])}")
    return issues, ambiguous


def prototype_texts(definition: CardDefinition, rarity: Rarity, inventory: InventoryView, supply: SupplyView) -> list[str]:
    bonus = rarity_bonus(rarity)
    card = create_card_instance(f"audit-{definition.definition_id}-{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus_tenths=bonus)
    row = CardInventoryRow(card=card, definition=definition, quantity=12, status="Available")
    offer = SupplyOffer(f"audit:{definition.definition_id}:{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus, 100)
    data = supply._display_data_for_offer(offer)
    supply_card = SupplyOfferCardFrame()
    return [
        inventory._card_game_title(row).upper(),
        inventory._card_game_meta(row).upper(),
        inventory._card_game_detail(row).upper(),
        "AVAILABLE",
        _display_card_title(definition).upper(),
        data.rarity_label.upper(),
        supply_card._detail_text(data).upper(),
        supply_card._secondary_text(data).upper(),
    ]


def audit_glyphs(definitions: dict[str, CardDefinition], inventory: InventoryView, supply: SupplyView) -> tuple[set[str], set[str], set[str], set[str]]:
    required: set[str] = set()
    for definition in unique_definitions(definitions):
        for rarity in Rarity:
            for text in prototype_texts(definition, rarity, inventory, supply):
                required.update(char for char in text if char != " ")
    supported = set(_BLOCK_GLYPHS)
    missing = required - supported
    unused = supported - required
    return required, supported, missing, unused


def render_card_variants(definitions: dict[str, CardDefinition], inventory: InventoryView, supply: SupplyView) -> tuple[list[RenderVariant], list[str], list[Path]]:
    variants: list[RenderVariant] = []
    suspicious: list[str] = []
    inventory_images: list[tuple[str, QImage]] = []
    supply_images: list[tuple[str, QImage]] = []
    for definition in unique_definitions(definitions):
        for rarity in Rarity:
            bonus = rarity_bonus(rarity)
            card = create_card_instance(f"audit-{definition.definition_id}-{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus_tenths=bonus)
            row = CardInventoryRow(card=card, definition=definition, quantity=12, status="Available")
            inventory_card = inventory._build_inventory_card(row, selected=False)
            inventory_image = render_widget(inventory_card, INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)
            non_background, unique_colors = image_stats(inventory_image)
            if non_background < 2000 or unique_colors < 20:
                suspicious.append(f"{definition.definition_id}/{rarity.value}: inventory render appears too sparse ({non_background} pixels, {unique_colors} colors)")
            inventory_images.append((f"INV {definition.definition_id} {rarity.value}", inventory_image))
            variants.append(RenderVariant("inventory", definition.definition_id, rarity.value, "", non_background, unique_colors))

            offer = SupplyOffer(f"audit:{definition.definition_id}:{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus, 100)
            data = supply._display_data_for_offer(offer)
            supply_card = SupplyOfferCardFrame()
            supply_card.bind_offer(data, source="common", state="available", button_text="BUY", can_buy=True)
            supply_image = render_widget(supply_card, COMMON_SUPPLY_CARD_WIDTH, COMMON_SUPPLY_CARD_HEIGHT)
            non_background, unique_colors = image_stats(supply_image)
            if non_background < 3000 or unique_colors < 20:
                suspicious.append(f"{definition.definition_id}/{rarity.value}: supply render appears too sparse ({non_background} pixels, {unique_colors} colors)")
            supply_images.append((f"SUP {definition.definition_id} {rarity.value}", supply_image))
            variants.append(RenderVariant("supply", definition.definition_id, rarity.value, "", non_background, unique_colors))
    inventory_atlas_paths = render_atlas(inventory_images, "inventory_cards")
    supply_atlas_paths = render_atlas(supply_images, "supply_cards", columns=6, rows_per_page=8)
    index_lines = ["renderer,page,row,column,definition_id,rarity"]
    for renderer, images, paths, columns, rows_per_page in (
        ("inventory", inventory_images, inventory_atlas_paths, 8, 10),
        ("supply", supply_images, supply_atlas_paths, 6, 8),
    ):
        per_page = columns * rows_per_page
        for index, (label, _) in enumerate(images):
            _, definition_id, rarity = label.split(" ", 2)
            page = index // per_page
            page_slot = index % per_page
            atlas_file = paths[page].name
            index_lines.append(f"{renderer},{atlas_file},{page_slot // columns},{page_slot % columns},{definition_id},{rarity}")
    (OUT_DIR / "card_atlas_index.csv").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    atlas_paths = [*inventory_atlas_paths, *supply_atlas_paths]
    return variants, suspicious, atlas_paths


def render_inventory_card_sample(inventory: InventoryView, definition: CardDefinition, rarity: Rarity) -> QImage:
    bonus = rarity_bonus(rarity)
    card = create_card_instance(f"comparison-{definition.definition_id}-{rarity.value}", definition.definition_id, definition.card_kind, rarity, bonus_tenths=bonus)
    row = CardInventoryRow(card=card, definition=definition, quantity=12, status="Available")
    return render_widget(inventory._build_inventory_card(row, selected=False), INVENTORY_CARD_WIDTH, INVENTORY_CARD_HEIGHT)


def render_comparison_sheets(definitions: dict[str, CardDefinition], inventory: InventoryView) -> list[Path]:
    samples = {
        "family_comparison": [
            "energy.solar_array",
            "energy.wind_turbine",
            "energy.coal_power_plant",
            "energy.gas_power_plant",
            "energy.nuclear_power_plant",
            "freight.truck",
            "freight.train",
            "freight.ship",
            "freight.aircraft",
            "machine.extractor",
            "machine.processor",
            "machine.fabricator",
            "machine.assembler",
        ],
        "stage_comparison": [
            "machine.extractor",
            "machine.processor",
            "machine.fabricator",
            "machine.assembler",
        ],
        "rarity_comparison": ["machine.fabricator"],
    }
    paths: list[Path] = []
    for prefix, definition_ids in samples.items():
        images: list[tuple[str, QImage]] = []
        if prefix == "rarity_comparison":
            definition = definitions[definition_ids[0]]
            images = [(rarity.value.upper(), render_inventory_card_sample(inventory, definition, rarity)) for rarity in Rarity]
        else:
            for definition_id in definition_ids:
                definition = definitions[definition_id]
                images.append((definition_id, render_inventory_card_sample(inventory, definition, Rarity.RARE)))
        paths.extend(render_atlas(images, prefix, columns=5, rows_per_page=3))
    return paths


def write_report(
    definitions: dict[str, CardDefinition],
    data_issues: list[str],
    data_warnings: list[str],
    symbol_issues: list[str],
    ambiguous: list[str],
    required: set[str],
    supported: set[str],
    missing: set[str],
    unused: set[str],
    variants: list[RenderVariant],
    render_suspicious: list[str],
    icon_render_issues: list[str],
    atlas_paths: list[Path],
    comparison_sheet_paths: list[Path],
) -> None:
    unique = unique_definitions(definitions)
    families = Counter()
    for definition in unique:
        if isinstance(definition, MachineDefinition):
            families[f'machine:{definition.machine_type.value}'] += 1
        elif isinstance(definition, EnergyDefinition):
            families[f'energy:{definition.energy_type.value}'] += 1
        elif isinstance(definition, FreightDefinition):
            families[f'freight:{definition.family.value}'] += 1
    summary = {
        "runtime_cards_audited": len(unique),
        "families": dict(sorted(families.items())),
        "unique_visual_variants_rendered": len(variants),
        "required_block_glyphs": "".join(sorted(required)),
        "supported_block_glyphs": "".join(sorted(supported)),
        "missing_block_glyphs": "".join(sorted(missing)),
        "unused_block_glyphs": "".join(sorted(unused)),
        "data_issues": data_issues,
        "data_warnings": data_warnings,
        "symbol_issues": symbol_issues,
        "ambiguous_cases": ambiguous,
        "render_suspicious": render_suspicious,
        "icon_render_issues": icon_render_issues,
        "atlas_paths": [str(path.relative_to(ROOT)) for path in atlas_paths],
        "comparison_sheet_paths": [str(path.relative_to(ROOT)) for path in comparison_sheet_paths],
    }
    (OUT_DIR / "card_system_audit_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    report = [
        "# Card System Full Audit",
        "",
        f"- Runtime cards audited: {summary['runtime_cards_audited']}",
        f"- Unique visual variants rendered: {summary['unique_visual_variants_rendered']}",
        f"- Card families/types: {json.dumps(summary['families'], sort_keys=True)}",
        f"- Required block glyphs: `{summary['required_block_glyphs']}`",
        f"- Supported block glyphs: `{summary['supported_block_glyphs']}`",
        f"- Missing block glyphs after fixes: `{summary['missing_block_glyphs'] or 'none'}`",
        f"- Unused block glyphs: `{summary['unused_block_glyphs'] or 'none'}`",
        "",
        "## Data Issues",
        *(f"- {item}" for item in data_issues or ["none"]),
        "",
        "## Data Warnings",
        *(f"- {item}" for item in data_warnings or ["none"]),
        "",
        "## Symbol Issues",
        *(f"- {item}" for item in symbol_issues or ["none"]),
        "",
        "## Render Suspicious",
        *(f"- {item}" for item in render_suspicious or ["none"]),
        "",
        "## Icon Render Issues",
        *(f"- {item}" for item in icon_render_issues or ["none"]),
        "",
        "## Ambiguous Cases",
        *(f"- {item}" for item in ambiguous[:80] or ["none"]),
    ]
    if len(ambiguous) > 80:
        report.append(f"- ... {len(ambiguous) - 80} more in card_system_audit_summary.json")
    report.extend(["", "## Comparison Sheets", *(f"- {path.relative_to(ROOT)}" for path in comparison_sheet_paths)])
    report.extend(["", "## Atlas Files", *(f"- {path.relative_to(ROOT)}" for path in atlas_paths)])
    (OUT_DIR / "card_system_audit.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    QApplication.instance() or QApplication([])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    definitions = load_card_definitions(DEFINITIONS_PATH)
    state = GameState(rng_seed=7)
    inventory = InventoryView(state, definitions)
    supply = SupplyView(state, CommandBus(state), definitions)
    data_issues, data_warnings = audit_definitions(definitions)
    symbol_issues, ambiguous = audit_symbols(definitions, inventory, supply)
    required, supported, missing, unused = audit_glyphs(definitions, inventory, supply)
    variants, render_suspicious, atlas_paths = render_card_variants(definitions, inventory, supply)
    comparison_sheet_paths = render_comparison_sheets(definitions, inventory)
    icon_render_issues = []
    for icon_key in sorted(KNOWN_ICON_KEYS):
        non_background, unique_colors = render_resource_icon(icon_key)
        if non_background < 350 or unique_colors < 6:
            icon_render_issues.append(f"{icon_key}: sparse icon render ({non_background} pixels, {unique_colors} colors)")
    write_report(
        definitions,
        data_issues,
        data_warnings,
        symbol_issues,
        ambiguous,
        required,
        supported,
        missing,
        unused,
        variants,
        render_suspicious,
        icon_render_issues,
        atlas_paths,
        comparison_sheet_paths,
    )
    print((OUT_DIR / "card_system_audit.md").relative_to(ROOT))
    print((OUT_DIR / "card_system_audit_summary.json").relative_to(ROOT))
    print(f"runtime_cards={len(unique_definitions(definitions))}")
    print(f"variants_rendered={len(variants)}")
    print(f"missing_glyphs={''.join(sorted(missing)) or 'none'}")
    print(f"data_issues={len(data_issues)} symbol_issues={len(symbol_issues)} render_suspicious={len(render_suspicious)} icon_render_issues={len(icon_render_issues)}")
    return 1 if data_issues or symbol_issues or missing or render_suspicious or icon_render_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
