# 0031 — P9-L3a-0: catalogue, identity and inference-path audit of the P9 PoE root model

**Actual result.** Gate: `runs/p9/l3/L3A_0_GATE.json` → **PASS** (8/8 integrity checks). No teacher, IK or planner call.

- **Integrity.**
  - `HEAD` = `origin/main` = `4be6d80`; the only tracked changes are the user's two pre-existing PDF deletions.
  - All 27 P9-L2 checkpoints match their manifest; the three P9 gates read PASS.
  - **4,252 / 4,252** stored repair-slot query IDs equal their canonical meaning `(root scene and robot state, ordered (object, destination cell) moves)`. No ID names two sequences.
- **The PoE "count once" claim is about observed variables only.**
  - P9 counts each *observed label* once.
  - It does **not** count each *energy contribution* once: of 1,265 distinct sequence queries, **742 have their repair-outcome unary applied by more than one candidate block** (up to 7).
- **Catalogue sensitivity of the P9 PoE**, measured on 12 saved roots with frozen P9-L2 seed-0 weights:
  - **exact candidate duplication changes other queries' prior marginals by up to 0.18** (B-full) / **0.17** (B-structured);
  - adding a one-move candidate that already exists as an omission, which introduces **no new factor** in B-structured, changes them by **0.046**;
  - permutation, renamed IDs and disconnected candidates are exactly invariant;
  - the scene prior never moves.
  - These are findings about the baseline, not gate failures.
- **Reporting ambiguity in 0030 (corrected here; 0030 unchanged).** Its "conditional d (scene → zR)" column sat in a table headed "root model". It was computed by the **per-candidate** `p8_eval.conditional`.

Previous turn sync: `4be6d803bbfcff693b8055eb4e2e25707a8da4ee`. Contract: `instruction-phase-md/0031_P9_L3a_Factor_Graph_Semantics_and_Saved_Data_Controls.md` (`sha256:df17943e…`). Methodology v1.8, Guide v2.0 and the P9 contract are present with the hashes recorded in P9.

## 1. Exact code paths (P9 at `4be6d80`)

```
saved learner root r  (labels only ever enter as masks; inputs: DINOv2 + geometry, q0, goal, candidate sequences, edits)
│
├─ abc7_train.forward ─► ModelBC7.joint(R, seq_r, slots_r, edits)        one call PER CANDIDATE   = "per_candidate"
│     ├─ scene_block(names) [memo]   F3 unaries, z0–zS pairs, F5 scene pairs, ho_s  ─► P_S (root-scoped, identical for all r)
│     ├─ order(seq) / order(seq∖t) [memo]   F2 φ_seq (also the F4 omission unary on r∖t), summary g, endpoints xy
│     ├─ _pairs(V, g_r, spec)   F4 zR–zO pairs, F5 scene–repair and zO–zO pairs (role types, context g_r)
│     ├─ ho_q(Z·ho_u(V), g_r)   F5 higher order over the whole block
│     └─ logP_Q,r = −E_Q,r − log Z_r(z_S)   ─► marg, u = logit P(zR=1), E = E_static + T·softplus(−u), J = softplus(cost(g_r))
│
├─ joint_likelihood.tables ─► S, blocks {logq = logP_Q,r, slot queries}, labels
│     ├─ log_evidence   exact PoE root evidence  P_S · Π_r P_Q,r · 1[copies agree] / Z_eq        (P9-L2 training NLL)
│     └─ marginals      PoE ROOT PRIOR (no labels)                                               = "root_prior"
│     (posterior P(q | labels) = exp(log_evidence(lab ∪ {q:1}) − log_evidence(lab)): offline only = "root_posterior")
│
├─ p9_run.root_eval    "expert" rows = p7_eval.evaluate (per-candidate);  "root" rows: u, p, energy, omission effects, bit NLL from root prior
└─ p9_run.evaluate_model
      repair metrics, funnel, κ  ── both modes (κ uses scene marginals = P_S in both)
      *_conditional            ── p8_eval.conditional: tasks a / b on logP_S (identical to root); tasks c / d on the
                                  PER-CANDIDATE block (not the root model)  ◄── source of the 0030 labelling ambiguity
```

**Metric provenance in 0030:**

| metric | source |
|---|---|
| exact root NLL | PoE root evidence |
| "root" accuracy / AUROC / NLL / ECE / funnel / omission effects / bit NLL | root prior |
| "expert" metrics | per-candidate |
| scene NLL, κ | P_S (identical in both modes) |
| conditional a / b | P_S |
| conditional c / d | **per-candidate** |

The new L3b evaluator (`p9_l3.evaluate9`) keeps three labelled outputs, each computed from the model's **own** joint: `root` (prior), `expert` (per-candidate), and `offline_conditionals` (root model) with `legacy_per_candidate_conditional` kept separate.

## 2. "One label once" vs "one factor once" (`runs/p9/l3/l3a0/multiplicity.json`, P8c dev + disclosed test)

