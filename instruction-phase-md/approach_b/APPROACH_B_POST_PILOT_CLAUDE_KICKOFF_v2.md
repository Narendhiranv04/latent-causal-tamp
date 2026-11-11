# Claude Opus High — Immediate Single-Session Continuation Prompt

You are continuing the existing Approach B implementation after the successful 3D historical-replay pilot and Blackwell BWL-0–BWL-4. **This is the one continuing Claude session; the separate reuse-audit session is retired.** Do not start a fresh research architecture or redo prior completed work.

## Read first; authoritative inputs

1. Read the attached **`APPROACH_B_POST_PILOT_RECOVERY_AND_TRAINING_CONTRACT_v2.md`** in full. Treat its resource ceilings, stage order, guards and output requirements as the execution contract.
2. Read **`final-fixed-methodology-1.pdf` (November 5, 2026)** in full. It overrides this contract if any scientific semantics conflict.
3. Inspect the actual repository, report 13 and source manifests at the reported branch `naren/approachb-3d-learning`, commit `c1188675`; reports 00–12, previously preserved data-reuse audit, original 3D teacher, current Blackwell scripts, pinned simulator/robot-policy hashes and existing immutable snapshots. Verify paths and hashes rather than assuming the report is sufficient.

The last reported gvlab run has already passed: pilot 145 items and recovery chunk 0 (30 train roots), producing **199 genuine X labels**, **342 Y records** (118 replay-positive, 224 recorded negatives), and first three real same-endpoint order contrasts. It confirmed the historical teacher/replay policy. The 2D Q2 collection was still active as of that report. These are starting claims to verify locally, not new results to manufacture.

## Explicit permission and limits for this run

By sending this prompt, I authorize the bounded stages **R0–R5** in the attached contract:

- **gvlab historical 3D recovery:** resume after existing chunk 0, at most **60 additional aggregate CPU-hours**, at most **two workers on the previously validated CPUs 16–17** if still permitted/free. Use the same guards, root-sharded resumable chunks and pinned teacher. Recover all eligible existing Y-positive witnesses and X-prefix+connector witnesses, and **fully reconfirm eligible recorded relocation-failure negatives**, within the cap. Do not interrupt Q2 or any other user. Start with one small resumed chunk, validate results, then continue within the authorized cap without waiting for further instructions if clean. Stop at any discrepancy or safety guard.
- **New Y for endpoints with no Y record:** develop and run a **small, preregistered target-only pilot only**, maximum **6 additional CPU-hours**. Do **not** dispatch all approximately 2,929 missing endpoint queries.
- **Blackwell:** audit data intake, reproduce/reuse frozen 2D development baselines, check real 3D X/Y loaders and run development-only D/E/DIRECT-GEO/G smoke training if label adequacy and guard checks pass, at most **6 total GPU-hours**, serial jobs, GPU 0 + CPU 7 one thread if currently approved. No physics or CPU training on Blackwell. Do not tune on held-out P24 or frozen 3D test data.
- **Preparation only:** the 75 hard-order roots, sampler-proposed 2D/3D X/Y pilot manifests, individual sampler-proposal physical confirmation and full dynamic search. These are **NOT** authorized as large new physics runs now.
- **Stop after R5.** No automatic bulk missing-Y collection, new candidate-diverse campaign, 12-worker scale-up, or full multiseed 3D training until a subsequent explicit approval.

## Immediate work sequence

**R0 — Reconcile and preserve:** Verify report 13, replays, source/policy hashes, old splits and existing immutable data. Produce a single canonical X-prefix and Y-endpoint query ledger with strict deduplication. **Resolve the negative-count discrepancy**: 1,141 original relocation failures versus only 866 reported to remain, after 21 reconfirmed. Explain exactly which query keys were deduplicated, ineligible or already verified. Check 6,773 -> 6,595 X candidates and 2,645 -> 2,527 Y replays. Confirm the Q2 writers and host safety before any physical load.

