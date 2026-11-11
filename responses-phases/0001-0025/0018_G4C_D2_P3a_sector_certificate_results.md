# 0018 — G4C-D2-P3a: link-0 sector certificate, implementation and static re-adjudication

| Field | Value |
|---|---|
| Report number | 0018 (new; 0001–0017 unchanged) |
| Date | 21 October 2026 |
| Stage | **G4C-D2-P3a only.** New pick-side certificate `LINK0_SECTOR_PICK_V1` (producer + independent checker), one static adjudication of the frozen 6 POC_S + 9 pilot queries, and a positive-witness control set. **Zero** motion-planner, skill, target-evaluation and relocation calls in the adjudication. No P3b, POC_F, training, 3D or hardware. |
| Execution contract | `instruction-phase-md/G4C_D2_P3A_Sector_Certificate_Implementation_and_Static_Adjudication.md` (180 lines, read in full; your file, left untracked) |
| Previous turn sync | Report 0017 was handed over uncommitted. At the start, HEAD = `origin/main` = `cd4e9fd`. It was then committed **alone** as `512259299ebaab5afdd5403edaf86c4359fda1ee` (report-only; byte-identical to the handed-over text, sha256 `a470abd9…`). |
| Run directory | [`../runs/g4c_d2_p3a_static/`](../runs/g4c_d2_p3a_static/), produced by `python run.py g4c-d2-p3a-static --out runs/g4c_d2_p3a_static` (exit 0) |
| **Verdicts** | `P3A_VALIDATED_CERTIFICATE` **NOT DECLARED**. Everything was met except the full regression gate, which is `REGRESSION_NOT_COMPLETED` and overshot its 300 CPU-s cap by 19.8 CPU-s (§6). · `P3A_Q2_MET` **NOT MET** · `P3A_ACCESS_ORDER_MET` **MET (checker-accepted)** · `P3A_FUTILITY` not triggered · **No certificate safety or integrity failure.** **STOP.** |

---

## 1. Repository, inputs and integrity

**Repository status (before and after this stage):**
- The two tracked root PDFs (`latent_causal_tamp_implementation_guide_v1_8.pdf`, `latent_causal_tamp_specification_v1_6.pdf`) remain deleted in the working tree, exactly as found. They were not restored, moved or staged.
- Instruction files and the v1.7/v1.9 bundle stay untracked.

