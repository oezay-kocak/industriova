# Company XP and Resource Progression Simulation — 2026-09-07

Date: 2026-09-07\
Scope: design and pacing analysis only. This report changes no runtime logic, saves, tests, UI, level curve, or game definitions.

## Executive finding

The proposed multi-source model fixes the structural problem in the current Contract-only Company XP flow: ordinary productive play, production breadth, and Contracts all contribute, while every repeatable source has a calendar bound. With the originally proposed values, the model reaches Level 25 in approximately **86 / 35 / 23 calendar days** for Casual / Regular / Optimizer. Regular and Optimizer are inside their target corridors, while Casual misses its 60–80 day corridor narrowly.

One permitted calibration closes that gap without changing the Company level curve: raise each daily Efficiency milestone from **300 to 500 XP**. Separately, the post-four Regular Contract multiplier should be **0% rather than 25%**, because any positive residual remains an unlimited repeatable XP source. This barely affects normal modeled play but removes the clearest farming loophole.

The resulting model reaches Level 25 in approximately **80 / 30 / 21 days**. No single XP source exceeds 50% for any profile. Family curve B gives useful late families three levels earlier without changing total XP pacing and should be used with **120 / 60 / 60** Lifetime gates and Uranium at Level 25.

## Repository baseline

The active Company curve in `src/production_zero/core/company.py:44-49` costs:

`500 + 125 × current level + 18 × current level²`

The cumulative requirement for Level 25 is **137,700 XP**. `award_company_xp()` in `company.py:74-89` supports overflow across levels. The only active gameplay call found for that function is Contract completion in `src/production_zero/core/contracts.py:497-518`; production currently grants no Company XP.

Current Contract offers use production-value-derived XP. The fixed fallback values in `company.py:65-71` are 90 / 450 / 2,400 for Regular / Daily / Weekly, while new offers use dynamic budgets. Daily and Weekly boundaries currently depend on `state.market.elapsed_seconds` (`contracts.py:125-150`), which advances through `SimulationEngine.advance_time()` (`simulation.py:56-177`). The proposed UTC calendar counters therefore require new persistent calendar state; the present simulated-time counter cannot safely serve that role.

Accepted output is the correct production signal. The simulation records output after input, power, capacity, and storage checks; stalled or rejected production must not count toward Operations XP or mastery. The future implementation should attach XP accounting to that accepted-output result rather than configured capacity.

## Proposed XP model tested

### Operations XP

- Continuity: **40 XP per real productive minute**, counted once across the whole factory, capped at **1,200 XP per UTC day**.
- Catch-up: unused Continuity capacity may bank for at most **three days / 3,600 XP**. Banked capacity produces no XP by itself and can only be consumed during later productive minutes.
- Efficiency baseline: daily accepted Production Value thresholds at **25 / 100 / 300 / 750**, each worth **300 XP**, maximum **1,200 XP/day**.
- Efficiency recommendation: retain those thresholds and raise each award to **500 XP**, maximum **2,000 XP/day**.

Production Value in this model comes only from accepted newly produced output. Purchases, inventory, incoming freight, theoretical capacity, and blocked cycles contribute nothing.

### One-time mastery XP

| Stage | Resources | XP each | Total XP |
|---|---:|---:|---:|
| Extractor | 49 | 25 | 1,225 |
| Processor | 68 | 40 | 2,720 |
| Fabricator | 86 | 60 | 5,160 |
| Assembler | 150 | 100 | 15,000 |
| **First production total** | **353** |  | **24,105** |
| Extractor Family Mastery | 18 | 250 | **4,500** |
| **All mastery XP** |  |  | **28,605** |

The expected totals match the actual 353-resource plan exactly. First-production XP is awarded once per resource. Family mastery is awarded once after every Extractor root in that family has at least 120 accepted Lifetime Production.

### Contract XP

| Contract | Easy | Medium | Hard |
|---|---:|---:|---:|
| Regular | 100 | 150 | 225 |
| Daily | 600 | 900 | 1,350 |
| Weekly | 3,000 | 4,500 | 6,750 |

Cash and other economic rewards may continue to scale independently. The first four completed Regular Contracts per UTC day receive full Company XP. The calibrated recommendation gives later Regular Contracts **0 Company XP**; they retain their cash and other rewards.

## Simulation assumptions

