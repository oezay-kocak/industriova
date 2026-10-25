# Extractor Resource Raster Asset Pass

Date: 2026-09-08

## Scope and validation

This pass maps the 49 supplied PNG files to the 49 active resources whose
`stage` is `extractor` in `resource_progression.json`. The mapping was validated
as a complete bijection before any target file was written: 49 source files,
49 Extractor definitions, 49 unique matches, no unknown file, no duplicate, and
no missing resource. The other 304 active resources retain the existing vector
fallback. No gameplay, progression, production, unlock, contract, save, or
freight data was changed.

Two filenames require explicit aliases grounded in the active definitions:
`phosphate.png` maps to `phosphate_rock`, and the supplied
`silicia sand.png` maps to `silica_sand`. `gold ore.png` is present and maps to
`gold_ore`.

## Complete mapping

| Source file | Ingame name | Resource ID |
| --- | --- | --- |
| `bauxite.png` | Bauxite | `bauxite` |
| `borate ore.png` | Borate Ore | `borate_ore` |
| `chromium ore.png` | Chromium Ore | `chromium_ore` |
| `clay.png` | Clay | `clay` |
| `coal.png` | Coal | `coal` |
| `cobalt ore.png` | Cobalt Ore | `cobalt_ore` |
| `copper ore.png` | Copper Ore | `copper_ore` |
| `corn.png` | Corn | `corn` |
| `cotton.png` | Cotton | `cotton` |
| `crude oil.png` | Crude Oil | `crude_oil` |
| `fluorspar.png` | Fluorspar | `fluorspar` |
| `fruit.png` | Fruit | `fruit` |
| `gold ore.png` | Gold Ore | `gold_ore` |
| `graphite.png` | Graphite | `graphite` |
| `gypsum.png` | Gypsum | `gypsum` |
| `iron ore.png` | Iron Ore | `iron_ore` |
| `kaolin.png` | Kaolin | `kaolin` |
| `lead ore.png` | Lead Ore | `lead_ore` |
| `limestone.png` | Limestone | `limestone` |
| `lithium ore.png` | Lithium Ore | `lithium_ore` |
| `magnesite.png` | Magnesite | `magnesite` |
| `manganese ore.png` | Manganese Ore | `manganese_ore` |
| `molybdenum ore.png` | Molybdenum Ore | `molybdenum_ore` |
| `natural gas.png` | Natural Gas | `natural_gas` |
| `natural rubber.png` | Natural Rubber | `natural_rubber` |
| `nickel ore.png` | Nickel Ore | `nickel_ore` |
| `niobium ore.png` | Niobium Ore | `niobium_ore` |
| `palladium ore.png` | Palladium Ore | `palladium_ore` |
| `phosphate.png` | Phosphate Rock | `phosphate_rock` |
| `platinum ore.png` | Platinum Ore | `platinum_ore` |
| `potash.png` | Potash | `potash` |
| `potatoes.png` | Potatoes | `potatoes` |
| `quartz.png` | Quartz | `quartz` |
| `rapeseed.png` | Rapeseed | `rapeseed` |
| `rare earth ore.png` | Rare Earth Ore | `rare_earth_ore` |
| `salt.png` | Salt | `salt` |
| `silicia sand.png` | Silica Sand | `silica_sand` |
| `silver ore.png` | Silver Ore | `silver_ore` |
| `soybeans.png` | Soybeans | `soybeans` |
| `sugarcane.png` | Sugarcane | `sugarcane` |
| `sulfur.png` | Sulfur | `sulfur` |
| `timber.png` | Timber | `timber` |
| `tin ore.png` | Tin Ore | `tin_ore` |
| `titanium ore.png` | Titanium Ore | `titanium_ore` |
| `tungsten ore.png` | Tungsten Ore | `tungsten_ore` |
| `uranium ore.png` | Uranium Ore | `uranium_ore` |
| `vanadium ore.png` | Vanadium Ore | `vanadium_ore` |
| `wheat.png` | Wheat | `wheat` |
| `zinc ore.png` | Zinc Ore | `zinc_ore` |

## Assets and rendering

All target files are stored as
`src/production_zero/assets/resources/<resource_id>.png`. Each file is a
512 × 512 RGBA PNG. The supplied artwork is fitted into a 440 × 440 maximum
area with Lanczos downsampling and centered on a transparent canvas; measured
transparent padding is at least 36 pixels on every edge.

`src/production_zero/ui/resource_art.py` is the canonical ID-to-path mapping.
`ResourceIconWidget` uses this mapping before its unchanged fallback renderer,
so Production Guide, Factory selection, Inventory, Charts, Chain Inspector,
Used In, Freight selection, tooltips, and detail views share the same assets.
Rendering continues to use `KeepAspectRatio`, `SmoothTransformation`, and
`SmoothPixmapTransform`.

## Alpha corrections

Six source files already contained usable alpha and retained it: `copper_ore`,
`cotton`, `fruit`, `gypsum`, `molybdenum_ore`, and `potatoes`. The remaining 43
RGB sources contained a real checkerboard, white, or black background. Their
background was removed with a deterministic silhouette mask based on the
supplied outline; RGB artwork pixels were not redrawn, recolored, sharpened, or
replaced. Visual inspection on alternating dark and light surfaces found no
checkerboard remnants, background rectangles, clipping, or stretching.

## QA and artifacts

The machine-readable report contains 49 successful entries with resource ID,
Ingame name, source file, target asset, dimensions, alpha status, alpha bounds,
correction status, and render status:

- `artifacts/resource-assets/extractor-pass/extractor_resource_assets.json`
- `artifacts/resource-assets/extractor-pass/extractor_icons_contact_sheet.png`
- `artifacts/resource-assets/extractor-pass/production_guide_1920x1080.png`
- `artifacts/resource-assets/extractor-pass/production_guide_1366x768.png`
- `artifacts/resource-assets/extractor-pass/factory_extractor_resource_selection_1366x768.png`

The contact sheet contains all 49 icons and the UI captures were produced with
Qt's offscreen platform. No real GUI was launched.

## Changed files

- 49 PNGs under `src/production_zero/assets/resources/`
- `src/production_zero/ui/resource_art.py`
- `src/production_zero/tools/integrate_extractor_resource_assets.py`
- `src/production_zero/tools/extractor_resource_asset_qa.py`
- `tests/test_resource_raster_assets.py`
- This report

## Verification

- Focused Resource/Factory/Guide/Charts/Inventory/Freight/Used-In suite:
  **301 passed**
- Full suite: **708 passed**
- `python -m compileall -q src tests`: **passed**
- `git diff --check`: **passed**
