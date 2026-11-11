# 0011 — G4D: corrections, legacy evidence recovery and bounded sparse collection

| Field | Value |
|---|---|
| Report number | 0011 (new; 0001–0010 unchanged) |
| Date | 19 October 2026 |
| Stage | **G4D only.** Four reproduced defects corrected, reason reporting and provenance repaired, archived evidence revalidated, collection runner built and tested, and the authorized sparse plan executed. **No** G4B, G4C, GRU, sampler, training, bulk generation, 3D or hardware work. |
| Instruction | `instruction-phase-md/G4D_corrections_and_bounded_collection_prompt.md` (your copy; left untracked) |
| Normative documents | Methodology v1.6, Guide v1.8, addenda A1 and **A2 (new)**, reports 0009 and 0010, `runs/g4d_migration/` |
| Plain-language guide | `Architecture_Explained_Step_by_Step.md` is still absent from the repository and the machine. I used the methodology's appendices A and B instead; nothing was blocked by its absence. |
| Previous turn sync | Report 0010 was committed as `5011e82398ef275bd4f8cdd99d598f70248bb370`. The review examined that same commit. At the start of this work, HEAD and `origin/main` equalled it, so there was no newer work to preserve. The untracked items were your instruction file and your two PDF copies. |
| Starting revision | `5011e82398ef275bd4f8cdd99d598f70248bb370` |
| Ending revision | The commit that carries this report; its hash is given in chat and recorded in report 0012. |
| Run directory | [`../runs/g4d_evidence/`](../runs/g4d_evidence/), produced by `g4d-legacy` → `g4d-finalize` → `g4d-run` → `g4d-judge` |
| **Gate** | **G4D PASS** against the five blocking requirements. All seven D-V2 cases are met, three of them with qualifications that §7 states explicitly. |
| Collection compute | **133.8 CPU-s** (units 133.3 plus coordinator 0.57) against an 18,000 CPU-s cap. Wall 2 min 16 s. Every unit COMPLETED with overshoot 0.0 s; no censoring, no enforcement failure, no resume. |
| Separate compute | Legacy revalidation 11.6 CPU-s; judge and figures 4.0 CPU-s; tests about 2.6 min; replays about 2 min. |
| Tests / replays | **135 passed** (101 earlier, 14 from report 0010 with two assertions updated to the corrected API, 15 correction tests, 5 runner tests). All six archived runs replay (77/77/2/50/20/257). No tracked file under `runs/` or `responses-phases/` changed. |

G4A remains **NOT_READY_TO_SCALE**, and its 4.56 CPU-h use against a 4.0 CPU-h cap stays historical. Passing G4D does not pass G4A retroactively.

---

## 1. Reproduced defects and fixes (§2)

Each defect was reproduced on `5011e82` before any change, using a scratch script.

