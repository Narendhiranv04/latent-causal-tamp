# Validation decision — 17 November 2026 (IST)

The implementation is substantially corrected and auditable. The evidence still
supports a **pilot baseline**, not a completed strong, matched publication
comparison. No new DISCO task-success improvement or Approach B superiority is
claimed.

| Stage | Verdict | Evidence / remaining gate |
|---|---|---|
| V0 source/host audit | DONE | Current pushed source recovered; four hosts authenticated read-only; archived primary predictions 315/315 replayed; original tests 10/10; four fresh physical order replays 4/4. Native meshes and all48 historical parity queries were not re-audited/re-executed. |
| V1 state conditioning | DONE (implementation) | Versioned O0/O1, old checkpoints preserved, policy/value/training/inference wiring; final 35 tests pass. Actual O1 closed-loop task benefit remains unmeasured. |
| V2 MCTS/STOP/value | PARTIAL | Deterministic visits/targets/backups/call caps, unique STOP evidence, censoring, strict pairing, VAL-only calibration implemented/tested. Intermediate STOP and continuation calibration need physical validation. |
| V3 stronger-data pipeline | PARTIAL | Frozen independent-family manifest, resolved budgets, atomic clean-boundary resume, per-query write-ahead results/state journal and external watchdog. Independent 2D pilot complete;3D interrupted before first tree checkpoint. Full optimizer-state training resume remains absent. |
| V4 expanded training | PARTIAL |18 matched fixed-schedule R0 fits completed (3 arms×3 seeds×2 domains). These reuse small historical trees. Larger independent-root and search-budget training ladders NOT_RUN. |
| V5 paired evaluation | BLOCKED | Candidate root pairing exists; exact V3/V3.1 model/input/teacher attestation incomplete on authorized host; physical O0/O1 matched evaluation NOT_RUN. |
| V6 release | PARTIAL | Corrected methods/results, nine PNG/SVG figure pairs, scripts, manifests and checksums. No full 3D arm trajectory/video, final paired tables or independent-root performance learning curves. |

**Source and changes.** Source branch remains untouched at
`b4414510cbc79c5198e8f6a0d14cdee33283504a`.
Dedicated branch: `naren/disco-grid-validation`.
Implementation commit: `2a78dc397a7fe401ed24d7ce1a73bb0f31796f19`;
audit commit: `827f06bd52e81cf18059133f2a0b1c802cb4c5be`.
The final evidence commit and remote push SHA are given in the execution reply;
verify with `git ls-remote origin refs/heads/naren/disco-grid-validation`.
No source/Approach B branches, user changes, frozen datasets, historical reports
or checkpoint bytes were overwritten. Full historical report/doc preservation
and deployed checkpoint/source rehash are recorded in release_verification.json.

Code changes: `env.py`, `policy.py`, `mcts.py`, `distill.py`, `data.py`,
`evaluate.py`; bounded collection and matched training drivers `collect.py` and
`ablate.py`; `tests/test_validation_v2.py`; README/config clarification. Actual
teacher/planner source files are read-only. Administrative budget censoring is
explicitly prospective and must be common across methods before a paired claim.

**Workloads.** All tests, physical replays, training, collection, analysis and
plotting ran on gvlab CPU, one thread per process, low priority, GPU use zero.
Other hosts had no DISCO jobs or transfers. Two live shared GPU workloads and
16 ongoing Approach B CPU workers were observed; none was interrupted. Only our
own 3D pilot PID was signalled by an identity-checked watchdog.

**Measured evidence.** Historical primary O0:11/135 task prediction trials over
45 roots 2D (8.15%, root CI 3.70–14.07%);15/54 over 18 roots 3D (27.78%, CI 11.11–46.30%).
These are exposed historical TEST results. Corrected value differences are
−2.22 [−7.41,+2.96] points 2D and+7.41 [−5.56,+20.37] points 3D. Neither establishes a
value gain. The old whole-method Approach B percentages remain unpaired.

Independent 2D K3 root `D2H_7aa5bebefe`:10 transitions+6 terminal invocations,
8 feasible edges,0 solutions,99.582 seconds wall /99.377 seconds CPU.
Independent 3D K3 root `D3H_GVLAB_366ce85b50`:stopped at 300+5 seconds, first iteration
in flight. Actual calls and CPU seconds unavailable; no false zero-call or
negative-label claim. Partial witnesses and IN_FLIGHT marker are preserved;
automatic resume is refused. Per-query journaling was added after that finding
and validated with deterministic state/result fixtures.

Frozen base root counts: 2D TRAIN/VAL/TEST 3500/751/749; 3D 1766/364/370. Historical
MCTS uses 24/12 TRAIN roots; fresh pilots add one excluded-historical-family root
per domain, but only the 2D tree completed. New matched fits reuse the original
R0 trees and network seeds 0/1/2; they are not independent search repetitions.
No TEST outcome selected a new threshold, model or training root. Optional STOP
calibration uses 751/364 VAL roots with family-disjoint fit/audit halves and is
not adopted as the primary selector.

**Next highest-value action.** Reconcile the interrupted 3D root from its saved
witness/store files, then perform one journalled, externally bounded TRAIN search
with measured depth3/STOP yield before requesting a larger aggregate envelope.
In parallel, freeze the actual Approach B V3 and V3.1 checkpoint/input/teacher
registries on the authorized host. The candidate pairing manifest is ready;
attestation must precede physical paired evaluation. Reserve a new untouched
family-held-out confirmation cohort for any final generalization claim.

On-host experiment root: `/scratch/nav/disco_grid/validation_v2/`.
Exact run/checkpoint paths and hashes: `new_training.json`,
`training_pilots.json`, `artifact_inventory.json`, `archive_replay.json`.
See METHODS_RESULTS.md for publication text and INDEX.md for all artifacts.
