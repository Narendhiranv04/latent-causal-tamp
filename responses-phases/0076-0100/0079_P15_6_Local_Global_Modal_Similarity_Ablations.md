# 0079 — P15-6: local / global / modal / threshold / online-only lookup ablations

**Actual result**
- **Design:** geometry guide (deterministic, no learned input), the **first 12 roots of the frozen retrospective roster**, and the identical frozen search.
  - Budget {400 motion checks, 6 online moves, 16 goal plans}, soft CPU cap 150 s per root.
  - Same slot set: indexed destinations are offered even when lookup is off, so edges stay aligned.
  - Only the lookup varies.
- **Data:** `runs/p15/search/ABL_*.json`, with `combined` = `RETRO_geometry.json` on the same roots. Summary: `runs/p15/eval/ABLATION_SUMMARY.json`.
- **Spend:** `ablation` 8,047 / 12,000 CPU-s.
- **Gate:** `runs/p15/P15_6_GATE.json` → **PASS (executed); all contrasts UNDERPOWERED**.

## 1. Search-level ablation (12 roots, paired)

| variant | solved (replay CLEAR) | motion checks / root | online moves / root | lookup candidates tried | lookup hits | rare-mode edges | CPU / root | co-solved travel (variant vs combined) | discordant vs combined |
|---|---|---|---|---|---|---|---|---|---|
| **combined** (3×3 / 4×4 + 0.25 global, multimodal) | **10** | 105.5 | 4.0 | 1,266 | 125 | 23 | 130.8 | — | — |
| local only | 10 | 117.9 | 4.0 | 1,415 | 123 | 14 | 126.4 | 1.701 / 1.701 | 0 |
| global only | 10 | 101.4 | 4.0 | 1,217 | 125 | 28 | 125.5 | 1.701 / 1.701 | 0 |
| combined + DEV threshold (1.0499) | 10 | **68.2** | 4.6 | 819 | 104 | 22 | 121.7 | 1.698 / 1.701 | 0 |
| modal-top1 (one candidate per edge) | 9 | 8.8 | 4.2 | 105 | 43 | 0 | 103.5 | 1.474 / 1.480 (9 roots) | 0 / 1 |
| representative per mode (no within-mode alternatives) | 10 | 21.5 | 4.2 | 258 | 85 | 36 | 108.2 | **1.877 / 1.701** | 0 |
| online only (no lookup) | **8** | 0 | 5.2 | 0 | 0 | 0 | 83.9 | 1.445 / 1.431 (8 roots) | 0 / 2 |

**Readings**
- **Every contrast is UNDERPOWERED.** At most 2 discordant roots out of 12, and the exact sign test needs ≥ 6 all one way. Nothing here proves equivalence.
- **Lookup vs online only:** 10 vs 8 solved (2 discordant, both favour lookup, p = 0.5). Lookup turns 125 certified library witnesses into edges, which the 6-call online budget alone cannot supply.
- **Similarity scoring:** local, global and combined give identical search outcomes, consistent with the 0075 transfer benchmark (top-1 0.48–0.52). The ranking changes cost, not coverage: local tries 12 % more candidates, global 4 % fewer.
- **Threshold:** it saves 35 % of motion checks (68 vs 105) with the same 10 solved here. On the 0075 TEST half it lost 11.6 % of available motions, so it remains a cost-only, non-deployed option.
- **Clustering loss:**
  - Representatives cost 18 % more travel on co-solved roots (1.877 vs 1.701), because a representative is not the cheapest certified member of its mode.
  - Modal-top1 loses a root and never uses a rare mode.
  - Neither saves more than 27 CPU-s per root.
- These four rows (threshold, modal-top1, representative, online-only) change the number of available edges, so they are **resource / coverage ablations**. Their downstream differences are not attributed to similarity scoring.

## 2. Transfer-level evidence (0075)

**Coverage is separated from precision:** a key match exists for 330 / 330 held-out queries, but only **72.4 %** have *any* certifiable other-root motion, and top-1 certifies in only 50.6 %.

| ranking | top-1 | any | mean calls | rare-mode rescues |
|---|---|---|---|---|
| combined | 0.506 | 0.724 | 6.37 | 53 |
| global | 0.515 | 0.724 | 6.19 | 49 |
| local | 0.476 | 0.724 | 6.83 | 57 |

**False retrieval** (top-ranked candidate not certifiable in the new scene):
- 163 / 330 queries under combined ranking;
- 1,347 swept-collision rejections and 2,603 failed start transits among 6,890 candidate certifications.

The top-K curve is `visualizations/p15/P15_lookup_topk.png`.

## 3. Index cost (amortization)

- **Build cost:** 1,125 CPU-s for the P14 index build plus 1.5 CPU-s for the v2 statistics. The 0075 transfer benchmark (1,674 CPU-s) is evaluation, not deployment cost.
- **Search-time cost:** lookup costs **+46.9 CPU-s per root** relative to online-only (130.8 vs 83.9), because certifying library candidates is real work.
- **Break-even:** not a CPU break-even. Lookup buys solved roots (+2 / 12) rather than saving time. Spreading the build over the 408 benchmark root-searches run in P15 (6 × 24 retrospective + 6 × 32 prospective + 6 × 12 ablation) adds ≈ 2.8 CPU-s per search.
- **Optional wider catalogue (ablation 8):** **NOT_TESTED**. No DEV-only expansion could be frozen without new teacher data.

## 4. Verdicts

| question | verdict |
|---|---|
| lookup improves solved roots over online-only at equal counts | **UNDERPOWERED** (10 vs 8, 2 / 0 discordant) |
| local vs global vs combined scoring matters downstream | **UNDERPOWERED / no observed difference** |
| similarity threshold safe to deploy | **NEGATIVE** (loses 11.6 % of available TEST motions in 0075; cost-only option) |
| representatives lose travel (clustering loss) | **SUPPORTED, descriptively** (+0.18 travel on 10 co-solved roots; no test) |
| modal-top1 incomplete | **SUPPORTED, descriptively** (0 rare modes, −1 root) |
| index coverage is the bottleneck | **PARTIAL**: 27.6 % of held-out moves have no certifiable other-root witness |
