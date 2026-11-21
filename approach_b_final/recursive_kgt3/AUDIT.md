# Recursive K>3: methodology and code audit (first pass)

**Verdict: REVISE.** Every component the method needs exists and reproduces exactly. Three findings change the design, though:
- The existing retarget path breaks the immutable original task.
- A full K≤3 enumeration is far too slow to sit inside a recursion at 25–28 objects.
- **Nothing yet shows that the frozen model gives any usable signal toward the *original* target when K > 3.** Every proper prefix of a minimum-K plan has original Y = 0, so this is the central scientific risk.

With amendments A1–A14 (plan.md, "Amendments and why"), P0–P2 can start. P3 is **CONDITIONAL** on a DEV diagnostic of whether the learned signal is informative. Nothing here has been run on TEST.

Contents:
1. What was examined
2. Component and interface map
3. Mathematical semantics
4. Recursion: algorithm and worked K6/K12 examples
5. Combinatorial cost and budget
6. Risk register
7. File-change plan
8. Gates, no-leakage protocol, test and ablation schedule
9. Adversarial second review
10. Answers to plan §4 Q1–Q15
11. Claim ledger
12. Verdict, implementation order, commands run

---

## 1. What was examined

| Item | Finding |
|---|---|
| Main checkout | branch `approach-d-v1` @ `daf8a04601`, 212 untracked/modified files. **Not touched.** |
| Pinned dataset commit | `e07354b3c8344954c05e3b5ddf499436d855a550` (`naren/scaling2d-k12-test`, equal to origin) |
| New work branch | `naren/kgt3-recursive` from that commit, local only, **not pushed**. Worktree `.claude/worktrees/kgt3`. It is a **non-cone sparse checkout**: `approach_b_final/*.py`, `scaling2d_k12/*.py`, `G1/G1_LONG_TEACHER.md` and `G7/release_v2/public/` only. **No private file, witness, G4/G5/G7 jsonl or GIF exists in this worktree.** |
| Code identity | `placement.py`, `search.py`, `xy.py`, `construct.py`, `contracts.py`, `exhaustive.py` are **byte-identical** (same git blob) at the dataset commit, at the V3.4 benchmark (`c72eb1ef75`) and at post-ablation (`e9fa587c3b`). There is no divergent "corrected" copy to merge. |
| Retarget code | `validation_k3/retarget.py` and `ttarget.py` exist **only** on `naren/k3-postablation-validation` (not an ancestor of the dataset commit), so they must be ported narrowly. |
| Frozen bundle | `~/abf_v34/approach_b_bundle`. **All 10 files match `BUNDLE_MANIFEST.json` SHA-256:** 2D/3D sampler, scorers s0–s2, scalers. 2D sampler `a01f25eb…`, 2D scorer s0 `0fa126da…`. Config: M=4, propose_top=6, n_z=64, S1, proposal_seed 0, K_max 3, chunk 8192, noop_gate 0.5, eta 0.3, α=β=γ=0. **No checkpoint blocker.** |
| Public release | 23 roots; `PUBLIC_MANIFEST` SHA-256 23/23 OK. Objects per root: 16×3, 17×4, 18×6, 19×2, 20×2, 25×3, 27×1, 28×2. Every root: 8×8, all 64 cells legal, one `t0`, `fixed_ids` empty, every non-target object `movable`, identical `q0`, goal never occupied. **No label, K, witness or sequence fields** (key scan). |
| Historical fixtures (DEV) | `~/abf_v34/parity/public_val_2d.jsonl` (751 VAL roots) and `pred_val_2d_gpu.jsonl` (frozen predictions; recorded parity 751/751, max \|Δp11\| 3.6e-7) |
| Environment | laptop RTX 5060 (7.5 GB), torch 2.9.1+cu128. **`/home` has 336 MB free**; see R-M11. |

## 2. Component and interface map (actual call graph)

