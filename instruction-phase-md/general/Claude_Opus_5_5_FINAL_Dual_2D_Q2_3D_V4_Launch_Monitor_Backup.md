# FINAL EXECUTION CONTRACT — Launch BOTH Approach-B placement datasets

**Audience:** Claude Opus 5.5 High in the user's established laptop workspace, with authorised SSH access to `gvlab`.
**Objective:** Complete the **2D Q2 production-policy amendment and actual collection launch on the laptop**, and the **3D Q2-parity v4 full-collection launch on gvlab**, with unattended 10-minute telemetry and recoverable, hash-verified cross-machine backups. **This is an execution task, not another project-planning or mock-only exercise.**

## The user's explicit authorisation (read literally)

> I authorise starting the 2D **Q2** placement dataset collection on my laptop: **238,160 physical placement queries**, ADAPTIVE_FULL **8→32 valid mode pairs**, **25 workers**, the existing verified boost-OFF thermal/safety configuration. I also newly authorise starting the 3D **v4 Q2_3D_PARITY_V1** placement dataset collection on **`gvlab`**: **59,972 physical placement queries**, **adaptive_v1 4×500 → 8×1500 → 16×5000**, **12 workers pinned to CPUs 0–11**. This v4 authorisation supersedes no previous history and **does not authorise v3**. I authorise *user-level* recurring telemetry, fast-forward GitHub pushes of status/milestone files, and reversible incremental backup to my available machines, subject to checking permissions and disk availability. This authorisation applies **only if the appropriate frozen-manifest, scientific, thermal, resource, reproducibility, and integrity guards pass**. Do not forge a personal identity, modify another user's files, bypass a permission prompt, delete existing data, or use sudo without separate approval.

Record the authorisation statement verbatim, the actual UTC recording timestamp, the exact frozen policy hashes and the traceable execution context. For v4's required `authorization` fields, use an accurate provenance string such as `"requesting user — authorisation supplied in this execution prompt"` instead of inventing the user's legal name. If the runtime explicitly requires a user-only action that cannot legally be delegated, ask for **only that exact action** and keep the other host progressing. Never call a run authorised merely because a token can be computed; the full guard must pass.

## Authoritative sources — verify LIVE HEAD and working copies before touching anything

**Repository:** `Narendhiranv04/rss-ebm-infeasibility`.

**2D laptop:** branch `naren/2d-object-relocations` (also inspect `naren/2d-dataset-relocation` and the previous *detached/uncommitted* worktree). Prior validated worktree: `/home/naren/Desktop/rss-placement-ready-v2`; sidecar under `gh-yadu-iiith/planar_2d/dataset_relocations_v1/launch_ready_2d_v2/`; code under sibling `code_v2/`; previous frozen Q1 selection rule in `launch_ready_2d_v2/audit/package/reviewed/mock_v2_gate.py`; launcher `launch_full_2d.sh`; run directory `.../dataset_relocations_v1/full_2d_v2`. **Prior known state: mock validated but Q1 forecast gate blocked; Q2 was chosen verbally and needs an explicit traceable policy amendment, not a skipped guard.** Inspect the live host, all worktrees and branches; preserve uncommitted work. Do not hard-reset, `git clean`, overwrite local files, or manufacture success if old worktree differs.

**3D gvlab:** `ssh gvlab`, branch `naren/3d-dataset-relocations`; last audited v4 commit `83c1135f69f894424873e0a3843be67c91d9ce99` (verify new HEAD). Checkout `~/approachb3d_v3/repo`; project subfolder `gh-yadu-iiith/shelf_6x6_open_sides/dataset_placement_extension_v2/`; runbook `production_v4/V4_RUNBOOK.md`; launcher `production_v4/launch_v4.sh`; code `code/{q2roster3d,prod4,collect4,status4,decide_v4}.py`; v4 run dir `production_v4/run_q2_parity`. Existing v4 first-cohort source = 1,582 QC-eligible K0–K3 roots, 1,466 roots with queries. **Prior known state: scientifically validated, new v4 authorisation missing, no actual v4 production started.** V3 is superseded; do not launch it.

**Telemetry GitHub branch:** `naren/3d-dataset-relocations-telemetry`, intended to contain status artifacts only. Verify current remote before any push.

## Hard scope limits

