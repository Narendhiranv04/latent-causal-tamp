# Complete-repair cVAE versus factorized proposal + X/Y — implementation and evaluation contract

**Version 1.0 | 25 November 2026 | RSS ablation | 2D and 3D, K≤3 only**

## 0. Decision and scope

This is a new, isolated experiment for the repository `Narendhiranv04/latent-causal-tamp`. It answers the reviewer question: **Why use a per-object generative placement model and a separate learned feasibility scorer instead of a single conditional generative model that predicts complete ordered repairs?** This is RQ1 of the RSS draft (Fig. 2 / discussion). It is NOT another attempt to improve MCTS or X/Y. The separate 3D K4/K5 composition study is out of scope and may run in another Claude Code session; do not touch its branch, files, runtime directories or GPU allocation.

Train only the new complete-repair cVAE (CR-cVAE). Keep both released domain-specific per-object cVAEs and all X/Y weights, scalers, thresholds and existing data immutable. No additional training interventions, new scenes, ranking loss, X/Y fine-tuning, MCTS, full-domain tree search, K>3, new physical training labels or changes to the physical teacher. Physical queries are for evaluation of sealed choices only. Use the existing 2D and 3D datasets. Separate models per domain, no cross-domain transfer. Public K_max=3 for every root; the true K is private evaluator metadata. Report K1, K2 and K3 separately and pooled; retain K0 and NONE as decision safeguards. Do not mistake the recent K≤2 diagnostics for the released K≤3 architecture.

### Context a fresh agent needs

- Existing method: original scene S0 + target object and goal → task-conditioned per-object cVAE → four destinations per movable object → all statically legal unordered assignments of 1–3 distinct movers and distinct initially empty destinations → all execution permutations → frozen X/Y → rank, commit or abstain. The original target is never relocated by the repair itself. Target execution follows the repair.
- X is physical execution of the ordered relocation sequence with the declared robot-reference connection; Y is task feasibility from its edited endpoint. In the coupled arm D, `pY=sigmoid(b)`, `pX1=sigmoid(a+w)`, `p11=pY*pX1`, marginal `pX=pY*pX1+(1-pY)*sigmoid(a)`. The separate X/Y model can use negative and partially observed intervention labels, unlike the generative positive-repair training objective. This extra supervision is a real architectural distinction and must be disclosed, not hidden as a matched-label claim.
- Previous 2D fixed-pool and full-domain MCTS studies did not establish a gain. The subsequent repair-ranking study (final `87ebf65d24`) did not produce a qualifying revised scorer. Keep the released models. Those studies are development-only, K1/K2, with high UNKNOWN rates. They are not this ablation's test data or baseline performance targets.
- RSS draft Table I contains historical 2D K≤3 success 51.8% and a 3D comparison 78.2% (mixed splits); neither number is a substitute for recomputing the baseline on the exact same roots, weights, rule and evaluator as the new arm. Historical fresh-cohort figures may differ. Never select whichever denominator makes ours look better.

## 1. Repository, source-of-truth and safety

Start from verified full SHA of `87ebf65d24` on `naren/rss27-xy-repair-ranking` (or an explicitly authorized descendant that contains the identical frozen source). Fetch, verify remote SHA, check clean state. Use an independent git worktree and new branch `naren/rss27-complete-repair-cvae`; do not checkout/reset the other session's worktree. Never merge. Separate output/cache/checkpoint prefixes e.g. `~/cr_cvae_runs`, `~/cr_cvae_private`, remote `.../complete_repair_cvae/`. No GPU or CPU jobs belonging to another session may be killed, modified or oversubscribed. Inspect GPU/CPU usage and coordinate exclusivity for live timing. Use a read-only bundle and snapshot paths, do not upload private raw data/checkpoints to Git unless already explicitly authorized. Commit code, configs, aggregate reports, manifests/hashes and sealed predictions only if compatible with existing data policy. Avoid module names `search.py`, `run.py` imports across packages, etc. Use explicit source paths and imports; the previous studies had module-shadowing problems.

Source audit at this commit (verify locally; paths to private files are host-dependent):

