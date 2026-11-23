# Original-root set-MCTS for K < 3 (K1 / K2)

The controlling methodology is `plan.md`, copied unchanged. **Verdict: NULL.** Set-MCTS gives the same verified success as exhaustive K ≤ 2 but is slower; see `reports/P4_FINAL_DECISION.md`.

## Files

| File | Role |
|---|---|
| `search_sets.py` | model-agnostic core: Pool, budgeted Oracle, frozen `choose`, and the arms EXACT_K2 / RAND_SET / BEAM_SET / UCT_SET / PW_UCT_SET |
| `run.py` | frozen-model driver, public inputs only: `p0`, `pilot` (DEV tuning grid), `eval` (frozen protocol, replay), `live` (timing subset) |
| `analyze.py` | `tune`, `model`, `manifest` and `physical`. The last two are evaluator-side and read private K, masks and teacher caches only after sealing |
| `figs.py` | `roots` (real VAL scenes, explored sets, X/Y-chosen order), `curves` (model-only agreement and live wall time), `physical` (verified success) |
| `tests/test_sets.py` | 13 contract and parity tests |

## Reproduce

Laptop GPU. The defaults read `~/abf_v34/approach_b_bundle`, `~/abf_v34/parity/public_val_2d.jsonl` and `~/abf_v34/parity/pred_val_2d_gpu.jsonl`, and write to `~/mcts_sets_runs`.

```
python -m pytest approach_b_final/mcts_sets/tests -q                    # 13 passed
python run.py p0 --n 40                                                 # hashes, K<=3 parity 40/40, batch invariance
python run.py pilot && python analyze.py tune ~/mcts_sets_runs/pilot_dev.jsonl    # DEV-only tuning -> reports/P2_FROZEN_PARAMS.json
python run.py eval && python run.py live                                # sealed EVAL predictions; live timing subset
python analyze.py model ~/mcts_sets_runs/eval_val.jsonl EVAL reports/MODEL_SUMMARY_EVAL.json
# evaluator side (private files under ~/mcts_sets_private, never committed):
python analyze.py manifest ~/mcts_sets_runs/eval_val.jsonl PRIVATE_VAL_2D CACHE_K3ABL,CACHE_K3VAL JOBS.jsonl
#   gvlab2: source k3abl/env.sh; export V3OUT=<new dir>; $PY2D -c "import benchmark as BM; BM.teach('2d', JOBS, CACHE_DIR, 32, 8)"
python analyze.py physical ~/mcts_sets_runs/eval_val.jsonl PRIVATE_VAL_2D CACHE_K3ABL,CACHE_K3VAL,CACHE_MCTS
python figs.py roots && python figs.py curves && python figs.py physical
```

## Reports, in order

1. `reports/P0_SOURCE_AUDIT.md`, `P0_FROZEN_PROTOCOL.json`, `P0_GAPS.md`, `P0_TESTS.json`, `P0_EMPIRICAL.json`
2. `reports/P1_PARITY_TESTS.md`
3. `reports/P2_TUNING.json`, `P2_FROZEN_PARAMS.json`, `P2_PREREG.md`, `P2_PREDICTIVE_PILOT.md`, `MODEL_SUMMARY_*.json`, `P2_EVAL_PREDICTIONS.jsonl.gz`, `P2_LIVE_TIMING.jsonl`
4. `reports/P3_SEAL.json`, `P3_MANIFEST.json`, `P3_PHYSICAL_VAL.md` / `.json` / `_STRICT.json`, `P3_PER_ROOT*.jsonl`
5. `reports/P4_FINAL_DECISION.md`, `figures/`
