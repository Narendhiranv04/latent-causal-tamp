# 0082 — P16-0: source / evidence audit and method lock

**Actual result**
- **Base:** `20f775483077a568efb225f22aa93ca619160c53` (P15 final). HEAD equalled origin/main at the start.
- **User-modified files, untouched:** the two root PDFs deleted by the user, and the untracked instruction documents (including `0044`).
- **Historical source manifest:** `runs/p16/audit/HISTORICAL_MANIFEST.json`.
  - Covers 50,082 tracked files under `runs/p10…p15`, `visualizations/` and the 0022–0081 reports plus decision documents, recorded as git blob ids.
  - Also records SHA-256 hashes of 27 core sources and all P13 checkpoints.
  - Dirty tracked historical files: **0**.
  - `p16_eval.verify_historical()` returns `[]`; it is re-run in tests and at every gate.
- **Historical regression:** **457/457** tests and **6/6** archived replays, 828 CPU-s (`runs/p16/regression0/regression_result.json`).
- **Spend:** `audit` 829 of 3,000 CPU-s. No teacher calls, training or prospective labels in P16-0.
- **Gate:** `runs/p16/P16_0_GATE.json` → **PASS**.

## 1. B: source → equation → inference use → label → test → verdict

| component | source (lines) | equation / role | inference use | supervision | historical verdict | P16 lean B |
|---|---|---|---|---|---|---|
| scene / query unaries | `abc7_models.ModelBC7.scene_block` 154–168, `order` 136–152 | s_z0 from the unedited scene, s_zS from edited-scene vectors; s_q = order-head logit on the ordered sequence | P(y_q=1)=σ(s_q/T) when uncoupled | outcome NLL (`unique_factor.log_evidence` 105–116; UNKNOWN summed out) | kept | **kept** |
| F2 order | `ModelBC7._order` (B: prefix-pair `pairo` + `mix`; C: GRU) 140–152 | repair summary g depends on action order | yes | via s_q | **useful** (P13 / P14 / P15) | **kept** (B prefix form; lean C as control) |
| keyed identity | `unique_factor_keyed.instances` 37–74 | one variable per physical query; one sequence per query, enforced (IdentityError) | yes | — | keep (invariance) | **kept** |
| F1 learned static | `Shared.static` + `abc7_train._static` 50–56 | BCE on per-endpoint static labels | admission veto | static checks | static route not supported | **removed** (λ_static = 0); analytic static veto kept |
| F3 scene pair | `pair_scene` in `_pairs` 170–182 | ½ z_S' W z_S over (z0, zS) | coupling | through the joint | reversal P12 / P13; no practical benefit | **removed** |
| F4 omission pair | `pair_omit` | zR–zO pairs | coupling | joint | gain via admission only | **removed** (archived sensitivity only) |
| F5 generic | `cpl` (couple full / quadratic) | scene–repair and zO–zO pairs | coupling | joint | combined F5 harmful on the natural mix | **off**; generic-only is a new arm only if pre-registered |
| F5 higher order | `ho_u`, `ho_s`, `ho_q` (couple full) | HO energy | coupling | joint | underpowered | **deferred** |
| learned J | `cost` head; `unique_factor.losses` travel term | log-Huber on witnessed travel | tie-break | witnessed cost | underpowered / sign error corrected | **removed** (λ_travel = 0); measured travel only |
| joint normalisation | `unique_factor._factors` 75–95, `log_partition` 97–99 (exact contraction) | one conditional normaliser per scene state | marginals | — | exact | with couple = "none" the joint is **exactly a product of Bernoullis** |

**Erratum, P15 0080 §5.** `B-F3pm`, `B-F5spm` and `B-F5qpm` are **separately trained, parameter-matched checkpoints**, not inference masks (`p13_pipeline._arms` 190–207: the factor is removed and the scene head widened, PM widths 320 / 641 / 448). `B-F5spm` removes generic **and** higher-order coupling (abc8 "B-structured"); it is not generic-only. The checkpoints are unchanged; this is a wording correction.

