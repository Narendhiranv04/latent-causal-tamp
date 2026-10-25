# 0066 — P13-7: factor-by-factor scientific verdict (2D)

**Status: PARTIAL.** Engineering passes, and each factor below has a graded verdict. The confirmatory evidence is mechanism-conditioned, and the natural-mix evidence is small.

**Commits:**
- start `021cd00`;
- P13-0 `719493e`;
- P13-1 `efc6854`;
- P13-2 + PREREG `a551db6`;
- plans + dedup `ac6b4e3`;
- **freeze `c975629`** (before any blind label);
- **label hash `4da8ca2`** (before unsealing);
- final SHA in the chat reply.

**The four evidence grades:**
- **Implemented:** the mathematics and code path are verified.
- **Learnable:** the factor's function is learned above controls on held-out roots.
- **Incrementally useful:** matched, preregistered removal hurts its own endpoint, with Holm correction, at or above the practical threshold, and without natural-mix harm.
- **Deployment useful:** strict-TOP1 executed success improves.

None of these grades implies the next.

## 1. Factor dashboard

**Δ** = full keyed B minus the factor-off arm; positive means the factor helps. "pm" means parameter-matched. The challenge set has 62 four-tuples, 34 order roots, 60 omission roots and 21 triple lattices; the natural mix has 29, 2, 32 and 0. Execution covers 129 roots (81 challenge, 48 natural).

