#!/usr/bin/env python3
"""G2b engineering pilot (excluded from any release): physical witnesses for static layouts with a sound bound K_lb (cert.py), using the
FROZEN 2D teacher unchanged (bxy_teacher.x_query / y_query, frozen <= 6-relocation contract; K > 6 needs a separately versioned wrapper).
Candidate witness = the bound's minimal goal set, ordered by relaxed feasibility, destinations ranked by the number of screen kills they add on
the target / goal / remaining movers (ties by cell); bounded retries (alternative destination at the failing step, then alternative order).
Certified minimum K = K_lb when a witness of length K_lb has replay-verified X = 1 and Y = 1 (and Y0 = 0 is measured).
    python witness.py TABLE.json LAYOUTS.jsonl OUT.jsonl WORKERS [MAX_TRIES=12]"""
import itertools, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cert as C  # noqa: E402
import mink as MK  # noqa: E402


def rec_of(L, geom):
    """layout -> raw root record in the frozen format (template scene; target t0, movable obstacles o00..)."""
    MK.boot(geom)
    ids = ["t0"] + [f"o{i:02d}" for i in range(len(L["cells0"]) - 1)]
    S = MK.scene([(i, "target" if i == "t0" else "obstacle", c) for i, c in zip(ids, L["cells0"])])
    sd = MK._M["sc"].scene_to_dict(S)
    sd["root_id"] = L["root_id"]
    return {"scene": sd, "goal_cell": L["goal_cell"], "fixed_ids": [], "geometry_impl": geom, "ids": {"root_id": L["root_id"]},
            "q0": list(sd["robot"]["q_rad"]), "roles": {i: "movable" for i in ids if i != "t0"}}, ids


def plan(T, L, cb, tries, qc):
    """yield candidate ordered sequences [(idx, cell)] of length K_lb.  Occupancy is simulated exactly on the tables (moved discs sit at their
    destinations): each step needs a live pick of o and a live place at d given every other disc currently present; d ranked by the number of
    screen kills it adds to the target pick, the goal place and the remaining movers' picks; the final state must leave the target pick and
    the goal place live.  Orders = permutations of the bound's minimal goal set (relaxation-consistent first)."""
    cells0, M, goal = list(L["cells0"]), list(cb["witness_set"]), L["goal_cell"]
    pk, pl, p0, pl0 = T["pickkill"], T["placekill"], T["pick0"], T["place0"]
    occ0 = set(cells0)
    adm = [d for d in range(64) if d not in occ0 and d != goal and d in qc]
    kill = lambda tab, x, occ: __import__("functools").reduce(lambda acc, q: acc | int(tab[str(x)].get(str(q), 0)), occ, 0)  # noqa: E731
    pick_live = lambda x, occ: int(p0[str(x)]) & ~kill(pk, x, occ) != 0  # noqa: E731
    place_live = lambda d, occ: int(pl0[str(d)]) & ~kill(pl, d, occ) != 0  # noqa: E731
    seqs = []
    for perm in itertools.permutations(M):
        cur = dict(enumerate(cells0))
        seq, ok = [], True
        for j, o in enumerate(perm):
            others = [c for i, c in cur.items() if i != o]
            if not pick_live(cur[o], others):
                ok = False; break
            used = set(cur.values())
            rem = [i for i in perm[j + 1:]] + [0]
            cand = [d for d in adm if d not in used and place_live(d, others)]
            if not cand:
                ok = False; break
            cand.sort(key=lambda d: (sum(bin(int(pk[str(cur[i])].get(str(d), 0))).count("1") for i in rem)
                                     + bin(int(pl[str(goal)].get(str(d), 0))).count("1"), d))
            seq.append((o, cand))
            cur[o] = cand[0]
        if ok:
            fin = [c for i, c in cur.items() if i != 0]
            if pick_live(cur[0], fin) and place_live(goal, fin):
                seqs.append(seq)
        if len(seqs) >= 6:
            break
    k = 0
    for seq in seqs:
        base = [(o, c[0]) for o, c in seq]
        yield base; k += 1
        for j in range(len(seq)):
            if k >= tries:
                return
            for d in seq[j][1][1:2]:
                if d not in {x for _, x in base}:
                    yield base[:j] + [(seq[j][0], d)] + base[j + 1:]; k += 1


