# 0036 — P9-L3d: input-controlled visual ablation, keyed vs unique matched training, and the 2D model freeze

**Actual result.**
- **Engineering gate:** `runs/p9/l3d/L3D_GATE.json` → **PASS** (14/14), including the historical suite **392/392** and **6/6** replays rerun under the same aggregate guard (624.8 CPU-s).
- **Scientific verdict, kept separate from the engineering gate:**
  - **Visual features:** DINOv2 + geometry fits validation much better than the **same architecture** with zeroed visual inputs.
    - Validation root NLL 0.065 vs 0.428 (3 seeds each, 400 matched updates).
    - Per-root contrast −0.363 [−0.737, −0.060], sign-stable under leave-one-root-out.
    - Calibration is far better (validation ECE 0.000 vs 0.092).
    - The **disclosed** test (descriptive only) shows the opposite tendency: full-vision 2.42 / 1.17 / 0.86 vs visual-zero 0.88 / 0.86 / 0.92. That is an over-fitting warning on 12 validation roots, not a selection input.
  - **Keyed vs unique** (matched 200 updates, same initialization and batches): **indistinguishable** on validation.
    - Root NLL −0.001 [−0.024, +0.023]; leave-one-root-out not sign-stable.
    - Repair accuracy 0.990 vs 0.980; scene NLL 0.088 vs 0.074.
- **Freeze:** by the rule pre-registered *before* any keyed result was read (`runs/p9/l3d/freeze_rule.json`, `sha256:efba5b4e…`), the decision is **FREEZE_KEYED** (`P9_2D_FREEZE_DECISION.md`, `runs/p9/2d_freeze_manifest.json`).

Previous turn sync: `6aa4ba55a267e6dfaded8ba3a8e91369b6795443`. L3c-0 PASS (0034), L3c-1 PASS (0035).

## 1. Protocol (`runs/p9/l3d/L3D_plan.json`, `sha256:b8a947a6…`, frozen before training)

**Visual control:**
- **Reference:** the existing full-vision U-B-full 400-update runs. All 3 seeds are hash-verified against the L3b checkpoint manifest, so the preferred 400-update schedule is used for every arm, with no mixed durations.
- **Control:** `torch.manual_seed(seed); abc8.build("B-full")` — the *same* `vision=True` architecture with the same 698,154 parameters and the identical initialization (test asserts identical state dicts).
  - Every root's precomputed DINOv2 tensor is replaced by zeros for training, validation and evaluation.
  - Same RootSampler batches, AdamW 1e-3 / 1e-4, clip 10, own-NLL validation selection every 20 updates.
  - No new DINOv2 inference.
- **Gradient path:** with zero input, the 384→32 projection *weight* receives exactly zero gradient (test). Its norm ends at the initialization value (3.262 / 3.272 / 3.262), because decoupled weight decay over 400 steps is negligible. Only the projection *bias* trains, acting as a constant object-token offset (mean module gradient 0.74–0.87 vs 10.8–13.8 with DINOv2).
- **Capacity caveat:** nominal capacity is identical; *effective* capacity is not (fewer informative inputs). This is an input ablation, not a capacity-matched proof.

**Keyed vs unique (optional, run because L3c-1 PASS and the budget rule allowed it):**
- `ABC9K_KEYED_V1` through `unique_factor_keyed.installed()`, B-full, 200 updates, seeds 0–2;
- the same initialization and batches as the L3b `U-B-full#s0–2` (200-update) runs;
- identical supervision: own exact root NLL + static BCE + witnessed J.

**Decisions** use the 12 validation roots only. The disclosed test is descriptive.

## 2. Visual control — validation (12 roots; 3 seeds each; 400 updates)

| run | val root NLL | per observed query | calibrated repair NLL | repair accuracy | ECE | scene NLL | best update | clip | disclosed test root NLL (descriptive) |
|---|---|---|---|---|---|---|---|---|---|
| DINOv2 s0 | 0.057 | 0.014 | 0.000 | 1.000 | 0.000 | 0.006 | 380 | 0.58 | 2.421 |
| DINOv2 s1 | 0.078 | 0.020 | 0.000 | 1.000 | 0.000 | 0.020 | 380 | 0.55 | 1.166 |
| DINOv2 s2 | 0.060 | 0.015 | 0.000 | 1.000 | 0.000 | 0.012 | 360 | 0.54 | 0.855 |
| visual-zero s0 | 0.445 | 0.111 | 0.147 | 0.912 | 0.096 | 0.117 | 380 | 0.51 | 0.877 |
| visual-zero s1 | 0.454 | 0.114 | 0.121 | 0.912 | 0.083 | 0.137 | 280 | 0.43 | 0.858 |
| visual-zero s2 | 0.384 | 0.096 | 0.167 | 0.912 | 0.096 | 0.201 | 400 | 0.58 | 0.917 |

