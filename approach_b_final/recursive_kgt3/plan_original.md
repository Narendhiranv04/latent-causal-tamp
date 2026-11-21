# Recursive K>3 TAMP — implementation and scientific-validation plan

**Status:** Proposed implementation plan; **not** a claim of completed recursive experiments.  
**Date:** 2026-11-21  
**Authoritative dataset:** `Narendhiranv04/latent-causal-tamp`, `naren/scaling2d-k12-test`, commit `e07354b3c8344954c05e3b5ddf499436d855a550`.  
**Scope:** 2D, 8×8 tabletop/grid, planar 3R arm, frozen K≤3 cVAE and factorized X/Y scorer. Design extension must remain compatible with the 3D architecture, but **no 3D K>3 performance claim** is part of this campaign.  
**Target figure:** RSS Fig. 3(a), **Iterative loop → Retarget → Compose → Rank**, followed by independent physical verification.

> **Mission:** Determine whether frozen models trained for at most three corrective relocations can, without new training or inference-time physics calls, propose, recursively compose, and rank longer corrective repairs for a task whose original target is blocked. This must be evaluated on new minimum-K-certified scenes without allowing the planner to inspect certified witnesses, K labels, or teacher outcomes.

---

## 0. Non-negotiable research contract

1. **No retraining, changing, fine-tuning, or adapting neural weights** in the primary experiment. The task-conditioned `scratch_all` cVAE and D-family factorized X/Y model remain frozen and hash-verified. Any future training is a separate study and must never silently enter this result.
2. **No explicit blocker classifier, dependency oracle, search-time robot motion planner, IK queries, teacher feedback, certified-K input, or witness-guided proposals** in the proposed method. Dependency hypotheses arise through retargeting and learned candidate generation. Static grammar/occupancy checks are allowed.
3. **K≤3 remains the existing frozen method**; do not rewrite its behavior or move the decision boundary. New code is additive and isolated.
4. **Each local model call handles 0–3 proposed relocations only.** Never pass a K4–K12 ordered sequence to a frozen X/order head trained and configured for ≤3. A Y-only endpoint evaluation may include >3 *edits* via the original root's endpoint scene; that is still distribution shift and must be reported.
5. **Original target and goal remain immutable.** A temporary target changes only a local model view. It must never overwrite or silently alter the original task. The original target may never be used as a corrective mover.
6. **Search uses learner-visible public inputs only.** Keep `release_v2/private/LABELS.jsonl`, `COVERAGE.jsonl`, witness routes, certification records and physical GIFs inaccessible to proposal, ranking, configuration selection, search pruning, and model prompts used to steer it. Private information may be used *only by an independently separated evaluator after the prediction is committed*. The already-known K-level counts are dataset metadata, **not** model input.
7. **No physical simulation during candidate generation, recursion, or ranking.** Motion/teacher calls are counted only during post-commit verification. A physical result must never be fed back into the same scene's search unless explicitly running a *separately labeled oracle-assisted diagnostic*.
8. **Full physical verification must follow the unchanged long teacher semantics:** chained relocations with carried arm state; one terminal connector back to `q_ref`; independent Y check for the original target from canonical reference. Do not reset to `q_ref` or teleport between stages to make recursion appear feasible.
9. **No statistical inflation:** 23 scenes, and only 3 K12 examples with one target/goal pair. Report absolute counts, not only percentages; wide uncertainty and pair concentration must be explicit. This is a small stress-test cohort, not a general long-horizon benchmark.
10. **No unconditional execution on TEST.** Follow the gates below; freeze/harden all code, config and the full 23-scene prediction file before the first post-commit teacher verification. Never iterate using TEST outcomes to tune the primary reported method.

### Evidence/lineage index

- `scaling2d_k12/G7/FINAL_REPORT_V2.md`, `release_v2/SUMMARY.json`, `release_v2/public/PUBLIC_MANIFEST.jsonl`, `release_v2/private/LABELS.jsonl` (private **evaluator only**), `G7/gifs_physical/` (**post-evaluation visualization only**).
- `scaling2d_k12/teacher_long.py`, `G1/G1_LONG_TEACHER.md`, G5 acceptance audits and parity tests. The long teacher is separately versioned; for `len(seq)≤6` it dispatches to the frozen teacher.
- `approach_b_final/placement.py`, `search.py`, `xy.py`, `construct.py`, `contracts.py`, `exhaustive.py`, `benchmark.py`.
- `approach_b_final/validation_k3/retarget.py` and `.../ttarget.py` from `naren/k3-postablation-validation` (may not be present on the scaling branch—**inspect and port narrowly**, preserving provenance).
- Frozen bundle manifest: `approach_b_final/reports/final_v34/BUNDLE_MANIFEST.json`, branch `naren/approach-b-v3-4-final-benchmark`; package identifies the `scratch_all` 2D sampler s0, D scorer(s), and TRAIN-only scalers.
- `approach_b_final/ablations_k3/reports/FINAL_REPORT.md` in `naren/k3-ablation-gvlab2-20261120`: validates K≤3 and documents historical TEST exposure.
- `approach_b_final/validation_k3/reports/TASK_RETARGET_REPORT.md`: retargeting diagnostics. Its temporary-task Y is poorly calibrated relative to original-task Y, and 3D intermediate-scene proposals are weaker. These are constraints, not evidence of long-horizon success.

