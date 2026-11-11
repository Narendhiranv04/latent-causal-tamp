# 0009 — G4A follow-up: reporting reconciliation and bounded offline teacher-budget diagnostic

| Field | Value |
|---|---|
| Report number | 0009 (new; 0001–0008 unchanged) |
| Date | 16 October 2026 |
| Stage | **G4A follow-up only**: reporting reconciliation plus a bounded offline teacher diagnostic on g4a_r04, g4a_r14 and g4a_r15 (all-stay). No G4B, learned proposal search, training, bulk generation, root expansion, 3D or hardware work. Execution is 2D kinematic. |
| Instruction | `instruction-phase-md/G4A_followup_reporting_and_teacher_budget_diagnostic.md` (read in full) |
| Normative documents | Methodology v1.5, Guide v1.7, addendum A1, the G4A instruction, reports 0007/0008, and the G4A plan, config, labels, episodes and diagnostic records |
| Previous turn sync | Report 0008 was committed as `44679ce67f2ffdf88afdcf3c58e09b48c6dbd76f` on `main`. At the start of this work the branch, HEAD and `origin/main` were verified identical, and the only untracked item was this instruction file. |
| Run directory | [`../runs/g4a_teacher_budget_diagnostic/`](../runs/g4a_teacher_budget_diagnostic/). `python run.py teacher-plan` then `teacher-run` (29.1 min wall). |
| **Decision** | **No new zero-move witness.** Zero-move coverage stays **3 roots** (r05, r10, r19), both first-pass and diagnostic-enriched. The original G4A audit remains **NOT_READY_TO_SCALE**; nothing in it is overwritten. |
| Compute | 6 evaluations started (cap 6). **1,742.7 CPU-s** (0.48 CPU-h; cap 7,200 CPU-s), plus 2.2 CPU-s for a post-hoc pose-only screen. Maximum per evaluation 870.2 CPU-s (cap 900; trigger 870; measured overshoot 0.0 s). Wall 1,743.7 s (cap 3 h). One worker. |
| Tests / replays | **101 passed** (94 existing + 7 new). All six archived runs replay (77/77/2/50/20/257 trajectories). All 147 prior run files and reports 0001–0008 are byte-identical (sha256 lists compared). |

---

## 1. Starting state

| Item | Value |
|---|---|
| Branch / HEAD / remote | `main` / `44679ce` / `origin` = github.com/Narendhiranv04/latent-causal-tamp (equal) |
| `AGENTS.md`, `CLAUDE.md` | absent |
| Deployment config hash | `sha256:a9f3f2360e17d9827e24b4e9bb32727569afdf04aa4f87c72ba3cccf50953ae3`, unchanged by this work |
| Robot profile hash | `sha256:2d7986761356f926…3c1ae858`, unchanged |
| G4A plan hash | `sha256:0537694b9c1d649b9dc857192050c1a97ef0cae1047f514edf274b04e9441c07` (archive intact; re-verified by a test) |
| Diagnostic plan hash | `sha256:5edcb81595b5be9da524a8a1f6add3b047dac595c0c43e8f71cab255678fcb36` (frozen before any new outcome) |
| Plan source binding | HEAD `44679ce` + uncommitted diff `sha256:0091ab8bcca31794dd0956dbb382f7c0913378539fac00d07e71bf3a54d75046` (untracked: `teacher.py`, `teacher_figures.py`, `tests/test_teacher.py`) |

---

## 2. Reconciliation of report 0008 against saved records

All figures below are recomputed from `runs/g4a_evidence_audit/{candidate_labels,primary_episodes,seed_panel,result}.json`. The full record is [`reporting_reconciliation.json`](../runs/g4a_teacher_budget_diagnostic/reporting_reconciliation.json) and the figure is [`A_reporting_reconciliation.png`](../runs/g4a_teacher_budget_diagnostic/A_reporting_reconciliation.png).

### 2.1 Certificate records vs. unique negative assignments

0008 §7 reported 72 GOAL_OVERLAP, 13 TARGET_PICK and 4 FIRST_MOVER (89 records) alongside 86 negatives. Keyed by (root, query, physical signature):

