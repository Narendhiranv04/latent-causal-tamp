# Analytical baselines (E-M4M, MO-SeGMan, MS-MCTS): pre-benchmark report

**Scope.** This report covers the implementation, contract tests and full **VALIDATION** run of the three analytical repair planners, on the K ≤ 3 target-repair benchmark in 2D and 3D.

The following were **not used**:
- TEST.
- The V3.4 fresh cohort.
- The new expanded benchmark dataset.

Cross-method comparisons are deliberately left out and will be made later, on the frozen benchmark cohort. This report only establishes that the baselines are implemented correctly and ready.

Branch: `naren/analytical-baselines-k3-finalize`. All VAL shards ran code commit `0fd751c40f`.

## 1. What was implemented

All three methods are **adapted re-implementations** under the benchmark contract. The paper-by-paper deviations are listed in [`ADAPTATIONS.md`](../ADAPTATIONS.md); the defects found in the legacy 2D port `14ade19a` and their fixes are in [`AUDIT.md`](../AUDIT.md).

**Contract:**
- **Decision:** one committed decision per root: REPAIR, NOOP or ABSTAIN.
- **Repair constraints:**
  - A repair has at most 3 ordered relocations.
  - Only movable non-target objects may be moved, each at most once.
  - Each must go to a legal cell that is free now and was empty in the original scene, never the goal cell.
  - Illegal actions are rejected before physics is called.
- **Physics:** every relocation is executed physically from the **carried** robot, gripper and physics state, using DISCO stage-2 `RepairEnv` (read-only).
  - 2D uses BXY DetPhysics.
  - 3D uses fin3d with xArm7 and MuJoCo 3.16.
- **Goal test:** the X terminal connector, then the Y target query in the canonical endpoint scene.
- **State identity:** includes the robot configuration q and the gripper.
- **Labels:** private labels are never read.
- **Oracle-assisted regime (disclosed):**
  - Search-time physical X/Y queries are allowed and counted per root: transitions, connector calls, Y calls, reference plans, grasp attempts and capped calls.
  - A capped call counts as UNKNOWN, which the search treats as a planner failure. It is never used as a label.
- **Budget:** 300 CPU-s per root (the whole process). The 60 CPU-s results are read from the same run by `run.py cut`, which is exact; see `config/grid.json`.

**Tests:** `pytest baselines/analytical/tests` gives **85 passed, 2 skipped**. The 2 skipped tests are the host-gated real-physics checks, which ran separately; see `reports/real_checks_{2d,3d}.json`.

## 2. VAL execution

| | 2D | 3D |
|---|---|---|
| Roots (existing VAL split) | 751 | 364 |
| Shards | 48 | 24 |
| Runs (config `paper`, 300 CPU-s) | E-M4M s0, MO-SeGMan s0, MS-MCTS s0/s1/s2 | same |
| Exactly one prediction per root and run | 751 of 751, for all 5 runs | 364 of 364, for all 5 runs |
| Hosts | laptop, gvlab2 | gvlab2, enigma, laptop |

**Execution details:**
- One process per shard, with `OMP_NUM_THREADS=1` and `nice 10`.
- Remote hosts ran byte-identical copies of the code; per-file sha256 was checked against the laptop worktree.
- The DISCO `env.py`/`data.py` and NOR `homotopy.py` hashes are identical in all 160 shard manifests.
- MS-MCTS seeds 1 and 2 were written to separate shard trees (`seeds12/`) so the seed-0 manifests were not overwritten.

**Verification:**
- Shards were merged by `run.py merge`, which asserts exactly one prediction per public root and no duplicates.
- The 60 s cut was applied.
- Every run file was **sealed (sha256) before any teacher call**.
- Each file was then verified independently through the unchanged V3.4 harness (`approach_b_final/benchmark.py` validate → queries → teach → evaluate → summarize) with the unchanged finalized teachers.
- Teacher source hashes were identical on all verification hosts.
- On the remote hosts, the private-index copies had only their raw-root *paths* rewritten to the host layout; the originals are kept as `*.laptop`.

## 3. Results (VAL, verified X·Y, 0 UNKNOWN in all 20 runs)

The task rate is over K1–K3 roots, with a bootstrap 95% CI. NOOP is the correct-NOOP rate on K0 roots, and ABSTAIN is the correct-ABSTAIN rate on NONE roots. Full tables, including CPU, physical-call and per-K columns, are in `reports/val/2d/REPORT_2d.md` and `reports/val/3d/REPORT_3d.md`.

### 2D (751 roots)

