# 0037 — P10-0: validation readiness, matched A / B / C / SF training, and the pre-registered protocol

**Actual result.**
- **Engineering gate:** `runs/p10/P10_0_GATE.json` → **PASS** (8/8 checks).
- **Audit:** passed. The frozen `ABC9K_KEYED_V1` checkpoint (`K-B-full#s1`) replays its stored validation root NLL exactly (0.2552811945133491).
- **Training:** all 12 planned 400-update runs completed: keyed B-full, keyed C-full, A and SF × 3 seeds. Learner spend was **3,294.9 / 4,000 CPU-s**.
- **Regression:** the historical regression reproduced **392 / 392 tests and 6 / 6 replays**. It is charged separately (633.3 CPU-s), and its fixture planner calls are itemized below.
- **Scientific reading (validation only, 6 independent lineages):**
  - Keyed B-full beats A by a large margin (−0.80 NLL [−1.52, −0.20]) and beats SF (−0.22 [−0.39, −0.06]). Both contrasts are sign-stable under leave-one-out.
  - Keyed C-full is **not** distinguishable from keyed B-full (+0.028 [−0.013, +0.070]).
  - These are in-distribution P8c validation numbers. §5 and report 0038 show they did **not** carry over to the P10a roots.

Previous turn sync: `37cd2b7b84ce4666f93b13f31db331ae96a3e457`. Intermediate freeze commit (pushed before any P10a teacher call): `3afa81c2f8804fc1a8d11e08e2b3f010286fc784`.

## 1. Audit (`runs/p10/p10_0/audit.json`, non-mutating)

- **Repository:** HEAD = origin = `37cd2b7`. The only tracked changes were the two pre-existing user PDF deletions (never staged).
- **Hashes:**
  - freeze manifest hash OK;
  - all 11 frozen source files match;
  - P8c datasets (dev / sealed) OK;
  - 24 local P9 checkpoints OK;
  - the frozen checkpoint is committed and its hash matches.
- **Canonical identity:** 214 / 214 roots pass `check_identity`.
- **Keyed patch:** `unique_factor_keyed.installed()` restores `uf.instances` after an injected exception.
- **Static veto** (deployable TOP1 step: pure disc geometry, `proposals.static_endpoints` + `goal_blockers`, no robot) makes **0** physical calls on the validation roots and vetoes nothing there.
- **Call counter:** I wrote a precise one (`p10_protocol.instrument`) because `p9_l3c.instrument` would also count `motion._band` and FK helpers. It wraps the planner, skill, ordered, verify, evaluate, sector and teacher modules, plus IK / collision / checker constructors.

## 2. Pre-registration (`runs/p10/p10_0/P10_0_PREREG.json`, hashed before training and before any P10a outcome)

- **Unit of analysis:** the independent reference root, i.e. the constructor seed / lineage. Orders, omissions, edits and `_ref` variants of one root are never independent replicates.
- **Statuses:** VERIFIED (1), CERTIFIED (0, pick-side only, no place-side certificate) and BUDGET (operational 0, never a proof). UNKNOWN and NOT_RUN are missing.
- **Strata:** proof-grounded (all components VERIFIED or CERTIFIED), operational (≥ 1 BUDGET), undecided (excluded but counted).
- **Interaction contrast:** κ = y(A+B) − y(A) − y(B) + y(0). The predicted κ̂ uses **root-prior** marginals only.
- **Primary endpoints:**

  | hypothesis | endpoint | primary contrast |
  |---|---|---|
  | H1 | \|κ̂ − κ\| on proof-grounded complete tuples | B-keyed vs A |
  | H3 | paired order choice on proof-grounded pairs | C-keyed vs B-keyed |
  | H4 | omission-necessity accuracy | B-keyed vs SF |

  Everything else is exploratory.
- **Statistics:**
  - root-cluster bootstrap (2,000 resamples, seed 0);
  - exact binomial test on discordant roots;
  - **UNDERPOWERED** if fewer than 5 decided independent roots;
  - no equivalence claims.
- **Calibration:** τ and admission threshold are chosen per checkpoint on the 12 P8c validation roots and frozen. They are never refit on P10a or on the disclosed test.
- **Splits:** P8c 178 train / 12 validation; 24 disclosed test (descriptive only); P10a = 14 **ADAPTIVE** constructibility roots (never a blind holdout).
- **P10d protocols** (not run): TOP1_COMMIT is primary; TOP5_PRECOMMIT is secondary and planner-assisted.

## 3. Training protocol (`P10_0_TRAIN_PLAN.json`, `sha256` in every run record)

| item | value |
|---|---|
| data | P8c learner view, unchanged |
| schedule | `abc8.RootSampler(train, 12, seed)`, AdamW 1e-3 / 1e-4, clip 10, 400 updates; best validation own-likelihood NLL every 20 updates |
| keyed B / C objective | exact root NLL under `P_K` + static BCE + witnessed-J log-Huber (unchanged) |
| A / SF objective | the documented factorized objective (sum of Bernoulli log-losses + static + J). **Not a joint NLL** |
| job order rule | priority 1 = keyed B and C (6 jobs); A (3) and SF (3) only while ≥ 450 learner CPU-s remain. All 12 ran |

## 4. Results — validation (12 P8c roots = 6 lineages); disclosed test descriptive

