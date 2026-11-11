# 0104 — Approach D G3: causally directed repair search (`D_CAUSAL_G3`)

**Authority:** `approachD_G3_causal_repair_instructions_v1_4.md`.
**Branch:** `approach-d-v1` (local), on `ca33aefc7`.
**Scope:** local workstation; existing P13–P17 2D data; frozen catalog C3 (G2c-lite, predeclared).
**Not done:** no training, no new losses, no D(A) / D(B) queries, no catalog growth, no 442-query benchmark, no push.

## Verdict

- **Engineering: PASS.**
  - D builds and expands a *different bounded candidate frontier* from geometry.
  - Every counterfactual is scored at the stored motion's own end configuration q_end.
  - Accepted chains use only independently replayed stored motions.
  - Runtime solver calls = 0.
  - 11 / 11 G3 tests pass, and the full suite plus the 6 replays pass (§8).
- **Scientific advantage: INCONCLUSIVE for repair success, POSITIVE for counterfactual evaluation.**
  - **Repair success:** every policy, D included, repairs only the directly feasible DEV root (1/12) on the frozen library. This is the catalog ceiling already measured in 0103.
  - **Counterfactual evaluation:** D's re-query of the *original* target on edited scenes predicts which edits make T feasible far better than a non-learned geometric score. On **held-out** P16 calib edits (214 decided), AUROC is 0.949 for D vs 0.781 for geometry vs 0.559 for uniform.

## 1. What changed, and why

**Before (historical `Dp17-norec`).** D reordered the mover list of a conventional search that enumerated every mover × slot anyway, so its effect was mostly "which one first" (0103: 71 = 71 / 90).

**Now (`D_CAUSAL_G3`).** D decides **which obstacles are investigated** and **which placements are worth certifying**:

| role | who | what it does |
|---|---|---|
| learned diagnosis | frozen pairless `Dp17`, **original T and goal only** | p_T(x) and blocker marginals m_i(x) at the current hypothetical occupancy and the robot's exact recorded q |
| mover frontier | **D** | the top-2 movers by m_i enter the frontier (others only through logged widening: top-2 → top-4 → all) |
| destination proposals | **geometry** (non-learned) | scene-only P17 slots that have a stored relocation motion, ranked by the share of stored T-action sweeps covering the slot (evidence, never a veto) |
| counterfactual evaluation | **D** | each candidate (object, destination, stored motion, q_end) is scored by re-querying D for **T** with the object moved and q = **that motion's q_end** |
| physical check | **provider** | certifies **that exact** stored motion and its stored connectors in the current scene; only then does a successor exist |
| success | **provider** | a stored original-T action certifies, and the whole chain replays independently |

D learns no destination, order, trajectory or swept volume. Counterfactual effectiveness is *estimated* by applying its learned original-target predictor to edited scenes. View A tests whether that generalises.

## 2. Algorithm (pseudocode)

```
search(policy, root):                       # one shared budget per root: 60 relocation certifications, 30 expansions, 200 D calls
  for k in widening = [2, 4, all]:          # stage skipped if it would not enlarge the root frontier (logged)
    frontier = [root]
    for depth = 0..max_depth (2):
      for x in frontier:                    # verify-first
        if provider.goal(x) certifies a stored T action: replay chain -> SUCCESS (stage, depth)
      if depth == max_depth: break
      cands = []
      for x in frontier:
        U    = eligible movers x first 4 slots with a stored relocation motion      # identical universe for every policy
        F    = top-k movers by policy score (D marginal | stored-sweep relevance | seeded shuffle)
        for o in F, d in 3 geometric proposals, motion m in 2 stored motions (distinct q_end):
           score(o, d, m) = D(T | x with o->d, q = q_end(m))      # D policies only
        order candidates per mover (D: -p_after, travel; geometry: sweep conflict, travel); interleave movers
        cands += ordered
      frontier = first `beam` (3) candidates whose EXACT stored motion certifies (provider.edges(..., only=m))
  -> FAILURE with reason (NO_VERIFIED_REPAIR | MOTION_CHECK_BUDGET | EXPANSION_BUDGET | D_CALL_BUDGET)
```

