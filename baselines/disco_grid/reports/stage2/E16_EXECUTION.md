# E16-v1 execution record

Authorized by the user's exact session reply, “Authorize E16-v1 for both domains”.
`COMPUTE_ENVELOPE_REQUEST.json` and `cohorts.json` freeze the limits and root registry.
This authorizes TRAIN collection and fitting only. VAL physical studies and final
TEST execution require separate envelopes. No TEST labels select these models.

One gvlab CPU worker, one thread, nice +10, GPUs hidden. The controller checks
existing host/load/RAM/disk guards and the cross-job physical lock. Per-root pilot
ceilings remain enforced. Adapter calls are durable intents, including interrupted
queries. Trees with unresolved intents are quarantined and retained in coverage.
The controller refuses ambiguous restart; clean model epochs support exact resume.

Collection: 16 distinct source components per domain, two fresh rounds, caps
32 calls/root/round in 2D and 16 in 3D. Maximum 1,024/512 adapter calls,
4/8 CPU-hours and active wall-hours, query limits 60/120 seconds. Each run reserves
60 seconds per envelope for measured controller overhead plus five seconds of
termination grace. Child RSS is capped at 3 GiB, reserving 1 GiB for the parent.
New campaign disk ceiling is 10 GiB. Fitting has an aggregate 1,800-second CPU/wall
limit. A cap is a ceiling, not a claim that every call or root completed.

R0 uses P0 seed 0. R1 uses the completed O0 P1/Q1 seed 0, with new search seeds.
P2 fits pooled R0/R1 executed trees. All-feasible O0/O1 and successful-only O0
controls use model seeds 0/1/2 and 45 fixed epochs. O0/O1 supervision is identical;
O1 uses actual saved joints. Successful-only P2 starts from all-feasible P1 to
isolate the current edge-selection intervention. Q supervision remains all decided
visited leaves; shaped progress is not a success target.

Fresh K3 pilot `pilot_3d_k3_20261117`, source a2df650174a7e228c6778eb73f208f83c0f5b253:
24 completed calls = 15 feasible relocation transitions + 9 terminal calls;
0 verified solutions, best shaped path return 0.566, 3 completed iterations.
Parent-measured CPU 399.403797 s, elapsed 400.546165 s, peak child RSS 790940 KiB.
This is TRAIN search evidence, not held-out model performance.

Prelaunch verification: 46 passing tests plus an archive-path failure in an
incorrectly flattened deployment; the complete-repository deployment then passed
all 17 Stage 2 tests, including the archive registry and aggregate-budget tests.
The original 30 non-Stage-2 tests passed in the first invocation. Logs retain the
failed packaging attempt; no archive hash mismatch was observed.
