# V3-1: direct one-shot candidate construction on the frozen V2 models

**Hypothesis tested (plan V3 §5.3, T1):**
1. With identical frozen V2 weights, a single sampler pass on the original scene, followed by complete-sequence construction, batched scoring and one selection, is a valid replacement for the old bounded prefix search.
2. If it is not, the deficit should come from the proposal set rather than the scorer.

Nothing was trained. Every selected repair below was verified independently with the unchanged finalized teachers, and 0 selected repairs are unverified.

## 1. What was implemented

`construct.py` is the single new V3 module.

- `run_root` makes **one** batched sampler call per root, over all eligible movable objects, on S0. The sampler is never re-queried on an edited scene.
- `build` constructs every statically legal ordered sequence of 1–3 distinct objects with pairwise distinct destinations.
  - All permutations are kept as separate X candidates.
  - The constructor enumerates completely when the valid count fits `B_score`.
  - Otherwise it uses the label- and model-blind budgeted constructor: all K1 actions, then the remaining budget split evenly between K2 and K3. Each share is filled with whole, uniformly sampled unordered assignments **and all k! of their orders**. Seeding is per root.
  - Exact valid counts per length come from inclusion–exclusion. They are recorded together with the counts built and scored.
- Scoring is batched (chunks of 8,192) through the unchanged `search.Scorer`, which always scores from the ORIGINAL root. The endpoint Y is shared by all permutations.
- Selection is unchanged: `xy.choose`, with the no-op gate, η admission, and argmin −log p11 + α m + β D + γ Ĵ.
- `planner_calls` is 0 by construction.
- `verify` reuses `evaluate._verify_job`. The frozen V2 verify cache is read-only; V3 results go to `$V3OUT/verify_<dom>.jsonl`, and witness stores are redirected to V3.
- `legacy` converts old search outputs into the same record format, so all arms share the same selection, verification and metrics.
- `summary` reports:
  - top-1 task, repair, no-op and abstention;
  - known-assignment ingredient recall;
  - presence of a known or verified success in the scored set;
  - conditional selection success;
  - attribution (success / ranking failure / unresolved), never "proposal failure" without labels;
  - budgets and latency;
  - a paired root-cluster bootstrap of the difference to a reference arm.
- The old `oneshot` arm is reproduced with the unchanged `evaluate.py select … oneshot`. It remains a *bounded prefix-tree expansion* with 12 expansions and is reported separately from direct construction.

Tests (`tests/test_v3.py`; 17 / 17 tests in the full suite pass on gvlab2):
- toy n = 3, M = 4 gives exactly 12 + 96 + 384 = 492 sequences, with orders kept;
- inclusion–exclusion counts match brute force on 30 random destination sets with overlaps;
- the budgeted constructor never exceeds B, keeps every K1 action and whole permutation groups, and is deterministic per seed key;
- the one-pass contract holds with an instrumented sampler and scorer: one sampler pass, on S0 only; the no-op is scored; planner calls are 0; exactly one selection, which is one of the scored candidates.

**Parity of the frozen V2 models on gvlab2** (torch 2.9.1 / RTX 5090 vs gvlab torch 2.5.1 / RTX 4090), from `v3_1/PARITY_V2_GVLAB2.json`:
- re-scored candidates differ by max |Δp11| = 8e-7 (2D) and 1.5e-6 (3D);
- re-running the old iterative search reproduced 40 / 40 identical candidate sets and selections per domain.

## 2. Results on valsub (seed 0)

Setup:
- Models: frozen V2 = the V1 Q2 cVAE sampler plus the V2-retrained coupled D and the V1 travel head.
- Rules: frozen V2 rule, 2D `{gate 0.5, η 0.3, β 0.1}` and 3D `{gate 0.5, η 0.3}`.
- Roots: 300 in 2D, 291 in 3D.
- Task n = 180 (2D) and 173 (3D). Δ is the paired root-cluster bootstrap 95 % CI vs V2 iterative.

