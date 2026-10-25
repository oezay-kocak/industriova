# Final QA: classification of the 15 original failures

Review date: 25 October 2026. Final result: **3,784 passed, 0 failed, 0 errors, 0 skipped across all 121 modules**. No test was disabled or deleted in this finalization. No gameplay feature or economic rule was added.

## Implementation defects

| Original case | Cause | Correction and validation |
| --- | --- | --- |
| `test_research_live_save.py::test_heartbeat_detects_a_stall_after_the_initiating_callback` | Opt-in tracing attempted to wrap the removed `EventFeedWidget._advance_ticker` method, aborting initialization | Instrument the current `_present_next` presentation path. Existing heartbeat-stall detection passes; a freshly installed application also starts and closes with Research tracing enabled |
| `test_industriova_release_ui.py::test_supported_resolution_and_cached_card_rendering[size0]` | Header layout minimum width became 1369px under the supported Windows fonts, exceeding the 1366px viewport | Reduce the header's inter-module spacing from 10px to 8px, retaining all controls. Exact requested dimensions pass at all three tested sizes; header containment is also asserted |

## Obsolete tests or fixtures

| Original case | Current requirement/evidence | Updated verification |
| --- | --- | --- |
| `test_factory_ui.py::test_freight_tab_refreshes_shipment_progress_from_factory_simulation_tick` | Runtime subscribers intentionally skip invisible main tabs; current `main_window._refresh_active_runtime_view` implements this performance boundary | Show and settle the offscreen window before exercising the visible Freight subscriber. Existing widget identity, no structural refresh, shipment status, remaining time and progress assertions are retained |
| `test_factory_ui.py::test_resources_view_opens_visual_production_selection_view_for_extractor_card` | All 49 primary outputs start unlocked; the family partition is 37 mining, 2 drilling, 10 agriculture. See primary-card and production-sales progression tests | Assert all 37 mining options are present and enabled, with no artificial locked primary previews; retain family filtering, search, selection and persisted configuration checks |
| `test_factory_ui.py::test_factory_view_opens_visual_recipe_selection_view_for_processor_card` | The picker shows available recipes and two locked previews ordered by prerequisite state, input count and name. Under current root unlocks the fixture's previews are Aluminum and Ammonia | Replace the obsolete Bitumen preview expectation with Ammonia and assert Bitumen is absent; retain two disabled locked previews, available choices and applied Copper configuration |
| `test_factory_ui.py::test_factory_production_guide_marks_unlocked_next_and_later_progression` | Each downstream product needs 100 self-produced units of each direct input. This is explicit in `core/progression.py` and catalog-wide production-sales progression tests | Require `STEEL 12 / 100`, retaining unlocked/next/later state checks |
| `test_industriova_release_ui.py::test_retired_navigation_and_global_resources_available` | The overlay fits within its parent when reopened. The old 620px-high fixture at y=180 exceeded its parent's height | Test position persistence at an in-bounds position, then additionally move it out of bounds and assert reopening clamps the complete overlay inside its parent |
| `test_phase1_performance.py::test_quick_actions_commit_once_and_visible_views_are_current[50]` | Current infrastructure exposes five unlocked lines of ten slots in this fixture, including vacant slots | Require 50 visible slot widgets after template placement; preserve ownership counts, exact command history and installed MK1 assertions |
| `test_phase1_performance.py::test_quick_actions_commit_once_and_visible_views_are_current[500]` | Same visible-hall rule; 500 is the whole synthetic company card count | Same verification; no reduction in workload or economic assertions |
| `test_pre_research_polish.py::test_controller_and_history_preserve_exact_resource_ids_for_concrete_events` | Different sources of the same event type merge within a fixed aggregation window; mixed-resource summaries intentionally have no single resource identity. Covered by `test_activity_feed_band.py` | Flush between the two concrete unlock windows. Preserve all exact resource-ID and actual History card-icon checks; aggregate behavior remains tested separately |
| `test_research_ui.py::test_research_communications_use_existing_activity_without_small_node_spam` | RP rewards are typed `rp`, while Major-node purchases are `research`; Small nodes do not add activity spam | Assert the RP event's exact amount and source and the single Foundation Research event, plus empty communications queues |
| `test_shareable_playtest.py::test_xp_notification_threshold_preserves_earned_xp[0.5-False]` | The current fixed-window feed retains positive fractional XP instead of discarding values below the old 10-XP threshold; covered by current band aggregation tests | Expect one XP record with the exact 0.5 amount; retain actual company XP and no-inbox-message assertions |
| `test_shareable_playtest.py::test_xp_notification_threshold_preserves_earned_xp[1-False]` | Same positive-XP aggregation rule | Exact 1-XP record and unchanged accounting checks |
| `test_shareable_playtest.py::test_xp_notification_threshold_preserves_earned_xp[5-False]` | Same positive-XP aggregation rule | Exact 5-XP record and unchanged accounting checks |
| `test_shareable_playtest.py::test_xp_notification_threshold_preserves_earned_xp[9.9-False]` | Same positive-XP aggregation rule | Exact 9.9-XP record and unchanged accounting checks |

The original parameter labels above identify the initial failing cases. Positive-XP cases now have the `True` expectation; the 10- and 75-XP cases remain and also pass. No test inputs were discarded.

## Execution and evidence

The complete suite ran with Python 3.12.14, PySide6 6.11.1 and pytest 9.1.1 on Windows, using Qt offscreen, three workers, fresh module processes and a 180-second timeout per module. All 121 current modules were accounted for in the runner output and JUnit totals. Results are stored locally under `artifacts/portfolio-finalization/tests/`; the former failing cases were also checked during focused diagnosis.

Earlier focused attempts encountered the workstation's unavailable default temporary/cache directory and stale parameter node IDs after expectation updates. These attempts were not counted as verification. The final full run uses explicit writable directories and the current complete node set. The runner's own exit code is not used as a substitute for checking all module outcomes.

The pre-existing deletion of the old `tests/test_mk_upgrades.py` predates both portfolio passes and is preserved, not introduced by these corrections. Its former scrap-based, separate-definition upgrade rules are superseded by current cash-based MK1–99 progression; current MK and release integration modules remain included in the full run. The complete change inventory exposes this historical deletion for review.

Offscreen regression and package startup are technical checks. Native drag-and-drop, subjective response, other operating systems and extended human balancing acceptance remain separate limits, as described in the release report.
