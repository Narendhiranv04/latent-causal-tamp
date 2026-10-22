# P8 read-only audit: ABC7_V1 factor scopes and P7 evidence

## Repository and evidence

- **Repository state:** HEAD = origin/main = `11543142fe75…` on branch `main`. Pre-existing dirty state, left untouched: the two
  tracked root-PDF deletions, the user's untracked instruction files and guide folder, and nine uncommitted P7a grid
  checkpoints (hashed in `runs/p7/a_training/checkpoint_manifest.json`).
- **Baseline regression** (guarded, `runs/p8/audit/regression`): **316 / 316 passed, 6 / 6 replays**, 591.4 CPU-s (cap 1,200).
- **Manifests:** all 8 historical manifests (G4C pilot, POC_S, G4D, P4 pilot, P5 D3-lite, P5 G4E, P6 collect, P7 collection)
  have every listed file present and byte-identical (`replay_audit.json`).
- **P7 recount from saved records** (`baseline_status.json`, `data_coverage.csv`):
  - statuses 269 VERIFIED / 368 CERTIFIED / 125 BUDGET / 8 UNKNOWN / 201 NOT_RUN, which **matches report 0023 exactly**;
  - κ +1 ×16 (all operational), −1 ×5 (all certified), 0 ×7 (4 certified, 3 operational);
  - 17 decided order contrasts and 48 one-shot episodes (A 6, B 6, C 7, U 6 successes).

## Tensor and parameter path (B; C differs only in the order block)

| stage | computation | shapes / notes |
|---|---|---|
| object tokens | `enc([numeric(xy) 14, vproj(DINO 384→32)])` | `[n, 128]` |
| edit-aware tokens | `edit_proj([moved, dx, dy, abs(d), x0, y0])` added to the tokens | `[n, 128]` |
| edit vector e_I | `edit_head([mean ⊕ max pool 128, mean of moved 128, target token 128, n_moved/3])` | `[128]` |
| scene slots | logit `scene([e_I, ctxn(c0) 128])`; slot vector v = e_I + `typ(zS)` | — |
| repair order | ideal-prefix action tokens `act([tok_i 128, end_i 128, pooled 128, t])` give `[m, 128]` | B: `mix([a_t, mean_{u<t} pairo([a_u, a_t])])`, mean over t → g; C: GRU (`h0`, `gru`) → g |
| order logits | `s_R = order_s([g, scene_vec(final xy)])`; each zO[t] repeats this on the RECOMPUTED omitted prefix | — |
| scene block | `E_S(z_s) = −s·z − ½ z^T W_S z − ho_s([Z U(v), c0])` over `2^{K_s}` (K_s ≤ 4) | W_S: `pair_scene` (z0–zS[I]) + `cpl` (zS–zS), context c0 |
| repair block | `E_Q(z_q; z_s) = −s_q·z_q − ½ z^T W z − ho_q([Z U(V), g])`, normalized per z_s | W: `pair_omit` (zR–zO[t]), `cpl` (scene↔repair, repair↔repair), context g(r); `[2^{K_s}, 2^{K_q}]` |
| joint | `log P = log P_S ⊕ log P_Q` over `2^K` states, K ≤ 9 (512) | exact enumeration |
| derived logit and energy | `l_T(r)` = logit of P(zR = 1), or of P(z0 = 1) for r = ∅; `Ebar_R = E_static + T softplus(−l_T)` | travel `J = softplus(cost(g))`, independent of z |

## Which parameter can move what (`factor_mapping.json → scope_tests`)

Each test perturbs one module's parameters on a 4-move synthetic root:

| module | P_S (unconditional scene beliefs) | P_Q (repair conditionals) | P(zR) |
|---|---|---|---|
| `scene`, `pair_scene`, `ho_s` | **changes** | 0 | changes (only through P_S) |
| `pair_omit`, `ho_q`, `order_s` | **0** | changes | changes |
| `cpl` | changes (scene–scene pairs) | changes (cross and repair pairs) | changes |

**Consequences.**
- **Generic coupling has two different roles.** Within the scene block (`cpl` on zS–zS pairs and `ho_s`) it CAN change the
  root-level intervention beliefs, including κ. Across blocks (scene↔repair `cpl` pairs and `ho_q`) it can only change
  repair conditionals; it can **never** change P_S, by construction of the chain normalization.
- **B-structured** keeps only z0–zS[I] and zR–zO[t] pairs. Its scene block can couple each edit only to z0, so it cannot
  represent a direct zA–zB–zAB dependence. The offline conditional tasks a / b test exactly this.
- **B-none** (P7 "B-no-coupling") is a product of independent Bernoulli fields. It is **not** a test of generic coupling
  alone, because it also removes the structured pairs.
- **Factorized predictors can still produce nonzero κ̂**: κ̂ = p_AB − p_A − p_B + p_0 is defined from marginals alone.
  Predicting κ is therefore NOT evidence of learned coupling.

## Mathematical and scope tests (guarded run, `runs/p8/a_tests`: 32 passed, 257.9 CPU-s)

- **`test_p8.py`, 7 tests:**
  - identical direct parameters with different cross terms;
  - `none` equals the product of marginals (< 1e-12);
  - repair-side perturbations never move P_S (< 1e-12);
  - the structured `pair_omit` changes P(zO[1] | zR) without `cpl`;
  - 2^K normalization for K ∈ {4, 5, 7, 8, 9} and brute-force conditioning (< 1e-12);
  - unaliased omission slots, and omitted objects that stay at their initial pose;
  - gradient reachability for every named factor and objective;
  - factorized conditionals equal marginals (< 1e-10);
  - identical hash masks and sampler batches for every arm, with task labels never hidden;
  - κ fixtures and a held-out compositional fixture (finite; capacity only).
- **Also re-run:** `test_p7_models.py` (9), `test_p6_math.py` (14) and `test_p7_plan.py` (2).

## Changes made in P8a (versioned; P7 semantics unchanged)

- `abc7_train._static` is vectorized: the same mean of the same BCE terms, |Δ| = 0.0.
- `abc7_train` gains an additive SF branch (no effect on other arms).
- `abc8.py` (`ABC8_DIAG_V1`) adds the SF arm, the κ-balanced root sampler and the SPARSE_AUX masks.
- No ABC7 factor, normalization or checkpoint key changed.
