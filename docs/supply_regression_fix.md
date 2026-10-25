# Supply UI regression fix

Train cards retain their red Freight identity, while every Supply BUY button
again uses the shared Production Zero yellow action style. The Train-specific
normal, hover, pressed, and disabled button overrides were removed from
`theme.py`; no Train card or asset colors changed.

Daily Freight and Daily Machines now use fixed, centered four-card rows inside
their existing section bands. The outer Daily Supply area and both inner card
bands disable horizontal and vertical scrollbars, keep zero scroll range, and
consume wheel events. At reduced heights, cards scale with their existing
aspect ratio so the complete selection remains visible. Common Supply retains
its independent scroll area and virtualized grid.

Offscreen QA files are stored under `artifacts/supply_regression_fix/`.
`verification.json` confirms identical button crops for all four Freight
families, retained red Train card accents, zero Common Supply pixel changes,
and disabled Daily scrolling.
