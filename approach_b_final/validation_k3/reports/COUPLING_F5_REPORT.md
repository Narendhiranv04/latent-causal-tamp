# Experiment A: is the X/Y coupling factor F5 useful?

**Sources and scope**
- Every number below is computed from the frozen checkpoints and frozen labels. The scripts are `nodes.py`, `coupling.py`, `multipass.py`, `pools.py` and `rules.py`; the machine-readable outputs are in `runs/out/{nodes,coupling,pools,rules}/`.
- **D** = the frozen bundle scorer (FULL_s0/s1/s2), never modified.
- **E** = the matched retrained uncoupled control from the ablation.
- **DREFIT** = D re-fitted on gvlab2. It is the environment-matched comparator for E, because E was trained in the same environment.

## A1. What D and E represent (from `xy.py` `XYNet.coeffs`)

**Shared quantities.**
- h_r = [g_r, v_s, c], where:
  - g_r is the ordered action summary;
  - v_s is the edit-aware endpoint scene vector;
  - c is the context: robot reference pose, goal and target attributes.
- **F3:** b_s = scene([v_s, c]), the endpoint Y logit, shared by every ordering of one endpoint.
- **F2:** o_r = order_s([g_r, v_r]), the ordered-X logit. It has no direct path from the context vector c.

| | D (coupled, frozen) | E (uncoupled, matched) |
|---|---|---|
| X logit at Y=0 | a_r = o_r | a_r = o_r + xs(h_r) |
| X logit at Y=1 | a_r + w_r = o_r + **xy(h_r)** (F5) | the same a_r (w ≡ 0) |
| Joint | P(Y=y)·P(X=x \| Y=y) with log odds-ratio(X, Y \| input) = w_r | X ⟂ Y \| input (log odds-ratio 0) |
| p11 used by the selector | σ(b_s)·σ(o_r + xy(h_r)) | σ(b_s)·σ(o_r + xs(h_r)) |
| Marginal P(X=1) | σ(b)σ(a+w) + (1−σ(b))σ(a) | σ(a) |

**1. The p11 hypothesis class is identical.**
- `xs` and `xy` are the same `mlp2(3W, 1)` on the same input h_r. With equal weights, D and E output the same p11 for every candidate.
- **F5 therefore adds no expressive capacity for the selector's score.** It adds capacity only for the *conditional* distribution: D can make X depend on Y, E cannot.
- D is also *less* expressive than E for X | Y = 0, since σ(o_r) has no context path.

**2. Every observed X has an observed Y (A3).** The two likelihoods therefore factorize exactly:
- L_D = Σ_s ℓ(Y_s; b_s) + Σ_{r: Y=0} ℓ(X_r; o_r) + Σ_{r: Y=1} ℓ(X_r; o_r + xy(h_r))
- L_E = Σ_s ℓ(Y_s; b_s) + Σ_r ℓ(X_r; o_r + xs(h_r))

So D fits its success-relevant X factor **only on Y = 1 endpoints**, while E fits one X head to the X labels pooled over both values of Y.

**3. What E's p11 estimates.** The target is P(X=1, Y=1 | in) = P(Y=1 | in)·P(X=1 | Y=1, in). E's p11 = σ(b)·P̂(X=1 | in) has the population bias

  bias_E = P(Y=1|in) · (1 − P(Y=1|in)) · [P(X=1|Y=0,in) − P(X=1|Y=1,in)].

Two consequences:
- The bias vanishes when X ⟂ Y given the network input. That holds if Y is (nearly) a deterministic function of the endpoint encoding v_s that the network can learn; Y AUROC on edited endpoints is 0.88–0.96 here.
- The bias is multiplied by P(Y)(1 − P(Y)), so it is small exactly for the candidates the selector picks, those with σ(b) near 1.

**This is the mathematical reason a correctly specified coupling can leave argmax selection unchanged.**

**4. Consequences for the knockout (A5).** In D, setting w ← 0 gives σ(b)·σ(o_r). That removes the **only context path into D's X factor** and returns D's Y = 0 conditional, P̂(X=1 | Y=0). The knockout therefore removes capacity as well as coupling. It is a reliance diagnostic, not an uncoupled model; E is the uncoupled control.

