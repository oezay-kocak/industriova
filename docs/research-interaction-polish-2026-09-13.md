# Research interaction and control polish — 2026-09-13

Research is ready for continued manual playtest. The measured purchase path is substantially faster, with stable widget identities and immediate local state updates. No Research mechanics or balance values changed.

## Measured blocking work

The old purchase callback synchronously ran a full company save, global header refresh, hidden Market refresh, and hidden Contracts refresh before returning to the event loop. Instrumentation and a cumulative Python profile identified:

| Operation | Old measured duration / work |
| --- | --- |
| Full company save | 13.5–35.2 ms, including serialization, JSON encoding, and SQLite commit |
| Hidden Market refresh | 9.0–9.3 ms; emits all-row changes and filters 353 products |
| Hidden Contracts refresh | 32.8–34.4 ms; rebuilds nine offer panels and selection/reward controls |
| Research canvas refresh | Approximately 0.3–0.4 ms |
| Widgets created by the callback | 378 per purchase, from Contracts |

The Research tree and sidebar were **not** being recreated. The profile did not identify modifier cache invalidation or domain catalog validation as the dominant cost. The avoidable blocking work was the application callback rebuilding hidden quote screens and writing the save synchronously.

The reported live one-second pause was not reproduced on this machine. The original starter-state click handler took 57.3–77.7 ms; a level-200 company run took 89.6–107.0 ms including event processing. These are measured local results, not a claim to have timed the user's exact live session.

Evidence is preserved in `artifacts/ui/research-interaction-polish/before-timing.json`, `before-developed-timing.json`, and `before-profile.txt`.

## Fix and new timings

Market and Contracts now refresh when entered instead of during Research purchases. Their authoritative quote calculations still use the existing lazy additive modifier resolver. The global header continues to refresh for relevant value/capacity changes.

Research node and specialization widgets cache their presentation state and skip unchanged accessibility text, tooltips, and repaint requests. The canvas invalidates changed connector regions rather than repainting the entire canvas on each purchase/clock refresh. No widgets are rebuilt. The cheap state scan remains so grants, respec, cooldown-related changes, and the final available RP transition stay correct.

| Measurement | Before | After |
| --- | --- | --- |
| Median click handler | 58.0 ms | **7.0 ms** |
| Click handler range | 57.3–77.7 ms | **5.9–19.8 ms** |
| New click plus event-processing range | — | **20.4–35.1 ms** |
| Widgets created per purchase | 378 | **0** |
| Small-node presentations updated | All 35 refreshed | **2** in the representative sequence |
| First Major presentations updated | All 35 refreshed | **4** |

The two updates are typically the clicked node and its next lane node; purchasing a final-row node can instead update the next Major's prerequisite tooltip. Header counters and relevant connector colors also update. When RP availability crosses zero or respec affects multiple nodes, all genuinely affected states update.

The benchmark clicks an already-rendered tree, includes a real SQLite save queue, and processes Qt events to include the visible update. It does not defer the visible state change. Results are in `after-timing.json`. The focused test also holds the disk writer behind a gate and verifies that a purchase still returns below 100 ms, updates the UI, retains every existing widget, and never calls hidden Market/Contracts refreshes.

## Persistence and integrity

Company snapshots are still serialized and JSON-encoded synchronously on the UI thread, giving an immutable, consistent snapshot. **SQLite I/O and commits are now asynchronous** on one ordered worker; no worker reads mutable game state. Autosaves and Research saves share the same queue, preventing older writes from overtaking newer allocations.

Each write remains a single atomic SQLite transaction. Connections now close explicitly after commit/read; the prior connection context manager committed but could leave handle cleanup to garbage collection. Closing the game queues the latest snapshot, waits for pending commits, and refuses to close if the latest save fails. Failures surface in the status bar and later complete snapshots can retry successfully. Tests cover worker-thread execution, ordered immutable snapshots, failures, retry, and close-time durability.

Purchase callbacks no longer promise that the disk commit has finished when they return: the snapshot is queued immediately and durability follows when its transaction completes. Order and atomicity are preserved, and normal shutdown flushes the queue. Unexpected process termination during a pending write remains a limitation of asynchronous saving.

## Scoped UI changes

