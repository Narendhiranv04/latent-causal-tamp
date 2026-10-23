# 0038 — P10a: bounded physical constructibility pilot, label provenance, and frozen-prediction diagnosis

**Actual result.**
- **Engineering gate:** `runs/p10/P10A_GATE.json` → **PASS** (15/15).
- **Construction:** 14 independent roots (7 mechanisms × 2 waves) and **110 queries**.
- **Teacher results:** 104 / 110 queries decided.
  - **64 VERIFIED**, **40 CERTIFIED**, **3 BUDGET_INFEASIBLE** (operational), **3 UNKNOWN**, 0 NOT_RUN, 0 FATAL.
  - Teacher spend was **582.8 / 5,000 CPU-s**, with 70 queries needing a teacher call and 78 seed attempts.
- **Wave-1 yield gate:** passed for all 7 mechanisms, including the sound-negative requirement for H1 and H3. Every wave-2 root ran.
- **Proof-grounded mechanisms obtained:**
  - H1 κ = +1 (2 / 2 roots);
  - H2 κ = −1 and κ = 0 (1 + 1);
  - H3 opposite-order pairs with one VERIFIED and one CERTIFIED order (2 / 2);
  - H4 necessity and redundancy omissions (4 omissions, 2 roots);
  - H5 feasible original with a certified harmful edit (2 / 2).
- **Not obtained:**
  - **H7:** no edit-vs-executable mismatch; the executable relocation was also feasible in both roots.
  - **H8:** no obstruction realized; the original task was VERIFIED in both roots.
- **Frozen-prediction diagnosis** (exploratory; adaptive roots, not a blind test):
  - **No** arm predicts complementarity: every κ̂ on the two H1 κ = +1 roots is ≤ 0.43, and the observed κ is 1.
  - **No** arm discriminates opposite orders: margins below 0.02.
  - All arms get the H4 omissions right.
  - On per-root NLL of decided outcomes, keyed **B is worse than A and SF**: +0.52 [+0.07, +1.04] for each.
- **Pre-registered primaries:** H1, H3 and H4 are all **UNDERPOWERED** (2 roots each).

Previous turn sync: `37cd2b7b84ce4666f93b13f31db331ae96a3e457`. Freeze commit (plan + predictions, pushed **before** static admission): `3afa81c2f8804fc1a8d11e08e2b3f010286fc784`.

## 1. Construction (`p10_scenes.py`, `P10A_MECHANISMS_V1`; plan `sha256:44bc199b…`)

**All 14 roots are CERTIFICATE_TARGETED, i.e. adaptive.** Construction used the pose screens and sound pick-side certificate checkers only: no planner, no teacher. These roots are therefore never a blind holdout. Each root's layout is a parameterized template around the target's grasp-side enclosure; the predicates and checkers decide acceptance.

| H | template (roles) | acceptance predicates (sound checkers / pose-screen intent) |
|---|---|---|
| H1 | A = grasp occluder (W), B = link-0 sweep barrier between start and target angle; N, S fixed | z0 certified; A+B open; **A-edit LINK0_SECTOR_PICK**; **B-edit TARGET_PICK** |
| H2 | κ−1: two of W / N / S as A, B; κ0: one side plus a far B | z0 TARGET_PICK; A+B open; κ−1: A and B each open; κ0: A open, B certified |
| H3 | A = N or S of T, boxed by T, its outer cell and the W diagonal | z0 TARGET_PICK; **A-first ORDER_FIRST_ACTION**; B pickable; A pickable after B; open after both |
| H4 | A = W occluder, N, S fixed; C far | z0 TARGET_PICK; A-edit open; C-alone TARGET_PICK; open after both |
| H5 | two of W / N / S fixed; X, Y far; X's edit destination = third side | original open; X-edit TARGET_PICK; Y-edit open |
| H7 | M = W occluder (N, S, W-of-M fixed); D far | z0 certified; M-edit open. **Executable-failure side NOT targeted** |
| H8 | angles only: M between target and goal angle, not on the start sweep | angle conditions only (ANGLE_ONLY; no pose screens) |

**Constructor development** (all charged to the construction ledger and disclosed): 12 guarded jobs, 1,115.3 CPU-s, including:

| job | CPU-s | outcome |
|---|---|---|
| first dry run | 502 | guard ERROR at the internal cap |
| `probe2` | 285 | CPU_CENSORED |
| `probe6` | ≈ 0 | syntax ERROR, ≈ 0 CPU |

**Constructibility per mechanism** (25-attempt probes):

