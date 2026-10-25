# Factory Capacity Split Audit — 2026-09-09

## Executive summary

The current runtime starts a new game with **one Hall**, **two unlocked Lines per Hall**, and **three unlocked slots per active Line**: **6 usable Factory slots initially**. Every Hall is structurally allocated for **6 Lines × 10 slots = 60 slots**. Lines 3–6 and slots 4–10 are unlocked independently per Hall using cash only.

The most important audit finding is that the runtime has **no maximum Hall count**. `PurchaseHall.apply()` can add another Hall whenever the player can pay the rising cash price; neither the command nor either Factory UI checks a Hall cap, Company Level, or resource requirement. Consequently:

- bounded maximum per Hall: **60 slots**;
- current maximum number of Halls: **unbounded**;
- current maximum total Factory capacity: **unbounded**;
- a finite percentage reduction versus the true current global maximum is therefore **not mathematically meaningful**.

For scenario comparison only, this report uses a clearly labelled **three-Hall planning benchmark of 180 slots**. Three Halls are demonstrably supported and explicitly exercised by the tests, but **three is not a runtime maximum**.

Runtime card data contains four installable machine families and five Energy families. The four machine families expose 353 selectable production options: 49 Extractor, 68 Processor, 86 Fabricator, and 150 Assembler. Energy adds five installable definitions. Thus the split removes 6 of 9 installable non-Freight definition families (66.7%), but only 54 of 358 definition/production choices (15.1%). This difference matters: family count argues for a large cut, while production breadth argues that Factory still needs most of the useful configurable capacity.

The recommended capacity policy is therefore to establish a real Hall cap, remove one Line per Hall, and preserve the familiar 10-slot visual rhythm. A **3 Hall × 5 Line × 10 slot** Factory has 150 maximum slots, 16.7% fewer than the three-Hall current-geometry benchmark. Suggested future Resources and Energy envelopes are 24–36 and 12–18 slots respectively, making the combined split envelope 186–204 slots. That is a modest 3.3–13.3% increase over the 180-slot benchmark, not three copies of the old Factory. These are planning ranges, not implementation commitments.

## Scope and source-of-truth rule

This is a read-only repository audit. No runtime code, tests, saves, or board implementation was changed. Runtime Python and loaded JSON definitions take precedence over older documents. The only file added is this report.

## Current Factory capacity

| Measure | Runtime value | Source of truth |
|---|---:|---|
| Starting Halls | 1 | `_create_initial_state()` builds `hall-1` |
| Maximum Halls | **No cap / unbounded** | `PurchaseHall.apply()` has no maximum check |
| Starting unlocked Lines per Hall | 2 | `START_UNLOCKED_FACTORY_LINES = 2` |
| Maximum Lines per Hall | 6 | `MAX_FACTORY_LINES = 6` |
| Starting unlocked slots per Line | 3 | `START_FACTORY_SLOTS_PER_LINE = 3` |
| Maximum slots per Line | 10 | `MAX_FACTORY_SLOTS_PER_LINE = 10` |
| Physical `HallSlot` objects allocated per Hall | 60 | `FactoryHall.__post_init__()` |
| Initially usable slots per new Hall | 6 | 2 Lines × 3 slots |
| Maximum usable slots per Hall | 60 | 6 Lines × 10 slots |
| Initial total Factory capacity | **6** | 1 starting Hall × 6 usable slots |
| Maximum total Factory capacity | **Unbounded** | unbounded Halls × 60 slots/Hall |
| Currency/gates | Cash only | no Company Level or resource checks in expansion commands |

`FactoryHall(..., slot_count=6)` and `PurchaseHall.slot_count = 6` look configurable, but `FactoryHall.__post_init__()` recomputes `slot_count` from the generated production lines. Under the default structure, a newly constructed Hall always ends at 6 usable slots regardless of that constructor value. This is a compatibility-shaped field, not an independent current capacity control.

## Unlock and expansion progression

### Hall construction

The first Hall is granted during new-game initialization at no purchase cost. Subsequent Halls use:

`hall_purchase_price(existing_hall_count) = 1000 + max(0, existing_hall_count - 1) × 500`

