# R3.0 — Contract, readout and lineage audit

Baseline: `a4265ccf54` (R2.4). No earlier R3 work existed: there were no local or remote commits, no gvlab2 directory and no live process. Everything here ran on gvlab2 before any new local-X label, training run or comparison outcome was opened. The pre-registration is in `../R3_PREREG.json`.

**Verdict:** **PASS.** There were no contract errors, so the teacher, label and readout contracts are unchanged. The frozen 3D X error lies in the conditional execution logits, on states the training data never covered (blocked first grasps, crowded and intermediate scenes). It does not come from the pY mixture weight, from label noise or from the prefix contract.

## 1. Teacher and label contract (physical; sealed manifests `r30/parity_jobs_{3d,2d}.json`)

| Check | Question | Result |
|---|---|---|
| 3D DET (8) | Does an identical re-run of an archived chunked run reproduce x and the failing phase? 4 fail after ≥1 chunk, 2 fail in chunk 0, 2 succeed. | **8/8**, same phase |
| 3D HYP (12) | Does an h ≥ 1 label from a physically reached prefix reproduce from a hypothetical static start (ideal cell poses, q_ref)? 6 positives, 6 negatives. | **12/12** |
| 3D DER (6) | Does a derived continuous-prefix negative, run directly from the same start, fail at the same relocation? | **6/6** |
| 3D TRN (8) | Does an original v32 VAL X label (continuous S0 run) reproduce through `run_xb` with a single terminal boundary? | **8/8** (4 positive, 4 negative) |
| 2D DET (8) | Same as 3D DET, including 3 unresolved planner runs (`UNKNOWN_PLANNER`) | **8/8**; `UNKNOWN_PLANNER` is reproduced deterministically |
| 2D `x_query` = `x_chunked({m})` | (reused R1 fixture) | 3/3 |

What follows from these checks:

- **Ideal poses are a valid contract.** The canonical prefix scene the planner scores is physically equivalent to the reached prefix state on this sample.
- **Labels are deterministic** under the fixed teacher mode and seed.
- **Derived prefix negatives** are valid under the continuous-run contract.
- **Original and chunked labels match.** The original training X labels use the same contract as the chunked local labels: a continuous run plus the terminal connector.
- **Failure cause.** Of the 3D negatives, 10 of 12 failed with "no feasible side grasp" (relocation-phase grasp infeasibility).
- **2D unresolved labels.** Unresolved planner outcomes are deterministic budget outcomes. They stay excluded as negatives.

Cost: 3D 34 jobs / 0.213 CPU-h; 2D 8 queries / 0.019 CPU-h. There were no errors, censoring or retries.

## 2. Readout decomposition (frozen F0, `r30/readouts_{3d,2d}.json`)

The natural panel is the original v32 VAL X labels on non-exposed families: 3D 776 labels, 108 families; 2D 1,392 labels, 286 families. The hard panel is the R2.4 exact local chunk labels on the 20 exposed roots, used for diagnostics only.

AUROC is shown with family-cluster 95 % CIs.

| 3D | marginal pX | pX\|Y=1 = σ(a+w) | pX\|Y=0 = σ(a) |
|---|---|---|---|
| natural VAL, all m ≤ 3 | 0.882 [0.85, 0.92] | 0.876 | 0.867 |
| natural VAL, m = 1 | 0.669 (133/134 positive) | – | – |
| hard h = 0 | 0.668 [0.60, 0.73] | 0.636 | 0.676 |
| hard h ≥ 1 | 0.522 [0.45, 0.59] | 0.503 | 0.569 |
| hard h ≥ 1, m = 2–3 | 0.166 [0.06, 0.27] | 0.189 | 0.196 |

