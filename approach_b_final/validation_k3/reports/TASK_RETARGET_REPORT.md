# Experiment C: does explicit cVAE task conditioning matter, and does task reassignment transfer?

**Sources and scope**
- **Models:** the frozen bundle sampler (`TaskCVAE scratch_all` s0) and the NoTask cVAE s0 from the ablation.
- **Scripts:** `retarget.py` (task reassignment of the learner view), `cvae_probe.py` (C2/C4) and `ttarget.py` (C3, physical).
- **Outputs:** `runs/out/cvae/C2C4_{dom}.json` and `runs/out/ttarget/TT_{dom}.json`.
- **Statistics:** VAL roots only. CIs are 95% cluster bootstraps over roots.

## C1. What the conditioning can see (code audit)

| Component | Inputs (`placement.scene_features`, `task_features`, `search.Root`) |
|---|---|
| Scene encoder (`SceneEncoder`, 14 features per object) | 2D: radius, is_fixed, row/col, x/y, distance/angle to the robot base, is_query, offsets to the queried object. 3D: is_box, is_cyl, size, height, plus the same positional features. **No target flag, no goal.** Occupancy grid. |
| Task branch (`TaskEncoder.task`, additive) | Goal one-hot; current target-cell one-hot; query→goal and query→target offsets; the root context vector (2D: robot reference pose (sin/cos), goal xy, gripper gap; 3D: reference pose, goal xy, target size/height/is_box); `task_on` flag. |
| Queried-object representation | The is_query flag and the query-relative offsets, in the scene encoder. |
| Decoder | [encoder output, z] → logits over cells, masked to legal destinations. |
| Legal mask (inference and training) | Declared support, minus initially or currently occupied cells, **minus the goal cell**. |

**What NoTask receives**
- NoTask (`scratch_all_notask`) zeroes the whole task-feature vector, including the robot context.
- It therefore receives **no explicit or implicit target or goal input**. The scene features carry no target identity: 2D discs all have r = 0.024, and the target attributes are not passed to `pattr`.
- **The only task-dependent information it can use** is the legal mask, which excludes the goal cell. This affects only the output support.
- **Matched training (P0_P3_REPORT, re-checked):** same scratch init sha `79d9991d410c`, same examples and weights, and same fixed step budget (2D 2,400 / 3D 1,520) with VAL selection.
- **Training signal:** it is trained on the same verified destinations, so it learns the task-*marginal* placement prior given the scene.

## C2. Same-scene task sensitivity (VAL; 2D 751 roots, 3D 364 roots)

**Method**
- Per (root, queried movable object), the destination marginal is estimated from 512 prior draws, with common random numbers across contexts.
- Contexts compared: the **true** task, a **goal-swapped** task (a legal free cell at Chebyshev distance ≥ 2 from the true goal, chosen by a label-blind sha rule), and a **target-swapped** task (another movable object made the target, chosen by a label-blind sha rule).
- Every target-specific field is updated: tid, the target/obstacle attribute flags, goal xy in the context vector, and in 3D the target size/height/box. Retarget identity and round-trip self-tests: **0 failures on all 751 / 364 VAL views**.

| | 2D task cVAE | 2D NoTask | 3D task cVAE | 3D NoTask |
|---|---|---|---|---|
| JS divergence, goal swap (common legal set) | 0.027 | 0.000 | **0.145** | 0.000 |
| JS divergence, target swap | 0.035 | 0.000 | 0.032 | 0.000 |
| JS divergence, MC-noise floor (two generators) | ≈0.000 | ≈0.000 | ≈0.000 | ≈0.000 |
| JS divergence, between two queried objects (scale reference) | 0.086 | 0.051 | 0.359 | 0.341 |
| Top-4 overlap, goal swap / target swap | 0.77 / 0.77 | 0.96 / 1.00 | 0.61 / 0.84 | 0.94 / 1.00 |
| Mass on the true target→goal corridor (goal cells excluded): true / goal-swapped / target-swapped context | 0.092 / 0.108 / 0.112 | 0.119 / 0.117 / 0.119 | 0.099 / 0.134 / 0.105 | 0.106 / 0.106 / 0.106 |
| **Recall@4 of known successful (object, cell)**: true task | 51.3 | 49.1 | 77.7 | 75.7 |
| … goal-swapped context | 46.0 | 47.9 | 61.2 | 73.8 |
| … target-swapped context | 48.4 | 49.1 | 75.1 | 75.7 |
| Paired: true − goal-swapped (pp) | **+5.3 [2.4, 8.4]** | +1.2 [0.1, 2.3] (legal-mask effect only) | **+16.5 [11.2, 21.9]** | +1.9 [0.0, 4.0] |
| Paired: true − target-swapped (pp) | +2.8 [0.0, 6.0] | 0 | +2.6 [−0.3, 5.8] | 0 |
| **Paired: task cVAE − NoTask, true context (pp)** | +2.2 [−0.9, 5.4] | | +1.9 [−2.3, 6.3] | |

