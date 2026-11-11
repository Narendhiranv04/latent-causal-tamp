# 0039 — P10b-0: source audit, P10a erratum, corrected yield gate, H7 / H8 development, D model and preregistration

**Actual result.**
- **Gate:** `runs/p10b/P10B0_GATE.json` → **PASS** (9/9 checks).
- **Audit:** read-only; HEAD = origin = `dd12f0c`. It covers the P10a hashes, decision replay, constructor replay and 13 / 13 checkpoints.
- **D:** the D model and its 9 synthetic tests pass.
- **Preregistration:** `runs/p10b/p10b0/P10B_PREREG.json`, `sha256:5cf3040e…`. It holds the 180-root roster, endpoints, statistics, the teacher policy and the training / ablation plan, and was frozen **before any roster label**.
- **H7 and H8 development** (development seeds only, never in the dataset):
  - **H7 realized on 2 / 2 dev roots.** The edit is VERIFIED; the physical relocation is CERTIFIED.
  - **H8 realized on 1 / 2.** The original is sector-CERTIFIED and barrier removal is VERIFIED. The other root is UNKNOWN because target planning was censored.
- **Correction to P10a:** under the contract's corrected yield gate, H7 and H8 were **not** realized in P10a. Reports 0038 / P10a_NEXT_DECISION already said so; P10A_GATE's "pass" for H7 / H8 tested decidedness only.

Previous turn sync: `dd12f0ce354c16e2525f88805cf2a8b5e811aadf` (prediction freeze `3afa81c`).

## 1. Audit (`runs/p10b/p10b0/audit.json`)

All of the following were checked and passed:
- HEAD = origin/main = `dd12f0c`;
- `3afa81c` and `dd12f0c` are ancestors of HEAD;
- the P10a plan hash and the predictions hash recompute;
- adjudication replayed from `progress.json` equals `decisions.json` (110 / 110);
- re-running the P10a constructor on root 01 at its recorded attempt reproduces the same scene hash;
- the learner records are bound to the plan;
- all 13 checkpoints match their stored SHA-256;
- both P10 gates read PASS.

**Source drift:** exactly one file. `p10_scenes._try` gained a backward-compatible root-prefix hook (`spec.get('prefix', 'p10a')`), which is why the replay above was run. The only tracked working-tree changes are that hook and the user's two PDF deletions, which are never staged.

## 2. Erratum to 0038 (P10a H1 root 01)

0038 §5 says every arm predicts "the single sequence `A` to be feasible (0.74–1.00). Both are sound negatives." That is **wrong for root 01**:

| query | status | evidence |
|---|---|---|
| physical sequence `A` (root 01) | **BUDGET_INFEASIBLE** | operational: three clean `SCHEDULE_COMPLETED_NO_WITNESS_UNCERTIFIED_REJECTIONS` seeds |
| scene edit A (root 01) | CERTIFIED | `LINK0_SECTOR_PICK` |
| physical sequence `A` (root 08) | CERTIFIED | `LINK0_SECTOR_PICK` on the first action |

Only the **edit** enters the proof-grounded κ = +1 four-tuple (0038 §4 used the edit, correctly). The other status wording in 0038 was re-verified against `decisions.json` and is correct.

## 3. Corrected mechanism-yield gate

The P10a gate counted H7 / H8 as passing because their anchors were *decided*. The contract requires the mechanism itself to be **realized**:
- **H7:** edit VERIFIED **and** physical relocation decided infeasible.
- **H8:** the original task decided infeasible.

Re-evaluated on P10a (`audit.json → p10a_corrected_gate`):
- **H7 roots 06, 13:** edit feasible yes; relocation infeasible **no**. Not realized.
- **H8 roots 07, 14:** original infeasible **no**. Not realized.

## 4. Revised constructors (P10B_FAMILIES_V1, `p10b_scenes.py`) and development evidence

**H7 (enclosed destination).**
- M occludes T's grasp, and T's N / S are fixed.
- M's catalogue destination dM is enclosed on N, S and W by fixed bodies. Its alternative M* is open.
- Acceptance uses only the existing checkers and pose-screen intent:
  - z0 certified;
  - the M-edit is open;
  - M is pickable;
  - no screen-passing place at dM;
  - a place exists at M*.

