# R1: faithful Fig. 3 recursive retargeting and home-anchored chunking (implementation and contract tests)

**Scope.**
- **Branch / base:** `naren/rss27-fig3-retarget-home` from `fac59ecd1f`. The commit SHA is in the commit message and is reported back to the owner.
- **Contract:** `fig3_recursive_scaling_plan.md` plus `fig3_R1_dual_domain_amendment.md`, with the owner note of 2026-11-26 asking that TT_ADAPTER_V1 and C3b/C4 be reused.
- **Compute:** gvlab2 only (RTX 5090 and CPU). No laptop or enigma compute.
- **Data boundaries:** no TEST, release_v2 or protected scaling data was opened. Nothing was retrained.
- **What R1 validates:** mechanics only. **No claim is made about recursive-scaling efficacy.**

## Decisions

| Component | Decision | Basis |
|---|---|---|
| Shared implementation (`views`, `models`, `rank`, `recursive`, `run`) | **PASS** | All synthetic contract tests pass, including the literal seven-action Fig. 3 composition. Historical suites pass. B0 K≤3 parity 3D 6/6 and 2D 8/8. Historical B4 4/4. Demos complete with no cap stop. |
| 3D physical adapter (`physical3d.py`, SHELF66V3 + CONNECTOR_TO_QREADY_V1) | **PASS** | Exact reference parity. Chunked and local-paired executions verified and replayed 4/4. Disconnected replays refused 2/2. TT_ADAPTER_V1 cross-check: labels and witnesses identical 6/6. A temporary target is witnessed blocked → feasible after its enablers. |
| 2D physical adapter (`physical2d.py`, BXY teacher primitives) | **PASS (mechanics)**, with one open physical risk | `x_query` and `t_goal` parity exact 3/3 each. TT_ADAPTER_V1 cross-check: labels 6/6. Chunked (1,1) **2/3**: the third failed honestly at an intermediate connector (UNKNOWN_TRANSIT). Disconnected replays refused 2/2. All 6 rejection fixtures fire. |

## 1. Shared implementation

### Files and what each does

New package `approach_b_final/fig3_retarget/`. The historical modules are unchanged.

| File | Purpose |
|---|---|
| `views.py` | Retargets learner views and rebases hypothetical scenes. Holds the masks, immutable action keys `(object id, cell)`, the legality grammar and the partitions. |
| `models.py` | Counted, cached readouts from the frozen bundle (MANIFEST `147645ee…`). Readouts: pY = σ(b), pX1 = σ(a + w), pX0 = σ(a), pX (marginal), p11, Y_global, and the per-domain cVAE top-4. |
| `rank.py` | Home-anchored E_home, with a DP over 1–3-action chunks (single chunk with m ≤ 3 = exact −log p11). Also the declared top-1 selection, and B0 with EXACT4 semantics. |
| `recursive.py` | The R-FIG3, R-GATED, F-FLAT and R-TOPO arms in one harness. |
| `run.py` | Parity and model-only demos. |
| `tt_adapter.py` | **Verbatim** copy of TT_ADAPTER_V1 `adapt()` from `validation_k3/ttarget.py @ e9fa587c3b` (sha256 `bd2831d7…`). |
| `tt_retarget_ref.py` | Verbatim copy of `validation_k3/retarget.py @ e9fa587c3b`, kept as a field-semantics reference. |
| `physical3d.py`, `physical2d.py`, `jobs.py` | Evaluator-side teacher adapters and the smoke-job builders. |
| `viz.py` | Figures. |
| `tests/test_fig3.py` | Synthetic contract tests (Section 1.4). |

### 1.1 The 13 R0 issues

