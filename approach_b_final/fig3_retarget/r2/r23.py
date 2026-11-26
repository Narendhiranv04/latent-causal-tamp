#!/usr/bin/env python3
"""R2.3 evaluator: presealed physical selection of committed plans, funnel against known witnesses / verified repairs, arm outcomes.
    python r23.py build DOM CAP        unique (root, seq, partition) plans in fixed arm priority, exact archived labels reused, <= CAP new units
    python r23.py analyze DOM          funnel + per-arm outcomes (strict: NOT_RUN / UNKNOWN never counted as success)"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import common as C  # noqa: E402

O = C.R2 / "r23"
PRIORITY = ["R-FIG3", "F-FLAT", "R-GATED", "R-FIG3-ALL", "R-FIG3-RP", "R-TOPO", "B0"]


def bounds(part):
    out, s = [], 0
    for g in part:
        s += g; out.append(s)
    return out


def plans(dom):
    return [json.loads(l) for l in open(O / f"plans_{dom}.jsonl")]


def rows_of(dom):
    return {json.loads(l)["root_id"]: json.loads(l) for l in open(O / f"roster_{dom}.jsonl")}


def archived(dom):
    """Exact-compatible archived labels: 3D K45 evaluations keyed (root, names-seq json, bounds); 2D pool X+Y for continuous partitions."""
    A = {}
    if dom == "3d":
        for f in ("eval_primary.jsonl", "eval_oracle.jsonl"):
            for l in open(C.NW / "k45/eval" / f):
                e = json.loads(l)
                p = e["key"].split("|")
                if e.get("censored") or len(p) < 4 or "X" not in e:
                    continue
                A[(e["root_id"], p[2].replace(" ", ""), p[3].replace(" ", ""))] = {"x": e["X"].get("x"), "y": (e.get("Y") or {}).get("y"), "src": "k45 eval " + p[0]}
    else:
        X, Y = {}, {}
        for e in C.pool(dom):
            if e["t"] == "X":
                X[(e["root"], json.dumps([list(map(int, a)) for a in e["seq"]]))] = e["x"]
            else:
                Y[(e["root"], json.dumps(sorted([list(map(int, a)) for a in e["edit"]])))] = e["y"]
        A = {"X": X, "Y": Y}
    return A


def build(dom, cap):
    P = plans(dom); R = rows_of(dom); A = archived(dom)
    seen, units, jobs, sel = set(), 0, [], []
    order = sorted(P, key=lambda p: (PRIORITY.index(p["arm"]), C.h("R2_3|" + p["root_id"])))
    for p in order:
        if not p["seq"]:
            continue
        ids = R[p["root_id"]]["inputs"]["ids"]
        part = p["partition"] or [len(p["seq"])]
        b = bounds(part)
        k = (p["root_id"], json.dumps(p["seq"]), json.dumps(b))
        if k in seen:
            continue
        seen.add(k)
        names = [[ids[o], d if dom == "2d" else [d // 6, d % 6]] for o, d in p["seq"]]
        if dom == "3d":
            ak = (p["root_id"], json.dumps(names).replace(" ", ""), json.dumps(b).replace(" ", ""))
            if ak in A:
                sel.append({"key": k, "status": "REUSED", **A[ak]}); continue
        else:
            xs = A["X"].get((p["root_id"], json.dumps(p["seq"])))
            ys = A["Y"].get((p["root_id"], json.dumps(sorted(p["seq"]))))
            if b == [len(p["seq"])] and xs is not None and ys is not None:
                sel.append({"key": k, "status": "REUSED", "x": xs, "y": ys, "src": "pool (x_chunked(bounds={m}) == x_query)"}); continue
        cost = 1 if dom == "3d" else 2
        if units + cost > int(cap):
            sel.append({"key": k, "status": "NOT_RUN_BUDGET"}); continue
        units += cost
        key = f"S|{p['root_id'][-18:]}|{json.dumps(p['seq'])}|{json.dumps(b)}"
        if dom == "3d":
            rp = C.NW / "k45/cohort/roots" / f"{p['root_id']}.json"
            rec = json.loads(rp.read_text())
            jobs.append({"key": key, "path": str(rp), "kind": "X_CHUNKED", "order": names, "bounds": b, "y": {"target": "t0", "goal": rec["goal"]}})
        else:
            path, geom = C.raw_path(dom, p["root_id"])
            jobs.append({"key": key, "path": path, "geom": geom, "kind": "X_CHUNKED", "seq": names, "bounds": b, "y_endpoint": True})
        sel.append({"key": k, "status": "QUEUED", "job": key})
    jf = O / f"jobs_S_{dom}.json"; jf.write_text(json.dumps(jobs, indent=1))
    sf = O / f"selection_{dom}.json"; sf.write_text(json.dumps(sel, indent=1))
    for f in (jf, sf):
        (O / (f.name + ".SEAL")).write_text(hashlib.sha256(f.read_bytes()).hexdigest())
    print(json.dumps({"dom": dom, "unique_plans": len(sel), "reused": sum(s["status"] == "REUSED" for s in sel), "queued_jobs": len(jobs), "units": units,
                      "not_run_budget": sum(s["status"] == "NOT_RUN_BUDGET" for s in sel)}))


def analyze(dom):
    P = plans(dom); R = rows_of(dom)
    sel = {tuple(s["key"]): s for s in json.loads((O / f"selection_{dom}.json").read_text())}
    phys = {json.loads(l)["key"]: json.loads(l) for l in open(C.R2 / f"phys_S_{dom}.jsonl")} if (C.R2 / f"phys_S_{dom}.jsonl").exists() else {}
    def outcome(p):
        if not p["seq"]:
            return {"z": 0, "why": p["decision"]}
        b = bounds(p["partition"] or [len(p["seq"])])
        s = sel.get((p["root_id"], json.dumps(p["seq"]), json.dumps(b)))
        if s is None:
            return {"z": None, "why": "MISSING"}
        if s["status"] == "REUSED":
            x, y = s["x"], s["y"]
        elif s["status"] == "QUEUED" and s["job"] in phys:
            r = phys[s["job"]]; x = (r.get("X") or {}).get("x"); y = (r.get("Y") or {}).get("y")
        else:
            return {"z": None, "why": s["status"]}
        ph = None
        if s["status"] == "QUEUED":
            X = phys[s["job"]].get("X") or {}
            ph = str(X.get("phase") or X.get("failed_phase") or "")
        return {"z": None if x is None or y is None else int(x == 1 and y == 1), "x": x, "y": y, "why": s["status"], "phase": ph}
    # known useful ingredients: 3D witness order; 2D verified (X=1, Y=1) pool sequences on the root
    known = {}
    if dom == "3d":
        for rid, row in R.items():
            rec = json.loads((C.NW / "k45/cohort/roots" / f"{rid}.json").read_text())
            ids = row["inputs"]["ids"]
            known[rid] = [[[ids.index(o), d[0] * 6 + d[1]] for o, d in rec["k45"]["witness"]["order"]]]
    else:
        Yl = collections.defaultdict(dict)
        for e in C.pool(dom):
            if e["root"] in R and e["t"] == "Y":
                Yl[e["root"]][json.dumps(sorted([list(map(int, a)) for a in e["edit"]]))] = e["y"]
        for e in C.pool(dom):
            if e["root"] in R and e["t"] == "X" and e["x"] == 1 and Yl[e["root"]].get(json.dumps(sorted([list(map(int, a)) for a in e["seq"]]))) == 1:
                known.setdefault(e["root"], []).append([list(map(int, a)) for a in e["seq"]])
    arms = sorted({p["arm"] for p in P}, key=PRIORITY.index)
    res = {"dom": dom, "roots": len(R), "arms": {}, "funnel": {}}
    for arm in arms:
        pa = [p for p in P if p["arm"] == arm]
        outs = [outcome(p) for p in pa]
        z = [o["z"] for o in outs]
        dec = [v for v in z if v is not None]
        res["arms"][arm] = {"roots": len(pa), "repair": sum(p["decision"] == "REPAIR" for p in pa), "verified": sum(v == 1 for v in z), "decided": len(dec),
                            "unknown_or_not_run": sum(v is None for v in z), "strict_lower": sum(v == 1 for v in z) / len(pa), "upper": (sum(v == 1 for v in z) + sum(v is None for v in z)) / len(pa),
                            "mean_len": float(np.mean([len(p["seq"]) for p in pa if p["seq"]])) if any(p["seq"] for p in pa) else None,
                            "mean_returns": float(np.mean([len(p["partition"]) - 1 for p in pa if p["partition"]])) if any(p["partition"] for p in pa) else None,
                            "latency_median_s": float(np.median([p["latency_s"] for p in pa])), "cap_stops": sum(bool(p["cap_stop"]) for p in pa),
                            "readouts_median": {k: float(np.median([p["counters"].get(k, 0) for p in pa])) for k in ("x_unique", "y_unique", "temp_readouts", "repair_expansions", "staged_calls", "not_admitted")},
                            "per_root": {p["root_id"]: o for p, o in zip(pa, outs)}}
        res["arms"][arm]["failure_modes"] = dict(collections.Counter(
            f"X{o.get('x')}Y{o.get('y')}" + (":" + (o.get("phase") or "reused").split(":")[0] if o.get("x") == 0 else "") for o in outs if o.get("z") == 0 and "x" in o))
        # funnel: first stage at which a known useful ingredient set is lost
        fn = collections.Counter()
        for p in pa:
            K = known.get(p["root_id"])
            if not K:
                fn["no_known_ingredients"] += 1; continue
            acts = [{tuple(a) for a in k} for k in K]
            d4 = {(int(o), int(d)) for o, ds in p["d4_s0"].items() for d in ds}
            pu = {tuple(a) for a in p["proposals_union"]}
            ranked = [{tuple(a) for a in s} for s in p["ranked"]]
            fin = {tuple(a) for a in (p["seq"] or [])}
            if any(a <= fin for a in acts):
                fn["kept_to_final"] += 1
            elif any(any(a <= r for r in ranked) for a in acts):
                fn["lost_at_final_ranking"] += 1
            elif any(a <= pu for a in acts):
                fn["proposed_but_not_composed"] += 1
            elif any(a <= d4 for a in acts):
                fn["in_D4_S0_lost_in_search"] += 1
            else:
                fn["not_proposed"] += 1
            fn["ingredient_recall_D4_S0"] += max(len(a & d4) / len(a) for a in acts)
            fn["ingredient_recall_any_proposal"] += max(len(a & pu) / len(a) for a in acts)
        nk = sum(1 for p in pa if known.get(p["root_id"]))
        res["funnel"][arm] = {k: (v / nk if k.startswith("ingredient") and nk else v) for k, v in fn.items()}
    # paired contrasts (strict decided-only and bounds)
    def paired(a, b):
        A = res["arms"][a]["per_root"]; B = res["arms"][b]["per_root"]
        d = [(A[r]["z"], B[r]["z"]) for r in A if r in B]
        both = [(x, y) for x, y in d if x is not None and y is not None]
        return {"pairs_decided": len(both), "a_only": sum(x == 1 and y == 0 for x, y in both), "b_only": sum(x == 0 and y == 1 for x, y in both),
                "both": sum(x == 1 and y == 1 for x, y in both), "undecided_pairs": len(d) - len(both)}
    res["paired"] = {f"{a} vs {b}": paired(a, b) for a, b in (("R-FIG3", "F-FLAT"), ("R-FIG3", "R-GATED"), ("R-FIG3", "B0"), ("R-FIG3-ALL", "R-FIG3"),
                                                              ("R-FIG3-RP", "R-FIG3"), ("R-TOPO", "R-FIG3")) if a in res["arms"] and b in res["arms"]}
    (O / f"R2_3_{dom}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"arms": {a: {k: v for k, v in s.items() if k != "per_root"} for a, s in res["arms"].items()}, "funnel": res["funnel"], "paired": res["paired"]}, indent=1, default=str))


if __name__ == "__main__":
    {"build": lambda: build(sys.argv[2], sys.argv[3]), "analyze": lambda: analyze(sys.argv[2])}[sys.argv[1]]()
