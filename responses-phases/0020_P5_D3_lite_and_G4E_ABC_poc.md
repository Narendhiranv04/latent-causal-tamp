# 0020 — P5: corrected B/C layout, D3-lite collection (batch 1, gated) and the first real A/B/C proof of concept

| Field | Value |
|---|---|
| Report number | 0020 (new; 0001–0019 unchanged) |
| Date | 21–22 October 2026 |
| Stage | **P5 only.** P5.0 foundation, D3-lite collection (batch 1; batch 2 halted by its predeclared gate), and the G4E-ABC tiny-data proof of concept. **No** G5/G6, 40-root collection, 3D or hardware. |
| Contracts | `instruction-phase-md/P5_D3_Lite_Then_G4E_ABC_POC_Execution_Plan.md` (primary, 199 lines) and `A_B_C_Learning_Methodologies_Detailed_Explained_Report.md` (explanatory, 751 lines). Both read in full; your files, left untracked. Methodology v1.7 and Guide v1.9 remain authoritative, amended only by `2D-ABC-OPNEG-v1`. |
| Previous turn sync | Report 0019 was committed as `0bd8fdd813308cc638f8fda3cb872aac422f62a9`. At the start, HEAD = `origin/main` = `0bd8fdd`. |
| Run directory | [`../runs/p5/`](../runs/p5/): `g4b/`, `regression/`, `d3lite/`, `g4e/` (each with a sha256 manifest) |

**Verdicts**

| Gate | Verdict |
|---|---|
| `P5_LAYOUT_SAMPLER_PASS` | **PASS** |
| `P5_D3_LITE_COLLECTED` | **PARTIAL**: batch 1 collected; batch 2 halted by its gate (0 order contrasts) |
| `G4E_A_B_C_IMPLEMENTED` | **PASS** |
| `G4E_TINY_OVERFIT_PASS` | **PASS** (in-sample). Validation and holdout are smoke checks only. |
| `G5/G6` | **NOT_AUTHORIZED** |

**STOP.**

---

## 1. What was built (new or changed code; no historical file touched)

| File | Role | Logical lines |
|---|---|---|
| `zlayout.py` (new) | **Z_LAYOUT_V2**: z0, eligible zS[k], zR (m ≥ 1), zO[t] only for t < m (m ≥ 2); canonical slot→query map; alias, version and hash refusal; `from_v1` view of stored evidence; exact marginal via `sampler` | 79 |
| `d3lite.py` (new) | Frozen construction: 8 seeds, predeclared family/split/batch, G4C `_layout` families J2/J1, target ρ ≥ 0.45 m, every rejection logged; 12-query catalogue with V2 layouts | 132 |
| `d3lite_run.py` (new) | Collection over the **unchanged** guarded runner: reference phase, then obstructed phase; checkpoint gate; sealed holdout; V2 pools | 138 |
| `d3lite_figures.py` (new) | Scenes and catalogues, outcome grid, recorded witnesses, compute | 94 |
| `learn_data.py` (new) | Common learner view: `data.learner_tensors_v2` + frozen **DINOv2-small** mask-pooled object features; privileged namespace; leakage audit | 123 |
| `abc_models.py` (new) | Shared encoder and local factors; **A**, **B** and **C** energies; exact z enumeration | 155 |
| `abc_train.py` (new) | Masked losses, training, gradient norms | 140 |
| `abc_run.py` (new) | Guarded PoC worker: train 9 runs, evaluate, learned-energy sampler, sealed-holdout unsealing | 135 |
| `abc_figures.py` (new) | E1–E7 diagnostics from `results.json` | 108 |
| `teacher_pilot.py` (changed) | P4 seed-round loop extracted as `run_rounds()` (behaviour unchanged; P4 tests pass) | 201 |
| `run.py` | Commands `p5-d3lite`, `p5-g4e` | +14 |
| `tests/test_zlayout.py`, `tests/test_d3lite.py`, `tests/test_abc_models.py` (new) | 8 + 3 + 12 tests | — |

## 2. P5.0 — the mathematical foundation (all before any collection)