**Input integrity (preflight and post-run, sha256 against each run's own manifest):** zero mismatches in every frozen run.

| Run | Files checked |
|---|---|
| `runs/g4c_d2_poc_s` | 452 |
| `runs/g4c_pilot` | 324 |
| `runs/g4d_evidence` | 129 |
| `runs/g4c_d2_precheck` | 9 |
| `runs/g4c_preflight` | 7 |

- The POC_S and pilot plans' source bindings match the current files, so no forbidden module changed.
- `runs/g4c_d2_p3a_static/input_manifest.json` records the hashes of all sources and frozen inputs used.
- No source changed after the official run.

**Files created or changed:**

| File | Role | Lines (total / logical) |
|---|---|---|
| `sector_check.py` (new) | Independent checker: own annulus radius, barrier, sector and closed-form IK code; rebuilds the world from source records; re-runs the trusted pose-only pick screen; refuses any mismatch | 173 / 155 |
| `sector_cert.py` (new) | Producer, frozen query and control enumeration, zero-call guards and static-op counters, CPU caps, versioned adjudication, science delta, figure | 352 / **309 (≈ the 300 review trigger)** |
| `tests/test_sector_cert.py` (new) | 31 tests (§5) | 228 / 189 |
| `run.py` | One command, `g4c-d2-p3a-static` | +6 |
| `runs/g4c_d2_p3a_static/` (new) | Evidence (below) | 13 manifest files |

Unchanged: `skill.py`, `planner.py`, `motion.py`, `geometry.py`, `certificates.py`, `ordered.py`, `verify.py`, `evaluate.py`, `g4d_run.py`, `g4c_pilot.py`, `d2*.py`, `d2_poc*.py`, configs, and all earlier runs and reports.

The checker is a separate file because independence required it. It shares **no** IK, sector or annulus code with the producer. It shares only the trusted pose screen (`skill.screen_pick`), which the existing `certificates.py` also trusts.

## 2. The theorem as implemented

The proof obligations are recorded in `proof_obligations.json`.

**Scope (A1, as you confirmed):** "infeasible under the declared six-phase 2D skill (48 grasps = 24 tool axes × 2 elbow branches, grasp point fixed at (0.032 m, 0), straight approach) **from this fixed start**". This is never physical impossibility.

**Ingredients:**
- **Barrier.** An object disc whose centre satisfies $\rho < R_0 - \tau$, with $R_0 = L_1 + \max(w_0/2, r_h) + r + \delta - \varepsilon$ = 0.42 + 0.012 + 0.024 + 0.005 − 0.0002 = **0.4608 m**, and τ = 1e-9 (fail-closed).
  - This was verified against `geometry.bodies` (link 0 half-width 0.009 m, housing 1 of 0.012 m at its end) and `geometry.Checker`. A world disc versus link 0 or the housing is COLLISION iff clearance < δ − ε.
  - The resting moved object and the target count as barriers (start world).
- **Free sector.** The open interval of q[0] between the nearest barrier angles around the start q[0], clamped to the joint-1 limits [−3.14159265, 3.14159265] ⊂ (−π, π). Wrap is refused, and so is a start on a barrier angle.
- **Per declared (φ, b), any one of:**
  - `NO_IK`: the independent closed form agrees there is no solution;
  - `DEFINITE_SCREEN:<stage>`: a fresh `screen_pick` rejection with `certified=True`;
  - `SECTOR`: the exact IK q[0] lies outside the sector by more than τ.
- **Certificate.** Issued only if **all 48** candidates are excluded, every claimed reason re-verifies, the family is exactly the canonical 48 in order, and the start (q, open gap, free attachment), world, scene hash, profile, config and constants all match the source.
- **Enabled branches.** Pick sector + pick definite screen: **on**. Place screen: **off**. Place sector: **diagnostic only, never released**. A7, the 2 mm goal tolerance versus exact-centre placement, remains **OPEN**.

**Label scopes:**

| Scope | Covers |
|---|---|
| `ORIGINAL_TARGET` | Empty repair from S0/q0 |
| `SCENE_TARGET_ONLY` | Edited object poses, robot unchanged; hash = the frozen intervention hash |
| `FIRST_ACTION_ORDER` | The first action of an ordered proposal from S0 before any move; adjudicated as **ORDER** scope, never ASSIGNMENT |

Target stages after a relocation are refused by construction.

## 3. The 15 frozen units (`decisions.json`, per candidate in `candidates.jsonl`)

All 15 old labels were UNKNOWN. In "Proved excluded", a candidate can have more than one reason. CPU is per query.

| Unit | Scope | New verdict | Proved excluded (NO_IK / DEF / SECTOR) | Not excluded | CPU s |
|---|---|---|---|---|---|
| `scene:d2_g4c_r00_AB:o05>41` | SCENE_TARGET_ONLY | UNKNOWN | 46/48 (14/22/25) | (270°, −1) q0 55.1° **passes screen**; (285°, −1) q0 64.4° gray band `link2\|o01` | 0.24 |
| `scene:d2_g4c_r00_AS:o04>56` | SCENE_TARGET_ONLY | UNKNOWN | 46/48 (14/19/27) | (285°, −1) gray band; (330°, −1) q0 78.0° **passes** | 0.28 |
| `scene:d2_g4c_r00_AS:o05>48` | SCENE_TARGET_ONLY | UNKNOWN | 47/48 (14/18/25) | (285°, −1) gray band `link2\|o01` | 0.30 |
| `seq:d2_g4c_r00_A:empty` **Q2** | ORIGINAL_TARGET | UNKNOWN | 46/48 (14/17/25) | (270°, −1) **passes**; (285°, −1) gray band | 0.31 |
| `seq:d2_g4c_r00_AB:empty` **Q2** | ORIGINAL_TARGET | UNKNOWN | 46/48 (14/24/25) | (270°, −1) **passes**; (285°, −1) gray band | 0.19 |
| `seq:d2_g4c_r00_AS:empty` **Q2** | ORIGINAL_TARGET | UNKNOWN | 46/48 (14/19/25) | (270°, −1) **passes**; (285°, −1) gray band | 0.28 |
| `scene:g4c_r19:o00>9` | SCENE_TARGET_ONLY | UNKNOWN | 42/48 (20/17/18) | 6 in-sector picks (q0 23°–48°) **pass** | 0.20 |
| `seq:g4c_r19:o00>27` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (0/36/36) | — | 0.29 |
| `seq:g4c_r19:o00>27.o01>28` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (0/36/36) | — | 0.29 |
| `seq:g4c_r08:o00>15` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/17/22) | — | 0.11 |
| `seq:g4c_r08:o00>47` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/17/22) | — | 0.11 |
| `seq:g4c_r08:o00>47.o01>46` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/17/22) | — | 0.11 |
| `seq:g4c_r08:o01>46.o00>47` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/17/19) | — | 0.10 |
| `seq:g4c_r14:o02>39.o00>38` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/19/19) | — | 0.07 |
| `seq:g4c_r14:o02>39.o01>7.o00>38` | FIRST_ACTION_ORDER | **CERTIFIED_INFEASIBLE** | 48/48 (26/19/19) | — | 0.08 |