- The RP badge keeps its orange Research identity and now has a raised chassis, highlight, shaded bevel, and dark large count.
- Full Respec uses a shared raised primary PZ control with the Storage Expand yellow material palette. Normal, hover, pressed depth, disabled, and focus treatments are implemented without changing respec behavior.
- History and Inbox use the same surface painter's compact graphite/steel variant with light text and preserved unread emphasis. Their native size hints and compact geometry remain unchanged; ticker behavior and panel actions are preserved.
- The audit found painted Storage `GameButton` controls and separate Production Guide/action stylesheet groups. A shared painter now serves the requested primary, compact secondary, and resource-badge variants. Existing Storage/Production Guide rendering was deliberately left unchanged rather than applying an unvalidated app-wide restyle.
- Research heading increased from 19 to 22 px at Black weight; COMPANY and INDUSTRIES increased from 14 to 16 px. The sidebar remains 250 px wide and item fonts/selection geometry are unchanged.
- All Industry side slots move **42 px left**, using one shared inset. Their right clearance is now 68 px. Ordinary lane widths and centers remain unchanged, and horizontal connectors remain clear. The independently positioned slot widgets are raised above row containers so mouse interaction is preserved.

## Exact source and test files changed in this pass

1. `src/production_zero/ui/main_window.py` — targeted purchase callback, tab-entry quote refresh, queued saves and close flush.
2. `src/production_zero/ui/research_view.py` — incremental presentations/connectors, shared controls, sidebar headings, side-slot inset.
3. `src/production_zero/ui/research_specialization.py` — skip unchanged slot presentations.
4. `src/production_zero/ui/pz_controls.py` — shared raised surface painter, primary/secondary buttons, RP badge.
5. `src/production_zero/ui/event_feed.py` — scoped History/Inbox button class changes.
6. `src/production_zero/persistence/session_writer.py` — ordered background commit queue.
7. `src/production_zero/persistence/sqlite_store.py` — immutable-payload write entry point and explicit connection lifetime.
8. `src/production_zero/tools/research_interaction_qa.py` — timing instrumentation and four captures.
9. `tests/test_research_interaction_polish.py` — incremental updates, responsiveness with blocked disk, write order/retry, controls and compact inset coverage.
10. `tests/test_research_ui.py` — wait for queued durability before inspecting SQLite.
11. `tests/test_research_specialization_ui.py` — wait for queued specialization/refund commits before inspecting SQLite.
12. `docs/research-interaction-polish-2026-09-13.md` — this report.

No Research catalog, modifier economics, RP rewards, icons, or global Theme source was changed in this pass. Preexisting workspace changes were preserved.

## Validation

With `QT_QPA_PLATFORM=offscreen`, ran the four existing Research test files, `test_research_interaction_polish.py`, `test_sqlite_store.py`, and the two focused History/Inbox interaction/geometry tests from `test_live_playtest_polish.py`:

**58 passed in 150.44 seconds.**

This includes all current Research topology, specialization, exact-product economics, migration, persistence, cooldown, and compact text-fit tests. New UI coverage checks primary button state renderings, History/Inbox geometry, heading fonts, slot position/hit testing, and zero horizontal scroll at 1600×900 and 1366×768.

`compileall -q src tests scripts` passed. `git -c core.safecrlf=false diff --check` passed; newly added/untracked edited files also received explicit whitespace checks.

**The full suite was not run. No live GUI was launched.** QA uses an isolated game state and artifact-directory SQLite files, not the player save.

## Four inspected offscreen screenshots

1. [Raised RP and Full Respec header](../artifacts/ui/research-interaction-polish/01-raised-research-header.png)
2. [Full Research view and stronger sidebar](../artifacts/ui/research-interaction-polish/02-research-sidebar-and-controls.png)
3. [Industry inset at 1366×768](../artifacts/ui/research-interaction-polish/03-industry-inset-1366x768.png)
4. [Compact History and Inbox controls](../artifacts/ui/research-interaction-polish/04-history-inbox-controls.png)

The renders show readable raised controls, unchanged main lanes, inset specializations without overlap, and no horizontal clipping. Regenerate with `.venv/Scripts/python.exe -m production_zero.tools.research_interaction_qa`.

## Verdict

**Responsive enough for continued manual playtest based on the measured 20–35 ms rendered interaction.** Confirm the improvement in the original live save; its reported one-second delay was not directly reproduced during offscreen profiling.
