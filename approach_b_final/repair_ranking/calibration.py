#!/usr/bin/env python3
"""P2: inference-only rules on the frozen scorer (P2_PREREG.md).  Fit on DEV_CAL known candidates, evaluate DEV_AUDIT once.
    python calibration.py d12      # score EXACT12 pools of every K1/K2 VAL root with s0 (private cache)
    python calibration.py run      # fit, select, evaluate -> P2_RESULTS.json, P2_FROZEN_RULES.json"""
from __future__ import annotations

import collections, json, math, pickle, sys

import numpy as np

import rr
import diagnostics as D

TMAP = {"T4": 0, "T56": 1, "R7_12": 1, "TAIL": 2, "OUTSIDE": 2, "NOOP": 0}          # prereg tier merge: T4 / R5_12 / TAIL
GRID = {"F2": [0.01, 0.1, 1, 10], "F3a": [0, 0.05, 0.1, 0.25, 0.5], "F3b": [0, 0.05, 0.1, 0.25, 0.5], "F4": [0, 0.02, 0.05, 0.1], "F5": [0, 0.5, 1]}


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def arrays(r):
    if "tc" not in r:
        r["tc"] = np.array([TMAP[i["max_tier"]] for i in r["info"]]); r["off"] = np.array([i["off"] for i in r["info"]], float)
        r["prior"] = np.array([i["prior"] for i in r["info"]], float)
        r["lp11"], r["p11"] = r["sc"]["s0"]["lp11"], r["sc"]["s0"]["p11"]
    return r


# ------------------------------------------------------------------------------------------------------------- rules -> utility arrays
def utility(rule, r, prm, fit):
    arrays(r); sc = r["sc"]["s0"]
    if rule in ("F0", "F1", "F4"):
        return sc["lp11"]
    if rule == "F2":
        b, g = fit["F2"][prm]
        return b * logit(sc["p11"]) + g[r["tc"]]
    if rule == "F3a":
        return sc["lp11"] + prm * r["prior"]
    if rule == "F3b":
        return sc["lp11"] - prm * r["off"]
    if rule == "F5":
        P = np.stack([r["sc"][k]["p11"] for k in ("s0", "s1", "s2")])
        return P.mean(0) - prm * P.std(0)
    raise KeyError(rule)


def fit_logistic(roots, C, with_tier=True):
    from sklearn.linear_model import LogisticRegression
    X, y = [], []
    for r in roots:
        arrays(r)
        for i, v in r["known"].items():
            if v["z"] is not None:
                lg = logit(r["sc"]["s0"]["p11"][i])
                X.append([lg] + ([r["tc"][i] == 1, r["tc"][i] == 2] if with_tier else [])); y.append(v["z"])
    m = LogisticRegression(C=C, max_iter=1000).fit(np.array(X, float), np.array(y))
    b = float(m.coef_[0][0]); g = np.array([0.0] + ([float(m.coef_[0][1]), float(m.coef_[0][2])] if with_tier else [0.0, 0.0])) + float(m.intercept_[0])
    return max(b, 1e-6), g


def cv_logloss(roots, C, k=5):
    fams = sorted({r["family"] for r in roots}, key=lambda f: rr.hx("CV|", f))
    tot, n = 0.0, 0
    for j in range(k):
        te = set(fams[j::k])
        b, g = fit_logistic([r for r in roots if r["family"] not in te], C)
        for r in roots:
            if r["family"] in te:
                for i, v in r["known"].items():
                    if v["z"] is not None:
                        p = 1 / (1 + math.exp(-(b * logit(r["sc"]["s0"]["p11"][i]) + g[r["tc"][i]])))
                        p = min(max(p, 1e-6), 1 - 1e-6); tot -= v["z"] * math.log(p) + (1 - v["z"]) * math.log(1 - p); n += 1
    return tot / max(n, 1)


