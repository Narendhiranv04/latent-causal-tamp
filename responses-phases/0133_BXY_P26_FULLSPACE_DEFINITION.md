# BXY-P26: universal corrective-action domain, source audit and the exhaustive toy oracle

**Instruction:** [BXY_P26_P30_UNIVERSAL_CORRECTIVE_SEQUENCE_SEARCH_INSTRUCTIONS.md](../instruction-phase-md/BXY_P26_P30_UNIVERSAL_CORRECTIVE_SEQUENCE_SEARCH_INSTRUCTIONS.md), gate P26.

**Previous turn sync:** P25 closed at `e113c66808c4ab4682196f1fa62ae51885b08ca3` on `approach-b-xy-v1`. That branch is untouched.

**Status:**
- New branch: `approach-b-universal-search`, created from that commit.
- No teacher call, no optimizer step, no model forward pass.
- No P24 file was read.

## Verdict

`P26_DOMAIN_DEFINED_AND_TESTED`.

**The universal domain is defined and implemented as a lazy, complete enumerator.** It covers:
- every movable object, in every order;
- every destination that is free at that step, including a cell vacated by an earlier move;
- every length from 0 (the no-op) to K.

**Verification against brute force.** On three toy scenes and one development root, the enumerator's sequence set equals an independent brute force over every object and every lattice cell. The brute force uses the historical `bxy_f1` X screen plus `bxy_teacher.eligible`, and shares no code with the new module.

**Size.** The domain size has an exact closed form. At K ≤ 4 it is a median of **1.37 × 10⁹ sequences per development root**. The historical catalogue has a median of **11** sequences, so it covers a median fraction of **8 × 10⁻⁹** of the domain.

## (a) Source and commits

| Item | Value |
|---|---|
| Start | `e113c668` (P25 HEAD); branch `approach-b-universal-search` |
| End | this report's commit (recorded in chat and as "Previous turn sync" in 0134) |
| New code | [bxy_fullspace.py](../bxy_fullspace.py) (domain + enumerator + exact counts + toy records + CPU ledger)<br>[bxy_p26_report.py](../bxy_p26_report.py) (counts, catalogue audit, figures)<br>[tests/test_bxy_fullspace.py](../tests/test_bxy_fullspace.py) |
| Domain manifest | [ACTION_DOMAIN_V1.json](../runs/approach_b/bxy_p26_fullspace_v1/ACTION_DOMAIN_V1.json) |
| Counts | [FULLSPACE_COUNTS_P26.json](../runs/approach_b/bxy_p26_fullspace_v1/FULLSPACE_COUNTS_P26.json) |
| Ledger | [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p26_fullspace_v1/CPU_LEDGER.jsonl) |
| Legacy code changed | none |
| Historical evidence changed | none (hash guard below) |

## (b) Declared capability, the domain, and tests

### ACTION_DOMAIN_V1

A candidate is r = ((o1, d1), …, (om, dm)) with 0 ≤ m ≤ K. K ≤ 6 is the teacher contract, and K_search = 4 for this study.

| Part | Definition |
|---|---|
| Fields read | `scene` (objects: id, kind, cell, radius; lattice; legal_cells), `goal_cell`, `fixed_ids`. Nothing else. |
| Objects M(S0) | every non-target object not in `fixed_ids`; each relocated at most once |
| Destinations D(S_t, o) | every legal cell empty **at step t** other than o's own cell; a cell vacated earlier is available |
| Lengths and orders | every m in 0…K and every order the grammar allows |
| Kept as members (potential negatives) | far cells, the goal cell, the q_ref footprint, access-killing cells, the reference corridor, pick-closed or unreachable placements, useless and harmful edits |
| Out of domain (reason recorded, never a label) | UNKNOWN_OBJECT, TARGET_MOVED, FIXED_MOVED, DUPLICATE_OBJECT, NULL_RELOCATION, DEST_NOT_LEGAL, DEST_OCCUPIED (includes simultaneous swaps), LENGTH |
| X node | the ordered sequence (`xsig`, equal to `bxy_data.sig`) |
| Y node | the edited endpoint (`ysig`, equal to the payload of `bxy_teacher.ykey`) |

