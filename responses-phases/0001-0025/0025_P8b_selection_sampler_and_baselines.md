# 0025 — P8b: repair-selection funnel, thresholds, sampler mixing and the geometry + full-motion baseline

**Actual result.** On P7 validation and legacy-test roots, with no new teacher call, the **candidate pool** and
**ranking** limit selection, not motion execution:

- **Coverage ceiling:** only 10 of 12 validation roots and 7 of 12 legacy roots contain any VERIFIED catalogue repair.
- **Ranking is the bottleneck:** every chosen candidate whose recorded relocation succeeded also succeeded at the target
  (0 "relocation witness but target failed").
- **Offline selection success at validation-chosen thresholds** (validation / legacy):
  - B-full 8 / 5;
  - **G+M (no learning) 7 / 6**;
  - B-structured 6 / 5;
  - A 4 / 5;
  - C-full 5 / 4;
  - B-none 3 / 3;
  - SF 2 / 3;
  - uniform 4 / 2.
- **Empty repair:** SF chooses it falsely on 8 / 12 validation roots at p ≥ 0.5; validation-chosen thresholds of 0.85
  remove all such errors for A, B-none, SF and C-full.
- **Sampler:** exact detailed balance holds, but on a 356-state pool a 4,000-step chain is far from stationary
  (TV 0.20–0.21; 0.10 at 16,000). By the predeclared rule, **P8d uses deterministic bounded-pool ranking.**
- **G+M** runs under `ordered.primary_v2` with the common budget and audit.

**Gate:** `runs/p8/P8B_GATE.json` → **`P8B_ENGINEERING_PASS`** (7/7). Compute: **285.0 / 3,000 CPU-s**, 0 teacher calls,
0 target executions. Revision: `33c6133` (P8a) plus P8b evidence in this commit.

## 1. Predeclared method (`p8_select.py`, `p8b_run.py`)

- **Models:** the seed-0 FULL_DECIDED checkpoint of each P8a arm at its chosen configuration; temperature fitted on P7
  validation.
- **Selection rule (unchanged):** among statically eligible candidates with calibrated p ≥ threshold, choose fewest moves,
  then lowest predicted J, smallest analytic displacement, lowest feasibility energy, then id. An empty admitted set means
  ABSTAIN, counted as failure.
- **Threshold family** {0.5, 0.7, 0.85, 0.95}, chosen on P7b **validation** roots by a lexicographic criterion:
  1. fewest false-feasible empty repairs;
  2. most offline successes;
  3. fewest moves.
- **Offline assessment** uses saved teacher records only *after* ranking: the chosen query's status and, from the teacher
  unit's `final.json`, whether its relocation was witnessed and the target result. Labels never enter a ranking.
- **Uniform (U):** seeded uniform order over the root's catalogue.
- **G+M:** deterministic geometry + full-motion ranking.
  1. Pose-only grasp screens for each mover in order, plus the LINK0 sector claim for the first action at the fixed
     start.
  2. Target grasp and goal-place screens after the moves.
  3. Then fewest moves, then analytic displacement.
  - The top 5 go through `ordered.primary_v2`, which plans complete 3R relocations in rank order under the same allowance
    as the learned arms. No teacher verdict is read.
  - **Constructor alignment:** P7/P8 families were *built* with these pose screens, so G+M may enjoy a constructor
    advantage. They are not an outcome oracle (motion-planner failures are invisible to them).
- **Sampler check:** G4B kernels on each learned sampling energy (Ē + displacement + predicted J) on three development
  pools (13, 46 and 356 canonical states, the last a 4-move root). Each uses 4 seeded chains of 4,000 and 16,000 steps,
  measuring TV against the exact π, energy-trace ESS, top-5 discovery, CPU and model calls. The **retain rule** (frozen
  in code before running) keeps the sampler only if every mean TV(4k) ≤ 0.10.

## 2. Root-level decision funnel (`runs/p8/b/decision_funnel.csv`; validation / legacy, 12 obstructed roots each)

