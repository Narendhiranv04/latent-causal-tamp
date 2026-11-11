# Approach B X/Y — BXY-P9: Connector-aware teacher and bounded supervision pilot

**Status:** Handoff / new work instruction, **not an executed result**.  
**Scientific authority:** `Approach_B_Final_Methodology_2026-10-31.pdf` (13 pages, 2026-10-31), particularly §§2.1–2.3, 3–6, 8.  
**GitHub repository:** `Narendhiranv04/latent-causal-tamp`; branch `approach-b-xy-v1`; inspected HEAD `156ddf94117ab2202c7d6f32404043a683157585` (2026-10-31 IST).  
**Prior implementation commit:** `daeec40082b173fdc4d47fc0e857ac30fa3e6760`. The only subsequent branch change was raw LB/X/Y training stdout logs; no teacher collection or source changes.  
**Execution rule:** Finish **BXY-P9 only**, report, and STOP. No P-min/P-full, 300-root collection, neural retraining or retuning, new test evaluation, 3D, or Approach D work.

## A. Verified starting point — treat these as historical facts, not targets

1. `responses-phases/0106`–`0113` document BXY Phases 0–8. `bxy_data.py` builds `BXY_SIDECAR_V1` for 231 accepted roots (`176 train / 21 validation / 34 historical test`), with the recorded `BD_GEN_V1` hash `78ca0e7c35d5a2b937554c03ce38b06db2486e5d74af5f2831e37e335ccb1a38`. The original snapshot is **external to the repository**, typically `BXY_DATA=/home/naren/Desktop/rss_ebm_dataset_snapshot/20261031_mock2d_5000_full` on the author's machine. Confirm existence, hash and readonly access before doing data-dependent work. If unavailable, do source-only tests and STOP with `BLOCKED_DATA`.
2. The existing training observations consist of `860 Y` and `109 X=0`, **no X=1**; the old `616` successful train repairs do not provide matched X+connector or matched travel. The old X/Y run selects no-op on all 34 historical test roots (55.9%), versus historical LB mean 69.6%; shortest nonempty 82.4% but high unnecessary-move rate; verify-first 97.1% uses recorded outcomes and is **not** a zero-query selector. Never present these historical numbers as a new experiment.
3. `bxy_core.py` already implements the correct root-consistent normalized X/Y Boltzmann model and tests; its `views()` currently reads the V1 sidecar, and its `j_obs` is **legacy** travel. Do **not** train that travel head on unconverted records or claim it is final-methodology J.
4. `bxy_lb.py:run()` evaluates and writes test predictions during each seed's training procedure, before `bxy_run.py:freeze()`. Historical report `0112`'s strict first-read custody claim is not established. Preserve records as history; fix custody in a **fresh** evaluation workflow later, never rewrite historical files.
5. `bxy_run.py:choose()` presently has no explicit F1 analytic hard-screen call, and the no-op `J_hat=0` convention needs reconciliation with the final PDF's `J` definition including target travel. These are **tracked deferred protocol questions**, not reasons to rebuild selection in P9.
6. Historical `p16_common.verify_sequence()` greedily picks one cheapest motion mode per relocation **and then attempts the target from achieved q**; it does not supply X+connector. The P17 existential verifier is a different policy. Choose **one fixed versioned X teacher** for the pilot (default the historical BD2D greedy P16_FAST path, since identical attempted-label reuse needs an identical protocol); do not silently alternate greedy and existential policies. If a robust existential control is useful, isolate it as a separate versioned diagnostic without merging labels.
7. Inspect `bd_2d.py` `QB={motion_checks:150, online_moves:8, goal_plans:3, transit_plans:6}`, `ADMIN_CPU_S=900` (historical root construction), `bd_2d.t_goal()`, `p16_motion.DetPhysics`, `p16_motion.replay`, `p17_verify.py`, `motion.checkers`, `geometry.certify`, `ordered.joint_travel`. Current historical verifier `p16_motion.replay()` expects a terminal **target** record, so it cannot be used unchanged to certify a relocation+connector X witness. Implement a narrowly scoped independent replay for that witness.

## B. Methodology that must remain exact

For a root `c` with starting scene `S0`, initial robot `q0`, fixed target start `q_ref=q0` unless a predeclared root says otherwise, ordered corrective prefix `q=((o1,d1),...,(ot,dt))`, and its deterministic edited scene `S^q`:

