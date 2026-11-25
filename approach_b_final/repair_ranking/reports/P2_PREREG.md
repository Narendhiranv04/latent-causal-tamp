# P2 pre-registration: inference-only fixes to the frozen scorer

Registered before any rule is fitted. The P1 diagnostics are committed (`a786a5b5d1`).

## Fixed for every variant

- **Models and pools:**
  - Same frozen cVAE (D4/D6 exact prefix).
  - Same frozen scorers; s0 for everything except F5.
  - Same K_max = 2 grammar.
  - Every order of every set is scored.
- **Gate and admission are not variables in P2.**
  - The NOOP gate (p_noop ≥ 0.5) and admission (raw s0 p11 ≥ 0.3, including the empty row, exactly as `search_sets.choose`) stay frozen.
  - Variants change only the **ranking** of admitted candidates, or (F4) which admitted candidate replaces the anchor.
  - K0/NONE decisions are therefore identical to F0 by construction. This is checked, not assumed.
- **Fitting data:** DEV_CAL K1/K2 known candidates with decided logical Z, from exact-contract caches only (89 roots with both a Z+ and a Z−). DEV_AUDIT is evaluated **once**, after the rule is frozen.
- **Features (public only):**
  - `s = log p11`.
  - Max rank tier of the set under the frozen marginal.
  - `off` = fraction of off-D4 actions.
  - `prior` = mean log normalized cVAE probability of the set's actions.

## Variants

| ID | Rule (utility; higher is better) | Grid, chosen on DEV_CAL |
|---|---|---|
| F0 | `s` (the frozen rule) | none |
| F1 | Platt map of logit p11 (monotone; ranking identical to F0) | none; calibration reported only |
| F2 | logistic `Z ~ β·logit(p11) + γ_tier`, β > 0 | L2 strength C ∈ {0.01, 0.1, 1, 10} by 5-fold family CV log loss |
| F3a | `s + λ·prior` | λ ∈ {0, 0.05, 0.1, 0.25, 0.5} |
| F3b | `s − λ·off` | λ ∈ {0, 0.05, 0.1, 0.25, 0.5} |
| F4 | anchored replacement (below) | δ ∈ {0, 0.02, 0.05, 0.1} |
| F5 | mean p11 over s0/s1/s2, minus λ·sd | λ ∈ {0, 0.5, 1}; 3× scorer cost |
| F6 | not run | P1 found only 7 gate errors among 240 K1/K2 roots, so no gate or length change is justified |

**F2 tier structure, fixed now from label counts only.** The DEV_CAL decided counts are:

| Tier | Z+ / Z− |
|---|---|
| T4 | 738 / 365 |
| T56 | 94 / 20 |
| R7_12 | 125 / 35 |
| TAIL | 263 / 128 |

T56 has fewer than 30 negatives, so it is merged with R7_12. The resulting tiers are **T4 / R5_12 / TAIL**, with T4 as the reference.

**F4 anchored replacement:**
- The anchor is the F0 choice within the EXACT4 pool (gate and admission frozen).
- An off-D4 candidate from the wider pool (D6 or D12) replaces the anchor only if its F1-calibrated probability exceeds the anchor's by more than δ.
- If the anchor is ABSTAIN, the best admitted off-D4 candidate is taken. If the anchor is NOOP, it stays NOOP.

**F5 handling:** if F5 wins, it is reported as a diagnostic comparator with 3× network cost. It is not adopted by default.

## Metrics

**DEV_CAL drives selection; DEV_AUDIT is evaluated once.**
- **Known-candidate metrics:**
  - Within-root concordance between Z+ and Z− (ties 0.5), averaged over roots.
  - Top-1 among the known decided candidates.
  - The rate of verified failures among top-1 picks with a calibrated probability ≥ 0.9.
- **End-to-end with cached labels**, for the EXACT4, EXACT6 and EXACT12 pools:
  - Decided success.
  - Unresolved picks: an uncached pick is unresolved, never a failure.
  - Intention-to-treat bounds.
  - Rescues and harms against F0.
  - Equality of K0/NONE decisions.

## Selection and promotion rule (at most one finalist F*)

1. **Within each family:** choose λ / C / δ on DEV_CAL by highest concordance. For F4 this is end-to-end decided success on the EXACT6 pool, since F4 has no utility.
2. **Across families (F2, F3a, F3b, F5):** highest DEV_CAL concordance, then lower high-confidence FP rate, then the simpler rule.
3. **Promotion requires all of the following:**
   - The DEV_CAL paired concordance difference vs F0 has a family-bootstrap 95 % lower bound > 0.
   - Known top-1 is not below F0 on DEV_CAL.
   - EXACT4-pool decided success is no worse than F0 − 3 pp.
   - K0/NONE decisions are unchanged.
4. **F4 qualifies** only if its DEV_CAL EXACT6-pool decided success exceeds F0's, with rescues > harms.
5. **DEV_AUDIT is reported once and can veto.** A veto applies if the point concordance difference vs F0 is < 0, or known top-1 drops by more than 3 pp. A vetoed rule is reported, not retuned.
6. **If nothing qualifies:** no P2 finalist; F0 stays.

## Interpretation limits

- The labelled candidates are selection-biased, which P1 documented. A tier penalty fitted on them may suppress valid tail repairs.
- No result here is physical evidence for unlabelled picks.
