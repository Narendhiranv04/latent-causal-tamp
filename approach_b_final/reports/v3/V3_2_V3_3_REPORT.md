# V3-2 (M and sampling rules) and V3-3 (task-conditioned cVAE)

**Hypotheses.**
- **V3-2 (plan §4.3, §5.3):** with frozen models, a larger M or a different readout rule of the goal-blind Q2 cVAE raises proposal coverage and top-1 success.
- **V3-3 (plan §3, §5.4):** a cVAE trained on the destinations of physically verified successful complete repairs proposes the ingredients of successful repairs far more often than the Q2 cVAE, and this raises top-1 success at a matched budget.

**Setup.**
- Seed 0 for the physical arms; 3 seeds for the teacher-free sweeps.
- Frozen V2 coupled D scorer and frozen V2 rule.
- Direct one-shot construction with B = 4,096.
- Full validation split: 751 2D and 364 3D roots; task n = 413 / 220.
- Every selected repair was verified by the unchanged teachers, with 0 unverified.
- **Teacher hosts:** gvlab2, plus the laptop, which the user authorised for CPU teacher work on 2026-11-16. Laptop parity vs recorded labels: 2D 56 / 56 and 3D 16 / 16 identical.
- No test data was used.

## 1. Implementation (all in existing modules)

**Sampling rules** (`placement.propose_rule`, `marginal`, `band_dist`):
- S0: the old repeat-and-dedup rule, unchanged and bit-identical.
- S1: true top-M of the Monte-Carlo marginal, E_z softmax(masked decoder) with 64 prior draws.
- S2: Gumbel-top-M without replacement from that marginal.
- S3: temperature τ ∈ {1.5, 2, 3}.
- S4: (1 − ε) p + ε q_broad, with q_broad uniform or the exact band distribution, and ε ∈ {0.25, 0.5}.
- Controls: legal-uniform and band-stratified.

**Task-conditioned cVAE** (`placement.TaskCVAE`, `task_features`, `repair_data`, `fit_task`), in the same cVAE family:
- The Q2 SceneEncoder plus an additive task branch, with a zero-initialised last layer, so a Q2-initialised model equals the Q2 cVAE before training.
- **Task input:** goal and target one-hot grids, query-relative goal and target offsets, the root's context vector, and a `task_on` flag.
- **Never input:** labels, K, blocker identities or outcomes.
- **Loss:** the exact negative conditional ELBO (reconstruction + β KL with warm-up), weighted per example by 1/|A_i| · 1/|A|. Six successful orders of one assignment count as one target set, and roots without a positive give no examples (never negatives).
- **Data:** TRAIN from the V2 snapshot (V3-legal Z = 1 assignments); model selection uses the validation-repair ELBO of the base snapshot.

**Variants** (3 seeds × 2 domains each; identical architecture, optimiser and epoch budget):
- `scratch_one`, `scratch_all`;
- `q2init_one`, `q2init_all` (Q2-pretrained, then repair fine-tuned);
- `combined_one` (repair plus a goal-masked Q2 branch with task_on = 0);
- `goalablated_one` (repair supervision, no task input).

Each training run takes 4–8 s on the RTX 5090.

**Other code:**
- `construct.py sweep`: teacher-free proposal metrics.
- `construct.make_sampler`: `task:<variant>` samplers.
- 3D padding raised from 12 to 16 objects, because some 3D TRAIN NONE scenes have 13 objects. Padding only: proposals on 40 validation roots are identical (`scripts/pad_parity.py`).

**Tests:** 22 / 22 pass. The V3-3 tests cover:
- rules emit only legal, unique cells;
- S1 is the true top-M of the same-draw marginal;
- marginals sum to 1;
- the band distribution has equal band mass;
- Q2-init equals Q2;
- the goal changes the distribution;
- labels and K do not change the task features;
- assignment weights are correct and Y = 0 or no-positive roots contribute nothing.

## 2. Teacher-free proposal coverage (validation, 3 seeds; `v3_23/SWEEP_*.json`, `recall_vs_M.png`)

The metric is known-assignment ingredient recall: the share of task roots where one sampler pass on S0 contains every action of a verified Z = 1 assignment.

| M = 4 | 2D | 3D | M = 16: 2D | M = 16: 3D |
|---|---:|---:|---:|---:|
| Q2 cVAE, S0 (old) | 1.8 ± 1.0 % | 4.1 ± 0.6 % | 14.1 % | 21.8 % |
| Q2 cVAE, best rule (S1 / S4) | 4.1 % | 4.3 % | 21.8 % | 26.0 % |
| Uniform / band-stratified | 1.6 / 3.6 % | 4.3 / 2.3 % | 13.2 / 17.4 % | 28.5 / 21.0 % |
| **Task cVAE q2init_all, S1** | **29.4 ± 0.3 %** | **58.8 ± 2.4 %** | **85.6 %** | **90.4 %** |
| Task cVAE scratch_all, S1 | 27.1 % | 60.3 % | 86.4 % | 88.7 % |
| Goal-ablated repair cVAE, S1 | 23.2 % | 54.3 % | 83.5 % | 87.5 % |

