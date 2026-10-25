# Production Zero Research V1 — implementation report

## Architecture

Research is a shared Company/Industry progression system in `GameState.research`. `ResearchState` owns lifetime earned RP, the active set of unlocked node IDs, a UTC respec deadline, a clock high-water mark, and future named allocation snapshots. Available RP is lifetime earned minus active node count, so allocation and point balance cannot independently drift. Every small and Major node costs exactly one RP.

The versioned JSON catalog defines trees and nodes with stable IDs, names, descriptions, node types, costs, canonical resource icons, explicit prerequisite IDs, effect type/scope/target/value, and row/position. The UI generates widgets from these definitions. Runtime validation checks domains, targets, resources, costs, supported effects, and strictly earlier prerequisites; cycles cannot pass validation. The reproducible content builder contains explicit authored canonical ID assignments, rather than display-name heuristics.

The centralized modifier resolver sums Research contributions against a mechanic's pre-Research base. Existing rarity, warehouse upgrades, and market price evolution continue to define their existing bases. Global, single-domain, and exact-product bonuses add together; Research nodes never multiply one another. Additional `Modifier` contributions provide a common extension point for future Events/Consortium systems. Resolved Research contributions are cached by immutable allocation, keeping repeated production and pricing lookups inexpensive.

There is no recipe lookup or ancestry traversal in the resolver. Copper Ore, Copper, and Copper Wire are Metals products; Microchip is Electronics. A Microchip's inputs cannot grant Metals or Chemicals bonuses. Industry bonuses never alter quantities, recipes, cycle timing, or input requirements.

### Taxonomy audit

All 353 canonical resources/products have one authoritative domain in `research_domains.json`. Every recipe input/output is covered. Broad existing Materials/Components labels were audited and assigned explicitly by product identity. Electrical components, refined silicon, cables, computing and telecom products are Electronics; transformers/generation/storage hardware are Energy Technology. Crop cotton and processed textiles are Textiles. Natural rubber remains a Forestry primary product, while processed rubber is Chemicals. Biodiesel and biofuel are Energy Technology fuels; precursor feedstocks remain Chemicals. Coal is grouped with the fossil energy commodities in Oil & Gas. These assignments affect only each item's own economic value.

| Industry tree | Products |
| --- | ---: |
| Agriculture & Food | 28 |
| Forestry & Wood | 14 |
| Metals & Metallurgy | 64 |
| Oil & Gas | 4 |
| Chemicals | 45 |
| Electronics | 52 |
| Construction Materials | 23 |
| Machinery & Industrial Goods | 42 |
| Automotive | 9 |
| Aerospace | 14 |
| Energy Technology | 30 |
| Textiles | 9 |
| Rail Transport | 7 |
| Maritime | 7 |
| Medical Technology | 5 |
| **Total** | **353** |

### Persistence and migration

SQLite's existing state serializer includes a separately versioned Research payload. It saves total/available/spent RP, unlocked IDs, cooldown deadline/high-water timestamp, notification state, and named snapshots. Available/spent values are derived on load from the authoritative total and allocation. Saves without Research load with zero earned RP and an empty allocation; no retroactive level or Contract grants are synthesized. Removed node definitions and invalid dependent allocations are refunded on load. Invalid point totals or timestamps are rejected.

Warehouse saves retain the pre-Research capacity, preventing bonus compounding on repeated loads. Respec can leave goods above reduced capacity; it preserves those goods and blocks new storage until space is available.

The desktop entry point now uses the existing SQLite store at `%LOCALAPPDATA%/Production Zero/saves/company.sqlite` (home-directory fallback). The company loads at startup, autosaves every 30 seconds, saves immediately on Research purchase/respec, and saves on close. A save failure is shown in the status bar; closing is blocked until the save succeeds. Tests inject temporary stores and do not touch the player's save. Existing Dev JSON saves also carry Research through the shared serializer.

## Research content