```text
public raw root (release_v2/public/roots/*.json)
 └─ contracts.view2d(rec)                         contracts.py:L67-80  -> inputs {ids, tid, attrs[r,is_t,is_obs,is_fixed], xy0, cells0, goal, goal_cell,
                                                                           cell_xy, legal_cells, ctx[sin q0, cos q0, goal xy, gap], base, q_ref}
 └─ search.Root(row,'2d')                         search.py:L28-52     movable = i≠tid & !fixed;  legal_dests = legal − occupied − OCC0 − goal (L45-47)
 └─ exhaustive.proposals(root, samp, seed=0)      exhaustive.py:L196   gen = torch.Generator(dev).manual_seed(0) per root; propose_many(M=6)
     └─ search.Sampler.propose_many               search.py:L67-89     per mover: placement.scene_features (L40-59, MAXOBJ['2d']=20 -> IndexError >20)
                                                                       + placement.task_features (L457-479: goal/target one-hot, offsets, ctx)
         └─ placement.propose_rule 'S1'           placement.py:L426-445  z~N(0,I) [B,64,8]; marginal = mean_z softmax(masked dec); top-M, no Gumbel
 └─ exhaustive.score_root(root,D6,scorer,[RULE],mmax=4,chunk=8192)
     ├─ p_noop = Scorer.score(root,[[]])          exhaustive.py:L108   = py[y0]
     ├─ stream(D6,4): k=1..3, combinations × product(top-4) × permutations, distinct destinations (exhaustive.py:L35-45; construct.assignments)
     ├─ Scorer.score -> XY.make_view(y_edits=[], x_seqs) -> collate -> XYNet.predict   search.py:L116-135
     └─ Selectors: pool p11≥eta, cost −log p11; finish: p_noop≥0.5 NOOP; p_noop≥0.3 & better NOOP; else best | ABSTAIN  exhaustive.py:L61-96
 └─ benchmark.predict  (one-shot frozen K≤3 decision)  benchmark.py:L119-145
Verification (post-commit only): scaling2d_k12.teacher_long.x_query/y_query (≤6 → frozen bxy_teacher; 7-12 → LongPhysics) teacher_long.py:L96-110
```

**Existing pieces to reuse unchanged:** `search.Root`, `search.Sampler.propose_many`, `search.Scorer`, `xy.make_view`/`collate`/`XYNet.predict`, `exhaustive.stream`/`Selectors`, `construct.counts`, `benchmark.load_bundle`/`predict` (the B0 control), and `teacher_long` (evaluator only).

**Missing adapters**, all new and all in `recursive_kgt3/`:

| # | Adapter | What it does |
|---|---|---|
| a | `DynPad` | `scene_features` allocates `max(MAXOBJ, n)` rows (verified, §6 R-M1) |
| b | `TaskView` | A temporary-target view of the learner input that **keeps the original target immovable and the original goal illegal** (R-C1) |
| c | `HypoRoot` | A `search.Root`-compatible object for an intermediate hypothetical scene S_p (rebased `xy0`/`cells0`), carrying a global reservation mask (original target, original goal, already-planned movers, cells occupied in S0) |
| d | `score_Y_endpoint(S0, r)` | `make_view(y_edits=[edit(r)], x_seqs=[])` on the **original** root |
| e | `score_X_chunk(S_p, c)` | Marginal `px` for a ≤3 chunk in the HypoRoot under the original task view |
| f | Budgeted local generator | Replaces the unbounded inner enumeration (R-C3) |

## 3. Mathematical semantics (verified in code and numerically)

From `xy.py:L59-63` (`marginals`) and `L352-357` (`predict`), for X node q with parent Y node `par(q)`:
- `py[s] = σ(b_s/τ)`: the learned P(Y=1) for endpoint node s.
- `p1 = σ((a_q+w_q)/τ)` = P(X=1 | Y=1), and `p0 = σ(a_q/τ)` = P(X=1 | Y=0).
- **`px[q] = py[par]·p1 + (1−py[par])·p0`: the marginal P(X=1), which is returned.**
- **`psucc[q] = py[par]·p1 = p11`, the joint, which is returned.** The conditional `p1` is **not** returned; recover it as `psucc/py[par]`.
- `p_noop = py[y0]`.

`Scorer.score` returns `p11 = psucc`, `py = py[par]` and `px` = marginal (search.py:L132-133). The frozen decision uses **only p11** (exhaustive.py:L61-96).

Check C5 on 24 VAL REPAIR roots: p11 equals the scorer output with max \|Δ\| = 0.0. On chosen (feasible) candidates the marginal px and the conditional differ by −0.007 on average.

