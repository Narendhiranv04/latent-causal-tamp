# 0108: Teaser assets reverted to v1, with an approach pose in (a)/(b)

Previous turn sync: `680406d02` (three-question sequence) was pushed to `origin/approach-d-v1`. Its content is superseded here, but reports 0106/0107 stay as written.

## Changes
- **Reverted:** `teaser-assets/` is back to its `557d03ac9` state. The A/B diagrams, the Q1–Q3 panels, the rotated home and the board frame are removed. `archive/v1_right_column/` is kept.
- **Single new change:** in (a) `02_blocked_access` and (b) `04_relocation_arrows`, the upright home robot is replaced by `robot-approach`:
  - pose: elbow-up IK toward the target, heading −5°, `q = [1.341, −3.063, 1.634]`
  - the open gripper halts 2.4 cm short of b3 (the disc west of the target), and nothing sits inside its mouth
  - schematic overlap check: clear; min link x = base x (nothing left of the base)
- **(c) `06_feasible_transfer`:** uses the full faint place pose again, matching the contact-sheet image.
- **New composite:** `svg/right_column_abc.svg`, which stacks (a)/(b)/(c) cropped to `viewBox 400 60 900 820` (base plate → board edge).
- **Not restored from the old sheet:** (a) keeps the open-U approach marks and the corrected contact arcs. The sheet's dashed-rectangle marks put one arc on the wrong side of the lower-left blocker.

CONCEPTUAL ILLUSTRATION; not a verified dataset witness.
