# order_dependency_final: read-only order-dependency audit of the final 2D/3D datasets

**Goal.** Separate handoff (carried robot configuration) dependence from geometric precedence in the frozen final datasets:
- 2D: 5,000 roots;
- 3D: 2,500 roots;
- snapshot `abf_9de85710c2a7103f`.

**Start with** `AUDIT_REPORT.md`.

## Reproduce

```bash
cd audits/order_dependency_final
python3 audit.py              # ~3 s; reads only; writes the JSON/JSONL artifacts below and prints GATES.json
python3 audit.py && sha256sum *.json *.jsonl   # run twice and compare: outputs are byte-identical (gate 12)
```

**Inputs** (laptop paths, overridable by environment variables):

| Input | Path |
|---|---|
| Snapshot | `$ABF_SNAPSHOT` (default `~/abf_v3_laptop/root/snapshot/abf_9de85710c2a7103f`) |
| Final generation tree | `$FINAL_GEN` (default `~/Desktop/boltzmann_lfd/final_dataset_generation`): readiness-gate manifests, 3D replay results, selection manifests, dep/hard stores, fresh-env legacy files |
| Raw original roots | the `~/abf_v3_laptop` mirrors |
| Per-scene legacy permutations | `order_classification_{2d,3d}` |
| V3.4 private index | its root ids only, used solely to prove the cohort is excluded |

## Artifacts

| File | Content |
|---|---|
| `AUDIT_REPORT.md` | Construction, evidence, classification, learning claim, required corrections, gates |
| `DATASET_SUMMARY.json` | Counts by domain, split, K, source and family; legacy vs finalized order strength; classes and flags; missing-query counts; pilot |
| `ORDER_DEPENDENCY_CLASSIFICATION.jsonl` | One row per K2/K3 root (see below) |
| `FAILURE_MECHANISM_SUMMARY.json` | Order-level failure *locations* and teacher *kinds* (legacy and finalized), not causes |
| `MISSING_COUNTERFACTUALS.jsonl` | Deduplicated controlled queries (REF from q_ref, CARRIED) needed to resolve unknown mechanisms |
| `PILOT_QUERIES.jsonl` | The smallest representative pilot subset (70 TRAIN roots) |
| `GATES.json` | Acceptance gates 1–14 per domain |
| `COUNTERFACTUAL_AUDIT_PLAN.md` | Bounded execution plan, cost, validation, authorization (not run) |
| `controls.py` | REF / CARRIED query implementation on the unchanged DISCO `RepairEnv`. `--dry-run` builds states only; `--run` refuses without user approval |

**Each `ORDER_DEPENDENCY_CLASSIFICATION.jsonl` row contains:**
- the assignment;
- all permutations, each with finalized X, phase, kind, legacy y, legacy failed step and kind, and provenance;
- omission orders;
- P1 (step-0 from q_ref);
- flags and evidence;
- the primary class;
- what remains unknown;
- generator provenance;
- the raw-record path.

## Interpreting classes

**Primary class (one per root):**

| Class | Meaning |
|---|---|
| `GEOMETRIC_*_CONFIRMED` | 2D only. A configuration-independent `CERTIFIED_INFEASIBLE` relocation certificate gives a matched object-state comparison at a common configuration |
| `CONNECTOR_ONLY` | All relocations succeed in every order; only the terminal connector differs |
| `LEGACY_TARGET_ONLY` | Every finalized order succeeds; only the legacy target-from-achieved-q differed |
| `PLANNER_LIMITED_OR_INCONCLUSIVE` | Every relevant failure is budget-limited (2D UNKNOWN_PLANNER, 3D NO_PLAN_FOUND), with no controlled contrast |
| `UNKNOWN_REQUIRES_CONTROL` | Certificates or contrasts exist, but the mechanism cannot be isolated without P2/P4 controls (all 3D) |
| `HANDOFF_ONLY_CONFIRMED`, `MIXED_CONFIRMED` | Never assigned: no record starts an intermediate step from q_ref |

**Flags (non-exclusive):**

| Flag | Meaning |
|---|---|
| `CARRIED_STATE_EFFECT_AT_FIXED_IDEAL_GEOMETRY_*` | Same action, same predecessor set, different predecessor order, different outcome |
| `GEOMETRIC_*_CERT_SUPPORTED` | 3D certificate copied from the legacy same step; q-dependent IK-branch caveat |
| `SUSPECTED_*` | Confounded comparisons: geometry and carried q both changed |
| `UNEXPLAINED_RELOCATION_FAILURES_REMAIN` | Some failure is not covered by a configuration-independent certificate |
| `SNAPSHOT_LEGACY_Y_INCOMPLETE` | Gate 4c exception |
