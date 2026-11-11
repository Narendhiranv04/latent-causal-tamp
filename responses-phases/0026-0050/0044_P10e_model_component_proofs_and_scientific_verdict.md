# 0044 — P10e: model-component proof ledger and the 2D scientific verdict

**Verdict in one paragraph.**
- **Keyed B (JOINT-CAUSAL-EBM)** is the empirically strongest **learned** approach on the sealed 2D benchmark (65 independent blind roots, predictions frozen before unsealing).
  - It wins the preregistered primary **executed TOP1** comparison against SF (71.8 % vs 38.5 %, Holm p = 8e-6), and also beats A (+13 points) and geometry-only (+27 points).
  - It wins the **H1 complementarity** primary against A (κ error 0.014 vs 0.277, 9 / 9 roots, Holm p = 0.012).
  - Its per-root NLL is the best of all arms.
- **C (GRU order encoder) adds nothing over B** on any endpoint.
- **Order and omission endpoints do not discriminate the main arms.** Order is at ceiling; omission is +3 points, not significant.
- **Retrained ablations attribute the gains** to:
  - the order factor (F2): order accuracy 1.00 → 0.28 without it;
  - the scene-pair factor (F3) and the generic coupling (F5): H1 error worse without them;
  - the visual input: NLL and order worse with it zeroed.

  The repair–omission pair (F4) shows **no benefit**.
- **Weaknesses:**
  - Planner-assisted G+M still executes better (83 %).
  - All learned arms fail the H7 edit-vs-executable family (0 / 4).
  - Predictions are appearance-sensitive (H9 shift about 0.16).
- **D** predicts initial feasibility perfectly on the blind roots and attributes blockers well (F1 0.87). Its **pairwise Boltzmann term is not supported**: the pairless control is equal or better.

## 1. Component proof ledger (A / B / C, F1–F5) — evidence from P10c / P10d (blind) unless stated

Code paths:
- model: `abc7_models.ModelBC7` / `ModelA7`, `abc8`;
- exact keyed inference: `unique_factor_keyed.installed()` + `unique_factor.instances` / `prior_marginals`;
- factorized objective: `joint_likelihood.factorized_logits`;
- training: `p9_l3.fit`;
- selection: `p9_l3c.deployed` / `p10_protocol.top1`.

Tests (all pass, 81 total):
- `tests/test_p9_joint.py`, `tests/test_p9_l3_unique.py`, `tests/test_p9_l3c.py`: normalization, exact elimination, duplicate / alias / permutation invariance, keyed ontology;
- `tests/test_p10c_ablations.py`: hooks bit-identical by default; F2 order invariance; F3 / F4 removal still gives exact inference;
- `tests/test_d_blockers.py`.

**Training signal:** VERIFIED / CERTIFIED / BUDGET teacher labels, with BUDGET kept as an operational 0 and UNKNOWN never supervised. The removal controls were **retrained from scratch** with identical data, seeds and schedule.

| component | mathematical role | removal control | blind effect of removal vs keyed B (Δ, 95 % CI, sign-test p) | verdict |
|---|---|---|---|---|
| **F1** static endpoint head | E_static (outside P(z \| r)) | analytic static veto vs learned F1 | **NOT_RUN** (analytic veto used by every arm; no F1-only retrain) | not identified |
| **F2** order (B predecessor term) | phi_seq / repair summary g | B-F2 (order-invariant: sorted, prefix-free tokens) | order accuracy **−0.718** [−0.833, −0.603] (26 roots); NLL +0.059 [0.017, 0.098] (p 0.006); H1 −0.031 | **NECESSARY** for order discrimination |
| **F2** as GRU (C) | replaces B's predecessor term | K-C vs K-B | order 0.000; NLL +0.035 [0.007, 0.067]; H1 −0.042; TOP1 0.000 | **NOT_BENEFICIAL** over B |
| **F3** scene edits / scene pair | P_S(z0, zS) scene-pair factor | B-F3 (no `pair_scene`) | H1 error worse: −0.143 [−0.239, −0.063] (9 / 9 roots worse, p 0.004); NLL +0.012 (ns) | **USEFUL** for complementarity |
| **F4** repair–omission pair | zR–zO[t] pair | B-F4 (no `pair_omit`) | NLL −0.025 [−0.055, 0.005] (ns, slightly *better*); omission +0.016 (ns); H1 −0.038 | **NOT_BENEFICIAL** (not identified as useful) |
| **F5** generic couplings + HO | `cpl` pairs + HO residual | B-F5s (structured: no generic, no HO) | H1 −0.099 [−0.122, −0.079] (p 0.004); NLL +0.033 [0.001, 0.063] (p 0.006) | **USEFUL** |
| **F5** HO only | HO residual | B-F5q (quadratic) | H1 −0.040 [−0.051, −0.029] (p 0.004); NLL +0.024 [−0.005, 0.053]; omission −0.026 | **small benefit** |
| DINOv2 visual input | object tokens | B-V0 (zeroed DINOv2, same architecture) | NLL +0.089 [0.049, 0.133] (p 1e-4); order −0.19; H1 −0.072 | **USEFUL**, but appearance-sensitive (H9 shift 0.14–0.17) |
| keyed ontology | one factor per physical scope | B-U (historical unique) | NLL +0.012 [−0.014, 0.036]; H1 −0.035 | small, ns; keyed kept for semantics |
| witnessed-J travel head | TOP1 tie-break | — | **NOT_RUN** as a separate selection ablation | not identified |
| A (GRU, factorized) | no joint | A vs B | TOP1 −0.133; H1 +0.262 worse; NLL +0.047 | B > A |
| SF (factorized control) | no joint, no energy | SF vs B | TOP1 −0.333; NLL +0.133 | B ≫ SF |

