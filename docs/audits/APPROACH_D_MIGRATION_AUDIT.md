# Approach D v1.0 — migration audit (G0) and G1 scope

**Authority:** `approachD_methodology.pdf`, proposed v1.0 (28 Oct 2026).
**Base:** `main` @ `027fb7f` (P17 closed at `f2149bb`). **Branch:** `approach-d-v1`.

This is an audit of the existing code, not evidence for the proposed pipeline. Only G1 (relative retrieval) is implemented here. G2–G6 are not started.

## 1. Current architecture and exact call paths (2D, P17 production)

### 1.1 D execution (`p17_exec.d_root`)

```
d_root(task, idx=p15_lookup.index_v2()[0], guides)
 └ for guide g:
     phys = p16_motion.DetPhysics(task, idx, budget=D_BUDGET 400/6/16/8, cache)      # shared exact cache, virtual accounting
     mv   = p17_domain.movers(task, cells0)                                         # every movable non-fixed object, nearest TARGET first
     gd   = p17_d.Guide(g, task, phys, mv)                                          # loads 3 Dp17 seeds + own calibration
     p17_search.search(phys, gd.order, mv, p17_domain.slot_fn(phys, idx, width=4), cells0, q0, n_max=4, per_obj=2, node_cap=500)
       └ iterative deepening DFS; at every node: gd.order(cells, q, moved, cands) -> phys.edges(cells, q, o, d) -> recurse
           leaves at depth n: phys.goal(cells, q)                                    # original-target verification (planner)
     p16_motion.replay(phys, plan)                                                   # independent re-certification
```

### 1.2 Where D is called (`p17_d.Guide.order` → `Guide._d`)

| call | target argument | state | used by |
|---|---|---|---|
| `_d(cells, q, "t0", goal, pool)` | **original T** | the node's hypothetical cells **and** the achieved q | every learned guide, `-norec` included |
| `_d(cells, q, o, d, others)` | **obstacle o rebound as a temporary target** | same | recursion only (default guides and `-blk`, not `-norec`) |

Further temporary-target (rebinding) sites outside production search:
- `p17_d.temp_lattice`, `raw_temp_p`, `score_probes` and `_lattice_probes`;
- `p17_data.temp_intermediate`;
- `p15_retarget.build_record` / `retarget_scene`.

These are calibration and label paths. They stay as historical code.

**Finding A1.** The historical `Dp17-norec` arm already queries D only for the original target, at every hypothetical node, with the updated cells and q. The proposed "target-only" rule therefore does not change what D is asked; it removes only the recursion branch. On the P17 prospective cohort, `-norec` arms already solve 71/90 against Dp17's 70 and geometry-norec's 71 (0098). The scientific novelty of G3 must come from *how* the target-only signal allocates compute, not from the re-query alone (§6, G3).

### 1.3 Ordering and search semantics

- **Guide score.** `γ_i = (1 − p_T)·marg_i`, i.e. exactly spec §3.1. Ties break on candidate index, which is movers order (nearest the *target* first) then slot order. The spec asks for nearest the *current end effector*, then estimated travel. That ordering is not implemented anywhere today.
- **Pruning.** None: guides reorder only and never prune. This already satisfies "never permanently discard". There is no top-K / widening rule because there is nothing to widen.
- **Search.** `p17_search.search` is iterative-deepening DFS with travel branch-and-bound and sound dominance on (occupancy, exact q, last mover). Target verification runs on every depth-n leaf, in DFS order.
  - Consequence (0098 §3): under budget, ordering changes only which branch is reached first. This is why learned ordering showed no advantage.
  - The spec's beam / best-first loop (§5.2–5.3) is a different search. It must be added as a new arm, not replace the historical one.

### 1.4 Motion provider and absolute keys

`DetPhysics._edges(cells, q, o, d)` in `p16_motion.py` runs:
1. scoped certificates (ORDER_FIRST_ACTION / STATIC_ENDPOINT_INVALID → CERTIFIED / STATIC_INVALID);
2. `p14_sweep_index.lookup_candidates`, i.e. the pool `idx.by_key[(src, dst)]` (**exact absolute cells**);
3. for each candidate, `motion.certify_trajectory` in the current scene, then a certified transit from q to the witness start (direct, else bounded RRT);
4. on failure, the online planner `skill.plan_skill`;
5. otherwise `UNKNOWN_*`.

Every use of an absolute key:

