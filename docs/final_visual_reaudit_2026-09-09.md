# Production Zero — Final Visual / UI / UX Re-Audit

**Audit date:** 2026-09-09\
**Build assessed:** current working-tree runtime after `final_visual_audit_fix_pass_2026-09-09`\
**Review standard:** paid/commercial Early Access PC game on Steam\
**Method:** deterministic Qt offscreen rendering only; 24 required states at 1366×768 and 1920×1080; runtime values and asset mappings independently inspected; normal GUI not launched; no saves changed

## 1. Executive summary

The current build meets a strong commercial Early Access UI baseline. The two previous release blockers are visibly and runtime-wise resolved: Resources/Energy prices are positive and monotonic, and Extractor, Drilling Rig, and Harvester render as three distinct transparent artworks in Resources Card Selection. The normal shell contains no Dev tab, core compact interactions are available at 1366×768, disabled actions read as disabled, and the split production boards now feel like a coherent family.

The result is not release-grade perfection. The early-game Factory Production Selection state is still visibly under-authored: it presents a very small, low-contrast sentence in a large otherwise empty dark surface. Dense secondary text also remains close to the comfortable reading floor, and several sparse wide states could use more authored composition. None of these remaining issues blocks a gameplay action or creates a broken first impression.

**Independent answer to the primary question:** No. If this exact build appeared on Steam today, the UI itself would not make the product look unfinished or unprofessional. It would look like a credible, visually distinctive Early Access management game with a limited number of remaining polish issues.

## 2. Overall visual score

**4.1 / 5**

This score was assigned from the current captures, not by mechanically incrementing the previous 3.4. The improvement is supported by the visible removal of both blockers, all nine former Severity B faults, and most former minor faults.

## 3. Commercial Early Access verdict

**READY**

The UI is suitable for a commercial Early Access build. It has a coherent visual identity, reliable cross-screen structure, legible core actions at the mandatory compact target, and no observed player-facing corruption or invalid values.

## 4. Steam first-impression verdict

**NO**

The UI would not itself create a negative first impression. The industrial command deck, card art, operational boards, Market, Crafting, Supply, and Packs presentation communicate an authored product rather than a prototype. The remaining weaknesses become apparent during closer inspection rather than in an immediate store-page glance.

## 5. Severity A findings

**Count: 0**

No inaccessible core action, broken render, invalid economy value, unreadable essential information, major clipping, or visual corruption was found in the 48 native captures.

## 6. Severity B findings

**Count: 1**

### B-01 — Factory Production Selection has an under-authored empty state

- **Where:** Factory → installed Processor → Select Recipe, before the first recipe is unlocked.
- **Observed:** the otherwise empty drawer contains only a small, low-contrast sentence: `No unlocked production options · Open Production Guide for the next requirement`.
- **Why this is Severity B:** the explanation is correct, but the presentation looks like fallback copy placed into a finished shell. It lacks a clear empty-state hierarchy and a direct visual affordance to open the Guide.
- **Impact:** no action is inaccessible, but a core early-game flow looks less commercially finished than the surrounding UI.
- **Evidence:** `native/1366x768/06_factory_production_selection.png` and `native/1920x1080/06_factory_production_selection.png`.

## 7. Severity C findings

**Count: 4**

### C-01 — Dense secondary microtype remains near the comfort floor

Market metadata, Charts values, Guide statuses, card footers, and some filter labels are readable at native 1366×768, but they demand more attention than the primary hierarchy. This is no longer a broad readability failure; it is a remaining refinement issue.

### C-02 — Some sparse wide result/selection views underuse their authored canvas

Resources/Factory Card Selection and Used In place a small valid result group at the upper left of a large surface at 1920×1080. This does not apply to the intentionally left-aligned Inventory decision and does not impair use, but the responsive composition feels less authored than Market, Supply, or Packs.

### C-03 — The Packs empty-state support copy is visually too quiet

`NO UNOPENED PACKS` is clear, but the explanatory lines are very small inside a large light field at both resolutions. The state is professional enough, yet a modest increase in hierarchy would improve clarity and atmosphere.

### C-04 — The live Production Network module remains visually under-instrumented

The former placeholder wording is gone and the unit/module count is useful, but the module reserves a comparatively large dark panel for one small line of information. It no longer reads as broken; it simply trails the density and finish of the Cash, Energy, Storage, and Level modules.

## 8. Severity D observations

- Slightly stronger board-specific secondary accents could further distinguish Resources, Factory, and Energy, but their shared V2 language should remain dominant.
- Freight card names remain shorter in Inventory and more descriptive in Supply. Both are contextually understandable; normalization is optional unless a canonical naming policy is chosen.
- Animation timing and tactile feel cannot be fully graded from deterministic terminal-state captures. The Packs reveal result itself is well composed.

## 9. Per-screen score table

