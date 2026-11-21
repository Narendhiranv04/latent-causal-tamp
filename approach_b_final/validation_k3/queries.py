#!/usr/bin/env python3
"""Fixed physical query list for P1-P4 (PREREG_P1_P4): the argmax repair of every multipass score variant on every eval_task root, minus the
copied verifier cache.  Writes the benchmark.need job format and a hash manifest BEFORE any teacher call; then teaches with the unchanged
benchmark.teach into $K3V/runs/verifier_cache (a copy of the ablation cache; the original is never written).
    python queries.py list SPLIT DOM            -> $K3V/runs/out/queries/{jobs_SPLIT_DOM.jsonl, QUERY_LIST_SPLIT_DOM.json}
    python queries.py teach SPLIT DOM WORKERS   (refuses unless the query list hash matches)"""
import collections, json, os, subprocess, sys, time
from pathlib import Path

import vk

Q = vk.OUT / "queries"
CACHE = vk.K3V / "runs/verifier_cache"


def mp(split, dom):
    out = {}
    for p in sorted((vk.OUT / "multipass").glob(f"{split}_{dom}*.jsonl")):
        for r in vk.jl(p):
            out[r["root_id"]] = r
    return out


def listq(split, dom):
    import benchmark as BM
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_{split}_{dom}.jsonl")}
    M = mp(split, dom)
    assert set(M) == set(priv), (len(M), len(priv))
    have = BM.cache_labels(CACHE, dom)[0]
    jobs, n_all, n_have = collections.defaultdict(set), 0, 0
    for rid, r in M.items():
        e = priv[rid]
        if not e["masks"].get("eval_task"):
            continue
        for vn, v in r["variants"].items():
            n_all += 1
            k = (rid, json.dumps(v["seq"]))
            if None not in have.get(k, (None, None)):
                n_have += 1; continue
            jobs[rid].add(json.dumps([[e["ids"][o], c] for o, c in v["seq"]]))
    base = vk.K3A / "runs/public"
    Q.mkdir(parents=True, exist_ok=True)
    fo = Q / f"jobs_{split}_{dom}.jsonl"
    with open(fo, "w") as f:
        for rid in sorted(jobs):
            e = priv[rid]
            f.write(json.dumps({"root_id": rid, "dom": dom.upper(), "path": str((base / e["path"]).resolve()), "geom": e.get("geom", "original"),
                                "seqs": [json.loads(s) for s in sorted(jobs[rid])], "ids": e["ids"]}) + "\n")
    man = {"split": split, "dom": dom, "variant_root_pairs": n_all, "already_labeled": n_have, "new_roots": len(jobs),
           "new_queries": sum(len(v) for v in jobs.values()), "jobs_sha256": vk.sha(fo),
           "multipass_sha256": {p.name: vk.sha(p) for p in sorted((vk.OUT / "multipass").glob(f"{split}_{dom}*.jsonl"))},
           "cache_sha256_before": {p.name: vk.sha(p) for p in sorted(CACHE.glob(f"verify_{dom}*.jsonl"))}, "utc": time.strftime("%FT%TZ", time.gmtime())}
    man_p = Q / f"QUERY_LIST_{split}_{dom}.json"
    assert not man_p.exists(), "query list already registered (never overwritten)"
    vk.wjson(man_p, man)
    print(json.dumps(man, indent=1))


def teach(split, dom, W):
    man = json.loads((Q / f"QUERY_LIST_{split}_{dom}.json").read_text())
    fo = Q / f"jobs_{split}_{dom}.jsonl"
    assert vk.sha(fo) == man["jobs_sha256"], "query list changed after registration"
    py = os.environ["PY2D" if dom == "2d" else "PY3D"]
    C0 = int(os.environ.get("TEACH_CPU0", 4))
    assert 4 <= C0 and C0 + W - 1 <= 42, "CPUs 0-3 and 43-47 stay free"
    t0 = time.time()
    subprocess.run(["taskset", "-c", f"{C0}-{C0 + W - 1}", py, str(vk.HERE.parent / "benchmark.py"), "teach", dom, str(fo), str(CACHE), str(W), str(C0)], check=True,
                   env={**os.environ, "V3OUT": str(vk.K3V / "runs/teach_out")})
    with open(Q / f"TEACH_LOG_{dom}.jsonl", "a") as f:
        f.write(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "split": split, "queries": man["new_queries"], "workers": W, "wall_s": round(time.time() - t0, 1)}) + "\n")



def listb(dom):
    """E5 budget diagnostic (VAL): argmax repairs of budget.py for every eval_task root, minus the cache; registered before teaching."""
    import benchmark as BM
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_val_{dom}.jsonl")}
    M = {r["root_id"]: r for p in sorted((vk.OUT / "budget").glob(f"val_{dom}*.jsonl")) for r in vk.jl(p)}
    assert set(M) == set(priv)
    have = BM.cache_labels(CACHE, dom)[0]
    jobs = collections.defaultdict(set)
    for rid, r in M.items():
        if priv[rid]["masks"].get("eval_task"):
            for v in r["B"].values():
                if None in have.get((rid, json.dumps(v["seq"])), (None, None)):
                    jobs[rid].add(json.dumps([[priv[rid]["ids"][o], c] for o, c in v["seq"]]))
    fo = Q / f"jobs_budget_val_{dom}.jsonl"
    with open(fo, "w") as f:
        for rid in sorted(jobs):
            e = priv[rid]
            f.write(json.dumps({"root_id": rid, "dom": dom.upper(), "path": str((vk.K3A / "runs/public" / e["path"]).resolve()), "geom": e.get("geom", "original"),
                                "seqs": [json.loads(s) for s in sorted(jobs[rid])], "ids": e["ids"]}) + "\n")
    mp_ = Q / f"QUERY_LIST_budget_val_{dom}.json"
    assert not mp_.exists()
    vk.wjson(mp_, {"dom": dom, "new_roots": len(jobs), "new_queries": sum(len(v) for v in jobs.values()), "jobs_sha256": vk.sha(fo),
                   "budget_sha256": {p.name: vk.sha(p) for p in sorted((vk.OUT / "budget").glob(f"val_{dom}*.jsonl"))}, "utc": time.strftime("%FT%TZ", time.gmtime())})
    print(json.loads(mp_.read_text()))


def teachb(dom, W):
    man = json.loads((Q / f"QUERY_LIST_budget_val_{dom}.json").read_text())
    fo = Q / f"jobs_budget_val_{dom}.jsonl"
    assert vk.sha(fo) == man["jobs_sha256"]
    C0 = int(os.environ.get("TEACH_CPU0", 4))
    assert 4 <= C0 and C0 + W - 1 <= 42
    subprocess.run(["taskset", "-c", f"{C0}-{C0 + W - 1}", os.environ["PY2D" if dom == "2d" else "PY3D"], str(vk.HERE.parent / "benchmark.py"), "teach", dom, str(fo), str(CACHE), str(W), str(C0)],
                   check=True, env={**os.environ, "V3OUT": str(vk.K3V / "runs/teach_out")})


if __name__ == "__main__":
    a = sys.argv[1:]
    {"list": lambda: listq(a[1], a[2]), "teach": lambda: teach(a[1], a[2], int(a[3])), "listb": lambda: listb(a[1]), "teachb": lambda: teachb(a[1], int(a[2]))}[a[0]]()