**Mechanism-level reading.** These are **intervention-conditional physical effects** that the joint graph represents better than the factorized controls: complementarity κ, predecessor-dependent order and the joint scene-edit structure. They are not a learned structural causal model. Shared encoders can carry some of the same information, so a removed factor never "mathematically forbids" a relation. The table reports only measured incremental effects.

**Inference cost** (blind roots; `runs/p10d/INFERENCE_COST.json`):
- per-root exact marginals: B 0.021 s mean (max 0.076), C 0.020, A 0.011, SF 0.010, D 0.0004;
- 3–11 objects per root; 4–10 candidates;
- active outcome slots ≤ 9 (cap), MAX_SCOPE 16, **0 scope failures**, 0 physical calls.

## 2. D audit (D_BLOCKERS_V1)

| item | content |
|---|---|
| definition | u (feasibility logit), a_i (blocker unaries), w_ij (symmetric pairs); exact Z_B over 2^n, n ≤ 6 (fail-closed `CapError`) |
| tests | normalization against brute force, gradcheck, permutation equivariance, pairless control, partial masks, minimal-set cases, independent enumerator (200 random tables), 0 physical calls |
| labels | all 2^n parking subsets (target-only scene edits, frozen parking rule); minimal sets via `minimal_sets` and an independent re-derivation in `p10b_dataset.d_labels` (agree on every complete mask); blocker loss only on proof-grounded masks |
| results (blind) | feasibility perfect (64 / 64); blocker F1 0.872 (D) vs 0.882 (pairless) vs 0.797 (heuristic); matched 33 B/C-supported roots: D 0.94, heuristic 0.93, pairless 0.92, B / C 0.86 |
| pair term | **not supported**: D − pairless F1 −0.010 [−0.046, 0.038]; pairless better on 19 roots vs 6 |

## 3. Direct answers (contract §7)

1. **Are A / B / C better than SF, geometry-only and G+M on new long repairs?**
   - B and C beat SF and geometry-only by a wide margin on executed success. On 3-move roots: B 0.52 vs A 0.04, SF 0.00, geometry 0.00. On 4-move roots: B 0.78 vs A 0.74, SF 0.00. Overall B − SF is +0.333 [0.226, 0.441].
   - B and C do **not** beat planner-assisted G+M: 0.72 vs 0.83, with G+M better on 24 roots vs 8. G+M plans relocations for up to 5 ranked candidates and uses pose screens, so its compute is unequal: about 15.7 CPU-s per episode plus screens, against a single planned candidate for TOP1.
2. **Does C improve over B on paired order contrasts? Does B / C beat A on complementarity after relevant training?**
   - C does **not** improve over B: order is at ceiling (1.0 for both), TOP1 is identical and NLL is slightly worse.
   - B **does** beat A on complementarity after training on H1 data: κ error 0.014 vs 0.277, Holm p = 0.012. Before relevant training (P10a), every arm failed H1.
3. **Which of F1–F5 matter?**
   - **F2** (order): necessary for order discrimination.
   - **F3** (scene pair) and **F5** (generic coupling, smaller HO effect): matter for complementarity and fit.
   - **F4**: not beneficial.
   - Still unidentified: **F1** (learned static vs analytic) and the J head (not run as separate selection ablations); order beyond ceiling (the blind order pairs were too easy once trained); omission (all arms 0.90–0.95).
4. **How does performance degrade from 1–2 to 3–4 relocations, and where does exact inference fail?**
   - Executed B success is 0.75 on 1–2-move families, 0.52 on 3-move and 0.78 on 4-move roots. SF, geometry and (on 3-move roots) A collapse to about 0.
   - **Length extrapolation:** B trained only on ≤ 2-move data keeps omission and order accuracy at 1.00 on blind 3- / 4-move roots (A 0.67 / 0.83, SF 0.77 / 0.76), but its NLL degrades from 0.04 to 0.48.
   - Exact keyed inference **never** hit the scope cap: ≤ 9 active slots, MAX_SCOPE 16, 0 failures.
5. **Does D identify genuine initial blockers, including joint and alternative sets, better than pairless or heuristic baselines?**
   - Feasibility: yes, perfect.
   - Blockers: better than the geometry heuristic (+0.075 F1) and better than counterfactual B / C attribution on matched roots. It does **not** beat its pairless control, so the Boltzmann pair term is not justified by these data.
   - Jointly necessary pairs (H1, F1 0.98 in the 2-blocker stratum) and alternative minimal sets (H2a) are recovered.
   - The 3- / 4-object corridor masks exist only operationally (F1 0.80 / 0.67).
6. **What is still open?**
   - The H7 edit-vs-executable failure of every learned arm.
   - Appearance invariance (H9).
   - The gap to planner-assisted G+M.
   - F1 / J ablations.
   - D destinations and recursive displacement (`D_DESTINATION_AND_RECURSION_DEFERRED.md`) and all 3D work. These are **future work, not implemented**.

## 4. Limitations

- **Adaptive construction.** The roots are certificate-targeted, though the blind roots and their labels were never used for tuning. Results are relative to this constructor family and this pick-side certificate scope. Place-side negatives exist only as FIRST_MOVER placement-screen certificates (scope stated in 0039) or as operational BUDGET labels.
- **Small strata.** H1 has 9 blind roots, H7 4 and H8 4. Per-mechanism claims beyond P1 / P2 are descriptive.
- **Minimality is catalogue-relative.** For H10 it is SOUND on 10 roots and OPERATIONAL elsewhere; it is never global.
- **Compute disclosures:**
  - the training cap was lifted by user instruction;
  - the preliminary pass's ledger was over-counted;
  - one episode job was restarted.

All are recorded in 0041–0043.
