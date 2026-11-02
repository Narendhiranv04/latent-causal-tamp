# 0132 — BXY-P25: final implemented method and findings (Approach B, 2D)

Date: 2026-11-02. Gate: BXY-P25 (final).

- **Start:** `41636139` (P24 complete).
- **Inputs:** the one locked P24 output ([EVALUATION_P24.json](../runs/approach_b/bxy_p24_v1/EVALUATION_P24.json), sha `d1f6644c…`), plus the historical development artifacts, which are reported separately.
- **Not done:** no training, no retuning of the frozen rules, no teacher call, no new scene.

**Companion documents:**
- [METHODOLOGY_FINAL_IMPLEMENTED.md](METHODOLOGY_FINAL_IMPLEMENTED.md): the manuscript-ready method.
- [0131](0131_BXY_P24_ONE_SHOT_CONFIRMATION.md): the P24 evidence.
- [0129A](0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md): the preserved P22 addendum.
- The 31 October specification, which is unchanged.

## 1. Final answers

From [DECISION_P25.json](../runs/approach_b/bxy_p25_v1/DECISION_P25.json):

| Question | Answer from the independent P24 cohort |
|---|---|
| Does the X/Y system beat a matched direct success predictor? | **Not established.** U: D 0.259, E 0.269, DIRECT-GEO 0.218. D − DIRECT +0.041 (Holm CI [−0.005, 0.088]); E − DIRECT +0.052 (Holm CI [0.000, 0.104], p 0.0170 vs a Holm level of 0.0167). Both are below the +0.10 gain gate, and both would fail the unnecessary-repair guardrail (+0.182). |
| Does order-aware X matter? | **Yes.** O2: D beats its order-invariant twin G by **+0.173** in success on repairable K3/K4 roots (Holm CI [0.058, 0.308]). On 41 certified order-twin roots, D and E rank every twin correctly. G's 0.5 there is structural. |
| Does the quadratic coupling F5 help? | **No.** D − E is −0.010 [−0.031, 0.010] on U, and has never been positive in any study. |
| K3 / K4? | **Physically established:** 31 K3 and 21 K4 roots are witnessed *and* certified necessary in independent data (K4 was 7 in development). Learned selection on them is descriptive only: K4 success D 0.71, E 0.71, DIRECT 0.52, G 0.62, n = 21. |
| Is the 2D method ready? | **The 2D pipeline is complete, reproducible and custody-verified.** The predicted *advantage* of X/Y over a strong direct baseline is small, consistent in sign, and unconfirmed. If X/Y is used, prefer **E**. |

## 2. Method actually tested (summary)

The full text is in [METHODOLOGY_FINAL_IMPLEMENTED.md](METHODOLOGY_FINAL_IMPLEMENTED.md); the schematic is [00](../visualizations/approach_b/bxy_p25_v1/00_protocol_and_architecture_schematic.png).

**Teacher protocol (31 October, original).** A scene is repaired by an ordered relocation prefix r = (a1 … am), executed from q0 with no reset. X = 1 iff every relocation and the final connector to q_ref execute. Y = 1 iff the original target succeeds from q_ref in the edited scene. Success = X · Y.

**Scorer (original F1–F5 plus the P17 extensions GEO2 and SYM).**
- F1 is an analytic screen.
- F2 is the order-aware X unary a_q; F3 is the edited-scene Y unary b_s; F5 is an optional coupling w_q.
- p_succ = σ(b)σ(a + w).
- Training uses the joint X/Y likelihood, travel (Huber) and the SYM edit contrast.
- Selection: F1 first, then a no-op gate, then argmin −log p + α m + γ Ĵ.

**What the models do.** The models **rank an already-generated catalogue**. They do not generate trajectories or discover global causes.

**Frozen ensembles.** P21 trained 15 members per arm; they were frozen, custody-verified on Google Drive, and evaluated once.

## 3. Confirmatory results

All results are from P24: one look, 237 roots.

