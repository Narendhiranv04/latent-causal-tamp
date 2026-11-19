# Counterfactual audit plan: handoff vs geometric attribution (NOT AUTHORIZED, NOT RUN)

**Goal.** Resolve the mechanism behind the **1,693 K2/K3 roots** (2D 1,128, 3D 565) whose `unknown_control_requirements` is non-empty.

That is every K2/K3 root except:
- `NO_ORDER_CONTRAST`;
- `LEGACY_TARGET_ONLY`;
- `NO_VERIFIED_SUCCESSFUL_ORDER`;
- 2D roots whose every relocation failure is explained by a configuration-independent certificate.

So it includes:
- all `PLANNER_LIMITED_OR_INCONCLUSIVE` (2D 688, 3D 171) and all `UNKNOWN_REQUIRES_CONTROL` (2D 69, 3D 385);
- `CONNECTOR_ONLY` roots, for the connector contrast;
- geometry-confirmed 2D roots that still have unexplained failures.

The plan does this without changing any existing label:
- Results go to a separate audit store.
- The teacher labels of the frozen dataset stay as they are.

## Queries (`MISSING_COUNTERFACTUALS.jsonl`, deduplicated)

For each such root, with A = its selected assignment:

| Query | What it measures | 2D | 3D |
|---|---|---|---|
| REF a, P (\|P\| = 1) | F(a \| S_P, q_ref): P2 for singleton predecessor sets | 5,142 | 3,306 |
| REF a, P (\|P\| = 2) | F(a \| S_P, q_ref): P2 with both others moved | 2,190 | 1,632 |
| CARRIED a, prefix | F(a \| S_P, q(prefix)) for prefixes never executed (orders stopped earlier) | 889 | 682 |
| **Total** | | **8,221** | **5,620** |

**Queries that need no new run:**
- P = {} is already observed at step 0 of every order, starting from q_ref.
- In 2D, REF queries already implied 0 by a configuration-independent certificate are omitted.

**What each comparison establishes.** P4 pairs each failing carried step (already recorded) with its REF query at the same S_P:

| Reference start (q_ref) | Carried start (achieved q) | Reading |
|---|---|---|
| Succeeds | Fails | Handoff |
| Fails | Fails | Geometric or planner |
| Reference succeeds; P = {} also succeeds | Another P fails | Blocking |
| Fails at P = {}; succeeds at P | — | Enabling |

## Protocol

1. **Code.** `controls.py`, using the unchanged DISCO stage-2 `RepairEnv`, which wraps the finalized teachers' relocation planners.
   - REF = state rewritten to S_P with the robot at q_ref:
     - 2D: payload cells and q;
     - 3D: `bd_3dt.settle`, the same primitive the generators' independence checks use.
   - CARRIED = reset, then execute the prefix with carried state.
   - Only the robot start differs between REF and CARRIED.
2. **Interface check.** `controls.py --dry-run` has passed on 2D, with no planner call:
   - the S_P cells are correct;
   - q = q_ref;
   - P = {} reproduces the reset state hash;
   - the action stays legal after P.
   - The 3D state builder is implemented but not exercised, because doing so would initialise MuJoCo.
3. **Seeds.** Seed 0 for every query.
   - Seeds 1 and 2 only where seed 0 returns a planner-limited 0: 2D `UNKNOWN_PLANNER`, 3D NO_PLAN_FOUND or RRT exhaustion.
   - A planner-limited 0 is never read as physical impossibility. Unanimous planner-limited zeros stay "planner-limited".
4. **q_ref reachability.** A q_ref start inside S_P is a diagnostic intervention. If q_ref is in collision in S_P, the result is recorded as `QREF_NOT_CLEAR` and is not a label.
5. **Validation before the full run:**
   - REF with P = {} must reproduce the recorded step-0 outcomes.
   - CARRIED for executed prefixes must reproduce the recorded step outcomes.
   - Target: 100% agreement on the pilot's reproducible subset; otherwise stop.
6. **Isolation:**
   - Outputs go to `audits/order_dependency_final/counterfactual_runs/`.
   - The snapshot, labels, manifests and checkpoints are unchanged; sha256 is checked before and after.
   - The V3.4 cohort is excluded by construction (gate 2).

## Cost (from measured historical teacher costs)

Measured per-step CPU:

| Domain | Successful steps | Failed steps |
|---|---|---|
| 2D | median 2.0 s, mean 3.2 s (n = 1,008) | mean 9.2 s, p90 32 s (n = 2,136) |
| 3D | median 10.1 s, mean 12.3 s (n = 3,061) | mean 25.1 s, p90 42 s (n = 419) |

Sources: 2D dep/hard store permutations; 3D fresh-env legacy executions.

| | Queries | Seed-0 CPU | + reseeds (assume 40% planner-limited) | Total |
|---|---|---|---|---|
| 2D | 8,221 | ≈ 14 CPU-h | ≈ 16 CPU-h | **≈ 30 CPU-h** (≈ 1.5 h wall on 20 cores) |
| 3D | 5,620 | ≈ 28 CPU-h | ≈ 31 CPU-h | **≈ 60 CPU-h** (≈ 3 h wall on 20 cores) |

- CPU only; no GPU.
- CARRIED queries add their prefix steps (+1–2 transitions each); this is included in the margin.

## Smallest meaningful pilot (`PILOT_QUERIES.jsonl`)

**Selection:**
- 70 TRAIN roots: in each domain, 8 K3 + 4 K2 per source family, chosen deterministically by sha256(root_id).
- 600 queries: 2D REF 230 + CARRIED 16; 3D REF 314 + CARRIED 40.
- Cost ≈ 4 CPU-h, about 20–30 min wall on 10 cores.

**Purpose:**
- validate the interface on both domains;
- measure q_ref-in-S_P clearance rates;
- estimate the share of planner-limited REF outcomes, which sizes the reseeding;
- give a first estimate of the handoff vs geometric split per family.

**Decision after the pilot:**
- If REF success equals CARRIED success at more than 95% of failing steps, handoff is rare. Run the full audit on the K3 hard-order and dependence families only.
- Otherwise run everything.

## Authorization

- **No new expensive planner or MuJoCo calls are authorized by the request that produced this plan.**
- `controls.py --run` refuses unless both conditions hold:
  1. the user has added a line `APPROVAL_TOKEN: <token>` to this file;
  2. `ORDER_AUDIT_EXECUTION_APPROVED=<token>` is set.
- Hosts and limits follow the standing compute rules: laptop minus 2 cores, gvlab2 minus 4–5, enigma ≤ 15 inside its workspace, never blackwell.
