# P7 — Causal-Representation Repair, Faithful Five-Factor Audit, Balanced 2D Generalization and Model-Selected Execution

**Status:** Proposed, execution-ready research/engineering contract; **not executed** by this document.  
**Intended executor:** Claude Opus 5.5 High in the existing `latent-causal-tamp` repository.  
**Starting checkpoint:** Report `responses-phases/0021_P6_four_move_dataset_ABC_ablations_gifs.md`, P6 pushed commit `0006365` (confirm full HEAD, branch and remote; do not blindly reset).  
**Normative documents:** `latent_causal_tamp_methodology_v1_7.md` and `latent_causal_tamp_implementation_guide_v1_9.md` plus the separately approved teacher policy `2D-ABC-OPNEG-v1`. P6 is measured evidence, not a replacement for the methodology.  
**Stage boundary:** P7a (mandatory, **no new robot-teacher collection**) → approval-by-machine gate → P7b (bounded **new 2D data**, retraining and independent simulated evaluations only if gate passes). No full G5/G6 verdict, 3D, physical xArm, new teacher policy, unbounded sampling, or unilateral scope expansion.

> **Research question:** Can explicitly modeled, edit-specific and omission-specific outcomes improve **out-of-scene prediction and the selection of executable minimally disruptive ordered repairs**, beyond sequence-only and geometry-based controls? **Do not assume B or C will win.** Any null or negative result is valid evidence when documented honestly.

## 0. Read-first, authority, working tree, and reporting rules

1. Read this whole document; methodology v1.7; guide v1.9; `responses-phases/0019...`, `0020...`, **`0021...`**; original P6 contract; actual `abc_models.py`, `abc_train.py`, `zlayout.py`, `zlayout_r4.py`, `p6_scenes.py`, `p6_run.py`, `p6_learn.py`, `p6_train.py`, `p6_viz.py`, `p6_viz_models.py`, `sampler.py`, `ordered.py`, `skill.py`, `verify.py`, and associated tests before touching code. **Locate modules rather than assuming filenames are exact.** Inspect complete definitions and call sites, not only grepped snippets.
2. Check branch/HEAD/remote (expected short commit `0006365`), working tree, root-PDF deletions, user's untracked files and report/run manifest hashes. No `git reset --hard`, cleaning unrelated files, forced push, rewriting reports or editing archived P4–P6 evidence. Use selective `git add` only. Record any pre-existing dirty state.
3. Preserve the existing 2D articulated **finite-width 3R** robot, wrist/gripper and actual object transport. Legal candidate cells are **terminal poses**, not a teleporting robot; a relocation means pick, carry, place, release and retreat with continuous joint/gripper state, then target completion with `SAFE_RETREAT` from the genuinely achieved state. **All 48 declared grasps** and the existing fixed planner/seed policy are respected; failure of one grasp or single path is not proof of infeasibility.
4. Preserve A/B/C as scientific baselines. All architectural fixes must be explicitly **versioned/config-selected** so P6 checkpoints load with their original meaning; if mathematical equivalence cannot be maintained, name a new corrected arm, never call it an unchanged B/C. Data from earlier operational-negative policies must retain source provenance.
5. All stages emit `PASS`, `PARTIAL`, or `BLOCKED` independently, and each gate records a machine-readable decision/reason. A software PASS is distinct from an empirical hypothesis being established. No successful-looking figure substitutes for a numerical result.
6. Prefer minimal, readable modules (target <=180 logical lines; trigger a design review above ~300), shared existing utilities, no parallel mini-framework, limited subfolders, headless visualizations, explicit deterministic seeds, immutable manifests and small unit tests. If necessary create a tiny `p7_*.py` adapter rather than refactoring historical teacher code.

## 1. Why P7 is necessary — frozen P6 observations and falsifiable hypotheses

P6 collected **16** independent roots in four families and four robot initial configurations: **316** fully decided queries, **95** witnessed feasible, **179** certified negatives, **42** policy-relative budget negatives, no UNKNOWN, **11** four-action witnesses, **9** decided same-endpoint order contrasts on development roots, and all **12** development roots with **kappa = +1**. The proof-grounded/policy-relative distinctions matter: **nine** kappa results rely on operational place-side negatives. There were no verified one-action repairs among the obstructed ordered queries. These are **not** estimates of global minimal-repair length.

On the P6 holdout, primary model mean accuracies A/B/C = **0.746/0.799/0.582**, AUROC **0.841/0.884/0.808**. B-no-coupling reached **0.825 accuracy** on its single reported seed, so B's coupling contribution is **not established**. B/C assigned essentially equal effects to the **A-only, B-only and A+B** scene edits, despite teacher pattern **(0,0,1)** for those edits. All P6 negatives came from the same screen-access mechanism. C was poorly calibrated and often stopped at epoch 10–30; global clipping occurred on every training step. Offline selected-repair success on four held-out roots was weak (A 0, B 0.417, C 0.167 mean over seeds). The privileged geometry baseline was perfect by construction.

P7 tests distinct hypotheses; the following are **not** results to assume:

- **H-R (representation):** Giving each outcome slot its own hypothesized edit/omission description, while sharing original-scene conditioning correctly, permits separation of singleton versus joint edits. First show a traceable input/logit cause, not a superficial loss decrease.
- **H-O (optimization):** Per-root/per-loss normalization and auditable clipping let B/C fit separately supervised outcomes and joint probabilities without collapsing calibration or C training.
- **H-I (interaction):** The corrected system predicts **kappa ∈ {-1,0,+1}** on *fresh independent roots*. A nonlinear scene network may learn kappa **without cross-outcome coupling**, so kappa accuracy alone is **not** proof that a coupling factor helps.
- **H-P (planning):** Better calibrated predicted executability improves **matched-budget model-chosen complete repair success** and avoids unnecessary relocations, not merely higher offline AUROC.
- **H-G (generalization):** Gains persist beyond the one P6 access-screen construction pattern. If a screen/motion-planning baseline wins, state this.