**Z_LAYOUT_V2.** For the P4 AB two-move repair, `from_v1` keeps the stored 8-slot evidence untouched and drops only `zO[2]`. The result is **7 distinct active slots**, mapping to the same 7 physical queries.

Tests check:
- exact `logsumexp` equal to brute force;
- inactive placeholders change neither the energy nor any probability;
- normalization;
- the finite-difference gradient of Ē;
- refusal of alias, version, hash, active-mask and > 8-slot violations.

The G4B synthetic layout already used the correct rule (`zO0`/`zO1` only when m ≥ 2). The defect existed **only** in the G4C/D2 data layout (`g4c.layout`, frozen, unchanged).

**G4B re-run** (`python run.py g4b --out runs/p5/g4b`): **PASS**. Maximum proof error 4.4e-16, **0** planner calls, 79.2 CPU-s (≤ 120).

**P4 `loss_masks` change.** It is now covered by a **full** guarded regression: `python run.py g4c-lf-p4-regression --out runs/p5/regression`.

| Item | Result |
|---|---|
| Tests | **273 / 273 passed** |
| Archived replays | **6 / 6 passed** |
| CPU (process-tree guard) | **341.7 CPU-s of 650**, 0 overshoot |
| Wall | 349 s |
| In-process planner calls | **621 / 60**, exactly the historical baseline |

**Gate P5.0: PASS.** Collection started only after this.

## 3. D3-lite collection (`runs/p5/d3lite`, `python run.py p5-d3lite`)

### 3.1 Frozen plan (before any teacher call)

**Roots.** Seeds 2026102201…08. Families predeclared by index: J2 (goal occupant A + adjacent access blocker B, the r19 pattern) and J1 (goal occupant A + corridor blocker C).

| Batch | Roots | Splits |
|---|---|---|
| 1 | indices 0–3 | train, train, validation, holdout |
| 2 | indices 4–7 | train, train, validation, holdout |

Each batch holds 2 J1 + 2 J2. **15 construction attempts** were logged (7 rejected: 4 with target ρ < 0.45 m, 3 where the family pattern could not be placed).

**Catalogue per root (12 queries):**
- the reference (clean-base) empty repair, as its own root and never in a z-vector;
- the obstructed scene's empty repair;
- A→a and B→b;
- A→a,B→b and B→b,A→a;
- fixed-robot edits A, B, joint and nuisance;
- alternatives A→a2 and B→b2.

That makes **96 queries and 288 seed units**. All scene edits are eligible and all sequences are canonical.

**Static admission:** 51.9 CPU-s of 300.

**Selection bias, recorded:** the ρ ≥ 0.45 m preference, and the J1/J2 families (whose goal occupant makes the original task and every repair not moving A **trivially** GOAL_OVERLAP-negative).

### 3.2 Batch 1 results (4 roots, 48 planned queries)

| | Count |
|---|---|
| **VERIFIED_FEASIBLE** | 22 (incl. all 4 references) |
| **CERTIFIED_INFEASIBLE** | 20 (all static GOAL_OVERLAP) |
| **BUDGET_INFEASIBLE** | **0** |
| **UNKNOWN** | **6** |
| NOT_RUN | 0 |
| FATAL | 0 |

Development roots (holdout outcomes sealed): 19 verified / 15 certified / 0 budget / 2 UNKNOWN.

**The 6 UNKNOWNs**, all expensive single repairs or a scene edit of the goal occupant:
- `d3_…01: o00>32`, `o00>33`: seeds 1 and 2 each **CPU-censored at 240 s**; seed 3 never admitted because the batch budget was exhausted.
- 4 on the holdout root: guard-censored or not admitted.

The UNKNOWN reason string reports only "declared seed(s) not run"; the ledger (`attempts.jsonl`) shows the censoring explicitly. None became a negative.

**Compute.**

