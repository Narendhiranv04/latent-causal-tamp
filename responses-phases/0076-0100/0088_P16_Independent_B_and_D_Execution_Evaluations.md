# 0088 — P16: independent prospective evaluations of B and D

**Data.** `runs/p16/eval/B_TEST.json` and `D_TEST.json`, from the sealed outputs (manifest `9389d34`, unsealed after the on-origin check).

**Common to both tracks:**
- every executed choice and plan is certified by the same deterministic certifier and independently replayed;
- root-level exact two-sided sign tests and root-bootstrap CIs; Holm across each secondary family;
- zero discordance is reported as UNDERPOWERED, never as equivalence.

## Part I — B: choosing a complete ordered repair, including "do nothing"

**Cohort.** 135 B roots covered of 144 (NAT 118 / 120; mechanism 17 / 24). Of these, **112** have an original decided by the certifier: **72 feasible** (≥ 60 required) and 40 infeasible. The other 23 are UNKNOWN and excluded from the endpoints.

### I.1 Decisions per arm (frozen, calibrated no-op-first rule; ensemble of 3 seeds)

| arm | correct no-op / 72 | unnecessary relocation / 72 | repair verified / 40 | wrong no-op / 40 | abstain (feasible / infeasible) | strict TOP1 / 112 |
|---|---|---|---|---|---|---|
| **LB** (lean B) | **32** | 40 | 25 | 4 | 0 / 0 | 0.509 |
| **LB+G** (lean B + generic-only coupling) | **47** | 25 | **26** | 4 | 0 / 0 | **0.652** |
| LC (lean, GRU order) | 40 | 32 | 24 | 4 | 0 / 0 | 0.571 |
| LB-F2 (lean, order-invariant) | 38 | 34 | 22 | 4 | 0 / 0 | 0.536 |
| A (retrained) | 31 | 41 | 24 | 4 | 0 / 0 | 0.491 |
| P13:K-B (frozen full keyed B) | **7** | 64 | 24 | 2 | 1 / 2 | 0.277 |
| P13:A | 37 | 35 | 24 | 4 | 0 / 0 | 0.545 |
| P13:SF | 34 | 38 | 22 | 4 | 0 / 0 | 0.500 |
| P13:K-C | 27 | 45 | 24 | 4 | 0 / 0 | 0.455 |
| P13:B-F2 | 22 | 49 | 14 | 4 | 1 / 13 | 0.321 |
| geometry selector | 2 | 64 | 20 | 0 | 6 / 7 | 0.196 |
| random catalogue choice | 4 | 68 | 20 | 5 | 0 / 0 | 0.214 |
| **always EMPTY** | 72 | 0 | 0 | 40 | 0 / 0 | **0.643** |

Repairs on co-solved infeasible roots are short in every arm: 1.32–1.50 moves, 2.45–2.80 joint travel.

### I.2 Pre-registered tests

**H-B1 (primary): correct no-op on decided feasible originals, LB vs P13:K-B.**
- 32 vs 7 of 72; 25 / 0 discordant; **p = 6.0e-8**; +34.7 pp [+23.6, +45.8].
- Clears the +15 pp minimum effect. **SUPPORTED.**

**Guard (pre-registered, reported, not tested).** Repair success on decided infeasible originals is 25 vs 24 of 40 (3 / 2 discordant), CI [−7.5, +12.5] pp. The lower bound is above −10 pp. **Non-inferior.**

**Secondary, strict TOP1, LB vs each arm (Holm-adjusted p):**

| comparison | wins / losses | diff | 95 % CI | Holm p |
|---|---|---|---|---|
| **LB+G** | 0 / 16 | −0.143 | [−0.214, −0.080] | **0.0003** (LB+G better) |
| P13:K-B | 28 / 2 | +0.232 | [+0.152, +0.321] | **< 1e-4** |
| P13:B-F2 | 29 / 8 | +0.188 | [+0.089, +0.286] | **0.0068** |
| geometry | 39 / 4 | +0.313 | — | **< 1e-4** |
| random | 39 / 6 | +0.295 | — | **< 1e-4** |
| LC | 1 / 8 | −0.063 | — | 0.31 (unadjusted 0.039) |
| A, LB-F2, P13:A, P13:SF, P13:K-C | — | −0.036 … +0.054 | — | ≥ 0.88 |
| always EMPTY | 25 / 40 | −0.134 | [−0.268, +0.009] | 0.57 |

