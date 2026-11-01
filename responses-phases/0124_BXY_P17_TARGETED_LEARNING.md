# 0124 — BXY-P17: targeted learning of the full X/Y methodology on informative development evidence

Date: 2026-11-01. Gate: BXY-P17, entered on the P16 **DATA_READY** decision (0123, commit `9d62caae`).

## Result (development, 5-fold cross-fit, out-of-fold; NOT independent confirmation)

The pre-declared primary candidate **D:XYQ-GEO-SYM** meets two frozen criteria on the outcome-blind population of record (P15 + V2.1:
115 roots, 76 initially infeasible, 31 of them with a verified repair in the catalogue):
- **IMPROVES_WITHIN_GUARDRAIL against the matched XYQ baseline B.**
- **SUPERIOR_TO_DIRECT** against the matched direct-success model A, which has the same GEO2 inputs.

Under the same frozen criteria:
- **the quadratic coupling is not supported**;
- **order-aware F2 is supported**;
- **SYM vs P14's CON is inconclusive**.

| Pre-declared contrast (outcome-blind roots) | Δ corrective success on infeasible roots [95% CI] (99%) | Δ unnecessary repairs on feasible roots [95% CI] | Other | Frozen verdict |
|---|---|---|---|---|
| P1 D vs B (XYQ-BASE) | **+0.215 [+0.136, +0.298]** (+0.118, +0.329) | −0.077 [−0.171, +0.009] | root joint NLL −1.86 [−2.46, −1.30]; harmful-edit (1→0) sign +0.67 | **IMPROVES_WITHIN_GUARDRAIL** |
| P2 D vs A (DIRECT-GEO) | **+0.123 [+0.061, +0.189]** (+0.044, +0.211) | **−0.103 [−0.179, −0.034]** | — | **SUPERIOR_TO_DIRECT** (development) |
| P3 D vs E (w = 0, scene-aware, same capacity) | +0.048 [+0.009, +0.092] (−0.000, +0.110) | +0.026 [−0.026, +0.077] | joint NLL **+0.11 [−0.17, +0.41]** (D not better) | **COUPLING UNSUPPORTED** (the gain is below 0.10 and the NLL is not better) |
| P4 D (SYM) vs C (P14 CON) | +0.039 [−0.004, +0.088] | −0.034 [−0.094, +0.026] | joint NLL −0.14 [−0.53, +0.24] | INCONCLUSIVE |
| P5 D vs G (order-invariant F2, same capacity) | +0.079 [+0.026, +0.140] | −0.017 [−0.068, +0.026] | **order concordance +0.18 [+0.047, +0.307]** | **ORDER_SUPPORTED** (99% CI of order: [0.000, 0.340], borderline) |

How the results hold up:
- **Per seed,** D's corrective success / unnecessary repairs on the outcome-blind roots are 0.303 / 0.154, 0.263 / 0.128 and
  0.250 / 0.077. D beats A and B on every seed.
- **On the independently generated, outcome-guided P-min roots** (reported separately; 55 infeasible) the ordering replicates:

  | Arm | Success | Unnecessary repairs |
  |---|---|---|
  | D | 0.485 | 0.054 |
  | B | 0.145 | 0.054 |
  | A | 0.291 | 0.073 |

  - P1: +0.339 [+0.234, +0.455].
  - P2: +0.194 [+0.115, +0.278].
  - Coupling (P3): nothing, +0.012 [−0.030, +0.056].

**What the result does not show, and the main caveats:**
1. **The gain is mostly the analytic geometry (GEO2), not the X/Y structure per se.** Every GEO2 arm (C, D, E, G) succeeds on 0.19–0.27
   of infeasible roots, against 0.06 for B.
   - GEO2's access features use the same grasp-screen geometry that built the V2.1 hard scenes. A **generator-geometry shortcut cannot be
     excluded**.
   - The gains do replicate on P-min, whose scenes were built by an older generator (BD_GEN_V1) without these maps.
   - DIRECT receives the same GEO2 inputs, and D still beats it by +0.12.
