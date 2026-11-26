# Final decision: structured-energy readouts (RQ2a) and execution-order sensitivity (RQ2b)

## Verdict

1. **Joint selection beats either readout alone.**
   - **3D (established):** J − X **+62.7 pp** [54.7, 70.4] and J − Y **+32.7 pp** [23.1, 41.9], both Holm p = 0.0002, 0 % UNKNOWN.
   - **2D:** the same direction (J − X +39.3, J − Y +16.7, both with randomization p < 0.001) but **INCONCLUSIVE** by the preregistered rule, because UNKNOWN is 24–45 %. In the worst case for J, UNKNOWN bounds allow −5.3 and −14.7 pp.
   - **The two failure modes are complementary:**
     - Marginal-X selection picks short, executable repairs that leave the target blocked (X = 1, Y = 0: 53 / 118 roots).
     - Y-only selection picks working final arrangements in orders that fail to execute (X = 0, Y = 1: 26 / 73).
2. **The frozen model prefers executable orders when the endpoint is identical.**
   - **Exposed VAL** (existing labels; selection-biased), on fully labelled three-move groups with Y = 1: the learned order succeeds 72 % (2D) / 76 % (3D), versus 42 % / 50 % for a random order and 39 % / 56 % for the canonical order. Mixed-group concordance is 0.71–0.83.
   - **Locked-cohort panel:** in 3D the learned order executed in 20 / 20 assignments, against 80 % canonical and 79 % random.
   - **This panel result is descriptive, not established.** It has only 9 (3D) and 5 (2D) mixed groups, below the preregistered minimum of 10.
3. **Is the order benefit measurable over canonical or random?**
   - **Yes on DEV for three-move repairs:** about +30 pp over random in 2D, +26 pp in 3D.
   - **Small for two-move repairs,** where both orders usually work (random already 84–87 %).
   - **Not established on the locked panel** (underpowered).
4. **Inconclusive:** every 2D deployment contrast (teacher UNKNOWN), the cohort order test (too few mixed groups), and order discrimination when the endpoint fails (3D m = 3, Y = 0: pX0 concordance 0.46 on 25 groups).

**Caveats that apply throughout:**
- This is a readout ablation of one frozen, jointly trained model. Marginal pX still contains pY, and the coupling w is still trained. It is not a retrained X-only or Y-only model.
- The same thresholds (gate 0.5, η 0.3) are not equally calibrated across events.
- Results are on a locked retrospective cohort (C0 / J outcomes were already known) plus exposed VAL.
- 3D negatives are teacher-budget-defined, not impossibility proofs.
- No causal-necessity claim follows from any of this.

## Integrity checks

- **J reproduces production exactly:** 20 / 20 VAL parity roots per domain against archived EXACT4, and 210 / 210 cohort roots per domain against the CR sealed C0.
- **Readouts are identical to `Scorer.score`** (0.0 difference). pY is identical across permutations (range 0). Cross-chunk float drift of at most 4e-7 is neutralized by sharing one pY per endpoint.
- **All four readouts come from one shared stream** of the identical top-4 pool (pool hashes sealed): mean 47,283 (2D) and 3,160 (3D) candidates per root.
- **Per-root time for all readouts together:** p50 / p90 0.80 / 5.7 s (2D) and 0.027 / 0.30 s (3D). No readout costs more than another, because one network produces them all.
- **No teacher calls at inference.**

## Main table (K1–K3, 50 roots per K per domain)

The rate is verified success over all roots, strict; brackets give the upper bound with UNKNOWN or UNQUERIED counted as success.

| | Arm | K1 | K2 | K3 | **K1–K3** | UNKNOWN | decided-only | mean length | K0 correct NOOP | NONE correct ABSTAIN (repairs) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2D | **J** (p11, released) | 66 | 72 | 26 | **54.7** [78.7] | 24.0 % | 71.9 | 2.65 | 100 | 100 (0) |
| 2D | **X** (marginal pX) | 40 | 6 | 0 | **15.3** [60.0] | 44.7 % | 27.7 | 1.06 | 100 | **0 (30)** |
| 2D | **Y** (pY) | 44 | 50 | 20 | **38.0** [69.3] | 31.3 % | 55.3 | 2.95 | 100 | 100 (0) |
| 2D | XC (pX1, secondary) | 24 | 0 | 0 | 8.0 [79.3] | 22.0 % + 49.3 % unqueried | 27.9 | 1.31 | 100 | 0 (30) |
| 3D | **J** | 66 | 78 | 82 | **75.3** | 0 | 75.3 | 2.37 | 86.7 | 83.3 (5) |
| 3D | **X** | 34 | 2 | 2 | **12.7** | 0 | 12.7 | 1.10 | 86.7 | **0 (30)** |
| 3D | **Y** | 40 | 46 | 42 | **42.7** | 0 | 42.7 | 2.62 | 86.7 | 76.7 (7) |
| 3D | XC (secondary) | 38 | 0 | 0 | 12.7 [57.3] | 0 + 44.7 % unqueried | 22.9 | 1.01 | 86.7 | 0 (30) |