| Source | Contract |
|---|---|
| `approach_b_final/contracts.py` | `view2d`, `view3d`, `positive_assignments`, `v3_grammar`, immutable snapshot locks |
| `placement.py` | `scene_features`, `task_features`, `TaskCVAE`, `repair_data`, `fit_task`, `_fit_task_steps`, S1 marginal/proposal rule |
| `search.py` | `Root`, `Sampler.propose_many`, `Scorer.score`; original-root ordered queries |
| `xy.py` | `XYNet`, exact likelihood, `make_view`, `collate`, `choose` |
| `construct.py`, `exhaustive.py` | assignment/permutation enumeration, production streaming selector; `exhaustive.proposals` requests top 6 with seed 0, top 4 prefix |
| `benchmark.py`, `evaluate.py` | bundle hashes, public projection, seals, physical verification; 2D teacher and external 3D `fin3d` |
| `repair_ranking/reports/P0_AUDIT.md`, `P6_FINAL_DECISION.md` | frozen 2D model and historical data provenance, limitations |
| `full_domain_sets/reports/P4_FINAL_DECISION.md` | why another search experiment is unnecessary |

Known from source: 2D 8×8 grid, 3D 6×6; `MAXOBJ` 20/16 respectively; 2D attrs `[radius,is_target,is_obstacle,is_fixed]`, 3D `[is_box,is_cylinder,size,height,is_target]`; context lengths 9/19. 3D context includes sin/cos of 7-DOF q_ref, goal xy, target size/height/box flag. Do not assume fixed-object flag in 3D (existing Root treats non-targets as movable). Existing bundle typically `~/abf_v34/approach_b_bundle`; 2D scorer is arm D seed 0, original TRAIN snapshot `abf_v32_fb0eef4f5ff433ee`, 3500/751/749 train/val/test roots. **Verify 3D scorer family, sampler variant, both domain training snapshots, exact seed, config and val/test counts from actual manifest/checkpoint and logs**. The historical `fit_task` defaults do not necessarily equal the released training run. Report discrepancy; never silently choose older data or use 2D weights for 3D.

Mandatory P0 artifacts: `P0_PROVENANCE.json` (full SHAs, paths, checkpoint hash/config, teacher/version, split hashes, source file hashes); `P0_DATA.md` (counts, root/lineage/layout duplicates, number of positive sets/orders by K, K0/NONE reliability, data overlap, prior-data parity); `P0_PREREG.md` (resolved budgets, evaluation cohort, metrics, seeds, arms and analysis rules). Record missing assets and stop only the affected work package, not unrelated CPU work. Never claim the external teacher has been audited until actual source/runtime is checked.

## 2. Hypotheses and experimental matrix

Primary hypotheses are separate:

- H1 (two-stage utility): reranking complete repairs with the frozen X/Y improves physically verified top-1 over the same complete generator without a scorer.
- H2 (factorization utility): per-object top-4 + combinatorial construction + X/Y improves physically verified top-1 over a complete-repair generator + the identical X/Y at comparable inference resources. The natural-budget comparison evaluates the deployed systems; matched scorer-count and wall-time comparisons distinguish proposal quality from search effort.
- H3 (practical advantage): compare deployed ours against standalone CR-cVAE on success, parameters, latency and candidate efficiency. A positive H3 alone does not identify whether factorization or scorer explains the gain.

| ID | Proposer | Selection | Role |
|---|---|---|---|
| C0 / OURS | Frozen per-object task cVAE top 4 | All legal ordered K≤3 candidates, frozen X/Y | Primary released reference (EXACT4, K_max=3) |
| C1 / CR-ONLY | New complete-repair cVAE | Approximate prior predictive sequence likelihood; integrated root decision head | Strong single-model baseline; no X/Y at inference |
| C2 / CR+XY | **Exact same checkpoint and generated ordered candidate pool as C1** | Frozen domain X/Y and original selection rule | Isolates value of separate scorer; candidate pool frozen before scoring |
| C3 / CR+XY matched count | Same CR-cVAE, larger fixed sample budget if needed | Frozen X/Y, count-matched to C0 up to declared hard cap | Secondary, isolates proposer under comparable scorer budget |
| C4 / C0-budgeted | Frozen per-object top4 | Deterministic fixed stratified subset of C0 ordered candidates, same scorer budget as C2 | Secondary symmetric count-matched control; no tree search or retraining |

C3/C4 are accounting controls, not new learned architectures. Include C1-first-draw diagnostic and CR-ONLY with common frozen no-op gate on the **same pool** as sensitivity only (not a standalone single-network claim). For K1/K2/K3 repair-selection comparisons report both complete pipeline (own gate) and common-gate diagnostic, to separate gate changes from ranking. C2 must not expand permutations of C1 outputs in the primary experiment: that changes candidate coverage and confounds the reranking contrast. Secondary `CR-SET+XY` may enumerate all permutations of generated unordered sets as an explicitly different candidate-pool control, if cheap, not a mandatory physical arm. No hybrid proposal union in primary. No online physical teacher, true K, masks, certified witness or success/failure labels available to any proposer or selector.

