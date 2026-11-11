# 0040 — P12: Independent 2D Generalization and Decisive Joint-Factor Validation

**Binding execution contract v1.0 — 2D only; evidence over architectural changes**  
**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Starting reference:** `b5d3f8504876585b758d6d9b02b785e9c7e1d990` (P11 final, `PARTIAL`). Verify live local `HEAD`, `origin/main`, ancestry and dirty state before acting; never silently reset work.  
**Destination in repo:** `instruction-phase-md/0040_P12_Independent_2D_Generalization_and_F3_F5_Scientific_Validation_Contract.md`  
**Mission:** Obtain the missing **independent difficult 2D held-out evidence**, test whether joint scene/coupling factors F3 and F5 add value on that evidence, examine realistic appearance robustness, clarify D blocker semantics, and deliver an auditable scientific verdict. **Do not force a positive result.**

## 0. Baseline facts and fixed boundary

P10/P11 are finished historical experiments; preserve their immutable datasets, witnesses, gates, figures, training snapshots, checkpoints and their disclosed blind outcomes. Important baseline facts to confirm from committed sources, **not to recreate or tune**:

- P10b: 80 train / 35 validation / 65 disclosed blind roots from known constructor families. Three-seed executed TOP1: **keyed B 0.718**, C 0.718, A 0.585, SF 0.385, geometry-only 0.446; planner-assisted G+M 0.831 on a different stronger precommit-planning protocol. B>Sf primary Holm p≈7.8e−6; B>A H1 complementarity primary Holm p≈0.0117 (9 proof-grounded roots).
- P11: all engineering checks passed (407 tests, 6 replays); P11-4 independent holdout BLOCKED. H9 severe palette remapping changes B's TOP1 on 77% of 100 roots (mean over two palettes/seeds); its original executed success is **not** an appearance-robust result.
- F2/order and visual input survive P11's **exploratory 32-test** family-wide correction. F3 scene-pair and F5 generic coupling/HO show consistent nine-root complementarity trends but remain UNDERPOWERED; F4, J practical ranking benefit and F1 repair-selection benefit are NOT IDENTIFIED. An absence of significance is not proof of no effect.
- Short-trained keyed B (trained on ≤2-move repairs) physically achieves ≈0.15/0.22 on H10_3/H10_4 vs full-trained B ≈0.52/0.78. Physical length extrapolation is NOT established. Three/four-move full-trained execution exists but minimality is only **catalogue-relative**; some labels are operational budget negatives.
- D: initial target feasibility + blocker identities **only**. 64 decided P10b blind roots (4 feasible); D F1≈0.872 and D-pairless≈0.882 over 60 complete blocker masks (39 proof-grounded, 21 operational). Attributions of A/B/C/SF are comparable to D only on the 33 physically matched 2-object edit/parking roots. Three/four-blocker masks are operational only. D's blocker definition is **union of inclusion-minimal sufficient clearing sets under a fixed hypothetical parking map**, not a global proof of physical culpability. D's pairwise interaction is not demonstrated useful.
- Existing 65 blind labels are *opened*. **Every P12 calculation on them is POST-HOC**, even if the calculation is new. New confirmatory conclusions require newly frozen independent roots and prediction hashes **before** their physical labels.

### Non-negotiable constraints