- **X(q):** under a declared finite teacher budget, physically execute **each** requested relocation from the actual achieved robot state of the preceding move; include approach, grasp, transport, placement, release, safe retreat; **then** verify a collision-free **free-gripper, unattached** connector from the terminal q to the **exact `q_ref` in `S^q`**. Apply connector only at a considered stopping prefix, not between successive corrective moves. `X(empty)=1` if the reference state is already available.
- **Y(S^q):** independently attempt the *original target task* in hypothetically edited `S^q`, with all nonedited bodies retained, from the **same fixed `q_ref`**, with the same declared goal/teacher budgets. Query Y even for an X=0 prefix. The robot does **not** have to be able to execute the hypothetical edits.
- The pair `(X,Y)` may take **all four** states `00,01,10,11`. A positive joint event means X witness + connector can be concatenated with a valid Y witness, after actual continuity and contact validation. `Y=1` is not guaranteed at every intermediate prefix, and `(0,1)` is not an error.
- **Keys:** unique ordered physical prefixes have unique X keys; different orders with the same **actual final object poses** and root/task/reference state reuse one Y key. The Y key must include versioned/root context and collision-independent identity, with provenance for all ignored fields. Omissions are recomputed as new sequences from S0; retained order preserved, omitted IDs stay at initial poses. Do not infer omission labels from existing trajectory deletion.
- **Binary training contract:** only a **completed, actually attempted query** under its **predeclared teacher budget** receives label `1` on full verification and otherwise `0`, including exhausted planner budgets. Store `negative_kind`, failed phase, attempts, physical status and budgets. **Unattempted** queries, interrupted administrative watchdog kills, missing worker outputs, invalid inputs, and unfinished/corrupt replay must be **unobserved/invalid** rather than fabricated zeros. Binary zero is **not** a certificate of global impossibility.
- **No leakage:** learner sees only initial scene/render/GT masks, supplied geometry/poses, robot state, candidate sequences and inferred ideal scene edits. Teacher trajectories, test labels, future observations, endpoint success, oracle distances and repair witnesses remain in privileged data only.

## C. One narrowly scoped implementation gate

### C1. Audit before editing

