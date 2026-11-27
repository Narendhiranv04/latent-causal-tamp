#!/usr/bin/env python3
"""R5.0 evidence audit (read-only; historical artefacts never rewritten).
    python r5audit.py seals            every *.SEAL under O/kgt3 (KGT3 + R4): sealed sha == file sha, job count / keys where applicable
    python r5audit.py recount          R4 headline numbers recomputed from RAW records with logic independent of the R4 analysis code
    python r5audit.py inventory        local X supervision inventory (KGT3 P2 + R4.3 + R4.4): roots, parent families, g / h, classes,
                                       label provenance, matched groups, exposure status -> O/kgt3/r5/inventory.json"""
from __future__ import annotations

import collections, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import common3 as K  # noqa: E402
O = K.C.FIG3 / "kgt3"
R5 = O / "r5"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p)]


def seals():
    out = []
    for s in sorted(O.rglob("*.SEAL")):
        f = Path(str(s)[:-5])
        txt = s.read_text().strip()
        try:
            rec = json.loads(txt); want = rec["sha256"]
        except (json.JSONDecodeError, TypeError):
            rec, want = None, txt
        ok = f.exists() and sha(f) == want
        n = None
        if rec and f.suffix == ".json":
            J = json.loads(f.read_text()); J = J if isinstance(J, list) else [x for v in J.values() for x in v]
            n = len(J) == rec.get("n_jobs")
        out.append({"file": str(f.relative_to(O)), "sha_ok": ok, "n_ok": n})
    bad = [o for o in out if not o["sha_ok"] or o["n_ok"] is False]
    print(json.dumps({"n": len(out), "bad": bad}, indent=1))
    return {"n": len(out), "bad": bad, "all": out}


def _succ3(r):
    return (r.get("X") or {}).get("x") == 1 and (r.get("Y") or {}).get("y") == 1 and (r.get("REPLAY") or {}).get("replay") == 1


def recount():
    res = {}
    # R4.2: plans -> per (root, arm) the job key (QUEUED / SAME_AS / REUSED by exact key) -> success, independent of order_phys.analyze
    od = O / "r4" / "order3d"
    sel = json.loads((od / "selection.json").read_text()); R = {r["key"]: r for r in jl(od / "phys.jsonl")}
    import order_phys as OP
    A = {v["src"]: v["rec"] for v in OP.archive().values()}
    key2rec = {s["job"]: (A[s["src"]] if s["status"] == "REUSED" else R[s["job"]]) for s in sel if s["status"] in ("QUEUED", "REUSED")}
    by = {}
    for s in sel:
        if s["study"] != "main":
            continue
        r = key2rec[s["job"] if s["status"] != "SAME_AS" else s["same_as"]]
        by.setdefault(s["arm"], []).append((s["root_id"], _succ3(r)))
    res["R4.2_success"] = {a: sum(x for _, x in v) for a, v in by.items()}
    res["R4.2_roots"] = {a: len({r for r, _ in v}) for a, v in by.items()}
    # R4.5 3D
    sm = O / "r4" / "smoke"
    sel = json.loads((sm / "selection_3d.json").read_text()); R = {r["key"]: r for r in jl(sm / "phys_3d.jsonl")}
    import smoke as SM
    A = {v["src"]: v["rec"] for v in SM.archive("3d").values()}
    cnt, lng = collections.Counter(), collections.Counter()
    for s in sel:
        if s["status"] == "NO_REPAIR":
            continue
        r = A[s["src"]] if s["status"] == "REUSED" else R[s["job"]]
        if _succ3(r):
            cnt[s["arm"]] += 1; lng[s["arm"]] += len(s["seq"]) > 3
    res["R4.5_3d_success"], res["R4.5_3d_long"] = dict(cnt), dict(lng)
    res["R4.5_3d_roots"] = len({s["root_id"] for s in sel})
    # R4.3 / R4.4 query outcome counts
    q = jl(O / "r4" / "b2d" / "queries.jsonl")
    res["R4.3_queries"] = len(q); res["R4.3_outcomes"] = dict(collections.Counter(x["outcome"] for x in q))
    f = jl(O / "r4" / "b2d" / "families.jsonl")
    res["R4.3_levels"] = dict(collections.Counter((x.get("family") or {}).get("level") for x in f))
    d = jl(O / "r4" / "d3d" / "phys.jsonl")
    res["R4.4_jobs"] = len(d); res["R4.4_X_success_replayed"] = sum(_succ3({**r, "Y": {"y": 1}}) for r in d if r.get("X"))
    res["R4.4_censored_error"] = sum(bool(r.get("censored") or r.get("error")) for r in d)
    print(json.dumps(res, indent=1))
    return res


