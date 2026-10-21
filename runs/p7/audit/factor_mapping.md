# P7a factor-mapping audit (A / B / C), P6 parameterization vs ABC7

Evidence: code at `abc_models.py` (P6, unchanged), `abc7_models.py` (ABC7_V1), numerical trace
`runs/p7/audit/p6_numerical_audit.json` (frozen P6 checkpoints, frozen P6 roots), tests
`tests/test_p6_math.py`, `tests/test_p7_models.py`. Truth table: `factor_truth_table.json`.

## Normative five factors (Methodology v1.7 §5)

`E_B(r,z) = E_static + phi_seq(r,zR) + Σ_I phi_scene(I,z0,zS[I]) + Σ_t phi_omit(r,t,zR,zO[t]) + phi_couple(r,z)`; C replaces B's
prefix order factor by a GRU; A has no z. Travel J is a separate readout (not a factor).

## Q1 — omission factor

* **P6:** `zO[t]` has a unary logit `order_s(order(r minus t))` (recomputed omitted prefixes, correct) but **no dedicated
  zR–zO[t] interaction**; the only link is the generic pair coupling `W(r)` over all slot pairs. With coupling off (P6
  B-no-coupling) zR and zO[t] are independent. **SPEC_MISMATCH (phi_omit was unary only).**
* **ABC7:** `phi_omit(r,t,zR,zO[t]) = −s_O[t] zO[t] − ω_t(r) zR zO[t]` with `ω_t = pair_omit(v_R, v_O[t], g(r))` (named module).

## Q2 — scene factor inputs

* **P6:** `s_I = scene([pooled(encode(edited xy)), c0])`, pooled = mean ⊕ max of all object tokens. No moved flags, no
  displacement, no original pose, no edit identity. Measured: the pooled edited vector differs from the unedited one by
  **0.04–0.23 % (relative L2)**; scene logits for none/A/B/A+B agree to **< 0.01** (B: 8.095/8.104/8.098/8.107) →
  identical A/B/A+B predictions (P6 report §7). **Root cause = representation**, not optimization alone.
* **ABC7:** per-object edit channels `[moved, dx, dy, |d|, x0, y0]` (from c0 and the declared edit only) added to the
  object token; `e_I = edit_head([pool(all), mean(moved tokens), target token, n_moved/3])`. No post-edit image, no
  teacher outcome, no screen/collision result, no trajectory. Test: pairwise relative L2 between edit vectors > 0.05 at
  init; permutation of object storage order leaves edit vectors unchanged (< 1e-10).

## Q3 — root scope of z0 / zS

* **P6:** coupling `W(r)` and `phi_HO` were conditioned on the repair summary g(r) for **all** pairs, so the marginal
  `p(zS[I] | r)` depended on the scored repair: on p6_2026102301 B's p(zS[A]) ranges **0.24–0.33** and p(z0)
  **0.003–0.28** across seven repairs of the same root (no-coupling: invariant). Contradictory "fixed-scene effects".
* **ABC7 (preferred contract):** chain-normalized joint
  `E(r,z) = Ebar_R(r) + [E_S(z_s) + T log Z_S] + [E_Q(z_q; z_s, r) + T log Z_Q(z_s, r)]`, hence
  `P(z | r) = P_S(z_s | c0) P_Q(z_q | z_s, r, c0)`; scene-block pairs use the root context c0 only. Test: scene marginals
  identical for every candidate of a root (< 1e-12). Cross-outcome coupling (scene ↔ repair) is kept inside `E_Q`.
  `Ebar_R(r) = E_static(r) + T softplus(−l_T(r))`, `l_T` = derived logit of `P(zR=1|r)` (P(z0=1) for the empty repair).
  This is a **changed normalization** (versioned ABC7), not the P6 parameterization.

## Q4 — order factors, no double counting

* B: `phi_seq` from prefix-conditioned predecessor interactions (`pairo`, `mix`), no GRU. C: GRU (`h0`, `gru`), no
  `pairo`/`mix`. Omission logits use **recomputed** omitted ideal prefixes in both (not a zeroed token). Test asserts the
  module sets.

## Q5 — coupling modes

`couple = full` (scene/omit pairs + general pairs `cpl` + higher-order `ho_s`, `ho_q`) | `quadratic` (no HO) |
`structured` (only phi_scene / phi_omit pairs) | `none` (**no** cross-outcome term at all). Tests: modules absent
exactly as named; under `none` the joint equals the product of its marginals (< 1e-12); `pair_omit` and `ho_q` receive
gradient under `full`.

## Q6 — compact implementation vs the five factors

| factor | P6 (`E_static − Σ s_k z_k − ½ zᵀW(r)z − phi_HO + T K ln2`) | ABC7 |
|---|---|---|
| static | U, V on final endpoints | same |
| phi_seq | s_zR (B prefix-pair / C GRU) | same |
| phi_scene | unary s_zS only; z0–zS pair only via generic W(r) (r-dependent) | unary (edit-specific) + named z0–zS[I] pair (c0) |
| phi_omit | unary s_zO only | unary + named zR–zO[t] pair |
| phi_couple | all pairs W(r) + HO(r) | remaining pairs + HO, scene block c0-conditioned |
| T K ln 2 | uniform reference measure needed because Ebar summed unnormalized z mass | not needed: Ebar_R is per-r normalized (test: Ebar_R equals −T log Σ_z exp(−E/T)) |
| travel J | separate head of g(r) | same; independent of z (scalar test) |

Name for the P6 form: **"P6 quadratic/logit parameterization"**.

## Q7 — Z_LAYOUT_V3_R4

Unchanged and re-verified (`tests/test_p6_math.py`): K = 4, 5, 7, 8, 9 for m = 0..4; 512 states at m = 4; aliases and
>4 moves refused; equal raw energies ⇒ equal Ē under the uniform measure; inactive slots never enter energy or partition;
G4B detailed balance at cap 4 with unequal K. ABC7 enumerates the same active slots (512 states at K = 9, test).

## Q8 — invariances and namespaces

Edit vectors permutation-invariant (test); pair potentials symmetric by construction (averaged over both argument
orders); B and C order logits change under a swap of two actions (test); cost head independent of z; learner inputs
remain the `learn_data.INPUT_KEYS` allowlist (leakage audit unchanged); teacher labels only in `privileged`.

## Loss / gradient audit (measured before change)

P6 B at initialization (train roots): pool 7.44 nats, gradient norm 8.82; task 0.70 / 0.84; outcome 0.69 / 1.34;
effect 0.45 / 2.33; static 0.71 / 0.87; cost 0.22 / 0.20. Pool term summed over every (r, z) state of all fully decided
candidates without per-root or per-bit normalization; global clip 1.0 then clipped every step (P6 report). ABC7 at
initialization: pool 2.97 / 1.68, task 0.69 / 0.67, scene 0.69 / 1.12, omit 0.57 / 2.47, effect 0.41 / 1.91,
static 0.67 / 0.69, cost 0.22 / 0.19 (each term averaged within root, then over roots; joint z-likelihood per bit).