There is **no intended-blocker whitelist**, and the domain never reads any of:
- construction intent (`options`, `intended`, `K_intent`, `K_cert`, `forced_order`, neutral or harmful cells, q_ref footprint);
- `roles` values;
- `spec`;
- catalogues or designs;
- labels, results or witnesses.

### Exact size

Every object of every development root rests on a legal cell, so each step offers exactly F = |legal| − |objects| destinations. Hence:

**N(K) = Σ_{m=0..K} P(n, m) F^m**, where n is the number of movable objects.

`count_endpoints` counts distinct Y nodes exactly by enumerating cell-pointer patterns. A pattern is kept only if it is injective and acyclic, so that a legal order exists.

### Tests

[tests/test_bxy_fullspace.py](../tests/test_bxy_fullspace.py) has 11 tests, all passing.

| # | Requirement (instruction §7) | Test |
|---|---|---|
| 1 | m = 0…2 enumeration equals an independent brute force | 3 toy scenes, one with a restricted lattice of 10 legal cells, brute force over every object × all 64 cells. One development root (`2d-bxyg34dev-k3-s000`, 12 objects, n = 5) at m ≤ 1 over every object and at m = 2 over its movables. |
| 1 | ID-permutation invariance | renaming every object leaves the universe unchanged after mapping back (K = 3) |
| 2 | Occupancy and vacated cells | `B 36→37, A 28→36` is a member; `A 28→36, B 36→37` is not; a swap is DEST_OCCUPIED |
| 3 | Permutations: same Y, distinct X | `ysig` and `T.ykey` are equal; `xsig` and `T.xkey` differ |
| 4 | Target and fixed objects never move; harmful and far edits kept | goal-cell and far-corner destinations are members |
| 5 | Privileged fields cannot change the universe | replace `construction`, `roles` values, `spec`, catalogue and design, or keep only READ: identical sequence list |
| — | Counts are exact | closed-form `count` and `count_endpoints` equal enumeration at K = 3 on the toys |
| 6 | F1 terminal vs subtree | on every member, `goal_blocked` equals `not F1.complete_ok`; GOAL_DEAD (a relocated object on the goal) holds for every extension |
| §9 A | Catalogue-absent sequences are members | the old catalogue {A→p1, (A→p1, B→p2)} is a subset of the domain; `(B→p3, A→p1)` and `(A→p2, B→p1)` are present |

## (c) Numerical coverage (development roots only)

**Population:** 173 development roots (P16 V21: 87; P20 K34: 86). None of them is a P24 confirmation root.

| Quantity, K ≤ 4 | V21 median | K34 median | Max |
|---|---|---|---|
| Sequences, m = 1 | 324 | 216 | 342 |
| Sequences, m = 2 | 87,480 | 34,992 | 97,470 |
| Sequences, m = 3 | 18.9 M | 3.78 M | 22.2 M |
| Sequences, m = 4 | 3.06 × 10⁹ | 2.04 × 10⁸ | 3.80 × 10⁹ |
| Distinct Y endpoints, m = 4 | 1.42 × 10⁸ | 9.5 × 10⁶ | — |
| Historical catalogue | 8 | 17 | 20 |

**Typical root parameters:** n ∈ {3,…,6} movable objects and F ∈ {51,…,60} free cells. The smallest root (`2d-bxyg34dev-k1-s032`) has one movable object, so its domain is 1 + 59.

**Worked example, `2d-bxyg34dev-k3-s000`** (n = 5, F = 52): 1 + 260 + 54,080 + 8,436,480 + 877,393,920 sequences, and 40.9 M distinct 4-move endpoints. Its catalogue has 20 entries.