**Expected evaluator data:** 23 certified minimum-K 2D scenes: K4=5, K5=5, K6=5, K9=5, K12=3; object counts K4=16–17, K5=17–18, K6=18–19, K9=20/20/25/25/25, K12=27/28/28. All 23 passed G5 checks including Y0=0, final X=Y=1 and proper-prefix Y=0 for the *certified witness*. K12 is confined to target/goal (61,63). Three new K9 witnesses are only trajectory-hash-identical on the producing host (girish); their physical **labels** agree across hosts.

**Important limitation:** `K_certified` is a *minimum under the declared grammar and static/physical certificate*, not a free planning hint. Do not train, tune or stop based on this label. A generated plan may have a length **greater than** the minimum certified K (up to 12), and its success should be counted as success; separately report excess length relative to K *post hoc*.

---

## 1. Mandatory feasibility/design audit BEFORE implementing

Produce `AUDIT.md` first, with a **PASS / CONDITIONAL / BLOCKED** status for every item, relevant source paths/lines, a runnable reproduction check (or explicit missing resource), and the smallest safe fix.

### A1. Snapshot and checkpoint provenance

- Confirm exact Git HEAD and uncommitted changes. Create a new additive work branch from the specified dataset commit; never alter dataset/search-generation/teacher source in place.
- Locate the frozen bundle's files (not just the JSON manifest), and verify sampler/scorer/scalers SHA-256 checksums. If absent, **block model experiments** and give exact paths/files needed; **do not retrain** replacements. Choose primary 2D sampler s0 and D scorer s0, with s1/s2 for a separately reported robustness check if available.
- Determine which `approach_b_final` implementation at the dataset commit is truly identical to the frozen inference path and which corrections live only on the validation/ablation branches. Resolve by a diff and exact-parity test—not by guessing or merging an entire branch.
- Identify exact inference parameters: 64 raw draws, S1 proposal rule, **top-4 distinct legal destinations per eligible movable object**, maximum local K3, frozen `noop_gate=0.5`, `eta=0.3`, zero α/β/γ for **the historical K≤3 baseline**. Keep recursive-specific scores and admission thresholds separately named; do not inherit `eta=0.3` blindly for nonprobabilistic aggregate scores.

### A2. 20-object limit: source, effect, and fix

- Read `placement.scene_features`, `placement.task_features`, `search.Sampler.propose_many`, `contracts.view2d`, `xy.collate`, and `XYNet` object pooling.
- The current `MAXOBJ['2d']=20` is a **feature-buffer size**, not a principled 20-object neural-layer maximum. A separate feature-building path must allocate `max(MAXOBJ['2d'], n_objects)` or batch-max object length with proper masks, without changing weights or scaler values. Show how scalar features, deterministic object ordering, query-token position, and target context remain identical for `n≤20`.
- Confirm XY's dynamic object padding and masked pooling work for N=28; detect NaN, max-empty-mask, incorrect target index, wrong attr shape, or special token overrun. The network may technically accept N>20 even though the *statistical* support ends at 20.
- **Gate:** byte-/tolerance-equivalent 2D K≤3 sampler distributions/proposals and X/Y predictions for historical fixtures (`n≤20`), plus finite legal outputs on new public N=25–28 fixtures. Record exact device/torch/RNG parity conditions; if CPU vs GPU sampling differs, separate numeric parity from identical RNG traces.

### A3. Semantics audit: local p11, X, Y and no-op

Verify from code, not from a slogan:

\[
 p_{11}(r,\tau) = P_\theta(Y_\tau(S_r)=1)\,P_\theta(X_r=1\mid Y_\tau(S_r)=1).
\]

