# 0032 — P9-L3a-1: the canonical unique-factor root model (mathematics, proofs, invariance)

**Actual result.** `unique_factor.py` (`ABC9U_UNIQUE_V1`) implements the contract §2.2 competitor for **B-full, B-structured and C-full** without dropping any factor family. That includes B-full's generic pairs and *both* higher-order terms.
- Every potential is ABC7's **raw** potential, re-evaluated through the model's own modules. Normalized `logP_Q` tables are never summed.
- Each distinct physical query gets **one** variable and **one** outcome unary; each distinct repair block contributes its relational terms **once**; there is one conditional normalizer per scene state.

**Verified properties:**
- equal to brute-force enumeration on **51 saved roots** (max |Δ log P| = 3.9e-14) and on toy fixtures (≤ 1e-10);
- **identical to the ABC7 joint for one-repair catalogues** and **identical to P9 PoE when no query is shared** (≤ 1e-10);
- scene prior exactly P_S;
- **every EXPECTED_INVARIANT case passes for all three arms**, where PoE fails exact duplication (≤ 0.18) and, in B-structured, the no-new-factor alias (0.046);
- peak elimination scope 8 (cap 16); cost per root 0.020 CPU-s, equal to PoE.

**Gate:** `runs/p9/l3/L3A_1_GATE.json` → **PASS** (10/10). Full suite **375/375** with **6/6** replays.

Previous turn sync: `4be6d803bbfcff693b8055eb4e2e25707a8da4ee`. L3a-0 PASS (report 0031).

## 1. The model

**Notation:**
- `z_S`: root-scoped scene bits (`z0`, `zS[I]`);
- `x_q`: one binary variable per distinct sequence query (a repair `zR` or an omission `zO[r,t]`, identified canonically by root and ordered `(object, cell)` moves; audited in 0031);
- `b`: distinct repair blocks (an exactly repeated candidate is one block).

```
P_U(z_S, x | c0, C) = P_S(z_S | c0) · exp(−E_Q(x, z_S)/T) / Z_U(z_S)

E_Q = Σ_q  −s_q x_q                                   s_q = order_s(g_q, scene_vec(xy_q)): F2 φ_seq on q's OWN ordered sequence
                                                      (for an omission role this is the F4 omission unary — shared scorer, kept)
    + Σ_b [ −½ z_bᵀ W_b z_b − HO_b(z_b) ]             z_b = (z_S, x_{σ_b});  W_b from _pairs(V_b, g_b):
                                                      F4 zR–zO pairs, F5 scene–repair and zO–zO pairs (role types, context g_b);
                                                      HO_b = ho_q(Z·ho_u(V_b), g_b) (B-full / C-full only)
```

**What stays where:**
- **Scene factors** (F3 unaries, `z0–zS` pairs, F5 scene pairs, `ho_s`) enter `P_S` once.
- **F1 static and travel J** are outside this conditional graph, trained by the same auxiliaries as P9.
- **Training objective:** `mean_roots(−log P_U(D_c)) + 1·static BCE + 1·witnessed log-Huber J`.

**Difference from P9 PoE** (`P_S · Π_r P_Q,r / Z_eq`). PoE keeps one variable per query but (i) re-applies `s_q` in every block containing `q`, and (ii) divides by every block's own normalizer `Z_r(z_S)`. On 76 saved roots: **1,386 PoE unary contributions vs 634 unique unary instances**, and 578 blocks in both.

## 2. Proofs

1. **Normalized, scene-consistent.** For every `z_S`, `Σ_x exp(−E_Q)/Z_U = 1`, so `Σ_x P_U(z_S, x) = P_S(z_S)` for **any** catalogue. Measured max deviation of scene marginals: 0.0.
2. **One-repair catalogue = ABC7.**
   - With one block, the slot unaries are `s` of distinct queries (ABC7 refuses intra-block aliases), each counted once.
   - Adding the pair and HO terms gives exactly ABC7's `E_Q,r` minus nothing.
   - One normalizer per `z_S` equals ABC7's `Z_r(z_S)`.
   - Hence `P_U = P_S·P_Q,r` (test: ≤ 1e-10 for B-full, B-structured, C-full).