## 2. The precise semantics: no scope confusion

- A candidate `r=((i1,k1),...,(im,km))`, `0 <= m <= 4`, moves distinct obstacle IDs **once**, in declared order. Initial q0/robot base/gripper, object poses, target and goal are known. Ideal prefix scenes used by models do not contain future actual arm trajectories. The training teacher **does** simulate/planner-verify complete physical relocations; models do **not** synthesize full joint trajectories.
- **`z0`** means target-only feasibility on original fixed robot scene; **`zS[I]`** target-only feasibility after a *specified eligible* fixed-robot object-pose edit `I` with original robot q0/g/attachment and original appearance anchor; **`zR(r)`** complete ordered relocation plus target and safe retreat; **`zO[r,t]`** complete independently reevaluated repair after removing actual action `t` from `r` (other actions keep order). The omitted object's position in remaining prefix scenes is its original position. No reuse of a trajectory from `r` to fabricate `r\t`.
- Observed `ΔS[I]=Y_S[I]-Y_0`, `ΔO[t]=Y_R-Y_O[t]`; `κ(I,J)=Y_S[I∪J]-Y_S[I]-Y_S[J]+Y_0`, only with **four independently decided eligible target-only labels**. A scene edit that succeeds is not proof that a robot can physically make the edit. An omission-specific necessary step is **not** universally necessary across all alternative plans.
- The joint `z` fields are binary **outcome hypotheses** (0/1), not binary object-culprit neurons or causal-graph arrows. B/C potentials are neural factor functions, not recovered scalar physical cause weights. “Joint Boltzmann learning” means a supervised **finite-pool (r,z)** partition with real fully decided outcome vectors, **not** Hopfield training, automated DAG discovery or globally normalized planning.
- Feasible = `VERIFIED_FEASIBLE` with full recorded witness; certified negative = accepted sound checker proof with explicit scope; `BUDGET_INFEASIBLE` = clean complete execution of the unchanged 3-seed **operational** policy; `UNKNOWN` = censored/incomplete and excluded from decided BCE/joint-pool targets. Unknown never becomes negative because a gate needs examples. `GOAL_OVERLAP`, target-pick access, first-action proof and place-side operational failure must be differentiated.
- `J*(r)` is measured **first complete relocation witness** normalized joint travel, excluding target/HOME; first-witness source must be pinned. `C_d(r)` is analytic displacement. At inference, `Jhat` and `C_d` guide proposals/lexicographic choice but **are not the five B/C causal-feasibility factors**.

## 3. P7a — strict diagnostic foundation, NO teacher/planner collection

### 3.1 Read-only representation/graph audit (first gate)

Trace from `learner_tensors` to every energy contribution for all A/B/C and all `m=0..4`. Output a document and a small per-factor runnable trace on one frozen P6 root. Do not guess from report wording.

**Normative five-factor B, with variables suppressed where obvious:**

```text
E_B(r,z|c0,Q) = E_static(x(r),c0)
               + phi_seq(r,zR,c0)
               + sum_I phi_scene(I,z0,zS[I],c0)
               + sum_t phi_omit(r,t,zR,zO[r,t],c0)
               + phi_couple(r,z,c0)
```

`E_C` keeps static, scene, omission and coupling and **replaces** B's prefix-conditioned order contribution with a GRU order potential; it must not double-count B's prefix factor. `E_A` remains endpoint U/V + GRU task feasibility factor, with scored-edited-scene explanations, no explicit z.

**Required audit questions, with evidence at code lines and tests:**

1. Is `phi_omit` genuinely represented as an interaction between `zR` and the **corresponding** `zO[r,t]`, or is it only an independent omission bias? If missing, mark **SPEC_MISMATCH** and implement a small, named, versioned omission potential. It may share a tiny MLP with order/context features; do not reimplement a huge network.
2. Does `phi_scene` truly see **edit identity, exact moved-object IDs, before/after poses, per-object delta, edited full-scene geometry, candidate eligibility and unchanged q0**? Can it distinguish A-only/B-only/A+B on the *same* root? For every slot, dump allowed feature checksum, nonzero mask, gradient and logits. **Do not add privileged post-intervention image, computed teacher feasibility screen outcomes or planner trajectory.** Counterfactual geometric poses calculated deterministically from `c0` and the predeclared edit are permissible.
3. Are `z0` and fixed scene-edit outcomes **root-scoped quantities**, the same for all `r` on that root? Diagnose any `p(zS[I]=1|r,c0)` dependence on the arbitrary repair scored or on its active omission-slot count. Define and document a **consistency contract**: either (preferred) a shared root-conditioned scene-outcome distribution and repair-conditioned `zR/zO` factors with a genuine joint EBM; or a strictly tested candidate-consistency constraint. A coupling interaction may encode correlation but must not produce contradictory claimed fixed-scene effects for identical `c0,I`. Version changes; do not claim exact original five-factor equivalence if the normalization/graph is changed.
4. Confirm B's `phi_seq` conditions on exact selected order/ideal prefixes **without a GRU**, and C uses GRU **without** B's old prefix order factor. C's omission potential should use omitted **recomputed** prefixes, not the full sequence with one input token zeroed ambiguously.
5. Confirm two coupling modes: **quadratic** `W(r)` and optional higher-order residual `phi_HO`. `no-coupling` MUST zero **all cross-outcome** coupling (`W` and `phi_HO`, plus any hidden shared joint interaction) while retaining identically expressive single-outcome networks. The `quadratic-only` control disables **only** `phi_HO`. Inspect gradients and do an equivalence test to show each switch changes exactly what its name asserts.
6. Report the current compact implementation `E_static - Σ s_k z_k - ½ zᵀWz - phi_HO + T K ln2`, identifying which original five factor types it covers, does not cover or approximates. **Do not call robot travel J the fifth factor.** Name historical implementation “P6 quadratic/logit parameterization”, if needed.
7. Verify `Z_LAYOUT_V3_R4`: up to **9 genuine** active outcome bits, exactly 512 enumerated states for specified 4-move edit layout, no duplicate omissions, correct empty `r` semantics, exact masks/aliases/refusal, stable logsumexp, temperature consistency, gradients and `+T*K*ln(2)` uniform reference correction. Proof-check repair comparison when K varies: equal raw energies must lead to equal *prior* repair mass; changing an inactive padded slot cannot change anything. Distinguish this correction from a substantive learned potential.
8. Verify scene-edit outcome invariance under object indexing/permutation and repair-catalogue expansion, pair symmetry, action-order sensitivity/invariance of the proper controls, valid first-witness travel cost and strict input/label namespace split.

