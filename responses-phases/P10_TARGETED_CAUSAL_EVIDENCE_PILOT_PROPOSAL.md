# P10 proposal — targeted causal-evidence pilot for the frozen 2D joint Boltzmann learner

**Status: DESIGN ONLY — REQUESTED, NOT AUTHORIZED.** Nothing here has been run. No teacher, IK or planner query and no new label was produced while writing it. Every outcome named below is the *question* to be decided by the existing physical teacher, never a presumed answer.

**Why this phase.** P8 / P9 established a mathematically exact, invariant learner (report 0035, `P9_2D_FREEZE_DECISION.md`), but the saved data cannot test the relations it is meant to learn:
- **κ = +1:** no proof-grounded complementarity (both P8c test +1 roots rest on a place-side BUDGET_INFEASIBLE label).
- **Order:** no independently decided same-endpoint order pair in the fresh P8c data.
- **Omission:** no omission-only labels in validation or test.
- **z0–zS pair:** unidentifiable — no root has scene edits *and* a feasible original.
- **G+M:** its constructor-aligned advantage is unresolved (9/12 vs learned ≤ 8/12 in P8d).
- **Appearance:** its value relative to geometry is unclear; the visual-zero control (0036) is mixed.
- **Validation:** 12 roots, with 3 roots carrying most of the likelihood.

P10 should produce **a small number of decisive, independently witnessed or certified contrasts** — not a larger benchmark.

## 1. Fixed setting (unchanged)

- **Robot and world:**
  - 2D fixed-base 3R arm (finite links, housings, palm and fingers, attached carried object, joint limits) and the 48-grasp family;
  - SAFE_RETREAT required after the target;
  - 8×8 support grid, 0.08 m pitch; discs of radius 0.024 m with 0.005 m clearance.
- **Teacher:** OPNEG-v1 policy (`teacher_opneg.toml`, `sha256:df54878d…`) for operational negatives.
- **Certificates:** pick-side sector certificate `LINK0_SECTOR_PICK_V1`. The place-side certificate is **not** available (open item A7), so place-side negatives remain operational.
- **Status values never merged:** VERIFIED (witness), CERTIFIED (sound, scoped), BUDGET_INFEASIBLE (policy-relative), UNKNOWN, NOT_RUN. UNKNOWN / NOT_RUN are missing, never 0.
- **Learner inputs only:**
  - initial scene geometry, q0, goal, and frozen DINOv2 object features (or the visual-zero control);
  - proposed ordered moves and destinations;
  - hypothetical pose edits.
- **No IK / planner screening in model scoring.** The planner is used only for training labels and for executing the single committed choice.

## 2. Causal questions, mechanisms and exact teacher questions (in priority order)

Notation: target T, obstacles A, B, C, robot base at the grid edge, cells `c(row, col)`.

The sketches are *intended mechanisms*:
- a constructor proposes cells;
- static screens and the teacher decide.

Cells shown are placeholders for the constructor search, **not** asserted outcomes.

### Q1 — Proof-grounded complementarity, κ = +1 (F3 + F5)

**Mechanism.**
- Every grasp of T that the 3R arm can reach lies in one approach sector.
- A and B each occlude part of that sector, so removing either alone leaves every feasible grasp blocked; removing both opens it.
- The blocking is on the **pick side**, so the single-edit negatives can be *certified* by `LINK0_SECTOR_PICK_V1`, not merely budget-limited.

```
 row 5 . . . . . .        base ▲ at the bottom edge; reachable grasp sector of T faces down-left
 row 4 . . A T . .        A occludes the left half of the sector, B the lower half
 row 3 . . . B . .        hypothesis: z0 = 0, zS[A] = 0, zS[B] = 0, zS[A+B] = 1   (to be decided)
        c2 c3 c4 c5
```

**Teacher questions (fixed robot q0, target-only):**
- `scene:{root}:A→a`, `scene:{root}:B→b`, `scene:{root}:A→a.B→b`, `seq:{root}:empty`;
- plus the physical repairs (A→a, B→b), (B→b, A→a) and their omissions (A→a), (B→b).

**Decisive only if** all four scene outcomes are decided with the negatives CERTIFIED (pick-side) and the positive VERIFIED.

**Predictions:**
- the F3 scene unaries alone (independent marginals) can reproduce κ only via `p_AB − p_A − p_B + p_0`; they carry no joint dependence;
- B-structured has no generic scene–scene coupling;
- B-full / C-full have it;
- SF has independent heads.

