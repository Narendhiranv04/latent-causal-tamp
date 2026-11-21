#!/usr/bin/env python3
"""AUDIT-ONLY diagnostics for recursive_kgt3 (no implementation; no TEST data; no physics; frozen weights untouched).
Inputs: historical VAL 2D fixtures (public inputs + recorded frozen predictions) and SYNTHETIC scenes built from them.  Never reads
release_v2 (public or private).  Every check prints one JSON line; the full report is written to OUT.
  C1  frozen K<=3 replay parity on the first N VAL roots (proposals, decision, moves, p11, p_noop) vs the recorded GPU predictions
  C2  dynamic object padding: (a) n<=20 proposals identical with/without the narrow fix; (b) unpatched IndexError at n=25/27/28;
      (c) patched proposals finite/legal/top-4 at n=25/27/28 (synthetic scenes)
  C3  Y-only endpoint parity on <=3 edits: py from the X path (Scorer.score) == py from make_view(y_edits=[E], x_seqs=[]); and the
      rebased-root no-op p_noop(E as new S0) vs py(E | S0) gap
  C4  Y-only endpoint with 4..12 edits on a synthetic 28-object scene: finite outputs; moved_count/3 feature value (OOD)
  C5  output semantics: p11 == psucc == py[parent]*sigmoid(a+w); px (marginal) vs conditional p1 = psucc/py
  C6  retarget leak: after validation_k3.retarget(tid=A, goal=d_A) the ORIGINAL target is movable and the ORIGINAL goal is a legal destination
  C7  K<=3 candidate counts (exact construct.counts) on VAL roots and on synthetic 25/27/28-object scenes (proposals only, no scoring)
    python audit_checks.py --n 25 --device cuda --out audit_checks.json"""
import argparse, copy, json, math, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
VAL_IN = Path.home() / "abf_v34/parity/public_val_2d.jsonl"
VAL_PRED = Path.home() / "abf_v34/parity/pred_val_2d_gpu.jsonl"
BUNDLE = Path.home() / "abf_v34/approach_b_bundle"


def jl(p):
    return [json.loads(l) for l in open(p)]


class DynPad:
    """The proposed narrow fix: placement.scene_features allocates max(MAXOBJ[dom], n_objects) rows (identical code path for n <= MAXOBJ)."""
    def __init__(self, PL):
        self.PL, self.orig = PL, PL.scene_features

    def __enter__(self):
        PL, orig = self.PL, self.orig

        def sf(dom, pattr, cd, query, legal, *a, **k):
            n, base = len(cd), PL.MAXOBJ[dom]
            if n <= base:
                return orig(dom, pattr, cd, query, legal, *a, **k)
            PL.MAXOBJ[dom] = n
            try:
                return orig(dom, pattr, cd, query, legal, *a, **k)
            finally:
                PL.MAXOBJ[dom] = base
        PL.scene_features = sf
        return self

    def __exit__(self, *e):
        self.PL.scene_features = self.orig


def synth(row, n_total, seed=0):
    """Synthetic scene: the VAL root plus extra obstacles (radius 0.024) on free legal non-goal cells, deterministic order."""
    import random
    r = copy.deepcopy(row)
    i = r["inputs"]
    free = [c for c in i["legal_cells"] if c not in set(i["cells0"]) and c != i["goal_cell"]]
    random.Random(f"SYN|{row['root_id']}|{n_total}|{seed}").shuffle(free)
    j = 0
    while len(i["ids"]) < n_total:
        c = free[j]; j += 1
        i["ids"].append(f"x{j:02d}"); i["attrs"].append([0.024, 0.0, 1.0, 0.0]); i["cells0"].append(c); i["xy0"].append(list(i["cell_xy"][str(c)]))
    r["root_id"] = f"{row['root_id']}~SYN{n_total}"
    return r


