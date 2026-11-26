"""Domain-specific public views (2D / 3D) for faithful Fig. 3 recursive retargeting.  Public inputs only; no labels, K, witnesses or teacher.

2D (contracts.view2d): attrs [radius, is_target, is_obstacle, is_fixed]; ctx = sin q (x3) | cos q (x3) | goal xy | gripper gap; q_ref = per-root q0.
   Retarget to temporary task (A -> d): A takes the target role (is_target 1, is_obstacle 0), the ORIGINAL target takes the ordinary
   non-target role of every other movable body in training (is_target 0, is_obstacle 1); radius and is_fixed never change; goal / goal_cell /
   ctx goal slots (6:8) rewritten.  Geometry is untouched (the role swap mirrors the training encoding of target vs obstacle bodies).
3D (contracts.view3d): attrs [is_box, is_cylinder, size, height, is_target]; ctx = sin q (x7) | cos q (x7) | goal xy | target size, height, is_box.
Both domains: rebased `legal_cells` = ORIGINAL declared legal cells minus original occupancy, original goal and reserved destinations
(R0 issue 9: never the full grid).  Action keys are immutable (object id string, destination cell)."""
from __future__ import annotations

import copy, hashlib, json, math

DOM_OF = lambda row: row["domain"]  # noqa: E731


def key(row0, a):
    """Immutable action key: (object id, destination cell)."""
    return (row0["inputs"]["ids"][int(a[0])], int(a[1]))


def skey(row):
    return hashlib.sha256(json.dumps(row["inputs"], sort_keys=True).encode()).hexdigest()[:20]


def forbidden(row0, reserved=()):
    inp = row0["inputs"]
    return set(int(c) for c in inp["cells0"]) | {int(inp["goal_cell"])} | {int(c) for c in reserved}


def _ctx_goal(dom, inp):
    if dom == "2d":
        assert len(inp["ctx"]) == 2 * len(inp["q_ref"]) + 3, "unexpected 2D ctx layout"
        n = 2 * len(inp["q_ref"])
        return slice(n, n + 2), None
    n = 2 * len(inp["q_ref"])
    assert len(inp["ctx"]) == n + 5, "unexpected 3D ctx layout"
    return slice(n, n + 2), slice(n + 2, n + 5)


def rebase(row0, prefix, task=None, reserved=()):
    """Hypothetical scene after ordered prefix [[obj, cell], ...]; task None = original target / goal, else (A, d) temporary target.
    Deep copy; every object kept; only cells0 / xy0 of moved objects change (+ role / goal fields for a temporary task)."""
    dom = row0["domain"]
    inp = copy.deepcopy(row0["inputs"])
    for o, d in prefix:
        inp["cells0"][int(o)] = int(d)
        inp["xy0"][int(o)] = list(inp["cell_xy"][str(int(d))])
    if task is not None:
        A, d = int(task[0]), int(task[1])
        T0 = int(row0["inputs"]["tid"])
        g, t = _ctx_goal(dom, inp)
        inp["tid"], inp["goal_cell"], inp["goal"] = A, d, list(inp["cell_xy"][str(d)])
        inp["ctx"][g] = inp["goal"]
        if dom == "2d":
            for i, a in enumerate(inp["attrs"]):
                if i == A:
                    a[1], a[2] = 1.0, 0.0
                elif i == T0 or a[1] == 1.0:
                    a[1], a[2] = 0.0, 1.0
        else:
            for i, a in enumerate(inp["attrs"]):
                a[4] = float(i == A)
            a = inp["attrs"][A]
            inp["ctx"][t] = [a[2], a[3], a[0]]
    bad = forbidden(row0, reserved)
    inp["legal_cells"] = [c for c in row0["inputs"]["legal_cells"] if int(c) not in bad]
    rid = f"{row0['root_id']}|{json.dumps(prefix)}|{json.dumps(task)}|{json.dumps(sorted(int(c) for c in reserved))}"
    return {"root_id": rid, "domain": dom, "inputs": inp, "base_root": row0["root_id"]}


def fixed(row0):
    inp = row0["inputs"]
    return {i for i, a in enumerate(inp["attrs"]) if row0["domain"] == "2d" and a[3] > 0.5}


def eligible(row0, used=(), pending=(), protect=()):
    """Movers now: never the ORIGINAL target, a fixed body, an already-moved / pending object or a protected (active ancestor / current
    temporary target) object."""
    tid = int(row0["inputs"]["tid"])
    bad = {tid} | fixed(row0) | {int(o) for o in used} | {int(o) for o in pending} | {int(o) for o in protect}
    return [i for i in range(len(row0["inputs"]["ids"])) if i not in bad]


def legal_seq(row0, seq, max_len):
    """Global grammar on the ORIGINAL root: distinct movable non-target non-fixed objects, distinct initially-empty legal non-goal cells."""
    inp = row0["inputs"]
    objs, ds = [int(o) for o, _ in seq], [int(d) for _, d in seq]
    legal = set(int(c) for c in inp["legal_cells"]) - forbidden(row0)
    return (len(seq) <= max_len and len(set(objs)) == len(objs) and len(set(ds)) == len(ds) and int(inp["tid"]) not in objs
            and not set(objs) & fixed(row0) and all(0 <= o < len(inp["ids"]) for o in objs) and all(d in legal for d in ds))


def partitions(m, max_group=3):
    """All compositions of m into ordered group sizes 1..max_group (m = 5: 13 partitions)."""
    if m == 0:
        return [()]
    out = []
    for g in range(1, min(max_group, m) + 1):
        out += [(g,) + p for p in partitions(m - g, max_group)]
    return out


def groups(seq, part):
    out, i = [], 0
    for n in part:
        out.append(seq[i:i + n]); i += n
    return out


def displacement(row0, seq):
    xy = row0["inputs"]["cell_xy"]; c0 = row0["inputs"]["cells0"]
    pitch = 0.08 if row0["domain"] == "2d" else 0.075
    return sum(math.dist(xy[str(c0[int(o)])], xy[str(int(d))]) for o, d in seq) / pitch