| arm (threshold) | roots with a VERIFIED candidate | abstain | false-feasible empty | shorter infeasible choice preempts a longer VERIFIED one | success | minimal-length successes |
|---|---|---|---|---|---|---|
| B-full (0.5) | 10 / 7 | 1 / 1 | 0 / 0 | 1 / 0 | **8 / 5** | 8 / 5 |
| B-structured (0.5) | 10 / 7 | 1 / 1 | 0 / 0 | 1 / 0 | 6 / 5 | 4 / 5 |
| A (0.85) | 10 / 7 | 5 / 2 | 0 / 0 | 1 / 0 | 4 / 5 | 4 / 1 |
| A (0.5) | — | 2 / 0 | **2 / 2** | 2 / 1 | 5 / 4 | 5 / 4 |
| C-full (0.85) | — | 4 / 6 | 0 / 0 | 1 / 0 | 5 / 4 | 3 / 4 |
| B-none (0.85) | — | 8 / 7 | 0 / 0 | 0 / 0 | 3 / 3 | 3 / 2 |
| B-none (0.5) | — | 4 / 2 | 3 / 3 | 3 / 1 | 3 / 4 | — |
| SF (0.85) | — | 8 / 7 | 0 / 0 | 1 / 0 | 2 / 3 | 2 / 2 |
| SF (0.5) | — | 2 / 3 | **8 / 4** | 7 / 4 | 0 / 2 | — |
| G+M | — | 0 / 0 | — | — | **7 / 6** | — |
| U | — | 0 / 0 | — | — | 4 / 2 | — |

- Minimality is **restricted-catalogue**: success with the fewest moves among VERIFIED catalogue repairs of that root.
- The first VERIFIED candidate's rank under each model's probability ordering is 0.1–1.1 on average. When the pool
  contains a feasible repair, learned arms usually rank one first; failures come from thresholding and length-first
  preemption.
- **False-feasible empty repairs** are concentrated in the factorized arms (SF, B-none) and A at p ≥ 0.5. All of them
  are against certified or operational negatives (`empty_repair_false_positive.gif`). The validation-chosen higher
  thresholds remove them but raise abstentions.

## 3. Sampler versus deterministic ranking

| arm | pool size | TV 4k | TV 16k | ESS 4k / 16k | top-5 found | chain CPU-s 4k / 16k | deterministic CPU-s (model calls) |
|---|---|---|---|---|---|---|---|
| A | 13 / 46 / 356 | 0.047 / 0.085 / **0.212** | 0.028 / 0.045 / 0.103 | 349–582 / 1,537–2,665 | 5 / 5 | 0.06 / 0.22–0.26 | 0.02 / 0.06 / 0.68 (13 / 46 / 356) |
| B-full | 13 / 46 / 356 | 0.045 / 0.077 / **0.201** | 0.025 / 0.044 / 0.098 | 299–384 / 1,543–1,958 | 5 / 5 | 0.06 / 0.22–0.26 | 0.04 / 0.22 / 2.59 |
| SF | 13 / 46 / 356 | 0.078 / 0.096 / **0.207** | 0.051 / 0.044 / 0.098 | 34–176 / 117–970 | 5 / 5 | 0.05 / 0.21–0.26 | 0.01 / 0.06 / 0.63 |

- Detailed balance passes for every arm and pool (error ≤ 1e-15).
- The chains find the top 5 states, but their empirical distribution is not the Boltzmann distribution at a realistic
  4,000-step budget on the largest pool.
- Exhaustive deterministic scoring of the same canonical pool costs at most 356 model calls and under 3 CPU-s. **Decision
  (`sampler_decision`): DETERMINISTIC_BOUNDED_POOL for P8d.** The sampling claim at this runtime is retired.

## 4. G+M protocol smoke (no target execution)

| root | committed repair | relocation plans | CPU-s | audit |
|---|---|---|---|---|
| p7_2026102402 | o00 > 60, o01 > 12 | 2 | 3.4 | PASS |
| p7_2026102406 | o00 > 37 | 1 | 2.1 | PASS |

The target evaluator was a stub that returns NOT_RUN, so no target was executed. On p7_2026102402, G+M commits the
repair whose target failed in the P7 teacher record (its pose screens cannot see that failure): an honest example of the
baseline's limitation.

## 5. Interpretation for P8c / P8d

- **Frozen for P8c / P8d:**
  - deterministic bounded-pool ranking (no sampler);
  - thresholds re-chosen on **P8c validation** with the same rule;
  - top 5 candidates per episode;
  - U and G+M baselines exactly as above.
- **Offline, B-full selects best on validation.** G+M matches or beats every learned arm on legacy roots, and uniform is
  clearly worse. The decisive comparison is the fresh P8d execution.

## 6. Artifacts and accounting

- **Code:** `p8_select.py`, `p8b_run.py`, `p8_gates.py` (gate_b).
- **Evidence:** `runs/p8/b/{results.json, decision_funnel.csv, guard.json, log.txt}`, `runs/p8/P8B_GATE.json`.
- **Figures:** `visualizations/p8/empty_repair_false_positive.gif`, `sampler_mixing.gif`, `P8_root_decision_funnel.png`
  (SHA-256 sidecars).
- **Compute:** P8b 285.0 / 3,000 CPU-s; figures 4.3 CPU-s.
