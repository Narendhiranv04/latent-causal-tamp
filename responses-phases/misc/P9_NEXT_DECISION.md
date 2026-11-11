# P9 next-decision memo — the exact joint Boltzmann objective, what it shows, and the L3 factor-ablation plan

**Bottom line.**
- **Engineering:** P9 delivers a genuine, verified joint Boltzmann factor-graph objective for B/C.
  - It is exact and equality-aware: one variable per physical query, `z0 ≡ zR[∅]`, scene evidence charged once per root.
  - It is brute-force verified on 167 saved roots, with all three gates passing.
  - The 7-term P8 loss is replaced by one likelihood plus the two auxiliaries the mathematics requires.
- **Science:** on disclosed legacy splits only, the simpler objective is **not shown to be better** on neutral metrics, and generic coupling helps the joint likelihood fit but **not** any decision-relevant quantity that matters yet.
- **Untested factors:** several factor families cannot be tested at all without new physical evidence.

Evidence: 0028 (L0), 0029 (L1), 0030 (L2). Gates: `runs/p9/P9_L{0,1,2}_GATE.json` = PASS / PASS / PASS. Compute: L2 4,000.9 / 8,000 CPU-s; 0 teacher calls in all of P9.

## Answers

1. **Is it a genuine joint Boltzmann factor-graph objective? Yes (engineering).**
   - B/C outcome probabilities are exact Boltzmann marginals of a normalized root distribution, `P_S · Π_r P_r · 1[copies agree] / Z_eq`.
   - Training maximizes the exact masked observed-data likelihood, summed by exact elimination (peak scope 9 variables).
   - It is not a composite fallback and not independent sigmoid heads.
   - **Properties to state with every claim:**
     - distinct repairs are conditionally independent given the scene bits, except through shared queries;
     - reused queries combine evidence as a product of experts, so root marginals depend on the declared catalogue;
     - static energy and travel are, provably, trained only by their auxiliaries.
2. **Are all five families attached to the right variables? Yes**, by code map, unit tests and measured gradient reach.
   - **F1** static: endpoint descriptors only, **no** z edge.
   - **F2** sequence: `zR`.
   - **F3** scene: `z0`, `zS[I]`, and the `z0–zS` pairs.
   - **F4** omission: `zO` unary and the `zR–zO` pair. The `zO` unary is the F2 scorer applied to `r∖t` (shared parameters).
   - **F5** generic pairs and higher order on every allowed scope.
   - The outcome likelihood never reaches the static or travel heads; finite differences agree for every factor group.
3. **Do they receive meaningful gradients? Mostly.** Mean norms over 200 updates, B-full: generic pairs 6.1, higher order 3.5, sequence 2.8, `zR–zO` pair 2.0, scene unary 0.8.
   - **Exception: the structured `z0–zS` pair** (0.03, sometimes exactly 0). It is **unidentifiable from the saved data**: every root with scene edits has a failing original task, so `z0 = 1` never co-occurs with scene variables.
   - **Shared DINOv2 projection:** it carries the largest gradient in every arm.
4. **Is unified joint training better than the P8 multi-loss?**
   - **Better engineering:**
     - 3 terms instead of 7;
     - each physical label counted once instead of 3.8–5.9 times;
     - equal cost per update, no non-finite losses;
     - **zero** false-feasible empty repairs (P8 B-structured: 3 per seed);
     - much lower exact root NLL on the disclosed test.
   - **Not better science yet:**
     - validation root NLL is equal or slightly worse (B-full +0.055);
     - calibrated test accuracy changes by −4 to +10 points depending on the arm;
     - the coupled arms' κ = +1 predictions disappear once the explicit effect loss is removed. Those predictions were operational-label, loss-driven behaviour, not an emergent joint property.
   - **Verdict:** objective `ENGINEERING_PASS`, scientific advantage **INCONCLUSIVE**.
5. **Does generic coupling add beyond structured factors or independent prediction?**
   - **Joint fit — INCONCLUSIVE-positive.** Root-NLL contrasts favour B-full over B-structured on validation and the disclosed test (−0.37 and −0.81 nats per root), and over SF on validation (−0.56). Scene → repair conditionals become informative (task d 0.21).
   - **Decision-relevant quantities — NOT_SUPPORTED:**
     - SF has the best scene marginals and hidden-scene completion on the test;
     - no arm predicts κ = +1;
     - restricted-catalogue selection is similar across B arms;
     - P8d already found no execution advantage.
