# P17 implementation map (2D only)

What runs where, with explicit formulas and which weights receive gradients. P10–P16 modules are reused read-only; P17 adds the `p17_*` modules below. No P10–P16 source or artifact is modified.

## 1. Shared physics, domain and search (used by B and D alike)

| concern | function | notes |
|---|---|---|
| deterministic motion provider | `p16_motion.DetPhysics` (unchanged) | planner profile `P16_FAST`: node budgets only, no wall-clock adjudication. Shared exact cache with virtual accounting. Direct transit, else a bounded RRT transit. |
| scene-only task | `p16_common.task_from_root` | deletion-tested: no catalogue, roles or teacher fields |
| action domain `P17_DOMAIN_V1` | `p17_domain.movers`, `slot_fn`, `repairs`, `exhaustive_sequences`, `query_id` | 0–4 relocations, every movable non-fixed object, slots recomputed on every hypothetical occupancy, freed source cells, ≤ 2 moves per object, never consecutive |
| corrected search | `p17_search.search` | key = (sorted occupancy, exact q bytes, last mover); dominance = travel ≤ and per-object counts ≤ within a key. Iterative deepening with travel branch-and-bound. Claims are restricted to the finite graph (§4). |
| exhaustive reference | `p17_search.exhaustive` | tests only: every legal sequence and every verified mode, no pruning |
| fixed-sequence verifier | `p17_verify.verify_existential` | branches over every certified motion alternative per step; VERIFIED if any branch completes. Only motion-independent certificates refute; the q-dependent LINK0_SECTOR_PICK refutes only its own branch. `first=True` (labels / execution) stops at the cheapest-first verified branch. |
| frozen P16 baseline | `p17_verify.verify_sequence_greedy_P16` | cheapest mode per step (comparison only) |
| replay | `p16_motion.replay` | independent sequential re-certification of every recorded array, with a continuity check |
| finite library domain (M7 only) | `p17_mech.lib_domain` | relocations: library trajectories + direct transits, no online relocation planning, so an edge with no realization is `REFUTED_IN_LIBRARY_DOMAIN` (scoped, never global). Target action: planner (VERIFIED is sound; failure is UNKNOWN) |

## 2. Approach B

### Production default: lean B (`LB`, `p17_b.model("LB")` = `abc7_models.ModelBC7("B", "none", order="pred")`)

For one root with active binary query variables (z0 = empty repair; zS[I] = parked-subset scene edits; zR = ordered repair; zO[t] = omission of step t):

- Scene block: `P_S(z_s) = Π_i Bernoulli(z_i; σ(s_i))`, where `s_i = scene(DINOv2-projection features, numeric context, edit embedding)`.
- Query block (couple = "none"): `P_Q(z_q | z_s) = Π_j Bernoulli(z_j; σ(r_j))`, where `r_j` = F2 prefix-order repair unary of the ordered sequence (or of the omission). The encoder replays the actions from the initial poses, so every intermediate pose is recomputed.
- So `P(z) = P_S(z_s) · P_Q(z_q)` is an exact product of Bernoullis.
- Analytic static check only: `λ_static = λ_travel = 0`.
- Keyed ontology (`unique_factor_keyed`): one variable per physical query (`seq:<root>:<o>d…` / `scene:<root>:<edit>`). A duplicate reference to the same physical query is the same variable.
- Loss: negative log-likelihood of the observed labels (UNKNOWN labels are marginalized, never 0).
- Gradients: DINOv2 is frozen; the projection `vproj`, encoders `enc` / `ctxn` / `pooln`, the scene head `scene`, edit heads, the order encoder `order_s` and `mix` all train.

### Experimental arm: LB+G (generic-only coupling; `ModelBC7("B", "quadratic", drop=("pair_scene", "pair_omit"))`)

