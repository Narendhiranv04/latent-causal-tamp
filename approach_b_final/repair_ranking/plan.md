# Approach B — Repair Ranking and Destination-Domain Generalization
## Time-prioritized experimental and implementation contract (v1.0)

**Date:** 25 November 2026  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Parent:** `naren/rss27-full-domain-set-search` at `7db1132d983a36b4505da02f23888237905cd17b` (verify locally against origin; do not silently change parent).  
**Proposed new branch:** `naren/rss27-xy-repair-ranking`  
**Scope:** 2D, K1/K2 primary, K0 and NONE safeguards, historical K3 regression audit only. No K>3, no 3D experiments or changes, no new motion planner, no new cVAE training.  
**Status:** prospective work package, not results. This document deliberately prioritizes evidence per unit of time. No previous teacher allowance is carried over. See §2 for proposed new authorization and budgets.

> **Central question:** Can better supervision and decision-level training make the joint X/Y scorer reliably select executable, task-restoring corrective repairs, including those beyond the cVAE top-four destinations, without sacrificing the original top-four system's success or fast inference?

## 1. Scientific motivation and non-negotiable historical evidence

Read the following files at the pinned parent, then audit the actual code and checkpoint metadata. Do not treat this plan as a substitute for them.

- `approach_b_final/full_domain_sets/reports/P4_FINAL_DECISION.md`, `P3_PHYSICAL.md`, `P3_PREREG.md`, `P4_ATTRIBUTION.json`, `P4_WINLOSS_VS_EXACT4.json`.
- `approach_b_final/full_domain_sets/reports/P1_RECALL.md`, `P1_RECALL.json`, `P0_SOURCE_AUDIT.md`, `P0_FROZEN_PROTOCOL.json`, `P2_MODEL_ONLY.md`, `P2_TUNING_PREREG.md`, `P2_FROZEN_PARAMS.json`, `P3_SEAL.json`.
- `approach_b_final/mcts_sets/reports/P4_FINAL_DECISION.md` and `P3_PHYSICAL_VAL.md`.
- `approach_b_final/xy.py`, `contracts.py`, `search.py`, `placement.py`, `exhaustive.py`, `construct.py`, `benchmark.py`, `evaluate.py`, `scripts/v32b_phys.py`, `full_domain_sets/{domain,fsearch,run,analyze}.py`, `mcts_sets/search_sets.py`.
- Existing historical V3.4 and ablation reports, manifests, training snapshots, checkpoint configuration and seed files. Locate actual paths with Git and manifests, never guess a replacement. Check the original lineage metadata and fresh-cohort usage.

### 1.1 What has already happened

On the 191 K1/K2 VAL development roots, the original top-four exhaustive K<=2 planner (EXACT4) achieves 120/191 = 62.8% operational success; strict 120/148 = 81.1%, 43 UNKNOWN. Fixed-pool MCTS had no established benefit. The later full-domain study was `EXPANSION_NOT_ESTABLISHED (INCONCLUSIVE)`:

- Seeded MCTS @1024: 123/191 = 64.4% operational; 123/153 = 80.4% decided-only. Strict paired delta vs EXACT4 +1.4 pp [-2.1,+5.0], 140 decided pairs. No demonstrated advantage over seeded/full beam. 0.170 s median vs EXACT4 0.027 s, same RTX 5060 timing subset.
- EXACT_FULL, the frozen model's exhaustive full-domain choice: 109/191 = 57.1%, strict 109/149 = 73.2%; strict paired delta -4.4 pp [-9.8,+0.7]. The model optimum is not a physical oracle.
- Increasing budget 1024 to 4096 lowers predicted regret but decreases operational success (seeded MCTS 64.4% to 61.3%). Neither more search nor higher confidence is a demonstrated remedy.
- P1: 61/71 operational EXACT4 non-successes had a known successful in-pool repair; 10 had only known off-pool witnesses. This combines exact-contract teacher caches and a secondary generator protocol, and is a lower-bound witness analysis, not exhaustive physical truth. Strict P4 attribution: 22 ranking, 6 pool-miss, 43 unresolved; seeded MCTS: 23 ranking, 7 retrieval, 38 unresolved. Do not conflate these denominators.
- Successful off-top-four repairs exist. Seeded MCTS committed 82 verified off-top-four successes, full beam 98. These are not all net rescues. All 10 strict losses of EXACT_FULL against EXACT4 used off-top-four assignments. Uniform-prior ablations trend worse; not every contrast is statistically significant.
- Existing VAL and previously used V3.4 fresh cohorts are exposed development evidence. No independent confirmation from reusing them. UNKNOWN is not an infeasibility certificate. The >20% unresolved criterion made the primary strict result inconclusive.

### 1.2 Hypotheses (not foregone conclusions)

H1: X/Y misranking and decision errors dominate over missed candidates for K1/K2. H2: errors increase in particular destination-rank and intervention strata, possibly due to selective training support and/or model capacity. H3: cheap conditional calibration/prior-aware selection can prevent harmful off-pool replacements. H4: targeted intervention coverage and within-root ranking supervision improve actual repair selection. H5: with a better scorer, expanded search might help; MCTS is optional and must still beat equally capable alternatives to justify adoption.

Do not claim that X/Y was trained only on cVAE candidates without auditing the snapshot. The original training labels come from finalized intervention manifests, not necessarily a cVAE-filtered pool. Do not infer causal blockers from network logits. Do not assume the coupled head is the cause of errors or that calibration, ranking loss, or new data must work.

## 2. Resources, authorization, and time-crunch rules

### 2.1 Priority order

1. **Mandatory, immediate, no new teacher calls:** P0, P1, P2 archived-label experiments, baseline reproduction, preparation of manifests. Reuse exact-contract caches and existing TRAIN labels wherever possible. No GPU-wide grid searches; run a small predetermined set of configurations.
2. **Mandatory if new training is authorized and P1 demonstrates usable contrasts:** P3 targeted data, P4 controlled learning. Start data inventory/manifest preparation in parallel with P1. Do not wait for a prettier report before starting another independent CPU-only task.
3. **Mandatory model-only P5** for completed eligible models; bounded physical P5/P6 only after authorization and sealing. Reserve evaluation compute first; never exhaust the entire budget on training. Stop if prerequisites fail and produce an actionable report.
4. **Optional only after primary results:** extra training seeds, a second ranking loss, architecture changes, wider rank pools, extra physical queries. Not part of the minimum viable run.

Run stages in dependency order; parallelize safe CPU diagnostics and authorized teacher jobs. Do not run GPU timing concurrently with training, inference, or other GPU jobs. Use resumable per-root/per-query output, deterministic seeds, atomic checkpoints, no busy waiting. Report actual elapsed wall time, CPU-hours, GPU time, peaks and job IDs; never promise an ETA without measurement. Do not launch unbounded or speculative jobs.

### 2.2 Proposed new resource caps (owner must explicitly authorize)

