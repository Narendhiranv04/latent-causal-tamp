# R2.2 (2D): continuous vs chunked execution with verified q_ref returns

**Setup.**
- **Teacher:** BXY primitives. `x_chunked` places the teacher connector at every declared boundary.
- **Labels:** continuous labels are reused exactly from the pool. R1 parity holds (`x_chunked(bounds={m}) == x_query`), and **8/8 continuous re-verifications agree**.
- **Panel:** VAL sequences spread round-robin over N bins, one per root, sealed manifest `jobs_C_2d.json`.
- **Data:** `R2_phys_2d.json → connectors`. Figures: `figures/R2_2_connectors.png`, `R2_2_connector_trajectories.png` (actual certified records).

| Panel | Partition | Verified | Wilson 95 % | Failures |
|---|---|---|---|---|
| m = 2, continuous X = 1 (24) | (1,1) | 21/24 | [0.69, 0.96] | boundary:1 1, boundary:2 1 (UNKNOWN_TRANSIT); relocation:1 1 (UNKNOWN_PLANNER) |
| m = 3, continuous X = 1 (16) | (1,2) | 16/16 | [0.81, 1.00] | — |
| | (2,1) | 14/16 | [0.64, 0.97] | boundary:2 ×2 (UNKNOWN_TRANSIT) |
| | (1,1,1) | 15/16 | [0.72, 0.99] | boundary:2 (UNKNOWN_TRANSIT) |
| m = 2, continuous X = 0 at the terminal connector (8) | (1,1) | 2/8 | [0.07, 0.59] | 6 UNKNOWN_TRANSIT |

**Gate.**
- **Result:** pooled split rate on the matched positive panel **66/72 = 0.917 [0.83, 0.96]**, against a continuous rate of 1.0 (by selection, re-verified 8/8).
- **Decision: CONNECTOR_COMPATIBLE**, narrowly. The lower bound is below 0.9, and the threshold is an engineering gate, not proof.
- **Unknowns:** none certified. All 6 failures are UNKNOWN_TRANSIT / UNKNOWN_PLANNER under the fixed budget; they are never relabelled as impossible.

**Observations.**
- **Boundary failures also happen at the *final* boundary.** Example: (1,1) failed at boundary:2. After a home return, the next relocation from q_ref ends in a different configuration, and its own terminal connector can fail.
- **The split pattern matters:** (1,2) has the best record (16/16), (2,1) the worst (14/16).
- **Chunking rarely rescues** a sequence whose continuous connector failed (2/8).
- **Consequence for R1:** E_home preferring splits (R1 demo: 0.481 vs 0.587) is a model preference, not an execution probability. Each extra return costs about 0–12 percentage points here.