| # | Reproduction on `5011e82` | Fix | Tests |
|---|---|---|---|
| 2.1 | `episode_audit` returned `boundary_ok=True` for `COMMIT→ABORT→TARGET_EVALUATE` and for `COMMIT→COMMIT→TARGET_EVALUATE` | Rewritten as a full event contract: one terminal event, last; ≤ 1 commit; ≤ 1 target call; no target before commit or after abort; the target only after **all** committed RELOCATEs (each certified) and successful REOBSERVEs; a target exists only with a completed repair. Each check is True/False/None; the `decision` is PASS only if all applicable checks are True, FAIL on any False, else UNKNOWN. `protocol_compliant` is separate from `outcome`. Added: `achieved_state_matches_commitment` (identities, poses, joints, gap, history via `validate_observation`); `target_invocation_equals_achieved` (the **recorded** input state of the actual target call, object poses included, also checked against the last relocation end); a trajectory-start check when a trajectory exists. | 5 illegal-history mutations, plus reordering the target before REOBSERVE: all FAIL. A valid empty-repair episode passes. A tampered achieved pose fails. A missing invocation record gives UNKNOWN. Abort and no-witness episodes are compliant but unsuccessful. |
| 2.2 | Cap 10, 9 used, 3 actions: accounting reached **12**, with 3 planner calls | `plan_fixed_order` now runs its own loop. Before every relocation-planner invocation it checks the allowance, and it charges every invocation, failed or not. A cut sequence is UNRESOLVED (`RELOCATION_BUDGET`): no witness, no cost label, partial prefix kept as a diagnostic. V1 `realize` and `plan_repair` are untouched. | Near-cap (1 call, used = 10), exact-cap (0 calls), below cap (3 calls), empty sequence at the cap (witness, 0 calls), failed call charged |
| 2.3 | `canonical` used `int(d)`: `True` became cell 1 and `29.9` became cell 29, and both passed | One public contract, `sequences.parse_sequence`, checks raw shape, string IDs and integer, non-bool cells **before** any conversion, then applies the physical rules. `canonical` now raises instead of coercing. `rank_sequences` and `teach_sequence` both use the contract; `plan_fixed_order` rejects non-canonical input. | 11 bad raw forms (bool, fraction, integral float, string cell, short pair, int ID, non-list, duplicate, stay, target, over cap) are rejected by `rank_sequences` and raise in `teach_sequence` before any planner call |
| 2.4 | `legacy_audit` never called the checker for negatives; it trusted `checker_accepted` plus the scope map | `legacy.revalidate_negative` rebuilds each certificate's claim from the archived scene, assignment and action. The archive kept only kind and verdict, so the claim is regenerated by the deterministic producer and **stamped with the archived identity hashes and assignment**. The independent checker is then re-run. Separately it checks observation and action hashes, target identity, robot profile, grasp family, contact rules, tolerances, end policy and move-once. The archived boolean is recorded for comparison only. Contradictions are screened. | Mismatched observation hash, action hash or assignment: rejected. Missing end policy: rejected. An unsound kind (planner exhaustion): rejected. |

`g4d.legacy_audit`, the migration API, now delegates to the corrected `legacy.revalidate`. Its archived outputs in `runs/g4d_migration/` are unchanged as historical records.

---

## 2. Reason reporting and provenance (§3)

**Termination events.** `SkillResult.termination` records the explicit end event. The historical `reason` strings, statuses and all archived outputs are unchanged. The events are:
- `SEARCH_LIMIT_PLAN_FAILURES` (an actual search limit);
- `SCHEDULE_COMPLETED_NO_WITNESS` and `SCHEDULE_COMPLETED_ALL_CERTIFIED_BLOCKED`;
- the screen-exhaustion events;
- `START_STATE_NOT_CLEAR`;
- `WITNESS_RECHECKED` and `WITNESS_REPLAY_REJECTED`.

`ordered.normalized_reason` maps these to V2 reasons, adding `_WITH_UNRESOLVED_CONNECTORS`, `_UNCERTIFIED_REJECTIONS` and `+WALL_LIMIT_INVOLVED`. CPU and wall censoring are runner-level stop statuses.

**Demonstration on the archive.** Re-planning g4a_r14 (0.6 CPU-s) returns `reason = PLANNER_BUDGET` with `termination = SCHEDULE_COMPLETED_NO_WITNESS`.

**Addendum.** The new [`docs/addenda/A2_termination_reasons_v1.md`](../docs/addenda/A2_termination_reasons_v1.md) states that the earlier count of 29 target-budget outcomes was a count of raw reason strings, which report 0009 subsequently questioned. Those rows stay UNRESOLVED and are **not** re-split; that would need re-planning, which is not authorized.

**Context identity.** `effects.context_identity` binds each side of a comparison to:
- the observation hash (all scene and robot fields) and the action-context hash (task, goal, policy, profile);
- the protocol and schema;
- the sequence or intervention;
- the appearance anchor and the evidence IDs.

`omission_records` now takes the query. `rank_sequences` uses `scene_hash` (robot joints, gap, attachment, lattice, legal cells, profile) together with the action. A test shows that identical sequences in different robot states, or with different anchors, get different hashes.

Scene effects, omission effects, robot-start comparisons and deletion diagnostics remain separate kinds. Necessity and minimum-repair stay `UNESTABLISHED`.

---

## 3. Legacy evidence revalidation (§2.4, §4); 11.6 CPU-s, outside the envelope

Record: [`legacy_revalidation.json`](../runs/g4d_evidence/legacy_revalidation.json).

| Item | Result |
|---|---|
| Positives (exact recorded order, full replay plus scope checks) | **44 / 44 validated** |
| Negatives transferred to every order (reconstructed and re-checked) | **86 / 86**; 0 rejected |
| Certificate records re-checked / accepted | 89 / 89 (GOAL_OVERLAP 72/72, TARGET_PICK 13/13, FIRST_MOVER 4/4) |
| Disagreements with the archived verdict | 0 |
| Positive/negative contradictions | **0**, so collection was allowed to proceed |

