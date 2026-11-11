# G4C-D2-P2 — Soundness Audit and Nontrivial Scene-Construction Decision

**Execution contract for Claude Opus 5.5 High**  
**Prepared:** 20 October 2026  
**Mode:** READ-ONLY REPOSITORY/SAVED-EVIDENCE AUDIT + ONE NEW REPORT  
**Status:** AUTHORIZED FOR DESIGN/ANALYSIS ONLY; NO NEW ORACLE CALLS OR COLLECTION

> **One-sentence objective.** Determine whether a formally sound, useful *original-task-level* infeasibility certificate can be constructed from the 15 fast UNKNOWNs in report 0016; otherwise specify a cheaper, independently certifiable scene-construction strategy that creates nontrivial blocked-target/repair evidence. Choose a justified next experiment and STOP. Neither outcome permits automatic implementation or collection.

## 0. Authority, version scope, and fixed evidence

Read, in this order, and distinguish the *scientific contract* from *implementation status*:

1. `latent_causal_tamp_methodology_v1_7.md` — normative scientific semantics for the 2D A/B/C comparison. In particular: **Three-valued source of truth; labelled quantities; fixed-robot interventions; omission; no-repair vs original target; executable ordered repair; unknown masking; one-shot boundary**.
2. `latent_causal_tamp_implementation_guide_v1_9.md` — stage gates, shared data and implementation boundaries, release criteria, preservation of G0–G4D.
3. `reports/0016_G4C_D2_P1_poc_s.md` **or the actual repository location** of report 0016, and its saved run/manifest/ledgers. The supplied copy is `0016_G4C_D2_P1_poc_s.md`. Inspect the actual report, not just this synopsis.
4. Earlier frozen D2/P0/G4C/G4D plans/reports **only where needed to establish the active allowed-action domain and exact proof/certificate contracts**. Identify actual paths by searching the repo; do not invent them. Read source and tests where the definitions live.
5. This document. If a newer local methodology exists, report it before use; **do not silently substitute** it for v1.7/v1.9 without user confirmation. Historical documents are evidence, not authority to revert to the old frozen-sweep-as-feasibility architecture.

**Current fixed observations, to verify against report 0016:**

- Repository report commit communicated as `cd4e9fd`; 216 tests and six archived replays passed; P0 artifacts byte-identical. Verify the repository HEAD/remote and actual hashes by inspection. Do not claim a fresh test run unless one is explicitly authorized (it is **not** here).
- `POC_S`: 68 frozen units + 2 fresh-base diagnostics attempted; 2 of the 70 attempted units CPU-censored; frozen outcomes = **30 VERIFIED_FEASIBLE, 6 CERTIFIED_INFEASIBLE, 32 UNKNOWN**; fresh bases = 2 feasible.
- Resource totals = **12,666 CPU-s / 18,000**, **12,634 wall-s / 23,400**, **40 relocation calls / 46**, **63 target evaluations / 70**. Recorded-checkpoint figures (39/61) omit in-flight/cancelled calls; never misreport them as totals.
- Original-target `+A`, `+A+B`, `+A+S` no-repair outcomes in **both** lineages are UNKNOWN despite colliding with the **old nominal target trajectory**. Only original no-repair `+G` cases have a certified block, by `GOAL_OVERLAP`.
- Two same-endpoint order contrasts in `+A+S` are real and sound but use `ORDER_FIRST_ACTION`: an occupied destination at the first action. This is **not** robot-access obstruction.
- Three substantive fully decided B/C pools exist: `g4c_r00 +N`, `g4d_R1 +G`, `g4d_R1 +N`; **none** establish the desired swept-body obstructed original target.
- **15 fast UNKNOWNs**: `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS`, 2–14 s. Their finite scheduled grasp/path attempts failed, but **no full allowed-domain certificate** exists. Other UNKNOWNs include planner node limits, unresolved connectors, and two CPU-censored attempts.
- `g4d_R1 +A+B`: 10 units, **6,655 CPU-s, zero decided**. No automatic escalation of that family.
- Known P0 `d2.py` status-string mismatch: adapter in `d2_poc.py` maps raw evidence to P/N/U terms without rewriting hash-frozen `d2.py`.

