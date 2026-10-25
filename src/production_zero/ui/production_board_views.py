from __future__ import annotations

from production_zero.core.enums import MachineType
from production_zero.ui.factory_view import ProductionBoardConfig
from production_zero.ui.factory_view_v2 import ProductionBoardViewV2


RESOURCES_BOARD_CONFIG = ProductionBoardConfig(
    board_kind="resources",
    title="RESOURCES",
    unit_label="Site",
    unit_plural="SITES",
    unit_id_prefix="site",
    track_label="SECTOR",
    purchase_label="Develop Site",
    production_guide_enabled=True,
    resource_drawer_enabled=True,
    allowed_machine_types=frozenset({MachineType.EXTRACTOR, MachineType.DRILLING, MachineType.AGRICULTURE}),
    max_lines=3,
    max_slots_per_line=10,
    start_unlocked_lines=1,
    start_slots_per_line=1,
)

ENERGY_BOARD_CONFIG = ProductionBoardConfig(
    board_kind="energy",
    title="ENERGY",
    unit_label="Plant",
    unit_plural="PLANTS",
    unit_id_prefix="plant",
    track_label="BLOCK",
    purchase_label="Build Plant",
    production_guide_enabled=True,
    resource_drawer_enabled=True,
    allowed_machine_types=frozenset(),
    allow_energy=True,
    max_lines=3,
    max_slots_per_line=5,
    start_unlocked_lines=1,
    start_slots_per_line=1,
)


class ResourcesViewV2(ProductionBoardViewV2):
    def __init__(self, state, command_bus, definitions) -> None:
        super().__init__(state, command_bus, definitions, RESOURCES_BOARD_CONFIG)


class EnergyViewV2(ProductionBoardViewV2):
    def __init__(self, state, command_bus, definitions) -> None:
        super().__init__(state, command_bus, definitions, ENERGY_BOARD_CONFIG)
