"""Approach D G3 (approachD_G3_causal_repair_instructions_v1_4): D_CAUSAL_G3 — D constructs and expands a bounded causal repair frontier.

Roles (kept separate on purpose):
  learned D      frozen pairless Dp17, queried ONLY for the original target t0 and its original goal, at hypothetical occupancies and the
                 robot's exact (recorded) q: p_T(x) and blocker marginals m_i(x). Never a temporary target, never a certificate.
  geometry       non-learned: the common candidate universe (P17 movers x scene-only slots with a stored relocation motion), destination
                 proposals ranked by how many stored target-action sweeps a slot falls in (candidate-specific evidence, not a veto).
  provider       AD_PRECOMPILED: certifies one exact stored motion (and its stored connectors) in the current scene; the only source of a
                 realised successor; final success only when a stored ORIGINAL-T action certifies and the whole chain replays.
  search         verify-first beam over <= max_depth relocations with logged progressive widening of the mover frontier, under one
                 fixed budget (relocation certifications, expansions, D calls) shared by every policy.
Policies differ ONLY in which movers enter the frontier and how candidate placements are ranked:
  D_CAUSAL_G3      movers by D marginals; placements by counterfactual p_T(edited occupancy, q_end of that stored motion)
  GEOM_CAUSAL      movers by stored target-sweep relevance; placements by sweep conflict, then travel (no D)
  D_BLOCKER_ONLY   movers by D marginals; placements geometric (isolates the counterfactual re-query)
  D_CF_ONLY        movers geometric; placements by counterfactual D (isolates D's mover gating)
  UNIFORM          seeded mover shuffle; placements in slot / provider order (no guidance)
No IK, planner, connector synthesis or trajectory generation is reachable (runs under ad_runtime.forbid('raise'))."""
from __future__ import annotations

import collections
import json
import time
from pathlib import Path

import numpy as np

import ad_runtime as ar

VERSION = "D_CAUSAL_G3_V1"
POLICIES = ("D_CAUSAL_G3", "GEOM_CAUSAL", "D_BLOCKER_ONLY", "D_CF_ONLY", "UNIFORM")
G4_POLICIES = ("D_CAUSAL_G3", "D_CAUSAL_G4_SWEEP", "D_BLOCKER_ONLY", "GEOM_CAUSAL", "UNIFORM")   # G4 (opt-in): + stored-sweep demotion
CKEYS = {"top_movers", "widening", "dests_per_mover", "templates_per_pair", "universe_slots", "beam", "max_depth", "max_reloc_attempts",
         "max_expansions", "max_d_calls"}
OUT, FIG = Path("runs/approach_d/g3"), Path("visualizations/approach_d/g3")


def ccfg(path="approach_d.toml") -> dict:
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["causal_search"]
    if set(c) != CKEYS or c["widening"][0] != c["top_movers"]:
        raise ValueError(f"invalid [causal_search]: {sorted(set(c) ^ CKEYS)}")
    return c


class DOracle:
    """Frozen Dp17 for the ORIGINAL target only. predict(cells, q) -> p_T and blocker marginals over the eligible movers. Cached on the exact
    occupancy, q bytes, target, goal and model hash; every uncached call counts against the D budget."""

    def __init__(self, st, movers, cap):
        import config as cf
        import p17_d as pd
        self.st, self.movers, self.cap = st, list(movers), cap
        self.models = pd.models("Dp17")
        self.model_hash = cf.stable_hash([str(sorted(m.state_dict().keys())) for m in self.models])[:23]
        self.cache, self.calls, self.cpu = {}, 0, 0.0

    def predict(self, cells, q, target="t0"):
        import p15_retarget as pr
        if target != "t0":
            raise ValueError("G3 queries D for the original target t0 only")
        k = (tuple(sorted(cells.items())), np.asarray(q, float).tobytes(), target, self.st.goal_cell, self.model_hash)
        if k not in self.cache:
            if self.calls >= self.cap:
                raise BudgetOut("D_CALL_BUDGET")
            t0 = time.process_time()
            s = pr.retarget_scene(self.st.s0, cells, "t0", q)
            r = pr.d_predict(self.models, pr.build_record(self.st.cfg, s, "t0", self.st.goal_cell), "t0", self.movers)
            self.cache[k] = {"p": r["p_feasible"], "marg": dict(zip(r["pool"], r["marg"]))}
            self.calls += 1
            self.cpu += time.process_time() - t0
        return self.cache[k]


