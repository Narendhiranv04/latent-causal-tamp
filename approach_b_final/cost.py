#!/usr/bin/env python3
"""P3 witnessed travel cost (plan.md 5).  Pinned target: J_complete = J_reloc + J_connector + J_target of a successfully witnessed X=1, Y=1 query,
J(record) = sum over consecutive waypoints of sum_j |dq_j| / (q_max_j - q_min_j) (ordered.joint_travel; gripper excluded).  2D: the 3R joint
range [-pi, pi] (2 pi each).  3D: the xArm7 joint ranges of the pinned SHELF66V3 model (stored in targets_3d.json).  A query lacking any of its
witnesses has NO label (masked), never 0.  Head: a separate XYNet (same encoder family) whose readout J = softplus(jt([v_s, c])) + softplus(cost(g_r))
is trained ONLY on Huber(log1p J_hat, log1p J) (independent objective; the X/Y models are untouched).

    python cost.py targets {2D,3D} SNAPSHOT [RANGES_JSON]   -> runs/p3/targets_<dom>.json
    python cost.py fit {2D,3D} SNAPSHOT SEED                -> runs/p3_<dom>/cost_s<seed>/model.pt"""
from __future__ import annotations

import json, math, os, sys, time
from pathlib import Path

import numpy as np

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
G = ABF / "mirror/boltzmann_lfd/final_dataset_generation"
STORES2 = [G / "FINAL_READINESS_GATE/work/xy2d_witnesses", ABF / "runs/teacher2d_witnesses"]
STORES3 = [G / "final3d_v4/work/store", G / "final3d_v4/work/store_gvlab", G / "k3_hard/d3/store", G / "FINAL_READINESS_GATE/work/rpl_store",
           ABF / "labelfill3d/store"]


def wload(w, stores):
    for s in stores:
        f = s / "witnesses" / w[:2] / f"{w}.npz"
        if f.exists():
            z = np.load(f)
            return {k: z[k] for k in z.files}
    return None


def jrec(q, rng):
    q = np.asarray(q, float)
    return float((np.abs(np.diff(q, axis=0)) / rng).sum()) if len(q) > 1 else 0.0


def y_witness_3d():
    """3D Y target witness per (root, endpoint) from the final3d_v4 result files (same resolution as make_final3d / build_rpl3d)."""
    W = G / "final3d_v4/work"
    res, items = {}, {}
    for f in ("k2_xy_yneg.jsonl", "xy_final_laptop.jsonl", "xy_final_gvlab.jsonl", "xy_assist_laptop.jsonl"):
        for l in open(W / f):
            r = json.loads(l)
            res[r["key"]] = r
    for f in ("xy_items.json", "yneg_items.json", "xy_items_k2.json", "yneg_items_k2.json"):
        for i in json.loads((W / f).read_text()):
            items[i["key"]] = i
    out = {}
    for k, r in res.items():
        y = r.get("y") or {}
        if y.get("y") == 1 and y.get("witnesses"):
            out[json.dumps(sorted((o, list(c)) for o, c in y["cells"].items()))] = y["witnesses"][0]
    lf = ABF / "labelfill3d/fin3d_xy.jsonl"
    if lf.exists():
        for l in open(lf):
            y = json.loads(l).get("y") or {}
            if y.get("y") == 1 and y.get("witnesses"):
                out[json.dumps(sorted((o, list(c)) for o, c in y["cells"].items()))] = y["witnesses"][0]
    return out


