# 0024 — P8a: decisive joint-coupling audit and matched comparison (saved evidence only)

**Actual result.** On saved P4–P7 evidence, generic **within-scene** coupling (B-full / B-quadratic) predicts fixed-robot
intervention outcomes and κ clearly better than the same model with only structured pairs (B-structured), with no
cross-outcome terms (B-none), or the feature-matched factorized non-energy control (SF).

- Paired by seed, B-full beats B-structured in **6/6** seed × split pairs on scene NLL (−0.21 to −0.38) and κ MAE
  (−0.09 to −0.26). This holds at every one of the four matched grid configurations.
- The **higher-order residual hurts conditional consistency**. With zA and zB revealed, B-full's zAB NLL is 1.45 / 1.71,
  against 0.02 / 0.09 for B-quadratic. **B-quadratic is the best arm overall.**
- **Repair-feasibility gains are small** (+0.006 to +0.062 accuracy; AUROC differences ≤ 0.03).
- **Under 50 % hidden auxiliary labels the coupling advantage disappears**: B-full degrades sharply.
- All evaluation roots were examined in P6 / P7 (**legacy diagnostics, not fresh tests**). The κ denominators are tiny
  (validation 2 / 2 / 4 roots for −1 / 0 / +1; legacy test 2 / 2 / 3).

**Gate:** `runs/p8/P8A_GATE.json` → **`P8A_ENGINEERING_PASS`** (10/10). Scientifically, generic coupling has
**INCONCLUSIVE-POSITIVE** value for intervention prediction (historical evidence only); repair value is
**NOT_SUPPORTED** at this resolution.

- Revision: P8 work started from `1154314`; this report is committed with P8a code.
- Previous turn sync: `1154314`.

## 1. Audit (`runs/p8/audit/`)

- **Evidence:** all 8 historical manifests are intact. The P7 recount from saved records matches report 0023 exactly
  (269 / 368 / 125 / 8 / 201; κ +1 ×16 operational, −1 ×5 certified, 0 ×7 (4 certified); 17 order contrasts;
  48 episodes).
- **Baseline:** full suite **316/316** and **6/6** replays, 591.4 CPU-s (guarded). P8 math and scope tests: **32 passed**,
  257.9 CPU-s (guarded).
- **Factor scopes** (`analysis.md`, `factor_mapping.json`, by controlled perturbation):
  - Unconditional scene beliefs P_S are moved only by scene logits, `pair_scene` (z0–zS), the scene-block generic pairs
    (`cpl`) and `ho_s`.
  - `pair_omit`, `ho_q`, `order_s` and the scene↔repair `cpl` pairs can move repair conditionals only, **never P_S**. This
    is guaranteed by the chain normalization P(z|r) = P_S(z_s|c0) P_Q(z_q|z_s, r).
  - So scene↔repair coupling cannot change κ; within-scene coupling can. **P7's "B-no-coupling" is `none`**, which also
    drops the structured pairs; it is not a test of generic coupling alone.
- **Engineering changes** (versioned, no semantic change to P7):
  - vectorized static BCE (|Δ| = 0.0);
  - an additive SF branch;
  - `abc8.py` (`ABC8_DIAG_V1`: arm builder, κ-balanced root sampler, SPARSE_AUX hash masks).

## 2. Design (predeclared in `p8_train.py`)

**Data.**
- Train: 94 roots (P7b train + P4–P6 history).
- Validation: 24 P7b validation roots.
- Legacy diagnostic: 24 P7b test roots.
- Training κ groups: **+1 ×25, 0 ×3, −1 ×1**, none ×65. Rare signs can be upweighted (clip 0.5–4×) but not created.

**Protocol.**
- **200 matched minibatch updates** of 12 roots, with identical batch sequences per seed for every arm.
- Validation outcome NLL every 20 updates; the best checkpoint is restored.
- Temperature fitted on validation only.
- Grid clip {1, 5} × λ_pool {0.25, 0.5} on seed 0 per arm. Chosen: B-full 5 / 0.5, B-structured 1 / 0.25,
  B-none 1 / 0.5, SF 5.
- A, B-quadratic and C-full use B-full's configuration; C-structured uses B-structured's.

**Regimes.**
- FULL_DECIDED: all decided labels.
- SPARSE_AUX: 57 auxiliary scene / omission labels (50 %) hidden on training roots by hash. Identical masks for every
  arm; task labels never hidden; pools eligible only if complete after masking.

**Arms.**
- 3 seeds × both regimes: B-full, B-structured, B-none, SF.
- 3 seeds FULL only: B-quadratic, C-full, C-structured, A.

