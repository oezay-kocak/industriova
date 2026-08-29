from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "production_zero" / "data"


def slug(name: str) -> str:
    return (
        name.lower()
        .replace("/", " ")
        .replace("-", " ")
        .replace("+", " plus ")
        .replace(".", "")
        .replace("·", " ")
        .replace("  ", " ")
        .strip()
        .replace(" ", "_")
    )


def visual_icon_key(resource_id: str) -> str:
    specific = {
        "iron_ore": "ore_iron",
        "copper_ore": "ore_copper",
        "gold_ore": "ore_gold",
        "lithium_ore": "ore_lithium",
        "uranium_ore": "ore_uranium",
        "rare_earth_ore": "ore_rare_earth",
        "fruit": "fruit",
        "natural_rubber": "latex",
        "silica_sand": "sand",
        "limestone": "stone_block",
        "salt": "salt_crystal",
        "sulfur": "sulfur_crystal",
        "graphite": "graphite_block",
    }
    if resource_id in specific:
        return specific[resource_id]
    if "oil" in resource_id or "bitumen" in resource_id:
        return "oil_drop"
    if "gas" in resource_id or "hydrogen" in resource_id:
        return "flame"
    if "timber" in resource_id or "lumber" in resource_id or "wood" in resource_id:
        return "log"
    if "wheat" in resource_id or "flour" in resource_id:
        return "wheat"
    if "corn" in resource_id:
        return "corn"
    if "cotton" in resource_id or "textile" in resource_id or "fabric" in resource_id:
        return "cotton"
    if "coal" in resource_id:
        return "coal_chunk"
    if any(token in resource_id for token in ("quartz", "salt", "silica", "crystal", "gypsum", "fluorspar", "borate")):
        return "crystal"
    if "ore" in resource_id:
        return "ore_chunk"
    if any(token in resource_id for token in ("steel", "iron", "copper", "aluminum", "titanium", "zinc", "lead", "nickel", "gold", "silver", "palladium", "platinum", "vanadium", "alloy")):
        return "ingot"
    if any(token in resource_id for token in ("acid", "chemical", "chlorine", "ammonia", "polymer", "resin", "rubber", "feedstock", "lubricant")):
        return "flask"
    if any(token in resource_id for token in ("semiconductor", "chip", "cpu", "processor", "memory", "computing", "electronics", "sensor", "control", "display")):
        return "chip"
    if "battery" in resource_id or "cell" in resource_id or "storage" in resource_id:
        return "battery"
    if any(token in resource_id for token in ("food", "sugar", "fruit", "soy", "nutrition", "meal", "beverage", "bakery", "potato")):
        return "package"
    if any(token in resource_id for token in ("component", "motor", "gear", "pump", "compressor", "turbine", "bearing", "hydraulic")):
        return "gear"
    if any(token in resource_id for token in ("vehicle", "truck", "automotive", "tire")):
        return "vehicle"
    if "rail" in resource_id or "train" in resource_id or "locomotive" in resource_id:
        return "rail"
    if any(token in resource_id for token in ("ship", "marine", "vessel", "tanker", "boat")):
        return "ship"
    if any(token in resource_id for token in ("aircraft", "aerospace", "avionics", "jet")):
        return "aircraft"
    if any(token in resource_id for token in ("satellite", "rocket", "orbital", "space")):
        return "satellite"
    if any(token in resource_id for token in ("medical", "diagnostic", "surgical")):
        return "medical"
    if any(token in resource_id for token in ("telecom", "network", "router", "radio")):
        return "signal"
    return "hex"


def visual_accent_key(resource_id: str) -> str:
    for token in ("iron", "copper", "coal"):
        if token in resource_id:
            return token
    if "oil" in resource_id or "bitumen" in resource_id:
        return "oil"
    if "gas" in resource_id or "hydrogen" in resource_id:
        return "gas"
    if "timber" in resource_id or "lumber" in resource_id or "wood" in resource_id:
        return "wood"
    if "wheat" in resource_id or "corn" in resource_id or "flour" in resource_id:
        return "grain"
    if "cotton" in resource_id:
        return "cotton"
    if any(token in resource_id for token in ("fruit", "soy", "potato", "rapeseed", "sugar", "food", "nutrition")):
        return "crop"
    if any(token in resource_id for token in ("quartz", "salt", "silica", "gypsum", "fluorspar", "borate")):
        return "crystal"
    if any(token in resource_id for token in ("acid", "chemical", "polymer", "resin", "rubber", "chlorine", "ammonia")):
        return "chemical"
    if any(token in resource_id for token in ("chip", "cpu", "semiconductor", "electronics", "computing", "sensor", "control")):
        return "electronics"
    if "battery" in resource_id or "cell" in resource_id or "storage" in resource_id:
        return "battery"
    if "rail" in resource_id or "train" in resource_id:
        return "rail"
    if "ship" in resource_id or "marine" in resource_id or "vessel" in resource_id:
        return "ship"
    if "aircraft" in resource_id or "aerospace" in resource_id:
        return "aircraft"
    if "satellite" in resource_id or "rocket" in resource_id or "orbital" in resource_id:
        return "space"
    if "medical" in resource_id or "diagnostic" in resource_id:
        return "medical"
    if "telecom" in resource_id or "network" in resource_id or "radio" in resource_id:
        return "telecom"
    if "component" in resource_id:
        return "component"
    return "default"


def visual_category(resource_id: str, stage: str) -> str:
    if stage == "extraction":
        if "ore" in resource_id or resource_id in {"coal", "graphite"}:
            return "Ores / Metals"
        if any(token in resource_id for token in ("limestone", "gypsum", "clay", "kaolin", "quartz", "salt", "sulfur", "fluorspar", "borate", "phosphate", "potash", "magnesite", "silica")):
            return "Minerals"
        if "oil" in resource_id or "gas" in resource_id:
            return "Oil & Gas"
        if "timber" in resource_id or "rubber" in resource_id:
            return "Forestry"
        return "Agriculture"
    if any(token in resource_id for token in ("food", "wheat", "corn", "soy", "fruit", "sugar", "nutrition", "bakery", "beverage")):
        return "Food & Agriculture"
    if any(token in resource_id for token in ("chemical", "acid", "polymer", "resin", "rubber", "hydrogen", "gas")):
        return "Chemicals"
    if any(token in resource_id for token in ("chip", "cpu", "semiconductor", "electronics", "computing", "sensor", "network", "telecom")):
        return "Electronics"
    if any(token in resource_id for token in ("battery", "solar", "wind", "reactor", "turbine", "energy", "storage", "fuel")):
        return "Energy"
    if any(token in resource_id for token in ("vehicle", "rail", "ship", "aircraft", "aerospace", "satellite", "rocket")):
        return "Transport"
    if any(token in resource_id for token in ("medical", "diagnostic", "surgical")):
        return "Medical"
    if "component" in resource_id or "equipment" in resource_id or "machine" in resource_id:
        return "Components"
    return "Materials"


