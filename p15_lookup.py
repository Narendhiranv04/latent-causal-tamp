"""P15-2: multimodal motion evidence over the P14 index (real witnesses only): deterministic canonical mode clustering with terminal-pose
signature, leakage exclusion by root AND geometry fingerprint, and a leave-one-root-out transfer benchmark on real held-out scenes.

Query = a held-out witness's own reconstructed scene and start q (its existence proves the move was available there); candidates = witnesses
of the SAME absolute move from OTHER roots (other fingerprints). Every candidate is decided by the exact certifier: certified joint-linear
transit from the query q to the candidate start, then motion.certify_trajectory in the query scene. Similarity only orders candidates; a
threshold only skips candidates (cost control) and is fitted on a DEV half of the queries and scored on the other half."""
from __future__ import annotations

import collections
import json
import time
from pathlib import Path

import numpy as np

import config as cf
import p14_sweep_index as sx
from p15_bench import OUT, rd

MODE_IOU, MODE_QEND = 0.6, 0.3      # merge only if whole-path swept IoU >= 0.6 AND terminal configurations within 0.3 rad (L-inf)


def modes(entries):
    """Deterministic canonical clustering: entries in (travel, file, index) order; join the first mode whose seed has IoU >= MODE_IOU and
    terminal-q distance <= MODE_QEND; order-invariant because the canonical sort fixes the processing order."""
    out = []
    for e in sorted(entries, key=lambda e: (round(e["travel_J"], 12), e["file"], e["index"])):
        for m in out:
            s = m[0]
            iou = len(s["_all"] & e["_all"]) / max(1, len(s["_all"] | e["_all"]))
            if iou >= MODE_IOU and np.max(np.abs(np.asarray(s["q_end"]) - np.asarray(e["q_end"]))) <= MODE_QEND:
                m.append(e)
                break
        else:
            out.append([e])
    return out


def index_v2():
    """P14 entries minus any whose root fingerprint matches an excluded (evaluation-pool) root fingerprint; mode statistics."""
    idx = sx.Index()
    P = sx._plans()
    excl = set(rd("runs/p14/eval_roster.json")["excluded_roots"])
    bad_fp = {json_fp(P[k]) for k in excl if k in P}
    keep = collections.defaultdict(list)
    dropped = 0
    for key, es in idx.by_key.items():
        for e in es:
            if json_fp(P[e["root"]]) in bad_fp:
                dropped += 1
                continue
            keep[key].append(e)
    idx.by_key = keep
    return idx, dropped


def json_fp(r):
    import json
    return json.dumps(r["fingerprint"])


def mode_stats() -> dict:
    idx, dropped = index_v2()
    per = []
    kinds, grasp = collections.Counter(), collections.Counter()
    for key, es in idx.by_key.items():
        ms = modes(es)
        perm = modes(list(reversed(es)))
        per.append({"records": len(es), "roots": len({e["support_id"] for e in es}), "modes": len(ms),
                    "modes_ge2_roots": sum(len({x["support_id"] for x in m}) >= 2 for m in ms),
                    "permutation_invariant": [sorted(id(x) for x in m) for m in ms] == [sorted(id(x) for x in m) for m in perm]})
        kinds.update(e["kind"] for e in es)
        grasp.update(tuple(np.round(e["held_local"], 4)) for e in es)
    out = {"keys": len(per), "entries": sum(p["records"] for p in per), "fingerprint_dropped": dropped, "modes": sum(p["modes"] for p in per),
           "independent_supported_modes": sum(p["modes_ge2_roots"] for p in per), "keys_ge2_modes": sum(p["modes"] >= 2 for p in per),
           "permutation_invariant_keys": sum(p["permutation_invariant"] for p in per), "kinds": dict(kinds),
           "grasp_offsets_distinct": len(grasp), "note": "kind / grasp offset are recorded but not hard filters: the certifier checks the actual "
           "held disc against the current scene and check_record verifies the grasp holds the object where it rests"}
    (OUT / "lookup").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "lookup" / "MODE_STATS_V2.json", out)
    return out


