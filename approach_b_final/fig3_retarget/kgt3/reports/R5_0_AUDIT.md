# R5.0 — implementation and evidence audit

**Branch:** `naren/rss27-fig3-retarget-home`
**Anchor:** `ea80e7d5e4`, verified equal to HEAD and origin on 2026-11-27 08:25 UTC, with no newer work.
**Scope:** cheap audits and correctness fixes only. No training, no new physical queries, no TEST or release_v2 access.

## 1. Branch, assets and resources

| Item | Value |
|---|---|
| gvlab2 | 48 cores, idle (load 0.04); RTX 5090 32 GB, idle; 107 GB RAM available |
| /home free | 34 GB (plan floor ≥ 20 GB, so ≤ 14 GB usable; R5/R6 request ≤ 2 GiB) |
| Environments | envgpu (models, torch), env2d (BXY teacher, PIL), env3d (SHELF66V3 / MuJoCo; no PIL) — all Python 3.13.11 |
| Frozen bundle | `$FIG3_BUNDLE` = k45/inf/bundle (hash-checked by `benchmark.load_bundle`) |
| Development X checkpoints (controls only) | r3/ckpt `3d_{F1,F2,M1,M1s,G1,G1s}_s{0,1}`, kgt3/ckpt `3d_M1ft_{O1,O2}_s{0,1}`. **No 2D query-relative checkpoint exists.** |
| Earlier X-head training cost | 5–25 s GPU per run (`curve.json` wall_s) |

## 2. R4 evidence reproduced from raw records (`r5audit.py`)

- **Seals.** All 16 `*.SEAL` files under `kgt3/` (KGT3 and R4) match their file hashes and job counts.
- **Recount.** Independent logic over the raw `phys*.jsonl` and selections, separate from the R4 analysis code, reproduces every R4 headline:

| Stage | Recount | R4 report |
|---|---|---|
| R4.2 strict success (20 roots per arm) | F0 2, M1s 10, G1s 11, O2 6, RANDOM 3, WITNESS 18 | same |
| R4.5 3D success / > 3 actions | FLAT 3/2, REC 10/8, GA 9/9, B0 2/0 (20 roots) | same |
| R4.3 queries | 1,159: 492 SUCCESS / 492 CERTIFIED / 175 UNRESOLVED; levels 0: 5, 2: 20, 3: 35 | same |
| R4.4 jobs | 626, 164 replayed X successes, 0 censored / error | same |

- **Exposure status (permanent).**
  - The 20 R4.2/R4.5 3D roots and the 30 coh2d 2D roots are development roots, never confirmation roots.
  - G1s was selected on the 3D panel.
  - Quarantined A2 outcomes enter only as labelled exact reuse.
  - The R4.3 (60) and R4.4 (34) families are development constructions. They were ranked once by frozen models and never trained on.

## 3. Leakage and provenance (`audit0.py`, extended)

- **Spec.** The extended audit loads the actual X model (F0 or G1s via `learn.load`) and the production F0 floor.
- **Import guard.** It is installed before any import and poisons 23 physical modules (teacher, simulator, planner, IK, geometry, kill tables).
- **Field tracking.** Tracked dicts record every row and inputs key read.
- **Sentinels.** Evaluator fields with sentinel values (`K`, `K_star`, `witness`, `labels`, `L_ref`, `split`, and inputs-level `witness_order`, `blockers`, `K`, `kill`) are injected into every row.
- **Plans compared.** Every arm (REC-ORDERED, FLAT-INSERT, GA) is planned three times: on the tracked row with sentinels, on the stripped public row, and on a row with a renamed `root_id`.
- **Relabelling.** Non-target object slots are permuted, and the audit checks identical X/Y/p11 readouts and mapped proposals.

**Result** (`r5/leak_3d_G1s.json`, `r5/leak_2d_F0.json`; 3 DEV roots per domain, all three arms, plus the production floor):

| Check | 3D (G1s) | 2D (F0) |
|---|---|---|
| Row fields read | `domain`, `inputs`, `root_id` | same |
| Input fields read | `attrs`, `base`, `cell_xy`, `cells0`, `ctx`, `goal`, `goal_cell`, `ids`, `legal_cells`, `q_ref`, `tid`, `xy0` (all allowlisted) | same |
| Fields outside the allowlist | none | none |
| Sentinel fields read | **none** | **none** |
| Plan = stripped-row plan | 9/9 | 9/9 |
| Plan = root-id-renamed plan | 9/9 | 9/9 |
| Relabelled scenes: proposals equal / max Δp | 3/3, ≤ 1.9e-7 | 3/3, ≤ 5.2e-8 |
| Physical modules imported | none (guard would raise) | none |
| Sampler task-conditioned | yes | yes |
| Scorer visual / geometry features | none (`vis_dim` −1 for the query-relative head, 0 for F0) | none |

