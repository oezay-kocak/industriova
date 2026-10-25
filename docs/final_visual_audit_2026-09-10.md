# Production Zero — Final Visual UI Audit

**Audit date:** 2026-09-10\
**Workspace:** current working tree after the reported clean `compileall` and `781 passed` validation\
**Scope:** visual/UI inspection only\
**Method:** native Qt offscreen rendering at 1366×768 and 1920×1080; no normal GUI launch; no gameplay regression tests; no runtime, UI, test, asset, configuration, progression, economy, or save changes

## Executive summary

Production Zero now presents as a coherent commercial management game rather than a prototype. The Resources / Factory / Energy boards have a consistent operational rhythm, Freight reads as the same product family without losing its facility identity, and the Market, Industrial Supply, Inventory, Crafting, Packs, Production Guide, Chain Inspector, and Unlock Tree share a recognizable industrial visual language.

The fresh audit found no player-reachable Severity A or Severity B issue. All observed shortcomings are cosmetic refinements: the Unlock Tree's default overview is visually busy, dense long chains require player zoom for comfortable reading, Packs remains very sparse on wide screens, low-count card selection leaves a large unused result surface, and the global Production Network module is less informative than its neighboring header modules.

**Overall UI score: 4.4 / 5.0**\
**Early Access verdict: READY**\
**Steam first-impression verdict: YES**

The current UI is visually credible for a paid Early Access release. Nothing captured looked broken, unusable, or materially unfinished.

## Audit method and reachability guard

The capture set was generated from a fresh `MainWindow(charts_enabled=False)` for each resolution. Normal main-tab controls, visible Back buttons, visible build slots, visible selection cards, Production Guide tiles, the Unlock Tree button, stage chips, search input, and Freight facility tree items were activated through Qt mouse/keyboard events.

Populated states were built only as legitimate in-memory player fixtures through the normal command layer (`AddCard`, `InstallCardInHall`, `SelectMachineProduction`, `UnlockProductionSlot`, `BuildFreightFacility`, `InstallFreightCard`, and `AssignFreightCard`). No save was loaded or written. No private view-opening method was invoked to bypass interaction gating.

The prior synthetic Factory Production Selection empty state was deliberately excluded. In the current runtime, `FactoryV2MachineCard.mousePressEvent()` only emits `production_change_requested` from the resource/recipe control area when `_production_change_available()` is true. With no compatible unlocked option, the card displays `NO RECIPE` and no player Production Selection route exists. This audit therefore does not repeat or score the withdrawn false positive.

Charts is disabled by default through `CHARTS_ENABLED` in `src/production_zero/config.py` and is not added to the normal tab set by `MainWindow`; it was not captured or scored.

## Capture coverage

| Area | Player-reachable states inspected |
|---|---|
| Resources | early board, active Extractor, card selection |
| Factory | early board, populated active/later board, card selection |
| Energy | active generation/expansion, card selection |
| Freight | Garage with active shipment, Rail Station, Harbor/Port, Airport/Airfield |
| Inventory | Cards with no selection, available scrap-eligible card selected, Crafting target/material workspace |
| Market | normal dense market table with icon wells and controls |
| Contracts | Daily, Weekly, and regular contract columns |
| Packs | empty and populated unopened-pack states |
| Industrial Supply | Common Machine, Common Energy, Daily |
| Leaderboard | normal ranking view |
| Production Guide | default browse state |
| Chain Inspector | Iron Ore, Steel, and Microchip |
| Unlock Tree | default CURRENT focus, selected trace, search plus stage filter |

## Screen scores

