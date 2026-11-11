# Approach B X/Y — P9 independent code/report audit and next gate

**Audit date:** 2026-10-31  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Branch/HEAD inspected:** `approach-b-xy-v1` / `68183081dbc1bc722a23e6efeb015454c616c88e`  
**Scientific authority:** `Approach_B_Final_Methodology_2026-10-31.pdf` (13 pages)  
**Repository primary evidence:** `responses-phases/0114_BXY_P9_TEACHER_PILOT.md`, `bxy_teacher.py`, `bxy_pilot.py`, `tests/test_bxy_teacher.py`, committed `SUMMARY.json` and selected individual X query JSON records. Historical supporting reports: `0106–0113`.  
**Audit scope:** source/read-only review of GitHub and supplied methodology; this audit did **not** independently run the server dataset or GPU/CPU physics tests.

## Executive decision

**PASS for the engineering objective of P9; CONDITIONAL READY FOR P-MIN collection.** The pilot has now produced reproducibly described positive X labels and composable matched X/Y witnesses under one versioned, budgeted robot teacher. However, a broad teacher collection should not start until a separate *no-new-collection preregistration and interface-hardening gate* fixes or formally resolves the outstanding F1 eligibility, cost/no-op, V2 loader, label-custody, and query-budget/cost design issues. **No new compute is authorized by this audit.**

## Verified observations and what they establish

- 20 TRAIN roots; 57 distinct attempted X, 59 distinct attempted Y; no censored queries on the frozen worklist; 1,470 aggregate worker CPU-seconds and 803 wall-seconds, versus caps of 3,600 each; max per-root CPU about 171 seconds. The numerical results agree between `0114` and committed `SUMMARY.json`.
- X: 49 positives, 8 operational negatives (3 `CERTIFIED_INFEASIBLE`, 5 `UNKNOWN_PLANNER`); all X=0 cases have length 2–5, while all 23 tested length-1 X queries are positive.
- Y: 29 positives, 30 operational negatives (6 certified, 24 planner-unknown/budget limited). Every observed Y that has a comparable old q_ref label agrees (45/45). This checks policy consistency, not physical impossibility of all Y=0 cases.
- All 49 completed relocation prefixes reached and passed a connector to q_ref: 10 direct, 39 planned. This is **conditional on the 49 prefixes that completed**, not a population-wide guarantee.
- 46 matched X/Y pairs: 23 (1,1), 18 (1,0), 5 (0,1), **0 (0,0)**. Exactly 11 observed X queries lack a matched measured Y in this pilot. `0 not attempted` in the report describes the activated worklist; it does not mean every X has Y supervision.
- 23 joint-success pairs have matched stitched travel labels. Connector is substantial (median 21% of reported total J). `s196` showed two valid orders with same endpoint and markedly different J (about 8.31 and 4.15).
- Seven tested same-endpoint reverse-order pairs; two operationally discordant. `s212` reverse first action returned a checked `ORDER_FIRST_ACTION` certificate; `s047` reverse first action returned `UNKNOWN_PLANNER`, not an impossibility certificate. The latter only establishes a fixed-budget policy difference.
- 17/20 preselected historical complete-success candidates remain full successes under X+connector+Y from q_ref. The three mismatches were the K=None roots with Y failure from q_ref; do not generalize the 85% rate beyond these selected scenes.
- Reported regression: 26/26 tests and 6/6 archived replay gates. The new tests contain stubs, tamper tests, and historical witness fixtures; the actual pilot queries and recertification of their witnesses provide the complementary physical evidence. This is the same geometry/robot model, not an independent dynamics/hardware validation.

## Implemented method audit

**X teacher:** `bxy_teacher.x_query` starts from S0/q0, executes the chosen ordered prefix via `p16_motion.DetPhysics` and `p16_common.best_edge`, carries each achieved q to the next relocation, checks the terminal free-gripper q_ref path by the existing `_transit` function, and requires a separate `replay_x` success. The full edited scene, including target and all obstacles, is retained for the connector. This is consistent with §2.2.1 of the final PDF under the declared **greedy teacher**; it does not exhaust all possible motion realizations.

**Y teacher:** `bxy_teacher.y_query` invokes `bd_2d.t_goal` from the fixed q_ref in the ideally edited scene even if X fails; `replay_y` rechecks the stored target trajectory and placement. Identical endpoints share Y keys; different sequence orders have distinct X keys. Correct in principle.

**Pair/travel:** `bxy_teacher.pair` refuses to fill a missing label, joins X and Y only under matching query identities, and uses `ordered.joint_travel` on concatenated relocation, connector, and target records. That method checks inter-record q and gripper-gap continuity; the individual replays independently recertify collision. The numeric J is *joint-range-normalized L1 motion*, not object displacement or an energy in joules.

**Operational labels:** The final PDF explicitly states that an attempted but budget-exhausted query is zero. The report correctly keeps `UNKNOWN_PLANNER` as metadata rather than calling it global physical infeasibility. Administrative censorship is excluded from learning, rather than mapped to zero.

## Findings to resolve **before** broad collection

### P0 — F1/edited-scene legality is not yet completely enforced

