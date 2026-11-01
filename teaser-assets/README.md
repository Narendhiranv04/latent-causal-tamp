# K4 teaser illustration assets (conceptual, text-free)

`python teaser-assets/build.py` regenerates everything here. Geometry (lattice pitch, disc radius, robot base, link lengths and widths, gripper, home q) is read from `config.toml`. This is a **conceptual** K4 example. It is not a verified dataset witness.

- `svg/A_blocked_and_displacement_plan.svg`: **diagram A**. The target and goal are blocked: soft dashed approach rays and contact arcs, four highlighted blockers, relocation arrows to faint destination slots, and the transit loop that starts and ends at home.
- `svg/B_target_placement_execution.svg`: **diagram B**. The repaired scene with the full robot executing the placement: three fine-line stroboscopic poses carrying the target, the transfer arrow, the final pose solid, and the target placed in the goal ring.
- `svg/0N_*.svg`: panels 01–06 (and 04b with the transit chain). They are transparent and share `viewBox="0 0 1360 920"`.
- `svg/07_preview_blocked_repaired.svg`: blocked | repaired side by side. The right half is the same frame shifted by +1480 px.
- `svg/layers/*.svg`: every element group as its own transparent file, all in the same viewBox, ready for stacking in HTML.
- `png/`: 2× transparent exports of the above.
- `previews/*_on_paper.*`: inspection renders on `#F7F5F0`. These are not assets.
- `manifest.json`: viewBox, world→px map, palette, every cell (world m and svg px), relocation order, robot poses, and the schematic overlap checks.

The robot's drawn home pose is the `config.toml` home with joint 1 rotated by +90°, so the folded arm lies horizontally and faces right. This is an illustrative choice, recorded in the manifest.

Element ids (`b1`…`b4`, `dest-b*`, `move-b*`, `contact-b*`, `target`, `goal`, `robot-*`) are stable, so CSS and JS can address them during composition.
