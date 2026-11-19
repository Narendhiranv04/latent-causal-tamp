# Order-dependency audit of the final 2D and 3D datasets: handoff (linear) vs geometric (non-linear)

**Scope**
- This is a read-only audit that uses existing evidence only.
- It covers the frozen training snapshot `abf_9de85710c2a7103f` (2D: 5,000 roots; 3D: 2,500 roots) and its selection manifests, gate manifests, replay results and raw root records.
- No dataset, label, manifest, snapshot or checkpoint was modified.
- No planner or MuJoCo call was made. The control interface check (`controls.py --dry-run`) builds states only.
- No root of the V3.4 expanded cohort enters any artifact. Gate 2 checks this against its private index ids.

**Artifacts** (all in this directory)
- `ORDER_DEPENDENCY_CLASSIFICATION.jsonl`: 1,950 2D and 1,224 3D K2/K3 roots.
- `DATASET_SUMMARY.json`
- `FAILURE_MECHANISM_SUMMARY.json`
- `MISSING_COUNTERFACTUALS.jsonl`
- `PILOT_QUERIES.jsonl`
- `GATES.json`
- `COUNTERFACTUAL_AUDIT_PLAN.md`
- `README.md`
- Code: `audit.py` and `controls.py`.

## 1. Bottom line

1. **No root in either dataset can be called *handoff-only* from existing evidence, and none can be called *mixed*.**
   - This needs the robot to start from q_ref in an intermediate object state (P2/P4), and no record contains such a start.
   - Every step after the first in every stored execution starts from the **achieved** configuration.
2. **In 2D, geometric dependence is confirmed by configuration-independent certificates in 643 of 1,950 K2/K3 roots (33.0%).**
   - Blocking only: 514. Enabling only: 100. Both: 29.
   - In 324 of these (16.6% of all K2/K3), *every* relocation failure is explained by such a certificate.
   - **Certificate:** `CERTIFIED_INFEASIBLE` at a relocation, meaning either the destination is occupied or the pose-only grasp screen proves every declared pick/place grasp is blocked by objects (`p16_motion.py:129`, `ordered.py:83-95`). It does not depend on the robot configuration, so it holds from q_ref too. That makes it an equivalent matched-state comparison against the observed step-0 success from (S0, q_ref).
3. **In 3D, nothing is confirmed.**
   - 3D CERTIFIED failure reasons come from the first IK branch tried, and branch order depends on the start configuration (`shelf_scene.py:913-914, 1222`).
   - The finalized 3D X record drops the kind altogether (`fin3d.py:111`); it is recoverable only from the legacy execution of the same step.
   - So 3D geometric evidence is at most *certificate-supported*: blocking in 305 roots, enabling in 32.
4. **2D handoff evidence is weak.** The 77 2D K3 roots with a fixed-geometry, carried-state contrast are all `UNKNOWN_PLANNER`.
   - In 2D the RRT seed, the candidate order and the cache keys are derived from q (`skill.py:193`, `planner.py:235`).
   - Such a contrast can therefore reflect seed or budget variation rather than a physical handoff impossibility.
5. **The generators never targeted handoff dependence.**
   - The original generators *avoid* geometric precedence: `bd_2d_plus.py:15-17`, `bd_2d_exact.py:12-13`, `bd_3dt_plus.py:22-23`.
   - The dependence-seeking and hard-order generators *deliberately construct geometric precedence* through mechanisms named in the code: `NEAR_OTHER_MOVER`, `BLOCK_PICK`, `BLOCK_PLACE`, CHAIN/DOUBLE enabling.
   - However, all of them *accept* a root on carried-state outcomes, so an accepted contrast can come from either mechanism. A handoff mechanism was never isolated or labelled.
6. **The Approach B model learns order-sensitive sequence success from one combined binary X label per ordered sequence.**
   - Its inputs are the original geometry plus *ideal-prefix* object states. They do not include achieved joint configurations.
   - It can represent geometric precedence. It can only absorb handoff effects implicitly.
   - It cannot identify the mechanism.
   - "Learns both linear and non-linear dependencies" is **not** a supported claim; see §8.

## 2. Final datasets: state and integrity

