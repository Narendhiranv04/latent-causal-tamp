# CF-pair and NULL feasibility audit — laptop-only execution plan

**Status:** Implementation handoff; no experiments have been executed by this document.  
**Scope:** Frozen-weight, inference-only comparison of learned **target-feasibility** predictors under planner-verified counterfactual (CF) and nonblocking (NULL) interventions.  
**Primary paper reference:** Sajid Ansari, Antony Thomas, Girish Varma, *Auditing Grasp Feasibility Predictors with Planner-Verified Counterfactuals*, arXiv:2611.09130 (2026), especially Sec. 3, Tab. 1, Tab. 3, and Appendix F/I.  
**Existing project:** `Narendhiranv04/latent-causal-tamp`, `approach_b_final/`, with frozen K≤3 ablations (`4aee798929`) and post-ablation validation (`e9fa587c3b`). The ongoing K>3 dataset construction is **a separate workspace/conversation**.

## 0. Scientific distinction — read before coding

**Do NOT randomly partition K=0 scenes into “CF” and “NULL”.** The reference paper's CF pair holds the **same query** fixed, edits only obstacle geometry, independently verifies a **feasible → infeasible** change, and checks whether the model's probability changes. Its NULL is a *matched nonblocking edit* that retains feasibility; the paper calls the oracle's false-flip rate “Null”. These are **intervention types, not disjoint source-scene splits**.

For our project, transfer the *audit principle*, **not** the paper's grasp-corridor physics or its reported numbers. Our query is the **original target task from `q_ref`**, not an individual grasp pose. A matched triplet is:

- **BASE**: scene `S`, unchanged target object `t0`, goal `G`, robot/reference/task context; independently verified `Y_T(S)=1`.
- **CF**: the **same target/task and robot reference** in `S_CF`, with a single controlled non-target obstacle intervention; independently verified `Y_T(S_CF)=0` under an explicitly documented oracle evidence standard.
- **NULL**: same base and matched intervention family in `S_NULL`, but independently verified `Y_T(S_NULL)=1`.

The ideally isolated difference is the **position or occupancy of one non-target object**. Prefer *moving an existing redundant/eligible obstacle* rather than adding a new object: it preserves object count, representation, and model support. If insertion is used instead, test input-capacity compliance and report it as a distinct intervention family. The edit need not be executed by the learned policy; its edited **scene** must be physically valid and compatible with the target Y teacher. Do not confuse this with an executable corrective X repair.

**CF-pair** evaluates whether the predictor ranks BASE above its matched CF case; **NULL** asks whether it correctly maintains feasibility on a harmless, nonblocking edit. Both must be measured on the **same frozen model** with labels withheld from inference. A scene in the old K>3 dataset with `Y=0` is *not automatically a CF*; it becomes one only when paired with an independently verified feasible BASE at **the same task** and an admissible controlled edit.

### Existing-test versus new-test cohorts

- Existing **2D historical TEST**: eligible 2D roots from the frozen original K≤3 dataset. K=0 verified-positive roots are natural BASE candidates; a verified repaired endpoint may qualify after full task and state reconstruction.
- New **2D K4/5/6/9/12 TEST**: separately generated minimum-K scaling cohort. This cohort may contribute additional legitimate **Y-positive witness endpoints** and Y-negative scenes, but **never pool unpaired positives and negatives to pretend they are counterfactual pairs**. Only include its roots after the data producer marks the release final, replayed, immutable, and never used for learning/tuning. If not yet ready, run the existing-test engineering pilot now and append the new cohort later with a new frozen combined manifest. Do not continuously mutate a scored test set.
- Existing **3D historical TEST**: eligible 3D roots; required for the 3D feasibility comparison table containing PIGINet, GRN, SCNet, and Our Approach. **Do not merge 2D K>3 scenes into the 3D benchmark.** A new 3D cohort can be incorporated only if a separately verified, compatible 3D release actually exists.
- Results must always be **per domain and per source cohort**, with a descriptive pooled estimate only when the same physical query and model-input contract applies. Report selection bias (especially from choosing only K0 / successful endpoints) and historical TEST exposure. A combined source pool is not a pristine held-out set.

## 1. Outcomes, metrics and definitions — lock before prediction

**Target Y, not repair Z.** For Our Approach use the frozen D model's **endpoint feasibility** readout