Every row had `saved_state_identical = true`. The rebuilt start equals the saved invocation or first-action state, and the checker raised no refusal reasons.

**Why every POC_S Q2 query stays UNKNOWN (exact failed premise).** In `g4c_r00` with A at 47.1° (free sector 47.1°–180°), the declared pick **(φ = 270°, branch −1) has q[0] = 55.1°, inside the sector, and passes the pick screen**. The target is therefore pickable under the declared skill. Whatever blocks the task lies on the **place/carry side**:
- The diagnostic place-sector count puts 43 of 48 place configurations outside the carry-world sector.
- The remaining 5 could only be excluded by place-screen rejections, which **A7 keeps disabled**.

So no pick-side theorem can decide these queries.

**What the 8 certificates rest on (checker-accepted).**
- **r08** (`o00` / `o01` from S0): every in-sector grasp is excluded (none for `o00`; 3 for `o01`, `link0|o03`, `link2|o04`). Barriers are `o03` (47.1°) and the resting target `t0` (−33.7°).
- **r14** (`o02` first): barriers `t0` (37.6°), `o03` and `o04`; 3 in-sector grasps hit `link0|t0`.
- **r19** (`o00` first): barriers `o01` and `o02`, sector (6.7°, 180°). Of the 12 in-sector grasps, **8 collide with the neighbour `o01`** (rail ×4, palm ×2, link 2 ×2), 2 with `o02`, 1 with link 0 (`o02`) and 1 with housing 2 (`t0`).

The r19 certificate is about **robot access to `o00`'s grasps**. It is not about destination occupancy (the place side is never used).

## 4. Outcome delta (new versioned adjudication = historical labels + the 8 accepted certificates)

Recomputed with the unchanged judges (`d2_poc.judge`, `g4c_pilot.judge`) in `science.json`. No historical file changed.

| Quantity | POC_S | Pilot |
|---|---|---|
| New ORIGINAL_TARGET negatives | **0** | 0 |
| New SCENE_TARGET_ONLY negatives | 0 | 0 |
| New FIRST_ACTION_ORDER negatives | 0 | **8** |
| Labels POS / NEG / UNK | 32/6/32 → unchanged | 13/26/20 → **13/34/12** |
| Same-endpoint order contrasts | 2 → 2 (both PLACE-occupancy) | 1 → **2**; new: r19 `o01>28.o00>27` POS vs `o00>27.o01>28` NEG (`LINK0_SECTOR_PICK`, ORDER) = **access-based** |
| Decided fixed-robot scene pairs | 4 → 4 | 15 → 15 (no new scene certificates) |
| Decided omission pairs | 6 → 6 | 22 → **42** (nonzero 9 → **12**) |
| Decided nonadditivity cases (all sides decided) | 0 → 0 | 6 → **13** (nonzero κ 1 → **3**) |
| Complete B/C pools | 7 → 7 | 2 → 2. Decided slots: r19 59 → 66/88, r14 78 → 83/96, r08 15 → 23/35 (still incomplete) |
| Q2 / Q3 / Q4 / Q5 (POC_S) | TRIVIAL_ONLY / MET (trivial `+G`) / MET (occupancy) / MET, unchanged | — |

