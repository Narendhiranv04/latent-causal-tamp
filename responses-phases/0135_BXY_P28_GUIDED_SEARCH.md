# BXY-P28: frozen learned X/Y guidance of universal search, matched baselines, label-free reliability (no teacher)

**Previous turn sync:** P27 was committed as `2fd3c7d2`, with follow-up `fbab49a4` filling the report cells. Report: [0134](0134_BXY_P27_FULLSPACE_SEARCH.md).

## Verdict

`P28_GUIDANCE_IMPLEMENTED_LEARNED_RELIABILITY_NOT_SUPPORTED_OFF_CATALOGUE`.

**Mechanically, the system works:**
- The frozen D, E, DIRECT-GEO and G ensembles score *arbitrary* universal-domain sequences exactly as the legacy pipeline scores catalogue candidates: max |Δ| = 2.2 × 10⁻¹⁶ over 180 members on 12 roots and all four ensembles.
- Permutations share one Y prediction, and G is order-invariant to rounding.
- Learned priorities drive the complete-in-principle search with exact coverage accounting.

**Scientifically, the label-free evidence argues against trusting the frozen models as an off-catalogue guide.** These are predictions only:
1. Their top choices are out of distribution. 56–65% of selected moves park 3 or more cells away, against 14% in the training catalogues. Ensemble disagreement at the selected sequence (median SD 0.10, and 0.14 for DIRECT) is 2–4× that on catalogue members (0.02–0.05).
2. On the 8 roots with a sound necessity certificate (K_cert, read **post hoc for evaluation only**), the learned top choice has fewer moves than certified necessary on 3–5 of 8 roots. Such a sequence **certainly fails** (Y = 0) under the analytic certificate, with no teacher needed. GEOM, the analytic remaining-blocker shortcut, does so on 0 of 8.
3. Each model's own predicted gain over the best catalogue member is about zero (median Δp̂: E +0.002, D +0.009, DIRECT −0.007, G +0.056).

This does not show that the models fail physically; that needs the teacher (P29). It does mean that P29 should not be expected to show a learned-guide advantage, and that GEOM is a strong shortcut baseline on this generator family.

Embedding works, so the hard-stop condition (arbitrary candidates cannot be embedded) is **not** triggered. I report the reliability concern as the main finding instead of stopping.

## (a) Source and commits

| Item | Value |
|---|---|
| Start | `fbab49a4` |
| End | this report's commit (recorded in chat) |
| New code | [bxy_fullscore.py](../bxy_fullscore.py) (dynamic label-free ScorerView, frozen-ensemble scorer, cost and no-op gate)<br>[bxy_full_eval.py](../bxy_full_eval.py) (learned policies added to the P27 non-learned priorities)<br>[bxy_p28_report.py](../bxy_p28_report.py) (tables, figures, consistency, P29 proposal)<br>[tests/test_bxy_fullscore.py](../tests/test_bxy_fullscore.py) |
| Code identity | The run executed from byte-identical copies of `bxy_full_eval.py` (sha256 `e05d8692…`) and `bxy_fullscore.py` (`325001b7…`), verified before staging. |
| Evidence | [GUIDED_SEARCH_P28.json](../runs/approach_b/bxy_p28_guided_v1/GUIDED_SEARCH_P28.json), [TABLES_P28.json](../runs/approach_b/bxy_p28_guided_v1/TABLES_P28.json), [CONSISTENCY_P28.json](../runs/approach_b/bxy_p28_guided_v1/CONSISTENCY_P28.json), [P29_PROPOSAL.json](../runs/approach_b/bxy_p28_guided_v1/P29_PROPOSAL.json), [run.log](../runs/approach_b/bxy_p28_guided_v1/run.log), [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p28_guided_v1/CPU_LEDGER.jsonl) |
| Unchanged | no retraining, no checkpoint change (`bxy_p24_confirm.load_member` hash-verifies every one of the 60), no legacy code change, no P24 file read |

## (b) Declared capability and tests

### Scorer

