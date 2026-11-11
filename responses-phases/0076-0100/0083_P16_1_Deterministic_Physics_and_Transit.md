# 0083 — P16-1: deterministic physics, alternate transit and replay

**Actual result**
- **Gate:** `runs/p16/P16_1_GATE.json` → **PASS (determinism), with partial coverage.**
  - Every repeated outcome was bit-identical.
  - Coverage: 4 of the 8 frozen representative roots completed under the default profile before the `motion` budget stop, and all 3 roots tested under the fast profile completed.
- **Spend:** `motion` 8,160 of 9,000 CPU-s, all recorded. This includes four runs stopped by me at 1,777 CPU-s each to stay inside the cap.
- **Code:** `p16_motion.py` (`DetPhysics`, `replay`, `traj_hash`) and `p16_eval.det_run`.
- **Data:** `runs/p16/shared/DET_{h0,h1,h2,direct,online,fast_h0,fast_h1}.json`.

## 1. Deterministic controlled mode (`DetPhysics`)

- **No CPU-time cap.** P15's soft per-root `process_time` cap is gone; search stops only on deterministic work budgets (motion checks, online moves, goal plans, transit plans, search nodes).
- **No wall-clock adjudication.** The planner's wall cap is set to 1e9 s, so node budgets decide. `wall_clock_cut` stays instrumented and was **0** on every call. A process watchdog (the job guard) remains as a safety limit; if it kills a run, that root is unrecorded (UNKNOWN_BUDGET), never CERTIFIED.
- **Seeds:** per-query seeds are a stable hash of (state, q, object, destination, budget, robot, profile). Statuses, transits, modes and travel are state-keyed.
- **Declared planner profile `P16_FAST`.** It cuts the cost of failing calls, which dominated labelling: one DEV root took 683 CPU-s under the default profile.
  - planner `max_nodes` 1,500, skill `max_plan_failures` 2, transit RRT 500 nodes;
  - still node-budgeted and deterministic;
  - positives remain sound; the only effect is that more hard calls become UNKNOWN (masked, never negative).
- **Shared exact cache across arms** (`DetPhysics._cached`, test `test_shared_cache_exact_virtual_accounting`):
  - a cached state-keyed result is reused only when the arm's remaining budget covers the recorded consumption, in which case the computation would have run identically;
  - the arm is charged the recorded counts, statistics and CPU (virtual CPU);
  - budget-censored results are never cached.

## 2. Determinism experiment (frozen set: P15 retro 003 / 009 / 012 / 024, P15 prospective 000 / 002 / 040 / 053)

Each run uses the full scene-only search: uniform order, all movable objects, n ≤ 3, node cap 400.

| run | roots completed | found / claim / trajectory hash / travel / budget counts / nodes |
|---|---|---|
| default profile, `PYTHONHASHSEED` = 0, 1, 2 (concurrent, under load from 2 other heavy jobs) | 4 | **identical** across all 3 processes on every root (e.g. 003: `68011839…`, travel 3.541424967; 009: `72fde865…`, 4.071869864) |
| `P16_FAST`, hash seed 0 and 1 (concurrent with 5 labelling / search jobs) | 3 (003, 012, 024) | **identical** to each other **and** to the default-profile hashes |

The P15 PROSP-053 divergence is consistent with P15's CPU-time cap and planner wall cap. Both are removed here; with them gone, repeats agree.

## 3. Start transit: direct-only vs planned alternate transit vs online-only (same 4 roots, default profile)

| root | direct-only (P15 semantics) | + bounded planned transit | online planner only (no library) |
|---|---|---|---|
| 003 | found, travel 3.541 | found, 3.541 (1 planned transit) | no plan |
| 009 | found, 4.655 | found, **4.072** (8 planned transits) | no plan |
| 012 | found, 2.093 | found, **2.008** (8) | no plan |
| 024 | found, 1.118 | found, 1.118 | found, 1.301 |
| online-only, all 8 roots | — | — | **2 / 8** |

**Findings:**
- **Planned transit** converts library witnesses whose straight start-transit failed (UNKNOWN_TRANSIT) into certified edges. It lowers plan travel on 2 / 4 roots, with equal success on these roots.
- **The library is essential:** online-only solves 2 / 8 roots, against 4 / 4 with lookup on the common roots.
- **Status discipline:**
  - a failed transit stays `UNKNOWN_TRANSIT`;
  - a planned transit is a multi-waypoint free-robot record whose every segment is certified;
  - its travel is counted in J.

## 4. Independent replay (`p16_motion.replay`)

- **Stricter than P15:** each record must **start where the previous one ended** (continuity, to 1e-6). Every transit waypoint segment is certified with the free-robot checker, and every relocation and target record by `motion.certify_trajectory` in the actual sequential scene.
- **Result:** every found plan in P16-1 and in the DEV pilot replays CLEAR.

## 5. Tests

- **Added:** `test_traj_hash_deterministic_and_sensitive`, `test_shared_cache_exact_virtual_accounting`, plus search and replay semantics.
- **Collision tests already covered:** mid-sweep collision and held-object collision are covered by the historical `motion` tests in the 457-test regression.
- **Not run as unit tests:** "same occupancy, different q" is not a unit test, because q is part of every memo, cache and seed key by construction (`p15_search.state_key`).
