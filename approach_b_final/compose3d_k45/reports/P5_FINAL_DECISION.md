# P5: final decision for the 3D K4/K5 composition pilot (exploratory, 20 roots)

## Decision labels (plan §8; every claim is limited by witness length)

All 20 roots are `WITNESS_LEN_k_MIN_UNKNOWN`: a verified continuous witness of length k, with no verified shorter subset of that witness. **No root has a certified minimum K.** On 3 roots an arm found a verified repair shorter than the witness length (below).

| Label | Holds? | Evidence |
|---|---|---|
| **COMPOSITION_WITNESSED** | **yes** | Public-only composed plans of more than 3 moves completed every q_ref boundary and the target, and replayed: B3 4 moves [2+2] on `srv-w0003-s004`; B4 4 moves [1+3] on `k45-b2c2-035`; B2 5 moves [3+2] on a K5 root and 4 moves [3+1] on another K5 root. This is existence evidence only. |
| **RETARGETING_WITNESSED** | **yes (1 root)** | B4 on fresh K4 root `k45-b2c2-035` (B0–B3 all failed there). The committed 4-move plan contains two explicit enabling insertions (objects 6 → 24 and 5 → 7), each preceding its parent in the trace. The plan executed chunked [1, 3] with verified connectors and replayed. **This does not show the insertions were necessary**: no counterfactual was run. |
| ORDERING_ONLY_WITNESSED | no | Public-only composition also succeeded. |
| DIRECT_ONLY_WITNESSED | no | Composed arms also succeeded. |
| NO_COMPOSITION_ESTABLISHED | no | |

- **No superiority claim.** Verified successes out of 20: B0 2, B1 5, B2 3, B3 2, B4 2.
  - B3 vs B1: 0 wins, 3 losses (exact p = 0.25).
  - B4 vs B2: 1 win, 2 losses (p = 1.0).
  - All intervals overlap. UNKNOWN is 0 %, so no comparison is flagged inconclusive for missingness; the sample is simply small.
- **Keep the released short-horizon method (B0 / EXACT4 K ≤ 3) unchanged.** This pilot does not warrant a change.

## What the pilot shows

1. **The frozen 3D cVAE and X/Y models *can* produce verified 4–5-move repairs at inference without training.** Every arm except B0 did so at least once (B1 3×, B2 2×, B3 1×, B4 1×).
   - The rates are low: at most 25 % of roots, and most failures are a planner-chosen first move that cannot execute.
2. **Ordering, not the q_ref boundary, is the binding limitation** (oracle diagnostic).
   - Given the true assignment, the frozen X model's best order succeeds 5/20 and the chunk-H order 4/20, against 4/20 for a random order.
   - The true witness order with a forced q_ref split succeeds 19/20.
   - Short-horizon chunking with q_ref returns is physically compatible with these repairs; the learned execution ranking beyond 3 moves is not reliable.
3. **Candidate discovery is also limited.**
   - The witness assignment lies wholly in the original cVAE top-4 pool on 2/20 roots.
   - No arm's candidate pool contained the exact witness assignment; all successes used other assignments.
4. **Fig. 3(a) retargeting is mechanically active but rarely decisive.**
   - B4 accepted insertions on every root during search.
   - It committed an insertion plan on 2 roots, and 1 of them succeeded physically.
   - Its temporary-task readout budget (64) bound on most roots.
5. **Cost:**
   - Composition costs 12–17 s median planning time (B3/B4), against 0.13 s for B0 and 0.6 s for B1, on an RTX 5090, uncached.
   - Teacher verification is separate (`P4_PHYSICAL.md`).

## Hypotheses (exploratory)

- **Direct extrapolation (B1) vs chunk composition (B3) on the identical shortlist:** composition did not help (0 wins / 3 losses). The modes also differ physically (continuous vs forced q_ref), and the oracle mode control shows equal success for the same order in either mode (5 vs 4 of 20).
- **Recursive insertion (B4) vs flat greedy (B2):** inconclusive (1 win / 2 losses). Their construction differs, so this is not a single-factor comparison.
- **The learned pY_temp proxy for temporary tasks is OOD.** No calibration claim is made.

## Deviations, limitations, what was not run

- **Cohort:**
  - Not 20 fresh roots. It is 4 fresh K4, 5 historical-unexposed K4 (re-certified), 1 K4 derived from an unexposed historical K3, and 10 K5 derived from K4 parents by one necessary enabler each.
  - The owner authorized this composition on 2026-11-26.
  - Derived roots share layout lineage with their parents; 4 K5 parents are also roster K4 roots.
- **Construction:**
  - Every scene is direct blockers plus enabling obstacles; the plan's three construction styles could not come from the existing generator.
  - Minimum K is not certified (the generator's route and BFS checks are planner-relative).
- **Hosts and caps:** gvlab2 (generation, evaluation, GPU inference), gvlab (K5 derivation) and the laptop (generation until freed at the owner's request, about 03:00 IST; no inference).
  - **Generation:** 62.8 worker CPU-h (owner-raised caps: 24 → 60 → 150 → unlimited), 764 teacher jobs and 517 attempt records, every censored attempt charged and never re-run.
  - **Evaluation:** 172 jobs and 1.95 CPU-h.
  - enigma was never used.
- **Not run:** the matched flat-beam control (optional, model-only), K6+, 2D, any training or calibration, and causal-necessity counterfactuals for B4's insertions.
- **Rendering:** figures are geometric drawings from real cells, sizes and heights. Physics rendering is disabled in the teacher environment, so there are no simulator videos.

## Reproduce

- Generation: `generate.py` (route + chain, `run_items` for RECERT / DERIVE / FRESH, `assemble2`).
- Inference: `run.py predict` (sealed).
- Physical: `evaluate_k45.py work` (gvlab2).
- Oracle: `oracle.py plans|jobs`.
- Analysis: `evaluate_k45.arm_outcomes` / `summarize` / `paired`.

Private data (cohort index and roots, witnesses, teacher caches) lives in `~/k45_private`, gvlab2 `naren_workspace/k45` and gvlab `/home/nav/k45`.
