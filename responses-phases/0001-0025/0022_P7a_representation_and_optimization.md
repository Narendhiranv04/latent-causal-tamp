# 0022 — P7a: causal-representation repair, faithful five-factor audit, controlled optimization

**Previous turn sync:** `0006365` (P6). HEAD, branch `main` and `origin/main` were all `0006365` at the start. The
pre-existing dirty state was only the two tracked root-PDF deletions, which are untouched and unstaged.
**Authorization:** user message authorizing P7a and its gated P7b continuation, per
`instruction-phase-md/P7_Causal_Representation_Optimization_Diverse_2D_Evaluation_Execution_Contract.md`.
**Verdict:** **`P7A_PASS`** (machine-readable: `runs/p7/a_gate.json`, 10/10 checks). This is an engineering pass. It
does **not** establish that coupling is useful: the P6 corpus contains only κ = +1 roots (§6). **0 teacher / planner
calls** were made in P7a. P7b was started after this gate and is reported separately in 0023.

## 1. Read-only audit of the P6 implementation (`runs/p7/audit/`)

Full write-up: `runs/p7/audit/factor_mapping.md`. Truth table: `factor_truth_table.json`. The numerical trace
`p6_numerical_audit.json` (`p7_audit.py`) used frozen P6 checkpoints on frozen P6 roots p6_2026102301 and p6_2026102303.

| question | P6 finding (measured) | status |
|---|---|---|
| Q1 omission factor | `zO[t]` had a unary logit only; zR–zO[t] were linked only through the generic coupling W(r), and not at all without coupling | **SPEC_MISMATCH** → fixed |
| Q2 scene inputs | the pooled edited-scene vector differs from the unedited one by **0.04–0.23 %** relative L2; scene logits none/A/B/A+B agree to < 0.01 (B: 8.095/8.104/8.098/8.107) | **root cause of identical A/B/A+B predictions** → fixed |
| Q3 root scope | W(r) and φ_HO were conditioned on the repair summary, so on one root B's p(zS[A]) ranges **0.24–0.33** and p(z0) **0.003–0.28** across seven repairs | **inconsistent** → fixed |
| Q4 order factors | B prefix-pair without GRU; C GRU without prefix-pair; omissions use recomputed prefixes | correct |
| Q5 coupling switches | P6 no-coupling removed W and φ_HO | correct for P6; extended |
| Q6 five factors | static ✓, seq ✓, scene = unary only, omit = unary only, couple = all pairs; T·K·ln2 is a reference measure, not a learned factor; J is not a factor | named "P6 quadratic/logit parameterization" |
| Q7 V3 layout | K = 4..9, 512 states, aliases refused, inactive invariance, detailed balance at cap 4 | re-verified (tests) |
| Q8 invariances | — | tested for ABC7 (§2) |

Loss audit, measured before any change (P6 B at init, P6 training roots): the pool term was 7.44 nats with gradient
norm 8.82, against task 0.70 / 0.84, outcome 0.69 / 1.34, effect 0.45 / 2.33 and static 0.71 / 0.87. The pool term
summed over every (r, z) state of every fully decided candidate with no per-root or per-bit normalization.

## 2. What changed: versioned `ABC7_V1` (`abc7_models.py`, `abc7_train.py`)

P6 code is unchanged and P6 checkpoints still load strictly. `p6_scenes.plan` gained optional arguments; the P6 plan
hash `sha256:22f408cddd99…` reproduces exactly.

- **Edit-specific scene evidence.** Per-object channels `[moved, dx, dy, |d|, x0, y0]` are added to the object
  tokens. The edit vector pools all tokens, the moved tokens and the target token. Everything is computed from c0 and
  the declared edit; no post-edit image, teacher outcome, screen result or trajectory is used.
- **Root-consistent exact joint.** The chain normalization
  `E(r,z) = Ē_R(r) + [E_S(z_s) + T log Z_S] + [E_Q(z_q; z_s, r) + T log Z_Q]` gives
  `P(z|r) = P_S(z_s|c0) P_Q(z_q|z_s,r)`. Scene beliefs are therefore identical for every r of a root (test: < 1e-12).
  Scene↔repair coupling lives in E_Q, and `−T log Σ_z exp(−E/T) = Ē_R(r) = E_static + T softplus(−l_T)`, where l_T
  is the derived logit of P(zR = 1 | r).
- **Named factors.**
  - φ_scene: unary term + z0–zS[I] pair (context c0).
  - φ_omit: unary term on the recomputed omitted prefix + zR–zO[t] pair.
  - φ_couple: remaining pairs + φ_HO.
- **Coupling modes:** `full` | `quadratic` (no φ_HO) | `structured` (φ_scene/φ_omit pairs only) | `none` (no
  cross-outcome term at all; the joint equals the product of its marginals, test < 1e-12).
