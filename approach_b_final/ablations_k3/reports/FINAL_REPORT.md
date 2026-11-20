# Approach B K≤3 ablation study: final report (P7)

| | |
|---|---|
| Branch | `naren/k3-ablation-gvlab2-20261120` (base `c72eb1ef75`) |
| Host | gvlab2 only (`taskset 0-42`: 43 of 48 CPUs, 5 always reserved) + RTX 5090 |
| Data | Frozen original snapshot `abf_9de85710c2a7103f` (2D 3,500/751/749; 3D 1,766/364/370) and expanded TRAIN snapshot `abf_v32_fb0eef4f5ff433ee` |
| Excluded | The V3.4 independent cohort (no root, label or prediction touched) |
| Not done | No counterfactual experiments, no K>3 work, no retraining of FULL |

**TEST caveat.** The historical TEST split was consulted during earlier development. It is **not a pristine hold-out**, and every TEST number below should be read with that in mind.

Earlier reports: `P0_P3_REPORT.md` covers sources, parity, the pilot and training. Machine-readable artifacts are in `manifests/`, `tables/`, `figures/`, `val/` and `test/`.

## 1. Protocol actually executed

**Reference (FULL)** = the frozen V3.4 bundle:
- scratch `TaskCVAE(scratch_all)` s0, with D scorer s0 (s1/s2 for stability);
- S1 proposals: 64 draws, top-4 destinations per object;
- every legal K1–K3 ordered sequence, with no cap;
- frozen rule: NOOP gate 0.5, η 0.3, α = β = γ = 0.

**FULL parity on gvlab2:**

| Domain | Proposals | Candidate counts | Decisions | max \|Δp11\| |
|---|---|---|---|---|
| 2D | 751/751 identical | 751/751 identical | 751/751 identical | 4.8e-7 |
| 3D | 364/364 identical | 364/364 identical | 364/364 identical | 3.0e-7 |

**Arms** (30 per domain):

| Arm | Change | Training |
|---|---|---|
| FULL s0/s1/s2 | — (frozen) | none |
| E s0–2 | X/Y coupling removed | matched D procedure, expanded TRAIN |
| G s0–2 | order-invariant scorer | same |
| DIRECT s0–2 | Z = X∧Y classifier | same |
| DREFIT s0–2 | *diagnostic only:* D refit in this environment | same |
| Uniform4 r0–2 | analytical proposals (4 distinct legal cells, seeded) | none |
| TaskFM s0–2 | task-conditioned flow matching | same examples, weights, steps, optimizer |
| NoTask s0–2 | scratch_all with the task-context branch zeroed | identical init and budget |
| SAMPREF s1/s2 | existing scratch_all sampler seeds (reference) | — |
| M1 | top-1 destination per object, still combinatorial search | none |
| C1 r0–2 | one label-blind complete candidate + NOOP | none |

**Fairness, enforced and checked:**
- Every scorer arm scored the **identical per-root candidate pool** as FULL: the pool-hash check passes 30/30 on VAL.
- Every sampler arm used the frozen D s0 scorer and the same selector.
- G gives identical scores within one endpoint: a P1 test checks this, and its order ranking is exactly 50% by ties.
- The DIRECT, E, G and DREFIT fits used the same expanded TRAIN snapshot, the `xy.fit` defaults of the frozen D, and VAL-only checkpoint selection.

**Verification:**
- Every prediction file was SEALED, and the protocol was LOCKED for VAL and later for TEST, **before any teacher call** on that split.
- Every unique selected (root, ordered sequence) was taught once through the unchanged finalized teachers (V3.4 harness, 2D BXY, 3D fin3d / MuJoCo 3.16), with independent replay and one shared cache.

| Split | 2D unique queries | 3D unique queries |
|---|---|---|
| VAL | 8,610 | 3,719 |
| TEST | union per `test/TEACH_LOG_*` | union per `test/TEACH_LOG_*` |

