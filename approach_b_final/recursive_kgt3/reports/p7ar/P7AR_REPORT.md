# P7A-R — Final bounded, pre-registered repair-scoring revision: offline report

Branch `naren/kgt3-exec-composition`, from `2497fa1415`.

**Commits, in order:**

| Commit | Content |
|---|---|
| `865dd533e5` | pre-registration |
| `43828dd933` | code freeze + amendment R1 |
| `e0100218db` / `0faecd835d` | roots, sealed P4 pools, endpoints, freeze manifest |
| `09fca42f9f` | sealed predictions, SHA `05d48ebccd3c856b…` |
| this commit | the one-shot evaluator report |

**Not done:** no teacher call, training, labels, dataset generation, release_v2 access, checkpoint or budget edit, or merge. The P7A gate (REVISE, `reports/p7/`) is preserved as the historical negative result.

## Decision: **`BLOCKED_FROZEN_KGT3`** (see `P7AR_DECISION.md`)

On 24 new independent development roots, **no arm committed a single statically valid plan** (0/24 for each of the six arms). FULL-R's net is therefore 0 against each of FLAT-STRONG, RANDOM-MATCHED, ORIG and DEST_ONLY; ≥ 3 against each was required. Roots with a novel enabler *and* a static-valid plan: 0, against ≥ 2 required.

## 1. Cohort (pre-registered, deterministic)

| Item | Value |
|---|---|
| Source pools | untouched engineering pools `lay_e` / `lay_g` / `lay_fg` (SHA in `P7AR_ROOT_SELECTION.json`) |
| Release disjointness | `scaling2d_k12/G1/GEN_SPEC.md`: "`ENG_*`, `ENG2_*` are excluded from every release". The release_v2 files were **not read** (that read was refused by the permission system and was not worked around) |
| Eligible after filters (original geometry, ≤ 20 objects, no DEV id, lineage or layout overlap, deduplicated) | 890 layouts, 518 seed lineages |
| Selected | **24 roots, one per lineage**: K_lb 4, 5 and 6 × 8 each (evaluator-only strata); 16–20 objects |
| Scope limit | DEEP9 (K9) roots have no release-disjointness guarantee and were excluded, so **K4–K6 only** |
| Anchors | frozen P4 pipeline (R2, R3, F; `p4_config` unchanged), sealed: R2 `bda7c265…`, R3 `64e41afc…`, F `e4ae33b9…`. P6A public rule: 2 endpoints per root, 48 total, m = 4–12 |

**Anchor quality (evaluator):** only **5 of 24** rank-0 anchors admit any static order; 12/24 have a live final target. Most anchors therefore require object-set repair, which is what P7A-R targets.

## 2. Primary result (one committed plan per root per arm; offline static check, not physical)

| Arm | Static-valid (primary) | Static-order exists | Final target live | Roots with a novel enabler | Novel + valid | Mean len | Mean retention | Mean re-destined | Roots with any top-5 valid |
|---|---|---|---|---|---|---|---|---|---|
| ORIG | **0** | 5 | 12 | 0 | 0 | 7.71 | 1.00 | 0.00 | 0 |
| DEST_ONLY | **0** | 5 | 5 | 0 | 0 | 8.04 | 1.00 | 6.96 | 1 |
| **FULL-R** | **0** | 5 | 10 | **11** | 0 | 8.29 | 0.997 | 4.67 | 0 |
| FULL-R-GEOM | **0** | 4 | 13 | 9 | 0 | 8.67 | 1.00 | 2.92 | 0 |
| FLAT-STRONG | **0** | 1 | 2 | 24 | 0 | 7.96 | 0.60 | 4.79 | 2 |
| RANDOM-MATCHED | **0** | **14** | 15 | 11 | 0 | 8.25 | 1.00 | 6.04 | 1 |

**Paired FULL-R:**