**Code footprint:**
- `ad_causal.py`: `DOracle` (t0 only, cache keyed on occupancy, q, target, goal and model hash), `Geo`, `universe`, `search`, `view_a`, `view_b`;
- one additive, backward-compatible change: `ad_provider.edges(..., only=action_id)`;
- `[causal_search]` in `approach_d.toml`;
- figures in `ad_viz.g3_figures`.

## 3. Policies compared (identical roots, universe, catalog C3, budgets, beam, widening, provider)

| policy | mover frontier | placement ranking |
|---|---|---|
| **D_CAUSAL_G3** | D marginals | counterfactual D p_T at q_end |
| GEOM_CAUSAL (main control) | stored T-sweep relevance of the object's cell, then distance | sweep conflict, then travel |
| D_BLOCKER_ONLY | D marginals | geometric (no re-query) |
| D_CF_ONLY | geometric | counterfactual D |
| UNIFORM | seeded shuffle | slot / provider order |

**Historical `Dp17-norec` (archived, solver backend; 71/90) is context only, never plotted with these.**

## 4. View A — causal-selection sanity on saved labelled edits (`VIEW_A_dev.json`, `VIEW_A_calib.json`; figure 03a)

**Protocol.** Labels are P16 scene edits (objects parked at catalogue slots) with the robot at the **original q**. Every score uses that same q, so the comparison is valid. UNKNOWN labels are excluded, never mapped to 0.

**Splits.**
- **DEV:** inside D's training data (`D_TRAIN_SPLITS = train, dev, p17train`).
- **P16 calib:** held out from every D family; this is the honest test.

**"Does this edit make T feasible?" (AUROC of the score against the decided edit label):**

| split | edits (verified / certified) | D (p_T after the edit) | geometry (fewer flagged objects remaining) | uniform |
|---|---|---|---|---|
| DEV (in training) | 28 / 34 | 0.923 | 0.743 | 0.519 |
| **P16 calib (held out)** | 156 / 58 | **0.949** | 0.781 | 0.559 |

**Best single edit.** Among single-object edits, the top-scored one is verified on calib in:

| D | geometry | uniform |
|---|---|---|
| 5/5 | 4/5 | 3/5 |

On DEV it is 2/3, 3/3 and 2/3.

**Mover frontier.** The top-2 hits an object of an inclusion-minimal clearing set in 7/7 cases for **every** scorer, including uniform. That test is uninformative here, because these roots have 2–4 eligible movers and a top-2 almost always contains a blocker.

**Reading.** D's counterfactual re-query of the original target generalises to held-out edits and clearly beats the non-learned geometric score. This is the specific capability G3 relies on, and it is now measured, not assumed.

## 5. View B — end-to-end on the frozen catalog (`VIEW_B_C3.json`; figures 01, 02, 03b-c)

12 P16-labelled DEV roots, zero forbidden calls.

| policy | repaired | new relocation certifications | expansions | D calls | relocations accepted |
|---|---|---|---|---|---|
| D_CAUSAL_G3 | 1/12 | 235 | 55 | 280 | 83 |
| GEOM_CAUSAL | 1/12 | 245 | 52 | 0 | 84 |
| D_BLOCKER_ONLY | 1/12 | 237 | 55 | 39 | 87 |
| D_CF_ONLY | 1/12 | 243 | 52 | 284 | 78 |
| UNIFORM | 1/12 | 254 | 55 | 0 | 87 |

- **The only success** is the directly feasible root `p13_2026210004`, at depth 0, found by verify-first for every policy (so zero relocations).
- **Every other root fails with `NO_VERIFIED_REPAIR`.**
- **The failure is entirely on the target side.** Relocations are realised (78–87 accepted certifications per policy), but **every** original-T check after a relocation fails (61–68 per policy, each exhausting its 6 stored-T checks on collisions and connectors).

**Does D change what is explored?** (D_CAUSAL_G3 vs GEOM_CAUSAL, 11 blocked roots; figure 03b)

| question | roots |
|---|---|
| the root frontier *set* differs (e.g. `p13_2026219000`: D {o00, o02} vs geometry {o01, o02}; figure 02) | 2/11 |
| the first certified candidate differs | 7/11 |
| only ≤ 2 eligible movers, so a top-2 frontier *is* every mover (structural reason for the small set difference) | 5/11 |