| Screen | Score | Assessment |
|---|---:|---|
| Resources | 4.4 | Strong Site/Sector hierarchy, clear expansion tracks, and consistent header alignment. |
| Factory | 4.5 | Mature operational board with strong machine-card rhythm and readable active/later state. |
| Energy | 4.3 | Shared board language is preserved; compact capacity remains visually intentional. |
| Freight | 4.4 | Garage, Rail Station, Harbor, and Airport are visually consistent and easy to distinguish. |
| Inventory — Cards | 4.3 | Strong collection presentation and permanent Scrap workflow; compact overflow remains discoverable. |
| Inventory — Crafting | 4.5 | Clear materials-to-target flow, rarity-aware target presentation, and decisive result area. |
| Market | **4.6** | Strongest screen: excellent information density, hierarchy, icon wells, and row scanability. |
| Contracts | 4.3 | Clear three-column cadence and consistent action/reward hierarchy. |
| Packs | 4.1 | Shared empty/populated chassis is consistent, though wide layouts remain very sparse. |
| Industrial Supply | 4.5 | Polished commerce layout, left-aligned card grids, readable quantity controls, and clear categories. |
| Leaderboard | 4.2 | Clean, restrained, and readable; appropriately secondary to the operational views. |
| Production Guide | 4.4 | Strong taxonomy, compact filters, readable resource tiles, and clear Unlock Tree entry. |
| Chain Inspector | 4.4 | Compact summary, clear rate/Used In blocks, open canvas, clean connectors, and no obsolete zoom box. |
| Unlock Tree | **4.0** | Weakest reachable screen: functional and legible, but the default full-context view is visually busy. |

## Findings

### C-01 — Unlock Tree default focus is visually congested

- **Severity:** C
- **Screen:** Unlock Tree
- **Resolution:** 1366×768 and 1920×1080
- **Player-reachable path:** Factory → Production Guide → Unlock Tree
- **Exact issue:** the default CURRENT-focused canvas exposes a dense mesh of low-contrast background edges and several partial neighboring node columns at the viewport boundaries. The intended current nodes are readable, but the first scan is busier than the selected-trace and search states.
- **Why it matters:** Unlock Tree is the weakest first-impression surface in the audited build; the player must visually separate the current frontier from a large amount of context before taking action.
- **Recommended fix:** slightly reduce non-selected edge opacity in the default state and add a little more focus-region padding so the CURRENT cluster is framed without increasing minimum zoom or removing pan context.

### C-02 — Long Chain Inspector auto-fit reaches the typography comfort floor

- **Severity:** C
- **Screen:** Chain Inspector — Microchip
- **Resolution:** most visible at 1366×768; also present at 1920×1080
- **Player-reachable path:** Factory → Production Guide → Microchip tile
- **Exact issue:** fitting the entire long chain preserves all stages and connectors, but node labels and input lines become small enough that reading details requires mouse-wheel zoom.
- **Why it matters:** the overview is excellent for structure, but its default terminal state is less immediately readable than the simple and mid-complexity chains.
- **Recommended fix:** preserve the existing canvas, automatic fit, zoom limits, and card geometry; consider a slightly closer default fit for dense chains or a typography-aware fit margin that still shows the complete stage sequence.

### C-03 — Packs states remain under-composed on wide screens

- **Severity:** C
- **Screen:** Packs — empty and populated
- **Resolution:** 1920×1080, with a smaller effect at 1366×768
- **Player-reachable path:** Packs; populated state after receiving unopened packs from normal rewards
- **Exact issue:** the empty message and two-pack cluster occupy a small central portion of a very large pale content surface. The shared chassis is consistent, but its visual weight is much lighter than Inventory, Supply, or Market.
- **Why it matters:** the screen is clean and correct, yet it feels less authored on a large monitor than the surrounding commerce/reward views.
- **Recommended fix:** strengthen the empty-state/support hierarchy and use a bounded centered content region or restrained contextual decoration without changing pack-card dimensions.

### C-04 — Low-count card selection underuses the result chassis

- **Severity:** C
- **Screen:** Resources, Factory, and Energy card selection
- **Resolution:** most visible at 1920×1080
- **Player-reachable path:** Resources / Factory / Energy → click an empty unlocked slot
- **Exact issue:** when the player owns only one compatible card, a single small tile sits at the upper-left of a very large dark result surface.
- **Why it matters:** the layout remains usable and its left-aligned growth behavior is consistent, but the low-count state feels less deliberately composed than the full Supply and Inventory grids.
- **Recommended fix:** keep left alignment and existing card dimensions, but add a bounded result width, stronger result-count context, or a subtle low-count composition treatment.

