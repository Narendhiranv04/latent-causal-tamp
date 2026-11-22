# P6A — Public, training-free, execution-aware order composition (methodology, implementation, model-only DEV diagnostics)

Branch `naren/kgt3-exec-composition`, from `f13d95530a` (P5B accepted: PHYSICAL_ORDER_RECOVERED, one exposed K4 DEV root).

Constraints observed:
- **Nothing new physical:** no teacher call, no training, no new learned module, no label regeneration, no changed budgets, and no TEST.
- **Frozen artefacts untouched:** checkpoints (bundle `~/abf_v34/approach_b_bundle`, hash-checked at load), teacher code, P4 seals, P5A/P5B artefacts.

## Bottom line

1. **The implementation works.** It is a bounded beam search over orders, with merging that is exact for this score, deterministic, legal, and reproducible: the rerun was byte-identical apart from wall time.
2. **The frozen "execution-aware" signal does *not* discriminate physical execution on these DEV scenes. Its point estimates are below chance.**
   - **Step level:** on 287 unique already-tested steps (P4 + P5B teacher rows), comparing executed vs failed steps at the same step index, frozen px scores AUROC **0.40** (W1) and **0.42** (W3); the root-clustered bootstrap 95% interval for W3 is 0.32–0.52.
   - **Public features do better:** source distance to the robot base scores **0.71** (0.61–0.80) and source clutter **0.73**.
   - **Within-endpoint pairs:** the lower W3 cost picks the order that executed further in **14/35** pairs.
   - **Exposed P5B endpoint:** W3 ranks the certified-infeasible original order best and the physically verified q23 order worst.
3. **The static-validity proxy shows no advantage either.** On the 13 statically recoverable teacher-Y endpoints, the top-1 order is static-valid in 3/13 for each of the following: W3, W2, W1, ORIG, RANDOM and CLUTTER_LOW_FIRST. With the candidate pool held fixed, W3 picks a valid order in **1/13**, below uniform selection (expected 2.0) and below P4's fixed-chunk score (3/13).
4. **The dominant bottleneck is not order.** Of the 50 public top-hY endpoints that P6A would actually commit to, **45 have no statically valid order at all** under the P5A abstraction. Only 5 endpoints (3 roots, K4–K6) are reorderable even in principle.

**Recommendation: REVISE. Do not run the proposed P6B before deciding.** The frozen-only order hypothesis (P6-FROZEN-ONLY) is not supported by any of the model-only DEV evidence. A frozen P6B schedule is supplied (section 9) because it was requested. If you run it, treat it as a falsification test with a low prior. Details are in section 10.

## 1. Inputs and boundary

| Input | Status | Used for |
|---|---|---|
| `dev_public.jsonl` (DEV scene: cells, xy, base, goal, `q_ref`) | public | everything in `p6_order.py` |
| sealed P4 R2/R3/F candidate pools (planner outputs, stored frozen hY and energy C) | public | **endpoint selection** (`select`) |
| frozen K≤3 X/Y scorer (bundle, hash-checked) | public model | window px |
| P5A kill tables (MINK_STATIC_V2), P5A DP, private witnesses, certified K | **evaluator only** | `p6_eval.py` static-validity labels, K strata |
| P4 `verify.jsonl` and P5B attempts (teacher rows) | **evaluator only** | physical-progress labels of *already-tested* orders |

**How the boundary is enforced:**
- `p6_order.py` imports only `data` and `models`.
- It installs the P4 path guard (`data.install_guard`), which aborts on any `private`, `witness` or `dev_private` path.
- Tests assert, from the AST rather than docstrings, that it never references the kill-table checker, `dev_eval`, `p5*`, teacher, verify, `K_certified`, P5B, q23 or the exposed root id.
- The evaluator-selected diagnostic endpoint file and the tested-orders file carry **only assignments and orders, no label** (keys were audited before the run).
- The q23 order, its first mover and every P5B failure explanation are **not** encoded anywhere in P6A. The exposed root is reported separately (`excl_exposed` columns).

