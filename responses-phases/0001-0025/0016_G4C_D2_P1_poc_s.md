# 0016 — G4C-D2-P1: witness-first 2D dataset — POC_S collection

| Field | Value |
|---|---|
| Report number | 0016 (new; 0001–0015 unchanged) |
| Date | 20 October 2026 |
| Stage | **G4C-D2-P1, `POC_S` only**, run under the explicit numerical authorization in your message. No POC_F (194 units), no remaining G4C roots, no new certificate kinds, no training, 3D or hardware. |
| Execution contract | `instruction-phase-md/G4C_D2_P1_Witness_First_POC_S_Instructions.md` (184 lines, read in full; your file, left untracked) |
| Previous turn sync | Report 0015 was committed as `5e87559e0a1367149964ddd1ce15879b16d04f8c`. At the start, HEAD, `main` and `origin/main` all equalled it, with no tracked modifications. |
| Starting revision | `5e87559e0a1367149964ddd1ce15879b16d04f8c` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0017. |
| Run directory | [`../runs/g4c_d2_poc_s/`](../runs/g4c_d2_poc_s/) (452 files in the manifest, 3.2 MB) |
| **Decision** | **`G4C_D2_P1_COLLECT_PARTIAL`.** All 68 frozen units and both fresh bases were attempted and adjudicated, inside every cap. Two units were cancelled by the per-unit guard at 870 CPU-s and are UNKNOWN, so not all 68 *completed*. **STOP.** |

**Six questions (§5).**

| Q | Verdict | Direct evidence |
|---|---|---|
| Q1 verified bases | **MET** | Both archived witnesses replay (`g4c_r00`, `g4d_R1`; two independent lineages). New base target runs are both POSITIVE. Both fresh bases are POSITIVE. |
| Q2 sound blocked target | **TRIVIAL_ONLY** | Only `seq:d2_g4c_r00_G:empty` and `seq:d2_g4d_R1_G:empty` are certified, both by GOAL_OVERLAP (goal occupant). Every swept-body-blocked root (`+A`, `+A+B`, `+A+S`) has an UNKNOWN no-repair outcome. |
| Q3 corrective recovery | **MET, on the trivial `+G` roots only** | `seq:d2_g4c_r00_G:o04>4`, `seq:d2_g4d_R1_G:o04>61` and `seq:d2_g4d_R1_G:o04>47` are complete relocation + target + safe-retreat witnesses on certified-blocked roots. There is no recovery on a *nontrivially* blocked root, because no such root exists (Q2). |
| Q4 ordering dependency | **MET, in `+A+S`, both families** | `o05>48.o04>49` POSITIVE vs `o04>49.o05>48` ORDER_FIRST_ACTION (g4c_r00). `o05>40.o04>41` POSITIVE vs `o04>41.o05>40` ORDER_FIRST_ACTION (g4d_R1). Caveat: the certificate proves that A's destination is still occupied by S when A moves first. It is an occupancy proof, not a reachability proof. |
| Q5 fully supervised B/C | **MET (3 pools)** | `d2_g4c_r00_N`, `d2_g4d_R1_G` and `d2_g4d_R1_N`: 8/8 active slots decided, ≥2 decided nonempty repairs incl. a witnessed POSITIVE. None is on a swept-body-blocking (`+A*`) variant. |
| Q6 audit | **MET** | All 12 integrity checks are true (below). Every attempt, stop, checkpoint, certificate and UNKNOWN is in the ledger and the manifest. |

---

## 1. Verified baseline and preservation

- **Repository.** HEAD = `origin/main` = `5e87559`, branch `main`. The only untracked files are yours: `instruction-phase-md/*` and the v1.7/v1.9 bundle and zip. They were not touched or committed.
- **P0 artifacts.** The P0 manifest and every file it lists are byte-identical before and after collection (`p0_artifacts_byte_identical`). The frozen inputs (G4C preflight plan, pilot plan/authorization/result, G4D final plan/result) are also unchanged against P0's `source_audit.json`.
- **Archived witnesses.** Both base witnesses (`g4c_r00`: 97 segments; `g4d_R1`: 208 segments) replay with `BASE_WITNESS_REPLAYED`. Their sha256 is unchanged after collection.
- **Earlier results.** The 59-unit pilot (13/26/20) and all earlier runs were not relabelled or rerun.

