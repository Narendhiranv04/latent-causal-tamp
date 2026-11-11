# Claude Opus 5.5 High — 3D Shelf Placement Mock Kickoff

You are implementing the **Approach B 3D placement-only dataset extension mock** on the lab server `nav@gvlab`, whose Xeon Gold 5317 exposes **12 physical cores / 24 logical CPUs**. My **absolute project CPU ceiling is 18 logical CPUs**, including any concurrently active 3D generation/extension jobs. **Do not assume 18 workers will be fastest.**

**Read `Approach_B_SHELF66V3_3D_Mock_Implementation_Instructions_v1.md` in full first and follow every scientific, engineering and safety gate.** Also read `final-fixed-methodology-1.pdf`, especially §§5, 7, 8 and 14. The scientific method takes precedence over shortcuts.

Repository: `Narendhiranv04/rss-ebm-infeasibility`. Audit `yadu/dataset-3d` (SHELF66V3 shelf dataset, snapshot commit `8032ad0bf842a490897a8247ee46312036c12546`) and the 2D placement extension on `naren/2d-dataset-relocation` for architectural patterns only. Inspect the **actual live server filesystem and currently running jobs**; do not assume the GitHub snapshot is current. Do not mix the older 8×8 open-tabletop corpus with the 6×6 SHELF66V3 shelf source.

## Your objective

Build a **minimal, correct, independently versioned, physically verified 3D conditional-placement teacher** and run a **bounded, stratified 3D mock** sufficient to decide whether a full shelf-placement sidecar could later be launched. The mock must reproduce the Approach B event: **object already validly grasped → lift/carry → supported placement/release → retreat**. It must **not** require the original pick approach, closure, return-to-ready, inter-action connector, target-task success, or known repair sequence. Full `plan_pick_place()` results are not replacement labels. Confirm the SHELF66V3 finger-width correction is respected.

## Required implementation and evidence

1. **Audit live source data and processes first.** Count valid selected roots and complete source witnesses by K, verify SHELF66V3 protocols/hashes and environment, confirm whether original 3D generation is still running, and document how the ≤18 logical-CPU limit can be enforced. If the ongoing generator already occupies the allocation, **do not launch competing mock workers or kill it**. Stop and report the conflict until I authorize coordination.
2. **Preserve everything original.** Create a new `dataset_placement_extension_v1` sidecar/worktree and immutable source manifest; leave selected roots, ledger, existing 3D/2D datasets and archived witnesses unchanged. No pushes/merges.
3. **Implement correct 3D held-state physics.** Enumerate 16 azimuth × 2 height grasp poses and allowed IK branches, certify valid attached initial states, plan and physically execute ONLY carry, release and retreat, check supported final pose, arm/hand/object collisions, no-overpass, ceiling and displaced-neighbor conditions. Store actual seven-joint witness trajectories and gripper/object/phase evidence.
4. **Freeze train-only mock roster in advance.** Use ≤24 selected roots across available K0–K3 classes and ≤240 distinct candidate placement queries spanning root, 1-edit and 2-edit hypothetical scenes, near/mid/far/vacated destinations and box/cylinder objects. Use geometry-only candidate selection, root-lineage splits and static-ineligible controls. No protected repair metadata.
5. **Benchmark instead of guessing budgets.** Compare predeclared 4/8/16/32 candidate modes and 500/1,500/5,000 RRT outer-iteration settings as appropriate, with counted extension/collision/IK work and a small stronger-reference subset of ≤60 preselected queries. Evaluate adaptive escalation and relative missed positives with confidence intervals. Preserve operational failures vs interrupted/unlabeled distinctions.
6. **Benchmark 8, 12, 16, 18 workers** using matched small tasks. Choose the fastest safe actual throughput, never exceed **18 logical CPUs for the entire concurrent project workload**. Restrict numerical threads, check cpusets/memory/disk, and do not copy AMD laptop boost settings to the Xeon host.
7. **Prove integrity:** two clean reproducible chosen-worker runs, serial overlaps, deterministic mode/work accounting, fresh independent physical witness replay, SIGKILL only your own mock workers followed by byte/canonical-identical resume, source hashes intact, no validation/test leakage, representative trajectory GIFs and scene visualizations.
8. **Forecast future collection carefully** from the actual live selected-root roster and costs stratified by K, distance, edit depth, object shape and clutter. Give expected CPU-hours, wall days, conservative range, storage and a guarded future launch runbook. Do not assert that a 3D production runtime can be inferred from the original scene-generation runtime.

## Absolute prohibitions

**DO NOT START THE FULL 3D PLACEMENT COLLECTION, FILL MISSING K4/NONE QUOTAS, MODIFY THE SOURCE GENERATOR OR ACTIVE JOB, RUN 2D PRODUCTION, TRAIN THE SAMPLER OR X/Y, PUSH/MERGE CHANGES, OR VIOLATE THE 18-LOGICAL-CPU CEILING.** Do not weaken or retroactively adjust safety/scientific gates to obtain a pass. If a correct simulated post-grasp state cannot be established, mark the mock blocked rather than silently substituting the full pick skill.

At the end write `LIVE_SOURCE_AUDIT.md`, `MOCK_REPORT.md`, `LAUNCH_READINESS_DECISION.json` and `RUNBOOK.md`; include exact code changes, verification evidence, statistical limitations, full output paths and hashes. Give the explicit verdict **`MOCK_PASS`, `MOCK_FAIL`, or `MOCK_BLOCKED`**, with separate semantic, reproducibility, physical witness, safety and coverage verdicts.

**STOP completely after the mock and its readiness report. I will authorize any full dataset extension separately.**
