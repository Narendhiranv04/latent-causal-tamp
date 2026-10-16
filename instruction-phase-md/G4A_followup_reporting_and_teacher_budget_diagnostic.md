# G4A follow-up: reporting reconciliation and bounded offline teacher diagnostic

## 1. Objective and stopping boundary

Complete a narrow follow-up to `responses-phases/0008_G4A_completion.md`. Resolve the reporting ambiguities against saved evidence, then test whether additional offline target-planning effort produces zero-move witnesses for the three frozen budget-limited roots.

This is **G4A follow-up only**. Do not start G4B, learned proposal search, model training, bulk data generation, 300/1,000-root expansion, 3D, or hardware work. Do not redesign the Boltzmann energy architecture in this stage.

The original G4A audit remains `NOT_READY_TO_SCALE`. New evidence must be reported as a separate teacher-schedule variant. Do not overwrite the original first-pass results or retroactively claim that its resource cap was met.

The attached handoff prompt authorizes the bounded work below. Do not repeatedly request approval for routine fixes, tests, visualizations or the explicitly bounded diagnostic. Stop and report if a necessary change exceeds this scope or cannot be performed within the limits.

## 2. Read and establish the actual repository state

Before edits, read:

1. Applicable `AGENTS.md` and `CLAUDE.md`, if present.
2. Current methodology v1.5 and implementation guide v1.7, or their explicitly documented successors.
3. `docs/addenda/A1_target_end_policy_v1.md`.
4. `instruction-phase-md/G4A_evidence_audit_and_automatic_candidates.md`.
5. Reports 0007 and 0008 and the G4A frozen plan, configuration, labels, episodes and diagnostic records.
6. The relevant target evaluator, planner, evidence checker, audit and coverage code.

The v1.4/v1.6 PDFs in `docs/archive/` are historical. The older master document does not override the current trajectory-free contracts. If current normative files are absent, complete evidence reconciliation where possible and report the missing dependency before changing planner semantics.

The reported G4A commit is `44679ce67f2ffdf88afdcf3c58e09b48c6dbd76f`. Verify the actual branch, HEAD, remote and working tree. Do not assume this commit is still HEAD, reset newer work, discard local changes, or force-push.

Hash the original G4A run and reports 0001-0008 before changes. Preserve their bytes. Put clarifications in a new report/addendum, with references to the original statements.

## 3. Established observations and the hypothesis under test

These are reported observations to verify against the raw records, not predetermined results to reproduce by changing the experiment:

| Quantity | G4A reported value |
|---|---:|
| Development roots | 20 |
| Candidate assignments | 240 |
| Positive / negative / unknown | 44 / 86 / 110 |
| Zero-move witness roots | 3: r05, r10, r19 |
| Zero-move target | At least 6 roots |
| Primary operational success | 8/20 |
| Main audit CPU | 4.56 CPU-h against 4.0 CPU-h |

Unknowns are reported as 67 relocation-search exhaustion, 29 target-budget exhaustion and 14 other unresolved assignment-level cases. Thus, target-budget exhaustion accounts for 26.4% of unknowns, not the majority. Increasing target budgets cannot directly resolve the 67 assignments lacking a relocation witness.

The narrow hypothesis is:

> With the initial state and action contract fixed, increasing the offline target search allowance may produce complete all-stay witnesses for g4a_r04, g4a_r14 and g4a_r15.

All three would need to become positive to reach six zero-move roots without resolving r09. Do not assume these witnesses exist.

## 4. Reconcile reporting from saved evidence first

### 4.1 Certificate records versus unique negative assignments

The reported certificate counts are 72 GOAL_OVERLAP, 13 TARGET_PICK and 4 FIRST_MOVER, totaling 89 records against 86 negative assignments.

Recompute using stable `(root, action, physical assignment signature)` keys:

- Total accepted certificate records, including any duplicates.
- Unique negative assignments and unique assignments per certificate type.
- Exact certificate-type combinations and their assignment counts.
- Duplicate records separately from distinct certificates on one assignment.

