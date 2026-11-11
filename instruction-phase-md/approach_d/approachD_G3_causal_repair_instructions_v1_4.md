# Approach D — G3: Causally Directed Repair Search (Local Workstation)

**Implementation instructions v1.4 | 29 October 2026**

## 0. Goal and authority

Implement a **new, opt-in Approach D repair policy** that uses D's learned **original-target feasibility and blocker-participation predictions to decide which obstacle–destination counterfactuals are worth exploring**. The current `Dp17-norec` policy mostly orders a conventional search over the same candidate domain; G3 must do something materially different: **D constructs and selectively expands a bounded causal search frontier**, while frozen swept-volume/trajectory geometry determines what can physically be executed.

**Do not claim D learns destinations, trajectories, swept volumes, order or motion feasibility.** The same frozen D is queried repeatedly, **for the original target T only**, to evaluate hypothetical modified scenes. That inference-time use of D is the methodological novelty being tested; its benefit remains an empirical question. No new loss, model architecture or retraining is required in G3.

**Local repository:** `Narendhiranv04/latent-causal-tamp`, local branch `approach-d-v1`. Latest reported local HEAD: `ca33aefc7` (G2c-lite; verify actual HEAD). Key sources: `ad_provider.py`, `ad_runtime.py`, `ad_compile.py`, `ad_local.py`, `p17_d.py`, `p17_domain.py`, `d_blockers.py`, `p17_search.py`, `approach_d.toml`; reports `0102_AD_G2b_...md`, `0103_AD_LOCAL_COMPARISON_AND_G2C_LITE.md`. Respect the previous v1.1–v1.3 rules where compatible; **this v1.4 replaces their 'D only reorders' policy for the new G3 experiment.** Historical D and all its evaluations remain immutable.

**Workstation only.** The server is separately generating a new systematic 2D/3D dataset. Do not access the server, ingest unfinished server data, or run 3D dataset jobs here. Existing P13–P17 2D development evidence is sufficient to test G3's logic and initial efficacy.

## 1. Research hypothesis and scientific distinctions

The hypothesis is:

> The learned causal diagnosis should determine **what candidate corrections are generated and evaluated**, not simply the first action in an otherwise unrestricted geometry-driven enumeration. Geometry supplies physically meaningful destinations and checks; D evaluates the consequence of each hypothetical edit for T; finite search joins those edits into a repair.

Distinguish all four roles:

1. **Learned D:** `p_T(S,q)` and conditional blocker marginals `m_i(S,q) = P(b_i=1 | y_T=0,S,q)` for *original T* and *original goal*. These are model predictions, not physical certificates or proof that all high-probability blockers must move.
2. **Nonlearned swept-volume geometry:** proposes plausible free slots and distinguishes where an object would collide with *specific stored* target/relocation motion sweeps. The union of every sweep is **not** an unconditional forbidden region: a destination may be fine for one target trajectory and bad for another.
3. **Precompiled motion provider:** retrieves stored **absolute** x/y joint trajectories for the current obstacle, source, destination, footprint, robot q and matching grasp mode; checks *complete* robot, gripper, held-object and connector phases. The accepted action records its exact `q_end`.
4. **Bounded causal search:** builds a shortlist from D, evaluates candidate destination effects with D, expands a small number of promising branches, and repeats. A fully checked original-T motion is the **only** success condition.

The previous archived comparison is a **baseline, not proof of G3 superiority**: `Dp17-norec = geometry-norec = 71/90` in historical P17; both used the old solver-based backend. The new precompiled development backend is extremely limited: G2c-lite completed the one *directly feasible* root and **none of the blocked roots** across 12; added templates did not improve it. Do **not** imply a new guidance policy alone fixes that motion-library gap.

Important counterexample: G2b F12 `p13_2026216000` admits a historical **one-relocation** repair `o00 -> 59`, even though its stored-motion demo uses `o00 -> 45`, `o01 -> 36`, then T. Do not call F12 K2 or claim that the finite library establishes causal necessity.

## 2. Locked learning and movement contracts

