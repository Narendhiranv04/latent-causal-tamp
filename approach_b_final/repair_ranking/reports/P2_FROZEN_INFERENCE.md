# P2: inference-only fixes to the frozen scorer

**Outcome:** no P2 finalist. F0 (the frozen rule) stays.

Rules were pre-registered in `P2_PREREG.md` (`6756785fed`) before fitting. Results are in `P2_RESULTS.json` and `P2_FROZEN_RULES.json`, with the figure at `figures/p2_rules_cal_vs_audit.png`.

## Known-candidate ranking (within root, Z+ vs Z−)

Concordance is the within-root rate at which a verified success outscores a verified failure, averaged over roots. "Δ vs F0" is the paired difference in concordance against F0, with 95 % family-cluster bootstrap intervals.

| Rule (chosen on DEV_CAL) | DEV_CAL concordance | DEV_CAL Δ vs F0 | DEV_AUDIT concordance | **DEV_AUDIT Δ vs F0** |
|---|---|---|---|---|
| F0 frozen | 0.695 | – | 0.745 | – |
| F2: tier-conditioned logistic (C = 0.1) | 0.752 | +0.057 [+0.029, +0.087] | 0.733 | **−0.012 [−0.052, +0.024]** |
| F3a: + 0.25·prior | 0.763 | +0.068 [+0.013, +0.124] | 0.678 | **−0.068 [−0.143, +0.003]** |
| F3b: − 0.25·off-D4 fraction | 0.739 | +0.044 [+0.008, +0.081] | 0.736 | −0.010 [−0.055, +0.035] |
| F5: seed ensemble, mean − 0.5·sd | 0.745 | +0.050 [+0.017, +0.082] | 0.768 | +0.023 [−0.020, +0.066] |

F1 (global Platt calibration) is monotone, so its rankings and picks are identical to F0 by construction.

- **Every rule that improved DEV_CAL ranking failed to replicate on the family-disjoint DEV_AUDIT half.**
  - F3a, the DEV_CAL winner, is the worst on DEV_AUDIT.
  - It also failed the EXACT4-pool gate on DEV_CAL: decided success fell from 0.851 to 0.765. Re-weighting by the prior moves picks onto unlabelled sets and causes a net 5 harms against 2 rescues.
  - The selection-biased labelled candidates documented in P1 do not support a transferable tier correction.
- **F2 and F3b cannot change EXACT4 at all.** Every D4 action is in tier T4 with no off-D4 fraction, so these rules only act on pools wider than top-4.
- **The seed ensemble (F5) is the only rule with a positive DEV_AUDIT point estimate,** and its interval includes 0. It costs 3× the network evaluations, so it is not adopted.

## End-to-end selection with cached exact-contract labels

Unlabelled picks are unresolved, never counted as failures. Cells show decided successes / decided picks.

| Pool | F0, DEV_CAL | F0, DEV_AUDIT | Best rule, DEV_CAL | Same rule, DEV_AUDIT |
|---|---|---|---|---|
| EXACT4 | 80/94 (36 unres.) | 65/83 (27) | identical (F2, F3b) | identical |
| EXACT6 | 75/93 (37) | 66/82 (28) | F3b: 80/95, 4 rescues / 0 harms | F3b: 65/83, 0 / 1 |
| EXACT12 | 68/83 (47) | 49/64 (46) | F2: 74/90, 1 / 1 | F2: 55/71, 1 / 0 |
| F4 anchored (d12, δ = 0.02) | – | – | 75/87, 2 / 1 (27 of 53 changed picks unresolved) | 57/75, 1 / 1 |

## Selection and veto (registered rule)

- **Utility rules:**
  - The ranked winner was F3a@0.25.
  - It passed the concordance and top-1 gates on DEV_CAL but **failed the EXACT4-pool gate** (−8.6 pp), so it is not promoted.
  - DEV_AUDIT would also have vetoed it (concordance Δ −0.068).
- **F4:**
  - F4[d12]@0.02 formally met the registered DEV_CAL qualification. The margin was one net rescue, and 27 of its 53 changed picks were unresolved.
  - On DEV_AUDIT it did not replicate: decided success 0.760 vs 0.783, with 1 rescue and 1 harm.
  - The pre-registration says DEV_AUDIT "can veto", but its explicit triggers were written for utility rules. I applied the analogous trigger (DEV_AUDIT decided success below F0 and no net rescue) **as a disclosed judgement**.
  - F4 is kept only as a P5 model-only diagnostic.
- **The automatic output was retained** as `finalist_auto` in `P2_FROZEN_RULES.json`.

## Reading

- **H3 is not supported:** cheap calibration or prior-aware selection on the frozen scorer does not reliably prevent harmful off-pool replacements.
  - The rules can be tuned to fit one half of the labelled development data. They do not transfer to the other half.
  - A monotone calibration (F1) leaves rankings unchanged, as expected.
  - What remains is a ranking problem inside the model, which motivates the data and objective experiments in P3/P4.