`bxy_teacher.eligible` checks the moved ID, duplicate actions, max length, and membership in `legal_cells`, but it does not check the full terminal endpoint assignment for overlap with other staying/relocated objects, immovable structures and the target, nor all intermediate object-occupancy conditions. `bxy_run.choose` also has no explicit F1 analytic hard screen. The PDF §3/§6.2 requires analytic F1 before candidate scoring. A hypothetical Y query should not silently treat an illegal overlapping edited scene as a legitimate counterfactual. Audit observed pilot candidates for this risk first; implement or reuse a sound F1 static screen at the correct boundary, with eligibility masks/provenance, without retroactively rewriting old labels.

Important: preserve genuinely order-specific **motion** negatives such as `ORDER_FIRST_ACTION`. Do not let a broad F1 shortcut erase legitimate F2 contrasts or filter candidates just because the motion planner timed out. F1 is for sound static legal/illegal endpoints, not uncertain robot motion.

### P0 — No-op travel and model selection are inconsistent

`bxy_run.predict_xy` gives empty candidate `J_hat=0`, and `bxy_run.choose` can therefore undercharge no-op compared with nonempty sequences whose new `J_total` includes the final target. The final PDF defines complete witness travel including target; measured successful Y0 target travel is nonzero (about 1.2–2.6 in P9). Before choosing lambda_J or tuning selection, decide an apples-to-apples objective: either (a) use full complete-action J for every candidate, including the no-op target, with a properly supervised no-op predictor; or (b) pre-register a separate *incremental corrective* travel criterion that excludes target for every candidate and label it as a deviation/secondary metric. The primary protocol should follow the PDF unless formally versioned otherwise. Do not silently force no-op J to zero in one arm while charging target in another.

### P0 — Existing model training code cannot consume the V2 pilot directly

`bxy_core.views()` reads the historical `runs/approach_b/bxy/SIDECAR.json` V1 schema (`x_vars`, `y_vars`, `x_obs`, `y_obs`), and `parse()` expects `X:{root}:{sequence}` / `Y:{root}:{endpoint}` keys. P9 writes an *entirely different* `BXY_SIDECAR_V2_PILOT.json` with `x_queries`, `y_queries`, `paired` and context-hashed `X2/Y2` keys. Calling the current training command would silently continue using the zero-positive V1 training evidence. Build an explicit V2-to-model adapter with canonical identity checking, observed/missing masks, root deduplication, provenance and unit tests. Do not replace or rename old sidecars/checkpoints.

### P1 — Supervision is not balanced for the coupling experiment

No matched (X=0,Y=0) example exists; only five matched (0,1) and none of the length-one X queries fail. Those gaps can allow a model to exploit sequence length, budget-failure prevalence, or historical catalogue roles rather than learn a genuine conditional X/Y interaction. Pre-register fully matched examples spanning all four cells, lengths, K strata, F1-valid X failures, target-negative edits, both orderings, and empty/no-op controls. Do not state that a missing (0,0) cell mathematically invalidates joint NLL; it limits *empirical identification/calibration*, particularly P(X=1 | Y=0), and the coupling ablation.

### P1 — The intended omission and causal-effect evidence is absent

The pilot has four X-only omission records and no decided omission effect. None of its queries establishes nonadditivity. In the next data plan, query Y for every selected prefix/omission in the predeclared bounded catalogue, and preserve an explicit original-vs-omission *matched* outcome comparison; distinguish scene-only effects, physical-execution effects, and full-joint-success effects. Do not infer a causal-necessity claim from object movement IDs or omitted X outcomes alone. Avoid post-outcome selection of explanation cases.

### P1 — Data custody/plan freezing and provenance need strengthening

The previous P7 test was exposed before selection freeze because `bxy_lb.run` computed test predictions during seed training. Keep those 34 scenes as *historically exposed test/dev diagnostics*, not a pristine decisive held-out cohort. A future definitive test needs independently grouped fresh roots and a frozen model, catalogue, threshold, analysis and evaluator before label exposure.

`bxy_pilot.plan()` overwrites the roster/worklist on each invocation. The report declares an earlier worklist was replaced **before** the first pilot query; that disclosure is acceptable for P9, but the next plan should be immutable and committed/hashed before worker launch, with an explicit lock refusing modification once collection begins. A final commit at the end is insufficient evidence of prospective pre-registration on its own.

`bxy_teacher.SOURCES` omits `bxy_data.py` (used for endpoint and key canonicalization), `bxy_pilot.py` (collection design), and several transitive scientific dependencies. Expand the manifest's versioned source/protocol hash set to cover all semantics-relevant code and workload policies. Preserve the original P9 manifest as archived evidence; use a new version for new data, not an in-place mutation.

### P1 — Label and budget instrumentation

Y queries currently report CPU but not the actual `bd_2d.t_goal` budget counters; the budget is enforced internally. Provide read-only/behavior-preserving per-query counters and failure reasons where feasible. Preserve fixed `QB`, query seeds, cache-scope accounting, and X/Y teacher comparability. The P9 teacher's X is the historical *greedy* policy, not existential physical feasibility: describe all zeros as budget-policy failures unless independently certified. For order contrasts, report certificate-vs-timeout separately.

