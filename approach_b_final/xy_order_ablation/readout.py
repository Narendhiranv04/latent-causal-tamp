#!/usr/bin/env python3
"""Planner-side frozen structured-energy readouts (plan.md 3).  Inputs: public rows {root_id, domain, inputs} + the frozen bundle only.

One forward pass of the frozen coupled X/Y net (tau = 1, xy.TAU) per chunk gives, for every ordered repair r with endpoint A:
    pY = sigmoid(b_A)   pX0 = sigmoid(a_r)   pX1 = sigmoid(a_r + w_r)   pX = (1 - pY) pX0 + pY pX1   p11 = pY pX1
computed with exactly the float32 ops of xy.XYNet.predict / xy.marginals, so J reproduces production p11 bit-for-bit.  pY of an endpoint is
shared by every order: the first value seen for a canonical assignment is reused (cross-chunk float drift is logged, never used).
Arms (same pool, gate, no-op = pY(empty), eta, tie key, exhaustive.Selectors):  J = p11, X = pX, Y = pY, XC = pX1.
Rank-only: argmax nonempty repair per readout, no gate, no admission threshold, no no-op."""
from __future__ import annotations

import hashlib, json, os, sys, time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ABF = HERE.parent
if str(ABF) not in sys.path:
    sys.path.insert(0, str(ABF))
import benchmark as BM  # noqa: E402
import exhaustive as EX  # noqa: E402
import search as S  # noqa: E402
import xy as XY  # noqa: E402

BUNDLE = Path(os.environ.get("XYO_BUNDLE", Path.home() / "abf_v34/approach_b_bundle"))
ARMS = ("J", "X", "Y", "XC")
FIELD = {"J": "p11", "X": "px", "Y": "py", "XC": "px1"}
RANK_RULE = {"noop_gate": None, "eta": 0.0, "alpha": 0.0, "beta": 0.0, "gamma": 0.0}


def sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def load(dom, dev=None):
    dev = dev or os.environ.get("XYO_DEVICE", "cuda")
    samp, scor, man = BM.load_bundle(BUNDLE, dom, dev, 0)
    return samp, scor, man


@torch.no_grad()
def score(scor, root, seqs):
    """Readouts for ordered sequences of one ORIGINAL root (production semantics: original-root view, ideal-prefix order features).
    -> (dict of float64 numpy arrays py, px1, px0, px, p11, b, a, w over seqs, p_noop)."""
    inp = root.row["inputs"]
    P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
    xs = [[(i, P(d)) for i, d in s] for s in seqs]
    v, _, xm = XY.make_view(root.id, inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
    b, _ = XY.collate([v], device=scor.dev, dtype=torch.float32)
    C = scor.net.coeffs(b)
    mg = XY.marginals(C["b"], C["a"], C["w"], b["parent"])
    p_noop = float(mg["py"][b["y0"]][0])
    if not seqs:
        return {}, p_noop
    q = torch.as_tensor(xm, device=C["a"].device)
    par = b["parent"][q]
    out = {"py": mg["py"][par], "px": mg["px"][q], "p11": mg["psucc"][q], "px1": torch.sigmoid(C["a"] + C["w"])[q], "px0": torch.sigmoid(C["a"])[q],
           "b": C["b"][par], "a": C["a"][q], "w": C["w"][q]}
    scor.evals += len(seqs)
    return {k: np.array([float(x) for x in v.cpu()], float) for k, v in out.items()}, p_noop


def canon(seq):
    return json.dumps(sorted([int(o), int(d)] for o, d in seq))


def run_root(row, samp, scor, man, chunk=8192):
    """Stream the identical original top-4 pool once; update J/X/Y/XC deployment + rank-only selectors.  No labels, no teacher."""
    dom = row["domain"]
    root = S.Root(row, dom)
    rule = man["config"]["rule"]
    sync(); t0 = time.time()
    D6 = EX.proposals(root, samp, man["config"]["proposal_seed"])
    sync(); t1 = time.time()
    dep = {a: EX.Selectors([rule]) for a in ARMS}
    rk = {a: EX.Selectors([RANK_RULE]) for a in ARMS}
    py_of, drift, n, h = {}, 0.0, 0, hashlib.sha256()
    counts = [0, 0, 0]
    p_noop = score(scor, root, [])[1]
    buf = []

    def flush():
        nonlocal drift
        if not buf:
            return
        sc, _ = score(scor, root, [list(map(list, s)) for s in buf])
        for i, s in enumerate(buf):                                   # one shared pY per canonical endpoint
            k = canon(s)
            if k in py_of:
                drift = max(drift, abs(py_of[k] - sc["py"][i]))
                sc["py"][i] = py_of[k]
            else:
                py_of[k] = sc["py"][i]
        m = np.array([len(s) for s in buf])
        Dd = np.array([root.displacement(list(s)) for s in buf], float)
        z = np.zeros(len(buf), int)
        extra = {k: sc[k] for k in ("py", "px", "p11", "px1", "px0")}
        for a in ARMS:
            dep[a].update(buf, sc[FIELD[a]], m, Dd, np.zeros(len(buf)), z, extra)
            rk[a].update(buf, sc[FIELD[a]], m, Dd, np.zeros(len(buf)), z, extra)
        buf.clear()

    for s, r in EX.stream(D6, man["config"]["M"]):
        buf.append(s); n += 1; counts[len(s) - 1] += 1
        h.update(json.dumps([list(map(int, a)) for a in s]).encode())
        if len(buf) >= chunk:
            flush()
    flush()
    sync(); t2 = time.time()
    out = {"root_id": row["root_id"], "domain": dom, "p_noop": p_noop, "n_pool": n, "counts_by_K": counts, "pool_hash": h.hexdigest(),
           "proposals": {str(k): v[:man["config"]["M"]] for k, v in D6.items()}, "py_endpoint_drift": drift, "n_endpoints": len(py_of),
           "timing_s": {"proposal": round(t1 - t0, 5), "stream_score_select": round(t2 - t1, 5)}, "teacher_calls": 0, "arms": {}, "rank_only": {}}
    for a in ARMS:
        d = dep[a].finish(p_noop)[4][0]
        out["arms"][a] = {"decision": "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR", "seq": None if d is None else d["seq"],
                          "score": None if d is None else (d["p11"] if not d["seq"] else d[FIELD[a]]), **({k: d[k] for k in ("py", "px", "p11", "px1", "px0") if k in d} if d and d["seq"] else {})}
        b = rk[a].best.get((4, 0.0, (0.0, 0.0, 0.0)))
        out["rank_only"][a] = None if b is None else {"seq": b[1]["seq"], **{k: b[1][k] for k in ("py", "px", "p11", "px1", "px0")}}
    return out