EXTRACTION = [
    ("Iron Ore", 1.00, "ore"),
    ("Copper Ore", 1.40, "ore"),
    ("Bauxite", 1.10, "ore"),
    ("Nickel Ore", 1.80, "ore"),
    ("Zinc Ore", 1.25, "ore"),
    ("Lead Ore", 1.15, "ore"),
    ("Tin Ore", 1.45, "ore"),
    ("Manganese Ore", 1.35, "ore"),
    ("Chromium Ore", 1.65, "ore"),
    ("Titanium Ore", 2.40, "ore"),
    ("Tungsten Ore", 2.80, "ore"),
    ("Cobalt Ore", 2.60, "ore"),
    ("Molybdenum Ore", 2.20, "ore"),
    ("Vanadium Ore", 2.10, "ore"),
    ("Silver Ore", 3.60, "ore"),
    ("Gold Ore", 5.00, "ore"),
    ("Platinum Ore", 5.80, "ore"),
    ("Palladium Ore", 5.40, "ore"),
    ("Lithium Ore", 2.30, "ore"),
    ("Uranium Ore", 3.20, "ore"),
    ("Rare Earth Ore", 2.70, "ore"),
    ("Niobium Ore", 2.50, "ore"),
    ("Coal", 1.20, "mineral"),
    ("Quartz", 1.10, "mineral"),
    ("Silica Sand", 0.90, "mineral"),
    ("Limestone", 0.80, "mineral"),
    ("Gypsum", 0.85, "mineral"),
    ("Clay", 0.70, "mineral"),
    ("Kaolin", 1.00, "mineral"),
    ("Phosphate Rock", 1.25, "mineral"),
    ("Potash", 1.35, "mineral"),
    ("Salt", 0.75, "mineral"),
    ("Sulfur", 1.15, "mineral"),
    ("Graphite", 1.75, "mineral"),
    ("Fluorspar", 1.50, "mineral"),
    ("Magnesite", 1.30, "mineral"),
    ("Borate Ore", 1.45, "mineral"),
    ("Crude Oil", 2.20, "feedstock"),
    ("Natural Gas", 1.90, "feedstock"),
    ("Timber", 1.10, "organic"),
    ("Wheat", 0.95, "organic"),
    ("Corn", 0.90, "organic"),
    ("Soybeans", 1.05, "organic"),
    ("Sugarcane", 0.85, "organic"),
    ("Cotton", 1.20, "organic"),
    ("Rapeseed", 1.00, "organic"),
    ("Potatoes", 0.80, "organic"),
    ("Fruit", 1.10, "organic"),
    ("Natural Rubber", 1.70, "organic"),
]


PROCESSING_RECIPES = [
    ("Iron", {"iron_ore": 12}, 6, 4, 8, ["recipe.furnace.iron"]),
    ("Steel", {"iron": 6, "coal": 3}, 4, 5, 12, []),
    ("Stainless Steel", {"steel": 4, "chromium": 1, "nickel": 1}, 3, 6, 13, []),
    ("Copper", {"copper_ore": 12}, 6, 4, 8, ["recipe.furnace.copper"]),
    ("Aluminum", {"bauxite": 10}, 5, 4, 9, []),
    ("Zinc", {"zinc_ore": 10}, 5, 4, 8, []),
    ("Lead", {"lead_ore": 10}, 5, 4, 8, []),
    ("Tin", {"tin_ore": 10}, 5, 4, 8, []),
    ("Nickel", {"nickel_ore": 10}, 5, 4, 9, []),
    ("Titanium", {"titanium_ore": 8}, 4, 5, 11, []),
    ("Tungsten", {"tungsten_ore": 8}, 4, 5, 11, []),
    ("Manganese", {"manganese_ore": 10}, 5, 4, 8, []),
    ("Chromium", {"chromium_ore": 10}, 5, 4, 9, []),
    ("Cobalt", {"cobalt_ore": 8}, 4, 5, 10, []),
    ("Molybdenum", {"molybdenum_ore": 8}, 4, 5, 10, []),
    ("Vanadium", {"vanadium_ore": 8}, 4, 5, 10, []),
    ("Lithium", {"lithium_ore": 8}, 4, 5, 10, []),
    ("Gold", {"gold_ore": 6}, 3, 5, 11, []),
    ("Silver", {"silver_ore": 6}, 3, 5, 10, []),
    ("Platinum", {"platinum_ore": 5}, 2, 6, 12, []),
    ("Palladium", {"palladium_ore": 5}, 2, 6, 12, []),
    ("Rare Earth Metals", {"rare_earth_ore": 8}, 3, 6, 12, []),
    ("Niobium", {"niobium_ore": 8}, 4, 5, 10, []),
    ("Nickel Alloy", {"nickel": 3, "steel": 2, "molybdenum": 1}, 3, 6, 13, []),
    ("Superconducting Alloy", {"niobium": 2, "titanium": 1, "rare_earth_metals": 1}, 2, 7, 15, []),
    ("Glass", {"silica_sand": 4, "limestone": 1, "borate_ore": 1}, 3, 4, 7, []),
    ("Cement", {"limestone": 4, "gypsum": 1}, 3, 4, 7, []),
    ("Ceramics", {"clay": 3, "kaolin": 1, "magnesite": 1}, 3, 4, 7, []),
    ("Processed Gypsum", {"gypsum": 3}, 3, 3, 6, []),
    ("Purified Graphite", {"graphite": 4}, 3, 5, 9, []),
    ("Silicon", {"quartz": 4, "coal": 1}, 2, 5, 10, []),
    ("High-Purity Silicon", {"silicon": 2, "chemical_feedstock": 1, "fluorspar": 1}, 1, 6, 12, []),
    ("Carbon Fiber", {"polymer": 2, "purified_graphite": 1}, 1, 6, 12, []),
    ("Lumber", {"timber": 3}, 3, 3, 5, []),
    ("Wood Pulp", {"timber": 3, "chemical_feedstock": 1}, 3, 4, 6, []),
    ("Cellulose", {"wood_pulp": 2}, 2, 4, 6, []),
    ("Treated Lumber", {"lumber": 3, "industrial_resin": 1}, 3, 4, 7, []),
    ("Polymer", {"crude_oil": 3, "natural_gas": 1}, 2, 5, 9, []),
    ("Synthetic Rubber", {"crude_oil": 2, "natural_gas": 1, "sulfur": 1}, 2, 5, 9, []),
    ("Industrial Resin", {"crude_oil": 2, "chemical_feedstock": 1}, 2, 5, 9, []),
    ("Chemical Feedstock", {"crude_oil": 2, "natural_gas": 2}, 3, 4, 8, []),
    ("Sulfuric Acid", {"sulfur": 2, "industrial_gas": 1}, 2, 4, 8, []),
    ("Chlorine", {"salt": 3}, 2, 4, 8, []),
    ("Ammonia", {"natural_gas": 2, "industrial_gas": 1}, 2, 4, 8, []),
    ("Phosphoric Acid", {"phosphate_rock": 2, "sulfuric_acid": 1}, 2, 4, 8, []),
    ("Potassium Compound", {"potash": 3}, 2, 4, 7, []),
    ("Industrial Gas", {"natural_gas": 2}, 2, 3, 7, []),
    ("Hydrogen", {"natural_gas": 2, "industrial_gas": 1}, 2, 4, 9, []),
    ("Bitumen", {"crude_oil": 3}, 2, 4, 8, []),
    ("Flour", {"wheat": 2}, 2, 3, 5, []),
    ("Corn Meal", {"corn": 2}, 2, 3, 5, []),
    ("Starch", {"corn": 2, "potatoes": 1}, 2, 3, 5, []),
    ("Raw Sugar", {"sugarcane": 2}, 2, 3, 5, []),
    ("Refined Sugar", {"raw_sugar": 2}, 2, 3, 5, []),
    ("Soy Oil", {"soybeans": 2}, 1, 3, 5, []),
    ("Soy Protein", {"soybeans": 2}, 1, 3, 5, []),
    ("Vegetable Oil", {"rapeseed": 2, "soy_oil": 1}, 2, 3, 5, []),
    ("Cotton Fiber", {"cotton": 2}, 2, 3, 5, []),
    ("Fruit Concentrate", {"fruit": 3, "refined_sugar": 1}, 2, 4, 5, []),
    ("Processed Rubber", {"natural_rubber": 2, "sulfur": 1}, 2, 4, 7, []),
    ("Fermentation Feedstock", {"corn": 2, "raw_sugar": 1}, 2, 4, 6, []),
    ("Galvanized Metal", {"zinc_ore": 4, "iron_ore": 4}, 3, 4, 8, []),
    ("Shielding Material", {"lead_ore": 4, "borate_ore": 1}, 3, 4, 8, []),
    ("Vanadium Alloy", {"vanadium_ore": 4, "iron_ore": 4}, 3, 5, 10, []),
    ("Catalyst Metal", {"palladium_ore": 3, "platinum_ore": 1}, 2, 5, 10, []),
    ("Nuclear Material", {"uranium_ore": 3, "lead_ore": 1}, 2, 6, 12, []),
    ("Bio-Lubricant", {"rapeseed": 2, "natural_gas": 1}, 2, 4, 7, []),
    ("Organic Feedstock", {"wheat": 1, "fruit": 1, "potatoes": 1}, 2, 4, 6, []),
]