**New measured causal facts (pilot, all sides decided):**
- **r19, `o01>28.o00>27` (POSITIVE).**
  - Omitting `o01>28` leaves `o00>27`, now NEGATIVE: **Δ^O = +1**. Moving `o01` is necessary within this repair, for access.
  - Omitting `o00>27` leaves `o01>28`, NEGATIVE by GOAL_OVERLAP: Δ = +1.
  - Omitting both leaves the empty repair, NEGATIVE: Δ = +1.
  - So **κ = 1 − (1 + 1) = −1**.
- **r14, `o02>39.o00>38` (now NEGATIVE).** Omitting `o02>39` leaves `o00>38`, POSITIVE: **Δ^O = −1**. The extra first action is harmful, because `o02` cannot be grasped first. κ = +1.

**Recovery story (§10 item 6, without any planner call).**
- **r19.** The original task is blocked only trivially (`o00` occupies the goal, GOAL_OVERLAP). The repair must move `o00`. Moving it **first** is certified impossible (access). Moving `o01` first, then `o00`, has a **complete witness**: relocation + relocation + target + SAFE_RETREAT, from G4C-P1 and unchanged.
  - This establishes *trivial original failure → access-constrained ordered repair → executable recovery*.
  - It does **not** establish a nontrivial original-task blockage.
- **POC_S `+A*`.** The story is not established, because Q2 is not met.

## 5. Tests and positive controls

**New tests.** `tests/test_sector_cert.py`, 31 tests, all passed in four standalone runs (≈ 21 CPU-s each). They cover:
- a synthetic certified fixture whose proof needs both sector and in-sector definite screens;
- the annulus boundary: R0 + 4 mm and ρ = 0.465 m refused, R0 − 4 mm accepted, R0 − τ/2 and R0 fail closed;
- two-sided sectors, and a start on a barrier refused;
- a gray-band in-sector candidate blocking the certificate, plus a forged definite claim refused;
- **21 tampering modes** refused: drop, duplicate, reorder, branch, φ, IK q (+1e-6 rad), nominal-path pseudo-proof, place-screen reason, false SECTOR claim, screen record, start q, gap, attachment, world, scene hash, profile, collision policy (δ), barriers, sector, version, scope;
- forged producer status, a moved object, a changed q0 and an added object refused;
- scope rules: target-after-relocation refused, first action of another object refused, no ASSIGNMENT scope;
- joint wrap fails closed;
- the independent IK equals `geometry.ik` over all 48 × 5 anchors;
- a sample of saved witnesses is uncontradicted;
- the guards raise on `planner.plan` and `skill.plan_skill`.

**One real defect was found by the tests and fixed before the official run.** `np.allclose` defaults to rtol = 1e-5, so the checker would have accepted a tampered IK value (+1e-6 rad). All checker comparisons now use `rtol=0`.

**Positive controls** (`controls.json`): every saved witnessed pick at its own actual start.
- 81 distinct starts covering 115 witnesses: 51 target and 30 relocation-action starts; 52 from POC_S, 19 from the pilot, 10 from G4D.
- **0 certificates issued, 0 witness grasps excluded, 0 unmatched witness grasps (all are declared candidates), 0 checker refusals → 0 contradictions.**
- Excluded counts ranged from 24 to 47 of 48. In 2 controls the witness's own grasp was the **only** surviving candidate (POC_S `seq:d2_g4d_R1_AS:o05>40.o04>41` target; pilot `seq:g4c_r10:o01>14.o00>5` relocation 0). These are the sharpest falsification tests passed.

## 6. Resources

**P3a static workflow (cap 900 CPU-s, 60 per query, 1 worker, 1,800 s wall).**

