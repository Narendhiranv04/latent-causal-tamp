# R10.0: canonical dataset release LEGOLAS_FINAL_v1

**Status: PASS-WITH-QUALIFICATIONS.** The release is sealed: `release_sha256` a537366e…, in `release/R10_DATASET_SEAL.json`. The 10 automated release tests pass.

The two qualifications are listed under "Exposure ledger" below:
- the original TEST was outcome-exposed historically;
- BENCH tracks are exposed by construction.

No known leakage remains in a learning or clean-evaluation partition.

**Code:**
- `r10/inventory.py` builds the lineage graph.
- `r10/split.py` applies the partition rules P0–P6 and builds the release.
- `r10/seal.py` seals it.
- `r10/test_release.py` holds the release tests.
- `r10/evalsplit.py` builds the evaluation roster.

**Raw records:**
- `reports/r10/inventory/`: `nodes.jsonl.gz`, the summary, and the first-run L3 summary.
- `reports/r10/release/`: registry, splits, provenance, checks, seal.

All computation ran on gvlab2.

## 1. Inventory: sources actually found and reconciled

| Source | 2D | 3D | Found as |
|---|---:|---:|---|
| Original TRAIN / VAL / TEST | 3500 / 751 / 749 | 1766 / 364 / 370 | `abf_9de85710c2a7103f`. The expanded `abf_v32_fb0eef4f5ff433ee` adds TRAIN labels only; VAL and TEST rows are byte-identical to base (asserted) |
| V3.4 cohort | 719 | 395 | `r8a_verify` public/private |
| R8B composition roster | — | 99 | Sealed R8B, re-verified against SEAL |
| Exposed development roots | 32 (R5.3 panel 20, R5 demo 12) | 20 (k45 panel) | `r53.panel` / `r6.roots` |
| Strict local supervision | 3,316 labels on 828 roots | 2,318 labels on 312 roots | Exact R7 builder `xlearn.build`: KGT3 P2, R3.1, R4.3/4.4, R5.1 |
| Q2 placement pretraining | 238,160 samples / 4,620 roots | 55,036 / 1,465 | `q2_{dom}`; 1,317 / 239 roots are unselected pool roots |
| Baseline training provenance | — | V4 split | `learned_reap/reap_shelf/split_v4.json`, sha f5b18516…. Its 1766 / 364 / 370 equals our original 3D split root-for-root (GRN, PIGINet, SCNet and REAP train or select on it) |

## 2. Identity and lineage rules (predeclared, `inventory.py`)

**Link rules:**
- **L1:** exact geometry, i.e. same scene and task.
- **L2:** the same 3D physical objects (continuous-dimension multiset).
- **L4:** declared lineage: `layout_root_id`, construction parent, or the same root id.
- **T:** factor template (`parent_family_id`).

**L3 (2D rearrangement similarity) was reviewed after the first run and demoted to a sensitivity measure.** With discrete 2D attributes it chained independently generated similar scenes into giant components. Its near-duplicate rate between TEST and TRAIN equals the rate between the independently generated V3.4 and TRAIN, so it is a generator property, not lineage. First-run numbers are in `inventory_summary_L3merge.json`.

## 3. Findings and resolutions

| Finding | Size | Resolution (rule) |
|---|---|---|
| 2D exact-duplicate or lineage twins across original splits (TEST–TRAIN / TEST–VAL / TRAIN–VAL) | 15 TEST rows, 24 TRAIN, 8 VAL (+ pool roots) | P2/P3: TEST twins and their TRAIN/VAL/local twins go to QUARANTINE. TEST rows whose twin was historically trained are not called held-out |
| 2D exact duplicates within a split (labels agree) | 925 TRAIN / 216 VAL / 5 TEST canonical records with aliases | P5: one canonical record, labels merged by edit, aliases kept. Evaluation scores each canonical scene once |
| Contradictory physical labels between exact duplicates | 18 (2D, X) | Dropped as unresolved, never voted (`provenance/label_conflicts.json`) |
| 3D local TRAIN labels physically derived from original VAL scenes | 241 labels | P4: moved to local VAL |
| 3D local labels on VAL templates (TRAIN in R7) / on TRAIN templates (VAL in R7) | 313 / 406 labels | P4: follow the template split |
| 2D local labels whose source scene duplicates an original TEST scene | 11 labels (2 roots) | EXCLUDE |
| Q2 placement data | TEST-split samples in Q2 split 2 were never trained on (verified); kept physically in a first build (bug, caught by tests) | Rebuilt: canonical TRAIN/VAL only. Scalers refit on canonical TRAIN. All training restarted |
| V3.4 and R8B templates are VAL templates | 395 + 99 | Template-level only; geometry disjoint by construction. Exposed benchmark tracks, qualified |
| 3D original splits | 0 cross-split physical links | Kept |

## 4. Partitions (canonical scenes)

| Partition | 2D | 3D | K0 / K1 / K2 / K3 / NONE (2D; 3D) |
|---|---:|---:|---|
| TRAIN | 3,802 | 1,859 | incl. local and pool roots |
| VAL | 917 | 402 | |
| TEST_SHORT | **729** | **370** | 185/120/117/161/146; 67/53/86/102/62 |
| BENCH_SHORT (V3.4) | 719 | 395 | 180/116/116/162/145; 93/58/106/75/63 |
| BENCH_COMP_3D | — | 99 | L_ref 4: 68, L_ref 5: 31 |
| DEV_EXPOSED | 30 | 20 | |
| TEST_FEAS_3D | — | annex | Prospective protocol `r10/FEAS_PROTOCOL.json`; collection running |
| QUARANTINE / EXCLUDE | 29 / 2 | 0 | |

The training views derived from the release are:
- canonical snapshot `abf_r10_70e8ec7db1d4c56b`, with TEST and quarantine rows physically absent;
- Q2 with 198,504 / 47,240 samples kept;
- the local split map: 2D 608 TRAIN / 218 VAL / 2 EXCLUDE roots; 3D 216 TRAIN / 96 VAL.

## 5. Exposure ledger (from commits and reports)

**Original TEST was never used for training, calibration or selection by any model in this release, or by the V4-split baselines.** Its aggregate outcomes were nonetheless viewed for earlier model generations:
- V3-6, 2026-11-16, ede29034b2;
- V3.1-4, 2026-11-17, 82de92e682;
- V3.2 E6 "exposed-TEST regression", 95dd41603d;
- DISCO-Grid TEST jobs, 2026-11-17;
- K≤3 ablation P6/P7, 4aee798929.

TEST_SHORT is therefore **held-out but not blind**. A genuinely blind short-horizon top-up of about 1,100 roots would need roughly 200 CPU-h for generation before any evaluation. That does not fit the 500 CPU-h envelope and is recorded as a requirement, not executed.

V3.4 (BENCH_SHORT) and R8B (BENCH_COMP_3D) were evaluated before (V3.4/R8A, R8C/R9). They are fixed exposed benchmarks and are never relabelled as test.

## 6. Tests (`r10/test_release.py`, 10/10 pass)

The tests cover:
- canonical id uniqueness;
- one partition per scene, with exclusion ledgers exempt;
- family disjointness between learning and evaluation, and between TRAIN and VAL;
- template disjointness between learning and TEST;
- the snapshot allowlist;
- Q2 lineage;
- local-split lineage;
- conflicts dropped, not voted;
- actions of length ≤ 3;
- seal hashes.

On the first run the tests caught two release bugs: Q2 split-2 residue, and a conflict re-added by a later alias. Both were fixed, the release was rebuilt, and training restarted from scratch.
