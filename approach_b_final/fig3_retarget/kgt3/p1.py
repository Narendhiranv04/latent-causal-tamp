#!/usr/bin/env python3
"""KGT3 P1 composition audit (no new physical queries; nothing here selects a checkpoint, loss or search setting).
  arch2d    2D R3.4D archived 90 X_CHUNKED runs: exact chunk labels (labels.chunks_of), first failure, h / g, F0 chunk energy, witness rank,
            order-vs-partition attribution, connector outcomes
  panels    2D 30 + 3D 20 known-assignment panels: grouped DP (lambda 0 vs -log 0.92; has_multi vs unrestricted) under F0 (2D) and
            F0 / G1s / M1s (3D); witness-order rank under the new objective; all-singleton diagnostics; candidate counts
  quarantine  the 49 A2 outcomes as DIAGNOSTIC_ONLY copies (coverage, per-arm outcomes; never formal)
    $PYG p1.py arch2d | panels | quarantine   -> O/kgt3/p1_*.json"""
from __future__ import annotations

import collections, hashlib, itertools, json, math, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import compose as CP  # noqa: E402
import views as V  # noqa: E402
C, LB = K.C, K.LB
OUT = C.FIG3 / "kgt3"


def rows2d():
    return {json.loads(l)["root_id"]: json.loads(l) for l in open(K.O / "coh2d" / "rows.jsonl")}


def arch2d():
    from models import Frozen
    fz = Frozen("2d"); fz.caps = {}
    R = rows2d()
    P = json.loads((K.O / "coh2d" / "plans.json").read_text())
    jobs = json.loads((K.O / "coh2d" / "jobs.json").read_text())
    res = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / "coh2d" / "phys.jsonl")}
    labs, runs = [], []
    for j in jobs:
        r = res[j["key"]]; X = r.get("X") or {}; row = R[j["root_id"]]
        ch = LB.chunks_of(j["seq_idx"], j["bounds"], X, unknown=LB._unknown(X))
        for c in ch:
            px = fz.score(V.rebase(row, c["prefix"]), [c["chunk"]])[0]["px"]
            labs.append({"root_id": j["root_id"], "arm": j["arm"], "h": c["prefix_len"], "g": len(c["chunk"]), "label": c["label"], "kind": c["kind"],
                         "px_F0": px, "K": P[j["root_id"]]["K"]})
        W = P[j["root_id"]]["WITNESS"]["order"]
        o = j["seq_idx"]
        ph = str(X.get("failed_phase") or "")
        first = o[0]
        runs.append({"root_id": j["root_id"], "arm": j["arm"], "status": X.get("teacher_status"), "phase": ph, "x": X.get("x"),
                     "same_order_as_witness": o == W, "first_action_is_witness_first": first == W[0],
                     "first_chunk_set_is_witness_prefix_set": sorted(map(tuple, o[:j["bounds"][0]])) == sorted(map(tuple, W[:j["bounds"][0]])),
                     "bounds": j["bounds"], "connector_failure": ph.startswith("boundary")})
    summ = {"labels": len(labs), "by_h_g_label": collections.Counter(f"h{min(e['h'], 2)}_g{e['g']}_y{e['label']}" for e in labs),
            "auroc_F0": {k: C.summary([e for e in labs if f(e)], "label", "px_F0", "root_id") for k, f in
                         {"all": lambda e: True, "h0": lambda e: e["h"] == 0, "h>=1": lambda e: e["h"] >= 1, "g1": lambda e: e["g"] == 1,
                          "g2-3": lambda e: e["g"] >= 2, "h0_g2-3": lambda e: e["h"] == 0 and e["g"] >= 2}.items()},
            "fx_failures": collections.Counter(f'{r["status"]}@{r["phase"]}|first_is_wit_first={r["first_action_is_witness_first"]}|first_chunk_set_wit_prefix={r["first_chunk_set_is_witness_prefix_set"]}'
                                               for r in runs if r["arm"] == "FX-DP" and r["x"] != 1),
            "connector_failures": sum(r["connector_failure"] for r in runs),
            "attribution_fx": {"order_equal_witness": sum(r["same_order_as_witness"] for r in runs if r["arm"] == "FX-DP"),
                               "first_action_matches_witness": sum(r["first_action_is_witness_first"] for r in runs if r["arm"] == "FX-DP"),
                               "first_chunk_set_matches_witness_prefix": sum(r["first_chunk_set_is_witness_prefix_set"] for r in runs if r["arm"] == "FX-DP")}}
    (OUT / "p1_arch2d.json").write_text(json.dumps({"summary": summ, "labels": labs, "runs": runs}, indent=1, default=str))
    print(json.dumps({k: v for k, v in summ.items() if k != "auroc_F0"}, default=str))
    print(json.dumps({k: (v.get("auroc"), v.get("n"), v.get("pos")) for k, v in summ["auroc_F0"].items()}))


