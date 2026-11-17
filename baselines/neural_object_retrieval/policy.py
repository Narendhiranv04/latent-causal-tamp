#!/usr/bin/env python3
"""NOR-Grid open-loop one-shot policy (no teacher, planner or label import; public rows only).

Rollout (Ren & Qureshi III-E, open-loop): for depth 1..3: OSNet argmax over eligible (movable, not yet moved) objects -> RPNet argmin cost
over statically legal destinations (graph.legal_dests) -> hypothetical object edit.  STOP adapter p_k = sigmoid(logit / T) on every
visited prefix k = 0..3 (T: temperature fitted on decided VALIDATION endpoint Y labels, never on this policy's outcomes).
Decision rule NOR_RULE_V1 (frozen before any VALIDATION prediction is verified): k* = first k with p_k >= 0.5 -> NOOP (k* = 0) /
REPAIR (prefix k*); none -> ABSTAIN.  Deterministic tie-breaks: lowest object index / lowest cell index.
Ablation variants (pre-declared): full | osnet_only (RPNet -> nearest legal cell to the source) | rpnet_only (OSNet -> eligible object
nearest to the target) | both_analytic | no_stop (always the full rollout; NOOP/ABSTAIN only when no legal move exists) | no_goal
(separately trained models on goal-free features).

    policy.py predict PUBLIC.jsonl MODELDIR OUT.jsonl [VARIANT] [DEVICE]"""
import hashlib, json, resource, sys, time
from pathlib import Path

import numpy as np
import torch

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import graph as G  # noqa: E402
import networks as NW  # noqa: E402

TAU = 0.5


def load(mdir, dev):
    mdir = Path(mdir)
    out = {}
    for k, cls in (("os", NW.OSNet), ("rp", NW.RPNet), ("st", NW.StopAdapter)):
        ck = torch.load(mdir / f"{k}.pt", map_location=dev)
        c = ck["cfg"]
        m = cls(c["d"], c[f"{k}_layers"]).to(dev)
        m.load_state_dict(ck["state"])
        out[k] = m.eval()
    cal = json.loads((mdir / "calibration.json").read_text()) if (mdir / "calibration.json").exists() else {"T": 1.0}
    out["T"] = float(cal["T"])
    out["hash"] = hashlib.sha256(b"".join((mdir / f"{k}.pt").read_bytes() for k in ("os", "rp", "st"))).hexdigest()
    out["goal"] = not (mdir / "NO_GOAL").exists()
    return out


def tens(sc, dom, tid, dev):
    tm = np.zeros(G.NMAX[dom] + 2, bool)
    tm[tid] = True
    f = lambda a, dt=torch.float32: torch.as_tensor(np.asarray(a)[None], dtype=dt, device=dev)  # noqa: E731
    return f(sc["X"]), f(sc["M"], torch.bool), f(sc["C"]), f(sc["elig"], torch.bool), f(tm, torch.bool)


@torch.no_grad()
def predict_one(row, Mo, variant="full", dev="cpu"):
    inp, dom = row["inputs"], row["domain"]
    tid, prefix, probs, t0 = inp["tid"], [], [], time.time()
    calls = {"os": 0, "rp": 0, "st": 0}
    xy = {int(k): np.array(v) for k, v in inp["cell_xy"].items()}
    for depth in range(4):
        sc = G.scene(inp, dom, prefix, goal=Mo["goal"])
        X, M, C, E, TM = tens(sc, dom, tid, dev)
        probs.append(float(torch.sigmoid(Mo["st"](X, M, TM) / Mo["T"])))
        calls["st"] += 1
        if depth == 3 or not sc["elig"].any():
            break
        cells = G.apply(inp, prefix)
        legal = G.legal_dests(inp, cells)
        if not legal:
            break
        elig = [int(i) for i in np.flatnonzero(sc["elig"])]
        if variant in ("rpnet_only", "both_analytic"):
            tp = np.array(inp["cell_xy"][str(cells[tid])])
            o = min(elig, key=lambda i: (float(np.linalg.norm(xy[cells[i]] - tp)), i))
        else:
            p, _ = Mo["os"](X, M, E, TM)
            calls["os"] += 1
            p = p[0].cpu().numpy()
            o = max(elig, key=lambda i: (p[i], -i))
        if variant in ("osnet_only", "both_analytic"):
            d = min(legal, key=lambda c: (float(np.linalg.norm(xy[c] - xy[cells[o]])), c))
        else:
            c = Mo["rp"](X, M, C, torch.tensor([o], device=dev), TM)[0].cpu().numpy()
            calls["rp"] += 1
            d = min(legal, key=lambda q: (float(c[q]), q))
        prefix = prefix + [(o, int(d))]
    if variant == "no_stop":
        k = len(prefix)
        decision = "REPAIR" if k else "ABSTAIN"
    else:
        k = next((i for i, pk in enumerate(probs) if pk >= TAU), None)
        decision = "ABSTAIN" if k is None else "NOOP" if k == 0 else "REPAIR"
    moves = [{"object_id": inp["ids"][o], "object_index": o, "destination_cell": d} for o, d in (prefix[:k] if decision == "REPAIR" else [])]
    return {"root_id": row["root_id"], "domain": dom, "decision": decision, "moves": moves, "method": f"nor_grid_{variant}",
            "model_hash": Mo["hash"], "inference_mode": "open_loop_one_shot", "stop_probs": [round(x, 5) for x in probs],
            "rollout": [[o, d] for o, d in prefix], "timing_s": {"total": round(time.time() - t0, 5)},
            "n_osnet_calls": calls["os"], "n_rpnet_calls": calls["rp"], "n_stop_calls": calls["st"], "device": dev,
            "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}


def predict(public, mdir, out, variant="full", dev="cpu"):
    torch.set_num_threads(2)
    Mo = load(mdir, dev)
    rows = [json.loads(l) for l in open(public)]
    done = {json.loads(l)["root_id"] for l in open(out)} if Path(out).exists() else set()
    with open(out, "a") as f:
        for r in rows:
            if r["root_id"] not in done:
                f.write(json.dumps(predict_one(r, Mo, variant, dev)) + "\n")
    print(json.dumps({"out": str(out), "n": len(rows), "variant": variant, "model_hash": Mo["hash"]}))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "predict":
        predict(a[2], a[3], a[4], a[5] if len(a) > 5 else "full", a[6] if len(a) > 6 else "cpu")