- No repair on a NONE root was a verified success.
- The historical operational convention gives the same verified counts; UNKNOWN is never a success under either.

**K1–K3 outcomes by actual factor labels** (strict; ? = unresolved):

| | X1Y1 | X0Y1 | X1Y0 | X0Y0 | partial / unknown | NOOP |
|---|---|---|---|---|---|---|
| 2D J | 82 | 13 | 8 | 3 | 41 | 3 |
| 2D X | 23 | 0 | **53** | 0 | 71 | 3 |
| 2D Y | 57 | **26** | 6 | 4 | 54 | 3 |
| 3D J | 113 | 14 | 12 | 2 | 0 | 9 |
| 3D X | 19 | 1 | **118** | 3 | 0 | 9 |
| 3D Y | 64 | **73** | 0 | 4 | 0 | 9 |

**Paired contrasts.** Equal-K-weighted, whole-family bootstrap (4,000 draws); family sign-flip randomization (20,000 draws); Holm over the four primary contrasts.

| Contrast | 2D Δ pp [95 % CI] | 2D W / L | 3D Δ pp [95 % CI] | 3D W / L | Holm p (2D / 3D) | Verdict |
|---|---|---|---|---|---|---|
| **J − X** | +39.3 [31.0, 47.9]; complete-case +35.7 (n = 70); worst case −5.3 | 64 / 5 | **+62.7 [54.7, 70.4]** | 96 / 2 | 0.0002 / 0.0002 | 2D inconclusive (UNKNOWN 45 %) · **3D established** |
| **J − Y** | +16.7 [7.8, 25.6]; complete-case +15.9 (n = 88); worst case −14.7 | 38 / 13 | **+32.7 [23.1, 41.9]** | 57 / 8 | 0.0006 / 0.0002 | 2D inconclusive (UNKNOWN 31 %) · **3D established** |
| J − XC (secondary) | +46.7 [38.6, 54.5] | 72 / 2 | +62.7 [54.4, 71.0] | 98 / 4 | – | descriptive (XC partly unqueried) |
| Y − X (secondary) | +22.7 [13.4, 32.4] | 48 / 14 | +30.0 [21.4, 38.9] | 52 / 7 | – | descriptive |

**3D by K:** J − X +32 / +76 / +80 and J − Y +26 / +32 / +40 for K1 / K2 / K3. The joint readout matters most for longer repairs.

## Rank-only (no gate, no η, no no-op)

- On K1–K3 the rank-only picks equal the deployment picks wherever the gate did not fire, so the ranking contrasts are the same as above (3D rank-only J − X +63.3, J − Y +32.7).
- **3D J:** rank-only gives 77.3 % versus 75.3 % deployed. The production no-op gate returns NOOP on 9 K1–K3 roots, 3 of which have a verified repair.
- Rank-only cannot decline, so it repairs on every K0 and NONE root. The gate is what provides those safeguards (2D J 100 % / 100 %).
- **X-only fails to abstain even with the gate:** its admission readout (pX ≥ 0.3) passes almost always, so it repaired all 30 NONE roots in both domains.

## Factor diagnostics (exposed VAL, existing labels; `P2_DEV_*.json`)

| | 2D | 3D |
|---|---|---|
| pY vs Y, unique endpoints: AUROC / AUPRC (n) | 0.933 / 0.957 (29,433) | 0.939 / 0.946 (14,553) |
| marginal pX vs X | 0.805 / 0.914 (33,683) | 0.828 / 0.867 (15,703) |
| **pX1 vs X given Y = 1** | 0.769 / 0.935 (16,902) | 0.787 / 0.890 (8,382) |
| pX0 vs X given Y = 0 | 0.828 / 0.881 (7,871) | 0.840 / 0.817 (7,321) |
| p11 vs Z | 0.883 / 0.853 (31,197) | 0.884 / 0.817 (15,703) |
| Within-root Z concordance J / Y / X / XC | **0.774** / 0.744 / 0.686 / 0.646 (451 roots) | **0.815** / 0.793 / 0.667 / 0.657 (273) |
| Top-1 of the known labelled set is Z = 1: J / Y / X / XC | **0.72** / 0.62 / 0.44 / 0.35 | **0.81** / 0.73 / 0.38 / 0.33 |
| **pX1 vs X given Y = 1, within root** | **0.744** [0.721, 0.766] (402 roots) | **0.775** [0.756, 0.794] (259) |

