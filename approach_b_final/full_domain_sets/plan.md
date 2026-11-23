# Approach B — Full-Legal-Domain Corrective Action-Set Selection
## Frozen cVAE top-4 seeding, staged full-domain expansion, matched search controls, and frozen X/Y execution-order scoring

**Version:** 1.1 — 23 November 2026; supersedes version 1.0 for this prospective follow-up. **Revision:** adds mandatory `PW_MCTS_SEEDED4` and matched staged-beam controls, while preserving soft-prior full-domain ablations and all prior safety/verification rules.  
**Project:** `Narendhiranv04/latent-causal-tamp`  
**Status:** **PROPOSED FOLLOW-UP.** No expanded-domain results, success gains, or new teacher queries are claimed here.  
**Historical study to preserve:** `naren/rss27-mcts-sets-klt3`, last reported P4 commit `b17c67d9cd` (verify complete SHA from Git before branching).  
**New isolated branch (proposed):** `naren/rss27-full-domain-set-search` from the verified P4 head. No merge, cherry-pick into released baselines, or edits to frozen historical reports.  
**Primary task:** **2D K1/K2** corrective relocations; planner receives the same **public `K_max=2` for every root**, with K0 NOOP and NONE ABSTAIN as safeguards. K3 and K>3 are excluded; 3D is excluded.  
**Models:** unchanged frozen V3.4 TaskCVAE `scratch_all` s0 and coupled X/Y s0, with exact manifest hashes. No training, model tuning or new outcome head in this study.

> **Research question:** Does removing the *top-four-destinations-per-object* hard search restriction improve physically verified K1/K2 repairs when frozen cVAE **initially seeds MCTS with top-four destinations per object, then progressively unlocks other legal cells**? Is this staged strategy more effective than a soft-prior full-domain MCTS from the outset, or than equally capable batched beam/simple search, at matched X/Y and wall-time budgets?

## 0. Why this study exists: findings already established

The completed fixed-pool experiment (`approach_b_final/mcts_sets/reports/P4_FINAL_DECISION.md` and `P3_PHYSICAL_VAL.md`) is **NULL** for K1/K2:

- EXACT_K2, original S1 top-four per object: **120/191 = 62.8%** under the **frozen operational** evaluator, median **817** ordered sequences, median live time **0.058 s**.
- UCT_SET@256: **121/191 = 63.4%**, 256 sequences, median **0.381 s** (**6.5× slower**). PW_UCT_SET@256: **123/191 = 64.4%**, no statistically demonstrated gain over exact or beam.
- K2 suffers considerably at 64-score budgets. Beam matches the predicted exhaustive choice more often than UCT at every reported budget. No proof that MCTS search beats simpler set search.
- These 191 roots belong to heavily reused **VAL development evidence**, not a fresh independent test. The physical evaluator counted `UNKNOWN_*` with value 0 as operational failures. A **strict** interpretation leaves approximately 19–25% unknown and is **inconclusive** by the registered rule.

**This study must not re-label that null result as success.** The new independent variable is **candidate-domain coverage**. The historical top-four search already exhausts its own frozen pool quickly; a wider pool can potentially add real repairs, but can also exacerbate X/Y misranking or computational cost. Neither direction is assumed.

### 0.1 Precisely what top-four means

The old frozen S1 sampler uses 64 prior-latent draws to estimate a destination marginal and retains an ordered **top-six list per eligible object**, of which the **top-four prefix** is the production pool. Four is **not** the total number of moves and **not** four globally chosen objects. Historical MCTS explored only this fixed pool; progressive widening could not leave it.

The existing code already provides the key ingredients, subject to source verification:

- `search.Root.legal_dests(root.cells0)`: the original-root legal supported cells, excluding *all originally occupied* cells and the goal cell.
- `placement.marginal(...)`: Monte Carlo approximation to the frozen cVAE's legal-cell destination distribution (S1 uses `n_z=64`); `placement.propose_rule(..., rule={name: "S1"})` returns ranked top-M cells.
- `search.Scorer.score(root, seqs)`: scores complete **ordered** sequences from the original root and returns `p11`, `py`, `px` (and `J` if present).
- `construct.assignments`, `exhaustive.stream`, `xy.choose` / `exhaustive.Selectors`: authoritative static grammar, permutation enumeration, no-op gate, admission and ties.
- `mcts_sets/search_sets.py`: existing fixed-pool set-MCTS, beam, random, budgeted X/Y oracle and test fixtures. Reuse and *extend minimally* rather than starting an unrelated stack.

**Critical code detail:** the historical sampler list is a top-M **Monte Carlo marginal**, not a proof of physical placeability or complete-task success. Frozen cVAE *proposal density* must not be described as calibrated repair-success probability.

## 1. Non-negotiable boundaries

