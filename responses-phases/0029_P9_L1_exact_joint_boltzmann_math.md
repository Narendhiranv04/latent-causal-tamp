# 0029 — P9-L1: exact, equality-aware joint Boltzmann root likelihood (math, proofs, tests)

**Actual result.** `ABC9_JOINTNLL_V1` (`joint_likelihood.py`) implements an **exact** masked observed-data root likelihood for the unchanged ABC7 factor graph. It is **not** a composite fallback.

- **Identity.** Every distinct physical query is one binary variable. Copies of one query in different repair blocks are tied by an explicit equality constraint, and `z0 ≡ zR[∅]`.
- **Exact computation.** The evidence is summed by exact variable elimination over the shared variables, batched over the 2^K_S scene states.
- **Checks on saved P8 structures:**
  - equals brute-force enumeration on **167** saved P8c roots (max |Δ log P| = **7.1e-15**);
  - normalization error ≤ **4.3e-15** on all 214 roots;
  - largest elimination scope **9** variables (cap 16);
  - cost per root-update **equal to or below** the P8 multi-loss.
- **Tests:** 26 new tests pass. The full suite passes **349/349** with **6/6** replays.
- **Gate:** `runs/p9/P9_L1_GATE.json` → **PASS** (12/12). Zero teacher calls.

Previous turn sync: `f9a6de0695d83699a2115d4898e5c78063852073`. L0 gate PASS (report 0028).

## 1. The model and why it is exact

