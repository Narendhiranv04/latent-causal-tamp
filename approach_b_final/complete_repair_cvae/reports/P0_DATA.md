# P0: provenance, data and parity audit

**Gate: PASS for P0/P1 (code, data, parity). P2–P4 are blocked on owner authorization (see `P0_PREREG.md` §0).** No teacher queries, no CR training and no held-out inference were run in P0.

## Provenance (`P0_PROVENANCE.json`)

- **Base:** `87ebf65d245dd9368397bf3577c9ff164cff619b` (`naren/rss27-xy-repair-ranking`), equal to `origin`. New branch `naren/rss27-complete-repair-cvae` in its own sparse worktree (`.claude/worktrees/cr-cvae`). No other worktree, branch, job or runtime directory was touched. The parallel K4/K5 worktree (`k45`) exists and was not opened.
- **Plan / prompt:** `plan.md` and `starting_prompt.md` are byte copies of `instruction-phase-md/cvae_ablation/complete_repair_cvae_{plan,opus55_prompt}.md` (sha256 `e13f92d2…`, `a598963c…`).
- **Released bundle** `~/abf_v34/approach_b_bundle`: all 10 manifest hashes verified.

| | 2D | 3D |
|---|---|---|
| Per-object sampler | TaskCVAE `scratch_all` s0, h 128, z 8, S1 rule (n_z 64, top-6 → top-4), proposal seed 0 | same family |
| Sampler training (from checkpoint, not defaults) | fixed **2,400** steps, eval every 30, batch 256, warm 10 evals, best VAL at step **810** | fixed **1,520** steps, eval every 19, best at step **665** |
| Sampler corpus | 1,938 TRAIN roots, 9,729 actions | 1,158 roots, 6,807 actions |
| Scorer | coupled X/Y **arm D** seed 0, epoch 48 | arm D seed 0, epoch 57 |
| Scorer/sampler TRAIN snapshot | `abf_v32_fb0eef4f5ff433ee` (sha `963c16b2…` / `bc03d896…`) | same snapshot |
| VAL snapshot (sampler selection) | `abf_9de85710c2a7103f` (sha `16222ff8…` / `1627f34b…`) | same |
| Rule | `noop_gate 0.5 / eta 0.3 / alpha = beta = gamma = 0`, M = 4, K_max = 3 | same |

The historical `fit_task` defaults (80 epochs, patience 15) are **not** what produced the released sampler: it ran the fixed-step mode above. The CR-cVAE matches the actual fixed-step budget (P0_PREREG §3).

## Teacher runtime (actual source, not assumed)

Both teachers are on this laptop (`pop-os`), the host that produced every V3.4 cohort label: `~/abf_v3_laptop/env2d`, `env3d`; source hashes in `P0_PROVENANCE.json`. The runtime `teacher2d.py` is byte-identical to the frozen repo copy.

| | 2D (`teacher2d` → `bxy_teacher`) | 3D (`fin3d.py` @ yadu/dataset-3d fb1120a30) |
|---|---|---|
| Field carrying resolution | `status` | `resolution` (+ free-text `status`) |
| Decided positive | `VERIFIED`, `EMPTY` (X of the empty sequence) | `resolution = EVALUATED`, value 1 |
| Decided negative | `CERTIFIED_INFEASIBLE` | `resolution = EVALUATED`, value 0 — **includes planner-budget failures by the teacher's own contract** ("Planner-budget failure = 0"; RRT iteration ceiling, no wall-clock cut). Reasons seen: `no feasible side grasp` (all grasps failed, geometric or RRT), `EXECUTION_NOT_VERIFIED`, `CONNECTOR_NO_PLAN` |
| Unresolved | `UNKNOWN_PLANNER`, `UNKNOWN_TRANSIT` (stored with value **0**) | `UNRESOLVED_ADMIN` (3,600 s wall), `UNRESOLVED_ERROR` |

- **V3.4's "0 UNKNOWN" is an operational convention.** Its 2D caches hold 123 X and 132 Y results with `UNKNOWN_*` status and value 0 (all cohort roots, not only this roster). V3.4 counted them as failures. Under this study's strict mapping they are UNKNOWN. Both are reported (P0_PREREG §6).
- **3D strict = teacher contract.** `fin3d` does not store whether a `no feasible side grasp` negative was geometric (`CERTIFIED` in `bd_3dt.kind`) or an RRT give-up, so 3D "decided 0" cannot be split further. This is disclosed, not corrected.

## TRAIN corpus (`P0_DATA.json`, `figures/p0_corpus.png`)

The supervision is rebuilt from the snapshot with `contracts.positive_assignments` + `contracts.v3_grammar` and **reproduces the released sampler's corpus exactly**: 2D 1,938 roots / 9,729 actions, 3D 1,158 / 6,807.

