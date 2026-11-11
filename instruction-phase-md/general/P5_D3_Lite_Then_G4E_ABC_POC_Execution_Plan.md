---
title: "P5: Small D3-Lite Dataset Extension, Then G4E-ABC Proof of Concept"
subtitle: "Proposed bounded implementation and collection plan | learning-first"
author: "Latent Causal Infeasibility for Long-Horizon TAMP"
date: "21 October 2026"
lang: en-US
fontsize: 10pt
geometry: margin=0.78in
colorlinks: true
linkcolor: NavyBlue
toc: true
toc-depth: 2
numbersections: true
---

> **PROPOSAL; not yet an execution authorization.** This is an implementation-ready planning contract using Methodology v1.7 + Implementation Guide v1.9, amended by report 0019's `2D-ABC-OPNEG-v1` policy. Last reported pushed revision: `0bd8fdd`. Do not assume source files, branch state or hashes without checking the actual repository. No part of P5 has run merely because this document was created.

# Exact purpose and decision

**Do not launch the old 40-root D3 or 194-unit POC_F yet.** Instead, implement the minimal corrected explanation layout and validated sampler, collect up to **8 fresh independent root lineages** in two batches **4 + 4**, and then run **tiny-data proof-of-concept training** on all three specified actual architectures A/B/C. Use development records already collected in P4. Keep data collection and model validation transparent enough that it can be scaled without rewriting experimental semantics.

The deliverable is **functional learning code and a clear evidence-coverage report**, not a generalization/publication claim. This is a study of causal energy-model factorization, not more certificate design.

## Decisions fixed for this plan

- Use the existing P4 versioned offline teacher policy **`2D-ABC-OPNEG-v1`** unchanged. Three pinned seed namespaces per teacher query; early-exit on complete witness or accepted certificate; `BUDGET_INFEASIBLE` only after *all* required clean per-seed terminals. Timeout/guard kill remains `UNKNOWN`.
- All three learned architectures are **exactly** those in Methodology v1.7 and Guide v1.9. Do not replace B/C's joint energy with an independent classifier, and do not infer hidden causal arrows from factor magnitudes.
- Correct the exact B/C omission layout using a **new versioned derived learner view**. A 2-move repair has two actual leave-one-out omission variables, not a duplicate third 'omit nothing' variable. Investigate and address semantic aliases without altering frozen teacher files.
- Same learner-visible data, root-split policy, candidates, teacher evidence and deployment verifier for A/B/C. Teacher output/status, precomputed collision or swept path, root IDs and privileged future trajectory never appear as neural inputs.
- New roots/variants and test splits are independent of all historical P4/G4C development lineages. The frozen P4 roots can be debug/training examples, not independent test results.
- Real full 3R articulated robot and recorded 48-grasp skill unchanged. Only legal rest cells discrete; actual relocation motion continuous. Goal success includes SAFE_RETREAT.

# Sequence of work and hard prerequisite gates

## Stage P5.0 — preflight, layout, sampler and final P4 change

**Tasks**

1. Verify repo branch/status, `origin/main`, the P4 commit, historical manifest/hash sets, and all previous test/replay evidence. Leave the two pre-existing tracked root-PDF deletions and all user-owned/untracked instruction files untouched; stage only explicit authorized paths.
2. Read v1.7/v1.9, P4 report 0019 and current `g4c.py`, `operational_teacher.py`, sampler, candidate/omission builder and execution code. Record source line evidence before deciding the smallest safe implementation change.
3. Create a **versioned** `z_layout_v2` builder/view (name is suggested, not a mandated filename) that deterministically defines `z0`, eligible predeclared scene slots, `z_r` and only real omission slots `t < m`; no no-op omission. Inactive slots deterministic, masked from energy **and** state enumeration. Preserve stored P4 eight-slot evidence and create a verified seven-distinct-slot view. If two outcome variables address an identical physical query, enforce/document a canonical identity or equality constraint so inconsistent aliases are not counted as independent hypotheses.
4. Test exact \(\log\sum_z e^{-E(r,z)/T}\), inactive-slot invariance, no energy or probability change when adding inactive placeholders, normalization, gradients and signature/hash/version mismatch refusal. Small bounded PoC allows **exact** z enumeration (\(\le 8\) active independent binary fields).
5. Re-run **G4B** sampler validation with the corrected layout. Validate sequence-space destination Gibbs, order swap, action birth/death, unequal destination counts, proposal ratios, row sums, detailed balance and finite-difference gradients. No planner calls.
6. Recheck P4's final `loss_masks` change (made after its full regression). At minimum run direct affected tests and needed regressions. Any new changes that affect policy/teacher outputs trigger a fresh guarded full regression before data release. Do not claim a post-change full pass if only the earlier P4 run passed.

