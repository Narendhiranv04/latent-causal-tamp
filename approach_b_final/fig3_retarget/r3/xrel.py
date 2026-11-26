#!/usr/bin/env python3
"""R3.3 conditional X encoders (only trained if the R3.2 gate fails on adequate data).  Y = frozen F0 path (bitwise); same X/Y factorization:
P(Y) = s(b), P(X | Y = y) = s(a + w y); the new module only emits a, w.

Per query (ordered chunk) and step t, the scene is the IDEAL prefix within the chunk (previous actions of the chunk applied), q_ref in ctx.
Node features (learner-visible only): xy, attrs, base / goal / target relations (xy.XYNet.numeric), role flags [moved-now, destination,
target], and query-relative geometry [dx, dy, |d|] to the moved object and to its destination.  The destination is one extra node.
  G1  two query-conditioned relational attention layers over all nodes; edge features = [dx, dy, |d|, attr_j - attr_i]
  M1  capacity-matched control: identical node features (incl. query-relative geometry), per-node MLP, NO message passing
Step token = mlp([h(moved), h(dest), mean / max pool, t]); predecessor mixer over u < t (as F0 'pred'); a = mlp([g, pooled end scene]);
w = mlp([g, v_parent, c]) with v_parent / c from the frozen F0 Y encoder (inputs only, detached).  Permutation-equivariant in object index;
order-sensitive in actions; no labels, witnesses, K, teacher traces or future-prefix information in any input."""
from __future__ import annotations

import torch
from torch import nn

H = 128


def mlp(i, o, h=H):
    return nn.Sequential(nn.Linear(i, h), nn.SiLU(), nn.Linear(h, o))


class RelLayer(nn.Module):
    def __init__(self, e_dim):
        super().__init__()
        self.q, self.k, self.v = nn.Linear(H, H), nn.Linear(H, H), nn.Linear(H, H)
        self.eb, self.ev = mlp(e_dim, 1, 64), nn.Linear(e_dim, H)
        self.up = mlp(2 * H, H)

    def forward(self, h, e, mask):
        att = (self.q(h)[:, :, None] * self.k(h)[:, None]).sum(-1) / H ** 0.5 + self.eb(e)[..., 0]
        att = att.masked_fill(~mask[:, None, :], -1e9).softmax(-1)
        agg = (att[..., None] * (self.v(h)[:, None] + self.ev(e))).sum(2)
        return h + self.up(torch.cat([h, agg], -1))


