# P0 pre-registration: complete-repair cVAE vs factorized proposal + X/Y

Written before any CR-cVAE fit, any held-out inference and any teacher query. Changes after this point go in `AMENDMENTS.md` with a reason and a timestamp, and never depend on held-out outcomes.

## 0. Authorization status

The starting prompt **proposes** an envelope and says it must be affirmed before new jobs run. It has **not** been affirmed in this session. Until it is:

| Stage | Needs | Status |
|---|---|---|
| P0 audit, P1 code / tests / CPU overfit fixtures | nothing new | done |
| P2 six CR fits (GPU), VAL pools | owner affirmation: ≤ 4 GPU-h training, ≤ 3 GPU-h inference | **blocked** |
| P3 inference on the locked V3.4 cohort roster (public rows only) | evaluation-only use of the cohort after freeze | **blocked** |
| P4 physical verification of sealed picks | ≤ 450 queries/domain, ≤ 8 (2D) + 16 (3D) teacher CPU-h, 8–16 workers, ≥ 4 cores free, laptop teacher runtime | **blocked** |
| Storage | proposed 15 GiB; **only 2.0 GB free on `/home`** | study kept < 1 GB |

Protected historical TEST is **not** needed (the V3.4 cohort is used) and is not requested.

## 1. Arms (seed 0 for every primary arm)

| ID | Proposal | Selection | Output |
|---|---|---|---|
| **C0 / OURS** | frozen bundle sampler, S1 top-6 → top-4, proposal seed 0 | all legal ordered K ≤ 3 (`construct.assignments` + permutations), frozen arm-D X/Y s0, `exhaustive.Selectors` with the production rule | NOOP / REPAIR / ABSTAIN |
| **C1 / CR-ONLY** | CR-cVAE s0, main-budget pool | integrated head: argmax of 3 classes (ties NOOP > ABSTAIN > REPAIR); REPAIR → argmax log p̂(r \| c) over the unique pool (ties: shorter, smaller displacement, lexicographic); REPAIR with an empty pool → ABSTAIN | same |
| **C2 / CR+XY** | the **same** pool (identical hash, order and checkpoint as C1) | frozen X/Y scores every unique sequence once; production rule (`noop_gate 0.5`, `eta 0.3`, α = β = γ = 0) through `exhaustive.Selectors` | same |
| C3 (secondary) | CR-cVAE s0, up to 4,096 raw draws, stop at C0's scored count | as C2 | model-only unless budget remains |
| C4 (secondary) | C0's ordered pool, deterministic subset: sha256 order within k = 1 / 2 / 3, round-robin over k, size = C2's unique count | as C0 | model-only unless budget remains |

Diagnostics on the same pools, never called a one-model baseline: C1 first draw; C1 common gate (frozen X/Y p_noop ≥ 0.5 → NOOP, else CR likelihood argmax, no eta); ungated best repairs on K1–K3. No MCTS, no extra order permutations in C2, no hybrid pools, no new thresholds.

## 2. Cohort (locked, retrospective)

- **Source:** the V3.4 fresh Option-B cohort (`~/abf_v34/final/PRIVATE_INDEX.jsonl`, sha256 `7a1336da8e50…`), compatible on every point the plan lists: public rows, raw scene files, sealed frozen-bundle predictions, teacher caches from the same runtime, family ids. Its C0 outcomes are historically known, so this is a **locked retrospective comparison**, not an independent benchmark.
- **Roster (`P0_COHORT.json`, private K per root in `~/cr_cvae_private/cohort_{dom}.jsonl`):** per domain 50 K1 + 50 K2 + 50 K3 + 30 K0 + 30 NONE = 210 roots. Order within a private stratum is sha256(`CRCVAE_COHORT_V1|root`), one root per parent family first, then the rest. No outcome or prediction was read to build it. 2D draws 210 distinct families; 3D 149.
- Every selected root stays in every denominator, including empty pools, crashes and unqueried picks. Same roots for every arm. True K, witnesses and labels never reach a planner process (planner reads `public_*.jsonl` rows only).

