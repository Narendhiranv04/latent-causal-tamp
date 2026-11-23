# RSS 2027 — Original-Root cVAE + Set-MCTS + X/Y: K<3 Research and Implementation Plan

**Version:** 1.0 | **Date:** 2026-11-23 | **Status:** Proposed prospective MCTS study; no MCTS measurements claimed  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Recommended implementation parent:** `naren/k3-postablation-validation` at **`e9fa587c3b9dd850f1fbbc454b20e4e00a35c4eb`** (verify its SHA immediately before branching; do not silently switch parents).  
**Suggested isolated branch:** `naren/rss27-mcts-sets-klt3`  
**Scope interpretation:** `K<3` means **K1 and K2 corrective-relocation tasks**. K0 is used only to evaluate the unchanged NOOP decision; NONE is used for unchanged abstention. **K3 is out of the primary experiment**, but may be added as a separately registered follow-up once the K1–K2 gates are met. Do **not** use the private/teacher-provided K to alter the planner's choices. The public planner receives only an allowed **maximum horizon of 2**, and the evaluation harness stratifies results afterward.

> **One-sentence scientific question:** With the same frozen original-scene destination proposals and the same frozen order-dependent X/Y predictions, can **MCTS over unordered corrective assignments** recover the successful K1–K2 repair decisions of exhaustive enumeration using substantially fewer unique evaluated ordered sequences and/or less planning time than strong search alternatives?

## 0. Non-negotiable scientific and engineering rules

1. **Responsibilities remain separate:** cVAE proposes candidate destinations **for each eligible object**; MCTS chooses **which object–destination pairs belong to an unordered assignment**; X/Y evaluates **complete physical execution orders** of that assignment and selects the best. Do not train a joint-assignment cVAE, object-selection neural policy, transition model, or learned MCTS value head in this phase.
2. **Original-root-only model inputs:** cVAE is queried once in a batch for the original scene `S0` and task; every X/Y call receives `S0`, its reference robot context, and the **complete ordered candidate**. **Never** feed the cVAE or X/Y a hypothetically edited scene, and never re-query them after physical execution begins.
3. **Prediction-only planning:** 0 physical teacher/IK/motion-planner calls inside MCTS or its action filters. Existing declared **static cell-grammar legality** (movable/non-target, supported cells, initially empty destination, distinct objects/destinations, goal-cell exclusion) is permitted and necessary for parity. Never describe static grammar as physical feasibility.
4. **Frozen models:** V3.4 `scratch_all` TaskCVAE s0 and D-expanded X/Y s0 initially, with hashes from `approach_b_final/reports/final_v34/BUNDLE_MANIFEST.json` and `config/final_protocol.yaml`. No model fitting or hidden threshold changes. Keep scorer D/E/DIRECT extensions out of this first experiment.
5. **One committed answer:** `REPAIR` (one ordered sequence), `NOOP`, or `ABSTAIN`, no physical retries. Independently evaluate after the output is sealed. UNKNOWN is never relabelled as false.
6. **No leakage:** Learner inputs are **public views only**; no `K_legacy`, teacher X/Y, masks, certificate, witness, ground-truth blockers, oracle outcomes or historical TEST results may enter action generation, search, tuning, or termination. The evaluator may stratify by private K **after** predictions are frozen.
7. **Research honesty:** Do not claim that MCTS has learned a transferable policy or proved causal dependencies. MCTS accumulates per-root visit statistics during inference; these do not train the cVAE or X/Y. This is a **search-efficiency** study, not a new long-horizon feasibility model.
8. **Historical protection:** Preserve all existing branches, checkpoints, teachers, caches, reports and sealed outputs. Work only on the new branch and new output directories. Do not merge.

## 1. Source-and-commit audit: what already exists

Before changing code, reproduce this provenance ledger from actual Git history and file contents; record mismatches instead of silently changing it.

