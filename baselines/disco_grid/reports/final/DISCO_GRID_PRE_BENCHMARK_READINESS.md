# DISCO-Grid: pre-benchmark readiness

**Scope.** This report covers DISCO-Grid's scaled training (stateful physical MCTS on TRAIN, distilled into policy and value networks), its ablations, and its freeze, all selected on **VALIDATION** only.

The following were **not used**:
- TEST.
- The V3.4 fresh cohort.
- The new expanded benchmark dataset.

Cross-method comparisons are deliberately left out; they come later, on the frozen benchmark cohort.

Branch: `naren/disco-grid-final`. Freeze record: [`DISCO_GRID_FREEZE_MANIFEST.json`](DISCO_GRID_FREEZE_MANIFEST.json).

## 1. Training data (TRAIN only)

**Cohorts:**
- The cohorts are `cohort_2d.json` (128 roots) and `cohort_3d.json` (86 roots). Every root is `split = train`.
- Dataset-wide split hygiene shows 0 root, family, layout, raw-hash or input-hash conflicts.
- I re-checked overlap with the VAL ids and the V3.4 cohort (1,114 roots): 0.

**Search:**
- Search is stateful progressive-widening MCTS over the unchanged physical adapter (DISCO stage-2 engine).
- **Round R0:** P0 proposals.
- **Round R1:** proposals from the R0 ALL / O0 / all-feasible / seed-0 fit.
- Hosts: gvlab, girish, gvlab2, enigma, dinesh and the laptop, all within the user's per-host limits. Roots were disjoint across hosts via preclaim or `--roots-file`.

**Incomplete trees:**
- A tree counted as complete only with a clean checkpoint and no IN_FLIGHT, ACTIVE_QUERY or BLOCKED_WALL_LIMIT marker.
- Incomplete trees were requeued as new attempts with new seeds; nothing was resumed or relabelled.
- Duplicates were resolved by the earliest-attempt rule (`MERGE_INDEX*.json`).

| | R0 trees | R1 trees |
|---|---|---|
| 2D | 117 clean | 127 clean. `2d-conv-plus2d-srv-w0076-s006` was excluded after hitting the wall limit on both attempts |
| 3D | 86 | 86 |

## 2. Fits

All fits are TRAIN-only and use 3 initialization seeds unless noted.

| Arm | 2D | 3D |
|---|---|---|
| R0 ladder L16 / L48 / ALL (O0, all-feasible) | ✓ | ✓ |
| R0 budget arm (trees truncated to 32 calls in 2D, 16 in 3D) | ✓ | ✓ |
| R1 ALL: O0 all-feasible, O0 successful-only, O1 all-feasible | ✓ (warm-start from R0) | ✓ |

## 3. Physical gates (stage-2 engine rerun, TRAIN)

The gates ran on girish (`gates/gates_{2d,3d}.json`).

**Order results** (2D: 5 roots, 17 orders; 3D: 4 roots, 14 orders):
- **24 orders** executed and decided X/Y exactly equal to the finalized labels.
- **7 orders** failed physically mid-sequence (NO_PLAN_FOUND or CERTIFIED). All 7 have finalized label X = 0, so they are consistent.

**Per-step checks passed:**
- every action is legal in the observation;
- moved objects leave the eligible set;
- the gripper is released;
- q changes.

**NOOP gate (G5)** passes in both domains. The earlier old-engine gates had also passed.

## 4. VAL evaluation (all arms sealed, then independently verified)

**Pipeline:**
- `predict.py` reads public rows only and runs the frozen stage-2 rule (B = 16 in 2D, 12 in 3D). It runs without a simulator or MCTS.
- It is open-loop: one committed sequence per root.
- Every prediction file was **sealed before any teacher call**: 36 files, all seals match.
- Each file then went through the V3.4 harness (`benchmark.py` queries → teach → evaluate → summarize) with the unchanged finalized teachers.
- Teacher source hashes were identical on all teach hosts.
- **0 UNKNOWN in every arm.** VAL has 751 roots in 2D and 364 in 3D.

Mean (sd) is over seeds. Per-seed rows are in `val/VAL_ARMS.json`, and the summaries in `val/summaries/`.

