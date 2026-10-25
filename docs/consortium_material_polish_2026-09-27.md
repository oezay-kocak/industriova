# Consortium final material and layout polish

## Implementation summary

The accepted Consortium structure is preserved. Members now has a flexible roster above a fixed bottom management module. Overview columns fill the workspace, and Daily/Weekly sections share the available height. A Consortium-local silver frame remains bright around the graphite recess, with concrete visible outside its rounded corners. Medium painted-metal housings distinguish stat/product objects from their dark parents.

Navigation, member typography and interactions, contract product buttons, permissions, confirmations, progression mechanics, notifications, and other screens were not redesigned.

## Files changed in this pass

- `src/production_zero/ui/consortium_materials.py` — shared Consortium workspace frame and painted-metal stat material, using existing PZ tokens.
- `src/production_zero/ui/consortium_view.py` — flexible layout policies, full-height Overview, distributed contract section height and transparent workspace setup.
- `src/production_zero/ui/theme.py` — scoped background transparency and Consortium material separation.
- `tests/test_consortium_material.py` — geometry, capacity, bottom anchoring, corner pixels and rim brightness checks at all three sizes.
- `tests/test_consortium_final_ux.py` — update the superseded compact-roster expectation and add the two-member case; behavioral assertions remain.
- `scripts/capture_consortium_material.py` — visual fixtures, reference screens, contact sheets, manifest and measured geometry.

These are this pass's edits; the workspace also contains earlier work.

## Members layout

The Members header remains 36 pixels high. Management Settings remains the accepted compact 148-pixel module at the bottom. The roster housing receives the flexible middle space; rows remain 48 pixels high and packed from the top. The roster's scroll area and housing ignore content-driven preferred heights, while retaining a usable minimum, so member count cannot enlarge the page or move the footer.

Only the roster scrolls as rows exceed its viewport. Pending applications remain actionable inside that same scrollable middle region, so they also cannot displace the bottom settings. Non-chairman members retain their existing Leave action at the bottom.

Measured geometry from `artifacts/consortium_material/geometry.json`:

| Window | Settings top within Members page | Settings height | Roster viewport area height | Member counts checked |
| --- | ---: | ---: | ---: | --- |
| 1366×768 | 210 | 148 | 98 | 1, 2, 10, 25, 50 |
| 1600×980 | 422 | 148 | 310 | 1, 2, 10, 25, 50 |
| 1920×1080 | 522 | 148 | 410 | 1, 2, 10, 25, 50 |

At every size, all five counts have identical footer and roster geometry and zero outer Members-page scrolling. The final row remains reachable through the roster's own scrollbar.

## Material hierarchy

The light concrete parent remains exposed around the bright silver workspace rim. Inside it, the graphite workspace and dark major sections contain visibly lighter functional housings:

- Overview stat objects use existing `interactive_hover` and `panel_elevated` tones, edge highlights and a restrained lower shadow.
- Contract requirement housings use the existing medium industrial grey; the accepted dark `ContractProductButton` objects remain unchanged.
- Metadata and eligibility rows use the existing lighter graphite level with visible borders.
- Management Settings uses the existing medium painted-metal tone, distinguishing it from the roster recess.

No palette or global painter was changed. The existing yellow/cyan/green semantics are retained.

## Overview and Contracts height

Overview's fixed 330-pixel card caps were removed. Both columns now extend to the bottom of the usable workspace and align exactly. Their existing internal stretch keeps compact stats and activity entries near the top, with deliberate breathing room inside the full-height columns.

Daily and Weekly sections receive equal stretch in their existing vertical order. Fixed-height section headers and compact product/metadata size policies prevent text or product buttons from stretching awkwardly. Additional room becomes section spacing. Both selected sections fill the workspace without outer scrolling at 1600×980 and 1920×1080. Compact/detail-heavy states retain internal scrolling. Product modules remain exactly 78 pixels high.

## Silver frame and black backing

The old workspace used `MaterialLevel.INSET` for its outer rim. That palette explicitly transitions from chassis grey through chassis shadow to `recessed_dark`, explaining the near-black right/bottom edge. `ConsortiumWorkspaceFrame` now uses existing chassis-light/chassis-mid tones for the rim, preserves a highlight/shadow edge and draws the established inset surface inside it. All four pages share this one implementation.

The rectangular backing was inherited background painting beneath the custom rounded frame: the generic QWidget background reached the tab stack/scroll viewport, and `QScrollArea.setWidget()` enabled host autofill. Painting a rounded frame alone did not clear those corners. The fix explicitly makes the Consortium tab stack, workspace viewport and frame backgrounds transparent, then disables viewport and host autofill after attaching the host. The real concrete parent now shows through; no corner-covering decoration was added.

Pixel checks on composited window captures verify light concrete at the rounded outer corners on Overview, Contracts, Members and Progression, and a bright silver rim on both sides.

## Visual review and iteration

The implementation was rendered, inspected, corrected and rendered again. Resources, Factory and Inventory references are included in every contact sheet.

1. The first flexible roster still grew with larger member counts. Geometry showed Settings moving from y=210 to y=496 at 1366×768. Qt's content-derived size hints were overriding the intended allocation. Ignoring those preferred heights in the middle area fixed the movement; subsequent captures and assertions verify exact stability.
2. The original nested stat material was too close to its parent. A medium painted-metal fill and brighter edge make each stat readable as an object at reduced size.
3. Rounded stat objects also needed explicit transparent stylesheet backgrounds to avoid their own rectangular inherited fill.
4. Contract headers needed a fixed height when their containing sections expanded; product/metadata areas retain compact size policies while extra space is distributed around them.
5. The existing inset rim and inherited corner backing were corrected separately: changing the rim palette alone would not have removed the black rectangles.

Full-size review covers sparse/populated Overview; 1-, 2-, 10-, 25- and 50-member rosters; last-row access; Daily-selected/Weekly-empty, both-selected and active contracts; and default/progressed Progression. Reduced-size contact-sheet review confirms distinct page, frame, section, functional housing and product/stat layers without relying on text.

## Capture manifest

`artifacts/consortium_material/manifest.json` lists **51 final captures** at 1366×768, 1600×980 and 1920×1080. Each size includes three unchanged reference screens and all focused review states. The three `contact_<resolution>.png` sheets support reduced-size comparison. `geometry.json` records the bottom-anchor measurements. All fixtures are in memory and leave real saves untouched.

## Validation

Focused material/layout, Consortium UX and behavior run: **32 passed**. This covers all requested capacities, last-row accessibility, fixed footer position, full-height panels, section non-overlap, unchanged product height, exact window sizes, corner pixels, silver-rim luminance, permissions, profile links and confirmations.

The final module-isolated suite uses the established QA-font setup: **978 passed across 69 modules**, with zero failures, errors or skips. Logs, XML and `summary.json` are under `artifacts/consortium_material/tests/`. `compileall -q src tests scripts` passed again after the final edits.

## Remaining human design decisions

None required. The intentional empty roster area and full-height Overview breathing room follow this review request. At 1366×768, the preserved header and compact bottom module leave roughly two visible roster rows; all remaining rows scroll internally while settings stay visible.