| quantity per distinct sequence query (1,265 queries) | distribution |
|---|---|
| PoE blocks applying its outcome unary | 1×: 523, 2×: 291, 3×: 243, 4×: 100, 5×: 52, 6×: 36, 7×: 20 |
| roles | zR and zO: 720; zR only: 468; zO only: 77 |
| scene–repair pair instances touching it (B-full) | 4 … 28 |
| zR–zO pair instances touching it | 0 … 6 |

## 3. Prediction modes on one saved validation root (`p8_2026102504`, P9-L2 B-full seed 0)

Root posterior is an **offline** diagnostic conditioned on every observed label; it is never a ranking input.

| slot of candidate | query | label | per-candidate | root prior | root posterior (offline) |
|---|---|---|---|---|---|
| zR of `o00>61` | `o00>61` | 0 | 0.141 | 0.013 | 0.000 |
| zO[1] of `o00>61.o01>13` | `o00>61` | 0 | 0.088 | 0.013 | 0.000 |
| zO[0] of `o01>13.o00>61` | `o00>61` | 0 | 0.086 | 0.013 | 0.000 |
| zO[1] of `o00>61.o06>31` | `o00>61` | 0 | 0.210 | 0.013 | 0.000 |
| zR of `o00>61.o01>13` | `o00>61.o01>13` | 1 | 0.776 | 0.893 | 1.000 |
| zO[2] of `o00>61.o01>13.o06>31` | `o00>61.o01>13` | 1 | 0.750 | 0.893 | 1.000 |
| zR of `o00>61.o06>31` | `o00>61.o06>31` | 0 | 0.342 | 0.029 | 0.000 |
| zR of `o00>60.o01>13` | `o00>60.o01>13` | — | 0.778 | 0.759 | 0.727 |

The query `o00>61` appears in four blocks with per-candidate beliefs 0.086–0.210. PoE combines them into **0.013**: four experts each saying "unlikely" become "almost impossible". Full table: `runs/p9/l3/l3a0/prediction_modes.json`.

## 4. Catalogue sensitivity of the P9 PoE (`sensitivity.json`, gate summary)

Max |change| of the prior marginals of the original queries, with frozen weights. The roots are 6 validation catalogue roots plus 6 training roots with omission-only queries.

| case | expected | B-full PoE | B-structured PoE | dedup-PoE (diagnostic) |
|---|---|---|---|---|
| permutation of candidates | EXPECTED_INVARIANT | 4e-16 ✓ | 3e-16 ✓ | ✓ |
| renamed query IDs | EXPECTED_INVARIANT | 2e-15 ✓ | 2e-15 ✓ | ✓ |
| unrelated, disconnected candidate | EXPECTED_INVARIANT | 2e-16 ✓ | 1e-16 ✓ | ✓ |
| **exact duplicate candidate** | EXPECTED_INVARIANT | **0.180 ✗** | **0.167 ✗** | 0 ✓ |
| one-move omission added as a candidate (no new factor; 3 roots) | EXPECTED_INVARIANT | — | **0.046 ✗** | **0.046 ✗** |
| same with a new factor (scene–repair coupling or its own zR–zO pairs) | ALLOWED_CHANGE | 0.042 | 0.0001 | same |
| genuinely related new candidate | ALLOWED_CHANGE | 0.140 | 0.193 | same |
| scene prior, every case | must not move | 0 | 0 | 0 |

**Choice stability.** Under an exact duplicate, the preferred candidate (fewest moves among p ≥ 0.5, then highest p) changes on 1/12 (B-full), 3/12 (B-structured) and 2/12 (C-full) roots (`l3a1/artifacts.json`).

Deduplicating repeated *blocks* fixes exact duplicates only. It cannot remove the repeated unary of a query reused across *different* blocks, so it is a diagnostic, not the unique-factor model.

**Label isolation.** Scrambling every label and status on a root leaves the PoE prior marginals bit-identical (max change 0.0).

**Classification correction during the audit.** My first alias-case construction chose the first omission-only query, which on some roots had two moves. Such a candidate carries its own new `zR–zO` omission pairs, a genuinely new relation. The expectation is now set per root: invariance is required only for one-move aliases without generic coupling. Both the audit and the artifacts were rerun.

## 5. Gate and accounting

- **Checks:**
  - head equals origin;
  - only pre-existing user changes;
  - P9 gates PASS;
  - checkpoints match manifests;
  - canonical query identity;
  - prior label isolation;
  - scene prior consistent in every case;
  - zero teacher / planner calls.
- **Evidence:** `runs/p9/l3/l3a0/{source_state, identity, multiplicity, prediction_modes, sensitivity, audit_done}.json`; ledger `runs/p9/l3/guards/`.
- **Compute:** audit runs 3.7 + 12.4 + 12.3 CPU-s (rerun after the classification fix), all charged to the 8,000 CPU-s L3 budget.
