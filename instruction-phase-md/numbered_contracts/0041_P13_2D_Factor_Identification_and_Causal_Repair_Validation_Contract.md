# P13 — 2D Factor Identification, Causal-Interaction Stress Tests, and Repair-Utility Validation

**Binding scientific / implementation contract for Claude Opus 5.5 High**  
**Project:** `Narendhiranv04/latent-causal-tamp`  
**Starting commit:** `021cd00461bfb346053c991303385a9e467769f5` (verify local HEAD, origin/main, manifests, and unstaged user changes)  
**Scope:** **2D only**, including proof-grounded physical counterfactuals and strict executed repair evaluation. **No 3D migration; no D destination/recursion/execution.**  
**Mode:** staged implementation with explicit scientific go/no-go decisions. Never report a factor as useful merely because it has a nonzero weight, gradient, or in-distribution loss.

---

## 0. Non-negotiable scientific principle

The objective is to **rigorously determine and, where evidence permits, demonstrate a meaningful, reproducible contribution from each proposed component**. It is **not** to manufacture a positive result for every factor. A factor that has no independent benefit under a fair comparison must be reported as `NOT_IDENTIFIED`, `UNNECESSARY_IN_TESTED_SCOPE`, `HARMFUL`, or `UNDERPOWERED`, and may be proposed for removal in a future model revision. Existing A/B/C/D models must remain unchanged during the **frozen retrospective/confirmatory comparison**. Architecture redesign is a *separately gated, later proposal*; it cannot be used to rescue a negative test and then described as confirmation of the original factor.

Separate four evidence grades for every component:

- **Implemented:** correct mathematics, output path, factor identity, gradients, normalization, activation and invariances tested.
- **Learnable:** distinct, sufficiently powered physical examples allow the associated function to be learned above simple controls.
- **Incrementally useful:** matched training and prospective held-out testing show its removal hurts a *predeclared relevant endpoint* with uncertainty and appropriate multiplicity control.
- **Deployment useful:** it improves a downstream decision or resource metric under the real fixed selector / robot evaluator, without unacceptable regression on normal, neutral or novel cases.

None of these grades implies the next. A mathematical ablation of one module need not identify its causal necessity if other flexible modules compensate. The word “proof” refers to **exact mathematics and scoped physical certificates**; empirical utility is **evidence**, never a universal proof.

### Existing evidence that must remain intact

- P10: keyed B strict TOP1 success 0.718 versus SF 0.385 on 65 known-family blind roots; complementarity better than A on 9 H1 roots.
- P11: short-trained B fails to generalize its executed 3–4-move performance; F2 and visual input hold up, F3/F5 underpowered in 32-test correction; F1 and J not identified as useful; severe appearance changes destabilize B.
- P12: 80 new roots, 65 sound four-tuples dominated by 59 neutral κ=0, four κ=+1, two κ=−1; B-F3 apparently wins on mean per-seed absolute κ error, F5s not confirmed, and geometry TOP1 beats B on 49 fully executed roots; 31 roots remain unfinished. D and geometry trade places by cohort. Do not overwrite P10–P12 artifacts or retroactively relabel post-hoc results as confirmatory.

### Critical source-level discrepancies to resolve **before new training or teacher calls**

1. **P12 preregistration/statistic mismatch:** `runs/p12/PREREG.json` says the error of *seed-averaged marginals*, but `p12_closure.factor_tests()` computes an *average of seed-wise absolute errors*. Recompute exact intended estimand:
   \[
   \widehat\kappa_{m,r}=\frac{1}{3}\sum_{s=0}^2\{p_{m,s}(A+B)-p_{m,s}(A)-p_{m,s}(B)+p_{m,s}(\varnothing)\},\quad
   e_{m,r}=|\widehat\kappa_{m,r}-\kappa_r|.
   \]
   Preserve the previously published seed-wise-error statistic separately, with unchanged records; regenerate comparisons and exact sign/Holm tests from **frozen predictions**, no fitting or label modifications. Explain any changed verdict.
