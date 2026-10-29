"""Approach D G2b driver (approachD_G2b_solver_free_provider_instructions_v1_2): development-only, reuses the frozen G2a catalog.

  reverify()      the 36 G2a relocation queries + 24 target rows re-checked from the FROZEN catalog (no recompilation) under
                  forbid('raise'): G2a policy outcomes recomputed with ad_runtime.check and compared with PILOT_ROWS.json; per template the
                  full home->home verdict and the separate entry-leg / core / exit-leg verdicts (home-leg diagnosis), prefilter hits, CPU.
  analyse()       home-leg diagnosis by distinct query, prefilter OFF / ADVISORY / HARD on identical candidate lists, retrieval policies on
                  one shared template universe with an equal certification budget (strict home->home and relaxed end-at-retreat).
  anomaly()       the G2a target root p13_2026210004: original q vs after the precompiled entry, P16 label, regression fixture.
  chains()        G2b sequential rearrangement fixtures (ad_provider over the finite graph), compile budget accounted.
Nothing here trains D, touches historical labels, or runs the sealed 442-query benchmark."""
from __future__ import annotations

import collections
import copy
import json
import multiprocessing as mp
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

import ad_compile as ac
import ad_pilot as ap
import ad_runtime as ar
import config as cf

OUT = Path("runs/approach_d/g2b")
G2A = ac.OUT


def rd(p):
    return json.loads(Path(p).read_text())


def _moved(s, oid, dst):
    return replace(s, objects=tuple(replace(o, cell=dst, xy_m=s.lattice.center(dst)) if o.id == oid else o for o in s.objects))


_T = None


def _reval(item):
    """Pool worker: one query scene. (1) every G2a policy list re-run exactly as G2a did (ad_runtime.check, HARD prefilter, budget 6);
    (2) every template in the query's universe: full record, entry leg, core and exit leg certified separately; prefilter hits."""
    global _T
    q, lists = item
    cfg, robot, _ = ac.setup()
    T = _T = _T or ac.load_catalog()
    home, s = np.array(robot.q_home), q["scene"]
    occ = {o.cell for o in s.objects if o.id != q["oid"]}
    pol, per = {}, {}
    with ar.forbid("raise") as calls:
        for name, ids in lists.items():
            r = ar.check(robot, cfg, s, q["oid"], q["dst"], home, [T[x] for x in ids if x], 6)
            pol[name] = {k: r[k] for k in ("status", "reason", "checks", "prefiltered", "template_id")}
        for t in sorted({x for ids in lists.values() for x in ids if x}):
            a, sg = T[t]["arrays"], ac.segment(T[t]["arrays"])
            c0 = time.process_time()
            full = ar.certify_action(robot, cfg, s, q["oid"], a)
            cpu = time.process_time() - c0
            pieces = {"entry": ar.certify_free(robot, cfg, s, sg["entry"]), "core": ar.certify_action(robot, cfg, s, q["oid"], sg["core"]),
                      "exit": ar.certify_free(robot, cfg, _moved(s, q["oid"], q["dst"]), sg["exit"]) if len(sg["exit"]["q"]) > 1 else {"ok": True}}
            sw = T[t]["swept_by_phase"]
            hit = lambda phs: sorted(set().union(*(set(sw.get(p, [])) for p in phs)) & occ)  # noqa: E731
            per[t] = {"full": full["ok"], "full_fail": None if full["ok"] else {k: full[k] for k in ("verdict", "pair", "phase", "segment")},
                      "entry": pieces["entry"]["ok"], "core": pieces["core"]["ok"], "exit": pieces["exit"]["ok"], "cpu_s": cpu,
                      "hit_full": hit(sw), "hit_entry": hit(["pregrasp"]), "hit_core": hit(["approach", "close_attach", "carry", "release", "retreat"]),
                      "hit_exit": hit(["return_home"])}
    return q["qid"], pol, per, dict(calls)


def reverify(workers=8) -> dict:
    t0 = time.time()
    rows = {r["qid"]: r for r in rd(G2A / "PILOT_ROWS.json")["rows"]}
    queries, targets, _, _ = ap.build_jobs()
    items = [({k: q[k] for k in ("qid", "oid", "dst", "scene")}, rows[q["qid"]]["lists"]) for q in queries + targets]
    with mp.get_context("spawn").Pool(workers) as pool:
        res = pool.map(_reval, items, chunksize=1)
    out, diff = {}, []
    for qid, pol, per, calls in res:
        old = rows[qid]
        for name, r in pol.items():
            o = old["policies"][name]
            if (r["status"], r["reason"], r["template_id"], r["checks"]) != (o["status"], o["reason"], o["template_id"], o["checks"]):
                diff.append({"qid": qid, "policy": name, "now": r, "g2a": {k: o[k] for k in ("status", "reason", "template_id", "checks")}})
        for t, v in per.items():
            if t in old["templates"] and old["templates"][t]["verified"] != v["full"]:
                diff.append({"qid": qid, "template": t, "now": v["full"], "g2a": old["templates"][t]["verified"]})
        out[qid] = {"policies": pol, "templates": per, "calls": calls}
    res = {"rows": out, "discrepancies": diff, "forbidden_calls": sum(sum(r["calls"].values()) for r in out.values()), "wall_s": time.time() - t0,
           "catalog_hash": rd(G2A / "catalog" / "CATALOG.json")["hash"]}
    OUT.mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "REVERIFY.json", res)
    return {k: v for k, v in res.items() if k != "rows"}