**If unconstructible** (no pick-side configuration yields certified single-edit negatives): report `+1 UNCONSTRUCTIBLE_PROOF_GROUNDED`. Complementarity then stays policy-relative, and nothing is fabricated.

### Q2 — Redundancy (κ = −1) and nuisance (κ = 0) controls (F3)

**Mechanism:**
- **κ = −1:** A and B both occlude the same narrow grasp sector, so either removal opens it.
- **κ = 0:** a nuisance object C far from every reachable grasp and from the swept arm.
- The same root family as Q1 is used, so κ signs are not confounded with constructor family.

**Decisive if** all four outcomes are decided for each root.

### Q3 — Same-endpoint opposite order from the same q0 (F2; B prefix vs C GRU)

**Mechanism.** Identical final arrangement, different action order:
- A's only reachable grasp is occluded by B, so `A then B` fails at A's pick and its negative is certified;
- `B then A` frees A's grasp;
- B's destination does not interfere with A's pick or carry.

```
 row 4 . . T . .
 row 3 . B A . .      A's reachable grasp approaches from the left, through B's cell
 row 2 . . . . .      r1 = (A→a, B→b): expected pick-side certified NEGATIVE at step 1 (to be decided)
        c1 c2 c3      r2 = (B→b, A→a): needs a complete relocation + target + SAFE_RETREAT witness
```

**Decisive only if:**
- one order is VERIFIED and the other order is CERTIFIED with an order-scoped proof (pick-side at the blocked step);
- both orders start from the same q0 and reach the same final object poses.

A BUDGET_INFEASIBLE order counts as a **policy-relative** contrast and is reported separately.

**Predictions:**
- an order-invariant scorer (C-order-invariant / B-no-prefix) cannot separate the two orders;
- the B prefix-pair and the C GRU can.

### Q4 — Omission necessity and unnecessary moves (F4)