Run `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, inspect `git log -5 --oneline`, compare working tree to inspected commit, read the 13-page PDF locally and `0106–0113` reports, and inspect the actual signatures of the functions in section A. Document source/hash/environment discrepancies and **STOP if the branch or dataset do not match without an explicit resolution**. Never reset or discard work.

### C2. Teacher adapter — minimal files, no refactor

Preferred new files (change names only if the repository provides clearer existing ownership):

- `bxy_teacher.py`: canonical query identity, fixed teacher policy/budget, independent relocation-only enumeration, terminal connector, independent replay, Y query, matched witness/travel provenance, serialization. Split at ~300 logical lines only if necessary, with a recorded ownership reason.
- `bxy_pilot.py`: bounded worklist, dry-run manifest, resume/atomic sidecar writing, CPU and wall watchdogs, source hashes and summary/visual hook; keep thin.
- `tests/test_bxy_teacher.py`: synthetic and real-source tests; can grow beyond ten tests if needed.
- `responses-phases/0114_BXY_P9_TEACHER_PILOT.md`: exact new gate report.
- `runs/approach_b/bxy_teacher_pilot_v1/`: **new** result area; never edit `runs/approach_b/bxy/SIDECAR.json`, `FROZEN.json`, historical checkpoints/plots or `bd2d_lb_v1`.

Permitted narrow helper changes only when justified by tests: e.g. export an existing **free-arm** checker or correctly account for a connector segment in an existing utility. Do not change `bd_core.py`, `bd_2d.py`, existing `p16_*`, `p17_*`, `bxy_core.py`, `bxy_run.py`, `bxy_lb.py`, Approach D, old seeds, numerical clearance tolerance, 48-grasp family, robot config, or older reports. A failure to reuse code without changing these must be reported as a blocker and requested for follow-up, not worked around with a fake simulator.

### C3. X implementation requirements

1. Start at stored `S0`, q0, gripper gap, free/attached mode and configured profile. Validate unique movable IDs, supported destination cells, no target move or duplicate move, legal finite domain, one margin. A rejected malformed query is `INELIGIBLE`, not an attempted X=0.
2. Use the **same** `DetPhysics` profile and per-query counts as the historical greedy teacher; record whether any replay/seed/caching choices differ. For each fixed order, take verified relocation edges only, carrying final joints and object poses across actions; log step witnesses. A failed relocation attempt within the completed query's budget is operational X=0. Preserve failure metadata.
3. On reaching the prefix endpoint, construct the **edited full scene including target and all other objects**; verify free gripper, no attachment, valid terminal safe-retreat state, and **both terminal and reference q** in collision-free configurations.
4. Plan a connector q_final→q_ref **in that scene with all bodies present**, using conservative full-arm/link/finger collision checks (`geometry.certify`/existing planner and certified segments) and the existing `transit_plans` counter. No teleport, reset, target excluded from free-arm collision world, fake straight-line motion or silent new planner settings. Use `p16_motion.DetPhysics._transit` only if its contact, `gap`, collision-world and counted-budget semantics are proven compatible; otherwise add a documented tiny adapter with existing geometry/planner functions. Check free gap exactly against the reference gripper contract.
5. Independently replay **relocations plus connector** with each stored segment, collision/contact allowance, robot/object continuity, target/resting object positions, joint limits and gripper/attachment schedule; require `||q_terminal−q_ref||∞ <= 1e-6` (or the repository's tested tolerance, cited explicitly). `X=1` only if the full witness and independent replay pass. Do not call `p16_motion.replay()` unchanged with the connector masquerading as the target.
6. Cache and store the first successful full X witness and also each **successfully reached prefix before the terminal connector** with separate provenance. Never infer positive X for a shorter prefix just because it is embedded in a longer successful sequence: its own terminal connector still needs testing. An X=0 for a failed prefix must be exact for the frozen policy/budget, not a blanket claim about all paths.
7. Log `J_move`, `J_between_actions`, `J_connector`; independently query Y and, when it has a complete witness, `J_target`. For a valid *matched complete X+Y* witness, log `J_total` computed with the 2026-10-31 PDF's **unwrapped normalized joint-space travel convention** across the complete stitched path (including connector and target). Do not assume that summing separate per-record numbers is identical unless cross-record joints and normalization are checked. Log gripper operations separately. `J` is an observed policy-witness travel value, **not** minimum possible travel. Do not silently set nonempty legacy J equal to new J; record no-op target travel convention explicitly.

### C4. Y implementation requirements

1. Construct `S^q` from S0 with **only** proposed object resting positions changed, leaving robot/task and all other object identities untouched; use the same frozen `q_ref` for all matched Y queries and preserve original GT visual appearance anchors.
2. Evaluate original T from q_ref using the pinned deterministic `bd_2d.t_goal` compatible interface and the full target goal+safe-retreat criterion. Independently replay the entire target witness if positive. Keep unsuccessful attempted outcomes binary 0 with status/budget/failure metadata; nonattempted remain absent.
3. Cache identical `(root, sorted-final-poses, target, q_ref, profile, teacher budget)` Y once regardless of the X query's sequence order, and assert identity/equality under order swap.
4. **Do not** use the achieved q from X as Y's start. Do not derive Y from recorded full-sequence `labels.B`, and do not infer Y from static geometry alone.

## D. Pilot selection and resource authority

**PILOT_SCOPE:** an **exploratory development-only cohort**, never a fresh test cohort. Predeclare a sorted/hashed 20-root **TRAIN-only** roster, attempting to cover 4 K0, 6 K1, all available K≥2 train roots (previous report: K2=3, K3=1, K4=1), 3 `verified_K=None`, and remaining 2 roots for distribution diversity. If availability differs, record deviations, never reach into historical validation or test merely to hit a quota. `verified_K` and legacy B outcomes can guide this *diagnostic* pilot only; report selection bias and do not use pilot accuracy as prospective evidence.

Predeclare per-root candidate/prefix worklist **without observing new X/Y outcomes**: empty original Y, one recorded old-success candidate if present, one recorded old-fail, a same-endpoint reversed-order pair if present, one useful intermediate prefix, one omission recomputed from S0, and a nuisance/alternative destination control when present. Deduplicate all X and Y keys before querying. When the fixed per-root cap cannot fit every type, record missing types, prioritize paired X/Y and useful contrast diversity. Do not create successes by choosing answers after seeing the teacher results.

**Proposed hard cap for an *explicitly authorized* first pilot slice:** maximum 20 train roots; at most 60 distinct nonempty X queries and 60 distinct Y queries globally (Y0 may be reused if protocol precisely matches); at most **3,600 aggregate process CPU-seconds**, 3,600 elapsed wall-seconds, **2 workers**, and 300 process CPU-seconds per root. Preserve the teacher's `QB` per-query counters unchanged. Run every worker in a supervised bounded process; stable task keys, atomic write/rename and resumable ledger. Aggregate caps govern **which queries get attempted**; if a query is killed by the administrative guard without completing the teacher's own policy, mark it **censored/unobserved**, never zero. If system overload, unexpected high CPU, missing deterministic replay, or dataset mismatch occurs, STOP and report.

**Authorization:** This instruction file does **not** authorize consuming CPU by itself. Do source-only audit, implementation and unit/synthetic dry-run first; launch physical teacher queries only when the user explicitly approves the stated numeric cap (or a smaller specified cap) in the prompting message. If no cap is authorized, end at `READY_FOR_BOUNDED_PILOT` and STOP.

## E. Required new sidecar schema (`BXY_SIDECAR_V2_PILOT`, immutable)

For every root/query save at least:

```yaml
manifest:
  source_branch: approach-b-xy-v1
  source_commit: <actual HEAD>
  source_data_sha256: <recomputed>
  source_label_protocol: BD_BINARY_BUDGET_V1
  new_x_teacher_version: <pinned code and budget hashes>
  y_teacher_version: <pinned code and budget hashes>
  robot_profile_hash: <actual>
  reference_state_hash: <actual>
  dataset_split: train
  pilot_roster_hash: <predeclared>
  query_worklist_hash: <predeclared>
  counts_and_limits: <exact CPU/wall/workers/queries>