MANUFACTURING_RECIPES = [
    ("Iron Components", {"iron": 2}, 2),
    ("Steel Components", {"steel": 2}, 2),
    ("Stainless Components", {"stainless_steel": 2}, 2),
    ("Aluminum Components", {"aluminum": 2}, 2),
    ("Titanium Components", {"titanium": 2}, 2),
    ("Precision Components", {"steel_components": 1, "aluminum_components": 1, "tungsten": 1}, 1),
    ("Gear Components", {"steel": 2, "manganese": 1}, 2),
    ("Bearing Components", {"steel": 2, "chromium": 1}, 2),
    ("Cutting Tooling", {"tungsten": 1, "steel": 1}, 1),
    ("Hydraulic Components", {"steel_components": 1, "industrial_resin": 1}, 1),
    ("Pump Components", {"steel_components": 1, "copper": 1}, 1),
    ("Compressor Components", {"steel_components": 1, "aluminum_components": 1}, 1),
    ("Turbine Components", {"nickel_alloy": 1, "titanium": 1}, 1),
    ("Structural Components", {"steel": 3, "cement": 1}, 2),
    ("Mining Components", {"steel_components": 1, "tungsten": 1}, 1),
    ("Vehicle Components", {"steel_components": 1, "aluminum_components": 1, "processed_rubber": 1}, 1),
    ("Marine Components", {"steel_components": 2, "industrial_resin": 1}, 1),
    ("Rail Components", {"steel_components": 2, "manganese": 1}, 1),
    ("Aerospace Components", {"aluminum_components": 1, "titanium_components": 1, "carbon_fiber": 1}, 1),
    ("Copper Wire", {"copper": 2}, 3),
    ("Insulated Wire", {"copper_wire": 2, "polymer": 1}, 2),
    ("Electrical Components", {"insulated_wire": 1, "copper": 1, "tin": 1}, 2),
    ("Transformer Components", {"copper_wire": 2, "steel_components": 1}, 1),
    ("Motor Components", {"copper_wire": 2, "magnetic_components": 1}, 1),
    ("Magnetic Components", {"rare_earth_metals": 1, "iron": 1}, 1),
    ("Power Electronics", {"semiconductor_components": 1, "copper": 1, "aluminum": 1}, 1),
    ("Display Components", {"glass": 1, "high_purity_silicon": 1, "polymer": 1}, 1),
    ("Semiconductor Components", {"high_purity_silicon": 2, "copper": 1, "gold": 1}, 1),
    ("Semiconductor Die", {"semiconductor_components": 1, "silver": 1}, 1),
    ("Sensor Components", {"semiconductor_components": 1, "rare_earth_metals": 1}, 1),
    ("Control Electronics", {"semiconductor_die": 1, "copper_wire": 1}, 1),
    ("Computing Components", {"semiconductor_die": 1, "control_electronics": 1}, 1),
    ("Memory Components", {"semiconductor_die": 1, "high_purity_silicon": 1}, 1),
    ("Processor Components", {"semiconductor_die": 1, "gold": 1, "rare_earth_metals": 1}, 1),
    ("Telecom Components", {"control_electronics": 1, "copper_wire": 1, "rare_earth_metals": 1}, 1),
    ("Network Components", {"telecom_components": 1, "power_electronics": 1}, 1),
    ("Avionics Components", {"control_electronics": 1, "sensor_components": 1, "aerospace_components": 1}, 1),
    ("Battery Materials", {"lithium": 2, "nickel": 1, "cobalt": 1}, 2),
    ("Battery Components", {"battery_materials": 1, "aluminum_components": 1}, 1),
    ("Advanced Cell Components", {"battery_components": 1, "purified_graphite": 1}, 1),
    ("Storage Components", {"advanced_cell_components": 1, "power_electronics": 1}, 1),
    ("Solar Components", {"glass_panels": 1, "high_purity_silicon": 1, "aluminum_components": 1}, 1),
    ("Wind Components", {"turbine_components": 1, "composite_components": 1}, 1),
    ("Reactor Components", {"uranium_ore": 1, "zirconium_proxy": 0}, 1),
    ("Electrolyzer Components", {"platinum": 1, "hydrogen": 1, "power_electronics": 1}, 1),
    ("Concrete Components", {"cement": 2, "steel": 1}, 2),
    ("Glass Panels", {"glass": 2, "aluminum": 1}, 2),
    ("Ceramic Components", {"ceramics": 2}, 2),
    ("Insulation Material", {"processed_gypsum": 1, "polymer": 1}, 2),
    ("Composite Components", {"carbon_fiber": 1, "industrial_resin": 1}, 1),
    ("Packaging Components", {"wood_pulp": 2, "polymer": 1}, 2),
    ("Food Ingredients", {"flour": 1, "corn_meal": 1, "refined_sugar": 1}, 2),
    ("Nutrition Components", {"soy_protein": 1, "vegetable_oil": 1, "fruit_concentrate": 1}, 1),
    ("Fertilizer Components", {"ammonia": 1, "phosphoric_acid": 1, "potash": 1}, 2),
    ("Agricultural Chemicals", {"chemical_feedstock": 1, "chlorine": 1, "sulfuric_acid": 1}, 1),
    ("Technical Textile", {"cotton_fiber": 1, "polymer": 1}, 2),
    ("Industrial Fabric", {"technical_textile": 1, "processed_rubber": 1}, 1),
    ("Wooden Components", {"lumber": 2, "treated_lumber": 1}, 2),
    ("Fiber Components", {"cellulose": 2, "industrial_resin": 1}, 1),
    ("Bio-Composite", {"cellulose": 1, "industrial_resin": 1}, 1),
    ("Biopolymer", {"starch": 2, "fermentation_feedstock": 1}, 1),
    ("Tire Components", {"processed_rubber": 2, "carbon_fiber": 1}, 1),
    ("Ethanol Components", {"fermentation_feedstock": 2}, 1),
    ("Biodiesel Feedstock", {"vegetable_oil": 2, "chemical_feedstock": 1}, 1),
    ("Galvanized Components", {"galvanized_metal": 2, "zinc": 1}, 2),
    ("Shielding Components", {"shielding_material": 2, "lead": 1}, 2),
    ("Advanced Alloy Components", {"vanadium_alloy": 2, "vanadium": 1, "titanium": 1}, 1),
    ("Catalyst Components", {"catalyst_metal": 1, "palladium": 1}, 1),
    ("Gas Handling Components", {"industrial_gas": 1, "hydrogen": 1}, 1),
    ("Asphalt Components", {"bitumen": 2, "cement": 1}, 1),
    ("Agricultural Mineral Components", {"potassium_compound": 2, "phosphoric_acid": 1}, 1),
    ("Sweetener Components", {"raw_sugar": 2, "soy_oil": 1, "organic_feedstock": 1}, 1),
    ("Silicon Substrate", {"silicon": 2, "glass": 1}, 1),
    ("Rubber Blend Components", {"synthetic_rubber": 2, "processed_rubber": 1}, 1),
    ("Refractory Alloy Components", {"molybdenum": 1, "niobium": 1, "superconducting_alloy": 1}, 1),
    ("Filtration Components", {"ceramics": 1, "processed_gypsum": 1, "polymer": 1}, 1),
    ("Membrane Components", {"polymer": 1, "cellulose": 1, "chlorine": 1}, 1),
    ("Medical Components", {"stainless_steel": 1, "glass": 1, "platinum": 1}, 1),
    ("Autonomous Components", {"high_purity_silicon": 1, "rare_earth_metals": 1, "copper": 1}, 1),
    ("Server Components", {"high_purity_silicon": 2, "copper": 1, "gold": 1}, 1),
    ("AI Compute Components", {"high_purity_silicon": 2, "rare_earth_metals": 1, "gold": 1}, 1),
    ("Chemical Components", {"chemical_feedstock": 2, "sulfuric_acid": 1}, 1),
    ("Bio-Material Components", {"bio_lubricant": 1, "cellulose": 1}, 1),
    ("Nuclear Fuel Components", {"nuclear_material": 2, "shielding_material": 1}, 1),
    ("Grid Storage Components", {"lithium": 1, "vanadium_alloy": 1, "purified_graphite": 1}, 1),
    ("Corrosion Resistant Components", {"galvanized_metal": 2, "stainless_steel": 1}, 1),
]


