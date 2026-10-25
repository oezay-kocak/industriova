# Unlock Tree progression audit — 2026-09-10

> Scope: audit/design data only. Runtime code, UI, definitions, saves, tests, and balance were not changed. Runtime definitions and evaluation code are the source of truth.

## 1. Executive summary

The current production-unlock model is a deterministic directed acyclic graph of **353 nodes** and **708 directed quantity-requirement edges**. It has **49 inputless roots**, of which **9 are canonical new-game unlocks**, and a maximum edge depth of **3** (root depth 0). Every normal locked node is unlocked automatically when all applicable gates are true: its company level is high enough, every input production is already unlocked, and lifetime accepted production of every input reaches the destination stage's fixed threshold. There are no player choices, research points, OR branches, or consumptive unlock payments.

`FIRST PRODUCTION COMPLETE` and family `MASTERY` are not unlock requirements. They award company XP once; that XP can indirectly cause a level-up and therefore satisfy a level gate. They must not be drawn as dependency edges. The tree should show concrete counters such as `COPPER ORE 72 / 120`, plus `LEVEL 11` where applicable.

The immediate unlock topology happens to use each production option's `input_resources`, so parent relationships match immediate recipe inputs today. The graphs are still semantically different: unlock quantities are fixed by destination stage (120/60/60), use cumulative accepted output, are not consumed, and are combined with company-level gates.

## 2. Exact unlock mechanisms

| Mechanism | Internal representation / definition | Evaluation | Progress and player action | Result | Cardinality / coexistence |
|---|---|---|---|---|---|
| Canonical inputless root/start | Progression entry plus a runtime option with empty `input_resources` | `_option_requirements_met`: company level only; initialization runs the fixed-point evaluator | No quantity counter; gain company levels | Adds canonical `production_id` to `unlocked_production_ids` | No quantity parent; can be level gated. Nine level-1 roots start available, 40 roots unlock at later levels |
| Quantity dependency | `ProductionUnlockRequirement(resource_id, quantity)` generated from every runtime input key | All parents must be unlocked and every `lifetime_produced[parent] >= quantity` | Run production with storage room; only positive accepted output counts | Unlocks destination option | One to four parents; strict AND; always coexists with destination level gate |
| Company level gate | `resources[output].company_level` in `resource_progression.json` | `state.company.level >= configured level` | Any company XP source: accepted-production continuity/efficiency, first production, family mastery, or contracts | Directly unlocks an inputless root, or permits quantity checks for a non-root | Present on every node and AND-combined with quantity parents |
| Fixed-point/startup reevaluation | `initialize_production_progress` / `update_production_unlocks` | Rescans all runtime options until no new option unlocks | Startup, accepted production, and level gains invoke it | Resolves all satisfied nodes, including same-call cascades | Applies existing gates; not a separate requirement |
| Save migration / grandfathering | `migrate_production_progress` | Preserves stored unlock IDs, selected productions, and positive-lifetime outputs; missing legacy progress seeds lifetime from current stock | Load/migrate an old save | Can mark historically used/selected nodes unlocked, then runs normal fixed-point evaluation; clears pending notices | Save-specific compatibility override; may bypass canonical ancestry and must not redefine roots |

`pending_unlock_ids` is an event-feed notification queue, not an availability gate. Production aliases assist lookup but do not define graph nodes.

### Thresholds

| Destination stage | Required lifetime accepted production of each parent |
|---|---:|
| Processor | 120 |
| Fabricator | 60 |
| Assembler | 60 |

Inputless Extractor, Drilling, and Agriculture options have no quantity requirement. The threshold belongs to the child stage, not the source or recipe input amount.

## 3. Root nodes

There are 49 structural roots: runtime options with no inputs. The nine marked `Yes` are logical starting nodes for a fresh-game tree; the other 40 remain roots but are company-level gated.

| Resource ID | Display name | Runtime stage | Level | Begins unlocked |
|---|---|---|---:|---|
| `bauxite` | Bauxite | Extractor | 1 | Yes |
| `borate_ore` | Borate Ore | Extractor | 13 | No |
| `chromium_ore` | Chromium Ore | Extractor | 11 | No |
| `clay` | Clay | Extractor | 3 | No |
| `coal` | Coal | Extractor | 1 | Yes |
| `cobalt_ore` | Cobalt Ore | Extractor | 15 | No |
| `copper_ore` | Copper Ore | Extractor | 1 | Yes |
| `corn` | Corn | Agriculture | 2 | No |
| `cotton` | Cotton | Agriculture | 4 | No |
| `crude_oil` | Crude Oil | Drilling | 1 | Yes |
| `fluorspar` | Fluorspar | Extractor | 13 | No |
| `fruit` | Fruit | Agriculture | 4 | No |
| `gold_ore` | Gold Ore | Extractor | 18 | No |
| `graphite` | Graphite | Extractor | 13 | No |
| `gypsum` | Gypsum | Extractor | 3 | No |
| `iron_ore` | Iron Ore | Extractor | 1 | Yes |
| `kaolin` | Kaolin | Extractor | 3 | No |
| `lead_ore` | Lead Ore | Extractor | 9 | No |
| `limestone` | Limestone | Extractor | 1 | Yes |
| `lithium_ore` | Lithium Ore | Extractor | 15 | No |
| `magnesite` | Magnesite | Extractor | 13 | No |
| `manganese_ore` | Manganese Ore | Extractor | 9 | No |
| `molybdenum_ore` | Molybdenum Ore | Extractor | 22 | No |
| `natural_gas` | Natural Gas | Drilling | 5 | No |
| `natural_rubber` | Natural Rubber | Agriculture | 5 | No |
| `nickel_ore` | Nickel Ore | Extractor | 11 | No |
| `niobium_ore` | Niobium Ore | Extractor | 22 | No |
| `palladium_ore` | Palladium Ore | Extractor | 20 | No |
| `phosphate_rock` | Phosphate Rock | Extractor | 7 | No |
| `platinum_ore` | Platinum Ore | Extractor | 20 | No |
| `potash` | Potash | Extractor | 7 | No |
| `potatoes` | Potatoes | Agriculture | 2 | No |
| `quartz` | Quartz | Extractor | 1 | Yes |
| `rapeseed` | Rapeseed | Agriculture | 4 | No |
| `rare_earth_ore` | Rare Earth Ore | Extractor | 15 | No |
| `salt` | Salt | Extractor | 7 | No |
| `silica_sand` | Silica Sand | Extractor | 3 | No |
| `silver_ore` | Silver Ore | Extractor | 18 | No |
| `soybeans` | Soybeans | Agriculture | 2 | No |
| `sugarcane` | Sugarcane | Agriculture | 4 | No |
| `sulfur` | Sulfur | Extractor | 7 | No |
| `timber` | Timber | Agriculture | 1 | Yes |
| `tin_ore` | Tin Ore | Extractor | 9 | No |
| `titanium_ore` | Titanium Ore | Extractor | 22 | No |
| `tungsten_ore` | Tungsten Ore | Extractor | 22 | No |
| `uranium_ore` | Uranium Ore | Extractor | 25 | No |
| `vanadium_ore` | Vanadium Ore | Extractor | 22 | No |
| `wheat` | Wheat | Agriculture | 1 | Yes |
| `zinc_ore` | Zinc Ore | Extractor | 9 | No |

Migration/startup compatibility has no fixed second root list. A save may grandfather any stored unlocked ID, selected production, or positive-lifetime output. A legacy payload without progression also copies current stock into lifetime progress and grandfathers that resource's production. These are state overlays, not canonical roots; display them as unlocked without rerouting the graph.

## 4. Directed dependency graph summary

| Depth | Meaning | Nodes | Runtime stages |
|---:|---|---:|---|
| 0 | Inputless primary roots | 49 | Agriculture 10, Drilling 2, Extractor 37 |
| 1 | Production chain tier 1 | 68 | Processor 68 |
| 2 | Production chain tier 2 | 86 | Fabricator 86 |
| 3 | Production chain tier 3 | 150 | Assembler 150 |

All incoming edges are AND. Company level is a separate AND gate. There are no OR conditions. The largest fan-out is 32, from `control_electronics`. There are 252 multi-parent nodes; maximum parent count is 4.

### Production dependency versus unlock dependency

Current parent IDs are derived from `ProductionOptionDefinition.input_resources`, so immediate topology equals recipe-input topology. Meaning differs:

- Recipe amounts and cycle consumption are ignored by unlock evaluation.
- Unlocks require fixed lifetime totals: 120 per input for Processor children; 60 for Fabricator; 60 for Assembler.
- Progress persists after inventory is spent and cannot be advanced by bought/freighted stock in current-schema saves.
- Every node also has a company-level gate, absent from recipes.

## 5. Quantity-gate table

Each row is one destination unlock. Multiple sources are separate incoming edges and all must reach the amount.