x_query:
  root: <id>
  x_key: <canonical ordered prefix>
  parent_y_key: <canonical endpoint scene>
  ordered_actions: [[object_id, physical_cell], ...]
  attempted: true|false
  observed: true|false
  y: 0|1|null
  teacher_status: <VERIFIED or failure>
  negative_kind: <category or null>
  failed_phase: <action index / connector / replay>
  budget_spent: <per field>
  q0: <joint vector/hash>
  q_ref: <joint vector/hash>
  final_q_before_connector: <joint vector/hash or null>
  final_q_after_connector: <joint vector/hash or null>
  witness_relocations: <IDs/hashes>
  witness_connector: <ID/hash or null>
  independent_replay: true|false|null
  travel_parts: <J_move / J_between / J_connector>
y_query:
  y_key: <shared edited-scene key>
  hypothetical_poses: <final object cells>
  robot_start_q_ref: <hash>
  attempted: true|false
  observed: true|false
  y: 0|1|null
  teacher_status: <VERIFIED or failure>
  failed_phase: <phase or null>
  target_witness: <ID/hash or null>
  independent_replay: true|false|null
  J_target: <float or null>
paired:
  x_key: <key>
  y_key: <key>
  matched_protocol: true|false
  full_joint_success: 0|1|null
  J_total: <float or null, only with matched stitched witness>