1. **Strict division of responsibilities.** cVAE supplies object-conditioned destination *preferences* across the **entire publicly legal cell set** and an archived-consistent top-four seed list. Search chooses **unordered sets** of `(object,destination)` pairs; frozen X/Y evaluates **all physical execution permutations of each completed set** from `S0`. **Seeded MCTS first exposes top-four actions per object and later unlocks other cells; this is not a permanent top-four candidate restriction.** MCTS tree-add order never determines physical execution order.
2. **Same action grammar as V3.4.** Up to two distinct **movable non-target** objects, each moved **at most once**, to distinct originally empty, supported, legal, non-goal cells. No vacated-cell destinations, swaps, repeated moves, target moves, new grasp families, relaxed robot margins, teleportation, or extra staging actions.
3. **No privileged inference.** Only public `inputs`, original scene and root robot context, target, goal, legal cells. Never pass K, teacher labels/statuses, masks, blocker IDs, hidden certificates, successful interventions or test selection outcomes to cVAE, search, priority or termination.
4. **No edited-scene neural queries.** cVAE marginal computed only for original `S0`, once per root; X/Y called only with `S0` plus a complete original-root ordered repair. No intermediate-scene re-encoding, transition model, physical lookahead, IK or motion-planner calls within candidate exploration.
5. **The entire legal domain means support, not exhaustive evaluation.** An eligible `(o,d)` outside top-four (even outside top-six or unseen in 64 MC samples) must be **representable and reachable by a nonzero exploration mechanism**. Do not claim all action sets have actually been evaluated under a finite budget.
6. **Freeze model and decision rule:** `noop_gate=0.5`, `eta=0.3`, `alpha=beta=gamma=0` and exact `xy.choose` ordering/tie behavior. No hindsight threshold, rescaling, reward substitution at final decision, or candidate-specific teacher filters.
7. **Complete-order accounting:** for K1 evaluate one ordered X/Y sequence; for K2 evaluate **both** physical orders, or neither if the remaining score budget cannot pay for both. A cached ordered sequence is charged once to its method's budget. Count no-op consistently as one query token even if the underlying scorer optimizes it separately. Unique X/Y scores, model batches, decoder calls, CPU/GPU time, proposal-generation time and tree overhead are separate counters.
8. **One answer:** `REPAIR` with an ordered sequence, `NOOP`, or `ABSTAIN`. No execution-time retries or teacher feedback to search. Teacher independently assesses sealed answers only at evaluation.
9. **Report UNKNOWN faithfully.** In the primary *strict* evidence accounting, VERIFIED successes and sound CERTIFIED failures are decided; `UNKNOWN_*`, timeout and worker errors are not false. Also show frozen historical operational (`UNKNOWN`→0) results **separately** for parity. Do not convert unresolved outcomes into negative causal certificates.
10. **Historical protection:** no changes to frozen model bundle, teacher, training data, historical sealed predictions, existing null report or source branches. Preserve exact input/manifest hashes. If an audit finds drift, stop and report it rather than concealing it.

## 2. Formal action domain, prior and optimization

Let `S0` be the original public root; `O` all eligible movable non-target objects; and `D0(S0)` the common original-root legal destination set (or the exact object-specific legal set if existing *public static* rules require it). Define

\[
\mathcal A_{\mathrm{legal}} = \{(o,d):o\in O,\ d\in D_0(o\mid S_0)\}.
\]

The unordered corrective set `A` is a sorted immutable tuple of one or two pairs, with different objects and different destinations. A complete physical order is `r ∈ Perm(A)`. A candidate is not physically valid merely because `A` is statically legal.

### 2.1 Frozen cVAE destination prior, with guaranteed full-domain support

For each `o`, obtain the frozen S1 Monte Carlo marginal `p_cvae(d | S0, o, target, goal)` for every legal cell, **not just its `topk` indices**. Reuse the exact S1 64-draw / generator protocol; assert that sorting this marginal reproduces the archived top-six destinations and top-four prefix. Record sampler seed, MC draws, ties, and checkpoint. Do **not** silently increase samples and call it the frozen baseline.

Use a legal-domain mixture prior, *for expansion only*:

\[
\pi(o,d\mid S_0)= (1-\varepsilon)\frac{p_{\mathrm{cVAE}}(d\mid o,S_0)}{|O|}
+\varepsilon\frac{1}{|\mathcal A_{\mathrm{legal}}|},\qquad 0<\varepsilon\le1.
\]

If object-specific domains vary, normalize the object marginal and the legal-action uniform term correctly. This ensures every legal atomic action has positive proposal mass. **It is not a success estimator.** Freeze a small `epsilon` grid on development before locked evaluation (illustrative grid `{0.1,0.25,0.5}`), and compare the `epsilon=1` uniform-prior ablation. Do not assume tiny nonzero mass provides measurable coverage within finite search: explicitly audit out-of-top-four evaluation.

**No new cVAE checkpoint is trained.** Low/zero raw MC probability for an unsampled cell is handled by the uniform floor, not by inventing an empirical success probability or quietly excluding it. The resulting prior is a proposal distribution over object/destination actions, **not a probability of independent object selection** learned by cVAE.

### 2.2 Mandatory top-four-seeded, progressively expanding action domain (NEW in v1.1)

**What this means:** Keep the authoritative original-root S1 cVAE ranking **for each eligible object**, initially permitting MCTS to expand only the existing top-four destinations for that object. **As search progresses, make additional legal destinations eligible**: ranks 5–6, then every remaining legal cell (rank 7+). The first four are the starting *frontier*, **not** the only candidates, not four moves overall, and not guaranteed to be physically executed or X/Y-scored. MCTS still chooses objects jointly with destinations and builds unordered K1/K2 sets; X/Y chooses the physical order.

For root `S0` and object `o` define disjoint tiers:

- `T4(o)`: exactly the frozen S1 top-four prefix (fewer only if fewer public legal cells exist).
- `T56(o)`: frozen S1 ranks 5 and 6, excluding `T4`.
- `TTAIL(o)`: **all other** originally legal destinations, including cells not returned by 64 MC samples. Rank deterministically using the same full-grid frozen marginal, tie-breaking by numerical cell ID. Zero raw cVAE mass is legal and must remain reachable via the uniform floor/exploration stream.

