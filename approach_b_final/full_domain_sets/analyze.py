#!/usr/bin/env python3
"""Evaluator-side analysis (reads private K / teacher caches / generator labels ONLY here, never in run.py or fsearch.py).
  recall    P1: known verified complete-repair witnesses vs frozen D4 / D6 / full legal domain (lower bounds; analysis only)
  tune      P2: DEV model-only summary + frozen parameter choice (no labels)
  manifest  P3: unique teacher queries of sealed REPAIR picks, deduped against exact-contract caches
  physical  P4: strict (UNKNOWN unresolved) and operational (v32b_phys) outcomes, paired root bootstrap, attribution
    python analyze.py recall PRIVATE GENLAB CACHE1,CACHE2,... OLD_P3_PER_ROOT"""
from __future__ import annotations

import collections, hashlib, itertools, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE.parent / "scripts"))
REP = HERE / "reports"


def jl(p):
    return [json.loads(l) for l in open(p)]


def boot(x, n=2000, seed=0):
    x = np.asarray(x, float); g = np.random.default_rng(seed)
    if not len(x):
        return [None, None, None]
    b = x[g.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(x.mean()), 4), round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)]


def strict_labels(caches):
    """(root, seq json) -> (x, y, x_status, y_status, source) from exact-contract caches; a value counts only if VERIFIED / CERTIFIED_*."""
    lab = {}
    ok = lambda s: s == "VERIFIED" or str(s).startswith("CERTIFIED")  # noqa: E731
    for c in caches:
        for l in open(c):
            v = json.loads(l)
            for x in v["results"]:
                xr, yr = x["x"] or {}, x["y"] or {}
                xs, ys = xr.get("status"), yr.get("status")
                xv = xr.get("x") if ok(xs) else None; yv = yr.get("y") if ok(ys) else None
                k = (v["root"], json.dumps(x["seq"]))
                if k not in lab or (None in lab[k][:2] and None not in (xv, yv)):
                    lab[k] = (xv, yv, xs, ys, Path(c).parent.name)
    return lab


