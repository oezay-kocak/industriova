# Resource Progression Pacing Audit — 2026-09-07

Status: **NEEDS ADJUSTMENT**

This audit validates the design in `docs/resource_progression_plan_2026-09-07.md` and its JSON companion against the active repository state. It changes no progression rule, runtime code, save, test, or UI.

## Verdict

The dependency model is sound, and the proposed **120 / 60 / 30** gates are small rather than grind-heavy. The Level 1–25 pacing is not ready to implement against the current XP runtime, however. Company XP is earned only from Contracts, Contract XP scales strongly with configured theoretical factory capacity, and Daily/Weekly periods advance only while the simulation is running. Under explicit, plausible scenarios, Level 25 ranges from roughly **15.5 active hours / 5.2 calendar days** for an Optimizer to **213.6 active hours / 641 calendar days** for a Casual player. That spread is too large for the same fixed family schedule.

Two content cohorts compound the problem: Level 19 makes 63 options newly eligible by family ancestry, and Level 23 makes 67 eligible. Lifetime gates prevent an instantaneous unlock, but an optimized factory can traverse the new stage gates in minutes. The graph has no deadlock; the risk is severe XP/production desynchronization and uneven presentation.

## Active repository facts

### Company XP

`src/production_zero/core/company.py:44-49` defines the Level 1–99 cost as:

`XP to next level = 500 + 125 × current level + 18 × current level²`

Levels continue beyond 100. Titles exist at Levels 1, 10, 25, 50, 75 and 100. `award_company_xp()` carries overflow across any number of levels (`company.py:74-89`).

The active source search finds only one gameplay caller of `award_company_xp()`: completed Contracts in `src/production_zero/core/contracts.py:497-518`. Production, sales, supply, packs and ordinary level rewards do not grant Company XP. The fixed values returned by `xp_reward_for_contract_kind()`—90 Regular, 450 Daily and 2,400 Weekly—serve as persistence fallbacks for older offers; newly generated active offers use dynamic production-value budgets.

### Contract generation and rewards

The active Contract system has three concurrent kinds:

- **Regular:** target budgets based on 6 / 10 / 16 production minutes; a completed Regular is immediately replaced, so this is the only repeatable XP source without waiting for a period boundary.
- **Daily:** target budgets based on 25 / 45 / 75 production minutes; one accepted Daily can exist per simulated day.
- **Weekly:** target budgets based on 90 / 160 / 260 production minutes; one accepted Weekly can exist per simulated week.

Each refresh creates three offers. XP equals the selected production-value budget multiplied by **9 / 15 / 20** for Regular / Daily / Weekly and rounded to five (`contracts.py:35-61`, `301-328`). Budgets scale with `effective_pv_per_minute ** 0.88`, target minutes and kind multiplier, subject to capacity caps (`contracts.py:333-394`).

The capacity estimate sums the theoretical production value per minute of every installed, configured Machine. It does not verify current energy, inputs, storage space, or running status. A configured but stalled advanced line can therefore increase future Contract size and XP. Accepted offers are snapshots, and XP is awarded only after full freight delivery.

Daily and Weekly boundaries use `state.market.elapsed_seconds` (`contracts.py:125-150`). The value is persisted (`src/production_zero/persistence/sqlite_store.py:75,237`), but no wall-clock timestamp or offline catch-up path exists. The Factory timer calls `SimulationEngine.advance_time()` from a 250 ms Qt timer while the application is running (`src/production_zero/ui/factory_view.py:912-915,1966-1973`). Closing or pausing the game produces no resources, Lifetime progress, Contract-period progress or offline Company XP.

This means “Daily” currently means 24 accumulated hours of running simulation and “Weekly” means 168 accumulated hours. A player opening the game for one hour per day receives a new Daily period about every 24 calendar days and a new Weekly period about every 168 calendar days.

### Production and Lifetime tracking

All 353 production options use a six-second base cycle. At Common quality:

| Stage | Options | Output per cycle | Output per minute | Direct-input count |
|---|---:|---|---|---|
| Extractor | 49 | 12 for every option | 120 | 0 |
| Processor | 68 | 1–6; median 2.5 | 10–60; median 25 | 1–4 |
| Fabricator | 86 | 1–3; median 1 | 10–30; median 10 | 1–4 |
| Assembler | 150 | 1 | 10 | 1–4 |

Uncommon through Legendary output bonuses range from 1% to 20%, so even a maximum roll shortens a time gate by only 16.7%. `SimulationEngine.advance_time()` records accepted output after production (`src/production_zero/core/simulation.py:139-176`). Full storage, missing inputs or missing power stop production; purchased stock and freight receipts do not count as Lifetime Production.