| Quantity | Value |
|---|---|
| Accepted certificate records | 89; rejected 0 |
| Duplicate records (same assignment, same kind) | **0** |
| Unique negative assignments | 86 (unique per kind: GOAL_OVERLAP 72, TARGET_PICK 13, FIRST_MOVER 4) |
| GOAL_OVERLAP only | 70 |
| TARGET_PICK only | 10 |
| FIRST_MOVER only | 3 |
| GOAL_OVERLAP + TARGET_PICK | **2** |
| FIRST_MOVER + TARGET_PICK | **1** |
| Union | 70 + 10 + 3 + 2 + 1 = **86** = the negative count |
| Negatives without an accepted, scope-matching certificate | 0 |
| Accepted certificates on non-negative assignments; contradictions | 0; 0 |

**Clarification of 0008.** The 89 − 86 gap is exactly three assignments that each carry **two distinct** checker-accepted certificates. It is not duplicate records.

### 2.2 Primary target-call counts (from event traces)

| Quantity | Value |
|---|---|
| Episodes | 20 |
| Completed committed repairs, each with exactly **1** primary target evaluation | **18** (8 of them all-stay commitments) |
| No-repair-witness episodes, each with **0** target evaluations | **2** (g4a_r08, g4a_r13) |
| Aborted episodes | 0 |
| Target calls before commitment / between relocations | 0 / 0 |
| HOME diagnostics inside primary evaluations | 8 (only after a complete witness); 10 NOT_RUN; 2 none (no target call) |
| Invariant "at most one primary target evaluation; none before commit, between moves, after abort or without a repair" | **holds** |

**Teacher-call scope.** 0008's "171 target evaluations (first pass + primary)" came from in-memory records at collection time. The saved `candidate_labels.json` does not keep per-order target records, so the count of 153 first-pass teacher calls is **not independently re-auditable** from the JSON. The diagnostic panels (66 calls) are fully auditable from `seed_panel.json` and `order_panel.json`.

### 2.3 CPU-cap statement

**Retained:** 4.56 CPU-hours against the 4.0 CPU-hour cap (a 14% overrun).

**Corrected wording.**
- The audit loop checks the cap only when a root completes, and terminates if the cap is exceeded. The record shows 20 completed roots plus `stopped = MAIN_CPU_CAP`, so the threshold was crossed at the 20th completion event; that much follows from code and record.
- 0008's phrase "the evidence of one root lies beyond the cap" mis-describes concurrent execution. Roots ran 8 at a time, so the excess is an aggregate overrun, not the work of one identifiable root executed after the cap.
- Excluding r03, r07 or r13 is a **sensitivity calculation**, not a reconstruction of a cap-compliant run.
- Without scheduling or completion-order records, no claim is possible about which root crossed the cap or what work was in flight.

### 2.4 Seed and order claims

- **Seed panel.** It keeps all 12 entries. Nine ran, and 3 are NOT_RUN: g4a_r08 {o00→3, o01→11}, g4a_r09 {o00→0} and g4a_r13 {o01→4} had no achieved start state. Of the nine, only **one** was target-budget UNRESOLVED (g4a_r05 {o00→48}).
- **Correction.** 0008 §10–11 stated that "five seeds do not change those outcomes" for the unresolved zero-move roots. **That is unsupported:** r04, r14 and r15 were not in the seed panel. The panel's no-change result holds only for its own nine cases.
- The order panel's zero new witnesses likewise hold only for its six sampled assignments.

### 2.5 Unknown-cause attribution (new finding from the diagnostic)

0008 reported 110 unknowns: 67 relocation-search exhaustion, 29 target UNRESOLVED (PLANNER_BUDGET) and 14 other. The target-budget share is therefore **26.4%, not "most"**, and 0008 §11's "Most remaining unknowns end on that budget" is withdrawn. The diagnostic also shows the PLANNER_BUDGET reason string is not reliable evidence of a binding budget (§5).

---

## 3. Diagnostic design (frozen plan; [`plan.json`](../runs/g4a_teacher_budget_diagnostic/plan.json))

**Cases.**
- Exactly g4a_r04, g4a_r14 and g4a_r15, each with the original all-stay assignment.
- Their premise was verified in the archive: first-pass all-stay UNRESOLVED with reason `TARGET_UNRESOLVED:PLANNER_BUDGET`.
- The plan records the exact scene, target, goal, robot q/g/attachment, action-context and observation hashes, and the G4A config and robot-profile hashes.
- B0 references:
  - the first-pass key `<root>/audit/0/target`, whose per-query records were *not archived*;
  - the primary key `<root>/primary/target`: r04 UNRESOLVED after 536.6 s; r14 after 0.22 s; r15 after 0.26 s.