Write `reports/p7a_factor_mapping.md` (or the closest consistent existing report location), a machine-readable truth table of factors → inputs → state slots → parameters → losses → ablations, and minimal exact tests. **If the audit exposes a substantive factor mismatch, fix it with a new config/model version BEFORE training.** P6 weights and results remain immutable historical baselines.

### 3.2 Diagnose the identical scene-edit predictions, not just add descriptors

On at least one frozen, fully decided P6 root with `y0=0, yA=0, yB=0, yAB=1`, print/record:

- Three *learner-visible* `I_A`, `I_B`, `I_AB` edit encoding vectors and their normalized geometry components; checksum equality/difference, masking, changed object IDs, displacement directions and magnitudes; computed edited endpoints and root anchor ID only in **audit metadata**, not model input.
- `phi_scene`/unary outcome logits, `phi_omit` logits, `W`/HO contributions where applicable; exact `p(z0)`, `p(zS[A])`, `p(zS[B])`, `p(zS[A+B])` for **the same root**; `ΔA`, `ΔB`, `ΔAB`, `κhat`; source labels/masks.
- Re-evaluate the **same edit** while holding `c0,Q` fixed and changing only an unrelated candidate repair (0/1/2/4 moves). State whether the marginal is invariant; if not, separate raw conditional effects from any canonical root-level predictions and debug.
- One controlled **same-root tiny overfit** (B, C, B-no-coupling) to the three edited outcomes; a separate held-out simulation-free synthetic fixture with `κ=-1,0,+1`. Fit losses, gradients and inference must align. The expected **capability** is that a learnable nonlinear scene encoder can assign distinct marginals, **not** that the coupling ablation must necessarily fail. If even this overfit fails, block P7b and diagnose before spending teacher budget.
- A consistency test on empty vs nonempty repairs and duplicated `zS` supervision: count one independent scene-edit observation **once per root per epoch** in its supervised BCE; repeated appearance across candidate z vectors must not unintentionally multiply scene labels by candidate count. Joint energy denominators should stay mathematically correct, while loss weighting handles duplicated source observations transparently.

### 3.3 Fix training optimization in a controlled, measured way

Do **not** introduce an arbitrary loss weighting that makes a desired arm win. Before changing coefficients measure, per model and seed:

- Every unweighted loss (`static`, task, each outcome-field BCE, scene/omission effect, optional explicit `κ` metric, first-witness log-Huber, A finite-pool, B/C joint finite-pool). Count independent root/query observations and complete pools per term; count budget-sourced labels separately. Report units, means and variance.
- Per-term **unclipped** gradient norm on shared encoder, scene, omission, sequence, W/HO and cost modules, with the same batch; preclip and postclip global norm, clipping fraction by epoch, `NaN/Inf`, max logit/marginal energy and loss spikes.
- Explain why P6 joint pool ≈7 units of total ≈10 and why C stops early; diagnose whether frequent clipping simply suppresses small auxiliary terms. Normalize losses first **by valid observed units/roots**, not by arbitrary class count or number of enumerated z states; tune a **small, predeclared** coefficient grid on existing validation only. Freeze selected coefficients BEFORE new P7b test data; record discarded settings without cherry picking.
- Numerical guards: stable logsumexp, explicit float64 or documented precision, scalar `Ebar` and scalar `J` regression (past collision of variable name `j/J`), detached teacher fields, no in-place cached logits reused with changing grad contexts, finite-difference gradients and cost-head independence from z.
- Fair A/B/C comparison: identical train/validation data, DINO weights/features, update/early-stop protocol and proposal domain, 3 deterministic optimizer seeds; A parameter-matched, learned geometry-only controls and **fully disabled-coupling B/C**. Do not make B/C causal claims merely because they receive extra decided z labels; include **A with matched supervision where representable** and at least one supervised non-energy repair/task predictor under the same feature budget, or explicitly report the remaining supervision confound.
- Calibration: report proper probabilities `p_R` and `p_0`, reliability diagram, Brier/NLL, chosen feasible threshold and **abstention/coverage**; calibrate using validation only (simple temperature scaling is permissible if frozen). Distinguish `Ebar` (ranking) from `p(zR=1|r)` (success probability). Temperature scaling must not silently change trained joint energy or raw sampler checks.

**P7a experiment matrix:** A, B, C (3 seeds each) first; B-no-coupling, C-no-coupling (3 seeds each) second; capacity-matched A and a supervised non-energy sequence classifier (at least 1 seed, if budget permits); geometry-only arms and quadratic-only comparison only after core runs fit budgets. Keep all P6 checkpoints as frozen reference, train new models under versioned configs. **No new teacher/robot oracle calls in P7a.**

### 3.4 P7a gates — all predeclared

Mandatory foundation gates before P7b:

- Full historical tests and 6 archived replays pass; new B/C exact partition, active-layout, coupled-gradient and factor mapping tests pass. No teacher/target calls in training/test/plot stages.
- On **at least two distinct frozen development roots** with independently decided A/B/A+B outcomes, the new edit descriptors are observably distinct; B and C can **overfit exact observed field labels** on a deliberately tiny training microset; κhat is computed from predicted marginals and not derived from teacher labels at inference. Do not require generalization yet.
- On independent synthetic fixtures with outcome patterns `+1`, `0`, `-1`, exact `z` enumeration and scene-prediction bookkeeping are correct; both **quadratic-only and HO** parity capability tests report their true outcomes (quadratic need not fit parity).
- Root-scoped scene predictions are defined consistently across candidate repairs; noncoupling switch actually eliminates all specified coupling pathways, and no B prefix + C GRU double counting.
- Calibrated validation is evaluated without opening a fresh holdout; optimizer loss decomposition and clipping diagnostics are complete. A single architecture's poor validation performance is **not** grounds to block the entire study if its implementation and gradients are correct; label result inconclusive.
- If a core scientific bug persists (e.g. identical edit features, failed z marginal, omission aliasing, teacher leakage, wrong evidence masks) → `P7A_BLOCKED`, **STOP** before P7b. When a remaining ambiguity requires a major new causal architecture or teacher-policy change, stop and request explicit authorization; do not silently enlarge scope.

## 4. P7b — broaden root distributions while preserving honest physical verification

**P7b only after P7a PASS.** Freeze architecture implementation, loss choice, catalogue generator, robot policy, root seed/split list, comparison metrics, scene-family constructors and numerical caps **before teacher queries**. The **P6 holdout is already examined** and may be used as historical diagnosis; it is NOT the pristine final P7 holdout. P7b must create new independent split roots. Preserve grouping of any correlated same-geometry q0 variants, alternative renderings, siblings and permutations.

### 4.1 Target: 48 independent roots in two gated waves (24 + 24)

Use **six genuinely distinct construction intents**, each with **eight** independent root geometries (four train, two validation, two sealed test) and at least four valid initial robot configurations distributed across the complete set. For each family, wave 1 has 2 train + 1 val + 1 sealed test; wave 2 likewise. All 48 root definitions, seeds and group assignments are predeclared before the first teacher call. The total **48 is an upper bound**, never a retrospectively reported realized count if gates stop. Wave-2 does not begin unless wave-1 quality and resource gates pass. Existing P6 root data may be added to *training* with provenance and complete group-level exclusion from P7b heldout; do not label P6 holdout as untouched test evidence.

| Family | Constructed intent (verify; never assert labels from intent) | Why distinct |
|---|---|---|
| **K+** complementary blockers | Target-only `Y0=0, YA=0, YB=0, YAB=1`, `κ=+1` | Two changes jointly necessary for *specified* edit set |
| **K−** redundant alternative restorations | `Y0=0, YA=1, YB=1, YAB=1`, `κ=-1` | Either edit suffices; joint adds no further benefit |
| **K0** additive/irrelevant controls | e.g. `Y0=0, YA=1, YB=0, YAB=1`, `κ=0`; nuisance `Δ=0` | Negative controls and distinct effect magnitudes |
| **ORD** genuine access/order | Same endpoints but differing ordered outcomes; ≥3-action prefix dependencies and 4-move where attainable | Isolates sequence effects from endpoint geometry |
| **MOTION** access-screen-pass but downstream motion interference | Carried-object/link sweep obstruction, placement or retreat hindrance, destination-induced new obstruction; keep failure mechanism recorded | Tests beyond P6's adjacent-cell screen-negative shortcut |
| **ALT** alternative repairs / starts | 0/1/2/3/4-move *candidate alternatives*, multiple plausible verified solutions, contrasting q0 and travel/displacement tradeoffs | Tests lowest-number-of-moves preference and action feasibility |

**Critical sampling caveat:** These are *design intents*, not guaranteed teacher labels. Only count realized `κ` signs, order contrasts and verified multiple-cost solutions. If K−, MOTION or one-action witnessed alternatives are physically unconstructible under declared grasps/geometry, record `CONSTRUCTION_UNAVAILABLE` with rejected attempts and **do not manufacture them**. Mixed difficulty includes reference/empty success, true obstructed empty failures, valid but unexecuted/UNKNOWN, and static-invalid exemplars. A single failure screen is not evidence of underlying motion-path impossibility; full robot witnesses and sound certificates decide claims.

**Variety requirements:** vary initial q0 (including correlated same-object-geometry sibling starts kept in one root group), object layouts/distances/radii where allowed by pinned simulator, selected grasp direction availability, target/goal, relocation endpoint alternatives, number of unused obstacles, start-to-grasp transitions, placement/carrying obstacles and order. No artificial teleports represented as executed motion; scene edits are diagnostic target-only queries. Keep masks/appearance anchor genuine and use DINO/geometry-only comparisons; record identical-disc appearance limitations. Group mirrored/translated/ID-renamed near-duplicates before splits so templated scenes don't leak as “independent generalization”. Distinct (target,goal) alone is **not enough** to establish scene independence. If a family cannot vary under pinned physics, expose the limitation.

### 4.2 Per-root catalogue (<=32 UNIQUE teacher queries, frozen before results)

Build a compact deterministic candidate set sufficient to compare 0–4 moves, including controls and explanation closure:

- One separate **clean reference** and one obstructed **empty repair** (do not mix their root outcome hashes); correct target-only `z0` query comes from the obstructed initial root.
- Scene target-only edits `I_A`, `I_B`, `I_A∪I_B`, one **nuisance**, eligibility masks and anchored q0, with immutable named edit mapping. The nuisance may be excluded from the 9-bit exact `z` layout but remains supervised as a separately evaluated edit.
- A small set of distinct 1-, 2-, 3- and 4-move **complete ordered repairs** as meaningful for that family: at least one intended main solution, same-endpoint swaps/permutations, a different resting destination and where possible an order-independent alternative. Never count unqueried permutations as labels.
- All four leave-one-action-out queries for a designated 4-move main candidate (many may deduplicate with planned 3-move queries). Add omission closure for one additional candidate **only if** there is room. Every omission is evaluated from original S0 with unchanged rest order.
- Explicit **alternate target-only no-move** and **shorter full-repair** options needed for least-repair comparison; no oracle-selected shortest candidate construction after seeing labels.
- Static-invalid candidate endpoint controls evaluated by deterministic static checker **outside the teacher query cap**, with distinct provenance. Each family should include legitimate static-valid but physically difficult candidates.

A typical 4-obstacle catalogue may contain ~2 reference/base + 4 scene edits + 4 singles + 6 pairs + 4 triples + 3 quads + up to 4 omitted candidates (deduplicated) + ~3 alternative endpoints = <=32, but **the actual query-to-slot and unique count must be printed before execution**. The catalogue must not imply an impossible requirement that every one of 32 queries belongs to one 9-bit fully decided pool. For each required outcome slot store physical query ID, eligibility, decided status, outcome provenance and exact K; eligible UNKNOWN means the joint candidate is incomplete, not a zero label.

### 4.3 Teacher and certification boundaries

- Pin `2D-ABC-OPNEG-v1` **without changing its three seeds, grasp family or declared planner stops**. If policy change is scientifically necessary, do not quietly mix labels; stop and propose a versioned follow-up.
- Before collecting, perform read-only **A7 place-side certificate** soundness audit against full 3R/gripper/target goal and tight goal tolerance (historical ~2 mm mismatch). A robust certificate requires proof that **every** declared place/grasp approach is obstructed under valid boundary geometry and a correct fixed start, not a failed RRT run. Independent positive-witness replay and near-boundary counterexamples must not be contradicted. If no proof, keep A7 disabled, preserve `BUDGET_INFEASIBLE` and report.
- For every label log `VERIFIED_FEASIBLE / CERTIFIED_INFEASIBLE / BUDGET_INFEASIBLE / UNKNOWN`, certificate name + scope, seed attempts, per-connector results, process-tree CPU/wall, location of first witness, measured J, target safe-retreat, source hashes, censoring reason and all edit/omission group IDs. **Do not conflate 0 UNKNOWN with diverse/strong proofs.**
- For motion mechanisms, include full physical verification and actual swept geometry in the **teacher**; never feed future computed sweeps or teacher trajectories to the learner. Reject static invalidity separately. Do not promote an RRT timeout to a sound motion-blockage certificate.
- Report certificate-only vs operational effects and κ separately. The same intervention tensor must not be treated as proof of *physical relocation necessity*.

### 4.4 Predeclared collection gates, not result-dependent cherry picking

Wave 1 = 24 planned new independent roots (4 per family; 12 train, 6 validation, 6 sealed test), up to **768** teacher queries. Construction may reject some predeclared attempts; record them. Quality assessment uses **train/validation only** (test labels remain sealed). Advance to wave 2 only if all of the following are observed:

1. All high-integrity invariants pass: no witness/certificate contradictions, every negative has correct scope, no unexpected teacher-policy change, no failure of full robot replay, no leak of test outcomes, <20% UNKNOWN among attempted **development** queries.
2. At least **2 decided `κ=+1`, 2 decided `κ=-1`, and 2 decided `κ=0` roots** across development data **from appropriate independently constructed roots**, with provenance stratification; do not count intended patterns. If K− family is unavailable, fail this gate and stop rather than substitute more K+.
3. At least **4 distinct held-out-from-training (train/val) decided same-endpoint order pairs** across ≥2 independent roots, including at least 2 proof-grounded when possible; and ≥2 fully witnessed repairs of length ≥3 across ≥2 roots.
4. At least **3 development roots containing two differently-sized VERIFIED executable repairs** among the frozen catalogue, with first-witness J and displacement recorded; if not, flag `MINIMALITY_EVIDENCE_MISSING` and do not claim minimality even if overall collection continues only by explicit predeclared exception (default STOP).
5. At least **2 development roots where the ordinary neighboring-cell static screen does not already decide the nontrivial failure**, and at least one completed target/repair result after physical trajectory verification. If not, stop; don't call these broader motion tasks.
6. Adequate actual completed joint pools: ≥8 root-conditioned fully decided B/C candidate pools, with active slot/checksum integrity, distributed over ≥3 families; never infer hidden labels or buy completeness using post-hoc queries.
7. Budget thresholds in §7 hold. A gate miss causes **PARTIAL/STOP**. Do not change root definitions, labels, seed schedules or gates to force continuation. Report failures by family, including certified-vs-operational balance.

Wave 2 = 24 further predeclared roots under unchanged plan. No redefinition of families or targets based on wave-1 validation/test performance. Final empirical sufficiency target (not an assured pass): ≥6 independent roots of each κ sign, ≥12 new decided order contrasts spanning ≥6 roots, ≥8 roots with two genuinely different witnessed repair lengths, and a minimum of **12 sealed independent test roots** across six families. If these goals fail, still report denominators; do not claim causal/coupling/minimality generalization.

## 5. P7b model training and fair ablations