| Area | Verified branch head | Required source/report | Finding relevant to this study |
|---|---|---|---|
| Frozen independent benchmark | `naren/approach-b-v3-4-final-benchmark` at `c72eb1ef759a6817d557f06250f644a217233475` | `approach_b_final/reports/final_v34/V34_FINAL_REPORT.md`, `config/final_protocol.yaml`, `benchmark.py` | Frozen s0 TaskCVAE+coupled D, S1 64-draw top-4, all K1–K3 orders, `noop_gate=.5`, `eta=.3`, `alpha=beta=gamma=0`. Fresh 2D K1–K3 51.8% on 394 roots; 3D 76.6% on 239. This cohort is **not available for adaptive MCTS tuning**. |
| K≤3 registered ablations | `naren/k3-ablation-gvlab2-20261120` at `4aee798929968c6b34d911adcbb622d72bb69fa9` | `approach_b_final/ablations_k3/reports/FINAL_REPORT.md` | VAL 2D FULL 57.1%, 3D FULL 78.2% (K1–K3); frozen identical candidate pools for scorer arms. No-task cVAE difference small; Uniform4 and M1 much worse; order-invariant and DIRECT weaker. Historical TEST was exposed. |
| Post-ablation validation | **Recommended base** `naren/k3-postablation-validation` at `e9fa587c3b9dd850f1fbbc454b20e4e00a35c4eb` | `approach_b_final/validation_k3/reports/VALIDATION_REPORT.md`, `TASK_RETARGET_REPORT.md`, `COUPLING_F5_REPORT.md` | Both X/Y are useful for selection; F5 learned coupling has no robust task-success advantage. VAL label-blind random-scoring budget curve: 2D B=1/16/256/4096/all -> 9.7/28.1/38.7/50.1/57.1%; 3D 20.0/55.5/76.8/78.2/78.2%. These are K1–K3, **not** K1–K2 results. Task/no-task gap not significant. |
| Previous frozen K>3 attempt | `naren/kgt3-exec-composition` at `171eb65cc42a234892a0fd8cba8969823b4426ce` | `recursive_kgt3/reports/p6/P6A_METHOD_AND_DEV_REPORT.md`, `p7ar/P7AR_DECISION.md` | **Do not recreate this failure mode:** frozen 3-action windows on edited scenes yielded order-progress AUROC ~.42; P7A-R all arms 0/24 static-valid committed plans, no physical tests. That was a different long-horizon experiment; not evidence about proposed K1–K2 MCTS. |
| Adapted DISCO-grid MCTS | `naren/disco-grid-final` at `56b71743e932efe6627307d8346098bda0985de8` | `baselines/disco_grid/mcts.py`, `reports/DISCO_GRID_FINAL_REPORT.md`, `reports/validation_v2/FINAL_DECISION.md` | Already contains **training-time, stateful, physical-simulation MCTS**, **not reusable as-is** for this original-root, teacher-free, unordered-set search. Only reuse rigorously understood algorithmic ideas (UCB, widening, visits) without importing environment/teacher dependencies. Historical results are not an independent fair head-to-head with this new MCTS. |
| Analytical alternatives | `naren/analytical-baselines-k3-finalize` at `7ae0e54b7d843780bf8880f9e8375c1621316975` | `baselines/analytical/reports/ANALYTICAL_BASELINES_PRE_BENCHMARK_REPORT.md` | E-M4M, MO-SeGMan, MS-MCTS were run on VAL in an **oracle-assisted online physical-search regime**. Useful context, **not a matched predictor-only MCTS baseline**. |
| Physical order mechanism audit | `naren/order-dependency-audit` at `8e1c1a247e9c0d6af4925e30eb8436e8f126489a` | `audits/order_dependency_final/AUDIT_REPORT.md` | Physical order dependence is not universally attributable to handoffs; existing evidence is often ambiguous. Do not claim MCTS discovered physical causes from p11 alone. |

**Read implementation, not only summaries:** `approach_b_final/{benchmark.py,exhaustive.py,construct.py,search.py,placement.py,xy.py,contracts.py,evaluate.py}`; post-ablation `ablations_k3/{run.py,analyze.py,test_k3.py}` and `validation_k3/{budget.py,p0_audit.py,VALIDATION_REPORT.md}`. Read relevant commits and compare the base with V3.4; record actual parent, models and public-view semantics. Repository contains other projects; “audit entire history” means **trace all relevant lineages**, not pretend to review every unrelated commit in the huge repo.

