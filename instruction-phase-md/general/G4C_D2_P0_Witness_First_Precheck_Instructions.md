# G4C-D2-P0 — Witness-First Constructive 2D Dataset: PRE-CHECK ONLY

**Project:** Latent Causal Infeasibility for Long-Horizon TAMP  
**Stage:** G4C-D2-P0 / NEW generator design, feasibility audit and non-collecting preflight  
**Execution mode:** **PRE-CHECK ONLY; do not generate new teacher labels or run new motion/target searches.**  
**Purpose:** Design and test a practical route to a **fully decided, proof-carrying released 2D dataset** that starts from a verified feasible target trajectory, adds obstacles to induce informative failure modes, and contains complete supervised repair/intervention comparisons for A, B and C. Do not claim all arbitrary continuous-motion queries can be decided.

## 0. Authority, baseline and non-negotiable scope

Start by inspecting the actual repository, not by assuming these filenames or APIs are complete. Read the repository's own instructions; check branch, HEAD, remote, working tree, source hashes and relevant reports. The reported current baseline is:

- **G4D PASS:** `eb4e661aaaeb90a76cc02bb66d77cbb4a9567303`, report `responses-phases/0011_G4D_corrections_and_collection.md`.
- **G4B PASS:** `84f277d1f26307d5daea9c7a61d94cb4d8768339`, report `responses-phases/0012_G4B_sampler_exact.md`.
- **G4C-P0 original preflight:** `9e7242117a72429ea13f949d68e1d94b5a0f9510`, report `responses-phases/0013_G4C_preflight.md`.
- **G4C-P1 original 5-root pilot complete:** `68161515534000f0211c578e72911f78aa4b6fe0`, report `responses-phases/0014_G4C_pilot_collection.md`. **59 frozen units: 13 POSITIVE, 26 NEGATIVE, 20 UNKNOWN; 340.2 CPU-s; 183 tests; six archived replays.** These are report claims, to be verified against the actual repo.
- Scientific comparison: **Methodology v1.7 + Implementation Guide v1.9** (user-owned untracked bundle in the earlier reports). These remain the current A/B/C architecture proposal. Also read the relevant v1.6/v1.8 original physical-evidence contracts and addenda A1/A2 if available. Note old guide's G4D-BLOCKED statement is superseded by report 0011; do not rewrite historical evidence.

**Preserve everything:** old G0–G4D runs, G4B tests, `runs/g4c_preflight/plan.json` (original 20 roots), pilot plan/authorization/checkpoints and G4C judge outputs, legacy V1 configurations, hashes and source interfaces. **D2 is a new, separately versioned data-construction protocol and lineage, not an edit to, or relabeling of, G4C-P0/P1.** Do not delete UNKNOWN rows from the original 59-unit pilot or retrospectively call it complete-label data. Do not force-push. User-owned untracked instructions/PDFs/bundles must stay untouched.

**This turn authorizes:** source inspection, deterministic static geometry calculations, reading/checking stored *existing* witnesses and artifacts, synthetic unit tests, reproducible planning/manifests and visualization of archived witness geometry with clearly marked hypothetical added objects. This turn does **not** authorize new teacher searches, IK solving to create new ground truth, full target evaluations, root-scale generation, model training, or a new numerical CPU envelope. Do not borrow prior G4D/G4C-P1 budgets. Later D2-P1 teacher-based proof-of-concept requires a separate explicit user approval of numerical bounds.

### Fundamental physical contract (unchanged)

- Same repository-validated **articulated planar 3R robot** with full collidable link/body, base, palm, fingers, object attachment, joint limits, support/contact checks, exact grasp family (currently 48 candidates) and `GOAL_AND_SAFE_RETREAT` target end condition. Use actual tested configurations; no point robot, teleporting gripper, zero-width collision, fresh q/home between actions or silently simplified executor.
- 8×8 resting-cell grid, 0.08 m pitch, identical radius-0.024 m discs, 0.005 m margin unless the actual validated profile differs and its difference is documented. Continuous robot/body/object motion between the discrete resting poses.
- Current primary protocol `INITIAL_SCENE_ORDERED_ONE_SHOT_V2`: a learner sees only initial RGB-D/GT masks/object geometry and poses, initial robot joints/gripper/attachment, task/goal/constraints and legal candidate positions. **No source target trajectory, target swept volume, teacher collision report or construction family ID is available to A/B/C at inference or as an input tensor.** The teacher may use privileged target trajectories only to **construct and label** examples.
- Ordered repair `r=((object,destination),...)` with distinct non-target objects, non-stay supported destinations, one move/object, cap per pinned protocol (development cap currently 3), and `[]` as the only empty repair. Robot-motion backend may choose grasps/paths **within** this exact sequence but never reorder. The real candidate outcome depends on achieved robot state and all robot-body collisions; only a complete relocation+target+safe-retreat witness is POSITIVE.
- **NEGATIVE requires an independently accepted, sound impossibility certificate with the correct action/order/assignment scope.** Timeout, planner exhaustion, absence of a nominal trajectory, 48 tried grasps with unresolved continuous connector paths, or “all attempted pairs blocked” is **not** automatically a proof. These remain UNKNOWN in *raw attempts*. A released *complete-label subset* may reject such attempts, with full audit.

