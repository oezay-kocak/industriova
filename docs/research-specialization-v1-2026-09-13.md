# Product Specialization V1 — 2026-09-13

Product Specialization V1 is ready for manual playtest. The implementation uses the existing Research economy, command bus, modifier resolver, save system, and resource-picker components. Validation was offscreen only; no live game was launched.

## Structure

Every Industry tree now has **5 Majors, 4 ordinary clusters, and 4 optional specialization slots**. Each cluster retains six pure-domain nodes in three vertical lanes. Slots 1–4 attach only to Majors II–V, respectively. No slot appears in an ordinary node's prerequisites; all five Majors can be researched without buying a specialization.

The 15 Industry trees have 29 ordinary nodes and four side slots each. The six Company trees retain their 35 ordinary nodes and have no specialization slots. There are 645 ordinary nodes, including the original 105 Majors, plus 60 specialization slots across the catalog.

To reach the requested structure, the six ordinary nodes below Major V were retired from each Industry tree: 90 retired IDs in total. All 645 surviving ordinary IDs, bonuses, and icons are unchanged by this pass. The canonical map still assigns each of the 353 products to exactly one Industry domain.

## Selection and gameplay

- An attached Major unlocks its slot. Choosing a valid product costs exactly **1 RP**. The purchase command rechecks ownership, Major prerequisites, domain membership, and available RP before changing state.
- Products can be selected repeatedly, including the same product in all four slots. Already-purchased slots cannot be changed or purchased again until Full Respec.
- Each slot grants **+1.0% exact-product value**. The central setting is `specialization.value_bonus` in `src/production_zero/data/research_definitions.json`, authored by `scripts/build_research_content.py`. Slot definitions and gameplay/UI values read this configuration.
- Four matching slots add +4% product value. Company, Industry, and exact-product contributions remain additive in `core/modifiers.py`; the modifier cache includes the slot/product allocation.
- Existing Market sale-price and Contract quote functions use that resolver. A mixed Contract receives the exact-product bonus only on the matching product's contribution. Accepted Contract quotes and dispatched Market shipment prices retain their snapshots through respec.
- Specializations do not modify production speed, quantities, recipes, power, storage, or freight capacity. No Market base prices, Contract requirements, RP rewards, or normal Research bonus values were rebalanced.
- One Research Activity event is created per successful selection. Opening, searching, and leaving the picker creates no Activity or Inbox messages.

## State, saves, and respec

`ResearchState.specializations` stores a structured mapping from stable slot IDs to canonical product IDs. For example:

```json
{
  "industry.electronics.specialization.1": "microchip",
  "industry.electronics.specialization.2": "microchip"
}
```

The catalog defines each slot's Industry tree, attached Major, and 1-RP cost. Research spending includes both ordinary owned nodes and selected slots. Lifetime earned RP remains the authoritative total.

New Research payloads use revision 3. Revision-1 and revision-2 saves remain supported, with no selected slots when the field is absent. Existing legacy lane exceptions continue to round-trip. Ownership of retired trailing-cluster nodes is refunded automatically on load without reducing lifetime earned RP or removing surviving Majors. The 90 retired IDs are not reassigned to new slots.

Unknown slots, deleted products, products from the wrong domain, or selections whose Major no longer survives validation are cleared and refunded. Invalid structural payloads or allocations exceeding earned RP are rejected consistently with existing Research validation. SQLite continues to store the structured Research payload through its existing save path; no separate specialization database or calculation path was introduced.

Full Respec refunds ordinary and specialization RP, clears all selected products and their modifiers, preserves earned RP, and starts the existing 24-hour reset cooldown. Research and specialization purchases remain possible during that cooldown once their prerequisites are met. Existing Dev RP grants and allocation refunds also handle specialization state.

## UI

Specializations use compact 176×184 chamfered side chassis. They appear to the right of their attached Majors, connected by a single horizontal line. Main-node columns share the same reserved side space, maintaining aligned vertical lanes. Connections never traverse small nodes or other slots.

