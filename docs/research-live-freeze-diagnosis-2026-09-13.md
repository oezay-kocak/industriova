# Research purchase freeze diagnosis — 2026-09-13

## Finding and evidence boundary

A multi-second freeze was reproduced through the real MainWindow → ResearchView → CommandBus → save callback path, using an offscreen window and a running Qt event loop. The dominant source was synchronous `json.dumps(serialize_game_state(...))` in MainWindow._save_session. SQLite had already moved to a worker, but JSON encoding had not.

The corrected baseline recorded a **2029.1 ms callback and 2094.7 ms heartbeat gap**, with **1988.7 ms in UI-thread JSON encoding**. The first pre-fix run independently measured 2,702.9 ms in the callback; a corrected heartbeat run measured 2,166.6 ms. No performance patch preceded that evidence.

This proves a source-level cause on a developed QA save, not the provenance of the user's running binary. The default player company.sqlite was absent. No original player save was read or modified. Existing EXEs are present under dist; they were not rebuilt or launched. The user's exact launch command/build and real company remain unconfirmed.

## Why earlier timing missed it

The previous timing fixture had little history and sampled only a few event-processing passes. Merely raising company level does not reproduce save size. Simulation records three series per resource every 250 ms. The new fixture has 14,400 samples per resource series (one hour at that cadence), approximately 15.3 million metric samples and a roughly 92 MB SQLite file. It includes 353 unlocked products, 492 cards, multiple factory/resource/energy units, 32 owned research nodes after the click, contracts/freight, communications and an active ticker. No game balance, RP cost or research content changed.

## Trace and comparison

All numbers below are milliseconds. Nested stage times must not be added together. The baseline comparison mode replays the original UI JSON expression; an initial pre-patch run also reproduced the freeze. Both use the same developed fixture, QTest mouse click, application callbacks, timers and opt-in trace. The window follows a pending writer and continues for at least two seconds after it finishes, so durations/counts differ with write latency.

| Measurement | Before | After |
|---|---:|---:|
| Purchase callback | 2029.10 | 29.75 |
| Mouse release / clicked dispatch (includes diagnostic entry) | 2038.01 | 39.20 |
| Worst 16 ms heartbeat gap | 2094.69 | 108.86 |
| State mutation | 0.23 | 0.07 |
| Command dispatch | 0.33 | 0.10 |
| Game-state serializer | 13.88 | 11.14 |
| UI JSON encoding | 1988.71 | 0.00 |
| Whole save request | 2005.22 | 26.69 |
| Queue enqueue | 1.91 | 3.00 |
| Research header + node refresh (max invocation) | 23.03 | 2.81 |
| Global header (max invocation) | 0.43 | 0.63 |
| Canvas paint (max invocation) | 1.86 | 2.99 |
| Simulation timer + subscribers (max invocation) | 89.75 | 97.53 |
| Save completion poll (max invocation) | 0.04 | 0.04 |

After snapshot construction including detaching non-history state: **23.59 ms**. UI JSON encoding is now absent. Diagnostic object enumeration adds about 7.1 ms at entry, included in mouse dispatch but outside the purchase callback.

The final after trace covers **11.54 seconds**. No ~1 second event-loop stall remains in that captured window. **The ideal 50–75 ms maximum-gap target is not met:** the worst gap is 108.9 ms. It overlaps a simulation timer invocation, including simulation core, factory runtime widgets and the active-view/feed subscriber. The same company with no purchase/save has a **82.3 ms** worst gap over 10.01 seconds, and its simulation callback reaches 81.1 ms. Writer contention adds some overhead; this report does not attribute all remaining delay to an unrelated timer or claim perfectly smooth frames.

## Fix

1. Capture a detached non-history state dictionary on the UI thread, including Research/RP, cash, progression, contracts and other mutable mappings.
2. Capture each historical series as a backing-list reference plus a fixed prefix length. Simulation only appends; trimming now replaces the list rather than shifting an already-published prefix. A save therefore sees exactly the metric values present at capture time, even if simulation appends, trims or replaces state before encoding finishes.
3. Encode that snapshot in the existing ordered writer. Large history arrays are encoded in 2,048-value chunks. The worker yields for 1 ms after roughly 1 ms of encoding work so Qt can reacquire the Python interpreter lock. This sleep exists only in the save worker, never in the purchase/UI callback.
4. Commit the complete JSON through the existing atomic SQLite transaction. Schema, save/load format, write ordering and error reporting are preserved. Close still waits and refuses to close after a failed save.

A thread-only intermediate implementation was measured and rejected: the callback became short, but Python GIL contention inflated Qt paint/runtime handlers and left a 1,242 ms heartbeat gap. A zero-duration yield also failed on this Windows host. Positive, time-budgeted yields removed that measured delayed freeze. Yielding once per tiny series initially delayed starter saves; the final budget-based implementation passes that regression test.

The large final save takes **9.12 seconds in the background** including encoding and commit. This is a latency tradeoff for UI responsiveness. Rapid purchases can queue behind it, and closing still waits for pending saves plus the final snapshot; this work does not claim faster shutdown or immediate durability after a click.

## Signals, waits and side effects

The ordinary purchase has one QPushButton.clicked connection to ResearchView._purchase. It synchronously dispatches PurchaseResearch, invokes the save/global-header callback and refreshes Research presentation. CommandBus applies the command and appends command history; it does not emit a broad game-state/economy/inventory/research signal. No tab change fires during the purchase. The specialization tile's selected_product signal routes to the specialization purchase callback, also instrumented.

