# 0105 — Approach D G4: local witness-grounded motion coverage and causal repair evaluation

**Authority:** `approachD_G4_local_witness_catalog_and_causal_repair_instructions_v1_0.md`.
**Branch:** `approach-d-v1`, starting at HEAD `99587dea3`. That commit is G3 `804e3ddf7` plus a one-line status-file scrub.
**Scope:** local workstation only. Existing P13–P17 2D archives, frozen Dp17 and frozen catalog C3.
**Not done:**
- no server use;
- no new scenes or labels;
- no retraining;
- no runtime IK, planning or motion generation;
- no sealed 442-query run;
- no use of the 7-action protocol.

**Previous turn sync:** pushed `approach-d-v1` = `99587de` and `dataset-bd-v1` = `cd365b5` to `origin`, per the user's standing instruction that every update goes to `Narendhiranv04/latent-causal-tamp`.

## Verdict

| Claim | Evidence | Status |
|---|---|---|
| Original G3 baseline reproduced | Saved hashes in `runs/approach_d/g4/baseline/BASELINE.json`. All 5 G3 policies were re-run on C3 under the G4 code. Their per-root traces equal the saved `VIEW_B_C3` traces event for event (test-enforced). Result: 1/12 repaired, 0 forbidden calls. | **PASS** |
| Teacher-witness chain reconstructed by stored motions | 30/30 DEV witness sequences (11 roots) execute from W-ROOT stored records with full independent replay. That covers **9/9 blocked roots with a known witness**. | **9 blocked roots.** Engineering ceiling only: compiled from each root's own witness. |
| Cross-root motion transfer | The W-TRANSFER ceiling on blocked DEV roots is **0/9**. Of 96 transfer actions, only one target pair matches a DEV task. | **Coverage-censored** (no leakage: test-enforced) |
| D learned counterfactual value | Historical held-out P16-calib edit AUROC: 0.949 (D) vs 0.781 (geometry). New G4 evidence, limited to development roots: on the two roots where D's ranking failed on W-ROOT, the placements D preferred are **teacher-VERIFIED**. | **Positive (unchanged)**, plus a development observation |
| D versus geometry full repair advantage | On W-ROOT (development demonstration), blocked roots repaired: D_CAUSAL_G3 6/10, D_CAUSAL_G4_SWEEP 6/10, D_BLOCKER_ONLY 8/10, GEOM_CAUSAL 8/10, UNIFORM 7/10. W-ROOT's stored T motions are witness-specific. | **Inconclusive** (negative on a confounded development catalog; no clean test possible locally) |
| Runtime solver-free and regressions | 0 forbidden calls in every diagnostic and evaluation; 11/11 G4 tests; full suite 565/565 + 6/6 replays (`P3A_REGRESSION_CLOSED`) | **PASS** |

## 1. What G4 separates

1. **Teacher feasibility.** The historical P16 teacher (`DetPhysics` + `verify_sequence`, deterministic node budgets, label budget) VERIFIED a specific sequence from a specific occupancy and start q.
2. **Library realizability.** The solver-free provider executes a chain from stored records only. Each record is re-certified in the current scene, and the whole chain replays with bitwise q continuity.
3. **Policy effectiveness.** A search policy finds a realizable repair under a common budget, without the teacher sequence as a hint.

F12 (`p13_2026216000`) stays a **one-relocation** verified repair (`o00>59`, test-enforced). Nothing here labels it K2.

## 2. G4.0 baseline (Gate 0: PASS)

- **Fingerprints** (`BASELINE.json`): C3 graph hash `sha256:c3ae684f…`, its arrays hash, `config.toml`, the overlay, DEV plan and keys, DEV labels, the three Dp17 checkpoints, and `VIEW_B_C3.json`.
- **Approach D tests before any G4 change:** 52/52 pass (`baseline/APPROACH_D_TESTS.txt`).
- **Reproduction finding.** My first G4 edit to `ad_causal.search` placed the new demotion block between `if usesD_place:` and its `elif`. That silently re-sorted D_CAUSAL_G3's candidates geometrically. The divergence was caught by diffing the re-run C3 traces against the saved G3 file, and it is fixed. A permanent test now requires event-identical G3 traces on C3 for D_CAUSAL_G3, GEOM_CAUSAL, D_BLOCKER_ONLY and UNIFORM. Every number below is from the fixed code.

## 3. G4.1 witness inventory (read-only; `manifest/WITNESS_MANIFEST.json`)

