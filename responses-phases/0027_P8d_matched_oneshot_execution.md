# 0027 — P8d: independent matched one-shot 2D execution on 12 fresh sealed roots

**Actual result.** All 72 planned one-shot simulator episodes resolved (64 attempted, 8 abstained): 12 fresh sealed
P8c test roots × 6 arms, at most 5 ranked candidates, one target attempt after commit, 180 CPU-s per episode,
**2,245.1 / 12,000 CPU-s**.

| arm | GOAL_AND_SAFE_RETREAT success |
|---|---|
| **Geometry + full motion (G+M), no learning** | **9 / 12** |
| B-full | 8 / 12 |
| B-structured | 7 / 12 |
| uniform | 7 / 12 |
| A | 6 / 12 |
| SF | 4 / 12 |

- **No learned arm beats G+M.** Paired root-level discordance (learner wins / G+M wins): B-full 0 / 1, B-structured
  0 / 2, A 0 / 3, SF 0 / 5 (exact McNemar p = 1.0, 0.5, 0.25, 0.06).
- **No learned arm meaningfully beats uniform.** B-full 1 / 0, B-structured 2 / 2, A 2 / 3, SF 1 / 4.
- **G+M was minimal on all 7 roots that have a shortest known VERIFIED catalogue repair.** B-full used one extra move on
  2 of its 6 such successes.

**Verdicts.**
- `P8D_ENGINEERING_PASS`: 72 / 72 attempted or abstained; protocol audit PASS for every attempted, uncensored episode;
  rankings verified against their frozen hash; recorded arrays for every executed repair.
- `P8_PRIMARY_LEARNED_ADVANTAGE`: **NOT_SUPPORTED** (pilot scale, n = 12).
- `P8_GENERIC_COUPLING_VALUE`: **NOT_SUPPORTED** by the contract rule. The direction favours B-full (fresh accuracy
  +0.093, executed 2 / 1 discordant, p = 1.0), but the root-cluster intervals overlap and the oracle-revealed
  conditional advantage reversed on fresh roots (0026).

Previous turn sync: `b79ef14`.

## 1. Protocol (`p8d_run.py`, `p7_oneshot.py`, rankings from `p8c_train.py`)

**Rankings** were frozen before any test label was read; P8d checks them against `sha256:5d2f9238…`.
- *Learned arms* (seed-0 checkpoints): the P8c validation-chosen temperature and threshold; admitted candidates sorted by
  fewest moves, predicted J, analytic displacement, energy. The deterministic bounded-pool ranking was frozen in P8b, with
  no sampler.
- *U*: a seeded uniform order over the catalogue.
- *G+M*: pose-screen geometry ranking (§P8b), top 5.
- Arm order per root was a predeclared seeded permutation (round-robin interleaving).

**Episode** (`ordered.primary_v2`, own seed namespace per arm and root):
1. static check;
2. complete fixed-order 3R relocation planning in rank order under the declared allowance;
3. COMMIT of the first relocation witness;
4. executed and re-observed moves;
5. **one** target attempt with SAFE_RETREAT; no fallback after commit.

An empty admitted list is ABSTAIN. A guard hit is UNRESOLVED_CENSORED, counted as failure.

**Equal budgets.** Every arm had the same per-episode guard (180 CPU-s, 600 s wall), the same top-5 candidate limit and
the same declared relocation allowance. G+M's ranking uses only static screens; its motion search is the same
`primary_v2` planning as every other arm.

## 2. Results (12 roots; every original task is CERTIFIED_INFEASIBLE)

| arm | success | target failed after commit | censored | abstained | moves of successes | minimal (regret 0) / successes with known best | extra-move successes | mean J (successes) | mean J (all committed) | CPU-s total |
|---|---|---|---|---|---|---|---|---|---|---|
| **G+M** | **9** | 0 | 3 | 0 | 1–2 | **7 / 7** | 0 | 0.84 | 0.84 | 554.9 |
| B-full | 8 | 1 | 3 | 0 | 1–2 | 4 / 6 | 2 | 1.06 | 1.10 | 575.2 |
| B-structured | 7 | **5** (4 = empty repair) | 0 | 0 | 1–2 | 4 / 5 | 1 | 0.83 | 0.57 | 79.5 |
| U | 7 | 3 | 2 | 0 | 1–3 | 2 / 6 | 4 | 1.18 | 1.07 | 415.2 |
| A | 6 | 2 (1 = empty repair) | 3 | 1 | 1–2 | 4 / 4 | 0 | 0.74 | 0.66 | 592.2 |
| SF | 4 | 1 | 0 | **7** | 1 | 2 / 2 | 0 | 0.72 | 0.78 | 28.0 |

