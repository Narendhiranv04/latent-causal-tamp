# Approach B — Blackwell Learning Server Execution Contract

**Version:** BWL-1.0  
**Prepared:** 8 November 2026  
**Project:** Latent Causal Infeasibility for Long-Horizon TAMP  
**Mode:** Stage-gated implementation, training, audit, and experimental validation  
**Scope:** 3D sampler completion and 3D X/Y readiness now; 2D Q2 intake and authentic 2D/3D X/Y training/integration only after evidence and resource gates

> **THIS DOCUMENT IS AN EXECUTION CONTRACT, NOT A NEW METHODOLOGY.** The scientific authority is `final-fixed-methodology-1.pdf` (5 November 2026), especially §§4–16 and 18. The earlier `Approach_B_Final_Methodology_2026-10-31.pdf` is a reference for the historical X/Y model, not a competing specification. Existing validated code, data schemas, configurations, witness hashes, frozen test results, and experimental artifacts are evidence: inspect them before editing. If this instruction contradicts the final-fixed methodology on scientific semantics, the final-fixed methodology wins; document the contradiction and stop rather than silently improvising.

## 0. What is authorized right now

**Immediately authorized on the Blackwell server, in order:**

1. **BWL-0: Read-only audit and freeze/identify exact data, code, hardware, runs, ownership and safety.**
2. **BWL-1: 3D sampler comparison/diagnostics** using existing frozen data and bounded GPU experiments: include band-stratified, cVAE, flow, ranker, cVAE+ranker, stratified+ranker, mixture and simple conditional categorical control if the existing code/data support it. All new model/selection decisions use development/validation roots, not the exposed test set.
3. **BWL-2: Bring the 3D X/Y adapter into fidelity with the November 5 F2/F3/F5 2D source model**; run exhaustive mathematical and synthetic/typed-data checks; implement matched D/E/DIRECT/G interfaces without changing the probability semantics.
4. **BWL-3: Audit the 7,012 nominal 3D Y target-only records and produce actionable physics-side replay/X-collection manifests.** Do not silently accept planner-only labels as replay-verified physical success.
5. **BWL-4: Produce one consolidated readiness report and STOP.** It may prepare *nonexecuting* future training configurations/loaders and an audited 2D Q2 import plan.

**Not immediately authorized:** new physics trials on Blackwell; simulator rollout; full real-data X/Y training using absent X supervision; modifying running 2D collectors; adding a second 3D causal architecture; 300/5,000-root bulk data campaigns; rewriting old dataset labels; changing existing held-out/test evaluations; installing drivers/CUDA globally; stopping anybody else's processes; launching continuous unattended compute jobs; deploying learned correction sequences on hardware; or automatically advancing to post-label stages.

**After BWL-4, later stages BWL-5 through BWL-8 are documented but require explicit new authorization and satisfied entry gates.** This file is designed to remain the same roadmap when more data become available. No ETA is a substitute for proof that data are ready.

### Exact desired scientific system

A frozen-root task context `(S0, q0, q_ref, target T, goal g_T)` enters two *separate* learning responsibilities:

- **Placement-only sampler** `G_phi(S_hyp, movable_object, domain, robot_capability)` supplies candidate physical destination poses **conditional on the object already having been grasped**. It is goal-blind to the repair task. It may use the declared support/geometry/robot-capability conventions but not teacher outcomes, intended repairs, causal blocker lists, or target-planning feedback. It never decides what repair sequence solves the original task.
- **Bounded branch-specific ordered-sequence search** composes `(object_id, destination_pose_id)` moves. It may query the sampler again after applying object-pose-only hypothetical edits to a branch-local copy. It never corrupts the immutable original root or sibling branches.
- **One F2/F3/F5 X/Y model** scores *each whole ordered sequence relative to the original root*, including no-op, from initial object/robot context. It predicts whether the ordered physical moves can execute (X) and whether their hypothetical endpoint restores the original target (Y). It does not propose destinations, grasp configurations, IK, robot waypoints, or future joint states.
- **A cost-aware selector** ranks complete stopping candidates using joint X/Y probability, exact move count, deterministic displacement and optional learned travel, before separate physical verification.

**2D and 3D must be the same learning and inference method.** Embodiment-specific input tensors, primitive shapes, shelf grids/support domains, robot capabilities, physical teachers and learned weights are permitted; a separate 3D probability model or invented 3D causal mechanism is not.

## 1. Source of truth and starting inventory

### 1.1 Authority order

1. `final-fixed-methodology-1.pdf` (2026-11-05): *authoritative scientific contract*. The executing agent must actually open/read this locally; if missing, document the missing reference, use the established copy only if verified identical, and **do not assert contract compliance** based on this summary alone.
2. Source-verified 2D `approach-b-xy-v1` implementation and pinned checkpoints/reports, for real **implementation parity**, not for redefining methodology. Prior audit reports source revision `e113c6680`; verify locally rather than trusting the short hash.
3. Existing 3D branch/source on `naren/approachb-3d-learning`, reported head `3a820819`; local version/remote availability must be checked. The reported repository location and report paths are **discovery hints only**; do not create/fetch guessed paths or edit a different repo to make the instruction fit.
4. Historical 2D and 3D datasets, recorded source/witness hashes, splits, runtime logs, and physically verified teacher semantics. Logs are observations, not a license to reinterpret labels.
5. This staged engineering contract for operating the training server and deciding what to run next.

### 1.2 Historical status — facts to verify, not results to recompute from memory

**3D v4 placement snapshot:** `v4full_82926152fa9cc345`, reported 59,972 queries: 40,822 verified positives, 7,572 certified geometry negatives, 6,642 under-policy negatives, 4,936 unresolved; train/val/test 42,612 / 8,752 / 8,608 queries. Reported as the *complete K0–K3 v4 collection cohort*, not the complete planned 5,000-root 3D programme. Approximately 1,582 qualified roots, 1,466 with placement queries. A 6×6 supported upright-placement shelf benchmark, **not unconstrained 3D pose sampling**. All figures must include their actual denominators and cohort scope.

