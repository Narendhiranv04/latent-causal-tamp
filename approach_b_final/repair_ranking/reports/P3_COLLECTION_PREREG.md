# P3 pre-registration: targeted TRAIN interventions

This was sealed before any teacher call. The manifest is `P3_MANIFEST.jsonl` and its seal is `P3_MANIFEST.SEAL.json`, with manifest sha256 `931e4599…` and jobs sha256 `884449ba…`.

## Authorization and budget

- **Owner authorization, 2026-11-25:** up to 1,800 new 2D TRAIN ordered queries and 12 teacher worker CPU-hours, on gvlab2 with at most 32 workers.
- **Plan:** exactly 1,800 queries.
- **Stopping and retries:** the run stops at whichever cap is reached first. There are no retries, and no interrupted job is resubmitted.

## Roster

- **Who:** 360 original TRAIN roots, 190 legacy K1 and 170 legacy K2, chosen in sha256('XYRR_P3_ROSTER|'+root) order.
- **Eligibility:** only roots whose raw file exists in the teacher mirror (2,563 of 3,500 TRAIN roots).
- **K is used only to stratify the roster.** It never enters a model.
- **Exclusions:** no VAL, CONFIRM, TEST or V3.4-cohort root.

## Candidates

All candidates come from public TRAIN S0 inputs, the frozen cVAE marginal and the frozen s0 scorer. Every query is a legal K ≤ 2 original-grammar sequence that is not already labelled in the TRAIN snapshot. Queries are filled by deterministic round-robin over roots; unused quota rolls over to RANDOM.

| Category | Queries | What is queried |
|---|---|---|
| HIGHCONF | 540 | Highest-p11 unlabelled sets (best order), drawn from the EXACT12 pool plus 600 score-independent full-domain draws per root. A high score is a hypothesis, not a negative label. |
| DEST | 450 | A verified positive TRAIN anchor (X = Y = 1, original labels) with one destination replaced by a rank 5–6, 7–12 or >12 cell. Object set and length are kept. |
| OBJSET | 360 | Omission of one move from a K2 anchor; substitution of one object, keeping the destination; or addition of a compatible move to a K1 anchor. |
| ORDER | 270 | The other order of already-labelled K2 sequences or of top HIGHCONF K2 sets (same endpoint). |
| RANDOM | 180 | Score-independent uniform legal sets, alternating lengths 1 and 2. |

**Realized mix:**
- Length 1: 867; length 2: 933.
- Worst rank: 1–4 = 361, 5–6 = 491, 7–12 = 507, >12 = 441.
- 353 of the 360 roots have a verified anchor.

## Teacher and merge

- **Teacher:** unchanged `benchmark.teach` → `evaluate._verify_job`, using the k3abl env, code and mirror (read-only). The new cache is under `naren_workspace/xy_repair_ranking`.
- **Label contract:** X and Y are recorded separately. A value counts only under VERIFIED / CERTIFIED_*; UNKNOWN stays missing.
- **Merge** (`collect.py merge`), by exact (root, ordered sequence):
  - An X node is added only if X is decided.
  - An endpoint Y is added only if decided and not already labelled. If it is already labelled, the values must agree; disagreements are quarantined.
  - Partial observations are kept.
- **Storage:** the augmented snapshot is private (`~/xyrr_private/snap_aug`). The original snapshot is unchanged. VAL and TEST rows are byte-identical.

## Gates for P4

- **Report-only gates:**
  - At least 100 TRAIN roots with both a Z+ and a Z− after the merge.
  - At least 50 roots with newly decided rank > 6 candidates.
- **If either gate is missed:** P4's data arms are labelled exploratory.