**Gate P5.0 PASS:** independent layout and mathematical/sampler checks pass, old source evidence byte-identical, `loss_masks` tested, no new planner calls from math checks. **Otherwise stop before collection.**

**Proposed isolated CPU limit:** G4B checks \(\le120\) CPU-s; any separately authorized full regression \(\le650\) aggregate CPU-s, process-tree guarded. Source changes kept near ~120–280 logical lines per module; >300 triggers explicit review.

## Stage P5.1 — D3-lite frozen root plan (before any outcomes)

**Fresh independent lineages:** \(R=8\). Freeze 8 predeclared random seeds and a deterministic root-level split **before generating children, queries or results**:

- 4 fresh **development/train** lineages;
- 2 **validation** lineages;
- 2 **diagnostic sealed holdout** lineages.

The legacy two P4 roots (AB, r19) remain **development only**. Eight roots, especially a two-root holdout, are insufficient for claims about generalization, confidence intervals or model superiority. The holdout is a no-peek smoke check.

**Geometry:** test verified candidate base layouts at \(q_0\) under the unchanged J0 rule and avoid defaulting to the very close-to-base (\(\rho<0.42\) m) `g4d_R1` geometry that produced expensive RRT tails. A candidate planning preference for target \(\rho \ge0.45\) m is reasonable; **record the selection bias** rather than calling it a random sample of all 2D workspace scenes. Do not discard a base after seeing an unfavorable target outcome without logging it. The generator should include planned access blocking, dual-blocker/interaction, alternative destination, and nuisance controls, with scene families balanced by predeclared deterministic assignments.

**Maximum 12 unique teacher queries per lineage, including baseline validation** (maximum 96 new queries total):

1. One baseline original-task witness query from the clean J0 reference base (diagnostic for construction; if not feasible, record/stop that lineage rather than treating its children as guaranteed recoverable).
2. One no-repair target query from the **constructed obstructed** initial scene (this is the root that supplies the repair dataset).
3. Two distinct single-object relocation candidates (also used as both genuine omissions of a two-move repair when appropriate).
4. Two exact same-endpoint two-object sequences, one in each order.
5. Two eligible fixed-robot singleton scene edits and one compatible joint edit, all predeclared; evaluate target-only at the original fixed robot state.
6. One nuisance or potentially harmful fixed-robot scene edit (record eligibility and no-change/harmful result).
7. Up to two candidate repair destination alternatives, predeclared for contrast/cost.

This is **1 + 1 + 2 + 2 + 3 + 1 + 2 = 12** unique queries. The baseline query belongs to its reference scene, while all repair and effect queries belong to the constructed obstructed scene; **never pool their outcomes into one B/C z vector**. If a scene has fewer eligible edits, reserve its missing slots as inactive/NA, not fake negatives, and do not invent replacement queries after seeing outcomes. Genuine omission queries that aren't among the two singleton repairs must consume a predeclared slot from the 12; reduce alternatives accordingly. For a length-2 repair the omitted-one sequences are normally the two singletons; a remove-none slot never counts as a query.

**Important B/C distinction:** a **complete B/C pool** means *every active field of the actual repair's layout is decided*, **not** that every attempted query in the entire lineage is decided. More than one fully decided repair **within the same root** is especially valuable: a joint loss over one positive repair and its z assignments is a useful smoke test, but does not test repair discrimination as strongly as a positive/negative repair pair in one fully decided candidate catalogue.

