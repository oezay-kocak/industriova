# Player Profile and visual convergence — 27 September 2026

## Implementation

One immutable `PlayerProfile` snapshot contract and one embedded `PlayerProfileView` serve the Command Deck level button, Consortium member company-name links, and explicit Leaderboard PROFILE buttons. `MainWindow.open_player_profile(snapshot)` is the reusable entry point for future surfaces. The overlay restores the previous enabled state of underlying controls, closes with Escape or Close, and follows host resizing without creating a native window.

Local profiles read lifetime earnings from `AccountStatistics.total_earnings`, production totals and the most-produced product from `ProductionProgress.lifetime_produced`, company level/title, and local Consortium membership/role/contribution. Stock is not mistaken for production. The graph uses the existing `LineChartWidget` with an immutable snapshot of the leading product's last 600 recorded production-rate samples.

Consortium records expose only known identity/membership/contribution information. Offline leaderboard fixtures are explicitly marked DEMO. Unknown metrics remain unavailable, rather than displaying invented zeroes or another player's data. No save schema, gameplay rule, Research mechanic, or Consortium mechanic changed.

## Visual grammar extracted from the product

The before-pass contact sheet is `artifacts/global_ui_contact_sheet.png`. Factory V2, Resources, Energy and Freight supplied the main references; Inventory, Market and Contracts supplied the secondary-workspace references.

| Element | Existing grammar reused |
| --- | --- |
| Shell | Light concrete / painted-metal chassis, restrained rounded corners, shaded structural edges |
| Functional surface | Dark graphite recess inside a visible housing; neutral borders rather than decorative green outlines |
| Header | `MainTabHeader`: large dark title, red subtitle, material track and compact status modules |
| Typography | Existing industrial section labels; existing Segoe UI hero/metric hierarchy; compact muted metadata |
| Actions | Raised yellow primary controls; raised graphite secondary controls; red reserved for destructive actions |
| Navigation | Dark inset choices, yellow selected accents, consistent hover/focus borders; scroll within dense rails |
| Rows/cards | Neutral dark material, compact separators, material hierarchy around groups |
| Semantics | Cyan for information/progress, green for completed/eligible/success, red for danger, yellow for action/selection |
| Icons | Existing `ResourceIconWidget` assets; no new icon family |
| Spacing | Existing 8–12 px gaps and 14–18 px internal panel padding; internal scrolling at minimum window size |
| Empty/locked | Existing empty-state language; truthful empty data, preserved prerequisite and unavailable states |

The new `MaterialFrame` is layout-neutral and calls the existing material painters. `RecessedPanel` extends the existing `GamePanel`; it adds the existing inset surface over a graphite backing. These are used only by the changed views. Global material primitives were not restyled.

## Findings and corrections

| Finding | Classification | Correction and review |
| --- | --- | --- |
| Consortium flat blue-grey shell | A material, D component, I visual smell | Concrete secondary chassis; existing material painter for progress, roster and overview housings |
| Decorative green progress/operation borders | A, B geometry, G hierarchy | Neutral structural edges; cyan XP progress; green retained only for semantic success |
| Consortium internal navigation looked disconnected | B, D, E states | Dark tabs with yellow selected plates and explicit hover state; same four pages and order |
| Generic-looking member table | A, C typography, D, G | Material housing, graphite rows, role accents, readable company profile links; management row selection preserved |
| Flat small secondary actions and Cancel buttons | D, E, I | Existing `RaisedPZButton` painter, preserving action roles and callbacks |
| Directory inactive filters lost contrast against light shell | A, E | Scoped dark text on concrete inactive chips; yellow active state retained |
| Research rail's pale category buttons differed from production rails | A, B, D, E | Existing chassis painter, dark choices, yellow selection, hover/pressed/focus states; all 21 categories and scrolling preserved |
| First Profile/overview material pass was too light under white text | A, C | Added canonical recess over dark backing; rerendered |
| First member profile links were visually too heavy | G, H density | Quiet left-aligned text buttons with hover/focus feedback; management selection remains on the row |
| Initial Profile graph at 150 px crowded tick labels | C, H | 210 px compact graph; reduced identity padding; rerendered at all three resolutions |
| Consortium section-heading contrast after shell changes | C, G | Corrected headings for their actual dark page surface |

All entries above were found during code inspection or agent review of automated captures. They are not claims of a pixel-level automated design classifier.

## Screen audit

Categories: A material/color, B geometry, C typography, D component reuse, E interaction states, F iconography, G hierarchy, H density, I visual smells. PASS means no major unexplained discrepancy was found in the inspected states, not exhaustive coverage of every possible save.

| Screen / inspected scope | A | B | C | D | E | F | G | H | I | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Resources / default, locked expansion | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Reference, preserved |
| Factory V2 / default, locked slots/lines | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Reference, preserved; only shared Command Deck level became an action |
| Energy / default, locked expansion | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Reference, preserved |
| Freight / default, locked capacity | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Reference, preserved |
| Inventory / populated card collection, filters, crafting | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Preserved |
| Market / populated rows, filters, price-history detail | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Preserved |
| Contracts / default offers and product picker pattern | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Preserved |
| Consortium / directory, empty/populated/full/locked | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Converged |
| Consortium / Overview, Contracts, Members, Progression | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Converged; 50-member and scrolled management captures |
| Consortium / create, invite, product picker, daily/weekly preview, active contract | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Canonical actions/materials, workflows retained |
| Research / default, final category, available/locked, scrolled rail | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Rail converged; tree and specialization materials preserved |
| Industrial Supply / daily and owned-offer storefront pattern | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Preserved |
| Packs / empty state and six-card reveal | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Preserved |
| Leaderboard / ranking rows, own company, profile actions | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | Existing composition preserved |
| Profile / empty, populated, demo, remote missing metrics, long company name | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | New, shared component language |

