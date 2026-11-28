#!/usr/bin/env python3
"""Complete-repair cVAE (plan.md 4): one shared latent z, an autoregressive pointer decoder over the scene's object tokens and grid cells,
an order-sensitive posterior (training only) and a small integrated root decision head (NOOP / REPAIR / ABSTAIN) on the same scene embedding.

    p(r | c, z) = prod_{t<k} p(o_t | c, z, r_<t) p(d_t | o_t, c, z, r_<t) * p(STOP | c, z, r_<=k)      (STOP forced, prob. 1, at k = 3)

Static grammar masks only (no physical check): an object is eligible iff movable (non-target, non-fixed, real token), not moved yet, and at
least one destination is still available; a destination is available iff it is a declared support cell, not occupied in S0, not the goal and
not reserved by an earlier action.  STOP is illegal at t = 0, legal at t = 1, 2, forced when nothing is eligible or at t = 3.  A root with
nothing eligible at t = 0 yields an explicit no-candidate (length 0), never a draw from all -inf logits."""
from __future__ import annotations

import math

import torch
from torch import nn
from torch.nn import functional as Fn

from data import GRID, KMAX, NCELL, NTOK, glob_dim

NEG = -1e9


def mlp(i, h, o, n=2):
    layers, d = [], i
    for _ in range(n):
        layers += [nn.Linear(d, h), nn.SiLU()]
        d = h
    return nn.Sequential(*layers, nn.Linear(d, o))


