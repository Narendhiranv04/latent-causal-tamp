# P4 recovery: development report (exploratory)

Protocol `P4_PROTOCOL_V1` (`P4_RECOVERY_PLAN.md`, `p4_config.json`) was committed before any P4 run (`fdbc5a257c`). Amendment P4-A1 followed from Gate B mock evidence only.

**Data.** The 25 DEV engineering scenes were already exposed in P3, so **every result here is exploratory**.

**Data handling:**
- No release_v2 TEST file was opened, and nothing was pushed.
- Every arm was sealed before the teacher ran (`SEAL.json` per arm). The teacher was never in any planning loop.
- Outputs are in `/home/naren/kgt3_runs/{p4, p4eval, figs}`.

## 0. Verdict: **BLOCKED for TEST under the current constraints.**

Physically verified success is **0/25 for every arm**: the historical R0 arms, R1, R2, R3, flat F and random N. The pre-declared confirmatory trigger (a recursive arm strictly beating both F and N) was **not met**, so no confirmatory cohort was run.

The recovery fixed the generation failure but uncovered a deeper one:

| Change | Before (R0) | After (R2 / R3 / F) |
|---|---|---|
| Committed plans with a correct object set | ~1/25 | 12 / 14 / 9 of 25 |
| Committed plans with a physically valid endpoint (teacher Y = 1) | 0 | **9 / 11 / 9** |
| Committed plans with an executable order | – | **0** |

The frozen models can now be steered toward plausible *endpoints*. They cannot order a long sequence executably, and recursion adds nothing over flat or random search at matched compute.

## 1. Gate A: causal diagnosis of the historical 0/25 (all 25 scenes, R0 re-runs with full candidate pools)

| Historical arm | Scenes with **any statically complete candidate** in the pool | Mean candidates | Mean committed \|r\| | Short candidates (\|r\| < 4) with h_Y ≥ 0.5 | Temp-target probes below 0.5 | Stop reasons |
|---|---|---|---|---|---|---|
| REC | **0/25** | 1.7 | 2.8 | 48% | 98% | LOCAL_CALLS 17, WALL 7, YTASK 1 |
| REC2 | **0/25** | 24.4 | 3.7 | 46% | 97% | LOCAL_CALLS 11, FRONTIER_EMPTY 11, WALL 3 |
| FLAT | **0/25** | 42.6 | 3.7 | 46% | – | FRONTIER_EMPTY 25 |

**The historical failure was generation, not ranking.** No pool ever contained a complete plan, so even the corrected R1 energy re-ranking the same pools selects 0 complete plans.

Contributions:

| Hypothesis | Finding |
|---|---|
| H1, Σ-chunk length penalty | Arg-min length 3.7, against 5.1 under mean-X over the same pool (FLAT) |
| H2, false-high h_Y stopping | ~46–48% of short candidates have h_Y ≥ 0.5; FLAT ends FRONTIER_EMPTY in 25/25 |
| H3, absolute 0.5 temporary-target gate | 97–98% of probes are below it, so nearly every action is "suspect" |
| H4, starvation | REC: 1.7 candidates per scene, a single round |

## 2. Gate B: mock correctness (no K, no blocker signal)

- **R1 and R2 compose the K4/K6/K9/K12 chains in a valid order**, after amendment P4-A1. R2 passes K9 and K12 at the minimum length with 27 and 38 local calls, against 77 and 115 for R1.
- **F fails every nested chain.**
- **R3 fails mock K12.** Its seeds were empty in the mock, so they only cost budget.
- **R1 energy check:** a complete 12-move plan (C = 0.08) beats an incomplete 3-move plan (C = 4.14).

**P4-A1:** R2's "lowest-ŷ action" rule always suspected the single action of a one-action hypothesis, which exhausted the per-insertion budget before nested enablers. It was replaced by a scene-relative reference: ŷ below the median ŷ of movable objects to their top cVAE destination in the same scene. The per-insertion cap went from 3 to 6.

## 3. Gate C: model-only search behaviour (before any label)

Common caps: ≤150 local calls, ≤4,000 probes. Wall time was only a 600 s safety cap.

