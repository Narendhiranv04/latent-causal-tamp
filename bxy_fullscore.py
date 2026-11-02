"""BXY-P28 frozen learned scoring of ARBITRARY universal-domain candidates (no learning, no labels, no teacher).

view() builds the unchanged bxy_p11 ScorerView contract (SCORER_KEYS / CAND_KEYS / FORBIDDEN, checked) for any list of domain members:
the label-free root tensors (bxy_p16_inputs cache: scene, goal_cell, q0 = q_ref only), x_seqs = each non-empty member's ORDERED actions as
(object index, destination centre), y_poses = one entry per distinct EDITED ENDPOINT (bxy_fullspace.ysig; permutations share it), parent,
y0 = the unedited scene. Every member is scored ('admissible' = scored); the F1 terminal rule (GOAL_BLOCKED) is applied by the search, which
never selects such a node. Per-candidate outputs do not depend on the other candidates of the chunk (bxy_core.marginals is element-wise and
the memo lives inside one coeffs call), so chunked / streamed scoring equals scoring through one legacy view (tested).
Scores come from the frozen 15-member D / E / DIRECT-GEO / G ensembles of P23 (checkpoint hashes verified by bxy_p24_confirm.load_member)
and their mean rule (bxy_p24_confirm.ensemble). Search cost of a member under a rule (alpha, beta, gamma, noop_gate):
    C(r) = -log max(p, 1e-12) + alpha m + beta C_d + gamma J_hat;  the no-op ranks first when P(Y0) >= noop_gate (verified first)."""
from __future__ import annotations

import math
import time
from pathlib import Path

import bxy_fullspace as S
import bxy_p11 as P
import bxy_p17 as M
import bxy_p24_confirm as C

ARMS = C.ARMS
EPS = 1e-12
GATE_COST = -1e6
INPUTS = (Path("runs/approach_b/bxy_p21_v1/INPUTS_K34.pt"), Path("runs/approach_b/bxy_p16_v1/inputs/INPUTS_V21.pt"))
_ROOT = {}


def inputs() -> dict:
    """Label-free development root tensors (bxy_p16_inputs contract; built and hashed in P16 / P21, read-only here)."""
    import torch
    out = {}
    for f in INPUTS:
        out.update(torch.load(f, weights_only=False)["roots"])
    return out


def _root(key, inp):
    import abc_models as am
    if _ROOT.get("key") != key:
        _ROOT.clear()
        _ROOT.update(key=key, R=am.Root({"inputs": inp["inputs"]}))
    return _ROOT["R"]


def view(key, rec, inp, seqs) -> dict:
    """Dynamic label-free ScorerView of the given members (deduplicated by xsig; Y deduplicated by edited endpoint; Y0 always present)."""
    from scene import scene_from_dict
    D, lat, ids = S.domain(rec), scene_from_dict(rec["scene"]).lattice, inp["ids"]
    ys, y_poses, x_seqs, parent, cands, seen = {}, [], [], [], [], set()

    def yid(seq):
        k = S.ysig(D, seq)
        if k not in ys:
            ys[k] = len(y_poses)
            y_poses.append({ids.index(o): tuple(lat.center(int(c))) for o, c in S.endpoint(D, seq).items()})
        return ys[k]
    y0 = yid(())
    for seq in seqs:
        seq = tuple((o, int(d)) for o, d in seq)
        why = S.classify(D, seq)
        if why:
            raise ValueError(f"{S.xsig(seq)} is outside the domain ({why})")
        s = S.xsig(seq)
        if s in seen:
            continue
        seen.add(s)
        yi, xi = yid(seq), None
        if seq:
            xi = len(x_seqs)
            x_seqs.append([(ids.index(o), tuple(lat.center(int(c)))) for o, c in seq])
            parent.append(yi)
        cands.append({"sig": s, "m": len(seq), "cd": P.cd_cells(rec, list(seq)), "xi": xi, "yi": yi, "admissible": True})
    sv = {"key": key, "R": _root(key, inp), "y_poses": y_poses, "x_seqs": x_seqs, "parent": parent, "y0": y0, "cands": cands}
    P.check_scorer(sv)
    return sv


def cost(row, rule) -> float:
    if row["m"] == 0 and rule.get("noop_gate") is not None and row["p"] >= rule["noop_gate"]:
        return GATE_COST
    return -math.log(max(row["p"], EPS)) + rule["alpha"] * row["m"] + rule.get("beta", 0.0) * row["cd"] + rule["gamma"] * (row.get("J_hat") or 0.0)


class Scorer:
    """cost(list of members) -> list of floats for one arm's frozen ensemble and rule; keeps every scored row (p, px, py, J_hat) and the
    model CPU / call counts. Chunks bound memory; the GEO2 feature cache is cleared when it grows past `phi_cap` entries."""

    def __init__(self, key, rec, inp, arm, nets, rule, chunk=400, phi_cap=200000):
        self.key, self.rec, self.inp, self.arm, self.nets, self.rule, self.chunk, self.phi_cap = key, rec, inp, arm, nets, rule, chunk, phi_cap
        self.rows, self.cpu_s, self.calls = {}, 0.0, 0

    def score(self, seqs) -> dict:
        c0 = time.process_time()
        out = {}
        for i in range(0, len(seqs), self.chunk):
            sv = view(self.key, self.rec, self.inp, seqs[i:i + self.chunk])
            for r in C.ensemble(self.arm, self.nets, sv)["cands"]:
                out[r["sig"]] = {k: r.get(k) for k in ("m", "cd", "p", "px", "py", "J_hat")}
            if len(M._PHI) > self.phi_cap:
                M._PHI.clear()
        self.cpu_s += time.process_time() - c0
        self.calls += len(seqs)
        self.rows.update(out)
        return out

    def __call__(self, seqs) -> list:
        rows = self.score(list(seqs))
        return [cost(rows[S.xsig(s)], self.rule) for s in seqs]