def recall(private, genlab, caches, old_p3):
    """P1.  Witness = complete ordered relocation sequence with an independently VERIFIED success (x = y = 1, both statuses VERIFIED) in an
    exact-contract teacher cache (primary) or a generator label (labels.B, BD2D_TEACHER_V1 label protocol; secondary source, reported
    separately).  Classified by its WORST per-action frozen rank: TOP4 / RANK5_6 / BEYOND6, or GRAMMAR_OUTSIDE_SCOPE (K > 2, vacated /
    illegal / goal destination, repeated object or destination, fixed or target object)."""
    import run as RUN
    import search as S
    samp, scor, man = RUN.models()
    priv = {e["root_id"]: e for e in jl(private)}
    gen = {e["root_id"]: e for e in jl(genlab)}
    lab = strict_labels(caches)
    old = {e["root_id"]: e for e in jl(old_p3)}
    W = collections.defaultdict(dict)                                   # root -> seq json -> {sources}
    for (rid, sq), (xv, yv, xs, ys, src) in lab.items():
        if xv == 1 and yv == 1:
            W[rid].setdefault(sq, set()).add("CACHE:" + src)
    for rid, g in gen.items():
        idx = {n: i for i, n in enumerate(g["ids"])}
        for b in g["B"]:
            if b.get("y") == 1 and b.get("reason") == "VERIFIED":
                W[rid].setdefault(json.dumps([[idx[o], int(c)] for o, c in b["sequence"]]), set()).add("GENERATOR")
    conflicts = []
    for rid in W:
        for sq, src in W[rid].items():
            if "GENERATOR" in src and lab.get((rid, sq), (None,) * 2)[:2] not in ((None, None), (1, 1)) and None not in lab[(rid, sq)][:2]:
                conflicts.append({"root_id": rid, "seq": sq, "cache": lab[(rid, sq)][:4]})
    conf = {(c["root_id"], c["seq"]) for c in conflicts}
    per_root, wit = [], []
    for r in RUN.root_rows():
        rid = r["root_id"]; K = str(priv[rid]["K"]); root, dom, _ = RUN.build(r, samp, man, 0.25)
        legal, cats = set(dom.L), collections.Counter()
        for sq, src in sorted(W.get(rid, {}).items()):
            seq = [tuple(x) for x in json.loads(sq)]
            objs, dests = [o for o, _ in seq], [d for _, d in seq]
            if (rid, sq) in conf:
                c = "SOURCE_MISMATCH"
            elif len(seq) > 2 or len(set(objs)) < len(objs) or len(set(dests)) < len(dests) or any(o not in dom.objs or d not in legal for o, d in seq):
                c = "GRAMMAR_OUTSIDE_SCOPE"
            else:
                t = max(dom.tier[a] for a in seq); c = {1: "TOP4", 2: "RANK5_6", 3: "BEYOND6"}[t]
            prim = any(s.startswith("CACHE") for s in src)
            rec = {"root_id": rid, "K": K, "seq": seq, "category": c, "primary_source": prim, "sources": sorted(src), "len": len(seq)}
            if c in ("TOP4", "RANK5_6", "BEYOND6"):
                A = tuple(sorted(seq)); sc = scor.score(root, [list(map(list, p)) for p in itertools.permutations(A)])
                rec.update({"ranks": [dom.rank[a] + 1 for a in seq], "raw_prior": [dom.raw[a] for a in seq], "stratum": dom.strata(A),
                            "p11_this_order": scor.score(root, [list(map(list, seq))])[0]["p11"], "p11_best_order": max(x["p11"] for x in sc)})
            wit.append(rec); cats[(c, prim)] += 1
        o = old.get(rid, {}); e4 = (o.get("EXACT_K2@None") or {})
        per_root.append({"root_id": rid, "K": K, "split": RUN.split_of(rid), "n_witness": sum(cats.values()),
                         "cats": {f"{c}|{'cache' if p else 'gen'}": n for (c, p), n in cats.items()}, "exact4_outcome": e4.get("outcome"),
                         "exact4_p11": e4.get("p11"), "objects": len(dom.objs), "legal_cells": len(dom.L)})
    return per_root, wit, conflicts


