# R5.3 decision rules (written and committed before any R5.3 diagnostic was computed)

These refine `R5_PREREG.json` §R5_3. They are applied per domain, to the X model selected in R5.2. F0 is reported as a control.

## 1. Calibration

- Fit a temperature T on the X conditional logits (a / T, (a + w) / T) by grid search, minimising R5.1-VAL family NLL of marginal pX.
- **Use the calibrated model** only if VAL NLL improves by ≥ 0.005. Otherwise use the raw model.

## 2. Selection rule

The candidates are:

| Rule | Definition |
|---|---|
| S0 | Original rule: argmin E (named control) |
| S1 | Argmin E with the calibrated X (identical to S0 when T is not used) |
| S2 | Reliability-threshold shortest: among candidates whose reliability statistic is ≤ τ, choose the shortest (ties by E); otherwise fall back to argmin E |

- **S2 reliability statistic:** Σ_chunks −log pX for a long candidate; −log pX of its single chunk for L ≤ 3.
- **τ:** the 95th percentile of −log pX over **R5.1-VAL positive local labels with g ≥ 2**. This is local evidence only. It is not fitted on any K4/5 outcome.

**Choice:**
- **S2** if the model-only length audit of the chosen (raw or calibrated) model shows best-E non-increasing in size on ≥ 80% of DEV roots, which is the R4.0 over-long bias.
- Otherwise **S1** if calibration was adopted, else **S0**.

S0 is always reported alongside as a model-only control.

## 3. Admission (Fig. 3A)

The rules:

| Rule | Admit a non-empty temporary repair iff |
|---|---|
| A0 | Temporary pY after > temporary no-op pY (`beats_empty`) |
| A1 | Temporary pY after ≥ no-op pY + m |
| A2 | A1 and the group's temporary p11 ≥ 0.3 (production eta) |

**Evidence:** paired physical temporary-target interventions.
- **3D:** beneficial / irrelevant / harmful, from the R5.1 3D VAL families.
- The same family enters every rate's denominator.

**Choosing m:** the smallest m ∈ {0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3} with VAL false-admission (non-beneficial admitted) ≤ 0.20 and true-admission (beneficial admitted) ≥ 0.80. If no m meets both, choose the m minimising false + missed admissions on VAL.

**A2** is chosen over A1 only if it lowers false admission without reducing true admission by more than 0.05 on VAL.

**2D:** only beneficial and baseline labels exist (cage probes), so false admission cannot be measured. 2D keeps A0 unless the 3D-derived m is shown not to reduce 2D true admission by more than 0.05; it is reported as such.

## 4. Proposals

**GA (Fig. 3B) initial pool.** Keep S1 top-4 unless top-8 both:
- raises DEV witness-action recall in the GA pool by ≥ 0.10; and
- keeps the exact envelope on ≥ 50% of DEV roots with median model-only GA wall ≤ 120 s.

**REC (Fig. 3A) local proposals.** Adopt ANC64 (top-4 + the 4 most frequent of 64 ancestral draws on each hypothetical temporary scene) only if:
- DEV witness-action recall of the recursive union rises by ≥ 0.05; and
- median REC wall stays ≤ 60 s.

**UNIF** (top-4 + 4 uniform legal cells) is an exploration control only and never primary.

**2D cVAE recovery** (conditionally authorised) is triggered if the best frozen option recovers < 50% of 2D reference actions in the relevant pool. When triggered:
- it uses the existing TaskCVAE architecture and the original staged recipe from fresh initialisation;
- it adds local verified placements from TRAIN families (enabler relocations verified for their temporary task in their own starting scene; chunk ≤ 3);
- validation is family-disjoint, Y is frozen, and the production cVAE is untouched.

## 5. What R6 physical outcomes can never change

None of the choices above may be revisited after any R6 physical outcome.
