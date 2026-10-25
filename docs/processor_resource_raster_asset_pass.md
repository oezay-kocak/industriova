# Processor Resource Raster Asset Pass

Date: 2026-09-08

## Scope and validation

This pass maps the 68 supplied PNG files to entries 050–117 in the Google Drive document **Production Zero — Resource & Product Master List (353)** and to the 68 active resources whose `stage` is `processor` in `resource_progression.json`. The mapping was validated as a complete bijection before any target file was written: 68 source files, 68 Processor definitions, 68 unique matches, no unknown file, no duplicate, and no missing resource. All Processor status markers in the master list were already complete, so the Google document required no update.

The only filename alias is `aluminium.png` → `aluminum`, matching master-list entry 054 and the active game ID. Gameplay, progression, recipes, unlocks, balance, contracts, saves, and freight data were not changed.

## Complete mapping

| Source file | Ingame name | Resource ID |
| --- | --- | --- |
| `<USER_HOME>\Desktop\PZ R\2\aluminium.png` | Aluminum | `aluminum` |
| `<USER_HOME>\Desktop\PZ R\2\ammonia.png` | Ammonia | `ammonia` |
| `<USER_HOME>\Desktop\PZ R\2\bio lubricant.png` | Bio-Lubricant | `bio_lubricant` |
| `<USER_HOME>\Desktop\PZ R\2\bitumen.png` | Bitumen | `bitumen` |
| `<USER_HOME>\Desktop\PZ R\2\carbon fiber.png` | Carbon Fiber | `carbon_fiber` |
| `<USER_HOME>\Desktop\PZ R\2\catalyst metal.png` | Catalyst Metal | `catalyst_metal` |
| `<USER_HOME>\Desktop\PZ R\2\cellulose.png` | Cellulose | `cellulose` |
| `<USER_HOME>\Desktop\PZ R\2\cement.png` | Cement | `cement` |
| `<USER_HOME>\Desktop\PZ R\2\ceramics.png` | Ceramics | `ceramics` |
| `<USER_HOME>\Desktop\PZ R\2\chemical feedstock.png` | Chemical Feedstock | `chemical_feedstock` |
| `<USER_HOME>\Desktop\PZ R\2\chlorine.png` | Chlorine | `chlorine` |
| `<USER_HOME>\Desktop\PZ R\2\chromium.png` | Chromium | `chromium` |
| `<USER_HOME>\Desktop\PZ R\2\cobalt.png` | Cobalt | `cobalt` |
| `<USER_HOME>\Desktop\PZ R\2\copper.png` | Copper | `copper` |
| `<USER_HOME>\Desktop\PZ R\2\corn meal.png` | Corn Meal | `corn_meal` |
| `<USER_HOME>\Desktop\PZ R\2\cotton fiber.png` | Cotton Fiber | `cotton_fiber` |
| `<USER_HOME>\Desktop\PZ R\2\fermentation feedstock.png` | Fermentation Feedstock | `fermentation_feedstock` |
| `<USER_HOME>\Desktop\PZ R\2\flour.png` | Flour | `flour` |
| `<USER_HOME>\Desktop\PZ R\2\fruit concentrate.png` | Fruit Concentrate | `fruit_concentrate` |
| `<USER_HOME>\Desktop\PZ R\2\galvanized metal.png` | Galvanized Metal | `galvanized_metal` |
| `<USER_HOME>\Desktop\PZ R\2\glass.png` | Glass | `glass` |
| `<USER_HOME>\Desktop\PZ R\2\gold.png` | Gold | `gold` |
| `<USER_HOME>\Desktop\PZ R\2\high purity silicon.png` | High-Purity Silicon | `high_purity_silicon` |
| `<USER_HOME>\Desktop\PZ R\2\hydrogen.png` | Hydrogen | `hydrogen` |
| `<USER_HOME>\Desktop\PZ R\2\industrial gas.png` | Industrial Gas | `industrial_gas` |
| `<USER_HOME>\Desktop\PZ R\2\industrial resin.png` | Industrial Resin | `industrial_resin` |
| `<USER_HOME>\Desktop\PZ R\2\iron.png` | Iron | `iron` |
| `<USER_HOME>\Desktop\PZ R\2\lead.png` | Lead | `lead` |
| `<USER_HOME>\Desktop\PZ R\2\lithium.png` | Lithium | `lithium` |
| `<USER_HOME>\Desktop\PZ R\2\lumber.png` | Lumber | `lumber` |
| `<USER_HOME>\Desktop\PZ R\2\manganese.png` | Manganese | `manganese` |
| `<USER_HOME>\Desktop\PZ R\2\molybdenum.png` | Molybdenum | `molybdenum` |
| `<USER_HOME>\Desktop\PZ R\2\nickel.png` | Nickel | `nickel` |
| `<USER_HOME>\Desktop\PZ R\2\nickel alloy.png` | Nickel Alloy | `nickel_alloy` |
| `<USER_HOME>\Desktop\PZ R\2\niobium.png` | Niobium | `niobium` |
| `<USER_HOME>\Desktop\PZ R\2\nuclear material.png` | Nuclear Material | `nuclear_material` |
| `<USER_HOME>\Desktop\PZ R\2\organic feedstock.png` | Organic Feedstock | `organic_feedstock` |
| `<USER_HOME>\Desktop\PZ R\2\palladium.png` | Palladium | `palladium` |
| `<USER_HOME>\Desktop\PZ R\2\phosphoric acid.png` | Phosphoric Acid | `phosphoric_acid` |
| `<USER_HOME>\Desktop\PZ R\2\platinum.png` | Platinum | `platinum` |
| `<USER_HOME>\Desktop\PZ R\2\polymer.png` | Polymer | `polymer` |
| `<USER_HOME>\Desktop\PZ R\2\potassium compound.png` | Potassium Compound | `potassium_compound` |
| `<USER_HOME>\Desktop\PZ R\2\processed gypsum.png` | Processed Gypsum | `processed_gypsum` |
| `<USER_HOME>\Desktop\PZ R\2\processed rubber.png` | Processed Rubber | `processed_rubber` |
| `<USER_HOME>\Desktop\PZ R\2\purified graphite.png` | Purified Graphite | `purified_graphite` |
| `<USER_HOME>\Desktop\PZ R\2\rare earth metals.png` | Rare Earth Metals | `rare_earth_metals` |
| `<USER_HOME>\Desktop\PZ R\2\raw sugar.png` | Raw Sugar | `raw_sugar` |
| `<USER_HOME>\Desktop\PZ R\2\refined sugar.png` | Refined Sugar | `refined_sugar` |
| `<USER_HOME>\Desktop\PZ R\2\shielding material.png` | Shielding Material | `shielding_material` |
| `<USER_HOME>\Desktop\PZ R\2\silicon.png` | Silicon | `silicon` |
| `<USER_HOME>\Desktop\PZ R\2\silver.png` | Silver | `silver` |
| `<USER_HOME>\Desktop\PZ R\2\soy_oil.png` | Soy Oil | `soy_oil` |
| `<USER_HOME>\Desktop\PZ R\2\soy protein.png` | Soy Protein | `soy_protein` |
| `<USER_HOME>\Desktop\PZ R\2\stainless steel.png` | Stainless Steel | `stainless_steel` |
| `<USER_HOME>\Desktop\PZ R\2\starch.png` | Starch | `starch` |
| `<USER_HOME>\Desktop\PZ R\2\steel.png` | Steel | `steel` |
| `<USER_HOME>\Desktop\PZ R\2\sulfuric acid.png` | Sulfuric Acid | `sulfuric_acid` |
| `<USER_HOME>\Desktop\PZ R\2\superconducting alloy.png` | Superconducting Alloy | `superconducting_alloy` |
| `<USER_HOME>\Desktop\PZ R\2\synthetic rubber.png` | Synthetic Rubber | `synthetic_rubber` |
| `<USER_HOME>\Desktop\PZ R\2\tin.png` | Tin | `tin` |
| `<USER_HOME>\Desktop\PZ R\2\titanium.png` | Titanium | `titanium` |
| `<USER_HOME>\Desktop\PZ R\2\treated lumber.png` | Treated Lumber | `treated_lumber` |
| `<USER_HOME>\Desktop\PZ R\2\tungsten.png` | Tungsten | `tungsten` |
| `<USER_HOME>\Desktop\PZ R\2\vanadium.png` | Vanadium | `vanadium` |
| `<USER_HOME>\Desktop\PZ R\2\vanadium alloy.png` | Vanadium Alloy | `vanadium_alloy` |
| `<USER_HOME>\Desktop\PZ R\2\vegetable oil.png` | Vegetable Oil | `vegetable_oil` |
| `<USER_HOME>\Desktop\PZ R\2\wood pulp.png` | Wood Pulp | `wood_pulp` |
| `<USER_HOME>\Desktop\PZ R\2\zinc.png` | Zinc | `zinc` |