## 3. Existing data — exact label semantics and matching

### 3.1 Repair supervision

Recreate the released per-object sampler's *actual* positive assignment corpus using the manifest's TRAIN snapshot and `contracts.positive_assignments` + `v3_grammar`. A complete repair is a nonempty ordered sequence r=((o1,d1),...,(ok,dk)) with 1≤k≤3; all object and destination IDs distinct; no target/fixed object, no initial occupancy, no original goal, no non-support cell. Pair endpoint Y with X by **canonical endpoint key** (not by list index), then retain only verified X=1,Y=1 orders. Audit snapshot provenance: finalized binary labels already censor unresolved outcomes; if any label source has ambiguous statuses, exclude it and disclose. Do not infer an unverified order is valid merely because another order works. No permutation augmentation of successful orders unless independently verified. Deduplicate by root, canonical assignment and exact order.

`placement.repair_data` groups by distinct assignment A and weights each action 1/(|A_i| |A|), where |A_i| is the number of assignments for root i. Match this by sampling root uniformly, assignment uniformly within root and verified order uniformly within assignment. Equivalent CR weight w(i,A,r)=1/(|A_i| |O_i,A|). Thus a root or endpoint does not become artificially important because it has six successful orders. Use all successful assignments, not only minimal ones; if released sampler provenance differs, make its exact policy primary, label alternative as sensitivity. Record both weighted and raw counts. No class-label K input; order labels and sequence length used only as training targets. Roots with no verified successful nonempty repair contribute no reconstruction/ELBO, never presumed negative examples.

### 3.2 Root decision supervision for a genuinely standalone model

A positive-only conditional generator cannot reliably abstain on unsolvable roots. Use a **small integrated root decision head** on the same scene embedding (not an external feasibility network or per-repair X/Y model). This allows one model to predict NOOP/REPAIR/ABSTAIN. Train with existing root-level labels only:

- NOOP: verified Y(empty)=1. If root label and witness disagree, audit; no silently overridden label.
- REPAIR: verified Y(empty)=0 and at least one verified legal nonempty repair within public K_max=3.
- ABSTAIN: only a sound existing relative NONE certificate for this grammar/horizon and verified Y(empty)=0; do not treat absence of a witness, unknown planner result or legacy NONE from another contract as proof. If certificates are not sound/exist only under restricted domain, explicitly describe the label as benchmark-relative; if no adequate labels, omit the ABSTAIN loss/class and disclose limitations, do not fabricate.
- Ambiguous root class: mask decision loss (can still train repair ELBO if positive known). K0/NONE metadata is evaluator-only; derivation of target labels occurs solely in training loader.

Decision head trained on root-uniform labelled TRAIN roots; class-weighted losses only if preregistered on TRAIN frequencies (default unweighted). For C1 use argmax of 3-class probabilities, deterministic ties NOOP, ABSTAIN, REPAIR; if REPAIR but no legal sample, abstain. Root decision is shared encoder + tiny head, still one checkpoint/model; do not claim it predicts physical feasibility of each candidate. To avoid extra supervision confounding C1/C2, C2 ignores head and uses frozen X/Y no-op gate and admission; also report C1 restricted to K1–K3 with common frozen no-op gate and no artificial p11 threshold. Explicitly disclose standalone head sees additional root supervision, while X/Y sees detailed negatives. For C1 standalone no teacher at inference; no score called p11 unless it is from X/Y.

### 3.3 Splits and cohorts

Keep original TRAIN/VAL/TEST and family/lineage grouping; no re-splitting to obtain more favorable results. Train new models only on TRAIN, use original VAL (exposed development) for checkpoint and inference-budget selection, no test labels for tuning. Verify geometry/layout duplicates and report sensitivity excluding overlaps where practical. Ensure actual 2D and 3D original sampler positive data manifests match; do not use `repair_ranking` P3 augmented data, K4/K5 scenes or private diagnostic caches for model training. Use already-existing locked evaluation cohorts; choose before examining new predictions/results. Prefer the exact historical V3.4 fresh physical evaluation roster for both domains **if** its public rows, raw scene paths, frozen scorer choices, outcome statuses and family metadata are available and compatible. This is a locked retrospective comparison, not an independent novel benchmark because historical baseline outcomes are known. Otherwise use the original historical TEST roster with a new evaluation-only authorization (no training process may read labels). No protected TEST access unless explicitly authorized, after all weights/configs/arms are frozen. If neither is allowed/available, report VAL-only development and do not claim independent generalization. Do not mix TEST and VAL or reuse old metrics on different roots. No new scene generation.

