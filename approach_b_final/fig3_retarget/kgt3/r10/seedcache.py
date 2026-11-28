#!/usr/bin/env python3
"""Seed the R10 verifier cache from historical caches of the IDENTICAL teacher contract (exact root-file sha + ordered sequence keys only).
A (root, sequence) answered differently by two caches is dropped (re-taught, never voted).  Prints counts only.
    python3 seedcache.py OUT_DIR CACHE_DIR...      -> OUT_DIR/verify_{2d,3d}.jsonl + SEED_MANIFEST.json"""
import collections, hashlib, json, sys
from pathlib import Path
CONTRACT = "unchanged finalized teacher (evaluate._verify_job), V3.4 benchmark"


def main(out, srcs):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    man = {"contract": CONTRACT, "sources": {}, "domains": {}}
    for dom in ("2d", "3d"):
        roots = {}
        conf = collections.Counter()
        for s in srcs:
            f = Path(s) / f"verify_{dom}.jsonl"
            if not f.exists():
                continue
            man["sources"][str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
            for l in open(f):
                r = json.loads(l)
                assert r.get("teacher_provenance") == CONTRACT, (f, r.get("teacher_provenance"))
                rk = json.dumps(r["root"], sort_keys=True)
                cur = roots.setdefault(rk, {"root": r["root"], "results": {}, "cpu_s": 0.0, "teacher_provenance": CONTRACT, "_drop": set()})
                res = r["results"]
                items = res.items() if isinstance(res, dict) else [(json.dumps(x.get("seq", x.get("key")), sort_keys=True), x) for x in res]
                for k, v in items:
                    if k in cur["_drop"]:
                        continue
                    if k in cur["results"] and json.dumps(cur["results"][k], sort_keys=True) != json.dumps(v, sort_keys=True):
                        a, b = cur["results"][k], v
                        same_outcome = all((a.get(x) if isinstance(a, dict) else a) == (b.get(x) if isinstance(b, dict) else b) for x in ("x", "y", "outcome", "status", "success"))
                        if not same_outcome:
                            cur["_drop"].add(k); del cur["results"][k]; conf["conflict_dropped"] += 1; continue
                        conf["same_outcome_metadata_differs_kept_first"] += 1; continue
                    cur["results"][k] = v
                cur["cpu_s"] += float(r.get("cpu_s") or 0.0)
        with open(out / f"verify_{dom}.jsonl", "w") as f:
            for rk in sorted(roots):
                c = roots[rk]; c.pop("_drop")
                if c["results"]:
                    c["results"] = [c["results"][k] for k in sorted(c["results"])]      # cache format: list of {seq, x, y}
                    f.write(json.dumps(c) + "\n")
        man["domains"][dom] = {"roots": len(roots), "queries": sum(len(c["results"]) for c in roots.values()), **conf}
        man["domains"][dom]["output_sha256"] = hashlib.sha256((out / f"verify_{dom}.jsonl").read_bytes()).hexdigest()
    (out / "SEED_MANIFEST.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(man["domains"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