| | 2D | 3D |
|---|---|---|
| Roots (snapshot = expected) | 5,000 ✓ | 2,500 ✓ |
| TRAIN / VAL / TEST | 3,500 / 751 / 749 ✓ | 1,766 / 364 / 370 ✓ |
| K0 / K1 / K2 / K3 / NONE | 1,250 / 800 / 800 / 1,150 / 1,000 ✓ | 511 / 357 / 612 / 612 / 408 ✓ |
| Raw record per root, sha256 matched | 5,000 / 5,000 | 2,500 / 2,500 |
| Parent-family split leakage | none | none |
| X / Y labels in snapshot | 12,400 X (9,300 selected-order + 3,100 omission) | 7,089 X (5,253 + 1,836) |
| Snapshot and selection manifest sha vs lock | unchanged | unchanged |
| Known K exceptions | 60 `FLAGGED_NO_FINALIZED_X1Y1_ORDER` (K1 23, K2 10, K3 27) | 8 `FLAGGED_SHORTER_REPAIR_PROVEN` + 3 `NO_FINALIZED_X1Y1_ORDER` |

**Sources** (from the raw records' `construction.method`):

**2D K2/K3:**
- 633 original: `exact_cover2d` 600, `convert2d` 23, `route` 10.
- 510 dependence re-parking: `repark2d` NEAR_OTHER_MOVER 460, ALT_PARKING 47, TWO_STAGE 3.
- 807 hard-order re-parking: `hardk3_2d`, with path mechanisms BLOCK_PICK 980 and BLOCK_PLACE 150.

**3D K2/K3:**
- 847 published original (`route` / `bd_3dt`).
- 22 published run-dependent K3.
- 5 generated V4.
- 37 dependence re-parking: ALT_PARKING 23, NEAR_OTHER_MOVER 14.
- 313 hard-order: V3 202, V4 111; BLOCK_PICK 282, BLOCK_PLACE 205.

**K is a minimum within a finite teacher search, not a proven minimum, in both domains.**
- 2D limits: pool ≤ 4–5 objects, first parking cell only, ≤ 14 sequence tries, fixed per-query budget.
- 3D limits: pool ≤ 6, BFS over q_ref plans, first parking only, ≤ 8 executed sequences, RRT 5,000 iterations.
- Exception: 2D exact-cover roots where `K_static == verified_K` have K proven within the static screen model.

## 3. How handoff (linear) dependence was generated or allowed

**Allowed everywhere; constructed nowhere.**

**Carried state:**
- Every legacy and finalized-X execution carries the robot state between relocations:
  - 2D: `p16_common.verify_sequence`, `bxy_teacher.x_query` l.211-223.
  - 3D: `bd_3dt.seq` with `RETURN_TO_READY=False`; `fin3d.run_x`.
- The next plan starts from the achieved q (2D `p16_motion.py:175`; 3D `bd_3dt.py:101`).

**How q affects the outcome:**
- 2D: through the start-state clearance check, the pregrasp connector, candidate ordering, and q-keyed RRT seeds and caches.
- 3D: through IK branch ordering (by distance to q0) and the RRT free move from q0.
- 3D also has at least one deterministic carried-state failure in the published data: "start configuration is in collision" in `3ds66-lap3-w0141-s002`. It is bucketed as NO_PLAN_FOUND.

**No check isolates the mechanism:**
- No generator ever evaluates the same step from q_ref and from the achieved q in the same intermediate state.
- No record stores such a pair.
- The 2D teacher's per-step `steps`/`detail` and the 3D audit permutations' `steps` were dropped at write time.

## 4. How geometric (non-linear) dependence was generated or allowed

### Original generators (independence intended)

**2D `bd_2d_plus.independent()` and 3D `bd_3dt_plus.independent()`.** Both plan each mover from q_ref:
- (i) in the original scene, and
- (ii) with **all** other movers parked.

Effect on intermediate-subset independence:
- For K2 this covers both predecessor subsets.
- **For K3 the singleton subsets {b} and {c} are never checked.** The check therefore does **not** establish intermediate-subset independence (P2).
- 2D exact cover repeats only the original-scene check after distractors are added (`bd_2d_exact.py:424-425`).
- The annotation `independent_moves=True` means exactly this weaker check. Roots that failed it were rejected (`run_2d_plus.py:86-89`, `run_shelf66_full.py:151-158`).

**Annotations contradicted by finalized-X evidence:**
- 2D: 48 roots with `independent_moves=True` (24 K2, 24 K3) have a *configuration-independent* blocking certificate under the finalized teacher. Example: `2d-conv-plus2d-srv-w0098-s010`, where parking o00 at cell 38 certifiably blocks o01's placement at cell 39.
- 3D: 34 such roots have a certificate-supported geometric flag, and 6 have a step-0 failure from q_ref.
- The 3D docstring claim "each object moves once and in any order" is false for K3: of the 517 published K3 layouts that passed the check, only 184 are 6/6 under legacy execution.

**Not inherited.** Every re-parked or hard-order variant writes `independent_moves = None`: 0 roots in either domain carry `True` after a destination change. In 3D, however, children *do* inherit the parent's `construction` block and a stale `alt_parking`. Example: `D3H_GVLAB_5cb1c4a878`, where `alt_parking.o00[0] = [4,1]` but the actual destination is [2,3]. Read that block with care.

### Dependence-seeking and hard-order generators (precedence intended)

**Re-parking** (2D `dep2d` REPARK, 3D `dep3d` REPARK). Moves one destination to within Chebyshev 1–2 (2D) or exactly 1 (3D) of another mover's initial cell. This is blocking by construction.
- The 3D methods report says "1–2 cells"; the code uses 1.

**CHAIN / DOUBLE** (`dep2d`, `dep3d`). Adds obstacles that make a mover un-pickable from q_ref in S0. This is enabling by construction.

**`dep2d_k3` K3_STRONG.** Requires X→Y to fail at step 1 while Y→X succeeds.

**Hard-order** (`hard2d`, `hard3d`). Greedy BLOCK_PICK / BLOCK_PLACE destination moves, accepted when the number of successful legacy orders drops.

**Common to all of these:**
- None runs an independence or subset check.
- Every acceptance test is a **carried-state legacy** outcome, which includes the target executed from the achieved q.
- The construction intent (`mechanism`, `path[].mechanism`) is recorded, but it is an *intent*, not a verified mechanism.

**Data confirmation of the intent:**
- **Step-0 failures from (S0, q_ref).** These occur only in the new families:
  - 2D: 0 of 633 original roots, versus 86 of 510 dependence and 224 of 807 hard-order roots.
  - 3D: 6 of 847, versus 10 of 37 and 121 of 313.
  - These are precisely the enabling-type constructions; original roots satisfy P1 by construction.
- **Certificate-confirmed geometry (2D):**
  - hard-order 462 of 807 (57.2%);
  - dependence 135 of 510 (26.5%);
  - original 46 of 633 (7.3%).

## 5. Order strength: legacy and finalized X, never mixed

All permutations of a root share one object→destination assignment (gate 3: 1,950 and 1,224 of 1,950 and 1,224). Strength counts finalized X = 1 over all permutations. Legacy is the complete task with the target executed from the achieved q.

| 2D | 0/n | 1/n | 2/n | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---|---|---|---|---|---|---|
| K2 finalized X (800) | 10 | 449 | 341 | | | | |
| K2 legacy | 0 | 480 | 320 | | | | |
| K3 finalized X (1,150) | 27 | 342 | 289 | 211 | 78 | 80 | 123 |
| K3 legacy | 0 | 403 | 326 | 172 | 78 | 67 | 104 |

| 3D | 0/n | 1/n | 2/n | 3/6 | 4/6 | 5/6 | 6/6 |
|---|---|---|---|---|---|---|---|
| K2 finalized X (612) | 0 | 21 | 591 | | | | |
| K2 legacy | 0 | 23 | 589 | | | | |
| K3 finalized X (612) | 0 | 203 | 114 | 57 | 54 | 116 | 68 |
| K3 legacy | 0 | 210 | 112 | 53 | 46 | 121 | 70 |

**Notes:**
- Per-split tables are in `DATASET_SUMMARY.json` → `order_strength`.
- **Y = 0 at the selected endpoint:**
  - 2D: 0 K2/K3 roots.
  - 3D: 2 roots (1 K2, VAL; 1 K3, TEST).
- X = 1 is never treated as task success. Task success is X = 1 *and* Y = 1, with Y shared per endpoint (gate 5).
- **3D K2 is almost entirely order-independent:** 591 of 612 roots are 2/2.

## 6. Failure locations and kinds (order level; locations, not causes)

| | 2D | 3D |
|---|---|---|
| Finalized X success | 4,134 | 3,009 |
| First relocation fails | 590 (CERTIFIED 253, planner 337) | 360 (cert-supported 162, no-plan 176, execution 22) |
| Later relocation fails | 3,553 (CERTIFIED 1,385, planner 2,168) | 1,502 (cert-supported 837, no-plan 603, execution 62) |
| Terminal connector fails | 223 (UNKNOWN_TRANSIT, budget-limited) | 25 (CONNECTOR_NO_PLAN) |
| Legacy fails at the original target step | 395 (312 of these are finalized X = 1, Y = 1) | 29 (26 are X = 1, Y = 1) |

**Notes:**
- **"Planner" failures are not proofs of infeasibility.**
  - 2D `UNKNOWN_PLANNER` = NO_PLAN_FOUND within budget. It also absorbs some certified planner results whose detail string was not stored.
  - 3D NO_PLAN_FOUND includes RRT exhaustion and "start configuration is in collision".
- **Legacy versus finalized X:**
  - Legacy and finalized X agree at every relocation step: the computation is the same.
  - They differ only at the end: legacy fails at the target from the achieved q, while finalized X fails at the connector.
  - Where a legacy order failed at the target but finalized X = 1, the legacy "order dependence" was a target-from-achieved-q effect.
  - 65 2D roots and 9 3D roots are `LEGACY_TARGET_ONLY`: every finalized order succeeds.

## 7. Causal classification (K2/K3; denominators in parentheses)

**Basis of the primary classes.**
- **Confirmed** classes rest only on configuration-independent certificates, i.e. matched object states at a common configuration.
- **Suspected** mechanisms are non-exclusive flags and are not counted as confirmed.

| Primary class | 2D K2 (800) | 2D K3 (1,150) | 3D K2 (612) | 3D K3 (612) |
|---|---|---|---|---|
| HANDOFF_ONLY_CONFIRMED | 0 | 0 | 0 | 0 |
| GEOMETRIC_BLOCKING_CONFIRMED | 99 (12.4%) | 415 (36.1%) | 0 | 0 |
| GEOMETRIC_ENABLING_CONFIRMED | 27 (3.4%) | 73 (6.3%) | 0 | 0 |
| GEOMETRIC_BLOCKING_AND_ENABLING_CONFIRMED | 0 | 29 (2.5%) | 0 | 0 |
| MIXED_CONFIRMED | 0 | 0 | 0 | 0 |
| CONNECTOR_ONLY | 33 (4.1%) | 16 (1.4%) | 5 (0.8%) | 4 (0.7%) |
| LEGACY_TARGET_ONLY | 39 (4.9%) | 26 (2.3%) | 7 (1.1%) | 2 (0.3%) |
| PLANNER_LIMITED_OR_INCONCLUSIVE | 290 (36.3%) | 398 (34.6%) | 14 (2.3%) | 157 (25.7%) |
| UNKNOWN_REQUIRES_CONTROL | 0 | 69 (6.0%) | 2 (0.3%) | 383 (62.6%) |
| NO_ORDER_CONTRAST (independent under finalized X) | 302 (37.8%) | 97 (8.4%) | 584 (95.4%) | 66 (10.8%) |
| NO_VERIFIED_SUCCESSFUL_ORDER | 10 (1.3%) | 27 (2.3%) | 0 | 0 |

**Non-exclusive evidence flags** (2D K2 / 2D K3 / 3D K2 / 3D K3):
- **Fixed-ideal-geometry carried-state contrast** (the only controlled handoff contrast in existing data; K3, step 3):
  - planner-limited: 0 / 77 / 0 / 20;
  - with a 3D certificate-supported failing side: 0 / 0 / 0 / 5.
- **3D certificate-supported geometry:**
  - blocking 2 (K2) and 303 (K3);
  - enabling 32 (K3).
- **Suspected, confounded comparisons** (geometry and q both changed):
  - blocking-or-handoff: 251 / 550 / 12 / 226 (multi-q 0 / 435 / 0 / 152);
  - enabling-or-q-dependent: 47 / 136 / 2 / 125.
- **Unexplained relocation failures remaining** (even where geometry is confirmed): 298 / 814 / 16 / 540.

**Confidently classified from existing evidence alone** (no mechanism question, or every failure explained by confirmed geometry):

| | K2 | K3 | K2+K3 | TRAIN / VAL / TEST |
|---|---|---|---|---|
| 2D | 511 of 800 (63.9%) | 363 of 1,150 (31.6%) | 874 of 1,950 (44.8%) | 43.7 / 46.8 / 47.9% |
| 3D | 596 of 612 (97.4%) | 72 of 612 (11.8%) | 668 of 1,224 (54.6%) | 54.1 / 61.1 / 51.1% |

- In 3D this is almost entirely K2 "no contrast".
- **No 3D root with a relocation-order contrast is mechanism-resolved.**

**By source family:**
- **Where true geometric precedence is most common:** hard-order re-parking (2D 57% confirmed), then dependence re-parking (2D 26%). In 3D, the hard-order K3 roots carry 290 of the 383 UNKNOWN_REQUIRES_CONTROL.
- **Original roots** are mostly order-independent: 2D 399 of 633 and 3D 650 of 847 are NO_ORDER_CONTRAST.
- Per-family details are in `DATASET_SUMMARY.json` → `by_family`.

## 8. The learning claim (Approach B, `approach_b_final/xy.py`)

| Question | Answer (code) |
|---|---|
| Original scene geometry | Yes: `xy0`, attrs, target, goal, base, ctx. 3D ctx includes q_ref (l.1-36, 106-147) |
| Ordered actions | Yes: ordered action tokens with predecessor-pair mixing (`actions`, `order`, l.276-306; arm D `order: "pred"`) |
| Ideal intermediate object states | Yes: tokens are encoded on the **ideal prefix** scene (`xy2` update per step, l.284-293) |
| Achieved robot joint configurations | **No.** "No new energy, causal graph or q-state head" (docstring) |
| Separate geometric vs handoff output | **No.** One X logit `a_r + w_r·y` per ordered sequence, coupled to Y |
| Trained on sequence-level X only | Yes: one X node per ordered key; omissions and on-policy items are additional sequences, not steps |
| Connector inside X | Yes (finalized protocol) |
| Same-endpoint contrasts | 2D 1,950 roots × 2/6 orders; 3D 1,224. But 650 3D roots (53%) have no X contrast; 3D K2 has 21 contrast roots |

**Additive TRAIN-only on-policy labels** (V2/V3 `onpolicy.py`; the frozen V3.4 scorer is D-expanded):
- These are extra ordered queries on TRAIN roots, including "every constructed order of the selected repair's assignment".
- They carry the same combined X label. They add same-endpoint contrasts, not mechanism information.
- They are *not* part of the 2/6-permutation strength audited here.

**Supported wording:**
- The model learns **order-sensitive sequence feasibility (X) and endpoint feasibility (Y)** from a single combined label.
- It has **access to ideal intermediate geometry**, so geometric precedence is representable.
- Carried-state effects are only absorbed **implicitly**, as a function of the action order, because q is never observed.

**Not supported:**
- "learns both linear and non-linear dependencies";
- any mechanism-level attribution.

**The `Order` metric** (`order_acc`, `xy.py:583-600`):
- It is pairwise ranking accuracy over **same-endpoint, Y = 1, discordant finalized-X** pairs.
- It mixes geometric, carried-state, planner-budget and connector contrasts.
- It is **not** a handoff-only discrimination measure.

## 9. Required corrections to descriptions and claims

1. **Do not describe K2/K3 ordering labels as "handoff" or "linear" dependence, and do not describe them as a mixture with known proportions.**
   - Say instead: "order-sensitive finalized X; geometric precedence confirmed by configuration-independent certificates in 33% of 2D K2/K3 roots; mechanism otherwise unresolved."
2. **`independent_moves=True` means:**
   - each mover is planned from q_ref in (i) S0 and (ii) the scene with all other movers parked;
   - K3 singleton subsets are not checked;
   - carried state is not considered.
   - Finalized-X geometry contradicts it in 48 2D roots (configuration-independent certificate).
   - It is challenged in 34 3D roots (certificate-supported only).
3. **"Verified K"** should read "minimum within the finite teacher search". Exception: 2D exact-cover roots where `K_static == verified_K`.
4. **Report-text discrepancies to fix:**
   - `DEPENDENT_GENERATION_METHOD_AND_VALIDATION.md`:
     - says dependence affects only "the next pick" (step-0 enabling also exists);
     - says "1–2 cells" for 3D re-parking (the code uses 1);
     - says asserts are used in REPARK (it uses a filter only).
   - `2D_TARGET_ORDER_STRENGTH_AND_REBALANCING_AUDIT.md:95`, "No failing order fails on the first relocation": true only for original roots. 310 new 2D roots fail at step 0.
   - `K3_HARD_ORDER_GENERATION_REPORT.md:3`, "planner-budget failure = 0": true only for UNKNOWN_BUDGET. UNKNOWN_PLANNER is the most frequent hard-order failure.
   - `FINAL_2D_TARGET_DATASET_REPORT.md`: describes selection V2. The final dataset is V3.
5. **Selection used legacy strength for slot assignment** (3D `select_final3d.py:77-97,147`; 2D selection V3 `n_success`), with finalized X as a tie-break.
   - Every strength quoted for model evaluation must be finalized X. Legacy strength must be labelled as such.
6. **Snapshot annotation gap (gate 4c).**
   - 73 original 2D K3 roots carry `legacy_y` for only some permutations; the full legacy outcomes are in `order_classification_2d/per_scene_six_permutation_outcomes.jsonl`.
   - This does not affect training labels (legacy_y is metadata), but it is reported, not suppressed.
7. **The `Order` metric** should be labelled "same-endpoint X ranking", not handoff discrimination.
   - A separate handoff-specific metric needs P2/P4-controlled labels; see the plan.

## 10. What is still needed

The plan is in `COUNTERFACTUAL_AUDIT_PLAN.md`. Two kinds of controlled query are missing:
- **REF:** F(a | S_P, q_ref) for every action and every non-empty predecessor subset. 2D queries already implied by a configuration-independent certificate are omitted.
- **CARRIED:** F(a | S_P, q(prefix)) for every prefix never executed.

Restricted to the 1,693 roots that need controls (2D 1,128; 3D 565), the queries break down as:

| | REF, \|P\|=1 | REF, \|P\|=2 | CARRIED, \|prefix\|=2 | Total |
|---|---|---|---|---|
| 2D | 5,142 | 2,190 | 889 | 8,221 |
| 3D | 3,306 | 1,632 | 682 | 5,620 |

**Pilot** (`PILOT_QUERIES.jsonl`):
- 70 TRAIN roots (12 per family and domain: 8 K3 + 4 K2), with 600 queries.
- Nothing runs until you approve it.

## 11. Integrity gates (`GATES.json`)

| Gate | 2D | 3D |
|---|---|---|
| 1 Root counts and split identities | PASS | PASS |
| 2 No V3.4 expanded-cohort root | PASS | PASS |
| 3 Permutations share one assignment, complete 2/6 | PASS | PASS |
| 4 Finalized strength recomputed = snapshot meta | PASS | PASS |
| 4b Legacy strength = meta (after per-scene fallback) | PASS | PASS |
| **4c Snapshot per-order legacy_y complete** | **FAIL: known exception, 73 roots (§9.6)** | PASS |
| 4d Failure kind resolved for every X = 0 | PASS | PASS (3D kinds come from the legacy same step or the replay audit) |
| 5 Y shared across identical endpoints | PASS | PASS |
| 6 X provenance retained | PASS | PASS |
| 7 No binary failure promoted to certified impossibility | PASS | PASS |
| 8 No handoff inferred from a later-step failure alone | PASS | PASS |
| 9 No geometric claim without matched comparison or valid certificate | PASS | PASS |
| 10 Per-scene classes sum to the aggregate counts | PASS | PASS |
| 11 Known integrity exceptions reported | PASS (K exceptions, 4c, report discrepancies) | PASS |
| 12 Deterministic re-run | PASS: two runs gave byte-identical artifacts | PASS |
| 13 Snapshot and selection manifests unchanged (sha vs lock) | PASS | PASS |
| 14 Evidence references resolve | PASS | PASS |

**Small residual inconsistency** (3D legacy sources). For 4 orders, the historical per-scene legacy record and the fresh-env legacy record disagree on the kind: 3 have `legacy_other:None` and 1 has `legacy_success|CERTIFIED`. They are listed in `FAILURE_MECHANISM_SUMMARY.json` and do not affect any primary class.
