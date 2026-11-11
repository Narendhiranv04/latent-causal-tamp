# Approach B — P26–P30: Universal Corrective-Sequence Search
## Implementation instructions for Claude Opus 5.5 High

**Status:** New research extension, prospective design. **This document is not an amendment to, or reinterpretation of, the completed P24/P25 experiment.**

**Repository:** `https://github.com/Narendhiranv04/latent-causal-tamp`  
**Frozen baseline commit:** `e113c66808c4ab4682196f1fa62ae51885b08ca3` on `approach-b-xy-v1` (P25 closed).  
**Create a new branch:** `approach-b-universal-search` from the exact P25 commit, with separate run/figure/report namespaces. Do not push changes to the historical P25 branch.  
**Required source reading before coding:**
- `responses-phases/METHODOLOGY_FINAL_IMPLEMENTED.md`, `responses-phases/0131_BXY_P24_ONE_SHOT_CONFIRMATION.md`, `responses-phases/0132_BXY_P25_FINAL_METHOD_AND_FINDINGS.md`, and `responses-phases/0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md`;
- `bxy_p20_k34.py` (`candidates`, `root_design`), `bxy_p16.py`, `bxy_p17_data.py` (`phi_y`, `phi_x`, `view`), `bxy_p11.py` (`Model`, `predict_all`, `choose`), `bxy_p24_confirm.py` (frozen ensembles), `bxy_p24_analysis.py`, `bxy_p19_audit.py`, `bxy_teacher.py` (`eligible`, `xkey`, `ykey`, `x_query`, `y_query`, `pair`), `bd_2d.py`, F1 implementation, and tests.

## 0. User intent — non-negotiable

> Given a scene and target task, **consider the complete, explicitly defined set of possible corrective actions, destinations, lengths, and orderings** — including useless, harmful, physically impossible, and target-nonrestoring proposals. Do **not** obtain candidates by first knowing or estimating from generator-intended labels which sequences repair the scene. The learned model predicts whether a proposed **ordered relocation sequence is physically executable (X)** and whether its **edited scene restores the target task (Y)**. Search then chooses a high-quality correction under a cost objective. A physical teacher verifies the selected proposals, not the generator's preferred repairs.

**Do not confuse four distinct concepts:**
1. **Complete underlying action space** — *every legal symbolic sequence is representable and enumerable*, with mathematical rules and a coverage proof on tiny cases.
2. **Materializing/scoring every sequence** — generally infeasible at K=4; use lazy complete-by-construction enumeration and an explicit compute budget.
3. **Using a learned probability to order the search** — allowed, but a heuristic; not a completeness or global-optimality certificate under a finite budget.
4. **Teacher certification** — attempted X/Y outcomes for selected candidates; non-attempted and budget-censored sequences are **unknown**, never 0.

**Mandatory scientific honesty:** Search must report `FOUND_VERIFIED`, `EXHAUSTED_DEFINED_SPACE`, `BUDGET_EXHAUSTED_UNKNOWN`, `TEACHER_CENSORED`, or another precise terminal state. It must **never** report “no feasible repair exists” when it merely ran out of search/verification budget. A learned cost is not an admissible lower bound unless specifically proved.

## 1. Frozen scientific semantics — preserve exactly

- Domain: existing planar **finite-width 3R arm**, 8×8 supported resting lattice, continuous robot joint motion, declared side-grasp skills, fixed `q0` and `q_ref` (`q_ref=q0` in P21/P24 data), existing target and obstacle geometry.
- A candidate `r=((o1,d1),...,(om,dm))`, `0<=m<=K_search` (`K_search=4` for the initial study; original teacher supports up to six corrective moves subject to existing `bc.MAX_ACTIONS`). **Each movable object may be relocated at most once** while retaining the existing teacher contract. Do not silently add repeated moves, pushing, grasp changes, new skills, or a different robot.
- `X(r)=1`: the robot executes the actions in order from `q0`, carries achieved joint states across relocations (NO reset between them), then executes **one** gripper-free terminal connector to `q_ref`. `Y(r)=1`: the original target task is physically possible from `q_ref` in the hypothetical edited scene, independently of whether X succeeds. The same final object poses across different action orders share one Y. Success is `X AND Y`.
- F1 remains an *analytic* structural/skill screen; F2 ordered-prefix X, F3 edited-scene Y, F4 omissions via F2/F3, F5 optional quadratic X/Y interaction. Main search arms: **E** (uncoupled X/Y), **D** (quadratic X/Y), matched **DIRECT-GEO** and **G** order-invariant control. GEO2 and SYM stay as implemented. Existing frozen checkpoint identities must not change.
- Complete-success scoring: `p_succ(r)=sigmoid(b_s)*sigmoid(a_r+w_r)` for D; E has `w_r=0`; no-op uses `P(Y0=1)`. Continue exact scene deduplication; never create one Y for every order.
- Selection objective (frozen family, with prospectively specified policy variants): `C(r) = -log(max(p_succ(r), eps)) + alpha*m + beta*C_displacement(r) + gamma*J_hat(r)`; choose lower cost among candidates *examined by the search*. Report score, verification calls, actual outcome, m, displacement, and witnessed travel separately.

