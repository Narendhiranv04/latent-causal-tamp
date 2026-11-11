# 0008 — G4A completion report: evidence audit, automatic candidates and a bounded data-readiness study

| Field | Value |
|---|---|
| Report number | 0008 |
| Date | 16 October 2026 |
| Stage | **G4A only** (G4A instruction §1–12). **No bulk dataset generation, no 300/1,000-root expansion, no G4B sampler, no training, no 3D work and no hardware execution.** The automatic proposals are geometric (B1-style), not learned. All execution is kinematic replay, not simulation or hardware. |
| Instruction | `instruction-phase-md/G4A_evidence_audit_and_automatic_candidates.md` (read in full) |
| Normative documents | Methodology v1.5, Guide v1.7 (current, repository root); addendum A1 (new, `docs/addenda/`) |
| Previous turn sync | Report 0007 was committed as `a2727e4563f4fcfd05fd7f492c5628c4e709daef` on `main` and pushed. At the start of this stage the local head, `origin/main` and the remote head were verified equal. |
| Run directory | [`../runs/g4a_evidence_audit/`](../runs/g4a_evidence_audit/). Plan: `python run.py g4a-plan`. Collection: `python run.py g4a-audit` (70.6 min wall, 8 workers). |
| **Readiness decision** | **NOT_READY_TO_SCALE.** One predeclared target is BLOCKED: zero-move witnesses were found on 3 roots against a target of 6. All other targets pass. The main audit also **overran its 4 CPU-hour cap by 0.56 CPU-hours** (§6). |
| Tests | **94 passed** (G0–G3.5: 83, G4A: 11). Mutation checks: 14 G4A mutants, all killed after one test addition. |
| Archives | The 102 archived run files are byte-identical before and after (sha256 lists compared), and reports 0001–0007 are unchanged. All six replays pass: g1_robot 77, g1_hardening 77, g2 2, g3 50, g3.5 20, g4a 257. |

---

## 1. Starting state and administrative items

| Item | Value |
|---|---|
| Branch / commit | `main` @ `a2727e4` (equal to `origin/main`) |
| Working tree at start | (a) new `instruction-phase-md/G4A_evidence_audit_and_automatic_candidates.md`; (b) the root `latent_causal_tamp_specification_v1_4.pdf` and `…implementation_guide_v1_6.pdf` deleted locally (left unstaged at G3.5) |
| `AGENTS.md` / `CLAUDE.md` | re-checked: still absent |
| Robot profile hash | `sha256:2d7986761356f926…3c1ae858`, unchanged. Home q = [π/2, π/2, π/2]; 24 directions × 2 branches = **48 grasp candidates**; full layered 3R body. |
| Config hash | G3.5: `c1854e4e…`. **G4A: `sha256:a9f3f2360e17d9827e24b4e9bb32727569afdf04aa4f87c72ba3cccf50953ae3`**. The change adds `[evidence]`, `[generator]`, `[audit4a]` and two `[target_evaluation]` keys. The tested node and evaluation caps are unchanged. |

**Historical PDFs.**
- The exact tracked bytes were recovered with `git show a2727e4:<file>` into [`../docs/archive/`](../docs/archive/), with a README recording the hashes:
  - v1.4: sha256 `4afcd919…87bf5`, blob `a97c2466…`;
  - v1.6: sha256 `15d1a6fe…7f7606`, blob `033cbcda…`.
- Both git blob hashes equal those committed in `b55063e`.
- The root copies are removed in this commit as a move. v1.5/v1.7 remain in the root as current.
- The README links are updated; historical reports are not edited.

**`run.py` split** (narrow, behaviour-preserving):

| Command | Body moved to | Lines (logical) |
|---|---|---|
| `scene` (G0) | `viz.cmd_scene` (+ `scene_checks`, `load_fixture`) | |
| `check` (G1) | `figures.cmd_check` (+ `traj_extent`) | |
| `intervene` (G2) | `intervention_figures.cmd_intervene` | |
| `solve` (G3) | `assignment_figures.cmd_solve` | |
| `case-analysis` (G3.5) | `case_figures.cmd_case_analysis` | |
| `g4a-plan`, `g4a-audit` | `audit.cmd_g4a_plan`, `audit.cmd_g4a_audit` | |
| shared I/O | `config.write_json`, `config.write_manifest` | |
| **`run.py`** | argparse, dispatch, cross-stage `replay` | **356 → 94** |