## 1. Motivation: what the previous pilot taught us

G4C-P1 had 20 UNKNOWN/59 despite no time-budget cancellations. Seven first relocations ended with the skill's “all pairs certified blocked from q0” but lack an independently verified **full-domain** first-action certificate; seven ended with uncertified first-action search failures, three had later relocation failures and three unresolved target searches. The 26 negatives were mostly trivial GOAL_OVERLAP (21/26); only one root supplied a decided order contrast, and only `r10` supplied a substantive fully decided B/C pool. **Do not solve this by accepting unsupported negative labels.** Do not overfit a synthetic set to goal overlaps or reward shortcuts.

**New direction requested by the researcher:** (i) find a feasible initial target IK/motion *witness*; (ii) insert varied supported obstacles to create new initial scenes, including nested one/two/three-obstacle variants; (iii) independently re-evaluate target feasibility, scene intervention effects, and complete ordered corrective actions; (iv) generate only release-worthy roots/pools whose entire declared supervised label set has decided evidence; (v) transparently record every construction failure and unresolved candidate.

## 2. What “feasible first, then add blockers” means EXACTLY

### 2.1 Canonical base-witness generation — D2-P1, NOT run at this precheck

1. Freeze a root's **base** 2D scene `S_base`, task action, goal, supported target and initial robot state `q0`, gripper/attachment state and backend/profile/seed.
2. Plan the original target task **with the full robot** (no corrective action) in `S_base`. Accept a base only if an independently checked complete trajectory reaches the goal **and SAFE_RETREAT**, with full link/gripper/attached target, support/contact and continuous collision checks.
3. Save the **actual witness** trajectory, q(t), end states, grasp, source hashes and its continuous robot/target swept geometry as **privileged construction evidence**; do not hand its sweep to the model.
4. A base witness can be drawn from pre-existing verified records for P0 static exploration; to create fresh bases using planning, wait for D2-P1 authorization.

### 2.2 Add obstacles in a controlled, causal way

5. Find supported cells that are initially collision-free with each other, the target, fixed workspace, the robot at **q0**, and the mandatory start geometry. Place an obstacle so that it intersects the **recorded nominal witness** during some nonzero-time part of the complete robot + attached-object motion (target transport, gripper approach/carry or arm-link sweep). Record the exact collision time/segment, body pairs and earliest interruption. **This is a construction trigger and a path-specific diagnostic only.**
6. Construct a family of nested variants: `S_base`, `S_{+A}`, `S_{+B}`, `S_{+A+B}`, `S_{+A+B+C}` (when valid), plus swaps between obstacle cells, unrelated/nuisance objects and alternative initial robot states. Put new/relocated obstacle poses into a **clone**, never duplicate a physical object, and keep object IDs/provenance valid. An already placed object remains present for later edits. Record every reject reason (initial robot overlap, unsupported pose, object overlap, etc.).
7. Deliberately vary obstacle *roles*: `target-goal occupant` (easy certificate, capped fraction), `transport-path obstacle`, `grasp/access blocker`, `arm-link sweep blocker`, `staging-slot occupant`, `second independent blocker`, `possible redundant blocker`, `harmless nearby obstacle`, `helpful/harmful edit`. Use at least one successful free-goal nuisance control; do not call a plan-feasibility change an object “cause” without measured counterfactuals.
8. **CRUCIAL recheck:** a new obstacle may block the nominal witness yet allow another target IK solution, grasp or continuous path. The root's **no-repair outcome** is NOT negative until the full target teacher gives a sound *full-scope* negative certificate. A newly found full alternate success labels it POSITIVE; unresolved stays UNKNOWN in attempts and is **not released as a decided negative**.

### 2.3 Construct candidate repairs, not just obstruction locations

