"""Approach D G2a pilot (approachD_G2_offline_only_instructions_v1_1 §6 G2a): a modest, development-only physical pilot of the offline
compiler and the zero-solver runtime contract. Not the G2c benchmark: no validation / blind / test root is used as a query.

Cohort: the 36 G1 LOKO queries whose root is in the P10b-P13 'dev' split and has a relative family. For each, the move src -> dst in the
held-out witness's own scene (that witness is VERIFIED there from its own start q, so a motion exists in that scene). Exclusions follow G1
(query root, every root sharing its geometry fingerprint, and the query's absolute key). Offline, per query: the relative family's modes
(first two distinct snapped grasp classes per mode), the unseeded baselines, and (LORO, where they exist) exact-cell witnesses are compiled
in the generic fixture. Online, under ad_runtime.forbid('raise'): G1 ranks the modes from the query scene's patches and ad_runtime.check
certifies the frozen templates from q_home. Plus 24 P16 dev roots (ENTRY + target-T templates in the initial scene) and no-template probes."""
from __future__ import annotations

import collections
import copy
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

import ad_compile as ac
import ad_runtime as ar
import config as cf

OUT = ac.OUT
POLICIES = {"REL_K1": (1, 1), "REL_3x2": (3, 2), "REL_6x1": (6, 1)}
PROBES = [(0, 4), (8, 12), (16, 20), (24, 28), (40, 44), (56, 60)]       # sources inside / at the edge of the link-0 annulus


def rd(p):
    return json.loads(Path(p).read_text())


def witness_scene(e, P):
    """The scene a stored relocation was recorded in (p14_sweep_index.records' prefix rule) and the moved object's id."""
    import p14_sweep_index as sx
    d = Path(e["file"]).parent
    job = rd(d / "job.json")
    if "unit" in job:
        seq = job["unit"].get("sequence") or []
    else:
        seq = (rd(d / "result.json") if (d / "result.json").exists() else {}).get("committed_sequence") or []
    s = sx.scene_at(P[e["root"]], [list(x) for x in seq[:e["index"]]])
    oid = seq[e["index"]][0]
    assert s.get(oid).cell == e["src"], "witness scene reconstruction"
    return s, oid


def _modes(ri, key, keep, idx, W):
    """Canonical family modes after exclusion: mode id = its canonical seed (full-mode first member); up to 2W member seeds each."""
    import p14_sweep_index as sx
    out, member = [], {}
    for m in ri.modes.get(key, []):
        mid = f"{m[0]['file']}#{m[0]['index']}"
        for e in m:
            member[(e["file"], e["index"])] = mid
        kept = [e for e in m if keep(e)]
        if kept:
            out.append((mid, kept[:2 * W]))
    return out, member


def _seeds(modes, idx, src, dst, base):
    import ad_compile as ac
    import p14_sweep_index as sx
    out = []
    for mid, es in modes:
        for e in es:
            res, psi = sx.base_residual(base, e["src"], e["dst"], src, dst)
            out.append({"mode": mid, "ref": f"{e['file']}#{e['index']}", "root": e["root"], "seed_src": e["src"], "seed_dst": e["dst"],
                        "grasp": ac.grasp(idx.arrays(e)), "psi": psi, "residual_m": res})
    return out


def _order(ri, q, radius, excl, member, mode_tpl, L, W, exclude_abs=True):
    """Runtime template order for a (modes x per-mode) policy: G1 ranks the family's modes on the query patches; each mode contributes its
    first W offline templates (canonical, scene-independent). Pure retrieval: no motion is touched."""
    import p15_lookup as pl
    rv = copy.copy(ri)
    rv.cfg = {**ri.cfg, "mode_limit": L, "witnesses_per_mode": 1}
    r = pl.lookup_relative(rv, q, radius, excl, exclude_abs)
    ids, info = [], []
    for c in r["candidates"]:
        mid = member[(c["entry"]["file"], c["entry"]["index"])]
        for t in mode_tpl.get(mid, [])[:W]:
            if t not in ids:
                ids.append(t)
                info.append({"mode": mid, "seed": f"{c['entry']['file']}#{c['entry']['index']}", "score": c["total"],
                             "residual_m": c["residual_m"]})
    return ids[:L * W], info[:L * W]