## 2. Score (exact)

For an order (m₁, …, m_m) of a fixed assignment, with window w (default 3):

- px_j = frozen `px`(window = (m_{j−w+1}, …, m_j) | the hypothetical scene Edit(S₀, {m₁, …, m_{j−w}}), with the robot at `q_ref`).
- C(order) = Σ_j −log max(ε, px_j), with ε = 1e-4.
- The reported components are the sum C, the mean, the bottleneck (max), and the first-move term.

**How to read px.** Inside a window, the frozen chained-X head models up to 3 relocations with the robot state carried through, which is its training semantics. Between windows, the robot is **assumed** to be back at `q_ref`. px_j is therefore a ranking signal on hypothetical prefix states, never a physical execution estimate. No privileged trajectory or achieved robot state is used.

**Ablations** (all searched with the same beam unless noted):
- **W1:** the single move in the scene after all previous moves; no composition.
- **W2:** windows of 2 moves.
- **RANDSCORE:** seeded uniform px, as a matched control.
- **P4CHUNK:** P4's fixed stride-3 chunks; a non-causal rerank score only.

## 3. Search algorithm and budgets

**Beam search over ordered prefixes:**
- Expand every prefix by every remaining move.
- Merge on the key (set of done moves, last w−1 moves), keeping the lower (cost, sequence).
- Keep the top B; return the top 5 complete orders.

**Why the merge is exact.** C is Markov in that key: the scene depends only on the done set, and the next window only on the last w−1 moves. So B ≥ #keys gives exact DP. The tests confirm this against exhaustive permutations for m = 2–7 and W1/W2/W3.

**Histories are kept separate.** Prefixes with the same done set but different last moves stay distinct, because their future windows differ.

**Monotonicity.** Best cost is non-increasing in B. This is tested; the beam at width B is contained in the beam at any wider width.

**Budgets:**
- Default: B = 16. Ablations: B ∈ {1, 4, 64}.
- The budget is counted as window requests (`window_calls`, before cache) and unique frozen calls (`local_scored`).
- Method set (50 endpoints): mean window requests per endpoint were 44 (B1), 151 (B4), 534 (B16) and 1,841 (B64). All P6A arms together used 144,819 unique frozen calls in 54.6 s.
- Diagnostic set (53 endpoints): 232,548 unique frozen calls in 82.9 s.
- One GPU (RTX 5060 Laptop); 3 min 44 s for all runs, including the rerun and the tested-order scoring.

**Public controls** (model-free fixed orders on S₀ geometry):
- **ORIG:** the lowest-energy recorded P4 pool order of the assignment.
- **RANDOM:** seeded.
- **BASE_NEAR_FIRST:** source closest to the robot base first.
- **CLUTTER_LOW_FIRST:** fewest S₀ neighbours within 1.5 cells first, then base distance.

## 4. Generated candidates

**Method set** (public, `select`):
- For each of the 25 DEV roots, take the top 2 assignments by stored frozen hY from the union of the sealed P4 R2/R3/F pools, deduplicated by sorted assignment. That gives **50 endpoints / 25 roots**, with m up to 12.
- For each endpoint the output is the top-5 orders for every arm, the controls, per-step px, components, P4CHUNK cost and call counts (`p6_method.jsonl`).

**Diagnostic set** (evaluator-selected, label-free file): the 53 P5A teacher-Y=1 endpoints (17 roots), used only to measure.

**Every output order is checked in code:**
- legal under the declared grammar (`data.check_sequence`);
- a permutation of the fixed assignment (each object once, target never moved).

**Distinctness.** W3_B16 returns 4.7 (method) and 5.0 (diagnostic) distinct top-5 orders per endpoint. Its top-1 differs from ORIG in 46/50 and 52/53 endpoints. The mean W3 gain over ORIG is 2.7 and 2.9 nats, with a range of −3.2 to +10.2. A negative gain is possible because ORIG is not in the beam.

