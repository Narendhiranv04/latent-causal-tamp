# P2: pipelines, unit tests and smoke checks

**Gate: PASS. Every check below was run before any fresh-root inference.**

## Contract tests (`tests/test_k45.py`): 14 passed

| Area | Test |
|---|---|
| Scene | rebase identity; prefix pose update; stationary objects, ids, heights and target flags preserved; no aliasing |
| Retarget | tid / goal / goal_cell / is_target column for every object / ctx goal and target size, height, is_box slots; q_ref slots kept; height never mutated; roundtrip to the original task |
| Sampler input | `placement.task_features` of a retargeted row: goal one-hot = d, target one-hot = A's cell, ctx copied |
| Grammar | vacated original cell, original goal and reserved pending destinations are illegal in rebased scenes (`Root.legal_dests`); double move, original target, occupied and goal destinations rejected; eligibility excludes moved, pending and current-task objects |
| Composition | K4 splits 1+3 / 2+2 / 3+1 and K5 splits 2+3 / 3+2; group lengths; order counts (5!·2 = 240, 4!·3 = 72); dependency-respecting orders |
| Selector | NOOP gate, ABSTAIN when nothing is admitted, tie-break toward the shorter plan |
| B4 (stub model) | the enabler is inserted **before** its parent with a recorded edge; the no-insertion sibling is kept; no room → no insertion; repeated (prefix, task, reservations) → cycle guard |
| Real frozen 3D bundle | B0 reproduces the sealed V3.4 DEV decisions and scores, deterministic on rerun; Y-only `Y_global` = full-view pY (≤ 1e-5); pY identical for both orders; p11 = pY·pX1 and the marginal pX identity (≤ 1e-12); length-5 sequences give finite readouts (OOD); cache entries differ across tasks |
| Caps | `CapReached` is raised **before** a batch would exceed the unique-readout cap; nothing is counted |
| Isolation | planner modules (`run, compose, recursive, scene, models`) never reference the evaluator, generator, teacher or private paths |
| Statuses | strict outcomes: UNKNOWN and missing are never failures; a decided X = 0 with unresolved Y is FAIL_X |

**Historical tests:** all 50 still pass (`full_domain_sets` 26, `mcts_sets` 13, `repair_ranking` 11). The old `approach_b_final/tests` modules need `/scratch/nav` data that is absent on the laptop; they fail identically at the parent, and no file there was modified.

## B0 parity on exposed DEV (`P0_B0_PARITY_DEV.json`)

5/5 identical decisions and moves (REPAIR-3/2/1, NOOP, ABSTAIN); score |Δ| ≤ 1.0e-7; top-4 proposals equal.

## Physical adapter validation (`P2_ADAPTER_SMOKE.json`; 2 counted evaluation jobs, 15.2 CPU-s)

The root is an exposed TRAIN 3D root (`3ds66-lap3-w0047-s012`) whose archived teacher result for `[[o01, (4,0)], [o00, (1,3)]]` is X = Y = 1.

| Mode | X | Y | Independent replay | Boundary trace |
|---|---|---|---|---|
| continuous (connector at the end; `fin3d.run_x` semantics) | 1 (VERIFIED) | 1 | 1 | move, move, connector (|dq| 1.8e-4) |
| chunked 1+1 (q_ref connector after each group) | 1 (VERIFIED) | 1 | 1 | move, connector (3.2e-4), move, connector (1.8e-4) |
| **disconnected fixture** (inner q_ref return removed) | – | – | **0: DISCONNECTED_START** | the next stored witness does not start at the current arm state, so it is rejected, never teleported |

## Dry run of all five arms on 2 exposed DEV roots (model only)

All arms produce one committed plan within the caps.

| Arm | Latency per root |
|---|---|
| B0 | 0.6–0.8 s |
| B1 | 1.1–3.8 s |
| B2 | 0.4–1.1 s |
| B3 | 18–22 s |
| B4 | 23 s |

- **Coverage logging:** on one root the length-5 endpoint pool (54,304) was hash-sampled to 50,000 under the shared endpoint cap, and this was logged as incomplete.
- **B4:** 5–9 insertions accepted with depth 2. The 64 temporary readouts are reached and logged (`readout_cap_hit`); further prefixes then continue without retargeting.

**Figure:** `figures/p2_synthetic_retarget_chain.png` (stub-model fixture; schematic, not physical).