| Arm | U (193 INF) | C (75 AVAIL) | REP34 (52) | Unnecessary (44 FEA) | K0 no-op correct |
|---|---|---|---|---|---|
| D XYQ-GEO-SYM | 0.259 [0.202, 0.325] | 0.667 | 0.750 | 0.227 | 0.773 |
| E XY-UNC-SA-GEO-SYM | **0.269** [0.212, 0.336] | **0.693** | **0.769** | 0.227 | 0.773 |
| DIRECT-GEO | 0.218 [0.165, 0.281] | 0.560 | 0.635 | **0.045** | **0.955** |
| G order-invariant | 0.212 [0.161, 0.275] | 0.547 | 0.577 | 0.205 | 0.795 |
| Analytic access (not learned) | 0.212 | 0.547 | — | 0.000 | 1.000 |
| Verify-first oracle (evaluator-only) | 0.389 | — | — | — | — |

The paired contrasts with Holm adjustment are given in full in [0131 §(d)](0131_BXY_P24_ONE_SHOT_CONFIRMATION.md). Every primary and secondary contrast is `NOT_ESTABLISHED`; O1, O2 and O3 are `IMPROVES`. The figures are [frontier](../visualizations/approach_b/bxy_p25_v1/05_frontier.png) and [contrasts](../visualizations/approach_b/bxy_p24_v1/02_contrasts.png).

**Development and confirmation side by side (kept separate, never pooled):**

| Study | D | E | DIRECT | D − DIRECT |
|---|---|---|---|---|
| P21 development (398 roots, out-of-fold, 3 seeds) | 0.289 | 0.287 | 0.258 | +0.031 [−0.002, 0.064] |
| **P24 independent (237 roots, frozen 15-member ensembles)** | 0.259 | 0.269 | 0.218 | +0.041 [0.000, 0.083] (Holm [−0.005, 0.088]) |

Both studies point to a small positive X/Y effect of about +0.03 to +0.05 on U, and neither establishes it. They are not combined post hoc.

## 4. Why the primary failed (failure explanations)

1. **Most failures are physical X failures, not ranking errors.** On the 193 infeasible roots, the sealed choice ends as follows ([figure](../visualizations/approach_b/bxy_p25_v1/04_failure_breakdown.png)):

| Arm | Success | No-op | X fails during a relocation | X fails at the connector | Y fails | Unverified |
|---|---|---|---|---|---|---|
| D | 50 | 24 | 86 | 1 | 32 | 0 |
| E | 52 | 24 | 81 | 1 | 34 | 1 |
| DIRECT | 42 | 20 | 97 | 1 | 32 | 1 |
| G | 41 | 26 | 98 | 1 | 26 | 1 |

   - Only 75 / 193 roots have *any* verified repair; the projection was 123. This caps U near 0.39, which is exactly the verify-first oracle.
   - The binding limitation is unchanged: relocation planning under the fixed per-query budget.
   - X/Y's advantage is concentrated where X is the issue: it has 11 to 16 fewer relocation failures than DIRECT.
2. **Availability fell short of the plan.**
   - Generator intent is not physics. Of 152 roots built with K_intent 3 or 4, only 52 have a verified K3/K4 repair.
   - 22 of the 66 K0-intent v21b roots were in fact infeasible.
   - This roughly halved the effective n and widened every interval.
3. **The unnecessary-repair cost comes mostly from the frozen decision rule.** This is exploratory; see §6.
   - D and E carry a no-op gate of 0.7 and α = 0; DIRECT carries 0.5 and α = 0.3. Both were chosen per fold on development early-stop roots, then frozen.
   - Recomputed on the labelled cohort, D/E with DIRECT's gate would repair 4/44 feasible roots (not 10/44). With DIRECT's α they would repair 2/44, the same as DIRECT.
   - Their U advantage shrinks accordingly, to +0.026 to +0.041.
   - These settings are **not** adopted. Picking a rule on test labels would be retuning.
4. **DIRECT omits; X/Y does not.**
   - DIRECT's length penalty makes it choose a repair shorter than the verified K on 7 AVAIL roots. D, E and G never do.
   - None of the 202 single-object omission tests on shortest verified repairs found a removable object: 96 are certified necessary, 40 necessary but uncertified, and 66 unobserved.

## 5. Claims matrix

