# Final Visual Audit Fix Pass — 2026-09-09

## Executive summary

This pass resolves both Severity A defects, all nine Severity B findings, and six of seven Severity C findings from `docs/final_visual_audit_2026-09-09.md`. C-02 remains intentionally deferred because the audited left-aligned Inventory sparse layout is an explicit design decision and the existing framed growth canvas is internally consistent; further alteration would be subjective redesign rather than a clean defect fix.

The release-critical outcomes are verified in runtime code and offscreen renders:

- Resources and Energy slot expansion now starts at `$120` and remains positive/monotonic.
- Extractor, Drilling Rig, and Harvester use explicit runtime-type artwork mappings in Resources Card Selection.
- the default player shell has no Dev tab; explicit development mode still exposes it.
- the command deck contains a live production-network summary instead of placeholder copy.
- primary actions become neutral gray when unaffordable.
- compact Inventory filters have a visible horizontal continuation mechanism.
- the Crafting confirmation and CTA remain in the initial 1366×768 viewport.
- Charts and Market use `PRIMARY PRODUCTION`; Freight uses `BUILD FACILITY`.
- Guide statuses use compact wording, singular/plural grammar is correct, and production tracks show a compact continuation chevron.
- wide Energy tracks are vertically proportioned within the shared Factory V2 chassis.

## Finding disposition

