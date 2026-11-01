"""BXY-P17 targeted-learning design (frozen before any P17 optimizer step; entered only after the P16 DATA_READY decision).

Data: every development triple of bxy_p17_data.build_all -- PMIN (176 TRAIN + 21 VAL, outcome-guided historical catalogues), P15 (28 BXY_GEN_V2
pilot roots) and V21 (BXY_GEN_V21 / V21B waves). 5 family-grouped folds over all of them (a P-min family with its variants and reversed /
omitted queries stays in one fold; each new root is its own family), stratified by corpus x difficulty intent; an early-stop subset of ~1/5
of each fold's training families. The 34 exposed P-min test roots and every confirmatory namespace never appear.

Arms (6 x 5 folds x 3 seeds = 90 runs; F of the contract's menu is REPLACED, before launch, by the order-invariant control G):
  A DIRECT-GEO        bxy_p11 DIRECT (scene-aware success logit) + GEO2 on the success logits (geoY of the endpoint scene, geoX of the prefix)
  B XYQ-BASE          bxy_p11 XY-quadratic, lambda_J = 1, exact joint NLL + travel; no GEO, no contrast (matched baseline)
  C XYQ-GEO-CON       B + GEO2 + the frozen P14 contrast (kappa 1)
  D XYQ-GEO-SYM       B + GEO2 + the symmetric within-root edit contrast SYM (kappa 1)          <- primary candidate (pre-declared)
  E XY-UNC-SA-GEO-SYM D with w = 0 and the scene-aware xs head (capacity-matched uncoupled control)
  G XYQ-GEO-SYM-ORDINV D with an order-invariant F2 of identical capacity (prefix-free tokens, unordered pair mixing) and S0-evaluated
                      action access features (phi_X0); tests whether order-aware F2 matters
Why G replaces F (XYQ-GEO-SYM-noJ): the travel auxiliary's effect on feasibility was already measured (P11/P12 XY-quadratic-noJ); order
reasoning has never had a trained control and is a named weakness (P13: certified order ranking ~chance). Travel-blind SELECTION is still
evaluated on every XY arm with gamma = 0 (evaluation-only rule), and travel is assessed on matched successful roots.

GEO2 (bxy_p17_data, analytic, scorer tensors only): geoY = mlp(13 -> 1)(P14 8 clearances + 5 access features) added to the Y unary b (XY)
/ to the DIRECT success logits; geoX = mlp(8 -> 1)(action access statistics) added to the X unary a (XY) / DIRECT success logit.
SYM (auxiliary; the exact joint NLL stays the core and is logged separately): within a root with observed Y0, for every observed edited Y_s:
  (Y0, Ys) = (0, 1): softplus(-(b_s - b_0));  (1, 0): softplus(-(b_0 - b_s));  (0, 0) / (1, 1): softplus(|b_s - b_0| - 1);
  root loss = mean of [mean over 01 pairs, mean over 10 pairs, mean over concordant pairs] (present groups only) + the P14 contrast over
  discordant EDITED-edited pairs (n_obsY-weighted like P14 / n_obsY), batch mean over roots. Labels enter only the loss.
Selection: one rule per (arm, fold) chosen on the fold's early-stop roots (3 seeds pooled, never the held-out fold) from the grid
noop_gate in {None, 0.5, 0.7} x alpha in {0, 0.1, 0.3} (beta 0, eta 0, gamma 0.05 for travel-trained arms else 0): maximize early-stop
corrective success on infeasible roots subject to early-stop unnecessary repairs on feasible roots <= 0.10; ties -> fewer unnecessary
repairs, larger alpha, stricter gate; none feasible -> the rule with the fewest unnecessary repairs. P11.1 PRIMARY is a fixed-rule sensitivity."""
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
import bxy_p13 as Q
import bxy_p14 as H14
import bxy_p17_data as DATA
from abc_models import W, mlp

OUT = DATA.OUT
ARMS = {"A:DIRECT-GEO": {"base": "DIRECT", "lam": 0.0, "geo": True, "loss": None, "order": "pred"},
        "B:XYQ-BASE": {"base": "XY-quadratic", "lam": 1.0, "geo": False, "loss": None, "order": "pred"},
        "C:XYQ-GEO-CON": {"base": "XY-quadratic", "lam": 1.0, "geo": True, "loss": "CON", "order": "pred"},
        "D:XYQ-GEO-SYM": {"base": "XY-quadratic", "lam": 1.0, "geo": True, "loss": "SYM", "order": "pred"},
        "E:XY-UNC-SA-GEO-SYM": {"base": "XY-uncoupled-SA", "lam": 1.0, "geo": True, "loss": "SYM", "order": "pred"},
        "G:XYQ-GEO-SYM-ORDINV": {"base": "XY-quadratic", "lam": 1.0, "geo": True, "loss": "SYM", "order": "invariant"}}
