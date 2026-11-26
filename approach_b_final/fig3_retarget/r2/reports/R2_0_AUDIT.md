# R2.0 audit and freeze: why does the frozen X/Y + Fig. 3 method fail beyond K = 3?

**Scope.**
- **Branch / base:** `naren/rss27-fig3-retarget-home` from `209560f86f`.
- **Contract:** `fig3_R2_dual_domain_diagnostic_plan.md` plus the owner authorization of 2026-11-26.
- **What this stage did:** read-only auditing on gvlab2. No teacher call, no model readout and no new label.
- **Data boundaries:** TEST rows were skipped by their split field **before** their labels were parsed (2D 749, 3D 370 counted only). release_v2 was not opened.

**Variables, kept separate throughout:**

| Symbol | Meaning |
|---|---|
| N | All scene objects, including the target |
| m | Length of the local ordered corrective sequence |
| K | Certified minimum number of moves (used only where certified) |
| L | Total proposed or witness repair length |
| h | Number of prior hypothetical edits |

## 1. Training support (`R2_0_inventory.json`, `figures/R2_0_train_support.png`)

**Training data:** the bundle's TRAIN snapshot is **V3.2 `abf_v32_fb0eef4f5ff433ee`**, the `train_snapshot` for both the samplers and the scorers. VAL is V3.4 `abf_9de85710c2a7103f`.

| | 2D TRAIN | 2D VAL | 3D TRAIN | 3D VAL |
|---|---|---|---|---|
| Roots / families | 3,500 / 1,574 | 751 / 584 | 1,766 / 871 | 364 / 185 |
| N min / median / q95 / max | 1 / 10 / 19 / 20 | 2 / 11 / 19 / 20 | 1 / 5 / 9 / 13 | 1 / 5 / 9 / 12 |
| Fixed bodies | **0 in every root** | 0 | 0 | 0 |
| X labels, m = 1 / 2 / 3 (X = 1) | 2,325 (1,916) / 6,360 (3,654) / 11,865 (4,789) | 240 / 586 / 1,038 | 1,274 / 3,477 / 6,139 | 150 / 334 / 420 |
| X labels with m ≥ 4 | **none** | none | **none** | none |
| Y labels by edit size 0 / 1 / 2 / 3 | 3,500 / 2,559 / 6,349 / 9,503 | | 1,766 / 1,402 / 2,771 / 3,653 | |

### Established finding: high N is perfectly confounded with infeasibility in TRAIN

| Domain | N range | Roots | Status in TRAIN | Y labels |
|---|---|---|---|---|
| 2D | 16–20 | 686 | **all K = NONE** | **all 0** (X = 1 rate: m = 2 0 %, m = 3 6 %) |
| 2D | 14–15 | 330 | all K = 3 | |
| 3D | 9–13 | 134 | **all K = NONE** | **all 0** |
| 3D | 8 | 101 | 68 NONE, 33 K2/K3 | |

- **What this implies:** the frozen scorer has *never* seen a feasible endpoint in a 2D scene with N ≥ 16, or in a 3D scene with N ≥ 9.
- **Two readings remain open:**
  - a learned "many objects ⇒ infeasible" shortcut (a support / label confound);
  - an encoder capacity limit.
- **What the audit alone cannot do:** distinguish between them. R2.1-A, the matched add-distractor panel, is the direct test.
- **Status:** H_N is **not assumed**; this is a hypothesis with a concrete mechanism.

### Development material, compared with TRAIN support

| Material | N range | Relation to TRAIN support |
|---|---|---|
| 3D K4/K5 cohort (20) | 5–9 | Inside TRAIN support; median 7 |
| 3D C3b | 4–7 | Inside support |
| 2D C3b | 8–15 | Inside support |
| 2D P7AR / kgt3 engineering roots | 16–20 | Inside the *count* support, but entirely in the all-NONE / all-Y = 0 regime |
| 2D release_v2 | 25–28 | Outside TRAIN support **and** outside the cVAE padding cap. Protected; known from its committed report only. |

**Consequence for 3D:** the 3D K4/K5 failures cannot be explained by N lying outside the *count* support. Their N ≤ 9 overlaps the region where the labels shift toward NONE (N = 8: 67 % NONE; N = 9: 100 %).

## 2. Encoders: what N, m and h do to the inputs (source audit, `xy.py`, `placement.py`)

### X/Y scorer (`xy.XYNet`)

- **Object encoding:** per-object MLP tokens (position, attributes, base distance and angle, goal- and target-relative offsets), pooled as **mean ⊕ max** over a padding mask. There is no attention and no cardinality cap; padding is per batch.
- **Effect of growing N:** the mean dilutes, the max saturates, and there is no pairwise interaction term.
- **The edit-aware scene vector adds three things:**
  - the mean token of moved objects;
  - the target token;
  - **`moved.sum() / 3`**, which spans [0, 1] in training (edits ≤ 3).
- **Consequence for representations:**
  - An original-root representation of h + m > 3 edits is **out of range on that feature** (H_m / H_h).
  - Rebasing resets `xy0`, so a rebased view has `moved = 0`. That avoids the out-of-range feature but discards the edit signal.
- **Action tokens:** they carry the step index t as a float, with t ∈ {0, 1, 2} in training; m ≥ 4 means unseen positions. Pair mixing averages over predecessors.

### cVAE (`placement.SceneEncoder`)

