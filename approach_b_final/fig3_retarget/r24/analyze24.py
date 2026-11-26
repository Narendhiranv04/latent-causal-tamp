#!/usr/bin/env python3
"""R2.4 analysis (evaluator side; strict: NOT_RUN / UNKNOWN never counted as success).
    python analyze24.py oracle            R2.4A: order recovery vs direct / chunk-H / random / witness controls (3D)
    python analyze24.py arms DOM          R2.4B/C: arm outcomes, coverage funnel, failure locations, paired vs R2.3 arms
    python analyze24.py local DOM LABELS  local-X discrimination by prefix length h; Y_global vs Y_rebased on identical endpoints"""
from __future__ import annotations

import collections, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent), str(HERE.parent / "r2")]
import common as C  # noqa: E402
import jobs24 as JB  # noqa: E402
import order as OD  # noqa: E402

O = C.FIG3 / "r24"


def roster(dom):
    return {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / f"roster_{dom}.jsonl")}


def outcome_index(dom):
    """(root, seq json, bounds json) -> outcome from the R2.4 selection + R2.4 physical results."""
    sel = json.loads((O / f"selection_24_{dom}.json").read_text())
    pf = O / f"phys_24_{dom}.jsonl"
    phys = {json.loads(l)["key"]: json.loads(l) for l in open(pf)} if pf.exists() else {}
    out = {}
    for s in sel:
        k = tuple(s["key"])
        if s["status"] == "REUSED":
            out[k] = {"x": s["x"], "y": s["y"], "phase": s.get("phase") or "", "src": s["src"], "status": "REUSED"}
        elif s["status"] == "QUEUED" and s["job"] in phys and not phys[s["job"]].get("censored") and not phys[s["job"]].get("error"):
            r = phys[s["job"]]; X, Y = r.get("X") or {}, r.get("Y") or {}
            unk = lambda d: str(d.get("teacher_status") or d.get("status") or "").startswith("UNKNOWN")  # noqa: E731
            out[k] = {"x": None if unk(X) else X.get("x"), "y": None if unk(Y) else Y.get("y"), "phase": str(X.get("phase") or X.get("failed_phase") or ""),
                      "replay": (r.get("REPLAY") or {}).get("replay"), "teacher_status": X.get("teacher_status") or X.get("status"), "status": "NEW"}
        else:
            out[k] = {"x": None, "y": None, "phase": "", "status": s["status"] if s["status"] != "QUEUED" else "UNKNOWN_OR_MISSING"}
    return out


def z_of(o):
    if o is None or o.get("x") is None or o.get("y") is None:
        return None
    return int(o["x"] == 1 and o["y"] == 1)


def fail_loc(seq, part, o):
    """first failing chunk index, its prefix length h, chunk length, kind (relocation / boundary / Y)."""
    if not o or o.get("x") is None:
        return None
    if o["x"] == 1:
        return {"kind": "Y" if o.get("y") == 0 else None}
    kind, _, j = o.get("phase", "").partition(":")
    if not j.isdigit():
        return {"kind": kind or "unknown"}
    j = int(j); s = 0
    for ci, g in enumerate(part):
        e = s + g
        if (kind == "relocation" and s <= j < e) or (kind == "boundary" and j == e):
            return {"kind": kind, "chunk": ci, "h": s, "g": g, "chunk_seq": seq[s:e], "prefix": seq[:s]}
        s = e
    return {"kind": kind}


