# 0099 — P17-5: final closure, 2D method verdicts and remaining limitations

**Verdicts**
- **METHOD_B_2D_COMPLETE** — technically complete. The scientific result is negative: production lean B does not beat ALWAYS_EMPTY, and VERIFY_FIRST dominates.
- **METHOD_D_2D_COMPLETE: not granted. D is PARTIAL / BLOCKED**, solely on mechanism gate M7. A verified repeat witness exists, but the required finite-domain necessity proof is blocked on 8 named roots. All other D gates pass. The scientific result is negative or underpowered: learned guidance shows no search advantage over geometric ordering.
- **P17_2D_COMPLETE: not granted**, because D is PARTIAL. Every mandatory test roster was executed: retrospective 48 / 48, and prospective labels / B / D / oracle at 174 / 174 / 90 / 56.
- **No 3D work was started.**

## 1. Stage gates

| stage | report | gate |
|---|---|---|
| P17-0 audit | 0090 | PASS: starting SHA `bd9a2e8`, historical blob manifest, 0 mismatches at the end of P17 |
| P17-1 physical correctness | 0091 | PASS: corrected dominance (0 mismatches vs exhaustive on 2,000 graphs), existential verifier, UNKNOWN / optimality semantics, determinism 5 × 3 under load |
| P17-2 shared domain | 0092 | PASS: scene-only 0–4-move domain, multiple slots, freed sources, repeats |
| P17-3 mechanisms | 0093 | **PARTIAL**: M0–M6, M8 (3 and 4 moves) and M9 realized with witness, counterfactual, PNG and replay GIF; M7 witness only |
| P17-B1 training | 0094 | PASS: 326 roots of existential labels, 8 arms × 3 seeds early-stopped, calibrated policies |
| P17-D1 diagnosis | 0095 | PASS with scope: per-family calibration; temporary blocker marginals not validated, so recursion is feasibility-only |
| P17-4 frozen test | 0096 | PASS: custody order satisfied, all rosters complete |
| P17-B2 evaluation | 0097 | complete (negative) |
| P17-D2 evaluation | 0098 | complete (negative / underpowered) |
| P17-5 closure | 0099 | this report |

## 2. What changed in P17

**Physics:**
- the search state carries the last mover in its key, so dominance is now sound;
- existential fixed-sequence verification replaces the P16 greedy verifier, with 46 P16 q-dependent labels corrected (erratum);
- certificate scope: only motion-independent certificates refute, and a q-dependent certificate refutes only its own branch (the empty sequence at q0 included);
- a finite library domain was added for scoped proofs.

**B:**
- one shared scene-only candidate domain;
- labels under `P17_EXISTENTIAL_V1`;
- early stopping;
- an exact fast scorer, equality-tested;
- matched retraining of LB, LB+G, LB-W, LB-F2, LC, A, SF and FULLB on one dataset;
- controls: inference-only coupling switched off, and swapped thresholds;
- VERIFY_FIRST and TOP-3 arms.

**D:**
- pairless Dp17 trained on `MULTI_DEST_LATTICE_V1` and `PARKING_LATTICE_V1` labels;
- per-family CV-selected calibration (this fixes the P16 shared-calibration defect);
- temporary-target lattices;
- recursion used for feasibility only.

## 3. Remaining 2D limitations (exact, not "another phase")

1. **M7 necessity.** No finite-domain proof exists on these 8 roots:
   - train p13_2026221033 and p13_2026222001;
   - p17train p13_2026270007, p13_2026271032 and p13_2026274003;
   - p17calib p13_2026280009 and p13_2026281010;
   - train p13_2026228002.

   On 5 of them a no-repeat plan exists in the library domain; on the other 3 neither class is decidable. Closing M7 needs either a repeat-requiring scene whose witness lies inside a finite adjudicable domain, or a refutation procedure for online-planned relocations. Neither is available from the current planner, which reports UNKNOWN when it fails.
2. **Temporary-target blocker marginals are unvalidated.** Only 6 masks exist, so `-blk` stays experimental.
3. **Proposal recall.** B's capped catalogue holds 10–33 % of certified solutions, and B never sees most long repairs.
4. **Budget censoring.** 19–24 of 90 prospective D roots and about 9 of 48 retrospective roots end with NO_PLAN_FOUND, which is not proven infeasibility. 34 / 174 prospective originals are UNKNOWN.
5. **Power.** Every D contrast vs geometry has ≤ 6 discordant roots and is labelled UNDERPOWERED, never equivalence.

## 4. Regression

The run is guarded (`runs/p17/regression_final/`):
- all historical tests;
- the 6 historical replays: g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit, each exiting 0;
- `tests/test_p16.py` + `tests/test_p17.py`: 45 passed, including 2 new custody / alias tests.

**Result:** the full suite in `runs/p17/regression_final/` passed 500 tests with 0 failures; the baseline before P17 was 474. All 6 replays are CLEAR, and the verdict is `P3A_REGRESSION_CLOSED`. The totals are also recorded in `runs/p17/P17_FINAL_MANIFEST.json → regression`.
