# 0060 — P13-1: factor source paths, mathematics and activation audit

**Previous turn sync:** P13-0 pushed as `719493e61a2a5d7a35bb25ec5bc24d9bd3ad102f`.

**Actual result.**
- **Gate:** `runs/p13/P13_1_GATE.json` → **PASS** (implementation).
- **Implementation:**
  - every named factor is wired into its intended root-scoped energy;
  - the energy split by factor reproduces the model's instance energies to 1.4e-14;
  - each retrained ablation removes only its own term;
  - keyed inference matches brute-force enumeration;
  - gradients from the real training loss reach every factor present;
  - scoring makes 0 physical calls.
- **13 / 13 tests pass:** `tests/test_p13.py`.
- **Two factors have no live decision path on the current benchmarks:**
  - **F1 learned static validity:** the analytic veto fires on 0 candidates, and learned F1 reaches TOP1 only through the fourth sort key, which no tie ever reached (0 of 435 frozen B choices).
  - **Keying:** it changes the factor graph on 27 of 100 P10b blind / validation roots and **0 of 80** P12 roots.
- **κ error does not test joint factors.** κ is a linear function of four marginals, so a model with independent outputs can represent κ = +1 exactly. In keyed B, F3 is the z0–zS pair, while edit–edit interaction lives in the F5 scene–scene pairs and the scene HO term, which B-F3 keeps. **P13's primary F3 / F5 endpoints therefore include the joint four-bit likelihood under P_S**, not κ error alone.
- **Implementation only:** none of these findings shows that a factor is useful.

## 1. Source-to-equation map (keyed B = `ABC9K_KEYED_V1`, frozen P10c checkpoints `F-*-s{0,1,2}`; T = 1)

**Root model:**
P(z_S, x | c₀, catalogue) = P_S(z_S | c₀) · exp(−E_Q(x, z_S)) / Z(z_S)
- z_S = (z₀, z_S[A], z_S[B], z_S[A+B]) are the fixed-q0 scene outcomes.
- x are the distinct ordered-repair variables.
- There is one normalizer per scene state.

**Scene block** (`abc7_models.ModelBC7.scene_block`; once per root):
E_S(z) = −Σᵢ sᵢ zᵢ − ½ zᵀ (W_F3 + W_F5) z − HO_s(z)

**Repair self-block** for each distinct sequence query q (`unique_factor_keyed.instances`):
E_q = −s_q x_q − ½ (z_S, x_q, x_{q∖t})ᵀ (W_F4 + W_F5) (…) − HO_q

| component | exact source | equation term | where it acts |
|---|---|---|---|
| scene unary | `scene` MLP on `scene_vec` (edit-aware tokens), context `ctxn(c₀)` | −sᵢ zᵢ for z₀, z_S[A], z_S[B], z_S[A+B] | P_S |
| **F3** scene pair | `pair_scene` in `_pairs(..., "scene")`, symmetrized | −½ w(z₀, z_S[e]) z₀ z_S[e], one per edit | P_S |
| **F5** generic pair | `cpl` in `_pairs(..., "couple")` | z_S–z_S pairs (P_S); scene–query pairs (a, x_q) with context g_q; z_O–z_O pairs | P_S and E_Q |
| **F5q** HO residual | `ho_u`, `ho_s`, `ho_q` | −ho_s([Σ z_k ho_u(v_k), c₀]); −ho_q([Σ z_k ho_u(V_k), g_q]) | P_S and E_Q |
| **F2** order | `actions(ordered=True)` (prefix-scene tokens with step index) + `pairo` / `mix` predecessor terms + `order_s` | s_q = order_s([g_q, scene_vec(final)]) | unary s_q, context g_q |
| **F4** omission pair | `pair_omit` | −½ w(x_q, x_{q∖t}) for omissions that are themselves variables | E_Q |
| **F1** static | `Shared.static`: `unary`, `pairh` → E_static | outside P(z \| r); BCE with λ_static = 1 (`unique_factor.losses`) | 4th TOP1 key `energy` = E_static + T softplus(−u) |
| **J** travel | `cost` on g | outside P(z \| r); log-Huber vs witnessed travel | 2nd TOP1 key (after move count) |
| **DINOv2** | frozen DINOv2-small mask-pooled features → `vproj` (384 → 32) → `enc` | every token | all heads |
| **keying** | `unique_factor_keyed.instances` vs `unique_factor.instances` (B-U) | factor set is a function of the distinct physical variables only | E_Q instantiation |
| **D** | `d_blockers.ModelD`: `feas` (u), `unary` (a), `pairf` (w) | P(y₀); P(b \| y₀ = 0) ∝ exp(aᵀb + ½ bᵀwb) | identification only |