Locked slots use neutral frames and the existing lock icon. Available slots use safety yellow, an existing plus/build icon, and a clear 1-RP choice. Selected slots use the exact product icon, full wrapped product name, +1.0% product-value text, and researched cyan. No new artwork was generated.

The dedicated `SELECT SPECIALIZATION` screen occupies the Research content area. It reuses `SecondaryViewHeader`, `ResourceSelectionTile`, `ResourceSelectionGridHost`, and the existing resource-scroll setup used by Factory/Freight selection. It includes the Industry name, search, Back, canonical icons, current specialization count, and the projected exact-product total. Membership uses canonical domain IDs rather than names or recipe ancestry.

The responsive grid supports vertical scrolling, case-insensitive product-name/ID search, an empty-results state, keyboard tile activation, and return to the previous tree scroll position. Long grid names follow the shared picker's elision/full-tooltip convention. Selected side-slot names wrap and were measured for all 353 products. Electronics renders 52 choices in six columns at 1600×900; compact testing covers every Industry, including the four-product Oil & Gas domain.

## Validation

The focused command was run with `QT_QPA_PLATFORM=offscreen`:

```text
.venv/Scripts/python.exe -m pytest tests/test_research.py tests/test_research_ui.py tests/test_research_specialization.py tests/test_research_specialization_ui.py -q --tb=short
49 passed in 19.29s
```

Coverage includes:

- All Industry structures, slot attachments, independent main progression, and unchanged Company counts.
- Invalid/locked/insufficient-RP purchases, duplicates and distinct selections, atomic spending, and lock-until-respec behavior.
- Additive exact-product effects, no recipe inheritance, Market sale values, proportional mixed Contract values, and actual shipment/Contract payout snapshots.
- Repeated SQLite round-trips, immediate UI purchase persistence, revision-1/2 migration, retired-tail refunds, invalid selections, full refund, cooldown, and Dev support.
- Offscreen selection, search, Back, exact icons, slot and connector placement, main-tree typography, side-slot text fit for every product, and all-domain grids at 1600×900 and 1366×768.

`compileall -q src tests scripts` passed. `git -c core.safecrlf=false diff --check` passed; new/untracked edited files also received explicit whitespace checks. The preexisting dirty workspace was preserved.

**The full suite was not run. No live GUI was launched.** All game windows used the Qt offscreen platform. Persistence tests used temporary SQLite files; screenshot runs used an in-memory QA game.

## Six offscreen captures

All six captures were inspected for side placement, clear horizontal attachments, main-lane separation, text, states, picker readability, and exact product icons. The compact Research viewport is 1036 px wide with zero horizontal scrolling. Both tested picker sizes also have zero horizontal scrolling.

1. [Complete Industry tree with four side slots](../artifacts/ui/research-specialization-v1/01-industry-four-side-slots.png)
2. [Locked specialization slot](../artifacts/ui/research-specialization-v1/02-locked-slot.png)
3. [Available specialization slot](../artifacts/ui/research-specialization-v1/03-available-slot.png)
4. [Electronics product picker — 52 products](../artifacts/ui/research-specialization-v1/04-electronics-product-picker.png)
5. [Selected Microchip specialization](../artifacts/ui/research-specialization-v1/05-microchip-selected.png)
6. [Compact specialization layout — 1366×768](../artifacts/ui/research-specialization-v1/06-compact-specialization-1366x768.png)

Metadata: `artifacts/ui/research-specialization-v1/qa.json`. Regenerate using `.venv/Scripts/python.exe -m production_zero.tools.research_specialization_qa`; the module enforces offscreen mode.

## Manual-playtest verdict

**Ready for manual playtest.** The focused gameplay, migration, and UI checks pass. Manual feel and the first-pass +1% balance still require player evaluation; broad regression testing remains deferred as requested.
