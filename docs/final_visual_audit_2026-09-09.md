# Production Zero — Final Visual / UI / UX Quality Audit

**Audit date:** 2026-09-09\
**Build assessed:** current working-tree runtime\
**Review standard:** paid/commercial Early Access PC title\
**Method:** deterministic Qt offscreen captures only; no normal GUI launch and no persistent game-state changes

## 1. Executive summary

Production Zero now has a coherent and recognizable visual identity. The industrial chassis, dark operational surfaces, pale work areas, hazard markings, yellow primary actions, card frames, and compact technical typography form a consistent product language across most of the game. Market, Leaderboard, Factory, Used In, and the populated Supply views are credible commercial Early Access screens. The Resources / Factory / Energy split also reads as one deliberate system rather than three unrelated interfaces.

The current build is nevertheless **not visually release-ready**. Two visible defects meet the audit's Severity A definition:

1. Resources and Energy display a negative unlock price (`$-60`) for Slot 02. This is visible at both mandatory resolutions and reads as a broken economy/UI value.
2. Drilling Rig and Harvester render with blank art wells in the Resources card-selection drawer, despite rendering correctly in Inventory and Supply. This makes two of the three new Primary Production families appear broken at the exact point where the player installs them.

The build also exposes a `Dev` tab, retains placeholder-like global-header copy, uses inconsistent `EXTRACTION` versus `PRIMARY PRODUCTION` terminology, hides Inventory filters beyond the compact viewport without a clear affordance, and places the Crafting confirmation action below the initial 1366×768 fold.

The recently polished expansion-track presentation itself is substantially improved: `EXPANSION`, the track identifier, and the yellow `UNLOCK` action now form a clear and consistent hierarchy. That previous presentation weakness is **resolved**, apart from incorrect cost data and weak disabled-state differentiation.

## 2. Overall score

**3.4 / 5**

This is a credible Early Access presentation in broad visual language, but the two conspicuous defects in the newly promoted production flow, together with several product-facing remnants, pull the build below a safe commercial threshold.

## 3. Commercial Early Access verdict

**NOT READY**

The underlying presentation is close to a solid Early Access baseline, but missing card art and a negative purchase price are immediately visible defects in a core system. They should not appear in commercial store screenshots or a player-facing build.

**Would the UI itself create a negative first impression on Steam today? YES.** The general art direction is strong, but a buyer encountering `$-60`, two blank machine illustrations, a `Dev` navigation tab, and placeholder status copy could reasonably conclude that the build was not packaged or visually verified for release.

## 4. Severity A findings

### A-01 — Resources and Energy show a negative Slot 02 unlock price

- **Where:** Resources → Site 1 → Sector 01 → S02; Energy → Plant 1 → Block 01 → S02.
- **Observed:** `$-60` at 1366×768 and 1920×1080, in both affordable and zero-cash captures.
- **Impact:** obvious invalid commercial presentation; it also makes purchase intent impossible to interpret reliably.
- **Evidence:** `boards/resources_compact_1366x768.png`, `boards/energy_desktop_1920x1080.png`, and the corresponding `states/*_unaffordable_*` captures.
- **Runtime corroboration:** `factory_slot_unlock_cost()` in `src/production_zero/core/state.py` calculates against the Factory-wide starting-slot constant. The split boards start at one slot, allowing the second-slot formula to become negative. `UnlockHallSlot` spends that returned value in `src/production_zero/core/commands.py`.

### A-02 — Drilling Rig and Harvester art is blank in the Resources card-selection drawer

- **Where:** Resources → empty slot → Card Selection.
- **Observed:** Extractor renders normally; Drilling Rig and Harvester retain only their colored art-well backgrounds. The machine illustration is absent at both resolutions.
- **Impact:** two of three flagship Primary Production families appear to have missing assets during installation.
- **Scope:** the source assets and generic card renderer are not globally broken. Drilling Rig and Harvester render correctly in Inventory and Supply. The defect is isolated to the production-board selection-card path.
- **Evidence:** `art/primary_board_selection_art_1366x768.png`, `art/primary_board_selection_art_1920x1080.png`; compare with `art/all_card_families_*.png`.
- **Runtime corroboration:** `FactoryCardSelectionTile` in `src/production_zero/ui/factory_view.py` passes `definition.name.lower()` as its art family. That produces `drilling rig` and `harvester`, while the raster lookup keys are `drilling` and `agriculture`.

