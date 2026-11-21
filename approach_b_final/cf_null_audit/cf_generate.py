#!/usr/bin/env python3
"""BASE / CF / NULL intervention proposals (label-blind, model-blind).  One edit = MOVE ONE existing non-target obstacle to a free legal cell
(object count, identities, target, goal, robot reference unchanged).  Proposal family PROP_V1 (registered before any label is read):
  CF candidates   free cells in the 8-neighbourhood of the target cell or the goal cell, or in the "front corridor" between the robot side and
                  the target / goal (3D: rows nearer the robot, |dc| <= 1; 2D: columns nearer the base at the left, |dr| <= 1)
  NULL candidates free cells at Chebyshev distance >= 2 from target and goal and outside both front corridors; ordered by |displacement -
                  displacement of the object's first CF proposal| (matched magnitude), then sha256
  objects         non-target movable obstacles in sha256('CFNULL|root|obj') order; cells in sha256('CFNULL|root|obj|cell') order
  per base        up to N_OBJ objects x (N_CF CF + N_NULL NULL) proposals, all physically labelled; nothing depends on any model output.
    python cf_generate.py DOM BASES.jsonl OUT_JOBS.jsonl     (BASES rows: {root_id, path, cells, goal, geom?, base_kind})"""
import hashlib, json, sys

N_OBJ, N_CF, N_NULL = 2, 4, 4
N_OBJ_V2 = int(__import__("os").environ.get("CF_NOBJ_V2", 4))   # final 2D (amendment 3); the engineering pilot used 2


def h(*a):
    return hashlib.sha256("|".join(map(str, ("CFNULL",) + a)).encode()).hexdigest()


def cells_3d():
    return [(r, c) for r in range(6) for c in range(6)]


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def front(dom, x, y):
    """y in the front corridor of x (between the robot side and x)."""
    if dom == "3d":
        return y[0] < x[0] and abs(y[1] - x[1]) <= 1
    return y[1] < x[1] and abs(y[0] - x[0]) <= 1