Predeclare all queries/candidate IDs, intervention scopes, robot-start states, appearance anchors, omission transforms and policy hashes before querying the teacher. Treat reference J0 diagnostic as a different scene from the obstructed root.

## Stage P5.2 — collect batch 1 (4 fresh roots) and decide continuation

Run one worker, versioned policy with three specified seeds, process-tree guard, early witness/certificate short-circuit, and complete evidence per query. Report witnesses, actual first-witness J, static checks, seed terminal types, outcomes, policy-specific negative evidence and UNKNOWN causes. Root-level release/masking and counterfactual consistency checks are mandatory.

**Predeclared stop rules**

- FATAL witness/certificate contradiction, hash/provenance mismatch or guard-enforcement failure: **immediate stop**.
- If more than **25%** of planned queries are UNKNOWN at the end of four roots: halt extension, write an explicit data-quality report and proceed to engineering PoC with the available decided examples, not to more blind collection.
- If zero multi-repair complete z pools or zero candidate order contrasts were collected: stop automatic expansion, review whether the fixed catalogue actually elicits those contrasts; the model PoC can still proceed as an implementation test.
- Do not substitute a scene or query after seeing a bad outcome to manufacture an apparent pass. Predeclared replacement/abstention rules must be part of the frozen plan.

## Stage P5.3 — only if gate permits, collect batch 2 (up to four more roots)

Continue within the **same** frozen eight-lineage plan, teacher version and aggregate envelope. Respect the previously frozen train/validation/holdout split. Hide the sealed holdout results from model development until checkpoints and hyperparameters are frozen.

## Stage P5.4 — create one common learner-view dataset

Export model-ready records from raw evidence with explicit version/hash and **strict allowlisted features**:

- initial RGB-D/masks or a documented cached **initial-only** frozen feature representation; known poses/shapes/support and legal destinations; actual initial robot/task state;
- canonical physical sequences and predeclared eligible explanation-catalogue records;
- separate privileged teacher namespace with label kind (`WITNESS`, `CERTIFICATE`, `PLANNER_BUDGET`, `UNRESOLVED`), policy hash, true outcomes, static labels, first-witness costs, decided masks and effect-eligibility masks;
- deduplicated typed B/C z layout for each repair and a collection-wide mapping from every z-field to its independently evaluated teacher query;
- source/root lineage and split metadata **stored for auditing, never exposed as model features**.

No leakage of RRT state/seed, teacher trajectory, goal-check result, collision oracle distance, privileged future image, old nominal sweep or root ID to the feature tensors. If DINOv2 frozen features cannot be obtained reproducibly in the current environment, identify that as a *visual-feature blocker*. A geometry-only tensor or synthetic fixture may still test model wiring, but must be clearly labelled a partial PoC, **not** the completed required multimodal model.

**Operational negatives:** trainable binary 0 under the P4 protocol; preserve source and measure certified-only vs combined loss/method sensitivity. UNKNOWN is never silently converted to 0. Fully supervised B/C joint term requires **every active z field** decided under the matching policy.

# Hard collection resource envelope (proposed)

| Item | Maximum / interpretation |
|:--|:--|
| Fresh reference lineages | 8 total: 4 + 4 checkpoint |
| Teacher queries | 12/lineage including clean-base control; \(\le96\) total |
| Seed attempts | 3/query; \(\le288\) declared; actual may be smaller due to short-circuit |
| Per-seed guard | 250 CPU-s, 600 s wall (unchanged P4 policy) |
| Per-query guard | 900 CPU-s hard; cancellation at 870; 1,800 s wall (unchanged policy) |
| Aggregate collection CPU | **4,800 CPU-s**, includes coordinator/worker processes; hard stop |
| Aggregate wall | **7,200 seconds** (2 h); hard stop |
| Workers | 1 |
| Static admission compute | \(\le300\) CPU-s, separately measured; must not silently exceed total authorized compute |
| Collection split | batch 1 \(\le2,400\) CPU-s, batch 2 uses remaining \(\le2,400\), total 4,800 |
| New planner/call claims | record actual child-worker connector-level calls if instrumented; do not report 0 merely because coordinator made 0 |
| Saved outputs | frozen plan, raw ledger, seed records, witness/trace, statuses, masks, pool map, CPU accounting, plots, integrity manifest |

