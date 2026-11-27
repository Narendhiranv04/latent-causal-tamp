#!/usr/bin/env python3
"""R4.4 3D deeper intermediate-state supervision + temporary-target pilot (collection only; no training).  Unchanged SHELF66V3 teacher
(fin3d A.query probes from q_ready on the settled scene; X_CHUNKED with q_ref connectors at declared bounds + independent replay; Y_TARGET).
Construction per fresh family (not consumed by KGT3; deterministic sha order):
  level 2 (as KGT3): B -> pB plans; BIG obstacle E at x (Chebyshev 1 of B) blocks it; E -> pE plans; B -> pB plans after E parked
  level 3 (new):     BIG obstacle F at y (Chebyshev 1 of x, not adjacent to B) blocks E -> pE; F -> pF plans; E -> pE plans after F parked
  prefixes:          two ordinary objects Z1, Z2 with destinations that plan in the family's initial scene (irrelevant relocations)
Job templates (X_CHUNKED, y = null; '|' = q_ref boundary): 1-, 2-, 3-action chunks at h0; 2-/3-action chunks after 1, 2 and 3 preceding
relocations incl. [Z1] | [F,E,B] and [F,E] | [B,Z1,Z2]; matched same-endpoint alternative permutations for every chunk.
Temporary-target physical interventions (Y_TARGET, target B, goal pB): baseline (E at x), beneficial (E parked), irrelevant (Z1 moved),
harmful (E parked, F moved onto x).  The learner never receives the dependency graph, blocker identities or witness orders.
    $PY3D deep3d.py construct WORKERS CPU_LO MAX_CPU_H NFAM   -> O/kgt3/r4/d3d/construct.jsonl
    $PY3D deep3d.py jobs                                      -> jobs.json (+ SEAL), rows.jsonl, recs/
    $PY3D physical3d.py work jobs.json phys.jsonl ...         (unchanged runner)
    $PYG  deep3d.py temp                                      -> temp_model.json (frozen Y / cVAE / recursive admission on verified E-enables-B)
    $PY3D deep3d.py analyze                                   -> R4_4_deep3d.json (coverage matrix, contrasts, interventions)"""
from __future__ import annotations

import collections, hashlib, itertools, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "r3"), str(HERE.parent / "r24"), str(HERE.parent.parent)]
import data2 as D2  # noqa: E402
OD = D2.O / "r4" / "d3d"
BIG = D2.BIG


def h(*a):
    return hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()


