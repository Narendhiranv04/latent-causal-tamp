#!/usr/bin/env python3
"""DISCO-Grid Factorized Categorical Policy (P0/P1/P2) and Continuation Value Network (Q1/Q2_value).

Implements `DISCO_plan.md` Sections 6, 7, 9.1, and 10.1:
- Factorized categorical policy:
    pi_theta(o, d | h_t, T) = pi_theta^obj(o | h_t, T) * pi_theta^dst(d | h_t, o, T)
  plus an explicit terminal `STOP` token.
- P0 Pretraining:
    Trains `pi_theta^dst(d | s, o, goal-masked)` on positive Q2 isolated placement records (`label == 1`,
    TRAIN split only) with goal features masked (`task_on=False`). Keeps `pi_theta^obj` uniform over
    eligible movable objects because Q2 queries are not expert object-selection decisions.
- Policy Distillation (P1, P2):
    Trains both `pi_theta^obj` and `pi_theta^dst` on ALL physically executed feasible tree edges
    (and verified-positive `STOP` decisions) via masked categorical cross-entropy.
- Value Network `Q_phi(h_t, a)`:
    Predicts continuation success probability in `[0, 1]` for relocation actions `a = (o, d)` and terminal `STOP`,
    trained with log-evidence-weighted binary cross-entropy:
        w_i = log(1 + n_visited_leaves),  y_i = n_success_leaves / n_visited_leaves.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import data as D
import env as E

GRID = D.GRID_SHAPE
MAXOBJ = D.MAX_OBJ
NORM_COLS = [2, 3, 6, 7, 8]


def task_dim(dom: str) -> int:
    dom_l = dom.lower()
    r, c = GRID[dom_l]
    n_cells = r * c
    ctx_d = 9 if dom_l == "2d" else 19
    return 2 * n_cells + 4 + ctx_d + 2  # +2 for [task_on, remaining_steps_frac]


def cell_xy_tuple(dom: str, c: int) -> tuple[float, float]:
    dom_l = dom.lower()
    R, C = GRID[dom_l]
    row, col = divmod(int(c), C)
    if dom_l == "2d":
        return (0.08 * (col + 0.5), 0.08 * (row + 0.5))
    return (0.42 + (row - 2.5) * 0.075, (col - 2.5) * 0.075)


def extract_query_features(
    dom: str,
    obs: E.LearnerObservation,
    query_obj_idx: int,
    scalers: dict[str, Any],
    task_on: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build normalized learner-only tensors `(obj_feat [MAXOBJ, 14], obj_mask [MAXOBJ], occ_task [N + tdim], legal_dest [N])`
    for one queried object `query_obj_idx` in `obs`.
    Matches the 14-column Q2 feature definition so P0 Q2 weights transfer seamlessly to MCTS & distillation.
    """
    dom_l = dom.lower()
    R, C = GRID[dom_l]
    N = R * C
    max_o = MAXOBJ[dom_l]
    base = (-0.14, 0.32) if dom_l == "2d" else (0.0, 0.0)

    # Map each object index to its 4-tuple geometry attributes (matching placement.py pattr)
    pattr = {}
    for i, oid in enumerate(obs.ids):
        a = obs.attrs[i]
        if dom_l == "2d":
            pattr[oid] = (float(a[0]), float(a[3]), 0.0, 0.0)
        else:
            pattr[oid] = (float(a[0]), float(a[1]), float(a[2]), float(a[3]))

    q_id = obs.ids[query_obj_idx]
    cells_by_id = {obs.ids[i]: int(obs.cells[i]) for i in range(len(obs.ids))}
    ordered_ids = [q_id] + sorted(oid for oid in cells_by_id if oid != q_id)

    feat = np.zeros((max_o, 14), dtype=np.float32)
    mask = np.zeros(max_o, dtype=bool)
    occ = np.zeros(N, dtype=np.float32)

    qr, qc = divmod(int(cells_by_id[q_id]), C)
    for k, oid in enumerate(ordered_ids[:max_o]):
        c_val = int(cells_by_id[oid])
        r, c = divmod(c_val, C)
        x, y = cell_xy_tuple(dom_l, c_val)
        dx, dy = x - base[0], y - base[1]
        feat[k] = [
            *pattr[oid],
            r / (R - 1),
            c / (C - 1),
            x,
            y,
            math.hypot(dx, dy),
            math.atan2(dy, dx) / math.pi,
            float(oid == q_id),
            (r - qr) / (R - 1),
            (c - qc) / (C - 1),
            max(abs(r - qr), abs(c - qc)) / (R - 1),
        ]
        mask[k] = True
        occ[c_val] = 1.0

    mu = np.asarray(scalers["mean"], dtype=np.float32)
    sd = np.asarray(scalers["std"], dtype=np.float32)
    feat_norm = (feat - mu) / sd * mask[:, None]

    t_vec = np.zeros(task_dim(dom_l), dtype=np.float32)
    if task_on:
        g_cell = int(obs.goal_cell)
        t_cell = int(obs.cells[obs.tid])
        t_vec[g_cell] = 1.0
        t_vec[N + t_cell] = 1.0
        t_vec[2 * N : 2 * N + 4] = [
            (g_cell // C - qr) / (R - 1),
            (g_cell % C - qc) / (C - 1),
            (t_cell // C - qr) / (R - 1),
            (t_cell % C - qc) / (C - 1),
        ]
        ctx_len = len(obs.ctx)
        t_vec[2 * N + 4 : 2 * N + 4 + ctx_len] = np.asarray(obs.ctx, dtype=np.float32)
        t_vec[-2] = 1.0
        t_vec[-1] = float(obs.remaining_steps) / 3.0

    occ_task = np.concatenate([occ, t_vec], axis=0)
    legal_dest = np.zeros(N, dtype=bool)
    for d in obs.legal_destinations:
        legal_dest[int(d)] = True
    return feat_norm, mask, occ_task, legal_dest


def extract_scene_object_tokens(
    dom: str,
    obs: E.LearnerObservation,
    scalers: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build scene-level object tokens `[MAXOBJ, 18]`, `obj_mask [MAXOBJ]`, `scene_ctx [N + tdim]`,
    and `eligible_action_mask [MAXOBJ + 1]` (last index = `STOP`) in `obs.ids` index order.
    Strictly learner-visible features: geometry, coordinates, distance/offset to target and goal,
    `moved_mask`, `is_target`, `is_fixed`, and `remaining_steps`.
    """
    dom_l = dom.lower()
    R, C = GRID[dom_l]
    N = R * C
    max_o = MAXOBJ[dom_l]
    base = (-0.14, 0.32) if dom_l == "2d" else (0.0, 0.0)

    t_cell = int(obs.cells[obs.tid])
    g_cell = int(obs.goal_cell)
    tr, tc = divmod(t_cell, C)
    gr, gc = divmod(g_cell, C)

    mu = np.asarray(scalers["mean"], dtype=np.float32)
    sd = np.asarray(scalers["std"], dtype=np.float32)

    obj_tok = np.zeros((max_o, 18), dtype=np.float32)
    obj_mask = np.zeros(max_o, dtype=bool)
    occ = np.zeros(N, dtype=np.float32)

    for i in range(min(len(obs.ids), max_o)):
        a = obs.attrs[i]
        p4 = (float(a[0]), float(a[3]), 0.0, 0.0) if dom_l == "2d" else (float(a[0]), float(a[1]), float(a[2]), float(a[3]))
        c_val = int(obs.cells[i])
        r, c = divmod(c_val, C)
        x, y = cell_xy_tuple(dom_l, c_val)
        dx, dy = x - base[0], y - base[1]
        base14 = np.array(
            [
                *p4,
                r / (R - 1),
                c / (C - 1),
                x,
                y,
                math.hypot(dx, dy),
                math.atan2(dy, dx) / math.pi,
                float(i == obs.tid),
                (r - tr) / (R - 1),
                (c - tc) / (C - 1),
                max(abs(r - tr), abs(c - tc)) / (R - 1),
            ],
            dtype=np.float32,
        )
        base14_norm = (base14 - mu) / sd
        extra4 = np.array(
            [
                (r - gr) / (R - 1),
                (c - gc) / (C - 1),
                max(abs(r - gr), abs(c - gc)) / (R - 1),
                float(obs.moved_mask[i]),
            ],
            dtype=np.float32,
        )
        obj_tok[i, :14] = base14_norm
        obj_tok[i, 14:] = extra4
        obj_mask[i] = True
        occ[c_val] = 1.0

    t_vec = np.zeros(task_dim(dom_l), dtype=np.float32)
    t_vec[g_cell] = 1.0
    t_vec[N + t_cell] = 1.0
    t_vec[2 * N : 2 * N + 4] = [
        (gr - tr) / (R - 1),
        (gc - tc) / (C - 1),
        0.0,
        0.0,
    ]
    ctx_len = len(obs.ctx)
    t_vec[2 * N + 4 : 2 * N + 4 + ctx_len] = np.asarray(obs.ctx, dtype=np.float32)
    t_vec[-2] = 1.0
    t_vec[-1] = float(obs.remaining_steps) / 3.0

    scene_ctx = np.concatenate([occ, t_vec], axis=0)
    elig_mask = np.zeros(max_o + 1, dtype=bool)
    if obs.legal_destinations and obs.remaining_steps > 0:
        for o_i in obs.eligible_objects:
            if o_i < max_o:
                elig_mask[o_i] = True
    if obs.can_stop:
        elig_mask[max_o] = True  # STOP token index = max_o
    return obj_tok, obj_mask, scene_ctx, elig_mask


def mlp(in_dim: int, hid_dim: int, out_dim: int, n_hidden: int = 2) -> nn.Sequential:
    layers: list[nn.Module] = []
    d = in_dim
    for _ in range(n_hidden):
        layers += [nn.Linear(d, hid_dim), nn.SiLU()]
        d = hid_dim
    layers.append(nn.Linear(d, out_dim))
    return nn.Sequential(*layers)


class QuerySceneEncoder(nn.Module):
    """Shared scene encoder for destination proposal `pi_dst(d | h_t, o, T)`.
    Uses an additive zero-initialized task branch so when `task_on=False` (P0 Q2 pretraining),
    only the geometry/occupancy branch is active; during MCTS distillation (`task_on=True`),
    goal/target context smoothly adapts destination proposals.
    """

    def __init__(self, n_cells: int, t_dim: int, n_feat: int = 14, h: int = 128):
        super().__init__()
        self.n_cells = n_cells
        self.t_dim = t_dim
        self.h = h
        self.phi = mlp(n_feat, h, h, 2)
        self.q = nn.Linear(h, h)
        self.k = nn.Linear(h, h)
        self.v = nn.Linear(h, h)
        self.grid = mlp(n_cells, h, h, 1)
        self.out = mlp(4 * h, h, h, 1)
        self.task_mlp = mlp(t_dim, h, h, 2)
        nn.init.zeros_(self.task_mlp[-1].weight)
        nn.init.zeros_(self.task_mlp[-1].bias)

    def forward(self, obj: torch.Tensor, mask: torch.Tensor, occ_task: torch.Tensor) -> torch.Tensor:
        e = self.phi(obj) * mask[..., None]
        qtok = e[:, 0]
        att_logits = (self.q(qtok)[:, None] * self.k(e)).sum(-1) / math.sqrt(self.h)
        att = att_logits.masked_fill(~mask, -1e9).softmax(-1)
        ctx = (att[..., None] * self.v(e)).sum(1)
        mean = e.sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        occ = occ_task[:, : self.n_cells]
        t_feat = occ_task[:, self.n_cells :]
        base_emb = self.out(torch.cat([qtok, ctx, mean, self.grid(occ)], dim=-1))
        return base_emb + self.task_mlp(t_feat)


class DiscoPolicyNet(nn.Module):
    """Factorized categorical action-proposal policy for DISCO-Grid:
    - `dst_logits(obj, mask, occ_task, legal_dest)` -> masked logits `[B, N_cells]` for `pi_dst(d | h_t, o, T)`
    - `obj_logits(scene_obj_tok, scene_obj_mask, scene_ctx, elig_mask)` -> masked logits `[B, MAXOBJ + 1]`
      over eligible objects `0..MAXOBJ-1` plus `STOP` (`index = MAXOBJ`).
    """

    def __init__(self, dom: str, h: int = 128):
        super().__init__()
        self.dom = dom.lower()
        self.R, self.C = GRID[self.dom]
        self.N = self.R * self.C
        self.max_obj = MAXOBJ[self.dom]
        self.tdim = task_dim(self.dom)
        self.h = h

        # 1. Destination proposal network (pretrained in P0 on Q2, refined in P1/P2 on MCTS feasible edges)
        self.dst_enc = QuerySceneEncoder(self.N, self.tdim, n_feat=14, h=h)
        self.dst_head = mlp(h, h, self.N, 2)

        # 2. Object + STOP selection network (uniform in P0, distilled in P1/P2 on MCTS feasible edges)
        self.obj_phi = mlp(18, h, h, 2)
        self.obj_att_q = nn.Linear(h, h)
        self.obj_att_k = nn.Linear(h, h)
        self.obj_att_v = nn.Linear(h, h)
        self.scene_ctx_mlp = mlp(self.N + self.tdim, h, h, 2)
        self.obj_head = mlp(2 * h, h, 1, 2)
        self.stop_head = mlp(2 * h, h, 1, 2)
        self.obj_trained = False

    def forward_dst(
        self,
        obj: torch.Tensor,
        mask: torch.Tensor,
        occ_task: torch.Tensor,
        legal_dest: torch.Tensor,
    ) -> torch.Tensor:
        emb = self.dst_enc(obj, mask, occ_task)
        logits = self.dst_head(emb)
        return logits.masked_fill(~legal_dest, -1e9)

    def forward_obj(
        self,
        scene_obj_tok: torch.Tensor,
        scene_obj_mask: torch.Tensor,
        scene_ctx: torch.Tensor,
        elig_mask: torch.Tensor,
    ) -> torch.Tensor:
        e = self.obj_phi(scene_obj_tok) * scene_obj_mask[..., None]
        sc = self.scene_ctx_mlp(scene_ctx)
        att_logits = (self.obj_att_q(sc)[:, None] * self.obj_att_k(e)).sum(-1) / math.sqrt(self.h)
        att = att_logits.masked_fill(~scene_obj_mask, -1e9).softmax(-1)
        pooled = (att[..., None] * self.obj_att_v(e)).sum(1)
        global_feat = torch.cat([sc, pooled], dim=-1)  # [B, 2*h]

        B, M, _ = e.shape
        per_obj_in = torch.cat([e, sc[:, None].expand(B, M, -1)], dim=-1)
        o_logits = self.obj_head(per_obj_in).squeeze(-1)  # [B, MAXOBJ]
        s_logit = self.stop_head(global_feat)  # [B, 1]
        all_logits = torch.cat([o_logits, s_logit], dim=-1)  # [B, MAXOBJ + 1]
        return all_logits.masked_fill(~elig_mask, -1e9)

    def dst_loss(
        self,
        obj: torch.Tensor,
        mask: torch.Tensor,
        occ_task: torch.Tensor,
        legal_dest: torch.Tensor,
        target_dest: torch.Tensor,
    ) -> torch.Tensor:
        logits = self.forward_dst(obj, mask, occ_task, legal_dest)
        return F.cross_entropy(logits, target_dest)

    def obj_loss(
        self,
        scene_obj_tok: torch.Tensor,
        scene_obj_mask: torch.Tensor,
        scene_ctx: torch.Tensor,
        elig_mask: torch.Tensor,
        target_obj_or_stop: torch.Tensor,
    ) -> torch.Tensor:
        logits = self.forward_obj(scene_obj_tok, scene_obj_mask, scene_ctx, elig_mask)
        return F.cross_entropy(logits, target_obj_or_stop)


class DiscoValueNet(nn.Module):
    """Continuation Value Network `Q_phi(h_t, a)` for DISCO-Grid (Section 7).
    Scores candidate actions `a = (o, d)` or `a = STOP` in `[0, 1]` using the scene observation.
    Trained with log-evidence-weighted BCE: `w_i = log(1 + n_visited_leaves)`.
    """

    def __init__(self, dom: str, h: int = 128):
        super().__init__()
        self.dom = dom.lower()
        self.R, self.C = GRID[self.dom]
        self.N = self.R * self.C
        self.max_obj = MAXOBJ[self.dom]
        self.tdim = task_dim(self.dom)
        self.h = h

        self.obj_phi = mlp(18, h, h, 2)
        self.att_q = nn.Linear(h, h)
        self.att_k = nn.Linear(h, h)
        self.att_v = nn.Linear(h, h)
        self.ctx_mlp = mlp(self.N + self.tdim, h, h, 2)
        self.dest_embed = nn.Embedding(self.N + 1, h)  # N cells + 1 STOP destination token
        self.q_head = mlp(4 * h, h, 1, 2)

    def forward_logits(
        self,
        scene_obj_tok: torch.Tensor,
        scene_obj_mask: torch.Tensor,
        scene_ctx: torch.Tensor,
        action_obj_idx: torch.Tensor,
        action_dest_idx: torch.Tensor,
    ) -> torch.Tensor:
        """
        `action_obj_idx`: `[B]` in `0..MAXOBJ` (`MAXOBJ` = `STOP`)
        `action_dest_idx`: `[B]` in `0..N` (`N` = `STOP`)
        """
        e = self.obj_phi(scene_obj_tok) * scene_obj_mask[..., None]
        sc = self.ctx_mlp(scene_ctx)
        att_logits = (self.att_q(sc)[:, None] * self.att_k(e)).sum(-1) / math.sqrt(self.h)
        att = att_logits.masked_fill(~scene_obj_mask, -1e9).softmax(-1)
        pooled = (att[..., None] * self.att_v(e)).sum(1)

        # Gather object token for relocation actions, or zeros for STOP (action_obj_idx == max_obj)
        B = e.shape[0]
        zero_tok = torch.zeros((B, 1, self.h), dtype=e.dtype, device=e.device)
        e_ext = torch.cat([e, zero_tok], dim=1)  # [B, MAXOBJ + 1, h]
        picked_obj = e_ext[torch.arange(B, device=e.device), action_obj_idx.long()]  # [B, h]
        d_emb = self.dest_embed(action_dest_idx.long().clamp(0, self.N))  # [B, h]

        joint = torch.cat([sc, pooled, picked_obj, d_emb], dim=-1)  # [B, 4*h]
        return self.q_head(joint).squeeze(-1)

    def predict_q(
        self,
        scene_obj_tok: torch.Tensor,
        scene_obj_mask: torch.Tensor,
        scene_ctx: torch.Tensor,
        action_obj_idx: torch.Tensor,
        action_dest_idx: torch.Tensor,
    ) -> torch.Tensor:
        return torch.sigmoid(
            self.forward_logits(scene_obj_tok, scene_obj_mask, scene_ctx, action_obj_idx, action_dest_idx)
        )

    def weighted_bce_loss(
        self,
        scene_obj_tok: torch.Tensor,
        scene_obj_mask: torch.Tensor,
        scene_ctx: torch.Tensor,
        action_obj_idx: torch.Tensor,
        action_dest_idx: torch.Tensor,
        targets: torch.Tensor,
        n_leaves: torch.Tensor,
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """DISCO Eq. (Value Distillation):
            y_i = n_success_leaves / n_visited_leaves
            w_i = log(1 + n_visited_leaves)
            L_Q = sum_i w_i * BCE(Q(s_i, a_i), y_i) / sum_i w_i
        """
        logits = self.forward_logits(scene_obj_tok, scene_obj_mask, scene_ctx, action_obj_idx, action_dest_idx)
        per_sample_bce = F.binary_cross_entropy_with_logits(logits, targets.float(), reduction="none")
        weights = torch.log1p(n_leaves.float())
        w_sum = weights.sum().clamp(min=1e-6)
        loss = (weights * per_sample_bce).sum() / w_sum
        with torch.no_grad():
            probs = torch.sigmoid(logits)
            mse = (probs - targets.float()).pow(2).mean().item()
            mae = (probs - targets.float()).abs().mean().item()
        return loss, {"weighted_bce": float(loss.item()), "mse": mse, "mae": mae}


# ---------------------------------------------------------------------------
# Action Sampling & Proposal Interface (Used by MCTS and Open/Closed-Loop Inference)
# ---------------------------------------------------------------------------

class PolicyProposalWrapper:
    """Wraps either a trained `DiscoPolicyNet` (P0/P1/P2) or the `uniform` control
    behind a unified candidate-sampling and probability interface.
    Counts every neural forward pass for strict compute accounting.
    """

    def __init__(
        self,
        dom: str,
        model: DiscoPolicyNet | None,
        scalers: dict[str, Any],
        device: str = "cuda",
        mode: str = "p0",  # "uniform", "p0", "distilled"
        value_model: DiscoValueNet | None = None,
    ):
        self.dom = dom.lower()
        self.model = model.to(device).eval() if model is not None else None
        self.value_model = value_model.to(device).eval() if value_model is not None else None
        self.scalers = scalers
        self.device = device
        self.mode = mode
        self.policy_calls = 0
        self.value_calls = 0

    @torch.no_grad()
    def action_distribution(self, obs: E.LearnerObservation) -> dict[str, Any]:
        """Compute exact masked probability distribution over all legal `(o, d)` actions and `STOP`."""
        elig_objs = list(obs.eligible_objects)
        leg_dests = list(obs.legal_destinations)
        R, C = GRID[self.dom]
        N = R * C
        max_o = MAXOBJ[self.dom]

        if not elig_objs or not leg_dests or obs.remaining_steps <= 0:
            return {
                "reloc_actions": [],
                "reloc_probs": np.zeros(0, dtype=np.float32),
                "stop_prob": 1.0,
                "obj_probs": {},
                "dst_probs_by_obj": {},
            }

        if self.mode == "uniform" or self.model is None:
            n_o = len(elig_objs)
            n_d = len(leg_dests)
            obj_probs = {o: 1.0 / n_o for o in elig_objs}
            dst_probs_by_obj = {}
            reloc_actions = []
            reloc_probs = []
            for o in elig_objs:
                p_d = np.zeros(N, dtype=np.float32)
                for d in leg_dests:
                    p_d[d] = 1.0 / n_d
                    reloc_actions.append((o, d))
                    reloc_probs.append((1.0 / n_o) * (1.0 / n_d))
                dst_probs_by_obj[o] = p_d
            return {
                "reloc_actions": reloc_actions,
                "reloc_probs": np.asarray(reloc_probs, dtype=np.float32),
                "stop_prob": 0.10,
                "obj_probs": obj_probs,
                "dst_probs_by_obj": dst_probs_by_obj,
            }

        # Query `forward_dst` in one batch over all eligible objects
        task_on = (self.mode == "distilled")
        Fs, Ms, OTs, LDs = [], [], [], []
        for o in elig_objs:
            f, m, ot, ld = extract_query_features(self.dom, obs, o, self.scalers, task_on=task_on)
            Fs.append(f); Ms.append(m); OTs.append(ot); LDs.append(ld)

        t_F = torch.as_tensor(np.stack(Fs), dtype=torch.float32, device=self.device)
        t_M = torch.as_tensor(np.stack(Ms), dtype=torch.bool, device=self.device)
        t_OT = torch.as_tensor(np.stack(OTs), dtype=torch.float32, device=self.device)
        t_LD = torch.as_tensor(np.stack(LDs), dtype=torch.bool, device=self.device)

        dst_logits = self.model.forward_dst(t_F, t_M, t_OT, t_LD)
        dst_probs = dst_logits.softmax(dim=-1).cpu().numpy()  # [len(elig_objs), N]
        self.policy_calls += len(elig_objs)

        if self.mode == "distilled" and getattr(self.model, "obj_trained", False):
            s_tok, s_mask, s_ctx, s_elig = extract_scene_object_tokens(self.dom, obs, self.scalers)
            o_logits = self.model.forward_obj(
                torch.as_tensor(s_tok[None], dtype=torch.float32, device=self.device),
                torch.as_tensor(s_mask[None], dtype=torch.bool, device=self.device),
                torch.as_tensor(s_ctx[None], dtype=torch.float32, device=self.device),
                torch.as_tensor(s_elig[None], dtype=torch.bool, device=self.device),
            )
            o_probs_all = o_logits.softmax(dim=-1)[0].cpu().numpy()
            self.policy_calls += 1
            stop_prob = float(o_probs_all[max_o])
            reloc_mass = max(float(sum(o_probs_all[o] for o in elig_objs)), 1e-8)
            obj_probs = {o: float(o_probs_all[o] / reloc_mass) for o in elig_objs}
        else:
            # P0: uniform over eligible movable objects
            obj_probs = {o: 1.0 / len(elig_objs) for o in elig_objs}
            stop_prob = 0.10

        dst_probs_by_obj = {}
        reloc_actions = []
        reloc_probs = []
        for idx_o, o in enumerate(elig_objs):
            dst_probs_by_obj[o] = dst_probs[idx_o]
            po = obj_probs[o]
            for d in leg_dests:
                reloc_actions.append((o, int(d)))
                reloc_probs.append(po * float(dst_probs[idx_o, int(d)]))
        reloc_probs_arr = np.asarray(reloc_probs, dtype=np.float32)
        s = reloc_probs_arr.sum()
        if s > 0:
            reloc_probs_arr = reloc_probs_arr / s
        return {
            "reloc_actions": reloc_actions,
            "reloc_probs": reloc_probs_arr,
            "stop_prob": stop_prob,
            "obj_probs": obj_probs,
            "dst_probs_by_obj": dst_probs_by_obj,
        }

    @torch.no_grad()
    def sample_candidates(
        self,
        obs: E.LearnerObservation,
        B: int,
        rng: np.random.Generator,
    ) -> dict[str, Any]:
        """Sample up to `B` unique legal relocation actions `(o, d)` without replacement from `pi_theta`."""
        dist = self.action_distribution(obs)
        actions = dist["reloc_actions"]
        probs = dist["reloc_probs"]
        if not actions:
            return {"candidates": [], "probs": [], "n_available": 0, "stop_prob": dist["stop_prob"], "dist": dist}

        k = min(int(B), len(actions))
        # Ensure strictly positive probabilities on legal support for sampling without replacement
        p_safe = np.maximum(probs, 1e-9)
        p_safe = p_safe / p_safe.sum()
        chosen_idx = rng.choice(len(actions), size=k, replace=False, p=p_safe)
        cands = [actions[i] for i in chosen_idx]
        c_probs = [float(probs[i]) for i in chosen_idx]
        return {
            "candidates": cands,
            "probs": c_probs,
            "n_available": len(actions),
            "stop_prob": dist["stop_prob"],
            "dist": dist,
        }

    @torch.no_grad()
    def score_actions_q(
        self,
        obs: E.LearnerObservation,
        actions: list[tuple[int, int] | str],
    ) -> np.ndarray:
        """Predict `Q_phi(obs, a)` for a list of actions (`(o, d)` tuples or `'STOP'`)."""
        if not actions:
            return np.zeros(0, dtype=np.float32)
        if self.value_model is None:
            return np.zeros(len(actions), dtype=np.float32)

        s_tok, s_mask, s_ctx, _ = extract_scene_object_tokens(self.dom, obs, self.scalers)
        max_o = MAXOBJ[self.dom]
        N = GRID[self.dom][0] * GRID[self.dom][1]

        M = len(actions)
        t_tok = torch.as_tensor(s_tok[None], dtype=torch.float32, device=self.device).expand(M, -1, -1)
        t_mask = torch.as_tensor(s_mask[None], dtype=torch.bool, device=self.device).expand(M, -1)
        t_ctx = torch.as_tensor(s_ctx[None], dtype=torch.float32, device=self.device).expand(M, -1)

        o_idxs = []
        d_idxs = []
        for a in actions:
            if a == "STOP":
                o_idxs.append(max_o)
                d_idxs.append(N)
            else:
                o_idxs.append(int(a[0]))
                d_idxs.append(int(a[1]))
        t_o = torch.tensor(o_idxs, dtype=torch.long, device=self.device)
        t_d = torch.tensor(d_idxs, dtype=torch.long, device=self.device)

        q_vals = self.value_model.predict_q(t_tok, t_mask, t_ctx, t_o, t_d).cpu().numpy()
        self.value_calls += M
        return q_vals


# ---------------------------------------------------------------------------
# D2: P0 Pretraining & Held-Out Q2 Evaluation
# ---------------------------------------------------------------------------

def train_p0(
    dom: str,
    seed: int = 0,
    epochs: int = 40,
    batch_size: int = 512,
    lr: float = 1e-3,
    hidden: int = 128,
    device: str = "cuda",
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Train DISCO-Grid P0 destination policy on positive Q2 examples (`split == 0` & `label == 1`)
    with goal features masked (`task_on = False`).
    """
    dom_l = dom.lower()
    torch.manual_seed(seed)
    np.random.seed(seed)

    q2 = D.load_q2_dataset(dom_l)
    scalers = q2["scalers"]
    R, C = GRID[dom_l]
    N = R * C
    max_o = MAXOBJ[dom_l]

    raw_obj = q2["obj"]
    raw_mask = q2["mask"]
    # Pad object axis to MAXOBJ[dom_l] if needed (3D Q2 has 8 slots while 3D NONE scenes have up to 16)
    if raw_obj.shape[1] < max_o:
        pad_n = max_o - raw_obj.shape[1]
        raw_obj = np.pad(raw_obj, ((0, 0), (0, pad_n), (0, 0)))
        raw_mask = np.pad(raw_mask, ((0, 0), (0, pad_n)))

    mu = np.asarray(scalers["mean"], dtype=np.float32)
    sd = np.asarray(scalers["std"], dtype=np.float32)
    obj_norm = (raw_obj - mu) / sd * raw_mask[..., None]

    # Goal-masked task vector = zeros of length task_dim(dom_l)
    tdim = task_dim(dom_l)
    occ_task = np.concatenate([q2["occ"], np.zeros((len(q2["occ"]), tdim), dtype=np.float32)], axis=1)

    t_obj = torch.as_tensor(obj_norm, dtype=torch.float32, device=device)
    t_mask = torch.as_tensor(raw_mask, dtype=torch.bool, device=device)
    t_ot = torch.as_tensor(occ_task, dtype=torch.float32, device=device)
    t_leg = torch.as_tensor(q2["legal"], dtype=torch.bool, device=device)
    t_dest = torch.as_tensor(q2["dest"], dtype=torch.long, device=device)
    t_split = torch.as_tensor(q2["split"], dtype=torch.long, device=device)
    t_label = torch.as_tensor(q2["label"], dtype=torch.long, device=device)

    tr_idx = torch.nonzero((t_split == 0) & (t_label == 1)).squeeze(1)
    va_idx = torch.nonzero((t_split == 1) & (t_label == 1)).squeeze(1)

    model = DiscoPolicyNet(dom_l, h=hidden).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    gen = torch.Generator(device=device).manual_seed(seed)

    save_dir = (out_dir or (D.DISCO_ROOT / "runs/p0" / dom_l / f"s{seed}"))
    save_dir.mkdir(parents=True, exist_ok=True)

    curve = []
    best_val = (math.inf, -1)
    t0 = time.time()

    for ep in range(epochs):
        model.train()
        perm = tr_idx[torch.randperm(len(tr_idx), device=device, generator=gen)]
        tr_losses = []
        for i in range(0, len(perm), batch_size):
            ix = perm[i : i + batch_size]
            loss = model.dst_loss(t_obj[ix], t_mask[ix], t_ot[ix], t_leg[ix], t_dest[ix])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tr_losses.append(float(loss.item()))

        model.eval()
        with torch.no_grad():
            va_losses = [
                float(model.dst_loss(t_obj[va_idx[i : i + 2048]], t_mask[va_idx[i : i + 2048]], t_ot[va_idx[i : i + 2048]], t_leg[va_idx[i : i + 2048]], t_dest[va_idx[i : i + 2048]]).item())
                for i in range(0, len(va_idx), 2048)
            ]
            vl = float(np.mean(va_losses))
        curve.append({"epoch": ep, "train_ce": float(np.mean(tr_losses)), "val_ce": vl})
        if vl < best_val[0]:
            best_val = (vl, ep)
            ckpt = {
                "domain": dom_l,
                "round": "P0",
                "seed": seed,
                "epoch": ep,
                "best_val_ce": vl,
                "hidden": hidden,
                "obj_trained": False,
                "scalers": scalers,
                "state_dict": model.state_dict(),
            }
            tmp_p = save_dir / "model.pt.tmp"
            torch.save(ckpt, tmp_p)
            os.replace(tmp_p, save_dir / "model.pt")

    meta = {
        "domain": dom_l,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "lr": lr,
        "hidden": hidden,
        "train_positives": int(len(tr_idx)),
        "val_positives": int(len(va_idx)),
        "best_val_ce": best_val[0],
        "best_epoch": best_val[1],
        "wall_s": round(time.time() - t0, 2),
        "gpu_peak_mib": round(torch.cuda.max_memory_allocated() / (2 ** 20), 1) if torch.cuda.is_available() else 0.0,
        "checkpoint": str(save_dir / "model.pt"),
        "curve": curve,
    }
    (save_dir / "curve.json").write_text(json.dumps(meta, indent=2))
    return meta


def load_policy_checkpoint(ckpt_path: Path | str, device: str = "cuda") -> tuple[DiscoPolicyNet, dict[str, Any]]:
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = DiscoPolicyNet(ck["domain"], h=ck.get("hidden", 128)).to(device)
    model.load_state_dict(ck["state_dict"])
    model.obj_trained = bool(ck.get("obj_trained", False))
    model.eval()
    return model, ck


def evaluate_p0_on_q2(
    dom: str,
    ckpt_path: Path | str,
    split: str = "val",
    Ms: tuple[int, ...] = (1, 2, 4, 8, 16),
    device: str = "cuda",
) -> dict[str, Any]:
    """Compare P0 categorical destination policy against Uniform legal-cell sampling on held-out Q2 contexts."""
    dom_l = dom.lower()
    model, ck = load_policy_checkpoint(ckpt_path, device=device)
    q2 = D.load_q2_dataset(dom_l)
    scalers = q2["scalers"]
    R, C = GRID[dom_l]
    N = R * C
    max_o = MAXOBJ[dom_l]

    raw_obj = q2["obj"]
    raw_mask = q2["mask"]
    if raw_obj.shape[1] < max_o:
        pad_n = max_o - raw_obj.shape[1]
        raw_obj = np.pad(raw_obj, ((0, 0), (0, pad_n), (0, 0)))
        raw_mask = np.pad(raw_mask, ((0, 0), (0, pad_n)))

    mu = np.asarray(scalers["mean"], dtype=np.float32)
    sd = np.asarray(scalers["std"], dtype=np.float32)
    obj_norm = (raw_obj - mu) / sd * raw_mask[..., None]
    tdim = task_dim(dom_l)
    occ_task = np.concatenate([q2["occ"], np.zeros((len(q2["occ"]), tdim), dtype=np.float32)], axis=1)

    # Group by unique context
    ctx_arr = q2["ctx"]
    n_ctx = int(ctx_arr.max()) + 1
    first_row = np.full(n_ctx, -1, dtype=np.int64)
    for i, c in enumerate(ctx_arr):
        if first_row[c] < 0:
            first_row[c] = i
    pos_mat = np.zeros((n_ctx, N), dtype=bool)
    neg_mat = np.zeros((n_ctx, N), dtype=bool)
    lab = q2["label"]
    dst = q2["dest"]
    pos_mat[ctx_arr[lab == 1], dst[lab == 1]] = True
    neg_mat[ctx_arr[lab == 0], dst[lab == 0]] = True

    sp_idx = D.SPLITS.index(split)
    ctx_split = q2["split"][first_row]
    eval_ctxs = np.flatnonzero((ctx_split == sp_idx) & (pos_mat.any(axis=1) | neg_mat.any(axis=1)))
    rows = first_row[eval_ctxs]

    with torch.no_grad():
        t_obj = torch.as_tensor(obj_norm[rows], dtype=torch.float32, device=device)
        t_mask = torch.as_tensor(raw_mask[rows], dtype=torch.bool, device=device)
        t_ot = torch.as_tensor(occ_task[rows], dtype=torch.float32, device=device)
        t_leg = torch.as_tensor(q2["legal"][rows], dtype=torch.bool, device=device)
        logits = model.forward_dst(t_obj, t_mask, t_ot, t_leg)
        probs_p0 = logits.softmax(dim=-1).cpu().numpy()

    leg_np = q2["legal"][rows]
    probs_uni = leg_np.astype(np.float32) / np.maximum(leg_np.sum(axis=1, keepdims=True), 1)
    pos_sub = pos_mat[eval_ctxs]
    neg_sub = neg_mat[eval_ctxs]

    # Compute entropy over legal cells
    ent_p0 = float(np.mean([-np.sum(p[p > 1e-12] * np.log(p[p > 1e-12])) for p in probs_p0]))
    ent_uni = float(np.mean([-np.sum(p[p > 1e-12] * np.log(p[p > 1e-12])) for p in probs_uni]))

    results = {"domain": dom_l, "split": split, "n_contexts": int(len(eval_ctxs)), "entropy_p0": ent_p0, "entropy_uniform": ent_uni, "arms": {}}
    rng = np.random.default_rng(0)

    for arm_name, p_mat in (("p0", probs_p0), ("uniform", probs_uni)):
        per_m = {}
        for M in Ms:
            hits, precs, uniqs = [], [], []
            for i in range(len(eval_ctxs)):
                leg_cells = np.flatnonzero(leg_np[i])
                k = min(M, len(leg_cells))
                if arm_name == "p0":
                    # Top-k by probability for deterministic ranking + stochastic sample comparison
                    p_row = p_mat[i, leg_cells]
                    p_row = np.maximum(p_row, 1e-12)
                    p_row = p_row / p_row.sum()
                    chosen = leg_cells[rng.choice(len(leg_cells), size=k, replace=False, p=p_row)]
                else:
                    chosen = rng.choice(leg_cells, size=k, replace=False)
                uniqs.append(len(chosen))
                if pos_sub[i].any():
                    hits.append(float(any(pos_sub[i, c] for c in chosen)))
                kn = [c for c in chosen if pos_sub[i, c] or neg_sub[i, c]]
                if kn:
                    precs.append(float(sum(pos_sub[i, c] for c in kn)) / len(kn))
            per_m[str(M)] = {
                "hit_rate": round(float(np.mean(hits)), 4),
                "known_precision": round(float(np.mean(precs)), 4) if precs else None,
                "mean_unique": round(float(np.mean(uniqs)), 2),
            }
        results["arms"][arm_name] = per_m
    return results


def _eval_one_step_root_worker(args: tuple[str, dict[str, Any], dict[str, list[tuple[int, int]]], int]) -> dict[str, Any]:
    dom_l, row, cands_by_arm, seed = args
    env = E.RepairEnv(dom_l)
    rid = row["root_id"]
    s0 = env.reset(rid, seed=seed)
    res_by_arm = {}
    for arm_name, cands in cands_by_arm.items():
        n_total = len(cands)
        n_legal = 0
        n_exec = 0
        n_failed = 0
        times = []
        fail_kinds: dict[str, int] = {}
        for act in cands:
            if not D.validate_repair_sequence(row["inputs"], dom_l, [act]):
                n_legal += 1
            sr = env.transition(s0, act)
            times.append(sr.time_s)
            if sr.status == "EXECUTED":
                n_exec += 1
            else:
                n_failed += 1
                fk = sr.failure_kind or "UNKNOWN"
                fail_kinds[fk] = fail_kinds.get(fk, 0) + 1
        res_by_arm[arm_name] = {
            "n_total": n_total,
            "n_legal": n_legal,
            "n_exec": n_exec,
            "n_failed": n_failed,
            "unique_ratio": len(set(cands)) / max(len(cands), 1),
            "times": times,
            "fail_kinds": fail_kinds,
        }
    return res_by_arm


def validate_p0_physical_transitions(
    dom: str,
    ckpt_path: Path | str,
    n_roots: int = 10,
    B_sample: int = 4,
    seed: int = 0,
    device: str = "cuda",
) -> dict[str, Any]:
    """Validate P0 vs Uniform sampled actions on actual stateful physical transitions (`RepairEnv.transition`)
    on a deterministic subset of TRAIN roots (`DISCO_plan.md` Section 9.1 item 2).
    """
    import hashlib
    import multiprocessing as mp
    dom_l = dom.lower()
    model, ck = load_policy_checkpoint(ckpt_path, device=device)
    scalers = ck["scalers"]

    train_rows = [r for r in D.load_snapshot_rows(dom_l, "train") if r["K_legacy"] in ("1", "2", "3")]
    train_rows.sort(key=lambda r: hashlib.sha256(f"d2_phys|{r['root_id']}".encode()).hexdigest())
    cohort = train_rows[:n_roots]

    p0_wrap = PolicyProposalWrapper(dom_l, model, scalers, device=device, mode="p0")
    uni_wrap = PolicyProposalWrapper(dom_l, None, scalers, device=device, mode="uniform")

    # Pre-sample candidate actions per root for both arms on GPU
    jobs = []
    for idx_r, r in enumerate(cohort):
        inp = r["inputs"]
        leg = D.legal_actions_at_prefix(inp, dom_l, [])
        obs0 = E.LearnerObservation(
            root_id=r["root_id"],
            domain=dom_l,
            ids=list(inp["ids"]),
            cells=list(inp["cells0"]),
            xy=list(inp["xy0"]),
            attrs=list(inp["attrs"]),
            tid=int(inp["tid"]),
            goal_cell=int(inp["goal_cell"]),
            goal_xy=list(inp["goal"]),
            base_xy=list(inp["base"]),
            ctx=list(inp["ctx"]),
            legal_cells=list(inp["legal_cells"]),
            cell_xy=dict(inp["cell_xy"]),
            moved_mask=[False] * len(inp["ids"]),
            remaining_steps=3,
            eligible_objects=leg["eligible_objects"],
            legal_destinations=leg["legal_destinations"],
        )
        cands_by_arm = {}
        for arm_name, wrap in (("p0", p0_wrap), ("uniform", uni_wrap)):
            rng = np.random.default_rng(seed + 1000 * idx_r + (0 if arm_name == "p0" else 500))
            cands_by_arm[arm_name] = wrap.sample_candidates(obs0, B=B_sample, rng=rng)["candidates"]
        jobs.append((dom_l, r, cands_by_arm, seed))

    if dom_l == "3d" and len(jobs) > 1:
        with mp.get_context("spawn").Pool(min(8, len(jobs))) as pool:
            worker_outs = pool.map(_eval_one_step_root_worker, jobs)
    else:
        worker_outs = [_eval_one_step_root_worker(j) for j in jobs]

    out_arms = {}
    for arm_name in ("p0", "uniform"):
        n_total = sum(w[arm_name]["n_total"] for w in worker_outs)
        n_legal = sum(w[arm_name]["n_legal"] for w in worker_outs)
        n_exec = sum(w[arm_name]["n_exec"] for w in worker_outs)
        n_failed = sum(w[arm_name]["n_failed"] for w in worker_outs)
        unique_ratios = [w[arm_name]["unique_ratio"] for w in worker_outs]
        times = [t for w in worker_outs for t in w[arm_name]["times"]]
        fail_kinds: dict[str, int] = {}
        for w in worker_outs:
            for fk, cnt in w[arm_name]["fail_kinds"].items():
                fail_kinds[fk] = fail_kinds.get(fk, 0) + cnt
        out_arms[arm_name] = {
            "n_roots": len(cohort),
            "B_sample": B_sample,
            "n_attempted": n_total,
            "legal_rate": round(n_legal / max(n_total, 1), 4),
            "unique_proposal_rate": round(float(np.mean(unique_ratios)) if unique_ratios else 1.0, 4),
            "verified_execution_rate": round(n_exec / max(n_total, 1), 4),
            "n_executed": n_exec,
            "n_failed": n_failed,
            "mean_step_time_s": round(float(np.mean(times)) if times else 0.0, 4),
            "total_step_time_s": round(float(np.sum(times)), 2),
            "failure_kinds": fail_kinds,
        }
    return {"domain": dom_l, "n_roots": len(cohort), "B_sample": B_sample, "arms": out_arms}


def run_d2_pipeline(seeds: tuple[int, ...] = (0, 1, 2), device: str = "cuda") -> dict[str, Any]:
    """Train P0 for 2D and 3D across seeds, evaluate on held-out Q2 val, and run physical transition checks."""
    summary: dict[str, Any] = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "domains": {}}
    for dom in ("2d", "3d"):
        runs = []
        q2_evals = []
        for s in seeds:
            tr_meta = train_p0(dom, seed=s, epochs=40, batch_size=512, lr=1e-3, hidden=128, device=device)
            ev_val = evaluate_p0_on_q2(dom, tr_meta["checkpoint"], split="val", device=device)
            runs.append(tr_meta)
            q2_evals.append(ev_val)
        # Physical one-step validation on seed 0 checkpoint (10 roots in 2D, 5 roots in 3D, B=4 per root)
        n_r = 10 if dom == "2d" else 5
        phys_val = validate_p0_physical_transitions(dom, runs[0]["checkpoint"], n_roots=n_r, B_sample=4, seed=0, device=device)

        # Save a sample heatmap for visualization on the first TRAIN K2 root
        model0, ck0 = load_policy_checkpoint(runs[0]["checkpoint"], device=device)
        wrap0 = PolicyProposalWrapper(dom, model0, ck0["scalers"], device=device, mode="p0")
        row0 = next(r for r in D.load_snapshot_rows(dom, "train") if r["K_legacy"] == "2")
        inp0 = row0["inputs"]
        leg0 = D.legal_actions_at_prefix(inp0, dom, [])
        obs0 = E.LearnerObservation(
            root_id=row0["root_id"],
            domain=dom,
            ids=list(inp0["ids"]),
            cells=list(inp0["cells0"]),
            xy=list(inp0["xy0"]),
            attrs=list(inp0["attrs"]),
            tid=int(inp0["tid"]),
            goal_cell=int(inp0["goal_cell"]),
            goal_xy=list(inp0["goal"]),
            base_xy=list(inp0["base"]),
            ctx=list(inp0["ctx"]),
            legal_cells=list(inp0["legal_cells"]),
            cell_xy=dict(inp0["cell_xy"]),
            moved_mask=[False] * len(inp0["ids"]),
            remaining_steps=3,
            eligible_objects=leg0["eligible_objects"],
            legal_destinations=leg0["legal_destinations"],
        )
        dist0 = wrap0.action_distribution(obs0)
        q_obj = obs0.eligible_objects[0]
        heatmap_sample = {
            "root_id": row0["root_id"],
            "queried_obj_idx": q_obj,
            "queried_obj_id": obs0.ids[q_obj],
            "queried_obj_cell": obs0.cells[q_obj],
            "cells0": obs0.cells,
            "goal_cell": obs0.goal_cell,
            "legal_destinations": obs0.legal_destinations,
            "p0_dst_probs": dist0["dst_probs_by_obj"][q_obj].tolist(),
        }

        summary["domains"][dom] = {
            "seeds": list(seeds),
            "train_runs": [{k: v for k, v in r.items() if k != "curve"} for r in runs],
            "curves": {str(s): runs[i]["curve"] for i, s in enumerate(seeds)},
            "q2_val_evals": q2_evals,
            "physical_one_step_validation": phys_val,
            "heatmap_sample": heatmap_sample,
        }

    out_f = HERE / "reports/d2_p0_summary.json"
    out_f.parent.mkdir(parents=True, exist_ok=True)
    out_f.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    if sys.argv[1:2] == ["train_p0"]:
        dom_arg = sys.argv[2]
        seed_arg = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        res = train_p0(dom_arg, seed=seed_arg)
        print(json.dumps({k: v for k, v in res.items() if k != "curve"}))
    elif sys.argv[1:2] == ["run_d2"]:
        s = run_d2_pipeline()
        print(json.dumps({"d2_done": list(s["domains"].keys())}))