**Split verification.**
- A git worktree of `a2727e4` (old dispatcher) and a frozen snapshot of the split tree ran **identical inputs**: scene, check `--no-figures`, intervene, and reduced-fixture solve and case-analysis, plus replay.
- Every output file was identical, except wall-clock seconds in two `metrics.csv` files and the manifest hashes of those same files.
- A test asserts that each subcommand dispatches to its owning module and that archive replays pass.

---

## 2. Certificate audit (instruction §3)

**Independent checker:** [`certificates.py`](../certificates.py). It never trusts a producer boolean. It recomputes:
- the scope: observation hash, action-context hash, assignment signature, target and object identities;
- the declared rules: no pushing, side-grasp support contact, no lift, disc goal orientation "ANY", move-once, no target action before repair completion, and the target not being a repair object;
- the premise itself, from the scene and action.

It shares only trusted primitives: disc distances and the pose-only grasp screens over the full declared (direction, branch) family. The producer (`evaluate.audit_candidate`) emits structured records. Only checker-accepted records become negative evidence.

| Certificate | Premise recomputed by the checker |
|---|---|
| `GOAL_OVERLAP` | For **every** allowed final target placement (each declared goal pose, anywhere within the goal tolerance τ_g = 2 mm), some claimed obstacle's final pose overlaps it. The obstacle's pose uncertainty is the release tolerance (2 mm) if it moves, or the declared state uncertainty (0 m, an exact kinematic state) if it stays. Overlap means clearance < δ − ε = 4.8 mm. Goal regions with alternatives are supported, and any free alternative rejects the certificate. |
| `FIRST_MOVER` | Every selected object, moved first from S0, fails a definite pose-only screen. Either PICK (grasp pose, approach line, closure, for all 48 candidates) or PLACE at its assigned destination. The movers must equal the selected set, the record must cover all 48 grasps, and all rejections must be definite. Connector, start-dependent or budget failures are refused. |
| `TARGET_PICK` (new, added after the pilot) | The active target cannot be grasped **even with every moved object deleted**: its pick screen fails definitely for all 48 grasps among the staying objects. The screen is pose-only and adding obstacles only adds definite collisions, so every realization fails. |
| `STATIC_ENDPOINT_INVALID` | The static factors are recomputed. |
| `ACTION_LOWER_BOUND` | Each claimed goal occupant passes the goal-overlap check with everything else staying. The +1 term additionally needs each occupant's S0 pick to fail definitely. |

**Adversarial suite** (`controls.certificate_suite`; 33 cases; **all as expected**; [`A_certificate_audit.png`](../runs/g4a_evidence_audit/A_certificate_audit.png), `certificate_checks.json`):
- **Accepted:**
  - an exact goal occupant;
  - clearance 4.0 mm (< δ − ε);
  - R4's o00 cannot be picked first;
  - g4a_r00's blocked target grasp;
  - the R4 bound of 2;
  - the R2 bound of 1;
  - every G3.5 certificate and bound, re-audited from the archived records (6 cases).
- **Rejected:**
  - premise removed; stale object ID; stale goal; pushing allowed;
  - a goal region with a free escape pose;
  - clearance 4.9 mm (inside the gray band);
  - a 10 mm goal tolerance that reaches a clear placement;
  - an altered radius;
  - a selected object that *can* go first;
  - one grasp omitted;
  - a start-dependent connector failure;
  - a planner timeout offered as a certificate;
  - an assignment changed after production;
  - a grasp family narrowed to 12 directions;
  - a removed set that differs from the moved set;
  - every obstacle moved away (target then graspable);
  - a graspable target;
  - an overstated bound (3);
  - an unjustified +1 term;
  - a bound under an escape region.
- A test additionally rejects a record that omits a selected mover entirely. This test was added after a mutant survived.

