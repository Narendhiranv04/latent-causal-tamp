# 0131 — BXY-P24: one-shot independent confirmation of the frozen D / E / DIRECT-GEO / G ensembles

Date: 2026-11-02. Gate: BXY-P24.

- **Start:** `e2c90cde` (P23.1, `REMOTE_CUSTODY_VERIFIED`); HEAD equalled origin.
- **Sequence of commits:**
  1. authorization `a7efb1d4`;
  2. cohort and seal `3457e5f4`;
  3. labels `0eb0f390`;
  4. evaluation `4ba3f0a1`;
  5. this report commit.
- **Scope:** the single authorized cohort. There was no training, no second collector and no second look.

## (g) Verdict

**`P24_COMPLETE_PRIMARY_NOT_ESTABLISHED`.**

**The preregistered hypothesis that X/Y beats DIRECT is not confirmed.**
- Measured on all 193 initially infeasible roots (U), D and E are numerically ahead of DIRECT-GEO: +4.1 and +5.2 percentage points.
- Under the registered Holm rule, neither difference is established.
- E − DIRECT misses its Holm level by 0.0003: p = 0.0170 against a level of 0.0167.
- Both also fall short of the +0.10 success-gain threshold.

**Quadratic coupling (D vs E) shows no benefit.**

**The order family is established.** The order-aware D beats the order-invariant G on outcomes in the repairable K3/K4 roots:
- O2: +17.3 points, Holm CI [+0.058, +0.308], p = 0.0094.
- The strict-order contrasts O1 and O3 are also positive. They are structurally guaranteed, however, because G scores exactly 0.5 by construction.

**D and E pay for their gains with unnecessary repairs.** On 44 initially feasible roots they repair 10 of 44 (22.7%), against 2 of 44 for DIRECT. All of those edits are neutral: the target remained reachable.

All numbers below come from the single [EVALUATION_P24.json](../runs/approach_b/bxy_p24_v1/EVALUATION_P24.json) (sha `d1f6644c…`). They are not the P21 out-of-fold results.

## (b) What was executed (no runner or code change during the test)

| Step | Result |
|---|---|
| Preflight | `require_authorization` passed: approval, P23 plan lock, P23.1 analysis lock, frozen-model manifest, verified Drive custody, code tree (226 files), teacher hash. Zero `bxyg34confirm` files existed before generation |
| Authorization | [AUTHORIZATION_P24.json](../runs/approach_b/bxy_p24_v1/AUTHORIZATION_P24.json) (`049248f9…`): verbatim user approval text, post-P23.1 hashes; committed before the first scene |
| Generate | 440 / 440 predeclared slots attempted with the unchanged P23 mix, `BXY_GEN_K34C` and namespace; **237 accepted**; all 203 rejections (`NO_VALID_LAYOUT`) are kept, none replaced |
| Freeze | catalogues, label-free inputs and all 4 × 15-member predictions; [SEAL_P24.json](../runs/approach_b/bxy_p24_v1/SEAL_P24.json) (`4530a8d6…`) and ledger seal event; committed and pushed **before** the first teacher query |
| Collect | one exclusive supervisor (flock, UUID owner), 4 single-thread workers, unchanged per-query budgets, no robot reset between relocations; no crash, no recovery needed |
| Evaluate | once, `bxy_p24_analysis.evaluate` under `CONFIRM_ANALYSIS_P23_1_LOCK` (the P23 analysis lock with only the custody-gate amendment) |

The reporting module [bxy_p24_report.py](../bxy_p24_report.py) was written only after the evaluation had been committed.
- It is read-only: it never calls the teacher, never re-scores and never writes into the P24 run.
- Adding it changes the top-level code tree. `require_authorization` would therefore now refuse a fresh P24 step, which is the intended effect: no further P24 run is possible.

## (c) Artifacts

All paths are in `runs/approach_b/bxy_p24_v1/` unless stated otherwise.

