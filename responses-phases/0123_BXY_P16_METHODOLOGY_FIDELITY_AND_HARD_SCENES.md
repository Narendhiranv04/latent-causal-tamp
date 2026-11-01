# 0123 — BXY-P16: methodology fidelity audit, label-free V2 inputs, access-closure hard-scene generator, development waves

Date: 2026-11-01. Gate: BXY-P16 (first gate of the BXY-P16 → P18 contract). Start commit `954e85b8`.

## Result

**DATA_READY.** The six readiness thresholds were frozen in `bxy_p16.READINESS` before any P16 label (the wave-A generator snapshot,
sha `ab2920ed…`, contains them). Over the three labelled development waves:

| Threshold | Target | Realized |
|---|---|---|
| independently generated labelled development roots | ≥ 60 | **87** |
| initially infeasible roots (Y0 = 0) | ≥ 20 | **69** |
| roots with verified K ≥ 2 within the finite catalogue | ≥ 12 | **13** (11 × K2, 2 × K3) |
| F1-admissible same-endpoint X-discordant order pairs | ≥ 4 | **23** pairs in **20** roots, 7 with a certified failing order |
| roots with a Y0 = 1 / Y_edit = 0 harmful-edit contrast | ≥ 12 | **12** |

- **Labelling quality:** 1,498 frozen queries, **1,498 labelled**; 0 censored, 0 replay failures, 0 identity mismatches.
- **Compute:** 16,832 of 24,000 CPU-s and 8,556 of 14,400 s wall. 87 of the 120 permitted new roots were used.
- **The K ≥ 2 claims are catalogue-relative.** In each of the 13 roots, every shorter F1-admissible catalogue candidate was labelled and
  failed, and every intermediate prefix of the verified repair has Y = 0. Of the 61 shorter-candidate Y failures, **49 are certified** and
  **12 are fixed-budget planner failures**. No global necessity claim is made beyond the analytic K_geom scope (§2).
- **Reproduction:** P12, P14 and P15 aggregates reproduce **exactly** from the committed artifacts ([REPRODUCTION_P12_P15.json](../runs/approach_b/bxy_p16_v1/REPRODUCTION_P12_P15.json)).
- **Frozen evidence:** every frozen P-min … P15 artifact is unchanged (hash guard: `git diff` empty over the frozen run directories).

The domain is now genuinely harder than P15, with honest limits:
- K4 never verified, and K3 only twice.
- Half of the hard roots (43 / 87) have **no verified repair** in their catalogue, mostly because of fixed-budget planner failures, not
  certified impossibility (§5).

---

## 1. Requirements-to-evidence matrix

Machine-readable files:
- [REQUIREMENTS_MATRIX_START.json](../runs/approach_b/bxy_p16_v1/REQUIREMENTS_MATRIX_START.json) — 22 requirements, with their status
  before P16;
- [REQUIREMENTS_MATRIX_AFTER_P16.json](../runs/approach_b/bxy_p16_v1/REQUIREMENTS_MATRIX_AFTER_P16.json) — the evidence counts
  afterwards.

"Data" means the phenomenon is now present in labelled development roots. Whether a model learns it is a P17 question.

