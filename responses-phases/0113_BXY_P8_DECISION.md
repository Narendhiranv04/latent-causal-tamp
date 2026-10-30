# 0113 — Approach B X/Y, Phase 8: status and decision

**Overall verdict: PARTIAL.** The finalized X/Y Approach B is implemented, tested and runs end to end on the existing 2D dataset. The existing dataset cannot train or evaluate its X half.

## A. Phase verdicts

| Phase | Verdict | Report |
|---|---|---|
| 0 Starting state | PASS | 0106 |
| 1 Legacy LB baseline (also instruction 0106) | PASS | 0107 |
| 2 Data interface + collection plan | PARTIAL (no X = 1 in the data) | 0108 |
| 3 Mathematics | PASS | 0109 |
| 4 Neural implementation | PASS | 0109 |
| 5 Initial learning | PARTIAL (Y learned; X and w not identifiable) | 0110 |
| 6 Travel-aware selection | PARTIAL (implemented; legacy travel; degenerate) | 0111 |
| 7 Comparisons | PARTIAL (run as specified; X/Y arms equal NOOP) | 0112 |

## B. Decision (methodology §8.2)

1. **No benefit can be claimed for X/Y or for the coupling.**
   - XY-quadratic does not outperform XY-uncoupled; their selection is identical. Per the methodology, the coupling is not supported by this evidence.
   - This is not evidence against it either: X was never observed as 1.
2. **LB stays the operative B model on this dataset**, at 0.696 mean test selection success. It also has the better Y log loss.
3. **Neither learned arm beats the analytic SHORTEST_NONEMPTY rule** (0.824) on this catalogue. Any future B claim must beat that baseline as well as LB.
4. **The single blocking requirement is data.** To unblock X/Y, collect the sidecar plan **P-min** (0108 §D):
   - X with the terminal connector for the 1,114 catalogue candidates;
   - Y for the 593 unobserved candidate endpoints;
   - estimated at about 4 CPU-h of teacher time on the existing 231 scenes.

   It also yields matched travel J for the travel arm. **This has not been run: it needs your authorization.**
5. **K coverage remains thin** (K3/K4: 3 roots). That is a property of the interrupted generator run, not of B.

## C. Reproduction

```bash
python3 bxy_data.py                         # P0 manifest + BXY_SIDECAR_V1
python3 bxy_lb.py build                     # LB learner records (DINOv2 features)
python3 bxy_lb.py run {0,1,2}               # P1 LB seeds (val early stopping; test evaluated after selection)
python3 bxy_run.py train XY-quadratic 0 {0.1,0.3,1.0} XY-quadratic-lam{l}-s0   # P5 / P6 lambda_J grid
python3 bxy_run.py jobs | while read a s l; do python3 bxy_run.py train $a $s $l; done   # P7 remaining arms
python3 bxy_run.py freeze                   # validation-only rules -> FROZEN.json
python3 bxy_run.py final                    # the single test evaluation -> EVAL_P7.json
python3 -m pytest -q tests/test_bxy.py      # 15 tests
python3 bxy_viz.py {p0,p3,p1,p5,p7}
```

The dataset is read through `BXY_DATA`, which defaults to the local read-only snapshot. Its hash is `sha256:78ca0e7c35d5a2b937554c03ce38b06db2486e5d74af5f2831e37e335ccb1a38`.

## D. Artifacts

- **Code:** `bxy_data.py`, `bxy_lb.py`, `bxy_core.py`, `bxy_run.py`, `bxy_viz.py`, `tests/test_bxy.py`.
- **Untouched:** the historical P13–P17 code and checkpoints, `bd_*` generators, Approach D, 3D and retrieval code.
- **Run outputs:**
  - `runs/approach_b/bd2d_lb_v1/`: RECORDS, 3 LB checkpoints, EVAL / TRAIN_LOG / PREDICTIONS per seed;
  - `runs/approach_b/bxy/`: P0_MANIFEST, SIDECAR, 12 X/Y checkpoints with training logs, FROZEN, EVAL_P7, PREDICTIONS_P7_test.
- **Figures:** `visualizations/approach_b/bxy/P0_coverage.png`, `P1_LB.png`, `P3_math.png`, `P5_initial_learning.png`, `P7_comparison.png`.