The full action universe is always `A_legal`; the tiers only change **when an action becomes eligible for an ADD expansion**. Preserve a complete action registry with `object`, `dest`, `cvae_rank`, `tier`, `raw_prior`, `mixed_prior`, `eligible_since` and `first_expansion/scoring` records. `eligible` ≠ `expanded` ≠ `fully_scored` ≠ `committed`.

**Two independent mechanisms:**

1. **Global monotone staged release** of eligible actions. Initially enable `T4` for every object. At a preregistered fraction `f56` of the **non-noop** unique ordered X/Y scorer budget spent, enable `T56` for every object. At fraction `ftail` enable `TTAIL` for every object, where `0 < f56 < ftail < 1`. A proposed DEV-only comparison grid is `{(0.20,0.40), (0.25,0.50), (0.40,0.70)}`; select/freeze before independent outcomes. Compute progress as `(unique_ordered_scores - 1) / max(B_score - 1, 1)` (the no-op is excluded from the fraction but included in the charged budget); use a consistent, documented inclusive threshold. This schedule is an **opportunity-unlock**, not a promise that the entire tier will be scored in that finite run. **Deadlock rule:** if the currently eligible search space is fully exhausted before the next fraction threshold, unlock the next tier immediately (without charging fake scorer evaluations), log `EARLY_TIER_EXHAUSTION`, and apply the **identical rule in `BEAM_SEEDED4`**. Otherwise never advance tiers because an individual low score looked unpromising. Do not use hidden `K`, teacher labels, success estimates, or hindsight to advance tiers. Keep `B_score` finite for this staged variant.
2. **Node-local progressive widening** within currently eligible actions: `N_children(A) <= max(1, floor(k_pw * (N_visits(A)+1)^alpha_pw))`, with preregistered `k_pw>0` and `0<alpha_pw<1`. Within each tier, prioritize the frozen cVAE marginal (optionally mixed with legal-uniform probabilities); ensure a nonzero, seeded exploration route for every eligible action. Frozen rankings are not learned physical-success predictions. A node's unexpanded-action queue must be **refreshed when a new global tier unlocks**. A node declared exhausted under an earlier tier must be reopenable after unlock; never mark the root permanently exhausted just because `T4` is exhausted.

**Fairness controls:** The v1.0 `PW_MCTS_FULL` remains as a **soft-prior, all-legal-cells-eligible-from-start** control. Add `PW_MCTS_SEEDED4` as the **primary new hypothesis**. Also implement `BEAM_SEEDED4`, a strong batched beam with the **same global tier-release fractions, full legal action universe, direct low-singleton pair exploration, and measured budgets**; retain `BEAM_FULL` (all legal eligible immediately). This lets us separate *search type* from *top-four seeding/staging*. Include `PW_MCTS_UNIFORM` and `BEAM_FULL_UNIFORM` prior ablations as capacity permits. Do not let only MCTS benefit from opening the tail or from extra X/Y calls.

**At least these ablations (predeclare before tuning):** (i) `PW_MCTS_SEEDED4` versus `PW_MCTS_FULL` (effect of hard initial staging versus soft initial preference), (ii) `PW_MCTS_SEEDED4` versus `BEAM_SEEDED4` (effect of MCTS under identical staged access), and (iii) both against `EXACT4` / `EXACT6` (effect of a wider destination domain). An optional seeded-tail-uniform versus seeded-tail-cVAE comparison isolates tail ordering without silently changing model checkpoints. Report both raw source-prior and the fixed legal-uniform mixture floor. Do not fit a learned value head.

**Anti-starvation rule:** After tail unlock, the method must have a declared, positive *opportunity* to score at least one set using an off-top-four action on nontrivial fixtures before stopping when the remaining budget can pay for it. A small DEV-selected matched out-of-top-four evaluation reservation/direct-pair stream is allowed, **provided the staged beam receives the same allowance**. Never claim finite-budget coverage of *every* legal cell or guarantee an off-top-four success will be found. If an arm exhausts its budget before a tier unlock or before any tail set can fit, log `TIER_NOT_REACHED_BUDGET`/`TAIL_UNLOCKED_NOT_SCORED` and count the absence honestly.

**Pair synergy and canonicalization:** New tier eligibility must not silently change the static action grammar or create different representations of one set. A low-`p11` top-four singleton may be essential to an off-top-four pair: preserve pair exploration that does **not** prune by low singleton Y. The canonical expansion order / transposition policy must still make **every legal unordered K2 assignment reachable after full unlock**; verify on a tiny full-domain exact fixture, including pairs containing two tail actions and object-order counterexamples.

**The desired scientific distinction:** We are experimentally testing whether *starting from high-prior cVAE cells and only widening the action domain after gathering search evidence* is better than *giving MCTS every legal cell from its first visit*. Neither is claimed to be superior in advance. A top-four prefix is an **initial exploration prior**, not a proof of relevance or a permanent clipping rule.

### 2.3 X/Y remains the physical execution-order authority

For completed `A` calculate every `r ∈ Perm(A)` from `S0` using frozen `search.Scorer`. Let

\[
R(A)=\max_{r\in\mathrm{Perm}(A)} p_{11}(r\mid S_0),
\]

for **search guidance only**, with `p11 = P(Y_end=1) P(X_r=1 | Y_end=1)` under the frozen model. Keep `px` and `py` for error attribution. The final committed candidate is selected using unchanged `XY.choose` on **every fully scored ordered candidate**, including the no-op and admission rule. Reward `R(A)` is not a certified success, an upper bound on extensions, or an independently measured causal effect.