| Build step | Existing Halls | Cash cost | Capacity immediately gained | Capacity after fully expanding the new Hall | Resource requirement | Level requirement |
|---|---:|---:|---:|---:|---|---|
| Starting Hall 1 | 0 | $0 | +6 | 60 | none | none |
| Build Hall 2 | 1 | $1,000 | +6 | +60 | none | none |
| Build Hall 3 | 2 | $1,500 | +6 | +60 | none | none |
| Build Hall 4 | 3 | $2,000 | +6 | +60 | none | none |
| Build Hall `H` | `H-1` | `$1,000 + $500 × (H-2)` | +6 | +60 | none | none |

There is no final Hall-build step because there is no Hall cap.

### Line unlocks within every Hall

Lines 1 and 2 start unlocked with three slots each. Each later Line unlock gives three slots immediately.

| Line | Initial state | Unlock cash | Capacity gained | Cumulative Hall capacity before slot upgrades | Resource requirement | Level requirement |
|---:|---|---:|---:|---:|---|---|
| 1 | unlocked | $0 | +3 | 3 | none | none |
| 2 | unlocked | $0 | +3 | 6 | none | none |
| 3 | locked | $750 | +3 | 9 | none | none |
| 4 | locked | $1,250 | +3 | 12 | none | none |
| 5 | locked | $1,750 | +3 | 15 | none | none |
| 6 | locked | $2,250 | +3 | 18 | none | none |

Unlocking all four locked Lines costs **$6,000 per Hall** and adds 12 usable slots.

### Slot unlocks within every unlocked Line

Each slot unlock adds exactly one slot. The formula is:

`factory_slot_unlock_cost(line_number, slot_number) = 120 + (slot_number - 4) × 90 + (line_number - 1) × 35`

| Line | Slot 4 | Slot 5 | Slot 6 | Slot 7 | Slot 8 | Slot 9 | Slot 10 | All seven |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | $120 | $210 | $300 | $390 | $480 | $570 | $660 | $2,730 |
| 2 | $155 | $245 | $335 | $425 | $515 | $605 | $695 | $2,975 |
| 3 | $190 | $280 | $370 | $460 | $550 | $640 | $730 | $3,220 |
| 4 | $225 | $315 | $405 | $495 | $585 | $675 | $765 | $3,465 |
| 5 | $260 | $350 | $440 | $530 | $620 | $710 | $800 | $3,710 |
| 6 | $295 | $385 | $475 | $565 | $655 | $745 | $835 | $3,955 |

All 42 slot unlocks cost **$20,055 per Hall** and add 42 slots. Fully expanding a new Hall from 6 to 60 slots therefore costs **$26,055 after construction**: $6,000 for Lines plus $20,055 for slots. The Hall purchase price is additional.

Expansion can be interleaved: the runtime does not require filling an earlier Line before unlocking a later Line, and it imposes no Company Level or material requirement. A locked Line must be unlocked before its slots can be expanded.

## Capacity gained at each kind of step

| Expansion action | Immediate capacity gain | Resulting local ceiling |
|---|---:|---:|
| Start game with Hall 1 | +6 total | 6 total initially |
| Purchase any additional Hall | +6 total immediately | new Hall can later reach 60 |
| Unlock any of Lines 3–6 | +3 in that Hall | that Line starts at 3 |
| Unlock any of slots 4–10 | +1 in that Hall | that Line can reach 10 |
| Fully expand one new Hall | +54 beyond its starting 6 | 60 per Hall |

For `H` Halls, current usable capacity ranges from `6H` when all are new to `60H` when all are fully expanded. Since `H` is unbounded, so is total capacity.

## Runtime card/category audit

Counts below come from loading `src/production_zero/data/game_definitions.json` through the actual `load_card_definitions()` parser, de-duplicated by loaded definition object. Freight is excluded because it is not allowed in Hall slots and has its own facilities.

| Category | Installable definition families | Selectable production options | Inputless options/definitions | Post-split destination |
|---|---:|---:|---:|---|
| Extractor | 1 (`machine.extractor`) | 49 | 49 | Resources |
| Energy | 5 | 5 definition choices | 2 inputless; 3 fuel-consuming | Energy |
| Processor | 1 (`machine.processor`) | 68 | 0 | Factory |
| Fabricator | 1 (`machine.fabricator`) | 86 | 0 | Factory |
| Assembler | 1 (`machine.assembler`) | 150 | 0 | Factory |
| **Total installed in Factory-compatible slots** | **9** | **358 choices** | **51 inputless choices** | — |