def panel(dom, models):
    """Known-assignment panels: SEL-style grouped DP under each model; lambda / has_multi variants; witness rank (evaluator)."""
    import planners as PL
    import train as TR
    if dom == "2d":
        R = rows2d(); P = json.loads((K.O / "coh2d" / "plans.json").read_text())
        items = [(rid, R[rid], P[rid]["assignment"], P[rid]["WITNESS"]["order"]) for rid in sorted(P)]
    else:
        R = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.R2 / "r23" / "roster_3d.jsonl")}
        orc = json.loads((C.FIG3 / "r24" / "oracle_3d.json").read_text())
        items = []
        for rid in sorted(R):
            rec = json.loads((C.NW / "k45/cohort/roots" / f"{rid}.json").read_text()); ids = R[rid]["inputs"]["ids"]
            W = [[ids.index(o), int(d[0]) * 6 + int(d[1])] for o, d in rec["k45"]["witness"]["order"]]
            items.append((rid, R[rid], orc[rid]["assignment"], W))
    out = {}
    for tag in models:
        if tag == "F0":
            from models import Frozen
            fz = Frozen(dom)
        else:
            a, s = tag.split("_s")
            fz, net = TR.load(dom, a, s); fz.net = net
        fz.reset(); fz.caps = {}
        rows = []
        for rid, row, A, W in items:
            T = CP.Scores(fz, row, V.rebase)
            A = sorted(CP._t(A)); T.need(CP.requests(A))
            yg = fz.y_global(row, [list(map(list, A))])[0]
            v = {}
            for name, kw in (("lam0_multi", {}), ("lam0_free", {"need_multi": False}), ("lamH_multi", {"lam": CP.LAM_HIST}), ("lamH_free", {"need_multi": False, "lam": CP.LAM_HIST})):
                F, o, p = CP.grouped_dp(T, A, **kw)
                v[name] = {"order": o, "partition": p, "E": F - math.log(max(CP.EPS, yg)), "all_singleton": max(p) == 1}
            rk = sorted(((CP.fixed_order_dp(T, list(o))[0], list(map(list, o))) for o in itertools.permutations(A)), key=lambda t: (round(t[0], 12), json.dumps(t[1])))
            wr = 1 + next(i for i, (_, o) in enumerate(rk) if o == [list(map(int, a)) for a in W])
            wf = CP.fixed_order_dp(T, [tuple(a) for a in W])
            rows.append({"root_id": rid, "m": len(A), "variants": v, "witness_rank_lam0_multi": [wr, len(rk)], "witness_partition": wf[2], "witness_F": wf[0],
                         "selected_eq_witness_order": v["lam0_multi"]["order"] == [list(map(int, a)) for a in W], "counts": CP.counts(len(A)), "x_scored": T.n["x_unique"],
                         "lam_changes_choice": (v["lam0_multi"]["order"], v["lam0_multi"]["partition"]) != (v["lamH_multi"]["order"], v["lamH_multi"]["partition"]),
                         "multi_constraint_binds": v["lam0_free"]["all_singleton"]})
            print(dom, tag, rid, v["lam0_multi"]["partition"], "wrank", rows[-1]["witness_rank_lam0_multi"], flush=True)
        out[tag] = {"roots": rows, "summary": {"lam_changes_choice": sum(r["lam_changes_choice"] for r in rows), "multi_constraint_binds": sum(r["multi_constraint_binds"] for r in rows),
                                               "witness_order_selected": sum(r["selected_eq_witness_order"] for r in rows),
                                               "median_witness_rank_quantile": sorted(r["witness_rank_lam0_multi"][0] / r["witness_rank_lam0_multi"][1] for r in rows)[len(rows) // 2],
                                               "partition_mix": collections.Counter(str(r["variants"]["lam0_multi"]["partition"]) for r in rows)}}
    (OUT / f"p1_panel_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({t: o["summary"] for t, o in out.items()}, default=str))


def quarantine():
    """DIAGNOSTIC_ONLY: copy the write-protected A2 outcomes, record hashes and coverage, tabulate per arm (no formal use)."""
    Q = K.O / "QUARANTINE_unauthorized"; D = OUT / "p1_quarantine_DIAGNOSTIC_ONLY"; D.mkdir(parents=True, exist_ok=True)
    for f in ("phys_34_3d.jsonl", "regr_phys.jsonl"):
        (D / f).unlink(missing_ok=True); shutil.copyfile(Q / f, D / f)
    h = {f: hashlib.sha256((D / f).read_bytes()).hexdigest()[:16] for f in ("phys_34_3d.jsonl", "regr_phys.jsonl")}
    R = {json.loads(l)["key"]: json.loads(l) for l in open(D / "phys_34_3d.jsonl")}
    sel = json.loads((K.O / "r34" / "selection_34_3d.json").read_text())
    per = collections.defaultdict(dict)
    for s in sel:
        if s["status"] == "QUEUED":
            r = R.get(s["job"])
            if r is None:
                per[s["key"][0]][s["arm"]] = "NOT_RUN"
            else:
                x, y = (r.get("X") or {}).get("x"), (r.get("Y") or {}).get("y")
                ok = x == 1 and y == 1 and (r.get("REPLAY") or {}).get("replay") == 1
                per[s["key"][0]][s["arm"]] = {"succ": ok, "x": x, "y": y, "phase": (r.get("X") or {}).get("phase")}
        elif s["status"] == "REUSED":
            per[s["key"][0]][s["arm"]] = {"succ": s["x"] == 1 and s["y"] == 1 and s.get("replay", 1) == 1, "archived": True}
    cov = collections.Counter(f'{a}:{"NOT_RUN" if v == "NOT_RUN" else ("succ" if v["succ"] else "fail")}' for r in per.values() for a, v in r.items())
    RG = [json.loads(l) for l in open(D / "regr_phys.jsonl")]
    out = {"label": "DIAGNOSTIC_ONLY (A2 unauthorized runs; no gate, no recovery estimate, no regression claim, no training / selection use)",
           "copies_sha16": h, "r34_coverage": dict(cov), "r34_per_root": per, "regr_jobs_completed": len(RG), "regr_jobs_sealed": 60,
           "regr_outcomes": collections.Counter(f"x{(r.get('X') or {}).get('x')}_y{(r.get('Y') or {}).get('y')}" for r in RG)}
    (OUT / "p1_quarantine.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "r34_per_root"}, default=str))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    a = sys.argv[1]
    if a == "arch2d":
        arch2d()
    elif a == "panels":
        panel("2d", ["F0"]); panel("3d", ["F0", "G1s_s0", "M1s_s0"])
    elif a == "quarantine":
        quarantine()
