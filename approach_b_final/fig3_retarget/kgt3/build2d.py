#!/usr/bin/env python3
"""R4.3 2D teacher audit + witness-first dependency construction pilot (UNCHANGED BXY teacher primitives via physical2d; full articulated
planar robot; per-query budgets unchanged; fresh cache per query).  Kill tables (MINK_STATIC) only RANK candidate obstructor cells; every
label is a teacher outcome.  Negatives only CERTIFIED_INFEASIBLE; UNKNOWN_* = unresolved (never a negative).
    $PY2D build2d.py audit                     -> O/kgt3/r4/b2d/audit_unknown.json (P2 UNKNOWN mechanisms; static kill + small re-query sample)
    $PY2D build2d.py roster N                  -> roster.json (+ SEAL): family ids R4.3-F000..
    $PY2D build2d.py work WORKERS CPU_LO MAX_CPU_H  -> families.jsonl (one terminal record per family), queries.jsonl (every teacher query)
Family (deterministic in sha256('R4.3|' + fid)):  t0, goal, B on fresh cells (8x8 lattice, q_ref footprint cells excluded)
  1 B -> pB VERIFIED from q_ref                           (probe = x_chunked single relocation from q_ref, bounds [1], replayed)
  2 static cage around B (walls ranked by the MINK kill table until no static pick grasp is left; one wall = E, the one whose removal
    restores a grasp); B -> pB VERIFIED without E, CERTIFIED_INFEASIBLE with E (single discs never block the planar arm: smoke R4.3-SMOKE0)
  3 E -> pE VERIFIED;  4 B -> pB VERIFIED after E parked at pE      => level-2 dependency established (E enables B)
  5 matched X runs (x_chunked + independent replay): [E,B] and [B,E] with bounds {[2], [1,2]}
  6 level 3: cage around E with removable wall F: E -> pE CERTIFIED with F; F -> pF VERIFIED; E -> pE VERIFIED after F parked
  7 matched X runs on {F, E, B}: all 6 orders as one chunk [3]; F,E,B with [1,2,3], [1,3], [2,3]
  8 nuisance (only after the dependency is established): 3 extra discs away from the chain; verified order and B-first order, one chunk."""
from __future__ import annotations

import collections, hashlib, json, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent.parent)]
NW = Path(os.environ.get("R2_NW", "/home/projects/long-horizon/naren_workspace"))
OB = Path(os.environ["B2D_OUT"]) if os.environ.get("B2D_OUT") else NW / "fig3" / "kgt3" / "r4" / "b2d"   # R5.1: r5/b2d (R4.3 untouched)
PREFIX = os.environ.get("B2D_PREFIX") == "1"                    # R5.1: prefix templates (h >= 1 chunks) from verified wall relocations
K3S = NW / "k3scale"
QREF_CELLS = {50, 58}                                                   # cells swept by the robot at q_ref (QCLEAR_original complement)
R, C, PITCH = 8, 8, 0.08


def h(*a):
    return hashlib.sha256("|".join(map(str, a)).encode()).hexdigest()


