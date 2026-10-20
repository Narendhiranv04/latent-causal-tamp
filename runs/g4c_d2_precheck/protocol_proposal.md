# G4C-D2 witness-first constructive dataset: protocol proposal (`G4C-D2-v0`, PRECHECK)

**Status:** proposal plus static precheck only. Every constructed target, repair and intervention label is **NOT_RUN**.
D2 is a new, separately versioned lineage; it does not edit, extend or relabel G4C-P0 (`runs/g4c_preflight/plan.json`) or G4C-P1 (`runs/g4c_pilot/`).

## 1. Generation algorithm

1. **Base family.** A root with an immutable scene `S_base`, target `t0`, goal cell, the robot at its tested `q0` (gap open, gripper free), the 48-grasp family and `GOAL_AND_SAFE_RETREAT`.
   - The base needs a **complete target-only witness**: every recorded segment re-certified CLEAR (`motion.certify_trajectory`, conservative continuous check over links, housings, base, palm, rail, fingers and the held disc); a record that starts at `q0`, places within the goal tolerance, and ends open-handed in retreat.
   - P0 uses **archived** witnesses only: G4C-P1 `seq:g4c_r00:empty`, G4D `seq:R0:empty` and G4D `seq:R1:empty`, all `BASE_WITNESS_REPLAYED`.
   - D2-P1 may additionally plan fresh base witnesses (`evaluate.evaluate_target` under the guarded runner) on bases built by the G4C geometric rule, within an authorized attempt cap.