The transfer checks now actually establish the scope validation that report 0010 claimed. Their success does not mean the earlier transfer was unsound; it shows that the archived verdicts hold up under the full check.

### Derived legacy omission pairs ([`legacy_omission_pairs.json`](../runs/g4d_evidence/legacy_omission_pairs.json))

These come from a deterministic enumeration over validated positives: omitted subsets of size 1–2, with the remaining actions kept in order.
- A positive side counts only for its exact witnessed order.
- A negative side needs a revalidated assignment-wide certificate covering the remaining assignment.
- Anything else is masked.

| Quantity | Count |
|---|---|
| Pairs enumerated | 91 |
| Decided | **47**: Δ = +1 ×25, Δ = 0 ×22, Δ = −1 ×0 |
| Masked (an unknown side) | 44 |
| Unique roots with a decided pair | 9 (r01, r02, r03, r05, r10, r11, r12, r16, r19) |
| Unique roots with a decided +1 | 6 (r01, r02, r03, r11, r12, r16) |

The review's 25-candidate observation is reproduced independently: 25 decided +1 pairs across 6 roots.

The review example also checks out. On g4a_r02, r = (o00→41, o07→42) at audit 2 is POSITIVE. Omitting o00 leaves (o07→42), whose assignment at audit 9 carries a re-checked GOAL_OVERLAP, so Δ = +1 (tested).

These pairs are **derived legacy evidence (V1 backend)**, not independent new examples. Legacy joint travel remains diagnostic only.

### The ten exact two-move positives ([`legacy_two_move.json`](../runs/g4d_evidence/legacy_two_move.json))

All ten pass joint continuity, achieved-state consistency, target-start equality, safe retreat and the scope checks. So under the same scope-based reuse used for D-V2-0, they meet the general two-move-witness requirement as **DERIVED_LEGACY** evidence for their exact order:
- g4a_r02 audits 2 and 6
- g4a_r03 audit 2
- g4a_r05 audits 2 and 6
- g4a_r11 audits 2 and 6
- g4a_r12 audit 10
- g4a_r16 audits 2 and 6

None supplies a same-endpoint order contrast, because the other order of each is unresolved. They did not alter the frozen units.

---

## 4. Runner, checkpoints and their tests (§5)

**Components.** `g4d_run.py` provides:
- `make_final_plan`;
- `worker`, a per-unit subprocess;
- `run_collection`, which uses `teacher.guard` (process-tree CPU, process-group kill, single-threaded numerical libraries);
- `unit_evidence`.

The commands live in `g4d_gate.py`. The figures, drawn from saved evidence, are in `g4d_evidence_figures.py`.

