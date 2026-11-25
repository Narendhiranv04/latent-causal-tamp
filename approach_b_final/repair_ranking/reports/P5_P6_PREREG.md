# P5 and P6 pre-registration: pipeline choice and independent confirmation

Registered **before** the P4 finalist is selected and before any end-to-end result for a trained scorer has been seen. At this point only A0 (frozen) DEV predictions were running.

## P5: model-only matrix on DEV (cached exact-contract labels)

- **Scorers:** A0 (frozen) and the P4 finalist A*, if one exists.
- **Constructors:** EXACT4, EXACT6, BEAM_SEEDED4@1024, BEAM_FULL@1024 and PW_MCTS_SEEDED4@1024 (frozen `P2_FROZEN_PARAMS` of the completed study). BEAM_SEEDED4@256 and PW_MCTS_SEEDED4@256 are secondary budgets.
- **Shared settings:** cVAE, seed 0 and the frozen gate/admission rule. Every order of every set is scored.
- **Roots:** all 578 VAL roots with K ∈ {0, 1, 2, NONE}.
- **Outcomes:** historical strict outcome from cached labels. An uncached pick is UNKNOWN, never a failure.
- **Reported:** decided success, UNKNOWN, ITT bounds, paired cached deltas against A0+EXACT4, off-D4 verified successes and failures, and K0/NONE decisions.
- **Timing:** synchronized live timing on 30 predeclared CONFIRM-independent DEV roots (first 30 in `XYRR_P5` hash order) for every A* arm.

**P2 had no finalist,** so no F* arm exists. The F5 ensemble is not carried forward.

## Choosing the primary revised pipeline (deterministic; DEV_CAL decides, DEV_AUDIT can veto)

1. **If P4 produced no A*:** no revised pipeline qualifies. **No CONFIRM queries are spent**, and the result is a negative, development-only decision.
2. **Default primary:** **A* + EXACT4**.
3. **When an expanded constructor replaces it.** A* + C, for C ∈ {BEAM_SEEDED4@1024, BEAM_FULL@1024, PW_MCTS_SEEDED4@1024}, replaces A* + EXACT4 only if all of the following hold:
   - On DEV_CAL, its paired cached comparison against A* + EXACT4 has wins − losses ≥ 3.
   - Its UNKNOWN count is no more than 10 % of K1/K2 roots above A* + EXACT4's.
   - On DEV_AUDIT, wins − losses ≥ 0.
   - Median live latency is ≤ 1.0 s.

   If several qualify, the one with the largest DEV_CAL wins − losses is chosen, then the cheapest.
4. **Secondary arms (at most 2, mechanistic):**
   - If the primary is A* + EXACT4: A* + PW_MCTS_SEEDED4@1024 and A* + BEAM_SEEDED4@1024.
   - If the primary is expanded: A* + EXACT4 and the other staged constructor.
5. **A0 + EXACT4 is the reference arm** on every CONFIRM root.

## P6: CONFIRM cohort and protocol

- **Cohort:** `~/xyrr_private/confirm/PRIVATE_INDEX.jsonl` (sha256 `e3643a64…`).
  - 207 fresh roots from the V3.4 generation runs that were never admitted and never inferred: K1 61, K2 23, K0 114, NONE 9.
  - Disjointness checks are listed in `P0_CONFIRM_POOL.json`.
  - Public rows (sha256 `de654c81…`) were built with `benchmark.public`.
  - **No root is selected by model output.**
- **Planner inputs:** public rows only, and K_max = 2 for every root.
- **Predictions:** for all arms, sealed with `benchmark.seal` and committed and pushed **before** any teacher call.
- **Queries:**
  - One committed plan per root per arm. Identical ordered choices across arms are deduplicated.
  - No retries and no fallback.
  - Unchanged teacher (`benchmark.teach`, the k3abl env on gvlab2).
  - Charged to the validation allocation (≤ 1,200; CONFIRM ≤ 1,000, with 200 kept for optional DEV). Expected ≤ 4 arms × 207 roots, much lower after deduplication.
- **Primary contrast:** primary pipeline − A0 + EXACT4.
  - Historical strict outcome (FAIL_Y if Y = 0; SUCCESS if X = Y = 1; FAIL_X if Y = 1 and X = 0; else UNKNOWN), on K1 + K2 roots where both arms are decided.
  - 95 % paired cluster bootstrap over `parent_family_id`, 4,000 resamples, seed 0.
  - Also reported: decided pairs, wins/losses, per-arm denominators, operational (`v32b_phys`) all-root success, ITT bounds, logical-conjunction sensitivity, K1 and K2 separately (exploratory; K2 n = 23), K0 NOOP and NONE ABSTAIN, UNKNOWN by factor, and latency.

## Decision labels (adopted now)

- **SCORER_IMPROVED_CONFIRM** requires all of:
  - Primary strict lower bound > 0.
  - UNKNOWN ≤ 20 % for both primary arms.
  - Safeguard point changes no worse than −3 pp.
  - Median latency ≤ 1.0 s.

  Whether the point gain is ≥ 5 pp is also reported.
- **SCORER_IMPROVED_DEV_ONLY:** P4/P5 DEV gains, but the CONFIRM interval includes 0.
- **EXPANSION_HELPFUL_WITH_NEW_SCORER:** A* + expanded − A* + EXACT4 has a lower bound > 0. This is secondary, with a multiplicity caveat.
- **MCTS_ADDED_VALUE:** **untested formally.** It would need staged MCTS to beat both staged and unstaged beam with the same scorer, and the two-secondary cap leaves no room. A* + PW_MCTS_SEEDED4 vs A* + BEAM_SEEDED4 is reported descriptively.
- **NO_ESTABLISHED_IMPROVEMENT:** the interval crosses 0 or a guard fails.
  - **INCONCLUSIVE** if UNKNOWN > 20 %.
  - **HARMFUL** if the upper bound < 0.
- **Released method:** EXACT4 with A0 stays the released method unless SCORER_IMPROVED_CONFIRM holds.

## Power caveat

The cohort is small: 84 K1/K2 roots, below the plan's target of 80 each. Small paired differences will likely stay inconclusive, and the result is labelled underpowered. No extra queries or roots are added after labels are seen.