KAPPA = 1.0
FOLDS, ES_EVERY, SEEDS = 5, 5, (0, 1, 2)
GRID = [{"noop_gate": g, "alpha": a} for g in (None, 0.5, 0.7) for a in (0.0, 0.1, 0.3)]
U_MAX = 0.10
CONTRASTS = {"P1_SYM_vs_BASE": ("D:XYQ-GEO-SYM", "B:XYQ-BASE"), "P2_SYM_vs_DIRECT": ("D:XYQ-GEO-SYM", "A:DIRECT-GEO"),
             "P3_COUPLING": ("D:XYQ-GEO-SYM", "E:XY-UNC-SA-GEO-SYM"), "P4_SYM_vs_CON": ("D:XYQ-GEO-SYM", "C:XYQ-GEO-CON"),
             "P5_ORDER": ("D:XYQ-GEO-SYM", "G:XYQ-GEO-SYM-ORDINV")}
DECISION = {"IMPROVES_WITHIN_GUARDRAIL": "P1 / P4: paired 95% CI lower bound of Delta corrective success on initially infeasible OUTCOME-BLIND "
            "roots > 0, point Delta >= 0.10, point Delta unnecessary repairs on feasible outcome-blind roots <= 0.05",
            "PROMISING_BUT_GUARDRAIL_FAILED": "Delta success CI lower > 0 but Delta unnecessary > 0.05 or point gain < 0.10",
            "SUPERIOR_TO_DIRECT": "P2: Delta success 95% CI lower > 0 AND Delta unnecessary point <= 0.02 AND its 95% CI upper <= 0.05",
            "COUPLING_SUPPORTED": "P3: D better than E on root-averaged held-out joint NLL of observed X/Y (95% CI excludes 0 in D's favour) or "
                                  "IMPROVES_WITHIN_GUARDRAIL on selection; otherwise coupling unsupported",
            "ORDER_SUPPORTED": "P5: D's order concordance on measured F1-admissible same-endpoint X-discordant pairs exceeds G's (95% CI of the "
                               "root-level difference excludes 0) -- with G trained, not evaluation-only",
            "INCONCLUSIVE / NEGATIVE": "otherwise; the population of record is the outcome-blind corpora (P15 + V21), P-min is reported separately",
            "multiplicity": "five pre-declared contrasts; 95% CIs are primary, Bonferroni 99% CIs reported"}
LIMITS = {"aggregate_cpu_s": 48000, "per_run_cpu_s": 1500, "workers": 4, "wall_s": 21600, "runs": 90, "torch_threads": 1}
RESERVE = {"evaluation_cpu_s": 4000, "evaluation_wall_s": 1500}


# ------------------------------------------------------------------ GEO2 features (cached per process; scorer tensors only)
_PHI = {}


def phi_y(sv, s) -> list:
    k = ("y", sv["key"], tuple(sorted(sv["y_poses"][s].items())))
    if k not in _PHI:
        _PHI[k] = H14.phi(sv["R"], sv["y_poses"][s]) + DATA.phi_y(sv["R"], sv["y_poses"][s])
    return _PHI[k]


def phi_x(sv, q, ordered=True) -> list:
    k = ("x", sv["key"], tuple((i, tuple(d)) for i, d in sv["x_seqs"][q]), ordered)
    if k not in _PHI:
        _PHI[k] = DATA.phi_x(sv["R"], sv["x_seqs"][q], ordered)
    return _PHI[k]