- **Restricted-catalogue minimality.** "Known best" is the fewest moves among VERIFIED teacher-catalogue repairs of that
  sealed root; only 7 of 12 test roots have one. Some arms succeeded on roots without one: their independent episodes
  found repairs the teacher catalogue never verified, under its own caps. No global minimum is claimed.
- **False-feasible empty repairs.** B-structured committed the empty repair on 4 certified-infeasible roots, and A on 1.
  These are classifier false positives at their validation-chosen thresholds.
- **Hard roots.** p8_2026102506, 2517 and 2523 censored the planner-heavy arms at 180 CPU-s; no arm succeeded on 2506,
  2517 or 2523.

**Paired comparisons** (root-cluster bootstrap 95 % CI of the success difference; exact McNemar on discordant pairs):

| comparison | learner-only wins / baseline-only wins | difference | 95 % CI | p |
|---|---|---|---|---|
| B-full vs G+M | 0 / 1 | −0.083 | [−0.25, 0.00] | 1.0 |
| B-full vs U | 1 / 0 | +0.083 | [0.00, +0.25] | 1.0 |
| B-structured vs G+M | 0 / 2 | −0.167 | [−0.42, 0.00] | 0.5 |
| A vs G+M | 0 / 3 | −0.250 | [−0.50, 0.00] | 0.25 |
| SF vs G+M | 0 / 5 | −0.417 | [−0.75, −0.17] | 0.06 |
| B-full vs B-structured | 2 / 1 | +0.083 | — | 1.0 |

With n = 12 these are **pilot-level** comparisons; none is significant at 0.05.

## 3. What this means

- **Simplest strong method.** The non-learned geometry + full-motion baseline is the strongest planner on fresh roots: most
  successes, fully minimal within the catalogue, no target failure after commit.
  - Caveat: its pose screens are the same family that *constructed* these roots (constructor alignment, reported since
    P8b). Its failures are the three planner-heavy roots where every arm failed.
- **B-full** is the best learned arm (8 / 12, no false empty repair) but adds no measurable executed value over G+M or U,
  and uses more moves and travel than G+M.
- **Factorized and structured arms** fail through calibration and thresholding (SF abstains 7 / 12; B-structured
  commits 4 infeasible empty repairs), not through motion.

## 4. Support matrix (all of P8)

| hypothesis | verdict | measured basis |
|---|---|---|
| H-coupling (conditional) | **NOT_SUPPORTED** | P8a historical: B-quadratic best, B-full's higher-order term breaks conditionals (zAB NLL 1.45 / 1.71 vs 0.02 / 0.09). Fresh P8c test: B-structured best on tasks a / b (0.56 / 0.67 vs B-full 0.95 / 1.03). |
| H-interaction (unconditional κ) | **INCONCLUSIVE** (positive direction) | P8a 6/6 seed pairs B-full < B-structured κ MAE; fresh test: only coupled arms predict +1 (0.67 vs ≤ 0.17), but κ test roots 2 / 3 / 2 and every +1 label is operational. |
| H-repair-success | **NOT_SUPPORTED** | P8d: G+M 9 / 12 ≥ every learned arm; best learned B-full 8 / 12, 0 / 1 discordant vs G+M, 1 / 0 vs U. |
| H-minimality-within-catalogue | **INCONCLUSIVE** | Defined on only 7 / 12 test roots. G+M minimal 7 / 7; B-full 4 / 6; U 2 / 6. No claim outside the declared catalogue. |
| H-vision | **BLOCKED** | Not in P8 scope: every arm consumes the symbolic scene state; no image input was trained or tested. |
| H-sampler | **NOT_SUPPORTED** (at bounded runtime) | P8b: exact detailed balance, but TV 0.20–0.21 at 4k steps on a 356-state pool; deterministic scoring of the same pool < 3 CPU-s. |
| H-geometry-baseline (G+M is a strong baseline) | **SUPPORTED** (pilot, with constructor-alignment caveat) | P8b offline 7 / 6; P8d 9 / 12, minimal 7 / 7, 0 target failures after commit. |

## 5. Artifacts and accounting

- **Evidence:** `runs/p8/execution/<arm>__<root>/{job.json, result.json, relocation.npz, target_witness.npz}` and
  `ledger.json`; rankings `runs/p8/c_training/rankings.json`.
- **Figures:** `visualizations/p8/ABC_S_GM_oneshot.gif` (all six arms side by side per root, recorded arrays only;
  "NO TRACE" panels for abstained, censored and certified outcomes), `visualizations/p8/P8_paired_success.png`.
- **Compute:** P8d 2,245.1 / 12,000 CPU-s; figures (all stages) 197.7 CPU-s; final full suite **323 / 323 passed**,
  530.8 / 1,200 CPU-s, guarded (`runs/p8/final_tests`).