ASSEMBLY_INPUTS = {
    "Industrial Equipment": {"steel_components": 2, "electrical_components": 1, "iron_components": 1},
    "Heavy Machinery": {"structural_components": 2, "hydraulic_components": 1, "control_electronics": 1},
    "Mining Equipment": {"mining_components": 2, "steel_components": 1},
    "Mining Drill": {"mining_components": 1, "motor_components": 1, "steel_components": 1},
    "Heavy Mining Drill": {"mining_components": 2, "hydraulic_components": 1, "control_electronics": 1},
    "Excavator": {"vehicle_components": 2, "hydraulic_components": 1, "structural_components": 1},
    "Industrial Crusher": {"mining_components": 2, "gear_components": 1},
    "Industrial Pump": {"pump_components": 2, "motor_components": 1},
    "Industrial Compressor": {"compressor_components": 2, "motor_components": 1},
    "Hydraulic System": {"hydraulic_components": 2, "steel_components": 1},
    "Electric Motor": {"motor_components": 2, "electrical_components": 1},
    "Precision Motor": {"motor_components": 1, "precision_components": 1, "magnetic_components": 1},
    "Gearbox": {"gear_components": 2, "bearing_components": 1},
    "CNC Machine": {"precision_components": 2, "control_electronics": 1, "structural_components": 1},
    "Industrial Cutting Machine": {"precision_components": 1, "tungsten": 1, "control_electronics": 1},
    "Processing Equipment": {"steel_components": 2, "pump_components": 1, "control_electronics": 1},
    "Advanced Furnace": {"stainless_components": 2, "ceramic_components": 1, "control_electronics": 1},
    "Construction Materials": {"concrete_components": 2, "wooden_components": 1},
    "Reinforced Concrete": {"concrete_components": 2, "steel_components": 1},
    "Structural Systems": {"structural_components": 2, "concrete_components": 1},
    "Industrial Hall Modules": {"structural_components": 2, "galvanized_components": 1, "insulation_material": 1, "glass_panels": 1},
    "Prefabricated Structures": {"structural_components": 1, "wooden_components": 1, "concrete_components": 1},
    "Industrial Glass Panels": {"glass_panels": 2, "aluminum_components": 1},
    "Industrial Insulation": {"insulation_material": 2, "fiber_components": 1},
    "Engineered Structures": {"structural_components": 2, "composite_components": 1},
    "Electrical Cable": {"insulated_wire": 2, "copper_wire": 1},
    "Power Cable": {"insulated_wire": 2, "aluminum_components": 1},
    "Transformer": {"transformer_components": 2, "electrical_components": 1},
    "Switchgear": {"electrical_components": 2, "control_electronics": 1},
    "Industrial Relay": {"electrical_components": 1, "control_electronics": 1},
    "High-Voltage Equipment": {"transformer_components": 1, "power_electronics": 1, "insulation_material": 1},
    "Industrial Generator": {"motor_components": 2, "turbine_components": 1},
    "Industrial Inverter": {"power_electronics": 2, "control_electronics": 1},
    "Solar Array": {"solar_components": 2, "power_electronics": 1},
    "Wind Turbine": {"wind_components": 2, "structural_components": 1, "power_electronics": 1},
    "Gas Turbine": {"turbine_components": 2, "nickel_alloy": 1},
    "Steam Turbine": {"turbine_components": 2, "stainless_components": 1},
    "Grid Battery": {"battery_components": 2, "power_electronics": 1},
    "Grid Storage System": {"storage_components": 2, "power_electronics": 1},
    "Hydrogen Electrolyzer": {"electrolyzer_components": 2, "power_electronics": 1},
    "Nuclear Fuel Assembly": {"uranium_ore": 2, "reactor_components": 1},
    "Nuclear Reactor": {"reactor_components": 2, "control_electronics": 1, "structural_components": 1},
    "Basic Chip": {"semiconductor_components": 1, "copper_wire": 1},
    "Microcontroller": {"semiconductor_die": 1, "control_electronics": 1},
    "Microchip": {"semiconductor_die": 1, "gold": 1},
    "CPU": {"processor_components": 2, "memory_components": 1},
    "Memory Module": {"memory_components": 2, "control_electronics": 1},
    "Industrial Sensor": {"sensor_components": 2, "control_electronics": 1},
    "Industrial Controller": {"control_electronics": 2, "sensor_components": 1},
    "Industrial Display": {"glass_panels": 1, "control_electronics": 1},
    "Industrial Computer": {"computing_components": 2, "industrial_display": 1},
    "Server": {"computing_components": 2, "memory_components": 1},
    "Server Rack": {"server": 2, "structural_components": 1},
    "Compute Node": {"processor_components": 2, "memory_components": 1, "network_components": 1},
    "AI Accelerator": {"processor_components": 2, "rare_earth_metals": 1, "power_electronics": 1},
    "AI Server": {"ai_accelerator": 1, "server": 1, "network_components": 1},
    "Data Center Module": {"server_rack": 2, "grid_storage_system": 1},
    "Supercomputer": {"compute_node": 2, "ai_accelerator": 1, "grid_storage_system": 1},
    "Robotic Actuator": {"precision_components": 1, "motor_components": 1},
    "Servo Motor": {"precision_motor": 1, "control_electronics": 1},
    "Robotic Arm": {"robotic_actuator": 2, "control_electronics": 1},
    "Industrial Robot": {"robotic_arm": 2, "industrial_controller": 1},
    "Industrial Drone": {"aerospace_components": 1, "sensor_components": 1, "battery_components": 1},
    "Autonomous Mobile Robot": {"vehicle_components": 1, "sensor_components": 1, "control_electronics": 1},
    "Advanced Industrial Robot": {"industrial_robot": 1, "machine_vision_system": 1, "ai_accelerator": 1},
    "Utility Vehicle": {"vehicle_components": 2, "industrial_controller": 1},
    "Combustion Vehicle": {"vehicle_components": 2, "gas_turbine": 1},
    "Electric Vehicle": {"vehicle_components": 1, "battery_components": 2, "electric_motor": 1},
    "Premium Electric Vehicle": {"electric_vehicle": 1, "advanced_cell_components": 1, "industrial_display": 1},
    "Autonomous Vehicle": {"electric_vehicle": 1, "sensor_components": 1, "ai_accelerator": 1},
    "Commercial Truck": {"vehicle_components": 2, "industrial_tires": 1, "industrial_controller": 1},
    "Industrial Tires": {"tire_components": 2, "processed_rubber": 1},
    "Railway Track": {"rail_components": 2, "steel_components": 1},
    "Freight Railcar": {"rail_components": 2, "structural_components": 1},
    "Diesel Locomotive": {"rail_components": 2, "industrial_generator": 1},
    "Electric Locomotive": {"rail_components": 2, "electric_motor": 1, "power_electronics": 1},
    "High-Speed Train": {"rail_components": 2, "aerospace_components": 1, "power_electronics": 1},
    "Autonomous Freight Train": {"electric_locomotive": 1, "sensor_components": 1, "network_components": 1},
    "Workboat": {"marine_components": 2, "industrial_generator": 1},
    "Cargo Vessel": {"marine_components": 3, "steel_components": 1},
    "Container Ship": {"cargo_vessel": 1, "marine_components": 2},
    "Tanker": {"cargo_vessel": 1, "industrial_pump": 1},
    "Autonomous Cargo Ship": {"cargo_vessel": 1, "sensor_components": 1, "network_components": 1},
    "High-Speed Vessel": {"marine_components": 1, "turbine_components": 1, "composite_components": 1},
    "Light Aircraft": {"aerospace_components": 2, "avionics_components": 1},
    "Cargo Aircraft": {"aerospace_components": 3, "avionics_components": 1},
    "Commercial Aircraft": {"aerospace_components": 3, "avionics_components": 1, "turbine_components": 1},
    "Jet Engine": {"turbine_components": 2, "nickel_alloy": 1},
    "Advanced Aircraft": {"aerospace_components": 2, "jet_engine": 1, "avionics_components": 1},
    "Autonomous Aircraft": {"advanced_aircraft": 1, "sensor_components": 1, "network_components": 1},
    "Satellite": {"aerospace_components": 1, "solar_components": 1, "telecom_components": 1},
    "Communication Satellite": {"satellite": 1, "telecom_components": 1},
    "Navigation Satellite": {"satellite": 1, "sensor_components": 1},
    "Rocket Engine": {"turbine_components": 2, "titanium_components": 1},
    "Launch Vehicle": {"rocket_engine": 1, "aerospace_components": 2, "control_electronics": 1},
    "Orbital Vehicle": {"launch_vehicle": 1, "avionics_components": 1},
    "Packaged Food": {"food_ingredients": 2, "packaging_components": 1},
    "Processed Food": {"food_ingredients": 2, "vegetable_oil": 1},
    "Packaged Nutrition": {"nutrition_components": 2, "packaging_components": 1},
    "Bakery Products": {"flour": 2, "refined_sugar": 1, "packaging_components": 1},
    "Packaged Meals": {"processed_food": 1, "packaging_components": 1, "nutrition_components": 1},
    "Packaged Beverages": {"fruit_concentrate": 1, "refined_sugar": 1, "packaging_components": 1},
    "Soft Drinks": {"fruit_concentrate": 1, "refined_sugar": 1},
    "Animal Feed": {"corn_meal": 2, "soy_protein": 1},
    "Fertilizer": {"fertilizer_components": 2},
    "Advanced Fertilizer": {"fertilizer": 1, "agricultural_chemicals": 1},
    "Construction Frames": {"wooden_components": 2, "structural_components": 1},
    "Packaging Materials": {"packaging_components": 2},
    "Industrial Packaging": {"packaging_components": 2, "wooden_components": 1},
    "Protective Packaging": {"packaging_components": 1, "insulation_material": 1},
    "Cargo Pallets": {"wooden_components": 2},
    "Commercial Furniture": {"wooden_components": 2, "technical_textile": 1},
    "Sustainable Packaging": {"packaging_components": 1, "bio_composite": 1},
    "Clothing": {"technical_textile": 2},
    "Workwear": {"technical_textile": 1, "industrial_fabric": 1},
    "Protective Clothing": {"industrial_fabric": 2, "processed_rubber": 1},
    "Industrial Clothing": {"industrial_fabric": 2, "technical_textile": 1},
    "Safety Equipment": {"industrial_fabric": 1, "glass_panels": 1, "processed_rubber": 1},
    "Advanced Protective Equipment": {"protective_clothing": 1, "sensor_components": 1, "composite_components": 1},
    "Industrial Plastics": {"polymer": 3, "industrial_resin": 1},
    "Industrial Rubber Products": {"processed_rubber": 2, "synthetic_rubber": 1},
    "Industrial Seals": {"processed_rubber": 1, "precision_components": 1},
    "Industrial Chemicals": {"chemical_feedstock": 2, "sulfuric_acid": 1},
    "Bio-Based Chemicals": {"fermentation_feedstock": 2, "cellulose": 1},
    "Bioplastic": {"biopolymer": 2, "industrial_resin": 1},
    "Biofuel": {"ethanol_components": 2, "chemical_feedstock": 1},
    "Biodiesel": {"biodiesel_feedstock": 2},
    "Crop Protection Products": {"agricultural_chemicals": 2, "industrial_chemicals": 1},
    "Laboratory Equipment": {"glass_panels": 1, "precision_components": 1, "control_electronics": 1},
    "Medical Monitor": {"industrial_display": 1, "sensor_components": 1},
    "Surgical Equipment": {"precision_components": 2, "stainless_components": 1},
    "Diagnostic System": {"medical_monitor": 1, "computing_components": 1, "sensor_components": 1},
    "Advanced Medical Equipment": {"diagnostic_system": 1, "precision_components": 1, "platinum": 1},
    "Communication Cable": {"insulated_wire": 2, "telecom_components": 1},
    "Network Switch": {"network_components": 2, "control_electronics": 1},
    "Router": {"network_components": 1, "telecom_components": 1},
    "Radio Transceiver": {"telecom_components": 2, "rare_earth_metals": 1},
    "Cellular Base Station": {"telecom_components": 2, "structural_components": 1, "power_electronics": 1},
    "High-Speed Network System": {"network_switch": 1, "router": 1, "network_components": 1},
    "Semiconductor Equipment": {"precision_components": 2, "control_electronics": 1, "ceramic_components": 1},
    "Industrial Laser": {"precision_components": 1, "semiconductor_components": 1, "rare_earth_metals": 1},
    "Machine Vision System": {"sensor_components": 2, "computing_components": 1},
    "Autonomous Control System": {"control_electronics": 2, "ai_accelerator": 1},
    "Advanced Semiconductor Equipment": {"semiconductor_equipment": 1, "industrial_laser": 1, "machine_vision_system": 1},
    "Carbon Capture Plant": {"industrial_pump": 1, "compressor_components": 1, "industrial_chemicals": 1},
    "Desalination Plant": {"industrial_pump": 1, "industrial_filter": 0, "power_electronics": 1},
    "Synthetic Fuel Plant": {"industrial_chemicals": 1, "hydrogen": 1, "carbon_capture_plant": 1},
    "Quantum Computing Module": {"superconducting_alloy": 1, "processor_components": 1, "control_electronics": 1},
    "Superconducting Magnet System": {"superconducting_alloy": 2, "power_electronics": 1},
    "Fusion Reactor Module": {"superconducting_magnet_system": 1, "reactor_components": 1, "hydrogen": 1},
}