| 2D | Task | K1 / K2 / K3 | Repair | No-op | Abstain | Scored (median) | Unique actions | Latency (median) | Δ task vs iterative |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| V2 iterative | 33.9 | 61.7 / 35.0 / 5.0 | 22.0 | 93.3 | 95.0 | 412 | 247 | 0.33 s | — |
| V2 bounded oneshot | 27.2 | 55.0 / 23.3 / 3.3 | 20.2 | 93.3 | 95.0 | 397 | 39 | 0.24 s | −6.7 [−13.3, −0.6] |
| Direct M4 B512 | 23.3 | 50.0 / 20.0 / 0.0 | 15.6 | 93.3 | 95.0 | 512 | 39 | 0.04 s | −10.6 [−17.2, −4.4] |
| Direct M4 B4096 | 23.9 | 50.0 / 20.0 / 1.7 | 15.6 | 93.3 | 93.3 | 4,095 | 39 | 0.37 s | −10.0 [−16.7, −2.8] |

| 3D | Task | K1 / K2 / K3 | Repair | No-op | Abstain | Scored (median) | Unique actions | Latency (median) | Δ task vs iterative |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| V2 iterative | 51.4 | 56.6 / 50.0 / 48.3 | 39.0 | 80.0 | 93.1 | 120 | 57 | 0.32 s | — |
| V2 bounded oneshot | 44.5 | 60.4 / 46.7 / 28.3 | 31.4 | 80.0 | 91.4 | 111 | 16 | 0.21 s | −6.9 [−13.9, 0.0] |
| Direct M4 B512 | 49.1 | 60.4 / 58.3 / 30.0 | 30.2 | 80.0 | **100** | 508 | 16 | 0.06 s | −2.3 [−11.0, +5.2] |
| Direct M4 B4096 | 52.6 | 58.5 / 58.3 / 41.7 | 32.6 | 80.0 | **82.8** | 1,506 (78 % complete) | 16 | 0.08 s | +1.2 [−6.9, +8.7] |

Proposal-side diagnostics (task roots):

| | 2D ingredient recall (known assignment) | 2D success in scored set (known / known + verified) | 2D conditional selection | 3D ingredient recall | 3D success in scored set | 3D conditional selection |
|---|---:|---:|---:|---:|---:|---:|
| V2 iterative | 21.4 % | 3.3 / 53.3 % | 63.5 % | 14.0 % | 5.2 / 69.9 % | 73.6 % |
| V2 bounded oneshot | 3.5 % | 3.3 / 39.4 % | 69.0 % | 5.8 % | 5.2 / 54.9 % | 81.1 % |
| Direct M4 B512 | 3.5 % | 3.3 / 35.6 % | 65.6 % | 5.8 % | 5.2 / 61.8 % | 79.4 % |
| Direct M4 B4096 | 3.5 % | 3.3 / 40.6 % | 58.9 % | 5.8 % | 5.8 / 68.2 % | 77.1 % |

## 3. Interpretation

1. **3D:** direct one-shot construction matches the old iterative search (Δ = +1.2, CI −6.9 to +8.7) at a quarter of its latency (0.08 vs 0.32 s), with a single sampler pass.
   - It is clearly better than the old bounded oneshot at K2 / K3.
   - More scored candidates cost **NONE-abstention**: 100 % at B = 512 vs 82.8 % at B = 4096. A larger pool exposes more confident false positives, which is the plan's predicted coverage-vs-false-positive tension.
2. **2D:** direct construction is significantly worse than iterative (−10 points) and not better than the old bounded oneshot.
   - The cause is on the proposal side. One pass of the goal-blind Q2 cVAE at M = 4 contains every action of the known successful assignment at only **3.5 %** of 2D task roots, versus 21.4 % for the iterative search. Iterative re-queries about 100 times per root and sees 247 distinct actions instead of 39.
   - Raising B from 512 to 4,096 does not help (23.3 → 23.9 %), because the extra budget only recombines the same 39 actions.
   - 2D K3 is ≈ 0 % for every one-shot arm.
3. **Ranking is not the main 2D deficit.** Given a known or verified success in the scored set, the direct arms select a verified success 59–66 % of the time (iterative: 64 %). Confident false positives still exist: the 3D example shows p11 = 1.00 with physical Y = 0. Those are the target of the V3-4/5 matched-distribution retraining.
4. **These results are consistent with the plan's premise** that the M = 4 goal-blind proposal distribution is the bottleneck for the one-shot method, in 2D especially. They motivate V3-2 (M sweep and sampling rules) and V3-3 (task-conditioned cVAE).

## 4. Caveats (do not over-read)

