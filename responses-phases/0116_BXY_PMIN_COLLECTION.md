# 0116 — BXY-P-MIN-COLLECT: bounded physical X/Y collection of `PMIN_DEV_MATCHED`

Date: 2026-10-31. Gate: BXY-P-MIN-COLLECT only. Authority: `Approach_B_Final_Methodology_2026-10-31.pdf`; frozen plan from 0115.

**Verdict: `READY_FOR_TRAINING_DESIGN`.**
- The whole frozen design was collected within every authorized limit.
- Every query is observed: 0 censored, 0 not attempted, 0 corrupt.
- Every positive witness was independently re-verified.
- All four X/Y outcome cells are populated.

This is supervision data only. **No model was trained, no selector was tuned, and no test data was touched.** Nothing here supports any
coupling or selection claim.

**Contract note.** The instruction message names `BXY_PMIN_COLLECT_CLAUDE_OPUS_5_5_HIGH_PROMPT.md` as the binding contract. That file
does not exist anywhere on this machine (filesystem search). The instruction message itself was detailed and self-contained, so it was
followed as the contract. If the named file carries extra requirements, they were not seen.

---

## 1. Provenance

**Commits:**

| commit | content |
|---|---|
| start HEAD `f429219b9` | 0115, the frozen plan |
| `de3fee687` | runner `bxy_pmin_collect.py` and fault-injection tests (pre-launch) |
| `1c46bac3e` | execution authorization manifest, committed before launch |
| the commit adding this report | sidecar, evidence, figures, report |

**Hashes:**

| object | sha256 |
|---|---|
| `PMIN_DESIGN.json` (frozen, unchanged) | `8f164845e5804821b8fbf9411c52ca2584f22d6f6f4a0efd19b8c3bcb86ff658` |
| `PMIN_LOCK.json` (unchanged; its historical `authorized: false` flag was **not** edited) | `4d42027e8c111e49557a68c9e128d0359918dd6032dcf8431fd051c044dfffaa` |
| lock semantic source set (114 files) | `812e0cff49fc587779e36e12f7a6faefea789667abca3b66cdbb8af932865f6e` |
| `AUTHORIZATION_COLLECT_V1.json` (separate, versioned) | `9689f43781933e08ab8270fbcc9a0fc24e72a82bd27efbd1cb55358cd7884944` |
| runner `bxy_pmin_collect.py` (`BXY_PMIN_COLLECT_V1`) | `78b85a121f3d051ecfc6090a1da6b0d0fc960ae2ebb3d24f8f83744aac049462` |
| teacher (`BXY_X_TEACHER_V1` / `BXY_Y_TEACHER_V1`; the same hash as P9, so P9 reuse is valid) | `4930754123e6905619b5e34ae450c8e78599643460c03e6cd0ce11393ea0a4fe` |
| dataset BD_GEN_V1 (live, read-only) | `78ca0e7c35d5a2b937554c03ce38b06db2486e5d74af5f2831e37e335ccb1a38` |
| P9 sidecar (unchanged) | `adea6983f1303236b05c41b5755652d0b05dab808dff2951df07a8c26ca2f840` |
| robot profile | `2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858` |
| **`BXY_SIDECAR_V2_PMIN.json`** (immutable) | `0191f49bc165cf21b33246855f7e8a788a17fd74b187eb120d31548c4176cd7e` |

**Per-query budget.** The teacher budget `bd_2d.QB` = {motion_checks 150, online_moves 8, goal_plans 3, transit_plans 6} was unchanged
and checked in preflight.

## 2. Collector and preflight

`bxy_pmin_collect.py` is new and separately hashed. None of the 114 locked sources was modified, including `bxy_pmin.py`; the collector
reuses `assert_frozen`, `admitted`, `y_query_counted` and `checkpoint` from it.

**Preflight.** The run refuses to start unless every check below passes; it passed against git immediately before launch.
1. The frozen design and lock are intact, there is no source drift, and both are committed and clean.
2. The design sha equals `8f164845…`.
3. The authorization manifest exists and its limits, design, lock and runner hashes match. Its executing commit is an ancestor of HEAD,
   and both the runner and the manifest are committed and clean.
4. The live dataset hash, P9 sidecar hash, teacher hash, policy and QB match, and the robot profile equals P9's.
5. The worklist is exactly 2,165 X and 1,807 Y over 197 roots.
6. Every query passes design membership, F1 admissibility and key re-derivation from the root record (q_ref and context included).
7. No query is duplicated, all 116 reused P9 observations exist with the same teacher hash, and none is scheduled again.

**Collection controls:**

