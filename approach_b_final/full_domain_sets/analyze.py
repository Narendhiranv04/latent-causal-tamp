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


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "recall":
        pr, wt, cf = recall(a[1], a[2], a[3].split(","), a[4])
        out = Path(a[5]) if len(a) > 5 else Path.home() / "fds_private"
        (out / "P1_WITNESSES_PRIVATE.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wt))
        (out / "P1_PER_ROOT_PRIVATE.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pr))
        S = recall_summary(pr, wt, cf); (REP / "P1_RECALL.json").write_text(json.dumps(S, indent=1)); print(json.dumps(S, indent=1))