Production Guide / Chain Inspector components and existing secondary-surface code were inspected as references. The final suite also regenerated Packs six-card reveal, Inventory crafting and Market detail screenshots; these were visually reviewed as additional references. Existing tests cover additional production, inventory, market, packs, navigation, resource tiles and Research interaction states; the new capture manifest does not claim a fresh screenshot of every such state.

## Intentional differences and data limitations

- Research retains its larger 250 px scrolling category rail, warm node plates, angular major nodes and orange RP counter. They support its established hierarchy; its mechanics and canvas were not reopened.
- Consortium keeps its four-tab workspace, row management selection and scrolling roster. Profile links act on company names; clicking elsewhere in a member row still selects management actions.
- Profile is an embedded compact summary, rather than a new main tab. Missing foreign-company metrics use explicit unavailable states.
- No authoritative company valuation total or cumulative regular-contract completion statistic was found. Neither was fabricated. Known Consortium contribution is displayed when available.
- The graph describes recorded production rate, not revenue, lifetime production, or a server timeline. It shows at most 600 recorded samples; the existing renderer labels its range `10M` and its horizontal axis as samples ago.
- Broad layout redesign, changes to accepted reference screens, new asset generation and new persistence were unnecessary.

No blocking human design decision remains from the inspected states. Optional art-direction judgment: whether Research's intentionally preserved warm canvas/node material should later migrate to the cooler production chassis palette. That would be a separate design decision.

## Captures and reproduction

`artifacts/profile_convergence/manifest.json` lists **84 screen/state/resolution captures**: 69 primary captures across **1366×768, 1600×980 and 1920×1080**, plus 15 detailed Consortium captures at 1366×768. The primary capture tool asserts the exact root-window size after every capture.

- `scripts/capture_profile_convergence.py`: all twelve main tabs and Profile/Consortium/Research states at all three sizes, golden comparisons, and the detailed Consortium tool; isolated in-memory fixtures, no player-save writes.
- `scripts/capture_consortium_v1.py`: existing detailed Consortium workflow capture tool, rerun after the changes.
- `artifacts/profile_convergence/contact_<resolution>.png`: full review contact sheets.
- `artifacts/profile_convergence/golden_comparison_<resolution>.png`: Profile/Consortium/Research beside Factory, Freight, Inventory, Market and Leaderboard.

## Files changed in this pass

| File | Purpose |
| --- | --- |
| `src/production_zero/core/player_profile.py` | Immutable read-only contract and local/member/demo adapters |
| `src/production_zero/ui/player_profile.py` | Reusable embedded profile |
| `src/production_zero/ui/material_frame.py` | Thin layout-neutral adapters around existing material painters |
| `src/production_zero/ui/main_window.py` | Shared profile opening and entry-point routing |
| `src/production_zero/ui/factory_view_v2.py` | Accessible Command Deck level action |
| `src/production_zero/ui/consortium_view.py` | Canonical panel/button reuse and company profile links |
| `src/production_zero/ui/research_view.py` | Scoped navigation rail treatment |
| `src/production_zero/ui/leaderboard_view.py` | Profile row actions |
| `src/production_zero/ui/theme.py` | Scoped Consortium styling; accepted screens unaffected |
| `tests/test_player_profile.py` | Data provenance, all entry points, embedded lifecycle, three resolutions |
| `tests/test_factory_view_v2.py` | Level assertion updated from label to button; geometry assertions retained |
| `tests/test_research_ui.py` | Canvas palette check preserved while permitting shared rail tokens |
| `scripts/capture_profile_convergence.py` | Three-resolution capture matrix |
| `scripts/validate_profile_convergence.py` | Complete module-isolated suite runner with QA fonts and XML/log evidence |
| This report and generated capture/test artifacts | Audit evidence |

The workspace already contained extensive modified and untracked work. This list describes this pass, not the entire Git working-tree diff.

## Validation

**Full suite: 949 passed, 0 failed, 0 errors, 0 skipped across all 64 modules**, using process isolation per module and a font-corrected retry of the Inventory geometry module. Compileall passed. Profile: 4 passed at all three supported resolutions. Final Consortium tests: 13 passed. Leaderboard polish module: 25 passed. Research UI: 9 passed; Research layout stability: 2 passed; Factory V2: 59 passed. The complete module-isolated run and its final totals are recorded in `artifacts/profile_convergence/tests/summary.json`; individual XML and logs are alongside it.

The ordinary combined run did not finish: it was interrupted after prolonged cross-module application-stylesheet processing while updating retained `ElidedResourceLabel` widgets from earlier windows. `combined_diagnostic.log` contains the faulthandler stack at `test_leaderboard_polish.py:19` and `resource_tiles.py:40`. Module isolation avoids this shared QApplication-state problem. The isolated runner loads the existing QA fonts, which are necessary for reliable offscreen geometry: an initial Inventory scrollbar assertion failed without those fonts and passed after loading them.