### C-05 — Production Network header module remains visually under-instrumented

- **Severity:** C
- **Screen:** global command deck across all screens
- **Resolution:** 1366×768 and 1920×1080
- **Player-reachable path:** any normal player screen
- **Exact issue:** `3 UNITS · 0 MODULES ONLINE` is useful, but it occupies only the lower edge of a relatively large dark module while Cash, Energy, Storage, and Level carry stronger icon/value structure.
- **Why it matters:** the module is not a placeholder, but it is the least finished-looking part of an otherwise polished global header.
- **Recommended fix:** add one compact live network indicator or rebalance the existing label vertically; do not add decorative data with no gameplay meaning.

## Severity summary

| Severity | Count | Release effect |
|---|---:|---|
| A | **0** | None |
| B | **0** | None |
| C | **5** | Optional cosmetic polish |

## Required release fixes

None. No player-reachable clipping, unusable control, broken layout, critical readability failure, major inconsistency, or obviously unfinished core screen was found.

## Optional polish priorities

1. Reduce default Unlock Tree connector noise and improve CURRENT-cluster framing.
2. Improve default long-chain legibility while preserving automatic fit and player zoom/pan.
3. Give Packs empty/populated states stronger large-screen composition.
4. Refine low-count production-board card-selection composition without changing card dimensions or left alignment.
5. Add restrained live information density to the Production Network header module.

## Recently changed area verification

- **Resources / Factory / Energy:** right-side header controls align consistently; Guide, Resources, Energy, and Revenue placement is stable; first tracks and expansion rows share the same rhythm; assignment drawers use the same mature chassis.
- **Freight:** Garage, Rail Station, Harbor, and Airport use consistent facility plates, slot cards, locked states, and sidebar navigation. The active shipment state remains readable.
- **Inventory:** Cards and Crafting share the revised header/subtab language. The Scrap footer remains permanently present, and available-card selection produces a clear Scrap action state.
- **Supply:** Common Machine, Common Energy, and Daily preserve left-aligned grids, readable purchase actions, and Market-quality control styling.
- **Packs:** empty and populated states use the same content chassis and header; remaining weakness is composition rather than inconsistency.
- **Market:** icon wells, event actions, filters, and dense rows retain the clearest hierarchy in the build.
- **Chain Inspector:** compact summary, Production Rate, Used In, stage titles, open canvas, and connector routing remain coherent. The former `- / % / + / FIT` control chassis is absent with no visible placeholder.
- **Unlock Tree:** default focus, trace highlighting, search focus, stage filters, and the compact top control bar are all present and player reachable.
- **Charts:** absent from the normal default player build and excluded from scoring.

## Release verdict

**Early Access: READY**\
**Steam first impression: YES**

The UI has a strong, recognizable identity and sufficient polish to support commercial screenshots. The five remaining findings are optional refinements, not release blockers.

## Screenshot artifacts

**Native screenshots: 60**

- 30 at 1366×768: `artifacts/final_visual_audit_2026-09-10/native/1366x768/`
- 30 at 1920×1080: `artifacts/final_visual_audit_2026-09-10/native/1920x1080/`

**Contact sheets: 5**

- `artifacts/final_visual_audit_2026-09-10/all_major_1366x768.png`
- `artifacts/final_visual_audit_2026-09-10/all_major_1920x1080.png`
- `artifacts/final_visual_audit_2026-09-10/operations_resources_factory_energy_freight.png`
- `artifacts/final_visual_audit_2026-09-10/inventory_supply_packs_market.png`
- `artifacts/final_visual_audit_2026-09-10/guide_chain_unlock_tree.png`

## Audit limitations

This was a terminal-state visual inspection. Static captures can assess layout, hierarchy, text, iconography, selection state, responsive composition, and post-navigation zoom/pan framing, but not animation timing or subjective input feel. Those were intentionally outside this visual-only pass. No synthetic defensive state was scored.
