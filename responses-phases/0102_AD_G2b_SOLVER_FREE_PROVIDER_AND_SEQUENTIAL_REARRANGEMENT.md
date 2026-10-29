# 0102 — Approach D G2b: solver-free precompiled provider and sequential rearrangement

**Authority:** `approachD_G2b_solver_free_provider_instructions_v1_2.md` (G2b only; on top of v1.1).
**Branch:** `approach-d-v1` (local, not pushed).
**Chain:** `027fb7f` → G1 `df913ae` → G2a `4b8aa2c` → this commit.
**Scope:** development data only. The following were **not** done:
- D training or relabelling;
- a board-wide catalog;
- the 442-query held-out benchmark;
- any start on G2c.

## 0. Verdict

**G2b: PASS** — see `runs/approach_d/g2b/G2B_GATE.json` and §9. All eight v1.2 §8 conditions hold.

**What passes:** one development root (`p13_2026216000`) is repaired end to end entirely from stored records, with zero runtime IK, planning or connector generation:
1. relocate o00;
2. relocate o01;
3. perform the **original target T** action.

Every step continues from the exact joint state the previous one left, and an independent replay re-certifies all 9 records.

**Within the finite library** (not a physical claim):
- both relocations are necessary;
- six earlier candidates in the declared list fail, each with an isolated, recorded cause.

**What does not hold up:**
- **Coverage is thin.** 1 of 12 declared fixtures completes, and only under the policy that adds the generic offline-catalog tier.
- **Ranking signal is absent within the relative tier.** On the 36-query pilot, 3×3/4×4 ranking does not beat geometry-only or random ordering inside that tier. The relative tier's gain over exact-cell-only comes from *which templates exist*, not from the ranking.

## 1. G2a verified on the working tree (before any change)

| check | result |
|---|---|
| HEAD / branch | `4b8aa2c` on `approach-d-v1`; only the user's two deleted root PDFs differ (untracked files untouched) |
| fresh regression at `4b8aa2c` (`runs/approach_d/g2b/g2a_verify/`) | **525 passed, 0 failed**, 6/6 archived replays clean (809 s) |
| G2a pilot re-check from the **frozen** catalog (`REVERIFY.json`; no recompilation) | every G2a policy outcome on the 36 relocation + 24 target rows and every per-template verdict reproduced: **0 discrepancies**, 0 forbidden calls |
| catalog | hash `sha256:2908fd08…`, 1,073 templates (unchanged) |

**G2a statement corrected.** The anomalous root (§6) was *not* "constructed as obstructed": its P16 original label is `VERIFIED`, y = 1.

## 2. Finite robot-state graph (offline; `ad_compile.segment` / `build_graph`)

**Segmentation, no new motion.** Each validated home→home template is cut, at existing waypoints, into three pieces:
- **entry leg:** home → approach start (free arm);
- **core:** approach → close/attach → carry → release → **complete safe retreat**;
- **exit leg:** retreat end → home (free arm).

Pieces share bit-identical boundary waypoints, and concatenating them reproduces the record exactly for all 1,070 relocation/target templates. Every piece is re-validated in its compile fixture: `motion.check_record` + certification for the core, free-arm certification for the legs, and the exit leg with the disc at its destination. **0 rejected.**

**Graph** (`runs/approach_d/g2b/catalog/GRAPH.json`, hash `sha256:660b1a91…`, arrays `2a5f3db9…`, 7.4 MB):

