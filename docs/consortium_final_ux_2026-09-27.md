# Consortium final UX and Daily Activity notification pass

## Implementation summary

Consortium now uses the existing global navigation material rules, rounded recessed workspaces, a composed Overview dashboard, simultaneous Daily and Weekly contracts, and a compact member roster with context-menu management. Destructive actions use explicit embedded confirmations. Routine Daily Activity XP is silent until its configured daily allowance is complete.

Changes are confined to Consortium and activity notifications. The accepted Research, personal Contract product component, Player Profile, and production/economy screens were not redesigned.

## Files changed

| File | Change |
| --- | --- |
| `src/production_zero/core/company_xp.py` | Emit a completion notification when the existing daily counter reaches its configured cap. |
| `src/production_zero/ui/event_feed.py` | Exclude routine continuity XP from generic Company Progress notifications; display the completion event in ticker/history. |
| `src/production_zero/ui/consortium_view.py` | Overview, simultaneous contracts, member roster/context menus, material workspaces, confirmations. |
| `src/production_zero/ui/theme.py` | Remove flat Consortium tab overrides; add scoped roster, menu and dashboard typography. |
| `tests/test_daily_activity_notifications.py` | Silent increments, configured cap, completion deduplication, save/load, next period, bank and other XP. |
| `tests/test_consortium_final_ux.py` | Responsive sections, independent callbacks, roster capacity states, permissions, profile links and destructive confirmations. |
| `tests/test_consortium_ui.py` | Adapt assertions to two visible sections, readable rows and context-menu interaction. |
| `tests/test_human_review_followup.py` | Scope existing product/quantity checks to each simultaneous contract section. |
| `scripts/capture_consortium_final_ux.py` | Reproducible in-memory visual fixtures and manifest. |

The workspace already contained extensive prior changes; this list describes only this pass.

## Daily Activity: before and after

Previously, the feed inferred generic XP events from every increase in total Company XP. This produced repeated small Company Progress entries even though the game already tracked continuity XP separately.

The feed now subtracts the increase in the existing cumulative `xp_by_source['continuity']` counter from that generic notification calculation. Daily and banked continuity awards remain mechanically unchanged and silent. Other XP sources, contract rewards, unlocks, research points and ordinary meaningful events keep their existing behavior.

At the actual daily-cap crossing, `record_accepted_production_xp` emits one `daily_activity` event through the existing pending activity channel. The text uses the actual earned daily counter, governed by `CONTINUITY_DAILY_CAP`, rather than an assumed amount. It appears immediately in the ticker and Activity History as **DAILY ACTIVITY COMPLETE · +… XP**.

No XP rates, caps, award calculations, levels or XP persistence fields changed. Existing persisted counters prevent replay after reloading a completed day; a partial day can complete after loading, and a new day can emit its own event. Spending banked XP after daily completion does not produce another daily completion event. No historical entries or saves are destructively migrated. Activity History retains its existing session-history lifecycle.

## Components reused

- Consortium internal tabs now inherit the exact global `QTabBar::tab`, selected, hover and pressed stylesheet rules. Only sizing and typography scale are local. The former flat background/state overrides were removed.
- `MaterialFrame` with `MaterialLevel.INSET` supplies page chassis, contract sections, status cards and stat modules.
- The accepted `ContractProductButton` remains unchanged and is reused for all three Daily and four Weekly products, including active delivered/required values.
- Existing `RaisedPZButton` variants provide Start, Contribute, Invite, Save, Cancel and destructive actions.
- Existing progress bars, embedded scrim behavior, company Profile entrypoints, contract picker and service permission checks are retained.

## Overview

The left status card contains prominent level and member-capacity modules, next capacity and join-policy modules, chairman identity and the existing XP progress treatment. The right card retains the recent-activity list. Both cards have bounded heights, preserving deliberate open space rather than stretching sparse content across a huge panel.

## Daily and Weekly contracts

The presentation selector is gone. Two separately scoped sections appear in order, Daily then Weekly, each with its own status/action, products, metadata and rewards. Active sections add per-product progress/contribution and eligibility details. Product picker callbacks carry their contract kind explicitly; starting or contributing to Weekly cannot accidentally target Daily. Both timers refresh independently.

Empty and selected sections fit together without page scrolling at 1600×980 and 1920×1080. At 1366×768, the unchanged readable product-module height requires internal vertical scrolling. Detail-heavy active states may also scroll; lower metadata and controls are captured separately. Horizontal scrolling and root expansion are checked.