# ------------------------------------------------------------------ model
class Model(P.Model):
    """bxy_p11.Model of the arm's base (built first, so B is initialized exactly like bxy_p11.build_model), plus GEO2 heads and, for G, the
    order-invariant F2 with the same predecessor modules applied to prefix-free tokens over all other actions (unordered)."""

    def __init__(self, arm):
        super().__init__(ARMS[arm]["base"])
        self.arm17 = arm
        if ARMS[arm]["geo"]:
            self.geoY, self.geoX = mlp(13, 1), mlp(8, 1)

    def _order(self, R, seq):
        if ARMS[self.arm17]["order"] != "invariant":
            return super()._order(R, seq)
        toks, xy, _ = self.actions(R, seq, False)                         # prefix-free tokens (S0 context): order cannot enter
        n = len(toks)
        rows = [self.mix(torch.cat([a, torch.stack([self.pairo(torch.cat([toks[u], a])) for u in range(n) if u != t]).mean(0) if n > 1
                                    else torch.zeros(W, dtype=torch.float64)])) for t, a in enumerate(toks)]
        g = torch.stack(rows).mean(0) if rows else torch.zeros(W, dtype=torch.float64)
        return self.order_s(torch.cat([g, self.scene_vec(R, xy)]))[0], g, xy

    def coeffs(self, sv) -> dict:
        C = super().coeffs(sv)
        if hasattr(self, "geoY"):
            fy = self.geoY(torch.tensor([phi_y(sv, s) for s in range(len(sv["y_poses"]))], dtype=X.D))[:, 0]
            ordered = ARMS[self.arm17]["order"] != "invariant"
            fx = self.geoX(torch.tensor([phi_x(sv, q, ordered) for q in range(len(sv["x_seqs"]))], dtype=X.D))[:, 0] if sv["x_seqs"] else None
            C["b"] = C["b"] + fy
            if fx is not None:
                C["a"] = C["a"] + fx + (fy[torch.tensor(sv["parent"])] if self.family == "direct" else 0.0)
        return C


def build_model(arm, seed=None) -> Model:
    if seed is not None:
        torch.manual_seed(seed)
    return Model(arm).double()


def sym(b, obs_y, y0) -> torch.Tensor:
    """SYM auxiliary of one root (0 when Y0 is unobserved and there is no discordant edited pair)."""
    parts = []
    if y0 in obs_y:
        g = {"01": [], "10": [], "cc": []}
        for s, y in obs_y.items():
            if s == y0:
                continue
            d = b[s] - b[y0]
            if obs_y[y0] == 0 and y == 1:
                g["01"].append(F.softplus(-d))
            elif obs_y[y0] == 1 and y == 0:
                g["10"].append(F.softplus(d))
            else:
                g["cc"].append(F.softplus(d.abs() - 1.0))
        parts += [torch.stack(v).mean() for v in g.values() if v]
    ed = {s: y for s, y in obs_y.items() if s != y0}
    con = H14.contrast(b, ed) / max(len(ed), 1)
    return (torch.stack(parts).mean() if parts else b.new_zeros(())) + con


def batch_loss(m, svs, labs, lam, kappa=KAPPA):
    """L_joint (root mean exact observed-data NLL; DIRECT: success BCE) + lam * L_J + kappa * auxiliary; terms logged separately."""
    loss = ARMS[m.arm17]["loss"]
    nll, jp, jo, aux = [], [], [], []
    for sv, lab in zip(svs, labs):
        C = m.coeffs(sv)
        if m.family == "xy":
            nll.append(-P.log_evidence(C["b"], C["a"], C["w"], sv["parent"], lab["obs_x"], lab["obs_y"]))
        else:
            lg = torch.stack([C["b"][sv["y0"]] if q is None else C["a"][q] for q in lab["succ"]]) if lab["succ"] else torch.zeros(0, dtype=X.D)
            nll.append(F.binary_cross_entropy_with_logits(lg, torch.tensor([float(v) for v in lab["succ"].values()], dtype=X.D), reduction="sum"))
        jp.append(torch.stack([C["J0"] if i is None else C["J"][i] for i, _, _ in lab["j"]]) if lab["j"] else torch.zeros(0, dtype=X.D))
        jo.append(torch.tensor([j for *_, j in lab["j"]], dtype=X.D))
        if loss == "CON":
            aux.append(H14.contrast(C["b"], lab["obs_y"]))
        elif loss == "SYM":
            aux.append(sym(C["b"], lab["obs_y"], sv["y0"]))
    nll, jp, jo = torch.stack(nll).mean(), torch.cat(jp), torch.cat(jo)
    tr = F.huber_loss(torch.log1p(jp), torch.log1p(jo), reduction="sum", delta=P.TRAIN["huber_delta"]) / len(jp) if len(jp) else None
    tot = nll + lam * tr if (lam and tr is not None) else nll
    a = torch.stack(aux).mean() if aux else None
    if a is not None:
        tot = tot + kappa * a
    return tot, {"nll": float(nll.detach()), "travel": None if tr is None else float(tr.detach()), "aux": None if a is None else float(a.detach())}


