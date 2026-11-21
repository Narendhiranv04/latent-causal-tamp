# CF / NULL counterfactual audit: final report (P7)

> **Two intervention families are reported.**
> - **PROP_V1 (move one obstacle, task-level):** prescribed by `plan.md`. Gives the main table below.
> - **PROP_INS_3D (paper-faithful corridor insertion at a fixed grasp, arXiv:2611.09130):** added in amendment 4 after the owner asked for the paper's construction; see its own section.
>
> They give the same model ranking.

Branch `naren/cf-null-audit`, from `e9fa587c3b`. All compute ran on the laptop: ≤ 29 of 32 cores, the GPU with one model at a time, and no remote compute. No training, tuning or threshold fitting was done; the threshold is 0.5 throughout. The protocol is `reports/PROTOCOL_LOCK.json` (`CF_NULL_PROTOCOL_LOCK_V1`). It has three dated amendments, each registered before the scores or labels it affects:
1. cf_teacher robustness fix;
2. PIGINet-noimg and SCNet available;
3. 2D proposal family PROP_V2.

## What was measured

| | |
|---|---|
| Query | the original target task from q_ref (t0 → goal), one physical target-Y query per state |
| Triplet | **BASE**: a physically re-verified feasible state (y = 1). **CF**: the same state with ONE non-target obstacle moved, relabelled y = 0. **NULL**: the same obstacle moved elsewhere by a matched displacement, still y = 1. Same objects, target, goal and robot reference throughout. |
| Cohorts | **STRONG**: CF y = 0 is *certified* (3D: every one of the 32 grasps fails a deterministic geometric check; 2D: teacher `CERTIFIED_INFEASIBLE`). **BUDGET**: CF y = 0 is only planner-budget-limited. Reported separately, never called infeasible. |
| Model readouts | **Ours**: endpoint Y `sigmoid(b)` (p_noop), never p11. **GRN**: sigmoid of the action head. **PIGINet-noimg**: plan head on the "move T" sample. **SCNet**: max over the 32 grasps of P(grasp works). Seeds s0–s2 plus the seed mean. |
| Metrics | **CF-pair AUROC**: pooled BASE (positive) vs CF (negative), midrank ties. **NULL retention**: % of NULL states scored ≥ 0.5. Also flip-rank, CF blocked accuracy, conditional NULL retention and BASE accuracy. 95% CIs from 2,000 lineage-bootstrap replicates, seed 0. |
| Oracle quality | rates over **all** attempted proposals: certified CF flip rate, and NULL false-flip rate (dataset metrics, not model metrics) |

## Main table: 3D, STRONG triplets (n = 224, historical 3D TEST)

| Model | CF-pair AUROC [95% CI] | NULL retention (%) [95% CI] | flip-rank | CF blocked acc | BASE acc |
|---|---|---|---|---|---|
| PIGINet (no image) | **0.948** [0.930, 0.964] | **92.0** [88.4, 95.1] | 0.982 | 0.759 | 0.933 |
| SceneCollisionNet | 0.901 [0.872, 0.928] | 81.2 [76.3, 86.2] | 0.942 | 0.835 | 0.812 |
| **Ours** | 0.898 [0.873, 0.922] | 85.3 [80.8, 89.7] | 0.955 | 0.679 | 0.853 |
| GRN | 0.783 [0.748, 0.820] | 54.0 [47.8, 60.3] | 0.893 | 0.830 | 0.603 |
| constant 0.5 (control) | 0.500 | 100 (trivial) | 0.500 | 0.000 | 1.000 |

Per-seed values, s0 / s1 / s2:

| Model | AUROC | NULL retention (%) |
|---|---|---|
| Ours | .895 / .898 / .876 | 85.3 / 85.3 / 81.2 |
| PIGINet | .926 / .932 / .934 | 88.8 / 89.3 / 93.8 |
| SCNet | .898 / .882 / .898 | 83.0 / 83.0 / 77.7 |
| GRN | .779 / .776 / .775 | 58.9 / 54.9 / 49.1 |