**Historical evidence is immutable.** Do not relabel UNKNOWN, reinterpret a nominal swept-volume collision as a complete target infeasibility certificate, or report the existing order contrast as physically nontrivial access dependence. No existing artifact, hash, split, witness or scene may be rewritten.

## 1. Hard boundary: what is and is not authorized

**Permitted:** `git status`, `git log`, `git ls-files`, source reads, file searches, parsing *stored* JSON/NPZ/text/logs **without invoking project modules**, inspection of already computed collision/witness/trajectory evidence, static mathematics, written proof/counterexample analysis, simple arithmetic on saved counts. You may create **one new Markdown report** in the repository's existing report location; if the repository has no clear reporting convention, use `reports/` only after confirming this will not overwrite user files. Do not mutate archived inputs to generate the report.

**Prohibited, even if seemingly cheap:**

- Any `run.py` project command, `pytest`, replay, simulator import with side effects, planner/IK/target/collision oracle execution, fresh labels, fresh scenes, new variants, collection, numerical trials or resuming a cancelled unit. **Planner calls = 0; target evaluations = 0; relocation skill calls = 0; new learner training = 0.**
- Creating/modifying code, configurations, tests, source hashes, schemas, existing reports, manifests, assets, archived runs, or the supplied instruction document.
- Implementing or registering a new certificate kind; changing tolerances, grasp/IK/domain limits, timeout semantics, `GOAL_AND_SAFE_RETREAT`, or the 48-grasp contract.
- Starting `POC_F`, finishing other G4C roots, sampler G4B, G4E, G5, G6, 3D or hardware. Do not turn a suggestion in this report into execution authorization.
- Claiming domain exhaustion from `4,000 nodes`, a 900-s budget, 870-s cancellation, a planner failure, a handful of trajectories, an incomplete IK/grasp enumeration, or a collision on a frozen historic path.

**Safety of read-only inspection:** If Python imports trigger planning, do not import. Read the text/data directly. Respect untracked `instruction-phase-md/*` and user-owned workspace files. If any required evidence is missing or contradictory, explicitly mark `NOT_VERIFIABLE_FROM_AVAILABLE_REPO`; do not silently interpolate.

## 2. Reconstruct the actual feasibility question (before proposing certificates)

Copy the exact *implemented* definitions from code and compare with v1.7, citing file/line or symbol and evidence scope. Do not reason from the colloquial phrase “all grasps blocked.”

For an initial state `S0`, the empty repair `r=∅`, all **permitted** complete target executions `Gamma(S0)`, and the original goal with checked safe retreat:

\[
Y_0^*(S_0)=1\left[\exists\gamma\in\Gamma(S_0): \operatorname{Valid}(\gamma;S_0)=1\right].
\]

The label `CERTIFIED_INFEASIBLE` for the original target is only defensible if a sound argument excludes **every** allowed execution in `Gamma(S0)` at the stated policy/scope, or a more direct necessary-condition contradiction holds. A complete witness proves feasible; failed finite stochastic searches prove neither.

For ordered corrective sequence `r`, keep the separate definition

\[
Y^*(r\mid S_0)=1\left[\exists w\in\mathcal W(r,S_0),\ \exists\gamma:\operatorname{Valid}(w,\gamma)=1\right]
\]

with achieved state continuity, fixed user-requested object order, target evaluated only after a complete relocation witness, and `GOAL_AND_SAFE_RETREAT`. Separate original-target proof, static-endpoint proof, first-action-order proof, and complete-ordered-repair proof. Never transfer certificates across these scopes without formally establishing their quantifiers.

Determine from actual repository code (and record **unknown/ambiguous** rather than presuming):

