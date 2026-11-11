# 0044 — P16: Evidence-Locked Dual-Track Methodology Completion for B and D

**Binding implementation and scientific protocol for Claude Opus 5.5 High**  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Verified starting commit:** `20f775483077a568efb225f22aa93ca619160c53` (P15 final)  
**Scope:** One shared physics/benchmark layer; two independent learned-method tracks; staged development and prospective 2D validation; a concrete 3D migration specification, **not** an unvalidated full 3D port.  
**Status at launch:** P15 engineering substantially complete; scientific claims PARTIAL. This instruction authorizes no reinterpretation of historical results and no changes to P10–P15 evidence.

> **Core directive.** Develop **both** approaches to the best *evidence-supported* methodology, independently. Do **not** resurrect discredited factors merely to match the original proposal; do **not** abandon a method merely because earlier comparisons were negative. Implement each cleanly, verify the intended claim, and accept negative/underpowered results. Physical and causal claims must be tied to exact witnesses and valid counterfactual evidence.

---

## 0. Read first: authority, history, and non-negotiable conclusions

### 0.1 Read these sources in chronological and technical context

1. Original intent and mathematical conventions: `latent_causal_tamp_methodology_v1_8.md`, `latent_causal_tamp_implementation_guide_v2_0.md` (if present in the workspace), older `latent_causal_tamp_methodology_v1_7.md` and `latent_causal_tamp_implementation_guide_v1_9.md` only for provenance. The original five-factor description is **not** an instruction to keep every factor in production.
2. Mathematical and source evolution: `responses-phases/0022_*` through `0036_*` and implementation contracts `0037`–`0043` under `instruction-phase-md/` (read files that actually exist; record missing references).
3. High-value corrected decisions: `responses-phases/P12_2D_SCIENTIFIC_DECISION.md`, `responses-phases/0066_*`, `responses-phases/P13_2D_FACTOR_SCIENTIFIC_DECISION.md`, `responses-phases/0067_*` through `0072_*`, `responses-phases/P14_SCIENTIFIC_AND_D_REARRANGEMENT_DECISION.md`, `responses-phases/0073_*` through `0081_*`, `responses-phases/P15_D_REARRANGEMENT_AND_B_CALIBRATION_DECISION.md`.
4. Reproducible artifacts, *not just narrative*: frozen model checkpoints, prediction snapshots, root-level outcomes, label provenance, P12 prereg correction, P13 factor comparisons, P14 admission/counterfactual executions, P15 matched physical probes, multimode transfer, prereg/amendment, and 32-root prospective results.
5. Source modules to audit: `unique_factor.py`, `unique_factor_keyed.py`, `abc_models.py`, `d_blockers.py`, `learn_data.py`, `p13_factors.py`, `p14_sweep_index.py`, `p14_d_search.py`, `p15_retarget.py`, `p15_lookup.py`, `p15_search.py`, `p15_bench.py`, underlying `motion.py`, `geometry.py`, `skill.py`, `data.py` and certificate verifiers.

**Authority order:** physical evidence + sound certificate scope > frozen primary experiment/prereg > validated corrections in a newer report > earlier preliminary report > original conceptual speculation. A later explanation does not silently supersede earlier raw data. Write a provenance map and flag any discrepancy rather than overwriting history.

### 0.2 Immutable evidence ledger — preserve these judgments

| Question | Established evidence / default decision |
|---|---|
| Order sensitivity / F2 | Useful. P13 targeted order effect substantial; P14/P15 ranking/physical comparisons retain an advantage over F2-removed variants. **Keep an order-aware representation**; no claim that B's particular module beats A/C on every order endpoint. |
| DINOv2 | Predictively useful in the tested 2D setting. **Keep** with explicit frozen appearance controls; vision alone is not evidence of causal abstraction. |
| Physical-query keying | Enforces catalogue/omission consistency; unkeyed representation violates invariance. **Keep keyed identities**, even when unkeyed NLL is lower. |
| Learned F1 static head | Static discrimination/decision route not supported. **Drop learned head; retain analytic static certification/veto.** |
| F3 scene-pair | No independent practical benefit, reversal in P12/P13, mean harm not conclusively established. **Drop** from lean B. |
| F4 omission-pair | Apparent execution gain primarily tied to admission. **Drop from default lean B**, preserve archived factor for sensitivity only; do not claim omission causality from admission results. |
| F5 combined pairwise + higher-order | Challenge likelihood benefit, major natural-mix harm, no executed gain after matched admission. **Do not ship as default**. An isolated generic-only pair term is a genuinely untested hypothesis, to be tested with fresh matched retraining if budget/power allow. |
| Higher-order F5q | Underpowered / no independent deployment demonstration. **Defer**; no default component. |
| J learned travel head | Suggestive but underpowered; earlier sign error and oracle-filtered regret corrected. **Do not require learned J**. Use physically measured robot travel in shared optimization; any learned J is an explicitly optional future hypothesis. |
| D pair term | Incremental benefit not established. **D-pairless is the lean learned reference**; keep full D as frozen comparison. Do not assert that a pairless model learns blocker interaction. |
| D diagnoses blockers | Feasibility-gated blocker F1 0.903 on P14 decided cohort; union of minimal sufficient clearing sets, **not** necessary-object intersection, global physical impossibility, or a unique minimal repair. |
| Arbitrary-target D | P15 rebuilt correct target/goal/vision/current-q inputs; raw underpredicts feasibility. DEV root-CV scalar calibration reported BA 0.924. **Temporary-target blocker marginals are not validated**. Recalibrated feasibility is an engineering result, not universal generalization. |
| B on feasible originals | Only 0.543 empty-repair TOP1 on 27 natural feasible originals. **Critical defect to address on genuinely fresh mixed data**. Validation-only temperature/bias alone did not fix it. |
| B advantage over A/C/ablations | Historical differences largely due to admission. Keep tests of candidate ranking, coverage, threshold and execution distinct. B vs geometry reversed on P12 holdout. |
| D search guidance vs geometry | P15 32 new roots: both 27/32, zero discordances; −1.7% motion calls vs 20% intended reduction. **No demonstrated incremental advantage**. This is not a proof of equivalence. |
| Motion lookup and search | 4,821 indexed witnessed relocations, 1,163 motion modes, 330 other-root transfers: top-1 50.6%, any 72.4%, 53 rare-mode rescues; 0 replay failures in P15 benchmark. **Keep** as non-learned shared infrastructure. |
| Search certificates and optimality | UNKNOWN is not certified infeasible. Minimum-move/travel proofs only apply to a fully adjudicated **declared finite graph**, not continuous space. |
| Physical scope | Logical, causal high-level infeasibilities (blocking target retrieval, access chains, occupied slots, constrained placement), **not** a benchmark designed around rare IK failures. |