These are planning defaults, not a statement of existing permission. The old 1,200-query allowance belonged to the completed study and is not reusable. A suggested owner approval line is provided in the starting prompt.

| Resource | Suggested fast-track maximum | Allocation / guard |
|---|---:|---|
| New 2D teacher ordered-sequence queries | 3,600 total | <=1,800 P3 TRAIN, <=600 fresh-cohort construction/certification, <=1,200 P5/P6 validation, deduplicated only where exact contracts match; reserve the validation allocation |
| Teacher CPU | 24 worker CPU-hours combined | <=12h TRAIN, <=6h cohort certification, <=6h validation; first cap reached stops the corresponding work |
| Teacher machine | gvlab2, <=32 workers | confirm actual free cores/memory, preserve other workloads; reserve at least 4 cores; smaller if needed |
| GPU training | <=8 aggregate GPU-hours | initial fast-track 1 seed per arm; at most 2 additional matched seeds for finalists within cap; record actual GPU/model/device |
| Inference and analysis | <=4 GPU-hours plus ordinary CPU | avoid repeated all-grid enumeration; chunk, stream or reuse immutable tables per model; don't count replay as deployment |
| Storage | <=20 GiB new working artifacts | no private raw data/checkpoints in Git; keep model checkpoints in approved local/server storage; commit manifests and compact aggregates |

Count all physical X/Y evaluation jobs and construction/certification teacher calls in a ledger; additionally report X calls, Y calls and low-level planner attempts. If the generator cannot expose a comparable count or enforce caps, do not launch it until a separate bounded protocol is approved. A physical query is an ordered sequence under the unchanged teacher contract (including separately tracked X/Y calls); no unmetered hidden retries. If no approval is recorded, perform all no-new-label work and prepare exact proposed manifests; stop before new physical collection, training or protected TEST access. Owner approval can authorize the above new training and teacher use in one go. Protected TEST access always needs explicit separate permission if a truly fresh cohort cannot be obtained. No transfer of leftover allocations without logged, explicit approval. Do not change teacher timeout or planner budget to manufacture a lower UNKNOWN rate; if an evaluator change is required, separate method, matched reruns for all arms, preregistered, separately authorized.

## 3. Fixed method, notation, and implementation layout

Public original root S0: object attributes, poses/grid cells, target, task goal, robot context/reference pose, legal support. K_max=2 for every inference root; true K is private evaluator metadata. A legal relocation (o,d) moves an eligible non-target, non-fixed object to an originally empty supported cell, not the goal. Each object and each destination used at most once. No vacated-cell reuse, swaps, repeated object, artificial object removal, or altered fixed flags. A canonical assignment A is an unordered set; a sequence r is an ordering of A. K2 has two orders, both charged and evaluated together. X/Y can use ideal-prefix representations internally as before, but no intermediate-root inference, state transition, teacher, IK, or robot planner in deployment.

Frozen cVAE: S1 TaskCVAE `scratch_all` s0, n_z=64, proposal seed=0. D4 and D6 derived exactly from archived top-six order. Full marginal pi_cvae(d|o,S0) provides a destination preference, not an object-importance score or certificate. All legal cells remain available in expanded arms. The learned prior is conditioned on the considered object. Full domain is static legality only, not physical feasibility.

For an endpoint s and ordered sequence r, existing coupled X/Y coefficient outputs b_s, a_r, w_r, tau=1 give:

```
pY(s) = sigmoid(b_s)
pX1(r) = P(X=1 | Y=1,r) = sigmoid(a_r+w_r)
pX0(r) = P(X=1 | Y=0,r) = sigmoid(a_r)
pX(r) = pY*pX1 + (1-pY)*pX0
p11(r) = pY*pX1
```

Here X is execution of the ordered relocations and required reference connector per teacher contract, Y is target-task feasibility in the edited endpoint under its reference convention. The coupling is probabilistic, not proof of causation. NOOP predicts pY(S0). `search.Scorer.score` exposes p11, py and marginal px; **do not mistake px for conditional pX1**. Implement a read-only diagnostic adapter to `coeffs` / `make_view` / `collate` for logits and conditionals, numerically stable; compare against `predict`. Do not divide by tiny py as the production diagnostic. Check exact identities and batch invariance. Shared endpoint Y remains one observation across orders; do not duplicate labels or silently alter the original joint likelihood.

Frozen reference selection `xy.choose`: if p_noop >= 0.5, NOOP; otherwise admit candidates with p11 >= 0.3 (including the empty row as in the real code); if none, ABSTAIN; then minimize `-log(max(p11,1e-12)) + alpha*m + beta*D + gamma*J_hat`, with alpha=beta=gamma=0 and exact deterministic ties. Verify actual handling of the empty candidate below the NOOP gate; do not assume it cannot be selected. For baseline retain the exact rule. Candidate ranking changes must not redefine true task success.

### 3.1 Minimal new code (suggested names)

All new code under `approach_b_final/repair_ranking/`, avoiding name shadowing of `search.py` / `run.py` from older experiments. Reuse source by explicit import paths and thin adapters. No edits to `xy.py`, historical reports, snapshots, frozen model bundle, or existing search branches unless explicitly required and approved (prefer wrappers).

```
repair_ranking/
  README.md, plan.md, config.json
  audit.py           # provenance, teacher/label and split audits
  diagnostics.py     # read-only model readouts and within-root analysis
  calibration.py     # cheap frozen inference variants
  collect.py         # deterministic TRAIN manifest and label merge (private)
  train_rank.py      # adapter + ranking objective + training harness
  run_eval.py        # planner-only inference; no private fields / teacher
  evaluate_rank.py   # evaluator-side manifests, physical results, bootstrap
  figures.py        # compact real-scene and aggregate visualizations
  tests/            # focused tests, no giant framework
  reports/          # phase markdown, JSON metrics, hashes and figures
```

Aim for <=300 lines per core file when practical; avoid monoliths, unnecessary frameworks and duplicated legacy logic. Private manifests and teacher caches outside repo with access restricted to evaluator/collection process. `run_eval.py` accepts public root and model bundle only. No training rows, K, labels, masks, certificates, witness IDs, or teacher outputs accessible at inference. Disclose any departures.

## 4. Data partition and evidence policy (before any new optimization)

