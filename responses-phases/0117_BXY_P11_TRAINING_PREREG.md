# 0117 — BXY-P11-TRAINING-PREREG: leakage-separated training interface, exact objective, preregistered comparison

Date: 2026-10-31. Gate: BXY-P11-TRAINING-PREREG only. Authority: `Approach_B_Final_Methodology_2026-10-31.pdf` (§2–§9). Previous gate:
0116, commit `9673f8fbbeaab76f65f54d8e72531fdc59de8a18` (pushed, `READY_FOR_TRAINING_DESIGN`).

**Verdict: `READY_TO_REQUEST_TRAINING_BUDGET`.** `PREFLIGHT.json → passed: true`.
- The verified P-min evidence is intact.
- The new training path is leakage-separated and proven invariant to every hidden outcome.
- The exact joint objective matches `bxy_core` and brute-force enumeration, including gradients.
- Every training, selection and evaluation decision is frozen in `TRAINING_DESIGN.json` / `TRAINING_LOCK.json` before any model is trained.

**Nothing was trained.**
- 0 optimizer steps, 0 teacher queries, 0 test-split roots touched, no generation, no `PREFIX_COMPLETE`, no P-full, no 3D.
- The only real-data computation on models was:
  - forward/backward cost timing (no optimizer step, nothing saved);
  - leakage-invariance checks of randomly initialized models.

**Contract.** The pasted instruction is self-contained and was followed as the contract; no other prompt file was needed.

---

## 1. Authoritative state (verified, nothing modified)

| Evidence | sha256 | Status |
|---|---|---|
| `BXY_SIDECAR_V2_PMIN.json` | `0191f49b…76cd7e` | match |
| `PMIN_DESIGN.json` | `8f164845…ff658` | match |
| `PMIN_LOCK.json` | `4d42027e…dfffaa` | match |

**Counts, recomputed by `bxy_p11.evidence()`:**
- 2,222 X; 1,866 unique Y; 2,222 matched pairs.
- 1,452 complete-success travel witnesses and 142 successful no-op target witnesses.
- 176 train and 21 validation roots.
- No historical test root appears in the design or the sidecar. The 34 exposed test roots are excluded.
- Strata: 142 K0, 37 K1, 9 K≥2, 9 unknown-K.
  - train: 131 / 32 / 5 / 8;
  - val: 11 / 5 / 4 / 1.
- 55 roots need repair (Y0 = 0): 45 train and 10 val.

**What I read:**
- `bxy_core.py` (V1 exact model);
- `bxy_v2.py` (P10 V2 reader and `ModelXY2`);
- `bxy_run.py` (historical V1 trainer and selection);
- `bxy_data.py`, `bxy_pmin.py`, `bxy_pmin_sidecar.py`;
- `abc_models.Root` / `abc7_models.ModelBC7` (shared LB modules);
- `bd_2d.py` (how the historical catalogue was made);
- reports 0114–0116;
- the methodology PDF.

## 2. Audit of the training interface — what was wrong, and the fix

### 2.1 Findings (blocking for any training run)

1. **`bxy_run.train()` cannot be used.** It calls `bxy_core.views` (V1 sidecar, legacy LB-derived labels) and `bxy_core.ModelXY` (no target-travel head, no-op J = 0). It is left untouched as the archived V1 path.
2. **The V2 reader leaks outcome-informed metadata.** `bxy_v2.catalogue()` and `bxy_v2.views()` copy into every per-root view the historical `role`, `y_full`, `travel` and `failed_step`. `bxy_v2.predict()` returns `role`. `bxy_v2.choose()` breaks ties by catalogue position.
3. **The catalogue order itself is an outcome signal.** In `bd_2d.py`, `minimal` is the first sequence the BD teacher found to succeed, and it is always placed at index 1. `wrong_order`, `partial`, `redundant+k` and `intended_union` are all derived from it. So catalogue position and role reveal outcomes.
4. **The view's variable set depended on which queries were observed** (`full=False`). It was harmless on P-min, because every variable is observed, but it was not outcome-free by construction.
5. **Travel acceptance did not check replay.** The P10 reader accepted a pair's `J_total` without checking that its X and Y were independently replayed.

### 2.2 Fix: three strictly separated objects (`bxy_p11.build`)