## A2. Does the trained D use F5?

Labeled VAL/TEST X nodes; w and Δp = σ(a+w) − σ(a). Full tables: `coupling/{dom}_{split}.json`.

| | w mean (sd), s0/s1/s2 | frac w>0 | mean \|Δp\| | frac \|Δp\| > 0.1 | within- vs between-endpoint sd of w (s0) |
|---|---|---|---|---|---|
| 2D VAL | 0.59 (1.22) / 0.35 (1.03) / 0.40 (0.73) | 0.66–0.72 | 0.10–0.12 | 0.41–0.45 | 0.69 vs 1.10 |
| 2D TEST | 0.67 / 0.44 / 0.51 | 0.67–0.77 | 0.12–0.14 | 0.46–0.49 | 0.67 vs 1.16 |
| 3D VAL | 0.39 / 0.73 / 0.51 | 0.69–0.78 | 0.08–0.09 | 0.27–0.33 | 0.32 vs 1.23 |
| 3D TEST | 0.29 / 0.63 / 0.47 | 0.66–0.76 | 0.09 | 0.28–0.32 | 0.37 vs 1.20 |

**Over the full M4 candidate pools** (FULL_s0, every scored candidate): mean w = 1.56 (2D VAL) and 1.57 (2D TEST); mean |Δp| = 0.19 / 0.19.

**Where w is large (FULL_s0)**
- **By sequence length:**
  - 2D: w is largest for K1 / length-1 sequences (1.8–1.9; Δp ≈ 0.07–0.09).
  - 3D: w is positive for length 1–2 (≈1.0) and slightly negative for length 3 (−0.3).
- **By the observed endpoint label:**
  - In 3D, w is ≈0 on Y = 1 endpoints (0.06 / −0.02) and large on Y = 0 endpoints (1.3 / 1.2).
  - But for an endpoint with observed Y = 0, σ(a + w) is a **counterfactual** prediction that no label ever supervised. Large w there is unidentified extrapolation, not learned coupling.

**Interpretation.** The trained D does use F5 numerically: conditional X probabilities differ by about 0.1 on average, and by more than 0.1 for 30–50% of the labeled nodes. The coefficient is mostly an endpoint-level quantity; it varies more between endpoints than between orderings of one endpoint.

**A large w is not evidence that coupling helps planning** (see A4, A5).

## A3. Is the coupling identifiable from our labels?

Unique-endpoint accounting from `nodes.py audit` (`audit_{dom}.json`); TRAIN is the expanded training snapshot.

| | 2D TRAIN | 2D VAL | 3D TRAIN | 3D VAL |
|---|---|---|---|---|
| X observed, Y observed | 20,550 (100%) | 1,864 | 10,890 (100%) | 904 |
| X observed, Y missing | **0** | 0 | **0** | 0 |
| Y observed (edited endpoint), no X child | 4,232 (all Y = 0) | 0 | 1,244 (all Y = 0) | 0 |
| X with Y = 0 → supervises σ(a) | 9,060 (x=1 rate 0.44) | 466 (0.67) | 3,191 (0.61) | 239 (0.77) |
| X with Y = 1 → supervises σ(a+w) | 11,490 (0.56) | 1,398 (0.51) | 7,699 (0.64) | 665 (0.68) |
| Endpoints with ≥ 2 observed orderings, Y=0 / Y=1 | 995 / 1,579 | 173 / 293 | 471 / 1,270 | 71 / 166 |
| … with discordant X across orderings, Y=0 / Y=1 | 450 / 1,093 | 82 / 219 | 227 / 605 | 30 / 68 |

**What the table shows**
- Both conditionals are supervised on thousands of nodes. In the sense of the model, P(X | Y=0, in) and P(X | Y=1, in) are **identified separately**.
- What is *not* identified is the counterfactual X | Y = 1 for an endpoint that is physically Y = 0, and vice versa: each endpoint has one Y value.
  - So w at a given input is learned only by interpolation across endpoints with different Y.
  - Those endpoints differ systematically, for example in how much the edit changes the scene.