| ID | Status | Fix and validation | Files |
|---|---|---|---|
| A-01 | **RESOLVED** | `factory_slot_unlock_cost()` accepts the unit topology's `start_slots_per_line`; command and UI callers pass the selected Hall/Site/Plant value. Factory remains `$120…$660` on Line 1 (slots 4–10), Resources is `$120…$840` (slots 2–10), and Energy is `$120…$390` (slots 2–5), with the existing `$35` per-line surcharge preserved. Full-sequence positivity/monotonicity tests pass. | `src/production_zero/core/state.py`, `src/production_zero/core/commands.py`, `src/production_zero/ui/factory_view_v2.py`, `tests/test_final_visual_audit_fix_pass.py` |
| A-02 | **RESOLVED** | Added one canonical `MachineType → raster family` mapping and routed both selection and installed-card renderers through it. Offscreen Resources selection shows all three distinct artworks. | `src/production_zero/ui/machine_art.py`, `src/production_zero/ui/factory_view.py`, `src/production_zero/ui/factory_view_v2.py`, `tests/test_final_visual_audit_fix_pass.py` |
| B-01 | **RESOLVED** | `PRODUCTION_ZERO_DEV_MODE` now defaults off. An explicit development-mode construction path remains tested. | `src/production_zero/config.py`, `tests/test_factory_ui.py`, `tests/test_final_visual_audit_fix_pass.py` |
| B-02 | **RESOLVED** | Inventory/Crafting filter rails use `ScrollBarAsNeeded`; the established 10 px themed scrollbar makes hidden controls discoverable at 1366×768. Actual-window overflow and visibility are asserted. | `src/production_zero/ui/inventory_view.py`, `tests/test_factory_ui.py`, `tests/test_final_visual_audit_fix_pass.py` |
| B-03 | **RESOLVED** | Reduced non-card Crafting margins, spacing, connector height, and material-slot minimum height while retaining the 2×2 material layout and unchanged card dimensions. The target card is not clipped, and the CTA intersects the initial compact viewport. | `src/production_zero/ui/inventory_view.py`, `tests/test_inventory_workspaces.py`, `tests/test_final_visual_audit_fix_pass.py` |
| B-04 | **RESOLVED** | Both custom `GameButton` primaries and stylesheet-driven Build/Expand buttons now render a muted neutral disabled chassis. Geometry and labels are unchanged. | `src/production_zero/ui/game_ui/widgets.py`, `src/production_zero/ui/theme.py`, `tests/test_final_visual_audit_fix_pass.py` |
| B-05 | **RESOLVED** | Replaced placeholder copy with `PRODUCTION NETWORK` and a live count such as `3 UNITS · 0 MODULES ONLINE`. | `src/production_zero/ui/factory_view_v2.py`, `src/production_zero/ui/text_format.py`, `tests/test_factory_view_v2.py` |
| B-06 | **RESOLVED** | Freight purchase action now reads `BUILD FACILITY`; no player-visible `BUILD SITE` remains in UI sources. | `src/production_zero/ui/freight_view.py` |
| B-07 | **RESOLVED** | Generic stage filters and stage classification now use `Primary Production`; specific Extractor terminology is unchanged. No player-visible generic `Extraction` remains in UI sources. | `src/production_zero/ui/charts_view.py`, `src/production_zero/ui/market_view.py`, `tests/test_factory_ui.py`, `tests/test_market_polish.py` |
| B-08 | **RESOLVED** | Guide status lines now use compact canonical forms such as `NEXT · STEEL 12/60` and `UNLOCKED · MASTERED`; full requirement text remains available to the tile lifecycle as tooltip detail. | `src/production_zero/ui/factory_view.py`, `tests/test_factory_ui.py` |
| B-09 | **RESOLVED** | Energy's existing Block/expansion content is vertically balanced with flexible top/bottom space at wide sizes. No Guide, drawer, fake metric, or Energy-specific visual system was added. | `src/production_zero/ui/factory_view_v2.py`, `tests/test_final_visual_audit_fix_pass.py` |
| C-01 | **RESOLVED** | Reduced command-deck/root vertical margins and spacing while retaining safe metric-label bounds. | `src/production_zero/ui/factory_view_v2.py`, `src/production_zero/ui/main_window.py`, `tests/test_factory_view_v2.py` |
| C-02 | **DEFERRED** | Inventory remains deliberately left-aligned inside its authored light growth canvas. Centering or imposing a speculative narrow rail would reverse the locked design decision; no clean, objective defect remained after compact overflow was fixed. | No runtime change |
| C-03 | **RESOLVED** | Charts resource cards were reduced from 166 px to 146 px, with proportional internal padding/icon adjustments. Metrics and names remain intact. | `src/production_zero/ui/charts_view.py`, `tests/test_factory_ui.py` |
| C-04 | **RESOLVED** | Sparse Common Supply rows now center by computed viewport gutter without resizing cards. Packs already used the intended centered max-width composition and was retained/verified rather than redesigned. | `src/production_zero/ui/supply_view.py`, `tests/test_factory_ui.py`, `tests/test_recipe_retirement.py` |
| C-05 | **RESOLVED** | Selectively raised global navigation, command-deck hint, locked-slot hint, Freight action hint, and Inventory footer microtype. Market row metadata was already 11 px and was left unchanged. | `src/production_zero/ui/theme.py` |
| C-06 | **RESOLVED** | Added shared `count_label()` and applied it to Hall/Site/Plant tracks, module/unit summary, and Freight slot/shipment summaries. Captures show `1 sector` and `1 block`. | `src/production_zero/ui/text_format.py`, `src/production_zero/ui/factory_view_v2.py`, `src/production_zero/ui/freight_view.py` |
| C-07 | **RESOLVED** | Added a small, non-interactive yellow edge chevron while horizontal track content remains clipped/scrollable using the established hidden native bar strategy. | `src/production_zero/ui/factory_view_v2.py`, `tests/test_final_visual_audit_fix_pass.py` |

## Terminology audit

Player-visible UI sources now consistently use `PRIMARY PRODUCTION`, `RESOURCES`, `FACTORY`, `ENERGY`, `FREIGHT`, `SITE`, `SECTOR`, `HALL`, `LINE`, `PLANT`, `BLOCK`, and `FACILITY` in the affected surfaces. `EXTRACTOR`, `DRILLING RIG`, and `HARVESTER` remain the player names backed by explicit machine types and asset families.

The Freight-name discrepancy (`AIRCRAFT/SHIP/TRAIN/TRUCK` versus supply-context `CARGO AIRCRAFT/CARGO SHIP/FREIGHT TRAIN/FREIGHT TRUCK`) is **deferred**. Both sets are contextually coherent, and the repository does not establish a single canonical player-facing choice strongly enough to justify a broad rename in a polish pass.

## MK Upgrade stale-state audit

