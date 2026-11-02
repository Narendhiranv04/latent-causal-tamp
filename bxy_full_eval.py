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
Every policy gets the same budget BUDGET (scored members / expansions), K = 4, fair = 4; GEOM / SHORTEST / UNIFORM cost no model CPU, which is
reported (an equal-scoring budget is not equal compute). Learned searches use the COMMON rule as priority and selector; each arm's own frozen
rule is reported as a selection-only variant over the same examined members. Diagnostics are label-free (no teacher, no stored labels).
    python3 bxy_full_eval.py run | figures"""
from __future__ import annotations

import json
import resource
import sys
import time
from pathlib import Path

import numpy as np

import bxy_fullsearch as Q
import bxy_fullspace as S

OUT = Path("runs/approach_b/bxy_p28_guided_v1")
FIG = Path("visualizations/approach_b/bxy_p28_guided_v1")
COMMON = {"noop_gate": 0.5, "eta": 0.0, "alpha": 0.3, "beta": 0.0, "gamma": 0.0}
LEARNED = {"E": "E:XY-UNC-SA-GEO-SYM", "D": "D:XYQ-GEO-SYM", "DIRECT": "A:DIRECT-GEO", "G": "G:XYQ-GEO-SYM-ORDINV"}
BASELINES = ("GEOM", "SHORTEST", "UNIFORM")
K, FAIR = 4, 4
BUDGET = {"scored": 3000, "expansions": 16}


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


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def cheb(rec, seq) -> list:
    c0 = S.domain(rec)["cells0"]
    return [max(abs(d % 8 - c0[o] % 8), abs(d // 8 - c0[o] // 8)) for o, d in seq]


def diagnostics(D, rec, sc) -> dict:
    """Label-free reliability diagnostics of one learned search: sound-F1 sanity (P(Y) on GOAL_BLOCKED endpoints), order sensitivity of
    P(X) across permutations sharing an endpoint, and the parking-distance profile of the scored members vs the training catalogues."""
    rows, blk, ok, groups = sc.rows, [], [], {}
    for k, r in rows.items():
        seq = _seq(k)
        if r.get("py") is not None and seq:
            (blk if S.goal_blocked(D, seq) else ok).append(r["py"])
        if r.get("px") is not None and len(seq) >= 2:
            groups.setdefault(S.ysig(D, seq), []).append(r["px"])
    dpx = [max(v) - min(v) for v in groups.values() if len(v) >= 2]
    far = [c >= 3 for k in rows for c in cheb(rec, _seq(k))]
    return {"py_goal_blocked_median": float(np.median(blk)) if blk else None, "py_goal_blocked_max": float(max(blk)) if blk else None,
            "py_other_median": float(np.median(ok)) if ok else None, "n_goal_blocked": len(blk),
            "perm_groups": len(dpx), "perm_dpx_median": float(np.median(dpx)) if dpx else None, "perm_dpx_max": float(max(dpx)) if dpx else None,
            "frac_actions_cheb_ge3": float(np.mean(far)) if far else None}


def anytime(st, sc, learned) -> list:
    """[scored count, best value so far] in scoring order: learned -> max predicted p over selectable non-no-op members; GEOM -> min h."""
    out, best = [], None
    for i, (k, n) in enumerate(st["nodes"].items()):
        if n["m"] and not n["blocked"]:
            v = sc.rows[k]["p"] if learned else sc.rows[k]["h"] if "h" in sc.rows.get(k, {}) else None
            if v is not None and (best is None or (v > best if learned else v < best)):
                best = v
        if (i + 1) % 100 == 0 or i + 1 == len(st["nodes"]):
            out.append([i + 1, best])
    return out


def spread(arm, nets, sv) -> dict:
    """Across-member standard deviation of p per candidate (ensemble disagreement; an out-of-distribution indicator, not a label)."""
    import bxy_p11 as P
    pr = [P.predict_all(n, sv)["cands"] for n in nets]
    return {c["sig"]: float(np.std([p[j]["p"] for p in pr])) for j, c in enumerate(sv["cands"])}


def run(budget=None, roots=None) -> dict:
    import torch
    import bxy_fullscore as SC
    import bxy_p24_confirm as C
    torch.set_num_threads(1)
    budget = budget or BUDGET
    OUT.mkdir(parents=True, exist_ok=True)
    inp, fz = SC.inputs(), C.frozen_models()
    nets = C.load_all(fz)
    res = {"version": "BXY_P28_EVAL_V1", "budget": budget, "K": K, "fair": FAIR, "common_rule": COMMON,
           "own_rules": {a: fz["arms"][LEARNED[a]]["rule"] for a in LEARNED}, "roots": {}}
    for corpus, k, rec in roots or dev_roots():
        D = S.domain(rec)
        row = {"corpus": corpus, "n_movable": len(D["movable"]), "F": S.free0(D), "domain_total": sum(S.count(D, K).values()), "policies": {}}
        for name in list(LEARNED) + list(BASELINES):
            arm = LEARNED.get(name)
            sc = SC.Scorer(k, rec, inp[k], arm, nets[arm], COMMON) if arm else Analytic(rec, name)
            w0 = time.time()
            st, r = Q.run(D, K, sc, budget, fair=FAIR)
            sel = r["selected"]
            p = {"selected": sel, "m": len(_seq(sel)) if sel else None, "status": r["status"], "coverage": r["coverage"],
                 "selected_row": sc.rows.get(sel), "model_cpu_s": round(sc.cpu_s, 2), "search_cpu_s": round(st["cpu_s"], 2), "scored_calls": sc.calls,
                 "wall_s": round(time.time() - w0, 2), "rss_mb": round(rss_mb(), 1), "in_catalogue": sel in catalogue_sigs(rec),
                 "top10": Q.ranked(st)[:10], "anytime": anytime(st, sc, bool(arm)), "selected_cheb": cheb(rec, _seq(sel)) if sel else None}
            if arm:                                                            # secondary: each arm's own frozen rule, re-selected among the
                own = fz["arms"][arm]["rule"]                                    # SAME examined members (selection-only variant)
                cand = [kk for kk in sc.rows if not S.goal_blocked(D, _seq(kk))]
                p["own_rule_selected"] = min(cand, key=lambda kk: (round(SC.cost(sc.rows[kk], own), 12), sc.rows[kk]["m"], kk))
                p["diagnostics"] = diagnostics(D, rec, sc)
            row["policies"][name] = p
        sels = sorted({p["selected"] for p in row["policies"].values() if p["selected"]})
        cat = sorted(s for s in catalogue_sigs(rec) if S.classify(D, _seq(s), K) is None and not S.goal_blocked(D, _seq(s)))
        seqs = [_seq(s) for s in sels + [c for c in cat if c not in sels]]
        sv = SC.view(k, rec, inp[k], seqs)
        row["cross"] = {a: {r_["sig"]: {f: r_.get(f) for f in ("p", "px", "py", "J_hat")} for r_ in C.ensemble(LEARNED[a], nets[LEARNED[a]], sv)["cands"]}
                        for a in LEARNED}
        row["spread"] = {a: spread(LEARNED[a], nets[LEARNED[a]], sv) for a in LEARNED}
        row["catalogue_in_K"] = cat
        res["roots"][k] = row
        print(k, {n: (p["selected"], p["model_cpu_s"]) for n, p in row["policies"].items()}, flush=True)
        (OUT / "GUIDED_SEARCH_P28.partial.json").write_text(json.dumps(res, sort_keys=True, default=str))
    (OUT / "GUIDED_SEARCH_P28.json").write_text(json.dumps(res, sort_keys=True, default=str))
    (OUT / "GUIDED_SEARCH_P28.partial.json").unlink()
    return {k: {n: p["selected"] for n, p in r["policies"].items()} for k, r in res["roots"].items()}


def _seq(sig) -> tuple:
    return () if sig == "empty" else tuple((a.split(">")[0], int(a.split(">")[1])) for a in sig.split("."))




if __name__ == "__main__":
    print(json.dumps(run() if sys.argv[1] == "run" else figures(), indent=1))
