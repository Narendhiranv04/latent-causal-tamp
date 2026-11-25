#!/usr/bin/env python3
"""Evaluator-only K4/K5 3D scene construction + witness certification (gvlab2, the unchanged SHELF66V3 teacher via fin3d).  Never imported
by the planner.  Construction = the existing route generator (bd_3dt_plus.construct, requested K_b in {2, 3}: K_b direct blockers of every
feasible target grasp, each pickable / parkable from the original scene) + n_chain ENABLING obstacles: a new ordinary obstacle next to a
blocker B (or next to an earlier chain obstacle, depth 2) such that B's pick-and-place to its parking cell no longer plans from the original
scene, the new obstacle itself picks and parks from the original scene, and after it is parked B plans again.  Target witness length
K = K_b + n_chain (K4: 3+1 / 2+2; K5: 3+2 / 2+3).  All destinations are free in the original scene, distinct, not the goal.
Certification per layout (counted jobs; a job = one complete-plan X run or one endpoint Y run of fin3d):
  1 initial target query from q_ready (Y on the original scene): y = 0 required (kind CERTIFIED / NO_PLAN_FOUND recorded)
  2 continuous witness: fin3d.run_x(order) (carried arm state + CONNECTOR_TO_QREADY_V1) and fin3d.run_y(endpoint); X = Y = 1 required
    (one alternative block order if the first X fails)
  3 shorter-repair probe: Y on each (K-1)-subset endpoint of the witness; a Y = 1 there is then X-checked; a verified shorter repair
    -> SHORTER_WITNESSED (excluded from the stratum).  Minimum K is NOT certified (planner-relative probes): label WITNESS_LEN_K_MIN_UNKNOWN.
Instrumentation (process-local, behaviour unchanged): every XArm7TableEnv.plan_pick_place / plan_free_move call is counted.
Dispatcher caps (authorized 2026-11-25): <= 120 layouts, <= 1,000 jobs, <= 24 worker CPU-h (live /proc accounting of running workers,
dispatch stops with in-flight headroom, hard stop at cap), <= 16 workers.  No retries, no replacement.
    $PY3D generate.py OUT WORKERS CPU_LO      (env: k3abl env.sh; FIN3D_STORE set below)"""
from __future__ import annotations

import hashlib, itertools, json, multiprocessing as mp, os, signal, sys, time, traceback
from pathlib import Path

CAPS = {"layouts": 120, "jobs": 1000, "cpu_h": 24.0, "workers": 16}
QUOTA = {("4", "B3C1"): 5, ("4", "B2C2"): 5, ("5", "B3C2"): 5, ("5", "B2C3"): 5}
STYLE = {"B3C1": (3, 1), "B2C2": (2, 2), "B3C2": (3, 2), "B2C3": (2, 3)}
CHAIN_S = 900.0                     # chain-stage wall cap per layout (construction keeps the generator's own CONSTRUCT_S / CONSTRUCT_S_K)
GEN_WALL = 1200                     # fin3d administrative wall per certification sequence (UNRESOLVED_ADMIN -> rejected, never a label)
RESERVE_H = 0.6                     # dispatch headroom per running layout (CPU-h)
G = {}


# ------------------------------------------------------------------------------------------------------------- worker
def boot(store):
    os.environ["FIN3D_STORE"] = store
    sys.path.insert(0, os.environ["FIN3D_CODE"])
    import fin3d as F
    F.boot()
    F.WALL = GEN_WALL
    A, bc = F.Q._M["A"], F.Q._M["bc"]
    import bd_3dt_plus as P
    TS = A.env()["TS"]
    cnt = {"plan_pick_place": 0, "plan_free_move": 0}
    for name in cnt:
        orig = getattr(TS.XArm7TableEnv, name)

        def wrap(self, *a, _o=orig, _n=name, **k):
            cnt[_n] += 1
            return _o(self, *a, **k)
        setattr(TS.XArm7TableEnv, name, wrap)
    G.update(F=F, A=A, P=P, bc=bc, cnt=cnt, jobs=0)


