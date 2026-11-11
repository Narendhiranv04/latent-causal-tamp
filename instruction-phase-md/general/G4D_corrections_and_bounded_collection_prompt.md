# G4D corrections, evidence recovery and bounded collection

Continue the latent causal TAMP project from its actual current repository state. Complete the focused G4D corrections below, recover valid evidence from the archives, implement and test the collection runner, then execute the bounded sparse G4D plan. Stop after the G4D report. This is not an architecture redesign or permission to begin G4B, G4C, training, bulk generation, 3D or hardware.

This instruction authorizes the corrections, focused tests, legacy evidence revalidation and the numerical collection envelope below once all prerequisites pass. Do not ask again for those budget numbers or routine implementation decisions. If a correctness blocker remains, stop collection, preserve the completed work and report the exact blocker. Do not relax the experiment to obtain a pass.

## 1. Establish the current state

Read applicable repository instructions, Methodology v1.6, Implementation Guide v1.8, addendum A1, reports 0009 and 0010, and the existing G4D migration outputs. Use `Architecture_Explained_Step_by_Step.md` if supplied; if absent, use the current methodology's explanatory appendices and record the absence without blocking otherwise specified work.

The review examined commit `5011e82398ef275bd4f8cdd99d598f70248bb370` in `Narendhiranv04/latent-causal-tamp`. Verify current HEAD, branch, working tree and remote. Preserve newer work; do not reset to the reviewed commit. Reproduce findings against current code and do not reapply a fix already present.

Keep reports 0001-0010, prior run directories, the pending G4D plan and archived PDFs byte-unchanged. Preserve unrelated and untracked files. Put corrections in a new report/addendum and a new run directory, suggested `runs/g4d_evidence/`. Use the next unused report number. Follow the established repository synchronization authorization; never force-push.

G4A remains NOT_READY_TO_SCALE. Its original 4.56 CPU-hour usage against a 4.0 cap remains historical. Passing G4D does not retroactively pass G4A.

## 2. Correct the four verified implementation issues

### 2.1 Make the episode audit reject invalid event histories

At the reviewed commit, `ordered.episode_audit` returns `boundary_ok=True` for both `COMMIT -> ABORT -> TARGET_EVALUATE` and `COMMIT -> COMMIT -> TARGET_EVALUATE`. It records the violations separately but omits them from the acceptance expression.

Enforce the complete event contract: at most one commitment; at most one primary target invocation; no target before commitment, after abort, or before all committed relocations and successful reobservations. An empty repair legitimately has no relocation events. No-witness and abort episodes may be protocol-compliant while remaining unsuccessful; distinguish those concepts.

Keep order equality, actual motion continuity, achieved-state validation and target-start equality as explicit checks. Add an overall audit decision requiring all applicable checks. Missing evidence must be unknown or a failure, not a vacuous pass. Validate the actual target invocation against the achieved state even if no target trajectory is returned. Verify object poses and identity as well as joints and gripper state. Add mutation tests for illegal event sequences and a valid empty-repair episode.

### 2.2 Enforce relocation-call budgets during the sequence

`verify.plan_fixed_order` checks the cap only before calling `realize`. With a cap of 10, 9 calls already used and a three-action sequence, its accounting can reach 12.

Enforce the remaining allowance before every actual relocation-planning invocation. Count attempted calls, including failures, consistently; do not charge a reused result as a new planner call. An interrupted sequence is unresolved and is not a complete witness or cost label. Preserve achieved partial records as diagnostics. Test near-cap, exact-cap and empty-sequence behavior. Keep V1 compatibility scoped; do not silently reinterpret archived counts.

### 2.3 Validate raw proposals before canonicalization

`ordered.teach_sequence` calls `sequences.canonical` before validation. The latter uses `int(d)`, so `True` and `1.9` can both become cell 1 and pass validation.

Validate raw shape, object-ID type and destination type before conversion. Canonicalization must not change the requested action. Reject booleans, fractional values, malformed pairs, duplicate objects, stay entries, forbidden targets and over-cap sequences at the public entry points. Use one clear validation contract across ranking and teaching. Test those entry points, not only the validator directly.

### 2.4 Revalidate transferred negative certificates

The negative branch of `g4d.legacy_audit` currently trusts archived `checker_accepted` plus the certificate-kind scope map. A record with mismatched observation/action hashes or assignment can still transfer. The reviewed code therefore does not establish the scope validation claimed in report 0010.