- `P(z) = P_S(z_s) · P_Q(z_q | z_s)`, with `P_Q ∝ exp(z_q·s_q + ½ zᵀ W z)`, normalized per `z_s`.
- `W_ab = ½[cpl(v_a, v_b, ctx) + cpl(v_b, v_a, ctx)]` over scene–query and query–query pairs.
- F3 (scene pair), F4 (omission pair), higher-order and J terms are absent.
- Because `P_Q` is normalized for every `z_s`, the scene marginals (including `P(z0)`) do not depend on `cpl`. This is tested: `test_coupling_off_is_inference_only_and_keeps_original_marginal`.
- Gradients: as LB, plus `cpl` and `typ`.

### Controls

| arm | definition |
|---|---|
| `LB-W` | LB with the scene head widened to h = 320 (516,901 vs LB+G 516,774 parameters): parameter-matched, non-coupled |
| `LB-F2` | order-invariant summary (`order="none"`) |
| `LC` | GRU order (`ModelBC7("C", "none")`) |
| `A`, `SF` | P13 architectures (`abc8.build`), factorized objective |
| `FULLB` | full keyed B (F1, F3, F4, F5 + higher-order, J; `abc8.build("B-full")`) retrained on the same data with its historical `λ_static = λ_travel = 1`: comparator only |
| `P13:*` | frozen historical checkpoints |

### Inference-only and policy controls

| arm string | meaning |
|---|---|
| `LB+G\|nocpl` | `p17_b.coupling_off`: `cpl` outputs 0 at inference, weights frozen; own calibrated policy |
| `X@Y` | X's frozen scores under Y's frozen thresholds (`LB+G@LB`, `LB@LB+G`) |

### Training (`p17_b.fit` → `_fit_es`)

- AdamW (lr 1e-3, weight decay 1e-4), RootSampler batch 12, gradient clip 10.
- Validation root NLL every 20 updates. Early stop after 15 evaluations without a relative improvement > 1e-3; hard cap 3000 updates. The best checkpoint is restored.
- Data: `runs/p17/b/TRAIN.pt` = P13 train (tagged protocol `P13_TEACHER_CONSTRUCTOR_CATALOGUE`) + P17 existential labels on P16 train / dev / calib + p17train. Validation = P13 val + P16 val (P17 labels).

### Labels (`p17_b.label`, protocol `P17_EXISTENTIAL_V1`)

- One provider per sequence (`P17_SEQ_BUDGET_V1` = 150 / 4 / 6 / 4) over a shared exact cache.
- y = 1: VERIFIED + replay CLEAR. y = 0: only a motion-independent certificate. Otherwise UNKNOWN.

### Scoring and decision

- `p17_b.score` gives the exact prior marginals (equality-tested against `p9_l3.root_eval9`); ensemble = mean over seeds 0, 1, 2.
- Decision (`p16_b.choose`): EMPTY if `p'(empty) ≥ t0`; else the admitted (`p' ≥ t`) repair with the fewest moves, then the highest `p'`; else ABSTAIN.
- `(t0, t)` per arm on p17calib only (`p17_data.b_calibrate`).
- Execution (`p17_exec.b_root`): the chosen query is verified existentially (first-mode) and replayed.

### Baselines

| baseline | definition |
|---|---|
| `empty_always` | always choose EMPTY |
| `random` | uniformly random catalogue entry |
| `geometry` | static blocker heuristic |
| `verify_first` | certify the original target (charged), else run the geometry-guided corrected search (charged) |

## 3. Approach D

### Production model: pairless D

- `p_f = σ(u)` and conditional blocker Bernoullis `P(b | y0 = 0) = Π_i Bernoulli(σ(a_i))` (`d_blockers.ModelD(pair=False)`).
- Loss: feasibility BCE + masked blocker NLL (λ_B = 2), only for MINIMAL_SETS lattices with a defined proof-grounded mask. NO_CLEARING / INCOMPLETE / NON_MONOTONE / UNKNOWN never become an all-zero mask.
- Gradients: projection and heads; DINOv2 is frozen.

