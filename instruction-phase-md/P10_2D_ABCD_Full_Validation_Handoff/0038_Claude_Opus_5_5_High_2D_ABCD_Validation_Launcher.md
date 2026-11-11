# Claude Opus 5.5 High — 2D A/B/C Validation + Minimal D Launch Prompt

Continue `Narendhiranv04/latent-causal-tamp` after successful P10-0/P10a, latest verified commit `dd12f0ce354c16e2525f88805cf2a8b5e811aadf` (with pre-teacher prediction-freeze `3afa81c2f8804fc1a8d11e08e2b3f010286fc784`). Inspect actual remote/local HEAD; preserve all unrelated user changes.

**Read the entire binding execution contract:**

`instruction-phase-md/0038_P10b_P10e_2D_ABCD_Implementation_and_Scientific_Validation_Contract.md`

Also read the project's Methodology v1.8, Implementation Guide v2.0, P9 freeze records, P10 contract and P10-0/P10a reports, provenance and gates. Inspect the real code and teacher evidence. **The new contract takes precedence for this task; do not silently change the frozen A/B/C methodology.**

## Objective

Finish a rigorous, professor-defensible **2D scientific investigation**, not another architectural redesign. I want:

1. End-to-end, matched physical assessment of **A** (independent GRU), **B** (keyed joint Boltzmann with predecessor ordering) and **C** (same keyed graph with GRU ordering), compared fairly with **SF, geometric controls and G+M**.
2. Independent, genuinely decided physical examples showing **complementarity, redundancy, action-order dependence, omission necessity, harmful interventions, destination effects, and difficult 3-/4-obstacle rearrangements** under the existing 2D 3R-robot R4 four-move cap. Report exactly how many moves were *witnessed* versus how many are *proven necessary within a fully checked catalogue*. No unsupported five-/six-move claim.
3. Retrain all approaches on representative new mechanism data (three seeds), including **factor-wise retrain-without-factor ablations**, frozen validation calibration, independent lineage splits, a sealed blind holdout, uncertainty intervals and separate **strict TOP1** versus planner-assisted TOP5 evaluations. Actually execute A/B/C on chosen repairs under the defined simulator one-shot protocol; never use IK/planning to test hypothetical alternatives in learned inference.
4. Implement **Approach D only as initial target retrieval feasibility + causal blocker identification**, with one small conditional Boltzmann machine (feasibility scalar and unary/optional pairwise blocker energies). Train it using independently decided teacher counterfactuals and prove its blocker ground truth, including jointly necessary and alternative sufficient clearing sets. Evaluate feasibility accuracy and blocker precision/recall/exact-set accuracy against GT, pairless-D and geometric controls. **DO NOT implement destination selection, recursive displacement, an obstacle-moving controller, or D physical execution.** Those remain future questions.
5. Produce detailed component-by-component evidence that the implemented F1–F5, order encoders, teacher-label pipeline, exact likelihood, selection algorithm, visual inputs and D Boltzmann normalization work as intended; run ablations to see whether each component **actually improves held-out performance**. Be prepared to report that A/SF wins or some B/C factors add nothing.

## Scientific boundaries

- P10a's 14 roots are **adaptive disclosed pilot data**. Use for diagnosis/development or training only, never as blind evaluation. Earlier P8c disclosed test is also not a selection set.
- P10a showed real proof-grounded mechanisms but **all models failed novel H1/H3**, and keyed B/C reversed their ranking relative to old validation. Treat that as the motivating missing-coverage question; do not preselect B/C as winners.
- Current B/C exact graph has `MAX_SCOPE=16`; report capacity failures/abstentions on complex candidate sets, never silently skip difficult roots or substitute a different model. Current R4 teacher has `move_cap=4`.
- Strictly distinguish original physical repair, hypothetical fixed-q0 target-only edit, oracle teacher certificate, planner-budget operational negative and missing query. The physical repair `A` on P10a H1 root 01 was BUDGET, while its matching edit was certified.
- A/B/C do not natively output direct blocker labels. Compare all four on **matched initial retrieval feasibility**. Evaluate D's direct blocker labels versus pairless D and heuristics; include A/B/C blocker attribution from counterfactual scene predictions **only where the full, faithful query scope is supported**, with coverage denominators and no model redesign.
- D's only use of parking poses is to define *frozen teacher counterfactual labels*. D must not predict, choose, plan or execute parking poses.
- No 3D, hardware, Slot Attention, external paid calls, unsupported ground-truth fabrication or architectural overhaul. Prefer small existing code files and a few new files of ≤300 logical lines each.

## Execution and stopping

Follow P10b-0 → P10b-1 → P10b-2 → P10c → P10d → P10e as **gated phases under the contract's hard aggregate CPU caps**. Do not pause for a new generic prompt between passed gates. If a constructibility, scientific-power, computational-budget, safety/provenance or frozen-split gate fails, stop with a rigorous `BLOCKED`/`UNDERPOWERED` decision rather than expanding the budget or inventing a successful result. Preserve full audit trails, root and model hashes, all unsuccessful cases and recorded physical witness/certificate visuals.

First: audit commit and P10a evidence, freeze hypotheses/splits/teacher budget, correct H7/H8 acceptance requirements and implement/test only D's simple probability and blocker inference. **Before any new teacher collection, push a preregistration commit containing the immutable plan, datasets split roster and D label definition.** Then perform bounded constructibility and proceed only through documented GO gates.

Deliver the new reports 0039–0044, `P10_2D_SCIENTIFIC_DECISION.md`, and `D_DESTINATION_AND_RECURSION_DEFERRED.md` exactly as specified, plus checkpoints, data/compute manifests, visualizations and all code/tests. Push verified commits, quote their full SHAs, explicitly identify the scientific winner/limitations and state what remains unproven. The expected outcome is **truthful, complete 2D evidence**, not manufactured superiority for B/C.