| Object | Contents | Consumer |
|---|---|---|
| **ScorerView** | exactly `R, cands, key, parent, x_seqs, y0, y_poses` — see below | `Model.coeffs` (asserts the whitelist; `check_scorer` also rejects any forbidden field name) |
| **Labels** | observed X / Y (absent = marginalized), DIRECT success events, complete-witness travel `(xi \| None, yi, J)` | the loss only |
| **EvalView** | candidate outcomes, teacher status / negative kind / failed phase / certificate detail, legacy roles, order groups, omission structure, Y0, K stratum | the evaluator only |

ScorerView fields:
- `R` = `abc_models.Root` built from the record's `inputs` only (object xy, radius, target/obstacle flag, robot q, goal, FK joints, DINOv2 visual features);
- `x_seqs` = ordered (object index, destination) actions;
- `y_poses` = hypothetical edit poses;
- `parent` = shared Y index of each X;
- `y0` = index of the empty-edit Y;
- `cands` = canonical candidates `{sig, m, cd, xi, yi, admissible}`.

Construction rules:
- **Variables come from the outcome-free frozen P-min design**: every F1-admissible `PMIN_DEV_MATCHED` query, every X's parent Y, and Y0.
- **Candidates are sorted by `(m, action signature)`.** Admissibility is analytic `bxy_f1.screen(...).complete_ok`; the zero-move candidate is always admissible.
- **A complete-witness travel label is accepted only if all of these hold:**
  - `full_joint_success == 1` and `matched_protocol`;
  - X and Y both `independent_replay`, with replay witnesses;
  - `J_total == J_prefix_stitched (relocations + connector) + J_target` to 1e-9.

  A no-op label needs a replayed Y0 target witness. Anything else raises.

### 2.3 Leakage proof — `PREFLIGHT.json → leakage`

`bxy_p11_prereg.perturb()` builds a self-consistent alternative outcome world:
- every X and Y label is flipped;
- new positives get replay flags and random travel, and pairs are recomputed;
- every failure kind, phase and detail is rewritten;
- every legacy role, B label, travel and `failed_step` is rewritten, and the legacy catalogue order is shuffled.

Geometry and actions are untouched. Results:

| Check | Result |
|---|---|
| ScorerViews identical (tensors and fields), all 197 roots | **197 / 197** |
| Labels changed / evaluator views changed | 197 / 197 |
| All 5 arms, 12 roots: max coefficient difference, max probability difference | **0.0, 0.0** |
| Selection changed by perturbation / by candidate-list permutation | **0 / 0** |

Tests also show:
- injecting `role`, `y_obs` or `travel` into a scorer view raises;
- reversing the legacy B order leaves the canonical candidates identical.

### 2.4 Data checks (`PREFLIGHT.json → audit`)

- **Root/family separation:**
  - 0 families straddle train/val;
  - 0 test roots in the design or sidecar;
  - LB records agree with `split_of` for every root;
  - `build(("test",))` raises, and a record relabelled as test raises.
- **Shared Y:**
  - 551 Y nodes have ≥2 X children; 528 reversal X share a Y node with their forward order;
  - `build` raises if an X's parent edit differs from its endpoint (none do).
- **Deduplication:**
  - 2,222 X and 1,866 Y rows, all unique keys;
  - the 57 X + 59 Y reused P9 rows each count once;
  - a duplicate identical row collapses; a conflicting duplicate raises `ConflictError`.
- **Missingness:** 0 unobserved rows and 0 unobserved variables on P-min.
  - Exact marginalization is proven on microcases: an unobserved Y with observed children is summed, never set to 0.
  - It is inactive on this data.
- **No-op:**
  - no X variable has an empty prefix (X_∅ = 1 by definition);
  - Y0 is observed in 197/197 roots and learned through b_0;
  - 142 no-op travel labels come from replayed Y0 target witnesses, so no-op J > 0.
- **Travel:**
  - 1,452 complete and 142 no-op labels; 0 on any failed candidate;
  - every complete prefix contains its connector;
  - changing a failed pair's `J_total` does not change any label.
- **Diagnostic negatives retained (EvalView only):**

  | | certified | planner | transit |
  |---|---|---|---|
  | X | 162 | 286 | 42 |
  | Y | 64 | 281 | — |

  Order groups: 551, of which 113 are discordant; the failing orders are 24 certified and 89 budget/policy.
- **Encoding:** X lengths 1–6 (556 / 756 / 600 / 242 / 60 / 8). Every one of the 8 six-step sequences survives encoding.
- **Catalogue:**
  - 1,143 candidates, 17 F1-screened, 0 admissible candidates undecided;
  - 48 of the 55 repair-needing roots contain at least one successful admissible candidate (oracle availability).

