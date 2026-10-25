# Resources / Factory / Energy Split Implementation

Date: 2026-09-09

## Outcome

Production is now presented as four operational areas in the locked order `Resources | Factory | Energy | Freight`. Resources, Factory, and Energy use one configurable Factory V2 board implementation. The split changes ownership and topology without changing production recipes, cycle times, outputs, energy values, market values, contracts, unlock thresholds, or Freight.

New-game usable capacity is intentionally 8 slots rather than 18: 1 Resources slot + 6 Factory slots + 1 Energy slot. This is the smallest topology that lets a player install one primary producer, retain the established Factory start, and install one generator.

## Board responsibilities and terminology

| Board | Allowed cards | Unit | Track | Purchase action | Production Guide | Production drawer |
|---|---|---|---|---|---|---|
| Resources | Extractor/Mining, Drilling/Rig, Agriculture | Site | `SECTOR 01` | Develop Site | No | Yes |
| Factory | Processor, Fabricator, Assembler | Hall | `LINE 01` | Build Hall | Yes | Yes |
| Energy | Energy definitions | Plant | `BLOCK 01` | Build Plant | No | No |

All three boards retain the Factory V2 chassis, navigation hierarchy, physical plates, card and slot dimensions, Build/Locked states, status treatment, typography, material language, selection interactions, and scrolling behavior.

## Capacity

| Board | Starting units | Initially unlocked tracks | Initial slots per unlocked track | Geometry per unit | Initial usable capacity | Maximum per unit |
|---|---:|---:|---:|---:|---:|---:|
| Resources | 1 Site | 1 Sector | 1 | 3 × 10 | 1 | 30 |
| Factory | 1 Hall | 2 Lines | 3 | 5 × 10 | 6 | 50 |
| Energy | 1 Plant | 1 Block | 1 | 3 × 5 | 1 | 15 |
| Combined new game | 3 units | — | — | — | 8 | 95 across the initial units |

Factory Hall purchasing remains functional and uncapped. Site and Plant purchasing use the same current purchase-cost progression; permanent unit caps and long-term gating remain deferred. The Factory reduction is exactly one removed Line per Hall (60 to 50 maximum slots, a 16.7% reduction) while preserving ten-position Lines and the original six-slot start.

## Shared architecture

`ProductionBoardConfig` in `src/production_zero/ui/factory_view.py` supplies the real variations required by the three boards: identity, unit/track labels, purchase label, allowed machine types, Energy allowance, Guide/drawer switches, and topology. `ProductionBoardViewV2` in `src/production_zero/ui/factory_view_v2.py` owns the shared V2 composition and interactions. `FactoryViewV2`, `ResourcesViewV2`, and `EnergyViewV2` are thin configured siblings, so Qt type lookup cannot mistake a Resources or Energy board for Factory.

The core topology remains represented by `FactoryHall` for save compatibility, but each unit records `board_kind` and its own `max_lines`, `max_slots_per_line`, `start_unlocked_lines`, and `start_slots_per_line`. `GameState.production_units()` and `GameState.all_production_units()` provide board-specific and aggregate traversal.

## Primary-resource classification

The loader retains the selectable-production-option model and partitions the former 49-target universal Extractor at runtime into three canonical definitions. No recipes or resource graph edges were duplicated or rebalanced.

| Family | Definition | Count | Targets |
|---|---|---:|---|
| Extractor / Mining | `machine.extractor` | 37 | iron ore, copper ore, bauxite, nickel ore, zinc ore, lead ore, tin ore, manganese ore, chromium ore, titanium ore, tungsten ore, cobalt ore, molybdenum ore, vanadium ore, silver ore, gold ore, platinum ore, palladium ore, lithium ore, uranium ore, rare-earth ore, niobium ore, coal, quartz, silica sand, limestone, gypsum, clay, kaolin, phosphate rock, potash, salt, sulfur, graphite, fluorspar, magnesite, borate ore |
| Drilling Rig | `machine.drilling` | 2 | crude oil, natural gas |
| Harvester | `machine.agriculture` | 10 | timber, wheat, corn, soybeans, sugarcane, cotton, rapeseed, potatoes, fruit, natural rubber |

Downstream definitions remain Processor (68 options), Fabricator (86), and Assembler (150). The five canonical Energy definitions found at runtime remain Solar Array, Wind Turbine, Coal Power Plant, Gas Power Plant, and Nuclear Power Plant.

The expected final artwork hooks are:

- `src/production_zero/assets/machines/drilling_rig.png`
- `src/production_zero/assets/machines/agriculture.png`

The final Drilling Rig and user-designated Harvester artwork are installed at their canonical paths. Neither family uses Extractor fallback art. The Harvester source is RGB-only and its baked checkerboard remains visible; the integration preserves the supplied bytes unchanged.

## Save version and migration

Serialized game state now contains `state_schema_version: 2`, `resource_sites`, and `energy_plants`. The outer developer-save envelope remains version 1 because its file/container contract did not change; its nested state payload carries the new migration version.

`migrate_production_boards()` in `src/production_zero/persistence/sqlite_store.py` performs the versioned migration and also repairs invalid ownership in current-version payloads:

1. Creates Site 1 and Plant 1 when absent.
2. Traverses every saved Hall without imposing a Hall-count cap.
3. Uses stored `slot_indexes` to identify valid positions in the first five Lines.
4. Moves primary-production installations to Resources and Energy installations to Energy.
5. Reclassifies legacy Extractors from their selected target while retaining the same card ID and `MachineProductionState`, including target, selected production ID, status, and partial-cycle progress.
6. Compacts downstream cards displaced from removed Line 6 into free valid Factory positions.
7. Leaves any card that cannot fit uninstalled, which returns it to the ordinary inventory without changing card records or stack quantities.
8. Validates version-2 board contents on every load, relocating wrong-family placements or returning them to inventory if the correct board has no free slot.

