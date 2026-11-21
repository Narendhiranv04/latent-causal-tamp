#!/usr/bin/env python3
"""EVALUATOR ONLY (post-seal): DEV_PREREG.md outcomes and diagnostics D1-D6 from sealed predictions/traces, the private DEV labels, the
construction-time kill tables (MINK_STATIC_V2 relaxation) and the teacher verification file.  Frozen models are used only for D2 probes.
    python dev_eval.py RUNS_DIR DEV_PUBLIC DEV_PRIVATE_DIR VERIFY.jsonl TABLES_DIR OUT_DIR [--device cuda]"""
import argparse, functools, hashlib, json, math, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "scaling2d_k12"))
import numpy as np  # noqa: E402

ARMS = ("REC", "REC2", "FLAT", "RAND", "B0")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    return [json.loads(l) for l in open(p)]


def auroc(pos, neg):
    if not pos or not neg:
        return None
    from scipy.stats import rankdata
    s = np.concatenate([pos, neg]); r = rankdata(s); n1 = len(pos)
    return float((r[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * len(neg)))


def boot_mean(vals, B=2000, seed=0):
    v = np.array([x for x in vals if x is not None], float)
    if len(v) == 0:
        return None, None
    rng = np.random.default_rng(seed)
    bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(B)]
    return float(v.mean()), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def mcnemar(a, b):
    """exact two-sided sign test on discordant pairs: a, b lists of 0/1 (paired)."""
    from scipy.stats import binomtest
    n10 = sum(1 for x, y in zip(a, b) if x and not y); n01 = sum(1 for x, y in zip(a, b) if y and not x)
    p = binomtest(n10, n10 + n01, 0.5).pvalue if n10 + n01 else 1.0
    return {"a_only": n10, "b_only": n01, "p_exact": float(p)}


class Static:
    def __init__(self, tables_dir):
        self.T = json.loads((Path(tables_dir) / "MINK_TABLE_original.json").read_text())
        self.QC = set(json.loads((Path(tables_dir) / "QCLEAR_original.json").read_text())["cells"])

    def kill(self, tab, x, occ):
        t = self.T[tab][str(x)]
        return functools.reduce(lambda a, q: a | int(t.get(str(q), 0)), occ, 0)

    def pick(self, cell, others):
        return int(self.T["pick0"][str(cell)]) & ~self.kill("pickkill", cell, others)

    def place(self, d, others):
        return int(self.T["place0"][str(d)]) & ~self.kill("placekill", d, others)

    def feasible(self, cells, A, d):
        oth = [c for i, c in enumerate(cells) if i != A]
        return bool(self.pick(cells[A], oth)) and bool(self.place(d, oth))

    def order_valid(self, cells0, T0, goal, seq):
        cells = list(cells0)
        for i, d in seq:
            if not self.feasible(cells, i, d):
                return False
            cells[i] = d
        return self.feasible(cells, T0, goal)

    def endpoint_y(self, cells0, T0, goal, seq):
        cells = list(cells0)
        for i, d in seq:
            cells[i] = d
        return self.feasible(cells, T0, goal)

    def pick_blockers(self, cells, A):
        base = int(self.T["pick0"][str(cells[A])])
        return {o for o, c in enumerate(cells) if o != A and base & int(self.T["pickkill"][str(cells[A])].get(str(c), 0))}

    def union_goal_sets(self, cells0, T0, goal, K):
        import cert as C
        n = len(cells0); ids = [str(i) for i in range(n)]
        mov = [i for i in range(n) if i != T0]
        dest = [d for d in range(64) if d != goal and d in self.QC]
        P_, D_, G_ = C.masks_fast(self.T, cells0, ids, mov, T0, goal, dest)
        full = (1 << n) - 1
        lv = lambda S, pres: any(m & pres == 0 for m in S)  # noqa: E731
        layer, seen = {0}, {0}
        for _ in range(K):
            nxt = set()
            for M in layer:
                pres = full & ~M
                for o in mov:
                    if not M >> o & 1 and lv(P_[o], pres & ~(1 << o)) and lv(D_[o], pres & ~(1 << o)):
                        N = M | (1 << o)
                        if N not in seen:
                            seen.add(N); nxt.add(N)
            layer = nxt
        GS = [M for M in layer if lv(P_[T0], full & ~M) and lv(G_, full & ~M)]
        U = set()
        for M in GS:
            U |= {i for i in range(n) if M >> i & 1}
        return U, len(GS)