9. For each blocked root, predefine candidate **object/destination/order** combinations via a deterministic, geometry-based rule. Include the empty repair, alternatives (different legal resting cells), competing object subsets, same-endpoint reversed orders, and omission remainders; all are canonically validated. Candidate selection/catalogue must be **frozen before looking at that root's candidate outcomes**. Do not choose only whichever rescue actions the generator knows are successful.
10. Construct **witness-first repair opportunities**: when proposing an “intended successful” repair, demand an independently rechecked actual fixed-order robot witness from the *blocked scene* (approach/grasp, transport, place, release, retreat for each move, then original target from achieved state). A successful base target trajectory is **not** a sufficient repair witness, and may not be replayable after relocations because the robot's q changed. Check target at the actual post-relocation q, gap, attachment and object poses. Store first complete relocation witness cost *before* target selection.
11. Construct **certificate-first negative repair opportunities** using exact, sound existing checker rules: occupied goal, illegal simultaneous endpoints, a first-action placement into a still-occupied slot, checked all-grasps impossibility at the correct scope, etc. A failure of the nominal path is NOT a repair certificate. For any proposed additional connector/C-space certificate, make a separate proof-obligation review: documented quantified domain, conservative geometry, independent checker, adversarial tests and counterexample attempts. **Do not add such a certificate or convert pilot UNKNOWNs at P0.**
12. Ensure **complete informative candidate pools**, not just a collection of positive roots and trivial negatives. Include multiple successful alternatives, truly order-discriminating same-endpoint pairs, nonempty multi-move costs, singleton/joint intervention effects and nuisance zero effects with both sides proven feasible where possible.

### 2.4 Measured effects and the question of “noncontributing” obstacles

13. For fixed-robot scene effects, compare `Y*(empty | S0)` with `Y*(empty | do(I)(S0))`, holding **q0/gripper/attachment/task/other objects** fixed. Recheck both sides independently; the intervention state must be geometrically eligible. Diagnostic “teleport” is **not an executable repair**. Hold original appearance features anchored for future learner contexts.
14. Evaluate **all required subsets** of nested A/B (and selected A/B/C) interventions, not only the order of successive obstacle insertion. For a pair, record four outcomes `Y(S),Y(do(A)),Y(do(B)),Y(do(A,B))`; the nonadditive interaction needs all four decided. Removing one obstacle may show effect 0 because a second still blocks the task—do **not** conclude the first is irrelevant or universally noncausal.
15. For omission effects, compare a complete candidate repair `r` with `r\{selected actions}`, each verified afresh from its own initial scene, with omitted objects restored to stay and surviving order unchanged. These measure necessity **within the proposed repair**, not across all repairs.
16. Control `root = initial scene + robot + task`, `family = common base-witness lineage`. Group *all* nested edits, alternatives, orders and descendants of a base across the same train/validation/test split. Never split siblings across sets.

## 3. Definition of a fully decided released example

The raw generator is allowed to produce UNKNOWN attempts. **The released `DECIDED_COMPLETE` split is NOT.** Require:

- Immutable base witness proved valid, blocker placements valid, initial robot clearance and full scene-state provenance.
- For the *blocked* root: a decided original empty-repair outcome. To call it “induced infeasibility,” require original **NEGATIVE with sound certificate**, not just nominal swept-path collision. A target that reroutes successfully is a useful `REROUTABLE` control, not an induced-infeasible example.
- Each released *candidate repair* has either checked end-to-end complete witness (POS) or correct-scope independently validated certificate (NEG). Never substitute “could not find” for NEG. Mixed raw attempts retain UNKNOWN outside the released complete subset.
- Every scene edit, omission, and joint effect **promised by the pool catalogue** has both/all sides independently decided; geometrically ineligible edits are discarded at predeclaration and never mislabeled infeasible.
- For B/C `z` layouts, every **active** slot of every **included** sequence is decided, complete decision catalogue frozen and stable, exact ≤8 active z slot limit of G4B, no inactive-slot duplicate counting. A **substantive** joint pool contains at least two distinct repairs with a meaningful positive/negative or competing positive distinction; one-sequence empty/nuisance pools are reported separately and do not satisfy the primary substantive-pool quota.
- Motion cost for positive/negative-with-relocation-witness sequences from the **first complete relocation witness** only. If a candidate was certified negative before relocation and no witness exists, its cost is masked, not zero. Empty repair J=0 exactly.
- Store the raw outcome ledger **including rejected/unresolved attempts** with initial family, reason, CPU, failures and thresholds. Dataset completeness is `decided released / released`, while selection rate is `released / attempted`; **both** are mandatory. No cherry-picked success percentages, no hiding hard failed constructions.

