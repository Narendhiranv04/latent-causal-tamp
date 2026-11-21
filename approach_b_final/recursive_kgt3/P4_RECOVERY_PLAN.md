# P4 recovery plan and protocol (`P4_PROTOCOL_V1`, frozen in `p4_config.json` before any P4 run)

**Goal.** Make Iterative Loop → Retarget → Compose → Rank work as intended, using only public scene information plus the frozen cVAE and frozen X/Y model. Then determine whether recursion helps **beyond extra search**.

**Constraints:**
- No privileged information at inference.
- No training and no new learned modules.
- The teacher is used only post-seal.
- No release_v2 TEST access.

**Data status.** The 25 DEV engineering scenes (K4 ×8, K5 ×4, K6 ×4, K9 ×8, K12 ×1) were **already exposed** in P3, so every DEV result below is **exploratory**. A single confirmatory cohort is pre-declared in §6.

## 1. Diagnosis hypotheses (Gate A tests them causally)

| ID | Hypothesis | Code path | Gate A test |
|---|---|---|---|
| H1 | The ranking prefers incomplete plans | `planner.energy`: C = −log h_Y + λ_X **Σ**_j −log h_X(c_j). Each extra canonical chunk adds a non-negative cost, and λ_m = 0 gives no reward for length. | Re-run R0 arms with full candidate-pool logging. Per scene: best energy by length, and the length of the arg-min. |
| H2 | Premature stopping on false-high h_Y | `planner.run`: candidates with h_Y ≥ 0.5 are "done" and leave the frontier | Fraction of scenes ending FRONTIER_EMPTY with every frontier plan "done"; h_Y of short plans |
| H3 | The absolute 0.5 temporary-target threshold over-triggers recursion | `planner.expand` suspect rule; `solve_tt` success ŷ ≥ 0.5 | Probe logs: fraction of actions suspected; subgoal success rate; mean ŷ scale |
| H4 | Budget starvation | REC spends its budget inside round 1 (`log.rounds`) | Local calls consumed before round 2 |
| H5 | No original-task mover signal (D1 = 0.51) | `planner.local` for task T0 ranks by original-task p11 | Already measured; R3 tests whether temporary-task decompositions recover it |
| H6 | Mismatch between local X (start at and return to q_ref) and carried execution | `energy` h_X | Post hoc: teacher X failure phase among statically valid plans |
| **Key** | **Was a statically complete plan ever generated and then mis-ranked?** | – | Post hoc relaxation check (kill tables) over the logged candidate pools |

## 2. Variants (minimal, separately attributable; all in `planner_r.py` + `p4_config.json`)

| Arm | Definition |
|---|---|
| **R0** | Historical sealed P3 results (REC / REC2 / FLAT), plus Gate A re-runs with candidate logging. Identical code (`planner.Planner`); determinism verified in P3. |
| **R1** | Rank and stop correction, keeping the original threshold retarget. Formula below. Termination: no h_Y-based "done"; every legal \|r\| < 12 plan stays eligible for the frontier; stop on budget, 12 rounds, or **energy stagnation** (best C not improved for 3 rounds). A high h_Y improves rank only. |
| **R2** | R1 plus fair recursion (rules below) |
| **R3** | R2 plus target-centric seeding (separate variant; rules below) |
| **F** | Budget-matched flat control: same frozen models, proposals and R1 ranking/stopping; no retarget or insertion; frontier B_top = 24, so it can spend the same 150-call budget |
| **N** | Random/fair control: the R2 search with uniform random destinations, random local scores and random gates (`models.Random`), but the **same frozen final energy** |

**R1 energy:**

C(r) = −log h_Y(r) + λ_X · **mean**_j[−log h_X(c_j)]

The mean over canonical chunks of 3 makes a plan's X evidence an average over its stages. It no longer grows with every added chunk. The local X values are correlated and include a q_ref return, so they are not treated as independent probabilities. λ_X = 1, λ_m = 0, and no reward for length (the planner never knows K).

**R2 rules:**
- **Suspected actions:** in each local hypothesis u, the action with the lowest ŷ (temporary-target Y in its pre-scene), plus any action with ŷ < 0.5 · max ŷ(u). This is relative, with no absolute threshold.
- **Enabler acceptance:** a temporary subgoal is accepted when ŷ at least **doubles**; scale-free, because ŷ ranges over about 0.01–0.1.
- **Pacing:** per round, the remaining local calls ÷ remaining rounds. Per frontier plan, an equal share. Per insertion, ≤ 3 local calls. Temporary-task depth D_max = 2.
- The no-enabler alternative is always kept, so recursion never removes options.

