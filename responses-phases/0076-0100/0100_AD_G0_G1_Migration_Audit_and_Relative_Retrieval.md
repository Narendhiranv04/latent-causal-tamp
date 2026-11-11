# 0100 — Approach D v1.0: G0 migration audit and G1 relative-motion retrieval

**Previous turn sync:** `main` @ `027fb7f` (PoC-takeaway refresh after P17, pushed). Branch `naren/PoC` @ `3a7062f` in `rss-ebm-infeasibility`.

**Authority:** `approachD_methodology.pdf` (proposed v1.0, 28 Oct 2026). Only G0 (audit) and G1 (relative retrieval) are done. G2–G6 are not started: no motion adaptation, no D training change, no target-only runtime policy, no expensive evaluation.

**Branch:** `approach-d-v1`, created from `027fb7f`. The work is committed locally and **not pushed** (per instruction).

## Actual result

- **G0 baseline:** **PASS**: unmodified `027fb7f`, **502 passed / 0 failed**, all 6 historical replays CLEAR (`P3A_REGRESSION_CLOSED`, 808 CPU-s; [`../runs/approach_d/g0_baseline/`](../runs/approach_d/g0_baseline/)). Tests were collected about 190 s before the first G1 edit, which was additive in any case.
- **G1:** **PASS (retrieval scope only).**
  - **Tests:** 11 / 11 new tests.
  - **Index equality:** indexed retrieval = brute-force scan on 884 / 884 held-out queries.
  - **Real held-out witnesses** (root- and fingerprint-disjoint), new absolute location (LOKO):
    - the relative index offers candidates for **400 / 442** queries; the legacy exact-cell lookup offers **0**;
    - the top-1 relative witness has the held-out witness's motion pattern in **149 / 400** queries (chance 0.163 ≈ 65), and the ≤ 6 shortlist has it in **250 / 400**.
  - **Candidate coverage** on 86 development roots: 548 / 1,032 moves (53 %) absolute → 963 / 1,032 (93 %) relative.
  - **Scope of these numbers:** no motion was adapted or certified. They are **retrieval** results, not physical transfer. Cross-location witnesses are flagged `requires_adaptation`, and none is reachable from any physics provider yet.
- **Post-change regression:** **513 passed / 0 failed** (502 + 11 new), 6 replays CLEAR (`P3A_REGRESSION_CLOSED`; [`../runs/approach_d/g1/regression/`](../runs/approach_d/g1/regression/)).

## 1. Audit summary (full document: [`../APPROACH_D_MIGRATION_AUDIT.md`](../APPROACH_D_MIGRATION_AUDIT.md))

- **D is already re-queried for the original target at every hypothetical node.** `p17_d.Guide._d(cells, q, "t0", …)` runs with the node's cells and achieved q. Rebinding an obstacle as a temporary target happens only in the recursion branch, which `-norec` disables. So `Dp17-norec` already satisfies the spec's target-only D-call rule (0098: 71/90). G3's new arm must change how D's signal allocates compute — best-first / beam by node p_T, D-ordered target verification, soft top-K with widening, end-effector-distance ordering — or it will reproduce the P17 null.
- **Motion lookup is keyed by exact absolute (src, dst)** at every call site listed in audit §1.4, including destination proposal in `p17_domain.slot_fn`. That use stays unchanged so every arm keeps one shared action domain.
- **The kinematic conflict (C1).** The 3R arm's base is at (−0.14, 0.32) m with joint limits ±π, so grid translation is not one of its symmetries. Its exact symmetries are rotation about the base (a joint-1 offset) and reflection about y = 0.32.
  - About 40 % of each witness's swept cells lie more than 2 cells from both endpoints (arm sweep), so translated masks or joint paths are invalid.
  - G1 keeps the spec's (Δrow, Δcol, footprint) key for retrieval and adds the **endpoint residual after the best base rotation** as the robot-relative descriptor. G2 uses that rotation as its first, exact adaptation step.