1. **Models frozen:** No architecture changes to A, B, C, SF or D; preserve B/C `ABC9K_KEYED_V1` (physical-scope factor identities), existing F1–F5 ontology, exact Boltzmann inference, pretrained DINOv2 features, checkpoint hashes, training objectives, learned selection rule. Do not implement a new model, tune on fresh holdout, introduce reward learning, or start 3D/hardware.
2. Reuse the existing **three-seed full-trained P10 checkpoints**: B (`F-K-B-s0..2`), C, A, SF, B-F3 (`pair_scene` removed), B-F5s (generic coupling + HO removed), B-F5q (HO-only removed), B-F2, B-F4, B-V0 and optionally B-U. **No retraining on any new P12 holdout**. Other matched capacity diagnostics only after a distinct budgeted approval; record original ablation parameter-count differences as a limitation.
3. No planner, IK, physical teacher, oracle labels or motion feasibility checks in *model inference, hypothetical intervention prediction, or learned ranking*. Instrument and assert zero calls; distinguish analytic geometry-only proposal/screening, D evaluation and permitted independent physical teacher labelling and actual execution.
4. For learned methods, **strict TOP1_COMMIT**: select exactly one candidate from frozen catalogue using existing calibration/selector; if abstained, count failure; never physically try alternative candidates before commitment. G+M is a **separate planner-assisted reference** (up to five precommit candidates) and must never be described as an equal-planning-budget TOP1 baseline.
5. Preserve `VERIFIED_FEASIBLE`, **scope-specific** `CERTIFIED_INFEASIBLE`, `BUDGET_INFEASIBLE` (operational), `UNKNOWN`, `NOT_RUN`, `INELIGIBLE`, and all teacher attempts. Never convert timeouts/unsolved searches into universally sound infeasibility. State whether a claim is hypothetical fixed-robot scene-edit, full executable relocation, or omission. No global shortest-move claim from a finite catalogue.
6. **No favourable test construction using learned predictions.** You may target difficulty by a **predeclared physics/geometric generator and sound analytic prescreen**, even though the resulting benchmark is conditional on that prescreen. Freeze the screening criteria, rejection counts and seed roster **before** inspecting held-out physical labels and any model result. Do not promise uniform-random distribution generalization.
7. Maintain minimal code: prefer focused small functions and a handful of compact versioned P12 modules; aim ≤300 lines/new file and avoid modifying long legacy files. Add unit tests for each actual new behavior. Avoid re-running expensive historical suites until final regression. Version P12 outputs under `runs/p12/`, reports under `responses-phases/`, visuals under `visualizations/p12/`.
8. Record all CPU-s, wall-s, source hashes, random seeds, teacher policies, guard limits, physical calls, and incomplete attempts. Count parallel process CPU **per child** (avoid the previous `RUSAGE_CHILDREN` overcount). All stages STOP/PARTIAL instead of inventing results or relaxing a frozen gate.

## 1. P12-0 — Read-only source audit and scientific preregistration draft

Read P11 reports `0045`–`0051`, `P11_2D_FINAL_SCIENTIFIC_DECISION.md`, `runs/p11/P11_FINAL_MANIFEST.json`, gates/figures, and relevant P10 originals and source. Focus on `p11_holdout.py`, `p10b_scenes.py`, `p10b_dataset.py`, `p10c_train_eval.py`, `p10d_execute.py`, `p10_protocol.py`, `p10e_report.py`, `p11_closure.py`, `abc7_models.py`, `unique_factor_keyed.py`, `d_blockers.py`, `ordered.py`, `p7_oneshot.py`, teacher policies and certificate definitions. Re-verify source of the named checkpoints and ablation hashes. Read the prior 0039 contract and the P11-4 failure modes.

**Deliver a short prereg draft before programming constructors**, with fixed research questions:

- **Primary F3:** On novel **proof-grounded H1-like complementary scene-edit four-tuples**, does full B have smaller paired absolute \(\kappa\) error than retrained `B-F3`? \(\kappa=Y_{AB}-Y_A-Y_B+Y_0\) and \(\hat\kappa\) is the same combination of frozen model marginals. Metric: root-wise \(\Delta_{F3}=|\hat\kappa_{B-F3}-\kappa|-|\hat\kappa_B-\kappa|\), positive means full B better.
- **Primary F5:** Identical cohort/metric, **full B versus `B-F5s`** (generic coupling **plus** higher-order residual removed). This tests that *combined factor block*, **not** F5 generic alone. `B-F5q` diagnoses higher-order residual separately as secondary.
- **Prospective correction:** Holm over **these two** F3/F5 primary paired tests only, α=0.05, two-sided exact sign test (ties removed), with paired root-cluster bootstrap 95% CI on mean difference. This narrower family is legitimate **only for a new prediction-frozen holdout**, not retroactively for the P11 nine-root data. Report unadjusted and Holm p, mean, CI, sign counts, ties, effect sizes, and denominators.
- **Other preregistered secondary endpoints:** fixed original/edited-scene binary NLL/calibration; H3-style same-endpoint order choice and margin; omission necessity on verified full repairs; strictly executed TOP1 with A/B/C/SF/geometry and G+M separated; 3-/4-move witnesses where constructible; error provenance, false-feasible, abstention, longer-length subgroup; no equivalence claim when B vs C ties.
- **Design maturity:** Determine *before* seeing new holdout outcomes whether enough independent, physically decided H1 roots can be created. Target **at least 24 proof-grounded H1-like four-tuples** (prefer 30–40, spread across ≥2 new constructors) and **at least 24 additional hard roots** for ordering, omissions and execution. Deliberately target variation in the *true* interaction: e.g., ≥12 complementary (κ=+1) and ≥8 redundant/neutral (κ≤0) **as planning targets**, not as outcome-conditioned inclusion rules. Report whatever classes the preregistered accepted roster actually produces; never discard roots after reading κ merely to meet a quota. These are target **realized independent roots**, not guaranteed power. Conduct power/sensitivity calculation based on already-disclosed P10/P11 effects; prespecify minimal meaningful effect and feasible N. Do not stop collecting because the observed p-value becomes significant.

**Output:** `responses-phases/0052_P12_0_scope_prereg_and_source_audit.md`; `runs/p12/P12_0_GATE.json` and draft machine-readable prereg. **Gate:** all referenced frozen checkpoints/semantics verified, conflicts resolved *before* proposing a sealed test.

## 2. P12-1 — New physics-first difficult scene constructors (DEV ONLY)

P11-4's uniformly random clutter and ring constructors yielded mostly feasible originals and a tiny, censored cost sample; this **does not prove** that an independent 2D hard-scene test is impossible. Instead devise **two genuinely new parameterized geometry grammars** encoding physical obstruction *without copying P10b template/placement logic* or consulting learned predictions. Examples to evaluate, not mandatory layouts:

- **New family X: articulated-arm swept-access gate** — blockers independently placed in two disjoint segments of the robot's swept reach corridor, with parameterized arc/orientation, target region and alternative parking clearance; goal of joint/multi-body access conflict, not a renamed P10 H1 template.
- **New family Y: offset bottleneck / obstructed approach** — target behind an asymmetric narrow approach, where collision of different robot links and nearby movable/fixed bodies creates interdependent feasibility; vary support-side, start angles, robot link geometry exposures, shape/radii and passage orientations.

**Feasibility and novelty requirements:** inspect true simulator geometry, robot link dimensions and certificates before fixing layouts. Do not claim a family is genuinely disjoint merely because its class/function name is new: record differences in **generation mechanism, obstacle topology, involved links/regions, relative placements, successful intervention type, and P10b constructor lineage**. If proposed mechanisms are unconstructible within the current robot/physics capabilities, document why and test alternate geometry-first rules **on DEV seeds only**. No 3D, no extra robot or altered physics rules.

**Prescreening:** A *precommitted sound analytic certificate* or deterministic known physical obstruction geometry may define a conditional hard-scene stratum. Prescreen must be independent of any learned model output or teacher success label. It is **acceptable** that this benchmark estimates performance conditional on being a selected hard case. Keep a ledger of **every attempted seed, accepted/rejected reason**, acceptance rate, geometry fingerprint, duplicates and overlap with all P10 families. Also include a small fixed random-unfiltered diagnostic stratum (if affordable), explicitly separated from hard-case results, to measure selection effects; do not require it to contain infeasible scenes.

Each accepted root must have a **pre-frozen query catalogue** with at minimum original target retrieval, feasible/infeasible edit candidates relevant to H1, correct and reversed repair orders where legal, omission variants where physical semantics are defined, and some 1–4-move candidates as capacity permits. Do **not** assume a multi-move witness implies shortest plan. Keep object roles, exact parking edits, start robot pose, target and SAFE_RETREAT identical across comparisons. Track exact distinct binary outcome bits and the existing `MAX_SCOPE`/exact-inference caps; FAIL CLOSED on overflow rather than silently truncating.

