# P7A-R pre-registration: final bounded, offline repair-scoring revision

Branch `naren/kgt3-exec-composition`, from `2497fa1415`. This document is committed **before**:
- any new-root selection output, public root build or P4 candidate run;
- any P7A-R prediction;
- any evaluator run on new roots.

It is the authoritative protocol. Deviations must be disclosed as numbered amendments, committed before the new-root predictions are sealed. The P7A gate (REVISE, `reports/p7/`) is preserved unchanged as the historical negative result.

## 0. Status of evidence

- All P3–P7 DEV roots are **exposed**. Old DEV is used only for debugging (crashes, runtime, invariants), never to tune parameters against static-checker labels.
- All results are **offline static proxies**: a static-valid order is a *necessary screen*, not robot execution (P5B: 1/27 static-valid orders executed physically). UNKNOWN is never a negative.
- **Kill-table "blockers" are post-hoc static-checker contributors**, not proven causal identities. The P7A suspect precision (172/174) is a DEV-exposed, privileged number, not a new-root claim.

## 1. New independent development roots (deterministic; public metadata + evaluator-side K stratum only)

**Pools:** the untouched engineering layout pools copied for P3 (`/home/naren/kgt3_runs/dev_src/lay_e.jsonl`, `lay_g.jsonl`, `lay_fg.jsonl`; SHA-256 recorded at selection).

**Release disjointness:** `scaling2d_k12/G1/GEN_SPEC.md` states that "the engineering pilot roots (`ENG_*`, `ENG2_*`) are excluded from every release". Only `ENG_`/`ENG2_` roots are eligible. DEEP9 (K9) engineering roots carry no such guarantee and are **excluded**, so the cohort is K4–K6 only, which limits scope. release_v2 is never read.

**Filters:**
- `geom == "original"`;
- `n_objects ≤ 20`;
- root id not in DEV;
- lineage (`geom`, `seed`) not shared with any DEV root;
- exact layout signature (cells0, goal_cell, tid) not equal to any DEV layout;
- exact-layout duplicates across pool files are collapsed (first occurrence in the order `lay_e`, `lay_g`, `lay_fg`).

**Selection:**
- Within each lineage, the candidate for stratum K is the root with `K_lb == K` that has the smallest `sha256("P7AR|" + root_id)`.
- Strata are processed in the order K6, K5, K4. Each takes the **8** lineages with the smallest key, and no lineage is used twice. That gives **24 roots**.
- If a stratum has fewer than 8, the shortfall is disclosed; the gate stays unchanged.
- `K_lb` is evaluator-side stratification only and is never given to any planner. `witness_set` is never copied into any public file.

**Public build** (`p7ar_roots.py`): `witness.rec_of` + `contracts.view2d` (scene construction only; **no teacher query**). Outputs:
- public: `roots_public.jsonl` (same schema as `dev_public`);
- private: `roots_private.jsonl` (root, K_lb, layout without `witness_set`).

**Anchor candidates:** the **frozen P4 public pipeline**, unchanged:
- `run_p4.py` arms R2, R3, F, with `p4_config.json` (P4_PROTOCOL_V1 + A1) and the hash-checked bundle;
- sealed by `p4_queue.py` (≤ 6 workers, memory-guarded);
- no teacher, no labels.

**Endpoints per root:** the P6A public rule. The top 2 assignments by stored frozen hY over the union of the sealed R2/R3/F pools, deduplicated by sorted assignment (ties: lower recorded energy C, then signature). ORIG order = the lowest-energy recorded order of the rank-0 endpoint.

## 2. Public geometry (exact)

- **Constants:** pitch p = 0.08 m; robot base b = `inputs.base`.
- **Directions:** for a cell x, u₀ = unit(b − x), and U(x) = { rot(u₀, θ) : θ ∈ {−60°, −30°, 0°, +30°, +60°} }. These are base-facing side-approach directions.
- **Corridor cells:** CC(x, u) = { cells y ≠ x : 0 < (y − x)·u ≤ 2.0p and |(y − x) × u| ≤ 0.75p }, computed once per (cell, direction).
- **Corridor blockers:** for an arrangement c and an excluded set E, B(x, u; c, E) = { objects j ∉ E : c[j] ∈ CC(x, u) }.
- **Access:** a(x; c, E) = max over u ∈ U(x) of exp(−|B(x, u; c, E)|). It equals 1 if any corridor is free.
- **Move access:** acc(c, o, d) = a(c[o]; c, {o}) · a(d; c, {o}).
- **Target access:** accT(c) = a(c[T0]; c, {T0}) · a(G0; c, {T0}).
- **Term:** term(x) = min(Γ, −log x), with Γ = 4.