def _certify(cx, scene, oid, q, a):
    """(status, reason): VERIFIED or the failing stage (transit / trajectory / record). Never an infeasibility claim."""
    import geometry as ge
    import motion as mo
    import p14_d_search as ds
    if ds._transit(cx, scene, oid, q, a["q"][0], float(a["gap"][0])) is None:
        return "UNKNOWN_TRANSIT", "straight transit to the witness start not certified"
    try:
        v = mo.certify_trajectory(cx.robot, scene, oid, a, cx.p["delta"], cx.p["eps"], cx.p["evals"])
    except ValueError as ex:
        return "INCOMPATIBLE_RECORD", str(ex)[:60]
    if all(x.status == ge.CLEAR for x in v):
        return "VERIFIED", None
    return ("COLLISION" if any(x.status == ge.COLLISION for x in v) else "UNRESOLVED"), next(x.pair for x in v if x.status != ge.CLEAR)


def transfer(max_per_key=2, seed=0) -> dict:
    """Leave-one-root-out transfer benchmark (see module docstring); per query, every compatible other-root candidate is certified."""
    import p14_d_search as ds
    idx, _ = index_v2()
    cx = ds.Ctx(lookup=None)
    rng = np.random.default_rng(seed)
    provs = {(p["file"], p["index"]): (p, r) for p, a, r in sx.records()}
    rows = []
    for key in sorted(idx.by_key):
        es = idx.by_key[key]
        roots = sorted({e["support_id"] for e in es})
        if len(roots) < 2:
            continue
        for qr in [roots[i] for i in rng.permutation(len(roots))[:max_per_key]]:
            qe = next(e for e in sorted(es, key=lambda e: (e["file"], e["index"])) if e["support_id"] == qr)
            prov, root = provs[(qe["file"], qe["index"])]
            scene = sx.scene_at(root, prov["prefix"])
            q = np.asarray(qe["q_start"], float)
            cands = [e for e in es if e["support_id"] != qr]
            t0 = time.process_time()
            res = {}
            for mode_name in ("combined", "local", "global"):
                fake = type("I", (), {})()
                fake.by_key, fake.version, fake.hash = {key: cands}, idx.version, idx.hash
                res[mode_name] = [(c["entry"]["file"], c["entry"]["index"], c["mode"], c["similarity"])
                                  for c in sx.lookup_candidates(fake, prov["moved"], key[0], key[1], scene, root["goal_cell"], qe["radius"], mode_name)["candidates"]]
            ms = modes(cands)
            mode_of = {(e["file"], e["index"]): mi for mi, m in enumerate(sorted(ms, key=lambda m: (-len({x["support_id"] for x in m}), min(x["travel_J"] for x in m)))) for e in m}
            st = {}
            for e in cands:
                st[(e["file"], e["index"])] = (*_certify(cx, scene, prov["moved"], q, sx.Index.arrays(idx, e)), e["travel_J"])
            rows.append({"key": list(key), "query_root": qr, "family": qe["family"], "candidates": len(cands), "modes": len(ms),
                         "status": {f"{f}#{i}": v[0] for (f, i), v in st.items()}, "travel": {f"{f}#{i}": v[2] for (f, i), v in st.items()},
                         "mode_of": {f"{f}#{i}": m for (f, i), m in mode_of.items()}, "ranking": {k2: [f"{f}#{i}" for f, i, _, _ in v] for k2, v in res.items()},
                         "similarity": {k2: [s for *_, s in v] for k2, v in res.items()}, "cpu_s": time.process_time() - t0})
    cf.write_json(OUT / "lookup" / "TRANSFER.json", {"rows": rows, "version": "P15_TRANSFER_V1"})
    return summarize()


