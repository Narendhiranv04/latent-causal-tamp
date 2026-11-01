# 0125 — BXY-P18: final method readiness, honest model freeze, V2.1 confirmatory plan (NOT generated)

Date: 2026-11-01. Gate: BXY-P18, the last gate of the BXY-P16 → P18 contract.
- Previous gates: P16 `9d62caae` (0123) and P17 (0124).
- **No teacher query, no training and no cohort generation happened in P18.**

## Go / no-go

**READY_FOR_INDEPENDENT_CONFIRMATION, scoped to K ≤ 2.** All five conditions hold, with the limits stated below.

| Condition | Status | Evidence |
|---|---|---|
| full label-free adapter | ✔ | [bxy_p16_inputs.py](../bxy_p16_inputs.py): reads only scene / goal / q0 = q_ref; exact P-min reproduction (max abs difference 0.0); privileged-mutation invariance; q_ref ≠ q0 refused |
| valid prototype generation | ✔ | BXY_GEN_V21B with per-mechanism development realization rates ([DEVELOPMENT_RATES.json](../runs/approach_b/bxy_p18_v1/DEVELOPMENT_RATES.json)); every attempt and rejection recorded |
| relevant hard-scene coverage | ✔ for K1 / K2; ✘ for K3 / K4 | development: 13 verified K ≥ 2 (11 K2, 2 K3, **0 K4**); plan expects ≈ 84 repairable and ≈ 41 K ≥ 2 roots. **K3 / K4 claims are not testable with this generator** |
| frozen reproducible models + matched controls | ✔ | [FROZEN_MODELS.json](../runs/approach_b/bxy_p18_v1/FROZEN_MODELS.json): six arms × 15 cross-fit checkpoints (sha256 verified on load); one pooled rule per arm; a member reproduces its stored held-out prediction to 0.0 (test) |
| independent plan integrity | ✔ | new namespace `bxyg21confirm`, new seeds, never generated (test); P15 `CONFIRM_PLAN.json` immutable (sha `30fac794…`, test) and superseded; composition from development physics only |

**The frozen decision label is `CANDIDATE_MET_DEVELOPMENT_GATE`, not "final method".**
- **Candidate D:XYQ-GEO-SYM:** in development it met IMPROVES_WITHIN_GUARDRAIL against XYQ-BASE and SUPERIOR_TO_DIRECT against
  DIRECT-GEO.
- **Challenger E:XY-UNC-SA-GEO-SYM:** the coupling is unsupported (P3), so it is the deployment preference unless confirmation shows
  otherwise.
- **Matched baselines:** DIRECT-GEO, and the analytic-access rule as a non-learned reference.

---

## 1. Model freeze ([bxy_p18.py](../bxy_p18.py))

- **What is frozen:** the 15 P17 cross-fit checkpoints of an arm (5 folds × 3 seeds), scored as an ensemble. Per candidate, p (p_succ;
  no-op P(Y0)) and Ĵ are averaged over the 15 members; F1 is applied first, then the arm's rule.
- **The single rule per arm** is `bxy_p17.choose_rule` on the early-stop predictions pooled over all of the arm's folds and seeds, which
  are development data only:

| Arm | no-op gate | α | γ | pooled inner success / unnecessary |
|---|---|---|---|---|
| D XYQ-GEO-SYM (candidate) | 0.7 | 0.0 | 0.05 | 0.336 / 0.074 |
| E XY-UNC-SA-GEO-SYM (challenger) | 0.7 | 0.0 | 0.05 | 0.342 / 0.062 |
| A DIRECT-GEO (matched DIRECT) | 0.5 | 0.1 | 0 | 0.232 / 0.090 |
| C, B, G | as in FROZEN_MODELS.json | | | |

- **Also frozen (hashes in FROZEN_MODELS.json):**
  - the P17 design and evaluation;
  - the input caches;
  - the access maps (P16 + the P17 extra placement maps);
  - the input contract: DINOv2-small rev `ed25f3a3`, 224 px, 16 × 16 grid;
  - the output semantics.
- **Not frozen:** retraining on all development data. No compute was authorized for it in P18, and the cross-fit ensemble is the frozen
  object.
- **Caveat for ensembles on development roots:** each development root was in-sample for 12 of the 15 members, so development numbers
  must come from the out-of-fold P17 evaluation, never from the ensemble.

## 2. V2.1 confirmatory plan ([CONFIRM_PLAN_V21.json](../runs/approach_b/bxy_p18_v1/CONFIRM_PLAN_V21.json), sha `2ab2d565…`) — NOT generated

- **Generator:** `bxyg21confirm`, BXY_GEN_V21B (`bxy_p16.construct` / `validate`, REV["wB"]), new seeds.
- **Size:** **300 construction slots.**
  - Mix: near_closed K0 30%, goal_occupant K1 6%, place K1 6%, mixed K2 22%, nested K2 14%, pick K2 10%, mixed K3 6%, nested K3 6%.
  - The size was chosen as the smallest multiple of 10 that reaches ≥ 60 repairable infeasible roots, ≥ 24 verified K ≥ 2 roots and
    ≥ 40 feasible roots, from V21B development rates only.