**Potential** for pending set R: Φ(c, R) = Σ over (o, d) ∈ R of term(acc(c, o, d)) + term(accT(c)).

This proxy is an **imperfect, hand-designed heuristic**. It uses no IK, kill table, collision oracle, teacher or witness.

## 3. Search (FULL-R) — `p7ar_repair.py`

**State:** (plan = executed ordered moves, pending R = the required moves not yet executed). R starts as the anchor assignment.

**Ordinary deletion is disabled.** Every transition respects the grammar:
- the destination is legal, originally empty, not G0, not occupied, and not reserved by a pending destination;
- objects are distinct; the target is never moved;
- len(plan) + |R| ≤ 12 at all times.

**Transition families** (per parent, quotas fixed):

| Family | Definition | Path-cost increment Δg |
|---|---|---|
| EXEC (≤ 12) | execute a pending (o, d) | term(acc(c, o, d)) + λ_Y·(1 − ρ) |
| DEST (1 per pending) | execute pending o at the single best-access legal alternative destination p* (P(o) ranking below) | term(acc(c, o, p*)) + λ_Y·(1 − ρ) |
| ENABLE (6 suspects × 2 placements) | execute enabler e → p directly; only if len(plan) + |R| + 1 ≤ 12 | term(acc(c, e, p)) + λ_e + λ_Y·(1 − ρ) |
| INSERT (6) | add a pending enabler (e → best placement) to R without executing it; only if len(plan) + |R| + 1 ≤ 12. Lets second-level suspects target e's corridors | λ_e (its term enters Φ) |
| SUB (3 enablers × 2 replaced movers) | only when len(plan) + |R| + 1 > 12: **atomically** execute enabler e → p and remove one pending mover r | term(acc(c, e, p)) + λ_e + λ_Y·(1 − ρ) + term(acc(c, r)) + λ_sub + w_TR·TR(r) |

Notes on the families:
- **SUB charges r's current term.** A substitution is never cheaper than executing r, so deleting a hard move cannot produce a cheap short plan. At most one mover is removed per inserted enabler.
- **Replaced-mover candidates:** the 2 pending movers with the lowest TR(r) = term(accT(c)) − term(accT(c without object r)), i.e. the least public blocking of the target's corridors. Ties go by index. What was replaced, and why, is logged.
- **The 3 SUB enablers** are the ENABLE candidates with the largest potential gain −ΔΦ.

**Suspects** (ENABLE, INSERT, SUB):
- Level 1: objects (movable, unused, not pending, not T0) in any B(x, u; c, ·) for x ∈ {sources and destinations of pending moves, c[T0], G0}. Ranked by the number of (x, u) corridors they appear in (descending), then index.
- Level 2: objects in the corridors of level-1 suspects' cells.
- Keep the first k_e = 6.

**Placements** P(e):
- the frozen cVAE S0 top-2 for e, filtered for legality;
- plus the public top-2 legal free cells, ranked by (number of pending/target corridor cell-sets containing the cell, ascending; then distance to the nearest anchor, descending; then index).

**Learned term ρ:** the within-parent percentile rank (ties averaged, in (0, 1]) of the frozen temporary-target ŷ(o → d | Edit(S0, plan)) among all of that parent's move-executing children. It is a relative within-scene signal only, never a gate or a calibrated probability.
- FULL-R: λ_Y = 0.5. FULL-R-GEOM: λ_Y = 0.

**Constants:** λ_e = 0.3, λ_sub = 1.0, w_TR = 1.0.

**Beam:**
- B = 8. States are merged on (set(plan), set(R)), keeping lower (g, repr).
- Order: f = g + Φ(c, R). The difference-of-potential is counted exactly once; nuisance moves (ΔΦ = 0) are strictly penalized by λ_e.
- At most 24 layers.
- Complete when R = ∅ and plan ≠ ∅.

**Final score** for a complete candidate: F = g + term(accT(c_final)) + λ_end·(1 − ρ_end).
- ρ_end is the percentile of the frozen ŷ_end (original-task endpoint Y) among the arm's complete candidates of that root (top 5 per endpoint, pooled over both endpoints).
- FULL-R: λ_end = 1. GEOM: λ_end = 0.

**Root-level commitment:** each arm commits **exactly one** plan per root, the argmin F over its pooled candidates (tie: plan repr). No label is used.

## 4. Arms (same roots, anchors, legal domain, proposer ingredients, cap of 12 moves, budgets)