Reconstruct each certificate's actual scene, assignment and action context. Check identities, target, robot profile, grasp family, contact rules, tolerances, move-once and end policy. Run the independent checker on each certificate used for transfer and record the new verdict and reasons. Do not use an archived acceptance boolean as a substitute for this check.

Preserve original labels. A transfer failure becomes rejected/unresolved in the new migration output; an actual positive/negative contradiction blocks downstream collection until resolved. Test mismatched hashes, assignment and policy. Do not claim that the original 86 negatives were unsound merely because the migration lacked these checks.

## 3. Repair reason reporting and evidence provenance

Correct the prospective failure-reason ambiguity where `PLANNER_BUDGET` is returned after the declared enumeration has finished. Distinguish actual search limits, completed schedules without a witness, connector failures, CPU censoring and wall censoring using explicit termination events. All remain unresolved unless an independent, scope-matching proof establishes a negative.

Preserve historical outputs and raw reason strings. Add normalized V2 reasons if necessary for compatibility. Explain in a new addendum that the earlier count of 29 target-budget outcomes was based on recorded reason codes that report 0009 subsequently questioned. Do not edit archived reports or PDFs to hide that correction.

Bind every explanation comparison to the complete query and source evidence: initial observation, action context, protocol/schema, robot state/profile, ordered proposal or intervention, appearance anchor and evidence identifiers. `omission_records` currently hashes only the sequence; that is not a complete context identity. Identical sequences in different scenes or robot states must remain distinct. The frozen pool's context identity must likewise include all relevant initial robot and scene fields.

Keep scene effects, omission effects, robot-start comparisons and deletion diagnostics separate. Preserve anchored appearance and recompute structured geometric features from substituted poses. Mask effects when either side is unknown or the comparison is ineligible. Keep necessity and minimum-repair claims unasserted without supporting proofs.

## 4. Recover existing omission evidence before new planning

The committed legacy audit contains 25 candidate positive-versus-negative omission comparisons across six roots when omissions are restricted to one or two actions. This was a record-matching observation, not independent verification of those labels and not a target count you must reproduce.

Example: on `g4a_r02`, audit index 2 records the positive sequence `o00->41, o07->42`; omitting `o00->41` leaves `o07->42`, whose assignment at audit index 9 has an archived GOAL_OVERLAP negative. Revalidate both sides and their shared context before deriving an effect of +1.

Enumerate compatible omission pairs deterministically from the revalidated records. Preserve the remaining action order. An assignment-wide negative can cover the remaining order; a positive transfers only to its exact witnessed order. Record source hashes, checked evidence, omitted positions and effect sign. Keep multiple valid alternatives and report unique roots separately from pair counts. Do not convert the 25 candidates automatically into accepted labels or claim they are independent examples.

Mark accepted records as derived legacy evidence, never newly collected V2 evidence. Legacy joint-travel values remain diagnostic under their original backend, not V2 first-witness cost labels.

Explicitly account for the ten reported exact two-move positive sequences: after validation, determine whether they meet the general two-move-witness requirement under the same scope-based reuse policy used for D-V2-0. They cannot replace the missing same-endpoint order contrast. Do not alter the frozen sparse units based on this recovery.

## 5. Implement and test the runner before collection

Implement `g4d-run` using the existing guard and the smallest cohesive changes. Numerical limits are configuration, not a reason to postpone runner implementation. Avoid arbitrary file splitting to satisfy the approximate 300-line review trigger.

Test orchestration with synthetic workers: CPU cancellation, wall cancellation, child-process accounting, aggregate admission, nonzero exit, incomplete checkpoint, resume and preservation of completed evidence. Use temporary directories. These are correctness tests, not scientific labels or new root collection.

Use atomic evidence checkpoints. Persist independently accepted certificates and complete relocation witnesses/costs before starting target work. Persist a checked target-plus-safe-retreat witness before optional HOME diagnostics. Cancellation later must not erase already complete evidence. If the existing evaluator cannot expose that checkpoint, introduce a minimal hook or explicitly disable the optional HOME diagnostic in the new, frozen collection overlay. Never mutate the V1 configuration silently.

Keep evidence status separate from process stop status: a CPU-censored unit can retain a previously verified certificate or relocation-cost label. Partial trajectories do not count as witnesses. Revalidate completed checkpoints before reuse.

## 6. Finalize the execution plan and resource envelope