| mechanism | accepted / attempts |
|---|---|
| H1 | 5 / 25 (after the redesign) |
| H2 κ−1 | 5 / 25 |
| H2 κ0 | 9 / 25 |
| H3 | 4 / 25 |
| H4 | 11 / 25 |
| H5 | 8 / 25 |
| H8 | 3 / 25 |

**H7 attempts:** three enclosure designs gave **0 / 38** certified failures for physically relocating M (`construction_probe_n100.json`, `construction_probe_n25.json`). I therefore dropped that predicate and labelled it in the plan. The final construction took 22.2 CPU-s, and no root was unavailable.

**Redesigns made during development** (each before any teacher call):
- **H1:** a series of W-corridor blockers never gave complementarity, because removing W alone always opened the grasp. H1 was redesigned as two certified mechanisms: grasp occlusion plus a link-0 sweep barrier.
- **H3:** the A = W variant failed "open after B, A". It became A = N or S.
- **H7:** redesigned twice, as above.

**Catalogues:** 7–9 queries per root (cap 16), anchor first, in a fixed outcome-blind priority. They cover scene edits A, B and A+B (target-only evaluation in the edited scene), the empty repair, both orders, and singles. Seed keys come from the unchanged OPNEG-v1 template.

**Figure:** `visualizations/p10/P10a_scene_atlas.png` (all 14 roots at q0 with roles, goal, stratum and the anchor proposal tagged PROPOSED).

## 2. Order of operations (what was frozen when)

1. The plan was frozen: roots, catalogues, query IDs, priorities and seed units.
2. Unlabelled learner records were built (DINOv2 and geometry only).
3. **Predictions were frozen** from all 13 available checkpoints: 12 P10-0 runs plus the frozen `K-B-full#s1`. The snapshot hash is `sha256:949bb351…`; there were **0 physical calls** and no NOT_RUN catalogue. It holds root-prior marginals for every modelled query, per-candidate J and the TOP1 choice with the frozen τ and threshold.
4. Plan and predictions were **committed and pushed** (`3afa81c`).
5. Static admission ran (77.5 CPU-s, charged to the teacher budget). It certified 40 queries.
6. Teacher collection ran.
7. Offline scoring ran. Nothing was tuned on P10a labels.

## 3. Teacher limits and provenance

- **Execution limits are tighter than OPNEG-v1** (adjudication still uses the unchanged policy hash):
  - seed guard 100 CPU-s (kill at 95);
  - orchestration reserve 10 s;
  - query ≤ 120 CPU-s and ≤ 360 s wall;
  - one worker.
- **Seed admission:** a later seed starts only while `spent + 110 ≤ 120`. A cut seed is censored → UNKNOWN, never BUDGET.
- **Stop rule:** a root whose anchor is not VERIFIED would have its remaining planner-requiring queries marked NOT_RUN. It never triggered: every anchor was VERIFIED.
- **Ledger:** append-only, `runs/p10/p10a/teacher_calls.jsonl`. Each line records caller stage `LABEL_ACQUISITION`, root and query IDs, input hash, status and provenance, static certificate, per-seed terminals with CPU and wall, and the plan hash. Raw unit outputs are under `runs/p10/p10a/q/`.
- **Teacher cost:**
  - median 4.1 CPU-s per teacher query;
  - max 81.6 (one `SEARCH_LIMIT` seed);
  - all 78 seed attempts COMPLETED (none censored);
  - wall 510.8 s.

| mechanism | VERIFIED | CERTIFIED | BUDGET | UNKNOWN |
|---|---|---|---|---|
| H1 | 5 | 10 | 1 | 0 |
| H2 | 9 | 4 | 0 | 1 |
| H3 | 6 | 10 | 0 | 0 |
| H4 | 12 | 6 | 0 | 0 |
| H5 | 6 | 4 | 2 | 2 |
| H7 | 10 | 6 | 0 | 0 |
| H8 | 16 | 0 | 0 | 0 |

**Certificate kinds** (all pick-side, all re-checked by the independent checkers; **no place-side certificate**):

| kind | scope |
|---|---|
| `TARGET_PICK` | the target is ungraspable with the remaining objects |
| `LINK0_SECTOR_PICK` | the link-0 sweep from the fixed start is blocked |
| `ORDER_FIRST_ACTION` | the first mover cannot be picked |
| `FIRST_MOVER` | as above |

**The 6 undecided or operational outcomes** (reported as prominently as the positives):
- **H1 root 01, `A` (sequence: relocate only the grasp occluder):** BUDGET. Three clean `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS` seeds of 1–2 CPU-s each. This is operational only. Its edit counterpart is sector-certified.
- **H5 roots 05 / 12, `X`:** BUDGET. `PICK_SCREEN_EXHAUSTED_CERTIFIED` × 3.
- **H5 roots 05 / 12, `Y X`:** UNKNOWN. The first two seeds were clean but used 11–12 CPU-s together, so the **P10a seed-admission rule** (`spent + 110 ≤ 120`) excluded seed 3. This UNKNOWN is created by the tightened cap, not by the planner.
- **H2 root 09, `A B`:** UNKNOWN. Seed 1 hit `SEARCH_LIMIT_PLAN_FAILURES` at 82 CPU-s, and no further seed fit.

