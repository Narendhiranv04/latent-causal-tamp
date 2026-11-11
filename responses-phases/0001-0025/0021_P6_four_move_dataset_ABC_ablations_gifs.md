# 0021 — P6: expanded 2D four-move dataset, A/B/C retraining with ablations, scene-based GIFs

**Previous turn sync:** `15e1285` (P5: corrected B/C layout, D3-lite batch 1, first A/B/C proof of concept).
**Authorization:** user message authorizing implementation and execution of P6 per
`instruction-phase-md/P6_Expanded_2D_Four_Move_Dataset_ABC_Ablations_and_GIF_Execution.md`.
**Verdict:** **PASS** for the whole mandatory P6 scope. Every gate passed and every cap held. The learned-model claims are mixed and stated
in §7. B's coupling advantage and B/C learning of interaction structure are **NOT ESTABLISHED**. The optional one-shot simulator was **NOT_RUN**.

---

## 1. What was built (code)

| file | status | role |
|---|---|---|
| `config_v2_r4.toml` | new | Overlay of `config_v2.toml`, identical except `[proposal].move_cap = 4` (hash `sha256:f84190dbf55a2…`). `config_v2.toml` is unchanged (`sha256:fd721f1578009…`). |
| `zlayout_r4.py` (90 lines) | new | `Z_LAYOUT_V3_R4`: z0, zS[A], zS[B], zS[A+B], zR and zO[0..3], with K ≤ 9 active fields (512 states). Aliases are refused and nuisance edits are excluded. Supports the uniform reference measure (`E + T·K·ln2`) and a `raw` switch that reproduces P5. |
| `abc_models.py` | modified, backward compatible | Options added: `vision` (geometry-only), `extra` (capacity-matched A), `measure` and `higher_order` (masked MLP residual φ_HO(r, z)). The pairwise coupling is computed in one batched call and an exact per-pass memo covers `order()` and the scene slots. Defaults reproduce P5, and all 11 P5 checkpoints load with `strict=True`. |
| `abc_train.py` | modified, backward compatible | Analytic `static_checks` loss, `total()`, gradient clipping (pre/post norms logged), NaN/Inf guard, validation-only early stopping with best-state restore, and a snapshot hook used only for visualizations. |
| `p6_scenes.py` (287) | new | Four families, start strata, static intent predicates, ≤ 24-query catalogues with omission closure, and the frozen plan. |
| `p6_run.py` (249) | new | Four-batch collection with per-query, root, batch and aggregate caps, the censoring stop rule, predeclared gates, sealed holdout, and resumable progress. |
| `p6_learn.py` (92), `p6_train.py` (217) | new | V3 learner view with historical development data (training only), priority-ordered runs, baselines, cap-4 sampler check, and a single holdout evaluation. |
| `p6_viz.py` (277), `p6_viz_models.py` (146) | new | PNG and GIF output built from recorded data only, with SHA-256 sidecars and `visualizations/README.md`. |
| `run.py` | modified | `p6-collect`, `p6-train` and `p6-viz` subcommands. |
| `tests/test_p6_math.py`, `test_p6_plan.py`, `test_p6_eval_viz.py` | new | 22 tests, listed in §2. |

Every module stays under the ~300-line review trigger.

**Defect caught before use.** The batched-coupling refactor reused the name `j` and overwrote the travel cost `J` with a pair-index tensor.
The smoke test on real data caught it before the training run, because the sampler check failed. It is fixed, and a regression test now
asserts that `J` and `E_bar` are scalars. No reported number used the defective code.

## 2. Foundation and pre-collection gates