def spec_for(K_b, rng):
    return {"K": K_b, "distractors": ["0", "1-2"][int(rng.integers(2))], "source": ["near", "mid"][int(rng.integers(2))],
            "displacement": ["short", "medium", "long"][int(rng.integers(3))], "mechanism": "mixed", "parking": "one",
            "distractor_role": ["near_T", "near_goal", "near_path", "far"][int(rng.integers(4))], "start_pose": "home"}


def chain(c, n_chain, rng, t0):
    """Add exactly n_chain enabling obstacles.  For a mover B (route blockers in order, then depth 2 on chain obstacles): F_B = azimuths whose
    grasp plans B -> its parking cell in the FULL current scene; probe free cells within Chebyshev 2 of B's source with one standard obstacle
    (bd_3dt_plus.PROBE, the smallest intended blocker) and greedily cover F_B with <= the remaining chain budget; then verify with the real
    obstacles: B -> park(B) no longer plans; every new obstacle picks and parks from the original scene; with them parked B plans again.
    -> (objs, cells, {new id: blocked id}, parking) or Reject."""
    A, P = G["A"], G["P"]
    TS = A.env()["TS"]
    objs, cells = list(c["objs"]), {o: list(v) for o, v in c["cells"].items()}
    src, goal = tuple(c["src"]), tuple(c["goal"])
    park = {o: tuple(c["parking"][o][0]) for o in c["intended"]}
    avoid = {src, goal} | {(0, k) for k in range(A.GRID["C"])}
    blocked_by, left, queue = {}, n_chain, list(c["intended"])

    def scene(extra):
        allo = objs + [x for x, _ in extra]
        cc = {**cells, **{x["id"]: list(p) for x, p in extra}}
        e = A.build(allo, cc); A.settle(e, cc)
        return e

    def azim(e, name, dst):
        i = e.obj_id(name); e.objects[i]["pos"] = e.obj_pos(i); q0 = e.q_now(); ok = set()
        for g in TS.grasp_poses(e.objects[i], e.table_z):
            if g["azimuth_deg"] not in ok and e.plan_pick_place(name, tuple(dst), g, q_start=q0)["feasible"]:
                ok.add(g["azimuth_deg"])
        return ok

    def plans(extra, name, dst):
        e = scene(extra)
        return A.query(e, name, list(dst))[0] is not None
    added = []
    while left > 0:
        if time.time() - t0 > CHAIN_S:
            raise A.Reject("CHAIN_TIME_CAP")
        if not queue:
            queue = [x["id"] for x, _ in added if x["id"] not in blocked_by.values()]      # depth 2: block a chain obstacle's own pick
            if not queue:
                raise A.Reject("CHAIN_NO_TARGET_LEFT")
        B = queue.pop(0)
        bcell = tuple(cells[B]) if B in cells else next(p for x, p in added if x["id"] == B)
        F = azim(scene(added), B, park[B])
        if not F:
            continue
        occ = {tuple(v) for v in cells.values()} | {p for _, p in added} | set(park.values()) | avoid
        cand = sorted((x for x in itertools.product(range(A.GRID["R"]), range(A.GRID["C"])) if x not in occ and 1 <= A.cheb(x, bcell) <= 2),
                      key=lambda x: (A.cheb(x, bcell), x))[:10]
        probe = {}
        for x in cand:
            pr = {**P.PROBE, "id": "pz", "color": "red"}
            probe[x] = F - azim(scene(added + [(pr, x)]), B, park[B])
        pick, need = [], set(F)
        while need and len(pick) < left:
            x = max((x for x in cand if x not in pick), key=lambda x: (len(probe[x] & need), -A.cheb(x, bcell), x), default=None)
            if x is None or not probe[x] & need:
                break
            pick.append(x); need -= probe[x]
        if need:
            continue                                                            # this mover cannot be covered within the budget
        news = []
        for j, x in enumerate(pick):
            nid = f"o{len(objs) - 1 + len(added) + j:02d}"
            news.append(({"id": nid, "shape": P.PROBE["shape"], "size": P.PROBE["size"], "height": float(rng.uniform(0.12, 0.16)),
                          "color": A.COLORS[(len(objs) + len(added) + j) % len(A.COLORS)]}, x))
        if plans(added + news, B, park[B]):
            continue                                                            # real obstacles do not block B
        occ2 = occ | set(pick)
        pk = {}
        for x, p in news:
            spot = next((q for q in P.parking_cells(p, avoid | P.hand_zone(src) | P.hand_zone(goal), occ2 | set(pk.values()), 4)
                         if plans(added + news, x["id"], q)), None)
            if spot is None:
                break
            pk[x["id"]] = tuple(spot)
        if len(pk) < len(news):
            continue                                                            # a new obstacle cannot pick / park from the original scene
        moved = [(x, pk[x["id"]]) for x, _ in news]
        if not plans(added + moved, B, park[B]):
            continue                                                            # B still blocked after the enablers are parked
        for x, p in news:
            added.append((x, p)); park[x["id"]] = pk[x["id"]]; blocked_by[x["id"]] = B
        left -= len(news)
    for x, p in added:
        objs.append(x); cells[x["id"]] = list(p)
    return objs, cells, blocked_by, park


