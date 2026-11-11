# Approach B — Single-Session Post-Pilot Recovery and Training Contract (v2)

**Issued:** 2026-11-08  
**Project:** Latent Causal Infeasibility for Long-Horizon TAMP / Approach B  
**Scientific authority:** `final-fixed-methodology-1.pdf`, dated **2026-11-05**. Its semantics override this operational contract in any conflict.  
**Current reported development branch:** `naren/approachb-3d-learning`, report 13 at reported commit `c1188675`. Verify rather than assume.  
**Operator:** ONE continuing Claude Opus High session coordinating the approved physics host (gvlab) and Blackwell learning host; no second active Claude session.  
**Nature of this document:** An executable, bounded engineering work order. Do not represent proposed work as completed experiments.

## A. Actual authorization, resource ceilings and stopping point

The user will paste the accompanying kickoff prompt to authorize the following **and nothing beyond it**:

1. **Historical 3D recovery:** Resume existing audited root-sharded chunks after chunk 0, replay stored Y-positive witnesses, replay complete X relocation prefixes and test their stop-point connectors, and fully reconfirm eligible recorded relocation-failure negatives. Authorized aggregate **additional CPU consumption: maximum 60 CPU-hours** on gvlab, with **at most two workers**, exclusively on the **previously validated CPUs 16–17** if still free/approved. Start with a small recovery slice, measure, then continue autonomously within the cap if every gate passes. Never assume reported runtime estimates grant broader machine access. Set an enforceable wall-time guard; recommended **42 hours maximum elapsed for this work order**, if the host/guard can enforce it, and a per-query timeout consistent with the pinned teacher. Stop earlier on resource contention, any discrepancy or completion. If existing gvlab machine policies impose lower limits, the lower limit wins.
2. **Missing-endpoint Y protocol:** Develop and independently verify a new *target-only* query path for previously unlabelled endpoints, and perform a **small, preregistered pilot** only, consuming **at most 6 additional CPU-hours**. Do not automatically run all ~2,929 missing-Y queries. No other fresh 3D physics generation under this authority.
3. **Blackwell:** Perform data intake, real-record loader checks, frozen 2D baseline reproduction, and at most **6 aggregate GPU-hours** of serial, development-only smoke/preliminary training if and only if resource safety and data gates pass. This is **not** permission for an unbounded full D/E/DIRECT/G multiseed experiment. Use only GPU 0 and the previously verified CPU 7 with one CPU thread, if still permitted. Run no MuJoCo or CPU training on Blackwell.
4. **2D Q2:** Check status and intake only **after** both live writers finish and the merged, immutable dataset is hash-validated. Do not interrupt, reconfigure or compete with ongoing laptop/gvlab collectors. If merged Q2 is available and inspected, a bounded 2D placement-model smoke may use the above Blackwell GPU budget; no automatic full 2D experiment campaign.
5. **Preparation only:** Freeze sampler-sourced candidate-diverse pilot manifests, challenge-order split documentation and branch-local search interfaces, but do **not** run additional candidate-diverse physics experiments or the 75-root challenge collection under this work order.
6. **Mandatory stop:** Once the above stages have produced reports, **STOP**. Subsequent *bulk new-Y, sampler-sourced 2D/3D physics, enlarged worker counts, full 3D D/E/DIRECT/G multiseed training, BWL-7 integrated search and BWL-8 physical confirmation* require a new explicit user authorization and an audited budget. Do not leave unbounded jobs running after the response.

**Budget accounting:** Count actual measured process CPU-time aggregated across workers, not `workers × arbitrary ETA`; aggregate limits apply across all chunks and retries. Track retry costs and failed calls. A run's wall time is not identical to CPU-hours. Persist a machine-readable cumulative budget ledger. The 60 and 6 CPU-hour limits are separate: do not silently shift unused allowance between them. If a watchdog/cancellation mechanism cannot enforce a cap, stop rather than launching bulk work.

## B. Scientific invariants — frozen; no redesign

### B1. Architecture