def main(runs, dev_public, priv_dir, verify_f, tables, out, device):
    runs, out = Path(runs), Path(out); out.mkdir(parents=True, exist_ok=True)
    seals = {}
    for a in ARMS:
        sf = runs / a / "SEAL.json"
        if sf.exists():
            s = json.loads(sf.read_text())
            assert sha(runs / a / "predictions.jsonl") == s["predictions_sha256"], f"seal mismatch {a}"
            seals[a] = s
    arms = list(seals)
    pub = {r["root_id"]: r for r in jl(dev_public)}
    priv = {r["root_id"]: r for r in jl(Path(priv_dir) / "dev_private.jsonl")}
    VER = {(r["root_id"], json.dumps(r["seq"])): r for r in jl(verify_f)}
    ST = Static(tables)
    pred = {a: {p["root_id"]: p for p in jl(runs / a / "predictions.jsonl")} for a in arms}
    tr = {a: {rid: json.loads((runs / a / "traces" / f"{rid}.json").read_text()) for rid in pred[a] if (runs / a / "traces" / f"{rid}.json").exists()}
          for a in arms}
    per, D1u, D1w, recall8, D3i, D4, D2 = [], [], [], [], [], [], []
    D3p, D3n = {"REC": [], "REC2": []}, {"REC": [], "REC2": []}
    import models as MD
    FZ = MD.Frozen(device)
    ins_prec = {"true": 0, "all": 0}
    for rid in sorted(priv):
        pv, inp = priv[rid], pub[rid]["inputs"]
        cells0, T0, G0, K = [int(c) for c in inp["cells0"]], int(inp["tid"]), int(inp["goal_cell"]), pv["K"]
        U, nGS = ST.union_goal_sets(cells0, T0, G0, K)
        Wm = {i for i, _ in [(inp["ids"].index(o), d) for o, d in pv["witness"]]}
        rec = {"root_id": rid, "K": K, "n_objects": len(cells0), "pair": pv["pair"], "cells0": cells0, "T0": T0, "G0": G0, "U": sorted(U), "n_goal_sets": nGS,
               "W": sorted(Wm), "arms": {}}
        for a in arms:
            p = pred[a].get(rid)
            if p is None:
                continue
            def outcome(seq):
                if not seq:
                    return None
                v = VER.get((rid, json.dumps(seq)))
                return v
            v = outcome(p["seq"])
            succ = bool(v and v["x"] == 1 and v["y"] == 1)
            if p["decision"] != "REPAIR":
                fail = p["decision"]
            elif not ST.endpoint_y(cells0, T0, G0, p["seq"]):
                fail = "INGREDIENT (static endpoint Y dead)"
            elif not ST.order_valid(cells0, T0, G0, p["seq"]):
                fail = "COMPOSITION (static order invalid)"
            elif not v:
                fail = "UNVERIFIED"
            elif v["x"] != 1:
                fail = f"EXECUTION X=0 {v['x_status']} @{v['x_phase']}"
            elif v["y"] != 1:
                fail = f"FINAL_Y Y=0 {v['y_status']}"
            else:
                fail = "SUCCESS"
            alts = {}
            for k in ("alt_Yonly", "alt_Xonly"):
                va = outcome(p.get(k))
                alts[k] = bool(va and va["x"] == 1 and va["y"] == 1) if p.get(k) else None
            movers = {i for i, _ in p["seq"]}
            rec["arms"][a] = {"decision": p["decision"], "seq": p["seq"], "len": len(p["seq"]), "success": succ, "failure": fail,
                              "outcome": "SUCCESS" if succ else "FAIL", "hY": (p.get("energy") or {}).get("hY", float("nan")) if p.get("energy") else float("nan"),
                              "covers_U_frac": len(movers & U) / max(1, len(movers)), "stop": p["stop"], "budget": p["budget"], "n_candidates": p["n_candidates"],
                              "model_calls": p.get("model_calls"), "alt_success": alts, "teacher": v}
        # ---- D1 / D3(i) from the label-free S0 probe (REC trace)
        prb = tr.get("REC", {}).get(rid, {}).get("probe")
        if prb:
            kb = {int(o): s for o, s in prb["k1_best"].items()}
            mv = sorted(kb)
            D1u.append(auroc([kb[o] for o in mv if o in U], [kb[o] for o in mv if o not in U]))
            D1w.append(auroc([kb[o] for o in mv if o in Wm], [kb[o] for o in mv if o not in Wm]))
            top8 = sorted(mv, key=lambda o: -kb[o])[:8]
            recall8.append({"rid": rid, "hit": len(set(top8) & Wm) / max(1, len(Wm)), "chance": min(8, len(mv)) / max(1, len(mv))})
            pos, neg = [], []
            for o, z in prb["ytask_s0"].items():
                (pos if ST.feasible(cells0, int(o), int(z["d"])) else neg).append(z["y"])
            D3i.append(auroc(pos, neg))
            rec["probe_D1"] = {"auroc_U": D1u[-1], "auroc_W": D1w[-1], "recall8": recall8[-1]["hit"], "chance8": recall8[-1]["chance"], "D3i": D3i[-1]}
        # ---- D3(ii), D4, D5 insertion precision from REC/REC2 logs
        for a in ("REC", "REC2"):
            t = tr.get(a, {}).get(rid)
            if not t:
                continue
            for y in t["log"]["ytask"]:
                cells = list(cells0)
                for i, d in y["P"]:
                    cells[i] = d
                (D3p if ST.feasible(cells, y["A"], y["d"]) else D3n)[a].append(y["y"])
            for L in t["log"]["local"]:
                if L["task"].startswith("TT") and L["P_len"] == 0:
                    A = int(L["task"][2:]); blk = ST.pick_blockers(cells0, A)
                    kb = {int(o): s for o, s in L["k1_best"].items()}
                    D4.append(auroc([kb[o] for o in kb if o in blk], [kb[o] for o in kb if o not in blk]))
            for e in t["log"]["insert"]:
                if e["P_len"] == 0:
                    A = e["before"][0]; blk = ST.pick_blockers(cells0, A)
                    for o, _ in e["enabling"]:
                        ins_prec["all"] += 1; ins_prec["true"] += int(o in blk)
        # ---- D2: frozen h_Y (Y-only vs S0) on the witness endpoint vs 20 random same-size mover sets; and along witness prefixes
        wseq = [(inp["ids"].index(o), int(d)) for o, d in pv["witness"]]
        props = (prb or {}).get("proposals_s0", {})
        rng = random.Random(f"D2|{rid}")
        mv_all = [i for i in range(len(cells0)) if i != T0]
        rnd = []
        while len(rnd) < 20:
            objs = rng.sample(mv_all, min(K, len(mv_all))); used, sq = set(cells0), []
            for o in objs:
                d = next((x for x in props.get(str(o), []) if x not in used and x != G0), None)
                if d is None:
                    d = next(x for x in range(64) if x not in used and x != G0)
                used.add(d); sq.append((o, d))
            rnd.append(sq)
        hw = FZ.y_end(pub[rid], [wseq])[0]; hr_ = FZ.y_end(pub[rid], rnd)
        hp = FZ.y_end(pub[rid], [wseq[:k] for k in range(1, K + 1)])
        D2.append(float(np.mean([hw > x for x in hr_]) + 0.5 * np.mean([hw == x for x in hr_])))
        rec["D2"] = {"hY_witness": hw, "hY_random_mean": float(np.mean(hr_)), "auroc_vs_random": D2[-1], "hY_prefix": hp, "hY_S0": FZ.y_noop(pub[rid])}
        per.append(rec)
    with open(out / "per_scene.jsonl", "w") as f:
        for r in per:
            f.write(json.dumps(r) + "\n")
    # ---- aggregate
    S = {"n_scenes": len(per), "by_K": {}, "arms": {}, "paired": {}, "seals": {a: seals[a]["predictions_sha256"][:16] for a in arms}}
    for a in arms:
        rows = [r for r in per if a in r["arms"]]
        S["arms"][a] = {"success": sum(r["arms"][a]["success"] for r in rows), "n": len(rows),
                        "by_K": {str(k): f"{sum(r['arms'][a]['success'] for r in rows if r['K'] == k)}/{sum(1 for r in rows if r['K'] == k)}" for k in sorted({r['K'] for r in rows})},
                        "failures": {}, "stops": {}, "mean_local_calls": float(np.mean([r["arms"][a]["budget"]["local"] for r in rows])),
                        "mean_ytask_probes": float(np.mean([r["arms"][a]["budget"]["ytask"] for r in rows])),
                        "mean_wall_s": float(np.mean([r["arms"][a]["budget"]["wall_s"] for r in rows])),
                        "mean_local_scored": float(np.mean([(r["arms"][a]["model_calls"] or {}).get("local_scored", 0) for r in rows])),
                        "mean_len": float(np.mean([r["arms"][a]["len"] for r in rows])), "len_eq_K": sum(r["arms"][a]["len"] == r["K"] for r in rows),
                        "mean_covers_U_frac": float(np.mean([r["arms"][a]["covers_U_frac"] for r in rows])),
                        "alt_Yonly_success": sum(bool(r["arms"][a]["alt_success"].get("alt_Yonly")) for r in rows),
                        "alt_Xonly_success": sum(bool(r["arms"][a]["alt_success"].get("alt_Xonly")) for r in rows)}
        for r in rows:
            f_ = r["arms"][a]["failure"].split(" @")[0]
            S["arms"][a]["failures"][f_] = S["arms"][a]["failures"].get(f_, 0) + 1
            S["arms"][a]["stops"][r["arms"][a]["stop"]] = S["arms"][a]["stops"].get(r["arms"][a]["stop"], 0) + 1
    for a, b in (("REC", "FLAT"), ("REC", "RAND"), ("REC2", "FLAT"), ("REC2", "RAND"), ("REC", "REC2"), ("FLAT", "RAND")):
        if a in arms and b in arms:
            ids = [r for r in per if a in r["arms"] and b in r["arms"]]
            S["paired"][f"{a}_vs_{b}"] = mcnemar([r["arms"][a]["success"] for r in ids], [r["arms"][b]["success"] for r in ids])
    m, ci = boot_mean(D1u); S["D1_auroc_U"] = {"mean": m, "ci95": ci, "n_scenes": len([x for x in D1u if x is not None])}
    m, ci = boot_mean(D1w); S["D1_auroc_W"] = {"mean": m, "ci95": ci}
    S["D1_recall8"] = {"mean_hit": float(np.mean([x["hit"] for x in recall8])) if recall8 else None, "mean_chance": float(np.mean([x["chance"] for x in recall8])) if recall8 else None}
    m, ci = boot_mean(D3i); S["D3i_ytask_S0_auroc"] = {"mean": m, "ci95": ci}
    S["D3ii_ytask_logged_auroc"] = {a: {"auroc": auroc(D3p[a], D3n[a]), "n_pos": len(D3p[a]), "n_neg": len(D3n[a]),
                                        "mean_y_pos": float(np.mean(D3p[a])) if D3p[a] else None, "mean_y_neg": float(np.mean(D3n[a])) if D3n[a] else None} for a in D3p}
    m, ci = boot_mean(D2); S["D2_hY_witness_vs_random_auroc"] = {"mean": m, "ci95": ci}
    S["D2_hY_witness_mean"] = float(np.mean([r["D2"]["hY_witness"] for r in per])); S["D2_hY_random_mean"] = float(np.mean([r["D2"]["hY_random_mean"] for r in per]))
    m, ci = boot_mean(D4); S["D4_tt_blocker_ranking_auroc_S0"] = {"mean": m, "ci95": ci, "n_calls": len([x for x in D4 if x is not None])}
    S["D5_insertion_precision_S0"] = {**ins_prec, "frac": ins_prec["true"] / ins_prec["all"] if ins_prec["all"] else None}
    (out / "DEV_SUMMARY.json").write_text(json.dumps(S, indent=1))
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for k in ("runs", "dev_public", "priv", "verify", "tables", "out"):
        ap.add_argument(k)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(); main(a.runs, a.dev_public, a.priv, a.verify, a.tables, a.out, a.device)