| Requirement | Before P16 | Evidence added by P16 (independent roots) | Status after P16 |
|---|---|---|---|
| F1 analytic screen | SUPPORTED | every V2.1 query F1-screened; screened queries listed, never labelled | SUPPORTED |
| F2 ordered prefix X | EVIDENCE_WEAK (order ~chance) | 23 measured F1-admissible same-endpoint X-discordant pairs (20 roots), 7 certified | data SUPPORTED; learning → P17 |
| F3 hypothetical Y | EVIDENCE_WEAK (universal edit bonus) | 12 harmful (1→0) roots, designed neutral twins; 69 infeasible roots with partial-prefix Y = 0 | data SUPPORTED; learning → P17 |
| F4 omissions | EVIDENCE_WEAK | 59 omission Y labels of m ≥ 2 repairs; 16 differ from the full repair's Y | data SUPPORTED |
| F5 quadratic XY | EVIDENCE_WEAK (P12: no gain) | — (tested in P17) | → P17 |
| root-consistent likelihood | SUPPORTED | unchanged, re-tested in P17 | SUPPORTED |
| X/Y cells 00 / 01 / 10 / 11 | SUPPORTED (01 weak) | roots containing each cell: 66 / **28** / 68 / 42 | SUPPORTED |
| Y shared across orders | SUPPORTED | one Y key per endpoint in every design (test) | SUPPORTED |
| no-op | EVIDENCE_WEAK (over-repair) | 18 Y0 = 1 roots, 12 with a harmful alternative | data SUPPORTED |
| connector to q_ref | SUPPORTED (no negatives) | 20 connector-phase X negatives after verified relocations (UNKNOWN_TRANSIT: fixed-budget, not certified) | SUPPORTED (budget-relative) |
| achieved state carried | SUPPORTED | every X witness (replay_x continuity) | SUPPORTED |
| prefixes 1..6 | EVIDENCE_WEAK | labelled X prefix lengths 1: 342, 2: 350, 3: 70, 4: 16, 5: 2; 43 m ≥ 2 repairs prefix-complete, 8 verified | SUPPORTED to length 3; lengths 4–6 weak |
| K0–K4 coverage | EVIDENCE_WEAK (P15: one K2) | verified K0 18, K1 13, **K2 11, K3 2**, K4 0, none 43 | K2 SUPPORTED, K3 weak, K4 missing |
| redundant / harmful edits | EVIDENCE_WEAK | 12 harmful-contrast roots; repair + unnecessary and repair-then-harmful candidates | SUPPORTED |
| physics vs budget failures | SUPPORTED | Y: 361 certified / 195 budget; X: 49 certified / 353 budget (kept evaluator-side) | SUPPORTED |
| outcome-blind candidates | EVIDENCE_WEAK (easy) | V2.1 access-closure catalogue (§3); catalogue invariant to labels (test) | SUPPORTED |
| travel J / Ĵ | SUPPORTED | complete witnesses on V2.1 successes (stitched relocation + connector + target) | SUPPORTED |
| teacher / learner separation | SUPPORTED | new-corpus ScorerViews pass the whitelist; label-free inputs (§4) | SUPPORTED |
| V2 learner inputs | MISSING | [bxy_p16_inputs.py](../bxy_p16_inputs.py) | SUPPORTED |

## 2. Why P15 was easy, and the V2.1 answer

- The planar 3R side-grasp skill offers **24 approach directions × 2 elbows** for the pick, and again for the place.
- P15 put its blockers on **one** nominal target sweep, and the teacher used another mode.
- V2.1 closes modes analytically ([bxy_p16.py](../bxy_p16.py)):
  - **Access maps.** For every cell, the declared candidates passing the real `skill.screen_pick` / `screen_place` on the empty board,
    and for each candidate the cells whose disc kills it (grasp pose, 6 cm approach line or closure, whole arm included).
    - 98 maps: all 64 pick cells and the 34 valid goal cells.
    - Cost: 2,170 CPU-s, counted against P16.
  - **Union model.** A screen fails iff one disc kills it. The real populated-scene screen re-checks every accepted root; the union
    model agrees on ≥ 11 / 12 random layouts (test).
  - **K_geom.** For a pick candidate i and place candidate j, the fewest movable discs in `M_pick[i] ∪ M_place[j]` that must leave, each
    pickable when it leaves (a greedy analytic removal order). A fixed disc there rules the pair out.
    - It is a **necessary-condition intent, not a verified K**: transit, carry and relocation are planned by the teacher.
  - **Mechanisms:**
    - `open` and `near_closed` (K0): a partial ring with few open modes, plus a **harmful cell** whose occupation closes them;
    - `pick`, `place`, `mixed`: K-level closure of the source, the goal, or both;
    - `nested`: a needed remover is itself closed in S0, which forces the order;
    - `goal_occupant`: a disc sits on the goal.
  - **No populated scene is ever planned during construction.** The single empty-board reference planner call of P15 is kept.