1. Freeze architecture configs at the P7a gate. Train on **P7b train roots only plus allowed historical development roots**, tune early stopping/threshold/temperature/calibration and coefficient choices on **P7b validation only**, seal P7b test labels until all model choices frozen. A diagnostic retrospective comparison on P6 is separately reported and not a new holdout.
2. **Primary (3 independent seeds each):** A, corrected B, corrected C. Refit **B-no-coupling/C-no-coupling (3 seeds)** with **both** quadratic and higher-order cross-outcome interactions disabled. Include parameter-matched A, geometry-only models (frozen initial visual input removed, geometry kept), B quadratic-only, C quadratic-only and a supervised sequence-only nonenergy head as fit within the secondary budget. Mark incomplete ablations explicitly and never compare 3-seed means with 1-seed results as identical evidence.
3. Use exactly common learner-visible inputs and candidate sets, strict source-stratified masks/weights (certified vs operational), no root/family/query statuses at inference. Report additional B/C observation supervision and a fair supervision-matched or label-matched control; explain if comparison remains confounded. Define finite-pool weighting by root, not accidental dominance of roots with 32 queries or 512 z assignments. For `m=0..4`, preserve corrected `K(r)` uniform reference measure in B/C training and inference and cap exact enumeration memory/time.
4. Verify modeled scene outcomes A/B/A+B **separately**, including `κhat` sign and magnitude; report both full `B/C` and `no-coupling` to test whether any gain comes from coupling rather than edit-specific unary nonlinear features. Report `p(zS[I])` invariance across r and no fabricated predictions for UNKNOWN.
5. Freeze temperature and success/abstention thresholds **from validation only** before test. Evaluate probability calibration (NLL/Brier/ECE/reliability and coverage), task accuracy/AUROC with counts by label source, root-level clustered confidence intervals and per-family metrics, original-task feasibility, edit and omission MAE/sign, **κ confusion/magnitude**, same-endpoint order metrics, learned vs analytic travel cost, and paired repair ranking.
6. Define per-root **restricted-catalogue minimality** from independently `VERIFIED` candidates only, where any shorter UNKNOWN prevents proof of minimum over the full catalogue. Report (a) chosen vs best known verified number of moves, (b) chosen repair executable yes/no/unresolved, (c) predicted J vs first-witness J for successful choices, (d) displacement, (e) abstention and full episode denominator, (f) whenever possible one scene containing multiple verified move lengths. Never claim globally least-required number of obstacles from catalogue search or four omission failures alone.
7. For B/C joint probability claims report exact `P(z|r)`, exact marginal `P(r)` with uniform reference, fully decided pool counts, joint NLL, independent-field NLL, an explicit **coupling-dependence** diagnostic and quadratic/HO differences. Neither measured κ≠0 nor synthetic parity overfit alone proves higher-order factor or coupling improves real repair prediction.
8. The **analytic geometry screen** baseline is privileged for constructed screen cases. Report it as such, and separately compare to an equal-budget actual geometric/full-motion ordered-search baseline. Keep uniform proposal and supervised task-head controls. Match unique scored candidates, attempted relocation witnesses, full-motion CPU, one-shot target invocations, and sampling budget.

## 6. Independent one-shot model-chosen 2D execution (mandatory if gated)

After model/threshold/hyperparameters are frozen, run **up to 36** fully instrumented simulator episodes (12 fresh P7b sealed test roots × A/B/C), subject to §7 cap and actual available scenes. If wave 2 stops, only available legitimately untouched test roots; do not use P6 holdout as fresh test. This is **not hardware**.

- Same initial 3R `q0`/gripper/object poses/target/goal across arms. Each arm **proposes and ranks before teacher outcomes become visible**; use equal finite candidate enumeration/sampling and time. New out-of-catalogue candidates are allowed if legal, with immutable proposal hash and no teacher prelabel. Do not pick only known feasible catalogue repairs using hidden labels.
- Run shared static checks, then independent complete ordered relocation attempts in rank order under the identical declared planner budget. Once a relocation witness is committed, execute that full prefix in actual simulator state; target attempted **once only**, with SAFE_RETREAT, no switching to next repair after target failure. If no witness, abstain/unsolved and count it. Preserve failure, UNKNOWN and CPU/call denominator.
- Report original task no-repair test results as distinct, the selected move count, successful target+retreat and false-positive short repair selections, joint/object travel, verifier calls and CPU. Keep operational labels separate from proof-grounded claims. Do not treat replay of the P6 teacher's already-decided outcome as an independent test.
- Compare to matched uniform proposals and geometry+full-motion baseline if budget permits, otherwise label NOT_RUN. A/B/C matched independent test execution is higher priority than adding ablations.

## 7. Hard ceilings and stop order (authorized maxima; NOT targets)

All expensive runs use an existing guarded one-worker **process-tree** worker, durable checkpoints and append-only CPU/call/wall ledger; child processes count. Do not start a new costly stage if caps or gate cannot be honored. CPU and wall limits are **aggregate** per stage as stated; display both, plus any uncapped lightweight development commands. No silent top-up.

| Substage | Hard resource ceiling | Behavior |
|---|---:|---|
| P7a static audit/test/regression | 1,200 process-tree CPU-s, 2,400 wall-s; existing full-suite replays required | Stop on math/semantic failure |
| P7a controlled trainings & diagnostics | 6,000 CPU-s, 12,000 wall-s, **0 teacher calls** | Primary A/B/C and B/C-no-coupling first |
| P7a GIF/debug rendering | 700 CPU-s, 1,400 wall-s | No fabricated trajectories |
| P7b static admission | 1,200 CPU-s | No teacher calls unless the unchanged teacher collector is explicitly launched |
| P7b new teacher collection | **20,000 CPU-s**, **48,000 wall-s**, 1 worker | 48 roots max, 32 teacher queries/root, **1,536 queries max**, 4,608 declared seed units max |
| P7b per-root guard | **1,000 CPU-s**, bounded by aggregate cap | Stop/censor honestly; no unapproved retries |
| P7b per-batch guard | 5,000 CPU-s per 12-root batch, 4 batches max | Wave-1 gate after batches 1–2 (24 roots) |
| P7b training/ablation | 12,000 CPU-s, 24,000 wall-s; 0 teacher calls | Three-seed primary and essential controls first |
| P7b independent 2D one-shot | 9,000 CPU-s, 18,000 wall-s; ≤36 episodes | Max episode 250 CPU-s; failures count |
| P7b GIF/report rendering | 1,800 CPU-s, 3,600 wall-s | Draw only authentic evidence |