class XRel(nn.Module):
    def __init__(self, kind, attr_dim):
        super().__init__()
        self.kind, self.A = kind, attr_dim
        self.node = mlp(11 + attr_dim + 3 + 6, H)
        self.layers = nn.ModuleList([RelLayer(3 + attr_dim) for _ in range(2)]) if kind == "G1" else nn.ModuleList()
        if kind == "M1":                                                   # capacity match: deeper per-node MLP instead of message passing
            self.extra = nn.Sequential(mlp(H, H, 384), nn.SiLU(), mlp(H, H, 384))
        self.tok, self.pairo, self.mix = mlp(3 * H + 1, H), mlp(2 * H, H), mlp(2 * H, H)
        self.end = mlp(11 + attr_dim, H)
        self.ha, self.hw = mlp(3 * H, 1), mlp(3 * H, 1)

    @staticmethod
    def numeric(b, xy, attrs, ri, tgt):
        """xy.XYNet.numeric with explicit attrs / target position (used for object nodes and the destination node)."""
        rel = lambda p: torch.cat([xy - p, (xy - p).norm(dim=-1, keepdim=True)], -1)  # noqa: E731
        d = xy - b["base"][ri][:, None]
        ang = torch.atan2(d[..., 1], d[..., 0])
        return torch.cat([xy, attrs, d.norm(dim=-1, keepdim=True), ang.sin()[..., None], ang.cos()[..., None], rel(b["goal"][ri][:, None]), rel(tgt)], -1)

    def embed(self, base, b, xy, ri, qi, dest):
        """Node embeddings [Q, N+1, H] at scene xy [Q, N, 2] for moved object index qi [Q] going to dest [Q, 2]."""
        Q, N = xy.shape[:2]
        ar = torch.arange(Q, device=xy.device)
        attrs = b["attrs"][ri]
        tgt = xy[ar, b["tid"][ri]][:, None]
        num = self.numeric(b, xy, attrs, ri, tgt)                                           # [Q, N, 11 + A]
        dnum = self.numeric(b, dest[:, None], attrs[ar, qi][:, None], ri, tgt)              # destination node: moved body's attrs at dest
        allxy = torch.cat([xy, dest[:, None]], 1)
        nodes = torch.cat([num, dnum], 1)
        flags = torch.zeros(Q, N + 1, 3, device=xy.device, dtype=xy.dtype)
        flags[ar, qi, 0] = 1.0; flags[:, -1, 1] = 1.0; flags[ar, b["tid"][ri], 2] = 1.0
        rel = lambda p: torch.cat([allxy - p[:, None], (allxy - p[:, None]).norm(dim=-1, keepdim=True)], -1)  # noqa: E731
        h = self.node(torch.cat([nodes, flags, rel(xy[ar, qi]), rel(dest)], -1))
        mask = torch.cat([b["omask"][ri], torch.ones(Q, 1, dtype=torch.bool, device=xy.device)], 1)
        if self.kind == "G1":
            d = allxy[:, None] - allxy[:, :, None]
            at = torch.cat([attrs, attrs[ar, qi][:, None]], 1)
            e = torch.cat([d, d.norm(dim=-1, keepdim=True), at[:, None] - at[:, :, None]], -1)
            for L in self.layers:
                h = L(h, e, mask)
        else:
            h = h + self.extra(h)
        return h, mask

    def forward(self, base, b, v_parent, c_root):
        ri, obj, dest, Lq = b["q_root"], b["q_obj"], b["q_dest"], b["q_len"]
        Q, M = obj.shape
        ar = torch.arange(Q, device=obj.device)
        xy, toks = b["xy0"][ri].clone(), []
        for t in range(M):
            on = (t < Lq)
            i = obj[:, t].clamp(min=0)
            h, mask = self.embed(base, b, xy, ri, i, dest[:, t])
            m = mask[..., None]
            pool = (h * m).sum(1) / m.sum(1)
            toks.append(self.tok(torch.cat([h[ar, i], h[:, -1], pool, xy.new_full((Q, 1), float(t))], -1)))
            xy2 = xy.clone()
            xy2[ar, i] = torch.where(on[:, None], dest[:, t], xy[ar, i])
            xy = xy2
        toks = torch.stack(toks, 1)
        valid = torch.arange(M, device=obj.device)[None] < Lq[:, None]
        P = self.pairo(torch.cat([toks[:, None].expand(Q, M, M, H), toks[:, :, None].expand(Q, M, M, H)], -1))
        t_, u_ = torch.arange(M, device=obj.device)[:, None], torch.arange(M, device=obj.device)[None]
        allow = (u_ < t_)[None] & valid[:, None, :]
        pm = (P * allow[..., None]).sum(2) / allow.sum(-1, keepdim=True).clamp(min=1)
        rows = self.mix(torch.cat([toks, pm], -1))
        g = (rows * valid[..., None]).sum(1) / Lq[:, None].clamp(min=1)
        en = self.end(self.numeric(b, xy, b["attrs"][ri], ri, xy[ar, b["tid"][ri]][:, None]))
        om = b["omask"][ri][..., None]
        ep = torch.cat([(en * om).sum(1) / om.sum(1), en.masked_fill(~om, -1e9).max(1).values], -1)
        a = self.ha(torch.cat([g, ep], -1))[:, 0]
        w = self.hw(torch.cat([g, v_parent, c_root], -1))[:, 0]
        return a, w


class ScalingNet(nn.Module):
    """coeffs() drop-in for xy.XYNet: b from the frozen F0 Y path, (a, w) from the X module.  J heads are not used by any R3 decision."""
    def __init__(self, base, xmod):
        super().__init__()
        self.base, self.x = base, xmod
        for p in self.base.parameters():
            p.requires_grad_(False)
        self.arm, self.cfg = xmod.kind, base.cfg

    def coeffs(self, b):
        B = self.base
        c = B.ctxn(b["ctx"])
        v = B.scene_vec(b, b["s_xy"], b["s_root"])
        bb = B.scene(torch.cat([v, c[b["s_root"]]], -1))[:, 0]
        z = bb.new_zeros(len(b["q_root"]))
        if len(b["q_root"]) == 0:
            return {"b": bb, "a": z, "w": z, "J": z, "J0": bb.new_zeros(b["n_roots"])}
        a, w = self.x(B, b, v[b["parent"]].detach(), c[b["q_root"]].detach())
        return {"b": bb, "a": a, "w": w, "J": z, "J0": bb.new_zeros(b["n_roots"])}


def build(arm, base):
    A = base.enc[0].in_features - 11 - base.vis_dim
    return ScalingNet(base, XRel(arm, A).to(next(base.parameters()).device).to(next(base.parameters()).dtype))
