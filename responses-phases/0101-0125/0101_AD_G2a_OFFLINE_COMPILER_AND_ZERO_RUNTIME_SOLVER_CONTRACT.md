# 0101 — Approach D G2a: offline motion compiler and zero-runtime-solver contract

**Authority:** `approachD_G2_offline_only_instructions_v1_1.md` (supersedes `approachD_methodology.pdf` v1.0 where they conflict).
**Branch:** `approach-d-v1` (local, not pushed). **Base:** G1 commit `df913ae` (on `027fb7f`). **Scope:** G2a only. G2b provider integration, the 442-query G2c benchmark, any large catalog build, D training and the target-only arm (G3) are **not** started.

## 0. Verdict

**G2a: PASS** (gate file `runs/approach_d/g2a/G2A_GATE.json`). The gate criteria were written into `ad_pilot.gate` before the pilot ran:
- G1 re-verified independently;
- zero forbidden calls on every runtime row;
- the four required cases demonstrated on development data;
- unit tests and the post-change regression clean.

The gate has no success-rate threshold. The pilot is a modest development fixture set, not a benchmark, and its numbers below are not held-out claims.

The headline is twofold:
- **The runtime makes no IK, planner or connector calls.** All 60 runtime evaluations (1,145 template checks) ran under a guard that makes every such entry point raise.
- **The relative-family templates turn G1 pattern matches into executable motions** far more often than unseeded templates of the same budget:
  - 15/36 against 5/36 at K = 6;
  - 13/36 against 0/36 at K = 1;
  - per root: 9–0 and 12–0 in their favour.

The canonical-home contract, however, is the dominant cause of failure.

## 1. Step A — G1 verified on the working tree

| check | result |
|---|---|
| `git rev-parse HEAD`, branch | `df913ae51800…`, `approach-d-v1`; only the user's two deleted root PDFs and their untracked files differ |
| fresh full regression at `df913ae` (`runs/approach_d/g2a/g1_verify/`) | **513 passed, 0 failed**, 6/6 archived replays clean, `P3A_REGRESSION_CLOSED` (781 s) |
| G1 tests `tests/test_approach_d.py` | 11/11 pass inside that run |
| G1 benchmark recomputed from code into a scratch directory (`p15_lookup.g1_benchmark`) | all 884 rows and both summaries **identical** to the committed files apart from timing fields |
| LOKO numbers | relative candidates 400/442 (legacy 0); top-1 pattern 149/400; 3 × 2 shortlist 250/400; 6 × 1 shortlist 284/400; plus-ρ 152 / 247 — as reported |
| LORO | relative 422/442, legacy 330/442; hit1 214, hitK 315 — as reported |
| `config.toml` | untouched (no diff to HEAD; sha256 `56ede7f0…`) |

There are no numeric discrepancies. Three G1 *semantics* are superseded by v1.1. The G1 code and records are kept as they are, and the points are recorded here instead of rewriting history:
- **(i) `UNKNOWN_NO_WITNESS`.** `[relative_lookup] status_on_no_witness = "UNKNOWN_NO_WITNESS"` is the status string of the G1 retrieval API. The new runtime never surfaces it: an empty or missing template set is the finite-library failure `NO_TEMPLATE`.
- **(ii) Runtime adaptation and online fallback.** The G1 audit's G2 plan (closed-form IK at adaptation time, `UNKNOWN_ADAPT`, an online-planner tier) is withdrawn. All adaptation now happens in the offline compiler.
- **(iii) Physical meaning of G1 pattern hits.** They remain a retrieval proxy. §5.4 shows they are close to independent of physical success.

## 2. Step B — every runtime solver path, and the new entry point

### 2.1 Dynamic trace of the historical P16/P17 inference path

`ad_pilot.audit_runtime_paths` → `RUNTIME_PATH_AUDIT.json`. One D node was run on P16 dev root `p13_2026210000`, with `ad_runtime.forbid("count")` recording every forbidden call and its caller.

| historical call | forbidden calls reached | via |
|---|---|---|
| `p17_domain.movers` + `slot_fn` | **0** | scene-only rules + library-destination lookup (pure) |
| `DetPhysics.goal` (target-T check) | 261 `geometry.ik`, 96 `sector_check._ik`, 9 `motion.ik_line`, 3 grasp screens | `p15_retarget.certified` → `ordered.certificates_for` → `skill.pick_certificate` and `sector_cert.produce` → screens and IK; then `skill.plan_skill` |
| `DetPhysics.edges` (one relocation) | 721 `geometry.ik`, 37 `ik_line` / `ik_track`, 10 `planner.plan`, 1 `skill.plan_skill`, 5 grasp screens | `ordered.certificates_for` / `first_screen`, then the library lookup's transit RRT, then the online `plan_skill` fallback |