| Cohort | Content |
|---|---|
| **A (fixed DEV, 12 roots)** | 30 historically VERIFIED sequences on 11 roots: 2 empty (teacher-direct roots `…210004`, `…211000`), 11 one-move, 17 two-move. These are label sequences plus the P16 tag-search plans. `p13_2026210001` has no known witness. Trajectories were *not* archived (statuses only). |
| **B (12 train roots, ≥ 2 moves)** | Fixed sha order. All 12 lie inside the transfer pool, so they are reconstructed there; no separate compile. |
| **Transfer pool** | All 32 train roots with any verified witness, in root-id order, disjoint from DEV (asserted). |

**Disclosure.** Dp17 was trained on splits that include DEV (`train, dev, p17train`). DEV results are a catalog/library test, not a clean D-generalisation test.

## 4. G4.2 offline catalogs (`runs/approach_d/g4/catalogs/`)

**Reconstruction.** I re-ran the historical teacher with the same physics, P14 lookup index and `LABEL_BUDGET`, on the listed VERIFIED sequences. It is deterministic.
- All 30/30 DEV sequences re-VERIFY and pass the historical independent `p16_motion.replay`.
- The historical steps were: 19 lookup + direct transit, 10 lookup + planned transit, 5 lookup with no transit needed, and 11 online plans. The lookup records themselves came from *other* P10b/P13 roots' libraries.

**Pieces.** Each record is cut at existing waypoints into object **cores** (approach … retreat) and free-arm **connectors**. Consecutive free legs (transit + pregrasp lead-in) are concatenated bitwise, with no new waypoint. Every piece is validated in the scene of its own stage (`certify_action` / `certify_free`):
- 150/150 DEV pieces pass: 75 connectors, 45 relocation cores and 30 T cores.

**Catalogs.**
- **W-ROOT** = C3 + 62 connectors + 26 relocation cores + 28 T cores (after deduplication). It is an engineering ceiling: built from each root's own witness.
- **W-TRANSFER** = C3 + 32 train roots × the first 2 witnesses (56 sequences, all re-verified and replayed) → 98 connectors, 40 relocation cores and 56 T cores, plus 156 offline empty-workspace home connectors (the G2a EXACT_CELL_WITNESS representation). No DEV label, sequence or trace is read.
- **Provenance.** Witness actions carry `origins = [W_ROOT_WITNESS]` or `[W_TRANSFER_WITNESS]` plus root, sequence and piece. They never mix (test-enforced).
- **Provider order.** The provider's candidate order puts stored witness cores first (`WitnessFirst`), identically for every policy.

**Compile ledger** (`COMPILE_LEDGER.json`; caps 400 invocations / 1200 CPU-s): **306 invocations, 1086 CPU-s**, under both caps.

| Ledger entry | Invocations | CPU-s |
|---|---|---|
| Teacher re-run, W-ROOT | 59 | 453 |
| Teacher re-run, W-TRANSFER | 85 | 494 |
| Home connectors | 156 | 1 |
| Teacher check of D's preferences (§7) | 6 | 138 |

The transfer reconstruction was limited to 2 witnesses per pool root, in fixed order, with 250 CPU-s held back for the connectors. That rule was declared before running, and uses no DEV information.

## 5. G4.3 motion-availability diagnostic (`diagnostics/AVAILABILITY.json`; figure 01)

Each archived DEV witness sequence was pushed through the provider step by step (sequence supplied **for diagnosis only**). 0 forbidden calls.

| Catalog | Witness sequences fully executed | Every relocation stored + certified | A stored T core clear after the repair | Blocked-root ceiling |
|---|---|---|---|---|
| C3 | 1/30 | 11/30 | 17/30 | **0/9** |
| **W-ROOT** | **30/30** | 30/30 | 30/30 | **9/9** |
| W-TRANSFER | 1/30 | 11/30 | 17/30 | **0/9** |

- **First failures on C3 (29 sequences):**
  - 11: per-move check budget exhausted (6 stored candidates collide);
  - 7: blocked entry connector;
  - 6: no template for the pair;
  - 5: relocation-core collision.
- **W-TRANSFER** changes only the mix: 7 relocation-core collisions and 4 missing templates.
- **F12 (figure 03).** After o00 → 60 (G3's choice) *and* after o00 → 59 (the teacher's choice), C3 has 7/15 stored T cores that are clear in that occupancy. But from the relocation's own q_end, T fails with 4 entry-connector collisions and 2 core collisions, which exhausts the 6-check budget. The binding gap is **connectors / q continuity**, not the T core. On W-ROOT, the witness's own connector + T core certify.
- **Search universe.** 2/30 witness sequences use a destination outside G3's universe (first 4 scene-only slots per mover): `…210000` o02 → 62 (its only witness) and `…216000` o00 → 61 (an alternative). **`p13_2026210000` therefore cannot be found by any policy**, even on W-ROOT.

