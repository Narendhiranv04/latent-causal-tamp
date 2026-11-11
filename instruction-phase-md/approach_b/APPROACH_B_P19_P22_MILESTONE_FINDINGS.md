# Approach B | P19–P22 Milestone Findings

**Certified K3/K4 physical repairs, what the model learned, and the final 2D evaluation path**  
**Evidence freeze:** 1 November 2026 · Git commit `bcad58e68c09f5d7ec3cc5942f5fc7a40c9315a4`  
**Classification:** development evidence only. Independent K0–K4 confirmation has **not** been collected or evaluated.

> **Executive conclusion.** The methodology is now physically instantiated at K4: seven distinct 2D scenes have replayed four-relocation repairs, the terminal connector to `q_ref`, a separately replayed target action, and a certified necessity lower bound of four movements in the declared grasp family. Fourteen new K3 scenes are likewise certified-necessary. The strongest positive learning evidence is *ordered physical executability*, not the quadratic X/Y interaction. The full X/Y system does **not** establish an advantage over a geometry-informed direct-success predictor on the enlarged development population. The next defensible step is an audited, one-shot, independently generated K0–K4 test.


<div class="cover-panel"><div class="cover-kicker">PHYSICAL PROOF &nbsp; / &nbsp; LEARNING EVIDENCE &nbsp; / &nbsp; FINAL VALIDATION</div><div class="cover-metrics"><div class="cover-metric"><span class="cover-num">14</span><span class="cover-label">necessary K3 repairs</span></div><div class="cover-metric"><span class="cover-num">07</span><span class="cover-label">necessary K4 repairs</span></div><div class="cover-metric"><span class="cover-num">00</span><span class="cover-label">independent test scenes</span></div></div><div class="cover-divider"></div><div class="cover-step">Ordered obstacle relocation &nbsp;&rarr;&nbsp; terminal connector to <em>q_ref</em> &nbsp;&rarr;&nbsp; target task</div><div class="cover-note">No robot reset between relocations. Seven real K4 witnesses; no established K4 generalization claim.</div></div>
</div>

## 1. At-a-glance milestone scorecard

| Evidence | P22 state | Scientific interpretation |
|:---|---:|:---|
| New P20 development roots | **86** | Three outcome-blind construction waves; 2,174 observed of 2,202 planned query labels. |
| Certified-necessary K3 repairs | **14** | A complete successful three-move witness plus necessity certificate. |
| Certified-necessary K4 repairs | **7** | Real physical K4 phenomenon; below registered 10-root inferential threshold. |
| Strict K34 same-endpoint order contrasts | **46** | Same action multiset, altered order, unequal measured physical executability; not 46 independent K4 roots. |
| P21 training corpus | **398 roots** | P-min 197 + P15 28 + V2.1 87 + K34 86. |
| P21 outcome-blind infeasible roots | **150** | Just **63** offer a verified catalogue repair. |
| Independent confirmation | **0 scenes** | P22 froze models and a plan only; all results below are development results. |

The frozen P20 verdict `K4_PHYSICAL_DATA_NOT_ESTABLISHED` means only that **7 < 10** for the predefined inferential threshold. It **does not** negate the seven verified K4 witnesses. The remaining `K34_DATA_READY` threshold of 20 K3 and 20 K4 examples was not reached.

![Certified K coverage](figures/k_coverage.svg)

*Figure 1. Independent labelled roots by verified catalogue length in V2.1 (P16) and K34 (P20). Necessity is stricter than catalogue length: all fourteen P20 K3 and all seven P20 K4 roots are K_cert-certified; neither of the two older P16 K3 roots met the new certificate.*

## 2. The methodology that remains unchanged

**Problem.** Given a scene, target object and goal, an external proposer supplies a finite catalogue of ordered obstacle relocations to explicitly specified parking cells. The learned model scores proposed corrections; it does not invent new action sequences or synthesize continuous trajectories.

**Embodiment.** A planar finite-width **3R articulated arm**, side-grasp modes (24 directions and two elbow configurations), continuous joint motion and an **8 × 8** placement lattice. Candidate correction length `m` can be 0–6, with one target action after the corrections.

