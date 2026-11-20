# K≤3 ablation: P0–P3 (source/host audit, harness, pilot, training)

| | |
|---|---|
| Branch | `naren/k3-ablation-gvlab2-20261120` |
| Base | `c72eb1ef75` (V3.4 final benchmark) |
| Host | gvlab2 (`cstar`) |
| Work root | `/home/projects/long-horizon/naren_workspace/k3abl` |

Machine-readable sources (in `manifests/`): `EXPERIMENT_LOCK.json`, `GATES_P0.json`, `CPU_GPU_POLICY.json`, `TESTS_P1.json`, `PARITY_FULL_VAL_{2d,3d}.json`, `P2_PILOT_STATS.json`, `FITS_LOG.jsonl`.

## P0: sources and host (21 of 21 gates PASS)

### Data

**Original snapshot** `abf_9de85710c2a7103f`:
- Sha256: 2D `16222ff8…`, 3D `1627f34b…`. Both match the lock.
- 2D counts: TRAIN/VAL/TEST 3,500/751/749; K0/K1/K2/K3/NONE 1,250/800/800/1,150/1,000.
- 3D counts: TRAIN/VAL/TEST 1,766/364/370; K0/K1/K2/K3/NONE 511/357/612/612/408.

**Expanded TRAIN snapshot** `abf_v32_fb0eef4f5ff433ee` (2D `963c16b2…`, 3D `bc03d896…`):
- Same roots and splits as the original.
- VAL/TEST rows are byte-identical to the original.
- Added labels are TRAIN-only. **No TEST label enters any fit.**

**V3.4 cohort.** 0 of its 1,114 root ids appear in either snapshot. Only its id list, which is metadata, was copied to gvlab2.

**Evaluation masks:**

| Mask | 2D VAL / TEST | 3D VAL / TEST |
|---|---|---|
| eval_task | 413 / 412 | 220 / 241 |
| eval_noop | 188 / 187 | 85 / 67 |
| eval_abstain | 150 / 150 | 58 / 62 |

**Labels.** Y is shared per endpoint in both domains.

### Models

The frozen bundle (sampler `scratch_all` s0 and D scorer s0/s1/s2 per domain, plus scalers) matches both the `final_protocol.yaml` pins and the bundle manifest exactly.

### Teachers

On gvlab2 the teachers run from:
- 2D: `abf_v2/env2d` (Python 3.13), `bxy_teacher.py` `c18ac91c89b9`, `p16_motion.py` `43f4c38c6418`.
- 3D: `abf_v2/env3d` (MuJoCo 3.16), `fin3d.py` `29eb0b29ba76`, `bwlphys.py` `259652f14dab`, `bd_3dt.py` `62dc853ccb50`, `bd_shelf.py` `ef71dcf43c6d`.

All hashes are identical to the laptop reference.

### Host

| Resource | Value |
|---|---|
| CPUs | 48 logical, no cgroup quota |
| RAM | 125 GiB; swap 32/32 GiB used by other workloads |
| Disk | 34 GiB free (`/home` 99% full), so outputs are kept small |
| GPU | RTX 5090, 32 GiB, driver 580.95, torch 2.9.1 + CUDA 13.0, cuDNN 9.13 |

**CPU policy.** Every ablation process runs under `taskset -c 0-42`, which children inherit. The affinity observed inside the tree is 43. Five CPUs (43–47) are never used. Every worker has `OMP`/`MKL`/`OPENBLAS`/`NUMEXPR` = 1 and one torch thread.

**Other users.** A teammate's process (`cpu_governor.py`) was idle. **Another user's GPU training job** (`sajid`, about 4.3 GiB) started during the run. It was left untouched, and GPU concurrency was capped so the total stayed below 32 GiB.

## P1: harness and FULL parity

**Code** (`approach_b_final/ablations_k3/`, all new; the original modules are unchanged):

| File | Role |
|---|---|
| `p0.py` | Preflight |
| `index.py` | Private indexes with sha-verified raw roots; lineage = `layout_root_id`; the pilot |
| `arms.py` | TaskFlowMatch; matched fits; Uniform4 / flow-matching proposals |
| `run.py` | Prediction harness |
| `verify.py` | Seal → union teach → evaluate |
| `lock.py` | Protocol lock |
| `analyze.py`, `figs_k3.py` | Tables and figures |
| `test_k3.py` | P1 tests |

**How each arm runs.** Every arm calls the unchanged `exhaustive.score_root`, which does three things:
1. enumerates every legal K1–K3 ordered sequence, with no cap;
2. scores them in streamed chunks of 8,192;
3. selects with the frozen rule, through `Selectors`, which is identical to `xy.choose`.