Development protocol: pilot at most **12–16 developmental roots**, with signed and budgeted teacher statuses. Pilot outcomes may inform grammar/policy revisions **only on DEV**, and the final experiment must freeze a **new seed roster** after changes. A static certificate's *absence* is never evidence of feasibility. Cost forecast should use per-root distributions, including censored searches, rather than multiply a single expensive root; use conservative quantiles.

**Outputs:** `responses-phases/0053_P12_1_difficult_2D_constructor_development.md`, dev plans/attempts, root atlas (including rejection examples), `runs/p12/P12_1_GATE.json`. **STOP** with a reason if an adequate independently defined hard-case family cannot be generated. Never relabel/devise an artificial “independent” family to pass.

## 3. P12-2 — Lock novel holdout and freeze predictions BEFORE physical labels

Once P12-1's constructors are viable, freeze and **commit+push** a complete preregistration (`runs/p12/PREREG.json`) before collecting *any* confirmation-set teacher outcomes. Include:

- Exact generator source hashes, parameter bounds/distributions, any allowed analytic hardness prefilter, candidate catalogue rules, labels/certificates policy, roster seeds, scene/candidate fingerprints, train/dev/holdout exclusions, root-lineage disjointness, plan budget and semantic success endpoint.
- The independent-root experimental unit, target N / resource-constrained maximum, family/H1 allocation, effect-size rationale, stopping rules and attrition accounting, outcome provenance, inferential family of **exactly two** confirmatory F3/F5 tests, and separately declared exploratory tests.
- Three frozen model seeds/checkpoint SHA256 for A/B/C/SF/B-F3/B-F5s and optional other existing ablations, same frozen calibration and TOP1 rule, same feature generation. No fine-tuning, per-family recalibration or threshold shifts; no model-conditional filtering.
- Candidate query coverage, geometry hashes, exact hypothetical fixed-q0 edit definitions, full ordered relocation queries, omissions, D parking-map compatibility or NOT_SUPPORTED. Outcome-independent eligibility must not be based on future teacher results.

Perform **zero physical/planner/IK calls** while generating and freezing the *model predictions*. Freeze per-root calibrated marginals, \(\hat\kappa\), selected TOP1 action, ranked scored candidates, abstentions and input/checkpoint hashes. Commit and push prediction hashes; only afterward allow confirmation labels. A model-specific scope failure must count as a coverage failure, never remove a hard root silently.

**Output:** `runs/p12/holdout/SCENE_MANIFEST.json`, `PREDICTIONS_FROZEN.json`, `PREREG.json`, commit SHAs, `runs/p12/P12_2_GATE.json`. Gate FAIL if predictions not frozen and remotely committed before any new test labels, or if test scenes have been selected using frozen prediction performance.

## 4. P12-3 — Independently adjudicate held-out physical outcomes

Run each query according to the frozen teacher policies, including counted process-level CPU + wall guards and deterministic seeds. Store per-query source: `VERIFIED_FEASIBLE` with actual target+retreat witness; `CERTIFIED_INFEASIBLE` **with certificate scope**; `BUDGET_INFEASIBLE` operational; `UNKNOWN` / `NOT_RUN` censored or not adjudicated. Ensure edit-only outcomes are not conflated with executable relocation outcomes.

Produce decided H1 four-tuples only when **all four** fixed-q0 edit outcomes are VERIFIED/CERTIFIED; require actual \(\kappa\) class evidence and disclose class yield: positive complementarity, redundancy, neutral. A root constructed “to exhibit H1” is NOT automatically a proof-grounded H1 example. Same-endpoint order contrasts require one witnessed and the reverse appropriately certified, with identical final object poses and success conditions. Omissions must be independently adjudicated as shorter *executed* repairs. Keep UNKNOWNs out of denominators; do not promote budget negatives to certificates.

