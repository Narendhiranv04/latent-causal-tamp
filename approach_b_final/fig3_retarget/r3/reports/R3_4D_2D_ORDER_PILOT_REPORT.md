# R3.4D — 2D certified long-repair order-recovery pilot (DIAGNOSTIC)

**Contract:** `../R3_PREREG_ADDENDUM_A2.json` R3_4D_2d. Predictions, jobs and selection were sealed in `d56e1253b5` before any physical query. **Code:** `../coh2d.py`.

**Scope.** This is order recovery *given the known relocation assignment*. It is not repair discovery.

## Result

**The frozen 2D X does not recover execution orders.**

| Arm | Strict all-root success (UNKNOWN = failure) | Decided-only | UNKNOWN |
|---|---|---|---|
| **FX-DP** (frozen X, exact subset DP, chunks 1–3, λ = −log 0.92) | **3/30** | 3/20 | 10 |
| RANDOM (seeded order + frozen-X best partition) | 2/30 | 2/19 | 11 |
| WITNESS (verified order + frozen-X best partition, same protocol) | **29/30** | 29/29 | 1 |

| By certified minimum K | FX-DP | RANDOM | WITNESS |
|---|---|---|---|
| K4 | 2/10 | 2/10 | 10/10 |
| K5 | 1/10 | 0/10 | 9/10 (1 UNKNOWN) |
| K6 | 0/10 | 0/10 | 10/10 |

| By N | FX-DP | RANDOM | WITNESS |
|---|---|---|---|
| 14–16 | 2/10 | 1/10 | 9/10 |
| 17–18 | 1/15 | 1/15 | 15/15 |
| 19–20 | 0/5 | 0/5 | 5/5 |

**Paired comparisons** (exact McNemar):

| Comparison | Gained | Lost | One-sided p |
|---|---|---|---|
| FX-DP vs RANDOM | 2 | 1 | 0.50 |
| WITNESS vs FX-DP | 26 | 0 | 1.5e-8 |

**Diagnostic reference** (R3_PREREG R3_4.2d bands): FX-DP 3/30 is **NOT_RECOVERED_REF**, against ≥ 21/30 for recovered and 15–20 for partial.

**Gate status.**
- When the pilot was sealed, the 2D local-X gate was unresolved. R3.1D has since passed it, for single-step discrimination only.
- The pilot was pre-registered as diagnostic, so there is no formal gate in either direction.
- The pilot fails the reference bands by a wide margin.

## What the pilot shows

1. **The chunked execution protocol works.** The privileged order, run with the same chunk boundaries and connectors to q_ref, verifies on 29/30 roots, all with replay and Y = 1. Endpoint Y = 1 on 30/30.
   - Failures of FX-DP are therefore ordering failures, not protocol, connector or endpoint failures.
2. **The frozen X prefers wrong orders.**
   - The verified order's rank among all orders, each with its best partition, has median quantile ≈ 0.80 (range 0.06–0.98). Examples: 22/24, 98/120, 645/720.
   - The DP's chosen order always has lower model energy than the witness order. On every root, the model is confident in a wrong order.
   - FX-DP matches the witness order exactly on 0/30 roots.
3. **Where FX-DP fails.**

| Failure location | Certified infeasible | UNKNOWN_PLANNER |
|---|---|---|
| Relocation 0 (first move) | 13 | 6 |
| Relocation 1 | 1 | 3 |
| Relocation 2 | 3 | – |
| Relocation 4 | – | 1 |

   - FX-DP mostly fails at the **first relocation**. Its first move is a body whose pick or place is still blocked: an enabler is skipped.
   - First-chunk pX on certified failures ranges 0.09–0.94, median ≈ 0.5.
   - RANDOM fails later on average: relocation 1 is the most common failure point.
4. **Chunking.**

| Statistic | FX-DP | WITNESS |
|---|---|---|
| Reference returns, 1 / 2 / 3 / 4 | 24 / 6 / 0 / 0 roots | 16 / 8 / 5 / 1 roots |
| Mean planning time per root (exact DP) | 0.15 s (max 0.35 s) | – |

   - FX-DP prefers long chunks: 2–3 moves with one return. It is choosing exactly the multi-action chunks where frozen 2D X is weakest. R3.1D shows AUROC 0.40–0.73 for h ≥ 1, m = 2–3, on too few families.
5. **Single-step versus ordering.** R3.1D shows usable single-step discrimination after a prefix, and that does not translate into order recovery. This is the 2D analogue of the R2.4 3D finding.

## Cost and protocol

- **Queries.** 90 X_CHUNKED jobs plus 30 endpoint-Y queries = **120 queries** (cap 180).
- **Compute.** 0.41 CPU-h (cap 5), 3 workers. There were 0 errors, 0 censored jobs and 0 retries.
- **Coverage.** All 30 sealed roots are reported. No reserve root was used and no prediction was revised.
- **Hidden information.** The planner saw the assignment only as a sorted set (`order.Table.A`, unit-tested). Witness ranks were computed by the evaluator.
- **Teacher.** `physical2d` X_CHUNKED (BXY_X_TEACHER_V1 relocation primitives, connector to q_ref at every boundary, independent replay).
- **Endpoint Y.** Measured once per root. Every arm reaches the same endpoint.

## Figure

`figures/R3_4D_order_2d.png`:
- (a) Per-root outcome matrix by arm and K, with the first failing relocation.
- (b) Verified by K.
- (c–e) FX-DP predicted orders on a K4, a K5 and a K6 root. Shown are the chunk boundaries ('|' = return to q_ref), the first failing relocation (red) and the witness rank.
- (f) The privileged witness order for the K4 root.

The grids are schematic cell positions. Outcomes are actual teacher runs.

Reproduce (gvlab2):
```
$PY2D coh2d.py prep
$PYG coh2d.py plan
python coh2d.py jobs 180
physical2d.py work coh2d/jobs.json coh2d/phys.jsonl 3 25 90 5.0
python coh2d.py analyze
```
