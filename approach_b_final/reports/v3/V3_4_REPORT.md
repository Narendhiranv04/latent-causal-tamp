# V3-4: candidate-matched physical X/Y evidence (TRAIN roots only)

**Purpose (plan §5.5).** Label the candidate distribution the deployed method actually produces, so that the coupled scorer can be retrained on it in V3-5:
- the chosen generator: task cVAE `q2init_all`, S1, M = 4;
- direct construction with B = 4,096;
- scored by the frozen V2 D.

## Protocol

- **Roots.** TRAIN only, stratified by legacy class, in sha256 order:
  - 2D: 120 each of K1 / K2 / K3, plus 40 K0 and 60 NONE (460 roots);
  - 3D: 70 each of K1 / K2 / K3, plus 25 K0 and 40 NONE (275 roots).
  - K0 and NONE roots are included, unlike V2, because their false positives drive no-op and abstention errors.
- **Sequences per root.** Seeded and label-blind:
  - the top-2 by V2 p11;
  - one each from [0.3, 0.9), [0.1, 0.3) and < 0.1;
  - one uniformly random candidate;
  - every constructed order of the selected repair's assignment (same-endpoint order contrasts).
- **Teachers.** The unchanged finalized teachers (`evaluate._verify_job` semantics):
  - Y is queried once per endpoint;
  - X is queried where Y = 1, and where Y = 0 for a seeded third of the items, so the X | Y = 0 factor keeps observations;
  - unqueried X stays **missing** and is marginalised, never set to 0.
- **Hosts.** Deterministic root sharding (`V3_PART`) across gvlab2 and the laptop, whose parity was exact. 3D shares were moved between hosts mid-run and resumed by root, with no duplicate root.
- **Snapshot.** `abf_v3_e8a496bc66266fca` (lock in `v3_4/v3_snapshot.lock.json`):
  - it is the V2 snapshot plus these labels, on TRAIN rows only; validation and test rows are byte-identical;
  - every label coinciding with an existing observation agreed (asserted);
  - added: 2D 2,326 Y / 1,587 X and 3D 1,423 Y / 1,625 X;
  - every queried label was decided (0 missing); 1,633 2D and 562 3D X were deliberately not queried (Y = 0).

## What the labels show (`v3_4/V3_4_LABEL_ANALYSIS.json`)

The table compares the frozen V2 scorer's predictions with the physical outcomes on the deployed candidate distribution.

| | 2D | 3D |
|---|---:|---:|
| Labelled sequences (Z decided) | 3,234 | 2,224 |
| Physical success rate Z | 19.4 % | 37.5 % |
| Mean V2 p11 | 0.59 | 0.53 |
| ECE of the V2 scorer | **0.40** | 0.17 |
| Z rate when V2 p11 ≥ 0.9 | 43.7 % | 72.5 % |
| Z rate of the top-2 by p11 (mean p11) | 32.9 % (0.83) | 63.2 % (0.86) |
| Roots with ≥ 1 verified success, K1 / K2 / K3 | 107 / 80 / 15 of 120 each | 67 / 67 / 64 of 70 each |
| Legacy-NONE roots with a verified success | 0 / 60 | 0 / 40 |

Interpretation:
- **The V2 scorer is strongly overconfident on repair-like candidates**, especially in 2D. This quantitatively confirms the covariate shift diagnosed in V3-3.
- 2D K3 remains hard even with the task cVAE: only 2.8 % of K3 candidates succeed, and only 15 / 120 roots have any success among the labelled candidates.
- No new repairs were found on legacy-NONE roots. Under this finite budget that is consistent with the old labels, though not a proof of impossibility.
