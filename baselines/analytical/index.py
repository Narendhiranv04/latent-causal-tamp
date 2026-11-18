"""Build a TRAIN smoke set: public rows (benchmark format) + a private index for benchmark.py evaluate (same format as
~/sorc_grid/eval/private_val_*.jsonl).  This is evaluation plumbing: it reads K / masks from the snapshot to pick a K1-K3 mix and to fill
the PRIVATE index; the planners only ever receive the public file.

    python3 -m baselines.analytical.index SNAPSHOT_DIR OUT_DIR --per-k 2 [--ks 1,2,3] [--split train]"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import envs


def build(snap, out, per_k=2, ks=("1", "2", "3"), split="train", salt="ANALYTICAL_SMOKE_V1"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    envs.make_env("2d", str(out / "witness_unused"))                   # only to import disco_grid/data.py (raw paths)
    for dom in ("2d", "3d"):
        rows = [json.loads(l) for l in open(Path(snap) / f"data{dom}.jsonl")]
        rows = [r for r in rows if r["split"] == split]
        pick = []
        for k in ks:
            c = sorted((r for r in rows if r["K_legacy"] == k), key=lambda r: hashlib.sha256(f"{salt}|{r['root_id']}".encode()).hexdigest())
            pick += c[:per_k]
        pub, priv = out / f"public_{split}_{dom}.jsonl", out / f"private_{split}_{dom}.jsonl"
        with open(pub, "w") as fp, open(priv, "w") as fq:
            for r in sorted(pick, key=lambda r: r["root_id"]):
                p = envs.raw_path(dom, r["root_id"])
                rec = json.loads(Path(p).read_text())
                fp.write(json.dumps({"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]}, sort_keys=True) + "\n")
                fq.write(json.dumps({"root_id": r["root_id"], "domain": dom, "K": r["K_legacy"], "masks": r["masks"], "path": str(p),
                                     "geom": rec.get("geometry_impl") or "original", "ids": r["inputs"]["ids"],
                                     "evaluation_group_id": r["root_id"]}) + "\n")
        print(dom, len(pick), pub, priv)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("out")
    ap.add_argument("--per-k", type=int, default=2)
    ap.add_argument("--ks", default="1,2,3")
    ap.add_argument("--split", default="train")
    A = ap.parse_args()
    assert A.split == "train", "smoke sets are TRAIN-only"
    build(A.snapshot, A.out, A.per_k, tuple(A.ks.split(",")), A.split)