The new-game inventory owns three Common Extractors, two Common Processors and one Solar Array, but installs none automatically and owns no Fabricator or Assembler (`src/production_zero/ui/main_window.py:178-206`). Card acquisition, cash, installation, power, storage and freight can therefore dominate real progression even when the mathematical Lifetime threshold is short.

## Simulation method and limits

The repository contains no player telemetry, no implemented offline economy and no target number of Contracts per session. Exact calendar forecasts are therefore impossible. The following is a transparent scenario model, not a claim that the runtime enforces these behaviors.

All calculations use the current XP formula, current Contract reward formula, the mean of the three offers, and actual simulated-time Daily/Weekly cadence. Rewards are integrated at the current Company Level. Representative effective production-value capacity rises by band as more Machines are configured:

| Scenario | Active time per calendar day | Regular completions per active hour | Daily completion per simulated day | Weekly completion per simulated week | Effective PV/min at L1–4 / L5–9 / L10–15 / L16–20 / L21–25 |
|---|---:|---:|---:|---:|---|
| Casual | 20 min | 1.2 | 35% | 25% | 1.5 / 3 / 5 / 7 / 9 |
| Regular | 60 min | 2.0 | 82% | 70% | 2.5 / 6 / 12 / 20 / 30 |
| Optimizer | 180 min | 4.0 | 96% | 95% | 5 / 12 / 25 / 40 / 60 |

The Casual and Optimizer completion tendencies are anchored to the repository’s economy-stress profiles; the Regular profile is an explicit midpoint. Daily/Weekly rewards are amortized over 24/168 **active simulation hours**, matching the runtime clock. Initial one-off Daily/Weekly offers are not treated as instant rewards because their 25–260 production-minute requirements still need production and freight delivery.

Representative calculated XP rates illustrate the scaling:

| Scenario | L1-band XP/active hour | L10-band XP/active hour | L21-band XP/active hour |
|---|---:|---:|---:|
| Casual | ~203 | ~557 | ~942 |
| Regular | ~529 | ~2,193 | ~4,925 |
| Optimizer | ~1,841 | ~7,634 | ~16,480 |

The estimates exclude time spent unable to fulfil a selected Contract, cash/card acquisition delays and manual indecision. They can therefore be optimistic, especially for Casual players. Conversely, the capacity estimator’s stalled-line behavior can let expert players produce even larger offers than the model assumes.

## Level milestone estimates

“Active” is cumulative time with the simulation running. “Calendar” divides that time by the daily session assumption above. XP values are exact; time values are modeled estimates.

| Level | Cumulative XP | Casual active / calendar | Regular active / calendar | Optimizer active / calendar |
|---:|---:|---:|---:|---:|
| 2 | 643 | 3.2 h / 9.5 d | 1.2 h / 1.2 d | 0.4 h / 0.1 d |
| 3 | 1,465 | 7.2 h / 21.7 d | 2.8 h / 2.8 d | 0.8 h / 0.3 d |
| 4 | 2,502 | 12.3 h / 37.0 d | 4.7 h / 4.7 d | 1.4 h / 0.5 d |
| 5 | 3,790 | 18.7 h / 56.1 d | 7.2 h / 7.2 d | 2.1 h / 0.7 d |
| 7 | 7,263 | 28.7 h / 86.0 d | 10.1 h / 10.1 d | 2.9 h / 1.0 d |
| 9 | 12,172 | 42.7 h / 128.2 d | 14.2 h / 14.2 d | 4.1 h / 1.4 d |
| 11 | 18,805 | 57.9 h / 173.8 d | 18.4 h / 18.4 d | 5.4 h / 1.8 d |
| 13 | 27,450 | 73.5 h / 220.4 d | 22.4 h / 22.4 d | 6.5 h / 2.2 d |
| 16 | 44,820 | 104.6 h / 313.9 d | 30.3 h / 30.3 d | 8.8 h / 2.9 d |
| 19 | 68,337 | 135.3 h / 405.8 d | 37.1 h / 37.1 d | 10.8 h / 3.6 d |
| 21 | 87,910 | 160.8 h / 482.3 d | 42.9 h / 42.9 d | 12.5 h / 4.2 d |
| 23 | 110,935 | 185.2 h / 555.6 d | 47.5 h / 47.5 d | 13.9 h / 4.6 d |
| 25 | 137,700 | 213.6 h / 640.9 d | 53.0 h / 53.0 d | 15.5 h / 5.2 d |

The requested profile checkpoints are therefore:

| Player type | Level 5 | Level 10 | Level 16 | Level 19 | Level 23 | Level 25 |
|---|---:|---:|---:|---:|---:|---:|
| Casual | 18.7 h / 56 d | 51.6 h / 155 d | 104.6 h / 314 d | 135.3 h / 406 d | 185.2 h / 556 d | 213.6 h / 641 d |
| Regular | 7.2 h / 7 d | 16.8 h / 17 d | 30.3 h / 30 d | 37.1 h / 37 d | 47.5 h / 48 d | 53.0 h / 53 d |
| Optimizer | 2.1 h / 0.7 d | 4.9 h / 1.6 d | 8.8 h / 2.9 d | 10.8 h / 3.6 d | 13.9 h / 4.6 d | 15.5 h / 5.2 d |

## Lifetime-gate pacing

### Typical recipe times

| Gate | One direct input, Common Machine | 2–4 inputs with one upstream Machine used serially | 2–4 inputs produced fully in parallel |
|---|---:|---:|---:|
| Processor: 120 raw units | exactly 1 min | 2–4 min | 1 min |
| Fabricator: 60 processed units | 1–6 min; median 2.4 min | 2–24 min | 1–6 min |
| Assembler: 30 fabricated units | 1–3 min; median 3 min | 2–12 min | 1–3 min |

These are lower bounds once the needed Machine cards are installed and continuously supplied. A real multi-stage path must first produce and unlock its Processor input, then its Fabricator input. With unlimited parallel machines, a new family can expose its Processor layer after about one minute and complete a typical three-stage reveal in roughly 5–10 minutes. With one Machine per stage, all recipes in a broad family take the summed machine work shown below.

### Work introduced at each family level

“Eligible cohort” counts every option whose highest root-family requirement is that level. These options do not unlock automatically. Stage-work columns measure only new outputs needed to open the next stage, assuming earlier-family requirements are already mastered.

| Level | New roots | Processor | Fabricator | Assembler | Eligible cohort | Extractor / Processor / Fabricator machine-minutes | Assessment |
|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 9 | 8 | 7 | 0 | 24 | 9 / 4.7 / 0 | Dense start catalog, but downstream gates and missing installations limit the visible burst. |
| 2 | 3 | 4 | 0 | 0 | 7 | 3 / 0 / 0 | Light, readable expansion. |
| 3 | 4 | 2 | 3 | 2 | 11 | 4 / 2 / 3 | Healthy first full-chain introduction. |
| 4 | 4 | 7 | 5 | 2 | 18 | 4 / 18 / 4.5 | Moderate Processor workload; acceptable. |
| 5 | 2 | 10 | 12 | 22 | 46 | 2 / 24 / 22.5 | First notable content spike; requires monitoring. |
| 7 | 4 | 6 | 8 | 10 | 28 | 4 / 18 / 16.5 | Healthy mid-game branch expansion. |
| 9 | 4 | 5 | 4 | 4 | 17 | 4 / 5.6 / 4.5 | Well paced. |
| 11 | 2 | 3 | 3 | 2 | 10 | 2 / 3.2 / 4.5 | Deliberately light milestone. |
| 13 | 4 | 6 | 9 | 9 | 28 | 4 / 18 / 10.5 | Good bridge into advanced materials. |
| 16 | 3 | 3 | 6 | 5 | 17 | 3 / 5 / 9 | Content size is fine; elapsed level gap is the issue. |
| 19 | 2 | 2 | 15 | 44 | 63 | 2 / 4 / 42 | **Too broad:** many premium downstream recipes share only two new roots. |
| 21 | 2 | 3 | 2 | 3 | 10 | 2 / 9 / 6 | Useful small milestone after Level 19. |
| 23 | 5 | 8 | 10 | 44 | 67 | 5 / 14.5 / 28.5 | **Largest root drop and largest total cohort.** |
| 25 | 1 | 1 | 2 | 3 | 7 | 1 / 3 / 6 | Small, focused nuclear capstone. |

Levels 19 and 23 are presentation spikes, even though they are not instant mechanical unlocks. At Level 19, one Fabricator needs 42 machine-minutes to produce 30 of every newly relevant Fabricator output; three parallel Fabricators reduce that to roughly 14 minutes. Level 23 requires 28.5 Fabricator machine-minutes, or roughly 10 minutes with three parallel cards. Many of the 44 Assembler recipes then become eligible together. The Guide must stage notifications and reveal ordering; the 30-unit Assembler gate alone is too weak to space these cohorts for an Optimizer.

## Early, mid and late game assessment

### Early game: Levels 1–5