On the controlled fixtures (§7) D changes the candidate set decisively. On these sparse DEV roots, the domain leaves little room to.

**Worked example** (`p13_2026216000`, figures 01 and 04).
1. D (t0 only) gives p_T = 0.015 with marginals o00 0.99, o01 0.01, so the frontier is {o00, o01}.
2. Counterfactual scores for moving o00 are 0.78 (→ 60) and 0.64 (→ 59); for moving o01 they are ≤ 0.19.
3. D's top edit, o00 56 → 60, **certifies as a stored relocation**.
4. Afterwards **no stored original-T action certifies**. The first rejection is `link1|o00` in the retreat phase: the new o00 cell lies in that T motion's stored sweep, which the geometric conflict shading flags.

The historical teacher verified o00 → 59 then T. So D's diagnosis is right, the realisable placement is wrong for the *stored* T motions, and the library offers no alternative. That is a motion-library limit, not a learned-diagnosis error.

## 6. What learning changed

| question | evidence | result |
|---|---|---|
| **which** obstacles are investigated | frontier set differs 2/11, first candidate 7/11 (DEV); fixture test | D changes the candidate set where the domain allows; small on sparse DEV roots |
| **where** to move them (counterfactual value) | held-out edit AUROC 0.949 vs 0.781 (geometry) | **positive** |
| **whether** a physically verified repair results | 1/12 for every policy (C3) | **inconclusive**: catalog ceiling |
| search **effort** | relocation certifications 235 (D) vs 245 (geometry) vs 254 (uniform); D adds 280 forward passes (≈ 0.03 s each) | no meaningful difference |

## 7. Tests (`tests/test_approach_d_g3.py`, 11 / 11)

Deterministic fixtures (fake provider, D and geometry, so each test isolates one claim):
1. D marginals change the **candidate set**, not just the order: D explores {o3, o4}, geometry {o1, o2}; D repairs where geometry fails without widening.
2. The counterfactual p_T changes the chosen placement (`D_BLOCKER_ONLY` picks the geometric slot instead).
3. Each candidate is scored at **its own stored q_end** (two motions for one (o, d) → two distinct D inputs); T never moves.
4. A two-step repair is found although no single move raises p_T.
5. Widening (2 → all) recovers a wrong D shortlist within the same budget caps; the narrow run fails.
6. The shared budget is enforced (`MOTION_CHECK_BUDGET`).
7. Sweep conflict ranks but never vetoes.
8. A failed stored motion never becomes a successor.
9. `DOracle` refuses temporary targets.

Real data:

10. Real DEV root: zero forbidden calls, verified depth-0 success with replay.
11. Saved View A / View B consistency; `config.toml`, P17 results, P16 plans, `p17_d.py` and `p16_motion.py` are unchanged.

## 8. Regression

Full suite + 6 archived replays (`runs/approach_d/g3/regression/`): **554 passed, 0 failed** (513 historical + 41 Approach D), all 6 replays clean, `P3A_REGRESSION_CLOSED` (769 s). Approach D tests: 52 / 52.

## 9. Limitations

- **Small DEV pilot.** 12 roots with 2–4 movers each; the D-vs-geometry frontier contrast is structurally limited.
- **View A** uses historical parking edits at the original q, not the G3 candidates' q_end. It validates D's counterfactual re-query, not the full G3 ranking.
- **Default knobs, not tuned.** The configuration (top-2, 3 slots, beam 3, depth 2) is the predeclared default.
- **Frozen catalog.** C3 is predeclared; the dev-informed C4 was not used.
- **Geometry only.** Certification is geometric; there is no hardware or simulator execution.

## 10. Next stage

1. **Re-run `view_b` on the motion library built from the server dataset's offline teacher witnesses.** It needs many stored T motions per state and stored connectors that avoid near-base sweeps. Only with that library can D's held-out counterfactual advantage (§4) become, or fail to become, a repair-success advantage.
2. **Add one cheap, non-learned guard:** demote D's top placement when it falls in the sweep of every stored T motion (the failure in §5). Compare it as a separate, predeclared ablation.
3. **Keep D's training unchanged** (BCE + blocker NLL, original target only).