`bxy_fullscore.view(key, rec, inputs, seqs)` builds the unchanged `bxy_p11` contract (SCORER_KEYS / CAND_KEYS / FORBIDDEN, checked) for any domain members:

| Field | Content |
|---|---|
| inputs | label-free root tensors (`bxy_p16_inputs`: scene, goal_cell, q0 = q_ref) |
| `x_seqs` | ordered actions as (object index, destination centre) |
| `y_poses` | **one per distinct edited endpoint** |
| `parent`, `y0` | as in the legacy views |

`Scorer` returns the frozen 15-member mean (`bxy_p24_confirm.ensemble`). Its cost is:

C = −log p + α m + β C_d + γ Ĵ, and the no-op ranks first when P(Y0) ≥ gate.

### Policies, all matched

Every policy uses the same domain, K = 4, fair = 4, and a budget of ≤ 3,000 scored members (an expansion may overshoot) and ≤ 16 expansions per root.

| Policy | Priority |
|---|---|
| E, D, DIRECT, G | frozen ensembles under the common rule COMMON (gate 0.5, α 0.3, β 0, γ 0) |
| E, D, DIRECT, G (secondary) | each arm's own P23 rule, as a *selection-only* variant over the same examined members |
| GEOM | analytic remaining-blocker heuristic |
| SHORTEST | shortest first |
| UNIFORM | constant cost (canonical order) |

**COMMON** is the development-selected P23 DIRECT-GEO rule, chosen in P23 on development roots. **Disclosure:** P25's exploratory P24 recomputation pointed the same way, so this choice is not independent of P24 knowledge. It will be tested only on new data.

### Tests

[tests/test_bxy_fullscore.py](../tests/test_bxy_fullscore.py) has 5 tests, all passing.

| Requirement (instruction §7) | Evidence |
|---|---|
| 7: legacy equality | dynamic view equals the P20 design view (p, px, py, Ĵ ≤ 1e-9) on 2 roots × 4 ensembles; extended to all 12 P28 roots in [CONSISTENCY_P28.json](../runs/approach_b/bxy_p28_guided_v1/CONSISTENCY_P28.json) (180 members, max 2.2e-16) |
| Chunk invariance | chunk size 5 vs 400: identical to 1e-12 |
| 3, 7: shared Y | permutation pairs: identical py (D, E, G) |
| G is order-blind | px and p equal to ≤ 1e-12 |
| D is order-aware | Δpx > 0 |
| 5: no label leakage | scrambled `construction`, `roles` values, catalogue, design and spec give identical scores |
| Domain-only input | a non-member (moving the target) raises; candidate keys are exactly CAND_KEYS |
| 7: q_ref contract | `inputs.q_ref == rec.q0 == rec.q_ref` |
| Cost and gate | unit test |

## (c) Numerical coverage and results (12 development roots, predictions only)

**Roster:** 8 P20 K34 roots and 4 P16 V21 roots, the same as P27.

| Policy | Examined / root, median | Fraction of N(4) | Priority CPU-s (12 roots) | Selected m: 0 / 1 / 2 / 3 / 4 | m < K_cert (certain failure) of 8 |
|---|---|---|---|---|---|
| E | 3,104 | 1.8 × 10⁻⁶ | 533 | 2 / 1 / 6 / 2 / 1 | **5** (own rule: 3) |
| D | 3,104 | 1.8 × 10⁻⁶ | 541 | 3 / 0 / 6 / 0 / 3 | **4** (own rule: 4) |
| DIRECT | 3,104 | 1.8 × 10⁻⁶ | 538 | 1 / 2 / 6 / 1 / 2 | **3** (own rule: 3) |
| G | 3,104 | 1.8 × 10⁻⁶ | 564 | 2 / 2 / 5 / 1 / 2 | **5** (own rule: 3) |
| GEOM | 3,050 | 1.8 × 10⁻⁶ | 1.8 | 2 / 1 / 2 / 2 / 5 | **0** |
| SHORTEST | 3,078 | 1.8 × 10⁻⁶ | 0.1 | 12 no-op (a verification order, not a selector) | 8 |
| UNIFORM | 3,078 | 1.8 × 10⁻⁶ | 0.0 | 12 no-op (a verification order, not a selector) | 8 |