# ------------------------------------------------------------------------------------------------------------- known-candidate metrics
def known_metrics(roots, rule, prm, fit, base=None):
    u = {r["root_id"]: utility(rule, r, prm, fit) for r in roots}
    res = D.ranking(roots, lambda r: u[r["root_id"]])
    per = {p["root_id"]: p for p in res["per_root"]}
    out = {k: res[k] for k in ("roots", "concordance", "top1_known", "top3")}
    pb, pa = fit["F1"]                                                          # high-confidence FP among top-1 picks (calibrated)
    fp = [(1 - r["known"][max((i for i, v in r["known"].items() if v["z"] is not None), key=lambda i: u[r["root_id"]][i])]["z"])
          for r in roots if r["root_id"] in per and 1 / (1 + math.exp(-(pb * logit(r["sc"]["s0"]["p11"][max((i for i, v in r["known"].items() if v["z"] is not None), key=lambda i: u[r["root_id"]][i])]) + pa))) >= 0.9]
    out["top1_FP_rate_at_calibrated_p>=0.9"] = (float(np.mean(fp)), len(fp)) if fp else (None, 0)
    if base is not None:
        common = sorted(set(per) & set(base))
        d = [per[r]["conc"] - base[r]["conc"] for r in common]
        fam = [per[r]["family"] for r in common]
        out["paired_conc_delta_vs_F0"] = D.cboot(d, fam)
        out["paired_top1_delta_vs_F0"] = D.cboot([per[r]["top1"] - base[r]["top1"] for r in common], fam)
    return out, per


# ------------------------------------------------------------------------------------------------------------- end-to-end selection
def select(root, seqs, p11, util, idx, rule=rr.RULE):
    """Frozen gate + raw admission; argmax utility among admitted (ties as search_sets.choose: m, D, signature) -> index or None."""
    if p11[0] >= rule["noop_gate"]:
        return 0
    adm = [i for i in [0] + list(idx) if p11[i] >= rule["eta"]]
    if not adm:
        return None
    return min(adm, key=lambda i: (-round(float(util[i]), 12), len(seqs[i]), root.displacement([tuple(a) for a in seqs[i]]), json.dumps(seqs[i])))


def outcome(rid, seq, lab, K):
    if seq is None:
        return "ABSTAIN"
    if not seq:
        return "NOOP"
    e = lab.get((rid, json.dumps(seq)))
    return rr.z_hist(e["x"], e["y"]) if e else "UNKNOWN"


def end_to_end(roots, d12, rulefn, lab, pools=("d4", "d6", "d12")):
    import search as S
    pub = {r["root_id"]: r for r in rr.public_val()}
    out = {p: [] for p in pools}
    for r in roots:
        R = S.Root(pub[r["root_id"]], "2d")
        for p in pools:
            if p == "d12":
                t = d12.get(r["root_id"])
                if t is None:
                    continue
                seqs, p11, u = t["seqs"], t["p11"], rulefn(t)
                idx = range(1, len(seqs))
            else:
                seqs, p11, u, idx = r["seqs"], r["sc"]["s0"]["p11"], rulefn(r), r[p]
            k = select(R, seqs, p11, u, idx)
            seq = None if k is None else seqs[k]
            out[p].append({"root_id": r["root_id"], "K": r["K"], "family": r["family"], "seq": seq, "outcome": outcome(r["root_id"], seq, lab, r["K"])})
    return out


