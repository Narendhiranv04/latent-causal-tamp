# 0051 — P11-6: professor-ready 2D scientific closure

**Status of the whole 2D study: PARTIAL.**
- The engineering gates pass.
- The core P10 results survive code-level reconstruction.
- Several components are unsupported or unidentified.
- Execution-level length extrapolation fails.
- Constructor-disjoint generalization was **not** evaluated (P11-4 blocked).

## 1. What is established on this 2D benchmark

The 65 P10b blind roots were frozen before unsealing. Only P10's preregistered primaries are confirmatory; everything in P11 is post-hoc.

| claim | evidence | status |
|---|---|---|
| keyed B > SF, strict TOP1 executed success | 0.718 vs 0.385, +0.333 [0.226, 0.441], Holm p 7.8e-6 (exact recompute, 0045) | **confirmed** |
| keyed B > A, H1 complementarity κ error | 0.014 vs 0.277, 9 / 9 roots, Holm p 0.0117 | **confirmed** (9 roots) |
| keyed B > A and > geometry-only, executed TOP1 | +0.133 [0.077, 0.195]; +0.272 [0.128, 0.405] | supported (secondary) |
| C better than B | no endpoint; TOP1 identical; NLL +0.035 | **not supported** |
| B ≥ planner-assisted G+M | 0.718 vs 0.831; G+M better on 24 roots vs 8 | **not supported** |
| B cheaper than G+M per success | about 23.5 vs 24.2 CPU-s per success (`runs/p11/RESOURCES.json`) | **not supported** (about equal) |
| 3- / 4-move repairs executed (full-trained B) | H10_3 0.52, H10_4 0.78 (9 roots each); recorded witnesses | supported |
| length generalization of execution (trained ≤ 2) | short B 0.15 / 0.22 vs full 0.52 / 0.78, −0.46 [−0.63, −0.28] (0048) | **failed** |
| appearance robustness (H9, corrected) | B TOP1 changes on 77 % of roots under recolouring (0046) | **failed** |
| constructor-disjoint generalization | P11-4 blocked (0049) | **not evaluated** |

## 2. Component evidence ledger

| component | implementation | control | effect (95 % CI) | status |
|---|---|---|---|---|
| A (local GRU) | `abc7_models.ModelA7` | arm | TOP1 0.585 (vs B 0.718) | baseline, below B |
| B keyed joint Boltzmann | `ModelBC7('B')` + `unique_factor_keyed` | vs A / SF / geometry | P1 / P2 confirmed | **SUPPORTED** (this benchmark) |
| C (GRU order instead of predecessor) | `ModelBC7('C')` | vs B | 0 on TOP1 / order; NLL +0.035 | **NOT_BENEFICIAL** |
| F1 learned static head | `Shared.static` + static BCE | matched λ_static = 0 retrain | TOP1 −0.031 [−0.103, 0.041]; static AUROC 0.78 → 0.56 | **NOT_IDENTIFIED** for selection |
| F2 order (predecessor) | `_order` | B-F2 retrain | order −0.718; family-Holm p ≈ 0 | **SUPPORTED** |
| F3 scene pair | `pair_scene` | B-F3 retrain | H1 −0.143 (raw p 0.004; family-Holm 0.117) | **UNDERPOWERED** |
| F4 repair–omission pair | `pair_omit` | B-F4 retrain | no endpoint improved | **NOT_BENEFICIAL** |
| F5 generic coupling (+ HO) | `cpl` + HO | B-F5s retrain | H1 −0.099, NLL +0.033 (family-Holm 0.117 / 0.142) | **UNDERPOWERED** |
| F5 higher-order only | HO residual | B-F5q retrain | H1 −0.040 (family-Holm 0.117) | **UNDERPOWERED** |
| DINOv2 visual input | `vproj` | B-V0 (zero input) | NLL +0.089, family-Holm 0.0016; but TOP1 changes on 77 % of roots under recolouring | **SUPPORTED** for fit; **FAILED** invariance |
| keyed vs unique ontology | `unique_factor_keyed` | B-U | NLL +0.012 n.s. | **NOT_IDENTIFIED** |
| analytic static veto | `p10_protocol.static_veto` | — | vetoed 0 candidates on blind / H9 roots | **DIAGNOSTIC_ONLY** (never active) |
| J travel head | `cost` head + log-Huber | no-J / shuffled / oracle selection | tie-break on 6–20 / 65 roots; success within ±2 | **NOT_IDENTIFIED** (practically) |
| D feasibility | `d_blockers.ModelD` u-head | arms on the same 64 roots | perfect (4 / 60), NLL 0.005 | **SUPPORTED** (4 positives) |
| D blocker unaries + exact Z | a_i, exact 2^n | geometry heuristic | F1 +0.075 [0.007, 0.142] | **SUPPORTED** (vs heuristic) |
| D pairwise term | w_ij | D-pairless retrain | F1 −0.010 [−0.046, 0.038]; exact −0.089 | **NOT_BENEFICIAL** |

## 3. Proof strength and resources

**Labels:**
- κ and order use proof-grounded labels only (VERIFIED / CERTIFIED).
- NLL and omission include BUDGET (operational) zeros.
- FIRST_MOVER negatives are assignment-scoped placement-screen certificates.
- D 3- / 4-blocker masks are operational only.
- Minimality is catalogue-relative (SOUND for 10 H10_4 roots overall).

**Resources** (per blind root, including abstentions; `runs/p11/RESOURCES.json`):

| arm | total CPU-s | relocation plans | candidates physically tried | episode CPU when executed |
|---|---|---|---|---|
| B | 16.9 | 1.65 | 0.81 | 19.95 |
| G+M | 20.1 (4.4 pose-screen ranking + planning ≤ 5 candidates) | 2.11 | 1.20 | 15.7 |

G+M's mean executed-episode CPU is **lower** than B's. B is cheaper per root only because it plans one candidate and sometimes abstains.

**Reproducibility:**
- P10 artifacts are untouched.
- P11 outputs are versioned under `runs/p11/`.
- The final regression is in `runs/p11/regression/`; see the decision document for counts.

## 4. Visuals (`visualizations/p11/`, real data only)

- `P11_H9_two_palettes.png`
- `P11_length_executed.png`
- `P11_short_trained_long_success.gif` (recorded)
- `P11_short_trained_long_failures.png`
- `P11_D_vs_ABC.png`
- `P11_D_attribution_scenes.png`
- `P11_TOP1_outcome_classes.png` (G+M hatched)