Recall is computed over 774 (2D) and 309 (3D) known-success ingredients on movable objects.

**Reading**
1. **Explicit task conditioning measurably shapes the destination distribution.**
   - The changes exceed the Monte-Carlo noise floor by orders of magnitude. They are strongest for the goal in 3D.
   - They move probability mass *off* the true corridor when the true task is supplied.
2. **The conditioning is physically meaningful when the task is wrong.** A wrong goal costs 5 pp of recall in 2D and 17 pp in 3D.
3. **Removing the conditioning altogether costs only about 2 pp of recall (n.s.).** The NoTask model's task-marginal prior already places most of the useful destinations.
   - This matches the physical null of the NoTask ablation (−0.9 to +0.8 pp task success).
   - **Conditioning is used and is not harmful, but at K≤3 it adds little over a strong scene-only prior.**

## C4. Intermediate-scene generalization (no new labels)

**Set-up**
- For known successful 2- and 3-move assignments, the recall@4 of the j-th ingredient is compared between two queries:
  - asked in S0 (as deployed: all proposals are made once, in S0);
  - asked in the scene after the preceding verified move(s), re-rooted with the target cell updated.
- The cVAE was trained on S0 contexts only.

| | 2D task cVAE | 2D NoTask | 3D task cVAE | 3D NoTask |
|---|---|---|---|---|
| After 1 preceding move: recall S0 → intermediate | 55.1 → 58.5 (n 602) | 52.3 → 54.2 | 79.8 → 71.7 (n 396) | 80.3 → 69.9 |
| After 2 preceding moves | 54.7 → 62.6 (n 439) | 51.3 → 53.1 | 81.3 → 66.5 (n 209) | 84.2 → 49.8 |
| Paired intermediate − S0 (pp) | **+5.3 [2.5, 8.2]** | +1.8 [−0.7, 4.3] | **−10.4 [−15.3, −5.4]** | −18.7 [−24.0, −13.6] |

**Reading**
- **The two domains go in opposite directions.**
  - In 2D, re-querying in the intermediate scene *helps*: preceding moves free space and the decoder adapts.
  - In 3D it *hurts*, and more so with more preceding edits. The 3D shelf scenes after edits drift away from the S0 training contexts.
- **Implication for recursive reuse:** a recursive planner that re-queries the frozen cVAE at intermediate scenes is supported in 2D, but would need intermediate-scene training data (or augmentation) in 3D.

**Scorer-side evidence on edited scenes** (the frozen D on labeled endpoints, by number of edited objects): Y AUROC on edited endpoints is 0.88–0.96 (`coupling/*.json`), and X/Z metrics by sequence length are in `coupling` `by_K`.

## C3. Temporary-target tasks (physical; separately versioned adapter TT_ADAPTER_V1)

**Adapter**
- The frozen teachers hard-code `t0`. The adapter writes a new raw record in which the temporary target A carries id `t0` (kind target) and the original target takes A's id (kind obstacle, role `temporary_obstacle`). The goal becomes d_A. Every other field the teachers read is unchanged, and a `~TT~` root-id tag keeps caches separate.
- **The teachers themselves are unmodified.**
- The learner views are retargeted with `retarget.py`. Oracle labels never enter model inputs or proposal selection.

**Adapter validation** (all examples, both rounds)

