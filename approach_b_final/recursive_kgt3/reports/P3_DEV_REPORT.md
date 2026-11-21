# Recursive K>3: P0–P3 development report

Branch `naren/kgt3-recursive` (local only, **not pushed**). No release_v2 TEST scene was touched. All run outputs are in `/home/naren/kgt3_runs/` (persistent: the session's scratch was lost in two VS Code crashes, see Deviations).

## 0. Verdict: **REVISE. Do not proceed to TEST with this design.**

On 25 sealed DEV engineering scenes (K4 ×8, K5 ×4, K6 ×4, K9 ×8, K12 ×1), **every arm achieved 0/25 physical successes**: the recursive planner (REC), its declared variant (REC2), budget-matched flat search (FLAT), the matched random control (RAND) and the frozen K≤3 model (B0). The pre-registered criterion for "useful recursive guidance" fails on all three counts:
- REC does not beat FLAT or RAND (0 discordant pairs);
- the D1 lower bound is below 0.5;
- only D3 passes.

**This is a negative result for the method as designed.** The diagnostics show *where* it breaks:
- **The frozen models do carry local enabling-action information inside temporary-target subproblems:**
  - temporary-target Y: AUROC 0.80 [0.74, 0.85];
  - enabling-mover ranking: 0.78 [0.76, 0.80];
  - 86% of inserted enablers are true blockers.
- **They carry no usable information about which objects to move for the original K>3 target:** AUROC 0.51 [0.37, 0.64].
- **The final-Y head gives false-high scores to too-short endpoints, and the ranking energy penalises length.** Together these stopped every planner short: committed plans were shorter than the certified minimum K in 21–24 of 25 scenes, which guarantees failure.

## 1. Implementation status and tests

| Phase | Status | Evidence |
|---|---|---|
| **P0** frozen parity and dynamic objects | **PASS**: hashes 10/10; **751/751 VAL roots exact** (max \|Δp11\| 1.2e-7); 25–28 objects finite and legal | `reports/P0_PARITY.json`, §7 |
| **P1** temporary-target adapters | **PASS** | On all 751 VAL roots: identity 751/751; round trip 4,254/4,254; original target never movable 4,254/4,254; original goal and temporary goal illegal 4,254/4,254; reserved objects and cells excluded 4,254/4,254; task context consistent 4,254/4,254; 6/6 legality rejections (`P1P2_TESTS.json`). |
| **P2** recursive compose-and-rank planner on mocks | **PASS** | REC solves the K4/K6/K9/K12 synthetic chains at exactly the minimum length (7/27/59/91 local calls); FLAT fails all four; a hidden enabler makes REC fail; same endpoint → same Y, different X. Visual trace: `figs/P2_mock_traces.png`. |
| **P3** DEV diagnostics | **DONE** (negative) | `eval/DEV_SUMMARY.json`, `eval/per_scene.jsonl`, `figs/P3_DEV_summary.png`, `figs/dev_scenes/*.png` |

**Protocol checks:**
- Pre-registration (`DEV_PREREG.md`) and `dev_config.json` were committed (`028d7523fc`) **before any DEV prediction**.
- The rebuilt DEV inputs are byte-identical to the registered SHA-256 (`70ad98a9…`).
- Each arm was sealed (`SEAL.json`, predictions SHA) before `dev_verify.py` ran.
- Planner processes ran behind the path guard with zero teacher calls.

| Arm | Seal (prediction SHA prefix) |
|---|---|
| REC | a61e6fd9 |
| REC2 | d2596af0 |
| FLAT | f731dc0a |
| RAND | a55c045c |
| B0 | c093eba4 |

## 2. Paired results and exact compute

Physical success = teacher_long X = 1 and Y = 1 on the committed plan (163 teacher verifications in total).

| Arm | Success | Plans < certified K | Mean \|r\| | Local-generator calls (mean) | Temp-target probes (mean) | Local candidates scored (mean) | Wall s (mean) | Stop reasons |
|---|---|---|---|---|---|---|---|---|
| B0 frozen K≤3 | **0/25** | 16/16 REPAIR (9 ABSTAIN) | 1.72 | 1 (full K≤3 enumeration) | 0 | full | 12.2 | – |
| FLAT (B_top 12) | **0/25** | 21/25 | 3.68 | 7.1 | 0 | 75,315 | 5.2 | FRONTIER_EMPTY 25 |
| RAND (random proposals, scores, gates; frozen final energy) | **0/25** | 16/25 | 4.84 | 150 | 1,691 | 2.63 M | 62.1 | LOCAL_CALLS 25 |
| **REC** (pre-registered) | **0/25** | 24/25 | 2.76 | 128.2 | 2,764 | 1.33 M | 158.1 | LOCAL_CALLS 11, WALL 14 |
| REC2 (declared variant D-1) | **0/25** | 21/25 | 3.68 | 85.4 | 1,471 | 0.83 M | 96.9 | FRONTIER_EMPTY 12, LOCAL_CALLS 8, WALL 5 |

Caps for every arm: ≤150 local calls, ≤4,000 probes, ≤180 s, ≤12 rounds, |r| ≤ 12.

- **Paired exact sign tests:** REC vs FLAT, REC vs RAND, REC2 vs FLAT, REC2 vs RAND, REC vs REC2 and FLAT vs RAND all have **0 discordant pairs** (p = 1).
- **B2/B3 re-rankings** of the REC/REC2 candidate pools (λ_X = 0 Y-only; X-only): **0/25** each.
- **REC2's committed plan equals FLAT's in 25/25 scenes.** The recursion did produce candidates with inserted enablers (31 insertion events), but none ever won the final ranking.

## 3. Is there recursive guidance in the frozen models?

All label-dependent analyses were run post-seal. Labels come from the construction-time kill-table relaxation (MINK_STATIC_V2) and the certified witnesses.

| Diagnostic | Result | Reading |
|---|---|---|
| **D1** original task at S0: frozen best-K1 p11 ranking of useful movers (U = union of all minimal goal sets) | **AUROC 0.51 [0.37, 0.64]**, 12 scenes with both classes | **No information.** For a target needing ≥4 relocations, every ≤3-move hypothesis is infeasible, so the frozen head cannot tell helpful movers from irrelevant ones. |
| D1 witness movers W | 0.54 [0.43, 0.65]; recall@8 0.50 vs chance 0.45 | No information |
| **D2** final h_Y (Y-only vs S0): witness endpoint vs 20 random same-size sets | **0.73 [0.57, 0.87]**; mean h_Y witness 0.59 vs random 0.32 | Some information, but **false-high on short endpoints**: FLAT's 1–3-move plans scored h_Y 0.73–0.996 on K4–K6 scenes, ending its search early (FRONTIER_EMPTY after 1–9 rounds) |
| **D3** temporary-target ŷ(A→d) at S0 against static feasibility | **0.80 [0.74, 0.85]** | **Informative ranking** |
| D3 on logged in-search probes | REC 0.71 (n = 69,131), REC2 0.73 (n = 36,681) | Informative, but **miscalibrated by an order of magnitude**: mean ŷ 0.077 for feasible vs 0.009 for infeasible. A 0.5 gate flags almost every action as blocked, which caused REC's budget starvation. |
| **D4** temporary-task enabling-mover ranking (frozen K1 p11) against true pick blockers of A at S0 | **0.78 [0.76, 0.80]**, 398 calls | **Genuine enabling-action information in relative local rankings** |
| **D5** inserted enablers that are true blockers of their dependent action (S0 insertions) | **169/197 = 0.86** | Recursion inserts the right objects locally |
| D6 search exhaustion | see §2 stop reasons | REC never left round 1 (25/25 scenes: 1 round); REC2 reached 1–3 rounds; FLAT stopped on false-high h_Y |

**Answer:** the frozen K≤3 models contain **statistically clear and practically meaningful *local* guidance** (D3, D4, D5), wherever the remaining dependency fits their ≤3-move horizon. They contain **no guidance for the original long-horizon target** (D1). And their final-Y estimate is **unreliable exactly where K>3 needs it** (false-high short endpoints). Under this design, the useful local signal never turns into a correct global plan.

## 4. Failure breakdown (pre-registered order, first applicable)

| Arm | NOOP / ABSTAIN | **Ingredient** (static endpoint Y dead) | Composition (static order invalid) | Execution (X = 0) | Final Y | Success |
|---|---|---|---|---|---|---|
| B0 | 9 | 15 | 1 | 0 | 0 | 0 |
| FLAT | 0 | 24 | 1 | 0 | 0 | 0 |
| RAND | 0 | 22 | 3 | 0 | 0 | 0 |
| REC | 0 | 24 | 1 | 0 | 0 | 0 |
| REC2 | 0 | 24 | 1 | 0 | 0 | 0 |

Every failure is caught by the static relaxation before physics: the committed movers never cover a minimal goal set. That follows from committed lengths below K, plus the D1 null (wrong movers). The teacher verification agrees: no plan has X = 1 and Y = 1. Of the 163 verified plans, 22 reached Y = 1 with X = 0, and 13 reached X = 1 with Y = 0.

**Root causes, in order of impact:**
1. **The energy prefers short plans.** C(r) = −log h_Y + Σ_chunks −log h_X. Each extra chunk adds a non-negative cost, λ_m = 0 gives no reward for completeness, and h_Y is false-high on short endpoints.
2. **Early termination on false-high h_Y ≥ 0.5** (FLAT, REC2).
3. **Budget starvation of REC** in round-1 recursion: the miscalibrated ŷ suspects almost every action, and its subgoals never reach 0.5.
4. **No original-task mover signal** (D1). Even complete-length plans pick the wrong objects; REC's one K-length plan in this example was ingredient-dead.

## 5. Visualizations

All under `/home/naren/kgt3_runs/figs/`; key ones are copied to `reports/figs/`.

| File | Shows |
|---|---|
| `P2_mock_traces.png` | mock dependency DAGs, REC insertions and composed order vs FLAT (successful recursive searches on mocks) |
| `P3_DEV_summary.png` | outcome and failure classes per arm; committed length vs certified K; diagnostic AUROCs with CIs |
| `dev_scenes/<root>.png` (25) | committed plans of REC / REC2 / FLAT / RAND on the grid with post-seal relaxation labels |

Examples: `ENG2_01bacd0a7b91.png` (K5: REC commits exactly 5 moves with h_Y 0.82 but the wrong ingredients) and `ENG12_17ff1743fd83.png` (K12: all arms commit 3–6 moves).

There are **no successful real recursive searches to show**, because none succeeded.

## 6. Deviations from plan.md and DEV_PREREG (with justification)

| ID | Deviation | Justification and effect |
|---|---|---|
| D-1 | **REC2** added after observing *model-side* behaviour on the first DEV scene (no label read): REC spent 150 local calls inside round-1 recursion. REC2 adds a rank-based suspect rule, a per-insertion cap of 4, a gain-based subgoal acceptance and D_max = 2. | REC stays the pre-registered primary; both are reported. Both are 0/25. |
| D-2 | Two VS Code crashes. VS Code is a **Flatpak**, and its sandbox kills child processes and its private `/tmp`. The scratch outputs, DEV inputs and venv were lost. | The DEV inputs were rebuilt from the original engineering sources and are **byte-identical to the registered hash**. The ENG12 witness was re-derived deterministically (CERTIFIED, 33 queries, as before). Runners were made resumable (deterministic per-scene traces). The owner then relaunched the jobs on the host (`host_launch.sh`). No label had been read at either crash. |
| D-3 | Helper workers (scene sharding) were added for speed, under higher GPU contention. **REC hit the 180 s wall cap in 14/25 scenes** (before the crash: LOCAL_CALLS). | The wall cap is part of the registered budget. REC was round-1-starved under both stop types (its pre-crash first scene: 150 local calls → 1 candidate of length 3). The conclusion is unaffected. |
| D-4 | K4–K6 DEV witnesses were taken from `certs_e` + `certs_g` (16 rows) instead of the `eng_certs16` re-check file (lost with scratch). | Same scenes and certified K. Witnesses are used only for D1-W. Public inputs are unchanged (hash-verified). |
| D-5 | D4/D5 are restricted to S0-scene local calls and insertions (prefixes of deeper calls were not logged). | 398 calls and 197 insertions still give tight CIs |
| D-6 | Python is the miniconda `python3` (torch 2.9.1+cu128) instead of the lost scratch venv (same torch build). | P0 parity re-run under it |
| D-7 | A3/A4 implementation details: K2/K3 over top-L = 8 movers by K1 p11; ≤2 hypotheses per first mover; the reservation mask also covers pending destinations. | As amended; tested in P1/P2 |

## 7. P0 full parity (751 VAL roots, DynPad active)

**PASS** (`reports/P0_PARITY.json`):

| Check | Result |
|---|---|
| Bundle hashes | 10/10 |
| Proposals, decisions and moves identical to the recorded frozen predictions | **751/751** (0 mismatches) |
| max \|Δp11\| / max \|Δp_noop\| | 1.19e-7 / 1.19e-7 (float precision) |
| Synthetic 25/26/27/28-object scenes | finite, every mover has a legal top-4, scores finite |
| Full K≤3 candidate count at 25 / 26 / 27 / 28 objects | 491,478 / 637,270 / 625,568 / 723,592 |

The run used DynPad, which is the identical code path for ≤20 objects. It was completed after the crashes by resumable per-row checks, with the last rows computed by 6 parallel shards and merged by root id. Rows are deterministic.

## 8. What can and cannot be claimed

- **Supported:**
  - the adapters, reservation mask and recursive composer are correct and parity-preserving (P1/P2);
  - frozen temporary-target and enabling-mover signals are informative locally (D3/D4/D5);
  - the frozen original-task scorer is uninformative for K>3 mover selection (D1);
  - the frozen final-Y is false-high on short K>3 endpoints (D2 plus FLAT termination).
- **Not supported:** any claim that recursively composing the frozen K≤3 models solves K>3 tasks. DEV success is 0/25 for every arm, including flat and random controls.

**Revision options.** Each changes the method and needs owner approval; none involves retraining.
- (a) A length- and coverage-aware ranking. For example, terminate only on static-free criteria, or rank complete-length candidates without a per-chunk penalty.
- (b) Rank-based, not threshold-based, temporary-target gates with budgeted fair allocation.
- (c) Seed the top level from temporary-target decompositions of the *target's own pick and place*, where D4 shows informative rankings, instead of original-task p11 (D1 null).

Even with (a)–(c), D1 says the frozen models do not themselves know which objects block a K>3 target. Recovering that information would need either a learned signal (training, currently not authorised) or a construction-time oracle (forbidden in the method).
