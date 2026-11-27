# FIG3_KGT3 P0 — parity, provenance, completion and leakage audit

**Pre-registration:** `../FIG3_KGT3_PREREG.json`. **Start:** HEAD `7c948deef0`; no job was running on gvlab2. Historical decisions are unchanged: the R3 gate failed, the A2 rule was not passed, and the void manifests stay void.

**Verdict:** no leakage or privileged input was found. Five implementation issues were fixed in the scaling path only; the production path is untouched.

## 1. Inference provenance (runtime, both domains, all five arms)

`audit0.py` ran REC-ORDERED, REC-REORDER, FLAT-INSERT, GA and GA-YONLY on 2 roots per domain (`p0/p0_audit_{2d,3d}.json`). A meta-path guard blocked every teacher, simulator and planner module before any import:
- `fin3d`, `bd_3dt*`, `bwlphys`
- `bxy_teacher`, `teacher2d`, `teacher_long`
- `physical2d` / `physical3d`, `evaluate_k45`
- `bd_2d`, `motion`, `geometry`, `skill`
- `p15*`, `p16*`
- `mujoco`, `pybullet`
- the generator, witness, MINK and certificate modules

**No import was attempted.**

| Check | Result |
|---|---|
| Row fields read (field-tracking dict) | `root_id`, `domain`, `inputs` only |
| `inputs` fields read | `ids`, `xy0`, `cells0`, `attrs`, `tid`, `goal`, `goal_cell`, `base`, `ctx`, `legal_cells`, `q_ref`, `cell_xy` (all allow-listed: public scene and task) |
| Metadata invariance (row stripped to the three fields) | identical plans, 10/10 root-arms |
| Relabelling non-target slots | identical cVAE proposals; max \|ΔpX\| 4e-8, max \|Δp11\| 6e-9 |
| Legal support mask | full grid in **every** row: 2D 64/64 (4,251 rows), 3D 36/36 (2,130 rows), cohort 64/64. No reachability or grasp mask. |
| 2D fixed-body flag | `attrs[3]` (a public scene property) |
| Witness order vs object ID order | mean Kendall τ −0.16 (2D cohort), −0.13 (3D DEV): IDs are not a positive hint. Canonical JSON tie-breaks follow index order (disclosed). |

**Actual model conditioning** (loaded from the bundle, not assumed):
- **Sampler.** TaskCVAE with `task_on = True`, rule **S1** (top-M of a 64-draw Monte-Carlo marginal), M = 4 (top-6 drawn, top-4 kept).
  - Per queried object it receives `scene_features`: every object's attributes, cell, base-relative position, and offsets relative to the queried object. IDs are sorted by name.
  - It also receives `task_features`: goal one-hot, target-cell one-hot, query-to-goal and query-to-target offsets, and the ctx vector (q_ref sin/cos and goal xy).
  - So the released cVAE **is** conditioned on the original goal and target. The plan's concern came from `scene_features` alone. Under retargeting, the temporary task enters through the rebased `tid` / `goal` / `ctx`.
- **Scorer.** XYNet arm D with `vis_dim = 0`. `xy._NoGeo` returns zeros for all 13 Y and 8 X GEO columns.
- **Production rule.** NOOP gate 0.5, η 0.3, α = β = γ = 0.

## 2. Implementation issues and fixes (scaling path only)

| Issue | Historical code | Scaling path |
|---|---|---|
| m! materialisation | `r24/arms.score_set` builds every order of the set even for m > 3 | `compose.requests` reads only (U, ordered chunk ≤ 3) pairs. For m = 8: 15,360 ordered chunk evaluations, N_X(8) = Σ_g g!·C(8,g)·2^(8−g) (tested), vs 40,320 orders × 81 chunkings. *(R4.0 correction: an earlier version of this row said 1,800; the code and test always used 15,360.)* |
| Chunk size hard-coded | `order.dp` loops `range(1, 3)` and ignores `Table.maxg` | `compose.GMAX` |
| Multi-action constraint | `order.dp` `min_chunks` is exact only for 1 and 2; there is no has_multi state | DP state (U, has_multi); fixed-order prefix DP with has_multi |
| Displacement tie-break | `rank.select`, `rank.b0`, `recursive.seeds` | Removed from scaling ranking: (round(E, 12), length, chunks, canonical JSON). The production floor `rank.b0` is unchanged. |
| Return penalty | λ = −log 0.92 in `order.dp` | Primary λ = 0 (chunk X already includes its terminal connector); −log 0.92 kept as a named control |
| Low-X / high-temporary-Y repairs | `recursive.repairs` keeps the top-2 by temporary p11 | Default-off option `ylowx_extra`; the scaling arms keep one extra admitted high-temporary-Y repair per action |

**Tests** (`tests/test_kgt3.py`, 22 pass):
- grouped and fixed-order DP equal brute force for m ≤ 6, across variable chunks, has_multi, random precedence and λ ∈ {0, −log 0.92};
- the grouped DP equals the historical `order.dp` (same E, order and partition);
- the DP reads only requested scores;
- exact assignment counts equal brute force, with the e_k upper bound holding;
- the guard behaviour in §3.

## 3. Fail-closed completion guard (`guard.py`)

- **Seal and completion.** `seal` records the manifest sha and keys. `complete` returns COMPLETE only when the seal matches, every sealed key has exactly one terminal record (DONE, UNKNOWN, ERROR or CENSORED), and there are no duplicate or unexpected keys. Missing jobs are NOT_RUN, never negatives.
- **Decisions.** `decide` writes a gate decision bound to the sha256 of every input file and refuses unless every cited manifest is COMPLETE.
- **Dispatch.** `authorize` re-verifies the bindings and the decision field before any gated dispatch.
- **Tested cases:** premature completion, decide-on-partial, dispatch with a failed gate, a duplicate record after a decision, manifest edits after sealing, and duplicate keys.

## 4. Planner runtime (P0 smoke run, RTX 5090, CUDA-synchronised)

| Domain | REC-ORDERED / REC-REORDER / FLAT-INSERT | GA | GA-YONLY |
|---|---|---|---|
| 3D (DEV K4) | 1.0–2.8 s | **EXACT**, 76–82 s: all 2.9–3.2k size-5 and 2.5–2.6k size-4 assignments; 0.36–0.40 M X scores | 0.6 s |
| 2D (cohort K4) | 23–35 s | **BOUNDED**, 47–49 s | 2.1 s |

All runs are within the 180 s cap. These are smoke runs on exposed roots, so no outcome was used and nothing was tuned.

## 5. Quarantined A2 outcomes

These are opened in P1 only as DIAGNOSTIC_ONLY copies; the originals stay write-protected. Coverage: R3.4 20/39 sealed jobs, regression 29/60. They support no gate, recovery rate, regression claim, training or selection.
