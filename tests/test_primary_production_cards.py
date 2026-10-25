from pathlib import Path

from PySide6.QtGui import QImage

from production_zero.core.cards import create_card_instance
from production_zero.core.enums import CardKind, MachineType, Rarity
from production_zero.core.inventory import CardInventoryRow
from production_zero.data.definitions import load_card_definitions
from production_zero.ui.factory_view import PRIMARY_MACHINE_TYPES, PRODUCTION_STAGE_LABELS
from production_zero.ui.inventory_view import InventoryView
from production_zero.ui.machine_art import MACHINE_RASTER_ASSETS, MACHINE_RASTER_FALLBACKS, _raster_image


DEFINITIONS_PATH = Path("src/production_zero/data/game_definitions.json")


def test_primary_production_has_three_canonical_families_and_visible_names() -> None:
    definitions = load_card_definitions(DEFINITIONS_PATH)

    assert PRIMARY_MACHINE_TYPES == {
        MachineType.EXTRACTOR,
        MachineType.DRILLING,
        MachineType.AGRICULTURE,
    }
    assert {
        definitions["machine.extractor"].name,
        definitions["machine.drilling"].name,
        definitions["machine.agriculture"].name,
    } == {"Extractor", "Drilling Rig", "Harvester"}
    assert {PRODUCTION_STAGE_LABELS[family] for family in PRIMARY_MACHINE_TYPES} == {"Primary Production"}
    assert all(
        PRODUCTION_STAGE_LABELS[family] != "Primary Production"
        for family in (MachineType.PROCESSOR, MachineType.FABRICATOR, MachineType.ASSEMBLER)
    )


def test_drilling_rig_uses_its_final_transparent_asset_without_fallback() -> None:
    path = MACHINE_RASTER_ASSETS["drilling"]

    assert path == Path("src/production_zero/assets/machines/drilling_rig.png").resolve()
    assert "drilling" not in MACHINE_RASTER_FALLBACKS
    image = QImage(str(path))
    assert not image.isNull()
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    loaded = _raster_image("drilling")
    assert loaded.size() == image.size()
    assert loaded.hasAlphaChannel()


def test_machine_family_assets_resolve_explicitly_without_extractor_fallbacks() -> None:
    expected = {
        "extractor": Path("src/production_zero/assets/machines/extractor.png").resolve(),
        "drilling": Path("src/production_zero/assets/machines/drilling_rig.png").resolve(),
        "agriculture": Path("src/production_zero/assets/machines/agriculture.png").resolve(),
    }

    assert {family: MACHINE_RASTER_ASSETS[family] for family in expected} == expected
    assert MACHINE_RASTER_FALLBACKS == {}
    for family, path in expected.items():
        assert not QImage(str(path)).isNull(), path
        image = _raster_image(family)
        assert not image.isNull()
        assert image.width() > 0
        assert image.height() > 0


def test_harvester_uses_supplied_transparent_asset_through_standard_renderer() -> None:
    definitions = load_card_definitions(DEFINITIONS_PATH)
    path = MACHINE_RASTER_ASSETS["agriculture"]
    image = _raster_image("agriculture")

    assert definitions["machine.agriculture"].name == "Harvester"
    assert path.exists()
    assert image.size().width() == 1536
    assert image.size().height() == 1024
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    assert any(
        image.pixelColor(x, y).alpha() < 255
        for x in range(0, image.width(), 32)
        for y in range(0, image.height(), 32)
    )


def test_primary_family_target_partition_is_exact_and_disjoint() -> None:
    definitions = load_card_definitions(DEFINITIONS_PATH)
    outputs = {
        definition_id: {
            option.output_resource
            for option in definitions[definition_id].available_production_options
        }
        for definition_id in ("machine.extractor", "machine.drilling", "machine.agriculture")
    }

    assert len(outputs["machine.extractor"]) == 37
    assert outputs["machine.drilling"] == {"crude_oil", "natural_gas"}
    assert len(outputs["machine.agriculture"]) == 10
    assert outputs["machine.extractor"].isdisjoint(outputs["machine.drilling"])
    assert outputs["machine.extractor"].isdisjoint(outputs["machine.agriculture"])
    assert outputs["machine.drilling"].isdisjoint(outputs["machine.agriculture"])


def test_inventory_primary_production_filter_membership_is_exact() -> None:
    definitions = load_card_definitions(DEFINITIONS_PATH)

    def filter_label(definition_id: str) -> str:
        definition = definitions[definition_id]
        row = CardInventoryRow(
            card=create_card_instance("test", definition_id, CardKind.MACHINE, Rarity.COMMON),
            definition=definition,
            quantity=1,
            status="Available",
        )
        return InventoryView._row_type_filter_label(None, row)

    machine_ids = {
        "machine.extractor",
        "machine.drilling",
        "machine.agriculture",
        "machine.processor",
        "machine.fabricator",
        "machine.assembler",
    }
    assert {
        definition_id
        for definition_id in machine_ids
        if filter_label(definition_id) == "Primary Production"
    } == {"machine.extractor", "machine.drilling", "machine.agriculture"}
    assert all(
        filter_label(definition_id) != "Primary Production"
        for definition_id in ("machine.processor", "machine.fabricator", "machine.assembler")
    )