Dev pilot (`runs/p10b/dev_h7h8`), both roots:

| query | status |
|---|---|
| edit A (teleport M to dM) | VERIFIED (witness, 8 / 2 CPU-s) |
| physical `M` | CERTIFIED: **FIRST_MOVER**, PLACE stage |
| `M D` | CERTIFIED: ORDER_FIRST_ACTION |
| `D M` | BUDGET: PLACE_SCREEN_EXHAUSTED ×3 |
| `M*` | VERIFIED |

- **What the negative relies on.** FIRST_MOVER is a pre-existing (G4A) certificate kind that the independent checker accepted. Its PLACE stage is a definite pose-only screen over the declared 48-direction grasp family with the centred grasp. Scope is ASSIGNMENT, i.e. this mover as first mover to this destination.
- **What it is not.** It is not the disabled LINK0 place-side sector certificate, and nothing new was invented. H7 negatives are reported with this scope.

**H8 (sweep barrier only).**
- A barrier sits in the link-0 annulus between the start and target angles. There is no grasp occluder.
- Acceptance uses the **sector checker on the original task** plus eligibility of the barrier-removal edit. There are no pose screens, so the family is constructor-disjoint from G+M's pose-screen intent.
- Dev root 03:
  - original CERTIFIED (`LINK0_SECTOR_PICK`);
  - edit A and physical `M` VERIFIED;
  - `M D` VERIFIED, `D M` sector-CERTIFIED.
- Dev root 02: original CERTIFIED, but the barrier-removal edit and every sequence containing M were CPU-censored at 95 s, so they are UNKNOWN. H8 yield is therefore expected to be about 50 %.

**H10.** Development-seed designs are shown PROPOSED in `visualizations/p10b/P10b0_designs_and_dev_pilot.png`. No H10 teacher call was made in P10b-0.
- **H10_3:** A blocks T, B blocks A, C blocks B. Static predicates:
  - z0 TARGET_PICK;
  - `B C A` and `A B C` ORDER_FIRST_ACTION;
  - `C B` TARGET_PICK;
  - pick intent after each prefix.
- **H10_4:** H10_3 plus a sweep barrier E. Additionally, edit A is sector-certified and edit E is TARGET_PICK.
- **Trap:** A* (A parked inside the sweep sector).

**Constructibility on 30 development attempts per family** (`probe_n30.json`):

| family | acceptance rate |
|---|---|
| H1 | 0.33 |
| H2a | 0.23 |
| H2b | 0.17 |
| H3 | 0.20 |
| H4 | 0.40 |
| H5 | 0.37 |
| H7 | 0.30 |
| H8 | 0.23 |
| H10_3 | 0.17 |
| H10_4 | 0.13 |

Cost is 0.24–1.03 CPU-s per attempt.

## 5. D_BLOCKERS_V1 (`d_blockers.py`) — mathematics and tests

**Model:**
- `P_D(y0=1, b=0 | S) = σ(u)`
- `P_D(y0=0, b | S) = (1−σ(u)) · exp(Σ a_i b_i + Σ_{i<j} w_ij b_i b_j) / Z_B(S)`
- Z_B is computed by exact enumeration over `{0,1}^n` with n ≤ 6. Above that it fails closed (`CapError`).

**Networks:** `u`, `a_i` and `w_ij` are three compact MLPs over one object encoder: frozen DINOv2 projection plus the project's 14 geometry features, with the target token and the robot / goal context. `w_ij` is symmetrized. There is no GNN, GRU, decoder or search.

**Loss and labels:**
- **Loss:** BCE(σ(u), y0) + λ_B · 1[y0 = 0, mask complete] · (−log P(b | y0 = 0)). An incomplete mask contributes the feasibility term only.
- **Labels (`minimal_sets`):** from the statuses of all 2^n parking subsets:
  - minimal sets = VERIFIED subsets whose every proper subset is decided 0;
  - mask = union participation;
  - `necessary` = intersection;
  - FEASIBLE_ORIGINAL → all-zero mask;
  - NO_CLEARING_SET_WITHIN_POOL → all-zero mask, within this scope only;
  - INCOMPLETE / NON_MONOTONE / ineligible → mask UNKNOWN;
  - provenance is proof-grounded only if every proper subset used is CERTIFIED.