**Conclusion.** No existing certificate was found unsound. The G3.5 goal-overlap certificates, the first-mover certificate and the R4 scoped lower bound of 2 are all independently re-derived. **No erratum is needed.** The R4 bound remains scoped to the declared 48-candidate side-grasp family, move-once, no pushing, and the target not being a repair object.

**Producer fix made in this stage.**
- `goal_blockers` now handles declared goal alternatives: a pose is certified only if **every** allowed pose is blocked.
- It uses the declared state uncertainty for staying obstacles.

For unique goals and zero uncertainty this is identical to G3.5, and the G3.5 action hashes and records are reproduced.

---

## 3. Target completion contract and abort behaviour (§4)

**Addendum** [`docs/addenda/A1_target_end_policy_v1.md`](../docs/addenda/A1_target_end_policy_v1.md):
- Primary success means the goal is reached within τ_g **and** a certified safe retreat ends open-handed and clear.
- The record is re-certified independently from its first waypoint, which equals the achieved state bit-for-bit, through the retreat.
- HOME return is a separately planned and separately certified diagnostic that never erases a witness.

Fields recorded: `goal_achieved`, `safe_retreat_status`, `home_return_status` and `complete_target_status`. The policy is part of the action context. The G3.5 HOME-constrained context keeps its exact hash, and `case-analysis` reproduces the archived G3.5 records.

**Measured** ([`G_target_completion.png`](../runs/g4a_evidence_audit/G_target_completion.png)), over 171 SAFE_RETREAT evaluations (first pass + primary):
- complete: 52 VERIFIED, 84 scoped CERTIFIED_INFEASIBLE, 35 UNRESOLVED;
- HOME diagnostic on the 52 complete witnesses: **48 VERIFIED, 4 UNRESOLVED**. None of those four witnesses was erased.

**Old vs new scope** on bit-identical cloned states (seed-panel states): HOME_REQUIRED agreed with SAFE_RETREAT in all 9 available cases. Tests:
- a record truncated before its retreat is not counted;
- a forced HOME failure leaves the witness intact.

**Executor / REOBSERVE.**
- Each committed relocation record must start at the observed state and certify in the observed scene.
- After each move, the observation is validated against the *expected* state: the committed robot state and history, the moved object at its committed pose, and everything else where it actually is.
- The checks are: identities; attachment free; gripper gap; joints; and poses (moved objects within 2 mm, unmoved objects within 0 m).
- **A bug was found by the within-tolerance test and fixed.** The expected state used to reset earlier admitted deviations back to commanded poses; it now carries them forward.

**Fault injection** ([`F_abort_injection.png`](../runs/g4a_evidence_audit/F_abort_injection.png), `fault_injection.json`; **FAULT-INJECTION TEST, not physical robustness**). Two-move R4 layout; the deviation is injected after relocation 1:

| Injection | Outcome | Relocations executed | Target calls | Proposals / commits |
|---|---|---|---|---|
| o01 pose +6 mm (3× tolerance) | ABORTED ("deviates 6.00 mm > 2.00 mm") | 1 of 2 | 0 | 1 / 1 |
| o01 pose +1 mm (0.5×) | SUCCESS: relocation 2 re-certified in the perturbed scene; target planned from the perturbed state | 2 of 2 | 1 | 1 / 1 |
| gripper gap 35 mm vs 70 mm | ABORTED | 1 | 0 | 1 / 1 |
| attachment still `attached` | ABORTED | 1 | 0 | 1 / 1 |
| object identity o01 → o99 | ABORTED | 1 | 0 | 1 / 1 |

The initial observation and proposal hashes are fixed in every case.

---

## 4. Automatic candidate generator (§5)

**`B1_GEOMETRIC_V1`** (`proposals.generate_candidates`) is a geometric control, not learned. Its input is the allowlisted learner fields only: the initial scene geometry and poses, robot q/g, legal spots, the target and goal. It reads no reference path, label, planner outcome, pick certificate, root or family name, or construction history.