- Input: original scene `S0`, initial robot state `q0`, original target `T` and goal, legally available object-placement domains; initial observation and supplied primitive geometry/poses/robot numerical features. No teacher labels, construction-intended solutions, or complete target sweep is a learner input.
- **Placement sampler:** target-goal-blind, conditioned on an object having been grasped; propose destinations in a hypothetical current scene. Its label is individual placeability, **not X**. Its learned density is not a calibrated feasibility probability. Analytical stratified+ranker and cVAE+ranker remain legitimate competitors; sampler superiority is **INCONCLUSIVE** on existing partially labelled validation.
- **Search:** constructs ordered move-once relocation sequences, with branch-local hypothetical object edits and repeated sampler calls when useful. A branch is evaluated by X/Y on the **complete root-relative ordered prefix**. A low-Y prefix can still be expanded; no terminal connector is inserted between consecutive corrective moves.
- **F1:** analytic endpoint and action-grammar legality only. **F2:** order-/predecessor-aware physical correction scorer, including root and robot context. **F3:** target/goal-aware hypothetical endpoint scorer from fixed `q_ref`. **F4:** omissions are new queries of the same X/Y functions, not an independent learned repair/omission head. **F5:** retained named quadratic X–Y interaction in coupled D. No separate 3D causal graph, low-level policy, learned IK, interim joint-state predictor or new energy mechanism.
- Baselines: D coupled X/Y, E uncoupled X/Y (F5 off), DIRECT-GEO direct-success predictor, G order-invariant X/Y, plus strong analytical repair/sampler controls. Do not pick a winner in advance; frozen 2D findings do not establish F5 superiority.

### B2. Exact X, Y and normalization

- `X_r=1`: under the versioned, finite-budget 3D teacher, starting at original `S0,q0`, the robot successfully executes the entire exact ordered relocation sequence using the pinned grasp/contact/motion convention, carries achieved robot/gripper/attachment state forward, and **at a stopping prefix only** completes a valid connector to fixed free-gripper `q_ref` in the edited scene. Do **not** reset to home or `q_ref` between corrective actions. Failure of A's stop-point connector does not prove AB cannot execute.
- `Y_s=1`: an independently replay-verified witness that the original target task succeeds in hypothetical final arrangement `s`, starting from the **same fixed `q_ref`**, with the original target and goal unchanged. Y is independent of order for identical endpoint scene/task/reference policy; AB and BA share Y but may have different X.
- `X_empty=1` by declared reference-state convention. No-op joint success is `P(Y0=1)`. Four `(X,Y)` combinations are meaningful.
- A query that was **attempted** and did not meet the protocol may be an operational 0 under the frozen finite-budget policy; retain detailed status, negative kind, failure phase and budget. **Never call such a 0 a globally certified physical impossibility.** Unattempted, incompatible, censored or missing queries are not zero.
- Pinned temperature `tau=1`. `P(Y_s=1)=sigmoid(b_s)`; `P(X_r=1 | Y_s=y)=sigmoid(a_r+w_r*y)`. Hence `p_success=sigmoid(b_s)*sigmoid(a_r+w_r)`. The normalized scene-first **root-consistent** factorization, its local normalizers, shared Y nodes, exact missing-data marginalization and root-wise deduplication are authoritative. A naive unnormalized local product is not equivalent.
- Observed-data root likelihood plus witness-valid travel Huber auxiliary is the X/Y training objective. **Cost selection**, separate from learning, uses `-log(max(p_success,epsilon)) + alpha*move_count + beta*displacement + gamma*J_hat`, with coefficients frozen on development validation. No invented large cost for failed actions.
- Train-time X/Y data must preserve complete physical-query keys, endpoint equivalence, teacher policy, robot/gripper/attachment context, the exact attempted budget, split, missing-label masks and witness provenance. No training from synthetic X labels except explicitly labelled synthetic self-tests.

### B3. Same 2D/3D method, separate physical teachers

2D has the full articulated planar 3R robot with continuous joint motion and discrete legal resting cells; 3D has the real articulated xArm-like shelf/cupboard protocol and support-constrained objects. They share the algorithm and exact X/Y semantics, **not necessarily encoder weights or identical geometry features**. The reported 3D feature adapter uses observable occupancy stand-ins and has **partial** feature parity; document that limitation rather than claiming general 3D geometry representation.

## C. Starting evidence: reported figures to independently confirm

**Last completed physics report:** 3D pilot plus recovery chunk 0 (`RECOVERY_GO`), pushed at reported `c1188675`, report 13. Historical generator and physical teacher hashes were reported to match all 37 pinned files and 1,582 roots under MuJoCo 3.16.0. gvlab used CPUs 16–17, two workers, with no Q2 interruption and no guard trips. Verify this from the actual manifests/trace logs before resuming.