| # | R0 issue | Fix in R1 |
|---|---|---|
| 1 | Enablers were generated only when pY < 0.5 (or for the lowest action, < 0.9). | Every seed action and every newly introduced enabler is retargeted, including high-pY ones (tested). The legacy thresholds survive only as the R-GATED arm. |
| 2 | Repeated temporary readouts consumed the cap. | Unique readouts are counted on a full-input cache key; repeats are cache hits (tested). Per-action coverage is kept in the plan tree. |
| 3 | A global "seen" set acted as the cycle guard. | Branch-local ancestor stack, plus protection of the ancestor and the current temporary target (tested). |
| 4 | Siblings were dropped and edges used positional indices. | The empty (no-insertion) sibling is always kept, plus k variants. Edges use immutable `(id, cell)` keys. |
| 5 | `respecting()` ignored PARENT edges. | Edges are PREREQ, LOCAL, SEED or FLAT_BEFORE. `valid_dag` is checked on every pool entry. R-TOPO relaxes only SEED edges (tested). |
| 6 | Variants were sorted to prefer more insertions. | Variants are kept by cumulative local score plus object-set diversity, never by insertion count. |
| 7 | The frontier was pruned by global Y only. | No global-Y pruning. Y enters only the final E_home. |
| 8 | Ranking had a +60 s deadline extension. | One hard deadline (`wall_s`) covers seeds, recursion and ranking. A timeout yields a well-formed decision (tested). |
| 9 | Legal cells ignored the declared support. | Rebased legal cells = **declared** legal cells − original occupancy − original goal − reservations (tested in 2D). |
| 10 | Only declared two-group splits existed. | All compositions into chunks of 1–3, solved by DP and equal to brute force for m = 1..6 × 5 random scorers (tested). |
| 11 | The scored mode did not match the executed mode. | The scored partition is the executed partition (tested). |
| 12 | Assignments were fully materialized before caps. | Repair and flat group lists are enumerated with a running count. Above `exhaustive_max_groups = 4096` they switch to a declared staged beam (counted in `staged_calls`). Seeds at S0 stay exhaustive EXACT4, the same set B0 enumerates. |
| 13 | The target was hard-coded `t0`. | `physical3d.y_target(A, d)` and `physical2d.y_temp(A, d)`, with TT_ADAPTER_V1 as the reference labeller. |

### 1.2 Design decisions made in R1 (exposed by the synthetic tests)

All four are declared and configurable.