## 2. D: source → equation → inference use → label → test → verdict

| component | source (lines) | equation | use | supervision | verdict | P16 |
|---|---|---|---|---|---|---|
| feasibility head | `d_blockers.ModelD.forward` 49–66 (`feas`) | u = feas(pool(tokens), t, c); P(y0=1)=σ(u) | gate | BCE (`nll` 79–86) | AUROC high, raw feasible recall low on temporary targets | kept |
| blocker unaries | `unary` | a_i(tok_i, t, c) | blocker scores | −λ log P(b \| y0=0) | F1 0.903 (P14 decided cohort) | **kept (pairless default)** |
| blocker pair | `pairf` (`pair=True`) | +½ Σ w_ij b_i b_j, exact `blocker_logp` 72–76 | — | joint | incremental benefit not established | **frozen comparator only** |
| inference | `predict` 89–99 | reports `marg` = P(b_i \| y0=0) and `uncond` = (1−p)·marg separately | — | — | correct (sign / normaliser verified) | kept |
| label semantics | `minimal_sets` 102–125 | union of minimal VERIFIED clearing subsets (`mask`), intersection (`necessary`) | — | — | **defect**: `NO_CLEARING_SET_WITHIN_POOL` returns mask `[0]*n` | **P16 masks it (no blocker NLL)** |
| training items | `p10c_train_eval.d_items` 204–215 | blocker NLL only for proof-grounded, complete, y0=0 masks | — | — | defect active: P13 train 2 and validation 1 NO_CLEARING_SET records were fitted as all-zero masks (of 134 + 38 proof-grounded MINIMAL_SETS) | fixed in P16 D items |
| arbitrary target | `p15_retarget.retarget_scene` 24–31, `build_record` 34–47, `d_predict` 49–61 | rebuilds the scene, target role, goal, current q and DINOv2 view | recursion | — | recalibrated feasibility BA 0.924 (DEV CV); **marginals not validated** | P16-D0 validates the marginals |
| search guide | `p15_bench.Guide.order` 133–161 | reorder only | — | — | no incremental advantage (P15) | reused with a scene-only pool |

## 3. Privileged-input audit (static scan, `P16_0_AUDIT.json`)

| what | where | P16 response |
|---|---|---|
| P15 search movers taken from `ORDERED_TEACHER` catalogue sequences (the constructor's mechanism-aware proposals) | `p15_bench.run_arm` line 194 | kept for historical replay; P16 uses `p16_common.propose_movers`: every movable, non-fixed, non-target object, nearest first, cap 6, omissions recorded |
| frozen B scores the constructor catalogue; frozen D pool = constructor parking objects | — | P16 scores `p16_common.catalogue`: scene-only pool (≤ 3 nearest movers), scene-only parking (first free annulus-safe slot), all lattice subsets, all ordered pairs, the two extreme triple orders |
| oracle guide reads the teacher mask | — | declared non-deployable |

Fixed structures (`root['fixed']` cells) are exposed as **declared static metadata** (`Task.fixed_ids`), never as a label. A test checks that `task_from_root` gives an identical result after the catalogue, parking, roles and predicates are deleted from the root.

## 4. Determinism audit (to be tested in P16-1)

- **Planner:** RRT-Connect is node-budgeted with a per-query seed (`planner.call_seed`). The 300 s wall clock is a safety cap, flagged `wall_clock_cut`.
- **P15's soft CPU-time cap** (process_time) made the search frontier depend on CPU speed and contention.
- **Python's per-process hash seed** could affect any set-derived order.
- **Observed in P15:** the D re-run of PROSP 053 differed from its benchmark record.

## 5. Errata recorded in P16 (no historical file changed)

1. 0080 lean-inference wording (§1 above).
2. The P15 prospective bootstrap CI [0, 0] reflects zero observed discordances; it is not an equivalence interval.
3. The D NO_CLEARING_SET training-label defect (§2).
4. The P12 κ endpoint is abs(mean_seed κ̂ − κ), as corrected in P13; the κ ≡ 0 baseline is always shown.
