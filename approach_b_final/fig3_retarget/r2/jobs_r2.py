#!/usr/bin/env python3
"""R2 physical job builders (evaluator side; deterministic, label-blind to the NEW outcomes; manifests sealed with sha256 before dispatch).
    python jobs_r2.py matchedN DOM OUT_DIR     R2.1-A: families, perturbed raw records, jobs (+ rows for model readouts)
    python jobs_r2.py omission DOM OUT_DIR     R2.1-C: C3b omission Y_tau queries not already labelled
    python jobs_r2.py connectors DOM OUT_DIR   R2.2: split partitions of verified continuous sequences (continuous labels reused)"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import common as C  # noqa: E402
import perturb as PT  # noqa: E402

LEVELS = {"2d": [4, 8], "3d": [3, 6]}
NFAM = {"2d": 10, "3d": 8}
BASE_N = {"2d": (6, 12), "3d": (3, 6)}
NOISE_FAMS = 3


def names(dom, ids, seq):
    return [[ids[int(o)], int(d) if dom == "2d" else [int(d) // 6, int(d) % 6]] for o, d in seq]


def raw_index(dom):
    out = {}
    for sp in ("val",):
        for l in open(C.PRIV / f"private_{sp}_{dom}.jsonl"):
            e = json.loads(l)
            out[e["root_id"]] = (e["path"], e.get("geom", "original"))
    return out


def seal(out, name, obj):
    p = Path(out) / name
    p.write_text(json.dumps(obj, indent=1))
    (Path(out) / (name + ".SEAL")).write_text(hashlib.sha256(p.read_bytes()).hexdigest())
    return p


def matchedN(dom, out):
    out = Path(out); (out / "roots").mkdir(parents=True, exist_ok=True)
    rows = C.snapshot_rows(dom, ("val",))
    RI = raw_index(dom)
    P = [e for e in C.pool(dom) if e["split"] == "val"]
    X = collections.defaultdict(list); Y = collections.defaultdict(dict)
    for e in P:
        if e["t"] == "X":
            X[e["root"]].append(e)
        else:
            Y[e["root"]][json.dumps(sorted([list(map(int, a)) for a in e["edit"]]))] = e["y"]
    fams, used = [], set()
    for rid in sorted(rows, key=lambda r: C.h("R2_N|" + r)):
        r = rows[rid]; n = len(r["inputs"]["ids"])
        if not BASE_N[dom][0] <= n <= BASE_N[dom][1] or r["parent_family_id"] in used or rid not in RI:
            continue
        if Y[rid].get("[]") != 0:
            continue
        reps = sorted([e for e in X[rid] if e["x"] == 1 and len(e["seq"]) in (1, 2) and Y[rid].get(json.dumps(sorted([list(map(int, a)) for a in e["seq"]]))) == 1],
                      key=lambda e: (len(e["seq"]), json.dumps(e["seq"])))
        negs = sorted([k for k, v in Y[rid].items() if v == 0 and k != "[]"], key=lambda k: (len(json.loads(k)), k))
        if not reps or not negs:
            continue
        rep = [list(map(int, a)) for a in reps[0]["seq"]]; neg = json.loads(negs[0])
        fams.append({"root_id": rid, "fam": r["parent_family_id"], "N0": n, "rep": rep, "neg": neg, "path": RI[rid][0], "geom": RI[rid][1]})
        used.add(r["parent_family_id"])
        if len(fams) == NFAM[dom]:
            break
    jobs, variants = [], []
    for fi, f in enumerate(fams):
        raw = json.loads(Path(f["path"]).read_text())
        ids = rows[f["root_id"]]["inputs"]["ids"]
        cells = PT.cells_2d(raw) if dom == "2d" else PT.cells_3d(raw)
        protect = [cells["t0"]] + [cells[ids[o]] for o, _ in f["rep"] + f["neg"]] + [d for _, d in f["rep"] + f["neg"]]
        levels = ([0] if fi < NOISE_FAMS else []) + LEVELS[dom]
        for k in levels:
            new, added = PT.add(dom, raw, k, protect)
            v = {"fam": f["fam"], "root_id": f["root_id"], "k": k, "N": f["N0"] + k, "built": new is not None, "why": None if new else added}
            variants.append(v)
            if new is None:
                continue
            p = out / "roots" / f"{C.h(new['ids']['root_id'])[:16]}.json"
            p.write_text(json.dumps(new)); v["path"] = str(p); v["tag"] = new["ids"]["root_id"]
            key = f"N|{f['root_id'][-14:]}|+{k}"
            if dom == "2d":
                g = int(raw["goal_cell"])
                jobs += [{"key": key + "|X", "path": str(p), "geom": f["geom"], "kind": "X_CHUNKED", "seq": names(dom, ids, f["rep"]), "bounds": [len(f["rep"])], "y_endpoint": True},
                         {"key": key + "|Y0", "path": str(p), "geom": f["geom"], "kind": "Y_TEMP", "edit": [], "target": "t0", "goal": g},
                         {"key": key + "|YN", "path": str(p), "geom": f["geom"], "kind": "Y_TEMP", "edit": names(dom, ids, f["neg"]), "target": "t0", "goal": g}]
            else:
                c0 = {kk: list(vv) for kk, vv in new["initial_cells"].items()}
                cn = {**c0, **{o: d for o, d in names(dom, ids, f["neg"])}}
                jobs += [{"key": key + "|X", "path": str(p), "kind": "X_CHUNKED", "order": names(dom, ids, f["rep"]), "bounds": [len(f["rep"])], "y": {"target": "t0", "goal": new["goal"]}},
                         {"key": key + "|Y0", "path": str(p), "kind": "Y_TARGET", "cells": c0, "target": "t0", "goal": new["goal"]},
                         {"key": key + "|YN", "path": str(p), "kind": "Y_TARGET", "cells": cn, "target": "t0", "goal": new["goal"]}]
    seal(out, f"families_{dom}.json", {"families": fams, "variants": variants})
    seal(out, f"jobs_N_{dom}.json", jobs)
    nq = sum(2 if j["kind"] == "X_CHUNKED" else 1 for j in jobs)
    print(json.dumps({"dom": dom, "families": len(fams), "variants_built": sum(v["built"] for v in variants), "variants_unsupported": [v for v in variants if not v["built"]],
                      "jobs": len(jobs), "teacher_queries": nq}))


def omission(dom, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    T = C.NW / "k3val/runs/out/ttarget"
    E = json.loads((T / f"EXAMPLES_{dom}_b.json").read_text()); R = json.loads((T / f"TT_{dom}_b.json").read_text())["rows"]
    rows = C.snapshot_rows(dom, ("val",)); RI = raw_index(dom)
    jobs, have = [], 0
    for e, r in zip(E, R):
        if r["y_tt_S0"] != 0 or r["xy_tt_P"] != [1, 1] or len(e["P"]) < 2:
            continue
        ids = rows[e["root_id"]]["inputs"]["ids"]
        raw = json.loads(Path(RI[e["root_id"]][0]).read_text())
        for i in range(len(e["P"])):
            keep = [p for j, p in enumerate(e["P"]) if j != i]
            if len(keep) == 1 and f"{keep[0][0]}>{keep[0][1]}" in r["single"]:
                have += 1; continue                                               # already labelled exactly (single candidate)
            key = f"OM|{e['root_id'][-14:]}|-{i}"
            if dom == "2d":
                jobs.append({"key": key, "path": RI[e["root_id"]][0], "geom": RI[e["root_id"]][1], "kind": "Y_TT", "edit": names(dom, ids, keep),
                             "target": e["A_id"], "goal": int(e["dA"])})
            else:
                c0 = {kk: list(vv) for kk, vv in raw["initial_cells"].items()}
                jobs.append({"key": key, "path": RI[e["root_id"]][0], "kind": "Y_TT", "cells": {**c0, **{o: d for o, d in names(dom, ids, keep)}},
                             "target": e["A_id"], "goal": [int(e["dA"]) // 6, int(e["dA"]) % 6]})
    seal(out, f"jobs_OM_{dom}.json", jobs)
    print(json.dumps({"dom": dom, "omission_jobs": len(jobs), "already_labelled": have}))


def connectors(dom, out, n2=24, n3=16, nfail=8, nspot=8):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = C.snapshot_rows(dom, ("val",)); RI = raw_index(dom)
    P = [e for e in C.pool(dom) if e["split"] == "val" and e["t"] == "X" and e["root"] in RI]
    Yl = collections.defaultdict(dict)
    for e in C.pool(dom):
        if e["t"] == "Y" and e["split"] == "val":
            Yl[e["root"]][json.dumps(sorted([list(map(int, a)) for a in e["edit"]]))] = e["y"]
    yend = lambda e: Yl[e["root"]].get(json.dumps(sorted([list(map(int, a)) for a in e["seq"]])))  # noqa: E731
    def pick(cands, k):
        """k sequences spread over N bins (round-robin over bins, sha order inside), one per root."""
        by = collections.defaultdict(list)
        for e in sorted(cands, key=lambda e: C.h("R2_CONN|" + e["root"] + json.dumps(e["seq"]))):
            by[C.nbin(dom, e["N"])].append(e)
        sel, roots = [], set()
        while len(sel) < k and any(by.values()):
            for b in sorted(by):
                while by[b] and by[b][0]["root"] in roots:
                    by[b].pop(0)
                if by[b] and len(sel) < k:
                    e = by[b].pop(0); sel.append(e); roots.add(e["root"])
        return sel
    if dom == "2d":
        s2 = pick([e for e in P if len(e["seq"]) == 2 and e["x"] == 1 and yend(e) == 1], n2)
        s3 = pick([e for e in P if len(e["seq"]) == 3 and e["x"] == 1 and yend(e) == 1 and e["root"] not in {x["root"] for x in s2}], n3)
        sf = pick([e for e in P if len(e["seq"]) == 2 and e["x"] == 0 and e["status"] == "UNKNOWN_TRANSIT"], nfail)
    else:
        s2, sf = [], []
        s3 = pick([e for e in P if len(e["seq"]) == 3 and e["x"] == 1 and yend(e) == 1], 4)
    parts = {2: [[1, 2]], 3: [[1, 3], [2, 3], [1, 2, 3]]}
    jobs, panel = [], []
    for grp, sel in (("m2_pos", s2), ("m3_pos", s3), ("m2_conn_fail", sf)):
        for i, e in enumerate(sel):
            ids = rows[e["root"]]["inputs"]["ids"]
            seq = names(dom, ids, e["seq"]); m = len(seq)
            panel.append({"group": grp, "root": e["root"], "fam": rows[e["root"]]["parent_family_id"], "N": e["N"], "seq": e["seq"], "x_cont": e["x"],
                          "status_cont": e["status"], "y_end": yend(e), "src": e["src"]})
            bl = parts[m] + ([[m]] if (grp != "m2_conn_fail" and i < (nspot // 2 if grp == "m2_pos" else nspot // 2 if grp == "m3_pos" else 0)) else [])
            for b in bl:
                key = f"C|{grp}|{e['root'][-14:]}|{json.dumps(e['seq'])}|{b}"
                if dom == "2d":
                    jobs.append({"key": key, "path": RI[e["root"]][0], "geom": RI[e["root"]][1], "kind": "X_CHUNKED", "seq": seq, "bounds": b})
                else:
                    jobs.append({"key": key, "path": RI[e["root"]][0], "kind": "X_CHUNKED", "order": seq, "bounds": b, "y": None})
    if dom == "3d":                                                                # K4/K5 cohort: all-singleton partition of the witness order (new)
        for rp in sorted((C.NW / "k45/cohort/roots").glob("*.json")):
            rec = json.loads(rp.read_text()); w = rec["k45"]["witness"]["order"]; m = len(w)
            panel.append({"group": f"k{m}_witness", "root": rec["ids"]["root_id"], "fam": rec["ids"].get("parent_family_id"), "N": len(rec["objects"]),
                          "seq": w, "x_cont": 1, "status_cont": "WITNESS_REPLAYED (generation)", "y_end": 1, "src": "k45 cohort"})
            jobs.append({"key": f"C|k{m}_witness|{rec['ids']['root_id']}|singletons", "path": str(rp), "kind": "X_CHUNKED", "order": w,
                         "bounds": list(range(1, m + 1)), "y": {"target": "t0", "goal": rec["goal"]}})
    seal(out, f"panel_C_{dom}.json", panel)
    seal(out, f"jobs_C_{dom}.json", jobs)
    print(json.dumps({"dom": dom, "panel": collections.Counter(p["group"] for p in panel), "jobs": len(jobs)}))


if __name__ == "__main__":
    {"matchedN": matchedN, "omission": omission, "connectors": connectors}[sys.argv[1]](sys.argv[2], sys.argv[3])