**Rule (frozen before any outcome):**
1. Order obstacles by (distance to the target–goal segment or to the goal, x, y). Those within 0.12 m are task-proximal; if none are, the nearest one is used.
2. Free spots are legal cells that are not initially occupied and are neither the target's nor the goal's cell. Each obstacle prefers spots outside the corridor, then spots near itself, with ties broken by (x, y).
3. The raw pool contains:
   - all-stay;
   - singles: every obstacle × its 2 preferred spots;
   - pairs, plus one occupied-destination chain (a → b's spot, b moves on), among the first three proximal obstacles;
   - a proximal triple;
   - seeded broad moves: 4 singles and 1 triple of any obstacle, from a geometry-only seed.
4. The pool is screened statically on the whole assignment, so a joint move into a cell vacated by its owner is valid. It is deduplicated physically, then filled by a fixed round-robin over [single, pair/chain, triple, broad] up to 11, plus all-stay = 12.
5. **Primary ranking** (frozen): the G3.5 rule. The geometric task score is 0 if the endpoints leave the goal provably occupied, otherwise 1; candidates are then ordered by moved count, then by generator order.

**Measured counts:**
- raw proposals per query: 14–29 (cap 120);
- static-valid after dedup: 11 + all-stay on every query;
- 2 duplicates and 0 static-invalid in the raw pool;
- categories over 220 non-stay candidates: single 81, broad 67, pair 40, triple 32;
- every query's candidate set includes objects other than the goal occupant.

**Tests:**
- poisoning or deleting `oracle_only` leaves the candidates identical;
- changing the goal changes them;
- relabelling object IDs maps to the same physical assignments and the same geometry seed;
- mutants that order by ID or seed by ID are killed.

**Limitations:**
- Destinations prefer spots near the object, so the generator rarely proposes far, "clearing" moves.
- Pair and triple candidates use only the first three proximal objects.
- It never sees access or IK structure, by design. g4a_r00 shows the cost: all-stay was committed and the target grasp was blocked.

---

## 5. Frozen audit plan and roots (§6)

[`g4a_plan.json`](../runs/g4a_evidence_audit/g4a_plan.json) has plan hash `sha256:0537694b9c1d649b9dc857192050c1a97ef0cae1047f514edf274b04e9441c07`.
- It was written before any target outcome.
- The audit re-verifies the hash, the config hash, and a deterministic regeneration of every candidate list and ranking before collecting.
- It freezes the roots, actions, candidates, primary rankings, seed and order panels (stable-hash rules), budgets and targets.

**Roots.** 20 DEVELOPMENT_ONLY roots, 4 per stratum, with 4–8 obstacles and one query each.
- 26 construction attempts, all in [`root_ledger.json`](../runs/g4a_evidence_audit/root_ledger.json): 4 rejected for "more than two free spots near the goal occupant" and 2 for "target and goal closer than 2 cells".
- **Construction correction before the plan was frozen:** the first construction draft used rejection sampling for NUISANCE_CONTROL and yielded only 19 roots in 100 attempts (68 rejections). NUISANCE layouts now sample clutter only from cells at least 2 cells from the transport segment. This happened before any planning or outcome.

| Stratum | Roots |
|---|---|
| UNOCCUPIED_GOAL | g4a_r00, r05, r10, r15 |
| OCCUPIED_GOAL | r01, r06, r11, r16 |
| ACCESS_DEPENDENCY | r02, r07, r12, r17 |
| COMPETING_DESTINATIONS | r03, r08, r13, r18 |
| NUISANCE_CONTROL | r04, r09, r14, r19 |

**Pilot** (first four roots, one each from S1–S4; superseded):
- 1.07 CPU-hours, with no correctness fault in schemas, boundaries or certificates.
- It showed (a) the cost risk (g4a_r03 alone used 57 CPU-min), and (b) assignments left UNKNOWN only because the target's own grasp was blocked.
- **Decision recorded before the main collection:**
  - keep the tested per-query node/evaluation caps frozen (`max_nodes` 4000, skill failures 4 for the target and 2 for relocation, orders 6, relocation plans 40);
  - let the predeclared CPU cap govern;
  - add the sound `TARGET_PICK` certificate with checker and tests;
  - rerun all 20 roots (the pilot evidence is not mixed in).

---

## 6. Costs and the cap overrun

| Budget | Declared | Used |
|---|---|---|
| Main audit CPU | 4.0 CPU-h | **4.56 CPU-h (16,415 s): cap overrun of 0.56 CPU-h (14%)** |
| Diagnostic CPU | 2.0 CPU-h | 0.26 CPU-h (952 s) |
| Diagnostic target invocations | ≤ 120 | 66 (seed panel 9 × 6, order panel 12) |
| Workers | ≤ 8 | 8 |
| Wall-time safety cap hits | — | 0 (no `wall_clock_dependent` result) |

**Why the overrun happened.** The cap is checked when a root completes. The 20th root to complete pushed the total past 4 CPU-hours, so no root was cut, but the evidence of one root lies beyond the cap. Completion order was not recorded, so that root is one of g4a_r03 (3,743 s), g4a_r13 (3,509 s) or g4a_r07 (2,911 s); each alone exceeds the 2,015 s overrun.

**Sensitivity.** Excluding any one of those three roots leaves every coverage target unchanged, except that roots_complete becomes 19. The decision is NOT_READY either way.

**CPU distribution per root.** Median 282 s, mean 821 s, min 23 s, max 3,743 s. By stratum: COMPETING 7,310 s, ACCESS 3,927 s, NUISANCE 3,201 s, OCCUPIED 1,002 s, UNOCCUPIED 975 s. Long target evaluations (up to 657 s, ending UNRESOLVED) and blocked relocation searches dominate.

---

## 7. First-pass and diagnostic-enriched labels (§7)

The full 240-row table is in [`candidate_labels.json`](../runs/g4a_evidence_audit/candidate_labels.json): 20 queries × 12 static-valid assignments.

| | First pass | Diagnostic-enriched |
|---|---|---|
| Positive (complete witness) | 44 | 44 |
| Negative (checker-accepted certificate) | 86 | 86 |
| Unknown | 110 | 110 |
| Unknown fraction (static-valid) | **0.458** | 0.458 |
| Contradictions | 0 | 0 |

Diagnostics added **no** positives: the seed and order panels found no new witnesses.

**Negative sources** (accepted records):

| Source | Records |
|---|---|
| GOAL_OVERLAP | 72 |
| TARGET_PICK | 13 |
| FIRST_MOVER | 4 |
| Producer certificates rejected by the checker | 0 |

**Unknown reasons:**

| Reason | Assignments |
|---|---|
| Relocation orders exhausted (finite) | 67 |
| Target UNRESOLVED (planner budget) | 29 |
| Target scoped-infeasible without an assignment certificate (connectors certified blocked from a start, NO_PLACE after moves, etc.) | 14 |

The same budget- or start-dependent rejections stay unknown in G4A, and finite exhaustion is never labelled negative.

**Label masks** (`data.label_masks`):
- Unknowns are excluded from the binary loss and from the joint-pool denominator.
- A pool needs both a positive and a negative to count.
- A contradiction halts labelling.

These are tested; no model was built.

---

## 8. Seed and order sensitivity (§8)

**Target seed panel** ([`D_seed_variance.png`](../runs/g4a_evidence_audit/D_seed_variance.png), `seed_panel.json`).
- 12 cases were selected by the frozen stable-hash rule: per stratum, one all-stay and one nonempty candidate, then fill.
- 9 cases ran. **3 entries are missing**: g4a_r08 {o00→3, o01→11}, g4a_r09 {o00→0} and g4a_r13 {o01→4} had no first-pass relocation witness to define an achieved start state. They stay visible as NOT_RUN and were not replaced.
- Each of the 9 used a bit-identical state, identical budgets and five predetermined keys.
- **No case changed result across the five seeds:**
  - 2 cases 5/5 VERIFIED (g4a_r05 all-stay; g4a_r10 {o01→15});
  - 1 case 5/5 UNRESOLVED at the 4,000-node cap (g4a_r05 {o00→48}, about 32 s each);
  - 6 cases 5/5 scoped CERTIFIED_INFEASIBLE.
- These are finite-planner observations on fixed states, not feasibility probabilities.

**Order panel** ([`E_order_end_states.png`](../runs/g4a_evidence_audit/E_order_end_states.png), `order_panel.json`).
- 6 multi-object assignments, up to 3 executable orders each, 2 seeds per end state.
- Executable orders found:
  - g4a_r17: 1 of 2;
  - g4a_r06: 3 of 5 tried, with two **different end joint states**, [1.65, −1.93, −0.51] and [1.92, −1.99, −0.98];
  - g4a_r02: 2 of 2;
  - g4a_r13, g4a_r15, g4a_r05: 0.
- **Additional assignment positives beyond the first executable order: 0** (12 target calls, 730 CPU-s for the whole order panel; the seed panel used 222 CPU-s). Different orders change both the final object poses (within tolerance) and the robot state; no effect is attributed to joint configuration alone.

**Interpretation.** In this sample, more seeds or more orders are not a productive way to reduce unknowns.

---

## 9. Primary episodes (automatic proposals; one-shot)

[`primary_episodes.json`](../runs/g4a_evidence_audit/primary_episodes.json), [`H_primary_call_trace.png`](../runs/g4a_evidence_audit/H_primary_call_trace.png).
- Boundary check = True for 20/20 episodes: 0 target calls before commit or between relocations, 1 target call total, nothing after.

| Outcome | Queries |
|---|---|
| SUCCESS | 8 |
| TARGET_UNRESOLVED | 6 |
| TARGET_CERTIFIED_INFEASIBLE (scoped) | 4 |
| NO_REPAIR_WITNESS_WITHIN_BUDGET | 2 |
| **Operational complete success** | **8/20 = 0.40** (unknowns stay in the denominator) |

**The primary never adopts teacher results.** In g4a_r11 the primary committed its own first verified repair (o00→59) and ended TARGET_UNRESOLVED, while the offline teacher found 4 positive alternatives. The primary did not switch. A test reproduces this with stubs.

**Repair GIFs** from two distinct new roots: [`repair_g4a_r01.gif`](../runs/g4a_evidence_audit/repair_g4a_r01.gif) and [`repair_g4a_r02.gif`](../runs/g4a_evidence_audit/repair_g4a_r02.gif). Each shows the blocked scene, the committed relocation, then the newly planned target through the safe retreat.

---

## 10. Coverage and readiness (§9; [`C_label_coverage.png`](../runs/g4a_evidence_audit/C_label_coverage.png))

| Criterion | Target | First pass | Status |
|---|---|---|---|
| Independent valid roots audited | 20 (or explicit BLOCKED) | 20 completed, 26 attempts in the ledger (one root completed beyond the CPU cap, §6) | **PASS** (with the cap caveat) |
| Zero-move complete witnesses | ≥ 6 roots | **3** (r05, r10, r19) | **BLOCKED** |
| Nonempty complete witnesses | ≥ 8 roots | 11 | PASS |
| Alternative sufficient assignments | ≥ 4 roots | 8 | PASS |
| Static-valid certified goal negatives | ≥ 3 roots | 12 | PASS |
| Static-valid access negatives beyond goal overlap | ≥ 3 roots | 4 (FIRST_MOVER 3: r15, r17, r18; TARGET_PICK 2: r00, r17). The target is met by FIRST_MOVER alone. | PASS |
| Distinct signatures per multi-alternative query | ≥ 2 | every multi-alternative query has ≥ 2 physically distinct assignments | PASS |
| First-pass unknown fraction (static-valid) | ≤ 50% | 45.8% (enriched 45.8%, extra cost 0.26 CPU-h) | PASS |
| Semantic/protocol failures | 0 | 0: no false certificate, contradiction, leakage, target-feedback selection or archive change | PASS |

**Cohorts** (by the first-pass all-stay label):

| Cohort | Roots | Roots with a nonempty witness |
|---|---|---|
| Certified initially infeasible | 13 (12 goal overlap + r00 target pick) | 7 |
| Witnessed initially feasible | 3 | 3 (those repairs were unnecessary) |
| Initially unresolved | 4 (r04, r09, r14, r15) | 1 |

**Why the zero-move target is blocked.** The predeclared stratum mix put 12 of 20 roots in occupied-goal strata, where all-stay is certified infeasible by construction. Of the remaining 8 (UNOCCUPIED and NUISANCE):
- 3 have zero-move witnesses;
- 1 is certified infeasible (r00, target grasp blocked);
- 4 are unresolved: r04, r14 and r15 hit the target planner budget, and r09 had all connectors certified blocked from home, which is start-dependent and so remains unknown.

The seed panel shows that seed variation does not resolve these.

**Negative supervision remains limited to goal occupancy and finite-grasp access.** Of the 86 negatives, 72 are goal overlap, 13 target grasp blocked by staying objects, and 4 first-mover grasp access. There are **no path-level negatives**: finite search exhaustion never yields one. Passing the other targets does not establish learning of free-space connectivity, and it does not prove the absence of alternate paths.

**Invalid-endpoint control pool** (kept separate; [`invalid_endpoint_controls.json`](../runs/g4a_evidence_audit/invalid_endpoint_controls.json); static only, added after collection):
- duplicate destination, onto the resting target and off the support: INVALID with the checker's acceptance (5/5 each);
- "clearance exactly δ": UNRESOLVED (gray band) in 4 roots, which the checker correctly refuses as a negative; INVALID in g4a_r00, where the shifted pose also overlaps another object (−21 mm).

---

## 11. Recommendation

Do not scale. Before a re-run of the G4A gate, I propose **one concrete evaluator improvement**: an offline-teacher target schedule with a larger predeclared pick/place-pair and RRT allowance, used only in the teacher namespace. Three of the 4 initially-unresolved zero-move queries (r04, r14, r15) end on the target planner budget, as do 29 unknowns in total. The fourth (r09) has its connectors certified blocked from home. Five seeds do not change those outcomes. A larger pair and RRT budget is the measured remaining lever.

This needs approval, because it is a budget change, and it costs CPU: unknown target evaluations already reach 657 s. Its effect should be measured on these same 20 frozen roots, as a separately labelled teacher-schedule variant, before any G4B work.

A secondary observation for the next plan: with 3 of 5 strata occupying the goal by construction, the zero-move target needs either more unoccupied-goal roots or a stratum-weighted target. The strata must be fixed before outcomes, not tuned afterwards.

**G4B and later stages are not started.**

---

## 12. Tests, mutation checks and regression

`python -m pytest tests -q`: **94 passed**. `tests/test_g4a.py` (11 tests) covers §11 items 1–11:
1. the checker rejects invalid premises and stale scope;
2. a tolerance-aware occupancy proof cannot certify a region with an alternative;
3. the first-mover proof covers every mover and every grasp, with no start-dependent shortcuts;
4. success requires a safe retreat, and a HOME failure never erases a witness;
5. an injected deviation aborts with no forbidden follow-up;
6. generator allowlist and goal sensitivity;
7. permutation mapping;
8. masks, aggregation and contradiction handling;
9. the seed panel holds the state and budget fixed;
10. the primary never adopts the teacher's candidate;
11. the run.py split preserves the CLI and archive replay, including G3.5's key-filling.

**Mutation checks** (scratch copies). 14 G4A mutants:
- checker trusts the blocker list;
- checker ignores stale hashes;
- first-mover covers only one mover (**survived in round 1** → test added → killed);
- partial grasp record accepted;
- success without retreat;
- HOME failure erases the witness;
- reobservation ignores poses;
- abort still evaluates the target;
- contradiction resolved as positive;
- unknowns enter the joint pool;
- generator orders by ID;
- generator seeds by ID;
- seed panel varies the state;
- target-pick checker keeps the moved objects.

All are now killed.

**Regression:**
- The G3.5 case-analysis rerun matches the archived records, except a new empty `reasons` list on REOBSERVE events. All outcomes, labels, bounds and certificates are identical.
- **A regression was found and fixed:** the replay adapter filled only missing config *sections*, so the G3.5 archive (which predates the two new `[target_evaluation]` keys) failed strict validation. It now also fills missing keys and records them (`config_keys_filled_from_current`). A test covers this.
- All six replays pass.

---

## 13. Files changed (lines total / logical)

| File | Change | Lines |
|---|---|---|
| `proposals.py` | **new**: G3.5 endpoint code moved from `solve.py`; region-aware goal producer; frozen ranking; `B1_GEOMETRIC_V1` | 215 / 149 |
| `certificates.py` | **new**: independent checker | 180 / 134 |
| `roots.py` | **new**: strata, ledger, frozen plan, panel rules | 178 / 143 |
| `audit.py` | **new**: plan check, collection, panels, G4A commands | 254 / 205 |
| `coverage.py` | **new**: labels, coverage, cohorts, readiness | 114 / 94 |
| `controls.py` | **new**: adversarial suite, G3.5 re-audit, fault injection, invalid pool | 242 / 199 |
| `audit_figures.py` | **new**: figures A–H, GIFs, clean observations | 267 / 239 |
| `tests/test_g4a.py` | **new**: 11 tests | 218 / 177 |
| `evaluate.py` | SAFE_RETREAT evaluation, HOME diagnostic, observation validation, `advance`, executor hook, structured checked certificates, `TARGET_PICK` producer | 291 / 221 |
| `data.py` | end-policy action context (G3.5 hash preserved); `aggregate`, `label_masks` | 122 / 78 |
| `verify.py` | `motion_valid`, `executable_orders` | 385 / 280 |
| `config.py`, `config.toml` | new sections and validation; `write_json`, `write_manifest` | 270 / 212 |
| `solve.py` | G3.5 section moved out (frozen A0 only) | 231 / 155 |
| `run.py` | **dispatcher split**; replay key-filling fix | **119 / 94** |
| `viz.py`, `figures.py`, `intervention_figures.py`, `assignment_figures.py`, `case_figures.py` | received their stage commands; small GIF-title fix (goal free) | 381/288, 264/218, 258/210, 287/241, 286/245 |
| `cases.py`, `tests/test_protocol.py` | imports retargeted to `proposals` | — |
| `docs/archive/` (2 PDFs + README), `docs/addenda/A1_target_end_policy_v1.md` | **new** | — |
| `README.md` | archive links, addendum, new modules and commands, G4A status | — |
| `runs/g4a_evidence_audit/` | **new** run (flat) | — |

**Size notes.**
- `viz.py` is at 288 logical lines; it received the G0 command body in the split.
- `verify.py` is at 280.
- Both are at the edge of the guidance and below the ~300 review point.

**Figures post-processing.** A and E were regenerated after collection from their own saved records, for layout only: status words and colours in A, clipped labels, and the arm drawn for incomplete orders in E. The manifest records this (`post_collection_regenerated`). G's two truncated labels are left as rendered.

---

## 14. Data and visual deliverables (all in [`../runs/g4a_evidence_audit/`](../runs/g4a_evidence_audit/))

| File | Content |
|---|---|
| `g4a_plan.json`, `root_ledger.json` | frozen plan and every construction attempt |
| `candidate_labels.json` | 240 assignment records with first-pass and enriched labels |
| `certificate_checks.json` | suite plus every produced certificate with the checker verdict |
| `primary_episodes.json` | event traces, commits, target fields, CPU |
| `seed_panel.json`, `order_panel.json`, `fault_injection.json`, `invalid_endpoint_controls.json` | panels and controls |
| `result.json` | coverage, readiness, costs, replay tasks |
| `metrics.csv`, `config.json`, `manifest.json`, `scenes.json`, `arrays.npz` | per-query metrics, config, hashes, 257 replayable trajectories |
| Figures A–H | `A_certificate_audit.png`, `B_automatic_candidates.png` (candidates before evaluation; teacher statuses separate), `C_label_coverage.png`, `D_seed_variance.png`, `E_order_end_states.png`, `F_abort_injection.png`, `G_target_completion.png`, `H_primary_call_trace.png` |
| GIFs and observations | `repair_g4a_r01.gif`, `repair_g4a_r02.gif`; `obs_g4a_r00 … r19.png` (clean learner RGB) |

---

## Repository synchronization

This turn commits:
- the source, tests, config, README, addendum, the archived PDFs (moved from the root) and the instruction file;
- `runs/g4a_evidence_audit/`;
- this report.

Reports 0001–0007 and all earlier run directories are unchanged. The commit hash is given in chat and will be recorded as "Previous turn sync" in the next report.

**Stopping after G4A for review.**
