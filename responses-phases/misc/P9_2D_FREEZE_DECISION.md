# P9 2D freeze decision: **FREEZE_KEYED** (`ABC9K_KEYED_V1`)

**Manifest:** `runs/p9/2d_freeze_manifest.json` (`sha256:72b9a06e…`). **Rule:** pre-registered before any keyed result was read (`runs/p9/l3d/freeze_rule.json`, `sha256:efba5b4e…`).

**Gates:**

| gate | verdict | report |
|---|---|---|
| L3c-0 | PASS | 0034 |
| L3c-1 | PASS | 0035 |
| L3d | PASS | 0036 |

Historical suite 392/392 and 6/6 replays under the same CPU guard.

## What is frozen

**Model logic: the five-family joint Boltzmann outcome model**, unchanged in spirit since P9-L1:
- binary outcomes `z0` (= `zR[∅]`), `zS[I]`, and one `x_q` per physical sequence query;
- `P(z_S, x | c0, C) = P_S(z_S | c0) · exp(−E_K(x, z_S)/T) / Z_K(z_S)`, with exact elimination (scope cap 16, fail-closed).

**The keyed refinement (only change from `ABC9U_UNIQUE_V1`).** Every relational factor is instantiated **once per physical scope**:
- scene–query pairs once per (scene bit, query), computed from the query's own representation;
- omission links, omission–omission pairs and the higher-order hyperedge owned by the physical sequence;
- **not** per listing parent or slot role.

**Unchanged:**
- F2 unary (shared F2 / F4 scorer), F3 and F5 scene factors in P_S once, F4 pairs, F5 pairs and **all** higher-order terms;
- zero new parameters.

**Objective:** `mean_roots(−log P(D_c)) + 1·static BCE (endpoint-deduplicated) + 1·log-Huber witnessed J`. F1 static and travel J are outside the outcome likelihood.

**Inputs:**
- frozen DINOv2-small mask-pooled object features **enabled**, plus supplied geometry;
- proposed ordered moves and destinations; hypothetical pose edits.

**Labels:** VERIFIED 1, CERTIFIED 0, OPNEG-v1 BUDGET_INFEASIBLE 0 (operational); UNKNOWN / NOT_RUN missing.

**Deployed selector:**
- static-certificate precedence;
- root-prior admission `sigmoid(logit p / τ) ≥ threshold` (τ = 0.25, threshold = 0.7 from validation);
- then `(moves, predicted J, analytic C_d, E_static + T·softplus(−logit p), id)`;
- an empty admitted set means ABSTAIN.

**Checkpoint:** `runs/p9/l3d/ckpt/ckpt_K-B-full#s1.pt` (`sha256:d0cf4b6a…`), the lowest validation root NLL of the three keyed seeds (0.255; seeds 0 / 2: 0.348 / 0.261). The other seeds are kept as local hashes.

## Why keyed, and how strong that reason is

1. **Semantics (decisive).**
   - In the unique model, re-listing an already modelled omission as a candidate created new role- and parent-specific relational instances. That moved beliefs by up to 0.04 (B-full) and 0.30 (C-full) without any new physical outcome being modelled.
   - The keyed model is **exactly invariant** to re-listing, duplicates, permutation and renaming, while still responding to genuinely new outcomes or relations.
   - It is exact (brute force on 31 roots) and keeps every factor family and the higher-order terms.
2. **Prediction (non-decisive).**
   - At matched 200 updates keyed and unique are indistinguishable on validation: root NLL −0.001 [−0.024, +0.023]; repair accuracy 0.990 vs 0.980; scene NLL +0.014.
   - All pre-registered non-degradation conditions hold. The keyed model is **not shown to predict better.**

## Known limitations carried with the freeze

- **Training length.** The frozen checkpoint is at 200 updates. The 400-update unique checkpoints reach validation root NLL 0.065, a training-length effect visible for both formulations in P9-L3b. A matched 400-update keyed retraining is the first step for a future saved-data authorization. The freeze pins **model logic**; the checkpoint is the best *matched* keyed checkpoint, not a claim of best achievable fit.
- **Evaluation data.**
  - Validation is 12 roots, and the top 3 carry 91 % of the keyed model's NLL.
  - The disclosed P8c test is a legacy diagnostic. On it, full-vision 400-update models degrade while visual-zero models do not: an unresolved appearance over-fitting warning (P10 Q9).
- **Visual channel.** DINOv2 is kept because it is better on validation (−0.363 [−0.737, −0.060], sign-stable under leave-one-root-out). It is also intended for 3D. Its *independent, generalizing* benefit is not established.
- **Untested hypotheses:**
  - no proof-grounded κ = +1;
  - no decided same-endpoint order contrast in fresh data;
  - no omission-only labels;
  - the structured `z0–zS` pair is unidentifiable;
  - no physical execution of any P9 model; G+M remains the best executed method (P8d 9/12).
- **Identity.** `unique_factor.instances` dedupes candidate IDs by string. The frozen pipeline must call the identity check (`p9_l3c.check_identity`), or the keyed builder, which itself fails closed on an ID / sequence conflict.

## Next

`responses-phases/P10_TARGETED_CAUSAL_EVIDENCE_PILOT_PROPOSAL.md` is a design proposal (**REQUESTED, NOT AUTHORIZED**) for the physical evidence this frozen model needs:
- proof-grounded complementarity;
- same-endpoint order contrasts;
- omission necessity;
- feasible-original controls;
- constructor-disjoint scenes;
- appearance vs geometry;
- a blind one-shot comparison with G+M.

No 3D, data collection or teacher query has been started.
