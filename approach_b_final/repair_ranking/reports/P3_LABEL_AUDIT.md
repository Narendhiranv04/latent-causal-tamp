# P3: targeted TRAIN intervention labels

**Gate: PASS.** 1,743 TRAIN roots now have both a decided Z+ and Z− (threshold 100), and 281 roots have newly decided rank > 6 candidates (threshold 50).

The manifest and pre-registration were sealed and pushed (`dad6de566c`) before any teacher call. Counts are in `P3_COUNTS.json`.

## Execution ledger

| Item | Value |
|---|---|
| Host / harness | gvlab2, unchanged `benchmark.teach` → `evaluate._verify_job` (k3abl env, code and mirror read-only); 32 workers on cores 8–39 (16 cores left free) |
| Wall time | 2026-11-25 04:40:56Z to about 05:13Z; the process tree was killed by PID at 05:12Z |
| Queries | **1,794 answered** on 359 roots (cap 1,800). 6 queries on 1 root (`2d-conv-plus2d-w0007-s013`) were interrupted, not retried, and are ledgered as missing. |
| Teacher worker CPU | **12.03 h** (cap 12 h). The cap was reached while parallel work was in flight, so the run was stopped at once, leaving a **0.03 h overrun**. No other allocation was used. |
| CPU per query | about 24 s, against about 13 s on VAL in the completed study. TRAIN K1/K2 roots are harder for the planner. |
| Raw outputs | private: `~/xyrr_private/p3_cache/verify_2d.jsonl` (sha256 `192d624c…`), plus the gvlab2 copy |

## Teacher outcomes (per ordered query)

| | VERIFIED | CERTIFIED_INFEASIBLE | UNKNOWN |
|---|---|---|---|
| X | 1,386 | 121 | 287 (planner 178, transit 108, q_ref 1) |
| Y | 1,126 | 203 | 465 (planner) |

## Merge (strict, exact keys)

- **Added:** 1,507 X nodes and 1,116 endpoint Y nodes.
- **Existing endpoints:** 213 already had a Y label in the original snapshot, and all **213 agree**. No conflicts, 0 quarantined.
- **Logical Z:** 909 = 1, 313 = 0, 572 unresolved (missing, never negative).
- **Augmented snapshot:** sha256 `9870819c…`. The original is unchanged (`963c16b2…`), and VAL and TEST rows are byte-identical.

| Category | Z = 1 / Z = 0 / unresolved | Decided success |
|---|---|---|
| HIGHCONF (frozen-model top unlabelled sets) | 370 / 71 / 97 | 84 % |
| DEST (anchor with one destination moved to rank 5–6, 7–12 or >12) | 351 / 27 / 71 | **93 %** |
| OBJSET (omission, substitution, addition) | 45 / 97 / 217 | 32 % |
| ORDER (other order, same endpoint) | 117 / 53 / 99 | 69 % |
| RANDOM (uniform legal) | 26 / 65 / 88 | 29 % |

| Worst cVAE rank | Z = 1 / Z = 0 | Decided success |
|---|---|---|
| 1–4 | 134 / 82 | 62 % |
| 5–6 | 361 / 36 | 91 % |
| 7–12 | 283 / 89 | 76 % |
| >12 | 131 / 106 | 55 % |

## Readings (descriptive; TRAIN, not evaluation)

- **On TRAIN, moving one destination of a verified repair off the top-4, even to the tail, usually keeps it valid (93 %).** Many destinations are interchangeable, so the binding errors are not destination choice per se.
- **Score-independent random sets succeed 29 % of the time,** far below the model's high-confidence picks (84 %). On TRAIN the scorer clearly carries signal.
- **Changing the object set is the hard contrast:** omission and substitution succeed only 32 % of the time.
- **Selection effect:** these new labels come from roots where the old model was trained, so TRAIN-side success rates are not evidence of VAL generalization.