2. **Absolute performance is modest.** D finds a verified repair on 0.27 of infeasible roots against an availability ceiling of 0.41
   (verify-first). It still repairs **0.12** of initially feasible outcome-blind roots (0.20 on V2.1 alone) when doing nothing was
   correct.
   - The **geometry-only reference** (no-op if S0's access screens are open, else the shortest candidate whose edited scene has open
     modes) succeeds on 0.16 with **zero** unnecessary repairs. That is a different trade-off.
   - The inner rule choice on about 51 early-stop roots under-estimated the out-of-fold unnecessary-repair rate: inner ≤ 0.10, out of
     fold 0.12.
3. **Small n.** 76 infeasible and 39 feasible outcome-blind roots, all independent families. Verified-K strata among them:
   - K1 n = 17 (D 0.57, A 0.39, B 0.22);
   - **K2 n = 12 (D 0.83, A 0.36, B 0.06)**;
   - K3 n = 2.
4. **Development only.** Cross-fit on development roots whose scenes informed generator design.
   - The confirmatory test (P18 plan) is needed before any claim of superiority.
   - Nothing here identifies a causal edge: w is a statistical coupling, and it did not help.

---

## 1. Frozen design (before any optimizer step)

- **Design file:** [TRAINING_DESIGN_P17.json](../runs/approach_b/bxy_p17_v1/TRAINING_DESIGN_P17.json), sha `28c6a767…`, committed in
  `67661ac7` with authorization V1. The only pre-launch compute on real data was timing on **randomized labels**.
- **Data:** 312 development roots — P-min 197 (176 train + 21 val), P15 28, V2.1 87 — in 5 family-grouped folds, stratified by corpus ×
  outcome-free difficulty intent (P-min design stratum, P15 K_intent, V2.1 mechanism × K_intent).
  - Each fold has an early-stop subset of about 1/5 of its training families (≈ 51 roots).
  - Every root is held out exactly once. Families never cross folds (test).
  - The 34 exposed P-min test roots and every confirmatory namespace are absent.
- **Arms:** 6 × 5 folds × 3 seeds = 90 runs.

| Arm | Model | Loss | Role |
|---|---|---|---|
| A DIRECT-GEO | scene-aware direct success logit + GEO2 on its logits | success BCE | matched DIRECT |
| B XYQ-BASE | quadratic X/Y | exact joint NLL + λ_J L_J (λ_J = 1) | matched baseline |
| C XYQ-GEO-CON | B + GEO2 | + κ·P14 CON (frozen definition) | P14's best idea, retrained |
| D XYQ-GEO-SYM | B + GEO2 | + κ·SYM | **pre-declared primary** |
| E XY-UNC-SA-GEO-SYM | D with w = 0 + scene-aware xs head | + κ·SYM | capacity-matched uncoupled control |
| G XYQ-GEO-SYM-ORDINV | D with order-invariant F2 (same modules on prefix-free tokens, unordered pair mixing) + S0-evaluated action features | + κ·SYM | order control |

- **Parameter counts:** 553,001 for A, C, D, E and G (identical, tested), and 549,799 for B.
- **G replaces the menu's F (noJ), declared before launch.** The travel auxiliary's effect on feasibility already had P11 / P12 evidence;
  order had no trained control. Travel-blind *selection* is still reported for every arm.
- **GEO2** (scorer tensors and access maps only):
  - φ_Y = the P14 8 clearances + T's open pick / place modes (counts, open flags) and goal occupancy in the edited scene;
  - φ_X = per-action open pick modes of the moved object in its ideal predecessor scene and open place modes at its destination (S0 for
    G);
  - 30 extra placement maps for non-goal destinations were computed in P17 (871.6 CPU-s; the P16 map file is untouched).
- **SYM** (an auxiliary, separately logged; the exact joint NLL stays the core):
  - (Y0, Y_s) = (0, 1): softplus(−(b_s − b_0));
  - (1, 0): softplus(b_s − b_0), so harmful edits are penalized if predicted helpful;
  - (0, 0) / (1, 1): softplus(|b_s − b_0| − 1);
  - the three groups are averaged with equal weight within each root, plus the P14 contrast over discordant edited–edited pairs.
- **Training:** the P11 TRAIN settings (AdamW 1e-3, batch 12, clip 10, ES every 20 updates, patience 15, ≤ 3,000 updates). Early stopping
  uses only the exact joint NLL (DIRECT: success BCE).
