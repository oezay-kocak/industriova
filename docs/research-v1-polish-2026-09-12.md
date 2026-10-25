# Research V1 structure and visual polish — 2026-09-12

The focused polish pass is complete. The rendered Forestry section was inspected against the requested three-lane diagram. This pass keeps the existing Research architecture and does not introduce a specialization system.

## Tree structure and content

Every section in all 21 trees now follows this progression:

```text
              MAJOR
                |
       +--------+--------+
       |        |        |
      A1       B1       C1
       |        |        |
      A2       B2       C2
       |        |        |
       +--------+--------+
                |
              MAJOR
```

First-row nodes require only the preceding Major. Each second-row node requires only the first-row node in its own lane. The next Major requires the three second-row nodes. There are no cross-lane or horizontal prerequisites. All 105 sections are covered by catalog tests; rendered connection geometry is checked across all 21 trees.

The renderer emits each split/merge bus once, connects adjacent small nodes vertically, and uses no perimeter routes. Each complete tree has 60 unique orthogonal connection segments. Muted cyan indicates satisfied prerequisites and neutral steel gray indicates pending prerequisites.

The generated catalog still contains 735 nodes, including 105 Majors. All 735 IDs and all icon references are preserved. Exactly 399 node records changed: 315 second-row nodes received lane-specific prerequisites and 84 later Majors received three-node prerequisites. Within those 399 records, 75 former Industry product-specialization nodes were converted to ordinary +0.2% domain-value nodes. Zero Industry product-specialization effects remain. The exact-product modifier resolver remains available and has explicit coverage using an additional product modifier. The 353-product domain mapping is unchanged.

## Research UI

- Research-specific surfaces now use warm neutral concrete, graphite, near-black, and steel gray. Available nodes retain safety yellow; researched nodes use the existing PZ cyan. The global Theme and icon assets were not changed.
- The sidebar heading is larger, bold, black, and split over two lines. Group labels and category labels are stronger. Selected categories use graphite and a yellow accent.
- Sidebar movement came from changing the left border from 1 px to 4 px on selection. All states now reserve the same 4 px border and use the same padding, font size, and weight. Tests compare button bounds, size hints, font metrics, and content rectangles between selected and hovered/unselected states.
- The selected-tree title is 29 px and bold. The secondary line shows the actual sum of purchased bonuses in that tree and its researched-node count; it excludes company-wide spending.
- The RP counter is a compact orange rounded rectangle with large dark text. Full Respec uses the canonical safety-yellow action color with hover, pressed, and neutral disabled treatments. Active cooldown appears immediately below the button, only when relevant.
- The permanent Earn RP footer, respec helper strip, and bottom purchase/status footer are removed. Purchase outcomes update the header and nodes. Errors and refund feedback use a temporary overlay without a layout slot. The existing inline respec confirmation remains.
- Node typography is larger and bolder: eyebrow 12–13 px, bonus 25–29 px, effect 14–16 px, and state 11–12 px. Small nodes use light text; Major nodes use dark text on neutral light metal. Node height accommodates stronger type and wrapped effect labels.
- Chassis artifacts came from an unclipped left accent rectangle extending into the lower-left chamfer and an independently painted top highlight. The accent is now clipped to the inset chassis path, followed by one continuous outline with explicit joins and caps. The redundant highlight stroke is removed. Focus follows the inset chamfered shape.

## Save migration

The Research payload and generated catalog are now revision 2; the feature remains Research V1. Existing revision-1 saves are validated against their original prerequisite rules before migration. This matters because the old rules allowed a paid second-row node without its first-row lane node.

Valid old ownership, total earned RP, spent RP, and available RP are retained. Changed specialization IDs immediately apply their new domain effect after load. A small persisted `legacy_lane_node_ids` set records paid second-row nodes whose prerequisites changed; it does not grant free ancestors. New purchases obey the strict catalog prerequisites. Full Respec clears both the allocation and those legacy exceptions, refunds all spent RP, and retains the 24-hour cooldown behavior.

Tests exercise the old Forestry Major-plus-specialization allocation through three SQLite save/load cycles, check the new timber and lumber values, and verify identical earned/spent/available totals. A complete 735-node old allocation also retains every ID. Normal revision-2 saves do not automatically receive legacy exceptions. Unknown or genuinely invalid old allocations retain the existing refund behavior.

## Validation

- `QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m pytest tests/test_research.py tests/test_research_ui.py -q --tb=short` — **30 passed in 10.36 seconds**.
- This focused set covers topology, pure-domain content, RP earning/spending, additive and exact-product modifiers, Market and Contract snapshots/payouts, production and power effects, storage, refund/cooldown/clock behavior, SQLite persistence and migration, Activity integration, navigation, scrolling, and UI layout.
- UI text-fit checks cover every node in every tree at 1600×900 and 1366×768, along with every sidebar label and selected-tree header. Research palette checks reject green/olive colors in the audited component source.
- `.venv/Scripts/python.exe -m compileall -q src tests scripts` — passed.
- `git -c core.safecrlf=false diff --check` — passed. The preexisting dirty workspace was preserved.
- **The complete full suite was not run.**
- **No live GUI was launched.** All Qt validation and capture runs explicitly used the offscreen platform, temporary saves, or an in-memory QA game.

## Five offscreen captures

All five were visually inspected. Forestry matches the requested centered split, three vertical lanes, and clean convergence to the next Major. Chassis corners, high-contrast text, sidebar selection, neutral Research surfaces, and compact clipping were reviewed. The global Command Deck retains its existing colors outside this pass.

1. [General / Company — 1600×900](../artifacts/ui/research-polish-v1/01-general-1600x900.png)
2. [Forestry — complete three-lane section](../artifacts/ui/research-polish-v1/02-forestry-three-lanes.png)
3. [Forestry — researched, available, and locked states](../artifacts/ui/research-polish-v1/03-forestry-mixed-states.png)
4. [Header — RP and Full Respec](../artifacts/ui/research-polish-v1/04-rp-and-respec.png)
5. [Compact Research — 1366×768](../artifacts/ui/research-polish-v1/05-compact-1366x768.png)

The compact viewport is 1036 px wide, with zero horizontal scroll. Capture metadata is in `artifacts/ui/research-polish-v1/qa.json`; transformation counts are in `content-audit.json` beside it. Captures can be regenerated with `QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m production_zero.tools.research_polish_qa`.
