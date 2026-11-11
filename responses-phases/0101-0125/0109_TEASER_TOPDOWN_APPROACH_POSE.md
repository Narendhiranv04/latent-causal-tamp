# 0109: Teaser (a)/(b) top-down approach pose

Previous turn sync: `5c2be88de` (v1 revert + folded approach pose) was pushed to `origin/approach-d-v1`.

## Why the pose changed
The (a)/(b) robot reached along the target's row and halted short of b3. To do that, its wrist had to sit within ~9 cm of the base. With links of 0.42 m and 0.34 m, that forces joints 1–2 into an almost flat fold, which looked clumsy. The only open pose that keeps the elbow off the board and inside the crop comes down from directly above. In the old scene nothing blocked that direction, so the user chose to add a disc that closes it.

## Changes
- **Scene:**
  - context disc **c6 at (6,3)** added. It is never moved and closes the overhead approach, both initially and after repair (`overhead_full_reach_hits_* = [c6]`).
  - b1 now parks at **(5,5)** (was (7,3)); b3 at **(3,0)** (was (6,4)).
  - The new parking keeps every arrow and slot clear of the hovering arm. The four arrows now point in four distinct directions (right, down-left ×2, down).
- **(a)/(b) robot:**
  - heading −90°, elbow up, `back_m = 0.2225`
  - open Γ shape, elbow (−0.049, 0.73)
  - the gripper halts 2.05 cm above c6, and a clay contact arc on c6 faces the gripper
  - no overlap; min link x = base x
- **Crop:** `right_column_abc` now uses `viewBox 400 0 900 880`, which fits the higher wrist.

## Checks (schematic)
All pass:
- every declared mode is blocked initially and clear after repair
- the home, grasp and place poses and the transfer sweep are clear
- a free pick heading and a free place heading exist for each of the four relocations

CONCEPTUAL ILLUSTRATION; not a verified dataset witness.
