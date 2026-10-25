# First real playtest fix pass

Factory V2 remains the runtime Factory. No real GUI was launched. Existing uncommitted project work was preserved; the input snapshot is `artifacts/playtest-before.zip`. The supplied request ends at “If older saves”; existing accepted rewards are preserved unchanged.

## Economy model confirmed before edits

353 unique options: 49 Extractor, 68 Processor, 86 Fabricator, 150 Assembler. Six machine definitions: Extractor MK I/II/III, and MK I for the other three families. No later machine family exists yet. Extractors previously ran every 3 seconds; Processor options every 3–7 seconds; Fabricators every 6 seconds; Assemblers every 8 seconds.

For recipe output O, input I, cycle T, rarity bonus b:

- Output/cycle = O × (1 + b/100). Inputs/cycle = I; rarity increases yield rather than input requirements.
- Output/minute = O × (1 + b/100) × 60/T. Input/minute = I × 60/T.
- Machine power = recipe MW × (1 + b/200). Energy output = base MW × (1 + b/100). Power is capacity, not an accumulating resource.
- Runtime stores per-card selected production, target resource, progress seconds and status. Progress accrues when power, inputs and storage permit. Completing a cycle consumes the recipe inputs; output is capped by free storage. Machine iteration order can cause startup delay; it does not change the long-run planning ratio.
- Coal previously burned 2/min continuously (elapsed time prorated) for 100 MW. Gas uses 2/min for 180 MW and Nuclear 0.25/min for 500 MW. Solar 20 MW and Wind 35 MW have no fuel.
- Storage is global across halls. Freight loads up to capacity from available stock immediately when idle, removes that stock at departure, then becomes available after transit. Partial loads are allowed. Deliveries complete before the next dispatch opportunity; time is quantized by the simulation update interval.
- Market cargo snapshots the current market price at dispatch. On arrival it routes to eligible contracts first and sells any surplus. Direct contract cargo uses the same transit system and completes the contract only after arrival.
- Freight rarity increases cargo by (1+b/100) and transit time by (1+b/200). Freight has no MK upgrade path. Extractor MK outputs are 12/30/60 with power 6/14/25; those tier identities remain.
- Guide and production-value calculations derive from machine options. Production value is recursively input value per output plus machine minutes per output; flexible-contract required amounts use that value. Market unit prices themselves are independent resource data and are unchanged.
- The Resource drawer previously computed status-gated theoretical rates, not an actual storage-delta measurement. Blocking made those rates disappear, while Freight was excluded. Chain Inspector incorrectly accumulated downstream demand into the current node’s Input label.
- Saves already persist accepted `offer.reward_cash`, machine progress/assignments, market state, shipment cargo/capacity/remaining transit and dispatch price. No new save schema is required. Existing in-flight shipments retain their saved capacities and transit times; future departures use the new stats.

Example confirmed from actual data: Copper extraction = 12/3s, Copper processing consumes 12/4s and outputs 6/4s. One Extractor therefore fed 4/3 Processors, despite matching batch input/output. The recipe consumes 12 Ore, not the illustrative 6 in the request.

## Shared six-second cycle and ratio normalization

`core/economic_cycle.py` is the canonical duration. Six seconds is the median of the 353 original recipe durations, preserves all Fabricator timings, and lies between the faster early stages and eight-second Assemblers. All normal production options and all MK tiers now use it. Recipe outputs, power requirements, unlock IDs/thresholds, resource prices and rarity behavior remain unchanged.

This necessarily changes per-minute pacing: extraction becomes 50% of its old speed, four-second processing becomes 67%, Fabricators stay at 100%, and Assemblers become 133%. Keeping the old per-minute rates exactly would require fractional batch quantities or much larger batches, defeating the approved mental-math objective. These are deliberate timing consequences, not additional output rebalancing.

The audit checked all **353 products and 708 adjacent recipe inputs**. All base quantities are integers. A simple ratio is defined as 1:N or N:1 up to 12, or a reduced whole-number pair with each side at most 5 (including 2:3, 3:4 and 2:5). Only **32 inputs across 28 recipes** needed quantity changes; all other quantities remain intact. Fractional input quantities were rounded to the nearest integer that meets the ratio rule; equally close choices prefer the smaller input. Rarity and higher MK cards can still produce fractional effective ratios, as visible upgrades.

