# R2.3 (3D): controlled search attribution on the 20 exposed K4/K5 development roots

**Status of this evidence:** development only. These roots were exposed in the K45 study, so nothing here is confirmation.

**Setup.**
- **Planner inputs:** PUBLIC rows plus the frozen bundle only. Caches are reset per root × arm.
- **Arms:** B0, R-FIG3, R-FIG3-ALL, R-FIG3-RP, R-GATED, F-FLAT, R-TOPO, all sharing **one CFG**: m_max 5, 96 expansions, 256 temporary readouts, 100k unique readouts, 180 s.
- **Ceilings:** realized counters are logged and no arm hit a cap.
- **Physical outcomes:**
  - 18 unique plans reuse exact archived K45 labels (same run_xb mode and bounds);
  - **36 new presealed teacher jobs** (`jobs_S_3d.json`, sha256 `843d4547…`), selected in fixed arm priority;
  - 29 lower-priority unique plans are **NOT_RUN (budget)**: the 3D cap of 120 jobs is exhausted. R-FIG3, F-FLAT and B0 are **fully decided** (20/20 each).
- **Data:** `R2_3_3d.json`. Figure: `figures/R2_3_search_funnel.png`.

| Arm | Verified X=1, Y=1 | Decided | Mean length | Mean q_ready returns | Failure modes | Median latency |
|---|---|---|---|---|---|---|
| R-FIG3 | **5/20** | 20 | 4.1 | 2.2 | X0Y1 at relocation 14, X0Y1 reused 1 | 1.41 s |
| F-FLAT | **7/20** | 20 | 4.15 | 2.4 | X0Y1 at relocation 12, X0Y0 1 | 1.04 s |
| B0 (released K≤3) | 2/20 | 20 | 2.9 | 0 | X0Y0 6, X0Y1 7, X1Y0 2 | 0.15 s |
| R-GATED | 4/20 (13 decided) | 13 | 4.15 | 2.6 | X0Y1 9 | 0.96 s |
| R-FIG3-ALL | 4/20 (13 decided) | 13 | 4.1 | 2.45 | X0Y1 9 | 1.67 s |
| R-FIG3-RP | 5/20 (12 decided) | 12 | 4.1 | 2.45 | X0Y1 7 | 1.48 s |
| R-TOPO | 2/20 (10 decided) | 10 | 4.1 | 1.9 | X0Y1 8 | 4.61 s |

**Paired comparisons (decided pairs):**

| Comparison | Only the first verified | Only the second verified | Both verified |
|---|---|---|---|
| R-FIG3 vs F-FLAT | 0 | 2 | 5 |
| R-FIG3 vs B0 | 3 | 0 | 2 |
| R-FIG3-ALL / RP / TOPO vs R-FIG3 | 0 | 0 | — (no discordant decided pair) |

All counts are below the 10 mixed-family minimum, so **no contrast is established**.

## Funnel (first stage at which the generator witness's action set is lost)

| Arm | Witness ingredients in D4 at S0 | In any proposal | Lost: never proposed | Lost: proposed but not composed into one candidate | Kept to final |
|---|---|---|---|---|---|
| B0 | 51 % | 55 % | 18 | 2 | 0 |
| F-FLAT | 51 % | 76 % | 13 | 7 | 0 |
| R-FIG3 | 51 % | **83 %** | 8 | **12** | 0 |
| R-FIG3-ALL | 51 % | **86 %** | 6 | **14** | 0 |

The witness is one valid plan, not the only one. The verified successes are non-witness plans.

## Findings

- **Established (development panel):**
  - Retargeting every action **raises proposal recall** of the witness's actions from 51 % (S0) to 83–86 %, against 76 % flat.
  - **No arm composes the complete witness set.** The binding loss is the **composition / ranking stage**.
  - Among composed long plans, **every R-FIG3 failure has a feasible endpoint (Y = 1)**; 14 of the 15 fail at a *relocation* (one is an archived X = 0). The selected order or placement is not executable.
  - Combined with R2.1 (direct m = 4/5 p11 AUROC 0.55) and R2.2 (connectors 0.92), this places the 3D >K3 bottleneck in **X / executability of composed sequences, ranked by an energy that cannot see it**. Y, object count and connectors are not the binding limits.
- **Not established:**
  - R-FIG3 > F-FLAT (point estimate reversed: 5 vs 7);
  - any benefit from admit-all, from recompute-parent, or from topological reordering.
- **Hypothesis:** a composition step that searches over the union of retargeted proposals for **executable orders** would convert the 83 % recall into more verified plans. This needs an executability signal beyond the frozen pX (R2.1: pX vs X at m = 4/5 is 0.60).