**Notation.** For a root `c` with frozen catalogue `C`:
- scene variables `z_S = (z0, zS[I])`, at most 5 bits;
- one variable `x_q` per distinct **sequence** query occurring in any repair block (a repair's `zR`, or an omission `zO[r,t]` = the query of `r∖t`).

ABC7 already gives, for every repair, a conditional block `P_r(z_{Q,r} | z_S)` (exactly normalized, absent slots removed) and the root scene block `P_S(z_S)`. Let `σ_r` map r's slots to variables.

**The root model.**

```
P(z_S, x | c, C) = P_S(z_S) · Π_r P_r(x_{σ_r} | z_S) / Z_eq(z_S),      Z_eq(z_S) = Σ_x Π_r P_r(x_{σ_r} | z_S)
```

**Properties (proofs).**

1. **Normalized.** For each `z_S`, `Σ_x Π_r P_r / Z_eq = 1`, hence `Σ_{z_S,x} P = Σ_{z_S} P_S = 1`.
2. **Root-consistent scene beliefs.** `Σ_x P(z_S, x) = P_S(z_S)` for **any** catalogue. Scene marginals, and therefore κ, are identical to the ABC7 scene block. Scene evidence is charged once per root, however many repairs there are.
3. **This is the equality constraint the methodology asks for.**
   - Give every slot an independent copy `y_{r,j}`, with `Q(z_S, y) = P_S Π_r P_r(y_r | z_S)`.
   - Conditioning `Q` on the event "all copies of each query agree", *given* `z_S`, gives `Q(y | z_S, agree) ∝ Π_r P_r(y_r | z_S)·1[agree]`. This is exactly `P(x | z_S)` above.
   - So the model is the per-repair blocks as experts, conditioned on one physical outcome per query.
4. **No reuse → the guide's formula.** If no query is shared, `Z_eq = Π_r Σ P_r = 1`. The evidence is then `Σ_{z_S ⊨ y_S} P_S Π_r Σ_{z_Q,r ⊨ y} P_r`, Guide v2.0 §5.1 verbatim (test: identical to 1e-12).
5. **Observed-data likelihood.**
   - `log P(D_c) = logsumexp_{z_S ⊨ y_S}[log P_S + log N(z_S) − log Z_eq(z_S)]`, where `N` sums `Π_r P_r` over all unobserved variables consistent with the labels.
   - UNKNOWN / NOT_RUN labels are `None`: those variables are summed, never set to 0.
   - A root with no decided label gives `log P = 0` exactly and is excluded from the mean.
   - `N` and `Z_eq` are exact sums of products, computed by greedy variable elimination in log space; elimination order does not change an exact sum.
6. **`z0 ≡ zR[∅]`.** ABC7 has no `zR` slot for the empty repair; its success *is* `z0`. The implementation also ties any block slot carrying the `z0` query to the scene state (test with an explicit `zR[∅]` slot). Such a slot never occurs in saved data (L0).
7. **Static cancellation.**
   - Any energy `E_static(r)` that is constant over `z` adds the same term to every row of block r, so `P_r`, `N`, `Z_eq` and `P_S` are unchanged.
   - Hence `∂ log P(D_c) / ∂θ_static = 0` for parameters entering only `E_static`. The static unary/pair heads are trained only by the separate static BCE.
   - Likewise the travel head `J` is outside `P(z | r)` and is trained only by witnessed first-relocation travel (log-Huber). `J(∅) = 0` by construction.
8. **Objective (B/C)**, exactly as authorized:
   ```
   L = mean over roots with ≥ 1 observed bit of −log P(D_c)  +  1.0 · static BCE  +  1.0 · log-Huber travel J
   ```
   - The static BCE is over endpoint-deduplicated candidates and static checks.
   - Each auxiliary is averaged over the roots that have it.
   - A / SF have no joint z partition. They use the **factorized** root likelihood: the sum of Bernoulli log-losses over the **same** distinct observed queries (a test asserts identical label access), plus the same two auxiliaries.
   - Ranking stays success-conditioned: `E_rank(r) = E_static(r) − T_s log p_R(r)` (uniform ρ), with the P8 lexicographic comparator unchanged.

**Assumptions and consequences** (must accompany every claim):
- **(A1) Conditional independence.** Distinct repairs' outcome vectors are conditionally independent given `z_S`, except through shared physical queries. This is a modelling assumption, not a physical claim.
- **(A2) Experts.** Each ABC7 repair block is a conditional expert.
- **(C1) Product of experts.**
  - A query reused k times receives evidence from k blocks. Its ABC7 unary `φ_seq(q)` enters once per copy, because the omission unary is `φ_seq` on r∖t.
  - Root-model marginals therefore depend on *which repairs of the declared catalogue reuse the query*.
  - Legacy P8 checkpoints, trained as standalone experts, become over-sharp when combined. In `P9_L1_exact_likelihood.png` (c), the tied marginal often lies outside the range of the copies.
  - Models trained under this likelihood are calibrated *as a combination*.
- **(C2) Two prediction modes.** The single-candidate ABC7 `P(z | r, c0)` is the special case of a one-repair catalogue. For a frozen catalogue, the model's prediction is the root marginal; L2 reports both modes.
- **(C3) Alternative not implemented.** A single-normalizer root energy, with each factor instance once and no per-repair normalizers, is a *different* model and is not implemented. It is the natural L3 alternative.

## 2. Mandatory tests (`tests/test_p9_joint.py`, 26 tests; all pass)

| contract item | test(s) | result |
|---|---|---|
| 1 normalization (P_S, P_Q rows, product; K ≤ 9) | `test_normalization_and_scene_marginal` ×2; `test_real_root_normalization…` | errors ≤ 1e-12 (toy) / 1e-10 (real B-full) |
| 2 scene marginals invariant across r (different omission layouts) | `test_real_root_normalization_scene_consistency_and_aliases`; root model keeps P_S | ≤ 1e-12 |
| 3 root NLL = brute force (no reuse; then `z0 = ∅` and reused omission / full-repair aliases) | `test_evidence_equals_brute_force` ×6, `test_marginals_equal_brute_force…`, `test_empty_repair_slot_tied_to_z0`, `test_contradictory_copies_fail_closed` | ≤ 1e-10; equality-blind product differs (> 1e-3) only when queries are reused |
| 4 gradients: finite differences and signs | `test_gradients_match_finite_differences…` (scene unary, z0–zS pair, generic scene pair, scene HO, repair unary, zR–zO pair, generic repair pair, scene↔repair coupling, repair HO); `test_gradient_signs_of_unaries`; `test_real_directional_derivatives_per_factor_module` (`scene`, `pair_scene`, `pair_omit`, `cpl`, `ho_s`, `ho_q`, `order_s`, `mix` on a real root) | |AD − FD| < 1e-6 (toy), < 1e-5 relative (real) |
| 5 r-only offset cancels; static BCE / J reach their heads only; J(∅) = 0 | `test_r_only_offset_cancels…`, `test_real_static_gets_no_outcome_gradient…` | offset gradient ≤ 1e-14 (roundoff of an analytic 0); `unary`, `pairh`, `cost` gradient = 0 under the NLL |
| 6 UNKNOWN / NOT_RUN never 0; all-missing root; B vs C countable | `test_all_missing…`, `test_real_label_status_and_matched_label_access` | log P = 0 exactly; 0 violations |
| 7 order changes the representation; r∖t keeps the omitted object at its original pose in every prefix | `test_real_order_representation_and_omission_prefix` | reversed order: same endpoints, different `φ_seq`; every recorded prefix keeps the object at xy0 |
| 8 extremes / temperature, padding, no double scene charge, no ID / label leakage | `test_extreme_energies_and_temperature` ×3, `test_uncoupled_extra_slot…`, `test_real_no_leakage…` | finite at 1e3× energies; scene evidence identical for 1, 3, 6 repairs; scrambling key / split / labels / status leaves every table bit-identical |
| 9 real root smoke; benchmark; fail closed | real-root tests; `test_combinatorics_fail_closed`; §3 | `CombinatoricsError` above the cap |
| 10 P8 suite and archived replays | `runs/p9/l1/regression` | **349/349** passed (323 legacy + 26), **6/6** replays, 623.3 CPU-s |

## 3. Numerical artifacts on saved P8 structures (`runs/p9/l1`, 28.8 CPU-s)

| quantity | value |
|---|---|
| roots (P8c dev + disclosed test), legacy B-full seed 0 | 214 |
| roots verified against brute-force enumeration (≤ 10 sequence variables) | **167**, max |Δ| **7.1e-15** |
| max normalization error, any block | 4.3e-15 |
| largest elimination scope (cap `MAX_SCOPE` = 16) | **9** |
| roots with shared query variables | 108 |
| equality-blind product NLL − exact NLL (those roots) | mean **+0.77** nats, max +6.93, min −0.14; 67 % > 0.1 nat |

**CPU-s per root per update** (forward + backward, 12 training roots, seed-0 init):

| arm | ABC9 joint | P8 multi-loss |
|---|---|---|
| B-full | 0.026 | 0.027 |
| B-structured | 0.022 | 0.023 |
| B-quadratic | 0.024 | 0.027 |
| B-none | 0.020 | 0.021 |
| C-full | 0.027 | 0.029 |
| A | 0.018 | 0.020 |
| SF | 0.016 | 0.027 |

**Gradient reach** at initialization (`term_gradients.json`; figure panel d):
- **Joint NLL:** reaches **every** B/C outcome factor (`scene`, `pair_scene`, `order_s` / `pairo` / `mix` or `gru`, `pair_omit`, `cpl`, `ho_*`). It never reaches `unary`, `pairh` or `cost`.
- **Static BCE:** reaches only `unary` / `pairh` (+ shared encoder).
- **Travel term:** reaches only `cost` (+ the repair summary).
- **Legacy contrast:** under the same NLL, the legacy P8c checkpoints' `pair_scene` gradient is ≈ 0 (2e-4), against 1.5 at initialization (L0 finding 5).

Figure: `visualizations/p9/P9_L1_exact_likelihood.png`:
- (a) exact vs brute force;
- (b) cost of untied copies;
- (c) legacy copies vs one tied variable;
- (d) per-term factor reach.

## 4. Engineering notes

- **New code:**
  - `joint_likelihood.py` (195 logical lines);
  - `tests/test_p9_joint.py`;
  - `p9_run.py` (614 logical lines: the L0 audit, L1 artifacts, L2 driver and three gates). It is over the 300-line review trigger because the contract allows at most three new modules; each stage section is 150–250 lines.
  - **No P8 module, checkpoint, dataset or policy was modified** (re-verified by hash in the gate).
- **Test fixes during development.** Two first-run failures were test bugs, both fixed:
  - an exact `== 0` on a gradient whose value is 1.4e-17;
  - a broadcasting error in the padding fixture.
- **Re-run artifacts.** The first L1 artifact run summarized the wrong scope statistic and the sign of the duplicated-product difference. It was rerun (30 CPU-s) after recording the true elimination peak; the reported numbers are from the rerun.