**Correction of the earlier 2D report (`repair_ranking` P1, .718 / .706 / .451).**
- The .451 compared pX1 with Z across both Y classes. That is a repair-ranking diagnostic, not a test of pX1's own conditional label.
- Judged against its own label (X given Y = 1), pX1 is well above chance: 0.74–0.78 within root, AUROC 0.77–0.79.
- It ranks Z poorly (0.65) only because it ignores whether the endpoint works.
- With the larger label set and K3 included, the earlier ordering J ≥ Y > X1 still holds.
- Excluding layout-overlap roots changes within-root J by 0.01 or less.

## Matched-order results

**O-A: existing VAL labels.** Same root and assignment, all permutations scored; exposed DEV, selection-biased; m = number of objects.

| | m | groups (complete, Y = 1) | mixed (families) | concordance pX1 | learned top | canonical | random | oracle |
|---|---|---|---|---|---|---|---|---|
| 2D | 2 | 288 | 80 (78) | 0.83 [0.74, 0.90] | **92.7** | 84.0 | 83.7 | 97.6 |
| 2D | 3 | 173 | 188 (114) | 0.77 [0.72, 0.81] | **72.3** | 39.3 | 42.3 | 97.7 |
| 3D | 2 | 242 | 24 (20) | 0.71 [0.52, 0.88] | **88.8** | 85.1 | 86.8 | 91.7 |
| 3D | 3 | 70 | 111 (32) | 0.77 [0.70, 0.85] | **75.7** | 55.7 | 49.8 | 100 |

- The "learned top", "canonical", "random" and "oracle" columns give the % of complete groups whose chosen order has X = 1; "random" is the analytic n(X = 1) / m!.
- Endpoint-failing groups (Y = 0) are separate: pX0 concordance is 0.70–0.89, except 3D m = 3 at **0.46** (25 groups).

**O-B: locked-cohort panel** (preregistered; 20 legacy-witness assignments per domain, 20 families; all endpoints Y = 1).

| | complete | mixed (families) | all orders X = 1 | concordance | learned top | canonical | random | learned − random | chosen order unknown |
|---|---|---|---|---|---|---|---|---|---|
| 2D | 11 / 20 | 5 (5) | 8 | 0.75 [0.40, 1.00] | 11 / 11 | 81.8 % | 87.9 % | +12.1 [0, 24.2] | 4 |
| 3D | 20 / 20 | 9 (9) | 11 | 0.91 [0.80, 1.00] | **20 / 20** | 80.0 % | 79.2 % | **+20.8 [10.0, 33.3]** | 0 |
| 3D m = 3 only | 10 | 8 | 2 | 0.90 | 10 / 10 | 70 % | 63.3 % | +36.7 [21.7, 51.7] | 0 |

- pY range across permutations is 0 in every group.
- **Below the preregistered primary threshold** (≥ 10 mixed groups and ≥ 10 families) in both domains, so these are **descriptive**.
- No post-outcome replacement. 2D had 4 panel orders whose X was unresolved.
- p11 and pX1 give the same order ranking at a fixed endpoint, so they are not separate methods. The marginal-pX top order also executed on every complete panel group.

## Resource ledger

| Resource | Used | Approved |
|---|---|---|
| Training | 0 | 0 |
| GPU inference / analysis | under 0.5 GPU-h (parity, DEV scoring of 63,760 labelled sequences, 420 cohort streams, panel), RTX 5060 | 3 |
| New ordered teacher requests | 2D 400, 3D 400 (= X and Y factor calls each) | 400 per domain |
| Teacher CPU | 2D 1.06 h, 3D 2.98 h | 8 / 16 |
| Workers | 16, with ≥ 8 cores free | 16, ≥ 4 free |
| New disk | about 20 MB (`~/xyo_runs`) + about 1 MB in the repo; `/home` 1.5 GB free | 200 MB, ≥ 1 GB free |
| Protected TEST | not opened | – |
| K4/K5 study | not touched | – |

## Deviations (`AMENDMENTS.md`)

1. **2D certified negatives:** the strict mapping adds the two statuses `bxy_teacher` marks CERTIFIED.
2. **Primary-family bug, fixed before reporting:** an analysis bug briefly put Y − X into the Holm family. It was corrected to the four preregistered contrasts; no outcome changed.
3. **Extra module:** `stats.py` was added to the plan's file list.
4. **G arm not run:** the optional archived order-invariant G checkpoint for the panel was not used. The matched K3 G is on gvlab2; the laptop copies are older, unmatched fits.
5. **Draft table correction:** the draft's historical ablation figures (49.4 / 47.2 / 38.5) mix the V3.4 FULL rate with K3-ablation TEST deltas, and should be replaced with same-cohort numbers (P0_AUDIT).

## Commits

`a9bb0022ee` P0 / P1 tests · `8114a3dbf2` parity + DEV + seal + manifest (before teacher) · final commit: this report.