**Compute.** One guard, **6,342.2 / 7,000 CPU-s**, 0 teacher calls.

- Parameters: B-full 698 k, B-quadratic 616 k, B-structured 566 k, B-none 467 k, A 451 k, SF 351 k, C-full 715 k.
- CPU per run: about 108–170 CPU-s.
- Clip fractions: B-full 0.46, B-quadratic 0.52, B-structured 0.98, B-none 0.97, SF 0.37, A 0.30, C-full 0.48,
  C-structured 0.97.
- **Disclosure:** an accidental duplicate launch ran the first three grid runs twice in parallel for about 6 minutes
  before I killed it. The training is deterministic (identical validation losses: 0.373 / 0.336) and the guard accounting
  belongs to the surviving process only.

## 3. Results (FULL_DECIDED, mean ± sd over 3 seeds; first value validation, second legacy P7 test)

**(i) Unconditional intervention prediction and κ**

| arm | scene-bit NLL | κ macro MAE (by sign) | balanced κ-sign accuracy |
|---|---|---|---|
| **B-quadratic** | **0.039 / 0.092** | **0.130 / 0.283** | **0.92 / 0.78** |
| B-full | 0.116 / 0.169 | 0.277 / 0.380 | 0.72 / 0.61 |
| C-full | 0.078 / 0.102 | 0.209 / 0.263 | 0.78 / 0.72 |
| SF (factorized, edit-specific) | 0.280 / 0.294 | 0.359 / 0.539 | 0.67 / 0.52 |
| A | 0.362 / 0.314 | 0.398 / 0.461 | 0.67 / 0.44 |
| B-none | 0.399 / 0.331 | 0.390 / 0.436 | 0.69 / 0.61 |
| B-structured | 0.463 / 0.447 | 0.500 / 0.511 | 0.56 / 0.59 |
| C-structured | 0.420 / 0.382 | 0.498 / 0.515 | 0.50 / 0.56 |

**κ-sign accuracy by observed sign** (validation and legacy pooled, 3 seeds):

| arm | κ = −1 | κ = 0 | κ = +1 |
|---|---|---|---|
| B-quadratic | 0.67 | 0.92 | 0.96 |
| B-full | 0.50 | 0.50 | 1.00 |
| B-structured | 0.83 | 0.83 | **0.06** |
| B-none | 1.00 | 0.92 | **0.04** |
| SF | 0.33 | 0.50 | 0.94 |

Without within-scene coupling, complementarity (+1) is almost never predicted.

**(ii) Offline conditional completion — ORACLE-REVEALED DIAGNOSTIC, not a robot input**

Values are per-bit NLL (root-macro). Denominators: a: 8 / 7 roots (16 / 14 bits); b: 8 / 7 (8 / 7); c: 8 / 7 (40 / 38);
d: 8 / 7 (119 / 105).

| arm | a: reveal z0, zA → zB, zAB | b: reveal z0, zA, zB → zAB | c: reveal zR, zO[0] → other zO | d: reveal scene → zR |
|---|---|---|---|---|
| **B-quadratic** | **0.054 / 0.121** | **0.023 / 0.094** | 0.180 / 0.285 | 0.250 / **0.165** |
| B-full | 0.292 / 0.381 | **1.449 / 1.708** | **0.171** / 0.244 | 0.354 / 0.362 |
| C-full | 0.239 / 0.272 | 1.241 / 1.400 | **0.146 / 0.243** | 0.376 / 0.330 |
| SF (marginals) | 0.106 / 0.128 | 0.114 / 0.149 | 0.208 / 0.253 | 0.328 / 0.206 |
| B-structured | 0.556 / 0.496 | 0.545 / 0.535 | 0.291 / 0.282 | 0.305 / 0.278 |
| B-none (marginals) | 0.474 / 0.434 | 0.718 / 0.690 | 0.260 / 0.259 | 0.318 / 0.216 |

- The higher-order residual (B-full / C-full) makes conditionals over-confident and wrong once two scene bits are revealed.
- Removing it (B-quadratic) gives the best conditional predictions.
- With the true scene bits revealed (task d), no arm benefits clearly from scene↔repair coupling.

**(iii) Repair prediction / selection from the initial input only**

