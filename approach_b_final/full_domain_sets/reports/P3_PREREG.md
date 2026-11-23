# P3 pre-registration (committed before any EVAL prediction or teacher call)

## Authorization and cohort (owner decisions, 2026-11-23)

- **Teacher.** Physical verification is authorized:
  - at most **1,200 new 2D complete-sequence queries** and **24 physical-worker CPU-hours**;
  - on gvlab2, with 32 workers and 4–5 cores left free;
  - with the unchanged teacher (`benchmark.teach` → `evaluate._verify_job`, the K≤3 ablation harness);
  - with no retries and no second-choice plans; UNKNOWN stays UNKNOWN.
- **Cohort: VAL development-only pilot.**
  - These are the 600 EVAL roots of the K-blind split shared with the completed study. Tuning used only the 151 DEV roots.
  - These roots were examined before, including EXACT4's outcomes on them. The result is **development evidence**, not an independent test, and supports no generalization claim. No lineage-disjoint cohort could be generated within this study (`P0_GAPS.md`).

## Frozen planner

- **Parameters:** `P2_FROZEN_PARAMS.json`, chosen by the registered DEV criterion (`P2_TUNING.json`).
- **Grid edges:** `PW_MCTS_SEEDED4` took the smallest c (0.1) and the earliest unlock schedule (0.20, 0.40), both at the edge of their grids. This is disclosed and nothing is retuned.
- **Inputs:** the same public inputs, `K_max = 2` and frozen rule (`noop_gate = 0.5`, η = 0.3, α = β = γ = 0) for every root and arm.
- **Seeds:** every arm runs seeds 0, 1 and 2 at B ∈ {64, 256, 1024, 4096}, by offline replay of each root's full table; `EXACT4`, `EXACT6` and `EXACT_FULL` run once. **Physical picks are the seed-0 decisions.**
- **Seal:** the predictions file hashes and a gzipped seed-0 decision file are committed and pushed in the seal commit, before the manifest is executed.

## Physical arms and manifest

- **Primary tier:**
  - `EXACT4` (historical production anchor);
  - `EXACT6`;
  - `EXACT_FULL` (offline model-optimum reference: full-domain exhaustive scoring of about 239k sequences per root, about 10 s each; not a deployable candidate);
  - at **B = 1024**: `RAND_FULL`, `BEAM_SEEDED4`, `BEAM_FULL`, **`PW_MCTS_SEEDED4`** and `PW_MCTS_FULL`.
- **Secondary tier:** `PW_MCTS_UNIFORM` and `BEAM_FULL_UNIFORM` at 1024, plus the four BEAM/MCTS arms at 4096.
- **Queries:**
  - only sealed seed-0 **REPAIR** sequences on EVAL K1/K2 roots (evaluator-side strata), deduplicated against every exact-contract cache;
  - a cached UNKNOWN is **not** re-queried;
  - if the cap binds, whole roots are taken in sha256('FDS_P3|'+root) order, primary tier first, then secondary.
- **Safeguards:** K0 (NOOP) and NONE (ABSTAIN) are reported from the decisions, with no queries.

## Outcomes

- **Primary: strict.**
  - A value counts only under VERIFIED / CERTIFIED_* statuses.
  - SUCCESS means y = 1 and x = 1. FAIL_Y, FAIL_X, NOOP and ABSTAIN are decided failures on K1/K2 roots. UNKNOWN is unresolved and excluded from the paired comparisons.
  - Each arm also reports intention-to-treat bounds: UNKNOWN counted as all failures, and as all successes.
- **Secondary: operational.** The frozen `v32b_phys` rule, for parity with the completed study.
- **Statistics:**
  - paired, on K1+K2 pooled roots where both arms are decided, with K1 and K2 also reported separately;
  - a 95 % **lineage-cluster** bootstrap (generator `parent_family_id`, 584 families across 751 roots; 4,000 resamples, seed 0);
  - wins and losses with denominators.

## Registered contrasts and decision rules

The primary contrast **C1 = `PW_MCTS_SEEDED4@1024` − `EXACT4`** (strict) is pre-specified as the single primary test: the plan's primary hypothesis, and also the lowest-regret arm on DEV. Every other contrast is secondary and reported with Holm-adjusted interpretation; no other arm can be promoted after the fact.

Latency is the **live** median end-to-end time (uncached cVAE marginal plus search plus selection) on the predeclared live EVAL subset, on the same RTX 5060.

| Label | Rule |
|---|---|
| `EXPANSION_HELPFUL` (development-only) | lower bound of C1 > 0; strict UNKNOWN ≤ 20 % in both arms; `PW_MCTS_SEEDED4@1024` latency ≤ 1.0 s |
| `SEEDED_EXPANSION_HELPFUL` | lower bound of (`PW_MCTS_SEEDED4` − `PW_MCTS_FULL`) @1024 > 0, and seeded latency ≤ 1.25× full |
| `MCTS_ADDED_VALUE` | lower bounds of (`PW_MCTS_SEEDED4` − `BEAM_SEEDED4`) **and** (`PW_MCTS_SEEDED4` − `BEAM_FULL`) @1024 both > 0, and MCTS latency ≤ 1.25× the slower of the two beams. Otherwise, MCTS is not claimed to add value |
| `EXPANSION_HARMFUL` | upper bound of C1 < 0, **or** `PW_MCTS_SEEDED4@1024` latency > 1.0 s **and** > 10× `EXACT4` |
| `EXPANSION_NOT_ESTABLISHED` | none of the above. The sub-label `INCONCLUSIVE` applies if strict UNKNOWN exceeds 20 % in either C1 arm |

## Attribution (descriptive)

Attribution uses all known decided witnesses: the caches plus this study's new queries, and the generator labels. It is computed on the analysis side only.

| Category | Meaning |
|---|---|
| `SUCCESS_IN_D4` / `SUCCESS_OFF_D4` | the arm succeeded, with a committed set inside / outside the top-4 pool |
| `POOL_MISS` | exact arms only: a known witness exists, but none is inside the arm's pool |
| `TIER_LOCKED` | the witness tier was never unlocked within the budget |
| `RETRIEVAL_FAILURE` | the witness was eligible but never fully scored. Without per-node logs, *unlocked-not-expanded* and *expanded-not-scored* are merged here |
| `SCORER_RANKING_FAILURE` | a known successful set was scored but lost |
| `ORDER_SELECTION_FAILURE` | the committed set is a known witness in another order |
| `UNRESOLVED` | the outcome is UNKNOWN, or no witness is known |

## Not changed after this point

No parameter, prior, threshold, root selection or arm list changes after outcomes are seen. The completed study and its reports remain untouched.