## 2. What was built (minimum delta)

| File | Role | Lines (total / logical) |
|---|---|---|
| `d2_poc.py` (new) | Authorization record, fresh-base rule, deterministic rebuild of the POC_S roots/units from P0 code with **equality to the saved P0 artifacts**, `validate_plan` (used at finalize **and** immediately before the run), D2 judge over `g4c_pilot.adjudicate / judge_root / bc_pool`, three commands | 374 / 331 — **over the ~300 review trigger** |
| `d2_poc_figures.py` (new) | Evidence assembly via `g4d_gate.assemble`, 12 integrity checks, call accounting, JSON artifacts, figures A–E | 256 / 232 |
| `run.py` | `g4c-d2-poc-finalize`, `g4c-d2-poc-run`, `g4c-d2-poc-judge` | +11 |
| `tests/test_d2_poc.py` (new) | 23 tests (below) | 279 / 240 |

Reused unchanged: `g4d_run.run_collection` (process-tree guard, one worker, admission, atomic checkpoints, ambiguous-resume rule) and `g4d_run.unit_evidence` (checkpoint revalidation). Also reused: `g4c_pilot.adjudicate` (POSITIVE needs a complete witness plus all checks; NEGATIVE needs an accepted certificate of sound scope), and `d2` construction, release and split rules.

`d2_poc.py` exceeds the review trigger. Its bytes are hash-bound into the frozen plan, so it was not split after freezing. A future split (validator vs judge) is cosmetic.

**One real defect found before collection, by the synthetic dry run.** The P0 release rules in `d2.py` (`substantive_pool`, `pool_release`) compare against the abstract words `"POSITIVE"` and `"NEGATIVE"`. The evidence labels are `VERIFIED_FEASIBLE` and `CERTIFIED_INFEASIBLE`, so no pool could ever have been substantive. The adapter now maps labels to these words (`d2_poc.WORD`). `d2.py` itself is P0-bound and was left unchanged.

## 3. Frozen plan, authorization and admission

- **Authorization.** `authorization.json` (hash `sha256:677e0089…`) records the limits verbatim from your message:

  | Limit | Value |
  |---|---|
  | Units | 68 = 50 / 16 / 2 |
  | Fresh-base attempts | 2 |
  | CPU per unit | 900 s, cancellation at 870 s |
  | Aggregate CPU | 18,000 s |
  | Workers | 1 |
  | Wall | 1,800 s per unit / 23,400 s total |
  | Planner | 4,000 nodes |
  | Calls | 46 relocation / 70 target |

  It is bound to the instruction file's sha256 and the P0 manifest's sha256.
- **Final plan.** `final_plan.json` has plan hash `sha256:6dcdd266…`. It holds 70 units:
  - 2 fresh bases first, then the 68 frozen units in P0 order: 50 ordered / 16 scene / 2 robot-start.
  - Every unit passes `g4d_run.unit_scene`, canonical-sequence parsing and pool membership.
  - The plan also binds a source hash for 20 files.
- **Worst-case call schedule (structural, outcome-independent).** 46 relocation skills (Σ len(sequence)) and 70 target evaluations. This exactly fits the caps. Admission rule: spent + 900 + 60 s reserve ≤ 18,000.
- **Fresh bases.** Predeclared before any outcome:
  - Seeds `2026102101` and `2026102102`.
  - G4C J0 layout rule, q0 at the profile default, `GOAL_AND_SAFE_RETREAT`.
  - Static checks: q0 clear, and not a duplicate of any known geometry.
  - Both seeds were accepted statically: goal 52 / target 23, and goal 29 / target 57.
  - They are diagnostics only. No descendants were created, and they are not counted in the 68.
- **`construction_attempts.jsonl`.** Holds the P0 attempt file reference (sha256) plus the two fresh-base attempt rows.

## 4. Run envelope (`compute_summary.json`, `ledger.json`)

