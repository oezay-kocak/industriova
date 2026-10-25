# Production Zero — General Functionality QA

Date: 2026-09-10\
Scope: player-facing functional regression after production-board split, Freight modernization, Unlock Tree, and UI polish.\
Method: command-level state tests, real Qt offscreen interaction tests, persistence round-trips, grouped subsystem tests, compile validation, and one full-suite run. The normal GUI was not launched.

## Executive result

One functional defect was reproduced and fixed: Freight locked-slot affordability could remain stale after cash changed during runtime activity. The defect was shared by Garage, Rail, Port, and Airfield because all four use `FreightView.refresh_runtime()` and `ClickableFreightSlotCard`. It did not affect the underlying expansion command and did not affect Resources, Factory, or Energy, whose shared runtime refresh already updates expansion affordances.

No other gameplay-state defect was found. A broad subsystem run passed 248 tests and exposed three obsolete UI assertions; the one allowed full-suite run passed 773 tests and exposed eight additional obsolete ownership/geometry assertions. Those assertions were aligned with the current approved QGraphics Chain Inspector, compact Energy track, Packs result header, and current font metrics. All eleven affected tests pass when rerun in focused groups. Per the explicit one-full-suite constraint, the complete suite was not run a second time.

## Issue QA-01 — Freight expansion remains disabled after runtime cash increase

- Severity: B — player-facing progression action can remain unavailable despite satisfying its legitimate cost condition.
- Reproduction:
  1. Open Freight with less than the next-slot cost ($300).
  2. Install and assign a matching Freight card and start an active market shipment.
  3. Let runtime cash increase to an affordable amount, as when a delivery is credited.
  4. Observe that the already-rendered next locked slot still has `clickEnabled == false`.
  5. Removing/canceling a card causes a structural `refresh()`, reconstructing the locked slot with the correct enabled state; this explains the manual observation.
- Root cause: `FreightView._locked_slot_specs()` correctly derives affordability from cash, but it was only evaluated during structural `FreightView.refresh()`. `FreightView.refresh_runtime()` updated KPIs, cargo, and shipment widgets but not locked-slot or facility-build affordability. Additionally, the next-slot signal was connected only when the slot was affordable at construction, preventing later runtime enablement.
- Fix:
  - `ClickableFreightSlotCard.set_click_enabled()` now updates cursor, click state, rendered affordability, and repaint state.
  - Next-slot activation is wired based on topology (`isNextUnlock`), independently of current cash.
  - `FreightView._refresh_expansion_affordability()` recomputes locked-slot and build-button affordability during normal runtime refresh without rebuilding the board.
  - The command layer remains unchanged: `ExpandFreightFacility` still depends only on facility existence, maximum capacity, and cash.
- Regression coverage:
  - Real Qt mouse interaction for Garage/Truck, Rail/Train, Port/Ship, and Airfield/Aircraft.
  - Each case begins unaffordable, adds cash during an active shipment, calls the normal runtime refresh, clicks the same locked-slot widget, verifies exactly $300 is deducted, and verifies the card, assignment, and active shipment survive.
  - Facility-build buttons are checked through the same unaffordable-to-affordable runtime transition while the original shipment remains active.
  - SQLite round-trips cover all four expanded facility types with installed cards, assignments, and active shipments.

## A. Freight expansion

| Facility | Card | Active shipment | Slot unlock | Exact deduction | Existing card/shipment | Build while active | Save/load |
|---|---|---:|---:|---:|---:|---:|---:|
| Garage | Freight Truck | Pass | Pass | Pass | Pass | Pass | Pass |
| Rail Station | Freight Train | Pass | Pass | Pass | Pass | Pass | Pass |
| Harbor / Port | Cargo Ship | Pass | Pass | Pass | Pass | Pass | Pass |
| Airport / Airfield | Cargo Aircraft | Pass | Pass | Pass | Pass | Pass | Pass |

Initial capacities and full facility progression remain covered by `test_freight_facility_type_capacity_progression`. Installed and active cards do not participate in `freight_facility_expansion_cost()` or `expand_freight_facility()` validation.

## B. Resources expansion

- Active Extractor production was established through the real simulation path.
- Next slot, next Sector, and an additional Site were purchased while production was running.
- Each cost was positive and deducted exactly once.
- Installed card identity, selected resource, and subsequent accepted output remained intact.
- Result: Pass. No analogous stale-affordability risk; shared `FactoryView._refresh_runtime_widgets()` calls `_refresh_unlock_panels()` and `_refresh_build_hall_button()`.

## C. Factory expansion

- Active Processor production with a selected Iron recipe was established with adequate input and Energy.
- Next slot, next locked Line, and an additional Hall were purchased during production.
- Card, recipe selection, machine state, and later output remained intact.
- Result: Pass. No active-card dependency exists in `UnlockProductionSlot`, `UnlockProductionLine`, or `PurchaseProductionUnit`.

## D. Energy expansion

- A Solar Array was installed and contributing generation.
- Next slot, next Block, and an additional Plant were purchased while generation was present.
- Gross generation remained 20 MW before/after structural expansion; expansion itself created no phantom demand.
- Result: Pass. Shared production-board affordability refresh is current.

## E. Card lifecycle

- Primary Production: Extractor, Drilling Rig, and Harvester ownership/family validation passed.
- Factory: Processor, Fabricator, and Assembler board ownership and installation rules passed.
- Energy: install/remove and dynamic power contribution passed.
- Freight: Truck, Train, Ship, and Aircraft installation, assignment, busy-state preservation, recycling/crafting exclusion while installed, and persistence passed.
- Inventory stack tests verify installed cards leave available stacks and return without duplication or loss.
- Result: Pass.