- **Valsub is in-sample for the iterative arm.** The frozen V2 rule was tuned on these valsub roots with the iterative arm's candidates. A held-out comparison on `valrest` (validation roots outside valsub, never used for any stopping-rule tuning) is running and will be reported as a V3-1 addendum.
- **Confirmed-success presence is biased by label availability.** The iterative arm's candidates were verified far more often, since V2's 72-rule tuning verified their selections. The known-label-only column (3–6 %) is the unbiased lower bound, and unresolved candidates are **not** counted as proposal failures.
- Results are from a single seed. The frozen V2 rule was not re-tuned for direct construction, and that tuning belongs to V3-2 / V3-5.
- 2D negatives include teacher `UNKNOWN_PLANNER` Y = 0, exactly as in all V1 / V2 labels: protocol-relative zeros, not universal impossibility.
- No test-split data was used.

## 5. Artefacts

- `v3_1/SUMMARY_2d.json`, `v3_1/SUMMARY_3d.json`: all metrics.
- `v3_1/PARITY_V2_GVLAB2.json`.
- `v3_1/examples_2d.png`, `v3_1/examples_3d.png`: per root, the one-pass proposal density, the top-5 complete candidates with p11, and the selected ordered repair with its verified physical X / Y. Recorded outputs only; no robot motion is drawn.
- Per-root records (plan §8.2 schema, with stored candidates) are on gvlab2 under `~/abf_v3/runs/v3_1/{2d,3d}/`. The V3 verify caches are `~/abf_v3/runs/verify_{2d,3d}.jsonl`.
- Drivers: `scripts/v3_1.sh` and `scripts/v3_1b.sh` (valrest).

**Next:** first the V3-1 valrest addendum. Then V3-2:
- M ∈ {4, 8, 12, 16} at matched scored budgets;
- sampling rules S1–S4 on frozen models: true top-M of the MC-estimated marginal, Gumbel-top-k without replacement, temperature, and a legal-uniform or band mixture;
- teacher-free ingredient recall over all validation roots, with top-1 physical verification only on the selected configurations.

## Addendum (2026-11-16 04:40 IST): held-out `valrest` comparison

`valrest` = the validation roots outside valsub: 451 in 2D and 73 in 3D. No V1, V2 or V3 stopping rule was ever tuned on them. Setup:
- the same four arms, seed 0, with the frozen V2 models and rule;
- every selected repair physically verified (0 unverified);
- 2D teacher queries: 729; 3D: 152.

Sources: `v3_1/SUMMARY_{2d,3d}_valrest.json`.

| valrest | 2D task (n = 233) | 2D K1 / K2 / K3 | Δ vs iterative [95 % CI] | 3D task (n = 47) | Δ vs iterative [95 % CI] | Latency 2D / 3D |
|---|---:|---|---|---:|---|---|
| V2 iterative | 25.3 | 56.7 / 36.7 / 2.7 | — | 51.1 | — | 0.25 / 0.33 s |
| V2 bounded oneshot | 21.5 | 56.7 / 21.7 / 2.7 | −3.9 [−9.0, +1.3] | 53.2 | +2.1 [−12.8, +17.0] | 0.22 / 0.29 s |
| Direct M4 B512 | 17.6 | 55.0 / 11.7 / 0.9 | −7.7 [−12.4, −3.0] | 53.2 | +2.1 [−12.8, +14.9] | 0.07 / 0.07 s |
| Direct M4 B4096 | 18.0 | 51.7 / 16.7 / 0.9 | −7.3 [−12.4, −2.6] | 61.7 | +10.6 [−6.4, +27.7] | 0.28 / 0.07 s |

Findings:
- **Iterative was inflated in-sample.** Its in-sample valsub advantage shrinks on held-out roots, from 33.9 % to 25.3 % in 2D.
- **2D conclusion unchanged.** With the goal-blind Q2 sampler, one-pass direct construction remains significantly worse than iterative (about −7 points), almost entirely at K2 / K3. Known-assignment ingredient recall is 2.6 % vs 22.9 %.
- **3D conclusion unchanged.** Direct construction matches or exceeds iterative at about a fifth of the latency.
- **3D valrest is small.** It has only 47 task roots, no K1 and no NONE roots, so its CIs are wide.
- **Conditional selection is high.** Given a known or verified success in the scored set, the scorer picks a verified success 71–96 % of the time in 2D. The 2D deficit is a **proposal-coverage** problem, which motivates V3-3.
