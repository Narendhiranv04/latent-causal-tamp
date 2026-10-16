# G4A — Evidence audit, automatic candidates and bounded data-readiness study

**Instruction version:** 1.0 — 16 October 2026  
**Previous stage:** G3.5, report `0007_G3_5_completion.md`  
**Reported starting commit:** `a2727e4563f4fcfd05fd7f492c5628c4e709daef` on `main`; verify the actual state before work  
**Next report:** `responses-phases/0008_G4A_completion.md`  
**Normative references:** Methodology Specification v1.5; Implementation Guide v1.7  
**Authorized implementation scope:** G4A only. Complete the hardening and bounded audit below. No 300/1,000-root expansion, G4B sampler work, G5 learning, 3D implementation or hardware execution.

## 1. Purpose and scientific boundary

G3.5 established the new interface with hand-authored candidates and full-3R kinematic evidence. It did not establish an automatic proposal method, sufficient training data, planner-seed reliability or broad action-level negative supervision.

G4A must answer:

1. Are the new impossibility certificates sound and independently checkable?
2. Can an automatic candidate generator use only initial allowed inputs and produce useful repair alternatives?
3. How often do finite teacher searches resolve those candidates, at what cost, and with what seed/order sensitivity?
4. Is the resulting evidence broad enough to justify the next development stage?

Preserve `INITIAL_SCENE_ONE_SHOT_V1`: proposals use initial scene/object geometry, robot state and action/goal; no trajectory or swept-volume inputs. External relocation planning may search candidate orders before commitment. The target evaluator runs after the committed repair completes; its result does not select another repair in the same primary episode.

The **offline teacher** is separately allowed to evaluate multiple assignments, orders and target seeds. Those outcomes generate supervision and diagnostics; they must not leak into the automatic candidate generator or the primary selection policy.

Do not describe automatic geometric proposals as learned intelligence. Do not describe kinematic replay as simulation dynamics or hardware execution.

## 2. Inspect the repository and preserve evidence

Read repository instructions, reports 0001–0007, the G3.5 instruction, both current PDFs, and relevant source/config/tests. Inspect the actual working tree before making changes. The attached report is evidence to verify, not a substitute for inspecting code.

- Record current branch/commit, dirty files, robot/config hashes and archived run hashes.
- Preserve all G0–G3.5 run data and reports byte-for-byte. New evaluations of old cases get new records and output paths.
- Keep the tested robot, home, gripper/contact conventions and 48-candidate grasp family. Do not reset to provisional values from older PDFs.
- Retain `FROZEN_CONTROL`, including its original connector and replay semantics.
- Use `runs/g4a_evidence_audit/` with a flat set of per-case files and machine-readable records.
- The current report says there is no `AGENTS.md` or `CLAUDE.md`; check again rather than assuming this remains true.

### Resolve the two administrative items

**Historical PDFs:** preserve the exact tracked v1.4/v1.6 bytes under the repository's existing archive location, or a single `docs/archive/` folder if none exists. If they are currently deleted locally, recover their exact tracked bytes from the appropriate recorded commit for the archive. Keep v1.5/v1.7 clearly marked as current. Update current README links; do not edit immutable historical reports just to change paths. Preserve byte hashes and record the archive move. Do not permanently discard the historical contracts.

**`run.py`:** perform the previously proposed narrow responsibility split. Move stage command bodies into their existing owning modules and retain the CLI/argument/output behaviour. Aim to keep the dispatcher below approximately 280 logical lines; explain any exception. Do not create a framework, generic registry or duplicate module hierarchy. This split is within this instruction's scope and does not need a separate design approval.

## 3. Audit the certificates before using them at scale

Implement an independent checker for each certificate. It may share trusted primitive geometry routines, but must reconstruct the premise from the scene, action, domain and declared grasp/contact rules. It must not simply accept the certificate producer's boolean or reuse its final decision without recomputation.

### 3.1 Mandatory-goal-overlap certificate

For each claimed unavoidable overlap, verify:

- The goal pose/region and allowed target orientation are represented exactly; do not assume a unique pose when the action admits alternatives.
- Target and obstacle geometry, margin, numerical band, goal tolerance and achieved obstacle tolerance are included conservatively.
- The proof excludes all tolerated final placements under the declared goal and obstacle assignment. If a tolerance region includes a valid clearance, reject the certificate.
- The obstacle cannot move by unmodelled pushing/contact, and the target cannot execute intermediate actions before the repair completes.
- The object identity, target identity, state/action hashes and proof scope match the evaluated assignment.

For an obstacle required to stay, use the declared state uncertainty rather than inventing a relocation tolerance. For a moved obstacle, use the declared achieved endpoint tolerance. The bound must reflect the actual semantics and remain conservative.

Test close-to-margin cases, overlapping versus nonoverlapping goal tolerances, goal regions with an escape pose, stale object/goal IDs, altered radii and altered contact rules. A certificate must fail validation when one of its necessary premises is removed.

### 3.2 First-mover certificate and R4 bound

An assignment-wide first-mover certificate needs to exclude **every selected object as the first legal relocation**. One failed order or one exhausted motion search is insufficient.

Check that each excluded first move has a definite pick/place obstruction covering all declared grasp candidates, including the allowed approach/closure phases. The rejecting condition must depend only on the unchanged scene/object poses and declared skill restrictions, not on an arbitrary current arm start or one attempted RRT connector. Free arm repositioning without moving obstacles must not invalidate the purported impossibility argument.

Recheck G3.5's scoped lower bound of two: the goal occupant must move, it cannot be picked first under the full declared skill family, and another obstacle must therefore move before it. A complete two-move repair-plus-target witness closes the bound. Do not generalize it beyond the permitted actions and grasp family.

Add adversarial tests: one selected object actually can go first; one grasp was accidentally omitted; failure is caused only by a start-dependent connector; a planner timeout is supplied as a certificate; an assignment is changed after certificate production. Reject each unsound proof.

If an existing certificate is unsound, stop using it for new labels. Document an erratum and recompute affected new evidence. Preserve report 0007 and its original files as historical records, with an explicit correction linked from the current README/report.

## 4. Define target completion and exercise abort behaviour

### 4.1 Separate target goal, safe retreat and return HOME

G3.5's target action included a final HOME connector. For new G4A queries, use the following explicit contract:

- Primary complete target success requires approach, valid grasp/transport, release at the required goal, and a checked safe retreat with valid final robot/gripper state.
- Return to a designated HOME configuration is an optional separately checked diagnostic, not an implicit prerequisite for this transport task.
- Record `goal_achieved`, `safe_retreat_status`, `home_return_status` and `complete_target_status` separately.
- Do not report complete target success merely because placement occurred if the required safe retreat failed.

Represent the end-state policy in the action context/config and its hash. Add a short versioned repository addendum describing this refinement of the general action contract. Do not silently relabel G3.5's HOME-constrained records or modify the old PDFs in place. If comparing old/new end policies, use separately identified cloned-state evaluations with their exact scopes.

The backend must return an independently checked complete through-retreat witness for primary success. Do not infer success by truncating an incomplete or unverified failed planning record. Preserve the target's achieved final state for any optional HOME diagnostic.

### 4.2 Controlled execution-deviation test

Inject a known achieved-state perturbation after a committed relocation in a controlled test adapter. Test at least:

1. An object-pose deviation exceeding the declared placement tolerance.
2. An inconsistent gripper/attachment state or object identity.

Require an explicit `ABORT`, no refreshed proposal or changed destination, no second relocation performed under invalid assumptions, and no target evaluation after the invalid repair. Also test an admissible within-tolerance deviation if the checker claims tolerance support.

This is a fault-injection test, not measured physical robustness. Label its plots accordingly. Preserve the immutable initial observation/proposal hashes and record the commanded versus injected/achieved state.

## 5. Automatic candidate generation from permitted inputs

Replace the hand-authored per-query lists for **new** G4A queries. Keep the historical manual provider only for archived replay and explicit controls.

The generator receives only the same allowlisted initial scene/robot/action/goal/candidate interface intended for the learner. It may use explicit geometry, legal cells, static overlap checks and deterministic geometric heuristics. It must not read:

- Reference trajectories/envelopes, old blocker labels or known repair destinations.
- Target-planner outcomes, candidate label records, successful teacher traces or audit results.
- Root/family names, fixture-specific object IDs, episode-key outcomes or construction histories.
- IK/pick-certificate outputs as a hidden proposal feature. Those belong to the external executor or offline evidence audit in this initial B1-style generator.

