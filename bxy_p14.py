"""BXY-P14 bounded repair-learning design (implements runs/approach_b/bxy_p13_v1/P14_HYPOTHESES.json, frozen before this file existed).

Arms (5 family-grouped folds over the 176 original TRAIN roots x 3 seeds = 75 runs; val21 and the 34 exposed test roots never appear):
  DIRECT        bxy_p11 DIRECT, retrained on the P14 folds
  XYQ           bxy_p11 XY-quadratic, lambda_J = 1.0 (P12 lambda*), exact joint NLL + travel (the original objective)
  XYQ+CON       + kappa * matched within-root Y contrast (auxiliary loss, explicitly NOT part of the exact likelihood):
                l_root = n_obsY * mean over (s, t) with y_s = 1, y_t = 0 of softplus(-(b_s - b_t)); batch mean over roots (0 without a pair)
  XYQ+GEO       + geometry-aware control on the Y unary: b_s += mlp(8 -> 128 -> 1)(phi(S_s)), phi = 8 clearances computed from the scorer's
                own tensors only (bxy_p13.geo_features; distances in cell units / 0.08 m, counts raw)
  XYQ+CON+GEO   both
Everything else is bxy_p11 unchanged: probability semantics, F1, candidates, TRAIN (AdamW, clip, batches, early stopping on the exact
joint NLL / DIRECT success BCE), predictions. Selection rules: PRIMARY (P11.1) and PONLY (penalty-free -log p, no-op included)."""
from __future__ import annotations

import contextlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

import bxy_core as X
import bxy_p11 as P
import bxy_p11_1 as A
import bxy_p13 as Q
from abc_models import mlp

OUT = Path("runs/approach_b/bxy_p14_v1")
HYPOTHESES = Q.OUT / "P14_HYPOTHESES.json"
HYPOTHESES_SHA = "8c3b62395629bd1910793e0a016fc62ce856f0bfa89d20f516d0efe7fa24ee72"
ARMS = {"DIRECT": {"base": "DIRECT", "lam": 0.0, "con": False, "geo": False},
        "XYQ": {"base": "XY-quadratic", "lam": 1.0, "con": False, "geo": False},
        "XYQ+CON": {"base": "XY-quadratic", "lam": 1.0, "con": True, "geo": False},
        "XYQ+GEO": {"base": "XY-quadratic", "lam": 1.0, "con": False, "geo": True},
        "XYQ+CON+GEO": {"base": "XY-quadratic", "lam": 1.0, "con": True, "geo": True}}
KAPPA = 1.0
GEO_DIST = (0, 1, 2, 3, 6, 7)                                     # indices of geo_features that are distances (scaled to cell units)
RULES = {"PRIMARY": lambda arm: A.PRIMARY | {"gamma": 0.05 if ARMS[arm]["lam"] else 0.0},
         "PONLY": lambda arm: A.PRIMARY | {"alpha": 0.0, "beta": 0.0, "gamma": 0.0}}
CONTRASTS = {"C1": (("XYQ+CON", "PRIMARY"), ("XYQ", "PRIMARY")), "C2": (("XYQ+GEO", "PRIMARY"), ("XYQ", "PRIMARY")),
             "C3": (("XYQ+CON+GEO", "PRIMARY"), ("XYQ", "PRIMARY")), "C5": (("XYQ+CON+GEO", "PONLY"), ("XYQ", "PRIMARY"))}
C4 = {a: ((a, "PONLY"), (a, "PRIMARY")) for a in ARMS}
LIMITS = {"aggregate_cpu_s": 45000, "per_run_cpu_s": 1500, "workers": 4, "wall_s": 21600, "runs": 75, "torch_threads": 1}
RESERVE = {"evaluation_cpu_s": 3000, "evaluation_wall_s": 1200}


# ------------------------------------------------------------------ model and losses
def phi(Rt, edit) -> list:
    f = Q.geo_features(Rt, edit)
    return [v / 0.08 if i in GEO_DIST else v for i, v in enumerate(f)]


class Model(P.Model):
    """bxy_p11.Model of the arm's base, plus the GEO head on the Y unary when the arm has it (base modules are built first, so a non-GEO
    arm is initialized exactly like bxy_p11.build_model(base, seed))."""

    def __init__(self, arm):
        super().__init__(ARMS[arm]["base"])
        self.arm14 = arm
        if ARMS[arm]["geo"]:
            self.geo = mlp(8, 1)

    def coeffs(self, sv) -> dict:
        C = super().coeffs(sv)
        if hasattr(self, "geo"):
            f = torch.tensor([phi(sv["R"], p) for p in sv["y_poses"]], dtype=X.D)
            C["b"] = C["b"] + self.geo(f)[:, 0]
        return C


def build_model(arm, seed=None) -> Model:
    if seed is not None:
        torch.manual_seed(seed)
    return Model(arm).double()


def contrast(b, obs_y) -> torch.Tensor:
    pos = [s for s, y in obs_y.items() if y == 1]
    neg = [s for s, y in obs_y.items() if y == 0]
    if not pos or not neg:
        return b.new_zeros(())
    d = b[torch.tensor(pos)][:, None] - b[torch.tensor(neg)][None, :]
    return len(obs_y) * F.softplus(-d).mean()