Check that the union matches the negative count. Do not guess that exactly three assignments overlap: 89 versus 86 alone does not identify the overlap structure. Every negative must retain its checker-accepted, scope-matching evidence. Any genuine positive/negative contradiction is a blocker to collection until resolved.

### 4.2 Primary target-call counts

Recompute per-episode calls from traces or instrumentation records. Distinguish offline teacher calls, primary target evaluation, and optional HOME diagnostic calls.

The invariant is **at most one primary target evaluation per episode**:

- Zero before commitment and between relocations.
- Zero after abort or when no repair witness is found.
- One after a successfully completed committed repair, including an all-stay commitment.
- No target-feedback-driven candidate switch.

If the 18 episodes with a completed repair each have one target evaluation and the two no-repair episodes have none, report 18/2 explicitly. Verify rather than imposing these expected counts. If traces lack enough information, mark the historical total unauditable and instrument future runs; do not fabricate events.

### 4.3 CPU-cap claim

Retain 4.56 CPU-h and the 14% overrun. Explain that excluding each expensive root is a sensitivity calculation, not reconstruction of a cap-compliant execution. Without scheduling/completion records, do not claim which root alone crossed the cap or what concurrent work was in flight.

### 4.4 Seed and order claims

Keep all 12 seed-panel entries, including the three NOT_RUN cases. Report that nine ran and only one was target-budget unresolved. Do not generalize this panel into proof that seeds cannot help the unresolved population. Likewise, no new witness in the order panel is a result for that sampled panel only.

## 5. Freeze a separate diagnostic plan

Use a new flat directory, suggested `runs/g4a_teacher_budget_diagnostic/`, and a separately named teacher configuration. Keep deployment configuration and original G4A records unchanged.

Before any new planning outcome, write and hash a plan containing:

- Exactly g4a_r04, g4a_r14 and g4a_r15, each with the original all-stay assignment.
- Exact initial scene, target, goal, robot joints, gripper and attachment state.
- Original action, geometry, collision, uncertainty, grasp-family and SAFE_RETREAT policy hashes.
- Baseline evaluation identifiers, seed, algorithm and relevant configuration values.
- Both diagnostic budget levels, execution order, CPU limits, cancellation policy and stopping rules.
- Code revision or source hash, and any uncommitted diagnostic diff hash.

Use the archived original seed. Each diagnostic evaluation starts independently from the same original state; do not warm-start from a different tier or carry a partial trajectory forward. Retain the declared 48-candidate grasp family and its order. Changing search effort does not authorize changing the action domain.

Verify the three archived all-stay cases actually have the stated budget-limited status. If an ID or premise is wrong, record the discrepancy and stop collection; do not substitute another root based on its apparent likelihood of success.

## 6. Budget schedule and limits

### 6.1 Deterministic work allowances

First trace the actual configuration fields to the code paths they limit. Do not equate a field named `skill_failures` with a pick/place-pair cap without inspecting its semantics.

| Schedule | RRT node allowance | Target pick/place search allowance |
|---|---:|---:|
| B0: archived baseline | Original | Original |
| B1 | 2 times baseline | 2 times baseline |
| B2 | 4 times baseline | 4 times baseline |

If the archived node allowance is 4,000, B1/B2 use 8,000/16,000. Map the target search allowance to the actual enumeration/attempt limits, bounded by the unchanged finite grasp family. If only failure-based early stopping limits exist, describe that explicitly and multiply those applicable target-only limits. Record all effective values and any saturation at the finite domain size.

If no separate target search cap exists, keep enumeration unchanged and label the experiment RRT-budget-only. Do not invent a new planner architecture or change collision semantics to fit this table.

Changing two allowances together tests a combined schedule. Do not claim to isolate which allowance caused an improvement. Fine-grained ablation can be proposed later.

### 6.2 Authorized compute envelope

