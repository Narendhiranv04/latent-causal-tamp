# V3.1-0 (resource and artifact audit) and V3.1-1 (infrastructure corrections)

**Branch:** `naren/approach-b-v3-1-validation`, from V3 `ede29034b2245d8e85171c92966e2944dd6eb81a`. The historical V3 results and reports are unchanged.

## V3.1-0 Compute manifest (gvlab, audited 2026-11-16 12:35 IST)

| Item | Observed |
|---|---|
| Execution host | `gvlab`, reached via the `gvlab` ssh alias from the laptop. The laptop is used only for editing, git and orchestration. |
| GPU | 2× RTX 4090, 24,564 MiB each, both 2 MiB used and 0 % utilisation. V3.1 GPU jobs use **GPU 0 only**, one job at a time, checked before each job. |
| CPU / RAM | 24 cores, load about 2; 60 GB available of 62 GB. |
| Disk | `/scratch` 221 GB free (94 % used); `/` 43 GB free. |
| DISCO | `/scratch/nav/disco_grid` (same `nav` uid): `pytest test_d1_parity.py`, about 1 core, no GPU. V3.1 never touches DISCO processes, environments or paths; it identifies them by path. |
| Other users | Only `watch nvidia-smi` sessions; no compute jobs. |
| V3.1 CPU policy | Tests and audits: ≤ 2 cores (taskset), nice 10. Teacher verification: start with ≤ 8 workers, re-measured before each batch; DISCO's measured usage plus ≥ 4 cores stay free. |
| Envs | `approachb_final/venv` (torch 2.5.1+cu124, CUDA OK); 2D teacher `~/approachb3d_v3/2d_q2_spillover/venv313`; 3D teacher `~/approachb3d_mock/env` (MuJoCo 3.16). These are the V1/V2 teacher hosts, so parity is native. |
| V3.1 paths | `/scratch/nav/abf_v3_1/{code,runs,logs}`. The V1 / V2 root `/scratch/nav/approachb_final` is read-only. |

## Artifact availability on gvlab

**Present and verified:**

| Artifact | Location / sha256 (first 16) |
|---|---|
| Base snapshot `abf_9de85710c2a7103f` | `approachb_final/snapshot/` (lock `1b3b9e939882a117`) |
| V2 snapshot `abf_v2_7d146b53e4b92fe4` | `approachb_final/snapshot/` (lock `76afe645e651ba2d`) |
| Q2 placement data | `approachb_final/data/q2_{2d,3d}` |
| Q2 cVAE / FM checkpoints | `approachb_final/runs/p1_{2d,3d}/{cvae,fm}_s{0,1,2}` |
| V1 + V2 scorers D / E / G / DIRECT, 3 seeds; travel heads | `approachb_final/runs/{p2,v2/p2}_{2d,3d}`, `runs/p3_*` |
| V2 searches, rules, verify caches (incl. test) | `approachb_final/runs/v2/p5_*` |
| V3 verify caches, all three hosts | `abf_v3/caches/final_g2_verify_2d` `097bc743…` (516 roots), `final_g2_verify_3d` `dcc08c68…` (291), `final_lap_verify_2d` `ad65356c…` (935), `final_lap_verify_3d` `866c23d4…` (671); `abf_v3/runs/verify_2d` `b232b549…` (180), `verify_3d` `15864705…` (76) |
| V3-6 test selections (15 arm-seeds per domain) | `abf_v3/runs/slim_test/{2d,3d}` |
| V3-6 witnessed travel | `abf_v3/runs/v3_6/TRAVEL_TEST.json` `84c391c1…` |
| Teacher witness stores (V1 / V2 / V3, all hosts) | `approachb_final/runs/…`, `abf_v3/runs/{teacher2d_witnesses,verify_store_3d}`, `abf_v3/stores/*` (349 MB) |

**Missing on gvlab.** These exist only on gvlab2 under `~/abf_v3/runs/`; per the V3.1 rules they were not retrieved.

| Artifact | Identity | Needed for |
|---|---|---|
| V3 snapshot `abf_v3_e8a496bc66266fca` | data2d `a10aeba8c74e4f12…`, data3d `fcb30732b7379961…` (lock in `reports/v3/v3_4/v3_snapshot.lock.json`) | Retraining or controls on V3 evidence |
| Task cVAEs, V3-3 | `v3_3/{2d,3d}/{scratch,q2init}_{one,all}, combined_one, goalablated_one _s{0,1,2}/model.pt` (36 files; sha256 not recorded in V3) | Frozen V3 sampler, parity |
| V3 scorers, V3-5 | `v3_5/p2_{2d,3d}/{D,E,G,DIRECT}_s{0,1,2}/model.pt` (24 files) | **Frozen V3 D for every isolated comparison, budget curve and full-pool re-tuning** |
| V3-4 labels / items / candidates | `v3_4/{2d,3d}/{labels,items,cands}_task:q2init_all-S1_M4_B4096_s0*` | Rebuilding the V3 snapshot |
| V3 per-root records with stored candidates | `v3_1 … v3_6/{2d,3d}/*.jsonl` | Full-pool analysis of existing runs (now superseded by full-pool re-runs) |