| File | sha256 (prefix) |
|---|---|
| AUTHORIZATION_P24.json | `049248f9792ec2fd` |
| GENERATION.json (440 attempts) | `fa3994c723f6fe5b` |
| DESIGN.json (frozen catalogues and queries) | `25c9423025803362` |
| INPUTS_P24.pt (label-free inputs) | `8c8977d06a34ae73` |
| PREDICTIONS_P24.json (sealed) | `cdddaa29dd148e32` |
| SEAL_P24.json | `4530a8d6c04e9c9d` |
| EVALUATION_P24.json | `d1f6644ceafa9f35` |
| `results/` (6,041 write-once rows), `logs/`, `witnesses/`, LEDGER.jsonl (480 events, chain verifies) | — |
| `runs/approach_b/bxy_p24_report_v1/P24_TABLES.json` | `1f99c8cf43c40391` |
| `visualizations/approach_b/bxy_p24_v1/01–06*.png` | — |

## (d) Counts and confidence intervals

### Cohort and populations

| Family, K_intent | Slots | Accepted |
|---|---|---|
| local_mixed, K2 | 22 | 19 |
| local_mixed, K3 | 66 | 34 |
| local_mixed, K4 | 198 | 61 |
| local_pick, K3 | 44 | 42 |
| local_pick, K4 | 44 | 15 |
| v21b_near_closed, K0 | 66 | 66 |
| **Total** | **440** | **237** (locked projection 255, q10–q90 223–286) |

**Analysis populations** (teacher-verified; none underpowered):
- roots 237;
- INF 193 (projected 228);
- AVAIL 75 (projected 123);
- REP34 52 (projected 101);
- FEA 44 (projected 26).

**Verified K versus generator intent.** K_intent is a generator label, not a physical proof.

| Group | Roots |
|---|---|
| Verified K0 (feasible) | 44 |
| Verified K1 | 11 |
| Verified K2 | 11 |
| Verified K3 | 31 |
| Verified K4 | 21 |
| Certified necessary (K_cert = verified K) | 9 K2, 31 K3, 21 K4 |
| Infeasible, no candidate verified within budget | 118 |
| Available but K undecided (`s302`, censored at the CPU cap) | 1 |

- Of 152 roots built with K_intent 3 or 4, only 52 have a verified K3/K4 repair.
- 22 of the 66 K0-intent v21b roots were initially infeasible: 11 have a verified K1 repair, 2 a verified K2 repair, and 9 no verified repair.
- Availability (75/193) came in far below the projection (123). This is the main reason precision is lower than planned.

[Cohort figure](../visualizations/approach_b/bxy_p24_v1/04_cohort_populations.png)

### Per-arm endpoints (Wilson 95%)

| Arm | U (n = 193) | C (n = 75) | Unnecessary on FEA (n = 44) | Harmful | K0 no-op correct |
|---|---|---|---|---|---|
| **D** XYQ-GEO-SYM | **0.259** [0.202, 0.325] (50) | 0.667 [0.554, 0.763] | 10 / 44 = 0.227 | 0 | 0.773 |
| **E** XY-UNC-SA-GEO-SYM | **0.269** [0.212, 0.336] (52) | 0.693 [0.582, 0.786] | 10 / 44 = 0.227 | 0 | 0.773 |
| **DIRECT-GEO** | 0.218 [0.165, 0.281] (42) | 0.560 [0.447, 0.667] | 2 / 44 = 0.045 | 0 | 0.955 |
| **G** order-invariant | 0.212 [0.161, 0.275] (41) | 0.547 [0.434, 0.654] | 9 / 44 = 0.205 | 0 | 0.795 |
| ANALYTIC_ACCESS (not learned) | 0.212 | 0.547 | 0 | 0 | 1.000 |
| NOOP / SHORTEST_ADMISSIBLE / DISPLACEMENT_RANK | 0 / 0.005 / 0.005 | — | 0 / 1.0 / 1.0 | — | — |
| Verify-first oracle (evaluator-only upper bound, 14.6 teacher calls per root) | 0.389 | — | — | — | — |

[Endpoint figure](../visualizations/approach_b/bxy_p24_v1/01_endpoints.png)

**Unnecessary repairs.** All unnecessary repairs were neutral (harmful = 0). The FEA denominator is 44, so the D/E increase of +0.182 (CI [+0.068, +0.295]) is a real cost. It is not evidence of safety.