def proposals(dom, base):
    if dom == "3d":
        cell = lambda v: tuple(v)  # noqa: E731
        allc = cells_3d()
    else:
        cell = lambda v: (int(v) // 8, int(v) % 8)  # noqa: E731
        allc = [(r, c) for r in range(8) for c in range(8) if r * 8 + c in set(base["legal"])]
    occ = {o: cell(v) for o, v in base["cells"].items()}
    t, g = occ["t0"], cell(base["goal"])
    free = [c for c in allc if c not in occ.values() and c != g]
    cf_set = [c for c in free if cheb(c, t) == 1 or cheb(c, g) == 1 or front(dom, t, c) or front(dom, g, c)]
    null_set = [c for c in free if cheb(c, t) >= 2 and cheb(c, g) >= 2 and not front(dom, t, c) and not front(dom, g, c)]
    rid = base["root_id"]
    objs = sorted((o for o in occ if o != "t0" and o not in base.get("fixed", [])), key=lambda o: h(rid, o))[:N_OBJ]
    out = []
    for o in objs:
        cf = sorted(cf_set, key=lambda c: h(rid, o, c))[:N_CF]
        if not cf:
            continue
        d0 = cheb(occ[o], cf[0])
        nl = sorted(null_set, key=lambda c: (abs(cheb(occ[o], c) - d0), h(rid, o, c)))[:N_NULL]
        for kind, lst in (("CF", cf), ("NULL", nl)):
            for k, c in enumerate(lst):
                new = dict(base["cells"])
                new[o] = list(c) if dom == "3d" else c[0] * 8 + c[1]
                out.append({"qid": f"{rid}|{kind}|{o}|{c[0]}_{c[1]}", "root_id": rid, "kind": kind, "obj": o, "rank": k, "from": list(occ[o]),
                            "to": list(c), "disp": cheb(occ[o], c), "cells": new})
    return out


def proposals_v2_2d(base, T, qc):
    """PROP_V2_2D (registered after the 2D engineering pilot, before any final 2D label): frozen grasp-screen kill tables (scaling G1
    MINK_TABLE_original, derived from the unchanged teacher screens; no label, no model).  For object o moved to free q_ref-clear legal cell d:
    live target pick = pick0[t] & ~OR(pickkill[t][p] for other discs p != o); live goal place likewise; kill(d) = live candidates killed by d.
    CF order: (kills ALL live target-pick or ALL live goal-place candidates) desc, #killed desc, sha256.  NULL: cells with kill(d) = 0,
    Chebyshev >= 2 from target and goal, displacement-matched to the object's first CF cell, then sha256."""
    import functools
    occ = {o: int(v) for o, v in base["cells"].items()}
    t, g = occ["t0"], int(base["goal"])
    pk, pl, p0, pl0 = T["pickkill"], T["placekill"], T["pick0"], T["place0"]
    kill = lambda tab, x, cells: functools.reduce(lambda a, q: a | int(tab[str(x)].get(str(q), 0)), cells, 0)  # noqa: E731
    pc = lambda v: bin(v).count("1")  # noqa: E731
    rc = lambda c: (c // 8, c % 8)  # noqa: E731
    legal = [c for c in base["legal"] if c in qc]
    free = [c for c in legal if c not in occ.values() and c != g]
    rid = base["root_id"]
    objs = sorted((o for o in occ if o != "t0" and o not in base.get("fixed", [])), key=lambda o: h(rid, o))[:N_OBJ_V2]
    out = []
    for o in objs:
        others = [c for k, c in occ.items() if k not in (o, "t0")]
        lt = int(p0[str(t)]) & ~kill(pk, t, others)
        lg = int(pl0[str(g)]) & ~kill(pl, g, others + [t])
        sc = {}
        for d in free:
            kt, kg = lt & int(pk[str(t)].get(str(d), 0)), lg & int(pl[str(g)].get(str(d), 0))
            full = (lt and kt == lt) or (lg and kg == lg)
            sc[d] = (int(bool(full)), pc(kt) + pc(kg))
        cf = sorted((d for d in free if sc[d][1] > 0), key=lambda d: (-sc[d][0], -sc[d][1], h(rid, o, d)))[:N_CF]
        if not cf:
            continue
        d0 = cheb(rc(occ[o]), rc(cf[0]))
        nl = sorted((d for d in free if sc[d][1] == 0 and cheb(rc(d), rc(t)) >= 2 and cheb(rc(d), rc(g)) >= 2),
                    key=lambda d: (abs(cheb(rc(occ[o]), rc(d)) - d0), h(rid, o, d)))[:N_NULL]
        for kind, lst in (("CF", cf), ("NULL", nl)):
            for k, d in enumerate(lst):
                new = dict(base["cells"]); new[o] = d
                out.append({"qid": f"{rid}|{kind}|{o}|v2_{d}", "root_id": rid, "kind": kind, "obj": o, "rank": k, "from": list(rc(occ[o])), "to": list(rc(d)),
                            "disp": cheb(rc(occ[o]), rc(d)), "cells": new, "family": "PROP_V2_2D", "screen_kill": sc[d]})
    return out


def main(dom, bases_f, out_f):
    rows = [json.loads(l) for l in open(bases_f)]
    if dom == "2d_v2":
        import os
        tdir = os.environ["CF_TABLES"]
        T = json.load(open(f"{tdir}/MINK_TABLE_original.json")); qc = set(json.load(open(f"{tdir}/QCLEAR_original.json"))["cells"])
    with open(out_f, "w") as f:
        for b in rows:
            base_job = {"qid": f"{b['root_id']}|BASE", "root_id": b["root_id"], "kind": "BASE", "obj": None, "cells": b["cells"]}
            props = proposals_v2_2d(b, T, qc) if dom == "2d_v2" else proposals(dom, b)
            for j in [base_job] + props:
                j.update(path=b["path"], seed=0, base_kind=b.get("base_kind"), **({"geom": b["geom"]} if b.get("geom") else {}))
                f.write(json.dumps(j) + "\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