- **Other conflicts and their minimal fixes:**
  - C2: modes use the terminal branch plus the object-local sweep instead of absolute q_end.
  - C3: the global term is absolute clutter; the weakest ranking.
  - C4: `config.toml` is hash-pinned by the replays, so knobs live in the new overlay `approach_d.toml`.
  - C6: a 6 × 1 shortlist outperforms 3 × 2 on the proxy; the decision is deferred to G2 physics.
  - C7: G2 should try exact-cell witnesses before relative ones.
  - C8: the domain is left unchanged.

## 2. Files changed (all additive; historical functions byte-identical)

| file | change |
|---|---|
| `p14_sweep_index.py` | + `REL_VERSION`, `center`, `rel_key`, `descriptor`, `local_sweep`, `branch`, `base_residual`, `rel_view` (56 lines) |
| `p15_lookup.py` | + `rel_cfg`, `rel_modes`, `RelIndex`, `rel_score`, `lookup_relative`, `lookup_relative_scan`, `retrieve` (switch), `g1_benchmark`, `g1_summary`, `g1_domain_coverage`, `g1_gate` |
| `p15_viz.py` | + `g1_figures` |
| `approach_d.toml` | new overlay, `[relative_lookup]` (validated exact key set) |
| `tests/test_approach_d.py` | new, 11 tests |
| `APPROACH_D_MIGRATION_AUDIT.md` | the audit |
| `runs/approach_d/g0_baseline/`, `runs/approach_d/g1/`, `visualizations/approach_d/g1/` | evidence |

Not touched: `config.toml`, `d_blockers.py`, `p16_motion.py`, `p17_*.py`, every checkpoint, every historical result.

## 3. Relative lookup — implementation

- **Family key:** `(Δrow, Δcol, round(radius, 4))`. Index v2 has 62 families (31 with ≥ 2 absolute keys, covering 4,492 of 4,821 witnesses).
- **Descriptors:** the stored windows are reused unchanged — a 3 × 3 window centred on the cell and a 4 × 4 window anchored at local (1, 1). Off-board cells are −1. Codes: free 0, object 1, target 2, goal 3, moving object 4.
  - **Tested:** the windows are translation-consistent and invariant to object ids, and a query descriptor equals the stored one.
- **Robot-relative term:** the residual is computed by `base_residual`, a 2-point Procrustes about the fixed base, which also returns ψ.
  - **Similarity:** simρ = 1 / (1 + residual / 0.08 m).
- **Modes:** `rel_modes` groups witnesses with the same (elbow, wrist) sign class **and** an object-local sweep IoU ≥ 0.6, the local sweep being the cells within Chebyshev 2 of either endpoint, as source offsets.
  - **Properties:** canonical order, permutation-invariant, precomputed once — 372 relative modes (against 1,163 absolute P15 modes).
  - Members keep full provenance: file#index, root, query, seed, split, absolute key.
- **Score:** R = 0.5·sim3 + 0.5·sim4 + 0·simρ + 0.25·simG. With these weights R **equals the legacy combined score entry by entry** (tested to 1e-12).
- **Shortlist:**
  - Modes are ranked by (best R, independent roots, cheapest travel) and witnesses by (R, travel, provenance).
  - At most 3 modes × 2 witnesses are returned.
  - Every candidate carries `same_absolute`, `requires_adaptation`, `adapted = False`, `verified = False`, its score components, the residual and ψ.
  - An empty pool returns `UNKNOWN_NO_WITNESS`.
- **Switchable baseline:** `retrieve(ri, …)` with `key = "absolute_src_dst"` returns exactly `p14_sweep_index.lookup_candidates` (tested); the legacy P14 test "same Δ elsewhere → UNKNOWN" still passes.

## 4. Tests (`tests/test_approach_d.py`: 11 passed; with `test_p14.py` + `test_p15.py`, 38 passed)

1. Same Δ at (10→18) and (34→42) retrieve each other; the absolute keys stay distinct.
2. Distinct Δ and distinct footprints are not mixed.
3. No hit, or everything excluded → `UNKNOWN_NO_WITNESS`, never infeasible.
4. Windows are translation-consistent, with consistent border padding (corner cells 0 and 63).
5. The descriptor is invariant to object ids and equal to the stored descriptor pipeline.
6. Modes are deterministic under permutation and split by branch and by local sweep.
7. The shortlist is bounded (mode_limit × witnesses_per_mode, ≤ per-mode cap), and `requires_adaptation` ⇔ different absolute cells.
8. The legacy switch equals `lookup_candidates`; the legacy weights reproduce the legacy scores.
9. Indexed retrieval equals the brute-force scan on real keys; root exclusion and the LOKO own-key exclusion are honoured.
10. Base residual = 0 only for an exact rotation (90° about a cell-centred base); same Δ elsewhere on the real base gives residual > 0.
11. Config overlay validated (unknown key fails; a non-UNKNOWN no-witness status fails); `config.toml` untouched.