- Frozen production **pairless D (`Dp17`)**, exactly **two losses when later trained**: target feasibility BCE + `lambda_B=2` blocker-participation NLL where ground truth is justified. No `L_updated`, destination, order, travel or trajectory loss. G3 does **not** train anything.
- **Never query D on obstacles as temporary targets.** T's identity and goal stay constant at every search node. Use actual hypothetical occupancy and **recorded terminal robot q**. Disable the old temporary-target recursion and any hidden D(A)/D(B) fallback.
- D **does not explicitly learn the effectiveness of `(object, destination)` actions**. Counterfactual effectiveness is estimated by reapplying its learned original-T predictor to the edited scene. Test whether this generalizes; do not state that D was directly trained to choose placements.
- **No inference-time IK, RRT, motion planning, grasp synthesis, retargeting, joint interpolation or connector generation**, for either an obstacle or T. Offline generation remains allowed only in separately authorized compiler work; G3 should **freeze and reuse the current catalog** and run no bulk compilation.
- A missing stored action or blocked connector is `FAILURE` with a reason, **not** evidence that T is physically impossible. Do not relabel the teacher dataset from runtime catalog failures.
- The **existing** P17 evaluations use at most four obstacle relocations. Keep that exact protocol intact. For new dataset integration later, set a separate opt-in budget of **seven total pick-and-place actions = up to six corrective relocations plus T**, with **at most four intentionally necessary relocations**, allowing up to two nonessential moves. Do not retroactively convert historical labels or automatically make the local test search six moves deep.
- New operational teacher labels (later) are binary `1` verified / `0` no success under fixed offline budget, with failure provenance metadata; historical P17 unknown statuses remain unchanged. Never turn a library failure into a blocker mask.

## 3. The actual G3 causal search algorithm

Implement an easy-to-explain finite **D-driven candidate-and-counterfactual beam search** (or similarly simple bounded frontier). No need for elaborate optimality or formal proof apparatus.

**At every hypothetical state** `x = (occupancy, q, applied_moves, exact_motion_records)`:

**A. Verify-first:** ask the precompiled provider whether T can be completed **now**, using the same original T and goal. If an actual full stored T motion certifies and independently replays, terminate SUCCESS without extra moves. **D's probability alone never certifies success.**

**B. Ask D about T:** calculate `p = p_T(x)` and conditional marginals `m_i(x)` over eligible *currently movable* obstacles. Do not treat the marginals as independent proof of mandatory displacement or insist that every high-probability object be moved.

**C. D-controlled mover frontier:** primarily select the **top 2** eligible objects by D's blocker marginals (pilot default; configurable), not every mover. Apply no magic absolute probability cutoff; scores may be poorly calibrated. Keep at least one lower-scored *exploratory* object available through deterministic progressive widening if the narrow frontier stalls. Record which mover was selected due to D and which came from widening. A missing true blocker is a genuine policy miss, not a reason to secretly switch to unrestricted search.

**D. Propose destinations geometrically:** for each shortlisted object, produce up to **3** admissible, free slots (pilot default) using existing `p17_domain.slot_fn`/catalog indexing plus actual full-arm **stored-sweep** awareness. Consider destinations that avoid blocking at least one plausible target-T stored action, preserve free space, and have a compatible precompiled relocation candidate. Do not mark a location safe because of a 2D endpoint test or a shifted sweep. Avoid collision with the **current occupancy**; treat sweep overlap as candidate-specific evidence, not a global hard veto. Log why each slot was proposed. Geometry proposes **where**, D evaluates **whether that edit improves the original task**.

**E. Score a bounded counterfactual set with D:** for a pair `(object i, destination d)`, there may be multiple precompiled motion templates with different **exact `q_end`**. A candidate is `(i, d, stored_motion_id, q_end)`, not just `(i,d)`. Construct the *hypothetical* edited occupancy at that destination, set q to **that recorded end configuration**, and requery D **for T only**. Store `p_before`, `p_after`, remaining blocker marginals, source/destination, candidate sweep conflicts and provenance. Do not evaluate a hypothetical q that the candidate cannot actually achieve.

**F. Prioritize, then validate:** use a transparent, predetermined ranking combining (i) current D blocker relevance of the moved object, (ii) predicted counterfactual `p_T` for T, (iii) modest nonlearned movement-cost / geometry tie-breaking. For the initial prototype prefer **lexicographic ranking** over tuning an opaque weighted formula: high causal relevance, then best predicted post-edit T feasibility, then shorter stored travel; preserve diversity among candidate objects. **Do not require `p_after > p_before` at every step**: a genuine K2/K3/K4 repair can have no immediate gain before the final blocker is moved. Maintain small beam diversity; don't greedily discard necessary intermediate steps.

A candidate must pass **complete precompiled motion and connector checks in the current scene** before a successor can enter the search frontier. It is fine to rank a cheap hypothetical prior to expensive certification, but never promote it as a realized action without certifying it. Use exact recorded terminal q and phase-valid robot/object updates. Check the target again after each accepted successor.

**G. Progressively widen only if needed:** try more movers and/or more destination candidates when no verified plan emerges inside the initial D-focused frontier. Widen in explicitly logged stages (`top2 -> top4 -> all eligible`, subject to configured caps). Keep the same fixed number of total exact motion checks, D forward passes and node expansions across compared policies, so widening doesn't silently turn into a free exhaustive fallback. Report whether success came from the D-focused stage or widening.