def recall_summary(per_root, wit, conflicts):
    S = {"witness_definition": "x = y = 1 with VERIFIED statuses (exact-contract caches) or labels.B y = 1 VERIFIED (generator); lower bounds only"}
    for src, f in (("cache", lambda w: w["primary_source"]), ("generator_only", lambda w: not w["primary_source"]), ("any", lambda w: True)):
        c = collections.Counter((w["K"], w["category"]) for w in wit if f(w))
        S[f"witnesses_{src}"] = {f"K{k}|{cat}": n for (k, cat), n in sorted(c.items())}
    roots = collections.defaultdict(lambda: collections.Counter())
    bykey = collections.defaultdict(list)
    for w in wit:
        bykey[w["root_id"]].append(w)
    for src in ("cache", "any"):
        T = {}
        for K in ("1", "2"):
            R = [p for p in per_root if p["K"] == K]
            c = collections.Counter()
            for p in R:
                ws = [w for w in bykey[p["root_id"]] if (src == "any" or w["primary_source"]) and w["category"] in ("TOP4", "RANK5_6", "BEYOND6")]
                cs = {w["category"] for w in ws}
                c["roots"] += 1
                c["with_any_k_le2_witness"] += bool(ws)
                c["any_witness_in_TOP4"] += "TOP4" in cs
                c["any_witness_outside_TOP4"] += bool(cs - {"TOP4"})
                c["any_witness_outside_TOP6"] += "BEYOND6" in cs
                c["ONLY_outside_TOP4 (no known D4 witness)"] += bool(cs) and "TOP4" not in cs
                c["ONLY_BEYOND6"] += cs == {"BEYOND6"}
                c["no_known_witness"] += not ws
                if p["exact4_outcome"] is not None:
                    c["exact4_physically_evaluated (old P3, EVAL)"] += 1
                    if p["exact4_outcome"] != "SUCCESS":
                        c["exact4_not_success"] += 1
                        c["exact4_not_success|known_D4_witness (pool had a success: selection/ranking)"] += "TOP4" in cs
                        c["exact4_not_success|ONLY_outside_D4_witness (pool-miss candidate)"] += bool(cs) and "TOP4" not in cs
                        c["exact4_not_success|no_known_K<=2_witness"] += not cs
                if p["exact4_outcome"] not in (None, "SUCCESS") and cs - {"TOP4"}:
                    c[f"exact4_{p['exact4_outcome']}_AND_outside_TOP4_witness"] += 1
                    c["exact4_failed_AND_outside_TOP4_witness"] += 1
                    c["exact4_failed_AND_ONLY_outside_TOP4_witness"] += "TOP4" not in cs
            T[f"K{K}"] = dict(c)
        S[f"roots_{src}"] = T
    S["source_conflicts"] = len(conflicts)
    S["source_overlap_cache_and_generator"] = sum(1 for w in wit if w["primary_source"] and "GENERATOR" in w["sources"])
    m = collections.Counter()                                  # would the frozen X/Y even prefer a known off-top-4 witness? (model-only)
    for p in per_root:
        ws = [w for w in bykey[p["root_id"]] if w["category"] in ("RANK5_6", "BEYOND6")]
        if p["K"] in ("1", "2") and p["exact4_outcome"] not in (None, "SUCCESS") and ws:
            b = max(w["p11_best_order"] for w in ws); m["exact4_failed_roots_with_off4_witness"] += 1
            m["witness_best_order_p11_ge_eta_0.3"] += b >= 0.3
            m["witness_best_order_p11_gt_exact4_pick_p11"] += b > (p["exact4_p11"] or 0.0)
    S["model_preference_on_exact4_failed_roots"] = dict(m)
    oo = [w for w in wit if w["category"] in ("RANK5_6", "BEYOND6") and w["K"] in ("1", "2")]
    S["outside_top4_witness_rank_quantiles"] = np.percentile([max(w["ranks"]) for w in oo], [10, 25, 50, 75, 90]).round(1).tolist() if oo else None
    S["outside_top4_witness_best_order_p11_quantiles"] = np.percentile([w["p11_best_order"] for w in oo], [10, 25, 50, 75, 90]).round(3).tolist() if oo else None
    return S


# ---------------------------------------------------------------------------------------------------------------------- P2 model-only
def regret(ef, x):
    """p11(EXACT_FULL committed) - p11(arm committed); NOOP / ABSTAIN count as 0 unless EXACT_FULL made the same NOOP / ABSTAIN."""
    if x["decision"] == ef["decision"] and ef["decision"] in ("NOOP", "ABSTAIN"):
        return 0.0
    return (ef["p11"] if ef["decision"] == "REPAIR" else 0.0) - (x["p11"] if x["decision"] == "REPAIR" else 0.0)


def agree(a, b):
    return a["decision"] == b["decision"] and (a["decision"] != "REPAIR" or a["seq"] == b["seq"])


def load(files):
    """All root records, de-duplicated by root_id (helper workers may finish the same root twice; replay is deterministic)."""
    R = {}
    for f in files:
        for r in jl(f):
            R.setdefault(r["root_id"], r)
    return sorted(R.values(), key=lambda r: r["root_id"])