- **0 UNKNOWN, INVALID or MISSING outcomes in all 120 arm × split × domain result files.**

## 2. Main result: physically verified task success (K1–K3), paired vs FULL

These are pooled paired differences (seed-matched for scorer arms; vs FULL s0 for sampler and search arms), from a lineage-clustered bootstrap (2,000 resamples, seed 0). Points are percentage points.

| Arm vs FULL | VAL 2D | VAL 3D | TEST 2D | TEST 3D | Supported reading |
|---|---|---|---|---|---|
| **G (order-invariant)** | −6.8 [−10.0, −3.7] | −14.4 [−19.7, −8.8] | −4.5 [−7.7, −1.4] | −18.8 [−23.5, −14.1] | **Order sensitivity is needed**; the largest losses are on K3 |
| **DIRECT** | −10.9 [−14.2, −7.8] | −12.4 [−16.8, −8.2] | −13.3 [−16.4, −10.1] | −10.8 [−14.7, −7.0] | **Factorized X/Y beats a direct Z classifier** under the frozen rule (see §4) |
| E (no X/Y coupling) | +1.4 [−1.1, 3.8] | −4.2 [−7.0, −1.5] | −2.4 [−5.0, 0.0] | +2.8 [−0.1, 5.7] | **No robust effect**: the sign flips between VAL and TEST in both domains |
| **Uniform4** | −18.0 [−22.5, −13.6] | −17.9 [−23.3, −12.6] | −17.9 [−22.1, −13.8] | −18.9 [−23.9, −14.0] | **Learned placement is essential** |
| **TaskFM** | −8.4 [−12.5, −4.4] | −7.6 [−12.7, −2.6] | −8.0 [−12.0, −4.1] | −7.3 [−12.0, −2.6] | **cVAE beats a matched task-conditioned FM** |
| No task context | −0.9 [−4.4, 2.3] | +0.8 [−3.0, 4.7] | −1.5 [−4.6, 1.7] | −1.1 [−4.7, 2.6] | **No detectable effect** of the explicit task branch |
| **M1** | −27.4 [−32.9, −22.3] | −6.4 [−12.3, 0.0] | −21.8 [−26.9, −16.8] | −13.3 [−19.5, −7.0] | **Destination diversity matters**, much more in 2D |
| **C1** | −49.4 [−54.2, −44.5] | −60.6 [−66.5, −54.9] | −44.8 [−49.6, −40.1] | −66.5 [−72.1, −61.1] | **Search over the candidate pool is essential** |
| D refit (environment control) | +0.4 [−1.4, 2.3] | −1.7 [−3.8, 0.5] | −0.7 [−2.8, 1.2] | +2.1 [−0.4, 4.6] | **The training environment does not matter** |

**FULL s0 absolute task success** (K1–K3, [95% CI]):

| | 2D | 3D |
|---|---|---|
| VAL | 57.1 [52.5, 61.7] | 78.2 [72.7, 83.6] |
| TEST | 52.9 [48.1, 57.8] | 82.2 [77.2, 86.7] |

Both VAL figures reproduce the historical frozen-system numbers. Per-arm, per-seed, per-K, NOOP and ABSTAIN tables are in `tables/physical_{val,test}_{2d,3d}.json`, and plots in `figures/F2_*`.

**Other outcomes:**
- **NOOP on K0** is essentially unchanged across arms: 2D VAL about 97%, TEST about 90%; 3D 83–89%. The exceptions are G 3D TEST s0, at 62.7, and DIRECT.
- **ABSTAIN on NONE is the main side effect:**
  - DIRECT abstains on only 8–55% (2D) and 22–38% (3D) of NONE roots, vs 82–96% for FULL.
  - E abstains *more* in 3D VAL (93–95% vs about 79%).

## 3. Mechanism diagnostics

**Placement** (`tables/placement_*`, `figures/F1_*`):

