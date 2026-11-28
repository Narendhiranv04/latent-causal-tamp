#!/usr/bin/env python3
"""BENCH_COMP evaluation bookkeeping (gvlab2).  Planner outputs are merged and sealed from PUBLIC data only; the private index is read only by
`jobs` (evaluator), after the seal exists.
    $PYG evaljobs.py merge EVAL_DIR      -> EVAL_DIR/PLANS_EVAL.jsonl + .SEAL  (H3 / REC from r6 plans; GA@b, GA-MCTS-s{0,1,2}@b from anytime parts)
    $PY3D evaljobs.py jobs EVAL_DIR      -> jobs_eval.json (+ SEAL), selection_eval.json (+ SEAL): exact (root, ordered names, bounds) dedup across
                                            methods / budgets / seeds; reuse of sealed R8C records (r6.archive_r10, env R10_ARCHIVE_DIRS) when the
                                            scene path also matches.  env R10_PRIVATE (evaluator only), R10_PUBLIC."""
from __future__ import annotations

import collections, hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]
BUDGETS = (5, 10, 20, 30, 60, 180)
SEEDS = (0, 1, 2)


def jl(p):
    return [json.loads(l) for l in open(p)] if Path(p).exists() else []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def methods():
    return ["H3", "REC"] + [f"GA@{b}" for b in BUDGETS] + [f"GA-MCTS-s{s}@{b}" for s in SEEDS for b in BUDGETS]


def merge(ev):
    ev = Path(ev)
    import r6
    os.environ.setdefault("R10_PUBLIC", "/home/projects/long-horizon/naren_workspace/r10/comp/PUBLIC_bench_comp_3d.jsonl")
    order = [rid for rid, _ in r6.public_roots("r10comp")]
    P = {r["root_id"]: r for r in jl(ev / "r6" / "plans_r10comp.jsonl")}
    A = collections.defaultdict(dict)
    for f in sorted(ev.glob("any_s*.part*.jsonl")):
        for r in jl(f):
            lab = "GA" if r["arm"] == "GA" else f"GA-MCTS-s{r['seed']}"
            if lab in A[r["root_id"]]:
                raise SystemExit(f"duplicate trajectory {r['root_id']} {lab}")
            A[r["root_id"]][lab] = r
    out, miss = [], []
    for rid in order:
        m = {}
        for arm, lab in (("H3", "H3"), ("REC-ORDERED", "REC")):
            p = (P.get(rid) or {}).get("arms", {}).get(arm)
            if p is None:
                miss.append((rid, lab)); continue
            m[lab] = {"decision": p["decision"], "seq": p["seq"], "partition": p["partition"], "E": p.get("E"), "wall_s": p.get("wall_s")}
        for lab in ["GA"] + [f"GA-MCTS-s{s}" for s in SEEDS]:
            t = A[rid].get(lab)
            if t is None:
                miss.append((rid, lab)); continue
            for b in BUDGETS:
                v = t["budgets"][str(b)]
                m[f"{lab}@{b}"] = {k: v[k] for k in ("decision", "seq", "partition", "E", "kind", "overrun_s", "t_state")}
        out.append({"root_id": rid, "methods": m})
    if miss:
        raise SystemExit(f"missing {len(miss)}: {miss[:10]}")
    f = ev / "PLANS_EVAL.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in out))
    (ev / "PLANS_EVAL.jsonl.SEAL").write_text(sha(f))
    print("sealed", len(out), sha(f))


def jobs(ev):
    ev = Path(ev)
    import r6
    import jobs24 as J24
    f = ev / "PLANS_EVAL.jsonl"
    if sha(f) != (ev / "PLANS_EVAL.jsonl.SEAL").read_text().strip():
        raise SystemExit("plans not sealed")
    RT = {rid: (row, meta) for rid, row, meta in r6.roots("r10comp")}  # evaluator-side join (private index)
    Arc = r6.archive_r10()
    seen, jb, sel = {}, [], []
    for p in sorted(jl(f), key=lambda r: hashlib.sha256(f"MCTS|{r['root_id']}".encode()).hexdigest()):
        rid = p["root_id"]; row, meta = RT[rid]; ids = row["inputs"]["ids"]
        for lab in methods():
            m = p["methods"][lab]
            base = {"root_id": rid, "method": lab, "seq": m["seq"], "partition": m["partition"], "decision": m["decision"]}
            if m["decision"] != "REPAIR" or not m["seq"]:
                sel.append({**base, "status": "NO_REPAIR"}); continue
            b = r6.bounds(m["partition"])
            k = (rid, J24.nk(J24.names("3d", ids, m["seq"])), J24.nk(b))
            key = f"MCTS|r10comp|{rid}|{json.dumps(m['seq'])}|{json.dumps(b)}"
            if k in seen:
                sel.append({**base, "status": "SAME_AS", "job": seen[k]}); continue
            seen[k] = key
            if k in Arc and Arc[k]["path"] == meta["path"]:
                sel.append({**base, "status": "REUSED", "job": key, "src": Arc[k]["src"]}); continue
            jb.append({"key": key, "root_id": rid, "arm": lab, "path": meta["path"], "kind": "X_CHUNKED", "order": J24.names("3d", ids, m["seq"]), "bounds": b,
                       "y": {"target": "t0", "goal": meta["goal"]}})
            sel.append({**base, "status": "QUEUED", "job": key})
    jf, sf = ev / "jobs_eval.json", ev / "selection_eval.json"
    jf.write_text(json.dumps(jb, indent=1)); sf.write_text(json.dumps(sel, indent=1))
    (ev / "jobs_eval.json.SEAL").write_text(sha(jf)); (ev / "selection_eval.json.SEAL").write_text(sha(sf))
    print(json.dumps({"queued": len(jb), "reused": sum(s["status"] == "REUSED" for s in sel), "same_as": sum(s["status"] == "SAME_AS" for s in sel),
                      "no_repair": sum(s["status"] == "NO_REPAIR" for s in sel), "est_cpu_h": round(len(jb) * 4.8 / 449, 2)}))


if __name__ == "__main__":
    {"merge": lambda: merge(sys.argv[2]), "jobs": lambda: jobs(sys.argv[2])}[sys.argv[1]]()