### 1.1 What the current production logic actually does

- Frozen TaskCVAE conditions on original scene features, **queried object**, target/goal and robot reference context. It does **not** select blocker identities. `search.Sampler.propose_many(root, root.cells0, root.movable, M, gen)` is one batched original-root proposal pass.
- The final benchmark uses S1, 64 Monte Carlo draws, a top-6 proposal list whose **top-4 prefix** defines the candidate pool. This means four **destinations per eligible object**, not four globally selected actions.
- Existing `construct.assignments(D,k)` enumerates unordered valid assignments; `exhaustive.stream(...)` enumerates their **execution-order permutations**. `search.Scorer.score(root, seqs)` returns p11, pY and pX from original-root features. Reuse the exact legality and scoring interfaces.
- `exhaustive.Selectors` and `XY.choose` establish the final decision semantics and deterministic ties. Final rule: `noop_gate=0.5`, `eta=0.3`, `alpha=beta=gamma=0`. Do not replace or improvise them.
- Current K1–K3 full exhaustive scoring is exact within the sampled candidate pool; at **the same pool and predictor**, a budget-limited MCTS cannot beat exhaustive on **predicted optimal score**, though its independently verified outcome may differ through selection errors. MCTS has to earn its place through fewer scorer evaluations, lower wall time, or improved search under a later broader proposal regime.

## 2. Problem definition for this first study

- Original robot task: manipulate target T toward goal g after 1–2 corrective object relocations.
- Input to all methods: public original root `S0`, `q_ref`/declared context, task T/g; a frozen per-object proposal map `D={o:[d_1,...,d_M]}` from identical generator draws and seeds.
- Atomic candidate action: `a=(o,d)`, with o movable non-target, d in the frozen original-root legal supported and originally empty cells, d≠goal.
- Assignment `A`: unordered set of such actions, each object at most once, all destinations distinct, `1 <= |A| <= 2`. Represent as immutable sorted tuple of `(object_index, dest_cell)`.
- Ordered candidate `r`: a permutation of `A`. Distinct orders share a hypothetical endpoint Y but may have different complete-sequence X outcomes. **MCTS's insertion order is NOT the physical execution order**.
- Scorer for any candidate `r`: `p11(r)=P(Y_end=1)*P(X_r=1 | Y_end=1)` from frozen D; never run it on a synthetic intermediate scene. For assignment A:
  
  `best(A) = argmin_{r in permutations(A), p11(r)>=eta} (-log(p11(r)), len(r), displacement(r), signature(r))`, with the existing exact tie rule. Retain all outcomes for diagnostics. **Search reward** can use `max_r p11(r)` (continuous guidance independent of eta), while final commitment uses the exact gated selector. This distinction must be declared, not hidden.
- Open-loop decision: one REPAIR/NOOP/ABSTAIN; *no* simulation/IK/checking at planning time. Evaluation uses the unchanged physical teacher separately on sealed selected repairs.

### Important semantics: K<3

Use public `K_max=2` for **every evaluated root**; never use hidden true K in the planner. The evaluator reports K1 and K2 primary results, plus K0/NONE safeguards. With the cap at two, K3 roots cannot be used to claim full success; they should be excluded from the primary diagnostic cohort through an evaluator-side declared cohort manifest, without exposing that category to the planner. If a K3 appendix is added later, preregister a separate K_max=3 experiment.

## 3. MCTS formulation: exact search role, nonphysical search

### 3.1 Node and edge

A node is an unordered action assignment A. The root is empty. An edge **adds one new object–destination pair** with distinct object/destination and declared static legality. No edge executes a robot action; no robot-state transition is predicted.