def build_jobs():
    import p14_sweep_index as sx
    import p15_lookup as pl
    c = ac.ccfg()
    idx, _ = pl.index_v2()
    P = sx._plans()
    ri = pl.RelIndex(idx, pl.rel_cfg())
    fp_roots = collections.defaultdict(set)
    for es in idx.by_key.values():
        for e in es:
            fp_roots[pl.json_fp(P[e["root"]])].add(e["support_id"])
    rows = [r for r in rd("runs/approach_d/g1/RETRIEVAL_ROWS.json")["rows"] if r["proto"] == "LOKO" and r["rel_pool"]
            and P[r["root"]].get("split") == "dev"]
    queries, jobs = [], []
    for r in rows:
        src, dst = r["key"]
        f, i = r["query"].rsplit("#", 1)
        qe = next(e for e in idx.by_key[(src, dst)] if e["file"] == f and e["index"] == int(i))
        excl = frozenset(fp_roots[pl.json_fp(P[qe["root"]])] | {qe["root"]})
        keep = lambda e, excl=excl, k=(src, dst): e["support_id"] not in excl and (e["src"], e["dst"]) != k  # noqa: E731
        modes, member = _modes(ri, sx.rel_key(src, dst, qe["radius"]), keep, idx, c["templates_per_mode"])
        s, oid = witness_scene(qe, P)
        exact = sorted((e for e in idx.by_key[(src, dst)] if e["support_id"] not in excl), key=lambda e: (round(e["travel_J"], 12), e["file"], e["index"]))
        qid = f"Q{len(queries):02d}"
        queries.append({"qid": qid, "query": r["query"], "root": qe["root"], "split": "dev", "fingerprint": pl.json_fp(P[qe["root"]]),
                        "src": src, "dst": dst, "oid": oid, "scene": s, "desc": {k: qe[k] for k in ("src", "dst", "w3_src", "w4_src", "w3_dst",
                        "w4_dst", "global")}, "radius": qe["radius"], "excl": sorted(excl), "member": member, "n_modes": len(modes),
                        "g1": {k: r["variants"][v][k] for v in ("legacy_weights", "six_modes_x1") for k in ("hit1", "hitK")} | {
                            "hit1_3x2": r["variants"]["legacy_weights"]["hit1"], "hitK_3x2": r["variants"]["legacy_weights"]["hitK"],
                            "hitK_6x1": r["variants"]["six_modes_x1"]["hitK"]}, "witness": {"file": qe["file"], "index": qe["index"]}})
        jobs.append({"qid": qid, "src": src, "dst": dst, "kind": "RELOCATION", "direct_k": c["direct_k"], "seeds": _seeds(modes, idx, src, dst, ri.base),
                     "exact": [{"file": e["file"], "index": e["index"], "root": e["root"]} for e in _abs_modes(exact)[:2]]})
    targets = []
    for k, root in sorted(rd("runs/p16/data/dev/plan.json")["roots"].items()):
        from scene import scene_from_dict
        s = scene_from_dict(root["scene"])
        t0 = s.get("t0")
        excl = frozenset(fp_roots[json.dumps(root["fingerprint"])])
        keep = lambda e, excl=excl: e["support_id"] not in excl  # noqa: E731
        modes, member = _modes(ri, sx.rel_key(t0.cell, root["goal_cell"], t0.radius_m), keep, idx, c["templates_per_mode"])
        targets.append({"qid": f"T{len(targets):02d}", "root": k, "split": "dev", "fingerprint": json.dumps(root["fingerprint"]), "src": t0.cell,
                        "dst": root["goal_cell"], "oid": "t0", "scene": s, "q0": list(s.robot.q_rad), "stratum": root["stratum"],
                        "desc": sx.descriptor(s, root["goal_cell"], "t0", t0.cell, root["goal_cell"]), "radius": t0.radius_m, "excl": sorted(excl),
                        "member": member, "n_modes": len(modes)})
        jobs.append({"qid": targets[-1]["qid"], "src": t0.cell, "dst": root["goal_cell"], "kind": "TARGET", "direct_k": c["direct_k"],
                     "seeds": _seeds(modes, idx, t0.cell, root["goal_cell"], ri.base), "exact": []})
    jobs += [{"qid": f"P{i}", "src": a, "dst": b, "kind": "PROBE", "direct_k": c["direct_k"], "seeds": [], "exact": []} for i, (a, b) in enumerate(PROBES)]
    return queries, targets, jobs, ri