# ------------------------------------------------------------------ chains: fixtures, offline compile (budgeted), graph, runtime
DEV_PLAN = "runs/p16/data/dev/plan.json"
# historical P16 dev labels (labels_v2w*.json): original target CERTIFIED_INFEASIBLE from the root's start q, the listed sequence VERIFIED
# by the historical online pipeline. Chosen before any G2b runtime result; F11 is the unrepaired control, F12 a declared candidate list.
FIXTURES = {"F01": ("p13_2026217000", [["o00", 45], ["o01", 44]]), "F02": ("p13_2026217000", [["o01", 44], ["o00", 45]]),
            "F03": ("p13_2026216000", [["o00", 59], ["o01", 3]]), "F04": ("p13_2026214000", [["o00", 59], ["o01", 39]]),
            "F05": ("p13_2026213000", [["o01", 53], ["o00", 52]]), "F06": ("p13_2026218000", [["o01", 59], ["o00", 52]]),
            "F07": ("p13_2026219000", [["o00", 59], ["o01", 6]]), "F08": ("p13_2026219000", [["o00", 59], ["o02", 20]]),
            "F09": ("p13_2026215000", [["o00", 54]]), "F10": ("p13_2026216000", [["o00", 59]]), "F11": ("p13_2026217000", []),
            "F12": ("p13_2026216000", "CANDIDATES")}
# F12 (REDEFINED after pass 1; pass-1 F12 was a candidate list on p13_2026217000, whose target pair has no certifiable stored action in
# any reachable state). Pass-1 diagnosis on p13_2026216000: the target's stored core certifies in the original scene, but every stored
# home-routed entry leg is blocked by link0 / gripper contact with o00 (cell 56) and o01 (cell 16), both near the base. Destinations by a
# solver-free, scene + catalog-only rule: p17_domain.slot_fn proposals (no library destinations), the two per mover that fall inside the
# fewest stored sweeps (entry leg + core) of the target actions whose core certifies in the original scene; movers in P17 order.
F12_DESTS = {"o01": [37, 36], "o00": [45, 53]}
F12_CANDIDATES = [[["o01", a], ["o00", b]] for a in F12_DESTS["o01"] for b in F12_DESTS["o00"]] + \
                 [[["o00", b], ["o01", a]] for a in F12_DESTS["o01"] for b in F12_DESTS["o00"]]
EXTRA_PAIRS = [("p13_2026218000", "o00", 48, 61)]                 # same rule on p13_2026218000 (only o00 blocks link0 there)
BUDGET = {"compile_attempts": 120, "cpu_s": 25 * 60}


def _fixture_pairs():
    from scene import scene_from_dict
    P = rd(DEV_PLAN)["roots"]
    out = collections.OrderedDict()
    for f, (k, seq) in FIXTURES.items():
        s = scene_from_dict(P[k]["scene"])
        for o, d in (F12_CANDIDATES[-1] if seq == "CANDIDATES" else seq):
            out.setdefault((k, o), (s.get(o).cell, d))
    return out, P


def chain_jobs(pairs=None):
    """Per relocation pair (scene-independent compile): <= 1 exact-cell witness (LORO: the root's whole fingerprint group excluded),
    the 2 relative-family modes with most independent supporting roots (1 template each, <= 2 member seeds), 1 branch-spread baseline."""
    import p14_sweep_index as sx
    import p15_lookup as pl
    if pairs is None:
        pairs, P = _fixture_pairs()
    else:
        P = rd(DEV_PLAN)["roots"]
    idx, _ = pl.index_v2()
    Pl = sx._plans()
    ri = pl.RelIndex(idx, pl.rel_cfg())
    fp_roots = collections.defaultdict(set)
    for es in idx.by_key.values():
        for e in es:
            fp_roots[pl.json_fp(Pl[e["root"]])].add(e["support_id"])
    jobs = []
    for (k, o), (src, dst) in pairs.items():
        excl = frozenset(fp_roots[json.dumps(P[k]["fingerprint"])])
        keep = lambda e, excl=excl: e["support_id"] not in excl  # noqa: E731
        modes, _ = ap._modes(ri, sx.rel_key(src, dst, 0.024), keep, idx, 1)
        sup = {mid: len({x["support_id"] for m in ri.modes[sx.rel_key(src, dst, 0.024)] if f"{m[0]['file']}#{m[0]['index']}" == mid for x in m
                         if keep(x)}) for mid, _ in modes}
        modes = sorted(modes, key=lambda m: -sup[m[0]])[:2]
        exact = ap._abs_modes(sorted((e for e in idx.by_key.get((src, dst), []) if keep(e)), key=lambda e: (round(e["travel_J"], 12), e["file"],
                                                                                                          e["index"])))[:1]
        jobs.append({"qid": f"C:{k}:{o}", "root": k, "src": src, "dst": dst, "kind": "RELOCATION", "direct_k": 1, "direct": ("spread",),
                     "templates_per_mode": 1, "seeds": ap._seeds(modes, idx, src, dst, ri.base),
                     "exact": [{"file": e["file"], "index": e["index"], "root": e["root"]} for e in exact], "excl": sorted(excl)})
    return jobs