Preserve `runs/g4d_migration/g4d_plan.json` with its pending-budget status. Create a linked final execution plan after corrections and runner tests. Retain its 20 units, roots, sequences, interventions, seed keys, execution order and action/search policies. Do not replace roots or destinations based on expected success.

The authorized limits for this collection are:

- Per-unit CPU: **900 seconds**, cancellation trigger at **870 seconds**.
- Aggregate collection CPU: **18,000 seconds (5 CPU-hours)**.
- Planning workers: **1**; constrain internal numerical-library threading.
- Per-unit wall guard: **1,800 seconds**.
- Overall collection wall guard: **21,600 seconds (6 hours)**.
- CPU cancellation margin: **30 seconds**; record actual overshoot and polling settings.

Count unit initialization, certificate screens, relocation planning, target planning, validation and optional planning diagnostics inside the collection envelope, including descendants and coordinating work. Measure legacy revalidation, software tests and report generation separately; they must not conceal extra experimental planning.

Admit a unit only when spent CPU plus its full cap and the declared orchestration reserve fit within the aggregate cap. Apply the smaller of the unit wall allowance and remaining global wall allowance. Stop and report if enforcement is unreliable or the cap is exceeded. Do not raise limits automatically.

Keep the declared search schedule unchanged: the existing 4,000-node setting, relocation/target failure allowances, grasp family, collision margins, tolerances and supported-transport action domain. CPU ceilings are not permission to increase deterministic search effort.

Bind the final plan to the reviewed source state, runner, guard, configuration loading, scene construction and checking dependencies, and both normative documents. Verify hashes before work. A recorded commit plus a complete relevant source manifest is sufficient; no elaborate build system is needed. Record the relationship to the pending plan and why hashes changed.

The 20 units permit at most 13 relocation-skill planning calls and 20 target evaluations under the frozen plan. Count realized calls explicitly; accepted certificates can skip target calls. Do not rerun a completed or censored unit to seek a better outcome. Resume only work that was never started, using the same persisted aggregate budget and original collection wall deadline. An ambiguous interrupted unit is recorded as such, not automatically repeated.

## 7. Collect, judge the gate and visualize the evidence

After all correctness prerequisites pass, execute the final plan within the limits above. Do not ask again for approval of this explicitly bounded collection. Keep every unit in the ledger, including UNKNOWN, INELIGIBLE, ERROR and NOT_RUN_BUDGET outcomes.

Retain the guide's blocking requirements:

- A complete checked nonempty two-move sequence, with the source of any accepted legacy reuse explicit.
- A decided same-endpoint order contrast: one complete positive and one independently accepted order-wide negative.
- A decided eligible scene-effect pair.
- A decided omission pair, with derived legacy and new V2 evidence counted separately.
- Joint continuity, actual achieved-state consistency and target-start equality for every claimed complete witness.

Report D-V2-0 through D-V2-6 individually. A zero-effect pair is not evidence of the non-additive interaction intended by D-V2-4. Report singleton and joint outcomes; do not force an interaction. D-V2-5 needs the specified complete relocation-cost alternatives. D-V2-6 needs independently decided outcomes at valid robot starts; differing outcomes are desirable, not fabricated requirements.

The five blocking checks are the minimum gate decision. Report any unmet additional case requirements separately and do not label the entire evidence suite complete merely because those five checks pass. A timeout never establishes a bad order. A successful scene edit never proves the robot can execute that edit. No learned model exists at this stage.

Produce scene-based figures from saved evidence: the same endpoints under different orders; baseline versus scene intervention at fixed robot state; full repair versus omissions; actual joint continuity; endpoint displacement versus measured joint travel; and the robot-start comparison. Label legacy, new, unknown and not-run panels distinctly. Explain arrows and quantities. Show failed or unresolved cases rather than hiding them.

## 8. Deliver and stop

Write the next report with starting/ending revisions, reproduced defects and fixes, targeted test results, required compatibility replays, new negative-transfer verdicts, accepted/rejected legacy omission counts, final plan hash, per-unit CPU/wall/stop reason, checkpoint evidence, actual call counts and every D-V2 outcome.

Separate software correctness, evidence readiness and learned performance. Keep the full robot, ghost placements, order variables and one-shot target boundary intact. Do not add a GRU, Boltzmann sampler or new learning objective during this correction stage.

Report G4D PASS or BLOCKED against the stated requirements and the exact next dependency. Finish the established commit/push workflow without force, report HEAD and remaining worktree changes, and stop before G4B. Do not start more phases simply because the run finishes early.
