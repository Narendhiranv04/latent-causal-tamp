#!/usr/bin/env python3
"""Independent physical verification of SEALED ablation predictions with the unchanged finalized teachers (benchmark.py seal / queries / teach /
evaluate / summarize), deduplicated across arms: every distinct (root, ordered sequence) is taught at most once into one shared cache
($K3/runs/verifier_cache/verify_<dom>.jsonl, keyed by root + [[object index, cell]]; one teacher contract, sha-verified root files).
Only REPAIR decisions are queried (NOOP / ABSTAIN are scored by the frozen benchmark masks).  UNKNOWN stays UNKNOWN.  No retry, no fallback.
    python verify.py seal SPLIT DOM ARM...                 seal + validate (refuses to reseal)
    python verify.py teach SPLIT DOM WORKERS ARM...        union of missing queries -> one teach run (taskset 1..WORKERS, teacher env python)
    python verify.py evaluate SPLIT DOM ARM...             per-arm results + summaries (needs teach done)
SPLIT 'pilottrain' = the TRAIN part of the P2 pilot (predictions of split 'pilot' restricted to TRAIN roots)."""
import json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import benchmark as BM  # noqa: E402

K3 = Path(os.environ["K3"])
PUB, PRED, CACHE, VER = K3 / "runs/public", K3 / "runs/predictions", K3 / "runs/verifier_cache", K3 / "runs/verification"


def files(split, dom, arm):
    if split == "pilottrain":
        src = PRED / arm / f"pilot_{dom}.jsonl"
        train = {e["root_id"] for e in BM.jl(PUB / f"private_train_{dom}.jsonl")}
        dst = PRED / arm / f"pilottrain_{dom}.jsonl"
        if not dst.exists():
            dst.write_text("".join(l for l in open(src) if json.loads(l)["root_id"] in train))
        pub = PUB / f"public_pilottrain_{dom}.jsonl"
        if not pub.exists():
            pub.write_text("".join(l for l in open(PUB / f"public_pilot_{dom}.jsonl") if json.loads(l)["root_id"] in train))
        priv = PUB / f"private_pilottrain_{dom}.jsonl"
        if not priv.exists():
            priv.write_text("".join(l for l in open(PUB / f"private_pilot_{dom}.jsonl") if json.loads(l)["root_id"] in train))
        return dst, pub, priv
    return PRED / arm / f"{split}_{dom}.jsonl", PUB / f"public_{split}_{dom}.jsonl", PUB / f"private_{split}_{dom}.jsonl"


def main(cmd, split, dom, rest):
    CACHE.mkdir(parents=True, exist_ok=True); (VER / split).mkdir(parents=True, exist_ok=True)
    if cmd == "seal":
        for arm in rest:
            pred, pub, _ = files(split, dom, arm)
            _, c = BM.validate(pub, pred, quiet=True)
            assert c["MISSING"] == 0 and not any(k.startswith(("ILLEGAL", "UNKNOWN", "DUPLICATE", "BAD", "LENGTH", "IMMOVABLE", "OBJECT")) for k in c), (arm, dict(c))
            if not Path(str(pred) + ".SEAL.json").exists():
                BM.seal(pred, pub)
    elif cmd == "teach":
        W, arms = int(rest[0]), rest[1:]
        union = {}
        for arm in arms:
            pred, _, priv = files(split, dom, arm)
            out = VER / split / f"jobs_{arm}"
            BM.need(pred, priv, CACHE, out)
            p = Path(f"{out}_{dom}.jsonl")
            for j in BM.jl(p) if p.exists() else []:
                u = union.setdefault(j["root_id"], {**j, "seqs": []})
                for s in j["seqs"]:
                    if s not in u["seqs"]:
                        u["seqs"].append(s)
        uf = VER / split / f"jobs_union_{dom}.jsonl"
        with open(uf, "w") as f:
            for rid in sorted(union):
                f.write(json.dumps(union[rid]) + "\n")
        n = sum(len(u["seqs"]) for u in union.values())
        print(json.dumps({"split": split, "dom": dom, "arms": arms, "union_roots": len(union), "union_queries": n}), flush=True)
        if n:
            py = os.environ["PY2D" if dom == "2d" else "PY3D"]
            t0 = time.time()
            subprocess.run(["taskset", "-c", f"0-{W}", py, str(HERE.parent / "benchmark.py"), "teach", dom, str(uf), str(CACHE), str(W), "1"], check=True,
                           env={**os.environ, "V3OUT": str(K3 / "runs/teach_out")})
            with open(VER / split / f"TEACH_LOG_{dom}.jsonl", "a") as f:
                f.write(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "arms": arms, "queries": n, "workers": W, "wall_s": round(time.time() - t0, 1)}) + "\n")
    elif cmd == "evaluate":
        for arm in rest:
            pred, pub, priv = files(split, dom, arm)
            res = VER / split / f"results_{arm}_{dom}.jsonl"
            BM.evaluate(pub, pred, priv, CACHE, res)
            BM.summarize(priv, VER / split / f"SUMMARY_{arm}_{dom}.json", [res])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