def _abs_modes(es):
    """Absolute (same-cell) modes by whole-path swept IoU (p14 MODE_IOU), canonical cheapest-first; one representative each."""
    import p14_sweep_index as sx
    reps = []
    for e in es:
        if all(len(r["_all"] & e["_all"]) / max(1, len(r["_all"] | e["_all"])) < sx.MODE_IOU for r in reps):
            reps.append(e)
    return reps


_CAT = None


def _evaluate(item):
    """Pool worker: every compiled template of one query certified in the query scene from q_home, with and without the prefilter
    (diagnostic), and each policy's first-valid runtime check, all under forbid('raise')."""
    global _CAT
    q, lists = item
    cfg, robot, _ = ac.setup()
    T = _CAT = _CAT or ac.load_catalog()
    home = np.array(robot.q_home)
    s = q["scene"]
    per, pol = {}, {}
    with ar.forbid("raise") as calls:
        entry = None
        if "q0" in q and not np.array_equal(np.asarray(q["q0"]), home):
            ents = [t for t in T.values() if t["kind"] == "ENTRY" and t["stratum"] == q["stratum"]]
            entry = ar.check_entry(robot, cfg, s, q["q0"], ents[0]) if ents else {"status": ar.FAILURE, "reason": "NO_TEMPLATE", "checks": 0}
        for t in sorted({x for ids in lists.values() for x in ids if x}):
            c0 = time.process_time()
            r = ar.check(robot, cfg, s, q["oid"], q["dst"], home, [T[t]], 1, prefilter=False)
            per[t] = {"verified": r["status"] == ar.SUCCESS, "prefilter_hit": sorted(set(T[t]["swept"]) & {o.cell for o in s.objects if o.id != q["oid"]}),
                      "rejection": (r["rejected"] or [None])[0], "cpu_s": time.process_time() - c0}
        for name, ids in lists.items():
            c0 = time.process_time()
            ok_entry = entry is None or entry["status"] == ar.SUCCESS
            r = ar.check(robot, cfg, s, q["oid"], q["dst"], home, [T[x] for x in ids if x], ar_budget()) if ok_entry else \
                {"status": ar.FAILURE, "reason": f"ENTRY_{entry['reason']}", "checks": entry["checks"], "rejected": [], "template_id": None}
            pol[name] = {**{k: r.get(k) for k in ("status", "reason", "checks", "prefiltered", "template_id")}, "n_templates": len([x for x in ids if x]),
                         "rank": ids.index(r["template_id"]) if r.get("template_id") in ids else None, "rejected": r.get("rejected", []),
                         "online_cpu_s": time.process_time() - c0}
    return q["qid"], per, pol, entry, dict(calls)


def ar_budget():
    import tomllib
    with open("approach_d.toml", "rb") as f:
        return tomllib.load(f)["runtime"]["check_budget"]