class BudgetOut(Exception):
    pass


class Geo:
    """Non-learned stored-sweep geometry for the current target pair: per stored target action, its core + entry-leg sweep cells."""

    def __init__(self, g, templates, st):
        self.st, self.g = st, g
        self.sweeps = {}
        for i, a in g.actions.items():
            t = templates.get(a["template"])
            if t:
                self.sweeps[i] = set(a["swept"]) | set(t["swept_by_phase"].get("pregrasp", []))
            elif "entry_swept" in a:                          # G4 witness core: its own stored entry leg (the connector before it)
                self.sweeps[i] = set(a["swept"]) | set(a["entry_swept"])

    def target_sweeps(self, cells):
        return [self.sweeps[i] for i in self.g.by_pair.get((cells["t0"], self.st.goal_cell), []) if i in self.sweeps]

    def relevance(self, cells, o):
        sw = self.target_sweeps(cells)
        return sum(cells[o] in s for s in sw) / max(1, len(sw))

    def conflict(self, cells, d):
        sw = self.target_sweeps(cells)
        return sum(d in s for s in sw) / max(1, len(sw))

    def t_options(self, cells, d, movers):
        """G4 stored-sweep compatibility of placing a mover at d: (stored T motions compatible now = sweep avoids every non-mover object,
        of those how many also avoid d). Evidence from actual stored sweeps for ranking only, never a proof of infeasibility."""
        fixed = {c for o, c in cells.items() if o != "t0" and o not in movers}
        ok = [s for s in self.target_sweeps(cells) if not s & fixed]
        return len(ok), sum(d not in s for s in ok)


def universe(st, slot_f, prov, cells, movers, width):
    """Common candidate universe at one state (identical for every policy): eligible movers x their first `width` scene-only slots that have
    at least one stored relocation motion for (current cell, slot). Slots without a stored motion are logged, not explored."""
    out, dropped = collections.OrderedDict(), []
    for o in movers:
        for d in slot_f(cells, o)[:width]:
            if prov.g.by_pair.get((cells[o], d)):
                out.setdefault(o, []).append(d)
            else:
                dropped.append([o, d, "NO_STORED_RELOCATION"])
    return out, dropped