def order_of(intended, blocked_by, alt=False):
    """Dependency-respecting witness order: for each blocker (in order), its chain obstacles deepest first, then the blocker itself."""
    pre = {}
    for n, t in blocked_by.items():
        pre.setdefault(t, []).append(n)

    def expand(o):
        out = []
        for n in pre.get(o, []):
            out += expand(n)
        return out + [o]
    blocks = [expand(o) for o in intended]
    if alt:
        blocks = blocks[::-1]
    return [o for b in blocks for o in b]


def job_y(rec, cells):
    G["jobs"] += 1
    return G["F"].capped(G["F"].run_y, rec, cells)


def job_x(rec, order):
    G["jobs"] += 1
    return G["F"].capped(G["F"].run_x, rec, order)


def initial_kind(rec):
    A = G["A"]
    e = A.build(rec["objects"], rec["initial_cells"]); A.settle(e, rec["initial_cells"])
    p, qi = A.query(e, "t0", tuple(rec["goal"]))
    return None if p is not None else A.label(None, qi)["negative_kind"]


def attempt(item):
    t0, c0 = time.time(), time.process_time()
    cnt0 = dict(G["cnt"]); j0 = G["jobs"]
    K, style, seed = item["K"], item["style"], item["seed"]
    K_b, n_chain = STYLE[style]
    rid = item["root_id"]
    out = {**item, "accepted": False}
    import numpy as np
    rng = np.random.default_rng(seed)
    try:
        A, P, F = G["A"], G["P"], G["F"]
        spec = spec_for(K_b, rng)
        out["spec"] = spec
        c = P.construct(spec, seed, rid)
        objs, cells, blocked_by, park = chain(c, n_chain, rng, time.time())
        Gm = A.env()
        rec = {"ids": {"root_id": rid, "construction_seed": seed, "parent_family_id": "k45-" + hashlib.sha256(rid.encode()).hexdigest()[:10],
                       "config_hash": Gm["config_hash"], "teacher_version": A.TEACHER_VERSION, "robot_protocol": Gm["protocol"]},
               "domain": "3ds66", "spec": spec, "objects": objs, "initial_cells": cells, "target_src": c["src"], "goal": c["goal"],
               "geometry": Gm["geometry"], "source_files": Gm["source_files"], "roles": {**c["roles"], **{n: "chain_enabler" for n in blocked_by}},
               "construction": {**c["construction"], "k45_style": style, "K_b": K_b, "n_chain": n_chain, "chain_blocks": blocked_by,
                                "generator": "K45_ROUTE_PLUS_CHAIN_V1 over " + P.GENERATOR_VERSION}}
        goal = tuple(c["goal"])
        occ0 = {tuple(v) for v in cells.values()}
        assert all(tuple(p) not in occ0 and tuple(p) != goal for p in park.values()) and len(set(park.values())) == len(park)
        y0 = job_y(rec, cells)
        out["initial"] = {"y": y0.get("y"), "status": y0.get("status"), "resolution": y0.get("resolution"), "kind": initial_kind(rec)}
        if y0.get("resolution") != "EVALUATED" or y0.get("y") != 0:
            raise A.Reject("INITIAL_NOT_INFEASIBLE" if y0.get("y") == 1 else "INITIAL_UNRESOLVED")
        wit = None
        for alt in (False, True):
            order = [[o, list(park[o])] for o in order_of(c["intended"], blocked_by, alt)]
            assert len(order) == K
            x = job_x(rec, order)
            out.setdefault("x_tries", []).append({"order": order, "x": x.get("x"), "status": x.get("status"), "phase": x.get("phase"), "resolution": x.get("resolution")})
            if x.get("x") == 1:
                ycells = {**{k: list(v) for k, v in cells.items()}, **{o: d for o, d in order}}
                y = job_y(rec, ycells)
                out["witness_y"] = {"y": y.get("y"), "status": y.get("status"), "resolution": y.get("resolution")}
                if y.get("y") == 1:
                    wit = {"order": order, "x_witnesses": x["witnesses"], "y_witnesses": y["witnesses"], "dq_ready": x.get("dq_ready")}
                break
        if wit is None:
            raise A.Reject("NO_VERIFIED_TARGET_LENGTH_WITNESS")
        short = []
        for j in range(K):                                                  # shorter-repair probe: every (K-1)-subset endpoint
            sub = [m for i, m in enumerate(wit["order"]) if i != j]
            y = job_y(rec, {**{k: list(v) for k, v in cells.items()}, **{o: d for o, d in sub}})
            r = {"omit": wit["order"][j][0], "y": y.get("y"), "resolution": y.get("resolution"), "status": y.get("status")}
            if y.get("y") == 1:
                x = job_x(rec, sub)
                r.update(x=x.get("x"), x_status=x.get("status"))
            short.append(r)
        out["shorter_probe"] = short
        shorter = any(r.get("y") == 1 and r.get("x") == 1 for r in short)
        rec["k45"] = {"witness": wit, "initial": out["initial"], "shorter_probe": short, "label": f"SHORTER_WITNESSED_LE_{K - 1}" if shorter else f"WITNESS_LEN_{K}_MIN_UNKNOWN",
                      "K_by_construction_route_part": c["construction"].get("K_by_construction"), "parking": {o: list(v) for o, v in park.items()}}
        Path(item["out"], "roots").mkdir(parents=True, exist_ok=True)
        tmp = Path(item["out"], "roots", rid + ".json.tmp"); tmp.write_text(json.dumps(rec, default=G["bc"]._jd)); os.replace(tmp, tmp.with_suffix(""))
        out.update(accepted=not shorter, label=rec["k45"]["label"], n_objects=len(objs), reason="ACCEPTED" if not shorter else "SHORTER_WITNESSED")
    except Exception as e:  # noqa: BLE001
        out["reason"] = (str(e)[:160] if type(e).__name__ == "Reject" else f"ERROR:{type(e).__name__}:{str(e)[:160]}")
        if type(e).__name__ != "Reject":
            out["trace"] = traceback.format_exc()[-800:]
    out.update(cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1), jobs=G["jobs"] - j0,
               planner_calls={k: G["cnt"][k] - cnt0[k] for k in cnt0}, utc=time.strftime("%FT%TZ", time.gmtime()))
    return out