The five Energy definitions are Solar Array, Wind Turbine, Coal Power Plant, Gas Power Plant, and Nuclear Power Plant. Solar and Wind are inputless. Coal, Gas, and Nuclear consume fuel, so Energy is not synonymous with inputless production.

### Share conceptually removed

- By installable definition-family count: Extractor + Energy removes **6/9 = 66.7%**; Factory retains 33.3%.
- By configurable choice count: 49 Extractor targets + 5 Energy definitions removes **54/358 = 15.1%**; Factory retains **304/358 = 84.9%**.
- By machine production-option count alone: Extractor removes **49/353 = 13.9%**.
- In the new-game sample inventory, there are three Extractor cards, one Energy card, and two Processor cards; four of six sample cards (66.7%) belong to moving categories. None is installed automatically in `_create_initial_state()`, so this is inventory composition, not observed slot occupancy.

There is no repository telemetry or canonical player save describing real installed-card occupancy. This audit deliberately did not inspect or mutate external saves. Therefore a measured percentage of live player slot usage cannot be claimed.

### Special cases

- `InstallCardInHall.apply()` validates only `CardKind.MACHINE` or `CardKind.ENERGY`. It does not independently restrict `MachineType`; all four machine families are consequently allowed.
- Extractor is one reusable card definition with 49 production targets, not 49 card definitions.
- Processor, Fabricator, and Assembler likewise use one card family each while exposing 68, 86, and 150 recipes/targets.
- Energy has five distinct card definitions and no `production_options` collection.
- Three Energy cards require produced fuel, so they create cross-board dependencies after the split.
- Legacy enum aliases (`MINING`, `SMELTING`, `ASSEMBLY`) map to canonical values; legacy definition IDs normalize to Extractor or Processor families on load.

## Was current maximum capacity balanced for all five categories together?

The runtime clearly permits Extractor, Energy, Processor, Fabricator, and Assembler cards to compete for the same Hall slots, and simulation iterates all Hall slots. In that limited structural sense, the current Hall envelope was built to host all five categories together.

There is **no evidence of a completed numerical balance target**, however:

- no Hall cap exists;
- no capacity unlock is tied to Company Level or production progression;
- no resource cost is charged for Halls, Lines, or slots despite the presence of an `industrial_hall_modules` resource elsewhere in production data;
- no configuration declares intended category allocations or target occupancy;
- the capacity-sensitive contract estimator is driven by configured machines, not a target Hall count;
- tests verify mechanics through at least three Halls but do not assert three as a maximum.

Conclusion: capacity was functionally designed for the combined board, but the repository does not support the stronger claim that a finite global maximum was balanced around a specific combined-card mix. The unbounded Hall purchase path is itself the dominant balance risk.

## Post-split Factory capacity scenarios

Because the true current global maximum is unbounded, the requested reduction percentage cannot honestly use it as a finite denominator. The percentages below use the **three-Hall current-geometry planning benchmark: 3 × 6 × 10 = 180 slots**. They are decision aids, not claims about a runtime cap.

All options retain the current new-game opening of one Hall with two Lines × three slots = **6 initial slots**. “Halls” means the proposed maximum Hall count.

| Option | Halls | Lines/Hall | Slots/Line | Initial capacity | Maximum capacity | Reduction vs 180-slot benchmark | Gameplay reasoning |
|---|---:|---:|---:|---:|---:|---:|---|
| Conservative | 3 | 6 | 10 | 6 | 180 | 0.0% | Adds the essential Hall cap but otherwise preserves all current Factory room. Safest for highly parallel Processor/Fabricator/Assembler chains; weakest protection against total split-board inflation. |
| **Recommended** | **3** | **5** | **10** | **6** | **150** | **16.7%** | Retains most capacity because downstream production represents 84.9% of configurable choices, while removing one whole track per Hall and establishing a finite ceiling. Preserves the 10-slot track rhythm and granular slot unlocks. |
| Aggressive reduction | 2 | 5 | 10 | 6 | 100 | 44.4% | Strongly controls total infrastructure and makes specialization meaningful, but risks excessive recipe swapping and constraining multi-stage parallel chains among 304 retained downstream choices. |

Normalized per Hall, the recommended 5 × 10 layout is also a 16.7% reduction from the current 6 × 10 layout. The conservative layout has no geometric reduction; its meaningful change is replacing an unbounded Hall count with a cap. The aggressive option combines that cap with fewer Halls and Lines.

