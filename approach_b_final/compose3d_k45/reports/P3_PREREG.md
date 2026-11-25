# P3 pre-registration: frozen configuration for the sealed K4/K5 inference

This was registered after P0–P2 and **before** any inference on the fresh cohort. Nothing below may change after inference. Hashes are in `P3_PREREG.json`, which is written by `run.py` / `generate.py assemble` at registration time.

## Models and harness

- **Bundle:** frozen 3D bundle `~/abf_v34/approach_b_bundle`, hash-checked: S1 TaskCVAE `scratch_all` s0 and coupled X/Y arm D s0. The rule is NOOP gate 0.5, η 0.3, α = β = γ = 0.
- **Harness:** `scene.py`, `models.py`, `compose.py`, `recursive.py`, `run.py` at the registered commit.
- **Execution:** seed 0, float32, inference mode; one CUDA generator seeded 0 per proposal call.
- **Hardware:** laptop RTX 5060.
- **Caches:** reset per root × arm, so timings are uncached.

## Cohort

`~/k45_private/cohort/PUBLIC.jsonl` (`benchmark.public` rows). The sha256 and roster counts are in `P1_COHORT.md` and `P3_PREREG.json`. Inference sees public rows only.

## Arms (one committed plan per root and arm; no teacher, oracle or fallback)

| Arm | Candidates | Score | Physical mode |
|---|---|---|---|
| B0 | D4(S0), all K ≤ 3 sets × all orders (natural exact; no cap) | frozen p11 | continuous |
| B1 | the B0 pool + shared D4(S0) length-4/5 endpoints → Y_global shortlist L = 32 per length (≤ 2 per object set first, then fill; a deterministic hash sample if the endpoint cap of 100,000 binds) × all orders | direct p11 at S0 (OOD) | continuous |
| B2 | greedy: per step every legal group of 1–3 from D4 requeried on the rebased scene (original task), local score pX(group) · Y_global(prefix + group); ≤ 5 moves, ≤ 5 groups; every prefix is a stopping candidate | p11 if m ≤ 3, else H of the actual partition | chunked at the actual group ends |
| B3 | the B0 pool + the **same** shortlist as B1 × all orders × declared two-group splits (K4: 1+3, 2+2, 3+1; K5: 2+3, 3+2) | p11 if m ≤ 3, else max H | chunked at the chosen split |
| B4 | beam (width 6) of prefixes; local hypotheses (top 6, ≤ 2 per object set); recursive retarget + insert (thresholds 0.5 / 0.9 / +0.10; depth ≤ 2; ≤ 32 temporary probes, ≤ 64 temporary readouts; cycle guard); final ranking over dependency-respecting orders × declared splits | p11 if m ≤ 3, else H | chunked at the chosen split |

- **Chunk score:** `log H = log max(1e-8, Y_global(E)) + Σ_j log max(1e-8, pX(c_j | S_{j−1}))`, with Y_global from the original root's Y-only view and pX the **marginal** at each rebased prefix scene.
- **Selection:**
  - NOOP if p_noop(S0) ≥ 0.5.
  - Otherwise admit candidates with score ≥ 0.3: p11 for m ≤ 3, exp(H) for m > 3, a declared heuristic threshold that is not calibrated.
  - Then argmin (−log score, length, displacement, signature). If nothing is admitted: ABSTAIN.
- **Caps per root × arm:**

  | Item | Cap |
  |---|---|
  | unique ordered X readouts | 100,000 |
  | unique endpoint readouts | 100,000 |
  | wall time | 180 s (cap stops are logged; B0 never truncated) |
  | GPU inference, total | ≤ 2 GPU-h |

## Physical evaluation (P4)

- **Jobs:**
  - One job per unique (root, ordered sequence, boundary set). A Y endpoint is shared within a root.
  - The order is fixed: root id, then arm. Primary jobs are capped at 100.
  - NOOP uses the root's certified initial label (y = 0 from generation); ABSTAIN is no success.
- **Teacher and adapter:** the unchanged teacher via `evaluate_k45.run_xb` (continuous = `fin3d.run_x` semantics; chunked = a q_ref connector at every group end) plus `run_y`.
  - Independent replay runs on every X = Y = 1.
  - No retries; UNKNOWN stays UNKNOWN.
  - Evaluation caps: 200 jobs and 12 worker CPU-h in total, including the 2 smoke jobs already used. Up to 16 workers.
- **Oracle diagnostic (after the seal):** in fixed priority order
  1. direct-p11 top-1 (continuous), chunk-H top-1 (chunked) and a seeded random order (continuous);
  2. the mode control, chunk-picked order run continuously;
  3. the witness order with a canonical split [2, m].

  The oracle stage is trimmed by this priority and the roster order, never by outcome.

## Outcomes and interpretation

- **Strict outcomes:** SUCCESS (X = Y = 1 decided), FAIL_Y, FAIL_X, UNKNOWN; NOOP and ABSTAIN as above. Replayed success is reported separately.
- **Reported per arm and per witnessed length:**
  - all-root lower bound S/N with the exact binomial interval;
  - decided-only rate S/(S+F);
  - upper bound (S+U)/N.
- **Pairs:** B3 vs B1 and B4 vs B2, with wins / losses / ties / unknown and exact McNemar on discordant pairs. These are exploratory, with no superiority claim.
- **Decision labels:** COMPOSITION_WITNESSED, RETARGETING_WITNESSED, ORDERING_ONLY_WITNESSED, DIRECT_ONLY_WITNESSED, NO_COMPOSITION_ESTABLISHED, as defined in plan §8. Every claim is prefixed by the witness-length limitation (`WITNESS_LEN_k_MIN_UNKNOWN`). If more than 20 % of a comparison is UNKNOWN, it is flagged inconclusive.

## Deviations (declared)

- **Cohort construction** is route-direct blockers plus enabling chain obstacles (P0 deviation 1).
- **Minimum K** is not certified.
- **3D figures** are geometric block drawings, not simulator renders.
