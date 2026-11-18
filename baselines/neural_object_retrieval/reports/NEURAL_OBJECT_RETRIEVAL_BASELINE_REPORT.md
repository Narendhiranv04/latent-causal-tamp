# NOR-Grid: ICRA 2024 adapted baseline (validation-split results)

**What it is.**
- An adaptation of Ren & Qureshi, *Neural Rearrangement Planning for Object Retrieval from Confined Spaces Perceivable by Robot's In-hand RGB-D Sensor*, ICRA 2024, arXiv:2402.06976.
- OSNet + RPNet, placed in the Approach B K ≤ 3 target-repair benchmark.
- It is not a reproduction of the paper. Adaptations and fidelity limits: `METHOD_SWITCH_AND_FIDELITY.md`.
- Data, labels and leakage: `DATA_AND_LABEL_AUDIT.md`.

**Compute.** Laptop only: CPU plus RTX 5060 GPU.

**Splits.**
- Results use the VALIDATION split only.
- TEST outcomes were never opened.
- The ongoing V3.4 held-out cohort was never read.

## 1. Protocol

| Item | Value |
|---|---|
| Primary configuration (fixed before any VAL outcome) | `full_s0`, policy `full`, rule NOR_RULE_V1: stop at the first prefix with STOP p ≥ 0.5, else ABSTAIN after 3 steps; NOOP if p(S0) ≥ 0.5 |
| Inference | One-shot, open-loop. ≤ 3 hypothetical OSNet → RPNet steps, then a NOOP / REPAIR / ABSTAIN record |
| Verification | Sealed prediction files (`benchmark.py seal`) are verified **after** sealing by the unchanged physical X/Y teachers |
| Task metric | Verified X = 1 and Y = 1 on K1–K3 roots. UNKNOWN is excluded, never counted as failure. There were 0 UNKNOWN in every run |
| CIs | 95%, stratified by K, cluster bootstrap over layout-lineage groups (2,000 resamples). Contrasts are **paired** on the same roots |
| Seeds | s0 / s1 / s2 on the full VAL split. s0 is primary; the seed mean is reported as well |
| Ablations | On the registered **VALSUB**: 60 VAL roots per class, chosen in sha256(root_id) order. Registered before any ablation outcome was seen (`VALSUB_REGISTRATION.json`). Each ablation's predictions are the rows of its sealed full-VAL file, so the parent seal hash is recorded |

## 2. Primary results (full VALIDATION, seed 0)

| | 2D (751 roots, 413 task) | 3D (364 roots, 220 task) |
|---|---|---|
| **Task success** | **25.2% [21.6, 29.1]** | **24.1% [18.6, 29.6]** |
| K1 / K2 / K3 | 47.5 / 32.5 / 4.6 | 39.6 / 30.9 / 2.9 |
| NOOP correct (K0) | 97.9% | 84.7% |
| ABSTAIN correct (NONE) | 96.0% | 100% |
| False repairs on NONE | 6 | 0 |
| Repair attempts: success / FAIL_X / FAIL_Y | 298: 104 / 137 / 57 | 119: 53 / 38 / 28 |
| UNKNOWN | 0 | 0 |
| Latency p50 / p99 (GPU, per root) | 22 / 33 ms | 16 / 26 ms |
| Seed mean task (s0 / s1 / s2) | **27.1%** (25.2 / 28.3 / 27.9) | **23.3%** (24.1 / 25.9 / 20.0) |

### Paired contrast vs the frozen Approach B final model (same VAL roots)

**Approach B on these roots:** 2D 57.1%, 3D 78.2%. This matches the earlier VAL s0 values.

| | 2D | 3D |
|---|---|---|
| NOR s0 − Approach B | **−32.0 pp [−37.8, −26.6]** | **−54.1 pp [−61.8, −46.8]** |
| NOR seed mean − Approach B | −30.0 pp [−35.1, −24.9] | −54.9 pp [−61.2, −48.3] |
| Approach B K1 / K2 / K3 | 69.2 / 71.7 / 38.7 | 73.6 / 83.5 / 74.3 |

**Where the gap is.**
- **K3:** NOR-Grid almost never solves three-step repairs (≤ 7% in either domain).
- **K1/K2:** the gap is moderate.
- **2D failures:** mostly FAIL_X, i.e. a predicted placement that is physically infeasible. This is consistent with RPNet ranking regions by homotopy cost alone, with no learned feasibility check.
- **3D failures:** more evenly split between FAIL_X and FAIL_Y.
- **K0/NONE gating:** comparable to Approach B. This gating comes from the STOP adapter, which is not part of the paper's architecture.