2. **Obstacle insertion.**
   - **Legality:** every free supported cell is a candidate, accepted only if it is distinct from all objects and the robot at `q0` stays clear (`geometry.Checker`).
   - **Diagnostic:** the recorded witness is re-certified in the clone, giving `blocks_nominal_witness` ∈ {YES, NO, UNVERIFIED}, the first interrupted segment, its phase, path parameter and colliding body pair.
   - **Roles** come from the first interruption: `transport_path` (held disc), `grasp_access_blocker` (palm/rail/fingers before attachment), `arm_link_sweep_blocker`, `retreat_blocker`, `target_goal_occupant`, `harmless_nearby` (certified clear), and `staging_slot_occupant` (an obstacle on A's first G4C destination).
3. **Nested variants (frozen rule).**
   - **A:** the earliest-interrupting non-goal blocker.
   - **B, C:** the earliest blockers of other roles, pairwise non-adjacent.
   - **N:** a certified-clear nuisance farthest from the blockers.
   - **G:** the goal occupant.
   - **S:** the occupant of A's first destination.

   The variants are `base, +A, +B, +A+B, +A+B+C, +N, +A+N, +G, +A+S`. Earlier obstacles keep their IDs and cells, the robot and goal are unchanged, and nothing is cloned.
4. **Predeclared catalogue (before any outcome, frozen geometric rule; no witness information).**
   - **Participants:** the added obstacles.
   - **Destinations:** the G4C rule on the initial scene (outside the corridor, nearest first, joint assignment).
   - **Sequences:**
     - `[]`;
     - singles to two destinations;
     - both orders of each blocker pair;
     - three orders of the triple;
     - the staging trio (A→P, (S→, A→P), (A→P, S→));
     - every single- and pair-omission remainder (remaining order preserved; omitted objects stay).
   - **Fixed-robot scene edits:** singletons, the first joint pair, and the nuisance edit, each geometry-checked for eligibility; ineligible edits are discarded at predeclaration, never labelled.
   - **B/C catalogue:** the first ≤ 3 eligible edits. The layout is `z0, zS[q], zR (m ≥ 1), zO[t] (m ≥ 2)`, with at most 8 active slots (all variants: maximum 8) and no inactive multiplicity.
   - **Robot-start alternatives** (D2-F9) on the base variant.
5. **Teacher (D2-P1 only).** Every unit uses the unchanged G4D/G4C runner: guard, checkpoints, per-unit revalidation and the `g4c_pilot.adjudicate` rules.

## 2. Label semantics

- **POSITIVE:** a complete witness — relocations in exactly that order, each from the previous achieved state, then the target from the achieved state to goal and safe retreat — with every consistency check true.
- **NEGATIVE:** only a checker-accepted certificate of covering scope:
  - `GOAL_OVERLAP`, `STATIC_ENDPOINT_INVALID`, `TARGET_PICK`, `FIRST_MOVER` (assignment scope);
  - `ORDER_FIRST_ACTION` (order scope).
- **UNKNOWN:** everything else, including timeouts, censoring, uncertified rejections, and the skill's "all pairs certified blocked from q0" connector verdict (no checker kind exists; adding one requires a separate proof-obligation review and is **not** done here).
- **`blocks_nominal_witness` is never a label.**
  - A nominally blocked scene with a fresh target witness is `REROUTABLE_POSITIVE`, a hard positive control.
  - A nominally blocked scene with only failed searches is `UNKNOWN`.
  - "Induced infeasibility" requires a sound full-scope certificate.

## 3. Closed pools and released data

- A variant's declared pool is **closed**: `DECIDED_COMPLETE` only if every declared sequence, scene edit, omission and B/C active slot is decided. Otherwise the **whole** pool is `PARTIAL_OBSERVATION`; no item is dropped after labels arrive.
- A **substantive** B/C pool has at least two distinct decided nonempty repairs, including a POSITIVE (a POS/NEG distinction or competing positives). Empty-only and nuisance-only pools are reported separately.
- **Costs:** `J_first` comes from the first complete relocation witness only. It is masked when a certificate pre-empts relocation; the empty repair has J = 0.
- **Ledger:** every construction attempt, rejected cell and raw unit (including UNKNOWN) is kept. Both `decided released / released` and `released / attempted` are reported.

## 4. Splits and leakage

- **Family** = base scene lineage (`family_id` = hash of the declared lineage). G4D R0 and R1 are the G2_D1 reference scene and its blocked variant, so they form **one** family. Every variant, edit, order, omission and descendant inherits its family's split; siblings never cross splits.
- **Learner inputs** are only `data.learner_tensors_v2` of the **actual obstructed initial scene**.
- **Privileged** (never inputs): base witness, nominal sweep and collision times, construction role and family, seeds, certificate kinds, grasp indices, costs and outcomes. Poisoning these leaves learner tensors byte-identical (tested).

## 5. Alternative-path counterexample (why nominal obstruction ≠ infeasibility)

The recorded witness is one of many continuous realizations: 48 grasps × 2 elbow branches × arbitrary connector paths.

In G4D R1, an obstacle at cell 57 intersects the recorded pregrasp sweep at segment 0 (role `arm_link_sweep_blocker`), yet the robot may approach the same grasp along another connector or use another grasp. Only a fresh target evaluation can decide. The logical control is enforced in `tests/test_d2.py`: `root_release_label(nominal_blocked=True, witness=True, cert=False) == REROUTABLE_POSITIVE`, and `(True, False, False) == UNKNOWN`, never NEGATIVE.

## 6. D2-P1 proof of concept (NOT authorized; numbers in `budget_request.json`)

**Tier POC_S (recommended):** families `g4d_R1` and `g4c_r00`; variants `base, +A, +A+B, +A+S, +G, +N`; 68 units (50 ordered, 16 scene target-only, 2 robot-start); at most 46 relocation skills; up to 2 fresh-base attempts.

**Requirements**, each reported as met or as an explicit failure:
- (a) a verified base witness per family;
- (b) a sound target-blocked NEGATIVE root, if constructible (`+G` is goal-overlap; a non-trivial one needs a non-goal certificate);
- (c) a fully witnessed repair POSITIVE for that same root;
- (d) one decided order contrast (`+A+S` staging trio) or an explicit failure;
- (e) a complete substantive B/C pool, if constructible;
- (f) the full construction and discard audit.

**Tier POC_F:** all 3 archived bases (2 independent lineages: G4C r00 and G2_D1) × 9 variants (194 units). Request only after POC_S.
