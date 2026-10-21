# 0023 — P7b: 48 κ-diverse 2D roots, fair A/B/C retraining, independent one-shot 2D execution

**Previous turn sync:** `bc20227` (P7a, report 0022).
**Authorization:** the same user message (P7a plus the gated P7b continuation).
**Precondition:** `P7A_PASS` (`runs/p7/a_gate.json`).

**Stage verdicts.**
- Collection: **`P7B_COLLECTION_PASS`**. Both waves ran, the wave-1 gate passed 7/7, and every cap held. Coverage is
  **partial for κ = −1** (5 roots, target ≥ 6).
- Training and evaluation: **PASS (engineering)**.
- One-shot execution: **PASS (engineering)**, 48 episodes.

**Scientific claims.**
- `CAUSAL_INTERACTION_GENERALIZATION`: **NOT ESTABLISHED**.
- Coupling advantage: **REJECTED** on this distribution.
- `LEARNED_REPAIR_SUCCESS`: **NOT ESTABLISHED**. No learned arm beats the uniform-ranking control in one-shot execution.

**Overall P7: PARTIAL.** All engineering is complete and every gate was enforced; the main learning hypotheses fail or
remain unestablished.

## 1. Construction and plan (frozen before the first teacher call)

**Families** (`p7_scenes.py`): 6 families × 8 roots = 48. Each family has 4 train / 2 validation / 2 sealed test roots,
split across two waves of 24 (four batches of 12). Seeds 2026102401–48; every definition is predeclared in
`p7_scenes.ROOTS`.

| family | construction intent |
|---|---|
| KP | complementary grasp-side + place-side blockers |
| KM | redundant pair of grasp-side neighbours |
| K0 | one relevant neighbour + one irrelevant nearby object |
| ORD | access chains of 2–3 moves (+ optional place blocker, up to 4 moves) |
| MOT | link-0 **sweep barrier** inside the annulus; neighbour screens pass, the obstruction is motion-level |
| ALT | three interchangeable neighbours, 1–4-move alternatives with 2 destinations each |

**Start configurations.**
- Strata S0–S3 are assigned round-robin.
- MOT uses only {S0, S1, S3}: the static preview showed that S2 (link 0 at 45°) admits **no** annulus barrier
  (0 / 200 attempts). This is recorded as a physical limitation and was fixed before any teacher call.

**Independence and integrity.**
- Every root has a unique translation-invariant motif signature (family, role / fixed offsets, goal offset, stratum,
  clutter count) and a unique stable geometry against all historical roots.
- No family was `CONSTRUCTION_UNAVAILABLE`.
- Construction took 124.6 CPU-s, with every attempt logged (`construction_attempts.jsonl`).

**Plan.**
- Catalogues have at most 32 unique queries per root (≤ 27 sequences after the reference and edits), with omission
  closure; **971 queries and 2,913 seed units** in total (caps 1,536 / 4,608), plan `sha256:25d0c7139d1d2…`.
- Nuisance edits stay outside the 9-bit layout.
- Static-invalid endpoint checks (2 invalid + 2 valid per obstructed root) are kept outside the teacher cap.

**Static admission:** 780.7 CPU-s (total static **905.3 / 1,200**), 0 coordinator planner calls. **368 queries are
certified without the teacher**:

| certificate | count |
|---|---|
| TARGET_PICK | 260 |
| **LINK0_SECTOR_PICK** (motion-level sweep proofs) | 57 |
| FIRST_MOVER | 28 |
| ORDER_FIRST_ACTION | 23 |

**A7** stays disabled (`runs/p7/audit/a7_place_certificate_audit.md`), so place-side failures remain operational.

## 2. Collection (`runs/p7/collection`, OPNEG-v1 unchanged, process-tree guarded, 1 worker)

| quantity | value | cap |
|---|---|---|
| teacher CPU-s | **17,674.6** | 20,000 |
| wall | 18,602.5 s | 48,000 |
| largest root | 881.1 CPU-s | 1,000 |
| seed attempts | 656 (654 completed, 2 CPU-censored) | 4,608 |
| outcomes (all 971) | 269 VERIFIED / 368 CERTIFIED / 125 BUDGET_INFEASIBLE / 8 UNKNOWN / **201 NOT_RUN** / 0 FATAL | — |
| development / sealed test | 213 / 270 / 98 / 6 / 134 and 56 / 98 / 27 / 2 / 67 | — |