| | Ingredient recall, 2D VAL/TEST | 3D VAL/TEST |
|---|---|---|
| FULL (cVAE) | 0.50 / 0.51 | 0.75 / 0.76 |
| No task context | ~0.50 | ~0.73 |
| TaskFM | 0.27–0.29 | 0.46–0.51 |
| Uniform4 | 0.08 | 0.13–0.15 |

- A known successful assignment lies fully in the pool for 27–29% (2D) and 61% (3D) of roots under FULL, vs 2–4% under Uniform4.
- The placement loss explains the sampler-arm losses in §2.
- Uniform4 scores *more* candidates per root (2D about 86k vs 51k), because it rarely repeats cells across objects, yet it does far worse.

**Scorer quality**, teacher-free, frozen labels, seed means (`tables/scorer_*`, `figures/F3_*`):

| | 2D TEST: Z NLL / AUROC / order | 3D TEST: Z NLL / AUROC / order |
|---|---|---|
| D (FULL) | 0.650 / 0.767 / 0.767 | 0.424 / 0.896 / 0.877 |
| E | 0.652 / 0.765 / 0.790 | 0.430 / 0.890 / 0.878 |
| G | 0.681 / 0.695 / 0.500 | 0.504 / 0.842 / 0.500 |
| DIRECT | 0.519 / 0.826 / 0.746 | 0.415 / 0.897 / 0.866 |

"Order" is **same-endpoint finalized-X ranking**. It mixes geometric, robot-state, planner and connector effects, and is **not** a handoff-only metric.

## 4. Interpretation and limits

**1. DIRECT has the best success-event calibration but the worst decisions.**
- It loses 11–13 points of physical task success and largely stops abstaining.
- The frozen rule (NOOP gate 0.5, η 0.3) was set for D's factorized p11 scale, and was deliberately **not re-tuned**.
- So this tests "DIRECT under the registered rule", not DIRECT under its own best threshold.

**2. Coupling (E) has no reliable effect on task success.** VAL and TEST disagree in sign in both domains. "Coupling helps in 3D" is not supported.

**3. Order invariance (G) and placement quality** (Uniform4, TaskFM, M1) are the robust, replicated ablation effects, together with search breadth (C1).

**4. Removing the explicit task-context branch** worsens the cVAE's VAL ELBO but has no detectable effect on physical success. Target cues remain visible in the geometry branch.

**5. Other scope notes:**
- TEST is historically exposed.
- The bootstrap is lineage-clustered (`layout_root_id`). Multiple comparisons are not corrected; treat borderline cells as such.
- The other user's GPU jobs caused two out-of-memory crashes during TEST prediction. The resumable passes recovered both with no data loss.

## 5. Gates

| Gate | Result |
|---|---|
| G0 (P0, 21 checks) | PASS |
| G1: FULL parity exact; P1 tests | PASS (25/25) |
| G2: matched fits | PASS (pipeline reproduction: sampler bit-identical; D within ±0.03 VAL NLL) |
| G3: identical pools for scorer arms; sealed before TEST | PASS (30/30) |
| G4: each unique query taught once; no retry; UNKNOWN never coerced | PASS (0 UNKNOWN) |
| G5: all roots accounted for; masks; no V3.4 contamination | PASS |
| G6: manifests and hashes; frozen data and checkpoints unchanged | PASS (sha vs lock) |

## 6. Compute

**CPU:** all ablation processes were pinned to 43 of 48 CPUs.

**GPU** (RTX 5090): at most 16 concurrent scoring processes, about 1.4–1.9 GB each. Concurrency was reduced to 10 after another user's jobs appeared, so we never touched them.

**Training:** 38 fits, each 10–60 s.

**Inference:** for FULL-like arms, 2D median about 1.8 s per root and 3D about 0.1 s per root (`tables/placement_*` latency).

**Teacher verification wall time:**
- 2D VAL about 1.5 h, 3D VAL about 1 h;
- 2D TEST about 1.6 h, 3D TEST about 1.7 h;
- each run used 40 workers.
