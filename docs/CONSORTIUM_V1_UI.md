# Consortium V1 UI

## Architecture

`ConsortiumView` is a normal top-level Production Zero destination. It uses `ConsortiumService` for gameplay mutations and the current PZ chassis/recessed-surface hierarchy, Safety Yellow actions, and progression green.

The workspace has two root states:

- No Consortium: compact introduction, search/policy directory, join/application/invitation states, and the create flow.
- Member: identity/XP header and exactly four sections—Overview, Contracts, Members, and Progression.

## Player flows

- Directory rows expose level, membership/capacity, policy, minimum level, and an explained action/passive state. Search, filter, and scroll values survive refreshes.
- Create uses an embedded in-app modal with policy guidance and a validated plain numeric minimum-level field.
- Overview focuses on Consortium status and recent activity; Daily/Weekly gameplay lives in Contracts.
- Before Start, Daily has three and Weekly four fixed product slots. Each slot opens the existing normal-Contracts `ContractProductPicker`, including canonical resource tiles, search, and sibling-duplicate disabling. Selection previews quantities and rewards; Start freezes the authoritative V1 requirements/rewards/member snapshot. Active operations retain aligned resource/progress rows, timer, personal contribution, and eligibility information.
- Contribution uses the shared `ResourceSelectionTile`, displays Global Storage and remaining quantities, clamps the amount to the valid maximum, and confirms removal from Global Storage.
- The compact top-aligned member roster shows ten rows at 1366×768 and scrolls to 50. Chairman-only promote/demote/remove controls, management invitation/application controls, settings, Leave, and separated destructive Disband behavior reflect domain permissions. Invite uses one identity lookup; the local directory resolves only company identities already known through Consortium membership, applications, or invitations. It never accepts a manually entered company level.
- Progression is a compact milestone list—not another Research canvas—with Complete/Current/Locked states and the final 50-member state.

## Refresh strategy

The two root workspaces are built once. Simulation callbacks no longer rebuild Consortium content unless its relevant domain signature changes; this fixes hover/focus flicker. An open embedded modal or product picker defers content reconstruction. Routine refreshes preserve the active tab, selected Contract, selected member, directory search/filter/scroll, and page scroll. The timer label updates in place.

## Shared components

The Directory and member headers use `MainTabHeader`. Secondary tabs inherit the global metallic `QTabBar` treatment. Primary/secondary/destructive buttons use the existing `deliverContractButton` / `resourcesButton` / `freightRemoveButton` styles; filters use `inventoryFilterChip`; search uses `supplySearch`. Product slots and the picker reuse normal Contracts' `contractProductSlot` and `ContractProductPicker`. Contribution retains `ResourceSelectionTile`. The roster is a purpose-built compact list because no existing PZ list exposes this exact role/action column layout. The Consortium XP bars reuse the company progression green palette with a thicker, readable Consortium geometry. Embedded modals remain local to the application; no native dialog is opened.

## Responsive/offscreen QA

The final focused 1366×768 audit is in `artifacts/consortium_final_playtest/`: Directory empty/populated, Create, Overview, Daily empty slots, canonical picker, Daily/Weekly selected previews, active Contract, Members 1/10, resolved Invite, and Progression. Additional captures show Members 50 and management settings.

## Final playtest-polish validation

- Consortium domain/UI tests: 26 passed.
- Directly affected shared Contracts, Global Storage, UI foundation, and resource-asset tests: 42 passed.
- All 13 requested final states and the two extra roster/management states were recaptured at 1366×768 and visually checked.
- The local company-identity resolver is intentionally limited to identities already known in current Consortium data; it does not fabricate a global player directory. This keeps Invite repository-authoritative within the V1 abstraction.
- The full suite and long simulations were not rerun for this UI-only checkpoint.

## Files

- `src/production_zero/ui/consortium_view.py`
- `src/production_zero/ui/main_window.py`
- `src/production_zero/ui/theme.py`
- `src/production_zero/ui/empty_state.py` (optional icon suppression)
- `scripts/capture_consortium_v1.py`
- `tests/test_consortium_ui.py`
- `tests/test_factory_ui.py` (top-level navigation expectation)

## Deferred

No chat, presence simulation, Events, Shared Research/upgrades, warehouse/bank, trading, PvP, custom roles/permissions, profile system, leaderboard expansion, server browser, or decorative coming-soon UI was added.

## Historical V1 validation results

- Consortium domain/UI plus directly affected persistence, Contracts, Global Storage, Communications, and shared UI tests: 63 passed / 0 failed / 0 skipped in 4:44.01.
- Full suite before updating its exact tab-sequence expectation: 932 passed / 4 failed / 0 skipped in 45:40.16. The Consortium-caused navigation expectation then passed in the 18-test final follow-up (18 passed / 0 failed / 0 skipped in 7.58s). The other three full-suite failures are unchanged from baseline: ticker append positioning and the two offscreen Research hover-image assertions.
- Nine required offscreen captures were generated and visually inspected at 1366×768. No application-level horizontal scroll, clipped tabs, clipped primary action, or unreadable dialog/resource text remains.
