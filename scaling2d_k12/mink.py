#!/usr/bin/env python3
"""MINK_STATIC_V1 -- universal 2D grasp-screen kill tables and the exact screen-relaxation lower bound on the minimum number of relocations.

The frozen teacher (skill.plan_skill via p16_motion edges / bd_2d.t_goal) returns VERIFIED for a relocation of object o to cell d, or for the
target task, only if >= 1 of the 48 declared pick candidates (24 tool angles x 2 elbow branches) passes skill.screen_pick in the current scene
AND >= 1 place candidate passes skill.screen_place at d.  Both screens use object poses only (never the start configuration).  Screens are
monotone in the set of discs present (a candidate killed by disc p in {o, p} is killed in every superset), and every disc has r = 0.024, so
    OK_pick(o at x | present P)  subset of  PICK0[x] & ~OR_{p in P} PICKKILL[x][p]        (and likewise PLACE at d)
is a sound OVER-approximation of the passing candidates.  This module computes PICK0 / PICKKILL / PLACE0 / PLACEKILL for every cell pair with
the unchanged screens (single / two-disc scenes), per geometry implementation, plus the q_ref clearance of a single disc at each cell.
    python mink.py table GEOM WORKERS OUT.json      GEOM in {original, fastgeom1}
    python mink.py selftest GEOM TABLE.json N       full-scene screens of N real roots must be a subset of the relaxation (soundness check)"""
import json, os, sys, time
from pathlib import Path

ABF = Path(os.environ.get("ABF_ROOT", str(Path.home() / "abf_v3_laptop/root")))
CODE = ABF / "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code"
TEMPLATE = CODE.parents[0] / "raw/roots"
_M = {}


def boot(geom):
    if _M.get("geom") == geom:
        return _M
    for p in reversed([str(CODE / "dataset-bd"), str(CODE), str(CODE / "latent-causal-tamp"), str(ABF / "teacher2d_wt")]):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(CODE / "latent-causal-tamp")
    import warnings
    warnings.filterwarnings("ignore")
    import importlib.util
    spec = importlib.util.spec_from_file_location("data", str(CODE / "latent-causal-tamp/data.py"))
    m = importlib.util.module_from_spec(spec); sys.modules["data"] = m; spec.loader.exec_module(m)
    import fastgeom, motion as mo, scene as sc, skill as sk, bxy_teacher as T, geometry as ge
    fastgeom.install() if geom == "fastgeom1" else fastgeom.uninstall()
    E = T.env()
    tmpl = json.loads(sorted(TEMPLATE.glob("*.json"))[0].read_text())["scene"]
    _M.update(geom=geom, mo=mo, sc=sc, sk=sk, E=E, tmpl=tmpl, ge=ge)
    return _M


def scene(objs):
    """objs: [(id, kind, cell)] -> Scene on the frozen lattice / robot profile (template root's scene dict, objects replaced)."""
    M = _M
    lat = M["sc"].Lattice(**M["tmpl"]["lattice"])
    d = dict(M["tmpl"], objects=[{"id": i, "kind": k, "radius_m": 0.024, "support": "table", "xy_m": list(lat.center(c)), "cell": c} for i, k, c in objs])
    return M["sc"].scene_from_dict(d)


def mask(cands):
    return sum(1 << i for i, c in enumerate(cands) if c.stage == "OK")


def pick_mask(S, oid):
    M = _M; E = M["E"]; p = E["p"]
    o = S.get(oid)
    ck = M["mo"].checkers(E["robot"], S, oid, None, None, p["delta"], p["eps"])
    return mask(M["sk"].screen_pick(E["robot"], ck, o.xy_m, o.radius_m, p))


def place_mask(S, oid, dest):
    M = _M; E = M["E"]; p = E["p"]; rb = E["robot"]
    xy = S.lattice.center(dest)
    local, gap = (rb.grasp_x, 0.0), 2 * 0.024
    ck = M["mo"].checkers(rb, S, oid, xy, local, p["delta"], p["eps"])
    return mask(M["sk"].screen_place(rb, ck, xy, local, gap, p))


def row(args):
    """Every table entry with object / destination cell x: (PICK0[x], {p: PICKKILL}, PLACE0[x], {p: PLACEKILL})."""
    geom, x, cells = args
    boot(geom)
    t0 = time.process_time()
    p0 = pick_mask(scene([("o00", "obstacle", x)]), "o00")
    pl0 = place_mask(scene([("o00", "obstacle", x)]), "o00", x)
    pk, plk = {}, {}
    for q in cells:
        if q == x:
            continue
        S = scene([("o00", "obstacle", x), ("o01", "obstacle", q)])
        k1 = p0 & ~pick_mask(S, "o00")
        k2 = pl0 & ~place_mask(S, "o00", x)
        if k1:
            pk[q] = k1
        if k2:
            plk[q] = k2
    return x, p0, pk, pl0, plk, round(time.process_time() - t0, 2)


def table(geom, workers, out):
    import multiprocessing as mp
    boot(geom)
    cells = list(range(_M["sc"].Lattice(**_M["tmpl"]["lattice"]).n_cells))
    T = {"version": "MINK_STATIC_V1", "geom": geom, "n_cells": len(cells), "n_candidates": 48, "pick0": {}, "pickkill": {}, "place0": {}, "placekill": {}, "cpu_s": {}}
    with mp.get_context("spawn").Pool(workers) as pool:
        for x, p0, pk, pl0, plk, cpu in pool.imap_unordered(row, [(geom, x, cells) for x in cells]):
            T["pick0"][x], T["pickkill"][x], T["place0"][x], T["placekill"][x], T["cpu_s"][x] = p0, pk, pl0, plk, cpu
            print(f"{time.strftime('%H:%M:%S')} cell {x} pick0={bin(p0).count('1')} place0={bin(pl0).count('1')} cpu={cpu}", flush=True)
    Path(out).write_text(json.dumps(T, sort_keys=True))