- `TRAIN_ORIG`: original frozen TRAIN roots, their verified observations and lineage IDs. Only these (or newly generated explicitly assigned TRAIN families) may enter optimization of network weights. New teacher queries on TRAIN only in P3. Do not train on the 751 old VAL roots, including the historical 151/600 split. No label laundering through caches.
- `DEV_CAL`: choose a deterministic family-level hash split of previously exposed VAL families for calibration, ranking-loss weight and early stopping. Use only strict labels for fitting/selection of new rules. If old checkpoint used all VAL for early stopping, acknowledge that these roots are not independent of historical training selection. Use the complementary `DEV_AUDIT` for development diagnostics / screening and paired development evaluation. All siblings/near-duplicate lineage grouped; compare root IDs, scene/geometry fingerprints, family IDs against TRAIN. Do not claim independent test from either.
- `CONFIRM`: genuinely unseen lineage-disjoint public cohort, ideally preexisting unopened authorized holdout or fresh generated roots. Freeze generation seeds, roster and label protocol before inference. Aim for >=80 K1 and >=80 K2 (ideally >=100 each), plus K0/NONE safeguards if available; counts are targets not permission to exceed budget. No handpicking by model performance. K bins follow original generation/certification protocol, not globally proven minimum. If protected TEST is the only option, stop and ask for explicit one-time approval; audit historical access first. Previously examined V3.4 fresh cohort is a regression cohort, not new confirmation. No access to confirm outcomes for tuning. If fresh certification costs are excessive, report `DEV_ONLY / CONFIRM_BLOCKED` rather than recycling exposed roots.
- Partition by parent family, not root hash alone. Preserve membership manifest, lineage hashes and counts; verify no overlaps. Calibration roots and audit roots separated before fitting. New TRAIN examples cannot share a family with CONFIRM; if existing data conflict, resolve conservatively before training. Private files never reach planner.

### Strict supervision semantics

Teacher cache merging keyed by exact root, endpoint/ordered sequence, teacher version, configuration, reference-pose and geometry contract. A positive X or Y requires verified/certified status with matching value; a known negative requires a sound verified/certified zero; UNKNOWN/timeouts/unattempted remain missing. Failures can be identified in joint Z=X*Y if either factor is soundly 0; a positive requires both 1; if neither sufficient evidence, Z unknown. Follow the exact teacher contract; no generator-only Y=1 promoted to X=Y=1 in training or primary evaluation. Historical generator labels may appear only as clearly separate descriptive evidence, or as a separately validated source under explicit parity and authorization. Preserve partial X/Y observations for exact marginal likelihood. If labels disagree for an endpoint/order, quarantine and report; do not pick the convenient value. Same endpoint Y shared across orders only if reference convention identical. Use `-1`/missing masks rather than false zeros. Audit historic TRAIN label status provenance; if legacy labels lack sufficient metadata, report coverage and retain original unchanged only as a historical-control condition, not as new verified labels.

## 5. P0 — Audit, parity, and leakage checks

**Goal:** know which weights and supervision the old method actually uses; no reimplementation assumptions.

1. Pin parent SHA and branch. Hash protected tree, source, frozen 2D bundle files (sampler/scorer s0/s1/s2/scalers), dataset snapshot/label manifests, prior reports and evaluator harness. Confirm actual scorer arm, seed, feature configuration, training objective and dataset paths from checkpoint/manifest; historical source contains D/E/G/DIRECT, not every arm is necessarily in the bundle. Verify exact model and actual trained variant before naming it. Do not call model checkpoint architecture causal evidence.
2. Reproduce archive EXACT4 K<=2 decisions on at least 40 deterministic public roots (same exact proposal seed and frozen rule), D4/D6 parity, full-grid marginal, p11, pY, pX1 and pX identities. Check against existing sealed outputs at tolerance and exact decisions; batch size/shuffle invariance; no-op behavior including below gate. Reuse previous tests; do not change historical experiment.
3. Audit original TRAIN label counts by family, K, sequence length, endpoint, X/Y joint class, known/missing status, intervention kind (`SELECTED_ASSIGNMENT_ORDER`, omissions, distractors, alternatives; actual names from source), destination rank under frozen cVAE, set-level max rank and number off-D4, object eligibility, displacement and label source. Audit original evaluation/training generator geometry and teacher conventions. Check whether X/Y training distribution is narrow in ranks relative to legal support and in same-root competing outcomes. Report what is known, unknown, and missing. Distinguish cVAE training positives from X/Y intervention supervision. Query only public fields to compute marginal; analysis code joins labels offline.
4. Audit `xy.fit`: root-mean observed-data NLL actually sums observed nodes per root; adding many labels can overweight roots. Record number of observations/root and historical loss normalization. Do not claim per-label normalization exists unless implemented. Verify joint endpoint/sequence sharing, model seed and optional travel/aux flags; preserve probability math.
5. Reproduce prior P3/P4 aggregate counts from committed artifacts where accessible. Check exact-contract teacher caches, generator-only contributions and conflicts; report if private evidence unavailable. Test strict and operational outcomes and provenance. No new teacher queries.

**Deliverables:** `P0_AUDIT.md`, `P0_PROVENANCE.json`, `P0_TRAIN_COVERAGE.json`, split manifest/hashes, `P0_TESTS.json`; table/heatmap of rank x intervention class with counts. **Gate:** exact parity and data boundaries pass or stop the affected branch. If original training files are unavailable, run available diagnostics only; no fabrication.

## 6. P1 — Diagnose the frozen X/Y model (fast, no new queries)

**Do this before any retraining.** Use exact-contract cached labeled candidates on exposed development roots and original TRAIN observations. Keep protocol-mismatched historical witness labels separate. Primary metrics use known statuses, with missingness and source counts. Report root-macro averages and lineage-cluster uncertainty, not just a candidate-micro average dominated by roots with many labels.

### 6.1 Candidate-level readouts and contrasts

For each known endpoint and ordered repair, store the public signature, true X/Y/Z and provenance, `b,a,w`, pY, pX0, pX1, marginal pX, p11, p_noop, displacement, length, each cVAE probability/rank, number off-D4, tier, and frozen scorer seed. No labels enter the model. Score once in batches and cache by (checkpoint hash, root hash, ordered sequence), not by method. Keep unobserved labels absent. Report:

- pY vs decided Y (unique endpoints); marginal pX vs decided X (ordered sequences); pX1 vs decided X **restricted to observed Y=1**; pX0 vs decided X restricted to Y=0; joint p11 vs decided Z. Reliability diagrams, Brier score, log loss, AUROC/AUPRC with class denominators, calibration slope/intercept/ECE with specified bins, high-confidence false-positive fraction at p11>=0.8/0.9/0.95. AUROC alone is insufficient.
- Within-root pair concordance: compare every verified Z+ to verified Z- (or deterministic capped pair sample per root); ties count 0.5; report root/family-weighted mean, counts and intervals. Report known-candidate top-1, best-positive rank/percentile, top-3/top-5 recall and score gap between best true positive and selected false positive; report fraction of roots where no known positive exists. Rankings over known labeled subset are not full-domain physical optima.
- Stratify by K1/K2 roots (evaluation only), sequence length, T4 / T56 / TTAIL, one or two off-pool actions, same vs different moved-object set, same endpoint different execution orders, intervention kind, train vs dev, root clutter, displacement, and status/source. Include p11 distributions for high-confidence errors and frequency/shape of rank-related errors after matching root and length. Report counts; collapse sparse strata rather than overfit.
- For matched same-root positive/negative repairs, isolate (i) same object(s), different destination, (ii) different objects, similar rank/displacement, (iii) same set, different order with shared Y, (iv) omission / added move, (v) mixed cases. Only call these causal intervention contrasts if the construction and labels actually isolate the intervention; otherwise call matched comparisons.
- Compare conditional execution ranking on Y-positive endpoints, endpoint ranking on Y-positive vs Y-negative endpoints, and the joint ranking. For decided failed top picks, determine whether true Y=0, true X=0 with Y=1, both zero, or partial observation; high predicted pY and/or pX1 are diagnostic, not causal attribution. Avoid diagnosing pX1 against X when true Y=0. Report the coupling term distribution and compare available frozen D/E/DIRECT/G controls only if their checkpoints and contracts are comparable; if unavailable, mark not evaluated.
- Quantify proposal quality without conflating it with search: known positive witness action coverage and whole-set coverage by D4/D6/full; per-root number of known positive sets; rank distribution of positive and negative candidate actions; cVAE conditional probability not a learned object selector. Compare raw cVAE prior-only set ranking as a labeled-subset control (same length or normalized prior) to p11. Measure whether a successful known set actually enters the searched pool and the selected order. Do not count unknown candidates as failures or infer a hard recall bound from incomplete witnesses.

