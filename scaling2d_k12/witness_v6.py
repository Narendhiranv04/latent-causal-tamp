#!/usr/bin/env python3
"""G2 witness search v6 (= v5 + ALL minimal goal sets of the V2 relaxation as admissible mover sets + seeded tie-break jitter for parallel searches; K12, lock amendment 6) (physical; frozen teacher via teacher_long, <= 12 relocations).
Per layout: sound bounds MINK_STATIC_V1 (declared grammar) and V2 (teacher's full grammar); Y(empty) measured; then a depth-first prefix search
over the V2 bound's minimal goal set M with
  - real occupancy simulated on the kill tables (unmoved discs at their cells, moved discs at their parking cells),
  - destinations ranked by the PARKING PRIOR (gen_deep.park_rank: low blocking footprint, many place candidates, q_ref-clear), never initially
    occupied (declared grammar), hard-rejecting a destination whose disc would leave a remaining required pick (M, target) or the goal place
    with no live candidate,
  - objects ranked by pick robustness (live pick candidates in the current occupancy, descending),
  - ALT candidates per step, bounded backtracking (MAXQ physical prefix queries per layout); the teacher caches every prefix.
A prefix step is kept when relocation j verifies (x = 1, or the only failure is the intermediate connector).  Final: full X and Y.
CERTIFIED_MIN_K iff X = 1 and Y = 1 (both independently replayed), Y(empty) = 0 and len(witness) == K_lb(V2) == K_lb(V1).
    python witness_v3.py TABLE LAYOUTS OUT WORKERS [ALT=8] [MAXQ=48]"""
import functools, json, os, random, sys, time
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cert as C  # noqa: E402
import mink as MK  # noqa: E402
import witness as W  # noqa: E402
import gen_deep as GD  # noqa: E402

RESTARTS = 10
W6_SEED = int(os.environ.get("W6_SEED", "0"))      # randomised tie-breaks: independent parallel searches per layout use different seeds
JIT = 0.15


