# V3.3 fresh confirmation cohort — preparation (no confirmation run)

**Status: PREPARED, NOT RUN.** This document is a protocol and cost estimate only. No fresh-cohort outcome exists, and none was used for any V3.3 decision. All numbers below are VALIDATION-free generator ledger statistics, read on the user's laptop; no forbidden host was accessed.

## 1. How the existing roots were generated (frozen generators)

| | 2D planar 8×8 | 3D shelf 6×6 |
|---|---|---|
| Entry point | `dataset_bd_classquota/code/run_2d_plus.py` (launcher `run_2d_plus.sh`; run from `code/latent-causal-tamp`, `PYTHONPATH=dataset-bd:code:latent-causal-tamp`) | `shelf66_v3/run_shelf66_full.py` (run from `$SRC/code`); NONE via `run_shelf66_none.py` → `trim_none66_v3.py` |
| Seed / id | `seed = sha256(["BD_GEN_V1","2d",name,wave,slot])[:8]`, `root_id = 2d-<name>-w<wave>-s<slot>` (`bd_core.py:105-107`) | same scheme, domain tag `3ds66` |
| K teacher | `BD2D_TEACHER_V1:DetPhysics(P16_FAST)`: removal subsets in size order; budget 150 motion checks, 8 online moves, 3 goal plans, 6 transit plans; repair pool 5; CPU cap 1,200 s (1,500 s exact layouts); `config_hash 90d3eb68e8a42108` | `BD3DS66_TEACHER_V2`: RRT 5,000 iterations, pool 6, 8 sequence tries; wall cap 4,200 s plus a 3,600 s audit; `config_hash 8d521b1f6d23db23` |
| Not counted | DEPENDENT roots | DEPENDENT and INCONSISTENT roots |
| Env | `abf_v3_laptop/env2d` | `abf_v3_laptop/env3d` (Python 3.13.11, MuJoCo 3.16.0); `MUJOCO_GL=disable`, one thread per worker |

**Splits.**
- **2D:** union-find over family, identical layout and conversion origin, then a class-stratified greedy 70/15/15 split (seed `LAUNCH_READY_2D_V1`).
- **3D:** frozen first-cohort manifest plus union-find over family and layout (`select_final3d.py`).
- **Leakage:** the V3.3 data audit (`DATA_AUDIT.json`) found 0 families and 0 layouts in two splits in both snapshots.

**Important: `parent_family_id` is a factor-template hash, not a scene lineage.**
- **Definition:** `fam-sha256([domain, {8 factors}])[:10]`, from `bd_core.py:104-108`.
- **Templates:** 8,856 exist; existing ledgers use 4,371 (2D) and 1,570 (3D).
- **Untouched templates by K:**
  - 2D: K0 1,072, K1 1,029, K2 931, K3 567.
  - 3D: K0 430, K1 725, K2 626, K3 287; 3D NONE requests: only 63 of 432 untouched.
- **Consequence:** a *family-disjoint* cohort must restrict `bc.SPECS` to untouched templates. That keeps the frozen construction and teacher but shifts the factor mix, which is a decision for the user (option B: define a new lineage id and accept template overlap).

## 2. Disjointness requirements

A fresh root must avoid all of the following, and each is checked by assertion after generation:
- **Namespaces:** 2D `plus2d`, `plus2d-srv`, `conv-*`, `D2_*`, `D2H*`; 3D `lap`, `lap3`, `lap4`, `lap5`, `srv`, `srv3`, `srv5`, `lapN(t)`, `srvN(t)`, `D3_*`, `D3H_*`.
- **Family ids:** every family id in all existing ledgers and in snapshots `abf_9de85710c2a7103f`, `abf_v3_e8a496bc66266fca` and `abf_v32_fb0eef4f5ff433ee`.
- **Construction seeds:** collisions with existing ones (32-bit).
- **Fingerprints:** every existing `root_sha256`, plus a layout fingerprint sha256 over (object cells, target, goal).

## 3. Protocol (locked before any fresh outcome)

