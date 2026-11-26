#!/usr/bin/env python3
"""R2.1-A (matched N), R2.1-C (omission) and R2.2 (connectors) analysis on the new physical labels (evaluator side; gvlab2).
    python phys_analyze.py DOM OUT_DIR"""
from __future__ import annotations

import collections, json, math, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import common as C  # noqa: E402

J = C.R2 / "jobs"


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def load(dom):
    out = {}
    for l in open(C.R2 / f"phys_{dom}.jsonl"):
        r = json.loads(l)
        out[r["key"]] = r
    return out


def ylab(r):
    y = (r or {}).get("Y") or {}
    return y.get("y")


def xlab(r):
    x = (r or {}).get("X") or {}
    return x.get("x")


def matchedN(dom, R):
    F = json.loads((J / f"families_{dom}.json").read_text())
    V = {(v["fam"], v["k"]): v for v in json.loads((C.R2 / "r21" / f"variants_{dom}.json").read_text())}
    rows = []
    for f in F["families"]:
        base = {"x": 1, "y_rep": 1, "y_noop": 0, "y_neg": 0}
        rows.append({"fam": f["fam"], "k": "orig", "N": f["N0"], **base, **{kk: V.get((f["fam"], "orig"), {}).get(kk) for kk in ("p11_rep", "py_rep", "py_noop", "py_neg", "px_rep", "py_rep_rebased")}})
        for v in F["variants"]:
            if v["root_id"] != f["root_id"]:
                continue
            if not v["built"]:
                rows.append({"fam": f["fam"], "k": v["k"], "N": v["N"], "built": False, "why": v["why"]}); continue
            key = f"N|{f['root_id'][-14:]}|+{v['k']}"
            rx, r0, rn = R.get(key + "|X"), R.get(key + "|Y0"), R.get(key + "|YN")
            rows.append({"fam": f["fam"], "k": v["k"], "N": v["N"], "built": True, "x": xlab(rx), "x_status": ((rx or {}).get("X") or {}).get("teacher_status") or ((rx or {}).get("X") or {}).get("status"),
                         "y_rep": ylab(rx), "y_noop": ylab(r0), "y_neg": ylab(rn),
                         **{kk: V.get((f["fam"], v["k"]), {}).get(kk) for kk in ("p11_rep", "py_rep", "py_noop", "py_neg", "px_rep", "py_rep_rebased")}})
    out = {"families": len(F["families"]), "rows": rows, "by_k": {}}
    for k in sorted({r["k"] for r in rows}, key=str):
        rk = [r for r in rows if r["k"] == k and r.get("built", True)]
        same = [r for r in rk if (r["x"], r["y_rep"], r["y_noop"], r["y_neg"]) == (1, 1, 0, 0)]
        dec = [r for r in rk if None not in (r["x"], r["y_rep"], r["y_noop"], r["y_neg"])]
        o = {"variants": len(rk), "decided": len(dec), "labels_unchanged": len(same), "x_rep=1": sum(r["x"] == 1 for r in dec), "y_rep=1": sum(r["y_rep"] == 1 for r in dec),
             "y_noop=0": sum(r["y_noop"] == 0 for r in dec), "y_neg=0": sum(r["y_neg"] == 0 for r in dec)}
        for name, rr in (("all", rk), ("unchanged", same)):
            if rr and rr[0].get("py_rep") is not None:
                o[f"{name}_mean"] = {kk: float(np.mean([r[kk] for r in rr])) for kk in ("p11_rep", "py_rep", "py_noop", "py_neg", "px_rep")}
                o[f"{name}_disc_rep>neg"] = float(np.mean([r["py_rep"] > r["py_neg"] for r in rr]))
                o[f"{name}_disc_rep>noop"] = float(np.mean([r["py_rep"] > r["py_noop"] for r in rr]))
        out["by_k"][str(k)] = o
    pooled = {}
    for k in sorted({r["k"] for r in rows}, key=str):
        yl, pl = [], []
        for r in rows:
            if r["k"] == k and r.get("built", True) and r.get("py_rep") is not None:
                for yk, pk in (("y_rep", "py_rep"), ("y_noop", "py_noop"), ("y_neg", "py_neg")):
                    if r.get(yk) in (0, 1):
                        yl.append(r[yk]); pl.append(r[pk])
        pooled[str(k)] = {"n": len(yl), "pos": int(sum(yl)), "auroc_pY": C.auroc(yl, pl), "mean_py_pos": float(np.mean([p for y, p in zip(yl, pl) if y == 1])) if sum(yl) else None,
                          "mean_py_neg": float(np.mean([p for y, p in zip(yl, pl) if y == 0])) if len(yl) > sum(yl) else None}
    out["pooled_Y_by_level"] = pooled
    # paired change vs orig on the unchanged-label subset (per family, same distractors nested)
    orig = {r["fam"]: r for r in rows if r["k"] == "orig"}
    d = collections.defaultdict(list)
    for r in rows:
        if r["k"] in ("orig", 0) or not r.get("built") or (r["x"], r["y_rep"], r["y_noop"], r["y_neg"]) != (1, 1, 0, 0) or r.get("py_rep") is None:
            continue
        o = orig[r["fam"]]
        for kk in ("p11_rep", "py_rep", "py_noop", "py_neg"):
            d[(r["k"], kk)].append(r[kk] - o[kk])
    out["paired_delta_unchanged"] = {f"+{k}:{kk}": {"n": len(v), "mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))} for (k, kk), v in sorted(d.items(), key=str)}
    noise = [r for r in rows if r["k"] == 0]
    out["rng_noise_floor_+0"] = {"n": len(noise), "labels_unchanged": sum((r["x"], r["y_rep"], r["y_noop"], r["y_neg"]) == (1, 1, 0, 0) for r in noise),
                                 "rows": [{kk: r.get(kk) for kk in ("fam", "x", "y_rep", "y_noop", "y_neg")} for r in noise]}
    return out


def omission(dom, R):
    T = C.NW / "k3val/runs/out/ttarget"
    E = json.loads((T / f"EXAMPLES_{dom}_b.json").read_text()); Rw = json.loads((T / f"TT_{dom}_b.json").read_text())["rows"]
    rows = []
    for e, r in zip(E, Rw):
        if r["y_tt_S0"] != 0 or r["xy_tt_P"] != [1, 1] or len(e["P"]) < 2:
            continue
        for i in range(len(e["P"])):
            keep = [p for j, p in enumerate(e["P"]) if j != i]
            sk = f"{keep[0][0]}>{keep[0][1]}"
            if len(keep) == 1 and sk in r["single"]:
                y, src = r["single"][sk]["y"], "C3b single (exact reuse)"
            else:
                rr = R.get(f"OM|{e['root_id'][-14:]}|-{i}")
                y, src = ylab(rr), "new Y_TT"
            rows.append({"root": e["root_id"], "omit": i, "keep": keep, "y_tau": y, "src": src})
    ro = {x["root"]: x for x in json.loads((C.R2 / "r21" / f"omission_readout_{dom}.json").read_text())}
    for r in rows:
        x = ro.get(r["root"])
        if x:
            r.update(py=x["omit"][r["omit"]]["py"], py_P=x["py_P"], py_noop=x["py_noop"], fam=x["fam"])
    dec = [r for r in rows if r["y_tau"] in (0, 1)]
    model = {"auroc_py_keep_vs_ytau": C.auroc([r["y_tau"] for r in dec if "py" in r], [r["py"] for r in dec if "py" in r]),
             "mean_py_when_omission_breaks": float(np.mean([r["py"] for r in dec if r["y_tau"] == 0 and "py" in r])) if dec else None,
             "mean_py_when_omission_harmless": float(np.mean([r["py"] for r in dec if r["y_tau"] == 1 and "py" in r])) if dec else None,
             "beats_empty_on_keep": {"y1_admitted": sum(r["py"] > r["py_noop"] for r in dec if r["y_tau"] == 1 and "py" in r), "y1": sum(r["y_tau"] == 1 for r in dec),
                                     "y0_admitted": sum(r["py"] > r["py_noop"] for r in dec if r["y_tau"] == 0 and "py" in r), "y0": sum(r["y_tau"] == 0 for r in dec)}}
    per_ex = collections.defaultdict(list)
    for r in dec:
        per_ex[r["root"]].append(r["y_tau"])
    return {"queries": len(rows), "decided": len(dec), "omission_breaks_parent": sum(r["y_tau"] == 0 for r in dec),
            "examples_where_every_omission_breaks": sum(all(v == 0 for v in ys) for ys in per_ex.values()), "examples": len(per_ex),
            "examples_with_a_redundant_action": sum(any(v == 1 for v in ys) for ys in per_ex.values()), "model": model, "rows": rows}


def connectors(dom, R):
    panel = json.loads((J / f"panel_C_{dom}.json").read_text())
    jobs = json.loads((J / f"jobs_C_{dom}.json").read_text())
    arch = {}
    if dom == "3d":
        for l in open(C.NW / "k45/eval/eval_oracle.jsonl"):
            e = json.loads(l)
            if e["key"].startswith("oracle_witness_boundary") and not e.get("censored"):
                arch[e["root_id"]] = e
    res = []
    for p in panel:
        ks = [j["key"] for j in jobs if j["key"].split("|")[2] in (p["root"][-14:], p["root"]) and j["key"].split("|")[1] == p["group"]]
        row = {**{k: p[k] for k in ("group", "root", "fam", "N", "x_cont", "status_cont", "y_end")}, "m": len(p["seq"]), "parts": {}}
        for k in ks:
            r = R.get(k)
            if r is None:
                continue
            X = r.get("X") or {}
            b = k.split("|")[-1]
            conns = [t for t in X.get("trace", []) if t.get("kind") == "connector"]
            row["parts"][b] = {"x": X.get("x"), "status": X.get("teacher_status") or X.get("status"), "phase": X.get("failed_phase") or X.get("phase"),
                               "replay": X.get("independent_replay") if dom == "2d" else (r.get("REPLAY") or {}).get("replay"),
                               "connectors_ok": sum(1 for t in conns if t.get("ok", True)), "connectors": len(conns),
                               "how": [t.get("how") for t in conns] if dom == "2d" else None, "y": ylab(r), "cpu_s": r.get("cpu_s")}
        if dom == "3d" and p["root"] in arch:
            a = arch[p["root"]]
            row["parts"]["[2,m] archived"] = {"x": a["X"].get("x"), "status": a["X"].get("status"), "phase": a["X"].get("phase"), "y": (a.get("Y") or {}).get("y"), "src": "eval_oracle (exact reuse)"}
        res.append(row)
    summ = {}
    for grp in sorted({r["group"] for r in res}):
        rr = [r for r in res if r["group"] == grp]
        parts = sorted({b for r in rr for b in r["parts"]})
        s = {"sequences": len(rr), "continuous_x1": sum(r["x_cont"] == 1 for r in rr)}
        for b in parts:
            v = [r["parts"][b] for r in rr if b in r["parts"]]
            dec = [x for x in v if x["x"] in (0, 1)]
            k1 = sum(x["x"] == 1 for x in dec)
            s[b] = {"n": len(v), "decided": len(dec), "x1": k1, "rate": round(k1 / len(dec), 3) if dec else None, "wilson": wilson(k1, len(dec)),
                    "fail_phase": dict(collections.Counter((x.get("phase") or "none") for x in dec if x["x"] == 0)),
                    "fail_status": dict(collections.Counter(str(x.get("status")) for x in dec if x["x"] == 0))}
        summ[grp] = s
    # gate: pooled split partitions vs continuous on the matched positive panel(s)
    pos = [r for r in res if r["x_cont"] == 1 and r["group"] != "m2_conn_fail"]
    sp = [x for r in pos for b, x in r["parts"].items() if b not in (f"[{r['m']}]",) and x.get("x") in (0, 1)]
    cont_spot = [x for r in pos for b, x in r["parts"].items() if b == f"[{r['m']}]" and x.get("x") in (0, 1)]
    k = sum(x["x"] == 1 for x in sp)
    gate = {"split_runs": len(sp), "split_x1": k, "split_rate": round(k / len(sp), 3) if sp else None, "wilson": wilson(k, len(sp)),
            "continuous_rate_panel": 1.0, "continuous_spot_reverify": [sum(x["x"] == 1 for x in cont_spot), len(cont_spot)]}
    gate["ratio"] = gate["split_rate"]
    gate["decision"] = None if not sp else ("CONNECTOR_COMPATIBLE" if gate["ratio"] >= 0.9 else "CONNECTOR_LIMITED")
    return {"rows": res, "summary": summ, "gate": gate}


if __name__ == "__main__":
    dom, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    R = load(dom)
    res = {"dom": dom, "jobs_recorded": len(R), "cpu_h": round(sum(r.get("cpu_s", 0) for r in R.values()) / 3600, 3),
           "errors": [k for k, r in R.items() if r.get("error") or r.get("censored")],
           "matchedN": matchedN(dom, R), "omission": omission(dom, R), "connectors": connectors(dom, R)}
    (out / f"R2_phys_{dom}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"jobs": res["jobs_recorded"], "cpu_h": res["cpu_h"], "errors": res["errors"], "matchedN_by_k": res["matchedN"]["by_k"],
                      "paired": res["matchedN"]["paired_delta_unchanged"], "noise": res["matchedN"]["rng_noise_floor_+0"],
                      "omission": {k: v for k, v in res["omission"].items() if k != "rows"}, "conn_summary": res["connectors"]["summary"], "gate": res["connectors"]["gate"]}, indent=1, default=str))