| Item | Value |
|---|---|
| Collection total | **2,307.5 CPU-s** (process 2,316.4) of the 2,400 batch-1 / 4,800 total caps |
| Wall | 2,305 s |
| Seed attempts | 32 (23 COMPLETED, **9 CPU_CENSORED**) |
| Inner calls | 19 relocation skills, 22 target evaluations; 9 in-flight attempts not recorded at connector level |
| CPU per lineage | `…01` 970, `…02` 38, `…03` 16, holdout `…04` 1,220 |

**Effects and pools.** All are **proof-grounded** (witnesses versus certificates; no budget labels in D3).

| Item | Result |
|---|---|
| Scene effects, all 3 dev roots | A edit **+1**, B edit **0**, joint **+1**, nuisance **0** |
| Scene interaction κ_S | **0** in 3 roots |
| Omission interaction κ_O | **0** in 4 (root, order) cases |
| Same-endpoint swaps | **both orders witnessed feasible in all 3 dev roots**, so **0 decided order contrasts** |
| Complete V2 joint pools with both classes | `d3_…02` (train) and `d3_…03` (validation): 7 candidates, 6 nonempty each; `d3_…01` incomplete |
| First-witness J labels | 12 on dev roots, including 2 whose target is UNKNOWN (relocation cost valid per v1.7) |

**Checkpoint gate** (predeclared: `GATE` in `d3lite_run.py`):

| Condition | Result |
|---|---|
| Undecided | 6/48 = 12.5 % (≤ 25 % ✓) |
| Roots with a multi-repair complete pool | 3 ✓ |
| Fatal | none ✓ |
| **Decided order contrasts** | **0 ✗** |

**→ Batch 2 halted.** Its 48 queries are recorded as NOT_RUN, never as labels.

**Scientific reading.** In these J2/J1 constructions the adjacent blocker does **not** obstruct the goal occupant's relocation, so the order does not matter. The catalogue produced recovery, scene effects and joint pools, but **no** order dependence.

## 4. The learner view (`learn_data.py`, `runs/p5/g4e/dataset.pt`)

- **Visual features: no blocker.** Frozen **DINOv2-small**, pinned revision `ed25f3a3…` (official weights, `safetensors`, local cache; no remote code). Run on the 224 × 224 initial RGB of each root's appearance anchor; patch tokens (16 × 16 × 384) are area-pooled per instance mask.
- **Numeric inputs** are the allowlisted `learner_tensors_v2` fields: object xy, radius and flags, robot q, goal xy, FK joints.
- **Candidates:** canonical sequences, ideal-prefix positions, V2 slot names.
- **Privileged namespace** (losses only): y, source, weight, first-witness J, z labels and sources, analytic static labels.
- **`leakage_audit` passes:** inputs are exactly the 8 allowlisted keys. Root, lineage and split are audit metadata only.

**Development data.**

| Item | Count |
|---|---|
| Roots (incl. 3 empty batch-2 roots carrying static labels only) | 14 |
| Candidates | 56 |
| **Decided** | **30** (16 positive / 14 negative, of which 2 P4 budget negatives) |
| Cost labels | 24 |
| Candidates with complete z | 24 |

**Holdout, unsealed once at the end:** 4 roots, 5 decided labels.

## 5. The models (`abc_models.py`; T = 1, width 128, all float64, CPU)

**Shared by all three:**
- DINOv2 384 → trainable 32-dimensional projection, plus 14 numeric descriptors per object (xy, flags, base polar, goal and target offsets) → MLP → 128-dimensional object token.
- A robot/goal context MLP.
- Unary U and **symmetric** pair V heads, with energy e = softplus(−logit).
- Ideal-prefix action tokens (start token, end token, pooled prefix scene, step).

**Architectures:**
- **A** (383,780 parameters): GRUCell(128) over action tokens → task logit u and travel Ĵ. E_A = ΣU + ΣV + softplus(−u). Explanations come by **re-scoring** (empty repair under edited poses; shorter sequences).
- **B** (449,958 parameters): explicit binary z over the V2 active slots.

  $E_B(r,z)=E_{static}-\sum_k s_kz_k-\sum_{k<l}W_{kl}(r)z_kz_l$

  - s_z0 and s_zS come from (edited) scene encodings;
  - s_zR and s_zO come from **prefix-pair** order interactions (no GRU);
  - W(r) is a learned symmetric coupling between typed slot vectors, conditioned on the repair summary;
  - **exact** enumeration of 2^K states (K ≤ 8); Ē = −T·logsumexp; marginals are exact.
