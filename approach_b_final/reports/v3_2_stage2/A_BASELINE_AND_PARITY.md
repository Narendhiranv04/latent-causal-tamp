# V3.2 stage 2 — Phase A: integration, baseline and parity

## Source

- **Branch.** `naren/approach-b-v3-2-training` was created from `naren/approach-b-v3-1-validation` at `82de92e682` (V3.1-4, the latest; re-fetched, no newer work).
- **Integration.** The three V3.2-A commits from `naren/approach-b-v3-2-audit` at `b2b8012969` (re-fetched, no newer work) were cherry-picked with no conflicts:
  - `07edb8a1ca` → `c4d1e63f6a`
  - `73326a36c5` → `b6dd794edf`
  - `b2b8012969` → `a421f54909`
- **Scope of V3.2-A.** It only added files (`exhaustive.py`, `tests/test_v32.py`, reports, scripts). No existing module was modified, so the V3.1-4 code is unchanged.
- **Changes made in stage 2.** All are default-preserving: unset variables reproduce the old behaviour byte for byte.

| File | Change | Purpose |
|---|---|---|
| `onpolicy.py` | `V34_DIR`, `V3_SNAP_BASE`, `V3_SNAP_PREFIX`, `V3_SNAP_VARIANT`, `V3_LABEL_KIND` | Reuse the V3-4 TRAIN labelling and snapshot builder for V3.2 instead of duplicating them |
| `xy.py` | `XY_PATIENCE` | Matched arms run a fixed 60 epochs |
| `exhaustive.py` | `V32_SCORER`, `V32_PART` | Score a trained D on the identical frozen sampler stream; shard roots across processes |
| `v32c.py` (new) | TRAIN-only exhaustive-pool miner and label-blind item selector | Phase C |
| `scripts/v32b_phys.py` (new) | Phase B physics analysis | Phase B |

- **Teachers.** No teacher, model architecture or selector was edited. `construct.py` is `c9da937d` and `evaluate.py` is `18fb3814` on every host. `teacher2d.py` and `contracts.py` are byte-identical across all hosts.

## Tests

`pytest tests` gives 31 passed, both after integration and after the stage-2 changes. The suite covers:

- exact enumeration and counts;
- nested M4 ⊂ M5 ⊂ M6 membership;
- every K2 / K3 order retained;
- all 72 selectors equal to `xy.choose` across M, ties and chunk boundaries;
- the V3 / V3.1 core tests.

The V3.2-A real-root parity files are unchanged: `reports/v3_2/PARITY_M4.json` (exhaustive M4 equals the complete capped path), plus the M5 independent-pass equality on 100 roots and the 220 / 293 old-path roots identical (`V3_2A_REPORT.md`).

## Exhaustive-inference host parity

Blackwell (`server`, RTX PRO 5000) re-ran exhaustive M6 on validation subsets and was compared with the V3.2-A laptop records (`A/EXHAUSTIVE_PARITY_BLACKWELL.jsonl`). The selections are identical for every root, every M and all 72 rules, with matching candidate counts and known-success-in-pool counts.

| Domain | Roots | Decisions compared | Identical | Max \|Δp11\| |
|---|---:|---:|---:|---:|
| 3D | 40 | 8,640 | 8,640 | 1.8e-7 |
| 2D | 12 | 2,592 | 2,592 | 3.0e-7 |

Phase C mining is also host-deterministic: on the 24 pilot roots, 3D mining on Blackwell reproduced the laptop pilot exactly (proposals, pool size, decisions at M4/M5/M6, high-p11 list and seeded reservoir draws).

## Teacher parity (`A/TEACHER_PARITY_V32.json`)

**Predeclared sample.** It was drawn from the V3.1 gvlab reference cache on validation selections, with a fixed seed:

| Category | 2D | 3D |
|---|---:|---:|
| Z = 1 | 8 | 4 |
| X = 0, Y = 1 | 8 | 4 |
| Y = 0 | 8 | 4 |
| Shared-endpoint opposite-order pairs | 3 | 2 |
| **Total** | **30** | **16** |

The reference cache contains no unresolved labels, so timeout semantics could not be sampled.

**Procedure.** Each host verified the sample with no cache, and its labels were compared with the reference: X, Y and, for 3D, resolution.

| Host | Environment | 2D | 3D |
|---|---|---|---|
| laptop (`pop-os`) | `~/abf_v3_laptop` env2d / env3d | 30 / 30 PASS | 16 / 16 PASS |
| gvlab | venv313 / approachb3d_mock env | 30 / 30 PASS | 16 / 16 PASS |
| girish-laptop (`gvcstar`) | `~/abf_v314v` exact laptop copies | 30 / 30 PASS | 16 / 16 PASS |
| gvlab2 (`cstar`) | `~/abf_v2` env2d / env3d, frozen root `~/abf_v3/frozen` | 30 / 30 PASS | 16 / 16 PASS |

Only these four hosts contribute physical labels. Blackwell contributes GPU scoring and training only.

## Host inventory and allocation (read-only preflight, 2026-11-17 ~01:50 IST)

| Host | CPU / load | GPU | Decision |
|---|---|---|---|
| gvlab | 24 threads, load 6–8 (furqan) | 2 × 4090 both 100 % furqan | Teacher CPU only, ≤ 12 workers; GPUs not used |
| gvlab2 / cstar | 48 threads, load ~13.5 (`learned_reap` on the shared `long-horizon` account), 32 GB swap in use, home disk 98 % | 5090 84 % in use | Teacher CPU only, ≤ 24 workers; GPU not used; only a few MB written |
| Blackwell / server | 24 threads, yadu `reap` training (4 threads, ~1.3 GB GPU) | RTX PRO 5000 48 GB | GPU scoring / training; ≤ 13 pinned single-thread processes |
| girish / gvcstar | 24 threads idle | 3080 Ti idle | Teacher CPU ≤ 19 workers |
| laptop / pop-os | 32 threads; RAM-limited (~8 GB available, swap in use) | 5060 | Teacher CPU ≤ 10–12 workers; pilot mining |

On every host at least four logical CPUs stayed outside our jobs at all times. All jobs ran with `nice 10` and pinned CPUs, and no other user's process was touched.

## Worklist produced

Phase B needed 574 2D (339 roots) and 94 3D (81 roots) new teacher queries, after deduplicating V3.2-A's 644 / 145 unique selections against the 52-file hash-attested cache bundle (`B/CACHE_BUNDLE.sha256`).
