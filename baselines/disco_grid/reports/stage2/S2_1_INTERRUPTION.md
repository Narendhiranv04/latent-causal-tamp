# S2.1 — interruption reconciliation

The old 3D K3 run `pilot_3d_k3_seed20261116`, root `D3H_GVLAB_366ce85b50`, remains
unchanged. The complete recursive file inventory and hashes are in
`audit/interruption_ledger.json`. There are nine NPZ witnesses, a first-iteration
`IN_FLIGHT=0` marker, manifest, PID and parent-watchdog records. There is no saved
query intent, physical result or accepted child/parent state checkpoint.

Verdict: **QUARANTINED_UNRECOVERABLE**. Adapter invocation count, internal planner
count and CPU seconds remain **UNKNOWN/null**. The 300 s limit plus five-second
grace is documented; it is not a physical negative. Witness plans do not by
themselves certify execution acceptance, physical state continuity or terminal
success. No ambiguous query is replayed as independent evidence, no old PID is
signalled, and no old artifact is amended. Any diagnostic rerun needs a new ID.

New code writes fsynced intent before dispatch, exact parent blob/hash, process
start identities and configuration digest, then returned result/raw teacher
outcome and child state hash. The parent independently monitors each active query
and aggregate wall time; teacher SIGALRM replacement cannot extend these limits.
Only the child created by this run is signalled, with identity validation.
Clean restart validates contiguous completed query IDs, counters, state/result
hashes, RNG/configuration and backend caches. An interrupted query/tree is
quarantined. Time is charged at every completed iteration and across parent
attempts, including cancelled work; unknown internal IK/RRT counters remain null.

Deterministic crash, checksum, exact-resume and watchdog fixtures are in
`tests/test_stage2.py`. Real journal/teacher verification and measured accounting
are acceptance evidence only when their run records exist; see S2.3.