| Source resource(s), all AND | Required amount per source | Unlocked resource |
|---|---:|---|
| Aerospace Components (`aerospace_components`) + Avionics Components (`avionics_components`) + Turbine Components (`turbine_components`) | 60 each | Advanced Aircraft (`advanced_aircraft`) |
| Titanium (`titanium`) + Vanadium (`vanadium`) + Vanadium Alloy (`vanadium_alloy`) | 60 each | Advanced Alloy Components (`advanced_alloy_components`) |
| Aluminum (`aluminum`) + Cobalt (`cobalt`) + Lithium (`lithium`) + Purified Graphite (`purified_graphite`) | 60 each | Advanced Cell Components (`advanced_cell_components`) |
| Agricultural Chemicals (`agricultural_chemicals`) + Fertilizer Components (`fertilizer_components`) | 60 each | Advanced Fertilizer (`advanced_fertilizer`) |
| Ceramic Components (`ceramic_components`) + Control Electronics (`control_electronics`) + Stainless Components (`stainless_components`) | 60 each | Advanced Furnace (`advanced_furnace`) |
| AI Compute Components (`ai_compute_components`) + Autonomous Components (`autonomous_components`) + Sensor Components (`sensor_components`) | 60 each | Advanced Industrial Robot (`advanced_industrial_robot`) |
| Control Electronics (`control_electronics`) + Medical Components (`medical_components`) + Precision Components (`precision_components`) + Sensor Components (`sensor_components`) | 60 each | Advanced Medical Equipment (`advanced_medical_equipment`) |
| Composite Components (`composite_components`) + Industrial Fabric (`industrial_fabric`) + Sensor Components (`sensor_components`) | 60 each | Advanced Protective Equipment (`advanced_protective_equipment`) |
| Ceramic Components (`ceramic_components`) + Control Electronics (`control_electronics`) + Precision Components (`precision_components`) + Sensor Components (`sensor_components`) | 60 each | Advanced Semiconductor Equipment (`advanced_semiconductor_equipment`) |
| Aluminum (`aluminum`) + Carbon Fiber (`carbon_fiber`) + Titanium (`titanium`) | 60 each | Aerospace Components (`aerospace_components`) |
| Chemical Feedstock (`chemical_feedstock`) + Chlorine (`chlorine`) + Sulfuric Acid (`sulfuric_acid`) | 60 each | Agricultural Chemicals (`agricultural_chemicals`) |
| Phosphoric Acid (`phosphoric_acid`) + Potassium Compound (`potassium_compound`) | 60 each | Agricultural Mineral Components (`agricultural_mineral_components`) |
| AI Compute Components (`ai_compute_components`) + Power Electronics (`power_electronics`) | 60 each | AI Accelerator (`ai_accelerator`) |
| Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | AI Compute Components (`ai_compute_components`) |
| AI Compute Components (`ai_compute_components`) + Network Components (`network_components`) + Server Components (`server_components`) | 60 each | AI Server (`ai_server`) |
| Bauxite (`bauxite`) | 120 each | Aluminum (`aluminum`) |
| Aluminum (`aluminum`) | 60 each | Aluminum Components (`aluminum_components`) |
| Natural Gas (`natural_gas`) | 120 each | Ammonia (`ammonia`) |
| Food Ingredients (`food_ingredients`) + Nutrition Components (`nutrition_components`) | 60 each | Animal Feed (`animal_feed`) |
| Bitumen (`bitumen`) + Cement (`cement`) | 60 each | Asphalt Components (`asphalt_components`) |
| Aerospace Components (`aerospace_components`) + Autonomous Components (`autonomous_components`) + Avionics Components (`avionics_components`) + Sensor Components (`sensor_components`) | 60 each | Autonomous Aircraft (`autonomous_aircraft`) |
| Autonomous Components (`autonomous_components`) + Marine Components (`marine_components`) + Network Components (`network_components`) + Sensor Components (`sensor_components`) | 60 each | Autonomous Cargo Ship (`autonomous_cargo_ship`) |
| Copper (`copper`) + High-Purity Silicon (`high_purity_silicon`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Autonomous Components (`autonomous_components`) |
| Control Electronics (`control_electronics`) + Magnetic Components (`magnetic_components`) + Power Electronics (`power_electronics`) + Processor Components (`processor_components`) | 60 each | Autonomous Control System (`autonomous_control_system`) |
| Autonomous Components (`autonomous_components`) + Network Components (`network_components`) + Rail Components (`rail_components`) | 60 each | Autonomous Freight Train (`autonomous_freight_train`) |
| Control Electronics (`control_electronics`) + Sensor Components (`sensor_components`) + Vehicle Components (`vehicle_components`) | 60 each | Autonomous Mobile Robot (`autonomous_mobile_robot`) |
| AI Compute Components (`ai_compute_components`) + Autonomous Components (`autonomous_components`) + Sensor Components (`sensor_components`) + Vehicle Components (`vehicle_components`) | 60 each | Autonomous Vehicle (`autonomous_vehicle`) |
| Aluminum (`aluminum`) + Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Avionics Components (`avionics_components`) |
| Food Ingredients (`food_ingredients`) + Packaging Components (`packaging_components`) | 60 each | Bakery Products (`bakery_products`) |
| Copper Wire (`copper_wire`) + Semiconductor Components (`semiconductor_components`) + Silicon Substrate (`silicon_substrate`) | 60 each | Basic Chip (`basic_chip`) |
| Aluminum (`aluminum`) + Cobalt (`cobalt`) + Lithium (`lithium`) + Nickel (`nickel`) | 60 each | Battery Components (`battery_components`) |
| Cobalt (`cobalt`) + Lithium (`lithium`) + Nickel (`nickel`) | 60 each | Battery Materials (`battery_materials`) |
| Chromium (`chromium`) + Steel (`steel`) | 60 each | Bearing Components (`bearing_components`) |
| Bio-Material Components (`bio_material_components`) + Chemical Components (`chemical_components`) | 60 each | Bio-Based Chemicals (`bio_based_chemicals`) |
| Cellulose (`cellulose`) + Industrial Resin (`industrial_resin`) | 60 each | Bio-Composite (`bio_composite`) |
| Natural Gas (`natural_gas`) + Rapeseed (`rapeseed`) | 120 each | Bio-Lubricant (`bio_lubricant`) |
| Bio-Lubricant (`bio_lubricant`) + Cellulose (`cellulose`) | 60 each | Bio-Material Components (`bio_material_components`) |
| Biodiesel Feedstock (`biodiesel_feedstock`) | 60 each | Biodiesel (`biodiesel`) |
| Chemical Feedstock (`chemical_feedstock`) + Vegetable Oil (`vegetable_oil`) | 60 each | Biodiesel Feedstock (`biodiesel_feedstock`) |
| Chemical Components (`chemical_components`) + Ethanol Components (`ethanol_components`) | 60 each | Biofuel (`biofuel`) |
| Bio-Composite (`bio_composite`) + Biopolymer (`biopolymer`) | 60 each | Bioplastic (`bioplastic`) |
| Fermentation Feedstock (`fermentation_feedstock`) + Starch (`starch`) | 60 each | Biopolymer (`biopolymer`) |
| Crude Oil (`crude_oil`) | 120 each | Bitumen (`bitumen`) |
| Chemical Components (`chemical_components`) + Compressor Components (`compressor_components`) + Filtration Components (`filtration_components`) + Pump Components (`pump_components`) | 60 each | Carbon Capture Plant (`carbon_capture_plant`) |
| Crude Oil (`crude_oil`) + Graphite (`graphite`) + Natural Gas (`natural_gas`) | 120 each | Carbon Fiber (`carbon_fiber`) |
| Aerospace Components (`aerospace_components`) + Avionics Components (`avionics_components`) | 60 each | Cargo Aircraft (`cargo_aircraft`) |
| Wooden Components (`wooden_components`) | 60 each | Cargo Pallets (`cargo_pallets`) |
| Marine Components (`marine_components`) + Steel Components (`steel_components`) | 60 each | Cargo Vessel (`cargo_vessel`) |
| Catalyst Metal (`catalyst_metal`) + Palladium (`palladium`) | 60 each | Catalyst Components (`catalyst_components`) |
| Palladium Ore (`palladium_ore`) + Platinum Ore (`platinum_ore`) | 120 each | Catalyst Metal (`catalyst_metal`) |
| Power Electronics (`power_electronics`) + Structural Components (`structural_components`) + Telecom Components (`telecom_components`) | 60 each | Cellular Base Station (`cellular_base_station`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) + Timber (`timber`) | 120 each | Cellulose (`cellulose`) |
| Gypsum (`gypsum`) + Limestone (`limestone`) | 120 each | Cement (`cement`) |
| Ceramics (`ceramics`) | 60 each | Ceramic Components (`ceramic_components`) |
| Clay (`clay`) + Kaolin (`kaolin`) + Magnesite (`magnesite`) | 120 each | Ceramics (`ceramics`) |
| Chemical Feedstock (`chemical_feedstock`) + Sulfuric Acid (`sulfuric_acid`) | 60 each | Chemical Components (`chemical_components`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) | 120 each | Chemical Feedstock (`chemical_feedstock`) |
| Salt (`salt`) | 120 each | Chlorine (`chlorine`) |
| Chromium Ore (`chromium_ore`) | 120 each | Chromium (`chromium`) |
| Technical Textile (`technical_textile`) | 60 each | Clothing (`clothing`) |
| Control Electronics (`control_electronics`) + Precision Components (`precision_components`) + Structural Components (`structural_components`) | 60 each | CNC Machine (`cnc_machine`) |
| Cobalt Ore (`cobalt_ore`) | 120 each | Cobalt (`cobalt`) |
| Turbine Components (`turbine_components`) + Vehicle Components (`vehicle_components`) | 60 each | Combustion Vehicle (`combustion_vehicle`) |
| Aerospace Components (`aerospace_components`) + Avionics Components (`avionics_components`) + Turbine Components (`turbine_components`) | 60 each | Commercial Aircraft (`commercial_aircraft`) |
| Industrial Fabric (`industrial_fabric`) + Wooden Components (`wooden_components`) | 60 each | Commercial Furniture (`commercial_furniture`) |
| Control Electronics (`control_electronics`) + Sensor Components (`sensor_components`) + Tire Components (`tire_components`) + Vehicle Components (`vehicle_components`) | 60 each | Commercial Truck (`commercial_truck`) |
| Insulated Wire (`insulated_wire`) + Telecom Components (`telecom_components`) | 60 each | Communication Cable (`communication_cable`) |
| Aerospace Components (`aerospace_components`) + Network Components (`network_components`) + Solar Components (`solar_components`) + Telecom Components (`telecom_components`) | 60 each | Communication Satellite (`communication_satellite`) |
| Carbon Fiber (`carbon_fiber`) + Industrial Resin (`industrial_resin`) | 60 each | Composite Components (`composite_components`) |
| Aluminum (`aluminum`) + Steel (`steel`) | 60 each | Compressor Components (`compressor_components`) |
| Memory Components (`memory_components`) + Network Components (`network_components`) + Processor Components (`processor_components`) | 60 each | Compute Node (`compute_node`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Silver (`silver`) | 60 each | Computing Components (`computing_components`) |
| Cement (`cement`) + Steel (`steel`) | 60 each | Concrete Components (`concrete_components`) |
| Structural Components (`structural_components`) + Wooden Components (`wooden_components`) | 60 each | Construction Frames (`construction_frames`) |
| Asphalt Components (`asphalt_components`) + Concrete Components (`concrete_components`) + Wooden Components (`wooden_components`) | 60 each | Construction Materials (`construction_materials`) |
| Control Electronics (`control_electronics`) + Marine Components (`marine_components`) + Structural Components (`structural_components`) | 60 each | Container Ship (`container_ship`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Silver (`silver`) | 60 each | Control Electronics (`control_electronics`) |
| Copper Ore (`copper_ore`) | 120 each | Copper (`copper`) |
| Copper (`copper`) | 60 each | Copper Wire (`copper_wire`) |
| Corn (`corn`) | 120 each | Corn Meal (`corn_meal`) |
| Galvanized Metal (`galvanized_metal`) + Stainless Steel (`stainless_steel`) | 60 each | Corrosion Resistant Components (`corrosion_resistant_components`) |
| Cotton (`cotton`) | 120 each | Cotton Fiber (`cotton_fiber`) |
| Memory Components (`memory_components`) + Processor Components (`processor_components`) | 60 each | CPU (`cpu`) |
| Agricultural Chemicals (`agricultural_chemicals`) + Chemical Components (`chemical_components`) | 60 each | Crop Protection Products (`crop_protection_products`) |
| Steel (`steel`) + Tungsten (`tungsten`) | 60 each | Cutting Tooling (`cutting_tooling`) |
| Grid Storage Components (`grid_storage_components`) + Server Components (`server_components`) + Structural Components (`structural_components`) | 60 each | Data Center Module (`data_center_module`) |
| Filtration Components (`filtration_components`) + Membrane Components (`membrane_components`) + Power Electronics (`power_electronics`) + Pump Components (`pump_components`) | 60 each | Desalination Plant (`desalination_plant`) |
| Computing Components (`computing_components`) + Medical Components (`medical_components`) + Sensor Components (`sensor_components`) | 60 each | Diagnostic System (`diagnostic_system`) |
| Rail Components (`rail_components`) + Turbine Components (`turbine_components`) | 60 each | Diesel Locomotive (`diesel_locomotive`) |
| Glass (`glass`) + High-Purity Silicon (`high_purity_silicon`) + Polymer (`polymer`) | 60 each | Display Components (`display_components`) |
| Motor Components (`motor_components`) + Power Electronics (`power_electronics`) + Rail Components (`rail_components`) | 60 each | Electric Locomotive (`electric_locomotive`) |
| Electrical Components (`electrical_components`) + Motor Components (`motor_components`) | 60 each | Electric Motor (`electric_motor`) |
| Battery Components (`battery_components`) + Motor Components (`motor_components`) + Vehicle Components (`vehicle_components`) | 60 each | Electric Vehicle (`electric_vehicle`) |
| Copper Wire (`copper_wire`) + Insulated Wire (`insulated_wire`) | 60 each | Electrical Cable (`electrical_cable`) |
| Copper (`copper`) + Polymer (`polymer`) + Tin (`tin`) | 60 each | Electrical Components (`electrical_components`) |
| Aluminum (`aluminum`) + Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Electrolyzer Components (`electrolyzer_components`) |
| Composite Components (`composite_components`) + Structural Components (`structural_components`) | 60 each | Engineered Structures (`engineered_structures`) |
| Fermentation Feedstock (`fermentation_feedstock`) | 60 each | Ethanol Components (`ethanol_components`) |
| Hydraulic Components (`hydraulic_components`) + Structural Components (`structural_components`) + Vehicle Components (`vehicle_components`) | 60 each | Excavator (`excavator`) |
| Corn (`corn`) + Sugarcane (`sugarcane`) | 120 each | Fermentation Feedstock (`fermentation_feedstock`) |
| Agricultural Mineral Components (`agricultural_mineral_components`) + Fertilizer Components (`fertilizer_components`) | 60 each | Fertilizer (`fertilizer`) |
| Ammonia (`ammonia`) + Phosphoric Acid (`phosphoric_acid`) | 60 each | Fertilizer Components (`fertilizer_components`) |
| Cellulose (`cellulose`) + Industrial Resin (`industrial_resin`) | 60 each | Fiber Components (`fiber_components`) |
| Ceramics (`ceramics`) + Polymer (`polymer`) + Processed Gypsum (`processed_gypsum`) | 60 each | Filtration Components (`filtration_components`) |
| Wheat (`wheat`) | 120 each | Flour (`flour`) |
| Corn Meal (`corn_meal`) + Flour (`flour`) + Refined Sugar (`refined_sugar`) | 60 each | Food Ingredients (`food_ingredients`) |
| Rail Components (`rail_components`) + Structural Components (`structural_components`) | 60 each | Freight Railcar (`freight_railcar`) |
| Fruit (`fruit`) + Sugarcane (`sugarcane`) | 120 each | Fruit Concentrate (`fruit_concentrate`) |
| Electrolyzer Components (`electrolyzer_components`) + Nuclear Fuel Components (`nuclear_fuel_components`) + Reactor Components (`reactor_components`) + Refractory Alloy Components (`refractory_alloy_components`) | 60 each | Fusion Reactor Module (`fusion_reactor_module`) |
| Galvanized Metal (`galvanized_metal`) + Zinc (`zinc`) | 60 each | Galvanized Components (`galvanized_components`) |
| Iron Ore (`iron_ore`) + Zinc Ore (`zinc_ore`) | 120 each | Galvanized Metal (`galvanized_metal`) |
| Hydrogen (`hydrogen`) + Industrial Gas (`industrial_gas`) | 60 each | Gas Handling Components (`gas_handling_components`) |
| Advanced Alloy Components (`advanced_alloy_components`) + Turbine Components (`turbine_components`) | 60 each | Gas Turbine (`gas_turbine`) |
| Manganese (`manganese`) + Steel (`steel`) | 60 each | Gear Components (`gear_components`) |
| Bearing Components (`bearing_components`) + Gear Components (`gear_components`) | 60 each | Gearbox (`gearbox`) |
| Borate Ore (`borate_ore`) + Limestone (`limestone`) + Silica Sand (`silica_sand`) | 120 each | Glass (`glass`) |
| Aluminum (`aluminum`) + Glass (`glass`) | 60 each | Glass Panels (`glass_panels`) |
| Gold Ore (`gold_ore`) | 120 each | Gold (`gold`) |
| Battery Components (`battery_components`) + Battery Materials (`battery_materials`) + Power Electronics (`power_electronics`) | 60 each | Grid Battery (`grid_battery`) |
| Lithium (`lithium`) + Purified Graphite (`purified_graphite`) + Vanadium Alloy (`vanadium_alloy`) | 60 each | Grid Storage Components (`grid_storage_components`) |
| Power Electronics (`power_electronics`) + Storage Components (`storage_components`) | 60 each | Grid Storage System (`grid_storage_system`) |
| Control Electronics (`control_electronics`) + Hydraulic Components (`hydraulic_components`) + Structural Components (`structural_components`) | 60 each | Heavy Machinery (`heavy_machinery`) |
| Control Electronics (`control_electronics`) + Hydraulic Components (`hydraulic_components`) + Mining Components (`mining_components`) | 60 each | Heavy Mining Drill (`heavy_mining_drill`) |
| Crude Oil (`crude_oil`) + Fluorspar (`fluorspar`) + Natural Gas (`natural_gas`) + Quartz (`quartz`) | 120 each | High-Purity Silicon (`high_purity_silicon`) |
| Control Electronics (`control_electronics`) + Network Components (`network_components`) | 60 each | High-Speed Network System (`high_speed_network_system`) |
| Aerospace Components (`aerospace_components`) + Power Electronics (`power_electronics`) + Rail Components (`rail_components`) | 60 each | High-Speed Train (`high_speed_train`) |
| Composite Components (`composite_components`) + Marine Components (`marine_components`) + Turbine Components (`turbine_components`) | 60 each | High-Speed Vessel (`high_speed_vessel`) |
| Insulation Material (`insulation_material`) + Power Electronics (`power_electronics`) + Transformer Components (`transformer_components`) | 60 each | High-Voltage Equipment (`high_voltage_equipment`) |
| Industrial Resin (`industrial_resin`) + Steel (`steel`) | 60 each | Hydraulic Components (`hydraulic_components`) |
| Hydraulic Components (`hydraulic_components`) + Steel Components (`steel_components`) | 60 each | Hydraulic System (`hydraulic_system`) |
| Natural Gas (`natural_gas`) | 120 each | Hydrogen (`hydrogen`) |
| Electrolyzer Components (`electrolyzer_components`) + Power Electronics (`power_electronics`) | 60 each | Hydrogen Electrolyzer (`hydrogen_electrolyzer`) |
| Chemical Components (`chemical_components`) + Gas Handling Components (`gas_handling_components`) | 60 each | Industrial Chemicals (`industrial_chemicals`) |
| Industrial Fabric (`industrial_fabric`) + Technical Textile (`technical_textile`) | 60 each | Industrial Clothing (`industrial_clothing`) |
| Compressor Components (`compressor_components`) + Motor Components (`motor_components`) | 60 each | Industrial Compressor (`industrial_compressor`) |
| Computing Components (`computing_components`) + Display Components (`display_components`) | 60 each | Industrial Computer (`industrial_computer`) |
| Control Electronics (`control_electronics`) + Sensor Components (`sensor_components`) | 60 each | Industrial Controller (`industrial_controller`) |
| Gear Components (`gear_components`) + Mining Components (`mining_components`) | 60 each | Industrial Crusher (`industrial_crusher`) |
| Control Electronics (`control_electronics`) + Cutting Tooling (`cutting_tooling`) + Precision Components (`precision_components`) | 60 each | Industrial Cutting Machine (`industrial_cutting_machine`) |
| Control Electronics (`control_electronics`) + Glass Panels (`glass_panels`) | 60 each | Industrial Display (`industrial_display`) |
| Aerospace Components (`aerospace_components`) + Battery Components (`battery_components`) + Sensor Components (`sensor_components`) | 60 each | Industrial Drone (`industrial_drone`) |
| Electrical Components (`electrical_components`) + Iron Components (`iron_components`) + Steel Components (`steel_components`) | 60 each | Industrial Equipment (`industrial_equipment`) |
| Cotton Fiber (`cotton_fiber`) + Polymer (`polymer`) + Processed Rubber (`processed_rubber`) | 60 each | Industrial Fabric (`industrial_fabric`) |
| Natural Gas (`natural_gas`) | 120 each | Industrial Gas (`industrial_gas`) |
| Motor Components (`motor_components`) + Turbine Components (`turbine_components`) | 60 each | Industrial Generator (`industrial_generator`) |
| Aluminum Components (`aluminum_components`) + Glass Panels (`glass_panels`) | 60 each | Industrial Glass Panels (`industrial_glass_panels`) |
| Galvanized Components (`galvanized_components`) + Glass Panels (`glass_panels`) + Insulation Material (`insulation_material`) + Structural Components (`structural_components`) | 60 each | Industrial Hall Modules (`industrial_hall_modules`) |
| Fiber Components (`fiber_components`) + Insulation Material (`insulation_material`) | 60 each | Industrial Insulation (`industrial_insulation`) |
| Control Electronics (`control_electronics`) + Power Electronics (`power_electronics`) | 60 each | Industrial Inverter (`industrial_inverter`) |
| Magnetic Components (`magnetic_components`) + Precision Components (`precision_components`) + Semiconductor Components (`semiconductor_components`) | 60 each | Industrial Laser (`industrial_laser`) |
| Packaging Components (`packaging_components`) + Wooden Components (`wooden_components`) | 60 each | Industrial Packaging (`industrial_packaging`) |
| Composite Components (`composite_components`) + Packaging Components (`packaging_components`) | 60 each | Industrial Plastics (`industrial_plastics`) |
| Motor Components (`motor_components`) + Pump Components (`pump_components`) | 60 each | Industrial Pump (`industrial_pump`) |
| Control Electronics (`control_electronics`) + Electrical Components (`electrical_components`) | 60 each | Industrial Relay (`industrial_relay`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) | 120 each | Industrial Resin (`industrial_resin`) |
| Control Electronics (`control_electronics`) + Motor Components (`motor_components`) + Precision Components (`precision_components`) + Sensor Components (`sensor_components`) | 60 each | Industrial Robot (`industrial_robot`) |
| Chemical Components (`chemical_components`) + Rubber Blend Components (`rubber_blend_components`) + Tire Components (`tire_components`) | 60 each | Industrial Rubber Products (`industrial_rubber_products`) |
| Precision Components (`precision_components`) + Tire Components (`tire_components`) | 60 each | Industrial Seals (`industrial_seals`) |
| Control Electronics (`control_electronics`) + Sensor Components (`sensor_components`) | 60 each | Industrial Sensor (`industrial_sensor`) |
| Tire Components (`tire_components`) | 60 each | Industrial Tires (`industrial_tires`) |
| Copper (`copper`) + Polymer (`polymer`) | 60 each | Insulated Wire (`insulated_wire`) |
| Polymer (`polymer`) + Processed Gypsum (`processed_gypsum`) | 60 each | Insulation Material (`insulation_material`) |
| Iron Ore (`iron_ore`) | 120 each | Iron (`iron`) |
| Iron (`iron`) | 60 each | Iron Components (`iron_components`) |
| Turbine Components (`turbine_components`) | 60 each | Jet Engine (`jet_engine`) |
| Control Electronics (`control_electronics`) + Glass Panels (`glass_panels`) + Precision Components (`precision_components`) | 60 each | Laboratory Equipment (`laboratory_equipment`) |
| Aerospace Components (`aerospace_components`) + Control Electronics (`control_electronics`) + Turbine Components (`turbine_components`) | 60 each | Launch Vehicle (`launch_vehicle`) |
| Lead Ore (`lead_ore`) | 120 each | Lead (`lead`) |
| Aerospace Components (`aerospace_components`) + Avionics Components (`avionics_components`) | 60 each | Light Aircraft (`light_aircraft`) |
| Lithium Ore (`lithium_ore`) | 120 each | Lithium (`lithium`) |
| Timber (`timber`) | 120 each | Lumber (`lumber`) |
| Computing Components (`computing_components`) + Sensor Components (`sensor_components`) | 60 each | Machine Vision System (`machine_vision_system`) |
| Iron (`iron`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Magnetic Components (`magnetic_components`) |
| Manganese Ore (`manganese_ore`) | 120 each | Manganese (`manganese`) |
| Industrial Resin (`industrial_resin`) + Steel (`steel`) | 60 each | Marine Components (`marine_components`) |
| Glass (`glass`) + Platinum (`platinum`) + Stainless Steel (`stainless_steel`) | 60 each | Medical Components (`medical_components`) |
| Display Components (`display_components`) + Medical Components (`medical_components`) + Sensor Components (`sensor_components`) | 60 each | Medical Monitor (`medical_monitor`) |
| Cellulose (`cellulose`) + Chlorine (`chlorine`) + Polymer (`polymer`) | 60 each | Membrane Components (`membrane_components`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Silver (`silver`) | 60 each | Memory Components (`memory_components`) |
| Control Electronics (`control_electronics`) + Memory Components (`memory_components`) | 60 each | Memory Module (`memory_module`) |
| Semiconductor Components (`semiconductor_components`) + Semiconductor Die (`semiconductor_die`) | 60 each | Microchip (`microchip`) |
| Control Electronics (`control_electronics`) + Semiconductor Die (`semiconductor_die`) | 60 each | Microcontroller (`microcontroller`) |
| Steel (`steel`) + Tungsten (`tungsten`) | 60 each | Mining Components (`mining_components`) |
| Mining Components (`mining_components`) + Motor Components (`motor_components`) + Steel Components (`steel_components`) | 60 each | Mining Drill (`mining_drill`) |
| Mining Components (`mining_components`) + Steel Components (`steel_components`) | 60 each | Mining Equipment (`mining_equipment`) |
| Molybdenum Ore (`molybdenum_ore`) | 120 each | Molybdenum (`molybdenum`) |
| Copper (`copper`) + Iron (`iron`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Motor Components (`motor_components`) |
| Aerospace Components (`aerospace_components`) + Sensor Components (`sensor_components`) + Telecom Components (`telecom_components`) | 60 each | Navigation Satellite (`navigation_satellite`) |
| Aluminum (`aluminum`) + Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Network Components (`network_components`) |
| Control Electronics (`control_electronics`) + Network Components (`network_components`) | 60 each | Network Switch (`network_switch`) |
| Nickel Ore (`nickel_ore`) | 120 each | Nickel (`nickel`) |
| Coal (`coal`) + Iron Ore (`iron_ore`) + Molybdenum Ore (`molybdenum_ore`) + Nickel Ore (`nickel_ore`) | 120 each | Nickel Alloy (`nickel_alloy`) |
| Niobium Ore (`niobium_ore`) | 120 each | Niobium (`niobium`) |
| Nuclear Fuel Components (`nuclear_fuel_components`) + Shielding Components (`shielding_components`) | 60 each | Nuclear Fuel Assembly (`nuclear_fuel_assembly`) |
| Nuclear Material (`nuclear_material`) + Shielding Material (`shielding_material`) | 60 each | Nuclear Fuel Components (`nuclear_fuel_components`) |
| Lead Ore (`lead_ore`) + Uranium Ore (`uranium_ore`) | 120 each | Nuclear Material (`nuclear_material`) |
| Control Electronics (`control_electronics`) + Nuclear Fuel Components (`nuclear_fuel_components`) + Reactor Components (`reactor_components`) + Structural Components (`structural_components`) | 60 each | Nuclear Reactor (`nuclear_reactor`) |
| Fruit Concentrate (`fruit_concentrate`) + Soy Protein (`soy_protein`) + Vegetable Oil (`vegetable_oil`) | 60 each | Nutrition Components (`nutrition_components`) |
| Aerospace Components (`aerospace_components`) + Avionics Components (`avionics_components`) + Control Electronics (`control_electronics`) | 60 each | Orbital Vehicle (`orbital_vehicle`) |
| Fruit (`fruit`) + Potatoes (`potatoes`) + Wheat (`wheat`) | 120 each | Organic Feedstock (`organic_feedstock`) |
| Nutrition Components (`nutrition_components`) + Packaging Components (`packaging_components`) | 60 each | Packaged Beverages (`packaged_beverages`) |
| Food Ingredients (`food_ingredients`) + Packaging Components (`packaging_components`) + Sweetener Components (`sweetener_components`) | 60 each | Packaged Food (`packaged_food`) |
| Food Ingredients (`food_ingredients`) + Nutrition Components (`nutrition_components`) + Packaging Components (`packaging_components`) | 60 each | Packaged Meals (`packaged_meals`) |
| Nutrition Components (`nutrition_components`) + Packaging Components (`packaging_components`) | 60 each | Packaged Nutrition (`packaged_nutrition`) |
| Polymer (`polymer`) + Wood Pulp (`wood_pulp`) | 60 each | Packaging Components (`packaging_components`) |
| Packaging Components (`packaging_components`) | 60 each | Packaging Materials (`packaging_materials`) |
| Palladium Ore (`palladium_ore`) | 120 each | Palladium (`palladium`) |
| Natural Gas (`natural_gas`) + Phosphate Rock (`phosphate_rock`) + Sulfur (`sulfur`) | 120 each | Phosphoric Acid (`phosphoric_acid`) |
| Platinum Ore (`platinum_ore`) | 120 each | Platinum (`platinum`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) | 120 each | Polymer (`polymer`) |
| Potash (`potash`) | 120 each | Potassium Compound (`potassium_compound`) |
| Aluminum Components (`aluminum_components`) + Insulated Wire (`insulated_wire`) | 60 each | Power Cable (`power_cable`) |
| Aluminum (`aluminum`) + Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Power Electronics (`power_electronics`) |
| Aluminum (`aluminum`) + Steel (`steel`) + Tungsten (`tungsten`) | 60 each | Precision Components (`precision_components`) |
| Magnetic Components (`magnetic_components`) + Motor Components (`motor_components`) + Precision Components (`precision_components`) | 60 each | Precision Motor (`precision_motor`) |
| Concrete Components (`concrete_components`) + Structural Components (`structural_components`) + Wooden Components (`wooden_components`) | 60 each | Prefabricated Structures (`prefabricated_structures`) |
| Advanced Cell Components (`advanced_cell_components`) + Display Components (`display_components`) + Vehicle Components (`vehicle_components`) | 60 each | Premium Electric Vehicle (`premium_electric_vehicle`) |
| Food Ingredients (`food_ingredients`) + Nutrition Components (`nutrition_components`) | 60 each | Processed Food (`processed_food`) |
| Gypsum (`gypsum`) | 120 each | Processed Gypsum (`processed_gypsum`) |
| Natural Rubber (`natural_rubber`) + Sulfur (`sulfur`) | 120 each | Processed Rubber (`processed_rubber`) |
| Control Electronics (`control_electronics`) + Pump Components (`pump_components`) + Steel Components (`steel_components`) | 60 each | Processing Equipment (`processing_equipment`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Processor Components (`processor_components`) |
| Industrial Fabric (`industrial_fabric`) + Tire Components (`tire_components`) | 60 each | Protective Clothing (`protective_clothing`) |
| Insulation Material (`insulation_material`) + Packaging Components (`packaging_components`) | 60 each | Protective Packaging (`protective_packaging`) |
| Copper (`copper`) + Steel (`steel`) | 60 each | Pump Components (`pump_components`) |
| Graphite (`graphite`) | 120 each | Purified Graphite (`purified_graphite`) |
| Control Electronics (`control_electronics`) + Processor Components (`processor_components`) + Refractory Alloy Components (`refractory_alloy_components`) | 60 each | Quantum Computing Module (`quantum_computing_module`) |
| Magnetic Components (`magnetic_components`) + Telecom Components (`telecom_components`) | 60 each | Radio Transceiver (`radio_transceiver`) |
| Manganese (`manganese`) + Steel (`steel`) | 60 each | Rail Components (`rail_components`) |
| Rail Components (`rail_components`) + Steel Components (`steel_components`) | 60 each | Railway Track (`railway_track`) |
| Rare Earth Ore (`rare_earth_ore`) | 120 each | Rare Earth Metals (`rare_earth_metals`) |
| Sugarcane (`sugarcane`) | 120 each | Raw Sugar (`raw_sugar`) |
| Nuclear Material (`nuclear_material`) | 60 each | Reactor Components (`reactor_components`) |
| Sugarcane (`sugarcane`) | 120 each | Refined Sugar (`refined_sugar`) |
| Molybdenum (`molybdenum`) + Niobium (`niobium`) + Superconducting Alloy (`superconducting_alloy`) | 60 each | Refractory Alloy Components (`refractory_alloy_components`) |
| Concrete Components (`concrete_components`) + Steel Components (`steel_components`) | 60 each | Reinforced Concrete (`reinforced_concrete`) |
| Motor Components (`motor_components`) + Precision Components (`precision_components`) | 60 each | Robotic Actuator (`robotic_actuator`) |
| Control Electronics (`control_electronics`) + Motor Components (`motor_components`) + Precision Components (`precision_components`) | 60 each | Robotic Arm (`robotic_arm`) |
| Titanium Components (`titanium_components`) + Turbine Components (`turbine_components`) | 60 each | Rocket Engine (`rocket_engine`) |
| Network Components (`network_components`) + Telecom Components (`telecom_components`) | 60 each | Router (`router`) |
| Processed Rubber (`processed_rubber`) + Synthetic Rubber (`synthetic_rubber`) | 60 each | Rubber Blend Components (`rubber_blend_components`) |
| Glass Panels (`glass_panels`) + Industrial Fabric (`industrial_fabric`) + Tire Components (`tire_components`) | 60 each | Safety Equipment (`safety_equipment`) |
| Aerospace Components (`aerospace_components`) + Solar Components (`solar_components`) + Telecom Components (`telecom_components`) | 60 each | Satellite (`satellite`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Semiconductor Components (`semiconductor_components`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Silver (`silver`) | 60 each | Semiconductor Die (`semiconductor_die`) |
| Ceramic Components (`ceramic_components`) + Control Electronics (`control_electronics`) + Precision Components (`precision_components`) | 60 each | Semiconductor Equipment (`semiconductor_equipment`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Sensor Components (`sensor_components`) |
| Computing Components (`computing_components`) + Memory Components (`memory_components`) | 60 each | Server (`server`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Server Components (`server_components`) |
| Network Components (`network_components`) + Server Components (`server_components`) + Structural Components (`structural_components`) | 60 each | Server Rack (`server_rack`) |
| Control Electronics (`control_electronics`) + Motor Components (`motor_components`) + Precision Components (`precision_components`) | 60 each | Servo Motor (`servo_motor`) |
| Lead (`lead`) + Shielding Material (`shielding_material`) | 60 each | Shielding Components (`shielding_components`) |
| Borate Ore (`borate_ore`) + Lead Ore (`lead_ore`) | 120 each | Shielding Material (`shielding_material`) |
| Coal (`coal`) + Quartz (`quartz`) | 120 each | Silicon (`silicon`) |
| Glass (`glass`) + Silicon (`silicon`) | 60 each | Silicon Substrate (`silicon_substrate`) |
| Silver Ore (`silver_ore`) | 120 each | Silver (`silver`) |
| Nutrition Components (`nutrition_components`) + Packaging Components (`packaging_components`) | 60 each | Soft Drinks (`soft_drinks`) |
| Power Electronics (`power_electronics`) + Solar Components (`solar_components`) | 60 each | Solar Array (`solar_array`) |
| Aluminum (`aluminum`) + Glass (`glass`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Solar Components (`solar_components`) |
| Soybeans (`soybeans`) | 120 each | Soy Oil (`soy_oil`) |
| Soybeans (`soybeans`) | 120 each | Soy Protein (`soy_protein`) |
| Stainless Steel (`stainless_steel`) | 60 each | Stainless Components (`stainless_components`) |
| Chromium Ore (`chromium_ore`) + Coal (`coal`) + Iron Ore (`iron_ore`) + Nickel Ore (`nickel_ore`) | 120 each | Stainless Steel (`stainless_steel`) |
| Corn (`corn`) + Potatoes (`potatoes`) | 120 each | Starch (`starch`) |
| Stainless Components (`stainless_components`) + Turbine Components (`turbine_components`) | 60 each | Steam Turbine (`steam_turbine`) |
| Coal (`coal`) + Iron Ore (`iron_ore`) | 120 each | Steel (`steel`) |
| Steel (`steel`) | 60 each | Steel Components (`steel_components`) |
| Aluminum (`aluminum`) + Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) | 60 each | Storage Components (`storage_components`) |
| Cement (`cement`) + Steel (`steel`) | 60 each | Structural Components (`structural_components`) |
| Concrete Components (`concrete_components`) + Structural Components (`structural_components`) | 60 each | Structural Systems (`structural_systems`) |
| Natural Gas (`natural_gas`) + Sulfur (`sulfur`) | 120 each | Sulfuric Acid (`sulfuric_acid`) |
| AI Compute Components (`ai_compute_components`) + Grid Storage Components (`grid_storage_components`) + Network Components (`network_components`) + Server Components (`server_components`) | 60 each | Supercomputer (`supercomputer`) |
| Niobium Ore (`niobium_ore`) + Rare Earth Ore (`rare_earth_ore`) + Titanium Ore (`titanium_ore`) | 120 each | Superconducting Alloy (`superconducting_alloy`) |
| Power Electronics (`power_electronics`) + Refractory Alloy Components (`refractory_alloy_components`) | 60 each | Superconducting Magnet System (`superconducting_magnet_system`) |
| Precision Components (`precision_components`) + Stainless Components (`stainless_components`) | 60 each | Surgical Equipment (`surgical_equipment`) |
| Bio-Composite (`bio_composite`) + Packaging Components (`packaging_components`) | 60 each | Sustainable Packaging (`sustainable_packaging`) |
| Organic Feedstock (`organic_feedstock`) + Raw Sugar (`raw_sugar`) + Soy Oil (`soy_oil`) | 60 each | Sweetener Components (`sweetener_components`) |
| Control Electronics (`control_electronics`) + Electrical Components (`electrical_components`) | 60 each | Switchgear (`switchgear`) |
| Catalyst Components (`catalyst_components`) + Chemical Components (`chemical_components`) + Electrolyzer Components (`electrolyzer_components`) | 60 each | Synthetic Fuel Plant (`synthetic_fuel_plant`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) + Sulfur (`sulfur`) | 120 each | Synthetic Rubber (`synthetic_rubber`) |
| Corrosion Resistant Components (`corrosion_resistant_components`) + Marine Components (`marine_components`) + Pump Components (`pump_components`) | 60 each | Tanker (`tanker`) |
| Cotton Fiber (`cotton_fiber`) + Polymer (`polymer`) | 60 each | Technical Textile (`technical_textile`) |
| Copper (`copper`) + Gold (`gold`) + High-Purity Silicon (`high_purity_silicon`) + Rare Earth Metals (`rare_earth_metals`) | 60 each | Telecom Components (`telecom_components`) |
| Tin Ore (`tin_ore`) | 120 each | Tin (`tin`) |
| Carbon Fiber (`carbon_fiber`) + Processed Rubber (`processed_rubber`) | 60 each | Tire Components (`tire_components`) |
| Titanium Ore (`titanium_ore`) | 120 each | Titanium (`titanium`) |
| Titanium (`titanium`) | 60 each | Titanium Components (`titanium_components`) |
| Electrical Components (`electrical_components`) + Transformer Components (`transformer_components`) | 60 each | Transformer (`transformer`) |
| Copper (`copper`) + Steel (`steel`) | 60 each | Transformer Components (`transformer_components`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) + Timber (`timber`) | 120 each | Treated Lumber (`treated_lumber`) |
| Tungsten Ore (`tungsten_ore`) | 120 each | Tungsten (`tungsten`) |
| Nickel Alloy (`nickel_alloy`) + Titanium (`titanium`) | 60 each | Turbine Components (`turbine_components`) |
| Control Electronics (`control_electronics`) + Sensor Components (`sensor_components`) + Vehicle Components (`vehicle_components`) | 60 each | Utility Vehicle (`utility_vehicle`) |
| Vanadium Ore (`vanadium_ore`) | 120 each | Vanadium (`vanadium`) |
| Iron Ore (`iron_ore`) + Vanadium Ore (`vanadium_ore`) | 120 each | Vanadium Alloy (`vanadium_alloy`) |
| Rapeseed (`rapeseed`) + Soybeans (`soybeans`) | 120 each | Vegetable Oil (`vegetable_oil`) |
| Aluminum (`aluminum`) + Processed Rubber (`processed_rubber`) + Steel (`steel`) | 60 each | Vehicle Components (`vehicle_components`) |
| Carbon Fiber (`carbon_fiber`) + Industrial Resin (`industrial_resin`) + Nickel Alloy (`nickel_alloy`) + Titanium (`titanium`) | 60 each | Wind Components (`wind_components`) |
| Power Electronics (`power_electronics`) + Structural Components (`structural_components`) + Wind Components (`wind_components`) | 60 each | Wind Turbine (`wind_turbine`) |
| Crude Oil (`crude_oil`) + Natural Gas (`natural_gas`) + Timber (`timber`) | 120 each | Wood Pulp (`wood_pulp`) |
| Lumber (`lumber`) + Treated Lumber (`treated_lumber`) | 60 each | Wooden Components (`wooden_components`) |
| Marine Components (`marine_components`) + Turbine Components (`turbine_components`) | 60 each | Workboat (`workboat`) |
| Industrial Fabric (`industrial_fabric`) + Technical Textile (`technical_textile`) | 60 each | Workwear (`workwear`) |
| Zinc Ore (`zinc_ore`) | 120 each | Zinc (`zinc`) |

The counter is `lifetime_produced`: positive output accepted into storage by simulation. It is lifetime/save-persistent, not current inventory or per session. Unaccepted overflow does not count.

## 6. Level-gate table

Every node has a minimum level. Exact IDs are grouped by level and split between direct inputless unlocks and nodes that also require quantity parents.

| Level | Direct inputless roots | Nodes also requiring all quantity parents | Total |
|---:|---|---|---:|
| 1 | `bauxite`, `coal`, `copper_ore`, `crude_oil`, `iron_ore`, `limestone`, `quartz`, `timber`, `wheat` | `aluminum`, `aluminum_components`, `bitumen`, `compressor_components`, `copper`, `copper_wire`, `flour`, `iron`, `iron_components`, `lumber`, `pump_components`, `silicon`, `steel`, `steel_components`, `transformer_components` | 24 |
| 2 | `corn`, `potatoes`, `soybeans` | `corn_meal`, `soy_oil`, `soy_protein`, `starch` | 7 |
| 3 | `clay`, `gypsum`, `kaolin`, `silica_sand` | `asphalt_components`, `cement`, `concrete_components`, `processed_gypsum`, `reinforced_concrete`, `structural_components`, `structural_systems` | 11 |
| 4 | `cotton`, `fruit`, `rapeseed`, `sugarcane` | `animal_feed`, `biopolymer`, `cotton_fiber`, `ethanol_components`, `fermentation_feedstock`, `food_ingredients`, `fruit_concentrate`, `nutrition_components`, `organic_feedstock`, `processed_food`, `raw_sugar`, `refined_sugar`, `sweetener_components`, `vegetable_oil` | 18 |
| 5 | `natural_gas`, `natural_rubber` | `ammonia`, `bakery_products`, `bio_composite`, `bio_lubricant`, `bio_material_components`, `biodiesel`, `biodiesel_feedstock`, `bioplastic`, `cargo_pallets`, `cargo_vessel`, `cellulose`, `chemical_feedstock`, `clothing`, `construction_frames`, `construction_materials`, `electrical_cable`, `fiber_components`, `gas_handling_components`, `hydraulic_components`, `hydraulic_system`, `hydrogen`, `industrial_gas`, `industrial_insulation`, `industrial_packaging`, `industrial_resin`, `insulated_wire`, `insulation_material`, `marine_components`, `packaged_beverages`, `packaged_food`, `packaged_meals`, `packaged_nutrition`, `packaging_components`, `packaging_materials`, `polymer`, `power_cable`, `prefabricated_structures`, `protective_packaging`, `soft_drinks`, `sustainable_packaging`, `technical_textile`, `treated_lumber`, `wood_pulp`, `wooden_components` | 46 |
| 7 | `phosphate_rock`, `potash`, `salt`, `sulfur` | `advanced_fertilizer`, `agricultural_chemicals`, `agricultural_mineral_components`, `bio_based_chemicals`, `biofuel`, `chemical_components`, `chlorine`, `commercial_furniture`, `crop_protection_products`, `excavator`, `fertilizer`, `fertilizer_components`, `industrial_chemicals`, `industrial_clothing`, `industrial_fabric`, `membrane_components`, `phosphoric_acid`, `potassium_compound`, `processed_rubber`, `rubber_blend_components`, `sulfuric_acid`, `synthetic_rubber`, `vehicle_components`, `workwear` | 28 |
| 9 | `lead_ore`, `manganese_ore`, `tin_ore`, `zinc_ore` | `electrical_components`, `freight_railcar`, `galvanized_components`, `galvanized_metal`, `gear_components`, `industrial_equipment`, `lead`, `manganese`, `rail_components`, `railway_track`, `tin`, `transformer`, `zinc` | 17 |
| 11 | `chromium_ore`, `nickel_ore` | `bearing_components`, `chromium`, `corrosion_resistant_components`, `gearbox`, `nickel`, `stainless_components`, `stainless_steel`, `tanker` | 10 |
| 13 | `borate_ore`, `fluorspar`, `graphite`, `magnesite` | `carbon_capture_plant`, `carbon_fiber`, `ceramic_components`, `ceramics`, `composite_components`, `display_components`, `engineered_structures`, `filtration_components`, `glass`, `glass_panels`, `high_purity_silicon`, `industrial_glass_panels`, `industrial_hall_modules`, `industrial_plastics`, `industrial_rubber_products`, `industrial_tires`, `protective_clothing`, `purified_graphite`, `safety_equipment`, `shielding_components`, `shielding_material`, `silicon_substrate`, `solar_components`, `tire_components` | 28 |
| 15 | `cobalt_ore`, `lithium_ore`, `rare_earth_ore` | `advanced_cell_components`, `autonomous_components`, `battery_components`, `battery_materials`, `cobalt`, `electric_motor`, `electric_vehicle`, `industrial_compressor`, `industrial_pump`, `lithium`, `magnetic_components`, `motor_components`, `premium_electric_vehicle`, `rare_earth_metals` | 17 |
| 18 | `gold_ore`, `silver_ore` | `advanced_furnace`, `advanced_industrial_robot`, `advanced_protective_equipment`, `ai_accelerator`, `ai_compute_components`, `ai_server`, `autonomous_cargo_ship`, `autonomous_control_system`, `autonomous_freight_train`, `autonomous_mobile_robot`, `autonomous_vehicle`, `avionics_components`, `basic_chip`, `cellular_base_station`, `commercial_truck`, `communication_cable`, `compute_node`, `computing_components`, `container_ship`, `control_electronics`, `cpu`, `desalination_plant`, `electric_locomotive`, `electrolyzer_components`, `gold`, `grid_battery`, `grid_storage_system`, `heavy_machinery`, `high_speed_network_system`, `high_voltage_equipment`, `hydrogen_electrolyzer`, `industrial_computer`, `industrial_controller`, `industrial_display`, `industrial_inverter`, `industrial_relay`, `industrial_sensor`, `machine_vision_system`, `memory_components`, `memory_module`, `microchip`, `microcontroller`, `network_components`, `network_switch`, `power_electronics`, `processing_equipment`, `processor_components`, `radio_transceiver`, `router`, `semiconductor_components`, `semiconductor_die`, `sensor_components`, `server`, `server_components`, `server_rack`, `silver`, `solar_array`, `storage_components`, `switchgear`, `telecom_components`, `utility_vehicle` | 63 |
| 20 | `palladium_ore`, `platinum_ore` | `catalyst_components`, `catalyst_metal`, `diagnostic_system`, `medical_components`, `medical_monitor`, `palladium`, `platinum`, `synthetic_fuel_plant` | 10 |
| 22 | `molybdenum_ore`, `niobium_ore`, `titanium_ore`, `tungsten_ore`, `vanadium_ore` | `advanced_aircraft`, `advanced_alloy_components`, `advanced_medical_equipment`, `advanced_semiconductor_equipment`, `aerospace_components`, `autonomous_aircraft`, `cargo_aircraft`, `cnc_machine`, `combustion_vehicle`, `commercial_aircraft`, `communication_satellite`, `cutting_tooling`, `data_center_module`, `diesel_locomotive`, `gas_turbine`, `grid_storage_components`, `heavy_mining_drill`, `high_speed_train`, `high_speed_vessel`, `industrial_crusher`, `industrial_cutting_machine`, `industrial_drone`, `industrial_generator`, `industrial_laser`, `industrial_robot`, `industrial_seals`, `jet_engine`, `laboratory_equipment`, `launch_vehicle`, `light_aircraft`, `mining_components`, `mining_drill`, `mining_equipment`, `molybdenum`, `navigation_satellite`, `nickel_alloy`, `niobium`, `orbital_vehicle`, `precision_components`, `precision_motor`, `quantum_computing_module`, `refractory_alloy_components`, `robotic_actuator`, `robotic_arm`, `rocket_engine`, `satellite`, `semiconductor_equipment`, `servo_motor`, `steam_turbine`, `supercomputer`, `superconducting_alloy`, `superconducting_magnet_system`, `surgical_equipment`, `titanium`, `titanium_components`, `tungsten`, `turbine_components`, `vanadium`, `vanadium_alloy`, `wind_components`, `wind_turbine`, `workboat` | 67 |
| 25 | `uranium_ore` | `fusion_reactor_module`, `nuclear_fuel_assembly`, `nuclear_fuel_components`, `nuclear_material`, `nuclear_reactor`, `reactor_components` | 7 |

For an inputless root, reaching level directly satisfies its only gate and the next reevaluation unlocks it. For a non-root, level merely permits parent/quantity checks; it does not bypass them.

## 7. First-production semantics

`first_produced_resource_ids` is set when `record_accepted_production_xp` sees any positive accepted output for a resource for the first time. It is not a separately modeled full cycle: any positive accepted amount in the simulation batch triggers it. It awards one-time company XP from progression metadata stage: Extractor 25, Processor 40, Fabricator 60, Assembler 100.

First production does not directly unlock a node, does not transition the unlock graph, and must not be an edge. Its XP can indirectly cause a company level increase; `_award` then reevaluates ordinary gates. `FIRST PRODUCTION COMPLETE` / compact `FIRST COMPLETE` are informational only.

## 8. Mastery semantics

Family mastery covers 18 primary-production families. A family completes only when every listed root has at least 120 lifetime accepted units. `family_mastery_progress` sums each member capped at 120, so aggregate target is `120 × family size`; completion still requires every member individually. It awards 250 company XP once. It is not a direct unlock condition.

| Family | Level | Required roots (each 120) | Aggregate target |
|---|---:|---|---:|
| Base Metals & Carbon (`base_metals_carbon`) | 1 | `iron_ore`, `copper_ore`, `coal`, `bauxite` | 480 |
| Construction Minerals (`construction_minerals`) | 1 | `limestone`, `quartz` | 240 |
| Forestry (`forestry`) | 1 | `timber` | 120 |
| Staple Agriculture (`staple_agriculture`) | 1 | `wheat` | 120 |
| Petroleum (`petroleum`) | 1 | `crude_oil` | 120 |
| Field Crops (`field_crops`) | 2 | `corn`, `soybeans`, `potatoes` | 360 |
| Process Minerals (`process_minerals`) | 3 | `clay`, `gypsum`, `silica_sand`, `kaolin` | 480 |
| Food & Fiber Crops (`food_fiber_crops`) | 4 | `sugarcane`, `cotton`, `rapeseed`, `fruit` | 480 |
| Gas & Elastomers (`gas_elastomers`) | 5 | `natural_gas`, `natural_rubber` | 240 |
| Chemical Minerals (`chemical_minerals`) | 7 | `salt`, `sulfur`, `phosphate_rock`, `potash` | 480 |
| Common Alloy Metals (`common_alloy_metals`) | 9 | `zinc_ore`, `lead_ore`, `tin_ore`, `manganese_ore` | 480 |
| Advanced Alloy Metals (`advanced_alloy_metals`) | 11 | `chromium_ore`, `nickel_ore` | 240 |
| Carbon & Specialty Minerals (`carbon_specialty_minerals`) | 13 | `graphite`, `fluorspar`, `magnesite`, `borate_ore` | 480 |
| Battery & Electronics Feedstocks (`battery_electronics_feedstocks`) | 15 | `lithium_ore`, `cobalt_ore`, `rare_earth_ore` | 360 |
| Precious Metals (`precious_metals`) | 18 | `gold_ore`, `silver_ore` | 240 |
| Catalyst Precious Metals (`catalyst_precious_metals`) | 20 | `platinum_ore`, `palladium_ore` | 240 |
| Aerospace & Refractory Metals (`aerospace_refractory_metals`) | 22 | `titanium_ore`, `tungsten_ore`, `molybdenum_ore`, `vanadium_ore`, `niobium_ore` | 600 |
| Nuclear Materials (`nuclear_materials`) | 25 | `uranium_ore` | 120 |

Tree recommendation: never label an edge `MASTERY`. Show the actual source and counter (`COPPER ORE 72 / 120`). If mastery appears elsewhere, present it as a family XP achievement, not an unlock prerequisite.

## 9. Multiple-parent and branching behavior

- 252 nodes have multiple sources; maximum four.
- Every non-root combines level plus one or more quantity requirements using AND; there are no OR gates.
- One source can unlock many children. Largest fan-out: `control_electronics` → 32: `advanced_furnace`, `advanced_medical_equipment`, `advanced_semiconductor_equipment`, `autonomous_control_system`, `autonomous_mobile_robot`, `cnc_machine`, `commercial_truck`, `container_ship`, `heavy_machinery`, `heavy_mining_drill`, `high_speed_network_system`, `industrial_controller`, `industrial_cutting_machine`, `industrial_display`, `industrial_inverter`, `industrial_relay`, `industrial_robot`, `industrial_sensor`, `laboratory_equipment`, `launch_vehicle`, `memory_module`, `microcontroller`, `network_switch`, `nuclear_reactor`, `orbital_vehicle`, `processing_equipment`, `quantum_computing_module`, `robotic_arm`, `semiconductor_equipment`, `servo_motor`, `switchgear`, `utility_vehicle`.
- Fixed-point evaluation can unlock several nodes/cascades in one call when stored conditions are already met, especially during migration or level-up.

## 10. Graph integrity findings

| Check | Result |
|---|---|
| Cycles / topological remainder | None |
| Self-references | None |
| Unreachable from an inputless root | None |
| Missing prerequisite nodes | None |
| Missing/mismatched progression entries | None |
| Duplicate output nodes | None |
| Duplicate production IDs | None |
| Missing/duplicate family-root membership | None |

No canonical prerequisite is impossible: all parents exist, every node is root-reachable, and level 25 plus sufficient lifetime output unlocks all 353 nodes (covered by tests). Migration can create noncanonical unlocked ancestry intentionally; that is not a graph defect.

## 11. Graph scale metrics

| Metric | Value |
|---|---:|
| Unique runtime production resources/products | 353 |
| Nodes in progression | 353 |
| Roots | 49 |
| New-game unlocked roots | 9 |
| Directed quantity edges | 708 |
| Maximum depth (root = 0) | 3 |
| Largest branching factor | 32 |
| Multi-parent nodes | 252 |

Runtime-stage counts: Agriculture 10, Assembler 150, Drilling 2, Extractor 37, Fabricator 86, Processor 68.

## 12. Recommended player-facing states and text

The four proposed states are sufficient when derived strictly:

| State | Runtime derivation | Text |
|---|---|---|
| `UNLOCKED` | `production_id in unlocked_production_ids` | `UNLOCKED`, or omit if styling is sufficient |
| `CURRENT` | Locked; level satisfied; every parent production unlocked. Equivalent to runtime `next` | One line per parent: `COPPER ORE 72 / 120`; all AND |
| `LEVEL GATED` | Locked and company below required level; prioritize this even if ancestors are locked | `LEVEL 11` |
| `LOCKED` | Locked; level satisfied; at least one parent production locked. Non-level subset of runtime `later` | Parent names, or no counter until reachable |

A level-satisfied inputless root unlocks in the same reevaluation, so persistent `CURRENT` is not normal for roots. Recommended language is concrete uppercase resource plus `current / required`, `LEVEL N`, and optionally `UNLOCKED`. Avoid `MASTERY`, `NEXT`, `LATER`, and `FIRST COMPLETE`. There is no first-production gate, so do not show `FIRST PRODUCTION` as a requirement.

### Current Production Guide progression strings (unchanged)

Tiles can produce `UNLOCKED`, `UNLOCKED · FIRST COMPLETE`, `UNLOCKED · MASTERY current/target`, `UNLOCKED · MASTERED`, `NEXT · <compact requirement>`, `LATER · <compact requirement>`, and fallback `LATER · Production prerequisite`. Compact forms include `LEVEL N`, `NEED <resource>`, `<RESOURCE> current/target`, `FIRST COMPLETE`, and `MASTERY ...`. Detail rows use `Unlocked`, `Next unlock`, and `Locked`. Full lines/tooltips can emit `REQUIRES COMPANY LEVEL N`, `REQUIRES <FAMILY>`, `REQUIRES UNLOCKED INPUT: <RESOURCE>`, `PRODUCE N MORE <RESOURCE> (current / target)`, `FIRST PRODUCTION COMPLETE`, `FAMILY MASTERY current / target`, and `FAMILY MASTERY COMPLETE`.

Caution: `REQUIRES <FAMILY>` is descriptive text added for level-gated family metadata; `_option_requirements_met` does not enforce family mastery or a family gate. Never convert that string into an edge.

## 13. Recommended visual grouping

Use a technical dependency diagram with depth left to right: roots at depth 0, then Processor, Fabricator, and Assembler tiers. Within depth 0, cluster roots by the 18 primary families and label actual runtime stage (Extractor, Drilling, Agriculture). In later columns, use stage as primary lane and resource category only as secondary color/icon.

Do not force independent branch columns: 252 merge nodes and 32-child maximum fan-out make the graph strongly cross-linked. Directed edges represent quantity prerequisites only; company level is a node badge/gate. Filtering or highlighting selected ancestry/descendancy will be important at 353 nodes, but remains view behavior, not progression.

## 14. Zoom/pan reuse assessment

`ZoomPanGraphicsView` in `src/production_zero/ui/zoom_pan_view.py` is suitable as the viewport foundation. Reuse its `QGraphicsView`/scene, widget proxy, bounded cursor-centered wheel zoom (0.35–1.75), background drag pan, fit-to-view, resize refit, antialiasing, and zoom signal.

Chain-specific node widgets, connector geometry, stage headings, navigation, and chain layout in `factory_view.py` should remain specific. The tree needs its own graph layout/directed-edge rendering. A small generic scene-native content API or configurable fit padding/minimum zoom may help: a 353-node graph may require lower fit scale than 0.35, and a giant widget proxy is less suitable for selective scene items. This does not block reuse of viewport behavior.

## 15. Blockers / decisions before implementation

1. **Authoritative primary stage label:** runtime options identify 37 Extractor, 2 Drilling, and 10 Agriculture roots, while progression JSON normalizes all 49 primary entries to metadata stage `extractor`. Use `ProductionOptionDefinition.stage` for visual grouping; XP currently uses normalized metadata stage.
2. **XP achievements versus edges:** first production and mastery are indirect level contributors only. Decide only whether optional contextual badges are desired; neither is needed for a correct graph.
3. **Migrated state overlay:** grandfathered nodes may have locked ancestors. Preserve canonical edges and render the node unlocked; do not infer a new root.
4. **Large graph interaction scope:** at 353 nodes/708 edges, current minimum fit 0.35 may not be legible. Decide focus/highlight/filter scope before fixing layout dimensions, without adding mechanics.

## Relevant source of truth

- `src/production_zero/core/progression.py`: all unlock state, requirements, evaluation, labels, mastery, migration.
- `src/production_zero/data/resource_progression.json`: production IDs, levels, families, normalized progression stages.
- `src/production_zero/data/game_definitions.json` via `src/production_zero/data/definitions.py`: actual options, inputs, runtime stages, names.
- `src/production_zero/core/simulation.py`: accepted output forwarded to lifetime progress and XP.
- `src/production_zero/core/company_xp.py`: first-production/mastery XP and level-up reevaluation.
- `src/production_zero/core/state.py`: `GameState.production_progress`.
- `src/production_zero/persistence/sqlite_store.py`: serialization, legacy seeding, migration invocation.
- `src/production_zero/ui/factory_view.py`: Guide state/text and Chain Inspector viewport use.
- `src/production_zero/ui/zoom_pan_view.py`: reusable viewport.
- `src/production_zero/ui/event_feed.py`: consumes pending notifications only.
- `tests/test_production_progression.py`, `tests/test_company_xp_progression.py`, `tests/test_sqlite_store.py`: behavioral coverage.

## Appendix A — complete node catalog

All parents are AND. `First gate` is `No` for every node. Children are canonical direct quantity-edge destinations.

| Resource/product ID | Display name | Production ID | Stage | Depth | Level | Quantity parents | First gate | Begins unlocked | Direct children |
|---|---|---|---|---:|---:|---|---|---|---|
| `corn` | Corn | `resource.corn` | Agriculture | 0 | 2 | — | No | No | `corn_meal`, `fermentation_feedstock`, `starch` |
| `cotton` | Cotton | `resource.cotton` | Agriculture | 0 | 4 | — | No | No | `cotton_fiber` |
| `fruit` | Fruit | `resource.fruit` | Agriculture | 0 | 4 | — | No | No | `fruit_concentrate`, `organic_feedstock` |
| `natural_rubber` | Natural Rubber | `resource.natural_rubber` | Agriculture | 0 | 5 | — | No | No | `processed_rubber` |
| `potatoes` | Potatoes | `resource.potatoes` | Agriculture | 0 | 2 | — | No | No | `organic_feedstock`, `starch` |
| `rapeseed` | Rapeseed | `resource.rapeseed` | Agriculture | 0 | 4 | — | No | No | `bio_lubricant`, `vegetable_oil` |
| `soybeans` | Soybeans | `resource.soybeans` | Agriculture | 0 | 2 | — | No | No | `soy_oil`, `soy_protein`, `vegetable_oil` |
| `sugarcane` | Sugarcane | `resource.sugarcane` | Agriculture | 0 | 4 | — | No | No | `fermentation_feedstock`, `fruit_concentrate`, `raw_sugar`, `refined_sugar` |
| `timber` | Timber | `resource.timber` | Agriculture | 0 | 1 | — | No | Yes | `cellulose`, `lumber`, `treated_lumber`, `wood_pulp` |
| `wheat` | Wheat | `resource.wheat` | Agriculture | 0 | 1 | — | No | Yes | `flour`, `organic_feedstock` |
| `crude_oil` | Crude Oil | `resource.crude_oil` | Drilling | 0 | 1 | — | No | Yes | `bitumen`, `carbon_fiber`, `cellulose`, `chemical_feedstock`, `high_purity_silicon`, `industrial_resin`, `polymer`, `synthetic_rubber`, `treated_lumber`, `wood_pulp` |
| `natural_gas` | Natural Gas | `resource.natural_gas` | Drilling | 0 | 5 | — | No | No | `ammonia`, `bio_lubricant`, `carbon_fiber`, `cellulose`, `chemical_feedstock`, `high_purity_silicon`, `hydrogen`, `industrial_gas`, `industrial_resin`, `phosphoric_acid`, `polymer`, `sulfuric_acid`, `synthetic_rubber`, `treated_lumber`, `wood_pulp` |
| `bauxite` | Bauxite | `resource.bauxite` | Extractor | 0 | 1 | — | No | Yes | `aluminum` |
| `borate_ore` | Borate Ore | `resource.borate_ore` | Extractor | 0 | 13 | — | No | No | `glass`, `shielding_material` |
| `chromium_ore` | Chromium Ore | `resource.chromium_ore` | Extractor | 0 | 11 | — | No | No | `chromium`, `stainless_steel` |
| `clay` | Clay | `resource.clay` | Extractor | 0 | 3 | — | No | No | `ceramics` |
| `coal` | Coal | `resource.coal` | Extractor | 0 | 1 | — | No | Yes | `nickel_alloy`, `silicon`, `stainless_steel`, `steel` |
| `cobalt_ore` | Cobalt Ore | `resource.cobalt_ore` | Extractor | 0 | 15 | — | No | No | `cobalt` |
| `copper_ore` | Copper Ore | `resource.copper_ore` | Extractor | 0 | 1 | — | No | Yes | `copper` |
| `fluorspar` | Fluorspar | `resource.fluorspar` | Extractor | 0 | 13 | — | No | No | `high_purity_silicon` |
| `gold_ore` | Gold Ore | `resource.gold_ore` | Extractor | 0 | 18 | — | No | No | `gold` |
| `graphite` | Graphite | `resource.graphite` | Extractor | 0 | 13 | — | No | No | `carbon_fiber`, `purified_graphite` |
| `gypsum` | Gypsum | `resource.gypsum` | Extractor | 0 | 3 | — | No | No | `cement`, `processed_gypsum` |
| `iron_ore` | Iron Ore | `resource.iron_ore` | Extractor | 0 | 1 | — | No | Yes | `galvanized_metal`, `iron`, `nickel_alloy`, `stainless_steel`, `steel`, `vanadium_alloy` |
| `kaolin` | Kaolin | `resource.kaolin` | Extractor | 0 | 3 | — | No | No | `ceramics` |
| `lead_ore` | Lead Ore | `resource.lead_ore` | Extractor | 0 | 9 | — | No | No | `lead`, `nuclear_material`, `shielding_material` |
| `limestone` | Limestone | `resource.limestone` | Extractor | 0 | 1 | — | No | Yes | `cement`, `glass` |
| `lithium_ore` | Lithium Ore | `resource.lithium_ore` | Extractor | 0 | 15 | — | No | No | `lithium` |
| `magnesite` | Magnesite | `resource.magnesite` | Extractor | 0 | 13 | — | No | No | `ceramics` |
| `manganese_ore` | Manganese Ore | `resource.manganese_ore` | Extractor | 0 | 9 | — | No | No | `manganese` |
| `molybdenum_ore` | Molybdenum Ore | `resource.molybdenum_ore` | Extractor | 0 | 22 | — | No | No | `molybdenum`, `nickel_alloy` |
| `nickel_ore` | Nickel Ore | `resource.nickel_ore` | Extractor | 0 | 11 | — | No | No | `nickel`, `nickel_alloy`, `stainless_steel` |
| `niobium_ore` | Niobium Ore | `resource.niobium_ore` | Extractor | 0 | 22 | — | No | No | `niobium`, `superconducting_alloy` |
| `palladium_ore` | Palladium Ore | `resource.palladium_ore` | Extractor | 0 | 20 | — | No | No | `catalyst_metal`, `palladium` |
| `phosphate_rock` | Phosphate Rock | `resource.phosphate_rock` | Extractor | 0 | 7 | — | No | No | `phosphoric_acid` |
| `platinum_ore` | Platinum Ore | `resource.platinum_ore` | Extractor | 0 | 20 | — | No | No | `catalyst_metal`, `platinum` |
| `potash` | Potash | `resource.potash` | Extractor | 0 | 7 | — | No | No | `potassium_compound` |
| `quartz` | Quartz | `resource.quartz` | Extractor | 0 | 1 | — | No | Yes | `high_purity_silicon`, `silicon` |
| `rare_earth_ore` | Rare Earth Ore | `resource.rare_earth_ore` | Extractor | 0 | 15 | — | No | No | `rare_earth_metals`, `superconducting_alloy` |
| `salt` | Salt | `resource.salt` | Extractor | 0 | 7 | — | No | No | `chlorine` |
| `silica_sand` | Silica Sand | `resource.silica_sand` | Extractor | 0 | 3 | — | No | No | `glass` |
| `silver_ore` | Silver Ore | `resource.silver_ore` | Extractor | 0 | 18 | — | No | No | `silver` |
| `sulfur` | Sulfur | `resource.sulfur` | Extractor | 0 | 7 | — | No | No | `phosphoric_acid`, `processed_rubber`, `sulfuric_acid`, `synthetic_rubber` |
| `tin_ore` | Tin Ore | `resource.tin_ore` | Extractor | 0 | 9 | — | No | No | `tin` |
| `titanium_ore` | Titanium Ore | `resource.titanium_ore` | Extractor | 0 | 22 | — | No | No | `superconducting_alloy`, `titanium` |
| `tungsten_ore` | Tungsten Ore | `resource.tungsten_ore` | Extractor | 0 | 22 | — | No | No | `tungsten` |
| `uranium_ore` | Uranium Ore | `resource.uranium_ore` | Extractor | 0 | 25 | — | No | No | `nuclear_material` |
| `vanadium_ore` | Vanadium Ore | `resource.vanadium_ore` | Extractor | 0 | 22 | — | No | No | `vanadium`, `vanadium_alloy` |
| `zinc_ore` | Zinc Ore | `resource.zinc_ore` | Extractor | 0 | 9 | — | No | No | `galvanized_metal`, `zinc` |
| `aluminum` | Aluminum | `recipe.processor.aluminum` | Processor | 1 | 1 | `bauxite` 120 | No | No | `advanced_cell_components`, `aerospace_components`, `aluminum_components`, `avionics_components`, `battery_components`, `compressor_components`, `electrolyzer_components`, `glass_panels`, `network_components`, `power_electronics`, `precision_components`, `solar_components`, `storage_components`, `vehicle_components` |
| `ammonia` | Ammonia | `recipe.processor.ammonia` | Processor | 1 | 5 | `natural_gas` 120 | No | No | `fertilizer_components` |
| `bio_lubricant` | Bio-Lubricant | `recipe.processor.bio_lubricant` | Processor | 1 | 5 | `natural_gas` 120 + `rapeseed` 120 | No | No | `bio_material_components` |
| `bitumen` | Bitumen | `recipe.processor.bitumen` | Processor | 1 | 1 | `crude_oil` 120 | No | No | `asphalt_components` |
| `carbon_fiber` | Carbon Fiber | `recipe.processor.carbon_fiber` | Processor | 1 | 13 | `crude_oil` 120 + `graphite` 120 + `natural_gas` 120 | No | No | `aerospace_components`, `composite_components`, `tire_components`, `wind_components` |
| `catalyst_metal` | Catalyst Metal | `recipe.processor.catalyst_metal` | Processor | 1 | 20 | `palladium_ore` 120 + `platinum_ore` 120 | No | No | `catalyst_components` |
| `cellulose` | Cellulose | `recipe.processor.cellulose` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 + `timber` 120 | No | No | `bio_composite`, `bio_material_components`, `fiber_components`, `membrane_components` |
| `cement` | Cement | `recipe.processor.cement` | Processor | 1 | 3 | `gypsum` 120 + `limestone` 120 | No | No | `asphalt_components`, `concrete_components`, `structural_components` |
| `ceramics` | Ceramics | `recipe.processor.ceramics` | Processor | 1 | 13 | `clay` 120 + `kaolin` 120 + `magnesite` 120 | No | No | `ceramic_components`, `filtration_components` |
| `chemical_feedstock` | Chemical Feedstock | `recipe.processor.chemical_feedstock` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 | No | No | `agricultural_chemicals`, `biodiesel_feedstock`, `chemical_components` |
| `chlorine` | Chlorine | `recipe.processor.chlorine` | Processor | 1 | 7 | `salt` 120 | No | No | `agricultural_chemicals`, `membrane_components` |
| `chromium` | Chromium | `recipe.processor.chromium` | Processor | 1 | 11 | `chromium_ore` 120 | No | No | `bearing_components` |
| `cobalt` | Cobalt | `recipe.processor.cobalt` | Processor | 1 | 15 | `cobalt_ore` 120 | No | No | `advanced_cell_components`, `battery_components`, `battery_materials` |
| `copper` | Copper | `recipe.processor.copper` | Processor | 1 | 1 | `copper_ore` 120 | No | No | `autonomous_components`, `avionics_components`, `computing_components`, `control_electronics`, `copper_wire`, `electrical_components`, `electrolyzer_components`, `insulated_wire`, `memory_components`, `motor_components`, `network_components`, `power_electronics`, `processor_components`, `pump_components`, `semiconductor_components`, `semiconductor_die`, `sensor_components`, `server_components`, `storage_components`, `telecom_components`, `transformer_components` |
| `corn_meal` | Corn Meal | `recipe.processor.corn_meal` | Processor | 1 | 2 | `corn` 120 | No | No | `food_ingredients` |
| `cotton_fiber` | Cotton Fiber | `recipe.processor.cotton_fiber` | Processor | 1 | 4 | `cotton` 120 | No | No | `industrial_fabric`, `technical_textile` |
| `fermentation_feedstock` | Fermentation Feedstock | `recipe.processor.fermentation_feedstock` | Processor | 1 | 4 | `corn` 120 + `sugarcane` 120 | No | No | `biopolymer`, `ethanol_components` |
| `flour` | Flour | `recipe.processor.flour` | Processor | 1 | 1 | `wheat` 120 | No | No | `food_ingredients` |
| `fruit_concentrate` | Fruit Concentrate | `recipe.processor.fruit_concentrate` | Processor | 1 | 4 | `fruit` 120 + `sugarcane` 120 | No | No | `nutrition_components` |
| `galvanized_metal` | Galvanized Metal | `recipe.processor.galvanized_metal` | Processor | 1 | 9 | `iron_ore` 120 + `zinc_ore` 120 | No | No | `corrosion_resistant_components`, `galvanized_components` |
| `glass` | Glass | `recipe.processor.glass` | Processor | 1 | 13 | `borate_ore` 120 + `limestone` 120 + `silica_sand` 120 | No | No | `display_components`, `glass_panels`, `medical_components`, `silicon_substrate`, `solar_components` |
| `gold` | Gold | `recipe.processor.gold` | Processor | 1 | 18 | `gold_ore` 120 | No | No | `ai_compute_components`, `avionics_components`, `computing_components`, `control_electronics`, `electrolyzer_components`, `memory_components`, `network_components`, `power_electronics`, `processor_components`, `semiconductor_components`, `semiconductor_die`, `sensor_components`, `server_components`, `storage_components`, `telecom_components` |
| `high_purity_silicon` | High-Purity Silicon | `recipe.processor.high_purity_silicon` | Processor | 1 | 13 | `crude_oil` 120 + `fluorspar` 120 + `natural_gas` 120 + `quartz` 120 | No | No | `ai_compute_components`, `autonomous_components`, `avionics_components`, `computing_components`, `control_electronics`, `display_components`, `electrolyzer_components`, `memory_components`, `network_components`, `power_electronics`, `processor_components`, `semiconductor_components`, `semiconductor_die`, `sensor_components`, `server_components`, `solar_components`, `storage_components`, `telecom_components` |
| `hydrogen` | Hydrogen | `recipe.processor.hydrogen` | Processor | 1 | 5 | `natural_gas` 120 | No | No | `gas_handling_components` |
| `industrial_gas` | Industrial Gas | `recipe.processor.industrial_gas` | Processor | 1 | 5 | `natural_gas` 120 | No | No | `gas_handling_components` |
| `industrial_resin` | Industrial Resin | `recipe.processor.industrial_resin` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 | No | No | `bio_composite`, `composite_components`, `fiber_components`, `hydraulic_components`, `marine_components`, `wind_components` |
| `iron` | Iron | `recipe.processor.iron` | Processor | 1 | 1 | `iron_ore` 120 | No | No | `iron_components`, `magnetic_components`, `motor_components` |
| `lead` | Lead | `recipe.processor.lead` | Processor | 1 | 9 | `lead_ore` 120 | No | No | `shielding_components` |
| `lithium` | Lithium | `recipe.processor.lithium` | Processor | 1 | 15 | `lithium_ore` 120 | No | No | `advanced_cell_components`, `battery_components`, `battery_materials`, `grid_storage_components` |
| `lumber` | Lumber | `recipe.processor.lumber` | Processor | 1 | 1 | `timber` 120 | No | No | `wooden_components` |
| `manganese` | Manganese | `recipe.processor.manganese` | Processor | 1 | 9 | `manganese_ore` 120 | No | No | `gear_components`, `rail_components` |
| `molybdenum` | Molybdenum | `recipe.processor.molybdenum` | Processor | 1 | 22 | `molybdenum_ore` 120 | No | No | `refractory_alloy_components` |
| `nickel` | Nickel | `recipe.processor.nickel` | Processor | 1 | 11 | `nickel_ore` 120 | No | No | `battery_components`, `battery_materials` |
| `nickel_alloy` | Nickel Alloy | `recipe.processor.nickel_alloy` | Processor | 1 | 22 | `coal` 120 + `iron_ore` 120 + `molybdenum_ore` 120 + `nickel_ore` 120 | No | No | `turbine_components`, `wind_components` |
| `niobium` | Niobium | `recipe.processor.niobium` | Processor | 1 | 22 | `niobium_ore` 120 | No | No | `refractory_alloy_components` |
| `nuclear_material` | Nuclear Material | `recipe.processor.nuclear_material` | Processor | 1 | 25 | `lead_ore` 120 + `uranium_ore` 120 | No | No | `nuclear_fuel_components`, `reactor_components` |
| `organic_feedstock` | Organic Feedstock | `recipe.processor.organic_feedstock` | Processor | 1 | 4 | `fruit` 120 + `potatoes` 120 + `wheat` 120 | No | No | `sweetener_components` |
| `palladium` | Palladium | `recipe.processor.palladium` | Processor | 1 | 20 | `palladium_ore` 120 | No | No | `catalyst_components` |
| `phosphoric_acid` | Phosphoric Acid | `recipe.processor.phosphoric_acid` | Processor | 1 | 7 | `natural_gas` 120 + `phosphate_rock` 120 + `sulfur` 120 | No | No | `agricultural_mineral_components`, `fertilizer_components` |
| `platinum` | Platinum | `recipe.processor.platinum` | Processor | 1 | 20 | `platinum_ore` 120 | No | No | `medical_components` |
| `polymer` | Polymer | `recipe.processor.polymer` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 | No | No | `display_components`, `electrical_components`, `filtration_components`, `industrial_fabric`, `insulated_wire`, `insulation_material`, `membrane_components`, `packaging_components`, `technical_textile` |
| `potassium_compound` | Potassium Compound | `recipe.processor.potassium_compound` | Processor | 1 | 7 | `potash` 120 | No | No | `agricultural_mineral_components` |
| `processed_gypsum` | Processed Gypsum | `recipe.processor.processed_gypsum` | Processor | 1 | 3 | `gypsum` 120 | No | No | `filtration_components`, `insulation_material` |
| `processed_rubber` | Processed Rubber | `recipe.processor.processed_rubber` | Processor | 1 | 7 | `natural_rubber` 120 + `sulfur` 120 | No | No | `industrial_fabric`, `rubber_blend_components`, `tire_components`, `vehicle_components` |
| `purified_graphite` | Purified Graphite | `recipe.processor.purified_graphite` | Processor | 1 | 13 | `graphite` 120 | No | No | `advanced_cell_components`, `grid_storage_components` |
| `rare_earth_metals` | Rare Earth Metals | `recipe.processor.rare_earth_metals` | Processor | 1 | 15 | `rare_earth_ore` 120 | No | No | `ai_compute_components`, `autonomous_components`, `magnetic_components`, `motor_components`, `processor_components`, `sensor_components`, `telecom_components` |
| `raw_sugar` | Raw Sugar | `recipe.processor.raw_sugar` | Processor | 1 | 4 | `sugarcane` 120 | No | No | `sweetener_components` |
| `refined_sugar` | Refined Sugar | `recipe.processor.refined_sugar` | Processor | 1 | 4 | `sugarcane` 120 | No | No | `food_ingredients` |
| `shielding_material` | Shielding Material | `recipe.processor.shielding_material` | Processor | 1 | 13 | `borate_ore` 120 + `lead_ore` 120 | No | No | `nuclear_fuel_components`, `shielding_components` |
| `silicon` | Silicon | `recipe.processor.silicon` | Processor | 1 | 1 | `coal` 120 + `quartz` 120 | No | No | `silicon_substrate` |
| `silver` | Silver | `recipe.processor.silver` | Processor | 1 | 18 | `silver_ore` 120 | No | No | `computing_components`, `control_electronics`, `memory_components`, `semiconductor_die` |
| `soy_oil` | Soy Oil | `recipe.processor.soy_oil` | Processor | 1 | 2 | `soybeans` 120 | No | No | `sweetener_components` |
| `soy_protein` | Soy Protein | `recipe.processor.soy_protein` | Processor | 1 | 2 | `soybeans` 120 | No | No | `nutrition_components` |
| `stainless_steel` | Stainless Steel | `recipe.processor.stainless_steel` | Processor | 1 | 11 | `chromium_ore` 120 + `coal` 120 + `iron_ore` 120 + `nickel_ore` 120 | No | No | `corrosion_resistant_components`, `medical_components`, `stainless_components` |
| `starch` | Starch | `recipe.processor.starch` | Processor | 1 | 2 | `corn` 120 + `potatoes` 120 | No | No | `biopolymer` |
| `steel` | Steel | `recipe.processor.steel` | Processor | 1 | 1 | `coal` 120 + `iron_ore` 120 | No | No | `bearing_components`, `compressor_components`, `concrete_components`, `cutting_tooling`, `gear_components`, `hydraulic_components`, `marine_components`, `mining_components`, `precision_components`, `pump_components`, `rail_components`, `steel_components`, `structural_components`, `transformer_components`, `vehicle_components` |
| `sulfuric_acid` | Sulfuric Acid | `recipe.processor.sulfuric_acid` | Processor | 1 | 7 | `natural_gas` 120 + `sulfur` 120 | No | No | `agricultural_chemicals`, `chemical_components` |
| `superconducting_alloy` | Superconducting Alloy | `recipe.processor.superconducting_alloy` | Processor | 1 | 22 | `niobium_ore` 120 + `rare_earth_ore` 120 + `titanium_ore` 120 | No | No | `refractory_alloy_components` |
| `synthetic_rubber` | Synthetic Rubber | `recipe.processor.synthetic_rubber` | Processor | 1 | 7 | `crude_oil` 120 + `natural_gas` 120 + `sulfur` 120 | No | No | `rubber_blend_components` |
| `tin` | Tin | `recipe.processor.tin` | Processor | 1 | 9 | `tin_ore` 120 | No | No | `electrical_components` |
| `titanium` | Titanium | `recipe.processor.titanium` | Processor | 1 | 22 | `titanium_ore` 120 | No | No | `advanced_alloy_components`, `aerospace_components`, `titanium_components`, `turbine_components`, `wind_components` |
| `treated_lumber` | Treated Lumber | `recipe.processor.treated_lumber` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 + `timber` 120 | No | No | `wooden_components` |
| `tungsten` | Tungsten | `recipe.processor.tungsten` | Processor | 1 | 22 | `tungsten_ore` 120 | No | No | `cutting_tooling`, `mining_components`, `precision_components` |
| `vanadium` | Vanadium | `recipe.processor.vanadium` | Processor | 1 | 22 | `vanadium_ore` 120 | No | No | `advanced_alloy_components` |
| `vanadium_alloy` | Vanadium Alloy | `recipe.processor.vanadium_alloy` | Processor | 1 | 22 | `iron_ore` 120 + `vanadium_ore` 120 | No | No | `advanced_alloy_components`, `grid_storage_components` |
| `vegetable_oil` | Vegetable Oil | `recipe.processor.vegetable_oil` | Processor | 1 | 4 | `rapeseed` 120 + `soybeans` 120 | No | No | `biodiesel_feedstock`, `nutrition_components` |
| `wood_pulp` | Wood Pulp | `recipe.processor.wood_pulp` | Processor | 1 | 5 | `crude_oil` 120 + `natural_gas` 120 + `timber` 120 | No | No | `packaging_components` |
| `zinc` | Zinc | `recipe.processor.zinc` | Processor | 1 | 9 | `zinc_ore` 120 | No | No | `galvanized_components` |
| `ai_compute_components` | AI Compute Components | `recipe.fabricator.ai_compute_components` | Fabricator | 2 | 18 | `gold` 60 + `high_purity_silicon` 60 + `rare_earth_metals` 60 | No | No | `advanced_industrial_robot`, `ai_accelerator`, `ai_server`, `autonomous_vehicle`, `supercomputer` |
| `advanced_alloy_components` | Advanced Alloy Components | `recipe.fabricator.advanced_alloy_components` | Fabricator | 2 | 22 | `titanium` 60 + `vanadium` 60 + `vanadium_alloy` 60 | No | No | `gas_turbine` |
| `advanced_cell_components` | Advanced Cell Components | `recipe.fabricator.advanced_cell_components` | Fabricator | 2 | 15 | `aluminum` 60 + `cobalt` 60 + `lithium` 60 + `purified_graphite` 60 | No | No | `premium_electric_vehicle` |
| `aerospace_components` | Aerospace Components | `recipe.fabricator.aerospace_components` | Fabricator | 2 | 22 | `aluminum` 60 + `carbon_fiber` 60 + `titanium` 60 | No | No | `advanced_aircraft`, `autonomous_aircraft`, `cargo_aircraft`, `commercial_aircraft`, `communication_satellite`, `high_speed_train`, `industrial_drone`, `launch_vehicle`, `light_aircraft`, `navigation_satellite`, `orbital_vehicle`, `satellite` |
| `agricultural_chemicals` | Agricultural Chemicals | `recipe.fabricator.agricultural_chemicals` | Fabricator | 2 | 7 | `chemical_feedstock` 60 + `chlorine` 60 + `sulfuric_acid` 60 | No | No | `advanced_fertilizer`, `crop_protection_products` |
| `agricultural_mineral_components` | Agricultural Mineral Components | `recipe.fabricator.agricultural_mineral_components` | Fabricator | 2 | 7 | `phosphoric_acid` 60 + `potassium_compound` 60 | No | No | `fertilizer` |
| `aluminum_components` | Aluminum Components | `recipe.fabricator.aluminum_components` | Fabricator | 2 | 1 | `aluminum` 60 | No | No | `industrial_glass_panels`, `power_cable` |
| `asphalt_components` | Asphalt Components | `recipe.fabricator.asphalt_components` | Fabricator | 2 | 3 | `bitumen` 60 + `cement` 60 | No | No | `construction_materials` |
| `autonomous_components` | Autonomous Components | `recipe.fabricator.autonomous_components` | Fabricator | 2 | 15 | `copper` 60 + `high_purity_silicon` 60 + `rare_earth_metals` 60 | No | No | `advanced_industrial_robot`, `autonomous_aircraft`, `autonomous_cargo_ship`, `autonomous_freight_train`, `autonomous_vehicle` |
| `avionics_components` | Avionics Components | `recipe.fabricator.avionics_components` | Fabricator | 2 | 18 | `aluminum` 60 + `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `advanced_aircraft`, `autonomous_aircraft`, `cargo_aircraft`, `commercial_aircraft`, `light_aircraft`, `orbital_vehicle` |
| `battery_components` | Battery Components | `recipe.fabricator.battery_components` | Fabricator | 2 | 15 | `aluminum` 60 + `cobalt` 60 + `lithium` 60 + `nickel` 60 | No | No | `electric_vehicle`, `grid_battery`, `industrial_drone` |
| `battery_materials` | Battery Materials | `recipe.fabricator.battery_materials` | Fabricator | 2 | 15 | `cobalt` 60 + `lithium` 60 + `nickel` 60 | No | No | `grid_battery` |
| `bearing_components` | Bearing Components | `recipe.fabricator.bearing_components` | Fabricator | 2 | 11 | `chromium` 60 + `steel` 60 | No | No | `gearbox` |
| `bio_composite` | Bio-Composite | `recipe.fabricator.bio_composite` | Fabricator | 2 | 5 | `cellulose` 60 + `industrial_resin` 60 | No | No | `bioplastic`, `sustainable_packaging` |
| `bio_material_components` | Bio-Material Components | `recipe.fabricator.bio_material_components` | Fabricator | 2 | 5 | `bio_lubricant` 60 + `cellulose` 60 | No | No | `bio_based_chemicals` |
| `biodiesel_feedstock` | Biodiesel Feedstock | `recipe.fabricator.biodiesel_feedstock` | Fabricator | 2 | 5 | `chemical_feedstock` 60 + `vegetable_oil` 60 | No | No | `biodiesel` |
| `biopolymer` | Biopolymer | `recipe.fabricator.biopolymer` | Fabricator | 2 | 4 | `fermentation_feedstock` 60 + `starch` 60 | No | No | `bioplastic` |
| `catalyst_components` | Catalyst Components | `recipe.fabricator.catalyst_components` | Fabricator | 2 | 20 | `catalyst_metal` 60 + `palladium` 60 | No | No | `synthetic_fuel_plant` |
| `ceramic_components` | Ceramic Components | `recipe.fabricator.ceramic_components` | Fabricator | 2 | 13 | `ceramics` 60 | No | No | `advanced_furnace`, `advanced_semiconductor_equipment`, `semiconductor_equipment` |
| `chemical_components` | Chemical Components | `recipe.fabricator.chemical_components` | Fabricator | 2 | 7 | `chemical_feedstock` 60 + `sulfuric_acid` 60 | No | No | `bio_based_chemicals`, `biofuel`, `carbon_capture_plant`, `crop_protection_products`, `industrial_chemicals`, `industrial_rubber_products`, `synthetic_fuel_plant` |
| `composite_components` | Composite Components | `recipe.fabricator.composite_components` | Fabricator | 2 | 13 | `carbon_fiber` 60 + `industrial_resin` 60 | No | No | `advanced_protective_equipment`, `engineered_structures`, `high_speed_vessel`, `industrial_plastics` |
| `compressor_components` | Compressor Components | `recipe.fabricator.compressor_components` | Fabricator | 2 | 1 | `aluminum` 60 + `steel` 60 | No | No | `carbon_capture_plant`, `industrial_compressor` |
| `computing_components` | Computing Components | `recipe.fabricator.computing_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `silver` 60 | No | No | `diagnostic_system`, `industrial_computer`, `machine_vision_system`, `server` |
| `concrete_components` | Concrete Components | `recipe.fabricator.concrete_components` | Fabricator | 2 | 3 | `cement` 60 + `steel` 60 | No | No | `construction_materials`, `prefabricated_structures`, `reinforced_concrete`, `structural_systems` |
| `control_electronics` | Control Electronics | `recipe.fabricator.control_electronics` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `silver` 60 | No | No | `advanced_furnace`, `advanced_medical_equipment`, `advanced_semiconductor_equipment`, `autonomous_control_system`, `autonomous_mobile_robot`, `cnc_machine`, `commercial_truck`, `container_ship`, `heavy_machinery`, `heavy_mining_drill`, `high_speed_network_system`, `industrial_controller`, `industrial_cutting_machine`, `industrial_display`, `industrial_inverter`, `industrial_relay`, `industrial_robot`, `industrial_sensor`, `laboratory_equipment`, `launch_vehicle`, `memory_module`, `microcontroller`, `network_switch`, `nuclear_reactor`, `orbital_vehicle`, `processing_equipment`, `quantum_computing_module`, `robotic_arm`, `semiconductor_equipment`, `servo_motor`, `switchgear`, `utility_vehicle` |
| `copper_wire` | Copper Wire | `recipe.fabricator.copper_wire` | Fabricator | 2 | 1 | `copper` 60 | No | No | `basic_chip`, `electrical_cable` |
| `corrosion_resistant_components` | Corrosion Resistant Components | `recipe.fabricator.corrosion_resistant_components` | Fabricator | 2 | 11 | `galvanized_metal` 60 + `stainless_steel` 60 | No | No | `tanker` |
| `cutting_tooling` | Cutting Tooling | `recipe.fabricator.cutting_tooling` | Fabricator | 2 | 22 | `steel` 60 + `tungsten` 60 | No | No | `industrial_cutting_machine` |
| `display_components` | Display Components | `recipe.fabricator.display_components` | Fabricator | 2 | 13 | `glass` 60 + `high_purity_silicon` 60 + `polymer` 60 | No | No | `industrial_computer`, `medical_monitor`, `premium_electric_vehicle` |
| `electrical_components` | Electrical Components | `recipe.fabricator.electrical_components` | Fabricator | 2 | 9 | `copper` 60 + `polymer` 60 + `tin` 60 | No | No | `electric_motor`, `industrial_equipment`, `industrial_relay`, `switchgear`, `transformer` |
| `electrolyzer_components` | Electrolyzer Components | `recipe.fabricator.electrolyzer_components` | Fabricator | 2 | 18 | `aluminum` 60 + `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `fusion_reactor_module`, `hydrogen_electrolyzer`, `synthetic_fuel_plant` |
| `ethanol_components` | Ethanol Components | `recipe.fabricator.ethanol_components` | Fabricator | 2 | 4 | `fermentation_feedstock` 60 | No | No | `biofuel` |
| `fertilizer_components` | Fertilizer Components | `recipe.fabricator.fertilizer_components` | Fabricator | 2 | 7 | `ammonia` 60 + `phosphoric_acid` 60 | No | No | `advanced_fertilizer`, `fertilizer` |
| `fiber_components` | Fiber Components | `recipe.fabricator.fiber_components` | Fabricator | 2 | 5 | `cellulose` 60 + `industrial_resin` 60 | No | No | `industrial_insulation` |
| `filtration_components` | Filtration Components | `recipe.fabricator.filtration_components` | Fabricator | 2 | 13 | `ceramics` 60 + `polymer` 60 + `processed_gypsum` 60 | No | No | `carbon_capture_plant`, `desalination_plant` |
| `food_ingredients` | Food Ingredients | `recipe.fabricator.food_ingredients` | Fabricator | 2 | 4 | `corn_meal` 60 + `flour` 60 + `refined_sugar` 60 | No | No | `animal_feed`, `bakery_products`, `packaged_food`, `packaged_meals`, `processed_food` |
| `galvanized_components` | Galvanized Components | `recipe.fabricator.galvanized_components` | Fabricator | 2 | 9 | `galvanized_metal` 60 + `zinc` 60 | No | No | `industrial_hall_modules` |
| `gas_handling_components` | Gas Handling Components | `recipe.fabricator.gas_handling_components` | Fabricator | 2 | 5 | `hydrogen` 60 + `industrial_gas` 60 | No | No | `industrial_chemicals` |
| `gear_components` | Gear Components | `recipe.fabricator.gear_components` | Fabricator | 2 | 9 | `manganese` 60 + `steel` 60 | No | No | `gearbox`, `industrial_crusher` |
| `glass_panels` | Glass Panels | `recipe.fabricator.glass_panels` | Fabricator | 2 | 13 | `aluminum` 60 + `glass` 60 | No | No | `industrial_display`, `industrial_glass_panels`, `industrial_hall_modules`, `laboratory_equipment`, `safety_equipment` |
| `grid_storage_components` | Grid Storage Components | `recipe.fabricator.grid_storage_components` | Fabricator | 2 | 22 | `lithium` 60 + `purified_graphite` 60 + `vanadium_alloy` 60 | No | No | `data_center_module`, `supercomputer` |
| `hydraulic_components` | Hydraulic Components | `recipe.fabricator.hydraulic_components` | Fabricator | 2 | 5 | `industrial_resin` 60 + `steel` 60 | No | No | `excavator`, `heavy_machinery`, `heavy_mining_drill`, `hydraulic_system` |
| `industrial_fabric` | Industrial Fabric | `recipe.fabricator.industrial_fabric` | Fabricator | 2 | 7 | `cotton_fiber` 60 + `polymer` 60 + `processed_rubber` 60 | No | No | `advanced_protective_equipment`, `commercial_furniture`, `industrial_clothing`, `protective_clothing`, `safety_equipment`, `workwear` |
| `insulated_wire` | Insulated Wire | `recipe.fabricator.insulated_wire` | Fabricator | 2 | 5 | `copper` 60 + `polymer` 60 | No | No | `communication_cable`, `electrical_cable`, `power_cable` |
| `insulation_material` | Insulation Material | `recipe.fabricator.insulation_material` | Fabricator | 2 | 5 | `polymer` 60 + `processed_gypsum` 60 | No | No | `high_voltage_equipment`, `industrial_hall_modules`, `industrial_insulation`, `protective_packaging` |
| `iron_components` | Iron Components | `recipe.fabricator.iron_components` | Fabricator | 2 | 1 | `iron` 60 | No | No | `industrial_equipment` |
| `magnetic_components` | Magnetic Components | `recipe.fabricator.magnetic_components` | Fabricator | 2 | 15 | `iron` 60 + `rare_earth_metals` 60 | No | No | `autonomous_control_system`, `industrial_laser`, `precision_motor`, `radio_transceiver` |
| `marine_components` | Marine Components | `recipe.fabricator.marine_components` | Fabricator | 2 | 5 | `industrial_resin` 60 + `steel` 60 | No | No | `autonomous_cargo_ship`, `cargo_vessel`, `container_ship`, `high_speed_vessel`, `tanker`, `workboat` |
| `medical_components` | Medical Components | `recipe.fabricator.medical_components` | Fabricator | 2 | 20 | `glass` 60 + `platinum` 60 + `stainless_steel` 60 | No | No | `advanced_medical_equipment`, `diagnostic_system`, `medical_monitor` |
| `membrane_components` | Membrane Components | `recipe.fabricator.membrane_components` | Fabricator | 2 | 7 | `cellulose` 60 + `chlorine` 60 + `polymer` 60 | No | No | `desalination_plant` |
| `memory_components` | Memory Components | `recipe.fabricator.memory_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `silver` 60 | No | No | `compute_node`, `cpu`, `memory_module`, `server` |
| `mining_components` | Mining Components | `recipe.fabricator.mining_components` | Fabricator | 2 | 22 | `steel` 60 + `tungsten` 60 | No | No | `heavy_mining_drill`, `industrial_crusher`, `mining_drill`, `mining_equipment` |
| `motor_components` | Motor Components | `recipe.fabricator.motor_components` | Fabricator | 2 | 15 | `copper` 60 + `iron` 60 + `rare_earth_metals` 60 | No | No | `electric_locomotive`, `electric_motor`, `electric_vehicle`, `industrial_compressor`, `industrial_generator`, `industrial_pump`, `industrial_robot`, `mining_drill`, `precision_motor`, `robotic_actuator`, `robotic_arm`, `servo_motor` |
| `network_components` | Network Components | `recipe.fabricator.network_components` | Fabricator | 2 | 18 | `aluminum` 60 + `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `ai_server`, `autonomous_cargo_ship`, `autonomous_freight_train`, `communication_satellite`, `compute_node`, `high_speed_network_system`, `network_switch`, `router`, `server_rack`, `supercomputer` |
| `nuclear_fuel_components` | Nuclear Fuel Components | `recipe.fabricator.nuclear_fuel_components` | Fabricator | 2 | 25 | `nuclear_material` 60 + `shielding_material` 60 | No | No | `fusion_reactor_module`, `nuclear_fuel_assembly`, `nuclear_reactor` |
| `nutrition_components` | Nutrition Components | `recipe.fabricator.nutrition_components` | Fabricator | 2 | 4 | `fruit_concentrate` 60 + `soy_protein` 60 + `vegetable_oil` 60 | No | No | `animal_feed`, `packaged_beverages`, `packaged_meals`, `packaged_nutrition`, `processed_food`, `soft_drinks` |
| `packaging_components` | Packaging Components | `recipe.fabricator.packaging_components` | Fabricator | 2 | 5 | `polymer` 60 + `wood_pulp` 60 | No | No | `bakery_products`, `industrial_packaging`, `industrial_plastics`, `packaged_beverages`, `packaged_food`, `packaged_meals`, `packaged_nutrition`, `packaging_materials`, `protective_packaging`, `soft_drinks`, `sustainable_packaging` |
| `power_electronics` | Power Electronics | `recipe.fabricator.power_electronics` | Fabricator | 2 | 18 | `aluminum` 60 + `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `ai_accelerator`, `autonomous_control_system`, `cellular_base_station`, `desalination_plant`, `electric_locomotive`, `grid_battery`, `grid_storage_system`, `high_speed_train`, `high_voltage_equipment`, `hydrogen_electrolyzer`, `industrial_inverter`, `solar_array`, `superconducting_magnet_system`, `wind_turbine` |
| `precision_components` | Precision Components | `recipe.fabricator.precision_components` | Fabricator | 2 | 22 | `aluminum` 60 + `steel` 60 + `tungsten` 60 | No | No | `advanced_medical_equipment`, `advanced_semiconductor_equipment`, `cnc_machine`, `industrial_cutting_machine`, `industrial_laser`, `industrial_robot`, `industrial_seals`, `laboratory_equipment`, `precision_motor`, `robotic_actuator`, `robotic_arm`, `semiconductor_equipment`, `servo_motor`, `surgical_equipment` |
| `processor_components` | Processor Components | `recipe.fabricator.processor_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `rare_earth_metals` 60 | No | No | `autonomous_control_system`, `compute_node`, `cpu`, `quantum_computing_module` |
| `pump_components` | Pump Components | `recipe.fabricator.pump_components` | Fabricator | 2 | 1 | `copper` 60 + `steel` 60 | No | No | `carbon_capture_plant`, `desalination_plant`, `industrial_pump`, `processing_equipment`, `tanker` |
| `rail_components` | Rail Components | `recipe.fabricator.rail_components` | Fabricator | 2 | 9 | `manganese` 60 + `steel` 60 | No | No | `autonomous_freight_train`, `diesel_locomotive`, `electric_locomotive`, `freight_railcar`, `high_speed_train`, `railway_track` |
| `reactor_components` | Reactor Components | `recipe.fabricator.reactor_components` | Fabricator | 2 | 25 | `nuclear_material` 60 | No | No | `fusion_reactor_module`, `nuclear_reactor` |
| `refractory_alloy_components` | Refractory Alloy Components | `recipe.fabricator.refractory_alloy_components` | Fabricator | 2 | 22 | `molybdenum` 60 + `niobium` 60 + `superconducting_alloy` 60 | No | No | `fusion_reactor_module`, `quantum_computing_module`, `superconducting_magnet_system` |
| `rubber_blend_components` | Rubber Blend Components | `recipe.fabricator.rubber_blend_components` | Fabricator | 2 | 7 | `processed_rubber` 60 + `synthetic_rubber` 60 | No | No | `industrial_rubber_products` |
| `semiconductor_components` | Semiconductor Components | `recipe.fabricator.semiconductor_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `basic_chip`, `industrial_laser`, `microchip` |
| `semiconductor_die` | Semiconductor Die | `recipe.fabricator.semiconductor_die` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `silver` 60 | No | No | `microchip`, `microcontroller` |
| `sensor_components` | Sensor Components | `recipe.fabricator.sensor_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `rare_earth_metals` 60 | No | No | `advanced_industrial_robot`, `advanced_medical_equipment`, `advanced_protective_equipment`, `advanced_semiconductor_equipment`, `autonomous_aircraft`, `autonomous_cargo_ship`, `autonomous_mobile_robot`, `autonomous_vehicle`, `commercial_truck`, `diagnostic_system`, `industrial_controller`, `industrial_drone`, `industrial_robot`, `industrial_sensor`, `machine_vision_system`, `medical_monitor`, `navigation_satellite`, `utility_vehicle` |
| `server_components` | Server Components | `recipe.fabricator.server_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `ai_server`, `data_center_module`, `server_rack`, `supercomputer` |
| `shielding_components` | Shielding Components | `recipe.fabricator.shielding_components` | Fabricator | 2 | 13 | `lead` 60 + `shielding_material` 60 | No | No | `nuclear_fuel_assembly` |
| `silicon_substrate` | Silicon Substrate | `recipe.fabricator.silicon_substrate` | Fabricator | 2 | 13 | `glass` 60 + `silicon` 60 | No | No | `basic_chip` |
| `solar_components` | Solar Components | `recipe.fabricator.solar_components` | Fabricator | 2 | 13 | `aluminum` 60 + `glass` 60 + `high_purity_silicon` 60 | No | No | `communication_satellite`, `satellite`, `solar_array` |
| `stainless_components` | Stainless Components | `recipe.fabricator.stainless_components` | Fabricator | 2 | 11 | `stainless_steel` 60 | No | No | `advanced_furnace`, `steam_turbine`, `surgical_equipment` |
| `steel_components` | Steel Components | `recipe.fabricator.steel_components` | Fabricator | 2 | 1 | `steel` 60 | No | No | `cargo_vessel`, `hydraulic_system`, `industrial_equipment`, `mining_drill`, `mining_equipment`, `processing_equipment`, `railway_track`, `reinforced_concrete` |
| `storage_components` | Storage Components | `recipe.fabricator.storage_components` | Fabricator | 2 | 18 | `aluminum` 60 + `copper` 60 + `gold` 60 + `high_purity_silicon` 60 | No | No | `grid_storage_system` |
| `structural_components` | Structural Components | `recipe.fabricator.structural_components` | Fabricator | 2 | 3 | `cement` 60 + `steel` 60 | No | No | `cellular_base_station`, `cnc_machine`, `construction_frames`, `container_ship`, `data_center_module`, `engineered_structures`, `excavator`, `freight_railcar`, `heavy_machinery`, `industrial_hall_modules`, `nuclear_reactor`, `prefabricated_structures`, `server_rack`, `structural_systems`, `wind_turbine` |
| `sweetener_components` | Sweetener Components | `recipe.fabricator.sweetener_components` | Fabricator | 2 | 4 | `organic_feedstock` 60 + `raw_sugar` 60 + `soy_oil` 60 | No | No | `packaged_food` |
| `technical_textile` | Technical Textile | `recipe.fabricator.technical_textile` | Fabricator | 2 | 5 | `cotton_fiber` 60 + `polymer` 60 | No | No | `clothing`, `industrial_clothing`, `workwear` |
| `telecom_components` | Telecom Components | `recipe.fabricator.telecom_components` | Fabricator | 2 | 18 | `copper` 60 + `gold` 60 + `high_purity_silicon` 60 + `rare_earth_metals` 60 | No | No | `cellular_base_station`, `communication_cable`, `communication_satellite`, `navigation_satellite`, `radio_transceiver`, `router`, `satellite` |
| `tire_components` | Tire Components | `recipe.fabricator.tire_components` | Fabricator | 2 | 13 | `carbon_fiber` 60 + `processed_rubber` 60 | No | No | `commercial_truck`, `industrial_rubber_products`, `industrial_seals`, `industrial_tires`, `protective_clothing`, `safety_equipment` |
| `titanium_components` | Titanium Components | `recipe.fabricator.titanium_components` | Fabricator | 2 | 22 | `titanium` 60 | No | No | `rocket_engine` |
| `transformer_components` | Transformer Components | `recipe.fabricator.transformer_components` | Fabricator | 2 | 1 | `copper` 60 + `steel` 60 | No | No | `high_voltage_equipment`, `transformer` |
| `turbine_components` | Turbine Components | `recipe.fabricator.turbine_components` | Fabricator | 2 | 22 | `nickel_alloy` 60 + `titanium` 60 | No | No | `advanced_aircraft`, `combustion_vehicle`, `commercial_aircraft`, `diesel_locomotive`, `gas_turbine`, `high_speed_vessel`, `industrial_generator`, `jet_engine`, `launch_vehicle`, `rocket_engine`, `steam_turbine`, `workboat` |
| `vehicle_components` | Vehicle Components | `recipe.fabricator.vehicle_components` | Fabricator | 2 | 7 | `aluminum` 60 + `processed_rubber` 60 + `steel` 60 | No | No | `autonomous_mobile_robot`, `autonomous_vehicle`, `combustion_vehicle`, `commercial_truck`, `electric_vehicle`, `excavator`, `premium_electric_vehicle`, `utility_vehicle` |
| `wind_components` | Wind Components | `recipe.fabricator.wind_components` | Fabricator | 2 | 22 | `carbon_fiber` 60 + `industrial_resin` 60 + `nickel_alloy` 60 + `titanium` 60 | No | No | `wind_turbine` |
| `wooden_components` | Wooden Components | `recipe.fabricator.wooden_components` | Fabricator | 2 | 5 | `lumber` 60 + `treated_lumber` 60 | No | No | `cargo_pallets`, `commercial_furniture`, `construction_frames`, `construction_materials`, `industrial_packaging`, `prefabricated_structures` |
| `ai_accelerator` | AI Accelerator | `recipe.assembler.ai_accelerator` | Assembler | 3 | 18 | `ai_compute_components` 60 + `power_electronics` 60 | No | No | — |
| `ai_server` | AI Server | `recipe.assembler.ai_server` | Assembler | 3 | 18 | `ai_compute_components` 60 + `network_components` 60 + `server_components` 60 | No | No | — |
| `advanced_aircraft` | Advanced Aircraft | `recipe.assembler.advanced_aircraft` | Assembler | 3 | 22 | `aerospace_components` 60 + `avionics_components` 60 + `turbine_components` 60 | No | No | — |
| `advanced_fertilizer` | Advanced Fertilizer | `recipe.assembler.advanced_fertilizer` | Assembler | 3 | 7 | `agricultural_chemicals` 60 + `fertilizer_components` 60 | No | No | — |
| `advanced_furnace` | Advanced Furnace | `recipe.assembler.advanced_furnace` | Assembler | 3 | 18 | `ceramic_components` 60 + `control_electronics` 60 + `stainless_components` 60 | No | No | — |
| `advanced_industrial_robot` | Advanced Industrial Robot | `recipe.assembler.advanced_industrial_robot` | Assembler | 3 | 18 | `ai_compute_components` 60 + `autonomous_components` 60 + `sensor_components` 60 | No | No | — |
| `advanced_medical_equipment` | Advanced Medical Equipment | `recipe.assembler.advanced_medical_equipment` | Assembler | 3 | 22 | `control_electronics` 60 + `medical_components` 60 + `precision_components` 60 + `sensor_components` 60 | No | No | — |
| `advanced_protective_equipment` | Advanced Protective Equipment | `recipe.assembler.advanced_protective_equipment` | Assembler | 3 | 18 | `composite_components` 60 + `industrial_fabric` 60 + `sensor_components` 60 | No | No | — |
| `advanced_semiconductor_equipment` | Advanced Semiconductor Equipment | `recipe.assembler.advanced_semiconductor_equipment` | Assembler | 3 | 22 | `ceramic_components` 60 + `control_electronics` 60 + `precision_components` 60 + `sensor_components` 60 | No | No | — |
| `animal_feed` | Animal Feed | `recipe.assembler.animal_feed` | Assembler | 3 | 4 | `food_ingredients` 60 + `nutrition_components` 60 | No | No | — |
| `autonomous_aircraft` | Autonomous Aircraft | `recipe.assembler.autonomous_aircraft` | Assembler | 3 | 22 | `aerospace_components` 60 + `autonomous_components` 60 + `avionics_components` 60 + `sensor_components` 60 | No | No | — |
| `autonomous_cargo_ship` | Autonomous Cargo Ship | `recipe.assembler.autonomous_cargo_ship` | Assembler | 3 | 18 | `autonomous_components` 60 + `marine_components` 60 + `network_components` 60 + `sensor_components` 60 | No | No | — |
| `autonomous_control_system` | Autonomous Control System | `recipe.assembler.autonomous_control_system` | Assembler | 3 | 18 | `control_electronics` 60 + `magnetic_components` 60 + `power_electronics` 60 + `processor_components` 60 | No | No | — |
| `autonomous_freight_train` | Autonomous Freight Train | `recipe.assembler.autonomous_freight_train` | Assembler | 3 | 18 | `autonomous_components` 60 + `network_components` 60 + `rail_components` 60 | No | No | — |
| `autonomous_mobile_robot` | Autonomous Mobile Robot | `recipe.assembler.autonomous_mobile_robot` | Assembler | 3 | 18 | `control_electronics` 60 + `sensor_components` 60 + `vehicle_components` 60 | No | No | — |
| `autonomous_vehicle` | Autonomous Vehicle | `recipe.assembler.autonomous_vehicle` | Assembler | 3 | 18 | `ai_compute_components` 60 + `autonomous_components` 60 + `sensor_components` 60 + `vehicle_components` 60 | No | No | — |
| `bakery_products` | Bakery Products | `recipe.assembler.bakery_products` | Assembler | 3 | 5 | `food_ingredients` 60 + `packaging_components` 60 | No | No | — |
| `basic_chip` | Basic Chip | `recipe.assembler.basic_chip` | Assembler | 3 | 18 | `copper_wire` 60 + `semiconductor_components` 60 + `silicon_substrate` 60 | No | No | — |
| `bio_based_chemicals` | Bio-Based Chemicals | `recipe.assembler.bio_based_chemicals` | Assembler | 3 | 7 | `bio_material_components` 60 + `chemical_components` 60 | No | No | — |
| `biodiesel` | Biodiesel | `recipe.assembler.biodiesel` | Assembler | 3 | 5 | `biodiesel_feedstock` 60 | No | No | — |
| `biofuel` | Biofuel | `recipe.assembler.biofuel` | Assembler | 3 | 7 | `chemical_components` 60 + `ethanol_components` 60 | No | No | — |
| `bioplastic` | Bioplastic | `recipe.assembler.bioplastic` | Assembler | 3 | 5 | `bio_composite` 60 + `biopolymer` 60 | No | No | — |
| `cnc_machine` | CNC Machine | `recipe.assembler.cnc_machine` | Assembler | 3 | 22 | `control_electronics` 60 + `precision_components` 60 + `structural_components` 60 | No | No | — |
| `cpu` | CPU | `recipe.assembler.cpu` | Assembler | 3 | 18 | `memory_components` 60 + `processor_components` 60 | No | No | — |
| `carbon_capture_plant` | Carbon Capture Plant | `recipe.assembler.carbon_capture_plant` | Assembler | 3 | 13 | `chemical_components` 60 + `compressor_components` 60 + `filtration_components` 60 + `pump_components` 60 | No | No | — |
| `cargo_aircraft` | Cargo Aircraft | `recipe.assembler.cargo_aircraft` | Assembler | 3 | 22 | `aerospace_components` 60 + `avionics_components` 60 | No | No | — |
| `cargo_pallets` | Cargo Pallets | `recipe.assembler.cargo_pallets` | Assembler | 3 | 5 | `wooden_components` 60 | No | No | — |
| `cargo_vessel` | Cargo Vessel | `recipe.assembler.cargo_vessel` | Assembler | 3 | 5 | `marine_components` 60 + `steel_components` 60 | No | No | — |
| `cellular_base_station` | Cellular Base Station | `recipe.assembler.cellular_base_station` | Assembler | 3 | 18 | `power_electronics` 60 + `structural_components` 60 + `telecom_components` 60 | No | No | — |
| `clothing` | Clothing | `recipe.assembler.clothing` | Assembler | 3 | 5 | `technical_textile` 60 | No | No | — |
| `combustion_vehicle` | Combustion Vehicle | `recipe.assembler.combustion_vehicle` | Assembler | 3 | 22 | `turbine_components` 60 + `vehicle_components` 60 | No | No | — |
| `commercial_aircraft` | Commercial Aircraft | `recipe.assembler.commercial_aircraft` | Assembler | 3 | 22 | `aerospace_components` 60 + `avionics_components` 60 + `turbine_components` 60 | No | No | — |
| `commercial_furniture` | Commercial Furniture | `recipe.assembler.commercial_furniture` | Assembler | 3 | 7 | `industrial_fabric` 60 + `wooden_components` 60 | No | No | — |
| `commercial_truck` | Commercial Truck | `recipe.assembler.commercial_truck` | Assembler | 3 | 18 | `control_electronics` 60 + `sensor_components` 60 + `tire_components` 60 + `vehicle_components` 60 | No | No | — |
| `communication_cable` | Communication Cable | `recipe.assembler.communication_cable` | Assembler | 3 | 18 | `insulated_wire` 60 + `telecom_components` 60 | No | No | — |
| `communication_satellite` | Communication Satellite | `recipe.assembler.communication_satellite` | Assembler | 3 | 22 | `aerospace_components` 60 + `network_components` 60 + `solar_components` 60 + `telecom_components` 60 | No | No | — |
| `compute_node` | Compute Node | `recipe.assembler.compute_node` | Assembler | 3 | 18 | `memory_components` 60 + `network_components` 60 + `processor_components` 60 | No | No | — |
| `construction_frames` | Construction Frames | `recipe.assembler.construction_frames` | Assembler | 3 | 5 | `structural_components` 60 + `wooden_components` 60 | No | No | — |
| `construction_materials` | Construction Materials | `recipe.assembler.construction_materials` | Assembler | 3 | 5 | `asphalt_components` 60 + `concrete_components` 60 + `wooden_components` 60 | No | No | — |
| `container_ship` | Container Ship | `recipe.assembler.container_ship` | Assembler | 3 | 18 | `control_electronics` 60 + `marine_components` 60 + `structural_components` 60 | No | No | — |
| `crop_protection_products` | Crop Protection Products | `recipe.assembler.crop_protection_products` | Assembler | 3 | 7 | `agricultural_chemicals` 60 + `chemical_components` 60 | No | No | — |
| `data_center_module` | Data Center Module | `recipe.assembler.data_center_module` | Assembler | 3 | 22 | `grid_storage_components` 60 + `server_components` 60 + `structural_components` 60 | No | No | — |
| `desalination_plant` | Desalination Plant | `recipe.assembler.desalination_plant` | Assembler | 3 | 18 | `filtration_components` 60 + `membrane_components` 60 + `power_electronics` 60 + `pump_components` 60 | No | No | — |
| `diagnostic_system` | Diagnostic System | `recipe.assembler.diagnostic_system` | Assembler | 3 | 20 | `computing_components` 60 + `medical_components` 60 + `sensor_components` 60 | No | No | — |
| `diesel_locomotive` | Diesel Locomotive | `recipe.assembler.diesel_locomotive` | Assembler | 3 | 22 | `rail_components` 60 + `turbine_components` 60 | No | No | — |
| `electric_locomotive` | Electric Locomotive | `recipe.assembler.electric_locomotive` | Assembler | 3 | 18 | `motor_components` 60 + `power_electronics` 60 + `rail_components` 60 | No | No | — |
| `electric_motor` | Electric Motor | `recipe.assembler.electric_motor` | Assembler | 3 | 15 | `electrical_components` 60 + `motor_components` 60 | No | No | — |
| `electric_vehicle` | Electric Vehicle | `recipe.assembler.electric_vehicle` | Assembler | 3 | 15 | `battery_components` 60 + `motor_components` 60 + `vehicle_components` 60 | No | No | — |
| `electrical_cable` | Electrical Cable | `recipe.assembler.electrical_cable` | Assembler | 3 | 5 | `copper_wire` 60 + `insulated_wire` 60 | No | No | — |
| `engineered_structures` | Engineered Structures | `recipe.assembler.engineered_structures` | Assembler | 3 | 13 | `composite_components` 60 + `structural_components` 60 | No | No | — |
| `excavator` | Excavator | `recipe.assembler.excavator` | Assembler | 3 | 7 | `hydraulic_components` 60 + `structural_components` 60 + `vehicle_components` 60 | No | No | — |
| `fertilizer` | Fertilizer | `recipe.assembler.fertilizer` | Assembler | 3 | 7 | `agricultural_mineral_components` 60 + `fertilizer_components` 60 | No | No | — |
| `freight_railcar` | Freight Railcar | `recipe.assembler.freight_railcar` | Assembler | 3 | 9 | `rail_components` 60 + `structural_components` 60 | No | No | — |
| `fusion_reactor_module` | Fusion Reactor Module | `recipe.assembler.fusion_reactor_module` | Assembler | 3 | 25 | `electrolyzer_components` 60 + `nuclear_fuel_components` 60 + `reactor_components` 60 + `refractory_alloy_components` 60 | No | No | — |
| `gas_turbine` | Gas Turbine | `recipe.assembler.gas_turbine` | Assembler | 3 | 22 | `advanced_alloy_components` 60 + `turbine_components` 60 | No | No | — |
| `gearbox` | Gearbox | `recipe.assembler.gearbox` | Assembler | 3 | 11 | `bearing_components` 60 + `gear_components` 60 | No | No | — |
| `grid_battery` | Grid Battery | `recipe.assembler.grid_battery` | Assembler | 3 | 18 | `battery_components` 60 + `battery_materials` 60 + `power_electronics` 60 | No | No | — |
| `grid_storage_system` | Grid Storage System | `recipe.assembler.grid_storage_system` | Assembler | 3 | 18 | `power_electronics` 60 + `storage_components` 60 | No | No | — |
| `heavy_machinery` | Heavy Machinery | `recipe.assembler.heavy_machinery` | Assembler | 3 | 18 | `control_electronics` 60 + `hydraulic_components` 60 + `structural_components` 60 | No | No | — |
| `heavy_mining_drill` | Heavy Mining Drill | `recipe.assembler.heavy_mining_drill` | Assembler | 3 | 22 | `control_electronics` 60 + `hydraulic_components` 60 + `mining_components` 60 | No | No | — |
| `high_speed_network_system` | High-Speed Network System | `recipe.assembler.high_speed_network_system` | Assembler | 3 | 18 | `control_electronics` 60 + `network_components` 60 | No | No | — |
| `high_speed_train` | High-Speed Train | `recipe.assembler.high_speed_train` | Assembler | 3 | 22 | `aerospace_components` 60 + `power_electronics` 60 + `rail_components` 60 | No | No | — |
| `high_speed_vessel` | High-Speed Vessel | `recipe.assembler.high_speed_vessel` | Assembler | 3 | 22 | `composite_components` 60 + `marine_components` 60 + `turbine_components` 60 | No | No | — |
| `high_voltage_equipment` | High-Voltage Equipment | `recipe.assembler.high_voltage_equipment` | Assembler | 3 | 18 | `insulation_material` 60 + `power_electronics` 60 + `transformer_components` 60 | No | No | — |
| `hydraulic_system` | Hydraulic System | `recipe.assembler.hydraulic_system` | Assembler | 3 | 5 | `hydraulic_components` 60 + `steel_components` 60 | No | No | — |
| `hydrogen_electrolyzer` | Hydrogen Electrolyzer | `recipe.assembler.hydrogen_electrolyzer` | Assembler | 3 | 18 | `electrolyzer_components` 60 + `power_electronics` 60 | No | No | — |
| `industrial_chemicals` | Industrial Chemicals | `recipe.assembler.industrial_chemicals` | Assembler | 3 | 7 | `chemical_components` 60 + `gas_handling_components` 60 | No | No | — |
| `industrial_clothing` | Industrial Clothing | `recipe.assembler.industrial_clothing` | Assembler | 3 | 7 | `industrial_fabric` 60 + `technical_textile` 60 | No | No | — |
| `industrial_compressor` | Industrial Compressor | `recipe.assembler.industrial_compressor` | Assembler | 3 | 15 | `compressor_components` 60 + `motor_components` 60 | No | No | — |
| `industrial_computer` | Industrial Computer | `recipe.assembler.industrial_computer` | Assembler | 3 | 18 | `computing_components` 60 + `display_components` 60 | No | No | — |
| `industrial_controller` | Industrial Controller | `recipe.assembler.industrial_controller` | Assembler | 3 | 18 | `control_electronics` 60 + `sensor_components` 60 | No | No | — |
| `industrial_crusher` | Industrial Crusher | `recipe.assembler.industrial_crusher` | Assembler | 3 | 22 | `gear_components` 60 + `mining_components` 60 | No | No | — |
| `industrial_cutting_machine` | Industrial Cutting Machine | `recipe.assembler.industrial_cutting_machine` | Assembler | 3 | 22 | `control_electronics` 60 + `cutting_tooling` 60 + `precision_components` 60 | No | No | — |
| `industrial_display` | Industrial Display | `recipe.assembler.industrial_display` | Assembler | 3 | 18 | `control_electronics` 60 + `glass_panels` 60 | No | No | — |
| `industrial_drone` | Industrial Drone | `recipe.assembler.industrial_drone` | Assembler | 3 | 22 | `aerospace_components` 60 + `battery_components` 60 + `sensor_components` 60 | No | No | — |
| `industrial_equipment` | Industrial Equipment | `recipe.assembler.industrial_equipment` | Assembler | 3 | 9 | `electrical_components` 60 + `iron_components` 60 + `steel_components` 60 | No | No | — |
| `industrial_generator` | Industrial Generator | `recipe.assembler.industrial_generator` | Assembler | 3 | 22 | `motor_components` 60 + `turbine_components` 60 | No | No | — |
| `industrial_glass_panels` | Industrial Glass Panels | `recipe.assembler.industrial_glass_panels` | Assembler | 3 | 13 | `aluminum_components` 60 + `glass_panels` 60 | No | No | — |
| `industrial_hall_modules` | Industrial Hall Modules | `recipe.assembler.industrial_hall_modules` | Assembler | 3 | 13 | `galvanized_components` 60 + `glass_panels` 60 + `insulation_material` 60 + `structural_components` 60 | No | No | — |
| `industrial_insulation` | Industrial Insulation | `recipe.assembler.industrial_insulation` | Assembler | 3 | 5 | `fiber_components` 60 + `insulation_material` 60 | No | No | — |
| `industrial_inverter` | Industrial Inverter | `recipe.assembler.industrial_inverter` | Assembler | 3 | 18 | `control_electronics` 60 + `power_electronics` 60 | No | No | — |
| `industrial_laser` | Industrial Laser | `recipe.assembler.industrial_laser` | Assembler | 3 | 22 | `magnetic_components` 60 + `precision_components` 60 + `semiconductor_components` 60 | No | No | — |
| `industrial_packaging` | Industrial Packaging | `recipe.assembler.industrial_packaging` | Assembler | 3 | 5 | `packaging_components` 60 + `wooden_components` 60 | No | No | — |
| `industrial_plastics` | Industrial Plastics | `recipe.assembler.industrial_plastics` | Assembler | 3 | 13 | `composite_components` 60 + `packaging_components` 60 | No | No | — |
| `industrial_pump` | Industrial Pump | `recipe.assembler.industrial_pump` | Assembler | 3 | 15 | `motor_components` 60 + `pump_components` 60 | No | No | — |
| `industrial_relay` | Industrial Relay | `recipe.assembler.industrial_relay` | Assembler | 3 | 18 | `control_electronics` 60 + `electrical_components` 60 | No | No | — |
| `industrial_robot` | Industrial Robot | `recipe.assembler.industrial_robot` | Assembler | 3 | 22 | `control_electronics` 60 + `motor_components` 60 + `precision_components` 60 + `sensor_components` 60 | No | No | — |
| `industrial_rubber_products` | Industrial Rubber Products | `recipe.assembler.industrial_rubber_products` | Assembler | 3 | 13 | `chemical_components` 60 + `rubber_blend_components` 60 + `tire_components` 60 | No | No | — |
| `industrial_seals` | Industrial Seals | `recipe.assembler.industrial_seals` | Assembler | 3 | 22 | `precision_components` 60 + `tire_components` 60 | No | No | — |
| `industrial_sensor` | Industrial Sensor | `recipe.assembler.industrial_sensor` | Assembler | 3 | 18 | `control_electronics` 60 + `sensor_components` 60 | No | No | — |
| `industrial_tires` | Industrial Tires | `recipe.assembler.industrial_tires` | Assembler | 3 | 13 | `tire_components` 60 | No | No | — |
| `jet_engine` | Jet Engine | `recipe.assembler.jet_engine` | Assembler | 3 | 22 | `turbine_components` 60 | No | No | — |
| `laboratory_equipment` | Laboratory Equipment | `recipe.assembler.laboratory_equipment` | Assembler | 3 | 22 | `control_electronics` 60 + `glass_panels` 60 + `precision_components` 60 | No | No | — |
| `launch_vehicle` | Launch Vehicle | `recipe.assembler.launch_vehicle` | Assembler | 3 | 22 | `aerospace_components` 60 + `control_electronics` 60 + `turbine_components` 60 | No | No | — |
| `light_aircraft` | Light Aircraft | `recipe.assembler.light_aircraft` | Assembler | 3 | 22 | `aerospace_components` 60 + `avionics_components` 60 | No | No | — |
| `machine_vision_system` | Machine Vision System | `recipe.assembler.machine_vision_system` | Assembler | 3 | 18 | `computing_components` 60 + `sensor_components` 60 | No | No | — |
| `medical_monitor` | Medical Monitor | `recipe.assembler.medical_monitor` | Assembler | 3 | 20 | `display_components` 60 + `medical_components` 60 + `sensor_components` 60 | No | No | — |
| `memory_module` | Memory Module | `recipe.assembler.memory_module` | Assembler | 3 | 18 | `control_electronics` 60 + `memory_components` 60 | No | No | — |
| `microchip` | Microchip | `recipe.assembler.microchip` | Assembler | 3 | 18 | `semiconductor_components` 60 + `semiconductor_die` 60 | No | No | — |
| `microcontroller` | Microcontroller | `recipe.assembler.microcontroller` | Assembler | 3 | 18 | `control_electronics` 60 + `semiconductor_die` 60 | No | No | — |
| `mining_drill` | Mining Drill | `recipe.assembler.mining_drill` | Assembler | 3 | 22 | `mining_components` 60 + `motor_components` 60 + `steel_components` 60 | No | No | — |
| `mining_equipment` | Mining Equipment | `recipe.assembler.mining_equipment` | Assembler | 3 | 22 | `mining_components` 60 + `steel_components` 60 | No | No | — |
| `navigation_satellite` | Navigation Satellite | `recipe.assembler.navigation_satellite` | Assembler | 3 | 22 | `aerospace_components` 60 + `sensor_components` 60 + `telecom_components` 60 | No | No | — |
| `network_switch` | Network Switch | `recipe.assembler.network_switch` | Assembler | 3 | 18 | `control_electronics` 60 + `network_components` 60 | No | No | — |
| `nuclear_fuel_assembly` | Nuclear Fuel Assembly | `recipe.assembler.nuclear_fuel_assembly` | Assembler | 3 | 25 | `nuclear_fuel_components` 60 + `shielding_components` 60 | No | No | — |
| `nuclear_reactor` | Nuclear Reactor | `recipe.assembler.nuclear_reactor` | Assembler | 3 | 25 | `control_electronics` 60 + `nuclear_fuel_components` 60 + `reactor_components` 60 + `structural_components` 60 | No | No | — |
| `orbital_vehicle` | Orbital Vehicle | `recipe.assembler.orbital_vehicle` | Assembler | 3 | 22 | `aerospace_components` 60 + `avionics_components` 60 + `control_electronics` 60 | No | No | — |
| `packaged_beverages` | Packaged Beverages | `recipe.assembler.packaged_beverages` | Assembler | 3 | 5 | `nutrition_components` 60 + `packaging_components` 60 | No | No | — |
| `packaged_food` | Packaged Food | `recipe.assembler.packaged_food` | Assembler | 3 | 5 | `food_ingredients` 60 + `packaging_components` 60 + `sweetener_components` 60 | No | No | — |
| `packaged_meals` | Packaged Meals | `recipe.assembler.packaged_meals` | Assembler | 3 | 5 | `food_ingredients` 60 + `nutrition_components` 60 + `packaging_components` 60 | No | No | — |
| `packaged_nutrition` | Packaged Nutrition | `recipe.assembler.packaged_nutrition` | Assembler | 3 | 5 | `nutrition_components` 60 + `packaging_components` 60 | No | No | — |
| `packaging_materials` | Packaging Materials | `recipe.assembler.packaging_materials` | Assembler | 3 | 5 | `packaging_components` 60 | No | No | — |
| `power_cable` | Power Cable | `recipe.assembler.power_cable` | Assembler | 3 | 5 | `aluminum_components` 60 + `insulated_wire` 60 | No | No | — |
| `precision_motor` | Precision Motor | `recipe.assembler.precision_motor` | Assembler | 3 | 22 | `magnetic_components` 60 + `motor_components` 60 + `precision_components` 60 | No | No | — |
| `prefabricated_structures` | Prefabricated Structures | `recipe.assembler.prefabricated_structures` | Assembler | 3 | 5 | `concrete_components` 60 + `structural_components` 60 + `wooden_components` 60 | No | No | — |
| `premium_electric_vehicle` | Premium Electric Vehicle | `recipe.assembler.premium_electric_vehicle` | Assembler | 3 | 15 | `advanced_cell_components` 60 + `display_components` 60 + `vehicle_components` 60 | No | No | — |
| `processed_food` | Processed Food | `recipe.assembler.processed_food` | Assembler | 3 | 4 | `food_ingredients` 60 + `nutrition_components` 60 | No | No | — |
| `processing_equipment` | Processing Equipment | `recipe.assembler.processing_equipment` | Assembler | 3 | 18 | `control_electronics` 60 + `pump_components` 60 + `steel_components` 60 | No | No | — |
| `protective_clothing` | Protective Clothing | `recipe.assembler.protective_clothing` | Assembler | 3 | 13 | `industrial_fabric` 60 + `tire_components` 60 | No | No | — |
| `protective_packaging` | Protective Packaging | `recipe.assembler.protective_packaging` | Assembler | 3 | 5 | `insulation_material` 60 + `packaging_components` 60 | No | No | — |
| `quantum_computing_module` | Quantum Computing Module | `recipe.assembler.quantum_computing_module` | Assembler | 3 | 22 | `control_electronics` 60 + `processor_components` 60 + `refractory_alloy_components` 60 | No | No | — |
| `radio_transceiver` | Radio Transceiver | `recipe.assembler.radio_transceiver` | Assembler | 3 | 18 | `magnetic_components` 60 + `telecom_components` 60 | No | No | — |
| `railway_track` | Railway Track | `recipe.assembler.railway_track` | Assembler | 3 | 9 | `rail_components` 60 + `steel_components` 60 | No | No | — |
| `reinforced_concrete` | Reinforced Concrete | `recipe.assembler.reinforced_concrete` | Assembler | 3 | 3 | `concrete_components` 60 + `steel_components` 60 | No | No | — |
| `robotic_actuator` | Robotic Actuator | `recipe.assembler.robotic_actuator` | Assembler | 3 | 22 | `motor_components` 60 + `precision_components` 60 | No | No | — |
| `robotic_arm` | Robotic Arm | `recipe.assembler.robotic_arm` | Assembler | 3 | 22 | `control_electronics` 60 + `motor_components` 60 + `precision_components` 60 | No | No | — |
| `rocket_engine` | Rocket Engine | `recipe.assembler.rocket_engine` | Assembler | 3 | 22 | `titanium_components` 60 + `turbine_components` 60 | No | No | — |
| `router` | Router | `recipe.assembler.router` | Assembler | 3 | 18 | `network_components` 60 + `telecom_components` 60 | No | No | — |
| `safety_equipment` | Safety Equipment | `recipe.assembler.safety_equipment` | Assembler | 3 | 13 | `glass_panels` 60 + `industrial_fabric` 60 + `tire_components` 60 | No | No | — |
| `satellite` | Satellite | `recipe.assembler.satellite` | Assembler | 3 | 22 | `aerospace_components` 60 + `solar_components` 60 + `telecom_components` 60 | No | No | — |
| `semiconductor_equipment` | Semiconductor Equipment | `recipe.assembler.semiconductor_equipment` | Assembler | 3 | 22 | `ceramic_components` 60 + `control_electronics` 60 + `precision_components` 60 | No | No | — |
| `server` | Server | `recipe.assembler.server` | Assembler | 3 | 18 | `computing_components` 60 + `memory_components` 60 | No | No | — |
| `server_rack` | Server Rack | `recipe.assembler.server_rack` | Assembler | 3 | 18 | `network_components` 60 + `server_components` 60 + `structural_components` 60 | No | No | — |
| `servo_motor` | Servo Motor | `recipe.assembler.servo_motor` | Assembler | 3 | 22 | `control_electronics` 60 + `motor_components` 60 + `precision_components` 60 | No | No | — |
| `soft_drinks` | Soft Drinks | `recipe.assembler.soft_drinks` | Assembler | 3 | 5 | `nutrition_components` 60 + `packaging_components` 60 | No | No | — |
| `solar_array` | Solar Array | `recipe.assembler.solar_array` | Assembler | 3 | 18 | `power_electronics` 60 + `solar_components` 60 | No | No | — |
| `steam_turbine` | Steam Turbine | `recipe.assembler.steam_turbine` | Assembler | 3 | 22 | `stainless_components` 60 + `turbine_components` 60 | No | No | — |
| `structural_systems` | Structural Systems | `recipe.assembler.structural_systems` | Assembler | 3 | 3 | `concrete_components` 60 + `structural_components` 60 | No | No | — |
| `supercomputer` | Supercomputer | `recipe.assembler.supercomputer` | Assembler | 3 | 22 | `ai_compute_components` 60 + `grid_storage_components` 60 + `network_components` 60 + `server_components` 60 | No | No | — |
| `superconducting_magnet_system` | Superconducting Magnet System | `recipe.assembler.superconducting_magnet_system` | Assembler | 3 | 22 | `power_electronics` 60 + `refractory_alloy_components` 60 | No | No | — |
| `surgical_equipment` | Surgical Equipment | `recipe.assembler.surgical_equipment` | Assembler | 3 | 22 | `precision_components` 60 + `stainless_components` 60 | No | No | — |
| `sustainable_packaging` | Sustainable Packaging | `recipe.assembler.sustainable_packaging` | Assembler | 3 | 5 | `bio_composite` 60 + `packaging_components` 60 | No | No | — |
| `switchgear` | Switchgear | `recipe.assembler.switchgear` | Assembler | 3 | 18 | `control_electronics` 60 + `electrical_components` 60 | No | No | — |
| `synthetic_fuel_plant` | Synthetic Fuel Plant | `recipe.assembler.synthetic_fuel_plant` | Assembler | 3 | 20 | `catalyst_components` 60 + `chemical_components` 60 + `electrolyzer_components` 60 | No | No | — |
| `tanker` | Tanker | `recipe.assembler.tanker` | Assembler | 3 | 11 | `corrosion_resistant_components` 60 + `marine_components` 60 + `pump_components` 60 | No | No | — |
| `transformer` | Transformer | `recipe.assembler.transformer` | Assembler | 3 | 9 | `electrical_components` 60 + `transformer_components` 60 | No | No | — |
| `utility_vehicle` | Utility Vehicle | `recipe.assembler.utility_vehicle` | Assembler | 3 | 18 | `control_electronics` 60 + `sensor_components` 60 + `vehicle_components` 60 | No | No | — |
| `wind_turbine` | Wind Turbine | `recipe.assembler.wind_turbine` | Assembler | 3 | 22 | `power_electronics` 60 + `structural_components` 60 + `wind_components` 60 | No | No | — |
| `workboat` | Workboat | `recipe.assembler.workboat` | Assembler | 3 | 22 | `marine_components` 60 + `turbine_components` 60 | No | No | — |
| `workwear` | Workwear | `recipe.assembler.workwear` | Assembler | 3 | 7 | `industrial_fabric` 60 + `technical_textile` 60 | No | No | — |