def search(policy, prov, st, cells0, q0, movers, slot_f, geo, dor, cfg, seed=0) -> dict:
    """Verify-first causal beam search with logged widening; one shared budget per root. Returns SUCCESS/FAILURE plus a full trace."""
    A, budget = prov.g.actions, {"reloc": 0, "expand": 0}
    certified, trace = {}, []
    usesD_mover = policy in ("D_CAUSAL_G3", "D_BLOCKER_ONLY", "D_CAUSAL_G4_SWEEP")
    usesD_place = policy in ("D_CAUSAL_G3", "D_CF_ONLY", "D_CAUSAL_G4_SWEEP")
    rng = np.random.default_rng([seed, cells0["t0"], st.goal_cell])

    def mover_rank(cells, q, elig):
        if usesD_mover:
            m = dor.predict(cells, q)["marg"]
            return sorted(elig, key=lambda o: (-m.get(o, 0.0), elig.index(o)))
        if policy == "UNIFORM":
            return [elig[j] for j in rng.permutation(len(elig))]
        T = np.asarray(st.s0.lattice.center(cells["t0"]))
        return sorted(elig, key=lambda o: (-geo.relevance(cells, o), float(np.linalg.norm(np.asarray(st.s0.lattice.center(cells[o])) - T)), o))

    def candidates(x, k):
        cells, q = x["cells"], x["q"]
        U, dropped = universe(st, slot_f, prov, cells, [o for o in movers if o not in x["moved"]], cfg["universe_slots"])
        elig = list(U)
        ranked = mover_rank(cells, q, elig) if elig else []
        frontier = ranked[:k] if k else ranked
        p_before = dor.predict(cells, q)["p"] if (usesD_mover or usesD_place) and elig else None
        per = []
        for o in frontier:
            dests = U[o] if policy == "UNIFORM" else sorted(U[o], key=lambda d: (geo.conflict(cells, d), U[o].index(d)))
            cs = []
            for d in dests[:cfg["dests_per_mover"]]:
                acts = prov.order(prov, cells, o, d, list(prov.g.by_pair[(cells[o], d)]))[:cfg["templates_per_pair"]]
                for i in acts:
                    c = {"object": o, "dest": d, "action": i, "q_end": A[i]["to"], "travel": A[i]["travel_J"], "conflict": geo.conflict(cells, d),
                         "mover_score": (dor.predict(cells, q)["marg"].get(o) if usesD_mover else geo.relevance(cells, o)) if policy != "UNIFORM" else None}
                    if usesD_place:
                        r = dor.predict({**cells, o: d}, prov.g.q[A[i]["to"]])          # SAME T, edited occupancy, that motion's q_end
                        c["p_after"], c["marg_after"] = r["p"], r["marg"]
                    cs.append(c)
            if usesD_place:
                cs.sort(key=lambda c: (-c["p_after"], c["travel"], c["action"]))
            elif policy != "UNIFORM":
                cs.sort(key=lambda c: (c["conflict"], c["travel"], c["action"]))
            if policy == "D_CAUSAL_G4_SWEEP":                 # demote (never drop) placements inside every compatible stored T sweep
                for c in cs:
                    c["t_options"] = geo.t_options(cells, c["dest"], movers)
                    c["demoted"] = c["t_options"][0] > 0 and c["t_options"][1] == 0
                cs = [c for c in cs if not c["demoted"]] + [c for c in cs if c["demoted"]]
            per.append(cs)
        out = []
        for j in range(max((len(x) for x in per), default=0)):                         # interleave movers: diversity across objects
            out += [cs[j] for cs in per if j < len(cs)]
        return out, {"eligible": elig, "frontier": frontier, "ranked": ranked, "dropped": dropped, "p_before": p_before}

    root = {"cells": dict(cells0), "q": np.asarray(q0, float), "moved": [], "chain": []}
    result = {"status": "FAILURE", "reason": None, "stage": None, "depth": None}
    n_elig = len(universe(st, slot_f, prov, cells0, movers, cfg["universe_slots"])[0])
    prev = None
    try:
        for stage, k in enumerate(cfg["widening"]):
            eff = min(k or n_elig, n_elig)
            if eff == prev:                                   # widening would not enlarge the root frontier: stage skipped, logged
                trace.append({"stage": stage, "k": k, "event": "widening_skipped", "eligible": n_elig})
                continue
            prev = eff
            frontier = [root]
            for depth in range(cfg["max_depth"] + 1):
                nxt = []
                for x in frontier:
                    r = prov.goal(x["cells"], x["q"])
                    trace.append({"stage": stage, "k": k, "depth": depth, "event": "verify_T", "moved": list(x["moved"]), "status": r["status"],
                                  "reason": r["reason"]})
                    if r["status"] == "SUCCESS":
                        steps = [(kk, i, c["object"] if kk == "action" else None) for c in x["chain"] + [r] for kk, i in c["steps"]]
                        rep = prov.verify_plan(cells0, q0, steps)
                        result.update(status=rep["status"], reason=rep["reason"], stage=stage, depth=depth, moves=[[c["object"], c["dest"]] for c in x["chain"]],
                                      replay=rep, steps=steps)
                        raise StopIteration
                if depth == cfg["max_depth"]:
                    break
                cand_all = []
                for x in frontier:
                    if budget["expand"] >= cfg["max_expansions"]:
                        raise BudgetOut("EXPANSION_BUDGET")
                    budget["expand"] += 1
                    cs, info = candidates(x, k)
                    trace.append({"stage": stage, "k": k, "depth": depth, "event": "frontier", "moved": list(x["moved"]), **info,
                                  "candidates": [{kk: c[kk] for kk in ("object", "dest", "action", "q_end", "travel", "conflict", "mover_score")}
                                                 | ({"p_after": c["p_after"]} if "p_after" in c else {})
                                                 | ({"demoted": c["demoted"], "t_options": c["t_options"]} if "demoted" in c else {}) for c in cs]})
                    cand_all += [(x, c) for c in cs]
                for x, c in cand_all:
                    if len(nxt) >= cfg["beam"]:
                        break
                    key = (tuple(sorted(x["cells"].items())), np.asarray(x["q"]).tobytes(), c["action"])
                    if key not in certified:
                        if budget["reloc"] >= cfg["max_reloc_attempts"]:
                            raise BudgetOut("MOTION_CHECK_BUDGET")
                        budget["reloc"] += 1
                        certified[key] = prov.edges(x["cells"], x["q"], c["object"], c["dest"], only=c["action"])
                    e = certified[key]
                    trace.append({"stage": stage, "depth": depth, "event": "certify", "moved": list(x["moved"]), "object": c["object"], "dest": c["dest"],
                                  "action": c["action"], "status": e["status"], "reason": e["reason"], "reason_counts": e.get("reason_counts")})
                    if e["status"] == "SUCCESS":
                        y = {"cells": e["cells"], "q": prov.g.q[e["q_end"]], "moved": x["moved"] + [c["object"]], "chain": x["chain"] + [e]}
                        if all(not (y["cells"] == z["cells"] and np.array_equal(y["q"], z["q"])) for z in nxt):
                            nxt.append(y)
                frontier = nxt
                if not frontier:
                    break
        result["reason"] = "NO_VERIFIED_REPAIR"
    except StopIteration:
        pass
    except BudgetOut as b:
        result["reason"] = str(b)
    result.update(budget=dict(budget), d_calls=dor.calls if dor else 0, d_cpu=dor.cpu if dor else 0.0, provider=prov.stats()["counts"], trace=trace)
    return result


