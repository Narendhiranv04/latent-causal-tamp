# Approach B: post-ablation scientific validation (P0–P7)

| | |
|---|---|
| Branch | `naren/k3-postablation-validation` (from `4aee798929`). Code and reports are in `approach_b_final/validation_k3/`. |
| Host | gvlab2. Work root: `/home/projects/long-horizon/naren_workspace/k3val`. |
| Integrity | Every process ran under `taskset 4-42`, so CPUs 0–3 and 43–47 were always free. The other user's GPU jobs were left untouched. |
| Inputs | The ablation root `k3abl`, **read-only**. Every frozen checkpoint, prediction, seal, lock, manifest and dataset is unchanged (P0: 128/128 seals, all pins). The teacher cache is a copy. |
| Teachers | Unchanged. Every new physical query came from a fixed list hashed before teaching, with no retry. **0 UNKNOWN** outcomes across every evaluated policy. |
| Held-out status | TEST is historically exposed, so every TEST number is exploratory. The V3.4 cohort was **not** used: it is reserved, and spending it needs owner approval. |
| Detail reports | `P0_AUDIT.md`, `COUPLING_F5_REPORT.md`, `DIRECT_FAIRNESS_REPORT.md`, `TASK_RETARGET_REPORT.md`, `ABLATION_CLAIMS_AUDIT.md`, `K_GT6_TEACHER_AUDIT.md`. Figures: `figures/V1–V5`. Tables: `tables/`. |

## What was run (and what was not)

**P0: audit.**
- Re-derived the 36 pooled cells exactly.
- Re-clustered by template family.
- Bonferroni intervals.
- Arm isolation from code.
- Teacher statuses behind every failure.

**Multi-scorer exhaustive pass** (`multipass.py`)
- **Inputs:** the identical frozen M4 pools, scored by 9 frozen scorers (D s0–2, E s0–2, DIRECT s0–2) and 5 D variants (p11, F5 knockout, Y-only, X-marginal, X|Y=1).
- **Parity gate:** it reproduces **every** sealed FULL/E/DIRECT decision, 0 mismatches over 2,234 roots × 9 models.
- **Physical verification:** the argmax repair of every variant on every K1–K3 root of VAL and TEST.
  - New queries: 2D 5,443 and 3D 2,182, plus the cached ones.
  - **With α = β = γ = 0, every (gate, η) rule is a deterministic function of (p_noop, p_best, argmax repair).** So registered, VAL-tuned, fixed-gating and forced-repair policies are all evaluated exactly, with no further teacher calls.

**Teacher-free diagnostics:** labeled-node coefficients and label coverage (A2–A4, B1, B3), pool score distributions, and cVAE task sensitivity with intermediate-scene probes (C2, C4).

**New physical engineering studies**
- Temporary-target tasks through a separately versioned adapter (C3: 109 + 82 examples, 3 parity checks).
- A preregistered search-budget curve (E5).

**Not run, by instruction:** no retraining of FULL, no new ablation arms, no K>3 data, no counterfactual or handoff campaign, nothing in the scaling-dataset workspace.

## Headline results (pp; VAL 2D / VAL 3D / TEST 2D / TEST 3D; 95% layout-cluster CI in the detail reports)

| Question | Result |
|---|---|
| **F5 coupling: physical task success** | E − D, registered: +1.4 / −4.2 / −2.4 / +2.8. VAL-tuned: +1.5 / −0.9 / −2.4 / +5.1. Frozen knockout: −1.5 / −1.1 / −0.9 / −0.1. **No robust effect.** |
| F5: conditional X prediction | No difference for X\|Y=0. X\|Y=1 is better in D only in 3D TEST (0.02 nats). |
| F5: used by the model? | Yes. Mean \|P(X\|Y=1) − P(X\|Y=0)\| ≈ 0.10 (labeled) and 0.19 (pools). Knockout costs 0.02–0.04 in labeled Z AUROC. |
| **Factorized vs DIRECT** | Registered: −10.9 / −12.4 / −13.3 / −10.8. **VAL-tuned: −12.2 / −12.3 / −14.2 / −9.7. Forced, threshold-free: −11.6 / −12.7 / −14.2 / −11.5.** ABSTAIN gap: registered −48 to −55, tuned −17 to −35. |
| **Both X and Y needed for selection** (frozen D, forced) | Y-only: −16 / −30 / −16 / −36 (fails by X). X-marginal: −41 / −65 / −37 / −67, and X\|Y=1: −47 / −68 / −41 / −69 (both fail by Y). |
| **Task conditioning** | Changes the distribution (goal-swap JS 0.03 / 0.15). Recall cost of a wrong goal: 5 / 17 pp. Task − NoTask recall: +2.2 / +1.9 (n.s.). Physical NoTask: n.s. |
| **Temporary targets (C3b)** | Proposals contain a one-step fix for 95% (2D) and 91% (3D) of blocked temporary tasks, *with or without* retargeted context. Frozen D picks a working fix 67% / 64% of the time (random 27% / 15%). Frozen Y_τ: AUROC 0.69 / 0.82, miscalibrated. |
| **Intermediate scenes (C4)** | cVAE recall: 2D +5.3, 3D −10.4 pp vs S0. |
| **Teacher K>6** | 2D X and Y are INELIGIBLE for more than 6 relocations; 3D X is UNRESOLVED. The 2D shared budget of 8 online moves censors relocation 9+. Both are interface/budget limits, not physics. |