def summarize(dev_frac=0.5) -> dict:
    """Top-1 / any-certified, calls to first certified, first- vs best-certified travel, rare-mode rescue, transit / collision failures;
    similarity threshold fitted on DEV queries (minimum calls with >= 95 % of DEV availability kept), scored on TEST queries."""
    rows = rd(OUT / "lookup" / "TRANSFER.json")["rows"]
    keys = sorted({tuple(r["key"]) for r in rows})
    dev = {k for i, k in enumerate(keys) if i % 2 == 0}
    def stats(rs, mode="combined", thr=None):
        out = collections.Counter()
        calls, gap = [], []
        for r in rs:
            rank = r["ranking"][mode]
            sims = r["similarity"][mode]
            avail = any(v == "VERIFIED" for v in r["status"].values())
            out["queries"] += 1
            out["available_any"] += avail
            tried = [c for c, s in zip(rank, sims) if thr is None or s >= thr]
            first = next((i for i, c in enumerate(tried) if r["status"][c] == "VERIFIED"), None)
            out["top1_certifies"] += bool(tried) and r["status"][tried[0]] == "VERIFIED"
            out["found_within_tried"] += first is not None
            calls.append((first + 1) if first is not None else len(tried))
            if first is not None:
                best = min(r["travel"][c] for c in r["status"] if r["status"][c] == "VERIFIED")
                gap.append(r["travel"][tried[first]] - best)
                top_mode = r["mode_of"][rank[0]]
                if r["status"][rank[0]] != "VERIFIED" and r["mode_of"][tried[first]] != top_mode:
                    out["rare_mode_rescue"] += 1
            for c, s in r["status"].items():
                out[f"candidate_{s}"] += 1
        return dict(out) | {"mean_certifier_calls": float(np.mean(calls)) if calls else None,
                            "mean_first_minus_best_travel": float(np.mean(gap)) if gap else None}
    D = [r for r in rows if tuple(r["key"]) in dev]
    T = [r for r in rows if tuple(r["key"]) not in dev]
    grid = sorted({s for r in D for s in r["similarity"]["combined"]})
    base = stats(D)["found_within_tried"]
    thr = max([t for t in grid if stats(D, thr=t)["found_within_tried"] >= 0.95 * base] or [None], key=lambda t: -1 if t is None else t)
    out = {"queries": len(rows), "dev_queries": len(D), "test_queries": len(T),
           "all": {m: stats(rows, m) for m in ("combined", "local", "global")},
           "threshold": {"value": thr, "dev": stats(D, thr=thr), "test_no_threshold": stats(T), "test_threshold": stats(T, thr=thr)},
           "note": "availability = some other-root witness certifies in the query scene; the query's own witness proves the move exists there"}
    cf.write_json(OUT / "lookup" / "TRANSFER_SUMMARY.json", out)
    return out


# ------------------------------------------------------------------ Approach D G1: relative top-mode retrieval (opt-in). Retrieval only:
# nothing here adapts or certifies a motion. A cross-location witness is flagged requires_adaptation and must never be handed to the
# certifier as is (its recorded joint path is anchored to other absolute cells); an empty result is UNKNOWN_NO_WITNESS, never infeasible.
REL_KEYS = {"key", "alpha_3", "alpha_4", "alpha_global", "alpha_rho", "rho_scale_m", "local_sweep_cheb", "mode_iou", "mode_limit",
            "witnesses_per_mode", "status_on_no_witness"}


def rel_cfg(path="approach_d.toml", **over) -> dict:
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["relative_lookup"]
    if set(c) != REL_KEYS or c["key"] not in ("delta_rc_and_footprint", "absolute_src_dst") or not c["status_on_no_witness"].startswith("UNKNOWN"):
        raise ValueError(f"invalid [relative_lookup]: {sorted(set(c) ^ REL_KEYS)} {c.get('key')}")
    return {**c, **over}


def rel_modes(entries, iou):
    """Canonical clustering inside one relative family: same terminal branch AND object-local sweep IoU >= iou with the mode seed. Entries
    are processed in (travel, file, index) order, so the result does not depend on listing order; members keep full provenance."""
    out = []
    for e in sorted(entries, key=lambda e: (round(e["travel_J"], 12), e["file"], e["index"])):
        for m in out:
            s = m[0]
            if s["_branch"] == e["_branch"] and len(s["_loc"] & e["_loc"]) / max(1, len(s["_loc"] | e["_loc"])) >= iou:
                m.append(e)
                break
        else:
            out.append([e])
    return out