def cheb(a, b):
    return max(abs(a // C - b // C), abs(a % C - b % C))


def xy(c):
    return [round(0.04 + PITCH * (c % C), 6), round(0.04 + PITCH * (c // C), 6)]


class Kill:
    def __init__(self):
        T = json.loads((K3S / "G1" / "MINK_TABLE_original.json").read_text())
        self.p0 = {int(k): int(v) for k, v in T["pick0"].items()}
        self.pk = {int(k): {int(b): int(m) for b, m in v.items()} for k, v in T["pickkill"].items()}
        self.l0 = {int(k): int(v) for k, v in T["place0"].items()}
        self.lk = {int(k): {int(b): int(m) for b, m in v.items()} for k, v in T["placekill"].items()}

    def pick_left(self, c, occ):
        m = self.p0.get(c, 0)
        for b in occ:
            if b != c:
                m &= ~self.pk.get(c, {}).get(b, 0)
        return bin(m).count("1")

    def place_left(self, d, occ):
        m = self.l0.get(d, 0)
        for b in occ:
            if b != d:
                m &= ~self.lk.get(d, {}).get(b, 0)
        return bin(m).count("1")


def mkrec(fid, cells, goal):
    objs = [{"id": o, "kind": "target" if o == "t0" else "obstacle", "radius_m": 0.024, "xy_m": xy(c), "cell": int(c), "support": "table"} for o, c in sorted(cells.items())]
    q0 = [1.5707963267948966, -1.5707963267948966, -1.5707963267948966]
    return {"scene": {"root_id": fid, "variant_id": "orig", "lattice": {"rows": R, "cols": C, "pitch_m": PITCH}, "objects": objs,
                      "robot": {"q_rad": q0, "gripper_gap_m": 0.07, "attachment": "free", "attached_id": None}, "legal_cells": list(range(R * C)),
                      "domain_policy": "ALL_SUPPORTED", "robot_profile_hash": "sha256:2d7986761356f926f132f3b7045199a7e2b38a46d1c1516584a1929c3e1ae858", "action_hash": None},
            "goal_cell": int(goal), "fixed_ids": [], "geometry_impl": "original", "ids": {"root_id": fid}, "q0": q0,
            "roles": {o: "movable" for o in cells if o != "t0"}}


# ------------------------------------------------------------------------------------------------------------------ audit
def audit():
    import guard as GD
    K = Kill()
    O = NW / "fig3" / "kgt3"
    J = {}
    for tag in ("p2", "p2x"):
        if (O / f"jobs_{tag}_2d.json").exists():
            J.update({j["key"]: j for j in json.loads((O / f"jobs_{tag}_2d.json").read_text())})
    R_ = [json.loads(l) for t in ("p2", "p2x") if (O / f"phys_{t}_2d.jsonl").exists() for l in open(O / f"phys_{t}_2d.jsonl")]
    rows = {}
    import data2 as D2
    allr = D2.all_rows("2d")
    cnt, cpu, sample = collections.Counter(), collections.defaultdict(list), []
    for r in R_:
        j = J[r["key"]]; X = r.get("X") or {}
        oc = GD.outcome(r)
        row = allr[j["root_id"]]
        ids = row["inputs"]["ids"]; cells = {ids[i]: int(c) for i, c in enumerate(row["inputs"]["cells0"])}
        seq = [(ids[o] if isinstance(o, int) else o, int(d)) for o, d in (j.get("seq") or [])]
        ph = str(X.get("failed_phase") or "")
        stage = "none"
        if ph.startswith("relocation"):
            jj = int(ph.split(":")[1])
            for o, d in seq[:jj]:
                cells[o] = d
            o, d = seq[jj]
            occ = [c for n, c in cells.items() if n != o]
            pl, ll = K.pick_left(cells[o], occ), K.place_left(d, occ)
            stage = "PICK_STATIC_BLOCKED" if pl == 0 else ("PLACE_STATIC_BLOCKED" if ll == 0 else "STATIC_FREE")
            if oc == "UNRESOLVED" and len(sample) < 40 and int(h("r43aud", r["key"])[:8], 16) % 6 == 0:
                sample.append({"key": r["key"], "path": j.get("path"), "seq": seq[:jj + 1], "fail_at": jj})
        elif ph.startswith("boundary"):
            stage = "BOUNDARY"
        N = len(ids)
        cnt[(oc, ph.split(":")[0] or "-", stage, "N<=12" if N <= 12 else "N13-16" if N <= 16 else "N17+", j.get("stratum"))] += 1
        cpu[oc].append(r.get("cpu_s", 0))
    out = {"by": {"|".join(map(str, k)): v for k, v in sorted(cnt.items())}, "cpu_median": {k: sorted(v)[len(v) // 2] for k, v in cpu.items()}}
    agg = collections.Counter()
    for k, v in cnt.items():
        agg[(k[0], k[2])] += v
    out["outcome_x_static"] = {"|".join(k): v for k, v in sorted(agg.items())}
    # small re-query sample: the failed relocation alone from the reached state; planner status / reason kept (budgets unchanged)
    import physical2d as P2
    P2.boot("original")
    import numpy as np
    req = []
    for s in sample:
        rec = json.loads(Path(s["path"]).read_text())
        T, pc, bd = P2.M["T"], P2.M["pc"], P2.M["bd"]
        cache = {}
        phys = T._phys(rec["ids"]["root_id"], rec, cache)
        cells, q = bd.cells0(rec), T.qref(rec)
        ok = True
        for o, d in s["seq"][:-1]:
            e = pc.best_edge(phys.edges(cells, q, o, d))
            if e is None:
                ok = False; break
            cells, q = {**cells, o: d}, np.asarray(e[2], float)
        if not ok:
            req.append({**s, "requery": "PREFIX_NOT_REPRODUCED"}); continue
        o, d = s["seq"][-1]
        c0 = time.process_time()
        outs = phys.edges(cells, q, o, d)
        req.append({"key": s["key"], "fail_at": s["fail_at"], "status": outs[0][0] if outs else None, "meta": {k: str(v)[:80] for k, v in (outs[0][4] if outs else {}).items()},
                    "cpu_s": round(time.process_time() - c0, 2), "budget": dict(phys.used)})
    out["requery"] = req
    out["requery_status"] = dict(collections.Counter(f"{r.get('status')}|{(r.get('meta') or {}).get('planner')}" for r in req))
    OB.mkdir(parents=True, exist_ok=True)
    (OB / "audit_unknown.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "requery"}, indent=1)[:3000])


# ------------------------------------------------------------------------------------------------------------------ construction
class Fam:
    def __init__(self, fid):
        import physical2d as P2
        if not P2.M:
            P2.boot("original")
        self.P2, self.fid, self.K = P2, fid, Kill()
        self.rng = random.Random(h("R4.3", fid))
        self.q, self.recs, self.n = [], {}, 0

    def rec(self, cells, goal, tag):
        rid = f"{self.fid}-{tag}"
        r = mkrec(rid, cells, goal)
        OB.joinpath("recs").mkdir(parents=True, exist_ok=True)
        p = OB / "recs" / f"{rid}.json"
        p.write_text(json.dumps(r)); self.recs[tag] = str(p)
        return r, p

    def probe(self, cells, goal, A, d, stage):
        """Single relocation (A -> d) from q_ref with the X teacher (x_chunked, bounds [1]: relocation + terminal connector + independent
        replay).  y_temp's certificate routine (p15_retarget.certified) returned UNKNOWN_PLANNER on statically caged objects in the smoke
        families, whereas the X teacher's edges() certificates (ORDER_FIRST_ACTION / STATIC_ENDPOINT_INVALID) decide them."""
        tag = f"probe{self.n:02d}"
        oc = self.xrun(cells, goal, [(A, d)], [1], "PROBE:" + stage, tag)
        self.q[-1]["kind"] = "PROBE"
        return oc

    def xrun(self, cells, goal, seq, bounds, stage, tag):
        import guard as GD
        r, p = self.rec(cells, goal, tag)
        c0 = time.process_time()
        x = self.P2.x_chunked(r, [(o, int(d)) for o, d in seq], bounds, {})
        oc = GD.outcome({"X": x}, "X")
        if oc == "SUCCESS" and not x.get("independent_replay"):
            oc = "OPERATIONAL_FAILURE"
        q = {"fid": self.fid, "n": self.n, "kind": "X", "stage": stage, "tag": tag, "cells": cells, "seq": [[o, int(d)] for o, d in seq], "bounds": bounds, "x": x.get("x"),
             "status": x.get("teacher_status"), "phase": x.get("failed_phase"), "replay": x.get("independent_replay"), "outcome": oc,
             "cpu_s": round(time.process_time() - c0, 2), "trace": x.get("trace"), "rec": str(p)}
        self.q.append(q); self.n += 1
        return oc

    def free(self, occ, avoid=(), far=(), r=2):
        return [c for c in range(R * C) if c not in occ and c not in QREF_CELLS and c not in avoid and all(cheb(c, f) >= r for f in far)]

    def cage(self, c, occ, avoid):
        """Static candidate ranking only: walls around cell c (Chebyshev <= 2) added greedily until no statically feasible pick grasp of c
        is left; -> (walls, E) where E = the wall whose removal restores the most grasps (and which is itself statically pickable)."""
        K, walls = self.K, []
        cand = [x for x in self.free(set(occ) | set(avoid)) if 1 <= cheb(x, c) <= 2]
        while K.pick_left(c, list(occ) + walls) > 0 and len(walls) < 6:
            cand = [x for x in cand if x not in walls]
            if not cand:
                return None, None
            x = min(cand, key=lambda x: (K.pick_left(c, list(occ) + walls + [x]), cheb(x, c), h(self.fid, "w", c, x)))
            if K.pick_left(c, list(occ) + walls + [x]) == K.pick_left(c, list(occ) + walls):
                return None, None
            walls.append(x)
        if K.pick_left(c, list(occ) + walls) > 0:
            return None, None
        es = [x for x in walls if K.pick_left(c, list(occ) + [w for w in walls if w != x]) > 0 and K.pick_left(x, list(occ) + walls + [c]) > 0]
        if not es:
            return None, None
        E = max(es, key=lambda x: (K.pick_left(c, list(occ) + [w for w in walls if w != x]), h(self.fid, "e", x)))
        return walls, E

    def run(self):
        rng, K = self.rng, self.K
        st = {"fid": self.fid, "level": 0, "why": None, "attempts": []}
        for attempt in range(3):
            t0 = rng.choice(self.free(set()))
            goal = rng.choice(self.free({t0}, far=[t0]))
            b = rng.choice([c for c in self.free({t0, goal}, far=[t0, goal]) if K.p0.get(c, 0) and 2 <= c // C <= 5 and 1 <= c % C <= 6])
            cells = {"t0": t0, "oB": b}
            walls, x = self.cage(b, [t0], [goal])
            if walls is None:
                st["attempts"].append("NO_STATIC_CAGE"); continue
            for i, w in enumerate(sorted(walls)):
                if w != x:
                    cells[f"oW{i}"] = w
            cells["oE"] = x
            occ = set(cells.values())
            pBs = self.free(occ | {goal}, far=list(occ - {b}) + [b], r=2)
            rng.shuffle(pBs)
            free_after = {**{k: v for k, v in cells.items() if k != "oE"}}
            pB = next((d for d in pBs[:3] if self.probe(free_after, goal, "oB", d, "B_free_without_E") == "SUCCESS"), None)
            if pB is None:
                st["attempts"].append("NO_VERIFIED_B_RELOCATION"); continue
            if self.probe(cells, goal, "oB", pB, "B_blocked_by_E") != "CERTIFIED_INFEASIBLE":
                st["attempts"].append("B_NOT_CERTIFIED_BLOCKED"); continue
            pEs = self.free(occ | {goal, pB}, far=list(occ), r=2)
            rng.shuffle(pEs)
            pE = next((d for d in pEs[:3] if self.probe(cells, goal, "oE", d, "E_free") == "SUCCESS"), None)
            if pE is None:
                st["attempts"].append("NO_VERIFIED_E_RELOCATION"); continue
            if self.probe({**cells, "oE": pE}, goal, "oB", pB, "B_free_after_E") != "SUCCESS":
                st["attempts"].append("B_NOT_FREE_AFTER_E"); continue
            break
        else:
            return {**st, "why": "NO_CERTIFIED_LEVEL2"}
        S1 = dict(cells)
        st.update(level=2, cells1=S1, goal=goal, pB=pB, pE=pE)
        r2 = {}
        for seq, tag in (([("oE", pE), ("oB", pB)], "EB"), ([("oB", pB), ("oE", pE)], "BE")):
            for bd in ([2], [1, 2]):
                r2[f"{tag}{bd}"] = self.xrun(S1, goal, seq, bd, "L2", f"L2_{tag}_{'-'.join(map(str, bd))}")
        st["L2"] = r2
        S, chain = S1, [("oE", pE), ("oB", pB)]
        # level 3: cage E (its own walls), F = the removable wall of E's cage
        occ = [c for k, c in S1.items() if k != "oE"]
        walls2, y = self.cage(S1["oE"], occ, [goal, pB, pE])
        F = None
        if walls2 is not None:
            c2 = dict(S1)
            for i, w in enumerate(sorted(walls2)):
                if w != y:
                    c2[f"oV{i}"] = w
            c2["oF"] = y
            if self.probe(c2, goal, "oE", pE, "E_blocked_by_F") == "CERTIFIED_INFEASIBLE":
                o2 = set(c2.values())
                pFs = self.free(o2 | {goal, pB, pE}, far=list(o2), r=2)
                rng.shuffle(pFs)
                pF = next((d for d in pFs[:3] if self.probe(c2, goal, "oF", d, "F_free") == "SUCCESS"), None)
                if pF is not None and self.probe({**c2, "oF": pF}, goal, "oE", pE, "E_free_after_F") == "SUCCESS":
                    F = (c2, pF)
                else:
                    st["L3_why"] = "NO_VERIFIED_F_OR_E_AFTER_F"
            else:
                st["L3_why"] = "E_NOT_CERTIFIED_BLOCKED_BY_F"
        else:
            st["L3_why"] = "NO_STATIC_CAGE_FOR_E"
        if F is not None:
            S2, pF = F
            st.update(level=3, cells2=S2, pF=pF)
            A = {"oF": ("oF", pF), "oE": ("oE", pE), "oB": ("oB", pB)}
            r3 = {}
            for perm in __import__("itertools").permutations(["oF", "oE", "oB"]):
                r3["".join(p[1] for p in perm) + "[3]"] = self.xrun(S2, goal, [A[p] for p in perm], [3], "L3_perm", "L3_" + "".join(p[1] for p in perm) + "_3")
            for bd in ([1, 2, 3], [1, 3], [2, 3]):
                r3[f"FEB{bd}"] = self.xrun(S2, goal, [A["oF"], A["oE"], A["oB"]], bd, "L3_part", f"L3_FEB_{'-'.join(map(str, bd))}")
            st["L3"] = r3
            S, chain = S2, [A["oF"], A["oE"], A["oB"]]
        if PREFIX:
            st["prefix"] = self.prefix(S, goal, chain, st)
        # nuisance after the dependency is established
        occ = set(S.values()) | {goal} | {d for _, d in chain}
        fr = self.free(occ, far=list(occ))
        nz = rng.sample(fr, 3) if len(fr) >= 3 else fr
        if nz:
            SN = {**S, **{f"oN{i}": c for i, c in enumerate(nz)}}
            st["nuisance"] = {"cells": SN, "verified_order": self.xrun(SN, goal, chain, [len(chain)], "NUIS", "NUIS_chain"),
                              "B_first": self.xrun(SN, goal, [chain[-1]] + chain[:-1], [len(chain)], "NUIS", "NUIS_Bfirst")}
        st["why"] = "OK"
        return st

    def prefix(self, S, goal, chain, st):
        """R5.1 local intermediate states: up to two verified relocations Z of the family's own cage walls (no new bodies, density unchanged)
        precede matched permutations of the dependency chunk -> 3-action chunks after 1 relocation, 2-/3-action chunks after 2.  Every label
        is a chunk <= 3 of an executed run; the long rollout only supplies the intermediate starting state."""
        rng = self.rng
        walls = sorted([k for k in S if k.startswith(("oW", "oV"))], key=lambda k: h(self.fid, "Z", k))
        Zs = []
        for w in walls:
            if len(Zs) == 2:
                break
            occ = set(S.values()) | {goal} | {d for _, d in chain} | {d for _, d in Zs}
            ds = self.free(occ, far=[S["oB"]], r=2)
            rng.shuffle(ds)
            d = next((d for d in ds[:2] if self.probe(S, goal, w, d, "Z_free") == "SUCCESS"), None)
            if d is not None:
                Zs.append((w, d))
        out = {"Z": [[w, d] for w, d in Zs]}
        if not Zs:
            out["why"] = "NO_VERIFIED_PREFIX"; return out
        z1 = Zs[0]
        T = []
        if st.get("level") == 3:
            F_, E_, B_ = chain
            T += [("h1g3", [z1, F_, E_, B_], [1, 4]), ("h1g3", [z1, E_, F_, B_], [1, 4]), ("h1g3", [z1, B_, E_, F_], [1, 4]),
                  ("h2g2", [z1, F_, E_, B_], [2, 4]), ("h2g2", [z1, F_, B_, E_], [2, 4])]
            if len(Zs) == 2:
                T += [("h2g3", [z1, Zs[1], F_, E_, B_], [2, 5]), ("h2g3", [z1, Zs[1], E_, F_, B_], [2, 5])]
        else:
            E_, B_ = chain
            if len(Zs) == 2:
                T += [("h1g3", [z1, E_, B_, Zs[1]], [1, 4]), ("h1g3", [z1, B_, E_, Zs[1]], [1, 4]),
                      ("h2g2", [z1, Zs[1], E_, B_], [2, 4]), ("h2g2", [z1, Zs[1], B_, E_], [2, 4])]
            else:
                T += [("h1g2", [z1, E_, B_], [1, 3]), ("h1g2", [z1, B_, E_], [1, 3])]
        for t, seq, bd in T:
            out[f"{t}:{''.join(o[1] for o, _ in seq)}"] = self.xrun(S, goal, seq, bd, "PFX_" + t, f"PFX_{t}_{''.join(o[1] for o, _ in seq)}")
        return out


def roster(n, ns="R4.3-F"):
    import guard as GD
    OB.mkdir(parents=True, exist_ok=True)
    f = OB / "roster.json"
    f.write_text(json.dumps([{"key": f"{ns}{i:03d}"} for i in range(int(n))], indent=1))
    print(GD.seal(f))


def _one(fid):
    t0 = time.process_time()
    try:
        F = Fam(fid)
        st = F.run()
        err = None
    except Exception as e:  # noqa: BLE001
        import traceback
        st, err, F = {"fid": fid, "level": None, "why": "ERROR"}, f"{type(e).__name__}: {str(e)[:200]} {traceback.format_exc()[-400:]}", locals().get("F")
    qs = F.q if F is not None else []
    rec = {"key": fid, "X": {"x": int(st.get("level") or 0) >= 2, "status": st.get("why")}, "family": st, "n_queries": len(qs), "cpu_s": round(time.process_time() - t0, 1)}
    if err:
        rec["error"] = err
    rec["X"]["x"] = int(rec["X"]["x"])
    return rec, qs


def work(workers, cpu_lo, max_cpu_h):
    import multiprocessing as mp
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    R_ = json.loads((OB / "roster.json").read_text())
    fo, qo = OB / "families.jsonl", OB / "queries.jsonl"
    done = {json.loads(l)["key"] for l in open(fo)} if fo.exists() else set()
    prior = sum(json.loads(l).get("cpu_s", 0) for l in open(fo)) if fo.exists() else 0.0
    todo = [r["key"] for r in R_ if r["key"] not in done]
    pool = mp.get_context("spawn").Pool(int(workers), maxtasksperchild=4)
    running, ff, fq, i, cpu = {}, open(fo, "a"), open(qo, "a"), 0, prior
    while True:
        for k, (ar, t) in list(running.items()):
            if ar.ready():
                rec, qs = ar.get(); running.pop(k)
                for q in qs:
                    fq.write(json.dumps(q) + "\n")
                ff.write(json.dumps(rec) + "\n"); ff.flush(); fq.flush(); cpu += rec["cpu_s"]
                print(time.strftime("%H:%M:%S"), k, rec["family"].get("level"), rec["family"].get("why"), rec["n_queries"], rec["cpu_s"], round(cpu / 3600, 2), flush=True)
        live = (cpu + sum(time.time() - t for _, t in running.values())) / 3600
        if live >= float(max_cpu_h):
            pool.terminate(); break
        if i < len(todo) and len(running) < int(workers) and live + 0.1 * (len(running) + 1) < float(max_cpu_h):
            running[todo[i]] = (pool.apply_async(_one, (todo[i],)), time.time()); i += 1; continue
        if not running:
            break
        time.sleep(2)
    for k, (_, t) in running.items():
        ff.write(json.dumps({"key": k, "censored": True, "cpu_s": round(time.time() - t, 1)}) + "\n")
    print("B2D_DONE", round(cpu / 3600, 3), "undispatched", len(todo) - i, flush=True)


def analyze():
    """Attempt ledger, construction yield, decided contrasts (certified negatives only), unresolved, chunk coverage matrix, CPU."""
    import guard as GD
    c = GD.complete(OB / "roster.json", OB / "families.jsonl")
    F = [json.loads(l) for l in open(OB / "families.jsonl")]
    Q = [json.loads(l) for l in open(OB / "queries.jsonl")]
    fam = collections.Counter(str((f.get("family") or {}).get("level")) + "|" + str((f.get("family") or {}).get("why")) for f in F)
    att = collections.Counter(a for f in F for a in (f.get("family") or {}).get("attempts", []))
    l3why = collections.Counter((f.get("family") or {}).get("L3_why") for f in F if (f.get("family") or {}).get("level") == 2)
    qo = collections.Counter(f"{q['kind']}|{q['outcome']}" for q in Q)
    stage = collections.Counter(f"{q['stage']}|{q['outcome']}" for q in Q)
    # matched contrasts: same family + same scene + same destination set, different orders; decided = SUCCESS vs CERTIFIED_INFEASIBLE
    grp = collections.defaultdict(list)
    for q in Q:
        if q["kind"] == "X" and not q["stage"].startswith("PROBE"):
            grp[(q["fid"], json.dumps(sorted(q["cells"].items())), json.dumps(sorted(map(tuple, q["seq"]))), json.dumps(q["bounds"]) if q["stage"] != "L3_perm" else "perm")].append(q)
    disc = collections.Counter(); und = collections.Counter()
    for k, v in grp.items():
        o = {x["outcome"] for x in v}
        tag = v[0]["stage"]
        disc[tag] += ("SUCCESS" in o and "CERTIFIED_INFEASIBLE" in o)
        und[tag] += any(x in o for x in ("UNRESOLVED", "BUDGET_NO_PLAN", "OPERATIONAL_FAILURE"))
    mat = collections.Counter()
    for q in Q:
        if q["kind"] != "X" or q["stage"].startswith("PROBE"):
            continue
        b = [0] + q["bounds"]; ph = str(q.get("phase") or "")
        fail = int(ph.split(":")[1]) if ph.startswith("relocation") else None
        for s_, e in zip(b[:-1], b[1:]):
            if q["outcome"] == "SUCCESS":
                mat[(s_, e - s_, "pos_replayed")] += 1
            elif fail is not None and fail >= e:
                mat[(s_, e - s_, "pos_prefix")] += 1
            elif fail is not None and s_ <= fail < e and q["outcome"] == "CERTIFIED_INFEASIBLE":
                mat[(s_, e - s_, "neg_certified")] += 1; break
            else:
                mat[(s_, e - s_, "unresolved")] += 1; break
    nu = collections.Counter(f"{k}:{v}" for f in F for k, v in ((f.get("family") or {}).get("nuisance") or {}).items() if k != "cells")
    cpu = sum(f.get("cpu_s", 0) for f in F) / 3600
    out = {"completion": c, "families_attempted": len(F), "families": dict(fam), "level2_or_more": sum(1 for f in F if ((f.get("family") or {}).get("level") or 0) >= 2),
           "level3": sum(1 for f in F if (f.get("family") or {}).get("level") == 3), "attempt_failures": dict(att), "level3_failure": dict(l3why),
           "queries": len(Q), "query_outcomes": dict(qo), "by_stage": dict(sorted(stage.items())), "matched_groups": len(grp), "decided_discordant_groups": dict(disc),
           "groups_with_unresolved": dict(und), "chunk_matrix": {f"h{a}|g{b}|{c_}": v for (a, b, c_), v in sorted(mat.items())}, "nuisance": dict(nu), "cpu_h": cpu,
           "unresolved_queries": sum(v for k, v in qo.items() if k.endswith(("UNRESOLVED", "BUDGET_NO_PLAN", "OPERATIONAL_FAILURE")))}
    (OB / "R4_3_build2d.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1)[:5000])


def rank():
    """Model-only: frozen 2D F0 on the DECIDED matched groups (same family, scene, destination set and bounds; SUCCESS vs CERTIFIED).
    Every group has m <= 3, so the production energy is the exact joint p11 of the ordered sequence; marginal pX also reported."""
    import numpy as np
    import contracts as CT
    import learn as LN
    fz, net = LN.load("2d", "F0"); fz.net = net
    Q = [json.loads(l) for l in open(OB / "queries.jsonl")]
    grp = collections.defaultdict(list)
    for q in Q:
        if q["kind"] == "X" and not q["stage"].startswith("PROBE") and q["outcome"] in ("SUCCESS", "CERTIFIED_INFEASIBLE"):
            grp[(q["fid"], q["stage"][:4], json.dumps(sorted(q["cells"].items())), json.dumps(sorted(map(tuple, q["seq"]))), json.dumps(q["bounds"]))].append(q)
    fam = collections.defaultdict(lambda: collections.defaultdict(list))
    first = collections.Counter()
    for k, v in grp.items():
        pos = [q for q in v if q["outcome"] == "SUCCESS"]; neg = [q for q in v if q["outcome"] == "CERTIFIED_INFEASIBLE"]
        if not pos or not neg:
            continue
        rec = json.loads(Path(v[0]["rec"]).read_text())
        inp = CT.view2d(rec); row = {"root_id": rec["ids"]["root_id"], "domain": "2d", "inputs": inp}
        ix = {n: i for i, n in enumerate(inp["ids"])}
        seqs = [[[ix[o], int(d)] for o, d in q["seq"]] for q in pos + neg]
        sc = fz.score(row, seqs)
        for key in ("p11", "px"):
            vals = [x[key] for x in sc]
            pr = [1.0 if a > b else 0.5 if a == b else 0.0 for a in vals[:len(pos)] for b in vals[len(pos):]]
            fam[key][k[0] + "|" + k[1]].append(sum(pr) / len(pr))
        best = max(range(len(seqs)), key=lambda i: sc[i]["p11"])
        first[k[1]] += best < len(pos)
    out = {}
    rng = np.random.default_rng(0)
    for key, F in fam.items():
        byf = collections.defaultdict(list)
        for g, vals in F.items():
            byf[g.split("|")[0]].extend(vals)
        fv = {f: float(np.mean(v)) for f, v in byf.items()}
        fs = sorted(fv)
        bs = [float(np.mean([fv[f] for f in rng.choice(fs, len(fs))])) for _ in range(2000)]
        out[key] = {"families": len(fs), "groups": sum(len(v) for v in F.values()), "concordance": float(np.mean(list(fv.values()))),
                    "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                    "by_stage": {st: float(np.mean([x for g, v in F.items() if g.endswith(st) for x in v])) for st in sorted({g.split("|")[1] for g in F})}}
    out["argmax_is_verified_order_by_stage"] = dict(first)
    (OB / "R4_3_rank_F0.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    a = sys.argv[1]
    {"rank": rank, "analyze": analyze, "audit": audit, "roster": lambda: roster(*sys.argv[2:4]), "work": lambda: work(*sys.argv[2:5]), "one": lambda: print(json.dumps(_one(sys.argv[2]), default=str)[:3000])}[a]()