**21 trees, 735 nodes, 105 Major nodes.** Every category has five complete sections: Foundation, Development, Precision, Excellence, and Mastery. Each section starts with a Major, followed by two rows of three small nodes. All six small nodes gate the following Major; they can be purchased in any order after their own preceding Major. All Industry trees are open from the beginning, regardless of production unlocks.

Company categories: General / Company; Production; Energy; Freight & Logistics; Storage; Contracts.

| Company category | Small node | Early Major | All 35 V1 nodes |
| --- | --- | --- | --- |
| General / Company | +0.1% all-product value | +0.5% | +8% value |
| Production | +0.1% global cycle rate | +0.5% | +8% cycle rate |
| Energy | +0.2% generated power | +0.5% | +11% generated power |
| Freight & Logistics | +0.2% capacity | +0.5% | +11% capacity |
| Storage | +0.5% shared capacity | +1% | +25% capacity |
| Contracts | +0.1% Contract cash | +0.5% | +8% Contract cash |

Each Industry tree has +0.2% domain-value small nodes, one +0.3% exact-product specialization per section, and Major domain bonuses progressing from +0.5% to +1.5%. Finishing a tree gives +10% domain value and +1.5% to its chosen specialization product. Examples include Copper Wire, CPU, Packaged Food, Reinforced Concrete, Cargo Aircraft, and Commercial Truck. These add to General Company value and, for Contracts, Company Contract value.

No categories are placeholders. Further sections can be appended with stable IDs without UI changes. The next content pass should diversify exact-product specializations first in the largest domains—Metals, Electronics, Chemicals, Machinery, and Energy Technology—then extend all trees beyond V1 Mastery as pacing data warrants. V1 intentionally uses a regular section rhythm rather than claiming 735 individually playtested balance decisions.

## UI

Research is a main Command Deck tab. The left rail visibly separates Company and Industries, uses canonical resource thumbnails, and gives the selected tree a dark/yellow highlight. The rail scrolls independently and keeps the selected category visible after resizing. Main navigation still fits at 1366×768.

The header is compact: tree name, per-tree completion, company-wide spent RP, available RP, and full-respec control. Below it, a one-line reset/cooldown explanation leaves most of the panel for the tree.

Small nodes are compact graphite beveled buttons with the bonus magnitude, short effect label, icon and textual state. Major nodes have larger painted-metal chassis, larger artwork, stronger framing and named milestone labels. Yellow indicates affordable nodes, cyan researched nodes, gray prerequisite locks, and `READY / NEED 1 RP` distinguishes a satisfied prerequisite from insufficient points. Tooltips explain exact effects and prerequisites; keyboard focus and accessible names are included.

Connections represent actual data prerequisites, routing around intervening rows. Trees scroll vertically with no canvas panning or zoom. Each tree remembers its scroll position. Ordinary purchases have no modal; they immediately spend one point, apply effects and update nodes, points, connections and the feedback line.

Full respec has a compact inline refund review and returns 100% of spent RP. A persisted 24-hour cooldown prevents another allocation reset. **Purchasing nodes remains allowed during cooldown**, including with refunded or newly earned points; this follows the prompt's detailed respec behavior. The countdown remains visible, and existing allocations remain inspectable. Local UTC plus a high-water timestamp prevents moving the clock backward from extending/rewinding the observed cooldown state; future server timestamps can feed the same interface.

All node and sidebar icon references resolve to existing raster assets. No new art was generated. Dedicated Research/Company/Contract symbols could improve semantic identity later, but no missing artwork blocks V1.

## Gameplay integration