**Reading:**
- PIGINet-noimg ranks the matched clear/blocked pairs best and is the most stable on NULLs.
- Ours and SCNet tie on CF-pair AUROC (overlapping CIs). Ours keeps more NULLs feasible (85.3% vs 81.2%) but flags fewer CFs as blocked at 0.5 (0.679 vs 0.835).
- GRN reacts to almost any obstacle move: it keeps only 54% of NULLs.
- This is a frozen-model audit. Ours is not the best model on this test, and the report says so.

By base kind, seed mean, STRONG cohort:

| Base kind | n | Ours | PIGINet | SCNet | GRN |
|---|---|---|---|---|---|
| Repair endpoints (Y = 1 endpoint of a stored TEST repair) | 198 | .911 / 85.4% | .950 / 91.9% | .914 / 82.8% | .794 / 55.1% |
| K0 TEST roots | 26 | .791 / 84.6% | .911 / 92.3% | .824 / 69.2% | .710 / 46.2% |

**3D BUDGET cohort** (n = 21, budget-limited CF negatives), AUROC / NULL retention:

| Model | AUROC | NULL retention |
|---|---|---|
| SCNet | .912 | 76.2% |
| PIGINet | .889 | 90.5% |
| Ours | .864 | 90.5% |
| GRN | .755 | 61.9% |

CIs are wide, about ±0.1.

## Paper-faithful family PROP_INS_3D: corridor insertion at a fixed grasp (amendment 4)

The main table above uses the move-one-obstacle family that `plan.md` prescribed. That family does **not** reproduce the paper's construction. arXiv:2611.09130 Sec. 3 / App. F,H:
- the grasp pose is held fixed;
- a NEW solid box (edge 1.5–5 cm) goes into the 10 cm approach corridor at a 5–15 cm standoff, and the planner relabels the grasp;
- NULL is the matched box 30 cm off-corridor or 30 cm back;
- the paper's "Null" is the oracle false-flip rate.

PROP_INS_3D (`cf_insert.py`) is that construction on our shelf:

| | Paper | PROP_INS_3D |
|---|---|---|
| Fixed unit | one grasp pose | the BASE's winning grasp g* (labels `y_grasp` = pick-and-place planned through g*, plus the task Y) |
| Edit | insert a solid box in the approach corridor | insert a NEW box (edge 4 / 2.5 cm, height = target height: the paper's "resting pillar" form, since our objects stand on the lattice) on the free cell in g*'s corridor (standoff 0.05–0.15 m along −approach, lateral ≤ 3.75 cm). All accepted CFs: edge 4 cm, standoff 6.9–15 cm. |
| NULL | matched box 30 cm off-corridor / 30 cm back | the same box "30 cm back" (behind the target along the approach axis) first, else off-corridor (lateral ≥ 1.5 pitch). Accepted NULLs: 132 back, 135 lateral, mean 0.28 m from the CF cell. |
| Labels | RRT-Connect relabel, not certified | teacher planner relabel; every CF flip is a deterministic geometric failure (CERTIFIED) |

**Oracle (all attempted proposals, 287 bases):**

| | Paper (corridor 10 cm) | PROP_INS_3D |
|---|---|---|
| CF flip (fixed grasp) | 1.00 | **1.00** (616/616, all CERTIFIED) |
| CF flip (whole task) | n/a | 0.948 |
| NULL false-flip (fixed grasp) | 0.02 | **0.150** overall: **0.056** for "30 cm back" (25/448), 0.211 lateral (147/696) |

The NULL false-flip is higher than the paper's. Our shelf is only 45 cm wide, and the arm's carry path to the goal crosses most of it; GraspNet tabletop scenes have far more free space. Every NULL in an accepted triplet is still physically verified feasible (fixed grasp and task).

**Triplets:** 267 GRASP_FLIP (CF makes g* infeasible). 266 of them are also TASK_FLIP; the one exception keeps the task feasible through another grasp. Excluded: 3 bases whose g* re-plan failed, 16 with no feasible NULL, 1 with no free corridor cell. Visibility: the inserted box changes every model's input in 534/534 edited states.

| Model (GRASP_FLIP, n = 267, seed mean) | CF-pair AUROC [95% CI] | NULL retention (%) [95% CI] | flip-rank | CF blocked acc | BASE acc |
|---|---|---|---|---|---|
| PIGINet (no image) | **0.985** [0.978, 0.991] | **91.0** [87.6, 94.4] | 0.996 | 0.925 | 0.940 |
| SceneCollisionNet (max over grasps) | 0.954 [0.937, 0.970] | 79.0 [74.5, 83.9] | 0.989 | 0.951 | 0.816 |
| SceneCollisionNet, P(g*) (the paper's exact unit) | 0.952 [0.935, 0.969] | 66.3 [60.7, 71.9] | 1.000 | 0.996 | 0.727 |
| **Ours** | 0.934 [0.917, 0.951] | 84.6 [80.1, 89.1] | 0.996 | 0.779 | 0.869 |
| GRN | 0.722 [0.701, 0.748] | 39.0 [33.3, 44.6] | 1.000 | 0.712 | 0.614 |

Seeds s0 / s1 / s2:

| Model | AUROC | NULL retention (%) |
|---|---|---|
| Ours | .930 / .935 / .907 | 83.1 / 86.9 / 77.5 |
| PIGINet | .968 / .978 / .986 | 88.8 / 91.0 / 92.5 |
| SCNet | .948 / .946 / .948 | 79.0 / 79.8 / 74.5 |
| SCNet-g* | .942 / .940 / .946 | 66.3 / 67.8 / 57.7 |
| GRN | .737 / .705 / .706 | 44.6 / 41.6 / 33.7 |

TASK_FLIP (n = 266) gives the same values to within ±0.002.

**Reading:**
- In the paper's GraspNet setting most predictors sit at chance on CF-pair (≈ 0.50). Here every model responds to the inserted box, and PIGINet-noimg nearly separates the pairs.
- The difference is expected. These baselines were trained on this shelf's task labels, where corridor occupancy decides feasibility. The paper's models were trained on grasp labels that never varied an obstacle at a fixed pose.
- The ranking is the same as the move-one-obstacle family: PIGINet > SCNet ≥ Ours > GRN on AUROC; PIGINet > Ours > SCNet > GRN on NULL retention.
- The two families agree in direction, and Ours is not the best model in either.

### Why CF-pair is far above the paper's chance level (diagnostics)

Pooled AUROC, seed mean. Ideal: BASE>CF = 1, NULL>CF = 1, BASE~NULL = 0.5.

| PROP_INS_3D (n = 267) | BASE>CF | NULL>CF (same inserted box, placement only) | BASE~NULL |
|---|---|---|---|
| PIGINet | 0.985 | 0.979 | 0.560 |
| SCNet / SCNet-g* | 0.954 / 0.952 | 0.936 / 0.935 | 0.565 / 0.573 |
| Ours | 0.934 | 0.917 | 0.540 |
| GRN | 0.722 | **0.582** | 0.647 |
| Heuristic: fewer objects in the target's 8-neighbourhood (no learning) | 0.873 | 0.873 | 0.500 |
| Heuristic: fewer objects (count only) | 0.675 | 0.500 | 0.675 |

PROP_V1 (move family, n = 224):

| Model | BASE>CF | NULL>CF | BASE~NULL |
|---|---|---|---|
| Ours | 0.898 | 0.891 | 0.489 |
| PIGINet | 0.948 | 0.942 | 0.508 |
| SCNet | 0.901 | 0.906 | 0.531 |
| GRN | 0.783 | 0.744 | 0.542 |
| Neighbour heuristic | 0.659 | 0.686 | 0.475 |

**What this shows:**
1. **Placement, not clutter.** For PIGINet, SCNet and Ours, NULL>CF is close to BASE>CF, and BASE~NULL is close to 0.5. These models separate the blocking box from the same box elsewhere; they are not just penalising an extra object.
2. **GRN partly is.** Its NULL>CF is only 0.58 under insertion, and it drops on any added object (BASE~NULL 0.65). That is the closest analogue to the paper's finding.
3. **This domain's CF is easy.** A one-line neighbour-count heuristic reaches 0.873 under insertion. On a 6×6 lattice an object standing next to the target is a strong, simple blocking cue.

**Why the paper sees about 0.50 and we don't:**
- **Training data.** The paper's GraspNet predictors never saw "same grasp, obstacle in the corridor" contrasts, so they learn pose shortcuts. Our baselines were trained on this shelf's teacher labels, which contain exactly such contrasts: `labels.D` edits and lattice samples are the same scene with obstacles moved or parked, with flipped Y. This is the paper's own Table 6 regime ("train from scratch on CF: 0.991"), not its Table 1 regime.
- **Visibility.** In the paper the box is about 13 of 2,048 points. Here it is a first-class object: a token for PIGINet, a graph node for GRN, an object row for Ours, and about 450 cloud points for SCNet.
- **In-distribution edit.** The paper's box floats in the corridor, a configuration absent from training. Ours is a standard obstacle standing on a lattice cell beside the target, like thousands of training obstacles.

So the high values are a property of the domain and training data, not an implementation error: inputs change in 534/534 edited states, labels are never seen by the models, and the constant control is at 0.5. A paper-style **out-of-distribution** stress test would need edits the models never saw, such as an off-lattice box, a size outside the training range, or a floating body. That is a different protocol and has not been run.

## Oracle / dataset quality, 3D (PROP_V1, 288 bases)

| | |
|---|---|
| Bases | 288 (47 K0 + 241 repair endpoints). 287 re-verified feasible; 1 BASE came back budget-limited and was excluded. |
| CF proposals | 2,188 attempted. **Certified flip rate 25.9%** (566). 175 budget-limited y = 0, 1,447 still feasible. |
| NULL proposals | 2,156 attempted. **Oracle false-flip rate 9.6%** (123 certified + 85 budget y = 0). The paper reports 0–3% for its box-in-corridor proposals. In our shelf, moving an obstacle "off-corridor" still blocks the arm's sweep in about 1 in 10 cases. This is why every NULL in a triplet is *physically verified* y = 1, not assumed. |
| Funnel | **224 STRONG + 21 BUDGET** triplets; 42 bases had no matched CF/NULL pair |
| Errors | 0. 102 of 4,632 states used the flagged direct-build path (amendment 1). |

**Audits:**
- **Planner seed stability:** a deterministic 25% subset of accepted CF/NULL states (117) was relabelled with planner seed 1; 115/117 labels agree. The 2 disagreements are NULLs that became budget-limited NO_PLAN_FOUND; neither became certified.
- **Direct-build parity:** 40 conflict-free layouts forced through the direct path agree with run_y on y and status in 40/40.
- **Visibility:** in 490/490 edited states the moved obstacle changes the input of every model (Ours `xy0`; GRN graph hash; PIGINet value tokens; SCNet point cloud).

**Baseline reproduction before CF scoring.** On the baselines' own 370 V4 TEST "move T" queries, through the same adapters:

| Model | AUROC s0 / s1 / s2 | Matches |
|---|---|---|
| PIGINet-noimg | .9875 / .9866 / .9879 | prior 0.987 |
| SCNet | .9718 / .9693 / .9651 | prior 0.968 ± 0.003 |
| GRN | .9585 / .9564 / .9590 | prior 0.958 |
| Ours | .9831 / .9823 / .9773 | prior evaluation |

## 2D: Ours-only diagnostic (no 2D baselines exist)

The 2D bases are the historical 2D TEST K0 roots with stored Y0 = 1 (167). PROP_V2 (amendment 3) uses kill-table-ranked CF cells and zero-kill, displacement-matched NULL cells, with 4 objects per base.

| | |
|---|---|
| Funnel | **18 STRONG + 40 BUDGET** triplets; 109 bases had no match |
| Oracle | CF certified flip 3.2% (58/1,788), 148 budget y = 0. **NULL false-flip 1.8%** (28/1,596, all budget-limited). |
| Ours, STRONG (n = 18) | AUROC **0.849** [0.769, 0.944]; NULL retention **83.3%** [66.7, 100]; flip-rank 1.000; CF blocked acc 0.667. Seeds: .864 / .858 / .836. |
| Ours, BUDGET (n = 40) | AUROC 0.843 [0.774, 0.915]; NULL retention 87.5% |

The 2D teacher seldom *certifies* infeasibility. In the engineering pilot, 18 CFs had every live grasp killed by the screens; only 4 of them were certified and 11 ended UNKNOWN_PLANNER. So the 2D STRONG cohort is small and its CIs are wide.

**2D must not be mixed into the 3D table.** The 2D K>3 scaling cohort is not included: its release is not final.

## Proposed paper rows (3D target-feasibility table)

If the table should follow the paper's construction, use the PROP_INS_3D values:

| Method | CF-pair AUROC ↑ | NULL retention (%) ↑ |
|---|---|---|
| SceneCollisionNet | 0.954 | 79.0 |
| PIGINet (no image) | 0.985 | 91.0 |
| GRN | 0.722 | 39.0 |
| Ours | 0.934 | 84.6 |

Footnote: n = 267 fixed-grasp corridor-insertion triplets; oracle flip 1.00, NULL false-flip 0.150 (0.056 for "30 cm back").

Move-one-obstacle family (PROP_V1), for reference:

| Method | CF-pair AUROC ↑ | NULL retention (%) ↑ |
|---|---|---|
| SceneCollisionNet | 0.901 | 81.2 |
| PIGINet (no image) | 0.948 | 92.0 |
| GRN | 0.783 | 54.0 |
| Ours | 0.898 | 85.3 |

Footnote: n = 224 certified-CF triplets; oracle NULL false-flip 9.6% (dataset), certified CF flip 25.9%; PIGINet image variant excluded (no renders for edited states).

**Open question for the owner.** The paper table's existing TN/FN/TP/FP columns were not found in any local file. The rows above therefore add the two new columns only; they do not reconcile with those counts.

## Files

| Path | Contents |
|---|---|
| `results/3d/` | bases, jobs, labels (4,632), sealed `tripman3d.json`, inference manifest, scores (12 model-seeds), `metrics3d.json`, audit jobs and labels |
| `results/2d/` | the same for 2D (no audits) |
| `results/validation/` | 370-query adapter reproduction, plus the 2D v1/v2 and 3D engineering pilots (excluded from the final run) |
| `reports/figures/` | `fig_3d_cf_null_metrics.png`, `fig_3d_score_strips.png`, `fig_3d_example_triplets.png`, `fig_2d_cf_null_metrics.png`, `fig_2d_score_strips.png` |
| Code | `cf_generate.py`, `cf_teacher.py`, `cf_infer.py`, `cf_scnroots.py`, `cf_report.py`, `cf_figures.py`. Hashes are in the lock amendments. |

## Reproduce

```bash
python cf_generate.py 3d bases3d.jsonl jobs3d.jsonl
CF_TABLES=<scaling G1 tables> python cf_generate.py 2d_v2 bases2d.jsonl jobs2d.jsonl
python cf_teacher.py run3d jobs3d.jsonl labels3d.jsonl 26      # env3d
python cf_teacher.py run2d jobs2d.jsonl labels2d.jsonl 24      # env2d
python cf_report.py triplets 3d jobs3d.jsonl labels3d.jsonl tripman3d.json
python cf_scnroots.py infer3d_manifest.jsonl infer3d_scnroots.pkl   # env3d, CF_SCN, SHELF66_V3_DIR
CF_PIG=... CF_SCN=... CF_SCN_ROOTS=... CF_GRN=... python cf_infer.py 3d infer3d_manifest.jsonl scores3d.jsonl
python cf_report.py metrics 3d tripman3d.json labels3d.jsonl scores3d.jsonl metrics3d.json
python cf_figures.py 3d results/3d reports/figures
```