**H. Stop:** on first independently verified T success; otherwise at finite limits, return binary `FAILURE` with `NO_TEMPLATE`, `CONNECTOR_COLLISION`, `MOTION_CHECK_BUDGET`, `NO_CAUSAL_CANDIDATE`, `NO_VERIFIED_REPAIR`, etc. Distinguish no accepted plan **in the finite library** from physical impossibility. Minimality can be claimed only if an appropriately bounded finite search actually adjudicates shorter choices; otherwise report `first_verified_within_budget` and its action/travel counts.

**Simple default knobs (DEV pilot; not tuned on held-out data):** top movers 2; destination proposals 3 per mover; beam width 3; max 2 relocations for the **current 12-root pilot** (historical semantics); 6 exact checks per candidate move; max 60 relocation attempts/root; finite D-call and node caps aligned across policies. Add config under a small `[causal_search]` section in `approach_d.toml` only. Do not modify `config.toml`. If a cap is crossed, fail and record it. Keep knobs visible in report.

**Note:** existing G2c-lite comparison uses a fixed 3-mover × 2-slot domain with exactly the same provider for all guides. For scientific comparisons, a **common eligible universe** must be fixed first; the *selection and expansion* within that universe is the policy's job. Do not let D have more source/destination coverage than controls.

## 4. Required baselines and ablations (do not overbuild)

On precisely the **same frozen root cohort, motion catalog, static candidate universe and resource budget**, compare:

1. **D-CAUSAL (new production experimental policy):** D blocker-selected mover frontier + D-evaluated edited-scene target feasibility + stored-sweep destination proposals + progressive widening.
2. **GEOM-CAUSAL:** same frontend/proposals, beam, widening, provider and budgets, but a **nonlearned geometric obstacle-relevance score** and nonlearned target-sweep conflict/distance heuristic instead of any D calls. No fitted parameters. This is the main fair control.
3. **UNIFORM/RANDOM:** same universe and budget, deterministic seed / replay, no D.
4. **D-BLOCKER-ONLY ablation:** use D to select movers, but no counterfactual D score for destination choice (geometry-only tie-breaking). Isolates the value of D's *post-edit T re-query*.
5. **D-COUNTERFACTUAL-ONLY ablation (optional if easy):** evaluate edits with D but no D-based blocker shortlist, under identical resource limits. Isolates mover gating.
6. **Historical Dp17-norec:** show archived results for context, **never put its solver-based success numbers in the same experimental bar** as the new precompiled backend.

This design tests three distinct hypotheses: **which object** D selects, **where** D suggests moving it after geometric proposals, and **whether that actually enables an executable T action**. Report each separately. Don't report a better blocker-ranking metric as a repair-success improvement.

If the frozen precompiled library still solves **zero blocked roots**, accept that as a **catalog ceiling**. Do not fabricate successful chains, quietly expand compilation, or call the historical planner for rescue. In that case run a **separate, clearly labelled counterfactual-selection analysis** on already saved, legitimately labelled development interventions (same T/q protocol where comparable). It can measure candidate ranking agreement / rank of verified sufficient edit **without calling it physical repair success**. Beware: historical intervention labels often use original q; a new candidate's `q_end` may differ, so report which comparisons are valid or omit mismatched comparisons. No test-data tuning or legacy `UNKNOWN -> 0` conversion.

## 5. Implementation footprint

Start by reading and tracing the **actual local code at HEAD**. In particular, examine how `ad_provider` handles stored q/connectors, goal certification, failure codes, action records, and caching; understand `ad_local.py`'s search budgets and report outputs. Do not assume any existing module can be safely called with new policy inputs.

**Prefer one small new module** `ad_causal.py` with pure candidate-generation, selection, bounded frontier and experiment helpers, plus tests `tests/test_approach_d_g3.py`, an opt-in `[causal_search]` section, and an optional tiny `ad_viz.py` extension. Reuse existing provider, `p17_domain.slot_fn`, D input builder and model predictions; do not clone the planner or create many packages/subfolders. If modifying `ad_provider` is needed to expose `q_end` or candidate variants, make the smallest additive, backward-compatible change.

**Avoid any hidden old solver fallback:** `p17_search`/`p16_motion` paths may invoke online planning. New G3 runtime must use the guarded precompiled provider only. The historical model's temporary-target recursion must never be invoked in G3. Use a named new policy `D_CAUSAL_G3`, not just `Dp17-norec` with different printing. Store the old guide as a separate baseline.

