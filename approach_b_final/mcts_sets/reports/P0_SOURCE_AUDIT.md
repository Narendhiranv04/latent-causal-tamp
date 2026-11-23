# P0 source audit: original-root set search, K ≤ 2

Branch `naren/rss27-mcts-sets-klt3`, created from `naren/k3-postablation-validation` @ `e9fa587c3b9dd850f1fbbc454b20e4e00a35c4eb`. The parent SHA was verified immediately before branching. The worktree is a sparse checkout of `approach_b_final/*.py`, `config/`, `ablations_k3`, `validation_k3`, `tests`, `scripts/v32b_phys.py` and `mcts_sets/`.

## Branch heads (verified against `origin`, 2026-11-23; all equal to the prompt)

| Lineage | Head | Used for |
|---|---|---|
| V3.4 final benchmark | `c72eb1ef759a` | frozen bundle and protocol; 2D fresh cohort 51.8 % [47.2, 56.1] on 394 roots (report l.41). **The fresh cohort is not read** |
| K≤3 ablations | `4aee79892996` | VAL 2D FULL 57.1 [52.5, 61.7] (FINAL_REPORT l.83); its verifier cache is reused for deduplication only |
| Post-ablation validation (**parent**) | `e9fa587c3b9d` | the label-blind budget curve 9.7 / 28.1 / 38.7 / 50.1 / 57.1 (K1–K3; VALIDATION_REPORT l.92); its verifier cache is reused for deduplication |
| kgt3 exec composition | `171eb65cc42a` | negative K>3 history only. Its window scores are **not** used |
| DISCO-grid final | `56b71743e932` | `baselines/disco_grid/mcts.py` is training-only, stateful MCTS with physical transitions (`env.transition`, physical STOP queries). **Not reused.** Only the UCB form and the progressive-widening form are borrowed as ideas |
| Analytical baselines | `7ae0e54b7d84` | an oracle-assisted physical-search regime; context only, not a matched control |
| Order-dependency audit | `8e1c1a247e9c` | caution only: physical order dependence is not attributed to p11 |

## Implementation facts relied on (read from code)

- **Proposals:** `exhaustive.proposals` makes one batched `Sampler.propose_many(root, root.cells0, root.movable, 6, torch.Generator(cuda).manual_seed(0))`. M4 is the top-4 prefix: four destinations **per eligible object**. The sampler is the frozen `TaskCVAE scratch_all`, loaded by `benchmark.load_bundle`, which asserts every 2D bundle hash against `MANIFEST.json`.
- **Scorer:** `search.Scorer.score(root, seqs)` builds one view from the **original root** with complete ordered sequences (`XY.make_view(... [], xs ...)`). It returns `p11 = psucc`, `py` and `px`; the no-op is `p_noop`.
- **Grammar:** `construct.assignments(D, k)` returns unordered assignments with distinct objects and destinations. `exhaustive.stream` returns all permutations. `benchmark.legality` enforces the static cell grammar.
- **Selection:** `xy.choose` and `exhaustive.Selectors`: the no-op gate first; then the admissible pool p ≥ η; then argmin (round(−log p + αm + βD + γJ, 12), m, D, signature). The frozen rule is `noop_gate 0.5, eta 0.3, alpha = beta = gamma = 0`.
- **Proposal priors:** the frozen proposal API returns **ranked lists only**; no per-destination probability is retained. `PUCT_RANK` (secondary) would therefore be a rank prior. It was not run in this phase (see `P0_GAPS.md`).

## Empirical P0 (`P0_EMPIRICAL.json`)

- **Bundle:** all 2D bundle hashes match `MANIFEST.json`. The public VAL file `public_val_2d.jsonl` (sha `2c88f69b…`) is byte-identical to the K≤3 ablation's public VAL file.
- **K≤3 parity vs the frozen V3.4 VAL predictions** (laptop RTX 5060, torch 2.9.1, 40 hash-selected roots): proposals 40/40, decisions 40/40, max |Δp11| = 0, max |Δp_noop| = 0. The historical full record is 751/751 (`~/abf_v34/parity/PARITY_2d_gpu_vs_v33.json`).
- **Scorer batch-composition invariance** (12 roots, 4,576 sequences): max |Δp11| is 6.6e-7 (single vs batch) and 5.4e-7 (shuffled batch). It is float32 noise, not exact invariance. Score-table replay is therefore equal to live scoring up to ≤ 7e-7. Decision parity, live vs replay, is measured directly on the timing subset.
- **Public schema:** the public rows carry only `root_id`, `domain` and `inputs` (cells, attributes, legal cells, target, goal, `q_ref`, context). There are no K, labels, masks, witnesses or split fields.

## Privacy boundary

- **Planner inputs:** the planner (`search_sets.py`, `run.py`) reads only the public file and the frozen bundle.
- **Private material:** the private index (K, masks, raw-root paths) and the teacher caches live in `~/mcts_sets_private`. They are read only by the evaluator (`analyze.py manifest|physical`), after predictions are sealed.
- **Tests:** they assert that the planner modules import no teacher module (`evaluate`, `teacher2d`, `bxy_teacher`, `teacher_long`, `mink`) and reference no private field.