## 5. Severity B findings

### B-01 — A player-facing `Dev` tab is present in every captured screen

The tab is visually equal to normal product navigation and strongly signals an internal build. `DEVELOPMENT_MODE` defaults on in `src/production_zero/config.py`, and `MainWindow` adds the tab when it is true. This audit does not assume packaging will override it; the exact assessed runtime exposes it.

### B-02 — Inventory filter controls disappear beyond the 1366 px viewport without a clear affordance

The right side of the Sort group is cut after `RARITY`, with further options offscreen. The strip is horizontally scrollable, so the actions are not proven inaccessible, but the screenshot gives no obvious continuation cue or scrollbar. Filter discoverability is below commercial quality at the mandatory compact target.

### B-03 — The main Crafting action begins below the initial 1366×768 fold

In the ready state, `Craft Card` is only partially visible at the bottom. The workspace can scroll and remains usable, so this is not Severity A, but the confirmation checkbox and primary action should read as one complete decision zone on first view.

### B-04 — Unaffordable expansion and build actions retain too much of the enabled yellow treatment

At `$0`, the global `EXPAND $250`, board build button, and `UNLOCK $750` actions remain visually close to enabled primary actions; only text/contrast is reduced. The zero-cash state does not communicate disabled status decisively enough, particularly next to the always-yellow build-slot cards.

### B-05 — The global header contains placeholder-like copy

`GLOBAL OPERATIONS` followed by `READY FOR FACTORY-WIDE SIGNALS` looks like a future-feature placeholder rather than useful live status. It occupies premium space on every screen and reinforces a development-build impression.

### B-06 — Freight's facility purchase action is labeled `BUILD SITE`

The Freight sidebar calls the area `FACILITIES` and the active unit `GARAGE 1`, but its purchase action says `BUILD SITE ($1000)`. `Site` is now the Resources-board unit, so this is a particularly visible terminology collision after the split.

### B-07 — `EXTRACTION` remains in Charts and Market filters

Inventory, Packs, Production Guide, and new-board copy use `PRIMARY PRODUCTION`, while Charts and Market still label the stage `EXTRACTION`. The mixed terminology makes the new family taxonomy feel incompletely propagated.

### B-08 — Production Guide status copy truncates repeatedly

Resource tiles show strings such as `UNLOCKED · FAMILY MASTE...`. The truncation is systematic at 1366×768 and remains visually cramped at 1920×1080. The status is important progression information, not optional flavor text.

### B-09 — Energy's wide-screen composition feels unfinished

At 1920×1080, one five-slot block and two shallow expansion strips occupy the top third while most of the operational chassis is empty. Removing Guide/Resources controls did not create a header problem, but the overall page reads like a Factory clone with content removed rather than a fully resolved sparse board.

## 6. Severity C findings

### C-01 — The global command deck consumes disproportionate compact-window height

The header and main navigation occupy roughly the upper quarter of 1366×768 before screen-specific content begins. It is visually strong but makes every dense workspace more dependent on scrolling.

### C-02 — Wide Inventory states are visually under-filled

With a starter collection, three cards sit at the far left of a very large pale canvas. The empty space is functional growth capacity, but a modest sparse-state composition would look more intentional.

### C-03 — Charts uses large row cards for very little visible information

At 1366×768 only two complete resource rows are visible. The design is clean, but the density is lower than Market and forces excessive scrolling for a browser/analytics screen.

### C-04 — Packs and Common Supply become narrow content islands at 1920×1080

The layouts remain readable, but the populated pack pair and five Common Supply cards leave a large unused right/bottom field. This is acceptable Early Access roughness, though not maximally polished responsive composition.

### C-05 — Secondary microtype is very small at 1366×768

Global navigation, market row metadata, and some card footers remain technically readable but demand effort at native compact resolution. The display font is effective for headings and less effective for dense secondary data.

### C-06 — Unit-count grammar is mechanically pluralized

Sidebars show strings such as `1 sectors` and `1 blocks`. This is minor, but it is repeated prominently in the new boards.

### C-07 — Horizontal continuation on production tracks is understated

At 1366×768 the next slot is intentionally clipped to indicate more content, but the scrollbar/continuation cue is faint against the chassis. The interaction remains available.

## 7. Severity D / optional observations