- Original 3D relocation corpus: 4,815 ordered sequences attempted; 4,806 stored; 3,665 completed relocations; 1,141 originally failed relocations; nine attempted sequences were not stored. **6,773 unique prefix queries** are reported candidates for authentic X recovery, not automatically positive X labels.
- After pilot and chunk 0: **199 X labels** (178 positive via verified connector and 21 relocation-failure negatives), and **342 Y records** (118 replay-verified positives + 224 recorded negatives). **116 X queries have no matching Y record**; only 83 have both labels. All four combinations occur, but the cell counts are small.
- Remaining preliminary inventory: **6,595 X-prefix replay/connector candidates**, **2,527 Y-positive replays**, **866 listed negatives to reconfirm**, **2,929 missing Y endpoint queries**. The 6,595 and 2,527 counts align arithmetically with the above; **the 866 negative count does NOT trivially equal 1,141 minus the 21 reconfirmed = 1,120**. Resolve whether 254 records were filtered/deduplicated/out of scope, using raw unique keys before authorizing negative chunk scale. Document counts in *raw attempts*, *eligible unique X queries*, *already reconfirmed*, *noneligible/out-of-scope* and *remaining* forms. Do not silently drop anything.
- Pilot 145 items; chunk 0 30 train roots / 202 items. Reported 72/72 Y pilot positive replays, 30/30 negative reconfirmations, 35/35 X pilot connector successes, then 46 more Y positive replays and 143/143 X connectors in chunk 0; 13 additional relocation failures confirmed. Reported replay state match <=8.5e-11 rad, zero mismatches and three decided same-endpoint order contrasts. Cross-check all against raw output, including potential repeated queries in aggregate counts.
- Historical 3D target-only: 7,012 Y planning queries; 2,645 positives with saved trajectories, 4,367 negatives (reported 4,004 scoped finite grasp-family certificates, 363 policy budget-outs). These are planning/protocol outcomes; positive Y requires independent replay.
- Hard-order cohort: 75 excluded roots, reportedly 72 order-discordant pairs, and proposed 47 train / 15 validation / 13 inspected holdout roots. The 13 are **not a pristine blind test**. Verify lineage and selection mechanisms; keep distinct from the frozen 3D test split.
- 2D historical X/Y: 4,443 X, 3,831 Y on 398 development roots; P24 held-out 3,258 X/2,777 Y on 237 roots (635 roots total). Reported 188 2D order-discordant pairs in development. 60 prior frozen 2D models exist. Historical candidate catalogue was construction-informed, **not sampler-sourced**.
- 2D Q2: separate individual placement-label collection on the 5,000-root corpus; earlier progress updates are stale unless current checked. Do not equate Q2 samples to ordered X/Y. Its roots do not overlap historical 2D X/Y roots.
- Earlier Blackwell BWL-0–4: code at commits reportedly `69a6eeb8` and `985fe576`, sampler verdict inconclusive, all four XY arms numerically tested, watchdog updated; reports 08–12 and immutable 3D snapshot `v4full_82926152fa9cc345` (59,972 3D placement queries). This prior work is frozen and **must not be redone without evidence of corruption**.

## D. Stage R0 — Safe, precise intake/reconciliation

**Execute first, before bulk work.**

1. Inspect and hash the actual local source branches, report 13, reports 00–12, the prior `APPROACH_B_SINGLE_SESSION_NEXT_EXECUTION_v1.md`, the preserved `APPROACH_B_EXISTING_DATA_REUSE_AUDIT.md` and `approach_b_reuse_audit/` archive. Verify all are preserved; do not read the other Claude chat as a substitute for source files. Do not alter the historical branches/test records.
2. Confirm physical host gvlab, simulator revision, robot and gripper/contact/attachment semantics, execution policy, scene-root lineage, target-reference pose, pilot source hashes, connector type and full-prefix replay protocol. Verify checkpoint mirroring on Blackwell before touching the training worktree.
3. Reconstruct one deduplicated **canonical query ledger**:
   - X identity: original root + initial robot state + ordered physical object/destination sequence + terminal-stop `q_ref`/teacher policy/budget + grasp/contact/asset hashes.
   - Y identity: original root + target/goal + exact edited physical endpoint + fixed `q_ref` + target-only policy/budget + asset hash. Same-endpoint AB/BA share Y.
   - Include case family, lineage, split, query status and evidence/proof scope, source file hash, positive witness hash, replay status, connector status, failed phase, attempt counts and measured costs where valid.
   - Preserve ancestor/descendant prefix links without treating a complete-sequence success as proof for every different-order or different-stop query.
