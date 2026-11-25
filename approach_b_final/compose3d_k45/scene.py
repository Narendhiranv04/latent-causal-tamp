"""Public 3D scene views: hypothetical rebasing, temporary-task retargeting and the shared global action grammar (plan.md section 2).

A row is a `benchmark.public` 3D row: inputs = contracts.view3d (ids, xy0, cells0, attrs [is_box, is_cyl, size, height, is_target], tid,
goal xy, goal_cell, base, ctx = sin(q_ref) | cos(q_ref) | goal xy | target size, height, is_box, grid, legal_cells, q_ref, cell_xy).
Nothing here reads labels, K, witnesses or the teacher.  Rebasing copies the record (no aliasing), keeps every object, id, size, height,
the reference pose and the object order; only cells0 / xy0 of moved objects change.  Retargeting rewrites tid, goal, goal_cell, the
is_target column (index 4) of EVERY object and the ctx goal / target-geometry slots (derived from len(q_ref), not hard-coded).
`legal_cells` of a rebased row excludes the forbidden set (original occupancy, original goal, reserved destinations), so the frozen
sampler's own legality mask (search.Root.legal_dests) enforces the no-vacated-cell grammar on every hypothetical scene."""
from __future__ import annotations

import copy, hashlib, json

MAX_LEN = 5


def ctx_slots(inp):
    nq = len(inp["q_ref"])
    assert len(inp["ctx"]) == 2 * nq + 5, "unexpected 3D ctx layout"
    return slice(2 * nq, 2 * nq + 2), slice(2 * nq + 2, 2 * nq + 5)


def key(row):
    return hashlib.sha256(json.dumps(row["inputs"], sort_keys=True).encode()).hexdigest()[:20]


def forbidden(row0, reserved=()):
    """Cells no corrective action may use: every ORIGINALLY occupied cell, the original goal and reserved (pending) destinations."""
    inp = row0["inputs"]
    return set(int(c) for c in inp["cells0"]) | {int(inp["goal_cell"])} | set(int(c) for c in reserved)


def rebase(row0, prefix, task=None, reserved=()):
    """row0 = the ORIGINAL public row; prefix = ordered [[obj, cell], ...] applied hypothetically; task = None (original target and goal)
    or (A, d) = temporary target object A with goal cell d.  -> a new row (deep copy)."""
    inp = copy.deepcopy(row0["inputs"])
    R, C = inp["grid"]
    for o, d in prefix:
        o, d = int(o), int(d)
        inp["cells0"][o] = d
        inp["xy0"][o] = list(inp["cell_xy"][str(d)])
    if task is not None:
        A, d = int(task[0]), int(task[1])
        g, t = ctx_slots(inp)
        inp["tid"], inp["goal_cell"], inp["goal"] = A, d, list(inp["cell_xy"][str(d)])
        for i, a in enumerate(inp["attrs"]):
            a[4] = float(i == A)
        inp["ctx"][g] = inp["goal"]
        a = inp["attrs"][A]
        inp["ctx"][t] = [a[2], a[3], a[0]]                         # size, height, is_box (contracts.view3d order); height never edited
    bad = forbidden(row0, reserved)
    inp["legal_cells"] = [c for c in range(R * C) if c not in bad]
    rid = f"{row0['root_id']}|{json.dumps(prefix)}|{json.dumps(task)}|{json.dumps(sorted(reserved))}"
    return {"root_id": rid, "domain": "3d", "inputs": inp, "base_root": row0["root_id"]}


def eligible(row0, used=(), pending=(), task_obj=None):
    """Objects that may move now: never the ORIGINAL target, never an already-moved or pending object, never the current task target."""
    tid = int(row0["inputs"]["tid"])
    bad = {tid} | {int(o) for o in used} | {int(o) for o in pending} | ({int(task_obj)} if task_obj is not None else set())
    return [i for i in range(len(row0["inputs"]["ids"])) if i not in bad]


def legal_seq(row0, seq, max_len=MAX_LEN):
    """Global grammar on the ORIGINAL root: 1..max_len moves, distinct non-target objects, distinct destinations, each initially empty,
    in the grid and not the original goal (no swaps, no vacated-cell reuse, no double move)."""
    inp = row0["inputs"]
    R, C = inp["grid"]
    objs, ds = [int(o) for o, _ in seq], [int(d) for _, d in seq]
    bad = forbidden(row0)
    return (1 <= len(seq) <= max_len and len(set(objs)) == len(objs) and len(set(ds)) == len(ds) and int(inp["tid"]) not in objs
            and all(0 <= o < len(inp["ids"]) for o in objs) and all(0 <= d < R * C and d not in bad for d in ds))


def splits(m):
    """Declared two-group partitions (plan 2): m = 4 -> 1+3, 2+2, 3+1; m = 5 -> 2+3, 3+2; m <= 3 -> the single group."""
    if m <= 3:
        return [(m,)]
    return [(a, m - a) for a in range(1, m) if a <= 3 and m - a <= 3]


def groups(seq, part):
    out, i = [], 0
    for n in part:
        out.append(seq[i:i + n]); i += n
    return out


def displacement(row0, seq):
    import math
    xy = row0["inputs"]["cell_xy"]; c0 = row0["inputs"]["cells0"]
    return sum(math.dist(xy[str(c0[int(o)])], xy[str(int(d))]) for o, d in seq) / 0.075