| Arm | Mean \|r\| | Pool max \|r\| | Mean pool | Local calls | Temp probes | Candidates scored | Wall s | Stops |
|---|---|---|---|---|---|---|---|---|
| R1 (rank/stop only) | 3.7 | 4.5 | 1.7 | 148.6 | 3,277 | 1.57 M | 158 | LOCAL_CALLS 22, YTASK 3 |
| **R2** | **8.4** | 12 | 72 | **43.9** | 608 | 0.43 M | 41 | FRONTIER_EMPTY 15, STAGNATION 10 |
| **R3** | **8.7** | 12 | 77 | 48.4 | 722 | 0.51 M | 44 | same as R2 |
| F (flat) | 8.0 | 11.7 | 185 | 31.0 | 0 | 0.30 M | 24 | same as R2 |
| N (random) | 11.6 | 12 | 47 | 35.3 | 660 | 0.61 M | 8 | FRONTIER_EMPTY 22, STAGNATION 3 |

- The ranking and stopping fix **alone (R1) changes nothing**: it is still starved inside round-1 recursion.
- Relative gating plus pacing (R2) unlocks long plans at **under one third of the budget**.
- F, with the R1 ranking and stopping fix, *also* builds long plans. So plan length is no longer a recursion-specific effect.

## 4. Gates D and E: physical evaluation (teacher_long, sealed) and matched-compute comparison

| Arm | **Success** | Committed object set correct | Order valid (static) | Endpoint physically valid (teacher Y = 1) | Teacher X = 1 | \|r\| ≥ K | Pool has a statically complete plan | Pool has a verified success | Witness-object overlap |
|---|---|---|---|---|---|---|---|---|---|
| R0 REC / REC2 / FLAT | 0 / 0 / 0 | 1 / 1 / 1 | 0 | 0 / 0 / 0 | 6 / 4 / 4 | 1 / 4 / 4 | 0 | 0 | 0.21–0.26 |
| R1 | 0 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0.26 |
| **R2** | **0** | 12 | **0** | **9** (K4 2, K6 1, K9 6) | 3 | 19 | 1 | 0 | 0.54 |
| **R3** | **0** | 14 | **0** | **11** (K4 3, K5 1, K6 1, K9 6) | 3 | 19 | 2 | 0 | 0.56 |
| F | 0 | 9 | 0 | 9 (K4 2, K6 1, K9 6) | 2 | 18 | 2 | 0 | 0.55 |
| N | 0 | 13 | 0 | 7 (K4 3, K9 4) | 0 | 25 | 0 | 0 | 0.70 |

Success by K is 0/8 (K4), 0/4 (K5), 0/4 (K6), 0/8 (K9) and 0/1 (K12) for every arm.

**Paired exact sign tests** (R2 vs F, R2 vs N, R3 vs F, R3 vs N, R1 vs F, R2 vs R1, R3 vs R2, F vs N): **0 discordant pairs**.

**Where R2/R3/F fail, among committed plans with a correct object set:**
- The first static break is a **dead pick** (an object still blocked when moved: R2 7, R3 7, F 5) or a **dead place** (destination blocked at its time: R2 5, R3 7, F 4).
- The teacher agrees: X = 0 during a relocation (UNKNOWN_PLANNER / CERTIFIED_INFEASIBLE), while Y = 1 for 9/12, 11/14 and 9/9 of these plans.

**Further evidence:**
- **Temporary-subgoal success**, meaning inserted enablers that make their dependent action statically feasible: R2 184/387 (48%), R3 187/401 (47%), and the **random control N 153/299 (51%)**.
- **Destination liveness at execution time:** R2 0.71, F 0.76, N 0.81, R0 0.83–0.86.
- **Scene traces show the mechanism:** the witness parks blockers in free cells away from the cluttered region. The frozen cVAE's top-4 destinations park them inside the region, creating new blockages for later moves.
- **R3 seeds were non-empty** in 24/25 (pick side) and 20/25 (goal side) scenes, but their composition with the iterative loop did not change success.

**No pool, in any arm, contained a teacher-verified success** among its top-5 statically complete candidates (10 extra verifications). There is no "generated but mis-ranked" case.

## 5. Answers to the seven questions

1. **Does the iterative recursive loop now generate useful long-horizon repairs?** It generates long *candidates*, with plan length no longer collapsing, and reaches physically valid *endpoints* in 9–11/25 scenes. It does not produce executable repairs (0/25).
2. **Right objects and destinations without privileged information?** Partly, and **not because of recursion.**
   - The correct object set appears in 12–14/25 committed plans, but the random control reaches 13/25 simply by moving 11–12 objects.
   - Witness-object overlap is 0.54–0.56 for R2/R3/F against 0.70 for N.
   - Destinations are the weak point: cVAE proposals park objects inside the cluttered region.