1. **Allowed target action class:** can the target planner select alternate target trajectories? Is the earlier `gamma0` diagnostic only? What goal, start-state, contact and safe-retreat constraints apply?
2. **Grasps:** precisely which 48 candidates, their frames and symmetry, whether exhaustive **by task definition** or merely the scheduled subset, and whether unenumerated continuous or alternate grasp configurations remain permitted.
3. **IK/robot poses:** which branches, joint ranges, self-collision/obstacle checks, fingers, attached target, approach/closure/release and connector constraints; whether any tests are local necessary conditions versus heuristic failures.
4. **Motion:** what is explored by the continuous planner; whether candidate target trajectories may reroute; what 4,000-node and time caps mean; what a planner/connector rejection actually certifies.
5. **Numerical completeness:** signed clearance with the single 0.005-m margin; boundary-band and interval/collision conservativeness; whether any algorithm is exhaustive over a continuous variable, and under what explicit bound.
6. **All permitted outcomes:** robot start q/g/attachment fixed; goal and safe retreat; any authorized alternative grasp/target route. Ensure a proposed new certificate never proves merely `NOT_FEASIBLE_ON_GAMMA0` while labeling `NOT_FEASIBLE_FOR_ORIGINAL_TASK`.

Produce a short **formal domain inventory** of included/excluded possibilities with code locations and exact evidence semantics. If the domain cannot be reconstructed, this is a BLOCKED outcome, not permission to assume a narrower domain.

## 3. Line-by-line audit of the 15 fast UNKNOWNs

Find the actual 15 unit IDs in saved evidence; do **not** invent unit names, reasons, or counts. Create a compact table in the report with one row per unit, containing:

- saved unit ID; root/lineage/variant; query type (ordered repair / original target / fixed-robot scene edit / other), and whether it would affect the **original no-repair** Q2 label;
- original outcome `UNKNOWN`, wall/CPU if saved, and cited evidence paths;
- exact rejection trace grouped by **grasp candidate**, **IK branch**, **approach/closure**, **carry/transport**, **goal**, **retreat**, **connector**, **numeric ambiguity**, or **planner exhausted** (use actual recorded categories; never misstate a single-step rejection as a universally excluded grasp);
- number scheduled, number actually attempted, proof coverage of the *declared* allowed domain, and whether every failure is a sound necessary-condition exclusion;
- **candidate certifiability** (`PROVABLY_EXCLUDABLE`, `CONDITIONAL_ON_UNPROVEN_ASSUMPTION`, `NOT_CERTIFIABLE`, or `INSUFFICIENT_RECORD`) and minimal missing proof artifact;
- what scope would result if the proposed proof were accepted: `ORIGINAL_TARGET`, `SINGLE_ORDER`, `STATIC_ENDPOINT`, `SPECIFIC_GRASP`, `GAMMA0_ONLY`, etc.

Explicitly separate *all scheduled attempts rejected* from *all permitted configurations proved impossible*. Rank failure modes by how many of the 15 they cover **and** by whether they can ever support Q2—not by how quickly they would add apparent negatives.

Also summarize the remaining expensive UNKNOWN categories without replaying them: what is fundamentally different about `g4d_R1 +A+B` and why a local grasp certificate would, or would not, apply to those cases.

## 4. Proposed certificate: formal theorem, proof obligations and counterexamples

Call the proposed certificate **`ALL_ALLOWED_TARGET_GRASPS_EXCLUDED` (working name only, NOT an implemented status)**. Its sound use is a *negative original-task certificate* only after the following conditions have been **established**, not assumed:

- **Necessity:** every policy-permitted complete target success from the exact `S0` must pass through at least one grasp/attachment configuration in a declared family `G` (unless non-grasp target completion is allowed, in which case account for it).
- **Coverage:** `G` must contain **all** such allowed configurations, or its continuous complement must be soundly excluded; `48 scheduled candidates` is not automatically complete. Explicitly distinguish defined finite skill policy from unrestricted physical manipulation.
- **Sound exclusion for each g:** for every `g ∈ G`, prove at least one *necessary stage* geometrically impossible under all allowed IK branches / relevant continuous configurations **using a conservative, complete check for that subclaim**. Do not use timeout/failed sample path/failed random trial as exclusion.
- **Consistent scope:** fixed original `S0`, robot q/g/attachment, object poses, contact rules, margins, goal and retreat. No altering grasp/task definitions retroactively to make negatives certifiable.
- **No inference from partial transport:** a blocked particular sweep/connector is not a universal proof unless *all* alternatives in the declared domain are excluded. A grasp may be reachable but its transport unresolved—then still UNKNOWN unless another theorem applies.
- **Numerical soundness:** near-contact ambiguous intervals/approximate collision samples cannot be silently classified as guaranteed collision.