- **Methodology L_joint is kept exactly.** A test confirms the brute-force softmax over all (v, z) of the fully
  decided pool equals ranking CE + (−log P(z*|r)) to 1e-10.
- **Loss normalization.** Every term is averaged within a root over its independent units, then over roots. Scene
  outcomes are counted once per root. The joint z-likelihood is divided by its number of bits. No weight was chosen to
  favour an arm.
- **Matched supervision and a new control.** A and S receive the same scene-edit labels through re-scoring. S is a
  new supervised non-energy control: DeepSets over ideal-prefix tokens with a BCE head only.

**Tests** (`tests/test_p7_models.py`, 9 tests, all pass):
- 512-state normalization;
- brute-force equality of the joint-pool loss;
- root consistency across all coupling modes;
- each switch removes exactly what it names;
- B has `pairo` and no GRU, C the reverse;
- edit vectors pairwise distinct (> 0.05 relative L2) and permutation-invariant (< 1e-10);
- tiny-data overfit of three independent roots with **κ = +1, 0, −1** by B, C, B-no-coupling and A (all |p − y| < 0.25,
  κ̂ sign correct);
- order-swap sensitivity;
- finite-difference gradient.

## 3. Gates before training

- **Full suite + 6 archived replays:** 314 passed, 0 failed, 6/6 replays, **548.7 CPU-s** (cap 1,200, guarded),
  `runs/p7/audit/regression`.
- **Real-root micro-overfit** (`runs/p7/a_training/results.json → micro`): on p6_2026102301 and p6_2026102303, every
  decided field (18–141 per root) of B, C, B-no-coupling and A is fit with max |p − y| ≤ 0.0005, and κ̂ = +1.00 on both.
  Edit vectors are distinct at initialization (minimum pairwise relative L2 0.105).
- **A7 audit** (`runs/p7/audit/a7_place_certificate_audit.md`): **A7 stays disabled**. A definite collision at the
  exact goal centre carries no depth, the 2 mm tolerance does not map rigidly through IK, and no independent checker
  exists. Place-side negatives remain `BUDGET_INFEASIBLE`.

## 4. Controlled training on the frozen P6 corpus

**Setup.**
- **Guard:** one process-tree guard, **5,338.8 CPU-s** (cap 6,000), 0 teacher calls.
- **Data:** train = 30 roots / 183 candidates (P6 train + P4/P5 history); validation = 8 P6 validation roots.
- **Legacy diagnostic:** the 8 P6 holdout roots, which were already examined in P6 and were never used for any choice.
- **Grid** (predeclared, seed 0, chosen by validation outcome NLL): clip ∈ {1, 5} × λ_pool ∈ {0.5, 1}.
  - Chosen: A clip 5 / 0.5 (0.829), **B clip 5 / 0.5 (0.164)**, C clip 1 / 0.5 (0.560). Discarded settings are
    recorded in `results.json → grid`.
- **Optimizer:** AdamW lr 1e-3, wd 1e-4, early stopping on validation every 5 epochs (patience 8), ≤ 300 epochs, and a
  per-run CPU allotment. Temperature was fitted on validation only.

**Results** (calibrated, mean ± sd over 3 seeds):

| arm | split | accuracy | AUROC | NLL | ECE | κ MAE | κ sign | scene-effect MAE | omission-effect MAE | rank acc |
|---|---|---|---|---|---|---|---|---|---|---|
| A | val | 0.772 ± 0.113 | 0.876 ± 0.074 | 0.396 | 0.135 | 0.639 | 0.08 | 0.445 | 0.380 | 0.915 |
| **B** | val | **0.889 ± 0.032** | **0.978 ± 0.008** | **0.189** | **0.073** | **0.062** | **0.92** | **0.021** | **0.244** | **0.978** |
| C | val | 0.746 ± 0.027 | 0.862 ± 0.023 | 0.423 | 0.133 | 0.584 ± 0.650 | 0.50 | 0.198 | 0.418 | 0.932 |
| B-no-coupling | val | 0.852 ± 0.087 | 0.923 ± 0.044 | 0.306 | 0.084 | 0.920 | 0.00 | 0.470 | 0.329 | 0.915 |
| C-no-coupling | val | 0.730 ± 0.042 | 0.806 ± 0.037 | 0.479 | 0.129 | 0.807 | 0.00 | 0.539 | 0.442 | 0.847 |
| A | legacy P6 holdout | 0.778 ± 0.088 | 0.857 | 0.439 | 0.141 | 0.587 | 0.17 | 0.505 | 0.357 | 0.893 |
| **B** | legacy P6 holdout | **0.873 ± 0.016** | **0.961** | **0.284** | 0.096 | **0.116** | **0.92** | **0.039** | **0.254** | **0.973** |
| C | legacy P6 holdout | 0.741 ± 0.009 | 0.849 | 0.427 | 0.128 | 0.539 | 0.58 | 0.182 | 0.418 | 0.938 |
| B-no-coupling | legacy P6 holdout | 0.831 ± 0.009 | 0.917 | 0.367 | 0.107 | 0.910 | 0.00 | 0.445 | 0.336 | 0.928 |