For a Regular player, the first five Levels occupy about seven calendar days and interleave new roots with one-minute Processor gates. This is plausible. Casual pacing is not: Level 2 takes about ten calendar days and Level 5 about eight weeks because there is no offline clock. Optimizers reach Level 5 on the first day, so Levels 2–5 can arrive before the previous family’s Fabricator/Assembler branch has been installed or explored.

The Level-5 Gas & Elastomers cohort is larger than its two roots suggest. Its 46 eligible descendants remain gated, but the Guide needs grouping to avoid presenting them as one milestone payload.

### Mid game: Levels 7–16

The family order is coherent: chemicals, common alloys, advanced alloys, specialty minerals, then batteries/electronics. For Regular play, Level 7–16 spans about 20 active hours and 20 calendar days. For an Optimizer it spans under six active hours; Company Level can outpace meaningful operation of four newly discovered families. For Casual play it spans roughly 228 calendar days.

Battery & Electronics at Level 16 is thematically placed correctly and has a manageable 17-option cohort. Its three-level gap from Level 13 becomes 31 active hours / 94 calendar days for Casual, 7.9 hours / 8 days for Regular, and only 2.3 hours / under one day for an Optimizer. The problem is XP cadence variance rather than this family’s dependency structure.

### Late game: Levels 19–25

The thematic order is strong, and Uranium belongs at the Level-25 Industrialist milestone. The modeled time from Level 16 to 25 is about 109 active hours for Casual, 22.7 for Regular and 6.7 for Optimizer. Calendar time ranges from eleven months to just over two days.

Late gaps do not behave as intended across profiles:

- Casual players can spend 73–93 calendar days between root-family events.
- Regular players see a new root family every 5–8 days.
- Optimizers see each late family within roughly half a day and can traverse its Lifetime gates during a single session.

Daily/Weekly Contracts do not fill Casual gaps under the current clock because their periods barely advance during short sessions. For high-capacity players, dynamically scaled Regular Contracts are already sufficient to race through Levels; later Daily/Weekly rewards can create additional multi-level jumps.

## Specialization and ignored families

- **Ignored family:** Company Level continues through Contracts even if the player never operates the newly discovered roots. The ignored branch and every cross-family recipe depending on it remain locked. This is understandable and recoverable, but the Guide can accumulate a large backlog of `Produce ...` tasks.
- **Extreme specialization:** A player can repeatedly fulfil Contracts with a small set of efficient products and gain Levels without broad production mastery. New families arrive faster than they are explored; configured advanced but stalled lines can further inflate future Contract XP.
- **Production-first player:** A player who explores every available chain may finish all 120/60/30 gates long before the next Company Level, especially in the Level 13–25 gaps. They then wait entirely on Contract XP.
- **XP-first player:** An Optimizer can reach later family levels before acquiring or operating enough Fabricator/Assembler cards. The result is a large Guide eligibility backlog rather than a deadlock.

The system therefore allows XP progress and production progress to diverge strongly in both directions. Cross-family requirements eventually reconcile the catalog, but they do not correct pacing.

## Balancing recommendations

No dependency or Cross-Family rule needs changing. The following values are recommendations only.

| Area | Current plan/runtime | Proposed value | Reason | Expected effect |
|---|---|---|---|---|
| Processor gate | 120 per direct input | **Keep 120** | Exactly one Common Extractor-minute; clear tutorial feedback without instant unlock. | Processor stays early and legible. |
| Fabricator gate | 60 per direct input | **Keep 60** | Produces a 1–6 minute single-input wait and meaningful multi-input setup. | No unnecessary early grind. |
| Assembler gate | 30 per direct input | **Raise to 60** | The 44-option Level-19 and Level-23 Assembler cohorts can otherwise follow after about 10–14 optimized minutes. | Typical fabricated input takes 6 minutes; late cohorts spread over roughly twice the machine time while remaining modest. |
| Battery & Electronics | Level 16 | **Level 15** | Removes one empty level before a well-sized advanced family. | Regular arrival roughly one to two days earlier; Casual gap is reduced without exposing endgame metals. |
| Precious Metals | Level 19 | **Level 18** | Reduces the long 15→19 gap and starts the broad premium cohort sooner but still after electronics. | More even late milestone cadence. |
| Catalyst Precious Metals | Level 21 | **Level 20** | Preserves ordering and follows the large Precious cohort with a small milestone. | Adds a clear intermediate event. |
| Aerospace & Refractory Metals | Level 23 | **Level 22** | Reduces an empty level and gives more room before the nuclear capstone. | Large cohort arrives earlier but gains a three-level mastery window before Uranium. |
| Nuclear Materials | Level 25 | **Keep Level 25** | Correct thematic capstone and aligned with the existing Industrialist title. | Uranium stays late; its real date improves only when XP/idle pacing is fixed. |

