# Claude Opus 5.5 High — kickoff prompt: repair and revalidate ONLY the 2D placement smoke test

Read the attached **`Approach_B_2D_Placement_Smoke_Repair_Instructions_v2.md`** completely and implement its smoke-only instructions. Use **`final-fixed-methodology-1.pdf`** as the scientific authority, and the previous `Approach_B_Placement_Dataset_Extension_Smoke_Plan.pdf` as historical context where it does not conflict with the new repair instructions.

You are working in my **existing local worktree**, reported at:

```text
/home/naren/Desktop/rss-placement-smoke
branch: naren/placement-smoke-2d
baseline commit: 9e640690
```

**Inspect, do not assume.** First read the actual uncommitted `placement_smoke.py`, `placement_smoke_check.py`, `test_placement_smoke.py`, the full `smoke_20261106/report.md`, source dataset/teacher modules, and saved outputs. Preserve the failed smoke, dataset, and all Git changes. If paths/status differ, report the real state. Do not substitute the prior text summary for source or evidence.

The previous smoke failed reproducibility: short wall-clock caps caused planner cutoff under 28 workers, leading to one binary label flip and 12/35 differing witness sets across repeats. Fix this with **deterministic work-limited planning** (including failed extension attempts, collision evaluation budgets and deterministic shortcutting); keep wall/temperature limits as **emergency interrupts only**. A completed budgeted search without a verified placement witness gives operational binary `0`; a fully verified witness gives `1`; unattempted or safety-interrupted work has `label=null`, not a third observed class and not a fake zero.

**Scientific boundary:** the placement sampler teacher starts from a valid, **already-held** post-grasp state and verifies **carry → placement/release → local retreat**. It must **not** reject an otherwise valid placement just because the original pick approach or closure motion is blocked. Check the existing `skill.screen_pick()` dependency carefully, and ensure saved witnesses have correct post-grasp attachment transforms, phases and independent physical certification. Do not modify the full X/Y meaning or assume hypothetical intermediate scenes were physically executed.

Reuse the **same frozen tiny 35-query, four-root 2D roster** (including the previously occupied-then-vacated edited-scene example), not a new dataset. Preserve 48×48 mode identities and honest disjoint accounting; record which pairs were screened, motion-planned, successful, failed, reused or unattempted. Keep authentic trajectories as compressed NPZ with content hashes and resume-safe references. Recompute mode counts under the corrected post-grasp contract—do not inherit the old 70,825 rejection count uncritically.

Run only:

1. A serial correctness/real-witness replay pass.
2. The **same roster** in two fresh 16-worker runs, comparing canonical semantic outputs.
3. Two fresh **28-logical-CPU** stress runs **only if safe preflight and thermal monitoring permit**. Use one numerical thread per worker, pinned allowed logical CPU IDs, monitor memory/swap/temperature and cancel safely without assigning false zero labels. CPU affinity is not a cgroup hard quota; report enforcement truthfully.
4. One deliberate worker interruption/resume test; verify committed records and original dataset hashes remain unchanged.
5. Updated unit/integration tests, real placement map/GIF and `smoke_fix_report.md` with exact commands, scientific fingerprints, source changes, resource observations, and separate core/stress verdicts.

**Do not** train cVAE/flow/X/Y, collect a larger dataset, create or label 3D scenes, change the frozen Approach B architecture, touch the remote server, commit/push, or progress past the smoke test. If a run is blocked by safety or missing files, report `SMOKE_BLOCKED`; do not tune outcomes to force `PASS`.

Execute the task end to end within this smoke-only scope, and **STOP** after presenting the actual evidence and the final `SMOKE_PASS`/`SMOKE_FAIL`/`SMOKE_BLOCKED` verdict. Follow the attached instruction Markdown's test gates and final-report format exactly.
