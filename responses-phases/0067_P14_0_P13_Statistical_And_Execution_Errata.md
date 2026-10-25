# 0067 — P14-A0: P13 statistical and execution errata (versioned addendum; zero new physical labels)

**Previous turn sync:** P13 final `99bccf7cbc57feb6150d0d50062548af4d3eebe1`. Local equals origin/main at the start of P14; the only working-tree changes are the user's two deleted root PDFs (not staged).

**Actual result.**
- **Gate:** `runs/p14/P14_A0_GATE.json` → **PASS**.
- **Scope:** every correction is recomputed from frozen P13 artifacts (`runs/p14/audit/P13_ERRATA.json`, `KEYING_INVARIANCE.json`). All P10–P13 files and reports are unchanged; their SHA-256s are recorded in the errata JSON.
- **Cost:** 23 CPU-s (`a_correction`).

## 1. J contrast sign (0063 §2 and 0066 printed it wrong)

- **What went wrong:** the stored field `B_success_J_minus_noJ.mean_delta = −0.0185` was computed on *negated* success, so it is **no-J − J**.
- **Corrected J − no-J = +0.0185** [0.000, 0.041]. J's choice is right and no-J's wrong on 3 roots; the reverse happens on 0 roots (sign test p 0.25).
- **Rates:** J 0.836 vs no-J 0.818.
- **Endpoint:** this is **teacher-labelled choice correctness** (whether the chosen query is VERIFIED). It is not physically executed success, because the no-J choices were never executed.
- **Guard:** a regression test now pins the orientation (`test_j_contrast_sign_corrected`).

## 2. J travel regret

- **The historical numbers are oracle-filtered.** The 0063 regret figures (J 0.210, no-J 0.301, shuffled 0.236) first restrict the alternatives to teacher-VERIFIED candidates and only then choose by J. That is an oracle-filtered diagnostic, not deployed travel regret.
- **A deployable comparison on comparable selected choices** (K-B, 3 seeds, 507 choices):

  | outcome | choices |
  |---|---|
  | J and no-J pick the same query | 294 |
  | abstain | 184 |
  | both picks VERIFIED with witnessed travel | 23 |
  | different picks, not both VERIFIED | 6 |

- **On the 12 roots with both picks witnessed:** first-witness travel no-J − J = **+0.143** (J shorter) [−0.084, 0.458], 7 / 5 roots, p 0.77.
- **Nothing is imputed:** infeasible or unattempted choices have no travel.

## 3. Execution ledger reconciliation (0064)

- **What the final ledgers hold:** the eight final ledgers hold **428** unique episodes, with no duplicate identities:

  | outcome | episodes |
  |---|---|
  | SUCCESS | 301 |
  | NO_REPAIR_WITNESS | 52 |
  | censored | 34 |
  | target certified infeasible | 28 |
  | target unresolved | 13 |

- **Why 0064 differs:** 0064's histogram (295 / 51 / 7 NOT_RUN) was printed at 21:27 UTC. That was *before* the worker-2 continuation (guard at 21:28 UTC) ran the 7 never-attempted jobs, which produced 6 SUCCESS and 1 NO_REPAIR_WITNESS.
- **The per-arm numbers were already right:** `EXEC_RESULTS.json` was written at 21:36 UTC from the final ledgers, so per-arm success already used all 428 episodes; only the narrative histogram was stale.
- **Independent recomputation** (own code; abstain = failure): every per-arm success matches the reported values to 1e-16. **B 0.734 is correct.**

## 4. Admission versus conditional success (applies to the F2 / F4 / F5 / A / SF execution claims)

| arm | admission, all 129 roots (share of choices attempted) | success given attempt | root success (abstain = failure) | natural: admission / conditional / root |
|---|---|---|---|---|
| keyed B | **0.835** | 0.879 | **0.734** | 0.736 / 0.764 / 0.562 |
| B-F3pm | 0.835 | 0.848 | 0.708 | 0.792 / 0.789 / 0.625 |
| B-F4 | 0.605 | 0.868 | 0.525 | 0.597 / 0.756 / 0.451 |
| B-F5spm | 0.540 | **0.895** | 0.483 | 0.604 / 0.828 / 0.500 |
| A | 0.620 | **0.900** | 0.558 | 0.507 / 0.836 / 0.424 |
| C | 0.672 | 0.862 | 0.579 | 0.646 / 0.785 / 0.507 |
| SF | 0.346 | **0.918** | 0.318 | 0.340 / 0.857 / 0.292 |
| B-F2 | 0.341 | **0.917** | 0.313 | 0.396 / 0.860 / 0.340 |
| geometry | 1.000 | 0.612 | 0.612 | 1.000 / 0.625 / 0.625 |
| G+M | 1.000 | 0.783 | 0.783 | 1.000 / 0.646 / 0.646 |