- **Collector cross-check:** `p10b_dataset.d_labels` re-derives every complete mask independently (minimal = VERIFIED with no VERIFIED proper subset).

**Parking map:** the frozen `p6._dests` rule (free, annulus-safe, ≥ 2 cells from target and goal, nearest), in role order. It is frozen with the plan and is never learned, ranked or executed. D subsets that coincide with an A / B / C edit share its query ID (one physical query).

**Tests** (`tests/test_d_blockers.py`, 9 passed; log `runs/p10b/p10b0/test_d_blockers.log`):
- exact normalization against brute force, summing to 1 over all `(y0, b)`;
- `gradcheck`;
- permutation equivariance;
- pairless control has w = 0 and factorized marginals;
- partial masks contribute feasibility only;
- the cap fails closed;
- minimal-set cases: alternative, joint, feasible, no clearing set, non-monotone, incomplete, operational;
- independent enumerator against `minimal_sets` on 200 random monotone tables;
- **0 physical calls** in D inference and the heuristic.

**Scope fence:** no destination, placement, order, recursion or execution. See `D_DESTINATION_AND_RECURSION_DEFERRED.md`.

## 6. Preregistration (summary of `P10B_PREREG.json`)

**Roster** (`p10b_prereg.roster`): 180 independent roots, seeds 2026111001 onward.

| family | train / validation / blind |
|---|---|
| H1 | 8 / 4 / 9 |
| H2a | 7 / 3 / 5 |
| H2b | 7 / 3 / 4 |
| H3 | 8 / 4 / 9 |
| H4 | 8 / 3 / 7 |
| H5 | 7 / 3 / 5 |
| H7 | 7 / 3 / 4 |
| H8 | 8 / 3 / 4 |
| H10_3 | 10 / 5 / 9 |
| H10_4 | 10 / 4 / 9 |
| **total** | **80 / 35 / 65** |

- **Batches:** batch 1 (P10b-1) = 40 roots (per family 3 train + 1 validation). Batches 2–5 (P10b-2) = 35 roots each, with splits interleaved.
- **P10a:** its 14 roots are disclosed development data (training only).
- **Teacher P10B_S100_V1:**
  - OPNEG-v1 adjudication unchanged;
  - seed 100 CPU-s (kill at 95);
  - query 330 CPU-s / 900 s, so all three seeds fit;
  - root 900 CPU-s;
  - a censored seed ends the query (UNKNOWN, never BUDGET);
  - one worker.

  Both options (A: P10a 120 CPU-s; B: full seeds) were predeclared, and B was chosen before any label.
- **Blind outcomes** are written only to `<batch>/sealed/`. `p10b_dataset.records` refuses blind splits until `runs/p10b/UNSEALED` exists, which is created only after the prediction freeze is committed.
- **Primary endpoints (Holm over P1–P4):**

  | endpoint | measure | primary contrast |
  |---|---|---|
  | P1 | blind strict TOP1 executed success | B vs SF |
  | P2 | H1 \|κ̂ − κ\| | B vs A |
  | P3 | proof-grounded order choice (H3 + H10) | C vs B |
  | P4 | omission necessity | B vs SF |

  D's primary is blocker F1 on blind complete masks, D vs D-pairless.
- **Underpowered rule:** fewer than 5 decided roots → UNDERPOWERED. Per-mechanism blind counts of 4–9 will stay UNDERPOWERED for small effects; stated in advance.
- **Training:**
  - 400 updates × 3 seeds;
  - selection on P10b validation only;
  - full-data and short-sequence (≤ 2 moves, no H10) regimes;
  - ablation priority: F2 order-invariant, F4 no omission pair, F5 structured, F5 quadratic, F3 no scene pair, visual-zero, unique. Arms that do not fit the cap are NOT_RUN.

## 7. Compute (`runs/p10b/guards/`)

| category | used / cap (CPU-s) | notes |
|---|---|---|
| constructor_dev | 221.4 / 3,000 | |
| teacher | 625.3 / 24,000 | dev H7 / H8 pilot; 6 censored 95 s seeds account for most of it |
| evaluation | 13.6 / 5,000 | |
| training | 0 / 24,000 | |
| execution | 0 / 15,000 | |

**Next:** P10b-1, the first 40 roster roots (train / validation only).