STAGE_CAPACITY = {
    "extraction": 500,
    "processing": 300,
    "manufacturing": 180,
    "assembly": 100,
}

LEGACY_CAPACITY = {
    "iron_ore": 500,
    "coal": 500,
    "copper_ore": 500,
    "iron": 300,
    "copper": 300,
    "steel": 200,
}

LEGACY_PRICES = {
    "iron_ore": 1.0,
    "coal": 1.2,
    "copper_ore": 1.4,
    "iron": 3.0,
    "copper": 3.5,
    "steel": 8.0,
}


def recipe_value(inputs: dict[str, float], prices: dict[str, float]) -> float:
    return sum(prices[resource_id] * amount for resource_id, amount in inputs.items() if amount > 0)


def priced_output(
    name: str,
    inputs: dict[str, float],
    output_amount: float,
    prices: dict[str, float],
    stage: str,
) -> float:
    resource_id = slug(name)
    if resource_id in LEGACY_PRICES:
        return LEGACY_PRICES[resource_id]
    stage_margin = {"processing": 1.14, "manufacturing": 1.16, "assembly": 1.18}[stage]
    complexity = min(0.08, max(0, len([amount for amount in inputs.values() if amount > 0]) - 1) * 0.025)
    value = recipe_value(inputs, prices) / max(1.0, output_amount)
    return round(max(value * (stage_margin + complexity), value + 0.35), 2)


def ordered_recipes(recipes: list[tuple], known_prices: dict[str, float]) -> list[tuple]:
    pending = list(recipes)
    ordered: list[tuple] = []
    while pending:
        ready = [
            recipe
            for recipe in pending
            if all(amount <= 0 or resource_id in known_prices for resource_id, amount in recipe[1].items())
        ]
        if not ready:
            missing = {
                resource_id
                for recipe in pending
                for resource_id, amount in recipe[1].items()
                if amount > 0 and resource_id not in known_prices
            }
            raise ValueError(f"Recipe dependencies cannot be resolved: {sorted(missing)}")
        for recipe in ready:
            pending.remove(recipe)
            ordered.append(recipe)
            known_prices.setdefault(slug(recipe[0]), 0.01)
    return ordered


STAGE_RANK = {"extraction": 0, "processing": 1, "manufacturing": 2, "assembly": 3}