| TRAIN | 2D | 3D |
|---|---|---|
| Roots (all classes) | 3,500 | 1,766 |
| Roots with ≥ 1 verified legal repair | 1,938 | 1,158 |
| Distinct verified assignments (size 1 / 2 / 3) | 4,409 (1,017 / 1,464 / 1,928) | 3,032 (538 / 1,213 / 1,281) |
| Distinct verified ordered repairs (= training triples) | **6,394** | **4,890** |
| 3-object assignments with all 6 orders verified | 121 of 1,928 | 67 of 1,281 |
| Families | 1,574 | 871 |

- **Orders.** Only orders the teacher verified (X = 1 on a Y = 1 endpoint) are targets; 1,264 of 1,928 2D three-object assignments have exactly one verified order, so permutation augmentation would add mostly unverified orders. None is added.
- **Weights.** w(i, A, r) = 1 / (|A_i| · |O_iA|); every root's weights sum to exactly 1 (checked on TRAIN and VAL, max error < 1e-9), matching `placement.repair_data` (1 / |A_i| · 1 / |A| per action).
- **Endpoint join.** X rows are joined to Y by the canonical endpoint key (`contracts.ekey`), never by list index (unit test).
- **Legacy K vs shortest verified repair (TRAIN):** 2D K1 548 equal / 3 longer only / 9 none; K2 552 / 2 shorter / 6 none; K3 786 / 1 shorter / 18 none. 3D: K2 4 shorter, K3 8 shorter. K is training-loader metadata only; it is never a model input.
- **VAL is not expanded:** each VAL root carries only its legacy selected assignment (2D 404 roots / 719 orders; 3D 219 / 449). VAL witness coverage is therefore a narrow lower bound.

## Root decision labels (plan 3.2)

| Label | Rule | 2D TRAIN / VAL | 3D TRAIN / VAL |
|---|---|---|---|
| NOOP | verified Y(empty) = 1, legacy K0 | 875 / 188 | 358 / 85 |
| REPAIR | Y(empty) = 0, legacy K1–K3, ≥ 1 verified legal repair | 1,892 / 404 | 1,120 / 219 |
| ABSTAIN | Y(empty) = 0, legacy NONE, no verified repair | 699 / 150 | 288 / 58 |
| MASKED | anything else | 34 / 9 | 0 / 2 |

- **ABSTAIN is benchmark-relative.** Legacy NONE means "no repair found by the historical teacher scope", not impossibility; V3.4 found 4 verified 2D repairs on NONE roots. The label is kept with that meaning and named as such.
- **Masked roots (decision loss only):** legacy K1–K3 without a finalized repair (2D 33), one 2D TRAIN NONE root with a verified repair (label contradiction), one 3D VAL K0 root with Y(empty) = 0, one 3D VAL K2 root without a finalized repair. Their repairs, if any, still enter the ELBO.
- **K0 roots with verified repairs** (2D 45, 3D 38 TRAIN) are NOOP for the decision head and contribute their repairs to the ELBO, exactly as in the released sampler's corpus.

## Split integrity

- TRAIN/VAL family overlap: 0 (both domains). VAL rows are byte-identical between the TRAIN snapshot and the base snapshot.
- **Layout fingerprint overlap** (same occupied cells, target cell and goal): 15 2D and **58 3D** VAL roots share a layout with a TRAIN root. Kept and disclosed; DEV diagnostics will be repeated without them.
- **Locked cohort (V3.4 fresh, Option B):** 0 of its 541 2D / 181 3D families occur in TRAIN or VAL. Its roots are disjoint by id, seed, sha256 and GEOM_V1 fingerprint (V3.4 report).

## C0 parity (`P0_PARITY_{2d,3d}.json`)

The frozen EXACT4 path re-run through this package (`infer.c0` → `exhaustive.proposals` + `exhaustive.score_root`) against the archived laptop-GPU VAL predictions of the same bundle, on 20 VAL roots per domain (4 per legacy stratum K0/K1/K2/K3/NONE, chosen by sha256 `CRCVAE_PARITY_V1`):

| | decisions + sequences equal | top-4 proposals equal | max |p11 − archived| |
|---|---|---|---|
| 2D | 20 / 20 | 20 / 20 | 0.0 |
| 3D | 20 / 20 | 20 / 20 | 0.0 |

## Resources and environment

- Laptop: 32 threads, RTX 5060 Laptop 8 GB (7.2 GB free), torch 2.9.1+cu128 (`~/miniconda3`). Load was ~0.7 during P0; no other experiment process was running. Another Claude Code session is open on this machine (assumed to be the K45 study); it had no running jobs.
- **Storage: `/home` has 2.0 GB free (100 % used).** The proposed 15 GiB cannot be provided here. The study's footprint is small (checkpoints of about 2 MB each; pools and predictions of tens of MB), so P2–P4 fit if kept under 1 GB. No large caches will be written.
- P0 compute: C0 parity on 40 VAL roots (about 1 min GPU); the overfit sanity fits ran on CPU.
