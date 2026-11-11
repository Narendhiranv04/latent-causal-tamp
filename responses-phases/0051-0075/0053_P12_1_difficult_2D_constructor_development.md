# 0053 — P12-1: new physics-first 2D scene grammars (development only)

**Actual result.**
- **Gate:** `runs/p12/P12_1_GATE.json` → **PASS, with a scientific limitation**.
- **What worked:** two new grammars are constructible with **sound, model-independent prescreens**. They produce physically obstructed originals with executable 1–3-move repairs, at a forecast cost within the teacher cap.
- **Limitation: all 8 decided development four-tuples have κ = 0** (exactly one of the two edits suffices). Complementarity (κ = +1) was not observed in development.
  - Enriching κ would require either outcome-based selection, which is forbidden, or a further development teacher pilot, but the dev budget is exhausted (4,985 / 5,000 CPU-s).
  - The holdout therefore proceeds with the grammars **unchanged**. The F3 / F5 primaries are preregistered on all proof-grounded four-tuples (any κ), with this distribution disclosed in advance.

## 1. Grammars (`p12_families.py`, `P12_FAMILIES_V1_1`)

| family | generation mechanism | prescreen (sound, analytic) | how it differs from P10b |
|---|---|---|---|
| **X_SWEEP_GATE** | two blockers sampled independently in the link-0 inner annulus within ±0.5 rad of the start–target arc (either side); a third object C within Chebyshev 2 of the target | original has an accepted **LINK0_SECTOR_PICK** certificate | P10b H1 / H8 / H10_4 place one barrier between the start and target angle nearest the start, plus a grasp occluder or chain. X places **two** independently sampled barriers and no grasp occluder |
| **Y_BOTTLENECK** | two blockers in the target's approach cone (bearing to base ±75°) at Chebyshev 1–2, asymmetric; each non-cone Chebyshev-1 cell a fixed body with probability 0.7; C outside the cone | original has an accepted **TARGET_PICK** certificate | P10b grasp families use canonical W / N / S neighbours, chains or deterministic enclosures. Y samples cone positions at distance 1–2 with a stochastic side wall |

**Development revision:** Y V1 (no fixed bodies) passed the prescreen on **0 / 60** dev attempts, because two cone blockers never block all 48 grasps. V1.1 adds the stochastic side wall and passes 2 / 60. The revision was made before any holdout seed existed.

**Catalogue (generic, outcome-blind; 23 queries per root):** empty; singles; ordered pairs; ordered triples of A, B, C; edits A / B / A+B; all D parking subsets. Destinations and parking follow the frozen `p6._dests` rule.

## 2. Development evidence (16 dev roots planned, 12 adjudicated before the dev cap)

**Static acceptance** (60 dev attempts each):

| family | acceptance | rejections |
|---|---|---|
| X | 18.3 % | 42 sector prescreen, 7 start not clear |
| Y V1.1 | 3.3 % | 46 TARGET_PICK prescreen, 12 layout |

The plan's attempt ledger records every attempt and rejection reason.

**Teacher pilot** (`runs/p12/dev`, dev-only):

| outcome | value |
|---|---|
| originals | all CERTIFIED (prescreen holds) |
| proof-grounded four-tuples | 8 of 11 complete roots; **κ class: 0 × 8** |
| undecided four-tuples | 3 (UNKNOWN edits from censored searches); root 008 (edits A, B CERTIFIED, A+B UNKNOWN) was the only potential κ = +1 |
| minimum verified repair length | 1 on most roots; 2–3-move witnesses also present |
| CPU per root | mean 338, median 252, p90 719 |

**Forecast** for 80 roots: about 27k teacher CPU-s plus static admission, within the 40k cap.

**Figure:** `visualizations/p12/P12_1_dev_atlas.png`, showing accepted dev roots with prescreen tags and rejected attempts with their reasons.

## 3. Consequences for P12-2 (stated before any holdout label)

- **Expected cohort:** if the holdout matches development, the F3 / F5 primaries will be evaluated mainly on **κ = 0** roots. They then test whether full B predicts "no interaction" more accurately than B-F3 / B-F5s on novel geometry. They do **not** test complementarity specifically.
- **κ = +1 roots, if any appear,** are reported as a subgroup.
- **Complementarity on novel families remains unresolved** unless such roots occur.
