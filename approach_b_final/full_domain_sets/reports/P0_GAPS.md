# P0 gaps, blockers and caveats

1. **No lineage-disjoint fresh 2D evaluation cohort is available without new generation.**
   - The only fresh 2D cohort on this machine (`~/abf_v34/cohort`, V3.4) is **protected** and was not opened. `release_v2` TEST was not accessed.
   - Generating a new cohort needs the unchanged root generator plus teacher labelling (about 100 teacher-CPU-s per root in the historical records). That is outside the plan's proposed query ceiling and was not authorized.
   - **Consequence:** any physical evidence from this study is a **development-only VAL pilot**, on the same 600 EVAL roots the completed study used, with tuning on the same 151 DEV roots. **No independent generalization claim is possible.**
2. **Teacher authorization.**
   - The plan says the 1,200-query / 24 CPU-h ceiling is *not* inherited from the completed study and needs explicit owner and host authorization.
   - Until that is given, P3 stops at a sealed, executable manifest.
3. **`BEYOND6_NOT_IN_MC_DRAW` is not identifiable.**
   - S1 averages softmaxes over 64 latent draws, so every legal cell has positive mass (0 zero-mass actions on VAL). The stratum degenerates to `BEYOND6`.
4. **There are two witness sources.**
   - **Exact-contract teacher caches** (`evaluate._verify_job`: K≤3 ablation, post-ablation validation and the completed MCTS study) are the primary source.
   - **Generator labels** (`labels.B`, protocol `BD2D_TEACHER_V1:DetPhysics(P16_FAST,no-library)`, generator budgets) are a secondary source, reported separately.
   - They agree on all 78 overlapping (root, sequence) pairs, with 0 decided conflicts.
5. **Label semantics on NONE roots.** Some NONE-stratum VAL roots carry verified K≤2 successes in both sources (for example, 30 cache TOP4 witnesses). This study treats K strata only as evaluator-side labels, exactly as before, and draws no conclusion from it.
6. **Operational vs strict UNKNOWN.**
   - The frozen 2D evaluator counts `UNKNOWN_*` with value 0 as a failure (operational).
   - This study's **primary** physical accounting is **strict** (UNKNOWN is unresolved), as the plan requires. The operational numbers are shown separately, for parity with the completed study.
7. **Disk.** About 2 GB is free on the laptop's `/home`. Full-domain score tables are therefore never written to disk; they exist in RAM for one root at a time.