Primary cohort target: up to 150 K1–K3 roots per domain, ideally 50 per K (or all available if smaller), plus up to 30 K0 and 30 NONE per domain for decision safeguards. These are **proposed** caps; prefer entire available locked cohort if authorized budget fits and pre-register it. Sample within private strata by stable hash of root_id + fixed study salt, with family grouping/coverage and no baseline-success/prediction filtering. Include all selected roots even when no candidate is produced. If a stratum is small, use all and state counts. Same root IDs across every arm, every seed. If private evaluator K differs from a certified minimal repair, preserve legacy/relative meaning and report; never assert global optimality. An arm may return shorter/longer legal repair ≤3. No per-K oracle at inference.

## 4. Complete-repair cVAE: implement one credible joint generator

Use a **conditional VAE with a shared latent vector and an autoregressive pointer decoder over objects and cells**. This avoids the naive failure modes of independently predicting three actions, fixed object IDs, padding ambiguity, duplicate destinations and teacher-forced inference. It is intentionally a strong direct-generation baseline, not a straw man.

### 4.1 Condition

Condition c=E(S0,T) consists of full public original scene, geometry, occupancy, target identity, goal, robot context. Use same domain attributes, coordinates and normalization as frozen sampler. No query object is provided by oracle. A sensible implementation reuses the input feature functions: call `scene_features` with target as reference for all tokens, explicitly align its target-first + sorted object IDs to original slot indices, and use task features for target reference. Or implement a shared per-object MLP with same geometry/relative target/goal features. Use permutation-equivariant token encoder (shared MLP + masked mean/max pooling; optional small attention block if preregistered) and global scene context. Include each token's own attributes and location, target indicator and goal/robot context. Do not encode object ID integer as a learned identity; pointer logits refer to current tokens. Use original index map only for serialization. Mask padding, original target, and fixed objects from action pointer but retain them in scene encoder. Use occupancy support mask for destinations. Test permutation equivariance of encoder and teacher-forced likelihood under simultaneous slot remapping (tie effects may differ on sampled outputs).

### 4.2 Posterior and prior

Training only: an order-sensitive GRU/MLP over verified action tokens (object token embedding + destination embedding + position) and STOP, pooled with c, produces mu/logvar. `q_phi(z|c,r)=N(mu,diag(exp(logvar)))`; reparameterization `z=mu+exp(.5*logvar)*epsilon`, epsilon standard normal. Inference uses only `z~N(0,I)`, no posterior/ground truth/length. Start hidden state from [c,z]. Use a single z for all actions to model dependencies and alternative repairs. No separate learned placement model in C1.

### 4.3 Autoregressive decoder

At each t=1..3, with previous chosen actions and current hidden state, predict categorical over eligible object pointers plus STOP. For selected object o, predict masked destination categorical (all legal original-root cells, not restricted to per-object cVAE top4). Feed token(o,d), current scene summary and z into shared GRU update. STOP is disallowed before first action on repair branch and forced at cap 3 (deterministic, probability 1). After 1 or 2 actions STOP is legal; if no legal continuation, STOP forced. At initial step no eligible object/cell → explicit no-candidate, not uniform over -inf logits. After each step mask previous movers and reserved destinations; preserve original occupancy/goal exclusion. No resampling invalid actions, clipping invalid IDs or physical feasibility checks. This is static legality, not physical execution. Train with teacher forcing; inference feeds model's own sampled actions.

Factorization of one complete sequence:

```
p_theta(r|c,z) = product_{t=1..k} p(o_t|c,z,r_<t) p(d_t|o_t,c,z,r_<t)
                 * p(STOP|c,z,r_<=k)
```

For k=3 forced STOP term =1. This learns **which objects, how many, where, and in what order** under one latent and one decoder. Within-network autoregressive object/destination heads are not the original two-model architecture; there is no separate learned repair verifier in C1. This is a conditional sequence generator, not an independent per-slot multi-head placement model.

### 4.4 Loss

```
L_ELBO = E_q[-sum_t(log p(o_t)+log p(d_t)) - log p(STOP)]
         + beta * 0.5 * sum_j(mu_j^2 + exp(logvar_j) - 1 - logvar_j)
L_total = root-weighted mean(L_ELBO on verified repairs) + lambda_gate * CE(root_class)
```