| Screen / state | Score | Current assessment |
|---|---:|---|
| Resources | 4.2 | Clear Site/Sector hierarchy, positive costs, strong track rhythm. |
| Resources Card Selection | 4.1 | Three distinct machine families render correctly; sparse on wide screens. |
| Resources Production Selection | 4.2 | Strong icon grid, search, category rail, and Back hierarchy. |
| Factory | 4.2 | Mature operational cadence and clear Guide/Resources actions. |
| Factory Card Selection | 4.1 | Consistent cards and filtering; starter set leaves wide dead space. |
| Factory Production Selection | **3.6** | Weakest screen; correct but visually unfinished empty state. |
| Energy | 4.0 | Sparse by design but now vertically balanced and clearly structured. |
| Freight | 4.1 | Consistent operational presentation and corrected facility vocabulary. |
| Inventory | 4.0 | Strong cards; compact filter continuation is visible and usable. |
| Crafting | **4.4** | Strongest screen; conversion flow, target, confirmation, and CTA are immediately legible. |
| Charts | 3.9 | Improved density and consistent filtering; microtype remains compact. |
| Market | 4.2 | Excellent density, event emphasis, sorting, and scan-friendly rows. |
| Contracts | 4.1 | Clear three-column cadence with strong action/reward hierarchy. |
| Industrial Supply — Daily | 4.2 | Attractive category split and effective commerce presentation. |
| Industrial Supply — Common | 4.1 | Centered sparse row reads intentionally at both sizes. |
| Packs — empty | 3.9 | Clear state, but explanatory hierarchy is too quiet. |
| Packs — populated | 4.1 | Distinct packs, centered composition, clear Open actions. |
| Packs — reveal/result | 4.3 | Strong reward lineup and unmistakable collection CTA. |
| Leaderboard | 4.1 | Clean rankings, pinned player row, disciplined density. |
| Production Guide | 4.0 | Compact statuses no longer truncate repeatedly; good taxonomy. |
| Used In | 3.8 | Clear dependencies and icons; sparse wide composition. |
| Locked/expansion states | 4.2 | Costs, sequence, labels, and continuation cue are understandable. |
| Unaffordable/disabled states | 4.2 | Neutral disabled styling is decisive without harming label clarity. |
| Global shell/header/navigation | 4.1 | Strong identity, compact enough at 1366; live network panel could carry more information. |

## 10. Category score table

| Category | Score | Assessment |
|---|---:|---|
| Visual hierarchy | 4.3 | Screen purpose and primary actions are usually immediate. |
| Cross-screen consistency | 4.3 | Shared chassis, cards, controls, and vocabulary form one product. |
| Typography | 3.9 | Distinctive and disciplined; some dense secondary text remains small. |
| Resource/product iconography | 4.2 | Recognizable, centered, and consistent at actual UI sizes. |
| Machine/card artwork | 4.4 | High-quality family art and stable card presentation across contexts. |
| Spacing/alignment | 4.0 | Strong compact layout; sparse wide states remain less resolved. |
| Compact-window quality | 4.1 | Core controls and actions remain visible/discoverable at 1366×768. |
| Information density | 4.0 | Market and Supply excel; empty/result views are less balanced. |
| Interaction clarity | 4.2 | Yellow primaries, neutral disabled actions, Back actions, and scroll cues read well. |
| Commercial polish | 4.0 | Clearly commercial Early Access quality, with one notable empty-state weakness. |

## 11. Previous Severity A verification

| ID | Re-audit result | Evidence |
|---|---|---|
| A-01 negative Resources/Energy slot prices | **VERIFIED RESOLVED** | Resources shows S02 `$120`, then `$210`, `$300`, `$390`, `$480`, `$570`, with later `$660`, `$750`, `$840` visible at 1920. Energy shows S02–S05 as `$120`, `$210`, `$300`, `$390`. Zero-cash captures retain the same valid labels while actions become disabled. Runtime `factory_slot_unlock_cost()` returns the same positive monotonic sequences. |
| A-02 blank/wrong Drilling Rig and Harvester art | **VERIFIED RESOLVED** | Resources Card Selection shows Extractor, Drilling Rig, and Harvester as three distinct, centered images at both resolutions. Runtime maps `MachineType.EXTRACTOR → extractor.png`, `DRILLING → drilling_rig.png`, and `AGRICULTURE → agriculture.png`; the fallback map is empty. All three files load as non-null alpha images with transparent corner pixels. |

No new cost-display or machine-art regression was observed.

## 12. Previous Severity B verification