| Arm | Definition |
|---|---|
| ORIG | rank-0 endpoint, lowest-energy recorded P4 order; no search |
| DEST_ONLY | EXEC + DEST with **3** alternative destinations per pending (to match opportunities); no ENABLE / INSERT / SUB; λ_Y = 0.5, λ_end = 1 |
| **FULL-R** | section 3 |
| FULL-R-GEOM | FULL-R with λ_Y = λ_end = 0 (geometry only; measures the learned contribution) |
| FLAT-STRONG | no pending structure and no dependency suspects; Φ = target term only. Children = every movable unused object e × P(e), keeping the 48 lowest (term(acc(c, e, p)) + ΔΦ_target) per parent. Complete **only when len(plan) = m** (anchor length), so it cannot collapse to a 1-move stop. Same λ_Y, λ_end, final score and caps as FULL-R |
| RANDOM-MATCHED | FULL-R transitions, quotas, length rules and scores, but suspect lists = seeded random k_e movable unused objects, and placements = seeded random legal cells (same counts). Seed = sha256("P7AR\|RANDOM\|root\|state") |

**Shared budget** (per endpoint per arm):
- ≤ 6,000 frozen ŷ_temp calls; ≤ 200 ŷ_end calls; ≤ 3,000,000 corridor-access evaluations; ≤ 24 layers.
- An arm stops at the first exhausted cap and returns its completes. Actual consumption is logged.
- Old P7A FLAT/RANDOM remain reproducible historical records; they are not re-run.

## 5. Funnel accounting (logged per root, endpoint and arm; never used by search)

The stages are:
1. suspect objects;
2. legal enabler actions generated;
3. enabler actions scored (all generated within quota; no global shortlist);
4. enabler actions present in beam survivors;
5. complete candidates containing an enabler;
6. top-5 containing an enabler;
7. committed plan containing an enabler.

The log also records the first stage at which each proposed enabler object disappears.

## 6. Evaluation (`p7ar_eval.py`, run **once**, after predictions are sealed with SHA)

- **Primary (root level):** a committed plan scores 1 iff that exact order passes the P5A static checker (`run_order` = STATIC_VALID: every pick/place live in sequence and the final target live). Each arm gets one plan per root. Paired per-root discordance is reported.
- **Secondary:**
  - static-order existence for the committed assignment;
  - final-target static liveness;
  - top-5 static-valid count (diagnostic);
  - public access gain;
  - frozen ŷ_end;
  - original-mover retention;
  - novel enablers in the committed plan, and object/destination differences;
  - funnel;
  - length and K stratum (evaluator only);
  - density stratum;
  - compute and missingness.
- **Uncertainty:** descriptive only. Any bootstrap is by root.

## 7. Gate (numeric, frozen now)

Let N be the number of cohort roots (target 24).

**PASS** iff FULL-R's paired net (wins − losses) on the primary metric is **≥ 3 against each** of FLAT-STRONG, RANDOM-MATCHED, ORIG and DEST_ONLY, **and** at least **2 distinct roots** have a committed FULL-R plan that contains at least one novel enabling mover (an object not in the selected anchor assignment) **and** is static-valid.

**Otherwise `BLOCKED_FROZEN_KGT3`**, which is final for this line, with no further heuristic revision.

**Learned contribution** (reported, not part of the gate): FULL-R vs FULL-R-GEOM. If GEOM ≥ FULL-R, any success is reported as an **analytical geometry baseline**, not a learned K>3 correction. No arm can be promoted after the results.

**`BLOCKED_NO_NEW_DEV_ROOTS`** applies if fewer than 12 eligible roots exist (not expected; section 1 found 518 eligible lineages).

## 8. Order of operations

1. Commit this pre-registration.
2. Implement `p7ar_repair.py`, `p7ar_roots.py`, `p7ar_eval.py` and the tests. Synthetic fixtures must cover: enabler insertion, enabler needing an enabler, double counting, zero-effect nuisance, new destination blockage, atomic SUB at the cap (no cheap deletion), FLAT-STRONG building K4/K6/K9/K12-length plans, determinism, budgets, funnel and leakage. Debug only on synthetic fixtures and old DEV (crash/runtime only).
3. Freeze the code and config (commit).
4. Select and build the new roots; run the sealed P4 pipeline (commit the root list, its hashes and the seals).
5. Run all arms; seal the predictions (SHA, checkpoint hashes); commit.
6. Run the evaluator **once**; write the report and `P7AR_DECISION.md`; commit and push; **STOP**.

No teacher, training, labels or dataset generation; no release_v2; no edits to checkpoints, budgets or other worktrees; no merge.
