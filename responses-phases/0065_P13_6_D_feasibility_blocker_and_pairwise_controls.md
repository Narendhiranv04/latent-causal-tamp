# 0065 — P13-6: D feasibility, blocker identity and pairwise controls (same lattices, same roots)

**Actual result.**
- **Gate:** `runs/p13/P13_6_GATE.json` → **PASS**.
- **What D was asked:** D was used only for initial feasibility and blocker identification. No destinations, recursion or execution.
- **Exact lattices:** every scene edit in P13 *is* a D parking subset, so on all **119** infeasible originals with complete masks, A / B / C / SF, D, D-pairless and geometry are scored on identical lattices and identical roots.
- **Scoring rule:** a choice with no predicted clearing set is scored as a miss (F1 0), never as an empty blocker set. Counts: A 37, SF 39, C 28, B 23 (of 357 choices each).

## 1. Initial feasibility (166 decided originals; 27 feasible, all in the natural stream)

| model | AUROC | balanced accuracy | NLL | natural only (45; 27 feasible): AUROC / balanced accuracy |
|---|---|---|---|---|
| A | 0.984 | **0.930** | **0.123** | 0.889 / **0.833** |
| D-pairless | 0.982 | 0.926 | 0.142 | 0.862 / 0.806 |
| D (λ_B = 1.0) | 0.983 | 0.908 | 0.132 | 0.874 / 0.787 |
| SF | 0.983 | 0.904 | 0.128 | **0.891** / 0.787 |
| C | 0.979 | 0.893 | 0.138 | 0.866 / 0.796 |
| keyed B | 0.983 | 0.837 | 0.134 | 0.881 / 0.741 |

- **Challenge originals:** all 121 are infeasible, and every model gets them right; at most one false-feasible call (SF).
- **Ranking:** with feasible positives present, the models are statistically indistinguishable on AUROC. B has the lowest balanced accuracy because it calls feasible natural originals infeasible.

## 2. Blocker identity (infeasible originals, union of inclusion-minimal clearing sets; per-root F1 / exact set)

| cohort | N | D | D-pairless | geometry | B | C | A | SF |
|---|---|---|---|---|---|---|---|---|
| all infeasible | 119 | **0.892** / 0.871 | 0.880 / 0.863 | 0.824 / 0.689 | 0.866 / 0.843 | 0.864 / 0.849 | 0.832 / 0.798 | 0.844 / 0.821 |
| proof-grounded | 88 | 0.966 / 0.958 | **0.977** / 0.970 | 0.958 / 0.898 | 0.962 / 0.939 | 0.948 / 0.936 | 0.931 / 0.898 | 0.940 / 0.913 |
| operational | 31 | **0.681** / 0.624 | 0.602 / 0.559 | 0.441 / 0.097 | 0.591 / 0.570 | 0.624 / 0.602 | 0.552 / 0.516 | 0.573 / 0.559 |
| natural infeasible | 13 | **0.650** / 0.615 | 0.487 | 0.487 | 0.376 | 0.462 | 0.385 | 0.342 |

**Paired F1, model − D (all 119):**

| model | difference | 95 % CI | p |
|---|---|---|---|
| B | −0.026 | [−0.069, 0.012] | 0.65 |
| C | −0.028 | — | 0.68 |
| SF | −0.047 | — | 0.23 |
| A | **−0.059** | [−0.099, −0.022] | 0.004 |
| geometry | **−0.068** | [−0.121, −0.017] | 0.002 |
| D-pairless | −0.012 | [−0.047, 0.017] | 0.55 |

**Union is not necessity:** 13 roots have alternative minimal sets, and 26 union members are not necessary. D predicts the union; no necessity claim is made.

## 3. Reading

- **D is the best blocker identifier overall:** +0.059 over A and +0.068 over geometry. It is not distinguishable from keyed B or C.
- **D's advantage is on operational and natural masks;** on proof-grounded masks every model is ≥ 0.93.
- **The D pair term has no demonstrated benefit**, here (+0.012, n.s.) as in P10b and P11. P12's holdout gain (+0.154) did not replicate.
- **Feasibility:** D brings no feasibility advantage over A / SF once feasible originals are present.

**Figure:** `visualizations/p13/P13_D_blockers.png`.