Generate a bounded diverse set containing:

- All-stay.
- Single-object moves to multiple supported destinations.
- Joint two-object moves, including an occupied-destination chain where its occupant moves elsewhere.
- Some three-object assignments for indirect access/placement dependencies.
- Candidates involving objects other than the immediate goal occupant, rather than limiting selection to a preidentified blocker set.

Use stable deterministic geometry-based ordering and a separate recorded seed for any diversity sampling. Do not depend on storage slot order. Prefer a mixture of task-proximal and broad scene candidates so the audit can reveal whether the heuristic is too narrow. State the exact rule and its limitations.

Screen whole-assignment static geometry; assigning a moved object to another object's current cell can be valid if that other object is assigned elsewhere. Do not reject such joint candidates solely because the destination is occupied initially. Deduplicate physical endpoint assignments, including duplicate stay representations.

Freeze a primary ranking policy before teacher outcomes are available. No per-query hand edits after inspecting success. If a generator bug is corrected, version it, rerun the entire declared audit batch and preserve the earlier result as superseded evidence.

Test reference-field poisoning, goal sensitivity and object/candidate permutation behaviour. Undo the permutation when comparing physical assignments; tied candidate ordering may vary only under a documented tie policy, not change the intended admissible proposal set through object IDs.

## 6. Predeclare a bounded audit population and costs

Write and hash `g4a_plan.json` before collecting target outcomes. The settings below are engineering readiness targets, not statistical guarantees or established optimal sample sizes.

### Main audit limits

| Item | Default cap / rule |
|---|---|
| New independently sampled roots | 20 total; all tagged DEVELOPMENT_ONLY |
| Obstacles per root | 4–8, using the tested full-3R profile |
| Action queries per root | At most 2; all descendants share the root |
| Automatic candidate assignments | At most 12 unique static-valid assignments per query, including all-stay when valid |
| Moved objects per assignment | At most 3 for this sparse audit; state this domain restriction |
| Raw candidate proposals | At most 120 per query; retain rejection/dedup counts |
| First-pass teacher target evaluations | At most 1 per candidate after an executable relocation order is found |
| Root construction attempts | At most 100; retain every attempted seed and rejection reason |
| Additional diagnostic target invocations | At most 120 total across seed/order/end-policy diagnostics |

Separately keep a small fixed invalid-endpoint control pool. Do not fill the main static-valid pool with trivial invalid assignments to improve the apparent decided-label fraction. If fewer than 12 static-valid candidates exist or are proposed, report the actual count without outcome-based backfilling.

Use five construction strata, aiming for four independent roots each: unoccupied goals with varied transport geometry; occupied goals; access-dependency layouts; competing/occupied relocation destinations; and nuisance-object/control variations. These are intended construction categories, not ground-truth feasibility labels. Sample geometry independently; re-renderings or alternate goals of one layout are siblings, not new roots.

Freeze existing tested per-query node/evaluation caps for the first pass. Record every wall-time safety cap and cap hit. Use a predeclared aggregate limit of 4 CPU-hours for the main audit and 2 CPU-hours for diagnostics, with at most 8 workers. If resource availability requires lower caps, record them before collection. Do not silently raise limits to obtain passing outcomes. On exhaustion, save partial evidence and report incomplete readiness.

Start with four roots, one from each of the first four strata, to check construction, schemas and cost. Continue to the planned 20 only if no correctness fault is found. Do not select the easiest roots based on target success or replace unresolved roots without retaining them in the audit accounting.

The 20 roots are development evidence, not the future held-out test set. Do not reuse them as unbiased test roots in the later 300-root pilot. Preserve root lineage for any future train/validation use.

## 7. Offline teacher labels and outcome aggregation

For each frozen candidate assignment:

1. Record independent static factors and all relevant evidence.
2. Attempt legal move-once relocation orders from a clone of the same initial state, under the declared budget.
3. For the first fully verified relocation witness, evaluate the complete target from its exact achieved state.
4. A complete repair-plus-target witness establishes a positive. A validated assignment-wide certificate establishes a negative. Everything else remains unknown.