def tune(files):
    """P2_TUNING_PREREG: per arm, argmin mean regret @1024 (seeds 0, 1), then regret @256, then agreement @1024, then grid order."""
    import run as RUN
    G = RUN.grid(); R = load(files)
    acc = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in R:
        ef = next(x for x in r["results"] if x["arm"] == "EXACT_FULL")
        for x in r["results"]:
            if x["cfg"] is not None:
                acc[x["cfg"]][("reg", x["budget"])].append(regret(ef, x)); acc[x["cfg"]][("agr", x["budget"])].append(agree(ef, x))
    rows = []
    for j, (arm, p) in enumerate(G):
        a = acc[j]
        rows.append({"cfg": j, "arm": arm, "params": p, "regret_1024": float(np.mean(a[("reg", 1024)])), "regret_256": float(np.mean(a[("reg", 256)])),
                     "agree_1024": float(np.mean(a[("agr", 1024)])), "agree_256": float(np.mean(a[("agr", 256)])), "n": len(a[("reg", 1024)])})
    best = {}
    for arm in ("PW_MCTS_SEEDED4", "PW_MCTS_FULL", "BEAM_SEEDED4", "BEAM_FULL"):
        c = [x for x in rows if x["arm"] == arm]
        m = min(x["regret_1024"] for x in c)
        c = [x for x in c if x["regret_1024"] <= m + 1e-4]
        best[arm] = min(c, key=lambda x: (x["regret_256"], -x["agree_1024"], x["cfg"]))
    fp = {a: b["params"] for a, b in best.items()}
    fp["PW_MCTS_UNIFORM"] = {**fp["PW_MCTS_FULL"], "eps": 1.0}; fp["BEAM_FULL_UNIFORM"] = {**fp["BEAM_FULL"], "eps": 1.0}; fp["RAND_FULL"] = {}
    (REP / "P2_TUNING.json").write_text(json.dumps({"roots": len(R), "chosen": best, "all": rows}, indent=1))
    (REP / "P2_FROZEN_PARAMS.json").write_text(json.dumps(fp, indent=1)); print(json.dumps(best, indent=1))


def model(files, out):
    """K-blind model-only summary per arm x budget (seeds pooled): regret / agreement vs EXACT_FULL, agreement vs EXACT4, pick strata,
    off-top-4 share of scored sets, charges, batches, stops, tier events, replay wall."""
    R = load(files); S = {"roots": len(R), "arms": {}}
    g = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in R:
        ef = next(x for x in r["results"] if x["arm"] == "EXACT_FULL"); e4 = next(x for x in r["results"] if x["arm"] == "EXACT4")
        for x in r["results"]:
            k = f"{x['arm']}@{x['budget']}"; d = g[k]
            d["regret"].append(regret(ef, x)); d["agree_full"].append(agree(ef, x)); d["agree_exact4"].append(agree(e4, x))
            d["repair"].append(x["decision"] == "REPAIR"); d["scored"].append(x["scored"]); d["batches"].append(x["batches"])
            d["pick_off4"].append(x["decision"] == "REPAIR" and x["pick_stratum"] != "TOP4_ONLY")
            d["pick_beyond6"].append(x["decision"] == "REPAIR" and "BEYOND6" in (x["pick_stratum"] or ""))
            t = x["sets_by_max_tier"] or {}; n = sum(t.values()) or 1
            d["off4_set_share"].append((t.get("2", 0) + t.get("3", 0)) / n); d["stop"].append(x["stop"]); d["wall"].append(x["wall_s"])
            d["early_unlock"].append(any(e[2] == "EARLY_TIER_EXHAUSTION" for e in x["tier_events"] or []))
            d["tail_unlocked"].append(any(e[0] == 3 for e in x["tier_events"] or []) if "SEEDED" in x["arm"] else None)
    for k, d in sorted(g.items()):
        S["arms"][k] = {"n": len(d["regret"]), "mean_regret": round(float(np.mean(d["regret"])), 5), "agree_EXACT_FULL": round(float(np.mean(d["agree_full"])), 4),
                        "agree_EXACT4": round(float(np.mean(d["agree_exact4"])), 4), "repair_rate": round(float(np.mean(d["repair"])), 4),
                        "pick_off_top4": round(float(np.mean(d["pick_off4"])), 4), "pick_beyond6": round(float(np.mean(d["pick_beyond6"])), 4),
                        "off4_set_share": round(float(np.mean(d["off4_set_share"])), 4), "median_scored": float(np.median(d["scored"])),
                        "median_batches": float(np.median(d["batches"])), "stops": dict(collections.Counter(d["stop"])),
                        "early_unlock_rate": round(float(np.mean(d["early_unlock"])), 4), "median_replay_wall_s": round(float(np.median(d["wall"])), 5)}
    Path(out).write_text(json.dumps(S, indent=1)); return S


