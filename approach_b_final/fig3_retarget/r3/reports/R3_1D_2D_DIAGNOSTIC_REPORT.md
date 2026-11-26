# R3.1D — 2D frozen local-X diagnostic with established prefixes

**Contract:** `../R3_PREREG_ADDENDUM_A2.json` R3_1D_2d, sealed in `d56e1253b5` before outcomes. **Code:** `../data.py` `build2dd`, `../evaluate.py` `diag2dd`.

**Model:** frozen 2D F0 (`0fa126da80ceecb1`). No 2D training was done.

## Decision

**PASS under the pre-registered R3_1_2d.decision rule** at h ≥ 1. The rule needs ≥ 10 mixed families, AUROC ≥ 0.75 and a lower CI ≥ 0.60.

| h ≥ 1 panel | AUROC (family-cluster 95 % CI) | n (pos) | Mixed families | Rule |
|---|---|---|---|---|
| **Union** (R2.4 + R3.1 + R3.1D, pre-registered) | **0.829 [0.751, 0.899]** | 207 (172) | **18** | **PASS** |
| R3.1D alone | 0.829 [0.712, 0.924] | 63 (50) | 12 | PASS |
| R3.1 (60-query diagnostic) | 0.716 | 18 (9) | 1 | – |
| R2.4 panel (exposed) | 0.736 [0.59, 0.85] | 126 (113) | 5 | – |

**Scope of the pass**
- **Driven by single relocations.** The pass comes from single relocations after a prefix: h ≥ 1, m = 1 gives union 0.853 [0.73, 0.95] and R3.1D 0.899.
- **Multi-action intermediate chunks remain weak and under-supported:**

| h ≥ 1, m = 2–3 | AUROC | Mixed families | Labels |
|---|---|---|---|
| Union | 0.725 [0.60, 0.85] | 3 | – |
| R3.1D alone | 0.403 | 0 | 8 executable / 9 not |

- **Class balance.** Positives dominate: 50 executable vs 13 not at h ≥ 1 on R3.1D.
- **Confident false positives remain.** Of the 13 h ≥ 1 negatives, F0 gives pX ≥ 0.7 to 4 (0.70, 0.73, 0.96, 0.97).
- **Development evidence only.** The R2.4 component consists of exposed roots.

## Design (sealed: `r31d/jobs_31d_2d.json`, sha16 `f6d8322f2c868d8d`)

- **Roots.** 30 clean original-VAL families, not in the R3.1 diagnostic, with N 9–13 and K_legacy ≠ 0, one root per family.
- **Prefix.** p = an original v32 X = 1 single relocation of the root. This is a continuous run including its terminal connector, which the R3.0 parity check showed equals chunk [p].
- **Queries per root:**
  - Q1 [p | b], where b is the best frozen-pX cVAE single;
  - Q2 [p | r], with r random legal;
  - Q3 [p | x y], a pair;
  - Q4 [b] at S0.
- **States.** Every h ≥ 1 state is **physically reached** after the established prefix. No hypothetical-start scenes were used in 2D.
- **Cost.** 120 queries, 0.30 CPU-h, 3 workers. There were 0 errors, 0 censored jobs and 0 retries.

## Outcomes (UNKNOWN preserved)

**Prefix reproduction.** The established prefix reproduced in **90/90** runs (chunk 0 of Q1–Q3 is X = 1). Prefix-side truncation, which blocked R3.1, is gone.

**Teacher statuses over 120 queries:**

| Status | Count |
|---|---|
| VERIFIED | 78 |
| CERTIFIED_INFEASIBLE | 14 (relocation 1: 12; relocation 0: 1; relocation 2: 1) |
| UNKNOWN_PLANNER | 16 (relocation 0: 1, 1: 10, 2: 5) |
| UNKNOWN_TRANSIT | 12 (boundary 2: 10; boundary 3: 2) |

The 28 UNKNOWN runs are never negatives. They truncate 28 h ≥ 1 observations.

**Labels.** 182 exact labels:

| Template | Executable / not |
|---|---|
| Q4 [b] at h0 | 28 / 1 |
| Prefix p at h0 | 90 / 0 |
| Q1 [p \| b] at h1 | 28 / 1 |
| Q2 [p \| r] at h1 | 14 / 3 |
| Q3 [p \| x y] at h1 | 8 / 9 |

- **cVAE singles.** The best-pX cVAE single is almost always executable, before and after a relocation.
- **Where negatives come from.** Random singles and pairs supply most of the negatives.

## Implications

- **Single relocations.** On reached intermediate scenes, frozen 2D X now meets the engineering gate for single relocations. Training a 2D X model is not justified by single-step evidence.
- **Multi-action chunks.** The weak regime is still the order- and chunk-dependent one, which is what long repairs need. It is not supported by ≥ 10 mixed families anywhere.
- **Link to the pilot.** The R3.4D order pilot (`R3_4D_2D_ORDER_PILOT_REPORT.md`) shows this weakness binds physically.

## Figure

`figures/R3_1D_2d.png`:
- (a) labels by template and h;
- (b) teacher status at the failing phase, with UNKNOWN kept;
- (c) frozen pX AUROC at h ≥ 1 by panel.

Reproduce (gvlab2):
```
$PYG data.py build2dd 30
physical2d.py work jobs_31d_2d.json phys_31d_2d.jsonl 3 22 120 4.0
$PYG data.py labels 2d 31d
$PYG evaluate.py diag2dd
```