4. Resolve 1,141-vs-866 negative count discrepancy with a machine-verifiable derivation. Recheck `6,773 -> 6,595`, `2,645 -> 2,527`, and all `X/Y` paired-label totals by unique keys. Reconcile the 151 historically executed X overlaps and 129 known Y endpoints removed from the earlier 887-X manifest; do not double collect them.
5. Validate held-out split isolation and immutable test roots. Resume only actual authorized existing recovery chunks, starting after chunk 0; never mark a split or record as blind after model selection has examined its outcomes.
6. Preflight guards on gvlab: Q2 process health, worker CPU affinity, resource consumption, CPU/thermal protection, cancellation-by-owned-PID and no broad process matching. Blackwell: previously verified watchdog self-stop, CPU7, GPU0, script allowlist and collaborator queue guard. If any fails, stop that host's new work and continue safe audit on the other host.
7. Publish brief `R0_INTAKE_AND_BUDGET_LEDGER.md` plus machine-readable `R0_QUERY_RECONCILIATION.json` **before** starting a long recovery chunk. Include actual source paths rather than guessed names.

**Exit:** trusted deduplicated ledger; explanation of any count difference; machine and policy equivalence; no split/label/status leakage; enforced budget caps. Otherwise `R0_BLOCKED`, no bulk work.

## E. Stage R1 — Complete historical 3D recovery within 60 CPU-hour cap

**Proceed without reasking only if R0 passes and the user has pasted the companion kickoff prompt containing the explicit 60 CPU-hour authorization.** No third or fourth worker while Q2 is active. Always keep two workers on CPUs 16–17 only when the host has revalidated availability; immediately yield to Q2 or other users when required.

### E1. Resumable job design

- Use the already validated recovery runner, manifest and 53-chunk plan (`chunk 0` done), not a new framework. Each chunk is root-sharded, deterministically addressed and idempotent; persist complete and partial status, elapsed CPU/wall, safe resume cursor, exact source and witness hashes. New results reside in additive versioned sidecars, never by mutating the original corpus.
- First run one modest new chunk (or subset) as a resumed-system smoke; verify exact label continuity with report 13. If no mismatches and budget guard is functional, proceed serially/continuously through other eligible historical chunks within the approved cap. A report after every 5 chunks or a reasonable lower interval must record counts, split coverage and resource usage; stop immediately on mismatch.
- Schedule recovered Y-positive witness replays and X-prefix replay + connector, interleaving root shards where useful. Do not select only easily recovered positives. Include K0, K1, K2, K3, observed order swaps and all split groups; preserve missingness.
- **Negative reconfirmation is full, not sampled**, for all deduplicated, eligible historical relocation-failure X queries under the exact adopted teacher policy, subject to the overall cap. Give their count separately from raw 1,141 failures and link each label to exact proof/attempt scope; if budget cap is reached, report remaining negatives unverified rather than completing them by assertion.

### E2. Requirements for verified positive X

For each ordered-prefix X query, reset to the original `S0,q0`, reconstruct robot/gripper/attachment/contact mode through independent replay of the exact stored relocation steps, check each complete grasp/transport/release/retreat, carry achieved state into the next move, then attempt and replay collision-free terminal connector from the achieved end state to the pinned free-gripper `q_ref`. Check endpoint object poses and stability under the pinned support convention. Save all pertinent witness hashes and terminal joint/attachment state. No connector-only teleport; no home reset between moves. K0 X is one by convention.

For relocation failures: reconfirm under the identical old policy/budget and record failure phase; this is operational 0, not universal proof. If an old saved run is unreplayable, missing, conflicting or simulator-incompatible, mark unresolved/requires full rerun, **never** manufacture an X result. A stop-connector failure at A is not a certificate against extending to AB.

### E3. Requirements for Y

For each preexisting planning-positive Y, independently replay the saved original target trajectory at fixed `q_ref`, with the exact hypothetical edited scene and target goal; verify physical robot/object/contact outcome through the declared teacher. No old planning-only positive becomes final without replay. For existing negative Y, preserve exact finite-grasp certificate or finite-budget negative kind and independent scope. Do not infer a negative from lack of a saved positive trajectory. Deduplicate endpoint Y records across order variants and across repeated prefixes.