**R1 — Historical 3D recovery:** Resume exact stored witness replays and final connectors; verify gripper/attachment state reconstruction and true continuing robot state. A successful X needs the complete ordered relocations plus the stopping-point connector to fixed `q_ref`; no intermediate home reset. A successful Y requires independent target replay from the same fixed `q_ref` in its hypothetical endpoint. Reconﬁrm every eligible negative within the cap, retaining finite-policy/budget negative kinds. Distinguish attempted 0 from unattempted/missing. Save additive, hashed, split-preserving sidecars and report actual completed/remainder counts. Preserve all test/holdout boundaries.

**R2 — Missing Y pilot:** Recompute exact unlabelled endpoint keys after deduplication. Build one pinned target-only evaluation protocol for those endpoints, run a small preregistered and bounded sample, independently replay target successes, and validate equivalence on existing Y controls. Return measured per-query cost and remaining bulk workload; stop before a full missing-Y sweep.

**R3 — Future scientific evidence:** Freeze the lineage-safe 75-root challenge split, reporting the 13 aggregate-exposed holdouts honestly. Prepare—not run—separate candidate-diverse 2D/3D sequence X/Y manifests with real AB/BA, no-op, omitted-move and alternative destination controls. Retain **stratified+ranker** alongside **cVAE+ranker**, and the categorical control; the existing sampler verdict remains **INCONCLUSIVE**. Do not misrepresent known-label offline precision as physical success.

**R4 — Blackwell real-data readiness:** Reuse the existing 60 frozen 2D models and 398 historical development roots first. Verify loader and masked root-consistent F2/F3/F5 likelihood on recovered 3D sidecars, keeping D coupled, E uncoupled, DIRECT-GEO and order-invariant G; 3D uses the same semantics with embodiment-specific features. If genuine paired X/Y coverage and safe GPU access are sufficient, run limited development-only authentic-label training smoke, **not** final multiseed/full-test training. If Q2 is actually merged, audit and optionally smoke-test its 2D placement sampler under the same GPU cap. Do not convert Q2 placement labels to X/Y or fill missing labels synthetically.

**R5 — Report and STOP:** Produce stage reports with source paths, hashes, new true X/Y label counts, four paired outcomes, replay mismatches, negative-scope reconciliation, order contrasts, measured CPU/GPU hours and guard telemetry, remaining missing-Y queries, Q2 status, training readiness and next authorized-budget request. Use the next available report number after 13. Commit only safe source/report changes and keep raw datasets/checkpoints outside git with verified authorized mirrors. No orphaned processes.

## Non-negotiable scientific and execution rules

- Keep the **November 5 Approach B** model unchanged: goal-blind placement sampler; dynamic root-relative sequence search; F2 ordered executability; F3 target restoration; **F5 X–Y coupling**; F4 omissions by reevaluation; root-consistent normalization with shared Y and observed-label marginalization.
- **No new 3D-specific mechanism**, learned IK, causal DAG or intermediate robot configuration predictor. No claim that F5 wins without matched real evidence.
- AB and BA with identical endpoint geometry share Y; X may differ, and some pairs legitimately work in both orders. If one move suffices, the cost-aware selector should not invent a reason to move two.
- A finite-budget attempted failure can be operational X/Y=0 under the pinned policy; it is not global impossibility. A not-attempted or unresolved query is missing.
- Never use frozen test/P24 outcomes to tune samplers, model weights, thresholds or challenge split choices. Preserve provenance of construction-informed historical catalogue and sampler-generated future queries separately.
- Stop affected work on any source mismatch, replay failure, Q2 interference, competing user, watchdog failure, loss of CPU affinity or budget-cap violation. Do not silently change the teacher or collect new large physics data to make a gate pass.

**Execute the permitted work now, using real repo and machine evidence, then provide a concise complete report and STOP. Do not ask me to revisit the already finalized architecture.**
