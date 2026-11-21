#!/usr/bin/env python3
"""Experiment C2 / C4 (model-only, frozen TaskCVAE scratch_all s0 of the bundle vs the NoTask cVAE s0; VAL roots, no teacher):
  C2 same-scene task sensitivity: per (root, query object) destination marginals (n_z = 512 prior draws, common random numbers across contexts)
     under the TRUE task, a GOAL-SWAPPED task and a TARGET-SWAPPED task (retarget.py, label-blind deterministic choice), plus the MC-noise floor
     (two independent generators, same task) and the between-query-object scale.  JS divergence / top-4 overlap on the common legal set,
     corridor mass (cells within 1 pitch of the target->goal segment of the TRUE task), entropy, and ingredient recall@4 of known successful
     (object, destination) pairs under each context.
  C4 intermediate scenes: recall@4 of the 2nd / 3rd ingredient of known successful assignments queried in S0 vs in the scene after the
     preceding verified move(s) (re-rooted inputs; the cVAE was trained on S0 contexts only).
    python cvae_probe.py DOM [N_ROOTS]   -> $K3V/runs/out/cvae/C2C4_DOM.json"""
import hashlib, json, math, sys
from pathlib import Path

import numpy as np
import torch

import vk
import retarget as RT
import placement as PL  # noqa: E402
import search as S  # noqa: E402
import contracts as CT  # noqa: E402

NZ = 512


def load_cvae(path, dev="cuda"):
    ck = torch.load(path, map_location=dev, weights_only=False)
    m = PL.TaskCVAE(*ck["grid"], ck["tdim"], ck["cfg"]["hidden"], ck["cfg"]["zdim"]).to(dev)
    m.load_state_dict(ck["state"]); m.task_on = ck["v"]["task"]; m.eval()
    return m


def dists(m, mu, sd, root, cells, objs, inp, seed=0):
    """-> {obj: p over cells (numpy)} for scene `cells` and task inputs `inp` (legal = root.legal_dests(cells) with inp's goal)."""
    cd = {root.ids[i]: c for i, c in enumerate(cells)}
    occ0, occ = set(root.cells0), set(cells)
    legal = [d for d in root.legal if d not in occ and d not in occ0 and d != int(inp["goal_cell"])]
    Fs, Ms, Os, Ls = [], [], [], []
    for o in objs:
        F, Mk, oc, _ = PL.scene_features(root.dom, root.pattr, cd, root.ids[o], root.legal)
        lg = np.zeros(len(oc), bool); lg[legal] = True
        oc = np.concatenate([oc, PL.task_features(root.dom, inp, cells, o, m.task_on)])
        Fs.append((F - mu) / sd * Mk[:, None]); Ms.append(Mk); Os.append(oc); Ls.append(lg)
    T = lambda a, dt: torch.as_tensor(np.stack(a), dtype=dt, device="cuda")  # noqa: E731
    gen = torch.Generator(device="cuda").manual_seed(seed)
    with torch.no_grad():
        p, _ = PL.marginal(m, T(Fs, torch.float32), T(Ms, torch.bool), T(Os, torch.float32), T(Ls, torch.bool), None, NZ, gen)
    return {o: p[i].double().cpu().numpy() for i, o in enumerate(objs)}


def js(p, q, common):
    p, q = p[common], q[common]
    if p.sum() <= 0 or q.sum() <= 0:
        return None
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)
    kl = lambda a, b: float(np.sum(np.where(a > 0, a * np.log(np.maximum(a, 1e-300) / np.maximum(b, 1e-300)), 0.0)))  # noqa: E731
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def top(p, k=4):
    return set(np.argsort(-p, kind="stable")[:k][p[np.argsort(-p, kind="stable")[:k]] > 0].tolist())


def corridor(inp, cells, dom):
    """cells whose centre lies within 1 pitch of the segment target-cell centre -> goal centre (TRUE task)."""
    cx = {int(c): np.array(v, float) for c, v in inp["cell_xy"].items()}
    a, b = cx[int(cells[inp["tid"]])], cx[int(inp["goal_cell"])]
    pitch = 0.08 if dom == "2d" else 0.075
    out = []
    for c, x in cx.items():
        t = np.clip(np.dot(x - a, b - a) / max(np.dot(b - a, b - a), 1e-12), 0, 1)
        if np.linalg.norm(x - (a + t * (b - a))) <= pitch + 1e-9:
            out.append(c)
    return out


def pick(seq, key):
    return sorted(seq, key=lambda c: hashlib.sha256(f"{key}|{c}".encode()).hexdigest())[0] if seq else None