def job(args):
    T, L, alt, maxq = args
    geom = L["geom"]
    MK.boot(geom)
    import teacher_long as TL
    E = MK._M["E"]
    rec, ids = W.rec_of(L, geom)
    t0 = time.process_time()
    qc = set(MK.qclear(geom, rec["q0"]))
    root = {"ids": ids, "cells0": L["cells0"], "tid": 0, "goal_cell": L["goal_cell"], "legal_cells": list(range(64)), "fixed": [False] * len(ids)}
    b1, b2 = C.bound(T, root, qc, "unoccupied"), C.bound(T, root, qc, "any_legal")
    out = {"root_id": L["root_id"], "geom": geom, "K_lb_v1": b1["K_lb"], "K_lb_v2": b2["K_lb"], "K_lb": b2["K_lb"], "n_objects": len(ids), "tries": [],
           "gen": L.get("gen"), "seed": L.get("seed")}
    cache = {}
    y0 = TL.y_query(E, L["root_id"], rec, [], cache)
    out["Y0"] = {k: y0.get(k) for k in ("y", "teacher_status", "negative_kind", "independent_replay")}
    if not isinstance(b2["K_lb"], int) or b2["K_lb"] < 1 or any(c not in qc for c in L["cells0"]):
        out["verdict"] = "NO_BOUND" if not isinstance(b2["K_lb"], int) else "INVALID_LAYOUT_QREF_COLLISION"
        return out
    pk, pl, p0, pl0 = T["pickkill"], T["placekill"], T["pick0"], T["place0"]
    kill = lambda tab, x, occ: functools.reduce(lambda a, q: a | int(tab[str(x)].get(str(q), 0)), occ, 0)  # noqa: E731
    live = lambda base, tab, x, occ: int(base[str(x)]) & ~kill(tab, x, occ)  # noqa: E731
    goal, cells0, M = L["goal_cell"], list(L["cells0"]), list(b2["witness_set"])
    # V6: ALL minimal goal sets at layer K of the V2 relaxation (bfs returns only the first); the DFS may realise any of them
    n_ = len(ids); mov_ = list(range(1, n_)); K_ = b2["K_lb"]
    dest_ok = [d for d in range(64) if d != goal and d in qc]
    P_, D_, G_ = C.masks_fast(T, cells0, ids, mov_, 0, goal, dest_ok)
    full = (1 << n_) - 1
    lv = lambda S, pres: any(m & pres == 0 for m in S)  # noqa: E731
    layer, seen = {0}, {0}
    for k_ in range(K_):
        nxt = set()
        for Mm in layer:
            pres = full & ~Mm
            for o_ in mov_:
                if not Mm >> o_ & 1 and lv(P_[o_], pres & ~(1 << o_)) and lv(D_[o_], pres & ~(1 << o_)):
                    N_ = Mm | (1 << o_)
                    if N_ not in seen:
                        seen.add(N_); nxt.add(N_)
        layer = nxt
    GS = sorted(Mm for Mm in layer if lv(P_[0], full & ~Mm) and lv(G_, full & ~Mm))
    out["n_goal_sets"] = len(GS)
    rng6 = random.Random(f"W6|{L['root_id']}|{W6_SEED}")
    occ0 = set(cells0)
    prior = [d for d in GD.park_rank(T, qc, goal) if d not in occ0]
    rest = [d for d in range(64) if d in qc and d not in occ0 and d != goal and d not in prior]
    nq = [0]

    def cands(cur, done):
        dm = sum(1 << i for i in done)
        compat = [g for g in GS if g & dm == dm]
        um = functools.reduce(lambda a, b: a | b, compat, 0); im = functools.reduce(lambda a, b: a & b, compat, full) if compat else 0
        rem = [o for o in range(1, n_) if um >> o & 1 and o not in done]
        must = [o for o in range(1, n_) if im >> o & 1 and o not in done]
        res = []
        for o in rem:
            others = [c for i, c in cur.items() if i != o]
            lp = live(p0, pk, cur[o], others)
            if not lp:
                continue
            used = set(cur.values())
            for rank, d in enumerate(prior + rest):
                if d in used or not live(pl0, pl, d, others):
                    continue
                # optimistic future occupancy: every not-yet-moved object of M removed, non-M objects in place, parked discs (+ d) present.
                # Reject d only if it alone makes a remaining required pick (M, target) or the goal place impossible even then.
                parked = [cur[i] for i in done] + [d]
                fixed = [cur[i] for i in cur if not um >> i & 1 and i != 0]
                bad = any(not live(p0, pk, cur[i], fixed + parked + [cur[0]]) for i in must if i != o) \
                    or not live(p0, pk, cur[0], fixed + parked) or not live(pl0, pl, goal, fixed + parked)
                if bad:
                    continue
                res.append((round(GD.p_fail("pick_source", cur[o]) + GD.p_fail("dest", d) + 0.05 * PEN.get(d, 0) + JIT * rng6.random() * (W6_SEED > 0), 2), rank, -bin(lp).count("1"), o, d))
        res.sort()
        # V4: object-diverse candidate list -- round-robin over objects (each object's destinations in V3 order), so ALT covers several first
        # movers instead of ALT destinations of a single object (V3 failure mode on dense 25-object layouts: every candidate was one object)
        per = {}
        for *_, o, d in sorted(res, key=lambda r: -BOOST.get(r[3], 0)):   # V5: movers that failed in earlier restarts first (stable)
            per.setdefault(o, []).append((o, d))
        rr, k = [], 0
        while len(rr) < len(res):
            for o in per:
                if k < len(per[o]):
                    rr.append(per[o][k])
            k += 1
        return rr[:alt]

    # V5: failure-directed restarts.  A restart ends when its query share is spent; then every destination used by a failed prefix is penalised
    # (+1 per failed prefix containing it) and every mover whose relocation failed is boosted, so the next DFS parks elsewhere and moves the
    # blocked movers earlier.  Total queries <= maxq; restarts <= RESTARTS.
    PEN, BOOST, wit = {}, {}, None
    share = max(40, maxq // RESTARTS)
    for rnd in range(RESTARTS):
        lim = min(maxq, nq[0] + share)
        n0 = len(out["tries"])
        stop = [lim]
        def dfs(cur, seq):  # noqa: E306
            if len(seq) == K_:
                return seq
            for o, d in cands(cur, {x for x, _ in seq}):
                if nq[0] >= stop[0]:
                    return None
                s_ = [(ids[a], b) for a, b in seq + [(o, d)]]
                x = TL.x_query(E, L["root_id"], rec, s_, cache)
                nq[0] += 1
                ph = str(x.get("failed_phase") or "")
                out["tries"].append({"seq": [list(t) for t in s_], "x": x.get("y"), "x_status": x.get("teacher_status"), "x_phase": x.get("failed_phase"), "restart": rnd})
                if x.get("y") == 1 or ph.startswith("connector"):
                    r = dfs({**cur, o: d}, seq + [(o, d)])
                    if r is not None:
                        return r
            return None
        wit = dfs(dict(enumerate(cells0)), [])
        if wit is not None or nq[0] >= maxq:
            break
        for t in out["tries"][n0:]:
            if t["x"] != 1 and not str(t.get("x_phase") or "").startswith("connector"):
                BOOST[ids.index(t["seq"][-1][0])] = BOOST.get(ids.index(t["seq"][-1][0]), 0) + 1
                for _, dd in t["seq"][:-1]:
                    PEN[dd] = PEN.get(dd, 0) + 1
    out["restarts"] = rnd + 1
    if wit is not None:
        s = [(ids[a], b) for a, b in wit]
        x = TL.x_query(E, L["root_id"], rec, s, cache)
        tr = {"seq": [list(t) for t in s], "x": x.get("y"), "x_status": x.get("teacher_status"), "x_phase": x.get("failed_phase"),
              "x_replay": x.get("independent_replay"), "x_teacher": x.get("teacher"), "x_steps_witness": [st.get("witness") for st in (x.get("steps") or [])],
              "x_connector_witness": x.get("witness_connector"), "final": True}
        if tr["x"] == 1:
            y = TL.y_query(E, L["root_id"], rec, s, cache)
            tr.update(y=y.get("y"), y_status=y.get("teacher_status"), y_replay=y.get("independent_replay"), y_witness=y.get("target_witness"), y_teacher=y.get("teacher"))
        out["tries"].append(tr)
    ok = [t for t in out["tries"] if t.get("final") and t.get("x") == 1 and t.get("y") == 1 and t.get("x_replay") and t.get("y_replay")]
    cert = bool(ok) and out["Y0"]["y"] == 0 and len(ok[0]["seq"]) == b2["K_lb"] == b1["K_lb"]
    out["verdict"] = "CERTIFIED_MIN_K" if cert else ("WITNESS_ONLY_UNCERTIFIED" if ok else "NO_WITNESS_FOUND")
    out["n_queries"], out["cpu_s"] = nq[0], round(time.process_time() - t0, 1)
    out["certificate"] = {"v1": {k: b1[k] for k in ("version", "dest_mode", "K_lb", "witness_set", "layer_counts")},
                          "v2": {k: b2[k] for k in ("version", "dest_mode", "K_lb", "witness_set", "layer_counts")}}
    return out


def main(table, layouts, outp, workers, alt=8, maxq=48):
    T = json.loads(Path(table).read_text())
    Ls = [json.loads(l) for l in open(layouts)]
    done = {json.loads(l)["root_id"] for l in open(outp)} if Path(outp).exists() else set()
    todo = [(T, L, alt, maxq) for L in Ls if L["root_id"] not in done]
    with get_context("spawn").Pool(workers, maxtasksperchild=4) as pool, open(outp, "a") as f:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(json.dumps({k: r.get(k) for k in ("root_id", "K_lb", "verdict", "n_queries", "cpu_s")}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(os.path.abspath(a[0]), os.path.abspath(a[1]), os.path.abspath(a[2]), int(a[3]), int(a[4]) if len(a) > 4 else 8, int(a[5]) if len(a) > 5 else 48)
