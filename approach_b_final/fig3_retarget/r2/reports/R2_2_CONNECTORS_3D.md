# R2.2 (3D): continuous vs chunked execution with verified q_ready returns

**Setup.**
- **Teacher:** SHELF66V3 with CONNECTOR_TO_QREADY_V1 (planned, executed, |dq| ≤ 0.02).
- **K4/K5 cohort:** the continuous witness order verified by generation, and the [2, m] split reused exactly from `eval_oracle` (`oracle_witness_boundary`). The **all-singleton** partition is new (20 jobs).
- **VAL m = 3:** 4 sequences × every split, plus a continuous re-verification.
- **Data:** `R2_phys_3d.json → connectors`. Figures: `figures/R2_2_connectors.png`, `R2_2_connector_trajectories.png` (actual MuJoCo-executed witnesses).

| Panel | Partition | Returns to q_ready | Verified | Wilson 95 % | Failures |
|---|---|---|---|---|---|
| K4 witness (10) | continuous | 1 (terminal) | 10/10 (generation) | | |
| | [2, 4] (archived) | 2 | 10/10 | [0.72, 1.00] | |
| | singletons | 4 | 8/10 | [0.49, 0.94] | CONNECTOR_NO_PLAN at boundary:2 and boundary:3 |
| K5 witness (10) | continuous | 1 | 10/10 | | |
| | [2, 5] (archived) | 2 | 9/9 (1 not archived) | [0.70, 1.00] | |
| | singletons | 5 | 8/10 | [0.49, 0.94] | EXECUTION_NOT_VERIFIED at relocation:2 and relocation:3 (the move from q_ready fails) |
| VAL m = 3 (4) | (1,2), (2,1), (1,1,1) | 2–3 | 12/12 | | |
| | continuous re-verify | 1 | 4/4 | | |

**Gate.**
- **Result:** pooled split rate **47/51 = 0.922 [0.815, 0.969]**.
- **Decision: CONNECTOR_COMPATIBLE**, narrowly. The lower bound is below 0.9.

**Observations.**
- **Failure rises with the number of returns:**
  - one intermediate return: 19/19;
  - three or four intermediate returns: 16/20.
- **Two failure modes:**
  1. no collision-free connector plan within budget;
  2. a relocation that worked from the carried arm state fails when restarted from q_ready.

  Both are legitimate consequences of the connector mode, and they are labelled as such.
- **Consequence:** prefer partitions with **few, long (≤ 3) chunks**. The R1 DP's tie-breaking already favours fewer chunks only when energies tie, so R2.3 reports the realized number of returns.