## 5. DEV diagnostics (model-only search; labels only in the evaluator)

### D1 – Same endpoint, different orders

Scores separate orders strongly: the gain over ORIG reaches up to 10 nats, and all 5 returned orders are distinct. So the score does discriminate between orders; the question is whether it discriminates in the right direction (D5).

### D2 – Legal prefixes and consistent state history

- All orders are legal and are exact permutations of their assignment (asserted per order).
- The window semantics are tested: the window base is the prefix minus its last w−1 moves; W1 uses the scene after all previous moves.
- Exact merge equivalence is tested, and state histories are kept per (set, last w−1).

### D3 – Reproducibility under fixed budgets

Rerunning the method set gives **byte-identical output** apart from wall time (`reproducible_method_rerun = true`). Ties are broken deterministically by (cost, sequence), and RANDSCORE and RANDOM are seeded.

### D4 – Comparison with public controls (offline static checker; necessary, not sufficient)

Top-1 order statically valid, on statically recoverable endpoints:

| Arm | Diagnostic (13 recoverable) | Diagnostic excluding exposed root (10) | Method (5 recoverable) |
|---|---|---|---|
| W3_B16 (P6A) | 3 | 3 | 0 |
| W2_B16 | 3 | 3 | 0 |
| W1_B16 | 3 | 2 | 0 |
| RANDSCORE_B16 | 0 | 0 | 0 |
| W3_B1 / B4 / B64 | 2 / 3 / 2 | 2 / 3 / 2 | 0 / 0 / 0 |
| ORIG | 3 | 2 | 0 |
| RANDOM | 3 | 3 | 0 |
| BASE_NEAR_FIRST | 1 | 1 | 0 |
| CLUTTER_LOW_FIRST | 3 | 3 | 0 |

- Frozen-model arms beat the seeded random score (3 vs 0). They do **not** beat cheap public orders.
- Mean statically valid prefix fraction, over all endpoints: CLUTTER_LOW_FIRST 0.26–0.30, BASE_NEAR_FIRST 0.23–0.33, W3_B16 0.23–0.26, RANDOM 0.12–0.19.

### D5 – Does the frozen signal discriminate beyond heuristics? **No.**