**Any reversal of a judgment requires a new explicit hypothesis, controlled matched retrain where applicable, independent test cohort, and a new versioned addendum. Never rewrite P10–P15 outcomes.**

### 0.3 Important source-specific corrections to retain

- P12's preregistered κ endpoint is `abs(mean_seed(kappa_hat) - kappa_true)`, **not** `mean_seed(abs(kappa_hat-kappa_true))`; keep the corrected P13 rerun. Always show κ≡0 baseline.
- P13 F3 mean CI overlaps zero despite its directional root-sign reversal; no demonstrated mean harm.
- `B-F5spm` removes generic **and** higher-order coupling. It is not generic-only.
- P14 validation-coverage matching did not guarantee equal *test* coverage; distinguish the two.
- P14/P15 teacher-labelled J choice correctness is not executed success or deployed travel regret.
- P15 `B-F3pm` / `B-F5spm` have separately trained parameter-matched checkpoints in the P13 archive. If a report describes them merely as inference masks, verify and correct that **wording** in a new erratum; do not alter the checkpoints.
- P15 prospective paired bootstrap success-difference CI `[0,0]` arises from observed zero discordances; it is not a population equivalence interval or equivalence test.
- Retrospective roots, P13 test roots, and any roots already used to diagnose the design remain **development/exploratory**, never converted into new blind confirmation.

---

## 1. The two research methods and their clean interface

### Shared physical task

Given a *single observed initial scene* `S0`, robot configuration `q0`, original target `T`, goal `g`, movable scene objects, static constraints and a defined grasp/path protocol, determine whether the original task is currently executable. If not, find and verify a sequence of relocations that makes `pick-and-place(T,g)` executable. Check the actual scene after each committed relocation. No clairvoyant labels or teacher plans may enter runtime observations.

- Physical states include every object's pose/shape/class and the robot's configuration/held-object state; simulate hypothetical states with exact occupancy and robot-state updates.
- A relocation is `(object, destination, grasp/motion witness)`; a complete plan is an ordered list and final verified target action.
- Optimize **lexicographically** `(number_of_relocations, measured_robot_joint_travel)` where the *non-learned optimization* needs an objective. No subjective risk coefficient. Travel includes transit to grasp, transfer, placement, retreat, and target action; do not treat source–destination Euclidean distance as complete robot travel.
- Feasibility statuses are VERIFIED, accepted **scoped** CERTIFIED_INFEASIBLE, STATIC_INVALID, or particular UNKNOWN reasons. Exhausting candidates is not universal infeasibility.
- Goal success must be from independently replayed, certifier-accepted **full motion witnesses**, never from learned prediction alone.

### B — Lean, order-sensitive keyed energy model for **complete repair queries**

**Learned scope:** conditional distribution/energy of a candidate *ordered* corrective-action query, including the empty (no-move) action. This method directly evaluates a complete proposed repair order and its outcome rather than recursively predicting blockers and relying on D to decide object membership.

**Default architecture:** DINOv2 scene features + numeric target/object/robot/goal context; keyed variable identity for one physical query; scene/query unary energies and **order-sensitive sequence encoding (F2/GRU or justified equivalent)**; sound static veto outside learned head. Do not include learned F1, F3, F4, higher order or generic F5 by default. Preserve isolated factor controls as archived variants. An optional *generic-only* pairwise term must be trained/evaluated as a newly preregistered arm; until then no claim it helps.

**Mathematical contract (must match code):**

- Let `Q(S)` be a **non-privileged** finite catalogue of proposed repair queries `r`, including the empty repair. Each *unique physical query* has exactly one binary outcome variable `y_r` and a consistent identity even when referenced by other candidate/omission contexts.
- Construct conditional energy `E_θ(y | S,Q)`. At a minimum, per-query energies are functions of scene and **ordered** repair (not just unordered object set). If generic coupling is disabled, explicitly state that the resulting joint is factorized beyond shared encoder/identities—**do not call it demonstrated interaction reasoning**. If enabled, parameterize only terms permitted by the frozen hypothesis and normalise exactly (or use a mathematically documented unbiased/tractable alternative; do not quietly substitute independent BCE and call it a joint Boltzmann loss).
- `P_θ(y|S,Q) = exp[-E_θ(y|S,Q)] / Σ_{y'∈{0,1}^{|Q_unique|}} exp[-E_θ(y'|S,Q)]` **only when this is computationally tractable**. For no-coupling unaries, exact analytic factorisation is fine. For partial labels, marginalise unknown labels instead of assuming 0. Never duplicate a query's likelihood via repeated catalogue appearances.
- Train by the correctly scoped outcome NLL; specify separately and justify any genuinely necessary auxiliary (sequence/marginal/calibration) losses. No hidden teacher labels at inference; no leak from held-out repair outcomes into the feature builder, sampler or threshold selection.
- At inference, predict feasibility for the **empty query first**; select only admitted corrective sequences if appropriate, under a validation/calibration-only rule. Preserve the distinction between feasibility gating, candidate ranking, fewest relocations and travel. If several physically plausible sequences exist, rank/select without physics oracle access; then perform the common physical certification. Define behavior for `ABSTAIN` separately from `EMPTY_REPAIR` and from physical UNKNOWN.

