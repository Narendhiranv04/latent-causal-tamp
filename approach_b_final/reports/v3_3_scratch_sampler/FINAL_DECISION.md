# V3.3 final decision — from-scratch corrective-placement sampler

**Split.** All decisions here were made on VALIDATION. The exposed TEST was **not** used in V3.3. The fresh cohort is prepared but **not run**, so there is no confirmation claim.

## Answer to the registered question (H1)

**Does V3.2 successful-repair supervision improve a randomly initialized task cVAE?**

**No detectable effect: NULL in both domains.** The comparison holds fixed the architecture, initialization, optimizer steps, VAL checkpoint rule, proposal RNG, frozen D-expanded scorer, exhaustive M4 construction, frozen rule and teachers. S-expanded (V3.2 snapshot) vs S-control (V3 snapshot), physically verified, 3 sampler seeds, 0 UNKNOWN:

| Domain | S-control | S-expanded | Δ task [95 % CI] | Δ NONE abstention |
|---|---|---|---|---|
| 2D | 55.1 % | 55.0 % | −0.1 [−2.1, +2.0] | +0.2 [+0.0, +0.7] |
| 3D | 78.9 % | 79.1 % | +0.2 [−2.6, +2.6] | +0.6 [−1.7, +3.4] |

**Supporting observations** (`DATA_AUDIT.md`, `SCRATCH_TRAINING.md`, `PROPOSAL_RESULTS.md`, `PHYSICAL_VAL_RESULTS.md`):
- The expansion added genuinely new positive targets: +879 (2D) and +854 (3D) unique X = Y = 1 assignments, giving training examples 7,591 → 9,729 and 4,782 → 6,807.
- It changed the sampler in measurable but small ways:
  - slower overfitting;
  - VAL −ELBO −0.006 (2D) and −0.026 (3D);
  - M4 known-success coverage +2.0 [−0.3, +4.3] (2D) and +0.3 (3D);
  - about 5 2D failures moved from "no known success in pool" to "ranking error".
- None of this changed verified top-1 task success. The 2D seed-0 pilot gain (+2.7) did not replicate (seeds 1 and 2: 0.0 and −2.0).

**Interpretation.**
- About 880 extra positive assignments (+28–42 % examples) are not enough to move a scratch sampler's verified outcome.
- The frozen D-expanded scorer's ranking errors, rather than candidate generation, remain the larger 2D failure class for the scratch samplers.
- The registered robustness check (other scorer seeds) was conditional on a conclusive result, so it was **not run**.

## Registered final scratch configuration (VAL rule)

**Rule:** take the higher seed-mean task success unless NONE abstention is more than 3 points worse; the sampler seed is fixed at 0.

| Domain | Arm | Task / abstain (seed mean) | Frozen sampler checkpoint (sha256) |
|---|---|---|---|
| 2D | **S-control** | 55.1 / 94.9 vs expanded 55.0 / 95.1 | `scratch_all_s0` = `fe8f3eee4234b9bbe8fec9193ddf0c3e426b9859d9648bc81e514c3f5904f5b9` |
| 3D | **S-expanded** | 79.1 / 79.3 vs control 78.9 / 78.7 | `scratch_all_s0` = `6a0e26c47781fefe5e9fb84043bf772230b22758cb21f47358836d11e84be472` |

- Both margins are far inside noise. Which arm "wins" is a tie-break, **not** a finding.
- Paired with the frozen D-expanded s0, exhaustive M4 and the frozen rule.

## Production sampler: not replaced

The historical Q2-pretrained, fine-tuned `q2init_all` s0 is a different-initialization and different-data **reference**, not a matched ablation. On the same VAL roots and the M4 protocol, against the scratch arms:
- **Verified task success:** about 1.3–1.5 points higher (2D 56.4 %, 3D 80.5 %); no CI excludes 0.
- **Known-success M4 coverage:** significantly higher (2D +6.3 to +7.5 points, 3D +2.1 to +2.3).
- **3D NONE abstention:** 3.4–4.0 points higher (n.s.).

**Recommendation.**
- Keep `q2init_all` + D-expanded (exhaustive M4) as the production pipeline.
- A scratch sampler is a viable, fully from-scratch alternative at about 1.4 points lower VAL task success (n.s.), if the paper requires no Q2 pretraining. That choice is a trade-off for the user, and this milestone does not make it.

