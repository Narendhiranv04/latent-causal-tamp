# 0115 — BXY-P10-PREREG: P-min definition, F1 screen, travel convention, V2 learner interface, cost model

Date: 2026-10-31. Gate: BXY-P10-PREREG only. Contract: `BXY_P9_AUDIT_AND_NEXT_GATE_2026-10-31.md` (the audit of 0114). Authority:
`Approach_B_Final_Methodology_2026-10-31.pdf` §§2–6, 8.

**Verdict: `READY_TO_REQUEST_BUDGET`.**

Nothing in this gate ran the robot teacher, collected labels, trained a model, read test labels, overwrote P9 or historical outputs, or
touched 3D. Section 8 states the exact resource request; **nothing is authorized until you approve it.**

---

## 1. State, inventory, hashes

| item | value |
|---|---|
| branch | `approach-b-xy-v1` |
| HEAD before | `68183081dbc1bc722a23e6efeb015454c616c88e` (P9) |
| HEAD after | the commit that adds this report; no other commit in this gate |
| dataset | the external BD_GEN_V1 snapshot (`BXY_DATA`), read-only, `sha256:78ca0e7c35d5a2b937554c03ce38b06db2486e5d74af5f2831e37e335ccb1a38` (recorded in the design) |
| P9 sidecar | `BXY_SIDECAR_V2_PILOT.json`, sha256 `adea6983…`, unchanged (asserted by a test) |
| P9 teacher hash | `sha256:4930754123e6905619b5e34ae450c8e78599643460c03e6cd0ce11393ea0a4fe`, unchanged (asserted), so reusing P9 labels is valid |

New files (no existing file was modified):

| file | role |
|---|---|
| `bxy_f1.py` | `BXY_F1_V1` analytic static screen |
| `bxy_v2.py` | read-only V2 sidecar adapter, `ModelXY2` with the complete-travel head, prediction and choice with F1 applied first |
| `bxy_pmin.py` | P-min design, freezing and launch guards, semantic provenance, instrumented Y counters, cost model |
| `tests/test_bxy_p10.py` | 15 tests |
| `runs/approach_b/bxy_pmin_v1/` | `PMIN_DESIGN.json` and `PMIN_LOCK.json` (frozen), `PMIN_SUMMARY.json` (informational), `regression/` (replays and full pytest log) |
| `responses-phases/0115_BXY_P10_PMIN_PREREG.md` | this report |

Unchanged, verified by `git diff --quiet HEAD` and by the preservation test:
- source files `bxy_core.py`, `bxy_run.py`, `bxy_lb.py`, `bxy_teacher.py`, `bxy_pilot.py`, `bxy_data.py`, `bd_core.py`, `bd_2d.py` and
  `config.toml`;
- run directories `runs/approach_b/bxy` (V1 sidecar, FROZEN, checkpoints), `runs/approach_b/bd2d_lb_v1` and
  `runs/approach_b/bxy_teacher_pilot_v1`.

`bxy_core.views` stays the V1 reader of the historical evidence, and `bxy_run.predict_xy`/`choose` stay as the historical P7 code.

## 2. Audit findings and what this gate did about each

| audit item | resolution |
|---|---|
| P0 F1 not enforced | `bxy_f1.py` implemented; applied to every design query and at selection (`bxy_v2.choose`). Pilot audited first: 0 of 77 P9 items fail F1. Two historical findings in §3. |
| P0 no-op J inconsistent | Complete-travel convention implemented in `bxy_v2` (§4). The historical `bxy_run.predict_xy` (`J_hat = 0` for the no-op) is kept as the P7 record, never reused for new selection. |
| P0 V2 cannot be consumed | `bxy_v2.views` built: identity re-derivation, observed/absent masks, shared Y nodes, complete-travel items, provenance; tested on the pilot (§5). No training was run. |
| P1 four-cell balance | Enumerated rather than outcome-selected: every admissible catalogue candidate, reversal and omission gets both X and its Y, so all four cells can occur without choosing queries by outcome (§6). |
| P1 omission / causal evidence | Every single-action omission of every multi-move candidate gets X and Y, recomputed from S0, so original-vs-omission pairs are matched by design (§6). |
| P1 custody / freezing / provenance | Historical test split excluded. Design and lock frozen before any collection and committed. `assert_frozen` and `admitted` guards added. Transitive semantic source hashes recorded. The P9 manifest is untouched (§7). |
| P1 Y counters | `bxy_pmin.y_query_counted` exposes `DetPhysics.used` per Y query without changing outcomes (tested against the unwrapped teacher). |
| P2 "P-min" ambiguity | Three named phases with exact counts (§6). The 0108 shape is `PMIN_FULL_CATALOGUE`; the requested phase is `PMIN_DEV_MATCHED`. |
| Separate X/Y cost | Bootstrap from P9 per-query CPU (X by prefix length, Y by K stratum) plus per-root overhead, with a stress scenario (§8). |