**R3 seeding:** temporary tasks are derived **only** from the public target/goal and frozen calls.
- **Pick side:** query the frozen cVAE with T as the queried object (top-4 destinations). Score each destination d by ŷ(T→d) in S0, take the most reachable d*, and recursively solve the temporary task (T, d*).
- **Goal side:** compute ŷ(O→G) for every movable O, take O* = argmax, and recursively solve (O*, G).
- The seeds (pick, goal, and their union if disjoint) enter round 0 of the iterative loop and are ranked like any other candidate.
- No analytic blocker set, swept volume or known first action is used.

## 3. Common budget (binding, hardware-independent) and caps

Per root, for every arm:

| Item | Value |
|---|---|
| Local-generator calls | **≤150** |
| Temporary-target probes | **≤4,000** |
| Rounds | ≤12 |
| Plan length \|r\| | ≤12 |
| Local generator | L = 8, B_loc = 6, B_loc_tt = 4, B_exp = 4 |
| Wall time | **600 s safety cap only**, so GPU contention cannot change results |

Stop reasons: LOCAL_CALLS / YTASK_PROBES / WALL / STAGNATION / FRONTIER_EMPTY / MAX_ROUNDS.

Usage is reported per arm: local calls, probes, candidates scored and wall time.

## 4. Decision rule

Frozen p_noop ≥ 0.5 → NOOP. Otherwise REPAIR with argmin C over all scored candidates (ties broken by shorter, then lexicographic). With no candidate, ABSTAIN. Exactly one sealed answer per scene, and no retry after physical failure.

## 5. Metrics (post-seal; labels = teacher_long, plus kill-table relaxation and certified witnesses)

| Metric | Definition |
|---|---|
| **Primary** | physically verified success (X = 1 and Y = 1), per arm, per K |
| Object set correct | committed movers cover some minimal goal set (static endpoint Y live) |
| Destination coverage | fraction of committed actions whose placement is statically live at its time |
| Order coverage | static order validity of the committed sequence |
| Proposal coverage vs ranking failure | Did the **candidate pool** contain a statically complete plan (endpoint Y live **and** order valid)? If yes but not committed: **ranking failure**. If none: **generation failure**. Also: did the pool contain a teacher-verified success? (Teacher-checked for the top-5 statically complete candidates per scene, post hoc, never fed back.) |
| Length | \|r\| compared with certified K |
| Temporary subgoal success | Inserted enablers that make their dependent action statically feasible (kill tables) |
| Effort | search nodes (candidates), recursive calls (insertions, temporary-task local calls), model evaluations, wall time, stop reasons |
| **Matched-compute comparison (Gate E)** | each recursive arm vs F and vs N: paired discordance with an exact sign test (**descriptive only**, exploratory) |

## 6. Single confirmatory evaluation (pre-declared; run only if triggered)

**Trigger.** On DEV, some recursive arm Rk (k ∈ {2, 3}) has **strictly more** physical successes than **both** F and N. If none does, no confirmatory run happens and all results stay exploratory.

**Cohort.** Up to 30 engineering layouts from the scaling campaign's G0/G2 engineering pools (`lay_e`, `lay_g`):
- relaxation K_lb ∈ {4, 5, 6}, never witness-certified (so never DEV);
- not exact or near-duplicates (occupied-cell Jaccard > 0.85) of any DEV scene;
- ordered by sha256('P4CONF|root_id').

No release_v2 file and no final-pool candidate is used. K_lb is used **only** for this selection and post-hoc stratification, never by the planner.

**Arms.** The triggering Rk (if both trigger, the one with more DEV successes; ties go to R2), F and N. Same frozen config, sealed before verification.

**Outcome.** Success counts with exact paired tests. A scene may have no solution at all, which affects every arm equally; this is reported.

## 7. Gates

| Gate | Content |
|---|---|
| **A** | Diagnosis via R0 re-runs with candidate logging plus post-hoc analysis |
| **B** | Mock correctness of R1/R2/R3/F on K4/K6/K9/K12 chains (no K, no blocker signal) |
| **C** | Model-only runs of R1/R2/R3/F/N on DEV; inspect search behaviour (no labels) |
| **D** | Seal, then teacher verification |
| **E** | Comparison under matched compute; confirmatory run if triggered |

**No design changes after Gate D labels.** If the revised method fails, it is reported as failing.