- The raw label rates go the "wrong" way (X=1 is *more* common when Y=0 in VAL/TEST). This reflects how the label sets were built (omission/Y-negative constructions are short, easy relocations), not a causal X↔Y effect.

**Finite-budget caveat.**
- Many X = 0 and Y = 0 labels are budget-limited planner outcomes, not certificates of impossibility. In the ablation cache, 2D X = 0 is 2,909 UNKNOWN_PLANNER + 293 UNKNOWN_TRANSIT vs 3,036 CERTIFIED_INFEASIBLE, and Y = 0 is 4,166 UNKNOWN_PLANNER vs 2,665 CERTIFIED.
- Part of any learned X–Y dependence can therefore reflect *shared planner difficulty* (a cluttered endpoint makes both the relocation and the target plan harder), not a physical dependence of X on Y.

## A4. Conditional prediction quality (held-out, frozen labels)

Seed-mean paired differences E − D per labeled node; layout-cluster bootstrap. **Lower NLL is better, so positive means D is better.**

| | x\|y=0 NLL | x\|y=1 NLL | Z NLL (p11) |
|---|---|---|---|
| 2D VAL, E − FULL | −0.004 [−0.032, 0.024] | −0.000 [−0.020, 0.019] | +0.006 [−0.008, 0.019] |
| 2D TEST, E − FULL | +0.008 [−0.020, 0.037] | −0.013 [−0.035, 0.008] | +0.003 [−0.015, 0.020] |
| 3D VAL, E − FULL | +0.007 [−0.017, 0.029] | +0.013 [−0.006, 0.028] | +0.007 [−0.008, 0.021] |
| 3D TEST, E − FULL | +0.006 [−0.013, 0.025] | **+0.022 [0.006, 0.038]** | +0.006 [−0.008, 0.019] |
| 2D TEST, E − DREFIT | −0.003 [−0.033, 0.030] | −0.007 [−0.025, 0.010] | **−0.020 [−0.033, −0.006]** |
| 3D TEST, E − DREFIT | +0.002 [−0.019, 0.022] | **+0.018 [0.002, 0.034]** | +0.009 [−0.004, 0.021] |

**Other conditional metrics** (s0, `coupling/*.json`, per seed and per K)
- X AUROC given Y, Y AUROC on edited endpoints, Brier and ECE are all within seed spread between D and E.
- Same-endpoint order ranking is also within seed spread. Seed means for 2D TEST: D 0.767, E 0.790. For 3D TEST: D 0.877, E 0.878.

**Reading.**
- **X | Y = 0:** no detectable difference anywhere.
- **X | Y = 1** (the success-relevant conditional): D is better only in 3D TEST, by about 0.02 nats (about 5% of the NLL), against both FULL and DREFIT. It is not better in 3D VAL or 2D.
- **Z:** no consistent difference.
- **Multiplicity:** 18 cells were examined, so the two 3D-TEST cells are suggestive, not confirmatory.

## A5. Frozen-D coupling knockout (w ← 0)

**Teacher-free part** (labeled nodes; s0/s1/s2):

| | Z AUROC p11 → p11_w0 | Same-endpoint order accuracy p11 → p11_w0 |
|---|---|---|
| 2D VAL | 0.818/0.815/0.795 → 0.776/0.776/0.750 | 0.802/0.796/0.796 → 0.739/0.771/0.777 |
| 2D TEST | 0.779/0.766/0.756 → 0.738/0.728/0.709 | 0.758/0.776/0.766 → 0.708/0.755/0.762 |
| 3D VAL | 0.900/0.918/0.891 → 0.881/0.900/0.871 | 0.797/0.861/0.789 → 0.797/0.866/0.792 |
| 3D TEST | 0.909/0.901/0.879 → 0.884/0.883/0.854 | 0.903/0.870/0.859 → 0.910/0.868/0.864 |

