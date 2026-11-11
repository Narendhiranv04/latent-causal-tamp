# Approach B — Final 3D Training-Dataset Coverage Correction (Q2-Parity), Single-Pass Implementation and Launch-Readiness Contract

**Audience:** Claude Opus 5.5 High operating in the existing `rss-ebm-infeasibility` workspace.

**Priority:** Correct the previously overlooked mismatch in **the 3D training-query roster**. No new source-scene generation, no teacher redesign, no broad mock redesign. This is the final coverage correction before full 3D placement-label collection.

## 0. Scientific requirement, and why this is necessary

The previous 3D pipeline demonstrated a correct physical placement teacher and a reproducible, safe `adaptive_v1` search policy, but carried the **10-slot-per-root mock roster** into production. This is too sparse compared with the 2D Q2 production methodology. The user requires **comparable coverage methodology**, adapted to 3D, for training the placement sampler and subsequent Approach B inference. Do not equate a physically verified teacher with a sufficiently broad training dataset.

**Ground truth from the existing code and committed cohort:**

- Repo: `Narendhiranv04/rss-ebm-infeasibility`.
- Existing 2D base: branch `naren/2d-object-relocations`, `gh-yadu-iiith/planar_2d/dataset_relocations_v1/code_v2/launch_plan.py`; exact Q2 quota: `root_objects=4, root_dests=8, prefixes=3, prefix_objects=2, prefix_dests=4`.
- 2D root design: up to four non-target objects, selected with source-distance stratification; up to eight legal destinations each, near/mid/far interleaved. Prefix1 and prefix2 are **two independent one-edit hypothetical scenes**; prefix3 is one **two-edit hypothetical scene**, with distinct edited objects. Each prefix queries up to two **unmoved** objects nearest the edited objects, each at up to four stratified destinations, including a vacated cell when applicable. No protected construction/repair metadata or archived solution is used. Target goal cell may be a legal ordinary destination; it is not a veto.
- Existing 3D branch: `naren/3d-dataset-relocations`, last audited v3 integration commit `abac62ead7668fb610f2db2d635821a5df7e0114` (verify current HEAD).
- Existing 3D source first cohort: 1,582 QC-eligible K0–K3 roots, with 116 zero-non-target roots; 3D v3 roster: 13,651 physical queries, 2,768 static controls, 1,466 query-bearing roots. Current `code/plan3d.py:roster_for` uses just 10 slots with the root, one one-edit, and one two-edit scene.
- Verified non-target counts of all first-cohort roots (from `production_v3/QC_ELIGIBLE_ROOTS.json`): 0:116, 1:164, 2:298, 3:393, 4:383, 5:121, 6:66, 7:41. Theoretical Q2-style max, based on these counts and **before** destination availability or contextual geometry constraints: **59,972 physical queries**. This number is not a promise; compute exact roster numbers.
- Validated 3D physical teacher: `SHELF66V3_PLACE_V2`, protocol `89cbabed5d7e4847`, `adaptive_v1` stages `4 poses×500 -> 8×1500 -> 16×5000` (each pose has up to four eligible IK branches). Keep the source-exact collision protocol, physical MuJoCo checks, negative scopes, and witness retention unchanged.
- 3D working host: `ssh gvlab` -> `nav@gvlab`. Preferred 12 single-thread workers pinned to CPU 0–11; **absolute combined project ceiling: 18 logical CPUs**. Never interfere with another researcher's jobs. 2D Q2 on the laptop is a separate independent collection; do not interrupt or change it.

## 1. First step — detect whether collection has already begun

Inspect *actual* live processes, tmux, Git checkout, run ledgers and manifests on both hosts. Report `2D_Q2=not_started|running|paused|completed|blocked` and `3D_V3=not_started|running|completed|blocked` based on evidence, not assumptions.

- If **2D Q2 is running**, preserve it completely. No reconfiguration of its scientific policy, plan, witness handling or process.
- If **3D v3 (13,651 queries) is not started**, do not launch that obsolete sparse roster. Prepare a separately versioned **3D Q2-parity roster v4** and integrate it into the guarded production system.
- If **3D v3 has started or finished**, DO NOT modify its frozen files or interrupt an ongoing correct run merely because the roster is sparse. Preserve its verified data as **base coverage** and design a **deduplicated v4 extension**: only newly needed semantic placement queries, with independent run manifest, provenance, and no re-labeling of already physically verified identical queries. Run the extension when resource-safe. Do not mix an unfinished run with another competing physics job on `gvlab`.
- Define a canonical semantic query key using frozen source snapshot/root hash, exact hypothetical edited state (all object poses, shapes/dimensions), queried object, destination, placement teacher protocol and policy identity. Use it to deduplicate; qid strings alone are insufficient. Keep the old and new run provenance separate.