@contextlib.contextmanager
def arm_hooks(arm):
    """Inside a P17 worker only: bind bxy_p11.build_model / batch_loss (used by the frozen bxy_p12_run trainer loop) to the P17 arm."""
    old = P.build_model, P.batch_loss
    P.build_model = lambda _a, seed=None: build_model(arm, seed)
    P.batch_loss = lambda m, svs, labs, lam, tau=X.TAU: batch_loss(m, svs, labs, lam)
    try:
        yield
    finally:
        P.build_model, P.batch_loss = old


# ------------------------------------------------------------------ selection rule (inner, early-stop roots only)
def rule_of(arm, g) -> dict:
    return {"noop_gate": g["noop_gate"], "eta": 0.0, "alpha": g["alpha"], "beta": 0.0, "gamma": 0.05 if ARMS[arm]["lam"] else 0.0}


def choose_rule(arm, es_rows) -> dict:
    """es_rows: [(root, y0, rows, success-by-candidate)] pooled over seeds -> the frozen rule of this (arm, fold) and its inner scores."""
    best = None
    for g in GRID:
        r = rule_of(arm, g)
        inf, fea = [], []
        for _, y0, rows, succ in es_rows:
            i = P.choose(rows, r)
            ok = int(i is not None and succ.get(rows[i]["sig"]) == 1)
            (inf if y0 == 0 else fea).append(ok if y0 == 0 else int(i is not None and rows[i]["m"] > 0))
        s, u = (float(np.mean(inf)) if inf else 0.0), (float(np.mean(fea)) if fea else 0.0)
        key = (u <= U_MAX, s if u <= U_MAX else -u, -u, g["alpha"], -1.0 if g["noop_gate"] is None else -g["noop_gate"])
        if best is None or key > best[0]:
            best = (key, r, {"success_inf": s, "unnecessary": u, "n_inf": len(inf), "n_fea": len(fea)})
    return {"rule": best[1], "inner": best[2], "guardrail_met": best[0][0]}


# ------------------------------------------------------------------ folds, roster, design
def strata(V) -> dict:
    """Outcome-free stratum per family: PMIN design stratum (bxy_p11 SEVERITY), P15 K_intent, V21 mechanism x K_intent."""
    D = json.loads((P.PM.OUT / "PMIN_DESIGN.json").read_text())
    st = {}
    for sv, lab, ev in V:
        f = ev["family"]
        s = f"PMIN:{D['roots'][ev['key']]['stratum']}" if ev["corpus"] == "PMIN" else f"{ev['corpus']}:K{ev['K_intent']}" + (f":{ev['mechanism']}" if ev["corpus"] == "V21" else "")
        st.setdefault(f, set()).add(s)
    return {f: sorted(v)[-1] for f, v in st.items()}


def folds(V) -> dict:
    fam = {}
    for sv, lab, ev in V:
        fam.setdefault(ev["family"], []).append(ev["key"])
    st = strata(V)
    fold = {}
    for s in sorted(set(st.values())):
        for i, f in enumerate(sorted((f for f in fam if st[f] == s), key=lambda f: P.PM.bc.sha([f, "BXY_P17_FOLD"]))):
            fold[f] = (i + int(P.PM.bc.sha([s, "BXY_P17_OFFSET"])[:4], 16)) % FOLDS
    out = []
    for j in range(FOLDS):
        pool = sorted(f for f in fam if fold[f] != j)
        es = set()
        for s in sorted(set(st.values())):
            fs = sorted((f for f in pool if st[f] == s), key=lambda f: P.PM.bc.sha([f, "BXY_P17_ES", j]))
            es |= set(fs[:max(1, round(len(fs) / ES_EVERY))] if len(fs) >= 2 else [])
        roots = lambda fs: sorted(k for f in fs for k in fam[f])  # noqa: E731
        out.append({"fold": j, "heldout": roots([f for f in fam if fold[f] == j]), "early_stop": roots(es), "train": roots([f for f in pool if f not in es])})
    return {"folds": out, "family_stratum": st}


def roster() -> list:
    return [{"id": f"cv/f{f}/{a.split(':')[0]}/s{s}", "phase": "CROSSFIT", "arm": a, "lambda_J": ARMS[a]["lam"], "seed": s, "train": f"fold{f}.train",
             "early_stop": f"fold{f}.early_stop", "heldout": f"fold{f}.heldout"} for f in range(FOLDS) for a in ARMS for s in SEEDS]