Copper now plans as 1 Extractor → 1 Processor → 3 Copper Wire Fabricators (12 Ore → 6 Copper; each Fabricator consumes 2 Copper and makes 3 Wire). Guide and Inspector use the same `ProductionGuideRecipeIndex`. Each Inspector node shows only its own named inputs and output per cycle; extraction omits Input entirely.

### Changed input quantities

Ratios below mean **downstream machines supported per upstream machine**, not ingredient-to-product conversion. The old effective ratio includes the old differing cycle durations. Unchanged quantity recipes also benefit from timing normalization.

| Recipe | Input | Input quantity before → after | Old batch ratio | Old effective ratio | New ratio |
|---|---|---:|---:|---:|---:|
| processor.aluminum | bauxite | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.zinc | zinc_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.lead | lead_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.tin | tin_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.nickel | nickel_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.manganese | manganese_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.chromium | chromium_ore | 10 → 9 | 6/5 | 8/5 | 4/3 |
| processor.platinum | platinum_ore | 5 → 4 | 12/5 | 24/5 | 3 |
| processor.palladium | palladium_ore | 5 → 4 | 12/5 | 24/5 | 3 |
| processor.nickel_alloy | coal | 1.5 → 1 | 8 | 16 | 12 |
| processor.superconducting_alloy | rare_earth_ore | 2.8 → 3 | 30/7 | 10 | 4 |
| processor.high_purity_silicon | crude_oil | 1.5 → 1 | 8 | 16 | 12 |
| processor.high_purity_silicon | natural_gas | 1.5 → 1 | 8 | 16 | 12 |
| processor.carbon_fiber | graphite | 1.5 → 1 | 8 | 16 | 12 |
| processor.industrial_resin | crude_oil | 2.5 → 2 | 24/5 | 8 | 6 |
| processor.phosphoric_acid | natural_gas | 0.5 → 1 | 24 | 32 | 12 |
| fabricator.insulated_wire | copper | 1.5 → 1 | 4 | 6 | 6 |
| fabricator.electrical_components | copper | 1.5 → 1 | 4 | 6 | 6 |
| fabricator.electrical_components | polymer | 0.5 → 1 | 4 | 24/5 | 2 |
| fabricator.transformer_components | copper | 1.5 → 1 | 4 | 6 | 6 |
| fabricator.motor_components | copper | 1.5 → 1 | 4 | 6 | 6 |
| fabricator.control_electronics | copper | 1.5 → 1 | 4 | 6 | 6 |
| fabricator.computing_components | copper | 2.5 → 2 | 12/5 | 18/5 | 3 |
| fabricator.telecom_components | copper | 2.25 → 2 | 8/3 | 4 | 3 |
| fabricator.network_components | copper | 4.5 → 4 | 4/3 | 2 | 3/2 |
| fabricator.avionics_components | copper | 2.5 → 2 | 12/5 | 18/5 | 3 |
| fabricator.battery_components | nickel | 0.5 → 1 | 10 | 15 | 5 |
| fabricator.battery_components | cobalt | 0.5 → 1 | 8 | 48/5 | 4 |
| fabricator.advanced_cell_components | cobalt | 0.5 → 1 | 8 | 48/5 | 4 |
| fabricator.solar_components | aluminum | 1.5 → 1 | 10/3 | 5 | 5 |
| fabricator.industrial_fabric | cotton_fiber | 0.5 → 1 | 4 | 8 | 2 |
| fabricator.industrial_fabric | polymer | 0.5 → 1 | 4 | 24/5 | 2 |

## Coal and Freight exact changes

Coal Plant: **100 → 60 MW; 2/min → 6/cycle (60/min)**. One Common MK I Coal Extractor produces 12/cycle and sustains exactly two plants; a startup stock buffer is needed because fuel is drawn continuously before the extractor completes its first batch. Four Common plants now require two dedicated extractors and yield 240 MW. Coal is still stronger than Solar (20) and Wind (35). Gas/Nuclear balance is unchanged; fuel tooltips consistently convert their rates to the shared cycle. The legacy per-minute definition accessor remains for compatibility, but Coal data and runtime fuel calculation use the cycle concept.

| Freight | Cargo before → after | Transit (unchanged) | Full-load cargo/economic cycle before → after |
|---|---:|---:|---:|
| Truck | 40 → 40 | 60s | 4 → 4 |
| Train | 180 → 200 | 150s | 7.2 → 8 |
| Ship | 600 → 560 | 420s | 8.57 → 8 |
| Aircraft | 24 → 25 | 25s | 5.76 → 6 |