- Company XP's authoritative award path grants +1 RP for every gained level, including multiple levels in a single award. XP amounts and the XP curve are unchanged.
- Authoritative Daily completion grants +1 RP and Weekly completion +3 RP; partial delivery and repeated completion calls grant nothing extra. Existing packs, XP, requirements, budgets and selection rules remain intact. RP appears in Daily/Weekly reward chips.
- Market sales use Company + output-domain + direct-product Research at dispatch. Both manual sale commands and automated freight exports use the same sale-price resolver. The Market detail surface shows the player's effective sale value and Research percentage while its market history and base-price information retain their existing meaning.
- Contract acceptance sums each required product's base-market-price × quantity contribution with that product's applicable additive Research and Company Contract bonus. A bonus on one product cannot raise unrelated contributions. UI quotes share this same resolver. The resulting reward stays fixed at acceptance, preserving the existing Contract snapshot rule.
- In-flight freight retains its dispatch price/capacity; accepted Contracts retain their accepted cash reward through Research changes or respec. New commitments use the current allocation. Cancelled Contract freight converted to market uses the applicable market quote at conversion.
- Global production Research advances every machine's cycle progress by the same rate factor. Per-cycle inputs/outputs stay unchanged, and planned input/output flow reporting uses the identical global factor.
- Energy Research affects both simulation generation and preview/installed-module displays. Freight Research affects new dispatch capacity, installed fleet summaries, selection previews and inspection. Storage Research feeds authoritative shared capacity.
- RP earned, Major reached/ready, respec completed and cooldown finished flow through existing Company Communications into Activity/History/ticker. Small-node purchases only update local feedback, avoiding ticker spam. No separate Inbox notification architecture was added.
- Dev-only controls grant 25 RP, clear cooldown, and refund allocation. They live in the existing development tab, absent when development mode is disabled.

## Validation

Focused Research tests: **22 passed**. Coverage includes canonical resources and recipe coverage; duplicate domains; catalog/prerequisites; RP sources and exact spending; gating; additive global/domain/product modifiers; no recipe inheritance; actual freight dispatch/payout; proportional multi-product Contracts; simulation cycle/energy effects; no storage loss; cooldown/rollback; SQLite roundtrips without compounded capacity; legacy migration; removed-node refunds; Activity integration; every category/icon; click states; sidebar/scroll behavior; compact sizes; and immediate SQLite purchase persistence.

Related validation runs passed: **95** progression/storage/freight/persistence tests; **87** Research/command/simulation/company/Contract tests; **54** Research and related Contract/Market/communications/UI tests. These runs overlap; their counts are not an aggregate unique-test count.

`compileall` passed for source, tests and the content builder. `git diff --check` passed. Only one final full-suite run was launched; its result and the corrective focused follow-up are recorded below. The full-suite transcript and JUnit XML are in the screenshot directory.

**Single full-suite checkpoint: 877 passed, 1 failed in 1,817.24 seconds (30:17).** The sole failure was the pre-Research expected-tab list in `test_main_window_has_expected_top_tabs`. Its expectation now includes Research. A focused follow-up on the latest code passed **24 tests**, including that navigation test, all 22 Research tests, Activity aggregation, and the simulation UTC-clock path. No second full-suite run was performed. There are no known unresolved failures; the original full-suite log/XML preserve the historical assertion failure rather than being rewritten as a green run.

### Offscreen QA

Exactly **9 screenshots**, all generated with `QT_QPA_PLATFORM=offscreen`; the QA script asserts the platform. **No live GUI was launched.** The compact capture measures exactly 1366×768, with a 1,036 px tree viewport, zero horizontal scroll range, and a 2,058 px vertical scroll range. Every main navigation tab fits (last tab ends at 701 px in a 702 px bar).

Output directory: `artifacts/ui/research-v1/`

1. `01-company-available.png` — Company foundation and locked small rows.
2. `02-company-purchased.png` — RP spent, Major researched, small nodes available.
3. `03-industry-states.png` — Electronics available/researched/locked states.
4. `04-major-node.png` — larger Major chassis and exact resource art.
5. `05-deep-vertical-tree.png` — scrolled Excellence/Mastery section.
6. `06-respec-review.png` — inline full-refund review.
7. `07-respec-cooldown.png` — refunded/reallocated points and cooldown.
8. `08-compact-1366x768.png` — compact Command Deck.
9. `09-market-research-value.png` — effective Microchip sale value with Research.