## Experiment D: do we need both X and Y in selection?

Frozen D, identical pools. Forced = the variant's argmax repair on every K1–K3 root. Fixed gating = FULL's NOOP/ABSTAIN/REPAIR type with the repair replaced. Seed means.

| Selector | Task success, VAL 2D / VAL 3D / TEST 2D / TEST 3D (forced) | Dominant failure | Same-endpoint order accuracy (labeled, s0) | Labeled Z AUROC (s0) |
|---|---|---|---|---|
| p11 = σ(b)σ(a+w) | 57.8 / 83.8 / 53.8 / 84.1 | mixed | 0.80 / 0.80 / 0.76 / 0.90 | 0.82 / 0.90 / 0.78 / 0.91 |
| Y-only σ(b) | 41.6 / 53.3 / 38.2 / 48.5 | FAIL_X (148/236, 99/102, 149/257, 121/127) | 0.50 (ties by construction) | 0.65 / 0.76 / 0.68 / 0.76 |
| X marginal | 16.6 / 18.8 / 16.9 / 17.0 | FAIL_Y (349/350, 181/181, 345/347, 201/201) | 0.80 / 0.80 / 0.75 / 0.90 | 0.72 / 0.66 / 0.66 / 0.69 |
| X \| Y=1 | 10.8 / 16.2 / 12.9 / 14.8 | FAIL_Y | = p11 within an endpoint | 0.71 / 0.60 / 0.66 / 0.65 |

**Reading**
- **Y alone** picks the right *endpoint* but the wrong *order*.
- **X alone** picks easy relocations that do not free the target.
- **The product is necessary** for repair selection, independently of whether F5 helps. Within one endpoint, the order ranking comes entirely from X; across endpoints, Y dominates.

## Experiment E: the remaining ablation claims (audit)

**E1 G.**
- Exactly permutation-invariant: the within-endpoint range of a and b is 0, and the order accuracy is 0.500 by ties.
- Pools are identical. All 12 seed cells are negative, and the loss is concentrated in K3.
- This is *general* order dependence, not a handoff-specific effect.

**E2 Uniform4.** 0 legality, duplicate or count violations. It has the same per-object counts and object sets as FULL. Its higher candidate count comes from lower destination overlap across objects (26% vs 68% in 2D). Its proposal recall is 0.08 vs 0.50. The gain is proposal quality.

**E3 TaskFM.**
- **Model:** TaskEncoder + rectified-flow field (3-layer MLP, time embedding), 32 Euler steps, histogram over the nearest legal cell, top-4.
- **Matching:** same examples, weights, batch, optimizer and steps. 297k vs 328k parameters. **32× more network evaluations** than the cVAE.
- **Effect:** −7 to −8 pp in all four cells; the 3D cells lose significance after Bonferroni.
- **Scope of the claim:** only this FM implementation.

**E4 M1.** Exactly FULL's top-1 prefix, with the same scorer and legality. The loss is attributable to fewer destinations.

**E5 C1 and the search budget.**
- C1 is exactly the registered one-random-candidate control. It abstains on 58–61% of roots, so it is a weak control.
- The budget curve below measures how much search is actually needed.

Budget curve (VAL, frozen D s0, registered rule; argmax over the B label-blind sha-random candidates of the identical M4 pool; `rules/BUDGET_val_{dom}.json`; 0 UNKNOWN):

| B (candidates scored) | 1 | 16 | 256 | 4,096 | all (2D mean 51k / 3D 3.7k) |
|---|---|---|---|---|---|
| 2D task success | 9.7 (−47.5 [−52.5, −42.4]) | 28.1 (−29.1) | 38.7 (−18.4) | 50.1 (−7.0 [−10.4, −3.6]) | 57.1 |
| 3D task success | 20.0 (−58.2) | 55.5 (−22.7) | **76.8 (−1.4 [−4.5, +2.3])** | 78.2 (0.0) | 78.2 |