3. **No shared query = PoE.** Blocks with disjoint variables factorize given `z_S`: `exp(−Σ_b E_b)/Z_U = Π_b exp(−E_b)/Z_b`, which is the PoE with `Z_eq = 1` (test: ≤ 1e-10).
4. **Invariances.**
   - *Permutation and renamed IDs:* `E_Q` is a sum over sets keyed by identity.
   - *Exact duplicate:* same identity, same instance, collapsed.
   - *Disconnected candidate:* its variables appear in no other factor, so the conditional factorizes given `z_S` and others' marginals are unchanged.
   - *One-move alias without generic coupling:* the candidate adds a block whose only term is the unary `s_q` already present, so `E_Q` is unchanged.
   - *Scene prior:* by (1).
5. **What may change, by design.**
   - A genuinely related repair adds new relational instances.
   - So does an alias in B-full / C-full, through a new zR-role scene–repair coupling instance with context `g_q`.
   - So does an alias with ≥ 2 moves, through its own new `zR–zO` pairs.
   - These changes are measured, not forced.
6. **Static and J.**
   - `E_static(r)` and `J` never enter `E_Q`, so the outcome likelihood sends them exactly zero gradient.
   - Their auxiliaries do (test).
   - A z-constant output bias in any block or HO network also cancels exactly — a correct mathematical property that tripped my first gate probe (§5).
7. **Exactness.**
   - `log P_U(D_c) = logsumexp_{z_S ⊨ y_S}[log P_S + log N_U − log Z_U]`, with `N_U` and `Z_U` exact sums by elimination (`joint_likelihood.contract`, shared with P9).
   - UNKNOWN / NOT_RUN labels are summed, never zeros; an all-missing root gives exactly `log P = 0`.
   - Exceeding the scope cap raises `CombinatoricsError`; there is no sampling.

**Counterexample (contract §2.1)** — `test_duplicated_expert_counterexample_0p8` and the figure:

| situation | P(x = 1) |
|---|---|
| one expert | 0.8 |
| PoE with the expert duplicated | 0.64 / 0.68 = **0.9412** |
| unique factor with the candidate duplicated | **0.8** |

On saved roots the same mechanism moves PoE marginals by up to 0.18, and changes the PoE choice on 1–3 of 12 roots.

## 3. Executable verification (`tests/test_p9_l3_unique.py`, 26 tests, all pass)

**Toy fixtures** (random unaries and random raw block tables, i.e. arbitrary pair and higher-order potentials), checked against an **independent enumerator**:
- no aliases;
- one query in `zR` and `zO` roles across three blocks;
- an explicit `zR[∅]` slot tied to `z0`;
- labels that are UNKNOWN / NOT_RUN or all missing;
- extreme energy scales (1e3) and temperatures 0.25 / 4;
- prior and offline-conditional marginals;
- finite-difference gradients;
- the 0.8 counterexample.

**Saved P8c roots with P9-L2 checkpoints:**
- one-repair = ABC7 joint and = PoE (B-full, B-structured);
- unshared catalogue = PoE;
- brute force on real roots;
- invariance cases for B-full and B-structured;
- finite-difference directional derivatives for `scene`, `pair_scene`, `pair_omit`, `cpl`, `ho_s`, `ho_q`, `order_s`, `mix`;
- exact zero outcome gradient to `unary`, `pairh` and `cost`, with auxiliary gradient to F1;
- a same-endpoint reversed order gives a distinct query identity and a different unary;
- determinism and label isolation;
- fail-closed complexity;
- C-full one-repair equivalence.

**Full historical suite** (`runs/p9/l3/regression`): **375 passed** (323 historical + 26 P9 + 26 new) and 6/6 archived replays, 598.6 CPU-s. The planner calls counted there are **historical unit-test fixtures only**, e.g. `test_g4a.py` 198 `planner.plan` calls (full table in the gate file). They are separate from learned inference.

