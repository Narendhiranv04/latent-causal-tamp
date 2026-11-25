# Complete-repair cVAE ablation (RSS RQ1)

`plan.md` (v1.0) is the controlling contract and `starting_prompt.md` the owner prompt; both are byte copies. Amendments go in `AMENDMENTS.md`. Reports are in `reports/`, in phase order.

## Status

| Phase | Status | Report |
|---|---|---|
| P0 audit | PASS | `P0_DATA.md`, `P0_PREREG.md`, `P0_PROVENANCE.json`, `P0_COHORT.json`, `P0_PARITY_*.json` |
| P1 data + architecture | PASS | `P1_IMPL.md` |
| P2 train + freeze | **blocked: needs owner affirmation of the resource envelope** | – |
| P3 sealed cohort predictions | blocked | – |
| P4 physical verification | blocked | – |
| P5 decision | – | – |

## Environment

Laptop (RTX 5060 8 GB, 32 threads), `~/miniconda3` python with torch 2.9.1+cu128. Private data and checkpoints stay outside git: `~/cr_cvae_private` (cohort roster with K), `~/cr_cvae_runs` (checkpoints, pools, predictions). Teachers: `~/abf_v3_laptop/env2d`, `env3d` (the V3.4 runtime).

## Commands (run from this directory)

```
python p0_audit.py provenance && python p0_audit.py data && python p0_audit.py parity_ids && python p0_audit.py roster
for d in 2d 3d; do python infer.py parity $d ~/abf_v34/parity/public_val_$d.jsonl ~/abf_v34/parity/pred_val_${d}_gpu.jsonl reports/P0_PARITY_IDS.json reports/P0_PARITY_$d.json; done
python -m pytest tests -q                                   # 33 passed
CR_DEVICE=cpu python train.py overfit 2d 16 && CR_DEVICE=cpu python train.py overfit 3d 16
python viz.py p0 && CR_DEVICE=cpu python viz.py p1
# P2 (after authorization): for d in 2d 3d; do for s in 0 1 2; do python train.py fit $d $s; done; done
```
