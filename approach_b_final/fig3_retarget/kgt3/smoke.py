#!/usr/bin/env python3
"""R4.5 end-to-end development smoke test (R4_PREREG R4_5 + addendum).  Planners receive only public rows (no assignment, order, object
identities or K); each arm's ONE committed plan per root comes from p4run.py (model-only, common planners.CFG budget), sealed before any job.
Arms: FLAT-INSERT (flat-search control), REC-ORDERED (Fig. 3A), GA (Fig. 3B EXACT / BOUNDED), B0 (production K <= 3 reference).
Physical: X_CHUNKED + endpoint Y (t0, goal) + independent replay; success = all three.  NOOP / ABSTAIN = no repair (every DEV root needs one).
    python smoke.py jobs DOM PLANS.jsonl CAP   -> O/kgt3/r4/smoke/{plans_DOM.jsonl (copy) + SEAL, jobs_DOM.json + SEAL, selection_DOM.json}
    python smoke.py analyze DOM                -> R4_5_DOM.json"""
from __future__ import annotations

import collections, hashlib, json, shutil, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
import guard as GD  # noqa: E402
OS = K.C.FIG3 / "kgt3" / "r4" / "smoke"
ARMS = ("FLAT-INSERT", "REC-ORDERED", "GA", "B0")


def bounds(part):
    s, out = 0, []
    for g in part:
        s += g; out.append(s)
    return out


def plans_of(rec):
    out = {}
    for arm in ARMS[:3]:
        a = rec["arms"][arm]
        out[arm] = {"decision": a["decision"], "seq": a["seq"], "partition": a["partition"], "wall_s": a["wall_s"], "mode": a["mode"], "kind": a["kind"]}
    b = rec["B0"]
    out["B0"] = {"decision": b["decision"], "seq": b["seq"], "partition": [len(b["seq"])] if b["seq"] else None, "wall_s": None, "mode": "B0", "kind": "production"}
    return out


def archive(dom):
    import jobs24 as J24
    import order_phys as OP
    import p3 as P3
    A = {}
    if dom == "3d":
        for k, v in OP.archive().items():
            A[k] = {"rec": v["rec"], "src": v["src"]}
        sel = json.loads((OP.OD / "selection.json").read_text())
        R = {json.loads(l)["key"]: json.loads(l) for l in open(OP.OD / "phys.jsonl")}
        pan = {rid: row for rid, row, *_ in P3.panel("3d")}
        for s in sel:
            if s["status"] == "QUEUED":
                ids = pan[s["root_id"]]["inputs"]["ids"]
                A.setdefault((s["root_id"], J24.nk(J24.names("3d", ids, s["order"])), J24.nk(bounds(s["partition"]))), {"rec": R[s["job"]], "src": "R4.2:" + s["job"]})
    return A


def jobs(dom, plans_path, cap):
    import jobs24 as J24
    import p3 as P3
    OS.mkdir(parents=True, exist_ok=True)
    pp = OS / f"plans_{dom}.jsonl"; shutil.copyfile(plans_path, pp); (OS / f"plans_{dom}.jsonl.SEAL").write_text(GD.sha(pp))
    P = {json.loads(l)["root_id"]: json.loads(l) for l in open(pp)}
    pan = {rid: (row, meta) for rid, row, _, _, meta in P3.panel(dom)}
    A = archive(dom)
    seen, jb, sel = {}, [], []
    for rid in sorted(P, key=lambda r: hashlib.sha256(f"R4.5|{r}".encode()).hexdigest()):
        row, meta = pan[rid]; ids = row["inputs"]["ids"]
        for arm, p in plans_of(P[rid]).items():
            base = {"root_id": rid, "arm": arm, **p}
            if p["decision"] != "REPAIR" or not p["seq"]:
                sel.append({**base, "status": "NO_REPAIR"}); continue
            b = bounds(p["partition"])
            k = (rid, json.dumps(p["seq"]), json.dumps(b)) if dom == "2d" else (rid, J24.nk(J24.names("3d", ids, p["seq"])), J24.nk(b))
            key = f"R4.5|{dom}|{rid}|{json.dumps(p['seq'])}|{json.dumps(b)}"
            if k in seen:
                sel.append({**base, "status": "SAME_AS", "job": seen[k]}); continue
            seen[k] = key
            if k in A:
                sel.append({**base, "status": "REUSED", "job": key, "src": A[k]["src"]}); continue
            if len(jb) + 1 > int(cap):
                sel.append({**base, "status": "NOT_RUN_BUDGET", "job": key}); continue
            if dom == "2d":
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "geom": "original", "kind": "X_CHUNKED", "seq": [[ids[o], int(d)] for o, d in p["seq"]],
                           "seq_idx": p["seq"], "bounds": b, "y_endpoint": True})
            else:
                jb.append({"key": key, "root_id": rid, "arm": arm, "path": meta["path"], "kind": "X_CHUNKED", "order": J24.names("3d", ids, p["seq"]), "bounds": b,
                           "y": {"target": "t0", "goal": meta["goal"]}})
            sel.append({**base, "status": "QUEUED", "job": key})
    jf = OS / f"jobs_{dom}.json"; jf.write_text(json.dumps(jb, indent=1))
    sf = OS / f"selection_{dom}.json"; sf.write_text(json.dumps(sel, indent=1))
    GD.seal(jf); (OS / f"selection_{dom}.json.SEAL").write_text(GD.sha(sf))
    print(json.dumps({"queued": len(jb), "by": collections.Counter(f"{s['arm']}:{s['status']}" for s in sel)}))


