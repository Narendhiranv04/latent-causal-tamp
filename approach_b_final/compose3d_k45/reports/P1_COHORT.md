# P1: sealed K4/K5 3D cohort

**Status:** 10 K4 + 10 K5 roots admitted and sealed **before any learned inference** (`P1_COHORT_SEAL.json`).
- Public rows sha256 `5d1cfc5d…`; private index sha256 `be7ca339…`.
- Public rows are kept private, as plan §4 asks; only their hash and aggregate counts are committed.
- Figure: `figures/p1_cohort_roster.png` (top-down grid plus a 3D block view of every root, drawn from real cells, sizes and heights).

## Every root is `WITNESS_LEN_k_MIN_UNKNOWN`. None is a certified minimum.

Each admitted root has all four of the following, measured by the unchanged SHELF66V3 teacher (config hash `8d521b1f6d23db23`, the same on gvlab2, gvlab and the laptop):
1. The original target action is infeasible at q_ready. The certification records the negative kind.
2. A physically verified continuous repair of **exactly** length k: X = 1 including the q_ready connector, and Y = 1 at the endpoint. The witness is stored privately.
3. A probe of every (k−1)-subset of that witness, with no verified shorter repair: no subset endpoint gives X = Y = 1.
4. No sound lower bound. The probe in 3 is limited to the witness's own subsets and destinations; route-cover counts are planner-relative.

## Composition

| Stratum | Source | n | Objects |
|---|---|---|---|
| K4 | **fresh** (new route construction, 2 direct blockers + 2 enabling obstacles) | 4 | 5–7 |
| K4 | **historical-unexposed** generator K4 roots: never in any 3D TRAIN/VAL/TEST split or the V3.4 cohort, re-certified with the current teacher | 5 | 5–8 |
| K4 | **derived** from an unexposed historical K3 root + 1 necessary enabler | 1 | 5 |
| K5 | **derived** from a K4 parent + 1 necessary enabler (6 parents are derived K4 roots outside the roster; 4 parents are roster K4 roots) | 10 | 6–9 |

- **Enablers are not redundant.** An enabler is admitted only if all of the following hold:
  - with it present, every feasible grasp azimuth of a needed mover toward its destination is blocked;
  - the enabler itself picks and parks from the original scene;
  - once it is parked, the mover plans again;
  - with everything parked, the target plans.
  - The child is then certified from scratch, including the shorter-subset probe.
  - No distractors are added.
- **Lineage:**
  - The 10 K5 roots have 10 distinct parents.
  - 4 K5 roots share lineage with a K4 roster root (their parent).
  - Derived roots share layout lineage with their parents, and historical roots are not fresh.
  - All of this was authorized by the owner on 2026-11-26 and is disclosed here.

## Generation history and resources (every attempt ledgered; no attempt re-run)

**Owner authorizations:**
- 2026-11-25: 24 CPU-h.
- 2026-11-26 01:25: 60 CPU-h / 36 workers.
- ~02:40: 150 CPU-h plus the laptop, and the historical-K4 and derived-K5 sources.
- 03:00: free the laptop; K5 on gvlab2 and gvlab only.
- 03:05: unlimited CPU-h.

**Amendments**, all before the seal and none using any learned model:

| Amendment | Change |
|---|---|
| A1 | Movers = the generator's first tight set passing `independent()`; enabler parking avoids the target corridor; target-plans check; 2-blocker strata only |
| A2 | Probe only feasible azimuths; the largest generator blocker; 12 candidate cells |
| A3 | Place-side enablers; most constrained alternative parking cell |
| A4 | Historical re-certification; K5 derived from K4 parents |
| A5 | Derivation attempts enumerate blocker × destination |
| A6 | Unexposed K3 → K4 → K5 derivation pipeline |

**Historical K4 re-certification** (Yadu's `raw_k4_ordered`: 9 roots, 7 of them identical to raw/roots):
- 5 pass: srv-w0003-s004, srv3-w0078-s012, srv3-w0101-s007, srvNt-w0009-s012, srvNt-w0013-s010.
- 3 have a verified 3-move repair (omit one witness move and X = Y = 1): lap3-w0051-s013, srv3-w0082-s016, srv3-w0089-s022.
- 1 witness no longer verifies: srv-w0044-s014.
- 1 historical root outside Yadu's set (lap3-w0146-s011) also showed a verified 3-move repair.

**Totals:**

| Item | Value |
|---|---|
| Attempt records | 517 (including censored records) |
| Teacher worker CPU | **62.8 CPU-h** |
| Complete-plan / endpoint teacher jobs | 764 |
| Instrumented planner calls | 240,470 `plan_pick_place` + 148,000 `plan_free_move` |

**Hosts:** gvlab2 (≤ 44 workers), gvlab (19 workers, `/home/nav/k45`) and the laptop (≤ 22 workers; freed at 03:00 on the owner's request). enigma was never used for compute.

**Censored attempts:**
- Every attempt killed for a cap raise, the laptop release or a stuck drain was charged at full wall time and never re-run.
- 8 seeds (b2c2/b2c3 n = 24–31) were marked censored but never actually ran; their charge over-counts.
- The note is in `gen/GEN_NOTES.json` on gvlab2.