**Definitions used by the proposed planner:**
- **Local hypothesis score** for task τ (original or temporary) in hypothetical scene S_p, for a chunk u with |u| ≤ 3: `p11_τ(u | S_p)` = `psucc` of the HypoRoot(S_p) view under τ. A heuristic.
- **Stage X:** `h_X(c_j) = px_{τ0}(c_j | S_{j−1})`, the **marginal** px of chunk c_j in HypoRoot(S_{j−1}) under the *original* task view. The X label is "relocations with carried state **plus a connector to q_ref**" (teacher2d.py:L4-5; bxy_teacher L225-239), and training roots always start at q_ref. So `h_X` estimates "this chunk from q_ref, then back to q_ref". The true chained execution starts from the carried robot state. **Σ −log h_X is a ranking energy, not a probability.**
- **Original final Y:** `h_Y(r) = py[node of y_edits=[Edit(S0,r)]]` on the **original root S0**, with no X sequence. Check C3: on 24 VAL roots with ≤3 edits, Y-only equals the X-path py and `Scorer.score`'s py with **max \|Δ\| = 0.0**.
  - **A rebased root (S0 := E) is not equivalent:** \|p_noop(rebased) − py(E \| S0)\| has **mean 0.651, max 0.985**. Example: 0.909 vs 0.061.
  - The reason is the edit-history channels `moved, dx, dy, |d|, x0`, the moved-token mean `mv`, and `moved_count/3` (xy.py:L258-265).
- **Temporary-task Y:** `ŷ_A = p_noop` of TaskView(S_p, target A, goal d_A) means "A could reach d_A now". It has AUROC 0.69 and ECE 0.19 in 2D (TASK_RETARGET_REPORT C3b), so it is **only a priority signal**. It is never multiplied into h_Y.
- **Composition energy (plan §2.5):** `C(r) = −log max(ε, h_Y(r)) + λ_X Σ_j −log max(ε, h_X(c_j)) + λ_m|r|`, with canonical contiguous chunks of 3 starting at action 1. λ_J = 0, because the travel head is unfitted (`lam` = 0 in every arm; the bundle loads no cost model).
- **Physically verified:** only X = 1 and Y = 1 from `teacher_long` after the prediction file is sealed. Everything above is a neural heuristic.

## 4. Recursion: how it chooses what to repair, and worked examples

**Which pending action gets repaired, without a blocker classifier.** For each action a = (A, d_A) of a local hypothesis, in its pre-scene S_p, the planner asks the frozen model one task-level question through a retargeted view: Y of the temporary task "A → d_A". This is the frozen Y head on a different target. It is not a step-failure model, it receives no teacher feedback, and it is miscalibrated.
- If ŷ_A < θ_tt, the action is *suspected* blocked, and a recursive solve for the temporary task produces enabling chunks to insert before a.
- Because ŷ_A is weak, a fixed **diversity fallback** also recurses on the lowest-ŷ actions, even above θ_tt, within the branch budget.
- **Iterative loop:** after a chunk is composed, if the original-task Y is still low and capacity remains, the same task is re-solved from the edited scene.

```text
solve(S, τ, reserved, cap, depth):            # -> enabling sequences s (global order) with Ŷ_τ(S ⊕ s) high, within budget
  if Ŷ_τ(S) ≥ θ_done: return [[]]                         # τ0: Y-only on S0 history; temporary τ: TaskView p_noop
  if depth > D_max or cap == 0 or budget exhausted: return []
  H = local(S, τ, reserved, min(3,cap))                  # frozen cVAE top-4 + frozen D p11, budgeted (A4), fair over first movers
  for u in H[:B_loc]:
     for s in expand(S, u, reserved ∪ {obj(τ)}, cap, depth):
        if Ŷ_τ(S ⊕ s) ≥ θ_done: yield s
        elif |s| < cap: for t in solve(S ⊕ s, τ, reserved ∪ movers(s), cap−|s|, depth+1): yield s ⊕ t
expand(S, u, reserved, cap, depth):
  res = [[]]
  for a=(A,d_A) in u:                                    # insertion sites = every action of u (≤3), bounded beam B_exp
     for p in res:
        if ŷ_A(S ⊕ p) ≥ θ_tt and not fallback(a): keep p ⊕ [a]
        else: for e in solve(S ⊕ p, (A,d_A), reserved ∪ movers(u) ∪ {T0}, room, depth+1): keep p ⊕ e ⊕ [a]
  return dedup(res)[:B_exp]
global legality at every compose: each object ≤ once; T0 never a mover; d ∉ OCC0 ∪ {G0}; d free at its time; |r| ≤ 12; acyclic by construction
dedup key: (root_id, ordered prefix, current cells, moved mask, pending task chain) -- never endpoint-only
rank complete candidates by C(r); commit one decision (§2.6 + A8)
```