## 3. Frozen learning objective (methodology §4.2, §5.3, §6.2)

**Probability model:**
- P(Y_s=1) = σ(b_s/τ); P(X_q=1 | Y=y) = σ((a_q + w_q·y)/τ); τ = 1 (frozen).
- p_succ(q) = σ(b_s)·σ(a_q + w_q); p_succ(∅) = P(Y0=1).

**Learned coefficients:**
- F2 a_q: the LB predecessor-aware prefix unary.
- F3 b_s: the scene unary.
- F5 w_q = xy(g_q, v_s, c).
- F1 is analytic. F4 omissions are queries of the same scorers.
- There is no static BCE, no extra pair term and no higher-order term.

**L_joint** = the mean over the batch's roots of −log P(D_c):
- `bxy_p11.log_evidence` is the vectorized form, with one logsumexp per unique scene.
- It equals `bxy_core.log_evidence` and `bxy_core.brute_force` to 1e-10 on 12 random microcases.
- Gradients pass `torch.autograd.gradcheck` and match `bxy_core` to 1e-12.
- The four-state microcase normalizes to 1, and its (1,1) cell equals σ(b)σ(a+w).
- Appending an X proposal leaves P(Y) and the other p_succ bit-identical.

**L_travel** = Σ_w Huber_δ=1(log1p Ĵ, log1p J) / N_J, pooled over the batch's complete witnesses (the methodology's §6.2 form):
- Ĵ(q) = jt(v_s, c) + softplus(cost(g_q)): relocations, connector and target.
- Ĵ(∅) = jt(v_0, c): nonzero target travel for the no-op.
- At λ_J = 0 the travel term is absent.

**L_total** = L_joint + λ_J·L_travel.

DIRECT (§4) uses the root-summed BCE of success events, root-averaged.

## 4. Preregistered comparison

All learned arms share the same scene inputs, ordered actions, edited endpoint scenes, training roots, labels, candidate catalogue, seeds, optimizer and update budget. Parameter counts are from `PREFLIGHT.json → params`; "active" means receiving gradient.

| Arm | Model | λ_J | γ (selection) | Total / active params |
|---|---|---|---|---|
| **XY-quadratic** (primary) | a_q, b_s, w_q = xy(g, v_s, c) | own λ* ∈ {0.1, 0.3, 1.0} | 0.05 | 549,799 / 483,109 |
| **XY-quadratic-noJ** | same | 0 | 0 | 549,799 / 433,443 |
| **XY-uncoupled** | a_q, b_s, w = 0 | own λ* | 0.05 | 500,390 / 433,700 |
| **XY-uncoupled-SA** (capacity / feature control) | w = 0, a_q += xs(g, v_s, c): **same inputs and parameter count as the coupling head** | own λ* | 0.05 | 549,799 / 483,109 |
| **DIRECT** (protocol-aligned direct success) | logit a_q + xs(g, v_s, c) on x∧y of every decided X; no-op logit b_0 on Y0 | 0 | 0 | 549,799 / 433,443 |
| LB (historical reference) | frozen `BXY-LB-s{0,1,2}` (sha in the design) | — | 0 | 467,365 |

**How the capacity control works.** XY-quadratic and XY-uncoupled-SA have identical modules, inputs and parameter counts. The only difference is whether the extra head's output enters as a coupling w·x·y or additively into a. A gain of quadratic over SA is therefore attributable to the X–Y interaction, not to extra scene features or capacity. XY-uncoupled is reported as the methodology's plain control.

**LB is not a matched arm.** It is trained on BD_GEN_V1 whole-sequence outcomes from the achieved robot state, a different execution-outcome protocol. It is compared on val21 (from its frozen predictions) and on the fresh cohort only.

**References:**
- NOOP;
- SHORTEST_ADMISSIBLE (fewest moves; ties by displacement, then signature);
- DISPLACEMENT_RANK (smallest displacement; ties by moves, then signature);
- VERIFY_FIRST (oracle; reports success and number of verifications);
- ORACLE_AVAILABILITY.

## 5. Frozen training and validation procedure

