# Local work track — status

**Branch:** `approach-d-v1` (local only; not pushed or merged).
**Base:** G2b `43fd985`.
**Report:** `responses-phases/0103_AD_LOCAL_COMPARISON_AND_G2C_LITE.md`.

## What is done

| package | status | artifacts |
|---|---|---|
| L1 archived A/B/C/D comparison | **done**, reproduced exactly from saved P17 records | `runs/approach_d/local/ARCHIVED_P17.json`; figures 01–04 |
| L2 G2c-lite catalog additions | **done**, bounded: 303 / 500 offline attempts, 272 / 1,800 CPU-s | `runs/approach_d/local/catalog/` (CATALOG_LOCAL_*, CONNECTORS_*, GRAPH_C1..C4), `CATALOGS.json`, `COMPILE_LEDGER.json`, `AVAILABILITY_*.json`, `ATTRIBUTION_L3.json`; figure 06 |
| L3 D vs geometry vs uniform on the precompiled backend | **done** (12 DEV roots × C1–C4 × 3 guides) | `PILOT_L3.json`, `PILOT_L3_C4.json`, `FIRST_MOVE_HITS.json`, `D_F12.json`; figures 05–06 |
| Tests | `tests/test_approach_d_local.py`, 6 tests; all Approach D tests 41/41 | full regression: see below |

**Headline results:**
- **Archived, historical solver backend:** D's diagnosis is good, with AUROC 0.952 and 6/27 false alarms vs 11–17/27 for A/B/C. Its search success equals geometry's (71 = 71 / 90).
- **New precompiled backend, DEV pilot:**
  - catalog availability, not guidance, binds;
  - every guide repairs 1/12 roots on every catalog;
  - small offline additions did not raise target-action availability (15/51 states certify, 1/51 is reachable);
  - D's first move hits a verified-repair object 7/7, vs 6/7 for geometry and 4/7 for uniform (n = 7).

## Reproduce (local workstation, repo root)

```bash
python ad_local.py                                   # L1: ARCHIVED_P17.json + figures 01-04 (seconds; read-only on P17 files)
python -c "import ad_local as L; L.compile_search_pairs(); L.compile_target_diversity(); L.compile_connectors(); L.build_catalogs()"
python -c "import ad_local as L; L.availability(); L.attribute(); L.pilot()"
python -c "import ad_local as L; L.compile_state_connectors(); L.build_c4(); L.availability(cats=('C4',), name='AVAILABILITY_C4'); L.pilot(cats=('C4',), name='PILOT_L3_C4')"
python -c "import ad_local as L; L.first_move_hits(); L.fig_chain(); L.fig_g2c()"
python -m pytest -q tests/test_approach_d_local.py tests/test_approach_d_g2b.py tests/test_approach_d_g2a.py tests/test_approach_d.py
```

Compile steps are offline and charged to `runs/approach_d/local/COMPILE_LEDGER.json`; the ledger refuses to exceed the `[local_pilot]` budget. Every runtime step runs under `ad_runtime.forbid('raise')`.

## Verification

- **Full regression** (`runs/approach_d/local/regression/`): **543 passed, 0 failed** (513 historical + 30 Approach D), all 6 archived replays clean, `P3A_REGRESSION_CLOSED` (774 s).
- `config.toml`, the P13–P17 labels, checkpoints, archived reports and the 6 replay fixtures are unchanged (tested with `git diff` checks).

## Not done (by design)

- No new losses and no retraining.
- No D(A) / D(B) temporary-target queries.
- No inference-time IK, planning or trajectory generation.
- No 442-query benchmark.
- No conversion of the historical 0–4-relocation protocol to the 7-action dataset protocol.
- No exhaustive motion library.

## How this joins the server dataset track

- **Server work runs separately.** The server dataset bootstrap (balanced 2D and xArm7 3D B/D datasets, binary teacher labels, 7-action protocol) runs on `user1@10.4.25.63` under `/data/user1/rss_ebm_dataset/`. Its code lives on a separate local branch, `dataset-bd-v1`, in its own worktree; this branch never imports it.
- **When that dataset exists:**
  1. Build the precompiled library from its offline teacher witnesses: many alternatives per (state, target), plus near-base transit connectors. These are the two measured bottlenecks of §6.
  2. Re-run `ad_local.pilot` (unchanged guides, matched budgets) on its held-out roots.
  3. Keep D's two losses unchanged.
