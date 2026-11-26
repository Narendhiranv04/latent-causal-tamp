# FIG3_KGT3 P1 — existing evidence and model-only composition audit

**Contract:** `../FIG3_KGT3_PREREG.json` P1, committed before this audit opened any outcome. No new physical query was made. Everything here uses **exposed development roots** and is diagnostic. Nothing here selected a checkpoint, a loss weight or a search setting.

Outputs are in `p1/`: `p1_arch2d.json`, `p1_panel_{2d,3d}.json` and `p1_quarantine.json`.

## 1. 2D R3.4D archive (90 X_CHUNKED runs, 30 certified K4/K5/K6 roots)

These 90 runs yield **139 exact chunk labels** (`labels.chunks_of`). No anchored singleton labels are derived from completed chunks, and unobserved suffixes are dropped.

**Frozen F0 marginal pX on these labels, AUROC (family = root):**

| Stratum | AUROC | Notes |
|---|---|---|
| All | **0.46** | 139 labels, 105 executable |
| h0 | **0.37** [0.27, 0.48] | 74 labels |
| h ≥ 1 | 0.67 [0.52, 0.85] | 65 labels |
| Singles (g = 1) | 0.28 | – |
| Chunks of 2–3 (g = 2–3) | 0.45 | – |
| h0, g = 2–3 | 0.39 | – |

On the certified dense chain scenes, F0 ranks executable chunks **below** non-executable ones at h0. That is worse than chance.

**FX-DP failures** (27 non-successes):

| Where it failed | Certified infeasible | UNKNOWN_PLANNER |
|---|---|---|
| Relocation 0 | 13 | 6 |
| Relocations 1 / 2 / 4 | 6 | 2 |

**Attribution against the witness:**
- FX-DP's order never equals the witness order (0/30).
- Its first action is the witness's first action on 2/30.
- Its first chunk covers the witness's first-chunk set on 5/30.

The failures are **order errors**, not partition errors: FX-DP starts with an action the witness defers. No connector failed (0/90).

## 2. Known-assignment panels under the KGT3 objective (grouped DP; F0 in 2D; F0, G1s and M1s in 3D)

| Panel | Model | Median witness-order rank quantile | Witness rank ≤ 3 | DP picks the witness order | λ = −log 0.92 changes the choice | All-singleton when unconstrained (has_multi binds) |
|---|---|---|---|---|---|---|
| 2D (30, m = 4–6) | F0 | **0.82** | 0/30 | 0/30 | 3/30 | 0/30 |
| 3D (20, m = 4–5) | F0 | 0.33 | 0/20 | 0/20 | 9/20 | **7/20** |
| 3D | G1s s0 | 0.21 | 4/20 | 3/20 | 8/20 | 4/20 |
| 3D | M1s s0 | **0.17** | 4/20 | 2/20 | 2/20 | 1/20 |

- **2D.** F0 ranks the verified order in the worst fifth of all orders (median quantile 0.82). It never prefers singleton chunks, so the multi-action constraint never binds. Its wrong choices are confident long chunks. The ordering signal is absent or inverted for 2D chain scenes.
- **3D.** The query-relative heads (G1s / M1s) rank the witness order much better than F0. Without has_multi, F0's parameter-free optimum is all-singleton on 7/20 roots. The historical λ, which penalizes returns, changes the selected plan on 9/20 roots for F0 but only 2/20 for M1s.
  - So λ is not innocuous: it changes the selected plan on 8–9 of 20 roots (F0, G1s). That is why it stays a named control, and the primary objective is parameter-free.
- **Cost of the grouped DP** (assignment given): 3D about 304 unique X scores per root; 2D about 747 (m ≤ 6). This is far below the m! × compositions of full enumeration (720 × 24 at m = 6).

## 3. Quarantined A2 outcomes (DIAGNOSTIC_ONLY)

The copies' hashes match the write-protected originals (`0e1ea152f2c1caaa`, `f4933b3f3210df76`). **Labelled diagnostic only: no gate, recovery rate, regression claim, training or selection use.**

| Arm | Verified | Failed | Not run | Source |
|---|---|---|---|---|
| G1s order (S-DP), λ = −log 0.92, R3.4 plans | 9 | 9 | 2 | quarantined runs |
| Random order | 1 | 2 | 17 | quarantined runs |
| F0-DP | 2 | 18 | 0 | archived R2.4 executions, not quarantined |

- **Missing coverage.** The stop truncated 21 of the 39 sealed R3.4 jobs, so no rate over the cohort is reported.
- **Regression jobs.** 29/60 ran: x1/y1 on 23 runs, x1/y0 on 3, x0/y1 on 1, x0/y0 on 2. Only part of the changed-root sample was verified, so there is no estimate and no claim.

This is consistent with §2: the query-relative 3D heads carry ordering signal that F0 lacks. It is development exposure, not evidence for any gate.

## 4. Implications for P2 (no decision is taken here)

- **2D.** The deficit is multi-action ordering on chain-dependent scenes. P2 collects matched permutations at h0 and at reached h ≥ 1 states on new generator families.
- **3D.** F0 is weak and G1s / M1s look better. The P2 fresh gate decides; no exposed panel is used.