`p_Y(S,T) = sigmoid(b(S,T))` / `predict(...)["p_noop"]` on the **empty-edit query for that actual scene**, with consistent `t0`, `goal`, `ctx`, `q_ref` and inputs. **Do not** use the maximum over repair candidates, `p11`, selected REPAIR/NOOP/ABSTAIN, or cVAE proposals. This experiment measures *one target-feasibility query per intervention state*.

For each baseline, verify that its returned scalar means the **same target/task Y** and is monotonically increasing in feasibility. If a model produces logits, calibrations, or plan-level feasibility, explicitly document the adapter and its semantics; do not silently call a grasp/collision predictor a complete target-plan feasibility predictor.

**Primary metrics (each frozen model, common accepted triplets):**

1. `CF-pair AUROC` [0,1]: BASE (positive) versus matched CF (negative), with the exact pair-construction and AUROC implementation cross-checked against the cited paper/released audit code when accessible. State whether the implementation uses pooled pair scores or a within-pair statistic; **do not confuse them**. Include both, separately, if the reference implementation differs from a conventional pooled AUROC.
2. `Paired flip-ranking accuracy` [0,1]: mean over triplets of `1[p_BASE > p_CF] + 0.5*1[tie]`. This is explicitly a **within-pair** statistic and complements, but need not equal, pooled AUROC.
3. `CF blocked accuracy (%)`: fraction of teacher-verified CF cases predicted *infeasible* at the method's **prespecified** classification threshold; report also the mean/median score change `p_BASE - p_CF`.
4. `NULL model retention (%)`: fraction of teacher-verified `S_NULL` cases predicted **feasible** at the prespecified threshold. Also report conditional retention on those BASE cases the model predicts feasible and the mean `|p_BASE-p_NULL|`. These are **model** metrics, **not** the paper's oracle “Null”.
5. `Oracle NULL false-flip rate (%)`: fraction of attempted NULL edits independently relabeled **infeasible**, before filtering to accepted triplets. The paper's “Null” is this quantity (ideal 0); alternatively report oracle nonblocking retention = 100% minus this figure. Keep it as a **dataset/oracle quality metric, not one separate value per model**.
6. `BASE feasible accuracy (%)`, `CF/NULL pooled accuracy`, and optional ECE/Brier if the score semantics are validated. These prevent always-positive/always-negative shortcuts from looking good on a single metric.

**Paper table:** If columns remain `CF-pair` and `NULL`, use `CF-pair AUROC` and `NULL model retention (%)` in the caption; move oracle false-flip rate to the dataset-methods paragraph. Never fill all models' NULL columns with one oracle value or silently convert AUROC to percent while other columns are percentages.

**Threshold policy:** Prefer published frozen native thresholds, or a single preregistered threshold (such as 0.5 only when calibrated probability is genuinely the output). Never tune thresholds on the combined TEST/CF dataset. If no defensible threshold exists, label threshold-based metrics exploratory and prioritize ranking/score-change metrics. Do not train or fit Platt scaling/isotonic calibration here.

**Statistics:** At minimum 2,000 paired bootstrap replicates (fixed RNG seed 0) over **base-root/template lineage**, never treating CF and NULL variants or multiple obstacle offsets as independent roots. Provide 95% CIs for CF-pair, flip-ranking, NULL retention and paired model comparisons. Report sample sizes, unpaired/excluded counts, class balance, 2D/3D and source-cohort splits. Compare only methods evaluated on the **identical pair IDs**; otherwise a table of differing denominators is descriptive, not a paired comparison. Include inversion/tie/NaN checks and a random constant-score baseline (expected paired accuracy ~0.5).

## 2. Frozen learned methods and baseline fairness

Target methods for the existing paper's **3D target-feasibility** comparison:

- **Our Approach (Y branch of frozen D/XYNet)**: read `approach_b_final/xy.py`, final bundle/config, exact inference input contract. Freeze hash/seed; primary s0 and optional s1/s2 stability clearly identified.
- **PIGINet**: audit the **actual installed model/checkpoint and adapter**. PIGINet's native published score may describe **whole-plan feasibility**, not the isolated target motion; document the plan-query encoding and ensure the intended task is identical on BASE/CF/NULL.
- **GRN**: audit the actual released/reimplemented checkpoint and graph/box/obstruction inputs. Confirm edited obstacle geometry is represented and that its output can be interpreted as target-task feasibility.
- **SCNet (SceneCollisionNet)**: audit its actual point-cloud/voxel/gripper-query representation and checkpoint. Confirm changed obstacles reach its input. A collision score for a single gripper pose is not automatically target action feasibility.
- Include **other learned target-feasibility methods only if** frozen checkpoints, an appropriate input adapter, and native semantics are available. Never fabricate results or train replacements for unavailable checkpoints.