**TOP1 rule** (`p10_protocol.top1`, `p9_l3c.deployed`):
- **Admission:** σ(logit(p)/τ) ≥ thr, from the prior marginal p, and not vetoed analytically.
- **Order of keys:** (moves, J_pred, C_d analytic, energy, id).
- **Consequence:** F1 can decide only when moves, J and C_d tie exactly.

**What each ablation removes** (an exact parameter diff against K-B; `FACTOR_AUDIT.json`):

| arm | removed modules | parameters | Δ vs K-B (698,154) |
|---|---|---|---|
| B-F3 | `pair_scene` | 648,745 | −49,409 (−7.1 %) |
| B-F4 | `pair_omit` | 648,745 | −49,409 (−7.1 %) |
| B-F5q | `ho_u`, `ho_s`, `ho_q` | 615,592 | −82,562 (−11.8 %) |
| B-F5s | `cpl` + HO | 566,183 | −131,971 (−18.9 %) |
| B-F2 | `pairo`, `mix`, and the prefix-scene token path (`ordered=False`) | 599,338 | −98,816 (−14.2 %) |
| B-V0 / B-U | none (zeroed visual input / unkeyed instances) | 698,154 | 0 |
| K-C | `pairo` / `mix` → GRU | 714,922 | +16,768 |

Every factor ablation is confounded with a capacity loss. **P13 adds parameter-matched controls** (§4).

**B-F2 removes two order paths:** the predecessor module *and* the order-dependent prefix encoding. "F2 necessary" therefore means all order information, not `pairo` alone.

## 2. Mathematical tests (`tests/test_p13.py`, 13 / 13 pass, 121 s)

1. **Exact energy split:** the per-factor energies sum exactly to the scene-block and keyed-block energies, for K-B, K-C, B-F3 and B-F5s on real roots. Maximum error over all audited roots: 1.4e-14.
2. **Ablation isolation:** load full-B weights into each ablation. B-F3, B-F4, B-F5q and B-F5s change **only** their own term, which becomes exactly 0; every other term matches to 1e-12. B-F2 leaves the scene block bit-identical.
3. **Normalization:** keyed `log_evidence` equals brute-force enumeration (< 1e-8), with no labels, one label and two labels.
4. **Symmetry and duplicates:** pair matrices are symmetric. Re-listing modelled multi-move candidates leaves keyed prior marginals unchanged (< 1e-12).
5. **B / C identity:** B and C produce the identical P_S when they share weights.
6. **Gradient reach:** one backward pass of the real keyed objective (NLL + static BCE + J) on a labelled validation root reaches every factor group present in K-B, B-F3 and B-F5q.
7. **No physical calls** (IK / collision / screen / planner / teacher) in `deployed` scoring.
8. **κ estimand:** the preregistered seed-mean error is distinct from, and never larger than, the seed-wise mean (cancellation example).
9. **Strict lattice:** identity holds on a real P12 root and fails when an edit dict is perturbed.

## 3. Activation on real roots (frozen K-B s0)

**Counts are summed over roots; the number of roots with ≥ 1 instance is in brackets.**

| factor (instances) | P10b train (284) | P10b validation (35) | P10b blind (65) | P12 holdout (80) |
|---|---|---|---|---|
| scene bits (z_S) | 577 [190] | 105 [35] | 195 [65] | 240 [80] |
| F3 z₀–z_S pairs | 577 [190] | 105 | 195 | 240 |
| F5 z_S–z_S pairs | 591 [190] | 105 | 195 | 240 |
| sequence variables | 1,853 | 269 | 527 | 1,200 |
| multi-move variables (F2 opportunities) | 1,205 | 192 | 386 | 960 |
| same-endpoint reversed-order variable pairs | 546 [164] | 126 [26] | 258 [51] | 1,440 [80] |
| F4 x_q–x_{q∖t} pairs | 2,671 [190] | 399 | 799 | 2,400 |
| F5 scene–query pairs | 7,452 | 1,076 | 2,108 | 4,800 |
| F5 z_O–z_O pairs | 2,003 | 308 | 629 | 1,920 |
| F5q HO instances | 2,137 | 304 | 592 | 1,280 |
| D pair instances (pool ≥ 2) | 150 [80] | 65 [35] | 128 [65] | 240 [80] |

Every factor is structurally active on every labelled root with scene bits; 94 historical P8 / P10a training roots have no scene bits. Structural presence is not evidence that an interaction occurs: the P12 four-tuples are 91 % κ = 0.

**Magnitude:** the standard deviation of each term's energy across outcome states, in units of T (K-B s0).