## Recommended Factory capacity

Use a combination, weighted toward **fewer Halls and fewer Lines per Hall**:

1. Add a real maximum of three Halls. This is the only change that closes the current unbounded-capacity loophole.
2. Reduce the Hall from six to five Lines. A whole-Line cut is visually legible and removes capacity in meaningful 10-slot blocks.
3. Keep ten slots per Line. This preserves Factory V2's established horizontal rhythm, progressive one-slot purchases, card sizing, and player muscle memory.
4. Keep the initial 2 × 3 = 6 usable slots unless early-game pacing data later shows that the separated boards grant those opening slots for free as well. Board-specific starting capacity should be budgeted as part of combined infrastructure, not copied automatically.

Removing slots per Line should be the last lever. Factory V2 explicitly renders ten positions across every track and the slot-cost curve is the most granular progression layer. Shortening tracks creates more UI and test churn while doing less to communicate board-scale scarcity than removing one Line.

## Suggested Resources and Energy target ranges

These are non-binding planning ranges. They intentionally avoid reproducing a full 60-slot Hall on each new board.

| Board | Sensible maximum range | Why |
|---|---:|---|
| Resources | **24–36 slots** | Must support multiple simultaneous roots across future Mining/Drilling/Agriculture families, but one configurable producer can switch among many of the 49 current raw targets. Start near 24 and justify movement toward 36 with playtest concurrency data. |
| Energy | **12–18 slots** | Only five current Energy definitions exist; output scaling and fuel mix matter more than a large slot grid. Twelve supports redundancy and mixed generation without gifting another Factory-sized board. |

With the recommended Factory maximum of 150, the proposed combined maximum is:

| Split envelope | Factory | Resources | Energy | New total | Difference vs 180 benchmark |
|---|---:|---:|---:|---:|---:|
| Low | 150 | 24 | 12 | 186 | +3.3% |
| High | 150 | 36 | 18 | 204 | +13.3% |

The comparison is necessarily against the 180-slot planning benchmark, not the unbounded runtime maximum. The eventual design should also compare **starting** combined capacity: if each board receives 6 free slots, the split would start at 18 versus today's 6. Avoid that automatic tripling; stagger board unlocks, reduce starting slots on the new boards, or charge for their initial infrastructure.

## Relevant source files and exact symbols

### Defaults, limits, progression, and costs

| Path | Symbols / influence |
|---|---|
| `src/production_zero/core/state.py` | `MAX_FACTORY_LINES`, `MAX_FACTORY_SLOTS_PER_LINE`, `START_UNLOCKED_FACTORY_LINES`, `START_FACTORY_SLOTS_PER_LINE`, `FactoryHall.__post_init__`, `FactoryHall.unlocked_slot_indexes`, `factory_line_slot_index`, `next_factory_slot_index`, `factory_line_unlock_cost`, `factory_slot_unlock_cost`, `_default_production_lines`, `ProductionLine`, `HallSlot`, `GameState.halls` |
| `src/production_zero/core/economy.py` | `hall_purchase_price` |
| `src/production_zero/core/commands.py` | `BuildHall.apply`, `PurchaseHall.apply`, `UnlockProductionLine.apply`, `UnlockProductionSlot.apply`, `InstallCardInHall.apply`, `RemoveCardFromHall.apply` |
| `src/production_zero/ui/main_window.py` | `_create_initial_state` grants Hall 1 and the sample card inventory; `_copy_state` replaces `halls` during reset/load flows |

### Runtime cards, progression, and systems influenced by occupancy

