# R5/R6 allocation request (awaiting owner approval)

**Basis.**
- R5.0 audit PASS (`R5_0_AUDIT.md`, `9b1f3daa49`).
- Envelope proposed in `LEGOLAS_R5_R8_completion_plan.md`: gvlab2 only, ≤ 16 workers, ≤ 8 h wall, ≤ 16 CPU-h, ≤ 4 summed GPU process-hours, ≤ 2 GiB new storage, ≥ 20 GiB free.
- **Already used by R5.0:** 0.52 summed GPU process-h (device wall ≈ 0.30 h), 0 physical CPU-h, 68 KB.

**Cost model (measured):**

| Item | Measured cost |
|---|---|
| X-head training | 5–25 s GPU per run, plus about 60 s load / evaluation |
| 3D GA model-only plan | about 20 s per root (max about 115 s) |
| 2D GA model-only plan | about 70 s per root |
| 3D physical X_CHUNKED + Y + replay | about 30–40 CPU-s |
| 2D x_chunked | about 5–30 CPU-s |
| 2D witness-first family | about 80 CPU-s |
| 3D construction family | about 140 CPU-s of probes + about 18 jobs |

Model-only planning is CPU-bound Python DP holding a GPU model, so it dominates GPU process-hours.

## Proposed allocation

### Physical teacher CPU-h

| Stage | Work | Jobs (approx.) | Cap |
|---|---|---|---|
| R5.1 2D local gap-fill | 40 new witness-first families (fresh seed namespace `R5.1-2D`, family-split TRAIN/VAL 70/30 before outcomes). Adds prefix templates for h1 g3 and h2 g2/g3. Sparse / moderate density, unchanged teacher. | ~1,000 queries | 2.0 |
| R5.1 3D local gap-fill | 30 new families (R4.4 recipe, `R5.1-3D` namespace, same split rule), requiring two plannable irrelevant prefixes so h2 / h3 chunks exist | ~30 × 20 = 600 jobs + probes | 4.5 |
| R5.2 known-assignment order diagnostic | **3D:** 20 exposed roots × up to 3 newly trained heads (dedupe, exact archive reuse). **2D:** K ≤ 5 coh2d roots, 2 arms, subject to the 10-job > 50%-unresolved pilot stop. | ≤ 60 + ≤ 40 | 1.0 |
| R5.3 admission paired check | 3D Y_TARGET on the same denominators: beneficial / irrelevant / harmful for admitted vs rejected actions | ≤ 40 | 0.3 |
| R6 physical | **3D:** 20 roots × 5 arms (B0, same model H ≤ 3, FLAT, REC, GA), deduplicated, ≤ 100 new jobs. **2D:** 10-job pilot; if it passes, ≤ 100 jobs on the K4/5 roots. | ≤ 210 | 2.2 |
| GIF rendering | actual replays only | – | 0.3 |
| Reserve (not targeted) | – | – | 1.7 |
| **Total** | | | **12.0 of 16** |

### Summed GPU process-hours

| Stage | Work | Cap |
|---|---|---|
| R5.0 (used) | parity + leakage audits | 0.52 |
| R5.2 X ablation matrix (frozen Y and cVAE) | **Main matrix**, per domain: {original ordered X, query-relative MLP, query-relative GNN} × {original local data, + strict additional local data} × 2 seeds = 12 runs per domain, 24 in total. **Controls** on the selected representation: order-invariant, uncoupled and direct-success short control, × 2 seeds × 2 domains = 12 runs. All fresh X initialisation, preregistered single recipe. | 0.8 |
| R5.3 model-only diagnostics | Energy-by-length, partition / `has_multi`, calibration, coverage and admission on DEV roots for ≤ 2 candidate models per domain (3D 20 roots; 2D 20 K4/5 roots) | 1.0 |
| R6 model-only sealed plans | 3D 20 roots × 5 arms; 2D 20 roots × 5 arms; floor and deadline inside the timing | 0.9 |
| Reserve | – | 0.28 |
| **Total** | | **≤ 3.5 of 4** |

**Enforcement.**
- At most 2 concurrent GPU processes.
- Each launch is checked against the remaining summed budget plus its worst case, and logged with start and end times.
- Device occupancy is reported separately.

### Other limits

| Item | Plan |
|---|---|
| Workers | ≤ 16 concurrent (physical ≤ 12 + GPU ≤ 2 + analysis) |
| Wall clock | about 6 h of the 8 h guard |
| New storage | ≤ 0.5 GiB (records, small checkpoints at about 4 MB each, selected GIFs); /home stays ≥ 33 GB free |

## Preregistered rules (frozen before outcomes, committed with the R5.1 manifests)

- **Data.**
  - Strict labels only: replayed positives and certified negatives. UNKNOWN / budget / operational outcomes are excluded.
  - Chunks ≤ 3. No h, history or screen flags as features.
  - Family-disjoint TRAIN / VAL by parent family. Dedupe exact and symmetric scenes.
  - R4.3 / R4.4 families are designated DEVELOPMENT TRAINING and removed from all selection evidence. The R4.2 / R4.5 DEV roots are evaluation-only and never training.
- **Training.**
  - Original observed-data likelihood with replay, frozen Y (bitwise-asserted) and frozen cVAE.
  - One recipe: AdamW, lr 1e-4, wd 1e-4, ≤ 40 epochs, patience 8, clip 10, seeds 0 and 1. No O2 ranking loss.
  - **Selection by local VAL NLL only**, never by exposed end-to-end success.
  - The simpler representation is preferred unless the VAL NLL / concordance difference exceeds seed variation.
- **Minimum support for a defensible comparison** (otherwise DATA_LIMITED and a bounded collection request):
  - ≥ 20 VAL families per domain;
  - ≥ 30 VAL matched discordant groups;
  - ≥ 10 VAL families with h ≥ 1 multi-action labels.
- **Scoring rules** (R5.3; at most 3 predeclared variants per domain):
  - original selection (control);
  - local-VAL temperature calibration of conditional X logits, with pX / p11 recomputed;
  - a reliability-threshold shortest-candidate rule with the threshold set on local VAL only.
  - No length prior and no fitting on K4/5 outcomes.
- **Admission rules:** `beats_empty` (control), a minimum-improvement margin, and a feasibility gate. All use frozen models, with the margin chosen on local VAL.
- **Proposals:** frozen top-4, top-8 and bounded ancestral (≤ 64 draws per object) for REC local resampling, plus a labelled uniform-mixture exploration control. A local cVAE rebuild is **not** included and would need separate approval.
- **R6:**
  - H = 5, no true K / assignment / order;
  - one sealed plan per root and arm; no retries or replacement;
  - the 2D pilot stop is retained;
  - per domain × method gate: DEV_IMPLEMENTED / DEV_PHYSICALLY_DEMONSTRATED / BLOCKED.

## Expected limitations (stated before outcomes)

- The 2D DEV panel is dense (N 14–20). The R6 2D pilot may trip the unresolved stop again (R4.5: 7/10). In that case 2D is reported BLOCKED on the dense panel. A clearly labelled sparse demonstration on held-out R5.1 construction families is the only 2D physical evidence, and it is not a substitute.
- The 2D proposal coverage limit (R4.1) is not addressed without the separately approvable local cVAE rebuild.
- The 3D DEV panel is exposed (G1s was selected on it). R6 is development evidence only.