- Resources, Factory, and Energy could receive slightly more differentiated secondary accents or microcopy, but they should retain their shared V2 grammar.
- Energy does not need an artificial Production Guide or resource drawer solely to fill space; its composition should be solved without adding irrelevant controls.
- Packs' empty state could carry more authored atmosphere, but the current centered message is clear and professional enough.
- Leaderboard's large empty middle field at 1920×1080 is calm rather than broken. Additional decoration is optional and should not compete with rankings.

## 8. Per-screen score table

| Screen / state | Score | Assessment |
|---|---:|---|
| Resources board | 2.7 | Strong shared chassis, but negative S02 price is a blocker. |
| Factory board | 4.0 | Clear hierarchy, strong operational rhythm, good action placement. |
| Energy board | 3.1 | Negative S02 price plus unresolved wide-screen sparsity. |
| Freight | 3.7 | Strong board presentation; `BUILD SITE` terminology is inconsistent. |
| Inventory | 3.5 | Excellent card presentation; compact filter overflow lacks affordance. |
| Crafting workspace | 3.3 | Understandable conversion flow; compact primary action sits below fold. |
| MK Upgrade workspace | N/A | No runtime workspace exists in the current build; only legacy QSS selectors remain. |
| Charts | 3.5 | Clean and consistent, but oversized rows and low information density. |
| Market | **4.3** | Best overall hierarchy, density, icon use, filtering, and event emphasis. |
| Contracts | 3.9 | Clear three-column cadence and reward hierarchy; scrolling is expected. |
| Industrial Supply — Daily | 3.9 | Attractive category split and readable card commerce. |
| Industrial Supply — Common | 3.8 | Strong cards and filters; sparse on wide screens. |
| Packs — empty | 3.8 | Clear, calm, intentional empty state. |
| Packs — populated | 4.0 | Distinct pack identity and excellent centered hierarchy. |
| Packs — reveal/result | 3.8 | Clear reward result and CTA; motion feel was not assessable from stills. |
| Leaderboard | 4.1 | Strongest secondary-system screen; readable ranking and pinned player row. |
| Production Guide | 3.6 | Useful taxonomy and icon grid; repeated progression text truncation. |
| Used In | 3.9 | Clear dependency result grid with effective icon support. |
| Resources card selection | **2.3** | Weakest screen because two new machine families have blank art. |
| Resources production selection | 4.0 | Clear resource choice, strong icon rendering, good back/navigation hierarchy. |
| Factory card selection | 3.8 | Clean and readable, though sparse with starter inventory. |
| Factory production selection | 4.0 | Clear recipe-selection task and consistent drawer grammar. |

## 9. Category score table

| Category | Score | Summary |
|---|---:|---|
| Visual hierarchy | 3.8 | Major purposes and primary actions are usually obvious. |
| Consistency | 3.5 | Strong visual system, weakened by terminology and product-state remnants. |
| Typography | 3.4 | Characterful headings; truncation and compact microtype need attention. |
| Iconography | 4.0 | Resource/product icons are a major strength in actual UI sizes. |
| Interaction clarity | 3.2 | Negative cost, ambiguous disabled actions, and hidden filters are significant. |
| Responsive quality | 3.4 | Functional at 1366×768, but several workspaces depend too quickly on scrolling. |
| Commercial polish | 3.2 | Core language is commercial; blank art, `Dev`, and placeholder copy are not. |

## 10. Resources / Factory / Energy comparison

The three boards successfully communicate a shared operational platform:

- sidebars establish Site / Hall / Plant ownership;
- tracks consistently use Sector / Line / Block plates;
- build slots, locked slots, activity badges, metrics, and expansion strips use the same visual rules;
- primary actions remain yellow and immediately identifiable.

Purpose differentiation is sufficient at a glance. Resources shows a `RESOURCES` drawer control and Primary Production flow; Factory exposes `PRODUCTION GUIDE` and `RESOURCES`; Energy omits both. The omission does **not** create awkward header dead space. The larger issue is the Energy page's vertical composition at 1920×1080, where the reduced content leaves most of the chassis unused.

Resources feels more deliberate than a simple renamed Factory because its one-slot start, Sector terminology, card family, and resource-selection flow materially change the task. That positive result is undermined by the selection-card artwork defect.

### Expansion UI conclusion

The polished expansion treatment resolves the former hierarchy weakness. `EXPANSION` is now dominant enough, the track identifier is appropriately secondary, and the `UNLOCK $price` button aligns consistently across the three boards. Compact behavior is structurally sound. Remaining defects are not failures of the new composition itself:

- Slot 02 cost data is wrong on Resources and Energy.
- Disabled/unaffordable buttons retain too much enabled yellow emphasis.

## 11. Resource/product icon assessment

The new raster resource/product set is one of the strongest parts of the build.

- Market icons remain recognizable at approximately 24–32 px and make long lists scannable.
- Production Guide icons use distinctive silhouettes and varied materials without losing family coherence.
- Used In renders more complex manufactured products legibly at small size.
- Crafting material icons remain identifiable inside compact orange selection tiles.
- Centering and padding are broadly consistent; no accidental opaque backgrounds or obvious edge clipping were found in the inspected contexts.

The weakest context is Charts, not because the icons fail, but because the surrounding row design gives a very large surface to a small icon and minimal data. At true small sizes, pale mineral icons such as limestone/quartz have lower contrast against light wells than the ore and manufactured-product icons, but remain recognizable.

## 12. Machine/card artwork assessment

The generic card renderer is visually strong. Card title, rarity, art well, functional output, status, and quantity form a stable hierarchy across Inventory, Supply, Packs, and selection views.

- **Extractor:** strong silhouette and good fit.
- **Drilling Rig:** readable and well-centered in Inventory/Supply; broken only in the Resources selection-card path.
- **Harvester:** final transparent artwork is crisp, centered, and free of checkerboard/opaque-background artifacts in Inventory, Supply, and pack results; broken only in the Resources selection-card path.
- **Processor / Fabricator / Assembler:** consistent industrial detail and stronger perceived quality than older symbolic treatments.
- **Energy:** coherent family, though Solar and Wind use much brighter wells than fossil/nuclear cards; the contrast is purposeful and still reads as one system.
- **Freight:** Aircraft, Ship, Train, and Truck silhouettes remain readable at card size and fit the shared card frame well.

Machine naming is not fully consistent across contexts: Inventory uses `AIRCRAFT`, `SHIP`, `TRAIN`, and `TRUCK`, while Supply uses `CARGO AIRCRAFT`, `CARGO SHIP`, `FREIGHT TRAIN`, and `FREIGHT TRUCK`. This is not severe enough to impede use, but terminology should eventually be normalized.

## 13. Compact 1366×768 assessment

The application does function at 1366×768: no normal major screen was found with a proven inaccessible core action, and board, list, and drawer scroll areas generally preserve access. The target is not yet consistently polished, however.

Highest-impact compact issues:

1. Inventory's filter strip hides controls without an obvious continuation cue.
2. Crafting's confirmation/action zone begins below the first viewport.
3. The global deck and navigation consume substantial vertical space.
4. Production Guide progression status truncates.
5. Production tracks rely on a faint horizontal continuation cue.
6. Dense Market and card-footer microtype is close to the lower comfortable reading limit.

## 14. 1920×1080 assessment

At 1920×1080, clipping and filter overflow largely disappear. Factory, Market, Contracts, Leaderboard, Production Guide, Used In, and the full card-family Inventory capture all benefit materially from the extra space.

Wide-screen weaknesses are primarily compositional rather than functional:

- Energy leaves most of its chassis unused.
- Starter Inventory, Packs, and Common Supply appear as small content islands.
- Charts remains vertically inefficient despite the larger viewport.

The two Severity A defects persist unchanged at 1920×1080; they are not compact-layout artifacts.

## 15. Cross-screen consistency assessment

The global shell is highly consistent, but that consistency amplifies both strengths and unfinished elements: the excellent command-deck identity appears everywhere, as do the placeholder status copy and `Dev` tab.

Resources / Factory / Energy / Freight share a convincing operational vocabulary. Freight is visually compatible but terminologically behind the new split. Inventory / Supply / Packs use the same card renderer effectively; Packs feels the most authored of those sparse-state layouts. Charts / Market / Leaderboard share pale control decks over dark data canvases, but Charts is visibly less information-efficient. Production Guide / Chain / Used In form a coherent drill-down sequence with reliable Back navigation and repeated icon language.

No major screen looks wholly from an obsolete UI generation. The remaining inconsistency is concentrated in text propagation, responsive density, and a few isolated render/data defects rather than a need for redesign.

## 16. Top 10 highest-value remaining visual improvements

