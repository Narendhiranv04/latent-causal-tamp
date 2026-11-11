# 0028 — P9-L0: source, evidence and likelihood audit (nonmutating)

**Actual result.**
- **Gate:** `runs/p9/P9_L0_GATE.json` → **PASS** (11/11 checks). Zero teacher calls.
- **State:**
  - local `HEAD` = `origin/main` = `f9a6de0`; nothing staged;
  - every P8 checkpoint matches its manifest (P8a 46, P8c 21);
  - all 21 P8c checkpoints reproduce their published validation and disclosed-test metrics **exactly** (|Δ| = 0.0).
- **Baseline:** **323/323** tests and **6/6** archived replays (628.4 CPU-s, guarded).
- **Three findings shape P9-L1:**
  1. **One physical query, several variables.** In the ABC7 per-candidate blocks, the omission `zO[r,t]` of one repair is the same teacher query as the repair `zR[r∖t]`, and one omission is often shared by several repairs. On the P8c learner view, 794 sequence queries occur in two or more candidates. The P8 model treats each copy as its own variable; its copies of one event disagree by up to **0.30 (B-full) / 0.35 (C-full)** on validation.
  2. **The P8 multi-loss reuses evidence.** Each distinct decided label enters the seven P8 terms **5.93 times on average** for B/C (max 25); **90 %** of labels are used more than once.
  3. **DINOv2 features are used.** Report 0027 / `P8_DECISION.md` said otherwise; that line was wrong (corrected below).

Previous turn sync: `f9a6de0695d83699a2115d4898e5c78063852073`.

## 1. Sources read and repository state

- **Documents.** Methodology v1.8 (`sha256:65ed6218…`) and Guide v2.0 (`sha256:94302b33…`) were found in the repository root, not in `instruction-phase-md/`. Following the contract, they were imported **unchanged** (hashes identical, root copies kept). The P9 contract is `sha256:061c27cb…`.
  - v1.7 / v1.9 were read for preserved contracts only.
  - Reports 0024–0027 and `P8_DECISION.md` were read; hashes are in `runs/p9/l0/source_state.json`.
