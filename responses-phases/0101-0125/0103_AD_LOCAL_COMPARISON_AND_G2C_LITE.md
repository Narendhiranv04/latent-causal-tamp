# 0103 — Local track: A/B/C/D comparison (archived P17) and Approach D G2c-lite

**Authority:** `approachD_local_parallel_research_instructions_v1_3.md`.
**Branch:** `approach-d-v1` (local), on G2b `43fd985`.
**Data used:** existing P13–P17 2D data only. No historical label, checkpoint, report, replay or `config.toml` was changed. No dataset was regenerated, nothing was retrained, the 442-query set stays sealed, and nothing was pushed.

**Figures:** `visualizations/approach_d/local_comparison/01–06`.
**Code:** `ad_local.py` (opt-in `[local_pilot]` in `approach_d.toml`).

Two kinds of evidence appear below and are never mixed:
- **Historical P17 — archived shared evaluation.** Solver-based execution (`p16_motion.DetPhysics`), recomputed from saved records.
- **New precompiled backend — limited DEV pilot.** The `AD_PRECOMPILED` provider: stored trajectories only, zero runtime IK / planner calls.

---

## 1. The problem in one paragraph

A target T may be infeasible in the original arrangement even though its start and goal cells are valid: an obstacle blocks the grasp, the placement, the carried object, or the arm's own transit. Repairing it needs zero to four relevant relocations. Other nearby objects may be irrelevant, or moving them may make things worse.

Every approach here proposes or orders relocations. **None** of them learns IK, trajectories, swept volumes or destinations:
- destinations come from a scene-only slot rule;
- motions come from a certified planner (historical) or a precompiled library (new backend);
- every claimed success is an independently replayed, collision-certified record.

Certification of stored 2D paths is geometric, not hardware or simulator execution.

## 2. What each approach learns and how its choice is verified (figure 01)

| | learns | chooses a correction by | detection as scored below |
|---|---|---|---|
| **A** (retrained P13 architecture) | local endpoint penalties U, V + a GRU over the ordered sequence → task logit u_A(r); E_A(r) = Σ U + Σ V + λ softplus(−u_A(r)) | calibrated rule over a finite catalogue: EMPTY if p(empty) ≥ t0, else the fewest-move admitted repair, else ABSTAIN | chosen query ≠ EMPTY |
| **B** (`LB`, production lean B) | factorised Bernoulli outcome variables z0, zS[I] (scene edits), zR (ordered repair), zO[t] (omissions); P(z) = P_S(z_s) · P_Q(z_q), no coupling | same rule | same |
| **C** (`P13:K-C`, frozen historical checkpoint) | B's outcome variables + couplings, with A's GRU as order factor | same rule | same |
| **D** (`Dp17`, pairless) | p_T = σ(u(S, T, g_T, q)) for the **original** target, and P(b \| y0 = 0) = Π Bernoulli(σ(a_i)) blocker participation; loss BCE + 2 · masked blocker NLL | **no sequence choice**: reorders movers in a geometric search by γ_i = (1 − p_T) · marg_i, re-querying D for **T** after each hypothetical move | p_T < 0.5 (classifier) |

These are the exact historical variants; they are **not** four newly trained matched architectures.

The two detection definitions differ: a classifier threshold for D, a non-empty choice for A/B/C. Both are shown, and they are not merged.

## 3. Archived P17 comparison, recomputed from `runs/p17/eval/P17_PROSPECTIVE.json` (figure 02)

**Roster:** 90 roots. Under the historical operational convention (VERIFIED + replay = feasible; CERTIFIED and UNKNOWN count as infeasible) there are 27 feasible and 63 infeasible. Original statuses: 27 VERIFIED, 47 CERTIFIED_INFEASIBLE, 16 UNKNOWN_PLANNER.

All figures below reproduce the archived report exactly (`runs/approach_d/local/ARCHIVED_P17.json`).

| | blockage detected | false alarm on feasible | blocked task resolved | needless relocation on feasible | moves when resolved |
|---|---|---|---|---|---|
| A | 58/63 | 15/27 | 26/63 | 12/27 | 1.62 |
| B (`LB`) | 59/63 | 17/27 | 29/63 | 14/27 | 1.62 |
| C (`P13:K-C`) | 49/63 | 11/27 | 22/63 | 8/27 | 1.77 |
| **D** (classifier p_T < 0.5 / D-guided search) | 54/63 | **6/27** | **43/63** | **0/27** | 1.37 |
| geometry heuristic (choose one catalogue repair) | 60/63 | 25/27 | 25/63 | 24/27 | 1.72 |
| geometry-guided search | — | — | 40/63 | 0/27 | 1.33 |
| uniform-order search | — | — | 39/63 | 0/27 | 1.38 |
| random catalogue entry | 60/63 | 24/27 | 17/63 | 24/27 | 2.76 |
| never move | 0/63 | 0/27 | 0/63 | 0/27 | — |

**D's classifier.** AUROC is:
- 0.952 offline, over 140 decided P17-test originals (the figure in report 0098);
- 0.908 on this 90-root roster under the operational convention;
- 0.960 on its 74 decided roots.

