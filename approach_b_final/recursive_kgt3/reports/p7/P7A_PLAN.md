# P7A plan: public, bounded candidate repair (frozen before implementation results)

Branch `naren/kgt3-exec-composition`, from `60e7006d50`. This document was written **before** any P7A code was run on DEV. Every choice below, including the primary score, the budgets, the arms and the metrics, is fixed here so that no DEV label can select a variant.

## Motivation (from the evidence so far)

- **P5A:** 40 of 53 teacher-Y P4 endpoints are not statically reorderable. In 29 of them a mover's pickup is blocked by never-moved clutter, so the object set must change, not only the order. 22 are at the 12-move cap.
- **P6A:** frozen chained-X px does not rank physical execution (AUROC about 0.40), so it is **not** used as a feasibility gate or as the step score. Public source clutter and base distance were informative on exposed DEV roots; that is a prior observation, not a P7A selection.
- **P3 D3 (historical):** the frozen temporary-target ŷ(A→d) ranks static move feasibility (AUROC 0.80) but is miscalibrated by an order of magnitude, so it is usable **only as a soft log score**, never as a threshold.

## Algorithm: repair beam (`p7_repair.py`, public)

**Input:** a base endpoint, meaning an assignment A = {(o, d_o)} from the sealed P4 pools, chosen by the P6A public rule (top frozen hY), plus the public DEV scene and the frozen bundle.

**State:**
- `plan`: the ordered executed moves;
- `pending`: required moves not yet executed;
- `dropped`: required moves removed.

Cells follow from S0 + plan. The merge key is (set(plan), set(pending objects), set(dropped)). The cost-to-go depends only on these, so merging is exact for the score.

