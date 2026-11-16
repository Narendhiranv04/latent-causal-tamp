# Reproducing V3.2 stage 2

All commands run from `approach_b_final/` on branch `naren/approach-b-v3-2-training`. Input and output hashes are in `resolved_config.json`, and per-host launchers are in `scripts/v32_hosts/`. Paths below use the laptop layout; other hosts differ only in `ABF_ROOT`, `V3OUT` and env paths, as shown in their launchers.

## Environment variables

| Variable | Meaning |
|---|---|
| `ABF_ROOT` | Root holding `snapshot/abf_9de85710c2a7103f` (+ `abf_v3_e8a496bc66266fca`) and `runs/p3_*` |
| `V3OUT` | Holds `v3_3/` (frozen task cVAE) and `v3_5/` (frozen V3 D, `rule_*.json`) |
| `V3_TASK_STAGE=v3_3` | Selects the frozen task sampler |
| `V32_SCORER=<dir>/p2_{dom}/D_s<k>/model.pt` | Score with a trained arm (sampler stays seed 0) |
| `V32_PART=i/k` | Score only roots with `sha256(root) % k == i` |
| `V34_DIR` | Phase C mining / items / labels directory |
| `XY_PATIENCE=60 XY_EPOCHS=60 XY_RUNS=<out>` | Matched training |

## Phase A — tests and parity

```bash
python -m pytest -q tests                                       # 31 passed
python exhaustive.py run 3d val 6 parity_M6_sub40 40            # then ex_parity.py vs the V3.2-A ex_M6_val.jsonl
python exhaustive.py run 2d val 6 parity_M6_sub12 12
python scripts/ex_parity.py <ref ex_M6_val.jsonl> <host file>   # identical decisions, |dp11| < 1e-4
# teacher parity: construct.py verify <DOM> reports/v3_2_stage2/A/parity_<d>.jsonl <W> <CPU0>   (fresh V3OUT, no cache)
python scripts/parity_compare.py A/parity_2d_ref.json A/parity_3d_ref.json <dir of <host>_<d>.jsonl>
```

## Phase B — frozen-model exhaustive physics

1. Build the deduplicated worklist from `reports/v3_2/v3_2a/<d>/NEW_SELECTIONS_TO_VERIFY.jsonl` minus every cache file (see `B/CACHE_BUNDLE.sha256`).
2. Split it with `scripts/split_todo.py todo.jsonl prefix host:weight,...`.
3. Run `construct.py verify <DOM> <host list> <W> <CPU0>` on each host.
4. Compute the table:

```bash
python scripts/v32b_phys.py <snapshot abf_9de85710c2a7103f> <V3.2-A run dir v32a> B/B_FROZEN_EXHAUSTIVE_PHYS.json "<caches>/*2d*.jsonl" "<caches>/*3d*.jsonl"
```

## Phase C — TRAIN expanded-candidate labels

```bash
V34_DIR=<dir> python v32c.py mine 2d 100 100 150 50 75 [i/k]      # shards: separate V34_DIR per shard, then concatenate mine.jsonl
V34_DIR=<dir> python v32c.py mine 3d 70 80 90 30 40
V34_DIR=<dir> V32_DEDUP_SNAPSHOT=<abf_v3_e8a496bc66266fca> python v32c.py items 2d   # and 3d
python scripts/split_items.py <dir>/<d>/items_v32c.json <done labels or -> <dir>/<d> v32c host:w,...
V34_DIR=<dir> python onpolicy.py v3label 2D v32c_<host> <W> <CPU0> <host>          # per host (unchanged teachers)
ABF_ROOT=<root with abf_v3_e8a496bc66266fca> V3OUT=<out> V34_DIR=<dir> V3_SNAP_BASE=<.../abf_v3_e8a496bc66266fca> \
  V3_SNAP_PREFIX=abf_v32_ V3_SNAP_VARIANT="V3.2 EXHAUSTIVE TOP-M TRAIN CANDIDATES (Phase C, v32c)" V3_LABEL_KIND=V32C_EXHAUSTIVE_CANDIDATE \
  python onpolicy.py v3snapshot '{"2D": "v32c", "3D": "v32c"}'                     # -> abf_v32_fb0eef4f5ff433ee
```

## Phase D — matched training

```bash
for s in 0 1 2; do for D in 2D 3D; do
  XY_PATIENCE=60 XY_EPOCHS=60 XY_RUNS=train/control  python xy.py fit <abf_v3_e8a496bc66266fca> $D D $s
  XY_PATIENCE=60 XY_EPOCHS=60 XY_RUNS=train/expanded python xy.py fit <abf_v32_fb0eef4f5ff433ee> $D D $s
done; done
```

## Phase E — exhaustive scoring and physical evaluation

```bash
V32_SCORER=train/<arm>/p2_{dom}/D_s<s>/model.pt V32_PART=i/k python exhaustive.py run <dom> val 6 <arm>_s<s>_M6_val_p<i>of<k>
python scripts/v32e_eval.py todo  <snapshot> <records dir with 2d/ 3d/> val "<caches>/*2d*" "<caches>/*3d*" <todo dir>
#   -> verify the todo with construct.py verify on parity-passed hosts, add the outputs to the caches, then:
python scripts/v32e_eval.py table <snapshot> <records> val "<caches>/*2d*" "<caches>/*3d*" E/TABLE_VAL_E3_E4.json
python scripts/v32e_failures.py <snapshot> <V3.2-A v32a dir> <records> E/TABLE_FAILURES_VAL.json "<caches>/*2d*" "<caches>/*3d*"
python scripts/v32_figs.py reports/v3_2_stage2
```

TEST regression: run the same commands with `SPLIT=test` (split argument `test`) for D-expanded seeds 0–2 only, the configuration fixed by the registered rule. Then build the TEST table with `scripts/v32e_eval.py` in table mode with split `test`.