Blocker F1 is 0.893 (31 masks).

**Reading the table honestly:**
- **D's 0/27 needless moves come from the search, not the model.** Every D-search guide verifies T first, so geometry and uniform search also make 0/27 needless moves.
- **D's 43/63 belongs to the search family.** Its peers are geometry search (40) and uniform search (39). A/B/C commit to one catalogue repair, with no fallback.

## 4. Where learning helps and where it does not (figures 03, 04)

**Helps: diagnosis.** D's original-target classifier separates blocked from feasible tasks well. Its operating point (54/63 detected at 6/27 false alarms) dominates A/B/C, whose non-empty-choice flags cost 11–17/27 false alarms.

**Does not help: search success.** On the identical domain, budget, search and replay:

| guide | roots solved |
|---|---|
| `Dp17-norec` | 71/90 |
| `geometry-norec` | 71/90 |
| `Dp17` | 70/90 |
| `geometry` | 67/90 |
| `uniform` | 66/90 |

- **`Dp17-norec` vs `geometry-norec`:** 70 roots solved by both, 1 by D only, 1 by geometry only, 18 by neither.
- **`Dp17` vs `geometry`:** the first relocation tried differs on **34 of 90 roots**, but the outcome differs on only **5** of those.
- **Effort is nearly equal:** mean nodes to the first plan are 6.2 (`Dp17-norec`) and 6.6 (`geometry-norec`).

**Why.** The search verifies T first and then enumerates every mover × slot at each depth, within a budget that is rarely exhausted. Ordering changes *which* plan is found first, not *whether* one is found. And the nearest-to-target geometry order already puts true blockers early.

D's recursion variant (`Dp17`, 70) is better than geometry's recursion (67) only because recursion hurts geometry more (67 vs 71 without it). That is not a general advantage of D.

**Authentic illustration** (figure 04, bottom; recorded P17 test decisions):
- On `p13_2026290020`, A and B both commit to `o00>28, o02>59`, which is not verified. C's three-move choice also fails.
- D-guided search finds `o02>59, o03>52` (verified).
- **Geometry search finds the same plan, and `geometry-norec` finds a cheaper one** (`o03>36, o02>59`).
- The rescue comes from verified search, not from D's learning.

Figure 04 (top) also shows committed P17 mechanism evidence: feasible clutter with an unneeded decoy move, a single blocker, two blockers together, and an order dependence.

**Limitation per approach.**
- **A:** one score per whole sequence; explanations only by re-scoring.
- **B:** production `LB` has no coupling; coupled `LB+G` resolved only 23/63.
- **C:** a frozen P13 checkpoint, never retrained.
- **D:** no search-success gain over geometry; its value so far is diagnosis.

## 5. G2b bottleneck and the corrected reading of F12 (figure 05)

G2b's single accepted A→B→T chain (`p13_2026216000`: o00>45, o01>36, then T) is real, but it is **not a proven two-blocker task**:
- **The historical P16 teacher** verifies `o00>59` alone, then T.
- **D, queried on the original scene for t0 only, agrees:** p_T = 0.015, blocker marginal o00 0.99, o01 0.01.

The second relocation was needed only because the **finite library** could not realise the one-move repair. In G2b fixture F10, `o00>59` then T fails on connectors. That is a catalog limitation, not a causal property of the task.

## 6. G2c-lite: small, offline-only catalog additions (figure 06; `runs/approach_d/local/`)

**DEV set, fixed in advance:** all 12 P16-labelled development roots (`runs/p16/data/dev/pilot_keys.json`); no selection.

**Search domain, identical for every guide:**
- the 3 P17 movers nearest T;
- each to its first 2 scene-only P17 slots, with no library destinations, recomputed on every hypothetical occupancy;
- at most 2 relocations, then the original T.

**Offline compile budget:** 500 attempts / 1,800 CPU-s, all IK and planning offline. Spent: **303 attempts, 272 CPU-s.**

| catalog | adds | rule (declared before evaluation) | attempts → compiled |
|---|---|---|---|
| C1 | relocation templates for the search domain | ≤ 1 exact-cell witness, 1 relative-family mode, 2 branch-spread, per uncovered (mover, slot) pair | 135 → 99 (19 exact, 38 relative-family, 42 generic) |
| C2 | original-target diversity | one template per uncovered (pick branch, place branch, 60° pick sector), ≤ 6 per target pair | 28 → 28 |
| C3 | bypass-home connectors | retreat end of each pair's first template → 2 nearest target approach starts (joint distance; no scene used) | 118 → 118 |
| C4 (**dev-informed**, reported separately) | state connectors | for **every** state where a stored target action certifies but no stored path reaches it: actual node → that action's start | 22 → 22 |

All four graphs validate every piece in its compile fixture with 0 rejected. They are nested (C1 ⊂ C2 ⊂ C3 ⊂ C4).

**Result: availability did not improve.** Budget-free availability over the 51 states reachable in the domain:
- a stored target action certifies in **15/51 states (4 roots)** in every catalog;
- it is also reachable by a stored connector path in **1/51** in every catalog.