**Reported prior 3D sampler result, four proposals:** cVAE known-good hit@4 0.655, flow 0.557, uniform 0.451, **band-stratified 0.688**, ranker-only hit@4 reported in a different selection interpretation; cVAE known-label precision 0.801 with only ~0.267 known label fraction; ranker reported known-label precision 0.906 with only ~0.178 known label fraction. The band-stratified baseline is **ahead of cVAE** on the cited hit@4 metric. Do not claim learned sampler superiority, physical precision on newly proposed destinations, or 90.6% unconditional ranker success.

**Reported 3D training:** 21 prior runs, archived 00–07 reports, 21 checkpoints stored outside git, replicated on second server disk and laptop, source branch pushed. Preserve backups and verify hashes before writing. Existing result selection reportedly froze validation before test; the test set is now **already exposed** to the project and must not be used to choose new mixture/reranking hyperparameters.

**Reported 3D X/Y:** existing normalized math and synthetic-data recovery; 3D adapter not yet feature-equivalent to 2D; **no authentic 3D X labels**; ~7,012 target-only target-planning attempts may support partial Y evidence but need execution/replay semantics audit. No full real-data 3D X/Y run occurred.

**Reported 2D collectors as of 2026-11-08 around 01:22 UTC:** laptop 69/2,231 and gvlab 75/2,188; speculative completion 2026-11-09 UTC. Do not interfere. Do not equate Q2 individual-placement labels with ordered sequence-level X labels. Accept their future data only after source/root/split/witness audits.

**Reported Blackwell host:** GPU 0 NVIDIA RTX PRO 5000 Blackwell, CPU 7 only, one thread, existing watchdog yields to a collaborator GPU queue and a 3D generator process. The shared `user1` account and workload require special precautions. Verify current hardware/affinity/permissions before running; prior idle or peak telemetry is not current authorization.

### 1.3 Stage-0 read-only inspection checklist

Before any code change or training:

- Identify the working repository, branch, commit, clean/dirty status, remotes and ownership. Record `git status`, `git log -5`, `git branch --show-current`, `git diff --stat`, and relative paths. If uncommitted changes exist, **do not overwrite or stash them unilaterally**; isolate new work safely or stop for permission.
- Locate the actual `00_READ_ME_FIRST.md`, sampler model sources, training/evaluation scripts, `src/xy3d.py` (if present), source 2D model, 00–07 reports, frozen data manifest, `eval_val.json`, `eval_test.json`, checkpoint manifests and hash records. Do not pretend a filename exists because earlier Claude mentioned it.
- Inspect the exact split: root grouping, parent descendants, cross-split leakage, query/same-object duplication, allowed/illegal candidates, positive/negative/unknown status policy, known-label masks, support/grasp settings, and witnesses. Recheck 59,972 tally.
- Establish what is actually copied to Blackwell. A read-only snapshot is required; no `chown -R`, mass copying over a shared path, global environment modifications, or package upgrades to solve a routine problem.
- Verify the two checkpoint mirrors and hash identity; if a mirror is missing record it, never create an unapproved off-site upload.
- Locate the physical-3D generator source used for labels **through available local copies**; do not SSH into physics machines unless expressly authorized.
- Verify current GPU use and other users' processes. Record CPU affinity and watchdog readiness/self-stop behavior. If the watchdog cannot reliably protect shared workloads, mark `RESOURCE_BLOCKED` and **do not run GPU code**.

Stage-0 deliverable: one compact audit/manifest with exact commit, data snapshot and all blockers; print an absolute path to the new report. No invented hashes.

## 2. Resource and safety policy — mandatory for every Blackwell run