- **Mean \|p11 − p11_w0\|** on labeled nodes is 0.05–0.07.
- **Knockout rank of the best known success** (FULL_s0, pessimistic tie rank), median: 2D VAL 185 → 90 and TEST 91 → 88; 3D VAL 12 → 12 and TEST 15 → 12.
  - Known successes are a small labeled subset of each pool, so this is only a weak diagnostic.

**Physical part.** Every knockout argmax repair on every K1–K3 root was physically verified (0 UNKNOWN). Paired D(w=0) − D, seed-mean, pp, 95% CI:

| | Task, registered rule | Task, forced repair | Task, fixed gating | Correct ABSTAIN (NONE) | Correct NOOP (K0) |
|---|---|---|---|---|---|
| 2D VAL | −1.5 [−3.5, 0.6] | −1.8 [−3.8, 0.2] | −1.5 [−3.5, 0.6] | +3.3 [1.8, 4.9] | 0.0 |
| 2D TEST | −0.9 [−2.9, 1.3] | −1.1 [−3.2, 1.1] | −0.6 [−2.7, 1.5] | +2.0 [0.9, 3.3] | 0.0 |
| 3D VAL | −1.1 [−2.9, 0.8] | −1.1 [−2.9, 0.8] | −1.1 [−2.9, 0.8] | **+14.4 [7.5, 21.8]** | 0.0 |
| 3D TEST | −0.1 [−2.1, 1.8] | +0.1 [−1.8, 2.1] | 0.0 [−1.9, 1.9] | **+9.7 [4.3, 15.6]** | 0.0 |

Notes on the table:
- The knockout leaves the NOOP probability unchanged by construction.
- Its p11 is lower everywhere, so under the registered rule it abstains more often on NONE roots. That is a calibration shift, not better discrimination: D's own VAL-tuned rule reaches the same ABSTAIN level (2D 96.0, 3D 96.0).

**Reading.**
- The trained D's *task* decisions do not depend on F5: the argmax repair changes in many roots, but physical success does not.
- F5 does raise p11 overall, mostly on short sequences, which matters only for the threshold scale.

## A. Verdict on the six questions

| Question | Answer | Evidence |
|---|---|---|
| 1. Is F5 mathematically meaningful? | **Yes, for the conditional distribution; no, for the score family.** It lets P(X \| Y) differ by Y, so the joint P(X, Y) is correctly factorized. It adds no capacity for the selector's p11: D and E share the same p11 hypothesis class. | A1 |
| 2. Does the trained D use F5? | **Yes, numerically.** w > 0 for 66–78% of nodes; mean \|Δp\| ≈ 0.10 (2D) and 0.09 (3D), and 0.19 over the pools. Knocking it out lowers labeled Z AUROC by 0.02–0.04. | A2, A5 |
| 3. Is the conditional effect identifiable? | **Partly.** Both conditionals are supervised (2D TRAIN 9,060 Y=0 vs 11,490 Y=1 X labels; every X has its Y). Per input, the opposite-Y branch is a counterfactual that no label covers; w is learned by interpolation across endpoints, and part of it may reflect shared planner difficulty under a finite budget. | A3 |
| 4. Does F5 improve conditional X prediction? | **Not reliably.** No difference for X\|Y=0 anywhere. X\|Y=1: D is better only in 3D TEST (−0.02 nats vs E and vs DREFIT); there is no difference in 3D VAL or 2D. | A4 |
| 5. Does it improve ranking or physical success? | **No.** The matched E is +1.4 / −4.2 / −2.4 / +2.8 pp (sign flips). Under VAL-tuned rules it is +1.5 / −0.9 / −2.4 / +5.1. The knockout costs −1.5 to +0.1 pp, all n.s. | `rules/EVAL_*`, P0 |
| 6. Keep, make optional, or simplify? | **Treat F5 as optional.** Keep it in the model as the principled joint factorization (it costs nothing and gives the conditional semantics). Do **not** claim it improves planning. Report E as an equally good uncoupled variant and describe F5 as a modeling choice, not a contribution to task success. | all of the above |
