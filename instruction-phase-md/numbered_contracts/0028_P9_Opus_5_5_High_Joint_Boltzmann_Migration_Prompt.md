# P9 — Opus 5.5 High execution handoff: joint Boltzmann likelihood migration

**Intended repository path:** `instruction-phase-md/0028_P9_Opus_5_5_High_Joint_Boltzmann_Migration_Prompt.md`  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Known last P8 commit:** `f9a6de0695d83699a2115d4898e5c78063852073`  
**Agent:** Claude Opus 5.5 High, Antigravity  
**Authorized scope:** P9-L0, P9-L1 and *strictly gated, bounded* P9-L2 on **saved data only**. **No L3/L4.**

---

You are continuing my existing research implementation, not starting a new project. I want the actual mathematical implementation, tests, measurements, concise visualizations and evidence-backed reports—not an architecture proposal only.

## 0. Read and reconcile sources BEFORE any edits

Read these documents completely, in order, and verify the actual repository state:

1. `instruction-phase-md/latent_causal_tamp_methodology_v1_8.md` (Methodology v1.8).
2. `instruction-phase-md/latent_causal_tamp_implementation_guide_v2_0.md` (Implementation Guide v2.0).
3. The previous methodology v1.7 and guide v1.9 for preserved historical contracts.
4. `responses-phases/0024_P8a_joint_coupling_decisive_audit.md`.
5. `responses-phases/0025_P8b_selection_sampler_and_baselines.md`.
6. `responses-phases/0026_P8c_kappa_balanced_collection_and_training.md`.
7. `responses-phases/0027_P8d_matched_oneshot_execution.md`.
8. `responses-phases/P8_DECISION.md`.
9. Actual source, tests, configs, original teacher records, checkpoint manifests and six archived replays.

If the two new versioned `.md` files are not yet inside the repo, locate the explicitly provided attached copies or import the supplied files into `instruction-phase-md/` unchanged. **Never silently fall back to v1.7/v1.9 or invent their contents.** If a required document is unavailable, complete the nonmutating audit and report the blocker; do not implement an approximation from memory. Preserve the previous instruction docs.

Your actual starting revision may differ from `f9a6de0`. Before doing anything, run and record local HEAD, `origin/main`, `git status`, staged/untracked files and relevant source file hashes. **Never clean/reset/remove/overwrite unrelated working-tree content.** If the remote has advanced, inspect and reconcile; never force push. Do not create another repository.

## 1. Scientific goal and non-negotiable architecture

We retain exactly the originally agreed hypotheses:

- **A: LOCAL-SEQUENCE**, local static terms and GRU repair feasibility.
- **B: JOINT-CAUSAL-EBM**, explicitly normalized joint binary outcome factor graph with B's learned predecessor/prefix order function.
- **C: HYBRID-JOINT**, B's joint outcome graph with C's GRU replacing—not redundantly supplementing—the order representation.
- **SF**: matched factorized, non-energy supervised control; **G+M**: independent geometry + complete physical motion baseline.

For B/C retain the five *factor families*: **F1 static (unary + pairwise placement), F2 physical ordered sequence, F3 fixed-original-robot hypothetical scene interventions, F4 complete ordered repair omissions, F5 additional generic outcome coupling**. A factor family is a shared learned function instantiated on actual scoped variables, not one giant box or five independent classifiers. Binary outcome nodes are `z0`, eligible root-scoped `zS[I]`, repair-scoped `zR[r]`, and independently evaluated `zO[r,t]`; learned energies imply their probabilities via exact Boltzmann normalization/marginalization. `c0` and the high-level proposed repair `r` are observed inputs, not outcome nodes. The 3R continuous motion planner remains completely independent, uses the existing 48-grasp family, and verifies complete pick/carry/place/release/retreat and target `SAFE_RETREAT`.

**Do not simplify by deleting the joint distribution, making independent sigmoid heads the B/C ground truth, or changing the physical teacher.** Do not claim that statistical factor edges discover a causal DAG, that four intervention labels prove coupling is essential, or that more factors guarantee an advantage. Negative experimental results must be honestly reported.

## 2. The critical mathematical correction

The P8 B/C models already define the **root-consistent** conditional outcome distribution

`P(z | r,c0) = P_S(zS | c0) * P_Q(zQ | zS,r,c0)`, with correct *separate* normalizers, absent slots removed, and exact enumeration for bounded active bits (historically K≤9).

