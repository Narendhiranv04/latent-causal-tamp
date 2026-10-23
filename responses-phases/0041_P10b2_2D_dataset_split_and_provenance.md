# 0041 — P10b-2: the 180-root 2D dataset, split and label provenance

**Actual result.**
- **Construction:** all **180 / 180** roster roots constructed, with no unavailable root and no replacement.
  - 40 in P10b-1 (batch 1);
  - 140 in P10b-2 (batches 2–5).
  - The four P10b-2 plans were frozen and pushed (`9b9ee8a`) before any of their labels.
- **Split:** **80 train / 35 validation / 65 blind**, exactly as preregistered.
  - Unique seeds and unique geometric fingerprints across all splits.
  - The P10a roots are training only.
- **Blind outcomes are sealed:** written only to `batch*/sealed/`, never to the shared ledger or progress files, and never loaded by any training or selection code (`p10b_dataset.records` refuses them until `runs/p10b/UNSEALED` exists). Their file hashes are in `runs/p10b/SPLIT_MANIFEST.json`.
- **Teacher spend:** 14,769 / 24,000 CPU-s in total, including dev pilots and static admission.

## 1. Non-blind yield (train + validation, 115 roots; `runs/p10b/P10B2_YIELD.json`)

| family | roots | realized | proof-grounded |
|---|---|---|---|
| H1 κ = +1 | 12 | 12 | 12 |
| H2a κ = −1 | 10 | 8 | 8 |
| H2b κ = 0 | 10 | 10 | 10 |
| H3 order | 12 | 6 | 6 |
| H4 omission | 11 | 10 | 10 |
| H5 feasible original | 10 | 10 | 10 |
| H7 edit vs executable | 10 | 10 | 10 |
| H8 sweep obstruction | 11 | 7 | 6 |
| H10_3 three-move | 15 | 15 | (minimality operational) |
| H10_4 four-move | 14 | 14 | 10 (sound minimality) |

- **H3:** 0 / 4 under V1 (batch 1) and 6 / 8 under V1.1.
- **Decided:** 96 % of the required contrast queries.
- **H10_3:** every root witnessed at exactly 3 moves. Minimality relative to the catalogue is OPERATIONAL because the middle omission `C A` is a BUDGET negative.
- **H10_4:** every root witnessed at exactly 4 moves. Minimality is SOUND on 10 and OPERATIONAL on 4.

**D masks (non-blind):**

| mask type | roots | provenance |
|---|---|---|
| 1 blocker | 39 | proof-grounded |
| 2 blockers | 23 | proof-grounded |
| feasible original | 10 | proof-grounded |
| 2-blocker | 3 | operational |
| 3-blocker | 15 | operational |
| 4-blocker | 14 | operational |
| incomplete | 11 | — |

- **D training rule (preregistered):** only proof-grounded masks enter D's blocker loss.
- **Consequence:** the 3- and 4-blocker strata exist **only operationally**. They are the H10 corridor masks, where parking only the adjacent object fails with clean BUDGET seeds.

## 2. Cost

- Median teacher query: 4.0–5.0 CPU-s per batch.
- Mean total cost: about 75 CPU-s per root, including static admission and censored seeds.

| category | spent (CPU-s) | cap (CPU-s) | notes |
|---|---|---|---|
| teacher | 14,769 | 24,000 | |
| constructor_dev | 1,018 | 3,000 | |
| training (ledger) | 35,080 | lifted by user instruction | **inflated** (see note) |

**Note on the training ledger.** The preliminary pass ran in a threaded runner. Each guard's `RUSAGE_CHILDREN` then also counted sibling jobs, so the ledger over-states that pass. The runs' own `train_cpu_s` sum to 4,600 CPU-s. The runner was fixed to one process per job before the confirmatory training.

## 3. Learner view (`runs/p10c/`, `P10C_RECORDS_V1`)

| file | roots | contents |
|---|---|---|
| `dataset_trainval.pt` | 319 | 284 train (190 historical P8c view relabelled train, 14 P10a disclosed, 80 P10b) + 35 P10b validation; 1,823 labelled repair candidates |
| `dataset_blind.pt` | 65 | **no labels** |
| `dataset_h9.pt` | 200 | H9 appearance variants of every validation and blind root (two palettes). DINOv2 features are recomputed on a recoloured copy of the same observation; geometry and query ids are identical; no labels |

- **Short (≤ 2-move) regime:** drops every H10 root, every root whose shortest VERIFIED repair is longer than 2 moves, and every candidate longer than 2 moves.
