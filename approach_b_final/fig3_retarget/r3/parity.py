#!/usr/bin/env python3
"""R3.0 teacher-contract audit jobs (presealed; evaluator side).  All selections are deterministic (sha256 order) over archived labels.
3D (<= 40 jobs):
  DET   identical re-run of archived chunked runs (X only) -> same x and failing phase (determinism, mode / seed signature)
  HYP   h >= 1 chunk labelled on a PHYSICALLY reached prefix, re-run from a HYPOTHETICAL static start (cells0 = ideal prefix cells, q_ref)
        -> does the ideal-pose canonical scene reproduce the physical label?
  DER   derived continuous-prefix negatives run directly (same start, continuous, bounds {k}) -> must fail at the same relocation
  TRN   original v32 VAL X labels (continuous S0 runs; non-exposed families) re-run through run_xb(bounds {m}) -> training-label contract parity
2D (<= 40 queries): DET on decided + UNKNOWN R2.4 / R2.3 chunked runs (X only); x_query == x_chunked({m}) parity reused from R1 (3/3).
    python parity.py build DOM     -> O/parity_jobs_DOM.json (+ .SEAL)
    python parity.py analyze DOM   -> O/parity_DOM.json"""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common3 as K  # noqa: E402
C, LB = K.C, K.LB
N3 = {"DET": 8, "HYP": 12, "DER": 6, "TRN": 8}
N2 = {"DET": 8}


def hk(*a):
    return hashlib.sha256(("R3.0|" + "|".join(map(str, a))).encode()).hexdigest()


def archive(dom):
    """[(job, result, tag)] decided or UNKNOWN archived chunked X runs (no errors / censoring)."""
    out = []
    for jf, rf, tag in list(LB.sources(dom)) + [(C.FIG3 / "r24" / f"jobs_24_{dom}.json", C.FIG3 / "r24" / f"phys_24_{dom}.jsonl", "R2.4")]:
        if not Path(jf).exists():
            continue
        J, R = LB._load(jf, rf)
        for j in J:
            r = R.get(j["key"])
            if r and not r.get("censored") and not r.get("error") and j.get("kind", "X_CHUNKED") == "X_CHUNKED" and (r.get("X") or {}).get("x") in (0, 1, None):
                out.append((j, r, tag))
    return out