### Important physical interpretation
A prefix can fail its **terminal connector** to `q_ref` and yet be extendable by further relocations, because later edits could clear the connector. Do not prune all extensions of such a prefix. Likewise, a target that remains impossible after the first three moves may become feasible after the fourth; never treat Y(prefix)=0 as a prohibition on expansion. A fixed-budget `NO_PLAN_FOUND/TIMEOUT` is not a sound pruning proof. Every atomic move must be judged in the scene and achieved robot configuration in which it is attempted; analytic geometry alone is not a substitute for a full physical X witness.

## 2. Define the *universal* symbolic search domain first

Write a versioned `ACTION_DOMAIN_V1.json` specifying the domain, including:

- `M(S0)`: **all physical movable, non-target objects**. Read only mobility identities/type from allowed scene data; do NOT use `construction`, `forced_order`, `K_intent`, `K_cert`, named `repair`/`blocker`/`distractor` roles, original catalogue membership, teacher labels or hidden generator metadata to decide which objects to consider. If the legacy record's `roles` map is needed solely as the teacher's set of movable IDs, take keys only, never its semantic values. State and test this explicitly.
- `D(S_t,o)`: every supported lattice cell that is a physically and symbolically valid **resting destination at step t**: empty **at that step**, nontrivial (not the object's current cell), compatible with static obstacles, boundary, support, object size and the existing placement grammar. A destination vacated by an earlier action becomes available. Do not blacklist far cells, harmful destinations, the target goal, access-occluding cells or the reference corridor *merely because they are unfavorable*; these are potential negatives to be predicted. Exclude only objective invalidities with a recorded reason.
- No moving the target as a corrective action; target operation occurs after correction. No simultaneous swaps, no moving fixed structures and no duplicate relocation of a movable object under the existing teacher's single-move-per-object contract. Explicitly distinguish these **out-of-domain / syntactically invalid** actions from in-domain sequences that have X=0 or Y=0.
- Include the empty sequence `r=()` (no-op), all shorter stopping lengths `m=1,...,K_search`, all object selections, all destinations, and all permutations under the domain grammar. There must be **no intended-blocker whitelist**.
- A branch is a **sequence**, not just a final set of moved object poses. Two permutations with the same endpoint are different X nodes and one Y node. Preserve full ordered ancestry and final edit signature.

Mathematically, before collision/occupancy reductions, an upper bound is `N(K) <= 1 + sum_{k=1..K} P(n,k) D^k` for `n` movable objects and up to `D` destinations per action. Example: with 6 movables, 50 possible destinations and K=4, the K=4 term alone is **2.25 billion** combinations. Do not attempt to materialize this list. Its size is why **implicit complete action-space representation** and **bounded lazy search** are both essential.

**Required semantics test:** A sequence does not disappear because it is not in `bxy_p20_k34.candidates(rec)`. The *new* enumerator must be independent of P20's ground-truth-informed `construction.options`, intended repair, learned labels and any previous catalogue. Legacy catalogue is a comparison baseline ONLY.

## 3. Architecture — minimal implementation; reuse existing code

Propose exact API signatures during P26. Target a small number of new, focused modules (each ideally <=300–400 lines, exceptions justified):

1. `bxy_fullspace.py`: immutable symbolic scene/state representation; all-objects/all-destinations action generator; lazy depth-limited enumerator; canonical signatures, exact endpoint identities, provably sound syntactic filters; deterministic ordering. **No teacher, no neural model, no hidden labels.**
2. `bxy_fullscore.py`: bridge universal candidates into existing label-free X/Y model scorer views and E/D/DIRECT/G frozen ensemble; terminal F1 check; batching, Y endpoint dedup, cache invalidation, shared scene features; no learning or labels.
3. `bxy_fullsearch.py`: bounded deterministic search over fullspace with learned priority and *sound only* structural pruning, candidate verification, budget/time accounting, resumability and clear status. Optional exhaustive small-domain oracle in same module if short.
4. `bxy_full_eval.py`: matched reference search policies, coverage/quality/compute metrics and evaluations; NO adaptation to historical P24 labels.
5. Focused tests `tests/test_bxy_fullspace.py`, `tests/test_bxy_fullscore.py`, `tests/test_bxy_fullsearch.py` and stage-specific scripts/plots. New run namespaces e.g. `runs/approach_b/bxy_p26_fullspace_v1/`, `bxy_p27_fullsearch_v1/`, etc. Avoid a directory forest.

Reuse `bxy_teacher`, F1, GEO2, frozen `Model`, existing read-only development-scene records, model custody files and hash routines. Do **not** modify historical evidence artifacts or P24's one-shot cohort/labels/predictions. If a bridge requires changing a legacy function, prefer a new adapter; justify and regression-test any actual change.

### Scoring implementation contract

- Build dynamic scorer views with `x_seqs`, `y_poses`, `parent` and `y0` matching `bxy_p11.Model.coeffs`. Deduplicate Y by **actual edited scene endpoint**, not a role/sequence label.
- Process candidate chunks or root-local caches to avoid in-memory O(fullspace) materialization; exact numeric equivalence to scoring the same candidate through the existing model adapter is mandatory.
- Every candidate's prediction must depend only on initial scene, the full ordered action sequence, its hypothetical endpoint, available physical model parameters and frozen checkpoint. No teacher result, witness, ground-truth K, test-set performance, generator `options`, `kind` or privileged `roles` value may enter scoring.
- Note: F2 has learned order/geometry features, but **does not predict intermediate joint states**. These belong to the teacher. Prediction under longer/unseen sequences is out-of-distribution until measured.
- If F1's `complete_ok` rejects a complete stopping sequence, record which **sound** physical/symbolic rule rejected it and its negative kind. If any F1 screen is merely heuristic or can have false negatives against executable teacher witnesses, it must be demoted to ranking, not completeness pruning. *Prefix pruning requires a separate sound proof*; terminal F1 validity cannot automatically be promoted to subtree pruning.

## 4. Search protocol — complete in principle, bounded in practice

Implement two separate modes:

**Mode A: exhaustive reference** on tiny, explicit domains (e.g. 1–3 movable discs, 4–8 valid parking cells, `K<=2`, optionally K3 micro-cases). Enumerate the entire legal sequence graph; compare exact sequence sets and counts with an **independent brute-force reference**. Exhaustively score all valid stopping sequences if manageable. If teacher verification is used, only in a separately authorized DEVELOPMENT micro-budget. Emit coverage and proof that enumerator finds every legal sequence for that tiny domain.

**Mode B: lazy full-domain search** on original 8×8 scenes, `K<=4` initially:
- Branch over **every allowed** object–destination pair; deterministic canonical action order.
- Use best-first/beam/iterative deepening as an **efficiency device**, but do not pretend a finite-width beam has covered all possible sequences. Preferred implementation: an enumerable, persistent **best-first frontier with fair bounded fallback** (e.g. depth-stratified exploration) so that all actions remain reachable if unbounded time is granted. A beam that permanently drops candidates is allowed only as an explicitly named incomplete baseline.
- The learned X/Y probabilities and cost set **search priority**, not membership of the action space. Do not discard low predicted probabilities, high displacement or initially hopeless-looking edits as “impossible.” Store deferred branches with counts/priority, or state that such pruning forfeits completeness.
- Search verifies promising **complete stopping sequences**, not only generator-intended ones. After failure, it can continue to the next candidate; no retraining or online fitting within a frozen benchmark unless separately authorized.
- Shared Y endpoint may be evaluated once and reused across different ordered X sequences. No target-teacher Y query before model selection/verification when claiming zero-label prediction. Do not turn teacher feedback into a hidden candidate generator.
- Every expansion, unique X scoring call, unique Y scoring call, model-forward CPU/wall, F1 check, verification call, negative kind, successful witness, and explored/deferred/exhausted node count must be logged. Include early-stopping status and memory peak.
- Report the best **verified** repair found; `predicted top-1` and `physically verified top-1` are different. The search can produce multiple candidates ranked by expected cost and verify them sequentially within a fixed teacher budget.
- **Global minimum K or global minimum cost** may only be claimed after exhaustive/sound-bound search over all relevant shorter/cheaper alternatives. If only a heuristic search ran, say “best verified among examined candidates”.

### Candidate evaluation order and failed hypotheses

`X=0` in a teacher query may be **CERTIFIED** or **fixed-budget failure**. Do not infer global infeasibility from a planner timeout. A negative Y for the current endpoint does not imply longer extensions fail. An intermediate terminal connector failure may disappear after additional edits. Prefix X failure during an *actually attempted relocation* might make its exact extension impossible under fixed deterministic protocol, but only prune if a sound certificate of that relocation's impossibility exists for the unchanged earlier prefix; no causal leap from a bounded failure.

## 5. Matched baselines and essential ablations

The original P24 result was **E 0.269, D 0.259, DIRECT 0.218, G 0.212** on 193 infeasible roots; order effect D–G +0.173 on 52 available K3/K4 roots; unnecessary interventions E/D 10/44 vs DIRECT 2/44; K3/K4 physical 31/21. These are **historical P24 results**, not the results of the new method and **must never be recycled as new independent validation**.

Run identical **action-domain, candidate-expansion, F1, neural-forward/caching, teacher-verification and wall/CPU budgets** for:
- **E-guided universal search** (primary X/Y implementation; no unsupported coupling).
- **D-guided universal search** (coupled ablation).
- **DIRECT-GEO-guided universal search** (essential matched control).
- **G-guided universal search** (order-blind control, interpretable for ordering).
- **Analytic geometry priority** with no learning; **uniform/canonical** search; **shortest-first**; and optionally fixed beam / legacy P20 catalogue selection. Record oracle access separately; don't let any search policy read hidden teacher labels or constructions.

Choose and freeze a **common search-level stop/verification policy** on new DEVELOPMENT scenes, not on P24 confirmation scenes. Existing arm-specific no-op/alpha/gamma rules may be reported as a secondary legacy-policy comparison, but an apples-to-apples search study needs matched intervention budgets and preferably a common preregistered conservative no-op policy. No test-label tuning.

Report:
- **Search coverage**: legal sequences at K<=2 micro-oracle; number of sequence nodes generated/expanded/scored/deferred vs theoretical/empirical total; distinct Y endpoints; fraction of historical intended repairs that are discoverable (as a *post hoc coverage audit*, not a search input).
- **Discovery**: verified first-repair rate vs expansion count, teacher calls, CPU/wall, peak RAM; ability to find successful sequences absent from old catalogue; K3/K4 reachability and discovered repairs.
- **Quality**: verified target restoration AND full physical X, attempts to verify, length, displacement, witnessed travel, regret only where an oracle is exhaustive; no-op correctness and unnecessary/harmful interventions.
- **Mechanism**: exact-permutation order contrasts with identical endpoint; ablate ordered predecessor geometry vs sequence order separately if possible *without claiming matched weights unless actually retrained*; report that G removes a bundle of order information.
- **OOD/calibration**: stratify scored/verified sequences by whether their ordered actions/parking distances lie outside the P21 catalogue distribution. Do not assume frozen P21 probabilities generalize to fullspace.
- **Fairness**: record total candidate-generation/model-scoring time, F1 CPU, teacher time and model calls so any advantage is not due to unequal compute. Equal verified-query budget alone is insufficient if one arm uses much more model compute.

## 6. Gate-by-gate execution — phased and capped

### P26 — Formal contract, source audit and tiny-domain reference (START IMMEDIATELY)

**Scope:** New branch, no teacher calls, no optimizer steps, no P24 evaluation lookups for tuning. Write domain definition, labels-free API contract and independent brute-force reference. Audit F1 soundness (terminal vs prefix), P20 catalogue bias and caps, `xkey/ykey` identity, mobility type/roles leakage and the memory/runtime complexity. Implement on-paper + unit-tested micro-oracle (can be very small). Include three hand-drawn or SVG toy scenes: 1-action goal blockage, 2-action order contrast and 4-action conceptual closure (schematic unless recorded witness). Report numerical fullspace count on several bounded scenes.

**Mandatory test:** enumerate all legal m=0,1,2 sequences for a toy scene using two independently implemented enumerators and show identical sorted identities including negatives/harmful destinations. Ensure the presence/absence of construction `options` / `K_intent` / `roles` values does not alter the universe.

**Limits:** <= **3,000 CPU-s**, <= **5,400 wall-s**, <= **2 single-thread workers**. New code/docs only. Gate file `responses-phases/0133_BXY_P26_FULLSPACE_DEFINITION.md`; commit/push; continue to P27 if accepted by tests.

### P27 — Lazy universal enumerator and search skeleton (NO TEACHER)

Implement `bxy_fullspace.py` and `bxy_fullsearch.py`: state transitions, all supported parking destinations, duplicate handling, length bounds, sound structural pruning, deterministic persistence, fairness/effective coverage and interruption/resume. Reconcile when intermediate occupancy changes possible destinations. Confirm no silent truncation at P20 `MAX_CANDS/MAX_QUERIES`. Add search diagrams of frontier and explored vs deferred nodes. Test K<=3 small case against brute force; certify terminal statuses.

**Limits:** <= **6,000 CPU-s**, <= **7,200 wall-s**, <= **2 single-thread workers**. No real teacher calls, training or new test cohorts. Report `0134_BXY_P27_FULLSPACE_SEARCH.md`; commit/push; continue P28 only if completeness micro-tests pass.

### P28 — Learned X/Y-guided scoring and matched search policies (NO TEACHER)

Implement `bxy_fullscore.py`, frozen E/D/A/G adapters, common policy rules and synthetic-only tests. Check score consistency on candidates copied from legacy development views (exact same p/J), shared-Y symmetry across permutations, no label access and streaming stability. Measure OOD score distribution, runtime and memory on development scenes only (no P24 tuning). Record whether frozen model can be used reliably as a heuristic for dynamically created candidates, and stop with a blocker if it cannot. Add matched nonlearned baselines and per-budget trace plots.

**Limits:** <= **10,000 CPU-s**, <= **10,800 wall-s**, <= **2 single-thread workers**. No real teacher, no training. Report `0135_BXY_P28_GUIDED_SEARCH.md`; commit/push.

### P29 — Small *new* development-only physical validation (AUTHORIZATION REQUIRED)

**Do not start P29 automatically.** Prepare a prospectively frozen, outcome-blind design of up to **12 newly generated DEVELOPMENT roots** in namespace `bxyfull_dev`, across K0–K4 and at least two scene mechanisms if feasible. Include preassigned search budgets and matched policies, learner scoring before teacher labels, write-once results and witness handling. Propose a ceiling of **12,000 aggregate CPU-s**, **9,000 wall-s**, <= **2 single-thread workers**, <= **1,400 teacher CPU-s per root**, per-query budgets unchanged. This is a **proposal**, not blanket authorization. Request the user's explicit approval after P28. A smaller approved budget is fine. **No P24 confirmation-scene labels, results or witnesses for development/tuning**; historical P24 metrics remain static background.

Primary dev question: Can fullspace-guided search find verified repairs **absent from the historical P20/P24 candidate catalogue**, without allowing the catalogue to influence search? If physical samples are too scarce, clearly record the negative result and diagnostic bottleneck. Report `0136_BXY_P29_SEARCH_PHYSICS_DEV.md`, commit/push.

### P30 — Prospective independent protocol (NO CONFIRMATION DATA WITHOUT NEW APPROVAL)

Use P29 dev observations to lock a future test design with adequate repairable K3/K4 and initially feasible controls, **distinct generator families if possible**, and a primary endpoint measured at matched search/teacher compute. Include matched DIRECT and geometry-only baselines, order-effect and unnecessary-repair safeguards, statistical power and audit plan. Existing P24 cohort is not a fresh confirmation set. Freeze code/models/search rules and separately seek authorization for any independent data. Report `0137_BXY_P30_NEW_SEARCH_CONFIRM_READINESS.md` and **STOP**. Do not run P30 independent collection under the P26–P28 permissions.

### Gate summary

| Gate | Output | Real teacher? | May execute under this instruction? |
|---|---|---|---|
| P26 | Formal universal domain, source audit, exhaustive toy oracle | No | **Yes** |
| P27 | Lazy enumerator, sound pruning and reproducible search | No | **Yes** |
| P28 | Frozen X/Y search guidance and matched synthetic baselines | No | **Yes** |
| P29 | New small physical development test | **Yes** | **No — explicit additional approval** |
| P30 | New independent-test plan and future freeze | Not yet | Preparation only after P29 |

**Authorized upfront ceilings for P26–P28 combined:** at most **19,000 aggregate CPU-s** and **23,400 summed wall-s** (subject also to each phase's cap), no more than two single-thread workers. These are **upper bounds**, not targets. Log all compute including failures, imports, smoke checks and visualization. The fact that the user requests a prompt/instruction file does not itself authorize Claude to spend those resources; **Claude must receive this file plus the user's explicit execution instruction**. Even when that instruction is supplied, P29/P30 data collection is never authorized by this document.

## 7. Test requirements and scientific blockers

**Correctness tests (must pass):**
1. Universal 0–2 action enumeration equals independent brute force on at least three small scenes and remains invariant to object-ID permutation (after canonical relabelling).
2. Object identity, destination occupancy and relocation grammar are correct after every step; vacancies created by previous relocations are available.
3. Complete order permutations are included; same endpoint => same Y key, different order => distinct X key, even when some are infeasible.
4. Target, fixed objects and unsupported/out-of-grid cells are never moved/used; every in-domain failure remains representable, including harmful edits and long-distance placements.
5. `construction.options`, hidden K labels, intended repair metadata, old candidate catalogue and teacher labels cannot affect enumerated action space or neural input/predictions (scramble/drop tests).
6. F1 is never used to prune an entire subtree merely because the current stopping prefix fails; fail if unproven heuristic pruning is present.
7. On known legacy candidates, dynamic-scoring adaptation produces unchanged X/Y/DIRECT/G p and J within tolerance; shared-Y exact identity; `q_ref` matches model adapter contract.
8. Bounded search terminates precisely with *FOUND*, *EXHAUSTED* or *BUDGET_UNKNOWN*, persists hash-verified state and resumes without duplicating a physical teacher call.
9. When model scores are permuted/randomized, fullspace membership and exhaustive tiny-domain coverage remain invariant (only ordering should change).
10. Full existing regression suite, all six archived replays, hash guards over P-min–P25, and no P24 one-shot readback used for tuning.

**Hard stop conditions:** unknown F1 soundness, label leakage, inability to embed arbitrary candidates into the model, search deleting low-probability branches while claiming completeness, failure to preserve P24 evidence, CPU overrun, or any attempt to use new teacher labels prior to P29 authorization.

## 8. Required outputs at every phase

Every `0133`–`0137` phase report must include (a) actual source/commit SHAs, (b) declared capability and tests, (c) numerical coverage, (d) model vs external vs teacher boundaries, (e) diagnostics/figures and tiny examples, (f) CPU/wall ledger and caps, (g) all regression/replay outcomes, (h) open failures and next gate. No claim of success solely from a diagram, a successful unit test or a generated candidate list. Keep visually intelligible 2D diagrams and 2–3 colors; render and inspect plots.

**Most important final deliverable:** a working 2D tool that takes an arbitrary supported scene and target, represents **every permissible corrective sequence** up to the declared K, uses the learned X/Y model to guide discovery *without knowing labels*, and distinguishes **physically verified successful repairs** from *predicted*, *unverified*, *budget-limited* and *globally enumerated* outcomes.

## 9. Two testable examples, not to be skipped

**Example A — generator-missing correction:** Put two movable discs A and B and three supported parking cells into a toy scene. Let the old catalogue contain only `A->p1` and `A->p1,B->p2`. Configure the new universe to contain `B->p3,A->p1`, `A->p2,B->p1`, other valid destinations/orders, and Y-harmful edits. Prove the enumerator includes the missing sequences even when old catalogue is empty, and verify (with synthetic known labels only at this gate) that search can discover the absent winning sequence.

**Example B — order/connector trap:** Construct a case where `[A->p1, B->p2]` and `[B->p2, A->p1]` have the same endpoint, but different X, or where an intermediate stopping prefix fails its terminal connector while a longer sequence passes. Prove neither order nor extension is pruned by final-pose-only or premature connector checks. Check `Y(A,B)==Y(B,A)` identity and distinct X keys. Use synthetic outcomes until the P29 teacher authorization.

---

### Explicit warning about the word “all”

A mathematically defined universal **finite search domain** means every member is eligible to be explored. A finite runtime cannot generally inspect billions of candidates; a bounded result must state its **coverage and residual unexplored frontier**. If the user demands literal exhaustive verification of *every* four-move 8×8 sequence, explain the CPU/teacher infeasibility and offer the tiny-domain exhaustive ground truth plus budgeted full-domain guided search. Do not pretend a beam search or a catalog of 48 candidates is exhaustive.

**START with P26, then P27 and P28. Stop before P29 physical data collection for explicit authorization.**