class RelIndex:
    """Relative view of an absolute Index: families and their modes are precomputed once (deterministic); a query only filters and ranks."""

    def __init__(self, idx, cfg):
        self.idx, self.cfg = idx, cfg
        self.fam = sx.rel_view(idx, cfg["local_sweep_cheb"])
        self.modes = {k: rel_modes(es, cfg["mode_iou"]) for k, es in self.fam.items()}
        self.base = cf.load_config("config.toml")["arm2d"]["base_xy_m"]
        self.version, self.hash = sx.REL_VERSION, cf.stable_hash({"absolute": idx.hash, "cfg": cfg, "version": sx.REL_VERSION})


def rel_score(q, e, cfg, base) -> dict:
    """Deterministic retrieval score R = a3 sim3 + a4 sim4 + a_rho sim_rho + a_G sim_G (spec §4.2); not a learned energy, not feasibility."""
    s3 = (sx._sim(q["w3_src"], e["w3_src"]) + sx._sim(q["w3_dst"], e["w3_dst"])) / 2
    s4 = (sx._sim(q["w4_src"], e["w4_src"]) + sx._sim(q["w4_dst"], e["w4_dst"])) / 2
    res, psi = sx.base_residual(base, e["src"], e["dst"], q["src"], q["dst"])
    sr, sg = 1 / (1 + res / cfg["rho_scale_m"]), sx._sim(q["global"], e["global"])
    return {"total": cfg["alpha_3"] * s3 + cfg["alpha_4"] * s4 + cfg["alpha_rho"] * sr + cfg["alpha_global"] * sg, "sim3": s3, "sim4": s4,
            "sim_rho": sr, "sim_global": sg, "residual_m": res, "psi": psi}


def lookup_relative(ri, q, radius, exclude_roots=frozenset(), exclude_abs=False, modes=None) -> dict:
    """Bounded, diverse shortlist for the move q['src'] -> q['dst']: the (drow, dcol, footprint) family's precomputed modes minus excluded
    roots (callers pass every root sharing an excluded geometry fingerprint) and, if exclude_abs, minus the query's own absolute key;
    modes ranked by (best score, independent roots, cheapest travel), witnesses within a mode by (score, travel, provenance);
    mode_limit x witnesses_per_mode candidates at most."""
    cfg, key = ri.cfg, sx.rel_key(q["src"], q["dst"], radius)
    keep = lambda e: e["support_id"] not in exclude_roots and not (exclude_abs and (e["src"], e["dst"]) == (q["src"], q["dst"]))  # noqa: E731
    fam = [[e for e in m if keep(e)] for m in (ri.modes.get(key, []) if modes is None else modes)]
    fam = [m for m in fam if m]
    if not fam:
        return {"status": cfg["status_on_no_witness"], "candidates": [], "modes": 0, "pool": 0, "family": list(key), "index": ri.version}
    sc = {id(e): rel_score(q, e, cfg, ri.base) for m in fam for e in m}
    canon = lambda e: (-sc[id(e)]["total"], round(e["travel_J"], 12), e["file"], e["index"])  # noqa: E731
    fam = [sorted(m, key=canon) for m in fam]
    fam.sort(key=lambda m: (canon(m[0])[0], -len({x["support_id"] for x in m}), min(round(x["travel_J"], 12) for x in m), canon(m[0])[2:]))
    cands = []
    for mi, m in enumerate(fam[:cfg["mode_limit"]]):
        for j, e in enumerate(m[:cfg["witnesses_per_mode"]]):
            same = (e["src"], e["dst"]) == (q["src"], q["dst"])
            cands.append({"entry": e, "mode": mi, "rank_in_mode": j, "support": len({x["support_id"] for x in m}), "abs_key": [e["src"], e["dst"]],
                          "same_absolute": same, "requires_adaptation": not same, "adapted": False, "verified": False, **sc[id(e)]})
    return {"status": "CANDIDATES", "candidates": cands, "modes": len(fam), "pool": sum(map(len, fam)), "family": list(key),
            "index": ri.version, "index_hash": ri.hash}