| | 2D (60 + 49) | 3D (60 + 22) |
|---|---|---|
| Identity parity: the verified sequence re-taught on the unchanged record reproduces X=1, Y=1 | 109/109 | 82/82 |
| RNG-key noise floor: same task with only the root-id tag changed (planner seeds change) | 109/109 unchanged | 82/82 unchanged |
| Semantic cross-check: X(original; move o1→d1) vs Y(temporary task A=o1, goal d1). Different planners, so agreement is not required. | 101/109 agree (X0/Y1 6, X1/Y0 2) | 75/82 agree (X0/Y1 7) |

**Examples**
- **Round 1:** A = the *last* moved object of a verified K≥2 sequence. Only 4/60 (2D) and 4/60 (3D) are blocked in S0, so this round is reported only for Y calibration.
- **Round 2 (C3b, preregistered after round 1):** A = the object whose move came *first* in a Y=1 ordering that failed at relocation 0, while another ordering of the same endpoint verified. That makes A genuinely blocked, and the verified preceding moves are its corrective placements.

| C3b (blocked temporary targets) | 2D (49) | 3D (22) |
|---|---|---|
| Blocked in S0 (Y_τ(S0) = 0) | 39 | 22 |
| The verified preceding moves repair the temporary task | 31/39 | 20/22 |
| cVAE top-4 contains a one-step fix: temporary-task context / original context / NoTask | 94.9% / 94.9% / 97.4% | 90.9% / 90.9% / 90.9% |
| Fix rate per proposal, same three contexts | 29.0% / 29.4% / 27.0% | 15.0% / 15.1% / 16.5% |
| Frozen D (retargeted view) argmax-p11 one-step candidate succeeds | **66.7%** (vs 27.3% random) | **63.6%** (vs 14.5% random) |
| Frozen Y_τ on retargeted endpoints: AUROC / ECE / mean p vs positive rate | 0.69 / 0.19 / 0.26 vs 0.43 | 0.82 / 0.18 / 0.41 vs 0.25 |
| Round 1, Y_τ (mostly easy tasks): AUROC / ECE | 0.75 / 0.42 (mean p 0.45 vs 0.87) | 0.78 / 0.18 |

**Comparison point:** Y AUROC on the original tasks' edited endpoints is 0.88–0.96.

## Required conclusions

1. **Does explicit task conditioning influence the destination distribution?** **Yes.** The changes sit far above the MC noise floor, move probability mass off the true target–goal corridor, and depend most on the goal (C2).
2. **Does that influence improve physical usefulness?**
   - **Only when the alternative is the wrong task.** A wrong goal loses 5 pp (2D) and 17 pp (3D) of recall.
   - **Against no conditioning, the gain is small and n.s.** Recall: +2.2 / +1.9 pp. K≤3 physical success: NoTask −0.9 to +0.8 pp, n.s.
   - **On blocked temporary tasks it is the same** as with the original-task context or with NoTask (C3b).
3. **Does retargeting transfer to temporary object-relocation tasks?** **Partly.** The proposals contain a physically verified one-step fix for 91–97% of blocked temporary tasks, but that comes from the task-agnostic placement prior: retargeting the context adds nothing.
4. **Does the frozen Y evaluate reassigned tasks correctly?**
   - **Ranking: moderately.** AUROC 0.69–0.82 vs 0.88–0.96 on the original tasks.
   - **Calibration: miscalibrated** (ECE 0.18–0.42; strongly under-confident on easy 2D temporary tasks).
   - **As a selector it still helps:** among one-step candidates, the argmax of the frozen D's p11 succeeds 64–67% vs 15–27% at random.
5. **Is recursive reuse justified?** **Partially supported, not established.**
   - **The frozen D's ranking transfers well enough to guide selection** on reassigned tasks, and the frozen cVAE's (largely task-agnostic) proposals contain fixes.
   - **What blocks it:**
     - (a) Y calibration on reassigned tasks is poor, which matters for any threshold or gate.
     - (b) Explicit retargeting of the cVAE context gives no measurable benefit.
     - (c) In 3D, cVAE recall drops in intermediate scenes (C4).
   - **What a K>3 recursive claim needs:** at minimum, recalibration (or training) of Y on reassigned and intermediate tasks. Physical verification beyond 6 relocations also needs the versioned teacher extension (`K_GT6_TEACHER_AUDIT.md`).
