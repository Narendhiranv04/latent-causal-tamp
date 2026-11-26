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


if __name__ == "__main__":
    c = sys.argv[1]
    {"audit": audit, "panel": panel}.get(c, lambda: None)() if c in ("audit", "panel") else parity(sys.argv[2])