| control | behaviour |
|---|---|
| process model | one worker process per root |
| query order | frozen design order (X before Y, by key) |
| writes | atomic per-query JSON with an `.inprogress` marker |
| CPU caps | `RLIMIT_CPU` per root = min(3,300 − the root's spend, 64,000 − spent − reservations), enforced from the first worker; aggregate accounting from `os.wait4` rusage |
| wall cap | measured from the first launch, across resumes |
| ramp | 2 → 4 → 8 workers, gated on free memory and external load |
| early stop | the after-20-roots projection checkpoint, in addition to the hard caps |
| interruption | SIGTERM/SIGINT stops cleanly |
| interrupted queries | CENSORED, never 0 |
| never-started queries | NOT_ATTEMPTED |
| lost workers | charged their full CPU allowance |

**Tests.** `tests/test_bxy_pmin_collect.py` has 10 tests covering these fault injections:
- missing authorization;
- runner and limit hash mismatches;
- dataset hash mismatch;
- source drift;
- a duplicate query;
- an immutable authorization;
- a worker crash mid-query, followed by deterministic resume that never re-runs a finished query;
- corrupt and identity-mismatched result files;
- RLIMIT CPU exhaustion;
- a hard aggregate cap from the first worker;
- wall-time expiry, global across resumes;
- SIGTERM interruption with resume;
- an orphaned worker;
- the projection checkpoint;
- the ramp schedule.

`tests/test_bxy_pmin_sidecar.py` has 4 tests: a tampered or missing witness is demoted to unobserved (never relabelled 0); a negative
must carry its failed phase; identity is re-checked; order and omission bookkeeping is correct.

| check | exit | result |
|---|---|---|
| pre-launch: `pytest tests/test_bxy_pmin_collect.py tests/test_bxy_p10.py tests/test_bxy_teacher.py tests/test_bxy.py` | 0 | 51 passed |
| pre-launch: 6 archived replays (`run.py replay` on `g1_robot`, `g1_hardening`, `g2_interventions`, `g3_repairs`, `g3_5_initial_scene`, `g4a_evidence_audit`) | 0 × 6 | `replay_passed: true` × 6 (`collect_preflight/`) |
| post-collection: those 4 suites + `tests/test_bxy_pmin_sidecar.py` | 0 | 55 passed (`collect_final/pytest_bxy.log`) |
| post-collection: `bxy_pmin.assert_frozen()` | ok | design `8f164845…` |

## 3. Collection: what actually ran

| resource | authorized ceiling | used |
|---|---|---|
| aggregate worker CPU (RUSAGE) | 64,000 CPU-s | **32,157 CPU-s** (50%) |
| largest per-root CPU | 3,300 CPU-s | 2,331 (s029, K1); next are 1,545 (s270) and 1,536 (s014) |
| concurrent workers | 8 | 2 → 3 at 5.3 min → 8 from 10.1 min (fig. 03) |
| collection wall time | 13,800 s | **5,631 s** (94 min) |
| roots | 197 | 197 finished, all with exit code 0 |
| new X queries | 2,165 | 2,165 attempted, 2,165 observed |
| new Y queries | 1,807 | 1,807 attempted, 1,807 observed |
| reused P9 observations | — | 57 X + 59 Y (not re-run) |
| censored / not attempted / corrupt | — | **0 / 0 / 0** |

**Run behaviour:**
- **Projection checkpoint:** never triggered.
- **Peak worker memory:** 149 MB.
- **CPU split:** X queries 11,413 CPU-s and Y queries 20,089 CPU-s; the rest is process start-up.
- **Cost of a Y failure:** a failing Y averages 44.5 CPU-s against 4.1 for a success, because budget-limited failures exhaust the planner.
- **Tail:** the last 25 minutes ran at 1–2 workers on the heaviest roots.
- **Verification:** the independent re-verification while building the sidecar took 531 CPU-s on top of the collection, and is not
  part of the teacher budget.

## 4. Verification of the sidecar (`bxy_pmin_sidecar.py`)

Every row was checked as follows:
- the key is re-derived from the immutable root record (ordered X key, order-free endpoint Y key, q_ref and context hash);
- the row is F1-admissible and a member of the frozen phase;
- **every positive** is re-certified from the stored witness files: `replay_x` for the relocations and connector, `replay_y` for the
  target from q_ref;
- every negative carries a failed phase and a negative kind;
- a positive that fails re-verification is demoted to unobserved, never relabelled 0.

| outcome | count |
|---|---|
| positives re-verified | **3,253 of 3,253** (1,732 X + 1,521 Y) |
| verification failures | 0 |
| duplicate rows | 0 |
| mixed teacher hashes | none |
| witness stitches failed while computing J_total | 0 |

**Agreement with history:**
- **Y:** 661 of 661 Y queries that have a historical target-from-q0 label agree with it.
- **Relocation records:** 972 X rows have historical records for the same prefix.
  - 250 are byte-identical and 707 agree to within 1e-12.
  - 15 rows (8 roots) differ in exactly one relocation record, by a single waypoint in its dense path, with an **identical end
    configuration** (difference 0.0); every other record matches.
  - The relocation outcome equals the historical one in all 15. This is a cross-machine floating-point path-discretization effect, not a
    policy difference.

## 5. Results

### Labels

**X:** 2,222 observed; 1,732 X=1 and 490 X=0.

| X=0 kind | count |
|---|---|
| relocation, certified (`CERTIFIED_INFEASIBLE`) | 162 |
| relocation, planner budget (`UNKNOWN_PLANNER`) | 286 |
| connector, transit planner budget (`UNKNOWN_TRANSIT`) | 42 |

The first failing step: relocation 0 240, relocation 1 127, relocation 2 60, relocation 3 14, relocation 4 6, relocation 5 1, connector 42.

**Y:** 1,866 observed; 1,521 Y=1 and 345 Y=0 (64 certified, 281 planner budget).

**Connector:**
- Of 1,774 prefixes whose relocations all completed, 1,732 got a verified, re-certified connector to q_ref (97.6%): 576 direct, 1,156
  planned.
- The 42 failures are all transit-planner budget failures (no certificate), so they are policy failures, not proven impossibility.

**X by prefix length:**

| length | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| X=1 / n | 503/556 | 620/756 | 432/600 | 140/242 | 33/60 | 4/8 |
| rate | .905 | .820 | .720 | .579 | .550 | .50 |

**By stratum:**

| stratum | X=1 / n (rate) | Y=1 / n (rate) |
|---|---|---|
| K0 | 1226/1596 (.768) | 1258/1331 (.945) |
| K1 | 289/332 (.870) | 193/304 (.635) |
| K≥2 | 136/185 (.735) | 57/146 (.390) |
| None | 81/109 (.743) | 13/85 (.153) |

**Y0** (the original target from q0, empty edit): 142 of 197 succeed.

### Matched pairs (all 2,222 X have their Y decided)

| | Y=1 | Y=0 |
|---|---|---|
| **X=1** | **1,452** (full joint success) | 280 |
| **X=0** | 415 | **75** |

There are 185 roots with at least one pair; the other 12 roots have only a Y0 query in this phase. By query class (fig. 02):

| class | (1,1) | (1,0) | (0,1) | (0,0) |
|---|---|---|---|---|
| complete | 646 | 112 | 150 | 21 |
| reversal | 348 | 40 | 123 | 17 |
| omission | 853 | 197 | 235 | 49 |

K≥2 gives 57 / 79 / 35 / 14 (in the same order); None gives 8 / 73 / 13 / 15.

The P9 pilot's empty (0,0) cell, and its overall imbalance, came from P9's outcome-guided item choice. Full enumeration of the frozen
design removes both.

### Order contrasts: same endpoint, so one shared Y node

- 551 groups have two or more decided orders: 354 all X=1, 84 all X=0, and **113 discordant** (across 62 roots).
- The 113 discordant groups contain 113 failing orders:

| failing order | count | detail |
|---|---|---|
| certified | 24 | all `ORDER_FIRST_ACTION`: a geometric certificate that the relocation cannot begin in the scene left by the earlier actions |
| relocation planner budget | 68 | — |
| connector planner budget | 21 | — |

  Failing phase over all 113 failing orders: relocation 0: 37, relocation 1: 26, relocation 2: 21, relocations 3–5: 8, connector: 21.

- Only the 24 certified groups are claimed as geometry-forced order effects. The other 89 are order effects of the fixed, budgeted
  greedy teacher policy (methodology §9: "X is a budgeted-existence statement under a fixed policy").
- Example (fig. 05, s001): `o00>23, o02>31, o01>3` gives X=1, while `o01>3, o02>31, o00>23` fails at relocation 2 with
  `ORDER_FIRST_ACTION`. The shared Y is 1.

### Omission contrasts (recomputed from S0; Y deduplicated by endpoint)

**X transitions** (full prefix → omitted-action prefix):

| transition | count | meaning |
|---|---|---|
| 1 → 1 | 1,041 | — |
| 1 → 0 | 47 | removing an action made the remaining prefix fail: the omitted action enabled a later one |
| 0 → 1 | 151 | — |
| 0 → 0 | 262 | — |

**Y transitions** (full endpoint → omitted endpoint):

| transition | count | meaning |
|---|---|---|
| 1 → 0 | 131 | the omitted relocation was needed for the target in the edited scene |
| 1 → 1 | 1,007 | — |
| 0 → 1 | 34 | the omitted relocation itself obstructed the target |
| 0 → 0 | 114 | — |

**Two-move interaction.** For 2-move candidates, the interaction is Y_AB − Y_A − Y_B + Y_0, over 200 distinct edited scenes with all
four Y observed:

| pattern | count |
|---|---|
| additive (0) | 171, of which 125 are the trivial all-1 case (the target is already feasible from q0) |
| +1 | 15 |
| −1 | 13 |
| −2 | 1 |

The informative patterns:
- **Strict "both needed"** (1, 0, 0, 0): 9 scenes. Only 1 is fully certified; in 7, all three zeros are planner-budget failures.
  Fig. 06 (s261) is one of the budget-limited cases.
- **"Either suffices"** (1, 1, 1, 0): 10 scenes.
- **(0, 1, 1, 0)**: 1 scene. Each move alone clears T, but the two together re-block it.

These are operational-label contrasts, not certified causal necessities.

### Complete-witness travel (1,452 full joint successes)

J is range-normalized, unwrapped L1 joint travel over the stitched relocations, connector and target from q_ref.

| component | mean | median |
|---|---|---|
| J_total | 4.82 | 4.57 |
| relocations | 2.24 | 1.84 |
| connector | 0.93 | 0.92 |
| target | 1.65 | 1.38 |

- The connector's median share of J_total is 0.196.
- `J_total` equals the sum of its parts exactly (largest gap 0.0).
- By number of moves m, the mean J_total is: 1 → 3.51, 2 → 4.52, 3 → 5.87, 4 → 6.59, 5 → 8.10, 6 → 7.19 (n = 3).
- **No-op complete witness:** for the 142 successful Y0 queries, the target-only travel has mean 1.50, range 0.33–4.80. This supervises
  the 0115 complete-travel convention.

## 6. Figures (from the stored, re-verified witnesses and the ledger)

All are in `visualizations/approach_b/bxy_pmin_v1/`:
- `01_coverage.png`: X and Y outcome class (1 / certified 0 / budget 0 / censored / not attempted) by K stratum and prefix length.
- `02_four_cell.png`: matched (X, Y) pairs overall and per class.
- `03_cpu_and_workers.png`: per-root CPU against the 3,300 cap, cumulative CPU against the 64,000 cap, and the 2 → 4 → 8 ramp.
- `04_travel.png`: the complete-witness travel decomposition by m (no-op included) and the connector share.
- `05_order_effect_s001.png`: the certified `ORDER_FIRST_ACTION` contrast with the shared Y.
- `06_omission_s261.png`: the two-move interaction (budget-limited single-edit zeros, disclosed in the title context).
- `07_failed_attempts.png`: a connector failure after two completed relocations, and a certified Y failure.
- `08_full_joint_witness_s196_m6.gif`: a complete 6-relocation, connector and target witness.

## 7. Deviations and limitations

1. **Missing contract file** (see the header).
2. **Ramp gating.** The ramp is gated on finished roots plus free memory and load. Reaching 8 workers took 10 minutes, and the last 25
   minutes ran at 1–2 workers on heavy roots. This affected wall time only, not labels.
3. **Budget-limited zeros dominate.** 286 + 42 X=0 and 281 Y=0 are budget-limited. They are correct operational labels under the binary
   contract, but not impossibility. Any analysis claiming geometric necessity must use only the certified subset.
4. **Greedy teacher.** X is the fixed greedy policy (`best_edge`). Order effects beyond the 24 certified ones are policy-relative.
5. **K≥2 is scarce.** There are only 9 K≥2 roots (185 X, 146 Y), and K3/K4 scenes are effectively absent. The 34 historical test roots
   are excluded and remain historically exposed, so **there is no fresh independent evaluation set**. Both need new generation gates.
6. **Unlabelled queries.** Proper prefixes (`PREFIX_COMPLETE`) remain unobserved and marginalized. The F1-screened queries (48 X, 31 Y)
   are never labelled.
7. **Re-planning drift.** 15 historical relocation records re-plan with a one-waypoint dense-path difference, with the same endpoint and
   outcome (§4).
8. **Pilot rows lack class labels.** P9-reused rows carry no query-class field; the analysis takes classes from the frozen design. The
   immutable sidecar was not rewritten for this.

## 8. Verdict and next stage

**`READY_FOR_TRAINING_DESIGN`.** The evidence is complete, matched and independently verified:
- 2,222 X and 1,866 Y with every X's Y decided;
- all four cells populated;
- 113 order contrasts (24 certified);
- 200 omission interaction scenes;
- 1,452 complete travel witnesses, plus 142 no-op witnesses.

**Next gate (not started):** a training-design gate. It should:
1. freeze a root-grouped train/validation use of `BXY_SIDECAR_V2_PMIN` through `bxy_v2.views`;
2. freeze the XY-uncoupled / XY-quadratic / XY-quadratic-noJ arms with matched capacity;
3. separate certified from budget negatives in the evaluation analyses;
4. pre-register the selection metrics;
5. plan the fresh, independently generated test cohort and the K≥2 generation needed for a decisive claim.

**STOP.** `PREFIX_COMPLETE`, P-full, training, tuning, test evaluation, scene generation and 3D were not started.