`qa.json` records capture paths, platform and compact geometry. Screenshots were inspected and corrected for row backgrounds, mnemonic ampersands, selected-rail visibility and Market text contrast.

## Files created or changed for Research

The workspace already contained extensive uncommitted work before this task. That work was retained. The following is the Research-specific file list; it is not the entire pre-existing working-tree diff.

### Created

- `src/production_zero/core/research.py`
- `src/production_zero/core/modifiers.py`
- `src/production_zero/data/research_domains.json`
- `src/production_zero/data/research_definitions.json`
- `src/production_zero/ui/research_view.py`
- `src/production_zero/tools/research_qa.py`
- `scripts/build_research_content.py`
- `tests/test_research.py`
- `tests/test_research_ui.py`
- `docs/research-v1-implementation-2026-09-12.md`
- QA PNGs, `qa.json`, `full-suite.log`, `full-suite.xml`, `checkpoint-followup.log`, and `collected-tests.txt` in the output directory above.

### Modified

- `src/production_zero/core/state.py`
- `src/production_zero/core/communications.py`
- `src/production_zero/core/company_xp.py`
- `src/production_zero/core/contracts.py`
- `src/production_zero/core/commands.py`
- `src/production_zero/core/analytics.py`
- `src/production_zero/core/simulation.py`
- `src/production_zero/core/freight.py`
- `src/production_zero/persistence/sqlite_store.py`
- `src/production_zero/ui/main_window.py`
- `src/production_zero/ui/event_feed.py`
- `src/production_zero/ui/market_view.py`
- `src/production_zero/ui/contracts_view.py`
- `src/production_zero/ui/dev_tools_view.py`
- `src/production_zero/ui/freight_view.py`
- `src/production_zero/ui/factory_view_v2.py`
- `src/production_zero/ui/factory_view.py`
- `src/production_zero/app/__main__.py`
- `pyproject.toml`
- `ProductionZero.spec`
- `tests/test_factory_ui.py` — expected navigation now includes Research.

## Known follow-ups

### Suggested first manual playtest

1. Open Research, earn a Company level or use the existing Dev tab's `Grant 25 RP` control, then buy the General Company Foundation Major.
2. Open Electronics even before its production unlocks. Buy its Foundation and small nodes in mixed order; verify the next Major requires all six.
3. Inspect Microchip in Market. Compare the public market price with `YOUR SALE VALUE`; accept a mixed-product Contract and check its fixed reward.
4. Full-respec, verify the exact refund, allocate points again, and confirm another reset is blocked while purchases remain possible.
5. Close/reopen the normal desktop app and verify allocation and cooldown persist. Continue playing the balanced production chain and watch storage/freight constraints at the new global rate.

- Playtest RP pacing, +8% global production and Company value totals, +11% energy/freight, +25% storage, and combined Company/Industry/product/Contract value. These are conservative first-pass values, not final economy tuning.
- Expand product diversity before simply repeating more identical sections, prioritizing the largest five Industry domains. Extend all trees after the V1 Mastery milestone as needed for deeper longevity.
- Saved allocation data exists; template naming, management and application UX is deferred. Future allocation-reset application must share the full-refund/cooldown transition rather than bypass it.
- Optional dedicated Research, Company and Contracts artwork; current canonical resource substitutes are complete and usable.
- Future server authority should supply validated UTC timestamps. V1 is a local game and does not claim anti-cheat time authority.
- No executable build or live manual play session was performed. Packaging includes Research JSON and the reused resource PNGs.

## Final verdict

**Research V1 is ready for manual playtest.** The full-suite checkpoint exposed one obsolete navigation assertion, now corrected and passing in the focused follow-up. Core gameplay, persistence, respec/cooldown, all categories, and compact offscreen UI are validated. No known implementation blocker remains. Balance, deeper specialization variety, and template-management UX remain deliberate follow-ups; no live playtest or packaged executable build was performed.
