# G4 run status: local witness catalogs and causal repair

**Branch and source:**
- branch `approach-d-v1`, source revision `99587dea3` (G3 `804e3ddf7` plus a status-file scrub);
- G4 adds new `ad_g4.py` and `tests/test_approach_d_g4.py`;
- G4 changes, additively, `ad_causal.py` and `approach_d.toml` (`[g4]`).

**Report:** `responses-phases/0105_AD_G4_LOCAL_WITNESS_CATALOG_AND_CAUSAL_REPAIR.md`.

**Server evidence.** No SSH, server or GPU use. Every command below runs on the local workstation and reads only `runs/p13..p17` archives, plus the read-only P14 lookup index.

## Reproduce (in order)

```bash
python3 -c "import ad_g4 as G; G.baseline(); G.inventory()"      # G4.0 fingerprints, G4.1 WITNESS_MANIFEST
python3 ad_g4.py W_ROOT 6          # G4.2 teacher re-run of the 30 DEV witnesses (ledgered)
python3 ad_g4.py W_TRANSFER 6      # 32 train roots x first 2 witnesses (ledgered, 250 CPU-s held back)
python3 ad_g4.py home              # empty-workspace home connectors for transfer cores (ledgered)
python3 ad_g4.py graphs            # GRAPH_W_ROOT / GRAPH_W_TRANSFER = C3 + pieces
python3 ad_g4.py diagnose          # G4.3 AVAILABILITY.json (witness supplied for diagnosis only)
python3 ad_g4.py evaluate C3       # G4.5 five frozen policies, reproduction check vs G3
python3 ad_g4.py evaluate W_ROOT   # G4.5 development demonstration
python3 -c "import ad_g4 as G; G.teacher_check([...])"            # the 4 sequences in TEACHER_CHECK_D_PREFERENCES.json
python3 ad_g4.py figures           # visualizations/approach_d/g4/01..05
python3 -m pytest -q tests/test_approach_d_g4.py
python3 run.py g4c-lf-p4-regression --out runs/approach_d/g4/regression --cpu 3000 --wall 8000
```

The offline stages refuse to start a chunk once the ledger cap is reached, so they are bounded. Re-running them appends to the ledger; delete `runs/approach_d/g4/` first for a clean rerun.

## Catalogs and hashes

| Catalog | Graph hash | Contents |
|---|---|---|
| C3 (frozen, G3) | `sha256:c3ae684f341641337b92f7e17a73f70b472f94dc4ac22bc99cbb0dc87656a191` | `runs/approach_d/local/catalog/GRAPH_C3*` (unchanged) |
| W-ROOT | `sha256:f4f71d39565bd1061c09a77eac02ab46320380af6ec39833863eaa3741a87e2b` | C3 + 62 connectors, 26 relocation cores and 28 T cores from the 30 DEV witnesses (engineering ceiling) |
| W-TRANSFER | `sha256:4252fc76cf32e54c11ca93f895431c5259d8c5b99edc39c8cca5fb975ad8af13` | C3 + 98 connectors, 40 relocation cores and 56 T cores from 32 train roots, + 156 home connectors |

All three catalogs live in `runs/approach_d/g4/catalogs/`. Each witness piece is listed in `*_PIECES.json`, with its stage-scene validation verdict, and its arrays are in `*_PIECES.npz`.

## Compile ledger (`runs/approach_d/g4/COMPILE_LEDGER.json`)

Caps: 400 fresh planner / IK invocations or 1200 CPU-s, whichever comes first.

| Entry | Invocations | CPU-s |
|---|---|---|
| teacher_rerun:W_ROOT | 59 | 453.2 |
| teacher_rerun:W_TRANSFER | 85 | 494.4 |
| transfer_home_connectors | 156 | 1.0 |
| teacher_check:D_preferences | 6 | 137.5 |
| **total** | **306** | **1086.1** |

## Result files

| File | Content |
|---|---|
| `baseline/BASELINE.json`, `baseline/APPROACH_D_TESTS.txt` | Gate 0 fingerprints and the pre-G4 Approach D tests (52/52 pass) |
| `manifest/WITNESS_MANIFEST.json` | cohorts A and B, and the transfer pool |
| `diagnostics/AVAILABILITY.json` | per-root, per-catalog, per-witness step outcomes and the waterfall |
| `diagnostics/TEACHER_CHECK_D_PREFERENCES.json` | the offline teacher check of D's preferred placements |
| `eval/EVAL_C3.json`, `eval/EVAL_W_ROOT.json` | full traces for 5 policies × 12 roots |
| `regression/regression_result.json` | full suite and the six archived replays |

## Headline numbers

- **Witness ceiling (blocked roots):** C3 0/9, W-ROOT 9/9, W-TRANSFER 0/9 (coverage-censored).
- **W-ROOT blocked repaired:** D_CAUSAL_G3 6/10, D_CAUSAL_G4_SWEEP 6/10, D_BLOCKER_ONLY 8/10, GEOM_CAUSAL 8/10, UNIFORM 7/10. This is a development demonstration, confounded because geometry's stored T sweeps are witness-derived.
- **Runtime:** 0 forbidden calls everywhere.
