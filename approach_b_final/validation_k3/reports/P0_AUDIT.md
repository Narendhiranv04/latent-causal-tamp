# P0 — Source and result audit of the completed K≤3 ablation

| | |
|---|---|
| Branch | `naren/k3-postablation-validation` (from `4aee798929`) |
| Host | gvlab2; new work root `/home/projects/long-horizon/naren_workspace/k3val` |
| Policy | The ablation root `k3abl` is read-only. Nothing frozen is modified. The teacher cache is a copy (sha-identical at copy time). Every process runs under `taskset 4-42`; CPUs 0–3 and 43–47 are left free. |
| Machine-readable output | `runs/out/p0/P0_AUDIT.json`, `runs/out/nodes/audit_{2d,3d}.json` |

## Gate verdict: PASS, with five qualifications

**Checks that pass:**
- **Seals:** 128/128 sealed prediction files match their seal sha256.
- **Pins:** all 8 frozen bundle files (sampler + D s0/s1/s2, 2D and 3D) match `final_protocol.yaml`.
- **Code:** the hashes of `xy.py`, `placement.py`, `exhaustive.py`, `search.py` and `benchmark.py` on gvlab2 equal the worktree.
- **Pooled table:** independently re-derived from the sealed `results_*` files. All 36 (arm × split × domain) cells of `pooled_paired_task.json` are reproduced exactly (point estimate and CI).
- **Candidate pools:** E, G, DIRECT and DREFIT use pools identical to FULL on every root (pool hash). M1 differs by design (M=1), and C1 draws from the FULL pool.
- **Decision reproduction:** the new multi-scorer pass (`multipass.py`) re-derives every sealed decision from raw scores, with 0 mismatches for FULL/E/DIRECT s0–s2. This is shown for 3D VAL/TEST; 2D is checked in P1.

## What each arm actually changes (from the code)

| Arm | Change | Isolation verdict |
|---|---|---|
| **E** | `xy.py` `XYNet.coeffs`: D uses a = order_s(g, v_r) and w = xy([g, v_s, c]). E uses a = order_s(g, v_r) + xs([g, v_s, c]) and w = 0. The `xs` and `xy` heads have the identical shape, `mlp2(3W, 1)`. | **The p11 hypothesis class is identical:** σ(b)·σ(order_s + MLP(h)) for both. Only the training target of the context head differs: in D it is supervised only by X labels whose endpoint has Y=1. E is therefore a test of *Y-conditional X supervision*, not of capacity (see A1). |
| **G** | Canonically sorted actions, S0 tokens, pair mixing over u≠t. Coupled. Same Y head. | Permutation-invariant by construction. Same-endpoint order ranking is exactly 0.5 because every pair ties. |
| **DIRECT** | A single success logit, a = order_s + xs, plus a no-op logit b(y0). Trained with BCE on success events (z=0 if X=0 or Y=0). | **Also an information change, not just an output change.** Endpoint-only Y labels (edited endpoints with Y observed and no X child: 2D TRAIN 4,232; 3D 1,244) never reach DIRECT. Its objective (per-root BCE sum) is not comparable to the X/Y NLL. |
| **DREFIT** | The frozen D procedure re-run on gvlab2. | Environment control. |
| **NoTask** | The cVAE task branch input is zeroed. Same scratch init, examples, weights and steps. | The cVAE scene encoder sees only radius, is_fixed and position (`search.Root.pattr`, `placement.scene_features`). **There is no target flag and no goal**, so NoTask has no explicit or implicit target/goal input. The only leak is that the goal cell is masked out of the legal destinations (`Root.legal_dests`). |

## Qualifications for every downstream interpretation

**1. "Physical failure" means not verified under the frozen teacher budget, not impossibility.**

Breakdown of selected-repair failures, from the cache statuses:

| Example | FAIL_Y | FAIL_X |
|---|---|---|
| FULL_s0, 2D VAL | 72 UNKNOWN_PLANNER + 39 CERTIFIED_INFEASIBLE | 31 UNKNOWN_PLANNER + 25 CERTIFIED + 2 UNKNOWN_TRANSIT |

- In 3D, X failures include EXECUTION_NOT_VERIFIED and CONNECTOR_NO_PLAN.
- The "0 UNKNOWN" in `FINAL_REPORT.md` refers to *missing labels*. Budget-limited zeros are counted as failures by the frozen contract.
- Claims should read: **teacher-verified success under the frozen per-query budget**.

**2. The "lineage-clustered" bootstrap is in fact per root.**
- Every root has its own `layout_root_id` (VAL 2D: 751 roots / 751 ids, and likewise for the other splits).
- Re-clustering by template (`parent_family_id`; 2D VAL 584 families, at most 4 roots each; 3D VAL 185 families, at most 10) changes the CIs by ≤0.8 pt, and no conclusion changes.
- **No multiplicity correction** was applied across the 36 cells.

**3. Fit budgets are capped and matched across arms.**
- Several fits ran all 60 epochs with the best epoch at 57–59 (3D D_s1, E_s1, DIRECT_s1, E_s0), so they may be slightly under-converged.
- The cap is identical for all arms.

**4. Label structure (A3).** In the finalized labels, every X label has its endpoint Y observed (0 X-with-missing-Y in TRAIN/VAL/TEST, both domains). D's likelihood therefore factorizes exactly into P(Y)·P(X|Y), and the mixture over unobserved Y is never used.

**5. Held-out status.**
- TEST is historically exposed.
- The V3.4 cohort (1,114 roots) holds sealed and verified FULL outcomes (`c72eb1ef75`) and is reserved for the deferred baseline comparisons. Only its id list is on gvlab2.
- It is **not** used here. Spending it as a confirmatory cohort for any new rule needs owner approval.

## Per-seed stability of the registered results (task success vs FULL, pp)

| Arm | VAL 2D seeds | VAL 3D seeds | TEST 2D seeds | TEST 3D seeds |
|---|---|---|---|---|
| E | +2.4 / −0.2 / +1.9 | −3.6 / −3.6 / −5.5 | −3.2 / −4.1 / 0.0 | +3.3 / −0.8 / +5.8 |
| G | −8.2 / −5.3 / −6.8 | −12.7 / −15.9 / −14.6 | −6.8 / −2.2 / −4.6 | −19.5 / −20.8 / −16.2 |
| DIRECT | −15.7 / −10.2 / −6.8 | −9.1 / −18.6 / −9.6 | −13.1 / −15.8 / −10.9 | −8.3 / −19.5 / −4.6 |
| NoTask | −0.7 / −3.2 / +1.2 | −0.9 / +1.8 / +1.4 | −1.5 / −2.7 / −0.2 | −2.5 / −1.7 / +0.8 |

- G and DIRECT are negative in all 24 seed cells.
- E changes sign within a domain across splits and, in 2D VAL and 3D TEST, across seeds.
- The G loss concentrates in K3 (3D TEST K3 −32.7 [−41.2, −24.2]); K1 is ≈0.
