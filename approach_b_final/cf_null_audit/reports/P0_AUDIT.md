# P0: source, baseline and resource audit (laptop only)

Branch `naren/cf-null-audit` (from `e9fa587c3b`). This is a sparse worktree; the laptop's `/home` has 1.7 GB free.

## Laptop resources

| | |
|---|---|
| CPU | 32 logical. Our affinity is 0–31, with no cgroup quota. **CF jobs are pinned to CPUs 0–28 (29 cores)**, leaving 29–31 free. |
| RAM | 30 GiB, about 11 GiB available (the VS Code / IDE processes hold the rest). |
| GPU | NVIDIA GeForce RTX 5060 Laptop, 7.5 GiB, used through system/miniconda Python (torch 2.9.1+cu128). One model at a time. |
| Disk | `/home` has 1.7 GB free. Scratch (`/tmp`, tmpfs) has 3 GB. Large intermediates stay in scratch and are not committed. |
| Physical teachers | 2D: `~/abf_v3_laptop/root/teacher2d_wt` + `env2d`. 3D: `~/abf_v3_laptop/gen/final3d_v4/code/fin3d.py` + `env3d` (MuJoCo). Both still need hash checks against the locks. |

## Reference paper (arXiv:2611.09130, read via HTML v1)

**CF pair:**
- The grasp pose is fixed. A solid box goes into the approach corridor, the planner relabels it (RRT-Connect, PyBullet), and the box is added to the model input.
- **The paper never says** whether "infeasible" is certified or a budget outcome. Its sampling planner "cannot certify infeasibility", so its negatives are budget-limited.

**CF-pair metric:**
- Text: "ranks clear versus blocked versions of the same grasp at an identical pose". It reads as a pooled AUROC over pairs, but no formula or tie rule is given.
- We report **both** a pooled AUROC and the within-pair statistic.

**"Null":**
- Text: "false-flip rate of a matched off-corridor box that should stay feasible (ideal 0)".
- It is an **oracle** quality metric (values 0.00–0.03), not a model metric.
- Our table column will be `NULL model retention (%)`, with the oracle false-flip rate reported separately (plan §1).

**Models in the paper:** SceneCollisionNet and PIGINet are reimplemented and trained on the paper's own planner labels. GRN uses released weights on its own data. Their audit task is grasp-level, not our task-level target Y.

## Frozen learned target-feasibility predictors available on this laptop

| Model | Code | Weights | Native task vs our target-Y task | Status |
|---|---|---|---|---|
| **Our Approach** (D Y branch, `sigmoid(b)` at the empty edit) | `approach_b_final/xy.py` | `~/abf_v34/approach_b_bundle/{2d,3d}/scorer_s{0,1,2}.pt`. The s0 hashes match `final_protocol.yaml` (3D `c02afcbc…`, 2D `0fa126da…`). | Exact (endpoint Y from q_ref) | AVAILABLE (2D + 3D) |
| **GRN** (teammates' adaptation, `yadu/GRN` 986cce3a, read-only) | `baseline_grn/` (EdgeGATv2Conv, MIT) | `runs/s{0,1,2}/best.pt` in git (sha256 `fa4286e4…`, `08393528…`, `aa6689b3…`) | Adapted: "can T go to its goal in this layout", with the goal as a marker node. Trained on the 3D dataset's own `labels.original` / `labels.D`, V4 split. | AVAILABLE (3D only). Reproduction running. |
| **PIGINet** (teammates' implementation, `yadu/PIGINet` 1045e070) | `piginet_shelf/` | **Found later (amendment 2):** read-only on `blackwell:~/yadu_bd/piginet_shelf/runs/{noimg,full}_s{0,1,2}/best.pt`, copied to the laptop. Nothing was run on blackwell. | "move T" plan query = target feasibility in a state (same semantics). | **AVAILABLE, no-image variant** (TEST move-T AUROC .9875/.9866/.9879 reproduced through the CF adapter). The image variant is excluded because CF states have no renders. |
| **SceneCollisionNet (SCNet)** (teammates' reimplementation) | `scn_shelf/` | **Found later (amendment 2):** read-only on `blackwell:~/yadu_bd/scn_shelf/runs/adam_s{0,1,2}/best.pt`, copied to the laptop | State feasibility = max over the 32 target grasps of P(grasp works) | **AVAILABLE** (TEST move-T AUROC .9718/.9693/.9651 reproduced; grasp-input rebuild parity 240/240) |

**Source of the paper's existing 3D target-feasibility table (TN/FN/TP/FP for PIGINet, GRN, SCNet, Ours):** not found in any local file. The teammates' READMEs report AUROC only, with no SCNet row.

## 2D baselines

No 2D-trained PIGINet, GRN or SCNet checkpoints exist; the 3D checkpoints cannot take the 8×8 planar task. **The 2D result will be an Ours-only diagnostic** (plan §2).

## K>3 2D release

Not final. The scaling campaign is at G1/G2 in this same conversation, so the CF audit runs on the original TEST cohorts only and leaves the combined-cohort analysis gated (plan §1).

## Update (amendment 2, 2026-11-21)

PIGINet and SCNet were later located on blackwell, read-only. Their status changed from BLOCKED to AVAILABLE before any final model score was computed; see `PROTOCOL_LOCK.json`, amendment 2.
