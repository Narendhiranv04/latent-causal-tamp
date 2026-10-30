# 0108 — Approach B X/Y, Phase 2: data interface and sidecar collection plan

**Verdict: PARTIAL.**
- **Done:** canonical X/Y identities and the versioned sidecar are implemented and tested.
- **Not possible from this dataset:** positive X and the matched travel J. Both need new teacher queries, planned below and **not run**.

## A. Canonical identities (`bxy_data.py`)

| Variable | Key | Shared when |
|---|---|---|
| X (physical ordered prefix + terminal connector to q_ref = q0) | `X:{root}:{o>c.o>c...}` in action order | never across orders; one per distinct ordered prefix |
| Y (target from q_ref in the hypothetical edited scene) | `Y:{root}:{sorted moved objects o>c}`, from S0 with the prefix's destinations applied ideally | identical final object poses, so A→B and B→A share one Y |
| F4 omission | recomputed sequence without action t, endpoint recomputed from S0 | the same key as any identical ordered sequence; no separate variable |
| zero-move | no X variable (X = 1 by definition); `Y:{root}:empty` = Y₀ | — |

## B. Sidecar `BXY_SIDECAR_V1` (`runs/approach_b/bxy/SIDECAR.json`)

- One entry per root, containing:
  - every catalogue prefix and omission X variable, and every Y variable;
  - the X → Y links;
  - the observations with their source;
  - the frozen catalogue (empty repair first, then the recorded B sequences in recorded order, all lengths up to 6).
- **Original root files are never written.** The dataset copy is read-only.

**Observations reused, where the semantics match exactly:**
- **Y:** `labels.original` and `labels.D`. Both query the target from `q0` with the same teacher and budget. That gives 1,150 Y observations: 860 train, 117 val, 173 test.
- **X = 0:** from B sequences whose relocation step j failed. The 203 failing sequences collapse to 146 distinct shortest failing prefixes r₁:ⱼ₊₁, each recorded once. The `verify_sequence` teacher is deterministic under a fixed per-query budget, so the prefix query reproduces the same failing attempt.
- **Never reused:**
  - **B whole-sequence y.** The target is run from the achieved state, so this is the legacy LB target, not X.
  - **Successful relocation prefixes.** The connector was never tested.
  - **Legacy travel.** It has no connector, and its target is not run from q_ref.

## C. Coverage gap

The data contains no X = 1 observation. As a result:
- **No X probabilities:** P(X = 1) cannot be learned beyond "low".
- **No coupling:** the coupling w_q has no informative paired supervision. There are 34 training prefixes with both X and Y observed, and all of them have X = 0.
- **No matched travel:** methodology §6.1 travel needs a matched X + connector + Y witness, and none exists.

## D. Sidecar-only collection plan (existing 231 scenes; requires authorization; not started)

The plan uses one fixed, versioned X teacher, `BXY_X_TEACHER_V1`: the `bd_2d` DetPhysics teacher with the same per-query budget `QB`.

**X query, per ordered prefix:**
1. Run `p16_common.verify_sequence` on the relocations only, with the achieved state carried between relocations.
2. Then run one **connector**: a free-arm transit from the terminal configuration to `q0` in the resulting scene, with the gripper free and nothing attached. This uses the `transit_plans` budget.
3. Label X = 1 only if every relocation and the connector are verified and replayed. Every other attempted outcome is 0, with the failing stage kept as metadata.

**Y query, per edited scene:** `bd_2d.t_goal` from `q0`, exactly as `labels.D`. Each identical scene is cached once per root.

| Plan | Queries | Estimated teacher CPU (from the recorded 23,914 CPU-s over 1,442 target queries + 1,163 sequence queries) |
|---|---|---|
| **P-min** (selection evaluation) | X for the 1,114 full catalogue candidates + Y for the 593 unobserved candidate endpoints | about 6k CPU-s (X) + 1,114 connectors + about 8k CPU-s (Y), roughly 4 CPU-h |
| **P-full** (every learned variable) | X for 1,858 distinct prefixes + Y for 1,698 unobserved scene variables | roughly 9 to 10 CPU-h |
| **Order contrasts** | the 88 same-endpoint reordered pairs already in the catalogues; both orders' X in P-min | included |

**Output:** a new sidecar `BXY_SIDECAR_V2`, holding parent root and query IDs, the teacher hash, the attempted flag, binary y, the failure stage, the witness IDs and travel J split by segment.

The legacy B labels stay untouched and remain the direct-LB baseline. On the lab server, P-min is about 15 to 30 minutes of wall time at the existing worker count.

## E. Files

`bxy_data.py`, `runs/approach_b/bxy/SIDECAR.json`, tests in `tests/test_bxy.py` (sidecar semantics, identities, split rule).
