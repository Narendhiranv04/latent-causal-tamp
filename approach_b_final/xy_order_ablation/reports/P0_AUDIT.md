# P0: audit, label inventory and preregistration

**Gate: PASS (read-only).** No GPU inference, no teacher query. The resource envelope in `starting_prompt.md` is **not yet affirmed**, so P1 parity (it needs the CUDA proposal RNG to match the archived predictions), P2 and P3 are on hold.

## Provenance (`P0_AUDIT.json`)

- **Base and plan:** branch `naren/rss27-xy-order-ablation` from verified `c50a2ebb19893151…` (`87ebf65d24` is an ancestor), in its own sparse worktree. `plan.md` / `starting_prompt.md` are byte copies of `instruction-phase-md/final_ablations/`.
- **Bundle `~/abf_v34/approach_b_bundle`:**
  - All 10 manifest hashes verify.
  - Rule `noop_gate 0.5 / eta 0.3 / α = β = γ = 0`, M = 4, K_max = 3, S1 n_z = 64, proposal seed 0, identical for both domains.
  - Scorer: coupled arm D s0. `xy.TAU = 1.0`, so no logit rescaling is needed.
- **Teacher runtime:** `fin3d.py`, `perm3d.py`, `bwlphys.py` and `teacher2d.py` hash-equal to the CR P0 audit (laptop envs `~/abf_v3_laptop/env2d|env3d`).
- **Roster:** the CR roster files hash-equal `P0_COHORT.json` (210 per domain; 2D 210 families, 3D 149). The C0 reference reproduces exactly from the CR per-root results: **2D 82 / 150, 3D 113 / 150**.

## Historical ablation figures in the draft (correction)

The draft's 2D numbers (full 51.8, w/o coupling 49.4, w/o order 47.2, direct Z 38.5) **are not measured success rates of those arms on one cohort**.
- 51.8 is the V3.4 fresh-cohort FULL result.
- The others equal 51.8 plus the K3-ablation **historical-TEST paired deltas**: E −2.4, G −4.5 (51.8 − 4.5 = 47.3, not 47.2), DIRECT −13.3 (`ablations_k3/reports/FINAL_REPORT.md` §2).

That mixes two cohorts. The same-cohort figures are FULL TEST 52.9 % with paired deltas, or the per-arm absolute rates in `ablations_k3/reports/tables/physical_test_2d.json`. Note also that the K3 ablation's "0 UNKNOWN" used the operational convention. Its TEST split is not a pristine hold-out. None of this is re-run here.

## Label inventory (exact-contract caches + finalized snapshot labels)

The sources are 21 cache directories on this host, all index-keyed with the "unchanged finalized teacher" provenance, plus the VAL snapshot labels. There are **0 decided conflicts** in either domain.

| | 2D VAL | 2D cohort | 3D VAL | 3D cohort |
|---|---|---|---|---|
| X labels (decided 1 / 0 / unresolved) | 24,502 / 9,181 / 10,075 | 406 / 83 / 108 | 9,137 / 6,566 / 0 | 498 / 86 / 0 |
| Y endpoint labels (1 / 0 / unresolved) | 18,655 / 11,529 / 11,788 | 422 / 67 / 133 | 7,601 / 7,316 / 0 | 490 / 110 / 0 |
| m = 2 groups: any / complete / complete with Y = 1 | 9,773 / 495 / 288 | 176 / 1 / 1 | 4,283 / 381 / 242 | 214 / 6 / 6 |
| m = 2 **mixed X** (Y = 1) | 163 (80) | 0 | 66 (24) | 0 |
| m = 3 groups: any / complete / complete with Y = 1 | 27,019 / 173 / 173 | 322 / 0 / 0 | 8,601 / 70 / 70 | 240 / 0 / 0 |
| m = 3 **mixed X** (Y = 1) | 216 (188) | 0 | 136 (111) | 0 |
| roots / families with a mixed group | 245 / 193 | 0 | 116 / 59 | 0 |
| mixed groups inside the original top-4 pool (m = 2 + 3) | 113 | 0 | 85 | 0 |