**Fields traced to code before choosing the schedule:**

| Field | What it limits (code path) |
|---|---|
| `planner2d.max_nodes` | RRT-Connect node cap per connector query (`planner._rrt_connect`) |
| `planner2d.max_wall_seconds` | per-query wall safety cap (scaled with the node allowance so it does not pre-empt it) |
| `skill2d.max_plan_failures` | the target skill stops after this many UNRESOLVED RRT connector results while enumerating pick × place pairs: a **failure-based early stop**, not a pair cap |
| `skill2d.max_direct_pairs` | cap on pairs tried in the cheap direct-connector phase |
| enumeration | all passing picks × all passing places from the unchanged 48-grasp family (finite; no separate cap) |

**Schedule `TEACHER_BUDGET_V1`** (a combined schedule, so it cannot isolate which allowance matters):

| Tier | max_nodes | wall/query | max_plan_failures | max_direct_pairs | config hash |
|---|---|---|---|---|---|
| B0 (archived) | 4,000 | 300 s | 4 | 64 | `a9f3f236…` |
| B1 | 8,000 | 600 s | 8 | 128 | `61f6c0f9…` |
| B2 | 16,000 | 1,200 s | 16 | 256 | `f1e011f0…` |

**Unchanged:** grasp family and order (48), geometry, collision checks, margins, tolerances, SAFE_RETREAT policy, candidate generation and ranking, primary episodes, and the seed. The archived key is reused, so `call_seed(41, key)` is the same; each tier starts from the identical initial state with no warm start.

**Execution.**
- Order: B1 for r04, r14, r15, then B2 for those still unknown.
- Each evaluation runs in a fresh single-threaded process: OMP, OpenBLAS, MKL and NumExpr are set to 1 thread. G4A's pool workers used default thread settings; this difference is recorded.
- **In-flight guard:** a psutil process-tree CPU sample every 0.25 s. On reaching 870 CPU-s (900 minus a 30 s margin) or the remaining aggregate budget, the guard kills the whole process group.
- Final CPU = max(reaped-tree rusage, last in-flight sample). Each evaluation's limit is min(900, aggregate remaining).
- Only a completed, independently re-checked SAFE_RETREAT witness is positive. Censoring leaves the evidence UNKNOWN.

---

## 4. Results ([`teacher_budget_results.json`](../runs/g4a_teacher_budget_diagnostic/teacher_budget_results.json), [`event_trace.json`](../runs/g4a_teacher_budget_diagnostic/event_trace.json), [`B_budget_panel.png`](../runs/g4a_teacher_budget_diagnostic/B_budget_panel.png))

| Root | B0 (archived) | B1 (2×) | B2 (4×) |
|---|---|---|---|
| g4a_r04 | UNRESOLVED (PLANNER_BUDGET) | **CPU_CENSORED** at 870.18 CPU-s (trigger 870.0), active phase `carry4.4`. UNKNOWN; no record kept. | **CPU_CENSORED** at 870.10 CPU-s, active phase `carry4.1`. UNKNOWN. |
| g4a_r14 | UNRESOLVED (PLANNER_BUDGET) | COMPLETED in 0.56 CPU-s: UNRESOLVED "PLANNER_BUDGET". 9 picks / 3 places pass; 9 connector queries, **all certified COLLISION by the link-0 sweep from HOME** (0 RRT nodes). | COMPLETED 0.58 CPU-s, identical |
| g4a_r15 | UNRESOLVED (PLANNER_BUDGET) | COMPLETED 0.61 CPU-s: UNRESOLVED "PLANNER_BUDGET". 9 picks / 5 places; 9 connector queries, **all certified link-0-sweep COLLISION** | COMPLETED 0.63 CPU-s, identical |

**New complete witnesses: none.** CPU per new witness is not applicable (zero denominator), and no GIF was produced because nothing succeeded. [`C_scene_evidence.png`](../runs/g4a_teacher_budget_diagnostic/C_scene_evidence.png) shows each initial scene with only its recorded diagnostics. No path is drawn, and "UNKNOWN (not an impossibility proof)" is stated on every panel.