## Members and management

The roster has a fixed 32-pixel header and 48-pixel rows with readable company, level, role and contribution columns. One member uses a compact housing. Larger rosters use a bounded internal viewport, tested at 10, 25 and 50 members. Management Settings is a compact 148-pixel module, and Invite Player remains at the upper right for permitted roles.

Left-clicking a company opens its existing Player Profile. Right-clicking a row or its company name opens a styled context menu. All users can open a profile. The chairman can promote/demote or remove non-chairman members and transfer leadership through the already-supported service operation. Transfer has an explicit confirmation explaining the actor's new Board Member role. Unsupported permissions/actions are not offered. The old selected-member helper strip is removed.

The chairman sees only **Disband Consortium**; other members see only **Leave Consortium**. Both are raised red buttons. The permanent warning strip is removed.

## Destructive confirmations

The embedded confirmations use a material chassis, readable consequence text, neutral Cancel and a raised red confirmation. Cancel/Escape leaves state untouched. Underlying controls are disabled while the confirmation is open.

Disband explains that the Consortium, its XP/level and membership records are deleted; active contracts expire; their pending personal rewards are forfeited; delivered goods are not returned; and rewards already granted to companies remain. Leave explains immediate membership termination, no goods refund, active-contract personal reward forfeiture when applicable, and retention of the Consortium's progress. Wording follows the existing service methods.

## Screenshot review and corrections

Actual renders were inspected throughout, including side-by-side global/internal tabs and all requested sizes.

1. A one-member roster initially stretched its header into a tall grey region. Header and housing heights were bounded.
2. Management Settings then absorbed excess space at larger sizes. It now has a compact fixed height.
3. The normal-member header had no Invite button to constrain it and stretched independently. It now has a dedicated fixed-height header frame.
4. Confirmation text was initially tiny and later clipped after increasing the font. A readable font, wider chassis and sufficient body height now expose the complete consequences.
5. Overview cards stretched too far below their content. Their height is bounded, with larger primary statistics and deliberate whitespace outside the cards.
6. Active product wrappers retained obsolete row borders. These were removed locally without altering the accepted product component.
7. The generic event formatter added a redundant “DONE” prefix to daily completion. The dedicated event now displays the requested wording directly.
8. Native menu/history popups are not included by `window.grab()`. The capture tool now records those actual popup surfaces separately, and advances the ticker deterministically so the completion message is visible.

Progression was inspected with its existing milestone structure and only receives the common workspace treatment.

## Capture manifest

`artifacts/consortium_final_ux/manifest.json` lists **72 captures**, covering 1366×768, 1600×980 and 1920×1080. Each resolution includes Overview one/populated; Contracts empty/selected/Daily-active/both-active/contribution progress and scrolled details; Members 1/10/25/50, context-menu anchor and actual popup, bottom actions, owner/non-owner states; disband and leave confirmations; default/progressed Progression; and Daily Activity before/completion/history plus the actual History popup.

Three `contact_<resolution>.png` sheets collect the full-window states. Fixtures are in memory; no player save is modified.

## Validation

The established module-isolated runner loads QA fonts and uses a fresh offscreen QApplication per module. Logs, JUnit XML and the final summary are stored under `artifacts/consortium_final_ux/tests/`.

- Final full suite: **968 passed across 68 modules**, zero failures/errors/skips.
- Final post-review Consortium responsive and interaction rerun: **22 passed**; `artifacts/consortium_final_ux/final_focused.xml`.
- Daily Activity notifications: **2 passed**, including configured-cap substitution, silent increments, one completion, other XP preservation, partial/completed save-load, bank and next-day behavior.
- Company XP progression: **13 passed**; Consortium core mechanics/permissions: **13 passed**; Profile entrypoints: **4 passed**; shared UI foundation: **9 passed**; progression communications: **5 passed**.
- `compileall -q src tests scripts`: passed after final edits.

Existing presentation assertions were updated for two section containers and the requested row height/context-menu interaction. Behavioral permission, selection, completion and profile assertions remain. A final combined focused rerun exposed a deferred hidden header in a broad child search; the assertion now checks the current layout's header rather than a stale widget pending deletion.

## Remaining human design decision

None required for implementation. Human review can judge the deliberate Overview whitespace and comfortable roster density from the supplied captures. Readable product modules and internal scrolling are retained at compact sizes rather than reducing control legibility.
