#!/usr/bin/env python3
"""NOR-Grid training tensors from the TRAIN-only homotopy labels (homotopy.py) + decided endpoint Y (STOP adapter).

States per TRAIN root (all hypothetical object edits of S0, never robot states):
  S0; the label policy's own greedy rollout (argmax blocking count -> argmin region cost, <= 3 steps, stops when no object blocks);
  every prefix of a verified successful repair (X=1 and Y=1, nor_data.supervision).
Blocking of object o by reference path k: 2D cell(o) in sweep_k; 3D o in blockers_k if o is at its S0 cell (exact _object_hits) else
cell(o) in sweep_k (generic-column probe).  OSNet target p = counts / sum over eligible objects (state skipped if the sum is 0).
RPNet target for (state, o): cost map (illegal or majority-swept -> 1, else 0.9 * source distance / max), for the 3 most-blocking eligible objects and the successful repairs' next objects.
STOP: every decided endpoint Y of the root (TRAIN) or of VAL roots (calibration only).  Holdout: 10% of TRAIN roots (sha256 group).

    samples.py DOM LABELS.jsonl OUT.npz"""
import hashlib, json, sys
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import graph as G  # noqa: E402
import homotopy as HM  # noqa: E402
import nor_data as DA  # noqa: E402
import os  # noqa: E402

GOAL = os.environ.get("NOR_GOAL", "1") != "0"                     # NOR_GOAL=0: task-goal ablation tensors (every goal feature zeroed)


def paths_of(e, dom, inp):
    ids = {o: i for i, o in enumerate(inp["ids"])}
    out = []
    for p in e["paths"]:
        if p["status"] != "VERIFIED":
            continue
        out.append({"sweep": set(map(int, p["sweep"])), "blk": {ids[o] for o in p.get("blockers", []) if o in ids}})
    return out


def counts(inp, dom, cells, P):
    n = len(inp["ids"])
    mov = G.movable(inp, dom)
    c0 = [int(c) for c in inp["cells0"]]
    cnt = {}
    for o in mov:
        k = 0
        for p in P:
            if dom == "2d" or cells[o] != c0[o]:
                k += int(cells[o]) in p["sweep"]
            else:
                k += o in p["blk"]
        cnt[o] = k
    return cnt


def cost_map(inp, cells, P, o, nc):
    legal = set(G.legal_dests(inp, cells))
    # REGION_RULE_V2_MAJORITY (P2 pilot-gate revision, before any full training): a cell is homotopy-blocking iff it lies on the sweep of
    # at least half of the reference paths.  The V1 union rule marked 63/64 2D cells blocking (the planar 3R arm reaches over almost the
    # whole lattice across grasp homotopies), leaving RPNet a degenerate all-max cost map.
    U = {c for c in legal if P and sum(c in p["sweep"] for p in P) * 2 >= len(P)}
    xy = {int(k): np.array(v) for k, v in inp["cell_xy"].items()}
    s = xy[int(cells[o])]
    ok = [c for c in legal if c not in U]
    dmax = max([np.linalg.norm(xy[c] - s) for c in ok] or [1.0]) + 1e-9
    cost = np.ones(nc, np.float32)
    for c in ok:
        cost[c] = 0.9 * float(np.linalg.norm(xy[c] - s)) / dmax
    return cost