PROCESSING_PROMOTIONS = {
    "uranium_ore": "nuclear_material",
    "zinc_ore": "galvanized_metal",
    "lead_ore": "shielding_material",
    "vanadium_ore": "vanadium_alloy",
    "palladium_ore": "catalyst_metal",
    "potash": "phosphoric_acid",
    "wheat": "flour",
    "fruit": "fruit_concentrate",
    "potatoes": "starch",
    "rapeseed": "bio_lubricant",
}


MANUFACTURING_PROMOTIONS = {
    "steel": "steel_components",
    "stainless_steel": "stainless_components",
    "aluminum": "aluminum_components",
    "titanium": "titanium_components",
    "tungsten": "precision_components",
    "manganese": "gear_components",
    "chromium": "bearing_components",
    "copper": "electrical_components",
    "gold": "semiconductor_components",
    "silver": "semiconductor_die",
    "high_purity_silicon": "semiconductor_components",
    "rare_earth_metals": "magnetic_components",
    "nickel_alloy": "turbine_components",
    "processed_rubber": "tire_components",
    "synthetic_rubber": "tire_components",
    "polymer": "packaging_components",
    "industrial_resin": "composite_components",
    "carbon_fiber": "composite_components",
    "chemical_feedstock": "chemical_components",
    "sulfuric_acid": "chemical_components",
    "chlorine": "chemical_components",
    "ammonia": "fertilizer_components",
    "phosphoric_acid": "fertilizer_components",
    "hydrogen": "electrolyzer_components",
    "flour": "food_ingredients",
    "corn_meal": "food_ingredients",
    "refined_sugar": "food_ingredients",
    "soy_protein": "nutrition_components",
    "vegetable_oil": "nutrition_components",
    "fruit_concentrate": "nutrition_components",
    "fermentation_feedstock": "bio_material_components",
    "starch": "biopolymer",
    "cellulose": "bio_material_components",
    "bio_lubricant": "bio_material_components",
    "organic_feedstock": "food_ingredients",
    "platinum": "medical_components",
    "palladium": "catalyst_components",
    "catalyst_metal": "catalyst_components",
    "lead": "shielding_components",
    "shielding_material": "shielding_components",
    "nuclear_material": "nuclear_fuel_components",
    "vanadium": "advanced_alloy_components",
    "vanadium_alloy": "advanced_alloy_components",
    "zinc": "galvanized_components",
    "galvanized_metal": "galvanized_components",
    "glass": "glass_panels",
    "ceramics": "ceramic_components",
    "processed_gypsum": "insulation_material",
    "lumber": "wooden_components",
    "wood_pulp": "packaging_components",
    "cotton_fiber": "technical_textile",
    "technical_textile": "industrial_fabric",
    "concrete_components": "structural_components",
    "industrial_gas": "chemical_components",
    "bitumen": "construction_aggregate",
}


ASSEMBLY_OVERRIDES = {
    "Gas Turbine": {"turbine_components": 2, "advanced_alloy_components": 1},
    "Nuclear Fuel Assembly": {"nuclear_fuel_components": 2, "shielding_components": 1},
    "Nuclear Reactor": {"reactor_components": 2, "nuclear_fuel_components": 1, "control_electronics": 1, "structural_components": 1},
    "Industrial Cutting Machine": {"precision_components": 1, "cutting_tooling": 1, "control_electronics": 1},
    "Industrial Computer": {"computing_components": 2, "display_components": 1},
    "Server Rack": {"server_components": 2, "structural_components": 1, "network_components": 1},
    "AI Accelerator": {"ai_compute_components": 2, "power_electronics": 1},
    "AI Server": {"ai_compute_components": 1, "server_components": 1, "network_components": 1},
    "Data Center Module": {"server_components": 2, "grid_storage_components": 1, "structural_components": 1},
    "Supercomputer": {"ai_compute_components": 2, "server_components": 1, "grid_storage_components": 1, "network_components": 1},
    "Servo Motor": {"motor_components": 1, "precision_components": 1, "control_electronics": 1},
    "Robotic Arm": {"precision_components": 2, "motor_components": 1, "control_electronics": 1},
    "Industrial Robot": {"precision_components": 2, "motor_components": 1, "control_electronics": 1, "sensor_components": 1},
    "Advanced Industrial Robot": {"autonomous_components": 2, "sensor_components": 1, "ai_compute_components": 1},
    "Combustion Vehicle": {"vehicle_components": 2, "turbine_components": 1},
    "Electric Vehicle": {"vehicle_components": 1, "battery_components": 2, "motor_components": 1},
    "Premium Electric Vehicle": {"vehicle_components": 1, "advanced_cell_components": 1, "display_components": 1},
    "Autonomous Vehicle": {"vehicle_components": 1, "autonomous_components": 1, "sensor_components": 1, "ai_compute_components": 1},
    "Diesel Locomotive": {"rail_components": 2, "turbine_components": 1},
    "Electric Locomotive": {"rail_components": 2, "motor_components": 1, "power_electronics": 1},
    "Autonomous Freight Train": {"rail_components": 2, "autonomous_components": 1, "network_components": 1},
    "Workboat": {"marine_components": 2, "turbine_components": 1},
    "Container Ship": {"marine_components": 3, "structural_components": 1, "control_electronics": 1},
    "Tanker": {"marine_components": 2, "pump_components": 1, "corrosion_resistant_components": 1},
    "Autonomous Cargo Ship": {"marine_components": 2, "autonomous_components": 1, "sensor_components": 1, "network_components": 1},
    "Advanced Aircraft": {"aerospace_components": 2, "turbine_components": 1, "avionics_components": 1},
    "Autonomous Aircraft": {"aerospace_components": 2, "avionics_components": 1, "autonomous_components": 1, "sensor_components": 1},
    "Communication Satellite": {"aerospace_components": 1, "solar_components": 1, "telecom_components": 1, "network_components": 1},
    "Navigation Satellite": {"aerospace_components": 1, "sensor_components": 1, "telecom_components": 1},
    "Launch Vehicle": {"aerospace_components": 2, "turbine_components": 1, "control_electronics": 1},
    "Orbital Vehicle": {"aerospace_components": 2, "avionics_components": 1, "control_electronics": 1},
    "Processed Food": {"food_ingredients": 2, "nutrition_components": 1},
    "Bakery Products": {"food_ingredients": 2, "packaging_components": 1},
    "Packaged Beverages": {"nutrition_components": 1, "packaging_components": 1},
    "Soft Drinks": {"nutrition_components": 2, "packaging_components": 1},
    "Animal Feed": {"food_ingredients": 2, "nutrition_components": 1},
    "Advanced Fertilizer": {"fertilizer_components": 2, "agricultural_chemicals": 1},
    "Commercial Furniture": {"wooden_components": 2, "industrial_fabric": 1},
    "Sustainable Packaging": {"packaging_components": 1, "bio_composite": 1},
    "Protective Clothing": {"industrial_fabric": 2, "tire_components": 1},
    "Industrial Clothing": {"industrial_fabric": 2, "technical_textile": 1},
    "Safety Equipment": {"industrial_fabric": 1, "glass_panels": 1, "tire_components": 1},
    "Advanced Protective Equipment": {"industrial_fabric": 2, "sensor_components": 1, "composite_components": 1},
    "Industrial Plastics": {"packaging_components": 2, "composite_components": 1},
    "Industrial Rubber Products": {"tire_components": 2, "chemical_components": 1},
    "Industrial Chemicals": {"chemical_components": 2},
    "Bio-Based Chemicals": {"bio_material_components": 2, "chemical_components": 1},
    "Bioplastic": {"biopolymer": 2, "bio_composite": 1},
    "Biofuel": {"ethanol_components": 2, "chemical_components": 1},
    "Crop Protection Products": {"agricultural_chemicals": 2, "chemical_components": 1},
    "Medical Monitor": {"display_components": 1, "sensor_components": 1, "medical_components": 1},
    "Diagnostic System": {"medical_components": 1, "computing_components": 1, "sensor_components": 1},
    "Advanced Medical Equipment": {"medical_components": 2, "precision_components": 1, "sensor_components": 1, "control_electronics": 1},
    "Radio Transceiver": {"telecom_components": 2, "magnetic_components": 1},
    "High-Speed Network System": {"network_components": 3, "control_electronics": 1},
    "Industrial Laser": {"precision_components": 1, "semiconductor_components": 1, "magnetic_components": 1},
    "Advanced Semiconductor Equipment": {"precision_components": 2, "control_electronics": 1, "ceramic_components": 1, "sensor_components": 1},
    "Carbon Capture Plant": {"pump_components": 1, "compressor_components": 1, "chemical_components": 1, "filtration_components": 1},
    "Desalination Plant": {"filtration_components": 1, "membrane_components": 1, "pump_components": 1, "power_electronics": 1},
    "Synthetic Fuel Plant": {"chemical_components": 1, "electrolyzer_components": 1, "catalyst_components": 1},
    "Quantum Computing Module": {"advanced_alloy_components": 1, "processor_components": 1, "control_electronics": 1},
    "Superconducting Magnet System": {"advanced_alloy_components": 2, "power_electronics": 1},
    "Fusion Reactor Module": {"reactor_components": 1, "nuclear_fuel_components": 1, "electrolyzer_components": 1, "power_electronics": 1},
    "Industrial Equipment": {"steel_components": 2, "electrical_components": 1, "iron_components": 1},
    "Construction Materials": {"concrete_components": 2, "wooden_components": 1, "asphalt_components": 1},
    "Industrial Hall Modules": {"structural_components": 2, "galvanized_components": 1, "insulation_material": 1, "glass_panels": 1},
    "Grid Battery": {"battery_components": 2, "battery_materials": 1, "power_electronics": 1},
    "Basic Chip": {"semiconductor_components": 1, "silicon_substrate": 1, "copper_wire": 1},
    "Packaged Food": {"food_ingredients": 2, "sweetener_components": 1, "packaging_components": 1},
    "Fertilizer": {"fertilizer_components": 2, "agricultural_mineral_components": 1},
    "Industrial Rubber Products": {"tire_components": 2, "rubber_blend_components": 1, "chemical_components": 1},
    "Industrial Chemicals": {"chemical_components": 2, "gas_handling_components": 1},
    "Quantum Computing Module": {"refractory_alloy_components": 1, "processor_components": 1, "control_electronics": 1},
    "Superconducting Magnet System": {"refractory_alloy_components": 2, "power_electronics": 1},
    "Fusion Reactor Module": {"reactor_components": 1, "nuclear_fuel_components": 1, "electrolyzer_components": 1, "refractory_alloy_components": 1},
}