## 4. Decided-contrast matrix (proof-grounded vs operational kept apart)

| H | root (wave) | contrast | observed | stratum |
|---|---|---|---|---|
| H1 | 01 (1) | y0, yA, yB, yAB = 0, 0, 0, 1 | **κ = +1** | proof-grounded (A: sector certificate; B, 0: TARGET_PICK; AB: witness) |
| H1 | 08 (2) | 0, 0, 0, 1 | **κ = +1** | proof-grounded |
| H2 | 02 (1) | 0, 1, 1, 1 | **κ = −1** | proof-grounded |
| H2 | 09 (2) | 0, 1, 0, 1 | κ = 0 | proof-grounded |
| H3 | 03 (1) | `B A` VERIFIED / `A B` CERTIFIED (ORDER_FIRST_ACTION) | order matters | proof-grounded |
| H3 | 10 (2) | `B A` VERIFIED / `A B` CERTIFIED | order matters | proof-grounded |
| H4 | 04, 11 | `C A` VERIFIED; omit C → `A` VERIFIED (C redundant); omit A → `C` CERTIFIED (A necessary) | necessity + redundancy | proof-grounded (4 omissions) |
| H5 | 05, 12 | original VERIFIED; harmful edit X → CERTIFIED; neutral Y → VERIFIED | — | proof-grounded (`X` sequence operational) |
| H7 | 06, 13 | edit A VERIFIED; executable `M` VERIFIED | **no discrepancy (0)** | proof-grounded, mechanism **not realized** |
| H8 | 07, 14 | original (empty) VERIFIED; all 8 queries VERIFIED | **no obstruction** | mechanism **not realized** |

**Contrast yield:** 12 / 14 roots carry a decided proof-grounded contrast of their mechanism (5 / 7 mechanisms in both waves).

## 5. Frozen predictions vs outcomes (exploratory; nothing tuned on P10a labels)

**κ̂ (seed mean) on the κ roots:**

| root | κ | K-B | K-C | A | SF | frozen B |
|---|---|---|---|---|---|---|
| H1 01 | +1 | 0.25 | 0.23 | 0.43 | 0.03 | −0.09 |
| H1 08 | +1 | −0.16 | 0.00 | 0.21 | 0.04 | −0.04 |
| H2 02 | −1 | −0.08 | −0.01 | −0.96 | −0.86 | −0.01 |
| H2 09 | 0 | −0.03 | 0.00 | −0.08 | 0.00 | −0.04 |

- **Failure mode (H1):** every arm predicts the single grasp-freeing edit A to be feasible (p 0.74–1.00, both roots) and the single sequence `A` to be feasible (0.74–1.00). Both are sound negatives, because the link-0 sweep barrier B remains. The training distribution contains no sweep-barrier mechanism, so this is a coverage failure.
- **H1 primary (B − A on |κ̂ − κ|):** +0.27 per root (B worse) on n = 2. **UNDERPOWERED.**
- **H2 κ = −1 (root 02):** the factorized A and SF predict redundancy; both keyed models predict κ ≈ 0. Their joint coupling assigns the single edits too little feasibility.

**H3 (order choice; primary C vs B):**
- Both pairs are proof-grounded.
- The margin p(feasible order) − p(infeasible order) is at most |0.018| for every arm. Every model assigns 0.90–1.00 to **both** orders.
- C correct 0 / 2, B 0 / 2; A 1 / 2, SF 1 / 2, frozen B 1 / 2. This is chance-level: no order discrimination. **UNDERPOWERED.**

**H4 (omission necessity; primary B vs SF):** every arm is correct on all 4 omissions (2 roots). This is a ceiling, not a discriminating contrast. **UNDERPOWERED.**

**H5 TOP1:**
- A (3 / 3 seeds) and frozen B choose the empty repair on both roots.
- Keyed K-B and K-C mostly abstain or choose `Y X` (UNKNOWN): 1 / 6 runs choose empty for K-B, 0 / 6 for K-C.
- The keyed models under-predict the feasibility of an already-feasible original.

**H7 / H8:**
- **H7:** observed contrast 0; the sign matches only where predictions are ≈ 0.
- **H8:** keyed models give the VERIFIED anchor p = 0.36–0.92. Their per-root NLL on the all-feasible H8 roots is 2.6–2.7, vs 0.2–0.4 for A and SF: these are false negatives in novel geometry.

