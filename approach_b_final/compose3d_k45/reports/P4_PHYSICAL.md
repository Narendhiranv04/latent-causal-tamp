# P4: physical verification and oracle ordering diagnostic

**Protocol:** `P3_PREREG.md`.
- The sealed predictions (`P3_SEAL.json`, sha256 `effbf9a3…`; `P3_PREDICTIONS.jsonl.gz`) were committed and pushed at `0ffdb845c6` **before** any physical job.
- **Teacher:** the unchanged SHELF66V3 teacher on gvlab2 through `evaluate_k45.run_xb`.
  - B0/B1 run continuously (connector to q_ref only at the end).
  - B2/B3/B4 run chunked, with an executed and verified connector to q_ref after every group, and no teleport.
  - Y is `run_y` at the endpoint.
- Every X = Y = 1 was independently replayed: stored move witnesses, stored connector paths, then the stored target witness from the achieved state. **All 33 verified successes, primary and oracle, replay.**
- No retries; no fallback plans.

## P4a: end-to-end, public-only (20 roots × 5 arms, 75 unique jobs, 0 UNKNOWN)

| Arm | Verified successes (all roots) | 95 % exact interval | K4 / K5 | Successes with > 3 moves | NOOP / ABSTAIN | Median planning latency (p90) |
|---|---|---|---|---|---|---|
| B0 (EXACT4 K ≤ 3) | **2/20** | [0.01, 0.32] | 2 / 0 | 0 | 0 / 3 | 0.13 s (0.28) |
| B1 (direct K ≤ 5 extrapolation) | **5/20** | [0.09, 0.49] | 3 / 2 | 3 | 0 / 1 | 0.64 s (1.15) |
| B2 (greedy sequential groups) | **3/20** | [0.03, 0.38] | 1 / 2 | 2 | 0 / 0 | 0.21 s (0.39) |
| B3 (global set + chunk composition) | **2/20** | [0.01, 0.32] | 2 / 0 | 1 | 0 / 0 | 17.1 s (18.5) |
| B4 (Fig. 3(a) retarget + insert) | **2/20** | [0.01, 0.32] | 2 / 0 | 1 | 0 / 0 | 12.3 s (22.5) |

- **Failure phase:**
  - Every failure is decided (FAIL_X or FAIL_Y; UNKNOWN 0/100).
  - Of the 82 decided failures (100 plans − 14 successes − 4 ABSTAIN), **42 failed X at the very first relocation**; all other X failures are later relocation steps.
  - **No q_ref connector failed:** all 31 connectors reached by the arms executed and verified.
- **Paired comparisons** (wins / losses / decided ties; exact McNemar on discordant pairs):

  | Contrast | Wins | Losses | Ties | p |
  |---|---|---|---|---|
  | B3 vs B1 | 0 | 3 | 17 | 0.25 |
  | B4 vs B2 | 1 | 2 | 17 | 1.0 |
  | B1 vs B0 | 3 | 0 | 17 | 0.25 |
  | B4 vs B3 | 1 | 1 | 18 | – |

  20 roots support **no superiority claim** in any direction.
- **Verified long (> 3 move) public-only successes, all replayed:**

  | Arm | Root | Moves | Execution | Note |
  |---|---|---|---|---|
  | B4 | `k45-b2c2-035` (K4, fresh) | 4 | groups [1, 3], 2 connectors | Two **explicit enabling insertions** (objects 6 → 24 and 5 → 7), each placed before its parent. B0, B1, B2 and B3 all failed on this root. |
  | B3 | `srv-w0003-s004` (K4) | 4 | groups [2, 2] | B0 also solved this root with 3 moves, so a 3-move repair exists |
  | B2 | `k45d-srv3-w0061-…-k5v2j0` (K5) | 5 | groups [3, 2] | |
  | B2 | `k45d-srv3-w0078-s012-j0` (K5) | 4 | groups [3, 1] | |
  | B1 | `k45d-srv-w0018-s015-k4v2j0` (K4) | 4 | continuous | |
  | B1 | `k45d-srv3-w0059-…-k5v2j3` (K5) | 5 | continuous | |
  | B1 | `k45d-srv3-w0078-s012-j0` (K5) | 4 | continuous | |

- **Shorter repairs found.** On 3 witness-length roots a verified repair **shorter** than the witness length was found:
  - B0 with 3 moves on K4 roots `srv-w0003-s004` and `srv3-w0078-s012`;
  - B1 and B2 with 4 moves on K5 root `srv3-w0078-s012-j0`.

  As the plan anticipates, this is reported, not treated as a bug. It confirms that the witness-length labels are upper bounds.

## P4b: oracle-assignment diagnostic (after the seal; private verified assignment, no order; 95 jobs + 5 reused)

| Ordering of the known correct assignment | Verified successes /20 | K4 / K5 |
|---|---|---|
| direct p11 top-1 (continuous) | 5 | 3 / 2 |
| chunk-H top-1 (chosen two-group split, chunked) | 4 | 3 / 1 |
| seeded uniform random order (continuous) | 4 | 4 / 0 |
| mode control (chunk-picked order, continuous) | 5 | 3 / 2 |
| **private witness order with a forced q_ref split [2, m]** | **19** | 10 / 9 |

- **With the right objects and destinations given, the frozen X model's best order is no better than a random order** (5 vs 4 of 20).
- **The q_ref boundary contract is not the obstacle:** the witness order survives a forced intermediate q_ref return on 19/20 roots.
- **Order selection is therefore a binding limitation** of the frozen 3D X model beyond 3 moves.

## P4c: attribution (`P4_ATTRIBUTION.json`)

- **cVAE pool:**
  - The private witness assignment lies **entirely** inside the original-root cVAE top-4 pool on only **2/20** roots.
  - On average 51 % of the witness actions are in D4.
  - The witness destinations are generator parking cells. This does not prove that no D4 repair exists.
- **Candidate pools:** no arm's candidate pool contained the exact witness assignment (B1/B3 shortlist 0/20; B2/B4 pools 0/20). Every success came from a different assignment.
- **B4 search behaviour:**
  - Accepted insertions occurred during search on 20/20 roots, at depth ≤ 2.
  - The committed plan contained an insertion on 2/20.
  - The 64 temporary-task readout cap was reached on most roots (median 64).
- **Primary failure classes:**
  - (vii) gate/ABSTAIN: 4 plans (B0 3, B1 1).
  - (iv)/(v) order or boundary: no boundary failure.
  - Nearly all failures are relocation-phase X failures: the planner's chosen mover cannot be picked or placed in the current scene, consistent with missing enablers or a wrong order. The rest are endpoint Y failures (FAIL_Y 21 across arms).

## Resources (evaluation)

| Item | Value |
|---|---|
| Teacher jobs | 172 / 200 (2 adapter smoke + 75 primary + 95 oracle) |
| Worker CPU | 1.95 CPU-h (cap 24, owner-raised from 12) |
| Host | gvlab2, ≤ 36 workers |
| Planner inference | gvlab2 RTX 5090 (laptop freed on the owner's request): about 10 min for 20 roots × 5 arms, plus oracle and parity reruns, < 0.3 GPU-h |
| Device parity | B0 reproduces the archived DEV decisions 5/5 on the 5090 |
| Determinism | rerun of 2 roots identical |

**Figures:**
- `figures/p4_outcome_heatmap.png`
- `figures/p4_plans_K4.png` and `figures/p4_plans_K5.png`: each root's private witness (shown after the seal) and every arm's sealed plan, with numbered arrows, group colours, '|q' forced q_ref returns, and the verified outcome and failure phase.