**A single physical proposal is executed as follows:**

```
S0, q0  →  move obstacle 1  →  move obstacle 2  → ... → move obstacle m
                                                     [carry achieved q forward]
            →  one terminal connector to q_ref  →  target pick-and-place from q_ref
```

There is **no home/reference reset between relocations**. The robot begins each next action in the actual achieved state of the previous action. Only after the final relocation does the physical teacher connect to the fixed reference `q_ref`. The target action is independently witnessed from `q_ref`; together with an X witness including that connector it forms a composable complete repair.

**Two outcomes answer different questions.** `X_q` asks whether this *ordered* relocation prefix and its terminal connector can be physically executed under the frozen teacher and query budget. `Y_s` asks whether the original target manipulation succeeds from `q_ref` in the *hypothetically edited endpoint scene*, even if that endpoint is physically unreachable through the proposed relocations. Same endpoint and same target -> shared Y across different orders; X can differ. No-op success is simply `Y0`.

The root-consistent model is:

```
P(Y_s=1)                 = sigmoid(b_s)
P(X_q=1 | Y_s=y)         = sigmoid(a_q + w_q*y)
P(success for prefix q) = sigmoid(b_s) * sigmoid(a_q + w_q)
P(success for no-op)     = P(Y0=1)
```

**F1–F5.** F1 analytic candidate screening; F2 predecessor-aware ordered physical-prefix scorer; F3 edited-scene target-feasibility scorer; F4 omission edits evaluated using the same F2/F3 networks; F5 optional quadratic X/Y coupling `w_q`. In the capacity-matched uncoupled E model, `w_q=0` and X retains a scene-aware head.

**Implemented additions, distinct from the 31 October base specification.** GEO2 supplies label-free analytic grasp/place access features from the scene and specified edits. SYM adds a balanced auxiliary comparing beneficial (`Y0=0 → Ys=1`), harmful (`1→0`) and neutral edits. Current D/E use:

```
L_implemented = L_joint + lambda_J * L_J + kappa * L_SYM
```

Here `L_joint` is exact observed-data likelihood over root-deduplicated Y and X, with unobserved/censored queries marginalized; `L_J` is a witnessed-success-only Huber travel objective; `lambda_J=1` and `kappa=1` in D/E. The original October 31 base objective did not contain SYM. No cost or score is a global certificate of infeasibility; operational fixed-budget failures are recorded separately from definite geometric certificates.

## 3. P19: the necessary correction to the earlier K labels

Earlier P16 difficulty used an analytic union-of-blockers model, `K_geom`, to estimate how many obstacles must be removed to open a target grasp/place mode. That abstraction sometimes counted uncertain/non-definite candidate failures as definite closures. Its estimated K could therefore overstate necessary correction length.

**Example:** P16 `wA-s028` had a physically witnessed three-move correction, but the later real-screen lower bound was only **K_cert = 1**. This means three moves worked within its finite tested catalogue, not that three were provably required. Both P16 K3 examples lost their certified-necessary K3 claim under the stronger audit; their historical labels and reports remained untouched.

P19 introduced the stronger `K_cert` check. For every possible set of `K−1` movable objects, remove that set from the scene. If the target's declared pick or placement family is **still definitely blocked**, then moving fewer than K objects cannot restore that access under the stated monotonic obstruction assumptions. Combine that certificate with a witnessed K-move successful correction and K becomes both **necessary and achievable** within this fixed 2D skill family.

This is **not universal optimality** across other grasp strategies, different tools, or a different robot. It is a sounder lower bound for this declared task protocol.

P19 also diagnosed the execution bottleneck: across more than 1,100 prior relocation attempts, each relocation succeeded around **65%** of the time under the fixed budget. A rough independence illustration gives `0.65^4 ≈ 18%` for four consecutive successes, *before* target execution; real steps are correlated, so this is only an intuition. Failures were concentrated in difficult board regions, dense neighborhoods and early relocations. This motivates more executable hard-scene construction without loosening the teacher.

## 4. P20: genuinely necessary K3/K4 scenes