def lookup_relative_scan(ri, q, radius, **kw) -> dict:
    """Brute-force reference (tests / efficiency only): scan every entry, recompute keys and modes, then the same ranking."""
    key = sx.rel_key(q["src"], q["dst"], radius)
    fam = [e for (s, d), es in sorted(ri.idx.by_key.items()) for e in es if sx.rel_key(s, d, e["radius"]) == key]
    return lookup_relative(ri, q, radius, modes=rel_modes(fam, ri.cfg["mode_iou"]), **kw)


def retrieve(ri, oid, src, dst, scene, goal, radius) -> dict:
    """Switchable lookup: key 'absolute_src_dst' = the legacy P14/P15 exact-cell lookup (unchanged, directly certifiable witnesses);
    'delta_rc_and_footprint' = relative retrieval (candidates need G2 adaptation before any certification)."""
    if ri.cfg["key"] == "absolute_src_dst":
        return sx.lookup_candidates(ri.idx, oid, src, dst, scene, goal, radius)
    return lookup_relative(ri, sx.descriptor(scene, goal, oid, src, dst), radius)


G1_OUT = Path("runs/approach_d/g1")
G1_VARIANTS = {"legacy_weights": {}, "plus_rho": {"alpha_rho": 0.5}, "rho_only": {"alpha_3": 0, "alpha_4": 0, "alpha_global": 0, "alpha_rho": 1},
               "w3_only": {"alpha_4": 0, "alpha_global": 0}, "w4_only": {"alpha_3": 0, "alpha_global": 0}, "global_only": {"alpha_3": 0, "alpha_4": 0},
               "top1_mode_x6": {"mode_limit": 1, "witnesses_per_mode": 6}, "six_modes_x1": {"mode_limit": 6, "witnesses_per_mode": 1}}


def _pattern(e, qe, iou):
    """Same motion pattern as the held-out query witness (which is VERIFIED in the query scene): same terminal branch and object-local
    sweep IoU >= iou. A retrieval-quality proxy only: it says nothing about whether an adapted motion would certify there."""
    return e["_branch"] == qe["_branch"] and len(e["_loc"] & qe["_loc"]) / max(1, len(e["_loc"] | qe["_loc"])) >= iou


def g1_benchmark(max_per_key=2, seed=0) -> dict:
    """Held-out neighbour retrieval on real witnesses (no motion is adapted or certified). Queries: up to max_per_key roots per absolute
    key; the query descriptor is that witness's own stored descriptor. LORO excludes the query root and every root sharing its geometry
    fingerprint; LOKO additionally excludes the query's absolute key (forces a new location: the legacy lookup has 0 candidates there)."""
    import copy
    idx, _ = index_v2()
    P = sx._plans()
    ri = RelIndex(idx, rel_cfg())
    fp_roots = collections.defaultdict(set)
    for es in idx.by_key.values():
        for e in es:
            fp_roots[json_fp(P[e["root"]])].add(e["support_id"])
    rng, rows = np.random.default_rng(seed), []
    for key in sorted(idx.by_key):
        es = sorted(idx.by_key[key], key=lambda e: (e["file"], e["index"]))
        roots = sorted({e["support_id"] for e in es})
        for qr in [roots[i] for i in rng.permutation(len(roots))[:max_per_key]]:
            qe = next(e for e in es if e["support_id"] == qr)
            excl = frozenset(fp_roots[json_fp(P[qr])] | {qr})
            for proto in ("LORO", "LOKO"):
                ab = [] if proto == "LOKO" else [e for e in es if e["support_id"] not in excl]
                t0 = time.perf_counter()
                r = lookup_relative(ri, qe, qe["radius"], excl, proto == "LOKO")
                t1 = time.perf_counter()
                s = lookup_relative_scan(ri, qe, qe["radius"], exclude_roots=excl, exclude_abs=proto == "LOKO")
                t2 = time.perf_counter()
                sig = lambda x: [(c["entry"]["file"], c["entry"]["index"], c["mode"]) for c in x["candidates"]]  # noqa: E731
                pool = [e for m in ri.modes.get(sx.rel_key(*key, qe["radius"]), []) for e in m if e["support_id"] not in excl
                        and not (proto == "LOKO" and (e["src"], e["dst"]) == key)]
                row = {"key": list(key), "query": f"{qe['file']}#{qe['index']}", "root": qr, "proto": proto, "abs_pool": len(ab),
                       "abs_pattern_any": any(_pattern(e, qe, ri.cfg["mode_iou"]) for e in ab), "rel_pool": r["pool"], "rel_modes": r["modes"],
                       "rel_status": r["status"], "pool_pattern_rate": float(np.mean([_pattern(e, qe, ri.cfg["mode_iou"]) for e in pool])) if pool else None,
                       "indexed_us": (t1 - t0) * 1e6, "scan_us": (t2 - t1) * 1e6, "scan_equal": sig(r) == sig(s), "variants": {}}
                for name, over in G1_VARIANTS.items():
                    rv = copy.copy(ri)
                    rv.cfg = {**ri.cfg, **over}
                    c = lookup_relative(rv, qe, qe["radius"], excl, proto == "LOKO")["candidates"]
                    hits = [_pattern(x["entry"], qe, ri.cfg["mode_iou"]) for x in c]
                    row["variants"][name] = {"n": len(c), "hit1": bool(hits and hits[0]), "hitK": any(hits), "modes": len({x["mode"] for x in c}),
                                             "abs_keys": len({tuple(x["abs_key"]) for x in c}), "cross": sum(x["requires_adaptation"] for x in c),
                                             "res1": c[0]["residual_m"] if c else None, "res_min": min((x["residual_m"] for x in c), default=None)}
                rows.append(row)
    cf.write_json(G1_OUT / "RETRIEVAL_ROWS.json", {"rows": rows, "index": ri.version, "index_hash": ri.hash, "cfg": ri.cfg})
    return g1_summary(rows)