The historical frozen manifests (G4C pilot, POC_S, G4D, P4 pilot, P5 D3-lite, P5 G4E, P6 collect) are unchanged, and
the P6 train hashes are unchanged.

**Why so many NOT_RUN — honest cost finding.**
- In several KP / K0 / KM / ALT roots, the main or reference repair passes every static screen but the full 3R planner
  exhausts its search: 63 `SEARCH_LIMIT_PLAN_FAILURES` seed terminals at about 100–240 CPU-s each.
- These are clean `BUDGET_INFEASIBLE` labels. They are *motion-level* failures that the pose screens do not predict
  (e.g. p7_2026102402: main → destination 60 fails, alternative → 52 is VERIFIED).
- Each costs up to ~720 CPU-s, so the predeclared per-root (1,000) and per-batch (5,000) caps then stop the remaining
  queries of that root or batch: 134 NOT_RUN were cap-stopped.
- 67 more were lineage-stopped because the reference scene was not VERIFIED. Two references exhausted the planner
  (KP test p7_2026102428, KM train p7_2026102429); two ALT references were never run because of the batch cap.
- Nothing was reordered or relaxed after any outcome.

**Wave-1 gate** (development roots of batches 1–2 only; `progress.json → status.wave1`) — **PASS 7/7**:
1. Integrity: no FATAL; UNKNOWN 4 / 271 = **1.5 %** (< 20 %).
2. κ signs: **+1 ×6, −1 ×2, 0 ×2** (7 operational).
3. 6 decided order contrasts over 5 roots; 18 VERIFIED repairs of ≥ 3 moves over 13 roots.
4. **11 roots with two differently-sized VERIFIED repairs.**
5. Motion: 3 MOT roots with LINK0_SECTOR_PICK-certified failures and VERIFIED repairs.
6. 9 joint-pool-ready roots across 5 families.
7. Budget held: 8,397 CPU-s.

**Final evidence (all 48 roots).**

| target | result |
|---|---|
| κ | +1 ×16, 0 ×7, −1 ×5 (19 of 28 operational) |
| decided same-endpoint order contrasts | 17 over 13 roots (10 proof-grounded) |
| roots with ≥ 2 verified repair lengths | 30 |
| one-move VERIFIED repairs | 45 (P6 had none) |
| four-move VERIFIED repairs | 14 |
| complete development B/C candidates | 318 (5 complete at K = 9) |

Against the final sufficiency targets, κ = −1 **misses** (5 < 6). All other targets are met, and there are 12 sealed
test roots. The per-root table is in §8.

## 3. Training (`runs/p7/training`, one guard: **11,141.7 / 12,000 CPU-s**, 0 teacher calls)

**Setup.**
- **Configurations:** the frozen P7a choices (A: clip 5 / λ_pool 0.5, B: 5 / 0.5, C: 1 / 0.5). Learning rate, epochs
  and patience are unchanged.
- **Training data:** 94 roots / 700 candidates, consisting of the P7b train roots and all historical roots with
  provenance (P4, P5, P6 incl. the already-examined P6 holdout). Validation: 24 P7b roots.
- **Compute:** equal CPU per run (≈ 470 CPU-s), so B and C got fewer epochs than A (matched compute, not matched
  epochs).
- **Selection and calibration:** temperature and the 0.5 threshold come from validation only. The test roots were
  loaded once, after all 23 checkpoints and the one-shot rankings were frozen.

**Disclosure:** while compiling collection tables (before training finished) I printed the κ-sign *counts* of the sealed
test roots (3 / 2 / 2). No model, threshold or ranking choice depended on them; all were frozen in code before
collection.

**Sealed test results** (calibrated, mean ± sd over 3 seeds; 146 decided candidates, 45 positive; root-cluster
bootstrap 95 % CI for seed 0):