| Quantity | Value |
|---|---|
| Wall | 11:06:04 → 14:36:39 UTC (12,634 s; cap 23,400) |
| CPU | 12,622.1 unit + 44.0 coordinator = **12,666.1 CPU-s** (cap 18,000; 70 %) |
| Unit CPU median / p90 / max | 10.5 / 727.9 / 870.2 s |
| Stops | 68 COMPLETED, **2 CPU_CENSORED** (`seq:` and `scene:d2_g4d_R1_AB:o04>41`, both during target evaluation, carry phase); 0 NOT_RUN; 0 resumes |
| Overshoot past the trigger | 0.0 s max; no enforcement failure |
| Relocation-skill calls | **40 / 46**: 39 recorded in final checkpoints, plus 1 completed in the cancelled ordered unit (its relocation checkpoint exists) |
| Target evaluations | **63 / 70**: 61 recorded, plus 2 in flight at cancellation. Split: fresh bases 2, ordered 42 (+1), scene 15 (+1), robot-start 2 |
| HOME diagnostics | 32 (one after each positive target witness; diagnostic only, never a label) |
| Historical regression tests (in-process, disclosed separately) | 621 `planner.plan`, 60 `skill.plan_skill`, unchanged; `test_d2_poc.py`: 0 |

Figure E's title shows the 39/61 recorded counts. The 40/63 totals above include the cancelled units' in-flight calls.

Cost concentrates in `g4d_R1`'s blocked variants, `+A+B` above all: 10 units, 6,655 CPU-s, zero decided. All of `g4d_R1` cost 12,024 CPU-s; all of `g4c_r00` cost 596 CPU-s.

## 5. Outcomes (all denominators planned)

| Kind | POSITIVE | NEGATIVE | UNKNOWN | NOT_RUN | Total |
|---|---|---|---|---|---|
| Ordered (frozen) | 20 | 6 | 24 | 0 | 50 |
| Scene target-only | 8 | 0 | 8 | 0 | 16 |
| Robot-start | 2 | 0 | 0 | 0 | 2 |
| **Frozen 68** | **30** | **6** | **32** | **0** | **68** |
| Fresh-base diagnostics | 2 | 0 | 0 | 0 | 2 |

**No-repair outcome per variant root** (nominal-path collision is a diagnostic, never a label):

| Variant | g4c_r00 | g4d_R1 | Nominal path blocked? |
|---|---|---|---|
| base | POSITIVE | POSITIVE | no |
| +A | UNKNOWN | UNKNOWN | yes |
| +A+B | UNKNOWN | UNKNOWN | yes |
| +A+S | UNKNOWN | UNKNOWN | yes |
| +G | NEGATIVE (GOAL_OVERLAP) | NEGATIVE (GOAL_OVERLAP) | yes |
| +N | POSITIVE | POSITIVE | no |

- **REROUTABLE_POSITIVE:** none. No nominally blocked root got a no-repair witness.
- **"Collides with nominal path, task unknown":** 6 roots (`+A`, `+A+B`, `+A+S` × 2).

**UNKNOWN causes (32).**

| Cause | Count | Notes |
|---|---|---|
| `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS` | 15 | Fast (2–14 s). Every scheduled target grasp/connector attempt was rejected, but there is no checker-accepted full-domain certificate. |
| `SEARCH_LIMIT_PLAN_FAILURES` | 12 + 1 | Expensive (440–835 s); the extra one is in relocation. |
| `..._WITH_UNRESOLVED_CONNECTORS` | 2 | |
| CPU_CENSORED | 2 | |

None is a negative.

**Certificates (`certificate_breakdown.json`).**
- Trivial: GOAL_OVERLAP [ASSIGNMENT] ×2 and STATIC_ENDPOINT_INVALID [ASSIGNMENT] ×2. The latter is the A→S-occupied-cell single move in `+A+S`.
- Counted nontrivial: ORDER_FIRST_ACTION [ORDER] ×2.

That nontrivial count should not be over-read. ORDER_FIRST_ACTION certifies an occupied destination at the time of the first action. It is sound and order-scoped, but it is not a physically interesting access proof. No new certificate kind was introduced.

## 6. Repairs, contrasts, interventions, B/C pools (`per_root_coverage.json`, `comparison_effects.json`, `bc_pool_coverage.json`)

