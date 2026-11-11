# Independent G1 review and next Claude instruction

**Review date:** 15 October 2026  
**Repository:** https://github.com/Narendhiranv04/latent-causal-tamp  
**Reviewed commit:** `f1651159f7292d0fdfcfb4c7616594fdb88b5ac9`  
**Primary evidence:** submitted `0003_G1_completion.md`, repository `geometry.py`, `motion.py`, `planner.py`, `skill.py`, `tests/test_arm2d.py`, `runs/g1_robot/result.json`, and `runs/g1_robot/manifest.json`.

## Independent assessment

**Decision: G1 acceptable within its stated 2D kinematic scope, with one targeted label-soundness correction and a constrained G2 scene-generation decision before G2.** The repository contains the reported source, run manifests and artifacts at the given commit. The report states 34 passing tests, 64/64 empty-scene full skills, 12/12 corner skills, and replay of 77 trajectories. The resulting source contains sensible 3R FK/IK, separate collision geometry, a continuous interval verifier, phase-labeled joint trajectories, and a seeded RRT-Connect with an interrupted-tree-join regression test. The review did **not** rerun Python tests or inspect raw binary figures/animations, so claims of measured runtime and full visual quality remain report-derived rather than independently reproduced.

### Decisions on Claude's requests

| Request | Decision | Boundary |
|---|---|---|
| Seeded custom RRT-Connect instead of OMPL | **Accept** | Keep joins/edges independently certified, log node/time limits and seed. OMPL global RNG does not mean reproducibility is theoretically impossible in separate processes; the local choice is reasonable. |
| Folded home `[pi/2,pi/2,pi/2]` | **Accept** | Retain its documented G1 collision tests. Never silently change the frozen home during a later family. |
| Connected finger rail and 32-mm tool-to-object offset | **Accept** | The model remains a planar kinematic approximation, not evidence for dynamics or grasp stability. |
| Adjacent-link exclusions and support-contained object | **Accept with explicit scope** | These are disclosed layered-link simplifications and constrained carry semantics, not a physically tested co-planar arm. Robot-object pairs must remain checked. |
| Additional `planner.py`, `skill.py`, `figures.py` | **Accept** | Distinct responsibilities; monitor `scene.py` and `figures.py` size without gratuitous refactoring. |
| Sparse-first, then fill reference clearance cells, then reverify | **Accept only for bootstrap/development, not as the primary dense fixture protocol** | Primary reference actions must be planned and independently verified with all final clutter in place, and the generator must measure actual clutter-induced path structure. |

### Concrete correction A: do not certify numerical IK jump as infeasible

In `skill.py`, `_fail` treats `APPROACH` or `RETREAT` with `v=None` as `IK_TRACK_DISCONTINUOUS` and leaves `certified=True`. In `motion.py`, `ik_track` returns `None` both when an IK branch is missing and when the difference between adjacent sampled joint vectors exceeds the configured `max_ik_jump_rad=0.1`. The latter is an algorithmic discretization/continuation limit, not a sound impossibility proof. Because `_none_left` promotes all `certified` candidate failures to `CERTIFIED_INFEASIBLE`, this can create unsound infeasible labels in future data. Fix these two distinct reasons, ideally by refining the numerical continuation first, then returning `UNRESOLVED` for remaining step/jump uncertainty. A missing exact IK solution at a specified intermediate pose can rule out that **specified** straight-axis branch, but must not prove all possible approach curves or unrestricted task infeasibility. Add a regression that a deliberately restrictive waypoint-jump threshold never yields an unsupported `CERTIFIED_INFEASIBLE`. Recompute G1 tests and replay without overwriting historical G1 artifacts.

### Concrete correction B: dense reference generation in G2

The methodology requires final clutter to shape the nominal 3R motion. A sparse trajectory that is later surrounded by obstacles chosen *because they are outside its envelope* creates selection bias and an artificially protected corridor, even if the final path remains collision-free. It is permitted as a **development bootstrap**, clearly labeled `SPARSE_SEEDED_REFERENCE`, but **not the main T00/high-clutter training protocol**.

