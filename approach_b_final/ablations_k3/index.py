#!/usr/bin/env python3
"""Private evaluation indexes (benchmark.py format) and the P2 pilot split, from the ORIGINAL snapshot only.
Raw root paths are resolved on this host by file name under $ABF_ROOT/mirror and sha256-verified against the snapshot's root_sha256.
evaluation_group_id = layout_root_id (instance lineage: re-parked / hard-order children cluster with their parent layout).
    python index.py        -> $K3/runs/public/private_{train,val,test}_{dom}.jsonl, public_pilot_{dom}.jsonl (+ private_pilot), PILOT.json"""
import collections, hashlib, json, os
from pathlib import Path

K3, ABF = Path(os.environ["K3"]), Path(os.environ["ABF_ROOT"])
SNAP = ABF / "snapshot/abf_9de85710c2a7103f"
MIR = [ABF / "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/raw/roots",
       ABF / "mirror/boltzmann_lfd/final_dataset_generation", ABF / "mirror/rss3d_final_src"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    files = collections.defaultdict(list)
    for d in MIR:
        for p in d.rglob("*.json"):
            files[p.stem].append(p)
    out = K3 / "runs/public"
    pilot = {}
    for dom in ("2d", "3d"):
        rows = [json.loads(l) for l in open(SNAP / f"data{dom}.jsonl")]
        by = {s: [] for s in ("train", "val", "test")}
        miss = []
        for r in rows:
            p = next((q for q in files.get(r["root_id"], []) if sha(q) == r["root_sha256"]), None)
            if p is None:
                miss.append(r["root_id"]); continue
            geom = json.loads(p.read_text()).get("geometry_impl") or "original"
            by[r["split"]].append({"root_id": r["root_id"], "domain": dom, "K": r["K_legacy"], "masks": r["masks"], "path": str(p), "geom": geom,
                                   "ids": r["inputs"]["ids"], "evaluation_group_id": r["layout_root_id"], "source": r["source"]})
        assert not miss, f"{dom}: {len(miss)} roots without a sha-verified raw file, e.g. {miss[:3]}"
        for s, v in by.items():
            with open(out / f"private_{s}_{dom}.jsonl", "w") as f:
                for e in sorted(v, key=lambda e: e["root_id"]):
                    f.write(json.dumps(e, sort_keys=True) + "\n")
        # P2 pilot: 100 TRAIN (20 per K class) + 50 VAL (10 per K class), sha256('K3PILOT|' + root) order; never TEST
        pk = lambda e: hashlib.sha256(("K3PILOT|" + e["root_id"]).encode()).hexdigest()  # noqa: E731
        sel = []
        for s, n in (("train", 20), ("val", 10)):
            for K in ("0", "1", "2", "3", "NONE"):
                sel += sorted((e for e in by[s] if e["K"] == K), key=pk)[:n]
        ids = {e["root_id"] for e in sel}
        with open(out / f"private_pilot_{dom}.jsonl", "w") as f:
            for e in sorted(sel, key=lambda e: e["root_id"]):
                f.write(json.dumps(e, sort_keys=True) + "\n")
        with open(out / f"public_pilot_{dom}.jsonl", "w") as f:
            for r in sorted((r for r in rows if r["root_id"] in ids), key=lambda r: r["root_id"]):
                f.write(json.dumps({"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]}, sort_keys=True) + "\n")
        pilot[dom] = {"n": len(sel), "by_split_K": dict(collections.Counter(f"{'train' if e in by['train'] else 'val'}|{e['K']}" for e in sel)),
                      "by_source": dict(collections.Counter(e["source"] for e in sel))}
    (out / "PILOT.json").write_text(json.dumps(pilot, indent=1))
    print(json.dumps(pilot))


if __name__ == "__main__":
    main()