**Worked K6 chain** (synthetic objects; certified witnesses not consulted):
- T is pick-blocked by B and C and goal-blocked by D. B is blocked by E, E by H, and D by F. A valid order is H, E, B, C, F, D.
- solve(τ0) gives u = [B, C, D]. In expand(B), ŷ_B is low, so solve((B,b)) gives [E]. In expand(E), ŷ_E is low, so solve((E,e)) gives [H], and B's prefix becomes [H, E]. C passes. D is low, so solve gives [F].
- **Result: [H, E, B, C, F, D]**, using 4 local hypothesis calls and 15 Y probes in the mock.

**Worked K12 chain:**
- T is pick-blocked by A, B, C and goal-blocked by L. A needs D and E; D needs G. B needs F; F needs H and I. C needs J; J needs K.
- First level u = [A, B, C], which expands to [G, D, E, A, H, I, F, B, K, J, C] (11 moves).
- Original Y is still low, so the **iterative loop** (cap 1) adds [L]. **12 moves; nesting depth 3; 8 local calls.**

`mock_recursion.py` implements this exact pseudocode against a symbolic world with a **perfect** mock Y:

| Case | Result | Local calls |
|---|---|---|
| K6 | SOLVED, H E B C F D | 4 |
| K12 | SOLVED, G D E A H I F B K J C L | 8 |
| K12 with the enabler K hidden from proposals | **NO_CANDIDATE** | **185** (failure is ~23× costlier than success) |
| K12 with cap 11 | NO_CANDIDATE | 72 |
| Same endpoint, wrong order | identical final Y (1, 1); stage X correct-order True, wrong-order False | – |

**What the mock does *not* show:** that the real frozen model ranks true blockers into the local beam. In K>3 scenes the original-task p11 of every ≤3-move hypothesis is close to 0. Synthetic 28-object check C4 gives py 1.5e-4 to 5.6e-4 for 1–3 moves. So first-level choices rest on differences between tiny scores (R-C2). This is the main recall bottleneck. The search can discover a K12 chain **only if** every one of about 8 local calls surfaces the needed object, e.g. 0.8⁸ ≈ 0.17 if they were independent.

## 5. Combinatorial cost and budget (measured)

- **Frozen K≤3 path:** every permutation of top-4 destinations for K = 1..3, with no cap (`B_cap` unused). Count = `construct.counts` = K1 + K2 + K3.
- **Synthetic 25/27/28-object scenes** (VAL root plus extra discs; DynPad), with 24/26/27 movers: **K≤3 candidates 510,580 / 698,362 / 676,472** (K3 = 502,812 / 689,052 / 666,876).
- **VAL 751 throughput** on the laptop GPU, including Python overhead: median **20.6k candidates/s** (n_scored median 27,110, max 238,334; score time median 1.23 s, max 12.2 s).
- **So one full local K≤3 enumeration at 28 objects takes ≈ 33 s.** At ~8 calls on success and **≥185 on a single recall failure** (mock), unbounded recursion costs **4 min to 1.7 h per root** before branching.
- **A4 budget (registered on DEV, not TEST):**
  - Local generator: K1 for all movers (≤ 108 candidates), K2/K3 only over the top-L movers by K1 p11 (L = 8 → ≤ ~3–20k candidates, under 1 s), plus a round-robin diversity slot.
  - Per root: ≤ 150 local calls, ≤ 4,000 Y probes, ≤ 600 s wall time, D_max = 4, B_loc = 6, B_exp = 4.
  - Stop reasons: SOLVED / NO_CANDIDATE / SEARCH_BUDGET / MODEL_INPUT_ERROR.