- **The mixture weight is not the cause.** Of 157 confident 3D negatives (label 0, pX ≥ 0.8), 144 have both σ(a+w) ≥ 0.8 and σ(a) ≥ 0.8. Only 13 are mixture-driven. Median pY on them is 0.013, so marginal pX ≈ σ(a). The fault is the execution logit itself. Conditioning on the true Y would not recover the ranking, and neither would monotone calibration, because the ranking is lost. ECE is 0.25 at h ≥ 1 against 0.04 on the natural panel.
- **Missing supervision.** The 3D training X labels almost never contain a blocked first relocation: natural VAL m = 1 has 133 positive out of 134. Every original X label starts at the original S0. Crowded and intermediate scenes, where every R2.4 failure occurred, are out of distribution.
- **Natural vs hard contrast.** The natural panel is competent: marginal pX 0.88, p11 vs z 0.90, Y 0.97. The deficit is specific to the hard local regime.
- **2D hard panel.** Marginal pX at h ≥ 1 is 0.736 [0.59, 0.85], but on 5 mixed families only. 17 of 18 confident negatives again have both logits high. This is still inconclusive.

## 3. Parameter dependency map (autograd on a real root; `r30/params_{3d,2d}.json`)

| Group | Modules | Parameters (3D) |
|---|---|---|
| X-only (gradient to a or w, none to b) | `act`, `pairo`, `mix`, `order_s`, `xy` | 247,170 |
| Shared X/Y | `enc`, `pooln`, `edit_proj`, `edit_head`, `ctxn` | 137,472 |
| Y-only | `scene` | – |
| Travel only | `cost`, `jt` | – |

This matches the instruction's F1 freeze set exactly. Freezing everything except the X-only modules leaves Y bitwise unchanged; the training code tests this.

Representation note, for R3.3 if it is needed: an action token is `act([enc(obj at current pose), enc(obj at destination), mean/max pool of the scene, t])`. `enc` sees only that object's own features and its relation to the base, goal and target. Neighbouring bodies reach a token only through a permutation-invariant pool. So "is this object's side grasp blocked by a specific neighbour" has no direct input path.

## 4. Search-side checks

- **Order DP.** It equals brute force on m = 4 and 5 (R2.4 `tests/test_r24.py`, 19 tests, rerun in the R3 suite). Exactness is claimed only for the additive canonical-prefix cost under the default constraints.
- **GA shortlist truncation, independent of X** (`r30/shortlist_3d.json`). The verified witness set is in the refreshed union pool on 12/20 roots. On those roots its Y_global ranks 349 to 11,897 among 4,417–45,364 same-size sets, because Y_global saturates near 1 for thousands of sets. The Y-only top-4 shortlist can therefore essentially never keep it. This is a declared R3.5 bottleneck, separate from X.

## 5. Lineage and splits (`r30/lineage_{3d,2d}.json`)

- **DEV lineage.** It covers the 20 K45 roots, their K4 parents and their historical parent families. In 3D it shares 44 original TRAIN rows (dropped from replay and new data) and 6 VAL rows. In 2D it is the 20 R2.3/R2.4 roster roots plus their families: 37 VAL rows.
- **Diagnostic exposure.** These are roots with any R1/R2/R2.4 physical query: 42 roots / 23 families in 3D and 96 / 71 in 2D. They are excluded from TRAIN_SCALE and VAL_SCALE.
- **Clean eligible pool.**

| Domain | Split | Roots | Families |
|---|---|---|---|
| 3D | TRAIN | 1,722 | 861 |
| 3D | VAL | 338 | 177 |
| 2D | TRAIN | 3,492 | 1,571 |
| 2D | VAL | 656 | 516 |

- **Original split is family-pure.** In 3D, 871 families are TRAIN-only, 185 are VAL-only and none is mixed. TRAIN_SCALE and VAL_SCALE are therefore family-disjoint by construction.
- **Production scorer.** It is arm D seed 0, trained on `abf_v32_fb0eef4f5ff433ee`. Replay and the natural panel use that snapshot.

## Figure

`figures/R3_0_audit.png`:
- (a) X readouts on the natural vs the hard panel.
- (b) σ(a) vs σ(a+w) on the hard panel.
- (c) The witness set's Y_global rank vs pool size.