## 3. F1 analytic screen (`BXY_F1_V1`)

The screen is sound and geometry-only. It runs over the immutable root record: S0 disc poses, radii, legal cells, fixed ids, T and its
goal. It uses no planner, no IK and no learned score.

| group | rules |
|---|---|
| identity | ID_UNKNOWN, ID_TARGET, ID_FIXED, LENGTH (more than 6 relocations) |
| placement (sequential, in the ideal object prefix) | DEST_NOT_LEGAL, NULL_RELOCATION, DEST_OCCUPIED (the placed disc overlaps any stayed, already-relocated, fixed or target body *at that moment*, so it can be order-specific) |
| endpoint | PAIR_OVERLAP (checked on Y-only edits) |
| task | GOAL_BLOCKED (a body overlaps T's goal pose: the scene is legal but the complete task cannot succeed) |
| catalogue policy | DUPLICATE_OBJECT (the P9 scope rule; not a physical claim) |

How the rules gate queries:
- **X** is admissible when no identity, placement or policy rule fires.
- **Y** is admissible when its endpoint is a legal scene.
- **GOAL_BLOCKED** removes a *complete* candidate from selection only; neither query is labelled from it.
- F1 never writes a label, and never produces a motion negative.

**Checks:**
- **Agreement with the historical teacher (train/val):**
  - every one of the 15 historical `STATIC_INVALID` B labels is flagged by F1 at the same step;
  - no F1-admissible sequence carries `STATIC_INVALID`;
  - 2 further F1-invalid sequences failed earlier in motion (1 CERTIFIED_INFEASIBLE, 1 UNKNOWN_PLANNER).
- **Motion negatives preserved:** all 8 P9 X=0 cases (including s212's `ORDER_FIRST_ACTION` certificate and s047's planner timeout)
  are F1-admissible. F1 does not erase F2 order effects.

**Historical findings (reported, not rewritten):**
1. **17 recorded catalogue candidates on train/val are physically illegal.** They are mostly `alternative_destination` proposals that
   send two objects to the same cell, so their edited scene has two overlapping discs. They are F1-screened from the design and from
   selection.
2. **The V1 X/Y data contains static collisions labelled as X=0.** `BXY_SIDECAR_V1` derived X=0 for 15 of its 125 train/val X
   observations from such static collisions (`DERIVED_B_RELOCATION_FAILURE`). The P5–P7 X/Y runs therefore trained on a few X=0
   labels that are F1 illegalities rather than motion failures. This is history; V2 never reads V1 labels.

## 4. Complete-travel cost convention (resolves the no-op `J_hat = 0`)

This follows the PDF primary protocol, option (a) of the audit. Every candidate, the zero-move one included, is charged the travel of
its complete action witness:

`J_hat(r) = J_corr(g_r) + J_tgt(v_s(r), c)`

- `J_corr = softplus(cost(g_r))` for a nonempty prefix (relocations plus connector). It is **exactly 0** for the zero-move repair,
  because no motion precedes the target and the robot is already at q_ref; this is a fact, not a prediction.
- `J_tgt = softplus(jt([v_s, c]))` is a new scene head on the edited scene at q_ref.

**Supervision.** Only complete witnesses supervise travel:
- `J_total` of a replayed full-joint-success pair;
- for the no-op, the replayed Y0 target witness.

Failures carry no J label.

**Selection.** `bxy_v2.choose` applies F1 first (screened candidates are never scored, and the zero-move candidate is always kept).
It then applies the unchanged `bxy_run.choose` cost rule `C = −log p_succ + α m + β C_d + γ J_hat`.

**Tests:**
- the no-op gets J_hat > 0, and its value differs between scenes;
- the pilot yields 6 no-op travel items and 23 nonempty items, and failures contribute none;
- with λ_J = 0, the loss is the joint likelihood only;
- with γ = 0, rescaling J_hat cannot change the choice;
- an F1-screened candidate with p = 0.99 is never chosen.

**Deviation note.** The second scene head is the minimum needed to make no-op travel scene-dependent. Without it, the existing order
encoder maps the empty sequence to a zero vector, which gives every no-op the same constant travel. The incremental "corrective-only"
travel (option b) is **not** adopted. If it is ever reported, it must be labelled a secondary metric.

**LB comparison.** `bxy_run.predict_lb` gives LB `J_hat = 0` for all candidates, because LB has no travel head. Any future LB-vs-XY
selection comparison must therefore either use γ = 0 for both arms or state the asymmetry.

## 5. V2 learner interface (`bxy_v2.py`, tested, not trained)

**Reading.** `load` accepts only `BXY_SIDECAR_V2_PILOT` / `BXY_SIDECAR_V2_PMIN` and records the file's sha256. `check_identity`
re-derives every X2/Y2 key and its context (q_ref, goal, robot profile) from the immutable root record, and checks that there is a
single teacher hash. Any mismatch raises; the tests include tampered context and reordered actions.

**Labels:**
- An observation requires attempted, observed and y ∈ {0, 1}.
- CENSORED, NOT_ATTEMPTED, INELIGIBLE and F1-screened rows are absent, with their status kept in `provenance.absent`. They never become 0.
- Two rows with the same key must agree, otherwise `ConflictError` is raised.

**Variables:**
- every observed X, plus its parent Y (shared across orders);
- `full=True` adds every F1-admissible catalogue candidate as an unobserved variable.

**The pilot through the adapter:**
- 20 train roots;
- 49 X=1 and 8 X=0, 29 Y=1 and 30 Y=0;
- 11 parent Y nodes left unobserved (the X-only items);
- s047's reversed orders share one Y node;
- 29 travel items;
- no val or test roots.

**Correctness and leakage:**
- Root-exact `log_evidence` on a V2 view equals brute-force enumeration (to 1e-9).
- Model inputs are the leakage-audited LB record tensors plus (object index, cell centre) pairs. No teacher field reaches the scorer.

## 6. P-min definition (enumerated; no outcome selects a query or root)

**Custody:**
- Roots: train 176 + val 21 = 197, from the generator's family-grouped split.
- The 34 historical test roots are excluded: they were exposed in P7 and remain historical diagnostics only.
- A decisive test later needs fresh roots, a frozen model and a frozen evaluator.
- Root order is `sha([root, "BXY_PMIN_V1"])`.
- Strata: K0 142, K1 37, K≥2 9, None 9.

**Query classes.** All are deduplicated by V2 key, and F1 is applied to each:

| class | queries |
|---|---|
| `y0` | Y of the empty edit, one per root |
| `complete` | X and Y of every nonempty recorded catalogue candidate (the frozen selection catalogue) |
| `reversal` | X of the exact reversed order of every multi-move candidate; shares the forward candidate's Y |
| `omission` | X and Y of every single-action omission of a multi-move candidate, recomputed from S0 |
| `prefix` | X and Y of every proper prefix |

**Phases:**

| phase | classes | distinct X | X to query | distinct Y | Y to query | F1-screened (X / Y) |
|---|---|---|---|---|---|---|
| `PMIN_FULL_CATALOGUE` (0108 shape, train/val only) | y0, complete | 929 | 884 | 1,049 | 993 | 17 / 17 |
| **`PMIN_DEV_MATCHED` (requested)** | y0, complete, reversal, omission | **2,222** | **2,165** | **1,866** | **1,807** | 48 / 31 |
| `PREFIX_COMPLETE` (later) | prefix | 844 | 819 | 844 | 826 | 9 / 9 |

"To query" means not already observed in P9 under the identical teacher hash (57 X and 59 Y are reused).

**`PMIN_DEV_MATCHED` in detail:**
- **by prefix length (X):**

  | length | 1 | 2 | 3 | 4 | 5 | 6 |
  |---|---|---|---|---|---|---|
  | X queries | 556 | 756 | 600 | 242 | 60 | 8 |

- **by stratum (X):**

  | stratum | K0 | K1 | K≥2 | None |
  |---|---|---|---|---|
  | X queries | 1,596 | 332 | 185 | 109 |

- **by split:** X 1,980 train / 242 val; Y 1,666 train / 200 val.
- **matched pairs:** every X has its matched Y inside the phase (2,222 / 2,222).
- **order contrasts:** 551 same-endpoint order groups.
- **omission contrasts:** every omission has its parent candidate's X and Y.

**Relation to 0108.** 0108's "P-min" counted 1,114 X over all 231 roots, test included, and reused `labels.D` for Y. The new design
re-queries Y instead, for three reasons:
- the P9 contract needs a replayed target witness for every positive;
- `J_target` is needed for matched J;
- `labels.D` stays an agreement diagnostic only (P9: 45/45 agreed).

**Expected missing-label pattern after collection:**
- F1-screened queries are never labelled;
- proper prefixes outside the phase stay unobserved and marginalized;
- the empty prefix's X is the constant 1;
- administrative censoring is possible and is recorded as CENSORED, never 0;
- test roots are excluded.

**Remaining coverage limits.** These cannot be fixed by labelling the existing roots:
- only 9 K≥2 roots exist in train/val;
- hard K3/K4 scenes and a fresh independent test cohort need new root generation in a later gate.

No historical label was used to select roots or queries. Historical labels are used only in the F1 agreement check and as diagnostics.

## 7. Freezing and provenance

**Freeze.** `bxy_pmin.freeze()` wrote two files once, before any P-min result exists:
- `runs/approach_b/bxy_pmin_v1/PMIN_DESIGN.json`;
- `PMIN_LOCK.json`, holding:
  - the design sha256;
  - the requested phase;
  - **114 semantic source hashes**: the transitive repo-local imports of `bxy_teacher`, `bxy_f1`, `bxy_pmin`, `bxy_data`, `bxy_pilot` and
    `bd_2d`, plus `config.toml`; this is a superset of P9's `T.SOURCES`;
  - the git HEAD at freeze;
  - the freeze time;
  - `authorized: false`;
  - the requested caps.

A different rewrite raises `FileExistsError`, and freezing refuses to run if any result already exists.

**Launch guards for the collection runner:**
- `assert_frozen()` must pass before launch. It checks that the design matches the lock, that no semantic source has drifted, that both
  files are committed and clean in git, and that no result predates the lock.
- `admitted()` is a per-query guard. It allows only frozen, phase-member, F1-admissible, not-reused queries.

Both guards are tested, including a tampered design, an injected source drift, an uncommitted plan and late freezing.

**Frozen design:** `PMIN_DESIGN.json` sha256 `8f164845e5804821b8fbf9411c52ca2584f22d6f6f4a0efd19b8c3bcb86ff658`, with the requested caps
recorded in the lock. The source set is deliberately conservative: it also covers transitively imported modules such as `bd_3d.py`
and `abc7_*.py`, so editing any of them before launch requires a declared re-freeze.

**The P9 manifest** is untouched. New data will carry the new design and lock hashes.

**Y budget counters.** `y_query_counted` wraps `bd_2d._phys` for the duration of one call and returns the same DetPhysics object. The
test checks that the outcome row equals the unwrapped teacher's row exactly, apart from CPU time and the added counters, and that the
wrapper is removed afterwards.

## 8. Resource model and the exact request (not authorized)

**Measured P9 rates (worker CPU-s per query):**
- X by prefix length: 1 → 2.31, 2 → 5.59, 3 → 14.76, 4 → 15.04, 5 → 10.13 (n = 57; mean 6.6).
- Y by root stratum: K0 8.5, K1 20.0, K≥2 10.1, None 46.8 (n = 59; mean 18.3).
- Per-root process overhead, taken from the ledger.

**Method.** A bootstrap with 2,000 replicates, drawing each design query from its own class. The stress scenario puts every query at its
class's 90th percentile. P9 is a selected sample of 116 queries, and omission/reversal queries may fail, and so cost, more than it.

| phase | X / Y to query | mean CPU-s (X + Y) | 95% bootstrap | stress (p90) | max root (95% / stress) |
|---|---|---|---|---|---|
| `PMIN_FULL_CATALOGUE` | 884 / 993 | 18,893 (6,183 + 12,558) | 17,631–20,242 | 42,128 | 476 / 506 |
| **`PMIN_DEV_MATCHED`** | **2,165 / 1,807** | **40,294 (18,322 + 21,824)** | **38,539–42,150** | **90,809** | **1,066 / 2,171** |
| `PREFIX_COMPLETE` | 819 / 826 | 14,292 (4,632 + 9,532) | 13,282–15,357 | 30,237 | 687 / 1,219 |

**Requested authorization for `PMIN_DEV_MATCHED`** (upper bounds, not targets):

| cap | value | rule |
|---|---|---|
| aggregate worker CPU-s | **64,000** | 1.5 × the 95% bootstrap upper bound |
| CPU-s per root (`RLIMIT_CPU`) | **3,300** | 1.5 × the stress per-root maximum, so no root is censored by its own cap |
| workers | **8** | the machine has 16 physical cores |
| wall-seconds | **13,800** (3.8 h) | expected wall about 1.75 h |
| roots | 197 (176 train + 21 val) | |
| queries | 2,165 X + 1,807 Y | |
| per-query teacher budget | unchanged `bd_2d.QB` | |

**Runner safeguards:**
- **Projection checkpoint.** Once 20 roots have finished, after every further root: projected = spent / expected(finished) ×
  expected(all). If the projection exceeds 64,000, the runner stops launching new roots (never killing a running one) and reports.
  The stress case lies above the cap, so the checkpoint stops the run rather than silently censoring.
- **Unlaunched roots.** Roots not started remain NOT_ATTEMPTED, never 0.

**Runner implementation.** The P9 supervisor is hard-wired to its own output folder, caps and worklist. P-min needs a parameterized
runner that calls `assert_frozen`, `admitted`, `y_query_counted` and `checkpoint`. Writing it is the first step of the collection gate.
It needs no teacher CPU and is tested on stubs before launch.

## 9. Tests and regressions (actual exit codes)

| command | exit | result |
|---|---|---|
| `python3 -m pytest -q tests/test_bxy_p10.py tests/test_bxy_teacher.py tests/test_bxy.py` | 0 | 41 passed (15 + 11 + 15) |
| `python3 -m pytest -q tests/` (full repository suite; `runs/approach_b/bxy_pmin_v1/regression/pytest_full.log`) | 0 | 584 passed, 1 skipped (run before the 15th P10 test, the artifact-preservation test, was added; that test passed in the row above) |
| `python3 run.py replay --run runs/<r>` for `g1_robot`, `g1_hardening`, `g2_interventions`, `g3_repairs`, `g3_5_initial_scene`, `g4a_evidence_audit` | 0 × 6 | `replay_passed: true` × 6 |

**Not run:** any teacher query, any training, any evaluation, and any 3D work.

## 10. Remaining issues

1. **Historical P7 custody.** `bxy_lb.run` wrote test predictions before freeze. The 34 test roots stay historically exposed diagnostics
   and are excluded here.
2. **0114 did not separate certificate from timeout in its order contrasts.** The two reversed orders differ in kind:
   - s212's reverse order failed with `CERTIFIED_INFEASIBLE` (`ORDER_FIRST_ACTION`), a certified order effect;
   - s047's reverse order failed with `UNKNOWN_PLANNER`, which is only a fixed-budget *policy* difference.
   Future reports list the two kinds separately.
3. **Greedy teacher.** X is the historical greedy policy (`best_edge`), not existential feasibility. Every 0 is a budget-policy failure
   unless it is certified, and the certificate/timeout split is kept as metadata.
4. **K≥2 scarcity and no fresh test cohort** (§6). Both need generation gates.
5. **The coupling, travel and selection claims remain untested.** Training, λ_J selection and coupling ablation come only after
   collection, under a later gate.

## 11. Verdict and next gate

**`READY_TO_REQUEST_BUDGET`.**
- The P-min definition, worklist, F1 screen, travel convention, V2 loader, freezing and provenance are implemented, tested and frozen.
- No new labels exist.

**Next gate (only after your approval): BXY-P-MIN-COLLECT.**
- Write and stub-test the parameterized runner.
- Run `assert_frozen`, then collect `PMIN_DEV_MATCHED` within the caps in §8.
- Build the immutable `BXY_SIDECAR_V2_PMIN`, then STOP before any training.

**STOP.**