| arm | accuracy | AUROC | NLL | ECE | κ MAE | κ sign | scene-effect MAE | omission-effect MAE | rank acc | offline selection (7 roots) |
|---|---|---|---|---|---|---|---|---|---|---|
| A | **0.890 ± 0.012** [0.78, 0.96] | **0.963** | **0.248** | 0.064 | 0.762 | 0.19 | 0.455 | 0.185 | 0.922 | 0.48 |
| B | 0.833 ± 0.032 [0.74, 0.87] | 0.926 | 0.354 | 0.108 | 0.612 | 0.48 | **0.220** | 0.303 | **0.967** | 0.57 |
| C | 0.833 ± 0.016 [0.79, 0.89] | 0.917 | 0.370 | 0.087 | 0.662 | 0.43 | 0.327 | 0.320 | 0.961 | 0.62 |
| B-no-coupling | **0.897 ± 0.007** | 0.953 | 0.257 | **0.056** | **0.584** | 0.43 | 0.416 | **0.169** | 0.955 | 0.43 |
| C-no-coupling | 0.829 ± 0.036 | 0.927 | 0.304 | 0.085 | 0.713 | 0.29 | 0.506 | 0.215 | 0.886 | 0.38 |

**Secondary arms** (seed 0, test accuracy / AUROC / κ MAE):

| arm | accuracy | AUROC | κ MAE |
|---|---|---|---|
| S (non-energy) | 0.897 | 0.966 | 0.58 |
| A-capacity | 0.890 | 0.948 | 0.64 |
| A-geometry | 0.753 | 0.863 | 0.97 |
| B-geometry | 0.822 | 0.867 | 0.73 |
| C-geometry | 0.753 | 0.846 | 0.77 |
| B-quadratic | 0.863 | 0.935 | 0.67 |
| C-quadratic | 0.884 | 0.943 | 0.80 |
| B-structured | 0.863 | 0.930 | 0.67 |

Validation results show the same ordering (A 0.853, B 0.845, C 0.847, B-no-coupling 0.876 accuracy); full tables are in
`runs/p7/training/results.json`.

**κ confusion on test roots** (observed → predicted sign, pooled over 3 seeds):

| arm | κ = −1 | κ = 0 | κ = +1 |
|---|---|---|---|
| B (coupled) | 5 → 0, 1 → +1 (**never predicts −1**) | 5 → +1 | 9 → +1 |
| B-no-coupling | **4 → −1**, 2 → 0 | 5 → 0 | 9 → 0 (**never predicts +1**) |
| A | 5 → 0 | 3 → 0, 3 → +1 | 8 → 0 |