def run(workers=8) -> dict:
    t0 = time.time()
    queries, targets, jobs, ri = build_jobs()
    import p6_scenes as p6
    ctx = mp.get_context("spawn")
    with ctx.Pool(workers) as pool:
        comp = dict(zip([j["qid"] for j in jobs], pool.map(ac.compile_job, jobs, chunksize=1)))
    ent = ac.compile_entries({k: v for k, v in p6.STRATA.items()})
    templates = [x for o in comp.values() for x in o["templates"]] + ent["templates"]
    attempts = [{**a, "qid": q} for q, o in comp.items() for a in o["attempts"]] + ent["attempts"]
    cat = ac.save_catalog(templates, attempts)
    items = []
    for q in queries + targets:
        o = comp[q["qid"]]
        mode_tpl = o["modes"]
        lists = {"DIRECT_ORDER_K1": o["direct_order"][:1], "DIRECT_ORDER_K6": o["direct_order"], "DIRECT_SPREAD_K6": o["direct_spread"]}
        q["order_info"] = {}
        for name, (L, W) in POLICIES.items():
            lists[name], q["order_info"][name] = _order(ri, q["desc"], q["radius"], frozenset(q["excl"]), q["member"], mode_tpl, L, W, q["qid"][0] == "Q")
        if o.get("exact"):
            lists["EXACT_CELL_K2"] = o["exact"]
        lists["UNION_ALL"] = sorted({x for v in list(lists.values()) + list(mode_tpl.values()) for x in v if x})
        q["lists"] = lists
        items.append(({k: q[k] for k in ("qid", "oid", "dst", "scene") + (("q0", "stratum") if "q0" in q else ())}, lists))
    with ctx.Pool(workers) as pool:
        ev = {r[0]: r[1:] for r in pool.map(_evaluate, items, chunksize=1)}
    rows = []
    for q in queries + targets:
        per, pol, entry, calls = ev[q["qid"]]
        o = comp[q["qid"]]
        rows.append({k: v for k, v in q.items() if k not in ("scene", "member", "desc")} | {
            "screen": o["screen"], "templates": per, "policies": pol, "entry": entry, "calls_by_type": calls,
            "runtime_ik_calls": sum(v for k, v in calls.items() if k in ar.IK_ENTRIES),
            "runtime_planner_calls": sum(v for k, v in calls.items() if "<-" not in k and k not in ar.IK_ENTRIES)})
    probes = [{"qid": j["qid"], "src": j["src"], "dst": j["dst"], "templates": comp[j["qid"]]["direct_order"], "screen": comp[j["qid"]]["screen"],
               "attempts": comp[j["qid"]]["attempts"]} for j in jobs if j["kind"] == "PROBE"]
    res = {"version": ac.VERSION, "runtime": ar.VERSION, "catalog_hash": cat["hash"], "catalog_arrays_sha256": cat["arrays_sha256"],
           "wall_s": time.time() - t0, "workers": workers, "rows": rows, "probes": probes, "entry_attempts": ent["attempts"]}
    cf.write_json(OUT / "PILOT_ROWS.json", _plain(res))
    return summary(res)