### E4. Invariants, metrics and stopping gates

- Zero unexplained playback mismatch; explicit record of any remaining mismatches and whether they arise from mode reconstruction, contact, assets, target state, numerical tolerances or policy difference. A real evidence mismatch blocks unqualified batch continuation.
- Track raw vs unique vs recoverable vs completed vs unknown per root, split and K; `X=1`, `X=0`, `Y=1`, `Y=0`, and paired four-cell counts. Include order-discordant same-endpoint pairs and omission controls, connector failures if observed, and failures per movement phase. Do **not** fabricate order contrasts or force connector failures to exist.
- Record actual average and tail CPU time/query; total CPU-hour ledger including retries, 2-worker utilization, thermal/queue/watchdog status, all positive witness hashes, rerun reasons. Do not exceed **60 additional CPU-hours**; stop at cap, technical failure or completed eligible work. Do not automatically switch to 12 workers after Q2 finishes.

**Exit:** all eligible historical evidence recovered or a precise, resumable cap-limited remainder. Save an immutable, hash-audited **3D recovered-X/Y sidecar** and `R1_RECOVERY_REPORT.md`. This can support initial real 3D learning; it is not automatically candidate-diverse training data.

## F. Stage R2 — New Y for missing endpoint scenes: protocol + <=6 CPU-hour pilot

Do this alongside safe R1 planning or after R1 validation, but never at the cost of disrupting the live Q2 collector.

1. Recompute the exact number of unmatched **unique Y endpoint keys** arising from the existing X prefixes after historical deduplication; 2,929 is a reported preliminary count, not an assumption to code around.
2. Implement a minimal target-only query for an edited scene, same target/goal, fixed `q_ref`, exact source robot/asset/contact/grasp/teacher budgets; reset from the canonical root and apply only the hypothetical object pose edits. No historical relocation path is assumed in Y.
3. Freeze a small pilot sample **before outcomes are read**. Include training and validation roots, K0–K3, both originally X-positive and X-negative endpoints, same-endpoint multiple orders, occupied/illegal cases treated by declared eligibility masks, and known existing Y controls for equivalence.
4. For each new eligible query, independently plan and replay target success; 1 requires witness execution/replay. Attempted finite-budget failures may be recorded as operational 0 under the exact declared policy, retaining negative kind. Unattempted/out-of-scope/timeout caused by *meta budget exhaustion before a query starts* remains missing. Distinguish query-level teacher budget-out (attempted 0) from collection job cancellation (missing).
5. Compare existing Y controls to their prior labels and scene keys exactly. Y must be invariant to AB/BA action order when endpoints match. Save actual simulator state/witness evidence. If calibration/replay mismatch occurs, stop the pilot and repair the protocol rather than weakening evidence standards.
6. Spend at most **6 additional CPU-hours**; output a measured distribution of success/failure/unknown, per-Y runtime, and a conservative estimate for full missing-Y collection. **Do not launch all missing-Y queries** without another budget authorization.

**Exit:** validated new-Y protocol, small independently verified pilot sidecar, `R2_MISSING_Y_PILOT_REPORT.md`, and a clean bulk-manifest proposal only.

## G. Stage R3 — Order-challenge and sampler-diverse collection readiness (no new physics)

1. Audit the 75 excluded order-dependent 3D roots, their exact lineage and selection procedure. Freeze/reproduce the proposed 47 train / 15 validation / 13 *already aggregate-inspected* holdout allocation only if source-linked constraints confirm no conflict; else derive and explain a leakage-safe split before any use. Never intermingle these with original untouched test data. The test/holdout challenge is explicitly **non-blind** if its outcomes were inspected.
2. Generate **predeclared**, non-construction-guided candidate-diverse manifests separately for 3D and 2D. For 3D use legal proposals from the current sampler candidates (cVAE+ranker, stratified+ranker, optionally categorical control); for 2D wait until the Q2 placement sampler is trained or use a declared nonlearning proposal baseline. Include no-op, alternative endpoints, K1–K3, same-endpoint AB/BA, omitted-move, nuisance, and low-Y prefixes retained for possible later extension.
3. Separate *physical confirmation of individual placement proposals* (the existing 138-scene / 2,666-tuple manifest; 2,089 previously untested tuples) from *full ordered X/Y sequence trials*. The former validates placement, the latter validates high-level correction. Do not substitute one for the other. Prior test-scene exposure makes the 138-scene panel a **disclosed confirmation panel**, not pristine blind evaluation.
4. Put realistic, measured CPU-hour/query budgets and expected coverage/failure categories into the new manifests. No candidate-diverse physics is authorized in this work order.
5. Design diagnostic comparisons to test real order dependence and order invariance: AB and BA may both succeed; may differ; or may both fail. Do not fabricate desired discordance. Distinguish when one move suffices and a second is an unnecessary costly correction.