| site | use |
|---|---|
| `p14_sweep_index.Index.by_key`, `lookup_candidates`, `mode_stats` | index and retrieval |
| `p15_lookup.index_v2`, `transfer`, `mode_stats` | leakage filtering and LORO benchmark |
| `p15_search.Physics._edges`, `p16_motion.DetPhysics._edges`, `p14_d_search` (×2) | motion retrieval |
| `p17_domain.slot_fn` (`lib`), `p16_common`, `p15_bench._slots` | **destination proposal**: up to 2 library-witnessed destinations from the same source |
| `p15_viz.case`, `p17_data`, `p17_mechjobs` | figures, leakage checks |

## 2. Measured library facts (index v2: 4,821 real witnesses after root- and fingerprint-level leakage exclusion)

| quantity | value |
|---|---|
| absolute (src, dst) keys | 277 |
| P15 absolute modes | 1,163 |
| relative families (Δrow, Δcol, footprint) | 62 (31 contain ≥ 2 absolute keys, covering 4,492 witnesses) |
| object footprints / kinds / grasp classes | 1 / 1 / 1 (radius 0.024, obstacle) |
| fraction of each witness's swept cells within Chebyshev 2 of its source or destination | mean 0.60, median 0.56 |
| terminal (elbow, wrist) sign classes | (−,−) 2,667; (−,+) 1,336; (+,−) 464; (+,+) 354 |
| exact certification cost | ≈ 0.24 CPU-s per witness (P15 transfer benchmark) |
| P15 LORO reuse at the same absolute key | top-1 certifies 167/330, any 239/330; 2,603/6,890 failures are the start-q transit |

**Finding A2.** About 40 % of a witness's swept cells are arm sweep away from both endpoints. A translated swept mask is therefore wrong for a fixed-base arm; spec §4.4 is confirmed by the data.

## 3. Mismatches with the methodology, and the smallest defensible resolution

| # | spec | conflict with kinematics or verified behaviour | resolution |
|---|---|---|---|
| C1 | relative key (Δr, Δc, footprint) | Grid translation is **not** a symmetry of the fixed-base 3R arm (base at (−0.14, 0.32), links 0.42 / 0.34 / 0.20, joint limits ±π). Its exact symmetries are **rotation about the base** (a joint-1 offset, carrying the whole motion rigidly) and **reflection** about the base axis y = 0.32 (q → −q). | Keep the spec key for retrieval, since it is what the local patches support. Measure the robot-relative mismatch as the **endpoint residual after the best base rotation** (`base_residual`, 2-point Procrustes about the base). It is 0 iff the query move is an exact rotated copy. In G2 that rotation is the first, kinematically exact adaptation primitive. |
| C2 | modes by swept shape + "compatible terminal robot configuration" | Absolute q_end is not comparable across locations, and absolute swept masks are not either (A2). | A relative mode = same discrete terminal branch (elbow, wrist signs) **and** IoU ≥ 0.6 of the *object-local* sweep (cells within Chebyshev 2 of either endpoint, expressed as offsets from the source). |
| C3 | global occupancy term G | The stored 64-cell occupancy is absolute. Across locations it measures shared absolute clutter (relevant to the arm sweep), not context of the move. | Kept at 0.25 for legacy parity. In the G1 ablation, global-only ranking is the weakest (top-1 72/400 against chance ≈ 65). |
| C4 | "new config keys in existing TOML" | `config.toml` is hash-pinned by archived plans and the six replays (`audit.py`). Editing it would break historical replay. | Overlay `approach_d.toml`, following the precedent of `config_v2.toml`. `p15_lookup.rel_cfg` validates the exact key set. `patches = [3, 4]` is expressed by α3, α4 > 0, so there is no second authority. |
| C5 | target-only D policy | Already true of `Dp17-norec` (A1). | G3 adds the new arm and must differ in compute allocation (best-first by node p_T, D-gated target-verification order, soft top-K + widening, EE-distance ordering), compared against `Dp17-norec` on the same backend. |
| C6 | default shortlist 3 modes × 2 witnesses | On the retrieval proxy, 6 × 1 recovers the held-out pattern more often (LOKO 284 vs 250 of 400) at the same witness budget. | Keep 3 × 2 as specified (an engineering default). Decide in G2 on *physical* certification counts, not on the proxy. |
| C7 | relative retrieval as the motion source | Exact-cell witnesses need no adaptation, yet under legacy weights they get no priority inside a relative shortlist. In LORO, 3.3 of 5.5 returned witnesses are cross-location although exact-cell witnesses exist for 330/442 queries. | G2 provider: tier 0 = legacy exact-cell candidates (certify directly); tier 1 = relative candidates (adapt, then certify); tier 2 = online planner. That is the spec's `allow_absolute_fallback`, ordered by cost. |
| C8 | "library destinations" from the index | `slot_fn` proposes up to 2 library-witnessed destinations per source from absolute keys. Making that relative would change the action domain itself. | Unchanged. All arms keep one shared domain (P17_DOMAIN_V1); relative retrieval affects only how an edge is realised. |