**Nonmonotonicity:** a singleton can have very low Y while a pair solves the task. Do not prune all pairs by singleton `p11` alone. Preserve search paths for pair synergy and test them explicitly.

### 2.4 Key statistical questions: separate coverage from ranking

The physically meaningful outcomes differ:

1. **Candidate recall:** does a successful labelled action set exist in the top-four pool, top-six pool, or only the expanded legal domain? This can only be a **lower bound over observed verified witnesses** unless all candidates have sound decided labels.
2. **Assignment search:** given all candidate actions, does a budgeted method discover promising sets (model score), and does it evaluate a genuinely successful set under independent teacher evidence?
3. **Model selection:** if a successful set is evaluated but a failing set is committed, that is an X/Y scoring/selection error, **not** a top-four candidate-recall failure.
4. **Compute cost:** does the method produce better **physically verified top-1 success** without prohibitive batch overhead or wall time?

Do not write "MCTS found the right blocker" unless independently supported by intervention/omission evidence; selecting an object is not causal attribution.

## 3. Required experiments and controls

### 3.1 Diagnostic D0 — Can the original top-four actually miss successful repairs?

First audit historical **already-decided** labels, hashes and successful complete ordered repair witnesses without new teacher calls. For each recorded **independently VERIFIED complete repair** on a public root, compare exact action signatures against:

- frozen `D4(o)`,
- frozen `D6(o)`,
- full public legal domain `D0(o)`.

Classify by `ALL_IN_TOP4`, `NEEDS_RANK5_6`, `NEEDS_BEYOND6`, `GRAMMAR_OUTSIDE_SCOPE`, `SOURCE_MISMATCH` and `INSUFFICIENT_EVIDENCE`. A successful K2 witness belongs to top-four only when **both** object destinations are in the appropriate per-object top-four lists. Distinguish failure because of **destination coverage** from a search process that selected the wrong object combination.

Report root-level witness *lower bounds*, number of historical decided witnesses, share of roots with any known out-of-pool witness, candidate/endpoint counts and coverage denominators. A known successful outside-top-four sequence establishes a concrete pool limitation. **Absence of such witnesses does not prove top-four sufficiency**, because the historical teacher did not exhaust every legal action set.

Do not rank candidate algorithms using any held-out/physical label. This diagnostic may access historical labels in **analysis only**, never in new search or its priorities. Clearly mark these roots as already-examined development evidence; this is hypothesis generation, not prospective test confirmation.

**D0 gate:** if clear out-of-pool witnesses exist, proceed. If none exist, still allow a **small, predeclared discovery pilot** in new K1/K2 roots; do not assert there is no opportunity. If most labels are unknown/sparse, label the diagnostic *UNRESOLVED* and report it.

### 3.2 Matched search families

| ID | Domain | Search / role | What it tests |
|---|---|---|---|
| `EXACT4` | S1 top 4/object | Frozen exhaustive K≤2; retain old exact method | Historical production reference |
| `EXACT6` | S1 top 6/object | Full batched K≤2 exhaustive **where within declared compute cap**; otherwise explicitly `NOT_RUN_CAP` | Wider proposal pool alone |
| `RAND_FULL` | **all legal actions** | Budgeted uniform valid set sampling, with stratified K1/K2 budget | Full-domain random control |
| `BEAM_SEEDED4` | **all legal actions; identical staged unlock** | Batched diversified beam/direct-pair search with the **same tier schedule** as seeded MCTS | Fair staged-search comparator |
| `BEAM_FULL` | **all legal actions from the start** | Budgeted, **batched**, prior-aware/diverse set beam with explicit low-singleton pair coverage | Strong simple search challenger |
| `PW_MCTS_SEEDED4` | **all legal actions; unlock top4 → ranks 5–6 → tail** | **Primary new v1.1 arm:** cVAE top-4 seeded, staged domain unlock + batched progressive-widening MCTS | Does seeded expansion improve candidate discovery/quality? |
| `PW_MCTS_FULL` | **all legal actions from the start** | Batched/parallel-leaf UCT with progressive widening, cVAE mixture prior and explicit STOP | Soft-prior full-domain MCTS ablation |
| `PW_MCTS_UNIFORM` | **all legal actions** | Identical search and budget, uniform action prior | Effect of cVAE guidance |
| `BEAM_FULL_UNIFORM` | **all legal actions** | Same beam except uniform/no cVAE prior | Simple search with no learned guidance |

Optionally include `BEAM4` / historical `UCT4` as archived context, **not** as substitutes for full-domain beam controls. An **unbatched** `PW_MCTS_FULL` can be shown as a runtime ablation, but the main claim requires actual batched live performance. No need to repeat old top-four physics unless protocol/source hashes require it; reuse only exact-contract cached labels.

`EXACT6` might be expensive on dense roots; use stream/chunk enumeration and declare the per-root maximum. Never imply it is exact over the full legal domain. On **tiny synthetic action spaces**, also include `EXACT_FULL` as a correctness oracle only; on typical dense real roots, do not enumerate millions of pairs merely to manufacture a full-domain gold optimum.

### 3.3 Strong, non-naive expanded-domain beam

Do **not** simply scan every singleton, keep those with highest `p11`, then expand them: this can discard pairs whose two singletons have poor Y. Use a predeclared, balanced expansion policy, e.g.:

- A cVAE-prior candidate stream **plus** a uniform legal stream, both with nonzero access to every legal action.
- Evaluate singleton sets and selected pairs **in batches**; preserve a preregistered portion of the score budget for **direct pair proposals** that do not require either singleton to have high p11.
- Maintain diversity across **objects**, destination ranks/regions and pair novelty. The exact mixture weights, beam width, direct-pair share and budget schedule are fixed from DEV model-only diagnostics, not EVAL physical outcomes.
- Same complete-order scoring, no-op, cache, thresholds and final selector as MCTS.

An additional **stratified random-pair** control is strongly encouraged if a more sophisticated beam is used. The point is to show a real *search-method* advantage, not defeat a deliberately weak beam.

### 3.4 Batched full-domain MCTS requirements

- Use **canonical unordered assignments**. No duplicate pair sets; distinguish a tree with a documented canonical expansion ordering from a transposition graph. Test index-seed bias; an action can only be added if object and destination are not already used.
- Implement **both** `PW_MCTS_SEEDED4` (initial top-four *per object* → unlock S1 ranks 5–6 → unlock remaining original legal cells) **and** `PW_MCTS_FULL` (all actions eligible from the start). The seeded arm has **two levels of expansion control**: global budget-progress tier release and node-local visit-based progressive widening. Log per-root tier transitions and refresh formerly exhausted/untried nodes after unlock. Never wait for every top-four combination to be scored before allowing ranks 5+; the release rule must operate within realistic B_score.
- Implement **matched** `BEAM_SEEDED4`, with same access schedule and nonzero direct-pair/tail exploration, plus `BEAM_FULL`. Record the four comparisons seeded-MCTS/full-MCTS/seeded-beam/full-beam separately; do not conclude MCTS is necessary from an improvement that the staged beam also achieves.
- `ADD(o,d)` is a search edge, not a physical move. A nonempty assignment has `STOP`; STOP at K1 may score the singleton, and search can still extend that singleton to K2. K2 nodes are terminal.
- Use UCT or documented PUCT with cVAE prior only as **exploration**, progressive widening over full legal candidates, visit counts and deterministic tie policies. Back up **terminal predicted** rewards, not teacher results. Do not claim search-time visits train a transferable policy.
- Batch **multiple distinct complete assignments** before X/Y calls; each K2 candidate contributes both order permutations. Use deterministic batched frontier selection or explicit virtual-loss/bookkeeping so one batch does not duplicate terminal candidates or change score accounting. Distinguish a batched UCT approximation from mathematically sequential UCT; unit-test both on small problems.
- **Full-domain coverage proof:** include fixtures where the only positive candidate uses a legal cell ranked 7th or not observed in the first 64 cVAE samples. After **full tier unlock** and with adequate budget, the staged search must be capable of reaching it (not guaranteed to do so at a fixed low budget). Add a fixture where T4 exhausts before unlocking T56 and a fixture where an already-visited node becomes viable after tail unlock. Positive support alone is insufficient: measure actions eligible/expanded, sets fully scored, visits and outcomes in `TOP4_ONLY`, `ONE_OFF4`, `TWO_OFF4`, and `BEYOND6` strata. Include `BEYOND6_NOT_IN_MC_DRAW` where identifiable.
- If explicit exploration quotas are used to make non-top-four discovery observable, preregister them and apply a matched non-top-four budget to the expanded beam. Do not give MCTS special access to a wider pool than its opponents.
- Hard limits: unique ordered scores (`B_score`), model batches (`B_batch`), wall time (`B_wall`), iteration guard, peak RAM/GPU memory. No silent overrun, no partial 2-order scoring, no infinite loops. Record termination reason for every run.
- Do not use the full-domain search result to retune cVAE weights or X/Y calibration.

### 3.5 Model-only budgets and fair runtime measurements

Suggested **pilot**, subject to DEV hardware profiling and preregistration: `B_score ∈ {64,256,1024,4096}` (all counts include no-op). Exact4 and Exact6 have natural exhaustive costs. For controls, also match **actual wall-time envelopes**, because previous sequential MCTS was 6.5× slower despite 69% fewer sequence evaluations. A method must be reported on at least two axes:

1. verified/task prediction outcome versus **unique ordered X/Y scores**, and
2. verified/task prediction outcome versus **end-to-end wall-clock time** (original public root → proposal prior → search → committed decision), on the **same machine**, with GPU synchronization, warmups and repeated timed trials.

Report **decoder/MC prior compute** even if the score budget excludes it. If prior marginals are cached to make per-algorithm replay fair, show an **uncached complete latency** figure as primary deployment cost; separate shared precomputation from downstream per-arm runtime. Record #X/Y batches, mean/max batch sizes and peak GPU memory. Never claim speedup from a replayed score table: live scorer calls on a preselected, hash-seeded subset are mandatory.

On new candidate pools, model-only replay is possible only after storing actually scored sequences; **do not build a fake full-domain table and then omit its preprocessing cost while claiming deployable speed**. Tiny exact or bounded replay is permitted as explicitly offline diagnostics.

## 4. Implementation plan (minimal changes)

**Base branch:** create the proposed isolated branch from the verified `naren/rss27-mcts-sets-klt3` P4 head after confirming clean worktree, full SHA and all protected report hashes. Use the prior code as a regression oracle, *not* a target for modifications.

Proposed minimal directory:

```text
approach_b_final/full_domain_sets/
  plan.md                 # exact copy of THIS contract
  domain.py               # legal full-domain actions + frozen marginal prior + source IDs
  search.py               # shared cached scorer, batchable beam/random/MCTS, final chooser
  run.py                  # frozen bundle, public-root driver, locked experimental runs
  analyze.py              # diagnostic evidence, paired metrics, manifests, decisions
  figs.py                 # 2D public-scene / prior / set-search / outcome plots
  tests/test_full.py      # legality, full support, microfixtures, parity and budgets
  reports/                # only new provenance, preregistration and results
```

Prefer **fewer files**, not more, if clean responsibility boundaries permit. Keep ordinary modules approximately 150–300 logical lines; split only for actual separation of concerns. Reuse `approach_b_final/mcts_sets/search_sets.py` and existing geometry/teacher **interfaces** via imports/read-only code; do not duplicate a separate robot stack, sampler training system, dataset loader framework or physics oracle. Existing large source files need not be refactored. If prior `search_sets` requires changing to support lazy full-domain actions or batch scores, implement wrappers in the new package, not an edit of the frozen baseline.

**Important: validate real API details rather than blindly following filenames.** `placement.marginal` may need the same task-conditioned inputs/normalization used in `search.Sampler.propose_many`. Test matching the exact archived top-six proposal list, not just approximating it visually. If sampled S1 logits and reconstructed priors differ, stop and resolve the source/seed discrepancy before any results.

## 5. Milestones, gates, deliverables

### P0 — Provenance and immutable parity (read-only audit)

- Read actual source on both parent and frozen V3.4 lineage. Read `mcts_sets/plan.md`, `P2_PREREG.md`, `P3_PHYSICAL_VAL.md`, `P4_FINAL_DECISION.md`, `search_sets.py`, `run.py`, `README.md` and 13 historical tests. Read `placement.py`, `search.py`, `exhaustive.py`, `construct.py`, `xy.py`, `benchmark.py`, `contracts.py`, `evaluate.py` and source manifests.
- Check branch ancestry, git status, full commit SHAs, model/scale hashes, valid datasets/private path availability and teacher contract. Confirm 13 original tests pass and sample original top-four decisions exactly reproduce the archived fixed-pool outputs on a deterministic audit subset.
- Commit `reports/P0_SOURCE_AUDIT.md`, `reports/P0_FROZEN_PROTOCOL.json`, `reports/P0_GAPS.md`, `reports/P0_PARITY.json`. Identify any previously used DEV/VAL/TEST roots and which genuinely fresh lineages are accessible. Preserve secrets and private data paths outside Git.
- **Stop gate:** absent checkpoint, inconsistent manifests, invalid static legality or any unintended private inference field.

### P1 — Candidate-recall diagnosis (before new MCTS)

- Reconstruct per-object original S1 top-four/top-six and complete legal cells; compare known complete, contract-matched **physically successful** ordered witnesses against the pools, as specified in §3.1.
- Report `KNOWN_WITNESS_OUTSIDE_TOP4`, `KNOWN_WITNESS_OUTSIDE_TOP6`, conditional upper/lower statements, missing/unknown label counts, K1/K2 separately, and at least 4 real original-root 2D figures with top4/6/full legal overlay and historical witness if one exists. All figures must be grounded in records, not schematic inventions presented as evidence.
- Report novelty strata and prior-mass coverage, prior MC variance (diagnostic only), count of legal actions per object and estimated full-domain K2 pair count (analytically; no unbounded materialization).
- **Decision gate:** if positive examples are found, record their provenance. If not, state `OPPORTUNITY_UNPROVEN`, not `TOP4_SUFFICIENT`, and either proceed to a small prospective, bounded discovery pilot or explicitly stop for insufficient evidence/resource authorization. **Do not use the labels to build a special selected action list for the planner.**

### P2 — Correct algorithm / synthetic and small real model-only pilot

- Implement `domain.py`, `search.py` and exact microfixtures. Tests must cover:
  - every legal action represented, including outside top4/top6; no illegal/fixed/goal/originally-occupied destination;
  - exact `D4`/`D6` recovery and unchanged historical selector outcome;
  - canonical assignment enumeration, no duplicate object/destination, all K2 physical orders;
  - singleton score low / pair score high, order-dependent X with shared Y, off-top4-only winning pair;
  - marginal normalization, all-action nonzero proposal support, seed stability and deterministic topk ties;
  - full-domain tiny exact parity, NOOP/ABSTAIN and final `xy.choose` ties;
  - **new:** initially only top-four actions eligible per object; top-five/six and all tail cells unlock in the specified order at exact declared budget fractions; legal cell unseen in MC still selectable; unlock cannot depend on success/K/teacher;
  - **new:** a previously exhausted node reopens on tier unlock; every legal unordered K2 set remains reachable after full unlock even with canonical object ordering; low-singleton/high-pair plus off4-only-winner fixtures;
  - **new:** `PW_MCTS_SEEDED4`, `PW_MCTS_FULL`, `BEAM_SEEDED4`, `BEAM_FULL` share the exact same full legal domain, and seeded arms the same access schedule; no duplicates or premature physical-order choice;
  - cache/batch invariance, correct token accounting and refusal of a partially affordable pair;
  - no oracle/teacher call, no private K/labels, no intermediate neural scene;
  - time/batch/memory/iteration termination without loops, scorer batch output aligned with input sequences.
