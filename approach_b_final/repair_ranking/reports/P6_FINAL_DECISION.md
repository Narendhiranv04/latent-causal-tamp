# Final decision: X/Y repair ranking (K1/K2, 2D)

## Verdict: **NO_ESTABLISHED_IMPROVEMENT (development evidence only).** P6 confirmation was **not run** by the registered rule. **Keep A0 + EXACT4.**

## Phase status

| Phase | Status | Commit | Key result |
|---|---|---|---|
| P0 audit / parity | PASS | `b66c54749e` | 40/40 D6 and EXACT4 parity; readout identities ≤ 1.3e-7; TRAIN snapshot already labels tail destinations (46 % of X labels go beyond rank 12); old aggregates reproduced exactly |
| P1 diagnosis | PASS | `a786a5b5d1` | Ranking errors dominate. pX1 anti-ranks within a root (0.45); same-object destination pairs are near chance (0.48); off-top-4 sets are over-confident by tier; VAL slope 0.68 vs TRAIN 1.10 |
| P2 frozen rules | no finalist | `6756785fed` prereg, `5334c84e4d` | F2/F3/F5 improve DEV_CAL ranking by +0.04 to +0.07 but **do not replicate** on DEV_AUDIT (−0.07 to +0.02); F4 vetoed (disclosed) |
| P3 TRAIN labels | PASS (at cap) | `dad6de566c` seal, `8d932eef93` | 1,794 queries on 359 roots; 12.03 / 12 CPU-h; +1,507 X / +1,116 Y; 0 conflicts |
| P4 training | no finalist | `c95447641a` prereg | Data lowers held-out NLL by 0.3–0.4 nats per root; the rank loss has no effect; best arm A4 +0.019 [−0.003, +0.040] on DEV_CAL and +0.001 on DEV_AUDIT |
| P5 pipelines | no primary | `0be7966e68` prereg | A0: no constructor beats EXACT4 consistently. A4 + EXACT4: 3 / 1 and 1 / 0 on cached changed picks, but 14 / 11 more unlabelled picks. Latency unchanged |
| P6 confirmation | **NOT RUN** (registered rule 1) | – | Pool of 207 fresh roots prepared and sealed in P0 (61 K1, 23 K2, 114 K0, 9 NONE); 0 of the 1,200 validation queries spent |

## Answers to the plan's checklist

1. **Did TRAIN under-represent tail destinations or contrasts?**
   - Partly. The tail is labelled, but less often than its share of legal actions (46 % vs 76 %).
   - Order contrasts are rich on TRAIN, and destination contrasts for a fixed object set were scarce before P3.
   - The VAL/TRAIN gap is large: p11 AUROC 0.80 vs 0.94, slope 0.68 vs 1.10. That points to generalization, not missing support alone.
2. **Which component dominates?**
   - Within a root, all of the ranking signal comes from pY (0.71 alone, against 0.72 for p11). pX1 ranks below chance (0.45 [0.40, 0.50]).
   - High-confidence errors split between FAIL_Y (206) and FAIL_X with Y = 1 (156).
   - The EXACT4 decomposition (240 VAL K1/K2 roots, decided labels): 21 ranking, 7 gate, 2 pool-miss candidates, 0 order, 58 unresolved.
3. **cVAE prior and calibration:**
   - The prior alone has no within-root signal (0.51).
   - Prior- or tier-aware rescoring fits DEV_CAL but does not transfer. The apparent gains were threshold and selection effects on a selection-biased label set.
   - A monotone calibration cannot change rankings.
4. **Data vs objective vs optimization:**
   - **A1 − A0 (extra optimization):** DEV_CAL-only gains of +0.015 to +0.028; DEV_AUDIT −0.015 to −0.003.
   - **A2 − A1 (data):** held-out NLL improves by 0.3–0.4 nats per root on both halves, but ranking does not change (DEV_AUDIT +0.006 to +0.015, CIs touch 0).
   - **A3 − A1 (rank loss):** none.
   - **A4 vs A2/A3:** small or none.
   - All of this rests on 3 seeds and one exposed development cohort.
5. **Does the improved scorer with EXACT4 select better repairs? Does wider search help? Is MCTS justified?**
   - The scorer was **not improved** by the registered criterion, so CONFIRM was not spent.
   - Model-only, A4 + EXACT4 is not identifiable from cached labels because too many picks are new.
   - Wider search and MCTS show no consistent DEV benefit with either scorer. **No MCTS claim.**
   - Runtime is unchanged: EXACT4 at 0.034 s against about 0.17 s for search at 1024.
   - K0/NONE safeguards are identical across all cells. The K3 historical top-1 did not regress (within 3 pp).

## Recommended released method

**A0 + EXACT4:** the frozen S1 cVAE top-4 and frozen coupled arm-D X/Y scorer s0, with exhaustive K ≤ 2 and the NOOP 0.5 / η 0.3 rule, unchanged. The released bundle weights are untouched. No K3, K > 3, 3D, causal-blocker or global-minimality claim is made.

## Limitations

- **Exposed development data:** all evidence comes from VAL. The scorer's original checkpoint was early-stopped on VAL NLL, and the cached labels are selection-biased.
- **Unresolved labels:** DEV UNKNOWN rates are about 25–30 % even for EXACT4.
- **Teacher cap overrun:** the TRAIN teacher allocation was exhausted at 12.03 h (a 0.03 h overrun from in-flight work), and 6 queries on one root are missing.
- **Small CONFIRM pool:** the prepared pool is underpowered (84 K1/K2 roots, of which 23 are K2), because the generator cannot be capped in teacher queries (P0).

## Smallest justified next step (needs new authorization)

- **Physical check of the changed picks:** spend ≤ 200 DEV physical queries on the A4 + EXACT4 picks that changed and are unlabelled (about 25 roots per half), to see whether its likelihood gain turns into selection gain.
- **Only if that is positive:** a preregistered CONFIRM run on the prepared 207-root pool, at roughly 250 queries.
- **No new search study** is justified by this evidence.

## Resources actually used

| Resource | Used | Cap |
|---|---|---|
| New 2D teacher queries | **1,794** TRAIN (6 interrupted); 0 certification; 0 validation | 1,800 / 600 / 1,200 |
| Teacher worker CPU | **12.03 h** TRAIN; 0 / 0 | 12 / 6 / 6 h |
| Teacher host | gvlab2, 32 workers on cores 8–39 (16 free); 2026-11-25 04:40–05:12Z | ≤ 32 workers |
| GPU training | 0.31 GPU-h (12 fits, RTX 5060) | 8 h |
| GPU inference | about 0.5 GPU-h (readouts of 2.7 M VAL + 2.0 M D12 sequences, DEV predictions, timing) | 4 h |
| Storage | about 1.1 GB (984 MB private tables and caches, 159 MB checkpoints and runs) | 20 GiB |
| Protected TEST | not opened | – |
