# P17 — complete 2D B and D: scientific decision

**Decision.** METHOD_B_2D_COMPLETE. METHOD_D_2D_COMPLETE not granted: D is **PARTIAL / BLOCKED on M7 only**. P17_2D_COMPLETE not granted. Neither learned method shows a prospective advantage over its strongest non-learned baseline. No 3D work.

## Implemented
- **Shared physics:**
  - corrected search with the last mover in the dominance key;
  - existential sequence verifier with scoped certificates;
  - finite-graph claim vocabulary;
  - independent replay;
  - finite library domain for scoped proofs.
- **Shared domain:** scene-only, 0–4 relocations, multiple slots, freed sources and repeats (`P17_DOMAIN_V1`).
- **B:**
  - lean B (production) and LB+G (generic coupling, experimental);
  - controls: LB-W, LB-F2, LC, A, SF, FULLB and the frozen P13 arms;
  - inference-only coupling toggle, swapped thresholds, TOP-3 verify-then-next, VERIFY_FIRST.
- **D:**
  - pairless Dp17 with multi-destination labels;
  - per-family calibration;
  - temporary-target lattices;
  - feasibility-only recursion, `-blk` experimental, and an oracle guide.
- **Custody:** pre-registration, then sealed execution, then a sealed manifest pushed before unsealing (`f22a444` → `b96870d`).

## Verified (tests, proofs, replays)
- **Search dominance:** 0 mismatches against the exhaustive reference.
- **Existential verifier:** 9 controlled physical counterexamples; 46 P16 q-dependent labels corrected.
- **Determinism:** 5 hash seeds × 3 roots, under load.
- **Exactness checks:**
  - LB exact factorization;
  - P(z0) invariant to the coupling;
  - the fast scorer equals the slow scorer to < 1e-12.
- **D checks:**
  - calibration isolation;
  - union ≠ necessary;
  - the NO_CLEARING mask is never 0;
  - multi-destination semantics.
- **Custody:** the manifest and unseal steps refuse an incomplete roster or a changed sealed file.
- **Mechanisms:** M0–M6, M8 (3 and 4 moves) and M9 each have a physically VERIFIED witness, replayed, with a counterfactual.
- **Replay coverage:** every prospective and retrospective D plan, and every B execution, was replayed.
- **Regression:** 45 P16 / P17 tests; historical regression and 6 replays in `runs/p17/regression_final/`.

## Empirically supported (prospective p17test unless stated)
- **Verify-first beats every learned B arm.**
  - It is the best repair-selection policy: strict TOP1 0.850 (75 / 75 no-op, 44 / 65 repairs).
  - It beats lean B 56 : 4 (Holm p = 1e-11) and costs about 13× more motion checks.
- **Learned B scores are informative, but the deployable no-op threshold is the weak link.**
  - Score quality: AUROC about 0.96–0.97, and z0 Brier 0.08–0.14 against 0.25 for a constant.
  - The no-op decision is what fails: on 51 calibration roots the thresholds transfer poorly.
- **Order awareness has a measurable effect.** All 7 certified reversed-order pairs are ranked correctly by the ordered arms, against 0.5 for order-invariant LB-F2.
- **The D original-target classifier is informative.**
  - Dp17 reaches AUROC 0.952 and blocker F1 0.89.
  - In the matched operational comparison it produces the fewest false alarms (6 / 27, against 11–17 / 27 for A–C).
- **Search resolves more blocked scenes than single-repair selection.** On the matched 90 roots, D resolves 43 / 63 and geometry-ordered search 40 / 63, against 22–29 / 63 for A–C.

## Negative
- **Lean B vs ALWAYS_EMPTY (primary):** 0.479 vs 0.536 (31 : 39, p = 0.40). On natural scenes it is worse than doing nothing (8 : 26, p = 0.003).
- **Generic coupling (LB+G):**
  - It does not replicate: 0.350 vs LB 0.479 (3 : 21, Holm p = 0.0025).
  - The deficit is a threshold failure, since the coupling leaves P(z0) unchanged.
  - The P16 +16 gain is not reproduced.
- **Lean B is beaten by its own controls:** LC (1 : 26), FULLB (7 : 23) and order-invariant LB-F2 (13 : 31).
- **Learned D guidance vs geometric ordering:** no advantage.
  - Retrospective 39 vs 38 / 48; prospective 70 vs 67 / 90.
  - The no-recursion orderings are as good or better (71 / 90).
- **Oracle blocker knowledge does not improve search:** 48 / 56 prospective, 27 / 33 retrospective.

## Unresolved
- **M7 repeat necessity.** No finite-domain proof on 8 named roots (0093 §2, 0099 §3).
- **Temporary-target blocker marginals.** Only 6 masks, so not validated.
- **Power.** D contrasts are UNDERPOWERED (≤ 6 discordant roots each).
- **Budget censoring.** It affects D (19–24 / 90) and 34 / 174 prospective originals.