**Coverage:** `balanced` on all 84 root × policy runs. Peak RSS 954 MB.

**Catalogue-absent discoveries (predicted):** every non-no-op selection of every policy lies **outside** the historical catalogue. On the K34 roots the learned policies choose 2–4-move sequences with far parking. The search found these with no catalogue input. Whether any of them is physically executable and restorative is P29's question.

**Selections disagree across policies.** Of 12 roots, the policies chose the same sequence on:

| Pair | Same sequence |
|---|---|
| D–E | 5 |
| DIRECT–G | 3 |
| E–DIRECT | 2 |
| E–G | 2 |
| E–GEOM | 2 |
| D–DIRECT | 1 |

Same-endpoint counts equal these.

### Label-free diagnostics

From [TABLES_P28.json](../runs/approach_b/bxy_p28_guided_v1/TABLES_P28.json):

| Diagnostic | E | D | DIRECT | G |
|---|---|---|---|---|
| Ensemble SD of p, selected / catalogue (median) | 0.101 / 0.023 | 0.098 / 0.043 | 0.142 / 0.046 | 0.096 / 0.044 |
| Selected moves with Chebyshev ≥ 3 (training catalogues: 0.138) | 0.57 | 0.58 | 0.56 | 0.65 |
| Scored moves with Chebyshev ≥ 3 (median) | 0.71 | 0.74 | 0.71 | 0.71 |
| Median P(Y), GOAL_BLOCKED endpoints / other (certain Y = 0 vs other) | 0.024 / 0.163 (max 0.42) | 0.036 / 0.176 (max 0.48) | n/a | 0.037 / 0.165 (max 0.41) |
| Permutation Δpx, median / max (groups) | 0.053 / 0.35 (300) | 0.064 / 0.44 (142) | n/a | **0 / 0** (149) |
| Predicted p of selection − best catalogue p (median, n) | +0.002 (10) | +0.009 (9) | −0.007 (11) | +0.056 (10) |

**Interpretation:**
- The models do separate goal-occupied endpoints on median, but individual certain-negative endpoints receive P(Y) up to 0.48.
- The order-aware F2 genuinely changes P(X) across permutations; G does not, by construction.
- Optimising a learned score over about 10⁹ members moves the search into a region that is sparsely covered by training and where the members disagree. This is a known optimiser's-curse risk, and nothing the search can do label-free removes it.

## (d) Boundaries

| Component | Boundary |
|---|---|
| Scorer | reads the `bxy_p16_inputs` view plus each candidate's ordered actions and edited poses only (tested by scrambling) |
| Search | reads the domain plus the priority |
| Catalogue, K_cert | read only by the post hoc evaluator (`catalogue_sigs`, `certified_short`) |
| Teacher | not called |
| Stored development labels | not read |

## (e) Figures (rendered and inspected)

| Figure | Content |
|---|---|
| [01 anytime](../visualizations/approach_b/bxy_p28_guided_v1/01_anytime_best_predicted_success.png) | best *predicted* p_succ among examined members vs scored members, 12 roots × 4 arms |
| [02 selected sequences](../visualizations/approach_b/bxy_p28_guided_v1/02_selected_sequences_boards.png) | 4 K_cert-4 roots; rows E, DIRECT, GEOM; numbered order; all marked "predicted only". E chooses 2–3 moves on three K_cert-4 roots, which is certain failure; GEOM chooses 4. |
| [03 reliability](../visualizations/approach_b/bxy_p28_guided_v1/03_label_free_reliability_diagnostics.png) | ensemble disagreement (selected vs catalogue), the GOAL_BLOCKED P(Y) sanity check, out-of-distribution parking distance |
| [04 compute](../visualizations/approach_b/bxy_p28_guided_v1/04_compute_per_policy.png) | an equal scored budget is not equal compute: about 535 CPU-s per learned policy vs about 2 for GEOM |

