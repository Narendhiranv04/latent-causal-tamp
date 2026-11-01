# 0130 — BXY-P23: final-confirmation preflight (frozen G control, locked one-shot protocol, hardened engine; no confirmation scene)

Date: 2026-11-02. Gate: BXY-P23 of the P23 → P25 contract.

- **Work done:** read-only checks and synthetic tests only.
- **Not done:** no teacher query, no training, no confirmation scene and no test prediction.

## Readiness verdict

**`BLOCKED_CHECKPOINT_CUSTODY`**, so P23 is **not** `P23_READY`. Every other exit item passes. Under the contract's stopping rule,
P24 cannot start until custody is completed. P24 also still needs the user's separate approval.

| Exit item | Status | Evidence |
|---|---|---|
| P22 anchor, frozen evidence intact | PASS | HEAD `bcad58e6` at start; tracked tree clean; hash guard ok; no P-min…P22 file modified (`git diff bcad58e6 --stat` lists only new P23 / P24 paths) |
| P21 evaluation reproduced | PASS | `EVALUATION_P21.json` recomputed from the committed runs is identical except `accounting.eval_cpu_s` ([REPRODUCTION_P21.json](../runs/approach_b/bxy_p23_v1/REPRODUCTION_P21.json)) |
| Checkpoints verified and test-loaded | PASS | all 90 P21 runs: RESULT.json, run id and best.pt sha256 match. All 60 D / E / A / G members load and reproduce their stored held-out predictions to max \|Δ\| = 3.6e-15 ([CHECKPOINTS_P23.json](../runs/approach_b/bxy_p23_v1/CHECKPOINTS_P23.json)) |
| **Independent checkpoint custody** | **BLOCKED** | One physical disk only (`nvme0n1`). The repository, the P22 copy, the Windows partition (nvme0n1p3) and `/mnt/newvolume` (an empty directory) all share it. No off-machine location is approved. Nothing was copied ([CUSTODY_P23_attempt1-3.json](../runs/approach_b/bxy_p23_v1/)) |
| G frozen without retraining | PASS | [FROZEN_MODELS_P23_APPEND.json](../runs/approach_b/bxy_p23_v1/FROZEN_MODELS_P23_APPEND.json) (sha `7324ff53…`) |
| q_ref = q0, label-free inputs | PASS | 398 development records and all 3 frozen input caches (201 roots): q_ref = q0 = scene robot state. Mutation and label-blindness tests pass |
| One-shot protocol unambiguous | PASS | [CONFIRM_PLAN_P23_LOCK.json](../runs/approach_b/bxy_p23_v1/CONFIRM_PLAN_P23_LOCK.json) (`2f442bf5…`) and [CONFIRM_ANALYSIS_P23_LOCK.json](../runs/approach_b/bxy_p23_v1/CONFIRM_ANALYSIS_P23_LOCK.json) (`f7e8692c…`) are successors; the P22 originals stay untouched and are referenced by sha |
| Exclusive collector and recovery | PASS | 13 mock-teacher smoke tests ([tests/test_bxy_p23_engine.py](../tests/test_bxy_p23_engine.py)); repeated 5× with no flake |
| P24 runner loads models and computes features for a synthetic scene | PASS | 2 synthetic-namespace roots generated, frozen, encoded and scored by all 60 members ([SYNTHETIC_PIPELINE_P23.json](../runs/approach_b/bxy_p23_v1/SYNTHETIC_PIPELINE_P23.json)) |
| No confirmation scene | PASS | no `bxyg34confirm` path exists; `runs/approach_b/bxy_p24_v1/` does not exist; every P24 step raises `PermissionError` (tested) |

**To clear the blocker,** do one of the following:
- attach an external drive and run `python3 bxy_p23_preflight.py custody <mount point>`; or
- explicitly approve an off-machine / private-storage location.

The step then:
1. copies the 60 frozen checkpoints and their RESULT.json files;
2. verifies every sha256;
3. restores them into a scratch directory and re-loads every member;
4. writes the next `CUSTODY_P23_attemptN.json`.