Keep specific-attempt results separate from aggregate assignment evidence. One positive witness establishes existential feasibility even if other seeds/orders fail. A validated impossibility certificate and a positive witness for the same scope/state are a contradiction that must halt affected labeling until resolved.

Use distinct negative sources: static-invalid; unavoidable-goal-overlap; first-mover/access certificate; other sound certificate with a documented checker. No path-level negative may be inferred from finite sampling exhaustion. Do not call unsuccessful attempted orders assignment-wide negatives.

Store the operational finite-budget success flag separately. Unknown episodes remain in the operational success denominator and contribute no success. They are excluded from binary feasibility losses and, later, from the decided pool's joint-softmax denominator. Implement/test label-mask helpers now without building or training a model.

Record both first-pass evidence and diagnostic-enriched evidence. Extra seeds or orders may produce more positives; do not overwrite the first-pass unknown rate or hide their extra cost. A later positive upgrades the aggregate existential label while retaining every earlier attempt.

## 8. Measure seed and final-order sensitivity separately

### 8.1 Target-planner seed panel

Select up to 12 query/assignment cases by a predeclared stratified, stable-hash rule from the audit inputs, without inspecting target outcomes. Include all-stay and nonempty candidates. For nonempty candidates, a verified relocation witness is needed to define an achieved target-start state; if unavailable, retain the missing panel entry rather than silently choosing an easier case.

For each available case, hold the achieved state bit-identical and run five predetermined target seeds with identical budgets. Save each result, runtime, node/evaluation counts and witness. Report witnessed-success counts out of five and cases whose result changes across seeds. These are empirical finite-planner outcomes, not ground-truth feasibility probabilities or five independent scene roots.

The positive/negative/unknown proportions of this small panel do not estimate the whole scene distribution. Pair comparisons on the same fixed states and show raw observations.

### 8.2 Relocation-order panel

Select up to six multi-object assignments using a rule fixed before target evaluation. Attempt up to three distinct executable orders under the declared order-search cap. For each achieved end state, run the same two predetermined target seeds. Keep all unexecutable/unresolved orders in the table.

Report how many additional assignment positives are found beyond the first executable order and at what cost. Track final joint/gripper states and endpoint tolerances. If both final object poses and robot states differ, report both; do not attribute the entire effect to joint configuration alone.

All of this is `OFFLINE_CASE_AUDIT`. The primary episode still commits once and does not use target feedback to change its repair. Budgeted diagnostics may stop early at the aggregate cap; report missing entries honestly.

## 9. Coverage targets and readiness decision

Report coverage over all attempted roots, all eligible queries, all generated candidates and all static-valid audited assignments. Repeated seeds or repeated orders do not increase the count of distinct assignments or roots.

Predeclared targets for this 20-root development audit:

| Criterion | Target |
|---|---|
| Root/candidate audit complete | 20 independent valid roots, or explicit BLOCKED/INCOMPLETE result with attempted-root ledger |
| Zero-move complete witnesses | At least 6 distinct roots |
| Nonempty complete repair witnesses | At least 8 distinct roots; do not infer that the repair was necessary |
| Alternative sufficient assignments for the same query | At least 4 distinct roots |
| Static-valid certified goal negatives | At least 3 distinct roots |
| Static-valid access/first-mover negatives beyond goal overlap | At least 3 distinct roots, independently checked |
| Distinct candidate signatures per multi-alternative query | At least 2 genuinely different physical endpoint assignments, not reordered records |
| First-pass unknown fraction among static-valid audited assignments | Target at most 50%; also report enriched fraction and additional cost |
| Semantic/protocol failures | Zero: no false certificates, label leakage, target-feedback selection or corrupted archives |

The nonempty witness group can overlap the zero-move group; in that case the relocation was unnecessary for that query. Separately report nonempty witnesses on certified-initially-infeasible and initially-unresolved queries. This prevents the first two targets from being mistaken for evidence that repair is needed.

The 50% unknown target is a practical throughput/data-usefulness threshold, not a mathematical truth or permission to discard unknowns. If coverage is inadequate, report `NOT_READY_TO_SCALE`, describe the failed strata and propose one concrete generator/evaluator improvement. Do not weaken thresholds after seeing outcomes or fabricate negative labels.