**Expansions** (all respect the grammar: destination originally empty and legal, not G0, not currently occupied, not reserved as a pending move's destination; each object moved at most once; target never moved; ≤ 12 moves):
1. **Execute a pending move** (o, d), where d ∈ D(o):
   - D(o) = {d_o} in arms without destination adjustment;
   - D(o) = {d_o} ∪ P(o) with destination adjustment.
2. **Enabling move** (e, p): e is a *public suspect* (below), not used, not pending, not T0, not fixed; p ∈ P(e).
3. **Drop** a pending move (replacement or redundancy). Cost: λ_d + max(0, log ŷ_end(plan ∪ pending) − log ŷ_end(plan ∪ pending ∖ r)), where ŷ_end is the frozen endpoint Y.

**Public suspects** (a hand-designed heuristic, explicitly a hypothesis about blocking):
- *Anchors:* the current cells of pending movers and their primary destinations, the target's cell, and G0.
- *Level 1:* objects whose cell is within 1.5 cells of an anchor (8-neighbourhood).
- *Level 2:* objects within 1.5 cells of a level-1 suspect's cell. This supports multi-step enabling chains.
- Ordered by (level, distance to the nearest anchor, index); keep k_s = 6.
- **Not limited to P4's objects:** any movable object may become a suspect.

**Placement candidates** P(e) (≤ 8, deduplicated), drawn from two sources:
- **frozen cVAE top-4 at S0** (the unchanged frozen proposals), filtered for current legality;
- **public parking top-4:** legal free cells ranked by (fewest occupied 8-neighbours, farthest from the anchors, index).

So placements are not confined to the old top-4.

**Step score** (lower is better): −log max(1e-4, φ(c, o, d)). The primary φ is fixed **here**:
- φ = √(φ_G · φ_Y);
- φ_G = exp(−0.5 · (occupied 8-neighbours of the source + of the destination)). This is a **hand-designed public clearance heuristic**.
- φ_Y = frozen temporary-target ŷ of task (o → d) in the hypothetical scene Edit(S0, plan), with the robot at `q_ref`. This is a **learned (frozen) prediction**.
- φ is a soft score; there is no threshold or gate anywhere.

**Completion:**
- A state is complete when `pending` is empty.
- Final score = path cost − log max(ε, φ(T0 → G0 in the final scene)) − log max(ε, ŷ_end(final assignment)).
- Return the top 5 complete candidates.

**Beam:** B = 8, at most 24 expansion layers (moves plus drops), and at most 12 moves.

**Rebuild** (FULL only): if the first pass yields no complete candidate, run a second pass with the remaining budget. Its core = the original movers within 1.5 cells of the target's cell or G0, or else the 3 movers nearest those.

## Matched budget and stopping rules (identical for every arm)

- **Per endpoint:** Φ_MAX = 2,000 step-score requests (each φ request is one frozen ŷ call plus geometry; counted before the cache) and Y_MAX = 300 ŷ_end requests.
- An arm **stops** when the beam is empty, after 24 layers, or when either budget is exhausted. It then returns the complete candidates found so far.
- Actual consumption is logged per arm.

## Arms (one code path; configuration flags only)

| Arm | Enablers | Drops | Destination adjustment | Rebuild | Proposals |
|---|---|---|---|---|---|
| FULL | ✓ | ✓ | ✓ | ✓ | suspects + P() |
| DEST_ONLY | – | – | ✓ | – | P() for required movers |
| OBJSET_ONLY | ✓ | ✓ | – (original movers keep d_o) | – | suspects + P() for enablers |
| FLAT | non-recursive: no required set; any movable object × P(); every state is a candidate | – | – | – | same generators |
| RANDOM | FULL skeleton, but suspects = seeded random k_s movable objects, placements = seeded random legal cells (same counts) | ✓ | ✓ | ✓ | random |
| ORIG (reference) | P4 order of A, zero search | | | | |
| FULL_φG / FULL_φY | score ablations (reported; **not** used to pick a winner) | | | | |

## Endpoint sets

- **Method set (public):** the 50 P6A endpoints, the top-2 by frozen hY per root over 25 DEV roots.
- **Diagnostic set (evaluator-selected, label-free file):** the 53 P5A teacher-Y endpoints, used to measure only.
- All DEV roots are exposed, so all results are **exploratory**. ENG2_e3c632c779c0 is reported separately.

## Offline evaluation (`p7_eval.py`; labels only after predictions)

- **Availability:** at least one complete candidate within budget.
- **Top-1:** static-order validity of the committed order (P5A checker); static-order existence for its assignment (subset DP); static final-target liveness; frozen ŷ_end; length; moves added, dropped and re-destined.
- **Generation vs ranking:** any static-valid order among the top 5 (generation) vs the top-1 (ranking).
- **Diversity:** distinct proposed objects and destinations; objects absent from every P4 pool of that root; destinations outside the S0 cVAE top-4.
- **Cost:** Φ and Y requests, frozen calls, wall time.
- **Enabler audit (private, evaluator only):** for P5A pickups blocked by never-moved objects, do the public S0 suspects contain the kill-table blockers, and does a FULL candidate move them? Were those objects absent from the P4 pools?
- **Per-K strata;** excluding the exposed root.

## Synthetic fixtures (deterministic, mock φ / ŷ_end, no frozen model)

| Fixture | Scenario |
|---|---|
| F1 | missing pickup enabler |
| F2 | destination-induced blockage (only a destination change fixes it) |
| F3 | two-level enabling chain |
| F4 | redundant original mover |
| F5 | 12-move cap with one redundant mover and a needed enabler, so replacement is forced |
| F6 | rebuild |

**Expected results:**
- FULL solves all six.
- DEST_ONLY fails F1, F3 and F5.
- OBJSET_ONLY fails F2.
- Invariants checked throughout: legality, no target move, no repeats, ≤ 12 moves, determinism, budget accounting.

## Gate (decided by the plan, not by the outcome)

- **BLOCKED:** FULL fails any synthetic fixture.
- **REVISE:** on DEV, FULL shows no credible advantage over **both** FLAT and RANDOM in top-1 static validity or static-order existence, with matched budget.
- **PROCEED (to propose P7B):** otherwise. Physical claims still require P7B.

## Explicitly not done in P7A

No teacher call, training, dataset generation, release_v2 access, or P7B/P7C execution.

**Minimal code:** `p7_repair.py` (public; reuses `data.HypoRoot`, `data.check_sequence`, `models.Frozen.ytask/propose/y_end`), `p7_eval.py` (evaluator; reuses P5A `Chk`, `run_order`, `classify`), and `tests/test_p7_repair.py`.