**Atomic checkpoints, in order.** Each is written as `.tmp` then renamed:
1. `certificates.json` (all producer records with the checker's verdict);
2. `relocation.json/.npz` (the fixed-order result, first-witness cost and achieved states; for a failed sequence, only the verified prefix records as a diagnostic);
3. `target_witness.json/.npz`, written through the new `evaluate_safe_retreat(on_witness=…)` hook **before** the optional HOME diagnostic, which stays on (V1 config untouched);
4. `final.json`.

**Evidence and stop are separate.** Unit evidence is rebuilt only from checkpoints that re-check now:
- the independent checker is re-run on each stored certificate;
- each relocation record is re-certified in its pre-move scene, from the previous achieved state, ending at the next achieved state in retreat, and the cost is recomputed;
- the target witness must pass `check_witness` and its recorded invocation must equal the last achieved state.

A unit's evidence status is separate from its process stop status.

**Synthetic orchestration tests (temporary directories).**
- CPU cancellation (2.5–3.5 CPU-s at a 2 s trigger), with an incomplete `certificates` checkpoint preserved;
- a child process's CPU counted while the parent sleeps;
- wall cancellation;
- nonzero exit reported as ERROR with its return code;
- aggregate admission (`NOT_RUN_BUDGET`) and the global wall (`NOT_RUN_WALL`);
- resume: only never-started units run; a STARTED unit becomes `INTERRUPTED_AMBIGUOUS` and is not repeated; completed units are kept; the original deadline is reused; a ledger from another plan is refused.

**Two real-unit tests (temporary directories; test seed keys for R2).**
- R4's bad order through the real worker yields an ORDER_FIRST_ACTION certificate, and a tampered checkpoint is not reused.
- R2 o03→60 checkpoints its relocation witness, cost and target witness; all re-check. A 1e-3 rad change to a relocation record voids the witness and the cost label.

**Bugs found during this stage, all fixed before or during the gate run.**
- The runner did not create the output directory (test).
- The final-plan identity check compared in-memory tuples with stored lists; finalization refused until fixed. The plans were identical.
- The judge's manifest writer could not hash the per-unit subdirectory. I added a recursive manifest and regenerated only the judge's derived outputs, which were not yet committed. No collection output was touched.

---

## 5. Final execution plan and envelope (§6)

The plan is [`final_plan.json`](../runs/g4d_evidence/final_plan.json), hash `sha256:a1b5a67fe36b21279e739bbb341c6f71647f87b3870c925c707e1fe5868eb215`. Its status is `FINAL_AUTHORIZED`.

**Link to the pending plan.** The pending plan `runs/g4d_migration/g4d_plan.json` (hash `sha256:c0f3bcb2…13c4bf`) is unchanged and is verified by file sha and plan hash. The corrected code regenerates its units, roots and cases identically, and the 20 units are copied verbatim: roots, sequences, interventions, seed keys, order and action/search policies. Hashes changed only because sources were corrected and the envelope was added; the plan records why.

**Bindings.**
- source: HEAD `5011e82` plus the sha256 of 28 files (runner, guard, scene construction, checking dependencies, configs, fixtures, the G2 archive files that R0/R1/R5 load, the pending plan), verified before collection and again after it (no mismatch);
- the legacy revalidation sha;
- both document hashes.

**Envelope (as authorized).**

| Limit | Value |
|---|---|
| CPU per unit | 900 s, cancellation trigger 870 s (margin 30 s) |
| Aggregate CPU | 18,000 s, with a 60 s orchestration reserve in admission |
| Workers | 1 (OMP, OpenBLAS, MKL and NumExpr set to 1 thread) |
| Wall per unit | 1,800 s |
| Global wall | 21,600 s |
| Poll | 0.25 s |

The search schedule is unchanged: 4,000 nodes; relocation and target failure allowances of 2 and 4; 48 grasps; the same margins, tolerances and supported transport.

---

## 6. Collection ledger (§7)

Ledger: [`ledger.json`](../runs/g4d_evidence/ledger.json). Evidence: [`unit_evidence.json`](../runs/g4d_evidence/unit_evidence.json).

| Unit | Stop | Evidence label | CPU s | Wall s | Overshoot | Checkpoints | Reloc / target calls | V2 J |
|---|---|---|---|---|---|---|---|---|
| `scene:R2:o03>38` | COMPLETED | POSITIVE | 6.71 | 6.78 | 0.0 | cert, reloc, target, final | 0 / 1 | (empty) 0 |
| `scene:R2:o03>60` | COMPLETED | POSITIVE | 8.55 | 8.79 | 0.0 | cert, reloc, target, final | 0 / 1 | 0 |
| `scene:R5:o02>40` | COMPLETED | POSITIVE | 5.02 | 5.02 | 0.0 | cert, reloc, target, final | 0 / 1 | 0 |
| `scene:R5:o02>40.o05>49` | COMPLETED | POSITIVE | 1.90 | 2.01 | 0.0 | cert, reloc, target, final | 0 / 1 | 0 |
| `scene:R5:o05>49` | COMPLETED | UNKNOWN (target `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS`) | 5.95 | 6.03 | 0.0 | cert, reloc, final | 0 / 1 | 0 |
| `seq:R0:empty` | COMPLETED | POSITIVE | 10.43 | 10.55 | 0.0 | cert, reloc, target, final | 0 / 1 | **0.0 exactly** |
| `seq:R1:empty` | COMPLETED | POSITIVE | 60.16 | 60.26 | 0.0 | cert, reloc, target, final | 0 / 1 | 0.0 |
| `seq:R2:empty` | COMPLETED | NEGATIVE (GOAL_OVERLAP) | 0.56 | 0.75 | 0.0 | cert, reloc, final | 0 / 0 | 0.0 |
| `seq:R2:o01>21.o03>13` | COMPLETED | UNKNOWN (action 0 `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS`) | 1.07 | 1.26 | 0.0 | cert, reloc, final | 1 / 0 | — |
| `seq:R2:o03>13` | COMPLETED | NEGATIVE (STATIC_ENDPOINT_INVALID) | 0.37 | 0.50 | 0.0 | cert, final | 0 / 0 | — |
| `seq:R2:o03>13.o01>21` | COMPLETED | NEGATIVE (ORDER_FIRST_ACTION) | 1.07 | 1.26 | 0.0 | cert, final | 0 / 0 | — |
| `seq:R2:o03>38` | COMPLETED | POSITIVE | 6.34 | 6.53 | 0.0 | cert, reloc, target, final | 1 / 1 | 1.0408 |
| `seq:R2:o03>60` | COMPLETED | POSITIVE | 7.32 | 7.53 | 0.0 | cert, reloc, target, final | 1 / 1 | 1.0212 |
| `seq:R4:empty` | COMPLETED | NEGATIVE (GOAL_OVERLAP) | 0.49 | 0.50 | 0.0 | cert, reloc, final | 0 / 0 | 0.0 |
| `seq:R4:o00>29` | COMPLETED | NEGATIVE (FIRST_MOVER + ORDER_FIRST_ACTION) | 0.58 | 0.75 | 0.0 | cert, final | 0 / 0 | — |
| `seq:R4:o00>29.o01>18` | COMPLETED | NEGATIVE (ORDER_FIRST_ACTION) | 2.56 | 2.76 | 0.0 | cert, final | 0 / 0 | — |
| `seq:R4:o01>18` | COMPLETED | NEGATIVE (GOAL_OVERLAP); relocation witness | 2.40 | 2.51 | 0.0 | cert, reloc, final | 1 / 0 | 1.3937 |
| `seq:R4:o01>18.o00>29` | COMPLETED | **POSITIVE (two moves)** | 5.15 | 5.28 | 0.0 | cert, reloc, target, final | 2 / 1 | 1.7227 |
| `seq:R5:empty` | COMPLETED | UNKNOWN (target `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS`) | 4.44 | 4.52 | 0.0 | cert, reloc, final | 0 / 1 | 0.0 |
| `start:R1:0` | COMPLETED | POSITIVE | 2.20 | 2.26 | 0.0 | cert, reloc, target, final | 0 / 1 | 0.0 |

**Realized calls.**
- relocation-skill planner: **6** (cap 13)
- primary target evaluations: **12** (cap 20)
- optional HOME diagnostics: 10 (inside the envelope; all VERIFIED; they never change a label)

Accepted certificates skipped 8 target calls. No unit was rerun.

---

## 7. Gate and D-V2 outcomes

### Blocking requirements (the minimum gate)

| Requirement | Result | Evidence |
|---|---|---|
| B1: complete checked nonempty two-move sequence | **PASS** | NEW V2: `seq:R4:o01>18.o00>29`, two certified relocations plus a target with safe retreat, all re-checked. DERIVED LEGACY: the 10 sequences in §3, counted separately. |
| B2: decided same-endpoint order contrast | **PASS** | R4: (o01→18, o00→29) POSITIVE vs (o00→29, o01→18) NEGATIVE by an **order-scope** ORDER_FIRST_ACTION certificate (o00's pick is excluded over all 48 grasps while o01 stays), re-checked by the independent checker. The second contrast attempt, on R2, is **undecided**: its good order's first relocation (o01→21) ended UNRESOLVED and is not counted. |
| B3: decided, eligible scene-effect pair | **PASS** | R2: baseline empty repair NEGATIVE (GOAL_OVERLAP) vs o03→38 and o03→60 at the fixed initial robot state, both POSITIVE target-only, so Δ = +1 twice. |
| B4: decided omission pair | **PASS** | NEW V2: 3 decided (R4, below). DERIVED LEGACY: 47 decided (§3), counted separately. |
| B5: continuity, achieved state and target start on every claimed witness | **PASS** | All 10 new witnesses pass the joint-continuity, achieved-state and target-invocation checks. |

**G4D PASS.**

### Each D-V2 case

- **D-V2-0 — met.** NEW V2: R0 empty repair POSITIVE with J = 0.0 exactly. DERIVED LEGACY: g4a_r05, r10 and r19.
- **D-V2-1 — met.** R2's goal occupant o03 is certified mandatory for the empty repair (GOAL_OVERLAP). Sufficient repairs o03→60 and o03→38 are both POSITIVE. Both scene pairs are decided (Δ = +1).
  - A successful scene edit does **not** prove the robot can execute that edit. The executable repairs are separate witnesses.
- **D-V2-2 — met on R4; R2 undecided.** See B2. No timeout was used anywhere.
- **D-V2-3 — met at endpoint level, with a qualification.** On R2, o03→13 with o01 staying is certified static-invalid (o01 occupies 13), while o03→60 with o01 staying is POSITIVE. So o03's destination decides whether o01 must move. The alternative that actually moves o01, the chain (o01→21, o03→13), is UNRESOLVED: its first relocation's schedule completed without a witness. Its reverse order is certified NEGATIVE (first action place excluded).
- **D-V2-4 — omission interaction exposed; scene interaction undecided.** R4 omissions of r = (o01→18, o00→29):

  | Omitted | Remaining | Remaining label | Δ |
  |---|---|---|---|
  | {o01} | (o00→29) | NEGATIVE: first action excluded; FIRST_MOVER also accepted | +1 |
  | {o00} | (o01→18) | NEGATIVE: o00 still on the goal (GOAL_OVERLAP) | +1 |
  | {o01, o00} | ∅ | NEGATIVE (GOAL_OVERLAP) | +1 |

  The singleton effects sum to 2 while the joint effect is 1, so the effects are non-additive. That is the access dependency: o01's action matters only together with o00's. Two of the three negatives are goal-overlap certificates.

  For the R5 scene comparison, the baseline is UNKNOWN, so all three pairs are masked. The singleton o02→40 and the joint o02→40 + o05→49 are POSITIVE, and o05→49 alone is UNKNOWN. No interaction is claimed there.
- **D-V2-5 — met.** First-witness V2 cost labels, with endpoint distance C_d:

  | Root | Sequence | C_d | J |
  |---|---|---|---|
  | R2 | o03→38 | 0.125 | 1.041 |
  | R2 | o03→60 | 0.198 | 1.021 |
  | R4 | o01→18 | 0.125 | 1.394 (ordered label NEGATIVE; the cost label is still valid) |
  | R4 | (o01→18, o00→29) | 0.213 | 1.723 |

  On R2 the larger endpoint displacement had slightly *lower* measured joint travel. This is one observation, not a trend, and no inequality was presupposed.
- **D-V2-6 — met; outcomes equal.** R1 empty repair at home q0 and at the frozen alternative start (π/2, −π/2, −π/2), with identical object geometry, are both POSITIVE, so Δ = 0. Both outcomes are independently decided; they do not differ.

**Unmet additional requirements:** none by the stated case criteria, apart from the qualifications above: the R2 contrast and chain, and the R5 interaction, are undecided.

---

## 8. Figures (from saved evidence; provenance and status written on every panel)

**Panel conventions (A, B, C, F).**
- Grey discs are obstacles; t0 (orange) is the target; the red dashed circle is the goal cell.
- Dashed circles are ghosts (proposed poses of the same object), and numbered dashed arrows give the action order.
- Thin blue curves are **recorded** carried paths; the orange curve is the **recorded** target transport; the faint arm is the target record's retreat end.
- Tags read NEW V2 | POSITIVE/NEGATIVE/UNKNOWN, and the box gives the deciding certificate or the normalized reason, the stop and the CPU.

| Figure | What it shows |
|---|---|
| [`A_order_contrast.png`](../runs/g4d_evidence/A_order_contrast.png) | The same endpoints under both orders for R4 (POSITIVE vs NEGATIVE ORDER_FIRST_ACTION) and for R2 (UNKNOWN vs NEGATIVE) |
| [`B_scene_effects.png`](../runs/g4d_evidence/B_scene_effects.png) | Baselines for R2 (NEGATIVE) and R5 (UNKNOWN), and the substitutions at the fixed initial robot state, each titled with its Δ (decided or masked) |
| [`C_omissions.png`](../runs/g4d_evidence/C_omissions.png) | The full R4 repair, its three omissions (omitted objects drawn at their initial poses), Δ per panel, and the derived-legacy summary |
| [`D_joint_continuity.png`](../runs/g4d_evidence/D_joint_continuity.png) | q0–q2 against waypoint index for the new two-move witness. Dashed lines are record boundaries (end q equals next start q bit-exactly); the dotted target record is excluded from J. |
| [`E_endpoint_vs_joint_travel.png`](../runs/g4d_evidence/E_endpoint_vs_joint_travel.png) | Left: the new V2 cost labels (C_d against measured J). Right: the legacy diagnostic, plotted separately and labelled not-a-V2-label. |
| [`F_robot_start.png`](../runs/g4d_evidence/F_robot_start.png) | R1 at home vs the alternative start, with identical objects, each with its recorded target path |
| [`G_unit_ledger.png`](../runs/g4d_evidence/G_unit_ledger.png) | Every unit's stop, label, CPU, wall, calls and deciding reason |

---

## 9. Files changed and why

Line counts are total / logical.

| File | Change | Lines |
|---|---|---|
| `ordered.py` | Event-contract audit; recorded target invocations; staged teacher with checkpoint hook and parse contract; `normalized_reason`; `state_record` | 289 / 255 |
| `verify.py` | `plan_fixed_order` per-call allowance and charging | 425 / 365 |
| `sequences.py` | `parse_sequence`, strict `canonical`, `scene_hash` context identity | 174 / 146 |
| `effects.py` | `context_identity`; `omission_records(query, …, evidence)` | 155 / 129 |
| `skill.py` | `SkillResult.termination` and its events (status and reason unchanged) | 359 / 311 |
| `evaluate.py` | `on_witness` hook before HOME; termination and unresolved-connector count in the target record | 307 / 277 |
| `legacy.py` (new; code moved from `g4d.py`) | Scope checks, positive replay, negative reconstruction and recheck, contradictions, omission pairs, two-move accounting | 244 / 218 |
| `g4d.py` | Legacy functions moved out; `legacy_audit` delegates to the corrected path | 294 / 264 |
| `g4d_run.py` (new) | Final plan, worker, guarded resumable scheduler, checkpoint revalidation | 312 / 274 |
| `g4d_gate.py` (new) | Commands, evidence assembly, judgement, recursive manifest | 269 / 235 |
| `g4d_evidence_figures.py` (new) | Figures A–G | 204 / 185 |
| `run.py` | Four subcommands | 143 / 132 |
| `docs/addenda/A2_termination_reasons_v1.md` (new) | Reason correction | — |
| `tests/test_g4d_corrections.py`, `tests/test_g4d_run.py` (new); `tests/test_g4d.py` (2 assertions updated to the corrected API) | Checks | — |

`verify.py` (365 logical lines) and `skill.py` (311) remain above the review trigger. I did not split them arbitrarily.

**Compatibility.** `config.toml` and every V1 hash are unchanged. V1 `realize` and `plan_repair` are untouched. `primary_episode` without `planner` behaves as before. The new `SkillResult` field and the evaluator outputs are additive. All replays pass.

---

## 10. Separation of claims

- **Software correctness:** 135 tests, the reproduced defects fixed, and the runner tested with synthetic and real units.
- **Evidence readiness:** G4D's five blocking requirements pass on **sparse, hand-designed development scenes**: 20 units and 133.8 CPU-s. That does not make the evidence sufficient for training. G4C's data-readiness thresholds are a separate, unexecuted gate.
- **Learned performance:** none. No model, GRU, sampler or learning objective exists.

The one-shot primary V2 episode was not part of the collection plan, which contains only teacher units. Its corrected audit is verified by tests only.

---

## 11. Next dependency

**G4B** (exact sampler checks on tiny sequence spaces) needs your go-ahead and its own stage plan. I did not start it.

Before scaling, the open evidence items are:
- the undecided R2 contrast and chain;
- the R5 baseline;
- the 29 archived "target-budget" unknowns, which still need re-planning to be re-split (addendum A2).

---

## Repository synchronization

Before committing I checked for secrets and looked at the diff. The commit contains:
- the code and tests in §9;
- addendum A2;
- `runs/g4d_evidence/` (about 1.7 MB);
- this report.

It is pushed to `main` without force. Your untracked instruction file and PDF copies in `instruction-phase-md/` are left untouched and uncommitted. The commit hash is given in chat and recorded in report 0012.
