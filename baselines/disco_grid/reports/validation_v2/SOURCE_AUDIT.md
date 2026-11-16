# V0 source audit (supersedes claims, preserves archives)

Source: fetched `origin/naren/disco-grid-baseline` at full SHA
`b4414510cbc79c5198e8f6a0d14cdee33283504a`. No remote delta.
Validation branch: `naren/disco-grid-validation`, separate worktree. Original worktree
contains user changes; none reset or discarded. Historical tracked bytes are hashed
in `manifest.json`. No Approach B branch or teacher edited.

Read: complete user handoff; original `instruction-phase-md/DISCO_plan.md`;
committed DISCO README/config, data/env/policy/MCTS/distillation/evaluation code,
D0–D8 reports and machine-readable summaries; Approach B V3 plan and V3.1 report.
Upstream deployed reference HEAD independently read on gvlab:
`c62b32e5f6e40444459742525a86ffef620951aa`.
Approach B branches are distinct: V3 `ede29034b2`, V3.1 `c1717ca03b`.
Current V3.1 verification is live on gvlab; its results are not interchangeable with V3.

| Claim | Execution / artifact | Finding / required action |
|---|---|---|
| q_t input to historical networks | policy.extract_query_features/extract_scene_object_tokens; env.observe default False | False. Physical state carries q; learned O0 omits intermediate q and gripper. Version O1 separately; forbid O1 open-loop. |
| PUCT, alpha .5 | mcts.MCTSNode.ucb_score/widening_condition | UCB C=1.5, k=2, alpha=.3, batch expansion. Correct prose, preserve algorithm. |
| 25 iterations, B16 actually used | config vs distill.run_d3_d4_d5_pipeline | Pilot 2D 8/B4/cap14, 3D 5/B3/cap8. Call cap can overshoot at unguarded STOP. |
| Exact crash resume | save_tree stores nodes only, worker skips existing dirs | Missing RNG/config/counters and atomic generation. Fix; legacy snapshots remain analysis-only. |
| All feasible policy edges | distill.extract_distillation_data_from_tree | Correct, successful-only filters policy only; same value rows. |
| STOP value labels | same | Both decided signs present; repeated cached successful STOP visits inflate evidence weights. Count unique physical checks. |
| Value is whole-plan success probability | policy.DiscoValueNet | Action-conditioned continuation fraction under sampled visited descendant leaves; exploration biased. |
| O0 feedback equality establishes O1 result | env.observe, closed-loop call sites | O0 still q blind; parity is expected for identical structural cells and seeds; no proprioceptive result. |
| Independent test n=135/54 | d6 summary per prediction | 75/30 distinct overall roots, 45/18 task roots × 3 initializations. Bootstrap roots. |
| 48 parity roots | d1_parity_audit.json | 48 queries over 24 roots (32 2D + 16 3D queries). New replay pending resources. |
| Fair Approach B win | old final report | Cohorts unequal; unpaired exploratory aggregates only. No causal factor attribution. |
| Checkpoint filenames/checksum prefixes | final report vs deployed runs | Prose registry untrusted; measure deployed bytes in artifact inventory. |

Physical semantics from code: 2D carried `(cells,q,used,records)`, no intermediate
connector; 3D exact MuJoCo payload and IK cache restored before each branch.
STOP connects to q_ref; Y uses separate canonical endpoint, not executed subcell poses.
Model proposal uses neither teacher nor Approach B weights. Grammar retains K≤3,
non-target movable once, root-original-empty destinations, no reuse/swaps.
Actual teacher configuration recheck and regression logs will be appended as evidence.

Execution gate: no new physical collection or GPU training while both gvlab GPUs
and the ongoing 9+7 Approach B verification workers are busy. Lightweight tests
may use one nice CPU thread. Other three hosts: authenticated read-only inventory,
zero DISCO execution authorization. See HOST_INVENTORY.md / host_inventory.json.

Validation completion addendum (17 November 2026 IST): original lightweight
suite 10/10, final suite 35/35 on gvlab; archived primary predictions replayed
315/315 exactly and fresh 2D/3D physical order parity 4/4. Teacher sources are
hashed in teacher_sources.json (15 possible 2D imports, 7 authoritative 3D files).
The actual 3D wrapper selects `confined` and applies SHELF66 scene overrides:
6×6, pitch .075, floor .55, azimuth step22.5 degrees, level side grasps with
middle/top heights. Base module defaults are not the resolved shelf settings.
Native mesh/library hashes were not exhaustively re-audited.

Additional verified issues and fixes: repeated cached STOP visits inflated
positive evidence; wrapped minibatch slices could omit/empty batches; NOOP
unknowns were missing from task censoring; closed-loop unresolved steps were
coerced to X=0; seed/root pairing silently intersected cohorts; early 3D wall
alarms could be replaced by the teacher. These corrections and remaining gates
are documented in Q_STATE_AND_MCTS_AUDIT.md and FINAL_DECISION.md. Historical
reports/data labels/checkpoints remain unchanged; any prospective administrative
censoring revision must be common to both methods before paired evaluation.