No query may be labelled budget-negative unless it met **the exact clean completion rule** from `2D-ABC-OPNEG-v1`. A process-tree cancellation cannot be reinterpreted as a clean terminal. Large, expensive search-limited scenes may remain UNKNOWN and count against the coverage report; do not continue silently with a higher per-seed budget.

The 4,800 CPU-s envelope is a proposed **hard ceiling**, not a claim that 96 queries can always finish inside it. P4's 77.6/12 CPU cost is selected-root calibration and cannot predict fresh-root tails reliably.

# What to measure in the D3-lite report

Report per root and overall:

- attempted original/base/ordered/scene query counts with planned denominators;
- `VERIFIED_FEASIBLE` / `CERTIFIED_INFEASIBLE` / `BUDGET_INFEASIBLE` / `UNKNOWN` counts and provenance;
- independently checked original negative + complete ordered repair witness pairs;
- count of fully decided single repair outcomes, **fully decided multi-repair B/C joint pools**, and distinct z-fields (after alias/no-op correction);
- same-endpoint swap pairs with both sides decided, and whether negative is access/occupancy/budget-only;
- fixed-robot scene effects, omission effects, jointly decided \(\kappa\), nonzero versus zero and proof versus operational;
- eligible nuisance/negative-effect controls; first-witness J and analytic displacement C_d;
- CPU/wall per root, per query and seed terminal, full process-tree calls, caps and censored attempts;
- train/validation/holdout distributions frozen before training; no selected-root quality claims.

**Coverage desiderata, NOT automatic relabelling or pass guarantees:** at least four fully decided B/C pools from at least three independent roots **including any valid P4 training pool**, two decided same-endpoint order pairs and two measured nonzero interactions across eligible effects, plus \(\ge6\) relocation cost labels. Report shortfall exactly.

# G4E-ABC proof-of-concept training immediately after batch results

**This is actual model implementation.** Synthetic fixtures are allowed as mathematical tests but cannot replace the real documented 3R observations/labels.

## Implement shared feature/preprocessing once

Frozen DINOv2 mask-pooled initial appearance + trainable width-128 projection, supplied numeric object and robot descriptors; reusable local unary and symmetric pair factors with logistic/nonnegative-energy outputs; one canonical physical sequence/ideal-prefix generator; exact and masked teacher tensors. No three parallel duplicated data pipelines. Avoid refactoring working G0–G4 robot code.

## Model A: real GRU sequence EBM

GRU 128 over ordered action/prefix tokens; nonnegative unary/pair endpoint energies; predicted task logit and predicted nonnegative first-witness J. Train static BCE, ordered task BCE, effect MSE, masked cost log-Huber and decided-pool **feasibility-energy** ranking. Explanations obtained by rescoring eligible fixed-robot scene edits and regenerated omission sequences. Boltzmann sampling energy adds analytic C_d and predicted J.

**Minimal behavior:** Fit the historical r19 access-sensitive swapped order and several new order contrasts if decided. Neither endpoint-only local factors nor a model receiving shuffled actions may get credit for 'learning order.'

## Model B: true joint energy over \((r,z)\)

Use *same* object tokens/local factors and **prefix pair/adjacent order interactions without GRU**. Implement neural scene, omission and coupling potentials with explicit binary z assignments. Compute exact \(E_B(r,z)\), exact \(\bar E_B(r)=-T\log\sum_z e^{-E_B(r,z)/T}\), derived \(p_B(z_r=1\mid r)\), effect marginals and separate nonrecurrent joint-travel head.

Train joint fully-decided pool log probability over **all valid r,z states** plus decided marginal task/outcome BCE, effect MSE, static BCE and first-witness cost Huber. Skip incomplete pool terms visibly. Include `B-no-coupling` trained on the same records. Check exact partition, z-layout/alias invariance and finite-difference energy gradients.

## Model C: B joint outcomes + A GRU