**Unverified choices.** A, E and G each made 1 choice that is unverified. These all lie on root `s302`, the root that reached the CPU cap (see (e)).
- D's choice on `s302` was verified as a success. The other three arms' choices were never labelled, and the locked rule counts an unverified choice as
  a failure.
- This adds one root (+0.005 on U) to D − DIRECT and D − E only. No label changes either way.

### Locked contrasts (paired root-family bootstrap, B = 10,000; Holm)

| Family | Contrast | Endpoint | Diff | 95% CI | Holm CI | p (raw / Holm) | Label |
|---|---|---|---|---|---|---|---|
| Primary | D − DIRECT | **U** | +0.041 | [0.000, 0.083] | [−0.005, 0.088] | 0.055 / 0.110 | NOT_ESTABLISHED |
| Primary | E − DIRECT | **U** | +0.052 | [0.010, 0.093] | [0.000, 0.104] | 0.017 / 0.051 | NOT_ESTABLISHED |
| Primary | D − E | **U** | −0.010 | [−0.031, 0.010] | [−0.031, 0.010] | 0.459 / 0.459 | NOT_ESTABLISHED |
| C check | D − DIRECT | C | +0.107 | [0.000, 0.213] | — | 0.051 | — |
| C check | E − DIRECT | C | +0.133 | [0.040, 0.240] | — | 0.013 | — |
| C check | D − E | C | −0.027 | [−0.080, 0.027] | — | 0.440 | — |
| Secondary K34 | D − DIRECT | REP34 | +0.115 | [−0.019, 0.250] | [−0.019, 0.269] | 0.098 / 0.196 | NOT_ESTABLISHED |
| Secondary K34 | E − DIRECT | REP34 | +0.135 | [0.019, 0.250] | [0.000, 0.288] | 0.036 / 0.108 | NOT_ESTABLISHED |
| Secondary K34 | D − E | REP34 | −0.019 | [−0.058, 0.000] | [−0.058, 0.000] | 0.73 | NOT_ESTABLISHED |
| Order | O1 D − G strict order | 85 roots | +0.334 | [0.258, 0.405] | [0.238, 0.417] | < 1e-4 | IMPROVES* |
| Order | **O2 D − G REP34 success** | 52 roots | **+0.173** | [0.058, 0.308] | [0.058, 0.308] | 0.0094 | **IMPROVES** |
| Order | O3 E − G strict order | 85 roots | +0.361 | [0.295, 0.419] | [0.285, 0.427] | < 1e-4 | IMPROVES* |

\* **O1 and O3 are structurally guaranteed.** G is order-invariant, so its strict-order concordance is 0.5 by construction. On the 41 certified order-twin roots, D and E order every twin correctly (1.000). Outside that subset their concordance is 0.834 (D) and 0.861 (E).

**O2 is the substantive order result.** The order-aware model succeeds more often on outcomes than its order-blind twin. On the 44 FEA roots, D − G unnecessary repairs differ by +0.023 [−0.045, +0.091].

**Holm detail for E − DIRECT.** The ordered levels are 0.0167, 0.025 and 0.05. E − DIRECT has the smallest raw p, 0.0170, which exceeds 0.0167, so the Holm sequence stops at the first step. That borderline miss is reported as is. Under the locked rule, the +0.10 gain gate would also have yielded at most `POSITIVE_BELOW_THRESHOLD`, and the unnecessary-repair guardrail (+0.182 > +0.05) would have yielded `GUARDRAIL_FAILED`.

[Contrast figure](../visualizations/approach_b/bxy_p24_v1/02_contrasts.png)

### Strata, choices, omissions, order twins, travel, calibration

**Availability-conditioned success by verified K** (descriptive; Wilson intervals in [P24_TABLES.json](../runs/approach_b/bxy_p24_report_v1/P24_TABLES.json)):

| Stratum | D | E | DIRECT | G |
|---|---|---|---|---|
| K1 (n = 11) | 0.36 | 0.55 | 0.18 | 0.45 |
| K3 (n = 31) | 0.77 | 0.81 | 0.71 | 0.55 |
| K4 (n = 21) | 0.71 | 0.71 | 0.52 | 0.62 |

[Strata figure](../visualizations/approach_b/bxy_p24_v1/03_strata_by_K.png)

**Choices on INF.**

