# LEGOLAS: final methodology, clean training and complete evaluation (R7–R9)

**Branch** `naren/rss27-fig3-retarget-home`. **Detailed reports:**
- `R7_DATASET_REPORT.md`, `R7_TRAINING_REPORT.md`, `R7_FREEZE.md`
- `R8_K3_FINAL_REPORT.md`, `R8_K45_DATASET_REPORT.md`, `R8_K45_FINAL_REPORT.md`

**Raw records** are under `reports/final/`; figures and CSV/MD/TeX tables are in `reports/final/figures/`; GIFs are in `reports/final/gifs/`.

## Method (as frozen)

- **Placement:** a task-conditioned cVAE (Q2 placement pretraining, then task fine-tuning).
- **Feasibility:** a coupled X/Y model with the original probabilistic contract, pY = σ(b), pX1 = σ(a+w), pX0 = σ(a), and an observed-data likelihood with marginalisation. The Y head is frozen; the X head is a fresh query-relative **GNN**, trained on original replay plus strict local labels of ≤ 3 actions.
- **Selection:** by energy E.
  - ≤ 3 actions: E = −log p11.
  - Longer repairs: E = Σ local marginal-X NLL + terminal-Y NLL, over chunks of ≤ 3 actions with hypothetical pose updates and q_ref connectors. This long-horizon E is a learned surrogate.
- **Composition:** recursive (Fig. 3A) and global (Fig. 3B), up to H = 5.
- **Not used at inference:** no teacher, blocker identities, IK, collision oracle, reference assignment or witness.

All components were retrained from scratch (seeds 0, 1, 2) and selected by predefined VAL rules: 3D `R7:3d_G1_hi_base_s2` + cVAE s1; 2D `R7:2d_G1_hi_base_s0` + cVAE s0; raw X in both.

## RQ1: Which components matter? (K ≤ 3, V3.4 cohort, verified; 0 UNKNOWN)

FINAL task success is **80.3% (3D) / 59.9% (2D)**. The V3.4 production model scores 76.6% / 51.8% on the same roots; the 2D gain of +8.1 pp has p = .002. Figure: `figures/a_ablations.png`.

**Established losses vs FINAL** (95% CI excludes 0):

| Component removed | 3D | 2D |
|---|---|---|
| Order sensitivity | −15.1 | −8.4 |
| Learned proposals (uniform instead) | −14.2 | −17.8 |
| Multiple destinations (top-1 instead) | −17.6 | −23.4 |
| Pool search (single candidate) | −62.3 | −48.7 |
| X/Y evaluation of a complete-repair generator (CR cVAE alone) | −30.1 | −18.8 |
| X/Y coupling | n.s. | −9.6 |
| cVAE vs flow matching | n.s. | −6.1 |

**Not established:** explicit task conditioning, in both domains. A direct Z classifier matches the task rate but fails to stop: correct ABSTAIN on NONE roots is 5.5% in 2D and 60% in 3D, against 97% / 83% for FINAL.

**Generative architecture:**
- The complete-repair cVAE scored by our X/Y is on par with FINAL (+1.3 / −1.5, n.s.).
- So the evidence supports **"X/Y evaluation is necessary"**, not "factorized generation is necessary".

**Representation:**
- The GNN X head with strict local labels has VAL NLL .224 (3D) and .228 (2D). The MLP has .512 / .330 and the original ordered X .590 / .424.
- The supervision and representation effects interact: the GNN gains most from the local labels.

## RQ2: 3D planning vs baselines (V3.4 3D, 239 task roots; same scenes, no oracle K)

Ours scores **80.3%**. Figure: `figures/b_planning3d.png`.

| Baseline | Task success | Note |
|---|---|---|
| E-M4M | 51.0 | 300 CPU-s per root |
| DISCO-Grid | 36.4–38.9 | 3 seeds; never abstains |
| MS-MCTS | 30.5 | 300 CPU-s per root |
| MO-SeGMan | 26.4 | 300 CPU-s per root |
| NOR-Grid | 24.3 | — |
| REAP | not run | No runnable implementation in our workspace |

At a 60 CPU-s cut, the analytical planners fall to 0–3.3%.

## RQ3: 3D target feasibility (395 roots)

Figure: `figures/c_feasibility3d.png`.

| Method | AUROC | TPR / TNR at threshold 0.5 |
|---|---|---|
| **PIGINet** (no image) | **.989** | .892 / .960 |
| SCNet | .974 | .774 / .987 |
| Ours (final Y) | .974 | .828 / .960 |
| GRN | .961 | .828 / .957 |

**Ours is not the best feasibility predictor.** This is reported as measured.

## RQ4: Composition beyond three actions (3D, 99 sealed independent roots, physical verification)

Figure: `figures/d_composition3d.png`. GIFs: `gifs/R8C_*`.

| Method | Verified success |
|---|---|
| **Original final model (H ≤ 3)** | **23/99** |
| **Recursive, Fig. 3A** | **59/99**, 47 of them 4–5-action repairs |
| **Global, Fig. 3B** | **64/99**, 60 of them 4–5-action repairs |
| Flat insertion | 48/99 |
| Production B0 | 8/99 |

- Either REC or GA succeeds on 77/99 roots.
- REC vs GA is not significant (13 vs 18 discordant wins, p = .47). GA costs about 10× the planning time, with 20 deadline stops at 180 s.
- **The original-data-only GNN control collapses** (REC 14, GA 8). Strict local supervision is necessary for composition.
- Planners mostly find valid repairs *other* than the reference: mean witness-action recall is .13–.20.

2D compositional work was discontinued per the contract. The R6 2D negative results stand, and no 2D composition appears in the main table.

## Claim boundaries

- **Not claimed:** no causal claims; no certified minimum K (every L_ref is a verified witness length, `WITNESS_LEN_K_MIN_UNKNOWN`); no universal generalisation.
- **Sizes:** the R8B cohort is 99 roots, below the 200 target, under a prospectively frozen, time-based budget.
- **Tuning:** nothing was tuned on any independent outcome.
- **Known deviations, each disclosed in the sub-reports:**
  - the floor uses the final model;
  - the analytical baselines read scene files by path (`--raw-paths`);
  - SCNet's grasp poses were regenerated;
  - the baseline checkpoints selected on a related split.

## Resources (budget: 1,000 CPU-core-h, 100 GPU-process-h)

Hosts were gvlab2, gvlab, Blackwell and the laptop (all user-authorised). girish was idle for thermal reasons.

| Item | CPU-h |
|---|---|
| R8B generation | ≈ 496 worker-h |
| R8B derivation | 86 |
| Teacher verification, new queries (R8A + baselines) | 49.6 (2D 16.9, 3D 32.7) |
| Analytical baselines | ≈ 55 (395 roots × 3 methods × ≤ 300 CPU-s) |
| R8C planning and physical verification | ≈ 25 |
| R7 / R7b fits and dev checks | ≈ 10 |
| **Total** | **≈ 720 CPU-h** |

**GPU process-h ≈ 35:**
- R7 fits ≈ 1.5;
- R8A predictions ≈ 12;
- R8C and dev planning shards ≈ 20.

**Storage:** never below 20 GiB free on the servers. The laptop's own free space was low at the start (~0.9 GB); I freed 3.3 GB of regenerable caches with the user's permission.