**Optimizer and batching:**
- AdamW, learning rate 1e-3, weight decay 1e-4, gradient clip-norm 10.
- 12 roots per update, sampled uniformly without replacement (root-balanced); the loss is the root mean.
- At most 3,000 updates. Early-stopping evaluation every 20 updates, patience 15 evaluations, relative tolerance 1e-3, restore the best checkpoint.
- The early-stopping metric is the arm's own likelihood (joint NLL; BCE for DIRECT), never a selection metric.
- float64, 1 torch thread per worker. Seeds {0, 1, 2}.
- The trainer `bxy_p11.fit` is implemented and was validated only on synthetic roots: deterministic, the best checkpoint is restored, parameters move.

**Changes from the historical trainer, made before any training:**
- verified V2 sidecar through the separated views;
- pooled travel Huber (was a per-root mean);
- complete Ĵ, including no-op target travel (was 0);
- 1 thread per worker;
- early stopping on NLL only.

**λ_J selection.** Each J-trained arm picks its own λ* = argmin over {0.1, 0.3, 1.0} of its mean (over 3 seeds) best val21 joint NLL. A relative difference ≤ 1e-3 counts as a tie and goes to the smaller λ. The procedure is the same for every arm.

**Roster: 108 runs, frozen in `TRAINING_DESIGN.json → roster`.**
- **SPLIT** (176 train, early stop on val21): 27 λ runs (3 arms × 3 λ × 3 seeds), plus noJ × 3 and DIRECT × 3. The λ* runs and these 6 are the confirmatory checkpoints.
- **CROSSFIT**: 5 folds × 5 arms × 3 seeds = 75 runs, using each arm's λ*.
  - The 197 roots are split into family-grouped folds, stratified by the family's most severe stratum.
  - Held-out size per fold: 37–41 roots, with 10–12 non-K0 roots per fold.
  - Each fold has an early-stopping subset of about 1/8 of the training families, inside the training pool (20–21 roots).
  - Every root is scored only by models that never saw it.
  - This answers the problem that val21 has only 10 repair-needing roots: development comparisons use all 197 roots (55 repair-needing).

**Selection rule (fixed a priori; not tuned, since 10 repair-needing val roots cannot support tuning 4 decision hyperparameters):**
1. F1 screen; keep the zero-move candidate.
2. No-op gate: if P(Y0=1) ≥ 0.5, choose the no-op.
3. Admit candidates with p ≥ η, where η = 0 (never abstain).
4. Choose argmin C(r) = −log p_succ + 0.1·m + 0·C_d + γ·Ĵ, with γ = 0.05 for J-trained arms and 0 for the others. C_d is measured in lattice cells.
5. Break ties by (m, C_d, signature). A test proves invariance to candidate permutation.

Report-only alternatives (never used to choose anything):
- an abstaining variant with η = 0.5;
- a sensitivity grid: α {0, 0.1, 0.3} × β {0, 0.1} × γ {0, 0.05, 0.2} × η {0, 0.5};
- a lexicographic length-first ablation.

α, β, γ and η are decision hyperparameters; λ_J is the training auxiliary weight.

**Requested training budget (needs explicit authorization):**