Findings:
- **V3-2:** with the Q2 cVAE, the readout rule barely matters; at M = 4 no rule beats uniform by more than about 2 points. M is the main lever, and even M = 16 recovers K3 assignments in only 3–12 % of roots.
- **V3-3:** repair supervision raises recall about 15× at M = 4.
  - S1 beats S2 for every task model.
  - "All assignments" beats "one per root" (2D 29.4 vs 27.7 %; 3D 58.8 vs 52.4 % for q2init).
  - Q2 pretraining helps only slightly in 2D.
  - **Most of the gain comes from repair supervision, not from goal conditioning:** the goal-ablated control gets 79–92 % of it.
- **Chosen V3-4 generator:** `task:q2init_all`, S1, M = 4. Per plan §5.4 it was selected on validation proposal metrics (best mean recall over both domains).

## 3. Physical top-1 (validation, frozen V2 scorer; `v3_23/SUMMARY_*_val.json`, `physical_top1.png`)

| Setup | 2D task | Δ vs Q2 S0 M4 [95 % CI] | 2D NONE abstain | 3D task | Δ vs Q2 S0 M4 [95 % CI] | 3D NONE abstain |
|---|---:|---|---:|---:|---|---:|
| Q2 S0 M4 | 20.6 | — | 93.3 | 54.5 | — | 82.8 |
| Q2 S0 M8 | 19.6 | −1.0 [−4.4, +2.7] | 94.7 | 60.5 | +5.9 [−0.9, +13.2] | 87.9 |
| Q2 S0 M16 | 19.6 | −1.0 [−5.1, +3.1] | 94.7 | 65.9 | +11.4 [+4.1, +18.2] | 69.0 |
| Q2 S1 M4 | 17.7 | −2.9 [−7.3, +1.2] | 94.7 | 44.5 | −10.0 [−17.3, −2.7] | 98.3 |
| Uniform M4 | **27.8** | **+7.3 [+3.1, +11.4]** | 93.3 | 47.3 | −7.3 [−14.1, 0.0] | 53.4 |
| Goal-ablated M4 | 18.2 | −2.4 [−6.3, +1.7] | 71.3 | 65.9 | +11.4 [+4.5, +18.6] | 32.8 |
| **Task cVAE M4** | 22.0 | +1.5 [−2.9, +6.1] | 76.0 | **67.7** | **+13.2 [+6.4, +20.0]** | 37.9 |
| Task cVAE M8 | 20.8 | +0.2 [−3.9, +4.4] | 76.7 | 68.6 | +14.1 [+6.8, +21.4] | 36.2 |

K-level results and scorer behaviour:
- 3D task cVAE M4 by K1 / K2 / K3: 62.3 / 74.2 / 62.9, vs 58.5 / 56.7 / 48.6 for Q2.
- 2D K3: 4.6 % vs 1.2 %.
- No-op accuracy is identical across all setups (95.2 % in 2D, 81.2 % in 3D), since the no-op gate does not depend on proposals.
- Conditional selection success (a known or verified success is in the scored set and gets selected): 2D task cVAE 61.5 % vs uniform 92.7 %; 3D 79.7 % vs 95.4 %.

## 4. Interpretation

1. **3D: the proposal distribution matters, and the hypothesis is supported.**
   - With an unchanged scorer, the task cVAE raises verified top-1 success by +13.2 points (CI excludes 0) at M = 4.
   - It matches the Q2 cVAE at M = 16 with ¼ of the unique actions and a third of the latency (0.12 vs 0.34 s).
2. **2D: the coverage gain does not reach top-1 with the frozen V2 scorer.**
   - Ingredient recall rises from 1.8 % to 29 %, but task success moves only from 20.6 % to 22.0 % (n.s.).
   - Given a success in the pool, the scorer selects it far less often (62 % vs 93 % for uniform proposals).
   - This is the **covariate-shift** case of plan §5.1. The V2 D was trained on labels from the old Q2 / iterative candidate distribution and is miscalibrated on repair-like candidates.
3. **Both domains: NONE abstention collapses** with repair-like proposals (2D 93 → 76 %; 3D 83 → 38 %).
   - The frozen scorer admits confident false positives on legacy-NONE roots.
   - This is a protocol-relative abstention metric. Some NONE roots may be repairable outside the old search scope; that is unverified, since these selections were checked only as repairs, and a 3D NONE selection with X = Y = 1 would be a new verified repair.
   - It is still the main scorer problem to fix.
4. **Uniform proposals win in 2D under the frozen scorer** (+7.3, CI excludes 0) without changing abstention. This is preserved as a negative result for the learned samplers in that configuration: broad, unstructured proposals pair better with a scorer trained on broad candidates.
5. **Next step, as the plan prescribes:**
   - V3-4: label the task-cVAE candidates on TRAIN roots, now running and including NONE and K0 roots.
   - V3-5: retrain D, E, G and DIRECT on base + V2 + V3 evidence, and re-tune the rule on validation.
   - V3-6: the 2×2 cross of old / new sampler × old / new scorer (experiment E), with uniform kept as a control.

## 5. Caveats

- Physical arms use a single seed with the frozen V2 rule, which was not re-tuned for the new candidate distributions.
- Validation is now used for V3 methodology selection; the V1 / V2 test split stays untouched. Strong final claims will need a fresh cohort or a clearly stated test-exposure caveat (plan §6.3).
- Ingredient recall checks only the teacher's known assignment. It is a lower bound on coverage, and it can reward imitation of the teacher's style.
- 2D teacher negatives include `UNKNOWN_PLANNER` zeros. These are protocol-relative, exactly as in all labels.
