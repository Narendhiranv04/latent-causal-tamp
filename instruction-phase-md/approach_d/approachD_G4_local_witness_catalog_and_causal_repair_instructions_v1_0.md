# Approach D — G4: Local Witness-Grounded Motion Coverage and Causal Repair Evaluation

**Implementation instructions v1.0 | 29 October 2026**  
**Scope:** Local workstation only; existing 2D P13–P17 scenes, labels, checkpoints, offline teacher records and visualizations.  
**Starting point:** `approach-d-v1`, reported local commit `804e3ddf7` (G3). Inspect the actual HEAD first.  
**Result sought:** An executable, measured bridge between D's excellent counterfactual predictions and *verified* multi-object rearrangement with stored motions. Do **not** claim an efficacy gain unless measured.

---

## 1. Purpose and the one conceptual gap to close

G3 is now methodologically correct: **D selects a causal obstacle frontier and evaluates hypothetical obstacle–destination–stored-motion interventions for the original target T**. Geometry proposes destinations and examines actual stored sweeps; the provider certifies the exact stored actions and connectors. No IK, RRT or trajectory generation is permitted at inference.

The G3 *View A* counterfactual test is encouraging: 214 decided held-out P16-calibration edited scenes, **AUROC 0.949 (D), 0.781 (geometry), 0.559 (uniform)**. Yet the frozen G2c-lite C3 catalog only completed **1/12 development roots**, the already directly feasible scene, and **0/11 blocked roots**. G3 accepted numerous stored obstacle-relocation motions but could not realize any subsequent target T action. Additional generic straight-joint connectors did not help. This is **a motion-coverage problem**, not evidence that causal learning fails.

G4's goal is **not another learning architecture, another dataset generator, or large indiscriminate compiling**. It is to turn archived, already teacher-verified local repairs into accurate precompiled execution records, establish which capabilities are reusable, and run the same frozen G3 comparisons once some real repair chains are executable. G4 can pass an engineering milestone with a negative or inconclusive learned-efficacy result.

### The three things that must never be conflated

1. **Teacher/task feasibility:** historical offline solver verified some particular sequence from a specified occupancy and robot start q. It is an existence witness for *that task and protocol*, not necessarily a proof of minimal repair depth.
2. **Library realizability:** the finite precompiled provider can reproduce a compatible full chain using stored exact motions and connectors, after fresh collision verification and independent replay. A missing library motion means *unknown/unavailable within this library*, not physical infeasibility.
3. **Policy effectiveness:** D, geometry or uniform *discovers* a realizable repair under a common, limited search budget, **without being handed the teacher sequence as a runtime hint**.

**Root `p13_2026216000` (F12) is the canonical cautionary example:** historical P16 verifies `o00 -> 59; T`; G2b's library accepts a different `o00 -> 45; o01 -> 36; T`. The second relocation was library/placement contingent; it was not physically proven necessary. Never label this as a ground-truth K2 root.

## 2. What may be used, and what must remain unchanged

### Allowed local sources

Inspect the existing repository rather than assume paths:

- `runs/p13/**`, `runs/p16/**`, `runs/p17/**` **read-only**, with `runs/p16/data/dev/labels_v2w2.json`, `runs/p16/data/dev/plan.json`, P17 plan/label/catalog files and saved witness/replay trajectories where available.
- P16's fixed 12-root DEV fixture cohort; relevant P13/P16 train and P17 train/DEV roots for additional witnessed 2-, 3- or 4-step examples **only if those records actually exist**. Do not invent K3/K4 examples.
- Frozen Dp17 weights, `ad_causal.py`, `ad_provider.py`, `ad_runtime.py`, `ad_compile.py`, `ad_local.py`, `ad_viz.py`, `p17_d.py`, `p17_domain.py`, `p17_search.py`, `approach_d.toml` and reports `0102`, `0103`, `0104`.
- Existing planar robot, lattice, object footprints and side-grasp implementation. **This is the same local data as used for the existing A/B/C/D research comparisons.**

### Forbidden for this stage