P20 generated challenging scenes *from geometry before reading target/repair outcomes*. Its **doorway closure** construction keeps a narrow angular set of target manipulation modes potentially available and uses fixed discs to close other modes. It places three or four movable blockers to close the remaining doorway. The candidate corrections relocate those blockers to legal parking cells. This creates a genuine *environmental reason* for several corrective actions, rather than blocking a single nominal target trajectory.

To keep the corrected scene physically solvable, the construction screens candidate blocker picks, short-carry parking destinations, definite edge/sector failures, and the number of reopened target modes. Real populated-scene teacher queries still independently determine X and Y; geometric construction does not label a correction successful.

| P20 development wave | K3 verified necessary | K4 verified necessary | Intended long repairs fully successful |
|:---|---:|---:|---:|
| k1 / initial doorway | 3 | 0 | 3 of 15 |
| k2 / per-action certificates | 5 | 2 | 4 of 19 |
| k3 / more reliable work region | 6 | 5 | 10 of 22 |
| **Total** | **14** | **7** | — |

**Recorded evidence for each of seven K4 roots:** a complete replayed ordered relocation sequence from `q0`, the final connector to `q_ref`, a replayed target witness from `q_ref`, and target Y remaining negative after one, two and three corrections. The `K_cert=4` certificate independently rules out any fewer-than-four-object correction within the skill family. There are two K4 construction mechanisms (`local_mixed` and `local_pick`), but both rely on the related doorway framework.

**What still fails.** The harder the target access closure, the more those same blockers interfere with the arm's own blocker pick/transit. A hypothesized final edit may give `Y=1` while the ordered physical correction has `X=0`. Many negative X results are bounded-planner `NO_PLAN_FOUND`, not certified impossibilities. Among P20's 2,202 frozen queries, **2,174 were labelled** and **28 remained unattempted** on one budget-exhausted K3 root. A duplicate-supervisor incident after a session restart was logged without evidence of label corruption; **2,642 CPU-s** of duplicate/conservative charges remained in the budget.

## 5. P21: what was actually learned

The existing six P17 model families were retrained without changing their neural architectures. There were 90 jobs: five family-grouped held-out folds times three seeds times six arms. Results are *out of fold*, with fold-specific selection rules chosen on early-stop development data. They are **not** the test performance of P22's later frozen fifteen-checkpoint ensemble.

In P21's outcome-blind development population (P15 + V2.1 + K34), 201 roots include 150 initially infeasible scenes; **63/150 (42%)** contain a verified corrective candidate. That 42% is an evaluator-only *catalogue availability ceiling*, not a failure rate of every possible planner.

![Development model comparisons](figures/model_success.svg)

*Figure 2. Two different denominators: unconditional success across all 150 infeasible development scenes and conditional success on the 63 with a verified catalogue repair. Never read the 68.8% availability-conditioned number as 68.8% unconditional success.*

| Arm | Success / infeasible | Success / available | Unnecessary repairs / feasible |
|:---|---:|---:|---:|
| B: original XYQ-BASE | 0.056 | 0.132 | 0.213 |
| G: X/Y without order | 0.236 | 0.561 | 0.120 |
| A: matched DIRECT-GEO | 0.258 | 0.614 | 0.193 |
| E: uncoupled XY+GEO2+SYM | 0.287 | 0.683 | 0.160 |
| **D: coupled XY+GEO2+SYM** | **0.289** | **0.688** | **0.140** |
| Analytic geometry reference | 0.207 | — | **0.000** |
| Verify-first (oracle ceiling) | 0.420 | — | — |

**Interpretation.** The enhanced X/Y models vastly outperform the *unchanged* original XYQ baseline. However, geometry-informed DIRECT improves too. X/Y factorization with its available additional supervision does **not** establish a meaningful advantage over matched DIRECT in this larger, harder development comparison.

### 5.1 K3/K4 results (conditional on an available verified repair)

![K3 K4 repair selection](figures/k34_selection.svg)