Teacher **policy-internal** seed/node/skill limits remain exactly pinned to `2D-ABC-OPNEG-v1`. A P7 stage cap is not permission to replace them. Priorities when nearing cap: (1) soundness/regression, (2) unambiguous labels and minimal necessary z pools, (3) balanced root evidence/gate, (4) matched primary training and no-coupling controls, (5) fresh one-shot runs, (6) optional ablations and cosmetics. A planned root not run is `NOT_RUN`, never a negative. If a per-root cap prevents a clean operational decision, query is `UNKNOWN` (with censor provenance).

## 8. Visualizations — retain P6 GIF strengths, add causal debugging

Create an index `visualizations/p7/README.md` with SHA-256 sidecars and paths to reproducible source trace/checkpoint/config data. GIFs are mandatory for every successfully collected root with a witness and for each trained main model; if collection is gated off, produce P7a diagnostic GIFs from existing records.

**P7a diagnostics:** `scene_edits_A_B_AB.gif` displaying fixed robot q0 and exact edited geometry; teacher original/singleton/joint outcomes, each slot's distinct features and **predicted** scene marginal; `P7a_loss_gradients.gif` with per-term loss, gradient norms and clip fraction for A/B/C; `B_C_coupling_ablation.gif` showing one root's predicted marginals, κ, and HO/quadratic/no-coupling modes at checkpoints. Label these **diagnostic renders**, not new robot execution.

**P7b per root:** initial scene, predeclared query catalogue/status grid, authentic witnessed complete 3R pick/carry/place/retreat/target GIF (up to four moves), same-endpoint order comparison with non-witness side a static labeled status panel, hypothetical target-only edits with label `HYPOTHETICAL SCENE EDIT — NOT ROBOT RELOCATION`, selected order/destination ghosts labeled `PROPOSED, NOT EXECUTED` unless a matching trace exists.

**P7b per model:** A/B/C training snapshots, common-root side-by-side `p_R`, per-edit outcome marginals, `κhat`, selected number of moves, predicted travel, proposal ranking and equal-budget Boltzmann samples. Show certified vs budget negative separately, preserve exactly recorded physical q/object/gripper/attachment arrays when animating a successful trace. At least one GIF must show **a model-chosen genuinely new one-shot execution**, if any occurred; if not, mark `NOT_RUN`, not an old replay. All graphs fixed axes and root provenance; test first and last rendered frames.

## 9. What constitutes scientific PASS, PARTIAL and claims

**Engineering `P7A_PASS`:** real corrected edit-specific factor inputs, faithful explicit factor accounting and distinct/sound ablation modes, root-level scene consistency, synthetic and real micro-overfit, correct exact joint z math and clean tests, auditable loss norms and training. **This does not mean coupling has been proven useful.**

**Collection `P7B_COLLECTION_PASS`:** both waves completed under gates with all sources and output hashes preserved. If wave-1 gate fails, `P7B_PARTIAL_STOP`, not “all P7 passed.” A complete 48-root dataset lacking one κ sign or alternate verified repair length is at best **coverage-partial** for that hypothesis even when every query decided.

**Learning claim `CAUSAL_INTERACTION_GENERALIZATION`:** only when unseen roots contain several observed κ signs and predictions distinguish them with adequate sample sizes, good calibration and reported CIs. To claim **coupling helps**, retrained B/B-no-coupling and/or C/C-no-coupling must improve held-out root metrics at comparable capacity, labels and compute. If no-coupling matches or wins, **reject the coupling advantage**, even if full B scores best among A/B/C.

**Planning claim `LEARNED_REPAIR_SUCCESS`:** requires truly model-selected independently executed repairs with full target+safe retreat and fair baseline budgets, including abstain/failures in the denominator. `MINIMALITY` only means *restricted catalogue* or *best verified under declared search*; never global minimum if shorter unknown/unexplored solutions exist.

**Architecture selection:** determine by independently verified episode success under matched cost first, then calibrated ranking, joint travel and displacement, then explanation accuracy. If no learned model beats strong geometry/ordered-search controls, retain the simpler effective method and report the negative result. C's underperformance must be investigated, not hidden; if its representation is correct but inferior, say so.

## 10. Completion artifacts, integration commands, commit hygiene

Expected *small* new artifacts in conventional project locations (adapt to actual repo):

- `instruction-phase-md/P7_Causal_Representation_Optimization_Diverse_2D_Evaluation_Execution_Contract.md` (user-supplied, **do not edit**); `responses-phases/0022_P7a_representation_and_optimization.md`; `responses-phases/0023_P7b_diverse_roots_training_execution.md` **only if P7b actually starts**; monotonic immutable report numbers if 0022/0023 already taken.
- New versioned P7 configs and at most a handful of `p7_*.py` modules; small tests covering factor mapping, scene-root consistency, completely disabled coupling, z/masked gradients, κ signs, same-endpoint order and one-shot boundaries.
- `runs/p7/audit/`, `runs/p7/a_training/`, `runs/p7/plan/`, `runs/p7/collection/`, `runs/p7/training/`, `runs/p7/execution/`; SHA-256 manifests, exact source/seed/policy/budget hashes, root/split/category/provenance ledger; figures/GIFs and index under `visualizations/p7/`.
- One README summary of **what is now actually being learned**, which is a scored candidate sequence, typed conditional outcome probabilities, per-edit and omission contrasts, interaction/consistency metrics and first-witness robot cost — never learned continuous trajectories, discovered universal causes or globally minimal TAMP solutions.

Before beginning expensive work: run named commands in existing repo (discover actual CLI arguments; do not invent): historical regression + 6 replays, G4B exact tests, P6 corpus read-only integrity checks and P7 unit fixtures. After code changes rerun complete tests. All nonzero exit codes, partial test runs and resource overshoots are surfaced immediately.