- No SSH/server/GPU-server use, no 3D/xArm7 job, no server dataset ingestion or waiting for that track.
- No new scene generation or new root labels; no bulk retraining; **freeze Dp17 and A/B/C checkpoints**.
- No inference-time IK, RRT, solver, grasp synthesis, trajectory retargeting, connector synthesis or new motion generation. Offline compilation is allowed **only during the explicit G4 offline-compile stage**.
- No D queries with any moved obstacle as temporary target: **always query the original T, original goal**, using the current hypothetical occupancy and actual resulting robot q. No temporary-target recursion.
- No overwriting historical reports, `config.toml`, old labels or catalog C3; no merging or pushing.
- Do not run the sealed 442-query benchmark or use `p17test` for offline catalog selection. Do not compile from P16 calibration roots used in G3 View A. Treat P16 calibration's existing View A result as already inspected, not a new prospective test.
- The local P17 movement contract was **0–4 obstacle relocations** with historical label and search budgets. Do **not** silently transform it into the proposed 7-action protocol. If adding a new configurable total action cap, keep it distinct and off by default for archived experiments.

## 3. The minimal scientific questions

Answer these, in order:

**Q1. Motion ceiling:** For the existing local teacher-verified sequences, which individual actions and complete chains have a usable stored realization? Is failure due to missing target core, blocked entry connector, incompatible q, blocked relocation, or replay discrepancy?

**Q2. Witness recovery:** Can the existing historical witness records be imported or faithfully recompiled offline into self-contained, bitwise-continuous (or explicitly exactly connected) provider records, so that at least some blocked DEV roots can be repaired from storage only?

**Q3. Transfer, not memorization:** Do motion templates compiled from **other** existing training roots transfer to the fixed DEV roots? What is the difference between exact-scene witness reproduction and root-disjoint template reuse?

**Q4. Causal utility under a working catalog:** With the **same** catalog and motion-check/search budgets, does D select better obstacle/destination interventions than geometry or uniform? What improvement, if any, is specifically due to D's blocker marginals, its counterfactual feasibility predictions, and the swept-volume compatibility rule?

No new theorem, architecture, or loss is required.

## 4. Implementation plan, in strictly ordered steps

### G4.0 — Inspect and freeze the baseline

1. Run `git status`, identify HEAD and ensure local changes will not overwrite any user work. Read the G2b/G2c-lite/G3 code and reports.
2. Run the existing Approach D tests and baseline G3 `VIEW_A` / `VIEW_B` *using cached/saved results first*. If running a baseline measurement, use the frozen C3 catalog and exactly the G3 settings.
3. Copy/fingerprint the relevant baseline run manifests, catalog hashes, model hashes and fixed cohort definition to `runs/approach_d/g4/baseline/`.
4. Record historical baseline facts: `1/12` total; `0/11` blocked repaired; edit AUROC on P16 calib `0.949`; no new data or weights involved.

**Gate 0:** reproducible baseline, clean old files, no forbidden runtime calls. Do not proceed if pre-existing tests fail without a clear cause.

### G4.1 — Read-only witness inventory and failure localization

Make a *small deterministic witness manifest*, **before generating new motion templates**:

- **Cohort A (fixed):** the existing 12 P16 DEV roots, with all historically VERIFIED non-empty repair sequences, their source/destination cells, length, root q, target goal, and any accessible witness trajectories.
- **Cohort B (small, optional):** up to 12 additional eligible 2D TRAIN/DEV roots containing genuine historical 2–4 move **verified** sequences, sampled deterministically by root ID / mechanism and difficulty. Keep roots grouped; do not use new server scenes. Mark teacher uncertainty explicitly.
- **Transfer source pool:** only training roots disjoint from the fixed 12 DEV evaluation roots. The fact D itself has seen some DEV roots in historical training must be disclosed: this is a **catalog transfer test**, not a clean D generalization test.

For each witnessed sequence, inspect all stages: initial q, each obstacle's stored motion mode, grasp/carry/release/safe retreat, q_end, connector needs, target source and goal, and post-action occupancies. Compare existing C3 catalog coverage and identify the *first* point where the stored execution chain fails.

Output `WITNESS_MANIFEST.json` and a simple table/figure summarizing root, verified sequence, missing stages and whether source trajectories exist. Record `UNKNOWN` where a historical witness record is incomplete; do not fabricate it.

**Gate 1:** fixed inventory with no teacher-informed filtering based on new G4 search outcomes.