**Consequence.** V3 inference parity with the frozen checkpoints, all experiments that freeze the V3 D scorer (V3.1-A physical arm, V3.1-B, V3.1-C), and the D2–D5 attribution stages are **blocked on gvlab** until these artifacts are made available there, about 0.1 GB of checkpoints plus a 31 MB snapshot. They cannot be regenerated identically on gvlab: the V3-4 2D labels of 109 roots exist only on gvlab2, and retraining on a different torch and GPU would give different weights. Retraining instead would be a recorded methodological change; it is not done silently.

## V3.1-1 Infrastructure corrections (CPU only)

1. **Full candidate pool (V3.1-B):** `construct.run_root(store="all")`, or `V3_STORE_ALL=1`.
   - Stores every scored ordered sequence at full precision, plus the independent no-op.
   - Each entry carries its endpoint id (`endpoints` table), p11, P(Y), P(X|Y), m, D and Ĵ: every term of the selection cost.
   - Storage happens after selection, so candidates, scores, RNG and decision are unchanged. The compact V3 format stays the default for ordinary records.
2. **Tuning guards:**
   - `construct.gridslim` and `construct.tune` refuse truncated pools (`require_full`), unless `V3_ALLOW_TRUNCATED=1` is set to declare a restricted hypothesis.
   - `tune` no longer counts unverified selections as failures. Any rule with unresolved selections is marked `UNRESOLVED`, gets no objective, and cannot be chosen until the union of selections is physically verified.
3. **Matched goal ablation (V3.1-A):**
   - `placement.task_features(…, on="nogoal")` removes only the goal: the goal one-hot, the query-to-goal offset and the goal (x, y) inside the context vector (`CTX_GOAL`). It keeps the target one-hot and offset, the robot and target context, and `task_on`.
   - New variants:
     - `q2init_all_nogoal`: goal-only ablation;
     - `q2init_all_notask`: entire task-context ablation.
     Both are identical to `q2init_all` in init, assignments, weights, schedule, selection and architecture.
   - `goalablated_one` is kept and labelled **confounded**: it changes init, assignments and task input at once.
   - Training and loading stage is configurable (`V3_TASK_STAGE`, default `v3_3`), so V3.1 models go to new directories.

**Tests:** `tests/test_v31.py` adds 7 tests; 29 / 29 pass on gvlab (CPU, 2 cores). They cover:
- full count = scored + no-op;
- stored terms reproduce the decision;
- identical candidates and decision in full vs compact storage;
- full-list tuning picks a candidate missing from the top-2,048;
- the probability-only rule is unaffected;
- truncated pools are refused;
- unresolved selections are never failures;
- `nogoal` changes only goal fields and is goal-invariant; `notask` gives zeros;
- variants differ only in task input, with equal parameter counts;
- repair supervision (targets, weights, roots, scene inputs) is identical across task modes.

## Reporting corrections registered (to be carried into the final V3.1 report)

- The "goal-ablated" rows in V3-3 and V3-6 are confounded; see above.
- V3 rule tuning used truncated pools for 2D roots with more than 2,048 candidates. The selected rule (α = β = γ = 0) only needs the top candidate, so the frozen V3 rule is unaffected, but rules with non-zero penalties were evaluated on truncated pools.
- **5,458 labelled candidate sequences** (V3-4) is not the same as **6,961 newly added X/Y label entries** (2D 2,326 Y + 1,587 X; 3D 1,423 Y + 1,625 X).
- V3-7 status: the teammate's dataset extension was **deferred** while the methodology proceeded, not cancelled.

## Addendum: V3 artifacts on gvlab + inference parity (2026-11-16 13:15 IST)

- **Copy (user-approved, one time, read-only).** The frozen V3 artifacts were copied from gvlab2 to `/scratch/nav/abf_v3_1/v3_artifacts`, relayed through the laptop as a plain file transfer. Nothing was computed on gvlab2 or the laptop.
  - Contents: snapshot `abf_v3_e8a496bc66266fca`, `v3_3` task cVAEs, `v3_5` scorers / rules / tuning records, `v3_4` labels / items / candidates.
  - 8,015 files; sha256 verified at both ends against the source manifest (`SHA256SUMS.source`, sha256 `5fc6da800def7243…`); write-protected on gvlab.
- **Parity.** The frozen V3 primary (task cVAE q2init_all s0 + V3 D s0) was re-run on gvlab (RTX 4090, torch 2.5.1) on validation `valsub` (2D 300 / 3D 291 roots). It was compared with the original gvlab2 records (RTX 5090, torch 2.9.1), using the same seed, M = 4 and B = 4,096 (`v3_1_1/PARITY_GVLAB.json`):
  - identical proposal sets: 300 / 300 and 291 / 291;
  - identical stored candidate sets: 300 / 300 and 291 / 291;
  - max |Δp11| = 1.0e-6 (the stored rounding);
  - identical selections under the same rule: 300 / 300 (2D) and 291 / 291 (3D).
  The original valsub records were written under the V2 rule (2D β = 0.1) before V3-5 tuned the V3 rule. Re-selecting both record sets under either rule gives 300 / 300 agreement. **V3 inference is reproduced exactly on gvlab.**