Express the conditional statement and a proof sketch. Example sufficient form:

\[
\bigl(\forall \gamma\in\Gamma(S_0),\ \operatorname{Valid}(\gamma)\Rightarrow
\exists g\in G:\mathsf{NecessaryGraspStage}(\gamma,g)\bigr)
\land
\bigl(\forall g\in G:\ \mathsf{ProvenImpossibleNecessaryStage}(g,S_0)\bigr)
\Rightarrow Y_0^*(S_0)=0.
\]

The proof is only as strong as the coverage theorem and sound individual exclusions. **Do not implement this formula as a Boolean over the logged attempt count.**

Provide at least **five explicit counterexample sketches**, chosen to stress different missing premises:

1. old nominal target path intersects A but another allowed target trajectory avoids A;
2. all *scheduled* grasp configs fail but another permitted grasp orientation or IK branch succeeds;
3. a grasp is geometrically possible, but a finite planner times out on approach or carry;
4. a discrete 48-candidate set does not cover a continuous grasp continuum unless the *declared* skill domain genuinely makes it exhaustive;
5. the necessary grip/contact stage is locally ambiguous near the margin or a safe-retreat requirement was not included;
6. optional: original task blocked but a relocation witness succeeds—why a diagnostic teleport of an object does not itself prove the relocation is executable.

For each proposed sub-certificate (grasp/IK exclusion, static obstruction, topology/corridor barrier, etc.), give: exact quantifier, evidence needed, soundness status, code readiness, expected applicability to the 15 and to `+A*` Q2, residual UNKNOWN condition, and easiest correctness unit tests **for a *future*, separately approved implementation**. Provide no new code and do not run tests.

**Decision standard:** If the soundness proof depends on undocumented assumptions (finite grasp completeness, complete IK domain, certified continuous motion impossibility) and cannot be established from existing implementation/contracts, verdict = `CERTIFICATE_NOT_READY`, not “probably sound.” A limited, correctly scoped cert can still be recommended if its usefulness is measured honestly.

## 5. Audit the scene generator, not just the proof system

Report 0016 has a structural limitation: placing A on a **historical target sweep** proves that sweep is blocked, *not* that the initial task is impossible. Inspect the actual D2/P0 construction code, stored root geometry, candidate placements and relevant positive/unknown sequences (read only).

Answer with concrete evidence:

- Why did `+G` produce trivial goal-occupancy negatives while six `+A*` no-repair roots did not produce certified task negatives?
- Is `+A*` likely reroutable, or simply unresolved? **Do not claim reroutability without a complete no-repair witness.**
- Why did `g4c_r00` resolve many cases quickly, whereas `g4d_R1 +A+B` exhausted 6,655 CPU-s with no decided cases? Distinguish observed causes from hypotheses.
- Which construction choices improve *provability* and actual physical repairability rather than merely raise collision rates? Examine geometric chokepoints, genuine reach/access dependencies, permitted finite skill actions, placement supports, and a **positive relocation witness after repairing**.
- Which current `+A+S` contrasts are merely occupied-destination dependencies? Specify how a future same-endpoint swapped-order contrast would test **robot access or full-body motion**, not just occupancy. Both positive witness and sound order-scoped negative are required.
- What fixtures could deliver a **decided fixed-robot original-scene effect** and a **decided repair-omission effect**, without a nominal-sweep-only explanation? A joint intervention/nonadditivity test requires four decided sides; UNKNOWN cannot contribute.

