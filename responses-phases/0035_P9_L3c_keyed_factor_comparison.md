# 0035 — P9-L3c-1: the physically keyed relational variant `ABC9K_KEYED_V1`

**Actual result.** Gate: `runs/p9/l3c/L3C_1_GATE.json` → **PASS** (8/8). The variant was implemented after a GO feasibility decision (§1).

**What it is:**
- A 71-logical-line adapter, `unique_factor_keyed.py`, with **zero new parameters**.
- It changes only *which* factor instances exist. It reuses the trained ABC7 modules and `unique_factor`'s exact inference unchanged.
- It keeps all five families, every higher-order term, P_S, one normalizer per scene state, `z0 = zR[∅]` and the label masks.

**Evidence:**
- **Exact:** equal to brute force on 31 saved roots for each of B-full, B-structured and C-full (≤ 3.6e-15).
- **Normalized and scene-consistent.**
- **Fully invariant whenever the set of modelled physical outcomes is unchanged**, including every alias promotion (6 / 6 roots, B-full, B-structured, C-full: change **0.0**). The unique model moved by up to 0.04 (B-full) / 0.30 (C-full).
- **Genuinely new relations still change beliefs** (B-full ≤ 0.14).
- **Same cost per root** as the unique model; peak scope 11 (cap 16).
- **Not identical to the unique model** with the same frozen weights: B-full priors differ by up to 0.37 (mean 0.024); C-full by up to 0.16; B-structured identical on these roots.

Whether that difference matters after training is tested in report 0036 (matched 200-update retraining).

Previous turn sync: `6aa4ba55a267e6dfaded8ba3a8e91369b6795443`; L3c-0 PASS (report 0034).

## 1. Feasibility memo (written before implementation) — decision **GO**

**Question.** Can scene–query pairs, omission pairs and higher-order scopes be keyed by physical identity within a small adapter and the exact-inference cap, without deleting HO, inventing labels, changing the protocol or abandoning a family?

**Scene–query pairs (F5): yes.**
- The physical relation is (scene bit a, sequence outcome x_q). The canonical instance uses q's *own* representation `g_q + type(zR)` and q's own context `g_q`: exactly what ABC7 already computes when q is listed as a complete repair.
- One instance per (a, q); no new network; the role embedding is fixed to the "complete repair" type.
- Consequence: scene–omission pairs no longer depend on which parent listed the omission.

**Omission pairs (F4 zR–zO, F5 zO–zO): yes.**
- (q, q∖t) is determined by q and t. Each modelled q contributes its link to every omission q∖t that is itself modelled.
- zO–zO pairs among q's modelled omissions keep q's context, because they are relations *of q's sub-sequences*.
- Two different parents that share an omission pair remain two instances: distinct physical parents, distinct relations.

**Higher order (F5): yes, nothing dropped.**
- Each modelled q owns the hyperedge over (scene bits, x_q, x of its modelled omissions) with context `g_q`, using the trained `ho_q` / `ho_u`.
- The hyperedge exists whenever q is modelled, not only when q is listed.
- The scene-only `ho_s` stays in P_S once.