- **Root IDs** are used only for caching keys and the deterministic RANDOM control seed. Plans are invariant to renaming.
- **Relative geometry.** The query-relative heads compute relative offsets and occupancy from public `xy0` / `cells0` / `goal` only.

## 4. Mathematical and bundle parity

- **Bundle parity** (`run.py parity`, 40 public VAL roots per domain vs sealed V3.4 GPU predictions):
  - decisions equal **40/40 (2D)** and **40/40 (3D)**;
  - max |Δ p11| = 3.5e-7 (2D) and 1.8e-7 (3D);
  - proposals equal on every root where the archive recorded them (2D 40/40; 3D 36/40, the other 4 being NOOP roots with no archived proposals).
- **DP exactness.** Grouped subset DP vs brute force (every order × every composition) for m = 1…6, both λ, precedence constraints, fixed-order DP, historical `order.dp` equivalence and request coverage. N_X(m) is exact and equals `len(requests)` for m ≤ 8. Tie-break is deterministic (energy, chunk count, canonical JSON) with no geometry term.
- **Energy contract.**
  - L ≤ 3: a single chunk with the exact joint p11 (GA, REC, assignment_given). There is no marginal competitor.
  - L > 3: Σ −log max(ε, marginal pX(chunk | canonical prefix scene at q_ref, original task)) − log max(ε, Y_global).
  - `has_multi` is unchanged: the primary objective requires a chunk of size ≥ 2 when L > 3. The all-singleton-inclusive objective remains a named R5.3 diagnostic.

## 5. Scene / grammar contract on real rows (`tests/test_r5_rows.py`, 6 tests on the DEV panels)

- **Rebasing.** It changes only the moved objects' cells and xy. Rebased `legal_cells` always exclude ORIGINAL occupancy and the original goal, so a vacated cell never becomes legal. `tid`, `goal` and `q_ref` are unchanged.
- **Temporary task (A → d).**
  - 2D: A takes the target role, the original target becomes an ordinary obstacle, and radius and fixed flags are unchanged.
  - 3D: `is_target` is one-hot on A.
  - Cells and `q_ref` are unchanged.
- **Grammar.** Move-once, distinct destinations, initially-vacant destinations only, original target never a mover, goal never a destination, and H = 5. Every `rebase` call site uses the ORIGINAL root, so initial occupancy is never lost in nested recursion.
- **Eligibility.** In recursion it is computed on the original root (original target excluded) plus `protect` (ancestors and the current temporary target).
- **H.** H = 5 in both domains (`planners.CFG["H"]`; KGT3/R4 used 2D H = 6). K6 DEV roots are excluded from scoped evaluation by evaluator-only roster filtering.

## 6. Engineering defects fixed (with regression tests)

| Defect (found in R4 code) | Fix | Test |
|---|---|---|
| `plan()` caught TimeoutError / CapReached and **discarded every candidate** | Candidates stream into a sink. A budget stop keeps every completed incumbent: GA keeps completed sizes only, with mode `EXACT_TIMEOUT` / `BOUNDED_TIMEOUT` and `exhausted = false`; REC keeps candidates ranked so far. `incumbent_from_stop` is recorded. | `test_timeout_midway_keeps_completed_incumbent` |
| Production floor (`rank.b0`) was computed by the caller and **excluded from per-arm timing** (R4 p4run) | `plan(..., floor=callable)` runs the floor inside the single deadline. It reports `floor_wall_s`, `arm_wall_s`, total `wall_s` and `deadline_overrun_s`. Historical dict-floor callers remain valid and are labelled. | `test_floor_inside_deadline_and_no_budget_left` |
| Separate wall budgets for REC discovery (0.6) and ranking (0.4); GA had its own | One absolute deadline (`cfg['t_end']`) for floor, proposal, recursion, scoring, composition and selection | same + existing tests |
| After a cap stop, selection called the capped model again (possible crash) | Selection runs with caps lifted and its readouts counted (`selection_readouts`) | `test_cap_stop_then_selection_is_uncapped_and_counted` |
| Empty candidate pool | ABSTAIN with 0 candidates, never a crash | `test_empty_candidates_abstain` |