def trim_inputs(inputs: dict[str, float], prices: dict[str, float] | None = None, max_inputs: int = 4) -> dict[str, float]:
    cleaned = {resource_id: amount for resource_id, amount in inputs.items() if amount > 0}
    if len(cleaned) <= max_inputs:
        return cleaned
    if prices is None:
        return dict(sorted(cleaned.items(), key=lambda item: (-item[1], item[0]))[:max_inputs])
    ranked = sorted(cleaned.items(), key=lambda item: (-(prices.get(item[0], 1.0) * item[1]), item[0]))
    return dict(ranked[:max_inputs])


def round_inputs(inputs: dict[str, float]) -> dict[str, float]:
    rounded: dict[str, float] = {}
    for resource_id, amount in inputs.items():
        if amount <= 0:
            continue
        value = round(amount, 2)
        rounded[resource_id] = int(value) if value.is_integer() else value
    return rounded


def recipe_map(recipes: list[tuple]) -> dict[str, tuple[dict[str, float], float]]:
    return {slug(recipe[0]): (recipe[1], recipe[2]) for recipe in recipes}


def flatten_inputs_to_stage(
    inputs: dict[str, float],
    target_stage: str,
    stage_by_resource: dict[str, str],
    recipes_by_stage: dict[str, dict[str, tuple[dict[str, float], float]]],
    promotions: dict[str, str],
    trail: tuple[str, ...] = (),
) -> dict[str, float]:
    target_rank = STAGE_RANK[target_stage]
    flattened: dict[str, float] = {}
    for resource_id, amount in inputs.items():
        if amount <= 0:
            continue
        stage = stage_by_resource.get(resource_id)
        if stage == target_stage:
            flattened[resource_id] = flattened.get(resource_id, 0) + amount
            continue
        if resource_id in trail:
            promoted = promotions.get(resource_id)
            if not promoted:
                raise ValueError(f"Recursive content dependency cannot be flattened: {' -> '.join((*trail, resource_id))}")
            flattened[promoted] = flattened.get(promoted, 0) + amount
            continue
        if stage is not None and STAGE_RANK[stage] > target_rank and resource_id in recipes_by_stage.get(stage, {}):
            source_inputs, output_amount = recipes_by_stage[stage][resource_id]
            scaled = {source_id: source_amount * amount / max(1.0, output_amount) for source_id, source_amount in source_inputs.items()}
            nested = flatten_inputs_to_stage(scaled, target_stage, stage_by_resource, recipes_by_stage, promotions, (*trail, resource_id))
            for source_id, source_amount in nested.items():
                flattened[source_id] = flattened.get(source_id, 0) + source_amount
            continue
        promoted = promotions.get(resource_id)
        if promoted and stage_by_resource.get(promoted) == target_stage:
            flattened[promoted] = flattened.get(promoted, 0) + amount
            continue
        if promoted:
            nested = flatten_inputs_to_stage({promoted: amount}, target_stage, stage_by_resource, recipes_by_stage, promotions, (*trail, resource_id))
            for source_id, source_amount in nested.items():
                flattened[source_id] = flattened.get(source_id, 0) + source_amount
            continue
        raise ValueError(f"{resource_id} cannot be used as {target_stage} input")
    return flattened


def normalize_industrial_recipes() -> tuple[list[tuple], list[tuple], list[tuple]]:
    processing_stage = {slug(name): "processing" for name, *_ in PROCESSING_RECIPES}
    manufacturing_stage = {slug(name): "manufacturing" for name, *_ in MANUFACTURING_RECIPES}
    assembly_stage = {slug(name): "assembly" for name in ASSEMBLY_INPUTS}
    stage_by_resource = {
        **{slug(name): "extraction" for name, *_ in EXTRACTION},
        **processing_stage,
        **manufacturing_stage,
        **assembly_stage,
    }
    recipes_by_stage = {
        "processing": recipe_map(PROCESSING_RECIPES),
        "manufacturing": recipe_map(MANUFACTURING_RECIPES),
        "assembly": {slug(name): (inputs, 1) for name, inputs in ASSEMBLY_INPUTS.items()},
    }

    normalized_processing = []
    extraction_prices = {slug(name): price for name, price, _ in EXTRACTION}
    for name, inputs, amount, cycle, power, aliases in PROCESSING_RECIPES:
        flattened = flatten_inputs_to_stage(inputs, "extraction", stage_by_resource, recipes_by_stage, {})
        normalized_processing.append((name, round_inputs(trim_inputs(flattened, extraction_prices)), amount, cycle, power, aliases))

    normalized_processing_map = recipe_map(normalized_processing)
    stage_by_resource.update({slug(name): "processing" for name, *_ in normalized_processing})
    recipes_by_stage["processing"] = normalized_processing_map

    normalized_manufacturing = []
    for name, inputs, amount in MANUFACTURING_RECIPES:
        flattened = flatten_inputs_to_stage(inputs, "processing", stage_by_resource, recipes_by_stage, PROCESSING_PROMOTIONS)
        normalized_manufacturing.append((name, round_inputs(trim_inputs(flattened)), amount))

    normalized_manufacturing_map = recipe_map(normalized_manufacturing)
    stage_by_resource.update({slug(name): "manufacturing" for name, *_ in normalized_manufacturing})
    recipes_by_stage["manufacturing"] = normalized_manufacturing_map

    normalized_assembly = []
    for name, raw_inputs in ASSEMBLY_INPUTS.items():
        inputs = ASSEMBLY_OVERRIDES.get(name, raw_inputs)
        flattened = flatten_inputs_to_stage(inputs, "manufacturing", stage_by_resource, recipes_by_stage, MANUFACTURING_PROMOTIONS)
        normalized_assembly.append((name, round_inputs(trim_inputs(flattened)), 1))

    return normalized_processing, normalized_manufacturing, normalized_assembly