def construct_one(item):
    """One family -> {ok, level, rec | why, probes, cpu_s}.  Probes are fin3d A.query plan checks (construction queries, charged)."""
    EV = D2._boot3d() if not hasattr(construct_one, "EV") else construct_one.EV
    construct_one.EV = EV
    A = EV.W["F"].Q._M["A"]
    t0 = time.process_time(); n = {"probes": 0}
    rec = json.loads(Path(item["path"]).read_text())
    objs = [dict(o) for o in rec["objects"]]; cells = {k: tuple(v) for k, v in rec["initial_cells"].items()}
    goal = tuple(rec["goal"]); rid = item["root_id"]
    allc = [(r, c) for r in range(6) for c in range(6)]
    cheb = D2.cheb

    def plans(extra, ccells, name, dst):
        n["probes"] += 1
        e = A.build(objs + extra, {k: list(v) for k, v in ccells.items()}); A.settle(e, {k: list(v) for k, v in ccells.items()})
        return A.query(e, name, list(dst))[0] is not None
    srt = lambda xs, *k: sorted(xs, key=lambda x: h(*k, rid, x))  # noqa: E731
    ids = [o["id"] for o in objs]
    nid = lambda used: next(f"o{i:02d}" for i in range(len(objs), 99) if f"o{i:02d}" not in used)  # noqa: E731
    eid = nid(set(cells)); fid = nid(set(cells) | {eid})
    E = {**BIG, "id": eid, "color": "red"}; Fo = {**BIG, "id": fid, "color": "orange"}
    out = {"root_id": rid, "ok": False, "level": 0}
    try:
        occ = set(cells.values())
        free = [x for x in allc if x not in occ and x != goal]
        lvl2 = None
        for B in srt([o for o in ids if o != "t0"], "B")[:3]:
            pB = next((x for x in srt([x for x in free if cheb(x, cells["t0"]) >= 2 and cheb(x, cells[B]) >= 2], "pB", B)[:2] if plans([], cells, B, x)), None)
            if pB is None:
                continue
            for x in srt([x for x in free if cheb(x, cells[B]) == 1 and x != pB], "E", B)[:4]:
                c1 = {**cells, eid: x}
                if plans([E], c1, B, pB):
                    continue
                pE = next((y for y in srt([y for y in free if y not in (x, pB) and cheb(y, cells[B]) >= 2 and cheb(y, x) >= 2], "pE", B, x)[:2] if plans([E], c1, eid, y)), None)
                if pE is None or not plans([E], {**cells, eid: pE}, B, pB):
                    continue
                lvl2 = (B, pB, x, pE); break
            if lvl2:
                break
        if lvl2 is None:
            out["why"] = "NO_VERIFIED_LEVEL2"; raise StopIteration
        B, pB, x, pE = lvl2
        c1 = {**cells, eid: x}
        lvl3 = None
        for y in srt([y for y in free if cheb(y, x) == 1 and cheb(y, cells[B]) >= 2 and y not in (pB, pE)], "F", B, x)[:4]:
            c2 = {**c1, fid: y}
            if plans([E, Fo], c2, eid, pE):
                continue
            pF = next((z for z in srt([z for z in free if z not in (x, y, pB, pE) and cheb(z, x) >= 2 and cheb(z, cells[B]) >= 2], "pF", y)[:2] if plans([E, Fo], c2, fid, z)), None)
            if pF is None or not plans([E, Fo], {**c1, fid: pF}, eid, pE):
                continue
            lvl3 = (y, pF); break
        extra = [E] + ([Fo] if lvl3 else [])
        base = {**c1, **({fid: lvl3[0]} if lvl3 else {})}
        taken = {x, pB, pE} | ({lvl3[0], lvl3[1]} if lvl3 else set())
        Z = []
        for z in srt([o for o in ids if o not in ("t0", B)], "Z")[:4]:
            if len(Z) == 2:
                break
            cand = srt([d for d in free if d not in taken and cheb(d, cells[B]) >= 2 and cheb(d, x) >= 2], "pZ", z)[:1]
            if cand and plans(extra, base, z, cand[0]):
                Z.append((z, cand[0])); taken.add(cand[0])
        rec2 = {**rec, "objects": objs + extra, "initial_cells": {k: list(v) for k, v in base.items()},
                "ids": {**rec.get("ids", {}), "root_id": rid + "-R44"},
                "r44": {"parent_root": rid, "B": B, "pB": list(pB), "E": eid, "x": list(x), "pE": list(pE), "F": fid if lvl3 else None,
                        "y": list(lvl3[0]) if lvl3 else None, "pF": list(lvl3[1]) if lvl3 else None, "Z": [[z, list(d)] for z, d in Z]}}
        out = {"root_id": rid, "ok": True, "level": 3 if lvl3 else 2, "rec": rec2}
    except StopIteration:
        pass
    except Exception as e:  # noqa: BLE001
        out = {"root_id": rid, "ok": False, "level": 0, "why": f"ERROR {type(e).__name__}: {str(e)[:160]}"}
    out.update(probes=n["probes"], cpu_s=round(time.process_time() - t0, 1))
    return out


def families():
    used = {json.loads(l)["root_id"] for l in open(D2.O / "construct3d.jsonl")}
    usedf = {json.loads(l).get("fam") for l in open(D2.O / "construct3d.jsonl")}
    return [f for f in D2.families3d() if f["root_id"] not in used and f["fam"] not in usedf]


def construct(workers, cpu_lo, max_cpu_h, nfam):
    import multiprocessing as mp
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    OD.mkdir(parents=True, exist_ok=True)
    fams = sorted(families(), key=lambda f: h("R4.4", f["fam"]))[:int(nfam)]
    (OD / "roster.json").write_text(json.dumps([{"key": f["root_id"], "fam": f["fam"]} for f in fams], indent=1))
    outp = OD / "construct.jsonl"
    done = {json.loads(l)["root_id"] for l in open(outp)} if outp.exists() else set()
    cpu = sum(json.loads(l).get("cpu_s", 0) for l in open(outp)) if outp.exists() else 0.0
    todo = [f for f in fams if f["root_id"] not in done]
    pool = mp.get_context("spawn").Pool(int(workers), maxtasksperchild=6)
    running, f, i = {}, open(outp, "a"), 0
    while True:
        for k, (ar, fam, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k); r["fam"] = fam["fam"]; r["N"] = fam["N"]
                f.write(json.dumps(r) + "\n"); f.flush(); cpu += r["cpu_s"]
                print(time.strftime("%H:%M:%S"), r["root_id"], r["ok"], r["level"], r.get("why"), r["probes"], r["cpu_s"], round(cpu / 3600, 2), flush=True)
        live = (cpu + sum(time.time() - t for *_, t in running.values())) / 3600
        if i < len(todo) and len(running) < int(workers) and live < float(max_cpu_h):
            fam = todo[i]; i += 1; running[fam["root_id"]] = (pool.apply_async(construct_one, (fam,)), fam, time.time()); continue
        if not running:
            break
        time.sleep(1)
    pool.terminate()
    print("R44_CONSTRUCT_DONE", round(cpu / 3600, 3), "undispatched", len(todo) - i, flush=True)