def design(V=None) -> dict:
    V = V if V is not None else DATA.build_all()
    fo = folds(V)
    keys = sorted(ev["key"] for _, _, ev in V)
    held = sorted(k for f in fo["folds"] for k in f["heldout"])
    if held != keys:
        raise RuntimeError("folds must hold out every development root exactly once")
    corp = {}
    for _, _, ev in V:
        c = corp.setdefault(ev["corpus"], {"roots": 0, "y0_0": 0, "K>=2": 0, "families": set()})
        c["roots"] += 1
        c["y0_0"] += ev["y0"] == 0
        c["K>=2"] += isinstance(ev["verified_K"], int) and ev["verified_K"] >= 2
        c["families"].add(ev["family"])
    corp = {k: dict(v, families=len(v["families"])) for k, v in corp.items()}
    import bxy_p16 as G
    return {"version": "BXY_P17_DESIGN_V1", "gate": "BXY-P17", "date": "2026-11-01", "p16_readiness": json.loads((G.OUT / "READINESS.json").read_text()),
            "data": {"corpora": corp, "roots_sha256": P.PM.bc.sha(keys), "inputs_sha256": {k: P.sha(f) for k, f in DATA.INPUTS.items()},
                     "access_maps_sha256": P.sha(G._maps_file()), "extra_place_maps_sha256": P.sha(DATA.EXTRA_MAPS)},
            "arms": ARMS, "replaced": {"F:XYQ-GEO-SYM-noJ": "replaced by G:XYQ-GEO-SYM-ORDINV before launch (see module docstring)"},
            "kappa": KAPPA, "losses": {"CON": "bxy_p14.contrast (frozen P14 definition)", "SYM": "bxy_p17.sym"},
            "geo2": {"Y": "bxy_p14.phi (8 clearances) + bxy_p17_data.phi_y (5 access features) -> mlp(13, 1)", "X": "bxy_p17_data.phi_x -> mlp(8, 1)",
                     "X_invariant_arm": "phi_x(ordered=False): every action in S0"},
            "training": P.TRAIN | {"early_stopping": "exact joint NLL (XY) / success BCE (DIRECT) on the fold's early-stop roots; auxiliary terms "
                                   "never enter early stopping"},
            "selection": {"grid": GRID, "u_max": U_MAX, "procedure": "choose_rule on early-stop predictions pooled over the 3 seeds of (arm, fold)",
                          "sensitivity": {"P11.1_PRIMARY": "noop_gate None, alpha 0.1, beta 0, eta 0, gamma 0.05 (XY) / 0 (DIRECT)", "travel_blind": "gamma 0"}},
            "endpoints": {"primary": "verified corrective-selection success on initially infeasible OUTCOME-BLIND (P15 + V21) roots, out of fold, "
                          "seed-mean per root, candidate availability and abstention / no-op counts reported",
                          "safety": "unnecessary repairs on initially feasible outcome-blind roots (harmful vs harmless), m, C_d, witnessed J",
                          "representation": "Y0 AUROC / calibration, within-root edited-Y AUROC, edit sign by (0->1)/(1->0), order concordance on measured "
                          "discordant pairs, omission sign, root-averaged joint NLL, Brier, ECE",
                          "secondary_population": "P-min (outcome-guided catalogues) reported separately"},
            "contrasts": CONTRASTS, "decision": DECISION, "folds": fo, "roster": roster(), "limits": LIMITS, "reserve_inside_limits": RESERVE,
            "bootstrap": {"B": 10000, "unit": "family", "seed": 0},
            "budget": {"per_run_expected_cpu_s": {a: 450.0 for a in ARMS}, "basis": "P14: 24,389 CPU-s / 75 runs (325 mean) with ~120 training roots and "
                       "an ~15-root early-stop set; P17 updates cost the same per batch, the early-stop set is ~3x larger and GEO2 adds cached features"}}


def freeze() -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "TRAINING_DESIGN_P17.json"
    txt = json.dumps(design(), indent=1, sort_keys=True, default=str)
    if f.exists() and f.read_text() != txt:
        raise FileExistsError("P17 design already frozen with different content")
    f.write_text(txt)
    return P.sha(f)


def frozen() -> dict:
    d = json.loads((OUT / "TRAINING_DESIGN_P17.json").read_text())
    if d["roster"] != roster():
        raise RuntimeError("P17 design drift")
    return d


if __name__ == "__main__":
    t = time.time()
    print(freeze(), time.time() - t)