The migration never truncates Halls and never deletes cards. Tests cover Energy and Extractor moves, occupied Line 6, insufficient destination capacity, four-Hall saves, non-contiguous slot indexes, production-state preservation, and round-trip serialization.

## Command validation

`InstallCardInHall` now resolves board ownership below the UI. Explicit board commands and omitted-board calls against split states both validate the actual owning collection:

- Factory accepts only Processor/Fabricator/Assembler (plus canonical legacy aliases normalized by the data layer).
- Resources accepts only Extractor/Drilling/Agriculture.
- Energy accepts only `CardKind.ENERGY`.

The view filters are therefore convenience, not the security boundary. Raw pre-split `GameState` fixtures with no Site or Plant retain a narrow legacy path so old saves can be constructed and migrated in tests. Dev-tools line unlocks now dispatch against all three board collections with explicit ownership.

## Simulation and analytics

`SimulationEngine` and production analytics now traverse `GameState.all_production_units()`. The shared global resource inventory and energy state are unchanged: Resources creates raw inputs, Factory consumes and transforms them, and Energy contributes shared generation. Coal, gas, and nuclear generators continue to consume their configured fuel from global resource stock; Solar and Wind remain inputless. Freight remains structurally separate.

Installed-card accounting also traverses all three production-board collections, so cards installed on Sites or Plants are excluded from available inventory stacks exactly like Hall cards.

## Relevant implementation files

- `src/production_zero/core/enums.py`: `MachineType.DRILLING`, `MachineType.AGRICULTURE`.
- `src/production_zero/core/state.py`: `MAX_FACTORY_LINES`, `FactoryHall`, `GameState.resource_sites`, `GameState.energy_plants`, `production_units()`, `all_production_units()`.
- `src/production_zero/core/commands.py`: `PurchaseProductionUnit`, board-aware rename/unlock/install/remove commands, placement validation, primary-target validation.
- `src/production_zero/data/definitions.py`: `DRILLING_PRIMARY_RESOURCES`, `AGRICULTURE_PRIMARY_RESOURCES`, `primary_machine_type_for_resource()`, `_split_primary_production_families()`.
- `src/production_zero/core/simulation.py`: aggregate board traversal and unchanged global fuel/resource flow.
- `src/production_zero/core/analytics.py`: aggregate production-unit analytics.
- `src/production_zero/persistence/sqlite_store.py`: `STATE_SCHEMA_VERSION`, production-unit serialization, `migrate_production_boards()`.
- `src/production_zero/ui/factory_view.py`: `ProductionBoardConfig`, shared board logic, filtering, board-aware commands.
- `src/production_zero/ui/factory_view_v2.py`: `ProductionBoardViewV2`, configurable plates/controls, concrete `FactoryViewV2`.
- `src/production_zero/ui/production_board_views.py`: Resources and Energy configurations/views.
- `src/production_zero/ui/main_window.py`: board construction, navigation order, refresh routing, new-game/reset topology.
- `src/production_zero/ui/dev_tools_view.py`: explicit all-board line unlock support.
- `src/production_zero/ui/machine_art.py`: explicit primary-family asset mappings with no Extractor fallback.
- `src/production_zero/ui/game_ui/rendering/factory.py`: primary-family labels/accent routing.
- `tests/test_production_board_split.py`: split ownership, topology, migration, simulation, fuel, navigation, and persistence coverage.
- Existing Factory/core/UI/progression tests were updated where their assertions encoded six Lines, 60 slots, 13 canonical definitions, or mixed Factory ownership.
- `scripts/capture_production_board_split.py`: repeatable offscreen visual-QA capture.

## Validation

- Compile: `.venv/Scripts/python.exe -m compileall -q src tests` — PASS.
- Dedicated split suite: `tests/test_production_board_split.py` — 13 passed.
- Broader targeted core suite (`test_production_board_split.py`, `test_card_definitions.py`, `test_commands_and_simulation.py`) — 78 passed.
- Full suite: 723 passed in 692.25 seconds.

Eight offscreen captures were rendered at compact 1366×768 and desktop 1920×1080:

- `artifacts/production_board_split/resources_compact_1366x768.png`
- `artifacts/production_board_split/factory_compact_1366x768.png`
- `artifacts/production_board_split/energy_compact_1366x768.png`
- `artifacts/production_board_split/resources_drawer_compact_1366x768.png`
- `artifacts/production_board_split/resources_desktop_1920x1080.png`
- `artifacts/production_board_split/factory_desktop_1920x1080.png`
- `artifacts/production_board_split/energy_desktop_1920x1080.png`
- `artifacts/production_board_split/resources_drawer_desktop_1920x1080.png`

Visual inspection confirmed the shared V2 material language and dimensions, correct Hall/Line, Site/Sector, and Plant/Block terminology, five Factory Lines, absence of Guide controls on Resources/Energy, absence of the Energy drawer, and a functional Resources card drawer at both viewports. Ten-position tracks retain the established Factory V2 compact overflow treatment; no new board-specific clipping or dead control space was introduced.

## Unresolved issues

- Harvester now uses the supplied final file, but that 1536×1024 RGB file has no alpha channel and visibly contains an opaque baked checkerboard. A transparent replacement would be required to remove that background without modifying the supplied artwork.
- Permanent Hall/Site/Plant caps, purchase balance, and long-term progression/gating remain intentionally deferred.
- Site/Plant purchase pricing currently reuses the existing Hall progression and is not asserted as final balance.
