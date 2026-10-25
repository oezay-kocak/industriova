# Resource Raster Asset Batch 01

Date: 2026-09-07

## Scope and source

This pass migrates exactly eight resource IDs to raster artwork. The source is
`<USER_HOME>\Downloads\ChatGPT Image 7. Sept. 2026, 23_09_40.png`.
The source is an RGB batch image, so the extraction creates only the alpha mask;
it does not synthesize, redraw, recolor, or geometrically alter the supplied RGB
artwork.

No pre-existing `copper_ore.png` was present in the repository. Copper Ore was
therefore extracted from the supplied batch and is the reference treatment for
the other seven assets.

## Mapping

| Resource ID | Final asset |
| --- | --- |
| `copper_ore` | `src/production_zero/assets/resources/copper_ore.png` |
| `iron_ore` | `src/production_zero/assets/resources/iron_ore.png` |
| `coal` | `src/production_zero/assets/resources/coal.png` |
| `quartz` | `src/production_zero/assets/resources/quartz.png` |
| `wheat` | `src/production_zero/assets/resources/wheat.png` |
| `crude_oil` | `src/production_zero/assets/resources/crude_oil.png` |
| `bauxite` | `src/production_zero/assets/resources/bauxite.png` |
| `sulfur` | `src/production_zero/assets/resources/sulfur.png` |

The canonical mapping is `RESOURCE_RASTER_ASSETS` in
`src/production_zero/ui/resource_art.py`. `ResourceIconWidget` queries this
mapping before its existing programmatic renderer. Resources outside this table
continue to use the unchanged fallback renderer. This routes Factory Resource
Selection, Production Guide, Inventory, Chain Inspector, Used In, Freight Cargo
Selection, tooltips, and detail views through the same asset instance.

Rendering uses `KeepAspectRatio`, `SmoothTransformation`, and
`SmoothPixmapTransform`. Every output is a 512 × 512 RGBA PNG with the artwork
fitted to a maximum 430 × 430 area on a transparent canvas.

## Alpha and clipping QA

All four canvas corners have alpha 0. Every asset contains both alpha 0 and
alpha 255 plus a short antialiased transition. The nontransparent bounds are:

| Resource ID | Alpha bounds `(left, top, right, bottom)` |
| --- | --- |
| `bauxite` | `(47, 149, 464, 362)` |
| `coal` | `(76, 145, 436, 367)` |
| `copper_ore` | `(43, 135, 469, 377)` |
| `crude_oil` | `(102, 134, 409, 377)` |
| `iron_ore` | `(71, 136, 440, 375)` |
| `quartz` | `(89, 133, 422, 378)` |
| `sulfur` | `(81, 146, 431, 366)` |
| `wheat` | `(111, 131, 400, 380)` |

These bounds leave at least 36 transparent pixels on every canvas edge. Visual
inspection on dark and light backgrounds confirmed no source labels, background
panels, glow fields, stretching, or newly clipped artwork. Small detached pieces
belonging to the ore piles remain present.

## Changed files

- Eight PNGs under `src/production_zero/assets/resources/`
- `src/production_zero/ui/resource_art.py`
- `src/production_zero/ui/resource_icons.py`
- `src/production_zero/tools/extract_resource_batch_01.py`
- `src/production_zero/tools/resource_asset_batch_01_qa.py`
- `tests/test_resource_raster_assets.py`
- This report

No resource definitions, names, categories, production values, gameplay data,
or progression values were changed in this pass.

## Tests and offscreen artifacts

Focused raster, canonical icon, and Factory UI suite:

`212 passed`

Additional Inventory, Freight, Production Guide, and secondary-view regression
suite:

`71 passed`

Market, Supply, Contracts, Packs, Charts, and resource-economy consumer suite:

`95 passed`

Offscreen artifacts:

- `artifacts/resource-assets/batch-01/contact_sheet_dark_light_and_ui_size.png`
- `artifacts/resource-assets/batch-01/production_guide_resource_browser.png`

The real GUI was not launched. The Production Guide was instantiated only with
Qt's offscreen platform and captured directly to an image.
