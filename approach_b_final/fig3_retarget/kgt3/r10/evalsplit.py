#!/usr/bin/env python3
"""R10.9 canonical short-horizon roster union 'r10u' per domain = TEST_SHORT (canonical original TEST scenes) + BENCH_SHORT (V3.4), one row per
canonical scene, source track tagged in the PRIVATE index only.  Evaluator process; prints counts only (no TEST label is displayed).
    $PYG evalsplit.py RELEASE_DIR K3EVAL_DIR      -> K3EVAL_DIR/runs/public/{public,private}_r10u_{dom}.jsonl + ROSTER_r10u.json"""
import hashlib, json, sys
from pathlib import Path

NW = Path("/home/projects/long-horizon/naren_workspace")
SRC = {"TEST": NW / "k3abl/runs/public", "BENCH": NW / "fig3/final/r8a_verify/k3/runs/public"}
PUBK = ("domain", "root_id", "inputs")


def jl(p):
    return [json.loads(l) for l in open(p)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(rel, k3):
    rel, out = Path(rel), Path(k3) / "runs/public"
    out.mkdir(parents=True, exist_ok=True)
    man = {"roster": "r10u", "release_seal": json.loads((rel / "R10_DATASET_SEAL.json").read_text())["release_sha256"], "domains": {}}
    for dom in ("2d", "3d"):
        pub, prv = [], []
        for track, split, src in (("TEST_SHORT", f"test_short_{dom}", ("TEST", "test")), ("BENCH_SHORT", f"bench_short_{dom}", ("BENCH", "v34"))):
            P = {r["root_id"]: r for r in jl(SRC[src[0]] / f"public_{src[1]}_{dom}.jsonl")}
            Q = {r["root_id"]: r for r in jl(SRC[src[0]] / f"private_{src[1]}_{dom}.jsonl")}
            for c in jl(rel / "splits" / f"{split}.jsonl"):
                rid = c["canonical_root_id"]
                p, q = P[rid], dict(Q[rid])
                path = Path(q["path"])
                if not path.is_absolute():
                    path = next(x for x in (SRC[src[0]] / path, SRC[src[0]].parent.parent.parent / path, NW / "fig3/final/r8a_verify" / path) if x.exists())
                assert path.exists(), rid
                q.update(path=str(path), r10_track=track, r10_scene_id=c["scene_id"], r10_family=c["family_id"], r10_template=c["template_id"],
                         r10_aliases=c["aliases"], root_sha256_r10=sha(path))
                pub.append({k: p[k] for k in PUBK if k in p} | {"domain": dom})
                prv.append(q)
        ids = [r["root_id"] for r in pub]
        assert len(ids) == len(set(ids))
        for name, rows in (("public", pub), ("private", prv)):
            f = out / f"{name}_r10u_{dom}.jsonl"
            f.write_text("".join(json.dumps(r) + "\n" for r in rows))
        man["domains"][dom] = {"n": len(pub), "by_track": {t: sum(1 for q in prv if q["r10_track"] == t) for t in ("TEST_SHORT", "BENCH_SHORT")},
                               "public_sha256": sha(out / f"public_r10u_{dom}.jsonl"), "private_sha256": sha(out / f"private_r10u_{dom}.jsonl")}
    (Path(k3) / "ROSTER_r10u.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(man, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