- **Conditional on attempting a repair, every ablation and baseline is as accurate as B or more** (0.87–0.92 vs 0.88).
- **B's executed advantage over A / C / SF / B-F2 / B-F4 / B-F5spm is therefore an *admission* (coverage) effect:** with its validation-calibrated threshold, B attempts more roots.
- **Consequence:** the P13 deployment claims for F2, F4 and F5 and for B over A / C / SF are re-labelled **admission-entangled**, pending matched-coverage analysis (0068).

## 5. F3, F5, F4 wording

- **F3:**
  - the root-level sign test favours *removing* F3 (40 vs 22 roots; raw and Holm p 0.030);
  - the mean bootstrap CI crosses 0: −0.022 nats [−0.064, 0.015];
  - the magnitude is below the 0.05 threshold.
  - **Correct statement:** no demonstrated benefit. Mean harm is *not* established; only a directional root-count reversal is.
- **F5:** the primary ablation B-F5spm removes the **combined block, generic pairwise coupling plus the higher-order terms**.
  - Correct claim: *combined block* +0.175 nats on the challenge set, −1.14 on the natural mix.
  - **No generic-only claim exists**; generic-only was not tested.
- **F4:** admission 0.835 vs 0.605; conditional success 0.879 vs 0.868; root success 0.734 vs 0.525. The F4 execution gain is essentially admission.

## 6. Keying: correctness reference, not a likelihood contest

Frozen K-B and B-U checkpoints, 3 seeds, 40 multi-move test roots:

| catalogue change | keyed max \|ΔP\| | unkeyed max \|ΔP\| |
|---|---|---|
| exact duplicate re-listing (same query id) | 0 | 0 |
| reversed candidate order | 0 | 7e-15 |
| **query modelled only as an omission slot vs also listed as a candidate** | **8.5e-12** (102 cases) | **0.252** (mean 0.026; all 102 cases change) |

- **Keyed B** is invariant to how the catalogue lists a physical query; **unkeyed B is not**.
- **What 0063 reported:** unkeyed B's lower NLL. That is a prediction result. It does not support dropping the canonical one-variable-per-physical-query constraint.
- **Corrected keying verdict:** *keyed = correctness reference (catalogue invariance holds); predictive benefit not demonstrated.*

## 7. D: conditional versus feasibility-gated blocker inference

- **P13's 0.892 is conditional:** F1 on 119 roots whose original is *known* (truth) to be infeasible.
- **Feasibility-gated inference** (146 decided roots, 27 of them feasible originals; a predicted-feasible root yields an empty mask, and feasible roots have an empty true mask):

  | model | F1 | exact | exact on feasible originals |
  |---|---|---|---|
  | D | **0.903** | 0.886 | 0.951 |
  | D-pairless | 0.881 | 0.868 | 0.889 |
  | geometry heuristic | 0.719 | 0.610 | 0.259 |

  Geometry names blockers on feasible originals.
- **Limits:** the union of minimal sets is not universal necessity, and matched-lattice semantics are unchanged.

## 8. Compute ledger wording (P13 training)

| reading | CPU-s |
|---|---|
| raw guard sum (corrupted by the thread-parent RUSAGE bug; preserved) | 440,364 |
| upper bound min(guard, wall) | 33,624 (P13 reported 33,683, including 59 CPU-s of record-building jobs) |
| child-recorded `process_time` of completed runs | 24,705 |
| wall-clock upper bound for terminated runs | 8,517 |
| **best estimate** | **33,222** |

This is a **bounded estimate**, not an exact measurement. 0062's "corrected training spend 33,683" should be read as an upper bound.

## 9. Tests

`tests/test_p14.py` (5 / 5) covers:
- paired-difference orientation;
- J-sign correction;
- ledger recomputation equals 428 / 301;
- bounded-compute status;
- keyed omission invariance versus the unkeyed counter-example.
