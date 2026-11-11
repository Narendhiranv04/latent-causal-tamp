# Independent G2 Review and G3 Implementation Handoff

**Reviewed:** `responses-phases/0005_G2_completion.md` and repository `Narendhiranv04/latent-causal-tamp` commit `9d3d7c88274fb3e473e485f38186a419466568c0` on `main`.

**Authority:** `latent_causal_tamp_specification_v1_4.pdf`, `latent_causal_tamp_implementation_guide_v1_6.pdf`, especially Guide §4, §5 G3, §7 and the specification's terminal matching / executable repair sections.

## Independent assessment

**Decision: approve G2 and begin G3, maintaining its scientific scope.** I inspected the uploaded G2 report, committed code in `interventions.py`, `motion.py`, `config.py`, the new tests, fixture definitions and recorded result JSON. The commit and visual artifact filenames are present. I did **not** independently execute the user's G2 Python tests or inspect the binary figures/GIFs pixel-by-pixel; execution and visual inspection claims remain Claude's reported evidence.

Supported by the code/report:
- `FrozenAction` hashes the original recorded joint/gripper/contact trajectory and reference scene; changing the trajectory is detected.
- `object_check` tests original articulated robot-body motion plus the target at rest/carried/placed, with three-valued clearance labels; the `whole_scene_replay` cross-check aggregates all objects using the same underlying collision engine (independent aggregation, **not** independent collision physics).
- `apply_edit`/`audit_edit` preserve object identity and prohibit claiming a diagnostic edit as robot-executed.
- D1 one-blocker and D2 two-blocker lineages are development-only; the partial D2 correction clears one object's conflict but not overall target failure.
- The finite-grasp and 2D kinematic evidence boundaries remain explicit. There is not yet any evidence of physically executable corrective moves or exact repair minima.

**No G2 redesign needed.** The G2 result is an adequate foundation for G3. Preserve original evidence and annotations. Any unexpected source/fixture issue discovered in G3 should be documented; do not silently refactor a validated stage.

## Resolve Claude's two questions

1. **D1/D2:** reuse their actual G2 blocked variants for early G3 verification, including positive tests and transparent failure/unresolved outcomes. Their diagnostic correction endpoints may not admit actual robot movements; do not force success. Add a **new D3** development fixture containing a real order/access dependency and independently tested alternative endpoints. D3's claim must come from actual full-arm paths, not from a hand-drawn order graph.
2. **Density:** do not skip the development gates. G3 introduces strong analytic A0 and move-once verification and must implement the specified restricted-domain T07/control regression. Distinguish a small *development proxy* from genuinely dense 30–40-obstacle `T07`; never label the former as dense T07. Construct any G3 dense control with the **final dense background present when the nominal γ0 is planned**. The main `T00` dense reference bank, 20 audited roots, 300-root pilot and optional 1000-root expansion belong to G4, **not** G3. If mandatory G3 T07 construction is unavailable under the robot geometry, record `CONSTRUCTION_UNAVAILABLE` and report the unmet gate rather than inventing a dense result.

## Copy/paste the following into Claude Opus 5.5 High Thinking

Proceed with **G3 ONLY — analytic terminal matching (A0), alternate endpoint assignments and full executable move-once repair verification**.

Repository: `https://github.com/Narendhiranv04/latent-causal-tamp`  
Branch: `main`  
Accepted G2 commit: `9d3d7c88274fb3e473e485f38186a419466568c0`  
Mandatory full report: `responses-phases/0006_G3_completion.md`

I have added this document to `instruction-phase-md/`. **Read the entire document first**, then the two authoritative PDFs, the other instruction files, reports `0001`–`0005`, and the existing code/tests/artifacts. Explain your exact fixture/solver/visualization plan before implementation. Do not invent a new G-stage registry or skip acceptance gates.

### 1. Scientific question and boundaries

