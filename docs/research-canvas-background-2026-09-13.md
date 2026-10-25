# Research canvas background — 2026-09-13

## Root cause and scope

`ResearchTreeCanvas.paintEvent` still filled the entire workspace with solid
`#14171a`. Earlier visual passes changed surrounding controls and node surfaces,
which did not affect this fill behind the tree.

This pass changes only that background fill and its QLinearGradient import in
`src/production_zero/ui/research_view.py`. No other production file changed in
this pass. Added one focused QA test and this report. Existing unrelated work in
the dirty workspace was preserved.

## Existing material audit

- Freight constructs a `FactoryV2Board` and `FactoryV2TrackPanel` for the Garage
  workspace. The board uses `draw_game_surface`; the track uses the shared
  production-track material.
- Factory uses those same board/track surfaces. `draw_game_surface` layers a
  broad diagonal gradient, `draw_industrial_base_surface`, horizontal falloff,
  and industrial edges. `draw_production_track` adds a dark diagonal floor.
- Resources and Energy inherit `ProductionBoardViewV2`, sharing this material
  infrastructure through their board configurations.
- Research adapts the broad light-left/dark-right material transition rather
  than calling the shared helper directly: the helper also paints tinted
  layers, wear, seams and bolts outside this background-only brief.

## Implementation

One opaque QLinearGradient fills the canvas before the existing connectors:

| Stop | Color |
| --- | --- |
| 0 | `#454749` |
| 0.45 | `#292b2d` |
| 1 | `#0c0d0e` |

Direction: `(0, 0)` to `(canvas width, canvas height * 0.08)`, predominantly
left-to-right with a shallow downward component. This keeps strong horizontal
variation visible despite the very tall tree. Coordinates belong to the whole
canvas, independent of viewport scroll or dirty paint regions. No texture,
asset loading, animation, timer, blur, per-node effect or extra repaint request.

## Visual QA

All four screenshots below were opened and visually inspected at gameplay scale.
The exposed Research margins and spaces between nodes now clearly transition
from lighter graphite at left to near-black at right. Freight Garage shows the
same broad light-to-dark industrial depth, with its existing warmer/tinted
material and framing; Research remains neutral. Nodes remain dominant and
cyan/yellow/orange outlines, gray connectors and light labels remain readable.
No seams are visible in the scrolled view. Compact layout retains its fit.

Four dedicated captures in `artifacts/ui/research-canvas-background/`:

1. `01-research-1600x900.png` — Agriculture & Food, scroll 0.
2. `02-research-scrolled-1600x900.png` — same tree/state, scroll 420.
3. `03-research-1366x768.png` — same tree/state, scroll 420.
4. `04-freight-garage-reference.png` — Freight Garage, 1600x900.

## Validation

- `.venv/Scripts/python.exe -m pytest -q tests/test_research_canvas_background.py tests/test_research_ui.py tests/test_research_layout_stability.py`
  — **12 passed in 11.02 seconds**.
- Background test checks actual rendered opaque pixels, at least 30 red-channel
  levels of left/right contrast at four canvas heights, neutral channel spread
  of at most four, and exact canvas/viewport pixel equality after scrolling.
- Geometry stays identical across scroll positions. Existing layout tests cover
  all 21 trees at both resolutions, canonical node lanes and connector buses,
  reserved specialization width and absence of horizontal scrolling.
- `.venv/Scripts/python.exe -m compileall -q src tests` — passed.
- `git diff --check` — passed; existing Git line-ending notices only.
- Full suite **not run**. **No live GUI**: all Qt windows used the offscreen
  platform, in-memory QA state and no save store.