This is a deterministic expected-value scenario model, not telemetry. It uses the active Company XP curve and the resource topology in the progression-plan JSON. It does not attempt to predict player hesitation, exact card draws, cash shortages, freight delays, or every storage layout.

| Profile | Sessions and activity | Accepted PV/min | Discovery pace | Contracts |
|---|---|---:|---|---|
| Casual | Four 35-minute sessions/week, averaging 20 min/day; partial catch-up use | 1.5 | 2 new resources per session | 0.4 Regular/day; 3 Dailies per week; 0.35 Weeklies/week; mostly Easy |
| Regular | 60 minutes daily | 5 | 5 new resources/session | 1.5 Regular/day; 85% of Dailies; 75% of Weeklies; mostly Medium |
| Optimizer | 180 minutes daily | 12 | 10 new resources/session | 8 Regular/day; every Daily/Weekly; mostly Hard |

Difficulty mixes are Casual 60/30/10%, Regular 25/50/25%, and Optimizer 10/30/60% for Easy/Medium/Hard. Discovery follows dependency order and cannot select a resource before its family and direct prerequisites are eligible. The model treats completion of all first productions in a root family as an optimistic proxy for reaching its 120-unit root thresholds. Because Extractors produce 120 units per minute at their common base rate, that proxy is reasonable once a root is installed and running, but card, slot, and setup delays can make actual mastery later.

The model assumes no complete offline production. Catch-up only increases the spendable Continuity allowance; subsequent accepted production is still mandatory.

## Baseline result: proposed values as written

| Profile | Level 25 calendar days | Active hours | Target | Result |
|---|---:|---:|---|---|
| Casual | 86 | 28.58 | 60–80 days | 6 days slow |
| Regular | 35 | 35.00 | 28–40 days | inside |
| Optimizer | 23 | 69.00 | 18–25 days | inside |

Baseline XP-source shares to Level 25:

| Source | Casual | Regular | Optimizer |
|---|---:|---:|---:|
| Continuity | 49.08% | 30.50% | 20.04% |
| Efficiency | 10.46% | 22.29% | 20.04% |
| First Production | 3.64% | 6.99% | 9.36% |
| Family Mastery | 1.63% | 2.36% | 2.72% |
| Regular | 3.15% | 5.79% | 15.87% |
| Daily | 20.24% | 19.68% | 18.95% |
| Weekly | 11.81% | 12.40% | 13.01% |

No source exceeds 50%, although Casual Continuity at 49.08% leaves little margin and confirms that simply increasing Continuity would be the wrong calibration.

## Calibrated recommendation

The recommended case changes only two permitted parameters: Efficiency milestone XP becomes 500, and Regular XP after the fourth daily completion becomes zero.

### Time to milestones with family curve B

| Level | Cumulative XP | Casual day / active h | Regular day / active h | Optimizer day / active h |
|---:|---:|---:|---:|---:|
| 5 | 3,790 | 3.05 / 0.61 | 0.82 / 0.82 | 0.51 / 1.53 |
| 10 | 15,255 | 8.68 / 2.73 | 3.19 / 3.19 | 2.22 / 6.66 |
| 15 | 38,395 | 22.33 / 7.19 | 8.27 / 8.27 | 5.74 / 17.21 |
| 18 | 59,755 | 34.42 / 11.33 | 12.93 / 12.93 | 8.98 / 26.94 |
| 20 | 77,710 | 45.21 / 14.71 | 16.91 / 16.91 | 11.63 / 34.90 |
| 22 | 98,973 | 57.26 / 18.82 | 21.41 / 21.41 | 14.82 / 44.47 |
| 25 | 137,700 | **80.00 / 26.25** | **30.00 / 30.00** | **21.00 / 63.00** |

Early levels arrive quickly for every profile; the model does not create a multi-week early game. Casual calendar time differs from active hours because the four-session weekly pattern includes inactive days and partial use of banked Continuity capacity.

### XP amounts and shares to Level 25

| Source | Casual XP / share | Regular XP / share | Optimizer XP / share |
|---|---:|---:|---:|
| Continuity | 63,000 / 45.75% | 36,000 / 26.14% | 25,200 / 18.30% |
| Efficiency | 22,500 / 16.34% | 45,000 / 32.68% | 42,000 / 30.50% |
| First Production | 4,410 / 3.20% | 8,250 / 5.99% | 11,595 / 8.42% |
| Family Mastery | 2,250 / 1.63% | 2,750 / 2.00% | 3,500 / 2.54% |
| Regular | 4,080 / 2.96% | 7,031 / 5.11% | 15,960 / 11.59% |
| Daily | 26,229 / 19.05% | 23,906 / 17.36% | 23,159 / 16.82% |
| Weekly | 15,231 / 11.06% | 14,763 / 10.72% | 16,286 / 11.83% |