### Development iterations (wA pilot + the two permitted revisions), each frozen before its labels

| Wave | Generator | What changed and why | Slots → roots | Construction CPU |
|---|---|---|---|---|
| wA (pilot) | BXY_GEN_V21 | access closure, catalogue, prefix-complete design | 36 → 31 (5 geometric rejections) | 422 |
| wB | BXY_GEN_V21B | wA diagnosis (below) | 60 → 39 (21 NO_VALID_LAYOUT) | 2,924 |
| wC | BXY_GEN_V21B, K ≥ 2-weighted composition | wB still at 7 K ≥ 2 | 30 → 17 (13 NO_VALID_LAYOUT) | 2,549 |

- **wA diagnosis, from its labels; it informs the next wave only.**
  - The intended repairs reopened about **one** grasp mode, and the Y teacher certified those repaired scenes infeasible: the link-0
    sector certificate and the pick certificate cover the transit to the single reopened mode.
  - Many blocker relocations failed by fixed planning budget (UNKNOWN_PLANNER) in clutter.
- **V21B revision (geometry only, never the planner):**
  - ≥ 3 open pick and ≥ 3 open place modes after the intended repair (real screens);
  - the teacher's **analytic** certificate checker (`p15_retarget.certified`, `ordered.certificates_for`) must not fire on the repaired
    scene or on any intended relocation step;
  - every intermediate prefix keeps T closed;
  - K0 S0 is not certified;
  - harmful cells are confirmed by the real screen;
  - up to 25 layouts per slot are tried from the same seeded stream, and every failed layout is recorded in
    `construction.validation_rejects`.