- **Worst case:** 23 roots × 600 s ≈ 3.8 GPU-hours per arm, and five arms (B0–B4) ≈ 19 h. Fallback: cap 300 s per root, and report incompleteness explicitly.
- **B0 (frozen K≤3) keeps its full enumeration by definition:** ≤ 33 s per root.

## 6. Risk register

### CRITICAL

**R-C1. Retarget breaks the immutable original task.**
- Evidence: check C6 on 25 VAL roots. After `retarget(tid=A, goal=d_A)`, the **original target is movable 25/25** (`Root.movable` excludes only the current tid, search.py:L35) and the **original goal is a legal destination 25/25** (`legal_dests` excludes only the current goal, L47). Identity parity holds 25/25.
- Fix: TaskView plus HypoRoot with a **global reservation mask** (T0, G0, OCC0, planned movers), applied to the sampler's legal mask, the candidate filter and composition.
- Test: `test_retarget.py::test_original_task_immutable`, all VAL roots × every mover.

**R-C2. Original-task signal for partial progress is uninformative by construction.**
- Every proper prefix of a minimum-K plan has original Y = 0, by definition of minimum K under the declared grammar.
- The frozen Y head was trained on ≤3-edit endpoints, and its py for 1–3 moves in a K>3-like scene is about 1e-4 (C4).
- First-level hypothesis choice and the iterative loop therefore rest on ranking near-zero scores. Nothing shows this ranking is better than chance for K > 3.
- This cannot be fixed without training. **It must be measured before any claim:** DEV diagnostic D1 (§8). If D1 is at chance, the honest result is "recursion lacks a usable learned signal", and the design must be revised (for example, endpoint-Y set search; see §9 F7).

**R-C3. Unbounded local enumeration and recursion are infeasible at 25–28 objects.** See §5. Fix: A4 budgets and stop reasons. Test: budget accounting in P2, and timing on DEV in P3.

**R-C4. Private data sits near the planner.**
- The laptop holds certified witnesses: the `scaling2d` worktree (G4, G5, G7 jsonl), scratch directories, and the GIF folder in the main checkout.
- The final K9/K12 pool's certified-but-unselected candidates are recorded only in private coverage.
- The K12 pair (61,63) is shared with the engineering K9 and K12 scenes.
- Fix (A11): the planner runs from this sparse worktree; a `sys.addaudithook` guard aborts on opening any path outside the allowlist (public dir, bundle, code, DEV fixtures). DEV uses **engineering scenes only** (A5). The same-pair overlap is reported as a structural-leakage caveat.
- Test: `test_inference_isolation.py`.

### MAJOR

| ID | Risk | Evidence | Fix and test |
|---|---|---|---|
| R-M1 | `MAXOBJ['2d']=20` gives an IndexError above 20 objects | C2: unpatched IndexError at 25/27/28 | DynPad `max(MAXOBJ, n)`. **≤20 objects: identical by construction, 25/25 verified.** At 25/27/28: finite, legal, top-4 for every mover. Full 751 VAL parity in P0. |
| R-M2 | Y endpoints with more than 3 edits are OOD | `moved_count/3` reaches 4.0 at K12 against a training maximum of 1.0; the `mv` mean token changes | Allowed, but h_Y is reported as an uncalibrated heuristic. D2 checks monotonicity on DEV. |
| R-M3 | Rebased-root confusion | C3: gap mean 0.65 | A2: h_Y is always relative to S0. Local chunks in S_p use HypoRoot (rebased), which is the training-consistent X semantics (X starts at q_ref). Documented. |
| R-M4 | Stage-X mismatch (q_ref connector, carried state) | X label definition | Energy only. Ablation λ_X ∈ {0, 1} on DEV. Report chained-X failure phase post hoc. |
| R-M5 | Temporary-task Y miscalibrated (2D AUROC 0.69, ECE 0.19) | TASK_RETARGET_REPORT | Priority or gate plus diversity fallback; never multiplied into h_Y. D3 measures it on K>3 DEV. |
| R-M6 | Grammar differences | planner forbids OCC0 and G0 and ignores q_ref-clear; teacher allows vacated cells; certificate V1 = V2 | The certified K is a minimum under the same grammar as the planner. The q_ref-blocking park cells are not masked, matching frozen K≤3; **owner decision** (A9). Terminal `Q_REF_NOT_CLEAR` is reported. |
| R-M7 | Tiny, concentrated cohort | K12 = 3, all on pair (61,63); K9/K12 25–28 objects are OOD | Absolute counts plus exact intervals; no generalisation claim. |
| R-M8 | `UNKNOWN_*` stored as y = 0 | bxy_teacher L246/272 | The evaluator classifies by `teacher_status`/`negative_kind`; UNKNOWN is never called infeasible. |
| R-M9 | Compute confound | – | B1 uses the same budgets; all caps are logged; the predeclared falsifiers in §8. |
| R-M10 | Device or RNG dependence | the proposal generator is device-specific | Primary run fixed to the laptop CUDA device; device and torch recorded. Numeric parity separated from RNG-trace parity. |
| R-M11 | Disk space: `/home` has 336 MB free | df | Run outputs go to tmpfs scratch; only compact sealed artifacts are committed; abort if free space < 200 MB. |
| R-M12 | Verifier host numerics | girish witnesses reproduce bit-for-bit only on girish | Compare labels, not trajectory hashes; record the host. |
| R-M13 | Object recall versus destination recall | FULL ingredient recall 0.50 (2D) at K≤3 | D1 separates "object never proposed" from "destination never in top-4". |