1. **Build exclusions.** Build `EXCL2D.json` and `EXCL3D.json` (family ids, seeds, layout fingerprints) from the ledgers and snapshots above, and commit their hashes.
2. **Generate.** Use new namespaces `fc2d` / `fc3d`, an empty output directory and the frozen code and teachers. A wrapper only filters `bc.SPECS` to untouched templates and overrides `QUOTA`.
   - **2D:** K1/K2/K3 = 116/116/167 (≈ 400 task roots) plus K0 ≈ 180 and NONE ≈ 145.
   - **3D:** K1/K2/K3 = 54/93/93 (240 task roots) plus K0 ≈ 78 and NONE ≈ 62.
3. **Label and build rows.** Run Approach B finalized X/Y labelling and replay, then build snapshot rows with the same `masks` conventions (`contracts.py`).
4. **Evaluate once.** Run the frozen configuration from `FINAL_DECISION.md` exactly once, with all selections physically verified. Fresh outcomes are never used for training, threshold or model choice.

## 4. Measured generation cost (ledger statistics) and budget

CPU-seconds per *counted* root:

| Class | 2D | 3D |
|---|---|---|
| K0 | ≈ 25 | ≈ 145 |
| NONE | ≈ 45 | ≈ 750 (trimmed; dense-construction ledger not available locally) |
| K1 | ≈ 490 | ≈ 450 |
| K2 | ≈ 920 | ≈ 1,590 |
| K3 | ≈ 1,690 (28 % yield) | ≈ 7,700–11,600 |

Sources: 2D ledger of 11,720 attempts / 981 CPU-h; 3D ledger of 2,983 attempts / 1,237 CPU-h.

| Item | Estimate |
|---|---|
| 2D generation (400 task + K0 + NONE) | ≈ 127 CPU-h |
| 3D generation (240 task + K0 + NONE) | ≈ 270–370 CPU-h |
| X/Y labelling and replay (Approach B finalized protocol) | to be measured in the pilot |
| Evaluation (exhaustive M4 scoring + selected-repair teachers) | ≈ 1–2 GPU-h + < 10 CPU-h |
| Wall time on the two authorized laptops (≈ 20 girish + ≈ 12 laptop threads) | ≈ 2.5–4 days |

**Missing locally:**
- the dense 3D NONE store and ledger (`dataset_2500_raw_shelf66v3_none_dense`);
- the 2D/3D dependence-enrichment step (dep2d/dep3d/hard3d), which ran on gvlab and is needed to match the 60 : 40 dependent K2/K3 mix.

Without enrichment, the raw 2D generator gives about 31 % dependent roots, and the cohort would be reported as such.

## 5. Launch commands (pilot form; full run = larger QUOTA)

```bash
# 2D (laptop CPU, 4 workers)
L=$HOME/abf_v3_laptop/root/mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code
OUT=$HOME/abf_v33/fresh/fc2d/raw; mkdir -p $OUT; cd $L/latent-causal-tamp
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 PYTHONWARNINGS=ignore PYTHONPATH=$L/dataset-bd:$L:$L/latent-causal-tamp nice -n 10 \
$HOME/abf_v3_laptop/env2d/bin/python -c 'import sys,json,bd_core as bc,run_2d_plus as R
ex=set(json.load(open(sys.argv[1])));bc.SPECS[:]=[s for s in bc.SPECS if "fam-"+bc.sha(["2d",{k:s[k] for k in bc.FACTORS}])[:10] not in ex]
R.QUOTA.update({"NONE":2,"0":2,"1":2,"2":2,"3":2,"4":0});R.K4_MODE="harvest"
sys.argv=["x","--out",sys.argv[2],"--name","fc2dp","--workers","4"];R.main()' EXCL2D.json $OUT
```

The 3D command is analogous: `run_shelf66_full.py` with `QUOTA.json` / `K4_MAX_RUNNING=0` in the output directory, the domain tag `3ds66` in the family filter, then `run_shelf66_none.py` and `trim_none66_v3.py` for NONE.

## 6. Pilot

(filled in after the throughput pilot)