def res(dom, r):
    X, Y = r.get("X") or {}, r.get("Y") or {}
    rep = (r.get("REPLAY") or {}).get("replay") == 1 if dom == "3d" else bool(X.get("independent_replay"))
    ph = str(X.get("phase") or X.get("failed_phase") or "")
    return {"x": X.get("x"), "y": Y.get("y"), "replay": rep, "succ": bool(X.get("x") == 1 and Y.get("y") == 1 and rep), "x_outcome": GD.outcome(r, "X"),
            "y_outcome": GD.outcome(r, "Y") if r.get("Y") else None, "phase": ph or None, "cpu_s": r.get("cpu_s"), "wall_s": r.get("wall_s")}


def analyze(dom):
    import p3 as P3
    jf, rf = OS / f"jobs_{dom}.json", OS / f"phys_{dom}.jsonl"
    c = GD.complete(jf, rf)
    if c["status"] != "COMPLETE":
        raise SystemExit(f"INCOMPLETE {c}")
    R = {json.loads(l)["key"]: json.loads(l) for l in open(rf)}
    A = archive(dom)
    bysrc = {v["src"]: v["rec"] for v in A.values()}
    sel = json.loads((OS / f"selection_{dom}.json").read_text())
    W = {rid: sorted(tuple(map(int, a)) for a in Wo) for rid, _, _, Wo, _ in P3.panel(dom)}
    per = collections.defaultdict(dict)
    for s in sel:
        if s["status"] in ("QUEUED", "SAME_AS") and s["job"] in R:
            v = {**res(dom, R[s["job"]]), "src": "NEW"}
        elif s["status"] == "SAME_AS":
            first = next(x for x in sel if x.get("job") == s["job"] and x["status"] in ("QUEUED", "REUSED"))
            v = {**res(dom, R[first["job"]] if first["status"] == "QUEUED" else bysrc[first["src"]]), "src": "SAME_AS"}
        elif s["status"] == "REUSED":
            v = {**res(dom, bysrc[s["src"]]), "src": s["src"]}
        else:
            v = {"succ": False, "x": None, "y": None, "x_outcome": s["status"], "src": s["status"]}
        seq = [tuple(map(int, a)) for a in (s.get("seq") or [])]
        v.update(arm=s["arm"], length=len(seq), partition=s.get("partition"), plan_wall_s=s.get("wall_s"), mode=s.get("mode"),
                 witness_action_recall=len(set(seq) & set(W[s["root_id"]])) / len(W[s["root_id"]]), witness_set=sorted(seq) == W[s["root_id"]])
        per[s["root_id"]][s["arm"]] = v
    roots = sorted(per)
    summ = {}
    for arm in ARMS:
        rr = [per[r][arm] for r in roots]
        summ[arm] = {"repair_decisions": sum(x["length"] > 0 for x in rr), "x": sum(x.get("x") == 1 for x in rr), "y": sum(x.get("y") == 1 for x in rr),
                     "succ": sum(x["succ"] for x in rr), "long_succ": sum(x["succ"] and x["length"] > 3 for x in rr),
                     "length_hist": dict(collections.Counter(x["length"] for x in rr)), "x_outcomes": dict(collections.Counter(x["x_outcome"] for x in rr)),
                     "witness_action_recall_mean": statistics.mean(x["witness_action_recall"] for x in rr), "witness_set": sum(x["witness_set"] for x in rr),
                     "plan_wall_median": statistics.median([x["plan_wall_s"] for x in rr if x.get("plan_wall_s") is not None]) if arm != "B0" else None,
                     "verify_wall_median": statistics.median([x["wall_s"] for x in rr if x.get("wall_s")]) if any(x.get("wall_s") for x in rr) else None,
                     "new": sum(x["src"] == "NEW" for x in rr), "reused": sum(str(x["src"]).startswith("R") for x in rr)}
    out = {"domain": dom, "n_roots": len(roots), "summary": summ, "per_root": per, "completion": c, "cpu_h_new": sum(r.get("cpu_s", 0) for r in R.values()) / 3600,
           "label": "R4.5 DEVELOPMENT smoke (exposed roots; planners never see assignment / order / K)"}
    (OS / f"R4_5_{dom}.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k != "per_root"}, default=str)[:3500])


if __name__ == "__main__":
    a = sys.argv[1]
    {"jobs": lambda: jobs(*sys.argv[2:5]), "analyze": lambda: analyze(sys.argv[2])}[a]()
