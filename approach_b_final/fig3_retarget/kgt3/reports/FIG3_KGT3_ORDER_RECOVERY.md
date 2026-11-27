# FIG3_KGT3 P3 — physical order recovery given the assignment: NOT RUN

**Status:** not run in either domain. The pre-registration makes P3 conditional on a passed fresh local gate (P2_GATE = PASS) in that domain. Both domains recorded P2_GATE = DATA_LIMITED (`p2/gate_2d.json`, `p2/gate_3d.json`, bound by `guard.decide`).

**Enforcement.** The harness `../p3.py` (`plan` and `jobs`) calls `guard.authorize(gate_DOM.json, "P2_GATE", "PASS")` before any planning or dispatch. It would raise `NotAuthorized` on the current decisions.

**Cost.** No P3 teacher job, plan or seal was produced, and none of the 150 (2D) / 100 (3D) job reserve was spent.

**Related evidence** (exposed panels, diagnostic only; `FIG3_KGT3_COMPOSITION_AUDIT.md`):

| Item | Result |
|---|---|
| Archived 2D R3.4D learned order | 3/30 |
| Archived 2D privileged witness under the same protocol | 29/30 |
| Archived 3D R2.4 A-DP | 2/20 |
| Quarantined A2 G1s order runs (DIAGNOSTIC_ONLY, 18 of 20 roots run) | 9 verified |
| Witness-order rank quantile under the KGT3 objective | 2D F0 0.82; 3D F0 0.33, G1s 0.21, M1s 0.17 |

None of this is a P3 result.