Implement a **new versioned, root-level masked observed-data joint negative log likelihood**. For each root, count original and hypothetical scene evidence exactly once; integrate over unobserved scene/outcome variables; combine repair evidence conditioned on the shared scene assignment; and treat physically identical teacher queries as **one event**, not independent copies.

The canonical identities are critical: `zR[empty] = z0` and an omitted physical repair may be the exact same event as another complete candidate. These cannot be independently charged twice or allowed to disagree in an alleged exact likelihood. Audit all query IDs, all root/candidate scope assignments and every alias. Show both a mathematical proof and executable unit tests on tiny, exactly enumerable roots. A factor-graph identity assertion without numerical checks is insufficient.

If the P8 representation does not allow a computationally feasible exact **equality-aware root likelihood**, DO NOT call a duplicated-event product exact. Implement and clearly label a **de-duplicated composite likelihood as a fallback diagnostic**, show precisely where it differs from an exact tiny-domain model, write the engineering/scientific limitations and STOP BEFORE full L2 training. Do not silently choose a mathematically different objective to satisfy a gate.

**IMPORTANT:** `E_static(r)` is independent of outcome assignment z and cancels from `P(z|r,c0)`. Prove the outcome NLL sends it zero gradient and that separately supervised static unary/pair BCE actually trains it. Likewise the separate travel-head needs witnessed relocation path cost labels. The authorized **default proposed B/C objective** is:

`L = L_joint_observed_root + λ_static * L_static_BCE + λ_J * L_first_witness_travel`.

This is **one primary outcome likelihood plus two mathematically necessary auxiliary signals**; do not market it as literally one generative NLL for all physics. Do not restore redundant P8 task BCE, scene BCE, omission BCE, κ/effect MSE or ad hoc pool-CE by default. Additional selection loss requires its own defined observation model and future approval.

**Repair ranking is separate.** A conditional distribution that sums to one for each repair cannot identify the best repair merely by marginalizing over all outcomes. Derive `p_R(r)=P(zR=1|r,c0)` from B/C, and use an explicit success-conditioned candidate energy `E_rank(r)=E_static(r)-T_s*log(p_R(r))-T_s*log(rho(r))` (up to constants), with uniform reference measure unless otherwise frozen. Preserve the current lexicographic ranking comparator `move_count -> predicted witnessed J -> analytic displacement -> E_rank -> stable ID`, static certificate vetoes, abstention and bounded deterministic scoring. A risk-aware variant is NOT authorized to replace it in this stage.

## 3. P9-L0 — nonmutating source/evidence audit

Before edits:

- Record working-tree/remote hashes and all P8 checkpoints, manifests, policies and source metadata; trace exact numerical `z0`, zero-move `zR`, scene bit scopes, omission aliases, active-slot masks and `logP_S`/`logP_Q` computation in `abc7_models.py`, `abc7_train.py`, `abc8.py`, `p8_train.py`, `p8c_train.py`, `p8_eval.py`, `p8_learn.py`, `learn_data.py`, `ordered.py`.
- Confirm the published P8 results are reproducible from saved manifests; run the established baseline tests and archived replay/integrity checks with no new teacher invocations. The previous reported baseline was 323/323 tests, but report actual local outcome rather than assuming it.
- Verify historical DINOv2 image-derived features and known symbolic geometry are both being used and report precisely what is/was trained.
- Identify exact factor-to-variable edges, factor families, their tensors, which parameters receive gradients, and which P8 losses overlap or double-count evidence. Give a tiny illustrative factor graph with **circles for outcome nodes and boxes for factor instances**, not just a generic neural-network flowchart.
- Record discrepancy list between Methodology v1.8, Guide v2.0 and code, without rewriting old evidence.

Write `responses-phases/0028_P9_L0_source_and_likelihood_audit.md`, `runs/p9/P9_L0_GATE.json`, plus a small factor-instance diagram in `visualizations/p9/`. Do not commit unrelated files. On a fatal semantic discrepancy or baseline regression, STOP.

## 4. P9-L1 — exact math, data identity, gradients and small proofs (ZERO teacher calls)

Keep existing P8 code and checkpoints loadable. Add **no more than 2–3 focused Python files and one dedicated test module**, preferably `joint_likelihood.py`, an optional small `abc9_joint.py` wrapper if required, and `tests/test_p9_joint.py`. Prefer reuse to copying/rewriting full models. No big package hierarchy. Target ~120–280 logical lines/module; explain >300.