### MINOR

| ID | Item |
|---|---|
| R-m1 | `n_z`, `propose_top` and `K_max` from the manifest are hard-coded, not read (values match). Documented in the LOCK. |
| R-m2 | The 2D pitch 0.08 is hard-coded (`cell_xy`, `displacement`), which is fine for this 8×8 release. |
| R-m3 | The plan says "top-4 destinations": in the code it is the first 4 of a top-6 proposal (rank < M). Same result. |
| R-m4 | The 2D sampler `pattr` drops the target flag (search.py:L36); the target reaches the sampler only through the task features. Fine, but TaskView must update `task_features` through `inputs` (tid, goal). |
| R-m5 | The frozen decision tie-break prefers shorter sequences and then the json signature. A K>3 tie-break must be declared separately. |

## 7. File-change plan (small, additive)

| New file | Contents | Reuses |
|---|---|---|
| `data.py` | public loader, path-allowlist guard, DynPad, HypoRoot, TaskView (ported `retarget.retarget` with provenance plus the reservation mask) | contracts.view2d, search.Root |
| `models.py` | frozen bundle load with hash check; `propose`, `rank_local` (budgeted), `score_Y_endpoint`, `score_X_chunk`, `ytask`; call counters | benchmark.load_bundle, Sampler.propose_many, Scorer, xy.make_view/collate |
| `planner.py` | solve/expand, global legality, dedup keys, caches, budgets, stop reasons | construct.counts |
| `ranking.py` | canonical chunking and energy C(r); arms B1–B4 switches | – |
| `evaluate.py` | planner-side run and seal (no teacher import) | benchmark.predict (B0) |
| `verify.py` | evaluator-only; the only module allowed to read private files and import `teacher_long` | teacher_long |
| `tests/` | the 5 test files listed in plan §6 | – |

Rules:
- **No edit to any existing file.** The two compatibility fixes, DynPad and the reservation mask, are wrappers in `data.py`, parity-tested against 751 VAL roots.
- `audit_checks.py` and `mock_recursion.py` are audit diagnostics. They are kept, not used by the method.

## 8. Gates, no-leakage protocol, schedule

| Phase | Status now | PASS requires |
|---|---|---|
| P0 preflight | **CONDITIONAL**: assets 10/10 hash-OK, public 23/23 OK, K≤3 replay 25/25 exact, DynPad 25/25 | full 751-VAL replay parity with and without DynPad; LOCK; P0 visual |
| P1 adapters | NOT_STARTED | R-C1 test; Y-only parity on all VAL REPAIR roots; TaskView identity and round-trip; call counters |
| P2 mock planner | NOT_STARTED (design proven in mock) | K4/6/9/12 synthetic chains solved within budget; illegal-composition and cycle tests; budget accounting |
| P3 DEV | **CONDITIONAL on D1–D3** | D1 (engineering K>3): local-beam ingredient recall above a uniform-random control; D2: h_Y monotonicity; D3: temporary-task-Y AUROC on K>3 intermediate scenes; one frozen primary configuration |
| P4 seal | NOT_STARTED | 23 predictions, hashes, 0 teacher calls, isolation audit |
| P5 verify | NOT_STARTED | full outcome statuses with host provenance |
| P6 report | NOT_STARTED | per-root, per-K, failure decomposition |

