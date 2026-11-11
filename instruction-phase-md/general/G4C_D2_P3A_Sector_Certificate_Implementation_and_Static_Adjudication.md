# G4C-D2-P3a — Sector Certificate Implementation and Static Re-adjudication

**Execution contract for Claude Opus 5.5 High | 21 October 2026**  
**Stage type:** implementation + static verification + independent adjudication (NOT a new trajectory/teacher collection)  
**Immediate predecessor:** report `responses-phases/0017_G4C_D2_P2_certificate_soundness_review.md`, uncommitted at handoff; report 0016 and commit `cd4e9fd8fcf044419b266ab3359faa630326e6a0`.  
**Authority:** Methodology v1.7 for science, Implementation Guide v1.9 for implementation, report 0017 §4–§10 for this theorem and frozen target list. Where evidence contradicts a proposal, **stop and report**; never weaken a certificate to make counts pass.

## 0. The decision made for this P3a handoff

This handoff is the user's **explicit approval to perform P3a only within the numerical limits below**, once sent to the executing agent. It does **not** authorize P3b, POC_F, remaining G4C collection, new planner calls for data, neural training, 3D, or hardware.

1. **A1 — accept the declared benchmark domain:** for the *current 2D benchmark only*, the permitted target manipulation is the repository-defined six-phase supported 3R skill, with its exact recorded **48 grasp configurations** (24 orientations × 2 IK branches), frozen grasp point and predeclared approach/retreat, and current target/safe-retreat success semantics. Scope a negative as *infeasible under the declared skill and fixed start*, **never physical impossibility for arbitrary grasps or robots**. Do not expand or narrow the previously implemented skill implicitly.
2. **A7 — conservative initial certificate:** implement and release **pick-side** 48-candidate sector/definite-screen exclusion. Keep general **place-screen collision** exclusion disabled because task success accepts a 2-mm goal tolerance while the skill places at the exact centre. Optional **sector-only place** exclusion may be coded/tested but **MUST remain disabled for adjudication** unless an independent proof and implementation establish the angular envelope for **all placements allowed by the 2-mm task predicate**, with independent checker and adversarial tests. Do not solve this by silently changing goal tolerance. Pick-side-only is a valid P3a outcome.
3. **Meaning of zero calls:** **zero calls** to motion/path planners, relocation-skill executions, target evaluations, replays, or teacher outcome generation **during the P3a adjudication run**. Deterministic geometric computations needed for certificate production (FK, analytic IK, pose-only screen/collision checks, shape calculations) **are authorized** and MUST be separately counted. A later, separately accounted regression/test phase may invoke historical planner tests; never report those as zero.
4. **Old work stays frozen.** Old labels, hashes, runs, configs, archived witnesses, reports and POC_S plan remain byte-identical. P3a adds a new scoped adjudication, not a repair of history.
5. **No result promised.** A null result is acceptable. A certificate is valid only after the checker passes its proof obligations and tests. No fabricated negatives; unknown remains unknown when any necessary premise is missing.

## 1. Scientific objective — what done looks like

Answer all five questions with **actual independent checked artifacts**:

- Can a fixed-start link-0 sector theorem certify any of POC_S `g4c_r00` `+A`, `+A+B`, `+A+S` original no-repair UNKNOWNs, using **all 48** pick candidates and the initial unedited robot state?
- Can it certify any eligible diagnostic scene-edit outcomes, maintaining exactly the original fixed robot q/g/attachment and appearance anchor?
- Can it certify a **first-action** failure in pilot `g4c_r19`, turning the existing positive-vs-UNKNOWN swapped-order pair into a **positive-vs-certified-negative physical-access order contrast**, without mistaking an occupied destination for access proof?
- Do all saved positive witnesses and synthetic adversarial controls remain uncontradicted, with complete hashes, source scope, start-state scope and certifier independence?
- If the certificate does not fire, what exact premises failed and what must change in a later **separately authorized** scene-construction pilot?

Success is **valid checked labels, not a target count**. A good negative checker that fires zero times still preserves scientific integrity.

## 2. Repo intake, permissions and initial integrity check

Before writing code:

1. Inspect `git status --short`, branch, HEAD, `origin/main`, diffs and exact hashes. Read **in full** report 0017, report 0016, methodology v1.7, implementation guide v1.9 and the actually present source files (`skill.py`, `planner.py`, `geometry.py`, `motion.py`, `certificates.py`, `ordered.py`, `evaluate.py`, `g4c_pilot.py`, `g4d_run.py`, `d2.py`, `d2_poc.py`, configs). Identify actual CLI/test conventions rather than inventing them.
2. Two root tracked PDFs may already show deleted, with byte-identical untracked copies under `instruction-phase-md/`: `latent_causal_tamp_implementation_guide_v1_8.pdf`, `latent_causal_tamp_specification_v1_6.pdf`. **Do not restore, delete, move, or stage either PDF**. Treat as user-owned unresolved state. They do not block scoped implementation if other files are clean. Record the unchanged before/after status.
3. Report 0017 may be untracked. Do not alter its content. Only explicitly stage that single report in a separate *report-only* commit if safely possible; do not stage the PDF changes or user instruction files.
4. Confirm input runs/manifests exist. If hashes disagree, a dependency/contract differs, or prior POC_S evidence is damaged, **STOP without implementation** and report the precise discrepancy.
5. Create **only** the permitted files/changes in §3. Keep the new source module approximately 120–280 logical lines if possible, under ~300; split only for a compelling independently documented responsibility, not an architecture/framework rebuild.

## 3. File ownership: deliberately minimal

Permitted tracked additions/changes, and only as required:

- `sector_cert.py` **NEW**: pure pose/sector candidate evaluation, auditable proof record, independent certificate checker, and scoped adjudication adapter. Avoid circular checker reliance on producer verdict. If producer and checker cannot be sufficiently independent within one file, add a **single** `sector_check.py` (~small) after explaining why.
- `tests/test_sector_cert.py` **NEW**: microgeometry, counterexamples, checker tampering, saved-positive noncontradiction, source/scope, call-budget assertions.
- `run.py` **MINIMAL**: exactly one new command such as `g4c-d2-p3a-static` using existing CLI architecture.
- `responses-phases/0018_G4C_D2_P3a_sector_certificate_results.md` **NEW** (next available number only if existing repo numbering confirms); concise numerical result and per-unit evidence with limitations.
- `runs/g4c_d2_p3a_static/` **NEW**: frozen input manifest, no-call counters, per-candidate proof rows, decisions, figure(s), summary and source hashes. Generated static figures allowed; never present schematics as executed trajectories.
- If needed, one small isolated, reviewed test fixture file, created only if tests otherwise cannot be legible.

**Forbidden modifications**: `skill.py`, `planner.py`, `motion.py`, `geometry.py`, `certificates.py`, `ordered.py`, `verify.py`, `evaluate.py`, `g4d_run.py`, `g4c_pilot.py`, `d2*.py`, `d2_poc*.py`, `config*.toml`, any existing `runs/` files, plans/hashes, historical reports and archived test results. No generalized refactor or future-stage implementation.

## 4. Sound certificate, exact conditions

Follow report 0017 §6, **not** a merely suggestive proximity heuristic.

Let the immobile scene at the fixed start be `W`, the robot start `q_s`, link-0 base `b`, actual source-of-truth link/housing geometry, disc radius `r`, clearance delta `δ`, numerical tolerance `ε` and joint limits. Compute conservatively the certified annulus radius according to the currently verified collision/body policy (report suggests `R0 = 0.4608 m`; verify against code, do not hardcode if mismatched). An obstacle contributes a sector barrier **only with the theorem's strict geometric criterion**, clear validity of pose, and sound collision margin. Define the *open* angular free sector containing `q_s[0]`; clamp to physical joint limits, reject joint wrap or ambiguity. A near-boundary uncertainty must fail closed.

For each of the **exact 48** declared pick `(phi, elbow branch)` candidates, independently compute:

- Missing exact IK / definitely impossible IK result;
- Definite, sound pose-only pick-screen exclusion;
- Or valid IK whose first joint is **certifiably outside** the allowed start sector.

Only if **EVERY ONE of 48 picks** is excluded by a sufficient proof can we emit `CERTIFIED_INFEASIBLE` for the fixed-start first action / original target **with the exact declared-skill proof scope**. Any in-sector candidate with an uncertain screen, missing data or unknown IK means **UNKNOWN** unless another sound exclusion applies. Check start configuration and all geometrical conditions, including target/rest-world identity and allowed contacts.