**Mathematics (`tests/test_p6_math.py`)**
- K = 4, 5, 7, 8 and 9 hold for m = 0..4 moves, and m = 4 gives exactly 512 states. V3 equals V2 for m ≤ 3. Five moves and nuisance-in-layout are both refused.
- Uniform measure: equal raw energies give equal Ē for every K (raw Ē(m=4) is more than 3 nats below Ē(m=0)). P(z | r) is unchanged and normalized.
- Exact detailed balance of the G4B kernels holds for Ē with unequal K at move cap 4 (states of length 0–4 all present).
- **Five-factor audit of the coupling (parity fixture).** The joint B/C energy is E(r,z) = E_static(r) − Σ_k s_k(r) z_k − ½ zᵀW(r)z [− φ_HO(r,z)] + T·K·ln2. Its factors are:
  1. static (unary/pair endpoint support);
  2. scene logits s_zS;
  3. order logits s_zR and s_zO (prefix-pair in B, GRU in C);
  4. coupling W(r), quadratic;
  5. travel cost J (outside the z-sum, log-Huber supervised).

  On a 3-outcome parity target (exp(−3·parity)), the best quadratic fit stays at KL = 0.502 nats: a representation limit, since a pairwise binary energy cannot express third-order interaction. Adding the smallest masked residual φ_HO = MLP([Σ_k z_k u(v_k), 0]) reaches KL = 3.8e-5. B/C primaries therefore use φ_HO, and quadratic-only is a named ablation.
- **Four-action order fixture.** On all 24 permutations of 4 moves under "A before B", A, B and C separate positives from negatives, and A-no-order is provably invariant (spread < 1e-9). A conjunctive rule ("A before B and C before D") was not separated by B within 240 epochs; this is recorded and was not tuned away.
- Capacity: A with `extra=515` has 516,263 parameters, within 1% of C. Geometry-only ignores visual input. Clipping bounds the post-clip norm at ≤ 1.0, the non-finite guard stops cleanly, and φ_HO receives gradient.

**Gates**
- **G4B** passed under a guard: 74.6 CPU-s (cap 160), `runs/p6/g4b`.
- **Full regression** passed under a guard: 303 passed, 0 failed, 6/6 replays, 459.4 CPU-s (cap 800), `runs/p6/regression`.
- **Post-stage full suite** (after the model edits made during P6): 305 passed, 361 CPU-s, guarded, `runs/p6/final_tests`.

**Recorded integrity note on P5 (P5 evidence not modified).** `runs/p5/regression/manifest.json` lists `__pycache__/countcalls.cpython-313-pytest-9.1.1.pyc`, which was deleted after the manifest was written in P5 and never committed. All other P5 manifest entries are byte-identical. For P6, `__pycache__` was removed before any manifest was written.

## 3. Construction: families, roots, starts, splits

All construction is static and outcome-blind; no teacher or planner was called. It uses the trusted pose-only screens (`skill.screen_pick` / `screen_place`) at the fixed start.

**Mechanism, measured before design.** A disc whose N, S and W cells are occupied has 0 screen-passing grasps (48/48 certified rejections). Removing one neighbour restores grasps. The same holds for placing at a goal whose N, S and W cells are occupied. Every object, goal and destination lies outside the link-0 annulus (ρ ≥ R0 + 0.01 m, R0 = 0.4608 m), so no relocation can create a joint-0 sector barrier.

**Families**

| family | intent |
|---|---|
| F1 access order | B → A → target. A's grasp needs B gone; the target needs both gone. Main repair has 2 moves. |
| F2 dual blockers | A closes the target's grasp side, B the goal's place side. Main repair has 2 moves; κ intent is +1; not built on goal occupancy. |
| F3 3/4-step chain | C → B → A on the grasp side, plus D on the place side. **Main repair has 4 moves (K = 9).** |
| F4 alternatives | A plus goal occupant G; A's alternative destination closes the goal's place side (destination dependency); nuisance object and non-home starts. |

**Start strata** (predeclared, collision-checked per root):
- S0 = (π/2, π/2, π/2)
- S1 = (π/2, −π/2, −π/2)
- S2 = (π/4, π/2, π/2)
- S3 = (3π/4, −π/2, −π/2)

