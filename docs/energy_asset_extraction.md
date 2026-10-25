# Energy asset extraction

The supplied five-card reference image was used only as a pixel source. Five
independent transparent PNGs were extracted into
`src/production_zero/assets/energy/`:

- `coal_power_plant.png`
- `gas_power_plant.png`
- `nuclear_power_plant.png`
- `solar_array.png`
- `wind_turbine.png`

Card frames, labels, card-color fields, sky, and unrelated terrain were
removed with deterministic masks. The source artwork itself was not generated,
redrawn, recolored, or geometrically transformed. Coal and Nuclear steam was
omitted because it could not be separated from the background without carrying
the surrounding card field into the alpha edge.

The assets are intentionally not connected to the card renderer yet. The
dark/light alpha-edge contact sheet and machine-readable bounds report are in
`artifacts/energy_asset_extraction/`.
