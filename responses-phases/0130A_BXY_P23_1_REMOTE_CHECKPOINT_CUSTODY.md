# 0130A — BXY-P23.1: remote checkpoint custody on Google Drive (read-back verified) and the P24 custody gate

Date: 2026-11-02. Gate: BXY-P23.1.

- **Start:** `a863c174` (P23); preparation commit `be8b272f` (prepared code, then BLOCKED_REMOTE_AUTH).
- **Work done:** checkpoint upload, read-back verification and P24 gate code only.
- **Not done:** no teacher query, no training, no confirmation scene.

## Verdict

**`REMOTE_CUSTODY_VERIFIED`, so P23 is now `P23_READY_FOR_AUTHORIZATION`.** The only P23 blocker (single physical disk) is closed.

| Check | Result |
|---|---|
| Remote | rclone `drive` remote `bxydrive` (Google Drive, the user's own browser OAuth); about 5.48 TB free; target folder empty before upload |
| Snapshot | `Approach_B_P23_Frozen_P21_Checkpoints_a863c17/`: `p21_runs/<run dir>/best.pt` and `RESULT.json` for the 60 frozen members, `manifests/` (frozen models, plan and analysis locks, P23 authorization proposal, environment), README, MANIFEST |
| Manifest before upload | [MANIFEST_P23_1.json](../runs/approach_b/bxy_p23_1_v1/MANIFEST_P23_1.json) (sha `72af1a55…`): 126 files, 266,933,672 bytes, every file's sha256 / arm / run id, provenance commit `a863c174` |
| Upload | `rclone copy --checksum --immutable` (no overwrite); 127 objects, 266,963,085 bytes on Drive, in 1,148 s |
| **Independent read-back** | full download into a clean directory; **126 / 126 files sha256-identical**; **60 / 60 members re-loaded from the downloaded copy** (RESULT.json sha + run id + checkpoint sha), arm by arm D / E / DIRECT-GEO / G = 15 / 15 / 15 / 15 |
| Prediction check | 3 held-out development roots per member, recomputed from the restored weights vs the stored P21 predictions: **max \|Δ\| = 0.0** (tolerance 1e-9) |
| Evidence | [REMOTE_CUSTODY_P23_1.json](../runs/approach_b/bxy_p23_1_v1/REMOTE_CUSTODY_P23_1.json) (sha `9eeb354a…`). Drive file IDs are stored only as sha256; the raw listing is kept locally outside the repository |

- **Confidentiality warning (given before upload, still true):** the supplied folder is viewable by anyone with its link. An anonymous
  request returned the folder page "rss-weights". The user chose to proceed without restricting it, so the checkpoints are downloadable
  by anyone holding the link.
  - No folder link, file ID or OAuth token appears in Git, logs or reports.
  - Sharing settings were not modified.
- **Access path:** the user's rclone (v1.60.1) is a host install; it is reached from the VS Code flatpak sandbox at
  `/run/host/usr/bin/rclone`. My own attempt to download rclone was refused by the session policy and not worked around.

## Implementation delta

- **New: [bxy_p23_1_custody.py](../bxy_p23_1_custody.py)** with `preflight`, `stage`, `upload`, `readback`, `verify_evidence` and `lock`.
  - A partial check, or a remote whose type is not `drive`, can never produce `REMOTE_CUSTODY_VERIFIED`.
- **Gate (surgical): `bxy_p24_confirm.require_authorization`.** After the existing approval, lock, code-tree and teacher checks, it calls
  `verify_evidence` on `REMOTE_CUSTODY_P23_1.json`.
  - It refuses if the evidence is missing, corrupted, unverified, not read back, from a non-Drive remote, or names different or missing
    checkpoints.
  - `LOCKS` now names the P23 plan lock, the P23.1 analysis lock, the frozen-model manifest and the custody evidence.
  - Nothing else changed: generator, teacher, scorer and models, frozen weights, ranking, data, endpoints and statistics are all untouched.
- **Successors** (the P22 and P23 files stay intact and are linked by parent sha):
  - [CONFIRM_ANALYSIS_P23_1_LOCK.json](../runs/approach_b/bxy_p23_1_v1/CONFIRM_ANALYSIS_P23_1_LOCK.json) (`cb3d67ee…`) is the P23 analysis lock with
    post-P23.1 implementation hashes (runner, engine, analysis, custody) and the explicit gate-only amendment. Endpoints, populations,
    thresholds, families and statistics are copied unchanged.
  - [AUTHORIZATION_P24_PROPOSED_P23_1.json](../runs/approach_b/bxy_p23_1_v1/AUTHORIZATION_P24_PROPOSED_P23_1.json) (`4af35a9c…`): limits are
    unchanged (90,000 CPU-s including the 3,000 CPU-s reserve, 40,000 s wall, 4 workers, 1,400 CPU-s per root, 440 slots). Its `locks_sha256`
    covers plan, analysis, frozen models and custody. The code tree is 226 top-level files (sha `5821f83a…`), plus the teacher hash and the
    unchanged per-query budget.
- **Tests:**
  - [tests/test_bxy_p23_1.py](../tests/test_bxy_p23_1.py): custody refusal cases and a positive proof; a read-back round trip through a
    fake local remote, which can never verify; a corrupted download is detected; the P24 gate refuses without verified custody, opens with
    it, and reports drift when the evidence changes after approval.
  - The P22 and P23 namespace-absence tests now accept the namespace only under an approved P24 authorization. The P23 test never calls
    the real P24 steps once P24 is authorized.

## Resources ([LEDGER.jsonl](../runs/approach_b/bxy_p23_1_v1/LEDGER.jsonl), separate from P23)

| Phase | CPU-s | Wall s |
|---|---|---|
| Preparation (probe, code, tests, staging; conservative) | 45 | 60 |
| Upload | 2.7 | 1,148 |
| Read-back verification | 6.6 | 192 |
| Regression (single-thread) | 1,019 | 1,028 |
| **Total (hash-chained, 4 events)** | **1,073** | **2,428** |

Ceiling: 3,000 CPU-s and 10,800 s wall.

## Regression

Recorded in `runs/approach_b/bxy_p23_1_v1/regression/`, single-thread:
- full suite: **740 passed, 1 skipped** (737 at P23 + 3 new);
- six archived replays: exit 0;
- hash guard: clean.

## Gate

**`P23_READY_FOR_AUTHORIZATION`.** The user's explicit, conditional P24 authorization (handoff §2) becomes effective now that read-back
custody is verified. P24 proceeds only after `AUTHORIZATION_P24.json` is committed with these post-P23.1 hashes.

STOP (gate P23.1).
