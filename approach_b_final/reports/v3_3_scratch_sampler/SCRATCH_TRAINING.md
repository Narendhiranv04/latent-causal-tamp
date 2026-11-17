# V3.3 scratch TaskCVAE training — 12 fits (TRAIN; checkpoint chosen on VALIDATION ELBO)

## Recipe (registered in `EXPERIMENT_REGISTRY.json` before training)

- **Model.**
  - `placement.TaskCVAE`, variant `scratch_all`: hidden 128, latent 8, task branch on, task input unchanged.
  - Random initialization (`torch.manual_seed(seed)`, then construction on CPU).
  - **No** Q2 or pretrained weights, and no resume.
- **Supervision.** Every positive assignment (`assign="all"`), with root-balanced weights (`DATA_AUDIT.md`).
- **Objective.** Weighted negative conditional ELBO (reconstruction + β·KL), β_max 1, warmed up over the first 10 evaluations.
- **Optimizer.** AdamW, learning rate 1e-3, weight decay 1e-4, batch 256.
- **Matched budget.** Equal optimizer steps for both arms, set to 80 epochs of the S-control data:
  - 2D: 2,400 steps, VAL every 30 steps.
  - 3D: 1,520 steps, VAL every 19 steps.
  - Batches are slices of seeded permutations of each arm's own examples. No early stopping.
- **Checkpoint.** Minimum VAL weighted −ELBO on the identical base-snapshot VAL targets (2D: 860 examples on 404 roots; 3D: 455 on 219).
- **Code.** `placement.fit_task(..., train_snap, val_snap, device)` with `cfg["steps"]`, via the environment switches `V33_TRAIN_SNAP`, `V33_VAL_SNAP`, `V33_STEPS`, `V33_EVAL_EVERY` and `ABF_DEVICE`.
  - The old defaults (V2 TRAIN snapshot, CUDA, 80 epochs with patience 15) are unchanged when no switch is set.
- **Host.** girish RTX 3080 Ti Laptop GPU (16 GB, measured idle before use), torch 2.10.0+cu128.
  - Each fit took 4–7 s, with peak GPU memory of about 66 MiB.
  - A CPU path is exercised by `tests/test_v33.py`.

## Smoke gate (seed 0, both arms, both domains): PASS

- Training and VAL ELBO are finite.
- Initial `state_dict` sha256 is identical across arms for each seed (table below).
- Legal-mask assertions held inside `repair_data`, and the target sets are non-empty.
- **Budget rule:** if the best VAL ELBO fell on the final evaluation, the budget would be doubled. It never did: best steps were 437–1,170 of 1,520–2,400, so the budget was not doubled.

## All fits

| Domain | Arm | Seed | Train examples / roots | Best VAL −ELBO | VAL rec / KL at best | Best step / budget | Data epochs at best | Init sha256 (12) | Checkpoint sha256 (12) | Wall s |
|---|---|---|---|---|---|---|---|---|---|---|
| 2D | S-control | 0 | 7,591 / 1,913 | 2.7248 | 2.724 / 0.0006 | 510 / 2400 | 17.2 | `79d9991d410c` | `fe8f3eee4234` | 6.6 |
| 2D | S-control | 1 | 7,591 / 1,913 | 2.7277 | 2.727 / 0.0004 | 570 / 2400 | 19.2 | `cd4b5468f6a4` | `5562c06027ab` | 6.6 |
| 2D | S-control | 2 | 7,591 / 1,913 | 2.7458 | 2.745 / 0.0005 | 480 / 2400 | 16.2 | `bea7d7c00c6c` | `835fc76d5188` | 6.6 |
| 2D | S-expanded | 0 | 9,729 / 1,938 | 2.7380 | 2.737 / 0.0006 | 810 / 2400 | 21.3 | `79d9991d410c` | `a01f25eba316` | 6.5 |
| 2D | S-expanded | 1 | 9,729 / 1,938 | 2.7359 | 2.735 / 0.0006 | 1170 / 2400 | 30.8 | `cd4b5468f6a4` | `44e5b801c998` | 6.8 |
| 2D | S-expanded | 2 | 9,729 / 1,938 | 2.7063 | 2.706 / 0.0006 | 780 / 2400 | 20.5 | `bea7d7c00c6c` | `e3d2b9ae62af` | 6.7 |
| 3D | S-control | 0 | 4,782 / 1,136 | 1.9842 | 1.984 / 0.0001 | 532 / 1520 | 28.5 | `f6b833b851fb` | `e73e6a8cf3da` | 3.8 |
| 3D | S-control | 1 | 4,782 / 1,136 | 2.0562 | 2.056 / 0.0002 | 494 / 1520 | 26.4 | `6b22ad8a2e35` | `5f9967836ed7` | 4.0 |
| 3D | S-control | 2 | 4,782 / 1,136 | 1.9960 | 1.996 / 0.0002 | 437 / 1520 | 23.4 | `9788e3fece04` | `8bfd1f72bc6b` | 4.1 |
| 3D | S-expanded | 0 | 6,807 / 1,158 | 1.9344 | 1.934 / 0.0001 | 665 / 1520 | 25.0 | `f6b833b851fb` | `6a0e26c47781` | 4.2 |
| 3D | S-expanded | 1 | 6,807 / 1,158 | 1.9844 | 1.984 / 0.0002 | 608 / 1520 | 22.9 | `6b22ad8a2e35` | `4dda1041202f` | 4.3 |
| 3D | S-expanded | 2 | 6,807 / 1,158 | 2.0384 | 2.038 / 0.0003 | 532 / 1520 | 20.0 | `9788e3fece04` | `ede0a7dd764d` | 4.3 |

**Seed-mean best VAL −ELBO.**

| Domain | S-control | S-expanded | Difference (expanded − control) |
|---|---|---|---|
| 2D | 2.733 | 2.727 | −0.006 |
| 3D | 2.012 | 1.986 | −0.026 |

The differences are small relative to seed spread (2D 0.02, 3D 0.07).

**Observations.**
- **Posterior collapse in both arms.** VAL KL at the selected checkpoint is ≤ 0.0006 nats, so the latent is effectively unused. Each sampler is close to a conditional categorical over destinations, and the 64-draw S1 marginal is close to the decoder softmax. This holds equally for both arms, so it does not confound the contrast. It is a property of this recipe, not a V3.3 change.
- **Overfitting after the optimum** (`figures/training_curves.png`). S-control VAL ELBO rises steeply, to 5.3 nats at step 2,400 in 2D. S-expanded rises much more slowly (3.0 nats). The additional positives act as a regularizer. The best-VAL checkpoint rule removes this from the evaluated models.

## Checkpoint provenance and availability

- Each checkpoint stores `prov`: the train and VAL snapshot paths and sha256, the Q2 scaler sha256, `init = scratch`, the init state sha256, the device and the torch version.
- Full sha256 values are in `MODELS_SHA256`, and per-fit curves (train / VAL ELBO, reconstruction and KL per evaluation) in `train_curves/`.
- **Immutable copies:**
  - girish: `~/abf_v33/runs/v33/<arm>/<dom>/scratch_all_s<seed>/`
  - user's laptop, read-only: `~/abf_v33/models/`
  - The two copies were hash-verified identical.
- The checkpoints are **not** committed to git. Git LFS was not approved; they are about 1.3 MB each.