def main(dom, n_roots=None):
    torch.set_num_threads(4)
    sc = json.loads((vk.BUNDLE / dom / "scalers.json").read_text())
    mu, sd = np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)
    models = {"task": load_cvae(vk.BUNDLE / dom / "sampler.pt"), "notask": load_cvae(vk.K3A / "runs/training/notask_cvae" / dom / "scratch_all_notask_s0" / "model.pt")}
    R = vk.rows(dom, "val")
    selft = RT.selftest(R, dom)
    assert selft["failures"] == 0, selft
    R = sorted(R, key=lambda r: hashlib.sha256(("c2|" + r["root_id"]).encode()).hexdigest())[: n_roots or len(R)]
    acc = {m: {k: [] for k in ("js_goal", "js_target", "js_noise", "js_query", "ov_goal", "ov_target", "ov_noise", "corr_true", "corr_goalswap", "corr_targetswap",
                               "ent", "rec_true", "rec_goalswap", "rec_targetswap", "c4_rec_s0", "c4_rec_inter", "c4_n", "rec_root", "c4_root")} for m in models}
    for r in R:
        root = S.Root(r, dom)
        inp = r["inputs"]
        mv = list(root.movable)
        if len(mv) < 2:
            continue
        occ = set(root.cells0)
        gcand = [c for c in root.legal if c not in occ and c != inp["goal_cell"]
                 and max(abs(c // root_c(dom) - inp["goal_cell"] // root_c(dom)), abs(c % root_c(dom) - inp["goal_cell"] % root_c(dom))) >= 2]
        g2 = pick(gcand, "goal|" + r["root_id"])
        A = pick(mv, "target|" + r["root_id"])
        inp_g = RT.retarget(inp, dom, None, g2) if g2 is not None else None
        inp_t = RT.retarget(inp, dom, A, None)
        objs = [o for o in mv if o != A]                                     # queried under every context (A is the target in inp_t)
        cor = set(corridor(inp, root.cells0, dom)) - {int(inp["goal_cell"]), g2}       # goal cells excluded (their legality flips under a goal swap)
        Y = {CT.ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
        succ = [q["seq"] for q in r["labels"]["X"] if q["x"] == 1 and Y.get(CT.ekey(q["seq"])) == 1]
        ing = {(int(o), int(d)) for s in succ for o, d in s if int(o) in objs}
        for name, m in models.items():
            P = dists(m, mu, sd, root, root.cells0, objs, inp, 0)
            Pn = dists(m, mu, sd, root, root.cells0, objs, inp, 1)
            Pg = dists(m, mu, sd, root, root.cells0, objs, inp_g, 0) if inp_g else None
            Pt = dists(m, mu, sd, root, root.cells0, objs, inp_t, 0)
            a = acc[name]
            for i, o in enumerate(objs):
                p = P[o]
                lg = p > 0
                a["ent"].append(float(-(p[lg] * np.log(p[lg])).sum()))
                a["js_noise"].append(js(p, Pn[o], lg & (Pn[o] > 0))); a["ov_noise"].append(len(top(p) & top(Pn[o])) / 4)
                a["js_target"].append(js(p, Pt[o], lg & (Pt[o] > 0))); a["ov_target"].append(len(top(p) & top(Pt[o])) / 4)
                if Pg:
                    a["js_goal"].append(js(p, Pg[o], lg & (Pg[o] > 0))); a["ov_goal"].append(len(top(p) & top(Pg[o])) / 4)
                if i + 1 < len(objs):
                    q = P[objs[i + 1]]
                    a["js_query"].append(js(p, q, lg & (q > 0)))
                cm = [c for c in cor if c < len(p)]
                a["corr_true"].append(float(p[cm].sum()))
                a["corr_targetswap"].append(float(Pt[o][cm].sum()))
                if Pg:
                    a["corr_goalswap"].append(float(Pg[o][cm].sum()))
            for (o, d) in ing:
                a["rec_root"].append(r["root_id"])
                a["rec_true"].append(float(d in top(P[o])))
                a["rec_targetswap"].append(float(d in top(Pt[o])))
                a["rec_goalswap"].append(float(d in top(Pg[o])) if Pg else None)
            for s in succ:                                                   # C4: later ingredients in S0 vs after the preceding moves
                for j in range(1, len(s)):
                    o, d = int(s[j][0]), int(s[j][1])
                    if o not in root.movable:
                        continue
                    pre = root.cells([(int(x), int(y)) for x, y in s[:j]])
                    p0 = dists(m, mu, sd, root, root.cells0, [o], inp, 0)[o]
                    p1 = dists(m, mu, sd, root, pre, [o], inp, 0)[o]
                    a["c4_rec_s0"].append(float(d in top(p0))); a["c4_rec_inter"].append(float(d in top(p1))); a["c4_n"].append(j); a["c4_root"].append(r["root_id"])
    out = {"dom": dom, "n_roots": len(R), "retarget_selftest": selft, "n_z": NZ, "models": {}}
    rr = acc["task"]["rec_root"]
    assert rr == acc["notask"]["rec_root"]
    out["paired_task_minus_notask_rec_true_pp"] = vk.cluster_boot(np.array(acc["task"]["rec_true"]) - np.array(acc["notask"]["rec_true"]), rr)
    for name, a in acc.items():
        f = lambda k: [x for x in a[k] if x is not None]  # noqa: E731
        stat = lambda k: {"n": len(f(k)), "mean": float(np.mean(f(k))) if f(k) else None, "median": float(np.median(f(k))) if f(k) else None}  # noqa: E731
        res = {k: stat(k) for k in a if k not in ("c4_n", "rec_root", "c4_root")}
        def pd(x, y, roots):
            v = [(p - q, g) for p, q, g in zip(a[x], a[y], a[roots]) if p is not None and q is not None]
            return vk.cluster_boot([t[0] for t in v], [t[1] for t in v])
        res["paired_ci_pp"] = {"rec_true-goalswap": pd("rec_true", "rec_goalswap", "rec_root"), "rec_true-targetswap": pd("rec_true", "rec_targetswap", "rec_root"),
                               "c4_inter-s0": pd("c4_rec_inter", "c4_rec_s0", "c4_root")}
        n = np.array(a["c4_n"]); r0, r1 = np.array(a["c4_rec_s0"]), np.array(a["c4_rec_inter"])
        res["c4_by_preceding_moves"] = {int(j): {"n": int((n == j).sum()), "rec_s0": float(r0[n == j].mean()), "rec_inter": float(r1[n == j].mean())} for j in sorted(set(n.tolist()))}
        out["models"][name] = res
    vk.wjson(vk.OUT / "cvae" / f"C2C4_{dom}.json", out)
    print(json.dumps(out, indent=1))


def root_c(dom):
    return PL.GRID[dom][1]


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