2. **κ=0 naive baseline:** evaluate the constant \(\widehat\kappa=0\) control (the class mix implies MAE 6/65≈0.092 on P12, subject to exact ground-truth verification), plus a simple independently trained/no-coupling control. Evaluate conditional by true κ and overall; do not select a κ threshold post hoc.
3. **D counterfactual query identity:** in `p12_closure.d_semantics()`, restore the stronger P11 check: same object IDs, exact parking edit destination map, query identity, initial q0, and subset semantics; not merely `n==2` and existence of `edit:A/B/A+B`. Report per-model **coverage**, `NO_PREDICTED_CLEARING_SET`, and scores on the same supported roots. Do not conflate a no-clearing-set prediction with an empty actual blocker set.
4. **P12 execution coverage:** diagnose the 49/80 complete-root selection mechanism and differential censoring, preserving frozen job order and episode identity. One interrupted launch lacks a guard record: do not infer its CPU consumption or count it as a success. Completing the outstanding 31 roots is a separate explicitly budgeted stage, not a replacement for new blind test evidence.
5. Verify 407 + 6 P12 tests and six replays; report the test suite provenance and run all updated tests together at the end.

Every correction is a **versioned addendum**; never edit historical evidence in place.

---

## 1. Precise target scientific questions and factor contracts

### 1.1 Universal task definition

Scene \(S\) consists of learner-visible 2D object geometry, robot configuration, support/goal, visual encodings and action/candidate schema. Goal: **execute a valid repair sequence, then complete the original target retrieval or pick-place task**. Training labels are from the declared robot, grasp family, scene edits and motion planner with independently verified witnesses or scope-qualified certificates. `UNKNOWN` and `NOT_RUN` are missing, **not infeasible**. `BUDGET_INFEASIBLE` remains operational only.

Let \(z_0\) denote original target feasibility, \(z_{S[A]}\), \(z_{S[B]}\), \(z_{S[A+B]}\) fixed-q0 hypothetical scene-edit outcomes, \(z_{R_\pi}\) an ordered repair outcome and \(z_{O_j}\) its j-th omission. All outcomes and exact query identities must be tracked by root. The interaction contrast is:

\[
\kappa(S;A,B)=y_{A+B}-y_A-y_B+y_0\in\{-1,0,+1\}\quad \text{for binary decided outcomes.}
\]

- \(\kappa=+1\): complementary joint clearing under the specified intervention (neither single succeeds, joint does), assuming obstructed original.
- \(\kappa=0\): no net pair contrast; multiple distinct truth patterns exist and must be reported separately.
- \(\kappa=-1\): both singles can suffice (redundancy), assuming obstructed original.

**Do not confuse the edit \(S[A+B]\) with a physically executable move sequence**, or a catalogue-relative shortest witness with a globally optimal repair. Each teacher proof must carry its precise scope.

### 1.2 Matrix — component to be implemented, activated and tested