| Comparison | Primary wins / losses (net) | Static-existence net |
|---|---|---|
| vs FLAT-STRONG | 0 / 0 (0) | +4 |
| vs RANDOM-MATCHED | 0 / 0 (0) | **−9** |
| vs ORIG | 0 / 0 (0) | 0 |
| vs DEST_ONLY | 0 / 0 (0) | 0 |
| vs FULL-R-GEOM | 0 / 0 (0) | +1 |

Root-bootstrap 95% intervals of the primary net are [0, 0] throughout.

**Learned contribution:** none is measurable (FULL-R 0 = GEOM 0).

## 3. What changed versus P7A, and what still fails

**Fixed, as designed:**
- **Enabling movers now survive the search.** FULL-R's funnel, as object counts summed over 48 endpoints:

  | Stage | Objects |
  |---|---|
  | suspect | 443 |
  | legal actions generated (47,528 actions) | 443 |
  | scored | 434 |
  | beam survivor | 289 |
  | complete candidate | 312 |
  | top-5 | 55 |
  | committed | **13** |

  Novel enablers appear in **11/24** committed FULL-R plans (P7A: 0/29 endpoints moved a blocker).
- **Original work is preserved.** Retention is 0.997, with exactly one atomic cap substitution committed. There is no ordinary deletion, and there are no short collapsed plans (mean length 8.3).
- **FLAT-STRONG** builds full-length plans (mean 7.96, matching the anchor length). RANDOM-MATCHED uses the same transitions and quotas.

**Still failing** (post-hoc descriptive breakdown from the same sealed predictions, `P7AR_POSTHOC_FAILURES.json`; it does not change the gate):

| Arm | First static failure (pick / place / both / final target) | Mean static-valid prefix fraction | First failure at a novel enabler |
|---|---|---|---|
| ORIG | 6 / 12 / 4 / 2 | 0.21 | 0 |
| DEST_ONLY | 12 / 5 / 2 / 5 | 0.33 | 0 |
| FULL-R | **18** / 3 / 1 / 2 | 0.15 | 6 |
| FULL-R-GEOM | 16 / 2 / 6 / 0 | 0.09 | 7 |
| FLAT-STRONG | 17 / 2 / 3 / 2 | 0.34 | 10 |
| RANDOM-MATCHED | 15 / 3 / 4 / 2 | 0.19 | 5 |

- **The directional access proxy does not track the static checker's grasp screens.** FULL-R improves *its own* proxy access (for example, o02 goes from 0.37 to 1.00 in `p7ar_examples.png`). Yet its plans fail at a **pickup** in 18 of 24 roots, earlier on average than ORIG.
- **Random proposals produce more statically reorderable assignments.** RANDOM-MATCHED's committed assignments admit a static order in 14 roots, against 5 for FULL-R. The proxy-guided enabler choice is therefore *worse* than random at producing reorderable object sets. Even so, no arm's search ordered any of those 14 correctly.
- **A third of enabler failures start at the enabler.** In 6 of FULL-R's 22 first failures, the enabler itself is statically non-executable. Its own access is mis-estimated by the proxy.

## 4. What is validated, learned, heuristic or unverified

| Category | Items |
|---|---|
| **Mathematically validated (17 fixture tests)** | <ul><li>The repair grammar: legal destinations, no target move, move-once, ≤ 12 moves.</li><li>Atomic substitution only at the cap, never cheaper than executing the replaced move.</li><li>No ordinary deletion.</li><li>The potential difference is counted once (independent recomputation).</li><li>Zero-effect nuisance moves are never chosen.</li><li>New destination blockage is penalized.</li><li>Enabler-of-enabler chains work.</li><li>FLAT-STRONG reaches lengths 4, 6, 9 and 12.</li><li>Determinism, budget caps, funnel monotonicity, AST leakage.</li></ul> |
| **Learned (frozen, unchanged)** | <ul><li>cVAE S0 placement priors.</li><li>Temporary-target ŷ (within-parent rank).</li><li>Endpoint ŷ (within-root rank).</li><li>P4 anchor pools.</li></ul>No measurable contribution here. |
| **Hand-designed heuristics** | <ul><li>Directional corridor access proxy.</li><li>Potential Φ, with constants λ_e, λ_sub, w_TR, Γ.</li><li>Suspect and placement rankings.</li><li>Quotas.</li></ul> |
| **Physically unverified** | <ul><li>Everything.</li><li>Static validity is only a necessary screen; P5B executed 1/27 static-valid orders.</li></ul> |