| arm | accuracy | AUROC | NLL | ECE | offline restricted-catalogue selection |
|---|---|---|---|---|---|
| B-quadratic | **0.929 / 0.913** | 0.976 / **0.973** | **0.195 / 0.194** | 0.046 / 0.052 | 0.37 / 0.76 |
| B-full | 0.916 / 0.911 | **0.977** / 0.963 | 0.199 / 0.257 | 0.065 / 0.077 | **0.60 / 0.76** |
| C-full | 0.910 / 0.913 | 0.972 / 0.959 | 0.219 / 0.257 | 0.064 / 0.069 | 0.53 / 0.67 |
| C-structured | 0.901 / 0.906 | 0.969 / 0.957 | 0.234 / 0.247 | 0.059 / 0.071 | 0.40 / 0.71 |
| A | 0.897 / 0.893 | 0.960 / 0.961 | 0.240 / 0.234 | 0.046 / 0.066 | 0.43 / 0.71 |
| B-structured | 0.885 / 0.877 | 0.952 / 0.953 | 0.264 / 0.251 | 0.049 / 0.060 | 0.47 / 0.67 |
| SF | 0.874 / 0.897 | 0.965 / 0.967 | 0.280 / 0.227 | 0.074 / 0.066 | 0.17 / 0.38 |
| B-none | 0.868 / 0.884 | 0.951 / 0.952 | 0.274 / 0.258 | 0.060 / 0.061 | 0.30 / 0.62 |

**Matched-configuration control** (seed 0, identical clip / λ_pool for B-full, B-structured and B-none, all four grid
configurations): B-full has the lowest scene NLL in **every** configuration (0.06–0.11 vs 0.28–0.46), so the scene
advantage is not a clipping artefact. Repair accuracy is **not** consistently higher: at clip 5 / 0.5, B-structured has
0.937 / 0.938 against B-full's 0.943 / 0.911.

**SPARSE_AUX** (3 seeds, validation / legacy):

| arm | accuracy | scene NLL | κ MAE | conditional b | conditional d |
|---|---|---|---|---|---|
| B-full | 0.864 / 0.829 | 0.457 / 0.516 | 0.626 / 0.556 | 3.11 / 3.87 | 1.35 / 2.48 |
| B-structured | 0.851 / 0.840 | 0.483 / 0.456 | 0.478 / 0.420 | 0.53 / 0.54 | 0.37 / 0.32 |
| B-none | 0.832 / 0.826 | 0.592 / 0.547 | 0.422 / 0.397 | — | — |
| SF | 0.795 / 0.820 | 0.661 / 0.570 | 0.605 / 0.617 | — | — |

With half of the auxiliary labels removed, generic coupling loses its advantage and becomes unstable.

## 4. Interpretation

- **Supported on historical evidence (inconclusive for generalization).** Within-scene generic pair coupling helps
  predict intervention outcomes and κ beyond structured pairs and beyond an edit-feature-matched factorized predictor.
  - The mechanism is consistent with the factor scopes: only scene-block coupling can represent zA–zB–zAB dependence.
  - The training data are κ = +1 heavy, and the evaluation roots were already examined. P8c's fresh κ-balanced roots are
    the real test.
- **Not supported.**
  - The higher-order residual: it damages conditional calibration.
  - Coupling as a route to better repair feasibility or selection: differences are small and mixed; A and B-structured
    are within noise on legacy selection.
  - Robustness to sparse auxiliary supervision.
- **Consequences for P8c and P8d.**
  - The contract fixes the P8c/P8d arms; B-full stays the coupled arm as specified.
  - **B-quadratic** is added to P8c training as an *optional, separately labelled* offline arm, because P8a identified it
    as the best variant. It does not replace any mandatory arm and does not run in P8d.

## 5. Artifacts

- **Code:** `abc8.py`, `p8_eval.py`, `p8_train.py`, `p8_audit.py`, `p8_gates.py`, `p8_viz.py`, `tests/test_p8.py`;
  `abc7_train.py` (vectorized static BCE, additive SF branch); `run.py` (P8 commands).
- **Evidence:** `runs/p8/audit/*`, `runs/p8/a_tests/*`, `runs/p8/a/{results.json, guard.json, log.txt, ckpt_*.pt}`,
  `runs/p8/P8A_GATE.json`.
- **Figures** (`visualizations/p8/`, SHA-256 sidecars, `index.json`):
  - `factor_graph_modes.png` (code diagram);
  - `coupling_conditionals.gif` (oracle-revealed diagnostic, labelled);
  - `kappa_signs.gif`;
  - `loss_gradient_balance.gif`.

**Accounting**

| item | used | cap |
|---|---|---|
| audit + regression + tests | 591.4 + 257.9 + ≈ 30 CPU-s | 1,200 |
| P8a training | 6,342.2 CPU-s | 7,000 |
| figures | 11.8 CPU-s | — |