| term | P10b blind | P12 holdout |
|---|---|---|
| scene unary | 6.37 | 4.02 |
| **F3** | 4.94 | 4.93 |
| F5 scene–scene | 1.08 | 1.11 |
| HO scene | 3.14 | 2.41 |
| F4 | 1.52 | 1.85 |
| F5 scene–query | 3.29 | 1.11 |
| F5 omit–omit | 1.03 | 0.40 |
| HO block | 6.29 | 3.44 |

Every term moves log-probabilities by several nats, so none is inactive in magnitude. Large weights are not utility.

**Gradient norms** (real objective, 12 labelled validation roots, s0), keyed B: F1 0.017, F2 1.03, F3 0.19, F4 0.50, F5 1.68, HO 2.37, J 0.087, scene 0.72, vision 14.1. Every ablation also has non-zero gradients on all its remaining groups. In a randomly initialized D, `pairf` receives gradient (1.65).

**Keying:** the keyed and unkeyed factor sets differ on 18 / 65 P10b blind roots and 9 / 35 validation roots, but on **0 / 80 P12 roots**. On P12, B-U and B are the same model up to training differences.

**Decision influence** (TOP1 recomputed with frozen checkpoints; it reproduces every frozen non-abstaining choice: B 165 / 195 and 219 / 240):

| | P10b blind (195 choices) | P12 holdout (240) |
|---|---|---|
| analytic veto fires | **0 candidates** | **0 candidates** |
| B: J active (≥ 2 admitted at the minimum move count) | 30 | 105 |
| B: **J changes the choice** | 18 | 86 |
| C: J changes the choice | 15 | 79 |
| B-F3: J changes the choice | 44 | 80 |
| F1 energy key reached (exact moves / J / C_d tie) | **0** (every arm) | **0** |

- **F1's deployment test** is NOT_APPLICABLE on these catalogues, because its only TOP1 path is never reached. F1 can only matter through shared representation learning, which the matched λ_static = 0 retrain tests on static-validity prediction.
- **J** decides 9–36 % of B choices, so its travel effect is testable.

## 4. Exploratory joint four-bit likelihood (`JOINT_SCENE_NLL_EXPLORATORY.json`; post-hoc, frozen models, no fitting)

Mean −log P(observed z₀, z_S[A], z_S[B], z_S[A+B]) under each model's P_S, against the product of its own marginals:

| cohort | B joint | B product | B-F3 joint | B-F5s joint | B-F5q joint | A | SF |
|---|---|---|---|---|---|---|---|
| P10b blind (39; κ +1: 11, 0: 24, −1: 4) | **1.147** | 1.227 | 1.226 | 1.167 | 1.248 | 1.320 | 1.682 |
| P12 holdout (65; κ 0: 59) | 2.305 | **1.929** | 1.864 | 3.226 | 2.503 | 3.336 | 3.978 |

**P12, paired** (positive means the second model is better):

| contrast | difference | 95 % CI | p | reading |
|---|---|---|---|---|
| B product vs B joint | −0.376 | [−0.587, −0.180] | 0.006 | coupling hurts |
| B-F3 vs B | −0.441 | [−0.845, −0.014] | 0.006 | F3 hurts |
| B-F5s vs B | **+0.921** | [0.432, 1.42] | 0.006 | F5 coupling **helps** |
| SF vs B | +1.67 | — | — | B better |

**P10b:**
- B joint is better than its own product by 0.080 [−0.006, 0.187], p 0.52.
- B vs B-F3 and B vs B-F5s: not significant.
- SF vs B: +0.535 [0.20, 0.90].

**Reading.**
- The joint terms change the joint likelihood substantially and in opposite directions: F3 hurts, F5 helps on P12.
- The sign depends on the cohort (complementary-rich P10b vs neutral-rich P12).
- This is exploratory and post-hoc; it motivates the P13 endpoints and confirms nothing.

## 5. Design consequences fixed for P13-2 / P13-3

1. **F3 and F5 primary endpoints:** the joint four-bit log-loss under P_S on proof-grounded four-tuples, stratified κ = +1 / 0 / −1. κ MAE (seed-mean estimand) and the false-interaction rate on κ = 0 are co-primary safety endpoints. The constant κ̂ = 0 control is always reported.
2. **Catalogues** score every parking subset, so A / B / C / SF attribution can be matched to D (0059).
3. **Parameter-matched "off" controls** for F3 / F5s / F5q: the removed parameters are restored by widening the scene head (`scene` MLP hidden width), and the exact counts are documented.
4. **F1** is graded on static-validity prediction only (λ_static on / off), with deployment NOT_APPLICABLE unless the new catalogue creates veto or tie opportunities.
5. **J** is tested on equal-move, admitted, feasible alternatives with different witnessed travel.
6. **Keying** needs catalogues that re-list modelled queries under several roles; otherwise it cannot be distinguished.

**Compute:** 122.2 CPU-s audit (ledger total for P13-0 and P13-1).
