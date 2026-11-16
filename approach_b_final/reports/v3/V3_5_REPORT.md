# V3-5: retrained coupled scorer (D) and controls on matched evidence; validation rule tuning

**Hypothesis (plan §5.6, experiment E).** The coupled F2 / F3 / F5 model, retrained with the unchanged exact root-marginal X/Y NLL on base + V2 + V3-4 evidence, removes the overconfidence measured in V3-4 and restores ranking and abstention on the deployed candidate distribution.

## Training

- **Code and data.** Unchanged `xy.fit`: same architecture, same objective (exact observed-data root NLL with marginalisation of missing X / Y), and V2's hyper-parameters (60 epochs, batch 64, lr 1e-3, patience 10).
- **Snapshot and models.** Snapshot `abf_v3_e8a496bc66266fca`; arms D (coupled), E (F5 = 0), G (order-invariant) and DIRECT (binary-Z BCE), each with 3 seeds × 2 domains. Each fit takes about 40–70 s on the RTX 5090 with a peak of about 0.2 GiB.
- **Model selection.** Validation NLL on the base validation labels, as in V1 / V2.

## Held-out comparison on one shared labelled candidate set (`v3_5/HELDOUT_VAL_CANDIDATES.json`)

**The set.** Every physically labelled validation (root, ordered sequence) in the V2 and V3 verification caches; none were trained on.
- 2D: 5,511 candidates on 523 roots, Z rate 0.18.
- 3D: 3,411 on 303 roots, Z rate 0.40.

Most of these candidates were *selected by V2-scorer arms*. The set therefore measures whether a scorer corrects V2's confident errors, which is the relevant question, but it is a selected rather than a representative sample. Values are 3-seed means.

| Scorer | 2D NLL | 2D AUROC | 2D ECE | 2D mean p11 | 3D NLL | 3D AUROC | 3D ECE | 3D mean p11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V2 D | 0.917 | 0.741 | 0.364 | 0.546 | 0.734 | 0.838 | 0.200 | 0.603 |
| V2 E | 0.741 | 0.733 | 0.318 | 0.501 | 0.658 | 0.847 | 0.157 | 0.557 |
| V2 G | 0.535 | 0.800 | 0.203 | 0.386 | 0.596 | 0.815 | 0.109 | 0.507 |
| V2 DIRECT | 1.000 | 0.718 | 0.354 | 0.535 | 0.725 | 0.786 | 0.156 | 0.555 |
| **V3 D** | **0.474** | **0.845** | **0.183** | 0.365 | **0.509** | **0.862** | **0.105** | 0.503 |
| V3 E | 0.430 | 0.840 | 0.139 | 0.321 | 0.501 | 0.863 | 0.107 | 0.509 |
| V3 G | 0.381 | 0.862 | 0.105 | 0.287 | 0.503 | 0.845 | 0.067 | 0.449 |
| V3 DIRECT | 0.612 | 0.766 | 0.232 | 0.413 | 0.576 | 0.829 | 0.095 | 0.489 |

**Teacher-style validation labels** (`v3_5/xy_report_val_*.json`; the base validation set of selected-assignment orders):
- V3 D: NLL 0.536 / 0.415 (2D / 3D) and matched-endpoint **order accuracy 0.79 / 0.81**.
- E: order accuracy 0.80 / 0.82.
- DIRECT: order accuracy 0.78 / 0.77.
- **G: order accuracy 0.50 / 0.50.** The order-invariant model cannot rank executable vs infeasible orders of the same endpoint.

Findings:
- **Matched retraining roughly halves V2's NLL on the shared set** in 2D (0.92 → 0.47) and lowers 3D NLL from 0.73 to 0.51. ECE halves in both domains.
- V3 E and G have slightly lower held-out NLL than D. G's advantage comes with chance-level order discrimination.
- Per the plan, D stays the main model; the end-to-end D vs E / G / DIRECT comparison is part of V3-6.

## Stopping-rule tuning (validation `valsub`, physically verified; `v3_5/tune_*.json`)

**Procedure.**
- **Primary arm:** task cVAE `q2init_all` + S1, M = 4, B = 4,096, scored by V3 D seed 0. Candidates were stored once.
- **Grid:** the same 72-rule grid as V2, re-selected from the stored candidates (`construct gridslim`).
- **Verification:** the union of all rules' selections was physically verified: 2D 1,095 and 3D 833 sequences, 0 unverified.
- **Objective (V2's, unchanged):** the mean of task success (K1–K3), correct no-op (K0) and correct abstention (NONE). Ties go to the smaller mean move count.

| Domain | Frozen rule | Objective | Task | No-op | Abstain | Runner-up |
|---|---|---:|---:|---:|---:|---|
| 2D | gate 0.5, η 0.3, α 0, β 0, γ 0 | 0.770 | 49.4 % | 96.7 % | 85.0 % | gate 0.8: 0.735 (task 50.6 %, no-op 85.0 %) |
| 3D | gate 0.5, η 0.3, α 0, β 0, γ 0 | 0.797 | 76.3 % | 76.7 % | 86.2 % | β 0.1: 0.776 |

These are in-sample on the tuning roots, not final results. For orientation only, the valsub numbers of earlier pipelines are:
- old V2 iterative: 33.9 % (2D) / 51.4 % (3D), also in-sample for its own rule;
- task cVAE with the frozen V2 scorer: 3D abstention 38 %.

**Travel term.** γ = 0 again. The best rule with γ = 0.5 loses 15 task points in 2D (34.4 % vs 49.4 %). The V1 travel head is not a useful selection term here, so no travel benefit is claimed.

**The rules are frozen** in `v3_5/rule_{2d,3d}.json` (write-protected on gvlab2). V3-6 uses them without any change.