- At most **six new target evaluations**: three roots at B1, then B2 only for those still unknown.
- At most **900 CPU-seconds per evaluation**.
- At most **7,200 aggregate CPU-seconds (2 CPU-hours)** for diagnostic planning, including child-process planning and optional planner diagnostics.
- One planning worker at a time. Disable planner-internal parallelism for this diagnostic, or include every descendant's CPU in enforcement and report any difference from baseline execution settings.
- At most **3 hours wall time** for the diagnostic collection as a separate operational safety limit.
- Tests, report generation and plotting are measured separately; they must not silently launch additional experimental target evaluations outside this envelope.
- No paid compute provisioning, new remote jobs or hardware execution.

Run B1 in root order r04, r14, r15, then B2 in that same order for remaining unknowns. Skip higher tiers once a complete checked witness or sound assignment-wide negative is established. Do not stop simply because the coverage target is reached; follow the frozen applicable schedule.

CPU and wall guards may censor an evaluation before its deterministic allowance is exhausted. Mark these cases `CPU_CENSORED` or `WALL_CENSORED`, with the evidence status remaining UNKNOWN absent a complete accepted witness or certificate. Such a result is not evidence that the full B1/B2 work allowance was ineffective.

### 6.3 Enforce the cap during work

Checking only after a root finishes is insufficient. Use the smallest reliable existing process supervision mechanism, with in-flight CPU accounting and cancellation of the full planning process tree. Reserve a margin below the advertised cap for monitoring and termination. Record configured trigger, measured usage and overshoot, if any. Never describe an unenforced threshold as a hard cap.

Record start/end times, root, tier, PID/task identifier, CPU, wall time, active planner phase, stop reason and completed-evaluation status. On cancellation, preserve only fully validated evidence; never count partial work as success. Do not continue collection if the budget guard itself is faulty.

## 7. Preserve evidence and deployment semantics

Positive means a complete independently checked target witness from the exact initial state: approach, grasp/attachment, supported transport, release and safe retreat under the existing action contract.

- Goal contact alone or a trajectory truncated before retreat is not positive.
- HOME return remains a separate diagnostic and cannot erase a SAFE_RETREAT witness. Do not introduce extra HOME searches in this narrow study unless already required by the evaluator; if performed, include their CPU in the cap.
- Timeouts, RRT exhaustion, exhausted finite search and start-dependent failures are not automatically assignment-wide negatives.
- Use existing checker-accepted certificates only within their declared scope.
- Unknowns remain excluded from binary task supervision and finite-pool joint-loss denominators, while remaining in operational evaluation denominators.
- Do not modify candidate generation, ranking, object selection, destinations, relocation policy, grasp domain, safety margins, tolerances or success policy.
- Do not rerun primary episodes under the stronger teacher schedule or overwrite the original 8/20 result.
- No new learned model is involved.

If an implementation defect invalidates historical evidence, stop the diagnostic, document the affected scope and propose the smallest justified repair. Do not silently fix a defect and merge incompatible old/new labels.

## 8. Minimal implementation and verification

Prefer extending the existing audit/evaluation entry points with a named teacher schedule. Keep the project structure minimal. Add a new module only when it has a clear responsibility that cannot reasonably live in the existing modules; avoid broad refactoring or splitting files solely to manipulate line counts.

Add focused verification for the material changes:

1. Teacher overrides do not mutate deployment configuration or archived hashes.
2. Each tier starts from the identical archived state, assignment, policy and seed.
3. The CPU guard interrupts an in-flight synthetic expensive task, including descendants, and preserves UNKNOWN rather than inventing a negative or partial success.
4. Certificate aggregation distinguishes records, unique assignments, duplicates and overlaps.
5. Call-count accounting handles no-repair, abort and all-stay episodes correctly.
6. Replaying new successful witnesses retains safe retreat and the exact start state.

Use synthetic/stub workloads for guard and call-count tests; do not spend the experimental budget repeatedly running real planners as unit tests. Run the existing regression/replay gates required by the repository once after the final relevant change. Broaden testing only for a concrete remaining risk.