- **Repository.** `main`; local = remote = `f9a6de0`; 0 staged and 0 modified tracked files.
  - The two pre-existing user deletions of root PDFs are untouched.
  - 85 untracked paths (the user's documents and uncommitted P7/P8 checkpoints) are left alone.
- **Hashes** of the 19 relevant sources, configs and policies (including `teacher_opneg.toml`) and of the four learner views are recorded. L1 re-verified that no P8 source changed.
- **Baseline regression** (`runs/p9/l0/regression`):
  - 323 passed and 0 failed; six replays passed (g1_robot, g1_hardening, g2_interventions, g3_repairs, g3_5_initial_scene, g4a_evidence_audit); 628.4 CPU-s.
  - The call counter shows only the existing unit-test fixtures' planner calls; no teacher query on any dataset.
  - **First attempt:** it was launched without the `countcalls` plugin, so pytest did not start (replays passed). That attempt is kept in `regression_attempt1_missing_plugin/` and was rerun with the plugin.
- **Disclosure.** `joint_likelihood.py` and `tests/test_p9_joint.py` were *drafted* while the baseline ran. Neither was imported or executed before this gate passed, and pytest had collected its tests before the files existed (323 collected).

## 2. What the data actually contain (`runs/p9/l0/identity.json`)

| learner view | roots | empty-only roots | slot labels V / C / B / UNKNOWN / NOT_RUN | sequence queries in ≥ 2 candidates | `zO` = another `zR` | `zO` shared by ≥ 2 repairs | largest alias component (candidates) |
|---|---|---|---|---|---|---|---|
| P8c dev (train + validation) | 190 | 94 | 1,713 / 3,305 / 1,034 / 60 / 1,530 | 794 | 676 | 433 | 28 |
| P8c test (disclosed) | 24 | 12 | 163 / 212 / 61 / 34 / 74 | 56 | 44 | 28 | 11 |
| P7 dev | 118 | 58 | 1,148 / 2,381 / 755 / 13 / 1,066 | 561 | 479 | 309 | 28 |
| P7 test (disclosed) | 24 | 12 | 210 / 510 / 162 / 2 / 334 | 125 | 113 | 69 | 28 |

Label counts are slot occurrences (a reused query is counted per slot). V = VERIFIED, C = CERTIFIED (scoped), B = BUDGET_INFEASIBLE (OPNEG-v1 operational).

**Identity checks.** Every check below is zero in all four views:
- contradictory labels for one query;
- an empty repair with a `zR` slot;
- the `z0` query appearing in a repair slot;
- `zR` label ≠ candidate label, or `z0` ≠ empty-repair label;
- scene-slot sets differing across a root's candidates;
- UNKNOWN / NOT_RUN carrying a 0/1 label.

**What this implies.**
- **`z0 ≡ zR[∅]` holds by construction.** The empty repair has no `zR` slot, and ABC7 reads its success from P(z0).
- **The open identity is between repair-scoped slots.** `zO[r,t]` and `zR[r∖t]` (and `zO` across repairs) are one physical event.
- **Empty-only roots.** Of the 94 in P8c dev, **86 are originally feasible** (`z0 = 1`, witnessed), 3 are budget-negative and 5 are unlabelled. They are the only F0 originally-feasible controls, and they carry one bit each with no repair catalogue.

## 3. Factor families → code → variables (B/C; `abc7_models.ModelBC7`)

| family | module(s) | variables touched | notes |
|---|---|---|---|
| F1 static unary / pair | `unary`, `pairh` (+ shared encoder) | **none** (endpoint descriptors of r) | r-only offset E_static; cancels from P(z \| r) |
| F2 ordered sequence | B: `pairo`, `mix`, `order_s`; C: `h0`, `gru`, `order_s` | unary on `zR[r]` | C's GRU replaces B's prefix pairs |
| F3 scene intervention | `scene` (unary); `pair_scene` (structured `z0`–`zS[I]`) | `z0`, `zS[I]` (root block) | edited poses and the fixed q0 |
| F4 omission | unary = **`order_s` applied to r∖t** (shared with F2); `pair_omit` (`zR`–`zO[t]`) | `zO[r,t]` | omission unary is parameter-shared with F2 |
| F5 generic coupling | `cpl` (scene–scene, scene–repair, `zO`–`zO` pairs); `ho_u`, `ho_s`, `ho_q` (higher order) | any pair; all bits of a block | `quadratic` drops HO; `structured` drops all of F5 |
| travel J | `cost` | none | readout of the repair summary g |

Diagram: `visualizations/p9/P9_factor_instances.png` (SHA-256 in `index.json`). It shows a tiny root in full / quadratic / structured / none, with one thick circle where the omission of A from r1 *is* the repair r2.

## 4. P8 multi-loss: gradient reach and evidence reuse

**Reach** (`p8_term_gradients.json`, seed-0 P8c checkpoints, 12 training roots):
- All seven terms reach the shared DINOv2 projection and dominate through it (B-full, e.g., scene 18.8 and omit 10.6 of totals 20.0 and 11.1).
- **`pair_scene` (structured `z0`–`zS`) receives ≈ 0 from every term in every P8c B/C checkpoint** (≤ 0.007).
- Static BCE reaches only `unary` / `pairh` (+ encoder); `cost` only the J head.

**Reuse** (`p8_label_use.json`, 178 training roots, 1,232 distinct decided labels): the number of times each distinct label enters `static…pool`:

| arm family | mean uses / label | used > 1 time | max |
|---|---|---|---|
| B / C | 5.93 | 90.4 % | 25 |
| SF | 4.07 | 85.7 % | 13 |
| A | 3.81 | 91.7 % | 8 |

**Sources of reuse.**
- **task BCE + omission BCE:** a 1-move repair's label is charged again as the omission of every 2-move repair containing it;
- **effect MSE:** `z0` enters once per scene edit and per omission pair;
- **pool term:** `-log P(z*|r)` re-charges the scene bits once per positive, fully decided candidate.

## 5. DINOv2 (`dino_path.json`; correction to 0027)

- **The features are real.** Every P8 arm takes frozen, mask-pooled DINOv2-small features (`facebook/dinov2-small@ed25f3a3`; 1,294 objects × 384 dimensions; none all-zero) through a trainable 384→32 projection, together with supplied symbolic geometry.
- **The projection matters.** B-full seed 0:
  - the projection's weight norm is 4.11, and its P8-loss gradient is 33.3;
  - zeroing the visual features moves validation success probabilities by **0.23** on average (max 0.70);
  - shuffling them across objects moves them by 0.15.
- **Correction.** Report 0027's support-matrix row "H-vision: BLOCKED — every arm consumes the symbolic scene state; no image input" is **wrong**. The correct statement: appearance features were used jointly with geometry. No geometry-only arm was trained, so an **independent appearance benefit is untested**. The `vision=False` ablation is planned for L3 (`P9_NEXT_DECISION.md`). Report 0027 itself stays immutable.

## 6. Discrepancies between Methodology v1.8 / Guide v2.0 and the code (old evidence unchanged)

1. **Repeated physical queries (Guide invariant 6).** They are separate variables in the per-candidate blocks and disagree up to 0.35. This is resolved in L1 by an equality-aware root model.
2. **`zR[∅] = z0` (Guide invariant 5)** — satisfied by construction.
3. **Duplicated evidence in the P8 objective** (§4) — replaced in L1 / L2 by one root likelihood.
4. **F4 omission unary is not a separate network.** It is `order_s` on the rebuilt sequence. An L3 "remove omission unary" ablation therefore needs a dedicated head, or must be declared as removing slot evidence only.
5. **Structured `z0`–`zS` pair untrained in P8c** (≈ 0 gradient). P8's "structured vs none" contrasts are therefore weak evidence about this factor.
6. **Static BCE counts endpoint-identical candidates** (order permutations) more than once. L1 / L2 deduplicate them by endpoint.
7. **Originally feasible roots** exist only as single-bit roots. A real F0 test (false-empty and unnecessary-work controls with a repair catalogue) needs new data.
8. **E_static cancellation and ranking energy agree with Methodology §5.3:** `E = E_static + T softplus(-l_R)` with uniform ρ. The P8 lexicographic comparator is unchanged.

## 7. Artifacts and accounting

- **Code:** `p9_run.py` (L0: `source_state`, `identity`, `p8_label_use`, `reproduce_p8c`, `dino_path`, `alias_disagreement`, `gate_l0`); `p9_viz.py` (`factor_instances`). Nothing in the P8 code was modified.
- **Evidence:** `runs/p9/l0/{source_state, identity, p8_label_use, p8c_reproduction, p8_term_gradients, legacy_alias_disagreement, dino_path, audit_done}.json`, `runs/p9/l0/regression/`, `runs/p9/P9_L0_GATE.json`.
- **Compute:** audit 20.5 CPU-s; regression 628.4 + 51.9 CPU-s (first attempt); figures < 5 CPU-s. 0 teacher calls.