def g1_summary(rows=None) -> dict:
    rows = rows or rd(G1_OUT / "RETRIEVAL_ROWS.json")["rows"]
    mean = lambda xs: float(np.mean(xs)) if len(xs) else None  # noqa: E731
    out = {}
    for proto in ("LORO", "LOKO"):
        R = [r for r in rows if r["proto"] == proto]
        cov = [r for r in R if r["rel_pool"]]
        out[proto] = {"queries": len(R), "absolute_coverage": sum(r["abs_pool"] > 0 for r in R), "relative_coverage": len(cov),
                      "absolute_pattern_available": sum(r["abs_pattern_any"] for r in R),
                      "relative_pattern_available": sum((r["pool_pattern_rate"] or 0) > 0 for r in R),
                      "mean_abs_pool": mean([r["abs_pool"] for r in R]), "mean_rel_pool": mean([r["rel_pool"] for r in cov]),
                      "mean_rel_modes": mean([r["rel_modes"] for r in cov]), "chance_hit1": mean([r["pool_pattern_rate"] for r in cov]),
                      "scan_equal": sum(r["scan_equal"] for r in R), "median_indexed_us": float(np.median([r["indexed_us"] for r in R])),
                      "median_scan_us": float(np.median([r["scan_us"] for r in R])),
                      "variants": {v: {"hit1": sum(r["variants"][v]["hit1"] for r in cov), "hitK": sum(r["variants"][v]["hitK"] for r in cov),
                                       "mean_returned": mean([r["variants"][v]["n"] for r in cov]), "mean_modes": mean([r["variants"][v]["modes"] for r in cov]),
                                       "mean_abs_keys": mean([r["variants"][v]["abs_keys"] for r in cov]),
                                       "mean_cross": mean([r["variants"][v]["cross"] for r in cov]),
                                       "mean_res1_m": mean([r["variants"][v]["res1"] for r in cov]),
                                       "mean_res_min_m": mean([r["variants"][v]["res_min"] for r in cov])} for v in G1_VARIANTS}}
    out["note"] = ("pattern hit = retrieved witness has the same terminal branch and object-local sweep (IoU >= mode_iou) as the held-out "
                   "witness that is VERIFIED in the query scene; a retrieval proxy, not a feasibility or reuse measurement (G2)")
    cf.write_json(G1_OUT / "RETRIEVAL_SUMMARY.json", out)
    return out


