# 0071 — P14-D2: joint destination / order search with recursive D guidance

**Actual result.**
- **Gate:** `runs/p14/P14_D2_GATE.json` → **PASS** (engineering).
- **What was built:** `p14_d_search.py` implements a finite, budgeted, lexicographic search over **both** object order and destination slots. Every relocation is a certified physical motion, and every found plan ends with a planner-witnessed target pick-and-place. Found plans are re-certified step by step in an independent replay.
- **D's temporary-target interface failed its physical check:** querying D with an obstacle as the target agrees with the physical probe on only **45.7 %** of 35 decided probes.

## 1. Formal search

**State:**
- object → cell occupancy (all objects, fixed bodies included);
- robot configuration q (open gripper, nothing held);
- the executed prefix: which objects were moved, their destinations, and each motion's provenance.

**An edge** relocates a movable catalogue object, each at most once, to a candidate slot. Candidate slots per object:
- the 4 nearest free, annulus-safe cells that are ≥ 2 cells from the target and goal (the P10b parking rule);
- plus free indexed destinations for the object's current source cell.

The slot rule and the number of slots are identical for every method.

**How an edge is verified:**
1. **Library witness:** the retrieved witnesses are tried in mode order. Each needs a **certified joint-linear transit** q → witness start in the current scene, plus `motion.certify_trajectory` of the witness in the current scene (exact continuous certifier).
2. **Fallback:** if no witness certifies, the online planner (`skill.plan_skill`, `q_start = q`) runs, within budget.
3. **Occupancy update:** the source slot becomes free and the destination occupied, so later edges see the updated scene. A slot occupied by object C cannot receive B unless C has moved away.
4. **Robot update:** q becomes the final configuration of the executed witness.

**Goal test (always the real planner):** the target pick-and-place from the current q in the current scene, starting with the **zero-move original**.

**Objective:**
- **lexicographic (number of relocations, measured travel)**, with travel = `ordered.joint_travel` summed over transits, witnesses and the target record;
- no risk term and no weights;
- implemented as iterative deepening over the move count (0 … 3) with travel branch-and-bound inside a depth (sound: travel is nonnegative).

**Optimality** is claimed only when a depth was enumerated without budget truncation (`depth_exhaustive`), and only over the finite candidate graph (slots × library + fallback witnesses). Otherwise the result is "best plan found within the library and budget".

**Determinism and fairness:**
- planner seed keys are a pure function of the physical query (occupancy, q, object, destination), so every guidance method sees identical witnesses for identical states;
- a per-search memo charges each physical check once;
- the budget per root is 120 motion checks, 6 online relocation plans and 16 target checks.

**Guidance** affects only the expansion order:
- objects are expanded by blocker score;
- after a failed relocation of object o, guidance is re-queried with **o as temporary target** and o's predicted blockers are promoted (recursive D);
- **nothing is ever pruned or vetoed** by D;
- cycles are excluded by move-once and a per-search state memo.

## 2. Recursive-D interface check (`D_INTERFACE_PROBE.json`, DEV roots only)

- **Probe:** for each movable obstacle of 20 DEV roots, frozen D (λ_B = 1.0, 3 seeds) was queried with that obstacle as the target, versus the online planner trying to pick it and place it at its first free slot.

| measure | value |
|---|---|
| probes | 36 (24 VERIFIED, 11 CERTIFIED, 1 UNRESOLVED) |
| agreement at P(feasible) ≥ 0.5 | **0.457** |
| D says feasible, given physically VERIFIED | **0.208** |
| D says infeasible, given CERTIFIED | **1.000** |

- **Verdict: the arbitrary-target transfer is NOT validated.** D was trained only with the true target and is strongly pessimistic about obstacles as targets.
- **Consequence:** recursive D queries are used only to reorder expansion. They can waste budget, but they cannot remove a valid plan.

## 3. DEV benchmark (8 DEV roots, development budget 150 / 10 / 30, before the seed-key and budget freeze)

| method | roots solved (plan + replay) |
|---|---|
| D | 6 / 8 |
| D-pairless | 7 / 8 |
| geometry | 7 / 8 |
| uninformed | 7 / 8 |
| oracle | 7 / 8 |

- **Feasible original (NAT):** **0 moves**; target retrieval verified directly, with no relocation and no hallucinated blocker, for every method.
- **One blocker** (PN_GIMP, PN_SIMP, PR_SIDES, NAT): **1-move plans, depth-exhaustive**. Travel differed slightly between methods in this pre-freeze run because planner seeds depended on call counters; this was fixed before D3 (state-deterministic keys).
- **Two jointly necessary blockers** (PC_SG): 2-move plan, barrier by lookup witness, occluder by online witness. Budget-truncated, so "best found within budget".
- **Order / omission chains** (ORD_CHAIN): unsolved within budget by every method. OMIT_OPT: solved by four methods, not by D.

**Case figure:** `visualizations/p14/P14_search_case_004.png` and `.gif` show DEV PC_SG root 004 under D guidance:
- D scores the two true blockers at 1.00 each;
- the lookup returns 2 motion modes for the first move (one supported by 4 roots, travel 0.53; one by 1 root, travel 0.66);
- the executed plan is o00 → 44 (lookup), o01 → 22 (online), then the target;
- cost: 2 moves, travel 2.22.

The GIF is sampled only from the certified recorded arrays: transit + witness, the online witness, and the target witness.

## 4. Minimal benchmark coverage

| contract case | status |
|---|---|
| target already feasible | done (0 moves, every method) |
| one blocker, ≥ 2 destinations with different travel | done (depth-exhaustive 1-move plans) |
| two jointly necessary blockers | done on DEV (2 moves); 1 / 3 at D3 |
| A blocks B's grasp; reusing freed source slots | covered by ORD / OMIT roots; solved only for OMIT on DEV |
| free destination whose sweep blocks a later move | not isolated |
| multiple sufficient subsets | PR_SIDES (κ = −1): a single minimal move chosen, union not moved |
| rare mode succeeds while the modal mode collides | not observed at D3 (`modal_rejections_rescued` = 0); unit-tested |
| no library witness | fallback or UNKNOWN: ~40 % of candidate pairs |
| D access error corrected physically | interface probe (§2) |
| pairs / triples | pairs only; triples are prediction-only roots |