1. Correct the negative Resources/Energy Slot 02 price and verify the entire split-board cost sequence.
2. Route Drilling Rig and Harvester selection cards through the same explicit machine-art family mapping used elsewhere.
3. Ensure commercial builds never expose the `Dev` tab.
4. Replace or remove the placeholder `GLOBAL OPERATIONS / READY FOR FACTORY-WIDE SIGNALS` module.
5. Make all Inventory filter/sort choices discoverable at 1366×768 without invisible horizontal continuation.
6. Keep Crafting's confirmation and primary CTA together within the initial compact viewport, or make the need to scroll unmistakable.
7. Standardize `PRIMARY PRODUCTION` terminology in Charts and Market.
8. Rename Freight's `BUILD SITE` action to match Freight's facility/garage vocabulary.
9. Give unaffordable actions a decisively non-primary disabled treatment across header and boards.
10. Resolve Production Guide progression-status truncation, then tune Energy/Charts wide-screen density without changing the shared design language.

## 17. Things that should NOT be changed

- Do not split Resources, Factory, and Energy into unrelated visual systems; their shared V2 grammar is a strength.
- Do not remove the industrial chassis, hazard language, or yellow primary-action convention.
- Do not redesign card dimensions or the established machine-art fit logic; it works across normal card contexts.
- Do not replace the new resource/product icon set wholesale; it is already commercially credible.
- Do not add irrelevant Guide/Resources controls to Energy merely to fill space.
- Do not eliminate scrolling from Contracts or long Guide/Used In lists; the current scroll model is appropriate.
- Do not weaken the new `EXPANSION` hierarchy. It is a resolved improvement.
- Do not make sparse empty states busy for decoration's sake.

## 18. Screenshot/contact-sheet paths

All paths are relative to the repository root.

### Native capture directories

- `artifacts/final_visual_audit_2026-09-09/boards/`
- `artifacts/final_visual_audit_2026-09-09/major/`
- `artifacts/final_visual_audit_2026-09-09/drawers/`
- `artifacts/final_visual_audit_2026-09-09/states/`
- `artifacts/final_visual_audit_2026-09-09/art/`

**Native screenshots:** 64\
**Contact sheets:** 9\
**Total PNG artifacts:** 73

### Required contact sheets

- `artifacts/final_visual_audit_2026-09-09/contact_sheets/all_major_screens_1366x768.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/all_major_screens_1920x1080.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/resources_factory_energy_comparison.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/resource_icon_heavy_screens.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/card_heavy_screens.png`

### Additional cross-screen sheets

- `artifacts/final_visual_audit_2026-09-09/contact_sheets/operations_cross_screen.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/commerce_cards_cross_screen.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/analytics_cross_screen.png`
- `artifacts/final_visual_audit_2026-09-09/contact_sheets/guide_used_in_cross_screen.png`

### Coverage and limitations

- Every available major runtime screen was captured at 1366×768 and 1920×1080.
- Representative card-selection, production-selection, resource-summary, crafting disabled/ready, Inventory empty, Packs empty/populated/result, expansion affordable/unaffordable, Guide, Chain, and Used In states were captured.
- Pack result captures use a real deterministic `OpenPack` result with the animation advanced to its final static state. They assess the result layout, not animation timing or feel.
- Hover motion and focus transitions cannot be judged fully from still offscreen captures. Static selected/disabled treatments were inspected.
- No MK Upgrade runtime screen is available to capture. `src/production_zero/core/mk_upgrades.py` and its tests are absent in the current tree, while legacy `mkUpgrade*` QSS selectors remain in `src/production_zero/ui/theme.py`. Whether the feature is intentionally retired is an unresolved product question.

## 19. Final release-readiness conclusion

Production Zero has crossed the threshold from a collection of functional screens into a cohesive game UI. The strongest evidence is that Market, Leaderboard, Factory, Supply, Inventory cards, Packs, Production Guide, and Used In all feel related without being identical. The new icon set and transparent Harvester artwork materially improve perceived quality, and the expansion-track presentation is now clear.

The current exact build should still not be shown as a finished commercial Early Access UI. Fixing the two Severity A defects, removing product-facing development remnants, and completing the compact terminology/interaction pass would likely move the presentation into the **3.8–4.0 / 5, READY** range without a redesign.

**Unresolved product question:** Is MK Upgrade intentionally retired in favor of rarity crafting? If yes, remove the stale expectations and legacy styling in a future implementation task. If no, its missing runtime entry point is a separate release-scope issue. This audit makes no code change either way.