| Item | CPU s | Wall s |
|---|---|---|
| Official adjudication (attempt 2), whole process | 43.3 | 36.4 |
| … of which queries + controls | 34.7 | 34.7 |
| Attempt 1 | 42.0 | 35.1 |
| Four test runs | ≈ 85 | — |
| Two development probes | ≈ 20 (estimate) | — |
| **Total** | **≈ 190** | — |

- **Attempt 1** finished the full computation, then **crashed while writing results**: numpy `bool` was not JSON-serializable. It wrote no decisions. Its partial files are preserved in `crashed_attempt_1/` with `CRASH.txt`.
- Per-query maximum: 0.31 CPU-s for frozen queries, 0.66 for controls.
- **Static operations counted** (official run): IK 56,278; `screen_pick` 192; distance evaluations 87,268; `geometry.certify` 37,426.
- **Guarded calls: `planner.plan` 0, `skill.plan_skill` 0, `evaluate.evaluate_target` 0, `evaluate_safe_retreat` 0, `home_diagnostic` 0, `verify.relocate` 0, `verify.plan_fixed_order` 0, `ordered.teach_sequence` 0.**

**Regression and replay phase (separate cap 300 CPU-s).**

| Item | CPU s | Wall s | Result |
|---|---|---|---|
| Six archived replays (scratch reports) | 84.1 | — | **all pass** (77/77/2/50/20/257) |
| Full suite | **235.7** | 229.9 | **157 of 247 passed, 0 failed, 90 not run** |
| **Phase total** | **319.8** | 273 | **cap exceeded by 19.8** |

- The full suite was run with the pytest process limited to the remaining 215 CPU-s (`ulimit -t`). The kernel killed it at that limit; 235.7 CPU-s includes about 20.7 CPU-s in test subprocesses, which that per-process limit did not cover.
- **Result: `REGRESSION_NOT_COMPLETED`**, and the phase exceeded its 300 CPU-s cap by **19.8 CPU-s**. The cause was that my limit covered only the parent process, not test subprocesses. This is a budget breach in the regression phase, not in the adjudication.
- The planner-call counter plugin was killed before writing, so **this phase's planner calls were not measured**. The historical baseline is 621 `planner.plan` / 60 `plan_skill`.
- Not reached: tests from `test_protocol.py` (alphabetically) onward, including the 31 new tests. Those passed in their standalone runs.

## 7. Verdicts (strict)

| Gate | Verdict | Reason |
|---|---|---|
| `P3A_VALIDATED_CERTIFICATE` | **NOT DECLARED** | Met: independent checker, proof obligations, 31/31 new tests, 0 contradictions, static caps, zero calls. **Not met:** the full regression did not complete within its cap, and that phase overshot by 19.8 CPU-s. |
| `P3A_Q2_MET` | **NOT MET** | 0/3. An in-sector pick passes the screen, so the obstruction is place-side and A7 is disabled. |
| `P3A_ACCESS_ORDER_MET` | **MET (checker-accepted)** | r19 `o00>27` first action certified at ORDER scope; the swapped order `o01>28.o00>27` has a complete witness; the proof is pick-access, not occupancy. |
| `P3A_CAUSAL_EFFECTS` | **+20 decided omission pairs (+3 nonzero), +7 decided nonadditivity cases (+2 nonzero κ), 0 new scene effects** | Pilot only |
| `P3A_FUTILITY` | not triggered | 8/9 pilot certified |
| `P3A_FAILED_SAFETY/INTEGRITY` | **none** | No false negative, no theorem counterexample, no scope failure, no source mutation, no call violation |

**Label status.** The 8 new negatives are checker-accepted and stored **only** as this stage's versioned adjudication (`decisions.json`, `science.json`). I recommend holding them out of any training release until the regression gate is completed under an authorized budget.

**Remaining UNKNOWNs.**
- **POC_S: 32 (unchanged).**
  - 6 frozen queries (place side needed);
  - 9 post-relocation target stages (out of scope by theorem);
  - 17 expensive `g4d_R1`/censored queries (not attempted, as instructed).
