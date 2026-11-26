#!/usr/bin/env python3
"""Readout / order ablation CLI (plan.md 6).  Evaluator steps import labels.py; planner steps (parity, infer, panel scoring) use readout.py only.

    python run.py audit          P0: provenance, roster + C0 reference check, label / order-group inventory   -> reports/P0_AUDIT.json
    python run.py panel          P0: lock the O-B permutation panel from legacy witness endpoints (no scores, no X labels) -> reports/P0_PANEL.json
    python run.py parity DOM     P1: 20 VAL roots (CR parity roster): J == archived EXACT4, readout identities -> reports/P1_PARITY_<dom>.json"""
from __future__ import annotations

import collections, hashlib, itertools, json, os, platform, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ABF = HERE.parent
sys.path.insert(0, str(ABF))
H = Path.home()
REP = HERE / "reports"
RUNS = Path(os.environ.get("XYO_RUNS", H / "xyo_runs"))
PRIV = Path(os.environ.get("XYO_PRIV", H / "xyo_private"))
CR = ABF / "complete_repair_cvae"
CR_PRIV, CR_RUNS = H / "cr_cvae_private", H / "cr_cvae_runs"
V34 = H / "abf_v34"
TRAIN_SNAP = H / "abf_v32/snap_out/snapshot/abf_v32_fb0eef4f5ff433ee"
VAL_SNAP = H / "abf_v3_laptop/root/snapshot/abf_9de85710c2a7103f"
DOMS = ("2d", "3d")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl(p):
    import gzip
    op = gzip.open if str(p).endswith(".gz") else open
    return [json.loads(l) for l in op(p, "rt") if l.strip()]


def wj(name, obj):
    REP.mkdir(parents=True, exist_ok=True)
    (REP / name).write_text(json.dumps(obj, indent=1, default=str))


def h(tag, *parts):
    return hashlib.sha256("|".join([tag, *map(str, parts)]).encode()).hexdigest()


def roster(dom):
    return {e["root_id"]: e for e in jl(CR_PRIV / f"cohort_{dom}.jsonl")}


def val_rows(dom):
    return [r for r in map(json.loads, open(VAL_SNAP / f"data{dom}.jsonl")) if r["split"] == "val"]


def top4_of(dom):
    """Frozen C0 top-4 proposals per root (model output, label-free): cohort from the CR P3 records, VAL from the CR DEV records."""
    out = {}
    for f in (CR_RUNS / "p3" / f"pred_{dom}.jsonl", CR_RUNS / "dev" / f"pred_{dom}_s0.jsonl.gz"):
        if Path(f).exists():
            for r in jl(f):
                if "C0" in r:
                    out[r["root_id"]] = {int(k): set(v) for k, v in r["C0"]["proposals"].items()}
    return out


# ------------------------------------------------------------------------------------------------ P0
def legacy_witnesses(dom, e):
    """Generator legacy-protocol witnesses (labels.B, y = 1) of a cohort root as index sequences; endpoint metadata only."""
    rec = json.loads((V34 / "final" / e["path"]).read_text())
    ids = e["ids"]
    out = []
    for b in rec.get("labels", {}).get("B", []):
        if b.get("y") == 1 and b.get("sequence") and len(b["sequence"]) <= 3:
            out.append([[ids.index(o), int(c) if not isinstance(c, list) else int(c[0]) * 6 + int(c[1])] for o, c in b["sequence"]])
    return out


def audit():
    import labels as L
    rep = {"head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip(),
           "plan_sha256": sha(HERE / "plan.md"), "prompt_sha256": sha(HERE / "starting_prompt.md"), "host": platform.node(), "domains": {}}
    man = json.loads((V34 / "approach_b_bundle/MANIFEST.json").read_text())
    rep["bundle"] = {"config": man["config"], "files_ok": {n: sha(V34 / "approach_b_bundle" / n) == x for n, x in man["files"].items()}}
    crp0 = json.loads((CR / "reports/P0_PROVENANCE.json").read_text())
    rep["teacher_runtime_matches_CR_P0"] = {k: (sha(p) if Path(p).exists() else None) == v for k, v in crp0["teacher_runtime"]["source_sha256"].items()
                                            for p in [{"3d_fin3d": H / "abf_v3_laptop/gen/final3d_v4/code/fin3d.py", "3d_perm3d": H / "abf_v3_laptop/gen/final3d_v4/code/perm3d.py",
                                                      "3d_bwlphys": H / "abf_v3_laptop/gen/final3d_v4/code/bwlphys.py", "2d_teacher2d_runtime": H / "abf_v3_laptop/root/code/teacher2d.py"}[k]]}
    coh = json.loads((CR / "reports/P0_COHORT.json").read_text())
    per = [json.loads(l) for l in open(CR / "reports/P5_PER_ROOT.jsonl")]
    for dom in DOMS:
        ros = roster(dom)
        c0 = [x for x in per if x["domain"] == dom and x["arm"] == "C0" and x["K"] in ("1", "2", "3")]
        D = {"roster_n": len(ros), "roster_sha256": sha(CR_PRIV / f"cohort_{dom}.jsonl"),
             "roster_matches_CR_P0": sha(CR_PRIV / f"cohort_{dom}.jsonl") == coh["domains"][dom]["private_file_sha256"],
             "by_K": dict(collections.Counter(e["K"] for e in ros.values())), "families": len({e["parent_family_id"] for e in ros.values()}),
             "C0_reference_K1_3": {"success": sum(x["strict"] == "SUCCESS" for x in c0), "n": len(c0)}}
        vr = val_rows(dom)
        top4 = top4_of(dom)
        for split, roots, snap in (("val", {r["root_id"] for r in vr}, vr), ("cohort", set(ros), ())):
            led = L.Ledger(dom, roots, snap)
            xs = collections.Counter((r["status"] if r["strict"] is None else f"x={r['strict']}") for r in led.X.values())
            ys = collections.Counter((r["status"] if r["strict"] is None else f"y={r['strict']}") for r in led.Y.values())
            G = L.order_groups(led, roots)
            gs = collections.Counter()
            for (root, e), g in G.items():
                dec = {s: r["strict"] for s, r in g["orders"].items() if r["strict"] is not None}
                m = g["m"]
                tag = f"m{m}"
                in4 = root in top4 and all(d in top4[root].get(o, set()) for o, d in json.loads(e))
                gs[tag + "|groups"] += 1
                gs[tag + "|>=2_decided_orders"] += len(dec) >= 2
                mixed = 1 in dec.values() and 0 in dec.values()
                gs[tag + "|mixed_X"] += mixed
                gs[tag + "|mixed_X_and_Y1"] += mixed and g["y_strict"] == 1
                gs[tag + "|complete_all_orders_decided"] += len(dec) == math_fact(m)
                gs[tag + "|complete_and_Y1"] += len(dec) == math_fact(m) and g["y_strict"] == 1
                gs[tag + "|mixed_in_top4_pool"] += mixed and in4
            fam = {r["root_id"]: r["parent_family_id"] for r in vr} if split == "val" else {k: e["parent_family_id"] for k, e in ros.items()}
            mixed_roots = {root for (root, e), g in G.items() if {r["strict"] for r in g["orders"].values()} >= {0, 1}}
            D[split] = {"X_labels": dict(xs), "Y_endpoint_labels": dict(ys), "conflicts": {"|".join(k): v for k, v in led.conflicts.items()},
                        "order_groups": dict(sorted(gs.items())), "mixed_roots": len(mixed_roots), "mixed_families": len({fam.get(r) for r in mixed_roots}),
                        "sources": led.files if split == "cohort" else {k: v for k, v in led.files.items() if v["results_used"]}}
        rep["domains"][dom] = D
    wj("P0_AUDIT.json", rep)
    print(json.dumps({d: {k: v for k, v in x.items() if k in ("roster_matches_CR_P0", "C0_reference_K1_3")} | {s: x[s]["order_groups"] for s in ("val", "cohort")}
                      for d, x in rep["domains"].items()}, indent=0))