Use sequence-summed reconstruction (not token average), so likelihood is normalized across variable length in the generative model; report per-token NLL as secondary. Root-balanced weights as §3.1; integrated decision loss on separate root-uniform minibatch or once per distinct root; do not multiply it by number of orders. `lambda_gate=1` initially, beta linearly ramps 0→1 in first 10 epochs or matching optimizer-step fraction. Mask ambiguous root labels. Report reconstruction components (object, cell, STOP), KL, decision CE, posterior variance/active dims and decoded diversity. No ranking loss, no success BCE on generated repairs, no new negative labels. Use original per-object baseline's existing supervision, frozen unchanged.

### 4.5 Capacity, training and time-efficient control

- Start h=128, z=8 (same default family as frozen sampler; verify actual h/z); shared 1-layer GRU width h, object pointer MLP/bilinear, destination MLP, posterior GRU, small decision head. Train from scratch, no pretrained X/Y. Independent seed {0,1,2} for each domain. AdamW lr 1e-3, wd 1e-4, batch 128 or 256 roots/sequences according to memory; clip 10, max 80 epochs, patience 15, beta warm-up 10. Prefer matching actual production optimizer-step budget, not only epochs, since dataset examples differ. Record params per component (including training-only posterior) and inference params, optimizer steps, unique root/assignment exposure, GPU peak, GPU-hours. Do not force equal parameter count by crippling the baseline: report CR vs per-object cVAE vs combined frozen system. If CR params exceed combined system or are much smaller, report and optionally run one fixed width control on DEV only before any eval; default no further architecture tuning.
- One quick overfit sanity run per domain on 8–16 TRAIN roots: reconstruct verified orders, STOP length and masks, check no NaN, correct gradients, decoder posterior ignored at inference. Then one seed per domain smoke fit; if healthy launch remaining seeds within cap. Predeclare checkpoint selection using weighted VAL repair negative ELBO (fixed beta=1 and fixed latent MC seeds) plus root-decision CE; select minimum with earliest tie, no physical queries for checkpoint selection. Record best epoch and loss curves. If KL collapse/poor repair generation, report; at most one pre-registered remedy (slower beta warmup or free bits, choose one based only on DEV) applied identically both domains if triggered; preserve original run, clearly label remedy. Never keep trying until ours wins. Choose seed 0 deployment before seeing outcomes; seeds 1,2 assess generation/likelihood stability and report physical sensitivity only if budget explicitly permits. If optional seed fits cannot finish, report incomplete, no seed cherry-picking.

## 5. Inference: strong standalone comparison and fair budgets

### 5.1 Generate complete candidates once

For each root use seed 0 (fixed root-derived RNG stream) and sample 64, 256 and 1024 complete prior trajectories as nested prefixes of the same stream. Distinguish **raw trajectories** from unique legal ordered sequences; duplicates charged and reported, never hide extra draws. A fresh z per trajectory plus categorical draws; no rejection beyond hard masks. Cache unique sequences and raw counts. Main C1/C2 budget choose 256 on DEV by fixed rule: retain 256 unless predeclared latency/memory cap fails, then 64 for both domains/arms or disclose domain-specific cap before eval. 1024 is secondary saturation diagnostic. Prior distribution supports all legal destinations, so CR is not artificially confined to top4. Track off-top4 rate, object-set diversity, length distribution, unique sequence count and per-root cVAE draw cost. C1 and C2 must read identical serialized pool hashes including order; C2 does not influence generation. A direct first prior draw is descriptive, not the strongest standalone.

### 5.2 Standalone selection without X/Y

For each unique candidate, use a separate shared set of L=64 prior latent draws (seed distinct from proposal draws) and teacher-force the **candidate itself** through decoder to compute approximate marginal likelihood:

```
log p_hat(r|c) = logsumexp_l [log p_theta(r|c,z_l)] - log L.
```

Choose maximum (tie shortest, displacement, lexicographic). This is an approximation to probability of a generated repair, NOT calibrated physical success; no threshold borrowed from p11. Use same latent draws for all candidates of a root, batch/chunk likelihood computation, count all sequence-latent decoder passes and latency. If this is too expensive, preregister a DEV-only reduced L=16 alternative or frequency ranking, use one primary rule before evaluation, disclose. Raw sequence likelihood favors shorter sequences by construction; report length distribution and fixed length-normalized likelihood diagnostic on DEV only, do not condition on true K. Gate C1 with integrated decision head; pool still generated for C2 even if C1 gate says NOOP or ABSTAIN. Report C1 common-gate sensitivity as diagnostic: p_noop from frozen X/Y, then CR likelihood rank without eta. On K1–K3 also report ungated best repair rankings when both produce a candidate. Do not call C1 common-gate a one-model baseline.

### 5.3 Reranking and released baseline