### Families

| family | source |
|---|---|
| `D` (paired) | frozen P13 |
| `Dp` | frozen P13 pairless |
| `Dp16` | P16 retrain |
| `Dp17` | `p17_d.train_dp17`: P13 items (PARKING_LATTICE_V1, NO_CLEARING masked) + P16 / P17 roots with **MULTI_DEST_LATTICE_V1** labels; early stopping as B; seeds 0–2 |

### Label protocols

- `PARKING_LATTICE_V1`: the parked-subset edits of the B catalogue.
- `MULTI_DEST_LATTICE_V1` (`p17_d.multi_dest_lattice`): a subset is sufficient if **some** admissible assignment to its first k = 2 domain slots makes the original target VERIFIED. It is negative only if every assignment is CERTIFIED; otherwise UNKNOWN.

### Temporary-target interface

- `p15_retarget.build_record` rebinds roles, goal, numeric context and DINOv2 features for (state, q, temporary target o, destination d).
- `p17_d.temp_lattice` gives the physical labels at the original state; `p17_data.temp_intermediate` gives them after a certified first relocation.
- Probes: one per decided lattice state (`p17_d._lattice_probes`).

### Per-family calibration (fixes the P16 shared-calibration defect)

- `p17_data.d_calibrate` → `p17_d.fit_calibration` fits `p' = σ(a·logit + b)` per family.
- Form (identity / bias / full, Gaussian prior centred on the identity) is chosen by root-split 2-fold CV log loss.
- Fitted on p17calib probes, held out on P16 calib probes. No D family trains on either (`D_TRAIN_SPLITS` excludes P16 calib).
- `Guide` loads only `runs/p17/d/calibration/<family>.json` (tested).

### Guides (`p17_d.Guide`; reorder only, never prune)

| guide | behaviour |
|---|---|
| `<family>` | recursion: defer a mover whose own-family calibrated temporary-target feasibility to its first slot is < 0.5 |
| `-norec` | no recursion |
| `-blk` | experimental: also promotes predicted blockers of a deferred mover; not production until temporary blocker marginals are validated |
| `geometry[-norec]` | non-learned geometry ordering |
| `uniform` | uniform order |
| `oracle` | original-scene blocker union from sealed / unsealed labels; non-deployable |

Search: `p17_exec.d_root` → `p17_search.search` on the shared domain, with `D_BUDGET` 400 / 6 / 16 / 8, node cap 500, n ≤ 4, per object ≤ 2.

## 4. Status and claim vocabulary

**Statuses:** VERIFIED (witness + replay); CERTIFIED_INFEASIBLE / STATIC_INVALID (scoped certificate); UNKNOWN_<reason> (never a negative).

**Search claims:**
- MIN_MOVES[_AND_MIN_TRAVEL]_WITHIN_FULLY_ADJUDICATED_FINITE_GRAPH
- BEST_VERIFIED_WITHIN_BUDGET
- NO_PLAN_IN_FULLY_ADJUDICATED_FINITE_GRAPH
- NO_PLAN_FOUND

## 5. Orchestration

| module | responsibility |
|---|---|
| `p17_eval` | ledger, guarded jobs, gates, audit, P17-1 rescans, determinism. `p17_eval.<name>` forwards to the modules below. |
| `p17_data` | splits, labelling, training sets, B / D calibration |
| `p17_mechjobs` | mechanism screens, mining, evidence, M7 library checks, proposal recall |
| `p17_prosp` | retrospective P16-root re-analysis, pre-registration, sealed prospective workers |
| `p17_exec` | per-root B / D execution |
| `p17_analysis` | frozen analyses |
| `p17_final` | post-run custody (sealed manifest → push → unseal), prospective oracle guide, final analyses (frozen functions applied to unsealed outputs; matched per-root table), gates, final manifest |
| `p17_viz` | figures and replay-only GIFs |