## 2. Correct 3D query roster — same sampling **procedure**, 3D geometry-specific details

Implement **one** clean new `Q2_3D_PARITY_V1` roster-generation rule, preferably minimal additions/reuse within `code/` and a new versioned `production_v4/`, without editing any frozen v1/v2/v3 evidence. Avoid adding a proliferation of files.

For every one of the **1,582 QC-eligible K0–K3 roots**, generate the following **label-blind, deterministic** placement candidates:

1. **Root scene**: select up to **4 non-target objects** with deterministic diversity in source distance from the xArm base, object shape (box/cylinder), geometry/height and clutter when possible. Sample up to **8 distinct legal/free destinations per object**, interleaving near/mid/far bins so early prefixes cover all available bins. Do not require impossible diversity within single-object roots. Per-context order and inclusion probability must be recorded for future training weighting or debiasing.
2. **Prefix1 — independently designed one-edit state**: deterministically select a non-target mover and free destination without reading the archived construction, repair roles, B/D labels, goal feasibility, previous teacher outcomes or solution traces. Update the hypothetical scene. Query up to **2 other, unmoved objects** near the edited source region, each at **4 legal/free destinations**, with the vacated source cell included when appropriate.
3. **Prefix2 — second independently designed one-edit state from the SAME root**, changing a different mover and preferably a geometrically distinct destination. This is **not** the second step of Prefix1. Again, up to **2 unmoved objects × 4 legal/free destinations**. If no distinct eligible mover exists, record `NOT_APPLICABLE` rather than manufacturing impossible cases.
4. **Prefix3 — one two-edit hypothetical state**: two sequential deterministic, legal, non-target *scene edits* with distinct moved objects, starting from the root; then up to **2 other, unmoved objects × 4 legal/free destinations**. Do not label the edits themselves as physically executable. Preserve full `parent_scene`, edit provenance, and original cell occupancy. If insufficient objects or free cells, mark the context inapplicable.
5. **Static controls**: include targeted occupied/out-of-bounds and vacated-cell root-scene contrasts as *static-ineligible*, never as physical negatives; do not route these through the physical placement teacher.

**6×6-specific adaptation**: Use the actual shelf legal cell set and 3D xArm geometry. For target displacement Chebyshev distance, use near=1, mid=2–3, far=4–5 (or a predeclared defensible geometry-specific binning with an explicit histogram), rather than copying the 2D 8×8 far=5–7 rule. In addition to these 2D-style bins, report source distance from the arm, object geometry (height, size, box/cylinder), obstacle clutter near source/destination, and edit depth; do not infer labels from any of them. Free cells and destination legality are computed in each corresponding *hypothetical* scene, not the root scene.

**Important:** The Q2 quota is **4×8 root + 3×(2×4) prefix = 56 maximum per root**, **not** 56 guaranteed per root. Roots with 0/1/2/3 obstacles naturally have fewer context/object queries. Given the actual cohort's obstacle-count distribution, **59,972 is the nominal upper bound before destination availability**, not the final roster count. The assistant's earlier illustrative 75k estimate was incorrect for these data. Derive the final number mechanically, never pad a roster merely to hit an arbitrary target.

## 3. Quality and training-utility gates: do more than compare query counts

Compute full histograms and joint coverage for K0–K3 × split × root/prefix1/prefix2/prefix3 × source-distance × destination near/mid/far/vacated × shape × clutter/height. Also report per-root query counts including 0, distribution of distinct hypothetical scenes, object identities, destination diversity and exact semantic duplicates. Detect accidental heavy sampling of one easy stratum. Report the theoretical 59,972 before filtering, realized count and causes of every reduction.

Predeclare and mechanically test these gates before any full 3D run:

- Every feasible Q2 block appears on train/val/test and for each K where it is structurally representable; no impossible demands on K0 roots with 0/1 non-target objects.
- Root/source scenes and their 1/2-edit descendants stay in the *same inherited lineage split*; all old split assignments unchanged; no cross-split duplicate layouts or semantic query leakage.
- No use of protected task labels, target feasibility, archived repairs or teacher outcomes to select contexts, objects or destinations. The target's goal cell is allowed as an ordinary legal destination, never privileged for label generation or vetoed.
- Edit states are valid object configurations (inside free shelf cells, no duplicate occupied cells, no target moved); they are hypothetical **not execution labels**. The physical teacher continues to independently certify placement conditional on a valid held object.
- Distinguish `VERIFIED` (executed and witnessed) vs `NEG_CERTIFIED_GEOMETRY` (certificate with finite geometry scope) vs `NEG_UNDER_POLICY` (finite search scope) vs `UNLABELED` and static ineligible; never turn missing results/interruption/failed holds into physical negative labels.
- Include near, mid, far, vacated, root, 1-edit and 2-edit coverage in held-out testing. Preserve every verified witness under the attempted finite policy, branch provenance and execution replay, with exact protocol hash.
- Avoid systematic de-duplication that removes useful diverse **scene contexts**. Deduplicate **only** identical semantic query keys; record original context references if a query serves multiple strata.
- Freeze a training-utility report, not just a motion mock: positive/negative/unlabeled counts by all important strata as results arrive, effective distinct query counts, and a clearly described data loader schema for the later sampler.

No arbitrary quota change, no iterative hand-tuning after looking at validation/test outcomes. If a feasibility stratum is thin, state its limitation and whether geometric availability makes that unavoidable; do not silently oversample with protected labels.

## 4. Preserve existing physical and production protocols

- Do NOT change the SHELF66V3 MuJoCo teacher, 13 verification gates, finger-width source protocol, held-state definition, deterministic branch-aware `adaptive_v1` policy, or finite negative semantics. This request is a **roster coverage correction**, not a new teacher project.
- Implement v4 freezing and checks by extending the production-v3 guard (`prod3d.py`, `collect3d.py`) with the smallest necessary, separately versioned changes. Ensure the modified code/config is freshly hash-locked and cannot be mistaken for the old v3 authorization. A user authorization for the old 13,651-query roster **does not automatically authorize** the materially larger v4 roster.
- The preflight must independently regenerate the v4 roster and compare canonical content, hashes, source QC, cohort and split. Test 0 teacher calls, no run-dir creation. Keep an exclusive lock, all resource monitors, 12 pinned workers, <=18 combined logical CPUs, sensor fail-closed, disk/memory headroom and abort/resume integrity.
- Run ONE bounded targeted integration check on the **new roster**, including root and all representable prefix types, shapes, near/mid/far/vacated, difficult clutter, negative and unlabeled cases when available; all physical witnesses independently replay; exact restart/corrupt-NPZ recovery. Minimal size sufficient to expose roster/collector integration errors; this is **not another 405-query policy search** and cannot be tuned to achieve preferred label distributions.
- On production: 100% witness replay at completion, full post-run source/NPZ/ledger integrity, unique physical query keys, valid status/labels, split checks, coverage and class/shape/distance histograms. Preserve partial-run provenance and re-use verified old work only under exact matching semantics.

## 5. Workload, ETA and risk, before authorization

Determine exact v4 physical query count and compute a **stratified** forecast based on v2 costs (K × edit depth × distance band, and shape/clutter where sample support allows), real 12-worker efficiency, and a 1.5× or more conservative buffer. New prefix2 and denser destination sampling shift the query distribution: a naive 13,651-query linear extrapolation is insufficient as a standalone estimate. Use separate novice/unseen-stratum backoff, lineage bootstrap and a held-out 3D teacher timing sample if needed. Report sensitivity (optimistic/base/conservative) and maximum safe practical runtime/storage, with process temperatures and disk reserve.

**For scale only:** ~60k queries at the old mean cost (~9.27 CPU seconds/query), 12 workers and 0.881 efficiency would be approximately **14.6 hours wall** plus a 1.5× allowance of approximately **22 hours**. This is illustrative, not a measured final forecast. The final v4 roster and pilot stratum costs must replace it; 3D can take longer for harder placements.

If an old 13,651-query 3D run is complete or underway, compute only the **remaining v4 extension** cost after exact semantic deduplication. Never charge or execute already verified equivalent queries twice.

## 6. GitHub, durability and 10-minute status

- Use `naren/3d-dataset-relocations` for the v4 code and versioned artifacts. `naren/2d-object-relocations` remains the independent 2D Q2 source; do not edit or overwrite its collection state.
- Create the required 10-minute **machine-side** monitor service on each running host (tmux/systemd user service/cron as appropriate) that survives loss of Claude chat or SSH. Every 600 s: snapshot progress counters, success/negative/unlabeled counts, bytes, throughput, ETA, sensor/CPU/RSS/disk state, errors, active PID, source+run manifest ID; normal Git commit/push of **small stable status files** to the correct branch, with timestamp and SHA and retry queue for offline network conditions.
- Independently back up **finished and hash-verified** dataset units to a confirmed durable off-host storage location using atomic incremental transfer. A Git progress commit is NOT a dataset backup. Never add multi-GB unbounded binary updates every 10 minutes to Git. If no authorized backup destination is actually configured, report `OFFHOST_BACKUP_BLOCKED` and keep reliable local atomic snapshots; do not invent a destination or call status commits backups.
- Avoid parallel Git push conflicts between Claude and the monitor: dedicated telemetry branch/worktree (or other nonconflicting branch per host), serialized git lock, fast-forward-only push, no force. Copy final audited data into the permanent dataset branch in manageable batches or after completion.
- Every progress status and every completion report must clearly identify the Q2 2D job and v4 3D job independently, including whether they are actually running vs only prepared.