| Component | Exact implementation to inspect | Controlled physical condition | **Primary mechanism-specific endpoint** | Required control / failure mode |
|---|---|---|---|---|
| **F1 — learned static validity** | `Shared.static`, `unique_factor.losses` static BCE, λ_static | invalid endpoints / support / overlap **and** near-valid endpoints, including cases where analytic veto does and does not fire | AUPRC, balanced sensitivity/specificity, NLL/calibration on held-out static validity; **separate** selector utility | matched B λ_static=0 retrain; analytic veto held fixed; F1 may be redundant for deployment |
| **F2 — order representation** | B predecessor module (`pairo`, `mix`, `order_s`), C GRU, B-F2 orderless | same movers **and same final endpoints**, one order witnessed, reverse sound infeasible; nontrivial 3-/4-move chains when available | paired good-vs-bad order accuracy/margin and executed choice success | B-F2, A, C, geometry; preserve endpoint identity; action-count and grasp controls |
| **F3 — scene/repair precondition pair** | `pair_scene` in `_pairs`, and named scene-query pair | proof-grounded complementary **and** redundant/neutral A/B edits with no hidden geometry leakage | preregistered paired κ error **and** four-bit feasibility log loss / pair-calibration; false-κ positive rate on neutral cases | matched B-F3 retrain, independent SF; must show gains on interaction and avoid neutral harm |
| **F4 — repair/omission pair** | `pair_omit` + keyed omission identities in `unique_factor_keyed.instances` | a verified full repair where a particular omission is sound infeasible, plus matched redundant/optional omissions | necessity/non-necessity discrimination, pairwise ranking/NLL, and selection regret due to unnecessary moves | B-F4 retrain; verify omitted subquery is physically identical; F4 may not aid selector without different action catalogue |
| **F5s — generic pairwise coupling** | `cpl` across scene-query/repair-omission variables; B-F5s removes coupling and HO | multiple interacting edits/repairs with cross-variable dependence, plus neutral controls | joint-vs-independent four-bit NLL, κ and conditional dependence; incremental utility versus F3 controls | B-F5s, B-F3, SF; capacity-controlled extra baselines; distinguish from F3 |
| **F5q — higher-order residual** | `ho_u`, `ho_s`, `ho_q` in `scene_block` and keyed blocks | independently decided three-object subset lattice, nonzero three-way finite-difference interaction with controls | 3-way contrast error / held-out subset-joint likelihood; conditional execution only where applicable | B-F5q retrain, B-F5s; **do not call higher-order necessary merely because 3-way interaction exists** |
| **DINOv2 vision** | frozen image encoder / `vproj` visual input | geometry-identical appearance variations and actual geometry differences | predictive performance on physical test, appearance invariance and geometric sensitivity | B-V0; appearance normalization controls as exploratory; masks fixed vs segmentation separate |
| **Keyed joint ontology** | `unique_factor_keyed.instances` vs unkeyed `unique_factor.instances` | repeated physical subquery listed under distinct candidate contexts; variable alias stress | exact identity invariance, NLL and repair success on duplicate/reused-query stress | B-U retrain; a null effect means additional ontology benefit unproven |
| **J travel head** | `cost` log-Huber + TOP1 second sort key | equal-length, admitted, similarly feasible repairs with **different witnessed travel** | travel regret / travel CPU and path length **conditional on success**, with success non-inferiority | no-J / shuffled-J / oracle-J (offline only); may improve cost without changing success |
| **D feasibility/blockers** | `d_blockers.ModelD`, pair vs pairless | both feasible & infeasible originals, minimal clearing sets of variable cardinality | binary feasibility log loss and feasible recall; union/necessary-set blocker F1 and exact-set on scoped parking interventions | D-pairless, geometry; D is identification-only, **not** repair/execution |

Important: F5s ablates generic pairwise **plus** HO; F5q removes HO alone. A positive F5s test does not prove pairwise or higher-order necessity individually. F3's scene pairs cannot be interpreted as universal cause identification without proper counterfactual semantics.

### 1.3 Factor-activation and mathematical unit tests (no new teacher cost)

Implement source-level numerical/mathematical audits for each factor before evaluating scientific effects:

- Name the actual source parameters and exact energy contribution for each named factor, verified from `abc7_models.py`, `unique_factor.py`, `unique_factor_keyed.py`, `p10_protocol.py`.
- Verify each factor participates in the intended root-scoped energy; test canonical query identity, permutation invariance/equivariance where mathematically appropriate, duplicate-instance invariance, exact normalization against tiny brute force, finite gradients and gradient reachability through the **actual training loss**; test B/C consistency.
- Test that disabling the factor zeros/removes **only its intended contribution** (not other modules, candidate availability or evidence paths). List resulting parameter-count changes and any reduced-capacity confound.
- Log factor activation rates and intervention opportunities per root; e.g. number of actual pair factors, omission pairs, 3-way HO variables, tied admitted selections for J, analytically invalid endpoints for F1.
- Include tests in an isolated small test module. Zero physical-planner/IK/teacher calls in learned forward and factor-scoring paths. Never use teacher results to filter test candidates before selection.

The factor-value and gradient audit establishes implementation, **not predictive benefit**. A zero factor activation on the natural benchmark requires explanation, not a “no-effect” conclusion.

---

