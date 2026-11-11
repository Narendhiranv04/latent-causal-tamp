# Latent Causal TAMP: start here (v1.7 / v1.9)

**As of 19 October 2026.** The two revised guides define a prospective 2D experiment; **they do not edit the repository, authorize additional teacher compute or claim new training/robot results**. G4D's architecture migration completed; its actual physical evidence collection did not. Its frozen plan has no authorized compute numbers. All archived V1/G4A/G4D records stay unchanged.

## The three methods, with no conceptual conflation

- **A — LOCAL-SEQUENCE:** existing V2 local unary/pairwise MLP energies + GRU ordered-task/cost head; explanations from task-score counterfactual differences; sample ordered repair sequences via Boltzmann inference. Here the **energy factors are trained** but the Boltzmann sampler itself is not a trained classical machine.
- **B — JOINT-CAUSAL-EBM:** explicit binary outcomes of fixed-robot scene interventions, exact-order repairs and specified omissions; neural potentials and cause–repair coupling trained as a **joint conditional energy over repair r and explanation outcomes z**, using exact finite joint-energy losses where all outcomes are independently decided. Infer repair and explanation jointly using exact bounded-z marginalization for sparse 2D experiments. Pure B represents order through prefix-conditioned interactions, not a GRU.
- **C — HYBRID-JOINT:** B's joint causal/outcome variables and coupling **plus** A's order-sensitive GRU and GRU cost head. Test whether joint causal factors help when the GRU is already present.

All share the **same full articulated 3R robot, 48-grasp family, GT masks/known geometry, independent planner, teacher labels, episode boundary and candidate/call budgets**. Strong analytic geometry/matching, uniformly sampled ordered repairs, geometry-only neural variants and parameter-matched controls are mandatory. Outcome variables represent **scoped intervention results**, not automatically identified causal edges.

## Implement in this exact order after you provide the repo

1. **Nonmutating repo audit**: branch/HEAD/working tree, original config/profiles and G4D archived plan/report hashes, all tests and six replays.
2. **G4D-EVIDENCE**: ask for and freeze numeric teacher caps; run one sparse evidence plan at a time. Demonstrate a verified two-move execution, same-endpoint certified order contrast, decided scene effect and omission effect, and achieved joint continuity. If absent, **BLOCKED**.
3. **G4B**: validate all ordered sequence kernels and bounded joint-z marginalization exactly on finite mini spaces; detailed balance, variable-K Hastings ratios, masks, partition and gradients.
4. **G4C**: audit new **independent** 20-root development dataset and effect/cost/order label sufficiency. Split fresh 300 roots before mining descendants; never turn UNKNOWN into negative.
5. **G4E-ABC**: wire three models to the same tensors and verifiers; tiny-data supervised capacity checks, including actual order sensitivity, joint z gradients and mask invariance.
6. **G5-2D-ABC**: train three seed runs for each architecture with identical root splits/budgets; test BCE, effect, cost and joint energy losses, and freeze validation-selected thresholds.
7. **G6-2D-DECISION**: execute frozen held-out comparison with complete 3R target replay, explanation/order/cost metrics, strong analytic baselines and root-cluster uncertainty. Report the winner, tie or no supported improvement.
8. **G7–G10**: **do not start 3D or scripted long-horizon integration before the 2D decision report**.

## Files

- `latent_causal_tamp_methodology_v1_7.pdf` is the **scientific authority**: definitions, alternative energy equations, teacher labels, losses, joint inference, interpretations, ablations and falsification.
- `latent_causal_tamp_implementation_guide_v1_9.pdf` is the **execution authority**: module ownership, schema, stage gates, 2D fixtures, teacher collection, exact sampler tests, training checklist, comparisons, figures, logs and release conditions.
- The matching `.md` files are **editable source documents**. `architecture_overview.png` is an introductory schematic included in both PDFs.

When providing the current repository, request an **audit and mapped implementation plan first**, not implementation of all stages in one turn. No old files should be deleted or invalidated to make a new model fit a cleaner imagined repository layout.