**Splits and schedule.** Splits were predeclared per family (2 train / 1 validation / 1 holdout) and batches 1–4 each contain one root per family. Root seeds are 2026102301–16. Uniqueness is enforced against every historical geometry and between P6 (target, goal) pairs.

**Cost.** Construction took 12.1 CPU-s with 116 screen calls. The ledger is `runs/p6/collect/construction_attempts.jsonl`.

| root | family | split | batch | start | target | goal | attempt | queries | V/C/B/U | root CPU-s |
|---|---|---|---|---|---|---|---|---|---|---|
| p6_2026102301 | F1 | train | 1 | S0 | 14 | 54 | 4 | 19 | 6/12/1/0 | 48.5 |
| p6_2026102302 | F2 | train | 1 | S1 | 21 | 47 | 0 | 18 | 7/8/3/0 | 63.4 |
| p6_2026102303 | F3 | validation | 1 | S2 | 47 | 13 | 1 | 24 | 5/15/4/0 | 110.0 |
| p6_2026102304 | F4 | holdout | 1 | S3 | 23 | 55 | 13 | 18 | 6/10/2/0 | 81.3 |
| p6_2026102305 | F1 | validation | 2 | S1 | 54 | 30 | 4 | 19 | 6/12/1/0 | 35.7 |
| p6_2026102306 | F2 | holdout | 2 | S2 | 55 | 22 | 0 | 18 | 7/8/3/0 | 119.8 |
| p6_2026102307 | F3 | train | 2 | S3 | 55 | 21 | 3 | 24 | 4/15/5/0 | 87.4 |
| p6_2026102308 | F4 | train | 2 | S0 | 14 | 46 | 0 | 18 | 6/10/2/0 | 67.4 |
| p6_2026102309 | F1 | train | 3 | S2 | 38 | 14 | 0 | 19 | 6/12/1/0 | 104.9 |
| p6_2026102310 | F2 | train | 3 | S3 | 45 | 15 | 1 | 18 | 7/8/3/0 | 125.7 |
| p6_2026102311 | F3 | holdout | 3 | S0 | 15 | 47 | 0 | 24 | 5/15/4/0 | 132.4 |
| p6_2026102312 | F4 | validation | 3 | S1 | 53 | 22 | 0 | 18 | 6/10/2/0 | 55.1 |
| p6_2026102313 | F1 | holdout | 4 | S3 | 30 | 55 | 1 | 19 | 6/12/1/0 | 41.4 |
| p6_2026102314 | F2 | validation | 4 | S0 | 54 | 22 | 0 | 18 | 7/8/3/0 | 84.8 |
| p6_2026102315 | F3 | train | 4 | S1 | 23 | 54 | 2 | 24 | 5/14/5/0 | 112.4 |
| p6_2026102316 | F4 | train | 4 | S2 | 46 | 13 | 11 | 18 | 6/10/2/0 | 67.4 |

Queries include each root's separate reference root. V/C/B/U = VERIFIED / CERTIFIED / BUDGET_INFEASIBLE / UNKNOWN.

**Catalogue and plan.** Each root has at most 24 queries:
- the reference root and the empty repair;
- singles, swaps/pairs, triples, and quads (main + 2 permutations, F3 only);
- the main repair's omissions, plus an omission closure in catalogue order up to the cap;
- edits A, B and A+B, one nuisance edit and one alternative destination.

The plan totals 316 queries and 948 seed units (caps 384 / 1,152), with plan hash `sha256:22f408cddd99…`. The policy is unchanged 2D-ABC-OPNEG-v1 (`sha256:df54878deb69…`, seeds 20261021–23).

## 4. Collection (OPNEG-v1, process-tree guarded, 1 worker)

**Static admission.** 211.2 CPU-s (static total 223.3, cap 700) with zero planner calls by the coordinator. **179 of 316 queries** were settled by accepted certificates:

| certificate | count |
|---|---|
| TARGET_PICK | 135 |
| GOAL_OVERLAP | 24 |
| ORDER_FIRST_ACTION | 16 |
| FIRST_MOVER | 4 |

**Teacher.** 137 queries went to the teacher, using **221 seed attempts, all `COMPLETED` (0 censored)**. The mean attempt cost was 5.8 CPU-s and the maximum 66.9 CPU-s. Every witness came from the first seed. All 42 BUDGET_INFEASIBLE queries ended on clean screen-exhaustion terminals: 72 seed attempts PLACE_SCREEN_EXHAUSTED_CERTIFIED, 39 PICK_…_CERTIFIED, 12 PICK_…_UNCERTIFIED and 3 PLACE_…_UNCERTIFIED.

**Outcomes (all 316)**

| status | count |
|---|---|
| VERIFIED | 95 |
| CERTIFIED | 179 |
| BUDGET_INFEASIBLE | 42 |
| UNKNOWN | **0** |
| NOT_RUN | 0 |
| FATAL | 0 |

Development roots: 71 / 134 / 32 / 0. Sealed holdout (opened only after the checkpoints were frozen): 24 / 45 / 10 / 0.

**Compute**

| item | used | cap |
|---|---|---|
| teacher + coordinator | **1,337.4 CPU-s** | 20,000 |
| wall | 1,585 s | 36,000 |
| largest root | 132.4 CPU-s | 1,500 |
| largest batch | ≈ 306 CPU-s | 5,000 |

The censoring stop rule never triggered, and the frozen historical manifests (G4C pilot, POC_S, G4D, P4 pilot, P5 D3-lite, P5 G4E) are unchanged.

**Gates**

| batch | 4-move witnesses (dev, cumulative) | multi-step dependencies | decided order contrasts | nonzero κ | UNKNOWN | GOAL_OVERLAP / decided negatives | complete dev candidates | result |
|---|---|---|---|---|---|---|---|---|
| 1 | 3 | 6 | 3 | 3 | 0/79 | 0/43 | 37 | **PASS** |
| 2 | 5 | 10 | 6 | 6 | 0/79 | 6/88 | 72 | **PASS** (F1 order + F3 multi-step evidence) |
| 3 | 5 | 15 | 7 | 9 | 0/79 | 12/124 | 110 | **PASS** |
| 4 | 8 | 20 | 9 | 12 | 0/79 | 18/166 | 144 | PASS (final) |

Gate rules are frozen in `runs/p6/collect/plan.json` under `gate`; gates read development roots only. In every batch, decided negatives are far above the trivial-goal threshold (GOAL_OVERLAP < 1/3), and complete repairs per teacher kCPU-s were 111–128 against a threshold of 1.

## 5. Evidence: four-move witnesses, order and interaction

**Four-move witnesses.** 11 VERIFIED out of 16 proposed four-move repairs, with 8 on development roots and 3 in holdout.
- Each F3 root's main repair C→B→A→D is VERIFIED from its own start stratum (S2, S3, S0, S1).
- On every development F3 root, **all four omissions of the main repair are decided negative**: every one of the four moves is necessary.
- Example: `seq:p6_2026102303:o02>52.o01>36.o00>30.o03>3` with omissions [0, 0, 0, 0]. Its recorded trajectory is in `visualizations/p6/roots/p6_2026102303_F3_validation/executed_repairs.gif`.
- Moving the place-side blocker first (D, C, B, A) is VERIFIED on 3 of 4 F3 roots. On p6_2026102307 it is BUDGET_INFEASIBLE (operational).

**Outcomes by move count (all roots, ordered queries)**

| moves | VERIFIED | CERTIFIED | BUDGET_INFEASIBLE |
|---|---|---|---|
| 0 | 16 | 16 | 0 |
| 1 | 0 | 60 | 4 |
| 2 | 32 | 48 | 12 |
| 3 | 20 | 16 | 13 |
| 4 | 11 | 4 | 1 |

