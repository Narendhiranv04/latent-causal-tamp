# P13 — 2D factor scientific decision

**Overall: PARTIAL.** Engineering passes. Order representation, DINOv2 vision and keyed B's strict-TOP1 selection are supported. F5 coupling and F4 are conditional. F3, learned F1, keying and the D pair term are negative. J and F5q are underpowered.

**Evidence base:**
- 370 new roots; the freeze and the hash-committed labels were pushed in order (`c975629` → `4da8ca2`).
- Blind challenge set (mechanism-conditioned case-control): 122 roots.
- Natural stream: 48 roots.
- Matched retraining: 3 seeds, with parameter-matched off arms.
- Strict TOP1 on 129 roots.

| component | implemented | learnable | incrementally useful (preregistered) | deployment useful (strict TOP1) | decision |
|---|---|---|---|---|---|
| F1 learned static | PASS | **FAIL** (held-out AUROC 0.535) | calibration only (+3.93 log-loss vs off); no discrimination | NOT_APPLICABLE (veto 0, path never reached) | **NOT_IDENTIFIED → drop; keep the analytic veto** |
| F2 order | PASS | PASS (accuracy 1.00) | **PASS**: +0.779, Holm 3e-8 (natural: 2 roots) | **PASS**: +0.421; natural +0.222 | **SUPPORTED_CONDITIONAL** (any order representation; a GRU suffices) |
| F3 scene pair | PASS | — | **FAIL**: −0.023, Holm 0.030 reversal; triples −0.062 | n.s. (+0.026) | **HARMFUL (negligible) → drop** |
| F4 omission pair | PASS | PASS | **FAIL**: +0.014 < 0.05 threshold; natural −0.61 | **PASS**: +0.209; natural +0.111 | **DEPLOYMENT-ONLY (via admission) → keep provisionally, re-test** |
| F5s generic coupling | PASS | PASS | challenge **+0.175**, Holm 1.7e-7, but natural **−1.14**, which fails the safety rule | challenge +0.362; natural +0.063 (n.s.) | **CONDITIONAL; NOT SUPPORTED under the prereg (natural-mix harm)** |
| F5q higher-order | PASS | partial (triples) | secondary +0.060 on triples (Holm 0.022 secondary); Δ error n.s.; Δ = −1 class not constructible | not executed | **UNDERPOWERED → defer** |
| DINOv2 vision | PASS | PASS | secondary +0.194 (challenge) / +1.12 (natural) | not executed | **SUPPORTED (secondary) → keep** |
| keying | PASS (erratum: differs on every root) | — | secondary: unkeyed better (−0.032 / −1.00) | not executed | **NO_BENEFIT → simplify** |
| J travel | PASS | — | 15 roots; regret 0.21 vs 0.30 (n.s.) | success n.s. | **UNDERPOWERED → optional tie-break** |
| D pair term | PASS | — | blocker F1 +0.012 (n.s.) | — | **NO_BENEFIT → D-pairless** |
| D overall | PASS | PASS | feasibility ≈ A / SF (AUROC 0.98); blocker F1 0.892, best but ≈ B | — | **identification only; equivalent to B-derived masks** |

**Approaches:**
- **Strict TOP1** (129 roots):

  | approach | success |
  |---|---|
  | keyed B | 0.734 |
  | geometry-only | 0.612 |
  | C | 0.579 |
  | A | 0.558 |
  | SF | 0.318 |
  | *G+M (separate protocol)* | *0.783* |

- **P12 (80 roots, completed):** geometry 0.838 > B 0.629.

**Main risk carried forward:** every coupled model is badly miscalibrated on the realistic natural mix, where most originals are feasible. Generalization to unseen mechanism families failed in P12.

**Next decision:** do not port the full joint factor graph to 3D. The minimal model is order representation + DINOv2 + scene unary + generic pairwise coupling, trained on a realistic distribution that includes feasible originals, with the analytic veto. F3, learned F1, keying and the D pair term are dropped. F4 and higher-order terms are re-tested only with matched admission calibration and adequate triple data.
