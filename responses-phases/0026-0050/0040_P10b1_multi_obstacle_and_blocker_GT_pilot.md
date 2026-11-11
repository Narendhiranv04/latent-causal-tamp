# 0040 — P10b-1: first 40 independent roots, multi-obstacle witnesses and D blocker ground truth

**Actual result.**
- **Collection:** 40 / 40 roster roots constructed (train 30, validation 10; no blind root) under the frozen plan `sha256:2057cc90…`, which was pushed (`a369327`) before any label.
- **Outcomes:** 438 queries. **141 VERIFIED, 220 CERTIFIED, 64 BUDGET, 13 UNKNOWN**; 96 % of the required contrast queries are decided.
- **Long repairs:** **4 / 4 three-move** (H10_3) and **4 / 4 four-move** (H10_4) physically witnessed repairs.
- **D labels:** **35 / 40** complete blocker masks, **26** of them proof-grounded.
- **Gate:** the preregistered P10b-1 gate (`runs/p10b/P10B1_GATE.json`) returned **STOP on a single check: proof-grounded H3 = 0 / 4.** Following the contract, I revised only the development constructor (H3 V1.1, adding placement intent) and ran one bounded development attempt. That attempt realized H3 on **5 / 6** development roots, proof-grounded. Decision: **GO** for P10b-2 with V1.1 (`runs/p10b/P10B1_GATE_REVISION.json`).

## 1. Yield by family (realized = the mechanism itself, corrected semantics)

| family | roots | realized | proof-grounded realized | note |
|---|---|---|---|---|
| H1 complementarity | 4 | 4 | 4 | κ = +1 four-tuples, all CERTIFIED / VERIFIED |
| H2a redundancy | 4 | 3 | 3 | one tuple incomplete |
| H2b neutral | 4 | 4 | 4 | |
| H3 order | 4 | **0** | 0 | `A B` CERTIFIED on all 4; `B A` 2 × BUDGET (A has no place candidate at dA), 2 × UNKNOWN (CPU-censored) |
| H4 omission | 4 | 4 | 4 | |
| H5 feasible original | 4 | 4 | 4 | |
| H7 edit vs executable | 4 | **4** | 4 | edit VERIFIED, physical relocation CERTIFIED (FIRST_MOVER / ORDER_FIRST_ACTION, placement-screen scope) |
| H8 sweep obstruction | 4 | 4 | 2 | original sector-CERTIFIED; barrier removal VERIFIED |
| H10_3 three-move | 4 | **4** | — | witnessed `C B A`; minimality relative to catalogue OPERATIONAL (4 / 4) |
| H10_4 four-move | 4 | **4** | — | witnessed 4-move repairs; minimality SOUND 2, OPERATIONAL 2 |

- **H10 witnessed lengths:** 3 (H10_3) and 4 (H10_4) on every root. No shorter catalogue repair succeeded.
- **H10 minimality is relative to the frozen catalogue only.** It is never a global minimum. "OPERATIONAL" means at least one shorter candidate is a BUDGET (not certified) negative.

**H3 diagnosis and revision (development evidence only).**
- In batch 1 the reused P10a template accepted roots where the movers can be *picked* but not *placed*: A's destination dA had no placement candidate after B moved (roots 15, 16).
- **V1.1** adds pose-screen placement intent (B at dB, then A at dA). Re-checked against batch 1, it would have rejected roots 15 and 16 (0 place candidates). Roots 13 and 14 pass it; their failure was CPU censoring of planning.
- **Development attempt** (`runs/p10b/dev_h3v11`, 6 development seeds): 5 realized proof-grounded, 1 UNKNOWN.
- The batch-1 H3 roots stay in the training data as constructed (V1). No other family changed, and teacher semantics are unchanged.

## 2. D blocker ground truth (all 2^n parking subsets, target-only scene edits)

| mask type | roots | provenance |
|---|---|---|
| single blocker {A} | 14 | proof-grounded |
| jointly necessary pair {A, B} (H1) | 8 | proof-grounded |
| alternative minimal sets {A} or {B} (H2a, union mask) | 3 | proof-grounded |
| feasible original (empty mask) | 4 | proof-grounded |
| H10 corridor masks {A, B, C}, {A, B, C, E} | 8 | **operational** |
| other complete | 1 | operational |
| INCOMPLETE (UNKNOWN subsets) | 5 | — |

- The independent minimal-set check agrees on every complete mask.
- **Physical finding (H10).** Parking only A, the one object adjacent to the target, does **not** make the target retrievable. It fails operationally, with three clean BUDGET seeds. Only parking the whole grasp corridor (A + B + C, plus E in H10_4) succeeds. The arm's links sweep the corridor cells on the approach. So in this scene family the D "blockers" are the corridor, which also explains why the three- and four-move repairs are needed.
- These masks are operational, so by the preregistration they are evaluated separately and **not** used for D's blocker loss.

## 3. Cost and compute

| item | value |
|---|---|
| teacher queries needing a call | 218 |
| median query cost | 4.3 CPU-s |
| p95 query cost | 95.1 CPU-s (censored seeds) |
| batch-1 teacher spend incl. static admission | ≈ 3,000 CPU-s (≈ 75 CPU-s / root) |

**Ledger to date:**

| category | used / cap (CPU-s) |
|---|---|
| teacher | 3,867 / 24,000 |
| constructor_dev | 395 / 3,000 |
| evaluation | 86 / 5,000 |
| training | 175 (cap lifted to 200,000 by user instruction; `PREREG_ADDENDUM_1.json`) |

## 4. Figures (`visualizations/p10b/`)

- `P10b1_atlas.png`: every batch-1 root with its anchor and adjudicated status.
- `P10b1_long_repairs.gif`: recorded 3- / 4-relocation witnesses.
- `P10b1_D_masks.png`: all parking subsets for H1 roots. The joint blocker pair is visible: only "park A + B" is VERIFIED. Parking edits are labelled HYPOTHETICAL.

**Next:** P10b-2. 140 roots (50 train, 25 validation, 65 blind) are frozen in four batch plans before any label, collected in roster order. Blind outcomes go to `sealed/` only.