**Same-endpoint order contrasts.** 9 decided on development roots (49 swap pairs, 40 with equal labels).
- 8 are certified-versus-witness. Example: F1 `o00>4.o01>3` is CERTIFIED (ORDER_FIRST_ACTION) while `o01>3.o00>4` is VERIFIED.
- 1 is operational: in F3 p6_2026102307, the ordering that places D first is BUDGET_INFEASIBLE.

**κ (kind edits).** All 12 development roots have κ = **+1**, with y0 = yA = yB = 0 and yAB = 1.
- **9 are operational**, because one side is a place-side BUDGET negative; no place-side certificate exists (A7 is still open).
- **3 are certificate-only** (F4).
- κ therefore shows one pattern only; this lack of diversity matters for §7.

**B/C pools.** 144 fully decided candidates on development roots, and 12 of 12 development roots are joint-pool-ready. **6 complete K = 9 candidates** (512-state z-pools fully decided).

## 6. Training (one guard)

**Run.** One guard covered the whole worker: **2,428.6 CPU-s** (cap 9,000), 2,430 s wall (cap 18,000), CPU only, 1 thread, `runs/p6/train`. No teacher or planner was called.

**Data.**
- Training: 30 roots / 183 candidates. These are the P6 train roots plus the compatible historical development data (P4 pilot and P5 D3-lite train/validation, V2 layouts), used for training only.
- Validation: 8 P6 roots / 63 candidates.
- Holdout: 8 P6 roots / 63 candidates, loaded once after every checkpoint was frozen.
- 48 balanced analytic static checks (24 invalid, 24 valid placements), none of which are teacher queries.
- Leakage audit passed.

**Protocol.**
- AdamW (lr 1e-3, wd 1e-4), clip at 1.0, early stopping on validation loss only (every 5 epochs, patience 8, best state restored), at most 300 epochs.
- Gradient clipping was active on every step: pre-clip norms reached up to 90 for B, which suggests the raw losses are poorly scaled.
- No non-finite events occurred.
- All 21 runs completed, none NOT_RUN. Certified-only was established because there were 16 P6 budget negatives in training (≥ 8).

**Primary results** (3 optimizer seeds, mean ± sd)

| model | split | accuracy | AUROC | NLL | Brier | rank acc | selection success (4 roots) | scene-effect MAE | omission-effect MAE |
|---|---|---|---|---|---|---|---|---|---|
| A | validation | 0.730±0.042 | 0.841±0.032 | 0.476 | 0.161 | 0.876 | 0.083 | 0.333 | 0.438 |
| **B** | validation | **0.810±0.042** | **0.908±0.016** | **0.400** | **0.130** | 0.935 | 0.333 | 0.431 | **0.335** |
| C | validation | 0.587±0.042 | 0.794±0.013 | 0.796 | 0.272 | 0.934 | 0.333 | 0.431 | 0.508 |
| A | **holdout** | 0.746±0.055 | 0.841±0.043 | 0.477 | 0.163 | 0.881 | 0.000 | 0.334 | 0.440 |
| **B** | **holdout** | **0.799±0.009** | **0.884±0.007** | 0.487 | **0.153** | 0.929 | **0.417** | 0.435 | **0.341** |
| C | **holdout** | 0.582±0.040 | 0.808±0.026 | 0.799 | 0.274 | **0.948** | 0.167 | 0.438 | 0.512 |

**Baselines (holdout)**

| baseline | result |
|---|---|
| Uniform ordered | p = 0.5; expected selection success 0.306; order accuracy 0.5 |
| Analytic geometry | accuracy 1.000, AUROC 1.000, selection 1.000 |

The analytic geometry baseline is a *privileged reference, not a learner*: it uses the same pose screens that defined the families (§3), so it is perfect by construction.

**Ablations (seed 0, holdout)**

