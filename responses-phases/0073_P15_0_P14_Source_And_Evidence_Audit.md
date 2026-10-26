# 0073 — P15-0: P14 source and evidence audit

**Previous turn sync:** P14 final `cbd5d9b1509fcfdad733545b7d0e9cba4181ee4f`. Local equals origin/main. The only working-tree changes are the user's two deleted root PDFs, which were not staged.

**Actual result.**
- **Gate:** `runs/p15/P15_0_GATE.json` → **PASS**.
- **No silent numerical disagreement:** every P14 manifest hash matches (0 mismatches). The D3 and matched-admission tables recompute exactly from stored JSON (`runs/p15/audit/P15_0_AUDIT.json`).
- **Cost:** 1.1 CPU-s.

## 1. Recomputed P14 evidence

| item | value |
|---|---|
| sampled original-scene replays | 150 / 150 ALL_CLEAR |
| index entries / excluded roots (every P13 blind / natural root) | 4,838 / 170 |
| D3 common roots | `p13_2026180003`, `…006`, `…012`, `…015`, `…021`, `…024` |
| D3 success | D **4 / 6**; D-pairless, geometry, uninformed, oracle **3 / 6** each |
| roots each method completed before its cap | D 6, D-pairless 6, others 7 |
| mean CPU per root on the common roots | D 176.0, D-pairless 175.9, geometry 135.5, uninformed 135.3, oracle 136.5 |
| D − geometry | 1 discordant root, exact paired p = 1.0: **no established advantage** |

**The extra D success (root 012)** happened while every other method exhausted its online-planner budget first. It is a budget-ordering effect on one root.

## 2. Validation-matched versus actual test admission (P14-A1, coverage-matched)

Every arm was matched to K-B's **validation** coverage (mean 0.694). The resulting **test** admissions differ, so "matched admission" means validation-matched, not held-out-matched.

| arm | validation coverage | **test admission** | executed success |
|---|---|---|---|
| K-B | 0.694 | **0.835** | 0.731 |
| A | 0.694 | 0.827 | 0.731 |
| C | 0.694 | 0.860 | 0.731 |
| B-F3pm | 0.694 | 0.891 | 0.744 |
| B-F4 | 0.694 | **0.902** | 0.734 |
| B-F5spm | 0.694 | **0.902** | 0.742 |
| B-F2 | 0.698 | 0.910 | 0.664 |
| SF | 0.694 | 0.889 | 0.649 |
| B-U | 0.694 | 0.894 | 0.770 |

## 3. Source-to-claim matrix (corrected in P15)

| P14 issue | source | P15 action |
|---|---|---|
| first certified witness only (alternative modes / terminal configurations dropped) | `p14_d_search._move` | multi-edge provider keeping certified alternatives (P15-3) |
| UNKNOWN planner result collapsed to `None`; `depth_exhaustive` read as proof | `p14_d_search._target` | tri-state statuses; two separate completeness flags (P15-3) |
| restricted graph (ORDERED_TEACHER movers, move-once, K slots, depth ≤ 3) | `p14_d_search.search` | declared action domain; restriction labelled (P15-3) |
| `root_variant` kept `R.goal` and the original visual tokens while the probe used another destination | `p14_d_search.root_variant` | full scene-to-D-input rebuild through the training pipeline; matched probes (P15-1) |
| `unnecessary_moves` = moves outside the *original* blocker union | `p14_eval.run_method` | renamed `moves_outside_original_blocker_union`; true extra moves only on proven optima (P15-3) |
| no validated similarity threshold | `p14_sweep_index.lookup_candidates` | held-out transfer benchmark; DEV-frozen threshold as an ablation (P15-2) |
| validation-matched vs test admission | `p14_eval.matched_admission` | reported side by side (above; P15-7) |
| greedy, order-dependent mode clustering | `p14_sweep_index` | deterministic canonical clustering with terminal pose in the signature (P15-2) |

All P10–P14 artifacts are unchanged. Their hashes are recorded in `P15_0_AUDIT.json`.