### 6.2 Decision decomposition (use sealed previous picks)

For each root, reproduce baseline and full-domain decisions and compare with the known decided witnesses. Mark mutually exclusive primary categories, plus orthogonal flags:

1. Verified success (in-pool/off-pool, minimal known length vs actual length).
2. UNKNOWN unresolved (never silently counted as negative); report status by X and Y and failure stage.
3. False NOOP gate / empty candidate chosen, ABSTAIN/admission failure (known successful scored alternative exists but all relevant scores below eta, or gate blocks it); distinguish from ranking.
4. Ranking failure (a verified successful scored candidate loses to a verified failed candidate), split same-set ordering vs different set and true X/Y class.
5. Retrieval/pool miss candidate (known legal witness not scored), or no known witness (unresolved explanation). Absence of known witness is not proof of no valid repair.

For P1, label-aware analyses run only evaluator-side. Check strict attribution counts vs historic P4; differences are allowed if stricter source filtering or gate categories are added, but reconcile exactly and retain both. Use paired roots for method contrasts. Quantify rescues and harms separately, especially off-D4 replacements; do not call all off-D4 successes rescues. Inspect K1 vs K2; do not tune on ground-truth K. Use at least four reproducible real-scene figures: X failure, Y failure, off-D4 rescue, off-D4 harmful replacement; overlay object moves, known outcome, score components and cVAE rank. No private witness sequences in public Git; anonymize or use approved public scenes with non-sensitive derived examples.

**Gate and deliverables:** `P1_DIAGNOSTICS.md`, `P1_RANKING.json`, `P1_CALIBRATION.json`, `P1_FAILURES.json`, `P1_TRAIN_SUPPORT.json`, figures. Establish the number of usable strict same-root Z+/Z- pairs and rank strata. If strict known comparisons are too sparse, report diagnostic limitation and prioritize targeted data P3; do not invent labels. If errors are primarily gate/admission, prioritize P2 gate analysis. If no evidence of off-pool distribution shift, still test the data/learning hypotheses as such, not a presumed fact.

## 7. P2 — Cheap frozen-scorer inference fixes

**No network weight changes.** Fit/tune only on DEV_CAL strict labeled candidates; assess on DEV_AUDIT. Never tune on CONFIRM or use known positives to select plans online. Same frozen cVAE, same candidate sets, same kmax=2, same NOOP policy by default, same exact order coverage. Evaluate known labeled subset first to avoid pretending unseen candidates are failures. End-to-end sealed picks with cached verification may be reported with coverage and bounds; no new teacher calls by default. New selections without cache remain unresolved, not negative. Choose at most one frozen-rule finalist for physical confirmation if P2 provides credible improvement in within-root ranking and no safeguard regression.

### 7.1 Small, prespecified controls

Let `s(r)=log(max(p11(r),1e-12))`; define `off(r)=# off-D4 actions / |r|`, and `prior(r)=mean_i log(max(p_cvae(d_i|o_i,S0),1e-12))`. The prior is length-normalized; it is not a probability of a whole correct plan. Normalize rank/probability penalties within the object if using a different form. Use no action penalty for empty sequence; compare NOOP as its own candidate using original gate/score semantics. Costs and signs must be tested.

| ID | Fixed candidate scoring / selection change | Purpose |
|---|---|---|
| F0 | frozen p11 and exact old rule | historical anchor |
| F1 | fit global scalar temperature or Platt logistic map on p11 logit | calibration-only sanity; monotonic mapping cannot improve fixed-pool repair ranking absent thresholds |
| F2 | simple tier-conditioned logistic calibration: shared positive logit slope + intercept + off-D4/rank-tier offsets (regularized) | can change within-root cross-tier ordering; sample counts and shrinkage essential |
| F3 | `s + lambda*prior` or `s - lambda*off`, test each separately with small lambda grid {0,0.05,0.1,0.25,0.5} | explicit cVAE regularization of final choice, not just search guidance |
| F4 | anchored off-pool replacement: retain best EXACT4 candidate unless off-pool score exceeds it by delta {0,0.02,0.05,0.1} in calibrated probability units; if anchor abstains, apply predeclared admission for expanded repair | prevent replacing a good baseline with barely higher, less reliable alternative |
| F5 | three archived scorer seeds, joint p11 mean, then mean minus lambda*std (lambda {0,0.5,1}); calibrated clip if required | epistemic-disagreement proxy, not proof of uncertainty; report 3x network cost |
| F6 (secondary) | NOOP/admission calibration or small length penalty alpha {0,0.01,0.03,0.1} | only if P1 diagnoses gate/redundancy; do not silently change primary rule or use true K |

Use fitted conditional calibration only with sufficient labeled support in each stratum (suggest >=30 positives and >=30 negatives pooled before allowing a separate effect; otherwise shrink/merge). For F2, no negative slopes or unbounded interpolation; fit simple low-dimensional logistic model, regularization chosen on DEV_CAL or family CV. F1/F2 calibrated probabilities used consistently with declared admission if that is the experimental variable; otherwise keep the original raw admission gate and change ranking only. For F3, scores are **utilities**, not calibrated probabilities; admission uses original raw p11. For F4 specify exact selection precedence when baseline chooses NOOP/ABSTAIN and handle empty candidate; default NOOP gate shared, baseline anchor cannot be lost unless logged variant explicitly allows it. Do not interpret a changed threshold alone as a ranking improvement. F5 ensemble is a diagnostic comparator, not a default if too slow. Keep total combinations modest; do not stack every variant. One combined best simple variant is optional, selected on DEV_CAL only and logged.

Use exact same known candidate universe for all variants; additionally compare D4, D6, rank cap 12, and a budgeted expanded candidate set on deterministic development subsets. Report root-macro pair concordance, Brier/log loss, false-positive tail, known-label top-1, rescue/harm, strict labeled coverage, model score vs actual outcomes, and live latency. Selection criterion on DEV_CAL: highest root-macro pair concordance, then lower high-confidence false-positive rate and simpler rule; gate/safeguard nonregression and known top-1 required for promotion. Do not promote solely on ECE. Report DEV_AUDIT once with frozen rule. If labeled support inadequate, do not select a new rule. No guarantee that rank-dependent calibration generalizes; it may only suppress valid tail repairs.