- **Architecture:** query token, plus query→object attention, plus mean pooling, plus an occupancy grid.
- **Established limit:** **MAXOBJ is a hard padding cap, 2D 20 and 3D 16.**
  - N above the cap cannot be encoded by the released cVAE. The kgt3 DynPad patch reproduced VAL parity, but it is a modification.
  - The cap binds for 2D release_v2 (25–28), not for any 3D or ≤ 20 2D material.

## 3. Exact-compatible label pool for R2.1 (private: `gvlab2:fig3/r2/audit/pool_{dom}.jsonl`)

**Sources:**
- snapshot labels;
- unchanged-teacher verifier caches (`evaluate._verify_job`, the same BXY / FIN3D contracts): k3val, k3abl, xy_repair_ranking, full_domain_sets, mcts_sets, disco_final.

**Restriction:** TRAIN/VAL roots only. TEST and `~TT~` cache roots were excluded (2D 1,562 / 3D 869 cache root records skipped).

| | 2D | 3D |
|---|---|---|
| Unique X labels (root, ordered seq) | 42,098 | 18,444 |
| Unique Y labels (root, endpoint) | 41,906 | 16,484 |
| Conflicts between sources | **0** | **0** |
| VAL X, m = 1 / 2 / 3 (X = 1) | 2,233 (2,023) / 4,849 (3,679) / 12,500 (6,557) | 1,025 (959) / 2,145 (1,747) / 4,217 (2,250) |

**Status of the TRAIN labels in the pool:** most of them are training data, and serve only as the in-fit reference. TRAIN-cache labels not present in the training snapshot are held-out-like.

**Other sources, scoped as follows:**
- **C3/C3b TT_ADAPTER_V1 labels** (VAL, `k3val/runs/out/ttarget`, `ttarget_cache`): reused exactly for the temporary-target panel. Candidate sets were restricted and included privileged known movers, so they are a **restricted diagnostic**, not deployment evidence.
- **3D K4/K5 witnesses and evaluations** (`k45/eval/eval_{primary,oracle}.jsonl`, same teacher contract): reused as the m = 4/5 out-of-distribution control and as connector evidence.
- **Static-only material is not physical evidence:** the 24 P7AR 2D roots and the static checks are excluded as labels.

**View parity:** raw records rebuild the public views exactly (`contracts.view2d` / `view3d`) on 200/200 VAL roots per domain. Perturbed scenes can therefore be compiled faithfully.

## 4. Code observations: tested as declared R2 ablations, R1 reference unchanged

| # | Observation (R1 code) | R2 handling |
|---|---|---|
| 1 | `rank.best_partition:26-53` compares single-chunk −log p11 with Σ−log pX + (−log Y_global). These scales are not calibrated against each other; 0.481 vs 0.587 is a preference, not a probability of execution. | P4: score distributions against labels. R2.2 measures actual chunked execution. |
| 2 | `rank.final_y:20` defaults to Y_global; the rebased option is unused in recursion. | P2: Y_global vs Y_rebased on identical endpoints. |
| 3 | `rank.select:77` has no eta, so it forces a repair on NONE roots. | Reported. R2.3 only, labelled "forced repair". |
| 4 | Seeding B0's argmax (R1) does not guarantee output or physical parity under caps or repartitioning. | Acknowledged. No floor claim. |
| 5 | `recursive.repairs:107-125` shortlists by p11 and admits by relative temporary pY (`:121`). It can drop helpful repairs or admit tiny changes. | P3 on C3b: false-negative / false-positive admission. Admit-all comparison. |
| 6 | `recursive.place:170` reuses the pre-recursion group pY after nested insertions. | Declared ablation RECOMPUTE_PARENT (R2.3; budget charged). |
| 7 | `local_groups:67` switches to a staged beam above 4,096 groups. | Model-only recall of the staged vs exhaustive top groups by N (R2.1, H_C). |
| 8 | `flat` and the recursive arms use different expansion accounting. | R2.3: equal ceilings and realized counts. |
| 9 | Deadline checks are cooperative (`tick` at `:134`, `:270`, `:298`; none inside `best_partition`). | Overshoot is measured in any R2.3 run. |

## 5. Frozen plan

**Preregistration:** `r2/R2_PREREG.json` (sha256 in the commit). It fixes:
- the N bins;
- the panels P1–P4;
- the matched-N family rule and levels (2D +4 / +8; 3D +3 / +6; add-only, protected cells, nested);
- the omission panel;
- the connector panel and its 0.9 gate;
- the decision rules (≥ 10 mixed families; UNKNOWN > 20 % ⇒ inconclusive);
- the per-panel query budgets.

**Query ledger (maximums):**

| Domain | R2.2 | R2.1-A | R2.1-C | Reserve for R2.3 | Total |
|---|---|---|---|---|---|
| 2D | 88 | 92 | 30 | 90 | 300 |
| 3D | 32 | 57 | 10 | 21 | 120 |

Retries are prohibited, and UNKNOWN is never relabelled.

**Tests:** `r2/tests/test_r2.py`, 4/4 passed. They cover distractor legality, nesting and protection; 3D template copying and refusal when cells are insufficient; view compilation with the added bodies; and the metrics.

**Storage:** 23 MB used plus the audit pool (about 20 MB). gvlab2 /home has 34 GB free.

R2.1 and R2.2 are authorized and proceed next, in that order.
