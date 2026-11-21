#!/usr/bin/env python3
"""Offline decisions from the multipass scores (PREREG_P1_P4) and their physical evaluation with the (copied + extended) verifier cache.
    python rules.py parity SPLIT DOM            registered rule reproduces every sealed FULL/E/DIRECT decision (gate before any use)
    python rules.py tune DOM                    VAL-only threshold tuning per model checkpoint -> TUNED_RULES_DOM.json (write-once)
    python rules.py evaluate SPLIT DOM          all variants x {registered, tuned, fixed-gating, forced} -> EVAL_SPLIT_DOM.json"""
import collections, json, sys

import numpy as np

import vk
import queries as QU

REG = (0.5, 0.3)
GATES, ETAS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9], [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
B_MODELS = [f"{m}_s{s}" for m in ("FULL", "E", "DIRECT") for s in (0, 1, 2)]


def ctx(split, dom):
    import benchmark as BM
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_{split}_{dom}.jsonl")}
    lab, outcome = BM.cache_labels(QU.CACHE, dom)
    return QU.mp(split, dom), priv, lab, outcome


def decide(r, vn, gate, eta, noop_net=None):
    """-> None (ABSTAIN) | [] (NOOP) | seq.  p_noop from the variant's network (knockout / X / Y variants keep the D network's no-op)."""
    pn = r["p_noop"][noop_net or vn.split(":")[0]]
    v = r["variants"].get(vn)
    if pn >= gate:
        return []
    pb = v["p"] if v else -1.0
    if pn >= eta and (pb < eta or round(-np.log(max(pn, 1e-12)), 12) <= round(-np.log(max(pb, 1e-12)), 12)):     # NOOP wins ties (|r| = 0)
        return []
    return v["seq"] if v and pb >= eta else None


def scores(sel, priv, lab, outcome):
    """sel {rid: decision} -> per-root (task, noop, abstain) indicators with the frozen masks; UNKNOWN task outcomes counted separately."""
    out = {}
    for rid, d in sel.items():
        m = priv[rid]["masks"]
        o = outcome(d, lab, rid)
        out[rid] = {"o": o, "task": None if not m.get("eval_task") or o == "UNKNOWN" else float(o == "SUCCESS"), "unknown": m.get("eval_task") and o == "UNKNOWN",
                    "noop": None if not m.get("eval_noop") else float(o == "NOOP"), "abstain": None if not m.get("eval_abstain") else float(o == "ABSTAIN")}
    return out


def rates(S):
    g = lambda k: [v[k] for v in S.values() if v[k] is not None]  # noqa: E731
    t, n, a = g("task"), g("noop"), g("abstain")
    return {"task": float(np.mean(t)) if t else None, "noop": float(np.mean(n)) if n else None, "abstain": float(np.mean(a)) if a else None,
            "n_task": len(t), "unknown_task": sum(bool(v["unknown"]) for v in S.values()), "obj": float(np.mean([np.mean(x) for x in (t, n, a) if x]))}


def parity(split, dom):
    M, priv, lab, outcome = ctx(split, dom)
    res = {}
    for net in B_MODELS:
        P = {r["root_id"]: r for r in vk.jl(vk.K3A / "runs/predictions" / net / f"{split}_{dom}.jsonl")}
        bad = []
        for rid, r in M.items():
            d = decide(r, f"{net}:p11", *REG)
            ref = None if P[rid]["decision"] == "ABSTAIN" else [] if P[rid]["decision"] == "NOOP" else [[x["object_index"], x["destination_cell"]] for x in P[rid]["moves"]]
            if d != ref:
                bad.append(rid)
        res[net] = {"n": len(M), "mismatch": len(bad), "examples": bad[:5]}
    vk.wjson(vk.OUT / "rules" / f"PARITY_{split}_{dom}.json", res)
    print(json.dumps(res))
    return res


def tune(dom):
    fo = vk.OUT / "rules" / f"TUNED_RULES_{dom}.json"
    assert not fo.exists(), "tuned rules already registered (write-once)"
    M, priv, lab, outcome = ctx("val", dom)
    out = {}
    for vn in [f"{m}:p11" for m in B_MODELS] + [f"FULL_s{s}:p11_w0" for s in (0, 1, 2)]:
        grid = []
        for g in GATES:
            for e in ETAS:
                R = rates(scores({rid: decide(r, vn, g, e) for rid, r in M.items()}, priv, lab, outcome))
                assert R["unknown_task"] == 0, (vn, g, e, R["unknown_task"])
                grid.append((round(R["obj"], 12), -(abs(g - REG[0]) + abs(e - REG[1])), -g, -e, {"gate": g, "eta": e, **R}))
        grid.sort(key=lambda t: t[:4], reverse=True)
        reg = next(t[4] for t in grid if t[4]["gate"] == REG[0] and t[4]["eta"] == REG[1])
        out[vn] = {"tuned": grid[0][4], "registered": reg, "grid": [t[4] for t in grid]}
    out["_meta"] = {"objective": "mean(task, noop, abstain) on VAL", "multipass_sha256": {p.name: vk.sha(p) for p in sorted((vk.OUT / "multipass").glob(f"val_{dom}*.jsonl"))}}
    vk.wjson(fo, out)
    print(json.dumps({k: (v["tuned"]["gate"], v["tuned"]["eta"], round(v["tuned"]["obj"], 4), round(v["registered"]["obj"], 4)) for k, v in out.items() if k != "_meta"}, indent=1))


def evaluate(split, dom):
    M, priv, lab, outcome = ctx(split, dom)
    T = json.loads((vk.OUT / "rules" / f"TUNED_RULES_{dom}.json").read_text())
    lin = vk.lineage(dom, split)
    fam = {r["root_id"]: r["parent_family_id"] for r in vk.rows(dom, split)}
    K = {rid: priv[rid]["K"] for rid in M}
    pol = {}
    for vn in sorted({v for r in M.values() for v in r["variants"]}):
        net = vn.split(":")[0]
        pol[f"{vn}|forced"] = {rid: (r["variants"][vn]["seq"] if vn in r["variants"] else None) for rid, r in M.items()}
        pol[f"{vn}|registered"] = {rid: decide(r, vn, *REG) for rid, r in M.items()}
        if vn in T:
            t = T[vn]["tuned"]
            pol[f"{vn}|tuned"] = {rid: decide(r, vn, t["gate"], t["eta"]) for rid, r in M.items()}
        if net.startswith("FULL"):                                          # fixed gating: decision type of FULL_s* (registered rule)
            base = {rid: decide(r, f"{net}:p11", *REG) for rid, r in M.items()}
            pol[f"{vn}|fixedgate"] = {rid: (d if d in (None, []) else M[rid]["variants"][vn]["seq"]) for rid, d in base.items()}
    S = {k: scores(v, priv, lab, outcome) for k, v in pol.items()}
    out = {"policies": {}, "paired": {}}
    for k, s in S.items():
        R = rates(s)
        R["by_K"] = {kk: float(np.mean([v["task"] for rid, v in s.items() if K[rid] == kk and v["task"] is not None])) for kk in ("1", "2", "3")}
        R["outcomes_task_roots"] = dict(collections.Counter(v["o"] for rid, v in s.items() if priv[rid]["masks"].get("eval_task")))
        out["policies"][k] = R

    def paired(a_keys, b_keys, metric):
        rids = [rid for rid in M if all(S[k][rid][metric] is not None for k in a_keys + b_keys)]
        d = [np.mean([S[k][rid][metric] for k in a_keys]) - np.mean([S[k][rid][metric] for k in b_keys]) for rid in rids]
        res = {"n": len(rids), "diff": vk.cluster_boot(d, [lin[r] for r in rids]), "diff_family": vk.cluster_boot(d, [fam[r] for r in rids])}
        if metric == "task":
            res["by_K"] = {kk: vk.cluster_boot([x for x, r in zip(d, rids) if K[r] == kk], [lin[r] for r in rids if K[r] == kk]) for kk in ("1", "2", "3")}
        return res
    sd = lambda f, v, p: [f"{f}_s{s}:{v}|{p}" for s in (0, 1, 2)]  # noqa: E731
    for metric in ("task", "noop", "abstain"):
        for name, a, b in (("A5 knockout - D (registered)", sd("FULL", "p11_w0", "registered"), sd("FULL", "p11", "registered")),
                           ("A5 knockout - D (forced)", sd("FULL", "p11_w0", "forced"), sd("FULL", "p11", "forced")),
                           ("A5 knockout - D (fixed gating)", sd("FULL", "p11_w0", "fixedgate"), sd("FULL", "p11", "fixedgate")),
                           ("B DIRECT - D registered", sd("DIRECT", "p11", "registered"), sd("FULL", "p11", "registered")),
                           ("B DIRECT - D tuned", sd("DIRECT", "p11", "tuned"), sd("FULL", "p11", "tuned")),
                           ("B DIRECT - D forced (threshold-free)", sd("DIRECT", "p11", "forced"), sd("FULL", "p11", "forced")),
                           ("B E - D registered", sd("E", "p11", "registered"), sd("FULL", "p11", "registered")),
                           ("B E - D tuned", sd("E", "p11", "tuned"), sd("FULL", "p11", "tuned")),
                           ("B E - D forced", sd("E", "p11", "forced"), sd("FULL", "p11", "forced")),
                           ("D tuned - D registered", sd("FULL", "p11", "tuned"), sd("FULL", "p11", "registered")),
                           ("DIRECT tuned - DIRECT registered", sd("DIRECT", "p11", "tuned"), sd("DIRECT", "p11", "registered")),
                           ("D Y_only - p11 (forced)", sd("FULL", "Y_only", "forced"), sd("FULL", "p11", "forced")),
                           ("D X_marg - p11 (forced)", sd("FULL", "X_marg", "forced"), sd("FULL", "p11", "forced")),
                           ("D X|Y1 - p11 (forced)", sd("FULL", "X_given_Y1", "forced"), sd("FULL", "p11", "forced")),
                           ("D Y_only - p11 (fixed gating)", sd("FULL", "Y_only", "fixedgate"), sd("FULL", "p11", "fixedgate")),
                           ("D X_marg - p11 (fixed gating)", sd("FULL", "X_marg", "fixedgate"), sd("FULL", "p11", "fixedgate")),
                           ("D X|Y1 - p11 (fixed gating)", sd("FULL", "X_given_Y1", "fixedgate"), sd("FULL", "p11", "fixedgate"))):
            if metric != "task" and ("forced" in name or "fixed" in name):
                continue
            if all(k in S for k in a + b):
                out["paired"][f"{name} | {metric}"] = paired(a, b, metric)
    vk.wjson(vk.OUT / "rules" / f"EVAL_{split}_{dom}.json", out)
    for k, v in out["paired"].items():
        print(k, v["n"], v["diff"], v.get("by_K"))



def budget_eval(dom):
    """E5: task success of the registered rule when the argmax is taken over B label-blind random candidates (VAL), vs the full pool."""
    import benchmark as BM
    priv = {e["root_id"]: e for e in vk.jl(vk.K3A / "runs/public" / f"private_val_{dom}.jsonl")}
    lab, outcome = BM.cache_labels(QU.CACHE, dom)
    Bf = {r["root_id"]: r for p in sorted((vk.OUT / "budget").glob(f"val_{dom}*.jsonl")) for r in vk.jl(p)}
    M = QU.mp("val", dom)
    lin = vk.lineage(dom, "val")
    out, per = {}, {}
    for B in ("1", "16", "256", "4096", "all"):
        sel = {}
        for rid, r in Bf.items():
            if B == "all":
                sel[rid] = decide(M[rid], "FULL_s0:p11", *REG)
            else:
                v = r["B"].get(B) or (r["B"][max(r["B"], key=int)] if r["B"] else None)
                rec = {"p_noop": {"X": r["p_noop"]}, "variants": {"X:p11": {"seq": v["seq"], "p": v["p"]}} if v else {}}
                sel[rid] = decide(rec, "X:p11", *REG)
        S = scores(sel, priv, lab, outcome)
        per[B] = S
        out[B] = {**rates(S), "ci_task": vk.cluster_boot([v["task"] for v in S.values() if v["task"] is not None], [lin[r] for r, v in S.items() if v["task"] is not None])}
    for B in ("1", "16", "256", "4096"):
        rids = [r for r in per[B] if per[B][r]["task"] is not None and per["all"][r]["task"] is not None]
        out[B]["paired_vs_all_task"] = vk.cluster_boot([per[B][r]["task"] - per["all"][r]["task"] for r in rids], [lin[r] for r in rids])
    out["n_cand_mean"] = float(np.mean([r["n_cand"] for r in Bf.values()]))
    vk.wjson(vk.OUT / "rules" / f"BUDGET_val_{dom}.json", out)
    print(json.dumps({B: (v["task"], v["unknown_task"], v.get("paired_vs_all_task")) for B, v in out.items() if isinstance(v, dict)}))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"parity": lambda: parity(a[1], a[2]), "tune": lambda: tune(a[1]), "evaluate": lambda: evaluate(a[1], a[2]), "budget": lambda: budget_eval(a[1])}[a[0]]()
