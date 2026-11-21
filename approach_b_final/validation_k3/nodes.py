#!/usr/bin/env python3
"""Labeled-node coefficients and label-coverage audit (Experiments A2-A4, B1, B3, D ranking; teacher-free, frozen labels only).
    python nodes.py audit DOM                 A3: observation structure of the finalized X/Y labels (unique-endpoint accounting), all splits
    python nodes.py dump DOM SPLIT MODEL...   raw b (endpoint Y logit), a (X logit at Y=0), w (F5) for every labeled X node and Y node
-> $K3V/runs/out/nodes/{audit_DOM.json, DOM_SPLIT_MODEL.jsonl}.  MODEL: FULL_s0..2 (frozen D), DREFIT_s*, E_s*, G_s*, DIRECT_s*."""
import collections, json, sys
from pathlib import Path

import vk
import xy as XY  # noqa: E402


def audit(dom):
    out = {}
    for split in ("train", "val", "test"):
        C = collections.Counter()
        disc = collections.Counter()
        for r in vk.rows(dom, split):
            v, lab, qm = XY.root_view(r)
            oy, ox = lab["obs_y"], lab["obs_x"]
            kids = collections.defaultdict(list)
            for q, s in enumerate(v["parent"]):
                kids[s].append(q)
            C["roots"] += 1
            C["y_nodes_observed"] += len(oy)
            C["y_noop_observed"] += int(v["y0"] in oy)
            C["x_nodes"] += len(v["x_seqs"])
            C["x_nodes_observed"] += len(ox)
            for q, x in ox.items():
                y = oy.get(v["parent"][q])
                C[f"x_obs__y_{'missing' if y is None else y}"] += 1
                C[f"x{x}__y_{'missing' if y is None else y}"] += 1
                C[f"x_obs_len{len(v['x_seqs'][q])}__y_{'missing' if y is None else y}"] += 1
            for s, y in oy.items():
                if s == v["y0"]:
                    continue
                n_obs = sum(q in ox for q in kids.get(s, []))
                C[f"edited_endpoint_y{y}__x_children_observed_{min(n_obs, 2)}{'+' if n_obs >= 2 else ''}"] += 1
            for s, qs in kids.items():                                           # unique endpoints with >= 2 observed orderings
                xs = [ox[q] for q in qs if q in ox]
                if len(xs) >= 2:
                    y = oy.get(s)
                    k = f"y_{'missing' if y is None else y}"
                    disc[f"endpoints_multi_order__{k}"] += 1
                    disc[f"endpoints_discordant_x__{k}"] += int(0 < sum(xs) < len(xs))
            for s in kids:
                if s not in oy:
                    C["endpoints_with_x_child_but_y_missing"] += 1
        out[split] = {**dict(sorted(C.items())), **dict(sorted(disc.items()))}
    vk.wjson(vk.OUT / "nodes" / f"audit_{dom}.json", out)
    print(json.dumps(out, indent=1))


def dump(dom, split, models):
    import torch
    items = []
    snap = vk.EXPS if split == "train" else vk.SNAP
    for r in vk.rows(dom, split, snap):
        v, lab, qm = XY.root_view(r)
        items.append({"v": v, "lab": lab, "qm": qm, "root": r})
    for model in models:
        net = XY.load_model(vk.ckpt(model, dom), "cuda")
        fo = vk.OUT / "nodes" / f"{dom}_{split}_{model}.jsonl"
        fo.parent.mkdir(parents=True, exist_ok=True)
        with torch.no_grad(), open(fo, "w") as f:
            for chunk in XY.batches(items, 256):
                b, _ = XY.collate([c["v"] for c in chunk], [c["lab"] for c in chunk], device="cuda", dtype=torch.float32)
                C = {k: v.double().cpu().numpy() for k, v in net.coeffs(b).items() if k in ("b", "a", "w")}
                qo = so = 0
                for c in chunk:
                    v, l, r = c["v"], c["lab"], c["root"]
                    meta = {"root": r["root_id"], "lineage": r["layout_root_id"], "K": r["K_legacy"]}
                    for s in range(len(v["y_xy"])):
                        f.write(json.dumps({**meta, "node": "Y", "s": s, "noop": s == v["y0"], "y": l["obs_y"].get(s), "b": C["b"][so + s]}) + "\n")
                    for q in range(len(v["x_seqs"])):
                        s = v["parent"][q]
                        f.write(json.dumps({**meta, "node": "X", "q": q, "s": s, "len": len(v["x_seqs"][q]), "kind": c["qm"][q]["kind"] if c["qm"][q] else None,
                                            "seq": v["x_seqs"][q] and c["qm"][q]["seq"], "x": l["obs_x"].get(q), "y": l["obs_y"].get(s),
                                            "b": C["b"][so + s], "a": C["a"][qo + q], "w": C["w"][qo + q]}) + "\n")
                    qo += len(v["x_seqs"]); so += len(v["y_xy"])
        print(json.dumps({"dom": dom, "split": split, "model": model, "out": str(fo), "sha256_ckpt": vk.sha(vk.ckpt(model, dom))}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "audit":
        audit(a[1])
    elif a[0] == "dump":
        dump(a[1], a[2], a[3:])
    else:
        raise SystemExit(__doc__)