The proposed late curve becomes **13 → 15 → 18 → 20 → 22 → 25**. This smooths event spacing but cannot solve the 41× calendar-time spread between Casual and Optimizer by itself.

Before implementing Level gates, the runtime needs two explicit pacing decisions:

1. **Define the idle clock.** Either advance production, Contract periods and Lifetime state from elapsed wall time on load with a documented cap, or intentionally make the game session-only and rename/rebalance Daily/Weekly around active time. The current hybrid is unsuitable for calendar-based estimates.
2. **Normalize Contract XP throughput.** Contract capacity should reflect runnable production rather than merely configured theoretical output, and reward growth needs a target XP/hour band or per-period guardrail. Otherwise additional machines accelerate both fulfilment and reward size, creating multiplicative Level speed.

These are prerequisites for final numeric Level placement. Moving families by one Level cannot compensate for a progression that takes one profile five days and another nearly two years.

## Compact milestone table

Times are shown as **active hours / estimated calendar days** under the stated scenarios.

| Company Level | New family/families in current plan | Casual | Regular | Optimizer | Assessment |
|---:|---|---:|---:|---:|---|
| 2 | Field Crops | 3.2 h / 9.5 d | 1.2 h / 1.2 d | 0.4 h / 0.1 d | Too slow for Casual, almost immediate for Optimizer. |
| 3 | Process Minerals | 7.2 h / 21.7 d | 2.8 h / 2.8 d | 0.8 h / 0.3 d | Family size healthy; calendar variance unhealthy. |
| 4 | Food & Fiber Crops | 12.3 h / 37.0 d | 4.7 h / 4.7 d | 1.4 h / 0.5 d | Acceptable only in Regular scenario. |
| 5 | Gas & Elastomers | 18.7 h / 56.1 d | 7.2 h / 7.2 d | 2.1 h / 0.7 d | Large 46-option descendant cohort; monitor Guide load. |
| 7 | Chemical Minerals | 28.7 h / 86.0 d | 10.1 h / 10.1 d | 2.9 h / 1.0 d | Ordering good. |
| 9 | Common Alloy Metals | 42.7 h / 128.2 d | 14.2 h / 14.2 d | 4.1 h / 1.4 d | Content size and order good. |
| 11 | Advanced Alloy Metals | 57.9 h / 173.8 d | 18.4 h / 18.4 d | 5.4 h / 1.8 d | Useful light milestone. |
| 13 | Carbon & Specialty Minerals | 73.5 h / 220.4 d | 22.4 h / 22.4 d | 6.5 h / 2.2 d | Good transition point. |
| 16 | Battery & Electronics Feedstocks | 104.6 h / 313.9 d | 30.3 h / 30.3 d | 8.8 h / 2.9 d | Move provisionally to Level 15. |
| 19 | Precious Metals | 135.3 h / 405.8 d | 37.1 h / 37.1 d | 10.8 h / 3.6 d | 63-option cohort; move to 18 and stage presentation. |
| 21 | Catalyst Precious Metals | 160.8 h / 482.3 d | 42.9 h / 42.9 d | 12.5 h / 4.2 d | Small useful follow-up; move to 20. |
| 23 | Aerospace & Refractory Metals | 185.2 h / 555.6 d | 47.5 h / 47.5 d | 13.9 h / 4.6 d | 67-option spike; move to 22 and raise Assembler gate. |
| 25 | Nuclear Materials | 213.6 h / 640.9 d | 53.0 h / 53.0 d | 15.5 h / 5.2 d | Keep at Level 25; placement is right, runtime pace is not. |

## Final recommendations

- **120 / 60 / 30:** keep Processor 120 and Fabricator 60; change Assembler from **30 to 60** before implementation.
- **Level 1–25 distribution:** early ordering is sound; provisionally move the four late families to Levels **15 / 18 / 20 / 22** and retain the other family Levels.
- **Uranium:** keep at **Level 25** as the Industrialist capstone.
- **Largest risks:** missing offline/calendar advancement; Company XP available only through Contracts; Contract XP based on theoretical configured capacity; large Level-19 and Level-23 eligibility cohorts; strong divergence when a player ignores families or specializes in Contract output.
- **Implementation readiness:** **NEEDS ADJUSTMENT.** The dependency graph is ready, but the idle clock and Contract-XP throughput require explicit targets before the Level gates can be balanced with confidence.

No GUI was started. No code, save, test, plan JSON or existing progression-plan file was changed.