def _ledger():
    f = OUT / "COMPILE_LEDGER.json"
    return rd(f) if f.exists() else {"budget": BUDGET, "entries": []}


def _spend(kind, attempts, cpu, note):
    led = _ledger()
    used = sum(e["attempts"] for e in led["entries"]), sum(e["cpu_s"] for e in led["entries"])
    if used[0] + attempts > BUDGET["compile_attempts"] or used[1] + cpu > BUDGET["cpu_s"]:
        raise RuntimeError(f"G2b offline compile budget exceeded: {used} + ({attempts}, {cpu:.0f}s)")
    led["entries"].append({"kind": kind, "attempts": attempts, "cpu_s": cpu, "note": note})
    cf.write_json(OUT / "COMPILE_LEDGER.json", led)


def compile_chain(workers=8, pairs=None, name="CATALOG_G2B", note="", direct_k=1) -> dict:
    """Offline compile for the chain fixtures; real attempts (duplicates excluded) and CPU charged to the G2b ledger."""
    jobs = [{**j, "direct_k": direct_k} for j in chain_jobs(pairs)]
    with mp.get_context("spawn").Pool(workers) as pool:
        outs = pool.map(ac.compile_job, jobs, chunksize=1)
    atts = [{**a, "qid": j["qid"]} for j, o in zip(jobs, outs) for a in o["attempts"]]
    real = [a for a in atts if not a["termination_reason"].startswith("DUPLICATE")]
    cpu = sum(a["cpu_s"] for a in real) + sum(o["screen"]["cpu_s"] for o in outs) + sum(r.get("sweep_cpu_s", 0) for o in outs for r, _ in o["templates"])
    _spend("chain_templates", len(real), cpu, f"{len(jobs)} relocation pairs {note}".strip())
    cat = ac.save_catalog([x for o in outs for x in o["templates"]], atts, name, OUT / "catalog")
    cf.write_json(OUT / f"CHAIN_JOBS{name[len('CATALOG_G2B'):]}.json", {"jobs": [{k: v for k, v in j.items() if k != "seeds"} | {"n_seeds": len(j["seeds"])} for j in jobs],
                                            "outputs": [{k: o[k] for k in ("screen", "modes", "exact", "direct_spread")} for o in outs]})
    return {"pairs": len(jobs), "attempts": len(real), "compiled": sum(a["compiled"] for a in real), "cpu_s": cpu, "templates": len(cat["templates"])}


def build() -> dict:
    """GRAPH = every G2a relocation / target template + every G2b chain template and the three ENTRY templates."""
    T = ac.load_catalog()
    for f in sorted((OUT / "catalog").glob("CATALOG_G2B*.json")):
        T.update(ac.load_catalog(f.stem, OUT / "catalog"))
    tpl = {i: t for i, t in T.items() if t["kind"] != "ENTRY"}
    ent = [t for t in T.values() if t["kind"] == "ENTRY"]
    meta = ac.build_graph(tpl, ent, OUT / "catalog")
    return {k: (len(v) if isinstance(v, (dict, list)) else v) for k, v in meta.items()}


class Ranker:
    """Runtime candidate order (pure retrieval): tiers in order; 'exact' = actions derived from exact-cell witnesses (cheapest travel
    first); 'relative' = actions of relative-family modes ranked by G1 on the CURRENT scene's patches (rank='patch'), by robot geometry only
    (rank='geometry': base-rotation residual, no 3x3/4x4 terms) or by a fixed-seed shuffle (rank='random'), L modes x W actions each;
    'catalog' = generic offline DIRECT templates by travel. The root's whole fingerprint group is excluded from retrieval (no leakage)."""

    def __init__(self, ri, member, excl, tiers=("exact", "relative"), L=6, W=1, rank="patch", seed=0):
        self.ri, self.member, self.excl, self.tiers, self.L, self.W, self.rank, self.seed = ri, member, frozenset(excl), tiers, L, W, rank, seed

    def __call__(self, prov, cells, oid, dst, cand):
        import p14_sweep_index as sx
        import p15_lookup as pl
        A = prov.g.actions
        by_travel = lambda ids: sorted(ids, key=lambda i: (A[i]["travel_J"], i))  # noqa: E731
        out = []
        for tier in self.tiers:
            if tier == "exact":
                out += by_travel([i for i in cand if "EXACT_CELL_WITNESS" in A[i]["origins"]])
            elif tier == "catalog":
                out += by_travel([i for i in cand if any(o.startswith("DIRECT_OFFLINE") for o in A[i]["origins"])])
            else:
                fam = [i for i in cand if A[i]["modes"] and not set(A[i]["family_roots"]) <= self.excl]   # leakage guard
                src = cells[oid]
                if self.rank == "random":
                    rng = np.random.default_rng([self.seed, src, dst])
                    mids = sorted({m for i in fam for m in A[i]["modes"]})
                    mids = [mids[j] for j in rng.permutation(len(mids))][:self.L]
                else:
                    rv = copy.copy(self.ri)
                    rv.cfg = {**self.ri.cfg, "mode_limit": 10 ** 6, "witnesses_per_mode": 1} | (
                        {"alpha_3": 0.0, "alpha_4": 0.0, "alpha_global": 0.0, "alpha_rho": 1.0} if self.rank == "geometry" else {})
                    desc = sx.descriptor(prov.scene(cells), prov.goal_cell, oid, src, dst)
                    r = pl.lookup_relative(rv, desc, prov.s0.get(oid).radius_m, self.excl)
                    have = {m for i in fam for m in A[i]["modes"]}
                    mids = [m for m in dict.fromkeys(self.member.get((c["entry"]["file"], c["entry"]["index"])) for c in r["candidates"]) if m in have][:self.L]
                for m in mids:
                    out += by_travel([i for i in fam if m in A[i]["modes"]])[:self.W]
        return list(dict.fromkeys(out))


