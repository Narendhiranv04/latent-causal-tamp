# X/Y repair ranking (K1/K2, 2D)

`plan.md` (v1.0) is the controlling contract and `starting_prompt.md` is the owner prompt. The verdict is in `reports/P6_FINAL_DECISION.md`: **NO_ESTABLISHED_IMPROVEMENT (development only). Keep A0 + EXACT4.**

## Files

| File | Role |
|---|---|
| `rr.py` | Paths, family DEV_CAL/DEV_AUDIT split, read-only X/Y readout (b, a, w, pY, pX1, pX0, pX, p11 from logits), frozen cVAE ranks, strict exact-contract labels |
| `audit.py` | P0: provenance, 40-root parity, TRAIN coverage, partition and leakage, reconciliation, CONFIRM pool |
| `diagnostics.py` | P1: candidate tables, calibration per factor, within-root ranking, decision decomposition |
| `calibration.py` | P2: frozen-scorer rules F0–F5 and the anchored F4 |
| `collect.py` | P3: sealed TRAIN acquisition manifest, teacher jobs, strict merge into the private augmented snapshot |
| `train_rank.py` | P4: warm-start A1–A4 (exact NLL ± within-root hinge), DEV_CAL selection |
| `run_eval.py` | Planner-only inference (public rows + checkpoint), live timing |
| `evaluate_rank.py` | P5 DEV matrix (cached labels); P6 seal, jobs and physical (prepared, not run) |
| `figures.py` | `reports/figures/p0..p4_*.png` |
| `tests/test_rr.py` | 11 contract tests; the 39 historical tests also pass |

## Reproduce (laptop RTX 5060; teacher on gvlab2)

```
python audit.py all && python figures.py p0
python diagnostics.py build && python diagnostics.py report && python figures.py p1
python calibration.py d12 && python calibration.py run && python figures.py p2
python collect.py manifest     # then gvlab2: teach.sh p3_jobs_2d.jsonl (benchmark.teach, 32 workers)
python collect.py merge ~/xyrr_private/p3_cache/verify_2d.jsonl && python figures.py p3
for a in A1 A2 A3 A4; do for s in 0 1 2; do python train_rank.py $a $s; done; done; python train_rank.py select && python figures.py p4
python run_eval.py predict ~/xyrr_runs/p5/public_dev_k012n.jsonl CKPT OUT EXACT4,EXACT6,BEAM_SEEDED4@1024,BEAM_FULL@1024,PW_MCTS_SEEDED4@1024
python evaluate_rank.py dev A0=pred_A0.jsonl,A4s0=pred_A4s0.jsonl
python -m pytest tests ../full_domain_sets/tests ../mcts_sets/tests -q     # 50 passed
```

Private data is never committed: labels, caches, the augmented snapshot and the CONFIRM index live in `~/xyrr_private`; checkpoints and tables in `~/xyrr_runs`.

## Reports, in order

P0_AUDIT · P1_DIAGNOSTICS · P2_PREREG → P2_FROZEN_INFERENCE · P3_COLLECTION_PREREG (+ sealed manifest) → P3_LABEL_AUDIT · P4_TRAIN_PREREG → P4_LEARNING · P5_P6_PREREG → P5_MODEL_ONLY · **P6_FINAL_DECISION**