## 4. Minimal file-level changes

| file | G1 (done) | later gates (proposed) |
|---|---|---|
| `p14_sweep_index.py` | appended `REL_VERSION`, `center`, `rel_key`, `descriptor`, `local_sweep`, `branch`, `base_residual`, `rel_view`; the absolute index and `lookup_candidates` are byte-identical | — |
| `p15_lookup.py` | appended `rel_cfg`, `rel_modes`, `RelIndex`, `rel_score`, `lookup_relative`, `lookup_relative_scan`, `retrieve` (switch), `g1_benchmark`, `g1_summary`, `g1_domain_coverage` | — |
| `p15_viz.py` | appended `g1_figures` | — |
| `approach_d.toml` | new overlay, `[relative_lookup]` only | `[approach_d]` keys when G3 first reads them |
| `tests/test_approach_d.py` | new, 11 tests | grows per gate |
| `p16_motion.py` | — | G2: opt-in tiered provider; `UNKNOWN_ADAPT` status; legacy path untouched |
| `relative_motion.py` | — | G2, only if needed: base rotation + task-space residual alignment + closed-form 3R IK with branch continuity |
| `p17_d.py` | — | G3: a new `Dp17-targetonly` guide; `Dp17` and `Dp17-norec` frozen |
| `p17_search.py` | — | G3: an optional best-first / beam entry point with node-level `verify(T)` hooks; the IDDFS untouched |
| `d_blockers.py` | — | no change (two losses, pairless production). G4 only adds same-loss samples if the coverage audit requires it. |

## 5. Relative index schema and retrieval API (G1, implemented)

- **Family key:** `rel_key(src, dst, radius) = (Δrow, Δcol, round(radius, 4))`.
- **Per-entry derived fields** (added in memory by `rel_view`):
  - `_loc`: object-local sweep offsets;
  - `_branch`: the (elbow, wrist) sign class.
  - Stored fields are unchanged: provenance file / index / root / query / seed / split / family, the patches `w3_* / w4_*`, `global`, the swept cells and `q_start / q_end`.
- **Modes:** `rel_modes` is canonical (sorted by travel, file, index) and permutation-invariant. It is precomputed once per family in `RelIndex`: 372 relative modes.
- **Query descriptor:** `sx.descriptor(scene, goal, oid, src, dst)`, the same codes and anchoring as the stored entries.
- **Score:** `R = α3·sim3 + α4·sim4 + αρ·simρ + αG·simG`, with simρ = 1 / (1 + residual / 0.08 m).
  - The defaults (0.5, 0.5, 0, 0.25) reproduce the legacy combined score entry by entry (tested).
- **Shortlist:** `lookup_relative(ri, q, radius, exclude_roots, exclude_abs)`. Modes are ranked by (best score, independent roots, cheapest travel), witnesses by (score, travel, provenance); at most 3 modes × 2 witnesses.
  - Every candidate carries `same_absolute`, `requires_adaptation`, `adapted = False`, `verified = False`, its score components, the base residual and ψ.
  - An empty pool returns `UNKNOWN_NO_WITNESS`.
- **Switch:** `retrieve(ri, …)`. `key = "absolute_src_dst"` returns exactly `sx.lookup_candidates` (tested equal); `"delta_rc_and_footprint"` is relative.
- **Not wired into any physics provider.** A cross-location witness handed to `certify_trajectory` as is would be anchored to the wrong cells; G2 must adapt it first.

## 6. Motion-adaptation requirements (G2 plan, precise)

For a relative candidate witness τ_k (src_k → dst_k) and a query move (src_q → dst_q) at state (S, q):

1. **Exact base rotation.** ψ* = `base_residual(...)[1]`; set q₁(t) ← q₁(t) + ψ* on every waypoint. This is exact for free-space kinematics, and the carried disc and grasp offset (1 class) rotate rigidly with the arm.
   - **Reject** if the rotated record leaves the joint limits. With ±π limits this only requires wrapping, which `motion` must accept or the wrap must be refused.