- **Accounting.** Theoretical evaluations N_X, distinct cached readouts, requested reads, cache hits, unique model evaluations, batches, DP lookups and wall are reported separately (R4.0).
- **Shared floor.** It is never counted as a long repair (`long` requires a selected length > 3; `kind = production_floor` is flagged).
- **Physical feedback.** No physical feedback reaches a committed plan: plans are sealed before jobs, and runners read only manifests.

**Tests:** 53 pass on gvlab2 (20 KGT3, 2 learn, 25 R4/R5 unit, 6 R5 real-row).

## 7. Physical success contract (verified in code)

- **3D** (`physical3d.job`, unchanged SHELF66V3 teacher):
  - X runs every relocation with a planned and executed q_ref connector at each declared bound.
  - Y is an independent `bd_3dt.query` from q_ready on the settled ideal endpoint.
  - REPLAY is a fresh environment that re-executes the stored move witnesses, connector paths and the stored target witness **continuously from the achieved physical state**. It refuses a joint discontinuity > 0.02 rad and checks cell, |z| ≤ 1 cm and no displacement of other objects.
  - Strict success requires X = 1, Y = 1 and replay = 1, which is a composed sequential execution.
- **2D** (`physical2d.job`, unchanged BXY primitives):
  - `x_chunked` + `replay_xb` give exact continuity (1e-6), certified segments, placement at the lattice centre (1e-9) and a connector ending at q_ref at every declared bound.
  - Y is `bd_2d.t_goal` from q_ref on the ideal endpoint, with its own replay.
  - Because certified 2D placements are exact and the last connector ends at q_ref, the queried endpoint state equals the realised state. The composition holds by construction rather than by one continuous replay. This is stated as such, not claimed as a single replay.
- **No contract or budget change** in R5.0.

## 8. Local supervision inventory (`r5/inventory.json`)

**KGT3 P2:**

| | Labels | Families | Splits | Strict audit (R4.0) |
|---|---|---|---|---|
| 2D | 712 chunk labels from 1,032 runs (62% UNKNOWN runs excluded) | 115 | TRAIN 129 / SELECT 53 / GATE 530 (GATE never read by a model) | – |
| 3D | 621 | 128 | TRAIN 313 / SELECT 118 / GATE 190 | 51 budget-relative negatives, 42 un-replayed prefix positives |

**R4.3 2D (60 families, 1,159 runs).** Replayed positives and certified negatives by preceding moves h and chunk size g:

| h | g | Replayed + | Certified − |
|---|---|---|---|
| 0 | 1 | 373 | 175 |
| 0 | 2 | 88 | 77 |
| 0 | 3 | 31 | 222 |
| 1 | 1 | 79 | 0 |
| 1 | 2 | 24 | 6 |
| 1 | 3 | **0** | **0** |
| 2 | 1 | 48 | 12 |
| 2 | 2–3 | **0** | **0** |

**R4.4 3D (34 families, 626 jobs):**

| h | g | Replayed + | Certified − |
|---|---|---|---|
| 0 | 1 | 104 | 41 |
| 0 | 2 | 38 | 55 |
| 0 | 3 | 22 | 74 |
| 1 | 2 | 39 | 38 |
| 1 | 3 | 12 | 29 |
| 2 | 2 | 9 | 11 |
| 2 | 3 | 1 | 11 |

Budget-relative outcomes (71) are excluded from strict labels.

**Measured gaps.**
- 2D: no strict labels at h ≥ 1 with g = 3 or at h ≥ 2 with g ≥ 2, and no 2D query-relative model exists.
- 3D: h ≥ 2 is thin (21 / 22 labels).

## Gate

**R5.0: PASS.**

- Implementation correctness and leakage checks pass, all R4 evidence reproduces from raw records, and the five engineering defects are fixed with regression tests.
- No critical file is missing.
- **R5.0 cost:** 0.52 summed GPU process-hours (device wall ≈ 0.30 h), 0 physical CPU-h, 68 KB of storage.

**Open items carried to R5.1 / R5.3** (not defects):
- the 2D local-support gaps listed in §8;
- the `has_multi` and length-bias diagnostics on candidate final models;
- R6 runners must call `plan(..., floor=callable)` so floor cost is inside the timing.
