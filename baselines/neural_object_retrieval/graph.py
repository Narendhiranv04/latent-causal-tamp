"""SORC-Grid scene graphs from PUBLIC inputs only (contracts.view2d / view3d): accessibility graph of the current hypothetical scene, task-goal
graph, per-cell features for placement, and the shared static legality (identical to benchmark.legality / search.Root.legal_dests).

Accessibility graph (SORC Alg. 1 analogue): vertices = robot (base), objects, goal (target at its goal cell); edge (i, j) carries relative pose
and clear(i, j) = 1 iff no third object's centre lies within its radius + margin of the straight segment i -> j (public geometric proxy of a
collision-free straight end-effector path; no planner, no teacher).  Task-goal graph = robot + target-at-goal + fixed structure only (the
benchmark specifies no goal arrangement for the other objects).  goal=False zeroes every goal-derived feature (task-goal ablation)."""
import math
import numpy as np

NMAX = {"2d": 20, "3d": 13}                 # observed max objects (P0 audit)
NCELL = {"2d": 64, "3d": 36}
F_NODE, F_EDGE, F_CELL = 24, 4, 14
MARGIN = 0.01


def movable(inp, dom):
    fixed = [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])
    return [i for i in range(len(inp["ids"])) if i != inp["tid"] and not fixed[i]]


def legal_dests(inp, cells):
    occ0, occ = set(map(int, inp["cells0"])), set(map(int, cells))
    g = int(inp["goal_cell"])
    return [int(d) for d in inp["legal_cells"] if int(d) not in occ and int(d) not in occ0 and int(d) != g]


def apply(inp, prefix):
    cells = [int(c) for c in inp["cells0"]]
    for o, d in prefix:
        cells[int(o)] = int(d)
    return cells


def is_legal(inp, dom, prefix):
    """Same verdict as benchmark.legality for a non-empty prefix (None = legal)."""
    if not 1 <= len(prefix) <= 3:
        return "LENGTH"
    mov, cells, seen = set(movable(inp, dom)), apply(inp, []), set()
    for o, d in prefix:
        if not 0 <= o < len(inp["ids"]):
            return "UNKNOWN_OBJECT"
        if o not in mov:
            return "IMMOVABLE_OBJECT"
        if o in seen:
            return "OBJECT_MOVED_TWICE"
        if d not in legal_dests(inp, cells):
            return "ILLEGAL_DESTINATION"
        seen.add(o)
        cells[o] = d
    return None


def _frame(inp):
    P = np.array(list(inp["cell_xy"].values()), float)
    c, s = P.mean(0), max(np.ptp(P[:, 0]), np.ptp(P[:, 1])) / 2 + 1e-9
    return c, s


def _seg(p, a, b):
    ab = b - a
    t = float(np.clip(np.dot(p - a, ab) / (np.dot(ab, ab) + 1e-12), 0, 1))
    return float(np.linalg.norm(p - (a + t * ab))), t


def _radius(inp, dom, i):
    a = inp["attrs"][i]
    return float(a[0]) if dom == "2d" else float(max(a[2], 0.02))


