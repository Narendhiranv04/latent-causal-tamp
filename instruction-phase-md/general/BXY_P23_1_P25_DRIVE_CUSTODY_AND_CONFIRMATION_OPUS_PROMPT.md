# Claude Opus 5.5 High — P23.1 → P24 → P25 Execution Handoff

**Repository:** `Narendhiranv04/latent-causal-tamp`  
**Branch:** `approach-b-xy-v1`  
**Verified P23 HEAD:** `a863c17499d3ba49304962ccb89d436af0076533`  
**Intended private Google Drive backup folder:** `https://drive.google.com/drive/folders/174BJDHX-0x-ZM4Jy6MJjkfwZ_z9ZpxG6?usp=sharing`  
**Objective:** Finish the *existing*, already trained and frozen Approach B 2D K0–K4 experiment, with no model redesign and exactly one independent test.

## 0. Read before acting

You are the implementation and experimental-audit agent. **Execute** rather than merely analyze. First read the original `Approach_B_Final_Methodology_2026-10-31.pdf`, the implemented addendum `responses-phases/0129A_APPROACH_B_IMPLEMENTED_METHOD_ADDENDUM.md`, reports `0126`–`0130`, the previous P23–P25 instruction contract, and these frozen files:

- `runs/approach_b/bxy_p23_v1/FROZEN_MODELS_P23_APPEND.json`
- `runs/approach_b/bxy_p23_v1/CONFIRM_PLAN_P23_LOCK.json`
- `runs/approach_b/bxy_p23_v1/CONFIRM_ANALYSIS_P23_LOCK.json`
- `runs/approach_b/bxy_p23_v1/AUTHORIZATION_P24_PROPOSED.json`
- `bxy_p23_preflight.py`, `bxy_p24_confirm.py`, `bxy_p23_engine.py`, `bxy_p24_analysis.py`, and related tests.

Check HEAD == origin and all historical hash guards before any change. Do not override concurrent work. If HEAD has moved, audit those changes and reconcile explicitly. Never alter P-min–P23 frozen evidence in place.

### A crucial clarification

Retraining the same architecture and hyperparameters is *not* a substitute for preserving the existing checkpoints: random initialization, numerics, optimizer trajectories, data order, and environment can change the learned parameters and decisions. **The exact 60 already frozen P21 D/E/DIRECT/G checkpoints are the confirmatory model.** Do not retrain, refit, change seeds, select new checkpoints, or modify model outputs.

The current P23 verdict is `BLOCKED_CHECKPOINT_CUSTODY` only because the copies are on the same physical NVMe. All other P23 items passed. Use the provided Google Drive folder as independently stored backup, subject to authentication, write permissions, confidentiality, and verified restore. This is an authorization to attempt that backup; it is *not* evidence that a Drive connection is already available.

## 1. P23.1 — Close checkpoint custody on Google Drive

**First priority; no teacher queries, new confirmation scenes, or model training.** This is a new, incremental administrative budget of **at most 3,000 CPU-seconds and 10,800 seconds wall time**, with no more than four single-thread workers; account separately from the completed P23 ledger. Upload/download elapsed time counts toward wall time. If this is insufficient, stop with exact measured remaining work rather than silently extending the budget.