**B's independent contribution under test:** whether an order-sensitive keyed energy representation can learn to evaluate/choose complete corrective interventions across varied scenes and maintain correct zero-move decisions, beyond A/C/SF, order-off, geometry and a non-learned candidate ranker. Do not simply inherit D's recursive search and call it a different learning contribution.

### D — Pairless Boltzmann feasibility and **blocker membership** plus conventional rearrangement search

**Learned scope, and no more:** `P_D(target_feasible | S,T,g,q)` and a conditional Boltzmann distribution over blocker-set membership on a declared candidate object pool. Default to unary/pairless learned blocker energy unless isolated new evidence justifies the pair term. Reuse exact enumeration only within explicit tractable pool limits.

**Explicit learned distribution and loss (verify signs and exact normalization against source):** with a bounded movable pool `M` and binary blocker-membership vector `b`, the lean pairless model parameterises a target-conditioned feasibility logit `u_φ(S,T,g,q)` and blocker logits `a_i(S,T,g,q)`. For the pairless default, `P_φ(b | S,T,g,q, y0=0) = exp(Σ_i a_i b_i) / Σ_{b′∈{0,1}^{|M|}} exp(Σ_i a_i b′_i)`, equivalently a product of Bernoulli factors; **do not claim learned inter-blocker coupling**. In the archived paired control only, add the symmetric `½ Σ_{i,j} w_ij b_i b_j` term and exact bounded normalizer. `P_φ(y0=1)=sigmoid(u_φ)`. The loss is a feasible-original BCE plus a conditional blocker-mask NLL **only where the mask is well defined**, with the historical `λ_B` documented; partial or ambiguous masks must be masked/marginalized, not silently treated as all-zero negatives. Check that inference reports both `P(b_i=1|y0=0)` and the feasibility-gated `P(y0=0)P(b_i=1|y0=0)` without confusing them. If the actual source disagrees, document the discrepancy and its implications before modifying the model.

**Precisely distinguish:**

- Union of participating objects across minimal sufficient **clearing subsets** (within that intervention lattice, provenance and target/goal), versus the intersection of objects necessary in every such subset.
- `NO_CLEARING_SET_WITHIN_POOL`, incomplete/UNKNOWN lattices, operational budget negatives, and genuine no-blocker feasible originals. In particular, do not train a `NO_CLEARING_SET` record as confidently proving that every physical obstruction has zero membership. Audit the existing `minimal_sets()` target semantics and build a safe training-label mask/weight protocol.
- Original target feasibility versus temporary obstacle-as-target full pick/place; use the exact rebuilt scene/goal/current robot configuration/visual inputs. Calibrated temporary-target **feasibility** is not proof that temporary-target **blocker marginals** are accurate. Validate marginals independently or use only the feasibility component for recursion until labels exist.

**Non-learned correction:** D supplies *priority/diagnostic evidence*; a geometric search generates movers (including previously hidden enabling objects), destination slots, motion modes and trajectory fallbacks and jointly optimizes order+destination+motion. D must not hard-prune branches from uncertain diagnosis; score/order them, optionally provide a defensible soft heuristic. Geometry, uniform, D-pairless, frozen D and limited oracle baselines get the same complete candidate graph, budgets and certifier.

**D's independent contribution under test:** whether learned blocker diagnosis, especially recursive target-conditional diagnosis, reduces **verified search effort or increases bounded-budget task success**, as compared to identical conventional rearrangement search without learned blockers. Existing P15 results are negative/underpowered and remain so.

### Scientific separability / potential papers

- B focus: **learning and inference over complete ordered intervention outcomes**; factorisation, supervision, calibration, no-op and distributional generalization. Potential reasoning / learning paper *only if distinctive incremental evidence exists*.
- D focus: **learned diagnosis integrated into non-learned physical rearrangement**, with similarity-indexed trajectory reuse as existing infrastructure rather than assumed novelty. Potential robotics paper *only if learned diagnosis adds a reproducible advantage and technically distinct contribution*.
- Both may share simulation, benchmarking and common controls. **Do not reuse the same core novelty or primary experiment in two submissions**; keep separate claims, training variants, result tables and limitations. Do not promise acceptance or publishability in advance.

---

## 2. P16-0: non-mutating audit, hashes, and implementation/evidence map (mandatory first)

