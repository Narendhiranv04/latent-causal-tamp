# 0089 — P16 final: dual-method scientific decision

**Overall status: PARTIAL.**

| gate | status |
|---|---|
| shared | PASS |
| B methodology | **PASS** |
| D methodology | **PASS** |
| B prospective | primary SUPPORTED, with one strong negative |
| D prospective | **UNDERPOWERED / NEGATIVE** on effort; coverage 21 of 48 |
| oracle | NOT_RUN |
| temporary-target blocker marginals | UNDERPOWERED |

Historical P10–P15 artifacts are byte-identical (manifest of 50,082 files, 0 mismatches at every gate).

## 1. Shared physical substrate (both methods)

| component | evidence |
|---|---|
| deterministic provider (node budgets; no CPU / wall adjudication; `P16_FAST` profile) | identical trajectory hash, travel, budget counts and node counts across `PYTHONHASHSEED` 0 / 1 / 2 and under parallel load (4 roots default profile; 3 roots fast profile, which also equals the default) |
| alternate certified start transit | lower travel on 2 / 4 roots (009: 4.072 vs 4.655; 012: 2.008 vs 2.093); failed transit stays UNKNOWN_TRANSIT |
| multimodal lookup | online-only solves 2 / 8 roots vs lookup 4 / 4 on the common roots |
| scene-only API | no teacher catalogue, parking, roles, predicates or labels at runtime (deletion test) |
| expanded finite search | repeat moves (per-object ≤ 2), dominance, node caps, finite-graph-only claims |
| shared exact cache | virtual accounting test; all guides and arms on a root charged as if computed separately |
| independent replay | continuity + every transit waypoint + every record certified; 0 failures |

## 2. B — what the method is and what it showed

**Method.** Keyed, order-sensitive Boltzmann evaluation of complete ordered repairs, including the empty repair.
- **Inputs:** DINOv2 + numeric context.
- **Unaries:** scene / no-op unaries and order-head repair unaries.
- **Removed:** learned F1, F3, F4, F5 (combined), HO and J.
- **Joint:** exactly a product of Bernoullis, checked against brute force; UNKNOWN labels are summed out.
- **Decision rule:** no-op-first, calibrated on a separate split.

**Supported:**
- **The P15 feasible-original defect is fixed.** Correct no-op on 72 decided feasible originals rose from 7 (frozen K-B) to 32 (LB): +34.7 pp, p = 6e-8. Repair ability on infeasible originals was retained (non-inferior).
- **Generic-only coupling (new, pre-registered H-B2).** It raised strict TOP1 0.509 → 0.652 (16 / 0 discordant, Holm p = 0.0003) and gave the best validation NLL. This is the first positive evidence for any B coupling factor in isolation.

**Not supported or negative:**
- order-off vs order-on is n.s. on the test decision endpoint;
- no learned B arm beats "always do nothing" on the natural-mix strict TOP1 (0.643);
- LB's improvement is confounded by data and architecture (no full-B retrain on the new data).

**Untested:**
- higher-order F5q;
- learned J;
- full-B retrained on the new data;
- B on more-than-2-move repairs (catalogue limit).

## 3. D — what the method is and what it showed

**Method.**
- **Learned:** P(target feasible) and pairless union-blocker Bernoullis on the scene-only pool.
- **Labels:** corrected, with NO_CLEARING_SET / INCOMPLETE masked.
- **Recursion:** feasibility-only, DEV-recalibrated.
- **Search (non-learned):** scene-only movers and slots, multimodal certified library modes plus alternate transit plus online fallback, expanded finite lexicographic search (moves, measured joint travel). Guides reorder candidates only.

**Supported:** union-blocker diagnosis is accurate (gated F1 0.981 on 16 test masks; 0.818 on calibration), and union and necessary are separated (3 / 16 differ).

**Negative or underpowered:**
- **Search outcomes:** D guidance changed no outcome. 21 / 21 solved for every guide, 0 discordant, and effort differences under 9 % (Dp16 +1.7 % motion checks vs geometry).
- **Coverage:** DENSE coverage was 4 / 24, so the branch-heavy cohort where guidance could matter was mostly not evaluated.
- **Retraining:** the corrected-label retrain did not improve feasibility AUROC (0.805 vs 0.898; 5 positives).
- **Temporary-target blocker marginals:** not validated (2 labelled lattices).

## 4. Claim boundaries for potential papers

- **B (learning / reasoning).** A defensible claim exists: *"a keyed, order-aware energy over complete repairs with a generic scene–repair coupling term improves no-op correctness and repair selection in a prospective 2D cohort"*.
  - Needs replication of H-B2 on an independent cohort.
  - Needs a full-B retrain on the same data to separate data from architecture.
  - Must report the always-EMPTY baseline.
  - No physical or real-robot claim.
- **D (robotics).** **No publishable incremental claim yet.** Across P15 (32 roots) and P16 (21 roots), learned diagnosis never changed a search outcome. The non-learned search stack (deterministic certified multimodal lookup, alternate transit, finite-graph proofs) is solid infrastructure, not a learned contribution.
- **No shared core novelty.** B and D share only the physical substrate; their claims and experiments are disjoint.

## 5. 3D

**Not started (not authorised).** The specification is in `P16_3D_MIGRATION_SPECIFICATION.md`: robot, grasp sets, swept volumes, certificates that do not transfer, 10 families, input changes, gates, and a compute quote of ≈ 280k CPU-s.

## 6. Next blocking experiment per track

- **B:**
  - replicate H-B2 and test a stronger no-op gate on a fresh natural-mix cohort, powered against the always-EMPTY baseline;
  - add a full keyed B retrained on the same new data, to attribute the no-op fix.
- **D:**
  - first, budget a full DENSE-heavy cohort at the measured ≈ 550 CPU-s per 7-guide root (≈ 26k for 48 roots);
  - run the oracle guide;
  - only if the oracle shows headroom (it did not in P15: +1 / 32) should D-guided search be re-tested.