The current dirty working tree removes the runtime MK Upgrade module/tests while legacy `mkUpgrade*` QSS selectors remain. Because those deletions predate this pass and intent cannot be proven from runtime references alone, the retirement state is **ambiguous**. No feature was reintroduced and no potentially user-owned selectors were deleted.

## Validation

### Compile

- `.venv/Scripts/python.exe -m compileall -q src tests` — **PASS**
- `git diff --check` on fix-pass files — **PASS** (only repository line-ending notices)

### Focused tests

- Fix-pass regression file — **6 passed**
- Factory V2 — **58 passed**
- Primary Production cards — **6 passed**
- Energy assets — **20 passed**
- Market polish — **5 passed**
- affected Guide, Inventory filter, Crafting, Charts, Market, Supply, and Packs tests — **7 passed**
- focused total — **102 passed**

### Full suite

- collected: **742 tests across 42 test files**
- result: **742 passed**, executed as isolated per-file Pytest processes to avoid Qt cross-file native-state contamination
- `tests/test_factory_ui.py`: **204 passed**
- previously failing regression files were rerun after their fixes: `tests/test_inventory_workspaces.py` **7 passed**, `tests/test_recipe_retirement.py` **4 passed**

A single monolithic Windows/offscreen invocation repeatedly exits after roughly 9% without a Pytest failure or completion record. Every collected file passes in a fresh process, including the 204-test UI file; this is retained below as a test-runner lifecycle issue rather than a product-test failure.

### Visual regression

- **24 native-resolution screenshots**: 12 affected states at both 1366×768 and 1920×1080
- **2 contact sheets**
- capture script: `scripts/capture_final_visual_audit_fix_pass.py`
- artifact directory: `artifacts/final_visual_audit_fix_pass_2026-09-09/`
- compact contact sheet: `artifacts/final_visual_audit_fix_pass_2026-09-09/contact_sheet_1366x768.png`
- wide contact sheet: `artifacts/final_visual_audit_fix_pass_2026-09-09/contact_sheet_1920x1080.png`

Visual inspection confirmed distinct Extractor/Drilling Rig/Harvester art, positive slot prices, readable compact filters, fully visible Crafting decision controls, neutral disabled actions, compact Guide status, corrected unit grammar, improved Energy distribution, denser Charts cards, centered sparse Common Supply, and no new clipping or transparency regressions.

## Files changed by this pass

Runtime/configuration:

- `src/production_zero/config.py`
- `src/production_zero/core/commands.py`
- `src/production_zero/core/state.py`
- `src/production_zero/ui/charts_view.py`
- `src/production_zero/ui/factory_view.py`
- `src/production_zero/ui/factory_view_v2.py`
- `src/production_zero/ui/freight_view.py`
- `src/production_zero/ui/game_ui/widgets.py`
- `src/production_zero/ui/inventory_view.py`
- `src/production_zero/ui/machine_art.py`
- `src/production_zero/ui/main_window.py`
- `src/production_zero/ui/market_view.py`
- `src/production_zero/ui/supply_view.py`
- `src/production_zero/ui/text_format.py`
- `src/production_zero/ui/theme.py`

Tests/tooling/report:

- `tests/test_factory_ui.py`
- `tests/test_factory_view_v2.py`
- `tests/test_market_polish.py`
- `tests/test_recipe_retirement.py`
- `tests/test_final_visual_audit_fix_pass.py`
- `scripts/capture_final_visual_audit_fix_pass.py`
- `docs/final_visual_audit_fix_pass_2026-09-09.md`

## Remaining issues

1. C-02 is intentionally deferred as a subjective sparse-state composition choice; left alignment remains preserved.
2. Freight card naming remains context-dependent and is deferred pending a canonical product-language decision.
3. MK Upgrade retirement is ambiguous in the pre-existing dirty tree, so stale selectors were not deleted.
4. The monolithic Windows/offscreen Pytest process has a cross-file Qt lifecycle exit; all 742 collected tests pass in isolated per-file processes.

## Final disposition

- Severity A: **2/2 resolved**
- Severity B: **9/9 resolved**
- Severity C: **6/7 resolved**, **1 intentionally deferred**
- release-polish visual status: **READY**, subject to the explicitly documented non-product test-runner lifecycle issue and deferred subjective/product-language decisions above.