### G4.2 — Two explicitly separated offline catalogs

Use read-only historical data as sources. New files go exclusively under `runs/approach_d/g4/`.

**Catalog W-ROOT — exact witness-reconstruction / engineering ceiling.**

- Reconstruct or compile motion chains **for the specific already-teacher-verified development scenes**. Reuse complete historical motion records whenever they include the necessary joint paths, phase annotations and object attachment state. Otherwise invoke the existing offline IK/skill/connector planner **outside** inference, starting from the correct exact occupancy and robot q at that stage.
- Compile each action and required connector, not just a stand-alone `home -> home` target action. For the target, compile from the robot q *actually reached after previous relocations*; preserve exact original T goal.
- Include alternative branch/grasp modes only when needed to address a measured failure; prioritise **near-base entry transit, original-T action diversity and matching q continuity** over more similar generic obstacle moves.
- Validate each segment and the **whole chain** in the actual scene, including carried-object geometry, attachment/release phases, full retreat and changing occupancy; replay from original q with the G3 forbidden-call guard enabled.
- This catalog provides an **upper-bound engineering demonstrator**. A successful W-ROOT chain is **not** evidence of transfer or learned D superiority, because its offline compilation had access to the root's teacher witness.

**Catalog W-TRANSFER — root-disjoint reusable motions.**

- Build a compact catalog only from historical witness records on **training/source roots not among the fixed DEV target roots**.
- Normalize/index templates according to the existing G1/G2 exact-cell/relative/generic provenance rules *only where the existing compiler has a validated representation*. Never shift or synthesize a trajectory at runtime.
- For an evaluation DEV root, the provider may retrieve these stored **absolute** motions and exact compatible graph connectors and certify them in current occupancy, but neither the compiler nor catalog selector may read that DEV root's teacher sequence or failure trace to decide which template to add.
- Run the transfer catalog on all fixed DEV roots. Distinguish a template that originates from another root from a direct offline target-specific witness for the evaluation root.

**Budget:** Use an explicit conservative local workstation compile ledger (suggested maximum **400 total offline compile attempts or 1,200 CPU-seconds**, whichever is reached first). First reuse existing records; count fresh IK/connector attempts. No automatic large-scale retries or indefinite runs. You are authorized to execute this bounded local G4 pilot without further permission. If the first inventory shows this budget cannot meaningfully cover any verified repair, report the bottleneck instead of silently changing the budget. Check available disk/RAM and avoid oversubscribing the workstation.

For the *same target source/goal*, store multiple genuinely distinct grasp/branch/approach/connector alternatives **only if** they pass separate validation and add actual clearance coverage; do not equate many copies of the same swept corridor with useful diversity. Track target-core coverage separately from connector compatibility.

**Gate 2:** at least one validated whole-chain stored execution is demonstrated if technically achievable under the budget; otherwise a reproducible per-stage reason why the witness cannot be reconstructed. No artificial success labels.

### G4.3 — Explicit motion-availability diagnostic before policy evaluation

Before running learned search, compute for each DEV root and catalog:

- `teacher_has_verified_repair` for a specific source sequence (may coexist with UNKNOWN for other alternatives).
- `stored_relocation_step_available` for each stage at its actual q and occupancy.
- `stored_target_core_clear` in each relevant post-repair occupancy.
- `stored_target_entry_reachable` from the achieved robot q.
- `stored_full_chain_replayed` from root q.
- `catalog_ceiling` = how many of the **known teacher-witness candidate sequences** the catalog can execute when the exact sequence is supplied *for diagnosis only*.

**Important:** `catalog_ceiling` is conditional on the declared tested witness sequences, not a mathematically complete maximum over all possible repairs. Do not label an untested root infeasible.

Break down `NO_TEMPLATE`, blocked entry, target-core collision, gripper/held-object collision, q incompatibility, budget exhaustion and replay failure. Display an example of a specific target sweep and its connector; don't draw one global, supposedly mandatory target swept volume.

**Gate 3:** know whether the catalog can complete anything. If no blocked DEV chain can possibly be executed with W-TRANSFER, end transfer efficacy experiments as **coverage-censored**; still run and report W-ROOT reproduction separately as an engineering check.