def templates(kg, cell):
    B, E, F = (kg["B"], cell(kg["pB"])), (kg["E"], cell(kg["pE"])), (kg["F"], cell(kg["pF"])) if kg["F"] else None
    Z = [(z, cell(d)) for z, d in kg["Z"]]
    T = [("h0_g1_B", [B], [1]), ("h0_g1_E", [E], [1]), ("h0_g2", [E, B], [2]), ("h0_g2", [B, E], [2])]
    if F:
        T += [("h0_g1_F", [F], [1]), ("h0_g2_FE", [F, E], [2]), ("h0_g2_FE", [E, F], [2])]
        T += [("h0_g3", list(p), [3]) for p in itertools.permutations([F, E, B])]
        T += [("h1_g2", [F, E, B], [1, 3]), ("h1_g2", [F, B, E], [1, 3])]
    else:
        T += [("h1_g2_EB", [E, B], [1, 2])]
    if Z:
        z1 = Z[0]
        if F:
            T += [("h1_g3", [z1, F, E, B], [1, 4]), ("h1_g3", [z1, E, F, B], [1, 4]), ("h1_g3", [z1, F, B, E], [1, 4]),
                  ("h1_g2_FE", [z1, F, E], [1, 3]), ("h1_g2_FE", [z1, E, F], [1, 3])]
        else:
            T += [("h1_g2", [z1, E, B], [1, 3]), ("h1_g2", [z1, B, E], [1, 3])]
    if len(Z) == 2:
        z1, z2 = Z
        if F:
            T += [("h2_g3", [z1, z2, F, E, B], [2, 5]), ("h2_g3", [z1, z2, E, F, B], [2, 5]),
                  ("h2_g2", [z1, F, E, B], [2, 4]), ("h2_g2", [z1, F, B, E], [2, 4]),
                  ("h2_g3_AB|CDE", [F, E, B, z1, z2], [2, 5]), ("h2_g3_AB|CDE", [F, E, z2, z1, B], [2, 5]),
                  ("h3_g2", [z1, z2, F, E, B], [1, 2, 3, 5]), ("h3_g2", [z1, z2, F, B, E], [1, 2, 3, 5]),
                  ("h3_g2_c3", [z1, z2, F, E, B], [3, 5]), ("h3_g2_c3", [z1, z2, F, B, E], [3, 5])]
        else:
            T += [("h2_g2", [z1, z2, E, B], [2, 4]), ("h2_g2", [z1, z2, B, E], [2, 4]), ("h2_g3", [z1, z2, E, B, ], [1, 2, 4]),
                  ("h1_g3_A|BCD", [z1, E, B, z2], [1, 4]), ("h1_g3_A|BCD", [z1, B, E, z2], [1, 4])]
    return T