- Use the **same** frozen prior for full-domain beam and MCTS, and a uniform-prior control for both. Preregister two separate null hypotheses: *staging itself has no improvement* (`PW_MCTS_SEEDED4` vs `PW_MCTS_FULL`) and *MCTS adds nothing beyond matched staged beam* (`PW_MCTS_SEEDED4` vs `BEAM_SEEDED4`). Register outcomes for expansion and physical verification separately; keep `EXACT4` as the historical anchor. Evaluate model-only DEV roots with matched score budgets and record actual model-score regret against the **best evaluated reference**; never call that full-domain global regret unless exact full enumeration was performed.
- Tune (on DEV **model-only** diagnostics): epsilon, **seeded tier-release fractions `f56, ftail`, off-top-four evaluation reservation**, widening, UCT constant, batch size, beam width, direct-pair quota. Keep the tuning grid small, preregister all options before viewing physical results, use root-level seeds and audit overfitting to the fixed-pool predicted optimum.
- Save `reports/P2_TESTS.json`, `reports/P2_PRIOR_PARITY.md`, `reports/P2_MODEL_ONLY_DEV.md`, `reports/P2_BUDGET_LATENCY.md` and figures. **If model-only MCTS is consistently slower/worse than expanded beam, retain beam as the primary challenger; do not force a positive MCTS narrative.**

### P3 — Lock the prospective physical test *before* outcomes

- Freeze arm configurations, model bundle hashes, dataset cohort and lineage manifest, primary budgets, hardware, exact static grammar, final selector and intended physical verification queries. Produce a deterministic input/prediction/query seal (`sha256`) and push it as a commit **before any new physical teacher call**.
- **Preferred scientific path:** a genuinely new lineage-disjoint 2D evaluation cohort generated/frozen after model-selection lock, with original root scenes and K-blind public planner inputs; record proof of independence from frozen training, historical VAL, exposed TEST and V3.4 protected fresh cohort. The root generator/teacher must remain unchanged. If no new independent cohort is available, perform an explicitly **development-only** VAL pilot and declare that no independent generalization claim is possible.
- Run every algorithm on **all candidate cohort roots** without knowledge of private true K. Primary evaluator-side outcomes: K1/K2. K0 and NONE are safeguards. Do not select roots based on expected success, prior scores or historical labels.
- For primary physical comparison, **if independently authorized and within budget**, preregister at minimum `EXACT4`, `BEAM_FULL`, `PW_MCTS_FULL`, **`PW_MCTS_SEEDED4` and `BEAM_SEEDED4`**, plus `RAND_FULL` at one frozen matched budget. If queries exceed cap, predeclare a reduced paired root cohort or a smaller explicitly labeled physical arm subset **before** unblinding; do not quietly omit the matched seeded beam or compare an MCTS with a weaker/incomparable search space. Also `EXACT6` if computationally feasible and/or a preregistered compact sample. Prior ablations may be model-only first; include physical arms only if manifest/budget allows, frozen in advance.
- Pair all primary algorithms on the same roots. Query only their **sealed top-1 REPAIR sequences**, deduplicate exact `(root, ordered sequence, teacher-contract-hash)` against independent verified caches, and keep three-valued statuses. Never use teacher results to revise the chosen action, add a second try, alter thresholds, or choose the next root.
- Proposed resource ceiling **requires explicit owner/host authorization before launch**: at most **1,200 new 2D ordered repair verification queries** and **24 total physical-worker CPU-hours** for this NEW study (do not infer unused allowance carries from the earlier MCTS study), with any stricter local host limit taking precedence. No 3D/K3 queries. Precompute the query manifest; if it exceeds the cap, choose complete paired roots by a preregistered hash, not opportunistic truncation. Stop at the CPU cap. No retries to turn UNKNOWN into success/failure.
- Physical teacher not available/authorized? Finish P0–P2, freeze the query manifest and stop. Never substitute model predictions for real task-success labels.
- Save `reports/P3_PREREG.md`, `P3_FROZEN_PARAMS.json`, `P3_SEAL.json`, `P3_QUERY_MANIFEST.jsonl`, `P3_PHYSICAL.json`, `P3_PER_ROOT.jsonl`, and a transparent resource log, when permitted.

### P4 — Analysis, physical error decomposition and final choice

**Primary efficacy:** on the prospective **independent** cohort when available, paired K1/K2 **strict decided-label** verified top-1 task success, with UNKNOWN and coverage explicitly shown. Also report all-root intention-to-treat bounds or operational budget-policy outcome separately, without confusing unknowns with impossible cases. Use cluster/bootstrap resampling by independent root/lineage and present paired 95% intervals, wins/losses and denominators. Separate K1 and K2.

**Primary practical cost:** median and tail end-to-end latency; X/Y ordered scores; GPU batches and average batch size; cVAE marginal cost; total compute; peak memory. Evaluate live, not only from score-table replay.

**Attribution:**

- `POOL_MISS_CONFIRMED`: independent successful witness exists outside D4 and was unavailable to EXACT4.
- `RETRIEVAL_FAILURE`: candidate is in the algorithm's legal domain but it did not evaluate it under its budget; report when actual evidence exists.
- `TIER_LOCKED`: a candidate was in the full legal domain but its tier was not unlocked within the declared budget (separate this from failure to expand a tier that was already unlocked).
- `UNLOCKED_NOT_EXPANDED` versus `EXPANDED_NOT_SCORED`: keep these distinct; tree expansion is not an X/Y evaluation.
- `SCORER_RANKING_FAILURE`: a successful evaluated candidate loses to the committed failing candidate (only when both outcomes decided).
- `ORDER_SELECTION_FAILURE`: same endpoint, different decided physical X/order outcomes and the model selected the wrong order.
- `UNRESOLVED`: teacher UNKNOWN, insufficient coverage, or ambiguous scope; never silently assign a cause.

