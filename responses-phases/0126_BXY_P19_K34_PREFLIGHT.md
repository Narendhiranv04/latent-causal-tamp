# 0126 — BXY-P19: K3/K4 preflight audit (read-only)

Date: 2026-11-01. Gate: BXY-P19 of the BXY-P19 → P22 contract. Start commit `20121eee`.
- No teacher label and no optimizer step.
- CPU: ≈ 115 CPU-s of audits (+ checkpoint copy) against the 2,000 CPU-s ceiling.
- Wall: ≈ 240 s of compute inside the 3,600 s ceiling.
- Authorization: [AUTHORIZATION_P19.json](../runs/approach_b/bxy_p19_v1/AUTHORIZATION_P19.json).

## Result

**No blocking condition.**
- P17 reproduces exactly.
- All 90 P17 checkpoints are present locally and hash-verify against their RESULT.json files.
- A second hash-verified copy exists outside the repository. **Preservation gap:** that copy is on the same physical disk, and no
  off-machine copy exists.
- The X/Y semantics, the connector to q_ref and the label separation are unchanged.

The audit explains the K3/K4 gap and corrects two P16 / P18 claims.

1. **P16's K_geom overstated necessity.**
   - The new sound certificate `K_cert`: for every set of K−1 movable discs, the real populated-scene screen with that set removed must be
     certified closed (all declared candidates fail definitely) for the target pick or place. By monotonicity it bounds the relocations
     any successful repair needs.
   - Result: K_geom 2 → K_cert 2 in only 16 of 30 roots (11 give 1, 3 give 0); K_geom 3 → K_cert 3 in 7 of 10; K_geom 4 → 4 in 1 of 3.
   - **Neither verified K3 root is certified K3-necessary** (K_cert 2 and 1). Only 5 of the 11 verified K2 roots are certified K2.
   - **Cause:** the P16 union model counts single-disc kills and does not distinguish certified collisions from gray-band /
     non-definite failures, so some "closed" modes are not certifiably closed.
   - The order-free lower bound equals the greedy K_geom in 86 of 87 roots; the greedy removal order raised it in 1.
2. **The dominant physical bottleneck is relocation planning under the fixed budget, not catalogue truncation.**
   - Over 1,100 P16 relocation attempts, success is **0.65** per relocation (382 failures: 333 NO_PLAN_FOUND, 49 certified).
   - Four independent steps therefore succeed at ≈ 0.65⁴ ≈ 0.18 before the target query.
   - Success falls for blockers in columns 6–7 (0.42–0.53), beyond 0.6 m from the base (0.52) and with ≥ 4 neighbours (0.44). It rises
     for short carries < 0.1 m (0.75).
   - First relocations fail most (index 0: 0.62).
   - Intended-repair target failures after a full repair are mostly NO_PLAN_FOUND, not certified.
   - Caps: the 16-candidate / 44-query cap truncated **only controls** (harmful / neutral / pair / corridor) on K_geom ≥ 3 roots, and
     **never** a prefix or omission ([CAP_AUDIT.json](../runs/approach_b/bxy_p19_v1/CAP_AUDIT.json)).
3. **Paired power correction.** P18's "worst-case" 1.96·0.5/√n is the single-proportion bound, not a bound for paired D ∈ {−1, 0, 1}.
   - The P17 D − A paired SD on outcome-blind infeasible roots is **0.287** (disagreement rate 0.25).
   - The simulated 95% half-width is 0.071 at n = 60, 0.062 at 80, 0.056 at 100 and 0.045 at 150.
   - For D − E: SD 0.194, half-width 0.048 at n = 60.
   - So P18's 0.107 was conservative for these arms but is **not a valid bound in general**.

## 1. Reproduction ([REPRODUCTION.json](../runs/approach_b/bxy_p19_v1/REPRODUCTION.json))

- **P17:** `bxy_p17_eval.evaluate()` reproduces EVALUATION_P17.json exactly (accounting excluded).
- **P18 pooled rule, read-only diagnostic:** each arm's single pooled rule applied to the same P17 OOF 3-seed scores on outcome-blind
  roots.