6. **Which factors remain unproven and need new physical evidence?**
   - **F3 structured `z0–zS` pair.** It needs roots that are *originally feasible* and also carry scene edits (harmful or nuisance edits).
   - **F2 / C order representation.** P8c has no decided same-endpoint order contrast, and C-full vs B-full is not distinguishable (+0.04 / −0.08 nats).
   - **F5 complementarity.** Both +1 test roots depend on an operational place-side label, so a proof-grounded or witnessed +1 is required.
   - **F4 omission unary as a separate factor.** It is not separable from F2 in code, and omission necessity has no ablation yet.
   - **F1 neural static vs analytic screens** — untested.
   - **Appearance (DINOv2) benefit.** It is used, but no geometry-only arm has been trained.
   - **Originally feasible roots with a repair catalogue** (false-empty and unnecessary-work controls).
   - **Constructor-disjoint families** (the G+M alignment confound) and **any executed advantage**.

## L3 factor-necessity plan (Methodology v1.8 §9, Guide v2.0 Gate L3). Not authorized; no budget is implied

**A. Code prerequisites (no teacher):**
1. A predeclared flag that gives `zO` its **own** unary head (`omit_unary=separate`), so "remove omission unary" is a real ablation.
2. The `vision=False` geometry-only arm.
3. An optional **single-normalizer root energy** variant (each factor instance once, one `Z(z_S)`) as an alternative to the product-of-experts root model, compared on the same data.
4. Longer matched training. The best validation update was the last one in 12 of 21 runs, so a predeclared update budget should be selected on validation.

**B. Data (new, outcome-blind, frozen before any query; split by reference root):**
- **≥ 1 constructor-disjoint family**, i.e. obstruction mechanisms *not* built from the G+M pose screens.
- **Fixture coverage (F0–F13):**

  | fixture | what must be collected |
  |---|---|
  | **F0** | originally feasible targets *with* a repair catalogue and scene edits (identifies `z0–zS`; tests false-empty and unnecessary work) |
  | **F4 / F5 / F6** | A / B / A+B fixed-robot edits with all four outcomes decided, aiming for **proof-grounded or witnessed +1** (requires the place-side certificate, open item A7; otherwise +1 stays policy-relative) |
  | **F7 / F11** | **same-endpoint order swaps from the same q0**, physically verified vs a sound order-scoped negative |
  | **F8** | three- and four-move prefix dependence |
  | **F9** | independently evaluated omissions |
  | **F10** | alternative destinations |
  | **F12** | motion-only failures |
  | **F13** | two first-relocation witnesses with travel inversion |
  | **F1 / F2** | static unary- and pair-invalid endpoints |

- **Missing or unconstructible fixtures are BLOCKED**, never fabricated.

**C. Ablation matrix (retrain-without-factor; ≥ 3 seeds; matched batches, capacity reported):**
- B-full;
- B-quadratic (higher order);
- B-structured (generic coupling);
- B-none (structured pairs);
- B-no-static-unary / B-no-static-pair (vs analytic screens);
- B-no-order / C-order-invariant;
- B-no-scene-unary / B-no-`z0–zS`-pair;
- B-no-omission-unary (needs A.1) / B-no-`zR–zO`-pair;
- C-full, A, SF and geometry-only variants;
- primary metrics: root-cluster CIs of exact root NLL, κ by sign and provenance, order-pair accuracy and the selection funnel.
- **Decision rule:** a factor is kept only if removing it degrades a predeclared held-out endpoint with a root-cluster CI excluding 0. Otherwise it is demoted.

**D. Execution (L4, separately):** paired one-shot G+M vs B/C vs SF vs G+M + joint re-ranker on untouched constructor-disjoint roots, with all model and planner compute charged.

**E. Sizing.** The user must authorize budgets. P8c's 36-root pilot cost 8,893 teacher CPU-s; a comparable F0–F13 pilot (24–36 roots, ≤ 20 queries per root, OPNEG-v1 unchanged) would be of the same order. **No collection budget is requested as granted here.**

**Smallest useful next step (no teacher):** items A.1–A.4 on the same saved data, under a new frozen plan. They decide whether the product-of-experts root model or the single-normalizer variant should carry into L3 *before* any new physical evidence is collected.

**STOP.** No L3 / L4, collection, teacher call, robot episode, 3D or hardware work was started.