**Mechanism.** Repair r = (A→a, B→b) is witnessed. Its omissions are independently evaluated from S0:
- r∖B = (A→a) is expected to succeed (B's move was unnecessary);
- r∖A = (B→b) is expected to fail (A is necessary; certified pick-side if possible).

**Teacher questions:** the full repair and each single-action omission as **new independent queries** (never inferred from r's trajectory).

**Decisive:** r VERIFIED, plus at least one omission decided each way.

**Predictions:**
- the F4 zR–zO pair is the only factor that couples r with r∖t;
- removing it makes omission predictions independent of r.

**Selection test:** a correct model admits the shorter (A→a) and does not commit the unnecessary 2-move repair.

### Q5 — Originally feasible controls with scene edits (identifies z0–zS; false-empty)

**Mechanism.**
- T is reachable in S0 (`z0` expected 1, needing a witness).
- A *harmful* hypothetical edit moves an obstacle into the grasp sector (`zS[A]` expected 0); a *neutral* edit moves a far object.
- Repair catalogue: the empty repair plus a few unnecessary repairs.

**Decisive:** `z0` VERIFIED with at least one decided edit. This is the **only** data type that identifies the structured `z0–zS` pair, which is unidentifiable in all saved data.

**Selection test:** commit the empty repair, never an unnecessary move. Count false-empty on obstructed roots and unnecessary work on feasible ones.

### Q6 — Alternative destinations (F2 / F1 / J)

- **Mechanism:** the same mover with destination d1 (inside T's approach corridor or the arm's carry sweep) vs d2 (clear).
- **Contrast:** both destinations decided, with relocation-witness travel J recorded for the feasible one(s).
- **Also:** a travel-inversion pair (small displacement, longer joint travel) if constructible.

### Q7 — Static-invalid endpoints (F1)

- Off-workspace, unsupported and overlapping endpoints, labelled by the **existing analytic static checks**: no teacher, no planner, not used for ranking beyond the existing certificate precedence.
- Purpose: confirm F1 vs analytic screens (is the neural static head redundant?).

### Q8 — Constructor-disjoint family (G+M alignment)

- **Mechanism:** obstructions that pose-only screens cannot see:
  - swept-volume or carry-path conflicts;
  - link-body collisions far from T (link-0 / elbow sweep);
  - goal-side placement conflicts with no pick-side signature.
- **Constructor:** a new constructor that never calls the G+M pose screens. Its roots form the **blind holdout** (§4).
- **Question:** does G+M's 9/12 advantage persist when obstruction is not pose-visible?

### Q9 — Appearance vs geometry (visual features)

- **Mechanism:** identical geometry, altered nuisance appearance (render colours or textures of non-target objects; masks unchanged), and held-out appearance at test.
- **Labels:** physics is unchanged, so labels are identical by construction. **No new teacher query is needed** for the appearance variants; they reuse the geometric root's labels.
- **Measures:** prediction shift under nuisance appearance, compared between the full-vision and visual-zero models.

### Q10 — Fixed-robot intervention vs actual sequential execution (F3 vs F2)

- **Mechanism:** `zS[A]` (hypothetical teleport of A) is expected feasible, while the physical repair (A→a) fails because A cannot be carried to a (carry sweep through B or a link collision).
- **Decisive:** `zS[A]` VERIFIED and (A→a) CERTIFIED or BUDGET (reported separately).
- **Prediction:** a model that equates scene edits with repairs will over-predict (A→a).

## 3. Root plan, label provenance and ground-truth rules

**Freeze before any query:**
- constructor code and seeds;
- root list with reference-root lineage, splits and families;
- per-root query catalogue, in an outcome-blind priority order (essential contrast first, cheapest-first within a root);
- teacher policy hash.

**Quota per mechanism** (pilot stage, §6): ≥ 2 reference roots per Q1–Q5, Q8 and Q10; Q6, Q7 and Q9 are attached to those roots.

**Label provenance in every table:** VERIFIED / CERTIFIED (scope) / BUDGET_INFEASIBLE (policy) / UNKNOWN / NOT_RUN.
- κ, order and omission contrasts are reported **only** when every component is decided, and are split into proof-grounded vs policy-relative.

**No fabricated negatives.** A constructor's intent is never a label.

## 4. Splits, baselines, ablations, evaluation

**Splits by reference root** (descendants stay together):
- train;
- validation (**≥ 24 roots**, so that 3 roots cannot dominate);
- **blind holdout**: the constructor-disjoint family Q8 plus ≥ 2 roots per other mechanism, untouched by any report until frozen predictions exist.

**Arms (frozen checkpoints and calibration; deployed lexicographic selector; static-certificate precedence):**
- G+M (geometry + full motion; strong baseline);
- uniform;
- A, SF;
- frozen 2D model (`ABC9U_UNIQUE_V1`) at its pinned checkpoint;
- `ABC9K_KEYED_V1` as a diagnostic;
- B-structured, B-none, C-full;
- visual-zero B-full;
- optional G+M + learned re-ranker (separately declared).

**Factor ablations** (retrain-without-factor; same data, batches and updates; 3 seeds):
- F5 generic coupling (full → structured);
- F5 higher order (full → quadratic);
- F3 structured pair (→ none);
- F4 zR–zO pair (remove `pair_omit`);
- F2 order (prefix / GRU → order-invariant);
- F1 neural static → analytic screen;
- vision (visual-zero).

**Predicted differences per question:**

| ablation | Q1 κ = +1 | Q2 κ signs | Q3 order | Q4 omission | Q5 z0–zS | Q6 destination | Q10 edit vs repair |
|---|---|---|---|---|---|---|---|
| − F5 generic coupling | loses joint +1 | — | — | weaker omission coupling | — | — | weaker scene → repair transfer |
| − F5 higher order | partial | — | — | partial | — | — | partial |
| − F3 structured pair | — | — | — | — | **cannot fit** | — | — |
| − F4 zR–zO pair | — | — | — | **independent omissions** | — | — | — |
| − F2 order | — | — | **cannot separate** | — | — | — | — |
| visual-zero | — | — | — | — | — | — | — (Q9 appearance-robust) |

"—" means no specific prediction; any change is reported as found.

**Two evaluations, kept separate:**
1. **Offline prediction** on decided labels: own-joint exact root NLL, calibrated marginals, κ by sign and provenance, order-pair accuracy, omission-necessity accuracy, false-empty, root-cluster CIs.
2. **One-shot executed evaluation** on the blind holdout (P8d protocol):
   - top-5, relocation planning before commit, one target attempt with SAFE_RETREAT;
   - all model and planner CPU charged;
   - paired by root against G+M.

## 5. Decision rules and what failure means

- **A factor is retained only if** its removal degrades a predeclared validation endpoint of the matching question, with a root-cluster CI excluding 0. Otherwise it is demoted. A factor's existence is never evidence.
- **Q1 complementarity:** if +1 is unconstructible with certified negatives, complementarity remains **policy-relative**, and F5's claimed value for κ is limited to operational evidence.
- **Q3 order:** if no certified order contrast exists, the order hypothesis remains **UNTESTED**, regardless of GRU or prefix accuracy on random permutations.
- **Execution:** if learned arms do not beat G+M on the blind constructor-disjoint holdout, report **no executed advantage**. If they beat G+M only on the disjoint family, report that residual niche precisely.

## 6. Staged budget — REQUESTED, NOT AUTHORIZED

Reference costs from P8c: 450 queries, 8,893 teacher CPU-s (≈ 20 CPU-s per query, ≈ 247 per root), 19 % NOT_RUN; P8d: 72 episodes in 2,245 CPU-s.

| stage | content | queries | teacher CPU-s | stop rule |
|---|---|---|---|---|
| P10a constructibility | 14 reference roots (2 × Q1, Q2, Q3, Q4, Q5, Q8, Q10), ≤ 16 queries each, two waves of 7 | ≤ 224 | ≤ 5,000 | after wave 1: stop and redesign constructors if < 50 % of the planned decisive contrasts are decided, or 0 certified negatives for Q1 / Q3 |
| P10b pilot set | 54 roots (train 24 / validation 24 incl. Q9 appearance variants / blind 6 + the Q8 family) | ≤ 800 | ≤ 16,000 | per-wave gate on decided-contrast yield and NOT_RUN ≤ 25 % |
| P10c learning | frozen 2D model + ablation arms, 3 seeds, saved labels only | 0 | 0 teacher; ≤ 6,000 learner CPU-s | — |
| P10d one-shot execution | blind roots × {G+M, U, A, SF, frozen B, ablated B}, ≤ 5 candidates | 0 labels | ≤ 4,000 (episodes) | per-episode 180 CPU-s guard |

Totals requested for a future decision: ≤ 21,000 teacher CPU-s, ≤ 6,000 learner CPU-s, ≤ 4,000 execution CPU-s. One worker; process-tree guards; append-only ledger.

## 7. Appendix — transfer of the same learner to 3D (roadmap only; nothing implemented)

**Same model:**
- the conditional binary outcome graph: z0, fixed-robot scene edits zS[I], ordered repairs zR, independently evaluated omissions zO;
- the same five families (F1 static, F2 ordered sequence, F3 scene intervention, F4 omission, F5 coupling) and travel J;
- the exact root likelihood with physically keyed or unique factor instances;
- the same three-term objective;
- the same deployed selector and one-shot protocol.

**What changes is the observation encoder and the teacher.**

1. **Observations.**
   - RGB-D (single or multi-view), instance masks or tracklets, and per-object point clouds and poses.
   - Frozen DINOv2 patch features pooled per mask (as in 2D) remain the default appearance channel.
   - Slot Attention is an *optional* object discovery front end when masks are unavailable. It is evaluated against supplied masks, never assumed.
2. **Object tokens.**
   - 6-DoF pose, extent or shape descriptors (bounding box, point features), support relations and region or shelf membership;
   - robot q0 and kinematic features;
   - target and goal.
   - Observed state and privileged state are separated exactly as in 2D (no privileged swept volumes or outcomes in the encoder).
3. **Scene edits (F3):** hypothetical pose edits of tracked objects with fixed robot q0; the edit encoder uses pose deltas as in `edit_proj`.
4. **Repairs (F2 / F4):** ordered high-level pick-place actions with 3D destinations from a finite, support-aware catalogue; ideal-prefix tokens recomputed per order; omissions rebuilt from S0.
5. **Teacher (labels only):**
   - a 3D motion planner, grasp sampler and verifier;
   - sound certificates where available, with operational negatives under a pinned policy;
   - executed only for training labels and for the single committed one-shot action;
   - never for learned scoring.
6. **Validation first:** the P10 question set (complementarity, order, omission, feasible controls, constructor-disjoint, appearance) is re-instantiated in 3D *before* any benchmark scaling.

**Not implemented here:** 3D sensors, perception, teacher and simulator code. A separate authorization is required for each.