**Deliverables:** `P2_PREREG.md` before fitting, `P2_FROZEN_RULES.json`, `P2_FROZEN_INFERENCE.md`, `P2_RESULTS.json`, score reliability and top-1/rank plots. Keep the best frozen-rule candidate available for P5. P3/P4 remain justified as controlled experiments even if cheap P2 is promising, provided authorization and usable training contrasts; do not force expensive training if P1 and P2 show there is no evidence or the budget cannot support it.

## 8. P3 — Targeted TRAIN interventions (only after new authorization)

**Goal:** improve training support exactly where the scorer is unreliable. Teacher supervision is offline. Freeze candidate-selection/collection policy before new labels are revealed; avoid selection bias by collecting a mixture of difficult and representative examples. Use no fresh confirm scenes, no historical VAL roots, no protected TEST. Prefer existing strict labeled TRAIN alternatives before asking for new queries. Do not use existing P3/P4 VAL teacher calls for network training.

### 8.1 Collection manifest

Build a deterministic, lineage-aware TRAIN roster with a mix of K1/K2 roots and safeguards. K metadata may stratify the offline collection; it is never fed into the model. Preserve existing K3 TRAIN data in replay to mitigate regression. Aim for a broad number of roots rather than repeated variants on a few. Under 1,800 new TRAIN ordered-query cap, a reasonable initial target is 300–450 distinct TRAIN roots with about 4–6 new ordered queries/root if available, adjust deterministically to actual budget and dedup. Verify counts before scheduling. Use frozen cVAE and scorer for candidate generation on S0. Reuse batched exact D4/D6, capped sampled broader candidates or frozen batched beam/MCTS; full exhaustive only on small selected subsets and only for diagnostics. Score both orders when labeling an unordered K2 contrast if both can be afforded; do not claim complete order coverage otherwise. For matched order pairs reserve both queries together. Sample one or more known-positive TRAIN anchors from existing strict labels; if unavailable do not use an oracle positive from private VAL.

Proposed quota by **new ordered queries**, preallocate with deterministic rollover among TRAIN categories, not based on results:

| Collection type | Share | What to query |
|---|---:|---|
| Model-selected high confidence alternatives | 30% | Highest-scoring not-yet-labeled competing D4/tail repairs; candidate high score is only a hypothesis, not a negative label |
| Same-object destination contrasts | 25% | From known positive set, replace one legal destination with a rank-5–6, mid-tail or low-tail cell; preserve object set and length, include both physical orders for K2 when possible |
| Object-set / omission / synergy contrasts | 20% | Replace one moved object with another eligible object, omit one move, add a compatible second action; preserve legality and label actual effect; do not assume omitted/extra action automatically fails |
| Order contrasts | 15% | Same endpoint, both orders where missing; especially suspected executability disagreement or unusual high confidence |
| Representative broad coverage | 10% | Seeded random legal sets, stratified across length and rank bins, independent of score |

Across first two categories, target a mix of T4, T56, ranks 7–12 and >12 where legal. Track source, rank, object/length, model score, acquisition reason, pair group, duplicate and exact teacher hash. Hard negative is **only** a teacher-verified failed high-scoring candidate; hard positive is **only** a verified success with low score or bad within-root rank. Do not balance by relabeling; if rare, report. A second acquisition round is optional within the same TRAIN cap, preregistered, using first-round TRAIN outcomes and model errors, never DEV/CONFIRM. If collecting in one round saves time, do that.

### 8.2 Teacher execution and label merge

Use unchanged `benchmark.teach -> evaluate._verify_job` or verified equivalent, exact reference pose and task. Precompute sealed manifest keyed root + ordered sequence, dedup against verified exact-contract labels; a cached UNKNOWN is not a new negative or an automatic retry. Record separate X/Y labels/statuses, phase, planner budget, timing, endpoint signature and geometry hash. Share Y across orders only when teacher semantics prove equivalence; check conflicts before reuse. Preserve partial observations for joint likelihood. No unbounded retries or alteration of teacher planner budget. Use separate cache directory; all failures, interrupted jobs and unknowns ledgered. Keep private raw outputs outside Git.

Merge new observations into TRAIN only by stable identity. Deduplicate one Y node per endpoint and one X node per sequence. Maintain original TRAIN label snapshot and immutable augmented snapshot; include source/provenance, root/family, counts, conflicts, hash. Store clean training labels with UNKNOWN absent; baseline remains original historical model. Use explicit matched controls for any legacy-label sanitation. No raw training label file in public Git. Generate figures of matched contrasts and rank-stratified before/after training coverage.

**Gate:** proceed only with sufficient new strict observations and same-root positive/negative pairs to test ranking. Suggested minimal fast-track reporting target: >=100 TRAIN roots with both known Z+ and Z- across original+new data, >=50 roots with new decided tail candidates; if not reached, report low support, run only feasible controls and label conclusions exploratory. This is a design threshold, not an excuse to exceed caps. Report class counts, missingness, selection effects, actual resource ledger. `P3_COLLECTION_PREREG.md`, private manifest/seal, `P3_LABEL_AUDIT.md`, `P3_COUNTS.json`, snapshot hashes, progress figures.

## 9. P4 — Controlled learning: data vs ranking objective

Keep model architecture and cVAE fixed for primary learning experiments. Use the actual frozen coupled X/Y architecture/metadata (verify D arm), preserve endpoint and sequence semantics and original normalized Boltzmann factorization. Do not redesign network or introduce a transition model to make this work. Reuse original TRAIN + augmented labels under controlled conditions. All trained models get distinct hashes and filenames; never overwrite production weights.

### 9.1 Objective

For each root i, original observed-data joint loss is

```
L_joint_i = -log P_theta(observed X_i, Y_i | S_i)
L_joint = mean_i L_joint_i
```

Use existing `xy.batched_log_evidence` exactly, marginalizing missing variables. Keep joint loss separate from auxiliary decision loss. For each root with verified Z+ and Z- repairs, construct pairs using decided labels only. Define `s_theta(r)=log P_theta(X=1,Y=1|r,S0)`; compute from logits with log-sigmoid, not detached `predict()` and not naive probability multiplication/clipping for gradients. For coupled X/Y: `s=logsigmoid(b[parent])+logsigmoid(a+w)`. For uncoupled control w=0. For DIRECT: logsigmoid(success logit). Use a fixed margin m=0.2 nats for initial ranking objective:

```
L_rank_i = mean_(r+,r-) max(0, m - s_theta(r+) + s_theta(r-))
L_total = mean_i [ L_joint_i + lambda_rank * C * L_rank_i ]
```