1. **GPU 0 only**, if genuinely available. **CPU 7 only / one CPU thread** as previously established, but first check that CPU 7 is in allowed affinity and no higher-priority task is there. If not, stop or use only an explicitly approved alternative, not a speculative multi-core fallback.
2. Enforce single-threaded numerical libraries and no background DataLoader workers (e.g. `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, Torch intra/inter-op threads one, `num_workers=0`). Where appropriate use a process-affinity wrapper such as `taskset -c 7`; confirm with actual affinity telemetry. These are operating instructions, not a replacement for the tested job wrapper.
3. Run **at most one project GPU process** at a time. No CPU training, MuJoCo physics, rendering jobs or multiworker dataloading on this shared server. No hyperparameter sweeps via simultaneous jobs.
4. Preserve and *test* the existing watchdog policy and safety self-stop before new bounded training. It must yield if the collaborator's GPU queue starts or the 3D generator becomes active. Never make it kill an unrelated process. Do not use broad `pkill`, `killall`, `sudo`, scheduler impersonation, or match-and-kill by a nonunique command string. Terminate only a recorded child process/job owned by this experiment after confirming PID and start-time identity.
5. Recheck hardware contention **before each run**, not only at the session beginning. Record all GPU/CPU samples, VRAM maximum, GPU memory occupancy, job PID, start/stop time, exit status, energy/power/temperature where available, and reason for any abort.
6. Use existing pinned Python environment/dependencies. If unavailable or incompatible, create a minimal isolated environment only with permission and no driver/system CUDA changes. Prefer diagnostics before installation.
7. Bound every new training/sweep job by declared per-job GPU runtime, memory, single-core CPU time, disk budget and maximum runs. Derive caps from measured smoke runs + current local policy and write them *before* launching. Do not invent a universally safe cap or quietly disable protection.
8. Keep raw datasets, splits, previous test outputs, existing reports 00–07 and all 21 checkpoints immutable. New output paths must be noncolliding and write within the agreed project workspace. Favor small config overlays, not changing archived configs.
9. Back up newly selected checkpoints to the already authorized mirrors after verifying destination rights; save checksums. A third independent off-site location is recommended but **not authorized by this document**.
10. If any job fails or is interrupted, preserve partial logs and stop that stage safely; never hide a failed test or recast it as success.

## 3. Frozen scientific semantics — never reinterpret

### 3.1 The sampler is *placement-only*

Input: hypothetical scene `S_hyp`, selected movable object, valid support/placement domain, capability convention. Output: unique candidate destinations with optional selection score / **separately calibrated** placement-feasibility confidence. Grasp is assumed already achieved. Do not condition on the target goal or whether the original target task became feasible. Do not use labels, intended moves, blocker IDs, oracle distances, teacher success, or hidden scene-generator roles to filter candidates.

Minimal legality filtering may reject unsupported, duplicate, occupied, overlapping or structurally impossible destinations based on the **same declared observable rules** for every method. It may **not** use online IK/motion teacher to veto every sampled destination. A generative density is not calibrated probability of placeability.

The 3D first cohort uses 36 supported shelf cells; report that scope. Complete pose generation and arbitrary orientation claims require independent, future evidence and are **not** an invitation to redesign this stage.

### 3.2 Ordered proposals and hypothetical scenes

`r = ((o1, d1), ..., (om, dm))` with no moved object repeated, explicit physical destinations, and empty `r=()` as no correction. Root `S0` and `(q0,q_ref,T,gT)` remain immutable. An *ideal* hypothetical endpoint `S^r` changes only specified object-pose fields, not robot joints, physics outcomes, teacher-rendered future visual features or scene-generator annotations. Omitted actions mean those objects stay in their original poses. Within a branch, prefix actions are frozen; other branches are independent. The complete ordered sequence is evaluated **from S0**, not from an imaginary current robot configuration.

**Two independent queries may share one Y:** AB and BA resulting in the same physical endpoint and same target/reference state have identical Y query identities. Their X may differ.

### 3.3 X/Y labels and terminal connector

For an ordered prefix `r`, `X_r=1` under the *frozen finite-budget teacher* only if the robot physically completes **all relocation phases in order** (approach/grasp/carry/place/release/retreat) from the original robot state, retains achieved state between moves, and provides a valid terminal free-gripper connector to `q_ref` **when that prefix is a proposed stopping point**. No reset to home between A and B. Connector cost is part of the declared travel convention.

For unique endpoint scene `s=S^r`, `Y_s=1` under the frozen teacher only when the original target action/goal is feasible under its agreed full target verification in the hypothetical endpoint from the **fixed `q_ref`**, gripper free/no attachment. It is not evaluated by appending a target action from the arbitrary achieved robot state after relocations. Y can be tested even when X=0.

The four X/Y combinations `(0,0), (0,1), (1,0), (1,1)` are all valid; joint repair success requires `(1,1)`. `X_empty=1` by convention and `P_success(empty)=P(Y0=1)`. **No third learned success variable is introduced.**

**Operational status discipline:** under the older frozen X/Y teacher protocol an *attempted*, budget-exhausted query receives operational binary 0 with `negative_kind`, phase, budget, attempts and scope retained; an **unattempted** query is missing. New placement sidecars preserve their own certified-negative, policy-limited-negative, unresolved/censored distinctions. Different negative semantics may never be silently mixed. A failed finite planner does not certify universal impossibility.

### 3.4 Exact normalized F2/F3/F5 model (temperature = 1)

Let `b_s = h_Y(scene_endpoint, q_ref, target, goal, root_context)` from **F3**, and `a_r = h_X(initial_scene, initial_robot, full ordered prefix, endpoint, root_context)` from **F2**. Let `w_r = h_XY(full ordered prefix, endpoint, root_context)` be the **narrowly defined F5 X–Y coupling**. No new generic F3/F4 pair functions or separate F4 head. F4 is omission queries passed back through F2/F3.

For each **unique** endpoint `s` and unique ordered query `r`:

```text
P(Y_s=1)                 = sigmoid(b_s)
P(X_r=1 | Y_s=y)        = sigmoid(a_r + w_r*y)
P(X_r=1,Y_s=1)          = sigmoid(b_s) * sigmoid(a_r+w_r)
P(X_r=1)                = P(Y_s=1)*sigmoid(a_r+w_r)
                          + (1-P(Y_s=1))*sigmoid(a_r)
```

For a root with many candidates, the correct joint probability is **scene-first**:

```text
P(y_S, x_Q | root) = PRODUCT_{s in unique endpoints S} P(Y_s=y_s)
                     * PRODUCT_{r in unique ordered queries Q} P(X_r=x_r | Y_{s(r)}=y_{s(r)})
```

Equivalently the normalized energy contains each local negative-logistic factor including its `log(1+exp(...))` conditional normalizer. **Do not globally normalize independent raw `-a*x-b*y-w*x*y` local pairs as if they were unconnected:** doing so can spuriously change the Y marginal when extra sequence candidates are added. The existing mathematically verified 3D implementation should be preserved, not replaced.

`D`: coupled, learn `w`. `E`: uncoupled, set `w=0` with an otherwise matched comparison. `DIRECT-GEO`: an independently designed **direct joint-success prediction head**, not a hidden `a+b` shortcut. `G`: order-invariant comparator with equal endpoint/candidate coverage. Use the 2D source implementation to determine the precise matched family and document capacity/compute differences.

### 3.5 Losses and selection

Use one **root-averaged, observed-data marginal negative log-likelihood** for distinct X/Y queries; missing outcomes are marginalized exactly, and each physical query counts once per root. This is the authoritative X/Y likelihood. A Y-only observation contributes to F3 but does not independently supervise X or identify F5 coupling.

Travel: on eligible full witnesses, a pinned measure of normalized joint travel, including declared relocation phases, transitions, terminal connector and (under the November 5 measure) the target component. Auxiliary loss:

```text
L_B = L_joint + lambda_J * mean_w Huber(log(1+Jhat(w)), log(1+J(w)))
```

No fabricated travel penalty for failed/missing-witness sequences. Record exactly which successful witness and travel convention define `J`; do not conflate the October 31 and November 5 travel conventions.

Freeze selection coefficients on development data:

```text
C(r) = -log(max(P(X_r=1,Y_s(r)=1), eps))
       + alpha * m(r) + beta * C_displacement(r) + gamma * Jhat(r)
```

Sampler cVAE/flow losses **remain separate** from `L_B`. During inference network weights are fixed; search over candidate sequences, not gradient descent over raw energy for endpoint poses. Low-Y intermediate prefixes may still be expanded. No-op is always considered. Missing candidates imply possible **proposal coverage unknown**, not proof that no repair exists.

### 3.6 Causal-evidence meanings

Separate: (i) object intersects a historic frozen trajectory; (ii) a fixed-robot pose edit changes Y; (iii) omitting a move changes outcome in a specific ordered repair; (iv) a repair is necessary across all alternatives (requires stronger evidence). F5 measures statistical dependence between named outcomes; it **does not** identify a directed causal edge, unique blocker identity, or causal DAG.

## 4. BWL-1 — 3D sampler study (Blackwell: execute after BWL-0)

### Research questions

1. Does cVAE+ranker exceed a strong stratified analytical sampler **and stratified+ranker**, under an identical unique-proposal budget?
2. Is apparent cVAE performance due to a useful latent variable or to a simpler conditional categorical mapping over 36 shelf cells?
3. Do proposal diversity and feasibility ranking trade off? What fraction of generated destinations are untested, certified-negative, policy-negative or positive?
4. Can conclusions survive the known-label selection bias, the known near/mid/far data-collection distribution and different legal-cell snapping rates?

### Required arms

Retain archived: cVAE, conditional flow matching, uniform, band-stratified, ranker-only. Add *where supported by the existing code/data*: cVAE+ranker, stratified+ranker, predeclared cVAE/stratified mixture, simple conditional categorical network with comparable scene conditioning. If Sobol is distinct from current band-stratified, report it separately. The November 5 document lists swept-volume analytical sampling but says its specific method is **not frozen**; if no audited implementation exists, mark it `NOT_IMPLEMENTED/METHOD_UNSPECIFIED` rather than invent an advantageous privileged comparator.

**Fairness:** same per-query object, scene, legal support/occupancy rules, permitted input information, unique-proposal count, raw draw budget, random-seed schedule, candidate deduplication, rerank pool size, legal rejection handling, and measured wall/CPU/GPU inference cost. Distinguish feasibility ranking from generating destinations; ranker-only is not a generative sampler unless it is granted a disclosed candidate catalogue and its catalogue-generation cost is charged.

**No test-set retuning:** the previously exposed `eval_test.json` may be reproduced byte-for-byte as archived evidence, but do not choose mixture weight, ranker threshold, budget, architecture or seed based on its outcomes. Fit/train/choose on training/validation roots only. New arms require a newly locked blind confirmation set or an independently verified new root/destination sample for definitive post-selection claims; an already inspected test set cannot regain blindness.

### Metrics (all denominators explicit)

- `hit@1/2/4/8` based on **previously recorded verified positives**, not a physical-success claim for unknown candidates.
- Known-label precision with **known-label fraction** side by side; never hide unknown destinations in denominator or silently mark them negative.
- For each method: unique proposal count, raw draw count, legal/snap/reject fraction, repeated destinations, entropy/diversity/effective-cell count, near/mid/far support coverage, source-to-destination displacement, runtime and memory.
- Ranker AUROC/AUPRC, Brier, ECE/reliability **on comparable decided labels**; report separate performance on certified geometric vs policy-limited negatives and whether negatives were pooled.
- Causal/physical caveat: the above are offline catalogue metrics and do not establish independent physical placement precision. Compute oracle-known coverage and an explicit unknown-proposal ledger.
- Stratify by scene/root families (K0–K3 as actually present), object dimensions/height, clutter, distance band; group uncertainty intervals by **independent root**, not individual destination trial.
- Run at least the existing frozen seeds; any extra repeats must be small, declared in advance and resource-safe. Prefer paired root-bootstrap uncertainty on held-out development data instead of claiming significance from individual query counts.

### cVAE latent diagnostic

Inspect KL per latent dimension, aggregate KL, effective latent usage, samples with fixed scene vs changed z, distinct placement coverage, posterior collapse indicators, reconstruction/categorical NLL and diversity. Compare against a direct **conditional categorical** decoder with the same input/access restrictions. Use a bounded validation-selected training budget and retain existing checkpoints. Do not silently retrain 21 runs because a new baseline exists.

### Offline selection versus physical confirmation

Produce a **predeclared physics-host-only confirmation manifest** for previously untested (scene, object, destination) tuples from selected methods, with shared roots, unique query identifiers, support/grasp semantics, teacher budgets and outcome status. Include both model-favored and analytical-favored destinations and diverse strata. Evaluate *all* chosen candidates through the same teacher to remove the known-label-only selection bias once authorized on a physics host. **Do not run those trials on Blackwell.** Do not use target-repair success to redefine sampler placeability.

### Exit gate BWL-1

A reproducible validation-only sampler decision report, per-arm denominators + CIs, latent diagnostics, candidate/unknown provenance, a separately labelled physical confirmation manifest, and a clear verdict such as `PROMISING / TIED / ANALYTICAL_AHEAD / INCONCLUSIVE`. No claim that cVAE is universally better simply because it exceeds flow.

## 5. BWL-2 — 3D X/Y adapter fidelity (Blackwell: execute after BWL-0; parallel code review with BWL-1 is okay, GPU jobs serial)

### Do not rewrite the factorization

Preserve the existing correctly tested scene-first normalized X/Y kernel. Compare against the source-verified `approach-b-xy-v1` 2D implementation and reports. The changes belong in the 3D **feature and data interfaces**, not a new 3D energy or causal mechanism. Keep source files focused and reuse the existing layout. If responsibilities overlap, minimally refactor one local boundary; no new training framework or duplicated model tree.

### Mandatory feature repairs and anti-leakage

- **F3 must see** target identity, original target pose, target goal/destination, the full hypothetical object endpoint, fixed `q_ref` and reference gripper/attachment state, relevant robot capability and workspace context. Its representation is **target-centric**; the sampler's selected-object-centric encoder should not simply be reused unchanged. Changing only goal while holding scene fixed must be expressible by different F3 logits.
- **F2 must see** original root/object poses, initial robot `q0`/capability, ordered `(object, destination)` actions, all-object ideal prefix states, predecessor/sequence context and relevant endpoint features. Use the specific order architecture frozen in the source 2D implementation (prefix/predecessor-aware), not a newly invented recurrent mechanism. F2 need **not** predict intermediate joint states.
- **F5 remains explicitly present** in coupled D, with trainable coefficient `w_r` on exactly X–Y; no generic cross-outcome couplings or new causal latents. E sets `w=0` under controlled model/compute comparison.
- **F4 is not its own network:** omission creates a new ordered sequence and reuses the same F2/F3 evaluation; omitted objects remain at their original positions in every recomputed ideal prefix.
- **F1:** deterministic, shared, declared static legality screen, not learned collision-oracle leaks.
- **No-op:** `r=()` must work without invalid zero-length GRU/sequence handling, `X_empty=1`, and `p_success=p_Y(original)`. It must not generate a phantom action cost.
- **DIRECT** must be a genuine independent end-to-end direct-success baseline as specified by the 2D comparator; a trivial `sigmoid(a+b)` algebraic substitute is not adequate. **G** must remove ordering information while keeping equivalent endpoints/candidate evidence. Document capacity differences.
- Preserve frozen original appearance features; counterfactual endpoint changes may update supplied structural pose/support tokens but may **not** synthesize a teacher-observed future RGB frame or inject post-intervention privileged features. Allowed learner inputs and masks must be explicit.
- Do not feed oracle labels, ground-truth target trajectory/swept-volume result, teacher witness, intended repair, root ID, construction role, teacher random seed, or future actual robot state into learned features. Geometry/primitive state allowed by methodology should remain explicit.

### Precise mathematical and API tests (run actual code, not just reason)

1. Exact sum-to-one for all four `(X,Y)` possibilities over a single endpoint; brute-force equivalence on tiny multi-endpoint roots and gradients through all active factors.
2. Shared Y invariant for AB vs BA same endpoint; potential different X; repeated/duplicate X and Y queries do not gain extra loss weight.
3. Adding another sequence to an existing endpoint leaves its Y marginal exactly unchanged; batching/permutation of candidate queries and caching leave results unchanged.
4. `w=0` reduces D to the uncoupled conditional baseline within specified numerical tolerance; F5 gradients nonzero on relevant **joint decided** examples; no ability to infer F5 from Y-only labels alone.
5. Correct observed-data marginal loss for Y-only, X-only, both observed, neither observed, and multiple X children sharing Y; no post-hoc creation of fake missing labels.
6. Order swap changes F2 representation/X where conditioning differs, but unchanged endpoint cannot change F3 Y. Same scene/different target goal can change Y. Object input permutation with stable IDs preserves predictions.
7. A valid no-op, single relocation, multi-relocation, omission and censored/negative record round-trip through loaders and scorers without dropped/misaligned masks.
8. Training under planted synthetic coefficients shows recovery/calibration where identifiable. Synthetic order effect and planted F5 signal must be distinguishable; use multiple seeds/held-out synthetic roots to avoid memorization. **Mark all these results `SYNTHETIC`, not physical efficacy.**
9. DIRECT and G receive matched observable inputs, no accidental teacher/metadata leak, and independent head parameters. Include a check that mutating forbidden fields while holding allowed inputs fixed leaves inference invariant.
10. Legacy 2D compatibility: existing 2D scores/tests/archived replays should remain identical where their code is touched. If source paths are inaccessible, report `SOURCE_PARITY_UNVERIFIED`, not `PASSED`.

### Exit gate BWL-2

All available tests pass, parity matrix points to *actual source lines/commit*, the four model arms load real-format 3D records and produce defined forward/gradients, no-op/invariants pass, and no real X/Y training claims are made. If a parity mismatch requires changing the frozen scientific equations, stop and escalate instead of “fixing” the methodology.

## 6. BWL-3 — Y provenance and physically authentic X manifest (Blackwell: audit/prepare only)

### The Y audit

Previous report identifies about **7,012** target-only attempted queries: ~1,582 original-scene and ~5,430 edited-scene. The earlier source audit says `bd_3dt.py`'s target query resets to the ready configuration and invokes the target planner, but does not run the resulting target trajectory in MuJoCo as the B-sequence executor does. Thus an output marked target-planning success does **not automatically** satisfy the final full independently replay-verified Y convention.

For every record type (not every raw file if time-consuming), audit the source path: initial state and fixed `q_ref` identity; target/goal and scene edit identity; planning success/failure scope; stored motion witnesses; whether `run_plan`/independent target replay occurred; contact, support and gripper checks; budgets, witnesses, and hash/provenance. Produce counts per category:

- `Y_REPLAY_VERIFIED`: eligible after source/protocol and witness audit;
- `Y_PLANNING_ONLY`: potentially useful auxiliary supervision **but not** the final replay-verified Y pool;
- `Y_POLICY_FAILED`: attempted operational negative under a clearly pinned query policy;
- `Y_UNATTEMPTED_OR_UNRESOLVED`: masked, never auto-zero;
- `Y_SEMANTICS_INCOMPATIBLE`: wrong reference state, target/goal, edited-scene provenance or protocol.

A small, **predeclared, independently selected physics-host replay sample** should check both original and edited-scene outcomes, positive witness execution and reproducibility, and label equivalence. The report must distinguish planning negatives from certified impossibility. Do not launch MuJoCo on Blackwell. Do not mark all 7,012 final-Y valid simply because source metadata says `attempted=true`.

**Optional future Y-only analysis:** If a Y cohort is source-audited and its semantic scope is declared, optionally train F3 alone on training/validation roots with separate checkpoint namespace and report it as `Y_PLANNING_SUPERVISION_PRELIMINARY` unless independently replay-verified. It must not be presented as complete X/Y training; do not optimize F2/F5 against Y-only data or claim F5 learned. This optional GPU experiment is **not authorized in BWL-0..4 without further explicit approval**.

### Authentic X collection spec to hand to physics host

Produce an independent, versioned collection manifest with root IDs, split lineage, reference robot q/gripper/attachment state, candidate ordering, allowed grasp/motion family, endpoints, teacher budget, and a complete execution/replay record schema. Include labels for:

- `K0` no-op (X defined 1, Y separately measured);
- one-move positive/negative/unknown and multiple destinations for same object;
- two-move **AB versus BA same endpoint** attempted independently; do not invent a negative from a timeout unless pinned operational failure convention applies;
- three-move prefix-dependent access, including intermediate state carried through real moves;
- omission queries (A, B, AB, AB-minus-one) and nuisance/harmful/beneficial moves;
- X=1/Y=0, X=0/Y=1, and (if achievable) X=1/Y=1, plus true no-op cases;
- multiple candidate generator sources: cVAE, stratified, flow, alternative sampler, historical intended candidates, random distractors, predeclared **before** X/Y teacher outcomes;
- first complete relocation witness with accurate intermediate robot/joint/gripper/attachment state, the terminal connector to `q_ref` for stopping queries, complete target Y from fixed `q_ref`, and declared travel cost convention including target component;
- budgets, attempts, solver failures, contact failures, negative_kind, certified vs operational scope, unresolved/unattempted masks, physical witness/replay hashes and exact original-root lineage;
- planned independent roots split **before** generating descendants; no held-out test roots used to construct success-biased training pool.

**X must not be inferred from:** a successful single-object placement; an endpoint-only static certificate; a composite B-sequence that runs target from achieved terminal state without a `q_ref` connector; a successful order used to infer success of its permutations; or an IDEAL hypothetical edit that teleports objects.

Start with a small predeclared pilot on existing roots to establish attainable **decided** same-endpoint order contrasts, real X witnesses, physical replay success, teacher runtime, label balance and outcome coverage before authorizing scale. If such contrasts do not exist, label the architectural experiment `EVIDENCE_BLOCKED`; do not manufacture them by changing proof thresholds or copying labels.

### Exit gate BWL-3

Label-provenance report with exact status counts and source evidence; physics-only replay/collection manifest; gap matrix for authentic X, Y and travel. No physics work performed on Blackwell; no full 3D X/Y training.

## 7. BWL-4 — consolidate and stop (immediately authorized)

After BWL-0/1/2/3, produce one succinct executive findings report and exact run/commit/manifest list. Required verdict fields:

```text
SAMPLER_OFFLINE: PASS / INCONCLUSIVE / FAIL / RESOURCE_BLOCKED
SAMPLER_NEW_PHYSICAL_PRECISION: NOT_RUN / PASS / FAIL
XY_3D_MATH_AND_INTERFACE: PASS / INCOMPLETE / FAIL
XY_2D_PARITY: PASS / PARTIAL / UNVERIFIED
Y_3D_REPLAY_VALIDITY: VERIFIED_SUBSET / PLANNING_ONLY / UNRESOLVED
X_3D_AUTHENTIC_DATA: ABSENT / INSUFFICIENT / READY
BLACKWELL_FULL_XY_TRAINING: BLOCKED / READY_BY_EVIDENCE
END_TO_END_3D: NOT_RUN / READY_FOR_INDEPENDENT_EVAL
RESOURCES_AND_WATCHDOG: PASS / BLOCKED
```

Explicitly identify what changed in code versus what was merely analyzed. Show no more than necessary new modules, outputs, figure paths and exact commands used. Include all historical caveats. **STOP COMPLETELY** and ask for permission for the next named stage; do not use idle GPU time as permission to train unrelated models or run another dataset sweep.

## 8. Future stage BWL-5 — audited 2D Q2 data intake and 2D sampler training (NOT automatically authorized)

**Entry conditions:** laptop and gvlab complete, the new merged Q2 dataset arrives with hashes and witness/provenance manifests, split isolation independently passes, and the physical/placement definitions agree with the intended 2D sampler target. Completion estimates are not entry evidence.

1. Read-only verify root count, train/val/test inheritance, trial counts, positive vs certified negative vs policy negative vs unresolved, witness replay status, support domain, sampler object/grasp convention and potential under-collection of distance strata.
2. Distinguish Q2 individual-placement labels from X/Y ordered sequence labels. A placement dataset must **never** be treated as X.
3. Train the *same sampler method family and objective* as 3D, using the 2D domain-specific encoder/features (not a newly invented causal model). Compare cVAE, flow, analytical band/Sobol and selected ranker combinations with matched unique-proposal budgets, test only after validation freezing, and independently verify newly proposed destinations on a physics host later.
4. Use separate training runs, snapshots and model weights for 2D vs 3D; document the shared algorithm and distinct robot/scene geometry. No assumption that 3D weights transfer to 2D or conversely.
5. Produce a two-column *method-parity report*, not a forced performance equality claim. Archive checkpoints and return to stage gate.

If no authentic 2D X/Y sidecars are available, the main 2D full-X/Y training is separately blocked, regardless of Q2 placement completion.

## 9. Future stage BWL-6 — genuine X/Y training (NOT automatically authorized)

**Entry conditions:** authentic, source-checked, split-safe, sufficiently varied decided X/Y **sequence-level** labels matching the November 5 connector/reference convention are present for the domain being trained. Y-only records do not satisfy this gate. Not all observed examples need both labels, but the joint architecture must have adequate **paired**, multi-order, endpoint-varied evidence; report coverage before training. Travel labels are optional and masked when absent. Frozen source definitions and negative scopes verified.

**Training arms:** `D` F2/F3/F5 coupled primary; `E` uncoupled; `DIRECT-GEO` independent direct success; `G` order-invariant. Acknowledge that F5's improvement was **not established** in earlier 2D experiments; do not claim it is essential until matched ablations support it. Optional F2/F3/context and travel head ablations after primary comparison, not before data readiness.

**Training protocol:**

- Same independent roots, matched candidate pool and source labels, legal masks, inference budgets, freeze/test discipline. Group roots and all descendants together; do not let one popular root dominate via duplicate prefixes.
- Start with a tiny real-data batch sanity test, overfit a few fully decided controlled examples, then bounded multi-seed runs (target three seeds when resources allow), then validation calibration, and only after freezing run held-out evaluation.
- Implement exactly the root-average observed-data marginal NLL; test masked Y-only, X-only and both-observed cases, shared Y and duplicate queries. Optimize travel Huber only on eligible complete witnesses with declared `J` semantics.
- Log separate Y calibration, marginal X calibration, conditional X|Y, **joint** success calibration, NLL/Brier/ECE, X/Y failure decomposition, actual seen order contrasts, omission effect accuracy, model size and runtime.
- Compare against geometry-only and/or independent-scoring baseline where fair. Distinguish predictions from independent physical verification.
- For 2D, compare source-verified 2D model vs retrained candidate-diverse evidence under matched new candidate distribution; for 3D, same equation and controls with 3D data/features. Never smuggle teacher-based intended repair catalogue into test-time search.
- Produce 3D/2D model cards with exact sources, cohort scope, trainable parameters, training time, uncertainty intervals, failure cases and model/teacher boundaries.

**If the X/Y distribution is imbalanced or has no genuine AB/BA effects:** report it as a data/identifiability limitation; do not invent synthetic “physical” negatives. Synthetic planted-coupling experiments are math checks only.

## 10. Future stage BWL-7 — dynamic sampler / ordered search integration (NOT automatically authorized)

**Entry conditions:** sampler selected on development evidence; fully trained/frozen scoring models and source-compatible input APIs available; root splits/policies/version hashes frozen. Can develop pure state/search tests earlier without declaring physical success.

1. Implement the November 5 branch-local search (§13) using existing search code; do not introduce a separate 3D search mechanism.
2. Initialize with no-op and score its Y0. For each eligible unmoved object, sample unique legal destinations in the current hypothetical branch scene; append to full ordered root-relative `r` and score via frozen X/Y; cache endpoint Y by root/goal/q_ref/edited arrangement, X by ordered sequence and root.
3. Preserve sibling branches, unique physical object moves, original-root visual anchors, original robot state, full order and count of sampler/query/verification calls. Candidate stop ranking uses `P_success` plus count/displacement/travel costs; **low-Y intermediate prefixes remain expandable**.
4. No runtime IK teacher veto for every sampled destination. Static legal rules are equal across arms; final selected candidates are independently checked during evaluation.
5. Controlled ablations: fixed one-shot sampler vs dynamic resampling; cVAE vs stratified/mixture; sampler alone vs X/Y ranking; D vs E vs DIRECT vs G; X-only/Y-only/joint selection; cost terms on/off; no-op; proposer/sequence budget sweeps. Honor identical physical evaluator and proposal access.
6. Report coverage and reasons for `SELECTED_UNVERIFIED`, `FOUND_VERIFIED`, `SEARCH_BUDGET_EXHAUSTED_UNKNOWN`, and `PROPOSAL_COVERAGE_UNKNOWN` separately. A prediction is not a physical success.

## 11. Future stage BWL-8 — independent 2D/3D physical confirmation (NOT automatically authorized)

**Entry conditions:** selected models/configurations/budgets frozen before blind physical roots are seen, physics host explicitly authorized, equal budget verifier available, and 2D/3D outcome contracts independently auditable.

Three layers **must** be reported separately:

- **A — Sampler-alone physics:** actual teacher success and coverage on new, uniformly verified generated destinations, unknown/censored properly retained, independent analytical controls, paired root confidence intervals.
- **B — Fixed-candidate X/Y prediction:** joint outcome Brier/NLL/calibration and real AB/BA + omission effects using exactly the same candidate/evidence pool for D/E/DIRECT/G; no reward for sampler coverage in this layer.
- **C — End-to-end corrective search:** independent verified complete repairs, unnecessary no-ops, selected move count, displacement, joint travel, time-to-first-repair, teacher/solver calls, total runtime, missed proposed positives, abstentions and root-stratified paired uncertainty. Report whether failure is from sampler coverage, sequence construction, wrong X, wrong Y, ranker, or physical controller.

2D and 3D share *scientific method and evaluation structure*, but **not presumed shared weights, equal distributions, or identical robot success**. State hardware/control/dynamics limitations candidly. Keep original goal/action and robot-reset/reference conventions matched within each experiment.

## 12. Required data fields / interface tests (adapt existing schemas, do not duplicate blindly)

The codebase may already implement most of these. Add only missing fields, preserving old schema versions and archived loaders:

```text
Root:
  root_id, root_group_id, split, scene_source_version, scene_hash,
  S0_object_poses_and_geometry, supports, q0, q_ref, gripper_state,
  target_id, original_target_pose, target_goal, capability_policy_hash

PlacementTrial:
  root_id, hypothetical_scene_signature, selected_object_id,
  destination_pose_id_or_pose, legal_mask, grasp_assumption,
  policy_id, attempted, status, negative_kind, failed_phase,
  source_sampler, teacher_budget, witness_hash, metadata_hash

OrderedSequence:
  root_id, exact_ordered_move_list, stable_physical_sequence_hash,
  endpoint_signature, ideal_prefix_signatures, q0_hash, q_ref_hash,
  canonical_no_op, candidate_generation_source

XYTeacher:
  root_id, distinct_X_query_signature, distinct_Y_endpoint_signature,
  X_observed, X_value, X_status_and_negative_scope,
  Y_observed, Y_value, Y_status_and_negative_scope,
  X_terminal_connector_verified, Y_reference_qref_verified,
  relocation_witness, target_witness, replay_status,
  attempt_budget_and_count, failed_phase, travel_J, travel_mask,
  teacher_source_version, original_root_group_and_split

ModelBatch:
  learner_visible_initial_features_and_structural_hypothetical_edits,
  unique_X_and_Y_index_maps, label_masks, legal_masks, order_features,
  NEVER teacher outcomes/witnesses/privileged construction fields as inputs
```

**Critical test:** Same endpoint + goal + q_ref = same Y key regardless of order; same ordered action list + root = one X key. A nominal pair `(X=1,Y=1)` is composable only when the X terminal connector and Y target protocol match.

## 13. Implementation principles and change boundaries

- **Inspect, then patch.** No new project scaffold if an existing repo already works. No massive refactor to make an “ideal architecture.” Reuse existing `src/xy3d.py`, model/sampler/evaluation files, and historical source/2D checks when they exist. Inspect actual tree first.
- Prefer 120–280 logical lines per module; ~300 lines triggers a responsibility review rather than new abstractions. A small targeted module can be justified if one cohesive responsibility would otherwise become unreadable.
- Do not add model variants outside D/E/DIRECT/G and the small sampler controls defined here; no transformers, new graph nets, explicit q-next-state head, recurrent 3D-specific causal mechanism, or expanded RL/dynamics learning.
- Use checked dataclasses/typed JSON/NPZ/Torch with versioned snapshots; no new DB/queue/experiment-tracking server without a demonstrated need and permission.
- `train`/`evaluate` code must reject unavailable data cohorts and incompatible label conventions with a clear error; no silent fallback to synthetic data in real-data runs.
- Every new figure derived from real code output/teacher records; label synthetic diagrams visibly. For 3D show actual shelf/support/candidate/obstacle geometry and physical witness context where available. Never create persuasive but unverified physical success GIFs.
- Correct source-level mistakes; preserve the historical failed attempts and their provenance. Any bug that may invalidate a published metric must be documented, not silently repaired and forgotten.

## 14. Deliverables and new-report conventions

Keep the existing reports `00`–`07` intact. After inspecting actual paths, use the **next noncolliding report IDs** (suggested below, only if free):

```text
reports/08_BLACKWELL_AUDIT.md
reports/09_SAMPLER_VALIDATION_AND_LATENT_ABLATIONS.md
reports/10_XY3D_PARITY_AND_SYNTHETIC_TESTS.md
reports/11_Y_PROVENANCE_AND_X_COLLECTION_SPEC.md
reports/12_BLACKWELL_READINESS_DECISION.md
reports/figures/...            # plots from real saved metrics
configs/... or existing config dir: new named experiment overlays only
<existing data/manifest location>: new locked experiment manifests
<authorized checkpoint store>: checkpoints, never silently committed to git
```

If the repo uses a different output convention, follow it. **Do not create an unnecessary hierarchy** simply to match the examples. Produce an additional machine-readable `ready_next.json` only if an existing manifest/JSON convention can carry it without a new framework.

Each report must state: actual code commit; data/split/profile/hash; experiment status (`RUN`, `NOT_RUN`, `BLOCKED`, `SYNTHETIC`, `PLANNING_ONLY`, `PHYSICALLY_VERIFIED` as appropriate); exact input population and denominators; actual command(s); random seeds; prior vs new results; test outcome; CPU/GPU usage and watchdog logs; negative/unknown coverage; paths to raw metrics/figures; threats to validity; explicit proceed/stop decision.

**Visual minimum:** Sampler proposal heatmap per arm on identical scene axes; unknown-label vs known-positive/negative candidate visualization; diversity/coverage plot; cVAE latent diagnostic; X/Y outcome diagram showing same-endpoint shared Y and different-order X; tiny synthetic outcome-grid/reliability plot; real physical witness films only when actually verified. Charts must display scope and not conceal unknown labels.

## 15. Mandatory final response format from Claude Code

After completing **BWL-0 through BWL-4 only**, Claude must respond in this exact high-level order:

1. **Repository, data and hardware identities**: actual branch/commit, dataset/split hashes and watchdog state.
2. **Changes made**: paths + one-sentence purpose, no fabricated work.
3. **Sampler results**: compact comparable metrics including stratified baseline, labelled fraction and honest interpretation; identify new vs archived runs.
4. **X/Y model readiness**: F2/F3/F5/D/E/DIRECT/G parity pass/fail, real vs synthetic, exact tests.
5. **Y label audit and X gap**: honest counts with planning-only/replay-verified status and physics-only manifest paths.
6. **Remaining external dependencies**: 2D Q2 merge, 3D physics replay and X collection, fresh placement confirmation, full X/Y training.
7. **Artifacts**: all new report paths, figures, configurations, checkpoint hashes if generated, and git commits if any.
8. **Resource safety report**: precise watchdog checks and any stop reason.
9. **Gate verdict**: BWL-0/1/2/3/4 PASS/PARTIAL/BLOCKED; explicitly state **STOPPED**. No further stage may be started automatically.

No fake completion times, promises of unattended follow-up, or premature performance claims.

---

### Final reminder

**The science is frozen; only implementation fidelity, independent supervision, controlled learning and physical verification are pending.** F5 is part of the coupled primary hypothesis, **not a proven improvement**. Keep it, test it against E and DIRECT, and do not make a 3D-only mechanism. The Blackwell server should do what GPUs are for; physics hosts should produce the independent physical evidence that makes the GPU training meaningful.