### I.3 Readings and limits

- **The P15 no-op defect is fixed relative to the frozen K-B** (7 → 32 of 72). Attribution:
  - the comparison changes *both* the training distribution (new mixed scene-only data with 29 + 6 feasible originals) and the architecture (lean vs full);
  - no full K-B was retrained on the new data, so **the gain cannot be attributed to removing F3 / F4 / F5**;
  - every learned arm discriminates feasible from infeasible originals about equally (AUROC of P(empty) 0.855–0.891); LB's mean P(empty) on feasible originals is 0.707 vs 0.633 for K-B;
  - the gain is mostly calibration of the no-op unary under the same calibrated rule, not new discrimination.
- **Generic-only coupling (H-B2) is new positive evidence.** With F3 / F4 / HO absent on both sides, matched data and 3 seeds, adding only `cpl` raised correct no-ops 32 → 47 and strict TOP1 0.509 → 0.652 (16 / 0 discordant, Holm p = 0.0003). It also gave the best validation NLL in every seed.
  - **Limit:** this does not reverse the P13 verdict on *combined* F5 (generic + HO), which stays rejected.
  - It **qualifies** the untested generic-only hypothesis as SUPPORTED on this cohort, an independent prospective test with 72 feasible originals.
  - Replication on a second cohort is required before it becomes a default.
- **Order sensitivity on test:**
  - LB-F2 vs LB is not significant (Holm 1.0);
  - the GRU variant LC is numerically better than LB's prefix form (not significant after Holm);
  - the validation-NLL advantage of order sensitivity (0085) did **not** turn into a test decision advantage. P13's F2 verdict stays (order matters for order queries), but it is not re-confirmed on this NAT-heavy decision endpoint.
- **The strongest negative: no learned arm beats "always do nothing" on strict TOP1.**
  - always EMPTY scores 0.643 overall and 0.76 on NAT; LB+G scores 0.652 and 0.60.
  - Learned B earns its keep only on infeasible originals (25–26 of 40 repaired vs 0).
  - On a feasible-heavy natural mix it still relocates unnecessarily on 25–40 of 72 feasible scenes.
  - A deployable B therefore needs a stronger no-op gate. This is the next blocking experiment.
- **Mechanism roots** (17 covered): every learned arm repairs PR_SIDES, PC_SG, PN_GIMP, ORD_CHAIN, OMIT_OPT and TRI_OR roots at 1.0, and PN_SIMP at 0.33–0.67. There are too few for inference.

## Part II — D: learned blocker diagnosis inside the non-learned rearrangement search

**Cohort.** **21 of 48** D roots were covered before the `execution` cap. DENSE 4 / 24 (3 of the 4 are feasible originals), and 17 mechanism roots. The oracle guide was **NOT_RUN** (no post-unseal budget).

### II.1 End-to-end search (identical scene-only movers, slots, index, budgets, certifier; shared exact cache)

| guide | solved (replay CLEAR) | motion checks / root | online / goal / transit plans | nodes | virtual CPU / root (incl. D) | D calls / D CPU | min-moves proven | + min-travel |
|---|---|---|---|---|---|---|---|---|
| **Dp16** (P16 pairless, feasibility-only recursion) | 21 | 117.0 | 4.8 / 7.0 / 3.4 | 25.8 | 170.3 | 13.6 / 2.09 s | 15 | 7 |
| Dp16-norec | 21 | 117.0 | 4.8 / 7.0 / 3.4 | 25.8 | 168.8 | 4.9 / 0.72 s | 15 | 7 |
| Dp (frozen P13 pairless) | 21 | 109.7 | 4.8 / 7.7 / 3.4 | 24.5 | 173.9 | 12.2 / 1.79 s | 15 | 5 |
| D (frozen P13 paired) | 21 | 104.9 | 4.8 / 7.3 / 3.3 | 24.1 | 157.5 | 12.0 / 1.74 s | 15 | 6 |
| **geometry** | 21 | 115.0 | 4.8 / 7.0 / 3.4 | 25.3 | 169.3 | — | 15 | 7 |
| geometry-norec | 21 | 115.0 | 4.8 / 7.1 / 3.4 | 25.3 | 171.9 | — | 15 | 7 |
| uniform | 21 | 115.0 | 4.8 / 7.1 / 3.4 | 25.3 | 172.7 | — | 15 | 7 |