| # | Claim | Status | Evidence |
|---|---|---|---|
| 1 | The X/Y factorization (D or E) beats a matched direct success predictor on U | **NOT SUPPORTED (not established)** | P24 primary; P21 development same direction, also not established |
| 2 | X/Y beats it on availability-conditioned C | Consistency only: E − DIRECT +0.133 [0.040, 0.240] raw; not a registered claim | P24 C check |
| 3 | Order-aware F2 improves outcomes over an order-invariant control on repairable K3/K4 roots | **SUPPORTED (confirmatory)** | P24 O2 +0.173, Holm CI [0.058, 0.308] |
| 4 | F2 orders certified order twins correctly | **SUPPORTED** (descriptive; G's 0.5 is structural) | 41 certified roots: 1.000 |
| 5 | Quadratic coupling F5 (D vs E) helps | **UNSUPPORTED** | P24 D − E −0.010; P21 +0.002 |
| 6 | The X/Y arms keep false repairs at DIRECT's level | **NOT SUPPORTED** | Unnecessary repairs 10/44 vs 2/44 (+0.182 [0.068, 0.295]), all neutral |
| 7 | Learned arms avoid harmful edits on feasible roots | Observed 0 / 44 for all arms. **Not proven safe** (small denominator) | P24 FEA |
| 8 | K3 / K4 necessity exists physically in this 2D family | **SUPPORTED** | 31 K3 and 21 K4 roots witnessed and certified (K_cert = verified K) |
| 9 | Learned selection works on K4 specifically | Descriptive only: D 0.71 [0.50, 0.86] vs DIRECT 0.52 [0.32, 0.72], n = 21 | No registered per-stratum test |
| 10 | The learned scorer adds value over analytic geometry | Weakly: DIRECT (0.218) and G (0.212) are about equal to analytic access (0.212); D/E are about +0.05 above it | P24 arms (no registered test) |
| 11 | Y0 (target feasibility) is predicted well | Yes, descriptively: AUROC 0.960–0.967 for all arms | P24 calibration |
| 12 | The ensemble is reproducible and in custody | **SUPPORTED** | Drive read-back 126/126 hashes; P25 re-prediction max difference 0.0 vs the sealed means |
| 13 | Results generalize to other generators or to 3D | **NOT CLAIMED** | Same 2D K34 doorway family, new seeds only |
| 14 | The model generates trajectories or discovers global causes | **NOT CLAIMED** | It ranks a supplied catalogue; the trajectories are the teacher's |

## 6. Exploratory ablations (P25; no claims)

These come from [ABLATIONS_P25.json](../runs/approach_b/bxy_p25_v1/ABLATIONS_P25.json) and [figure 01](../visualizations/approach_b/bxy_p25_v1/01_ablations.png).

**Procedure.** The 60 frozen checkpoints were re-run on the sealed label-free views. Their 15-member means reproduce the sealed predictions exactly (max |Δ| = 0.0). Selections were then rescored on the stored teacher outcomes with the locked code. These numbers are not tests.

**Single members (U):**

| Arm | Range | Median |
|---|---|---|
| D | 0.223–0.285 | 0.249 |
| E | 0.228–0.280 | 0.259 |
| DIRECT | 0.083–0.249 | 0.223 |
| G | 0.130–0.233 | 0.202 |

- Every D and E member scores at or above DIRECT's median.
- DIRECT members span a range about 2.7× wider and gain the most from ensembling (mean 0.192 at size 1 → 0.218 at size 15).

**Decision-rule variants:**
- With DIRECT's no-op gate (0.5), D/E unnecessary repairs fall to 4/44. U stays at 0.254 / 0.259, which is +0.036 / +0.041 vs DIRECT.
- With DIRECT's α (0.3), D/E match DIRECT's 2/44, with U at 0.244 (+0.026).
- DIRECT with α = 0 reaches U 0.238, at 7/44 unnecessary repairs.

**Reading.** At matched false-repair levels, the X/Y advantage is about +0.03 to +0.04. That is the same size as in development and below the registered gain gate.

## 7. What is learned, what is supplied analytically, what remains unproved

- **Learned:**
  - the X and Y unaries over an analytic feature set;
  - order sensitivity of X (confirmed against G);
  - Y0 feasibility (well calibrated);
  - a travel estimate.
- **Supplied analytically:**
  - the F1 admissibility screen;
  - GEO2 access features, which share geometry with the generator (a shortcut risk, also given to DIRECT);
  - the candidate catalogue;
  - the q_ref connector and target semantics;
  - K_cert;
  - every trajectory (teacher witnesses).
- **Unproved:**
  - an X/Y advantage over a strong direct predictor;
  - any value of F5;
  - false-repair parity;
  - safety on feasible scenes;
  - per-K learned superiority;
  - any generator-shift or 3D transfer.

## 8. Figures

**P24:** [cohort](../visualizations/approach_b/bxy_p24_v1/04_cohort_populations.png) · [endpoints](../visualizations/approach_b/bxy_p24_v1/01_endpoints.png) · [contrasts](../visualizations/approach_b/bxy_p24_v1/02_contrasts.png) · [K strata](../visualizations/approach_b/bxy_p24_v1/03_strata_by_K.png) · [D vs DIRECT disagreements](../visualizations/approach_b/bxy_p24_v1/05_choices_D_vs_DIRECT.png)

**P25:**
- [schematic](../visualizations/approach_b/bxy_p25_v1/00_protocol_and_architecture_schematic.png): schematic only, not data;
- [ablations](../visualizations/approach_b/bxy_p25_v1/01_ablations.png);
- [certified order twin](../visualizations/approach_b/bxy_p25_v1/02_certified_order_twin.png);
- storyboards of D's sealed choices on certified roots: [K4 s134](../visualizations/approach_b/bxy_p25_v1/03_storyboard_K4_s134_D_choice.png), [K4 s143](../visualizations/approach_b/bxy_p25_v1/03_storyboard_K4_s143_D_choice.png), [K3 s026](../visualizations/approach_b/bxy_p25_v1/03_storyboard_K3_s026_D_choice.png), [K3 s029](../visualizations/approach_b/bxy_p25_v1/03_storyboard_K3_s029_D_choice.png);
- [failure breakdown](../visualizations/approach_b/bxy_p25_v1/04_failure_breakdown.png);
- [frontier](../visualizations/approach_b/bxy_p25_v1/05_frontier.png).

**How the storyboards are drawn:**
- Every trajectory panel is a recorded teacher witness: relocations blue, connector pink, target from q_ref green.
- The robot continues from where the previous relocation ended. Nothing shows a home reset.
- Scene edits show recorded destinations. No panel is a schematic edit, except figure 00, which is labelled as such.

**Printable PDF:** [APPROACH_B_P25_FINAL_FINDINGS.pdf](APPROACH_B_P25_FINAL_FINDINGS.pdf), generated from this report and the methodology.

## 9. Gate record

**(a) SHAs:**

| Gate | Commits |
|---|---|
| P23.1 | `be8b272f` → `e2c90cde` |
| P24 | `a7efb1d4` (authorization), `3457e5f4` (seal), `0eb0f390` (labels), `4ba3f0a1` (evaluation), `41636139` (report), `ab0f86ed` (log paths), `07633a33` (witness files) |
| P25 | the commit that adds this file; the SHA is reported in the hand-off message |

**(b) Changes:**
- [bxy_p25_final.py](../bxy_p25_final.py): read-only; frozen-model re-prediction with a reproduction check, exploratory ablations, failure breakdown, decision manifest, figures.
- This report, the methodology and the PDF.
- Repo-relative paths in the P24 pytest log.

**(c) Artifacts** in `runs/approach_b/bxy_p25_v1/`:
- ABLATIONS_P25.json;
- DECISION_P25.json;
- MEMBER_PREDICTIONS_P25.json.gz (per-member p and Ĵ);
- figures in `visualizations/approach_b/bxy_p25_v1/`.

**(d) Counts and CIs:** see §3–§6.

**(e) Resources:** about 250 CPU-s per P25 run, single thread. No teacher call. P24's total is unchanged (66,283 CPU-s).

**(f) Tests and replays:**
- full suite: **744 passed, 1 skipped**, including 4 new P25 tests (decision ↔ evaluation consistency, rescoring reproduces the locked numbers, the frozen mean rule, the PDF table parser);
- six archived replays: exit 0;
- frozen-evidence hash guard over P-min–P24 and the P24 tables: **clean**.

**Incident.** The guard found that the P24 labels commit had omitted the 2,830 witness trajectories written during collection, along with the engine lock and heartbeat files.
- They were committed unchanged in `07633a33`, and all 2,846 witnesses referenced by result rows are present.
- Nothing was regenerated.

**(g) Verdict:** **`APPROACH_B_2D_CLOSED_PRIMARY_NOT_ESTABLISHED_ORDER_SUPPORTED`**.

**(h) Blockers:** none. **STOP after P25.**
- No 3D work.
- No new neural factor.
- No new teacher.
- No further confirmatory cohort without a new explicit decision.
