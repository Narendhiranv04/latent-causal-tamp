#!/usr/bin/env python3
"""R2.1 model-only diagnostics on EXACT labels (evaluator side: labels are joined only after the frozen readouts; no planner, no cVAE in P1/P2).
    python scorer.py readout DOM OUT_DIR        P1/P2 readouts for the whole pool (pX, pX1, pX0, p11, pY of the endpoint, Y_global, Y_rebased)
    python scorer.py c3b DOM OUT_DIR            P3: C3b temporary-target panel (TT_ADAPTER_V1 labels) + admission analysis
    python scorer.py staged DOM OUT_DIR N       H_C: staged vs exhaustive group recall on N VAL roots (model-only)
    python scorer.py k45 OUT_DIR                3D m = 4/5 OOD control on the K4/K5 cohort (archived exact labels)"""
from __future__ import annotations

import collections, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
import common as C  # noqa: E402
import views as V  # noqa: E402
from models import Frozen  # noqa: E402


def readout(dom, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = C.snapshot_rows(dom)
    train_ids = {r["root_id"] for r in C.snapshot_rows(dom, ("train",), C.SNAP_TRAIN).values()}
    insnap = set()
    for r in C.snapshot_rows(dom, ("train",), C.SNAP_TRAIN).values():
        for q in r["labels"]["X"]:
            insnap.add(("X", r["root_id"], json.dumps([list(map(int, a)) for a in q["seq"]])))
        for y in r["labels"]["Y"]:
            insnap.add(("Y", r["root_id"], json.dumps(sorted([list(map(int, a)) for a in y["edit"]]))))
    P = C.pool(dom)
    byroot = collections.defaultdict(lambda: {"X": [], "Y": []})
    for e in P:
        byroot[e["root"]][e["t"]].append(e)
    fz = Frozen(dom)
    t0 = time.time()
    with open(out / f"P1_{dom}.jsonl", "w") as f:
        for i, (rid, L) in enumerate(sorted(byroot.items())):
            r = rows.get(rid)
            if r is None:
                continue
            fz.reset()
            row = {"root_id": rid, "domain": dom, "inputs": r["inputs"]}
            N = len(r["inputs"]["ids"]); fam = r["parent_family_id"]; split = r["split"]
            Yl = {json.dumps(sorted([list(map(int, a)) for a in e["edit"]])): e["y"] for e in L["Y"]}
            xs = [[list(map(int, a)) for a in e["seq"]] for e in L["X"]]
            sc = fz.score(row, xs) if xs else []
            for e, s, x in zip(L["X"], xs, sc):
                k = json.dumps(sorted(s))
                f.write(json.dumps({"t": "X", "root": rid, "fam": fam, "split": split, "N": N, "m": len(s), "seq": s, "x": e["x"], "status": e["status"],
                                    "y_end": Yl.get(k), "fit": ("X", rid, json.dumps(s)) in insnap, **{k2: round(v, 6) for k2, v in x.items()}}) + "\n")
            eds = [[list(map(int, a)) for a in e["edit"]] for e in L["Y"]]
            yg = fz.y_global(row, eds) if eds else []
            for e, ed, pg in zip(L["Y"], eds, yg):
                yr = fz.p_noop(V.rebase(row, ed)) if ed else pg                  # rebased endpoint: fresh-root no-op readout
                f.write(json.dumps({"t": "Y", "root": rid, "fam": fam, "split": split, "N": N, "h": len(ed), "edit": ed, "y": e["y"],
                                    "fit": ("Y", rid, json.dumps(sorted(ed))) in insnap, "py_global": round(pg, 6), "py_rebased": round(yr, 6)}) + "\n")
            if i % 500 == 0:
                print(dom, i, len(byroot), round(time.time() - t0, 1), flush=True)
    print("READOUT_DONE", dom, round(time.time() - t0, 1), fz.dev)


def c3b(dom, out):
    """C3b blocked temporary tasks: recompute frozen readouts on retargeted views (fig3 views.rebase; parity vs tt_retarget_ref checked)."""
    import tt_retarget_ref as RT
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    T = C.NW / "k3val/runs/out/ttarget"
    E = json.loads((T / f"EXAMPLES_{dom}_b.json").read_text()); R = json.loads((T / f"TT_{dom}_b.json").read_text())["rows"]
    rows = C.snapshot_rows(dom, ("val",))
    fz = Frozen(dom)
    res, parity_bad = [], 0
    for e, r in zip(E, R):
        row0 = {"root_id": e["root_id"], "domain": dom, "inputs": rows[e["root_id"]]["inputs"]}
        A, dA = int(e["A"]), int(e["dA"])
        Tv = V.rebase(row0, [], task=(A, dA))
        ref = RT.retarget(row0["inputs"], dom, A, dA)
        if any(json.dumps(Tv["inputs"][k]) != json.dumps(ref[k]) for k in ref if k != "legal_cells"):
            parity_bad += 1
        P = [[int(o), int(d)] for o, d in e["P"]]
        singles = [[[int(o), int(d)]] for o, d in e["single"]]
        cands = [[]] + ([P] if P else []) + singles
        fz.reset()
        sc = fz.score(Tv, cands)
        noop = sc[0]["p11"]
        lab = [{"group": [], "y": r["y_tt_S0"], "x": 1}] + ([{"group": P, "x": r["xy_tt_P"][0], "y": r["xy_tt_P"][1]}] if P else [])
        lab += [{"group": s, "x": r["single"][f"{s[0][0]}>{s[0][1]}"]["x"], "y": r["single"][f"{s[0][0]}>{s[0][1]}"]["y"]} for s in singles]
        # original-task context readouts of the same groups (no retargeting) for the T comparison
        so = fz.score(row0, cands)
        cand_out = []
        for g, l, s, s0 in zip(cands, lab, sc, so):
            cand_out.append({**l, "py": s["py"], "p11": s["p11"], "px": s["px"], "dpy": s["py"] - noop if g else 0.0,
                             "admit_beats_empty": bool(g) and s["py"] > noop, "py_origctx": s0["py"], "p11_origctx": s0["p11"]})
        res.append({"root_id": e["root_id"], "fam": rows[e["root_id"]]["parent_family_id"], "N": len(row0["inputs"]["ids"]), "K": e["K"], "A": A, "dA": dA,
                    "P": P, "y_tt_S0": r["y_tt_S0"], "py_noop": noop, "cands": cand_out})
    (out / f"P3_c3b_{dom}.json").write_text(json.dumps({"dom": dom, "n": len(res), "retarget_parity_failures": parity_bad, "rows": res}, indent=1))
    print("C3B_DONE", dom, len(res), "parity_bad", parity_bad)


def staged(dom, out, n):
    """H_C: recall of the exhaustive top-k (by S0 p11) inside the staged beam, by N bin, on VAL roots (sha order)."""
    import recursive as RC
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = sorted(C.snapshot_rows(dom, ("val",)).values(), key=lambda r: C.h("R2_STAGED|" + r["root_id"]))
    fz = Frozen(dom)
    res = []
    for r in rows:
        if len(res) >= int(n):
            break
        row = {"root_id": r["root_id"], "domain": dom, "inputs": r["inputs"]}
        fz.reset()
        ctx = RC.Ctx(fz, row, "R-FIG3", {"m_max": 3, "x_unique": 10 ** 9})
        ex = RC.local_groups(ctx, row, [], [], [], 3, exhaustive=True)
        if not ex:
            continue
        sx = fz.score(row, ex)
        top = [json.dumps(g) for g, _ in sorted(zip(ex, sx), key=lambda t: -t[1]["p11"])[:8]]
        ctx2 = RC.Ctx(fz, row, "R-FIG3", {"m_max": 3, "exhaustive_max_groups": 0, "x_unique": 10 ** 9})
        st = {json.dumps(g) for g in RC.local_groups(ctx2, row, [], [], [], 3)}
        res.append({"root": r["root_id"], "fam": r["parent_family_id"], "N": len(r["inputs"]["ids"]), "n_exhaustive": len(ex), "n_staged": len(st),
                    "top1_in_staged": top[0] in st, "top8_recall": sum(t in st for t in top) / len(top)})
    (out / f"H_C_staged_{dom}.json").write_text(json.dumps(res, indent=1))
    print("STAGED_DONE", dom, len(res))


def k45(out):
    """3D m = 4/5 OOD control: archived exact K4/K5 cohort labels (continuous / chunked witness orders) vs frozen direct readouts."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    pub = {json.loads(l)["root_id"]: json.loads(l) for l in open(C.FIG3 / "runs/PUBLIC.jsonl")}
    fz = Frozen("3d")
    res = []
    for f in ("eval_primary.jsonl", "eval_oracle.jsonl"):
        for l in open(C.NW / "k45/eval" / f):
            e = json.loads(l)
            if e.get("censored") or e.get("error") or e["root_id"] not in pub or "X" not in e:
                continue
            row = pub[e["root_id"]]
            parts = e["key"].split("|")
            try:
                order = json.loads(parts[2]) if len(parts) > 2 else None
            except ValueError:
                order = None
            if not order:
                continue
            ids = row["inputs"]["ids"]
            seq = [[ids.index(o), int(d[0]) * 6 + int(d[1])] for o, d in order]
            fz.reset()
            s = fz.score(row, [seq])[0]
            res.append({"key": e["key"], "root": e["root_id"], "N": len(ids), "m": len(seq), "mode": e.get("mode"), "x": e["X"].get("x"),
                        "y": (e.get("Y") or {}).get("y"), "phase": e["X"].get("phase"), **{k: round(v, 6) for k, v in s.items()}})
    (out / "OOD_k45_3d.json").write_text(json.dumps(res, indent=1))
    print("K45_DONE", len(res))


def variants(dom, out):
    """R2.1-A frozen readouts on every matched-N variant (views compiled from the perturbed raw records; +0 = original geometry, tag only)."""
    import contracts as CT
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    F = json.loads((C.R2 / "jobs" / f"families_{dom}.json").read_text())
    fz = Frozen(dom)
    res = []
    for f in F["families"]:
        levels = [{"k": "orig", "path": f["path"]}] + [{"k": v["k"], "path": v["path"]} for v in F["variants"] if v["root_id"] == f["root_id"] and v["built"]]
        for lv in levels:
            raw = json.loads(Path(lv["path"]).read_text())
            inp = (CT.view2d if dom == "2d" else CT.view3d)(raw)
            row = {"root_id": raw["ids"]["root_id"], "domain": dom, "inputs": inp}
            fz.reset()
            x = fz.score(row, [f["rep"]])[0]
            yg = fz.y_global(row, [[], f["neg"], f["rep"]])
            res.append({"fam": f["fam"], "root_id": f["root_id"], "k": lv["k"], "N": len(inp["ids"]), "p11_rep": x["p11"], "px_rep": x["px"], "pX1_rep": x["px1"],
                        "py_noop": yg[0], "py_neg": yg[1], "py_rep": yg[2], "py_rep_rebased": fz.p_noop(V.rebase(row, f["rep"]))})
    (out / f"variants_{dom}.json").write_text(json.dumps(res, indent=1))
    print("VARIANTS_DONE", dom, len(res))


def omission_readout(dom, out):
    """Frozen readouts for the omission groups (P minus one action) on the retargeted temporary-task view; labels joined later."""
    T = C.NW / "k3val/runs/out/ttarget"
    E = json.loads((T / f"EXAMPLES_{dom}_b.json").read_text()); R = json.loads((T / f"TT_{dom}_b.json").read_text())["rows"]
    rows = C.snapshot_rows(dom, ("val",)); fz = Frozen(dom); res = []
    for e, r in zip(E, R):
        if r["y_tt_S0"] != 0 or r["xy_tt_P"] != [1, 1] or len(e["P"]) < 2:
            continue
        row0 = {"root_id": e["root_id"], "domain": dom, "inputs": rows[e["root_id"]]["inputs"]}
        Tv = V.rebase(row0, [], task=(int(e["A"]), int(e["dA"])))
        P = [[int(o), int(d)] for o, d in e["P"]]
        groups = [[]] + [P] + [[p for j, p in enumerate(P) if j != i] for i in range(len(P))]
        fz.reset(); sc = fz.score(Tv, groups)
        res.append({"root": e["root_id"], "fam": rows[e["root_id"]]["parent_family_id"], "py_noop": sc[0]["py"], "py_P": sc[1]["py"], "p11_P": sc[1]["p11"],
                    "omit": [{"omit": i, "py": s["py"], "p11": s["p11"]} for i, s in enumerate(sc[2:])]})
    Path(out, f"omission_readout_{dom}.json").write_text(json.dumps(res, indent=1))
    print("OMISSION_READOUT_DONE", dom, len(res))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "readout":
        readout(sys.argv[2], sys.argv[3])
    elif c == "c3b":
        c3b(sys.argv[2], sys.argv[3])
    elif c == "staged":
        staged(sys.argv[2], sys.argv[3], sys.argv[4])
    elif c == "k45":
        k45(sys.argv[2])
    elif c == "omission":
        omission_readout(sys.argv[2], sys.argv[3])
    elif c == "variants":
        variants(sys.argv[2], sys.argv[3])