C2 scores each unique generated order exactly once using frozen `Scorer.score(root, seqs)` in batches. Apply exact production `xy.choose` / `exhaustive.Selectors` semantics, verified from manifest (expected noop_gate 0.5, eta 0.3, alpha=beta=gamma=0). No new threshold tuning. No score averaging with cVAE probability. C0 uses frozen `exhaustive.proposals` S1 top6 then prefix4, seed0; all `construct.assignments(D,k)` k=1..3 plus all permutations, streamed in chunks, same gate/selector. Reproduce archived predictions on ≥10 public VAL roots per domain (or all available fixture roots), including K3, NOOP/ABSTAIN. If parity fails, stop release comparison and diagnose. Do not use a new baseline that happens to be weaker than frozen EXACT4. Record natural count and time.

### 5.4 Budget accounting (do not conflate different model calls)

Report separately cVAE forward/latent trajectories, unique candidates, decoder likelihood passes, X/Y ordered scores, X/Y batches, CPU enumeration, total planning time, teacher calls during inference (=0). C0 exhaustive may score orders of magnitude more sequences than C2; that's a real deployed tradeoff but not an isolated proposer comparison. C3 uses fixed maximum raw 4096 draws or a predeclared lower hard cap; stop adding unique CR candidates when matching C0 count or cap, no promise of exact match. Mark underfilled roots; no artificial repeats counted as unique. C4 chooses from C0 pool with a fixed hash order stratified by k=1/2/3 (round-robin) to match C2 unique ordered scorer count; all legal orders eligible, no score peeking, explicit unequal coverage of assignments. Streaming hash selection allowed, no MCTS. Both use same selector and scorer. If exact count not attainable due to pool exhaustion, report actual. Matched-wall diagnostic on 20 predeclared DEV roots per domain: compare C0 and CR+XY at common measured wall cap(s) (e.g. 0.05/0.25/1s; choose after DEV hardware audit and freeze). A naturally completed method returns immediately; budget cutoff returns only fully scored candidates. Record live CUDA-synchronized uncached timing (three repeats after warmup, same GPU exclusive, no parallel competing jobs, same batch size/chunk limits where possible). Report p50/p90, CPU/GPU and wall time, number of objects and K strata. Physical evaluation of C3/C4 optional, require separate cap tier; do not describe model-only timing or witness metrics as physical success.

## 6. Phase execution and tests

### P0 — Audit, freeze design, dataset provenance

Read sources and previous reports; confirm exact checkpoints, original training corpus, 2D/3D teacher versions, available cohorts, authorization, runtime paths. Produce provenance and split manifests; inspect only TRAIN/VAL labels. Verify old baseline parity and root-level labels. Determine exact resource allocation, preregister all decisions. Check whether 3D teacher uses `resolution` rather than 2D `status`, and actual meanings of EVALUATED/VERIFIED/UNKNOWN; do not blindly port status mapping. Audit original reference pose and end-to-end task contract. Gate: no training if positive corpus or release bundle unverifiable; no physical run without compatible teacher and explicit approval.

### P1 — Dataset and architecture

Implement loaders, root-weighted ordered supervision, root decision labels, scene masks and CR-cVAE. Unit tests for deduplication, equal root/assignment weights, label key joins, true-order only, STOP and legal masks, forced STOP, no legal move, padded objects, permutation equivariance, 2D fixed vs 3D attrs, all-invalid cases, reproducibility, nonzero gradients, posterior not accessed at inference, no private inputs. Tiny overfit fixtures for both domains and real TRAIN scenes; visualize reconstruction and multiple sampled repairs (2D grid and 3D shelf render or clearly labelled top-down geometry if renderer unavailable). No scene generation.

### P2 — Train and seal models

Train 3 seeds per domain, evaluate fixed VAL ELBO and integrated decision head, report capacity/learning curves/diversity/length/validity/known witness coverage. Generate DEV candidate pools across budgets, validate exact C1/C2 pool parity and count accounting. Freeze checkpoints, selected hyperparameters, inference budgets, all arms, seeds and selection rule before evaluation labels/teacher. Write `P2_TRAIN.json`, `P2_CHECKPOINTS.json`, `P2_DEV.md`, `P2_FREEZE.json` and figures. Gates: static legality 100%, no hidden true-K leakage, finite model outputs, release baseline parity. Weak learned performance is a valid outcome, not a reason to quietly replace the model.

### P3 — Locked evaluation predictions and candidate diagnostics

