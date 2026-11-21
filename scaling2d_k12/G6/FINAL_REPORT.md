# 2D K>3 scaling dataset: final report (G0–G6)

Release `G6/release_v1` (`SCALING2D_K4_12_TEST_V1`). This is a test-only set of physically verified 2D scenes with a **certified minimum K**:
- 8×8 original geometry, frozen K≤3 teacher;
- ≤ 20 objects (the model cap);
- objects in TRAIN-supported columns 3–7.

**Accepted: 17 of the 25 targeted scenes.** No invalid scene was used to fill the quota.

| K | Quota | **Accepted** | Final candidates | Witness run | Certified | No witness | Not run | Objects | Target/goal pairs |
|---|---|---|---|---|---|---|---|---|---|
| 4 | 5 | **5** | 40 | 40 | 12 | 28 | 0 | 16–17 | 5 distinct |
| 5 | 5 | **5** | 40 | 39 | 14 | 25 | 1 (stopped after the selection was fixed) | 17–18 | 5 distinct |
| 6 | 5 | **5** | 40 | 40 | 7 | 33 | 0 | 18–19 | 5 distinct |
| 9 | 5 | **2** | 198 | 121 | 6 | 115 | 77 (pair already filled) | 20 | 1: (61,63) |
| 12 | 5 | **0** | – | – | – | – | – | – | **BLOCKED** |

## What each term means