**Defect caught during development.** The first version of test 7 assumed a same-location witness would lead the shortlist. Under legacy weights it does not when scores tie. This is reported as finding C7 rather than hidden; the test now fixes the travel so the flag check is deterministic.

## 5. Retrieval coverage and efficiency (`runs/approach_d/g1/`)

**Held-out protocol** (`RETRIEVAL_ROWS.json`, `RETRIEVAL_SUMMARY.json`):
- **Queries:** 442, i.e. ≤ 2 roots per absolute key, seed 0, each witness's own stored descriptor.
- **LORO:** excludes the query root and every same-fingerprint root.
- **LOKO:** also excludes the query's absolute key, i.e. a new location.
- **Pattern hit:** same terminal branch and object-local sweep IoU ≥ 0.6 as the held-out witness that is VERIFIED in that scene. This is a **proxy**, not feasibility.

| | LORO | LOKO (new location) |
|---|---|---|
| queries with ≥ 1 absolute-key candidate | 330 / 442 | **0 / 442** |
| queries with ≥ 1 relative candidate | 422 / 442 | **400 / 442** |
| held-out pattern present in the pool (absolute / relative) | 264 / 394 | 0 / 346 |
| mean pool scored (relative); mean modes | 311; 19.2 | 311; 19.7 |
| random top-1 pattern rate | 0.227 | 0.163 |
| top-1 pattern hit (legacy weights) | 214 / 422 (0.51) | **149 / 400 (0.37)** |
| shortlist (≤ 6) pattern hit | 315 / 422 (0.75) | **250 / 400 (0.63)** |
| mean returned / distinct modes / distinct absolute keys | 5.5 / 2.8 / 2.2 | 5.6 / 2.9 / 2.3 |
| top-1 base residual (m) | 0.023 | 0.053 |
| indexed = scan | 442 / 442 | 442 / 442 |
| median latency, indexed vs scan | 4.9 ms vs 7.7 ms | 4.6 ms vs 7.1 ms |

**LOKO ablation** (hit@1 / hit@≤6 over 400 queries; mean top-1 residual):

| variant | hit@1 | hit@≤6 | top-1 residual (m) |
|---|---|---|---|
| legacy weights (default) | 149 | 250 | 0.053 |
| + ρ (αρ = 0.5) | 152 | 247 | **0.036** |
| ρ only | 115 | 204 | 0.026 |
| 3 × 3 only | 135 | 235 | 0.066 |
| 4 × 4 only | 150 | 247 | 0.046 |
| global only | 72 | 182 | 0.095 |
| top-1 mode × 6 witnesses | 149 | 167 | 0.053 |
| 6 modes × 1 witness | 149 | **284** | 0.053 |

**Candidate coverage on development roots** (`DOMAIN_COVERAGE.json`):
- **Roots:** P16 dev / calib / val, 86 roots, 0 sharing a fingerprint with the index.
- **Moves:** every mover × the first 4 scene-only slots, 1,032 moves.
- **Coverage:** 548 absolute, **963** relative, **415** relative-only.
- Coverage means only that at least one indexed witness exists. It is not motion availability.

**Readings:**
- Local patches carry the ranking signal: 4 × 4 ≥ 3 × 3, and global-only is close to chance.
- Adding ρ keeps pattern recall and lowers the robot-relative mismatch by a third. This is the most promising G2 setting, but it stays an ablation until physical certification counts exist.
- Mode diversity matters: a top-1-mode-only shortlist loses 83 of 250 hits.
- Indexing saves about 1.5× over a full scan. The remaining cost is scoring the family (~311 entries), about 2 % of one exact certification (≈ 0.24 CPU-s). Retrieval is not the bottleneck.

## 6. Visualizations (`visualizations/approach_d/g1/`)