def math_fact(m):
    return 2 if m == 2 else 6


def panel():
    """O-B: 10 assignments of length 2 and 10 of length 3 per domain from legacy witness endpoints of the locked cohort; sha256 order
    XYORDER_PANEL_V1|domain|root|canonical, at most one per root, distinct families first.  No model score or X label is read."""
    out = {"salt": "XYORDER_PANEL_V1", "domains": {}}
    for dom in DOMS:
        ros = roster(dom)
        cand = {2: [], 3: []}
        for rid, e in ros.items():
            for s in legacy_witnesses(dom, e):
                if len(s) in (2, 3):
                    can = json.dumps(sorted(s))
                    cand[len(s)].append((h("XYORDER_PANEL_V1", dom, rid, can), rid, can, e["parent_family_id"], e["K"]))
        used_root, used_fam, sel = set(), set(), []
        for m in (2, 3):
            pool = sorted(set(cand[m]))
            pick = []
            for pass_ in (0, 1):                                            # distinct families first, then any unused root
                for hh, rid, can, fam, K in pool:
                    if len(pick) >= 10:
                        break
                    if rid in used_root or (pass_ == 0 and fam in used_fam):
                        continue
                    pick.append({"root_id": rid, "m": m, "assignment": json.loads(can), "family": fam, "K": K, "hash": hh[:16],
                                 "permutations": [list(map(list, p)) for p in itertools.permutations(json.loads(can))]})
                    used_root.add(rid); used_fam.add(fam)
            sel += pick
        out["domains"][dom] = {"n": len(sel), "by_m": dict(collections.Counter(x["m"] for x in sel)), "families": len({x["family"] for x in sel}),
                               "candidates_by_m": {m: len(set(cand[m])) for m in (2, 3)}, "ordered_requests_max": sum(len(x["permutations"]) for x in sel),
                               "items": sel}
    wj("P0_PANEL.json", out)
    print(json.dumps({d: {k: v for k, v in x.items() if k != "items"} for d, x in out["domains"].items()}))