## What was not done (deliberately)

- **No D / E / G / DIRECT retraining**, and no joint sampler and scorer update. Calibration was diagnosed instead: D-expanded is equally over-confident on all samplers' pools.
- **No M-specific models and no M5/M6 physical runs.** Coverage rises with M for all arms, but there was no M-dependent failure to justify them.
- **No selector retuning. No TEST run.**
- **No full fresh-cohort generation.** It needs an explicitly authorized CPU budget; see `FRESH_COHORT_PREPARATION.md`.

## Next scientifically justified step

The scratch-sampler question is closed as a null at this data scale. Two options remain, and both need user approval:
1. **Run the prepared fresh family-disjoint confirmation cohort** for the production configuration (`q2init_all` + D-expanded, M4). Optionally include the frozen scratch configuration above as a second pre-declared arm. This is the only route to an unbiased headline number.
2. **If sampler improvements are still wanted:** a matched experiment on the *amount* of positive supervision (a dose-response curve) or on Q2 pretraining with expanded fine-tuning. Each would be a new registered experiment with its own control. The present data cannot distinguish "the extra labels are uninformative" from "too few to matter".

## Reproducibility recipe

```bash
# laptop: data audit + tests (CPU only)
CUDA_VISIBLE_DEVICES= ABF_ROOT=<root with data/q2_<dom>/scalers.json> python scripts/v33_data_audit.py BASE CONTROL EXPANDED DATA_AUDIT.json
V33_SNAPS=BASE:CONTROL:EXPANDED CUDA_VISIBLE_DEVICES= ABF_ROOT=... python -m pytest tests/        # 38 passed
# girish: 12 fits (registered budget)
scripts/v33_hosts/girish_fit.sh "3d 2d" "control expanded" "0 1 2"
# girish: teacher-free proposals + coverage
scripts/v33_hosts/girish_props.sh;  python scripts/v33_proposals.py cover BASE "<caches>/*/*2d*.jsonl" "<caches>/*/*3d*.jsonl" COVERAGE_VAL.json NAME=DIR ...
# girish: exhaustive M4 scoring (per arm / sampler seed / shard), D-expanded s0
scripts/v33_hosts/girish_ex.sh v33/<arm> task:scratch_all <seed> 0 <dom> <i>/<k> <cpu> 4 <arm>_s<seed>_D0_M4_val
# todo -> verify on parity-passed hosts -> table
python scripts/v33_eval.py todo  BASE G2 G3 TODO_DIR  control:0,1,2:RUN/{d}/control_s{s}_D0_M4_val_p*.jsonl expanded:0,1,2:...
scripts/v33_hosts/lap_verify.sh <dom> V3OUT TODO W CPU0  |  scripts/v33_hosts/girish_verify.sh <dom> V3OUT TODO W CPU0
python scripts/v33_eval.py table BASE G2 G3 TABLE_PHYSICAL_VAL.json control:... expanded:... q2init:0:<V3.2 E_records>/{d}/expanded_s{s}_M6_val_p*.jsonl
python scripts/v33_figs.py reports/v3_3_scratch_sampler TABLE_PHYSICAL_VAL.json
```

**Code changes** (backward-compatible; old defaults unchanged):
- `placement.fit_task`: explicit train and VAL snapshots, device, and fixed-step mode with provenance (`state_sha`, `prov`).
- `placement.load_task`, `search.Sampler`, `search.Scorer`: default device from `ABF_DEVICE`.
- `exhaustive.setup` / `run`: `V33_SAMPLER` and `V33_SAMPLER_SEED`, plus a CPU guard.

## Changelog

| Commit | Content |
|---|---|
| `964ba7a24d` | Pre-registration: code switches, data audit, tests, `EXPERIMENT_REGISTRY.json` (before any training or teacher query) |
| `e9509d1597` | 12 fits, coverage, two-host parity, eval scripts |
| `45385384af` | Data, training and proposal reports; fresh-cohort exclusion manifests |
| `3f6611be6e` | Physical VAL results, final decision, records, labels, figures |
| (final commit) | Fresh-cohort generation pilot results and revised budget, checksums |