def build(dom, labels_file, out):
    R = {r["root_id"]: r for r in DA.rows(dom, DA.EXT, "train")}
    V = DA.rows(dom, DA.BASE, "val")
    nc = G.NCELL[dom]
    S = {k: [] for k in ("X", "M", "C", "L", "E", "T", "root", "hold")}
    OS, RP, ST = [], [], []
    cache = {}

    def state(rid, inp, prefix, hold):
        key = (rid, json.dumps(sorted(map(list, prefix))) if prefix is None else json.dumps([list(map(int, m)) for m in prefix]))
        if key in cache:
            return cache[key]
        sc = G.scene(inp, dom, [tuple(m) for m in prefix], goal=GOAL)
        tm = np.zeros(G.NMAX[dom] + 2, bool)
        tm[inp["tid"]] = True
        for k, v in (("X", sc["X"].astype(np.float16)), ("M", sc["M"]), ("C", sc["C"].astype(np.float16)), ("L", sc["L"]), ("E", sc["elig"]), ("T", tm)):
            S[k].append(v)
        S["root"].append(rid)
        S["hold"].append(hold)
        cache[key] = len(S["X"]) - 1
        return cache[key]

    n_skip = {"no_paths": 0, "zero_blockers_S0": 0}
    for l in open(labels_file):
        e = json.loads(l)
        r = R.get(e["root_id"])
        if r is None:
            continue
        inp, rid = r["inputs"], r["root_id"]
        hold = int(hashlib.sha256(("NOR_HOLD|" + rid).encode()).hexdigest(), 16) % 10 == 0
        P = paths_of(e, dom, inp)
        sup = DA.supervision(r, dom)
        for edit, y in sup["STOP"]:                                     # STOP adapter: decided endpoint Y (order-free endpoint scene)
            ST.append((state(rid, inp, edit, hold), float(y)))
        if not P:
            n_skip["no_paths"] += 1
            continue
        prefixes = [[]]
        cur = []
        for _ in range(3):                                              # label policy rollout
            cells = G.apply(inp, cur)
            cnt = {o: c for o, c in counts(inp, dom, cells, P).items() if o not in {m[0] for m in cur}}
            if not cnt or max(cnt.values()) == 0:
                break
            o = max(sorted(cnt), key=lambda k: cnt[k])
            cm = cost_map(inp, cells, P, o, nc)
            legal = G.legal_dests(inp, cells)
            if not legal:
                break
            d = min(legal, key=lambda c: (cm[c], c))
            cur = cur + [[o, d]]
            prefixes.append(list(cur))
        nxt = {}
        for pre, objs in sup["SEQ"]:
            prefixes.append(pre)
            nxt[json.dumps(pre)] = objs
        seen = set()
        for pre in prefixes:
            k = json.dumps(pre)
            if k in seen or (pre and G.is_legal(inp, dom, [tuple(m) for m in pre]) is not None):
                continue
            seen.add(k)
            moved = {m[0] for m in pre}
            cells = G.apply(inp, pre)
            cnt = {o: c for o, c in counts(inp, dom, cells, P).items() if o not in moved}
            si = state(rid, inp, pre, hold)
            tot = sum(cnt.values())
            if tot:
                p = np.zeros(G.NMAX[dom] + 2, np.float32)
                for o, c in cnt.items():
                    p[o] = c / tot
                OS.append((si, p))
            elif not pre:
                n_skip["zero_blockers_S0"] += 1
            objs = sorted(cnt, key=lambda o: -cnt[o])[:3] if tot else []
            objs = [o for o in objs if cnt[o] > 0] + [o for o in nxt.get(k, []) if o not in objs and o not in moved]
            for o in objs:
                RP.append((si, o, cost_map(inp, cells, P, o, nc).astype(np.float16)))
    vst = []
    for r in V:
        for edit, y in DA.supervision(r, dom)["STOP"]:
            vst.append((state(r["root_id"], r["inputs"], edit, False), float(y)))
    np.savez_compressed(out, **{k: np.stack(v) for k, v in S.items() if k not in ("root", "hold")}, root=np.array(S["root"]), hold=np.array(S["hold"]),
                        os_i=np.array([a for a, _ in OS]), os_p=np.stack([b for _, b in OS]),
                        rp_i=np.array([a for a, _, _ in RP]), rp_o=np.array([b for _, b, _ in RP]), rp_c=np.stack([c for _, _, c in RP]),
                        st_i=np.array([a for a, _ in ST]), st_y=np.array([b for _, b in ST], np.float32),
                        vst_i=np.array([a for a, _ in vst]), vst_y=np.array([b for _, b in vst], np.float32))
    info = {"goal_features": GOAL, "dom": dom, "states": len(S["X"]), "osnet": len(OS), "rpnet": len(RP), "stop_train": len(ST), "stop_val": len(vst), **n_skip,
            "holdout_roots": len({r for r, h in zip(S["root"], S["hold"]) if h})}
    Path(str(out) + ".json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3])
