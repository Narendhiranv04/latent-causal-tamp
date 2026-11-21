#!/usr/bin/env python3
"""E5 search-budget diagnostic (VAL only, frozen FULL_s0 D, identical M4 pools): the argmax-p11 repair among the B candidates with the smallest
sha256('BUDGET|root|signature') (a label-blind uniform random subset of size B), B in {1, 16, 256, 4096}; registered rule; all = FULL.
    python budget.py DOM [PART i/k]   -> $K3V/runs/out/budget/val_DOM[.part].jsonl"""
import hashlib, json, sys

import numpy as np
import torch

import vk
import xy as XY  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402

BS = (1, 16, 256, 4096)


def run(dom, part=None):
    pub = vk.jl(vk.K3A / "runs/public" / f"public_val_{dom}.jsonl")
    full = {r["root_id"]: r for r in vk.jl(vk.K3A / "runs/predictions/FULL_s0" / f"val_{dom}.jsonl")}
    if part:
        i_, k_ = map(int, part.split("/"))
        pub = [r for r in pub if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k_ == i_]
    fo = vk.OUT / "budget" / (f"val_{dom}.jsonl" if not part else f"val_{dom}.part{part.replace('/', 'of')}.jsonl")
    fo.parent.mkdir(parents=True, exist_ok=True)
    done = {r["root_id"] for r in vk.jl(fo)}
    scor = S.Scorer(vk.ckpt("FULL_s0", dom), None, device="cuda")
    with open(fo, "a") as f:
        for r in pub:
            if r["root_id"] in done:
                continue
            root = S.Root(r, dom)
            Dm = {int(o): [int(d) for d in v] for o, v in full[r["root_id"]]["proposals"].items()}
            seqs = [s for s, _ in EX.stream(Dm, 4)]
            h = np.array([int(hashlib.sha256(f"BUDGET|{root.id}|{json.dumps([list(x) for x in s])}".encode()).hexdigest()[:15], 16) for s in seqs], dtype=np.int64)
            order = np.argsort(h, kind="stable")
            p = []
            for i in range(0, len(seqs), 8192):
                p += [c["p11"] for c in scor.score(root, [list(map(list, s)) for s in seqs[i:i + 8192]])]
            p = np.array(p)
            rec = {"root_id": r["root_id"], "n_cand": len(seqs), "p_noop": scor.score(root, [[]])[0]["p11"], "B": {}}
            for B in BS:
                idx = order[:B]
                if not len(idx):
                    continue
                cost = -np.log(np.maximum(p[idx], 1e-12))
                near = idx[cost <= cost.min() + 1e-9]
                k0, i0 = min((EX.key(float(-np.log(max(p[i], 1e-12))), len(seqs[i]), root.displacement(list(seqs[i])), seqs[i]), int(i)) for i in near)
                rec["B"][str(B)] = {"seq": [list(map(int, x)) for x in seqs[i0]], "p": float(p[i0])}
            f.write(json.dumps(rec) + "\n"); f.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1] if len(a) > 1 else None)
