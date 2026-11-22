# P7AR decision: **BLOCKED_FROZEN_KGT3**

**Evidence.** The cohort is a frozen, pre-registered set of 24 new independent development roots (K4/K5/K6 × 8, release-disjoint by construction). There was one evaluator run, on predictions sealed with SHA `05d48ebccd3c856b…`.

| Gate condition (pre-registered) | Required | Observed |
|---|---|---|
| FULL-R net vs FLAT-STRONG (primary: committed plan static-valid) | ≥ +3 | 0 (0 wins / 0 losses) |
| FULL-R net vs RANDOM-MATCHED | ≥ +3 | 0 |
| FULL-R net vs ORIG | ≥ +3 | 0 |
| FULL-R net vs DEST_ONLY | ≥ +3 | 0 |
| Roots with a novel enabler and a static-valid committed plan | ≥ 2 | 0 |

**Every arm committed 0/24 statically valid plans.** FULL-R now selects novel enabling movers (11/24 roots), but they do not produce valid plans. Its access proxy does not track the static grasp screens: committed plans fail mostly at a pickup (18/24), and random proposals yield more reorderable assignments (14 vs 5).

**Meaning.** This closes the frozen-model, training-free K>3 repair line under its pre-registered terms. It is **not** evidence that K4–K6 or K>3 tasks are unsolvable. It describes this finite candidate pipeline: frozen P4 anchors plus hand-designed public repair. There is no physical result (no teacher call), and static validity is only a necessary screen.

**Not done:** no further heuristic revision, P7B, physical evaluation, training, release_v2 access or merge.

**Possible directions, each requiring a new owner decision; not recommended or started here:**
- learned access or blocking models trained on TRAIN-only labels (out of scope for "frozen, training-free");
- a planner with a sound public collision and grasp model;
- reporting the line as a negative result.

**STOP.** Authorization is required before any physical evaluation or new line of work.