Keep B's actual typed z, scene, omission and coupling potentials. Replace B's basic prefix pair-order term with a GRU 128 order-dependent factor linked to candidate z_r. Train with B/C full joint loss + supervised marginal/outcome/effect/static/cost losses. GRU-derived J head. Run `C-no-coupling` and A parameter-matched variant where feasible.

## Common training and evaluation contract

- Initially AdamW lr \(10^{-3}\), weight decay \(10^{-4}\), width 128 and frozen vision backbone; all loss weights start at 1, with label counts and gradients reported.
- Build first mathematical microfixtures (2–3 objects, exact tiny catalogue, seven distinct active outcomes for two-move canonical pool); then overfit genuine development data with all three.
- Validate `UNKNOWN` masks produce zero corresponding gradients, task/effect and cost losses have correct signs, learned static pair energies are symmetric, action-order dependence is possible, B/C coupling gradients exist, partition logZ matches brute-force.
- Hold all validation and holdout roots separate; tiny holdout is a smoke check only. No test-set hyperparameter choice.
- For B/C, a real joint loss across **multiple repairs** and candidate z assignments must be demonstrated, not a single-positive one-record denominator disguised as full comparative training.
- Check sampler stationary distribution and detailed balance before using energy-driven proposals; log candidate score/inference/robot verification budget identically for all three.
- Show diagnostic figures: root initial scene with real 3R bodies; decided outcome grid with missing masks; per-term losses/gradients; learned probability/energy of same-endpoint order pairs; observed-versus-predicted effects; predicted-versus-measured J; exact z-marginal normalization.
- Never use a learned low energy as an independent physical feasibility certificate. Robot verification retains the one-shot target-feedback boundary.

**PoC compute proposal:** CPU-only \(\le3,600\) aggregate CPU-s, \(\le7,200\) wall seconds; no teacher calls during model training; optional GPU use only with a new explicit budget. Run a minimal configuration first (one root, one short overfit per arm) before longer tiny-data overfits. Stop if mathematical losses/gradients/partition tests fail. Expected performance is **not** stipulated; report whether it actually overfits.

# Final gates and what a valid outcome means

**P5_LAYOUT_SAMPLER_PASS** — corrected versioned z slots, no duplicate/no-op multiplicity, exact marginal partition, validated G4B, and source integrity.

**P5_D3_LITE_COLLECTED / PARTIAL** — all planned roots attempted as budget permits, visible raw label denominators and UNKNOWNs, independent frozen splits, no label leakage or source contradiction. Two halves each have explicit stop gates.

**G4E_A_B_C_IMPLEMENTED** — three genuinely different models instantiated and trained with intended supervision, with all architecture-specific factors and gradient tests; checkpoint/version manifest and plots.

**G4E_TINY_OVERFIT_PASS / PARTIAL** — declared small-data objectives actually decrease, known decided order pairs ranked correctly when trained, joint B/C fully-decided z pools fit under exact normalization, and the decision uses no held-out cherry-picking. A failure is reported honestly; models should not be 'fixed' by weakening ground truth or leaking teacher data.

**G5/G6_NOT_AUTHORIZED** — no large-scale full training, statistically meaningful architecture superiority, 3D, robot hardware or long-horizon multi-target claim from this stage.

**Important branch if D3-lite coverage is weak:** still implement G4E mathematical PoC using P4 plus available compatible, decided earlier development records and synthetics. Record which architecture/hypothesis needs more real data. Next extension should target that missing evidence, not restart certificate-only research.

# Required delivery from the implementing agent

One next numbered immutable report; source/config/policy hashes; exact new/modified files and their line counts; commands and exit codes; G4B and affected regression tests; teacher evidence and per-root plots; corrected learner-view layout map; A/B/C checkpoints and loss curves; model-input privilege audit; actual compute and call accounting; PASS/PARTIAL/BLOCKED stage verdicts; commit hash and remote equality; separately costed recommendation for what would unlock G5/G6. Stage historical deleted root PDFs and user instruction files **only on explicit separate approval**, never as incidental cleanup.

The agent must **stop after G4E PoC**. Scaling from 8 roots to 40/300, full G5/G6 comparison, 3D and hardware require fresh authorization.