If a redesign is needed, specify a **small, auditable constructor**, not a new sprawling dataset generator. Its proposed recipe must retain the active full 3R arm, complete fingers and rigid attachment, 8x8 resting cells, continuous body motion, 48-grasp policy, original q0, goal/retreat and unknown-policy. Generate no scenes in this stage. The source and uncertainty of any proposed theoretical construction must be explicit: `DESIGN HYPOTHESIS — UNTESTED` versus existing measured evidence.

Prefer designing cases with **independently demonstrable original-task obstruction** AND a separately witnessed corrected path, before attempting 3-obstacle combinations or 30–40 clutter. Do not solve proof difficulty by redefining the research target to be the frozen `gamma0`.

## 6. Decide the best next route, with explicit release gates

Conclude **exactly one primary** recommendation (secondary conditional alternatives allowed):

- `A_CERTIFICATE_FIRST`: only if a rigorously scoped certificate and its likely usefulness on original-task Q2 labels are supported by the actual domain/traces. Future first step = separate, approved code/test change and tiny staged validation.
- `B_CONSTRUCTION_FIRST`: if grasp certificate cannot solve the main Q2 but a sounder, cheaper scene construction is promising. Future first step = design/freeze a small new plan with independent proof/witness checks, not POC_F.
- `C_COMBINED_STAGED`: only if a narrowly proven certificate and a construction change solve **different, individually demonstrated** bottlenecks. State exactly which is first and why.
- `D_BLOCKED`: if code/evidence is insufficient for a sound recommendation. State minimal missing facts needed and a zero-oracle inspection path.

For the next *proposed* pilot, predefine scientific acceptance criteria **before seeing any new results**. Minimum informative demonstration should include:

1. **At least one nontrivial** original no-repair `CERTIFIED_INFEASIBLE` at complete allowed-target scope (not GOAL_OVERLAP, not old-path collision, not first-action destination occupancy).
2. A complete **verified ordered relocation + original target + SAFE_RETREAT** witness on that *same* initially blocked scene.
3. At least one eligible, independently decided **fixed-robot scene edit** with nonzero effect on the original target, *if constructible under the declared catalogue*.
4. At least one independently decided positive ordered-repair **omission contrast** on a substantive repair; omission must regenerate the ordered query from S0, not splice old trajectories.
5. For order-learning claims, one decided **same-endpoint** feasible/infeasible swap whose negative is a sound nontrivial **access/motion** certificate, not occupancy-only; if unavailable, mark the order-access claim NOT_ESTABLISHED.
6. B/C full z-pool completeness and interaction/nonadditivity **only if genuinely decided**; do not weaken the missing-field masks or label independence to meet quotas.

Treat these as **predeclared proposed gates**, not currently achieved facts or authorization to collect. Report feasibility separately for the minimal first blocked/recovery pair and for the fuller causal/order pool. The three models A/B/C remain future comparisons, sharing the same independently labeled data; do **not** redesign the energy architectures in this stage.

### Cost and release planning

From the observed POC_S ledger, calculate only defensible empirical quantities: decided yield, useful-scene yield, CPU per decided original-target negative of each type (N/A where zero), CPU per substantive pool, unknown concentration and family cost. A zero denominator is `N/A`, never estimated as finite. Call cancelled/in-flight calls properly.

Specify a **next pilot proposal** (not executed) with:

- hypothesized scene types, numbers of *independent* roots, attempted candidates and predeclared query catalogue;
- exact comparison/control needed to isolate effect of certificate vs construction (same roots, same original target policy where meaningful);
- sound positive/negative/UNKNOWN labeling and full target execution policy;
- **proposed** per-unit CPU, aggregate CPU, wall, worker count, 4,000-node policy (or explicitly justified candidate revision), call caps and cancellation rules; tie budget suggestions to the POC_S ledger, mark extrapolations as unverified;
- expected scientific information per query and stopping/futility checks; do not promise throughput or inferred negative yield;
- what would justify expanding beyond the tiny pilot or approving `POC_F`, and what result would **stop** the line of inquiry.

