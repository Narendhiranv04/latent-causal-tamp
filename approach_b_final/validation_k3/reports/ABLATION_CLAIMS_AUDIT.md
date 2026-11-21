# Ablation claims audit: what the RSS paper can say

**Scope and notation**
- This audits the claims of `ablations_k3/reports/FINAL_REPORT.md` (4aee798929) against the underlying records, plus the targeted diagnostics of this study.
- **Pooled paired differences** are given as VAL2D / VAL3D / TEST2D / TEST3D, in percentage points.
- **"Bonf."** = the Bonferroni-adjusted interval over the 36 registered cells (99.86%; `p0/MULTIPLICITY.json`). Re-clustering by template family changes intervals by ≤ 0.8 pp (P0).
- **"Failure"** throughout means *not verified under the frozen per-query teacher budget* (P0 qualification 1).

## Supported

| Claim | Evidence | Remaining uncertainty |
|---|---|---|
| **Order-sensitive scoring is needed (G).** | −6.8 / −14.4 / −4.5 / −18.8. All 12 seed cells are negative. Bonf. excludes 0 in 3/4 cells (TEST 2D: [−9.5, +0.5]). The loss is concentrated in K3 (3D TEST K3 −32.7) and is ≈0 at K1, as expected. G is exactly invariant (within-endpoint range of a and b is 0; order accuracy 0.500 by ties). The candidate pools are identical. | This is *general* order dependence: geometric, robot-state, planner and connector effects combined. It is **not** evidence of handoff-specific order effects; the order-dependency audit (8e1c1a247e) confirms geometric order dependence only. |
| **Factorized X/Y beats direct Z classification.** | Registered rule −10.9 / −12.4 / −13.3 / −10.8 (Bonf. excludes 0 in all 4). **Model-specific VAL-tuned rule −12.2 / −12.3 / −14.2 / −9.7. Threshold-free forced repair −11.6 / −12.7 / −14.2 / −11.5.** DIRECT's extra failures are Y failures. Mechanism: winner's curse over large pools plus no access to endpoint-only Y labels. | The ABSTAIN advantage is about 60% rule-dependent (see Qualify). Part of the win is an information effect of the factorization. TEST is exposed. |
| **The X/Y factorization itself is needed (both factors used in selection).** | Frozen D, threshold-free. Y-only (σ(b), label-blind tie-break): −16.2 / −30.5 / −15.6 / −35.5, failing by *X* (wrong order). X-only, marginal: −41.2 / −65.0 / −36.9 / −67.1. X-only, X\|Y=1: −47.0 / −67.6 / −40.9 / −69.3, failing by *Y* (relocations that do not free the target). Fixed-gating versions are the same within 1.5 pp. | A frozen-model diagnostic, not a retrained ablation. It shows that p11 needs both factors; it says nothing about F5. |
| **Learned placement beats random placement (Uniform4).** | −18.0 / −17.9 / −17.9 / −19.0 (Bonf. excludes 0 in all 4). Legal, distinct, and with the same per-object counts and object sets as FULL (0 violations). Ingredient recall 0.08 vs 0.50 (2D). Uniform4 even scores *more* candidates (86k vs 51k, because its destinations overlap less across objects). | This is evidence of better **proposal quality**, not of "causal understanding". |
| **Destination diversity matters (M1 vs M4), more so in 2D.** | −27.4 / −6.4 / −21.8 / −13.3. M1 proposals are exactly FULL's top-1 prefix, with the same scorer and legality. | 3D VAL is not significant after Bonferroni ([−16.4, +3.6]). |
| **The training environment does not drive the results (DREFIT).** | +0.4 / −1.7 / −0.7 / +2.1, all n.s. Same best epochs. | Reproducibility *in this environment*, not universal environment independence. |

## Qualify

| Claim as written | Required qualification | Evidence |
|---|---|---|
| "cVAE beats a matched task-conditioned FM" (TaskFM −8.4 / −7.6 / −8.0 / −7.3) | Say "*this* task-conditioned rectified-flow model (TaskEncoder + 3-layer FM field, 32 Euler steps, nearest-legal-cell quantization)". Do not generalize to flow matching. The 3D cells lose significance after Bonferroni. TaskFM used **32× more** network evaluations (and 4.5× the proposal latency in 2D VAL, 37 vs 8 ms) with similar parameters (297k vs 328k), so it is not a compute disadvantage. | E3 audit; Bonf. 3D [−15.8, +0.5] / [−14.9, +0.6] |
| "Search over the candidate pool is essential" (C1 −45 to −67) | C1 is exactly the registered control: one random legal candidate, one scorer call, label-blind. **It abstains on 58–61% of roots**, so it shows that *a single random candidate is useless*, not how much search is needed. Use the budget curve (VALIDATION_REPORT §E5): 3D reaches full-pool success with about 256 random candidates (−1.4 [−4.5, +2.3]); 2D still loses 7 pp at 4,096. | E5 audit; `rules/BUDGET_*` |
| "Factorized beats DIRECT" for **NONE abstention** | Under the registered rule DIRECT abstains 31–39% vs 79–92%. With its own VAL-tuned thresholds it reaches 61–79%, still 17–35 pp below tuned D. Report both, not only the registered gap. | `DIRECT_FAIRNESS_REPORT` |
| "Removing the task-context branch has no detectable effect" | True for K≤3 physical success (−0.9 / +0.8 / −1.5 / −1.1, n.s.). But the conditioning *is* used: a wrong goal costs 5 pp of recall in 2D and 17 pp in 3D. Without conditioning, the scene-only prior already achieves nearly the same recall (task − NoTask +2.2 / +1.9 pp, n.s.). | `TASK_RETARGET_REPORT` |
| Any statement about "physical failure" or "infeasible" | "Not verified under the frozen per-query budget". In 2D about half of the zeros are UNKNOWN_PLANNER / UNKNOWN_TRANSIT. | P0 |
| "Lineage-clustered bootstrap" | Every root is its own lineage, so this is effectively a root-level bootstrap. A template-family re-clustering leaves every conclusion unchanged. | P0 |

## Not supported (do not claim)

| Claim | Why |
|---|---|
| "X/Y coupling (F5) improves task success" (in either domain) | The sign flips between VAL and TEST in both domains, under the registered rule (+1.4 / −4.2 / −2.4 / +2.8) and under tuned rules (+1.5 / −0.9 / −2.4 / +5.1). The frozen knockout has no effect. Only 3D VAL survives Bonferroni, barely ([−8.6, −0.2]), and it is contradicted by 3D TEST. |
| "F5 gives better conditional X prediction" | It is better only for X\|Y=1 in 3D TEST (one of four cells, about 0.02 nats); there is no difference elsewhere. |
| "The explicit task branch improves physical repairs at K≤3" | NoTask is n.s. in all four cells. |
| "Exhaustive search is indispensable" | It is not established by C1. See the budget diagnostic. |
| "Order sensitivity captures handoff effects" | G removes all order information. The handoff-only effect is unconfirmed (order-dependency audit: 0 handoff-only confirmable). |
| Anything on the V3.4 independent cohort for E, G, DIRECT, F5 or tuned rules | Not evaluated. The cohort is reserved and needs owner approval. |