# ------------------------------------------------------------------ View B: end-to-end on the frozen catalog (12 DEV roots, C3)
def _root_job(item):
    import ad_compile as ac
    import ad_g2b as g2
    import ad_local as L
    import ad_provider as pv
    import p17_domain as dm
    root, cat, policies = item
    cfg = ccfg()
    st = L.Stub(root)
    cells0 = {o.id: o.cell for o in st.s0.objects}
    mv, _ = dm.movers(st.task, cells0)
    f = dm.slot_fn(st, None, width=cfg["universe_slots"], origin=cells0)
    slot_f = lambda cells, o: f(cells, o)[:cfg["universe_slots"]]  # noqa: E731
    g = pv.Graph(L.OUT / "catalog", f"GRAPH_{cat}")
    ri, member = g2._ri()
    excl = g2._excl(root)
    T = L._catalog_all()
    geo = Geo(g, T, st)
    out = {}
    with ar.forbid("raise") as calls:
        for pol in policies:
            prov = pv.Precompiled(st.cfg, st.robot, st.s0, st.goal_cell, g, g2.Ranker(ri, member, excl, **g2.POLICIES["EXACT+REL_6x1+CATALOG"]),
                                  6, 2, "OFF", f"G3/{pol}")
            dor = DOracle(st, mv, cfg["max_d_calls"]) if pol != "GEOM_CAUSAL" and pol != "UNIFORM" else None
            c0 = time.process_time()
            r = search(pol, prov, st, cells0, st.s0.robot.q_rad, mv, slot_f, geo, dor, cfg)
            out[pol] = {**r, "cpu_s": time.process_time() - c0}
    return root, cat, out, sum(calls.values())