| Arm | fold-specific rule (P17 estimate) | P18 pooled rule on OOF |
|---|---|---|
| D | 0.272 / 0.120 | 0.254 / 0.128 |
| E | 0.224 / 0.094 | 0.246 / 0.103 |
| A | 0.149 / 0.222 | 0.145 / 0.205 |

- **Neither is an estimate of the frozen 15-checkpoint P18 ensemble.** Every ensemble member except the 3 held out in that root's fold
  saw the root (12 of 15).

## 2. Checkpoint custody ([CHECKPOINT_CUSTODY.json](../runs/approach_b/bxy_p19_v1/CHECKPOINT_CUSTODY.json))

- All 90 `best.pt` are present.
- For each, sha256(repo copy) = sha256(backup copy) = the RESULT.json hash.
- Backup: `/home/naren/bxy_checkpoint_backup/p17_v1`.
- **Gap:**
  - The backup is on the same NVMe; `/home` is 98% full.
  - The second disk is unmounted and was not touched.
  - Off-machine custody is recommended before any confirmation.

## 3. K_geom solver audit ([KGEOM_AUDIT.json](../runs/approach_b/bxy_p19_v1/KGEOM_AUDIT.json))

- **What `bxy_p16.k_geom` computes:**
  - an **exact** order-free minimum over the finite declared pick × place mode pairs of the movable discs in their union-model kill sets;
  - then a **greedy** removal-order filter.
- **When is it a sound necessity lower bound?** Only if the union model is exact and the screens' failures are definite. It is a
  **heuristic**, not a certificate, so P20 uses the real-screen `K_cert`.
- **Soundly handled:**
  - fixed discs (a pair touching a fixed disc is excluded);
  - T and the goal occupant;
  - the no-op (K = 0 when a pair is free).
- **Not modelled:**
  - transit and carry motions;
  - the link-0 sector;
  - parking reachability.
- **Counterexamples,** recorded per root:

| Root | K_geom | K_cert | Outcome |
|---|---|---|---|
| wA-s028 | 3 | 1 | verified only at 3 within the catalogue |
| wA-s033 | 4 | 2 | — |
| wA-s034 | 4 | 3 | — |
| three K_geom-2 roots | 2 | 0 | S0 not certified closed |

## 4. Failure phases by mechanism ([PHASE_AUDIT.json](../runs/approach_b/bxy_p19_v1/PHASE_AUDIT.json))

| Mechanism | Roots | Intended repair (X, Y) = (1, 1) | Intended-repair failures |
|---|---|---|---|
| nested K2 | 11 | 1 | 7 relocation NO_PLAN_FOUND, 5 Y NO_PLAN_FOUND |
| mixed K2 | 11 | 4 | 6 Y NO_PLAN_FOUND, 3 relocation |
| pick K2 | 7 | 1 | — |
| mixed K3, pick K3 | 3, 3 | 0, 0 | — |
| nested K3 | 4 | 2 | — |
| nested K4, pick K4 | 2, 1 | 0, 0 | K4 relocations fail at every index (0–3), plus certified target failures |

## 5. Strict order diagnostic ([ORDER_AUDIT.json](../runs/approach_b/bxy_p19_v1/ORDER_AUDIT.json))

- **Pair definition:** true permutations of one action multiset, same endpoint, both F1-admissible, X discordant.
- **Tie threshold** |ΔP(X)| ≤ 1e-8, fixed before computing.
- **Pairs:**
  - outcome-blind: 33 pairs in 25 roots (99 pair × seed), 10 of them certified (7 roots);
  - P-min: 113 pairs (62 roots).

| Arm | outcome-blind all / certified | P-min all / certified |
|---|---|---|
| D | **0.73 / 1.00** | 0.76 / 0.97 |
| C | 0.69 / 1.00 | 0.72 / 0.99 |
| E | 0.69 / 1.00 | 0.74 / 0.99 |
| B | 0.63 / 0.90 | 0.47 / 0.51 |
| G (order-invariant) | 0.50 / 0.50 (all ties, by construction) | 0.50 / 0.50 |