## 2. Dataset design: distinguish true causal interactions from geometric shortcuts

**Do not repeat P12's 59/65 neutral-κ distribution as the sole test of joint factors.** Also do not generate only complementary scenes and declare victory. Use a prospective **mechanism-stratified challenge set**, paired with a **natural-mix / neutral-control holdout**. Report the two distributions separately rather than using an artificially balanced challenge-set number as population accuracy.

### 2.1 Mechanism families, with physical acceptance conditions

1. **PAIR-COMP (κ=+1):** two independently necessary clearing edits. Independently sound-certify original, A-only and B-only infeasible; witness joint A+B feasible. Examples include two separated grasp obstructions or sweep+access obstruction. Construction on development roots may be tuned; holdout classifier **may be stratified by ground-truth label only if the label-dependent sampling scheme and all attempted seeds are frozen, disclosed and analyzed as mechanism-conditioned case-control**. Prefer model-independent analytic geometries/sound prescreens when possible.
2. **PAIR-REDUNDANT (κ=−1):** either independently identified intervention suffices to make original feasible. This is needed to detect spurious “both required” in B.
3. **PAIR-NEUTRAL (κ=0):** one edit suffices and another does not, plus no-op controls. Distinguish all neutral truth patterns and include hard geometric impostors; report false-positive κ and specificity.
4. **ORDER-REV:** identical mover multiset, identical destination map and final object poses, opposing order outcomes; witness good and sound-certify bad *for the declared grasp/robot policy*. Include 3–4-action chains if actually constructible; no motion planner prefilter during model selection.
5. **OMISSION-NECESSARY / OPTIONAL:** witnessed longer repair with individually tested omission subqueries, plus repairs with provably redundant action(s) and multiple sufficient alternatives; avoid labeling omission as necessary merely because one plan timed out.
6. **STATIC/J-TIE:** static-check hard negatives and near-valid positives, and equal-length, jointly feasible TOP1-admissible candidates with different *witnessed* travel. Do not use teacher outcomes to create test-time tie-break inputs.
7. **TRIPLE-INTERACTION:** 3-object intervention subset lattice (all 8 subsets). For binary feasibility \(f(U)\), calculate
   \[
   \Delta_{ABC} f=f(ABC)-f(AB)-f(AC)-f(BC)+f(A)+f(B)+f(C)-f(\varnothing).
   \]
   Retain also controls with \(\Delta_{ABC} f=0\); no claim that pairwise NN functions categorically cannot represent these scenes. Independently enumerate/witness/certify *every* compared subset, with UNKNOWNs excluded from the particular finite-difference label.
8. **HARMFUL-RELOCATION / ADVERSE-DESTINATION:** moving an apparently relevant blocker can close a later corridor; compare both successful and harmful destinations. Separate *scene edits* from executable repairs and certify claims only at declared scope.

Use symbolic 2D geometry only where needed to create causal mechanism types; their actual truth must come from the declared physical evaluator. No imaginary “logical” ground truth in place of a witnessed/certified physical result.

### 2.2 Splits, leakage prevention and size

- **Development:** iteratively design physically sound constructors, estimate yield and cost. Labels may be used to tune development generators. Version every change and use *new*, disjoint final holdout seeds after the constructors are frozen.
- **New mechanism-balanced training:** if additional examples are necessary, construct them in a **distinct train-only split**, retrain matched B and ablations three seeds under matched budgets. Never train on future blind roots or related geometries, parent-child seeds, reused fingerprints or rendered variants.
- **Validation:** independent scene identities and lineages, used for checkpoint selection and calibration only; never select based on blind p-values.
- **Confirmatory challenge test:** predeclared roots/algorithm and scene acceptance, predictions hash/commit before label unseal, sound provenance, root-cluster testing, and a fixed test budget; require **at least 12 independent proof-grounded PAIR-COMP** roots as a *minimum yield gate*, aim **20–30** plus 12–20 each redundant/neutral and 12–20 order/omission where feasible. This target is a power planning target, **not permission to stop at a favorable significance result**. If power/yield inadequate, report UNDERPOWERED.
- **Separate realistic-mix test:** new constructor family or naturally mixed stream with no interaction-outcome stratification. Report untouched prevalence and performance. This is essential to detecting false pairwise interactions on neutral geometry.
- **Triple interaction:** minimum pilot first. Only include HO as confirmatory if enough complete eight-subset, proof-grounded roots can be obtained within budget; otherwise status `UNTESTED / UNDERPOWERED` and do not retrofit an easier endpoint.
- If several roots arise from the same parent constructed scene/geometry, **cluster statistical resampling by parent lineage**, not by nominal root id. All sampling and rejection rates logged.
- Extra difficult scenes selected by outcome/teacher are valid for mechanism-conditioned diagnostics, but cannot represent unbiased scene-distribution generalization. Disclose conditioning and avoid pooling with natural-mix results.