**Report each stage:** original vs new SHA, exact executed commands, test counts/exit codes, phase guards, effective CPU/wall and spawned planner calls, decided UNKNOWN/masks, observed κ-source table by independent root, order/omission/cost/alternative-repair witnesses, model losses and seed variation, calibration, gradients, explicit z distribution, no-coupling truth tests, fair controls, root-cluster confidence intervals where valid, authentic GIF list, one-shot outcomes and limitations.

Selective stage and commit/push the authorized code and evidence if git conditions permit; **do not stage historical tracked PDF deletions, P6 evidence or untracked user files**. No force pushing. If root problems, inspect and report instead of rewriting Git history.

**End the stage with an explicit `PASS / PARTIAL / BLOCKED` and `STOP`.** G5/G6, further dataset enlargement, revised teacher policy, 3D and physical hardware require fresh authorization.

## 11. Ambiguity-resolution ledger (do not silently reinterpret these answers)

**What is the learned state?** In A, an ordered repair and ideal prefix/endpoints are inputs to a learned scorer; there are no explicit Bernoulli outcome spins. In B/C the typed 0/1 `z` fields represent hypothetical task/repair/omission *outcomes* (equivalently ±1 after a transformation), with jointly trained neural factor weights. These are not learned obstacle-on/off bits. The hypothesized `z` is summed over at inference; teacher observed `z*` is only in supervision.

**Is five necessary?** Five is the currently approved **conceptual B/C feasibility-factor decomposition** (static, sequence, scene, omission, coupling). P7 does not run an uncontrolled redesign contest. A compact mathematical implementation is allowed *only when its coverage, limitations, variable scopes and tested equality to the specification are explicit*. Travel is a separate preference/cost output.

**Is the coupling what creates κ?** Not necessarily. A **nonlinear edit-conditioned scene model** can learn `κ` from four separately predicted outcomes. A coupling effect is supported only by matched tests of joint outcomes/repair selection versus the fully disabled-coupling control, not merely nonzero κ values.

**Does a scene edit require the robot to move the obstacle?** No. It is a target-only outcome after a predeclared hypothetical pose edit with the robot fixed. The edit's resulting *poses* are allowed hypothesized model inputs; an actual successful relocation witness is required for any claim that the robot can execute the change.

**Can the same edit have a different physical answer for a different candidate r?** No: for a fixed root, q0 and prescribed edit I, the physical target-only result is invariant to which unrelated repair is under consideration. Model parameterizations that yield `p(zS|r)` variation must explicitly name it as a conditional belief issue and expose or correct it; do not show different 'causal effects' for the same experiment as if both were ground truth.

**Do we exhaust all IK or trajectories?** No. We use all **declared 48 grasps and pinned planner seeds/budgets**; a witnessed alternate route counts as feasible and is recorded. Clean budget exhaustion is **operational failure only**; global geometric infeasibility of all possible paths is not established by RRT timeout. Our models learn outcome consequences/cost from such teacher runs, not a continuous trajectory policy.

**Are four moves globally minimal if deleting any one fails?** No. Each leave-one-out label proves only **within that specific sequence** and policy (or certificate scope). Another destination, grasp, path, object or order may achieve the goal with fewer moves. Only finite-catalogue minimality or checked best-known search may be reported.

**What does the probability mean?** `p_R` is a learned/calibrated model estimate of full repair success under the fixed protocol. `P(z|r)` contains B/C predictions for multiple typed outcomes. Boltzmann marginal `P(r)` is a candidate-pool-relative sampling preference, **not** automatically a calibrated real-world success probability. Raw energies across different architectures are not directly comparable.

**What if any outcome is UNKNOWN?** It remains missing/censored, with masked direct loss, and makes the corresponding **fully decided joint pool ineligible**. Do not impute, exclude the whole root from other valid supervision automatically, or promote an unknown to negative. The false-negative risk of operational labels must be documented and ablated.

**What if a certificate is unavailable?** Keep the record operational/UNKNOWN as appropriate. Never add a place-side certificate without a sound proof over the entire declared action family. A diagnostic proof failure is not a failed project; it limits the claim.

**Do all new roots need the intended κ/order/alternative outcome?** No. Construction intent is predeclared, then reality is recorded; realized labels determine the gate. Failed constructions, static rejections, timeouts and negative outcomes stay visible in the ledger. The agent must not tune generation using sealed test results or relabel scenarios to meet quotas.

**Why two waves?** To stop a systematically uninformative generator early. Wave 2 consumes **new** roots only when wave 1 shows balanced outcomes, distinct physical mechanisms and actual shorter/longer verified repair alternatives. Gates are not retroactively relaxed just because total CPU remains.

**What about the prior P6 holdout?** It has already influenced our scientific diagnosis, so it is no longer a clean **new P7** test. It may be displayed as a legacy diagnostic, never recycled as fresh untouched evaluation. All P7b test lineages and correlated descendants remain sealed until predictions/configs are frozen.

**What if C stays worse?** Report it. Verify it did not double count order, suffer numerical clipping or use extra/missing labels. Once those are controlled, a negative C result is a valid architectural conclusion; do not add hidden capacity until C wins.

**What if B-no-coupling wins again?** Report it and reject the proposition that cross-outcome coupling is beneficial on the tested distribution. B could still be the best *edit-conditioned* predictor without requiring the stronger coupling hypothesis.

**What if a geometry search baseline wins?** Report that for known-geometry, access-dominated scenes the exact geometric controls are stronger. Do not describe privileged screens as a deployable learner trained with the same information, or call model ranking an improvement without comparable verifier CPU.

**When can new teacher collection, 3D or physical xArm begin?** P7b collection only after P7a gates pass, within the explicit authorized P7b ceilings. 3D and hardware remain forbidden without a **new** request. One-shot P7b refers to independent **2D simulator** execution only.