Consequences:
- **The historical motion provider cannot be reused unguarded at inference.** This covers `p16_motion.DetPhysics` and `p15_search.Physics`.
- **The scoped infeasibility certificates use IK**, so the new runtime has none. It therefore never returns a `CERTIFIED_INFEASIBLE` truth value; it returns only `SUCCESS` or `FAILURE` with a reason.
- **The P17 action domain (movers, slots) is solver-free** and can be shared unchanged.

### 2.2 The deny list and the new entry point (`ad_runtime.py`, 126 lines)

The deny list `ar.FORBIDDEN` has two kinds of entries:
- **Leaves:**
  - IK: `geometry.ik` and the second, independent IK `sector_check._ik`;
  - IK-tracked lines: `motion.ik_track / ik_line / carry_line`;
  - planners: `planner.plan / _rrt_connect`;
  - grasp screens and the online skill planner: `skill.screen_pick / screen_place / plan_skill`.
- **Composites that reach those leaves** (patched so a call is attributed): `skill._ik`, `skill.pick_certificate`, `ordered.certificates_for / first_screen`, `p15_retarget.certified / probe`, `sector_cert.produce`, `p6_scenes.Screens.pick / place`, `p14_d_search._transit`, `p15_search.Physics._goal / _edges`, `p16_motion.DetPhysics._goal / _edges / _transit`.

Inherited methods are patched on the subclass and removed afterwards. Only `viz.py` imports a function by name (`bodies`, drawing only), so patching module attributes covers every caller.

The new inference entry points:
- **`ad_runtime.check(robot, cfg, scene, oid, dst, q, templates, budget)`.** First-valid selection over an ordered list of frozen templates:
  1. destination occupancy;
  2. exact absolute (src, dst);
  3. footprint;
  4. exact start-q continuity;
  5. a conservative swept-cell prefilter, which rejects only;
  6. `motion.certify_trajectory` on the stored record in the current scene, which alone accepts.
- **`ad_runtime.check_entry`.** The same, for root start-q → home entry actions.

Allowed calls only: `ge.Checker`, `ge.make_world`, `ge.certify`, `mo.certify_trajectory`.

Failure reason codes are `NO_TEMPLATE`, `DEST_OCCUPIED`, `FOOTPRINT_MISMATCH`, `NO_COMPATIBLE_START`, `COLLISION_ALL_CHECKED`, `NOT_CLEAR_ALL_CHECKED` and `CHECK_BUDGET_EXHAUSTED`. They are reasons, not labels; nothing is ever re-planned.

### 2.3 Automated forbidden-call tests (`tests/test_approach_d_g2a.py`)

- **Static, deny by default.** An AST check: `ad_runtime` imports only an allowlist, and its inference functions reference only the allowed `ge.*` / `mo.*` attributes and no solver names.
- **Guard.** Every leaf raises under `forbid()`, including inherited `DetPhysics._goal`, and every patched attribute is restored afterwards.
- **Runtime paths under `forbid("raise")`, all with zero calls:**
  - success that stops at the first accepted template;
  - prefilter rejection followed by an alternative template;
  - all-collide;
  - budget exhausted;
  - destination occupied;
  - no template;
  - wrong start q;
  - footprint mismatch;
  - entry action;
  - the same displacement at other absolute cells (`NO_TEMPLATE`, never a translated template);
  - a whole-arm collision outside both local windows.
- **The pilot itself.** It ran every runtime check under `forbid("raise")`. A single forbidden call would have aborted it. `runtime_ik_calls = runtime_planner_calls = 0` on all 60 rows.

## 3. Step C — offline compiler and catalog (`ad_compile.py`, 384 lines; `[compiler]` / `[runtime]` in `approach_d.toml`)

**Contract.**
- Canonical home (`Q_HOME`): every template starts and ends **exactly** at `q_home`.
- A root that starts elsewhere needs a precompiled `ENTRY` template, root stratum → home. The 3 non-home strata S1–S3 were compiled.

