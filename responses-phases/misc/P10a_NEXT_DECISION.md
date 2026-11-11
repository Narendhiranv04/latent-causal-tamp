# P10a — next decision (per mechanism) and a bounded P10b request

This is **not** a claim that scientific validation is complete. P10a is an adaptive constructibility pilot with 2 roots per mechanism. Every pre-registered primary endpoint is UNDERPOWERED. Nothing beyond P10a was run.

## 1. Decision per physical mechanism

| H | decision | evidence (P10a) | blocker / required change |
|---|---|---|---|
| H1 complementarity (κ = +1) | **GO** | 2 / 2 roots proof-grounded κ = +1: A-edit sector certificate, B-edit TARGET_PICK, empty TARGET_PICK, A+B witness | none for construction; models fail it (κ̂ ≤ 0.43) |
| H2 redundancy / neutral | **GO** | κ = −1 (root 02) and κ = 0 (root 09), both proof-grounded | one UNKNOWN (`A B` hit SEARCH_LIMIT at 82 CPU-s under the 120 cap) |
| H3 order swap | **GO** | 2 / 2 pairs `B A` VERIFIED / `A B` ORDER_FIRST_ACTION-certified, same endpoints and q0 | none for construction; no arm discriminates (margins < 0.02) |
| H4 omission necessity | **GO (add harder cases)** | 2 roots, 4 proof-grounded omissions (necessity and redundancy) | every arm is correct (ceiling). Add omissions whose necessity depends on order or sweep, not only grasp occlusion |
| H5 feasible original + edits | **GO** | 2 / 2 originals VERIFIED, harmful edit CERTIFIED, neutral edit VERIFIED | `Y X` UNKNOWN on both roots: created by the P10a seed-admission rule, not by the planner (§3) |
| H7 edit vs executable | **REVISE_CONSTRUCTORS** | edit and physical relocation both VERIFIED on both roots: observed difference 0, mechanism not realized | three enclosure designs gave 0 / 38 certified M-relocation failures. Needs a mover that is analytically unpickable (for example a sector-blocked mover outside the start sweep, certified with `LINK0_SECTOR_PICK` on the first action). Never a place-side certificate |
| H8 constructor-disjoint obstruction | **REVISE_CONSTRUCTORS** | the angle-only constructor left the original task feasible (empty repair VERIFIED, 16 / 16 VERIFIED) | an obstruction must be realized without pose screens. Proposal: a carry-sweep blocker at an angle chosen from the goal-carry arc, confirmed only by the teacher. Keep it labelled constructor-disjoint, not certificate-targeted |
| H6 destination / J, H9 appearance | not attempted (no extra quota, per contract) | — | attach in P10b where compatible |

**Overall:** 5 / 7 mechanisms GO and 2 REVISE_CONSTRUCTORS. Nothing is BLOCKED or STOP.

**What P10a says about the models.** No model shows the A / B / C hypotheses on these mechanism geometries:
- H1: no arm predicts κ = +1.
- H3: no arm separates the opposite orders.
- Calibration: keyed B / C are worse calibrated than A / SF. On per-root NLL, B − A is +0.56 [+0.10, +1.08] and B − SF is +0.53 [+0.07, +1.05].

The training data (P4–P8c) contains no sweep-barrier, enclosure-order or H8-type geometry. This is first a **coverage** problem, and must not be read as a refutation of joint inference.

## 2. P10b request (proposed; NOT run; needs your approval)

**Scope.** Freeze the GO constructors (H1–H5) and the revised H7 / H8 constructors. The revisions are developed on development seeds only and reported. Then generate roots **without** looking at teacher labels:

| split | roots |
|---|---|
| train | 24 |
| validation | 24 |
| sealed blind (≥ 2 per mechanism) | 14 |
| **total** | **62 independent roots** |

Splits are root-disjoint and lineage-closed. Construction is constructor-disjoint where possible. The certificate-targeted constructors use only static checkers, never teacher labels, so the generator can be frozen before any blind label.

**Cost observed in P10a:**

| item | cost |
|---|---|
| teacher per root (incl. static admission) | ≈ 42 CPU-s |
| teacher per query | median 4.1 CPU-s |
| queries per root | ≈ 8 |
| construction per root, once constructors are fixed | ≈ 1.6 CPU-s |

**Estimate for 62 roots:**

| item | estimate |
|---|---|
| queries | ≈ 500 (cap 800, within the older forecast) |
| teacher CPU-s | ≈ 2,600 |
| requested cap (allows harder H4 / H7 / H8 roots and revised-constructor retries) | **6,000 CPU-s** |
| construction | ≤ 1,500 CPU-s |
| learner (P10c, a separate approval) | not included |

This is far below the older 16,000 CPU-s forecast.

**Power** (from P10a per-root paired NLL contrasts; SD ≈ 0.96 for B − A and B − SF; two-sided 80 %):
- detecting a 0.5-nat per-root difference needs ≈ 29 independent roots;
- detecting 0.25 nats needs ≈ 115 roots;
- for C − K-B (SD ≈ 0.44), 0.25 nats needs ≈ 25 roots.

So 62 roots can power a **pooled** NLL contrast at about 0.5 nats. They **cannot** power per-mechanism H1 / H3 inference: 2 blind roots per mechanism stays UNDERPOWERED by the ≥ 5-root rule. Powered per-mechanism claims need about 15–20 blind roots per mechanism, roughly 110–140 roots in total. Please decide whether to:
- (a) accept pooled-only confirmatory claims at 62 roots, or
- (b) budget about 120 roots, with teacher ≈ 5,000 and cap 10,000 CPU-s.

## 3. Protocol fixes to decide before P10b

1. **Seed admission under the 120 CPU-s / query cap.** The P10a rule (seed guard 100, later seed only while `spent + 110 ≤ 120`) turned 2 clean-but-slow-ish queries (`Y X`, 11–12 CPU-s over two seeds) into UNKNOWN. Two options:
   - a **35 CPU-s seed guard** (3 × 35 + 10 ≤ 120): all three seeds fit, but long SEARCH_LIMIT seeds (82–200 s) become censored → UNKNOWN;
   - keep the current rule and accept a few cap-induced UNKNOWNs.

   Neither option touches BUDGET semantics.
2. **H4 ceiling:** add order- or sweep-dependent omissions so that the omission endpoint can discriminate.
3. **P10c (training on P10b train labels)** needs a separate approval. Joint vs factorized can only be compared fairly once the training data covers these mechanisms.

## 4. Not authorized and not done

- P10b, P10c, P10d and P10e;
- any new dataset beyond the 14 P10a roots;
- training on P10a labels;
- robot or execution episodes;
- 3D.

The P10a labels must never be used as a blind test for models trained afterwards: they are adaptive and disclosed.