**No-leakage protocol (A11):**
- Planner processes run from the sparse worktree.
- The audit hook allowlist covers `release_v2/public`, the bundle, the repository code, `~/abf_v34/parity` (VAL) and the engineering DEV directory. Anything else, and any path containing `private`, `LABELS`, `COVERAGE`, `witness`, `/G4/`, `/G5/`, `gifs`, `g5_` or `sel_`, raises.
- The prediction file is sha256-sealed before `verify.py` runs. `verify.py` is the only module importing `teacher_long`, and it may read private files only after the seal digest is recorded.

**Predeclared DEV diagnostics (P3, before any TEST):**
- **D1:** for each engineering K>3 scene, the fraction of its known-necessary objects that appear in the local top-B_loc first-level hypotheses, against a matched uniform-random proposer. Reported split into object misses and destination misses.
- **D2:** h_Y along engineering witness prefixes against random prefixes of equal length. Monotone? A spurious-high rate?
- **D3:** temporary-task-Y AUROC for (A, d_A) in intermediate scenes, against teacher Y on DEV only.
- **Falsifiers:**
  - B4 ≤ B1 at matched budget means recursion adds nothing.
  - Gains vanish when B1 gets 2× budget means the gain was compute.
  - λ_X = 0 equal to λ_X = 1 means stage X has no value.

**Visuals per phase:** as in plan §7, with the P0 23-scene public grid carrying **no K labels**.

## 9. Adversarial second review

| # | Counterexample | Outcome | Status |
|---|---|---|---|
| F1 | High local p11 for every chunk, but a globally invalid order (an enabler placed after its dependent) | The global legality check does not catch physics. Stage X (energy) is the only learned guard; the mock shows X separates orders. Real X OOD is untested. | Fixable / measure (λ_X ablation) |
| F2 | Same endpoint, different physical order | h_Y identical by construction (Y-only node); stage X differs. Dedup keys are order-aware. | Fixed by design |
| F3 | A necessary enabler is never sampled (not in top-4 or the beam) | Search fails; the mock shows 185 calls wasted. No learned mechanism can recover it. | **Fundamental**; report as "ingredient missing" (D1) |
| F4 | X q_ref mismatch: a chunk is feasible from q_ref but not from the carried state | h_X over-optimistic; only the teacher reveals it. | Fundamental for the heuristic; reported as FAIL_X phase |
| F5 | K12 OOD: 27–28 objects, 12 edits | Code-capable (C2, C4 finite); predictive validity unknown. | Unsupported as a validity claim |
| F6 | Temporary-target Y says "A can go now" when it cannot | Recursion skips a needed enabler; mitigated by the diversity fallback. | Partially fixable |
| F7 | Original Y is 0 for every proper prefix, so first-level choice is noise | The whole method degenerates to a random search over plan shapes. | **CRITICAL unknown.** D1 decides; if negative, revise toward an endpoint-Y-guided set search: score Y-only endpoints of candidate mover sets relative to S0, then order with recursion and X. That is a design change needing approval. |
| F8 | The no-op gate fires (`p_noop ≥ 0.5` on a blocked target) | False NOOP on all-blocked TEST. B0 replicates frozen behaviour; the K>3 planner uses the same gate (A8), with false-NOOPs reported. | Reported |
| F9 | The original target or goal leaks into a temporary view | R-C1 evidence 25/25 | Fixed by A1 |
| F10 | Cost explosion masquerading as a method effect | Budget-matched B1, logged usage, falsifiers | Controlled |

## 10. Answers to plan §4 (short)