1. Verify `git status --short`, `HEAD`, `origin/main`, exact P15 final SHA and clean/unrelated worktree modifications. Two user-deleted root PDFs and any untracked user instruction files were previously noted; do not stage, restore or delete them without explicit instruction.
2. Hash P10–P15 decision docs, frozen predictions/checkpoints/manifests/ledgers, the current physical certifier, and P15 working search/lookup modules. Store an **immutable historical-source manifest**; do not change `runs/p10`–`runs/p15`, `responses-phases/0022`–`0081`, or historical visualisations.
3. Produce a compact source → equation → inference use → supervised label → test → current verdict matrix **for B and D separately**. Include paths and function/line ranges. If an original mathematical specification conflicts with a later validated correction, record the conflict and resolution in P16 documentation only.
4. Audit the P15 action pool source, notably `p15_bench.run_arm`: `movers` are derived from `root['items']` with `kind=='ORDERED_TEACHER'`. This is a declared *catalogue-restricted* protocol but **not a general deployable method receiving scene-only input**. Preserve it for historical replay, then create a privileged-free action pool built from `S0,T,g` and physical object properties for both methods. Confirm no teacher repair sequence is read by production candidate generators or guides.
5. Verify identity and scope of all statuses, full trajectory record consistency, witness-mode endpoints, start-transit, physical query fingerprints and calibration splits. Audit deterministic planner seed versus wall-clock cutoff, including the P15 prospective replay variation.
6. Run historical tests/replays once under a recorded resource cap; **no bulk teacher, training or prospective labels in P16-0**.

**Gate:** documented source map, no changed historical hash, and no unresolved runtime privileged-input path in the proposed scene-only APIs. A failed gate blocks later scientific claims, not necessarily safe refactoring.

---

## 3. P16-1: deterministic and efficient shared physical planning (before method comparison)

The online fallback planner in P15 used wall-clock stopping, so identical state-keyed calls can change results under varying machine load. Make a determinism-capable mode:

- Use controlled seeds, fixed attempt/iteration/sample limits, fixed expansion and collision-check counts, stable sorting and deterministic tie-breaks. Capture library versions, CPU model and numeric tolerance. Remove wall-clock timing from **physical success adjudication** in the controlled mode; retain a separate process watchdog as a safety resource cap that returns `UNKNOWN_BUDGET`, never `CERTIFIED_INFEASIBLE`.
- Ensure a fixed physical query yields the same status, selected trajectory hash, terminal `q`, certification outcome and measured travel in 3–5 independent repeated runs (including parallel-load runs if feasible). Where an underlying subroutine is not deterministic, isolate/report it and gate its contribution.
- Pre-check sound static impossibility certificates and cheap geometry before expensive online motion queries; do not convert a cheap rejection into a universal infeasibility assertion. Cache exact decided query results keyed by *all* physical state fields, planner configuration and task parameters. Unknown under a truncated budget must not be silently treated as permanent negative.
- Improve start transit: a failed straight joint-space connection to a stored witness must remain UNKNOWN_TRANSIT. Add a **bounded alternate-transit planner** to connect current `q` to witness start; certify it, account for its travel and budget separately. Compare lookup-only direct-transit, lookup+alternate-transit and pure online fallback on fixed roots.
- Avoid introducing learned swept-volume, destination or ordering policies. Make all method comparisons see exactly the same motion witnesses, deterministic queries and budgets.
- Instrument CPU-s, wall-s, motion checks, planner iterations, query/cache counts, reason codes and trajectory hashes per edge.

**Adversarial tests:** seeded parallel replays; same occupancy with different `q`; alternate-transit found when direct fails; collision in middle of robot-link sweep; held-object collision; cache cross-root/goal identity; unknown not promoted; exact replay.

**Gate:** deterministic repeated outcomes on a preregistered representative set; otherwise only engineering tests and exploratory results, no confirmatory D/B comparison. Retain existing nondeterministic historical mode unchanged.

---

## 4. P16-2: shared scene-only task API, candidate library and benchmark

### 4.1 Runtime interface; no teacher catalogues

Create *one* minimal callable interface, e.g.:

```
Task = {scene, original_target, goal, robot_start, object_metadata, allowed_actions, verification_contract}
propose_movers(Task, current_state) -> candidate movable object IDs   # derived from state, not labels
propose_slots(Task, current_state, object) -> physically admissible destination candidates
verify_move(...)-> VERIFIED(witness, q_end, travel) / CERTIFIED(scope) / STATIC_INVALID / UNKNOWN(reason)
verify_target(...)-> same status semantics
```

- The pool may include **every movable non-target object**, subject to a declared complexity cap. No inclusion based on a ground-truth `ORDERED_TEACHER` sequence or original clearing-set union.
- If using cheap geometry to reduce the pool, it must be declared as a shared algorithmic component and tested for false negatives; otherwise allow recoverable widening, not permanent pruning.
- Destination candidates: vacant static-valid slots plus previously freed source slots and safe buffers; update hypothetical occupancy at every move. Record which slots were omitted due to bounded candidate generation. A temporary buffer may become free/occupied over the sequence.
- Correctly treat goals, fixed structures, gripper/robot sweeps and obstacle size. Record `slot` separately from exact final object pose in any future non-grid variant.
- Default small benchmark still finite (for tractability), but add a separately tracked **expanded domain** supporting ≥4 relocations, newly discovered enabling movers, and when physically necessary, relocating an object twice. Prevent loops with state-aware dominance, not a universal move-once ban. Old catalogue-limited P15 protocol stays a regression baseline.
- The model-free shortest-path baseline and both learned approaches must be given equal access to scene-only candidate generation, destination choices, planner iterations and physical verification.

### 4.2 Benchmark content (physics-first, unbiased with respect to model predictions)

At least the following **development** mechanism families, each with feasible-original controls, must be constructible and visualized:

1. Target initially executable (0 moves), with nearby decoy objects.
2. One necessary blocker (1 move), several potential valid destinations.
3. Two complementary blockers: neither alone clears the target.
4. Alternative sufficient clearing sets: moving A **or** B works; blocker union differs from necessary intersection.
5. Access chain: C must be displaced before B can be picked, then A (real order reversal physically witnessed).
6. One relocation can block a future arm sweep although its endpoints are free.
7. Relocating a blocker to the wrong vacant slot blocks the original target or a later move; joint slot assignment required.
8. Buffer reuse / freed source slots; at least one verified case requires moving an object twice within the expanded finite action domain.
9. Two/three blockers with independent physical witness/provenance; a nontrivial sequence length rather than overwhelming single-move cases.
10. Difficult negative or unresolved cases, strictly distinguishing certified task impossibility from finite planning failure.