P23 becomes `P23_READY_FOR_AUTHORIZATION` only then. The model binaries are not pushed to GitHub.

## 1. Start state and source hashes

- **Start:** HEAD `bcad58e68c09f5d7ec3cc5942f5fc7a40c9315a4` (P22) = origin; tracked tree clean.
- **Confirmation namespaces:** `bxyg21confirm` and `bxyg34confirm` were verified absent anew.
- **Hashes:** evaluator, model and engine code hashes are in the manifests. The P24 authorization proposal pins the sha256 of all 225
  tracked top-level source files plus `config.toml` (tree sha `f8301523…`) and the teacher hash.

## 2. Hypotheses carried into the confirmation (unchanged)

| Family | Comparisons | Status entering P24 |
|---|---|---|
| Primary: whole-system selection | D vs DIRECT-GEO, E vs DIRECT-GEO, D vs E (coupling) | not established in development (P21: +0.031 [−0.002, +0.064]; coupling +0.002) |
| Secondary: K3/K4 | the same three on REP34 | not met in development (P21 H1–H3) |
| Order (mechanistic) | D vs G and E vs G strict order; D vs G REP34 success | supported in development (P21 H4, exploratory) |

- **Thresholds are the historical ones:**
  - paired CI lower bound > 0;
  - point gain ≥ 0.10;
  - unnecessary-repair increase ≤ +0.05.
- **Order concordance:** a CI lower bound > 0 is enough, as in P17's `ORDER_FAVOURS_FIRST`.

## 3. Implementation delta (and what is unchanged)

**New code** (no historical module edited):

| Module | Lines | Purpose |
|---|---|---|
| [bxy_p23_engine.py](../bxy_p23_engine.py) | 489 | hardened collector |
| [bxy_p23_preflight.py](../bxy_p23_preflight.py) | — | P23 steps |
| [bxy_p23_lock.py](../bxy_p23_lock.py) | — | locks, power, proposal, figure |
| [bxy_p24_confirm.py](../bxy_p24_confirm.py) | — | gated one-shot runner |
| [bxy_p24_analysis.py](../bxy_p24_analysis.py) | — | locked analysis |
| [tests/test_bxy_p23.py](../tests/test_bxy_p23.py), [tests/test_bxy_p23_engine.py](../tests/test_bxy_p23_engine.py) | — | tests |

The engine exceeds the contract's preferred 400 lines because the lock, recovery and ledger logic stays in one file.

**Unchanged:**
- the 2D 3R robot;
- the teacher (`bxy_teacher` / `bxy_pmin`, per-query budget `bd_2d.QB`);
- X/Y semantics, with one terminal connector to q_ref and no homing between relocations;
- F1–F5, GEO2, SYM, the model classes, the checkpoints and the P11 choose rule;
- the K_cert definition, the candidate grammar (`bxy_p20_k34.root_design`) and the generator.
  - The confirmation reuses P20 REV34['k3'] through an in-memory alias; `bxy_p20_k34.py` is not edited.

### 3.1 G frozen as the matched order-invariant control

The 15 P21 `G:XYQ-GEO-SYM-ORDINV` checkpoints form the G ensemble, with exactly the D / E / A averaging:
- mean p, J_hat, px and py over the 15 members;
- F1 first;
- `bxy_p11.choose` with the arm's rule.

D / E / A are referenced from P22 unchanged; members and checkpoint sha256 are identical (tested).

**A gap in P22, recorded as an amendment:** P22 declared the deployment rule procedure (`bxy_p18.pooled_rule`) but **never recorded the
chosen rules**. P23 computes them with exactly that procedure:
- data: the P21 early-stop predictions pooled over folds and seeds;
- grid and limit: the frozen GRID and U_MAX;
- no new search and no test data.

