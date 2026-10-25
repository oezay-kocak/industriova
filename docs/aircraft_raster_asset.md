# Aircraft raster asset

The final Aircraft artwork is stored at
`src/production_zero/assets/freight/aircraft.png`. It is copied byte for byte
from the supplied final image (1721 × 914 px, transparent ARGB PNG, SHA-256
`45a9622e78a5f508120914038afd7868c89c9ea218128ab688369bcf61213f09`).
The obsolete `src/production_zero/assets/freight/aircraft.svg` was removed.

`freight_art.py` sends Aircraft through the same raster pipeline as Truck and
Train. Rendering preserves aspect ratio, reserves transparent inset space,
and uses Qt `SmoothTransformation` plus `SmoothPixmapTransform`. Ship remains
an SVG asset.

The existing Aircraft color identity was already consistent across Selection,
installed, and Supply Shop cards, so it remains unchanged at `#9bb8ef`.
No neutral UI surfaces or other Freight-family colors were modified.

Offscreen QA output is stored in
`artifacts/aircraft_raster_violet_identity/`, including Selection and Shop
comparisons, the four-card overview, the available Shop state, and the
machine-readable `verification.json` report.