Subsequent timer subscribers captured after purchase:

- Factory simulation timer → SimulationEngine.advance_time → factory runtime widgets → MainWindow active runtime callback.
- Active runtime callback → EventFeedController.observe, global header and visible Research refresh.
- Research's own visible refresh timer, ticker/event-feed timers and save-completion poll timer.

Final trace: 46 simulation callbacks and 46 active-runtime callbacks across the full window. **Zero** Market refresh, Contracts refresh, full-views refresh, History opening or Inbox opening calls. Research activity is consumed by the next feed observation, without opening/rebuilding History or Inbox.

No purchase-side wait, join, flush, SQLite read/reopen or ordered barrier was found. SessionWriter.poll calls Future.result only when Future.done is already true, unless wait=True was explicitly requested for close. Enqueue just submits work. A gated encoder/disk test proves both submit and ordinary poll return while the worker remains blocked. No live purchase path calls processEvents or repaint; logging is disabled unless tracing is opted in, and the trace record is written on a separate diagnostic worker.

## GC, assets and paint/layout

- Collections during the window (generation 0/1/2): **[8, 1, 0] before; [14, 2, 0] after**. No generation-2/full collection. Maximum GC pause: 2.28 ms before and 1.60 ms after. Tracked object deltas: +530 / +546; these include trace records and active timers, not a leak measurement. GC remains enabled.
- Resource raster disk-load cache misses: **0 before / 0 after**. Scaled raster cache misses: **0 / 0**. The already-rendered tree uses cached resource art. Research source contains no purchase-time QPixmap/QIcon disk loader.
- Research canvas paints: **2 / 2**; node paints: **10 / 10**. Canvas regions are a local 310×304 region at (150,198), followed by the visible 1270×604 viewport, on a 1270×2624 canvas. The whole giant canvas is not repainted. A viewport refresh still occurs; the stricter “only changed nodes” paint ideal is not fully achieved, but maximum canvas painting is 2.99 ms.
- Research header layout request: **1 / 1**. No Research canvas resize or stylesheet event. Whole-application counts are 745 / 2203 Paint, 55 / 138 Resize, and 23 / 56 LayoutRequest events across unequal 5.53s / 11.54s windows. Many are ticking global-header/ticker child events; a MainWindow paint event is not proof of a whole-window repaint. The idle control also produces those recurring events. Style changes are local ticker-entry widgets, not reapplication of the application stylesheet.
- Remaining >50 ms UI work is the developed simulation timer and its core. The seconds-long save-worker span overlaps frames in wall time but is not itself UI-thread execution.

## Files changed in this pass

- [src/production_zero/app/__main__.py](src/production_zero/app/__main__.py)
- [src/production_zero/ui/main_window.py](src/production_zero/ui/main_window.py)
- [src/production_zero/ui/research_trace.py](src/production_zero/ui/research_trace.py)
- [src/production_zero/persistence/session_writer.py](src/production_zero/persistence/session_writer.py)
- [src/production_zero/core/history.py](src/production_zero/core/history.py)
- [src/production_zero/tools/research_live_trace_qa.py](src/production_zero/tools/research_live_trace_qa.py)
- [tests/test_research_live_save.py](tests/test_research_live_save.py)
- This report. Existing unrelated workspace changes were preserved. sqlite_store.py was inspected but not changed in this pass.

## Validation

**48 focused tests passed** in 5.68 seconds:

- tests/test_research_live_save.py: capture consistency through append/trim and mutable-state changes; no million-element snapshot copy; gated encoding/commit and ordered writes; heartbeat detection of a delayed injected stall.
- tests/test_research_interaction_polish.py: purchase timing, no hidden Market/Contracts fan-out, retained widgets, nonblocking disk work, save failure/retry, controls.
- tests/test_research.py, tests/test_research_specialization.py, tests/test_sqlite_store.py.
- The two existing metric history retention/range tests in tests/test_resources_and_cash.py.

compileall passed. git diff --check passed (Git printed pre-existing line-ending normalization warnings). Full suite **not run**. Automated Qt work was **offscreen only**; no live GUI or player-save modification. No packaged EXE was rebuilt.

## Trace artifacts and reproduction

- [Corrected before trace](artifacts/research-live-trace/before-verified/purchases.jsonl)
- [Final after trace](artifacts/research-live-trace/after-final/purchases.jsonl)
- [Idle control trace](artifacts/research-live-trace/idle-control/purchases.jsonl)
- [Developed-state metadata](artifacts/research-live-trace/after-final/state.json)

From the project directory, offscreen QA:

```powershell
.venv/Scripts/python.exe -m production_zero.tools.research_live_trace_qa --output artifacts/research-live-trace/new-after
# Diagnostic reference only: restores the old UI encoding expression for this QA process.
.venv/Scripts/python.exe -m production_zero.tools.research_live_trace_qa --output artifacts/research-live-trace/new-before --reference-ui-json
.venv/Scripts/python.exe -m production_zero.tools.research_live_trace_qa --output artifacts/research-live-trace/new-idle --idle-control
```

To enable tracing for a manual source launch, set PRODUCTION_ZERO_RESEARCH_TRACE to a JSONL filename before running `.venv/Scripts/python.exe -m production_zero.app`. Unset that environment variable to use ordinary QApplication with no diagnostic hooks, heartbeat or logging. Existing packaged EXEs require rebuilding before they contain this fix or trace support.
