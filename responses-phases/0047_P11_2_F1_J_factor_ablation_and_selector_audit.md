# 0047 — P11-2: F1 static head, J travel head, and conservative re-evaluation of F2–F5 / DINOv2

**Actual result.**
- **Gate:** `runs/p11/components/P11_COMPONENTS_GATE.json` → **PASS** (engineering).
- **Data status:** all P11-2 evidence is **POST-HOC on the disclosed 65 P10b blind roots** (exploratory).

| component | what was measured | status |
|---|---|---|
| **F1** (static supervision) | matched 3-seed retrain with the static BCE weight 0 (same architecture and 698,154 parameters) | static validity is learned only when supervised; **no identified benefit for repair selection** (TOP1 −0.031 [−0.103, +0.041]). The H1 effect (−0.09, 9 / 9 roots) is exploratory |
| **J** (travel head) | selector variants on frozen B / C | predicts witnessed travel reasonably (Spearman 0.71–0.79) but is **not practically identified** as useful: the tie-break is reached on only 6–20 / 65 roots, and removing J changes 4–9 choices with success within ±2 roots |
| **F2–F5, DINOv2** | Holm across the 32-test exploratory ablation family | only **F2 order** and **DINOv2** remain significant. The P10e F3 / F5 complementarity effects (9 / 9 roots each) **do not survive family-wise correction** (Holm p 0.117) and are reclassified UNDERPOWERED |

## 1. F1: learned static head vs analytic veto

**How F1 enters the system:**
- **Objective:** F1 contributes only the `static` BCE term of `unique_factor.total` (λ_static = 1), fed by `m.static(R, xy_end)` on candidates and on the seeded static-check placements (`uf.losses`). It is **not** a variable of P(z | r).
- **Deployment:** F1 enters only through `E_static`, which is the 4th key of the TOP1 sort (after move count, J, C_d), via the row energy.
- **Analytic veto:** a separate, unchanged geometric rule (`p10_protocol.static_veto`). On the blind and H9 roots it vetoes **nothing**, so the veto is held fixed for both arms.

**Control:** keyed B retrained with λ_static = 0. Everything else is identical: architecture (698,154 parameters, layers untouched), data, sampler, 400 updates, seeds 0–2, and validation-only checkpoint selection and calibration. Training took 1,062 CPU-s. The enabled condition is the P10c F-K-B runs, whose configuration differs only in λ_static.

| | F1 on (s0 / s1 / s2) | F1 off (s0 / s1 / s2) |
|---|---|---|
| static AUROC (blind; 23,256 analytic labels, **130 negatives**) | 0.773 / 0.798 / 0.782 | 0.572 / 0.606 / 0.498 |
| static NLL | 0.032 / 0.032 / 0.032 | 0.65 / 0.67 / 0.68 |
| validation own NLL | 1.47 / 1.53 / 1.43 | 1.72 / 1.41 / 1.77 |

Static accuracy (0.99 vs 0.58–0.85) is dominated by class imbalance and is not informative.

**Repair endpoints** (F1 off − on; seed mean per root; exploratory):

| endpoint | difference | 95 % CI | roots | p |
|---|---|---|---|---|
| H1 κ error | −0.090 (off worse) | [−0.146, −0.043] | 9 / 0 roots | 0.004 |
| per-root NLL | +0.019 | [−0.023, 0.065] | — | 0.46 |
| omission | −0.048 | [−0.115, 0.010] | — | — |
| order | 0.000 | — | — | — |
| TOP1 label success | 0.697 vs 0.728: −0.031 | [−0.103, 0.041] | 11 vs 10 roots | 1.0 |

The TOP1 row scores the chosen candidate by its teacher label. 3 F1-off choices had no executed episode; executed outcomes are reported where a P10d episode of the same (root, repair) exists.

**Status:** F1 is **NOT_IDENTIFIED** as improving repair selection. The H1 sensitivity is suggestive but rests on 9 roots and is exploratory.

## 2. J: travel-cost head in selection

