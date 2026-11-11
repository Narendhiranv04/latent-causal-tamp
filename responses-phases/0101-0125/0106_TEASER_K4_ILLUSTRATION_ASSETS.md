# 0106: Teaser K4 illustration assets (conceptual, text-free)

Previous turn sync: `557d03ac9` (first asset pack, panels 01–07 + 04b) was pushed to `origin/approach-d-v1`.

## What changed
- **Robot home (figure only):** the folded `config.toml` home is rotated +90° about the base, `q = [π, π/2, π/2]`, so the arm lies horizontally with the gripper facing right. The base mount is now a neutral square plate. The manifest records both poses. This is a drawing choice and does not change `config.toml`.
- **Diagram A**, [blocked + displacement plan](../teaser-assets/previews/A_blocked_and_displacement_plan_on_paper.png): soft blocked-approach rays and contact arcs, the four highlighted blockers, relocation arrows to faint destination slots, and the transit loop (home → four relocations in order → home, with no homing in between).
- **Diagram B**, [placement execution](../teaser-assets/previews/B_target_placement_execution_on_paper.png): the repaired scene (parked blockers muted), three fine-line stroboscopic poses carrying the target (joint-linear interpolation of the elbow-up grasp→place IK), the transfer arrow, the final full robot solid, and the target placed in the goal ring.
- Panels 01–07 were regenerated with the rotated home pose. 07 is otherwise unchanged.

## Checks (schematic, not planner-certified)
Capsule-vs-disc overlap: home, grasp, place and the full transfer sweep are clear. Each declared blocked mode overlaps exactly its blocker before repair and nothing after. A free pick heading and a free place heading exist for every relocation. Automated scan: no `<text>/<title>/<desc>`/font in any SVG. All PNGs are transparent RGBA.

## Status
CONCEPTUAL ILLUSTRATION. This is not a physically verified K4 witness from the dataset.