# ------------------------------------------------------------------------------------------------------------------- P3 / P4 physical
PRIMARY = ["EXACT4@None", "EXACT6@None", "EXACT_FULL@None", "RAND_FULL@1024", "BEAM_SEEDED4@1024", "BEAM_FULL@1024", "PW_MCTS_SEEDED4@1024",
           "PW_MCTS_FULL@1024"]
SECONDARY = ["PW_MCTS_UNIFORM@1024", "BEAM_FULL_UNIFORM@1024", "PW_MCTS_SEEDED4@4096", "PW_MCTS_FULL@4096", "BEAM_SEEDED4@4096", "BEAM_FULL@4096"]


def picks(r, names):
    """Sealed seed-0 picks of root record r for 'ARM@B' names."""
    out = {}
    for x in r["results"]:
        k = f"{x['arm']}@{x['budget']}"
        if k in names and x["seed"] == 0:
            out[k] = x
    return out


def op_labels(caches):
    import v32b_phys as V
    lab = {}
    for c in caches:
        for k, v in V.labels("2d", c).items():
            if k not in lab or (None in lab[k] and None not in v):
                lab[k] = v
    return lab


def manifest(evalf, private, caches, out, cap=1200):
    """Unique (root, ordered REPAIR seq) of sealed picks on EVAL K1/K2 roots not already in ANY exact-contract cache (a cached UNKNOWN is
    never re-queried: no retries).  If the cap binds, whole roots in sha256('FDS_P3|'+root) order, primary tier first, then secondary."""
    have = set()
    for c in caches:
        for l in open(c):
            v = json.loads(l); have |= {(v["root"], json.dumps(x["seq"])) for x in v["results"]}
    priv = {e["root_id"]: e for e in jl(private)}
    R = [r for r in load(evalf.split(",")) if r["split"] == "EVAL" and str(priv[r["root_id"]]["K"]) in ("1", "2")]
    order = sorted(R, key=lambda r: hashlib.sha256(("FDS_P3|" + r["root_id"]).encode()).hexdigest())
    plan, used, stat = {}, set(), collections.Counter()
    for tier, names in (("primary", PRIMARY), ("secondary", SECONDARY)):
        for r in order:
            need = set()
            for k, x in picks(r, names).items():
                if x["decision"] == "REPAIR":
                    key = (r["root_id"], json.dumps(x["seq"])); stat[f"{tier}_repair_picks"] += 1
                    if key in have:
                        stat[f"{tier}_cached"] += 1
                    elif key not in used:
                        need.add(key)
            if len(used) + len(need) > cap:
                stat[f"{tier}_roots_not_covered"] += 1; continue
            used |= need; plan.setdefault(r["root_id"], set()).update(need); stat[f"{tier}_roots_covered"] += 1
    jobs = []
    for rid, ks in sorted(plan.items()):
        if ks:
            e = priv[rid]
            jobs.append({"root_id": rid, "dom": "2D", "path": e["path"], "geom": e.get("geom", "original"), "ids": e["ids"],
                         "seqs": [[[e["ids"][o], int(c)] for o, c in json.loads(k[1])] for k in sorted(ks)]})
    Path(out).write_text("".join(json.dumps(j) + "\n" for j in jobs))
    S = {"primary_roots": len(R), "new_queries": sum(len(j["seqs"]) for j in jobs), "roots_with_queries": len(jobs), "cap": cap, **stat,
         "cache_sha256": {Path(c).parent.name: hashlib.sha256(Path(c).read_bytes()).hexdigest() for c in caches},
         "jobs_sha256": hashlib.sha256(Path(out).read_bytes()).hexdigest(),
         "query_keys_sha256": hashlib.sha256(json.dumps(sorted(k for v in plan.values() for k in v)).encode()).hexdigest()}
    print(json.dumps(S)); return S