- **Expected (development rates; indicative, because per-mechanism n is small):**
  - about 226 accepted roots, 186 initially infeasible, **84 with a verified repair**, **41 verified K ≥ 2**, 40 initially feasible,
    40 roots with harmful-edit contrasts;
  - worst-case paired 95% half-width ≈ **0.107** on the repairable population, ≈ 0.154 on K ≥ 2.
- **Honest power statement.** A true Δ of +0.12 (the development D vs DIRECT gain) is only marginally detectable at half-width 0.107.
  - 300 slots is a minimum, not a guarantee.
  - **K3 / K4 are not powered**: K3 verified only twice in development, K4 never.
- **Construction rules:**
  - a rejected slot is never replaced by a different spec;
  - all attempts and validation rejects are recorded;
  - censored = absent, attempted budget failure = 0;
  - certified vs budget negatives are reported per stratum;
  - each root is its own family; paired family bootstrap, B = 10,000.
- **Stops and custody:**
  - fixed slot count; one collection; one evaluation; no interim look;
  - if realized repairable < 60 or K ≥ 2 < 24, the single analysis still runs and is labelled **UNDERPOWERED**, and no extra wave may be
    added after any test-model look;
  - generated only after FROZEN_MODELS.json and CONFIRM_ANALYSIS.json are committed.

## 3. Frozen one-shot confirmatory analysis ([CONFIRM_ANALYSIS.json](../runs/approach_b/bxy_p18_v1/CONFIRM_ANALYSIS.json))

- **Primary endpoint:** verified corrective-selection success on initially infeasible confirm roots, both availability-conditioned and
  unconditioned. Candidate D is compared with XYQ-BASE, DIRECT-GEO and the uncoupled control E.
  - Two-sided 95% paired family-bootstrap CI.
  - IMPROVES if the CI lower bound is > 0, the point gain ≥ 0.10 and the unnecessary-repair increase ≤ 0.05.
  - Bonferroni 98.3% CIs are reported for the three comparisons.
- **Secondary endpoints:**
  - unnecessary repairs (harmful vs harmless);
  - Y0 / edited-Y AUROC, ECE, Brier;
  - edit sign by transition;
  - order concordance on measured discordant pairs;
  - omission sign;
  - K strata with n;
  - witnessed J on matched successes;
  - catalogue availability;
  - teacher / verification CPU;
  - no-op, shortest, displacement, analytic-access and verify-first references.
- **Corpus shift:** P-min, P15, V2.1-dev and confirm are reported side by side, with zero re-tuning on confirm.

## 4. Implementation-vs-methodology checklist ([COMPLIANCE.json](../runs/approach_b/bxy_p18_v1/COMPLIANCE.json))

| Methodology (2026-10-31) | Status |
|---|---|
| §1.1 ordered relocations, m ≤ 6, achieved state carried | implemented; labelled prefix lengths ≤ 5 (lengths 4–6 weakly covered) |
| §2.1 / 2.2 Y from fixed q_ref in the hypothetical scene; X with connector to q_ref | implemented + evidence (20 connector-phase negatives) |
| §2.3 all four X/Y cells; attempted-0 / unattempted-absent | evidence: cells in 66 / 28 / 68 / 42 V2.1 roots |
| §3.1 F1 analytic only; F2 prefix unary; F3 scene unary; F4 omissions with the same networks; F5 one quadratic coupling | implemented; **F2 order supported** (P5); **F5 benefit unsupported** (P3) |
| §3.2 / 4.2 root-consistent normalization, shared Y; exact marginalization | implemented; microcase and invariance tests |
| §6 exact m / C_d; full-witness J; L_joint + λ_J L_J (auxiliaries separate); F1-first frozen cost rule with abstention | implemented |
| §8.1 minimal boundaries; historical code frozen | new modules only; hash guard clean |
| §8.2 matched uncoupled / quadratic / DIRECT; analytic / shortest / no-op / verify-first references | implemented in P17 |
| §8.2 acceptance 6: coupling must beat uncoupled before claiming value | **tested: not met → no value attributed** |
| §8.2 acceptance 8: independent end-to-end evaluation | **planned only** (this report) |
| §9 no causal claim; budget-relative zeros; catalogue recall separate | honoured in 0123–0125 |

## 5. Scientific results digest (P16 → P17)

1. **The intended problem now exists in data.** 87 outcome-blind development roots:
   - 69 initially infeasible;
   - 13 verified K ≥ 2 (every shorter catalogue candidate failed, and every partial prefix has Y = 0);
   - 23 F1-admissible same-endpoint X-discordant order pairs, 7 with certified failing orders;
   - 12 harmful-edit (1→0) roots;
   - all four X/Y cells;
   - connector-phase X failures;
   - prefix-complete supervision of every m ≥ 2 intended repair;
   - the methodology's worked example (Y = 0, 0, 1 along a verified 3-move repair whose reversed order is certified X = 0).