- Canonical state key: sorted tuple of integer pairs `(o,d)`. Cache all terminal ordered scores by `(root_id, ordered_sequence)` and assignment best by `(root_id, canonical_A)`.
- To avoid duplicate sets, implement **one documented canonical expansion order** or a carefully tested transposition-aware graph. If canonical-only, monitor artificial index bias with multiple hash-seeded action-order rotations; **do not interpret the insertion path as an execution dependency**.
- Reuse `construct.assignments` as the exhaustive oracle. Unit-test that every legal K1/K2 assignment appears exactly once in the canonical state space and every scored order is an exact permutation of it.
- Explicit `STOP` is a **search action** that terminates the current *set* and evaluates all its execution orders. STOP must be available at depth 1 and 2. At depth 2, no further ADD is legal. Empty NOOP is handled by the frozen gate separately.
- A low predicted score for a K1 STOP does **not** prune the possibility that adding another object yields a useful K2 repair. A dependency can require a temporarily unhelpful action.

### 3.2 One MCTS iteration

1. **Select:** Starting from empty set, choose among developed children using UCT (`Q + c sqrt(log(N_parent+1)/(N_child+1))`) or a preregistered PUCT-style variant. `Q` is the average terminal reward backed up from explored candidate assignments, **not** a learned new network.
2. **Expand:** If widening/availability permits, add one new legal `(o,d)` candidate from fixed D, or select STOP. With optional progressive widening, `|children(A)| <= floor(k_pw * max(N(A),1)^alpha_pw)` for declared `k_pw,alpha_pw`. In this finite K2 case, **ordinary UCT may be as strong or simpler**; compare both rather than assuming PW matters.
3. **Evaluate a completed assignment:** On STOP (or required depth-2 terminal), generate **all 1! or 2! orders**, call the frozen X/Y scorer **from original root**, cache scores, take the maximum p11 for search guidance and retain best admissible order for final selection. Never call Y on edited scenes separately or feed teacher outcomes into MCTS.
4. **Back up:** Propagate terminal reward to visited MCTS search nodes. A K1 low score is not an upper bound on a K2 continuation. No permanent model weight update; no claim of RL learning across roots.
5. **Repeat** until a fixed budget is exhausted. Count actual unique *ordered scorer evaluations*, **including all permutations and the no-op query**, not merely MCTS iterations. Cache hits are separate counters. Enforce budget before a STOP evaluation; if a set requires two order scores but only one scorer token remains, do not partially score the set. Report unused final token.
6. **Select once at the end:** From **all fully scored** complete assignments and the cached no-op, use precisely the frozen `XY.choose`/`exhaustive.Selectors` convention: no-op gate, admission eta, tie-breaking, ABSTAIN if none admitted. **Return best evaluated plan**, not simply the most-visited child. Never perform physical retries.

**Search-reward nuance:** A predicted p11 score is a *terminal predictor*, not a true physical reward. UCT does not certify feasibility, and maximizing predicted score can exploit scorer errors. Experiments must separately report the predicted optimum and independently verified selected-repair success.

### 3.3 Proposals and priors

Primary **identical-candidate-pool** condition: freeze D with existing S1 64-draw top-4 per object, same per-root CUDA RNG. Don't retrain the cVAE, don't change top-M, and don't run it on intermediate scenes.

- UCT uniform over legal set-expansion edges is the **pure MCTS search** reference.
- A rank/frequency-informed PUCT prior is optional only if the frozen proposal API actually exposes a meaningful unnormalized/normalized destination score; **inspect before implementation**. Current output is primarily a ranked list; if actual probabilities are not retained, use preregistered rank weights and label this a **rank prior**, not a calibrated probability.
- An object-uniform prior is fair: the cVAE learns `p(d|o,S0,T,g)`, **not** `P(o is necessary)`. Never assign object-necessity probabilities without a trained model and ablation.
- Optional stronger-proposal experiment (after primary): top-6 rather than top-4 per object; **rerun every search baseline on the same enlarged pool**. This is a distinct experiment, not an explanation of an MCTS gain on unchanged D.
- Analytical band-stratified proposals form a separate ablation, **not** the control for search-efficiency alone; hold the search algorithm fixed to test cVAE value.

### 3.4 Termination and budgets