**Search is needed, but how much depends on the domain.**
- **3D:** about 256 scored candidates recover the full-pool success.
- **2D:** success still rises beyond 4,096 candidates (−7 pp), consistent with its about 14× larger pools and the larger M1 loss.
- **C1's −45 to −67 pp** reflects B = 1 plus abstention, not the cost of moderate budgets.

**E6 DREFIT.** +0.4 / −1.7 / −0.7 / +2.1, with the same best epochs. This shows reproducibility in this environment, not universal environment independence.

**Multiplicity.** With Bonferroni over the 36 registered cells:
- **Still exclude 0:** G (3/4 cells), DIRECT (4/4), Uniform4 (4/4), C1 (4/4), M1 (3/4) and TaskFM (2/4: 2D only).
- **Barely excludes 0:** E only in 3D VAL, contradicted by 3D TEST.

## Experiment F: the K>6 teacher limit

See `K_GT6_TEACHER_AUDIT.md`.
- The traced call paths show **both an interface restriction** (`bd_core.check_sequence`: ≤ 6 relocations, applied to X *and* Y in 2D and to X in 3D) **and a budget restriction** (2D X: one shared `online_moves = 8` per query, with every relocation consuming exactly one, verified on 11,244 cached queries).
- The planner RNG keys hash `str(budget)`, so naively raising the budget would break K≤6 reproducibility.
- A minimal versioned extension, with K≤6 dispatch to the frozen code, per-relocation move accounting without changing the budget dict, and exact-parity gates, is specified but **not implemented**.

## Final scientific recommendation

1. **Is F5 worth retaining?** As an optional modeling choice: yes, at zero cost, because it gives the correct joint factorization. As a contribution: no. It does not improve task success, and improves conditional X prediction in at most one of four cells. **Present E and D as equivalent for planning.**
2. **Does explicit coupling contribute to physical success?** No. Sign-inconsistent across splits in both domains, under both the registered and the tuned rules, and the frozen knockout has no effect.
3. **Is the factorized X/Y architecture justified even with F5 neutral?** **Yes, strongly.** Both factors are necessary for selection (−16 to −69 pp when either is removed), and the factorization beats direct Z classification by 10–14 pp regardless of thresholds. The mechanism: the endpoint factor uses endpoint-only Y labels and prevents winner's-curse scores on infeasible endpoints.
4. **Does the DIRECT comparison survive fair threshold tuning?** For task success, yes, fully (−9.7 to −14.2 pp; the threshold-free result is the same). For NONE abstention, partly: the gap shrinks from about 50 pp to 17–35 pp.
5. **Is task conditioning doing meaningful work?** It shapes the proposals and is clearly harmful when wrong. Against *no* conditioning, the measured benefit at K≤3 is small and not significant. It is not the source of the method's physical advantage; placement *learning* is (Uniform4, M1, TaskFM).
6. **Does task reassignment support recursive K>3 planning?** **Partially.**
   - The frozen D ranks reassigned (temporary-target) candidates usefully, and the frozen cVAE's proposals contain fixes.
   - But the frozen Y is miscalibrated on reassigned tasks, retargeted conditioning adds nothing, 3D cVAE recall falls in intermediate scenes, and the teacher cannot verify more than 6 relocations.
   - **The recursive extension (Fig. 3) should be presented as a proposed extension with these preliminary diagnostics, not as a validated capability.**
7. **Claims strong enough for RSS:** order sensitivity (G); the factorized X/Y over direct Z (including tuned and threshold-free results); X and Y both needed in selection; learned placement over random placement (Uniform4); destination diversity (M1, 2D); environment reproducibility (DREFIT).
8. **Claims requiring qualification:** TaskFM (this implementation only; 3D not significant after correction); C1 / search (use the budget curve); DIRECT abstention (report tuned rules); "failure" means budget-limited non-verification; TEST is exposed; the bootstrap is per root.
9. **Minimum remaining work before submission**
   - (a) **Decide whether to spend the V3.4 cohort** as a sealed confirmatory set for {FULL, E, DIRECT with VAL-tuned rules}. That is about 2 × 1,114 roots of argmax verification, all inference already cheap. Owner approval is needed.
   - (b) **If the paper makes any K>3 claim:** implement and parity-gate the versioned teacher extension, and recalibrate or train Y on reassigned and intermediate tasks.
   - (c) **Revise the ablation table text** per `ABLATION_CLAIMS_AUDIT.md`: drop the coupling claim, add the tuned and threshold-free DIRECT rows, add the X-only / Y-only rows, and add the budget curve.
   - Nothing else is required for the K≤3 claims.