## Assets and rendering

All target files are stored as `src/production_zero/assets/resources/<resource_id>.png`. Each output is a 512 × 512 RGBA PNG. Artwork is resized proportionally into a maximum 440 × 440 area with Lanczos downsampling and centered on a transparent canvas, leaving at least 36 pixels of transparent padding on every edge.

`src/production_zero/ui/resource_art.py` remains the single ID-to-path registry. `ResourceIconWidget` resolves the 49 Extractor and 68 Processor rasters before its existing vector fallback, so Production Guide, Factory selection, Inventory, Charts, Chain Inspector, Used In, Freight selection, tooltips, and detail views all use the same assets. Aspect-preserving smooth rendering remains unchanged.

## Alpha corrections

50 sources already contained usable alpha and retained it. The 18 RGB or non-usable-alpha sources received a deterministic silhouette mask based on the supplied outer outline: `aluminum`, `chromium`, `cobalt`, `copper`, `gold`, `iron`, `lead`, `lithium`, `manganese`, `molybdenum`, `nickel`, `stainless_steel`, `steel`, `tin`, `titanium`, `tungsten`, `vanadium`, `zinc`. RGB artwork pixels were not redrawn, recolored, sharpened, or replaced. Visual inspection on alternating dark and light panels found no checkerboard remnants, background rectangles, clipping, or stretching.

## QA and artifacts

- `artifacts/resource-assets/processor-pass/processor_resource_assets.json` — machine-readable 68-row audit
- `artifacts/resource-assets/processor-pass/processor_icons_contact_sheet.png` — all 68 icons on alternating dark/light panels
- `artifacts/resource-assets/processor-pass/production_guide_1920x1080.png`
- `artifacts/resource-assets/processor-pass/production_guide_1366x768.png`
- `artifacts/resource-assets/processor-pass/factory_processor_resource_selection_1366x768.png`

## Changed files

- 68 Processor PNGs under `src/production_zero/assets/resources/`
- `src/production_zero/ui/resource_art.py`
- `src/production_zero/tools/integrate_processor_resource_assets.py`
- `src/production_zero/tools/processor_resource_asset_qa.py`
- `tests/test_resource_raster_assets.py`
- This report

## Verification

- Focused Resource/Factory/Guide/Charts/Inventory/Freight/Used-In suite:
  **301 passed**
- Full suite: **708 passed**
- `python -m compileall -q src tests`: **passed**
- `git diff --check`: **passed**