2. **Residual correction.** If the residual exceeds tolerance (≈ 1e-9 m, i.e. not an exact copy), compute task-space TCP waypoints x(t), θ(t) = FK(q(t)) of the rotated record and shift the source-anchored phases (pregrasp → close_attach) by e_s = src_q − R(ψ*)·src_k and the destination-anchored phases (carry end → retreat) by e_d. Interpolate the carry. Then run closed-form 3R IK per waypoint (2 branches), selecting the branch that matches the witness `_branch` and has minimal joint-space distance to the previous waypoint (continuity). Fail with `UNKNOWN_ADAPT` on any unreachable waypoint or a branch flip.
3. **Record rebuild.** Gap, phase and attached are copied; `place_xy` = centre(dst_q); `held_local` is unchanged. The record must pass `motion.certify_trajectory`'s own consistency check (grasp holds the object where it rests).
4. **Fresh verification.**
   - `motion.certify_trajectory` on the adapted joint path in the current scene, which reconstructs the swept volume from the adapted q (never a translated mask);
   - certified transit from the current q (existing `DetPhysics._transit`);
   - `replay` continuity.
5. **Statuses:** VERIFIED | COLLISION (try the next witness or mode) | UNKNOWN_ADAPT | UNKNOWN_NO_WITNESS | UNKNOWN_BUDGET. Only the existing scoped certificates may produce CERTIFIED_INFEASIBLE.
6. **Tiered provider (C7).** Exact-cell legacy candidates, then adapted relative candidates, then the online planner. Every tier is charged to the same `motion_checks` budget.
7. **G2 gate tests (spec):**
   - (a) cross-location replay of a real relocation adapted from another key, independently replayed;
   - (b) a mid-path link / carry / gripper collision rejected after adaptation;
   - (c) an unreachable adapted waypoint → `UNKNOWN_ADAPT`, never certified;
   - (d) UNKNOWN preserved end to end.
   - Plus: an exact 0-residual rotation reproduces the witness's certification; reflection is **not** used unless gripper symmetry is proven.
8. **G2 physical benchmark:** extend the P15 LORO transfer to LOKO with adaptation (certified count, calls to the first certified witness, adaptation failure reasons, CPU), relative vs exact-cell, at equal motion-check budgets.

## 7. UNKNOWN / negative status handling

- **Existing:** V, CERTIFIED_INFEASIBLE (scoped certificates only), STATIC_INVALID, UNKNOWN_PLANNER / BUDGET / LIBRARY / TRANSIT.
- **G1 adds:** `UNKNOWN_NO_WITNESS` (relative retrieval). `rel_cfg` refuses any `status_on_no_witness` that does not start with `UNKNOWN`.
- **G2 adds:** `UNKNOWN_ADAPT`.
- A ranking threshold or shortlist bound never produces a negative.

## 8. Leakage prevention

- **Index v2:** excludes evaluation-pool roots by root id **and** geometry fingerprint (17 extra entries). Relative retrieval widens *which* entries a query matches but never adds entries.
- **G1 benchmark:** excludes the query root and every root that shares its fingerprint (LORO), and additionally the query's own absolute key (LOKO).
- **Domain coverage:** uses P16 dev / calib / val roots only (never a test split). 0 of 86 share a fingerprint with the index.
- **G4 / G5:** any new cohort must pass the existing root + fingerprint check against the index (`p17_data` `idx_fp`) before sealing. Test-derived intermediate states never enter training, calibration or the index.

## 9. Gates and their tests

| gate | tests (see methodology §8) |
|---|---|
| G0 | full historical suite + 6 replays on the unmodified base (`runs/approach_d/g0_baseline/`) |
| G1 | `tests/test_approach_d.py` (11): same Δ elsewhere retrieves each other / legacy does not; distinct Δ and footprint not mixed; no hit → UNKNOWN; window translation consistency + border padding; descriptor invariant to object ids and equal to stored descriptors; deterministic modes split by branch and local sweep; bounded, flagged shortlist; legacy switch and legacy-weight score equality; indexed = brute-force scan + exclusions; base residual 0 only for exact rotation; config validation with config.toml untouched |
| G2 | §6.7 |
| G3 | zero D calls with target ≠ T (instrumented); ≥ 1 re-query with changed cells / q and the same T; predicted blocker disappearance never declares success; beam backtracks; no hard-threshold false negative |
| G4 | held-out original-target and post-edit target feasibility / calibration; root isolation |
| G5 | frozen prospective roster; paired root-level effects, discordant counts, UNDERPOWERED labelling, 3 seeds |
