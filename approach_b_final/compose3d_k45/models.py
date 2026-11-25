"""Frozen 3D models behind counted, cached readouts (plan.md 2): S1 TaskCVAE proposals (search.Sampler.propose_many, top-6 -> top-4 prefix,
fresh CUDA generator seed 0 per call, exactly exhaustive.proposals), X/Y coefficients of the frozen coupled scorer (xy.make_view / collate /
XYNet.coeffs, float32, no grad).  Readouts per ordered sequence c at scene s: pY = sigmoid(b_s), pX1 = sigmoid(a + w), pX0 = sigmoid(a),
marginal pX = pY pX1 + (1 - pY) pX0, p11 = pY pX1.  Y_global(E) = the Y node of endpoint E in a Y-ONLY view of the original root (the
mapped edit node, never y0).  Cache keys include the full scene inputs (task, poses, ids, q_ref) and the ordered sequence."""
from __future__ import annotations

import math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for p in (str(HERE.parent),):
    if p not in sys.path:
        sys.path.insert(0, p)
import scene as SC  # noqa: E402

BUNDLE = Path(os.environ.get("K45_BUNDLE", Path.home() / "abf_v34/approach_b_bundle"))


class Frozen:
    def __init__(self, device="cuda", caps=None):
        import benchmark as BM
        import torch
        self.torch = torch
        self.samp, self.scor, self.man = BM.load_bundle(BUNDLE, "3d", device, 0)       # hash-checked 3D bundle
        self.net, self.dev = self.scor.net, device
        self.caps = caps or {}
        self.c = {"proposal_calls": 0, "latent_draws": 0, "x_unique": 0, "y_unique": 0, "batches": 0, "cache_hits": 0}
        self._x, self._y, self._p = {}, {}, {}

    def reset(self):
        self.c = {k: 0 for k in self.c}; self._x.clear(); self._y.clear(); self._p.clear()

    # ------------------------------------------------------------------ proposals
    def proposals(self, row, objs, m=4):
        import search as S
        k = (SC.key(row), tuple(objs))
        if k in self._p:
            self.c["cache_hits"] += 1
            return {o: v[:m] for o, v in self._p[k].items()}
        R = S.Root(row, "3d")
        if not objs or not R.legal_dests(R.cells0):
            self._p[k] = {o: [] for o in objs}
        else:
            gen = self.torch.Generator(device=self.samp.dev).manual_seed(0)
            D = self.samp.propose_many(R, R.cells0, list(objs), 6, gen)
            self._p[k] = {int(o): [int(d) for d in v] for o, v in D.items()}
            self.c["proposal_calls"] += 1; self.c["latent_draws"] += 64 * len(objs)
        return {o: v[:m] for o, v in self._p[k].items()}

    # ------------------------------------------------------------------ X / Y readouts
    def _cap(self, key, n):
        lim = self.caps.get(key)
        if lim is not None and self.c[key] + n > lim:
            raise CapReached(key)

    def score(self, row, seqs):
        """-> list of dicts (p11, py, px, px1, px0) per ordered seq on scene `row` (its own task).  [] -> the no-op row of that scene."""
        import xy as XY
        kr = SC.key(row)
        todo = [s for s in seqs if (kr, _sk(s)) not in self._x]
        todo = list({_sk(s): s for s in todo}.values())
        nx = sum(1 for s in todo if s)
        self._cap("x_unique", nx)
        self.c["cache_hits"] += len(seqs) - len(todo)
        for i in range(0, len(todo), 2048):
            ch = todo[i:i + 2048]
            inp = row["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(int(c))])  # noqa: E731
            xs = [[(int(o), P(d)) for o, d in s] for s in ch if s]
            v, _, xm = XY.make_view(row["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
            b, _ = XY.collate([v], device=self.dev, dtype=self.torch.float32)
            with self.torch.inference_mode():
                C = self.net.coeffs(b)
            bb, a, w = C["b"].double().cpu(), C["a"].double().cpu(), C["w"].double().cpu()
            self.c["batches"] += 1
            sig = lambda t: 1.0 / (1.0 + math.exp(-float(t)))  # noqa: E731
            k = 0
            for s in ch:
                if not s:
                    p = sig(bb[0]); self._x[(kr, _sk(s))] = {"p11": p, "py": p, "px": 1.0, "px1": 1.0, "px0": 1.0}
                    continue
                q = xm[k]; k += 1
                py, p1, p0 = sig(bb[v["parent"][q]]), sig(a[q] + w[q]), sig(a[q])
                self._x[(kr, _sk(s))] = {"p11": py * p1, "py": py, "px": py * p1 + (1 - py) * p0, "px1": p1, "px0": p0}
        self.c["x_unique"] += nx
        return [self._x[(kr, _sk(s))] for s in seqs]

    def y_global(self, row0, endpoints):
        """Y readout of each endpoint (unordered assignment [[obj, cell], ...]) from the ORIGINAL root: Y-only view, mapped edit nodes."""
        import xy as XY
        kr = SC.key(row0)
        keys = [_ek(e) for e in endpoints]
        todo = list(dict.fromkeys(k for k in keys if (kr, k) not in self._y))
        self._cap("y_unique", len(todo))
        self.c["cache_hits"] += len(keys) - len(todo)
        inp = row0["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(int(c))])  # noqa: E731
        for i in range(0, len(todo), 2048):
            ch = todo[i:i + 2048]
            edits = [{int(o): P(d) for o, d in eval(k)} for k in ch]
            v, ym, _ = XY.make_view(row0["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], edits, [], XY._NoGeo)
            b, _ = XY.collate([v], device=self.dev, dtype=self.torch.float32)
            with self.torch.inference_mode():
                C = self.net.coeffs(b)
            self.c["batches"] += 1
            for k, n in zip(ch, ym):
                self._y[(kr, k)] = 1.0 / (1.0 + math.exp(-float(C["b"][n])))
        self.c["y_unique"] += len(todo)
        return [self._y[(kr, k)] for k in keys]

    def p_noop(self, row):
        return self.score(row, [[]])[0]["p11"]


class CapReached(Exception):
    pass


def _sk(s):
    return tuple((int(o), int(d)) for o, d in s)


def _ek(e):
    return repr(tuple(sorted((int(o), int(d)) for o, d in e)))


def sync(fz):
    if fz.dev.startswith("cuda"):
        fz.torch.cuda.synchronize()
    return time.perf_counter()