## 7. Deliverables and decision

On the 3D branch, commit/push in a clean versioned `production_v4/` (or similarly isolated minimal location): exact roster and source-QC pins, generator code, Q2-parity spec, coverage report/plots, split+dedupe proof, preflight+smoke outcomes and replay, cost forecast, guarded production policy template, explicit next authorization procedure, rollback/resume/runbook, status+backup service and proof of 10-minute operation. Preserve old v1/v2/v3 files byte-identically; explain any minimal shared-code edits through hashes/diffs.

Before calling it ready, run the tests and clone/fresh-checkout verification. Report precisely:

1. `2D_Q2_CURRENT_STATE` with evidence and no interruption.
2. `3D_V3_CURRENT_STATE` and whether verified base data can be reused.
3. `3D_Q2_PARITY_ROSTER_PASS/FAIL` with **exact** realized physical queries, per-block/shape/K/bin breakdown and contrast count.
4. `3D_PHYSICAL_INTEGRATION_PASS/FAIL`, `SOURCE_QC_PASS/FAIL`, `SPLIT_LEAKAGE_PASS/FAIL`, `PRODUCTION_GUARDS_PASS/FAIL`, `WITNESS_REPLAY_PASS/FAIL`.
5. `3D_V4_READY_PENDING_NEW_USER_AUTHORIZATION/NOT_READY` and exact expected/buffered time for the full or extension workload.
6. Branch HEAD, validated launch commands, monitors and backup confirmation.

**STOP CONDITION:** Do not launch the larger 3D v4 collection under an authorization token for the old 13,651-query v3 scope. Once all v4 gates pass, present the exact new roster/query count and its frozen policy for **one explicit authorization**; then the real collection can proceed, with no more broad mock/roster iterations. If the user explicitly authorizes the expanded v4 run in a subsequent instruction, execute it under the new guarded policy and 10-minute monitoring. This restriction does not halt any already-authorized 2D Q2 run or a previously started 3D v3 run.

---

## Copy-ready Claude kickoff

You are continuing Approach B. The previous 3D first-cohort **teacher and production integration passed**, but we discovered a serious **training-query coverage error**: `plan3d.roster_for()` carried a sparse 10-slot mock roster into production, whereas the 2D Q2 design uses up to 4 objects × 8 destinations in the root and 3 hypothetical contexts (two independent 1-edit and one 2-edit), each up to 2 unmoved objects × 4 destinations. This is a **scientific sampling error, not a MuJoCo teacher failure**.

Read this entire Markdown file and treat it as the final coverage-correction contract. Inspect the real latest repository branches and live 2D/3D job states before acting. **Preserve any already-running 2D Q2 run, and preserve any begun 3D v3 work.** On `ssh gvlab`, implement the Q2-style roster for all 1,582 validated 3D K0–K3 roots with the appropriate 6×6 geometry and shape/clutter/distance stratification. The theoretical maximum based on real object counts is 59,972 before free-cell constraints; compute and defend the exact realized count, not an invented quota. Preserve the unchanged v2 physical placement teacher and adaptive_v1 policy. Version the expanded roster and guarded production as v4; no v1/v2/v3 dataset/artifact edits. Prove no metadata leakage, split leakage, duplicate labels, or physically invalid positivity; run one bounded physical integration smoke, preflight the exact full workload, generate a stratified forecast, set up durable 10-minute statuses/Git pushes and independent data backups, and commit/push the final reviewed system to `naren/3d-dataset-relocations`.

There must be **one final launch-ready dataset plan** after this pass, not another chain of broad pilot revisions. If v3 is already collecting, reuse it as a verified semantic-key-deduplicated base. **Do not mistake the user's old 13,651-query authorization for approval of the larger v4 roster**: freeze, validate and present the v4 authorization once with exact scope and time. Do not touch the 2D Q2 scientific run. Be implementation-driven, concise in code, comprehensive in evidence, and report the exact run states, query counts, ETA and GitHub SHA.