```

Omit the null/unused fields for other-side outcomes if that simplifies serialization, but never omit protocol identity, attempted/missing status or evidence scope. Keep the historical source and V1 sidecar byte-for-byte unchanged.

## F. Mandatory tests, negative controls and visual evidence

**Before physical collection**, demonstrate with synthetic/microfixtures where feasible:

- X identity order-sensitive; Y identity endpoint-only and shared for A→B / B→A; no aliasing across different roots, q_ref, robot profiles or task definitions; omission builds ideal prefixes from S0 and keeps omitted object present.
- X empty=1 by definition; Y0 is separately tested; correct zero vs missing vs administratively aborted semantics. Failed action at step j=0 and terminal-connector failure at the end are distinct metadata.
- Connector checks full robot, fingers, all objects and the target, gap and unattached mode; intentionally colliding path rejected; valid direct and planned transits handled with correct counters; failed connector never X positive; q_ref endpoint tolerance asserted.
- A longer successful prefix does not automatically set shorter prefix X=1; a Y=1 can coexist with X=0; all `00,01,10,11` are representable; missing one outcome cannot be filled from the other.
- Independent relocation/connector replay rejects a discontinuous robot path, wrong object destination, altered pose, omitted intermediate record, wrong attachment/gripper state, and a witness with only sampled (not certified) clearance.
- Query-key dedup across shared Y / omission aliases; repeated/resumed run does not double-charge labels; wrong teacher hash cannot be mixed; no train/val/test overlap.
- No learner-visible tensor can access privileged teacher paths, labels or witness hashes. Existing `tests/test_bxy.py` and archived six replays continue to pass when environment permits; avoid claiming they passed without running.

**Required visuals from actual evidence:** for 2–3 representative roots, original and hypothetical scene with all objects and full 3R arm; X relocation frames + q before and after connector; Y target trace from q_ref; a paired order contrast if observed; time/cost breakdown; failure/censored statuses visibly distinguished. A GIF from a simulated clean line between endpoints without certified trajectory must be marked `SCHEMATIC/NOT_RUN`. If no witness is obtained, generate failure diagrams and do not forge a successful animation.

## G. Pilot acceptance and stop logic

After all unit/dry-run checks pass and **only if physical budget explicitly authorized**, run the bounded pilot once and publish counts rather than invented quotas:

- distinct roots selected, attempted, completed, censored; per-query CPU/wall/calls and aggregate spend;
- X positives/negatives by prefix length and failure phase; Y positives/negatives; number of *matched decided* `(X,Y)` pairs and the four-cell table; distinct connectors replayed; root-deduplicated coverage;
- connector success rate **among successful relocation prefixes**; rate of legacy B positives that satisfy the new X/Y connector protocol, with full selection-bias disclosure;
- any **decided** same-endpoint reversed-order X contrast sharing Y; any decided omission/scene nonadditivity contrast; direct geometric and robot-start scope as appropriate;
- number of valid matched `J_total` witnesses, breakdown and correlation with legacy J **diagnostic only**; no claim of better optimization;
- distribution across K0–K4 and coverage limitations; explain why missing contrasting outcomes are absent;
- all source/robot/data/teacher/budget hashes and archived-replay pass/fail.

Decision states (no cherry-picking):

- `READY_FOR_P_MIN`: several replayed nonempty X=1 and X=0, independently decided Y, plus some **matched** pairs and matched J; enough to justify a larger **prospectively predeclared** collection design; **does not mean methodology validated**.
- `BLOCKED_CONNECTOR`: relocation witnesses exist but X+connector positives are rare or absent; explain whether q_ref collides, planner policy/budget fails, gripper state is incompatible, or genuine geometry blocks the connector. Do not replace q_ref, relax tolerance, omit connector, or use achieved-q Y to improve numbers.
- `BLOCKED_TEACHER`: inability to independently certify/replay or an interface inconsistency; code/physics must be fixed under a new explicit gate.
- `BLOCKED_DATA` / `BLOCKED_BUDGET`: source absent / permission absent / caps exhausted; preserve partial evidence.

**No neural retraining, λJ sweep, coupling selection, test metrics or full P-min/P-full collection in this gate.** Final 2D paper-level claim will require full prefix/omission coverage, balanced X/Y combinations and order contrasts, hard K3/K4 scenes, **new independent root-grouped frozen test cohort**, common operational full verifier for LB and XY, matched compute/labels and F1/travel convention repairs in a later gate.

## H. Mandatory final report format

Save `responses-phases/0114_BXY_P9_TEACHER_PILOT.md` with:

1. Exact branch, before/after HEAD, `git status`, committed changed-file inventory, source/dataset/config hashes and external dataset availability.
2. Implemented teacher policy, signed query and connector semantics, all relevant calls into actual repo functions; any intentional deviations from PDF.
3. Synthetic/unit/legacy test commands with actual exit codes, archived replays, failure tests, and a note about anything **not run**.
4. Approved numerical budget vs measured consumption, predeclared roster/worklist, all missing/censored cases and label/provenance breakdown.
5. Objective X/Y table, detailed witness and connector trace IDs, calibrated vs *uncalibrated* labels (no new model predictions), travel ledger and at least two actual visual links if available.
6. Issues discovered, including any code side paths that wrongly interpret absence as X=0, any accidental test-data access, historic P7 custody discrepancy, F1 screen and no-op J convention.
7. One exact verdict from Section G; recommended **next gate only** with explicitly required further CPU/resource authorization.
8. **STOP.** Do not start P-min, P-full, training or 3D.

## I. Sources inspected for this handoff

- PDF: `Approach_B_Final_Methodology_2026-10-31.pdf`, §§2–6, 8 (uploaded Project source; supersedes older v1.7/v1.9 on **new B X/Y semantics**).
- GitHub branch: https://github.com/Narendhiranv04/latent-causal-tamp/tree/156ddf94117ab2202c7d6f32404043a683157585
- `responses-phases/0106_BXY_P0_STARTING_STATE.md`, `0108_BXY_P2_DATA_INTERFACE.md`, `0109_BXY_P3_P4_MATH_AND_NEURAL.md`, `0110_BXY_P5_INITIAL_LEARNING.md`, `0111_BXY_P6_TRAVEL_AND_SELECTION.md`, `0112_BXY_P7_COMPARISON.md`, `0113_BXY_P8_DECISION.md`.
- Code: `bxy_data.py`, `bxy_core.py`, `bxy_run.py`, `bxy_lb.py`, `tests/test_bxy.py`, `bd_2d.py`, `bd_core.py`, `p16_common.py`, `p16_motion.py`, `p17_verify.py`, `p15_search.py`, `motion.py`, `geometry.py`, `p17_b.py`.
