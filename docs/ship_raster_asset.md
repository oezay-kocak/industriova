# Ship raster asset

The final Ship artwork is stored at
`src/production_zero/assets/freight/ship.png`. It is copied byte for byte from
the supplied final image (1721 × 914 px, transparent ARGB PNG, SHA-256
`21e5b3d9522a92d1a5e6d99d7b6806ad0575919d86db65cf06b8b3145e734159`).
The obsolete `src/production_zero/assets/freight/ship.svg` was removed.

All four Freight families now use the shared raster path in `freight_art.py`.
It preserves aspect ratio, reserves transparent inset space, and uses Qt
`SmoothTransformation` plus `SmoothPixmapTransform` for card-size output.

The existing Ship color identity was already consistent across Selection,
installed, and Supply Shop cards, so it remains unchanged at the established
PZ Cyan `#25b9e8`. No neutral UI surfaces or other Freight-family colors were
modified.

Offscreen QA output is stored in `artifacts/ship_raster_cyan_identity/`. It
contains individual Selection, Shop, and installed-card comparisons, the
four-card Freight overview, and the machine-readable `verification.json`.