G2 proved that privileged relocation of blocker A/B can clear the *frozen original action*. G3 must now answer a different question: **Can the real articulated planar robot execute an ordered sequence of relocation skills, starting from the actual blocked state, such that it can reconnect to the original action start and replay the exact same frozen target trajectory? What can be proved about minimal number of moved objects?**

Distinguish without exception:
- `TERMINAL_VALID`: all objects at legal, supported, mutually compatible endpoints and the original γ0 would be clear there;
- `EXECUTABLE_VERIFIED`: an actual move-once sequence with all 3R links, housings, palm, rail, fingers, gripper contact, attachment, obstacles, intermediate states, connecting paths and unchanged γ0 replay independently certified;
- `UNRESOLVED`: finite motion/order/assignment search exhausted without a complete witness or a sound impossibility certificate;
- `CERTIFIED_TERMINAL_INFEASIBLE`: a valid finite-domain matching/Hall or complete terminal-oracle proof;
- proof bounds `LB` and verified `UB` separately, with `MINIMUM_CERTIFIED` only when justified.

No IK timeout, limited sampling, failed RRT or unsuccessful single assignment may be called proof that a repair is impossible.

### 2. A0 — rigorous terminal assignment baseline

Create `solve.py` and `tests/test_matching.py` as in the guide. Use SciPy linear assignment/min-cost flow or an equivalently tested deterministic solver. Record the selected dependency version. Avoid brute-force enumeration over the full 35-object grid.

- Include **all present obstacles**, not only direct blockers, in the assignment domain, so auxiliary nonblocker moves are possible.
- Physical cell IDs must remain global and stable; per-object candidate index 0 means its **current** cell, not physical cell 0. Never conflate these indices.
- Use the exact declared candidate domain (all-supported or explicitly restricted), each object's frozen-action compatibility `y^a`, support `y^w`, one-to-one occupancy and any required pairwise constraints. Never double-inflate geometry.
- Stay has cost 0; relocation has cost 1; minimization is over **distinct moved IDs at terminal time**.
- For identical discs and the uniform nonoverlapping grid, justify why terminal compatibility reduces to bipartite matching. If different-size/general pair constraints invalidate that reduction, use an appropriate explicit constraint solver rather than pretending matching is exact.
- Return a deterministic first optimum and **k-best distinct complete assignments** via correct no-good exclusion / k-best methodology, not merely different object orders for the same assignment. Deduplicate and log assignment costs and physical destinations.
- Independently audit the small-case optimizer by **complete finite enumeration** and the original terminal oracle, including multiple equally optimal solutions, repeated destinations, stay options, impossible domains and action-blocked source poses.
- Do not leak information from known intervention histories into the baseline's selection rules. Oracle geometry and declared legal domains are permitted equally for A0 and later methods, but intervention-provided teacher answers are not privileged to A0.

**Mandatory restoration theorem regression:** for an appropriate all-supported, identical-cylinder reference-to-failure family, show that moving every current direct blocker to its *original reference cell* yields a valid terminal state and A0's terminal optimum is **exactly `|D|`**. Explain both inequalities: each direct blocker must leave its blocking pose; original reference cells provide a witness for `|D|` moves. A reference-to-failure example for which these premises do not hold cannot be used to claim the theorem.

### 3. Actual ordered move-once verifier

Create `verify.py`, `tests/test_verify.py`. Reuse existing `geometry.py`, `motion.py`, `planner.py`, `skill.py`, `interventions.py`, `viz.py` and figures where appropriate; avoid duplicated collision physics and a second robot class. Add only small, responsibility-focused functions and files.

A repair candidate consists of **real object IDs, their target physical cells and an order**. It is NOT a set of privileged `apply_edit` transitions.