def jobs():
    import contracts as CT
    import guard as GD
    R = [json.loads(l) for l in open(OD / "construct.jsonl")]
    (OD / "recs").mkdir(parents=True, exist_ok=True)
    jb, rows = [], []
    for r in sorted([r for r in R if r["ok"]], key=lambda r: h("R4.4f", r["fam"])):
        rec = r["rec"]; kg = rec["r44"]; rid2 = rec["ids"]["root_id"]
        p = OD / "recs" / f"{rid2}.json"; p.write_text(json.dumps(rec))
        inp = CT.view3d(rec); ids = inp["ids"]
        rows.append({"root_id": rid2, "domain": "3d", "parent_family_id": r["fam"], "inputs": inp, "path": str(p), "parent_root": r["root_id"], "level": r["level"]})
        cell = lambda rc: int(rc[0]) * 6 + int(rc[1])  # noqa: E731
        for t, seq, b in templates(kg, cell):
            jb.append({"key": f"R4.4|{rid2}|{t}|{json.dumps(seq)}|{json.dumps(b)}", "root_id": rid2, "fam": r["fam"], "template": t, "path": str(p), "kind": "X_CHUNKED",
                       "order": [[o, [d // 6, d % 6]] for o, d in seq], "seq": [[ids.index(o), d] for o, d in seq], "bounds": b, "y": None})
        c0 = rec["initial_cells"]
        iv = [("baseline", {}), ("beneficial", {kg["E"]: kg["pE"]})]
        if kg["Z"]:
            iv.append(("irrelevant", {kg["Z"][0][0]: kg["Z"][0][1]}))
        if kg["F"]:
            iv.append(("harmful", {kg["E"]: kg["pE"], kg["F"]: kg["x"]}))
        for tag, ed in iv:
            jb.append({"key": f"R4.4|{rid2}|TEMP_{tag}", "root_id": rid2, "fam": r["fam"], "template": f"TEMP_{tag}", "path": str(p), "kind": "Y_TARGET",
                       "cells": {**c0, **ed}, "edit": ed, "target": kg["B"], "goal": kg["pB"]})
    jf = OD / "jobs.json"; jf.write_text(json.dumps(jb, indent=1))
    with open(OD / "rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    s = GD.seal(jf)
    print(json.dumps({"families": len(rows), "levels": collections.Counter(r["level"] for r in rows), "jobs": len(jb), "templates": collections.Counter(j["template"] for j in jb), "seal": s["sha256"][:16]}))


def temp():
    """Frozen-model temporary-target diagnostic on physically verified E-enables-B families (R4.4 new + KGT3 P2 constructed; evaluator joins).
    Per family, temporary task (B -> pB) on the hypothetical scene S (E at x) and after moving E (S | E -> pE):
      dY      frozen Y_temp(B | S, E parked) - Y_temp(B | S) (should be > 0)
      prop    frozen task-conditioned cVAE on the temporary task: E among proposed movers with pE in its top-4; rank of pE; any E proposal
      admit   recursive admission rule (temporary pY after the group > temporary no-op pY): actual enabler E -> pE; best proposed E move
      false   irrelevant (Z1 -> pZ1) and harmful (F moved onto x / some object moved next to B) actions admitted by the same rule."""
    import learn as LN
    import views as V
    import cover as CV
    fz, _ = LN.load("3d", "F0")
    fams = []
    for f, kind in ((OD / "rows.jsonl", "R4.4"), (D2.O / "rows3d_con.jsonl", "KGT3")):
        if f.exists():
            for l in open(f):
                r = json.loads(l)
                rec = json.loads(Path(r["path"]).read_text())
                kg = rec.get("r44") or rec.get("kgt3")
                fams.append((kind, r, kg))
    cell = lambda rc: int(rc[0]) * 6 + int(rc[1])  # noqa: E731
    out = []
    for kind, r, kg in fams:
        row = {"root_id": r["root_id"], "domain": "3d", "inputs": r["inputs"]}
        ids = row["inputs"]["ids"]
        Bi, Ei = ids.index(kg["B"]), ids.index(kg["E"])
        task = (Bi, cell(kg["pB"]))
        S = V.rebase(row, [], task=task)
        S2 = V.rebase(row, [[Ei, cell(kg["pE"])]], task=task)
        y0, y1 = fz.p_noop(S), fz.p_noop(S2)
        pyS = lambda seq: fz.score(S, [seq])[0]["py"]  # noqa: E731
        el = V.eligible(S, protect=[Bi])
        D = fz.proposals(S, el)
        P, legal, _, _ = CV.marg(fz, S, el)
        rk = CV.ranking(P[Ei], legal) if P.get(Ei) is not None else []
        acts = {"enabler": [Ei, cell(kg["pE"])]}
        if kg.get("Z"):
            zi = ids.index(kg["Z"][0][0] if isinstance(kg["Z"], list) else kg["Z"])
            zd = kg["Z"][0][1] if isinstance(kg["Z"], list) else kg["pZ"]
            acts["irrelevant"] = [zi, cell(zd)]
        if kg.get("F"):
            acts["F_relocation"] = [ids.index(kg["F"]), cell(kg["pF"])]
        res = {k: {"py_after": pyS([a]), "admitted": pyS([a]) > y0} for k, a in acts.items()}
        Eprop = [[Ei, d] for d in D.get(Ei, [])]
        bestE = max((pyS([a]) for a in Eprop), default=None)
        others = [[o, d] for o, ds in D.items() if o != Ei for d in ds]
        adm_other = sum(pyS([a]) > y0 for a in others)
        out.append({"src": kind, "root_id": r["root_id"], "level": r.get("level", 2), "y_temp_S": y0, "y_temp_after_E": y1, "dY": y1 - y0, "dY_pos": y1 > y0,
                    "E_proposed": bool(D.get(Ei)), "pE_in_top4": cell(kg["pE"]) in D.get(Ei, []), "pE_rank": rk.index(cell(kg["pE"])) if cell(kg["pE"]) in rk else None,
                    "best_E_proposal_admitted": bestE is not None and bestE > y0, "actions": res, "other_proposals": len(others), "other_admitted": adm_other})
    summ = {"n": len(out), "by_src": dict(collections.Counter(o["src"] for o in out)), "dY_pos": sum(o["dY_pos"] for o in out),
            "dY_median": sorted(o["dY"] for o in out)[len(out) // 2] if out else None, "E_proposed": sum(o["E_proposed"] for o in out),
            "pE_in_top4": sum(o["pE_in_top4"] for o in out), "enabler_admitted": sum(o["actions"]["enabler"]["admitted"] for o in out),
            "best_E_proposal_admitted": sum(o["best_E_proposal_admitted"] for o in out),
            "irrelevant_admitted": [sum(o["actions"]["irrelevant"]["admitted"] for o in out if "irrelevant" in o["actions"]), sum("irrelevant" in o["actions"] for o in out)],
            "other_proposals_admitted_rate": sum(o["other_admitted"] for o in out) / max(1, sum(o["other_proposals"] for o in out)),
            "pE_rank_hist": dict(collections.Counter("none" if o["pE_rank"] is None else str(min(o["pE_rank"], 12)) for o in out))}
    (OD / "temp_model.json").write_text(json.dumps({"summary": summ, "per_family": out}, indent=1))
    print(json.dumps(summ))


def analyze():
    import guard as GD
    jf, rf = OD / "jobs.json", OD / "phys.jsonl"
    c = GD.complete(jf, rf)
    J = {j["key"]: j for j in json.loads(jf.read_text())}
    R = {json.loads(l)["key"]: json.loads(l) for l in open(rf)} if rf.exists() else {}
    cov, contr, iv = collections.Counter(), collections.defaultdict(list), collections.defaultdict(collections.Counter)
    outc = collections.Counter()
    for k, j in J.items():
        r = R.get(k)
        if r is None:
            outc["NOT_RUN"] += 1; continue
        if j["kind"] == "Y_TARGET":
            oc = GD.outcome(r, "Y"); iv[j["template"]][oc] += 1; outc[f"Y:{oc}"] += 1; continue
        X = r.get("X") or {}
        oc = GD.outcome(r, "X")
        if oc == "SUCCESS" and (r.get("REPLAY") or {}).get("replay") != 1:
            oc = "SUCCESS_NO_REPLAY"
        outc[f"X:{oc}"] += 1
        b = [0] + j["bounds"]
        ph = str(X.get("phase") or "")
        fail = int(ph.split(":")[1]) if ph.startswith("relocation") else (int(ph.split(":")[1]) - 1 if ph.startswith("boundary") else None)
        for s, e in zip(b[:-1], b[1:]):                                         # chunk-level evidence (decided chunks only)
            if oc == "SUCCESS" or (fail is not None and fail >= e):
                lab = 1 if (oc == "SUCCESS" or fail >= e) else None
            elif fail is not None and s <= fail < e and oc in ("CERTIFIED_INFEASIBLE",):
                lab = 0
            else:
                lab = None
            if lab is not None:
                cov[(s, e - s, lab, oc == "SUCCESS")] += 1
            if fail is not None and s <= fail < e:
                break
        contr[(j["root_id"], j["template"])].append((j["order"], oc))
    mat = collections.defaultdict(dict)
    for (hh, g, lab, rep), v in cov.items():
        mat[f"h{hh}"][f"g{g}_{'pos' if lab else 'neg'}{'' if not lab else ('_replayed' if rep else '_prefix')}"] = mat[f"h{hh}"].get(f"g{g}_{'pos' if lab else 'neg'}{'' if not lab else ('_replayed' if rep else '_prefix')}", 0) + v
    disc = collections.Counter()
    for (rid, t), v in contr.items():
        if len(v) >= 2:
            labs = {o for _, o in v}
            disc[t] += ("SUCCESS" in labs and "CERTIFIED_INFEASIBLE" in labs)
    cpu = sum(r.get("cpu_s", 0) for r in R.values()) / 3600
    con = [json.loads(l) for l in open(OD / "construct.jsonl")]
    out = {"completion": c, "construction": {"attempted": len(con), "level": dict(collections.Counter(r["level"] for r in con)), "probes": sum(r["probes"] for r in con),
                                             "cpu_h": sum(r["cpu_s"] for r in con) / 3600, "why": dict(collections.Counter(r.get("why") for r in con if not r["ok"]))},
           "outcomes": dict(outc), "coverage_matrix": mat, "discordant_by_template": dict(disc), "interventions": {k: dict(v) for k, v in iv.items()}, "cpu_h_jobs": cpu}
    (OD / "R4_4_deep3d.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, default=str)[:4000])


def rank():
    """Model-only: frozen X models on the DECIDED matched groups of R4.4 (same family + template = same scene, same destination set, same
    bounds; SUCCESS vs CERTIFIED_INFEASIBLE).  Energy of a run = sum over its declared chunks of -log marginal pX on the canonical anchored
    scene (compose.Scores; m <= 3 single chunk at h0 uses the exact joint p11, R4.0).  Family-weighted concordance, ties 0.5, by depth."""
    import math
    import numpy as np
    import compose as CP
    import guard as GD
    import learn as LN
    import views as V
    J = {j["key"]: j for j in json.loads((OD / "jobs.json").read_text())}
    R = {json.loads(l)["key"]: json.loads(l) for l in open(OD / "phys.jsonl")}
    rows = {json.loads(l)["root_id"]: json.loads(l) for l in open(OD / "rows.jsonl")}
    grp = collections.defaultdict(list)
    for k, j in J.items():
        if j["kind"] != "X_CHUNKED":
            continue
        oc = GD.outcome(R[k], "X")
        if oc == "SUCCESS" and (R[k].get("REPLAY") or {}).get("replay") != 1:
            continue
        if oc in ("SUCCESS", "CERTIFIED_INFEASIBLE"):
            grp[(j["root_id"], j["template"])].append((j, oc))
    grp = {k: v for k, v in grp.items() if len({o for _, o in v}) == 2}
    out = {}
    for name, spec in (("F0", "F0"), ("M1s", "M1s_s0"), ("G1s", "G1s_s0"), ("O2", "M1ft_O2_s0")):
        fz, net = LN.load("3d", spec); fz.net = net; fz.reset(); fz.caps = {}
        fam = collections.defaultdict(list); depth = collections.defaultdict(list)
        for (rid, t), v in grp.items():
            row = {"root_id": rid, "domain": "3d", "inputs": rows[rid]["inputs"]}
            T = CP.Scores(fz, row, V.rebase)
            E = []
            for j, oc in v:
                seq = [tuple(map(int, a)) for a in j["seq"]]; b = [0] + j["bounds"]
                if len(seq) <= 3 and len(b) == 2:
                    e = -math.log(max(CP.EPS, fz.score(row, [list(map(list, seq))])[0]["p11"]))
                else:
                    T.need([(frozenset(seq[:s0]), tuple(seq[s0:e0])) for s0, e0 in zip(b[:-1], b[1:])])
                    e = sum(T.cost(seq[:s0], seq[s0:e0]) for s0, e0 in zip(b[:-1], b[1:]))
                E.append((e, oc))
            pr = [1.0 if a < c else 0.5 if a == c else 0.0 for a, oa in E if oa == "SUCCESS" for c, oc2 in E if oc2 != "SUCCESS"]
            fam[rid].append(sum(pr) / len(pr)); depth[t.split("_")[0]].append(sum(pr) / len(pr))
        fv = {f: float(np.mean(x)) for f, x in fam.items()}; fs = sorted(fv)
        rng = np.random.default_rng(0)
        bs = [float(np.mean([fv[f] for f in rng.choice(fs, len(fs))])) for _ in range(2000)]
        out[name] = {"families": len(fs), "groups": len(grp), "concordance": float(np.mean(list(fv.values()))), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                     "by_depth": {d: [round(float(np.mean(x)), 3), len(x)] for d, x in sorted(depth.items())}}
        print(name, json.dumps(out[name]), flush=True)
    (OD / "rank_models.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1]
    {"rank": rank, "construct": lambda: construct(*sys.argv[2:6]), "jobs": jobs, "temp": temp, "analyze": analyze}[a]()