- [`G1_relative_match.png`](../visualizations/approach_d/g1/G1_relative_match.png) shows a held-out LOKO query, 47→45, Δ(0, −2), next to its top three cross-location witnesses (23→21, 31→29, 61→59).
  - **What each panel draws:** each witness in **its own** scene, with the arm at the grasp configuration, the recorded tool path, 3 × 3 (solid) and 4 × 4 (dotted) source and destination windows, and the displacement arrow.
  - **Patch strip:** the categorical patches below each panel mark the cells that differ from the query.
  - **Labels:** "own scene: VERIFIED | query scene: NOT adapted, NOT verified". The query's hidden witness is dashed.
- [`G1_coverage_ablation.png`](../visualizations/approach_d/g1/G1_coverage_ablation.png):
  - (a) coverage, absolute vs relative;
  - (b) LOKO ranking / shortlist ablation against the random line;
  - (c) top-1 base residual per variant;
  - (d) the Δ(0, −2) family: 13 absolute keys coloured by their base residual to the query, showing that the same displacement has different robot-relative geometry.

## 7. Unresolved engineering limitations

1. **No physical transfer has been measured.** The pattern proxy cannot say whether an adapted motion certifies (G2).
2. **The library has one footprint, one object kind and one grasp class,** so footprint generalisation is untested.
3. **42 / 442 LOKO queries have no family at all** (rare displacements), so G2 needs the online planner there.
4. **Relative modes are coarser than P15 absolute modes** (372 vs 1,163). Whether that merges physically distinct motions is unknown until G2.
5. **Reflection symmetry is not used.** The gripper's mirror symmetry is unproven.
6. **The 4 × 4 window is asymmetric** (anchored at local (1, 1)). This is kept for parity with stored descriptors, but it means a move and its mirror see different context.
7. **The physics provider is not wired yet** (deliberately, G2).

## 8. G1 gate

**PASS (retrieval scope)**, written to `runs/approach_d/g1/G1_GATE.json` with code, config and index hashes.

**Gate criteria (spec §7 G1):**
- indexed retrieval correctness: tests + 884 / 884 scan equality;
- translated local scenes map to the same relative key and retrieve each other: test 1 + LOKO 400 / 442;
- legacy exact-cell control kept and switchable;
- held-out neighbour metrics with counts and efficiency: §5.

## 9. G2 plan (precise; requires authorisation)

1. **Tiered opt-in provider** in `p16_motion.DetPhysics` (legacy default unchanged), all tiers charged to one `motion_checks` budget:
   - tier 0: exact-cell legacy witnesses;
   - tier 1: relative shortlist → adapt → certify;
   - tier 2: online planner.
2. **Adaptation** (`relative_motion.py`, only if it does not fit in `p16_motion`):
   - (i) an exact base rotation q₁ += ψ*;
   - (ii) if residual > 0: TCP waypoints from FK, source-anchored phases shifted by e_s and destination-anchored phases by e_d;
   - (iii) closed-form 3R IK per waypoint on the witness's branch, with joint continuity; failure → `UNKNOWN_ADAPT`;
   - (iv) the record is rebuilt (place_xy, phases, gap, attachment), and the grasp consistency check is required.
3. **Fresh verification:** `motion.certify_trajectory` on the adapted joint path (the swept volume comes from the adapted q, never a shifted mask), certified transit from the current q, and an independent `replay`.
4. **Tests:**
   - (a) a real cross-location adapted relocation replays CLEAR;
   - (b) a mid-path link / carry / gripper collision is rejected after adaptation;
   - (c) an unreachable waypoint gives `UNKNOWN_ADAPT`, never certified;
   - (d) UNKNOWN is preserved end to end;
   - (e) a 0-residual rotation reproduces the witness certification;
   - (f) the legacy provider is byte-identical when the switch is off.
5. **Physical benchmark:** LOKO with adaptation on the same 442 queries. Report certified count, calls to the first certification, failure reasons (transit / collision / adapt / budget) and CPU, for relative vs exact-cell vs planner, at equal budgets, plus the ρ and 6 × 1 shortlist ablations decided on these physical counts.

**STOP — G2 not started. Awaiting explicit authorization.**