| ID | Result | Re-audit evidence |
|---|---|---|
| B-01 Dev tab | **VERIFIED RESOLVED** | Exactly 11 normal tabs are visible; no Dev tab. `DEVELOPMENT_MODE` defaults off. |
| B-02 Inventory compact filters | **VERIFIED RESOLVED** | All filter groups are present at 1366×768 and a visible horizontal scrollbar communicates continuation. |
| B-03 Crafting CTA | **VERIFIED RESOLVED** | Confirmation zone and full `Craft Card` button are inside the initial 1366×768 viewport. |
| B-04 unaffordable buttons | **VERIFIED RESOLVED** | zero-cash Build/Develop/Unlock actions use muted neutral gray rather than enabled yellow. |
| B-05 global-header placeholder | **VERIFIED RESOLVED** | `PRODUCTION NETWORK` displays live unit/module counts; forbidden placeholder wording is absent. A minor density observation remains as C-04. |
| B-06 Freight terminology | **VERIFIED RESOLVED** | sidebar action reads `BUILD FACILITY ($1000)`; no `BUILD SITE` collision is visible. |
| B-07 Charts/Market stage terminology | **VERIFIED RESOLVED** | both use `PRIMARY PRODUCTION`. |
| B-08 Guide truncation | **VERIFIED RESOLVED** | statuses such as `UNLOCKED · MASTERED` and compact next requirements fit their tiles at both sizes. |
| B-09 Energy widescreen composition | **VERIFIED RESOLVED** | Block 01 and two expansion rows are vertically centered within the shared chassis. The page is sparse but structured, not broken. |

## 13. Previous Severity C verification

| ID | Result | Re-audit evidence |
|---|---|---|
| C-01 shell compact height | **VERIFIED RESOLVED** | board, drawer, filter, and CTA content retain useful first-viewport space at 1366×768. |
| C-02 Inventory sparse left alignment | **DEFERRED AS INTENDED / NOT PENALIZED** | left alignment is internally consistent and causes no usability problem. |
| C-03 Charts row density | **VERIFIED RESOLVED** | multiple rows and three columns are visible at 1366; four columns fit at 1920. |
| C-04 Packs/Common Supply wide composition | **VERIFIED RESOLVED** | Common Supply and pack groups are centered by their content, not stranded at the far left. |
| C-05 secondary microtype | **SUBSTANTIALLY RESOLVED** | targeted labels are readable, though dense data contexts remain a minor comfort issue recorded as current C-01. |
| C-06 singular/plural grammar | **VERIFIED RESOLVED** | captures show `1 slot · 1 sector`, `1 slot · 1 block`, and `6 slots · 2 lines`. |
| C-07 horizontal continuation | **VERIFIED RESOLVED** | a yellow right-edge chevron appears whenever the compact production track continues horizontally. |

## 14. Resources / Factory / Energy / Freight comparison

The four operational screens now read as a deliberate system:

- Resources, Factory, and Energy share the Site/Hall/Plant sidebar, Sector/Line/Block track, metrics, slot silhouettes, expansion strips, and yellow purchase language.
- Freight carries the same industrial framing and build-slot rhythm while retaining a facility-specific identity.
- Resources starts with one build slot and emphasizes resource assignment; Factory presents two lines and Guide access; Energy limits its row to five slots and omits irrelevant resource/Guide controls.
- At 1366×768, continuation is explicit and vertical scrolling remains available. At 1920×1080, more of each track appears without stretching card dimensions.

The shared rhythm is a strength and should be preserved. Energy is the sparsest board, but the current vertical balance prevents it from reading as a Factory page with content accidentally removed.

## 15. Resource/product icon assessment

Resource and product icons remain one of the UI's strongest systems at real render sizes.

- **Market:** small icons make dense rows quickly scannable; no clipping or accidental background was found.
- **Charts:** icons remain distinguishable despite compact row cards.
- **Production Guide:** ore, mineral, oil/gas, forestry, agriculture, and manufactured products remain recognizable across a large grid.
- **Used In:** complex products survive reduction and align consistently in result tiles.
- **Inventory/Crafting:** machine art and target cards remain crisp; material-selection surfaces preserve adequate padding.

Pale mineral silhouettes carry less contrast than saturated ore/product icons, but none became ambiguous or unreadable in the inspected contexts.

## 16. Machine/card artwork assessment

The normal card renderer is stable across Resources, Factory, Inventory, Supply, Packs, and Crafting.

- **Extractor:** correct tracked-extraction silhouette, centered with transparent surroundings.
- **Drilling Rig:** correct derrick artwork, distinct from Extractor, no fallback.
- **Harvester:** correct combine-harvester artwork, transparent background, no checkerboard or Extractor substitution.
- **Processor / Fabricator / Assembler:** coherent blue/orange/red family coding, consistent fit and title treatment.
- **Energy families:** all five cards are distinct; bright Solar/Wind wells and darker fuel plants remain visually coherent.
- **Freight:** Truck, Train, Ship, and Aircraft remain recognizable at Daily Supply and pack-result sizes.

Title fit, rarity color, art centering, card dimensions, and quantity/status placement are consistent. No blank art well was found in the captured player flows.