def inventory():
    """Local supervision available for X development (labels <= 3 actions per chunk)."""
    import guard as GD
    out = {}
    # KGT3 P2 labels (strict + historical), splits are KGT3 family splits; P2 3D GATE was opened once (exposed)
    for dom in ("2d", "3d"):
        L = jl(O / f"labels_p2_{dom}.jsonl")
        out[f"KGT3_P2_{dom}"] = {"labels": len(L), "families": len({e["fam"] for e in L}),
                                 "by_split": dict(collections.Counter(e["split"] for e in L)),
                                 "by_h_g_label": dict(collections.Counter(f"h{min(e['h'], 2)}|g{e['m']}|y{e['label']}" for e in L)),
                                 "exposure": "TRAIN/SELECT used for KGT3 training/selection; 3D GATE opened once (R4 strict audit); 2D GATE never read"}
    # R4.3 2D construction (development; disclosed exposure: R4 analyses only, no model trained)
    q = [x for x in jl(O / "r4" / "b2d" / "queries.jsonl") if x["kind"] in ("X", "PROBE")]
    lab = collections.Counter()
    for x in q:
        b = [0] + x["bounds"]; ph = str(x.get("phase") or "")
        fail = int(ph.split(":")[1]) if ph.startswith("relocation") else None
        for s, e in zip(b[:-1], b[1:]):
            if x["outcome"] == "SUCCESS":
                lab[f"h{min(s, 2)}|g{e - s}|pos_replayed"] += 1
            elif fail is not None and fail >= e:
                lab[f"h{min(s, 2)}|g{e - s}|pos_prefix_unreplayed"] += 1
            elif fail is not None and s <= fail < e and x["outcome"] == "CERTIFIED_INFEASIBLE":
                lab[f"h{min(s, 2)}|g{e - s}|neg_certified"] += 1; break
            else:
                lab[f"h{min(s, 2)}|g{e - s}|unresolved"] += 1; break
    out["R4.3_2d"] = {"families": len({x["fid"] for x in q}), "runs": len(q), "chunk_labels": dict(sorted(lab.items())),
                      "exposure": "development construction; frozen F0 ranked once (R4.3); no training"}
    # R4.4 3D construction
    J = {j["key"]: j for j in json.loads((O / "r4" / "d3d" / "jobs.json").read_text())}
    R = {r["key"]: r for r in jl(O / "r4" / "d3d" / "phys.jsonl")}
    lab = collections.Counter()
    for k, j in J.items():
        if j["kind"] != "X_CHUNKED":
            continue
        r = R[k]; oc = GD.outcome(r, "X"); X = r.get("X") or {}
        rep = (r.get("REPLAY") or {}).get("replay") == 1
        b = [0] + j["bounds"]; ph = str(X.get("phase") or "")
        fail = int(ph.split(":")[1]) if ph.startswith("relocation") else (int(ph.split(":")[1]) - 1 if ph.startswith("boundary") else None)
        for s, e in zip(b[:-1], b[1:]):
            if oc == "SUCCESS" and rep:
                lab[f"h{min(s, 2)}|g{e - s}|pos_replayed"] += 1
            elif fail is not None and fail >= e:
                lab[f"h{min(s, 2)}|g{e - s}|pos_prefix_unreplayed"] += 1
            elif fail is not None and s <= fail < e and oc == "CERTIFIED_INFEASIBLE":
                lab[f"h{min(s, 2)}|g{e - s}|neg_certified"] += 1; break
            else:
                lab[f"h{min(s, 2)}|g{e - s}|{oc.lower()}"] += 1; break
    rows = jl(O / "r4" / "d3d" / "rows.jsonl")
    out["R4.4_3d"] = {"families": len(rows), "parent_families": len({r["parent_family_id"] for r in rows}), "chunk_labels": dict(sorted(lab.items())),
                      "exposure": "development construction; frozen F0/M1s/G1s/O2 ranked once (R4.4 rank_models); no training"}
    # R3.1 TRAIN_SCALE and original snapshot local X labels used by M1s/G1s (provenance only)
    out["note"] = ("Every root of the R4.2/R4.5 3D panel (20) and the 2D coh2d panel (30) is a permanent development root: never a final confirmation root. "
                   "R4.3/R4.4 families may become DEVELOPMENT TRAINING only after explicit designation and removal from all selection evidence.")
    R5.mkdir(parents=True, exist_ok=True)
    (R5 / "inventory.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    {"seals": seals, "recount": recount, "inventory": inventory}[sys.argv[1]]()