**Data.** 300 already-tested orders (P4 verify rows plus the 27 new P5B calls), giving 525 step observations and 287 unique steps with no conflicting labels.
- Label per step: the step was executed (1), or it is the first failed step (0; the teacher's UNKNOWN or scoped CERTIFIED). Later steps are censored.
- No teacher call was made.

**Position-stratified AUROC** (pairs only at the same step index):

| Feature | All (525 steps) | Unique steps (287) | Excluding exposed root | First move only |
|---|---|---|---|---|
| frozen px W1 | 0.394 | 0.396 | 0.361 | 0.383 |
| frozen px W2 | 0.405 | – | 0.385 | 0.383 |
| frozen px W3 | 0.403 | 0.419 (bootstrap 0.32–0.52) | 0.387 | 0.383 |
| source near base (public) | **0.781** | **0.708** (bootstrap 0.61–0.80) | 0.782 | 0.788 |
| source low clutter (public) | **0.754** | **0.725** | 0.735 | 0.757 |
| destination near base | 0.574 | – | 0.603 | 0.603 |
| destination low clutter | 0.390 | – | 0.402 | 0.366 |

- **Not a padding effect:** 281 of the 287 unique steps are in scenes within the frozen model's 20-object limit.
- **In-distribution failure too:** even the first move from S₀, the exact K≤3 training setting, is not discriminated (0.38).
- **Within-endpoint concordance** (pairs of tested orders of the same assignment, with different physical depth): the lower cost picks the deeper order in 14/35 pairs for W3, 18/35 for W1, and 16/35 for P4CHUNK. None differs meaningfully from chance; W3 is below it.
- **Exposed P5B endpoint** (reported only, never used for tuning), W3 cost in nats:

  | Order | W3 cost | Teacher outcome |
  |---|---|---|
  | q32 (original order) | 3.26 | certified infeasible (scoped) |
  | q03 | 8.97 | UNKNOWN |
  | q14 | 9.19 | UNKNOWN |
  | q23 | 11.25 | **VERIFIED** |

  The ranking is fully inverted.

### D6 – Separating budget effects from ranking effects

- **Budget:** the mean W3 cost of the top-1 falls monotonically with B, from 9.6 to 8.3, 7.3 and 6.9 nats (method set), so the search optimizes its objective. But more search does not raise static validity (diagnostic: 2/13 at B1, 3/13 at B4, 3/13 at B16, 2/13 at B64), and the statically valid prefix fraction *falls* at B64 (0.18 vs 0.23).
- **Ranking:** the pool is held fixed (the union of all arms' top-5 orders plus controls; 5 of 13 recoverable endpoints contain a valid order). Selection by W3 picks a valid order in 1/13; P4CHUNK in 3/13; the bottleneck rule in 0/13; uniform selection has expected 2.01/13.
- **Separation achieved:** the search reliably optimizes C, but C is the wrong objective, so extra budget amplifies a mis-ranking rather than fixing it.

## 6. Failure taxonomy (P6A, offline)

1. **Endpoint not reorderable (dominant).** 45 of 50 public top-hY endpoints (and 40 of 53 teacher-Y endpoints) have no statically valid order. No ordering method can help these; they need endpoint or object-set repair (P7).
2. **Reorderable endpoint, but the search picks an invalid order.** This happened for 5/5 method and 10/13 diagnostic endpoints. W3_B16 top-1 static failures on the recoverable endpoints: method set 3 pick / 2 place; diagnostic set 3 pick / 6 place / 1 both.
3. **Signal inversion.** Frozen px is anti-correlated with physical step execution (D5). This is the root cause of failure 2 for the frozen arms.
4. **Static-valid but physically unknown.** P6A generated no new physical evidence. Physical outcomes keep the three-valued scheme: VERIFIED, scoped CERTIFIED, and UNKNOWN. UNKNOWN is never promoted to a negative.

## 7. Reproducibility and leakage audit

**Reproducibility:**
- The method-set rerun is identical; all randomness is seeded; ties are deterministic.
- Input hashes are in `P6A_SUMMARY.json → input_sha256`.
- Code: `p6_order.py` (200 lines, public), `p6_eval.py` (258 lines, evaluator), `tests/test_p6_order.py` (28 tests).

**Leakage:**
- **Boundary in code:** the AST-level test shows no privileged token in `p6_order.py`; the path guard is active during `run` and `score`; public P4 modules import neither P6 module.
- **Label-free inputs:** the endpoint and tested-order files contain only (root, assignment/order).
- **Kill tables, DP, private witnesses, certified K and teacher rows are read only by `p6_eval.py`, after the search.** No feature, filter or feedback reaches the search.

**Exposure:**
- The 25 DEV roots were already exposed in P3, P4 and P5. The public controls (base distance, clutter) and the AUROCs above were measured on these exposed roots, so a design that uses them must be validated on new roots.
- ENG2_e3c632c779c0 (the P5B witness) is reported separately; excluding it does not change any conclusion.

**Tests:**
- 56/56 pass: P6A 28, P5B 9, P5A 19.
- Historical regressions: `test_p1_p2` passes 22/22, and the `test_p4_mock` output is identical to the committed `GATE_B_MOCK.json`.
- No pre-existing file was modified, so P4 and K≤3 parity are preserved.

## 8. Score components (worked example)

Figure panel (d) shows ENG2_963783c2655b (m=12, not exposed). P6A W3 costs 15.1 nats against 25.2 for ORIG, a static-only diagram. Each order in `p6_method.jsonl` and `p6_diag.jsonl` carries its per-step px and its sum, mean, bottleneck and first-move components, so any ranking can be audited step by step.

## 9. Proposed frozen P6B physical schedule (NOT executed)

`P6B_PROPOSED_SCHEDULE.json` (+ `.sha256`), generated by `p6_eval.py schedule`, with the control fixed in code **before** the DEV analysis ran:

- **Endpoints:** for each of the 25 DEV roots, the public rank-0 endpoint (top frozen hY over the sealed P4 pools).
- **Arms:**
  - P6A W3_B16 top-1: 23 new calls (2 already tested, so reused);
  - the predeclared public control CLUTTER_LOW_FIRST: 23 new calls (1 reused);
  - ORIG, only where already teacher-tested: 18 reused, 0 new calls.
- **Y:** one fresh Y per endpoint that lacks a VERIFIED Y row with a matching key, which is 12 calls.
- **Caps:** **62 teacher calls** (58 scheduled plus a 4-call confirmation reserve: fresh X repeat and fresh Y for the first 2 X-positives), **2 workers**, **2,700 s cumulative wall time**. Per-query teacher budgets stay unchanged.
- **Execution rules:**
  - fixed queue order;
  - fail closed on `WORKER_ERROR`;
  - the cumulative wall cap carries across resumes (the P5B harness can be reused unchanged);
  - the exposed root is reported separately;
  - UNKNOWN stays UNKNOWN, and only the teacher's CERTIFIED status counts as a scoped negative.
- **Primary outcome:** complete X=1 ∧ Y=1 per root, P6A vs CLUTTER_LOW_FIRST, compared as paired roots.
- **Expectation on DEV evidence:** low. 45 of the 50 public endpoints are not even statically reorderable, and the score is anti-discriminative.

## 10. Recommendation for the next stage: **REVISE** (P6B not recommended as proposed)

- **P6-FROZEN-ONLY is not supported.** The frozen K≤3 px, evaluated on hypothetical prefix scenes, carries no order-execution information on these scenes. Spending about 58 physical calls to confirm this has low value, except as a formal falsification.
- **If order work continues,** plan2's P6-PUBLIC-GEOM variant (a transparent public geometry order filter based on source clearance and distance to the base) is the evidence-backed direction. But its signal was observed on exposed DEV roots, so it needs a predeclared test on new development roots.
- **Endpoint generation dominates.** With 45/50 public endpoints not reorderable, P7 (object-set and enabling-mover repair within the 12-move cap) is the higher-yield next stage, with matched flat and random controls.
- **No claim of learned causal order inference or K>3 deployment** follows from P5B or P6A.

**STOP.** P6B, P7, collection and TEST were not started.

## Files

**Added:**
- `p6_order.py`: public; modes `select`, `run`, `score`;
- `p6_eval.py`: evaluator; modes `prep`, `analyze`, `schedule`, `figure`;
- `tests/test_p6_order.py`;
- in `reports/p6/`: `P6A_SUMMARY.json`, `P6B_PROPOSED_SCHEDULE.json` (+ `.sha256`), `p6a_overview.png`, `endpoints_method.jsonl`, `endpoints_diag.jsonl`, `tested_orders.jsonl`, `p6_method.jsonl`, `p6_diag.jsonl`, `p6_tested_scores.jsonl`, and this report.

**Modified:** none.

**Reproduce:**
```
python p6_order.py select P4_DIR DEV_PUBLIC endpoints_method.jsonl
python p6_eval.py  prep reports/p5/P5A_PER_ENDPOINT.jsonl reports/p5/P5B_ATTEMPTS.jsonl VERIFY OUT
python p6_order.py run endpoints_{method,diag}.jsonl DEV_PUBLIC p6_{method,diag}.jsonl
python p6_order.py score tested_orders.jsonl DEV_PUBLIC p6_tested_scores.jsonl
python p6_eval.py  analyze OUT DEV_PUBLIC DEV_PRIVATE TABLES P5B_ATTEMPTS VERIFY reports/p6
python p6_eval.py  schedule OUT VERIFY reports/p6 ; python p6_eval.py figure OUT DEV_PUBLIC reports/p6
```