C2 adds about 2.4 target templates per state, but no new state gains a clearing target action. C3 and C4 connectors are single straight joint segments, compiled where nothing is in the way. In the real scenes they collide with exactly the near-base objects that make the task infeasible (`link0|o00`, `link0|o01`, `link1|t0`).

**Failure-source attribution** (C3, provider attempts over all reachable states):

| source | attempts |
|---|---|
| target action collides | 265 |
| target action clears but its connector collides | 35 |
| relocation collides | 50 |
| relocation connector collides | 25 |
| no relocation template | 11 |
| relocation check budget exhausted | 13 |
| relocation accepted | 39 |

**Conclusion of G2c-lite.** Small additions of generic, scene-independent motions do not close the gap. The binding constraints are:
- **target-action coverage** in clutter;
- **transit connectors that pass near the base**, where a single stored path has no alternative and only relocating the obstacle helps.

This is a sound negative result. It argues for the server dataset's larger, multi-alternative motion library, not for more learning.

## 7. D-guided vs geometry vs uniform on the new backend (figure 06 c–d; `PILOT_L3*.json`)

**Matched setup.**
- **Guides:** the **unchanged** P17 `Guide` code, `Dp17-norec` / `geometry-norec` / `uniform`. The recursion variants are excluded because they query D for temporary targets.
- **Shared across guides:** the same 12 DEV roots, domain, catalogs (C1–C4), per-move certification budget (6), connector hops (2), relocation-attempt cap (60) and verify-first iterative deepening.
- **Execution:** stored records only, then an independent replay.
- **D calls:** always t0 with the original goal, at the hypothetical occupancy and the achieved q (tested).
- **Solver calls:** 0 forbidden calls in every run.

**Result.**
- **Every guide repairs 1/12 roots on every catalog:** the directly feasible root `p13_2026210004`, at depth 0.
- **The other 11 roots fail identically:** each search exhausts the same finite domain (same number of relocation attempts per root).
- **No difference between guides can appear** while the catalog cannot complete the chains.

**What does differ is diagnosis inside the search.** On the 7 infeasible DEV roots with a historically verified repair, the first relocation tried:

| guide | moves an object of a verified minimal repair | is exactly its first step |
|---|---|---|
| D | 7/7 | 5/7 |
| geometry | 6/7 | 3/7 |
| uniform | 4/7 | 1/7 |

This is consistent with §4, where diagnosis is good and search success is unchanged. With n = 7 it is suggestive, not established.

**Exploratory common-backend A/B/C comparison: not attempted.** A/B/C choose among historical catalogue sequences whose destinations and motions are realised by the historical planner. Mapping those choices onto this finite catalog would change what they mean, and the catalog cannot realise most of them anyway. The honest A/B/C/D comparison remains the archived P17 one (§3).

## 8. Why each component exists (what it does → evidence)

| component | what it does | why it is included | evidence so far |
|---|---|---|---|
| D original-target classifier | p_T for T at any state and q | detects blocked tasks without proposing a move | AUROC 0.952 (140 decided); 54/63 detected at 6/27 false alarms |
| D blocker marginals | which objects participate in blocking T | orders movers in search | first-move hits 7/7 vs 6/7 vs 4/7 (n = 7); F12 o00 = 0.99 matches the teacher; **no search-success gain** (71 = 71) |
| verify-first search (non-learned) | checks T before any move, then enumerates | prevents needless moves; finds repairs | 0/27 needless moves for every search guide; 39–44 of 63 resolved |
| scene-only slot rule (non-learned) | proposes destinations | keeps destinations out of learning | shared by all arms |
| precompiled motion library | absolute stored trajectories + connectors | zero runtime IK / planning | G2a/G2b/G2c-lite: 0 forbidden calls; coverage, not guidance, binds |
| relative-family templates | cross-location motion classes | more usable motions than generic templates | G2b: exact + relative 18/36 vs exact-only 12/36; patch ranking ≈ random / geometry |

## 9. Limitations

- **Small DEV pilot.** 12 roots and 51 reachable states; the C4 connectors are dev-informed.
- **Different backends.** The historical P17 results come from a different motion backend and are not comparable bar for bar with §6–7.
- **The roster AUROC depends on the label convention** (UNKNOWN counted as infeasible): 0.908 vs 0.960.
- **Scope.** One object footprint and grasp family; geometric certification only.
- **The historical protocol stays as it was** (0–4 relocations); it is not converted to the future 7-action protocol.

## 10. Next step once the server dataset exists

1. **Rebuild the motion library at scale from the new dataset's offline teacher witnesses.** Both binding constraints need many stored alternatives per (state, target) rather than one generic path:
   - target-action coverage;
   - near-base transit connectors.
2. **Re-run the matched guide comparison (§7) on held-out new roots,** with the same unchanged guides, only after the library completes chains at a reasonable rate. Only then can D's diagnosis advantage (§4, §7) show up, or fail to show up, as search success.
3. **Keep D's training unchanged** (BCE + blocker NLL, original target only). The new binary-label dataset supplies more original-target and edited-scene examples, not new losses.