Construct using sound geometry constraints **independent of model scores**. Track acceptance attempts, random-unfiltered control strata, exact fingerprints and saturation. Do not infer universal feasibility/infeasibility from merely trying 64 grasps. Negative labels must be scoped to sound certificates or explicitly operational planning budgets.

### 4.3 3D migration design (gated, no speculative results)

Create a separate, concise **3D implementation-readiness specification** after the 2D scene-only API passes, including shelf cubbies, closed-side bins, objects in front of drawers/doors, slot conflicts, constrained vertical extraction, stacks and nontrivial object/gripper 3D geometry. Specify robot base, joints, top/side/angled grasp candidate sets, closed/open link sweeps, end-effector+carried-body volume, target-goal semantics and certificates valid in 3D. Do not assume 2D sector certificates translate to 3D. No large 3D experiment or real-robot claims in P16. If a pre-existing 3D simulator is available, an isolated non-learning one-scene smoke may be considered only after passing the explicit gate and inside the reserved cap; otherwise specification/test fixtures only.

---

## 5. P16-B: complete the **lean B** methodology, without restoring rejected factors

### B0. Reconstruct the mathematical and runtime contract

- Identify the exact default network and source entry points; test the full energy computation, gradients, finite/analytic partition function, keyed identity, shared scene outcome nodes, missing-label marginalization, renormalization, batch consistency and order sensitivity. Distinguish the conditional exact joint `P_B(y|S,Q)` from per-query marginals and intervention success probability.
- Specify the maximum exact-enumeration size; ensure silent capacity truncation cannot change physical-query identity. If the default has only unary terms, use exact factorized likelihood and accurately describe the absence of learned pairwise interactions.
- Add a **real no-op query** (the zero-move target action) to every eligible scene. Admission and ordering of the no-op must not depend on arbitrary catalogue placement or existence of other duplicated entries.
- Derive all candidate ordered sequences (object, destination, grasp/motion options as applicable) from the scene-only shared generator. Do not score only plans that a teacher pre-verified; generation and ground truth are separate.

### B1. Minimum defensible model and comparisons

- **Production candidate:** DINOv2 + numeric context + keyed identity + order-sensitive F2 representation + learned scene/query unaries; analytic static veto. **No** learned F1, F3, F4, F5q or learned J. Generic-only F5 is a separate fresh experimental arm, *not* a preinstalled feature.
- Controls: historical full keyed B (frozen), A, C, SF, B-F2/no-order, geometry-only, random/fewest-moves baselines; optionally separate matched-capacity generic-only-coupling arm if predeclared and budgeted. Shared candidate pool; clearly mark original P13 trained checkpoint vs any new model.
- Train on physically grounded **mixed** scenes containing feasible originals and infeasible originals, multiple repair lengths, neutral interaction controls and order-sensitive mechanisms. Do not train exclusively on hard infeasible challenge scenes.
- For a genuine optional generic-only F5 test, remove only `cpl`, **leave any controlled HO configuration identical on both sides**, retrain 3 matched seeds and capacity-match. Since HO is deferred, cleanest test is *generic on vs generic off, HO absent in both*, with identical data/candidates/training. No generic-effect inference from `B-F5spm` alone.

### B2. Loss, admission and selection validation

- Define the primary supervised likelihood, optional clearly weighted auxiliaries, and validation-only choice of checkpoints. Log gradients separately for active factors; verify that no inactive head is claimed useful.
- Use a **separate calibration split**, not blind test labels, to fit any temperature/bias and thresholds. Compare historical fixed rule, fine-grid coverage-matched thresholds, false-admission constrained choice, and **no-op-first rule**. Rule selection is a development choice and must be frozen before confirmatory test.
- Treat the exact **empty repair** and `ABSTAIN` as different outputs. Predicting a task already feasible but unnecessarily moving an object is an explicit error, not a success. An incorrect no-op when infeasible is also an explicit error. Preserve rates of both mistakes.
- Compare: original-feasible no-move recall and unnecessary relocation rate, original-infeasible repair success, physical TOP1 verified success, attempted-root coverage, success-conditional-on-attempt, candidate ranking at common decided queries, Brier/NLL/ECE where support permits, four-bit joint NLL on all-feasible neutral controls, κ predictions with κ≡0 baseline if applicable, across seeds and families.
- Record both validation-matched coverage and actual test admission; never describe them as interchangeable. If test choices were not physically executed, label metrics teacher-scored or unknown—never impute executed success.
- Natural distribution is synthetic unconditioned, **not** real-world prevalence. Report separately from constructed challenge distributions.

### B3. Prospective B gate

- Pilot new scene-only data generation and teacher costs *before* freezing a confirmatory cohort. Use 3 seeds only when data and compute gates pass; if not, complete a valid pilot, mark powered confirmation NOT_RUN/UNDERPOWERED.
- For a prospective zero-move improvement hypothesis, target roughly **≥60 physically decided feasible originals**, as suggested by the P15 power analysis (recompute power against actual paired discordance and class balance before freezing). Include infeasible originals and mechanism-disjoint held-out scenes to detect lost corrective ability.
- Predeclare primary comparison(s) and minimum practically interesting effect; adjust multiplicity if co-primary. Do **not** assume B must beat A or geometry; report if it does not. No post-unseal selection of successful families or thresholds.