- **Selection:** one rule per (arm, fold) from the early-stop roots (3 seeds pooled), grid no-op gate {none, 0.5, 0.7} × α {0, 0.1, 0.3}.
  - Maximize inner corrective success subject to inner unnecessary repairs ≤ 0.10.
  - γ = 0.05 for travel-trained arms, otherwise 0; β = η = 0.
  - Every arm × fold met the inner guardrail.
  - D's rules: α 0 or 0.1, no gate except fold 2 (gate 0.7).

## 2. Execution and compute

| | Value |
|---|---|
| runs | 90 / 90 DONE, 0 non-finite updates, median 700 updates, median 401 CPU-s / run (max 622) |
| aggregate CPU (ledger, incl. the V1 fault) | **38,138 / 48,000** |
| wall | **9,688 / 21,600 s** |
| evaluation | < 30 CPU-s |

**Fault, disclosed.**
- The P17 worker writes a fourth file, `predictions_es.json`, needed by the frozen inner rule choice. The frozen P12 result validator
  accepts exactly three files, so the first session reaped every finished run as `corrupt_output` and requeued it.
- I stopped the launcher. The validator fix is confined to `Runner17` (commit `9432d3a4`), with a new versioned
  [AUTHORIZATION_V2.json](../runs/approach_b/bxy_p17_v1/AUTHORIZATION_V2.json) that records the amendment; V1 was never edited.
- The V1 session's **3,542 CPU-s and 911 s stay charged**.
- Four complete attempt-1 outputs were reinstated unchanged from `quarantine/`. Their RESULT.json hashes verify, and attempt 2 of A and B
  reproduced attempt 1 bit for bit.

## 3. Arms on the outcome-blind population (inner rule; seed means per root)

| Arm | success (infeasible) | unnecessary (feasible) | harmful unnecessary | P11.1 rule succ / unn | travel-blind succ / unn | root joint NLL | edited-Y AUROC | edit sign 0→1 / 1→0 | order | omission | Y0 AUROC / Brier | P(Y) ECE / Brier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A DIRECT-GEO | 0.149 | 0.222 | 0.034 | 0.206 / 0.393 | 0.149 / 0.222 | — | — | — | — | — | 0.901 / 0.122 | — |
| B XYQ-BASE | 0.057 | 0.197 | 0.085 | 0.079 / 0.333 | 0.066 / 0.248 | 9.02 | 0.676 | 0.94 / **0.23** | 0.63 | 0.82 | 0.849 / 0.151 | 0.057 / 0.145 |
| C XYQ-GEO-CON | 0.232 | 0.154 | 0.017 | 0.250 / 0.239 | 0.237 / 0.154 | 7.30 | 0.931 | 0.97 / 0.89 | 0.65 | 0.98 | 0.925 / 0.108 | 0.049 / 0.104 |
| **D XYQ-GEO-SYM** | **0.272** | 0.120 | 0.034 | 0.241 / 0.094 | 0.298 / 0.291 | 7.16 | 0.935 | 0.98 / **0.90** | **0.71** | 1.00 | 0.931 / 0.110 | 0.044 / 0.102 |
| E XY-UNC-SA-GEO-SYM | 0.224 | **0.094** | 0.009 | 0.215 / 0.068 | 0.268 / 0.145 | **7.05** | 0.941 | 0.98 / 0.89 | 0.66 | 1.00 | 0.924 / 0.115 | **0.033** / 0.104 |
| G XYQ-GEO-SYM-ORDINV | 0.193 | 0.137 | 0.026 | 0.167 / 0.128 | 0.232 / 0.333 | 7.38 | 0.934 | 0.97 / 0.87 | **0.53** | 0.99 | 0.926 / 0.111 | 0.033 / 0.102 |

References on the same roots (single deterministic choice):

| Reference | Success (infeasible) | Unnecessary repairs |
|---|---|---|
| no-op | 0 | 0 |
| shortest | 0.092 | 0.97 |
| displacement | 0.092 | 0.97 |
| **analytic access** | **0.158** | **0.00** |
| verify-first (evaluator-only ceiling, mean 6.1 verifications / root) | 0.408 | — |

- **Decision categories** (D, 345 root × seed decisions): 103 correct no-op, 62 success, 135 no repair available, 15 missed (10 rejected
  by the penalty, 5 ranked below the no-op), 16 wrong repairs (8 X = 0, 8 Y = 0), 14 unnecessary repairs (10 of them still succeed: harmless
  but unneeded).
