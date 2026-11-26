# Frozen short-horizon composition in 3D: K4/K5 pilot

`plan.md` (v1.0) and `starting_prompt.md` are the controlling contract. The verdict is in `reports/P5_FINAL_DECISION.md`:
- **COMPOSITION_WITNESSED** and **RETARGETING_WITNESSED** (1 root).
- No superiority claim.
- B0 (EXACT4 K ≤ 3) stays the released method.

| File | Role |
|---|---|
| `scene.py` | Public 3D rows: rebase, retarget (ctx slots derived from q_ref), global grammar, two-group splits |
| `models.py` | Frozen 3D bundle readouts: `propose_many` top-4, coefficient-level pY / pX1 / pX0 / marginal pX / p11, Y-only `Y_global`; counted and cached |
| `compose.py` | B0, B1, B2, B3, chunk score H, frozen selector |
| `recursive.py` | B4: bounded Fig. 3(a) retarget + insert, dependency-respecting ranking |
| `run.py` | Planner-only inference (`parity`, `predict`) |
| `generate.py` | Evaluator-only: instrumented route + chain construction, re-certification, derivation, two-host item dispatcher, roster assembly |
| `evaluate_k45.py` | Evaluator-only: continuous / chunked q_ref physical adapter on the unchanged teacher, replay, dispatcher, outcomes, statistics |
| `oracle.py` | P4b oracle-assignment ordering diagnostic (after the seal) |
| `viz.py` | Shelf grids and block views from real geometry |
| `tests/test_k45.py` | 14 contract tests |

**Reports, in order:**
1. `P0_AUDIT.md`
2. `P1_COHORT.md` and `P1_COHORT_SEAL.json`
3. `P2_TESTS.md` and `P2_ADAPTER_SMOKE.json`
4. `P3_PREREG.md` / `.json`, `P3_SEAL.json`, `P3_PREDICTIONS.jsonl.gz`
5. `P4_PHYSICAL.md` / `.json` and `P4_ATTRIBUTION.json`
6. `P5_FINAL_DECISION.md`

Figures are in `reports/figures/`.