- **Positive repair witnesses by move count.**

  | Moves | Witnesses | Notes |
  |---|---|---|
  | 0 | 6 | |
  | 1 | 12 | |
  | 2 | 4 | `g4c_r00 +A+B` (both orders), `g4c_r00 +A+S` (1), `g4d_R1 +A+S` (1) |
  | 3 | 0 | |

- **Alternative destinations.** ≥2 positive alternative assignments on 6 roots.
- **Same-endpoint order contrasts.** 2 (Q4). Both other order pairs, in `+A+B`, are positive/positive on g4c_r00 and unknown/unknown on g4d_R1.
- **Cost.** 47 first-witness cost records (`label_available`), including 33 nonempty ones. J (normalized joint travel) ranges 0.98–2.62 across C_d ∈ {0.088, 0.125, 0.177} m (figure E, right).
  - Several costs belong to repairs whose target label is UNKNOWN. That is permitted: the relocation cost exists independently of the target outcome.
  - No target-selected cheapest trace is used.
- **Scene edits** (fixed robot, 16 eligible; Δ = Y(edit) − Y(empty)). Only 4 pairs are decided, because the reference no-repair is UNKNOWN on every `+A*` root:

  | Pair | Δ |
  |---|---|
  | `+G` singleton, ×2 | +1 |
  | `+N` nuisance, ×2 | 0 (nuisance invariance measured) |

  Eight edits are POSITIVE with an UNKNOWN reference, so they are masked.
- **Robot start.** 2 decided pairs, both Δ = 0.
- **Omissions.** 6 decided pairs. **Nonadditivity:** none measurable, because no joint and singleton set is fully decided.
- **B/C pools.** These are the 12 variant pools plus the 2 fresh bases.
  - Complete: 7.
    - Substantive: 3 (`g4c_r00_N`, `g4d_R1_G`, `g4d_R1_N`).
    - Trivial empty-only: 4 (both bases, both fresh).
  - Incomplete: `+A` 4/8 and 5/8; `+A+B` 21/40 and **0/40**; `+A+S` 7/37 and 8/37; `g4c_r00_G` 7/8 (one relocation UNKNOWN).
- **Yield.**

  | Measure | Value |
  |---|---|
  | Decided frozen units | 36/68 (53 %) |
  | Complete variant pools | 5/12 |
  | **Substantive complete pools** | **3/10 eligible variant pools** (the non-base variants) |
  | Lineages with a substantive pool | 2/2 |

  CPU of the three substantive pools' own units: 203 + 131 + 243 s. Whole-run CPU per substantive pool: 4,222 s.

## 7. Figures (recorded data only)

- `A_base_and_blockers.png`. Twelve variant roots at q0, each with:
  - the archived nominal target path, shown dashed and labelled *pre-insertion*;
  - the inserted blockers;
  - the first nominal collision;
  - the new no-repair outcome.
- `B_outcomes_by_variant.png`. POSITIVE / NEGATIVE / UNKNOWN / NOT_RUN per root, with the planned denominator.
- `C_order_and_repair_evidence.png`. The two real `+A+S` order contrasts with their recorded witnesses and certificates, plus the `+G` certified-blocked roots and their recorded recovery witnesses.
- `D_interventions_and_bc_pools.png`. Active-slot decided/undecided per pool with complete/substantive marks, plus the four decided scene-edit pairs.
- `E_compute_and_cost.png`. Per-unit CPU coloured by label, with the 870/900 lines; cumulative CPU vs the 18,000 cap; and C_d vs first-witness J. Cosmetic issue: the 870/900 line labels overlap at the top of the left panel.

## 8. Integrity (Q6; `poc_result.json` → `integrity`)

All true:
- sources unchanged (20 files plus plan hash);
- authorization unchanged and valid;
- P0 manifest unchanged;
- P0 artifacts byte-identical;
- historic frozen inputs unchanged;
- archived witnesses unchanged;
- units run ⊆ plan;
- every unit has evidence;
- no contradiction;
- relocation cap respected;
- target cap respected;
- no enforcement failure.

## 9. Tests and replays

