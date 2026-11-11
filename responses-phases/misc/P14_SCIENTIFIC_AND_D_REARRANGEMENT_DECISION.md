# P14 — scientific repair of P13 and the D-guided rearrangement sidecar: decision

**Overall: PARTIAL.** The P13 corrections and the B diagnosis are complete (exploratory). The D sidecar works as engineering, but the D3 pilot ran out of budget after 6 common roots. The fresh repair cohort was **not launched**: a powered design exceeds the authorized teacher cap.

## A. Approach B: what is learned, what is corrected (B track only)

**Errata (0067), all from frozen P13 artifacts:**
- **J contrast:** corrected to **J − no-J = +0.019** (teacher-labelled choice correctness, not execution). The historical travel regret was oracle-filtered.
- **Execution ledger:** reconciled. The final ledgers hold 428 episodes with 301 SUCCESS; 0064's 295 predates the worker-2 continuation. Per-arm success is reproduced exactly (B 0.734).
- **F3:** sign-test reversal (40 / 22 roots), but the mean CI crosses 0 (−0.022 [−0.064, 0.015]), so there is no established mean harm.
- **F5:** the tested ablation is the **combined generic + HO block**; there is no generic-only claim.
- **Training compute:** a **bounded estimate** of 33,222 CPU-s (upper bound 33,624), not an exact measurement.

**Diagnosis (0068, exploratory):**
- **B's P13 execution advantages come mostly from admission (coverage).**
  - At historical thresholds, success when it attempts is similar for every arm: B 0.879, A 0.900, F4-off 0.868, F5-off 0.895, SF 0.918.
  - At **validation-coverage-matched** admission, with all 77 counterfactual choices physically executed, B **ties** A (0.000), C (0.000), F3pm (−0.013), F4-off (−0.003) and F5-off (−0.010).
  - Only **order information (F2: +0.067, p 0.011)** and **B over factorized SF (+0.083, p 0.014)** survive matching.
- **Natural-mix failure:**
  - **Probabilistic, not ranking:** AUROC is 0.86–0.89 for every model.
  - B under-predicts feasibility: feasible-original recall **0.70** (A 0.89, D 0.85); mean P(feasible) on feasible originals 0.68.
  - B's joint likelihood is poor on the all-feasible pattern (2.34 nats vs 1.13 for B-F5spm).
  - B picks the empty repair on only **54 %** of feasible originals.
- **Keying is kept as the correctness reference.** Unkeyed B changes predictions by up to 0.25 when a modelled omission query is also listed as a candidate; keyed B by < 1e-11.

**Lean-B factor verdicts** (all exploratory; P13 roots reused, nothing reclassified as confirmation):

| component | verdict |
|---|---|
| order representation (F2 / GRU) | **keep** (the only factor whose benefit survives matched admission) |
| keyed physical-query ontology | **keep** (correctness / invariance) |
| DINOv2 | keep (0063; not re-tested) |
| F3 scene pair | no demonstrated benefit → drop |
| F4 omission pair | no benefit at matched coverage → drop or re-test |
| combined generic + HO coupling (F5) | no executed benefit at matched coverage; challenge NLL gain with natural harm → **re-test generic-only with a calibrated, natural-mix-trained model** |
| learned F1 | not identified → drop (keep the analytic veto) |
| J | +0.019 choice correctness, shorter travel on 12 comparable roots (n.s.) → optional tie-break |
| admission thresholds | must be calibrated (finer grid / coverage-matched); the coarse P8 grid caused most of the P13 differences |

**Repair cohort:** NOT LAUNCHED (`P14_COHORT_GATE.json`). A powered natural-like test (~45 feasible originals) plus training additions needs ~160 new roots × ~265 teacher CPU-s ≈ **43 k**, above the 18 k cap. Within the cap (~68 roots, ~18 feasible originals in test), the primary feasible-recall endpoint is underpowered.

## B. D sidecar: what is searched, what is learned (D track only)

**Learned:** D, frozen and unchanged, predicts original feasibility and the union of minimal clearing-set members.
- **Feasibility-gated blocker F1 (all 146 decided roots):** 0.903, vs D-pairless 0.881 and geometry 0.719.
- **Temporary-target use** (an obstacle as target) **fails its physical probe:** agreement 0.457; "feasible" given a VERIFIED probe 0.21.

**Searched, not learned:**
- **Evidence:** 6,032 real witnessed relocations (150 / 150 replay-certified) → 4,838-entry index (P13 blind roots excluded).
- **Index structure:** 278 absolute (source, destination) keys, 805 motion modes, 344 independently supported modes.
- **Coverage:** 60.1 % of the candidate pairs on evaluation roots.
- **Reuse rule:** hard fixed-base filter (absolute cells only) plus a certified transit and the exact certifier in the current scene.
- **Search:** finite lexicographic (moves, travel); target verified by the planner; independent replay.

**D3 pilot (6 common roots):**

| method | success |
|---|---|
| D-guided | 4 / 6 |
| D-pairless | 3 / 6 |
| geometry | 3 / 6 |
| uninformed | 3 / 6 |
| oracle | 3 / 6 |

- D − geometry is +0.167 (1 / 0 roots, p = 1.0), so **no established D advantage**.
- Identical plans wherever a depth was enumerated exhaustively.
- ~50 % of verified relocations needed online fallback.
- Lookup-vs-online and local / global ablations are not established (budget).

**Novelty discipline:** retrieval, local descriptors and trajectory reuse are established methods. The only contribution under test, D's blocker guidance, shows **no measurable advantage** in this pilot.

## Next scientifically defensible experiments (no 3D port)

1. **Calibrated lean B on a natural-mix distribution.** Order representation + keyed ontology + DINOv2 + scene unary + **generic-only** coupling, against no-coupling. Trained with ~50 % feasible originals; temperature / bias calibrated on validation; coverage-matched admission. Needs ~45 k teacher, ~7 k training and ~10 k execution CPU-s, with explicit authorization.
2. **D-guided search pilot at adequate budget.** The same frozen protocol on ≥ 24 roots (≈ 25 k execution CPU-s at the measured cost), plus a library densification pass on DEV roots to raise coverage above 60 %.
3. **Train D with arbitrary targets** only if recursive guidance is to be pursued; the current model does not transfer.