| run | accuracy | AUROC | NLL | order accuracy (3 pairs) | selection |
|---|---|---|---|---|---|
| A-capacity (516k params) | 0.698 | 0.826 | 0.590 | 1.00 | 0.00 |
| A-no-order | 0.794 | 0.875 | 0.427 | 1.00 | 0.00 |
| A-geometry | 0.635 | 0.726 | 0.649 | 0.00 | 0.00 |
| A + certified-only | 0.714 | 0.848 | 0.528 | 1.00 | 0.00 |
| B-no-coupling | **0.825** | **0.913** | **0.385** | 1.00 | 0.25 |
| B-quadratic (no φ_HO) | 0.825 | 0.873 | 0.691 | 1.00 | 0.50 |
| B-geometry | 0.698 | 0.780 | 0.689 | 0.67 | 0.00 |
| B + certified-only | 0.810 | 0.898 | 0.424 | 1.00 | 0.75 |
| C-no-coupling | 0.762 | 0.788 | 0.530 | 0.33 | 0.50 |
| C-quadratic (no φ_HO) | 0.508 | 0.824 | 0.997 | 0.00 | 0.25 |
| C-geometry | 0.651 | 0.730 | 1.212 | 0.67 | 0.00 |
| C + certified-only | 0.571 | 0.849 | 0.691 | 0.33 | 0.00 |

**Sampler.** On the F3 validation root (114 canonical states, move cap 4, K ≤ 9), the G4B kernels on the learned energy Ē + λ_d·C_d + λ_q·J pass exact detailed balance (max error 2.2e-16) for A, B and C. Chain-vs-exact total variation after 4,000 steps is 0.12 / 0.12 / 0.11 (diagnostic).

## 7. Interpretation (what is and is not established)

**Established**
1. The 2D generator now produces physical, recorded **four-move** repairs whose four steps are each necessary, from four distinct start strata.
2. It also produces decided same-endpoint order contrasts and decided nonzero κ, at **0 UNKNOWN** and about 7% of the teacher budget.
3. **B is the best learner on held-out roots.** Its accuracy, AUROC and Brier are best among A/B/C on both validation and holdout, with the smallest seed spread (holdout accuracy sd 0.009). Its omission effects are clearly better than A's or C's.
4. Vision helps: every geometry-only ablation is worse than its full model.

**Not established**
1. **B's coupling advantage.** B-no-coupling matches or beats B on every probability metric, so the quadratic coupling adds nothing measurable here.
2. **B/C learning of interaction structure.** For each root, B and C predict the same scene effect for the A, B and A+B edits (e.g. 0.28/0.28/0.28 against observed 0/0/1). Their scene-effect MAE (≈ 0.43) is worse than A's constant-zero prediction (0.33). The κ = +1 structure was not learned.
3. **φ_HO helps on real data.** It is needed for the parity fixture, but on P6 data B-quadratic has equal accuracy and worse NLL, and C-quadratic is worse than C (accuracy 0.51). The dataset's κ has one pattern only, which limits this test.
4. **C (B with the GRU order factor) underperforms B.** It is poorly calibrated: accuracy 0.58 despite AUROC 0.81, with early stops at epoch 10–30. Its rank accuracy is high (0.95), so it ranks reasonably but its probabilities are off.
5. **Order learning.** Validation and holdout each contain only 3 decided order pairs. A-no-order matches A on these roots. Order accuracy is not statistically meaningful at this size.
6. **Selection.** Learned selection (lowest-move candidate with p ≥ 0.5) succeeds on 0–75% of only 4 holdout roots per model. A always selected infeasible short repairs (0/4). Nothing here supports a planning-success claim.

**Caveats**
- 9 of 12 κ and all place-side negatives are **operational** (BUDGET_INFEASIBLE, policy-relative), because the place-side certificate is still disabled (A7).
- Families are designed and narrow: one mechanism (grasp/place access), one κ pattern.
- Every witness came on the first seed, so seed sensitivity was not exercised.

## 8. Visualizations (`visualizations/`, guarded 558.7 CPU-s / 559 s, caps 2,000 / 4,000)