- **Local STOP**: evaluate the current set as a candidate full correction; do not stop global search automatically.
- **Depth cap**: K_max=2, chosen publicly, identical across roots and algorithms.
- **Global hard cap**: unique ordered X/Y score calls `B_score` and optional secondary wall-time limit. Primary compare budgets **`B_score ∈ {16, 64, 256, 1024}`** plus exhaustive, with `p_noop` charged identically. These are experiment proposals; freeze after a no-label resource preflight. If 1024 exceeds the full pool on a root, clamp and report exact reachability.
- **No early stopping from p11 >= eta:** eta is admission, not evidence of actual success. Optional early-stop is a **separate ablation** with a preregistered threshold, not the primary.
- **Score accounting**: unique ordered repairs (primary), number of evaluated unordered assignments, model batches, raw cVAE draws, GPU wall time, CPU/wall total, search iterations, expansions, cache hits, max RAM/VRAM, no-op score. Distinguish *model forward batches* and *number of scored sequences*.
- **Determinism**: root-hash × search seed controls MCTS PRNG; model proposal seed and CUDA RNG remain frozen. Run MCTS seeds 0,1,2 for stability; run control seeds 0,1,2 for stochastic controls where applicable.

### 3.5 Minimal algorithm (pseudocode)

```text
INPUT: public original root R, frozen TaskCVAE, frozen XY, B_score, Kmax=2
D <- frozen_cvae_proposals(R.S0, all eligible objects, M=4)   # once
p0 <- XY(R.S0, empty_plan)                                      # cache
T <- SearchTree(root = empty unordered assignment)
cache <- {empty: p0}; scored_plans <- []
while unique_ordered_XY_queries < B_score and expandable(T):
    path <- UCT_or_PUCT_select(T)
    node <- add_legal_action_or_STOP(path, D)
    if node is completed_assignment:
        orders <- permutations(node.assignment)                  # k! <= 2
        if budget_allows_all_uncached(orders):
            outcomes <- XY(R.S0, orders)                         # original root only
            cache <- cache ∪ outcomes
            backup(path, max(outcomes.p11))                      # terminal predictor
            scored_plans <- scored_plans ∪ outcomes
        else:
            mark_budget_blocked(node)
    else:
        continue_tree_descent_without_intermediate_model_call()
return frozen_XY_choose([empty] + scored_plans, frozen_rule)
```

Implementation must make the loop well-defined if a selected branch already has a cached terminal reward: update visitation according to the declared search variant without counting phantom new model evaluations; if all reachable distinct assignments are scored, stop as EXHAUSTED. Add an iteration/selection guard so repeated visits cannot create an infinite loop after scorer budget stalls.

## 4. Experiments and controls (2D primary)

### 4.1 Cohort and splits

- **Pilot**: synthetic hand-verifiable fixtures, then deterministic small subset of historical **VAL** public roots. Only public fields are passed to the planner; private K stratifies evaluation afterward. Include K0, K1, K2, NONE strata for no-op/abstention. A development-only inner subset may be used to choose MCTS hyperparameters.
- **VAL primary**: all eligible existing 2D VAL K1 and K2 task roots (historically 120 each in the 751-root split; verify actual counts), plus K0 and NONE for safeguard reporting. Use disjoint development/evaluation groups when selecting hyperparameters. Prior VAL has been examined extensively; call these **development/validation**, not pristine independent evidence.
- **Historical TEST**: do **not** use for configuration or tuning. It is already development-exposed; if used eventually, state this and treat results as exploratory.
- **V3.4 fresh cohort**: was frozen for an earlier model and is now known through its aggregate metrics. Preserve it; **no reuse as a new untouched MCTS confirmation set without an explicitly documented protocol decision**.
- **Independent confirmation after lock**: prospectively generate a new layout/lineage-disjoint K0/K1/K2/NONE 2D cohort, seal root selection before inference, and keep model-selection decisions frozen. If this requires new generator/teacher capacity, preflight and report cap before generating. Template-disjointness must be stated honestly; geometry/lineage-disjointness is not template-disjointness.