2. **Edited-scene feasibility and harmful edits are now learnable,** and the no-op over-confidence of P13 / P14 is reduced: harmful-edit
   sign 0.23 → 0.90, edited-Y AUROC 0.68 → 0.94, Y0 AUROC 0.85 → 0.93 (B → D, outcome-blind, out of fold).
3. **Selection improves within the guardrail.** Corrective success on outcome-blind infeasible roots:

   | D vs B | D vs DIRECT-GEO |
   |---|---|
   | 0.272 vs 0.057 | 0.272 vs 0.149 |
   | Δ +0.215 [+0.136, +0.298] | Δ +0.123 [+0.061, +0.189] |

   - Unnecessary repairs: 0.12 vs 0.20 (B) and 0.22 (DIRECT-GEO).
   - On K2 roots: D 0.83, DIRECT 0.36, B 0.06 (n = 12).
   - The same ordering replicates on P-min.
4. **Order matters and F2 uses it:** order concordance 0.71 vs 0.53 for the matched order-invariant control, Δ +0.18 [+0.05, +0.31].
5. **The quadratic X–Y coupling adds no measurable value.**
   - Selection: +0.048, below the frozen 0.10.
   - Joint NLL: not better (+0.11 [−0.17, +0.41]).
   - On P-min: +0.01.
   - **Recommendation:** drop it from deployment unless independent confirmation shows otherwise; keep it as a tested hypothesis.
6. **Main threat to validity:** most of the gain comes from the analytic access features (GEO2).
   - They share geometry with the V2.1 generator.
   - The gains replicate on the independently generated P-min corpus and DIRECT gets the same features, but a generator-geometry shortcut
     cannot be excluded.
   - The confirmatory cohort uses the same generator family, so it **cannot rule this out either**.
   - A follow-up cohort from a geometrically different generator is required before any claim beyond this domain.
7. **Remaining gaps.**
   - About half of the hard development roots have no verified repair in their catalogue (mostly fixed-budget planner failures).
   - D still repairs 12–20% of feasible roots.
   - The pure geometry rule has zero unnecessary repairs at lower success.
   - K3 / K4 coverage is inadequate.

## 6. Figures

| File | Content |
|---|---|
| [visualizations/approach_b/bxy_p18_v1/01_architecture.png](../visualizations/approach_b/bxy_p18_v1/01_architecture.png) | final architecture: custody → label-free inputs + GEO2 → F1–F5 + travel → root-consistent likelihood → frozen selection → independent verification; frozen-model status |
| [visualizations/approach_b/bxy_p18_v1/02_confirm_plan_v21.png](../visualizations/approach_b/bxy_p18_v1/02_confirm_plan_v21.png) | plan composition and expected strata |

The 2D scene stories are in the P16 / P17 figure folders (prefix stories, order twins, harmful vs neutral edits, choice gallery, order-twin
probabilities).

## 7. Custody manifest and hashes ([CUSTODY.json](../runs/approach_b/bxy_p18_v1/CUSTODY.json))

- **Development roots:** P-min 197, P15 28, V2.1 87, with sha256 lists.
- **Excluded:** the 34 exposed P-min test roots; `bxyg2confirm` (P15 plan, never generated, superseded); `bxyg21confirm` (planned only).
- **Confirmatory roots generated:** 0.
- **P18 artifact sha256:**

| Artifact | sha256 |
|---|---|
| FROZEN_MODELS | `5de5d6aeceba…` |
| CONFIRM_PLAN_V21 | `2ab2d5650d68…` |
| CONFIRM_ANALYSIS | `c9c141cec0cd…` |
| DEVELOPMENT_RATES | `2e599d7863a4…` |
| COMPLIANCE | `265f2ca55b78…` |

## 8. Compute-budget request for a separately authorized confirmation (NOT authorized here)

| Item | Estimate |
|---|---|
| construction of 300 slots (V21B validation, ≈ 85 CPU-s / slot from wave C) | ≈ 25,500 CPU-s |
| teacher labelling of ≈ 226 roots (development mean CPU / root per mechanism) | ≈ 24,300 CPU-s |
| one evaluation (15-checkpoint ensembles × 6 arms, inputs, bootstrap) | ≈ 2,000 CPU-s |
| **total** | **≈ 52,000 CPU-s**, 4 workers, ≈ 13,000 s wall; 800 CPU-s per-root cap; P-min per-query budgets unchanged |

## 9. Regression

Recorded in `runs/approach_b/bxy_p18_v1/regression/`:
- full suite: **707 passed, 1 skipped**;
- six archived replays: all exit 0;
- hash guard: clean.

STOP (end of the BXY-P16 → P18 contract). No confirmatory cohort was generated.