The coupled scene block learned the dominant +1 pattern (P7a's apparent κ success). The uncoupled model captures
redundancy but not complementarity. **No arm generalizes κ across signs.**

**Sampler** (`ABC_boltzmann_samples.gif`): on an ORD test root (356 ordered repairs, cap 4), the G4B kernels on each
learned energy pass **exact detailed balance** (max error ≤ 3.3e-16). The 4,000-step chain TV against the exact
distribution is A 0.67, B 0.66, C 0.20, i.e. poor mixing for the peaked A / B energies at that length.

**Clipping** is still frequent (B / A 32–49 %, C 89–99 % at clip 1); there were no non-finite events.

## 4. Independent one-shot 2D execution (`runs/p7/execution`, 1,930 CPU-s, cap 9,000, ≤ 250 CPU-s per episode)

**Protocol.** Rankings were frozen and hashed (`runs/p7/training/rankings.json`, `sha256:b35a614f…`) before any
episode. Each arm (seed-0 model) ranks the sealed test root's catalogue: calibrated p ≥ 0.5, fewest moves, then
predicted J, displacement, energy, top 5. U is a seeded uniform ranking. Each episode is `ordered.primary_v2` with its
own seed namespace:
- shared static check;
- fixed-order relocation planning in rank order under the declared allowance;
- COMMIT of the first relocation witness;
- executed and re-observed moves;
- **one** target attempt with SAFE_RETREAT;
- no fallback.

Every attempted episode passed its 12-check protocol audit (one uniform episode was CPU-censored and has no audit).

| arm | success | target certified infeasible | target unresolved | no witness | abstained | censored | minimal-length successes (= best verified catalogue length) | mean J of successes |
|---|---|---|---|---|---|---|---|---|
| A | **6 / 12** | 2 (both: chose **empty** repair, false feasibility) | 1 | 1 | 2 | 0 | 2 | 3.22 |
| B | 6 / 12 | 2 | 2 | 0 | 2 | 0 | 1 | **1.83** |
| C | **7 / 12** | 3 | 2 | 0 | 0 | 0 | 3 | 1.95 |
| U (uniform) | 6 / 12 | 3 | 2 | 0 | 0 | 1 | 3 | 3.09 |

- **No learned arm meaningfully outperforms the uniform control** on executed success (n = 12; differences of one
  episode).
- B and C choose lower-travel successful repairs than A and U.
- Minimality is only *restricted-catalogue*: a success is minimal if its length equals the shortest VERIFIED catalogue
  repair of that root. Several successes used one extra move.
- These are **new, independent executions**, recorded in `runs/p7/execution/<arm>__<root>/` with `relocation.npz`
  and `target_witness.npz`. They are not replays of teacher records.

## 5. What is and is not established

| hypothesis | result |
|---|---|
| **H-R** representation | **Supported (engineering):** edit-specific features and root-consistent beliefs work; B's scene-effect MAE is the best of all arms on fresh roots (0.22) |
| **H-O** optimization | **Partly:** the losses are balanced and stable, but clipping stays frequent and B / C get fewer epochs at matched CPU |
| **H-I** interaction | **Not established:** κ MAE 0.58–0.76, sign accuracy ≤ 0.48 on fresh roots; coupling biases towards +1 and the no-coupling model biases away from it |
| coupling advantage | **Rejected:** B-no-coupling ≥ B on accuracy, NLL, ECE and κ MAE (contract §11) |
| **H-P** planning | **Not established:** one-shot success A 6, B 6, C 7, uniform 6 of 12 |
| **H-G** generalization | **Mixed:** feasibility AUROC 0.92–0.97 transfers to new families; interaction and selection do not |
| C vs B | C is not worse on test accuracy (0.833 each), has 7 / 12 one-shot successes, but needs clip 1 (≈ 95 % clipped); P7a's instability is reduced, not removed |
| A vs C (GRU held common, explicit z added) | no feasibility gain from explicit z; gain only on scene effects |
| non-energy control S | as accurate as the best energy model; energy structure is not what drives feasibility accuracy here |

**Limitations.**
- Templated mechanisms (pose-screen access, place access, link-0 sweep), identical discs, 8 × 8 grid.
- 19 of 28 κ values are operational (place side, A7).
- 201 NOT_RUN from motion-planner exhaustion under fixed caps.
- Small test denominators (7 κ roots, 3 order pairs, 12 episodes per arm).

## 6. Visualizations (`visualizations/p7/`, index `visualizations/p7/README.md` with SHA-256 of all 297 files)

- **P7b** (`visualizations/p7/b/`, guarded **695.1 / 1,800 CPU-s**):
  - per root (`roots/<root>_<family>_<split>/`, 48 roots): `scene_start.png`, `catalogue.png`, `executed_repairs.gif`
    (recorded witnesses only), `order_comparison.gif`, `interventions.gif` ("HYPOTHETICAL SCENE EDIT - NOT A ROBOT
    RELOCATION"), `candidate_orders.gif` ("PROPOSED, NOT EXECUTED");
  - models (`models/`): `ABC_side_by_side.gif` (synchronized A | B | C on the same sealed test roots: calibrated p_R,
    selection, per-edit marginals, κ̂ vs teacher κ), `A_training.gif`, `B_training.gif`, `C_training.gif`,
    `ABC_boltzmann_samples.gif`, and **`oneshot_episodes.gif`** (all 48 new one-shot episodes, animated only from each
    episode's own recorded arrays and labelled "NEW ONE-SHOT EXECUTION (recorded)").
- **P7a** diagnostic renders (`visualizations/p7/a/`): see report 0022.

Trace sampling was 8 frames per move and 10 per target to fit the cap, always from the same recorded arrays.

## 7. Accounting

| stage | used | cap |
|---|---|---|
| P7b static (construction + admission) | 905.3 CPU-s | 1,200 |
| P7b teacher collection | 17,674.6 CPU-s, 18,602 s wall | 20,000 / 48,000 |
| P7b training / ablation | 11,141.7 CPU-s, 11,144 s wall | 12,000 / 24,000 |
| P7b one-shot | 1,930.0 CPU-s (48 episodes) | 9,000 / 18,000 |
| P7b GIF / report rendering | 695.1 CPU-s | 1,800 |
| final full suite (guarded) | 514.2 CPU-s; **316 passed**, exit 0 | — |
| unguarded development checks (smoke tests, previews; no teacher calls) | ≈ 600 CPU-s | — |

**Commits.** Code, tests, plan / decisions / attempts, recorded unit arrays, training checkpoints (23), one-shot
episodes and GIFs, selected by explicit path. Untouched: root-PDF deletions, untracked user files, and P4–P6 evidence.

## 8. Per-root ledger (V / C / B / U / NR = VERIFIED / CERTIFIED / BUDGET / UNKNOWN / NOT_RUN)

| root | fam | split | wave/batch | start | attempt | queries | V/C/B/U/NR | CPU-s | verified move counts |
|---|---|---|---|---|---|---|---|---|---|
| p7_2026102401 | KP | train | 1/1 | S2 | 7 | 17 | 1/7/1/0/8 | 689.2 | — |
| p7_2026102402 | KP | validation | 1/1 | S3 | 12 | 12 | 2/4/3/0/3 | 691.3 | 2 |
| p7_2026102403 | KP | train | 1/2 | S0 | 5 | 17 | 6/7/4/0/0 | 84.2 | 2, 3 |
| p7_2026102404 | KP | test | 1/2 | S1 | 19 | 17 | 6/7/4/0/0 | 66.0 | 2, 3 |
| p7_2026102405 | KM | train | 1/1 | S3 | 2 | 16 | 8/3/1/1/3 | 816.2 | 1, 2, 3 |
| p7_2026102406 | KM | validation | 1/1 | S0 | 4 | 16 | 11/3/2/0/0 | 418.0 | 1, 2, 3 |
| p7_2026102407 | KM | train | 1/2 | S1 | 6 | 16 | 13/3/0/0/0 | 472.0 | 1, 2, 3 |
| p7_2026102408 | KM | test | 1/2 | S2 | 6 | 16 | 13/3/0/0/0 | 381.0 | 1, 2, 3 |
| p7_2026102409 | K0 | train | 1/1 | S0 | 5 | 16 | 1/7/1/1/6 | 775.0 | — |
| p7_2026102410 | K0 | validation | 1/1 | S1 | 1 | 16 | 1/7/2/1/5 | 702.6 | — |
| p7_2026102411 | K0 | train | 1/2 | S2 | 2 | 16 | 9/7/0/0/0 | 40.8 | 1, 2, 3 |
| p7_2026102412 | K0 | test | 1/2 | S3 | 0 | 16 | 1/7/1/1/6 | 759.6 | — |
| p7_2026102413 | ORD | train | 1/1 | S1 | 0 | 32 | 3/21/8/0/0 | 101.9 | 4 |
| p7_2026102414 | ORD | validation | 1/1 | S2 | 4 | 23 | 3/15/5/0/0 | 45.8 | 3 |
| p7_2026102415 | ORD | train | 1/2 | S3 | 1 | 17 | 5/11/1/0/0 | 32.9 | 2, 3 |
| p7_2026102416 | ORD | test | 1/2 | S0 | 5 | 32 | 5/21/6/0/0 | 121.2 | 4 |
| p7_2026102417 | MOT | train | 1/1 | S3 | 145 | 17 | 5/7/5/0/0 | 115.4 | 2, 3 |
| p7_2026102418 | MOT | validation | 1/1 | S0 | 14 | 17 | 5/7/5/0/0 | 66.1 | 2, 3 |
| p7_2026102419 | MOT | train | 1/2 | S1 | 5 | 17 | 5/7/5/0/0 | 65.5 | 2, 3 |
| p7_2026102420 | MOT | test | 1/2 | S3 | 71 | 17 | 5/7/5/0/0 | 71.4 | 2, 3 |
| p7_2026102421 | ALT | train | 1/1 | S3 | 0 | 27 | 17/3/0/1/6 | 437.4 | 1, 2, 3, 4 |
| p7_2026102422 | ALT | validation | 1/1 | S0 | 8 | 27 | 0/3/0/0/24 | 0.0 | — (batch cap before reference) |
| p7_2026102423 | ALT | train | 1/2 | S1 | 5 | 27 | 3/3/1/0/20 | 684.6 | 1, 4 |
| p7_2026102424 | ALT | test | 1/2 | S2 | 3 | 27 | 1/3/1/0/22 | 758.9 | — |
| p7_2026102425 | KP | train | 2/3 | S0 | 1 | 17 | 5/7/5/0/0 | 442.9 | 2 |
| p7_2026102426 | KP | validation | 2/3 | S1 | 31 | 17 | 6/7/4/0/0 | 53.5 | 2, 3 |
| p7_2026102427 | KP | train | 2/4 | S2 | 12 | 17 | 6/7/4/0/0 | 74.0 | 2, 3 |
| p7_2026102428 | KP | test | 2/4 | S3 | 25 | 17 | 0/7/1/0/9 | 524.9 | — (reference BUDGET_INFEASIBLE) |
| p7_2026102429 | KM | train | 2/3 | S1 | 0 | 16 | 0/3/1/0/12 | 583.9 | — (reference BUDGET_INFEASIBLE) |
| p7_2026102430 | KM | validation | 2/3 | S2 | 9 | 16 | 3/3/1/1/8 | 834.5 | 2, 3 |
| p7_2026102431 | KM | train | 2/4 | S3 | 2 | 16 | 4/3/1/1/7 | 837.9 | 1, 2, 3 |
| p7_2026102432 | KM | test | 2/4 | S0 | 1 | 16 | 13/3/0/0/0 | 577.1 | 1, 2, 3 |
| p7_2026102433 | K0 | train | 2/3 | S2 | 0 | 16 | 8/7/1/0/0 | 319.6 | 1, 2, 3 |
| p7_2026102434 | K0 | validation | 2/3 | S3 | 1 | 16 | 9/7/0/0/0 | 41.0 | 1, 2, 3 |
| p7_2026102435 | K0 | train | 2/4 | S0 | 0 | 16 | 5/7/1/0/3 | 725.6 | 1, 2, 3 |
| p7_2026102436 | K0 | test | 2/4 | S1 | 0 | 16 | 9/7/0/0/0 | 76.9 | 1, 2, 3 |
| p7_2026102437 | ORD | train | 2/3 | S3 | 6 | 32 | 4/22/6/0/0 | 70.4 | 3, 4 |
| p7_2026102438 | ORD | validation | 2/3 | S0 | 12 | 32 | 3/21/8/0/0 | 123.3 | 4 |
| p7_2026102439 | ORD | train | 2/4 | S1 | 2 | 32 | 5/21/6/0/0 | 118.9 | 4 |
| p7_2026102440 | ORD | test | 2/4 | S2 | 1 | 32 | 2/22/8/0/0 | 238.2 | 3 |
| p7_2026102441 | MOT | train | 2/3 | S1 | 14 | 17 | 3/7/4/0/3 | 682.3 | 2, 3 |
| p7_2026102442 | MOT | validation | 2/3 | S3 | 15 | 17 | 5/7/5/0/0 | 279.2 | 2, 3 |
| p7_2026102443 | MOT | train | 2/4 | S0 | 36 | 17 | 5/7/5/0/0 | 65.9 | 2, 3 |
| p7_2026102444 | MOT | test | 2/4 | S1 | 42 | 17 | 1/8/1/1/6 | 881.1 | — |
| p7_2026102445 | ALT | train | 2/3 | S1 | 8 | 27 | 17/3/1/0/6 | 811.8 | 1, 2, 3, 4 |
| p7_2026102446 | ALT | validation | 2/3 | S2 | 0 | 27 | 24/3/0/0/0 | 230.8 | 1, 2, 3, 4 |
| p7_2026102447 | ALT | train | 2/4 | S3 | 3 | 27 | 3/3/1/0/20 | 684.5 | 1, 4 |
| p7_2026102448 | ALT | test | 2/4 | S0 | 3 | 27 | 0/3/0/0/24 | 0.0 | — (batch cap before reference) |

## 9. Recommendation (not started; needs fresh authorization)

1. **Do not scale data yet.** Neither the coupling hypothesis nor model-chosen repair success is supported. More roots
   of the same mechanisms would mostly buy cost (motion-planner exhaustion dominates).
2. **Make interaction learnable with balanced exposure.** Collect κ-balanced training data (equal +1 / 0 / −1 per
   family; K− and K0 were under-represented), then re-test B against B-no-coupling. Add an explicit test where the edit
   features alone must separate the three signs.
3. **Cost and coverage.** Order each root's catalogue cheapest-first under a declared rule, or raise per-root caps
   (a new budget decision), to avoid 201 NOT_RUN. Consider deciding A7 (place-side certificate scope).
4. **Planning.** Run a larger one-shot comparison (more test roots, matched geometry + full-motion search baseline)
   before any architecture decision. On the present evidence the simpler A / S predictors are not worse than B / C on
   feasibility, while B / C pick lower-travel repairs.

STOP. Not started: G5 / G6, 3D, hardware, revised teacher policy and further data scaling.