Primary G2 construction:
1. Choose the active target, source/goal and a structured clutter layout with 30–40 obstacle IDs already placed; reject immediately invalid support/start poses.
2. Plan a complete 3R grasp/carry/release/retreat/connector in that **final dense snapshot**, using only the existing legal planner and honest `UNRESOLVED` outcomes.
3. Independently certify, record and freeze the **complete** trajectory and phase/contact hash; require a feasible witness before generating failure variants.
4. Measure safe physical candidate cells, density, path curvature, closest clearance and any meaningful path-shaping clutter. If there are insufficient safe supported cells for the desired population, reject or regenerate the root; do not lower the density silently.
5. Induce blocked variants by **relocating existing IDs** into available cells that intersect the frozen complete arm/tool/held-object sweep. Preserve family ancestry and saved one-edit ancestors; do not add new objects, regenerate the nominal motion or confuse multi-edit descendants with matched single-edit twins.
6. Verify direct object-specific collisions with independent geometry, separately from whether a corrective robot motion exists. Start with D1 and D2 development fixtures, then progress toward genuinely feasible dense five-blocker roots; do not force a five-blocker example before having validated reachable constructions.
7. Allow a sparse-seeded candidate as a diagnostic/fallback, but mark it separately and, for a primary benchmark claim, run planning/selection on the final dense scene and report the dependence on clutter; a mere final recheck is insufficient evidence that final clutter influenced path construction.

### Additional reproducibility caution

`planner.py` uses both a seeded RNG and `time.time()` to terminate search. The seed gives a reproducible sample stream, but a wall-time cutoff can end on a different sample under different machine loads. Preserve strict determinism by using the fixed node/evaluation limit as the primary canonical benchmark budget; keep the wall-time limit as a safety cap. Record the actual stopping reason and treat cutoff cases as `UNRESOLVED`. Test reruns under changed worker loads where feasible. No need to redesign the planner merely for this.

## Ready-to-send next Claude prompt: targeted G1 hardening only

Read both authoritative PDFs, the instruction file(s) under `instruction-phase-md/`, and reports `0001`–`0003`. Treat the current G1 code and run artifacts as a preserved baseline. The external review accepted G1 as a **kinematic** foundation but identified a label-soundness issue to correct **before** generating G2 causal data.

**Do a small G1 hardening response only; do not start G2 in this response.**

1. Review `skill._fail`, `skill._none_left` and `motion.ik_track`. Distinguish (a) exact IK nonexistence for a specified pose/branch, (b) definite geometry collision, (c) a discretization/continuation jump beyond `max_ik_jump_rad`, and (d) RRT budget failure. Only (a) under its explicitly declared finite-pose/branch scope and (b) with certified geometry are definite; (c) and (d) are unresolved unless there is a mathematically sound independent certificate. Prefer adaptive refinement if it can be implemented compactly; otherwise propagate a precise `UNRESOLVED` reason. Make the smallest code changes necessary, with targeted regression tests.
2. Rerun all G0/G1 tests and replay the saved 77 G1 trajectories. Do not overwrite the original G1 artifacts or alter their retrospective PASS records. If the new checks change any outcome, log both old and new semantics transparently.
3. Retain the existing tested base/link lengths, folded home, finger rail, grasp offset, 2D link/contact abstractions, `planner.py`, `skill.py` and `figures.py`. The compact custom seeded RRT-Connect is accepted, provided every returned edge remains independently certified.
4. Document the G2 reference-construction rule: final 30–40-object clutter **exists during nominal planning**, the full articulated motion is independently validated before freezing, then existing obstacles are relocated into its frozen sweep. Sparse-first/fill/reverify is a **clearly labeled development bootstrap only**, not the primary research dataset. Do not implement this generator in the hardening response.
5. Note that the wall-clock search limit may prevent exact reproducibility despite deterministic per-query seeds. Record deterministic node/evaluation budgets versus safety timeouts in the planned G2 protocol. Make a minimal logging fix only if needed for label provenance; no planner redesign.
6. Validate the current report's scope: `PLANAR_ARM_KINEMATIC_SKILL`, not actual 3D physics, dynamic execution or hardware verification. Do not turn this into broader physics work.
7. Produce a concise evidence-backed corrective report **`responses-phases/0004_G1_hardening.md`**, including file changes and line counts, exact tests and replay, classification example showing the fix, proof boundary, hashes and G2 readiness. A small diagnostic visual is appropriate if failure classification is easier to understand visually; do not manufacture scenes. Save every substantive answer to a numbered Markdown report as previously agreed.
8. Commit all changed code, tests and the new report; push to the designated GitHub `main` branch; confirm the remote commit. **STOP, and await approval for G2.**

### After that response passes

Next, request **G2 only**, using the final-populated-scene-first rule and compulsory scene-backed before/after, full-arm frozen-sweep, per-object contribution, and independent verifier visuals/GIFs. Begin with D1 then D2 before the high-density five-blocker challenge. Require a complete numbered report and verified GitHub push at its end.