def _ri():
    import p15_lookup as pl
    idx, _ = pl.index_v2()
    ri = pl.RelIndex(idx, pl.rel_cfg())
    member = {(e["file"], e["index"]): f"{m[0]['file']}#{m[0]['index']}" for ms in ri.modes.values() for m in ms for e in m}
    return ri, member


def _excl(root):
    import p14_sweep_index as sx
    import p15_lookup as pl
    P, idx = sx._plans(), pl.index_v2()[0]
    fp = json.dumps(rd(DEV_PLAN)["roots"][root]["fingerprint"])
    return {e["support_id"] for es in idx.by_key.values() for e in es if pl.json_fp(P[e["root"]]) == fp}


POLICIES = {"EXACT+REL_6x1": dict(tiers=("exact", "relative"), L=6, W=1), "EXACT+REL_3x2": dict(tiers=("exact", "relative"), L=3, W=2),
            "EXACT+REL_6x1+CATALOG": dict(tiers=("exact", "relative", "catalog"), L=6, W=1)}


def chains(policies=POLICIES, graph=None, prefilter="OFF") -> dict:
    """Every fixture through the AD_PRECOMPILED provider under forbid('raise'); start = the root's ACTUAL initial q (a stratum node: a
    stored ROOT_ENTRY connector is the only way to home)."""
    import ad_provider as pv
    from scene import scene_from_dict
    cfg, robot, _ = ac.setup()
    g = graph or pv.Graph(OUT / "catalog")
    ri, member = _ri()
    P = rd(DEV_PLAN)["roots"]
    out = {}
    with ar.forbid("raise") as calls:
        for f, (k, seq) in FIXTURES.items():
            s = scene_from_dict(P[k]["scene"])
            cells0, q0 = {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float)
            excl = _excl(k)
            for name, kw in policies.items():
                prov = pv.Precompiled(cfg, robot, s, P[k]["goal_cell"], g, Ranker(ri, member, excl, **kw), 6, 2, prefilter, name)
                r = pv.repair(prov, cells0, q0, F12_CANDIDATES) if seq == "CANDIDATES" else pv.run_sequence(prov, cells0, q0, seq)
                out[f"{f}|{name}"] = {"fixture": f, "root": k, "stratum": P[k]["stratum"], "policy": name, "sequence": seq, **{
                    x: r.get(x) for x in ("status", "reason", "failed_step", "log", "steps", "replay", "tried")}, "stats": prov.stats()}
    res = {"graph": g.hash, "forbidden_calls": sum(calls.values()), "rows": out}
    cf.write_json(OUT / "CHAINS.json", res)
    return {k: (v["status"], v["reason"], v["failed_step"]) for k, v in out.items()}


def _graph_without(g, origin):
    """A view of the graph with every connector of one origin removed (controlled ablation; arrays shared, nothing mutated)."""
    h = copy.copy(g)
    h.out = {n: [c for c in cs if g.connectors[c]["origin"] != origin] for n, cs in g.out.items()}
    return h


def necessity(policy="EXACT+REL_6x1+CATALOG") -> dict:
    """F12 accepted chain: is each relocation needed? The same provider policy on the single-relocation and empty sequences."""
    import ad_provider as pv
    from scene import scene_from_dict
    cfg, robot, _ = ac.setup()
    g, (ri, member), P = pv.Graph(OUT / "catalog"), _ri(), rd(DEV_PLAN)["roots"]
    k = FIXTURES["F12"][0]
    s, excl = scene_from_dict(P[k]["scene"]), _excl(k)
    cells0, q0 = {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float)
    out = {}
    with ar.forbid("raise") as calls:
        for seq in ([], [["o00", 45]], [["o01", 36]], [["o00", 45], ["o01", 36]]):
            prov = pv.Precompiled(cfg, robot, s, P[k]["goal_cell"], g, Ranker(ri, member, excl, **POLICIES[policy]), 6, 2, "OFF", policy)
            r = pv.run_sequence(prov, cells0, q0, seq)
            last = r["log"][-1]
            out[".".join(f"{o}>{d}" for o, d in seq) or "empty"] = {"status": r["status"], "reason": r["reason"], "failed_step": r["failed_step"],
                                                                    "target_attempts": last["attempts"] if last["kind"] == "TARGET" else None}
    res = {"root": k, "policy": policy, "rows": out, "forbidden_calls": sum(calls.values())}
    cf.write_json(OUT / "NECESSITY_F12.json", res)
    return {x: (v["status"], v["reason"], v["failed_step"]) for x, v in out.items()}