| component | implemented (0060) | physical activation evidence (blind) | targeted effect (challenge) | natural / neutral effect | executed success Δ | verdict |
|---|---|---|---|---|---|---|
| **F1 learned static** | yes; gradient 0.017; only TOP1 path is the 4th key | 676 analytic checks (338 invalid); veto fired 0; 4th key reached 0 | AUROC 0.535 (off 0.503): discrimination at chance; log-loss +3.93 (calibration only) | same | not applicable (path never reached) | **NOT_IDENTIFIED / NO_BENEFIT** |
| **F2 order** | yes; B-F2 removes predecessor + prefix encoding (−98,816 params) | 39 proof-grounded reversed-order pairs on 34 roots | order accuracy **+0.779** [0.65, 0.90], 28 / 0, Holm 3e-8 | natural: 2 roots (n.s.) | **+0.421** [0.34, 0.50]; natural +0.222; reversed-order roots +0.679 | **SUPPORTED_CONDITIONAL** (but A / C orders are equally perfect: *some* order representation is needed, not B's specific module) |
| **F3 z₀–z_S scene pair** | yes; exact isolation | 62 four-tuples (κ +1: 33, 0: 17, −1: 12); 21 lattices | joint log-loss **−0.023** [−0.064, 0.015], Holm 0.030 (reversal); triple joint −0.062 | natural −0.07 (n.s.); κ = 0 false interaction: no difference | +0.026 (n.s.); challenge +0.078; natural −0.062 (n.s.) | **HARMFUL (statistically), practically negligible**; replicates P12 |
| **F4 omission pair** | yes; exact isolation | 262 proof-grounded omissions (82 necessary, 180 optional) | omission log-loss +0.014 [0.005, 0.025], Holm 0.005, below the 0.05 threshold | natural **−0.61** (B worse) | **+0.209** [0.17, 0.26]; natural +0.111 | **NO_DEMONSTRATED_PREDICTIVE_BENEFIT; deployment-useful** (largely via fewer abstentions) |
| **F5s generic coupling (+HO)** | yes; exact isolation (−131,971 params; pm control) | 62 four-tuples; 21 lattices | joint log-loss **+0.175** [0.115, 0.245], Holm 1.7e-7; κ MAE +0.090; triple joint +0.348 | natural joint **−1.14** [−1.53, −0.73] (harm); natural κ −0.14 | **+0.251** [0.20, 0.31]; challenge +0.362; natural +0.063 (n.s.) | **CONDITIONAL**: strong on mechanism-like data, fails the natural-mix safety rule, so **NOT SUPPORTED** under the prereg |
| **F5q higher-order residual** | yes; exact isolation (pm control) | 21 complete lattices (Δ +1: 11, 0: 10; Δ = −1 not constructible) | triple joint +0.060 [0.040, 0.080], secondary Holm 0.022; Δ error +0.018 (n.s.); pairs +0.007 (n.s.) | natural pairs −0.41 (n.s.) | not executed (lattices are prediction-only) | **UNDERPOWERED / secondary-positive on triples only** |
| **DINOv2 vision** | yes; vproj gradient 14.1 | all roots | joint log-loss **+0.194**, secondary Holm 0.041 | natural **+1.12** | not executed | **SUPPORTED (secondary)** |
| **keying** | yes; erratum: keyed ≠ unkeyed on every root | all roots | B-U better: **−0.032**, Holm < 1e-4 | natural −1.00 | not executed | **NO_BENEFIT** (unkeyed is better) |
| **J travel** | yes; the 2nd TOP1 key decides 18–86 choices | 15 roots with ≥ 2 VERIFIED equal-move alternatives | regret: J 0.210, no-J 0.301, shuffled 0.236; Δ +0.091 [−0.03, 0.25], p 0.77 | — | success J − no-J −0.019 (n.s.) | **UNDERPOWERED** |
| **D pair term** | yes | 119 exact infeasible lattices | D − D-pairless F1 +0.012 [−0.017, 0.047] | natural 13: +0.16 (n.s.) | not applicable | **NO_DEMONSTRATED_BENEFIT** |

## 2. Approaches compared

**Strict TOP1** (129 roots):

| approach | success |
|---|---|
| **keyed B** | **0.734** |
| B-F3pm | 0.708 |
| geometry-only | 0.612 |
| C | 0.579 |
| A | 0.558 |
| SF | 0.318 |
| *G+M (planner-assisted)* | *0.783 (n.s. vs B)* |

- **B vs the learned baselines and geometry:** B beats A (+0.176), C (+0.155), SF (+0.416) and geometry (+0.121).
- **Challenge set (81 roots):** B is best of all the strict methods (0.835).
- **Natural mix (48 roots):** B 0.562 is not better than geometry (0.625) or B-F3pm (0.625).
- **P12 (80 roots, completed):** geometry 0.838 > B 0.629 > A 0.596 > C 0.546 > SF 0.512; B − SF +0.117 (p 0.008).

**Prediction:**
- **Challenge set:** every B-family model is accurate (κ MAE ≈ 0.10, against 0.73 for the constant-zero control).
- **Natural mix:** every coupled model is badly miscalibrated (joint log-loss 2.5 nats for B), and the constant κ̂ = 0 control is best there (κ MAE 0.034).

**D:**
- **Feasibility:** indistinguishable from A / SF (AUROC 0.98).
- **Blocker identity:** best overall (F1 0.892) but not distinguishable from B (−0.026, n.s.); better than A and geometry.

## 3. P12 corrections (0059)

- **F3 under the preregistered seed-mean estimand:** Δ −0.057 [−0.099, −0.016], Holm p 0.0496. It is still a reversal, but weaker than the published seed-wise statistic (−0.074, Holm 0.0118).
- **F5s:** Holm 0.082, still not confirmed.
- **Constant-zero control:** MAE 0.092, better than every frozen model on P12.
- **Strict D matching:** confirms the 33 P10b common roots; no-clearing-set predictions are now scored as misses.

## 4. Claims

**Supported** (two separate claims):
1. **Order:** an order representation is necessary for order-dependent choices, in both prediction and execution.
2. **Repair selection:** keyed B is the best *learned* strict-TOP1 repair selector on held-out roots from the training mechanisms. It improves on A, C, SF and geometry and is level with planner-assisted G+M.

**Conditional:**
- **F5 coupling:** generic pairwise coupling (F5s) improves interaction likelihood, triple lattices and execution on mechanism-like scenes, but is badly miscalibrated on the natural mix.
- **F4 omission pair:** improves execution mainly through admission (fewer abstentions), not through better omission prediction.

**Negative:**
- **F3** (reversal in P12 and P13);
- **learned F1** (no discrimination, no deployment path);
- **keying** (unkeyed is better);
- **the D pair term.**

**Unresolved:** J (15 roots); F5q (21 lattices, Δ = −1 class missing); natural-mix order (2 roots).

**Not claimed:** universality, generalization to new mechanism families (P12 shows it fails), 3D, hardware.

## 5. Recommendation for a lean 3D model (no 3D work was started)

**Keep:**
- **Some order representation:** a GRU or the predecessor module; A / C show the GRU suffices.
- **DINOv2 visual tokens.**
- **The scene unary with generic pairwise coupling (F5),** but only if the training distribution includes realistic, feasible-original scenes. The natural-mix calibration failure is the main risk.
- **The analytic static veto.**
- **Omission modelling (F4),** provisionally, for its deployment effect, to be re-tested with matched admission calibration.

**Drop:** the F3 z₀–z_S pair, the learned F1 static head, keyed instantiation (use the simpler unique-factor graph) and the D pair term (D-pairless is as good).

**Defer:** the higher-order residual (triple-only gain) and J (cheap tie-break, unproven).

**Before any 3D port:**
- the natural-mix miscalibration must be fixed and re-tested;
- generalization beyond the training mechanism families remains the open problem (P12).

## 6. Compute, tests, integrity

**Spend (CPU-s, all under the caps):**

| category | used / cap |
|---|---|
| audit / regression | 868 / 4,000 |
| dev | 3,921 / 10,000 |
| training | 33,683 / 35,000 (corrected; see 0062) |
| teacher | 59,278 / 65,000 |
| P12 continuation | 3,539 / 9,000 |
| execution | 10,698 / 22,000 |
| analysis | 714 / 5,000 |

**Tests:** full regression **430 / 430 passed** (407 historical + 6 P12 + 17 P13) and **6 / 6 replays**, in 739 CPU-s; 681 fixture planner calls are counted separately in `runs/p13/regression/calls.json`.

**Module sizes (explained exception):**
- `p13_factors.py` holds the P13-0 corrections, the P13-1 audit and the P13-4 / 6 analyses;
- `p13_pipeline.py` holds the ledger, construction, training and the freeze;
- they exceed the ~350-line target. There are four modules plus one test file, as specified.