# ------------------------------------------------------------------------------------------------ P1 parity
def parity(dom):
    import numpy as np
    import readout as R
    import search as S
    ids = json.loads((CR / "reports/P0_PARITY_IDS.json").read_text())[dom]
    pub = {r["root_id"]: r for r in map(json.loads, open(V34 / f"parity/public_val_{dom}.jsonl"))}
    arch = {r["root_id"]: r for r in map(json.loads, open(V34 / f"parity/pred_val_{dom}_gpu.jsonl"))}
    samp, scor, man = R.load(dom)
    rows, worst = [], collections.defaultdict(float)
    for rid in ids:
        rec = R.run_root(pub[rid], samp, scor, man)
        a = arch[rid]
        aseq = [[m["object_index"], m["destination_cell"]] for m in a["moves"]] if a["decision"] == "REPAIR" else ([] if a["decision"] == "NOOP" else None)
        J = rec["arms"]["J"]
        root = S.Root(pub[rid], dom)
        probe = [x["seq"] for x in rec["arms"].values() if x["decision"] == "REPAIR"] + [x["seq"] for x in rec["rank_only"].values() if x]
        perms = [list(map(list, p)) for s in probe for p in itertools.permutations(s)]
        sc, pn = R.score(scor, root, perms) if perms else ({}, None)
        ref = scor.score(root, perms) if perms else []
        for i, r in enumerate(ref):
            worst["p11_vs_Scorer"] = max(worst["p11_vs_Scorer"], abs(r["p11"] - sc["p11"][i]))
            worst["py_vs_Scorer"] = max(worst["py_vs_Scorer"], abs(r["py"] - sc["py"][i]))
            worst["px_vs_Scorer"] = max(worst["px_vs_Scorer"], abs(r["px"] - sc["px"][i]))
            worst["p11_identity"] = max(worst["p11_identity"], abs(sc["p11"][i] - sc["py"][i] * sc["px1"][i]))
            worst["px_identity"] = max(worst["px_identity"], abs(sc["px"][i] - (sc["py"][i] * sc["px1"][i] + (1 - sc["py"][i]) * sc["px0"][i])))
        for s in probe:                                                     # endpoint invariance of pY across the permutations of one assignment
            idx = [i for i, p in enumerate(perms) if sorted(map(tuple, p)) == sorted(map(tuple, s))]
            if idx:
                worst["py_perm_range"] = max(worst["py_perm_range"], float(np.ptp(sc["py"][idx])))
        worst["py_endpoint_drift_stream"] = max(worst["py_endpoint_drift_stream"], rec["py_endpoint_drift"])
        rows.append({"root_id": rid, "J_equal": J["decision"] == a["decision"] and J["seq"] == aseq, "proposals_equal": rec["proposals"] == a.get("proposals"),
                     "J": [J["decision"], J["seq"], J["score"]], "archived": [a["decision"], aseq, a.get("score_p11")], "p_noop": rec["p_noop"],
                     "noop_below_gate_competes": 0.3 <= rec["p_noop"] < 0.5, "n_pool": rec["n_pool"],
                     "arms": {k: [v["decision"], v["seq"]] for k, v in rec["arms"].items()}, "rank_only": {k: v and v["seq"] for k, v in rec["rank_only"].items()}})
    out = {"dom": dom, "n": len(rows), "J_equal": sum(r["J_equal"] for r in rows), "proposals_equal": sum(r["proposals_equal"] for r in rows),
           "max_abs": dict(worst), "noop_below_gate_roots": sum(r["noop_below_gate_competes"] for r in rows), "rows": rows}
    wj(f"P1_PARITY_{dom}.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}))



# ------------------------------------------------------------------------------------------------ P2 DEV diagnostics (VAL, exposed)
def score_many(scor, root, seqs, chunk=8192):
    import numpy as np
    import readout as R
    out = {k: [] for k in ("py", "px", "p11", "px1", "px0")}
    for i in range(0, len(seqs), chunk):
        sc, _ = R.score(scor, root, seqs[i:i + chunk])
        for k in out:
            out[k].append(sc[k])
    return {k: np.concatenate(v) if v else np.zeros(0) for k, v in out.items()}


def dev(dom):
    import numpy as np
    import labels as L
    import ordering as O
    import readout as R
    import search as S
    import stats as ST
    vr = val_rows(dom)
    fam = {r["root_id"]: r["parent_family_id"] for r in vr}
    Kof = {r["root_id"]: r["K_legacy"] for r in vr}
    pub = {r["root_id"]: r for r in map(json.loads, open(V34 / f"parity/public_val_{dom}.jsonl"))}
    led = L.Ledger(dom, set(fam), vr)
    samp, scor, man = R.load(dom)
    lay = layout_overlap(dom)
    seqs_by = collections.defaultdict(set)
    for (root, k) in led.X:
        seqs_by[root].add(k)
    for (root, e), r in led.Y.items():
        if e != "[]" and r["strict"] is not None and not any(L.ekey(json.loads(k)) == e for k in seqs_by[root]):
            seqs_by[root].add(json.dumps(json.loads(e)))                      # any order of the endpoint gives its pY
    G = {k: g for k, g in L.order_groups(led, set(fam)).items() if sum(r["strict"] is not None for r in g["orders"].values()) >= 2}
    for (root, e) in G:
        for q in O.all_orders(json.loads(e)):
            seqs_by[root].add(O.sig(q))
    rows, groups = [], []
    for root, ks in sorted(seqs_by.items()):
        seqs = [json.loads(k) for k in sorted(ks)]
        sc = score_many(scor, S.Root(pub[root], dom), seqs)
        S_ = {O.sig(q): {k: float(sc[k][i]) for k in sc} for i, q in enumerate(seqs)}
        for k, v in S_.items():
            x, y, z, xs, ys = led.get(root, json.loads(k))
            rows.append({"root": root, "seq": k, "e": L.ekey(json.loads(k)), "x": x if (root, k) in led.X else None, "y": y, "z": z if (root, k) in led.X else None, **v})
        for (r2, e), g in G.items():
            if r2 != root:
                continue
            ords = O.all_orders(json.loads(e))
            xl = {O.sig(q): (g["orders"][O.sig(q)]["strict"] if O.sig(q) in g["orders"] else None) for q in ords}
            res = {"root": root, "family": fam[root], "K": Kof[root], "y": g["y_strict"], "layout_overlap": root in lay}
            for f in ("px1", "px", "px0", "p11"):
                res[f] = O.group(json.loads(e), {O.sig(q): S_[O.sig(q)][f] for q in ords}, xl)
            res["py_range"] = float(np.ptp([S_[O.sig(q)]["py"] for q in ords]))
            groups.append(res)
    # ---- factor diagnostics (unique endpoints for Y; decided labels only)
    ys = {}
    for r in rows:
        if r["y"] is not None:
            ys.setdefault((r["root"], r["e"]), (r["py"], r["y"]))
    D = {"Y_pY_vs_Y_endpoints": ST.calib(*zip(*ys.values())) if ys else None}
    def sub(cond, f, lab):
        xs = [(r[f], r[lab]) for r in rows if cond(r) and r[lab] is not None]
        return ST.calib(*zip(*xs)) if xs else None
    D["X_marginal_pX_vs_X"] = sub(lambda r: True, "px", "x")
    D["XC_pX1_vs_X_given_Y1"] = sub(lambda r: r["y"] == 1, "px1", "x")
    D["X0_pX0_vs_X_given_Y0"] = sub(lambda r: r["y"] == 0, "px0", "x")
    D["J_p11_vs_Z"] = sub(lambda r: True, "p11", "z")
    for f in ("py", "px", "px1"):
        D[f"crosshead_{f}_vs_Z_pooled"] = sub(lambda r: True, f, "z")
    # ---- within-root Z ranking on identical labelled candidates (repair-ranking diagnostic, NOT calibration of a head)
    W = {}
    byroot = collections.defaultdict(list)
    for r in rows:
        byroot[r["root"]].append(r)
    for arm, f in (("J", "p11"), ("X", "px"), ("Y", "py"), ("XC", "px1")):
        for tag, cond in (("all", lambda r: True), ("excl_layout", lambda r: r["root"] not in lay), ("K1K2", lambda r: Kof[r["root"]] in ("1", "2")),
                          ("K3", lambda r: Kof[r["root"]] == "3")):
            gz = collections.defaultdict(list)
            for r in rows:
                if r["z"] is not None and cond(r):
                    gz[r["root"]].append((r[f], r["z"]))
            W[f"{arm}|{tag}"] = ST.within_root({k: (fam[k], v) for k, v in gz.items()})
        top = []
        for root, rr in byroot.items():
            c = [r for r in rr if r["z"] is not None]
            if any(r["z"] == 1 for r in c) and any(r["z"] == 0 for r in c):
                top.append((fam[root], max(c, key=lambda r: (r[f], -len(r["seq"])))["z"]))
        W[f"{arm}|top1_known_set"] = ST.cluster_mean([t for _, t in top], [f_ for f_, _ in top])
    # conditional X correctness: pX1 vs X restricted to Y = 1, within root
    gx = collections.defaultdict(list)
    for r in rows:
        if r["y"] == 1 and r["x"] is not None:
            gx[r["root"]].append((r["px1"], r["x"]))
    W["XC_vs_X_given_Y1|within_root"] = ST.within_root({k: (fam[k], v) for k, v in gx.items()})
    # ---- O-A order groups (exposed VAL; selection-biased)
    OA = {}
    for m in (2, 3):
        for ytag, yc in (("Y1", lambda g: g["y"] == 1), ("Y0", lambda g: g["y"] == 0), ("any", lambda g: True)):
            gg = [g for g in groups if g["px1"]["m"] == m and yc(g)]
            mix = [g for g in gg if g["px1"]["mixed"]]
            comp = [g for g in gg if g["px1"]["complete"]]
            OA[f"m{m}|{ytag}"] = {"groups": len(gg), "mixed": len(mix), "complete": len(comp), "mixed_families": len({g["family"] for g in mix}),
                                  "conc_pX1": ST.cluster_mean([g["px1"]["concordance"] for g in mix], [g["family"] for g in mix]),
                                  "conc_pX": ST.cluster_mean([g["px"]["concordance"] for g in mix], [g["family"] for g in mix]),
                                  "conc_pX0": ST.cluster_mean([g["px0"]["concordance"] for g in mix], [g["family"] for g in mix]),
                                  "complete_learned_pX1": ST.cluster_mean([g["px1"]["learned_x"] for g in comp], [g["family"] for g in comp]),
                                  "complete_canonical": ST.cluster_mean([g["px1"]["canonical_x"] for g in comp], [g["family"] for g in comp]),
                                  "complete_random": ST.cluster_mean([g["px1"]["random_x"] for g in comp], [g["family"] for g in comp]),
                                  "complete_oracle": ST.cluster_mean([g["px1"]["oracle_any"] for g in comp], [g["family"] for g in comp]),
                                  "complete_mixed_learned": ST.cluster_mean([g["px1"]["learned_x"] for g in comp if g["px1"]["mixed"]], [g["family"] for g in comp if g["px1"]["mixed"]]),
                                  "complete_mixed_random": ST.cluster_mean([g["px1"]["random_x"] for g in comp if g["px1"]["mixed"]], [g["family"] for g in comp if g["px1"]["mixed"]]),
                                  "complete_mixed_canonical": ST.cluster_mean([g["px1"]["canonical_x"] for g in comp if g["px1"]["mixed"]], [g["family"] for g in comp if g["px1"]["mixed"]]),
                                  "top_differs_from_canonical": sum(g["px1"]["top_differs_from_canonical"] for g in gg),
                                  "py_range_max": max([g["py_range"] for g in gg], default=None)}
    out = {"dom": dom, "split": "VAL (exposed DEV)", "n_scored_sequences": len(rows), "factor": D, "within_root": W, "order_OA": OA,
           "layout_overlap_roots": len(lay), "label_sources": {k: v for k, v in led.files.items() if v["results_used"]}}
    wj(f"P2_DEV_{dom}.json", out)
    with open(RUNS / f"dev_groups_{dom}.jsonl", "w") as f:
        for g in groups:
            f.write(json.dumps(g) + "\n")
    print(json.dumps({"factor": {k: v and {kk: v[kk] for kk in ("n", "auroc")} for k, v in D.items()},
                      "within": {k: v and v["mean"] for k, v in W.items()}, "OA": {k: (v["mixed"], v["conc_pX1"] and v["conc_pX1"]["mean"]) for k, v in OA.items()}}, indent=0))


def layout_overlap(dom):
    def fp(r):
        inp = r["inputs"]
        return json.dumps([sorted(int(c) for i, c in enumerate(inp["cells0"]) if i != inp["tid"]), int(inp["cells0"][inp["tid"]]), int(inp["goal_cell"])])
    tr = {fp(r) for r in map(json.loads, open(TRAIN_SNAP / f"data{dom}.jsonl")) if r["split"] == "train"}
    return {r["root_id"] for r in val_rows(dom) if fp(r) in tr}


# ------------------------------------------------------------------------------------------------ P2 cohort inference, panel scoring, seal
def infer(dom):
    import readout as R
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"pred_{dom}.jsonl"
    done = {json.loads(l)["root_id"] for l in open(out)} if out.exists() else set()
    samp, scor, man = R.load(dom)
    with open(out, "a") as f:
        for r in jl(CR_RUNS / "p3" / f"public_{dom}.jsonl"):
            if r["root_id"] not in done:
                f.write(json.dumps(R.run_root(r, samp, scor, man)) + "\n"); f.flush()
    sealed = {r["root_id"]: r for r in jl(CR / "reports/sealed" / f"sealed_C0_{dom}.jsonl")}
    P = jl(out)
    eq = sum(1 for p in P if p["arms"]["J"]["decision"] == sealed[p["root_id"]]["decision"] and
             (p["arms"]["J"]["seq"] or []) == [[m["object_index"], m["destination_cell"]] for m in sealed[p["root_id"]]["moves"]])
    print(json.dumps({"dom": dom, "n": len(P), "J_equals_CR_sealed_C0": eq}))


def panel_score(dom):
    import readout as R
    import search as S
    import ordering as O
    pan = json.loads((REP / "P0_PANEL.json").read_text())["domains"][dom]["items"]
    pub = {r["root_id"]: r for r in jl(CR_RUNS / "p3" / f"public_{dom}.jsonl")}
    samp, scor, man = R.load(dom)
    out = []
    for it in pan:
        perms = it["permutations"]
        sc, _ = R.score(scor, S.Root(pub[it["root_id"]], dom), perms)          # planner sees S0 + the unordered assignment only
        s = {O.sig(q): {k: float(sc[k][i]) for k in ("py", "px", "p11", "px1", "px0")} for i, q in enumerate(perms)}
        top = O.learned_top(perms, {k: v["px1"] for k, v in s.items()})
        topx = O.learned_top(perms, {k: v["px"] for k, v in s.items()})
        out.append({"root_id": it["root_id"], "m": it["m"], "assignment": it["assignment"], "scores": s, "learned_pX1": top, "learned_pX": topx,
                    "canonical": O.canonical(perms), "py_range": max(v["py"] for v in s.values()) - min(v["py"] for v in s.values())})
    with open(RUNS / f"panel_scores_{dom}.jsonl", "w") as f:
        for x in out:
            f.write(json.dumps(x) + "\n")
    print(json.dumps({"dom": dom, "n": len(out), "py_range_max": max(x["py_range"] for x in out),
                      "top_differs_from_canonical": sum(x["learned_pX1"] != x["canonical"] for x in out)}))


def seal():
    import benchmark as BM
    import time
    man = {"protocol_sha256": sha(HERE / "protocol.json"), "panel_sha256": sha(REP / "P0_PANEL.json"), "domains": {}}
    (REP / "sealed").mkdir(exist_ok=True)
    for dom in DOMS:
        P = jl(RUNS / f"pred_{dom}.jsonl")
        pub = {r["root_id"]: r for r in jl(CR_RUNS / "p3" / f"public_{dom}.jsonl")}
        assert set(p["root_id"] for p in P) == set(roster(dom)) == set(pub)
        files = {}
        for kind in ("arms", "rank_only"):
            for a in ("J", "X", "Y", "XC"):
                fp = REP / "sealed" / f"{kind}_{a}_{dom}.jsonl"
                with open(fp, "w") as f:
                    for p in sorted(P, key=lambda r: r["root_id"]):
                        x = p[kind][a]
                        if kind == "arms":
                            dec, seq = x["decision"], x["seq"] if x["decision"] == "REPAIR" else []
                        else:
                            dec, seq = ("REPAIR", x["seq"]) if x else ("ABSTAIN", [])
                        ids = pub[p["root_id"]]["inputs"]["ids"]
                        f.write(json.dumps({"root_id": p["root_id"], "domain": dom, "decision": dec,
                                            "moves": [{"object_id": ids[o], "object_index": o, "destination_cell": c} for o, c in seq]}) + "\n")
                v, c = BM.validate(CR_RUNS / "p3" / f"public_{dom}.jsonl", fp, quiet=True)
                assert not any(v.values()), (kind, a, dom, c)
                files[fp.name] = {"sha256": sha(fp), "validate": dict(c)}
        ph = hashlib.sha256("".join(p["pool_hash"] for p in sorted(P, key=lambda r: r["root_id"])).encode()).hexdigest()
        man["domains"][dom] = {"records_sha256": sha(RUNS / f"pred_{dom}.jsonl"), "panel_scores_sha256": sha(RUNS / f"panel_scores_{dom}.jsonl"),
                               "pool_hashes_sha256": ph, "files": files}
    man["sealed_utc"] = time.strftime("%FT%TZ", time.gmtime())
    wj("P2_SEAL.json", man)
    print(json.dumps({d: {k: v for k, v in x.items() if k != "files"} for d, x in man["domains"].items()}))


def manifest():
    """Tiered teacher jobs for sealed picks / panel orders lacking an exact-key label (protocol 'queries')."""
    import labels as L
    seal_ = json.loads((REP / "P2_SEAL.json").read_text())
    idx = {e["root_id"]: e for e in jl(V34 / "final/PRIVATE_INDEX.jsonl")}
    out = {"seal_sha256": sha(REP / "P2_SEAL.json"), "domains": {}}
    for dom in DOMS:
        assert sha(RUNS / f"pred_{dom}.jsonl") == seal_["domains"][dom]["records_sha256"]
        ros = roster(dom)
        led = L.Ledger(dom, set(ros))
        need = collections.defaultdict(dict)
        def want(rid, seq, tier):
            k = json.dumps([list(map(int, a)) for a in seq])
            if not led.queried(rid, seq):
                need[rid][k] = min(tier, need[rid].get(k, tier))
        P = {p["root_id"]: p for p in jl(RUNS / f"pred_{dom}.jsonl")}
        for rid, p in P.items():
            for a in ("J", "X", "Y"):
                x = p["arms"][a]
                if x["decision"] == "REPAIR":
                    want(rid, x["seq"], "T1" if ros[rid]["K"] in ("1", "2", "3") else "T3")
            for a in ("XC",):
                if p["arms"][a]["decision"] == "REPAIR":
                    want(rid, p["arms"][a]["seq"], "T4")
            for a in ("J", "X", "Y", "XC"):
                if p["rank_only"][a]:
                    want(rid, p["rank_only"][a]["seq"], "T4")
        for x in jl(RUNS / f"panel_scores_{dom}.jsonl"):
            for q in x["scores"]:
                want(x["root_id"], json.loads(q), "T2")
        caps = {"T1": 320, "T2": 80}
        keep, n, used = [], 0, collections.Counter()
        for t in ("T1", "T2", "T3", "T4"):
            for rid in sorted({r for r, v in need.items() if t in v.values()}, key=lambda r: h("XYO_Q", r)):
                js = [(rid, k, t) for k, tt in need[rid].items() if tt == t]
                if used[t] + len(js) <= caps.get(t, 400) and n + len(js) <= 400:
                    keep += js; n += len(js); used[t] += len(js)
        allj = [(r, k, t) for r, v in need.items() for k, t in v.items()]
        rows = []
        for t in ("T1", "T2", "T3", "T4"):                                       # dispatch order = tier order (CPU-cap truncation hits later tiers)
            by = collections.defaultdict(list)
            for rid, k, tt in keep:
                if tt == t:
                    by[rid].append(k)
            for rid in sorted(by, key=lambda r: h("XYO_Q", r)):
                e = idx[rid]
                rows.append({"root_id": rid, "dom": dom.upper(), "tier": t, "path": str((V34 / "final" / e["path"]).resolve()), "geom": e.get("geom", "original"),
                             "seqs": [[[e["ids"][o], c] for o, c in json.loads(k)] for k in sorted(by[rid])], "ids": e["ids"]})
        RUNS.joinpath("p3").mkdir(parents=True, exist_ok=True)
        with open(RUNS / "p3" / f"jobs_{dom}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        out["domains"][dom] = {"queries": len(keep), "by_tier": dict(collections.Counter(t for _, _, t in keep)),
                               "needed_by_tier": dict(collections.Counter(t for _, _, t in allj)), "dropped": len(allj) - len(keep),
                               "dropped_by_tier": dict(collections.Counter(t for r, k, t in allj if (r, k, t) not in keep)),
                               "jobs_sha256": sha(RUNS / "p3" / f"jobs_{dom}.jsonl")}
    wj("P2_QUERY_MANIFEST.json", out)
    print(json.dumps(out["domains"]))


CAP_H = {"2d": 8.0, "3d": 16.0}


def teach(dom, first=None, workers=16, cpu0=8, batch_q=100):
    import time
    L_ = H / "abf_v3_laptop"
    P3 = RUNS / "p3"
    jobs = jl(P3 / f"jobs_{dom}.jsonl")
    assert sha(P3 / f"jobs_{dom}.jsonl") == json.loads((REP / "P2_QUERY_MANIFEST.json").read_text())["domains"][dom]["jobs_sha256"]
    (P3 / "cache").mkdir(exist_ok=True)
    cf = P3 / "cache" / f"verify_{dom}.jsonl"
    env = {**os.environ, "ABF_ROOT": str(L_ / "root"), "V3OUT": str(P3 / "teach_out"), "FIN3D_CODE": str(L_ / "gen/final3d_v4/code"),
           "FIN3D_SRC": str(L_ / "gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass"), "FIN3D_STORE": str(P3 / "store3d"),
           "MUJOCO_GL": "disable", "OMP_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": ""}
    log = open(P3 / f"teach_{dom}.log", "a")
    def used():
        rows = jl(cf) if cf.exists() else []
        return sum(r.get("cpu_s", 0) for r in rows), {(r["root"], json.dumps(x["seq"])) for r in rows for x in r["results"]}
    cpu, have = used()
    todo = [j for j in jobs if any((j["root_id"], json.dumps([[j["ids"].index(o), c] for o, c in s])) not in have for s in j["seqs"])][: first or None]
    head = workers * (900 if dom == "2d" else 300)
    i = 0
    while i < len(todo):
        batch, n = [], 0
        while i < len(todo) and (not batch or n + len(todo[i]["seqs"]) <= batch_q):
            batch.append(todo[i]); n += len(todo[i]["seqs"]); i += 1
        cpu, have = used()
        per = cpu / max(1, len(have)) if have else (27.0 if dom == "2d" else 35.0)
        if cpu + per * n + head > CAP_H[dom] * 3600:
            log.write(f"{time.strftime('%FT%TZ', time.gmtime())} STOP_CAP cpu={cpu:.0f}s\n"); log.flush(); break
        bf = P3 / f"batch_{dom}.jsonl"
        with open(bf, "w") as f:
            for j in batch:
                f.write(json.dumps(j) + "\n")
        log.write(f"{time.strftime('%FT%TZ', time.gmtime())} BATCH roots={len(batch)} queries={n} tiers={sorted({j['tier'] for j in batch})} cpu={cpu:.0f}s\n"); log.flush()
        subprocess.run(["nice", "-n", "10", str(L_ / f"env{dom}" / "bin" / "python"), "benchmark.py", "teach", dom, str(bf), str(P3 / "cache"), str(workers), str(cpu0)],
                       cwd=ABF, env=env, stdout=log, stderr=log, check=True)
    cpu, have = used()
    print(json.dumps({"dom": dom, "cpu_h": round(cpu / 3600, 3), "queries_done": len(have)}))



# ------------------------------------------------------------------------------------------------ P4 analysis
def outcome(led, rid, x, conv):
    """-> (class, joint) for one arm decision.  class: SUCCESS / FAIL / UNKNOWN / UNQUERIED / NOOP / ABSTAIN; joint e.g. X1Y0, X?Y1."""
    if x is None or x.get("decision") in (None, "ABSTAIN"):
        return "ABSTAIN", None
    if x["decision"] == "NOOP":
        return "NOOP", None
    seq = x["seq"]
    if not led.queried(rid, seq):
        return "UNQUERIED", None
    xv, yv, z, _, _ = led.get(rid, seq, conv)
    j = f"X{'?' if xv is None else xv}Y{'?' if yv is None else yv}"
    return ("SUCCESS" if z == 1 else "FAIL" if z == 0 else "UNKNOWN"), j


def analyze():
    import numpy as np
    import labels as L
    import ordering as O
    import stats as ST
    per, res = [], {"domains": {}, "primary": []}
    for dom in DOMS:
        ros = roster(dom)
        led = L.Ledger(dom, set(ros))
        P = {p["root_id"]: p for p in jl(RUNS / f"pred_{dom}.jsonl")}
        for rid, p in P.items():
            e = ros[rid]
            y0 = led.Y.get((rid, "[]"))
            for kind in ("arms", "rank_only"):
                for a in ("J", "X", "Y", "XC"):
                    x = p[kind][a]
                    if kind == "rank_only":
                        x = {"decision": "REPAIR", "seq": x["seq"]} if x else None
                    cs, js = outcome(led, rid, x, "strict")
                    co, jo = outcome(led, rid, x, "oper")
                    seq = x["seq"] if x and x.get("decision") == "REPAIR" else None
                    row = {"domain": dom, "root_id": rid, "K": e["K"], "family": e["parent_family_id"], "arm": a, "kind": kind,
                           "decision": None if x is None else x["decision"], "seq": seq, "len": len(seq) if seq else 0,
                           "strict": cs, "joint": js, "oper": co, "y_empty": y0["strict"] if y0 else None, "n_pool": p["n_pool"]}
                    if e["K"] in ("1", "2", "3"):
                        row["verified"] = int(cs == "SUCCESS"); row["verified_oper"] = int(co == "SUCCESS")
                    elif e["K"] == "0":
                        row["correct"] = (int(row["decision"] == "NOOP") if row["y_empty"] == 1 else None)
                    else:
                        row["correct"] = int(row["decision"] == "ABSTAIN")
                    per.append(row)
        D = {"arms": {}, "contrasts": {}}
        for kind in ("arms", "rank_only"):
            for a in ("J", "X", "Y", "XC"):
                X_ = [r for r in per if r["domain"] == dom and r["arm"] == a and r["kind"] == kind]
                A = {}
                for g, Ks in (("K1", "1"), ("K2", "2"), ("K3", "3"), ("K1-3", "123")):
                    Y_ = [r for r in X_ if r["K"] in Ks and r["K"] not in ("0", "NONE")]
                    c = collections.Counter(r["strict"] for r in Y_)
                    N = len(Y_)
                    unk, unq = c["UNKNOWN"], c["UNQUERIED"]
                    A[g] = {"N": N, "verified_pct": round(100 * c["SUCCESS"] / N, 2), "unknown_pct": round(100 * unk / N, 2), "unqueried_pct": round(100 * unq / N, 2),
                            "upper_pct": round(100 * (c["SUCCESS"] + unk + unq) / N, 2), "decided_only_pct": round(100 * c["SUCCESS"] / max(1, N - unk - unq), 2),
                            "oper_pct": round(100 * sum(r["verified_oper"] for r in Y_) / N, 2), "classes": dict(c),
                            "joint": dict(collections.Counter(r["joint"] for r in Y_ if r["joint"])), "mean_len": round(float(np.mean([r["len"] for r in Y_ if r["len"]] or [0])), 3)}
                for g, K in (("K0", "0"), ("NONE", "NONE")):
                    Y_ = [r for r in X_ if r["K"] == K]
                    ev = [r for r in Y_ if r["correct"] is not None]
                    A[g] = {"N": len(Y_), "evaluable": len(ev), "correct_pct": round(100 * np.mean([r["correct"] for r in ev]), 2) if ev else None,
                            "repairs": sum(r["decision"] == "REPAIR" for r in Y_), "repair_success": sum(r["strict"] == "SUCCESS" for r in Y_)}
                D["arms"][f"{kind}:{a}"] = A
        vals = lambda kind, a, f="verified": {r["root_id"]: (r["K"], r["family"], r[f]) for r in per if r["domain"] == dom and r["kind"] == kind and r["arm"] == a and r["K"] in ("1", "2", "3")}  # noqa: E731
        for kind, a, b in (("arms", "J", "X"), ("arms", "J", "Y"), ("arms", "J", "XC"), ("arms", "Y", "X"), ("rank_only", "J", "X"), ("rank_only", "J", "Y")):
            ck = f"{kind}:{a}-{b}"
            D["contrasts"][ck] = {"strict": ST.paired(vals(kind, a), vals(kind, b)), "operational": ST.paired(vals(kind, a, "verified_oper"), vals(kind, b, "verified_oper"), n_perm=2000)}
            for K in "123":
                D["contrasts"][ck][f"K{K}"] = ST.paired({k: v for k, v in vals(kind, a).items() if v[0] == K}, {k: v for k, v in vals(kind, b).items() if v[0] == K}, n_perm=2000)
            if kind == "arms" and b in ("X", "Y"):
                res["primary"].append({"domain": dom, "contrast": f"J-{b}", **D["contrasts"][ck]["strict"],
                                       "max_unknown_pct": max(D["arms"][f"arms:{z}"]["K1-3"]["unknown_pct"] for z in (a, b)),
                                       "min_evaluable_pct": min(100 - D["arms"][f"arms:{z}"]["K1-3"]["unqueried_pct"] for z in (a, b))})
        # ---- O-B panel
        led_p = led
        panel_rows = []
        for x in jl(RUNS / f"panel_scores_{dom}.jsonl"):
            rid = x["root_id"]
            orders = [json.loads(k) for k in x["scores"]]
            xl = {k: led_p.get(rid, json.loads(k))[0] if led_p.queried(rid, json.loads(k)) else None for k in x["scores"]}
            yv = led_p.Y.get((rid, L.ekey(orders[0])))
            gm = O.group(x["assignment"], {k: v["px1"] for k, v in x["scores"].items()}, xl)
            gx = O.group(x["assignment"], {k: v["px"] for k, v in x["scores"].items()}, xl)
            queried = sum(led_p.queried(rid, q) for q in orders)
            panel_rows.append({"root_id": rid, "family": ros[rid]["parent_family_id"], "K": ros[rid]["K"], "m": x["m"], "y": yv["strict"] if yv else None,
                               "queried_orders": queried, **{f"pX1_{k}": v for k, v in gm.items()}, "pX_learned_x": gx["learned_x"], "py_range": x["py_range"]})
        PN = {}
        for m in (2, 3, "all"):
            G = [g for g in panel_rows if m == "all" or g["m"] == m]
            Y1c = [g for g in G if g["y"] == 1 and g["pX1_complete"]]
            mix = [g for g in G if g["pX1_mixed"]]
            fams = lambda gs: [g["family"] for g in gs]  # noqa: E731
            PN[str(m)] = {"assignments": len(G), "families": len(set(fams(G))), "y1": sum(g["y"] == 1 for g in G), "y0": sum(g["y"] == 0 for g in G),
                          "complete": sum(g["pX1_complete"] for g in G), "complete_y1": len(Y1c), "mixed": len(mix), "mixed_families": len(set(fams(mix))),
                          "all_pos": sum(g["pX1_complete"] and g["pX1_n_neg"] == 0 for g in G), "all_neg": sum(g["pX1_complete"] and g["pX1_n_pos"] == 0 for g in G),
                          "concordance_pX1": ST.cluster_mean([g["pX1_concordance"] for g in mix], fams(mix)),
                          "y1_learned": ST.cluster_mean([g["pX1_learned_x"] for g in Y1c], fams(Y1c)),
                          "y1_pX_learned": ST.cluster_mean([g["pX_learned_x"] for g in Y1c], fams(Y1c)),
                          "y1_canonical": ST.cluster_mean([g["pX1_canonical_x"] for g in Y1c], fams(Y1c)),
                          "y1_random": ST.cluster_mean([g["pX1_random_x"] for g in Y1c], fams(Y1c)),
                          "y1_oracle": ST.cluster_mean([g["pX1_oracle_any"] for g in Y1c], fams(Y1c)),
                          "y1_learned_minus_canonical": ST.cluster_mean([g["pX1_learned_x"] - g["pX1_canonical_x"] for g in Y1c], fams(Y1c)),
                          "y1_learned_minus_random": ST.cluster_mean([g["pX1_learned_x"] - g["pX1_random_x"] for g in Y1c], fams(Y1c)),
                          "all_roster_learned_verified": round(float(np.mean([g["pX1_learned_x"] == 1 for g in G])), 4) if G else None,
                          "chosen_order_unknown": sum(g["pX1_learned_x"] is None for g in G),
                          "random_bounds_mean": [round(float(np.mean([g["pX1_random_bounds"][0] for g in G])), 4), round(float(np.mean([g["pX1_random_bounds"][1] for g in G])), 4)] if G else None,
                          "top_differs_from_canonical": sum(g["pX1_top_differs_from_canonical"] for g in G), "py_range_max": max((g["py_range"] for g in G), default=None)}
        PN["adequate_for_primary"] = PN["all"]["mixed"] >= 10 and PN["all"]["mixed_families"] >= 10
        D["panel"], D["panel_rows"] = PN, panel_rows
        res["domains"][dom] = D
    adj = ST.holm([x["p_perm"] for x in res["primary"]])
    for x, a in zip(res["primary"], adj):
        x["p_holm"] = round(a, 5)
        x["verdict"] = ("INCONCLUSIVE (UNKNOWN > 20 %)" if x["max_unknown_pct"] > 20 else "INCONCLUSIVE (< 90 % evaluable)" if x["min_evaluable_pct"] < 90 else
                        "ESTABLISHED: J better" if a < 0.05 and x["ci95_pp"][0] > 0 else "ESTABLISHED: J worse" if a < 0.05 and x["ci95_pp"][1] < 0 else
                        "NO ESTABLISHED DIFFERENCE")
    with open(REP / "P4_PER_ROOT.jsonl", "w") as f:
        for r in per:
            f.write(json.dumps(r) + "\n")
    wj("P4_STATS.json", res)
    for x in res["primary"]:
        print(x["domain"], x["contrast"], x["delta_pp"], x["ci95_pp"], "p", round(x["p_perm"], 5), "holm", x["p_holm"], "unk", x["max_unknown_pct"], x["verdict"])


if __name__ == "__main__":
    c, args = sys.argv[1], sys.argv[2:]
    fn = {"audit": audit, "panel": panel, "parity": parity, "dev": dev, "infer": infer, "panel_score": panel_score, "seal": seal, "manifest": manifest, "analyze": analyze,
          "teach": lambda d, f=None: teach(d, int(f) if f else None)}[c]
    fn(*args)