No animation or transit synchronization was introduced. Freight, Supply and Inventory tooltips expose the effective full-load capacity per six-second cycle, including rarity. Partial loads, dispatch quantization and interruptions reduce actual throughput. Existing Supply price formulas continue to apply to the modest capacity adjustments; daily limits and offer persistence are unchanged.

## Concrete playtest fixes

- Resources: `EST. +/- per cycle` represents configured production minus machine inputs and fuel at full operation, excluding Freight. Temporary storage/power/input blocking does not change this planning metric. `ACTIVE` preserves the selected hall view; `ALL STORED` includes every global stock with quantity > 0.
- Newly granted machines start unconfigured. The starter Processor’s hardcoded Steel selection was the observed exception and is removed. Save loading and reinstalling a configured card preserve its assignment.
- Installed Factory V2 cards reuse the embedded card tooltip with rarity, MK, actual selected recipe output/inputs, power and fuel. Energy selection cards use the installed renderer’s specific Solar/Wind/Coal/Gas/Nuclear family.
- Expansion Line uses the existing utility chassis and affordability/hover treatment; costs, slots, scrolling and geometry are unchanged.
- Guide retains its panel and tiles when closed or visiting a chain, refreshing progress when needed. Keeping its original parent avoids expensive restyling. No resources or artwork were removed.
- Inventory wraps every row from the same left column. Identical deployed bound cards now stack; unique collectible/trade-state cards stay distinct. Available and In Use remain separate filterable stacks, with Owned/Available/In Use counts in the shared tooltip.
- Dedicated Scrap tab reuses recycling commands and existing Rare-or-higher confirmation rules, offers stack/quantity selection and shows the exact scrap return. Installed cards cannot be selected. Unchanged refreshes preserve the current interaction.
- Common Supply has a compact BUY ×1 / BUY ×4 selector, total-cost tooltips and atomic affordability checking. Daily purchases remain one choice per category per reset.
- Daily Supply retains its actual card widgets across ordinary refreshes, registers both Daily and Common cards for the same embedded hover path, and avoids redundant binding/icon regeneration. Layout activation settles resized card geometry without rebuilding the cards. Tooltip hit testing remains transparent. Locked cards have an explicit two-line `LOCKED / UNTIL RESET` footer; unaffordable cards retain grey BUY.
- Contract reward chips show one currency/XP marker. At acceptance, cash is current market unit price × accepted required quantity, rounded to cents and stored in the accepted offer. The offer preview uses the selected product’s market value; active cards show the frozen value. No premium is added, and XP remains unchanged. Old accepted rewards are never recalculated.

## Verification

- `scripts/audit_economic_cycle.py`: all 353 products, 708 base edges and six machine tiers pass. Complete edge data: `artifacts/playtest/economy-audit.json`.
- Focused simulation/save tests: one-hour Coal sustainability, exact one-cycle output/input checks across Processing/Fabrication/Assembly, all three contract categories’ reward freezing and SQLite roundtrips, old reward/assignment/progress preservation, atomic ×4 purchases and in-use grouping.
- `scripts/validate_playtest_pass.py`: offscreen hover across BUY-child transitions and repeated Supply refreshes, installed tooltip, full stored inventory, Scrap selection, Chain Inspector semantics; captures in `artifacts/playtest/`.
- With identical loaded fonts/theme and 1500×950 offscreen viewport: snapshot-before Guide opens **3375 / 4275 / 4482 ms**, creating 1059 tiles across three opens. After: **2840 / 33 / 27 ms**, creating only 353 tiles. Cold-open cost remains; repeated-open lag is removed. Timing varies by machine and concurrent test load.
- Compileall passes. The full suite exercised **665 tests**: 651 passed on the initial full run; all 14 remaining cases pass on their final rerun after updating obsolete timing/capacity/cache/layout expectations. Reports: `artifacts/playtest-suite.xml` and `artifacts/playtest-fixed-regressions.xml`. The separate 82-case core group and 96-case focused UI/core group also pass.
- Final offscreen checks click BUY ×4 (exactly four cards and four prices, then affordability disables BUY), click Scrap (one available card removed, installed card preserved), and remove a zero-stock resource from All Stored. All pass.
- A patch against the pre-pass workspace snapshot is available at `artifacts/playtest/changes.patch`; existing unrelated work is excluded.

This pass does not claim a second human playtest. The shared-cycle pacing and stronger Coal fuel commitment should be assessed in the next real run; automated tests verify behavior and consistency, not subjective balance.