**Common per-event metrics** (root-prior p on the same 104 decided outcomes, pooled over seeds):

| arm | NLL | accuracy | AUROC | Brier | ECE | false + | false − |
|---|---|---|---|---|---|---|---|
| K-B-full | 1.528 | 0.738 | 0.799 | 0.243 | 0.251 | 34 | 50 |
| K-C-full | 1.684 | 0.732 | 0.787 | 0.248 | 0.250 | 39 | 47 |
| A | 0.839 | 0.794 | 0.821 | 0.176 | 0.153 | 48 | 18 |
| SF | 0.730 | 0.826 | 0.870 | 0.151 | 0.136 | 34 | 22 |
| frozen K-B-full#s1 | 1.068 | 0.785 | 0.813 | 0.197 | 0.193 | 11 | 12 |

Counts are over 3 seeds (1 for frozen). Operational-only rows (9 per arm) are reported separately in `P10A_RESULTS.json`.

**Paired per-root NLL** (seed-mean p; 14 independent roots; proof-grounded only; root-cluster bootstrap):

| contrast | mean | 95 % CI | LORO | roots better / worse |
|---|---|---|---|---|
| K-B − A | +0.558 | [+0.104, +1.075] | [+0.41, +0.64] | 5 / 9 |
| K-B − SF | +0.533 | [+0.067, +1.054] | [+0.38, +0.63] | 3 / 11 |
| K-C − K-B | +0.164 | [−0.049, +0.399] | [+0.09, +0.23] | 7 / 7 |
| SF − A | +0.025 | [−0.147, +0.221] | — | 9 / 5 |

**TOP1** (per checkpoint; success = choice VERIFIED):

| arm | runs × roots | VERIFIED | CERTIFIED | BUDGET | UNKNOWN | ABSTAIN |
|---|---|---|---|---|---|---|
| K-B-full | 42 | 27 | 8 | 2 | 2 | 3 |
| K-C-full | 42 | 24 | 9 | 3 | 4 | 2 |
| A | 42 | 29 | 11 | 2 | 0 | 0 |
| SF | 42 | 30 | 8 | 3 | 0 | 1 |
| frozen B | 14 | 10 | 3 | 1 | 0 | 0 |

The dominant TOP1 error is the same everywhere: the lexicographic fewest-moves rule picks an over-admitted single move on H1 and H3.

**Reading.**
- The current 2D teacher **can** ground H1, H2, H3, H4 and H5 in sound certificates and witnesses at about 42 teacher CPU-s per root.
- None of the trained models, joint or factorized, generalizes the causal structure to these new mechanism geometries.
- The keyed joint models are **worse** calibrated here than the factorized controls, which reverses the P10-0 validation ranking.
- This is a diagnosis on adaptive roots with n = 2 per mechanism. It is **not** a validation or refutation of the A / B / C hypotheses.

## 6. Gate (`runs/p10/P10A_GATE.json`) and compute

PASS. Every check passed:
- plan frozen before predictions and before the teacher (file order and the pushed commit);
- predictions bound to the plan hash;
- 0 physical calls in prediction;
- roots ≤ 14, queries ≤ 224, teacher queries 70 ≤ 224;
- teacher CPU ≤ 5,000;
- per-query unit CPU ≤ 120;
- per-seed ≤ 100;
- no FATAL;
- statuses preserved;
- no BUDGET from a censored seed;
- wave-1 gate recorded;
- wall ≤ 14,400 s.

| category | CPU-s | cap | jobs |
|---|---|---|---|
| construction (static, incl. development) | 1,115.3 | 1,500 (raised from 600 before any teacher call; disclosed) | 12 (3 non-COMPLETED) |
| teacher (static admission 78.7 + collection 504.2) | 582.8 | 5,000 | 2 |
| prediction (records, dry run, freeze, scoring) | 24.5 | 600 | 7 (2 ERROR) |
| figures | 90.6 | 1,500 | 1 |

**Figures** (`visualizations/p10/`, SHA-256 beside each file; robot motion only from recorded witness arrays):
- `P10a_scene_atlas.png`;
- `P10a_summary.png` (κ per root; outcomes by mechanism; reliability per arm);
- `P10_compute.png`;
- per root, `roots/<root>_card.png`: catalogue, statuses with certificate kind, and frozen p per arm;
- per root, `roots/<root>_evidence.gif`: recorded witnesses first (edits tagged HYPOTHETICAL SCENE EDIT), then static panels for certified, BUDGET and UNKNOWN outcomes ("NO VERIFIED TRACE" / certificate kind).