# ------------------------------------------------------------------------------------------------------------- dispatcher
def proc_cpu(pid):
    try:
        f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")
    except OSError:
        return 0.0


def items():
    """Deterministic attempt list per stratum (fixed seeds); dispatch order interleaves strata."""
    out = {k: [] for k in QUOTA}
    for (K, style) in QUOTA:
        for n in range(40):
            rid = f"3ds66-k45-{style.lower()}-{n:03d}"
            out[(K, style)].append({"root_id": rid, "K": int(K), "style": style, "seed": int(hashlib.sha256(("K45GEN|" + rid).encode()).hexdigest()[:8], 16), "n": n})
    return out


def main(outdir, workers, cpu_lo):
    workers = min(int(workers), CAPS["workers"])
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    led = out / "ledger.jsonl"
    done = [json.loads(l) for l in open(led)] if led.exists() else []
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + workers)))
    pool = mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(str(out / "store"),), maxtasksperchild=4)
    queue = items(); ptr = {k: 0 for k in queue}
    for d in done:
        ptr[(str(d["K"]), d["style"])] = max(ptr[(str(d["K"]), d["style"])], d["n"] + 1)
    acc = {k: sum(1 for d in done if d.get("accepted") and (str(d["K"]), d["style"]) == k) for k in QUOTA}
    used = {"layouts": len(done), "jobs": sum(d.get("jobs", 0) for d in done), "cpu_s": sum(d.get("cpu_s", 0) for d in done)}
    running, f = {}, open(led, "a")
    stop_reason = None
    while True:
        live = sum(proc_cpu(p.pid) for p in pool._pool)                           # includes boot + finished-task CPU of live workers (conservative)
        for rid, (ar, k, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(rid)
                f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
                used["layouts"] += 1; used["jobs"] += r.get("jobs", 0); used["cpu_s"] += r.get("cpu_s", 0)
                acc[k] += bool(r.get("accepted"))
                print(f"{time.strftime('%H:%M:%S')} {rid} {r.get('reason')} cpu={r.get('cpu_s')} acc={dict((f'{a}{b}', v) for (a, b), v in acc.items())} "
                      f"used={used['layouts']}L/{used['jobs']}J/{used['cpu_s'] / 3600:.2f}h", flush=True)
        cpu_h = (used["cpu_s"] + sum(time.time() - t for _, _, t in running.values())) / 3600     # wall of running layouts as CPU upper proxy
        if cpu_h >= CAPS["cpu_h"] - 0.05 or used["jobs"] >= CAPS["jobs"] - 5:
            stop_reason = "CAP_HARD_STOP"; pool.terminate(); break
        open_k = [k for k in QUOTA if acc[k] + sum(1 for (_, kk, _) in running.values() if kk == k) * 0.4 < QUOTA[k] and ptr[k] < len(queue[k])]
        can = (len(running) < workers and used["layouts"] + len(running) < CAPS["layouts"]
               and cpu_h + (len(running) + 1) * RESERVE_H < CAPS["cpu_h"] and used["jobs"] + (len(running) + 1) * 12 < CAPS["jobs"])
        if can and open_k and not (out / "STOP").exists():
            k = min(open_k, key=lambda k: (acc[k] / QUOTA[k], ptr[k], k))
            it = {**queue[k][ptr[k]], "out": str(out)}; ptr[k] += 1
            running[it["root_id"]] = (pool.apply_async(attempt, (it,)), k, time.time())
            continue
        if not running:
            stop_reason = "QUOTA_FILLED" if all(acc[k] >= QUOTA[k] for k in QUOTA) else "NO_DISPATCH_ALLOWED (caps / stop / attempts)"
            break
        time.sleep(5)
    for rid, (_, k, t) in running.items():
        f.write(json.dumps({"root_id": rid, "K": int(k[0]), "style": k[1], "accepted": False, "reason": "CENSORED_AT_CAP", "wall_s": round(time.time() - t, 1)}) + "\n")
    f.close()
    (out / "GEN_SUMMARY.json").write_text(json.dumps({"stop": stop_reason, "used": used, "accepted": {f"{a}|{b}": v for (a, b), v in acc.items()}, "caps": CAPS,
                                                     "quota": {f"{a}|{b}": v for (a, b), v in QUOTA.items()}, "utc": time.strftime("%FT%TZ", time.gmtime())}, indent=1))
    print("GEN_DONE", stop_reason, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "smoke":                                                 # one layout in-process (counts toward the ledger of OUT)
        boot(str(Path(sys.argv[2]) / "store"))
        it = {**items()[(sys.argv[3], sys.argv[4])][int(sys.argv[5])], "out": sys.argv[2]}
        r = attempt(it)
        with open(Path(sys.argv[2]) / "ledger.jsonl", "a") as f:
            f.write(json.dumps(r) + "\n")
        print(json.dumps({k: v for k, v in r.items() if k not in ("trace",)}, default=str)[:3000])
    else:
        main(*sys.argv[1:4])