The step-by-step artifacts for each evaluated scene should be compact and reproducible: original occupancy/q, predicted `p_T` and blocker marginals, selected shortlist, geometric slot proposals and stored motion IDs, hypothetical post-edit `p_T` and q, full certification outcomes, selected expansion, final T check, reason on failure. Record number of D evaluations and collision checks, not just wall time. Cache D predictions on **exact scene occupancy, q, target, original goal, model hash**, and never share policy caches in a way that changes budgets unfairly.

## 6. Evaluate in two clearly separate views

**View A — Causal-selection sanity (existing DEV evidence).** Does D find actual known involved blockers early? Given available edited-scene labels, does it prefer an intervention that improves original-T feasibility? Include distractor-negative cases. Distinguish union-participation from *individually necessary* blockers, and remember nonmonotone / incomplete interventions. Report counts and denominators; a few authentic examples are sufficient. No need for new complex metrics or massive annotation.

**View B — End-to-end physically accepted repairs (precompiled backend).** How many truly obstructed DEV tasks are solved with the same bounded moves and checker budget? How many motion requests fail because of target core, connector, relocation core or missing template? Compare **the same** candidate universe across all policies. Report actual successful plans and unnecessary relocations separately; verify-first ensures zero relocation on already-feasible roots, not a learned advantage.

If View B is uniformly zero, **do not optimize the learned ranking to compensate for missing motions**; document the result, present a selected illustrative D-controlled proposal with the actual blocked swept volume and failure reason, and leave motion-library expansion for the server-side dataset/catalog integration.

**Visualizations** under `visualizations/approach_d/g3/` (lightweight but explanatory):
- `01_causal_pipeline.png`: scene → D blocker probabilities → shortlisted movers → swept-aware slot proposals → counterfactual D(T) values → checked motion or failure.
- `02_one_scene_trace.png`: actual DEV scene with proposed placements, candidate stored sweeps, and D's ranking/decision. Label inferred versus independently verified quantities clearly.
- `03_ablation.png`: mover shortlist relevance, candidate ranking and motion realizability for D, geometry, uniform and blocker-only.
- `04_failure_case.png`: a failed candidate where the D-predicted causal edit looks good but the stored motion/connector is blocked. An optional success figure only when actually independently replayed.

Use existing 2D scene rendering and accessible saved trajectories; never invent successful trajectories or draw a schematic as measured execution. Each figure should answer one question in plain language.

## 7. Tests and stop conditions

**Tests should establish logic, not demand an exhaustive formal proof.** Cover:
- original T and goal unchanged across every D call, including multi-move and failure paths; no temporary-target query;
- D's blocker marginals actually change the chosen **candidate set**, not just its ordering, and counterfactual `p_T` changes placement selection on a small deterministic fixture;
- altered robot `q_end` changes D's next-state input; a scene edit alone is insufficient;
- multi-blocker counterexample where first necessary move does **not** increase `p_T` immediately; search can still reach a two-step correction;
- widened search can recover from an incorrect D shortlist, **within the same total budget**;
- swept overlap is candidate/mode-specific and not blindly applied as an unconditional veto;
- provider collision failure cannot become a successful successor, nor a training blocker label;
- complete sequence replay and strict zero runtime IK/planning/trajectory synthesis under forbidden-call guards;
- comparable per-policy budgets, no cross-policy cache leakage, no changes to historical P13–P17 artifacts.

Run existing tests and six archived replays, then G3 tests. Reproduce the old G2b/G2c-lite documented outcomes where applicable. A failure is recorded honestly; no hand-picked success called an aggregate score. Don't run the sealed 442-query benchmark, retrain, grow the motion library at scale, access the dataset server, push or merge without new explicit authorization.

**G3 deliverables:**
- `ad_causal.py` (and minimal opt-in changes only), `tests/test_approach_d_g3.py`, config overlay;
- `responses-phases/0104_AD_G3_CAUSAL_REPAIR_SEARCH.md` with a short logic explanation, pseudocode, actual DEV outcomes, matched controls, genuine limiting factors, what learning changed, and PASS/PARTIAL/BLOCKED verdict;
- `visualizations/approach_d/g3/01–04*.png` with honest captions;
- local tested commit on `approach-d-v1` and a concise next-stage recommendation, **no push**.

**Engineering PASS:** D actually selects and assesses **a different bounded candidate frontier** than geometry-only; target-only counterfactual predictions are grounded in the hypothetical `q_end`; accepted sequences use only independently verified stored motions; forbidden solver calls = 0; tests pass. **Scientific positive** is *separate* and requires measurable held-out benefit on meaningful blocker/placement selection and, when catalog coverage permits, repair results. If catalog coverage prevents that, report an engineering PASS with scientific evidence INCONCLUSIVE, not a research success claim.
