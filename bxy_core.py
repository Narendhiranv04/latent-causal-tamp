"""Approach B X/Y: exact root-consistent Boltzmann model (methodology §3.2, §4, §5.3) and its neural coefficients (§4.1, §4.3).

    E_q(x, y) = -a_q x - b_s(q) y - w_q x y                                    (one quadratic X-Y pair per X query, F5)
    P(y_S, x_Q) = prod_s P^Y(y_s) prod_q P^X(x_q | y_s(q)),   P^Y(y) = e^{b y/tau}/(1 + e^{b/tau}),  P^X(x|y) = e^{(a+w y)x/tau}/(1 + e^{(a+w y)/tau})
    L_joint = -1/N_roots sum_c log P(D_c),   unobserved X summed (= 1), unobserved Y summed, exact per unique scene s
    p_succ(q) = sigma(b_s/tau) sigma((a_q + w_q)/tau)

Neural coefficients reuse the production LB modules unchanged (abc7_models.ModelBC7('B', 'none', order='pred')): b_s = scene(scene_vec(S^s),
ctx) [F3, the LB scene unary], a_q = order_s(g_q, scene_vec(final)) [F2, LB's predecessor-aware prefix unary], J = softplus(cost(g_q))
[travel readout]; the only new module is w_q = xy(g_q, v_s(q), ctx) [F5], absent in the uncoupled arm (w = 0). No static BCE (F1 is an
analytic screen), no scene-scene / omission pair potential (F4 omissions are queries of the same scorers), no higher-order term."""
from __future__ import annotations

import itertools
import json

import torch
from torch.nn import functional as F

import abc7_models as a7
from abc_models import W, mlp

D = torch.float64
TAU = 1.0


# ------------------------------------------------------------------ exact probability model (pure tensors)
def log_py(b, y, tau=TAU):
    return y * b / tau - F.softplus(b / tau)


def log_px(a, w, x, y, tau=TAU):
    u = a + w * y
    return x * u / tau - F.softplus(u / tau)


def log_evidence(b, a, w, parent, obs_y, obs_x, tau=TAU):
    """log P(D_c): per unique scene s, logsumexp over its allowed y of [log P^Y(y) + sum over observed children log P^X(x_q | y)].
    Scenes with neither an observation nor an observed child contribute exactly 0; unobserved X contribute exactly 0."""
    kids = {}
    for q, x in obs_x.items():
        kids.setdefault(parent[q], []).append((q, x))
    tot = b.new_zeros(())
    for s in sorted(set(obs_y) | set(kids)):
        ys = [obs_y[s]] if s in obs_y else [0, 1]
        terms = [log_py(b[s], y, tau) + sum((log_px(a[q], w[q], x, y, tau) for q, x in kids.get(s, [])), b.new_zeros(())) for y in ys]
        tot = tot + torch.logsumexp(torch.stack(terms), 0)
    return tot


def marginals(b, a, w, parent, tau=TAU) -> dict:
    """Prior (no evidence) P(Y_s = 1), P(X_q = 1) (Y marginalized, never conditioned on a revealed Y) and p_succ(q) = P(X_q = 1, Y_s(q) = 1)."""
    py = torch.sigmoid(b / tau)
    pb = py[parent] if len(parent) else py.new_zeros(0)
    p1, p0 = torch.sigmoid((a + w) / tau), torch.sigmoid(a / tau)
    return {"py": py, "px": pb * p1 + (1 - pb) * p0, "psucc": pb * p1}


def energy_root(b, a, w, parent, y, x, tau=TAU):
    """Root-normalized energy E_root(x, y) (§4.2) of one full assignment; P = exp(-E_root / tau)."""
    e = sum(-b[s] * y[s] + tau * F.softplus(b[s] / tau) for s in range(len(b)))
    for q in range(len(a)):
        u = a[q] + w[q] * y[parent[q]]
        e = e + (-u * x[q] + tau * F.softplus(u / tau))
    return e


def brute_force(b, a, w, parent, obs_y, obs_x, tau=TAU) -> float:
    """Reference log P(D) by enumerating every joint state through E_root (tiny roots only)."""
    nY, nX, out = len(b), len(a), []
    for y in itertools.product((0, 1), repeat=nY):
        if any(y[s] != v for s, v in obs_y.items()):
            continue
        for x in itertools.product((0, 1), repeat=nX):
            if any(x[q] != v for q, v in obs_x.items()):
                continue
            out.append(-energy_root(b, a, w, parent, y, x, tau) / tau)
    return float(torch.logsumexp(torch.stack(out), 0))