### 4.2 Matched search arms

All arms receive identical D, frozen X/Y scorer, rule, static grammar and K_max. The only experimental variable is the **set selection/search method**.

| Arm | Selection mechanism | Why necessary |
|---|---|---|
| `EXACT_K2` | Exhaustively enumerate all legal K1/K2 assignments; score every valid order | Predicted-score upper bound within D; a meaningful ceiling, not intended to meet low budgets |
| `RAND_SET` | Seeded uniform sampling of unique unordered complete assignments, with all order permutations scored | Controls for mere search budget |
| `BEAM_SET` | Simple bounded beam of unordered assignments, same terminal scoring and hard budget | Strong simpler deterministic/stochastic comparator; no MCTS-specific credit without beating it |
| `UCT_SET` | Monte Carlo set search using uniform object/destination expansion priors | Tests whether UCT backup/exploration offers value |
| `PW_UCT_SET` | Same, with preregistered progressive widening | Tests whether widening actually helps in this *finite shallow* K2 space |
| `PUCT_RANK` (secondary) | Uses cVAE rank weights for destination prioritization while object prior remains uniform | Tests whether cVAE-informed search policy adds benefit beyond the fixed pool |

For fair `BEAM_SET`, specify whether it ranks incomplete sets by their hypothetical STOP score; if so, **do not prune solely because immediate Y is poor** without a diversification/fairness arm. Record that this is a baseline weakness if relevant. Score all permutations and charge the same B_score.

**Separate proposal ablation (later only):** `task-cVAE` versus `NoTask` versus `band-stratified` with UCT fixed. The prior K3 post-validation demonstrated small, nonsignificant direct task-context effect, and P1 showed band sampler hit@4 can exceed cVAE. Do not attribute search gains to task conditioning unless directly tested.

### 4.3 Metrics and calculations

**Primary:** *independently verified top-1 repair success on K1 and K2 roots*, individually and pooled, as a function of unique complete ordered sequences scored. Report correct NOOP for K0 and correct ABSTAIN for NONE separately; wrong unnecessary corrections and false abstention must be visible.

**Secondary:** predicted-score regret versus exact within-D optimum, agreement with exact chosen sequence, true physical paired win/loss roots, 95% root-family/lineage-cluster bootstrap (>=2,000 resamples), success versus GPU/CPU wall time, p50/p90/p99 time, candidates/assignment coverage, scorer calls, batches, tree visits, expansion distribution, action-set size, entropy of chosen objects, and reason for termination.

**Diagnostics:** coverage of *known physically verified* successful assignments in D (lower bound only); coverage of verified successes among attempted sets; conditional selection success when a verified success is in scored pool (never infer unknowns are failures); failure type X or Y; number of high-p11 false positives among selected plans. Aggregate a matched *root-level* outcome for each arm; ensure no cross-root paired mismatch.

**Fairness constraint:** exhaustive can only be *matched* at its full score cost; do not compare MCTS B=256 with exhaustive full and claim it is better on predicted optimum. At equal scorer budgets compare RAND and BEAM; display EXACT as an asymptotic reference.

### 4.4 Scientific gates

- **G0 integrity:** all frozen checkpoints/manifest hashes match; old `benchmark.predict`, `exhaustive`, and selected historical regression tests reproduce established outputs; no private fields enter planner.
- **G1 mathematical parity:** on synthetic known pools, exact search == trusted exhaustive result with identical no-op, eta, tie, X/Y order; every assignment enumerated once; no illegal moves; no hypothetical model calls.
- **G2 MCTS operation:** MCTS terminates within unique-score and iteration caps, yields deterministic results per seed, shows *actual* nonuniform search allocation, and on at least one crafted two-action dependency fixture discovers a good pair even when every singleton STOP is poor.
- **G3 predictive efficiency:** report paired agreement/regret against exhaustive and matched RAND/BEAM over budget curves. A practical success claim requires both comparable verified success and materially fewer scored sequences/time; **do not manufacture a numerical success gate after observing results**. Before teacher verification register, for example, a **5 percentage-point noninferiority margin** and a **>=75% reduction in median scored ordered sequences**, with confidence interval uncertainty. These are **proposed criteria**, subject to preregistration, not results.
- **G4 physical evidence:** selected predictions sealed before verification; single unchanged teacher per unique unseen pair, UNKNOWN preserved; root-paired bootstrap and separate K1/K2/K0/NONE. If matched search algorithms are indistinguishable or MCTS is slower, report **NULL/NEGATIVE** and recommend the simpler method.
- **G5 held-out check:** any independent confirmation cohort is generated after final protocol lock; no iterating designs on its labels. Negative results and caveats remain in final report.