**Fixture.** `GENERIC_EMPTY_WORKSPACE`: the moved disc alone at `src`, with no root, split or scene geometry. A template is therefore scene-independent. It is valid in a new scene only after the runtime certifier says so.

**Origins (each compile attempt is binary).**

| origin | what is compiled (offline; IK / IK-lines / planner allowed) |
|---|---|
| `EXACT_CELL_WITNESS` | a stored witness at the same cells: its own path kept **verbatim**, wrapped in certified home connectors (pregrasp, return_home) |
| `BASE_ROTATION` | q1 + ψ moves the whole record rigidly about the base. **Lattice audit:** only 4 of the 4,032 ordered cell pairs have an exact rotation partner, all radially collinear and touching cells 16 / 40 inside the link-0 annulus. **No valid-cell pair has one.** It is therefore exercised only on a controlled off-lattice fixture (test), where the rotated record re-certifies and a ψ that misses the destination is rejected. |
| `FAMILY_RETARGET` | per G1 relative mode (canonical seed = the mode's first member), members in canonical order: the seed's pick and place elbow branches, its grasp axes rotated by the best base rotation ψ, **snapped to the declared 15° grasp set on the same branch** (≤ 30°); then realised at the new cells with offline IK, certified approach / retreat lines, a guide-line or pose-space carry, and certified home connectors. First `templates_per_mode = 2` distinct templates per mode. |
| `DIRECT_OFFLINE:order` / `:spread` | the unseeded baselines: declared grasp pairs in `plan_skill`'s own preference order, or spread over (pick, place) branch classes; K = 6 |
| `ENTRY` | stratum q → home, nothing held, certified joint path |

**Schema** (`runs/approach_d/g2a/catalog/CATALOG.json` + `CATALOG_TEMPLATES.npz`).

Each template stores:
- identity and kind: `id` (sha256 over version, src, dst, waypoints, gaps and phases), `compiler_version`, `origin`, `kind`, `src`, `dst`, `radius`, `object_class`, `fixture`, `contract`;
- robot state and grasp: `q_start`, `q_end`, `grasp` ((φ, branch) at close and release), `waypoints`, phase counts, `travel_J`;
- sweep: `swept_by_phase` (absolute cells of the **actual** stored path, return_home included), `swept`, `sweep_hash`;
- provenance and validation: `derivations` (every compile path yielding this exact template, with its lineage: seed file#index, root, seed cells, ψ, base-rotation residual, seed grasp, snapped grasp, grasp shift), `validation`, `compile_cpu_s`, `sweep_cpu_s`.

Arrays hold the full phase-labelled waypoint record: q, gap, phase, attachment, held offset, placement.

The **execution index** maps `src>dst|radius|home` → ids; it is kept separate from G1's relative pattern index.

Every **attempt** row is a binary `AD_BINARY_BUDGET_V1` outcome. It carries `compiled` 1/0, `negative_kind` ∈ {CERTIFIED, TIMEOUT, NO_PLAN_FOUND, OTHER_FAILURE} as metadata only, `termination_reason`, `budget_id = B_COMPILE_V1` (4,000 planner nodes, wall clock disabled), CPU, hardware and template id.

**Determinism.** Two complete runs produced the identical catalog: template hash `sha256:2908fd08…`, the same 1,073 templates, and the same array bytes.

## 4. Step D — development pilot (`ad_pilot.py`; `runs/approach_d/g2a/PILOT_ROWS.json`, `PILOT_SUMMARY.json`, `REACH_PROBES.json`)

**Cohort (dev split only; no validation, blind or test root is used as a query).**
- **Relocation queries.** The 36 G1 LOKO queries whose root is in a P10b–P13 *dev* split and has a relative family: 25 roots, 34 absolute keys. Each is the move src → dst in the held-out witness's own scene. That witness is verified there from its own start q, so a motion exists in that scene.
- **Exclusions follow G1:**
  - the query root and every root sharing its geometry fingerprint;
  - for the relative and direct policies, the query's own absolute key.

  The exact-cell policy uses LORO (same key, other roots).
- **Target T.** All 24 P16 dev roots, as target-T template checks in the **initial** scene (no repair), after their ENTRY action.
- **Reachability.** 18 empty-workspace probes.

**Runtime.** From `q_home`, with at most 6 exact certifications per move and the swept-cell prefilter, everything under `forbid("raise")`.

### 4.1 What compiles, and why it fails (offline)

| origin | attempts | compiled | failures (negative_kind: reason) | CPU median / total |
|---|---|---|---|---|
| FAMILY_RETARGET | 633 | **586** | 33 NO_PLAN_FOUND: no declared grasp within 30° of the rotated seed on its branch; 14 CERTIFIED: home → pregrasp blocked by a certified link-0 sweep | 0.14 s / 413 s |
| DIRECT_OFFLINE:order | 396 | 300 | 96 CERTIFIED: link-0 sweep, home → pregrasp | 1.13 s / 464 s |
| DIRECT_OFFLINE:spread | 264 | 232 | 32 CERTIFIED: link-0 sweep | 1.81 s / 454 s |
| EXACT_CELL_WITNESS | 40 | 40 | — | 0.10 s / 19 s |
| ENTRY | 3 | 3 | — | < 0.01 s |

- **Totals.** 1,073 distinct validated templates. Indexing their absolute sweeps cost 815 CPU-s, more than compiling them. Pilot wall time was 9 min on 8 workers. This is offline cost, reported separately from inference.
- **Robot geometry decides which G1 matches compile.** Family compile success falls with the seed's distance from an exact base rotation:

  | base-rotation residual | compiled |
  |---|---|
  | < 2 cm | 57/57 |
  | 2–5 cm | 153/153 |
  | 5–10 cm | 189/194 |
  | ≥ 10 cm | 187/229 |

  The failures are elbow-branch / grasp-axis unavailability at the new cells and link-0 sweeps.
- **Grasp shift is small.** The median snap shift is 4.5°.
- **Reachability.** In the empty workspace every probed pair compiles at least one template, including 12 pairs entirely inside the link-0 annulus (`REACH_PROBES.json`). On this board a missing template is a library or compile-policy outcome, not geometric unreachability.

### 4.2 What executes in the held-out scenes (online, zero solver calls)

36 dev relocation queries; success = a frozen template certified in the held-out scene from `q_home`:

| runtime policy (≤ 6 exact checks) | template available | **SUCCESS** | failures |
|---|---|---|---|
| REL_K1 (G1 top mode, 1 template) | 36 | **13** | 23 COLLISION_ALL_CHECKED |
| REL_3x2 (top 3 modes × 2) | 36 | **14** | 22 COLLISION |
| REL_6x1 (top 6 modes × 1) | 36 | **15** | 21 COLLISION |
| DIRECT_ORDER_K1 | 26 | 0 | 26 COLLISION, 10 NO_TEMPLATE |
| DIRECT_ORDER_K6 | 26 | 0 | 26 COLLISION, 10 NO_TEMPLATE |
| DIRECT_SPREAD_K6 | 36 | 5 | 31 COLLISION |
| EXACT_CELL_K2 (LORO, 23 queries with exact-cell witnesses) | 23 | **11/23** | 12 COLLISION |
| UNION_ALL (every compiled template for the query; catalog upper bound) | 36 | 19 | 17 COLLISION |

**Paired, root-clustered (exploratory, dev).**

| comparison | discordant queries | roots favouring each side | sign test |
|---|---|---|---|
| REL_6x1 vs DIRECT_SPREAD_K6 | 10 vs 0 | 9 vs 0 | p ≈ 0.004 |
| REL_K1 vs DIRECT_ORDER_K1 | 13 vs 0 | 12 vs 0 | p ≈ 0.0005 |
| 6 × 1 vs 3 × 2 | 1 vs 0 | — | no evidence either way |
| 3 × 2 vs K = 1 | 1 vs 0 | — | no evidence either way |

On the 23 exact-cell queries, exact-cell gives 11 and REL_6x1 gives 10, and 13 succeed under either.

**Target T (24 P16 dev roots, initial scene).**
- Entry actions certified for all 17 non-home roots.
- Unseeded target templates: 0/24.
- Only 8/24 target pairs have any relative family.
- One root (`p13_2026210004`, 52 → 47) has a REL template certified *before any repair*. That root is constructed as obstructed. This needs a G2b audit against its P16 status (likely: its obstruction is relative to its stratum start or grasp family) and is **not** interpreted here.

**Online cost.**
- A prefilter rejection costs about 0.15 ms.
- An exact frozen-trajectory certification costs a median 0.047 s (p90 0.106 s).
- The mean number of exact checks per move was 0.4, because the prefilter resolves most rejections.

### 4.3 Why moves fail: the home contract

Of 752 templates the prefilter rejected in the held-out scenes:
- **228 collide only in the home connector legs** (home → pregrasp or retreat → home) while the stored pick–carry–place core is clear;
- 511 collide in both;
- 13 in the core only.

The held-out witnesses that prove a motion exists all started from their own q and did not return home. The canonical-home contract is therefore the main coverage cost, not the relative transfer.

**Prefilter.** It caught every template the certifier would reject (0 misses). It wrongly rejected 4 templates the certifier would accept, costing 1 success each in REL_6x1, EXACT_CELL_K2 and UNION_ALL (16 / 12 / 20 without it).

### 4.4 Pattern retrieval vs executable motion

Per query, G1's top-1 pattern hit and REL_K1 physical success:

| | REL_K1 success | REL_K1 failure |
|---|---|---|
| G1 top-1 pattern hit | 5 | 9 |
| no pattern hit | 8 | 14 |

For the 6 × 1 shortlist (pattern hit vs success): 10 / 17 / 5 / 4.

A matched 3 × 3 / 4 × 4 pattern is **not** an executable motion, and is close to independent of one. The figures and tables report pattern retrieval, compilation and current-scene verification as separate quantities.

### 4.5 The four required cases (`visualizations/approach_d/g2a/G2a_cases.png`)

Every robot is a stored configuration drawn with the certifier's own bodies, over the absolute swept cells of that stored path.

| panel | case |
|---|---|
| (a) | **Exact-cell reuse:** Q05, 12 → 3, held-out scene `p13_2026152005`; stored core verbatim plus offline home connectors; verified. |
| (b1 / b2) | **Genuine shifted transfer:** seed 63 → 62 (own scene `p13_2026160071`) compiled offline for Q11, 21 → 20, held-out scene `p10b_2026127003`; base-rotation residual 20.2 cm (not a rotation); same branches; grasp shift 4° / 4°; verified. |
| (c) | **Same local pattern, whole-arm collision:** Q00, 4 → 3. The obstacle lies outside both 3 × 3 / 4 × 4 windows; certifier pair `link2 \| o00` in phase `pregrasp`; rejected. |
| (d) | **No compiled template:** Q04, 10 → 28. All 6 planner-order offline compiles fail on a certified `LINK0_SWEEP: link0 \| t0` → `NO_TEMPLATE`; the runtime stops with no IK or planner rescue. Other grasp classes do compile here, so this is a library-policy failure, not impossibility. |

`G2a_pilot_summary.png`: (a) per-policy physical outcome next to G1's retrieval proxy; (b) failure reasons.

## 5. Tests and regression

- **`tests/test_approach_d_g2a.py`: 12/12 pass (≈ 9 s).**
  1. static deny-by-default (AST);
  2. guard blocks and restores;
  3. first-valid, alternative and every failure path with zero calls;
  4. a same displacement elsewhere is a pattern, never a template;
  5. whole-arm collision outside the local windows is caught, with phase and body;
  6. entry template checked, not planned;
  7. exact rotation needs both endpoints, and no valid lattice pair has one;
  8. witness completion keeps the core verbatim, home to home;
  9. compile outcomes are binary with metadata only (no third label; `UNKNOWN` raises), and a bounded compile (K = 2) of the annulus pair 0 → 4 yields no template: every attempt is 0 with a declared negative_kind;
  10. seeded snap keeps branches and bounds the shift;
  11. catalog round trip and versioned ids;
  12. `[compiler]` / `[runtime]` are validated and `config.toml` is untouched.
- **Post-change full regression** (`runs/approach_d/g2a/regression/`): **525 passed, 0 failed** (513 historical + 12 new; 760 s), all 6 archived replays clean, `P3A_REGRESSION_CLOSED`.

## 6. Files

**New:**
- `ad_compile.py` (offline compiler, catalog);
- `ad_runtime.py` (inference contract, deny list, guard);
- `ad_pilot.py` (pilot, path audit, reach probes, gate);
- `ad_viz.py` (figures);
- `tests/test_approach_d_g2a.py`;
- this report;
- `runs/approach_d/g2a/**`, `visualizations/approach_d/g2a/*`.

**Modified:** `approach_d.toml` (appended `[compiler]`, `[runtime]`; `[relative_lookup]` unchanged).

**No historical module, test, report, label, replay fixture or `config.toml` was modified.**

## 7. Limitations (do not over-read)

- **Small development pilot.** 36 queries from 25 roots, dev split only. The defaults (3 × 2, 6 × 1, K = 1, per-mode W = 2, 30° snap) are not tuned and not frozen. The 6 × 1 vs 3 × 2 difference is 1 query.
- **Generic empty-workspace templates.** Their home connectors ignore clutter by construction; that is why 228 rejections are connector-only. A scene-specific compile would leak scene geometry and is not used.
- **Exact-cell vs relative compile cost.** Exact-cell templates reuse a recorded clutter-aware core; relative-family templates do not.
- **One object class.** One footprint (r = 0.024) and one grasp family. Mirror symmetry is unused: gripper symmetry is unproven.
- **Prefilter assumptions.** The swept-cell prefilter assumes that footprint for obstacles. It is conservative but not lossless (4 false rejects in 1,145 checks).
- **Pattern seed vs motion.** "Seed branch / grasp class realised offline" is the transfer. The compiled path is new; only its discrete motion class and grasp come from the seed.
- **No physical execution.** "Verified" means the frozen record passes the exact certifier in the held-out scene's geometry. No simulator or real-robot execution happened.
- **Target pilot.** It checks only the initial, unrepaired scene. Whole repairs (relocations then target) are G2b / G3 territory.
- **Retrieval cost.** It is a per-query family scan over the in-memory G1 index; a large catalog will need the mode-level index precomputed per absolute pair.

## 8. Gate and post-change regression

`runs/approach_d/g2a/G2A_GATE.json`: **PASS**.

| criterion | result |
|---|---|
| G1 re-verified at `df913ae` | 513 passed, 6/6 replays, benchmark recomputed identically |
| forbidden calls on runtime rows | **0** (60 rows, 1,145 template checks, raise-mode guard) |
| exact-cell reuse verified | Q05 |
| shifted transfer verified (residual > 2 cm) | Q11 (20.2 cm) |
| whole-arm collision outside local windows rejected | Q00 (`link2 \| o00`, pregrasp) |
| no template → `NO_TEMPLATE`, no rescue | Q04 |
| G2a unit tests | 12/12 |
| post-change regression | 525 passed, 0 failed, 6/6 replays |
| catalog | `AD_COMPILER_V1`, 1,073 templates, hash `sha256:2908fd08…`, arrays content hash `f0d61b72…`; deterministic across two runs |

Every file the gate covers carries a sha256 in the gate file, including `config.toml` (unchanged).

## 9. G2b plan (narrow; not started)

1. **`AD_PRECOMPILED` provider.** An opt-in sibling of `p16_motion.DetPhysics`'s interface (`edges` / `goal` with the same cells / q state keys) built only on `ad_runtime.check` / `check_entry` and a catalog. No certificates, transit, RRT or `plan_skill`. Cache keys include policy, compiler version, catalog hash, (src, dst), q, scene fingerprint, check budget and prefilter flag. The historical provider stays as is for old arms.
2. **Root entry.** If root q ≠ home, the stratum's ENTRY template must certify in the root scene, else root-level `FAILURE: NO_COMPATIBLE_START`.
3. **Ordering inside one move.**
   - tier 0: exact-cell templates (the LORO pool; start-q compatible by construction);
   - tier 1: G1-ranked relative-family templates (policy 3 × 2 or 6 × 1, chosen on DEV physical success at equal checks);
   - no tier 2.
4. **Reduce the home-contract cost** (the main G2a finding) in the smallest way allowed by v1.1 §2.2: a **finite configuration-transition graph**. Precompile additional terminal configurations, for example "retreat end" states plus certified retreat-end → home and retreat-end → next-pregrasp edges for a small declared set. At runtime, select only existing edges, still with zero solvers. Compare against pure `Q_HOME` on the same dev cohort.
5. **Forbidden-call guard tests on the full provider path:** multi-action sequence, failed witness, alternative destination, target check, and an execution failure that must not trigger a replan.
6. **Catalog size and cost estimate before any build**, for explicit budget authorization. From this pilot: about 0.14–1.8 CPU-s per compile plus about 0.8 s sweep indexing per template. The full valid board is 34 × 33 pairs × (modes × 2 + direct). The large catalog will not be built without approval.
7. **Not before authorization:** the 442-query G2c benchmark and any G3 D arm.

**STOP — G2b not started. Awaiting explicit authorization.** Nothing has been pushed or merged.