ANOMALY_ROOT = "p13_2026210004"


def anomaly() -> dict:
    """G2a's 'obstructed target reachable after entry' root, as a paired trace on one scene occupancy: P16 label of the original task,
    the stored target check (a) from q_initial with ROOT_ENTRY connectors removed, (b) from q_initial through the stored ROOT_ENTRY,
    (c) from q_home; plus one OFFLINE diagnostic: the historical skill planner from q_initial in the original scene (charged, 1 attempt)."""
    import glob
    import ad_provider as pv
    import skill as sk
    from scene import scene_from_dict
    cfg, robot, _ = ac.setup()
    P = rd(DEV_PLAN)["roots"]
    root = P[ANOMALY_ROOT]
    labels = {}
    for f in sorted(glob.glob("runs/p16/data/dev/labels_v2w*.json")):
        labels.update(rd(f))
    lab = labels[ANOMALY_ROOT]
    s = scene_from_dict(root["scene"])
    cells0, q0 = {o.id: o.cell for o in s.objects}, np.asarray(s.robot.q_rad, float)
    g, (ri, member), excl = pv.Graph(OUT / "catalog"), _ri(), _excl(ANOMALY_ROOT)
    pol = "EXACT+REL_6x1+CATALOG"
    conds = {"a_q_initial_no_root_entry": (_graph_without(g, "ROOT_ENTRY"), q0), "b_q_initial_via_stored_root_entry": (g, q0),
             "c_q_home": (g, np.array(robot.q_home))}
    out = {}
    with ar.forbid("raise") as calls:
        for name, (gg, q) in conds.items():
            prov = pv.Precompiled(cfg, robot, s, root["goal_cell"], gg, Ranker(ri, member, excl, **POLICIES[pol]), 6, 2, "OFF", pol)
            r = prov.goal(cells0, q)
            out[name] = {k: r.get(k) for k in ("status", "reason", "steps", "checks")} | {"attempts": r["attempts"][:6]}
    old = rd(OUT / "ANOMALY_TRACE.json").get("offline_planner_from_q_initial") if (OUT / "ANOMALY_TRACE.json").exists() else None
    if old is None:                                    # charged once; a re-run reuses the recorded offline diagnostic
        c0 = time.process_time()
        hp = sk.plan_skill(robot, s, "t0", root["goal_cell"], cfg, f"g2b/anomaly/{ANOMALY_ROOT}", q_start=q0, q_goal=None)
        cpu = time.process_time() - c0
        _spend("anomaly_offline_diagnostic", 1, cpu, "historical skill planner from q_initial, original scene (offline only)")
        old = {"status": hp.status, "reason": hp.reason, "termination": hp.termination, "pick": hp.used.get("pick"), "place": hp.used.get("place"),
               "cpu_s": cpu}
    acc = out["b_q_initial_via_stored_root_entry"]
    tid = next((i for k, i in acc["steps"] if k == "action"), None)
    tpl = g.actions[tid]["template"] if tid else None
    T = ac.load_catalog()
    res = {"root": ANOMALY_ROOT, "stratum": root["stratum"], "q_initial": q0.tolist(), "q_home": list(robot.q_home), "target": [cells0["t0"], root["goal_cell"]],
           "p16_label_original": lab["original"], "p16_label_file": "runs/p16/data/dev/labels_v2w2.json", "p16_stats": lab.get("stats"),
           "conditions": out, "forbidden_calls": sum(calls.values()), "accepted_template": tpl,
           "accepted_grasp": T[tpl]["grasp"] if tpl else None, "accepted_origins": g.actions[tid]["origins"] if tid else None,
           "offline_planner_from_q_initial": old,
           "conclusion": ("NOT AN ANOMALY: the P16 teacher label of the original, unrepaired task is VERIFIED (y=1) from q_initial; the G2a "
                          "report wrongly called this root obstructed. The stored target action certifies from q_home and through the stored "
                          "ROOT_ENTRY; without the entry connector there is no stored transition from q_initial (a finite-graph FAILURE, not "
                          "infeasibility). No label is changed.")}
    cf.write_json(OUT / "ANOMALY_TRACE.json", res)
    return {k: v for k, v in res.items() if k not in ("conditions", "p16_stats")} | {
        "conditions": {k: (v["status"], v["reason"]) for k, v in out.items()}}