3. **Does composition preserve executable order?** **No.** 0/25 committed plans in any arm have a statically valid order. The teacher confirms that execution fails mid-sequence while the endpoint is valid.
4. **Is the final scorer choosing complete repairs?** There is nothing correct to choose: pools contain a statically complete plan in at most 2/25 scenes, and none of those verified. The final h_Y does steer toward valid *endpoints* (Y = 1 in 9–11 scenes). Stage X, as a mean over chunk-level X from q_ref, does **not** discriminate executable orders.
5. **Does recursion beat flat search at comparable cost?** **No.** R2/R3 vs F is 0 vs 0, with 0 discordant pairs. Valid endpoints: R2 9, R3 11, F 9, N 7. Recursive subgoal success (47–48%) is no better than random insertions (51%).
6. **Which frozen-model information drives the improvements that did occur?**
   - **The frozen original-target Y (h_Y) evaluated over many long candidates**, enabled by the R1 ranking and stopping fix plus fair or flat search, explains the endpoint gains. N also benefits, from frozen h_Y alone.
   - The temporary-target signal steers recursion (D3/D4 informative in P3), but its insertions are not better than random at the subgoal level, and it does not translate into executable order.
7. **What remains unsupported by models trained only on K≤3?**
   - **Executable ordering of long sequences:** X is learned for ≤3-action chunks that start and end at q_ref, and its mean over chunks does not capture carried-state dependencies or blockages created by earlier placements.
   - **Selection of which objects block a K>3 target** (D1 null in P3).
   - **Destination choice that avoids creating new blockages** over long horizons.

## 6. Changes from the original methodology (all declared; the Fig. 3(a) architecture is unchanged)

| Change | Status |
|---|---|
| R1: length-neutral stage-X aggregate (mean instead of sum); no termination on h_Y; stagnation stop | adopted in R1–R3 and F |
| R2: scene-relative temporary-target gate (P4-A1); enabler accepted when ŷ doubles; round / plan / insertion pacing | R2, R3, N |
| R3: target-centric temporary tasks from public target/goal and frozen calls only | separate variant |
| Wall time demoted to a safety cap; local calls and probes binding | all P4 arms |
| Engineering: per-scene cache clearing; memory-guarded queue (≤6 workers, pause/requeue) after an OOM crash | no effect on results (deterministic) |

**Process deviations.**
- The system crashed with an OOM when 24 workers ran at once. All runs are resumable and deterministic, so no result was altered.
- R1's last 4 scenes were computed by fresh workers after their paused predecessors were killed.
- GIFs: no committed plan executes fully (X = 0 everywhere), so there are no complete selected-plan trajectories to animate. The release_v2 witness GIFs are not used here.

## 7. Figures

| File | Shows |
|---|---|
| `figs/P4_summary.png` | success, pool completeness, object set, order and length per arm; success vs expenditure |
| `figs/p4_scenes/<root>.png` (25) | per scene: committed R2 vs F plans against the witness (post hoc); candidate-pool energy vs length with static completeness; R2 insertion dependency graph; budget over rounds (R2 / F / N / R3) |
| `figs/P2_mock_traces.png` and `GATE_B_MOCK.json` | mock compositions |

## 8. Recommendation

**BLOCKED** for the final TEST under the constraints of no training, no new modules and no privileged information. The evidence does not support the claim that recursive reuse of the frozen K≤3 models yields executable K>3 repairs, or beats flat search at matched compute. Further no-training tweaks would amount to tuning on exposed scenes without a mechanism the data supports.

A meaningful next step needs a decision from you, because it changes the constraints:
- (i) a learned stage-executability signal conditioned on the carried state and on earlier placements, which requires training;
- (ii) a destination prior that avoids creating blockages, which also requires training;
- (iii) accepting an explicit non-learned order repair over the found endpoint, which is a different method and was excluded here.

The partial result worth reporting: **frozen original-target Y over long candidate pools finds physically valid endpoints in about 40% of K4–K9 DEV scenes, but executable ordering is the unsolved part.**