- **C** (466,726 parameters): B's z, scene and coupling factors, with the order factor **replaced** by A's GRU (tested: C has no prefix-pair module and B has no GRU).
- **Ablations:** A-no-order (sorted actions, initial-scene prefixes: provably order-invariant), B-no-coupling and C-no-coupling (W ≡ 0), and certified-only A/B/C (budget-sourced labels masked).

**Losses** (`abc_train.py`, all weights 1; AdamW, lr 1e-3, weight decay 1e-4):
- static BCE;
- task BCE (A: GRU logit; B/C: logit of the **derived** marginal p(z_R = 1), or p(z_0 = 1) for the empty repair);
- B/C outcome-field BCE on every decided active slot;
- effect MSE (scene and omission, both sides decided);
- log-Huber cost;
- A's finite-pool feasibility loss;
- **B/C exact joint pool likelihood over all (r, z) states** of fully decided candidates.

**12 model tests:**
- exact partition and marginals versus brute force;
- masked fields give no loss term;
- coupling gradients exist only with coupling;
- order capacity (A-no-order exactly invariant);
- pair symmetry and object-permutation invariance;
- a finite-difference check of Ē;
- tiny overfits in which the witnessed order beats its swap;
- the leakage audit.

## 6. PoC results (`runs/p5/g4e`, `python run.py p5-g4e`)

**Envelope:** one `teacher.guard` process tree, **826.4 CPU-s of 3,600** (process 836.1), **827 s wall of 7,200**, 0 overshoot, **0 teacher or planner calls**, 1 torch thread. Nine runs × 400 full-batch epochs. Checkpoints are `ckpt_*.pt`.

| Run | Loss start → end | Train task acc | Train rank acc (4 roots) | Train effect MSE | Val acc (n = 8) | Holdout acc (n = 5) |
|---|---|---|---|---|---|---|
| **A** | 3.61 → 0.94 | 1.00 | 1, 1, 1, 1 | 0.273 | 0.50 | 1.00 |
| A-no-order | 3.61 → 1.21 | 0.95 | 1, 0.67, 1, 1 | 0.295 | 0.50 | 1.00 |
| **B** | 8.99 → 1.15 | 1.00 | 1, 1, 1, 1 | **0.027** | 0.75 | 1.00 |
| B-no-coupling | 8.75 → 3.25 | 1.00 | 1, 1, 1, 1 | 0.144 | 0.38 | 0.80 |
| **C** | 8.98 → 1.12 | 1.00 | 1, 1, 1, 1 | **0.021** | 0.75 | 1.00 |
| C-no-coupling | 8.76 → 1.42 | 1.00 | 1, 1, 1, 1 | 0.007 | 0.38 | 1.00 |
| A certified-only | 3.53 → 0.84 | 0.91 | 1, 1, 1, 1 | 0.318 | 0.75 | 0.40 |
| B certified-only | 9.47 → 1.45 | 0.95 | 1, 1, 1, 1 | 0.067 | 0.75 | 0.60 |
| C certified-only | 9.47 → 1.42 | 0.95 | 0.75, 1, 1, 1 | 0.053 | 1.00 | 0.40 |

**Order (the r19 access contrast, proof-grounded).**

| Model | p(o00>27.o01>28) / p(o01>28.o00>27) |
|---|---|
| **A** | 0.000 / 1.000 |
| **B** | 0.000 / 1.000 |
| **C** | 0.002 / 0.995 |
| B-no-coupling | 0.06 / 0.99 |
| **A-no-order** | **0.5 / 0.5** (cannot separate; no credit for order without the ordered factor, as required) |

The D3 swap pairs are positive/positive; all models give both orders p ≈ 1.