**Do not infer a negative** from: archived nominal sweep collision; all scheduled connectors failing; RRT node/time limit; incomplete screen logs; an uncertain or gray-band screen result; an occupied intermediate goal from a different proof kind; a single relocation realization finishing in a bad q; or a successful scene-edit teleport.

**Scope distinction**:

- Original no-repair query: original `S0`/fixed `q0` → `ORIGINAL_TARGET` certified negative (declared skill).
- Eligible fixed-robot scene edit: edited object poses only, **unchanged** `q0`, gripper/attachment, target, eligibility and frozen appearance anchor → `SCENE_TARGET_ONLY` negative.
- First high-level action of an ordered repair: start `S0` before any move, first object and destination as requested → **ORDER-scope first-action negative** for that exact ordered proposal; can transfer only where the validated certificate covers the exact unchanged first action, robot state and world.
- **Never** apply this fixed-start theorem to the target after one or more relocations, or to later repair actions. Alternate valid relocation realizations may end at other joint sectors. Never turn an `ORDER` certificate into an assignment-wide negative unless separately proved.

**Place-side decision:** By default do not use general place-screen rejection in the new certificate. If a place-only sector proof is proposed, document a conservative bound over all valid 2-mm goal offsets and exact grasp/IK contingencies, prove it independently, test with adverse 1–2-mm goal shifts, and **do not release it in P3a** unless all conditions are met within the existing budget. Prioritize completing pick side quickly.

Record for each candidate: `(phi, branch, IK outcome, q0, screen outcome with definite/unknown flag, sector bounds, exclusion reason, checker verdict)` and provenance for geometrical constants. Do not use model predictions or privileged future targets as an input.

## 5. Frozen units — no cherry-picking after results

**POC_S, 6 eligible** (see report 0017 §5.2 rows 1,2,3,4,6,10):

1. `scene:d2_g4c_r00_AB:o05>41`
2. `scene:d2_g4c_r00_AS:o04>56`
3. `scene:d2_g4c_r00_AS:o05>48`
4. `seq:d2_g4c_r00_A:empty` **Q2**
5. `seq:d2_g4c_r00_AB:empty` **Q2**
6. `seq:d2_g4c_r00_AS:empty` **Q2**

**Pilot, 9 eligible** (resolve these from report 0017 §10 exact immutable IDs and original evidence; do not infer different IDs):

1. `scene:g4c_r19:o00>9`
2. `seq:g4c_r19:o00>27`
3. `seq:g4c_r19:o00>27.o01>28`
4. `seq:g4c_r08:o00>15`
5. `seq:g4c_r08:o00>47`
6. `seq:g4c_r08:o00>47.o01>46`
7. `seq:g4c_r08:o01>46.o00>47`
8. `seq:g4c_r14:o02>39.o00>38`
9. `seq:g4c_r14:o02>39.o01>7.o00>38`

**Controls**: every stored positive witness from POC_S, pilot and G4D under its actual start state and scene, not assumed uniform q0; 32 POC_S positives, 13 pilot positives and the actual applicable G4D witness inventory confirmed in repo. Include link-0 sector boundary and disconnected world tests. Log every enumerated unit with source/run/id/hash/scope and pre-existing label.

**Excluded**: POC_S fast-UNKNOWN rows 5,7–9,11–15 (target stage after relocation), plus all expensive RRT/censored UNKNOWNs. Report them as still UNKNOWN; do not attempt to re-adjudicate them under this fixed-start theorem.

## 6. Implementation sequence — run immediately, no new review loop