def qclear(geom, q):
    """cells where a single disc leaves the robot at configuration q clear (sound destination exclusion for the terminal q_ref connector)."""
    boot(geom)
    E, M = _M["E"], _M
    import numpy as np
    out = []
    for c in range(64):
        S = scene([("o00", "obstacle", c)])
        ck = M["mo"].checkers(E["robot"], S, "o00", None, None, E["p"]["delta"], E["p"]["eps"])
        if ck[("start", False)].status_at(np.asarray(q, float), E["robot"].open_gap).status == M["ge"].CLEAR:
            out.append(c)
    return out


def view(row):
    inp = row["inputs"]
    return {"root_id": row["root_id"], "ids": inp["ids"], "cells0": inp["cells0"], "tid": inp["tid"], "goal_cell": inp["goal_cell"],
            "legal_cells": inp["legal_cells"], "fixed": [bool(a[3]) for a in inp["attrs"]], "q_ref": inp["q_ref"]}


def soundness(snap, tables, rawmap, out, n_decomp=40):
    """(1) decomposition: real-scene screens subset of the relaxation (pick of every object; place at 3 admissible cells) on n_decomp TRAIN roots;
    (2) data: for every TRAIN K0-K3 root, K_lb <= length of every finalized X = 1 & Y = 1 sequence, K0 -> K_lb = 0."""
    import collections, hashlib, cert as C
    T = {g: json.loads(Path(tables[g]).read_text()) for g in tables}
    raw = json.loads(Path(rawmap).read_text())
    rows = [json.loads(l) for l in open(snap) if '"split": "train"' in l]
    res = {"decomp": collections.Counter(), "data": collections.Counter(), "violations": []}
    qc = {}
    for g in ("original", "fastgeom1"):
        boot(g)
        sub = sorted([r for r in rows if raw[r["root_id"]]["geom"] == g], key=lambda r: hashlib.sha256(r["root_id"].encode()).hexdigest())
        for r in sub[:n_decomp // 2]:
            S = M_scene_from_raw(raw[r["root_id"]]["path"])
            v = view(r)
            for i, oid in enumerate(v["ids"]):
                full = pick_mask(S, oid)
                x = str(v["cells0"][i]); rel = T[g]["pick0"][x]
                for j, c in enumerate(v["cells0"]):
                    if j != i:
                        rel &= ~T[g]["pickkill"][x].get(str(c), 0)
                res["decomp"]["pick_ok" if full & ~rel == 0 else "pick_VIOLATION"] += 1
                if full & ~rel:
                    res["violations"].append(["pick", r["root_id"], oid])
            for i, oid in enumerate(v["ids"][:3]):
                for d in [c for c in v["legal_cells"] if c not in v["cells0"]][:3]:
                    full = place_mask(S, oid, d)
                    rel = T[g]["place0"][str(d)]
                    for j, c in enumerate(v["cells0"]):
                        if j != i:
                            rel &= ~T[g]["placekill"][str(d)].get(str(c), 0)
                    res["decomp"]["place_ok" if full & ~rel == 0 else "place_VIOLATION"] += 1
                    if full & ~rel:
                        res["violations"].append(["place", r["root_id"], oid, d])
        for r in [r for r in rows if raw[r["root_id"]]["geom"] == g and r["K_legacy"] in ("0", "1", "2", "3")]:
            v = view(r)
            qk = json.dumps(v["q_ref"])
            if (g, qk) not in qc:
                qc[(g, qk)] = set(qclear(g, v["q_ref"]))
            cb = C.bound(T[g], v, qc[(g, qk)])
            Y = {json.dumps(sorted(map(list, y["edit"]))): y["y"] for y in r["labels"]["Y"]}
            ok_len = [len(x["seq"]) for x in r["labels"]["X"] if x["x"] == 1 and Y.get(json.dumps(sorted(map(list, x["seq"])))) == 1]
            if r["K_legacy"] == "0" and Y.get("[]") == 1:
                ok_len.append(0)
            kl = cb["K_lb"]
            if not ok_len:
                res["data"]["no_known_success"] += 1; continue
            bad = kl is None or isinstance(kl, str) or kl > min(ok_len)
            res["data"][("VIOLATION" if bad else "ok") + f"|K{r['K_legacy']}|lb={kl}|min_known={min(ok_len)}"] += 1
            if bad:
                res["violations"].append(["data", r["root_id"], kl, min(ok_len)])
    res = {"decomp": dict(res["decomp"]), "data": dict(sorted(res["data"].items())), "violations": res["violations"][:50], "n_violations": len(res["violations"])}
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps({"decomp": res["decomp"], "n_violations": res["n_violations"]}))


def M_scene_from_raw(path):
    return _M["sc"].scene_from_dict(json.loads(Path(path).read_text())["scene"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "table":
        table(a[1], int(a[2]), os.path.abspath(a[3]))
    elif a[0] == "soundness":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        soundness(a[1], {"original": a[2], "fastgeom1": a[3]}, a[4], os.path.abspath(a[5]))
    elif a[0] == "probe":                                   # timing probe: one row
        print(row((a[1], int(a[2]), list(range(64))))[0::5])
    else:
        raise SystemExit(__doc__)