**Scope limitation:** No finite stochastic planner guarantees a decided full continuous-motion label for every arbitrary scene. If genuinely unknown queries remain, reject the *whole declared closed pool* from `DECIDED_COMPLETE` or put it in an separately named `PARTIAL_OBSERVATION` set. Do NOT quietly drop one troublesome sequence from a predeclared pool after labels arrive. Do not loosen checks, silently change domains, or infer impossible from blocked reference trajectories. If predeclared target counts cannot be achieved with sound labels, report the gate BLOCKED and the attempted denominator.

## 4. Causal and benchmark coverage to design in the precheck

Build a fixed *construction-intent* matrix; intents are NOT oracle labels. Each family should have interpretable counterexamples. Design meaningful proportions and minimums for the **subsequent** D2 proof-of-concept and full dataset, but do not promise measured counts at P0.

| Family | Constructive mechanism | Must measure to make a scientific claim |
|---|---|---|
| D2-F0 | Verified empty-repair, clear goal, nuisance edit | Both original/edit complete target successes, Δ=0 |
| D2-F1 | Nominal target carried-object/body sweep intersects added obstacle | Whether *any alternative* target trajectory succeeds; no negative by nominal collision |
| D2-F2 | Obstacle occupies goal or is in valid target final geometry | Certified no-repair NEG, alternative successful destinations |
| D2-F3 | One obstacle obstructs manipulating another | Same endpoint assignment under opposite verified/certified orders |
| D2-F4 | Occupied staging destination | PLACE-scope order NEG vs witnessed reversed order |
| D2-F5 | Two independent blockers / redundant singleton effects | Four decided S/A/B/A+B target-only outcomes; joint vs individual effects |
| D2-F6 | Helpful/harmful/nuisance scene edits | POS↔NEG when sound, plus meaningful POS↔POS nuisance controls |
| D2-F7 | Several legal corrective destinations | Multiple complete successful repairs; measured J versus C_d and different order |
| D2-F8 | Three-step repairs | Full q-continuity across all moves, omissions and safe retreat |
| D2-F9 | Alternative robot-start state | Same objects/task, independently decided outcomes; no invented difference |

**Balance safeguards:** Limit trivially certified GOAL_OVERLAP and STATIC_ENDPOINT_INVALID negatives; target meaningful access/order/collision interactions. Include reroutable nominal-path blockers as **hard positive controls**. Vary target/goal cells, full-robot initial q, nuisance objects, exact geometry/separation, legal destination counts, obstruction type and count. Obstacle count 1→2→3→5 then independently 30–40 only after validated sparse cases; don't claim dense completeness until actually achieved. ID permutation and placement ties cannot encode labels. Keep visually identical discs honest: geometry-only baseline may win; don't claim DINOv2 necessarily adds information.

## 5. Architecture comparability and leakage audit

The dataset is **one shared dataset for A/B/C**, not three tailored training corpora. Each receives the same source scenes, candidate sequence set, root/family split, static checks and decided labels. B/C may represent the same labels as explicit active `z` outcome slots; this does not grant extra teacher outcomes. Unsupervised missing observations may be used only in a separately preregistered partial-label ablation, **not** as invented labels or substituted for the complete-pool benchmark.

Use `data.learner_tensors_v2` allowlist (or its verified equivalent). Forbid: base witness trajectory, nominal reference envelope, collision/contact time, negative-certificate kind used as shortcut, target path IK choice, grasp index, new obstruction construction mechanism, success/failure tag, candidate oracle costs, root IDs/seed, family IDs, trajectory interpolation/checker distances in learner features. Such fields remain privileged teacher/construction metadata only. At deployment all arms operate from the *actual initial obstructed scene*, not the unobstructed base or counterfactual image.

Test with *oracle poisoning*: randomly corrupt or replace privileged witness/sweep/certification fields while holding allowed inputs fixed; learner tensor serialization must stay byte-identical. Verify that changing true initial scene state changes learner input appropriately. During precheck, no trained model exists; only test tensors/schema when code exists.

## 6. PRECHECK implementation only — exact deliverables and boundaries

### 6.1 Inspect before coding