Implement a callable, differentiable observed-root NLL that uses existing learned scene and repair factor energies; include stable `logsumexp`, K guards, explicit observed/unknown masks, rootwise averaging, and no leakage of future/outcome/teacher fields to inference. Implement exact shared-scene outcome handling and **alias-safe** repeated query identities.

Mandatory tests (all executable with toy factors, then saved P8 structures):

1. `sum P_S = 1`, `sum P_Q(. | zS,r) = 1`, `sum P(z | r,c0) = 1` with ≤9 active bits.
2. Scene marginals invariant across candidate r even when omission-layout sizes differ.
3. Root NLL identical to brute-force evidence probability on tiny *nonduplicated* roots; then verify `z0=empty` and repeated omission/full-repair aliases against exact equality-aware tiny joint enumeration. Document exactly what model assumptions the result requires.
4. Gradient finite differences and gradient signs for representative scene-unary, scene-pair, sequence-unary, omission-unary, omission-pair, generic scene pair, scene↔repair coupling, higher-order terms.
5. Adding an r-only static constant changes ranking energy but not normalized outcome marginals or their gradient; explicit supervised static BCE gives static gradient. Cost head regression updates J only with witnessed labels; `J(empty)=0`.
6. Missing `UNKNOWN` / `NOT_RUN` fields are never mapped to zero; policy-relative `BUDGET_INFEASIBLE` and scoped `CERTIFIED` remain separately countable. An all-missing root gives no outcome loss (or is excluded), not NaN.
7. Same-endpoint reversed order yields different *input representations* when order matters; physically verified opposite outcomes cannot be fabricated. `r\t` recomputes all prefix states with omitted object retained at its original pose.
8. Clamp/extreme-energy and temperature behavior, no inactive z-slot padding dependence, no double scene-label count across a multi-repair root, no run-/root-ID leakage.
9. One real saved P8 development root forward/backward smoke without changing its data/checkpoint. Benchmark realistic root and K sizes. Fail closed on unacceptable combinatorics.
10. P8 full regression suite and six archived replays still pass; log every disagreement rather than hiding it.

Write `responses-phases/0029_P9_L1_exact_joint_boltzmann_math.md`, `runs/p9/P9_L1_GATE.json`, bounded numerical proof artifacts and a compact probability/factor-gradient visualization. **If exactness, alias consistency, teacher isolation or source invariance fails, STOP.** If only the formally named composite fallback works, retain it as a diagnostic and STOP before L2.

## 5. P9-L2 — gated, strictly bounded saved-data training pilot (NO new teacher collection)

I authorize L2 **only after both L0 and L1 engineering gates PASS for an exact equality-safe formulation**. Before any training, persist a frozen `runs/p9/L2_plan.json` with a CPU/time guard and intended arm-by-seed/update schedule; use the L1 throughput measurement to choose the largest **matched** experiment that fits the cap. Hard limits for this handoff:

- **Aggregate guarded training CPU:** 8,000 CPU-seconds maximum, inclusive of any tuning runs and aborted attempts; no GPU requirement or uncharged concurrent launches.
- **Per training process:** ≤1,800 CPU-seconds and ≤3,600 seconds wall-clock; **aggregate training wall:** ≤18,000 seconds; at most one trainer process active.
- **ZERO new teacher queries**, ZERO new root generation, ZERO physical target evaluation or one-shot episodes, ZERO 3D/hardware work.
- At most **one small predeclared seed-0 hyperparameter/gradient-sanity trial** (≤600 CPU-s of the total), without looking at legacy P8 test labels.
- Use exactly the same decided input supervision, source/masks, scene features, task data and candidate catalogues across arms, and the same optimizer update count and minibatch root indices for paired comparisons. Train from scratch; leave old P8 checkpoints unchanged.

Minimum comparison if measured throughput allows: `B-full`, `B-structured`, `B-quadratic`, `C-full`, `A`, and feature-matched `SF` at **three optimizer seeds each**, against historical P8 multi-loss inference metrics on equivalent disclosed legacy splits. `B-none` is an optional additional factor control if the cap permits. Maintain separate architecture and loss comparisons—do not attribute an objective improvement to coupling. If the 18-run matched matrix cannot fit, **freeze a reduced balanced arm/seed matrix before starting**, explicitly label it a pilot, and do not present unmatched runs as evidence of factor necessity. Prefer 3 seeds on B-full / B-structured / SF over many one-seed arms.