**B gate:** exact maths/inference and no-op unit tests pass; scene-only candidate generation; fresh calibration-split frozen policy; physical held-out evidence if resources permit. Otherwise mark methodological completion separate from scientific effect.

---

## 6. P16-D: complete the **pairless D + non-learned rearrangement** methodology

### D0. Correct target-conditional learning and label semantics

- Default **pairless** blocker-head plus feasibility head; frozen full D is a historical comparator. No new pair term unless preregistered independent evidence.
- Reuse P15 `retarget_scene/build_record` semantics for every `(scene, temporary target, intended destination, current robot q)` and DINOv2 rerender. Test exact identity on original queries and target/goal/q changes.
- Keep `feasible_original → empty mask` distinct from `no clearing subset found within limited intervention pool → UNKNOWN/unsupported blocker union`. Confirm soundness of every necessary/union label; distinguish `operational` vs `proof_grounded`; train only where valid or give explicitly justified weights/partial-mask loss.
- **Physically evaluate temporary-target blocker marginals** against complete and genuinely matched small intervention lattices, not only temporary-target feasibility recall. If this is infeasible under budgets, recursion may use only the DEV-calibrated *feasibility* and generic geometry for blocker ordering; it must not be described as learned recursive blocker causality.
- Test any DEV-only calibration on fresh target-disjoint scenes without refitting to test labels. If performance remains inadequate, optionally train the same D architecture on arbitrary targets with fixed loss/splits. Do not force retraining merely for a positive experiment.

### D1. Complete non-learned joint optimizer

- Search state: all object poses/slots, `q`, gripper/attachment as required, moved counts and remaining budget. Support generating movers from physical scene metadata, not `ORDERED_TEACHER`, and dynamically reconsider enabling obstacles. Allow bounded repeat moves in the separately declared expanded domain.
- Candidate destinations adapt after every hypothetical relocation; collision- and static-validity filters are computed on the current state. Slot conflicts and released source slots are handled correctly. No assumption that all blockers in a union must be moved.
- Retrieve scene-similar **multiple** joint-motion witnesses by local 3×3/4×4, global occupancy, absolute source/destination (fixed-base restriction), radius/shape, terminal `q` and grasp compatibility. Ranking by independent support/similarity/travel is heuristic; retain rare modes and physically certify each. **Never take common/intersection swept cells as a replacement for the actual motion sweep.**
- Include certified alternative transit to witness start as a possible edge and terminal-q-dependent future costs. If lookup fails, call the bounded deterministic online planner, recording UNKNOWN if not resolved. Online path options and caching must be consistent across all guidance baselines.
- Preserve tri-state search semantics, exact-state memoization, deterministic tie-breaks and lexicographic `(moves, full joint travel)`. The use of ≤K returned motion modes is an explicit restriction in the finite graph; don't claim minimum over all candidate witnesses unless they were actually enumerated/adjudicated.
- Log `MIN_MOVES...` only with complete enumeration **and** all physically decided shallower-depth states; `MIN_MOVES_AND_MIN_TRAVEL...` also needs same-depth completeness. Track distinct feasible plans, binding budget category and reason of each unresolved branch.
- `moves_outside_original_blocker_union` is a *diagnostic*, not the count of unnecessary moves. Actual extra moves are known only when a verified finite-graph move optimum exists. Report enabling moves outside the teacher lattice separately.

### D2. Test whether D *actually changes search*, not just whether the search works

- Controls: pairless D, frozen full D, D without recursion, geometry with same feasibility gate, geometry with geometric recursion, uniform, oracle-original-union (scope-limited, not omniscient), common no-learned-search. Keep candidate domain, motion index, action verification and budgets identical.
- *Diagnosis* metrics (feasibility AUROC/Brier/recall; blockers exact/F1 on all decided originals; temporary-target feasible and blocker marginal quality) are separate from *end-to-end* metrics (success, moves, travel, planner iterations, online fallback, nodes, cache, coverage, CPU).
- Compare fixed budgets for each physical resource **and** equal total CPU/wall/iteration budgets (including D inference). If all guidance variants produce identical results because the graph was fully enumerated or action bottlenecks dominate, report this as absence of demonstrated added value, not as a failure of the optimizer.
- Intentionally include independently generated *informative* tasks with branch alternatives, ambiguous original blocker sets, access chains and overlapping/conflicting destination sweeps. Preselect difficulty using **physics-only criteria** (e.g. certified existence of ≥2 plausible candidate first moves / combinatorial branching), not D-versus-geometry outcomes.
- Report a **guide-disagreement analysis**: on each root, did the candidate order differ, which physical branches were expanded, which budgets bound first, and did a learned blocker error propagate into wasted checks? Prioritize such diagnostics over simply adding hundreds of uninformative roots.
- Similarity ablations: no index (online-only), local-only, global-only, combined, modal-top1, one-per-mode, all available modes, transit planner vs straight-only, threshold *only exploratory* (P15 threshold discarded for losing 11.6% of available held-out motions). Test separate source-independent transfer metrics and executed task success; account for index-build cost separately.
- Baselines share **scene-only** candidate movers; original P15 label-derived catalogue restriction is a retrospective control, not the main result.

**D gate:** an end-to-end physically replayable logical rearrangement with scene-only access, documented finite search/proof semantics, honest diagnosis quality and a new independent baseline comparison if powered. Scientific lift is optional—not assumed.

---

## 7. P16 evaluation, statistical freezing, and no double-dipping

### 7.1 Cohort separation

