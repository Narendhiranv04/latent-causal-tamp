# R7 freeze

The final clean models below were frozen by predefined VAL-only rules before any R8 outcome existed. The machine-readable records are `reports/final/r7/runs/freeze_{2d,3d}.json` and `reports/final/r8c_config*.json`.

| | 3D | 2D |
|---|---|---|
| X head (rule: R5.2 simplest-within-tolerance; lowest-VAL seed) | **G1, seed 2** (`3d_G1_hi_base_s2`), VAL family NLL .2017; sha256 de45d683… | **G1, seed 0** (`2d_G1_hi_base_s0`), .2180; sha256 ceefe0c1… |
| Seed-mean VAL (A / M / G) | .590 / .512 / .224; tolerance .048 | .424 / .330 / .228; tolerance .024 |
| Calibration (R5.3: adopt iff ΔVAL NLL ≥ .005) | T = 0.896, Δ = .0009, **not adopted** (raw X) | T = 0.845, Δ = .0021, **not adopted** (raw X) |
| Y (frozen stage-B D, same seed as the X head) | `xy/p2_3d/D_s2` | `xy/p2_2d/D_s0` |
| cVAE (lowest base-snapshot VAL ELBO) | `q2init_all_s1`, sha256 7c750edb… | `q2init_all_s0` |
| Spec | `R7:3d_G1_hi_base_s2` | `R7:2d_G1_hi_base_s0` |

**R8C 3D configuration.** This is the R6 3D configuration with only the models changed:
- raw X;
- S0 selection;
- admission A1 with m = 0.10;
- GA with S1 top-4 proposals;
- REC with ANC64 proposals;
- H = 5;
- a 180 s deadline that covers floor, proposals, search and selection.

One disclosed change: the K ≤ 3 floor now uses the final clean model (`R6_FLOOR=final`). R6 used production F0. B0 remains the production model, as its named baseline.

**Control.** The original-data-only GNN control is `R7:3d_G0_hi_base_s2` (same seed, base and cVAE). It is evaluated with REC and GA only.

**Development sanity check.** 20 exposed DEV roots, development only; these roots never enter the independent cohort.

| Arm | Successes / 20 | Of which long (4–5 actions) |
|---|---|---|
| B0 | 2 | — |
| H3 | 4 | — |
| FLAT | 9 | 7 |
| REC | 14 | 12 |
| GA | 10 | 9 |

R6 with the development models gave B0 2, H3 4, FLAT 6, REC 11, GA 12. No setting was changed after this check.