**First reproduce the existing 3D TEST feasibility rates** (the paper table currently quotes PIGINet, GRN, SCNet, Ours TN/FN/TP/FP). Verify the exact evaluation split, label and denominator for all four, checkpoint hashes, output direction and baseline input contracts. If historical rates cannot be reproduced, report the mismatch **before** CF/NULL results. Do not silently invent or force an adapter merely to fill the table.

For 2D, do **not** assume 3D-trained baseline checkpoints accept the 8x8 planar task features. A separate 2D model audit is required; if no comparable 2D pretrained weights exist, provide a **2D Ours-only diagnostic** and a **3D multi-method comparison**, rather than a scientifically invalid 2D-vs-3D table.

All model runs are **frozen-weight inference only** (`eval`, `no_grad`, controlled sampling or determinism), with no optimizer steps, no fine-tuning, no new model weights, no test-set threshold tuning, no learned blocker detector, no geometry features secretly inserted into *our* model. Geometry is permitted solely to construct/verify interventions and to format **native baseline-visible inputs**.

## 3. Intervention generation protocol

### 3.1 Eligibility and base sampling

- Select from original TEST K0 roots with independently verified `Y_T(S)=1` under the final target-Y teacher and the exact task reference. K0 describes no *needed* correction, not an artificially manufactured baseline.
- Additionally permit an independently verified Y-positive endpoint of a known repair as a new base. Reconstruct the endpoint scene faithfully, including object attributes, target role, goal and reference robot configuration. Do not substitute the task's moved robot pose for `q_ref`.
- Use a deterministic, label-blind hash for sampling **base roots** and selecting proposed obstacle IDs/offset families. **Oracle** may reject and categorize interventions but may not use model predictions to cherry-pick them.
- Reserve a few **engineering-only** triplets for code validation; exclude those from the released audit. Lock a small intervention-family design and source quotas before the final runs.

### 3.2 Causal CF edits

For each BASE, propose one or more minimally changed scene variants in which **one non-target object** is relocated from its original legal cell to a position hypothesized to obstruct the target's pick, transfer, placement, or transit. In 3D, prefer task-native poses/placements. In 2D, use the declared legal grid support and unchanged object shapes.

Rules:

- Same `t0`, goal, requested target action, `q_ref`, object identities (unless separately preregistered insertion family), planner and baseline query identity.
- The edited object must not overlap or teleport into illegal configurations. If the experiment studies pure scene perturbation rather than executable relocation, say so; do not mistake its feasibility for X.
- When possible pair a CF intervention with a **matched NULL move** of the same object and similar displacement or action family. A NULL control should change something observable while remaining nonblocking, not merely be a duplicate of BASE.
- Optionally stratify by first binding mechanism, near/far, single-object/dense clutter, and task stage; record strata privately. All mechanisms must be physically rechecked, not inferred from distance alone.
- Preserve object-count/model-capacity and source-cohort constraints.

### 3.3 Physical re-labeling and acceptance

Run target-Y teacher independently for BASE, CF and NULL with immutable input manifests and separate cache namespaces. Accept a triplet for the **strong CF metric** only if:

- BASE `Y=1` with replayable witness;
- CF has a certified-infeasible status under the declared teacher grammar **or** an explicitly preregistered strong repeated/budget-sensitive negative oracle standard. If only a budget timeout exists, place it in a `BUDGET_NEGATIVE` sensitivity cohort and **do not call it proven physically infeasible**;
- NULL `Y=1` with replayable witness;
- all three queries keep the same task and an edit that is visible to every included model's actual inputs;
- no UNKNOWN/unresolved outcome is coerced into 0; no failed intervention is counted as a valid CF/NULL pair.

The historical teacher has finite planning budgets and may report `UNKNOWN_PLANNER`, not an impossibility proof. Log statuses such as CERTIFIED_INFEASIBLE, NO_PLAN_FOUND, TIMEOUT, INELIGIBLE and unresolved separately. Independently test seed/budget stability on a preregistered subset; report empirical flip yield over **all attempted edits** and reason counts. Use a single registered selection rule for which successful candidate edits are admitted—no model-driven selection and no indefinite search that silently filters hard cases.

### 3.4 Critically avoid these mistakes