1. **Admission of a non-empty local repair.**
   - **Rule:** the group must raise the frozen *temporary pY* (the parent's feasibility after the group) above the temporary no-op pY of the same view. This is the model's own "does this group unblock the parent?", with no fixed threshold.
   - **What is deliberately excluded:** the enabler's own X-infeasibility. Resolving it is the job of recursion on that enabler; the nested-prerequisite test fails without this rule.
   - **Why a rule is needed at all:** without admission, retargeting high-pY enablers spawned spurious repairs that exhausted the expansion budget before later seed actions were repaired. This was observed on the 7-action fixture.
   - **Option:** `admit="all"` restores unconditional admission.
2. **Beam bookkeeping score (never the final rank).**
   - Empty sibling = temporary no-op pY.
   - Repaired = temporary pY after the group × the enablers' own variant scores.
   - Per-seed expansion share: 24 of 96.
3. **Staged group generation** is used above 4,096 ordered groups per call. Without it, one 2D DEV demo root hit the 100k unique-readout cap and its coverage was truncated.
4. **The B0 argmax is always a seed.** Every long arm's pool therefore contains B0's K≤3 candidate.
   - **Why:** before this fix, a 2D demo picked a different 2-move plan, because the staged beam had also been applied to the seeds.

### 1.3 Evidence carried over from TT_ADAPTER_V1 / C3–C4 (e9fa587c3b; exposed VAL; same Y contract)

**C3b, blocked temporary targets** (Y_τ from q_ref in a hypothetical scene, unchanged teacher on an adapted record):

| Measure | 2D | 3D |
|---|---|---|
| Genuinely blocked in S0 | 39/49 | 22/22 |
| Verified preceding moves repair them | 31/39 | 20/22 |
| Frozen D argmax one-step candidate succeeds (vs random) | 66.7 % (vs 27.3 %) | 63.6 % (vs 14.5 %) |
| Adapter identity parity | 109/109 | 82/82 |

**C3, frozen Y_τ on reassigned tasks:** AUROC 0.69–0.82 (vs 0.88–0.96 on original tasks); badly miscalibrated (ECE 0.18–0.42).
- R1 therefore uses temporary pY only *relatively*, on the same view (admission and beam), never against an absolute gate.
- R-GATED keeps the legacy absolute gates on purpose, as the control.

**C4, intermediate-scene cVAE recall:**

| Domain | Intermediate − S0 (pp) | 95 % CI |
|---|---|---|
| 2D | **+5.3** | [2.5, 8.2] |
| 3D | **−10.4** | [−15.3, −5.4] |

R-FIG3 re-queries the frozen cVAE at rebased scenes, so this is a **predeclared 3D risk** for R2. It is an argument for running 2D first or in parallel, as the amendment allows.

**C3b also showed** that explicitly retargeting the cVAE context adds nothing over the original-task context or NoTask; the fixes come from the task-agnostic placement prior. R1 keeps the retargeted context because the plan requires it. R2 must not attribute any gain to context retargeting without that control.

### 1.4 Tests

All results are in `R1_TEST_LOG.txt` (run on gvlab2).

`tests/test_fig3.py`: **54/54 passed**. They cover:
- Literal and nested seven-action composition `[E,D,B,G,C,F,A]` with edges E→D→B, G→C, F→A, B→C→A.
- Retargeting of every action, including pY > 0.9.
- The R-GATED legacy gate.
- The cap-infeasible case (m_max 5): seed actions are never dropped.
- Empty sibling and the cycle guard.
- Protected and pending objects never appear in repairs.
- Masks and grammar: fixed, target, goal, occupied cell, double move, destination reuse, cap.
- 2D and 3D retarget fields and deep copy.
- Cache identity and counted temporary readouts.
- Hard caps and deadline.
- F-FLAT performs no retargeting.
- R-TOPO edge preservation.
- Partition counts 1/2/4/7/13/24.
- DP equals brute force for m = 1..6, with mode consistency and the p11 / marginal identities.
- No privileged imports or files in inference.
- The staged generator is bounded and declared.
- The B0 argmax is always seeded.

**Historical suites, with the real bundle on the RTX 5090:**

| Suite | Result |
|---|---|
| `compose3d_k45` | 14 passed |
| `full_domain_sets` | 26 passed |
| `mcts_sets` | 13 passed |
| `repair_ranking` | 10 passed, 1 skipped (the V3.2 snapshot is not on gvlab2) |

### 1.5 Parity and reproduction (RTX 5090)

**B0 (`rank.b0`) against sealed V3.4 EXACT4 GPU predictions:**
- **3D:** 6/6 decisions; |Δp11| ≤ 1.3e-7; proposals equal 4/4 (the 2 NOOP roots archive no proposals).
- **2D:** 8/8 decisions; |Δp11| ≤ 3.3e-7; proposals equal 8/8.
- Roots were chosen to span the archived decision kinds.

**Historical B4** (unchanged `compose3d_k45`): 4/4 cohort roots reproduce the archived decision and sequence exactly.

**Model-only demos** (2 roots per domain × 4 arms; no physical verification in R1):
- 3D latency: R-FIG3 1.5–1.9 s; R-TOPO up to 5.2 s.
- 2D latency: R-FIG3 2.6–3.5 s; R-TOPO up to 7.8 s.
- **3D:** R-FIG3 inserts 2 enablers on both cohort roots (4-move plans, partitions (1,1,2)). R-GATED differs on root 146.
- **2D:** both arms keep B0's two actions. On `w0073` the DP prefers a q_ref return between them (E_home 0.481 vs single-chunk −log p11 0.587). That is a **mode change that R2 must test physically**, given the 2D connector result below.

## 2. 3D adapter (gvlab2, 19 teacher jobs, 0.059 CPU-h, ≤4 workers)

### 2.1 What the adapter does

- **Mechanism:** reuses the audited `evaluate_k45.run_xb` (carried arm state, planned and executed CONNECTOR_TO_QREADY_V1 at every declared boundary) and replay (refuses any start with |dq| > 0.02).
- **Temporary target:** `y_target(rec, cells, A, d)` = `bd_3dt.query(e, A, d)` from q_ready in the settled scene. Every other body, including the original target, stays present.
- **Reference labeller:** the same query on a TT_ADAPTER_V1 record.

### 2.2 Results

| Fixture | Result |
|---|---|
| Target Y parity (t0 at the witness endpoint) vs the stored K4 witness | 2/2 identical witness ids |
| Generic temporary target = first relocation from q_ready vs the stored first move witness | 2/2 identical |
| Continuous run_xb (bounds {4}) vs the stored 5-witness trace | identical |
| Chunked (2,2) + t0: X / Y / replay | 2/2 X = 1, Y = 1, replay = 1; connector \|dq\| 1.9–4.3e-4 |
| Local paired (3,1): enablers → q_ready → parent | 2/2 verified and replayed |
| Inner connectors removed (negative fixture) | 2/2 refused: DISCONNECTED_START, dq 1.69 / 1.30 rad |
| Temporary target, last witness action, S0 → witness pre-state | Root 035: **blocked** (no feasible side grasp) → **feasible**. Root 146: feasible in both. |
| TT_ADAPTER_V1 vs direct parameterization (same 6 queries) | Labels 6/6, witness ids 6/6 identical |

The 3D connector and move trajectories (joint space) are in `figures/R1_3d_home_returns.png`.

### 2.3 Remaining hard-coding (3D)

- `evaluate_k45.run_y_g` and `replay` still use `t0`. That is production code, unchanged.
- The fig3 adapter and TT_ADAPTER_V1 cover temporary targets.

## 3. 2D adapter (gvlab2, 30 teacher queries in 23 job records, 0.029 CPU-h, ≤4 workers)

### 3.1 What the adapter does

`x_chunked`:
- Relocations via `DetPhysics.edges` + `best_edge` with carried q, exactly as `x_query`.
- At **every** boundary, the teacher's own connector: the pre-checks, then `_transit` to q_ref with the reference gap.
- The next relocation starts from q_ref.

`replay_xb` re-certifies:
- every relocation, in the scene it faces;
- every connector: continuity, free and open gap, joint limits, per-segment certification, clear endpoint, ends at q_ref;
- that connectors sit exactly at the declared boundaries.

`y_temp(A, d)` takes one of two paths:
- for `(t0, goal)`: production `bd_2d.t_goal`;
- otherwise: the same code path as `Physics._goal`, with the target and goal parameterized.

**Reference labeller:** TT_ADAPTER_V1 plus the unchanged `bxy_teacher.y_query`.

### 3.2 Results

| Fixture | Result |
|---|---|
| `x_chunked(bounds={m})` vs production `x_query` (fresh caches) | 3/3 identical X and witness ids |
| Generic goal (production key) vs `bd_2d.t_goal` | 3/3 identical Y and witness |
| Chunked (1,1) + endpoint Y | **2/3** X = 1, replayed. **1/3 X = 0: UNKNOWN_TRANSIT at boundary 1** (the bounded RRT connector to q_ref was not found within `transit_plans`). Endpoint Y = 1 in all 3. |
| Inner connector removed (negative fixture) | 2/2 refused ("move 1: discontinuous robot state") |
| Temporary target, 2nd action, at S0 and after the 1st | 6/6 feasible. **No blocked case** among these 3 roots. The blocked-parent contract is covered by C3b (39 blocked 2D cases). |
| TT_ADAPTER_V1 vs direct path | Labels 6/6; witness ids 4/6 identical. The 2 that differ are on one root, where planner keys differ by construction; both are VERIFIED and replayed, consistent with the TT RNG-key noise floor. |
| Rejections (0 planner calls) | All 6 fire: original-target mover; duplicate object; illegal destination; fixed mover; fixed temporary target; occupied temporary goal. The fixed-object case uses a **declared synthetic copy** of a TRAIN root with one obstacle marked fixed: none of the 2D TRAIN roots available on gvlab2 has fixed objects, and other splits were not opened. |

The joint-space records are in `figures/R1_2d_home_returns.png`, including the failed connector.

### 3.3 Reading

- The chunked 2D mode is mechanically correct.
- An intermediate q_ref return is **not free** in 2D: the budgeted transit can fail where the continuous plan succeeds. Under the amendment this is a legitimate connector-mode outcome, not an adapter error, and it is labelled as such.
- **R2 must measure** the chunked-vs-continuous success rate before trusting E_home's preference for chunking (Section 1.5).

## 4. Figures (`reports/figures/`)

| File | What it is |
|---|---|
| `R1_fig3_synthetic.png` | **SYNTHETIC**: recursion tree, dependency-preserving composition and DP chunk boundaries for the literal Fig. 3 example (declared fake scorer). |
| `R1_3d_home_returns.png` | **ACTUAL** MuJoCo-executed teacher witnesses in joint space: chunked (2,2) and local paired (3,1), with the planned connectors to q_ready. Not a render. |
| `R1_2d_home_returns.png` | **ACTUAL** geometry-certified 2D teacher records in joint space, with connectors to q_ref and the failed connector. Not a simulator render. |

## 5. Resources and storage

| | Authorized | Used |
|---|---|---|
| GPU (gvlab2 RTX 5090) | 0.3 GPU-h | ≈ 0.06 GPU-h (3 runs, ≈ 203 s wall, plus test runs) |
| 3D teacher | 20 jobs / 1 CPU-h | 19 jobs / 0.059 CPU-h. One earlier launch aborted on a pickling error before dispatch: 0 jobs. |
| 2D teacher | 30 jobs / 2 CPU-h | 30 teacher queries (23 job records) / 0.029 CPU-h, plus 1 zero-query rejection fixture |
| Concurrent physical workers | ≤ 8 | 8 (4 3D + 4 2D) |
| Storage | ≤ 5 GiB, keep ≥ 20 GiB free | 23 MB under `naren_workspace/fig3`; gvlab2 /home has 34 GB free |
| Hosts | gvlab2 | gvlab2 only. No laptop compute, no enigma, gvlab unused. |

## 6. Public/private boundary

- **Inference modules** read PUBLIC rows and the bundle only. An AST test rejects teacher, evaluator and private imports.
- **Committed outputs:** per-fixture summaries only (`R1_2D.json`, `R1_3D.json`).
- **Kept private (not committed):** raw per-query records, witnesses and trajectories. They live in `~/k45_private/fig3_R1` and `gvlab2:naren_workspace/fig3`.

## 7. Remaining blockers and risks

1. **2D intermediate connectors** fail on some chunk splits (1/3 in the smoke). The chunked-vs-continuous rate is unknown.
2. **3D intermediate-scene cVAE recall drop** (C4, −10 pp) directly affects R-FIG3's re-queries.
3. **Y_τ calibration** on reassigned tasks is poor (C3). This is why admission is relative; R-GATED's absolute gates inherit the problem.
4. **Temporary-target X for enablers** uses the original-task relocation certificates (`DetPhysics.edges`), exactly as in production. This is declared, not changed.
5. The 2D connector checker uses the free-robot ('start', False) world with the object argument `t0`, exactly as in production. It was exercised only with free-arm connectors.

## 8. Proposed R2 (requires owner approval; not started)

The two domains run independently. Each has its own gate and a lineage-disjoint confirmation cohort.

### 2D (run first, or in parallel)

- **Reuse without new collection:** the C3/C3b TT artifacts (`gvlab2:naren_workspace/k3val/runs/out/ttarget`; 49 C3b examples, 39 blocked). They serve as matched parent before/after and nuisance/omission fixtures under an identical Y contract.
- **New collection:**
  - **R2-2D-A, connector rate:** 60 exposed TRAIN/VAL K2–K3 verified sequences × {continuous, every chunk split}. About 300 X queries.
  - **R2-2D-B, local ordered ranking:** R-FIG3 / F-FLAT / R-GATED on 60 non-TEST roots with verified short contexts. About 400 X + 150 Y queries.
  - **R2-2D-C, bounded longer-repair witnesses:** only where (A) and (B) leave a K4–K6 gap; at most 40 roots and 200 queries.
- **Request:** ≤ 1,050 teacher queries, ≤ 8 CPU-h, ≤ 16 workers, ≤ 0.5 GPU-h, ≤ 2 GiB.

### 3D

- **Reuse:** C3b 3D (22 blocked) and the 20 K4/K5 cohort witnesses.
- **New collection:**
  - **R2-3D-A, connector rate:** 20 cohort roots × 3 partitions. About 60 X jobs.
  - **R2-3D-B:** R-FIG3 / F-FLAT / R-GATED plans physically verified on the 20 cohort roots plus 20 new non-TEST K4/K5 roots from the existing generator. About 120 jobs.
  - **R2-3D-C, intermediate-scene recall audit:** model-only; no teacher calls.
- **Request:** ≤ 200 teacher jobs, ≤ 10 CPU-h, ≤ 16 workers, ≤ 0.5 GPU-h, ≤ 3 GiB. The generation of the 20 new roots needs a separate budget line: ≤ 40 CPU-h at the historical K45 yield.

### Gates (per domain, preregistered before running)

1. **Connector rate:** chunked success ≥ 0.9 × continuous success on the same sequences. Otherwise E_home must be refit to the measured connector rates before R3.
2. **R-FIG3 vs F-FLAT:** a paired verified-success difference with a CI on the confirmation cohort.

**STOP.** R2 is not started, nothing was trained, TEST was not touched, and nothing was merged.
