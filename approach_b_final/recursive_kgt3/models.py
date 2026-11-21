#!/usr/bin/env python3
"""Frozen-model adapters (AUDIT A2/A3/A14): one interface used by the planner, implemented by
  Frozen  -- the hash-checked bundle (task cVAE s0 sampler, D scorer s0), DynPad active; nothing re-implemented
  Random  -- the matched control: uniform random legal destinations, random local scores, random temporary-task gates; the SAME final
             energy (frozen h_Y, h_X) is used to choose among its candidates (isolates learned guidance DURING search)
Interface (all object indices are S0 indices):
  propose(hr)            -> {obj: [<=4 dests]}   frozen: S1 top-6 marginal, rank < 4 (= frozen benchmark proposals)
  score(hr, seqs)        -> [{p11, py, px}]       local K<=3 scores in the HypoRoot view (rebased S_p, task view)
  ytask(hr)              -> P(Y=1) of the view's task in its current scene (p_noop) -- temporary-target feasibility signal
  y_end(row0, seqs)      -> [h_Y]   ORIGINAL task Y-only endpoint relative to S0 (y_edits on the original root; no X order head)
  x_chunk(hr, seq)       -> marginal px of a <=3 chunk in its pre-scene (original task view)"""
import hashlib, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import data as DA  # noqa: E402

BUNDLE = Path.home() / "abf_v34/approach_b_bundle"


def _seed(*a):
    return int(hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()[:8], 16)


class Counters(dict):
    def inc(self, k, n=1):
        self[k] = self.get(k, 0) + n


class Frozen:
    name = "frozen"

    def __init__(self, device="cuda", scorer_seed=0):
        import torch
        import benchmark as BM
        DA.enable_dynpad()
        self.torch = torch
        self.samp, self.scor, self.man = BM.load_bundle(BUNDLE, "2d", device, scorer_seed)   # check=True: hashes asserted
        self.dev, self.c = device, Counters()
        self._prop, self._sc, self._yend = {}, {}, {}

    @staticmethod
    def _key(hr):
        return (tuple(hr.cells0), hr.tid, hr.goal, tuple(hr.movable))

    def propose(self, hr):
        k = self._key(hr)
        if k not in self._prop:
            gen = self.torch.Generator(device=self.samp.dev).manual_seed(_seed("PROP", hr.id.split("~")[0], *k[0], hr.tid, hr.goal))
            D = self.samp.propose_many(hr, hr.cells0, list(hr.movable), 6, gen) if hr.movable else {}
            self._prop[k] = {int(o): [int(d) for d in v][:4] for o, v in D.items()}
            self.c.inc("cvae_queries", len(hr.movable)); self.c.inc("cvae_raw_draws", 64 * len(hr.movable))
        return self._prop[k]

    def score(self, hr, seqs, chunk=8192):
        base = self._key(hr)
        todo = [s for s in seqs if (base, tuple(s)) not in self._sc]
        for i in range(0, len(todo), chunk):
            part = todo[i:i + chunk]
            for s, r in zip(part, self.scor.score(hr, [list(x) for x in part])):
                self._sc[(base, tuple(s))] = {"p11": r["p11"], "py": r.get("py"), "px": r.get("px")}
            self.c.inc("local_scored", len(part))
        return [self._sc[(base, tuple(s))] for s in seqs]

    def ytask(self, hr):
        k = (self._key(hr), ())
        if k not in self._sc:
            self._sc[k] = {"p11": self.scor.score(hr, [[]])[0]["p11"]}
            self.c.inc("ytask_probes")
        return self._sc[k]["p11"]

    def y_end(self, row0, seqs):
        import xy as XY
        inp = row0["inputs"]
        keys = [tuple(sorted((int(i), int(d)) for i, d in s)) for s in seqs]
        todo = sorted({k for k in keys if (row0["root_id"], k) not in self._yend and k})
        for i in range(0, len(todo), 512):
            part = todo[i:i + 512]
            eds = [{a: tuple(inp["cell_xy"][str(d)]) for a, d in k} for k in part]
            v, ym, _ = XY.make_view(row0["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], eds, [], XY._NoGeo)
            b, _ = XY.collate([v], device=self.dev, dtype=self.torch.float32)
            with self.torch.no_grad():
                pr = self.scor.net.predict(b)
            for k, n in zip(part, ym):
                self._yend[(row0["root_id"], k)] = float(pr["py"][n])
            self.c.inc("yend_probes", len(part))
        out = []
        for k in keys:
            out.append(self._yend[(row0["root_id"], k)] if k else self.y_noop(row0))
        return out

    def y_noop(self, row0):
        k = ("NOOP", row0["root_id"])
        if k not in self._yend:
            hr = DA.HypoRoot(row0)
            self._yend[k] = self.scor.score(hr, [[]])[0]["p11"]
        return self._yend[k]

    def x_chunk(self, hr, seq):
        return self.score(hr, [seq])[0]["px"]


class Random(Frozen):
    """Matched uniform-random control: proposals, local scores and temporary-task gates are random (seeded per call); y_end / x_chunk stay
    frozen so the FINAL choice among its candidates uses the same learned energy as the recursive arm."""
    name = "random"

    def propose(self, hr):
        k = self._key(hr)
        if k not in self._prop:
            rng = random.Random(_seed("RPROP", hr.id.split("~")[0], *k[0], hr.tid, hr.goal))
            legal = hr.legal_dests(hr.cells0)
            self._prop[k] = {o: rng.sample(legal, min(4, len(legal))) for o in hr.movable}
            self.c.inc("cvae_queries", 0)
        return self._prop[k]

    def score(self, hr, seqs, chunk=8192):
        base = self._key(hr)
        out = []
        for s in seqs:
            kk = (base, tuple(s))
            if kk not in self._sc:
                r = random.Random(_seed("RSC", hr.id.split("~")[0], kk)).random()
                self._sc[kk] = {"p11": r, "py": r, "px": r}
                self.c.inc("local_scored")
            out.append(self._sc[kk])
        return out

    def ytask(self, hr):
        k = (self._key(hr), ())
        if k not in self._sc:
            self._sc[k] = {"p11": random.Random(_seed("RYT", hr.id.split("~")[0], k)).random()}
            self.c.inc("ytask_probes")
        return self._sc[k]["p11"]

    def x_chunk(self, hr, seq):                      # frozen px, separate cache (never the random local scores)
        k = (self._key(hr), tuple(seq))
        if not hasattr(self, "_xc"):
            self._xc = {}
        if k not in self._xc:
            self._xc[k] = self.scor.score(hr, [list(seq)])[0]["px"]
            self.c.inc("xchunk_frozen")
        return self._xc[k]