- **Historical:** P10–P15 roots, frozen models and trajectories. Use for regression, explanations, exploratory analyses and development only.
- **Development:** new roots generated before confirmation, used to tune planner determinism, local/global lookup heuristics, architecture, thresholds and CPU cost.
- **Training / calibration:** disjoint root identities **and geometry fingerprints**; calibrate on a separate split if threshold/calibrator chosen.
- **Prospective confirmatory test:** independent root seeds and mechanism/fingerprint disjointness as declared. Freeze root-generating algorithm, seed roster, hypotheses, motion index exclusions, candidate list procedure, checkpoints, thresholds, method code hash and compute rules **before collecting or unsealing blind labels**. Commit/push evidence lock, then hash-commit physical labels before unsealing; preserve all hashes.

### 7.2 Measured endpoints

| Shared | B-specific | D-specific |
|---|---|---|
| Verified target task success, feasible-original no-op, number of relocations, total measured robot travel, number of censored calls, independent replay, compute | Correct ordered repair ranking / probability, joint NLL, empty-vs-abstain, false-positive relocation, calibrated admission and predeclared mixed-family generalization, versus A/C/SF/order-off | Feasibility and blocker F1/exact, union vs necessary intersection, arbitrary-target marginals, D-guided vs geometry/uniform/oracle planner-call and success gaps, search effort per decision, lookup transfer and repeated moves |

- Pairs are independent **roots**, not candidate queries, seeds, or worker episodes. Aggregate seeds per root before paired inference. Show root-level bootstrap effect CIs and exact paired sign tests; multiplicity adjustments for simultaneous confirmatory claims. Record both p-values and practical effect thresholds.
- Do not treat zero-discordance bootstrap `[0,0]` as equivalence. Distinguish observed effect, uncertainty bounds and power to detect proposed differences.
- Report failures and censorship by reason; count ABSTAIN as failure for strict TOP1, but never conflate it with original task already feasible.
- Prefer measurable improvements and held-out generalization to handpicked successful examples. Keep challenge-family results and natural-mix results separate.

### 7.3 Explicit stop conditions

- If the deterministic planner gate fails: no claim based on close per-guide runtime or search success differences. Engineering may continue under a recorded exploratory protocol.
- If learned B's empty-repair behavior is not improved without unacceptable loss on infeasible originals: keep the negative result, do not silently change target class prevalence or success threshold.
- If D temporary-target blocker labels are unavailable: no claim about learned **recursive blocker** accuracy; feasibility-only recursion may be tested and labelled accordingly.
- If a powered confirmation exceeds budgets, stop at auditable pilot and deliver a power/resource proposal. No silent extra data collection, threshold changes or post-hoc hypothesis replacement.
- If methods tie with strong geometry or uniform guidance: retain the implementation and publish negative evidence internally; do not fabricate a novelty claim.

---

## 8. Implementation structure: minimal files, shallow folders, visual proof at every gate

**Prefer modification/reuse of existing tested modules over duplication.** Keep new source additions small (target ≤300–350 meaningful lines per Python file; if a file grows beyond that, separate by responsibility, not dozens of microfiles). No new `utils2.py`/framework for its own sake. Avoid moving historical files. Suggested maximum new code footprint (adapt only with documented reason):

```
p16_common.py    # deployable task/scene-only candidate interface, provenance, runtime status
p16_motion.py    # deterministic motion wrapper + transit/witness verification; reuse p15_* internals
p16_b.py         # minimal B default, train/infer/control APIs
p16_d.py         # pairless D target/label/recursion adapter to common search
p16_eval.py      # stage orchestration and independent evaluation (split if genuinely oversized)
tests/test_p16.py
runs/p16/{audit,shared,b,d,eval}/...
responses-phases/0082_...md through 0089_...md
visualizations/p16/{shared,b,d}/...
```

No maximum is permission to introduce 20 code files. Each new file must have a single obvious responsibility. If `p15_bench.py` is reused as a core helper, do not worsen its existing ~600-line size; isolate only new responsibilities. All controls must use one shared physical evaluation provider and the same status semantics.

**Visualization:** after each stage, output one or more genuinely explanatory 2D renderings derived from recorded initial / intermediate states, candidate destinations, robot-link sweeps, alternative motion-mode paths, search state trees, B probabilities/admission/no-op, D blocker union/necessity and calibrated arbitrary-target scores. Do not invent physical arrows/paths beyond recorded witness arrays. Animations must show certified trajectories with source/target and verification status. Tables/figures include denominators, scene family, evidence split, units and algorithm version. Do not turn every observation into a large plot unnecessarily.

**Tests:** mathematical zero-sum/exact normalization and known small-factor probability identities; keyed invariance; order reversal; all-feasible no-op; masked unknown label; D empty union/alternative clearing/complete lattice; case with no lattice clearing subset; temporary-target re-render; scene-only no-teacher dependency; deterministic planner; parallel-load replay; transit alternative; rare mode rescue; object moved twice; slot reassignment; true vs misnamed extra moves; budget and UNKNOWN semantics; physical replay all accepted plans; train/test leakage by root + fingerprint + trajectory provenance. Run all historical regressions and six historical replays.

---

## 9. Phases, gates, reports, and bounded resource authorisation

P16 should advance **both tracks concurrently after shared gates**, without waiting for one to beat the other. These caps are explicit maxima for this P16 handoff, not targets to exhaust. Before every costly phase, run a short cost/power pilot; stop or downscope if a valid test cannot fit. Count CPU child-process consumption correctly; wall time is not interchangeable with CPU. Fail closed if a guard is inaccurate. Preserve all guard logs including overruns. No work beyond caps without new user authorization.