### 2.3 Teacher and certificate contract

- Require exact 2D robot, grasp family, fixed q0 on hypothetical edits, destination map and final-goal task definition. Record all initial configurations and final states.
- `VERIFIED_FEASIBLE`: execution witness with replayable path, candidate repair sequence, final target completion and retreat checks.
- `CERTIFIED_INFEASIBLE`: explicit accepted certificate, scope, solver family and provenance; separate link-sweep, target-pick, order-first-action and placement-level labels. Never inflate pick-side certificates into universal impossibility.
- `BUDGET_INFEASIBLE`: operational negative only; exclude from confirmatory κ, order and multiway claims. `UNKNOWN`, `NOT_RUN` are missing.
- Higher-order/root minimality: quantify within frozen finite catalogue, and distinguish from a global shortest-sequence proof.
- Immutable manifests for all teacher jobs, rejected proposals, CPU-censored outcomes, exact queries and certificate/witness hashes.

---

## 3. Freeze order, fair controls, and empirical inference

### 3.1 Required order of operations

1. Audit P12 source and fix addenda (including κ seed-averaging and D matching), with read-only regeneration; no teacher calls.
2. Build *development-only* constructors; demonstrate authentic opposite-contrast examples (κ+1/0/−1), reversed-order and omission examples. Check physical feasibility, labels, compute and sample size. **If mechanism cannot be soundly constructed, stop or reduce the corresponding scientific claim.**
3. Freeze **scenario grammar**, physical prescreens, split rosters, candidate dictionary, targeted and realistic-mix estimands, mechanism primary endpoints, correction family and resource allocation. Commit.
4. Collect/train only from train/validation roots (with independent labels). Retrain **matched** controls for three seeds and fixed/symmetric search budgets. Record checkpoint selection, data balance, calibration, early-stopping and parameter counts. Check if factors actually learn and activate on validation.
5. Freeze **test root scenes/candidates, complete trained checkpoints, thresholds, code SHA, all test predictions** before test labels are opened. Commit and verify origin/main. Absolutely no label-driven refitting of models/thresholds afterward.
6. Collect and hash-commit test teacher outcomes; unseal only after physical label commit and frozen prediction hash checks. Compute preregistered tests. Do not change test geometry, roots, masks, edits or candidate menus based on predictions or results.
7. Execute strict TOP1 on a predeclared sample/budget; optional planner-assisted G+M separately. Freeze execution jobs and complete coverage without outcome-dependent subset picking. Preserve no-fallback and SAFE_RETREAT policy.
8. Produce mechanism-wise reports and mixed-distribution trade-offs. Run all tests/replays; commit and push artifacts. State which factors are defensible and which are not.

**Avoid freeze circularity:** Teacher data needed for training may be collected before blind predictions are frozen, but exclusively for independently designated train/validation roots. Never open or condition on test-root physical labels before test predictions are committed.

### 3.2 Controls and confounds

For each factor: `on`, `off` matched retraining and (if needed) a **parameter-matched** version of the off model, e.g. widened unrelated layers (document exactly). This distinguishes removal-of-interaction from reduction in total model capacity. Other models: A, SF, C, geometry and G+M where valid. Do not use G+M as same-policy TOP1: it may try up to five planner-screened candidates, so report separately.