- Randomly cutting K0 scenes into positive/null/CF piles; CF and NULL must be **matched interventions**.
- Scoring positive `K=0` versus unrelated `K>3` negative scenes as “CF-pair”.
- Confusing `Y_T` with X, `X∧Y`, `p11`, grasp-only reachability or highest-scored rearrangement.
- Retargeting the query, changing robot start, or changing obstacles not actually encoded by a baseline.
- Using source generator/witness/certificate tags as model features.
- Treating budget-exhaustion zeros as strict impossibility certificates.
- Using the 2D new scaling cohort to populate 3D baseline results.
- Selecting only CFs on which Our Approach succeeds, or repairing mismatched baseline adapters after inspecting final test labels.

## 4. Laptop execution and resource caps

This work runs **only on the user's laptop**. Do not SSH into gvlab, gvlab2, girish or enigma, and do not use their GPU/CPU or edit the ongoing dataset-expansion workspace.

- User-reported CPU: **32 logical cores**, permitted **maximum 29** across the **entire process tree**; keep at least 3 unallocated. Inspect `nproc`, `os.sched_getaffinity`, `lscpu`, cgroups, RAM/swap, process list and disk before launching. Apply `taskset`/affinity to **the parent process and descendants**; reserve CPU for system/UI. Discover actual allowed core IDs rather than assuming 0–28 are available.
- User-reported laptop GPU: use `nvidia-smi` to determine the **actual VRAM and concurrent usage** (past project context suggests an RTX 5060 with 8 GiB, but verify). One GPU model at a time; small adaptive batches, `torch.inference_mode`, mixed precision only after numerical parity, no multi-model GPU concurrency or OOM retries that change evaluation data. Offload unloaded baselines and clear caches between models.
- For CPU physical oracles use roughly 26–28 worker processes **including driver/IO within the total 29-core cap**; limit per-worker BLAS/OpenMP (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`). Do not spawn 29 workers plus controllers/dataloaders.
- Separate CPU teacher-generation jobs from GPU inference; no need to occupy GPU during physics if it cannot accelerate that step. Use bounded concurrency based on measured RAM and physical queries.
- Check whether all checkpoints and source data are **actually accessible locally** and whether physical teacher dependencies can run on the laptop; never assume server-only paths mount locally. If source/weights are absent, report precisely what is missing. No replacement training.
- Isolate into a dedicated local branch/worktree and output root (e.g. `approach_b_final/cf_null_audit/`), keeping code focused (scene builder, oracle runner, inference adapters, scoring/report, tests). Never overwrite the original TEST, frozen weights, previous ablation results or the new scaling dataset.

## 5. Stepwise implementation with gates

### P0 — Verify and lock baseline inputs

Audit `arxiv:2611.09130` (Sec. 3 and NULL definition), the frozen 2D/3D TEST source manifests and all checkpoints. Confirm model input/output adapters. Reproduce the existing 3D native feasibility predictions for PIGINet/GRN/SCNet/Ours **or** mark unsupported models blocked. Capture hashes, software versions, CPU/GPU resources. Verify the right source state for the separate K>3 test release; do not consume a partial dataset.

**Gate:** complete baseline/adapter provenance; no new model training, no dataset modifications.

### P1 — Contracts and unit tests

Implement strict scene/task identity assertions, legal intervention checking, BASE/CF/NULL triplet schemas, cache keys, test that identical inputs yield identical scores, test that changing CF obstacle reaches native model representations (including voxel/crop/token visibility), empty-edit Y parity for Our Approach, and CPU/GPU model-output parity. Add model-inference output sign/orientation checks and AUROC/tie tests.

**Gate:** end-to-end smoke tests on a handful of engineering-only triplets.

### P2 — Fixed-source cohort manifest

Create immutable per-domain test-source manifests with `source_cohort`, `original_split`, `root_id`, lineage/template, geometry version and hash. Deterministically derive eligible BASE scenes. Old TEST and new K>3 2D TEST may enter the same **2D source pool**, but there must be *no* unpaired label concatenation in CF. If the new release is incomplete, make a first engineering run on original TEST and defer sealing a combined release; maintain two separately identified versions of the pool.

**Gate:** source provenance and group-disjoint engineering-vs-final evaluation; no re-use of engineered triplets.

### P3 — Teacher-first intervention pilot

Start with ~20–30 candidate BASE roots per feasible domain to estimate oracle CF flip yield, NULL retention, adapter visibility and teacher cost. Generate multiple candidate edits via a **fixed label-blind proposal family**, NOT via model predictions. Record all attempted edits, successes/rejections, motions, timeouts and budget use. Assess how many can be certified with robust negative evidence; if strict infeasibility cannot be established, pause the strong CF claims and explicitly propose an audit-standard budget-labelled secondary study.

**Gate:** measurable CF and NULL yield; no unreported label ambiguity.

### P4 — Preregister and scale pair collection

Freeze the intervention placement/selection protocol, pair-ID formation, per-root retry budget, oracle evidence standard, null control, source inclusion, model list, metric implementation, and threshold policy. Then attempt a modest number of independent accepted triplets, **target 80–150 per eligible domain if physically attainable**, not a fabricated quota. Use multiple intervention families with balanced representation and a uniform reporting denominator. Re-verify a deterministic subset with alternate teacher seeds/budgets and independent replay.

**Gate:** accepted triplet manifest SHA256; all outcomes and attempted-edits funnel sealed.

### P5 — Inference only for all eligible models

Build each model's native, learner-visible representation separately for all **three** states of every accepted triplet. Run frozen inference on the exact same triplet list. For Ours, use the endpoint-Y no-op query on each state; for PIGINet/GRN/SCNet, use the verified native adapter and checkpoint, with no label- or certificate-dependent preprocessing. Save per-triplet probabilities, logits (if available), checkpoint SHA, device, runtime and input checksums. Seal predictions before evaluating metrics; no model re-runs to choose “better” outputs.

**Gate:** 100% prediction coverage or explicit missing/unsupported status by model, no silent imputation.

### P6 — Paired statistics and paper-table values

Compute the locked metrics. Report BASE, CF, NULL probabilities, oracle flip/false-flip, CF-pair AUROC, within-pair accuracy, CF accuracy, NULL retention, score gaps, numerical CIs and diagnostic plots. Compare identical pairs for each baseline. Report 2D and 3D independently; any pooled source results must include per-cohort values. Produce a concise row-ready output for the **3D table**: `PIGINet | CF-pair | NULL`, `GRN | ...`, `SCNet | ...`, `Our Approach | ...`; do **not** fill with invented values. Also produce a separate 2D audit if comparable models exist.

**Gate:** reproduce metrics from sealed prediction files only; validate denominators, random baseline and tie handling.

### P7 — Scientific audit and release

Produce all manifests, labels, frozen predictions, verified intervention descriptions, plots and 2–4 representative before/after visualizations or short GIFs. Clearly separate the source-domain experiment from the referenced paper's *grasp-level* corridor insertion. List any baselines that cannot be compared for task/representation reasons. Finalize a paper-ready methods paragraph and caption defining CF-pair and NULL. Include candid results even if every predictor scores near chance; no retraining or post-hoc test editing to improve an outcome.

**Gate:** independently reproducible `REPORT.md`, immutable source/prediction hashes and no unsanctioned compute or model training.

## 6. Minimal recommended artifacts

```
approach_b_final/cf_null_audit/
  plan.md                       # this experiment protocol / registered updates
  README.md                     # paths, dependencies, exact commands
  cf_generate.py                # public scene variations; immutable manifest
  cf_teacher.py                 # versioned teacher calls/cache/replay
  cf_infer.py                   # model adapters, frozen scoring
  cf_report.py                  # metrics/figures; no model access
  test_cf_null.py               # invariants, labels, pairs and parity
  reports/
    PROTOCOL_LOCK.json
    AUDIT_REPORT.md
    RESULTS.json
    CF_NULL_REPORT.md
    figures/
    manifests/
```

Only create files that add necessary distinct functionality; reuse existing teacher, model and rendering utilities. Separate outputs and logs under versioned `runs/` directories. Avoid duplicating large checkpoints; load existing read-only weights.

## 7. Required final scientific answers

1. Did the intervention *actually flip* target Y for CF, and preserve target Y for NULL? How many attempts failed each gate and why?
2. Did all models receive the edited obstacle in their **native inputs**? Did each model predict **the same target-task semantic**?
3. Does each frozen learned predictor reduce `P(Y=1)` on the blocked version of an otherwise identical task, compared with its clear version?
4. Does it preserve feasibility on the matched nonblocking edit, rather than naively treating every new obstacle as a blocker?
5. Are the reported CF-pair and NULL values directly comparable across models, from identical pairs, domain, query, and confidence convention?
6. Are the results truly **inference-only**, with no tuning on exposed TEST and no privileged causal features supplied to Our Approach?
7. Which final table entries are supported by physical labels, which are exploratory and which remain unavailable?

**Non-negotiable:** A missing baseline implementation, an unresolved physical label, a model-input mismatch, or an unfinished new TEST release must be reported as such. None is permission to invent results or silently substitute a different experiment.
