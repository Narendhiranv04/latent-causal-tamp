# Approach B: final implementation and experiment report

Everything here was computed on gvlab (GPU 0 only) and gvlab2 (CPU teacher queries, exact parity with gvlab). No result was tuned on test. V1 = the pre-registered design of plan.md; V2 = the same architectures retrained with on-policy X/Y labels (user decision after the V1 validation failure analysis). Calls = motion-planner calls inside the learned search (0 by construction; the independent physical verification is reported separately and is identical for every row).

## Table I(b): 2D component ablations (test)

### V1 (pre-registered)

Frozen stopping rule (validation-tuned): `{"noop_gate": 0.5, "eta": 0.3, "alpha": 0.5, "beta": 0.0, "gamma": 0.5}`. Test roots × 3 seeds; paired root-cluster bootstrap 95 % CI of the difference to the full approach (task success).

| Row | NLL ↓ | Order ↑ | Repair % ↑ | Task % ↑ | Calls ↓ | Travel ↓ | Δ Task vs full [95 % CI] |
|---|---:|---:|---:|---:|---:|---:|---|
| Uncoupled (F5=0, E) | 0.445 | 0.798 | 10.0 | 10.4 | 0 | 3.20 | -1.1 [-2.6, +0.3] |
| Order-invariant (G) | 0.523 | 0.500 | 10.6 | 10.7 | 0 | 2.92 | -0.8 [-2.5, +0.9] |
| Direct success predictor (DIRECT) | 0.479 | 0.773 | 11.4 | 11.6 | 0 | 3.10 | +0.1 [-1.7, +1.8] |
| Analytical sampler (band-stratified) | — | — | 10.9 | 11.1 | 0 | 3.15 | -0.4 [-2.1, +1.3] |
| Flow matching | — | — | 9.8 | 10.1 | 0 | 3.03 | -1.4 [-3.2, +0.3] |
| One-shot selection | — | — | 11.1 | 11.2 | 0 | 3.24 | -0.2 [-1.1, +0.7] |
| No travel-cost term (γ=0) | — | — | 9.0 | 9.5 | 0 | 3.82 | -2.0 [-4.1, -0.1] |
| **Our approach (F2,F3,F5, D)** | 0.472 | 0.782 | 11.4 | 11.5 | 0 | 3.27 | — |

Full approach, other strata: correct no-op on K0 92.7 % (n = 561), correct abstention on NONE 78.0 % (n = 450); Task n = 1236, Repair n = 1215 (certified roots × seeds); successful repairs shorter than the legacy K: 2.

### V2 (on-policy labels)

Frozen stopping rule (validation-tuned): `{"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.1, "gamma": 0.0}`. Test roots × 3 seeds; paired root-cluster bootstrap 95 % CI of the difference to the full approach (task success).

| Row | NLL ↓ | Order ↑ | Repair % ↑ | Task % ↑ | Calls ↓ | Travel ↓ | Δ Task vs full [95 % CI] |
|---|---:|---:|---:|---:|---:|---:|---|
| Uncoupled (F5=0, E) | 0.530 | 0.801 | 16.5 | 24.3 | 0 | 4.18 | -1.4 [-3.6, +1.1] |
| Order-invariant (G) | 0.557 | 0.500 | 17.6 | 23.9 | 0 | 4.24 | -1.7 [-4.2, +1.1] |
| Direct success predictor (DIRECT) | 0.495 | 0.756 | 14.6 | 19.5 | 0 | 4.20 | -6.1 [-9.0, -3.3] |
| Analytical sampler (band-stratified) | — | — | 12.8 | 21.1 | 0 | 4.39 | -4.5 [-7.1, -1.9] |
| Flow matching | — | — | 18.5 | 26.1 | 0 | 4.63 | +0.4 [-2.4, +3.3] |
| One-shot selection | — | — | 18.2 | 25.9 | 0 | 4.33 | +0.2 [-2.0, +2.6] |
| No travel-cost term (γ=0) | — | — | 18.4 | 25.6 | 0 | 4.35 | +0.0 [+0.0, +0.0] |
| **Our approach (F2,F3,F5, D)** | 0.528 | 0.792 | 18.4 | 25.6 | 0 | 4.35 | — |

Full approach, other strata: correct no-op on K0 90.4 % (n = 561), correct abstention on NONE 94.0 % (n = 450); Task n = 1236, Repair n = 1215 (certified roots × seeds); successful repairs shorter than the legacy K: 2.

## 3D: our approach (test; external baselines deferred by the user)