**Per-root contrast (DINOv2 − zero, seed-averaged):**
- −0.363 [−0.737, −0.060]; leave-one-root-out range [−0.399, −0.240], sign-stable;
- the three largest root differences: `p8_2026102534` −1.71, `p8_2026102516` −1.55, `p8_2026102504` −0.55;
- top-3 share of total validation NLL: 71 % (DINOv2), 83 % (zero).

**Label provenance** (validation repair NLL, calibrated):
- DINOv2 ≤ 1e-4 on witness / certificate labels (32) and operational labels (2);
- visual-zero 0.12–0.17 (witness / certificate) and 0.04–0.12 (operational).

**Deployed selection on validation:** success on 3–4 of the 4 obstructed validation roots with a VERIFIED candidate for every arm; 0 abstentions; 0 false-empty. No difference.

**Reading:**
- On these saved 2D roots, the DINOv2 channel carries information the learner uses.
- But the disclosed P8c test, already seen in P9, shows full-vision models degrading there while visual-zero models do not. That is consistent with appearance-specific over-fitting to a small, constructor-aligned distribution.
- Neither statement is a fresh-holdout result. The question is carried into P10 (Q9: held-out nuisance appearance with fixed geometry).
- **Per the pre-registered rule, DINOv2 stays enabled.** Visual-zero was *not* better on validation, so the "extraordinary evidence" bar for disabling it is not met.

## 3. Keyed vs unique — matched 200 updates (validation)

| run | val root NLL | repair accuracy | ECE | scene NLL | best update | disclosed test (descriptive) |
|---|---|---|---|---|---|---|
| keyed s0 | 0.348 | 1.000 | 0.000 | 0.127 | 160 | 0.804 |
| keyed s1 | 0.255 | 0.971 | 0.025 | 0.073 | 200 | 1.175 |
| keyed s2 | 0.261 | 1.000 | 0.005 | 0.063 | 180 | 0.824 |
| unique s0 | 0.483 | 0.941 | 0.063 | 0.134 | 180 | 1.223 |
| unique s1 | 0.224 | 1.000 | 0.000 | 0.044 | 200 | 1.119 |
| unique s2 | 0.161 | 1.000 | 0.001 | 0.043 | 200 | 1.044 |

**Contrast (keyed − unique):** −0.001 [−0.024, +0.023]; leave-one-root-out [−0.010, +0.006], **not** sign-stable; top-3 share 91 % vs 95 %.

**Trained-model invariance:**
- every trained keyed and visual-zero model is exactly invariant to duplicate, permutation, renamed and disconnected candidates (≤ 1.4e-14);
- the related-candidate (allowed) change is 0.12–0.37 (keyed) and 0.20–0.43 (visual-zero).

**Freeze rule (frozen before these results), FREEZE_KEYED iff all of:**
- L3c-1 PASS;
- the root-NLL CI lower bound ≤ 0;
- repair-accuracy drop ≤ 0.03;
- scene-NLL increase ≤ 0.05.

**Measured:**
- PASS;
- −0.024 ≤ 0;
- accuracy 0.990 vs 0.980, i.e. no drop;
- scene NLL +0.014.

So the decision is **FREEZE_KEYED**. The predictive evidence only says the keyed model is *not worse*; it is chosen for its verified semantics (one physical relation, one factor instance), which matter when deployed catalogues vary.

## 4. External-validity note (contract §4)

- **Root NLL is not a test of** action-order causality or omission necessity: the fresh P8c data contain no decided same-endpoint order pair and no omission-only labels.
- **κ = +1** evidence for the reported test roots is operational only.
- **P7 order evidence** (17 historical contrasts) is in the training history and was never a fresh test.
- **No P9 model has been executed physically;** G+M remains the best executed method (P8d 9/12).

## 5. Gate and accounting

`runs/p9/l3d/L3D_GATE.json` → **PASS**. Engineering checks (all PASS):
- plan frozen before training;
- freeze rule written before the keyed results;
- 3-seed visual control complete;
- plan hash in every run;
- identical architecture and parameter count;
- reference checkpoints verified;
- no non-finite loss;
- trained models invariant;
- checkpoint replay;
- budget and per-job caps;
- historical suite and six replays;
- zero physical calls in learned paths.

The scientific verdict is a separate field: visual = "DINOv2 better on validation"; keyed vs unique = "INCONCLUSIVE (no significant difference)".

**Compute (whole L3c / L3d task):** 2,327.8 / 5,000 CPU-s, 2,335 / 12,000 s wall, every job in `runs/p9/l3c/guards/` (including the corrected gate re-evaluation). 0 teacher, IK or planner calls in learned paths; planner calls only in the historical test fixtures, counted in the gate.

**Figures** (each with a SHA-256 input manifest):
- `visualizations/p9/P9_L3c_factor_graph_unique_vs_keyed.png`: real root `p8_2026102510`, 36 vs 20 scene–query instances;
- `P9_L3c_selection_and_calibration.png`;
- `P9_L3d_visual_control.png`.