Even if these targets pass, explicitly state whether negative supervision remains limited to goal occupancy and finite-grasp access. Passing this gate does not establish learning of general free-space connectivity or prove the absence of alternate paths. The next review decides G4B and later expansion; neither is automatically executed here.

## 10. Visualizations and machine-readable deliverables

Use recorded full-robot states and paths, fixed axes and clear status labels. Clean observation images remain separate from overlays. Store at least:

- `A_certificate_audit.png`: accepted/rejected proof premises, margin/tolerance cases and R4 scope.
- `B_automatic_candidates.png`: scene, goal, algorithmic candidates before teacher evaluation, followed by separately labelled oracle statuses.
- `C_label_coverage.png`: root/query/candidate counts, negative sources, first-pass and enriched unknown rates by stratum.
- `D_seed_variance.png`: five-seed result/time matrix on fixed achieved states; missing entries visible.
- `E_order_end_states.png`: same assignment, alternative order end states and target outcomes.
- `F_abort_injection.png`: commanded versus perturbed state, abort and forbidden-follow-up-call checks; label FAULT-INJECTION TEST.
- `G_target_completion.png`: goal achievement, safe retreat and optional HOME status, with old/new action-scope labels.
- `H_primary_call_trace.png`: commitment and target-call boundary for actual automatic-proposal episodes.
- At least two actual repair-plus-target GIFs from distinct new roots if witnesses exist; no invented paths for missing witnesses.

Machine-readable files: `g4a_plan.json`, resolved `config.json`, `manifest.json`, root-attempt ledger, candidate/label records, certificate-check results, primary episode records, seed/order panel results, metrics, and trajectory arrays. Use a flat run directory, not per-frame subfolders. Record scope/config/robot/action/observation/proposal hashes and all budget changes.

Do not claim a plot proves more than the records beneath it. A model-score plot is inappropriate here because there is no trained model.

## 11. Targeted verification and regression

Required checks cover:

1. Independent certificate checker rejects invalid premises and stale scope.
2. Tolerance-aware occupancy proof cannot certify a goal region with a valid alternative.
3. First-mover proof checks all selected movers and all declared grasps, without start-dependent planner shortcuts.
4. Target completion requires safe retreat; optional HOME failure does not erase a through-retreat witness.
5. Injected execution deviation causes abort and no forbidden subsequent motion/target/proposal call.
6. Automatic candidates depend only on allowlisted initial inputs; poisoned/deleted oracle fields do not change them.
7. Permutation and physical candidate mapping are consistent; IDs do not become geometric features.
8. Positive/negative/unknown masks and aggregate evidence logic are correct, including contradiction detection.
9. Target-seed panel holds achieved state and search budget fixed.
10. Primary episodes do not adopt the offline teacher's successful candidate/order based on target outcomes.
11. `run.py` refactor preserves existing CLI and relevant archive replay behaviour.

Run applicable existing tests/replays and inspect archive hashes. Add mutation checks for the high-risk proof/label/protocol decisions if useful; do not make mutation count a substitute for actual planning evidence. Stop additional testing once these concrete risks and required gates are resolved.

## 12. Completion report and stopping rule

Write `responses-phases/0008_G4A_completion.md` with:

- Exact scope, starting/current commit and reviewed source versions.
- Certificate audit conclusions, fixes and any historical erratum.
- Target-end-policy addendum and separate HOME metrics.
- Automatic candidate algorithm, input allowlist, ranking and limitations.
- Frozen audit plan, all attempted/accepted roots and actual candidate counts.
- First-pass versus diagnostic-enriched labels and unknown rates.
- Seed/order sensitivity with complete cost accounting.
- Controlled abort evidence, tests, archive checks and refactor summary.
- All required visuals/data paths and files changed with logical line counts.
- Each readiness target marked PASS, BLOCKED or NOT_ATTEMPTED with evidence.
- A recommendation for the next stage based on measured coverage and cost.

Follow the established repository workflow for numbered reports, commit/push and remote verification where already authorized. Preserve unrelated working-tree changes. Record synchronization honestly; do not invent a remote match or claim completion of unrun work.

**Stop after G4A.** No 300/1,000-root generation, Gibbs/global-energy implementation, neural training, 3D build or hardware action is part of this instruction. A failed readiness target is a useful result to report, not a reason to change scientific definitions or continue into the next stage.
