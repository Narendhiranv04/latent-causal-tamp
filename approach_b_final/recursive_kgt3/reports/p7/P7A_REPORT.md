# P7A — Public bounded candidate repair: implementation, matched controls, gate

Branch `naren/kgt3-exec-composition`. Starting point `60e7006d50` (P6A; its P6B is suspended).

**Commits:**
- `0922a9dc2e`: plan, pre-registered before any code result;
- `225cf7f5ca`: code, fixtures and amendments A1/A2, before any DEV run;
- this commit: DEV results and the report.

**Not done:** no teacher calls, training, dataset generation, release_v2 access, or P7B/P7C execution. Frozen checkpoints, teacher code, and all P4–P6 outputs and tests are untouched.

## Gate: **REVISE** (pre-registered amendment A2; fixtures pass, so not BLOCKED)

| Criterion (A2, union of method + diagnostic sets, exposed root excluded) | Result |
|---|---|
| Synthetic fixtures F1–F6 (FULL must solve all; controls fail as designed) | **12/12 tests pass** |
| FULL vs FLAT, paired top-1 static-valid (net ≥ 3) | 0 wins / 0 losses, net 0 |
| FULL vs FLAT, paired top-1 static-order existence (net ≥ 3) | 0 / 0, net 0 |
| FULL vs RANDOM (both metrics) | 0 / 0, net 0 |
| **Decision** | **REVISE** (no credible advantage over FLAT or RANDOM) |

FULL also **loses** to the simpler arms:
- vs DEST_ONLY: static-order existence net −8, validity net −1;
- vs ORIG: existence net −15, validity net −2.

## 1. What was built (minimal; reuses existing modules)

- **`p7_repair.py`** (public, 238 lines). A repair beam with expansions for:
  - executing pending moves (own or adjusted destination);
  - inserting enabling moves of public suspects;
  - dropping required moves (replacement);
  - rebuilding from a target-near core.

  The merge is exact on (plan set, pending, dropped). It uses a free public geometric shortlist (A1) and matched budgets (Φ_MAX 2,000 / Y_MAX 300 per endpoint). Every arm is a configuration flag of one code path. It reuses `data.HypoRoot`, `data.check_sequence`, `data.install_guard`, and `models.Frozen.ytask/propose/y_end`.
- **`p7_eval.py`** (evaluator, 191 lines). Reuses the P5A `Chk`, `run_order` and `classify`, and `dev_eval.Static`. Labels are read only here, after predictions.
- **`tests/test_p7_repair.py`** (142 lines, 12 tests): fixtures, invariants, budget, determinism, leakage.
- No existing file was modified apart from `reports/p7/`. P4, P5 and P6 code are byte-unchanged.

## 2. Candidate statistics and matched-control results (offline static proxy; exploratory, exposed DEV)

**Method set** (public: top-2 frozen-hY endpoints per root, 50 endpoints / 25 roots; 5 of 50 base endpoints are statically reorderable):

| Arm | Top-1 static-valid | Top-1 admits static order | Final target live | Any top-5 valid | Mean y_end | Mean len | +enablers / −dropped / re-destined | Mean Φ / Y used | Wall (s) |
|---|---|---|---|---|---|---|---|---|---|
| ORIG (P4 order, no search) | 0 | 5 | 27 | 0 | 0.93 | 8.3 | 0 / 0 / 0 | 0 / 1 | – |
| **FULL** | 0 | 0 | 5 | 0 | 0.13 | 2.9 | 0.04 / 5.4 / 2.8 | 186 / 61 | 21.7 |
| DEST_ONLY | 0 | 2 | 20 | 0 | 0.32 | 8.3 | 0 / 0 / 7.9 | 283 / 20 | 20.8 |
| OBJSET_ONLY | 0 | 0 | 2 | 0 | 0.35 | 1.9 | 0.20 / 6.6 / 0 | 184 / 171 | 22.4 |
| FLAT | 0 | 0 | 0 | 0 | 0.12 | 1.2 | 0.18 / 0 / 0.9 | 404 / 20 | 33.3 |
| RANDOM | 0 | 0 | 4 | 0 | 0.16 | 3.0 | 0.14 / 5.4 / 2.7 | 340 / 97 | 30.2 |
| FULL_φG (ablation) | 0 | 2 | 20 | 0 | 0.31 | 6.6 | 0.24 / 1.9 / 5.5 | 231 / 99 | 9.6 |
| FULL_φY (ablation) | 0 | 0 | 0 | 0 | 0.12 | 2.5 | 0.10 / 5.9 / 2.3 | 180 / 60 | 14.6 |

**Diagnostic set** (evaluator-selected label-free file: the 53 P5A teacher-Y endpoints; 13 of 53 are reorderable):