def summarize(rows, base=None):
    task = [x for x in rows if x["K"] in ("1", "2")]
    c = collections.Counter(x["outcome"] for x in task)
    dec = sum(v for k, v in c.items() if k != "UNKNOWN")
    s = {"K1K2_roots": len(task), "counts": dict(c), "decided": dec, "decided_success": c["SUCCESS"],
         "decided_success_rate": round(c["SUCCESS"] / dec, 4) if dec else None, "unresolved": c["UNKNOWN"],
         "ITT_bounds": [round(c["SUCCESS"] / len(task), 4), round((c["SUCCESS"] + c["UNKNOWN"]) / len(task), 4)] if task else None,
         "K0_NONE_decisions": dict(collections.Counter(f"K{x['K']}:{'REPAIR' if x['seq'] else 'NOOP' if x['seq'] == [] else 'ABSTAIN'}" for x in rows if x["K"] in ("0", "NONE")))}
    if base is not None:
        b = {x["root_id"]: x for x in base}
        s["rescues_vs_F0"] = sum(1 for x in task if x["outcome"] == "SUCCESS" and b[x["root_id"]]["outcome"] in ("FAIL_X", "FAIL_Y", "NOOP", "ABSTAIN"))
        s["harms_vs_F0"] = sum(1 for x in task if x["outcome"] in ("FAIL_X", "FAIL_Y", "NOOP", "ABSTAIN") and b[x["root_id"]]["outcome"] == "SUCCESS")
        s["changed_pick_vs_F0"] = sum(1 for x in task if x["seq"] != b[x["root_id"]]["seq"])
        s["changed_to_unresolved"] = sum(1 for x in task if x["seq"] != b[x["root_id"]]["seq"] and x["outcome"] == "UNKNOWN")
        s["safeguards_identical_to_F0"] = all(x["seq"] == b[x["root_id"]]["seq"] or (x["seq"] and b[x["root_id"]]["seq"]) for x in rows if x["K"] in ("0", "NONE"))
    return s


# ------------------------------------------------------------------------------------------------------------- D12 pools (s0)
def d12():
    """EXACT12 pools (ranks 1..12 per object under the frozen marginal) for every K1/K2 VAL root, scored by s0 (private)."""
    import search as S
    roots = [r for r in D.load() if r["K"] in ("1", "2")]
    pub = {r["root_id"]: r for r in rr.public_val()}
    samp, _, _ = rr.bundle()
    cv = rr.cvae_table(list(pub.values()), samp, "val")
    net = rr.load_net(rr.scorer_path(0))
    out = {}
    for r in roots:
        rk = rr.Ranks(cv[r["root_id"]])
        D12 = collections.defaultdict(list)
        for (o, d), k in sorted(rk.rank.items(), key=lambda kv: kv[1]):
            if k <= 12:
                D12[o].append(d)
        D12 = {o: sorted(v, key=lambda d: rk.rank[(o, d)]) for o, v in D12.items()}
        seqs = [[]] + D.pool(D12, 12)
        res = rr.readout(net, [(pub[r["root_id"]], seqs)])[0]["rows"]
        inf = [rk.seq_info(s) for s in seqs]
        out[r["root_id"]] = {"seqs": seqs, "p11": np.array([x["p11"] for x in res]), "lp11": np.array([x["lp11"] for x in res]),
                             "tc": np.array([TMAP[i["max_tier"]] for i in inf]), "off": np.array([i["off"] for i in inf]), "prior": np.array([i["prior"] for i in inf])}
    (rr.PRIV / "p2_d12_s0.pkl").write_bytes(pickle.dumps(out))
    print(json.dumps({"roots": len(out), "seqs": sum(len(v["seqs"]) for v in out.values())}))


def d12_util(rule, prm, fit):
    def f(t):
        if rule in ("F0", "F1", "F4"):
            return t["lp11"]
        if rule == "F2":
            b, g = fit["F2"][prm]; return b * logit(t["p11"]) + g[t["tc"]]
        if rule == "F3a":
            return t["lp11"] + prm * t["prior"]
        if rule == "F3b":
            return t["lp11"] - prm * t["off"]
        return None
    return f