- **Pilot: 12.**
  - 8 are S0-start queries:
    - `seq:g4c_r19:o00>9`, `o00>9.o01>27`, `o00>9.o01>28`. These share the **same** certified `o00` pick-from-S0 proof but were outside the frozen list, so they were not transferred.
    - `seq:g4c_r14:o00>6`, `o01>7.o00>38`, `o01>7.o02>39.o00>38`.
    - The fixed-robot `scene:g4c_r08:o00>47` and `o00>47.o01>46`.
  - 3 are later-action failures (r14 `o00>38…`), and 1 is the scene edit `scene:g4c_r19:o00>9`, whose in-sector picks pass.

## 8. P3b proposal (not executed; needs your authorization)

**What P3a measured that P3b should use:**
1. Pick-side certificates fire when the moved object's every in-sector grasp is body-blocked (r19) or when no grasp is in the sector at all (r08).
2. In `g4c_r00`-type original-target scenes the target stays pickable, so a nominal-sweep blocker cannot yield a pick-side certificate.
3. A static check costs about 0.3 CPU-s per query, so admission screening is nearly free.

**Constructor ("static-certifiability-first", about 150 lines).**
- Start from 4 fresh J0 bases: predeclared seeds, target at ρ 0.5–0.65 m (avoid ρ < L1 = 0.42 m, given the `g4d_R1` cost), q0 = home.
- Enumerate single and double obstacle insertions in a fixed order. **Admit a variant only if `sector_check` certifies the ORIGINAL_TARGET from q0**, which requires both:
  - every in-sector target grasp definitely body-blocked by an inserted neighbour (r19-like); and
  - the sector bounded by an annulus barrier.
- Require a predeclared repair that moves one blocker out of the annulus (ρ > 0.4608 m) or away from the target's grasp neighbourhood. Its witness is the only planner use.
- For order: two objects X and Y where X is first-action certified with Y present (r19 pattern), and Y then X is plausible.
- Scene edits and omissions come from the frozen D2 catalogue rule. Count nonadditivity only with four decided sides.

**Proposed budget** (per 0017 §10; all extrapolated from POC_S `g4c_r00`-type units):

| Limit | Value |
|---|---|
| Queries | ≤ 84 (4 bases × ≤ 20 units + 4 base witnesses) |
| CPU | 900 per unit, cancellation at 870; aggregate ≤ 9,000 |
| Workers | 1 |
| Wall | 1,800 per unit; ≤ 12,000 overall |
| Planner | 4,000 nodes unchanged |
| Calls | relocation ≤ 100, target ≤ 84 |
| Static admission | ≤ 600 CPU-s, zero planner |

**Kill gates.**
- No admitted variant after 2 bases ⇒ stop, with no planner CPU spent.
- Any positive contradicting an issued certificate ⇒ fail.
- Two search-limit units on one root ⇒ stop that root.

**Dataset-ready criterion (for a later release).** Per root, every active z slot of every declared sequence decided:
- a nontrivial certified original-target negative, plus a same-root complete recovery witness;
- at least one access-based order pair;
- decided omissions.

Unknowns are kept in the audit, never in supervision.

**Also needed (separate decisions):**
- (a) Complete the regression gate with a realistic cap: ≈ 400 CPU-s for 84 replay + ~290 suite + ~25 subprocess CPU-s.
- (b) Optionally, transfer the certified S0 pick proofs to the 8 S0-start pilot UNKNOWNs listed in §7. This is ≈ 3 CPU-s, zero planner.
- (c) Resolve A7 (a place-side proof robust to 2 mm), which would be required for the POC_S `+A*` Q2 rows.

## 9. Commits

- `512259299ebaab5afdd5403edaf86c4359fda1ee`: report 0017 only.
- The P3a commit stages exactly `sector_cert.py`, `sector_check.py`, `tests/test_sector_cert.py`, `run.py`, `runs/g4c_d2_p3a_static/` and this report.
- Both commits are pushed without force. Hashes and remote verification are given in chat and recorded in report 0019.
- The deleted PDFs and instruction files are not staged.

**STOP.** P3b, POC_F, the transfer adjudication and the regression rerun all need your separate authorization.
