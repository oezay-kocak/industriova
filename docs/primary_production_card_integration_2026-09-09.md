# Primary-production card integration — 2026-09-09

## Status

The runtime/data/UI integration and the Harvester fallback fix are complete. The user-designated final `Harvester.png` was installed byte-for-byte, all primary machine families now resolve to explicit assets, and automated tests pass. Offscreen captures confirm the combine-harvester artwork is rendered rather than Extractor. The supplied file is nevertheless RGB-only and its baked checkerboard remains visibly present inside the card.

## Canonical definitions and artwork

| Family | Definition ID | Player-visible name | Production targets | Artwork |
|---|---|---|---:|---|
| Mining | `machine.extractor` | EXTRACTOR | 37 | existing `src/production_zero/assets/machines/extractor.png` |
| Drilling | `machine.drilling` | DRILLING RIG | 2 | `src/production_zero/assets/machines/drilling_rig.png` |
| Agriculture/Forestry | `machine.agriculture` | HARVESTER | 10 | `src/production_zero/assets/machines/agriculture.png` |

The Drilling PNG was copied byte-for-byte from `<USER_HOME>\Downloads\Drilling.png`; source and target SHA-256 are both `D52E3F71F513863B4E11CB8D939512F8D158789FA40333F11DCBD76AEA2FC578`. It is 1402×1122 RGBA with transparent corner pixels. Its temporary Extractor fallback has been removed.

The Harvester PNG was copied byte-for-byte from `<USER_HOME>\Downloads\Harvester.png`; source and target SHA-256 are both `BD7C312F4BE7E1D39E30DAF661D833827842A5290B704DCCB63203B561C2E3`. It is 1536×1024 RGB32 with no alpha channel. The Agriculture fallback was removed, leaving an empty fallback map for the three primary families.

## Terminology and membership

The chosen generic label is **PRIMARY PRODUCTION**. It fits the existing horizontally scrollable compact filter surfaces without changing card or surrounding layout dimensions.

- Inventory uses one Primary Production type filter for exactly Extractor, Drilling Rig, and Harvester.
- The Production Guide uses Primary Production as the shared first-stage filter and chain heading while retaining each node's specific machine-family label.
- The specialized pack category is now Primary Production and its existing internal `extraction` category ID draws from exactly the three primary families.
- Resources card selection retains individual EXTRACTOR, DRILLING RIG, and HARVESTER filters.
- Specific Extractor names, IDs, enum values, art/accent keys, progression compatibility keys, starter cards, and legacy migration mappings remain unchanged.
- The batched unlock feed now says `primary-production resources` rather than using Extractor as an umbrella.

## Systems audited

- Runtime definitions and 37/2/10 target partition
- family-specific selection and cross-family command validation
- Resources board allow-list and installed-card exclusion
- Inventory rows, stacks, rarity variants, crafting, recycling, and filters
- general and specialized pack pools and rarity probabilities
- Industrial Supply machine enumeration and card presentation
- starter inventory (unchanged: existing Extractor cards retained; no free Drilling Rig/Harvester cards added)
- developer card creation options
- save/load definition IDs, legacy normalization, and split-board migration
- Production Guide indexing, ordering, filtering, and chain presentation

No recipe, quantity, rate, cycle, unlock, rarity probability, capacity, or economy value changed.

## Files changed by this focused pass

- `src/production_zero/assets/machines/drilling_rig.png`
- `src/production_zero/assets/machines/agriculture.png`
- `src/production_zero/data/definitions.py`
- `src/production_zero/core/packs.py`
- `src/production_zero/core/production_guide.py`
- `src/production_zero/ui/dev_tools_view.py`
- `src/production_zero/ui/event_feed.py`
- `src/production_zero/ui/factory_view.py`
- `src/production_zero/ui/inventory_view.py`
- `src/production_zero/ui/machine_art.py`
- `src/production_zero/ui/packs_view.py`
- `src/production_zero/ui/supply_view.py`
- `tests/test_card_definitions.py`
- `tests/test_factory_ui.py`
- `tests/test_packs.py`
- `tests/test_primary_production_cards.py`
- `tests/test_secondary_modernization.py`
- `docs/resource_factory_energy_split_implementation_2026-09-09.md`
- `docs/primary_production_card_integration_2026-09-09.md`
- `scripts/capture_harvester_card.py`

## Validation

- `compileall`: passed after the final changes.
- Focused Harvester/machine-art/card run: 77 passed in 13.51 seconds.
- Focused definition/pack/board/persistence/compact-control run: 66 passed.
- Focused post-Inventory-filter run: 55 passed.
- Full suite after the Inventory grouping: 733 passed in 904.13 seconds.
- Final event-feed terminology check: 17 passed.
- Final full suite after the Harvester asset/fallback change: 735 passed in 648.48 seconds.
- Offscreen captures:
  - `artifacts/harvester_card/harvester_inventory_compact_1366x768.png`
  - `artifacts/harvester_card/harvester_inventory_desktop_1920x1080.png`

## Remaining source-art issue

The fallback problem is resolved. However, visual inspection shows a pale checkerboard rectangle around the Harvester because the supplied final PNG contains that checkerboard as opaque RGB pixels. It was deliberately not altered during this asset-only integration. A genuinely transparent replacement would still be needed to satisfy a transparent-background visual standard.