**Variable set: unchanged.** The modelled variables are those of the unique model (the catalogue's repairs and their omissions). No latent closure variables are added and no labels are invented.

**Cost.** One self-block per modelled query instead of per listed candidate. On saved roots the elimination peak is 11 (cap 16) and the CPU per root equals the unique model's.

**What cannot be kept: exact one-candidate equality to ABC7 for multi-move candidates.** Scene–omission pairs now use the omission's own context and role, and each modelled omission owns its HO. For one-move single candidates the factor set is identical, which a test asserts. This is declared, not hidden.

## 2. Definition

```
P_K(z_S, x | c0, C) = P_S(z_S | c0) · exp(−E_K(x, z_S)/T) / Z_K(z_S)

E_K = Σ_{q∈V} [ −s_q x_q                                           F2 (= F4 unary), once per query
              − Σ_a W_cpl(v_a, g_q + τ_zR; g_q) z_a x_q             F5 scene–query, once per (a, q)
              − Σ_{t: q∖t∈V} W_omit(g_q + τ_zR, g_{q∖t} + τ_zO; g_q) x_q x_{q∖t}     F4
              − Σ_{s<t} W_cpl(g_{q∖s} + τ_zO, g_{q∖t} + τ_zO; g_q) x_{q∖s} x_{q∖t}   F5
              − HO_q(z_S, x_q, x_{q∖t∈V}; g_q) ]                     F5 higher order (full / C-full)
```

`V` is the distinct physical sequence queries of the catalogue; each is identified canonically and checked against its (object, destination) moves, failing closed on conflict.

**Properties (tested):**
1. `Σ_x P_K = P_S` for any catalogue.
2. The factor set is a function of `V` alone, so exact duplicates, permutations, renamed IDs and re-listing a modelled query in any role leave `E_K` unchanged.
3. Disconnected candidates factorize given `z_S`.
4. Genuinely new outcomes or relations change beliefs as they should.
5. `E_static` and `J` never enter `E_K`, so they receive zero outcome gradient.

## 3. Verification

**Tests** (`tests/test_p9_l3c.py`, 17 tests, guarded run `runs/p9/l3c/l3c_tests.txt`):
- conflicting ID fails closed in the wrapper and in the keyed builder, while the frozen unique builder is silent;
- per-family decomposition sums exactly to the unique block;
- the deployed selector equals the lexicographic rule;
- **keyed is exact (brute force) and normalized, with scene marginals = P_S, for B-full, B-structured and C-full**;
- keyed equals ABC7 for one-move single candidates and differs for multi-move ones (declared);
- **keyed is invariant whenever the modelled outcome set is unchanged**, for all three arms;
- genuinely new relations change beliefs;
- finite-difference directional derivatives for `scene`, `pair_scene`, `pair_omit`, `cpl`, `ho_s`, `ho_q`, `order_s`, `mix`;
- zero outcome-NLL gradient to `unary`, `pairh` and `cost`, while static BCE reaches `pairh`;
- no new parameters, and evidence depends on `ho_q` weights;
- visual-zero control: same parameters and initialization, zero projection-weight gradient, nonzero bias gradient;
- determinism, zero physical calls, fail-closed scope.

**Frozen-checkpoint comparison** (L3b seed-0 weights trained under the *unique* model; validation + disclosed-test roots; `runs/p9/l3c/l3c1/artifacts.json`):

| arm | max \|P_K − P_U\| (mean) over 206 queries | log-evidence K − U, min / mean / max | brute-force roots, max error | peak scope | CPU-s per root, unique / keyed |
|---|---|---|---|---|---|
| B-full | 0.367 (0.024) | −0.54 / +0.11 / +3.83 | 31, 3.6e-15 | 11 | 0.0053 / 0.0053 |
| B-structured | 0 (0) | 0 / 0 / 0 | 31, 3.6e-15 | 11 | 0.0043 / 0.0043 |
| C-full | 0.155 (0.003) | −3.43 / −0.12 / +0.001 | 31, 3.6e-15 | 11 | 0.0056 / 0.0054 |

These weights were never trained under K. The differences measure instantiation semantics only, not a fitted comparison.

**Catalogue transformations under K with the deployed selector** (same 12 roots and frozen calibration as report 0034):

| arm | duplicate / permutation / disconnected / renamed | **alias promotion** (unique model in parentheses) | related new candidate (allowed) | switches among existing candidates |
|---|---|---|---|---|
| B-full | ≤ 3.6e-15 | **0.0** (0.038) | 0.141 | 0 |
| B-structured | ≤ 3.7e-15 | **0.0** (0 one-move, 1e-6 multi-move) | 0.165 | 1 (related case) |
| C-full | ≤ 1.9e-15 | **0.0** (0.298) | 0.073 | 0 |

In all 6 promoted aliases no new variable appeared, so invariance is the correct expectation and it holds exactly.

## 4. Scientific status

This establishes a *semantic* property: one physical relation equals one factor instance, independent of how the catalogue lists it. It does **not** establish better predictions. The matched retraining comparison (keyed vs unique, 200 updates, seeds 0–2, same batches and initialization) is reported in 0036, and the freeze choice in `P9_2D_FREEZE_DECISION.md` follows the contract rule (prefer the unique model unless the keyed variant is verified *and* not materially degraded on validation).

**Compute:** L3c-1 used ~48 CPU-s (tests 11.1, artifacts 35.8, gate 1.2); ledger `runs/p9/l3c/guards/`. 0 teacher, IK or planner calls.