For each relocation:
1. Begin from the actual current scene **and actual current arm/gripper/attachment state**. Do not secretly reset robot q to G1 home between moves. A return-to-home is permitted only if the connecting trajectory is actually found, executed in the recorded path and independently certified.
2. Plan a complete 3R approach, grasp, attach, fixed-plane carry, release and retreat, collision-checking all bodies and the carried object against the actual other objects and support.
3. Update the achieved pose/state and ID-specific `moved_history` after a **verified** relocation; a moved object becomes stay-only at its **achieved** pose for the rest of this episode. Reject second moves of that ID.
4. Re-observe/re-evaluate the current scene for verification if needed, but preserve frozen action identity, root, episode, history and total move budget. No object teleportation.
5. Upon completion, certify the terminal state, the **connector from the achieved robot state to the exact pinned `γ0` initial configuration**, and independent replay of the *unchanged original γ0* against the final achieved scene. Do not replan a replacement target action.
6. Preserve failed/unresolved move attempts and the first offending pair/phase, including the robot state and budget that caused them.

Build search over **both alternative endpoint assignments and alternative legal move orders**. Keep a finite, explicitly logged call/node/assignment budget, reusable across methods. Do not mistake one failed order for general impossibility. State can be memoized with actual poses, q/g/attachment, moved history, remaining budget, target hash and robot/contact profile; stochastic `UNRESOLVED` results must never be cached as definitive impossibility.

### 4. Fixtures, execution order and proof controls

Start with real stored G2 D1 and D2 blocked states, using their exact frozen hashes and physical-cell IDs. Report if the diagnostic `clear` endpoints are *not* robot-executable and try legitimate alternative destinations. Do not alter archived G2 records to make success convenient.

Then construct a **new D3 development fixture** with actual order/access dependence. Show at least two plausible assignments or orders where the full-body robot changes the outcome. Demonstrate with real replay—not an abstract precedence graph. If neither a sound impossibility proof nor verified complete witness exists, report `UNRESOLVED` and show where verification stopped. Try small or sparse fixtures first rather than force a five-blocker dense scene prematurely.

Add an explicit, **paired restricted-domain terminal-infeasibility control** per guide T07/F8: the same underlying geometry and frozen γ0 under (i) an enumerated restricted per-object destination domain and (ii) the `ALL_SUPPORTED` domain. For the restricted side produce a **finite and checkable Hall violating subset or complete candidate-assignment exhaustion certificate**; for all-supported show the original reference restoration witness and the correct matching cardinality. If this is a small developmental proxy, identify it as such. A fixture called the dense `T07` must have the required 30–40-object, action-first-planned final populated reference, otherwise do not claim the dense T07 benchmark is done. Do not call a robot-motion inaccessible cell terminal-invalid.

Test a case where moving an occupied preferred destination's current owner may change order/access/executable move needs **without** changing the unrestricted terminal lower bound. Do not claim a six-terminal-move necessity when the reference restoration argument still supplies a five-move terminal solution.

If a scoped 5-direct-blocker fixture has an executable 5-move witness, the lower bound + witness prove optimum exactly 5. If a 6-move witness is found but no complete 5-move nonexistence certificate, report `LB=5, UB=6, MINIMUM_UNRESOLVED`. Do not fabricate a 6-move-optimality claim. Log `CONSTRUCTION_UNAVAILABLE` for required fixtures that cannot honestly be made.

### 5. Non-negotiable visualizations: understand G3 physically