## 3. CR-cVAE (frozen design)

- **Architecture (`model.py`):** per-object token MLP on the frozen sampler's 14 `scene_features` columns (target as reference, bundle TRAIN-only scalers) + goal offsets + movable flag; masked mean + max pooling + global MLP on [S0 occupancy, `task_features` of the target] → c; tokens re-contextualized with c; per-cell MLP + c. Posterior (training only): GRU over (object token, destination cell, position) then STOP, + c → μ, log σ². Prior N(0, I). Decoder: h₀ = tanh(MLP[c, z]); per step a pointer over eligible objects + STOP, then a bilinear destination head over available cells, then a GRU update on [object, cell, z, position]. Decision head: MLP(c) → 3. h = 128, z = 8 (the released sampler's values).
- **Static masks:** eligible object = movable (non-target, non-fixed, real token), not moved, some destination left; destination = support cell, not occupied in S0, not the goal, not reserved. STOP illegal at t = 0, forced at t = 3 or when nothing is eligible; empty root → explicit no-candidate. Verified by an exact normalization test (Σ p(r | c, z) = 1 over all legal sequences).
- **Loss:** root-weighted mean of [−log p(r | c, z ~ q) + β KL] over verified ordered repairs (sequence-summed) + 1.0 · CE(decision) on a separate root-uniform batch of 256 labelled TRAIN roots per step. Unweighted classes.
- **Budget = the released sampler's actual fixed-step schedule:** 2D 2,400 steps / eval every 30; 3D 1,520 / 19; batch 256 ordered repairs; AdamW lr 1e-3, wd 1e-4; clip 10; β linear 0 → 1 over the first 10 evaluations; no early stopping (fixed steps). This is about 96 (2D) / 80 (3D) passes over the triples, above the plan's nominal 80-epoch cap for 2D; the plan's preference for matching the production step budget decides it.
- **Selection:** minimum of weighted VAL −ELBO (β = 1, fixed posterior noise seed 12345) + VAL decision CE, earliest tie. No physical query.
- **Seeds 0, 1, 2 per domain; seed 0 is the deployment checkpoint**, fixed now. Seeds 1, 2 report DEV likelihood, generation and decision stability only.
- **Pre-registered remedy (at most one, both domains, preserving the original):** triggered iff, at the seed-0 checkpoint of either domain, VAL KL < 0.05 nats **and** VAL known-witness ordered recall@256 < 0.5. Remedy = free bits, 0.05 nats per latent dimension. The remedy replaces the original only if its VAL selection metric (plain −ELBO + CE) is lower. KL collapse alone is not a trigger: the released per-object sampler itself ends at KL ≈ 2e-4, and an autoregressive decoder may legitimately ignore z.
- No architecture tuning. One optional fixed-width control on DEV only if the CR parameter count exceeds the combined frozen system; default off.

## 4. Inference budgets (DEV rules, fixed now)

- Pool: 1,024 raw prior trajectories per root from `torch.Generator(seed = sha256("CRPOOL|root|0"))` on the evaluation device; budget b = unique legal sequences among the first b draws (b ∈ {64, 256, 1,024}, nested). Duplicates, no-candidate draws and illegal draws are counted.
- **Main budget 256**, switched to 64 for both domains and both arms only if, on 100 DEV roots per domain, p90 per-root C1 + C2 time > 10 s or GPU peak > 6 GiB.
- C1 likelihood: L = 64 shared latents (`sha256("CRLIK|root|0")`); L = 16 only if C1 selection p90 > 5 s on DEV. All U · L decoder passes are counted.
- 1,024 is a saturation diagnostic. C3 hard cap 4,096 raw draws.
- Matched-wall diagnostic: 20 DEV roots per domain (sha256 `CRCVAE_WALL_V1`), caps chosen from {0.05, 0.25, 1.0} s after the DEV hardware audit and frozen in `P2_FREEZE.json`; CUDA-synchronized, 3 repeats after warm-up, only when no other GPU job runs.