| Arm | Seeds | Task % mean (sd) | K1 / K2 / K3 | NOOP % | ABSTAIN % |
|---|---|---|---|---|---|
| 2D R0 L16 | 1 | 11.9 | 30.0 / 10.0 / 0.6 | 5.8 | 0 |
| 2D R0 L48 | 1 | 12.6 | 30.8 / 11.7 / 0.6 | 6.4 | 0 |
| 2D R0 ALL | 3 | 13.6 (2.4) | 29.7 / 15.8 / 1.0 | 6.9 | 0 |
| 2D R0 ALL, budget c32 | 1 | 13.8 | 30.8 / 15.8 / 0.6 | 14.9 | 0 |
| 2D R0 ALL, policy-only | 1 | 6.8 | 16.7 / 6.7 / 0.0 | 29.3 | 0 |
| 2D R1 ALL, all-feasible | 3 | 14.8 (1.2) | 33.1 / 16.7 / 1.0 | 14.2 | 0 |
| **2D R1 ALL, successful-only** | 3 | **21.1 (3.2)** | 42.5 / 26.4 / 2.5 | 13.5 | 0 |
| 2D R1 ALL, policy-only | 1 | 6.8 | 15.8 / 7.5 / 0.0 | 20.2 | 0 |
| 3D R0 L16 | 3 | 28.8 (0.9) | 50.3 / 32.3 / 7.6 | 24.3 | 0 |
| 3D R0 L48 | 3 | 36.5 (4.5) | 61.0 / 37.5 / 16.7 | 30.2 | 0 |
| 3D R0 ALL | 3 | 31.7 (4.5) | 54.7 / 29.9 / 16.7 | 32.5 | 0 |
| 3D R0 ALL, budget c16 | 3 | 28.9 (2.1) | 49.1 / 23.7 / 21.0 | 34.5 | 0 |
| 3D R0 ALL, policy-only | 3 | 26.2 (0.9) | 46.5 / 25.1 / 12.4 | 48.6 | 0 |
| 3D R1 ALL, all-feasible | 3 | 36.1 (3.2) | 56.0 / 38.1 / 18.1 | 43.5 | 0 |
| **3D R1 ALL, successful-only** | 3 | **36.8 (1.6)** | 57.9 / 37.1 / 20.5 | 43.9 | 0 |
| 3D R1 ALL, policy-only | 1 | 26.4 | 41.5 / 24.7 / 17.1 | 48.2 | 0 |

**Reference point:** the earlier small E16 DISCO run, same harness, seed 0, scored 4.4% task in 2D and 14.6% in 3D. The frozen scaled arms reach about 4.8× that task success in 2D (21.1%) and about 2.5× in 3D (36.8%). That is the evidence the training pipeline works as intended.

**Ablation read-outs** (VAL; differences below about 1 sd are not meaningful):

**Iterated search and distillation (R0 → R1)**
- 2D: +1.2 points all-feasible, +7.5 successful-only.
- 3D: +4.4 points ALL.

**Successful-only vs all-feasible targets (R1)**
- 2D: +6.3 points.
- 3D: +0.7 points (within noise).

**Value head**
- Policy-only loses 5.5–9.7 points in both domains and both rounds (2D R0 6.8, R1 8.0; 3D R0 5.5, R1 9.7).
- So policy+value is required.

**Tree-coverage ladder**
- 3D: L16 → L48 gains 7.7 points; ALL is not better than L48 in R0.
- 2D: the ladder is flat (11.9 / 12.6 / 13.6).

**Search budget (truncated trees)**
- 2D: c32 matches ALL.
- 3D: c16 loses 2.8 points.

**K3 is the weak point**
- 2D: at most 2.5%.
- 3D: about 20%.

**STOP calibration**
- The stage-2 rule is frozen: `noop_q_gate .55, stop_q_margin .02, abstain_eta 0, policy_stop_thresh .45, stop_q_min .35, noop_pol_gate .5`.
- It was **not re-tuned** on these VAL runs.
- With `abstain_eta = 0`, DISCO never abstains, so ABSTAIN is 0% and NONE roots always get a repair attempt.
- NOOP precision on K0 is low (2D about 14%, 3D about 44%): DISCO often repairs K0 roots that need no change.
- Both are properties of the published-style stop rule and are reported, not hidden.

## 5. Freeze

**Selection rule:** the highest mean VAL task rate over 3 seeds among final-round (R1) policy+value arms. The rule was applied once.

| | Frozen arm | Seeds | VAL task |
|---|---|---|---|
| 2D | R1 ALL, O0, **successful-only**, policy+value | 0, 1, 2 | 21.1 (3.2) |
| 3D | R1 ALL, O0, **successful-only**, policy+value | 0, 1, 2 | 36.8 (1.6) |

**Frozen weights:**
- The weights are committed under `frozen_models/` with `SHA256SUMS`; the hashes match the gvlab originals.
- Re-predicting on the laptop from the committed weights reproduces the sealed gvlab VAL predictions: 3D s0 on 5 of 5 roots, 2D s1 on 8 of 8.

**Benchmark entry:**
1. Run `python predict.py --model-dir reports/final/frozen_models/<D>_R1_ALL_succonly_s<S> --input <public_<D>.jsonl> --output pred_<D>_s<S>.jsonl --seed <S>` on CPU. The defaults are the frozen rule and B.
2. Then run `approach_b_final/benchmark.py`: seal, queries, teach, evaluate, summarize.

## 6. Not done / open

**O1 closed-loop physical evaluation is not run.**
- It executes real physics per step, and `physical_eval.py` refuses to run without a separately **APPROVED** evaluation envelope. That envelope must not be self-authorized, so this needs the user's explicit approval.
- The O1 fits exist (R1 ALL, 3 seeds).
- If approved: a matched O0-vs-O1 closed-loop run on a VAL subset of about 60 roots per domain, with 1–4 workers.
- Open-loop (the primary protocol) is complete. Closed-loop would be reported separately, as the published-style secondary protocol.

**Known limits:**
- Finite K ≤ 3 and discrete destination cells.
- Known state; no push, swap or new grasp.
- Open-loop deployment cannot observe intermediate q.
- One R1 2D root was excluded (wall limit).