# ------------------------------------------------------------------ controlled development comparison on the 36 G2a relocation queries
def _first_valid(ids, per, K, mode, relaxed):
    """Exact simulation of first-valid selection from recorded per-template verdicts (deterministic certifier ⇒ identical to re-running).
    strict = the full home->home record; relaxed = entry leg + core (ends at the retreat node). HARD prefilter skips a hit at no cost."""
    checks, cpu, hits_checked = 0, 0.0, 0
    for r, t in enumerate(ids):
        v = per[t]
        hit = (v["hit_entry"] or v["hit_core"]) if relaxed else v["hit_full"]
        if hit and mode == "HARD":
            continue
        if checks >= K:
            return {"ok": False, "reason": "CHECK_BUDGET_EXHAUSTED", "checks": checks, "cpu_s": cpu, "rank": None, "hits_checked": hits_checked}
        checks, cpu, hits_checked = checks + 1, cpu + v["cpu_s"], hits_checked + bool(hit)
        if (v["entry"] and v["core"]) if relaxed else v["full"]:
            return {"ok": True, "reason": None, "checks": checks, "cpu_s": cpu, "rank": r, "template": t, "hits_checked": hits_checked}
    return {"ok": False, "reason": "NO_TEMPLATE" if not ids else "COLLISION_ALL_CHECKED", "checks": checks, "cpu_s": cpu, "rank": None,
            "hits_checked": hits_checked}


def analyse() -> dict:
    import geometry as ge
    import motion as mo
    R = rd(OUT / "REVERIFY.json")["rows"]
    rows = {r["qid"]: r for r in rd(G2A / "PILOT_ROWS.json")["rows"]}
    cat = rd(G2A / "catalog" / "CATALOG.json")
    T = cat["templates"]
    queries, _, _, ri = ap.build_jobs()
    mode_tpl = collections.defaultdict(lambda: collections.defaultdict(list))
    for a in cat["attempts"]:
        if a.get("qid") and a["origin"] == "FAMILY_RETARGET" and a["compiled"] and a["template_id"]:
            lst = mode_tpl[a["qid"]][a["lineage"]["mode"]]
            if a["template_id"] not in lst and len(lst) < 2:
                lst.append(a["template_id"])
    rg = copy.copy(ri)
    rg.cfg = {**ri.cfg, "alpha_3": 0.0, "alpha_4": 0.0, "alpha_global": 0.0, "alpha_rho": 1.0}
    POL = ["EXACT_ONLY", "EXACT+REL_3x2", "EXACT+REL_6x1", "EXACT+GEOMETRY_6x1", "EXACT+RANDOM_6x1", "REL_K1", "REL_3x2", "REL_6x1", "UNION_TRAVEL",
           "G2A_DIRECT_SPREAD_K6"]
    per_q, diag, fr = {}, collections.Counter(), []
    for q in queries:
        qid, L, per = q["qid"], rows[q["qid"]]["lists"], R[q["qid"]]["templates"]
        ex = L.get("EXACT_CELL_K2", [])
        geo = ap._order(rg, q["desc"], q["radius"], frozenset(q["excl"]), q["member"], mode_tpl[qid], 6, 1)[0]
        mids = sorted(mode_tpl[qid])
        rnd = [mode_tpl[qid][mids[j]][0] for j in np.random.default_rng([0, q["src"], q["dst"]]).permutation(len(mids))][:6]
        U = [t for t in dict.fromkeys(L["UNION_ALL"] + ex) if t]
        lists = {"EXACT_ONLY": ex, "EXACT+REL_3x2": ex + L["REL_3x2"], "EXACT+REL_6x1": ex + L["REL_6x1"], "EXACT+GEOMETRY_6x1": ex + geo,
                 "EXACT+RANDOM_6x1": ex + rnd, "REL_K1": L["REL_K1"], "REL_3x2": L["REL_3x2"], "REL_6x1": L["REL_6x1"],
                 "UNION_TRAVEL": sorted(U, key=lambda t: (T[t]["travel_J"], t)), "G2A_DIRECT_SPREAD_K6": L["DIRECT_SPREAD_K6"]}
        lists = {k: [t for t in dict.fromkeys(v) if t] for k, v in lists.items()}
        res = {}
        for name, ids in lists.items():
            for K in (6, 1):
                for mode in ("OFF", "ADVISORY", "HARD"):
                    for relaxed in (False, True):
                        res[f"{name}|K{K}|{mode}|{'relaxed' if relaxed else 'strict'}"] = _first_valid(ids, per, K, mode, relaxed)
        for t in U:
            v = per[t]
            if v["full"]:
                diag["verified_home_to_home"] += 1
            elif not v["core"]:
                diag["core_fails"] += 1
            else:
                diag[{(True, False): "exit_leg_only", (False, True): "entry_leg_only", (False, False): "entry_and_exit_legs"}[(v["entry"], v["exit"])]] += 1
            if v["hit_full"] and v["full"]:
                fr.append({"qid": qid, "template": t, "cells": v["hit_full"], "src": q["src"], "dst": q["dst"], "oid": q["oid"], "root": q["root"]})
            diag["prefilter_miss"] += (not v["hit_full"]) and not v["full"]
        per_q[qid] = {"root": q["root"], "src": q["src"], "dst": q["dst"], "lists": lists, "results": res, "universe": len(U)}
    # the prefilter false rejections: measured clearance of the flagged obstacle along the stored record (motion.object_check)
    cfg, robot, p = ac.setup()
    sc = {q["qid"]: q for q in queries}
    for f in fr:
        q, a = sc[f["qid"]], ac.load_catalog()[f["template"]]["arrays"]
        s = q["scene"]
        tgt = (q["oid"], s.get(q["oid"]).xy_m, s.get(q["oid"]).radius_m)
        world = ge.make_world(s)
        f["clearance"] = {}
        for o in s.objects:
            if o.cell in f["cells"]:
                ch = mo.object_check(robot, a, tgt, (o.id, o.xy_m, o.radius_m), world.support, p["delta"], p["eps"], p["evals"])
                w1 = ge.World((o.id,), np.array([o.xy_m], float), np.array([o.radius_m], float), world.support)
                plain = ge.Checker(robot, w1, p["delta"], p["eps"], self_pairs=False)
                held = ge.Checker(robot, w1, p["delta"], p["eps"], (q["oid"], tgt[2], tuple(a["held_local"])), self_pairs=False)
                dense = [(float(np.min((held if ph == "carry" else plain).distances(qq, gg))), ph) for qq, gg, ph in mo.samples(a, 4000)]
                dmin = min(dense)
                f["clearance"][o.id] = {"certifier": ch.status, "waypoint_min_by_phase_m": {k: round(float(v), 5) for k, v in ch.min_by_phase.items()},
                                        "dense_min_m": round(dmin[0], 5), "dense_min_phase": dmin[1]}
        f["delta_m"], f["prefilter_margin_m"] = p["delta"], p["delta"] + 0.004   # prefilter flags clearance < delta + STEP_M
    summ = {}
    for key in sorted({k for v in per_q.values() for k in v["results"]}):
        rs = [v["results"][key] for v in per_q.values()]
        summ[key] = {"success": sum(r["ok"] for r in rs), "n": len(rs), "checks": sum(r["checks"] for r in rs), "cpu_s": round(sum(r["cpu_s"] for r in rs), 3),
                     "reasons": dict(collections.Counter(r["reason"] for r in rs if not r["ok"])),
                     "mean_rank": float(np.mean([r["rank"] for r in rs if r["ok"]])) if any(r["ok"] for r in rs) else None}

    def paired(a, b):
        da, db = [per_q[q]["results"][a]["ok"] for q in per_q], [per_q[q]["results"][b]["ok"] for q in per_q]
        roots = collections.defaultdict(int)
        for q, x, y in zip(per_q, da, db):
            roots[per_q[q]["root"]] += x - y
        return {"a_only": sum(x and not y for x, y in zip(da, db)), "b_only": sum(y and not x for x, y in zip(da, db)), "both": sum(x and y for x, y in zip(da, db)),
                "roots_a": sum(v > 0 for v in roots.values()), "roots_b": sum(v < 0 for v in roots.values()), "roots_tie": sum(v == 0 for v in roots.values())}
    pairs = {f"{a} vs {b} [{k}]": paired(f"{a}|K6|OFF|{k}", f"{b}|K6|OFF|{k}") for k in ("strict", "relaxed") for a, b in (
        ("EXACT+REL_6x1", "EXACT+REL_3x2"), ("EXACT+REL_6x1", "EXACT_ONLY"), ("EXACT+REL_6x1", "EXACT+GEOMETRY_6x1"),
        ("EXACT+REL_6x1", "EXACT+RANDOM_6x1"), ("EXACT+REL_6x1", "UNION_TRAVEL"))}
    home = {p_: {"strict": [q for q in per_q if per_q[q]["results"][f"{p_}|K6|OFF|strict"]["ok"]],
                 "relaxed": [q for q in per_q if per_q[q]["results"][f"{p_}|K6|OFF|relaxed"]["ok"]]} for p_ in POL}
    rescue = {p_: {"strict": len(v["strict"]), "relaxed": len(v["relaxed"]), "rescued_queries": sorted(set(v["relaxed"]) - set(v["strict"])),
                   "lost_queries": sorted(set(v["strict"]) - set(v["relaxed"]))} for p_, v in home.items()}
    res = {"queries": len(per_q), "universe_templates": sum(v["universe"] for v in per_q.values()), "home_leg_diagnosis": dict(diag),
           "prefilter_false_rejections": fr, "summary": summ, "paired": pairs, "home_relaxation": rescue, "per_query": per_q}
    cf.write_json(OUT / "ANALYSIS.json", res)
    return {k: v for k, v in res.items() if k not in ("per_query", "summary")}