Use **fixed non-p-value stopping** by reserved roster and budget; report all attempted scenes and rejection/unknown statuses. If fewer than 24 proof-grounded H1 roots or inadequately diverse effects, mark the F3/F5 tests **UNDERPOWERED / NOT_EVALUABLE** and show descriptive estimates; do not quietly expand the holdout after reading the result. A second preregistered independent follow-up may be proposed, not silently executed.

**Outputs:** `responses-phases/0054_P12_2_3_locked_holdout_and_physical_evidence.md`, labels and witness manifest, constructor-lineage coverage, certificate atlas, costs, `runs/p12/P12_3_GATE.json`.

## 5. P12-4 — Prospective statistical tests: A/B/C and F3/F5

Unseal only after physically adjudicated outcomes are hash-committed and frozen prediction snapshots already exist. Analyze independent roots; multiple orders/edits/seeds within a root are correlated. Predeclared comparisons:

1. **Primary pairwise factor utility** on **the same** proof-grounded \(\kappa\) roots: B vs B-F3 and B vs B-F5s, two-sided exact paired sign p, Holm(2), mean paired Δ, 95% root-bootstrap CI, root counts/ties, seed-specific direction and effect size. Report predictive adequacy (\(\hat\kappa\), binary scene NLL) of all arms; factor-ablation advantage without adequate absolute prediction is not a mechanism demonstration.
2. **Secondary** B-F5q, B-F2, B-F4, B-V0, A/B/C/SF, B-U; report effect size and confidence intervals, and control exploratory multiplicity if calculating many exploratory p-values. Parameter-count confounding recorded, not hidden. A/B/C use their exact established model semantics; never present them as having D's direct blocker output.
3. **Secondary order and omission:** actual matched order-pair success margins (not only saturated binary accuracy), omitted-repair marginal calibration, physical witness/certificate source, and per-family effects. Report 3-/4-move attempts/witnesses where available; **full-trained** ability vs **short-trained** generalization always separated. Do not selectively report only attained successful families.
4. **Predeclared cross-family diagnostics:** root-family aggregates, number of scene geometry factors shared with P10b, failure/abstention classifications, model scope/memory/normalization and inference CPU/s; do not collapse into one optimistic headline if family-specific performance differs.

If effects do not survive Holm correction, report **NOT_CONFIRMED**, even if all signs align. If the novel-family test produces widespread model failure, report it unambiguously; a positive ablation contrast alone does not show robust deployed usefulness. **No retraining on new holdout after opening labels.**

**Outputs:** `responses-phases/0055_P12_4_blind_factor_and_prediction_results.md`, primary-test machine-readable results, error cases, `runs/p12/P12_4_GATE.json`.

## 6. P12-5 — Independent end-to-end execution (if physically admissible)

On the newly frozen holdout, execute each model's **unchanged** strict TOP1 selection once per root/seed (deduplicate identical `(root, repair, deterministic episode seed)`), count abstentions and no witnesses as failures. Include A, B, C, SF and geometry-only; include G+M as a **different, explicit planner-assisted** reference up to five candidates. Do **not** let any learned arm preflight another choice. Reuse teacher traces only if the *complete identity and seed/protocol match* is proven; otherwise run and charge new physical episodes. Exact target success includes retrieval + SAFE_RETREAT. Report 3-/4-move fractions on valid/certified and only operational-minimality strata separately.

**Metrics:** root-level success, paired differences/CIs, planner calls, candidates physically tried, abstention, travel, number of moved objects, failure classes, CPU+wall per root **including abstentions**, CPU per success, end-to-end image feature-extraction/inference/ranking time (measured consistently), G+M pose-screen/ranking/planning time. A method that abstains frequently is not automatically efficient per successful task. No universal time advantage claim from protocol-mismatched means.

If difficult scenes do not contain any executable repair, preserve that as a genuine negative **coverage** finding rather than claim the models failed execution selection against no possible candidate. Define how many roots have at least one witness in the frozen catalogue and report results on both all-roots and witness-exists (latter conditional) cohorts.