def _cell(d):
    return [int(d) // 6, int(d) % 6]


def build3():
    A = archive("3d")
    rows = dict(C.snapshot_rows("3d"))
    for l in open(C.R2 / "r23" / "roster_3d.jsonl"):
        r = json.loads(l); rows[r["root_id"]] = r
    jobs = []
    # DET: multi-chunk archived runs, 4 failing after >= 1 chunk, 2 failing in chunk 0, 2 successes
    multi = sorted([(j, r, t) for j, r, t in A if len(j["bounds"]) >= 2 and not j.get("cells0") and r["X"].get("x") in (0, 1)], key=lambda e: hk("DET", e[0]["key"]))
    def fpos(e):
        ph = str(e[1]["X"].get("phase") or "")
        return int(ph.split(":")[1]) if ph.startswith("relocation:") else None
    pick = [e for e in multi if e[1]["X"]["x"] == 0 and fpos(e) is not None and fpos(e) >= e[0]["bounds"][0]][:4]
    pick += [e for e in multi if e[1]["X"]["x"] == 0 and fpos(e) is not None and fpos(e) < e[0]["bounds"][0]][:2]
    pick += [e for e in multi if e[1]["X"]["x"] == 1][:2]
    for j, r, t in pick:
        jobs.append({"key": f"R30|DET|{j['key']}", "audit": "DET", "ref": {"x": r["X"]["x"], "phase": r["X"].get("phase"), "src": t}, "root_id": LB.rid_of("3d", j),
                     "path": j["path"], "kind": "X_CHUNKED", "order": j["order"], "bounds": j["bounds"], "y": None})
    # HYP: h >= 1 labels from physically reached prefixes (no cells0 in the source run)
    L = [json.loads(l) for l in open(C.FIG3 / "r24" / "labels_3d.jsonl")]
    phys_keys = {j["key"]: j for j, r, t in A if not j.get("cells0")}
    H = sorted([e for e in L if e["t"] == "chunk" and e["h"] >= 1 and e["label"] in (0, 1) and e["key"] in phys_keys and e["kind"] in ("chunk_pos", "chunk_neg")],
               key=lambda e: hk("HYP", e["key"], json.dumps(e["prefix"]), json.dumps(e["chunk"])))
    for lab in (1, 0):
        for e in [e for e in H if e["label"] == lab][:N3["HYP"] // 2]:
            j = phys_keys[e["key"]]; ids = rows[e["root_id"]]["inputs"]["ids"]
            rec = json.loads(Path(j["path"]).read_text())
            cells0 = {k: list(v) for k, v in rec["initial_cells"].items()}
            for o, d in e["prefix"]:
                cells0[ids[o]] = _cell(d)
            jobs.append({"key": f"R30|HYP|{e['root_id']}|{json.dumps(e['prefix'])}|{json.dumps(e['chunk'])}", "audit": "HYP", "ref": {"x": lab, "src": e["src"], "h": e["h"]},
                         "root_id": e["root_id"], "path": j["path"], "kind": "X_CHUNKED", "cells0": cells0,
                         "order": [[ids[o], _cell(d)] for o, d in e["chunk"]], "bounds": [len(e["chunk"])], "y": None})
    # DER: derived continuous-prefix negatives, run directly from the same start
    D = sorted([e for e in L if e["t"] == "chunk" and e["kind"] == "continuous_prefix_neg" and e["label"] == 0 and e["key"] in phys_keys],
               key=lambda e: hk("DER", e["key"], json.dumps(e["chunk"])))
    seen = set()
    for e in D:
        if e["key"] in seen or len([x for x in jobs if x["audit"] == "DER"]) >= N3["DER"]:
            continue
        seen.add(e["key"])
        j = phys_keys[e["key"]]; ids = rows[e["root_id"]]["inputs"]["ids"]
        jobs.append({"key": f"R30|DER|{e['root_id']}|{json.dumps(e['chunk'])}", "audit": "DER", "ref": {"x": 0, "src_phase": None, "src": e["src"], "src_key": e["key"]},
                     "root_id": e["root_id"], "path": j["path"], "kind": "X_CHUNKED", "order": [[ids[o], _cell(d)] for o, d in e["prefix"] + e["chunk"]],
                     "bounds": [e["h"] + e["m"]], "y": None})
    # TRN: original v32 VAL labels on non-exposed families (m 2 / 3, 4 positive + 4 negative)
    lin = json.loads((K.O / "lineage_3d.json").read_text())
    diag = set(lin["diag_fams"])
    val = C.snapshot_rows("3d", splits=("val",), snap=C.SNAP_TRAIN)
    T = []
    for rid, r in val.items():
        if r["parent_family_id"] in diag:
            continue
        for q in r["labels"]["X"]:
            if len(q["seq"]) >= 2 and q["x"] in (0, 1):
                T.append((hk("TRN", rid, json.dumps(q["seq"])), rid, q))
    T.sort()
    used = set()
    for lab in (1, 0):
        n = 0
        for _, rid, q in T:
            if q["x"] != lab or rid in used or n >= N3["TRN"] // 2:
                continue
            path, _ = C.raw_path("3d", rid)
            if not path:
                continue
            used.add(rid); n += 1
            ids = val[rid]["inputs"]["ids"]
            jobs.append({"key": f"R30|TRN|{rid}|{json.dumps(q['seq'])}", "audit": "TRN", "ref": {"x": q["x"], "kind": q["kind"]}, "root_id": rid, "path": path,
                         "kind": "X_CHUNKED", "order": [[ids[int(o)], _cell(d)] for o, d in q["seq"]], "bounds": [len(q["seq"])], "y": None})
    return jobs


def build2():
    A = archive("2d")
    multi = sorted([(j, r, t) for j, r, t in A if t in ("R2.4", "R2.3")], key=lambda e: hk("DET2", e[0]["key"]))
    st = lambda e: str(e[1]["X"].get("teacher_status") or "")  # noqa: E731
    pick = [e for e in multi if st(e).startswith("UNKNOWN")][:3] + [e for e in multi if st(e) == "CERTIFIED_INFEASIBLE"][:2]
    pick += [e for e in multi if e[1]["X"].get("x") == 1][:3]
    return [{"key": f"R30|DET|{j['key']}", "audit": "DET", "ref": {"x": r["X"].get("x"), "status": st((j, r, t)), "phase": r["X"].get("failed_phase"), "src": t},
             "root_id": r.get("root_id"), "path": j["path"], "geom": j.get("geom", "original"), "kind": "X_CHUNKED", "seq": j["seq"], "bounds": j["bounds"]}
            for j, r, t in pick]


def build(dom):
    jobs = build3() if dom == "3d" else build2()
    cap = K.CEIL[dom]["R3.0"][0]
    assert len(jobs) <= cap, len(jobs)
    f = K.O / f"parity_jobs_{dom}.json"
    f.write_text(json.dumps(jobs, indent=1))
    (K.O / (f.name + ".SEAL")).write_text(K.sha(f))
    import collections
    print(json.dumps({"dom": dom, "n": len(jobs), "by": collections.Counter(j["audit"] for j in jobs), "seal": K.sha(f)[:16]}))


def analyze(dom):
    jobs = json.loads((K.O / f"parity_jobs_{dom}.json").read_text())
    R = {json.loads(l)["key"]: json.loads(l) for l in open(K.O / f"parity_res_{dom}.jsonl")}
    out, rows = {}, []
    for j in jobs:
        r = R.get(j["key"], {})
        X = r.get("X") or {}
        st = str(X.get("teacher_status") or X.get("status") or "")
        got = {"x": X.get("x"), "phase": X.get("phase") or X.get("failed_phase"), "status": st, "replay": (r.get("REPLAY") or {}).get("replay"),
               "censored": bool(r.get("censored")), "error": r.get("error"), "cpu_s": r.get("cpu_s")}
        agree = got["x"] == j["ref"]["x"] and (j["audit"] != "DET" or j["ref"].get("phase") in (None, got["phase"]))
        rows.append({"audit": j["audit"], "key": j["key"], "ref": j["ref"], "got": got, "agree": agree})
    for a in sorted({r["audit"] for r in rows}):
        rs = [r for r in rows if r["audit"] == a]
        out[a] = {"n": len(rs), "agree": sum(r["agree"] for r in rs), "decided": sum(r["got"]["x"] in (0, 1) for r in rs),
                  "disagreements": [{"key": r["key"], "ref": r["ref"], "got": r["got"]} for r in rs if not r["agree"]]}
    out["cpu_h"] = round(sum(r["got"]["cpu_s"] or 0 for r in rows) / 3600, 3)
    out["jobs"] = len(R)
    (K.O / f"parity_{dom}.json").write_text(json.dumps({"summary": out, "rows": rows}, indent=1))
    print(json.dumps({k: (v if not isinstance(v, dict) else {a: b for a, b in v.items() if a != "disagreements"} | {"n_dis": len(v["disagreements"])}) for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    {"build": build, "analyze": analyze}[sys.argv[1]](sys.argv[2])