| Run | Task % [95% CI] at 300 s | Task % at 60 s (cut) | NOOP % | ABSTAIN % | Verified outcomes at 300 s |
|---|---|---|---|---|---|
| E-M4M s0 | 65.1 [61.0, 69.0] | 25.4 | 99.5 | 96.0 | 275 SUCCESS · 187 NOOP · 289 ABSTAIN |
| MO-SeGMan s0 | 29.1 [25.2, 32.7] | 7.3 | 99.5 | 97.3 | 124 SUCCESS · 187 NOOP · 440 ABSTAIN |
| MS-MCTS s0 | 31.7 [28.1, 35.4] | 22.5 | 100 | 97.3 | 135 SUCCESS · 188 NOOP · 428 ABSTAIN |
| MS-MCTS s1 | 31.7 [28.1, 35.4] | 24.7 | 100 | 97.3 | 135 SUCCESS · 188 NOOP · 428 ABSTAIN |
| MS-MCTS s2 | 32.0 [28.3, 35.6] | 23.2 | 100 | 97.3 | 136 SUCCESS · 188 NOOP · 427 ABSTAIN |

### 3D (364 roots)

| Run | Task % [95% CI] at 300 s | Task % at 60 s (cut) | NOOP % | ABSTAIN % | Verified outcomes at 300 s |
|---|---|---|---|---|---|
| E-M4M s0 | 67.3 [61.4, 72.7] | 15.5 | 97.6 | 100 | 149 SUCCESS · 83 NOOP · 132 ABSTAIN |
| MO-SeGMan s0 | 39.1 [34.1, 45.0] | 5.5 | 97.6 | 100 | 87 SUCCESS · **1 FAIL_X** · 83 NOOP · 193 ABSTAIN |
| MS-MCTS s0 | 45.5 [39.6, 51.4] | 15.5 | 100 | 100 | 101 SUCCESS · 85 NOOP · 178 ABSTAIN |
| MS-MCTS s1 | 45.5 [39.5, 51.8] | 19.6 | 98.8 | 100 | 102 SUCCESS · 84 NOOP · 178 ABSTAIN |
| MS-MCTS s2 | 45.5 [39.6, 51.8] | 19.1 | 98.8 | 100 | 102 SUCCESS · 84 NOOP · 178 ABSTAIN |

### Observations relevant to correctness

**1. Committed repairs are almost always verified.**
- 1,346 of 1,347 committed 300 s repairs across all 10 runs were confirmed X = Y = 1 by the independent teachers.
- This is expected in the oracle-assisted regime: a REPAIR is committed only after the search-time terminal check succeeds.
- Failures therefore show up as ABSTAIN (EXHAUSTED or TIMEOUT), not as FAIL_Y.

**2. The single discrepancy is 3D MO-SeGMan on `3ds66-srv3-w0069-s005`.**
- The committed repair was `[[3,32],[1,29],[2,24]]`. The search-time terminal check returned X = 1 and Y = 1, but the independent replay returned FAIL_X.
- The search executes moves from the carried state of DISCO `RepairEnv`, while the teacher replays the sequence from scratch. A stochastic grasp or IK difference between the two is the likely cause.
- It is counted as a failure; nothing was retried.

**3. MS-MCTS is nearly seed-invariant at 300 s.**
- Seeds 0, 1 and 2 differ by at most 1 root in both domains.
- The seeds mainly change rollout order, which affects *when* a solution is found: the 60 s cut differs by up to 4 points between seeds.

**4. The budget matters.**
- Every method loses a large share of its successes at 60 s. E-M4M 2D drops from 65.1 to 25.4, for example.
- Both budgets are kept in the frozen schedule.

**5. NONE roots.**
- 2D: a few NONE roots are repaired successfully (correct ABSTAIN 96–97%), which again shows that NONE means "not found by the historical teacher scope".
- 3D: all NONE roots are ABSTAIN.

## 4. Readiness

**Ready.** See [`ANALYTICAL_READINESS_MANIFEST.json`](ANALYTICAL_READINESS_MANIFEST.json). For each run it records:
- the predictions sha256 and whether the seal matches;
- verified outcome counts and UNKNOWN = 0;
- the frozen config, budgets, dependency hashes and benchmark entry command.

**Frozen for the benchmark:**
- Methods {E-M4M, MO-SeGMan, MS-MCTS}.
- Config `paper`.
- Budget 300 CPU-s, with a 60 s cut.
- Seed 0 for all three methods, plus MS-MCTS seeds 1 and 2.
- Per-call cap 45 s, reference-plan cap 120 s.

Nothing was tuned on VAL: the grid default `paper` was fixed before VAL from the TRAIN smoke and dev runs (`AUDIT.md` §6).

**Benchmark entry:**
1. Run `val.sh run DOM I K em4m,mosegman,msmcts paper 0 300` per shard, with the benchmark's public file as `$AB_OUT/eval/public_val_DOM.jsonl`.
2. Run `val.sh finish DOM K 60`.

**Known limits** (carried over from `AUDIT.md` §7):
- Under heavy host load, a 3D Y query can hit the 45 s per-call cap. It then becomes UNKNOWN, which the planner treats as a failure. Benchmark runs should keep host load well below core count.
- Not reproduced by design: RRT re-plan per critical subset, CBS paths, continuous poses, pushes and non-monotone moves.
