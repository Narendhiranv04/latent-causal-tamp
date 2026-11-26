# R2.3 (2D): controlled search attribution on 20 VAL K3 development roots

**Status of this evidence:** development only.

**Why K3 roots.** No physically verified long-horizon 2D witness exists outside protected data:
- the 24 P7AR roots are static-only;
- release_v2 is protected.

The roster is therefore the hardest supported 2D regime: 20 VAL roots with K_legacy = 3 and N 9–15, sha-ordered, round-robin over N bins (`roster_2d.jsonl`, sha256 `880ded0c…`). This tests whether R-FIG3 machinery helps or harms where verified short repairs exist. It does **not** test K > 3 in 2D, and no new long-scene generation was done, as instructed.

**Setup.**
- Same arms and one CFG (2D m_max 6).
- **Physical outcomes:**
  - 20 unique plans reuse exact pool labels (continuous partition: `x_chunked(bounds={m}) == x_query`, plus the endpoint Y);
  - **36 new presealed jobs = 72 teacher queries** (`jobs_S_2d.json`, sha256 `d8c21bb5…`);
  - all 56 unique plans decided, 0 NOT_RUN.
- **Caps:** the 100k unique-readout cap stopped 6/20 R-FIG3 runs (4 F-FLAT, 5 R-GATED, 0 B0). These are recorded, not retried.

| Arm | Verified X=1, Y=1 | Mean length | Mean returns | Failure modes | Median latency |
|---|---|---|---|---|---|
| R-FIG3 | **8/20** | 3.8 | 1.1 | X1Y0 2; X0Y1 5 (relocation 2, boundary 1, reused 2); X0Y0 3 | 3.95 s |
| R-FIG3-ALL | 8/20 | 3.8 | 1.1 | identical to R-FIG3 | 3.93 s |
| F-FLAT | 7/20 | 3.6 | 1.1 | X1Y0 3; X0Y1 6; X0Y0 3 | 3.5 s |
| R-FIG3-RP | 7/20 | 3.6 | 1.2 | | 3.46 s |
| B0 (released) | 6/20 | 3.0 | 0 | X1Y0 5; X0Y0 5; X0Y1 4 | 1.42 s |
| R-TOPO | 6/20 | 4.0 | 1.3 | | 8.38 s |
| R-GATED | 5/20 | 3.7 | 1.0 | | 3.85 s |

**Paired comparisons:**

| Comparison | Only the first verified | Only the second verified |
|---|---|---|
| R-FIG3 vs F-FLAT | 2 | 1 |
| R-FIG3 vs B0 | 2 | 0 |
| R-FIG3 vs R-GATED | 3 | 0 |
| R-FIG3-ALL vs R-FIG3 | 0 | 0 |
| R-FIG3-RP vs R-FIG3 | 0 | 1 |

All are below the minimum sample, so **not established**.

## Funnel (against any verified K ≤ 3 repair of the root)

- **Ingredient recall:** 90 % in D4 at S0; 97 % in any proposal (B0 93 %).
- **R-FIG3 per-root outcome:**
  - a verified repair's action set reached the final plan in 7/20;
  - it was lost at final ranking in 3;
  - it was proposed but never composed in 8;
  - it was never proposed in 2.
- **B0:** 6 kept; 11 proposed but not composed. The K ≤ 3 production search scores all EXACT4 sets, so "not composed" here means *not selected among scored candidates*.

## Findings

- **Established:** in 2D, proposals are not the loss (recall 90–97 %). The losses are composition and selection (11/20 roots for R-FIG3), and Y errors on committed plans (X1Y0 in 2–5 per arm).
- **Not established:**
  - R-FIG3 vs F-FLAT, R-GATED or B0;
  - the admission ablation (R-FIG3-ALL identical to R-FIG3, consistent with R2.1: in 2D admission filters nothing);
  - recompute-parent.
- **Not testable in 2D under current support:** K > 3 and N ≥ 16. There are no verified long witnesses and no feasible labels at N ≥ 16 (R2.0/R2.1).