**Post hoc catalogue audit.** The catalogue is read only by [bxy_p26_report.py](../bxy_p26_report.py) and never by the domain module.
- All catalogue entries across the 173 roots are domain members (0 out of domain).
- 32 entries have m = 5 (`repair_plus_unnecessary`). They lie in the K ≤ 6 teacher domain, outside K_search = 4.
- All 68 recorded intended repairs are members.
- On every root, the teacher's movable set (`roles` **keys**) equals "not target, not fixed".

**Enumeration throughput.** Measured at about 6.5 M sequences per CPU-second (K = 3, 3.61 M sequences, exact count). Merely **listing** K = 4 for the median root would take about 212 CPU-s. Scoring all of them with 60 frozen networks, or verifying them with the teacher, is out of reach. That is why P27 uses bounded lazy search.

## (d) Boundaries: model vs external vs teacher

| Layer | Reads | Never reads |
|---|---|---|
| Domain (`bxy_fullspace`) | scene, goal_cell, fixed_ids | construction intent, roles values, catalogue, labels, results, witnesses |
| Learned scorer (P28) | the unchanged `bxy_p16_inputs` view (scene, goal_cell, q0, q_ref) plus the candidate's ordered actions and edited poses | same as the domain row |
| Teacher (P29, not authorized) | only the candidates the search selects for verification | — |

The teacher never generates candidates.

### F1 soundness audit

For domain members, the grammar is exactly F1's X rules. Two facts make the remaining checks hold automatically:
- Two discs of radius 0.024 m at distinct cells (pitch 0.08 m) cannot overlap, so DEST_OCCUPIED is the same as cell occupancy and PAIR_OVERLAP cannot fire.
- The robot base at (−0.14, 0.32) is at least 0.184 m from every cell centre, so no destination intersects it.

The only F1 rule that can reject a member is **GOAL_BLOCKED**. It is sound as a *terminal* rule: a body on the goal pose makes the target placement impossible.

Promoting it to *subtree* pruning is sound only for a **relocated** object on the goal, because the single-move contract forbids moving that object again. This rule is called GOAL_DEAD; it is proven in tests and exactly accounted in P27.

An *unmoved* object on the goal does **not** prune: moving it later can clear the goal.

The following are **never** used for pruning:
- Y(prefix) = 0;
- a prefix's terminal-connector failure;
- NO_PLAN_FOUND or TIMEOUT;
- low predicted probability.

The teacher's analytic certificates (`p15_retarget.certified`, order certificates) are teacher-side negative kinds, not search filters. Pruning on a certified relocation failure is not implemented. It would need a certificate independent of the achieved state and is deferred to the P29 design.

### Identity audit

- `bxy_teacher.xkey` embeds the ordered signature, so different orders give different X nodes.
- `bxy_teacher.ykey` embeds the sorted endpoint of moved objects, so permutations share one Y node.
- For members, the moved set is exactly the set of objects in the sequence, because relocations are nontrivial and single-move.

### P20 catalogue bias audit

`bxy_p20_k34.candidates` reads:
- `construction.intended`;
- `options[0]` (pick and place modes), to build the `avoid` kill sets;
- `neutral_cells`;
- `q_ref_footprint`;
- `roles` **values** (`distractor`).

Every candidate is a variant of the generator's intended repair: parking variant, permutations, prefixes, omissions, wrong destination, plus-unnecessary, or interference. The catalogue is capped by `MAX_CANDS` = 24 and `MAX_QUERIES` = 60.

The catalogue is therefore **ground-truth-informed**. It is a comparison baseline only.

### Scorer input contract (for P28)

`bxy_p17.Model` needs:
- `x_seqs` as (object index, xy) lists;
- `y_poses`, `parent` and `y0`;
- the GEO2 access maps.

The P16 and P17 maps cover all 64 pick cells and all 64 place cells, so arbitrary destinations can be embedded. Per-candidate scores are independent of the other candidates: `bxy_core.marginals` is element-wise, and memoisation happens only within a single `coeffs` call. Chunked scoring is therefore well defined. P28 must measure this rather than assume it.

### API contract for P27 and P28 (proposed)