1. Inspect existing `scene.py`, `arm2d.py`/geometry, `skill.py`, `planner.py`, `verify.py`, `ordered.py`, `teacher.py`, `effects.py`, `g4c.py`, `g4c_pilot.py`, `data.py`, certificates, plotting, all configs and stored G4D/G4C witness formats. Find exact APIs for validated **target-only complete witness**, trajectory q/attachment interpolation, independent continuous collision replay, obstacle cells, scene cloning, static geometry and root identity. Verify actual names; do not invent them.
2. Identify a **real existing** base scene + target trajectory witness from stored archives (e.g., G4C-P1 `r00` empty-repair POS or G4D `R0/R1`), and verify its provenance and actual robot start/end states. If the stored witness lacks sample density/geometry to compute conservative sweep collision accurately, mark that capability UNAVAILABLE rather than drawing fictitious collisions.
3. Inspect the 20 pilot UNKNOWNs by existing reason and identify which are potentially avoidable through constructive case design versus require an unproven negative cert. **Do not relabel or rerun them.**
4. Produce a **migration interface map**: which existing functions can be reused unchanged, where one small constructive generator module would belong later, and where separate audit/judge functionality should reside. No new code path to the teacher in P0.

### 6.2 Constructive dry-run/precheck (NO fresh planner calls)

5. Implement only a tiny **pure, deterministic, testable** prototype (or reuse existing geometry functions) that reads an existing archived feasible target witness and proposes legal obstacle insertions against its **recorded full-body path**. It may use deterministic static collision queries/replay; it may **not** search for a different target path or label the new root as globally infeasible. A proposal must remain collision-free at the initial robot pose and other resting objects. Save `blocks_nominal_witness` separately from `target_task_status=NOT_RUN`.
6. Produce nested variants at *construction-plan level* from one archived base: 0, 1, 2 and optionally 3 blockers, plus (where supported) a nuisance and an alternative destination. If no eligible insertion exists under the real 2D geometry/profile, explicitly document why and mark precheck BLOCKED rather than manufacturing one.
7. Propose a deterministic predeclared query catalogue: empty, selected one/two/three-move sequences, their same-endpoint reverse orders, omission remainders, fixed-robot single/joint scene edits and no-change/nuisance controls. **Do not run the teacher to assess them in P0.** Validate strict sequence grammar, unique/stay ID, candidate cells, eligibility, context identities and complete bounded z layouts. Any catalogue truncated to fit ≤8 slots must be selected by a frozen rule **before** outcomes, not after.
8. Produce an **example dry-run manifest** for 1–3 archived-base lineages, if existing witness artifacts permit: state IDs, parent witness hash, candidate physical locations, nominal path collision diagnostic, seed, scene/robot start hashes, predeclared repairs and intervention pool layouts. Only `PRECHECK_STATIC`, `BASE_WITNESS_REPLAYED`, and `NOT_RUN` are allowed as new statuses. Historic positive labels remain labeled `ARCHIVED_EVIDENCE`, never relabeled new results.
9. Run invariant tests and add a deterministic preview: initial planar 3R arm, target/goal, nominal **recorded** robot/attached-object trajectory, proposed obstacle cells, collision interval and ghost relocations. Annotate prominently **ARCHIVED VERIFIED NOMINAL TARGET TRAJECTORY / CONSTRUCTED OBSTACLE PREVIEW / NEW TARGET FEASIBILITY NOT RUN**. Never draw fabricated planner paths or new positive/negative labels.

### 6.3 Required unit tests (all without new teacher/planner calls)

- Same base-witness bytes + seed + config → same proposals, hashes and visualization; changed base version/hash rejected.
- Obstacle insertion leaves robot q0 collision-free; supported, inside workspace, distinct from target and other objects; actual target remains present; no clones.
- Exact nominal swept-body collision check includes **robot links, gripper, attachment and carried target**, not only the end-effector/target center. Conservative path interpolation; if unavailable mark diagnostic unverified.
- At least one deliberately constructed **nominal-path collision** fixture and one reroutable **logical control** where a nominal collision must NOT be labeled target-infeasible. (A synthetic abstract alternative-path fixture is sufficient to enforce the semantic test; do not claim a new robot trajectory.)
- Nested scene variants preserve object IDs/context and are reproducible; adding B does not overwrite A or change q0 or goal.
- Scene edits keep q/gripper/attachment/target and original appearance anchor; overlapping/unsupported edits rejected, not negative.
- Omission returns omitted objects to initial stay and preserves remaining order. Same-endpoint reversed sequences have distinct ordered signatures.
- No new `NEGATIVE`/`POSITIVE` label for constructed scenes; `blocks_nominal_witness` is not a feasibility label; UNKNOWN raw rows cannot be hidden.
- B/C active outcomes ≤8, no inactive multiplication, and all A/B/C information rights equal. Substantive-pool rule distinguishes multi-repair from trivial empty-only pools.
- Split keyed by base-witness **family lineage**, not descendant scene or intervention. Train/validation/test separation all related descendants.
- No privileged sweep/trajectory/certificate/seed or construction class leaks into future learner tensors; import guard: proposed generator scorer has no teacher callback.
- Frozen original G4C parent plan/pilot, configs and historical hashes unchanged; existing regressions and archived replay outputs unchanged.