| Version | Task % | Repair % | No-op % | Abstain % | Travel | Rule |
|---|---:|---:|---:|---:|---:|---|
| V1 | 29.0 | 23.1 | 82.1 | 27.4 | 8.975 | `{"noop_gate": 0.8, "eta": 0.3, "alpha": 0.5, "beta": 0.0, "gamma": 0.0}` |
| V2 | 52.4 | 38.0 | 78.1 | 84.4 | 10.262 | `{"noop_gate": 0.5, "eta": 0.3, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}` |

## Supporting evidence

### P1 placement samplers (test hit@4 / known-label precision @4; Δ hit@4 vs cVAE)

| Sampler | 2D | 3D |
|---|---|---|
| cvae | 0.428 / 0.748 | 0.657 / 0.799 |
| fm | 0.403 / 0.729 (Δ -0.026 [-0.033, -0.018]) | 0.581 / 0.774 (Δ -0.072 [-0.085, -0.058]) |
| stratified | 0.474 / 0.702 (Δ +0.037 [+0.026, +0.047]) | 0.679 / 0.756 (Δ +0.031 [+0.012, +0.050]) |
| uniform | 0.332 / 0.736 (Δ -0.103 [-0.114, -0.093]) | 0.463 / 0.716 (Δ -0.176 [-0.199, -0.153]) |

### V1 vs V2 on the search's own validation candidates (physically labelled; never trained on)

| Domain / version / arm | Z NLL | AUROC | ECE | mean p11 |
|---|---:|---:|---:|---:|
| 2D|V1|D | 1.480 | 0.835 | 0.477 | 0.599 |
| 2D|V1|E | 1.339 | 0.780 | 0.448 | 0.569 |
| 2D|V1|DIRECT | 1.040 | 0.811 | 0.373 | 0.495 |
| 2D|V2|D | 0.232 | 0.924 | 0.046 | 0.165 |
| 2D|V2|E | 0.234 | 0.918 | 0.043 | 0.160 |
| 2D|V2|DIRECT | 0.300 | 0.902 | 0.080 | 0.198 |
| 3D|V1|D | 0.825 | 0.885 | 0.320 | 0.501 |
| 3D|V1|E | 0.841 | 0.882 | 0.296 | 0.477 |
| 3D|V1|DIRECT | 0.777 | 0.831 | 0.282 | 0.463 |
| 3D|V2|D | 0.253 | 0.938 | 0.043 | 0.218 |
| 3D|V2|E | 0.247 | 0.939 | 0.040 | 0.215 |
| 3D|V2|DIRECT | 0.307 | 0.919 | 0.084 | 0.265 |

### Coverage diagnostic (train roots; labelled candidates)

- 2D: {"roots": 18, "proposal_failure(no successful candidate)": 10, "ranking_failure(success exists, not selected)": 7, "ranking_ok(selected succeeds)": 1}; by K {"1": {"missed": 3, "selected": 1}, "2": {"missed": 4}, "3": {"none": 10}}
- 3D: {"roots": 15, "ranking_ok(selected succeeds)": 4, "proposal_failure(no successful candidate)": 3, "ranking_failure(success exists, not selected)": 8}; by K {"1": {"selected": 1, "missed": 4}, "2": {"none": 1, "missed": 2, "selected": 2}, "3": {"selected": 1, "none": 2, "missed": 2}}

### Validation end-to-end (300-root tuning subset)

| | Task % | Repair % | No-op % | Abstain % |
|---|---:|---:|---:|---:|
| 2D V1 | 17.2 | 15.6 | 95.0 | 88.3 |
| 2D V2 | 33.9 | 22.0 | 93.3 | 95.0 |
| 3D V1 | 31.8 | 27.3 | 85.0 | 13.8 |
| 3D V2 | 51.4 | 39.0 | 80.0 | 93.1 |

## Caveats

- Repair uses a relative certificate (legacy-verified minimal K + finalized X=1/Y=1 order + no shorter repair found by omission); successful repairs shorter than K are counted separately.
- 3D K1 / K0 finalized labels were completed with the unchanged teacher (replay 1,225 / 1,225 agree); 70 flagged scenes are excluded from Repair only.
- The coverage diagnostic labelled the top 100 + 50 random (2D) / top 30 + 15 random (3D) candidates per root, so 'no successful candidate' is a lower bound.
- V2 stopping rules chose γ = 0 on validation in both domains, so the 'no travel-cost term' row equals the full row for V2.
- External 3D baselines (Table I(a)) are not run (deferred by the user).
