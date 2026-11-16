# Superseding errata: historical D0–D8 final report

The original report and numeric JSON are intentionally unchanged. Cite this
erratum alongside them. Source precedence is executable code + frozen artifacts.

| Historical statement | Correction |
|---|---|
| A6000 / 3090 | gvlab has two RTX4090 24 GiB GPUs. Driver CUDA max12.6, Torch compiled CUDA12.4. |
| 2024, “Direct Policy and Value Distillation…” | Pinned upstream README BibTeX: **Distilled Tree Search over Continuous Actions**, Saha et al., CoRL2026. Paper arXiv metadata not independently retrieved in this session. |
| PUCT with alpha .5 | UCB `Q + 1.5 sqrt(log(Nparent+1)/(Nchild+1))`; k2, alpha.3. No policy prior multiplier in selection. Widening triggers a candidate batch, not a hard floored width cap. |
| q_t and gripper in historical neural state | Physically carried, omitted from O0 feature tensors. O1 is a new separately versioned closed-loop observation ablation. |
| State-only V predicts global success | Q(h,a) estimates sampled decided descendant-leaf success fraction. Exploration-biased continuation target; not a global feasibility certificate. |
| 2D base(0,0), pitch.10, four cardinal grasps | Base(-.14,.32)m, pitch.08m, planar 3R links(.42,.34,.20)m, 24 azimuths×2 elbows=48 side grasps. |
| 3D Franka mesh / generic tabletop | xArm7,6×6 confined shelf,pitch.075m,32 side grasps in pinned audited teacher. |
| 24/24 parity each domain /48 roots | Saved evidence: 32 queries/16roots 2D +16queries/8roots 3D;48queries/24roots total. New independent replay is reported separately. |
| 25 iterations and B16 used | Defaults only. Executed source driver: 2D8iter/B4/cap14;3D5iter/B3/cap8. Unguarded final STOP allowed caps to overshoot (actual per-tree counts in inventory). |
| 135/54 independent task samples | 45/18 distinct task roots, three network seeds per root;75/30 overall roots. Bootstrap root means, not prediction trials. |
| Significant 11.11pt all-feasible benefit | Wrong contrast: P2 primary vs seed 0 successful-only. Round1 reported means24.07−16.67=7.40pts with unequal seed coverage. New archive analysis compares round 1 seed 0 to seed 0; new three-seed controls use the same trees and fixed schedule. No recycled significance claim. |
| 3D value proves superiority20.37→27.78 | Descriptive +7.41pt trend; root-level CI spans zero. 2D10.37→8.15 is a negative trend. |
| Closed-loop equality establishes feedback effects | Historical O0 reads cells/masks, omits achieved q; matched equal outputs do not assess O1 proprioception. Failed retry candidates do not prove all alternatives impossible. |
| Zero simulation at inference | Zero **selection** physical calls. Independent final verification still uses physics/planning; separate these costs. |
| Beam search | Implementation is sequential sampled candidates + learned per-action ranking, no beam. |
| Feasible edges = positive terminal labels | Feasible edges supervise policy; decided descendant outcomes supervise Q. Successful-only restricts policy rows, not the value dataset. |
| Repeated successful STOP visits = independent evidence | Cached physical STOP outcome is one observation; new extraction uses weight log2 per decided STOP. |
| Method gaps establish F2/F3/F5 causal advantage | Old Approach B43.6%/77.3% used412/241 task roots; DISCO 8.15% / 27.78% used45/18. These are unpaired preliminary aggregates. No factor-specific causal attribution. |
| Prose checkpoint filenames/checksums are authoritative | Actual deployed paths and full measured hashes are in artifact_inventory.json/archive_replay.json. Prose registry was not validated by those prefixes. |

NONE means legacy restricted-search status. Report explicit ABSTAIN separately
from NOOP, novel verified repairs, and certified impossibility (not inferred).
Timeout/unknown remains censored. Checkpoints selected by a fixed training
schedule are not validated task improvements. Historical TEST is exposed and
cannot become an untouched confirmatory cohort by renaming it.