# ------------------------------------------------------------------ R2.4A
def oracle():
    R = roster("3d")
    OR = json.loads((O / "oracle_3d.json").read_text())
    K = json.loads((C.NW / "k45/eval/oracle_plans.json").read_text())
    A = JB.archive("3d", R)
    OI = outcome_index("3d")
    lookup = lambda rid, seq, part: (OI.get((rid, json.dumps(seq), json.dumps(JB.bounds(part)))) or JB.lookup("3d", A, rid, R[rid]["inputs"]["ids"], seq, JB.bounds(part)))  # noqa: E731
    res = {"roots": {}, "counts": {}}
    for rid in sorted(OR):
        o, k = OR[rid], K[rid]
        w = k["witness_order"]; m = len(w)
        T = {"wt": w}
        per = {}
        plans = {"A-DP": (o["A-DP"]["order"], o["A-DP"]["partition"]), "A-PRE": (o["A-PRE"]["order"], o["A-PRE"]["partition"]),
                 "A-DP0": (o["A-DP0"]["order"], o["A-DP0"]["partition"]),
                 "direct": (k["direct"]["order"], [m]), "chunkH": (k["chunk"]["order"], k["chunk"]["partition"]), "random": (k["random"]["order"], [m]),
                 "mode_control": (k["chunk"]["order"], [m]), "witness_split": (w, [2, m - 2]), "witness_continuous": (w, [m])}
        for name, (seq, part) in plans.items():
            out = lookup(rid, seq, part)
            if name == "witness_continuous" and out is None:
                out = {"x": 1, "y": 1, "src": "generator continuous witness (x_witnesses + y_witnesses)"}
            per[name] = {"order": seq, "partition": part, "z": z_of(out), "x": (out or {}).get("x"), "y": (out or {}).get("y"),
                         "src": (out or {}).get("src") or (out or {}).get("status"), "exact_witness_order": seq == w, "kendall": OD.kendall(seq, w),
                         "fail": fail_loc(seq, part, out)}
        ords = [r["order"] for r in o["orders"]]
        wi = ords.index(w) if w in ords else None
        chunks = {(json.dumps(c["prefix"]), json.dumps(c["chunk"])): c for c in o["chunks"]}
        f = per["A-DP"]["fail"]
        if f and f.get("chunk_seq"):
            c = chunks.get((json.dumps(OD.canon(f["prefix"])), json.dumps(f["chunk_seq"])))
            f["px_failed_chunk"] = c["px"] if c else None
        wpre = {OD._t([a])[0]: i for i, a in enumerate(w)}
        edges = o["A-PRE"]["edges"]
        res["roots"][rid] = {"m": m, "arms": per, "witness_rank": None if wi is None else wi + 1, "n_orders": len(ords),
                             "witness_E": o["orders"][wi]["E"] if wi is not None else None, "witness_best_partition": o["orders"][wi]["partition"] if wi is not None else None,
                             "dp_E": o["A-DP"]["E"], "pre_edges": len(edges),
                             "pre_edges_agree_witness": sum(wpre[OD._t([a])[0]] < wpre[OD._t([b])[0]] for a, b, _ in edges), "y_global": o["y_global"],
                             "y_rebased": o["y_rebased"], "latency_s": o["latency_s"], "scenes": o["scenes"], "x_unique": o["counters"]["x_unique"]}
    rs = res["roots"].values()
    for name in ("A-DP", "A-PRE", "A-DP0", "direct", "chunkH", "random", "mode_control", "witness_split", "witness_continuous"):
        z = [r["arms"][name]["z"] for r in rs]
        res["counts"][name] = {"verified": sum(v == 1 for v in z), "decided": sum(v is not None for v in z), "unknown_or_not_run": sum(v is None for v in z),
                               "exact_witness_order": sum(r["arms"][name]["exact_witness_order"] for r in rs),
                               "mean_kendall": float(np.mean([r["arms"][name]["kendall"] for r in rs])),
                               "by_m": {m: sum(r["arms"][name]["z"] == 1 for r in rs if r["m"] == m) for m in (4, 5)},
                               "fail_kinds": dict(collections.Counter((r["arms"][name]["fail"] or {}).get("kind") for r in rs if r["arms"][name]["z"] == 0))}
    dpf = [r["arms"]["A-DP"]["fail"] for r in rs if r["arms"]["A-DP"]["z"] == 0 and r["arms"]["A-DP"]["fail"]]
    res["A-DP_failures"] = {"n": len(dpf), "by_chunk_h": dict(collections.Counter(f"chunk{f.get('chunk')}|h{f.get('h')}|{f.get('kind')}" for f in dpf)),
                            "confident_at_h_ge1": sum(1 for f in dpf if (f.get("h") or 0) >= 1 and (f.get("px_failed_chunk") or 0) >= 0.5),
                            "at_h_ge1": sum(1 for f in dpf if (f.get("h") or 0) >= 1), "connector": sum(1 for f in dpf if f.get("kind") == "boundary")}
    res["witness_rank"] = {"median": float(np.median([r["witness_rank"] for r in rs if r["witness_rank"]])),
                           "top1": sum(r["witness_rank"] == 1 for r in rs), "top10pct": sum(r["witness_rank"] <= max(1, r["n_orders"] // 10) for r in rs if r["witness_rank"]),
                           "median_E_gap": float(np.median([r["witness_E"] - r["dp_E"] for r in rs if r["witness_E"] is not None]))}
    pe = [(r["pre_edges_agree_witness"], r["pre_edges"]) for r in rs]
    res["pre_edges"] = {"edges": sum(b for _, b in pe), "agree_witness": sum(a for a, _ in pe), "roots_with_edges": sum(1 for _, b in pe if b)}
    def paired(a, b):
        d = [(r["arms"][a]["z"], r["arms"][b]["z"]) for r in rs if r["arms"][a]["z"] is not None and r["arms"][b]["z"] is not None]
        return {"pairs": len(d), "a_only": sum(x == 1 and y == 0 for x, y in d), "b_only": sum(x == 0 and y == 1 for x, y in d), "both": sum(x == y == 1 for x, y in d)}
    res["paired"] = {f"A-DP vs {b}": paired("A-DP", b) for b in ("direct", "chunkH", "random", "witness_split")}
    (O / "R2_4A_3d.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "roots"}, indent=1, default=str))


# ------------------------------------------------------------------ R2.4B / C
def known_sets(dom, R):
    K = {}
    if dom == "3d":
        for rid in R:
            w = json.loads((C.NW / "k45/eval/oracle_plans.json").read_text())[rid]["witness_order"]
            K[rid] = [{tuple(a) for a in w}]
    else:
        Yl = collections.defaultdict(dict)
        P = C.pool(dom)
        for e in P:
            if e["root"] in R and e["t"] == "Y":
                Yl[e["root"]][json.dumps(sorted([list(map(int, a)) for a in e["edit"]]))] = e["y"]
        for e in P:
            if e["root"] in R and e["t"] == "X" and e["x"] == 1 and Yl[e["root"]].get(json.dumps(sorted([list(map(int, a)) for a in e["seq"]]))) == 1:
                K.setdefault(e["root"], []).append({tuple(map(int, a)) for a in e["seq"]})
    return K


def arms(dom):
    R = roster(dom)
    OI = outcome_index(dom)
    D = {json.loads(l)["root_id"]: json.loads(l) for l in open(O / f"deploy_{dom}.jsonl")}
    r23 = json.loads((C.R2 / "r23" / f"R2_3_{dom}.json").read_text())
    K = known_sets(dom, R)
    res = {"dom": dom, "arms": {}, "funnel": {}, "paired": {}}
    per = {}
    for arm in ("R-FIG3-X", "R-FIG3-XP", "R-FIG3-XC", "GA-INIT", "GA-UNION"):
        rows = []
        for rid in sorted(R):
            p = D[rid][arm]
            if not p["seq"]:
                rows.append({"root": rid, "z": 0, "why": p["decision"]}); continue
            o = OI.get((rid, json.dumps(p["seq"]), json.dumps(JB.bounds(p["partition"]))))
            rows.append({"root": rid, "z": z_of(o), "x": (o or {}).get("x"), "y": (o or {}).get("y"), "why": (o or {}).get("status"),
                         "fail": fail_loc(p["seq"], p["partition"], o), "len": len(p["seq"]), "returns": len(p["partition"]) - 1})
        per[arm] = {r["root"]: r for r in rows}
        z = [r["z"] for r in rows]
        lat = [D[rid][arm]["latency_s"] for rid in R]
        res["arms"][arm] = {"verified": sum(v == 1 for v in z), "decided": sum(v is not None for v in z), "unknown_or_not_run": sum(v is None for v in z),
                            "repair": sum(D[rid][arm]["decision"] == "REPAIR" for rid in R), "mean_len": float(np.mean([r["len"] for r in rows if "len" in r] or [0])),
                            "mean_returns": float(np.mean([r["returns"] for r in rows if "returns" in r] or [0])),
                            "failure_modes": dict(collections.Counter(f"X{r.get('x')}Y{r.get('y')}" + (":" + (r["fail"] or {}).get("kind", "") if r.get("x") == 0 else "")
                                                                      for r in rows if r["z"] == 0 and "x" in r)),
                            "fail_h": dict(collections.Counter(f"h{(r['fail'] or {}).get('h')}" for r in rows if r["z"] == 0 and r.get("x") == 0)),
                            "connector_failures": sum(1 for r in rows if (r.get("fail") or {}).get("kind") == "boundary"),
                            "latency_median_s": float(np.median(lat)), "latency_max_s": float(np.max(lat)),
                            "cap_stops": sum(bool(D[rid][arm]["cap_stop"]) for rid in R),
                            "x_unique_median": float(np.median([D[rid][arm]["counters"].get("x_unique", 0) for rid in R])),
                            "y_unique_median": float(np.median([D[rid][arm]["counters"].get("y_unique", 0) for rid in R]))}
        # coverage funnel (proposal coverage kept distinct from executable-plan discovery)
        fn = collections.Counter()
        for rid in R:
            ks = K.get(rid)
            if not ks:
                fn["no_known"] += 1; continue
            p = D[rid][arm]
            pool = {tuple(a) for a in (p.get("pool_actions") or p.get("union_actions") or [])}
            ranked = [{tuple(a) for a in c["seq"]} for c in p["top"]]
            fin = {tuple(a) for a in (p["seq"] or [])}
            fn["recall_pool"] += max(len(k & pool) / len(k) for k in ks)
            if any(k <= pool for k in ks):
                fn["known_set_in_pool"] += 1
            if any(k in ranked for k in ks):
                fn["known_set_ranked_top40"] += 1
            if any(k == fin for k in ks):
                fn["known_set_selected"] += 1
            if per[arm][rid]["z"] == 1:
                fn["verified"] += 1
                if not any(k == fin for k in ks):
                    fn["verified_non_known_set"] += 1
        nk = sum(1 for rid in R if K.get(rid))
        res["funnel"][arm] = {k: (v / nk if k == "recall_pool" else v) for k, v in fn.items()}
    disc = [D[rid]["R-FIG3-X"]["discovery_counters"] for rid in R]
    res["discovery"] = {"staged_calls_total": sum(d.get("staged_calls", 0) for d in disc), "roots_with_staged": sum(1 for d in disc if d.get("staged_calls")),
                        "x_unique_median": float(np.median([d.get("x_unique", 0) for d in disc])), "discovery_s_median": float(np.median([D[rid]["R-FIG3-X"]["discovery_s"] for rid in R])),
                        "discovery_stops": sum(1 for rid in R if D[rid]["R-FIG3-X"]["discovery_stop"]),
                        "union_actions_median": float(np.median([len(D[rid]["R-FIG3-X"]["union_actions"]) for rid in R])),
                        "d4_actions_median": float(np.median([len(D[rid]["GA-INIT"]["pool_actions"]) for rid in R]))}
    for a in ("B0", "R-FIG3", "F-FLAT"):
        pr = r23["arms"][a]["per_root"]
        per[a] = {rid: {"z": pr[rid]["z"]} for rid in pr}
        res["arms"][a + " (R2.3)"] = {"verified": r23["arms"][a]["verified"], "decided": r23["arms"][a]["decided"]}
    def paired(a, b):
        d = [(per[a][r]["z"], per[b][r]["z"]) for r in R if per[a][r]["z"] is not None and per[b][r]["z"] is not None]
        return {"pairs": len(d), "a_only": sum(x == 1 and y == 0 for x, y in d), "b_only": sum(x == 0 and y == 1 for x, y in d), "both": sum(x == y == 1 for x, y in d)}
    for a in ("R-FIG3-X", "GA-UNION", "GA-INIT", "R-FIG3-XP", "R-FIG3-XC"):
        for b in ("R-FIG3", "F-FLAT", "B0"):
            res["paired"][f"{a} vs {b}"] = paired(a, b)
    res["paired"]["GA-UNION vs R-FIG3-X"] = paired("GA-UNION", "R-FIG3-X")
    res["paired"]["GA-UNION vs GA-INIT"] = paired("GA-UNION", "GA-INIT")
    res["paired"]["R-FIG3-X vs R-FIG3-XC"] = paired("R-FIG3-X", "R-FIG3-XC")
    res["per_root"] = {a: per[a] for a in per}
    (O / f"R2_4B_{dom}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "per_root"}, indent=1, default=str))


# ------------------------------------------------------------------ local X and Y representation
def local(dom, lab):
    L = [json.loads(l) for l in open(lab)]
    CH = [c for c in L if c["t"] == "chunk" and c["label"] in (0, 1)]
    EP = [e for e in L if e["t"] == "endpoint" and e["y"] in (0, 1)]
    for c in CH:
        c["fam"] = c["root_id"]
    RO = set(roster(dom))                                                  # the 20 R2.3 / R2.4 development roots of this domain
    res = {"dom": dom, "n_chunks": len(CH), "conflicts": sum(1 for c in L if c["t"] == "chunk" and c.get("conflict")), "by_h": {}, "by_src": {}}
    strata = {"h0": lambda c: c["h"] == 0, "h>=1": lambda c: c["h"] >= 1, "h1-2": lambda c: 1 <= c["h"] <= 2, "h>=3": lambda c: c["h"] >= 3,
              "h>=1,g1": lambda c: c["h"] >= 1 and c["m"] == 1, "h>=1,g2-3": lambda c: c["h"] >= 1 and c["m"] >= 2,
              "h>=1,no_conn_neg": lambda c: c["h"] >= 1 and c["kind"] != "chunk_conn_neg",
              "h0,cohort": lambda c: c["h"] == 0 and c["root_id"] in RO, "h>=1,cohort": lambda c: c["h"] >= 1 and c["root_id"] in RO}
    for name, f in strata.items():
        S = [c for c in CH if f(c)]
        res["by_h"][name] = {"px": C.summary(S, "label", "px", "fam"), "p11": C.summary(S, "label", "p11", "fam")}
        neg = [c for c in S if c["label"] == 0]
        res["by_h"][name]["confident_negatives_px>=0.5"] = sum(1 for c in neg if c["px"] >= 0.5)
        res["by_h"][name]["negatives"] = len(neg)
    for s in sorted({x for c in CH for x in c["srcs"]}):
        S = [c for c in CH if s in c["srcs"]]
        res["by_src"][s] = {"n": len(S), "pos": sum(c["label"] for c in S), "h>=1": sum(c["h"] >= 1 for c in S)}
    for e in EP:
        e["fam"] = e["root_id"]
    res["Y"] = {}
    for name, f in {"all": lambda e: True, "m<=3": lambda e: e["m"] <= 3, "m>=4": lambda e: e["m"] >= 4}.items():
        S = [e for e in EP if f(e)]
        res["Y"][name] = {"y_global": C.summary(S, "y", "y_global", "fam"), "y_rebased": C.summary(S, "y", "y_rebased", "fam")}
    (O / f"R2_4_local_{dom}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str)[:6000])


if __name__ == "__main__":
    {"oracle": lambda: oracle(), "arms": lambda: arms(sys.argv[2]), "local": lambda: local(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
