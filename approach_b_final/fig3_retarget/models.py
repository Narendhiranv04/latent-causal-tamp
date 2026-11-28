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
        """Production: S1 top-m (default m = 4, prop_mode 'S1').  R5.3 opt-in modes (never the production default; self.prop_mode):
        'TOP8' top-8 of the same marginal; 'ANC64' top-4 + the 4 most frequent other cells of 64 ancestral latent draws per object (bounded
        local resampling); 'UNIF' top-4 + 4 uniformly random legal cells seeded by the scene (labelled exploration control)."""
        mode = getattr(self, "prop_mode", "S1")
        if mode != "S1":
            return self._proposals_mode(row, objs, mode)
        return self._s1(row, objs, m)

    def _s1(self, row, objs, m=4):
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

    def _proposals_mode(self, row, objs, mode):
        import collections, hashlib, random
        k = (mode, V.skey(row), tuple(objs))
        if k in self._p:
            self.c["cache_hits"] += 1
            return self._p[k]
        base = {o: list(v) for o, v in self._s1(row, objs, 6).items()}
        if mode == "TOP8":                                                 # top-8 needs the 8-wide marginal (S1 caches top-6)
            sys.path.insert(0, str(HERE / "kgt3"))
            import cover as CV
            P, legal, _, _ = CV.marg(self, row, list(objs))
            base = {o: (CV.ranking(P[o], legal)[:8] if P.get(o) is not None else []) for o in objs}
        if mode == "TOP8":
            out = base
        elif mode == "ANC64":
            sys.path.insert(0, str(HERE / "kgt3"))
            import cover as CV
            P, legal, U, ev = CV.marg(self, row, list(objs), anc=(64,))
            self.c["latent_draws"] += 64 * len(objs)
            out = {}
            for o in objs:
                cnt = collections.Counter(d for d in (U.get(64, {}).get(o) or []) if d not in base[o][:4])
                out[o] = (base[o][:4] + [d for d, _ in sorted(cnt.items(), key=lambda t: (-t[1], t[0]))[:4]]) if base[o] else []
        elif mode == "UNIF":
            import search as S
            R = S.Root(row, self.dom); legal = R.legal_dests(R.cells0)
            rng = random.Random(hashlib.sha256(("UNIF|" + V.skey(row)).encode()).hexdigest())
            out = {o: base[o][:4] + rng.sample([d for d in legal if d not in base[o][:4]], min(4, len([d for d in legal if d not in base[o][:4]]))) if base[o] else [] for o in objs}
        elif mode in ("CR4", "CR8"):                                       # R10.7: complete-repair cVAE proposals (count-matched to S1 / ANC64)
            out = self._cr(row, list(objs), 4 if mode == "CR4" else 8)
        else:
            raise ValueError(mode)
        self._p[k] = {int(o): [int(d) for d in v] for o, v in out.items()}
        return self._p[k]

    def _cr(self, row, objs, M, budget=256):
        """R10.7: per-object destinations ranked by frequency over the CR cVAE's complete-repair hypotheses (<= 3 actions) sampled at THIS public
        (possibly hypothetical / retargeted) scene; ties by cell.  Model = env R10_CR_MODEL; the same 256-sample budget as the R8A CR arms."""
        import collections, os
        if getattr(self, "_crm", None) is None:
            sys.path.insert(0, str(HERE.parent / "complete_repair_cvae"))
            import infer as INF
            self._crm = INF.load_cr(os.environ["R10_CR_MODEL"], self.dev)[0]
        import infer as INF
        import data as CRD
        b1 = INF.enc_t(self.dom, row, self.dev, CRD.scalers(self.dom))
        P = INF.make_pool(self._crm, self.dom, row, b1, budget, 0)
        seqs, _ = INF.prefix(P, budget)
        self.c["latent_draws"] += budget; self.c.setdefault("cr_pools", 0); self.c["cr_pools"] += 1
        cnt = {o: collections.Counter() for o in objs}
        for s_ in seqs:
            for o, d in s_:
                if int(o) in cnt:
                    cnt[int(o)][int(d)] += 1
        return {o: [d for d, _ in sorted(cnt[o].items(), key=lambda t: (-t[1], t[0]))[:M]] for o in objs}

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