**H-D1 (primary), Dp16 vs geometry:** 21 vs 21; **0 discordant**, p = 1.0. **UNDERPOWERED.** Motion checks are +1.7 % against a pre-registered −20 %, so the effort criterion is **NEGATIVE**.
- Every secondary guide is also 0 / 0 vs geometry (Holm 1.0).
- Frozen paired D needs 8.8 % fewer motion checks, below the 20 % threshold.

**Plan quality:**
- moves 1.286 and travel 2.273 on all co-solved roots, identical for every guide;
- extra moves vs a proven optimum: **0 on 15 / 15** roots for every guide;
- repeat-move plans: 0;
- `moves_outside_original_blocker_union`: 0 on 16 plans and 2 on 1, the same for every guide; the lattice union is destination-scoped (0086 §2).

**Disagreement analysis.** The first expanded move differed from geometry's on **3 / 21** roots (OMIT_OPT 42000, ORD_CHAIN 43000, PR_SIDES 47002). On all three, both guides reached the same plan with the same motion-check count. Where order differed, budgets never bound first, so guidance had nothing to save.

### II.2 Diagnosis on the sealed test lattices (46 decided originals, 5 feasible, 16 defined masks)

| model | feasibility AUROC | Brier | feasible recall | infeasible recall | union-blocker F1 (gated) | exact | union ≠ necessary |
|---|---|---|---|---|---|---|---|
| frozen D | 0.912 | 0.079 | 0.60 | 0.878 | 0.981 | 0.938 | 3 / 16 |
| frozen Dp | 0.898 | 0.106 | 0.80 | 0.854 | 0.981 | 0.938 | 3 / 16 |
| **Dp16** | 0.805 | 0.163 | 0.80 | 0.756 | 0.981 | 0.938 | 3 / 16 |

**Test lattice types:** MINIMAL_SETS 16, **NO_CLEARING_SET_WITHIN_POOL 12** (masked in P16 training), INCOMPLETE 11, FEASIBLE_ORIGINAL 5, NON_MONOTONE 2, UNKNOWN 2.

### II.3 Readings and limits

- **Blocker diagnosis is accurate:** union F1 0.981 on 16 masks, the same for all three models. It **does not change search outcomes or effort** on the covered roots.
- **The corrected-label retrain (Dp16) did not improve feasibility discrimination.** Its AUROC was lower: 0.805 vs 0.898 frozen pairless, with 5 positives (wide uncertainty). The label correction is semantically necessary; its effect on performance is **not** shown to be positive.
- **The informative branch-heavy DENSE roots** (the physics-only pilot showed 2–10 verified first moves and 600–780 CPU-s searches) were mostly **not** covered. The D comparison therefore rests on cheap mechanism roots that every guide solves within 25 nodes.

## Verdicts (P16 prospective)

| claim | verdict |
|---|---|
| B fixes the feasible-original no-op defect vs frozen K-B | **SUPPORTED** (+34.7 pp, p = 6e-8; data and architecture confounded) |
| B keeps infeasible repair ability (guard) | non-inferior (CI lower bound −7.5 pp) |
| generic-only coupling helps lean B | **SUPPORTED on this cohort** (Holm p = 0.0003); replication required |
| order-sensitive vs order-invariant lean B on test decisions | **NOT SUPPORTED** (n.s.) |
| learned B beats "always do nothing" on strict TOP1 | **NEGATIVE** (0.509–0.652 vs 0.643) |
| D-guided search beats geometry | **UNDERPOWERED** (0 / 21 discordant; D coverage 21 / 48) |
| D reduces planner effort ≥ 20 % | **NEGATIVE** (+1.7 %) |
| corrected-label D improves diagnosis | **NOT SUPPORTED** (AUROC 0.805 vs 0.898; n = 5 positives) |
| oracle bound | **NOT_RUN** |