### G4.4 — One nonlearned swept-volume compatibility safeguard, opt-in

The G3 failure on root `p13_2026216000` chose `o00 -> 60` due to higher learned `p_T`, though that slot obstructed a stored target retreat; historical witness used `o00 -> 59`.

Add **one** lightweight, measured, **nonlearned** compatibility criterion to G3 (e.g. optional policy `D_CAUSAL_G4_SWEEP`):

- For proposed placement `(o,d,m)`, inspect the actual stored original-T **alternative** motion cores and eligible stored connectors under the hypothetical occupancy and the action's exact q_end; estimate how many different T motion options remain potentially usable. Use actual stored sweeps and prefilter evidence, not a fabricated single canonical path.
- **Demote** a placement that clashes with all currently compatible stored target-motion alternatives; **never treat this as a proof of infeasibility** or an unconditional veto. In multi-step problems an intermediate placement may become safe after subsequent moves.
- Preserve a diversity slot or progressive widening so the search can recover from imperfect D probabilities and imperfect prefilter geometry.
- Do not create a new learned head, loss or optimizer. Keep the original G3 policy available as an unmodified control.

Test it on F12 plus at least one contrasting controlled multi-step fixture where immediate target clearance is impossible but a two-move chain is valid. An improvement on F12 alone is an *illustration*, not a statistically meaningful superiority claim.

### G4.5 — Freeze policies and evaluate on exactly the same catalog

Only after a catalog has demonstrably nonzero *blocked-root* execution ceiling, run the five frozen policies:

1. `D_CAUSAL_G3` — original D blocker selection and D counterfactual ranking.
2. `D_CAUSAL_G4_SWEEP` — D with the optional stored-sweep compatibility demotion.
3. `D_BLOCKER_ONLY` — learned mover frontier, geometric placement ranking.
4. `GEOM_CAUSAL` — no learned guidance.
5. `UNIFORM` — deterministic seeded nonlearned control.

**Optional if already implemented and cheap:** `D_CF_ONLY` as sixth ablation, not required.

Use the same candidate source, mover set, destination proposals, catalog, per-action alternatives, global motion-check count, maximum search expansions, beam size and total corrective-action cap across policies. The D-call cap is additional resource accounting, not a substitute for equal physical checks. Budgets must be **global per root across widening stages** (never reset in each stage). Reuse baseline G3 budgets unless preregistered change is needed to reach historically verified 3–4-step examples; then report both original depth-2 and the new depth setting without merging denominators.

Do **not** filter the evaluation cohort to just roots where D succeeds. Preserve all root-level outcomes; report conditional-on-catalog-ceiling results alongside full-cohort rates. Any W-ROOT policy evaluation is **development demonstration only**; W-TRANSFER is the stronger test of library reuse, but still **not** an unseen-to-D evaluation on these historical DEV scenes.

Compute per-root:

- success / complete independent replay; zero/more obstacle relocations; required full target action;
- whether the root is teacher-known-feasible with a repair and whether a known witness is library-realizable;
- first obstacle and first destination ranks; unique obstacle–destination checks; expansion count and accepted relocations;
- model calls and CPU time; actual motion certifications and connector checks; failed-candidate reasons;
- optional redundancy/excess moves **only when a trusted minimal-move reference exists**. Otherwise report raw number of moves.

Compare D vs geometry under **equal physical-search budgets**. If there are too few executable blocked roots, explicitly mark learned repair advantage **INCONCLUSIVE** rather than inventing wins.

### G4.6 — Test and visualization requirements

Keep code minimal and opt-in. Prefer:

- `ad_g4.py` for witness inventory, targeted offline compile driver, diagnostics and matched evaluation (split if necessary; do not create a new package hierarchy).
- Narrow additive functions in existing `ad_compile.py`, `ad_provider.py` or `ad_causal.py` only when needed and fully backward compatible.
- `tests/test_approach_d_g4.py` for focused regression.
- An additive `[g4]` config section in `approach_d.toml` with fixed seeds, compilation cap, catalog modes and policy knobs.

The tests must confirm:

1. Original T and goal remain fixed in every D call; hypothetical q is the exact terminal q from the candidate motion.
2. W-ROOT versus W-TRANSFER provenance cannot mix silently; fixed DEV witness information never influences transfer compilation.
3. All stored actions, entry/exit connectors and object attachment phases replay with exact q continuity, and unconnected poses fail closed.
4. G4's policy and swept-sweep demotion change a concrete candidate ranking but cannot create a physically unrealizable successor or hard-veto a valid two-step intermediate.
5. Search budgets are global over widening and genuinely matched across policies; results are root-grouped.
6. G3/C3 outcomes, P13–P17 historical reports, model weights, `config.toml` and six archived replays remain unaffected.
7. The forbidden-call guard trips on attempted runtime IK, planning or motion generation; normal G4 runtime records **zero** such calls.
8. The historical F12 label remains compatible with its **one-relocation** verified repair; no fabricated 'K2 necessary' claims.

Deliver **four to six clear, actual 2D figures** under `visualizations/approach_d/g4/`:

- `01_coverage_waterfall.png` — archived teacher witness → stored relocation cores → q-compatible connectors → T-core clearance → full replay, separately for C3, W-ROOT and W-TRANSFER;
- `02_witness_replay.png` — original clutter, exact intermediate states, full T movement and final arrangement for a successfully reconstructed chain, if one exists;
- `03_target_sweeps.png` — target-core and connector swept-volume alternatives, with the specific collision causing failure;
- `04_D_counterfactual_vs_sweep.png` — F12 or another authentic example: before/after `p_T`, blocker marginals, candidate destinations and why an appealing edit does or doesn't work with the stored library;
- `05_policy_comparison.png` — root-matched outcomes and motion-check effort, with denominators, and clearly marked inconclusive results when applicable.

Figures must reflect real saved records, not imagined successful experiments. Do not imply W-ROOT plots are transfer results.

### G4.7 — Finish, verify and commit

- Run focused new tests, then **full existing suite + all six archived replays on final code**. If the full suite is impractically long locally, run it and record actual outcome; never mark a gate passed without it.
- Save a single report: `responses-phases/0105_AD_G4_LOCAL_WITNESS_CATALOG_AND_CAUSAL_REPAIR.md`.
- Save a concise `G4_RUN_STATUS.md`: how to reproduce, actual source revision, local catalog paths, hashes, compile ledger, commands, result files and no-server evidence.
- Use `runs/approach_d/g4/{manifest,catalogs,diagnostics,eval,regression}/` (or equivalent minimal existing structure), with checkpointed/resumable records where helpful. Keep large archives out of Git if current repo conventions require.
- Commit coherent tested changes **locally** to `approach-d-v1`. Do not push/merge or launch background remote work.

The final report must include a short table:

| Claim | Evidence | Status |
|---|---|---|
| Original G3 baseline reproduced | saved hashes + comparison | PASS / FAIL |
| Teacher-witness chain reconstructed by stored motions | number of blocked DEV roots with full replay | count and limitations |
| Cross-root motion transfer | W-TRANSFER catalog ceiling on fixed DEV roots | count; no leakage |
| D learned counterfactual value | frozen held-out 214 edit AUC (historical) + any added properly scoped observations | positive / unchanged / inconclusive |
| D versus geometry full repair advantage | matched policy results conditional on catalog availability | supported / negative / inconclusive |
| Runtime solver-free and regressions | guard + tests + replays | PASS / FAIL |

---

## 5. What qualifies as a useful result?

The ideal outcome is several authentic blocked roots that can now be repaired from stored motions, plus a fair matched D versus geometry comparison. **It is not acceptable to cherry-pick successful roots, sneak the teacher's answer into runtime, or certify success using the D probability alone.**

A scientifically useful negative outcome is also possible: even historical witness-guided offline compilation cannot produce reusable, collision-free chains with the current library interface. In that case, provide a crisp, reproducible failure localization and stop. Do not compensate with model retraining or an unbounded compiler search.

### Explicit separation from future dataset work

G4 is **only** about the existing 2D archive and the existing local planar arm. Do not discuss server status, start remote processes, or synchronize with new dataset work. The newer seven-total-action dataset protocol remains a separate future experiment. In this stage use exactly the label/action semantics supported by the local records; use P17's maximum four corrective relocations only where the local witness and search implementation can actually handle them.

**Stop after G4, report the measured outcome, and await the next research decision.**