If no valid pair, rank contribution zero (report pair-bearing fraction). `C` is the fixed median count of observed X+Y nodes per TRAIN_ORIG root (at least 1) recorded before training, to put rank loss on comparable scale to root-summed likelihood; never use outcomes to adjust C. `lambda_rank=0.1` primary; 0.5 secondary if budget and predeclared DEV_CAL tuning permit. Maintain same scaling across data arms. Sample up to 16 fixed-seed pairs/root/epoch with mixture of hard pairs and uniform same-root pairs, refresh by deterministic seed; avoid all-pairs explosion. No cross-root ordering; no treating unknown as negative; avoid duplicated Y labels from permutations. Pair labels may use a verified zero of either factor with the other missing, as the logical conjunction is then false. For conservative sensitivity, also report both-factor-decided-only pairs. Do not rank one success over another without a separately justified cost label. Positive vs negative ranking is supplementary, not a replacement for calibrated X/Y likelihood. Test gradients, finite values at extreme logits, duplicate handling and missing-label semantics.

The old NLL is a mean over roots of a **sum** of observed evidence, not a per-label mean. For primary factorial comparisons keep original semantics, same root roster and batch/epoch schedule, cap added examples/root, preserve original labels and log per-root node counts. This means data-only effect includes extra label volume as intended; report it. A matched per-observation/root-balanced normalization sensitivity is optional if differing counts dominate. If sanitizer changes legacy labels, run both original and augmented controls on same sanitized base; separately report original frozen historical baseline so effect is not confused with cleanup. Do not silently change loss normalization or mix architecture variants into the data/loss factorial.

### 9.2 Minimal controlled training matrix

Use warm-start from the **same frozen coupled X/Y checkpoint** for A1–A4, same optimizer initialization, same seed/roots/batch order and update count/patience, same model architecture, same label contract. A0 is the frozen reference. Predeclare optimizer and training budget before first fit; suggested short warm-start AdamW lr=1e-4, weight_decay=1e-4, gradient clip=10 (same as original), max 15 epochs, patience 4, batch 32–64 roots subject to memory; do not silently change between arms. Validate loss and pair metrics on DEV_CAL; choose checkpoint by prespecified joint likelihood plus within-root ranking metric or a common primary known-label top-1 criterion with tie NLL (see below). Record exact actual settings. No training on DEV_CAL. No expensive grid sweep. One seed initially; replicate at least the selected winner and A1 with matched additional seeds if budget remains; a one-seed result is explicitly pilot evidence.

| ID | Starting weights | Training data | Objective | What it identifies |
|---|---|---|---|---|
| A0 | frozen production | none | none | unchanged historical reference |
| A1 | frozen production | original TRAIN | original NLL | continued training / optimization control |
| A2 | frozen production | augmented TRAIN | original NLL | new data effect (A2 vs A1) |
| A3 | frozen production | original TRAIN | NLL + rank | ranking-objective effect (A3 vs A1) |
| A4 | frozen production | augmented TRAIN | NLL + rank | combined effect (A4 vs A2, A4 vs A3) |
| A5 optional | matched new initialization | augmented TRAIN | coupled NLL + rank | scratch reference for architectural comparison |
| A6 optional | matched new initialization | same augmented TRAIN | DIRECT supervised Z loss + rank | direct joint-success baseline, with matched data, training steps and comparable parameter count; no claim of exact capacity match without checking |

A1 is essential; otherwise additional optimization would confound data/ranking effects. A2/A3/A4 are the minimal factorial. Use A5/A6 as a **paired** optional scratch comparison, not a claim that a scratch DIRECT loss is inferior to warm-started A4. If matching compute or labels impossible, report archival DIRECT comparison separately as exploratory. DIRECT has no independent X/Y readouts; compare on decided Z and actual planning only. Existing available frozen D/E/G/DIRECT checkpoints may be analyzed without new training on P1/P5 when contracts match. If coupled vs uncoupled retraining is important, make it a separate matched optional comparison; no need to prove coupling superiority now. Do not train cVAE, or change its top-four ranks, in A1–A4.

### 9.3 Training evaluation and checkpoint freeze

For early stopping use common DEV_CAL known-candidate root-macro top-1 (only roots with known Z+ and Z-; score all known candidates with same kmax/order coverage), tie within 1e-3 by lower joint NLL for coupled arms (DIRECT uses Z NLL), then earlier epoch. NLL, pair concordance, high-confidence errors and safeguards reported each epoch. Checkpoint eligibility requires no material degradation of baseline known-label top-1 in D4 and no major K0/NONE or historical K3 regression (prespecify tolerance in preregistration, suggested <=3 pp absolute on observable known-label metrics; not a proof of noninferiority). If no model qualifies, retain A0. Choose the single trained finalist on DEV_CAL; DEV_AUDIT reported once and can veto gross regression but not search for another winner. If veto, report no trained finalist for confirm; do not retune on DEV_AUDIT. A2/A3/A4 comparisons are informative even if no finalist. Keep all model artifacts, hashes, configuration, learning curves, data counts, and wall/VRAM. Record best epochs and if data imbalance induced performance shifts. Optional learning improvements must be separate arms after primary; do not conflate model changes with cVAE/search changes.

**Deliverables:** `P4_TRAIN_PREREG.md` before training, configs and seed ledger, `P4_LEARNING.md`, `P4_ABLATION.json`, calibration/pair ranking/learning curves, checkpoint hashes, selection record. Run explicit joint probability/math self-tests and no-label-leakage tests. Stop training on budget or resource guard, report incomplete arms rather than claiming comparison.

## 10. P5 — Joint architecture and planning-level ablations

Do not evaluate a scorer only by AUROC or a lower training loss. It must choose better **complete repairs**. Cross the old and improved scorer with a small set of fixed search strategies. The user wants the whole inference architecture to improve, not a new MCTS paper.

### 10.1 Minimum inference matrix

Use A0 and all completed A1–A4 on matched D4 candidate lists for model-only DEV_CAL/AUDIT diagnostics; additionally evaluate the frozen inference finalist F* from P2. Evaluate expensive expanded arms primarily for A0 and the single frozen trained finalist A*, with other arms optional after primary. A* is selected by P4, not by final physical results. Use exactly the same cVAE weights and ranks in all cases.

| Candidate constructor | Role | Evaluation |
|---|---|---|
| NOOP / ABSTAIN + EXACT4 | production anchor; exhaustive D4 K<=2 | mandatory on every root for A0, F* where applicable and all completed coupled models |
| EXACT6 | inexpensive broader exhaustive pool | mandatory for A0 and A* |
| EXACT12 | optional intermediate rank cap | one model-only screen; no forced physical arm |
| BEAM_SEEDED4 and BEAM_FULL @1024 | prior-guided batched search controls | mandatory for A0 and A*, historical parameters frozen |
| PW_MCTS_SEEDED4 @1024 | previous staged MCTS, unchanged | mandatory for A0 and A*, historical parameters frozen |
| PW_MCTS_FULL @1024, uniform beam/MCTS, random | search/prior controls | optional unless specifically needed to explain a new observed benefit |
| EXACT_FULL | exhaustive model-optimum diagnostic | A0 vs A* on a predeclared family-hash subset (e.g. 40 development roots, resource cap); stream GPU batches, record exact coverage; never present incomplete capped enumeration as EXACT_FULL |