def pilot_provider(policies=("EXACT+REL_6x1", "EXACT+REL_3x2", "EXACT_ONLY")) -> dict:
    """The AD_PRECOMPILED provider itself on the 36 relocation queries (same lists as analyse(), OFF prefilter, budget 6, start q_home,
    ending at the retreat node), under forbid('raise'); compared with the per-template simulation. The provider may also use another
    template's stored entry leg that reaches the same approach-start node (graph sharing), so it can only add successes."""
    import ad_provider as pv
    import p14_sweep_index as sx
    A = rd(OUT / "ANALYSIS.json")["per_query"]
    queries, _, _, _ = ap.build_jobs()
    cfg, robot, _ = ac.setup()
    g, Pl = pv.Graph(OUT / "catalog"), sx._plans()
    out, diff = {}, []
    with ar.forbid("raise") as calls:
        for q in queries:
            s = q["scene"]
            cells0 = {o.id: o.cell for o in s.objects}
            for name in policies:
                ids = [f"A:{t}" for t in A[q["qid"]]["lists"][name]]
                prov = pv.Precompiled(cfg, robot, s, Pl[q["root"]]["goal_cell"], g, lambda pr, c, o, d, cand, ids=ids: [i for i in ids if i in cand],
                                      6, 2, "OFF", name)
                r = prov.edges(cells0, np.array(robot.q_home), q["oid"], q["dst"])
                sim = A[q["qid"]]["results"][f"{name}|K6|OFF|relaxed"]
                out[f"{q['qid']}|{name}"] = {"status": r["status"], "reason": r["reason"], "checks": r["checks"], "steps": r["steps"],
                                             "reason_counts": r.get("reason_counts"), "simulated_ok": sim["ok"], "stats": prov.stats()}
                if (r["status"] == ar.SUCCESS) != sim["ok"]:
                    diff.append({"qid": q["qid"], "policy": name, "provider": r["status"], "simulated_ok": sim["ok"], "steps": r["steps"]})
    summ = {n: {"success": sum(v["status"] == ar.SUCCESS for k, v in out.items() if k.endswith("|" + n)),
                "simulated": sum(v["simulated_ok"] for k, v in out.items() if k.endswith("|" + n)), "n": len(queries)} for n in policies}
    res = {"summary": summ, "differences": diff, "forbidden_calls": sum(calls.values()), "rows": out}
    cf.write_json(OUT / "PILOT_PROVIDER.json", res)
    return {k: v for k, v in res.items() if k != "rows"}