**Expected possibility:** For K1/K2, the full pool is small enough that `EXACT_K2` may be both easy and superior. MCTS could be unnecessary. This is a *valid scientifically useful outcome*, and a warning against overclaiming scaling from a shallow experiment.

## 5. Concrete implementation milestones

### P0 — History, data, model and protocol freeze (read-only)

- Verify branch heads and relevant commit ancestry; select exact base; hash original scripts/checkpoints/manifest; run existing smoke tests; list all read-only source dependencies.
- Write `reports/P0_SOURCE_AUDIT.md`, `reports/P0_FROZEN_PROTOCOL.json` (root IDs/splits, bundle/model SHA, sampler seed, evaluator semantics, host/software versions), `reports/P0_GAPS.md` (what cannot be accessed), `reports/P0_TESTS.json`.
- Confirm physical teacher is not imported by planner. Confirm K1/K2 eval cohort, index masks and layouts are evaluator-only. Confirm source data paths exist. If any required pretrained files are missing, stop with a concrete inventory—not a fictitious parity claim.

### P1 — Minimal MCTS + exhaustive parity, no new physical calls

Add minimally to `approach_b_final/mcts_sets/`:

```
mcts_sets/
  plan.md               # this document, copied unchanged
  search_sets.py         # canonical assignment tree, UCT/PW, counters, scorer cache
  run.py                 # load frozen bundle, public-only inference, seal/validate
  analyze.py             # paired search-budget and success analysis
  tests/test_sets.py     # exact microfixtures, determinism, illegal actions, gating
  reports/               # manifests, JSON outputs, plots (not model weights)
```

Reuse **existing** proposal, evaluator and benchmark code rather than copying it; new Python modules should generally remain <=250–350 lines each, with tests separate. Never make a new `env.py`, physical teacher, IK checker, geometric reachability code, second cVAE or second X/Y model.

Test STOP semantics, empty/unreachable pool, object/dest conflicts, set order invariance, permutation-specific X, tie stability, nonmonotonic K1→K2 reward, exact parity, counter monotonicity, root-hash determinism, hard scorer caps, all-action-exhausted stop, re-entrance without rescoring, CPU fallback, privacy schema and no runtime import of teacher modules. Test visualization on synthetic and a few real *public* roots.

### P2 — Paired teacher-free pilot and preregistration

- Build identical proposal-pool hashes per root; run `EXACT_K2`, `RAND_SET`, `BEAM_SET`, `UCT_SET`, `PW_UCT_SET` at B=16/64/256/1024 on a VAL pilot without reading physical outcomes.
- Generate one figure per selected root: 2D scene with object IDs, cVAE proposed destinations, MCTS expanded unordered sets (visits/mean reward), and selected **energy-ranked** order; indicate all displayed probabilities are predictions, not certificates. Also generate success-score regret and candidate-budget/time curves.
- Assess implementation correctness and runtime without selecting the most favorable roots. Tune only c, k_pw and alpha_pw on a predeclared DEV-only subset via *predicted-score* agreement/regret and time, not teacher labels. Freeze config before any physical calls on the paired evaluation subset.
- Save `reports/P2_PREREG.md`, `reports/P2_POOL_HASHES.json`, `reports/P2_PREDICTIVE_PILOT.md`, deterministic `predictions.jsonl` and seal hashes.

### P3 — Physical verification on development/VAL, within registered resource envelope