# ------------------------------------------------------------------ neural coefficients
class ModelXY(a7.ModelBC7):
    """Production LB modules + one restricted quadratic coupling head (coupled=True) and the travel readout."""

    def __init__(self, coupled=True):
        super().__init__("B", "none", order="pred")
        self.coupled = coupled
        if coupled:
            self.xy = mlp(3 * W, 1)

    def coeffs(self, rt):
        """b over rt['y_poses'], a / w over rt['x_seqs'] (parent rt['parent']), J over rt['j_seqs']; one memoized pass per root."""
        R = rt["R"]
        self._memo = {}
        try:
            c = self.ctxn(R.ctx)
            v = [self.memo(("v", tuple(sorted(p.items()))), lambda p=p: self.scene_vec(R, self.edited(R, p))) for p in rt["y_poses"]]
            b = torch.stack([self.scene(torch.cat([x, c]))[0] for x in v]) if v else torch.zeros(0, dtype=D)
            a, w = [], []
            for seq, s in zip(rt["x_seqs"], rt["parent"]):
                sq, g, _ = self.order(R, seq)
                a.append(sq)
                w.append(self.xy(torch.cat([g, v[s], c]))[0] if self.coupled else torch.zeros((), dtype=D))
            J = [F.softplus(self.cost(self.order(R, seq)[1])[0]) for seq in rt["j_seqs"]]
        finally:
            self._memo = None
        z = torch.zeros(0, dtype=D)
        return b, (torch.stack(a) if a else z), (torch.stack(w) if w else z), (torch.stack(J) if J else z)


ARMS = {"XY-uncoupled": False, "XY-quadratic": True, "XY-quadratic-noJ": True}


def build(arm):
    """Double precision, like production LB (p17_b.model)."""
    return ModelXY(coupled=ARMS[arm]).double()


# ------------------------------------------------------------------ root views over the LB records + BXY sidecar
def parse(key):
    """Y / X key -> [(object, cell)] (canonical keys: 'X:root:o>c.o>c', 'empty')."""
    body = key.split(":", 2)[2]
    return [] if body == "empty" else [(p.split(">")[0], int(p.split(">")[1])) for p in body.split(".")]


def views(split, full=False, records="runs/approach_b/bd2d_lb_v1/RECORDS.pt", side="runs/approach_b/bxy/SIDECAR.json") -> list:
    """Per root: tensors (am.Root of the LB record), the X / Y variables (observed-relevant only for training; every catalogue prefix,
    omission and endpoint with full=True; exact: unobserved leaves marginalize to 1), observations, travel items, catalogue."""
    import abc_models as am
    import bxy_data as bd
    from scene import scene_from_dict
    S, R = json.loads(open(side).read()), bd.roots()
    out = []
    for rec in torch.load(records, weights_only=False)["roots"]:
        k = rec["audit"]["root"]
        if rec["audit"]["split"] != split:
            continue
        sc, ids, lat = S[k], rec["audit"]["ids"], scene_from_dict(R[k]["scene"]).lattice
        xk = sorted(sc["x_vars"]) if full else sorted(sc["x_obs"])
        yk = sorted(set(sc["y_vars"]) | set(sc["y_obs"])) if full else sorted(set(sc["y_obs"]) | {sc["x_to_y"][q] for q in xk})
        yi = {q: i for i, q in enumerate(yk)}
        tseq = [c for c in sc["catalogue"] if c["seq"] and c["y_full"] == 1 and c["travel"] is not None]
        enc = lambda pairs: [(ids.index(o), tuple(lat.center(c))) for o, c in pairs]  # noqa: E731
        out.append({"key": k, "R": am.Root(rec), "ids": ids, "y_keys": yk, "x_keys": xk,
                    "y_poses": [{ids.index(o): tuple(lat.center(c)) for o, c in parse(q)} for q in yk],
                    "x_seqs": [enc(parse(q)) for q in xk], "parent": [yi[sc["x_to_y"][q]] for q in xk],
                    "obs_y": {yi[q]: v["y"] for q, v in sc["y_obs"].items() if q in yi}, "obs_x": {i: sc["x_obs"][q]["y"] for i, q in enumerate(xk) if q in sc["x_obs"]},
                    "j_seqs": [enc(c["seq"]) for c in tseq], "j_obs": [c["travel"] for c in tseq], "catalogue": sc["catalogue"],
                    "verified_K": R[k]["verified_K"], "cells0": bd.cells0(R[k])})
    return out


def root_loss(m, rt, lam_j, tau=TAU):
    b, a, w, J = m.coeffs(rt)
    nll = -log_evidence(b, a, w, rt["parent"], rt["obs_y"], rt["obs_x"], tau)
    tr = F.huber_loss(torch.log1p(J), torch.log1p(torch.tensor(rt["j_obs"], dtype=D))) if len(J) and lam_j else None
    return nll, tr


def total(m, roots, lam_j, tau=TAU):
    """L_B = L_joint (root mean) + lam_J L_J (mean over roots with a witnessed complete travel)."""
    per = [root_loss(m, r, lam_j, tau) for r in roots]
    nll = torch.stack([p[0] for p in per]).mean()
    trs = [p[1] for p in per if p[1] is not None]
    tr = torch.stack(trs).mean() if trs else None
    return nll + (lam_j * tr if tr is not None else 0.0), {"nll": float(nll.detach()), "travel": float(tr.detach()) if tr is not None else None}