*Figure 3. Root-level sample sizes: K3 n=14, K4 n=7. Each OOF root has three seed-model decisions. Reported 0.952 for K4 corresponds to 20/21 root×seed decisions, **not 20 independent K4 environments**. K3 is exploratory; K4 is descriptive, not a significant long-horizon generalization finding.*

On K3, D obtains 0.74 versus 0.79 for DIRECT and 0.60 for G. On K4, D obtains 0.95, DIRECT 0.86 and G 0.57. Those high conditional rates answer “can the model choose a verified candidate **when one is in the finite catalogue**?”; they do not imply that the approach can synthesize K4 repairs in arbitrary crowded scenes.

## 6. Ablation results and the actual contribution

![Paired learning contrasts](figures/paired_contrasts.svg)

*Figure 4. P21 paired root/family bootstrap comparisons. The K3/K4 D−G contrast is on a smaller repairable subset than the other three overall comparisons and should not be compared as if denominators were identical.*

**D versus unchanged XYQ-BASE:** overall corrective success gain **+0.233**, 95% paired interval **[+0.171,+0.298]**. Clear improvement from the implemented training/geometry package, not proof that a single term caused the gain.

**D versus DIRECT-GEO:** **+0.031 [−0.002,+0.064]**, not significant under the registered criterion. On the *21 repairable K3/K4 scenes*, the difference is effectively zero **[−0.127,+0.111]**. Thus P17's earlier claim of superiority over DIRECT **did not replicate** after adding K34 development data.

**D versus uncoupled E:** **+0.002 [−0.027,+0.031]** overall. The quadratic F5 term produces no established benefit; E is the preferred simpler deployment arm given the current data. This does not imply X and Y themselves are unhelpful.

**Order-aware D versus order-invariant G:** strict same-action-set permutation concordance on K34 is **0.929 versus 0.500** (across 33 independent roots; the reported 309 pair×seed evaluations are correlated). The certified-failure subset reaches 1.00 concordance in the saved measurements, but remains small. On the **21 repairable K3/K4 roots**, D's corrective success exceeds G's by **+0.222 [ +0.048, +0.413 ]**; the more conservative 99% interval includes zero. That is the strongest positive *mechanistic* learning evidence, still exploratory.

The geometry-only rule scores 0.207 success with zero unnecessary repairs. It is an informative *precision/safety* reference: some learned gains buy extra repair attempts. A verify-first oracle would score 0.420 but requires mean verification work and uses ground truth not available to a deployed predictor.

## 7. Interpretation of factors F1–F5 after this milestone

| Method component | Evidence status | Honest scientific takeaway |
|:---|:---|:---|
| F1 analytic screen | Implemented / validated | Cheap early rejection; not a motion-planning proof. |
| F2 ordered physical prefix X | Strong development signal | Correct ordering can determine whether a candidate is physically executable. |
| F3 hypothetical-scene Y | Substantially improved | Counterfactual feasibility and harmful edits can be learned in-domain using geometry and SYM. |
| F4 omissions using same scorers | Implemented; measured | Useful counterfactual comparisons, not a discovered global causal graph. |
| F5 quadratic X/Y coupling | Benefit unsupported | Keep D for scientific ablation, prefer simpler E unless independent test changes evidence. |
| Robot-travel auxiliary | Implemented; verified-witness-only | Costs full sequence+connector+target, assessed on matched successful repairs. |
| Long-horizon repair | K4 physically demonstrated | K4 learning statistically unresolved with only seven development roots. |

**Important methodological honesty.** GEO2 features are generated analytically from the same grasp-screen family that informs the scene generator. They are valid label-free deployment inputs, but they create a plausible generator-family shortcut. Even successful independent new-seed K34 scenes would not prove transfer to wholly different geometry distributions, manipulators, or 3D.

## 8. Why the “90% implemented” project assessment does not mean “90% scientifically proved”

Nearly all agreed *2D mechanisms* are implemented: no-reset sequential robot state, X with connector, Y with shared edited scenes, F1–F5, exact likelihood, GEO2/SYM extensions, cost-aware selection, physical teacher, K3/K4 generation and evaluation.

But claims require different evidence:

- **Proved as a bounded physical phenomenon:** seven certified-necessary K4 repairs and fourteen certified-necessary K3 repairs under the declared planar 3R skill family.
- **Strong development evidence:** action-order representations improve strict-order ranking and multi-move repair selection versus the order-invariant arm.
- **Not shown:** a statistically meaningful advantage of the full X/Y learning/selection system over matched DIRECT; a useful quadratic coupling term; reliable K4 selection on independent test roots; transfer beyond the generator family.

A physically valid K4 dataset and a good K4 learning demonstration are **not the same accomplishment**. The model's conditional K4 95% observed on n=7 should not be used as the paper's generalization headline.

## 9. The next bounded implementation: P23 → P24 → P25

**P23 — Make the independent test safe and scientifically decisive (no new teacher data).** Reproduce P21; hash-verify and store the frozen checkpoints off the original physical disk; explicitly freeze missing order-invariant **G** as a matched 15-member ensemble; reconcile the conditional/unconditional primary endpoints and multiplicity; make the collector single-owner across process namespaces to prevent the P20 duplicate incident; test crash/restart and incomplete-query recovery using synthetic data. Leave all P22 manifest files untouched and append a prospective, versioned lock.

**P24 — One-shot K0–K4 independent confirmation, only after separate approval.** Execute the locked **440 construction slots**, never replacing a rejected or difficult slot and never adapting to labels or model performance. Expected K3 ~50 and K4 ~41 come from small development rates and may be missed. Freeze the candidate catalogue before teacher calls, obtain witness-backed X/Y outcomes and test the exact frozen D/E/A/G ensembles **once**, with the preregistered paired root-level statistics, guardrails and K strata. Proposed budget ceiling 90,000 aggregate CPU-s (P22 estimate ~70,000) must be explicitly authorized. No interim results, retuning or replacement waves.

**P25 — Final evidence and manuscript-facing method.** Report what the independent test actually supports: whole-system D/E versus DIRECT; F5 D/E; F2 D/G; K0 unnecessary repairs; K1–K4 and certified-only sample sizes; omission contrasts; matched-success travel; availability and budget-failure breakdown. Update the implemented-method report and produce figures based only on actual replayed witnesses. Do not retrofit a new hypothesis onto a disappointing result.

### What we should not do next

Do not invent new neural terms, broaden the teacher grasp family, increase planning budgets to make tests easier, move to 3D before the current 2D evaluation, or claim cross-generator transfer from a second draw of the same K34 doorway generator.

## 10. Source ledger and provenance

All numerical findings above are sourced from the following pushed repository files at commit `bcad58e68c09f5d7ec3cc5942f5fc7a40c9315a4`:

- `responses-phases/0126_BXY_P19_K34_PREFLIGHT.md` — strict necessity audit, order control diagnostic, reported P19 bottlenecks.
- `responses-phases/0127_BXY_P20_K34_DEV_COLLECTION.md` — three construction waves, seven K4 witnesses, label accounting, incident.
- `responses-phases/0128_BXY_P21_K34_LEARNING.md` and `runs/approach_b/bxy_p21_v1/EVALUATION_P21.json` — all models, roots, OOF estimates, paired contrasts.
- `responses-phases/0129_BXY_P22_FINAL_2D_METHOD_AND_K34_READINESS.md` — frozen 2D state, K0–K4 evidence, planned cohort.
- `responses-phases/0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md` — original method versus implemented GEO2/SYM extension.
- `runs/approach_b/bxy_p22_v1/FROZEN_MODELS_P22.json`, `CONFIRM_PLAN_K04.json`, `CONFIRM_ANALYSIS_P22.json` — frozen prospective plan and custody.
- `bxy_p19_audit.py`, `bxy_p20_k34.py`, `bxy_p21_k34.py`, `bxy_p21_eval.py`, `bxy_p22_freeze.py` — implementation checks.
- `visualizations/approach_b/bxy_p20_v1/00_verified_k4_2-s013.png` and `00_verified_k4_2-s017.png` — actual 2D replay story figures (not reproduced here).

**Independent validation has not yet run.** This report is a source-grounded milestone synthesis; it is not a substitute for the future registered confirmation.