- **P13 / P14 failure modes are resolved within development.**
  - The universal edit bonus is gone: harmful-edit sign accuracy is 0.23 (B) vs 0.90 (D), and edited-Y AUROC 0.68 vs 0.94.
  - No-op over-confidence is reduced: Y0 AUROC 0.85 vs 0.93.
  - Certified order reasoning is now above chance: order concordance 0.71 vs 0.53 for the order-invariant control.
- **Travel:** on matched successes (roots where both arms succeed) D's witnessed J tracks DIRECT's and B's (figure 08). Travel-blind
  selection (γ = 0) raises D's success to 0.30 but its unnecessary repairs to 0.29, so the frozen γ = 0.05 trades success for safety.
  No method is credited for shorter paths that avoid necessary repairs.

## 4. Figures ([visualizations/approach_b/bxy_p17_v1/](../visualizations/approach_b/bxy_p17_v1/))

| Figure | Content |
|---|---|
| 01 | success vs unnecessary-repair frontier per arm (inner rule, P11.1 rule, travel-blind) with references, for outcome-blind, V2.1 and P-min |
| 02 | pre-declared paired contrasts (95% / Bonferroni 99%) |
| 03 | edit sign by transition (0→1, 1→0), edited-Y AUROC, Y0 AUROC (outcome-blind vs P-min) |
| 04 | reliability of P(Y) and p_succ |
| 05 | order concordance and omission sign |
| 06 | decision categories |
| 07 | success by verified K |
| 08 | witnessed travel on matched successes |
| 09 | 2D gallery of V2.1 K ≥ 2 roots: D's choice vs DIRECT's choice (teacher truth) vs the shortest verified repair with replayed relocation / connector / target witnesses |
| 10 | a measured certified order twin with P(X) from order-aware D vs order-invariant G |

## 5. Recommendation (single candidate, single challenger)

- **Candidate: D:XYQ-GEO-SYM.** It is the pre-declared primary and met IMPROVES_WITHIN_GUARDRAIL and SUPERIOR_TO_DIRECT in development.
- **Challenger: E:XY-UNC-SA-GEO-SYM** (no coupling). The coupling did not meet its frozen criterion. E has the best joint NLL, the lowest
  ECE and the fewest unnecessary repairs, at −0.048 success.
  - **Deployment recommendation:** prefer E (the simpler model) unless the independent confirmation shows D's coupling advantage.
  - Coupling evidence is preserved, not deleted.
- **Matched DIRECT-GEO** is retained as the confirmatory baseline, and the analytic-access rule as a non-learned reference.

## 6. Files

- **Code:**
  - [bxy_p17.py](../bxy_p17.py) — design, arms, GEO2 / SYM, rule choice;
  - [bxy_p17_data.py](../bxy_p17_data.py) — leakage-separated views of all corpora, access features;
  - [bxy_p17_run.py](../bxy_p17_run.py) — the runner (a P14-runner copy plus the Runner17 validator);
  - [bxy_p17_eval.py](../bxy_p17_eval.py);
  - [bxy_p17_viz.py](../bxy_p17_viz.py);
  - [tests/test_bxy_p17.py](../tests/test_bxy_p17.py) — label-free new-corpus views, results invariance of scorer views, SYM directions,
    matched capacity and order invariance, shared-Y invariance to appended X, six-step prefixes, guardrail rule choice, fold custody,
    travel only on complete successes, geometry-only reference.
- **Artifacts:** [EVALUATION_P17.json](../runs/approach_b/bxy_p17_v1/EVALUATION_P17.json), per-run `RESULT.json` / `predictions*.json`
  / `history.json` with file hashes, `LEDGER.json`, `quarantine/`. Checkpoints `best.pt` are git-ignored, and their sha256 values are in each
  RESULT.json and in P18's FROZEN_MODELS.json.
- **Regression:** see §7.

## 7. Regression

Recorded in `runs/approach_b/bxy_p17_v1/regression/`:
- full suite: **703 passed, 1 skipped** (P18 tests excluded because they belong to the next gate);
- six archived replays: all exit 0;
- frozen-artifact hash guard: clean.

STOP (gate P17).
