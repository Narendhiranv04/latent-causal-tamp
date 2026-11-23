# P0 gaps and limits

1. **Scorer batch invariance is only approximate** (≤ 6.6e-7 in p11). Replay decisions are validated against live scoring on a predeclared timing subset; the mismatch count is reported.
2. **No proposal probabilities.** The frozen proposal API returns ranked destinations only, so `PUCT_RANK` would be a rank prior. It is a declared secondary arm and is **not run** in this phase.
3. **Hyperparameter grid boundary.** The DEV-tuned UCT exploration constant c = 0.1 is the smallest value in the predeclared grid {0.1, 0.3, 1.0}. The grid is not extended after seeing results.
4. **VAL has been used extensively** by earlier studies, so all VAL results here are development/validation evidence, not independent confirmation. The V3.4 fresh cohort is reserved and was not read. No new independent cohort is generated in this phase; that would need generator and teacher capacity and a separate decision.
5. **Physical verification runs on gvlab2**, where the teacher environment, the raw VAL roots and the K≤3 ablation harness live. The laptop has only 2.2 GB of free disk.
6. **K3 roots (134 in EVAL)** are excluded from all primary analyses. This is done evaluator-side, so the planner always runs with public K_max = 2.
7. **`evaluation_group_id` equals `root_id`** for all 751 VAL roots, so cluster bootstrap = root bootstrap.