### 6.4 Outputs and gate decision

Write in a **new** namespaced directory such as `runs/g4c_d2_precheck/` (do not write to G4C-P0/P1):

- `source_audit.json` (Git, source/witness/profile hashes, baseline tests, missing interfaces).
- `protocol_proposal.md` (D2 generation algorithm, label semantics, alternative-path counterexample, accepted positive/negative certificate kinds, intended fully closed pools, train/test family split and complete-data definition).
- `construction_attempts.jsonl` (all dry-run candidate placements, accepted/rejected reasons; **no new teacher result**).
- `precheck_variants.json` and `precheck_queries.json` (pure frozen preview, proper NOT_RUN statuses).
- `precheck_coverage.json` (planned type coverage vs actual static eligibility; **all label outcomes NOT_RUN**).
- `precheck_overview.png` (scene-backed, recorded witness vs hypothetical blockers; clearly scoped).
- `budget_request.json` (required numbers **all proposals**, NOT authorization; per-unit CPU, cancel margin, aggregate CPU, worker count, per-unit/global wall, node/skill/target caps, expected roots/variants/query units, explicit stop-after-POC).
- `manifest.json` with SHA-256; test log and commands; one **next unused** numbered stage report (likely `responses-phases/0015_G4C_D2_precheck.md`; verify next number in repo).

The report MUST contain: status `G4C_D2_PRECHECK_PASS`, `BLOCKED` or `FAIL` with evidence; candidate placement acceptance counts and rejected reasons; actual stored witness used; whether full-robot nominal swept collision checks worked; **clear statement that all newly constructed target/repair labels are NOT_RUN**; risks of sample selection, trivial-cert dominance and sound negative coverage; honest proposal for a **tiny D2-P1 proof-of-concept** that actually runs new target/relocation checks *only when authorized*.

**Design the follow-up D2-P1 POC, do not execute it:** initial proposal 2–3 independent base-witness families with perhaps 4–8 nested variants each, several repair destination/order candidates per variant, and a small closed B/C query catalogue. Freeze exact counts and all numerical guard fields after the precheck establishes realistic unit counts. The follow-up should require (a) a verified base witness for each family; (b) at least one sound target-blocked NEG root if constructible; (c) a fully witnessed repair POS for that same blocked root; (d) one decided order contrast or an explicit failure report; (e) a complete substantive B/C pool if constructible; (f) full construction/discard audit. **Do not claim a POC target if physical evidence does not support it.**

## 7. Acceptance / go-no-go

`G4C_D2_PRECHECK_PASS` requires:

1. Verified actual repository state, unchanged prior results and original 20-root parent plan.
2. A provenance-checked archived **target-only full-arm feasible witness** identified and replayed/validated without new search.
3. Reproducible, geometrically eligible new obstacle-placement previews, nested variants and candidate correction/intervention catalogues.
4. Nominal-path collision diagnostic validated against full robot geometry **or honestly marked unsupported with gate blocked**; initial robot remains collision-free.
5. Strict semantic guard that `nominal swept collision ≠ target-task infeasibility` and no new fabricated POS/NEG labels.
6. Data-release/attempt-denominator policy including group-wise leakage prevention and B/C substantive full-pool rule.
7. Explicit source/budget/provenance plan, focused tests, archived replays and a valid stage report, with new dataset/teacher execution stopped.

`BLOCKED` if archived trajectory/sweep replay is unavailable, collision checks can't be correctly scoped, or no legal obstacle-placement preview can be constructed without changing physical rules. No toy point-robot fallback silently passes the gate. `FAIL` on invariant/test/provenance violations.

**STOP AFTER P0.** Do not run new base trajectories, new teacher labels, 2D bulk generator, full G4C remaining 15 roots, neural architectures/training, 3D or hardware. Await explicit numerical authorization for D2-P1.