## (f) CPU and wall-time ledger

| Item | CPU-s |
|---|---|
| P28 phase, per [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p28_guided_v1/CPU_LEDGER.jsonl) | **3,321.0** (wall 3,331.0 s) |
| of which the guided-search run | 2,212 |
| of which the regression | 996.5 |
| Cap | 10,000 CPU-s, 10,800 s wall, 2 single-thread workers (the guided search ran beside the P27 regression) |
| **Combined P26 + P27 + P28** | **5,751.9 CPU-s** of 19,000 (P26 1,087.7 + P27 1,343.2 + P28 3,321.0) |

## (g) Regression

| Check | Result |
|---|---|
| Full pytest | **774 passed, 1 skipped** in 957 s (769 + 5 new); exit 0 |
| Six archived replays | all exit 0 |
| Hash guard over P-min…P27 (`bxy_p27_fullsearch_v1` added) | `{"ok": true, "modified": [], "untracked_or_changed": []}` |

## (h) Open limitations, and the P29 request

1. **No physics yet.** Every P28 statement about "discovery" is a prediction. Certain failures come only from the sound K_cert certificate, read post hoc.
2. **Search depth is limited by learned scoring cost** (about 18 ms per member per ensemble). On 6-movable roots, 16 expansions mostly reach m ≤ 2 to 3, which partly explains the short selections. A larger budget, or the optional certified-closed screen (decision D1 below), would address this.
3. **GEOM is a shortcut.** It uses the generator's own access maps, and h(S0) equals K_cert. A GEOM win in P29 would not show general geometric competence.
4. **The common rule** is not independent of P25's exploratory P24 knowledge (disclosed).

### P29 authorization request

This is a proposal, **not started**. Full manifest: [P29_PROPOSAL.json](../runs/approach_b/bxy_p28_guided_v1/P29_PROPOSAL.json).

**Cohort:** 12 new development roots in namespace `bxyfull_dev`.

| Family | K_intent | Roots |
|---|---|---|
| local_mixed | 4 | 4 |
| local_mixed | 3 | 3 |
| local_pick | 3 | 1 |
| local_mixed | 2 | 1 |
| V21B nested | 3 | 1 |
| V21B near_closed | 0 | 2 |

**Generators and data rules:**
- existing generators with new seeds;
- every attempt recorded and none replaced;
- construction metadata never a search input.

**Policies:** E as primary, with DIRECT, G, GEOM and UNIFORM matched (D if budget allows).

**Per policy and root:**
- ≤ 3,000 scored members, 16 expansions, K = 4;
- **8 teacher calls**: Y of the endpoint first, then X;
- a candidate verified for one policy is reused but charged to each policy.

**Order of work:**
1. Generate the roots.
2. Run every search, then **seal** the ranked lists by sha256 before any teacher call.
3. Verify.
4. Write-once rows, keeping witnesses.
5. One evaluation.

**Teacher:** unchanged teacher and per-query budget, with no reset between relocations.

**Primary development question:** does universal guided search find teacher-verified repairs that are **absent from the historical catalogue**? The catalogue is rebuilt post hoc for comparison only.

**Limits:**
- 12,000 aggregate CPU-s;
- 9,000 s wall;
- ≤ 2 single-thread workers;
- ≤ 1,400 teacher CPU-s per root;
- per-query budgets unchanged.

**Decisions needed from you:**

| ID | Decision |
|---|---|
| D1 (optional) | Add a sound, label-free **certified-closed Y screen** at selection time: the real-screen certificate that the target pick or place is closed in the edited scene. Such a candidate is never selected or verified, but its subtree is not pruned. It would avoid spending teacher calls on certain failures like those found above. It adds to F1 and changes none of F1's existing rules. |
| D2 | Confirm COMMON as the primary rule, with own rules as secondary. |
| D3 | Approve the 12-root, 12,000 CPU-s budget, or a smaller one. |

P30 (the independent protocol) is not started and needs a separate approval.