- Before new physics, produce **exact unique teacher-query manifest** across locked primary search arms at fixed primary budgets; dedup with existing immutable cache. Count X and Y queries separately, expected maximum CPU time, host/worker allocation, and explicit statuses.
- **Safety/resource envelope for this plan:** no more than **1,200 new 2D complete-sequence physical teacher queries** total for this MCTS study without separate owner approval; no more than **24 cumulative physical-worker CPU-hours** without separate owner approval; no 3D new physical queries in this phase. These are conservative planning limits, not implied guaranteed available resources; honor more restrictive host limits. If the required set exceeds them, predeclare root-hash subset and report a partial-but-valid study, not silently add queries.
- Use only authorized idle compute; do not interfere with other workers or change machine environment. Seal predictions before querying. Reuse historical cached physical outcomes only if teacher semantics and lineage are identical. UNKNOWN/WORKER_ERROR abort and remain distinct; never change budget or retry to force a positive.
- Analyze real top-1 success on K1/K2, correct K0/NONE, paired differences, latency, scorer budgets, failure X/Y, diversity, and strongest control. Record all misses and resource usage.

### P4 — Final K<3 scientific decision

Classify outcomes: **MCTS useful**, **same performance but slower**, **worse than beam/random**, or **inconclusive due to evidence or resource limits**. For every claim state which controlled experiment supports it. If positive, propose independent confirmation with newly frozen root cohort; if not, keep exhaustive for K<3 and treat MCTS only as a possible later scaling idea. No changes to released K≤3 method.

### P5 — Optional follow-up, NOT automatically part of K<3

Only after K1–K2 gate and a new preregistration: increase `K_max` to **3** (still within X/Y's training horizon). Then consider whether MCTS has enough advantage at higher branching and whether performance on 2D/3D differs. **K>3 requires a separate validated scoring/composition method and possibly a changed physical protocol. This plan makes no K>3 success claim.**

## 6. Reporting and visualization deliverables

Required reports: `P0_SOURCE_AUDIT`, `P1_PARITY_TESTS`, `P2_PREDICTIVE_PILOT`, `P2_PREREG`, `P3_PHYSICAL_VAL` if authorized/achievable, `P4_FINAL_DECISION`, a CSV/JSON of per-root actions, counts, p11/X/Y, decisions, seeds, timing, physical outcomes and exact source/hash lineage; figures of root scenes, set trees, order permutations, budget–regret and budget–success curves (mark model-only versus physically verified). Provide a sample run transcript and reproducible commands.

The final narrative must answer: Did MCTS recover the correct **unordered action sets**? Was its final **order chosen by X/Y rather than insertion order**? Did it use fewer unique scorer evaluations than full enumeration? Was it faster end-to-end? Did it improve **verified task success**, or merely optimize the frozen predictor? Which precise changes, if any, are justified before considering K3?

## 7. What *not* to claim

- No one has shown a new MCTS run in this proposed branch yet. All existing numbers in §1 come from **other recorded experiments**.
- MCTS is not a neural model and not permanently trained in this phase.
- It does not search robot joint-space and cannot establish physical feasibility without the independent verifier.
- The best p11 assignment need not be the physically best repair. `Y` for two orders of the same endpoint is shared by definition.
- The superiority of cVAE placement over band-stratified analytical proposals, the necessity of explicit task conditioning, and the benefit of learned F5 coupling remain **distinct, not established by this study**.
- K<3 MCTS success would justify a **search-efficiency claim at K1/K2**, not horizon extrapolation, novelty of MCTS itself or causal discovery.

## 8. Go/no-go summary for the coding agent

**Go:** Implement a small **inference-time, original-root-only, unordered-set MCTS** using frozen cVAE and X/Y; complete mock/parity tests and budgeted VAL search comparisons; independently physically verify locked selections within the registered cap and authorized host permissions.

**Do not go:** Reuse DISCO's stateful physical MCTS as-is, train new networks, change action grammar, call models on edited scenes, feed K/teacher labels to the planner, run K>3, touch protected cohorts, overrun teacher/compute caps, or advertise model-predicted outcomes as verified repair success.
