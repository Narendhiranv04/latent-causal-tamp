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

## P9-L3 (unique-factor root model; saved data only)

| file | stage | what it shows |
|---|---|---|
| `P9_L3a_real_root_factor_graph.png` | L3a | Literal factor graph of saved root `p8_2026102510`: P9 PoE (a reused query gets one unary square per block) vs unique factor (one circle, one unary per physical query) |
| `P9_L3a_invariance.png` | L3a | Invariance cases for PoE / dedup-PoE / unique (B-full, B-structured, C-full), the duplicated 0.8 expert, PoE vs unique prior marginals by multiplicity |
| `P9_L3b_comparison.png` | L3b | Own exact root NLL, calibrated metrics and root-cluster contrasts for PoE vs unique B-full / B-structured / C-full, geometry-only, SF, A |
| `P9_L3b_health.png` | L3b | Per-factor gradients (PoE vs unique, seed 0), trained-model invariance, matched 400-update validation curves |

Each L3 figure also has `<file>.manifest.json` with SHA-256 of its input data and code. Regenerate with `python p9_l3.py job <name> "figures_l3a()"` / `"figures_l3b()"`.

## P9-L3c / L3d (factor semantics, visual control, freeze; saved data only)

| file | stage | what it shows |
|---|---|---|
| `P9_L3c_factor_graph_unique_vs_keyed.png` | L3c | Real root `p8_2026102510`: unique model (scene-query relations per listed parent / role, 36 instances) vs keyed model (one per physical scope, 20) |
| `P9_L3c_selection_and_calibration.png` | L3c / L3d | Max prior change per catalogue transformation (unique vs keyed, frozen weights; "sw" = deployed-selector switch among existing candidates) and validation calibration |
| `P9_L3d_visual_control.png` | L3d | Full-vision vs visual-zero B-full (same architecture), validation curves, grouped NLL, dominant roots and leave-one-root-out |

Each has `<file>.manifest.json` (SHA-256 of inputs). Regenerate: `python p9_l3c.py job <name> "figures()" 300 p9_l3d`.