Validation: use the predeclared P8c validation set for checkpoint/temperature/threshold choices; historical P8c test and all past sealed tests are now **disclosed legacy diagnostics only** and must never become a claimed fresh holdout. No new random train/test split chosen after seeing results. Optimize clipping/gradient stability honestly and record per-factor gradient reachability. For A/SF use an appropriately matched marginal likelihood (they do not possess a joint z partition), along with the same separate static and J supervision. Keep the P8 multi-loss training protocol as an immutable comparator.

Required L2 metrics by root/seed and provenance: observed-root joint NLL, masked active counts, scene and repair marginal NLL, repair accuracy/AUROC/ECE, κ by decided sign and whether labels were certified or operational, omission outcomes, conditional oracle-revealed diagnostic (clearly offline-only), same-endpoint order contrast N/A if none, loss-term magnitudes, gradient clipping percentages, CPU/model calls, root-level restricted-catalogue selection and abstention. All results should include uncertainty, sample size and comparison limitations. Optional proof-only versus operational-weighted label sensitivity on saved records if fully comparable and within budget.

Write `responses-phases/0030_P9_L2_saved_data_joint_objective_comparison.md`, `runs/p9/P9_L2_GATE.json`, hashed seed checkpoints (only store essential models), `runs/p9/L2_plan.json`, per-run source/config manifests and 2–4 quantitative figures (NLL versus legacy, factor gradient health, predicted probabilities and selection errors). L2 engineering PASS is **not** a claim of scientific superiority. On guard hit, abort cleanly and report partial status; do not secretly expand the CPU budget.

## 6. Factor necessity and physical evaluation: DEFER, do not implement now

Guide v2.0 names L3/L4, but this handoff **does not authorize** them. Do not run factor-removal studies requiring new teacher labels, constructor-disjoint scenes, full 3R physical episodes, G+M hybrid evaluation or any new 3D work. Instead finish with `responses-phases/P9_NEXT_DECISION.md` containing the exact, evidence-backed L3 factor-ablation plan required by Methodology v1.8 / Guide v2.0 (F0–F13 coverage; order-swaps with identical endpoints, actual physical contrasting outcomes; intervention κ signs including proof-grounded positives where possible; independently realized omissions; originally feasible cases; constructor-disjoint families), but **no new collection budget request is implicitly granted**.

Do not silently substitute a simplistic five-loss independent classifier for B/C. The primary conceptual reason for this stage is a **real, testable joint Boltzmann likelihood**, with shared scene variables and conditionals, rather than cosmetic energy nomenclature.

## 7. Visual, reproducibility and GitHub deliverables

- Preserve old P4–P8 reports, hashes, policies, splits, solver, checkpoints and GIFs. Do not change teacher, 48 grasp family, certificate semantics, planning order, robot physics or cost definitions.
- Save P9 artifacts under existing `runs/p9/` and `visualizations/p9/`; instruction docs in `instruction-phase-md/`; the three numbered reports and the decision memo in `responses-phases/`. Every figure should carry a SHA-256/source manifest; no fabricated robot-motion GIFs during this zero-execution stage. Diagram, numeric panels and plots are appropriate.
- Deliver concise top-level README pointer if useful, but avoid redundant new subdirectories. Run `git diff --check`, relevant mathematical checks, all P8 tests and archived replay checks; record actual pass/failure and runtimes.
- Commit and push P9 work only if the current branch/remote and working tree permit safe, non-destructive action. Never stage unrelated dirty/untracked content; never force push. Record commit SHA and `origin/main` match, or report why no push was safe.
- **FINAL RESPONSE FORMAT:** report L0/L1/L2 gates separately; list changed source files and report paths; explain actual training objective implemented (exact vs composite; no false claim); summarize metrics and B-full vs structured vs SF conclusions *without claiming fresh generalization*; identify any blocked factors; quote total CPU/teacher calls; give commit and verification status; STOP.

**Success means a smaller, mathematically correct joint Boltzmann implementation whose factor-to-variable scopes and gradients are independently testable, plus an honest bounded saved-data comparison—not an automatic B/C win.**