1. No changes to the validated **2D teacher**, pair-protocol, planner seeds, labels, source scenes, lineage grouping or 8→32 search semantics. No changes to the validated **3D teacher**, MuJoCo 13 verification gates, `adaptive_v1` pose/branch semantics, frozen 59,972-row roster, QC roots, source snapshot or splits. Do not generate K4/NONE or new root scenes.
2. Do not run broad mock studies again. Reuse already saved pilot evidence. Allow only targeted guard/preflight tests or minimal integration checks required to verify the exact launch path.
3. 2D runs only on **laptop**: 25 validated CPU workers, host AC, CPU boost OFF, existing Tctl safety thresholds and no suspend. Do not bypass power/thermal gates or change hardware configuration silently. If boost-off requires privileged action, request a minimal explicit manual command; let 3D progress independently.
4. 3D runs only on **gvlab**: 12 workers CPUs 0–11; absolute project ceiling 18 logical CPUs; nice 10, one numerical thread/worker; run guards, process ownership, temperature, RSS, available memory and disk; no sudo and no interruption of other users. Stop on safety failures.
5. **Never launch Q1 by accident** (the old 357,240-query 2D plan) or the obsolete 13,651-query 3D v3 roster. New production launch must be demonstrably Q2/v4 by hashes and recorded query counts.
6. Two independent hosts are not a hard deadline guarantee. Do not claim an ETA as a measured result before measuring live throughput.

## Work package A — Snapshot actual state before changes (both machines)

- Record live Git SHA, tree cleanliness, source and frozen manifest hashes, host CPU topology and resource occupancy, disk free space, Python version, active collection PIDs, tmux sessions, launch locks, cron entries, and existing run directories.
- If **either** job is already running, **do not launch a duplicate or change its policy**: verify manifest, resume/state, and attach monitoring/backup. Preserve all finished units.
- If 2D local files are uncommitted or belong to a detached worktree, preserve them in a new correctly named local branch/worktree. Reconcile with the remote by normal non-destructive commits/FF pushes; never silently overwrite previous work. Keep changes restricted to required 2D readiness/ops files.
- On gvlab run read-only v4 source/hash and frozen policy checks before token generation. Check other users' jobs; never commandeer the server.
- Produce a concise `INITIAL_HOST_AND_RUN_STATE.json` with real observations, not inferred from archived reports.

## Work package B — Complete 2D Q2 amendment once, correctly

The previous reviewed mock gate `audit/package/reviewed/mock_v2_gate.py` **hard-codes Q1** in `composition_forecast`, the runtime gate and frozen policy (`quota: Q1`). Merely changing a field in `production_policy.json` or manually patching a failure boolean would corrupt the scientific audit.

- Make a **versioned, explicit production Q2 amendment** to the decision protocol, retaining all pilot evidence and the reason for selecting the shorter cohort. Preserve the historical Q1 negative verdict; do not rewrite pre-registration history as though Q2 was pre-registered from day 1. Clear traceability of the new choice: quota Q2 = **up to 4 root objects × 8 destinations; 3 prefix blocks × up to 2 unmoved objects × 4 destinations**, yielding **238,160 physical queries** across the 5,000 2D roots.
- Recompute the **Q2-specific** composition-weighted CPU/walltime/storage forecast over Q2's actual destination/block mix; use the already-measured 25-worker boost-OFF throughput and original pilot costs; preserve conservative fallback for unseen prefix × band strata and the original 1.5× buffer. Prior forecast to verify, not to blindly copy: ~3.25 days expected and ~4.87 days buffered. The 7-day planning limit should pass without weakening it.
- Re-run the complete **original scientific and safety evidence gates**, using stored evidence; only the policy/quota/forecast/frozen hashes should change. Maintain ADAPTIVE_FULL first 8 valid pairs, escalate to first 32 only on no verified success, record **all** verified witnesses (witness_store_max >= 32), no archived reuse, no goal-cell veto, 1-edit and 2-edit contexts.
- Freeze `production_policy.json`, selection evidence, query-plan and split hashes. Confirm selected quota is literally **Q2** and counted physical teacher queries **238,160**; static-ineligible rows are separate. Require `launch_runner.py preflight ... full`, `launch_plan.py verify`, `launch_check.py integrity`, policy-guard and refusal tests to pass, including boost off, AC, CPU mask, memory/disk, and no existing conflicting collector. Test no-arguments launcher refusal without touching a run.
- Record the explicit Q2 amendment and the evidence in `2D_Q2_LAUNCH_DECISION.json` (inputs, passed/failed gates, hashes, actual command). Commit and push the **source + manifests**, not raw multi-day binaries, to the correct 2D branch.

## Work package C — 3D v4 final checks; preserve scientific freeze

- Pull/verify the latest `naren/3d-dataset-relocations` without discarding local work. Re-run the **production_v4** SHA256SUMS and v2/v3 manifests, `code/decide_v4.py`, source QC, and **59,972-query** metadata-only preflight; these should produce zero planner/teacher calls, identical roster generation, 0 other refusals, and no run directory.
- Confirm `adaptive_v1`, actual implemented stages, `SHELF_SRC`, 12 workers / CPUs 0–11, 1,582 validated roots, 59,972 physical rows, 4,616 static rows, and 0 lineage leakage. Do not regenerate a different roster or run 3D v3.
- Use the explicit new v4 authorisation above to fill the **v4-specific** authorisation copy (not the template), faithfully record the provenance and UTC, derive the v4 token with `code/prod4.py token`, and require `code/prod4.py check ... TOKEN` to return `ok: true`. Keep the authorised policy/token out of public Git commits; no tampering with frozen scientific hashes.
- If exact launch needs a user-controlled step or workspace permission, show the smallest command and continue on 2D in parallel. Do not claim launch before actual process and output evidence.