def targets(dom, snap, ranges=None):
    rows = [json.loads(l) for l in open(Path(snap) / f"data{dom.lower()}.jsonl")]
    if dom == "2D":
        rng, stores = np.full(3, 2 * math.pi), STORES2
    else:
        rng, stores = np.array(json.loads(Path(ranges).read_text())["arm_joint_ranges"]), STORES3
        yw = y_witness_3d()
    out, stat = [], {"x1y1": 0, "labelled": 0, "missing_witness": 0}
    for r in rows:
        inp = r["inputs"]
        ylab = {json.dumps(sorted(map(tuple, y["edit"]))): y["y"] for y in r["labels"]["Y"]}
        for q in r["labels"]["X"]:
            if q["x"] != 1 or ylab.get(json.dumps(sorted(map(tuple, q["seq"])))) != 1:
                continue
            stat["x1y1"] += 1
            xw = q.get("x_witnesses")
            if dom == "2D":
                ywid = q.get("y_witness")
            else:
                cells = {inp["ids"][i]: [c // 6, c % 6] for i, c in enumerate(inp["cells0"])}
                for i, c in q["seq"]:
                    cells[inp["ids"][i]] = [c // 6, c % 6]
                ywid = yw.get(json.dumps(sorted((o, c) for o, c in cells.items())))
            ws = [wload(w, stores) for w in (xw or [])]
            yz = wload(ywid, stores) if ywid else None
            if not xw or any(w is None for w in ws) or yz is None:
                stat["missing_witness"] += 1
                continue
            jx = sum(jrec(w["connector_q"] if "connector_q" in w else w["q"], rng) for w in ws)
            jy = jrec(yz["q"], rng)
            out.append({"root": r["root_id"], "split": r["split"], "seq": q["seq"], "J": jx + jy, "J_x": jx, "J_target": jy})
            stat["labelled"] += 1
    (ABF / "runs/p3").mkdir(parents=True, exist_ok=True)
    (ABF / "runs/p3" / f"targets_{dom.lower()}.json").write_text(json.dumps({"definition": __doc__.split("Head:")[0], "stats": stat, "rows": out}))
    print(json.dumps({"dom": dom, **stat, "J_mean": float(np.mean([o["J"] for o in out])) if out else None}))


def fit(dom, snap, seed, epochs=80, patience=12, batch=64, lr=1e-3):
    import torch
    import torch.nn.functional as F
    import xy as XY
    torch.manual_seed(seed)
    dev = "cuda"
    T = json.loads((ABF / "runs/p3" / f"targets_{dom.lower()}.json").read_text())["rows"]
    by = {}
    for t in T:
        by.setdefault(t["root"], []).append(t)
    rows = [json.loads(l) for l in open(Path(snap) / f"data{dom.lower()}.jsonl")]
    data = {"train": [], "val": [], "test": []}
    for r in rows:
        if r["root_id"] not in by:
            continue
        inp = r["inputs"]
        P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
        ts = by[r["root_id"]]
        v, _, xm = XY.make_view(r["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [],
                                [[(i, P(c)) for i, c in t["seq"]] for t in ts], XY._NoGeo)
        data[r["split"]].append((v, [(xm[k], t["J"]) for k, t in enumerate(ts)]))
    v0 = data["train"][0][0]
    net = XY.XYNet("D", len(v0["attrs"][0]), len(v0["ctx"])).to(dev).float()
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
    out = ABF / "runs" / f"p3_{dom.lower()}" / f"cost_s{seed}"
    out.mkdir(parents=True, exist_ok=True)

    def loss(chunk):
        b, _ = XY.collate([c[0] for c in chunk], device=dev, dtype=torch.float32)
        C = net.coeffs(b)
        qo, idx, val = 0, [], []
        for v, js in chunk:
            idx += [qo + q for q, _ in js]; val += [j for _, j in js]; qo += len(v["x_seqs"])
        jp, jt = C["J"][torch.tensor(idx, device=dev)], torch.tensor(val, device=dev)
        return F.huber_loss(torch.log1p(jp), torch.log1p(jt)), (jp.detach(), jt)
    rng = np.random.default_rng(seed)
    curve, best, bad, t0 = [], (math.inf, -1), 0, time.time()
    for ep in range(epochs):
        net.train()
        idx = rng.permutation(len(data["train"]))
        for i in range(0, len(idx), batch):
            l, _ = loss([data["train"][j] for j in idx[i:i + batch]])
            opt.zero_grad(); l.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(np.mean([loss(data["val"][i:i + 256])[0].item() for i in range(0, len(data["val"]), 256)]))
        curve.append({"epoch": ep, "val_huber_log": vl})
        if vl < best[0] - 1e-6:
            best, bad = (vl, ep), 0
            torch.save({"state": net.state_dict(), "arm": "D", "dom": dom, "seed": seed, "epoch": ep, "attr_dim": len(v0["attrs"][0]),
                        "ctx_dim": len(v0["ctx"]), "role": "travel_head_only"}, out / "model.pt")
        else:
            bad += 1
            if bad >= patience:
                break
    net.load_state_dict(torch.load(out / "model.pt", weights_only=False)["state"])
    net.eval()
    ev = {}
    with torch.no_grad():
        for s in ("val", "test"):
            if data[s]:
                _, (jp, jt) = loss(data[s])
                jp, jt = jp.cpu().numpy(), jt.cpu().numpy()
                ev[s] = {"n": len(jt), "mae": float(np.abs(jp - jt).mean()), "rel_mae": float((np.abs(jp - jt) / jt).mean()),
                         "spearman": float(np.corrcoef(np.argsort(np.argsort(jp)), np.argsort(np.argsort(jt)))[0, 1]), "J_mean": float(jt.mean())}
    (out / "curve.json").write_text(json.dumps({"curve": curve, "best": best, "eval": ev, "n_train_roots": len(data["train"]),
                                                "wall_s": round(time.time() - t0, 1)}, indent=1))
    print(json.dumps({"dom": dom, "seed": seed, "best": best, "eval": ev}))


if __name__ == "__main__":
    if sys.argv[1] == "targets":
        targets(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif sys.argv[1] == "fit":
        fit(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        raise SystemExit(__doc__)