def g1_domain_coverage(splits=("dev", "calib", "val")) -> dict:
    """Candidate-move coverage on development roots (P16 dev / calib / val; never a test split): every mover x first four scene-only
    slots (p17_domain.slot_fn without library destinations, so both arms see the same moves). Coverage = at least one witness under the
    key; it is NOT motion availability (absolute witnesses still need certification, relative ones adaptation + certification)."""
    import p16_common as pc
    import p16_motion as pm
    import p17_domain as dm
    idx, _ = index_v2()
    P = sx._plans()
    ri = RelIndex(idx, rel_cfg())
    idx_fp = {json_fp(P[e["root"]]) for es in idx.by_key.values() for e in es}
    cnt, per = collections.Counter(), collections.Counter()
    for split in splits:
        roots = rd(f"runs/p16/data/{split}/plan.json")["roots"]
        for k in sorted(roots):
            if json.dumps(roots[k]["fingerprint"]) in idx_fp:
                cnt["roots_fingerprint_in_index_skipped"] += 1
                continue
            task = pc.task_from_root(roots[k], k)
            phys = pm.DetPhysics(task, None, use_lookup=False)
            cells = {o.id: o.cell for o in phys.s0.objects}
            sl = dm.slot_fn(phys, None, width=4, origin=cells)
            cnt["roots"] += 1
            for o in dm.movers(task, cells)[0]:
                rad = phys.s0.get(o).radius_m
                for d in sl(cells, o)[:4]:
                    a = any(abs(e["radius"] - rad) < 1e-9 for e in idx.by_key.get((cells[o], d), []))
                    r = bool(ri.fam.get(sx.rel_key(cells[o], d, rad)))
                    cnt["moves"] += 1
                    cnt["absolute"] += a
                    cnt["relative"] += r
                    cnt["relative_only"] += r and not a
                    per[split] += 1
    out = dict(cnt) | {"per_split_moves": dict(per), "splits": list(splits),
                       "note": "coverage = >= 1 indexed witness under the key; not motion availability"}
    cf.write_json(G1_OUT / "DOMAIN_COVERAGE.json", out)
    return out


def g1_gate(tests: str, baseline: dict) -> dict:
    """G1_GATE.json: verdict inputs plus exact code / config / index hashes (reproducibility manifest)."""
    import hashlib
    import subprocess
    sha = lambda p: "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
    S, cov = rd(G1_OUT / "RETRIEVAL_SUMMARY.json"), rd(G1_OUT / "DOMAIN_COVERAGE.json")
    ri = RelIndex(index_v2()[0], rel_cfg())
    ok = all(S[p]["scan_equal"] == S[p]["queries"] for p in ("LORO", "LOKO")) and S["LOKO"]["relative_coverage"] > 0 and tests.startswith("11/11")
    out = {"stage": "APPROACH_D_G1", "verdict": "PASS" if ok else "PARTIAL", "scope": "retrieval only; no motion adapted or certified",
           "base_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "tests": tests,
           "g0_baseline": baseline, "index": {"absolute": ri.idx.hash, "relative": ri.hash, "version": ri.version, "families": len(ri.fam),
                                               "modes": sum(map(len, ri.modes.values()))},
           "files": {p: sha(p) for p in ("p14_sweep_index.py", "p15_lookup.py", "p15_viz.py", "approach_d.toml", "tests/test_approach_d.py",
                                         "runs/p14/lookup/INDEX.json")},
           "domain_coverage": {k: cov[k] for k in ("moves", "absolute", "relative", "relative_only")},
           "held_out": {p: {k: S[p][k] for k in ("queries", "absolute_coverage", "relative_coverage", "chance_hit1", "scan_equal",
                                                  "median_indexed_us", "median_scan_us")} | {"legacy_weights": S[p]["variants"]["legacy_weights"]}
                        for p in ("LORO", "LOKO")}}
    cf.write_json(G1_OUT / "G1_GATE.json", out)
    return out