class CRCVAE(nn.Module):
    def __init__(self, dom, h=128, z=8):
        super().__init__()
        R, C = GRID[dom]
        self.dom, self.N, self.h, self.zdim = dom, R * C, h, z
        self.tok, self.glob = mlp(NTOK, h, h), mlp(glob_dim(dom), h, h, 1)
        self.scene, self.tokc = mlp(3 * h, h, h, 1), mlp(2 * h, h, h, 1)
        self.cellm, self.cellc = mlp(NCELL, h, h), nn.Linear(h, h)
        self.dec0 = mlp(h + z, h, h, 1)
        self.gru = nn.GRUCell(2 * h + z + KMAX, h)
        self.objh, self.stoph, self.dsth = mlp(2 * h, h, 1, 1), mlp(h, h, 1, 1), mlp(2 * h, h, h, 1)
        self.post_gru = nn.GRU(2 * h + KMAX + 1, h, batch_first=True)
        self.post = mlp(2 * h, h, 2 * z, 1)
        self.gate = mlp(h, h, 3, 1)

    # -------------------------------------------------------------------------------------------- encoder (permutation-equivariant tokens)
    def encode(self, b):
        """b: dict of tensors tok [B,O,NTOK], tmask [B,O], cell [B,N,NCELL], glob [B,G] -> c [B,h], tokens [B,O,h], cells [B,N,h]."""
        m = b["tmask"]
        e = self.tok(b["tok"]) * m[..., None]
        cnt = m.sum(1, keepdim=True).clamp(min=1)
        mean = e.sum(1) / cnt
        mx = e.masked_fill(~m[..., None], NEG).max(1).values
        c = self.scene(torch.cat([mean, mx, self.glob(b["glob"])], -1))
        T = self.tokc(torch.cat([e, c[:, None].expand_as(e)], -1)) * m[..., None]
        Ce = self.cellm(b["cell"]) + self.cellc(c)[:, None]
        return c, T, Ce

    def decision_logits(self, c):
        return self.gate(c)

    # -------------------------------------------------------------------------------------------- one decoder step
    def _step(self, hs, T, Ce, movable, legal0, moved, reserved, t):
        """-> (logits over [objects..., STOP] [B,O+1], eligible-any [B], forced-stop [B])."""
        avail = legal0 & ~reserved
        elig = movable & ~moved & avail.any(1, keepdim=True)
        lo = self.objh(torch.cat([hs[:, None].expand(-1, T.shape[1], -1), T], -1)).squeeze(-1).masked_fill(~elig, NEG)
        ls = self.stoph(hs)
        if t == 0:
            ls = torch.full_like(ls, NEG)
        any_e = elig.any(1)
        return torch.cat([lo, ls], 1), any_e, (~any_e) & (t > 0)

    def _dest_logits(self, hs, T, Ce, o, legal0, reserved):
        to = T[torch.arange(T.shape[0], device=T.device), o]
        q = self.dsth(torch.cat([hs, to], -1))
        return ((Ce * q[:, None]).sum(-1) / math.sqrt(self.h)).masked_fill(~(legal0 & ~reserved), NEG), to

    def _advance(self, hs, to, Ce, d, z, t):
        B = hs.shape[0]
        cd = Ce[torch.arange(B, device=hs.device), d]
        oh = Fn.one_hot(torch.full((B,), t, device=hs.device), KMAX).float()
        return self.gru(torch.cat([to, cd, z, oh], -1), hs)

    def h0(self, c, z):
        return torch.tanh(self.dec0(torch.cat([c, z], -1)))

    # -------------------------------------------------------------------------------------------- teacher-forced likelihood
    def logp(self, c, T, Ce, movable, legal0, z, obj, dst, n):
        """Exact log p(r | c, z) of given ordered sequences (teacher forcing) -> (total [B], parts {obj, cell, stop} [B])."""
        B, O = movable.shape
        dev = c.device
        hs = self.h0(c, z)
        moved, reserved = torch.zeros_like(movable), torch.zeros_like(legal0)
        lo_, lc_, lst_ = (torch.zeros(B, device=dev) for _ in range(3))
        ar = torch.arange(B, device=dev)
        for t in range(KMAX):
            logits, any_e, forced = self._step(hs, T, Ce, movable, legal0, moved, reserved, t)
            lsm = logits.log_softmax(-1)
            act, stop = t < n, t == n
            o, d = obj[:, t], dst[:, t]
            lo_ = lo_ + torch.where(act, lsm[ar, o], torch.zeros_like(lo_))
            lst_ = lst_ + torch.where(stop & ~forced, lsm[:, O], torch.zeros_like(lst_))
            dl, to = self._dest_logits(hs, T, Ce, o, legal0, reserved)
            lc_ = lc_ + torch.where(act, dl.log_softmax(-1)[ar, d], torch.zeros_like(lc_))
            hn = self._advance(hs, to, Ce, d, z, t)
            hs = torch.where(act[:, None], hn, hs)
            moved = moved | (Fn.one_hot(o, O).bool() & act[:, None])
            reserved = reserved | (Fn.one_hot(d, self.N).bool() & act[:, None])
        return lo_ + lc_ + lst_, {"obj": lo_, "cell": lc_, "stop": lst_}

    def posterior(self, c, T, Ce, obj, dst, n):
        """q(z | c, r): GRU over (object token, destination cell, position) then a STOP token; hidden at the STOP position + c -> mu, logvar."""
        B = c.shape[0]
        ar = torch.arange(B, device=c.device)
        xs = []
        for t in range(KMAX + 1):
            if t < KMAX:
                act = (t < n).float()[:, None]
                tok = torch.cat([T[ar, obj[:, t]], Ce[ar, dst[:, t]], Fn.one_hot(torch.full((B,), t, device=c.device), KMAX).float(),
                                 torch.zeros(B, 1, device=c.device)], -1) * act
            else:
                tok = torch.zeros(B, 2 * self.h + KMAX + 1, device=c.device)
            stop = (n == t).float()[:, None]
            tok = tok * (1 - stop) + stop * torch.cat([torch.zeros(B, 2 * self.h + KMAX, device=c.device), torch.ones(B, 1, device=c.device)], -1)
            xs.append(tok)
        out, _ = self.post_gru(torch.stack(xs, 1))
        hT = out[ar, n]
        return self.post(torch.cat([hT, c], -1)).chunk(2, -1)

    def elbo_terms(self, b, obj, dst, n, gen=None):
        """Per-example -log p(r | c, z~q) (+ parts) and KL(q || N(0, I))."""
        c, T, Ce = self.encode(b)
        mu, lv = self.posterior(c, T, Ce, obj, dst, n)
        eps = torch.randn(mu.shape, device=mu.device, generator=gen)
        z = mu + eps * (0.5 * lv).exp()
        lp, parts = self.logp(c, T, Ce, b["movable"], b["legal0"], z, obj, dst, n)
        kl = 0.5 * (mu.pow(2) + lv.exp() - 1 - lv).sum(-1)
        return -lp, parts, kl, (mu, lv)

    # -------------------------------------------------------------------------------------------- prior sampling and marginal likelihood
    @torch.no_grad()
    def sample(self, b1, n, gen):
        """n prior trajectories for ONE root (b1 tensors with batch 1).  Fresh z per trajectory, Gumbel-max categorical draws with masks only.
        Random numbers are drawn for every row at every step (fixed consumption) -> deterministic given (checkpoint, device, seed).
        -> obj [n,3], dst [n,3], length [n] (0 = no candidate), decoder steps used."""
        c, T, Ce = self.encode(b1)
        dev = c.device
        z = torch.randn(n, self.zdim, device=dev, generator=gen)
        c, T, Ce = c.expand(n, -1), T.expand(n, -1, -1), Ce.expand(n, -1, -1)
        mov, leg = b1["movable"].expand(n, -1), b1["legal0"].expand(n, -1)
        hs = self.h0(c, z)
        moved, reserved = torch.zeros_like(mov), torch.zeros_like(leg)
        obj, dst = torch.zeros(n, KMAX, dtype=torch.long, device=dev), torch.zeros(n, KMAX, dtype=torch.long, device=dev)
        length, done = torch.zeros(n, dtype=torch.long, device=dev), torch.zeros(n, dtype=torch.bool, device=dev)
        O = mov.shape[1]
        for t in range(KMAX):
            logits, any_e, forced = self._step(hs, T, Ce, mov, leg, moved, reserved, t)
            g1 = -(-torch.rand(logits.shape, device=dev, generator=gen).clamp(1e-9, 1 - 1e-9).log()).log()
            ch = (logits + g1).argmax(-1)
            stop_now = done | forced | (ch == O) | ~any_e
            o = ch.clamp(max=O - 1)
            dl, to = self._dest_logits(hs, T, Ce, o, leg, reserved)
            g2 = -(-torch.rand(dl.shape, device=dev, generator=gen).clamp(1e-9, 1 - 1e-9).log()).log()
            d = (dl + g2).argmax(-1)
            act = ~stop_now
            obj[:, t] = torch.where(act, o, obj[:, t]); dst[:, t] = torch.where(act, d, dst[:, t])
            length = length + act.long()
            hs = torch.where(act[:, None], self._advance(hs, to, Ce, d, z, t), hs)
            moved = moved | (Fn.one_hot(o, O).bool() & act[:, None])
            reserved = reserved | (Fn.one_hot(d, self.N).bool() & act[:, None])
            done = done | stop_now
        return obj, dst, length

    @torch.no_grad()
    def marginal_loglik(self, b1, seqs_o, seqs_d, seqs_n, z, chunk=16384):
        """log p_hat(r | c) = logsumexp_l log p(r | c, z_l) - log L for U candidates of ONE root with shared latents z [L, zdim].
        -> [U] tensor and the number of sequence-latent decoder passes (U * L)."""
        c, T, Ce = self.encode(b1)
        U, L = seqs_o.shape[0], z.shape[0]
        out = torch.empty(U * L, device=c.device)
        ui = torch.arange(U, device=c.device).repeat_interleave(L)
        li = torch.arange(L, device=c.device).repeat(U)
        for s in range(0, U * L, chunk):
            u, l = ui[s:s + chunk], li[s:s + chunk]
            B = len(u)
            lp, _ = self.logp(c.expand(B, -1), T.expand(B, -1, -1), Ce.expand(B, -1, -1), b1["movable"].expand(B, -1), b1["legal0"].expand(B, -1),
                              z[l], seqs_o[u], seqs_d[u], seqs_n[u])
            out[s:s + B] = lp
        return out.view(U, L).logsumexp(1) - math.log(L), U * L


def param_counts(m):
    """Parameters per component; inference excludes the training-only posterior."""
    grp = {"encoder": ("tok", "glob", "scene", "tokc", "cellm", "cellc"), "decoder": ("dec0", "gru", "objh", "stoph", "dsth"),
           "posterior_train_only": ("post_gru", "post"), "decision_head": ("gate",)}
    out = {g: sum(p.numel() for n_, p in m.named_parameters() if n_.split(".")[0] in mods) for g, mods in grp.items()}
    out["total"] = sum(p.numel() for p in m.parameters())
    out["inference"] = out["total"] - out["posterior_train_only"]
    return out