def view_b(workers=12, cat="C3", policies=POLICIES) -> dict:
    import multiprocessing as mp
    import ad_local as L
    import config as cf
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_root_job, [(k, cat, policies) for k in L.dev_roots()], chunksize=1)
    rows = {k: o for k, _, o, _ in res}
    explored = {k: {p: sorted({(t["object"], t["dest"]) for t in o[p]["trace"] if t["event"] == "certify"}) for p in policies} for k, o in rows.items()}
    summ = {p: {"success": sum(rows[k][p]["status"] == "SUCCESS" for k in rows), "n": len(rows),
                "reasons": dict(collections.Counter(rows[k][p]["reason"] for k in rows if rows[k][p]["status"] != "SUCCESS")),
                "reloc_certifications": sum(rows[k][p]["budget"]["reloc"] for k in rows), "expansions": sum(rows[k][p]["budget"]["expand"] for k in rows),
                "d_calls": sum(rows[k][p]["d_calls"] for k in rows),
                "relocations_accepted": sum(sum(t["event"] == "certify" and t["status"] == "SUCCESS" for t in rows[k][p]["trace"]) for k in rows),
                "success_stage": dict(collections.Counter(rows[k][p]["stage"] for k in rows if rows[k][p]["status"] == "SUCCESS")),
                "explored_pairs_jaccard_vs_geom": float(np.mean([_jac(explored[k][p], explored[k]["GEOM_CAUSAL"]) for k in rows]))
                if "GEOM_CAUSAL" in policies else None} for p in policies}
    out = {"version": VERSION, "catalog": cat, "config": ccfg(), "forbidden_calls": sum(x[3] for x in res), "summary": summ, "explored": explored,
           "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / f"VIEW_B_{cat}.json", out)
    return {k: v for k, v in out.items() if k not in ("rows", "explored")}


def _jac(a, b):
    a, b = set(map(tuple, a)), set(map(tuple, b))
    return len(a & b) / len(a | b) if a | b else 1.0


# ------------------------------------------------------------------ View A: causal-selection sanity on saved, legitimately labelled edits
def _stub(plan, root):
    import ad_local as L
    st = L.Stub.__new__(L.Stub)
    import ad_compile as ac
    import p6_scenes as p6
    from scene import scene_from_dict
    P = plan[root]
    st.cfg, st.robot, _ = ac.setup()
    st.s0, st.goal_cell, st.scr = scene_from_dict(P["scene"]), P["goal_cell"], p6.Screens(st.cfg, st.robot)
    st.task = {"scene": P["scene"], "goal_cell": P["goal_cell"], "fixed_ids": [o.id for o in st.s0.objects if o.cell in set(P.get("fixed", []))],
               "target": "t0", "key": root}
    return st


def _auc(pos, neg):
    if not pos or not neg:
        return None
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def view_a(split) -> dict:
    """P16 labels of `split` (dev: inside D's training data; calib: held out from D training). All comparisons use the original robot q, the
    protocol the labels were made with. (1) mover frontier: does a policy's top-2 contain an object of an inclusion-minimal clearing set
    (decided edit lattice, original not VERIFIED)? (2) counterfactual edits: AUROC of each scorer's predicted 'T feasible after this edit' vs
    the decided edit label. Scorers: D (p_T at the edited occupancy), geometry (minus the number of P17 geometry-flagged objects still in
    place), uniform (fixed-seed random). UNKNOWN labels are excluded, never mapped to 0."""
    import glob
    import p17_d as pd
    import p17_domain as dm
    plan = json.loads(Path(f"runs/p16/data/{split}/plan.json").read_text())["roots"]
    lab = {}
    for f in sorted(glob.glob(f"runs/p16/data/{split}/labels_*.json")):
        lab.update(json.loads(Path(f).read_text()))
    rng = np.random.default_rng(0)
    dec = lambda s: {"VERIFIED": 1, "CERTIFIED_INFEASIBLE": 0, "STATIC_INVALID": 0}.get(s)  # noqa: E731
    front = {p: {"hit": 0, "n": 0} for p in ("D", "geometry", "uniform")}
    edits = {p: {"pos": [], "neg": []} for p in ("D", "geometry", "uniform")}
    single = {p: {"top1_verified": 0, "n": 0} for p in ("D", "geometry", "uniform")}
    rows = []
    with ar.forbid("raise"):
        for k in sorted(lab):
            L = lab[k]
            st = _stub(plan, k)
            cells0, q0 = {o.id: o.cell for o in st.s0.objects}, np.asarray(st.s0.robot.q_rad, float)
            mv, _ = dm.movers(st.task, cells0)
            dor = DOracle(st, mv, 10 ** 6)
            geo = pd.Guide("geometry-norec", st.task, st, mv)
            park = L["catalogue"]["parking"]
            d0 = dor.predict(cells0, q0)
            g0 = geo._geo(cells0, q0, "t0", mv)
            T = np.asarray(st.s0.lattice.center(cells0["t0"]))
            rank = {"D": sorted(mv, key=lambda o: (-d0["marg"].get(o, 0), mv.index(o))),
                    "geometry": sorted(mv, key=lambda o: (-g0.get(o, 0), float(np.linalg.norm(np.asarray(st.s0.lattice.center(cells0[o])) - T)), o)),
                    "uniform": [mv[j] for j in rng.permutation(len(mv))]}
            ed = {tuple(e.split("+")): dec(v["status"]) for e, v in L["edits"].items()}
            ok = [set(e) for e, y in ed.items() if y == 1]
            minimal = [s for s in ok if not any(t < s for t in ok)]
            union = set().union(*minimal) if minimal else set()
            row = {"root": k, "original": L["original"]["status"], "minimal_clearing_sets": [sorted(s) for s in minimal], "p_T": d0["p"],
                   "marg": d0["marg"], "geo": g0}
            if dec(L["original"]["status"]) == 0 and union and all(y is not None for y in ed.values()):
                for p in front:
                    front[p]["n"] += 1
                    front[p]["hit"] += bool(set(rank[p][:2]) & union)
                    row[f"top2_{p}"] = rank[p][:2]
            sc = {}
            for e, y in ed.items():
                if y is None or any(o not in park for o in e):
                    continue
                cells = {**cells0, **{o: park[o] for o in e}}
                sc[e] = {"D": dor.predict(cells, q0)["p"], "geometry": -sum(geo._geo(cells, q0, "t0", [o for o in mv if o not in e]).values()),
                         "uniform": float(rng.random()), "y": y}
                for p in edits:
                    edits[p]["pos" if y else "neg"].append(sc[e][p])
            singles = {e: v for e, v in sc.items() if len(e) == 1}
            if dec(L["original"]["status"]) == 0 and any(v["y"] for v in singles.values()):
                for p in single:
                    single[p]["n"] += 1
                    single[p]["top1_verified"] += max(singles.values(), key=lambda v: v[p])["y"]
            row["edits"] = {"+".join(e): v for e, v in sc.items()}
            rows.append(row)
    out = {"split": split, "in_D_training": split in ("train", "dev"), "roots": len(rows),
           "mover_frontier_top2_hits_minimal_union": front,
           "edit_auroc": {p: _auc(v["pos"], v["neg"]) for p, v in edits.items()}, "edit_counts": {"verified": len(edits["D"]["pos"]),
                                                                                                   "certified_infeasible": len(edits["D"]["neg"])},
           "single_edit_top1_verified": single, "rows": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    import config as cf
    cf.write_json(OUT / f"VIEW_A_{split}.json", out)
    return {k: v for k, v in out.items() if k != "rows"}