**Interpretation under the instruction's decision rules:**
- **r14, r15: full deterministic allowances ran to completion at B1 and B2 with identical results.** This bounded schedule did not help these cases, and the records show why. The skill never used its failure allowance: zero UNRESOLVED connector results, because every tried pregrasp connector was certified blocked by the link-0 sweep. It never reached RRT or carry.

  The UNRESOLVED status comes from the skill's final branch. When enumeration ends without reaching `max_plan_failures` but some screen rejections are uncertified, the skill cannot claim ALL_CONNECTORS_CERTIFIED_BLOCKED, so it returns its **default** reason `"PLANNER_BUDGET"`. A post-hoc pose-only screen ([`posthoc_pose_screens.json`](../runs/g4a_teacher_budget_diagnostic/posthoc_pose_screens.json), 2.2 CPU-s, no planning) finds the uncertified rejections:
  - r14: 4 GRASP_POSE rejections in the numerical gray band;
  - r15: 1 GRASP_POSE rejection in the gray band.

  Even if all were definite, a link-0 sweep blockage from HOME is start-dependent and so would not be an assignment-wide negative. These cases stay UNKNOWN; **no budget increase can resolve them**.
- **r04: censored at both tiers** (in carry RRT queries). The diagnostic is **incomplete** for r04. Its outcome is not attributable to the B1/B2 deterministic allowances being exhausted, and it says nothing about whether those allowances would have produced a witness.

**Coverage on the same 20 roots.** Zero-move roots: original first pass 3 → diagnostic-enriched 3. Selectively re-evaluating three all-stay cases does **not** yield a new whole-dataset unknown fraction or operational success rate. Those stay 45.8% and 8/20 as recorded in G4A.

---

## 5. Defect found (reported, not silently fixed)

**`skill.plan_skill` reason-code defect.** The SkillResult is initialised as `(UNRESOLVED, "PLANNER_BUDGET")` and returned unchanged in two different situations:
- (a) the failure allowance was reached, which is a genuine budget end;
- (b) enumeration completed with `failures < max_plan_failures` but with uncertified pick or place rejections, which is not a budget end.

**Affected scope.**
- Only the **cause label** of UNRESOLVED skill results, in G3.5, G4A and any reason-based histogram.
- No evidence status is wrong. UNRESOLVED stays UNRESOLVED in both cases, no certificate depends on the reason, and no positive or negative label changes.
- **Directly affected:** 0008's "29 target-budget unknowns" and "target planner budget" attributions. At least r14 and r15 all-stay are type (b). The other 27 are unverified, because per-query records were not archived for first-pass evaluations.
- **Possibly affected:** relocation-search unknowns built from the same skill.

**Smallest justified repair (proposed, needs approval).** Return a distinct reason such as `ENUMERATION_EXHAUSTED_UNCERTIFIED_REJECTIONS` when the skill exits with `failures < max_plan_failures`, and keep `PLANNER_BUDGET` only for type (a). This changes recorded reason semantics for future runs only. Old records keep their labels, with this caveat attached. It was not applied here, to avoid merging incompatible old and new labels.

---

## 6. Compute accounting ([`metrics.csv`](../runs/g4a_teacher_budget_diagnostic/metrics.csv))

| | Value |
|---|---|
| Evaluations started | 6 of 6 allowed (B2 ran for all three, since none was resolved at B1) |
| CPU, diagnostic evaluations | 1,742.66 s (r04: 870.18 + 870.10; r14: 0.56 + 0.58; r15: 0.61 + 0.63) |
| CPU, post-hoc pose screen | 2.24 s (no planning, no target evaluation) |
| Total against the 7,200 CPU-s cap | 1,744.9 s (24.2%) |
| Per-evaluation maximum; trigger; cap; measured overshoot | 870.18 s; 870.0 s; 900 s; **0.0 s** |
| Wall | 1,743.7 s (cap 10,800 s) |
| Guard validation | synthetic test: a parent and a CPU-burning grandchild are both cancelled in flight; the wall guard is also tested |
| Tests and plotting | measured separately; they launched no experimental target evaluations |

---

## 7. Code changes (minimal; lines total / logical)