Verify that all earlier reports and run archives remain byte-identical. If existing replay commands write outputs, use a separate temporary destination.

## 9. Required visualizations and outputs

Produce compact visualizations from saved records. Label all new scenes as 2D kinematic evidence, not physical robustness or hardware execution.

1. **Evidence reconciliation:** certificate-record and unique-assignment totals/overlaps; primary target-call counts with no-repair cases visible.
2. **Three-root budget panel:** B0/B1/B2 status, CPU and precise stop reason. Show skipped, not-run and censored tiers explicitly.
3. **Scene evidence:** each initial scene and, where positive, the checked target path through retreat. For unresolved cases, show only recorded diagnostics; do not invent a path or imply a motion-level failure is an impossibility proof.
4. **Witness playback:** one GIF per newly positive root when available; no placeholder success animation if none succeeds.

Reuse existing rendering code. Avoid a new dashboard framework. Render and inspect the figures for clipped labels and misleading colors.

Suggested new run records:

- `plan.json`, `config.json`, `manifest.json`.
- `reporting_reconciliation.json` with source-record references.
- `teacher_budget_results.json` with B0 references and every B1/B2 outcome.
- `event_trace.json` and `metrics.csv` with budgets and actual costs.
- Checked witness records, replay metadata, compact figures and any successful GIFs.

Create `responses-phases/0009_G4A_followup_completion.md` if that number is unused; otherwise choose the next unused number. Do not overwrite an existing report. Include:

- Exact source/config/plan hashes and branch state.
- Corrections to report 0008, each supported by saved records.
- Per-root baseline and diagnostic results, including censoring.
- New complete witnesses, incremental CPU and CPU per newly witnessed root, when the denominator is nonzero.
- Original versus diagnostic-enriched zero-move coverage on the same 20 roots.
- The fact that selectively reevaluating all-stay cases does not estimate a new whole-dataset unknown fraction or operational success rate.
- Tests/replays, archive integrity, changed files and material limitations.
- One concrete next recommendation; no unperformed work described as completed.

## 10. Decision rules after collection

| Observation | Required interpretation |
|---|---|
| Three new all-stay witnesses | Diagnostic-enriched coverage reaches six on the same roots. The original audit remains unchanged; this alone does not establish scalable teacher cost or authorize G4B. |
| One or two new witnesses | Budget expansion helps some cases; coverage remains below six. Report cost and remaining unresolved causes. |
| No new witnesses after full deterministic allowances | This bounded schedule did not help these cases. Do not infer physical impossibility or keep increasing budgets automatically. |
| CPU/wall limits censor evaluations | Diagnostic is incomplete for those tiers. Report censoring without attributing it to exhausted deterministic allowances. |
| Evidence/protocol contradiction | Stop, isolate the defect and report its scope before further collection. |

Do not extend to the 29 target-budget assignments in this stage. Estimate the cost and benefit of that potential next experiment only after seeing this diagnostic. The 67 relocation-search unknowns require a separately scoped diagnosis.

If future root-mixture changes are recommended, specify strata and counts before their outcomes. Keep all attempted roots in the ledger. Do not lower the original six-root target retrospectively, silently replace difficult roots, or select replacement roots for their planning outcomes.

Current certified negatives concern goal occupancy and finite-grasp access. Do not claim that this follow-up establishes path-level infeasibility learning or minimal causal explanations. Do not fabricate path negatives to fill that gap.

## 11. Completion and repository handoff

Place this instruction under `instruction-phase-md/` using the same basename. Complete the reconciliation, narrow code changes, bounded experiment, visual evidence and new report. Preserve unrelated work.

If the established repository workflow already authorizes commit and push, commit only the intended changes and push normally to the verified existing remote/branch. Never force-push. Otherwise leave the changes ready for review and report their state. A rejected or unavailable push must be reported accurately.

Final response: decision, per-root results, exact compute used, reporting corrections, test/replay outcome, report/artifact paths and commit/sync status. **Stop after this G4A follow-up.**