- **An abandoned wC design** ("reference-mode closure": close every mode except the empty-board witness's own) was found geometrically
  infeasible in pre-freeze dry runs: alternative modes' kill sets lie inside the reference sweep. No root was written and no teacher call
  was made. Its 200 CPU-s is charged to construction.
- **Retained records:**
  - superseded pre-freeze generations (two crashes before any manifest), charged conservatively at full elapsed wall;
  - all rejections;
  - wave-A construction stays byte-reproducible after the revision (test).

## 3. Outcome-blind catalogue and prefix-complete query design

The catalogue is built from geometry and construction intent only. Its candidates, in fixed priority order:

| Candidate | Definition |
|---|---|
| intended repair | in the analytic removal order, blockers to their nearest analytically placeable parking cells, off the reopened mode's kill cells, the q_ref footprint, T's source and the goal |
| reversed order | the intended repair, reversed |
| **every stopping prefix** | `prefix_t` of the intended repair |
| single-action omissions | the omission of the last action equals prefix m−1, so they share keys |
| swapped first pair | for m ≥ 3 |
| wrong final destination | a cell in the reopened mode's kill set |
| alternative minimal repair | another minimal removal set |
| single partial moves | each blocker moved alone |
| repair + unnecessary move | the intended repair plus a distractor move |
| repair then harmful move | the intended repair, then a move that re-closes |
| **interference pair** | A parked on a cell killing B's pick, before B and after B: same endpoint, both F1-admissible |
| harmful vs neutral edit | same object, two destinations |
| neutral pair | both orders |
| q_ref-corridor destination | a cell next to the q_ref footprint |

- **Query design.** Y0, plus X (relocations + the connector to q_ref, from q0 with the achieved state carried) and Y (target from q_ref
  in the hypothetical edited scene) of **every** candidate. Every candidate is a stopping prefix. Y keys deduplicate shared endpoints
  exactly.
- **Caps:** 16 candidates and 44 queries per root.
- **Teacher:** the per-query budget is the exact P-min `bd_2d.QB`, and the teacher hash is unchanged.
- **Every K ≥ 2 repair is prefix-complete:** all 43 m ≥ 2 intended repairs have X and Y at every prefix (§1).

## 4. Label-free V2 learner inputs ([bxy_p16_inputs.py](../bxy_p16_inputs.py))

- **What it reads.** Exactly four record fields: `scene`, `goal_cell`, `q0` and `q_ref`. It computes the **frozen P-min representation**:
  `learn_data.root_record` → `data.learner_tensors_v2`, plus frozen DINOv2-small patch tokens of the rendered initial scene, area-weighted
  per instance.
- **What it refuses.** A root with `q_ref ≠ q0` or `q_ref ≠` the scene robot state is refused rather than silently encoded, because the
  frozen tensors carry one robot state. All corpora so far pin q_ref = q0.
- **P-min equivalence.** Recomputing the stored P-min `RECORDS.pt` inputs through the adapter gives **max |Δ| = 0.0** on every tensor,
  with identical object order and identical render (anchor) hash, on 6 roots.
- **Leakage test.** Scrambling every non-READ field (labels, roles, construction intent, catalogue, ids, spec) leaves the inputs
  bit-identical (test), and the cache key is invariant to the scramble.
- **Cache identity:** DINO revision, image size, grid, tensor keys and the sha256 of the renderer sources.
- **Caches:** `INPUTS_P15_PILOT.pt` (28 roots) and `INPUTS_V21.pt` (87 roots, sha `7624d217…`).
- **Geometry-only control.** Not added as a separate arm. Vision is computed only from the rendered S0 by the identical frozen pipeline
  for every corpus; P17's GEO2 features are geometry-only and are given to every GEO arm and to DIRECT alike.

## 5. Realized physics

| | wA | wB | wC | total |
|---|---|---|---|---|
| labelled roots | 31 | 39 | 17 | 87 |
| queries labelled | 601 | 556 | 341 | 1,498 |
| Y0 = 0 | 25 | 27 | 17 | 69 |
| verified K: 0 / 1 / 2 / 3 / none | 6 / 4 / 2 / 2 / 17 | 12 / 9 / 3 / 0 / 15 | 0 / 0 / 6 / 0 / 11 | 18 / 13 / 11 / 2 / 43 |
| X-discordant same-endpoint pairs (roots) | 9 (9) | 6 (6) | 8 (5) | 23 (20) |
| harmful-contrast roots | 3 | 9 | 0 | 12 |
| connector-phase X negatives | 9 | 9 | 2 | 20 |
| teacher CPU-s | 1,990 | 3,611 | 2,300 | 7,901 |

- **K_geom → verified K:**
  - K_geom 2 → verified 2 in 11 of 30 roots;
  - K_geom 3 → verified 3 in 2 of 10;
  - K_geom 4 → 0 of 3.
- **Failure modes of the no-repair roots,** which are policy-relative:
  - fixed-budget relocation planning in clutter: X NO_PLAN_FOUND 353 vs certified 49;
  - fixed-budget target planning after the repair: Y NO_PLAN_FOUND 195 vs certified 361.
  - **These are not physical impossibility claims.**
- **The worked example of the methodology (§7) now exists in data.** In `wA-s028`:
  - the verified 3-move repair has Y = 0, 0 at prefixes 1–2 and Y = 1 at prefix 3, with X = 1 at every prefix;
  - its reversed order fails X at relocation 0 with a **certified** pick closure (figure 03 / 04).

## 6. Figures ([visualizations/approach_b/bxy_p16_v1/](../visualizations/approach_b/bxy_p16_v1/))

| Figure | Content |
|---|---|
| 01 | access-closure construction: S0 with zero open T-pick modes, the analytic kill cells of the reopened candidate, the ideal post-repair scene with the arm at the reopened grasp pose; and a near-closed K0 root with its harmful cell |
| 02 | realized difficulty: P15 vs V2.1 verified-K mix; K_geom vs verified K; verified K by mechanism |
| 03 (×3) | prefix-complete physical stories from **recorded, replayed witnesses** (relocations blue, connector to q_ref pink, target green), Y at every prefix (`s028`, `s036`, `s016`) |
| 04 (×3) | F1-admissible same-endpoint order twins with different measured X and one shared Y (`s026` certified, `s018`, `s004`) |
| 05 (×2) | harmful vs neutral edits of one object: Y 1 → 0 vs Y stays 1 |
| 06 | all four X/Y cells by mechanism and by independent-root coverage; certified vs budget negatives; connector failures |
| 07 | X and Y at every stopping prefix of every m ≥ 2 intended repair |
| 08 | P16 compute ledger (maps / construction / teacher) and per-root cost vs the 800 CPU-s cap |

## 7. Compute ledger (hard ceilings in [BUDGET_MANIFEST_P16.json](../runs/approach_b/bxy_p16_v1/BUDGET_MANIFEST_P16.json); per-wave AUTHORIZATION.json)

| | CPU-s | wall s |
|---|---|---|
| access maps | 2,169.8 | 846 |
| construction + pre-label audits + superseded / dry runs | 6,669.5 | 4,895.5 |
| teacher workers (LEDGER finish events) | 7,992.5 | 2,814.9 |
| **total** | **16,831.7 / 24,000** | **8,556.4 / 14,400** |

- **Per-root cap:** max teacher CPU per root was 387 (wA), 578 (wB) and **791.5 (wC)** CPU-s against the 800 CPU-s cap. Every worker
  exited cleanly with all of its queries labelled, and no root hit its RLIMIT.
- **Hardware:** 4 workers, one thread each, no GPU, no external API.
- **Construction wall** is reconstructed from timestamps in [CONSTRUCTION_WALL.json](../runs/approach_b/bxy_p16_v1/CONSTRUCTION_WALL.json),
  conservatively; wave C was constructed with 4 processes and its wall is recorded directly.

## 8. Files, hashes and tests

- **Code:**
  - [bxy_p16.py](../bxy_p16.py) — generator, catalogue, waves, collection, summary, readiness;
  - [bxy_p16_inputs.py](../bxy_p16_inputs.py);
  - [bxy_p16_audit.py](../bxy_p16_audit.py) — reproduction, guard, matrices;
  - [bxy_p16_viz.py](../bxy_p16_viz.py);
  - [tests/test_bxy_p16.py](../tests/test_bxy_p16.py) — union model, K_geom, record intent, catalogue label-invariance and determinism,
    shared-Y dedupe and caps, wave refusal, readiness logic, adapter READ-only view / q_ref refusal / mutation invariance / P-min
    equivalence, wave-A determinism after the revision.
- **Frozen designs (sha256):**
  - wA `0df3e04a8b88…`, wB `57dfdbc9c005…`, wC `96e6ddbd0885…`;
  - access maps `5bae2b3e2501…` (identical in all three designs);
  - READINESS `b8bcdfad82a2…`.
- **Per query:** each query and its witness ids sit under `runs/approach_b/bxy_p16_v1/w*/results` and `w*/witnesses`
  (content-addressed).
- **Regression:** full suite and six archived replays — see §9.

## 9. Regression

Recorded in `runs/approach_b/bxy_p16_v1/regression/`:
- full test suite: **693 passed, 1 skipped** (`pytest -q tests`, P17 tests excluded because they belong to the next gate);
- six archived replays (g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit): all exit 0;
- hash guard over every frozen P-min … P15 run directory: clean.

## 10. Next bounded decision

P16 is DATA_READY, so P17 may proceed: the frozen design must be written before any optimizer step. Its data are:
- the 197 P-min train/val roots;
- the 28 P15 pilot roots;
- the 87 V2.1 roots.

The 34 exposed P-min test roots and every confirmatory namespace remain excluded. **No confirmatory root was generated.**

STOP (gate P16).
