# P1: dataset and architecture

**Gate: PASS.** 33 contract tests pass; the 50 historical tests (`repair_ranking`, `full_domain_sets`, `mcts_sets`) still pass (83 together in one run, so no module-name collisions); tiny overfit fixtures converge to the irreducible entropy of their targets. Nothing was trained on the full corpus.

## Code

| File | Lines | Role |
|---|---|---|
| `data.py` | 178 | Public encoder inputs in original slot order; TRAIN-only supervision (verified orders, weights, root labels); static grammar |
| `model.py` | 201 | CR-cVAE: shared encoder, order-sensitive posterior, autoregressive pointer decoder with static masks, decision head, prior sampling, marginal likelihood |
| `train.py` | 186 | Fixed-step training matched to the released sampler, VAL selection, overfit fixture |
| `infer.py` | 224 | C0 (unchanged `exhaustive` path), nested CR pools + hashes, C1, C2 (`exhaustive.Selectors`), common-gate diagnostic, C0 parity |
| `p0_audit.py` | 170 | Provenance, corpus audit, cohort roster, parity roster |
| `viz.py` | 151 | P0–P2 figures on real scenes |
| `tests/test_cr.py` | 277 | Contract tests |

Frozen modules are imported, never edited (`git diff 87ebf65d24 -- approach_b_final/*.py` is empty).

## Tests (`python -m pytest tests -q`, CPU, 1.6 s): 33 passed

Each runs for both domains where it applies.

- **Supervision:** only verified X = 1 orders of Y = 1 V3-legal endpoints, deduplicated, never inferred permutations; every root's weights sum to 1; X/Y joined by canonical endpoint key (synthetic fixture with shuffled Y list and a failed sibling order); root-label rules including every masked case.
- **Inputs:** public rows `{root_id, domain, inputs}` encode identically to full snapshot rows (no labels read); movable = non-target, non-fixed, real token (2D `is_fixed`, 3D none); legal destinations = support − S0 occupancy − goal.
- **Decoder:** 256 prior samples per root are all statically legal, length 1–3, never STOP at t = 0; a root with no legal cell gives an explicit no-candidate; **Σ p(r | c, z) over every legal ordered sequence = 1** (to 1e-5) for 1×1, 2×3, 3×2 and 3×4 object × cell sub-problems, which checks STOP, forced STOP and every mask together.
- **Likelihood:** `marginal_loglik` equals a manual logsumexp over L latents, with the U · L pass count.
- **Inference hygiene:** sampling and marginal likelihood run with `model.posterior = None`.
- **Equivariance:** permuting object slots (and the target index and sequence object ids with them) leaves log p(r | c, z) and the decision logits unchanged (1e-4).
- **Determinism:** same generator seed → identical pool; different seed → different pool.
- **Gradients:** every parameter receives a finite, nonzero gradient from ELBO + decision CE.
- **Pools and selector:** nested prefixes, duplicate / no-candidate / illegal accounting, hash stability; `exhaustive.Selectors` with r = 0 equals `xy.choose` on 50 random p11 draws.

## Overfit fixtures (`P1_OVERFIT.json`, CPU)

First 16 TRAIN roots with a verified repair per domain. The floor is the entropy of the weighted target distribution (these roots have several verified repairs each), not 0.

| | steps | −ELBO | recon NLL | KL | floor | decision acc. |
|---|---|---|---|---|---|---|
| 2D | 600 | 1.63 | 1.54 | 0.09 | 1.23 | 1.00 |
| 2D | 2,500 | **1.25** | 0.96 | 0.29 | 1.23 | 1.00 |
| 3D | 600 | 1.43 | 1.42 | 0.006 | 1.13 | 1.00 |

At 2,500 steps the 2D bound sits 0.03 nats above the floor, and the latent carries which alternative repair is meant (KL 0.29). On the fixture roots, 24–64 of 64 prior samples are a verified order (`figures/p1_3d_samples_overfit_3d.png`); misses are near-misses (same objects, one cell off).

## Capacity (`P1_PARAMS.json`)

| | CR total | CR inference (no posterior) | released sampler | released X/Y | released system |
|---|---|---|---|---|---|
| 2D | 732,437 | 547,717 | 328,400 | 465,925 | 794,325 |
| 3D | 722,965 | 538,245 | 311,732 | 467,333 | 779,065 |

CR inference size is below the combined released system, so the optional width control is off (P0_PREREG §3).

## Figures

- `figures/p0_corpus.png`: verified assignments by legacy K and size, verified-order counts of 3-object assignments, root labels.
- `figures/p1_2d_samples_overfit_2d.png`, `figures/p1_3d_samples_overfit_3d.png`: real TRAIN fixture scenes, one verified order, three prior samples of the overfit checkpoint. 3D panels are a labelled top-down schematic of the 6 × 6 shelf cells, not a physics render.