| Arm | Top-1 static-valid | Top-1 admits static order | Final target live | Any top-5 valid | Generation / ranking failures | Mean y_end | Mean len |
|---|---|---|---|---|---|---|---|
| ORIG | 3 | 13 | 53 | 3 | 50 / 0 | 0.88 | 10.5 |
| **FULL** | 1 | 1 | 8 | 1 | 52 / 0 | 0.07 | 3.1 |
| DEST_ONLY | 3 | 8 | 35 | 4 | 49 / 1 | 0.29 | 10.5 |
| OBJSET_ONLY | 0 | 0 | 3 | 0 | 53 / 0 | 0.17 | 1.9 |
| FLAT | 0 | 0 | 0 | 0 | 53 / 0 | 0.05 | 1.0 |
| RANDOM | 0 | 0 | 2 | 0 | 53 / 0 | 0.05 | 3.2 |
| FULL_φG (ablation) | **5** | 6 | 33 | 5 | 48 / 0 | 0.30 | 8.3 |
| FULL_φY (ablation) | 0 | 0 | 2 | 0 | 53 / 0 | 0.07 | 2.5 |

**Notes on these tables:**
- **Availability:** every arm returned at least one complete candidate on every endpoint (50/50, 53/53).
- **Budget:** used far below the caps (beams emptied first, `stop = BEAM_EMPTY`). Total wall time across all arms and both sets was 5 min 43 s on one GPU.
- **Generation vs ranking:** almost every failure is a *generation* failure; there is no statically valid candidate even among the top 5. Ranking failures appear only for DEST_ONLY (1).
- **Diversity:** proposals do leave the old sets. FULL top-1 destinations outside the S0 cVAE top-4 numbered 104 (method) and 113 (diagnostic). Objects absent from every P4 pool reached a FULL *top-1* in 0 cases, although such objects were *proposed* (see section 3).
- **FULL_φG is an ablation.** Its better diagnostic-set numbers are reported, **not selected** (pre-registration).

## 3. Enabler audit (private evaluator; P5A never-moved pickup blockers)

On the 29 diagnostic endpoints that have pickups blocked by never-moved objects:

| Quantity | Value |
|---|---|
| Kill-table blocker objects (all contributors) | 254 |
| … of which in FULL's public S0 suspect list (k_s = 6) | **172** (recall 0.68) |
| Public suspects | 174, of which **172 are kill-table blockers (precision 0.99)** |
| Blocker objects absent from every P4 pool (so new to the candidate set) | 32 |
| Endpoints where any FULL top-5 plan moves a blocker | **0 / 29** |

**Answer to "can the search generate a required enabling move absent from the original candidate set?"**
- **Synthetic fixtures: yes.** In F1 and F3, enablers that were absent from A are discovered, inserted before the dependent move, and chained two levels deep.
- **DEV, proposal stage: yes.** The public suspect heuristic proposes the right objects (precision 0.99), including 32 that P4 never touched.
- **DEV, selection stage: no.** The search never commits to them.

## 4. Why FULL fails (diagnosis; no tuning was done on DEV)

1. **Drops are under-priced relative to executed moves.**
   - The frozen temporary-target ŷ is miscalibrated (P3 D3: around 0.01–0.08 even for feasible moves). Under it, an executed move costs about 2.5–4.6 nats.
   - A drop costs λ_d = 1 plus a frozen-ŷ_end loss. ŷ_end is false-high on short endpoints, the P3 D2 failure, so that loss is small.
   - Result: FULL drops 5.4–7.5 required moves and ends with 3-move plans with low ŷ_end (0.07–0.13), whose final target is statically live in only 5/50 and 8/53 endpoints.
2. **Enabling moves are under-valued** (post-hoc diagnostic `P7A_POSTHOC_NODROP.json`; not pre-registered, not eligible for P7B):
   - With drops disabled, enablers are still rare (0.09–0.22 per plan), and real blockers are moved in only 2/29 endpoints. Top-1 static-valid: 2/53 and 0/50.
   - The isotropic clearance heuristic φ_G charges at least about 1.5 nats to move an object out of clutter, but credits only about 0.5 nats of clearance to each affected move. Real blockage is direction-specific; it is not "any neighbour".
3. **The geometry-only score (FULL_φG) behaves more sensibly** (fewer drops, longer plans, 5/53 valid). This is consistent with the P6A finding that frozen temporary-target and chained-X signals are poor executability rankers on these dense scenes. It is an exploratory observation on exposed roots.

## 5. What is validated, learned, heuristic, or unverified

| Category | Items |
|---|---|
| **Mathematically validated (tests)** | <ul><li>Exact merge: the cost is Markov in (plan set, pending, dropped).</li><li>Grammar invariants on every returned plan: legal destinations, no target move, move-once, ≤ 12 moves.</li><li>Budget accounting.</li><li>Determinism.</li><li>The fixtures F1–F6 behave as specified under an oracle score. That shows the *mechanism* can express insertion, chains, replacement at the cap, destination repair and rebuild.</li></ul> |
| **Learned by existing frozen models** | <ul><li>φ_Y: temporary-target ŷ.</li><li>ŷ_end: endpoint target restoration.</li><li>cVAE S0 placement proposals.</li></ul> |
| **New hand-designed heuristics** | <ul><li>Public suspects (8-neighbourhood, two levels).</li><li>φ_G isotropic clearance.</li><li>Beam heuristic h.</li><li>Public parking ranking.</li><li>Drop price λ_d.</li><li>Rebuild core.</li><li>A1 shortlist.</li></ul> |
| **Physically unverified** | <ul><li>Everything on DEV.</li><li>Static checks are offline *necessary* screens (P5B showed 1/27 static-valid orders executed physically).</li><li>No P7A plan has been executed by the teacher.</li></ul> |