**Inference isolation** (`l3a1/isolation.json`): 72 PoE and unique root inferences in a fresh interpreter. **No** planner, motion, skill, ordered, evaluate, teacher, verify or geometry module was ever loaded.

## 4. Three-way comparison with frozen P9-L2 seed-0 weights (`l3a1/artifacts.json`)

This is a semantics comparison: the weights were trained under PoE. Max |change| of prior marginals of the original queries:

| case | B-full PoE / dedup / unique | B-structured PoE / dedup / unique | C-full PoE / dedup / unique |
|---|---|---|---|
| permutation, renamed IDs, disconnected | ≤ 4e-15 / ≤ 4e-15 / ≤ 4e-15 | same | same |
| **exact duplicate** | **0.180** / 0 / **0** | **0.167** / 0 / **0** | **0.139** / 0 / **0** |
| **one-move alias, no new factor** | n/a | **0.046 / 0.046 / 0** | n/a |
| alias with a new factor (allowed) | 0.042 / 0.042 / 0.305 | 9e-5 / 9e-5 / 0.013 | 0.377 / 0.377 / 0.513 |
| related candidate (allowed) | 0.140 / 0.140 / 0.134 | 0.193 / 0.193 / 0.226 | 0.059 / 0.059 / 0.216 |

**|PoE − unique| prior marginal by PoE unary multiplicity k:**

| k | queries | mean | max |
|---|---|---|---|
| 1 | 266 | 0.022 | 0.30 |
| 2 | 153 | 0.066 | 0.38 |
| 3 | 116 | 0.057 | 0.97 |
| 4 | 50 | 0.063 | 0.62 |
| 5 | 32 | 0.034 | 0.13 |
| 6 | 13 | 0.038 | 0.28 |

**Open semantic point (reported, not hidden).**
- In B-full and C-full the unique model still responds strongly (0.31 / 0.51) when an existing omission query is *also* listed as a complete candidate. The new block contributes ABC7's scene–repair coupling for that query in the zR role, with the query's own context.
- These are role- and context-specific relational instances (permitted by contract §2.2), not exact duplicates.
- If the physical intent is **one scene–query relation per (scene bit, query)**, that is a narrower factor graph, not a defect of this implementation. It is a candidate for the next ablation (`P9_L3_DECISION.md`).

## 5. Engineering notes and incidents

- **Code:**
  - `unique_factor.py`: 165 logical lines; no change to `abc7_models.py`, `joint_likelihood.py`, datasets or checkpoints;
  - `p9_l3.py` (627 logical lines): the guarded driver with ledger, audit, artifacts, L3b plan / train / evaluate and gates. It is over the 300-line trigger because it holds three stages behind one CPU ledger; it does not grow `p9_run.py`;
  - `tests/test_p9_l3_unique.py`;
  - two figure functions in `p9_viz.py`.
- **Incidents (all charged):**
  1. **Alias expectation.** The alias-case expectation first ignored that a ≥ 2-move alias carries new `zR–zO` pairs; fixed and rerun (§0031).
  2. **Summary grouping.** The L3a-0 gate summary first grouped by case only; it now groups by (case, expectation).
  3. **HO probe.** The first "HO retained" gate probe perturbed an output *bias*, which cancels exactly in every normalized block. The probe now perturbs final-layer weights, and evidence depends on `ho_q`, `ho_s` and `cpl`.
- **Figures** (each with a SHA-256 manifest of inputs):
  - `visualizations/p9/P9_L3a_real_root_factor_graph.png`: real root `p8_2026102510`; PoE with k unary squares per reused query vs unique with one;
  - `visualizations/p9/P9_L3a_invariance.png`.
- **L3a compute:** 755 CPU-s of the 8,000 L3 budget, including 604 CPU-s of regression. 0 teacher, IK or planner calls in learned inference.