def f4_rows(roots, d12t, lab, delta, fit, wide="d6"):
    """Anchor = F0 in EXACT4; replace with the best admitted off-D4 candidate of the wider pool iff calibrated gain > delta."""
    import search as S
    pub = {r["root_id"]: r for r in rr.public_val()}
    pb, pa = fit["F1"]
    cal = lambda p: 1 / (1 + math.exp(-(pb * logit(p) + pa)))  # noqa: E731
    rows = []
    for r in roots:
        R = S.Root(pub[r["root_id"]], "2d"); sc = r["sc"]["s0"]
        a = select(R, r["seqs"], sc["p11"], sc["lp11"], r["d4"])
        if wide == "d12":
            t = d12t.get(r["root_id"])
            if t is None:
                continue
            seqs, p11 = t["seqs"], t["p11"]; off = [i for i in range(1, len(seqs)) if t["off"][i] > 0]
        else:
            seqs, p11 = r["seqs"], sc["p11"]; d4 = set(r["d4"]); off = [i for i in r["d6"] if i not in d4]
        pick = None if a is None else r["seqs"][a]
        if a != 0:                                                              # NOOP anchor stays NOOP
            adm = [i for i in off if p11[i] >= rr.RULE["eta"]]
            if adm:
                c = max(adm, key=lambda i: (p11[i], -len(seqs[i])))
                if a is None or cal(p11[c]) - cal(sc["p11"][a]) > delta:
                    pick = seqs[c]
        rows.append({"root_id": r["root_id"], "K": r["K"], "family": r["family"], "seq": pick, "outcome": outcome(r["root_id"], pick, lab, r["K"])})
    return rows


