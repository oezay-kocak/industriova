# Train raster asset and red identity

The final Train artwork is stored at
`src/production_zero/assets/freight/train.png`. The file is copied byte for
byte from the supplied golden sample (1721 × 914 px, transparent ARGB PNG,
SHA-256 `d1d218fe910710424f7681a7ba5a783f749b78d500b47a6e3236cbd64bd4c3f2`).
The obsolete `src/production_zero/assets/freight/train.svg` was removed.

`freight_art.py` now routes Truck and Train through the same raster path. It
fits images with `KeepAspectRatio`, adds transparent inset space, and uses
`SmoothTransformation` plus `SmoothPixmapTransform`. Ship and Aircraft remain
SVG assets.

The canonical Train accent is `GAME_UI_TOKENS.colors.train`, derived from the
primary Production Zero red `GAME_UI_TOKENS.colors.area_anchor_red`: `#c83a2b`.
The installed Freight card, inventory Selection Card, Supply Shop card, and
Train BUY button use this definition. Neutral surfaces and the other Freight
families retain their existing colors.

Offscreen QA output is in `artifacts/train_raster_red_identity/`:

- `comparison_train_selection_166x224.png`
- `comparison_train_shop_208x276.png`
- `comparison_freight_overview.png`
- `after_train_shop_available_208x276.png`
- `verification.json`

The verification checks the source hash, alpha channel, aspect-preserving
card-box fit, transparent padding, shared PZ red, real card dimensions, and
pixel equality of Truck, Ship, and Aircraft before and after the Train pass.