| element | count | definition |
|---|---|---|
| nodes | 716 | exact float64 joint states (`qid` = sha256 of the bytes; **no tolerance clustering, no snapping**); open gripper, nothing attached |
| hubs | 4 | `q_home` + start strata S1, S2, S3 |
| actions | 1,119 | template cores (approach-start node → retreat-end node) for one absolute (src, dst) |
| connectors | 2,241 | 1,119 `ENTRY_LEG` + 1,119 `EXIT_LEG` (each template's own legs) + 3 `ROOT_ENTRY` (stratum → home, G2a) |

**No connector was synthesised for G2b.** Non-home states are the retreat-end nodes. The provider leaves the robot there after an action, and leaves only through a stored exit leg, or through another stored connector reaching the next action's start node.

**Graph-validation cost:** 71–82 CPU-s per build (two builds). No compile attempt was used for it.

## 3. `AD_PRECOMPILED` provider (`ad_provider.py`) and its zero-solver contract

**Interface:**
- `edges(cells, q, oid, dst)`;
- `goal(cells, q)` — the original target T only;
- `verify_plan(cells0, q0, steps)` — independent replay, cache bypassed;
- `stats()`;
- thin adapters `run_sequence` and `repair` (first SUCCESS over a declared finite candidate list; no optimality claim).

**Per move:**
1. exact node of the current q (else `NO_COMPATIBLE_Q`);
2. destination occupancy;
3. candidate actions for the absolute (src, dst) and footprint;
4. tiered order, via `Ranker`:
   - exact-cell-derived;
   - relative-family modes ranked by G1 on the current scene's patches (or geometry-only / random for ablation);
   - optionally the generic offline catalog;
5. for each candidate:
   - stored-connector path existence (pure graph lookup, ≤ 2 hops; else `NO_COMPATIBLE_CONNECTOR`, no certification spent);
   - optional prefilter;
   - exact certification of the frozen action in the current occupancy (counts against the 6-check budget);
   - certification of each connector on the path.

   The first fully clear candidate wins.

**Failure reasons:** `NO_TEMPLATE`, `NO_COMPATIBLE_Q`, `NO_COMPATIBLE_CONNECTOR`, `CONNECTOR_COLLISION`, `DESTINATION_OCCUPIED`, `PHASE_INCONSISTENT`, `SWEEP_PREFILTER_REJECT`, `COLLISION_CURRENT_SCENE`, `CHECK_BUDGET_EXHAUSTED`, `TARGET_TEMPLATE_UNAVAILABLE`, `TARGET_ACTION_COLLISION`, `SEQUENCE_DISCONTINUITY`, `REPLAY_REJECTED`. Outcomes are SUCCESS or FAILURE only; nothing reuses P17 `CERTIFIED_INFEASIBLE`.

**Cache:** the key is (provider version, graph hash, checker version, policy, budget, hops, prefilter, record id, full occupancy, object). There is one cache per provider instance, never shared across policies.

**Config:** `[provider]` in `approach_d.toml`, validated by `pv.pcfg`. An unknown key such as `online_fallback` is an error. `config.toml` is unchanged.

**Imports:** `ad_provider` imports only stdlib, numpy and `ad_runtime`.

**Forbidden-call audit:**
- 0 forbidden calls in every G2b runtime run: chains, necessity, anomaly conditions, 108 pilot provider runs (3 policies × 36 queries), and the 60-row re-verification.
- The goal path never reaches `p15_retarget.certified` / `ordered.certificates_for`; it is guarded.
- Tests inject a checker that secretly calls `geometry.ik` and confirm the guard trips.

## 4. Sequential rearrangement (12 development fixtures; `CHAINS.json`, `NECESSITY_F12.json`)

**Fixtures F01–F11** were declared before any G2b runtime result, from historical P16 dev labels (original target `CERTIFIED_INFEASIBLE` from the root's start q, listed sequence `VERIFIED` by the historical online pipeline; F11 = unrepaired control).

**F12 was redefined after pass 1, and this is documented.** Its pass-1 version was a candidate list on `p13_2026217000`, whose target pair has no certifiable stored action in any reachable state. Pass-1 diagnosis on `p13_2026216000` found:
- the target's stored core certifies in the original scene;
- but **every stored home-routed entry leg is blocked** by link 0 / gripper contact with o00 (cell 56) and o01 (cell 16), both next to the base.

F12's candidate destinations come from a **solver-free, scene + catalog-only rule**: P17 `slot_fn` proposals, keeping the two per mover that fall in the fewest stored sweeps (entry leg + core) of the target actions whose core certifies.

**Offline compile spent** (`COMPILE_LEDGER.json`; budget 120 attempts / 1,500 CPU-s):

| entry | attempts | CPU-s |
|---|---|---|
| 14 fixture relocation pairs (≤ 1 exact-cell, 2 best-supported relative modes, 1 branch-spread) | 56 | 85.8 |
| 5 F12-rule pairs | 7 | 4.4 |
| 4 annulus pairs, branch-spread K = 6 | 24 | 10.7 |
| anomaly offline diagnostic (`plan_skill` from q_initial) | 1 | 0.2 |
| **total** | **88** | **101** |

That produced 53 new templates. Target-T templates were reused from G2a.

**Results, start = the root's actual initial q, budget 6, prefilter OFF:**

| | EXACT+REL_6x1 | EXACT+REL_3x2 | EXACT+REL_6x1+CATALOG |
|---|---|---|---|
| fixtures accepted (to T) | 0/12 | 0/12 | **1/12 (F12)** |
| relocation steps accepted / attempted (all policies) | 38 / 56 | | |

**F12 accepted chain** (`G2b_chain_success.png`; 9 records; replay hash `eec8537ff32a4f1f`). Start at q_initial = S1:

| step | stored records | q nodes | action origin |
|---|---|---|---|
| o00 56 → 45 | `ROOT_ENTRY` S1→home, `ENTRY_LEG`, action | `39982c → 8b7659 (home) → 0f2788 → 4355d7` | DIRECT_OFFLINE (spread) |
| o01 16 → 36 | o00's `EXIT_LEG`, `ENTRY_LEG`, action | `4355d7 → home → de27ad → 31c997` | **FAMILY_RETARGET** (relative-family, cross-location) |
| t0 20 → 31 (original T) | o01's `EXIT_LEG`, `ENTRY_LEG`, target action | `31c997 → home → e8c330 → 57e8dd` | DIRECT_OFFLINE (order) |

- The robot ends at a non-home retreat node.
- Provider cost: 13 action and 17 connector certifications, 50 cache hits, 0.67 CPU-s over the whole candidate list.
- **Necessity (same policy):**

  | sequence | outcome |
  |---|---|
  | empty | FAILURE: target actions certify, connectors blocked |
  | o00 → 45 only | FAILURE at T |
  | o01 → 36 only | FAILURE at the relocation |
  | both | **SUCCESS** |

**Failed chains (isolated causes; `G2b_chain_failure.png` shows F03).** F03 is the historical sequence o00 → 59, o01 → 3:
- both relocations are accepted (exact-cell witnesses, stored root entry, exit and entry legs);
- the target then fails: `TARGET_ACTION_COLLISION`, `link1|o00` in the retreat phase, because o00 parked at 59 lies under the stored target action's arm path.

Failure taxonomy over the 36 fixture × policy runs:

| reason | runs |
|---|---|
| `COLLISION_CURRENT_SCENE` | 12 |
| `CHECK_BUDGET_EXHAUSTED` | 8 |
| `TARGET_ACTION_COLLISION` | 6 |
| `TARGET_TEMPLATE_UNAVAILABLE` | 4 |
| `CONNECTOR_COLLISION` | 3 |
| `NO_CANDIDATE_SEQUENCE_ACCEPTED` | 2 |

**Why the coverage is thin (measured, `ad_g2b` pass-1 table).** In 5 of the 7 fixture roots, **no stored target action certifies in any reachable occupancy state**. The 10–12 generic target templates per target pair, from G2a, all approach through the same neighbours. That is a library gap, not a provider failure, and it is the main G2c concern.

## 5. Controlled development comparison (36 G2a relocation queries, 25 roots; `ANALYSIS.json`, `PILOT_PROVIDER.json`)

**Setup.**
- **Universe:** the same frozen per-query universe of 892 (query, template) pairs: G2a exact-cell + relative-family + direct.
- **Budget:** ≤ 6 **exact certifications**, prefilter OFF.
- **Start and end:** start `q_home`. "Strict" = home→home (G2a contract); "relaxed" = end at the retreat node (entry leg + core).
- **Method:** the per-template verdict table is deterministic, so the policies are simulated from it exactly. The provider itself was then run under the guard and reproduces the simulation:
  - EXACT+REL_6x1: 23/23;
  - EXACT+REL_3x2: 22/22;
  - EXACT_ONLY: 16 vs 15. Q35 uses another template's stored entry leg into the same node — legitimate graph sharing.

| policy (same universe) | strict K=6 | relaxed K=6 | strict K=1 | relaxed K=1 |
|---|---|---|---|---|
| EXACT_ONLY | 12 | 15 | 11 | 14 |
| EXACT + REL 3×2 | 18 | 22 | 16 | 19 |
| EXACT + REL 6×1 | 18 | 23 | 16 | 19 |
| EXACT + geometry-only 6×1 (no patches) | 17 | 22 | 15 | 18 |
| EXACT + fixed-seed random 6×1 | 19 | 24 | 12 | 15 |
| whole universe by travel | 14 | 16 | 5 | 6 |
| REL 6×1 (no exact tier) | 16 | 18 | 13 | 13 |
| *G2a unseeded spread K6 (different universe)* | *5* | *6* | *4* | *4* |

**Paired, root-clustered (exploratory).**
- **EXACT+REL_6x1 vs EXACT_ONLY:** 6–0 queries strict (6 roots vs 0); 8–0 relaxed (8 roots vs 0).
- **vs geometry-only:** 1–0.
- **vs random:** 0–1.
- **vs whole-universe-by-travel:** 5–1 strict, 9–2 relaxed.
- **3×2 vs 6×1:** 0–0 strict, 0–1 relaxed. **No evidence separates them.**

**Provenance.**
- Accepted templates under EXACT+REL_6x1, relaxed: 15 exact-cell, **8 relative-family cross-location**.
- The first accepted candidate is at rank 0 in 19 of 23.
- `REL_K1` is unaffected by relaxation (13 / 13).

**Home-only relaxation, by distinct query** (exact certifier per piece, not prefilter phases). Of 892 checks:

| outcome | checks |
|---|---|
| verified home → home | 140 |
| core fails | 522 |
| entry and exit legs fail, core clear | 186 |
| entry leg only fails | 23 |
| exit leg only fails | 21 |

The 230 connector-only failures reproduce G2a's prefilter-based 228. Ending at the retreat node **rescues 5 distinct queries** (Q03, Q13, Q19, Q21, Q25) for EXACT+REL_6x1 (18 → 23) and loses none. Entry-leg failures need a different stored start node and are not rescued here.

## 6. The "obstructed" target root `p13_2026210004` (`ANOMALY_TRACE.json`; regression test)

Paired trace on one occupancy:
- **P16 teacher label of the original, unrepaired task** (`runs/p16/data/dev/labels_v2w2.json`): `VERIFIED`, y = 1, from q_initial = S3 `[2.356, −1.571, −1.571]`. **Not obstructed, and not a timeout negative.**
- **Stored target check:**

  | condition | outcome |
  |---|---|
  | (a) q_initial with `ROOT_ENTRY` connectors removed | FAILURE `NO_COMPATIBLE_CONNECTOR` |
  | (b) q_initial through the stored S3→home entry | **SUCCESS** |
  | (c) q_home | **SUCCESS** |

  The accepted action is relative-family derived, grasp (330°, elbow −) at pick and place.
- **Offline diagnostic (1 charged attempt).** The historical skill planner from q_initial in the original scene returns `VERIFIED_FEASIBLE`, with pick 300° / place 330°, elbow −. That is a different pick grasp within the same branch.
- **Conclusion: not an anomaly, and not a checker or record bug.** The G2a report mis-described the root; the q change is not what made the target reachable. No label was changed.
- **Also checked:** of the 12 dev roots with P16 labels, 10 are `CERTIFIED_INFEASIBLE` originally and none of them passes a G2a target-template check (agreement). Of the other two, `VERIFIED`, T04 passes and T06 fails (a library gap).

## 7. Swept-cell prefilter (same candidate lists)

**All four G2a false rejections reproduce and are explained.** Their dense continuous clearances along the stored path are 5.21, 8.47, 5.68 and 6.88 mm. Each lies between the certifier margin δ = 5 mm (certifier: VALID) and the prefilter's inflated margin δ + STEP_M = 9 mm (prefilter: flagged). One G2a waypoint-only clearance (186 mm, Q07) was a sampling artefact of a long joint-linear connector segment. There are no prefilter misses.

| policy (strict, K = 6) | OFF success / checks / CPU-s | ADVISORY | HARD success / checks / CPU-s |
|---|---|---|---|
| EXACT+REL_6x1 | 18 / 120 / 73.7 | = OFF | 18 / 18 / 1.2 |
| EXACT+REL_3x2 | 18 / 112 / 45.0 | = OFF | 17 / 17 / 1.1 |
| REL_6x1 | 16 / 128 / 70.9 | = OFF | 15 / 15 / 0.8 |
| REL_3x2 | 14 / 106 / 31.9 | = OFF | 14 / 14 / 0.7 |

HARD costs at most one success per policy and cuts exact certifications 6–8× (CPU about 60×). **The production default stays OFF**; HARD is a measured opt-in. The certifier alone ever accepts.

## 8. Tests and regression

- **`tests/test_approach_d_g2b.py`: 12/12 pass**, on real saved records, all under `forbid('raise')`:
  1. static deny-by-default for `ad_provider` and the new `ad_runtime` functions;
  2. A → B → T end to end, with bitwise continuity, origins and replay hash;
  3. an injected IK call inside a checker trips the guard;
  4. failed candidates then the alternative, with isolated reasons (B is necessary);
  5. no snapping (1e-7 rad off-graph → `NO_COMPATIBLE_Q`), connector ablation, goal through stored entry;
  6. anomaly regression fixture;
  7. replay detects discontinuity and a wrong pick cell; records not mutated; replay bypasses the cache;
  8. cache keyed on occupancy, versions and policy, not shared across policies;
  9. prefilter modes and the four reproduced false rejections;
  10. binary outcomes, no `UNKNOWN` in any new artifact;
  11. exact segmentation and a validated graph;
  12. compile ledger within budget, `[provider]` validation, `config.toml` untouched.
- **G1 + G2a tests:** 23/23 still pass on the final code.
- **Post-change full regression** (`runs/approach_d/g2b/regression/`): **537 passed, 0 failed** (513 historical + 12 G2a + 12 G2b; 774 s), all 6 archived replays clean, `P3A_REGRESSION_CLOSED`. It ran before two non-functional edits: removal of an unused, never-called offline connector compiler, and a docstring. The 35 Approach D tests were re-run on the final code (35/35), and the rebuilt graph hash is unchanged.

## 9. Gate

`runs/approach_d/g2b/G2B_GATE.json`: **PASS**.

| v1.2 §8 condition | evidence |
|---|---|
| 1. old + new tests, six replays, G2a reproduced | 537 / 0 failed, 6/6 replays; G2a 525 + 6 at `4b8aa2c`; re-verification 0 discrepancies |
| 2. zero runtime IK / planning / generated connectors; guard trips on injection | 0 forbidden calls across chains, necessity, anomaly, 108 pilot provider runs and 60 re-verification rows; injection test |
| 3. multi-relocation chain to the original T, plus an isolated failed chain | F12 (A → B → T, 9 records, replay `eec8537ff32a4f1f`); F03 and six F12 candidates fail with recorded causes |
| 4. non-home states and a stored connector graph with explicit q identities | retreat-end nodes, `EXIT_LEG` / `ROOT_ENTRY` / `ENTRY_LEG` records, node ids in §4 |
| 5. certifier decisive; prefilter false rejections measured | §7 (4/4 reproduced, OFF default) |
| 6. original-T anomaly resolved with a test | §6, `test_anomaly_root_regression_fixture` |
| 7. shared-catalog paired comparison with exact denominators | §5 |
| 8. hashes, switches, reasons and cache isolation tested | tests 5, 7, 8, 10, 12; graph `sha256:660b1a91…`; file hashes in the gate |

Offline compile spent: 88 / 120 attempts, 101 / 1,500 CPU-s.

## 10. Files

**New:**
- `ad_provider.py` (provider, graph, sequence / repair adapters);
- `ad_g2b.py` (driver: re-verification, chains, analysis, anomaly, gate);
- `tests/test_approach_d_g2b.py`;
- this report;
- `runs/approach_d/g2b/**`;
- `visualizations/approach_d/g2b/{G2b_chain_success, G2b_chain_failure, G2b_pilot}.png`.

**Modified (additive, opt-in):**
- `ad_runtime.py`: `certify_free`, `certify_action`;
- `ad_compile.py`: `segment`, `qid`, `build_graph`, directory argument for catalogs, restrictable baselines per job;
- `ad_viz.py`: G2b figures;
- `approach_d.toml`: `[provider]`.

**Untouched:** `config.toml`, all historical modules, tests, labels, replays and reports.

## 11. Limitations

- **Thin coverage.** 1/12 fixtures completes, and only with the generic offline-catalog tier (2 of its 3 actions are DIRECT_OFFLINE; the middle one is relative-family). The policies restricted to exact + relative tiers complete none.
- **Ranking.** No advantage of 3×3/4×4 ranking over geometry-only or random ordering within the relative tier on this cohort (36 queries).
- **F12 is dev-informed.** Its destinations were chosen after a pass-1 diagnosis (rule documented, solver-free). This is a demonstration, not an unbiased success rate.
- **Connectors.** Only segmentation legs and three root entries. Entry-leg failures (209 checks) remain unrescued without stored non-home connectors.
- **Necessity is library-relative.** "Both relocations necessary" holds for this finite library, budget and policy, not physically.
- **Scope.** One footprint and grasp family; planar arm; geometric certification only, with no simulation or real execution. Objects snap to cell centres between actions (the historical convention).

## 12. G2c plan (proposed; not started)

1. **Freeze the configuration.** Graph schema, `[provider]` = exact + relative (catalog tier reported separately), OFF prefilter, budget 6, max_hops 2. Leave 6×1 vs 3×2 unresolved; report both.
2. **Close the measured gaps offline, under an explicit budget request:**
   - target-T templates with grasp-class diversity (the dominant chain blocker);
   - a small stored non-home connector set (retreat-end → approach-start for actions sharing an object pair) to address 209 entry-leg failures.

   Estimate the cost from this ledger (~1.5 CPU-s per compile attempt + ~0.8 s sweep) before building anything.
3. **Matched physical transfer benchmark on the 442 held-out queries (G1 LOKO/LORO protocol), only after authorization.** Conditions:
   - exact-cell;
   - relative-family;
   - fixed-catalog travel order;
   - geometry-only;
   - random;
   - all on one frozen universe and budget, with root-clustered intervals, and pattern recall reported separately from physical success.
4. **A chain benchmark on held-out roots with declared candidate lists** (no dev-informed redefinition), with SUCCESS / FAILURE and reasons.

**STOP — G2c not started. Awaiting explicit authorization.** Nothing has been pushed or merged.