**Exit:** frozen candidate-diverse and hard-order manifests, independent-root split handling, no new physics claims. Produce `R3_FUTURE_PILOT_PLAN.md`.

## H. Stage R4 — Blackwell genuine-data preparation and limited training (<=6 GPU-hours)

Start Blackwell read-only data work as soon as audited 3D sidecars exist. Respect 2D Q2 and physical host safety. No unrestricted model search or test tuning.

### H1. Environment and code parity

- Verify GPU 0 + CPU7 one thread, watchdog, actual script allowlist and clean kill-by-owned PID before each run; no GPU work if another user has priority. No CPU physics or extra DataLoader workers. Preserve archived 21 checkpoints and new categorical controls, their mirrors, and prior BWL outputs.
- Use the existing 3D `xy3d.py`, `xy3d_data.py`, tests and the source-verified 2D F2/F3/F5 implementation; no second 3D mechanism. Record limitations of 3D occupancy stand-ins versus source 2D geometric features and fixed `q_ref` convention. Keep tests of shared endpoint Y, AB/BA order-sensitive X, group normalization, gradient in coupling, empty no-op, mask marginalization and cache invariance.
- Build/validate one X/Y sidecar intake from R1/R2 with exact split grouping, identical learner-visible input semantics, source witness hash checks, binary observed labels versus missing-mask separation, cost readouts only from appropriate completed witnesses, duplicated prefix/endpoint dedup, policy/profile compatibility. Reject contamination with `construction.intended`, oracle geometry labels, search seeds, future trajectories or test-family IDs.

### H2. 2D historical baseline now (do not touch P24)

- Inventory 60 frozen models and historical 398-root development X/Y dataset (4,443 X / 3,831 Y). Reproduce source-level metrics/identity on known development splits where possible; do not re-fit to P24 and do not treat those historical intended-catalogue results as sampler-diverse generalization.
- A limited development-only real-data 2D train smoke is permitted **only if needed** to check current loader/model parity; prefer checkpoint reuse. Save independently seeded and pinned small sanity outcomes, not a falsely reported full baseline campaign.

### H3. Preliminary authentic 3D X/Y fitting, if adequate labels

- Read first authentic 3D sidecar and **predeclare readiness criteria before looking at validation performance**. At minimum require: identity-verified training/validation roots, nontrivial X positive and X operational-negative coverage, observed Y positives/negatives, and an auditable count of paired X/Y outcomes from all four combinations; if some categories are sparse, mark limitations. No test-root labels for tuning.
- If data satisfy the minimum fit sanity requirements, run **bounded one-seed development-only fits** of matched D/E/DIRECT-GEO/G (or a smaller debugging subset if warranted), preserving the final normalized joint observed-data loss and the same input features/optimization budgets. Train/evaluate on development/train+validation only. No test-root selection, no fabricated X/Y completions, and no superiority claim from a smoke.
- If paired data remain too sparse, stop at data/gradient checks and report `TRAINING_BLOCKED_INSUFFICIENT_PAIRED_EVIDENCE`; do not fill with synthetic X, assume independent X/Y, drop F5, or silently change the algorithm.
- Full matched multi-seed 3D training is **not** authorized here. Estimate required budget and data balance for a subsequent request.

### H4. Q2 intake, conditional on completed merge

- Verify completed root counts, split isolation and immutable manifest hashes from *both* 2D Q2 collectors and the merge. Do not infer completion from an old ETA. If merged, perform loader and label-scope checks, then optionally a small 2D placement sampler smoke within the same GPU cap; retain analytical/learned baselines and untested outcomes as unknown. If Q2 incomplete, report actual progress and leave it running untouched.

**Exit:** safe data loaders, reproducible 2D baseline evidence, initial physically supervised 3D learning readiness or bounded development smoke, status of Q2. Total new GPU time across H2–H4 <= **6 GPU-hours**, serially. Report `R4_BLACKWELL_INTAKE_AND_SMOKE.md`.