Evaluator prepares public rows only; run all primary arms C0/C1/C2, optionally C3/C4 on same cohort, with seed0. Seal prediction files, candidate-pool hashes, budgets, runtime records and prephysical decision manifest (`benchmark.seal` or equivalent). Commit seal before evaluator opens held-out labels or teacher calls. Include decision, ordered sequence or NOOP/ABSTAIN, model score type (p11 vs log likelihood), candidate counts, source seed, timing and reasons. Predictions must exist for every root, including crash/timeout/empty pool. Test allowlist/path separation (model process cannot read private labels, oracle witnesses or raw scenes containing them). Preserve original frozen predictions before any physical evaluation. Once sealed, never change candidates/thresholds/checkpoint/roster based on outcomes.

After seal, evaluator-only candidate diagnostics: exact known verified ordered-witness recall, canonical assignment recall, object-set recall, recall@raw draw budget, rank of best known witness, K distribution, same-set order recall. All are lower bounds because known witnesses are not exhaustive. When known witness appears in a pool but is not picked, label possible selection failure only when chosen failure is decided. No-witness is unresolved, not proof pool misses all solutions. Separate recall from valid physical success. Score-only curves on DEV and retrospective labels are not an independent physical test.

### P4 — Physical verification (sealed picks only)

Build a deduplicated manifest of selected `(domain, root, exact ordered sequence, teacher version/config hash)` from C0/C1/C2. Reuse caches **only** for exact same scene hash, teacher semantics, order and statuses, with no conflict; report cache vs new queries. If old outcome is UNKNOWN, retain as unresolved, no automatic retry. Query missing top-1 picks of each arm using existing 2D/3D physical harness; no new training labels. No adaptive top-k verification, no fallback, no per-arm retries, no hand-picked rescue after outcome. K0/NONE report gate outcomes and any committed repair separately; if feasible, verify unexpected repair picks to detect false NONE relative labels; mark unverified if cap limits. If teacher verifies full task through X terminal connector + Y target trajectory from q_ref, report contract success, not hardware success or actual execution duration. If trajectory witness replay available, replay a fixed small subset for evidence with same rules. Distinguish plan-generation time, teacher verification time, robot motion/path cost, and real execution time if available; don't label inference latency as end-to-end robot execution.

- Strict factor labels: verified positive/explicit certified infeasible only per actual teacher contract. UNKNOWN timeout/give-up is unresolved, not negative. Preserve both factors. Logical Z=1 iff X=Y=1; Z=0 if either factor soundly 0, otherwise UNKNOWN. Also reproduce historical strict order of resolution and operational convention (UNKNOWN with legacy 0) as separate sensitivity. Never map absent labels to negative. For K1–K3, NOOP/ABSTAIN count as unsuccessful relative to cohort's known task infeasibility/repair; if original feasibility is unverified, report separately. For K0/NONE use known benchmark-relative decisions (not mathematical impossibility). Report UNKNOWN by factor, root and arm; operational success on all roots plus bounds [verified successes/N,(verified successes+UNKNOWN)/N].
- Query caps: allocate complete paired roots first, primary C0/C1/C2; if cap binds, choose roots by predeclared hash within domain/K strata **before outcomes** and preserve all roots in denominator with unqueried status. Do not evaluate C3/C4 physically until primary paired coverage is complete and owner-authorized budget remains. Stop dispatch with CPU headroom for in-flight work; hard cap aggregate worker+child CPU (not wall time), terminate safely and preserve completed jobs. No unbounded generator/teacher invocations.

### P5 — Results, paper-ready ablation, conclusion

For each domain and K stratum report exact counts N, verified success, decided fail X/Y, unresolved, NOOP/ABSTAIN, all-root success (verified/N), strict decided-only success, UNKNOWN rate, paired decided root coverage, ITT bounds. Paired family-cluster bootstrap (4000 draws seed0) for difference of binary successes among both-decided roots and operational all-root verified-success difference; report wins/losses and confidence intervals. Small strata descriptive only; no pooling 2D+3D as independent identical tasks. Primary contrasts C2−C1 (same generator/pool; scorer + gate distinction) and C0−C2 (same scorer; proposal/construction distinction). Also C0−C1 overall system. Pre-register Holm adjustment across primary domain-specific hypotheses (4 contrasts: 2 per domain); show unadjusted intervals and adjusted p-values or explicitly conservative multiplicity treatment. Paired cluster uncertainty must reflect family membership; don't pretend multiple sequences or seeds are independent scenes. Report complete-case sensitivity selection bias, conservative bounds on paired gains by assigning unresolved 0/1 (per-root best/worst case), and K0/NONE guards. Raw p11 vs generative likelihood scales incomparable; use physical outcomes, not score differences.