## Work package D — Make 10-minute monitoring ACTUALLY autonomous, for BOTH datasets

**Existing status4 service is only hand-tested**; `cron` was not installed. Implement the simplest authorised *user-level* persistence (`crontab`, or an existing user service); no sudo, background Claude chat session, or ad hoc infinite agent loop. Authorisation for user-level monitoring is explicitly given above. If the environment forbids installation even with this instruction, **do not bypass security policy**: provide the exact two/three pasteable user-terminal lines; identify precisely what is blocked and which jobs remain safe to start.

- On **gvlab**, every 10 minutes run the v4 `status4.py snapshot` and a **verified incremental second-disk backup**, guarded by nonblocking `flock` and with stdout/stderr to a persistent log. Install a retry queue so network/GitHub outages do not lose status.
- On the **laptop**, every 10 minutes capture a **real 2D Q2 progress summary** directly from the runner/committed per-root records: completed and remaining physical queries, completed roots, labels and witness counts, throughput and updated ETA, Tctl, AC/boost, memory/swap, disk, worker count/affinity, safety/paused/drained state, PIDs and errors. The pre-existing `status4.py state_2d()` only checks processes and run-dir existence; **that is not sufficient**. Implement a small robust read-only 2D summariser or extend status4 without changing the teacher.
- Have the laptop **relay** also fetch gvlab status and push a timestamped heartbeat + both structured summaries **once every 600 seconds** to `naren/3d-dataset-relocations-telemetry`, on a dedicated telemetry clone, with normal fast-forward pushes and file/commit filtering (no source tree dump). Preserve queue items on any failed fetch, commit, merge or push. Repair all cron path/virtualenv/SSH assumptions; use absolute paths, explicit PATH, deterministic working directories, and lock files. Prove by observing **at least two SUCCESSFUL automatic scheduler-triggered cycles** (not just manually invoking the code); show actual crontab/service content and last GitHub commits.
- If no new binary data exists in a period, still push status (with timestamp, useful metrics, and backup health). **Status commits are not backups.** Never run `git add .` on the large source repository or commit raw in-flight trajectory files every 10 minutes.
- Verify alert/health semantics: if no heartbeat for >20 minutes, a push fails, an output is quarantined, the collector stops, or backups lag, report an explicit `STALE/STOPPED/BACKUP_LAGGING` status; never silently mark healthy. Provide persistent logs and retry queue.

## Work package E — REAL incremental backups for BOTH hosts

Known missing resource: user has **not designated a guaranteed durable off-site storage service**. Do not invent cloud credentials or claim off-site durability. Use verified, permitted **cross-machine copies as an interim protection**:

- **3D canonical on gvlab** → existing second physical disk `/ssd_scratch/nav_shelf66v3_backup/run_q2_parity` **plus** mirrored complete verified units to laptop `~/Desktop/shelf66v3_offhost_mirror/`. The laptop mirror must be hash-verified. Validate real free space and permissions.
- **2D canonical on laptop** → a **different physical machine**, gvlab, in a new namespaced directory under a writable, capacity-checked `/ssd_scratch` or another explicitly validated user-writable path. Copy **only completed and integrity-checked packed roots** (`records/`, `modes/`, `witnesses/` and necessary run metadata), not partial `parts/` files or a currently mutating JSON. Use atomic copy, SHA-256, source manifest and on-destination rehash; track completed/lagging/failed backup units. Keep enough disk headroom for BOTH datasets; never overwrite another project's files.
- Fix any existing backup index logic that would skip a missing/corrupt destination file simply because the stored index hash matches the source ledger. In `status4.py cmd_backup`, specifically: an index match **must not** skip re-verifying destination file existence and actual SHA. Retry/re-copy if missing/corrupt. Likewise, a failed rsync must never be reported as a verified current mirror. Add tests for deletion, corruption and network failure.
- Backups must continue after Claude's interactive session ends; host state and exact last backup hashes/UTC go into telemetry. Test a restore **from the backup into an isolated temporary directory**, checksum and open a representative saved witness/packed root, without modifying production.
- If a true durable off-site target (NAS/bucket) has not been supplied, explicitly mark `DURABLE_OFFSITE_NOT_CONFIGURED`; make clear that the two-host setup is interim and cannot protect against correlated loss. Do not block a scientifically safe collection solely because an unspecified cloud account is absent, **provided both interim verified backups run** and the user has authorised their residual risk through this instruction. If even interim cross-machine backup cannot be established, flag an outstanding blocker and avoid unattended long-running launch until a minimum safe backup route exists.