72 GIFs and 32 PNGs (44 MB). Frames run at 10 fps and the final frame is held for 1.2 s. Every file has a `.sha256` sidecar, and `visualizations/README.md` indexes all files with descriptions and hashes.

**Per root** (`visualizations/p6/roots/<root>_<family>_<split>/`, all 16 roots):
- `scene_start.png`: roles, goal and start stratum, with the reference scene.
- `catalogue.png`: every query with its teacher status.
- `executed_repairs.gif`: **recorded witness arrays only**, main repair first, up to 4.
- `order_comparison.gif`: same-endpoint pairs side by side. Verified sides animate; certified, budget and unknown sides are static panels saying so (e.g. "CERTIFIED INFEASIBLE (ORDER_FIRST_ACTION) - no trajectory exists to show").
- `interventions.gif`: "HYPOTHETICAL SCENE EDIT - NOT A ROBOT RELOCATION", with the recorded target-only witness when VERIFIED.
- `candidate_orders.gif`: "PROPOSED, NOT EXECUTED", with numbered arrows.

**Per model** (`visualizations/p6/models/`):
- `A|B|C_proposals.gif`: lowest-energy proposals, p per candidate against teacher labels, and z marginals.
- `A|B|C_training.gif`: loss curves plus recorded checkpoint predictions over epochs.
- `ABC_side_by_side.gif`: per validation/holdout root, the three models' probabilities and the B/C top joint z-states.
- `ABC_selected_execution.gif`: each model's selected repair, animated only with the teacher's recorded witness of exactly that sequence; otherwise a status panel.

No trajectory was fabricated.

## 9. Optional one-shot simulator: NOT_RUN

Not run, by choice; the optional budget (≤ 12 episodes, ≤ 4,800 CPU-s) was left unused. Every selected repair is a catalogue member the teacher already decided under the same protocol, so a one-shot episode would mostly replay known labels at this selection quality (§7.6). `ABC_selected_execution.gif` shows the recorded teacher outcome of each selection instead.

## 10. Accounting summary

| item | used | cap |
|---|---|---|
| construction + static admission | 223.3 CPU-s | 700 |
| teacher (aggregate, incl. coordinator) | 1,337.4 CPU-s; wall 1,585 s | 20,000; 36,000 |
| per root (max) | 132.4 CPU-s | 1,500 |
| queries / seed attempts | 316 / 221 run (948 planned units, static queries need none) | 384 / 1,152 |
| G4B | 74.6 CPU-s | 160 |
| pre-collection regression | 459.4 CPU-s | 800 |
| training | 2,428.6 CPU-s; wall 2,430 s | 9,000; 18,000 |
| visualizations | 558.7 CPU-s; wall 559 s | 2,000; 4,000 |
| one-shot simulator | 0 (NOT_RUN) | 4,800 |
| development outside guards (static previews, smoke tests, unit-test runs; estimate) | ≈ 600 CPU-s, no teacher or planner calls | — |
| post-stage full suite | 361.4 CPU-s (guarded) | — |

## 11. Recommendation (not started; needs authorization)

1. **Fix the B/C scene slots before scaling.** The zS factor does not separate edits. Give each zS slot edit-specific inputs (moved-object identity and displacement), then re-test κ prediction. This targets the core B/C claim.
2. **Rescale the losses.** The pool term dominates (about 7 of the ~10 total); clipping is always active and C's calibration is poor. Rebalance the loss weights and add a calibration check before more seeds.
3. **Diversify the data.** Use κ ∈ {−1, 0, +1} (redundant blockers, irrelevant pairs) and more order-dependent pairs per held-out root, so order and φ_HO can be tested with real statistical power.
4. **Decide A7 (place-side certificate)** to turn the operational place-side negatives into certified ones.
5. Only then consider the one-shot simulator and larger budgets.

STOP. Not started: G5, G6, 3D work, hardware, and any further budget.
