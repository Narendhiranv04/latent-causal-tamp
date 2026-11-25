#!/usr/bin/env python3
"""P1: diagnose the frozen X/Y scorer on exact-contract labelled candidates (VAL, evaluator side) and its own TRAIN observations.
Candidate tables (private, with labels) are cached in ~/xyrr_private; every metric is root-macro with family-cluster bootstrap where stated.
    python diagnostics.py build     # candidate tables + frozen readouts (s0, s1, s2) + D4 / D6 pools
    python diagnostics.py report    # P1_*.json"""
from __future__ import annotations

import collections, itertools, json, math, pickle, sys

import numpy as np

import rr

sys.path.insert(0, str(rr.ABF / "full_domain_sets"))
TIERS = ["T4", "T56", "R7_12", "TAIL"]


# ------------------------------------------------------------------------------------------------------------- pools (frozen grammar)
def pool(D6, m, L=None):
    """All K<=2 ordered sequences over the archived top-m destinations (construct.assignments: distinct objects, distinct destinations),
    singles first, then both orders of every pair; deterministic order."""
    D = {int(o): [int(d) for d in v[:m]] for o, v in D6.items() if v[:m]}
    ob = sorted(D)
    out = [[[o, d]] for o in ob for d in D[o]]
    for o1, o2 in itertools.combinations(ob, 2):
        for d1 in D[o1]:
            for d2 in D[o2]:
                if d1 != d2:
                    out += [[[o1, d1], [o2, d2]], [[o2, d2], [o1, d1]]]
    return out


def choose(root, cands, rule=rr.RULE):
    """Frozen selection (search_sets.choose == xy.choose): cands = [{'seq', 'p11'}] incl. the no-op [] first -> chosen cand or None."""
    import fsearch as FS
    rows = [{"seq": c["seq"], "p11": c["p11"], "m": len(c["seq"]), "D": root.displacement([tuple(a) for a in c["seq"]])} for c in cands]
    k = FS.choose(rows, rule)
    return None if k is None else next(c for c, r in zip(cands, rows) if r is k)


def decision(c):
    return "ABSTAIN" if c is None else "NOOP" if not c["seq"] else "REPAIR"


# ------------------------------------------------------------------------------------------------------------- tables
def val_table(nets):
    """Every VAL root: its exact-contract labelled K<=2 legal sequences + D4/D6 pools, scored by every net (frozen s0/s1/s2 or new)."""
    import search as S
    pub = {r["root_id"]: r for r in rr.public_val()}
    vm, lab = rr.val_meta(), rr.strict_labels()
    samp, _, _ = rr.bundle()
    cv = rr.cvae_table(list(pub.values()), samp, "val")
    known = collections.defaultdict(dict)
    for (rid, sq), e in lab.items():
        if rid in pub and len(json.loads(sq)) <= 2:
            known[rid][sq] = e
    roots = []
    for rid, row in sorted(pub.items()):
        R = S.Root(row, "2d"); rk = rr.Ranks(cv[rid])
        d4, d6 = pool(cv[rid]["D6"], 4), pool(cv[rid]["D6"], 6)
        kn = {sq: e for sq, e in known[rid].items() if rr.legal_k2(row, json.loads(sq))}
        seqs, idx = [[]], {"[]": 0}
        for s in d6 + [json.loads(sq) for sq in sorted(kn)]:
            k = json.dumps(s)
            if k not in idx:
                idx[k] = len(seqs); seqs.append(s)
        roots.append({"root_id": rid, **vm[rid], "seqs": seqs, "d4": [idx[json.dumps(s)] for s in d4], "d6": [idx[json.dumps(s)] for s in d6],
                      "known": {idx[sq]: {"x": e["x"], "y": e["y"], "xs": e["xs"], "ys": e["ys"], "z": rr.z_logic(e["x"], e["y"]),
                                          "hist": rr.z_hist(e["x"], e["y"]), "src": sorted(set(e["src"]))} for sq, e in kn.items()},
                      "info": [rk.seq_info(s) for s in seqs], "D": [R.displacement([tuple(a) for a in s]) for s in seqs]})
    score_into(roots, pub, nets)
    return roots


def score_into(roots, pub, nets):
    """Attach per-net readouts: r['sc'][name] = {'p11','lp11','py','px1','px0','px','b','a','w'} arrays aligned with r['seqs']."""
    for name, net in nets.items():
        res = rr.readout(net, [(pub[r["root_id"]], r["seqs"]) for r in roots])
        for r, o in zip(roots, res):
            rows = o["rows"]
            r.setdefault("sc", {})[name] = {k: np.array([x.get(k, np.nan) for x in rows], float) for k in ("p11", "lp11", "py", "px1", "px0", "px", "b", "a", "w")}


