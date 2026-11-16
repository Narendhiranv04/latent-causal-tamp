# V3.2 stage 2 — execution manifest

- **Hashes:** source, input and model hashes are in `resolved_config.json`.
- **Experiments:** hypotheses, controls and status are in `EXPERIMENT_REGISTRY.json`.
- **Commands:** see `REPRODUCE.md`.

## Timeline (IST, 2026-11-17)

| Time | Event | Commit |
|---|---|---|
| ~01:50 | Read-only host preflight (5 hosts); branch created from V3.1-4 `82de92e682`; V3.2-A cherry-picked; 31/31 tests | — |
| ~02:30 | Experiment registry pre-registered (before any Phase C label or new-scorer outcome) | `b6de8c432b` |
| 02:00–02:50 | Teacher parity on laptop, gvlab, girish, gvlab2 (all PASS); Phase B verification (668 queries) | `8fc9926eb7` |
| 02:20–04:01 | Phase C: pilot, full mining (Blackwell), TRAIN labelling on 4 hosts; dataset frozen 04:01 | `ebf5ee09da` |
| 04:02 | Snapshot `abf_v32_fb0eef4f5ff433ee`; D-expanded trained (D-control trained at 02:35) | `ebf5ee09da` |
| 03:00–05:20 | Phase E exhaustive VAL scoring (6 models) and physical verification (4,875 queries) | `eb9fb499f7` |
| ~05:00 | TEST-regression rule registered before the 2D VAL outcomes of the trained arms | `0f438dfb95` |
| 05:20– | TEST scoring (D-expanded only, per rule) and TEST verification | (this report) |

## Host allocation journal

**Rule followed on every host.** At least 4 logical CPUs were kept outside our jobs. All jobs ran at `nice 10`, with pinned CPUs (`taskset`) and `OMP_NUM_THREADS=MKL_NUM_THREADS=1`. No other user's process was touched. We stopped our own processes only, by PID or exact pattern, when rebalancing. Load was re-checked before each batch.

| Host | Role | Peak V3.2 use | Other workloads observed | Notes |
|---|---|---|---|---|
| laptop (`pop-os`, 32 thr, ~31 GB RAM) | Teacher (2D / 3D), pilot mining, exhaustive scoring (RTX 5060) | ≤ 26 single-thread processes | Interactive use; ~21 GB RAM used by other programs | Memory-limited; 3D workers ≤ 12; low-memory watchdog |
| gvlab (24 thr) | Teacher only | ≤ 24 workers at peak during rebalancing (load ≤ 18–20) | furqan (both 4090 GPUs, ~3–5 CPUs); DISCO paths untouched | GPUs never used |
| gvlab2 / cstar (48 thr) | Teacher only | ≤ 30 workers | `learned_reap` on the shared account (~14 CPUs, 5090 at 84 %) | GPU not used; home disk 98 % full, so only a few MB written |
| Blackwell / server (24 thr, RTX PRO 5000) | Mining, matched training, exhaustive scoring | ≤ 16 pinned processes | yadu `reap` training (~4 threads, ~1–2 GB GPU) | Never touched sajid's queues or `/data/sajid` |
| girish-laptop / gvcstar (24 thr, RTX 3080 Ti) | Teacher (2D / 3D), exhaustive scoring | ≤ 20 processes | none | 3D teacher ~5× slower per worker, so 3D work moved off |

**Rebalancing events.** Each took the following steps:
1. Stop our own process by PID.
2. Recompute the exact remaining roots from the result files.
3. Re-split by root.

Events:
- gvlab 3D labels: 44 of 153 roots done when moved; remainder to gvlab + gvlab2.
- girish 2D labels: one duplicate pilot root stopped.
- girish control-2D verification: 51 of 198 roots done; remainder to 4 hosts.
- D-control TEST scoring stopped: not required by the registered rule.

Interrupted roots wrote no partial lines (atomic per-root JSONL appends), and every merged file was parse-checked.

## Job hygiene

- **Query identity.** A query is keyed by (domain, root_id, ordered sequence). Y is evaluated once per canonical endpoint and X per ordered sequence (`onpolicy._v3_job`, `construct.verify`).
- **Cache precedence.** A decided label is never overwritten by an unresolved one.
- **Conflicts.** Any conflict between decided labels from two hosts aborts the merge (`v32b_phys.labels`). None occurred:
  - 1,552 V3.1-4 duplicates agreed;
  - all parity samples agreed;
  - the snapshot builder's assertion found no conflicts with existing labels.
- **Work assignment.** Each worklist is split by root with a manifest (`split_todo.py` / `split_items.py`). Every result file is SHA-256 recorded (`B/PHASE_B_LABELS.sha256`, `E/PHASE_E_VAL_LABELS.sha256`, snapshot lock).
- **Unresolved labels.** Timeouts and unresolved outcomes stay MISSING / UNKNOWN. The count was 0 across Phases B, C and E.
- **Granularity.** The journal is per-root, not per-query: `construct.verify` appends one line per finished root. A crash loses at most the in-flight roots, which are then recomputed from the result files. Contract §3 asks for a per-query write-ahead journal; this implementation uses the existing per-root atomic records instead.

## Resource totals

| Item | 2D | 3D |
|---|---:|---:|
| Phase B teacher queries / CPU-h | 574 / 4.4 | 94 / 0.9 |
| Phase C TRAIN candidates / CPU-h | 4,477 / 19.9 | 2,680 / 23.2 |
| Phase E VAL teacher queries / CPU-h | 3,889 / 19.7 | 986 / 12.7 |
| Parity samples (4 hosts) | 4 × 30 | 4 × 16 |
| Exhaustive VAL scoring, 6 trained models (process-h) | 28.5 | 1.0 |
| Matched training (12 fits, GPU-min) | ~4.1 | ~2.0 |