For comparison, P6 B on the same holdout had accuracy 0.799 and scene-effect MAE 0.435.

**Secondary arms** (1 seed; validation | legacy holdout accuracy, κ MAE):

| arm | validation acc | holdout acc | κ MAE (val / holdout) |
|---|---|---|---|
| S (non-energy) | 0.905 | 0.889 | 0.09 / 0.10 |
| A-capacity (714,920 params ≈ C) | 0.683 | 0.698 | 0.75 / 0.73 |
| A-geometry | 0.825 | 0.762 | — |
| B-geometry | 0.889 | 0.873 | 0.00 / 0.06 |
| C-geometry | 0.905 | 0.857 | — |
| B-quadratic | 0.905 | 0.873 | 0.08 / 0.12 |
| B-structured | 0.873 | 0.873 | 1.12 / 1.10 |
| C-quadratic | 0.778 | 0.825 | 1.25 / 1.25 |

**Optimization diagnostics** (`results.json → runs[*].history / term_grads_final`):
- Per-term losses are now comparable in scale; at initialization the pool term is about 3 nats against about 0.2–0.7
  for the others.
- Clipping is **still frequent**:
  - B / A at clip 5: 26–70 % of steps;
  - C at clip 1: 91–100 % (C's grid chose clip 1);
  - pre-clip norms reach 10–30 late in training.
- Several runs ended on their CPU allotment rather than by early stopping (B: about 120 epochs).
- No non-finite events occurred.

## 5. Interpretation (what is established, and what is not)

- **Established (engineering):**
  - The representation bug is fixed. B's scene-effect MAE falls from 0.43 to 0.02–0.04, and edits A / B / A+B are
    predicted distinctly.
  - Scene beliefs are root-consistent by construction.
  - φ_omit is now an explicit pairwise factor.
  - The joint-pool loss no longer dominates.
  - All tiny-data capability tests pass, including κ = −1, 0 and +1 on independent synthetic roots.
- **Observed, but NOT established as a causal-coupling result:**
  - Full B (and B-quadratic, B/C-geometry) predict κ well, while **B-no-coupling and B-structured do not**
    (κ MAE 0.92 / 1.12).
  - Because every P6 root has the same pattern (0, 0, 0, 1), a coupled scene block can learn that **pattern prior**
    without understanding edits.
  - The non-energy control S, which has no coupling, also reaches κ MAE 0.09. The difference may therefore come from
    optimization rather than structure.
  - This is exactly what P7b's κ ∈ {−1, 0, +1} roots must test.
- **C** remains unstable across seeds (κ sign 0.50 ± 0.50; one grid configuration early-stopped at epoch 10).
- **A** is improved by edit-aware re-scoring but remains the weakest on effects.
- **Vision** gives no measurable gain at this scale.

## 6. Visualizations (`visualizations/p7/a/`, guarded 14.4 CPU-s, cap 700) — diagnostic renders, no robot execution

| file | what it shows |
|---|---|
| `scene_edits_A_B_AB.gif` | Fixed-robot edits none / A / B / A+B on two frozen roots: exact edited geometry with arrows, teacher outcome, and predicted root-level P(z = 1) for A, B, C, B-no-coupling and the P6 B checkpoint, with κ̂ per arm |
| `P7a_loss_gradients.gif` | A, B, C chosen runs: per-term loss curves, pre-clip global norm against the clip level with the running clipped fraction, and per-term unclipped gradient norms at snapshots |
| `B_C_coupling_ablation.gif` | Scene marginals and κ̂ over training for B, B-quadratic, B-no-coupling, C and C-no-coupling on p6_2026102303 |

SHA-256 sidecars sit beside each file. The index is `visualizations/p7/a/index.json`; all GIFs are listed in
`visualizations/README.md` after P7b.

## 7. Accounting

| stage | used | cap |
|---|---|---|
| static audit / tests / regression | 548.7 CPU-s regression (guarded) + ≈ 300 CPU-s audit script and unit tests (unguarded, no teacher) | 1,200 |
| controlled training and diagnostics | 5,338.8 CPU-s, 5,340 s wall, 0 teacher calls | 6,000 / 12,000 |
| GIF rendering | 14.4 CPU-s | 700 |

Checkpoints: the 23 reported-configuration checkpoints are committed. All 32 are hashed in
`runs/p7/a_training/checkpoint_manifest.json`; the 9 non-chosen grid checkpoints are not committed.

**Gate → P7b:** `P7A_PASS` permitted P7b. The configurations frozen for P7b are A: clip 5 / λ_pool 0.5,
B: 5 / 0.5, C: 1 / 0.5.