## 6. Leakage and regression audit

**Leakage:**
- An AST-level test shows `p7_repair.py` has no privileged token: no kill tables, `dev_eval`, `p5*`/`p6_eval`/`p7_eval`, teacher, verify, witness, `K_certified`, `unmoved_blockers`, or the exposed-root id.
- Public P4/P6 modules do not import P7.
- The path guard is active during `run`.
- Endpoint inputs are label-free.
- Kill-table blockers are used only in the post-prediction audit.

**Determinism:** FULL and RANDOM are reproducible (tested).

**Tests:**
- 68/68 pass: P7A 12, P6A 28, P5B 9, P5A 19.
- `test_p1_p2` passes 22/22.
- The `test_p4_mock` output is identical to the committed `GATE_B_MOCK.json`.

## 7. Visualizations (real DEV geometry; all plans unverified)

- **`p7a_examples.png`:** each row shows (1) the original P4 sequence, (2) public suspects (the suspected dependency, a heuristic) with cVAE candidates and new placements, and (3) the composed hypothetical plan, with its offline static status and frozen ŷ_end.
  - Rows 1–2 (FULL) show the failure mode: 10 or 8 of 12 moves dropped.
  - Row 3 is the post-hoc no-drop diagnostic, with one inserted enabler (green ring) on DEEP9_070dc43e4252, still statically invalid.
- **`p7a_arms.png`:** per-arm static-proxy counts, method and diagnostic sets.

## 8. Proposed P7B schedule: **conditional; not frozen, not executable now**

The arm P7B was meant to evaluate (FULL) failed its pre-registered gate. Freezing a physical queue for it now would spend teacher calls on a mechanism the offline evidence already rejects. The template below applies **only after a revised P7A-R passes A2-equivalent gates on new roots**:

- **Roots:** 12 development roots, non-exposed and new (no P3–P7 exposure), stratified (K4 ×4, K5/K6 ×3, K9 ×4, K12 ×1). The public endpoint is selected by the P6A rule.
- **Arms:** revised FULL top-1, DEST_ONLY top-1, FLAT top-1 (matched budget), and ORIG (reused only if already tested).
- **Caps:** ≤ 36 X calls + ≤ 12 Y calls + a 4-call confirmation reserve, giving **≤ 52 teacher calls, 2 workers, 2,400 s cumulative wall time**.
- **Harness:** the P5B harness (fixed queue, fail-closed, cumulative wall, three-valued statuses).
- **Primary outcome:** complete X=1 ∧ Y=1 per root, compared as paired roots.

## 9. Exact next gate (requires your authorization; nothing started)

**P7A-R (revision), offline only**, with a new pre-registration *before* any run:
- **(a) Value enablers by clearance gained at specific pending moves**, using a direction-aware public approach-corridor model relative to the robot base. Alternatively, a rule-based "clear the level-1 suspects of the lowest-clearance pending move" insertion. Suspect precision is already 0.99.
- **(b) Allow drops only to satisfy the 12-move cap**, priced by count, not by the miscalibrated ŷ_end.
- **(c) Use frozen ŷ only as within-scene rank-normalized evidence**, never as calibrated probabilities. No labels may be used for calibration.
- **(d) Keep the same arms, matched budgets and A2 gate,** evaluated on new development roots, because every current DEV root is exposed. Without new roots, any further DEV improvement remains exploratory.

**If P7A-R cannot beat FLAT and RANDOM under that gate, the frozen-model K>3 repair line should be reported as BLOCKED.**

## Files

**Added:**
- `p7_repair.py`, `p7_eval.py`, `tests/test_p7_repair.py`;
- in `reports/p7/`: `P7A_PLAN.md` (pre-registration + A1/A2), `P7A_REPORT.md`, `P7A_SUMMARY.json`, `P7A_JUDGED_TOP1.jsonl`, `P7A_POSTHOC_NODROP.json`, `p7a_examples.png`, `p7a_arms.png`.

**Raw predictions** (`p7_method.jsonl`, `p7_diag.jsonl`, `p7d_*.jsonl`) are committed in `reports/p7/`. They are label-free.

**Reproduce:**
```
python p7_repair.py run endpoints_{method,diag}.jsonl dev_public.jsonl p7_{method,diag}.jsonl
python p7_eval.py analyze RUN_DIR DEV_PRIVATE TABLES reports/p5/P5A_PER_ENDPOINT.jsonl P4_DIR reports/p7 ; python p7_eval.py figure RUN_DIR reports/p7
```

**STOP.**
