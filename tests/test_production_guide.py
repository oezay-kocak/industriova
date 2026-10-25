from __future__ import annotations

from importlib.resources import files

import pytest

from production_zero.core.production_guide import ProductionGuideRecipeIndex
from production_zero.data.definitions import load_card_definitions


def _definitions():
    return load_card_definitions(files("production_zero.data") / "game_definitions.json")


def test_production_guide_reverse_index_derives_direct_used_in_relationships() -> None:
    index = ProductionGuideRecipeIndex(_definitions())

    used_in_outputs = {entry.production.output_resource for entry in index.used_in("steel_components")}

    assert "industrial_equipment" in used_in_outputs
    assert "mining_drill" in used_in_outputs
    assert "steel" not in used_in_outputs


def test_production_guide_reverse_index_handles_multi_input_and_rates() -> None:
    index = ProductionGuideRecipeIndex(_definitions())
    industrial_equipment = next(
        entry
        for entry in index.used_in("steel_components")
        if entry.production.output_resource == "industrial_equipment"
    )

    assert set(industrial_equipment.production.input_resources) == {
        "steel_components",
        "electrical_components",
        "iron_components",
    }
    assert industrial_equipment.production.input_resources["steel_components"] == pytest.approx(4)
    assert industrial_equipment.input_per_minute("steel_components") == pytest.approx(40)
    assert industrial_equipment.output_per_minute == pytest.approx(20)


def test_production_guide_reverse_index_reports_empty_used_in_for_terminal_product() -> None:
    index = ProductionGuideRecipeIndex(_definitions())

    assert index.used_in("high_speed_network_system") == ()