No individual source exceeds 50%. Optimization remains valuable: the Optimizer reaches L25 about 2.3 times sooner than Casual in calendar days, while spending about 2.4 times as many active hours. The prior factor-of-100 outcome disappears. Better factories accelerate Efficiency, Contract completion, discoveries, and mastery, but hard daily caps prevent one optimized loop from erasing the whole progression.

## Family curve A versus B

Moving a family’s discovery level does not itself create XP, so both curves have the same modeled L25 totals and nearly identical calendar pacing. Their meaningful difference is when new content becomes available and how much time remains to use it before Uranium.

| Family | Curve A level | Curve B level | Casual day A → B | Regular day A → B | Optimizer day A → B |
|---|---:|---:|---:|---:|---:|
| Battery & Electronics | 16 | 15 | 26.32 → 22.33 | 9.67 → 8.27 | 6.72 → 5.74 |
| Precious Metals | 19 | 18 | 40.06 → 34.42 | 14.85 → 12.93 | 10.22 → 8.98 |
| Catalyst Precious Metals | 21 | 20 | 50.73 → 45.21 | 19.07 → 16.91 | 13.16 → 11.63 |
| Aerospace & Refractory Metals | 23 | 22 | 64.27 → 57.26 | 24.05 → 21.41 | 16.62 → 14.82 |
| Nuclear | 25 | 25 | 80.00 | 30.00 | 21.00 |

Curve B is preferable. It inserts late families before the next large XP wall, gives players time to pursue their chains, and separates Aerospace from the final Uranium moment. It also spreads the Level 19 and Level 23 content concentrations identified in the first audit without exposing Nuclear early.

## Lifetime-gate assessment

Keep **Processor 120 / Fabricator 60 / Assembler 60 per direct input**.

At common rates, one Extractor produces 120 units per minute, so a Processor prerequisite can be demonstrated quickly once the required root is installed. Processor outputs range from 10–60 units/minute; a 60-unit Fabricator gate takes roughly 1–6 productive minutes per input when produced serially. Fabricator outputs are usually 10 units/minute; a 60-unit Assembler gate is commonly about six minutes per input, or 6–24 minutes for one line to satisfy one-to-four inputs serially. Parallel factories shorten these times, as intended.

Assembler 60 is better than the earlier 30 proposal: 30 is often only three base cycles and barely demonstrates a working upstream line. Sixty remains small enough to avoid grind while making “operate the chain” meaningful. All direct inputs remain mandatory, so cross-family recipes cannot bypass their participating families.

Keep Uranium at **Level 25**. Curve B supplies earlier late-game material families, while Nuclear remains the final discovery and gives Level 25 a distinct capstone.

## Exploit and robustness matrix

| Scenario | Assessment | Finding |
|---|---|---|
| Leave one cheap machine running | Harmless / desired | It can earn Continuity only while accepted output is produced. The per-factory minute rule and daily cap prevent machine-count multiplication. Storage, input, and power blocks stop credit. This is a valid idle baseline. |
| Produce only the cheapest product | Harmless, self-limiting | It earns Continuity and perhaps the first Efficiency threshold, but sacrifices higher PV thresholds, breadth mastery, and many useful Contract targets. |
| Maximize daily Production Value | Desired | Optimization reaches thresholds sooner but receives at most 2,000 recommended Efficiency XP/day. Surplus PV still has economic value without infinite Company XP. |
| Farm Regular Contracts after four | Exploitable at 25% | Regular offers regenerate immediately. Any positive residual is mathematically unlimited. Set post-four Company XP to 0%; leave cash rewards intact. |
| Ignore broad resource progression | Problematic but bounded | Operations and Contracts can still level the company, but the player gives up up to 28,605 one-time mastery XP and downstream capability. The Production Guide should surface next mastery and chain unlocks. |
| Rush Family Mastery | Desired | Fast organization is rewarded, but only once per family and only 4,500 XP total. The 120 accepted-unit requirement prevents configuration-only credit. |
| Return after several inactive days | Desired / bounded | The three-day bank supports clustered Casual sessions. In the modeled four-by-35-minute week it allows about 5,600 Continuity XP/week instead of 4,800 without banking, a 16.7% benefit. It never grants login XP. |
| Play around UTC day/week rollover | Problematic but bounded | A player can intentionally complete work on both sides of a boundary, but only accesses two legitimate periods. UI must show UTC reset times clearly. |
| Change system clock, reload, or replay saves | Exploitable without safeguards | The implementation needs persisted UTC period IDs/high-water marks, monotonic completion counters, idempotent milestone/mastery flags, and rejection of backward local-clock resets. Calendar authority should not be derived solely from editable save timestamps. |

