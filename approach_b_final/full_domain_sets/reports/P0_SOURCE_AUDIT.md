# P0 source audit and history protection

## Provenance

| Item | Verified value |
|---|---|
| Parent | `naren/rss27-mcts-sets-klt3` head `b17c67d9cd5e677fcfd1f68e8a0bb9a8c9863885` (local equals `origin`; `e9fa587c3b` is an ancestor) |
| New branch | `naren/rss27-full-domain-set-search`, created from that head; nothing merged; no edits under `approach_b_final/mcts_sets/` (`git diff b17c67d9cd -- approach_b_final/mcts_sets` is empty; 29 file hashes in `P0_FROZEN_PROTOCOL.json`) |
| Contract | `plan.md` copied byte-identical (sha256 `c11dc0d9…`) |
| Bundle | `~/abf_v34/approach_b_bundle/MANIFEST.json` sha256 `147645ee…`; every `2d/` file hash checked by `benchmark.load_bundle` |
| Public VAL | `public_val_2d.jsonl` sha256 `2c88f69b…`: 751 roots, the same file as the completed study and the K≤3 ablations |
| Public fields | `attrs, base, cell_xy, cells0, ctx, goal, goal_cell, grid, ids, legal_cells, q_ref, tid, xy0`. No K, labels, masks, witnesses, certificates, `B` or `verified_K` (`public_has_private_fields = false`) |
| Historical completed study | NULL verdict, the UNKNOWN→0 operational caveat (strict analysis inconclusive) and the 191 primary VAL roots (development evidence) are all confirmed from `P4_FINAL_DECISION.md` and `P3_PHYSICAL_VAL.md` |
| Tests | 13/13 historical tests pass; 26/26 new tests pass |

## Source facts verified by reading the code, not assumed from the plan

1. **`search.Root.legal_dests(cells)`** returns `legal_cells` minus every *originally* occupied cell, minus the current occupancy, minus the goal cell. Called on `cells0`, it gives **one common legal set for every object**, so `A_legal = O × D0`. Median per VAL root: 10 movable objects and 52 legal cells, giving 119,340 unordered K2 sets (max 308,826) or about 239k ordered sequences.
2. **Movable objects** (`Root.movable`): every object except the target whose 2D attribute `is_fixed` is 0.
3. **`placement.marginal`** returns `E_z softmax(masked decoder(c, z))` over `n_z = 64` prior draws of **z**, multiplied by the legal mask. **`propose_rule` with S1** takes `topk(6)` of `log p` over cells with p > 0.
   - The marginal is an average of softmaxes, so **every legal cell has strictly positive mass**: 0 of 352,838 legal actions on VAL have zero mass.
   - S1 samples latents, not cells, so a stratum like "`BEYOND6_NOT_IN_MC_DRAW`" **is not identifiable** for this sampler (see `P0_GAPS.md`). The uniform floor ε is still applied, as registered.
4. **`search.Sampler.propose_many`** is one batched call over all movable objects of the hypothetical scene. **`exhaustive.proposals`** calls it on `cells0` with `M = 6` and a fresh CUDA generator seeded 0. `domain.cvae_raw` rebuilds exactly that call (same features, scalers, task context, mask, object order and generator) and returns the full marginal. Its `topk` equals the archived top-6 on **751/751** VAL roots, so the top-4 prefix matches as well (`P0_PARITY.json`). Marginal sums lie in [0.99999991, 1.00000008].
5. **`search.Scorer.score(root, seqs)`** scores complete ordered sequences from the original root view. `[]` returns `p_noop`. No intermediate scene is ever encoded.
6. **`xy.choose`, `exhaustive.Selectors` and `construct.assignments`** are reused through the completed study's `search_sets.Pool` (enumeration in `construct.assignments` order) and `search_sets.choose` (tested equal to `xy.choose`). Real-root parity holds: `EXACT4` here reproduces the sealed historical `EXACT_K2` decision on 6/6 EVAL roots (`test_real_roots_…`).
7. **Evaluator:** `scripts/v32b_phys.outcome` is the operational rule (an `UNKNOWN_*` status carrying value 0 counts as a failure). The strict rule (a value counts only under VERIFIED / CERTIFIED_*) lives in `analyze.strict_labels`. The teacher (`benchmark.teach` → `evaluate._verify_job`) is used only after sealing.

## Engineering decisions taken during the audit

- **Module name.** The plan suggested `search.py`; the module is named **`fsearch.py`**. A local `search.py` would shadow the frozen `approach_b_final/search.py` that `benchmark` and `exhaustive` import, which is the failure mode behind the voided P5B batch.
- **Loading the frozen `search_sets.py`.** It is loaded by explicit file path, never through `sys.path`, because `mcts_sets/run.py` would otherwise shadow this package's `run.py`. A test hit exactly that, and it was fixed.
- **Wrappers, no edits.** Nothing in the frozen code or in the completed study was edited; all extensions are wrappers in `full_domain_sets/`.
