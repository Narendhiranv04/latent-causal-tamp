# P12 — 2D scientific decision (independent generalization and joint-factor validation)

**Overall status: PARTIAL** (engineering PASS; execution covers 49 / 80 roots under the 12,000 CPU-s cap).
- The lock held: prereg and frozen predictions were pushed in `caa49df` before any label, and labels were hash-committed in `a2d7833` before unsealing.
- On two new, independently constructed 2D families, **the P10 advantages of keyed B do not generalize**, and **F3 / F5 are not confirmed**: F3 is significantly reversed on the preregistered cohort.

**Stage gates:**

| stage | gate |
|---|---|
| P12-0 audit and prereg draft | PASS |
| P12-1 constructors (dev) | PASS (scientific limitation: dev κ all 0) |
| P12-2 lock and frozen predictions | PASS |
| P12-3 physical adjudication | PASS (80 / 80 roots, 65 proof-grounded four-tuples) |
| P12-4 factor tests | PASS (engineering); F3 / F5 NOT_CONFIRMED |
| P12-5 executed TOP1 | **PARTIAL** (49 / 80 roots) |
| P12-6 appearance and D | PASS |
| P12-7 regression | PASS: 407 / 407 tests + 6 / 6 replays (627.7 CPU-s; 681 fixture planner calls counted separately) + 6 / 6 new P12 tests |

## Verdict per scientific question

| # | question | verdict | key numbers |
|---|---|---|---|
| Q1 | Can independent, physics-first difficult 2D families be constructed without model or outcome selection? | **PASS** (with limitation) | X_SWEEP_GATE 40 / 198 accepted (20.2 %), Y_BOTTLENECK 40 / 578 (6.9 %); 776 attempts ledgered; 0 fingerprint overlap with P10b. Limitation: originals are hard, but repairs are mostly 1-move (64 / 80); no 4-move witness; no random-unfiltered stratum. |
| Q2 | ≥ 24 proof-grounded four-tuples? | **PASS** | 65 (κ = 0: 59, +1: 4, −1: 2) |
| Q3 | **Primary F3:** does full B beat B-F3 on κ error? | **FAILED** (significant reversal) | Δ −0.0735 [−0.112, −0.032]; 21 / 44 roots (0 ties); raw p 0.0059; **Holm p 0.0118** |
| Q3b | F3 on complementary (κ = +1) H1-like four-tuples | **UNDERPOWERED** | 4 roots (target ≥ 12); B 0.81 < B-F3 0.94 (descriptive) |
| Q4 | **Primary F5:** does full B beat B-F5s? | **FAILED to confirm** (null) | Δ −0.027 [−0.109, 0.058]; 30 / 35; **Holm p 0.62**; family-heterogeneous (X +0.175, Y −0.170) |
| Q5 | Is κ prediction absolutely adequate? | **FAILED** | mean \|κ̂ − κ\|: SF 0.219 (best), B 0.404, A 0.421; B creates spurious interaction on κ = 0 (0.377 vs SF 0.179) |
| Q6 | Does B's strict TOP1 executed advantage generalize? | **FAILED** | 49 roots: B 0.633, A 0.626, SF 0.565, C 0.558; B − A +0.007 [−0.068, 0.082]; B − SF +0.068 [−0.007, 0.143] p 0.38; geometry 0.796 beats B: −0.163 [−0.265, −0.054], p 0.0015 |
| Q7 | Learned vs planner-assisted G+M (separate protocol) | **PARTIAL** (descriptive) | G+M 0.571 (X 0.20, Y 0.958); B − G+M +0.061 n.s.; protocols differ, so no ranking claim |
| Q8 | Order factor necessary / best order chooser | **PASS** for necessity, **FAILED** for B best | B − F2 +0.458 (18 / 0 roots); A 0.983 > B 0.916 (p 0.003); C − B margin +0.075 (p 0.031, exploratory) |
| Q9 | Omission necessity | **FAILED** (weak for all arms) | 1,470 omissions on 76 roots; arms at 0.56–0.69; B − SF −0.003 n.s. |
| Q10 | Realistic appearance robustness (masks fixed) | **PASS** (conditional) | B TOP1 changed 3.7 % / 10.7 % / 9.0 % (G1 / G2 / G3) vs 77 % severe; segmentation is not tested |
| Q11 | D initial feasibility on new families | **NOT_EVALUABLE** (0 feasible originals) | false-feasible: D 3 / 80, D-pairless 3, B 1, C 1, A 4, SF 7 |
| Q12 | D blocker identity (infeasible-only) | **FAILED** vs geometry | holdout: geometry 0.850 > D 0.752 > D-pairless 0.598; proof-grounded: geometry 0.855, D 0.757; D − geometry −0.098 [−0.172, −0.026] |
| Q13 | D pair term | **PARTIAL** (exploratory positive) | holdout D − pairless +0.154 [0.103, 0.209]; on P10b −0.011 [−0.051, 0.039] |
| Q14 | Matched A / B / C / SF blocker attribution | **PARTIAL** | P10b 33 matched (D 0.939, geometry 0.929, D-pairless 0.919, C 0.882, B 0.872, SF 0.855, A 0.842); holdout **UNSUPPORTED** (0 matched, 64 pool-3 roots); no-predicted-clearing-set A 7, SF 2 |
| Q15 | 3- / 4-move length on new families | **UNTESTED** | min-verified-repair length 1 / 2 / 3 on 64 / 11 / 1 roots; no 4-move witness |

## Claims

- **Supported:**
  - P10b-benchmark superiority of keyed B in strict TOP1 (P10 / P11; benchmark only);
  - F2 order necessity;
  - DINOv2 benefit (B-V0 +0.269 κ error);
  - mild-photometric stability with fixed masks.
- **Negative (failed):**
  - generalization of B's TOP1 advantage;
  - F3 on the preregistered cohort (reversed);
  - F5s;
  - HO residual (B-F5q better by 0.132);
  - B best order chooser;
  - D blocker identity over geometry;
  - absolute κ calibration.
- **Unresolved:**
  - F3 / F5 on complementary κ = +1 scenes (4 roots);
  - G+M vs learned (protocol mismatch);
  - D feasibility on new families (no feasible originals);
  - matched attribution on 3-object pools.
- **Untested:**
  - multi-move length on new families;
  - segmentation-level appearance;
  - 3D and hardware.

## Next decision (truthful)

The 2D programme reaches a negative-generalization conclusion for the joint factors and for keyed B's selection advantage. Two follow-ups would add evidence without redesign:
1. a dedicated κ = +1 constructor (prescreen on both single edits being certified-infeasible), to answer Q3b with ≥ 12 roots;
2. an execution continuation for the remaining 31 roots (about 7.5k CPU-s at the observed rate).

The record does not justify a 3D port of the joint factors. Per the contract, no 3D work or redesign was started.

**Commit:** P12 artifacts are pushed to `origin/main`; the final SHA is in the chat reply.
