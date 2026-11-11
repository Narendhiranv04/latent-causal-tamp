# Independent G1 Hardening Review and G2 Kickoff

**Review target:** `responses-phases/0004_G1_hardening.md`, commit `5e1c311221343db7bafcde60bc39b6bee80dd323`, repository `Narendhiranv04/latent-causal-tamp`, branch `main`.

## Independent review verdict

**Proceed to G2, with a scoped policy adjustment.** I inspected the hardening report and the code committed at the cited revision, particularly `motion.py`, `skill.py`, `geometry.py`, `planner.py`, `scene.py`, the regression tests, and recorded results. The major issue from G1—the promotion of numerical IK discontinuities to certified infeasibility—is corrected through adaptive path refinement and separate definite/unresolved outcomes. Replay now audits joint limits, gripper gap, attachment and placement. Planner budgets expose wall-clock versus node exhaustion. The old G1 reference run is retained. Claude reports 42 passing tests, 77/77 historical replay and no query-status changes; these execution claims have not been independently rerun here.

**Precise outstanding policy mismatch:** `scene.REFERENCE_POLICIES` currently accepts only `FINAL_DENSE_PLANNED/PRIMARY` and `SPARSE_SEEDED_REFERENCE/BOOTSTRAP_ONLY`. The guide mandates G2 development fixtures `D1` and `D2` in genuinely sparse *final development scenes*, with the reference action planned *with all development-scene background objects present*. Those are not necessarily sparse-first-dense-filled bootstraps. Introduce a narrowly scoped third policy, for example `FINAL_DEV_SCENE_PLANNED/DEVELOPMENT_ONLY`, rather than relabeling genuine dev fixtures as dense or bootstrap. Keep dense-primary restrictions unchanged. The exact policy names may be adjusted, but their semantic separation must be enforced and tested.

**Boundary of approval:** 2D layered-link kinematic verification only, finite grasp family, no dynamic/controller/hardware claims, and no unrestricted IK/kinodynamic completeness. A finite-depth numerical joint-limit-crossing diagnosis is scoped to a declared IK branch and straight path; maintain inspectable evidence and conservative unresolved labeling where exactness is not established. No need to redesign the robot or revisit earlier G1 results to start G2.

---

## Copy/paste this prompt into the current Claude Opus 5.5 High Thinking session

Proceed to **G2 only — Frozen Obstruction and Local Causal Effects**, following the authoritative Methodology Specification v1.4 and Implementation Guide v1.6. G1 and its hardening are complete; preserve their verified evidence and the tested robot profile.

Repository: `https://github.com/Narendhiranv04/latent-causal-tamp`  
Branch: `main`  
Current accepted commit: `5e1c311221343db7bafcde60bc39b6bee80dd323`  
Mandatory completion report: `responses-phases/0005_G2_completion.md`

### First, orient yourself

Read both PDFs, the Markdown instructions under `instruction-phase-md/`, the four previous reports `0001`–`0004`, and the actual G1 source and test code. Do not infer G2 semantics from an earlier document version. Explain your minimal G2 plan, file ownership, proposed `D1`/`D2` fixtures and acceptance visuals before coding. Then implement G2; **do not proceed to G3**.

### 1. Resolve one reference-policy classification issue (part of G2)

The current fixture validator accepts `FINAL_DENSE_PLANNED/PRIMARY` or `SPARSE_SEEDED_REFERENCE/BOOTSTRAP_ONLY`. G2's `D1`/`D2` are intentionally simple sparse *development* scenes in which the reference action is planned and independently certified **with their final development-scene background already present**. Add a narrowly scoped `FINAL_DEV_SCENE_PLANNED/DEVELOPMENT_ONLY` (or equivalent unambiguous) policy with validator tests. **Do not** call these sparse scenes 30–40-object dense primary roots. **Do not** treat them as sparse-first-dense-filled bootstraps. Retain the existing strict policy for primary future dense roots.

### 2. Calibrate deterministic planning budgets

The prior 20,000-node cap was unreachable before the 30-second wall cap. Measure actual G2 fixture search costs and choose a justified node/evaluation limit with a generously larger wall-time safety cap, recording node counts, verifier calls, stop reasons, seeds and any wall-cap dependence. The 3,000-node suggestion in report 0004 is provisional, not an obligatory value. Canonical results must not use a wall-clock cut to claim infeasibility or deterministic exhaustion. Preserve original G1 configurations and hashes.

### 3. Build and freeze trustworthy reference actions

Start with `D1` (one blocker), then `D2` (two independent direct blockers). Build simple final sparse reference scenes where every background object is already placed. Plan the **complete 3R home → pregrasp → approach → contact/attachment → carry → release → retreat → home** reference action in each final reference scene, independently replay/certify its entire joint/gripper/object path, and freeze its phase schedule, allowed contact pairs, object geometry, target identity and action hash. Store the unmodified nominal reference scene, original robot profile hash, exact arrays and proof of clearance. If a reference cannot be verified, do not fabricate it or simply downgrade the failure; choose/document another valid development fixture.

Full robot links, housings, palm, rail, fingers, target at rest and carried target belong to the fixed-action collision checks at their respective phases; do **not** simplify the frozen motion to a swept disc or object-only TCP trace.

### 4. Create matched controlled interventions

Use **existing obstacle IDs only**, never clone/create/delete one to fabricate a failure. Relocate exactly one existing obstacle per ancestry edge from a supported legal resting cell into another vacant supported cell intersecting the frozen action sweep. Verify no present-state object intersections and preserve every unrelated field. Preserve stable IDs, root/variant lineage, one-edit ancestry, source/destination physical cell IDs, reference scene hash and the **same frozen target action hash** across the whole family.