| Path | Symbols / influence |
|---|---|
| `src/production_zero/data/game_definitions.json` | authoritative machine and Energy family definitions plus all production options |
| `src/production_zero/data/definitions.py` | `load_card_definitions`, `_parse_card_definition`, `_parse_machine_type`, `normalize_legacy_card_definition_id`, `LEGACY_CARD_FAMILY_IDS` |
| `src/production_zero/core/definitions.py` | `MachineDefinition`, `ProductionOptionDefinition`, `EnergyDefinition`, `CardDefinition` |
| `src/production_zero/core/enums.py` | `CardKind`, `MachineType`, `EnergyType`, including legacy aliases |
| `src/production_zero/data/resource_progression.json` | Company Level and dependency gates for the 353 production options; affects demand for parallel capacity, not Hall/Line/slot unlocking |
| `src/production_zero/core/progression.py` | initializes, evaluates, and migrates production-option unlock state; no Factory structural gate |
| `src/production_zero/core/simulation.py` | iterates installed Hall cards for Energy and machine production; all Halls share global resources and Energy |
| `src/production_zero/core/analytics.py` | reads installed Hall slots for production/consumption analytics |
| `src/production_zero/core/contracts.py` and `src/production_zero/core/production_values.py` | configured production capacity influences contract sizing/value, so a capacity reduction can indirectly alter economy pacing |
| `src/production_zero/core/inventory.py`, `src/production_zero/core/supply.py`, `src/production_zero/core/packs.py`, `src/production_zero/core/crafting.py` | expose/acquire machine and Energy definitions that may be installed; category counts and availability affect pressure on slots |

### UI

| Path | Symbols / influence |
|---|---|
| `src/production_zero/ui/factory_view.py` | `FactoryViewBase._refresh_build_hall_button`, `_purchase_hall`, `_unlock_line`, `_unlock_slot`, Hall selection/tree, card filters, production selection, and legacy/base Factory presentation |
| `src/production_zero/ui/factory_view_v2.py` | `FactoryViewV2._refresh_hall_tree`, `_hall_nav_label`, `_refresh_content`, `_build_line_panel`; loops over every `production_line` and renders `MAX_FACTORY_SLOTS_PER_LINE` positions |
| `src/production_zero/ui/game_ui/rendering/factory.py` | Factory board/card visual rendering; capacity changes can affect geometry assumptions even though it does not own the limits |
| `src/production_zero/ui/theme.py` | Factory/Hall/Line/locked-slot styling and fixed visual rhythm |
| `src/production_zero/ui/dev_tools_view.py` | traverses Hall production lines and can affect audit/demo state behavior |

### Save/load and migration

| Path | Symbols / influence |
|---|---|
| `src/production_zero/persistence/sqlite_store.py` | `serialize_game_state` writes `halls`, every 60-element `slots` list, `slot_count`, and `production_lines`; `deserialize_game_state` reconstructs them and invokes `FactoryHall.__post_init__` |
| `src/production_zero/persistence/dev_save_store.py` | `SAVE_VERSION = 1`, `DevJsonSaveStore.save/load`; wraps the same serializer/deserializer without a Factory-specific schema version |
| `src/production_zero/data/definitions.py` | normalizes legacy card family IDs while loading saved cards |
| `src/production_zero/core/progression.py` | `migrate_production_progress` migrates production unlock data, but not Hall topology or board ownership |

No dedicated Hall-cap, Hall-topology, or Factory-to-board migration exists.

### Tests that directly define or exercise Factory capacity

| Path | Coverage relevant to this decision |
|---|---|
| `tests/test_commands_and_simulation.py` | asserts 60 physical slots, 6 Lines, 2 initially unlocked Lines, 3 starting slots, 10-slot maximum; checks Hall-local expansion, cash failures, multiple Halls, and all-Hall simulation |
| `tests/test_factory_view_v2.py` | exercises V2 locked-slot and locked-Line interactions and Energy installation |
| `tests/test_factory_ui.py` | extensive Hall/Line/slot UI behavior, ten-position tracks, independent multi-Hall state, Hall purchase through Hall 3, inventory/category selection, and card installation |
| `tests/test_sqlite_store.py` | round-trips Hall slots, Lines, unlock state, and multiple Halls |
| `tests/test_dev_save_store.py` | round-trips the serialized Hall state through developer JSON saves |
| `tests/test_analytics.py` | mixed Energy/Extractor/Processor Hall occupancy and analytics |
| `tests/test_production_progression.py` | installed machine selection and progression with Hall slots |
| `tests/test_rarity_only_progression.py` | installed cards and canonical family behavior after legacy progression removal |
| `tests/test_card_stacks.py`, `tests/test_crafting.py`, `tests/test_recycling.py`, `tests/test_supply.py` | installed-card exclusion and machine/Energy card lifecycle around Hall occupancy |
| `tests/test_resources_and_cash.py`, `tests/test_playtest_fix_pass.py` | Factory resource/cash and UI regression behavior influenced by Hall contents |

The broader `tests/test_factory_ui.py` suite contains many geometry and object-name assertions; even capacity-only implementation will have a large UI regression surface.

