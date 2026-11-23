# P2 pre-registration: K ≤ 2 original-root set search (frozen before EVAL predictions and before any physical outcome)

Branch `naren/rss27-mcts-sets-klt3`. This file is committed together with `P2_FROZEN_PARAMS.json` and `P2_TUNING.json` **before**:
- `run.py eval` (the EVAL predictions);
- `run.py live` (the live timing subset);
- any teacher query.

Changes after this commit are dated amendments only.

## Frozen inputs

| Item | Value |
|---|---|
| Models | V3.4 bundle `~/abf_v34/approach_b_bundle` (MANIFEST sha in `P0_FROZEN_PROTOCOL.json`): sampler `a01f25eb…` (TaskCVAE scratch_all s0), scorer s0 `0fa126da…`, scalers `884b3567…` |
| Proposals | `exhaustive.proposals`: S1, 64 draws, top-6, CUDA generator seed 0 → **top-4 per eligible object**. One batched S0 pass per root; identical for every arm |
| Planner horizon | public **K_max = 2** for every root |
| Selection | `noop_gate 0.5, eta 0.3, alpha = beta = gamma = 0` (frozen `xy.choose` semantics, implemented in `search_sets.choose`; parity-tested against `xy.choose` and `exhaustive.Selectors`) |
| Search reward | max p11 over a set's orders (guidance only). The final commitment uses the gated selector over every fully scored ordered candidate plus the no-op |
| Budget accounting | unique ordered X/Y evaluations **including the no-op**. A set is scored with all of its orders or not at all |
| Hyperparameters (DEV-tuned; `P2_TUNING.json`) | UCT_SET c = 0.1; PW_UCT_SET c = 0.3, pw (k, α) = (2.0, 0.5); BEAM_SET w = 16; RAND_SET none |

The tuning criterion was fixed in code before the pilot: mean agreement with EXACT_K2's committed decision over B ∈ {16, 64, 256, 1024} and seeds, ties broken by best-reward regret, then grid order. It used model outputs only, on the 151 K-blind DEV roots.

## Cohort

- **Roots:** the VAL 2D public split (751 roots). The planner runs on all of them, K-blind. DEV (151 roots) was used only for tuning. **EVAL = 600 roots.**
- **Primary (evaluator-side):** EVAL roots with K ∈ {1, 2}, i.e. 96 + 95 = 191 roots.
- **Safeguards:** EVAL K0 (147 roots, correct = NOOP) and NONE (128 roots, correct = ABSTAIN).
- **Excluded:** K3 (134 EVAL roots), from all primary analyses.

## Arms and budgets

- **Model-only (all EVAL roots):** EXACT_K2; RAND_SET, BEAM_SET, UCT_SET and PW_UCT_SET at B ∈ {16, 64, 256, 1024}, with seeds {0, 1, 2} (BEAM is deterministic: seed 0).
- **Replay:** each root's K ≤ 2 table is scored once, and every arm reads it through the budgeted Oracle (identical charges).
- **Live timing:** a predeclared subset of ≤ 30 EVAL roots with `sha256('MCTS_LIVE|' + root_id) % 20 == 0` is run with live scorer calls (all arms, all budgets, seed 0). It reports wall time, and the decision mismatch count of live vs replay.

## Physical verification (P3)

**Primary arms:** EXACT_K2, UCT_SET@256, PW_UCT_SET@256, BEAM_SET@256 and RAND_SET@256, all seed 0. **Secondary (only if the cap allows):** the same four search arms at B = 64.

**Manifest:**
- Unique (root, ordered sequence) for every REPAIR decision of these arms on primary EVAL roots (K1/K2).
- Minus any sequence already labelled in the K≤3 ablation or post-ablation caches (same teacher contract; the labelled status must be decided, otherwise the sequence is re-queued).
- NOOP and ABSTAIN need no query. A REPAIR on a K0 or NONE root is incorrect by mask, with no query.

**Caps:**
- ≤ **1,200 new** complete-sequence teacher queries.
- ≤ **24 cumulative teacher CPU-hours** (sum of the teacher's `cpu_s`).
- gvlab2, ≤ 40 workers (≥ 5 CPUs left free), idle compute only. No 3D query and no retry. UNKNOWN and WORKER_ERROR are kept as such.

**If the primary manifest exceeds 1,200:** whole primary roots are taken in `sha256('MCTS_P3|' + root_id)` order until the cap is reached, so every included root has every primary arm verified (paired). Partial coverage is reported. The secondary B = 64 set is added only with the remaining cap, by the same root order. If the CPU cap is reached mid-run, verification stops and the uncovered roots are reported as `NOT_VERIFIED_CAP`.

## Metrics

- **Primary:** verified task success (`v32b_phys.outcome == SUCCESS`) on K1, K2 and pooled K1+K2 EVAL roots, per arm, at B = 256. UNKNOWN is excluded from the task denominator and reported separately (`benchmark.correct`).
- **Safeguards:** K0 correct NOOP; NONE correct ABSTAIN.
- **Uncertainty:** paired root-level differences vs EXACT_K2, BEAM_SET and RAND_SET, with 95 % percentile bootstrap (2,000 resamples, seed 0, resampling `evaluation_group_id` = root).
- **Secondary:** model-only agreement and regret vs EXACT_K2; unique scored sequences; sets; iterations; stops; replay and live wall times; FAIL_X / FAIL_Y; coverage.

## Decision rule for UCT_SET@256 (registered now)

- **(a) Noninferiority:** the lower 95 % bound of the paired pooled K1+K2 success difference (UCT − EXACT_K2) is ≥ −5 pp.
- **(b) Efficiency:** median unique scored sequences ≤ 25 % of EXACT_K2's median on the same roots.
- **(c) Added value:** the paired difference UCT − BEAM_SET has lower 95 % bound > 0, **and** UCT − RAND_SET has lower bound > 0.

**Classes:**

| Class | Condition |
|---|---|
| **USEFUL** | (a) and (b) and (c) |
| **NONINFERIOR_NOT_BETTER_THAN_SIMPLER** | (a) and (b), but not (c) |
| **WORSE** | (a) fails, or UCT − BEAM or UCT − RAND has upper 95 % bound < 0 |
| **INCONCLUSIVE** | more than 20 % of the verified primary roots are UNKNOWN for any primary arm, or coverage < 50 % of primary roots |

PW_UCT_SET is classified the same way and reported separately. K1 and K2 are reported separately and described only; the decision uses the pooled result.

**Model-only results never support a task-success claim.**