Primary A* vs A0 with EXACT4 isolates scorer improvement. A* with expanded beam/MCTS vs A* EXACT4 isolates candidate-domain/search effect. A* expanded vs A0 expanded tests improved scorer under same search. Compare F* with A* without silently stacking both changes. A combined finalist (A* + calibrated rule) may be selected only on DEV_CAL with preregistered procedure if needed; then label separately. Keep actual original NOOP/eta rule as primary for A1–A4 to isolate learning. One secondary threshold-tuned version may be logged separately if needed. No post-hoc retuning of the old search hyperparameters; changes require a distinct secondary arm.

**Same-pool diagnostic is mandatory:** for each scorer, score the same D4/D6 and archived expanded sets on a common public root, evaluate known-label top-1 and matched positive/negative ranking. For true end-to-end adaptive search, search with that scorer's own values; candidate traces may differ. This separates selection errors from retrieval changes. Measure known-witness whole-set recall among scored sets, true X/Y on chosen candidates where available, new off-D4 rescues and losses. Use cached replay only if batch parity established per model and candidates charged as in live. Avoid generating full tables for all 751 roots and all models; use cached small pools and live batched methods. P2 old timing and model-only summaries are historical anchors, not evidence of new model runtime.

### 10.2 Planner controls and timing

Every completed set evaluated in every order; count unique ordered X/Y evaluations including NOOP, number of sets, batches, cVAE calls/decoder evaluations, model calls (ensemble counts), time to construct, time to score, time to choose. Use unchanged canonical grammar, fixed seed 0 for physical picks, seeds {0,1,2} for model-only stochastic variance if resources allow. Use budgets 256 and 1024 for model-only sensitivity, 1024 primary expanded arm; 4096 optional only if there is evidence. Report matched-score and matched-wall comparisons; measure on same hardware, warm-up then synchronized live calls, median and p90 on a predeclared 30-root subset, no concurrent GPU jobs, uncached prior and complete final decision time. Batch parity vs replay must be checked, especially new scorer coefficients/calibration. Teacher runtime is evaluation cost and is not online planning time.

Before any physical verification of new picks, freeze architecture, checkpoint, candidate constructor, thresholds, seeds, roster and per-root selection records and SHA256 seal. On DEV, use old exact-contract labels when available; report label coverage and unknowns, not a claimed physical success rate from selected-known-only subsets. If DEV physical queries are necessary for model/strategy selection, preallocate <=200 of the 1,200 validation allowance **before** any such queries, keep independent CONFIRM allocation and explicitly mark DEV-only; no adaptive repeated tuning on the same physical outcomes. Prefer model-only screening plus confirmation when time is short. If P4 does not produce an eligible A*, use A0 plus F* if eligible and report negative learning result, rather than inventing a winner.

**Decision policy for CONFIRM:** choose at most one primary revised pipeline on DEV_CAL (with DEV_AUDIT veto only): improved scorer with EXACT4, frozen rule F*, or improved scorer with expanded search. Use a deterministic rule documented in P5 preregistration: first prioritize common-pool known top-1 and ranking improvement with safeguards; only promote expanded constructor if it improves DEV_CAL known-label end-to-end selection with comparable known-label coverage, no severe DEV_AUDIT regression and practical latency; otherwise choose improved EXACT4. Retain at most two mechanistic secondary arms (A* EXACT4 if primary expanded, A* expanded or F* if primary exact) so query budget supports all matched roots. No selecting winner by CONFIRM outcomes. If no pipeline qualifies, freeze only baseline and best diagnostic comparator, or stop before spending confirm queries and issue a negative/development-only decision. No user time wasted on a new confirm cohort for a method that has not passed basic controls.

**Deliverables:** `P5_EVAL_PREREG.md`, `P5_MODEL_ONLY.md`, `P5_MATRIX.json`, `P5_TIMING.json`, `P5_FINALIST.json`, candidate/prediction seals (compact public predictions only), comparison figures. Retain historical K<=3 and 3D release unmodified; do not silently replace scorer for those tasks. For K3 historical regression, compare same original K<=3 candidate pool and rules with old/new scorer using available archived labels or model-only diagnostic; no new K3 teacher queries, no generalization claim.

## 11. P6 — Independent physical confirmation (bounded, only if authorized)

This is the endpoint of the study, not a repeated VAL search. Use `CONFIRM` from §4. If it cannot be obtained/certified under caps, report `CONFIRM_BLOCKED` and give a precise resource request; no substitution of a previously inspected cohort. The protected TEST is not to be opened without separate explicit permission. Confirm lineage overlap, public/ private isolation, scene roster, generation parameters, K convention, frozen models/rules and selection code before inference. Use K_max=2 for every public root; evaluator alone stratifies true K.

### 11.1 Evaluation manifest and outcomes

Primary contrast: revised frozen pipeline vs A0 EXACT4, one chosen repair per root per method. Secondary contrasts limited as in P5. K0/NONE safeguard decisions measured on all applicable roots, not used to tune or filter; NONE is relative to generator certification grammar, not proof of global impossibility. Use identical independent 2D teacher harness, q_ref convention and budgets. Run baseline and candidate for the same root roster. Dedup exact identical ordered choices across methods, no retries, no second-best fallback, no online teacher access. Do not prefer roots based on method-specific confidence or anticipated labels. If cap binds, use whole paired root blocks ordered by predeclared family hash; report lost coverage and reason. Budget authorization is ceiling, not requirement to consume it. For newly generated cohort certification use separate <=600/6h allocation; include every teacher call. If insufficient, do not mislabel constructed but uncertified roots as K1/K2; include a separate unstratified exploratory cohort only if preregistered.

Strict physical outcome semantics should be pinned against historical `analyze.outcome`, `strict_labels` and `v32b_phys`. Keep historical strict/operational parity in parallel, explicitly document any distinction: a soundly certified zero of either X or Y means conjunction is false; a positive requires both 1; otherwise unresolved. In old evaluator FAIL_Y has priority and FAIL_X may require Y=1, so a case X=0/Y unknown can remain historical UNKNOWN. Report both historical strict parity and logical-conjunction strict as sensitivity if they differ; **primary uses historical strict parity** for comparability. Never retroactively change prior report. NOOP/ABSTAIN are errors on certified K1/K2 per frozen protocol; no plan is a success only where the task convention says so. Every root accounted for, no hidden censoring. Show separate X/Y UNKNOWN status counts, physical failure phases, and bounds for joint success.

### 11.2 Statistical reporting and gates (pre-register before confirm predictions)

