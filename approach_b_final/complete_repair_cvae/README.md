# Complete-repair cVAE ablation (RSS RQ1)

`plan.md` (v1.0) is the controlling contract and `starting_prompt.md` the owner prompt; both are byte copies. Amendments go in `AMENDMENTS.md`. Reports are in `reports/`, in phase order.

## Status

| Phase | Status | Report |
|---|---|---|
| P0 audit | PASS | `P0_DATA.md`, `P0_PREREG.md`, `P0_PROVENANCE.json`, `P0_COHORT.json`, `P0_PARITY_*.json` |
| P1 data + architecture | PASS | `P1_IMPL.md` |
| P2 train + DEV + freeze | PASS | `P2_DEV.md`, `P2_TRAIN.json`, `P2_DEV_*.json`, `P2_FREEZE.json` |
| P3 sealed cohort predictions | PASS | `P3_SEAL.json`, `P3_MODEL_ONLY.json`, `sealed/` |
| P4 physical verification | PASS (2D 450 / 3D 434 queries) | `P4_PHYSICAL.md`, `P4_QUERY_MANIFEST*.json` |
| P5 decision | **done** | **`P5_FINAL_DECISION.md`**, `P5_STATS.json`, `P5_ATTRIBUTION.json`, `P5_PER_ROOT.jsonl` |

## Environment

Laptop (RTX 5060 8 GB, 32 threads), `~/miniconda3` python with torch 2.9.1+cu128. Private data and checkpoints stay outside git: `~/cr_cvae_private` (cohort roster with K), `~/cr_cvae_runs` (checkpoints, pools, predictions). Teachers: `~/abf_v3_laptop/env2d`, `env3d` (the V3.4 runtime).

## Commands (run from this directory)

```
python p0_audit.py provenance && python p0_audit.py data && python p0_audit.py parity_ids && python p0_audit.py roster
for d in 2d 3d; do python infer.py parity $d ~/abf_v34/parity/public_val_$d.jsonl ~/abf_v34/parity/pred_val_${d}_gpu.jsonl reports/P0_PARITY_IDS.json reports/P0_PARITY_$d.json; done
python -m pytest tests -q                                   # 33 passed
CR_DEVICE=cpu python train.py overfit 2d 16 && CR_DEVICE=cpu python train.py overfit 3d 16
python viz.py p0 && CR_DEVICE=cpu python viz.py p1
for d in 2d 3d; do for s in 0 1 2; do python train.py fit $d $s; done; done
python evaluate_cr.py devids; python infer.py predict 2d ~/abf_v34/parity/public_val_2d.jsonl ~/cr_cvae_runs/models/2d/cr_s0/model.pt OUT --c0   # (+ seeds, --controls --ids, timing)
python evaluate_cr.py dev 2d OUT [SEED_OUTS]; python evaluate_cr.py freeze
python evaluate_cr.py public; python infer.py predict {2d,3d} ~/cr_cvae_runs/p3/public_{dom}.jsonl CKPT ~/cr_cvae_runs/p3/pred_{dom}.jsonl --c0 --controls
python evaluate_cr.py seal reports/P2_FREEZE.json && python evaluate_cr.py manifest      # commit + push before any teacher call
python evaluate_cr.py teach 3d 20; python evaluate_cr.py teach 3d; python evaluate_cr.py teach 2d
python evaluate_cr.py manifest2; python evaluate_cr.py teach 3d 0 2; python evaluate_cr.py teach 2d 0 2
python evaluate_cr.py per_root && python evaluate_cr.py stats && python evaluate_cr.py attribution && python viz.py p5
```
