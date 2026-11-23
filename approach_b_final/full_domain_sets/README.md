# Full-legal-domain corrective action-set selection (K1 / K2)

`plan.md` (v1.1, copied unchanged) is the controlling contract. This is a follow-up to the completed fixed-pool study in `../mcts_sets/`, which ended NULL and is preserved untouched. The verdict is in `reports/P4_FINAL_DECISION.md`.

## Files

| File | Role |
|---|---|
| `domain.py` | Public legal action universe `A_legal = movable x Root.legal_dests(cells0)`. Frozen S1 cVAE marginal over **every** legal cell, rebuilt from the archived batched call; its top-6 equals the archived list on 751/751 roots. Tiers T4 / T56 / TTAIL; uniform-floor mixture prior. |
| `fsearch.py` | Budgeted batched `Oracle` (all orders or nothing, unique ordered charges, batch / wall limits); `Stage` (FULL or SEEDED4 tier release with early unlock on exhaustion); `Frontier` (prior-Gumbel priority with tier deferral); arms `EXACT4/6/FULL`, `RAND_FULL`, `BEAM_*` and `PW_MCTS_*`; frozen `xy.choose`. |
| `run.py` | Public inputs only. Modes: `p0` (parity), `pilot` (DEV grid), `dev` / `eval` (frozen protocol; offline full-table replay), `live` (live GPU timing subset). |
| `analyze.py` | Evaluator side; the **only** reader of private K, caches and generator labels. Modes: `recall` (P1), `tune`, `model`, `manifest`, `physical`, `attribution`, `latency`. |
| `figs.py` | `p1`, `alloc`, `curves`, `physical`. All figures use real public VAL scenes. |
| `tests/test_full.py` | 26 contract tests. The 13 historical tests in `../mcts_sets/tests` also pass. |

The module is named `fsearch.py` rather than the plan's suggested `search.py`, because a local `search.py` would shadow the frozen `approach_b_final/search.py`.

## Reproduce

The laptop GPU (RTX 5060) runs everything except the teacher. Defaults read `~/abf_v34/approach_b_bundle` and `~/abf_v34/parity/public_val_2d.jsonl`, and write to `~/fds_runs`. Private evaluator files live under `~/mcts_sets_private` and `~/fds_private` and are never committed.

```
python -m pytest approach_b_final/full_domain_sets/tests -q          # 26 passed
python run.py p0                                                     # hashes, top-6 parity, marginal support
python analyze.py recall PRIVATE GENLAB CACHE_K3ABL,CACHE_K3VAL,CACHE_MCTS ../mcts_sets/reports/P3_PER_ROOT.jsonl
python figs.py p1
for i in 0 1 2 3; do python run.py pilot --part $i/4 & done; wait      # DEV grid (P2_TUNING_PREREG)
python analyze.py tune ~/fds_runs/pilot_dev.0.jsonl,...               # -> reports/P2_FROZEN_PARAMS.json
for i in 0..k; do python run.py dev --part $i/k & python run.py eval --part $i/k & done
python run.py live --split DEV ; python run.py live --split EVAL       # live latency (GPU alone)
python analyze.py model ~/fds_runs/frozen_dev.*.jsonl reports/MODEL_SUMMARY_DEV.json
python analyze.py manifest ~/fds_runs/frozen_eval.*.jsonl PRIVATE CACHES JOBS.jsonl
#   gvlab2: source k3abl/env.sh; export V3OUT=<new dir>; $PY2D -c "import benchmark as BM; BM.teach('2d', JOBS, CACHE_DIR, 32, 8)"
python analyze.py physical EVALFILES PRIVATE CACHES+NEW FAMILIES reports/P3_PHYSICAL
python analyze.py attribution EVALFILES PRIVATE CACHES+NEW GENLAB reports/P3_PHYSICAL_PER_ROOT.jsonl reports/P4_ATTRIBUTION.json
```

## Result

**EXPANSION_NOT_ESTABLISHED (INCONCLUSIVE). Keep EXACT4.**

On VAL K1/K2 development roots:
- **Seeded MCTS vs EXACT4:** PW_MCTS_SEEDED4@1024 − EXACT4 = +1.4 pp strict [−2.1, +5.0]. EXACT4's strict UNKNOWN rate is 22.5 %.
- **Speed:** seeded MCTS takes 0.170 s against EXACT4's 0.027 s.
- **No arm adds value:** neither seeding nor MCTS beats the matched controls.
- **The full-domain model optimum is physically worse** than top-4: −4.4 pp strict, −5.8 pp operational.
- **Conclusion:** X/Y misranking of out-of-pool sets dominates cVAE destination recall.

See `reports/P4_FINAL_DECISION.md`.

## Reports, in order

1. **P0:** `P0_SOURCE_AUDIT.md`, `P0_FROZEN_PROTOCOL.json`, `P0_PARITY.json`, `P0_GAPS.md`
2. **P1:** `P1_RECALL.md` / `.json`, `P1_FIGURES.json`, `figures/p1_root_*.png`
3. **P2:** `P2_TUNING_PREREG.md`, `P2_TUNING.json`, `P2_FROZEN_PARAMS.json`, `P2_TESTS.json`, `P2_LOW_SINGLETON_FIXTURE.json`, `MODEL_SUMMARY_DEV.json`, `MODEL_SUMMARY_EVAL.json`, `P2_BUDGET_LATENCY_LIVE.json`, `P2_LIVE_REPLAY_PARITY.json`, `P2_MODEL_ONLY.md`, `figures/p2_*.png`
4. **P3:** `P3_PREREG.md`, `P3_SEAL.json`, `P3_EVAL_PREDICTIONS.jsonl.gz`, `P3_QUERY_MANIFEST.jsonl`, `P3_PHYSICAL.md` / `.json`, `P3_PHYSICAL_PER_ROOT.jsonl`
5. **P4:** `P4_FINAL_DECISION.md`, `P4_ATTRIBUTION.json`, `P4_WINLOSS_VS_EXACT4.json`, `figures/p4_physical_success.png`
