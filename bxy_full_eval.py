"""BXY-P28 matched search policies on DEVELOPMENT roots (no teacher, no labels, no P24 file): the same universal domain, K, fairness,
expansion / scoring budgets and selection family for every policy.

Policies (priority = search cost, lower first; a priority orders the search, it never removes a member):
  E, D, DIRECT, G   frozen 15-member ensembles under ONE common rule COMMON (and, secondary, each arm's own frozen P23 rule)
  GEOM              analytic remaining-blocker priority, no learning (P16 / P17 access maps, union model of the grasp screens):
                    h = min over (T pick mode at its cell, T place mode at the goal) of the number of bodies on the pair's kill cells (pairs
                    killed by a fixed body excluded; H_INF if none or the goal is occupied); x_pen = number of actions whose object pick or
                    destination place is analytically closed in its ideal predecessor scene; cost = h + x_pen + alpha m
  SHORTEST          m, then displacement C_d (shortest-first)
  UNIFORM           constant cost: canonical breadth-first order
COMMON = the dev-selected P23 DIRECT-GEO rule (gate 0.5, alpha 0.3, beta 0, gamma 0): chosen in P23 on development early-stop roots; it is the
only frozen rule with a length penalty, which a ~1e9-member K <= 4 domain needs. Disclosure: P25's exploratory recomputation on P24 labels
pointed the same way, so this choice is not independent of P24 knowledge; it is tested only on new data (P29 dev, P30 independent).
(P27 ships the non-learned priorities and the development-root roster; P28 adds the learned policies.)"""
from __future__ import annotations

import json
import time
from pathlib import Path

import bxy_fullspace as S

OUT = Path("runs/approach_b/bxy_p28_guided_v1")
FIG = Path("visualizations/approach_b/bxy_p28_guided_v1")
COMMON = {"noop_gate": 0.5, "eta": 0.0, "alpha": 0.3, "beta": 0.0, "gamma": 0.0}
LEARNED = {"E": "E:XY-UNC-SA-GEO-SYM", "D": "D:XYQ-GEO-SYM", "DIRECT": "A:DIRECT-GEO", "G": "G:XYQ-GEO-SYM-ORDINV"}
BASELINES = ("GEOM", "SHORTEST", "UNIFORM")
K, FAIR = 4, 4


# ------------------------------------------------------------------ non-learned priorities
H_INF = 10.0


def _closing(km, cells, skip=()) -> list:
    """Per declared mode, the set of bodies (ids) on its kill cells; None for a mode killed by a fixed body."""
    at = {c: o for o, c in cells.items() if o not in skip}
    return [frozenset(at[c] for c in ks if c in at) for ks in km["kill"].values()]


def geom_cost(rec, seq, alpha) -> tuple:
    import bxy_p16 as G
    import bxy_p17_data as DATA
    Mp, D = DATA._maps(), S.domain(rec)
    fixed, cells, pen = set(D["fixed"]), dict(D["cells0"]), 0
    for o, d in seq:
        others = [c for i, c in cells.items() if i != o]
        pen += (not G.open_after(Mp[f"pick:{cells[o]}"], others)) + (not G.open_after(Mp[f"place:{int(d)}"], others))
        cells[o] = int(d)
    t = D["target"]
    if D["goal"] in [c for i, c in cells.items() if i != t]:
        h = H_INF
    else:
        P_ = {b for b in _closing(Mp[f"pick:{cells[t]}"], cells, (t,)) if not b & fixed}
        Q_ = {b for b in _closing(Mp[f"place:{D['goal']}"], cells, (t,)) if not b & fixed}
        h = float(min((len(a | b) for a in P_ for b in Q_), default=H_INF))
    return h + pen + alpha * len(seq), h, pen


class Analytic:
    def __init__(self, rec, kind, alpha=COMMON["alpha"]):
        self.rec, self.kind, self.alpha, self.rows, self.cpu_s, self.calls = rec, kind, alpha, {}, 0.0, 0

    def __call__(self, seqs) -> list:
        c0, out = time.process_time(), []
        for s in seqs:
            if self.kind == "GEOM":
                c, h, pen = geom_cost(self.rec, s, self.alpha)
                self.rows[S.xsig(s)] = {"m": len(s), "h": h, "x_pen": pen}
            elif self.kind == "SHORTEST":
                c = len(s) + 1e-3 * _cd(self.rec, s)
            else:
                c = 0.0
            out.append(c)
        self.cpu_s += time.process_time() - c0
        self.calls += len(seqs)
        return out


def _cd(rec, seq) -> float:
    import bxy_p11 as P
    return P.cd_cells(rec, list(seq))


# ------------------------------------------------------------------ development roots (outcome-free choice: fixed sorted-hash order)
def dev_roots(n_k34=8, n_v21=4) -> list:
    import hashlib
    sel = []
    for corpus, base, n in (("K34", Path("runs/approach_b/bxy_p20_v1"), n_k34), ("V21", Path("runs/approach_b/bxy_p16_v1"), n_v21)):
        fs = sorted(base.glob("*/roots/*.json"), key=lambda f: hashlib.sha256(f"P28|{f.stem}".encode()).hexdigest())
        sel += [(corpus, f.stem, json.loads(f.read_text())) for f in fs[:n]]
    return sel


def catalogue_sigs(rec) -> set:
    """POST HOC audit only (never a search input): the historical catalogue signatures of this root."""
    return {S.xsig([(o, int(d)) for o, d in c["seq"]]) for c in rec.get("catalogue_v21", [])}


def _seq(sig) -> tuple:
    return () if sig == "empty" else tuple((a.split(">")[0], int(a.split(">")[1])) for a in sig.split("."))