**Outputs:** `responses-phases/0056_P12_5_new_family_executed_TOP1.md`, provenance-linked physical GIFs only for actual recorded witnesses, `runs/p12/P12_5_GATE.json`. No invented paths, no alternative planning masquerading as strict TOP1.

## 7. P12-6 — Focused appearance and D attribution semantics (secondary; no new methods)

### Appearance: diagnose realism, not merely severe recolouring

P11 H9 homogenized every object pixel to one colour and every support pixel to another, removing much visual identity. Keep it as a *severe palette-remap stress test*. On original **P10 images** and, if feasible, novel holdout observations, create a frozen realistic photometric set: modest brightness/contrast, white balance, desaturation and texture-preserving colour changes **with geometry, segmentation masks, object IDs, robot state, goal and candidates exactly fixed**. Use a fixed, published per-variant recipe and seed; no selecting perturbations by model outputs. Distinguish robustness **conditional on provided instance masks** from robustness of an entire real visual perception stack; do not claim to have tested segmentation or detection stability when masks are held fixed. Recompute the same frozen DINOv2 embeddings. Report average \(|\Delta p|\), TOP1 change, admission changes, \(\kappa\) shifts, root-level CI, and both gentle and severe conditions. Optionally run a known-geometry visual-zero control; do **not** claim visual invariance if near-zero change is solely because pixels are ignored. Results on already-open P10 roots are POST-HOC. A fresh photometric stress test on new sealed imagery remains secondary unless prospectively preregistered and fully frozen before labels.

### D: semantic and class-balance completeness, no recursive manipulation

Recompute previous P11 D evaluation on the identical cohort, plus on new roots **only if** all frozen parking-subset inputs/teacher labels are physically identical and complete. Distinguish:

- Feasible original (empty GT blocker set), **infeasible original with at least one certified minimal clearing set**, **infeasible with no discovered clearing set in the fixed pool**, and `UNKNOWN`/`INCOMPLETE`.
- `union-participation` blocker mask vs `necessary` **intersection**; on alternative minimal-set roots, never call every union member individually necessary.
- A/B/C/SF counterfactual-derived blocker masks only where every corresponding edit query matches the **same** parking subsets and fixed q0; every other root `UNSUPPORTED`, not zero F1. If model predicts no sufficient clearing subset, report `NO_PREDICTED_CLEARING_SET` and coverage, **not** silently an empty “no blockers” mask.
- On **infeasible-original roots only**, with complete masks: macro/micro precision, recall, F1, exact set, false-positive irrelevant objects, cardinality MAE and root-cluster CIs, separated by proof-grounded and operational provenance and true blocker counts 1/2/3/4. Also report the overall 0-blocker convention explicitly, initial feasibility with TP/TN/FP/FN, AUROC/NLL and class prevalence.
- D-full vs D-pairless and geometric heuristics; the current pairwise term has NO confirmed value. Don't create D destination/placement/recursion or train another D architecture.

**Outputs:** `responses-phases/0057_P12_6_photometric_and_D_attribution_controls.md`, JSON summaries and realistic appearance/D figures, `runs/p12/P12_6_GATE.json`.

## 8. P12-7 — Final independent evidence ledger, quality assurance, decision

Do a focused complete code/data/test review; implement tests for new generator reproducibility, non-overlap with P10 family logic, hardness-filter replay and acceptance log, record identity, frozen threshold/checkpoint/source hashes, two-step lock/unseal enforcement, zero IK/planner calls in inference, unknown masking, root-level vs outcome-level aggregation, H1 certification, F3/F5 contrast signs and Holm, episode reuse identity, D no-clearing-set handling and photometric invariance of nonvisual inputs. Rerun whole regression suite + six historical replays after all modifications and report exact totals; don't assume 407 remains unchanged.

Produce:

- `responses-phases/0058_P12_7_2D_independent_generalization_and_scientific_verdict.md` — professor-facing evidence-to-claim matrix, new-vs-old benchmark side-by-side, provenance/CI/power, negative findings, exact claims approved for talk/paper.
- `responses-phases/P12_2D_SCIENTIFIC_DECISION.md` — verdict `PASS / PARTIAL / FAILED / BLOCKED` **per scientific question**, not one overall engineering-only PASS.
- `runs/p12/P12_FINAL_MANIFEST.json` — complete SHAs for prereg, frozen predictions, scene roster, labels, checkpoints, figures/animations, executable code, regression and compute ledger.
- `visualizations/p12/` — a clean 2D family atlas (accepted/rejected scene samples), a causal-ground-truth κ scene-edit witness/certificate panel, paired factor-ablation plot with uncertainty, A/B/C/SF/G+M separate-protocol execution plot, photometric stability panel, D blocker error/provenance panel, and recorded motion GIFs only if actually executed.

In the **final Claude chat message**, report directly (do not merely link reports):

1. New physically adjudicated roots attempted/accepted/decided, proof-grounded H1 sample count, two novel scene mechanisms and acceptance/rejection rates.
2. **New test F3 and F5** paired numerical deltas, 95% CIs, raw and Holm p-values, per-family and absolute predictive error; declare underpowered when appropriate.
3. A/B/C/SF TOP1 physical success on new roots, and separate G+M protocol/costs, or mark `NOT_RUN` explicitly.
4. Gentle vs severe appearance robustness, including TOP1 changes.
5. Short 2D blocker comparison: D vs D-pairless vs geometry and strictly matched A/B/C/SF; infeasible-only, proof-grounded separately, no-clearing-set/UNSUPPORTED counts, with exact numerical results if evaluable.
6. Overall supported/unresolved/negative scientific claims, budget breakdown, engineering tests/replays, hash-verified pushed commit(s) and truthful next decision.

**Final response is not complete unless it visibly prints the P12 causal-factor results *and* the D attribution comparison.** Don't claim a novel confirmed result if P12-2 freeze, P12-3 decisive-label coverage, or paired statistical gate fails.

## 9. Staged resource ceilings and autonomous stop boundaries

These budgets are **maximum ceilings, not targets**, and start fresh for P12; do not reuse P10/P11 ledgers as if their budgets were available. If estimates exceed caps, stop before overspend and explain. Declare CPU-s and wall-s; no untracked background jobs; don't claim completion of a job that did not finish.

| Work category | P12 cap (CPU-s) | Notes |
|---|---:|---|
| Read-only audit, prereg, new module tests, visual/reports | 4,000 | Reuse P11 evidence wherever possible |
| New constructor DEV + bounded teacher pilot | 5,000 | Up to 16 DEV roots; all attempts recorded |
| New confirmation physical teacher | 40,000 | Up to 80 new independent roots, staged batches (≤20 roots/batch) |
| New independent TOP1 physical execution | 12,000 | Deduped exact physical episode keys |
| Secondary appearance + D diagnostic analysis | 5,000 | No model retraining |
| Final regression/replays | 2,000 | Count fixture planner calls separately |

**Gating decisions:**
- P12-0 FAIL → stop before any new collection.
- P12-1 unconstructible / scientifically indistinct / forecast grossly exceeds ceiling → stop, produce reproducible DEV failure report, *do not* issue holdout claims.
- P12-2 cannot remotely commit frozen predictions before labels → stop and invalidate the attempted confirmatory cohort.
- P12-3 incomplete physical evidence / insufficient N → produce descriptive estimates and mark the *factor tests* UNDERPOWERED. Continue supported secondary audits but don't present a confirmatory factor verdict.
- P12-4 positive statistical results never override catastrophic absolute miscalibration, source corruption or wrong factor semantics.
- P12-5 prohibit planner-assisted advantage being conflated with TOP1; if no executable roots, mark end-to-end selection performance NOT_EVALUABLE.
- If holding all 24+ H1 roots within 40,000 teacher CPU-s proves impossible, explain coverage/yield/cost before proposing any later continuation; do not silently relax evidence criteria.

**No architecture redesign. No new 3D, D placement/recursion, or hardware. Stop after P12-7 and push reports/code/gates only when genuinely executed.**