def _plain(x):
    """JSON-safe copy (numpy arrays / scalars -> lists / floats)."""
    return json.loads(json.dumps(x, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


def _rate(xs):
    return [int(sum(xs)), len(xs)]


def summary(res=None) -> dict:
    res = res or rd(OUT / "PILOT_ROWS.json")
    cat = rd(OUT / "catalog" / "CATALOG.json")
    A = cat["attempts"]
    out = {"compile": {}, "relocation": {}, "target": {}, "probes": {}}
    for org in sorted({a["origin"] for a in A}):
        xs = [a for a in A if a["origin"] == org and not a["termination_reason"].startswith("DUPLICATE")]
        out["compile"][org] = {"attempts": len(xs), "compiled": sum(a["compiled"] for a in xs),
                               "negative_kind": dict(collections.Counter(a["negative_kind"] for a in xs if not a["compiled"])),
                               "termination": dict(collections.Counter(a["termination_reason"].split(":")[0] for a in xs if not a["compiled"])),
                               "cpu_s_total": sum(a["cpu_s"] for a in xs), "cpu_s_median": float(np.median([a["cpu_s"] for a in xs])) if xs else None}
    T = cat["templates"]
    out["compile"]["sweep_cpu_s_total"] = sum(t.get("sweep_cpu_s", 0.0) for t in T.values())
    out["compile"]["templates"] = len(T)
    fam = [a for a in A if a["origin"] == "FAMILY_RETARGET" and a["termination_reason"] != "DUPLICATE_OF_COMPILED"]
    out["compile"]["family_grasp_shift_deg"] = {"median": float(np.degrees(np.median([max(a["lineage"]["grasp_shift_rad"]) for a in fam
                                                                                      if a["lineage"].get("grasp_shift_rad")]))) if fam else None}
    for kind, pref in (("relocation", "Q"), ("target", "T")):
        R = [r for r in res["rows"] if r["qid"].startswith(pref)]
        pol = sorted({p for r in R for p in r["policies"]})
        o = out[kind]
        o["queries"] = len(R)
        o["runtime_ik_calls"], o["runtime_planner_calls"] = sum(r["runtime_ik_calls"] for r in R), sum(r["runtime_planner_calls"] for r in R)
        o["templates_checked"] = sum(len(r["templates"]) for r in R)
        o["templates_verified_in_query_scene"] = sum(v["verified"] for r in R for v in r["templates"].values())
        pf = [(bool(v["prefilter_hit"]), v["verified"]) for r in R for v in r["templates"].values()]
        o["prefilter"] = {"hits": sum(h for h, _ in pf), "false_rejects": sum(h and v for h, v in pf), "misses_of_collisions": sum(not h and not v for h, v in pf)}
        o["policies"] = {}
        for p in pol:
            rr = [r for r in R if p in r["policies"]]
            pp = [r["policies"][p] for r in rr]
            o["policies"][p] = {"queries": len(rr), "success": sum(x["status"] == ar.SUCCESS for x in pp),
                                "with_template": sum(x["n_templates"] > 0 for x in pp), "mean_templates": float(np.mean([x["n_templates"] for x in pp])),
                                "mean_checks": float(np.mean([x["checks"] for x in pp])), "reasons": dict(collections.Counter(x["reason"] for x in pp if x["reason"])),
                                "median_online_cpu_s": float(np.median([x["online_cpu_s"] for x in pp]))}
        if kind == "target":
            o["entry"] = dict(collections.Counter("HOME_START" if r["entry"] is None else r["entry"]["status"] + (":" + r["entry"]["reason"] if r["entry"]["reason"] else "")
                                                  for r in R))
    out["probes"] = {f"{p['src']}>{p['dst']}": {"templates": len({a["template_id"] for a in p["attempts"] if a["compiled"]}),
                                                 "planner_order_templates": len([x for x in p["templates"] if x]), "screen": p["screen"],
                                                 "termination": sorted({a["termination_reason"] for a in p["attempts"]})} for p in res["probes"]}
    out["wall_s"], out["catalog_hash"] = res["wall_s"], res["catalog_hash"]
    cf.write_json(OUT / "PILOT_SUMMARY.json", out)
    return out


def gate(tests: str, g1_verify: dict, regression: dict, figures: dict) -> dict:
    """G2A_GATE.json. Criteria (declared before the pilot ran): G1 re-verified; zero forbidden calls on every runtime row; the four required
    cases demonstrated on dev data (exact-cell reuse VERIFIED, genuine shifted transfer (base-rotation residual > 2 cm) VERIFIED, whole-arm
    collision outside both local windows REJECTED, no compiled template -> NO_TEMPLATE); unit tests and post-change regression clean.
    No success-rate threshold is part of the gate (the pilot is not a benchmark). PASS / PARTIAL (a case missing) / BLOCKED (any forbidden
    call, failing test or regression)."""
    import hashlib
    import subprocess
    sha = lambda p: "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    S, R = rd(OUT / "PILOT_SUMMARY.json"), rd(OUT / "PILOT_ROWS.json")
    calls = sum(r["runtime_ik_calls"] + r["runtime_planner_calls"] + sum(v for k, v in r["calls_by_type"].items() if "<-" not in k)
                for r in R["rows"])
    cases = {k: bool(figures.get("cases", {}).get(k)) for k in ("exact", "shifted", "collision", "probe")}
    clean = g1_verify.get("passed") and regression.get("passed") and tests.split("/")[0] == tests.split("/")[1].split()[0] and calls == 0
    out = {"stage": "APPROACH_D_G2a", "verdict": "BLOCKED" if not clean else "PASS" if all(cases.values()) else "PARTIAL",
           "scope": "offline compiler + zero-solver runtime contract + dev pilot; no G2b provider, no 442-query benchmark, no large catalog",
           "head": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "tests": tests,
           "g1_verify": g1_verify, "regression": regression, "runtime_forbidden_calls": calls, "cases": cases, "figures": figures,
           "catalog": {k: rd(OUT / "catalog" / "CATALOG.json")[k] for k in ("hash", "arrays_sha256", "version")} | {"templates": S["compile"]["templates"]},
           "files": {p: sha(p) for p in ("ad_compile.py", "ad_runtime.py", "ad_pilot.py", "ad_viz.py", "approach_d.toml", "config.toml",
                                         "tests/test_approach_d_g2a.py", "tests/test_approach_d.py", "p14_sweep_index.py", "p15_lookup.py")}}
    cf.write_json(OUT / "G2A_GATE.json", out)
    return out


REACH = [(0, 1), (1, 9), (8, 9), (9, 17), (17, 25), (25, 33), (33, 41), (41, 49), (26, 27), (18, 19), (34, 35), (2, 10)]


def reach_probes(pairs=REACH, workers=12) -> dict:
    """Empty-workspace reachability of source / destination pairs inside the link-0 annulus: does ANY declared-grasp template compile
    from q_home (planner order and branch spread, K = direct_k)? Written to REACH_PROBES.json."""
    c = ac.ccfg()
    jobs = [{"src": a, "dst": b, "kind": "PROBE", "direct_k": c["direct_k"], "seeds": [], "exact": []} for a, b in pairs]
    with mp.get_context("spawn").Pool(workers) as pool:
        outs = pool.map(ac.compile_job, jobs, chunksize=1)
    res = {f"{j['src']}>{j['dst']}": {"templates": len(o["templates"]), "planner_order_templates": len([x for x in o["direct_order"] if x]),
                                       "spread_templates": len([x for x in o["direct_spread"] if x]), "screen": o["screen"],
                                       "failures": dict(collections.Counter(a["termination_reason"] for a in o["attempts"] if not a["compiled"]))}
           for j, o in zip(jobs, outs)}
    cf.write_json(OUT / "REACH_PROBES.json", res)
    return res


# ------------------------------------------------------------------ Step B: dynamic trace of the historical (P16/P17) runtime
def audit_runtime_paths() -> dict:
    """Run one historical D node (P17 domain + p16_motion.DetPhysics) on a P16 dev root under forbid('count'): which forbidden entry points
    the existing inference path reaches, and from where. Then the new runtime under forbid('raise')."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_domain as dm
    plan = rd("runs/p16/data/dev/plan.json")
    k = sorted(plan["roots"])[0]
    task = pc.task_from_root(plan["roots"][k], k)
    idx = pl.index_v2()[0]
    out = {"root": k}
    phys = pm.DetPhysics(task, idx, budget={"motion_checks": 6, "online_moves": 1, "goal_plans": 1, "transit_plans": 1})
    cells0, q0 = {o.id: o.cell for o in phys.s0.objects}, phys.s0.robot.q_rad
    for name, fn in (("p17_domain.movers+slot_fn", lambda: dm.slot_fn(phys, idx, width=4, origin=cells0)(cells0, dm.movers(task, cells0)[0][0])),
                     ("DetPhysics.goal", lambda: phys.goal(cells0, q0)),
                     ("DetPhysics.edges", lambda: phys.edges(cells0, q0, dm.movers(task, cells0)[0][0],
                                                             dm.slot_fn(phys, idx, width=4, origin=cells0)(cells0, dm.movers(task, cells0)[0][0])[0]))):
        c0 = time.process_time()
        with ar.forbid("count") as calls:
            r = fn()
        out[name] = {"calls": dict(sorted(calls.items())), "cpu_s": time.process_time() - c0,
                     "result": r if name.startswith("p17") else str(r)[:200]}
    cf.write_json(OUT / "RUNTIME_PATH_AUDIT.json", out)
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(audit_runtime_paths() if sys.argv[1:] == ["audit"] else run(), indent=1)[:4000])
