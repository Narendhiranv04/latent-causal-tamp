# BXY-P27: lazy universal enumerator and bounded search skeleton (no teacher, no model)

**Previous turn sync:** P26 was committed and pushed as `e81e52ad` on `approach-b-universal-search`. Report: [0133](0133_BXY_P26_FULLSPACE_DEFINITION.md).

## Verdict

`P27_SEARCH_COMPLETE_IN_PRINCIPLE_AND_ACCOUNTED`.

The search is complete in principle and its coverage is accounted exactly:
- **Nothing is dropped.** Expanding a node generates and scores *all* of its children (every unmoved movable × every destination free at that step). Children are never truncated, so there is no analogue of P20's `MAX_CANDS` / `MAX_QUERIES` caps.
- **Every member stays reachable.** Best-first order is interleaved with a breadth-first fallback (every 4th expansion takes the oldest open node). With unbounded budget the search reaches every member, whatever the priority.
- **Exact accounting.** Under any budget: examined + sound-pruned + unexplored residual = N(K), exactly, on every toy and on every development root.
- **Precise outcomes.** Every run ends in one precise terminal status. A budget limit is never reported as "no repair exists".

## (a) Source and commits

| Item | Value |
|---|---|
| Start | `e81e52ad` |
| End | this report's commit (recorded in chat and in 0135) |
| New code | [bxy_fullsearch.py](../bxy_fullsearch.py) (search, coverage, verification phase, sealed persistence, Mode A oracle)<br>[bxy_full_eval.py](../bxy_full_eval.py) (non-learned priorities GEOM / SHORTEST / UNIFORM and the development-root roster; P28 adds the learned policies)<br>[bxy_p27_report.py](../bxy_p27_report.py)<br>[tests/test_bxy_fullsearch.py](../tests/test_bxy_fullsearch.py) |
| Evidence | [SEARCH_P27.json](../runs/approach_b/bxy_p27_fullsearch_v1/SEARCH_P27.json), [STATE_interrupted.json](../runs/approach_b/bxy_p27_fullsearch_v1/STATE_interrupted.json), [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p27_fullsearch_v1/CPU_LEDGER.jsonl) |
| Legacy code or evidence changed | none |

## (b) Declared capability and tests

### Search: `bxy_fullsearch.run(D, K, cost, budget, verify=None, fair=4, st=None)`

**Nodes.** Each node is an ordered sequence, and every node is a complete stopping candidate (the empty sequence is the no-op).

**Priority.** `cost(list[seq]) -> list[float]`, lower first. A priority only orders the search; it never decides membership.

**Sound rules (the only reductions):**

| Rule | Effect |
|---|---|
| GOAL_BLOCKED | The node is never *selected* (success 0), but it is still *expanded*: moving the blocker later can clear the goal. |
| GOAL_DEAD | A relocated object rests on the goal. The node is not expanded, and its descendants are counted exactly as `pruned_sound`. |
| Shared Y | A verified Y result belongs to the single Y node shared by every order with that endpoint. A second Y query is never made. |

**Never pruned:**
- low cost or probability;
- Y(prefix) = 0;
- a failure of a prefix's terminal connector;
- NO_PLAN_FOUND or TIMEOUT outcomes.

**Verification (optional).** Candidates are visited in ascending (cost, m, xsig), Y first and then X. Recorded calls are reused. In P27 and P28 the verifier is **synthetic only**.

**Terminal statuses:**

| Status | Meaning |
|---|---|
| FOUND_VERIFIED | best verified *among examined candidates*; not a global optimum |
| EXHAUSTED_DEFINED_SPACE | every member examined and every selectable candidate verified 0; negative kinds reported |
| VERIFY_BUDGET_EXHAUSTED_UNKNOWN | teacher-call budget spent |
| BUDGET_EXHAUSTED_UNKNOWN | search budget spent |
| TEACHER_CENSORED | a verification result was censored |
| SELECTED_UNVERIFIED | no verifier: a prediction only |

**State.** JSON sealed with sha256 (`save` / `load`). `run(..., st=load(...))` resumes the same search, and the budget is cumulative.

**Mode A.** `exhaustive(D, K, cost)` scores every member of a tiny domain. It is the reference ranking.

### Tests

[tests/test_bxy_fullsearch.py](../tests/test_bxy_fullsearch.py) has 12 tests, all passing.