| run | val own NLL | repair acc | repair ECE | scene NLL | κ macro MAE | TOP1 success / VERIFIED-exists | abstain | test NLL (descr.) | CPU-s |
|---|---|---|---|---|---|---|---|---|---|
| K-B-full s0 | 0.041 | 1.000 | 0.000 | 0.014 | 0.061 | 4 / 4 | 0 | 1.25 | 368 |
| K-B-full s1 | 0.052 | 1.000 | 0.000 | 0.004 | 0.018 | 4 / 4 | 0 | 0.78 | 343 |
| K-B-full s2 | 0.045 | 1.000 | 0.000 | 0.021 | 0.063 | 4 / 4 | 0 | 1.32 | 352 |
| K-C-full s0 | 0.071 | 1.000 | 0.000 | 0.026 | 0.125 | 4 / 4 | 0 | 1.41 | 363 |
| K-C-full s1 | 0.040 | 1.000 | 0.000 | 0.003 | 0.011 | 3 / 4 | 0 | 1.12 | 357 |
| K-C-full s2 | 0.069 | 1.000 | 0.000 | 0.021 | 0.101 | 4 / 4 | 0 | 0.80 | 359 |
| A s0 | 0.516 | 0.941 | 0.050 | 0.199 | 0.473 | 4 / 4 | 0 | 2.44 | 194 |
| A s1 | 0.470 | 0.971 | 0.039 | 0.194 | 0.517 | 3 / 4 | 0 | 2.27 | 195 |
| A s2 | 0.351 | 0.971 | 0.027 | 0.116 | 0.318 | 3 / 4 | 0 | 2.33 | 202 |
| SF s0 | 0.161 | 1.000 | 0.006 | 0.036 | 0.122 | 3 / 4 | 0 | 1.43 | 178 |
| SF s1 | 0.160 | 0.971 | 0.017 | 0.020 | 0.088 | 4 / 4 | 0 | 1.72 | 169 |
| SF s2 | 0.143 | 1.000 | 0.001 | 0.025 | 0.093 | 3 / 4 | 1 | 1.71 | 177 |

**Paired per-lineage contrasts** (NLL of the *same* observed bits; seed-mean; 6 lineages):

| contrast | mean | 95 % CI | LORO range | sign-stable |
|---|---|---|---|---|
| K-B-full − A | −0.800 | [−1.518, −0.203] | [−0.952, −0.474] | yes |
| K-B-full − SF | −0.217 | [−0.389, −0.064] | [−0.257, −0.150] | yes |
| K-C-full − K-B-full | +0.028 | [−0.013, +0.070] | [+0.012, +0.045] | yes (CI includes 0) |
| K-C-full − A | −0.772 | [−1.480, −0.197] | [−0.918, −0.456] | yes |

**Reading.**
- On this in-distribution validation set, the joint keyed models fit the observed bits far better than factorized A and SF, and fully calibrated repair prediction is reached by every keyed run.
- Two warnings were already visible here:
  - **Disclosed test** (descriptive): keyed 0.78–1.41 vs SF 1.43–1.72 vs A 2.27–2.44. The ordering is the same, but every arm loses an order of magnitude.
  - **Small effective n:** only 6 lineages, and the three largest differences carry most of the mass.
- C (GRU order) shows **no** advantage over B (prefix / predecessor). These saved data contain no decided same-endpoint order pairs (0036 §4), so this was expected to be uninformative for H3.

## 5. What P10a then showed (cross-reference)

On the 14 adaptive P10a roots, with predictions frozen before any outcome (report 0038), the ranking **reverses**. Per-root NLL on decided outcomes:

| contrast | mean | 95 % CI |
|---|---|---|
| K-B − A | +0.52 | [+0.07, +1.04] |
| K-B − SF | +0.52 | [+0.07, +1.04] |

Validation fit of the joint models did not transfer to new mechanism geometry. This is exploratory (adaptive roots), but it is the most important P10 finding so far.

## 6. Gate and compute

`runs/p10/P10_0_GATE.json` → **PASS**. Every check passed:
- audit;
- pre-registration before training (plan hash in all 12 runs);
- priority 1 complete;
- A trained under its documented objective;
- no non-finite loss;
- learner cap;
- per-job caps (≤ 1,800 CPU-s, ≤ 3,600 s);
- aggregate wall ≤ 10,000 s.

**Compute ledger** (`runs/p10/guards/`, one record per guarded job, including failures):

| category | CPU-s | wall s | jobs | notes |
|---|---|---|---|---|
| learner | 3,294.9 | 3,297.6 | 14 | 12 training runs, audit and pre-registration |
| regression (declared fixtures) | 633.3 | 637.9 | 1 | see below |

**Regression fixture calls:** pytest 392 passed, 0 failed (`runs/p10/p10_0/regression/`). The fixtures made **621 `planner.plan`** and **60 `skill.plan_skill`** calls:

| test file | `planner.plan` | `skill.plan_skill` |
|---|---|---|
| `test_arm2d` | 75 | 3 |
| `test_g4a` | 198 | 22 |
| `test_g4d` | 24 | 4 |
| `test_g4d_corrections` | 40 | 4 |
| `test_interventions` | 37 | 1 |
| `test_protocol` | 104 | 14 |
| `test_verify` | 143 | 12 |

These are test fixtures, never learned scoring. All six replays passed (`g1_hardening`, `g1_robot`, `g2_interventions`, `g3_5_initial_scene`, `g3_repairs`, `g4a_evidence_audit`).

There were **0** IK, collision or planner calls in any learned path. The P10a prediction counter is recorded in `predictions.json`.

**Disclosures:**
- After the plan hash, `p10_protocol.py` gained the summary, regression and figure-ledger functions, and the cap table gained a `figures` line. Training code paths (`train_job`, `fit`, objectives) were not changed after the hash.
- Training ran in parallel with P10a constructor development. The two share no data.

**Figure:** `visualizations/p10/P10_0_training_and_validation.png` (training curves; per-lineage validation NLL). B / C and A / SF objectives are in separate panels because they are not the same quantity.
