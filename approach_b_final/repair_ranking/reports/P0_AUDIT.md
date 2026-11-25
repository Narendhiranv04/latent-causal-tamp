# P0: audit, parity and data boundaries

**Gate: PASS.** Parity, data boundaries and the reconciliation of earlier results all hold. No teacher queries were made in this phase.

## Provenance (`P0_PROVENANCE.json`)

- **Parent:** `naren/rss27-full-domain-set-search` @ `7db1132d98`, equal to origin. The new branch is `naren/rss27-xy-repair-ranking`, and `full_domain_sets/` and `mcts_sets/` are unchanged.
- **Plan:** `plan.md` is a byte copy of the controlling contract (sha256 `6ee1e659…`).
- **Frozen 2D bundle:** `~/abf_v34/approach_b_bundle` (manifest sha256 in JSON). Every file hash is checked by `benchmark.load_bundle`.
  - **Scorer:** `2d/scorer_s0.pt` is the coupled X/Y **arm D** (`coupled=True`, order `pred`, no SYM, no GEO, travel λ = 0), seed 0, best epoch 48.
  - **Sampler:** S1 TaskCVAE `scratch_all` s0, with n_z = 64 and proposal seed 0.
- **Training data:** snapshot `abf_v32_fb0eef4f5ff433ee` ("V3.2 exhaustive top-M TRAIN candidates"). It has 3,500 TRAIN, 751 VAL and 749 TEST rows. TEST was not opened.
- **Training objective, read from `xy.py`, not assumed:**
  - Per root, `nll_r = -batched_log_evidence(...)`: the **sum** over that root's observed Y and X nodes, with missing nodes marginalized exactly.
  - The loss is the mean of `nll_r` over roots. There is **no per-label normalization**.
  - Optimizer: AdamW, lr 1e-3, wd 1e-4, clip 10, batch of 64 roots, 60 epochs.
- **Early stopping used VAL NLL.** It was computed on the snapshot `val` split, which is the 751 old VAL roots. Old VAL is therefore **not independent of the scorer's checkpoint selection**, and this caveat applies to all DEV numbers below.

## Parity on 40 deterministic EVAL roots (`P0_PARITY.json`): pass

| Check | Result |
|---|---|
| cVAE top-6 (`exhaustive.proposals` vs the reconstructed marginal) | 40/40 equal |
| EXACT4 decision vs the sealed full-domain prediction | 40/40 equal |
| Read-only readout vs `Scorer.score` (p11, marginal px, py) | max abs error ≤ 1.3e-7 |
| `p11 = pY·pX1` and `px = pY·pX1 + (1−pY)·pX0` | ≤ 2.2e-16 |
| Shuffle invariance; same-endpoint pY across orders | 0.0 |
| Batching across roots (padding masked) | ≤ 1.7e-7 |

`Scorer.score` returns the **marginal** pX. The conditional pX1 = σ(a + w) comes only from the adapter (`rr.readout`).

## Original TRAIN supervision (`P0_TRAIN_COVERAGE.json`, `figures/p0_train_rank_support.png`)

- **Volume:** 20,550 finalized X labels and 21,911 Y labels. Every X label has a labelled endpoint Y. UNKNOWN outcomes are absent from the snapshot; they are missing, not negative.
- **Joint classes:** X1Y1 6,394; X0Y1 5,096; X0Y0 5,095; X1Y0 3,965.
- **Grammar:** all labels are legal under the original-root grammar.
- **Rank support.** Ranks are the frozen S1 marginal on each TRAIN S0, and each sequence is classified by its worst rank:

  | Worst rank | Share of labelled sequences |
  |---|---|
  | 1–4 | 18 % |
  | 5–6 | 11 % |
  | 7–12 | 25 % |
  | >12 | 46 % |

  - **The X/Y scorer was not trained only on cVAE top-4 proposals.** Tail support is mostly `ONPOLICY_COLLECT` (6,496 labels beyond rank 12) and `SELECTED_ASSIGNMENT_ORDER` (1,428).
  - **Tail labels are concentrated in a few intervention kinds.** The top-4 and 5–6 tiers are over-represented relative to legal support, and the tail is under-represented: 46 % of labelled sequences against 76 % of legal actions.
- **Labels per root:** median 6 observed nodes, mean 12.1, maximum 279. The rank-loss scale C = **6** is fixed now, before any training.
- **Usable ranking pairs:** 1,719 TRAIN roots already have both a decided Z+ and a decided Z− (logical conjunction).

## Partition and leakage (`P0_SPLIT_MANIFEST.json`)

- **DEV split:** DEV_CAL / DEV_AUDIT by parent family, using sha256('XYRR_DEV|'+family) parity.
  - DEV_CAL: 370 roots (295 families; K1 69, K2 61).
  - DEV_AUDIT: 381 roots (289 families; K1 51, K2 59).
- **Overlap with TRAIN:** zero families and zero root ids. **15 VAL roots share a cell-layout fingerprint with a TRAIN root** (same occupied cells, target cell and goal). They are kept and disclosed.
- **Labelled VAL candidates (four exact-contract caches):**
  - 14,263 VAL keys: 5,909 decided Z = 1, 4,267 decided Z = 0, 4,087 unresolved. 0 conflicts.
  - 165 K1/K2 roots have both a decided Z+ and a decided Z− among K ≤ 2 sequences: 89 in DEV_CAL, 76 in DEV_AUDIT.
  - The generator labels (`labels.B`) are secondary and used only descriptively.

## Reconciliation with the completed study

Recomputed from the committed `P3_PHYSICAL_PER_ROOT.jsonl`, everything matches:
- **EXACT4:** strict 120/148 with 43 UNKNOWN (FAIL_X 10, FAIL_Y 11, NOOP 7).
- **PW_MCTS_SEEDED4@1024:** 123/153.
- **EXACT_FULL:** 109/149.

## CONFIRM cohort candidate (`P0_CONFIRM_POOL.json`; private index in `~/xyrr_private/confirm/`)

**Source:** the V3.4 generation runs accepted 2D roots that were never admitted to the V3.4 cohort and never inferred or teacher-evaluated by any method. They have new seeds and ids, and the same generator, teacher config hash and acceptance rule as the V3.4 cohort.

**Disjointness:**
- Each candidate is checked by root id, construction seed, sha256 and GEOM_V1 layout fingerprint against the historical exclusion lists, the V3.4 cohort and within the pool.
- REPARK/HARD enrichment parents (39) are excluded because they share lineage with cohort children.
- 0 template families overlap with TRAIN.

**Admitted, at 0 teacher queries:**

| Class | Roots |
|---|---|
| K1 | 61 |
| K2 | 23 |
| K0 | 114 |
| NONE | 9 |

**This is below the plan's target of ≥ 80 K1 and ≥ 80 K2.**
- More roots could only come from the generator. Its certification runs its own planner searches, which can be capped by CPU time but not counted as teacher ordered queries.
- Plan §2.2 forbids launching such a generator without a separately approved bounded protocol, so none was launched, and none of the 600-query certification allowance was spent.
- Any P6 result on this pool is therefore labelled **underpowered (84 K1/K2 roots)**. The K2 stratum (23) is too small for a separate inference.