Predeclared comparisons:

- **F3:** B vs B-F3 on (a) complementary-case κ error, (b) neutral false-interaction error and (c) jointly defined four-bit NLL. Must not ignore a significant neutral regression while celebrating κ+1.
- **F5s:** B vs B-F5s on the same outcomes, plus block-level joint NLL. **F5q:** B vs B-F5q on three-way effects if eligible.
- **F2:** B vs B-F2 and A/C on matched reversed-order sets, including deployment choice.
- **F4:** B vs B-F4 on individually adjudicated omission necessity, plus extra-move regret in execution.
- **F1:** B λ_static on/off on static validity, plus selection-level effect when analytic veto either inactive or separately diagnosed. The analytic veto stays unchanged in deployment.
- **J:** no-J / shuffled / predicted-J on matched admitted choice sets, travel/path cost per successful repair and success non-inferiority. Oracle-J cannot be used during deployment.
- **Vision/keying:** B-V0 and B-U as capacity/scope controls; repeat mild photometric changes only as a secondary check.
- **D:** with/without pairwise blockers vs geometry on common, infeasible-only and feasible-positive cohorts. No D actions, destinations or recursive calls.

### 3.3 Statistics and thresholds

- Declare a **small primary family** before seeing blind labels: ideally (i) F3 κ+1 with neutral-specificity safety, (ii) F5s matched joint NLL / κ+1, (iii) F2 order discriminability, (iv) F4 necessity on a prespecified balanced omission set. Correct across the number of actual primary hypotheses with Holm. The exact family must be frozen in the P13 prereg—not chosen after results.
- F1 and J should have **task-appropriate primary endpoints** but may be formally secondary to the central causal-claim family; clearly delineate multiplicity families. They must not be promoted to “confirmed” via isolated uncorrected p-values.
- Paired **lineage-level** bootstrap confidence intervals, exact paired sign/permutation tests as appropriate, and three-seed variability. Test units are independent source scenes/lineages, not candidate queries or seeds.
- **Minimum practically meaningful effects** to freeze prospectively and motivate from scale/power: e.g. κ MAE reduction ≥0.10 on κ+1, omission F1 gain ≥0.05, order accuracy gain ≥0.10, NLL improvement ≥0.05 nats/root, path-cost regret reduction ≥5% while preserving success; these are suggested starting thresholds, not automatic standards—document pilot-scale justification before preregistration.
- Non-significance is not equivalence. To claim equivalence or “unneeded” quantitatively, use a powered equivalence/non-inferiority design with predeclared bounds. Otherwise say `NO_DEMONSTRATED_BENEFIT`.
- Require stable improvement **on both** a targeted mechanism-conditioned test and a realistic-mix distribution, or state explicitly that usefulness is conditional. If a factor helps complementarity but hurts the natural mix, **show the trade-off**.
- Report raw and corrected p-values, adjusted sample sizes, 95% CIs, direction by test family, effect sizes, the baseline error rates, and selection/execution effects; no rankings based solely on p-values.
- For κ diagnostics, always include **zero-interaction** baseline and stratify κ=+1/0/−1. Stratify neutral cases by their actual four-bit truth pattern.
- Joint probability NLL should be clearly distinguished from per-variable marginal BCE or sum of independent binary NLLs. Do not call the latter “joint likelihood”.

### 3.4 Definition of “factor scientifically supported”

Set `SUPPORTED_CONDITIONAL` only if: (1) factor activation and mathematics validated; (2) appropriate proof-grounded teacher labels; (3) matched retrained factor-on/off comparison; (4) preregistered, multiplicity-corrected and practically nontrivial improvement on its intended endpoint; (5) realistic-distribution harms disclosed, with acceptable trade-off; (6) any deployment claim has actual fixed-policy improvement. Otherwise choose `IMPLEMENTED_ONLY`, `UNDERPOWERED`, `NO_BENEFIT`, `HARMFUL`, or `NOT_APPLICABLE` with evidence. A factor can be useful for *prediction* but not for *TOP1 success*: report separate grades.

---

## 4. Physical execution comparisons and failure attribution