def train_table(net):
    """Original TRAIN observations (finalized snapshot labels) scored in-sample by the frozen scorer: one row per X node (len <= 3)."""
    import search as S
    samp, _, _ = rr.bundle()
    rows = rr.snapshot_rows("train")
    cv = rr.cvae_table(rows, samp, "train")
    jobs, meta = [], []
    for r in rows:
        Y = {json.dumps(sorted([int(i), int(c)] for i, c in y["edit"])): y["y"] for y in r["labels"]["Y"]}
        seqs = [[[int(i), int(c)] for i, c in q["seq"]] for q in r["labels"]["X"]]
        if not seqs:
            continue
        rk = rr.Ranks(cv[r["root_id"]])
        jobs.append((r, seqs))
        meta.append([{"root_id": r["root_id"], "K": r["K_legacy"], "family": r["parent_family_id"], "seq": s, "kind": q["kind"], "x": q["x"],
                      "y": Y.get(json.dumps(sorted(s))), **rk.seq_info(s)} for s, q in zip(seqs, r["labels"]["X"])])
    out = []
    for m, o in zip(meta, rr.readout(net, jobs)):
        for c, x in zip(m, o["rows"]):
            c.update({k: x[k] for k in ("p11", "py", "px1", "px0", "px")}); c["z"] = rr.z_logic(c["x"], c["y"])
            out.append(c)
    return out


# ------------------------------------------------------------------------------------------------------------- metrics
def calib(y, p):
    import xy as XY
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    if len(y) == 0:
        return {"n": 0}
    lg = np.log(p / (1 - p))
    slope = icpt = None
    if 0 < y.sum() < len(y):
        from sklearn.linear_model import LogisticRegression
        m = LogisticRegression(C=1e6).fit(lg[:, None], y)
        slope, icpt = float(m.coef_[0][0]), float(m.intercept_[0])
    hi = {f"FP_rate_at_p>={t}": (float((y[p >= t] == 0).mean()) if (p >= t).any() else None) for t in (0.8, 0.9, 0.95)}
    hin = {f"n_at_p>={t}": int((p >= t).sum()) for t in (0.8, 0.9, 0.95)}
    return {"n": int(len(y)), "pos": int(y.sum()), "brier": float(((p - y) ** 2).mean()), "logloss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
            "auroc": XY.auroc(y, p), "auprc": XY.auprc(y, p), "ece10": XY.ece(y, p), "slope": slope, "intercept": icpt, **hi, **hin}