def option(recipe_id: str, name: str, stage: str, inputs: dict[str, float], output_amount: float, cycle: float, power: float | None = None, aliases: Iterable[str] = ()) -> dict:
    output_resource = slug(name)
    data = {
        "id": recipe_id,
        "name": name,
        "stage": stage,
        "output_resource": output_resource,
        "output_amount": output_amount,
        "cycle_seconds": cycle,
        "input_resources": {resource: amount for resource, amount in inputs.items() if amount > 0},
        "icon_key": visual_icon_key(output_resource),
        "accent_key": visual_accent_key(output_resource),
    }
    if power is not None:
        data["power_draw"] = power
    aliases = list(aliases)
    if aliases:
        data["aliases"] = aliases
    return data


def recipe_card(recipe_id: str, name: str, stage: str, inputs: dict[str, float], output_amount: float, duration: int) -> dict:
    output_resource = slug(name)
    return {
        "id": recipe_id,
        "kind": "recipe",
        "name": f"{name} Recipe",
        "duration_ticks": duration,
        "stage": stage,
        "input_resources": {resource: amount for resource, amount in inputs.items() if amount > 0},
        "output_resources": {output_resource: output_amount},
        "icon_key": visual_icon_key(output_resource),
        "accent_key": visual_accent_key(output_resource),
    }


def machine(definition_id: str, aliases: list[str], name: str, machine_type: str, mk: int, output: float, power: float, cycle: float, default_output: str, options: list[dict], alias_defaults: dict[str, str] | None = None) -> dict:
    data = {
        "id": definition_id,
        "kind": "machine",
        "name": name,
        "machine_type": machine_type,
        "stage": machine_type,
        "mk_level": mk,
        "base_output_per_tick": output,
        "base_power_draw": power,
        "cycle_seconds": cycle,
        "input_resources": options[0].get("input_resources", {}),
        "output_resource": default_output,
        "icon_key": default_output,
        "accent_key": default_output,
        "production_options": options,
    }
    if aliases:
        data["aliases"] = aliases
    if alias_defaults:
        data["alias_default_productions"] = alias_defaults
    return data


def main() -> None:
    processing_recipes, manufacturing_recipes, assembly_recipes = normalize_industrial_recipes()
    prices = {slug(name): price for name, price, _ in EXTRACTION}
    resources: dict[str, dict] = {}

    def add_resource(resource_id: str, name: str, stage: str, price: float) -> None:
        capacity = LEGACY_CAPACITY.get(resource_id, STAGE_CAPACITY[stage])
        resources[resource_id] = {
            "id": resource_id,
            "name": name,
            "default_capacity": capacity,
            "base_market_price": round(price, 2),
            "volatility": round(0.0065 + min(price, 40.0) * 0.00008 + {"extraction": 0.0, "processing": 0.0005, "manufacturing": 0.0010, "assembly": 0.0014}[stage], 5),
            "icon_key": visual_icon_key(resource_id),
            "accent_key": visual_accent_key(resource_id),
            "category": visual_category(resource_id, stage),
        }

    for name, price, _ in EXTRACTION:
        add_resource(slug(name), name, "extraction", price)

    processor_options = []
    recipe_cards = []
    for name, inputs, amount, cycle, power, aliases in ordered_recipes(processing_recipes, dict(prices)):
        rid = slug(name)
        prices[rid] = priced_output(name, inputs, amount, prices, "processing")
        add_resource(rid, name, "processing", prices[rid])
        recipe_id = f"recipe.processor.{rid}"
        processor_options.append(option(recipe_id, name, "processor", inputs, amount, cycle, power, aliases))
        recipe_cards.append(recipe_card(recipe_id, name, "processor", inputs, amount, int(cycle)))

    fabricator_options = []
    for name, inputs, amount in ordered_recipes(manufacturing_recipes, dict(prices)):
        rid = slug(name)
        prices[rid] = priced_output(name, inputs, amount, prices, "manufacturing")
        add_resource(rid, name, "manufacturing", prices[rid])
        recipe_id = f"recipe.fabricator.{rid}"
        fabricator_options.append(option(recipe_id, name, "fabricator", inputs, amount, 6, 10))
        recipe_cards.append(recipe_card(recipe_id, name, "fabricator", inputs, amount, 6))

    assembler_options = []
    for name, inputs, _ in ordered_recipes(assembly_recipes, dict(prices)):
        rid = slug(name)
        prices[rid] = priced_output(name, inputs, 1, prices, "assembly")
        add_resource(rid, name, "assembly", prices[rid])
        recipe_id = f"recipe.assembler.{rid}"
        assembler_options.append(option(recipe_id, name, "assembler", inputs, 1, 8, 12))
        recipe_cards.append(recipe_card(recipe_id, name, "assembler", inputs, 1, 8))

    extractor_options = [
        option(f"resource.{slug(name)}", name, "extractor", {}, 12, 3)
        for name, _, _ in EXTRACTION
    ]
    cards = [
        machine("machine.extractor.mk1", ["machine.mining_drill.mk1"], "Extractor MK I", "extractor", 1, 12, 6, 3, "iron_ore", extractor_options),
        machine("machine.extractor.mk2", ["machine.mining_drill.mk2"], "Extractor MK II", "extractor", 2, 30, 14, 3, "iron_ore", extractor_options),
        machine("machine.extractor.mk3", ["machine.mining_drill.mk3"], "Extractor MK III", "extractor", 3, 60, 25, 3, "iron_ore", extractor_options),
        machine(
            "machine.processor.mk1",
            ["machine.furnace.mk1", "machine.blast_furnace.mk1"],
            "Processor MK I",
            "processor",
            1,
            6,
            8,
            4,
            "iron",
            processor_options,
            {"machine.furnace.mk1": "recipe.processor.iron", "machine.blast_furnace.mk1": "recipe.processor.steel"},
        ),
        machine("machine.fabricator.mk1", [], "Fabricator MK I", "fabricator", 1, 1, 10, 6, fabricator_options[0]["output_resource"], fabricator_options),
        machine("machine.assembler.mk1", [], "Assembler MK I", "assembler", 1, 1, 12, 8, slug(next(iter(ASSEMBLY_INPUTS))), assembler_options),
        {
            "id": "energy.solar_array.mk1",
            "kind": "energy",
            "name": "Solar Array MK I",
            "energy_type": "solar",
            "mk_level": 1,
            "base_power_output": 20,
            "input_resources": {},
        },
        *recipe_cards,
        {
            "id": "freight.truck.class1",
            "kind": "freight",
            "name": "Freight Truck · Class I",
            "family": "truck",
            "class_level": 1,
            "class_label": "Class I",
            "facility_id": "garage_depot",
            "facility_name": "Garage / Depot",
            "base_capacity": 40,
            "base_transport_time_seconds": 60,
        },
        {
            "id": "freight.train.class1",
            "kind": "freight",
            "name": "Freight Train · Class I",
            "family": "train",
            "class_level": 1,
            "class_label": "Class I",
            "facility_id": "rail_station",
            "facility_name": "Rail Station",
            "base_capacity": 180,
            "base_transport_time_seconds": 150,
        },
        {
            "id": "freight.ship.class1",
            "kind": "freight",
            "name": "Cargo Ship · Class I",
            "family": "ship",
            "class_level": 1,
            "class_label": "Class I",
            "facility_id": "harbor",
            "facility_name": "Harbor",
            "base_capacity": 600,
            "base_transport_time_seconds": 420,
        },
        {
            "id": "freight.aircraft.class1",
            "kind": "freight",
            "name": "Cargo Aircraft · Class I",
            "family": "aircraft",
            "class_level": 1,
            "class_label": "Class I",
            "facility_id": "airport",
            "facility_name": "Airport",
            "base_capacity": 24,
            "base_transport_time_seconds": 25,
        },
    ]

    (DATA / "resource_definitions.json").write_text(
        json.dumps({"resources": list(resources.values())}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (DATA / "game_definitions.json").write_text(
        json.dumps({"cards": cards}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