Primary strict paired difference on both-decided K1+K2 roots, 4,000 lineage-cluster bootstrap resamples (seed=0) using predeclared family ID; report pair denominator, discordant wins/losses, point and 95% CI. Also report per-arm decided denominators, operational ALL-root success (UNKNOWN->failure only for historical comparability), intention-to-treat success lower/upper bounds (all unresolved fail/succeed) and paired worst/best-case delta bounds with per-root missingness. Report K1/K2 separately as secondary; K0/NONE guard; exact status counts and selection length. Complete-case estimates can be selection-biased if UNKNOWN is method-dependent; discuss. Report no significance on differences whose intervals cross 0; secondary contrasts exploratory or Holm-adjusted if formal, predeclare family. A single-seed trained finalist and single cohort do not establish seed robustness.

Suggested prospective decision thresholds (explicitly adopt or change BEFORE labels, do not after seeing results):

- `SCORER_IMPROVED_CONFIRM`: selected revised pipeline's primary strict paired delta CI lower bound >0, both primary arms UNKNOWN <=20%, no material safeguard degradation (suggest point change no worse than -3 pp, with denominators/intervals), median live latency <=1.0 s. Also report whether point gain is >=5 pp (practically meaningful target, not a required outcome or post-hoc cutoff). Operational and worst-case bounds must be discussed; if they contradict the strict inference, label robustness limited. For an actual claim of improved X/Y independently of search, require matched EXACT4 contrast of trained vs frozen scorer; if primary is expanded, this is a required secondary mechanistic check but not an independently preregistered primary claim.
- `SCORER_IMPROVED_DEV_ONLY`: gains on DEV ranking / selection, no independent confirmation or primary CI includes 0. No generalization claim.
- `EXPANSION_HELPFUL_WITH_NEW_SCORER`: paired new scorer expanded vs new scorer EXACT4 lower CI >0 (secondary inference with multiplicity caveat), acceptable latency, and unresolved criterion; not inferred from cross-scorer comparison alone.
- `MCTS_ADDED_VALUE`: only if same new scorer and matched prior/domain/budget staged MCTS beats a strong staged and unstaged beam with predeclared positive intervals and <=1.25x slower; otherwise no MCTS claim. If secondary arm budget excludes this, mark untested, not negative or positive.
- `NO_ESTABLISHED_IMPROVEMENT`: interval crosses zero or guard fails; `INCONCLUSIVE` if UNKNOWN >20%, insufficient pairs or independent cohort blocked. `HARMFUL` only if paired upper CI <0 or preregistered safety/latency guard violated. Keep released EXACT4 frozen unless credible evidence supports replacement. No automatic upgrade of K3/3D.

Do not use historical VAL success counts to make a power guarantee. With small paired differences and many UNKNOWN, a useful effect may remain inconclusive. If no independent test is possible, the strongest claim is a DEV diagnosis and controlled training result. Do not expand evaluation budget after seeing a marginal p-value.

**Deliverables:** `P6_PREREG.md`, roster+seal hashes, `P6_PHYSICAL.md`, `P6_PAIRED.json`, strict and operational attribution, query ledger, `P6_FINAL_DECISION.md`, final figures. Commit/push isolated branch, no merge. If any stage is blocked, report exact completed/blocked gates and next minimal experiment; not a promise of future results.

## 12. Required tests and visualizations

Keep old 39 search tests passing (historical 13 + full-domain 26); no legacy edit to fix a test shortcut. At minimum add tests for:

1. Frozen checkpoint/feature parity, exact cVAE D4/D6 and decision parity; original grammar and K_max constant, no private-field access or teacher imports in planner-only modules.
2. `p11=pY*pX1`, marginal pX formula, conditional readouts from logits, same-endpoint pY across orders, extreme-logit stability, batch/shuffle parity. Preserve Boltzmann exact observed-data math; brute force on tiny roots with missing X/Y.
3. Strict label masks, exact-contract cache keys and conflict quarantine; generator protocol separate; distinct family partitions with no duplicates; X/Y negative and positive conjunction semantics; unknown excluded from ranking; same-endpoint Y dedup.
4. Ranking loss zero for correctly separated pairs, positive for inversions, gradients on actual coefficients, missing pair contributes zero; root-sum scaling, deterministic hard/uniform pair sampling; A1–A4 controls share initialization, data differences only as declared.
5. F1 monotone map preserves repair ranking, tier-conditioned/F3/F4 score/threshold precedence, safe empty/no-op behavior, conservative replacement, ensemble accounting.
6. Complete-order scoring, equal budgets, replay/live parity per new checkpoint, baseline exact parity and no mutation; P3/P6 manifest dedup, whole-root cap, seal verification, strict/operational outcome and bootstrap denominators. Simulated failure/timeout and blocked budget fixtures.

Visualizations per stage, not decorative: P0 rank-support coverage; P1 calibration/within-root score gaps and real scene examples; P2 before/after reliability and rescue/harm; P3 actual matched destination/object/order contrasts; P4 learning and ranking curves by tier and model; P5 budget/latency vs known-label performance; P6 paired win/loss with CIs and UNKNOWN bands, real successes/failures from permitted public scenes. Every figure states cohort, label provenance, exact denominators and predicted vs verified. Avoid bar charts comparing different decided denominators as if paired. Use compact matplotlib figures and one summary figure; no unnecessary rendering pipeline.

## 13. Final report checklist and stop rules

Answer these in order, with numbers and confidence intervals where applicable:

- Does the original X/Y TRAIN data actually underrepresent tail destinations or informative contrasts? Which X/Y/joint component and intervention type dominates decision mistakes? How many gate/admission vs true ranking vs retrieval failures?
- Does raw cVAE prior help whole-set recall, and does explicit use at final selection improve ranking without discarding useful off-pool moves? Is the effect of calibration real or just threshold movement?
- Is better X/Y ranking due to added data (A2-A1), auxiliary objective (A3-A1), both (A4 vs A2/A3), or merely extra optimization (A1-A0)? Are component probabilities preserved? Which claims are limited by one seed, label bias, or unavailable controls?
- Does A* EXACT4 select more physically successful repairs than A0 EXACT4? Does wider search with A* add value? Is MCTS justified over beam? What happens to runtime, K0/NONE, historical K3 regression, UNKNOWN and off-D4 losses?
- Do the independent results establish gain? If not, what is the smallest next necessary action? If scorer improvements are negative, retain frozen method rather than launching a new search study.

Scientific decision: separate candidate support, candidate retrieval, scorer ranking, decision thresholds, physical verification, and deployment latency. Improvements in any intermediate metric are not automatically gains in verified task success. No claims of K>3, causal blocker discovery, robot execution guarantees or global minimality. No changes to old data or report history. Preserve Git evidence of preregistration/sealing, all test outcomes, raw private labels off Git, resource consumption and actual limitations. Include final concise table of phase status, commit hashes, results, remaining blockers, and recommended released method.

**End state:** a defensible improvement (or defensible negative finding) for the *whole* K1/K2 cVAE + X/Y inference architecture. Only after this is established should long-horizon composition or K3/3D extension be opened as a separate study.