def batch_loss(m, svs, labs, lam, kappa=KAPPA):
    """bxy_p11.batch_loss for arms without CON (identical call); with CON the same joint NLL / travel terms (one coefficient pass per root)
    plus kappa * the batch mean of the matched Y contrast."""
    if not ARMS[m.arm14]["con"]:
        return P.batch_loss(m, svs, labs, lam)
    nll, jp, jo, cl = [], [], [], []
    for sv, lab in zip(svs, labs):
        C = m.coeffs(sv)
        nll.append(-P.log_evidence(C["b"], C["a"], C["w"], sv["parent"], lab["obs_x"], lab["obs_y"]))
        jp.append(torch.stack([C["J0"] if i is None else C["J"][i] for i, _, _ in lab["j"]]) if lab["j"] else torch.zeros(0, dtype=X.D))
        jo.append(torch.tensor([j for *_, j in lab["j"]], dtype=X.D))
        cl.append(contrast(C["b"], lab["obs_y"]))
    nll, jp, jo, con = torch.stack(nll).mean(), torch.cat(jp), torch.cat(jo), torch.stack(cl).mean()
    tr = F.huber_loss(torch.log1p(jp), torch.log1p(jo), reduction="sum", delta=P.TRAIN["huber_delta"]) / len(jp) if len(jp) else None
    tot = (nll + lam * tr if (lam and tr is not None) else nll) + kappa * con
    return tot, {"nll": float(nll.detach()), "travel": None if tr is None else float(tr.detach()), "contrast": float(con.detach())}


@contextlib.contextmanager
def arm_hooks(arm):
    """Inside a P14 worker process only: bxy_p12_run.fit_resumable (the frozen, bitwise-tested trainer loop) builds its model and batch loss
    through bxy_p11.build_model / bxy_p11.batch_loss; this binds them to the P14 arm for the duration of one run and restores them."""
    old = P.build_model, P.batch_loss
    orig_loss = old[1]
    P.build_model = lambda _a, seed=None: build_model(arm, seed)
    P.batch_loss = lambda m, svs, labs, lam, tau=X.TAU: (orig_loss(m, svs, labs, lam, tau) if not ARMS[arm]["con"] else batch_loss(m, svs, labs, lam))
    try:
        yield
    finally:
        P.build_model, P.batch_loss = old


# ------------------------------------------------------------------ design
def folds() -> dict:
    """5 family-grouped folds over the 176 TRAIN roots only (bxy_p11.folds procedure: stratified by family stratum, hash order, early-stop
    subset inside each training part)."""
    D, R = json.loads((P.PM.OUT / "PMIN_DESIGN.json").read_text()), P.bd.roots()
    tr = [k for k in D["root_order"] if P.bd.split_of(R[k]) == "train"]
    return P.folds({"root_order": tr, "roots": D["roots"]}, R) | {"roots": tr}


def roster() -> list:
    return [{"id": f"cv/f{f}/{a}/s{s}", "phase": "CROSSFIT", "arm": a, "lambda_J": ARMS[a]["lam"], "seed": s, "train": f"fold{f}.train",
             "early_stop": f"fold{f}.early_stop", "heldout": f"fold{f}.heldout"} for f in range(P.FOLDS) for a in ARMS for s in P.SEEDS]


def design() -> dict:
    fo = folds()
    held = sorted(k for f in fo["folds"] for k in f["heldout"])
    if held != sorted(fo["roots"]) or len(held) != 176:
        raise RuntimeError("P14 folds must hold out each of the 176 TRAIN roots exactly once")
    return {"version": "BXY_P14_DESIGN_V1", "gate": "BXY-P14", "date": "2026-11-01", "hypotheses_sha256": HYPOTHESES_SHA,
            "parents": {"p11_design_sha256": P.sha(P.OUT / "TRAINING_DESIGN.json"), "p11_1_design_sha256": P.sha(A.OUT / "TRAINING_DESIGN_P11_1.json"),
                        "evidence_sha256": P.EVIDENCE},
            "arms": ARMS, "kappa": KAPPA, "geo": {"features": "bxy_p13.geo_features (8 clearances from scorer tensors)", "distance_scale_m": 0.08,
                                                   "head": "mlp(8 -> 128 -> 1) added to the Y unary b only"},
            "training": P.TRAIN | {"early_stopping": "exact joint NLL (XY arms) / success BCE (DIRECT) on the fold's early-stop roots, every arm"},
            "selection": {"PRIMARY": {a: RULES["PRIMARY"](a) for a in ARMS}, "PONLY": {a: RULES["PONLY"](a) for a in ARMS}},
            "contrasts": {k: [list(x) for x in v] for k, v in CONTRASTS.items()} | {"C4": {a: [list(x) for x in v] for a, v in C4.items()}},
            "decision": json.loads(HYPOTHESES.read_text())["decision"], "endpoints": json.loads(HYPOTHESES.read_text())["endpoints"],
            "folds": {"folds": fo["folds"], "family_stratum": fo["family_stratum"]}, "roster": roster(),
            "limits": LIMITS, "reserve_inside_limits": RESERVE,
            "budget": {"per_run_expected_cpu_s": {a: 450.0 for a in ARMS}, "basis": "P12 CROSSFIT median 324 CPU-s per run (max 505) on ~135 "
                       "training roots; P14 trains on ~120 roots; CON adds one contrast term per root, GEO 8 clearances per scene"}}


def freeze() -> str:
    if P.sha(HYPOTHESES) != HYPOTHESES_SHA:
        raise RuntimeError("P14 hypotheses changed after freezing")
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "TRAINING_DESIGN_P14.json"
    txt = json.dumps(design(), indent=1, sort_keys=True, default=str)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("P14 design already frozen with different content")
    f.write_text(txt)
    return P.sha(f)


def frozen() -> dict:
    d = json.loads((OUT / "TRAINING_DESIGN_P14.json").read_text())
    if d["roster"] != roster() or d["hypotheses_sha256"] != P.sha(HYPOTHESES):
        raise RuntimeError("P14 design drift")
    return d


if __name__ == "__main__":
    t = time.time()
    print(freeze(), time.time() - t)