## F. Recipes and production

- Processor with zero unlocked compatible recipes stays `NO RECIPE` and cannot open an invalid production view.
- Adding exactly one compatible unlock enables the real selection control and exposes only that recipe.
- Selecting it persists the recipe and produces output when input and power are available.
- Adding a second compatible recipe restores the change control.
- Primary family/target compatibility and Resources/Factory/Energy board ownership remain enforced by commands.
- Storage-full, missing-input, insufficient-power, fuel-energy, and resume paths passed.
- Result: Pass.

## G. Progression and Unlock Tree

- Canonical starting unlocks, lifetime accepted-production thresholds, multi-input/fixed-point evaluation, company-level gates, persistence, legacy migration, and grandfathered unlock state passed.
- Unlock Tree still contains 353 runtime-derived nodes and 708 runtime-derived edges.
- Open/Back, stage filters, search, direct parent/child trace, zoom/pan, read-only behavior, and representative displayed/runtime state agreement passed.
- Result: Pass.

## H. Industrial Supply

- Common and Daily Supply purchase, affordability, daily independence/reset, Energy availability, Freight availability, and inventory insertion passed.
- Current runtime definitions include Drilling Rig and Harvester in the appropriate Machine supply pool.
- Quantity purchase and total-price behavior are covered by the current Common Supply UI tests and command tests.
- Result: Pass.

## I. Inventory, Crafting, and Scrap

- Card filtering/workspace navigation, rarity targets, quantity/state presentation, and reachable actions passed.
- Scrap values, selected quantities, inventory decrement, Scrap increment, and installed-card rejection passed.
- Rare/Epic/Legendary crafting, exact material count, mixed type/same rarity handling, successful consumption/grant, invalid-count rejection, and persistence passed.
- Result: Pass.

## J. Packs

- Empty state, Daily Mini Pack, Full Pack, category pools, valid rarity generation, exactly-once opening, inventory rewards, pack consumption, contract rewards, and save/load passed.
- Two stale visual tests assumed the result canvas had no current `PACK OPENED` header and sampled the old canvas background. They now verify current geometry stability through reveal/confirmation without generating QA screenshots.
- Result: Pass.

## K. Contracts

- Regular partial delivery/regeneration, Daily completion/reset, Weekly reset/reward, cash and XP award timing, Freight autorouting, surplus sale, and duplicate-payment prevention passed.
- Result: Pass.

## L. Market

- Deterministic ticks, search/filter control preservation, event rotation/modifiers, market delivery, contract priority, surplus sale, cash changes, and capacity-limited shipment behavior passed.
- Resource commands prevent impossible over-capacity and negative consumption states.
- Result: Pass.

## M. Storage and Energy

- Production respects storage limits and resumes when space becomes available.
- Storage expansion deducts the correct cost once, increases capacity, persists, and clears the blocked state.
- Insufficient Energy blocks machines; Solar/fuel generation restores supply; removing generation and fuel consumption update totals dynamically.
- Cross-board demand/generation aggregation passed, and structural expansion creates no Energy use by itself.
- Result: Pass.

## N. Save/load

- SQLite round-trips preserve expanded board topology, all four Freight facility expansions, installed cards, selected production, assignments, active shipments, resources, cash, progression, XP/company state, inventory stacks, packs, and storage level.
- Legacy board split, rarity-only, progression, storage, and malformed cross-board placement migrations passed without card loss or duplication.
- Result: Pass.

## Test results

- Reported defect before fix: 1 failed, demonstrating stale `clickEnabled` after runtime cash change.
- Final focused regression group: 28 passed.
- Focused retest of all eight full-suite failures: 8 passed (five in the first retest group and three in the final retest group).
- Broad gameplay subsystem run: 248 passed, 3 obsolete UI assertions initially failed; all three subsequently passed after assertion updates.
- Compileall: passed for `src` and `tests`.
- Full suite (single permitted run): 773 passed, 8 obsolete UI assertions failed in 502.00 seconds. All eight were subsequently rerun and passed in focused tests. No second full run was performed because the task explicitly permits only one full-suite run.

## Files and symbols

- `src/production_zero/ui/freight_view.py`
  - `ClickableFreightSlotCard.set_click_enabled`
  - `FreightView.refresh_runtime`
  - `FreightView._refresh_expansion_affordability`
  - `FreightView._build_locked_slot_card`
- `src/production_zero/core/commands.py`
  - audited unchanged: `ExpandFreightFacility`, `BuildFreightFacility`, `UnlockProductionSlot`, `UnlockProductionLine`, `PurchaseProductionUnit`
- `src/production_zero/core/freight.py`
  - audited unchanged: `freight_facility_expansion_cost`, `expand_freight_facility`, `start_outbound_shipments`
- Regression tests:
  - `tests/test_factory_ui.py`
  - `tests/test_freight.py`
  - `tests/test_production_board_split.py`
  - current-structure assertion maintenance in `tests/test_final_language_alignment.py`, `tests/test_factory_view_v2.py`, `tests/test_final_visual_audit_fix_pass.py`, `tests/test_packs_polish.py`, and `tests/test_secondary_modernization.py`

## Remaining release blockers

No known gameplay blocker remains. Verification caveat: although every failing test from the single full-suite run now passes in focused reruns, policy for this task prevented a second clean full-suite invocation. A future CI/full run should confirm the aggregate `781/781` result.