### P2 — Dataset coverage / catalogue definition before any budget request

The phrase **P-min** is currently used for two different potential workloads. Report 0108 defined P-min as about **1,114 complete candidate X queries plus 593 Y endpoint queries on the existing 231 roots**; report 0114 proposes about **150 roots × 8 queries ≈ 1,200 queries**, specifically TRAIN/VAL and contrast-balanced. These are not the same coverage target. The latter leaves some complete candidates and many intermediate prefixes unseen. Name the planned phase precisely (e.g. `PMIN_DEV_MATCHED` followed by `PMIN_FULL_CATALOGUE` and `PREFIX_COMPLETE`) and state exact eligible query counts, deduplication, split/custody rules, and expected missing-label pattern. Estimate CPU using separate measured X and Y distributions, not just an overall average; include headroom for K≥2 and long prefixes.

From P9: roughly 377 CPU-seconds for 57 X (~6.6/query) and 1,078 for 59 Y (~18.3/query); these rates are indicative only and depend strongly on query class. Thus the original 1,114 X + 593 Y P-min shape suggests ~18k worker CPU-seconds before overhead/uncertainty, whereas the uniform 1,707 × 12.7 average suggests ~22k. No resource budget is authorized by this document.

## Recommended next bounded gate: **BXY-P10-PREREG — audit, fixes, coverage plan, and cost model ONLY**

**No physical teacher queries, no network downloads, no retraining, no validation/test result peeking, no 3D.** Tasks and exit criteria:

1. Read actual branch/HEAD and full methodology/report 0114. Preserve the P9 sidecar and all 26 existing tests and archived replays.
2. Write a separate prospective `PMIN_DESIGN.json`/Markdown report naming train/validation/holdout custody, canonical complete candidates and selected prefix/omission Y pairs, F1-eligible masks, four-cell targets and independent order contrasts; pre-compute counts **without running the teacher**. Make targeted root selection based on pre-existing scene/role/config information, not new teacher outcomes, and disclose any intentional historical-label stratification.
3. Implement only the minimal, behavior-preserving F1 legality/admissibility check and provenance (or first provide an audit that current data already satisfy it). Preserve F2 motion-specific negatives. Add counterexamples: occupied stay cell, same endpoint assigned twice, target overlap, unsupported/fixed cell, legal-but-physically-unreachable prefix, and identity after omissions.
4. Add a read-only V2 adapter to the X/Y model data interface; unit test 49 positive X and 8 negative X observations from the **pilot**, correct context keys and shared Y nodes, absence/missing/unknown treatment, and no training leakage. Do not train yet.
5. Fix the selection-time no-op J convention and define a matched travel auxiliary; write tests that include successful no-op Y0, successful nonempty repair, failures with no J, and travel-disabled ablation. Do not tune hyperparameters.
6. Add strict prospective plan freezing and a full semantic provenance manifest. Capture Y budget counters if possible without altering old outcomes; otherwise document the limitation and a deterministic alternative check.
7. Estimate per-query CPU separately for X and Y (including uncertainty and administrative caps), enumerate exact required queries by split/length/K, and propose **a requested, not automatically authorized**, CPU/wall/worker cap for a later collection.
8. Run the new unit tests and archived regressions and generate the no-new-label audit report `0115_BXY_P10_PMIN_PREREG.md`; give `READY_TO_REQUEST_BUDGET` or `BLOCKED` with reasons, commit the audit-only changes, then STOP.

## Suggested Claude Opus 5.5 High kickoff (no compute authorization)

> Inspect current `approach-b-xy-v1` HEAD and all relevant code, report `0114_BXY_P9_TEACHER_PILOT.md`, and `Approach_B_Final_Methodology_2026-10-31.pdf`. Follow this `BXY_P9_AUDIT_AND_NEXT_GATE_2026-10-31.md` as the audit/next-stage contract. Execute **BXY-P10-PREREG only**: freeze a scientifically defensible P-min definition and worklist, reconcile static F1 screening, no-op/complete J cost, and V2 learner-loader semantics, add nonleaking tests and provenance, estimate a separate X/Y resource budget, and produce report `0115`. **Do not collect any new teacher labels, run P-min, retrain, touch frozen test, overwrite P9/historical outputs, or launch 3D.** Stop after the report and code/checkpoint preservation tests; ask for explicit budget authorization only after you give the exact CPU, wall and worker request.

## Evidence links

- Commit: https://github.com/Narendhiranv04/latent-causal-tamp/commit/68183081dbc1bc722a23e6efeb015454c616c88e
- P9 report: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/responses-phases/0114_BXY_P9_TEACHER_PILOT.md
- Teacher: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/bxy_teacher.py
- Pilot: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/bxy_pilot.py
- P9 tests: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/tests/test_bxy_teacher.py
- Existing X/Y loader: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/bxy_core.py
- Selection: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/bxy_run.py
- Original P-min description: https://github.com/Narendhiranv04/latent-causal-tamp/blob/68183081d/responses-phases/0108_BXY_P2_DATA_INTERFACE.md