| Requirement (instruction §7 and §9) | Evidence |
|---|---|
| 9: completeness invariant to scores | 5 priorities (constant, two random seeds, shortest, longest-first) and `fair` ∈ {0, 1, 3, 4}. With unbounded budget, the examined set equals every member except sound GOAL_DEAD descendants, on a toy with 3 movables, 10 legal cells, a fixed wall and K = 3. |
| Exact accounting | 4 bounded budgets: `balanced`, residual > 0, status SELECTED_UNVERIFIED |
| Mode A oracle | bounded-free search ranking equals the exhaustive ranking of all selectable members (K = 2) |
| §9 Example A (catalogue-absent winner) | Synthetic labels: Y = 1 iff A at p1 and B moved; X = 1 iff B moves before A. Both catalogue repairs (A→p1) and (A→p1, B→p2) fail. With no catalogue input, the search returns FOUND_VERIFIED on (B→·, A→p1), which is absent from the catalogue. With a 3-call verification budget the same root returns VERIFY_BUDGET_EXHAUSTED_UNKNOWN, never "no repair". |
| §9 Example B (order / connector trap) | Synthetic labels: [A→4] fails X (connector) and Y; [B→5, A→4] fails X; [A→4, B→5] passes. The search verifies the failed prefix and the failed order and still finds the winner, with **one** shared Y query for both orders. |
| 8: statuses | EXHAUSTED_DEFINED_SPACE (all CERTIFIED negatives), BUDGET_EXHAUSTED_UNKNOWN, TEACHER_CENSORED |
| 8: resume | interrupt → save → load → resume equals the uninterrupted run (nodes, coverage); 30 verification calls in total with **no repeat**; a tampered state file is refused |
| 6: only sound pruning | the blocked root is still expanded; every GOAL_DEAD node stays closed |

## (c) Numerical coverage on 12 development roots (40 expansions, non-learned priorities)

**Roster:** 8 P20 K34 roots and 4 P16 V21 roots, in a fixed hash order chosen without looking at outcomes. The same roster is used in P28.

| Priority | Examined members, median [min, max] | Median fraction of N(4) | CPU per root |
|---|---|---|---|
| SHORTEST | 9,796 [2,297, 11,458] | 5.5 × 10⁻⁶ | ≤ 0.84 s |
| GEOM | 7,447 [729, 11,458] | 5.1 × 10⁻⁶ | ≤ 0.82 s |

- **Accounting:** `balanced` = true for all 24 root × priority runs. The open frontier and its exact residual subtree size (for example 2.4 × 10⁹ on `k3-s019`) are reported, not hidden.
- **Root expansion size:** at least 112 children (n·F) on every root, against the old catalogue cap of 24.
- **Resume:** on `2d-bxyg34dev-k3-s019`, an interruption after 13 expansions, a sealed save and a resume to 40 give identical nodes, coverage, selection and trace.
- **Depth, SHORTEST:** it expands m = 1 nodes breadth-first, so it reaches only m ≤ 2 within 40 expansions, and its "selection" is trivially the no-op. It is a *verification-order* baseline, not a selector.
- **Depth, GEOM:** it reaches m = 4 and selects analytically opened 3–4 move sequences on the K34 roots.

### Correction made in this gate

My first GEOM priority was a product of open-mode fractions. It is zero for every still-blocked scene, so it degenerated into shortest-first. I replaced it before reporting with an analytic **remaining-blocker** count:
- **h:** the minimum, over target pick-and-place mode pairs not killed by a fixed body, of the number of bodies on the pair's kill cells;
- **penalty:** +1 for each action whose pick or place is analytically closed;
- **length term:** + α m.

**Disclosure.** h(S0) equals the generator's K_cert on the roots checked: the P16 / P17 access maps are the generator's own geometry. GEOM is therefore a strong **shortcut** baseline for this generator family, and P28 / P29 must read it as such.

## (d) Boundaries

| Component | What it reads or does |
|---|---|
| Search | the domain plus a priority callable. It never reads the catalogue, labels, roles values or construction. |
| GEOM | the scene and the access maps (analytic; no labels) |
| Synthetic verifiers | exist only in tests |
| Teacher | not called |
| Model | not called (P28) |

## (e) Figures (rendered and inspected)

| Figure | Content |
|---|---|
| [01 toy search tree](../visualizations/approach_b/bxy_p27_fullsearch_v1/01_toy_search_tree_explored_vs_deferred.png) | K = 2 toy with 25 members. After 3 expansions: expanded (blue), examined-open or terminal (black), GOAL_DEAD (orange ×), never generated (hollow). 13 examined + 6 pruned_sound + 6 residual = 25. |
| [02 development coverage](../visualizations/approach_b/bxy_p27_fullsearch_v1/02_dev_coverage_examined_vs_domain.png) | examined members per root (log scale) against N(4); balanced on every root |

## (f) CPU and wall-time ledger

| Item | CPU-s |
|---|---|
| P27 phase, per [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p27_fullsearch_v1/CPU_LEDGER.jsonl), regression included | P27_CPU |
| Synthetic test draft run during P26 (charged in the P26 ledger) | 0.5 |
| Cap | 6,000 CPU-s, 7,200 s wall, 2 single-thread workers |

## (g) Regression

| Check | Result |
|---|---|
| Full pytest | P27_PYTEST |
| Six archived replays | P27_REPLAYS |
| Hash guard over P-min…P25 | P27_GUARD |

## (h) Open limitations and next gate

1. **Expansion cost.** Expansion is all-children. With a learned scorer at about 18 ms per candidate per 15-network ensemble (measured; P28), one expansion of a root costs 2–6 CPU-s per arm. Learned search therefore examines thousands, not millions, of members. This is the honest efficiency limit.
2. **Coverage assumption.** Exact descendant accounting assumes every object rests on a legal cell. This holds for all development roots, and the code refuses otherwise.
3. **Certified pruning.** Pruning on a certified relocation failure is deliberately absent. It needs a certificate that is independent of the achieved robot state, to be designed with P29.

**Next gate:** P28, frozen learned guidance with matched baselines. It uses no teacher.
