# Stable Research horizontal geometry

Company previously used a 690 px minimum canvas with no side spacer; Industry used 918 px and a 176 px side spacer plus a 20 px gap on every row. The centered main-lane region therefore changed when selecting a different family.

All 21 trees now use the existing Industry geometry: 918 px minimum canvas, 26 px left/right margins, and a permanent 176 px specialization column separated by the existing 20 px gap. The main axis is canvas_width / 2 - 98 px in canvas coordinates, irrespective of tree family. The actual slot remains at canvas_width - 26 - 176 - 42 px. Company reserves space with plain layout widgets and creates no specialization controls.

The existing node size constraints, vertical row heights, Industry slot heights and tree heights remain unchanged. Company height is 2624 px; Industry height is 2448 px. No mechanics, topology, costs, content, icons or specialization behavior changed.

| Window | Major axis X | Left lane X | Center lane X | Right lane X | Horizontal scroll maximum |
|---|---:|---:|---:|---:|---:|
| 1600×900 | 826 | 499.5 | 826 | 1152.5 | 0 |
| 1366×768 | 709 | 455 | 709 | 963 | 0 |

Coordinates are relative to the main window. All 21 trees match exactly, including switching back to Company. Tests inspect every node, the first cluster's split/merge bus X coordinates, reserved column widths, slot bounds/inset, vertical scrolling, and no horizontal scrollbar at both sizes.

Validation: 11 focused tests passed across test_research_layout_stability.py, test_research_interaction_polish.py and test_research_specialization_ui.py. After strengthening the all-node assertion, both layout cases passed again. compileall and git diff --check passed. The full suite was NOT run. All automated GUI work was OFFSCREEN; no live GUI was launched and no player save was used.

Three screenshots, all 1600×900 at vertical scroll position 420, were captured and visually inspected:

- artifacts/ui/research-layout-stability/01-general.png
- artifacts/ui/research-layout-stability/02-agriculture.png
- artifacts/ui/research-layout-stability/03-electronics.png

Geometry records for every tree are in the same directory as geometry-1600x900.json and geometry-1366x768.json. Industry retains its pre-existing vertical spacing; the comparison is horizontal, not a change to vertical topology.

Files changed in this pass: src/production_zero/ui/research_view.py, tests/test_research_layout_stability.py, this report. Unrelated existing workspace changes were preserved.