## 5. Physical evaluation (P4)

- Sealed top-1 picks only, no retries, no fallback, no adaptive top-k. Cache reuse only for the exact (root, ordered sequence, teacher runtime) key from the V3.4 caches (same host, same envs).
- **Query priority per domain (cap 450):** (1) C1 and C2 REPAIR picks on K1–K3 roots (≤ 300); (2) any C0 pick not already cached (expected 0 if C0 re-run equals the sealed V3.4 pick); (3) REPAIR picks of any arm on K0 / NONE roots. If the projected total exceeds 450, tier 3 is trimmed first, then tier 1, each by sha256(`CRCVAE_QCAP_V1|root`) with all arms of a root kept together. Unqueried picks stay in the denominator as UNQUERIED.
- 3D cost is profiled on the first 20 jobs before the rest are dispatched. Dispatch stops with headroom before the CPU-hour cap.

## 6. Label mapping

| | strict (primary) | operational (sensitivity) |
|---|---|---|
| 2D | decided iff status ∈ {VERIFIED, EMPTY, CERTIFIED_INFEASIBLE}; `UNKNOWN_*` → UNKNOWN | historical V3.4 convention: stored value (UNKNOWN_* = 0) |
| 3D | decided iff `resolution = EVALUATED` (planner-budget failures are 0 by teacher contract, disclosed); `UNRESOLVED_*` → UNKNOWN | same as strict |

Z = 1 iff X = 1 and Y = 1; Z = 0 iff a factor is decided 0; else UNKNOWN. On K1–K3 roots NOOP and ABSTAIN are unsuccessful. K0: correct = NOOP (Y(empty) from the V3.4 ground-truth query). NONE: correct = ABSTAIN; a verified successful repair on a NONE root is reported separately as evidence against the relative label.

## 7. Statistics and decision rules

- Per domain, K1–K3 pooled and by K. Counts N, verified success, decided FAIL_X / FAIL_Y, UNKNOWN, NOOP / ABSTAIN, UNQUERIED.
- **Primary statistic:** all-root strict verified success (verified successes / N; UNKNOWN and UNQUERIED count as not verified). Co-reported: complete-case difference among roots decided for both arms; best/worst bounds assigning UNKNOWN 1/0 per root.
- Paired family-cluster bootstrap (parent family; 4,000 draws, seed 0), stratified by K.
- **Primary contrasts (Holm over 4):** 2D C2 − C1, 2D C0 − C2, 3D C2 − C1, 3D C0 − C2. Two-sided bootstrap p = 2 · min(P(Δ* ≤ 0), P(Δ* ≥ 0)). C0 − C1 is reported unadjusted.
- **Improvement** only if the Holm-adjusted test rejects with Δ > 0, the 95 % lower bound > 0, UNKNOWN ≤ 20 % in both arms and ≥ 90 % of roster roots evaluable. A point gain ≥ 5 pp is reported as practical size, not required. A CI covering 0 = no established difference, never equivalence. UNKNOWN > 20 % → INCONCLUSIVE whatever the point estimate.
- Interpretation rules of plan §6 P5 apply verbatim (scorer vs proposal vs budget attribution).

## 8. Deviations from the plan, declared now

1. Training length follows the production fixed-step budget (§3), not 80 epochs / patience 15.
2. Audit code lives in `p0_audit.py` (not in the plan's file list) to avoid a module-name clash with `repair_ranking/audit.py`.
3. Cohort caps: 50/50/50/30/30 per domain (plan targets), not the whole cohort, because the full 2D K1–K3 set (394 roots) would need up to about 790 new queries against a 450 cap.
4. 3D strict labels cannot separate geometric from planner-budget negatives (§6).
5. Storage capped at about 1 GB by the free disk, not 15 GiB.