| File | Change | Lines |
|---|---|---|
| `teacher.py` | **new**: `TEACHER_BUDGET_V1` overrides on a deep copy (deployment untouched), frozen plan with source binding, in-flight process-group CPU/wall guard, isolated single-threaded worker with phase heartbeat, independent witness check (malformed record = not a witness), schedule runner, commands | 274 / 221 |
| `teacher_figures.py` | **new**: reconciliation, budget panel, scene evidence, witness GIFs (none produced) | 107 / 98 |
| `coverage.py` | `certificate_reconciliation`, `call_accounting` | 162 / 135 |
| `run.py` | `teacher-plan`, `teacher-run` | 128 / 102 |
| `tests/test_teacher.py` | **new**: 7 tests | 130 / 106 |
| `README.md`, `requirements.lock` | follow-up entries; `psutil==7.1.3` (already installed; now pinned for the guard) | — |

No change to candidate generation, ranking, relocation policy, grasp domain, margins, tolerances, success policy, primary episodes or any G4A record.

**Post-collection figure fix.** C now shows r04's recorded censoring lines. It was regenerated from the saved records, and the manifest notes this. The figure code is not part of the collection code bound by the plan.

---

## 8. Tests and integrity

`python -m pytest tests -q`: **101 passed**. `tests/test_teacher.py` covers the §8 list:
1. Teacher overrides leave the deployment config dict and `config.toml` bytes unchanged. Only the four declared fields differ, and the G4A plan hash still verifies.
2. Every tier starts from the identical archived state, assignment (∅), action, policy, hashes, grasp family (48) and seed key.
3. The CPU guard cancels an in-flight synthetic task including a grandchild. CPU_CENSORED runs stay UNKNOWN through the whole schedule: never negative, never success, and B2 still runs.
4. Certificate aggregation separates records, unique assignments, duplicates and overlaps.
5. Call accounting handles no-repair, abort and all-stay episodes, and flags violations.
6. The witness check accepts an archived G4A through-retreat witness (g4a_r05) and rejects truncated-retreat and shifted-start records.

**Replays** (reports written to scratch): g1_robot 77, g1_hardening 77, g2_interventions 2, g3_repairs 50, g3_5_initial_scene 20, g4a_evidence_audit 257, all passed. The new diagnostic run has no trajectories to replay (no witness).

**Integrity:** 147 run files and reports 0001–0008 are byte-identical to the pre-work hashes.

---

## 9. Limitations

- **r04 remains undecided under B1/B2.** The 900 CPU-s per-evaluation envelope censored both tiers in carry RRT. A conclusion needs a larger per-evaluation envelope, which this instruction does not authorize.
- **The schedule is combined:** nodes, failures and direct pairs were scaled together. No attribution to a single allowance is possible.
- **Thread settings differ from G4A:** one thread here, defaults there. The outcomes are seeded-deterministic, but CPU and wall timings are not directly comparable to G4A timings.
- **Not re-auditable:** the first-pass B0 per-query records and the 153 first-pass teacher call count.
- **Negative supervision is unchanged** (goal occupancy and finite-grasp access only). Nothing here establishes path-level infeasibility or minimal causal explanations.

---

## 10. Recommendation (one)

**Repair the reason-code defect first (§5), then re-derive causes before spending any budget on the 29 "target-budget" unknowns.**

Re-running those 29 first-pass target evaluations at B0 with the repaired cause codes and per-query records would show how many genuinely end on `max_plan_failures`. Only that subset can benefit from a teacher budget increase. Its cost is bounded above by 29 × 900 CPU-s ≈ 7.25 CPU-hours under the same guard, and is likely far less: in this diagnostic, two of three cases finished in under 1 CPU-s.

r04-type cases, still in carry RRT at 870 CPU-s, would need an explicitly authorized larger per-evaluation envelope. The 67 relocation-search unknowns need their own scoped diagnosis.

**Stopping after this G4A follow-up for review.**

---

## Repository synchronization

This turn commits:
- the instruction file;
- `teacher.py`, `teacher_figures.py`, `coverage.py`, `run.py`, `tests/test_teacher.py`, `README.md`, `requirements.lock`;
- `runs/g4a_teacher_budget_diagnostic/`;
- this report.

No earlier report or run is modified. The commit hash is given in chat and will be recorded as "Previous turn sync" in the next report.