- **Training signal:** J is trained on witnessed first-seed travel cost (log-Huber, `uf.losses`).
- **Deployment:** J enters only as the 2nd sort key among *admitted* candidates with the minimal move count.
- **Variants:** on identical frozen checkpoints and identical admitted pools:
  - default (J);
  - no-J (C_d, energy, id);
  - shuffled-J (seeded permutation);
  - oracle-J (witnessed J; **offline upper bound only**).

| checkpoint | abstain | tie-break reached (≥ 2 admitted at min moves) | choices changed: no-J / shuffled / oracle | label success default → no-J | executed success default → no-J (known episodes) |
|---|---|---|---|---|---|
| K-B s0 | 16 | 6 | 4 / 3 / 5 | 44 → 43 | 44 → 43 |
| K-B s1 | 5 | 16 | 9 / 7 / 10 | 48 → 50 | 47 → 49 |
| K-B s2 | 9 | 8 | 5 / 6 / 5 | 50 → 50 | 49 → 49 |
| K-C s0 | 7 | 20 | 6 / 12 / 11 | 50 → 51 | 49 → 50 |
| K-C s1 | 13 | 9 | 5 / 6 / 7 | 43 → 43 | 43 → 43 |
| K-C s2 | 6 | 10 | 4 / 4 / 4 | 49 → 48 | 48 → 47 |

All counts are out of 65 blind roots.

- **J regression** (100 witnessed blind repairs): MAE 0.47–0.52 on a mean witnessed J of 1.80; Spearman 0.71–0.79.
- **Status: NOT_PRACTICALLY_IDENTIFIED.** J predicts cost but rarely decides a choice, and changing it does not change success. Shuffled and oracle J perform the same within noise.

## 3. F2–F5, DINOv2, keyed vs unique, C (re-verified)

**Definitions verified by construction** (`COMPONENTS.json → ablations.definitions`):

| arm | modules | params |
|---|---|---|
| B-F2 | no predecessor module (`order_mode = none`) | 599,338 |
| B-F3 | no `pair_scene` | 648,745 |
| B-F4 | no `pair_omit` | 648,745 |
| B-F5s | no `cpl`, no HO | 566,183 |
| B-F5q | no HO | 615,592 |
| B-V0 | same as B (698,154), inputs zeroed | 698,154 |
| B-U | same as B, unkeyed | 698,154 |

All ablations were retrained from scratch. **Capacity confound:** the ablations have fewer parameters than B, by 0 to 132k.

**Exploratory family (8 arms × 4 endpoints = 32 sign tests, Holm within the family):**

| removed | order Δ | H1 Δ (−: worse) | NLL Δ (+: worse) | omission Δ | survives family Holm? |
|---|---|---|---|---|---|
| F2 | **−0.718** [−0.833, −0.603] | −0.031 | +0.059 | +0.006 | **yes** (order) |
| F3 | −0.013 | −0.143 [−0.239, −0.063] (raw p 0.004) | +0.012 | −0.013 | no (Holm 0.117; n = 9) |
| F4 | 0 | −0.038 | −0.025 | +0.016 | no |
| F5s | 0 | −0.099 (raw 0.004) | +0.033 (raw 0.006) | 0 | no (0.117 / 0.142) |
| F5q | 0 | −0.040 (raw 0.004) | +0.024 | −0.026 | no |
| V0 (DINOv2 off) | −0.192 | −0.072 | **+0.089** [0.049, 0.133] | −0.003 | **yes** (NLL, Holm 0.0016) |
| U (unkeyed) | 0 | −0.035 | +0.012 | +0.006 | no |
| C (GRU) | 0 | −0.042 (raw 0.004) | +0.035 | −0.003 | no |

**Interpretation limits:**
- A null effect is **not** proof of redundancy everywhere. These families, at these sample sizes (9 H1 roots, 26 order roots), cannot show small effects.
- Shared encoders can absorb a removed factor's role.
- The H1 endpoint has a minimum attainable sign-test p of 0.0039 with 9 roots, so no H1 effect can survive a 32-test correction.

**Artifacts:**
- `runs/p11/components/COMPONENTS.json`
- `runs/p11/components/F1_TOP1.json`
- `runs/p11/components/F1_BLIND_EVAL.json`
- F1-off checkpoints and run records under `runs/p11/components/`
