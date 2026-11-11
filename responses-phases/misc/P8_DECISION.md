# P8 decision memo — which learning approach is useful for diagnosing infeasibility and choosing minimal executable corrections?

**Bottom line.** On fresh 2D roots, **no learned model produced more executed repairs than the non-learned geometry +
full-motion baseline (G+M)**. G+M reached 9 / 12 against 8 for the best learned arm (B-full). That is pilot evidence:
12 roots, no comparison significant. The joint energy model (B-full / B-quadratic / C-full) is the **best
feasibility and interaction predictor**, but that predictive edge does not become planning success. The Boltzmann
**sampler** is not useful at bounded runtime. Carry forward **G+M as the planner**, with **B-full as an optional
diagnostic / re-ranking predictor**, and test the smallest hybrid next.

Evidence: reports 0024 (P8a, historical audit), 0025 (P8b, selection, sampler, G+M), 0026 (P8c, 36-root κ-balanced
collection and fresh training), 0027 (P8d, 72 matched one-shot episodes). Gates: `P8A_ENGINEERING_PASS`,
`P8B_ENGINEERING_PASS`, `P8C_COLLECTION_PASS`, `P8C_TRAINING_PASS`, `P8D_ENGINEERING_PASS`. All budgets held (largest
use: teacher 8,893 / 12,000 CPU-s).

## 1. Does generic B/C coupling help beyond structured factors and feature-matched independent predictors?

**Partly, for prediction only; not for conditional reasoning or execution.**

| endpoint | evidence | verdict |
|---|---|---|
| Unconditional intervention / κ | P8a: B-full beats B-structured in 6 / 6 seed × split pairs (scene NLL −0.21 to −0.38, κ MAE −0.09 to −0.26). Fresh P8c: only coupled arms predict any +1 (0.67 vs ≤ 0.17). | INCONCLUSIVE-positive |
| Repair feasibility (fresh) | B-full 0.882 / AUROC 0.953, C-full 0.886 vs B-structured 0.789, SF 0.838, A 0.825; seed-0 CIs overlap. | INCONCLUSIVE-positive |
| Oracle-revealed conditionals | P8a: the higher-order term breaks consistency (B-quadratic best). Fresh P8c: B-structured best (task a 0.56 vs B-full 0.95). | NOT_SUPPORTED |
| Executed success | B-full vs B-structured 8 vs 7, discordant 2 / 1, p = 1.0. | NOT_SUPPORTED |

**Caveats on the positive results.**
- The κ test denominators are 2 / 3 / 2, and every +1 label is *operational* (place side), never proof-grounded.
- Under SPARSE_AUX (50 % hidden auxiliary labels) the P8a coupling advantage disappeared.
- `P8_GENERIC_COUPLING_VALUE` is therefore **NOT_SUPPORTED** under the contract rule, which requires a material
  root-cluster advantage.

## 2. Is the more complex EBM justified over A, S (SF) and G+M by complete one-shot success under matched resources?

**No.** P8d, 12 fresh sealed roots, every arm with the same 180 CPU-s guard, top 5 and relocation allowance:

| arm | success | discordant vs G+M (learner / G+M) | main failure mode |
|---|---|---|---|
| G+M | **9** | — | 3 censored on planner-heavy roots (all arms failed there) |
| B-full | 8 | 0 / 1 | 3 censored, 1 target failure |
| B-structured | 7 | 0 / 2 | 4 false-feasible **empty** repairs committed |
| U | 7 | — | 3 target failures, extra moves |
| A | 6 | 0 / 3 | 3 censored, 1 abstain, 1 empty repair |
| SF | 4 | 0 / 5 (p = 0.06) | **7 abstentions** (threshold 0.85 needed to suppress false empty repairs) |

- The EBM is the best learned arm, but it beats neither G+M nor uniform (1 / 0 discordant).
- The simpler supervised models fail through **calibration and thresholding**, not motion.
- `P8_PRIMARY_LEARNED_ADVANTAGE`: **NOT_SUPPORTED**.

## 3. Is Boltzmann search useful at bounded runtime?

**No — use deterministic scoring.**
- The G4B kernels satisfy exact detailed balance (error ≤ 1e-15).
- On a realistic 356-state pool, 4,000-step chains remain far from π (TV 0.20–0.21; still 0.10 at 16,000), although they
  do find the top 5.
- Exhaustively scoring the same bounded pool costs ≤ 356 model calls and < 3 CPU-s.
- The predeclared retain rule failed, so P8c / P8d used deterministic bounded-pool ranking. The sampling claim is
  retired at this scale; it matters only if candidate pools become too large to enumerate, which P8 never reached.

## 4. Can least-required displacement be substantiated within a declared finite candidate set?

**Only partially, and only within the restricted catalogue.**
- *What holds.* Minimality is defined against the fewest-move VERIFIED repair in each root's ≤ 20-query teacher catalogue,
  which exists on only 7 / 12 test roots. On those roots G+M was minimal on 7 / 7 successes, B-full on 4 / 6, U on 2 / 6.
  Displacement J is reported per episode (mean over successes: G+M 0.84, B-full 1.06, U 1.18).
- *Unresolved.*
  1. The catalogue is not exhaustive: some arms succeeded on roots where the teacher verified nothing, so a catalogue
     "minimum" can be beaten.
  2. Minimality is over move *count* and analytic displacement for a fixed grasp set (48 grasps) and planner seed.
     Different grasps or paths could realize the same move set with less travel, and no global optimum over grasps or
     paths is certified.
  3. BUDGET_INFEASIBLE, UNKNOWN and NOT_RUN (19 % of P8c queries) are **operational** negatives, not proofs.
     Only CERTIFIED labels are proof-grounded infeasibility.

## 5. Which single architecture carries forward to further 2D evaluation, and what would falsify it?

**G+M as the planner of record**, plus **B-full (or B-quadratic) as a scoring module only**: re-rank G+M's admitted top
5 and veto false-feasible repairs. B-full never committed an empty repair on fresh roots; B-structured, A and SF did.
No standalone learned planner is carried forward.

**Falsification.** On a fresh, matched, sealed one-shot set, if G+M + B-full re-ranking does not exceed G+M alone in
paired success, or minimal-repair rate, at equal CPU, with the root-cluster lower bound above 0, the learned component
is dropped and G+M alone is the 2D baseline.

## 6. Simplest supported baseline and the smallest next experiment

- **Simplest supported baseline: G+M**, with no learning. Caveat: its pose screens share a family with the P7 / P8 root
  constructors, so its advantage may partly reflect constructor alignment; motion-planner failures remain invisible to
  it, as shown on p7_2026102402 in P8b.
- **Negative evidence.** Kept separate as certified (proof) versus operational (budget, unknown, not run). Every
  original task in the test set is CERTIFIED_INFEASIBLE; all +1 κ labels are operational.
- **Smallest next experiment** (not authorized here; no new 48-root collection):
  - re-use the 12 sealed P8c test roots plus the 6 validation roots;
  - compare G+M vs G+M + B-full re-ranking vs B-full alone, at equal CPU with a 180 CPU-s guard;
  - add a second, independent constructor family to remove the alignment confound;
  - cost: about 3 arms × 18 roots = 54 episodes, ≤ 10,000 CPU-s, no teacher calls except for the new family.

**Hard STOP.** No G5/G6, 3D, hardware, teacher-policy change or further collection is begun.
