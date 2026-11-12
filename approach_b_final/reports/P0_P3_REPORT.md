# Approach B final: handoff and phases P1–P3 (2026-11-12)

Everything below ran on gvlab: GPU 0 (RTX 4090) only, `CUDA_VISIBLE_DEVICES=0`, one GPU job at a time. Peak VRAM was under 1.1 GiB per job.
Results are under `/scratch/nav/approachb_final/runs/`. Data snapshot: `abf_9de85710c2a7103f`. Code: branch `naren/approach-b-final`.

## Handoff (plan section 2)

| Check | Result |
|---|---|
| Package hashes (gate, 3D V4, K3 V3, V2 selections) on gvlab | 58 / 404 / 8 / 3 files, 0 mismatches |
| Selected root files vs recorded hashes | 0 mismatches (2D 5,000, 3D 2,500) |
| Split hygiene (family, layout) | 0 conflicts; placement and X/Y splits lineage-consistent (0 mismatches) |
| Qualified-training exception | `QUALIFIED_TRAINING_EXCEPTION.json`: original BLOCKED verdict retained, legacy K as metadata, 70 flagged scenes kept |
| 3D label completion | K1 X/Y (357) + K0 Y (511) with the unchanged fin3d teacher; replay 1,225 / 1,225 AGREE |
| Evaluation masks | 2D: Repair 2,690 · Task 2,750 · no-op 1,250 · abstain 1,000. 3D: Repair 1,570 · Task 1,581 · no-op 510 · abstain 408 |

The Repair certificate is relative. It requires three things:
- the legacy teacher's verified minimal K;
- a finalized X=1/Y=1 order at that K;
- no finalized shorter repair found by the omission check.

It is not a proof of global minimality under the finalized protocol.

## P1: placement proposals

These are validation results, mean of 3 training × 3 evaluation seeds, M = unique legal proposals. Paired differences are root-cluster bootstrap (2,000 resamples).

| Sampler | 2D hit@4 | 2D known-label precision @4 | 3D hit@4 | 3D known-label precision @4 |
|---|---|---|---|---|
| cVAE (primary) | 0.430 | **0.753** | 0.660 | **0.821** |
| Flow matching | 0.403 | 0.727 | 0.586 | 0.805 |
| Band-stratified (analytical row) | **0.476** | 0.710 | **0.693** | 0.788 |
| Uniform | 0.327 | 0.729 | 0.457 | 0.730 |

- Band-stratified minus cVAE on hit@4: 2D +0.040 [0.029, 0.051]; 3D +0.039 [0.019, 0.061].
- The 3D numbers reproduce the earlier verified 3D study (cVAE 0.655, band 0.688, FM 0.557, uniform 0.451), so the generalized code has parity.
- Known-label precision counts recorded trials only; 70–85 % of proposals have no recorded outcome.
- Flow matching needs projection for about 20 % of raw draws.
- **Gate: PASS** (swappable frozen samplers, identical legality and budgets, no target / goal / repair inputs, latency measured).
- Caveat: the cVAE does not dominate the analytical control on hit@M. Whether its higher precision pays off end to end is measured in P5.

## P2: coupled X/Y Boltzmann models

Models are the `xy3d` / `bxy_core` family with the exact root-marginal NLL, in arms D / E / G / DIRECT. Each arm was trained with 3 seeds and early-stopped on validation.

Test set: the shared candidate pool of every labelled order with both X and Y observed. Paired differences against D are root-cluster bootstrap.

| Test metric | 2D D | 2D E | 2D G | 2D DIRECT | 3D D | 3D E | 3D G | 3D DIRECT |
|---|---|---|---|---|---|---|---|---|
| Binary-Z NLL ↓ | 0.472 | **0.445** | 0.523 | 0.479 | 0.400 | **0.390** | 0.467 | 0.408 |
| AUROC (Z) | 0.865 | **0.873** | 0.800 | 0.858 | 0.902 | **0.910** | 0.860 | 0.898 |
| Order accuracy ↑ | 0.782 | **0.798** | 0.500 | 0.774 | 0.861 | **0.881** | 0.500 | 0.849 |

- Candidates: 2D 1,856 (412 roots, 1,064 order pairs); 3D 1,127 (241 roots, 575 pairs).
- 2D paired differences vs D:
  - E: NLL −0.009 [−0.030, 0.012], order +0.018 [0.004, 0.032];
  - G: NLL +0.044 [0.018, 0.069], order −0.316;
  - DIRECT: NLL +0.037 [0.004, 0.071].
- 3D paired differences vs D:
  - E: NLL +0.015 [−0.008, 0.039];
  - G: NLL +0.051 [0.027, 0.075], order −0.35;
  - DIRECT: NLL +0.026 [−0.005, 0.057].
- **Findings:**
  - Action order matters strongly (G).
  - The learned coupling F5 shows no held-out benefit in either domain. E is equal or slightly better.
  - The explicit factorization beats DIRECT in 2D but not significantly in 3D.
  - Y and the no-op endpoint are predicted very well (AUROC ≈ 0.97–0.99).
- **Gate: PASS** (exact math vs brute force, invariant tests 10 / 10, matched training data / splits / early stopping, no test-set selection).

## P3: witnessed travel cost

- J_complete = relocations + connector + target, Σ|Δq|/joint-range over waypoints. 2D uses the 3R ranges; 3D uses the pinned xArm7 ranges.
- Labels: 2D 3,339 and 3D 3,088 X=1/Y=1 queries with complete witnesses. Missing witnesses are masked, never zero.
- Head: separate network, Huber on log(1+J), 3 seeds.
- Test results: 2D relative MAE 0.19–0.20 and Spearman 0.81–0.83; 3D relative MAE 0.08 and Spearman 0.78–0.80.
- **Gate: PASS** for the fit. The γ = 0 versus tuned-γ comparison is evaluated in P5 with executed travel.