**Joint B/C fit.** The joint pool loss reaches its theoretical floor, mean(log #positives per pool) = (log 2 + log 4)/2 ≈ 1.04: B 1.06, C 1.05. For the P4 AB two-move repair, B and C's exact marginals match **all 7 observed slot labels**, and the exact joint concentrates on the observed bundle `0101101` (B 0.96, C 0.99; figure E5).

**Coupling.**
- The coupling module receives the **largest** gradient norm of any module in B (6.2) and C (2.7), and none in the no-coupling ablations (E6).
- Removing coupling raises B's train effect MSE (0.027 → 0.144) and its joint pool loss (1.06 → 2.83).
- In C, removing coupling did **not** hurt the in-sample fit (effect MSE 0.007). This is not a measured benefit of coupling in C at this data size.

**Effects.** A's re-scoring explanations plateau at effect MSE ≈ 0.25. B/C's explicit outcome variables fit the decided scene and omission contrasts almost exactly in-sample. This is the first measured indication of the B/C hypothesis, **in-sample only**.

**Cost.** All three track measured first-witness J on training repairs (A closest, for example 1.24/1.24 and 2.79/2.79; E4). Validation and holdout cost errors are larger.

**Selection.** The lexicographic selection (p ≥ 0.5, then fewest moves, Ĵ, C_d, energy) picked a witnessed-feasible candidate on every train root where one was eligible. On validation, A and the no-coupling ablations picked a negative on one root; B and C did not. n = 2 roots, so this is anecdotal.

**Sampler.** On the learned sampling energies (E + C_d + Ĵ) of the `d3_…01` root (13 states):
- G4B-kernel transition matrices **pass** detailed balance and stationarity, with maximum error **2.2e-16**, for A, B and C;
- the 3,000-step chain has total variation 0.033 / 0.035 / 0.051 from exact π (E7).

**Diagnostics** (figures in `runs/p5/g4e`): E1 per-term loss curves; E2 energies per candidate against labels (budget negatives hatched); E3 order pairs; E4 effects and costs; E5 exact B/C marginals and joint states; E6 gradient flow; E7 sampler.

D3 figures in `runs/p5/d3lite`: real 3R scenes and predeclared ghost destinations (A), the outcome grid (B), six **recorded** two-move witnesses (C), and compute (D).

**Observed problems, reported as they are:**
- **Optimizer spikes.** Transient loss spikes occur (B around epoch 185, C around 180, B-certified-only around 290), then recover. There is no gradient clipping; recommend adding it.
- **Static factors are barely supervised.** The catalogue's static labels are essentially all "valid", so the static heads learn a constant (static loss ≈ 0, near-zero gradients). Meaningful static supervision needs a catalogue that includes statically invalid endpoints.
- **The certified-only ablation is weak here.** Only P4's 2 budget negatives differ, since D3 has none.
- **Validation and holdout differences are meaningless at this size**, even where certified-only variants score 0.4–0.6 on 5 holdout labels.

## 7. Integrity and resources

**Frozen evidence.** Byte-identical against their manifests: `g4c_d2_poc_s` (452), `g4c_pilot` (324), `g4d_evidence` (129), `g4c_d2_precheck` (9), `g4c_preflight` (7), `g4c_d2_p3a_static` (13), `g4c_lf_p4/pilot` (104), `g4c_lf_p4/regression` (20). No historical label or configuration changed.

**Post-hoc regeneration.** The D3 figures were regenerated **from saved records** after a legend fix (no teacher call), and the D3 manifest was rewritten to include them. P4's committed figure, which has the same cosmetic legend issue, was **not** touched.

**Resources against caps.**

| Phase | Used | Cap |
|---|---|---|
| G4B | 79.2 CPU-s | 120 |
| Regression | 341.7 CPU-s / 349 s | 650 / 1,500 |
| Static admission | 51.9 CPU-s | 300 |
| Collection | 2,307.5 CPU-s / 2,305 s | 2,400 (batch 1) / 4,800 total; 7,200 s wall |
| PoC | 826.4 CPU-s / 827 s | 3,600 / 7,200 |
| Unit tests and smoke runs | ≈ 35 CPU-s | not separately capped |

**Calls.**
- Collection inner calls: 19 relocation, 22 target, 9 censored in-flight (not recorded at connector level). Coordinator: 0 (guarded).
- Model training: 0.

**Working tree.** The two pre-existing root PDF deletions and all your untracked files (instruction files, root PDFs, bundle) are untouched and unstaged.

## 8. Assessment: what works, what does not, what is missing

| Level | Status |
|---|---|
| Software correctness | **PASS**: exact layout, exact joint normalization, masking, coupling gradients, symmetric factors, order (in)sensitivity, sampler detailed balance, no leakage, no teacher calls |
| Tiny-data overfitting (in-sample) | **PASS** for A, B, C: decided labels, rankings, the r19 order contrast, the joint z pools (at their floor), costs. B/C additionally fit effects that A's re-scoring cannot. |
| Operational-label prediction out of sample | **Not established**: 8 validation and 5 holdout labels |
| Physical repair success | **Not measured.** No model-chosen repair was executed by the robot. All selections were compared offline to stored labels. |

**Missing data, specifically:**
1. **Order contrasts.** J1/J2 produced none. Use an access-coupled construction, e.g. the r19/J9 or P3a-certified first-action pattern: a neighbour occluding the occupant's in-sector grasps.
2. **Nonzero interaction κ.** Every decided κ was 0. A dual-blocker family is needed where both blockers must move.
3. **Budget negatives in fresh roots.** None occurred. Expensive single-move repairs were **censored** (UNKNOWN) at 250 CPU-s rather than ending in clean terminals.
4. **Statically invalid catalogue endpoints** for the static heads.
5. **More independent roots** before any out-of-sample claim.

## 9. Recommendation for what would unlock G5/G6 (requires your authorization)

**P6a — targeted contrast collection, not another generic batch.**

| Item | Proposal |
|---|---|
| Roots | 8 new independent roots from a **J9/r19-type access family** (occupant + occluding neighbour + annulus barrier, admitted only if the P3a checker certifies the occupant's first action, zero planner) plus a **two-necessary-blocker family** for κ ≠ 0 |
| Catalogue | The same 12-query template, plus 1 statically invalid endpoint per root |
| Policy | Unchanged `2D-ABC-OPNEG-v1` |
| Caps | ≤ 96 queries, ≤ 4,800 CPU-s, 1 worker |
| Gate | Same gate, but **requiring order contrasts and κ ≠ 0 in batch 1** |

Measured basis: the cheap roots cost 16–38 CPU-s each; one expensive root costs about 1,000 CPU-s. So a per-root CPU cap (≈ 600 CPU-s) should be predeclared to stop a single root consuming the batch.

**P6b — G4E iteration before G5:**
- gradient clipping;
- **validation-only** early stopping;
- a capacity-matched A;
- a geometry-only arm (no DINOv2) to isolate the appearance contribution;
- 3 seeds per arm;
- CPU ≤ 3,600 per round.

**G5/G6 only when:** at least 6 independent roots carry decided order contrasts, at least 4 carry nonzero κ, and there are at least 10 complete joint pools across ≥ 6 roots, split before descendants. Then 3 seeds × {A, B, C, ablations} on matched data and compute, with one-shot robot verification of the selected repairs on held-out roots.

## 10. Commands

| Command | Exit | Result |
|---|---|---|
| `python -m pytest -q tests/test_zlayout.py tests/test_d3lite.py tests/test_abc_models.py` | 0 | 23 passed |
| `python run.py g4b --out runs/p5/g4b` | 0 | PASS |
| `python run.py g4c-lf-p4-regression --out runs/p5/regression` | 0 | 273/273, 6/6 |
| `python run.py p5-d3lite --out runs/p5/d3lite` | 0 | batch 1 collected; gate halted batch 2 |
| `python run.py p5-g4e --out runs/p5/g4e` | 0 | 9 runs trained and evaluated; holdout unsealed once |

Committed with explicit paths only, and pushed without force. Hashes and remote verification are given in chat and recorded in report 0021.

**STOP.** P6a/P6b, G5/G6, 40-root collection, 3D and hardware need separate authorization.