| Term | Definition |
|---|---|
| Successful witness length | Length of a relocation sequence for which the teacher verified X = 1 and Y = 1, both independently replayed |
| Proven minimum K | MINK_STATIC_V1 (declared grammar) = MINK_STATIC_V2 (the teacher's full grammar, `any_legal`) = K. These are sound lower bounds, so no sequence of fewer than K relocations can work. |
| Teacher-confirmed feasibility | X = 1 and Y = 1 on the witness, replayed (`independent_replay`), and Y0 = 0 (`CERTIFIED_INFEASIBLE`) |
| Accepted (CERTIFIED_MIN_K) | The witness length equals both bounds, plus the G5 audit (below) passed |
| Budget-limited / uncertified | `NO_WITNESS_FOUND`: the bounded DFS (ALT 8, MAXQ 60 for K4–6, 80 for K9) found no verified sequence. It is **not** evidence of infeasibility. These scenes are not released. |

Every accepted scene is also **LABEL_OK** in G5. G5 ran in a fresh process with a fresh teacher cache, separate from the search, and checked:
- Y0 = 0;
- X = 1 and Y = 1, with replays;
- per-step X witness hashes and the Y witness hash reproduce the search run exactly;
- **Y = 0 after every proper prefix** of the witness (1 … K−1), as the certificate implies;
- witness length = V1 = V2.

Results: **17/17 LABEL_OK**, 0 audit failures, 127 physical queries.

## Gates

| Gate | Result |
|---|---|
| G0 audit | PASS: source/teacher locks, historical fingerprint exclusions, K≤3 parity 46/46 (girish) and 46/46 (enigma) |
| G1 long teacher | PASS: `teacher_long.py` (BXY_X/Y_TEACHER_V2_LONG). ≤ 6 relocations dispatch to the frozen teacher unchanged; 7–12 use `LongPhysics` with the budget dict unchanged, so RNG keys are identical. Parity P1–P4 recorded in `G1/G1_LONG_TEACHER.md`. |
| G2 priors and witness search | Option (b) approved. TRAIN parking prior plus `witness_v3` DFS raised the witness yield from 1.6% to 24.6% (K4–6 pilot). |
| G3 deep scenes | K9: 8 certified engineering scenes (not released). **K12 BLOCKED** (`G3/K12_BLOCKED.md`): at ≤ 20 objects the largest certifiable K is 9; K_lb 12 needs ≥ 25 objects. |
| G4 final cohort | Fresh generator seeds. Excluded historical and engineering fingerprints plus near-duplicates (Jaccard > 0.85). Locked sha256('FINAL\|root') order; ≤ 2 scenes per target/goal pair per stratum (`G3/EXPERIMENT_LOCK.json`). |
| G5 labels | 17/17 LABEL_OK (`G5/g5_labels_k45.jsonl`, `G5/g5_labels_k69.jsonl`) |
| G6 release | Manifests, labels, coverage, figures, this report |

## Shortfalls, stated exactly

- **K9 = 2 of 5.** Every K_lb 9 layout at ≤ 20 objects comes from the corner pairs (5,7) and (61,63). The witness search certified 6 of 23 (61,63) candidates it ran, but **0 of 98 (5,7) candidates**. The ≤ 2-per-pair rule then admits only 2 scenes, both on pair (61,63). K9 diversity is therefore limited to one target/goal pair; the two layouts differ.
- **K12 = 0 of 5.** BLOCKED by the 20-object cap, with full evidence in `G3/K12_BLOCKED.md`.
- Raising either count needs a protocol change that is not authorised: more objects, a larger lattice, relaxing the pair cap, or a larger witness budget.

## Compute (remote hosts only; the laptop did only bookkeeping and drawing)

| Host | Work |
|---|---|
| gvlab2 (CPUs 4–42) | gen_deep, annealing, final K4/K6 witness search, all G5 labelling, release serialisation |
| enigma (≤ 15 cores, inside naren-m4m) | final K5 and K9 witness search, K9 engineering |
| girish (≤ 21 workers) | K9 engineering and final K9 |
| Total final witness search | 16.3 CPU-hours |

Stragglers stopped by exact PID (rows recorded as NOT_RUN in coverage):
- one K5 row, after the K5 selection was fixed;
- the girish engineering K9 run at 77/80 rows (engineering is not released);
- the (61,63) K9 rows, once that pair was filled.

## Release layout

| Path | Contents |
|---|---|
| `public/roots/*.json` | 17 raw 2D records in the frozen format (scene, goal, q0, roles). **No** labels, K, witness or certificate (leak check: clean). |
| `public/PUBLIC_MANIFEST.jsonl` | Paths and sha256, in sha256('RELEASE\|root') order, so K cannot be inferred from order or id |
| `private/LABELS.jsonl` | K_certified, witness, V1/V2 certificates (minimal goal set, layer counts), Y0, X/Y statuses and replay hashes, G5 checks and every query |
| `private/COVERAGE.jsonl` | All 318 final-stratum candidates with verdict, queries, CPU time and status (SELECTED / CERTIFIED_AFTER_QUOTA / CERTIFIED_PAIR_CAP / NO_WITNESS_FOUND / NOT_RUN_*) |
| `SUMMARY.json` | Per-K statistics |
| `G6/figures/overview_final.png` | All 17 scenes with numbered witness arrows |
| `G6/figures/gifs/K*_*.gif` | One schematic step-by-step animation per scene (lattice states after each verified relocation; the physical replay is the teacher's, recorded in G5) |

Construction-time certificates and witnesses are private. They must never be inputs to the learned inference pipeline: only `public/` is.

## Reproduce

```bash
python gen_deep.py G1/MINK_TABLE_original.json G1/QCLEAR_original.json <seed0> 20 6000 out.jsonl     # K4-6 generation
python anneal20.py ... '{"random_init":true,"t":61,"goal_cell":63,"n_objects":20}'                   # K9 generation
python final_select.py CANDIDATES eng_list.txt OUT.jsonl 4,5,6 40                                    # G4 novelty + locked order
python witness_v3.py tables/MINK_TABLE_original.json LAYOUTS OUT WORKERS 8 60|80                     # witness + certificate
python label_g5.py LAYOUTS WITNESS OUT WORKERS                                                       # G5 audit
python release.py G6/RELEASE_SPEC.json release_v1 && python viz_release.py LAYOUTS G5 G6/figures     # G6
```

Code hashes are in `private/LABELS.jsonl` (`provenance.g5.code_sha256`) and in `G6/release_v1.sha256`.