## 5. Protocol, leakage and provenance

**Amendment R1:** λ_sub changed from 1.0 to 0.3, based on a synthetic fixture only, before any new-root work. It is disclosed in the pre-registration.

**No other change after the freeze.** The old-DEV debug (3 roots) checked runtime, stops and the public funnel only; no labels were computed.

**Leakage and provenance:**
- **Boundary in code:** the AST test shows no privileged token in `p7ar_repair.py` (kill tables, `dev_eval`, P5/P6/P7 evaluators, teacher, witness, K_lb, `roots_private`, `unmoved_blockers`, exposed-root ids). The path guard is active during `run`.
- **Public file is clean:** the public root file contains no witness or K_lb field (checked).
- **Planner inputs:** the planner read only `roots_public.jsonl`, `endpoints.jsonl` and the frozen bundle (hash-checked at load; `MANIFEST.json` SHA in the freeze manifest).
- **Evaluator ran once,** on the sealed predictions (SHA recorded in `P7AR_EVAL.json`).

**Regression:**
- 85/85 tests pass: P7A-R 17, P7A 12, P6A 28, P5B 9, P5A 19.
- `test_p1_p2` passes 22/22, and the `test_p4_mock` output is identical to the committed `GATE_B_MOCK.json`.
- No pre-existing file was modified.

## 6. Resource ledger (actual; per-endpoint caps were model 6,000 / ŷ_end 200 / geometry 3,000,000 / 24 layers; every run stopped `BEAM_EMPTY`)

| Arm | Model calls | Geometry access evaluations | Expansions | Layers | Wall (s) |
|---|---|---|---|---|---|
| DEST_ONLY | 45,921 | 666,278 | 45,921 | 374 | 58.6 |
| FULL-R | 63,963 | 1,429,024 | 99,335 | 742 | 86.4 |
| FULL-R-GEOM | 0 | 1,328,868 | 94,854 | 737 | 7.8 |
| FLAT-STRONG | 110,249 | 1,175,588 | 110,249 | 374 | 101.6 |
| RANDOM-MATCHED | 83,202 | 1,648,718 | 117,244 | 755 | 118.5 |

**Totals:**
- New-root P4 pipeline: about 6 min wall (≤ 6 workers).
- P7A-R predictions: 6 min 15 s on one GPU.
- Evaluator: about 1 min.
- Teacher calls: 0.

## 7. Files

**Added:**
- code: `p7ar_repair.py` (public), `p7ar_roots.py` (selection is evaluator-side; build is public), `p7ar_eval.py` (evaluator), `tests/test_p7ar_repair.py`;
- in `reports/p7ar/`:
  - `P7AR_PREREG.md` (+ R1), `P7AR_ROOT_SELECTION.json`, `P7AR_FREEZE_MANIFEST.json`, `P7AR_ENDPOINTS.jsonl`;
  - `P7AR_PREDICTIONS.jsonl` + `P7AR_PREDICTIONS_SEAL.json`;
  - `P7AR_EVAL.json`, `P7AR_PER_ROOT.json`, `P7AR_PER_ROOT.csv`, `P7AR_POSTHOC_FAILURES.json`;
  - `p7ar_examples.png`, `p7ar_primary_funnel.png`;
  - this report and `P7AR_DECISION.md`.

**Private, never committed:** `roots_private.jsonl` (K_lb and layout) and kill-table outputs.
