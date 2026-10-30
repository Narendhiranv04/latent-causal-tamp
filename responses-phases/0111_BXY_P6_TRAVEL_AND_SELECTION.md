# 0111 — Approach B X/Y, Phase 6: travel-aware selection (validation only)

**Verdict: PARTIAL.** The travel regression and the cost/risk rule are implemented and tuned on validation only. Two limits apply:
- **Travel source:** the travel supervision is the legacy witness travel (no connector; target from the achieved state), not the matched J of methodology §6.1.
- **X/Y selection is degenerate:** see 0110 §C.

## A. Implementation (`bxy_run.py`)

- **Travel loss:** ℒ_J = Huber(log1p Ĵ_θ(r), log1p J(w)), over successful complete candidates that have a recorded witness travel (616 in training).
  - There is no fabricated travel for failures.
  - **λ_J = 1.0** was chosen by validation joint NLL (0110 §A). The noJ arm uses λ_J = 0.
- **Rule** (methodology §6.3):
  1. Admit a candidate when p_succ ≥ η. The zero-move candidate is always scored.
  2. Choose argmin C(r) = −log p_succ + α m(r) + β C_d(r) + γ Ĵ(r).
     - C_d is the summed Euclidean displacement in cell units (L = 0.08 m).
     - Ties break by catalogue order.
  3. Abstain if nothing is admitted.
- **Grid:** η ∈ {0, .05, .1, .2, .3, .5}, α ∈ {0, .25, .5, 1}, β ∈ {0, .1, .25}, γ ∈ {0, .25, .5, 1}.
  - γ = 0 for LB and noJ, since their travel heads are untrained.
- **Criterion:** validation selection success, then fewer moves, then less displacement.
- **Outcome of a choice:** the recorded full-execution check of the chosen candidate (B y; the original y for the zero-move candidate). It is never an input to a score.

## B. Frozen rules (`runs/approach_b/bxy/FROZEN.json`, frozen before any test read)

| Model | η, α, β, γ | Val success | Val mean moves |
|---|---|---|---|
| LB s0 / s1 / s2 | 0,0,0,0 / 0,0,0,0 / 0.5,0,0,0 | 0.667 / 0.714 / 0.762 | 0.33 / 1.00 / 1.00 |
| XY-uncoupled s0–s2 | 0,0,0,0 | 0.524 (= no-op) | 0 |
| XY-quadratic s0–s2 | 0,0,0,0 | 0.524 (= no-op) | 0 |
| XY-quadratic-noJ s0–s2 | 0,0,0,0 | 0.524 (= no-op) | 0 |

Every X/Y model selects the zero-move candidate on every validation root, because p_succ ≈ 0 for all non-empty repairs. The travel term therefore cannot change any selection. Its effect is unmeasurable here, and it is not claimed as a benefit or a harm.
