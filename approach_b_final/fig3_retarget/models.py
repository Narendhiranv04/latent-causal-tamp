"""Frozen per-domain bundle behind counted, cached readouts (same math as compose3d_k45.models, domain-parametrized).
S1 TaskCVAE proposals via search.Sampler.propose_many (top-6 with a fresh CUDA generator seeded 0, D4 = prefix, = exhaustive.proposals);
X/Y coefficients from the frozen coupled scorer (xy.make_view / collate / XYNet.coeffs): pY = s(b), pX1 = s(a + w), pX0 = s(a),
pX = pY pX1 + (1 - pY) pX0, p11 = pY pX1.  Y_global(E) = mapped edit node of a Y-only view of the ORIGINAL root.  Caches are keyed by the
full scene inputs (task, poses, roles, legal cells) and the ordered sequence; every unique readout is counted once."""
from __future__ import annotations

import math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
import views as V  # noqa: E402

BUNDLE = Path(os.environ.get("FIG3_BUNDLE", Path.home() / "abf_v34/approach_b_bundle"))


class CapReached(Exception):
    pass


class Frozen:
    def __init__(self, dom, device="cuda"):
        import benchmark as BM
        import torch
        self.torch, self.dom = torch, dom
        self.samp, self.scor, self.man = BM.load_bundle(BUNDLE, dom, device, 0)          # hash-checked per-domain bundle
        self.net, self.dev = self.scor.net, device
        self.caps = {}
        self.reset()

    def reset(self):
        self.c = {"proposal_calls": 0, "latent_draws": 0, "x_unique": 0, "y_unique": 0, "batches": 0, "cache_hits": 0}
        self._x, self._y, self._p = {}, {}, {}

    def _cap(self, k, n):
        lim = self.caps.get(k)
        if lim is not None and self.c[k] + n > lim:
            raise CapReached(k)

    def proposals(self, row, objs, m=4):
        import search as S
        k = (V.skey(row), tuple(objs))
        if k not in self._p:
            R = S.Root(row, self.dom)
            if not objs or not R.legal_dests(R.cells0):
                self._p[k] = {o: [] for o in objs}
            else:
                gen = self.torch.Generator(device=self.samp.dev).manual_seed(0)
                D = self.samp.propose_many(R, R.cells0, list(objs), 6, gen)
                self._p[k] = {int(o): [int(d) for d in v] for o, v in D.items()}
                self.c["proposal_calls"] += 1; self.c["latent_draws"] += 64 * len(objs)
        else:
            self.c["cache_hits"] += 1
        return {o: v[:m] for o, v in self._p[k].items()}

    def score(self, row, seqs):
        import xy as XY
        kr = V.skey(row)
        todo = list({_sk(s): s for s in seqs if (kr, _sk(s)) not in self._x}.values())
        nx = sum(1 for s in todo if s)
        self._cap("x_unique", nx)
        self.c["cache_hits"] += len(seqs) - len(todo)
        sig = lambda t: 1.0 / (1.0 + math.exp(-float(t)))  # noqa: E731
        inp = row["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(int(c))])  # noqa: E731
        for i in range(0, len(todo), 2048):
            ch = todo[i:i + 2048]
            xs = [[(int(o), P(d)) for o, d in s] for s in ch if s]
            v, _, xm = XY.make_view(row["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [], xs, XY._NoGeo)
            b, _ = XY.collate([v], device=self.dev, dtype=self.torch.float32)
            with self.torch.inference_mode():
                C = self.net.coeffs(b)
            bb, a, w = C["b"].double().cpu(), C["a"].double().cpu(), C["w"].double().cpu()
            self.c["batches"] += 1
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
        import xy as XY
        kr = V.skey(row0)
        keys = [_ek(e) for e in endpoints]
        todo = list(dict.fromkeys(k for k in keys if (kr, k) not in self._y))
        self._cap("y_unique", len(todo))
        self.c["cache_hits"] += len(keys) - len(todo)
        inp = row0["inputs"]; P = lambda c: tuple(inp["cell_xy"][str(int(c))])  # noqa: E731
        for i in range(0, len(todo), 2048):
            ch = todo[i:i + 2048]
            edits = [{int(o): P(d) for o, d in k} for k in ch]
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


def _sk(s):
    return tuple((int(o), int(d)) for o, d in s)


def _ek(e):
    return tuple(sorted((int(o), int(d)) for o, d in e))


def sync(fz):
    if str(fz.dev).startswith("cuda"):
        fz.torch.cuda.synchronize()
    return time.perf_counter()