| Limit | Value |
|---|---|
| Aggregate CPU | **110,000 CPU-s** (1.25 × expected 79,324, plus 10,000 for evaluation; worst case if no run stopped early: 191,973) |
| Per-run CPU cap | **3,500 CPU-s** (1.6 × the slowest arm's 3,000-update worst case) |
| Workers | **8 concurrent** (1 thread each), gated on memory |
| Wall | **31,200 s** (assumes 4 effective workers) |

- Measured cost (single process, no optimizer step): ≈0.4–0.6 CPU-s per 12-root update; ≈0.3 CPU-s per val21 evaluation; max RSS 662 MB (measured twice; the frozen budget uses the second run).
- Memory gate: launch a worker only if available memory ≥ 2.0 GB + 0.8 GB per running worker (ramp 2 → 4 → 8). The host showed only ~4 GB available, from processes outside this project.
- Projection checkpoint after 12 finished runs: stop launching new runs (never kill a running one) if the projection exceeds the cap.
- The next gate must commit its own runner and a separate authorization manifest before launch, guarded by `bxy_p11_prereg.assert_frozen()`. The lock's `authorized` stays `false`.

## 6. Frozen evaluation (`TRAINING_DESIGN.json → evaluation`)

**Three evaluation tiers:**
- **Development, primary:** CROSSFIT out-of-fold predictions on all 197 roots. Per-root metrics are averaged over 3 seeds, then compared between arms with a paired root-cluster bootstrap (B = 10,000).
- **Development, split:** SPLIT models on val21. Descriptive only; this is the only place LB is comparable.
- **Confirmatory:** SPLIT checkpoints, evaluated once on the fresh cohort (§7).

**Metrics:**
- **Probability quality:**
  - P(X) vs observed X, P(Y) vs observed Y, and p_succ vs x∧y of every decided X query plus P(Y0) vs Y0;
  - per-root joint NLL;
  - root-averaged and pooled log loss and Brier score, ECE10, reliability diagrams.
- **Selection:**
  - **success on repair-needing roots (Y0 = 0): the primary decision metric**;
  - overall success, false repair on Y0 = 1 roots, abstention, oracle availability;
  - optimality (fewest moves among successful candidates);
  - chosen m and C_d, witnessed J_total of successful choices, travel regret.
- **Ordering:** concordance on discordant same-endpoint pairs, separately for the 24 certified and the 89 budget/policy failing orders. They are never pooled into one claim.
- **Omissions:** sign agreement of predicted changes in P(X), P(Y) and p_succ with decided transitions, plus a descriptive two-move interaction table. Planner-budget zeros are never used to claim a necessary cause.
- **Strata:** K0, K1, K≥2 and unknown-K reported separately with their root counts. No claim is made for a stratum with fewer than 10 roots.

**Coupling decision** (quadratic minus control, against both XY-uncoupled and XY-uncoupled-SA):

| Verdict | Condition |
|---|---|
| **BENEFICIAL** | success log-loss CI upper < 0 against both controls, **and** selection non-inferior (CI lower > −0.05) against both, **and** ≥2 of 3 seeds improve against both |
| **UNSUPPORTED** | log-loss point estimate ≥ 0 against either control, **or** selection point estimate < 0 with CI lower ≤ −0.05 |
| **INCONCLUSIVE** | otherwise |

- A nonzero w is not evidence.
- A CROSSFIT verdict is development evidence only.
- If the coupling is not BENEFICIAL on the fresh cohort, it is removed from the deployed model (methodology §8.2).

**Other preregistered decisions:**
- **Travel auxiliary:** λ* is kept over 0 only if (a) success log loss is non-inferior to noJ (CI upper < 0.02) **and** (b) the paired witnessed J of successful choices is lower (CI upper < 0).
- **DIRECT and LB:** the factorized model is preferred only if it is non-inferior to DIRECT on both success log loss and selection. Otherwise DIRECT / LB is reported as the simpler alternative.

**Visualizations required in the training gate:**
- reliability diagrams;
- paired per-root difference plots with CIs;
- loss curves;
- order-contrast scene panels (certified vs budget);
- no-op decisions;
- a gallery of selection errors (false and missed repairs);
- failure categories of chosen candidates;
- successful selected corrections with replayed witnesses;
- the distribution of w by four-cell outcome (descriptive only).

**Implemented and tested now:** `prob_metrics`, `per_root`, `cluster_boot`, `selection_row/summary`, `order_metric`, `omission_metric`, `verify_first`, `verdict`.
- On untrained models, the plumbing reproduces 0116's 24/89 order pairs and the 47/151 (X) and 131/34 (Y) omission transitions.
- Those plumbing values are not results.

## 7. Fresh independent evaluation cohort (plan only; not generated)

- **Generator:** a new BD_GEN version, with a seed and family space disjoint from BD_GEN_V1; disjointness is hash-checked.
- **Target mix:**
  - K0 ≤ 30%; K1 ≥ 20%; K2 ≥ 20%; K3 ≥ 15%; K4 ≥ 10%;
  - ≥ 25% order-sensitive roots, verified;
  - ≥ 10% connector-stress roots;
  - 4–8 movable objects.
- **Size:** planning target ≥ 300 roots, with ≥ 200 needing repair. The exact size will come from a paired-root power calculation using the CROSSFIT discordance rate.
- **Outcome-blind catalogue:**
  - Candidates are enumerated from geometry only: sufficient subsets of the analytic swept-volume obstruction set up to 4 moves, both orders for 2-move sets, alternative destinations, and redundant / wrong-destination controls, via a seeded rule.
  - No candidate's own outcome decides whether it enters the catalogue.
  - The catalogue is frozen and hashed before any teacher query.
- **Labels:** the same teacher hash, budgets, q_ref and F1; X, Y and Y0 for every admissible candidate, plus reversals and omissions; every positive independently replayed.
- **Custody:** generated by a runner that cannot import model code; frozen before any model sees it; evaluated once.
- The 34 old test roots remain historical diagnostics only.

## 8. Remaining limitations

1. **The validation cohort is small** (21 roots, 10 repair-needing). SPLIT validation is descriptive. λ* is chosen on val21, and those roots later appear as CROSSFIT held-out roots; this is a disclosed, low-dimensional choice.
2. **K0 dominates** (142/197). K≥2 has 9 roots, unknown-K 9, and K3/K4 are essentially absent, so no difficulty-stratum claim is possible on this data.
3. **Negative labels are budget-limited.** 328 of 490 X zeros and 281 of 345 Y zeros are planner/transit budget failures, so they are policy-relative. Certified subsets are small (X 162, Y 64; 24 certified order failures).
4. **The historical catalogue is outcome-guided.** Scorers never see roles or order, but the catalogue's composition (and so the P-min design built from it) still inflates oracle availability (48/55) for every method alike. Only the fresh, outcome-blind cohort removes this.
5. **Exact marginalization is inactive.** All P-min variables are observed, so the machinery is tested but not exercised on this data.
6. **Independence approximation.** X queries are treated as conditionally independent given their shared Y.
7. **LB cannot be cross-fitted.** Its protocol differs, so its comparison is limited to val21 and the fresh cohort.
8. **Travel labels are policy-specific.** They measure the first teacher witness's travel, not minimum travel.
9. **Folds are stratified by an outcome-derived stratum** (verified K). This only balances evaluation and never reaches a scorer.

## 9. Deliverables

**Code:**
- [bxy_p11.py](../bxy_p11.py): views, model arms, exact objective, trainer, prediction, selection, metrics, folds, roster.
- [bxy_p11_prereg.py](../bxy_p11_prereg.py): audits, perturbation, benchmark, budget, design, freeze / `assert_frozen`, preflight.
- [bxy_p11_viz.py](../bxy_p11_viz.py): figures.
- [tests/test_bxy_p11.py](../tests/test_bxy_p11.py): 35 tests covering exactness, gradients, marginalization, leakage, whitelist, canonical order, travel, no-op, DIRECT, splits / folds, dedup, arms, selection, metrics, freezing, and the synthetic trainer.

**Frozen artifacts:**
- [TRAINING_DESIGN.json](../runs/approach_b/bxy_p11_v1/TRAINING_DESIGN.json) (sha `24ffa822ac57c1ff33b0c20b52cbd7cbebfa975df74db1e1f14f8f2fec5782cf`);
- [TRAINING_LOCK.json](../runs/approach_b/bxy_p11_v1/TRAINING_LOCK.json): design sha, evidence hashes, transitive source hashes, `authorized: false`;
- [PREFLIGHT.json](../runs/approach_b/bxy_p11_v1/PREFLIGHT.json).

**Regression ([regression/](../runs/approach_b/bxy_p11_v1/regression/)):** full pytest suite **634 passed, 1 skipped, exit 0** (14 min 11 s; includes the 35 new P11 tests); six archived replays `g1_robot`, `g1_hardening`, `g2_interventions`, `g3_repairs`, `g3_5_initial_scene`, `g4a_evidence_audit`: **exit 0 × 6, `replay_passed: true` × 6** (77 / 77 / 2 / 50 / 20 / 257 trajectories).

**Figures ([visualizations/approach_b/bxy_p11_v1/](../visualizations/approach_b/bxy_p11_v1/)):**
- `01_training_data_audit.png`: roots by split and K; label kinds; travel supervision.
- `02_crossfit_design.png`: fold × stratum; per-fold custody.
- `03_scorer_vs_evaluator_s001.png`: two orders → one Y node, beside the evaluator-only outcomes.
- `04_roster_budget_capacity.png`: runs, expected CPU and parameter counts.

## 10. Verdict

**`READY_TO_REQUEST_TRAINING_BUDGET`.** Requested for the next gate (BXY-P12-TRAIN; not started):

| Request | Value |
|---|---|
| Runs | 108 (33 SPLIT + 75 CROSSFIT), roster frozen |
| Aggregate CPU | 110,000 CPU-s |
| Per-run CPU | 3,500 CPU-s |
| Workers | 8 (memory-gated, 1 thread each) |
| Wall | 31,200 s |

Planned comparisons:
- XY-quadratic vs XY-uncoupled-SA, and vs XY-uncoupled: the coupling;
- XY-quadratic vs noJ: travel;
- XY vs DIRECT / LB;
- every arm vs the references.

**STOP.** No training, tuning, teacher query, scene generation, historical test evaluation, `PREFIX_COMPLETE`, P-full or 3D was started.