Declare improvement only if primary paired lower bound >0 with multiplicity-aware evidence, UNKNOWN ≤20% in both arms and coverage adequate; report point gain ≥5 pp separately (practical importance, not required to detect smaller effects). If CI crosses zero, no established improvement (not equivalence); if UNKNOWN >20%, label inconclusive even if descriptive rates look good. If C0 loses, report it. No claim of superiority from selected successful examples, no claim two models universally needed. If C1 is competitive, acknowledge simpler method; if C2 improves C1, learned scorer adds utility but training supervision differs; if C0 improves C2, factorized construction adds utility under measured budget; if only natural-budget C0 wins but count/time matched does not, attribute to search budget rather than representation. If C1 gate drives differences, state separately. No K>3, attribution or causal-minimality claims.

## 7. Proposed resource envelope (owner must authorize)

| Item | Proposed cap |
|---|---:|
| New scene generation / training teacher queries | 0 / 0 |
| New physical evaluation queries, 2D | 450 |
| New physical evaluation queries, 3D | 450 |
| Teacher aggregate CPU-hours | 24 total (initial allocation 8 2D / 16 3D) |
| GPU training | 4 GPU-hours total (six fits + smoke) |
| GPU inference/analysis | 3 GPU-hours total |
| Workers | start 8–16, max 16 unless owner/host confirms more; leave ≥4 cores and respect concurrent K45 workload |
| New local storage | 15 GiB |

These are proposals, not inherited authorizations. Need separately approved host (existing 2D gvlab2, existing actual 3D host/runtime from audit; do not assume same machine). Stage P0–P3 can run with existing authorized read/train compute only; P4 requires approval. 450 queries/domain covers ≤150 roots × three top1s worst-case excluding safeguards and cache; if safeguard verification necessary reserve before sealing or reduce roster. 3D query cost may be much larger: profile a small authorized batch of sealed primary jobs, then enforce headroom and cap. No runtime promises. If resources tight, prioritize primary three arms, seed0 physical, same roots, cache reuse; reduce optional controls first. Record stop reasons and completed denominators. No borrowing other experiment's compute caps.

## 8. Minimal implementation layout

```
approach_b_final/complete_repair_cvae/
  plan.md                  # immutable supplied contract, amendments separately
  starting_prompt.md
  README.md                # exact commands, environment, reproduction
  data.py                  # public encoder inputs, TRAIN-only supervision, manifests
  model.py                 # CR-cVAE, integrated gate, masked decoding and likelihood
  train.py                 # six bounded fits, checkpoint selection
  infer.py                 # C0/C1/C2, count/wall controls, seal-ready records
  evaluate_cr.py           # evaluator only, jobs, cache/status mapping, statistics
  viz.py                   # real-scene overlays, training curves and ablation plots
  tests/test_cr.py
  reports/                 # P0–P5 reports, figures, aggregate and seal manifests
```

Keep files readable, type/docstrings for nontrivial functions, avoid unnecessary framework abstractions; prefer ≤400 lines/file if practical, split only by cohesive responsibility. No notebook-only logic. Use existing modules through adapters, never edit frozen sources. Smoke tests and all relevant historical tests pass; record actual commands and counts rather than inventing. Use private checkpoint paths with hashes. Save per-domain visualizations: P0 positive repair/order counts and coverage; P1 2D grids and real 3D renders where possible showing objects and destinations in sequence; P2 learning curves and sample diversity; P3 candidate overlap and length distributions; P4 paired rescue/harm/unknown examples with physical witness status; P5 task success by K, natural and matched budgets, latency/parameters. Any schematic clearly labelled not an executed result. Include examples of each arm succeeding/failing, chosen by predetermined hash/category, not only ours successes.

## 9. Final deliverable checklist

- `P5_FINAL_DECISION.md` with exact commit, completed stages, all deviations, model/data hashes, teacher CPU/GPU resources, cohort provenance, all results and caveats, no unqualified claim.
- Paper-ready table (2D and 3D each): C0/C1/C2, K1/K2/K3 and pooled success, unresolved, time, calls during inference, params; secondary matched counts and coverage. Include denominator and paired CIs, separate training time vs inference.
- Direct answers to RQ1: (i) does separate X/Y reranking help complete generative proposals, (ii) does factorized cVAE proposal + enumeration help with the same scorer, (iii) is extra complexity worth cost, (iv) is the conclusion robust by domain/K, (v) which failures are recall/order/selection/gate vs unknown. No demand that results favor ours.
- P0–P5 commits pushed only to isolated branch; nothing merged; report status of the parallel K45 worktree only if necessary to avoid resource collision. No background work claimed if not running. If blocked, report exact missing artifact/approval and completed subset.