- **Before collection.**
  - 216 passed (193 + 23 new).
  - Six replays pass (77/77/2/50/20/257 trajectories).
  - Synthetic judge dry run on an empty ledger: 70 NOT_RUN kept in the denominator, 0 teacher calls, all 12 integrity checks true.
- **After collection.** 216 passed; six replays pass again, into scratch report paths.
- **`test_d2_poc.py` (23).**
  - Exact P0 scope with zero calls.
  - Four wrong-authorization cases.
  - Eleven plan mutations fail closed: 67/69 units, extra POC_F `+A+B+C` variant, wrong lineage, mutated robot q0, noncanonical sequence, changed catalogue, leaked teacher field, reordered units, changed intervention hash, extra fresh base.
  - A changed P0 query file refuses finalization.
  - Tampered source/plan hash.
  - Guard: 870 cancellation, overshoot → enforcement failure, over-budget → NOT_RUN_BUDGET, expired wall → NOT_RUN_WALL, ambiguous STARTED never rerun, foreign ledger refused.
  - Synthetic judge: P/N/U/contradiction; TRIVIAL_ONLY for GOAL_OVERLAP; REROUTABLE_POSITIVE; invalid TRAJECTORY scope → UNKNOWN; missing invocation → UNKNOWN.
  - Order contrast needs ORDER scope and both sides decided.
  - Substantive pool, and one UNKNOWN slot breaks it.
  - Corrupted cost is not a label.
  - Learner view carries no construction privilege.

## 10. Commands

| Command | Exit | Result |
|---|---|---|
| `python -m pytest -q tests` (with scratch call counter) | 0 | 216 passed (before and after) |
| `python run.py replay --run runs/<run> --report <scratch>` ×6 | all 0 | all `replay_passed` |
| `python run.py g4c-d2-poc-finalize --out runs/g4c_d2_poc_s` | 0 | plan `sha256:6dcdd266…`, 70 units, worst case 46/70 |
| `python run.py g4c-d2-poc-run --out runs/g4c_d2_poc_s` | 0 | 68 COMPLETED + 2 CPU_CENSORED, 12,666 CPU-s, no failure |
| `python run.py g4c-d2-poc-judge --out runs/g4c_d2_poc_s` | 0 | `G4C_D2_P1_COLLECT_PARTIAL`, 32/6/32 |

## 11. What this POC does and does not show

- **Shown:**
  - Witness-first construction is reproducible.
  - Proof-carrying labels work end to end under a hard envelope.
  - Order dependence arises *by construction* in `+A+S`, on both lineages.
  - Complete, substantive B/C pools exist, but on `+N`/`+G` variants.
- **Not shown:**
  - A sound, nontrivial infeasibility induced by a swept-body blocker. All six `+A*` no-repair outcomes are UNKNOWN.
  - On `g4c_r00` they resolve in 2–3 s to "every scheduled attempt rejected, uncertified". This is exactly the pattern a full-domain grasp/connector certificate would decide. It needs a **separate soundness review and authorization**, and was not implemented.
  - On `g4d_R1` the same queries hit the 4,000-node search limit at 440–835 CPU-s.
- **Not a dataset.** This is two lineages and a development feasibility study. There is no `DATASET_READY` claim and no train/validation/test split claim.

**Options for you to decide (none started):**
1. A soundness review of an "all target grasps blocked at a fixed scene" certificate. This targets the 15 fast UNKNOWNs.
2. A cheaper construction rule that favours `g4c_r00`-like geometry (fast resolution) over `g4d_R1 +A+B` (6,655 CPU-s, zero decided).
3. POC_F, only after 1 or 2, because the `+A+B+C` variants are likely costlier than `+A+B`.

## 12. Decision

**`G4C_D2_P1_COLLECT_PARTIAL`.** All 68 units and both fresh bases were attempted and soundly adjudicated within all caps. Two units were guard-cancelled (UNKNOWN). Q1, Q3 (trivial root), Q4, Q5 and Q6 are MET; Q2 is TRIVIAL_ONLY. **STOP.** POC_F, the remaining G4C roots, new certificates, training, 3D and hardware were not started.

## Repository synchronization

Committed to `main` with the code, tests, `runs/g4c_d2_poc_s/` and this report, then pushed without force. The commit hash and remote verification are given in chat and recorded in report 0017.