**No numerical budget automatically carries over from report 0016.** A new pilot requires the user's explicit authorization for each budget/cap and for code changes if needed. There is **no implicit authorization for 194-unit POC_F**.

## 7. Required review report: structure and evidence quality

Create **one** new Markdown report following the repo's existing report-number convention; do **not** overwrite 0016 or 0017. Recommended descriptive suffix: `G4C_D2_P2_certificate_soundness_review.md`. It must include these sections, in order:

1. **Decision banner**: chosen `A/B/C/D` route, certificate verdict (`SOUND_AS_SCOPED` / `CONDITIONAL` / `NOT_READY` / `NOT_VERIFIABLE`), one-sentence reason and `STOP; NO COLLECTION AUTHORIZED`.
2. **Authority/source hashes**: inspected commit/branch, relevant source/report paths, methodology versions, tracked/untracked cleanliness; report what was not readable.
3. **Invariants and fixed POC_S ledger**: no relabeling, full 68-unit denominator, Q2 TRIVIAL_ONLY, resource totals, incomplete pools and cancels.
4. **Mathematical task and domain inventory**: original no-repair vs `gamma0` diagnostic vs ordered repair, exact policy/exhaustiveness boundaries, code line/symbol references.
5. **15-UNKNOWN unit-by-unit audit**: full evidence citation, rejection stage, coverage, candidate certifiability and missing proof.
6. **Certificate theorem/assumptions and falsification attempts**: explicit quantified proof, counterexamples, scope and whether it would actually decide Q2 cases.
7. **Scene-constructor forensic review**: observed versus hypothesized bottlenecks; nontrivial access/repair opportunities; why `g4d_R1 +A+B` is expensive.
8. **Evidence-to-learning impact**: what labels support static/A and outcome-coupled B/C today; why absent `+A*` Q2/nonadditivity prevents causal scientific claims; never treat B/C pool completeness as general causal coverage.
9. **Ranked options + one recommendation**: decision rule applied, rejected alternatives and risks.
10. **Proposed next micro-pilot contract**: exact scope, controls, quantitative *proposed* limits and explicit user approvals needed; all `NOT_RUN` until approved.
11. **Integrity/zero-call attestations**: `git diff --name-status` before/after, no code/config/source changes, planner/target/relocation calls 0 in this stage, no new labels, no new training, no project test/replay claims.
12. **Stop statement and handoff**: list at most two substantive next authorization decisions, including which files/code functions would be allowed to change and which must remain immutable; stop completely.

Use compact tables where they make auditing easier; no lengthy generic EBM background. Quote concrete code symbols / file:line locations for the definition of each asserted domain or certificate. Write `UNVERIFIED` whenever the implementation does not support the statement; use `INFERENCE` for interpretation. State selected `A/B/C/D` only **after** reviewing saved evidence.

## 8. Completion and repository handoff

- Check `git status` at start and end. Preserve untracked user documents and all historic artifacts. No speculative refactors or amendments to `d2_poc.py` despite its 331 logical lines and hash binding; cosmetic figure issues are out of scope.
- Run **no** project tests/replays/collisions in this stage. The only allowed tracked addition is the new report, after confirming numbering and existing repo convention. If repository report commit/push is supported, make a **report-only** commit (never auto-stage other files), push non-force, and verify local/remote refs. If the working tree has unexpected tracked changes, do **not** commit; report blocker instead. This report-only synchronization is not permission for any other change.
- In your final chat response provide: precise decision/verdict; number of audited fast UNKNOWNs; whether any may be certified under the **current** policy and with what missing prerequisites; why original `+A*` Q2 is or is not resolved; the recommended next micro-stage; proposed—not authorized—compute envelope; report path/commit/push status; explicit note **NO CODE CHANGED, ZERO NEW PLANNER CALLS, POC_F NOT STARTED**.
- If uncertain, do not ask open-ended questions in place of doing the review. Make the best justified bounded recommendation, identify which exact missing fact prevents stronger proof, and STOP. Never manufacture a positive or negative result to provide closure.

**STOP at the report. Do not take the next stage's actions until the user explicitly approves its code and compute budget.**