1. **Why would the cVAE propose useful destinations?** It is task-conditioned for "where to park so the target benefits". Destination choice is lenient (many free cells work); object choice is the bottleneck. Fallback: round-robin diversity. A necessary placement with negligible mass is a recorded miss (F3).
2. **Which action to repair?** Temporary-task Y (§4), plus a deterministic diversity fallback. No step-failure model.
3. **Temporary Y versus X?** Y_A means "A could reach d_A in this scene from q_ref", a task-level endpoint judgement. The chunk's px is the execution heuristic. Neither is "the robot can do it now from its carried state".
4. **A needed object outside the top hypotheses?** Insertion-site branching and repeated sampling in edited scenes help only within budget. Misses are fundamental (F3) and measured by D1.
5. **A 12-move plan without exponential enumeration?** Yes, if recall holds: 8 local calls in the mock. Failure costs ≥ 185 calls, so A4 caps are mandatory.
6. **Why use stage X as a ranking energy?** It is the only learned order-sensitive term. The λ_X = 0 ablation decides its value.
7. **Why an edited endpoint of S0?** C3: exact on ≤3 edits; rebased differs by a mean of 0.65.
8. **Order sensitivity?** h_Y is shared per endpoint; h_X is per order; dedup keys are order-aware.
9. **25–28 objects and 9 or more edits?** The code runs (C2, C4); validity is OOD and unknown.
10. **Can the no-op gate suppress search?** It can (F8). The same frozen gate is used, and false-NOOPs are reported.
11. **Same teacher as certification?** Yes, `teacher_long` at the dataset commit (≤6 → frozen; 7–12 → LongPhysics), with the connector, `UNKNOWN_*` statuses and host recorded.
12. **What falsifies the method?** The falsifiers in §8.
13. **What counts as partial evidence?** Ingredients present but uncomposed; composed but FAIL_X; Y high but FAIL_Y. All reported separately.
14. **How is leakage prevented?** A11 hook, sparse worktree, sealed predictions.
15. **Why is a tiny cohort useful?** It is a stress test of *capability under composition*. It is not a benchmark: no generalisation beyond these 23 scenes, and K12 has one target/goal pair.

## 11. Claim ledger

| Claim | Status |
|---|---|
| Frozen assets intact (10/10 SHA-256) | **PROVEN** |
| The six inference files are identical across the dataset, V3.4 and post-ablation branches | **PROVEN** |
| K≤3 replay is exact on 25 VAL roots | **PROVEN** (751 pending in P0) |
| DynPad is identical at ≤20 objects and finite at 25–28 | **PROVEN** on 25 VAL roots plus 3 synthetic scenes |
| Y-only endpoint equals the frozen py (≤3 edits) | **PROVEN** (24 roots) |
| A rebased no-op is not equivalent | **PROVEN** (gap 0.65 mean) |
| The existing retarget leaks the original target and goal | **PROVEN** (25/25) |
| The recursion algorithm can construct the K6 and K12 chains given perfect signals | **SUPPORTED_BY_MOCK** |
| The frozen model's signals are informative for K > 3 | **NOT_TESTED** (D1–D3) |
| Recursion improves over budget-matched flat search | **NOT_TESTED** |

## 12. Verdict, implementation order, commands run

**REVISE.** Adopt A1–A14. Then:
1. P0: full 751 replay and DynPad parity; LOCK; public grid.
2. P1: data.py and models.py with the R-C1 fix and parity tests.
3. P2: planner.py on mocks, plus budgets.
4. P3: DEV D1–D3. **Stop and report.** If D1 is at chance, stop and propose the F7 revision instead of tuning.
5. P4–P6 only after approval.

**Commands actually run** (read-only or mock; no TEST data, no physics, no training):

```bash
git -C <repo> rev-parse ...; git worktree add --no-checkout -b naren/kgt3-recursive .claude/worktrees/kgt3 e07354b3c8...
git sparse-checkout set --no-cone '/approach_b_final/*.py' '/approach_b_final/recursive_kgt3/' '/scaling2d_k12/*.py' \
    '/scaling2d_k12/G1/G1_LONG_TEACHER.md' '/scaling2d_k12/G7/release_v2/public/'
python3 - (sha256 of ~/abf_v34/approach_b_bundle vs BUNDLE_MANIFEST)          # 10/10 OK
python audit_checks.py --n 25 --device cuda --retarget <read-only copy of validation_k3/retarget.py>   # results: audit_checks_result.json
python3 mock_recursion.py                                                      # K6/K12 SOLVED; recall-miss/cap11 NO_CANDIDATE
```