1. **Preflight and theorem gate.** Verify the current code/body/joint/IK/screen contracts match report 0017; write a compact proof-obligation/assumption manifest with open A7 explicitly disabled. If report theorem fails on actual code, STOP before issuing any new negative.
2. **Implement small pure producer/checker.** Producer computes per-candidate proof. Checker reconstructs geometry/state directly from source records, reruns/cross-checks the necessary inputs, independently verifies the *full* 48 candidate exclusion proof and scope/source hashes. Producer's boolean is never authoritative. Check for missing, duplicated, or unexpected candidates, changed q/start/world/goal/profile, unknown screen states, collision margins and invalid annulus assumptions.
3. **Unit tests BEFORE real adjudication.** At minimum implement tests in §7; run the new tests without invoking planners. Enforce call guards around planner/skill/target/relocation interfaces. Count static IK/screen/geometry operations separately.
4. **Run exactly one P3a static adjudication** for the immutable 6+9 target list and positive controls; output exact per-unit proofs and undecided reasons. Respect single-worker, wall/CPU/query caps. If interruption occurs, checkpoint; never convert partial work to negative.
5. **Re-evaluate science questions** only from checker-accepted new proof + unchanged historical witnesses. Recompute no-repair Q2, same-root recovery Q3, decided fixed-robot effects and omission/order contrasts; compute nonadditivity **only when all four required sides were independently decided**. Distinguish a verified *access* order contrast from trivial occupancy.
6. **Regression/replay phase (separate accounting):** run complete existing regression suite and six archived replays once each, only if the agreed separate budget permits. These historical tests **do invoke** planner and relocation helpers; record their actual 621/60 prior counts as historical baseline, actual new counts as measured. No hidden planner invocation or falsely reporting zero for this phase. Fail closed if regression fails. Never create new teacher labels from test/replay executions.
7. **Write report 0018 and stage verdict.** Include detailed decision list for all 15 adjudication candidates, all positive controls, CPU/wall/call accounting, hashes, source diffs, affected original/scene/order/omission outcomes, contradiction counts, and explicit limitations.
8. **Commit discipline.** Prefer a report-only commit for previously untracked report 0017, if untouched and safe, plus a separate P3a scoped commit; stage *only* explicitly listed files. Verify cached diff and `git status` before and after. Never stage the preexisting deleted PDFs, instruction files or unrelated untracked content. Push only if branch/remote synchronization can be verified without force; otherwise leave valid outputs and report blocker without discarding work.
9. **STOP.** No P3b execution, no POC_F, no training, 3D or new large dataset.

## 7. Non-negotiable tests and independent falsification

- Theorem boundary test on synthetic link-0 annulus blocker; same object moved outside `R0` (e.g. ρ = 0.465 m) must be rejected as a proof premise.
- In-sector candidate with ambiguous gray-band screen => fail certificate. No missing 48 candidates, duplicates, incorrect elbow branch or wrong grasp depth tolerated.
- Invalid start, changed q0, added/removed objects, altered source/goal/hash/gripper/attachment/profile => proof refused.
- Wrap/joint-limit changes, obstacle near threshold, collision-policy mismatch => fail closed.
- Never apply fixed-start target-stage proof after an already committed relocation; first-action order use only before any move.
- Pick and place are not conflated; no place-screen exclusion due to exact-centre placement/2-mm goal discrepancy; adverse shifted-goal controls if optional sector-place machinery exists.
- All archived positive target and repair witnesses remain noncontradicted **at their own actual start**. Treat any contradiction as an immediate stage failure; investigate without silently changing the test.
- Independent checker must reject tampered/missing certificates, forged producer status, candidate reorder/subset, changed reasons, mistaken source hashes, and an old-path-collision-only pseudo-proof.
- No telemetry gap: count static geometric calculations as such and assert zero motion planning, zero target evaluations and zero relocation calls **in P3a adjudication**.
- Verify no mutation of existing runs, reports, manifests, hashes, source config or labels. No incomplete positive/negative relabeling.

## 8. Resource authorization and hard stops

### P3a static code + adjudication

| Resource | Hard authorization |
|---|---|
| Frozen adjudication targets | Exactly 6 POC_S + 9 pilot units; plus existing saved positive controls |
| Target evaluations | **0** |
| Relocation-skill calls | **0** |
| Robot motion-planner calls | **0** |
| Static pose/IK/screen/geometry computations | Allowed; **measured separately** |
| Aggregate CPU (P3a static workflow, excluding regression/replay) | **≤ 900 CPU-s** |
| CPU per eligible query | **≤ 60 CPU-s** |
| Workers | **1** |
| Wall | **≤ 1,800 s** |
| Incomplete/timeout | Return UNKNOWN; cancel under guards; never overshoot budget |

### Separate authorized regression budget