Save the actual generated artifacts under `runs/g3_repairs/` (or the guide's declared name), with readable full-grid axes, stable IDs and status legend. Mandatory visual outputs:

**A. A0 matching board:** a physical 8×8 scene showing every source object, proposed destination, stay/move assignments, and frozen target action envelope; distinguish action-safe candidates from blocked cells. Include cost and the exact set of moved IDs. If a large matching diagram is unreadable, also show a focused direct-blocker candidate table.

**B. Actual D1 robot repair GIF:** from the *G2 blocked scene*, show each real full articulated grasp/carry/release/retreat skill, resulting achieved state, arm connector to γ0 initial q, then the **original frozen full robot target action replayed successfully**. Label `VERIFIED` or the honest failure, not a pictorial teleportation.

**C. D2 paired alternatives and stepwise status:** show both blocker conflicts, which object the robot is attempting next, the real path and first offending collision if rejected, achieved scenes, cumulative moved-history, terminal oracle and target replay. Explain why fixing A diagnostically does not by itself prove executable A-then-B repair.

**D. D3 order/access comparison:** side-by-side actual attempts with different orders/endpoints, including any collision/IK/connector rejection. Use animations of stored robot paths, not invented interpolation. Explicitly separate `TERMINAL_VALID` from `EXECUTABLE_VERIFIED` and `UNRESOLVED`.

**E. Restricted vs all-supported T07/control visualization:** same physical scene, two distinct domain overlays, marked Hall subset / unavailable eligible cells and the all-supported restoration witness; include matching costs and evidence scope.

**F. Verification summary:** per-candidate terminal cost vs actual motion/order outcome, first valid assignment rank, actual moves, lower and upper bounds, verification calls and stop reasons. Show actual executed robot links and fingers at keyframes and the original target action hash unchanged.

When a required successful animation is impossible due to a genuine blocked fixture, give a **truthful failure animation** and include a separate feasible demonstration fixture; do not fake a completion. The figures must be understandable without opening code. GIFs for moving robots replay stored q/g/attachment segments only; include optional phase/clearance plots as helpful.

### 6. Tests, experiment fairness and stages

Add negative and positive tests for:
- Matching vs exhaustive finite oracle; equal-cost k-best/no-good uniqueness; all-object inclusion; source/candidate physical-ID mapping; restricted-domain impossibility proof and all-supported paired control; present-state support and pair constraints.
- Restoration-to-reference = `|D|` under exactly stated assumptions.
- One actual full-arm relocation and two-relocation sequences; order sensitivity; alternate endpoints; moved-ID history (no twice-move), actual robot state continuity, no skipped/unverified connectors, no target replanning, exact frozen action identity and independent whole-trajectory replay.
- Clear separation of `CERTIFIED_TERMINAL_INFEASIBLE`, `EXECUTABLE_VERIFIED`, `CERTIFIED` scoped path blockage and `UNRESOLVED` motion/budget.
- Sound LB/UB accounting and no false minimum claims after a finite failed search.
- Deterministic seeds/nodes/verifier calls; wall-clock cap remains a safety constraint only, and cannot justify infeasibility.

Rerun all G0–G2 tests, preserve archival runs `runs/g0_scene`, `runs/g1_robot`, `runs/g1_hardening`, `runs/g2_interventions`, and replay the frozen G2 actions. Preserve the tested robot-profile hash. Do not invent outcomes or prelabel D3/T07 as successful.

**G3 only:** No Gibbs/Boltzmann inference, neural features, joint learning, dataset-scale generation, 3D cupboard, T00 expansion or G4 implementation. If dense T07 itself is infeasible to construct under current geometry, report the missing gate for approval rather than moving silently to G4.

### 7. Code hygiene, report and synchronization

Use the existing flat repository. Aim for ~120–280 logical lines per ordinary module and review any module near 300; modularize by real responsibility only. Keep a single entry point `run.py`. Prefer small changes to G1/G2 skills to allow actual-state start/finish rather than duplicating them. Expose necessary configuration through TOML and version any new solver dependency.

Write a comprehensive self-contained report to `responses-phases/0006_G3_completion.md` containing the actual mathematical formulation, solver assumptions, k-best enumeration and exactness scope, all development/paired control results, actual robot-path verification status, real moved-ID history, LB/UB proof evidence, tests, timing/call budgets, figures/GIFs with relative links, changed files with line counts, config/robot/target hashes, limitations and explicit failed/unavailable fixtures. Include enough detail for independent review from this file alone.

Commit all pertinent source, configs, tests, reports and reproducible artifacts and **push to `main`** after writing the report. Verify local/remote HEAD equality. Do not rewrite earlier reports. Return the new commit SHA and report path in chat.

**STOP — Await explicit approval before G4.**
