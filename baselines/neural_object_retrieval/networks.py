"""NOR-Grid networks (random init, PyTorch).  Token features come from graph.scene (public inputs only):
  X [B, N+2, F_NODE]  objects (padded to NMAX) then robot token (base + q_ref context) then goal token (target-at-goal); M token mask
  C [B, NCELL, F_CELL] cell (region) tokens; L legal-destination mask; E eligible-object mask

OSNet  (Ren & Qureshi eq. 2): alpha-MLP token embeddings -> multi-head self-attention Transformer -> per-object MLP -> masked softmax
       over eligible objects = predicted blocking distribution p_hat.  Loss: MSE to the homotopy blocking distribution.
RPNet  (eq. 3 / 4): encoder over [robot, goal, target, cell] tokens (kappa-MLP for cells); decoder queries = kappa(cell) + alpha(selected
       object), attending to the encoder output; MLP -> one cost per cell (lower is better).  Loss: MSE to the region cost map.
STOP   OSRP-openloop-adapter (NOT part of the paper): separate small Transformer over all tokens -> p(target task feasible from q_ref in
       this hypothetical scene); BCE on decided TRAIN endpoint Y.  Separate parameters, so it never shapes OSNet / RPNet."""
import torch
import torch.nn as nn

import graph as G


def mlp(i, o, h=128):
    return nn.Sequential(nn.Linear(i, h), nn.ReLU(), nn.Linear(h, o))


def tfm(d, layers, heads=4, ff=256, drop=0.1, decoder=False):
    L = nn.TransformerDecoderLayer if decoder else nn.TransformerEncoderLayer
    layer = L(d, heads, ff, drop, batch_first=True, norm_first=True)
    return (nn.TransformerDecoder if decoder else nn.TransformerEncoder)(layer, layers)


class Tokens(nn.Module):
    """alpha (object / robot / goal tokens, with a learned type embedding: object, target, robot, goal)."""

    def __init__(self, d):
        super().__init__()
        self.alpha = mlp(G.F_NODE, d)
        self.typ = nn.Embedding(4, d)

    def forward(self, X, tid_mask):
        B, T, _ = X.shape
        N = T - 2
        ty = torch.zeros(B, T, dtype=torch.long, device=X.device)
        ty[tid_mask] = 1
        ty[:, N], ty[:, N + 1] = 2, 3
        return self.alpha(X) + self.typ(ty)


class OSNet(nn.Module):
    def __init__(self, d=128, layers=3):
        super().__init__()
        self.tok = Tokens(d)
        self.enc = tfm(d, layers)
        self.head = mlp(d, 1)

    def forward(self, X, M, Elig, tid_mask):
        h = self.enc(self.tok(X, tid_mask), src_key_padding_mask=~M)
        s = self.head(h).squeeze(-1).masked_fill(~Elig, -1e9)
        p = torch.softmax(s, -1) * Elig
        return p, s


class RPNet(nn.Module):
    def __init__(self, d=128, layers=2):
        super().__init__()
        self.tok = Tokens(d)
        self.kappa = mlp(G.F_CELL, d)
        self.enc = tfm(d, layers)
        self.dec = tfm(d, layers, decoder=True)
        self.head = mlp(d, 1)

    def forward(self, X, M, C, obj, tid_mask):
        """obj [B] index of the selected object -> cost [B, NCELL]."""
        B, T, _ = X.shape
        N = T - 2
        tk = self.tok(X, tid_mask)
        keep = torch.zeros_like(M)                                     # encoder: robot, goal, target (+ cells); not other objects
        keep[:, N] = M[:, N]
        keep[:, N + 1] = M[:, N + 1]
        keep |= tid_mask
        kc = self.kappa(C)
        mem = self.enc(torch.cat([tk, kc], 1), src_key_padding_mask=~torch.cat([keep, torch.ones(C.shape[:2], dtype=torch.bool, device=C.device)], 1))
        q = kc + tk[torch.arange(B, device=X.device), obj][:, None, :]
        y = self.dec(q, mem, memory_key_padding_mask=~torch.cat([keep, torch.ones(C.shape[:2], dtype=torch.bool, device=C.device)], 1))
        return self.head(y).squeeze(-1)


class StopAdapter(nn.Module):
    def __init__(self, d=128, layers=2):
        super().__init__()
        self.tok = Tokens(d)
        self.enc = tfm(d, layers)
        self.head = mlp(2 * d, 1)

    def forward(self, X, M, tid_mask):
        h = self.enc(self.tok(X, tid_mask), src_key_padding_mask=~M)
        m = M.float()[..., None]
        pooled = torch.cat([(h * m).sum(1) / m.sum(1).clamp(min=1), h.masked_fill(~M[..., None], -1e9).max(1).values], -1)
        return self.head(pooled).squeeze(-1)