| Gate / deliverable | Purpose | CPU-s ceiling |
|---|---|---:|
| P16-0 / `0082` | Source/evidence audit, historical regressions | 3,000 |
| P16-1 / `0083` | Deterministic planner + transit + replay tests | 9,000 |
| P16-2 / `0084` | Scene-only shared API, mechanism pilot, 3D migration specification | 10,000 |
| P16-B0/B1 / `0085` | Lean-B mathematical implementation, saved-data controls, dev training pilot | 10,000 |
| P16-D0/D1 / `0086` | Pairless D label/retarget audit, expanded search, dev probe | 10,000 |
| P16 data / `0087` | Independent pilot + **prospective labels for both tracks**, physical teacher calls | 55,000 |
| P16 training / `0087` | Up to 3 seeds/method for frozen matched arms, with pilot gate | 20,000 |
| P16 execution / `0088` | B/D/common baseline physical execution, ablations, independent replay | 38,000 |
| P16 final / `0089` | Statistics, plots, test suite, manifests and decisions | 6,000 |
| **Maximum P16 total** | Not an intended spend; strict stop ceiling | **161,000** |

Cost-sensitive decisions:

1. Complete all code and tests with no new bulk labels first. P16-B and P16-D methodology implementations **must not be held hostage by the powered-cohort budget**.
2. For B, the P15 suggested 60 feasible-original test cases may need ~31.5k CPU-s total depending on teacher costs. Use actual pilot estimates and disjoint split sizes to decide feasibility; never claim adequately powered if 60 decided feasible roots are not obtained.
3. For D, P15 prospective zero discordances suggest that 32 near-identical difficulty roots will not show a guide effect. Before any large D comparison, ensure (on physics-only DEV) that the new scene-only action domain offers informative branching and that the deterministic planner is fast enough. Do not condition test-set selection on D beating geometry.
4. If the full dual-track prospective design cannot satisfy independence/power under shared caps, prioritize a properly frozen smaller pilot per track and report `PARTIAL`/`UNDERPOWERED`. Do not borrow caps from one track to mask a failure unless documented before the freeze and within total ceiling.
5. Full 3D simulation training/benchmark collection and real robot are **not authorised in P16**; deliver the validated design, candidate 3D scene list, robot/grasp assumptions and compute quote for the following phase. An isolated existing-simulator smoke test (if already supported) may use only remaining shared-development budget, with no claim of a 3D method result.

### Reports and strict gate language

- `0082_P16_0_Source_Evidence_and_Method_Lock.md` — source/inference maps, historical decisions, hashes and scope audit.
- `0083_P16_1_Deterministic_Physics_and_Transit.md` — planner stability, status contracts, runtime and negative cases.
- `0084_P16_2_Scene_Only_Candidates_and_3D_Readiness.md` — no-label candidate API, challenging physical mechanisms, 3D design scope.
- `0085_P16_B0_B1_Lean_B_Exact_Energy_and_NoOp.md` — equations, losses, logits, calibrated rule, factor status, tests.
- `0086_P16_D0_D1_Target_Conditional_Blockers_and_Rearrangement.md` — blocker semantics, arbitrary targets, modes, repeated-move finite search.
- `0087_P16_Training_and_Frozen_Prospective_Evidence.md` — train/calibration/test splits, physical labels, prereg locks, hash custody, cost accounting.
- `0088_P16_Independent_B_and_D_Execution_Evaluations.md` — separate B vs A/C/SF and D vs geometry/uniform/oracle, no mixed protocols.
- `0089_P16_Final_Dual_Method_Scientific_Decision.md` plus `responses-phases/P16_B_AND_D_SCIENTIFIC_DECISION.md` — factor decisions preserved/reconfirmed, exact new evidence, negative findings, 3D readiness, paper-level claim boundaries.

Machine-readable `runs/p16/P16_FINAL_MANIFEST.json` and `P16_CODE_MANIFEST.json` must include source hashes, model weights/hashes, numerical budgets, commits, stages, dataset fingerprints, labels, test/replay results, and method-specific claim verdicts. Record overall status as PASS / PARTIAL / BLOCKED based on gates, not narrative enthusiasm.

**Commit/push incremental work and verify origin SHA after meaningful gates.** Keep user-unrelated dirty files untouched. If creating new files, record exact paths in report.

---

## 10. Required final assistant output (the launcher expects all of this)

Do not simply reply “P16 complete” or list commits. Print:

1. Base/final SHA and source-hash integrity, exact historical results that remain unchanged.
2. B's **actual learned method** (equations and what was retained/removed), parameter count, training data/3 seeds if run, calibrated policy, original-feasible no-op and infeasible repair performance, common-candidate ranking, physical TOP1, matched baseline results, uncertainty and negatives.
3. D's **actual learned method** (feasibility + union blocker probability), arbitrary-target feasibility and blocker labels, number of tested roles/roots, current recursion status, full scene-only action domain, multiple mode/transit costs, finite optimality flags, physically verified results, D vs geometry/uniform/oracle, CPU and planner counts, uncertainty and negatives.
4. Shared planner determinism (repeat hashes), lookup coverage/rare rescues/start-transit findings, repair lengths, destination/order examples with independently certified trajectories and visual locations.
5. What can responsibly be claimed for a potential B paper versus a D paper—and what **cannot** yet be claimed. Never claim two independently publishable papers by fiat.
6. Every stopped/underpowered gate, exact CPU-s spent, 2D/3D scope, regression count and six archived replay results; precise next blocking experiment for each track.

**Final success condition:** B and D are both scientifically honest, structurally distinct, fully testable 2D methods with a shared reproducible physical substrate. Positive empirical superiority is not required for implementation PASS. Strong causal-learning claims are contingent on independently validated mechanism and execution evidence. The next 3D phase is designed rather than prematurely claimed.