### 4.1 Completion of P12 (separate supplementary section)

- Using exactly frozen P12 TOP1 choices, complete the 31 remaining roots if within its separately designated budget. Preserve episode/candidate identity, one commitment/no fallback, independent 2D simulator evaluator, and root-level aggregation.
- No modifying existing decisions after labels known; results remain **P12 continuation** and not new preregistered P13 confirmation.
- Compute final 80-root A/B/C/SF/geometry/G+M outcomes, by X/Y family, contingency of CPU censoring, rescored confidence intervals and CPU per root/success. Treat any unresolved as failure in primary conservative analysis and separately report adjudicated-only sensitivity.

### 4.2 New mechanism test

- Strict TOP1 executed repair on proof-grounded, predeclared mechanism and neutral controls. Record choice, candidate rank, admission, abstention, repair witness, target completion, number/identity/order of displaced objects, displacements, total motion and planner calls. Never do learned precommit motion-plan screening.
- Report success by mechanism, including PAIR-COMP, redundant/neutral, reverse-order, omission, triple and adverse-destination cases; avoid collapsing into one number hiding base rates.
- Compare full B, B-F3, B-F4, B-F5s, B-F5q, B-F2, A, C, SF, geometry-only, and G+M where executable, within a bounded and fair schedule. If exhaustive ablation execution exceeds cap, predeclare an outcome-independent representative evaluation subset and mark incomplete arms explicitly, rather than performing selection based on success.
- Use actual replayable GIFs/traces for selected successful and failed physical episodes. Do not draw fictional trajectories. Keep *hypothetical scene edit panels* visually distinct from executable moves.
- Explain which model mistakes cause failure: wrong original feasibility; false κ; failure to admit feasible repair; incorrect order; omitted necessary obstacle; bad destination; execution/certificate uncertainty; planner censoring.

---

## 5. Compute proposal and stop gates

These are **hard ceilings for this handoff if adopted by the operator**; they are not estimates of necessary work. Use independent ledgers and `process_time` carefully (avoid double-counting threaded process CPU). Do not exceed existing external quotas or change them without explicit authorization.

| Category | Upper cap (CPU-s) | Hard-stop condition |
|---|---:|---|
| P12 correction + mathematical audit + regression | 4,000 | inconsistent source, hashes, or failed identity tests |
| New constructor development + physical pilot | 10,000 | no sound complementary / order / omission cases by dev gate |
| Training & matched retrained controls | 35,000 | matched architecture/seeds/budgets cannot be completed |
| Confirmatory physical teacher labels | 65,000 | insufficient proof-grounded target mix after budget; do not relax criteria |
| P12 remaining 31 execution continuation | 9,000 | frozen job identity/censoring mismatch, or ceiling reached |
| New P13 execution | 22,000 | insufficient complete root/arm coverage; report PARTIAL |
| Analysis, visualization and extra regression | 5,000 | reproducibility/plot integrity failure |

Use **batch gates**: dev pilot ≤10 roots first; freeze/author training splits; collect test in roots batches of ≤12–16 without interim significance-driven stopping; evaluate only after predeclared stopping. If one high-order family is empirically infeasible to construct, leave it `NOT_EVALUATED` rather than spending the entire 65k teacher budget. Favor non-wasteful early termination of a component **for proven impossibility/yield inadequacy**, not to inflate significance.

The caps are sufficient ceilings for a best-effort study, not a promise of powered evidence for all factors. If a cap is reached, **stop, document remaining work and present partial scientific results**. Do not launch 3D or hardware.

---

## 6. Minimal source code and reproducibility structure

Avoid another monolithic `p11_closure.py`-style script. Reuse existing tested modules. Proposed **at most four** small new top-level modules, with one dedicated test module; aim for roughly ≤350 lines per new module and explain any exception:

- `p13_scenes.py` — development and frozen mechanism grammars and shared scene metadata.
- `p13_pipeline.py` — staged construction, freeze, teacher manifests and training orchestration, no heavy model logic.
- `p13_factors.py` — numerical factor path/activation audits, corrected κ and targeted analyses.
- `p13_execution.py` — execution continuation, fixed-policy evaluation and visualization coordination.
- `tests/test_p13.py` — identity, physics-label scope, prereg κ estimand, normalization, duplicate handling and freeze integrity.

