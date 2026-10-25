"""Rebuild the versioned Research V1 catalog. IDs are permanent save identities."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src/production_zero/data"

# Authored canonical IDs, never inferred from names or recipe ancestry.
DOMAINS = {
    "agriculture": "wheat corn soybeans sugarcane rapeseed potatoes fruit flour starch vegetable_oil fermentation_feedstock corn_meal raw_sugar refined_sugar soy_oil soy_protein fruit_concentrate food_ingredients nutrition_components packaged_food processed_food packaged_nutrition bakery_products packaged_beverages packaged_meals soft_drinks animal_feed sweetener_components",
    "forestry": "timber natural_rubber lumber wood_pulp cellulose treated_lumber wooden_components packaging_components packaging_materials industrial_packaging protective_packaging cargo_pallets commercial_furniture sustainable_packaging",
    "metals": "iron_ore copper_ore bauxite nickel_ore zinc_ore lead_ore tin_ore manganese_ore chromium_ore titanium_ore tungsten_ore cobalt_ore molybdenum_ore vanadium_ore silver_ore gold_ore platinum_ore palladium_ore lithium_ore uranium_ore rare_earth_ore niobium_ore iron steel stainless_steel copper aluminum zinc lead tin nickel titanium tungsten manganese chromium cobalt molybdenum vanadium lithium gold silver platinum palladium rare_earth_metals niobium nickel_alloy superconducting_alloy galvanized_metal shielding_material vanadium_alloy catalyst_metal nuclear_material copper_wire iron_components steel_components stainless_components aluminum_components titanium_components galvanized_components shielding_components advanced_alloy_components catalyst_components refractory_alloy_components corrosion_resistant_components",
    "oil_gas": "crude_oil natural_gas coal bitumen",
    "chemicals": "borate_ore graphite phosphate_rock potash salt sulfur fluorspar magnesite purified_graphite carbon_fiber chlorine ammonia potassium_compound bio_lubricant organic_feedstock bio_composite biodiesel_feedstock polymer synthetic_rubber industrial_resin chemical_feedstock sulfuric_acid phosphoric_acid industrial_gas hydrogen processed_rubber agricultural_chemicals biopolymer gas_handling_components rubber_blend_components chemical_components industrial_rubber_products industrial_chemicals bio_based_chemicals industrial_plastics industrial_seals bioplastic crop_protection_products fertilizer advanced_fertilizer fertilizer_components ethanol_components agricultural_mineral_components composite_components bio_material_components",
    "electronics": "quartz silica_sand silicon high_purity_silicon silicon_substrate insulated_wire electrical_cable power_cable electrical_components transformer_components magnetic_components display_components memory_components processor_components microcontroller memory_module industrial_controller industrial_display industrial_computer server server_rack compute_node ai_accelerator ai_server data_center_module supercomputer communication_cable router radio_transceiver cellular_base_station autonomous_control_system power_electronics semiconductor_components semiconductor_die sensor_components control_electronics computing_components telecom_components network_components basic_chip microchip cpu industrial_sensor network_switch high_speed_network_system semiconductor_equipment advanced_semiconductor_equipment quantum_computing_module autonomous_components server_components ai_compute_components machine_vision_system",
    "construction": "limestone gypsum clay kaolin glass cement ceramics processed_gypsum glass_panels insulation_material construction_materials reinforced_concrete structural_systems industrial_hall_modules prefabricated_structures industrial_glass_panels industrial_insulation engineered_structures construction_frames structural_components concrete_components ceramic_components asphalt_components",
    "machinery": "cutting_tooling mining_drill heavy_mining_drill excavator industrial_crusher industrial_pump industrial_compressor hydraulic_system electric_motor precision_motor gearbox advanced_furnace robotic_actuator servo_motor robotic_arm industrial_robot industrial_drone autonomous_mobile_robot advanced_industrial_robot industrial_laser carbon_capture_plant desalination_plant superconducting_magnet_system precision_components gear_components bearing_components hydraulic_components pump_components compressor_components mining_components motor_components filtration_components membrane_components industrial_equipment heavy_machinery mining_equipment cnc_machine industrial_cutting_machine processing_equipment safety_equipment advanced_protective_equipment laboratory_equipment",
    "automotive": "vehicle_components tire_components utility_vehicle combustion_vehicle electric_vehicle premium_electric_vehicle autonomous_vehicle commercial_truck industrial_tires",
    "aerospace": "aerospace_components avionics_components jet_engine light_aircraft cargo_aircraft commercial_aircraft advanced_aircraft autonomous_aircraft satellite communication_satellite navigation_satellite rocket_engine launch_vehicle orbital_vehicle",
    "energy": "transformer switchgear industrial_relay industrial_generator industrial_inverter advanced_cell_components electrolyzer_components turbine_components battery_materials battery_components storage_components solar_components wind_components reactor_components nuclear_fuel_components grid_storage_components solar_array wind_turbine steam_turbine grid_battery grid_storage_system nuclear_fuel_assembly nuclear_reactor biofuel biodiesel synthetic_fuel_plant fusion_reactor_module gas_turbine hydrogen_electrolyzer high_voltage_equipment",
    "textiles": "cotton cotton_fiber technical_textile industrial_fabric fiber_components clothing workwear protective_clothing industrial_clothing",
    "rail": "rail_components railway_track freight_railcar diesel_locomotive electric_locomotive high_speed_train autonomous_freight_train",
    "maritime": "marine_components workboat cargo_vessel tanker high_speed_vessel container_ship autonomous_cargo_ship",
    "medical": "medical_components medical_monitor surgical_equipment diagnostic_system advanced_medical_equipment",
}

# The fourth field retains the original sixth-node artwork, not a product effect.
INDUSTRIES = [
    ("agriculture", "Agriculture & Food", "wheat", "packaged_food"),
    ("forestry", "Forestry & Wood", "timber", "lumber"),
    ("metals", "Metals & Metallurgy", "copper", "copper_wire"),
    ("oil_gas", "Oil & Gas", "crude_oil", "natural_gas"),
    ("chemicals", "Chemicals", "polymer", "industrial_chemicals"),
    ("electronics", "Electronics", "microchip", "cpu"),
    ("construction", "Construction Materials", "cement", "reinforced_concrete"),
    ("machinery", "Machinery & Industrial Goods", "industrial_robot", "heavy_machinery"),
    ("automotive", "Automotive", "electric_vehicle", "commercial_truck"),
    ("aerospace", "Aerospace", "satellite", "cargo_aircraft"),
    ("energy", "Energy Technology", "grid_battery", "solar_array"),
    ("textiles", "Textiles", "cotton", "workwear"),
    ("rail", "Rail Transport", "high_speed_train", "freight_railcar"),
    ("maritime", "Maritime", "container_ship", "cargo_vessel"),
    ("medical", "Medical Technology", "medical_monitor", "diagnostic_system"),
]
COMPANY = [
    ("general", "General / Company", "industrial_computer", "value", "Company value", .001, .005),
    ("production", "Production", "industrial_equipment", "production_speed", "Global cycle rate", .001, .005),
    ("energy", "Energy", "solar_array", "energy_output", "Power generation", .002, .005),
    ("freight", "Freight & Logistics", "commercial_truck", "freight_capacity", "Freight capacity", .002, .005),
    ("storage", "Storage", "cargo_pallets", "storage_capacity", "Warehouse capacity", .005, .01),
    ("contracts", "Contracts", "industrial_packaging", "contract_value", "Contract cash", .001, .005),
]


def main():
    resources = {r["id"]: r for r in json.loads((ROOT / "resource_definitions.json").read_text())["resources"]}
    mapping = {}
    for domain, ids in DOMAINS.items():
        for rid in ids.split():
            assert rid not in mapping, f"Duplicate domain: {rid}"
            mapping[rid] = domain
    assert set(mapping) == set(resources), ("Missing", set(resources) - set(mapping), "Extra", set(mapping) - set(resources))
    (ROOT / "research_domains.json").write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    trees, nodes, slots = [], [], []
    for family, specs in (("company", COMPANY), ("industry", INDUSTRIES)):
        for spec in specs:
            key, name, icon = spec[:3]
            tid = f"{family}.{key}"
            trees.append(dict(id=tid, name=name, family=family, icon_resource=icon, order=len(trees)))
            effect, label, small, major = spec[3:] if family == "company" else ("value", f"{name} value", .002, .005)
            target = "*" if family == "company" else key
            scope = "global" if family == "company" else "domain"
            previous = []
            for section in range(5):
                mid = f"{tid}.s{section + 1}.major"
                section_name = ("Foundation", "Development", "Precision", "Excellence", "Mastery")[section]
                def node(nid, title, typ, prereqs, value, row, col, *, legacy_icon=None):
                    rid = legacy_icon or icon
                    bonus = label
                    descriptions = {
                        "value": "Adds to Market sale value and new Contract quotes for this industry. Production speed stays the same." if family == "industry" else "Adds to Market sale value and new Contract quotes for all products.",
                        "production_speed": "All machine stages run faster together. Input and output quantities per cycle stay the same.",
                        "energy_output": "Increases power generated by all installed power modules.",
                        "freight_capacity": "Increases capacity for newly dispatched freight shipments.",
                        "storage_capacity": "Increases shared warehouse capacity. Respec never deletes stored goods.",
                        "contract_value": "Adds to the cash contribution of every product in newly accepted Contracts.",
                    }
                    nodes.append(dict(id=nid, tree_id=tid, name=title, description=f"+{value * 100:g}% {bonus}. " + descriptions[effect], node_type=typ, cost=1, icon_resource=rid, prerequisites=prereqs, effect_type=effect, effect_scope=scope, effect_target=target, effect_value=value, bonus_label=bonus, row=row, position=col))
                node(mid, section_name, "major", previous, round(major * (1 + section * .5), 6), section * 3, 1)
                if family == "industry" and section > 0:
                    slots.append(dict(id=f"{tid}.specialization.{section}", tree_id=tid, major_node_id=mid, cost=1))
                if family == "industry" and section == 4:
                    continue  # Industry progression ends at Major V; four clusters.
                previous = []
                for index in range(6):
                    nid = f"{tid}.s{section + 1}.n{index + 1}"
                    legacy_icon = spec[3] if family == "industry" and index == 5 else None
                    prereqs = [mid] if index < 3 else [f"{tid}.s{section + 1}.n{index - 2}"]
                    node(nid, "Value standards" if family == "industry" else label, "small", prereqs, small, section * 3 + 1 + index // 3, index % 3, legacy_icon=legacy_icon)
                    if index >= 3:
                        previous.append(nid)
    (ROOT / "research_definitions.json").write_text(json.dumps(dict(version=3, trees=trees, nodes=nodes,
        specialization=dict(value_bonus=.01, slots=slots)), indent=2) + "\n", encoding="utf-8")
    print(f"{len(mapping)} products; {len(trees)} trees; {len(nodes)} nodes; {sum(n['node_type'] == 'major' for n in nodes)} majors")


if __name__ == "__main__":
    main()