**Reading.**
- **O-A (existing labels):** exposed VAL holds hundreds of same-endpoint groups whose orders disagree on X, in both domains. That is far more than the 2 discordant pairs of the earlier K ≤ 2 diagnostic. They were collected by earlier studies, so they are selection-biased and say nothing about population prevalence.
- **The locked cohort has no mixed group at all**, so cohort-level order evidence needs the O-B panel.

**2D status mapping (amendment 1).** `bxy_teacher.py` marks `Q_REF_NOT_CLEAR_IN_EDITED_SCENE` and `TERMINAL_STATE_NOT_CLEAR` as `negative_kind: CERTIFIED` (deterministic geometric checks), so they are decided negatives under the strict mapping. That reclassifies 63 2D VAL X labels. The CR study's cohort labels contained neither status, so its results are unchanged. `REPLAY_FAILED` (OTHER_FAILURE), `INELIGIBLE` and `UNKNOWN_*` stay unresolved.

## O-B order panel, locked (`P0_PANEL.json`, sha256 in `protocol.json`)

- **Candidates:** legacy-witness endpoints (`labels.B`, y = 1) of the locked roster. That is 133 m = 2 and 97 m = 3 candidates in 2D, 92 and 82 in 3D.
- **Selection:** 10 per m per domain by sha256 `XYORDER_PANEL_V1|domain|root|canonical`, at most one per root, distinct families first. This gives **20 assignments and 20 families per domain**, and at most 80 ordered requests per domain.
- No model score, X label or order outcome was read to choose them.

## Preregistration (`protocol.json`)

- **Arms:** J (p11), X (marginal pX), Y (pY, one shared value per canonical endpoint) and XC (pX1, secondary). All share the pool, no-op (pY(empty)), gate, η, tie key and `exhaustive.Selectors`. Rank-only: argmax over nonempty repairs per readout.
- **Primary statistics:** four contrasts (2D / 3D × J − X, J − Y) on K1–K3 all-root strict verified success. Whole-family bootstrap (4,000 draws, seed 0). Paired family-level sign-flip randomization p (20,000 draws, plus-one). Holm over the four.
- **Established improvement** requires all of: Holm p < 0.05, a CI excluding 0, ≤ 20 % UNKNOWN in both arms, and ≥ 90 % of the roster evaluable.
- **Order primary** (learned vs canonical / random, Holm over 4) only if ≥ 10 mixed groups and ≥ 10 families per domain; otherwise descriptive.
- **Query tiers** per domain (cap 400): T1 primary picks ≤ 320 → T2 panel (reserved 80) → T3 K0 / NONE → T4 rank-only + XC.

## P1 status (CPU contract tests, `tests/test_contracts.py`): 14 passed

- J is **bit-identical** to the production `Scorer.score` p11; py and px match exactly.
- The algebraic identities hold, and pY is exactly invariant across permutations within a forward pass.
- Batch parity holds within 1e-6.
- On CPU, the shared streamed selector equals the production `exhaustive.score_root` decision, with chunking parity at 8,192 vs 97.
- An empty pool gives NOOP / ABSTAIN and no rank-only pick.
- J / X / Y selectors equal `xy.choose` over 300 random cases, including 0.3 ≤ p_noop < 0.5.
- The Y arm is order-blind.
- The label mapping, conflict quarantine and decided-over-unknown upgrade behave as specified.
- Order metrics: concordance with ties counted 0.5, analytic random-order bounds.
- The panel constraints hold, and the planner never imports labels.

The 81 historical tests still pass; 2 GPU-dependent ones skip on CPU.

## Resources

- `/home` has 1.5 GB free.
- The laptop had just rebooted; no other job was running (the K4/K5 study runs on gvlab2 and was not touched).
- New files total under 1 MB so far.