def run():
    roots = D.load()
    d12t = pickle.loads((rr.PRIV / "p2_d12_s0.pkl").read_bytes())
    lab = {k: v for k, v in rr.strict_labels().items()}
    cal = [r for r in roots if r["part"] == "DEV_CAL"]; aud = [r for r in roots if r["part"] == "DEV_AUDIT"]
    calK = [r for r in cal if r["K"] in ("1", "2")]
    for r in roots:
        arrays(r)
    f1 = fit_logistic(calK, 1e6, with_tier=False)
    fit = {"F1": (f1[0], float(f1[1][0])), "F2": {}}
    cvl = {C: cv_logloss(calK, C) for C in GRID["F2"]}
    for C in GRID["F2"]:
        fit["F2"][C] = fit_logistic(calK, C)
    res = {"F2_cv_logloss": cvl}
    base_m, base_per = known_metrics(cal, "F0", None, fit)
    res["DEV_CAL"] = {"F0": base_m}
    choice = {}
    for rule in ("F2", "F3a", "F3b", "F5"):
        grid = [min(cvl, key=cvl.get)] if rule == "F2" else GRID[rule]
        best = None
        for prm in grid:
            m, _ = known_metrics(cal, rule, prm, fit, base_per)
            res["DEV_CAL"][f"{rule}@{prm}"] = m
            if best is None or m["concordance"][0] > best[1]["concordance"][0]:
                best = (prm, m)
        choice[rule] = best[0]
    e2e = {}
    b4 = end_to_end(cal, d12t, lambda t: t["lp11"], lab)
    e2e["F0"] = {p: summarize(v) for p, v in b4.items()}
    for rule in ("F2", "F3a", "F3b"):
        prm = choice[rule]
        rows = end_to_end(cal, d12t, d12_util(rule, prm, fit), lab)
        e2e[f"{rule}@{prm}"] = {p: summarize(v, b4[p]) for p, v in rows.items()}
    f4 = {}
    for wide in ("d6", "d12"):
        for dl in GRID["F4"]:
            rows = f4_rows(cal, d12t, lab, dl, fit, wide)
            f4[f"F4[{wide}]@{dl}"] = summarize(rows, b4["d4"] if wide == "d6" else b4["d4"])
    res["DEV_CAL_end_to_end"] = e2e; res["DEV_CAL_F4"] = f4
    # ---------------- selection (prereg)
    fams = ["F2", "F3a", "F3b", "F5"]
    ranked = sorted(fams, key=lambda f: (-res["DEV_CAL"][f"{f}@{choice[f]}"]["concordance"][0],
                                         res["DEV_CAL"][f"{f}@{choice[f]}"]["top1_FP_rate_at_calibrated_p>=0.9"][0] or 1, fams.index(f)))
    win = ranked[0]; wm = res["DEV_CAL"][f"{win}@{choice[win]}"]
    e4w = e2e.get(f"{win}@{choice[win]}", {}).get("d4")
    gates = {"conc_delta_lower_bound>0": wm["paired_conc_delta_vs_F0"][1] > 0, "top1_not_below_F0": wm["top1_known"][0] >= base_m["top1_known"][0],
             "EXACT4_decided_success_within_3pp": (e4w is None) or (e4w["decided_success_rate"] or 0) >= (e2e["F0"]["d4"]["decided_success_rate"] or 0) - 0.03,
             "safeguards_identical": (e4w is None) or e4w.get("safeguards_identical_to_F0", True)}
    promoted = all(gates.values()) and win != "F5"
    f4best = max(f4, key=lambda k: (f4[k]["decided_success_rate"] or 0, -f4[k]["harms_vs_F0"]))
    f4q = (f4[f4best]["decided_success_rate"] or 0) > (e2e["F0"]["d4"]["decided_success_rate"] or 0) and f4[f4best]["rescues_vs_F0"] > f4[f4best]["harms_vs_F0"]
    res["selection"] = {"family_choices": {k: str(v) for k, v in choice.items()}, "ranked": ranked, "winner": f"{win}@{choice[win]}", "gates": gates,
                        "promoted_utility_rule": promoted, "F4_best": f4best, "F4_qualifies": f4q}
    # ---------------- DEV_AUDIT once (frozen choices)
    a_base, a_per = known_metrics(aud, "F0", None, fit)
    res["DEV_AUDIT"] = {"F0": a_base}
    for f in fams:
        res["DEV_AUDIT"][f"{f}@{choice[f]}"] = known_metrics(aud, f, choice[f], fit, a_per)[0]
    ab4 = end_to_end(aud, d12t, lambda t: t["lp11"], lab)
    res["DEV_AUDIT_end_to_end"] = {"F0": {p: summarize(v) for p, v in ab4.items()}}
    for f in ("F2", "F3a", "F3b"):
        rows = end_to_end(aud, d12t, d12_util(f, choice[f], fit), lab)
        res["DEV_AUDIT_end_to_end"][f"{f}@{choice[f]}"] = {p: summarize(v, ab4[p]) for p, v in rows.items()}
    res["DEV_AUDIT_F4"] = {k: summarize(f4_rows(aud, d12t, lab, float(k.split("@")[1]), fit, k[3:6].strip("[]")), ab4["d4"]) for k in [f4best]}
    am = res["DEV_AUDIT"][f"{win}@{choice[win]}"]
    veto = am["paired_conc_delta_vs_F0"][0] < 0 or am["top1_known"][0] < a_base["top1_known"][0] - 0.03
    res["selection"]["DEV_AUDIT_veto"] = veto
    final = f"{win}@{choice[win]}" if promoted and not veto else (f4best if f4q else None)
    res["selection"]["P2_finalist"] = final
    rr.wjson(rr.REP / "P2_RESULTS.json", res)
    rr.wjson(rr.REP / "P2_FROZEN_RULES.json", {"F1_platt": list(map(float, fit["F1"])), "F2": {str(C): [float(b), list(map(float, g))] for C, (b, g) in fit["F2"].items()},
                                               "choices": {k: str(v) for k, v in choice.items()}, "finalist": final, "tier_merge": "T4 / R5_12 (T56+R7_12) / TAIL"})
    print(json.dumps(res["selection"], indent=1))


if __name__ == "__main__":
    {"d12": d12, "run": run}[sys.argv[1]]()