| Arm | No-op gate | α | β | γ | Pooled early-stop success / unnecessary (development) |
|---|---|---|---|---|---|
| D | 0.7 | 0.0 | 0 | 0.05 | 0.367 / 0.076 |
| E | 0.7 | 0.0 | 0 | 0.05 | 0.382 / 0.081 |
| A (DIRECT-GEO) | 0.5 | 0.3 | 0 | 0.0 | 0.348 / 0.083 |
| **G** | none | 0.0 | 0 | 0.05 | 0.348 / 0.094 |

All four meet the inner guardrail (≤ 0.10). These are early-stop operating points, **not** performance estimates of the ensembles.

### 3.2 Protocol lock (successors; the P22 files are untouched)

- **Population:**
  - 440 predetermined slots, P22 mix unchanged: local_mixed K4 198, local_pick K4 44, local_mixed K3 66, local_pick K3 44, local_mixed
    K2 22, V21B controls 66;
  - every slot's spec and seed rule is frozen;
  - no replacement, no adaptive sampling;
  - one generation, one design freeze, one labelling run and one evaluation;
  - labelling order is a seeded hash permutation, so a budget stop leaves an outcome-independent remainder.
- **New and stricter: predict first, then label.**
  - The frozen ensembles score every accepted root from the label-free design immediately after the catalogue freeze.
  - Those predictions are **sealed** (sha256 in the hash-chained ledger) **before the first teacher call**, so they cannot depend on labels.
- **Endpoints and denominators:**
  - **U** = success over **all** initially infeasible roots; roots with no verified candidate are failures for every arm.
  - **C** = success over infeasible roots with ≥ 1 teacher-verified candidate.
  - **Unnecessary repairs** are measured over initially feasible roots.
  - **REP34** = available roots with verified K ∈ {3, 4}, where every shorter admissible candidate has been decided.
- **Authoritative hierarchy:**
  - U is the single primary endpoint and gives the headline label.
  - C must have a 95% CI lower bound > 0 for any positive label: C cannot rescue a failed U, and U is never swapped for C.
  - Holm is applied within three separate families: primary, K3/K4 secondary and order.
  - Labels: `IMPROVES`, `POSITIVE_BELOW_THRESHOLD`, `GUARDRAIL_FAILED`, `REVERSED`, `NOT_ESTABLISHED`, plus an `UNDERPOWERED` flag below the
    locked minimum n (INF 60, AVAIL 30, REP34 30, FEA 30, order roots 20, inferential K stratum 10).
- **Statistics:**
  - paired bootstrap over root families (one per root), B = 10,000, seed 0, percentile intervals;
  - Holm step-down on two-sided bootstrap p-values, with explicit Holm-level intervals.
  - Each frozen ensemble is **one deterministic predictor**, so each root contributes one binary outcome per arm; pair × seed counts are
    never treated as independent.
  - Strict order is averaged per root first; ties are \|Δpx\| ≤ 1e-8.
- **K labels and missingness:**
  - certified-necessary = K_cert = K_catalogue, reported with and without that requirement;
  - an unobserved Y0 is excluded from denominators and counted;
  - censored and unattempted queries are absent, never 0;
  - corrupt rows are a custody event;
  - an undecided chosen candidate is **not** a success (counted per arm, plus a sensitivity analysis);
  - certified negatives are kept separate from fixed-budget negatives.
- **References:** no-op, shortest, displacement, the analytic-access geometry rule, and the verify-first **evaluator-only** oracle with its
  verification count.

**Reconciliation with P22** (explicit in the analysis lock):
- P22's "two primary endpoints by K stratum, Holm per endpoint" becomes the hierarchy above.
- The K3/K4 test population is fixed as REP34.
- G gets its own family.
- The pooled rules are recorded.
- Thresholds are unchanged.

### 3.3 Hardened one-shot engine (fixes the P20 duplicate-supervisor failure)