def cboot(vals, clus, n=4000, seed=0):
    """Family-cluster bootstrap of a root-macro mean -> [mean, lo, hi]."""
    if not len(vals):
        return [None, None, None]
    g = collections.defaultdict(list)
    for v, c in zip(vals, clus):
        g[c].append(v)
    keys = list(g); arr = [np.array(g[k]) for k in keys]
    rng = np.random.default_rng(seed); bs = []
    for _ in range(n):
        pick = rng.integers(0, len(keys), len(keys))
        s = np.concatenate([arr[i] for i in pick]); bs.append(s.mean())
    return [round(float(np.mean(vals)), 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]


def pair_kind(a, b):
    sa, sb = {tuple(x) for x in a}, {tuple(x) for x in b}
    if sa == sb:
        return "same_set_other_order"
    oa, ob = {x[0] for x in a}, {x[0] for x in b}
    if sa < sb or sb < sa:
        return "omission_or_addition"
    if oa == ob:
        return "same_objects_other_destinations"
    if not oa & ob:
        return "disjoint_objects"
    return "mixed"


def ranking(roots, score, which="known", Ks=("1", "2")):
    """Within-root ranking over decided labelled candidates (Z logical): concordance Z+ vs Z- (ties 0.5), known-candidate top-1, best-positive
    percentile, top-3/5 recall; pair concordance by pair kind and by (pos tier, neg tier).  score(r) -> array aligned with r['seqs']."""
    per, kinds, tiers = [], collections.defaultdict(list), collections.defaultdict(list)
    for r in roots:
        if r["K"] not in Ks:
            continue
        kn = {i: v for i, v in r["known"].items() if v["z"] is not None}
        P = [i for i, v in kn.items() if v["z"] == 1]; N = [i for i, v in kn.items() if v["z"] == 0]
        if not P or not N:
            continue
        s = score(r)
        conc = [1.0 if s[p] > s[n] else 0.5 if s[p] == s[n] else 0.0 for p in P for n in N]
        order = sorted(kn, key=lambda i: (-s[i], i))
        top = order[0]
        bestpos = min(order.index(p) for p in P)
        per.append({"root_id": r["root_id"], "family": r["family"], "K": r["K"], "conc": float(np.mean(conc)), "top1": float(kn[top]["z"] == 1),
                    "top3": float(bestpos < 3), "top5": float(bestpos < 5), "best_pos_pct": bestpos / max(1, len(kn) - 1), "n_known": len(kn), "n_pos": len(P)})
        for p in P:
            for n in N:
                c = 1.0 if s[p] > s[n] else 0.5 if s[p] == s[n] else 0.0
                kinds[pair_kind(r["seqs"][p], r["seqs"][n])].append((r["root_id"], c))
                tiers[f"pos_{r['info'][p]['max_tier']}|neg_{r['info'][n]['max_tier']}"].append((r["root_id"], c))
    fam = [p["family"] for p in per]

    def macro(lst):
        g = collections.defaultdict(list)
        for rid, c in lst:
            g[rid].append(c)
        return {"pairs": len(lst), "roots": len(g), "root_macro_conc": round(float(np.mean([np.mean(v) for v in g.values()])), 4) if g else None}
    return {"roots": len(per), "concordance": cboot([p["conc"] for p in per], fam), "top1_known": cboot([p["top1"] for p in per], fam),
            "top3": cboot([p["top3"] for p in per], fam), "top5": cboot([p["top5"] for p in per], fam),
            "best_pos_percentile_mean": round(float(np.mean([p["best_pos_pct"] for p in per])), 4) if per else None,
            "by_pair_kind": {k: macro(v) for k, v in sorted(kinds.items())}, "by_tier_pair": {k: macro(v) for k, v in sorted(tiers.items()) if len(v) >= 20},
            "per_root": per}


def factor_calibration(roots, name, part=None, Ks=None):
    """pY vs Y (unique endpoints), marginal pX vs X, pX1 vs X | Y=1, pX0 vs X | Y=0, p11 vs Z, by max tier."""
    out, ep = {}, {}
    rows = []
    for r in roots:
        if (part and r["part"] != part) or (Ks and r["K"] not in Ks):
            continue
        sc = r["sc"][name]
        for i, v in r["known"].items():
            rows.append((r, i, v, sc))
            if v["y"] is not None:
                ep[(r["root_id"], json.dumps(sorted(r["seqs"][i])))] = (v["y"], sc["py"][i])
    out["pY_vs_Y_unique_endpoints"] = calib([a for a, _ in ep.values()], [b for _, b in ep.values()])
    out["pX_marginal_vs_X"] = calib([v["x"] for r, i, v, sc in rows if v["x"] is not None], [sc["px"][i] for r, i, v, sc in rows if v["x"] is not None])
    out["pX1_vs_X_given_Y=1"] = calib([v["x"] for r, i, v, sc in rows if v["x"] is not None and v["y"] == 1], [sc["px1"][i] for r, i, v, sc in rows if v["x"] is not None and v["y"] == 1])
    out["pX0_vs_X_given_Y=0"] = calib([v["x"] for r, i, v, sc in rows if v["x"] is not None and v["y"] == 0], [sc["px0"][i] for r, i, v, sc in rows if v["x"] is not None and v["y"] == 0])
    out["p11_vs_Z"] = calib([v["z"] for r, i, v, sc in rows if v["z"] is not None], [sc["p11"][i] for r, i, v, sc in rows if v["z"] is not None])
    out["p11_vs_Z_by_max_tier"] = {t: calib([v["z"] for r, i, v, sc in rows if v["z"] is not None and r["info"][i]["max_tier"] == t],
                                            [sc["p11"][i] for r, i, v, sc in rows if v["z"] is not None and r["info"][i]["max_tier"] == t]) for t in TIERS}
    out["p11_vs_Z_by_len"] = {L: calib([v["z"] for r, i, v, sc in rows if v["z"] is not None and len(r["seqs"][i]) == L],
                                       [sc["p11"][i] for r, i, v, sc in rows if v["z"] is not None and len(r["seqs"][i]) == L]) for L in (1, 2)}
    return out


def train_calibration(tr):
    out = {"note": "IN-SAMPLE (the frozen scorer was trained on these labels)"}
    L2 = [c for c in tr if len(c["seq"]) <= 2]
    out["p11_vs_Z_len<=2"] = calib([c["z"] for c in L2 if c["z"] is not None], [c["p11"] for c in L2 if c["z"] is not None])
    out["pX1_vs_X_given_Y=1_len<=2"] = calib([c["x"] for c in L2 if c["y"] == 1], [c["px1"] for c in L2 if c["y"] == 1])
    out["p11_vs_Z_by_max_tier_len<=2"] = {t: calib([c["z"] for c in L2 if c["z"] is not None and c["max_tier"] == t], [c["p11"] for c in L2 if c["z"] is not None and c["max_tier"] == t]) for t in TIERS}
    return out


def high_conf_errors(roots, name, t=0.8, Ks=("1", "2")):
    c = collections.Counter(); py, px1 = [], []
    for r in roots:
        if r["K"] not in Ks:
            continue
        sc = r["sc"][name]
        for i, v in r["known"].items():
            if v["z"] == 0 and sc["p11"][i] >= t:
                k = "FAIL_Y (y=0)" if v["y"] == 0 else "FAIL_X (x=0, y=1)" if v["y"] == 1 else "x=0, y unresolved"
                c[k] += 1; c[f"tier_{r['info'][i]['max_tier']}"] += 1; c[f"len{len(r['seqs'][i])}"] += 1
                py.append(sc["py"][i]); px1.append(sc["px1"][i])
    return {"threshold": t, "counts": dict(c), "median_pY": float(np.median(py)) if py else None, "median_pX1": float(np.median(px1)) if px1 else None}


def coverage(roots, Ks=("1", "2")):
    """Known verified K<=2 successes vs D4 / D6 pools (whole-set), plus tier mix of decided positives vs negatives."""
    c = collections.Counter(); tp, tn = collections.Counter(), collections.Counter()
    for r in roots:
        if r["K"] not in Ks:
            continue
        d4, d6 = set(r["d4"]), set(r["d6"])
        P = [i for i, v in r["known"].items() if v["z"] == 1]
        c["roots"] += 1; c["roots_with_known_success"] += bool(P)
        c["roots_with_known_success_in_D4"] += any(i in d4 for i in P); c["roots_with_known_success_in_D6"] += any(i in d6 for i in P)
        c["roots_with_ONLY_off_D4_known_success"] += bool(P) and not any(i in d4 for i in P)
        for i, v in r["known"].items():
            if v["z"] == 1:
                tp[r["info"][i]["max_tier"]] += 1
            elif v["z"] == 0:
                tn[r["info"][i]["max_tier"]] += 1
    return {**dict(c), "decided_positive_by_max_tier": dict(tp), "decided_negative_by_max_tier": dict(tn),
            "positive_rate_by_max_tier": {t: round(tp[t] / max(1, tp[t] + tn[t]), 4) for t in TIERS},
            "note": "lower bounds: labelled candidates are those some earlier method selected; absence of a known witness is not a pool miss"}


def decomposition(roots, name="s0"):
    """Re-run the frozen EXACT4 / EXACT6 decision with this scorer and classify every K1/K2 root (mutually exclusive primary category)."""
    import search as S
    pub = {r["root_id"]: r for r in rr.public_val()}
    out = {}
    for arm, key in (("EXACT4", "d4"), ("EXACT6", "d6")):
        cat = collections.Counter(); rows = []
        for r in roots:
            if r["K"] not in ("1", "2"):
                continue
            R = S.Root(pub[r["root_id"]], "2d"); sc = r["sc"][name]
            cand = [{"seq": [], "p11": float(sc["p11"][0]), "i": 0}] + [{"seq": r["seqs"][i], "p11": float(sc["p11"][i]), "i": i} for i in r[key]]
            ch = choose(R, cand)
            dec = decision(ch)
            kn = r["known"]; P = [i for i, v in kn.items() if v["z"] == 1]
            inpool = set(r[key])
            Pin = [i for i in P if i in inpool]
            if dec == "REPAIR":
                v = kn.get(ch["i"])
                z = None if v is None else v["z"]
                if z == 1:
                    c = "SUCCESS"
                elif z is None:
                    c = "UNRESOLVED (no decided label for the pick)"
                else:
                    same = [i for i in Pin if sorted(r["seqs"][i]) == sorted(ch["seq"])]
                    c = "ORDER_FAILURE (other order of the same set verified)" if same else "RANKING_FAILURE (verified success scored lower)" if Pin else \
                        "RETRIEVAL_OR_POOL_MISS (known success only outside the pool)" if P else "FAILURE_NO_KNOWN_WITNESS"
                    c += f"|{'FAIL_Y' if v['y'] == 0 else 'FAIL_X'}"
            else:
                c = f"{dec}_WITH_SCORED_KNOWN_SUCCESS (gate / admission)" if Pin else f"{dec}_ONLY_OFFPOOL_SUCCESS" if P else f"{dec}_NO_KNOWN_WITNESS"
            cat[c] += 1
            rows.append({"root_id": r["root_id"], "K": r["K"], "decision": dec, "seq": ch["seq"] if ch else None, "cat": c,
                         "p11": ch["p11"] if ch else None, "p_noop": float(sc["p11"][0])})
        out[arm] = {"categories": dict(cat), "per_root": rows}
    return out


def build():
    nets = {f"s{k}": rr.load_net(rr.scorer_path(k)) for k in (0, 1, 2)}
    roots = val_table(nets)
    (rr.PRIV / "p1_val_table.pkl").write_bytes(pickle.dumps(roots))
    tr = train_table(nets["s0"])
    (rr.PRIV / "p1_train_table.pkl").write_bytes(pickle.dumps(tr))
    print(json.dumps({"val_roots": len(roots), "val_seqs": sum(len(r["seqs"]) for r in roots), "known": sum(len(r["known"]) for r in roots), "train_rows": len(tr)}))


def load():
    return pickle.loads((rr.PRIV / "p1_val_table.pkl").read_bytes())


def report():
    roots = load(); tr = pickle.loads((rr.PRIV / "p1_train_table.pkl").read_bytes())
    s0 = lambda r: r["sc"]["s0"]["p11"]  # noqa: E731
    prior = lambda r: np.array([i["prior"] if s else -1e9 for i, s in zip(r["info"], r["seqs"])])  # noqa: E731
    rand = lambda r: np.random.default_rng(rr.hx("RAND|", r["root_id"]) % 2 ** 32).random(len(r["seqs"]))  # noqa: E731
    cal = {"VAL_all_K": factor_calibration(roots, "s0"), "VAL_K1K2": factor_calibration(roots, "s0", Ks=("1", "2")),
           "DEV_CAL_K1K2": factor_calibration(roots, "s0", "DEV_CAL", ("1", "2")), "DEV_AUDIT_K1K2": factor_calibration(roots, "s0", "DEV_AUDIT", ("1", "2")),
           "TRAIN_in_sample": train_calibration(tr)}
    rk = {}
    for part in (None, "DEV_CAL", "DEV_AUDIT"):
        R = [r for r in roots if part is None or r["part"] == part]
        tag = part or "VAL"
        rk[tag] = {"frozen_p11_s0": ranking(R, s0), "cvae_prior_only_control": ranking(R, prior), "random_control": ranking(R, rand),
                   "pY_only": ranking(R, lambda r: r["sc"]["s0"]["py"]), "pX1_only": ranking(R, lambda r: r["sc"]["s0"]["px1"])}
    for d in rk.values():
        for v in d.values():
            v.pop("per_root", None) if not (v is d.get("frozen_p11_s0")) else None
    fail = {"high_conf_false_positives_p11>=0.8_VAL_K1K2": high_conf_errors(roots, "s0"), "coverage_VAL_K1K2": coverage(roots), "decomposition": decomposition(roots)}
    per = {a: v.pop("per_root") for a, v in fail["decomposition"].items()}
    (rr.PRIV / "p1_decomposition_per_root.json").write_text(json.dumps(per))
    rr.wjson(rr.REP / "P1_CALIBRATION.json", cal)
    rr.wjson(rr.REP / "P1_RANKING.json", {k: {kk: {x: y for x, y in vv.items() if x != "per_root"} for kk, vv in v.items()} for k, v in rk.items()})
    rr.wjson(rr.REP / "P1_FAILURES.json", fail)
    rr.wjson(rr.REP / "P1_TRAIN_SUPPORT.json", train_support(roots, tr))
    print(json.dumps({k: v["frozen_p11_s0"]["concordance"] for k, v in rk.items()}))


def train_support(roots, tr):
    """Decided positive / negative counts by max tier and pair kind: TRAIN (finalized labels) vs VAL caches (exact contract)."""
    t = collections.Counter((c["max_tier"], c["z"]) for c in tr if len(c["seq"]) <= 2 and c["z"] is not None)
    v = collections.Counter((r["info"][i]["max_tier"], k["z"]) for r in roots for i, k in r["known"].items() if k["z"] is not None)
    return {"TRAIN_len<=2_decided_by_tier": {f"{a}|z{b}": n for (a, b), n in sorted(t.items())},
            "VAL_cache_decided_by_tier": {f"{a}|z{b}": n for (a, b), n in sorted(v.items())},
            "TRAIN_roots_with_pairs_len<=2": len({c["root_id"] for c in tr if c["z"] == 1 and len(c["seq"]) <= 2} & {c["root_id"] for c in tr if c["z"] == 0 and len(c["seq"]) <= 2})}


if __name__ == "__main__":
    {"build": build, "report": report}[sys.argv[1]]()