## 3. Ablations (VALSUB, paired vs NOR s0 on the same roots)

| Variant (what changes) | 2D Δ task (n = 180) | 3D Δ task (n = 173) |
|---|---|---|
| `osnet_only`: RPNet replaced by the analytic rule "nearest legal cell to the object's current cell" | −0.6 [−7.8, 6.7] | **−10.4 [−17.3, −3.5]** |
| `rpnet_only`: OSNet replaced by the analytic rule "eligible object nearest to the target" | −5.0 [−10.6, 0.6] | **−5.2 [−9.8, −1.2]** |
| `both_analytic`: neither network | **−8.3 [−15.6, −1.1]** | **−11.6 [−18.5, −4.6]** |
| `nogoal`: goal tokens zeroed in training and inference | **−8.3 [−15.6, −1.1]** | −5.2 [−12.1, 1.7] |
| `no_stop`: STOP adapter ignored. The full rollout runs (≤ 3 steps, until no eligible object or legal move is left); REPAIR if any move was made, else ABSTAIN | −3.9 [−9.4, 1.7]; NOOP 0%, NONE false repairs 60/60 | +1.7 [−2.9, 6.4]; NOOP 0%, NONE false repairs 58/58 |

**Reading.**
- **Both networks together add value** in both domains (`both_analytic` is significantly worse).
- **2D:** the gain comes mainly from OSNet; learned placement is not distinguishable from the analytic rule.
- **3D:** both OSNet and RPNet contribute significantly.
- **Goal conditioning:** helps in 2D; in 3D the CI includes 0.
- **Removing STOP:** task change is not significant in either domain (2D −3.9, 3D +1.7), but abstention and NOOP collapse completely. So the adapter is what makes K0/NONE behaviour competitive at all.

## 4. Training cost

| | 2D | 3D |
|---|---|---|
| TRAIN reference-path labels | 3,500 roots, 11.7 CPU-h | 1,766 roots, 5.0 CPU-h |
| OSNet / RPNet / STOP params | 434k / 718k / 318k | same |
| GPU training wall time per seed (OS + RP + ST) | ≈ 5 min (peak 0.4 GiB) | ≈ 2.3 min (peak 0.2 GiB) |
| Physical verification of an additional full-VAL seed (unchanged teachers, laptop CPU, shared query cache) | ≈ 10 min | ≈ 17 min |

## 5. Figures

| Figure | What it shows |
|---|---|
| `figures/P2_labels_{2d,3d}.png` | TRAIN reference-path sweeps, the majority-rule region costs, and OSNet blocking targets for example roots |
| `figures/P5_{2d,3d}_K*_*.png` | Per-domain examples: S0, OSNet distribution, RPNet cost map, chosen placement and verified outcome. Covers K2 SUCCESS, K3 SUCCESS, K3 FAIL_X, K1 FAIL_Y and NONE ABSTAIN |

## 6. Not run, or blocked

| Item | Status | Reason |
|---|---|---|
| Native closed-loop NOR (re-perceive after each move) | NOT_RUN | The benchmark is one-shot sealed. The paper's in-hand RGB-D re-perception has no counterpart here |
| Q2 placement auxiliary | NOT_RUN | Q2 trials are not in the local snapshot (NOT_LOCAL) |
| REAP / DISCO comparators | NOT_RUN_COMPARATOR | Out of scope for this contract. DISCO runs separately on other hosts |
| Witnessed (executed) travel paths for homotopy labels | NOT_RUN | Collision-ignorant planner reference paths were used instead (documented adaptation) |
| Held-out TEST / V3.4 evaluation | NOT_RUN by design | The frozen configuration is ready: `NOR_FREEZE_MANIFEST.json` |

## 7. Freeze and reproduction

- **Manifest:** `NOR_FREEZE_MANIFEST.json` (written by `freeze.py`). It records:
  - commit;
  - SHA-256 of code, labels, tensors and every model checkpoint;
  - calibration temperatures;
  - every seal hash;
  - the VALSUB registration hash;
  - the exact held-out protocol commands.
- **Rule:** no retraining, recalibration, threshold or variant change is allowed after seeing held-out outcomes.
- **Commands:** `../README.md`.