| Arm | Chose a no-op | Failed repair | Repairs shorter than the verified K on AVAIL |
|---|---|---|---|
| D | 24 | 119 | 0 |
| E | 24 | 117 | 0 |
| DIRECT | 20 | 131 | 7 |
| G | 26 | 126 | 0 |

DIRECT's seven under-length repairs are omissions, which X/Y never makes. D chose a repair longer than K on 4 AVAIL roots and E on 2.

**Single-object omission signs** of the shortest verified repair (202 omitted-object tests):
- 96 `NECESSARY_CERTIFIED`: the target is certified infeasible without that move.
- 40 `NECESSARY_UNCERTIFIED`: the bounded planner found no plan.
- 66 unobserved: no catalogue entry.
- 0 unnecessary.

**Order twins.** 111 same-endpoint order groups across 85 roots are discordant: some orders execute and others do not. In 45 of them the failing order is *certified* infeasible.

**Matched successful travel J** (each arm vs DIRECT on the same roots):

| Arm | Its own J | DIRECT's J | Roots |
|---|---|---|---|
| D | 5.05 | 4.93 | 38 |
| E | 5.03 | 4.92 | 39 |
| G | 5.17 | 5.05 | 30 |

X/Y successes travel about 2% longer.

**Calibration of Y0** (AUROC / Brier):

| Arm | AUROC | Brier |
|---|---|---|
| D | 0.965 | 0.060 |
| E | 0.967 | 0.059 |
| DIRECT | 0.960 | 0.063 |
| G | 0.965 | 0.060 |

**Physical evidence.** All panels below are drawn from recorded teacher witnesses: relocations blue, connector to q_ref pink, target from q_ref green.
- [D vs DIRECT outcome disagreements](../visualizations/approach_b/bxy_p24_v1/05_choices_D_vs_DIRECT.png): 9 roots where only D succeeds and 3 where only DIRECT does; both directions are shown.
- Storyboards: a [certified K4 root, s134](../visualizations/approach_b/bxy_p24_v1/06_storyboard_K4_s134.png) and a [certified K3 root, s025](../visualizations/approach_b/bxy_p24_v1/06_storyboard_K3_s025.png).

**Interpretation limits.**
- Geometric access features (GEO2) and the analytic-access reference are supplied analytically, and the generator's K intent is label-free metadata. The learned part is the ranking of already-generated candidates.
- These are new seeds from the **same 2D doorway generator family**. They are not evidence of cross-generator or 3D generalization.

## (e) Resources and incidents

Hash-chained [LEDGER.jsonl](../runs/approach_b/bxy_p24_v1/LEDGER.jsonl):

| Phase | CPU-s | Wall s |
|---|---|---|
| Construction (4 workers) | 28,431 | 7,116 |
| Freeze (inputs + 60-member predictions, 1 thread) | 263 | 263 |
| Labelling (237 roots, summed per-root) | 37,587 | 9,532 (supervisor wall) |
| Evaluation | 1.5 | 1.5 |
| **Total** | **66,283 of 90,000** (3,000 reserve untouched) | **about 16,900 of 40,000** |

**Incident.** Root `2d-bxyg34confirm-c34-s302` reached the per-root ceiling (`CPU_CAP(RLIMIT_CPU)` at 1,398.8 CPU-s). This was handled exactly as locked:
- 1 query was `CENSORED` and 5 were `UNATTEMPTED`; the root was not retried and no budget was extended.
- Query statuses: 6,035 OBSERVED, 1 CENSORED, 5 UNATTEMPTED, 0 CORRUPT.

There were no crashes, no recovery events, no duplicate workers and no custody or data-blindness exposure.

## (f) Tests and replays

Recorded in `runs/approach_b/bxy_p24_v1/regression/`, single-thread:
- full suite: **740 passed, 1 skipped** (1,010 s);
- six archived replays: all exit 0;
- frozen-evidence hash guard (P-min–P15 and P16–P23.1 run directories): **clean** (no modified or new file).

The suite ran against the evaluated code tree. The two reporting modules are read-only and post-evaluation; their output is the committed tables and figures.

## (h) Blockers

None for P25. P25 uses only these stored results: no teacher call, no optimizer step, no second cohort.