## I. Stage R5 — Exact deliverables, go/no-go and STOP

### File ownership / minimal code

- Use existing repo structure; add only the minimum necessary repair to existing runners, importers or audit scripts. Prefer small source modules ~120–280 logical lines; justify >300 and do not create duplicate framework directories. No blanket refactoring or automatic dependency upgrades. Use JSON/NPZ/CSV/Markdown and existing visualization pipeline. Do not add README/reports in unrelated repos.
- All new sidecars and trained checkpoints are **immutable, content-hashed, additive** and stored under versioned output namespaces. Maintain off-repo authorized mirrors where already used. No raw giant datasets/checkpoints or secrets in git. An editable source/report commit is allowed only after tests, manifest validation and clean diff inspection. Do not push to an unrelated branch. Distinguish code commit from external data snapshot.

### Minimum reports

1. `R0_INTAKE_AND_BUDGET_LEDGER.md` and canonical query ledger with scope and negative-count reconciliation.
2. `R1_RECOVERY_REPORT.md`, including X/Y recovery breakdown by train/val/test and new proof/witness status, replay/connector results, actual CPU-hours, mismatches, and hashes.
3. `R2_MISSING_Y_PILOT_REPORT.md`, actual evidence and revised total-Y estimate.
4. `R3_FUTURE_PILOT_PLAN.md`, frozen source-independent sampler proposals and challenge order cohort.
5. `R4_BLACKWELL_INTAKE_AND_SMOKE.md`, true/false real-training availability, repeated math tests and bounded development results.
6. A concise sequential `14_POST_PILOT_RECOVERY_AND_TRAINING_DECISION.md` (or next available report number), with a machine-readable status JSON. Do not overwrite existing reports 00–13.
7. A small set of faithful visuals: historical vs replayed relocations, connector sequence, fixed-q_ref edited-scene Y, same-endpoint order contrast and per-stage label coverage. Every visualization must cite actual logged states/witnesses; schematics explicitly labelled.

### Required final human report shape

- Exact branch/commit + source/asset/teacher hashes and access limitations.
- Stages R0–R5 `PASS / PARTIAL / BLOCKED`, what actually ran vs what was only prepared.
- Historical recovered unique X and Y, X/Y paired combinations, X positive/negative, Y positive/negative, split counts and scope; remaining queries by status and reason; negative count reconciled.
- Y protocol pilot evidence and resource measured versus authorized caps.
- Q2 status and historical 2D baseline readiness; 3D D/E/DIRECT/G development-smoke or precise block.
- Source leakage and test-set safeguards, observed order-discordance versus non-order-sensitive examples, fixed budgets and runtime/resource guard telemetry.
- Next three gated actions with measured input need and requested compute cap: missing-Y bulk, sampler-sourced 2D/3D X/Y pilot, matched full training and integrated independent physical confirmation.
- All report/output paths and any files that remain uncommitted; explicit safe stop state, no orphaned workload.

### Hard stop conditions

Any of: replays disagree with pinned teacher beyond documented tolerance; source/asset policy changes; unfixable gripper/attachment reconstruction; lost split isolation, label leakage or test-root tuning; physical host/Q2/collaborator contention; missing guard/CPU affinity or kill safety; cumulative CPU/GPU/wall cap reached; budget ledger missing; unexpectedly incomplete/corrupt witness; or any attempt to treat planning-only positives as replay-verified X/Y. Mark affected records unresolved, preserve raw evidence, report and STOP relevant host. Continue independent safe tasks only when no cross-dependency is compromised.

## J. What this work order does *not* prove

Historical X/Y recovery is authentic *under the pinned policy*, but its intended-catalogue sampling is construction-informed. It cannot by itself establish robust generalization to sampler-generated corrective destinations. A small development fit is not a full D/E/DIRECT/G experiment, and a D/E difference does not alone prove F5 is causally meaningful. Validation on exposed test roots is not pristine blind evaluation. The final scientific claim still requires candidate-diverse authentic X/Y, independent proposal physical checking, held-out matched D/E/DIRECT/G results with uncertainty, bounded dynamic search and independent executable repair verification in both 2D and 3D.

**After R5: STOP.** Do not expand scopes just because hardware is available or the first chunks appear successful.
