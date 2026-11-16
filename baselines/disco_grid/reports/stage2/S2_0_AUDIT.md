# S2.0 — restored source and preservation gates

Run `stage2-20261117`, gvlab CPU only. Starting remote and local validation head
both `8c5213fd0c7cb739e2358452564320eac1891db5`; new worktree/branch
`naren/disco-grid-stage2`. No concurrent edits on the validation worktree were
observed. The unrelated main worktree's existing changes were preserved.

Stage 2 contract read completely. Existing implementation retained. Shared
snapshot/teacher contracts are read-only dependencies; this stage contains no
competing-method experiments. Source and checkpoint bytes are recorded in
`audit/input_audit.json`; all 56 archived checkpoint/teacher hashes match.
`archive_protection.json` protects all tracked preexisting reports and plan bytes.
The protection test checks that entire registry, including validation figures.

Unchanged suite: **35/35**, 52.62 s on gvlab CPU, CUDA hidden, one thread, nice +10.
Prediction preservation replay: **315/315 primary exact**, 1,785 archived arm
predictions regenerated without physics. See `base_tests.log` and
`preservation_replay.json`. These are preservation tests, not new evaluation.
The original ten lightweight tests are included in the 35-test suite.

Base 2D TRAIN/VAL/TEST: 3500/751/749; 3D:1766/364/370. Snapshot locks pass; raw,
input, family, layout and root split conflicts are zero. Full split×K counts and
independent-family counts are machine-readable in `audit/input_audit.json`.
O0 task dimensions are 143 (2D),97 (3D); O1 dimensions152/118. Actual model
context additionally includes the occupancy vector (64/36). O1 observes three
or seven joints as sin/cos/visibility. Gripper is physically carried, not learned.

Pinned reference `c62b32e5f6e40444459742525a86ffef620951aa` was rechecked clean on
host. Current reference locations: UCB at mcts.py:108, widening:416,
backup:741; leaf_stats at disco/data.py:17. Prior prose line numbers were stale.
UCB C1.5 and batch widening k2/alpha.3 agree; administrative censoring and
categorical actions/STOP are declared adaptations. Geometry, grasp families,
teacher budgets and terminal connector/canonical-Y rules remain unchanged.
Native mesh hashes have not been exhaustively re-audited.

Stage 1 crosswalk: V0 preservation → S2.0; V1 observed joints → S2.2/S2.6/S2.7;
V2 search/STOP/value → S2.2; V3 journaling/resume → S2.1; V4 independent data →
S2.3–S2.5. Old cross-method attestation is outside this contract and is not a
Stage 2 blocker. V6 reporting → S2.8/S2.9.

Current issues found in source: per-iteration checkpoint time was not incremented
until final return; trainer lacked optimizer/RNG recovery; policy training skipped
STOP-only datasets; separately normalized destination/object losses did not give
the stated joint NLL when STOP rows were present; fresh-width Q initialization
confounded matched O0/O1 fits. In-flight result identity and per-query parent wall
limits required strengthening. Narrow prospective fixes have been made; archived
weights/labels/reports remain unchanged. Physical parity and new physical-tree
gates are recorded separately and must pass before expanded collection.

Commands: see `REPRODUCTION.md`; original source audit runner `audit_inputs.py`,
archive replay `replay_preservation.py`, and read-only four-host inventory
`inventory_hosts.py`. `host_inventory.json` contains UTC timestamps, hardware,
load, RAM, disk and process names without other users' command arguments. A
nonzero inventory shell return on inventory-only hosts reflects the final test
for a nonexistent local DISCO directory, not failed SSH authentication.