## Save and migration risks

1. **Over-cap existing saves:** introducing a Hall cap can leave saves with more Halls than allowed because current purchases are unlimited.
2. **Removed Lines or slots may be occupied:** reducing to five Lines or changing slots per Line can strand installed cards. Silent truncation would lose placement and potentially production selection state.
3. **Physical storage is fixed at 60 slots:** `FactoryHall.__post_init__()` pads short saved slot arrays to the current 60-slot structural count. Changing constants without an explicit schema/migration policy can remap or orphan indexes.
4. **Indexes are not geometrically stable:** `next_factory_slot_index()` assigns the next unused global Hall index rather than using `factory_line_slot_index()`. Existing expanded Lines can contain non-contiguous indexes (and tests explicitly preserve such layouts). Migration must use each Line's stored `slot_indexes`, not assume row-major geometry.
5. **Board ownership is absent:** saves store cards in `state.halls[*].slots`; they do not distinguish Factory, Resources, and Energy boards. Moving Extractor/Energy cards requires an explicit, lossless relocation policy.
6. **No capacity schema version:** the developer wrapper has `SAVE_VERSION = 1`, but Hall topology has no own version. SQLite stores a JSON state payload with no top-level migration dispatcher for this split.
7. **Dangling machine production state:** Extractors have entries in `state.machine_production`. Moving their cards without moving/retaining those records can reset target selection and progress.
8. **Energy fuel dependencies:** relocating Energy must preserve its access to global fuel stocks and simulation ordering.
9. **Excess cards need a safe destination:** if reduced Factory capacity is already full after moving categories, displaced retained machines must return to inventory rather than be dropped.
10. **Reset/new-game parity:** `_create_initial_state`, dev reset copying, JSON load, and SQLite load must converge on the same topology after any future implementation.

## Test implications for a future implementation

No tests were changed in this audit. A later implementation should add or revise coverage for:

- a hard Hall cap in both command and UI paths, including direct command dispatch;
- exact starting and maximum capacity for all three boards;
- per-board allowed card categories and rejection at the command layer, not merely UI filtering;
- migration of over-cap Halls and occupied removed Lines/slots without card loss;
- preservation of saved non-contiguous `slot_indexes`;
- Extractor production selection/progress across relocation;
- Energy cards, including fuel consumers, across relocation;
- combined starting and maximum infrastructure budgets;
- contract/production-value pacing after installed capacity changes;
- V2 track geometry with five Lines while retaining ten slot positions;
- serialization round trips and an explicit version transition;
- inventory stack exclusion across all three installation locations;
- analytics and resource summaries across the new board boundaries.

Existing assertions of six Lines, 60 physical slots, multi-Hall behavior, ten slot widgets, and mixed-category Hall installation should be treated as deliberate migration targets, not mechanically updated snapshots.

## Unresolved questions

1. What should happen to existing saves with more than the proposed maximum Halls?
2. If Line 6 contains retained machines, should migration compact them into free Factory slots, return them to inventory, or grandfather the Hall topology?
3. Should Resources and Energy begin unlocked, or should their initial capacity replace rather than add to today's six free slots?
4. Are Sites/Plants capped globally from day one, and are their build costs cash-only or tied to produced construction resources?
5. How many distinct raw-resource producers must run concurrently in target playstyles? The 49 Extractor choices do not imply 49 simultaneous slots.
6. What Energy redundancy target is desired at early, mid, and late game, especially for fuel transitions?
7. Should Hall/Line/slot expansion acquire Company Level gates? None exist today.
8. Should `industrial_hall_modules` eventually become a Hall build requirement? It currently has no relationship to `PurchaseHall`.
9. Is the three-Hall planning benchmark acceptable for balance comparison, or should telemetry/playtest goals define a different finite old-world reference before final numbers are locked?
10. Should Factory capacity influence contract sizing after the split using only Factory machines, or all production boards?

RECOMMENDED POST-SPLIT FACTORY: 3 halls × 5 lines × 10 slots = 150 maximum slots

RATIONALE: Establishing a three-Hall cap fixes the current unbounded global capacity, removing one Line per Hall provides a measured 16.7% cut against the explicit 180-slot three-Hall benchmark, and retaining ten slots per Line preserves Factory V2's established visual rhythm and granular slot progression while leaving adequate parallel room for the 304 retained Processor, Fabricator, and Assembler production choices.