**FULL parity.** gvlab2 was compared with the bundle's recorded laptop-GPU VAL predictions:

| Domain | Proposals | Candidate counts | Decisions | max \|Δp11\| |
|---|---|---|---|---|
| 2D | 751/751 identical | 751/751 identical | 751/751 identical | 4.8e-7 |
| 3D | 364/364 identical | 364/364 identical | 364/364 identical | 3.0e-7 |

**P1 tests: 25 of 25 PASS.** They cover:
- Uniform4 legality and determinism;
- TaskFM: finite loss, non-zero task-context gradient, legal unique proposals, 64×32 evaluations;
- the no-task branch is zero and otherwise matched to `scratch_all`;
- C1 makes exactly one candidate with one scorer call, deterministically and label-blind;
- G gives identical scores for every permutation of one endpoint;
- DIRECT outputs p_succ with no marginals;
- resumable and idempotent prediction.

## P2: cost / coverage pilot (100 TRAIN + 50 VAL per domain, K-stratified, never TEST)

**Pilot composition:**
- 2D: 110 original, 21 dependence-seeking, 19 hard-order roots.
- 3D: 128 published, 14 + 5 hard-order, 3 run-dependent.

| Arm | Domain | Candidates/root mean (p99 / max) | Latency mean / p99 s | GPU peak MiB |
|---|---|---|---|---|
| FULL | 2D | 48,201 (195,008 / 197,102) | 2.42 / 10.6 | 337 |
| Uniform4 | 2D | 80,507 (351,366 / 353,320) | 4.11 / 18.8 | 337 |
| M1 | 2D | 323 (1,862 / 2,326) | 0.03 / 0.14 | 103 |
| C1 | 2D | 1 | 0.03 | 14 |
| FULL | 3D | 4,264 (27,151 / 37,248) | 0.19 / 1.22 | 225 |
| Uniform4 | 3D | 4,942 (30,259 / 42,794) | 0.22 / 1.33 | 225 |

**Other pilot facts:**
- Eligible objects per root: 2D p50/p99 9/19; 3D 4/9.
- Each CUDA process holds about 1.4 GiB of context. So concurrency is GPU-memory-bound, not CPU-bound: at most about 18 processes, after allowing for the other user's job.
- **Teacher cost** (TRAIN pilot, union of 4 arms, 38 workers):
  - 2D: 177 queries, 13.8 CPU-s per query, 546 s wall.
  - 3D: 188 queries, 34.3 CPU-s per query, 263 s wall.
  - These figures size the VAL/TEST verification pools.
- **No VAL root was taught during P2.**

## P3: training (TRAIN fit, VAL selection, seeds 0/1/2)

| Control | Procedure | VAL criterion (s0 / s1 / s2) |
|---|---|---|
| E | `xy.fit`, the frozen D procedure (60 epochs, batch 64, lr 1e-3, patience 10, expanded TRAIN) | 2D 1.697/1.689/1.728; 3D 1.352/1.364/1.467 (X/Y NLL) |
| G | same | 2D 1.887/1.901/1.939; 3D 1.584/1.531/1.552 |
| DIRECT | same (binary Z BCE, root sum; **not comparable** with X/Y NLL) | 2D 1.237/1.334/1.278; 3D 1.303/1.219/1.252 |
| No-task cVAE | `placement.fit_task(scratch_all_notask)` = `scratch_all` with the task input zeroed: same scratch init (sha `79d9991d410c`), examples, weights, steps (2D 2,400 / 3D 1,520), eval cadence | weighted −ELBO 2D 2.775/2.759/2.787 vs `scratch_all` 2.738; 3D 2.117/2.077/2.139 vs 1.934 |
| TaskFlowMatch | `TaskEncoder` + FlowMatch field, same examples, weights, batch, optimizer and steps; VAL = weighted FM loss with a fixed eval generator | 2D 1.334/1.346/1.342; 3D 1.369/1.382/1.403 (FM loss, not comparable with ELBO). Parameters: 2D 296,962, 3D 287,490 |

**Pipeline reproduction (never used as the reference):**
- **`scratch_all` s0 refit:** reproduces the frozen sampler *bit-for-bit* (2D best VAL 2.738048553466797 at step 810; 3D best at step 665).
- **D refit:** same best epoch, VAL NLL within ±0.03 of the frozen D. It is kept as the **diagnostic arm `DREFIT`**, which separates the training-environment effect from the architecture effects of E/G/DIRECT. The frozen D (FULL) stays the reference.

**Teacher-free VAL scorer metrics** (frozen VAL labels; `tables/scorer_val_*.json`) are summarized in P7. G's same-endpoint order ranking is exactly 50%, as expected: its scores are permutation-invariant, so every pair is a tie.