**Gate 3:** W-ROOT has a nonzero blocked-root ceiling, so policy evaluation proceeds there as a development demonstration. W-TRANSFER is **coverage-censored**: no transfer efficacy experiment was run.

## 6. G4.4 opt-in stored-sweep safeguard (`D_CAUSAL_G4_SWEEP`)

**Rule.** For a candidate placement (o, d, m), take the stored original-T motions of the current T pair whose sweep (core + its stored entry leg) avoids every non-mover object: these are the "compatible" ones. If at least one exists and **all** of them sweep d, the candidate is **demoted** to the end of that mover's list. Nothing is dropped. Interleaving and widening keep every candidate reachable.

There is no learned head, loss or optimiser, and G3's policy is unchanged.

**Tests** (fixtures):
- It changes a concrete choice (D's top slot inside every T sweep → the next slot).
- It still reaches a valid two-step repair whose intermediate placements are *both* demoted.
- It never turns a failed motion into a successor.

**Real roots.**
- The rule fired on 69/438 candidates (C3) and 48/314 (W-ROOT).
- For 297/438 candidates, no compatible stored T sweep exists, so the rule is silent.
- **It changed no root outcome:** 6/10 for both D variants on W-ROOT, with relocation certifications 190 vs 191.
- On F12 nothing was demoted at the first frontier (figure 04). There, D's top placement (60, p_T 0.78) relocates fine; the T-side failure is connectors, not sweeps.

## 7. G4.5 matched policy evaluation (`eval/EVAL_C3.json`, `eval/EVAL_W_ROOT.json`; figure 05)

**Setup.** Identical across policies: 12 roots (none filtered), catalog, universe, beam 3, depth 2, widening [2, 4, all], 60 relocation certifications and 30 expansions per root (global across widening), and provider action budget 6. D-call cap 200, as resource accounting.

**Root sets.**
- "Blocked" = the 10 roots whose original target is not teacher-VERIFIED.
- "Ceiling" = the 9 blocked roots with an executable witness on that catalog.

| Policy | C3 all | C3 blocked | **W-ROOT all** | **W-ROOT blocked** | W-ROOT within ceiling | Reloc certs (W-ROOT) | D calls |
|---|---|---|---|---|---|---|---|
| D_CAUSAL_G3 | 1/12 | 0/10 | 8/12 | 6/10 | 6/9 | 191 | 201 |
| D_CAUSAL_G4_SWEEP | 1/12 | 0/10 | 8/12 | 6/10 | 6/9 | 190 | 201 |
| D_BLOCKER_ONLY | 1/12 | 0/10 | 10/12 | 8/10 | 8/9 | 173 | 28 |
| GEOM_CAUSAL | 1/12 | 0/10 | 10/12 | 8/10 | 8/9 | 191 | 0 |
| UNIFORM | 1/12 | 0/10 | 9/12 | 7/10 | 7/9 | 193 | 0 |

**Notes.**
- **Failures.** Every policy fails `…210000` (outside the search universe) and `…210001` (no known witness). Both D-placement policies also fail `…217000` and `…218000`. UNIFORM also fails `…212000`.
- **Motions used.** Every successful W-ROOT repair uses only witness cores (W actions). No C3 motion completed a repair anywhere.
- **CPU per policy** is wall-noisy: parallel workers, and the first policy in each process pays the model load. I do not compare it.

**Why D's counterfactual ranking lost on W-ROOT**, inspected per root:
- **`…217000`.** D scores o01 → 45 (0.99) and o00 → 44 (0.94) above the witness o00 → 45 (0.87). W-ROOT stores T motions only for witnessed post-states, so D's choices have no stored T motion, and the beam (3) fills with them. Geometry's stored-sweep conflict happens to rank o00 → 45 first, because the stored T sweeps *are the witness's own*.
- **`…218000`** is a two-blocker root. Every single move has p_T ≈ 0 (correct: no single move suffices), so D's depth-1 order falls back to travel. At depth 2 it again prefers placements (o00 → 44) without a stored T core.
- **Offline teacher check** (6 invocations, ledgered; `diagnostics/TEACHER_CHECK_D_PREFERENCES.json`):

| D's preferred placement | Teacher status |
|---|---|
| `…217000` o01 → 45 | **VERIFIED** |
| `…217000` o00 → 44 | **VERIFIED** |
| `…218000` o01 → 60, o00 → 44 | **VERIFIED** |
| `…218000` o01 → 59, o00 → 44 | UNKNOWN_PLANNER (not infeasible) |

**Reading.** D's preferences were physically right. They lost because the library lacked the motions for those states. Meanwhile geometry ranks with sweeps that are themselves witness-derived. On W-ROOT this comparison is **confounded in geometry's favour**. It is not evidence that D's counterfactual ranking is worse, and it is not evidence that it is better.

## 8. What each part contributes, and what remains impossible

- **Learned D.**
  - It picks which obstacles to investigate, and scores counterfactual feasibility of the original T at each stored motion's q_end.
  - Held-out evidence (0.949 AUROC) is unchanged.
  - New development evidence: its top placements on the two W-ROOT failures are teacher-VERIFIED.
  - It does **not** know which motions the library holds, so it can prefer correct but unrealizable placements.
- **Swept-volume geometry.**
  - Stored-sweep conflict is cheap and library-aware, so it aligns with whatever the catalog can execute. On W-ROOT that alignment is partly inherited from the witness.
  - The G4 demotion rule is a safe, non-vetoing variant. It never helped or hurt an outcome on these roots.
- **Motion library.**
  - It is the binding constraint. C3: 0/9 blocked repairable even with the teacher sequence supplied. W-ROOT: 9/9.
  - The gap is mostly **entry connectors from the actual q** and **per-state target motions**, not obstacle relocations.
- **Remains impossible locally.**
  - *Transfer.* Root-disjoint train witnesses share almost no absolute (src, dst) pairs with DEV, so W-TRANSFER is coverage-censored.
  - *`…210000`* needs a destination outside the declared search universe.
  - *`…210001`* has no known repair.
  - *A fair learned-advantage test* needs a library that is (i) not built from the evaluation roots' witnesses and (ii) dense enough per state. The local 2D archive cannot provide that within G4's bounds.

## 9. Tests and regression

- **`tests/test_approach_d_g4.py`: 11/11 pass**, covering:
  - original T + exact q_end in every D call;
  - demotion changes a ranking, never vetoes a valid intermediate, never creates a successor;
  - global matched budgets and one config for all policies;
  - provenance separation and no DEV leakage into transfer;
  - bitwise-continuous validated pieces;
  - off-graph q fails closed and a skipped connector is a discontinuity;
  - guard trips and 0 runtime calls;
  - F12 is one relocation;
  - G3/C3 traces and history unchanged.
- **Approach D G3 tests: 10/10** (re-run after the fix).
- **Full suite + 6 archived replays** (`runs/approach_d/g4/regression/regression_result.json`): **565 passed, 0 failed** (554 historical including Approach D, plus 11 G4); **all 6 archived replays pass** (g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit); verdict `P3A_REGRESSION_CLOSED`; guarded run 842 CPU-s / 850 s wall.

## 10. Figures (`visualizations/approach_d/g4/`, from saved records only)

| Figure | Content |
|---|---|
| `01_coverage_waterfall.png` | witness → relocations → T-core clear → full replay, per catalog; C3 / W-TRANSFER first failures |
| `02_witness_replay.png` | `…213000` (ORD_CHAIN) stored W-ROOT chain o01 → 53, o00 → 52, T; final arrangement after replay (engineering demo) |
| `03_target_sweeps.png` | F12: per-alternative stored T sweeps; why C3 fails after both placements (connectors / budget); W-ROOT's witness T core |
| `04_D_counterfactual_vs_sweep.png` | F12: D's counterfactual p_T per candidate placement, certification outcome, demotion flags |
| `05_policy_comparison.png` | root-matched outcomes per policy on C3 and W-ROOT; relocation-certification effort |

## 11. Files

| Kind | Files |
|---|---|
| Code | `ad_g4.py` (new). `ad_causal.py` (additive: `G4_POLICIES`, `Geo.t_options`, witness `entry_swept` fallback, opt-in demotion). `approach_d.toml` (additive `[g4]`). `tests/test_approach_d_g4.py`. |
| Runs | `runs/approach_d/g4/{baseline,manifest,catalogs,diagnostics,eval,regression}/`, `COMPILE_LEDGER.json` |
| Status | `G4_RUN_STATUS.md` |

**STOP** — G4 complete. Awaiting the next research decision.