def job(args):
    T, L, tries = args
    geom = L["geom"]
    MK.boot(geom)
    import bxy_teacher as BT
    E = MK._M["E"]
    rec, ids = rec_of(L, geom)
    t0 = time.process_time()
    r = {"ids": ids, "cells0": L["cells0"], "tid": 0, "goal_cell": L["goal_cell"], "legal_cells": list(range(64)), "fixed": [False] * len(ids)}
    qc = set(MK.qclear(geom, rec["q0"]))
    cb = C.bound(T, r, qc)
    out = {"root_id": L["root_id"], "geom": geom, "K_lb": cb["K_lb"], "n_objects": len(ids), "tries": []}
    cache = {}
    y0 = BT.y_query(E, L["root_id"], rec, [], cache)
    out["Y0"] = {k: y0.get(k) for k in ("y", "teacher_status", "negative_kind", "independent_replay")}
    if not isinstance(cb["K_lb"], int) or cb["K_lb"] < 1:
        out["verdict"] = "NO_BOUND"; return out
    if any(c not in qc for c in L["cells0"]):
        out["verdict"] = "INVALID_LAYOUT_QREF_COLLISION"; return out
    # v2: greedy PHYSICAL prefix search over the bound's minimal goal set.  At each step the relaxation-allowed (object, destination) pairs
    # (exact occupancy on the tables; ranked by added kills) are tried in order with the frozen x_query on prefix + pair; the first whose new
    # relocation succeeds (failed_phase is not relocation:j) is kept.  <= `tries` candidates per step; prefix results cached by the teacher.
    pk, pl, p0, pl0 = T["pickkill"], T["placekill"], T["pick0"], T["place0"]
    goal, cells0, M = L["goal_cell"], list(L["cells0"]), list(cb["witness_set"])
    occ0 = set(cells0)
    adm = [d for d in range(64) if d not in occ0 and d != goal and d in qc]
    kill = lambda tab, x, occ: __import__("functools").reduce(lambda acc, q: acc | int(tab[str(x)].get(str(q), 0)), occ, 0)  # noqa: E731
    cur, seq = dict(enumerate(cells0)), []
    for j in range(len(M)):
        rem = [o for o in M if o not in {x for x, _ in seq}]
        cands = []
        for o in rem:
            others = [c for i, c in cur.items() if i != o]
            if int(p0[str(cur[o])]) & ~kill(pk, cur[o], others) == 0:
                continue
            used = set(cur.values())
            for d in adm:
                if d in used or int(pl0[str(d)]) & ~kill(pl, d, others) == 0:
                    continue
                cost = sum(bin(int(pk[str(cur[i])].get(str(d), 0))).count("1") for i in rem if i != o) + bin(int(pl[str(goal)].get(str(d), 0))).count("1")
                cands.append((cost, o, d))
        cands.sort()
        step_ok = False
        for cost, o, d in cands[:tries]:
            s = [(ids[a], b) for a, b in seq + [(o, d)]]
            x = BT.x_query(E, L["root_id"], rec, s, cache)
            tr = {"seq": [list(t) for t in s], "x": x.get("y"), "x_status": x.get("teacher_status"), "x_kind": x.get("negative_kind"),
                  "x_phase": x.get("failed_phase"), "x_replay": x.get("independent_replay")}
            out["tries"].append(tr)
            if x.get("failed_phase") != f"relocation:{j}" and (x.get("y") == 1 or str(x.get("failed_phase", "")).startswith(("relocation:", "connector"))) \
                    and not str(x.get("failed_phase") or "").startswith(tuple(f"relocation:{i}" for i in range(j + 1))):
                seq.append((o, d)); cur[o] = d; step_ok = True
                break
        if not step_ok:
            break
    if len(seq) == len(M):
        s = [(ids[a], b) for a, b in seq]
        x = BT.x_query(E, L["root_id"], rec, s, cache)
        tr = {"seq": [list(t) for t in s], "x": x.get("y"), "x_status": x.get("teacher_status"), "x_phase": x.get("failed_phase"),
              "x_replay": x.get("independent_replay"), "final": True}
        if tr["x"] == 1:
            y = BT.y_query(E, L["root_id"], rec, s, cache)
            tr.update(y=y.get("y"), y_status=y.get("teacher_status"), y_replay=y.get("independent_replay"))
        out["tries"].append(tr)
    ok = [t for t in out["tries"] if t.get("x") == 1 and t.get("y") == 1]
    out["verdict"] = ("CERTIFIED_MIN_K" if ok and out["Y0"]["y"] == 0 else "WITNESS_Y0_NOT_0") if ok else "NO_WITNESS_FOUND"
    out["cpu_s"] = round(time.process_time() - t0, 1)
    return out


def main(table, layouts, outp, workers, tries=12):
    import multiprocessing as mp
    T = json.loads(Path(table).read_text())
    Ls = [json.loads(l) for l in open(layouts)]
    done = {json.loads(l)["root_id"] for l in open(outp)} if Path(outp).exists() else set()
    todo = [(T, L, tries) for L in Ls if L["root_id"] not in done]
    with mp.get_context("spawn").Pool(workers, maxtasksperchild=4) as pool, open(outp, "a") as f:
        for r in pool.imap_unordered(job, todo):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(json.dumps({k: r.get(k) for k in ("root_id", "K_lb", "verdict", "cpu_s")}), flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(os.path.abspath(a[0]), os.path.abspath(a[1]), os.path.abspath(a[2]), int(a[3]), int(a[4]) if len(a) > 4 else 12)