def outcome(x, lab, rid, strict):
    """-> SUCCESS / FAIL_Y / FAIL_X / NOOP / ABSTAIN / UNKNOWN (strict: values only under VERIFIED / CERTIFIED_*; operational: v32b_phys)."""
    if x["decision"] != "REPAIR":
        return x["decision"]
    v = lab.get((rid, json.dumps(x["seq"])))
    xv, yv = (v[0], v[1]) if v else (None, None)
    if yv == 0:
        return "FAIL_Y"
    if yv == 1 and xv == 1:
        return "SUCCESS"
    if yv == 1 and xv == 0:
        return "FAIL_X"
    return "UNKNOWN"


def cboot(pairs, clus, n=4000, seed=0):
    """Paired cluster (lineage family) bootstrap of the mean difference -> [mean, lo95, hi95]."""
    if not pairs:
        return [None, None, None]
    d = collections.defaultdict(list)
    for (a, b), c in zip(pairs, clus):
        d[c].append(a - b)
    keys = sorted(d); g = np.random.default_rng(seed); tot = np.array([sum(d[k]) for k in keys]); cnt = np.array([len(d[k]) for k in keys])
    idx = g.integers(0, len(keys), (n, len(keys)))
    bs = tot[idx].sum(1) / cnt[idx].sum(1)
    m = sum(a - b for a, b in pairs) / len(pairs)
    return [round(m, 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


CONTRASTS = [("PW_MCTS_SEEDED4@1024", "EXACT4@None"), ("PW_MCTS_SEEDED4@1024", "PW_MCTS_FULL@1024"), ("PW_MCTS_SEEDED4@1024", "BEAM_SEEDED4@1024"),
             ("PW_MCTS_SEEDED4@1024", "BEAM_FULL@1024"), ("BEAM_SEEDED4@1024", "EXACT4@None"), ("BEAM_FULL@1024", "EXACT4@None"),
             ("PW_MCTS_FULL@1024", "EXACT4@None"), ("EXACT6@None", "EXACT4@None"), ("EXACT_FULL@None", "EXACT4@None"), ("RAND_FULL@1024", "EXACT4@None"),
             ("BEAM_SEEDED4@1024", "BEAM_FULL@1024"), ("PW_MCTS_UNIFORM@1024", "PW_MCTS_FULL@1024"), ("BEAM_FULL_UNIFORM@1024", "BEAM_FULL@1024"),
             ("PW_MCTS_SEEDED4@4096", "EXACT4@None"), ("PW_MCTS_SEEDED4@4096", "BEAM_SEEDED4@4096")]


def physical(evalf, private, caches, fam, out_prefix):
    priv = {e["root_id"]: e for e in jl(private)}; famof = {e["root_id"]: e["parent_family_id"] for e in jl(fam)}
    labs = {"strict": {k: v[:2] for k, v in strict_labels(caches).items()}, "operational": op_labels(caches)}
    R = [r for r in load(evalf.split(",")) if r["split"] == "EVAL" and str(priv[r["root_id"]]["K"]) in ("1", "2", "0", "NONE")]
    names = PRIMARY + SECONDARY; S = {"cohort": "VAL EVAL (development evidence; not an independent test)", "roots": {}, "by_mode": {}}
    per = []
    for r in R:
        rid, K = r["root_id"], str(priv[r["root_id"]]["K"]); pk = picks(r, names)
        rec = {"root_id": rid, "K": K, "family": famof.get(rid)}
        for k, x in pk.items():
            rec[k] = {"decision": x["decision"], "seq": x["seq"], "p11": x["p11"], "pick_stratum": x["pick_stratum"],
                      **{m: outcome(x, labs[m], rid, m == "strict") for m in labs}}
        per.append(rec)
    S["roots"] = dict(collections.Counter(p["K"] for p in per))
    for m in labs:
        T = {"arms": {}, "contrasts": {}}
        prim = [p for p in per if p["K"] in ("1", "2")]
        for k in names:
            row = {}
            for strat, P in (("K1", [p for p in prim if p["K"] == "1"]), ("K2", [p for p in prim if p["K"] == "2"]), ("K1+K2", prim)):
                o = [p[k][m] for p in P if k in p]
                n, s, u = len(o), sum(v == "SUCCESS" for v in o), sum(v == "UNKNOWN" for v in o)
                row[strat] = {"n": n, "success": s, "unknown": u, "decided": n - u, "rate_decided": round(s / max(n - u, 1), 4),
                              "itt_bounds": [round(s / max(n, 1), 4), round((s + u) / max(n, 1), 4)], "unknown_rate": round(u / max(n, 1), 4),
                              "outcomes": dict(collections.Counter(o))}
            row["K0_noop_correct"] = sum(p[k]["decision"] == "NOOP" for p in per if p["K"] == "0" and k in p)
            row["NONE_abstain_correct"] = sum(p[k]["decision"] == "ABSTAIN" for p in per if p["K"] == "NONE" and k in p)
            T["arms"][k] = row
        for a, b in CONTRASTS:
            for strat, P in (("K1+K2", prim), ("K1", [p for p in prim if p["K"] == "1"]), ("K2", [p for p in prim if p["K"] == "2"])):
                pr, cl = [], []
                for p in P:
                    if a in p and b in p and "UNKNOWN" not in (p[a][m], p[b][m]):
                        pr.append((int(p[a][m] == "SUCCESS"), int(p[b][m] == "SUCCESS"))); cl.append(p["family"] or p["root_id"])
                T["contrasts"][f"{a} - {b} | {strat}"] = {"pairs": len(pr), "diff": cboot(pr, cl), "wins": sum(x > y for x, y in pr),
                                                          "losses": sum(x < y for x, y in pr)}
        S["by_mode"][m] = T
    Path(out_prefix + ".json").write_text(json.dumps(S, indent=1))
    Path(out_prefix + "_PER_ROOT.jsonl").write_text("".join(json.dumps(p) + "\n" for p in per))
    return S, per


def attribution(evalf, private, caches, genlab, per_root_file, out):
    """Per K1/K2 EVAL root and arm (B = 1024 / exact), strict outcomes: why did it (not) succeed?  Uses every known decided witness
    (caches incl. this study's new queries + generator labels; analysis only) and the arm's stored scored sets / final tier level."""
    import run as RUN
    priv = {e["root_id"]: e for e in jl(private)}; per = {p["root_id"]: p for p in jl(per_root_file)}
    lab = {k: v[:2] for k, v in strict_labels(caches).items()}
    wit = collections.defaultdict(set)
    for (rid, sq), (xv, yv) in lab.items():
        if xv == 1 and yv == 1:
            wit[rid].add(sq)
    for g in jl(genlab):
        idx = {n: i for i, n in enumerate(g["ids"])}
        for b in g["B"]:
            if b.get("y") == 1 and b.get("reason") == "VERIFIED":
                wit[g["root_id"]].add(json.dumps([[idx[o], int(c)] for o, c in b["sequence"]]))
    samp, scor, man = RUN.models(); rows = {r["root_id"]: r for r in RUN.root_rows(None, "EVAL")}
    C = collections.defaultdict(collections.Counter)
    for r in load(evalf.split(",")):
        rid = r["root_id"]
        if rid not in per or per[rid]["K"] not in ("1", "2"):
            continue
        _, dom, _ = RUN.build(rows[rid], samp, man, 0.25)
        W = [[tuple(x) for x in json.loads(s)] for s in wit[rid]]
        W = [w for w in W if len(w) <= 2 and len({o for o, _ in w}) == len(w) and all(a in dom.tier for a in w)]
        for x in r["results"]:
            k = f"{x['arm']}@{x['budget']}"
            if x["seed"] != 0 or k not in ("EXACT4@None", "EXACT6@None", "BEAM_SEEDED4@1024", "BEAM_FULL@1024", "PW_MCTS_SEEDED4@1024", "PW_MCTS_FULL@1024", "RAND_FULL@1024"):
                continue
            o = per[rid][k]["strict"]
            if o == "SUCCESS":
                c = "SUCCESS_OFF_D4" if x["pick_stratum"] != "TOP4_ONLY" else "SUCCESS_IN_D4"
            elif o == "UNKNOWN":
                c = "UNRESOLVED_UNKNOWN"
            else:
                if k.startswith("EXACT"):
                    m = 4 if k.startswith("EXACT4") else 6
                    scored = {tuple(sorted(w)) for w in W if all(dom.rank[a] < m for a in w)}; level = None
                else:
                    scored = {tuple(sorted(tuple(a) for a in A)) for A in x.get("scored_sets") or []}; level = x["final_level"]
                Wc = {tuple(sorted(w)) for w in W}
                pick = tuple(sorted(tuple(a) for a in x["seq"])) if x["seq"] else None
                if pick is not None and pick in Wc:
                    c = "ORDER_SELECTION_FAILURE"
                elif Wc & scored:
                    c = "SCORER_RANKING_FAILURE"
                elif not Wc:
                    c = "UNRESOLVED_NO_KNOWN_WITNESS"
                elif level is None:
                    c = "POOL_MISS (known witness outside the exhaustive pool)"
                elif any(max(dom.tier[a] for a in w) <= level for w in Wc):
                    c = "RETRIEVAL_FAILURE (witness eligible, not scored)"
                else:
                    c = "TIER_LOCKED"
            C[k][c] += 1
            C[k + f"|K{per[rid]['K']}"][c] += 1
    Path(out).write_text(json.dumps({k: dict(v) for k, v in sorted(C.items())}, indent=1)); return C


def latency(files, out):
    """LIVE timing summary per arm @ budget (and wall caps): median / p90 end-to-end and search wall, batches, peak GPU memory."""
    g = collections.defaultdict(lambda: collections.defaultdict(list)); pri = []
    for f in files:
        for r in jl(f):
            pri.append(r["t_prior_s"])
            for x in r["runs"]:
                k = f"{x['arm']}@{x['budget']}" + (f"|wall{x['wall_cap_s']}" if x["wall_cap_s"] else "")
                for f_ in ("live_wall_s", "end_to_end_s", "batches", "scored", "peak_gpu_mb"):
                    g[k][f_].append(x[f_])
                g[k]["stop"].append(x["stop"])
    S = {"roots": len(pri), "cvae_marginal_s": {"median": float(np.median(pri)), "p90": float(np.percentile(pri, 90))}, "arms": {}}
    for k, d in sorted(g.items()):
        S["arms"][k] = {**{f"{f_}_median": round(float(np.median(d[f_])), 5) for f_ in ("live_wall_s", "end_to_end_s", "batches", "scored", "peak_gpu_mb")},
                        "end_to_end_s_p90": round(float(np.percentile(d["end_to_end_s"], 90)), 5), "stops": dict(collections.Counter(d["stop"]))}
    Path(out).write_text(json.dumps(S, indent=1)); return S


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "recall":
        pr, wt, cf = recall(a[1], a[2], a[3].split(","), a[4])
        out = Path(a[5]) if len(a) > 5 else Path.home() / "fds_private"
        (out / "P1_WITNESSES_PRIVATE.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wt))
        (out / "P1_PER_ROOT_PRIVATE.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pr))
        S = recall_summary(pr, wt, cf); (REP / "P1_RECALL.json").write_text(json.dumps(S, indent=1)); print(json.dumps(S, indent=1))
    elif a[0] == "tune":
        tune(a[1].split(","))
    elif a[0] == "model":
        model(a[1].split(","), a[2])
    elif a[0] == "manifest":
        manifest(a[1], a[2], a[3].split(","), a[4])
    elif a[0] == "physical":
        physical(a[1], a[2], a[3].split(","), a[4], a[5])
    elif a[0] == "attribution":
        attribution(a[1], a[2], a[3].split(","), a[4], a[5], a[6])
    elif a[0] == "latency":
        latency(a[1].split(","), a[2])