| Mechanism | How it works |
|---|---|
| Supervisor lock | `flock(LOCK_EX \| LOCK_NB)` on SUPERVISOR.lock for the supervisor's lifetime. The lock is held by the kernel on the file itself, so it is seen across PID namespaces, unlike `ps` |
| Owner record | owner UUID, manifest sha and a heartbeat |
| Second launch | refused while the lock is held, while the heartbeat is fresh, or while reservations exist |
| Stale owner | needs the explicit `recover <out> <owner> <note>` step; no blind restart |
| Per-root work | an O_EXCL reservation by the supervisor, plus a worker-held root flock; a duplicate or unreserved worker exits 75 without writing |
| Results | one file per query: tmp + fsync + `os.link`, so a write cannot overwrite; each row carries its own sha256 |
| Bad rows | hash or identity mismatches are reported as CORRUPT and never re-queried |
| Scene identity | record sha vs the design → exit 76 and a custody stop; a teacher key mismatch → an unobserved row |
| Ledger | append-only, fsync'd, hash-chained (each event carries the sha256 of the previous line); construction, cache, prediction, labelling and evaluation are all charged |
| Recovery charge | workers write a CPU heartbeat; a lost worker is charged min(allowance, CPU at its last heartbeat + 2 × wall time since), which is sound for single-thread workers even if a C call stalls the heartbeat. Without a heartbeat, the full allowance is charged |
| Query states | OBSERVED / CENSORED / CORRUPT / UNATTEMPTED (+ reason: root cap, aggregate stop, not started) |

## 4. Data custody, counts and strata

- **No new data.**
- **Development population** used for reproduction and the power analysis: 398 roots (P-min 197, P15 28, V2.1 87, K34 86).
- **Synthetic validation roots:** namespace `bxyp23synth`, seeds hash the namespace, never confirmation seeds.
  - one local_pick doorway root (K_cert 3, 17 candidates, 31 queries);
  - one V21B control (7 candidates, 14 queries);
  - no teacher call.

**Projected confirmation yield** (P20 k3 realization per family; Dirichlet(counts + ½) restricted to structurally possible outcomes, since
K_cert = K_intent excludes a smaller verified K):

| Population | Median | 10–90% |
|---|---|---|
| Accepted roots | 255 | 223–286 |
| Initially infeasible | 228 | 193–262 |
| Available | 123 | 97–152 |
| **REP34** | **101** | 78–128 |
| K3 | 47 | 34–61 |
| K4 | 53 | 33–78 |
| Initially feasible | **26** | 12–42 |

P22's point figures (K3 49.5, K4 41.4) fall inside these ranges.

**Weakness:** the P22 mix leaves only about 26 feasible roots, so the unnecessary-repair guardrail will be imprecise and is flagged.

**Power:**
- With one deterministic ensemble per arm, the per-root difference is −1, 0 or +1, so its sd ≈ √(disagreement rate).
- From P21 (D vs DIRECT) that gives U 0.42, C 0.64 and REP34 0.62, against 0.21 / 0.32 / 0.28 for P21's 3-seed means.
- Projected 95% half-widths:
  - U ≈ 0.054 (MDE at 80% power 0.077, n = 228);
  - C ≈ 0.11;
  - REP34 ≈ 0.12.
- **Honest expectation:** given P21's D − DIRECT point estimate of +0.031, the primary comparison will most likely be `NOT_ESTABLISHED`.
  The order family is the most likely positive result.

## 5. Resource ledger ([LEDGER.jsonl](../runs/approach_b/bxy_p23_v1/LEDGER.jsonl), hash-chained)

| Phase | CPU-s | Wall s |
|---|---|---|
| Checkpoint verification + 60-member test-load | 1,145 | 73 |
| Reproduction, freeze, contract, locks (re-runs included), figure | ≈ 40 | ≈ 40 |
| Synthetic pipeline (two runs, 2 workers) | 69 | 49 |
| Unledgered development and test runs (conservative charge) | 150 | — |
| Regression (six replays + full pytest + guard, single-thread) | 1,025 | 1,033 |
| Custody re-check + proposal regeneration after a path-redaction edit | ≈ 10 | ≈ 10 |
| **Total (ledger, hash chain verified: 23 events)** | **2,431** | **1,197** |

