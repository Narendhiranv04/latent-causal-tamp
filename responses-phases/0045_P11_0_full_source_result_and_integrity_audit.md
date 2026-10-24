# 0045 — P11-0: source-to-result and integrity audit of P10

**Actual result.**
- **Gate:** `runs/p11/P11_0_GATE.json` → **PASS** (9 / 9 checks). The audit was read-only, starting from HEAD = origin/main = `0a5aa4d`.
- **What was re-derived:** every central P10 number recomputed from code and recorded evidence alone, without any new physical teacher call.
  - The blind evaluation reproduces **bit-identically**.
  - The P1 contrasts and the four Holm-adjusted p-values match exactly.
  - All 975 arm × seed choices map to the 255 deterministic episodes with zero mapping errors.
- **Discrepancy confirmed:** **one**, the H9 overwrite. The 200 recoloured validation / blind records share 100 root keys, so the frozen snapshot holds 100 H9 entries per run, and palette P2 overwrote palette P1. It affects only the H9 appearance claim and is corrected (evaluation-only) in 0046.
- **Other issues:** two accounting / format issues, both explained below. None affects any headline result.

## 1. Evidence-to-source matrix

| claim (P10) | source (function) | artifact | unit / n | provenance | prereg | planner policy | recomputed |
|---|---|---|---|---|---|---|---|
| 80 / 35 / 65 split; P10a and history train-only | `p10b_prereg.roster`, `p10c_train_eval.build_records` | `runs/p10b/SPLIT_MANIFEST.json` (hash OK), `dataset_trainval.pt` | roots: 190 hist + 14 P10a + 80 P10b train, 35 val, 65 blind | — | yes | — | yes (disjoint root ids; unique seeds / fingerprints) |
| blind records carry no labels | `build_records` | `dataset_blind.pt` | 65 roots | — | yes | — | yes (0 labels) |
| H3 constructor change (V1 → V1.1) | `p10b_scenes.try_root` | batch plans | V1 roots: 3 train + 1 val; all 9 blind H3 are V1.1 | development evidence only | revision recorded (`P10B1_GATE_REVISION.json`) | — | yes |
| 69 checkpoints | `train_job`, `train_d` | `runs/p10c/ckpt/*.pt` | 69 | — | yes | — | 69 / 69 SHA-256 match (records store bare hex) |
| frozen snapshot before unseal | `p10d_execute.freeze` / `unseal` | `predictions.json` `sha256:52a2d278…`, commit `162338e` | — | — | yes | 0 physical calls | hash OK; commit time precedes `UNSEALED` |
| 255 episodes = 975 choices | `p10d_execute.jobs` / `episodes_batch`, `p7_oneshot.worker` | `episode_jobs.json` (hash OK), per-batch ledgers | 255 deterministic physical episodes; 975 arm × seed choices, 204 of them abstentions (no episode) | — | yes (cache rule) | one committed choice, no fallback | yes; each committed sequence equals its choice |
| P1 TOP1 B 0.718, SF 0.385, A 0.585, C 0.718, G+M 0.831 | `p10e_report.p1_eval` | `P1_TOP1.json` | 65 roots, seed mean per root | physical episodes | yes | G+M planner-assisted, separate | exact |
| Holm P1–P4 | `p1_eval` | `P1_TOP1.json` | 4 primaries | — | yes | — | exact (Holm p 7.8e-6, 0.0117, 1.0, 0.604) |
| H1, order, omission, NLL endpoints | `p10e_report.blind_eval` | `BLIND_EVAL.json` | 9 / 26 / 52 / 65 roots | proof-grounded only for H1 and order | yes | — | bit-identical recompute (`runs/p11/audit/BLIND_EVAL_recomputed.json`) |
| ablation contrasts | `blind_eval` | `BLIND_EVAL.json` | 65 roots | — | arms yes; multiplicity exploratory | — | exact (exploratory, no family correction in P10e; see 0047) |
| H9 shift about 0.16 | `freeze` + `blind_eval` | `predictions.json` h9 entries | **only one palette per root retained** | — | yes | — | **DEFECT**, corrected in 0046 |
| regression 404 / 404 + 6 / 6 | `p10b_dataset.regression` | `runs/p10b/regression/regression_result.json` | — | fixture planner calls only | — | fixtures counted separately | read OK |

## 2. Label provenance and scope reminders

- **Blind statuses:** 211 VERIFIED, 415 CERTIFIED, 125 BUDGET (operational, policy-relative), 20 UNKNOWN.
- **Proof-grounded only:** κ (H1) and order use only VERIFIED / CERTIFIED components.
- **Omission and NLL** include BUDGET labels as operational zeros. P10e reported them pooled, and stratified only in the common metrics.
- **FIRST_MOVER scope:** this placement-stage certificate is scoped to *the assignment* (this mover as first mover to this destination) under the declared 48-direction grasp family with a centred grasp. It is **not** a universal impossibility of placement.

## 3. Accounting and format issues (explained; no result impact)

1. **Training ledger:** the guard ledger shows 52,504 CPU-s; true training compute is **21,859 CPU-s**. The difference is the threaded preliminary runner's shared `RUSAGE_CHILDREN`. This was disclosed in 0041 / 0043.
2. **Checkpoint hash format:** checkpoint SHA-256 values are stored without the `sha256:` prefix. Content matches for all 69.
3. **Censored episode:** one TOP1 episode (root `p10b_2026111044`, the one re-run after the runner restart) was guard-censored and has no `result.json`. Its ledger outcome is `UNRESOLVED_CENSORED`, counted as a failure. This is consistent.
4. **Inference time unit:** process CPU seconds per root (`time.process_time`), single thread, on blind roots.

## 4. Gate

PASS on every check:
- HEAD = origin;
- split counts;
- manifest and sealed hashes;
- blind unlabelled and disjoint;
- 69 checkpoints;
- snapshot hash and order;
- episode mapping;
- P1 / Holm exact;
- blind-eval identical.

Downstream quantitative claims are **unblocked**. P11 compute so far: 110 CPU-s (audit_eval).
