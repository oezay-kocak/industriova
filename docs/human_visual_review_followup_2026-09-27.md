# Human visual review follow-up — 27 September 2026

## Implementation

The Player Profile now has darker, stronger, compact metadata aligned with the Company panel, a raised red Close control, and an **Inventory History** panel. The left production highlight remains the lifetime production leader. The chart independently follows the resource with the largest current quantity in global storage, with its icon, name, and authoritative current quantity.

Personal Regular/Daily/Weekly contracts and Consortium Daily/Weekly contracts share `ContractProductButton`: one recessed product object containing the existing resource artwork, name, and required quantity. The same component handles empty, selected, active/read-only, and disabled presentations. Existing pickers, duplicate prevention, permissions, rewards, accept/cancel/contribute workflows, and requirement counts remain in place.

The Consortium tab bar backing is transparent, exposing its light parent between and after the existing tabs. Research's outer navigation rail uses the canonical dark inset material; all 21 category buttons, grouping, icons, width, scrolling, and research behavior remain intact.

## Inventory history architecture

- `GameState.inventory_history` owns timestamped global-stock observations, independent of the existing short raw-history series.
- The simulation records the first positive advance, then an endpoint at least every **300 seconds of accumulated simulation time**. Sampling runs after production and freight delivery.
- Each resource retains at most **865 observations over 72 hours of active simulation time**. Sparse or unusually long advances record only the observed endpoint; they do not invent intermediate stock quantities.
- SQLite saves serialize the history clock, last sample time, and bounded series. Loading preserves cadence. The existing background save snapshot detaches this data from subsequent state mutation.
- Legacy saves start with no history. Offline wall-clock time is excluded. The axis explicitly says **HOURS OF PLAY AGO**; a tooltip explains sampling and retention.
- No history produces a clear empty state. One observation produces a point, not a fabricated trend. Existing observations use their actual time spacing; the chart adds the current stock endpoint for display without mutating saved history.
- Changing the current stock leader changes the displayed series. Empty storage and unavailable remote-company data have distinct messages. Profile snapshots remain immutable.

## Shared Contract Product component

`ui/contract_product.py` owns painting, resource icon placement, name elision and tooltip, quantity presentation, focus/hover/pressed treatment, keyboard activation, and accessibility text. It uses `ResourceIconWidget` and the canonical inset painter.

Personal cards use a compact 62-pixel product module. Consortium selectors and active requirements use a wider 78-pixel horizontal form from the same component. Required quantities come from the existing personal/Consortium calculations. Active modules show delivered/required quantities and preserve progress/fulfilled properties.

## Visual review and iteration

Offscreen captures were inspected against the Resources, Factory, and Energy references included at the start of each contact sheet.

1. The first personal-card render exposed product/reward overlap with the old 166-pixel height. Cards now adapt between 176 and 198 pixels, keeping all three columns. Compact board padding and header spacing restore the existing no-scroll layout at 1600×900 as well as the requested larger sizes.
2. Profile metadata initially sat a few pixels too far right; its padding was corrected to match the Company panel edge.
3. Consortium pre-start requirements were duplicated beneath selected products. The shared modules now carry those quantities directly; active contribution/progress rows remain available.
4. Active Consortium rows had excessive outer padding. Reducing it gives the reward and eligibility sections more space without shrinking the product component.
5. A remaining selector-specific quantity alignment override was removed, keeping icon/name/quantity together according to the shared component's layout.
6. Research rail headings were changed to a neutral light foreground for contrast; the palette check caught and removed a slight green bias.
7. Regression checks found a missing fulfilled property on completed product quantities. Both initial presentation and live updates now preserve it.

Reviewed populated, empty-history, sparse-history, and long-name Profiles; empty/selected/active personal contracts across all three kinds; Consortium daily/weekly selectors and active requirements; the tab row; and Research navigation at top and bottom. Root dimensions remained exact in every capture. Geometry checks verify icon/quantity containment, reward separation, and absence of horizontal scrolling.

## Intentional presentation choices

- At 1366×768, the personal board uses its existing internal vertical scroll area for the taller cards. Bottom actions remain reachable. Larger requested sizes show all nine personal cards without scrolling.
- Narrow product names use ellipsis with full-name tooltips; quantities remain visible. Long Profile company/resource names wrap, with internal scrolling when necessary.
- Active Consortium contracts retain internal scrolling where their contribution, progress, reward, and eligibility content exceeds the viewport. Scrolled captures explicitly verify the lower content.
- History represents active simulation time, not calendar days. Old saves do not gain synthetic historical data.

## Files changed in this follow-up

All source paths below are relative to `src/production_zero/`; pre-existing workspace modifications are outside this inventory.

| Area | Files |
| --- | --- |
| History and snapshot model | `core/inventory_history.py` (new), `core/state.py`, `core/simulation.py`, `core/player_profile.py` |
| Persistence | `persistence/sqlite_store.py` |
| Profile presentation | `ui/player_profile.py`, `ui/inventory_history_chart.py` (new), `ui/pz_controls.py` |
| Shared products and consumers | `ui/contract_product.py` (new), `ui/contracts_view.py`, `ui/consortium_view.py` |
| Local visual corrections | `ui/theme.py`, `ui/research_view.py` |
| Tests | `tests/test_inventory_history.py`, `tests/test_human_review_followup.py`, `tests/test_player_profile.py`, `tests/test_consortium_ui.py`, `tests/test_contracts_polish.py`, `tests/test_factory_ui.py`, `tests/test_playtest2_consistency_followup.py` |
| QA tools | `scripts/capture_human_review_followup.py`, `scripts/validate_profile_convergence.py` |

Test updates replace superseded exact-height/plain-button/duplicate-row assumptions with the requested component and quantity checks. The small-screen active-board assertion now follows the same scrolling policy as the pre-acceptance board; larger-screen no-scroll assertions are retained.

## Capture manifest

`artifacts/human_review_followup/manifest.json` lists **69 full-window PNGs**: 23 states at each of **1366×768, 1600×980, and 1920×1080**. Fixtures are in memory and do not alter player saves. The three `contact_<resolution>.png` sheets include accepted reference screens alongside the changed surfaces. Additional scrolled images cover long Profile names and active Consortium metadata.

## Validation

Final results are recorded in `artifacts/human_review_followup/tests/summary.json`, with module logs, JUnit XML, and retry provenance in the same directory. The runner uses the proven QA fonts and a fresh offscreen QApplication per test module. Single-process Qt stylesheet/lifetime interactions are avoided through module isolation.

- `compileall -q src tests scripts`: passed after the final edits.
- Full module-isolated validation: **957 passed across 66 modules; zero failures, errors, or skips**. Failed first-attempt modules were corrected and rerun in full; `results.json` retains their previous-attempt provenance.
- Final geometry/component and Consortium UI rerun after the last layout/alignment changes: **17 passed**, recorded in `artifacts/human_review_followup/final_consortium_geometry.xml`.
- Focused coverage includes Profile snapshots and entrypoints; inventory sampling, retention, simulation integration, SQLite and detached-save round trips; personal Contract selection and completion; Consortium previews and permissions; Research layout/palette; and shared rendering components. Per-module counts and logs are in the validation directory.
