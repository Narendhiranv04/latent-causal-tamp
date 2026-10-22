# P9 figures (no robot motion: P9 executed nothing)

| file | stage | what it shows |
|---|---|---|
| `P9_factor_instances.png` | L0 | Factor instances of a tiny root for B-full / quadratic / structured / none (circles = binary outcomes, squares = factor instances, dashed = observed context; one shared circle where an omission *is* another repair) |
| `P9_L1_exact_likelihood.png` | L1 | Exact evidence vs brute force on 167 saved roots; cost of untied copies; legacy copies vs one tied variable; which factor families each ABC9 term reaches |
| `P9_L2_nll_vs_legacy.png` | L2 | Exact root NLL and calibrated NLLs, P8 multi-loss vs ABC9 joint, per arm and seed |
| `P9_L2_gradient_health.png` | L2 | Per-factor gradient norms over ABC9 training (seed 0); median pre-clip norms vs P8 |
| `P9_L2_predictions_selection.png` | L2 | Reliability (seed 0), restricted-catalogue selection funnel, root-cluster NLL contrasts |

SHA-256 of each file: `index.json` and `<file>.sha256`. All test-split panels show the **disclosed** P8c test (a legacy diagnostic, not a fresh holdout).
Regenerate: `python p9_viz.py <factor_instances | l1_math | l2_nll | l2_gradients | l2_predictions>`.