`bxy_fullspace` (P26, implemented):
- `domain(rec)`, `walk(D, K, prefix)`, `actions(D, cells, moved)`, `classify(D, seq)`;
- `xsig`, `ysig`, `endpoint`, `goal_blocked`, `goal_dead`;
- `count`, `count_endpoints`, `toy`, `charge`.

`bxy_fullsearch` (P27):
- `run(D, K, cost, budget, verify=None, fair=4, st=None) -> (state, result)`, where `cost(list[seq]) -> list[float]` and `verify(side, seq) -> {y, negative_kind} | None`;
- `save` / `load` (sha256-sealed);
- `exhaustive(D, K, cost)` (Mode A);
- `coverage(state)`, which satisfies examined + pruned_sound + unexplored_residual = N(K).

`bxy_fullscore` (P28):
- `Scorer(rec, key, inputs, arms)`;
- `.score(list[seq]) -> per-arm {p, px, py, J_hat}`, through dynamic scorer views with Y deduplicated by edited endpoint.

## (e) Figures (rendered and inspected)

| Figure | Content |
|---|---|
| [01 one-action goal blockage](../visualizations/approach_b/bxy_p26_fullspace_v1/01_toy_one_action_goal_blockage.png) | every one of A's and B's 60 single moves; blue = goal clear, orange = goal still blocked (success 0) and still a member |
| [02 two-action order contrast](../visualizations/approach_b/bxy_p26_fullspace_v1/02_toy_two_action_order_contrast.png) | vacated-cell dependency (member vs out of domain); a permutation pair with one Y node and two X nodes |
| [03 four-action closure, SCHEMATIC](../visualizations/approach_b/bxy_p26_fullspace_v1/03_toy_four_action_closure_SCHEMATIC.png) | T enclosed by 4 movable discs and 4 fixed walls; one of 223,644,521 members (K ≤ 4); no robot motion, no witness |
| [04 domain size vs catalogue](../visualizations/approach_b/bxy_p26_fullspace_v1/04_domain_size_vs_catalogue.png) | exact sizes for m ≤ 1…4 on all 173 development roots against the historical catalogue (log scale) |

**Toy counts** (scenes 1 and 2: 2 movable objects, F = 60): 1 + 120 + 7,200 sequences, with 3,660 distinct two-move endpoints. The 3,660 is checked by hand: 60·59 + 60 + 60, with the swap excluded.

## (f) CPU and wall-time ledger

| Item | CPU-s | Wall s |
|---|---|---|
| Phase total, per [CPU_LEDGER.jsonl](../runs/approach_b/bxy_p26_fullspace_v1/CPU_LEDGER.jsonl) (includes a conservative 40 CPU-s pre-ledger estimate for source reading) | **1,087.7** (1,031.0 of it the full regression; 0.5 is a P27 test draft) | **1,116.8** |
| P26 cap | 3,000 | 5,400 |

Workers: at most 2, single-thread (OMP / MKL / OPENBLAS = 1).

## (g) Regression

Script: [regression.sh](../runs/approach_b/bxy_p26_fullspace_v1/regression/regression.sh).

| Check | Result |
|---|---|
| Full pytest | **755 passed, 1 skipped** in 988 s (744 pre-existing + 11 new); exit 0 |
| Six archived replays (g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit) | all exit 0 |
| Hash guard over P-min…P25 run trees (`bxy_p16_audit.guard`; P16–P25 including `bxy_p24_report_v1`) | `{"ok": true, "modified": [], "untracked_or_changed": []}` |

## (h) Open limitations and next gate

**Limitations:**
- The domain reproduces the teacher's grammar, so it shares that grammar's restrictions:
  - each object moves at most once;
  - no pushing;
  - no new grasps or skills;
  - lattice cells only.
- Sequences that move an object twice are out of domain by contract, not because they are physically impossible.
- `count_endpoints` assumes that every object starts on a legal cell. This holds for all 173 development roots.
- The closed-form descendant count used for P27 coverage needs the same uniformity.

**Next gate:** P27, the lazy search with sound pruning, resumable state and exact coverage accounting. It uses no teacher.