- The historical P17 order metric is unchanged.
- The certified subset is small (10 pairs).

## 6. Methodology extensions, documented as such

- **The October 31 objective:** L_B = L_joint + λ_J L_J.
- **P17 candidate D adds:**
  - **GEO2** — analytic access features: 8 clearances + T's open pick / place modes and goal occupancy in the edited scene; per-action
    pick / place modes in the ideal predecessor scene. These are label-free but share geometry with the generator.
  - **SYM** — κ L_SYM with κ = 1, symmetric within-root edit pairs plus the P14 contrast.
- **D's objective is L_joint + λ_J L_J + κ L_SYM. SYM is not part of the October 31 base specification.** The original is preserved
  as provenance; the P22 addendum will state both.

## 7. K0–K4 requirements-to-evidence matrix ([REQUIREMENTS_MATRIX_K04.json](../runs/approach_b/bxy_p19_v1/REQUIREMENTS_MATRIX_K04.json))

| Item | Evidence at P18 (real teacher witnesses) | Status |
|---|---|---|
| K0 | 18 roots | proven |
| K1 | 13 roots | proven |
| K2 | 11 catalogue-relative, **5 certified-necessary** | proven (catalogue), weak (necessity) |
| K3 | 2 catalogue-relative, **0 certified-necessary** | weak |
| K4 | 0 | **missing** |
| prefixes 1–6 | lengths ≤ 5 labelled; 4–6 sparse | weak |
| strict order twins | 33 outcome-blind pairs, 10 certified | weak for K3 / K4 |
| omissions of K ≥ 2 repairs | 59 labels, 16 differ | partial |
| harmful edits | 12 roots | proven |
| X/Y four cells | 66 / 28 / 68 / 42 roots | proven |
| matched travel | P17 figure 08 | partial |
| independent test | proposal only | not run |

## 8. Frozen P20 plan ([P20_PLAN.json](../runs/approach_b/bxy_p19_v1/P20_PLAN.json)), before any P20 teacher call

- **Namespace and generator:** `bxyg34dev`, BXY_GEN_K34.
- **Construction rules derived from §§1–4:**
  - local blocker pools (Chebyshev ≤ 2 of the source / goal);
  - K3 / K4 as distributed pick + place closure by exact enumeration of the finite mode abstraction;
  - **K_cert = K_intent required** (real screens);
  - each relocation's pick open (≥ 2 modes) with no edge certificate, short-carry parking with ≥ 3 open place modes;
  - after the repair, ≥ 3 / ≥ 3 open target modes and no certificate;
  - arm-comfortable task region;
  - no populated-scene planning, teacher call or witness chasing.
- **Caps:** 24 candidates / 60 queries.
- **Waves:**
  - k1, a 40-slot probe: K4 12, K3 14, K2 4, K1 4, K0 controls 6;
  - k2 and k3 up to 55 slots each, versioned and frozen before their labels.
- **Readiness:**
  - K34_DATA_READY at ≥ 20 verified K3, ≥ 20 verified K4, ≥ 2 mechanisms each, ≥ 10 strict K3/K4 order contrasts, and ≥ 10 harmful and
    ≥ 10 neutral controls;
  - LIMITED at ≥ 12 K3 / ≥ 10 K4;
  - otherwise K4_PHYSICAL_DATA_NOT_ESTABLISHED.
- **P21 endpoints:**
  - unconditional and availability-conditioned repair success;
  - K strata K1–K4;
  - per-family reporting.

## 9. Files

- [bxy_p19_audit.py](../bxy_p19_audit.py), [tests/test_bxy_p19.py](../tests/test_bxy_p19.py).
- `runs/approach_b/bxy_p19_v1/*.json`.
- **Regression:** full suite **710 passed, 1 skipped**; six archived replays exit 0; hash guard clean.

STOP (gate P19).
