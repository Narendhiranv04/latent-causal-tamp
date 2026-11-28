# R8A: K ≤ 3 final evaluation (component ablations, generative architectures, 3D baselines)

**Cohort.** The V3.4 independent cohort (1,114 roots: 2D 719, 3D 395), used unchanged. Task success is measured on the K1–K3 roots (2D 394, 3D 239).

**Protocol.** Every arm:
1. was predicted from public rows only (`r8a.py`; Blackwell GPU);
2. was sealed before any teacher call;
3. was verified by the unchanged V3.4 teachers through one shared, deduplicated cache (`r8av.sh`, gvlab2), with no retries.

0 UNKNOWN outcomes in either domain.

**FINAL** = the clean R7 models: stage-A cVAE, then S1 top-4 proposals, then exhaustive ordered K ≤ 3 search, then frozen stage-B Y plus the selected GNN X, then the production rule. Each arm changes exactly one component.

**Paired comparison.** Same roots; percentage-point difference vs FINAL; 95% CI from a group-cluster bootstrap (2,000 resamples); two-sided sign test. Raw data: `reports/final/r8a/` (`R8A_PAIRED.json`, `SUMMARY_*`, per-root results).

## (a) Component ablations

| Component | Arm | 3D task % | Δ vs FINAL [95% CI] | 2D task % | Δ vs FINAL [95% CI] |
|---|---|---|---|---|---|
| — | **FINAL** | **80.3** | — | **59.9** | — |
| — | FINAL, other X seeds | — | — | 60.9 / 61.9 | +1.0 / +2.0 (n.s.) |
| reference | V3.4 production model (sealed) | 76.6 | −3.8 [−10.0, +2.1] | 51.8 | **−8.1** [−13.2, −3.0] |
| scoring | no X/Y coupling | 79.1 | −1.3 [−5.4, +2.9] | 50.3 | **−9.6** [−14.0, −5.3] |
| scoring | no ordering (order-invariant X) | 65.3 | **−15.1** [−21.3, −8.8] | 51.5 | **−8.4** [−12.7, −3.8] |
| scoring | direct Z | 78.2 | −2.1 [−7.1, +2.9] | 57.4 | −2.5 [−7.6, +2.3] |
| placement | uniform (4 legal cells) | 66.1 | **−14.2** [−20.5, −8.4] | 42.1 | **−17.8** [−23.6, −11.9] |
| placement | task-conditioned flow matching | 76.6 | −3.8 [−8.8, +1.7] | 53.8 | **−6.1** [−10.7, −1.5] |
| placement | no task conditioning | 80.8 | +0.4 [−2.9, +3.8] | 57.9 | −2.0 [−5.6, +1.5] |
| selection | top-1 destination | 62.8 | **−17.6** [−23.4, −11.3] | 36.5 | **−23.4** [−28.7, −17.5] |
| selection | single candidate | 18.0 | **−62.3** [−68.2, −55.6] | 11.2 | **−48.7** [−54.1, −43.4] |

**Direct Z** never abstains correctly in 2D: correct ABSTAIN on NONE is 5.5%, against 97.2% for FINAL. In 3D it is 60.3% (FINAL 82.5%). So its task-rate parity hides a stopping failure.

## (b) Generative architecture (same budget; count-matched)

| Arm | 3D | Δ | 2D | Δ |
|---|---|---|---|---|
| complete-repair cVAE alone (CR) | 50.2 | **−30.1** | 41.1 | **−18.8** |
| CR pool + final X/Y (CRXY) | 81.6 | +1.3 [−3.8, +6.3] | 58.4 | −1.5 [−6.1, +3.3] |
| factorized pool count-matched to the CR pool + final X/Y (FC4) | 77.8 | −2.5 [−6.7, +1.7] | 43.4 | **−16.5** [−21.3, −11.7] |
| factorized + X/Y, full pool (FINAL) | 80.3 | — | 59.9 | — |

**Reading.**
- X/Y evaluation is what makes the complete-repair generator work: CR alone is −30.1 (3D) and −18.8 (2D) vs FINAL, while CRXY is within noise of FINAL.
- At an equal, small candidate count, the CR pool beats a hash-subsampled factorized pool in 2D.
- At its natural, larger pool, FINAL matches CRXY.
- The supported claim is therefore **"X/Y evaluation is necessary"**, not "factorized generation is necessary".

## (c) 3D target feasibility

395 roots: 93 feasible, 302 infeasible. Threshold 0.5. TPR/TNR intervals are Wilson; AUROC intervals are a family-cluster bootstrap. Full table in `reports/final/feas/`.

| Method | TP | FP | TN | FN | TPR | TNR | AUROC |
|---|---|---|---|---|---|---|---|
| PIGINet (no image) | 83 | 12 | 290 | 10 | .892 | .960 | **.989** |
| SCNet | 72 | 4 | 298 | 21 | .774 | **.987** | .974 |
| **Ours (final clean Y)** | 77 | 12 | 290 | 16 | .828 | .960 | .974 |
| GRN | 77 | 13 | 289 | 16 | .828 | .957 | .961 |

Ours is not the best predictor of initial target feasibility. PIGINet leads on AUROC. Our Y head's AUROC is tied with SCNet.

## (d) 3D planning baselines (V3.4 3D, 239 task roots)

| Method | Task % | Δ vs FINAL | NOOP (K0) | ABSTAIN (NONE) | Latency |
|---|---|---|---|---|---|
| **FINAL** | **80.3** | — | 82.8 | 82.5 | GPU, < 1 s median |
| DISCO-Grid s0 / s1 / s2 | 38.9 / 36.4 / 37.7 | −41 to −44 | 35–46 | 0 (never abstains) | 5–8 ms median |
| NOR-Grid (OSNet + RPNet) | 24.3 | −56.1 | 82.8 | 100 | 20 ms median |
| E-M4M (300 CPU-s) | 51.0 | −29.3 [−37.2, −20.9] | 100 | 100 | 300 CPU-s budget |
| MS-MCTS (300 CPU-s) | 30.5 | −49.8 | 100 | 100 | 300 CPU-s budget |
| MO-SeGMan (300 CPU-s) | 26.4 | −54.0 | 98.9 | 100 | 300 CPU-s budget |
| E-M4M / MS-MCTS / MO-SeGMan at a 60 s cut | 0.0 / 3.3 / 0.0 | | | | 60 CPU-s (exact cut of the same runs) |
| REAP | **not run**: no runnable implementation in our workspace (upstream clone, wheels and an online teacher are missing) | | | | |

No baseline used oracle K. Every planner saw the same scenes and was verified by the same teachers.