The total is against a 3,000 CPU-s / 5,400 s ceiling.

**Incident (disclosed):** the checkpoint test-load ran torch with its default intra-op threading. It used 1,145 CPU-s in 73 s of wall
time, which breaks the contract's single-thread-worker rule (CPU charged in full). Every later step pins one thread
(`OMP / MKL / OPENBLAS = 1`, `torch.set_num_threads(1)`), and the P24 freeze does the same.

No teacher CPU, no training and no cohort generation occurred.

## 6. Results

- **Reproduction:**
  - P21 is identical.
  - The frozen ensembles' members reproduce their stored predictions bit-for-bit up to floating-point noise (3.6e-15).
- **Frozen G and rules:** see §3.1.
- **Figure:** [visualizations/approach_b/bxy_p23_v1/01_protocol_power_rules.png](../visualizations/approach_b/bxy_p23_v1/01_protocol_power_rules.png):
  - (a) projected yield with uncertainty, the P22 point values and the locked minimum n;
  - (b) half-width against n under the single-ensemble sd;
  - (c) the frozen pooled rules' development operating points.
- **No test score exists.** The analysis code was exercised only on synthetic units and as a structure dry run on the K34 development
  roots with P21 out-of-fold predictions (labelled "not evidence"; it checks counts, for example 86 roots, REP34 = 21, G's order
  concordance exactly 0.5, and 7 certified K4).

## 7. Leakage, reproducibility and regression

**Leakage checks:**
- The scorer view built with labels on disk is identical to the prediction-time view, which reads no result file.
- Member predictions are identical for both views.
- `privileged_mutation` leaves the input cache key unchanged.
- Scrambled labels / K / witness leave `root_design` unchanged.
- Candidate rows carry only `admissible, cd, m, sig, xi, yi`.

**Disclosed limitation:** the catalogue is generated from the construction's intended order, which is label-free but
generator-informed. The scorer never sees a candidate's kind.

**Regression** (recorded in `runs/approach_b/bxy_p23_v1/regression/`, single-thread):
- full suite: **737 passed, 1 skipped** (718 at P22 + 19 new P23 tests);
- six archived replays: exit 0;
- hash guard: clean (`modified: []`, `untracked_or_changed: []`).

After the regression, `bxy_p23_preflight.py` received one edit: the custody step now enumerates mounts from `/proc/mounts` instead of a
hardcoded private path. The P23 tests were re-run (19 passed), and the authorization proposal was regenerated against the final code tree.

## 8. Limitations, claim status, STOP

**Claim status is unchanged from P22:**
- not established: D / E vs DIRECT, and coupling;
- supported in development: order-awareness;
- physically witnessed but below the inferential threshold: K4 (7 certified roots).

No independent result exists. A future positive X/Y-vs-DIRECT result would not isolate the factorization, because the X/Y arms also use
component labels and SYM supervision. New seeds come from the same K34 doorway family, so there is no cross-generator claim.

**Authorization request for P24** (after custody): approve
[AUTHORIZATION_P24_PROPOSED.json](../runs/approach_b/bxy_p23_v1/AUTHORIZATION_P24_PROPOSED.json) (sha `c15b1ea1…`):

| Item | Proposed |
|---|---|
| Slots | 440 |
| Aggregate CPU-s | ≤ 90,000, including a 3,000 CPU-s evaluation reserve |
| Wall | ≤ 40,000 s, covering construction, freeze, labelling and evaluation |
| Workers | 4 single-thread |
| Per root | ≤ 1,400 CPU-s |
| Teacher budget | unchanged |

- **Point projection:** 70,322 CPU-s.
- **Cost basis:** about 75 CPU-s of construction per slot (33k CPU-s in total), about 154 CPU-s of teacher time per accepted root, and
  about 2–4k CPU-s for the freeze.

STOP (gate P23, `BLOCKED_CHECKPOINT_CUSTODY`). No confirmation scene has been generated or labelled.