One full regression-suite run and **six** archived replays, with a **separate aggregate cap of 300 CPU-s** and no more than the minimum historical test/replay planner work already required by those procedures. Run only after adjudication; record exact time and calls. If full regression cannot finish within 300 CPU-s, stop gracefully and report `REGRESSION_NOT_COMPLETED` rather than claiming it passed. These calls are **not** new teacher collection; do not mix their counts with P3a's zero-call claim.

**No conditional automatic transition to P3b.** The agent can deliver a budgeted P3b handoff plan, but must not call any P3b planner or generator without a later explicit user authorization.

## 9. Decision gates — execute and stop, don't force success

- **P3A_VALIDATED_CERTIFICATE:** independent checker + proof obligations + tests pass, 0 positive contradictions, all work within caps. This can be true even when it certifies zero frozen UNKNOWNs.
- **P3A_Q2_MET:** checker certifies **at least one** of `seq:d2_g4c_r00_A:empty`, `seq:d2_g4c_r00_AB:empty`, `seq:d2_g4c_r00_AS:empty` as `ORIGINAL_TARGET` negative, and existing same-root repair + target + SAFE_RETREAT witness is sound and unchanged. Report original-task negative and recovery as two independent facts.
- **P3A_ACCESS_ORDER_MET:** checker certifies r19's `o00>27` first action from original `S0` at ORDER scope, and the swapped order already has a complete witness; no occupancy-only proof substituted.
- **P3A_CAUSAL_EFFECTS:** count only fully decided independent fixed-robot scene-pair and omission outcomes. Report nonadditivity values only for actually complete 4-way comparisons. No guaranteed numerical improvement.
- **P3A_FUTILITY:** if 0/3 Q2 units **and** 0/9 pilot units are newly certified, stop this certificate line for current geometry and recommend a redesigned static-certifiability-first constructor (P3b candidate). Otherwise say what remaining decision gaps need another independently approved strategy.
- **P3A_FAILED_SAFETY/INTEGRITY:** a false-negative against saved positive, theorem counterexample, scope failure, source mutation, call violation or guard breach: freeze outputs, do not release certificate labels, report exactly what failed.

## 10. Required report and handoff (short, numerical, conclusive)

Report 0018 must include:

1. Revision, repo status, input source/frozen hashes, tracked/untracked diffs; whether report 0017 was committed separately.
2. Exact theorem implementation and assumptions, including which pick/place proof branches are enabled, and whether A7 remains unresolved.
3. For all **15** eligible units: old label, new verdict, proof scope, 48-candidate exclusion breakdown, checker acceptance/refusal, reason, CPU; and all saved positive controls' contradiction statistics.
4. Outcome delta with counts kept distinct: ORIGINAL_TARGET negatives, SCENE_TARGET_ONLY, FIRST_ACTION_ORDER, decided scene effects, decided omissions, access-order pairs, fully decided interaction pools, remaining UNKNOWNs by source/scope.
5. Static-operation counts; P3a motion/planner/teacher-call totals **zero**; regressions/replays in **separate** accounting with actual counts; exact caps vs use.
6. Whether previously proved same-root recovery witnesses establish the full failure → executable repair → target + safe retreat story **without rerunning planner**.
7. An explicit `P3A_VALIDATED_CERTIFICATE`, `P3A_Q2_MET`, `P3A_ACCESS_ORDER_MET`, `P3A_FUTILITY` (or failed) verdict; no vague 'mostly works'.
8. Concrete next P3b alternative in ≤ one page: constructor logic, independently predeclared 4 fresh bases / ≤84 queries, approximate 9,000 CPU-s ceiling, all caps/kill gates per report 0017 §10, separate authorization, and criteria for dataset-ready **fully decided** A/B/C pools. This is a **proposal only**.
9. Exactly which files were changed/created, tests passing/failing, commit IDs if any, remote sync verified or blocked.

**Dataset policy for all later stages:** keep the complete attempted-root/UNKNOWN audit, but do not emit an UNKNOWN as a positive or negative binary supervision label. Exact joint B/C pools require every active required outcome decided; unresolved fields are masked, not fabricated. An eventual training/evaluation release may consist of fully decided examples while reporting the independent-root selection/coverage denominator. Do not select only easily certified trivial GOAL_OVERLAP roots and claim generalization.

**Final STOP rule:** At conclusion, report only evidence-supported results, request a separate decision for P3b, and **STOP completely**.
