# 0072 — P14-D3: D-guided vs geometry-guided search, and lookup ablations (pilot)

**Status: PARTIAL / UNDERPOWERED.**
- **Gate:** `runs/p14/P14_D3_GATE.json`.
- **Frozen before any run:** `P14_PREREG.json`, pushed in `4bb95b8` (index hash, similarity weights, mode IoU, slots, depth, budgets, methods, roster).
- **Budget exhausted:** every method job hit its per-job CPU cap (1,250 CPU-s; ablations 400) after 6–7 of the 24 preregistered roots. Real cost was ~176 CPU-s per root, against a DEV estimate of ~75.
- **Pilot spend:** 6,947 / 8,000 CPU-s. Per the contract, the stage stops; nothing beyond the completed roots is reported.

## 1. Identical-condition comparison (the 6 roots completed by every method)

Same roots, slots, index, deterministic planner seeds, budget and success criterion (plan found **and** independent replay success).

| method | success | moves (solved) | travel (solved) | unnecessary moves | lookup hit rate | online fallback share of verified moves | nodes / root | motion checks / root | online plans / root | target checks / root | D calls / root | CPU / root |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **D-guided** | **4 / 6** | 1.25 | 1.75 | 0 | 0.474 | 0.50 | 10.7 | 25.7 | 4.5 | 8.2 | 2.5 | 176 |
| D-pairless | 3 / 6 | 1.00 | 1.33 | 0 | 0.464 | 0.51 | 10.5 | 26.0 | 4.5 | 7.7 | 2.5 | 176 |
| geometry | 3 / 6 | 1.00 | 1.33 | 0 | 0.474 | 0.50 | 11.0 | 25.2 | 4.5 | 8.2 | 0 | 135 |
| uninformed | 3 / 6 | 1.00 | 1.33 | 0 | 0.474 | 0.50 | 11.0 | 25.2 | 4.5 | 8.2 | 0 | 135 |
| oracle (labels; not deployable) | 3 / 6 | 1.00 | 1.33 | 0 | 0.474 | 0.50 | 11.0 | 25.2 | 4.5 | 8.2 | 0 | 136 |

**Per root:**
- **PR_SIDES 006, 015, 024:** every method found the **identical** depth-exhaustive 1-move plan. Travel was 1.72 (lookup witness, mode 0), 1.22 (online) and 1.05 (online). Guidance cannot matter once a depth is fully enumerated.
- **PC_SG 012:** only **D-guided** found a plan, 2 moves (o01 → 45 online, o00 → 44 lookup), travel 3.03, budget-truncated. All other methods exhausted the online budget first.
- **PC_SG 003, 021:** unsolved by every method within budget. Barrier relocations near the base miss the library and need the online planner.

**Paired comparisons:**

| contrast | success difference | roots split | sign p |
|---|---|---|---|
| D − geometry | **+0.167** [0.0, 0.5] | 1 / 0 (5 ties) | 1.0 |
| D − D-pairless | +0.167 | — | 1.0 |
| D − uninformed | +0.167 | — | 1.0 |
| oracle − geometry | 0 | — | — |

**Cost on roots both solved:** moves and travel identical; D costs +40 CPU-s per root (D inference, and the extra root it explored).

**Reading:**
- **No statistically supported D advantage.** One root out of six favours D (n = 1 discordant), and the oracle blocker labels did no better than geometry here.
- With this budget, the outcome is dominated by **lookup coverage and online-planner budget**, not by blocker guidance.

## 2. Lookup ablations

Only one ablation root (PC_SG 003) completed in every variant before the 400 CPU-s caps. The local-only and global-only runs did not finish a root.

| variant | completed roots | success | motion checks | online plans | CPU |
|---|---|---|---|---|---|
| D + combined lookup, all modes | 1 (003) | 0 / 1 | 73 | 6 | 288 |
| D + modal-top1 | 1 (003) | 0 / 1 | 3 | 6 | 282 |
| online-only (no lookup) | 2 (003, 006) | 1 / 2 | 0 | 6 | 14 / 247 |
| local-only | 0 | — | — | — | — |
| global-only | 0 | — | — | — | — |

- **On root 006 (descriptive, n = 1):** lookup + search found the depth-exhaustive 1-move plan with travel **1.72**; online-only found a non-exhaustive 1-move plan with travel **1.95**.
- **Modal-only false rejections at D3:** 0 (`modal_rejections_rescued` = 0 on completed roots). The rare-mode rescue mechanism is verified by unit test, but **its frequency is not estimated**.
- **Library coverage of D3 candidate pairs:** 60.1 %. Lookup hit rate during search: ~0.47. About half of the verified relocations needed the online planner.
- **Cache cost:** building the index cost 1,143 CPU-s, a one-off, reported separately from per-query cost.

## 3. Findings

- **Engineering works:** retrieval, certification, transit, fallback, search, replay and figures function on real physics. Every reported success was independently re-certified.
- **D vs geometry:** **not established.** +1 root of 6, p = 1.0; underpowered pilot.
- **Lookup vs online-only:** not established (n = 1 descriptive travel gain).
- **Negative finding:** D's temporary-target interface fails its physical probe (agreement 0.457).
- **Next experiment, if authorized:**
  - same frozen protocol on ≥ 24 roots;
  - a larger execution budget (≈ 25 k CPU-s at the measured 176 CPU-s per root × 5 methods × 24 roots plus ablations), or a cheaper target-verification stage;
  - a pre-measured per-root cost model before freezing the roster.