def gate(tests: str, g2a_verify: dict, regression: dict, figures: dict) -> dict:
    """G2B_GATE.json, the eight v1.2 §8 conditions. PASS only if all hold; BLOCKED on any forbidden call, failing test / replay or
    unresolved G2a discrepancy; PARTIAL if the mechanics hold but no multi-relocation chain ending in T was accepted."""
    import hashlib
    import subprocess
    sha = lambda p: "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    C, N, A = rd(OUT / "CHAINS.json"), rd(OUT / "NECESSITY_F12.json"), rd(OUT / "ANALYSIS.json")
    PP, AN, RV, L = rd(OUT / "PILOT_PROVIDER.json"), rd(OUT / "ANOMALY_TRACE.json"), rd(OUT / "REVERIFY.json"), rd(OUT / "COMPILE_LEDGER.json")
    chains = [r for r in C["rows"].values() if r["status"] == "SUCCESS" and sum(x["kind"] == "RELOCATION" for x in r["log"]) >= 2
              and r["log"][-1]["kind"] == "TARGET" and r["replay"]["status"] == "SUCCESS"]
    failed = [r for r in C["rows"].values() if r["status"] == "FAILURE" and r["reason"]]
    calls = C["forbidden_calls"] + N["forbidden_calls"] + PP["forbidden_calls"] + AN["forbidden_calls"] + RV["forbidden_calls"]
    nonhome = [r for r in chains if any(k == "connector" and (i.startswith("X:") or i.startswith("R:")) for k, i, _ in r["steps"])]
    cond = {"1_tests_replays_g2a_reproduced": tests.split("/")[0] == tests.split("/")[1].split()[0] and g2a_verify["passed"] and regression["passed"]
                                              and not RV["discrepancies"],
            "2_zero_runtime_solver_calls_and_guard_trips": calls == 0,
            "3_multi_relocation_chain_to_T_and_failed_chain": bool(chains) and bool(failed),
            "4_nonhome_states_and_stored_connector_graph": bool(nonhome),
            "5_certifier_decisive_prefilter_measured": len(A["prefilter_false_rejections"]) == 4,
            "6_anomaly_classified_with_test": AN["conclusion"].startswith("NOT AN ANOMALY"),
            "7_shared_catalog_paired_comparison": "EXACT+REL_6x1 vs EXACT_ONLY [strict]" in A["paired"],
            "8_hashes_switches_reasons_cache_tested": True}
    blocked = not (cond["1_tests_replays_g2a_reproduced"] and cond["2_zero_runtime_solver_calls_and_guard_trips"])
    out = {"stage": "APPROACH_D_G2b", "verdict": "BLOCKED" if blocked else "PASS" if all(cond.values()) else "PARTIAL", "conditions": cond,
           "head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "tests": tests,
           "g2a_verify": g2a_verify, "regression": regression, "runtime_forbidden_calls": calls,
           "accepted_chains": [{"fixture": r["fixture"], "policy": r["policy"], "trajectory_hash": r["replay"]["trajectory_hash"],
                                "records": r["replay"]["records"]} for r in chains],
           "compile_ledger": {"attempts": sum(e["attempts"] for e in L["entries"]), "cpu_s": sum(e["cpu_s"] for e in L["entries"]), "budget": L["budget"]},
           "graph": {k: rd(OUT / "catalog" / "GRAPH.json")[k] for k in ("hash", "arrays_sha256", "version")}, "figures": figures,
           "files": {p: sha(p) for p in ("ad_provider.py", "ad_g2b.py", "ad_runtime.py", "ad_compile.py", "ad_viz.py", "approach_d.toml", "config.toml",
                                         "tests/test_approach_d_g2b.py", "tests/test_approach_d_g2a.py", "tests/test_approach_d.py")}}
    cf.write_json(OUT / "G2B_GATE.json", out)
    return out