- **Original Y endpoint:** how to obtain `P(Y_T(S_final)=1)` **without** feeding a >3 order to X. The preferred implementation uses `xy.make_view` with the **immutable original root** and a **Y-only edit for the complete endpoint**, `x_seqs=[]`; use its returned `y_map` to read `py` for the edited endpoint. Do **not** treat `p_noop` on a newly rebased endpoint root as automatically equivalent: it loses the edit-history features. A test must prove 1–3 edit Y-only parity against frozen scoring of the *same endpoint and root*.
- **Stagewise X:** determine what `px` actually means (model's marginal `P(X=1)`, as opposed to the conditional `P(X=1|Y=1)` or `p11`). Use the declared value consistently and test exact extraction. `px` is a heuristic for a <=3 local sequence and **includes a terminal return-to-ready**, so its product across chunks is *not* a calibrated probability of the chained global execution.
- **Retargeted Y:** the scorer can receive a new goal/target input, but retargeting was validated only partially and Y is miscalibrated. Its probabilities are hypothesis-selection heuristics, **not** a calibrated gate or proof that one specified move is executable.
- **NOOP:** an estimated high original Y0 may cause a wrong NOOP. Preserve the frozen K≤3 no-op decision for the K≤3 control; explicitly define if/how it is used in K>3 and report false-NOOP, with no peek at certified Y0.

### A4. Legality and teacher semantics

- Verify exact grammar on `release_v2`: objects fixed vs movable, original occupied cells never parking, `goal_cell` exclusion, no object moved twice, current occupancy, legal support, and `max_total_moves=12`. Read `teacher_long.long_eligible`, `search.Root.legal_dests` and the physical teacher's own eligibility code. Document any differences, e.g., whether original-vacated cells are actually forbidden in the **research planner grammar** versus allowed by the teacher: **do not silently relax or narrow the agreed method**. Avoid attributing grammar differences to model failure.
- Verify complete K4–K12 X/Y verification calls and status handling, including `UNKNOWN_BUDGET`; even a nominal failure due to budget must never be recoded as geometric infeasibility.
- Confirm whether same-scene teacher verification is host-sensitive. Prefer physical-label agreement over cross-host trajectory-hash identity; preserve producing-host provenance where necessary.

### A5. Formal feasibility of the recursion itself

Before coding, write a **small worked example** of a nested dependency chain (e.g., candidate `[B,C,A]`, with A needing `[E,D]` and E needing `[G]`), show the exact resulting global order and intermediate scene, and show the model calls needed to generate it **without an oracle saying which action failed**. Explain whether a finite search budget can discover it, and identify action-choice/goal-choice recall bottlenecks. Provide a no-go argument if the selected algorithm cannot propose a necessary enabling action under its own grammar.

**Audit decision rule:** Do not start P2+ until A1–A5 are PASS or explicitly CONDITIONAL with a diagnostic isolating the issue. `BLOCKED` must include evidence and resolution; never silently skip a failed gate.

---

## 2. Exact algorithm contract (the paper figure)

### 2.1 Inputs, outputs and hidden information

Input: public raw scene, original target T and original goal G, frozen model paths, fixed search budget/config, random seed.  
Output: **exactly one committed decision** per root: `REPAIR` with complete ordered sequence `r` of length 1–12; `NOOP`; or `ABSTAIN`, with provenance and metrics.  
Planning state must never include `K_certified`, certified witness, prior teacher outcomes, success labels or query budgets gleaned from TEST.

Define:

- `S0`: immutable original scene, original robot reference `q_ref`.
- `τ0 = (T,G)`: immutable original task.
- `r = [(o1,d1), …, (om,dm)]`: proposed **global** corrective sequence, m≤12.
- `Edit(S0,r)`: *hypothetical occupancy/pose edits only*, not simulated robot execution.
- `Moved(r)`: objects appearing in the complete prefix, including pending recursive repairs.
- `τ=(A,d_A)`: temporary task; locally retarget object A as the target whose goal is d_A.
- `u`: candidate corrective sequence (≤3) from the same frozen cVAE/D routine to make `τ` feasible.
- `Compose(prefix,u,A→d_A,suffix)`: insert the recursively generated enabling sequence before the particular pending action, then revalidate the **entire** global sequence in order.

The original target is never a candidate mover even in a temporary retargeted view; descendants may not move an object already used in an ancestor/prefix or pending elsewhere in the plan. All recursive reservations must be checked in the **global** composed sequence; local legality alone is insufficient.

### 2.2 Iterative local hypothesis generator

At any local scene `S_p` and task `τ`:

1. Build learner-visible task features with target identity, goal, original geometry/attributes, legal mask and context mutually consistent.
2. For each still-eligible movable object, use **frozen task-conditioned cVAE s0**, exactly 64 draws/S1/top-4 unique legal destinations, recording proposal order/deduplication and RNG seed. The cVAE is **not** trained to predict blockers.
3. Construct ordered legal action sequences of length 1, 2, 3 (bounded computation; exact enumeration only inside whatever proposal pool is explicitly retained). Use the frozen D scorer for `p11` and its separate `py`/`px` when available. Support a **budgeted beam / fair best-first strategy** for dense scenes; document that it approximates a potentially huge local K≤3 pool rather than claiming full enumeration.
4. Preserve candidate diversity across different objects, destinations, and orderings. Do not select only the local highest `p11` if its Y is low or it repeats a dead-end; otherwise an initial K12 scene may never yield a useful seed.
5. Return ranked local hypotheses and full provenance, **no physical query**.

Important: on K>3 scenes, a short local hypothesis may make original Y remain 0. That does **not** justify pruning. All certified witness prefixes in the release keep original Y=0.

### 2.3 Retarget as a **planning transformation**, not a discovered blocker label

Given a pending action `a=(A,d_A)` in a local/global candidate:

1. Construct the precise hypothetical scene preceding `a` after its current compositional prefix.
2. Create a temporary task `τ_A=(A,d_A)` with updated `tid`, attributes, goal coordinates, `ctx`, and task features. Use the retarget view adapter; retain original `τ0` separately.
3. If the local model says that `τ_A` is already feasible, that is **only a heuristic** for leaving `a` without an enabling repair, not physical confirmation.
4. Otherwise—and as a diversity fallback even for seemingly easy actions—query frozen cVAE/D again for local ≤3 corrective sequences `u` to make `τ_A` feasible.
5. For each proposed `u`, recursively consider inserted repairs before difficult/uncertain actions in `u` and then compose the complete `u → a`. This builds a nested, acyclic dependency tree without predicting explicit blocker identities.
6. Do not treat the frozen X prediction for the whole local plan as a label for the exact failing step. If several actions might be responsible, branch on multiple insertion sites using a deterministic fixed budget; ranking and prefix controls decide which hypotheses survive. **No teacher-outcome-driven recursion trigger.**
7. A temporary target must not accidentally permit the original target T as an enabling move, or permit deleting/replacing a previously planned action without a separately generated alternative.

### 2.4 Global composition invariants

Every candidate `r` produced by recursion must satisfy:

- length `1 ≤ |r| ≤ 12` and each object appears **at most once**;
- all destinations supported, legal and free **at the moment of relocation**;
- no destination originally occupied **if the planner's declared frozen grammar requires this**, including those vacated earlier;
- original target never moved; original goal never used as a parking destination;
- each enabling sequence precedes its target action and preserves the relative order of unaffected actions; all order alternatives have distinct recorded sequences;
- no cycles or self-enabling (A depends on A, A→B→A), and no duplicate global state/action-set with different provenance under an identical search key;
- proposal generation, insertion and ranking operate over **hypothetical object scenes**, never inventing an actual robot configuration for an unexecuted plan.

**State/dedup key:** At minimum `(original_root_id, global_ordered_prefix, current_hypothetical_cells, moved_object_mask, pending_actions_and_goals, recursion_depth/task_chain)` for open search states. A cruder endpoint-only key is **wrong** because the X model and physical execution are order-sensitive. After proving dominance under identical relevant state/context, more aggressive caching is optional. Cache Y solely by original task+canonical endpoint; cache local X by ordered local action sequence **and** local start scene/task; cache cVAE proposals by scene/query/task/model seed.

### 2.5 Ranking: distinguish local p11, execution heuristic, original final Y

**Local search** uses the frozen `p11` exactly as a heuristic over candidate repairs of the *current* task (original or retargeted).

**Global complete-sequence ranking:** for each globally legal `r`, partition its ordered actions into deterministic contiguous chunks `c1,…,cJ`, with `1≤|cj|≤3`. Prefer the same canonical partition for all candidates (e.g., contiguous blocks of 3 starting at action 1), not the tree decomposition that happened to discover the candidate.

Compute local marginal X predictions on the corresponding hypothetical scene before each chunk, using the frozen model and a fixed, documented task interpretation:

\[
 h_X(c_j) = P_\theta(X_{c_j}=1 \mid S_{j-1},\tau_j),
 \qquad S_{j-1}=\operatorname{Edit}(S_0,c_1\oplus\cdots\oplus c_{j-1}).
\]

For the **terminal original Y**, evaluate the original frozen D *Y head* on the **complete endpoint edit relative to S0**, without giving a long order to the X head:

\[
 h_Y(r) = P_\theta(Y_{\tau_0}(\operatorname{Edit}(S_0,r))=1).
\]

Use a declared heuristic ranking family such as:

\[
 C(r)=-\log\bigl(\max(\epsilon,h_Y(r))\bigr)
 + \lambda_X\sum_{j=1}^J -\log\bigl(\max(\epsilon,h_X(c_j))\bigr)
 + \lambda_m|r| + \lambda_D D(r) + \lambda_J\hat J(r).
\]

**Not a probability statement:** stagewise X returns to reference in the training/labeling contract, while physical global execution carries the robot state. The chunks are correlated; multiplying them as independent probabilities is unjustified. The expression is an additive **ranking energy**, not calibrated `p11(K12)`.

- Primary weights, aggregation and epsilon must be fixed *before TEST* on DEV; a nontrivial `λ_X` must be justified and compared to `λ_X=0`. **Do not recycle K≤3 `eta=0.3` as a threshold on `exp(-C)`**.
- The `λ_J`/travel head (if available) is frozen and may be out-of-support at high K. Use `λ_J=0` by default unless justified and evaluated in development; do not invent an end-to-end trained travel head.
- Compare a canonical chunking with, at most, one predeclared alternative aggregation **on DEV only** to expose decomposition dependence. Do not choose the better aggregation on the 23 final scenes.
- Keep original Y, stage X, action-count and travel components in logs. If retarget Y is used to prioritize recursion, its contribution must be a *search priority only*, not multiplied into final original Y.
- Check endpoint permutations: final `h_Y` identical for same endpoint, but X cost can differ by order. This is core to our mechanism claim.
- Check cases where global Y is spuriously high for an impossible prefix. Preserve competing candidates; do not equate a neural score with a certified fact.

### 2.6 Decision rule and semantics

- Run the **frozen K≤3 one-shot control** separately and exactly for reference.
- For the proposed K>3 planner, define a predeclared method of comparing NOOP, REPAIR, and ABSTAIN. NOOP uses the frozen original-task `Y0` estimate; REPAIR requires a complete legal sequence and a model-score criterion determined solely on development evidence; ABSTAIN means no permitted candidate after fixed resource limits or a frozen evidence threshold. Distinguish `NO_CANDIDATE`, `LOW_CONFIDENCE`, `SEARCH_BUDGET`, `MODEL_INPUT_ERROR` and `TEACHER_UNKNOWN`.
- Do not use the certified minimum K to determine recursion depth or allowed plan length; max 12 is fixed uniformly.
- Commit **one** answer per root. It must be frozen before independent verification. A post-commit second choice is a **separate** oracle-assisted diagnostic, not the primary open-loop result.

---

## 3. Executable phase plan, ordered by gates

### P0 — Repository and data preflight (read-only)

**Files / artifacts:** `AUDIT.md`, `MANIFEST_LOCK.json`, `PUBLIC_PREFLIGHT.json`, `FROZEN_PARITY.json`.

- Pin base commit `e07354b3c8` and create `naren/kgt3-recursive` (or a similarly isolated new branch); do not overwrite another active branch or any code-generated dataset.
- Read the public manifest, verify all 23 public-root SHA-256s, root_id uniqueness, 8×8 and legal destination assumptions. Private labels remain strictly behind the evaluator boundary.
- Inspect **all** frozen assets and hash manifest; fail on missing files/checksum mismatch.
- Write the central immutable frozen configuration and resource limits. Specify Python/torch/CUDA versions, RNG seed rules and separate output directory.
- Confirm exact K≤3 replay parity on historical fixtures for proposals, model outputs, candidate ordering, no-op and final decision.
- Reproduce the object's new dynamic-padding path with 16/20/25/27/28 objects; ensure fixed decoder cell count remains 64.

**PASS:** public records all resolve; model hashes match; no private leakage in planner; historical predictions/decisions unchanged; all 23 public scenes encode with finite model outputs.

### P1 — Local reusable API and retarget parity

**Minimal modules:** `data.py` (public loader + features), `models.py` (frozen adapters), `tests/test_retarget.py`.

- Wrap existing `placement` and `XYNet` inference, never reimplement their learned architecture. Expose `propose(scene,task,query,M=4)`, `rank_local(scene,task,seqs<=3)`, `score_Y_original(S0,endpoint)` and `score_X_chunk(scene,task,seq<=3)`.
- Use retarget logic from `validation_k3/retarget.py` and `ttarget.py`, porting only audited pieces required for 2D.
- Enforce identity and round-trip tests, target/goal/context consistency and collision-free role bookkeeping.
- Ensure local `p11`, `px`, `py` reproduce frozen outputs for matched ≤3 cases. Ensure Y-only endpoint equals the same frozen Y-node on ≤3 edited endpoints.
- Add instrumented per-call counters, deterministic RNG, finite-probability checks, legal destination masks.

**PASS:** no changed neural weights; same local predictions as frozen; identity retarget parity; no original target moving; Y-only parity.

### P2 — Recursive compose engine with **mock models only**

**Minimal modules:** `planner.py`, `tests/test_compose.py`, `tests/test_search.py`.

- Implement immutable original task, mutable hypothetical occupancy, pending action queue/dependency ancestry, full ordered prefix and remaining capacity.
- Unit-test all legal/illegal insertion cases and order sensitivity; test self-cycle, A↔B cycle, repeated movers, original-occupied destinations, occupied current destination, original goal, long plan >12 and no feasible destinations.
- Build synthetic 4/6/9/12-action dependency chains whose **mock** local cVAE/X/Y deliberately prefer the prerequisite path. Verify recursive search can generate the specified full sequence without a teacher or true blocker labels.
- Add a negative mock: locally high `p11` but wrong global Y; ranking should reject it if the final Y term is effective. Add another negative: same endpoint, one executable order and one invalid order.
- Build fair/budgeted best-first search, duplicate/cycle detection, local batch scoring, deterministic caches, and stop reasons.
- Measure bounded work: wall time, peak RAM/VRAM, cVAE calls, raw samples, local X/Y calls, composition candidates, deduplicated states, maximum depth, number and reason of pruned candidates.

**PASS:** all synthetic chains reachable within explicitly defined fixture budgets; 0 physical calls; reproducible traces and no illegal composition.

### P3 — End-to-end on DEV only

**Minimal modules:** `ranking.py`, `tests/test_ranking.py`, `tests/test_regression_k3.py`.

- Use historical K≤3 **TRAIN and VAL** and independently constructed engineering fixtures with proven non-overlap with `release_v2` to debug the frozen integration. **Never use release_v2 witness-containing reports or outputs to pick actions.** Audit any engineering/test overlap by geometry fingerprint and root lineage before use.
- Verify local sampler has top-4 proposal support and no hidden alternate model/seed, estimate candidate growth at 16–28 objects using public inputs only.
- Test full ranking components under deterministic chunks, preserve identical-endpoint Y and different-order X, log false positive/overconfidence patterns on DEV only.
- Freeze a **small, registered grid** of resource caps and permitted ranking weights. Select one primary using DEV metrics and fixed feasibility criteria; no opportunistic TEST sweep.
- Baselines: (i) frozen K≤3, (ii) iterative no-retarget local search up to the same total cap, (iii) recursive search + final Y only, (iv) recursive + stagewise X only, (v) recursive with both; optionally rank random/composition-free controls under matched resource budgets.
- Include ablations for retargeting itself, insertion-point choice, and learned sampler vs uniform4 *if resources allow*. Label any unrun arm explicitly rather than fabricating a table.
- Prove that increasing resource cap cannot silently switch from an open-loop method into teacher-guided search. If policy depends on a cap, include cap in config and metrics.

**PASS:** predictions reproducible under fixed config; mechanism parity checks; appropriate search latency/memory; no leakage; one frozen primary configuration selected for final cohort.

### P4 — Pre-register and seal full 23-scene predictions

**Minimal modules:** `evaluate.py` (planner side; no teacher imports), `LOCK.json`, `PREDICTIONS.jsonl`, `PREDICTIONS.sha256`, `PREREG.md`.

- Lock code commit, model hashes, dataset public manifest, resource caps, scorer, temp target semantics, recursion policy, ranking weights, RNG, number of primary runs (prefer one locked seed; extra seeds must be predeclared), analysis definitions and confidence intervals.
- Predefine three endpoints: **physical task success** (`X=1 and Y=1` for committed REPAIR); success rate by certified K (K4/K5/K6/K9/K12), and **efficiency / teacher calls during planning**. Secondary metrics: selected length and excess vs minimum K, score of selected candidate, `FAIL_X` phase vs `FAIL_Y`, abstention, time/calls, architecture/generalization diagnostics.
- Decide in advance how NOOP and ABSTAIN are counted on these all-blocked scenes: both are unsuccessful task outcomes; separately show false-NOOP and abstention. Do not exclude them from denominators.
- Execute inference on all **23 public roots** with private label files unavailable to the planner process. Generate exactly one sealed prediction per root; verify that the file contains no labels, witness, K, or oracle data and no teacher calls occurred.
- Preserve raw full scores (not only rounded 6-decimal metrics), roots/checkpoints/config hashes, provenance and run outputs. No post-hoc replacement of a chosen plan.

**PASS:** 23 unique predictions, complete code/data/model hashes, 0 planner physics calls, clean privacy audit, verifiable immutable prediction SHA.

### P5 — Independent physical evaluation (after P4 PASS)

**Minimal modules:** `verify.py` or an evaluator-only subcommand, `TEACH_LOG.jsonl`, `EVAL_RESULTS.jsonl`.

- A separate verifier loads sealed predictions and the private manifest only after locking. It may read `K_certified` and witness solely to stratify results or conduct post-hoc diagnostics, never to choose a replacement plan.
- Run `scaling2d_k12.teacher_long.x_query / y_query` with full chosen sequence, no intermediate reset, terminal connector and true original target. Preserve all `OK`, `FAIL_X`, `FAIL_Y`, `UNKNOWN_BUDGET`, `INVALID`, `ERROR`, source version, host and replay status distinctly.
- Teacher calls are **post-commit** verification, not planning cost; report separate query accounting. Where teacher outputs are cross-host numerically different but agree in labels, record the label agreement and provenance rather than requiring identical trajectory hashes.
- Verify cached results are never reused across different root/sequence/teacher version/geometry/host settings without an explicit parity audit.
- No second search or learning after outcome; no physical oracle retry in the primary result.

**PASS:** every committed decision receives an unambiguous outcome or an explicit unresolved status; full replay provenance; no result leakage into the primary planner.

### P6 — Scientific report and figures

**Artifacts:** `FINAL_REPORT.md`, `TABLES.csv`, `TRACE_*.json`, `figures/`, `videos/`.

- Report all 23 scene decisions individually **after evaluation** and aggregate by K: 5/5/5/5/3 denominators. Exact physical-success counts and percentages, uncertainty (bootstrap or Wilson/exact interval appropriate to n), and a separate OOD object-count split (≤20 vs >20) for K9.
- Report success if **any valid ordered repair** of ≤12 is verified, even if its length exceeds certified minimum K. Only after the fact compare selected length to K; don't mistake longer but successful plans for failures.
- Decompose failures: no proposal for a necessary object/cell; not composed; composition illegal; ranked valid plan below invalid; high-Y false positives; wrong ordering; stagewise X mismatch; physical X failure phase; final Y failure; false-NOOP; search-budget exhaustion; input OOD; unknown budget. The **witness may be used only post hoc** to calculate necessary-ingredient coverage, with the limitation that one witness does not describe all possible repairs.
- Compare the mechanism ablations at **matched inference budgets** and identical primary scene set; not just isolated placement hit@4. Do not claim statistical significance on tiny K12 strata or after choosing the best arm on TEST.
- For every completed root, render: original configuration; cVAE destination proposals; top local K≤3 hypotheses; actual retarget dependency tree; composed sequence; ranking components; chosen physical execution; final original target. For failures, render predicted sequence, failed stage, and representative alternative, explicitly labeling simulations as hypothetical.
- Use original G7 certified GIFs solely as post-hoc **oracle/reference** visuals, never as planner-generated evidence. Distinguish chosen-plan GIFs from certified-witness GIFs.
- State exactly what was **learned** (nothing newly trained in this extension), what is recursively inferred, what is only a heuristic, what is physically verified, and what remains out of distribution.
- Update Fig. 3(a) and RSS Table I(a) scaling rows **only using verified results**; do not label a K12 success rate as generalization to all object/goal pairs.

---

## 4. Scientific questions that must receive explicit answers

The agent must put a concise but technically defensible answer to every question in `AUDIT.md` and update it after P3 with evidence:

1. Why would the frozen goal-aware cVAE propose helpful destinations when the original Y remains false for every witness prefix? What is the fallback when its sampling assigns negligible probability to a necessary placement?
2. How does recursion select which proposed action needs enabling **without** a learned step-level failure classifier or teacher oracle? Show selection/fairness and its computational trade-off.
3. When a temporary task requires freeing A before executing `(A,dA)`, how is retargeted Y distinguished from actual execution X? Does any term incorrectly score “A can go there” as “the robot can move A there now”?
4. How are dependencies discovered when the useful object is not among the local top-ranked proposals? Are insertion-point exploration and repeated sampling sufficient under the recorded budget?
5. Can the exact proposed algorithm reach a valid 12-relocation plan **without having to enumerate exponential action combinations**? Give measured worst-case limits, not an asymptotic claim unsupported by implementation.
6. Why is multiplying or summing stagewise X scores appropriate as a **ranking heuristic** despite the terminal-connector and carried-robot mismatch? What does a `λ_X=0` ablation reveal?
7. Why is `Y_original(S_final)` evaluated as an edited endpoint of `S0`, and not as a no-op on a freshly rebased scene? Prove numerical parity on ≤3 edits.
8. How is order sensitivity retained even when two sequences yield the same endpoint? How are their final Y scores shared but X scores distinct?
9. What does the cVAE/XY encoder do when it encounters 25–28 objects and ≥9 edited objects? Distinguish *code-capability* from *OOD predictive validity*.
10. Could the frozen model's original NOOP probability suppress every K12 search? Does the no-op gate create an unfair comparison if tuned only for K≤3?
11. Does the final verification use the exact long teacher used in certification, including `q_ref` connector and unknown-budget semantics, or a simpler simulator? Show provenance hashes.
12. What result would **falsify** the proposed value of recursion? Predefine at least: no improvement over nonrecursive equal-budget search, gains explained entirely by search expansions, or stagewise X contributing no verified ordering benefit.
13. What would count as **partial evidence** rather than success? e.g., cVAE ingredients present and composed but final X fails, or final Y high while Y teacher fails.
14. How are leaked TEST labels avoided, given the repository contains private witness JSON and reference GIFs? Describe access control in implementation and audit it.
15. Why should a tiny fixed-K release yield a useful research result? Explain what it demonstrates and what broader generalization cannot be claimed.

---

## 5. Ablation and comparison matrix (no hand-waving)

Pre-register the **minimal primary set** of comparison arms on DEV:

| Arm | cVAE | Local X/Y | Temporary targets | Compose | Global ranking | Primary purpose |
|---|---|---|---|---|---|---|
| B0 Frozen K≤3 | frozen task cVAE | frozen D | no | no | frozen `p11` | failure floor beyond training horizon |
| B1 Budgeted nonrecursive | same | same | no | flat prefixes ≤12, same budget | final Y + X heuristic | effect of recursion vs more search alone |
| B2 Recursive, Y-only | same | local p11 | yes | yes | final original Y only | contribution of recursive composition |
| B3 Recursive, X-only | same | local p11 | yes | yes | canonical stage X only | contribution of endpoint Y |
| B4 **Full recursive** | same | local p11 | yes | yes | stage X + original final Y | proposed method |

Where practical, add `B5 NoRetarget` (same recursive topology but original-task context) and `B6 Uniform4` (same sampling/scoring/search budgets), to test whether conditioning and learned proposal density matter. **Do not remove baselines to conceal a null outcome.**

**Cost fairness:** Align caps on *model evaluations, cVAE draws, expansions and wall time*, and show actual usage. A “flat” planner that is prevented from composing must still be a credible budget-matched comparator. Matching only wall time on different hardware is insufficient.

**Intervention for interpretation:** After the primary predictions are sealed, a diagnostic may inject *known witness* actions only to test whether the scorer can rank successful compositions. This is explicitly **ORACLE_PROPOSAL diagnostic**, never scored as open-loop task success.

**Statistics:** For a paired comparison, report per-root success/failure discordance, exact McNemar/sign-test as descriptive if justified, and 95% interval. Highlight that each K contains 3–5 scenes; do not call a small difference “significant” without a planned error family. Preserve per-root seeds and uncertainty. Report no TEST hyperparameter search.

---

## 6. Expected minimal code layout

Keep new files small, single-purpose, typed where useful, with no second framework. Avoid copying the 500–800-line existing frozen model source or creating dozens of files. An initial target layout:

```text
approach_b_final/recursive_kgt3/
  AUDIT.md                  # evidence-based feasibility and red-team review
  plan.md                   # this evolving plan + decisions and gate history
  config.json               # pre-TEST defaults and frozen experiment config
  data.py                   # public loader, dynamic masked features
  models.py                 # frozen cVAE / X / Y + retarget adapters
  planner.py                # recursion, search state, caching, compose
  ranking.py                # canonical chunks, global energy
  evaluate.py               # inference/sealing; evaluator isolated by CLI boundary
  report.py                 # after lock: verification metrics and plots
  tests/
    test_frozen_parity.py
    test_retarget.py
    test_compose.py
    test_ranking.py
    test_inference_isolation.py
  outputs/                  # gitignored, versioned; sealed predictions + logs
```

If model/evaluator separation needs `verify.py` to enforce no-private-data, add it; prefer separation over shaving one file at the cost of leakage. Keep existing `placement.py`, `xy.py`, `search.py`, `contracts.py`, the K≤3 harness and physical teacher **unchanged**. Any required compatibility fix should be localized, tested, and documented. Never add files inside `G7/release_v2/` or rewrite G7 data.

---

## 7. Visualization requirements at each phase

- **P0:** 23-scene public-only grid sheet (K labels hidden in planner-facing output), occupancy and legal cells, plus feature/mask size diagram and input OOD histogram (post-audit metadata, not search features).
- **P1:** side-by-side original/temporary target scene with target/goal marker and cVAE top-4 destination heatmaps. Show same frozen model under different task contexts, without using physical labels to steer proposals.
- **P2:** dependency-tree and actual ordered-composition diagram, including failed insertions/cycles on synthetic mock fixtures.
- **P3:** local search beam timeline, top candidate scene endpoints and global ranking breakdown (Y term, each stage X term, cost). Include order-permutation comparison.
- **P4:** one trace GIF of an entirely hypothetical candidate construction (clearly labeled **model prediction**, not verified execution); manifest+checksum summary.
- **P5/P6:** once verified, a physical GIF of the **selected** sequence with carried object and robot trajectories, terminal q_ref return and original target move; overlay the predicted task graph and report outcome. Certified G7 GIFs can be shown adjacent only as *oracle witnesses after evaluation*.

A missing visualization must be recorded explicitly as a gate failure or declared nonessential, not quietly omitted.

---

## 8. Reproducibility, resource and stop rules

- Default work is local code inspection, tiny mocks and parity tests. **Do not start high-core generation/training, remote jobs or physical search campaigns in the audit phase.** Do not interrupt the CF/NULL laptop experiment, modify unrelated worktrees, connect to unapproved servers or spend GPU time without accounting for the user's other jobs.
- Dataset expansion is complete. **Do not generate another K>3 dataset, restart old searches, regenerate witnesses, or rewrite certificates.**
- No model training is authorized for this experiment. If hashes/assets are missing: report `BLOCKED_CHECKPOINTS_MISSING` and exact remediation; do not make substitute weights.
- Logs use per-root deterministic seeds, batch/chunk sizes, torch and device settings, total model calls and wall time. On any OOM or failure, preserve partial logs and stop; never use an incomplete set as a full-run success claim.
- Abort on private-label import in planning module, model hash drift, missing parity, invalid geometry, silently truncated >20-object features, teacher calls during planning, non-reproducible selection, or a mismatch between prediction digest and evaluation digest.
- No automatic pushing/committing outside the isolated development branch. Existing experiment branches and data are read-only. Keep a change ledger with reason for every changed file.

---

## 9. Required reporting structure and explicit decision gates

Maintain the following in `AUDIT.md` (or separate concise phase reports) as the work advances:

1. **What was examined:** actual commit, files, functions, checkpoints, models, teacher, data lineage.
2. **Architecture match to Fig. 3(a):** each arrow maps to named API/call; flag any missing functionality.
3. **Mathematical semantics:** which probabilities are learned, which terms are heuristics, what is physically verifiable and what is not.
4. **Potential failure modes:** search incompleteness, cVAE support, recursion cycle, retarget calibration, stagewise-X qref mismatch, OOD count, endpoint Y shift, fair comparison and leakage.
5. **Necessary code changes:** file, function, precise adjustment, risk of regression, unit test, output artifact.
6. **Tests and evidence:** command used, pass/fail, numerical parity where relevant, elapsed time and resource usage.
7. **Independent reviewer / devil's-advocate pass:** try to construct a counterexample to each mechanism claim and adjudicate each CRITICAL concern; do not merely declare the design sound.
8. **Gate table:** P0–P6 `NOT_STARTED / PASS / CONDITIONAL / BLOCKED`, blocker and exact next action. A `CONDITIONAL` gate does not license TEST evaluation.
9. **Claim ledger:** `PROVEN`, `SUPPORTED_BY_DEV`, `HYPOTHESIS`, or `NOT_TESTED` for statements intended for the paper.
10. **Decision:** `PROCEED`, `REVISE_DESIGN`, or `BLOCKED` with reasons. If a core premise fails, recommend a scientific correction rather than inventing a passing experiment.

### Stop at these checkpoints

- **After audit:** show `AUDIT.md` + revised `plan.md`; no large compute or full implementation until blockers are resolved. Audit may propose minimal diagnostic code, but it must be clearly separated from claimed results.
- **After P0–P2:** show unit/parity/visualization artifacts and complexity measurements on mock/DEV; confirm remaining algorithm can in principle construct a 12-action sequence.
- **After P3:** show frozen experimental specification and a TEST-readiness assessment. Do **not** touch `release_v2` physical outcomes until the registered run is approved and sealed.
- **After P4:** only then run independent P5 verification, not before.

**Success criterion for this handoff:** a defensible feasibility audit, correctly scoped experimental design, minimal reproducible implementation, and an honest GO/NO-GO decision. Passing the tests is not equivalent to demonstrating success at K12; the primary TEST results decide that claim.

---

## 10. Exact first actions for the implementation agent

1. Read this file fully; create a **checkpointed audit to-do list**, not a generic implementation description.
2. Inspect commit `e07354b3c8`, G7 public release, code files and long teacher listed in §0, and the frozen model manifest. Verify the working branch and do not modify existing data.
3. Trace `public raw → contracts.view2d → dynamic features → frozen cVAE proposal → local XY → temporary retarget → nested compose → original Y-only endpoint → stagewise X → sealed decision → long teacher` through actual functions. Provide a call graph and **list precise missing adapters**.
4. Stress-test the concept on a hand-worked K6 and K12 chain **without consulting private release witnesses**, and assess the action-branching and score semantics.
5. Red-team the mathematical/protocol problems in §4, especially `px` vs conditional X, edited-endpoint Y vs rebased no-op, qref connector mismatch, same-endpoint order effects, old occupied-cell grammar and object padding.
6. Write `approach_b_final/recursive_kgt3/AUDIT.md` with evidence, tests possible now, risk status and required amendments. Revise the local copy of `plan.md` if the audit finds any inconsistency; preserve an explicit change log.
7. **STOP and report** an actionable PASS/CONDITIONAL/BLOCKED assessment. Only then proceed with minimal code under the phase gates as explicitly authorized.

### Repository sources

- https://github.com/Narendhiranv04/latent-causal-tamp/tree/naren/scaling2d-k12-test
- https://github.com/Narendhiranv04/latent-causal-tamp/blob/naren/scaling2d-k12-test/scaling2d_k12/G7/FINAL_REPORT_V2.md
- https://github.com/Narendhiranv04/latent-causal-tamp/blob/naren/scaling2d-k12-test/scaling2d_k12/teacher_long.py
- https://github.com/Narendhiranv04/latent-causal-tamp/blob/naren/approach-b-v3-4-final-benchmark/approach_b_final/reports/final_v34/BUNDLE_MANIFEST.json
- https://github.com/Narendhiranv04/latent-causal-tamp/blob/naren/k3-postablation-validation/approach_b_final/validation_k3/reports/TASK_RETARGET_REPORT.md
- https://github.com/Narendhiranv04/latent-causal-tamp/blob/naren/k3-ablation-gvlab2-20261120/approach_b_final/ablations_k3/reports/FINAL_REPORT.md