1. Establish whether the provided folder is accessible using an already authenticated Google Drive integration, browser session, `rclone`, or a supported upload client. Verify **write permission** and available capacity; do not assume the URL permits writing. If account authorization is required, present the exact one-time browser/OAuth action needed; do not ask me to paste passwords or tokens and do not write OAuth secrets into the repository, logs, or report. Do not modify sharing permissions or expose the checkpoints publicly. If the supplied folder is publicly shared, warn me before uploading sensitive research artifacts.
2. Make a versioned subfolder for this immutable snapshot, e.g. `Approach_B_P23_Frozen_P21_Checkpoints_<shortSHA>`, preserving the directory identity of each `(fold, arm, seed)` checkpoint. Back up the **60 specific checkpoint binaries** used by the frozen D/E/DIRECT/G ensembles, their `RESULT.json` metadata, and small reproducibility manifests (frozen models/analysis/plan, code/teacher hashes, README with exact commit, dependency/environment notes). Other checkpoints may be backed up separately only if space allows; the frozen 60 have priority.
3. Build a manifest *before upload* listing every relative filename, byte count, SHA-256, model arm/run ID, and provenance SHA. Upload using binary-safe methods with retries and integrity checks. Do not use a GitHub commit for large `.pt` files and do not put credentials or unrestricted share links into Git.
4. **Read back from Google Drive** and verify a complete independent copy: download into a clean scratch location, check SHA-256 of every checkpoint and metadata file, load all 60 restored members, and compare a representative set of frozen development predictions to recorded baselines at the existing numerical tolerance. Merely listing uploaded filenames or comparing Drive-side size is insufficient. Capture actual remote file IDs/paths and readback evidence, but do not expose private tokens.
5. The current `bxy_p23_preflight.py custody <mount>` checks a *separate physical disk* and may not recognize cloud storage. Add a **small, explicit, versioned `remote_custody` verification path** rather than falsifying a mount, setting a fake `CUSTODY_OK`, or waiving the check. Use a new P23.1 evidence location, e.g. `runs/approach_b/bxy_p23_1_v1/`. The path must produce `REMOTE_CUSTODY_VERIFIED` only after independent download, SHA verification and restore/test-load succeed. The remote snapshot must not be a directory on the same NVMe presented as a different drive.
6. Ensure the **P24 runtime refuses to generate** if the verified remote-custody evidence is missing, corrupted, or references different frozen checkpoints. Surgical changes to the *gate code* are permitted, but do not change the teacher, generator semantics, scorer/model, frozen weights, candidate ranking, data, or statistical endpoint. Unit-test the refusal and positive proof cases.
7. If any source file changes, update every affected prospective code-tree hash/manifest and versioned lock before requesting or recording approval. Keep the P22 and P23 prior lock files intact, with explicit parent SHA links. Re-run the pertinent regression tests, full suite and six historical replays. Commit and push P23.1, with exact HEAD and custody artifact evidence.

**STOP here if remote backup cannot be authenticated and fully restored.** Report the precise blocker and a single actionable login/mount step. Do not bypass custody or proceed with P24 simply because local files still exist.

## 2. P24 — Authorization and one-shot independent K0–K4 evaluation

**Conditional execution authorization:** When, and only when, P23.1 remote custody has passed, all locked evidence/code rechecks pass and the final authorization manifest is committed, you may execute exactly the one-shot P24 experiment stated below. This explicit authorization is granted by my sending you this handoff; transcribe this text faithfully in the new `AUTHORIZATION_P24.json` and attach final *post-P23.1* code/lock hashes. Do not pretend that an unverified manifest is approved, and do not substitute a different budget or research plan.

> **I authorize BXY-P24: one-shot generation and labelling of the 440-slot `bxyg34confirm` cohort and one evaluation of the frozen D / E / DIRECT-GEO / G ensembles, with at most 90,000 aggregate CPU-seconds (including a 3,000 CPU-second evaluation reserve), 40,000 seconds wall time, four single-thread workers and 1,400 CPU-seconds per root; the per-query teacher budget remains unchanged. This approval is conditional on successful, read-back-verified independent Google Drive checkpoint custody and on the final versioned hashes being recorded before the first scene is generated.**

**The authorization is specific; it does not approve data collection, training, or repeated tests outside that cohort.** If the final code tree must change after authorization, stop and record the mismatch. Do not silently reauthorize or patch the runner during the test.

Execute these steps **in order** using the existing `bxy_p24_confirm.py` contract:

1. Validate the commit, P23/P23.1 manifests, old artifact hashes, teacher and code-tree hashes; verify all four frozen model ensembles and remote-custody proof. Confirm zero `bxyg34confirm` files or prior labels. If any confirmatory data already exist, STOP—do not run a second cohort.
2. Commit a copy of the final authorization with `approved=true`, provenance identifying the user's explicit prompt, verbatim approval text and matching final hashes. If the authorization mechanism requires any surgical compatibility amendment, document and test it *before* approval is committed.
3. **Generate exactly 440 predeclared construction slots** with the unchanged P23 mix, generator and namespace. Preserve every rejection; do not replace rejected slots or change the ratio to chase K4 yield. A K-intent label is not a physical K proof.
4. **Freeze all candidate catalogues and label-free inputs before teacher labels.** Run each of the four 15-member ensembles once per accepted root and seal predictions/selected candidates and their SHA-256 in the append-only ledger **before** the first teacher result is collected. Do not inspect model choices to change the cohort.
5. Run the unchanged physical teacher once with the exclusive-supervisor engine; respect the original per-query budgets and the 90k CPU / 40k wall / 4-worker / 1400-per-root ceilings. Between relocations there is **no robot reset**; after the final relocation X connects to `q_ref`, then Y independently executes the target from `q_ref` in the edited scene. Track `CERTIFIED` vs `NO_PLAN_FOUND/TIMEOUT`, censored, unattempted, corruption, recovery and conservative resource charges faithfully.
6. Perform **one** locked evaluation using `bxy_p24_analysis.py` and `CONFIRM_ANALYSIS_P23_LOCK` (or explicit versioned P23.1 successor only if required by the remote-custody gate). No new training, post-hoc thresholds, replanning of the test, adaptive extra scenes, or second look.
7. The single authoritative endpoint is **U**, verified corrective success across *all* initially infeasible roots. **C** (availability-conditioned) is a required consistency check for positive labels; a high C alone cannot override a failed U. Use the registered Holm-adjusted paired family bootstrap for D vs DIRECT, E vs DIRECT, D vs E, and the separate order family (D vs G and E vs G strict permutations, plus D vs G repairable K3/K4 success). Preserve `UNDERPOWERED` flags and caution for few initially feasible roots; do not characterize a zero or uncertain false-repair difference as proven safe.
8. Report per-K counts based on the **verified** `K_catalogue` and certified necessity `K_cert`; include K0/no-op correctness, physical replay samples, harmful/neutral edits, strict certified order twins, omission signs, matched successful travel and verify-first upper bound. Distinguish geometric access features and label-free generator intent from learned results. Never claim that new seeds from the same doorway generator demonstrate cross-generator or 3D generalization.
9. Commit immutable P24 evidence, all machine-readable tables, resource ledger, scene/witness figures, relevant tests, six replay logs and `responses-phases/0131_BXY_P24_ONE_SHOT_CONFIRMATION.md`. Push and confirm local == remote. If P24 is interrupted, follow only the already tested explicit recovery protocol—do not restart a second collector. If custody, hash, or data-blindness is compromised, STOP and report without hiding exposure.

**Expected but not guaranteed:** ~255 accepted roots, ~228 initially infeasible, ~123 with a verified candidate, ~101 available K3/K4, only ~26 feasible controls. Do not claim the planned 440 slots imply 440 usable independent roots. Be candid about likely weak statistical precision of the unnecessary-repair safeguard and the possibility that D/E will not beat DIRECT.

## 3. P25 — Final analysis and documentation

Once P24's **single locked evaluation** completes, use the stored results without any second teacher collection or optimizer update to produce:

- `responses-phases/0132_BXY_P25_FINAL_METHOD_AND_FINDINGS.md`, a concise final implemented methodology (original Oct 31 specification *unchanged* plus the GEO2/SYM addendum), claim-support matrix, comparison tables, paired confidence intervals and proper failure explanations.
- Publication-ready 2D scenes and trajectory evidence, including verified K3/K4 storyboards with each relocation, the terminal connector, prefix Y and final target execution; truthful distinction between true witness trajectories and schematic edits.
- Clear baseline discussion: even if D/E fail to beat DIRECT, report the result without reinterpretation. Treat quadratic coupling as unsupported unless independent data prove otherwise. Prefer E as the practical X/Y architecture if coupling remains unhelpful, but do not switch the preregistered primary D-vs-DIRECT comparison after seeing labels.
- A printable final research findings PDF if the repository tooling supports it, with the correct independent data and no exaggerated claims. Freeze the artifact hashes and produce a compact report of what the method has actually learned, what is supplied analytically, and what remains unproved.

Preserve all original results. All verification, tests and six archived replays must pass. Commit/push exact SHAs for P23.1, P24 and P25. **Stop after P25.** Do not start 3D, add another neural factor, broaden to a new teacher, or launch another confirmatory cohort.

## 4. Non-negotiable research and security boundaries

- Never claim an uploaded file is safe until its downloaded bytes hash-match. No secrets in Git or logs; never make a private research backup public without permission.
- Do not change `F1–F5`, GEO2, SYM, model classes, existing trained weights, physical teacher, `q_ref` semantics, candidate grammar, learning loss or estimator during confirmatory work.
- Do not report P21 out-of-fold three-seed results as performance measured for P24's frozen fifteen-checkpoint ensembles.
- The planned false-repair control denominator may be small. Keep it transparent; no post-test extension of the control set.
- Use model probabilities to rank **already generated** corrective candidates; do not suggest the model generates robot trajectories or independently discovers global causes.
- **Meaningful negative evidence is an acceptable endpoint.** The aim is to complete the research correctly, not force significance.

## 5. Response format while executing

For each gate, give: (a) verified starting SHA and committed ending SHA; (b) exact changes; (c) artifact paths and hashes; (d) complete counts and relevant CIs; (e) CPU/wall/resource ledger and any incidents; (f) test/replay results; (g) gate verdict; (h) whether any future work is blocked. No generic status messages in place of final evidence. If an external authentication step is needed, stop only at that concrete blocker and show precisely what I must do.