AFK/login farming is prevented only if “productive minute” is derived from accepted output and accumulated from actual simulation intervals. Opening the game, configuring a machine, or restoring a full bank must award nothing on its own.

## Sensitivity analysis

All rows use family curve B and change only the named permitted parameter from the 300-XP baseline.

| Case | Casual L25 day | Regular L25 day | Optimizer L25 day |
|---|---:|---:|---:|
| Baseline | 86 | 35 | 23 |
| Continuity 35 XP/min | 91 | 35 | 23 |
| Continuity 45 XP/min | 81 | 35 | 23 |
| Continuity cap 1,000 | 86 | 37 | 24 |
| Continuity cap 1,400 | 86 | 33 | 22 |
| Efficiency 250 each | 87 | 36 | 24 |
| Efficiency 350 each | 84 | 34 | 22 |
| **Efficiency 500 each** | **80** | **30** | **21** |
| Regular post-four 10% | 86 | 35 | 24 |
| Regular post-four 0% | 86 | 35 | 24 |
| Regular bands −15% | 86 | 35 | 24 |
| Regular bands +15% | 85 | 35 | 23 |
| Daily bands −15% | 88 | 36 | 24 |
| Daily bands +15% | 83 | 34 | 23 |
| Weekly bands −15% | 87 | 36 | 24 |
| Weekly bands +15% | 84 | 34 | 23 |

Increasing Continuity to 45 nearly reaches the Casual target but would make its already dominant source even larger. Efficiency 500 instead rewards actual productive value, brings all profiles into range, and produces a healthier source mix. The Regular residual change has little effect on expected normal play but is decisive for mathematical exploit resistance.

## Final implementation parameters

- Keep the current Company XP level curve; no curve change is needed.
- Continuity: **40 XP/productive minute**, **1,200 XP daily cap**, up to **3,600 banked XP / three missed days**.
- Efficiency thresholds: **25 / 100 / 300 / 750 accepted Production Value per UTC day**.
- Efficiency awards: **500 XP per threshold**, maximum **2,000 XP/day**.
- First-production XP: **25 / 40 / 60 / 100** for Extractor / Processor / Fabricator / Assembler.
- Family mastery: **250 XP**, once, after every Extractor root in the family reaches 120 accepted Lifetime Production.
- Regular: **100 / 150 / 225 XP**, first four per UTC day; subsequent completions grant **0 Company XP**.
- Daily: **600 / 900 / 1,350 XP** per UTC day.
- Weekly: **3,000 / 4,500 / 6,750 XP** per fixed UTC week.
- Family discovery: **curve B** (late families at 15 / 18 / 20 / 22 / 25).
- Lifetime gates: **120 / 60 / 60** for Processor / Fabricator / Assembler.
- Uranium: **Level 25**.
- Production Guide: show the next family level, every required direct-input Lifetime counter, first-production status, and family-mastery progress.
- Factory resource selection: list eligible recipes consistently with the same level, family, and direct-input predicates, with unmet requirements visible rather than ambiguous.
- Save data: persist UTC period identities, cap/bank balances, four-full-Regular counter, Efficiency threshold flags, first-production flags, Lifetime counters, and family-mastery flags idempotently.

The machine-readable companion `docs/company_xp_resource_progression_simulation_2026-09-07.json` contains parameters, profile assumptions, both family curves, source totals, milestone results, and the sensitivity cases. It is a reproducible model artifact, not runtime configuration.

## Final verdict

**READY FOR IMPLEMENTATION**

With Efficiency set to 500 XP per milestone and post-four Regular Company XP set to zero, all three modeled profiles land inside their target corridors, no XP source exceeds 50%, optimization retains a clear advantage, and repeatable XP is bounded. Curve B plus 120 / 60 / 60 gates provides the smoother content cadence while preserving Uranium as the Level 25 capstone.