def scene(inp, dom, prefix=(), goal=True):
    """-> dict of numpy arrays: node feats [N+2, F_NODE], node mask, edge feats [N+2, N+2, F_EDGE], cell feats [NCELL, F_CELL], legal mask,
    eligible-object mask, with node order = objects (padded to NMAX) then robot, goal."""
    c, s = _frame(inp)
    n, N = len(inp["ids"]), NMAX[dom]
    cells = apply(inp, prefix)
    moved = {int(o) for o, _ in prefix}
    pos = np.array([inp["cell_xy"][str(cells[i])] if i in moved else inp["xy0"][i] for i in range(n)], float)
    tid = inp["tid"]
    base, gxy = np.array(inp["base"], float), np.array(inp["goal"], float)
    tpos = pos[tid]
    mov = set(movable(inp, dom))
    X = np.zeros((N + 2, F_NODE), np.float32)
    for i in range(n):
        a = list(inp["attrs"][i]) + [0.0] * 5
        dtg, along = _seg(pos[i], tpos, gxy)
        f = [*(pos[i] - c) / s, float(i == tid), float(i in mov), float(i not in mov and i != tid), float(i in moved), *a[:5],
             np.linalg.norm(pos[i] - tpos) / s, np.linalg.norm(pos[i] - base) / s, _seg(pos[i], base, tpos)[0] / s,
             np.linalg.norm(pos[i] - gxy) / s if goal else 0.0, dtg / s if goal else 0.0, along if goal else 0.0,
             _seg(pos[i], base, gxy)[0] / s if goal else 0.0, 1.0, 0.0, 0.0]
        X[i, :len(f)] = f
    ctx = list(inp["ctx"])[:6] + [0.0] * 6
    X[N, :2] = (base - c) / s
    X[N, 2:8] = ctx[:6]
    X[N, 22] = 1.0
    if goal:
        X[N + 1, :2] = (gxy - c) / s
        X[N + 1, 6:11] = (list(inp["attrs"][tid]) + [0.0] * 5)[:5]
    X[N + 1, 23] = 1.0
    nm = np.zeros(N + 2, bool)
    nm[:n] = True
    nm[N] = True
    nm[N + 1] = goal
    P = np.zeros((N + 2, 2))
    P[:n], P[N], P[N + 1] = pos, base, gxy
    rad = np.array([_radius(inp, dom, i) for i in range(n)])
    E = np.zeros((N + 2, N + 2, F_EDGE), np.float32)
    idx = np.array([i for i in range(N + 2) if nm[i]])
    A, B = P[idx][:, None, None, :], P[idx][None, :, None, :]                     # segment i -> j, every object k
    K = pos[None, None, :, :]
    ab = B - A
    t = np.clip(((K - A) * ab).sum(-1) / ((ab * ab).sum(-1) + 1e-12), 0, 1)
    dist = np.linalg.norm(K - (A + t[..., None] * ab), axis=-1)                   # [I, J, n]
    blk = dist < (rad + MARGIN)[None, None, :]
    for a_, i in enumerate(idx):                                                 # an endpoint never blocks its own segment
        if i < n:
            blk[a_, :, i] = False
            blk[:, a_, i] = False
    clear = ~blk.any(-1)
    D = P[idx][None, :, :] - P[idx][:, None, :]
    sub = np.concatenate([D / s, np.linalg.norm(D, axis=-1, keepdims=True) / s, clear[..., None]], -1)
    for a_ in range(len(idx)):
        sub[a_, a_] = 0.0
    E[np.ix_(idx, idx)] = sub
    nc = NCELL[dom]
    C = np.zeros((nc, F_CELL), np.float32)
    leg = np.zeros(nc, bool)
    ld = set(legal_dests(inp, cells))
    occ, occ0, lc = set(cells), set(map(int, inp["cells0"])), set(map(int, inp["legal_cells"]))
    for q in range(nc):
        if str(q) not in inp["cell_xy"]:
            continue
        p = np.array(inp["cell_xy"][str(q)], float)
        dtg, along = _seg(p, tpos, gxy)
        C[q] = [*(p - c) / s, float(q in occ), float(q in occ0), float(q in lc), float(q in ld),
                np.linalg.norm(p - tpos) / s, np.linalg.norm(p - base) / s, _seg(p, base, tpos)[0] / s,
                float(q == int(inp["goal_cell"])) if goal else 0.0, np.linalg.norm(p - gxy) / s if goal else 0.0,
                dtg / s if goal else 0.0, along if goal else 0.0, _seg(p, base, gxy)[0] / s if goal else 0.0]
        leg[q] = q in ld
    elig = np.zeros(N + 2, bool)
    for i in mov - moved:
        elig[i] = True
    return {"X": X, "M": nm, "E": E, "C": C, "L": leg, "elig": elig, "n": n}


def goal_graph(inp, dom, goal=True):
    """Task-goal graph: robot + target placed at its goal cell + fixed structure (other movable objects absent)."""
    full = scene(inp, dom, (), goal)
    n, N = full["n"], NMAX[dom]
    keep = np.zeros(N + 2, bool)
    keep[N] = True
    keep[N + 1] = goal
    mov = set(movable(inp, dom))
    for i in range(n):
        if i not in mov and i != inp["tid"]:
            keep[i] = True                                         # fixed structure (2D immovable objects)
    return {**full, "M": keep}
