# V3.2 stage 2 — Phase D: matched D-control vs D-expanded training (E3)

## What changes and what does not

| | D-control | D-expanded |
|---|---|---|
| Snapshot | `abf_v3_e8a496bc66266fca`: the frozen V3 D's own training data (V1 + V2 + V3-4 TRAIN labels) | `abf_v32_fb0eef4f5ff433ee`: identical, plus the Phase C TRAIN labels |
| TRAIN roots | 3,500 (2D) / 1,766 (3D); the same roots in the same file order | the same 3,500 / 1,766 roots; only the label sets of 449 / 305 roots grow |
| VAL rows used for checkpoint selection | identical bytes (751 / 364 roots, historical VAL labels) | identical |
| Architecture / objective | `xy.XYNet` arm D, exact root-marginal X/Y NLL (`xy.py`, unchanged) | same |
| Initialisation | `torch.manual_seed(seed)` | same seed, so identical initial weights |
| Batch partition | `np.random.default_rng(seed)` over the same roots, batch 64 | identical partition (same root count and order) |
| Optimiser / steps | AdamW lr 1e-3, weight decay 1e-4, grad-clip 10; fixed 60 epochs (`XY_PATIENCE=60`), same number of optimiser steps | identical |
| Checkpoint rule | lowest VAL NLL epoch | identical |
| Seeds | 0, 1, 2 (after a seed-0 smoke run) | 0, 1, 2 |

The only controlled variable is the evidence: the additional physically labelled exhaustive-distribution X/Y outcomes. Model seeds share the same labelled data; they are not independent data collections. The frozen historical V3 D checkpoints (`v3_5/p2_*/D_s*`) are kept untouched as an external reference.

## Fidelity of the control

D-control reproduces the original V3-5 recipe within seed variation:

| Domain | Frozen V3-5 D, best VAL NLL (seeds 0 / 1 / 2) | D-control, best VAL NLL |
|---|---|---|
| 2D | 1.6544 / 1.6425 / 1.6722 | 1.6642 / 1.6603 / 1.6492 |
| 3D | 1.5159 / 1.3038 / 1.3456 | 1.3951 / 1.2999 / 1.3332 |

They differ because the hardware differs and the V3-5 run used early stopping (patience 10). Byte identity is not expected.

## Training runs (Blackwell RTX PRO 5000, one pinned CPU, nice 10; `D/train_curves/`)

| Domain | Arm | Seed | Best VAL NLL | Best epoch | Epochs run | Wall s | TRAIN roots | GPU peak MiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2D | control | 0 | 1.6642 | 54 | 60 | 40.1 | 3500 | 144.2 |
| 2D | control | 1 | 1.6603 | 46 | 60 | 40.3 | 3500 | 141.1 |
| 2D | control | 2 | 1.6492 | 40 | 60 | 40.3 | 3500 | 149.1 |
| 2D | expanded | 0 | 1.6955 | 48 | 60 | 33.9 | 3500 | 162.4 |
| 2D | expanded | 1 | 1.6784 | 48 | 60 | 34.0 | 3500 | 158.4 |
| 2D | expanded | 2 | 1.7168 | 34 | 60 | 34.0 | 3500 | 168.0 |
| 3D | control | 0 | 1.3951 | 57 | 60 | 21.0 | 1766 | 93.0 |
| 3D | control | 1 | 1.2999 | 51 | 60 | 21.0 | 1766 | 96.2 |
| 3D | control | 2 | 1.3332 | 59 | 60 | 20.9 | 1766 | 96.2 |
| 3D | expanded | 0 | 1.3626 | 57 | 60 | 17.8 | 1766 | 107.5 |
| 3D | expanded | 1 | 1.3165 | 59 | 60 | 17.7 | 1766 | 122.6 |
| 3D | expanded | 2 | 1.4442 | 45 | 60 | 17.7 | 1766 | 103.0 |

- **Training cost.** 12 fits took about 5.6 GPU-minutes in total, so training cost is negligible next to teacher labelling (43 CPU-h) and exhaustive scoring.
- **Historical VAL NLL.** D-expanded is slightly worse in 2D (mean 1.697 vs 1.658) and mixed in 3D (1.374 vs 1.343). These historical VAL labels come from the V1/V2 candidate distribution, not the exhaustive pools the model is deployed on. NLL was never the pre-registered primary metric, which is physically verified top-1 success on exhaustive VAL pools (`E_FINAL_EVALUATION.md`).

## Checkpoints

SHA-256 values are in `C/CONTROL_SHA256` and `C/EXPANDED_SHA256`.
- Mirrors: Blackwell `~/abf_v32/train/{control,expanded}`, laptop `~/abf_v32/train/`, girish `~/abf_v32_E/train/`.
- `*.pt` files are not committed to git. The project rule requires approval before Git LFS use; the checkpoints are about 1.9 MB each (12 files, about 23 MB) and can be added on request.