No new general framework, CLI abstraction layer, duplicated data representation, or architecture churn. If a single existing helper is the right place for a repair, change minimally with backward-compatibility tests. Version every P13 artifact in `runs/p13/`; every report in `responses-phases/`; visual evidence under `visualizations/p13/`.

### Deliverables and phase order

- **P13-0** — `0059_P13_0_P12_statistics_and_label_semantics_corrections.md`: corrected prereg vs implemented κ tests; zero-κ baseline; D exact matching; full regression / no old artifact writes.
- **P13-1** — `0060_P13_1_factor_source_paths_and_mathematical_activations.md`: explicit source-to-equation map for F1–F5q, J, DINO, keying, D; tests and activation rates.
- **P13-2** — `0061_P13_2_physical_mechanism_constructor_pilot.md`: witnessed/certified κ+1, −1, 0, ordering, omissions, F1/J opportunities, feasibility/cost and honest failed mechanisms.
- **P13-3** — `0062_P13_3_preregistration_train_validation_and_frozen_test.md`: registration before test, lineage disjointness, retrained controls, frozen checkpoints, scores and public-hash commit sequence.
- **P13-4** — `0063_P13_4_physical_test_labels_and_factor_utility.md`: independently decided labels, calibrated targeted and natural-mix comparisons, Holm-adjusted claims, factor-specific evidence and limitations.
- **P13-5** — `0064_P13_5_strict_execution_and_P12_continuation.md`: observed 2D repairs, TOP1 vs G+M, complete P12 continuation or budget-limited status, failure attribution and CPU.
- **P13-6** — `0065_P13_6_D_feasibility_blocker_and_pairwise_controls.md`: same-cohort D checks, matched A/B/C/SF attribution support and original-target feasibility, no D recourse.
- **P13-7** — `0066_P13_7_factor_by_factor_scientific_verdict.md` plus `P13_2D_FACTOR_SCIENTIFIC_DECISION.md`: one row per component, 4 evidence grades, exact support, negatives, recommendations for lean 3D model.

Gates `P13_0_GATE.json` … `P13_7_GATE.json`; immutable predictions / label manifests / `P13_FINAL_MANIFEST.json` with hashes and commits. Provide figure atlas, grounded certificate/witness cards, κ confusion/error by class and family, factor-on/off with CIs, full TOP1 outcome table, and cost/coverage plot.

### Mandatory final Claude response (not only files)

Directly print all meaningful numbers and gaps:

1. **P12 correction**: prereg seed-mean κ F3/F5 primary effects/95% CIs/raw+Holm p, existing seed-wise sensitivity, constant-zero baseline, updated interpretation.
2. **Factor dashboard**: each of F1, F2, F3, F4, F5s, F5q, DINOv2, keying, J and D pair term with *activation count*, GT evidence count, targeted effect, corrected p/CI, neutral/mixed effect, executed repair impact and honest `SUPPORTED` / `UNDERPOWERED` / `NO_BENEFIT` / `HARMFUL` verdict.
3. **Physical tasks**: positive/negative/neutral κ counts, reverse-order pairs, omission contrasts, completed triple lattices, witness/certificate provenance and coverage.
4. **Execution**: complete or partial P12 80-root continuation and new mechanism-stratified strict TOP1 A/B/C/SF/B-ablation versus geometry; G+M separately; CPU and censoring.
5. **D**: initial feasibility with feasible positives present, infeasible-only blocker F1/exact set, proof vs operational, necessary vs union and pair vs pairless; A/B/C/SF only on exact common parking-map semantics.
6. **Status**: no 3D, no new D recourse, no universal claim; exact commits, tests, replays, budgets and final recommendation on which modules would be worth carrying into 3D.

**A report asserting “all factors are proven to matter” without the preceding independent evidence is a FAILED scientific gate, even if every software test passes.**