## 17. Compact 1366×768 assessment

1366×768 now meets the commercial target. No required screen loses a core action:

- Inventory filters expose their continuation mechanism.
- Crafting keeps confirmation and CTA visible.
- board slots, costs, expansion actions, and track continuation remain legible.
- Supply cards retain Buy actions and Packs retains Open/Collect actions.
- Guide and Used In preserve Back navigation and useful result density.

The main remaining compact weakness is secondary microtype in dense contexts. The Factory recipe-empty state is also too visually quiet, although its sentence is technically visible.

## 18. 1920×1080 assessment

At 1920×1080, the application scales by revealing more rows/columns rather than distorting established card dimensions. Market, Charts, Guide, Contracts, Inventory, and the operational tracks benefit strongly. Common Supply and Packs are centered, and Energy is vertically balanced.

Wide-screen weaknesses are compositional: sparse card-selection groups and Used In results sit in large canvases, and the command deck's Production Network panel is under-filled. These are polish opportunities, not evidence of a broken responsive layout.

## 19. Cross-screen consistency assessment

The build now uses a consistent visual grammar across all major systems: pale headers/control decks, dark operational/data surfaces, yellow primary actions, red industrial section accents, cyan/green telemetry, and stable card frames. Terminology is consistent where it matters: Primary Production, Site/Sector, Hall/Line, Plant/Block, and Facility.

Inventory, Supply, and Packs share card artwork without renderer drift. Charts, Market, and Leaderboard use related analytical surfaces while retaining clear roles. Production Guide and Used In form a coherent drill-down pair. No screen looks like an obsolete UI generation or a development-only utility.

## 20. Remaining highest-value improvements

1. Replace the Factory recipe-selection fallback sentence with an authored empty-state block containing a clear `OPEN PRODUCTION GUIDE` action.
2. Raise or simplify the smallest secondary typography in Market, Charts, Guide, and compact card footers without enlarging card geometry.
3. Improve sparse wide-state composition for card selection, Used In, and the Production Network module while preserving established left alignment and slot/card dimensions.

## 21. Things that should NOT be changed

- Do not redesign the shared Resources/Factory/Energy V2 board rhythm; it is now a major consistency strength.
- Do not center sparse Inventory merely for symmetry. Its left-aligned growth canvas is coherent and usable.
- Do not change established card dimensions, rarity frames, generic art-fit behavior, or yellow primary-action language.
- Do not add irrelevant Guide/resource controls or fake metrics to Energy just to fill space.
- Do not replace the resource/product icon set; it is already commercially strong at actual UI sizes.
- Do not over-densify the interface at the expense of the current clear hierarchy.

## 22. Screenshot and contact-sheet paths

**Native screenshots: 48**

- 24 × 1366×768: `artifacts/final_visual_reaudit_2026-09-09/native/1366x768/`
- 24 × 1920×1080: `artifacts/final_visual_reaudit_2026-09-09/native/1920x1080/`

**Contact sheets: 8**

- `artifacts/final_visual_reaudit_2026-09-09/all_major_1366x768.png`
- `artifacts/final_visual_reaudit_2026-09-09/all_major_1920x1080.png`
- `artifacts/final_visual_reaudit_2026-09-09/operations_comparison.png`
- `artifacts/final_visual_reaudit_2026-09-09/inventory_supply_packs_comparison.png`
- `artifacts/final_visual_reaudit_2026-09-09/analytics_comparison.png`
- `artifacts/final_visual_reaudit_2026-09-09/card_heavy_comparison.png`
- `artifacts/final_visual_reaudit_2026-09-09/resource_icon_heavy_comparison.png`
- `artifacts/final_visual_reaudit_2026-09-09/guide_used_in_comparison.png`

## 23. Final release-readiness conclusion

**Commercial Early Access visual/UI presentation: READY**

Production Zero's UI is now visually credible as a paid Early Access product. The fix pass removed the defects that previously made the build look unverified for release. The remaining one Severity B issue and four Severity C issues are bounded presentation refinements; they do not compromise access, correctness, or the overall first impression.

### Change comparison

| Audit | Score | Verdict | Severity A | Severity B | Severity C |
|---|---:|---|---:|---:|---:|
| Previous strict audit | 3.4 / 5 | NOT READY | 2 | 9 | 7 |
| Current re-audit | **4.1 / 5** | **READY** | **0** | **1** | **4** |

The difference is supported by direct visible evidence, not by the existence of a fix attempt: negative prices are replaced by valid monotonic values; all three Primary Production artworks render correctly; the Dev tab and placeholder text are absent; compact filters and the Crafting CTA are discoverable; disabled actions, terminology, Guide statuses, grammar, track continuation, Charts density, Common Supply centering, and Energy composition are all visibly improved in both mandatory resolutions.