def main(n, device, out):
    import numpy as np
    import torch
    import benchmark as BM
    import exhaustive as EX
    import construct as CO
    import placement as PL
    import search as S
    import xy as XY
    R = {}
    rows = jl(VAL_IN)[:n]
    ref = {r["root_id"]: r for r in jl(VAL_PRED)}
    samp, scor, man = BM.load_bundle(BUNDLE, "2d", device, 0)
    cfg = man["config"]
    # ---------------- C1 replay parity
    t0, res = time.time(), []
    for r in rows:
        root = S.Root(r, "2d")
        D6 = EX.proposals(root, samp, cfg["proposal_seed"])
        rec = EX.score_root(root, D6, scor, [cfg["rule"]], cfg["M"], set(), cfg["chunk"])
        d = rec["per_M"][str(cfg["M"])]["decisions"][0]
        kind = "ABSTAIN" if d is None else "NOOP" if d["seq"] == [] else "REPAIR"
        moves = [[root.ids[o], c] for o, c in (d["seq"] if kind == "REPAIR" else [])]
        g = ref[r["root_id"]]
        props = {str(o): v[:4] for o, v in D6.items()}
        res.append({"root": r["root_id"], "dec": kind == g["decision"], "moves": moves == [[m["object_id"], m["destination_cell"]] for m in g["moves"]],
                    "props": all(props.get(k) == v for k, v in g["proposals"].items()),
                    "dp11": abs((d["p11"] if d else 0) - (g["score_p11"] or 0)), "dpnoop": abs(rec["p_noop"] - g["p_noop"]), "n_scored": g["n_scored"]})
    R["C1"] = {"n": len(res), "decision_equal": sum(x["dec"] for x in res), "moves_equal": sum(x["moves"] for x in res),
               "proposals_equal": sum(x["props"] for x in res), "max_dp11": max(x["dp11"] for x in res), "max_dpnoop": max(x["dpnoop"] for x in res),
               "wall_s": round(time.time() - t0, 1), "device": device, "torch": torch.__version__}
    print(json.dumps({"C1": R["C1"]}), flush=True)
    # ---------------- C2 dynamic padding
    same = 0
    for r in rows:                                     # strict: unpatched vs patched, compared as plain dicts
        root = S.Root(r, "2d")
        a = EX.proposals(root, samp, cfg["proposal_seed"])
        with DynPad(PL):
            b = EX.proposals(root, samp, cfg["proposal_seed"])
        same += int(a == b)
    syn = {}
    for nt in (25, 27, 28):
        sr = synth(rows[0], nt)
        root = S.Root(sr, "2d")
        try:
            EX.proposals(root, samp, cfg["proposal_seed"]); err = None
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:80]}"
        with DynPad(PL):
            D = EX.proposals(root, samp, cfg["proposal_seed"])
        legal = set(root.legal_dests(root.cells0))
        syn[nt] = {"unpatched_error": err, "movers": len(root.movable), "all_have_top4": all(len(v[:4]) == 4 for v in D.values()),
                   "all_legal": all(set(v) <= legal for v in D.values()), "free_legal_cells": len(legal),
                   "K3_candidates_M4": CO.counts({o: v[:4] for o, v in D.items()}) if hasattr(CO, "counts") else None}
    R["C2"] = {"n_le20_identical": f"{same}/{len(rows)}", "synthetic": syn}
    print(json.dumps({"C2": R["C2"]}), flush=True)
    # ---------------- C3 / C5 Y-only endpoint parity, rebased gap, semantics
    net = scor.net
    c3, c5 = [], []
    for r, g in ((r, ref[r["root_id"]]) for r in rows):
        if g["decision"] != "REPAIR":
            continue
        inp = r["inputs"]
        seq = [(m["object_index"], m["destination_cell"]) for m in g["moves"]]
        P = lambda c: tuple(inp["cell_xy"][str(c)])  # noqa: E731
        v, ym, xm = XY.make_view(r["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"],
                                 [{i: P(d) for i, d in seq}], [[(i, P(d)) for i, d in seq]], XY._NoGeo)
        b, _ = XY.collate([v], device=device, dtype=torch.float32)
        with torch.no_grad():
            pr = net.predict(b)
        q = xm[0]; par = v["parent"][q]
        py_x, py_y = float(pr["py"][par]), float(pr["py"][ym[0]])
        vy, ym2, _ = XY.make_view(r["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"],
                                  [{i: P(d) for i, d in seq}], [], XY._NoGeo)                  # Y-only: no X sequence at all
        by, _ = XY.collate([vy], device=device, dtype=torch.float32)
        with torch.no_grad():
            pry = net.predict(by)
        py_only = float(pry["py"][ym2[0]])
        e = copy.deepcopy(inp)                                                                  # rebased root: S0 := endpoint E
        for i, d in seq:
            e["xy0"][i] = list(P(d)); e["cells0"][i] = d
        vr, _, _ = XY.make_view(r["root_id"] + "~R", e["xy0"], e["attrs"], e["tid"], e["goal"], e["base"], e["ctx"], [], [], XY._NoGeo)
        br, _ = XY.collate([vr], device=device, dtype=torch.float32)
        with torch.no_grad():
            prr = net.predict(br)
        p_reb = float(prr["p_noop"][0])
        sc = scor.score(S.Root(r, "2d"), [seq])[0]
        c3.append({"k": len(seq), "py_xpath": py_x, "py_shared_node": py_y, "py_yonly": py_only, "py_scorer": sc["py"], "p_noop_rebased": p_reb})
        p1 = float(pr["psucc"][q]) / max(py_x, 1e-12)
        c5.append({"p11": float(pr["psucc"][q]), "py": py_x, "px_marginal": float(pr["px"][q]), "pX_given_Y": p1, "p11_scorer": sc["p11"]})
    R["C3"] = {"n": len(c3), "max_abs_yonly_minus_xpath": max(abs(x["py_yonly"] - x["py_xpath"]) for x in c3),
               "max_abs_scorer_minus_xpath": max(abs(x["py_scorer"] - x["py_xpath"]) for x in c3),
               "rebased_gap_abs_mean": float(np.mean([abs(x["p_noop_rebased"] - x["py_yonly"]) for x in c3])),
               "rebased_gap_abs_max": max(abs(x["p_noop_rebased"] - x["py_yonly"]) for x in c3), "rows": c3[:6]}
    R["C5"] = {"n": len(c5), "max_abs_p11_minus_scorer": max(abs(x["p11"] - x["p11_scorer"]) for x in c5),
               "px_marginal_minus_pXgivenY_mean": float(np.mean([x["px_marginal"] - x["pX_given_Y"] for x in c5])), "rows": c5[:6]}
    print(json.dumps({"C3": {k: v for k, v in R["C3"].items() if k != "rows"}, "C5": {k: v for k, v in R["C5"].items() if k != "rows"}}), flush=True)
    # ---------------- C4 Y-only with 4..12 edits on a synthetic 28-object scene
    sr = synth(rows[0], 28)
    inp = sr["inputs"]
    root = S.Root(sr, "2d")
    free = root.legal_dests(root.cells0)
    c4 = []
    for k in (1, 2, 3, 4, 6, 9, 12):
        ed = {o: tuple(inp["cell_xy"][str(free[j])]) for j, o in enumerate(root.movable[:k])}
        v, ym, _ = XY.make_view(sr["root_id"], inp["xy0"], inp["attrs"], inp["tid"], inp["goal"], inp["base"], inp["ctx"], [ed], [], XY._NoGeo)
        b, _ = XY.collate([v], device=device, dtype=torch.float32)
        with torch.no_grad():
            pr = net.predict(b)
        val = float(pr["py"][ym[0]])
        c4.append({"edits": k, "py": val, "finite": math.isfinite(val), "moved_count_feature": round(k / 3.0, 3)})
    R["C4"] = c4
    print(json.dumps({"C4": c4}), flush=True)
    # ---------------- C6 retarget leak
    sys.path.insert(0, str(Path(__file__).resolve().parents[0] / "_vendor_audit"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("retarget_audit", VENDOR_RETARGET)
    RT = importlib.util.module_from_spec(spec); spec.loader.exec_module(RT)
    leaks = []
    for r in rows:
        inp = r["inputs"]
        root = S.Root(r, "2d")
        A = root.movable[0]
        dA = root.legal_dests(root.cells0)[0]
        new = {**r, "inputs": RT.retarget(inp, "2d", A, dA)}
        rt = S.Root(new, "2d")
        leaks.append({"orig_target_movable": inp["tid"] in rt.movable, "orig_goal_legal": inp["goal_cell"] in rt.legal_dests(rt.cells0),
                      "identity_exact": RT.retarget(inp, "2d", inp["tid"], inp["goal_cell"]) == inp})
    R["C6"] = {"n": len(leaks), "orig_target_movable": sum(x["orig_target_movable"] for x in leaks), "orig_goal_legal": sum(x["orig_goal_legal"] for x in leaks),
               "identity_exact": sum(x["identity_exact"] for x in leaks)}
    print(json.dumps({"C6": R["C6"]}), flush=True)
    # ---------------- C7 counts on VAL
    R["C7_val_n_scored"] = {"min": min(ref[r["root_id"]]["n_scored"] for r in rows), "max": max(ref[r["root_id"]]["n_scored"] for r in rows),
                            "mean": float(np.mean([ref[r["root_id"]]["n_scored"] for r in rows])),
                            "objects": [len(r["inputs"]["ids"]) for r in rows]}
    Path(out).write_text(json.dumps(R, indent=1))
    print(json.dumps({"written": out}))


VENDOR_RETARGET = None
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", default="audit_checks.json")
    ap.add_argument("--retarget", required=True, help="read-only copy of naren/k3-postablation-validation validation_k3/retarget.py")
    a = ap.parse_args()
    VENDOR_RETARGET = a.retarget
    main(a.n, a.device, a.out)