Report whether expanded beam or expanded MCTS is responsible for gains, whether the gain comes from top5–6 or truly outside top6, and whether actual latency rises. Don't claim a "new learned action selector" or "causal graph": all learned weights are unchanged.

**Decision rules must be registered in P3, not invented afterward.** Suggested strict evidence categories (parameters can be frozen before P3):

- `EXPANSION_HELPFUL`: lower paired 95% CI of (best prespecified expanded arm − EXACT4) **> 0** on independent verified top-1 outcomes, with adequate decided/coverage and tolerable registered latency overhead.
- `SEEDED_EXPANSION_HELPFUL`: seeded MCTS beats **soft-prior full-domain MCTS** at matched budgets with a prospective paired improvement and acceptable wall time; if only model-score evidence exists, label the result *model-only*.
- `MCTS_ADDED_VALUE`: the preregistered seeded MCTS beats **matched seeded beam** (and the stronger full-domain beam where applicable) under matched score and wall budgets, with a positive lower paired CI; otherwise do not say MCTS is required.
- `EXPANSION_NOT_ESTABLISHED`: no robust gain, high UNKNOWN or inadequate independent cohort.
- `EXPANSION_HARMFUL`: credible reduction in verified success or unacceptable wall/compute cost.

The **best expanded arm must be chosen in advance on DEV** (or adjust multiplicity if several arms are tested against EXACT4). A favorable selected result on reused VAL alone is **development evidence** and cannot satisfy an independent confirmation claim. Also report absolute success fractions, uncertainty in unresolved rates and operating cost.

**Final recommendation could be**: keep EXACT4; switch only to top6 exhaustive; adopt an expanded beam; adopt batched expanded MCTS; or conclude that X/Y misranking dominates candidate recall. Every verdict is acceptable if supported.

### P5 — Optional, explicitly OUTSIDE this study

No automatic K3/K>3 progression and no re-training. After a positive K1/K2 full-domain study, request a separately preregistered K3 experiment with its own combinatorial, batching and physical-label budgets. K>3 requires additional validated composition/prediction semantics and is not justified here.

## 6. Mandatory quantitative reporting and visualization

Create figures using actual scene data, never fabricated teacher trajectories:

1. **Original 2D scene map:** all objects, fixed/movable, target/goal, full original legal cells, top4 and top5–6, ranked cVAE prior heatmaps per highlighted object. Distinguish top6 from **unseen-but-legal** cells.
2. **Search allocation + tier-release plot:** show `PW_MCTS_SEEDED4` alongside `PW_MCTS_FULL`, `BEAM_SEEDED4` and `BEAM_FULL`. Plot vertical unlock boundaries (`T4`→`T56`→`TTAIL`) as score-budget fractions, eligible vs actually expanded vs fully scored action/set counts, K and cVAE rank strata (`top4`, `5–6`, `>6`), object diversity, score and branch visits. Explain MCTS insertion order is **not** the physical order.
3. **Physical-order comparison:** selected pair permutations with shared predicted Y, order-specific X, p11 and chosen execution sequence; show actual teacher witnesses/paths only if verified and available.
4. **Prior/budget curves:** candidate novelty, model score vs B_score, proportion of budget spent outside D4, latency, GPU batches, expanded success vs SAME comparator.
5. **Physical success with UNKNOWN:** K1/K2 paired absolute and delta confidence intervals, strict/operational separate, failure attribution and timing tradeoff.

Every plot must state cohort, number of roots, score budget, whether values are **predicted, verified or UNKNOWN**, and exact code/model/teacher version. Provide machine-readable `jsonl` per-root records (proposed actions, prior mass, visited sets, selected order, score breakdown, counters, stop reason, teacher status), CSV summaries, and full commands.

## 7. Final deliverables and integrity checklist

- New isolated branch, commits for **P0/P1 diagnostic**, **P2 implementation and model-only**, **P3 frozen pre-teacher seal**, **P4 verification and final analysis**; no merging.
- `README.md` with exact environment variables and commands, dependencies/hashes, data lineage and reproduction instructions.
- All new and historical regression tests pass, including checkpoint parity and privacy smoke test.
- New model weights: **zero**. Search-time teacher calls: **zero**. Inference inputs: original public S0 only.
- No protected evaluation cohort touched for tuning; no new physical work beyond explicit caps/authorization.
- Results distinguish **coverage** (available in search domain), **retrieval** (actually evaluated), **selection** (which predicted repair committed), **verified physical execution**, and **wall time**.
- An explicit honest P4 recommendation: **keep simple baseline** if expanded search is no better or too slow; no invented positive result and no silent protocol changes.

**v1.1 experimental principle:** Top-four-seeded progressive widening is the **primary new hypothesis**, not a guaranteed upgrade. The top-four cVAE destinations are merely initial eligible ADD actions per object; ranks 5–6 and then *every other publicly legal cell* must become eligible on a declared progression schedule and be testably reachable. Soft-prior full-domain MCTS and equivalently staged full-domain beam are mandatory controls. A better result from both seeded arms is evidence for *staged candidate release*, not specifically for MCTS.

**Core principle:** Full-domain MCTS is a hypothesis, not the conclusion. The first question is whether the old top-four **destination recall** is a real failure source. The second is whether searching that wider space can improve **physical top-1 success** more efficiently than strong, batched, expanded-domain alternatives.