## Work package F — LAUNCH real production; do not stop at readiness

Carry out A–E and **launch both jobs**, independently as each host becomes ready. Execute 3D while preparing 2D; don't let 2D Q2's old gate unnecessarily delay the server.

**3D:** in gvlab checkout, after all guards and v4 authorisation pass, start `production_v4/launch_v4.sh --execute --policy-file production_v4/production_policy_v4.json --confirm <computed-v4-token>` in a named **tmux** session. Do not launch v3. Account for the wrapper's preflight and tests before the actual collector starts. Inspect process tree, assigned CPU mask, lock ownership, run manifest hashes, first committed units and real ledger/monitor evidence. Confirm 59,972-query v4 roster in `production_v4/run_q2_parity/`.

**2D:** after Q2 policy is frozen and every original safety gate passes, call the existing `launch_ready_2d_v2/launch_full_2d.sh --execute-full --confirm <current-Q2-token>`. It uses `nohup` by default; **verify the child process actually survives shell exit** and that `full_2d_v2/` has the correct `Q2` manifest; create a persistent tmux/supervision wrapper only if needed and only if it does not duplicate the coordinator. Confirm the worker count/CPU affinity/boost-off/AC and at least one completed packed root. Do NOT start Q1. Inhibit host sleep in an authorised user-level way while the laptop collector runs, without weakening thermal safeguards.

**Both:** check startup output and monitor after the first verified unit, at least one 10-minute automatic telemetry cycle, a successful GitHub push with both host status rows, and a successful source→backup→destination SHA verification for real collected data. If one host cannot launch, finish the other and give the exact minimal blocker, not a false dual-success claim. If the run ends during this handoff, carry out final audit instead of restarting it.

## Work package G — When runs finish (no fabricated completion)

- 3D `code/collect4.py --audit` must show **all units complete**, then `code/replay3d.py` must freshly verify **100% of stored positive witness associations**; validate split/no leakage, all negative categories and unlabeled semantics, and `code/q2roster3d.py utility` per stratum. Keep frozen experimental protocol.
- 2D `code_v2/launch_check.py audit` and integrity must pass with **100% of stored verified witnesses re-certified**, all requested Q2 rows accounted for and no leakage. Do not turn `NO_PLAN_FOUND`, `WORK_BUDGET_EXHAUSTED` or `UNLABELED` into global negatives.
- Publish compact final reports and immutable manifests; transfer large data separately and deliberately in manageable batches only if storage/repository policy permits. Back up final validated data off-host, hash-verify, and record restore verification. Do not claim either is complete before these gates pass.

## Forecasts: a planning estimate, NOT a guarantee

| Run | Physical queries | Expected active collector time | Conservative planning allowance |
|---|---:|---:|---:|
| 2D Q2 on laptop | 238,160 | ~3.25 days | ~4.87 days (1.5×) |
| 3D v4 on gvlab | 59,972 | ~15.6–17 h; held-out calibrated could be ~22.3 h | ~33.4 h |

The clocks start at **actual physical collector start**, not at Claude configuration. Re-estimate from measured first hours; keep a confidence range and report pauses/safety stops separately. 3D code startup includes preflight and tests. Running both simultaneously is permitted because they are on different hosts.

## Minimum final reporting format (facts, not promises)

At end of THIS execution session, report for **each host**:

- state: `RUNNING_VERIFIED`, `COMPLETE_AUDITED`, `BLOCKED_WITH_REASON`, or `NOT_LAUNCHED`; actual SSH host and run directory;
- exact frozen roster count, quota/policy/teacher hash, Git SHA/branch, user-authorisation source;
- invocation and tmux/nohup name, real PID and child-worker count, 1st completed root or query/ledger evidence, time of actual start;
- health: temperatures, CPU affinity, memory, disk, monitor last heartbeat, any safety stop;
- reporting service: **installed/disabled** user scheduler and proof of TWO *automatic* cycles, status-branch GitHub commits, whether GitHub push is up to date;
- backups: source/destination paths, total verified roots/units, most recent success, restore proof, any pending/failed units, and honest durable-offsite limitation;
- ETA measured vs initial forecast and first concrete next action if blocked.

Push an implementation + launch audit to the appropriate branches using normal fast-forward pushes; never force push, never push credentials/tokens/authorisation copy, and never claim periodic commits replace data backups.

**Success means BOTH collectors are really running (or already finished and audited), both are independently protected by scheduled hash-verified backups, and both produce 10-minute GitHub progress records. Anything less must be reported as partial completion with an exact blocker, not dressed up as success.**
