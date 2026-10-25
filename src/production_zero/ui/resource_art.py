"""Central cached raster artwork for resources and shared UI symbols."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter


RESOURCE_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "resources"
RESEARCH_GENERIC_ICON = "ui.research_generic"
RESEARCH_GENERIC_ASSET = RESOURCE_ASSET_DIR.parent / "ui" / "research_generic.png"
EXTRACTOR_RESOURCE_IDS = (
    "iron_ore",
    "copper_ore",
    "bauxite",
    "nickel_ore",
    "zinc_ore",
    "lead_ore",
    "tin_ore",
    "manganese_ore",
    "chromium_ore",
    "titanium_ore",
    "tungsten_ore",
    "cobalt_ore",
    "molybdenum_ore",
    "vanadium_ore",
    "silver_ore",
    "gold_ore",
    "platinum_ore",
    "palladium_ore",
    "lithium_ore",
    "uranium_ore",
    "rare_earth_ore",
    "niobium_ore",
    "coal",
    "quartz",
    "silica_sand",
    "limestone",
    "gypsum",
    "clay",
    "kaolin",
    "phosphate_rock",
    "potash",
    "salt",
    "sulfur",
    "graphite",
    "fluorspar",
    "magnesite",
    "borate_ore",
    "crude_oil",
    "natural_gas",
    "timber",
    "wheat",
    "corn",
    "soybeans",
    "sugarcane",
    "cotton",
    "rapeseed",
    "potatoes",
    "fruit",
    "natural_rubber",
)
PROCESSOR_RESOURCE_IDS = (
    "iron",
    "steel",
    "stainless_steel",
    "copper",
    "aluminum",
    "zinc",
    "lead",
    "tin",
    "nickel",
    "titanium",
    "tungsten",
    "manganese",
    "chromium",
    "cobalt",
    "molybdenum",
    "vanadium",
    "lithium",
    "gold",
    "silver",
    "platinum",
    "palladium",
    "rare_earth_metals",
    "niobium",
    "nickel_alloy",
    "superconducting_alloy",
    "glass",
    "cement",
    "ceramics",
    "processed_gypsum",
    "purified_graphite",
    "silicon",
    "high_purity_silicon",
    "carbon_fiber",
    "lumber",
    "wood_pulp",
    "cellulose",
    "treated_lumber",
    "polymer",
    "synthetic_rubber",
    "industrial_resin",
    "chemical_feedstock",
    "sulfuric_acid",
    "chlorine",
    "ammonia",
    "phosphoric_acid",
    "potassium_compound",
    "industrial_gas",
    "hydrogen",
    "bitumen",
    "flour",
    "corn_meal",
    "starch",
    "raw_sugar",
    "refined_sugar",
    "soy_oil",
    "soy_protein",
    "vegetable_oil",
    "cotton_fiber",
    "fruit_concentrate",
    "processed_rubber",
    "fermentation_feedstock",
    "galvanized_metal",
    "shielding_material",
    "vanadium_alloy",
    "catalyst_metal",
    "nuclear_material",
    "bio_lubricant",
    "organic_feedstock",
)
FABRICATOR_RESOURCE_IDS = (
    "advanced_alloy_components", "advanced_cell_components", "aerospace_components",
    "agricultural_chemicals", "agricultural_mineral_components", "ai_compute_components",
    "aluminum_components", "asphalt_components", "autonomous_components", "avionics_components",
    "battery_components", "battery_materials", "bearing_components", "bio_composite",
    "bio_material_components", "biodiesel_feedstock", "biopolymer", "catalyst_components",
    "ceramic_components", "chemical_components", "composite_components", "compressor_components",
    "computing_components", "concrete_components", "control_electronics", "copper_wire",
    "corrosion_resistant_components", "cutting_tooling", "display_components",
    "electrical_components", "electrolyzer_components", "ethanol_components",
    "fertilizer_components", "fiber_components", "filtration_components", "food_ingredients",
    "galvanized_components", "gas_handling_components", "gear_components", "glass_panels",
    "grid_storage_components", "hydraulic_components", "industrial_fabric", "insulated_wire",
    "insulation_material", "iron_components", "magnetic_components", "marine_components",
    "medical_components", "membrane_components", "memory_components", "mining_components",
    "motor_components", "network_components", "nuclear_fuel_components", "nutrition_components",
    "packaging_components", "power_electronics", "precision_components", "processor_components",
    "pump_components", "rail_components", "reactor_components", "refractory_alloy_components",
    "rubber_blend_components", "semiconductor_components", "semiconductor_die",
    "sensor_components", "server_components", "shielding_components", "silicon_substrate",
    "solar_components", "stainless_components", "steel_components", "storage_components",
    "structural_components", "sweetener_components", "technical_textile", "telecom_components",
    "tire_components", "titanium_components", "transformer_components", "turbine_components",
    "vehicle_components", "wind_components", "wooden_components",
)
ASSEMBLER_RESOURCE_IDS = (
    "industrial_equipment", "heavy_machinery", "mining_equipment", "mining_drill",
    "heavy_mining_drill", "excavator", "industrial_crusher", "industrial_pump",
    "industrial_compressor", "hydraulic_system", "electric_motor", "precision_motor",
    "gearbox", "cnc_machine", "industrial_cutting_machine", "processing_equipment",
    "advanced_furnace", "construction_materials", "reinforced_concrete", "structural_systems",
    "industrial_hall_modules", "prefabricated_structures", "industrial_glass_panels",
    "industrial_insulation", "engineered_structures", "electrical_cable", "power_cable",
    "transformer", "switchgear", "industrial_relay", "high_voltage_equipment",
    "industrial_generator", "industrial_inverter", "solar_array", "wind_turbine",
    "gas_turbine", "steam_turbine", "grid_battery", "grid_storage_system",
    "hydrogen_electrolyzer", "nuclear_fuel_assembly", "nuclear_reactor", "basic_chip",
    "microcontroller", "microchip", "cpu", "memory_module", "industrial_sensor",
    "industrial_controller", "industrial_display", "industrial_computer", "server",
    "server_rack", "compute_node", "ai_accelerator", "ai_server", "data_center_module",
    "supercomputer", "robotic_actuator", "servo_motor", "robotic_arm", "industrial_robot",
    "industrial_drone", "autonomous_mobile_robot", "advanced_industrial_robot",
    "utility_vehicle", "combustion_vehicle", "electric_vehicle", "premium_electric_vehicle",
    "autonomous_vehicle", "commercial_truck", "industrial_tires", "railway_track",
    "freight_railcar", "diesel_locomotive", "electric_locomotive", "high_speed_train",
    "autonomous_freight_train", "workboat", "cargo_vessel", "container_ship", "tanker",
    "autonomous_cargo_ship", "high_speed_vessel", "light_aircraft", "cargo_aircraft",
    "commercial_aircraft", "jet_engine", "advanced_aircraft", "autonomous_aircraft",
    "satellite", "communication_satellite", "navigation_satellite", "rocket_engine",
    "launch_vehicle", "orbital_vehicle", "packaged_food", "processed_food",
    "packaged_nutrition", "bakery_products", "packaged_meals", "packaged_beverages",
    "soft_drinks", "animal_feed", "fertilizer", "advanced_fertilizer", "construction_frames",
    "packaging_materials", "industrial_packaging", "protective_packaging", "cargo_pallets",
    "commercial_furniture", "sustainable_packaging", "clothing", "workwear",
    "protective_clothing", "industrial_clothing", "safety_equipment",
    "advanced_protective_equipment", "industrial_plastics", "industrial_rubber_products",
    "industrial_seals", "industrial_chemicals", "bio_based_chemicals", "bioplastic",
    "biofuel", "biodiesel", "crop_protection_products", "laboratory_equipment",
    "medical_monitor", "surgical_equipment", "diagnostic_system", "advanced_medical_equipment",
    "communication_cable", "network_switch", "router", "radio_transceiver",
    "cellular_base_station", "high_speed_network_system", "semiconductor_equipment",
    "industrial_laser", "machine_vision_system", "autonomous_control_system",
    "advanced_semiconductor_equipment", "carbon_capture_plant", "desalination_plant",
    "synthetic_fuel_plant", "quantum_computing_module", "superconducting_magnet_system",
    "fusion_reactor_module",
)
RESOURCE_RASTER_ASSETS = {
    resource_id: RESOURCE_ASSET_DIR / f"{resource_id}.png"
    for resource_id in (
        *EXTRACTOR_RESOURCE_IDS,
        *PROCESSOR_RESOURCE_IDS,
        *FABRICATOR_RESOURCE_IDS,
        *ASSEMBLER_RESOURCE_IDS,
    )
}

UI_RASTER_SIZES = (32, 38, 48)
UI_RASTER_COLUMNS = 16
_UI_RASTER_IDS = tuple(sorted(RESOURCE_RASTER_ASSETS))
_UI_RASTER_INDEX = {resource_id: index for index, resource_id in enumerate(_UI_RASTER_IDS)}


@lru_cache(maxsize=1)
def _ui_raster_atlas() -> QImage:
    image = QImage(str(RESOURCE_ASSET_DIR / "ui_raster_atlas.png"))
    rows = (len(_UI_RASTER_IDS) + UI_RASTER_COLUMNS - 1) // UI_RASTER_COLUMNS
    if (image.isNull() or image.width() != UI_RASTER_COLUMNS * max(UI_RASTER_SIZES)
            or image.height() != rows * sum(UI_RASTER_SIZES)
            or image.text("resource_ids") != "\n".join(_UI_RASTER_IDS)
            or image.text("raster_sizes") != ",".join(map(str, UI_RASTER_SIZES))):
        return QImage()  # Original assets remain a complete, safe fallback.
    return image


def normalized_resource_id(resource_id: str) -> str:
    return resource_id.removeprefix("resource.")


def has_resource_raster(resource_id: str) -> bool:
    return resource_id == RESEARCH_GENERIC_ICON or normalized_resource_id(resource_id) in RESOURCE_RASTER_ASSETS


@lru_cache(maxsize=len(RESOURCE_RASTER_ASSETS) + 1)
def resource_raster_image(resource_id: str) -> QImage:
    normalized = normalized_resource_id(resource_id)
    path = RESEARCH_GENERIC_ASSET if normalized == RESEARCH_GENERIC_ICON else RESOURCE_RASTER_ASSETS[normalized]
    image = QImage(str(path))
    if image.isNull():
        raise RuntimeError(f"Invalid or missing resource raster asset: {path}")
    return image


@lru_cache(maxsize=768)
def _cached_scaled_resource_raster(resource_id: str, width: int, height: int) -> QImage:
    if width == height and width in UI_RASTER_SIZES and resource_id in _UI_RASTER_INDEX:
        atlas = _ui_raster_atlas()
        if not atlas.isNull():
            index = _UI_RASTER_INDEX[resource_id]
            rows = (len(_UI_RASTER_IDS) + UI_RASTER_COLUMNS - 1) // UI_RASTER_COLUMNS
            offset = rows * sum(size for size in UI_RASTER_SIZES if size < width)
            return atlas.copy((index % UI_RASTER_COLUMNS) * width,
                              offset + (index // UI_RASTER_COLUMNS) * height, width, height)
    return resource_raster_image(resource_id).scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _scaled_resource_raster(resource_id: str, width: int, height: int) -> QImage:
    # Room for all 353 resources at the common 38/48 px sizes, with a hard
    # <48 MiB pixel budget. Large export/preview rasters must not evict UI icons.
    if width * height <= 128 * 128:
        return _cached_scaled_resource_raster(resource_id, width, height)
    return resource_raster_image(resource_id).scaled(
        width, height, Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation)


_scaled_resource_raster.cache_info = _cached_scaled_resource_raster.cache_info
_scaled_resource_raster.cache_clear = _cached_scaled_resource_raster.cache_clear


def draw_resource_raster(painter: QPainter, rect: QRectF, resource_id: str) -> None:
    """Draw a complete transparent resource asset without cropping or stretching."""
    normalized = normalized_resource_id(resource_id)
    scaled = _scaled_resource_raster(
        normalized,
        max(1, round(rect.width())),
        max(1, round(rect.height())),
    )
    target = QRectF(
        rect.center().x() - scaled.width() / 2,
        rect.center().y() - scaled.height() / 2,
        scaled.width(),
        scaled.height(),
    )
    painter.save()
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, scaled)
    finally:
        painter.restore()