Generate a clear reference, a blocked one-edit descendant (`D1`), and an intervention that returns the blocking ID to an admissible nonblocking supported endpoint. At G2 these relocation edits are *privileged diagnostics*, not robot-executed corrective actions; the full corrective robot motion/order verifier is reserved for G3. Prove only that the **unchanged frozen action** becomes geometrically clear again, not that a new corrective pick/place skill was executable.

For `D2`, construct two independent blockers with separate one-edit parent-child snapshots. Show reference success → one-blocker failure → two-blocker failure. Diagnostic correction of just one must remove that object's conflict while overall target action remains blocked by the second; correcting both restores the unchanged action. Save independently checked outcomes for each twin, with the fixed target hash unchanged.

Also test an unrelated one-object edit that leaves the original target action result unchanged.

### 5. Implement honest fixed-action and local attribution oracles

Follow Methodology §§3, 4 and 6. Use the existing exact uninflated primitive geometry and δ=0.005 m once, with ε numeric gray band; never double-inflate. Implement continuous per-entity/per-phase collisions against the **recorded original joint-linear trajectory and recorded gripper/attachment phase state**. Use analytic bounds/adaptive subdivision as in the certified G1 geometry. A sampled collision is definite evidence of a violation; an unproven clear interval remains `UNRESOLVED`. Preserve contact exceptions precisely; distinguish collision with a resting target, carried target, non-target obstacle and support.

Return a per-object local contribution `c_i` with a clearly defined operational meaning (e.g., direct-blocking indicator and minimum signed clearance / violation deficit, plus first offending body/phase/interval). Do not equate the binary whole-action success `F_fixed` with a per-object causal contribution. Distinguish diagnostic *removal* from diagnostic *relocation*. For each intervention `I`, record `d_I=c(S^I,γ0)-c(S,γ0)` and `Δ_I=F_fixed(S^I;γ0)-F_fixed(S;γ0)` without falsely claiming causal identifiability.

Use three-valued validity (`VALID`, `INVALID`, `UNRESOLVED`) with conjunction semantics: definite violation dominates, all definite valid implies valid, otherwise unresolved. Check workspace/support validity and symmetric obstacle–obstacle nonoverlap with physical cell IDs. No learned factor scores or handcrafted energy training targets in G2.

### 6. Required tests and replay evidence

Add `interventions.py` and `tests/test_interventions.py` in the guide's flat repository design; modify existing files only where justified. Test frozen-hash invariance across descendants, stable object count and IDs, exact one-edit ancestry, support/vacancy/occupancy invariants, numeric margin boundary and gray band, phase-specific contact exemptions, blocker detection on actual arm/palm/finger/object sweep, unrelated-edit noninterference, per-ID conflict cancellation even when global success stays 0, and one versus two blocker restoration. Add negative tests that fail if anyone silently replans `γ0`, substitutes the descendant's scene hash into the frozen identity, inserts a new obstacle, counts a privileged diagnostic as an executed repair, or treats gray-band/budget exhaustion as proof.

Re-run all G0/G1 tests and re-certify the archived G1 trajectories after G2 changes. Keep their original run directories untouched. If a fixture is impossible under the selected geometry, describe its construction constraints and mark it unavailable rather than fake data.

### 7. Mandatory visible stage outputs

Create self-explanatory **actual-scene** figures and an intervention sequence GIF in `runs/g2_interventions/` (or the standard guide directory). Every frame must preserve the same axes, IDs, robot base, full articulated robot and physical 8×8 grid. Include:

- `D1`: side-by-side original populated reference, one-object intrusion into the frozen swept corridor, and restored terminal diagnostic; visually highlight the *actual full-body segment* that first collides, not a made-up straight TCP path.
- `D2`: an easy-to-read **reference → blocker A → A+B → remove A → remove B** lineage; print `F_fixed` and separate `c_A`, `c_B` each frame so the viewer sees `F_fixed=0` after A is cleared while B still blocks it.
- A per-ID phase/clearance plot or heatmap pinpointing which robot body and original action phase first conflicts with which obstacle; annotate the numeric signed clearance and status, including gray-band cases.
- A frozen-target trace replay showing the unchanged q/g/attachment trajectory on the different scene snapshots, clearly labeling fixed-action collision and restored fixed-action clearance.

**Do not animate diagnostic teleportation as if a robot physically executed it.** Use clearly labeled snapshot transitions for interventions and separately replay the *recorded* robot action. Explain in plain physical language what each panel proves and does not prove. Save separate clean learner observations (no oracle overlays).

### 8. Code size, report and push

Keep code minimal and modular. Aim for ~120–280 logical lines per ordinary module; review those near 300. Prefer `interventions.py` and existing geometry/viz components, not a large framework or gratuitous nested folders. Maintain one `run.py` entry point and explicit TOML configurations. Do not start matching, assignment optimization, repair-order execution, Gibbs/Boltzmann, neural training, 3D or G3.

Produce the **complete** stage report at `responses-phases/0005_G2_completion.md`: objective, exact math/status definitions, policies, changed files and line counts, fixtures and lineage diagrams, hashes, test commands/results, per-ID attribution metrics, all PNG/GIF/NPZ links relative to the report, scientific limitations, unresolved cases and next-stage readiness.

Commit the code, configs, tests, documentation and reproducible reasonably sized run/visual artifacts, and push to `main`. Verify that the remote SHA matches the local pushed SHA; report the commit and report path in chat. Do not overwrite any existing reports or G1 artifacts.

**STOP — Awaiting my explicit approval before G3.**
