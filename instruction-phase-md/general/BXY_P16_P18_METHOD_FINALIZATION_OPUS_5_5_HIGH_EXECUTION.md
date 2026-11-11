# Claude Opus 5.5 High — BXY-P16→P18: Complete the Intended Approach B Methodology, Not Just Another Benchmark

**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Branch:** `approach-b-xy-v1`  
**Verified starting commit:** `954e85b82335d31d74a37ce919044f8030b003bf`  
**Authoritative scientific specification:** `Approach_B_Final_Methodology_2026-10-31.pdf` (also read the project's current methodology/implementation docs and reports 0117–0122).  
**Primary objective:** faithfully realize, test, and stress the *whole scientific contract* in that methodology: prefix-wise physically composable X, fixed-reference counterfactual Y, genuine order dependence, omissions, the root-consistent quadratic Boltzmann model, and cost-aware corrective selection on **nontrivial multi-obstacle tasks**. Do not redefine success to make the project look good.

You are acting simultaneously as robotics researcher, experimental designer, implementation engineer and skeptical reviewer. Be determined and resourceful about fixing demonstrable deficiencies, **not** determined to manufacture a positive result. **Execute all authorized development stages below, with commits and reports after each gate.** Do not merely draft a plan. If a protected experimental precondition fails, stop that gate, report exactly why, and preserve all completed work. Do not launch the final independent confirmatory test cohort.

## A. Read, reconcile, and preserve the actual methodology

Before changing code, read fully:

- `Approach_B_Final_Methodology_2026-10-31.pdf`, especially §§1–9. This is the intended **methodological contract**, though model superiority remains to be demonstrated empirically.
- `latent_causal_tamp_methodology_v1_7.md` and `latent_causal_tamp_implementation_guide_v1_9.md` only insofar as they add implementation guidance. In case of conflict, the October 31 Approach B document and versioned, audited operational protocol prevail; document conflicts rather than silently reconciling them.
- Reports `0117_BXY_P11_TRAINING_PREREG.md`, `0118_BXY_P11_1_AMENDMENT.md`, `0119_BXY_P12_TRAIN.md`, `0120_BXY_P13_FAILURE_ATTRIBUTION.md`, `0121_BXY_P14_BOUNDED_REPAIR_LEARNING.md`, `0122_BXY_P15_FRESH_COHORT_READINESS.md`.
- Relevant source: `bxy_core.py`, `bxy_f1.py`, `bxy_data.py`, `bxy_teacher.py`, `bxy_p11.py`, `bxy_p11_1.py`, `bxy_p12_run.py`, `bxy_p12_eval.py`, `bxy_p13.py`, `bxy_p14.py`, `bxy_p14_eval.py`, `bxy_p15.py`, `bxy_lb.py`, `abc_models.py`, `abc7_models.py`, geometry, scene and rendering modules.
- Reproduce all key P12–P15 aggregate figures before new intervention design; verify local/origin Git HEAD, clean repository, frozen manifests and hashes. Historical artifacts must remain byte-identical. If only partial files or checkpoints are available, distinguish verifiable versus unverified claims explicitly.

**Non-negotiable X/Y semantics:**

1. A candidate is an **ordered** relocation sequence `r=(a1,...,am)`, `0 <= m <= 6`, of object/destination actions. A complete plan may then execute **one original target manipulation**. 2D planar 3R arm, 8×8 resting-object grid; robot joint paths and attachments remain continuous.
2. `X_q=1` only when the teacher executes every corrective action in the ordered prefix **from original q0**, with the robot's achieved joint configuration carried into the next move (no q0 reset between moves), **and** verifies a collision-free, gripper-free terminal connector to the fixed target-start configuration `q_ref` in the edited scene. `q_ref` is normally q0 under the pinned protocol, but do not conflate them without verifying equality in each setup. Connector is tested at each queried stopping prefix, not between successive actions.
3. `Y_s=1` iff the **original target action** executes from fixed `q_ref` in the hypothetical edited scene `s`, with **no requirement** that the robot can actually perform those relocations. Distinct orders with the same endpoint share one Y; they can have different X. All four observed X/Y cells are valid.
4. `X_empty=1`; no-op success is `P(Y0=1)`, with nonzero target travel if verified. A complete candidate succeeds iff `X_q=1 AND Y_s=1`, under the composable witness contract. Attempted budget failures are operational `0`, never universal impossibility; unattempted queries are missing. Keep failure certificates/budget metadata evaluator-side.
5. Keep F1 analytical invalid-placement screening, F2 predecessor-aware ordered prefix X unary, F3 hypothetical-scene Y unary, F4 omissions recomputed from **S0** and scored by the **same networks** (no pair head), F5 the **one testable quadratic XY interaction**. No extra outcome variables, fictitious per-object blockers, higher-order residuals, hard-coded Y monotonicity or training-oracle features. Y need **not** turn positive after every correct relocation; sequences requiring several blockers may stay Y=0 until the final move.
6. Authoritative normalized model (temperature pinned to 1):

   `P(Y_s=1)=sigmoid(b_s)`; `P(X_q=1 | Y_s=y)=sigmoid(a_q+w_q*y)`;  
   `P(success_q)=sigmoid(b_s(q))*sigmoid(a_q+w_q)`;  
   `P(X,Y)=PRODUCT_unique_s P(Y_s) * PRODUCT_unique_q P(X_q|Y_s(q))`.

   `E_q(x,y)=-a_q*x - b_s*y - w_q*x*y` is a **local quadratic energy**. Do not mistakenly normalize each candidate pair separately, count duplicate Y nodes repeatedly or permit adding X proposals to change marginal Y.
7. Learn neural coefficients and optional *verified full-travel* estimate `J_hat`. Calculate `m` and object displacement `C_d` exactly; neither is learned. Full J includes relocation, connector and original target. Selection is an F1-admissible, frozen risk/effort rule using `-log(p_success)+alpha*m+beta*C_d+gamma*J_hat` and optional validation-frozen `eta`, with an explicit abstention convention. No online motion generation in the learned scorer.
8. We are entitled to say the factorization is **diagnostically useful** when supported, but cannot claim quadratic coupling is necessary, causal identification is proven, or learned travel globally optimal. If the matched uncoupled or DIRECT baseline is better, that is the result.

**Existing immutable checkpoints/data:** P-min X=2,222; Y=1,866; paired=2,222; complete J=1,452; no-op J=142; development 176 train/21 val; 34 exposed historical test roots excluded. P12 108 runs; P14 75 runs; P15 development pilot 28 scenes, 514 queries. All remain historical evidence, never rewritten.

## B. Why this intervention is necessary (reproduce, don't assume)

P13: XYQ predicts roughly the same positive edited-Y shift for good and bad edits. Within-root edited-Y AUROC ~0.48, Y0 held-out AUROC ~0.69, selection penalties reject real repairs, certified order ranking close to chance. P14: adding contrast loss CON and explicit geometry GEO improves within-root edited Y AUROC to ~0.65 and correct-repair selection, but the full CON+GEO arm increased infeasible-root repair by **+0.200** while also increasing unnecessary repairs on feasible roots **+0.112**, violating the predeclared +0.05 guardrail. It still fails to identify harmful Y=1→0 edits (~0.14 direction agreement). P12 did not support quadratic coupling versus capacity-matched uncoupled. P15 generated only **one** verified K2 scene in 28 and 21/28 K0, despite intending harder examples; the frozen 360-scene confirmatory plan predicts only ~30 K≥2 using a tiny pilot and must NOT be launched casually.

The goal is **not** just new loss weights. It is to make the intended problem learnable and independently testable: physical multi-blocker access, safe actual sequences and connectors, distinguishing helpful from harmful edits, valid counterfactual X/Y pairs, and order-sensitive execution. Treat a model/data mismatch, teacher-policy noise, candidate recall and calibration as separate possible explanations.

## C. BXY-P16 — Methodology fidelity + hard-scene generation, development only

### C1. Build a requirements-to-evidence matrix

For **every methodology requirement**, record: exact semantics, existing implementation, existing tests, evidence count, observed failures, confidence, missing work, and the minimal test needed. Include F1–F5, every X/Y cell, Y shared across orders, no-op, physical connector, 1–6 prefixes, K0–K4 coverage, redundant/harmful edits, omission outcomes, physics versus search-budget failures, candidate generation, travel, and teacher/learner separation. A codepath existing is *not* experimental proof that it works; mark `IMPLEMENTED_UNTESTED`, `EVIDENCE_WEAK`, or `SUPPORTED` accurately.

### C2. Make V2 learner inputs genuinely label-free

Implement a minimal adapter accepting P15/V2 and forthcoming V2.1 roots without reading `labels`, old catalogue `role/minimal/y_full`, `travel`, `failed_step`, `verified_K`, teacher outcomes/witnesses or construction-intent labels. Compute the same **frozen input representation** (including DINOv2 visual features) from rendered original scenes, object geometry, robot q0, goal and query actions. Preserve q_ref as an explicit input when it differs from q0. Match old V1 tensors for equivalent scenes to numerical tolerance; check renderer/version identity; freeze DINO weights, preprocessing and feature-cache keys. Compare with a geometry-only control if rendered vision creates leakage/confounding. Cache safely by outcome-free scene hash; tests must mutate all privileged metadata without changing model inputs, scores or selections. Never pretend zero image embeddings reproduce a trained DINOv2 model.

### C3. Explain the generator failure and construct V2.1 with real difficulty

P15's nominal-sweep blockers can be bypassed through other supported side grasps or transfers. Do not solve this with outcome-guided witness chasing disguised as a blind generator. Design **physically motivated obstacles that close alternative grasp/motion modes**: occupied target-access corridors, multiple plausible grasp approaches blocked, goal-side constraints, nested access, interference from a first relocation, scarce safe parking spaces, and fixed geometry that forces genuine sequential access while leaving the task solvable. Use the existing 3R arm's actual geometry, support checks and continuous collision checker. Preserve the teacher and q_ref protocol.

Generator MUST produce meaningful, explicit phenomenon families:

- Initially feasible no-op cases and **harmful relocations** that can turn Y0=1 into Y_edit=0. Include neutral/safe edits, so learner cannot use a universal "edit always helps" shortcut.
- Y0=0 with a **verified feasible single repair**, and Y0=0 with 2-, 3-, ideally 4-step *verified catalogue* repairs; include partial prefixes that remain Y=0 until enough obstacles move.
- Candidate contrasts: same object/different destinations (good versus wrong/blocked); necessary versus unnecessary moves; full versus single-action omissions; multiple placements yielding identical endpoint Y.
- **Both F1-admissible orders** leading to the same final object arrangement but different **measured X** outcomes, with an independently reproducible certificate when possible. An F1-invalid reversed order is a hard-screen test, not evidence of the learned order factor.
- Connector-sensitive cases where relocating objects succeeds but the terminal connector to q_ref fails; record whether certified or teacher-budget-limited.
- Realistic redundant moves and distractors, and all four X/Y cells in a nontrivial number of independent roots.

Enumerate candidate sequences from geometry only; do **not** use actual labels to decide proposal membership/order/destination. Ensure fair proposal coverage across mechanism families and a predeclared candidate/query cap; quantify generated versus screened candidates, fraction with any verified repair, sample difficulty, rejections and budget limitations. An "intended K" is **not** a verified K; the minimum number of positive complete candidates is only *minimum verified within this finite catalogue*. If a global necessary-move claim is desired, require certified exclusion of all shorter relevant alternatives and disclose the search domain.

Include prefix-complete supervision **where explicitly budgeted and feasible**: for selected length-2–6 candidate sequences evaluate X and Y for each stopping prefix and exact omitted alternatives, while deduplicating shared Y. If query caps (historically 12 candidates / 36 queries per root) make this impossible, design a predeclared stratified query budget rather than silently dropping critical prefixes. Report coverage of each prefix length and omissions.

Before any teacher labels, create extensive geometry and property-based tests, stress deterministic generation using only outcome-free checks, freeze at least one candidate design, record construction failures and show 2D visuals of scenes and target/parking regions. Never use a teacher label to change a *frozen* development catalogue; if revision is warranted, freeze a new **development** version with separate manifests and logs.

### C4. Iterative bounded development pilot (NOT confirmatory)

Perform up to two **predeclared, separately versioned development-generator iterations** if the first pilot fails to yield informative cases, within the same combined authorized resource ceiling. For each iteration: pre-label freeze geometry/candidates/seeds, run bounded labels, summarize actual Y0 and X/Y cells, independent complete witnesses, realized K, order-discordance, harmful edits and missing queries; propose a justified revision only for the **next** development wave. Retain all failed/rejected attempts. Never retroactively suppress easy/failed scenes or select a test cohort based on model performance.

Targets are **engineering readiness criteria, not outcomes to fabricate**: aim for at least 60 independently generated labelled development roots, at least 20 initially infeasible, at least 12 with verified K>=2 within the catalogue, multiple truly F1-admissible same-endpoint X-discordant pairs, and at least 12 independent roots containing Y0=1 / Y_edit=0 harmful-edit contrasts. These cannot be guaranteed. If the authorized pilot does not meet them, report `DATA_READINESS_FAILED` with evidence and stop expansion; never falsely call the domain hard.

### C5. P16 artifacts / gate

Use small, versioned modules (prefer `bxy_p16.py`, `bxy_p16_inputs.py`, `bxy_p16_viz.py`; no giant monolith). Output `responses-phases/0123_BXY_P16_METHODOLOGY_FIDELITY_AND_HARD_SCENES.md`, machine-readable requirement matrix, generator seed/scene/catalogue hashes, per-query labels/witness hashes, physical audits, 2D animations or informative stills and >=8 scientific plots/panels. Run focused, full relevant regression and six archived replays. Commit and push with exact SHA. The next gate needs a new frozen development manifest and P16 data-readiness decision.

## D. BXY-P17 — Learn the full methodology on informative development evidence

**Enter only if P16 data-readiness is demonstrated** (or document and obtain a versioned alternative scientifically justified criterion **before** looking at model results). Do not perform heroic model fitting on a generator that fails to create the intended task.

### D1. Freeze experiment before any new optimizer step

Build family-grouped, mechanism-aware cross-fitting over historical development and *new development* roots, isolating whole original scenes, variants, different action orders, omissions and renderer versions to the same fold. Record independent-root counts by difficulty and mechanism. Keep legacy exposed test roots and reserved `bxyg2confirm` namespace untouched. Separate **training-only development roots** (can be balanced/oversampled) from predeclared **held-out development folds**. Use nested/inner-fold validation for loss weights, stopping and selection-threshold tuning; do not tune on the outer fold. Historical data has outcome-guided candidate composition; explicitly analyze historical and outcome-blind V2.1 performance separately. No label-conditioned candidate proposer in inference.

### D2. Scientific issues to address, one at a time

1. **Y-head discrimination, especially harmful edits**. Add a *symmetric, within-root* Y-contrast auxiliary that explicitly sees both `(Y0,Yedit)=(0,1)` and `(1,0)` plus `(0,0)` and `(1,1)` controls. Pair/oracle outcomes are labels only, never features. Keep original exact joint observed-data NLL as the core; contrast loss is separately stated. Design scene-feature improvements using only geometry/vision available at inference; avoid encoding true swept collision/witness paths as hidden oracle features. Report edit sign agreement broken out by the four label transitions, not pooled accuracy alone. Report both within-root AUROC and calibrated probabilities.
2. **No-op versus repair decision**. Stop teaching the network "edits generally help". Evaluate per-root base-rate shift, loss calibration, harmful-edit prediction, and a probability-consistent comparison of `P(Y0)` with `P(X,Y)` for proposed repairs. Ensure the F1 and no-op definitions remain correct. No arbitrary optimistic additive constants to repair probabilities. If tuning selection hyperparameters, use inner folds, predeclared grids, a constrained objective and root-level honest evaluation.
3. **Genuine order and prefix reasoning**. Evaluate F2 on valid same-endpoint X-discordant orders and compare order-aware F2 against a **capacity/feature-matched order-invariant control**; study whether the available ideal-prefix encoding can resolve state-dependent achieved-arm effects without secretly using teacher trajectory state as an input. If observability fundamentally limits order inference, say so. Use measured order pairs and prefix-complete evidence, not only F1-rejected examples.
4. **F4 omissions and multi-step necessity**. Explicitly train/evaluate on recomputed omissions and prefixes with shared F2/F3, not a new omission head. Require Y changes on both removal directions where available; no imposed per-step monotonic increase, because intermediate necessary movements may not individually clear the target. Report multi-step final-success and each prefix Y in representative scenes.
5. **Quadratic coupling as a test**. Keep the XY head in the primary method for scientific evaluation; compare matched `w=0` (including scene-aware capacity control) with exactly the same GEO/CON/data/compute. The presence of w or its magnitude never establishes benefit or causality. If matched uncoupled wins, mark coupling unsupported and recommend dropping it from deployment without deleting its experimental evidence.
6. **Travel-aware selection**. Preserve full witnessed `J` and `J_hat` head, but isolate optional travel auxiliary training from adding travel to selection. Assess travel on **matched successful cases**, and report success-versus-travel Pareto curves. Never reward a method for being shorter only because it avoids difficult but necessary repairs. No J labels on failed executions.

### D3. Matched frozen ablation menu (adjust only prospectively)

Unless P16 diagnoses a compelling contradiction, use at most **six 5-fold × 3-seed model arms = 90 runs**:

- **A DIRECT-GEO**: direct full-success model with same original-scene/edited-scene geometric information available to the XY models, matched capacity or carefully reported differences. It must not get worse information solely to make factorization look strong.
- **B XYQ-BASE**: unchanged quadratic architecture, same new data, original exact joint loss, no extra contrast; provides matched baseline.
- **C XYQ-GEO-CON**: P14's best idea with same frozen P14 contrast definition, retrained on the same new data; proper reproduction.
- **D XYQ-GEO-SYM**: same geometry, new explicitly symmetric harmful/helpful within-root contrast, loss and sampling policy frozen in advance (strong hypothesis).
- **E XY-UNC-SA-GEO-SYM**: capacity/feature-matched uncoupled control for arm D.
- **F XYQ-GEO-SYM-noJ**: travel head loss off, probability/selection ablation; use gamma=0 for clean travel-blind comparisons.

If a dedicated order-invariant matched control is scientifically more valuable than one above, specify which is replaced **before launch**, why, and keep the total roster/caps fixed. The F2/order test should otherwise remain a frozen evaluation-only comparison and be marked limited by absence of a trained control. Do not opportunistically add arms after inspecting results.

**No more than two prospectively chosen contrast-loss settings** using nested early-stopping training, and no post hoc test-root tuning. If the planned compute cannot cover all 90 paired runs, lower the number of arms prospectively and preserve complete matched seeds/folds; do not prefer incompletely evaluated favorable arms. Make the original `L_joint` and additional auxiliary terms explicitly separable in logs. Preserve root-unique marginalization and attempted=0/missing=absent semantics. Select a single frozen primary decision rule on inner-fold development only, with a declared maximum unnecessary-repair guardrail; report Pareto/frontier sensitivity separately.

### D4. Fair evaluation and success criteria

Pre-register *before P17 training*:

- **Primary task endpoint:** verified corrective-selection success on **initially infeasible independent roots**, with explicit candidate availability and abstention/no-op counts.
- **Safety / economy:** unnecessary repairs on initially feasible roots, unnecessary failing repairs, number of actions, displacement, full witnessed J; distinguish harmless but unnecessary from harmful moves.
- **Representation:** Y0 AUROC + calibration; edited-Y within-root AUROC; edit sign accuracy for `(0→1)` and `(1→0)` separately; order concordance on truly admissible same-endpoint discordant X; omission contrast sign accuracy; K1/K2/K3/K4 with actual independent n; root-averaged/pool LL, Brier, ECE.
- **Controls:** DIRECT, no-op, shortest, displacement, travel-blind, outcome-blind proposer oracle availability and verify-first evaluator-only ceiling; count teacher/planner calls and verification costs, report physical replay failure phases and certified versus budget negatives.
- **Uncertainty:** family/root-cluster paired bootstrap and per-seed agreement; predeclared 95% CI, multiplicity where applicable, effect sizes with appropriate uncertainty. Do not pretend 5 K>=2 roots provide a robust claim.

Use a meaningful explicit gate: to claim "IMPROVES WITHIN GUARDRAIL", candidate-vs-matched baseline infeasible-repair success `Delta` must have paired 95% CI lower bound >0, point gain >=0.10, and its **unnecessary-repair point increase <=0.05**, with confidence interval also transparently reported. To claim **SUPERIOR TO DIRECT**, require independent evidence of advantage under comparable or better unnecessary-repair rate (with a predeclared paired uncertainty criterion). A result may be `PROMISING_BUT_GUARDRAIL_FAILED`, `INCONCLUSIVE`, or `NEGATIVE`. Do not alter the metric or guardrail retrospectively or collapse success and false repair into a flattering pooled score. Report any difference between beneficial prediction and beneficial physical selection.

### D5. P17 artifacts / gate

Use minimal training/eval adapters, reuse P12/P14 runner and hash-based resume rather than rebuilding everything. Outputs `responses-phases/0124_BXY_P17_TARGETED_LEARNING.md`, frozen `TRAINING_DESIGN_P17.json`, separate authorization, per-run ledgers/checkpoint hashes/predictions, a real-world-interpretation failure gallery, at least 10 useful scientific plots including many 2D scenes, complete matched contrasts, and a recommended *single* candidate and *single* challenger. Verify relevant tests and six archived replays. Commit and push.

## E. BXY-P18 — Final research readiness and honest model freeze (NO confirmatory collection)

1. If and only if P17 produced a model meeting the predeclared development gate, freeze all proposed models (at least winning XY, matched DIRECT and uncoupled control), selection rules, preprocessing, features, seeds/ensembles, versions, output semantics, and one-shot confirmatory metrics. If none meets the gate, freeze **negative result and best diagnostic model**; do not silently promote it to a successful "final" method.
2. Generate and check, **without executing**, an independent outcome-blind test-cohort plan. The existing P15 `CONFIRM_PLAN.json` must remain immutable. A stronger V2.1 plan uses a **new namespace, seeds and version**, informed only by development physics/difficulty and never test-model performance. Document how to handle construction rejects, realization shortfall, K strata, censored queries, budget failures, sample-size uncertainty, independent family clustering and predeclared stops. Do not inspect or generate the reserved `bxyg2confirm` cohort accidentally.
3. Confirmatory analysis must freeze: primary 2-sided/one-sided tests as appropriate, root-family confidence intervals, direct/uncoupled/no-op baselines, model failure under corpus shift, catalogue availability, runner/teacher cost, full physical replay and zero test-look tuning. Report K>=2/K3/K4 counts actually observed even if low. A 360-scene plan based on 1 observed K2 case is **not** a guarantee of adequate multi-step power; if insufficient, state so and propose power/precision justified sizes without making fake promises.
4. Explicit **go/no-go**: `READY_FOR_INDEPENDENT_CONFIRMATION` only if full label-free adapter, valid prototype generation, sufficient relevant hard-scene coverage, frozen reproducible models + matched controls, and independent plan integrity all hold. Otherwise `NEEDS_MORE_DEV_DATA`, `LEARNING_HYPOTHESIS_UNSUPPORTED`, or `BLOCKED_PROTOCOL` with specific requirements.
5. Publish `responses-phases/0125_BXY_P18_METHOD_FINAL_READINESS.md`, detailed implementation-vs-methodology compliance checklist, a complete scientific results digest, final architecture diagram, clear 2D visualizations, train/test custody manifest, hashes, and compute-budget request for a **separately authorized** confirmation. Commit and push; STOP.

## F. Hard budget / authorization / execution protection

**By pasting this prompt, I authorize only the bounded development work described below; the final independent confirmatory cohort is NOT authorized.** Implement *new*, versioned manifests first (do not flip prior authorization flags), and enforce these as hard limits with durable CPU/wall ledgers across resumes, memory gates, per-run/root ceilings, atomic hashes, fault injection and safe worker shutdown. If limits are insufficient, stop and report a revised resource request; never silently expand them.

| Resource | P16 new development teacher + scene construction | P17 model training + evaluation |
|---|---:|---:|
| Aggregate CPU hard ceiling | 24,000 CPU-s including construction and evaluations | 48,000 CPU-s including evaluations |
| Per-root / per-run hard ceiling | 800 CPU-s per labelled development root | 1,500 CPU-s per training run |
| Max concurrency | 4 CPU workers | 4 CPU workers |
| Cumulative wall hard ceiling | 14,400 s | 21,600 s |
| Maximum distinct new labelled development roots | 120 | Training on permitted development roots only |
| Maximum registered model training runs | — | 90 |
| Motion teacher/query budgets | exact existing P-min limits; no increase | no motion-teacher queries |

These are independent stage ceilings, **not additional to any prior unused budget**. One thread per worker, no GPU needed/authorized, no third-party paid API calls, no 3D work, no independent test collection. A problem-specific exception requires a separate user authorization. Make CPU/wall metrics auditable; do not infer that unfinished work may consume the remaining ceiling opportunistically. If fewer than the planned 60 informative roots are acquired, declare the learning stage not ready and preserve completed work; do not waive constraints to produce a positive story.

## G. Mandatory engineering, visualization, and report discipline

- Each gate: **design → preregistration + tests → separate authorization (when needed) → execute → evaluate exactly as frozen → report + figures → full relevant tests + six archived replays → commit + push → verify origin HEAD**.
- Keep new code readable and small; prefer 3–5 focused `.py` modules per stage, no needless new subfolders, and no separate generic orchestration system. Existing historic scripts/files stay frozen.
- Assertions and tests must cover q0/q_ref distinction, continuous connector composability, achieved robot state across relocations, X/Y 4-state microcases, shared Y invariance, F1 admissible versus rejected orders, missing/censored observations, duplicates, six-step prefixes, harmful Y edits, label-flip nonleakage and candidate-order invariance.
- Visualize the entire physical story for representative scenes: **original infeasibility → correction prefix states → independently queried hypothetical Y at every prefix → complete robot trajectory including connector → chosen action versus successful alternative**. Overlay original/edited obstacle positions, target, q0/q_ref robot arms, collision/clearance information, and distinguish data-truth from learned probability. Use recorded physics witnesses for any "realized motion" picture; no invented demonstration frames.
- Provide figures of learner mechanism: common-Y order twins, helpful/harmful edits, K2–K4 prefixes, pairwise probabilities, calibration, selection cost/penalty, paired CI and failure analysis; include informative captions and reproducible scripts.
- Report counts of independent roots as denominator of main claims. Failed labels from bounded search remain policy-relative; only certification supports physical impossibility.
- Never modify frozen P-min, P11, P11.1, P12, P13, P14 or P15 artifacts. Do not use the exposed 34 test roots, `bxyg2confirm` namespace, or any future confirmatory labels for training/tuning.
- Stage progress at each commit: what was done, what was learned, quantitative evidence, what failed, budget used/remaining, and next bounded decision. The final answer must include exact SHA for each stage, verdict, evidence table and links/paths for all reports and figures.

## H. Final research standard

**Do not stop at building a working generator or at lowering training loss.** The central scientific goal is: given a high-level proposed obstacle-rearrangement sequence, predict (a) whether the robot can physically execute that order and connect to the target start, (b) whether the edited scene makes the original task feasible, (c) whether omitting or reordering actions changes those outcomes, and (d) which valid successful proposal is economical. Show this end-to-end on challenging, physically grounded 2D scenes, with honest controls and root-grouped uncertainty.

If Approach B truly improves, demonstrate it without leakage, favorable-only scenes, changed baselines or post hoc selection. If its quadratic component is unnecessary or DIRECT remains superior, keep the valid negative finding and recommend the simpler deployed model. **The methodology is the final intended scientific question and protocol; positive model performance is a hypothesis, not a requirement that may override evidence.**

**START NOW at commit `954e85b82335d31d74a37ce919044f8030b003bf`. Complete P16 → P17 (only if ready) → P18, commit/push, and STOP before any independent confirmatory cohort is generated.**
