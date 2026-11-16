# Observation, search, STOP and value audit

O0 `o0_v1` preserves every historical feature dimension and schema-free checkpoint.
It consumes observable geometry/goal/q_ref context, structural edits, moved masks
and remaining horizon. Intermediate achieved q and gripper state are absent.
O1 `o1_qt_v1` appends `[sin(q),cos(q),visible_mask]`: 9 features in 2D and21
in 3D. This analytic normalization needs no held-out statistics. Actual-root or
executed-node joints are supplied to destination/object policy and Q(h,a).
The gripper remains excluded (no reliably common observation schema was added).

P0 Q2 lacks intermediate q. Explicit O0→O1 transfer zero-pads new input columns;
existing weights/normalizers transfer exactly. Physical saved node blobs supply
q during tree extraction; state hash/prefix lineage must agree. New MCTS node
observations and closed-loop deployment request achieved q. Predicted edits erase
q; O1 rejects both predicted observations (even forged q fields) and the entire
strict open-loop sequence function. Policy/value schema mismatch and unsupported
checkpoint downgrade fail clearly. No Approach B weights, energies or labels are
neural inputs. Root K/NONE are offline strata/metrics only.

Synthetic tensor tests demonstrate O0 invariance under pure q substitution, O1
sensitivity in tensors and policy/value scores, shape/visibility/finite checks,
old checkpoint byte-equivalent loads, controlled transfer, real training/reload,
and no oracle calls before open-loop commitment. `figures/same_geometry_different_q`
uses a saved physically achieved pre-STOP state and its accepted connector q_ref
with identical endpoint cells; these are static configurations, not interpolated
motion. Full 3D arm trajectory rendering remains unavailable.

Search remains UCB, C1.5, k2, alpha.3, batch widening. Returns telescope in the
geometric reward and backups match the audited upstream root-path-return mean.
Toy tests replay every iteration's leaf, visits, Q and return analytically.
Failed STOP leaves a prefix open; max depth remains three relocations. Decided
visited descendant leaves set Q targets; unresolved/unvisited leaves are censored.
All feasible executed edges supervise policy. Successful-only changes policy
rows, not the value labels. A cached decided STOP is one physical observation
(weight log2), even after repeated visits. No standalone feasibility guarantee
or worldwide probability calibration is claimed for continuation Q.

Corrections: strict transition+terminal call caps (including final STOP), explicit
resolved config, atomic nodes/RNG/counter/trace checkpoints, model/scaler/adapter
fingerprints on resume, cooperative cancellation, and refusal to resume an
unreconciled IN_FLIGHT tree. New write-ahead query journals charge before a call
and save exact returned state/result blobs; this addresses the measured loss of
partial accounting in the early 3D pilot. The journal improvement itself was
validated on deterministic fixtures, not a second physical collection campaign.

The teacher installs its own SIGALRM; an outer in-process timer is insufficient.
The final collector has an independent parent watchdog (five-second cancellation
grace), tested against a child replacing the alarm and ignoring SIGTERM. The
session's early 3D pilot was stopped by an independently attached watchdog at
300+5 seconds. No other user's process was signalled.

Administrative censoring is a **prospective interpretation revision**, not a
teacher/planner/budget change: preserve raw statuses; UNKNOWN_BUDGET/TIMEOUT do
not become new physical-negative supervision. All archived trees were scanned:
zero affected STOP records. Archived labels/reports remain untouched. Both
methods must explicitly use the same interpretation for any future paired claim;
the historical teacher's protocol-relative negative is not global impossibility.

VAL-only root-STOP affine-logit calibration is an optional named task adaptation;
default raw-Q ranking is preserved. It changes no intermediate STOP score and
has not been adopted as the primary selector. Its family-disjoint validation
audit reports calibration only, not verified repair success.
