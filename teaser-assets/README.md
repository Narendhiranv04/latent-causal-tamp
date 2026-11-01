# K4 teaser illustration assets (conceptual, text-free)

`python teaser-assets/build.py` regenerates everything here. Geometry (lattice pitch, disc radius, robot base, link lengths and widths, gripper, home q) is read from `config.toml`. This is a **conceptual** K4 example. It is not a verified dataset witness.

- `svg/0N_*.svg`: panels 01–06 (and 04b with the transit chain). They are transparent and share `viewBox="0 0 1360 920"`.
- `svg/07_preview_blocked_repaired.svg`: blocked | repaired side by side. The right half is the same frame shifted by +1480 px.
- `svg/layers/*.svg`: every element group as its own transparent file, all in the same viewBox, ready for stacking in HTML.
- `png/`: 2× transparent exports of the above.
- `previews/*_on_paper.*`: inspection renders on `#F7F5F0`. These are not assets.
- `manifest.json`: viewBox, world→px map, palette, every cell (world m and svg px), relocation order, robot poses, and the schematic overlap checks.

Element ids (`b1`…`b4`, `dest-b*`, `move-b*`, `contact-b*`, `target`, `goal`, `robot-*`) are stable, so CSS and JS can address them during composition.
