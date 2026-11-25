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

CAPS = {"layouts": 200, "jobs": 1000, "cpu_h": 60.0, "workers": 36}   # owner raise 2026-11-26 01:25 IST (was 120 / 24 h / 16)
QUOTA = {("4", "B2C2"): 10, ("5", "B2C3"): 10}          # amendment A1 (2026-11-26, pre-seal): K_b = 3 routes dropped (ROUTE_TIME_CAP), see P1_COHORT.md
STYLE = {"B3C1": (3, 1), "B2C2": (2, 2), "B3C2": (3, 2), "B2C3": (2, 3)}
CHAIN_S = 900.0                     # chain-stage wall cap per layout (construction keeps the generator's own CONSTRUCT_S / CONSTRUCT_S_K)
GEN_WALL = 1200
GEN_CODE = "K45_GEN_V5 (A3: enablers may block the place side; most-constrained alternative parking cell; A2: probe only known-feasible azimuths, largest generator blocker, 12 candidate cells; A1: K_b=2 strata only, most-constrained mover first; 2026-11-26 IST: enabler parking avoids the target corridor; target-plans-after-parking check; movers = first tight set passing bd_3dt_plus.independent)"                     # fin3d administrative wall per certification sequence (UNRESOLVED_ADMIN -> rejected, never a label)
RESERVE_H = 0.6                     # dispatch headroom per running layout (CPU-h)
G = {}
BIG = {"shape": "cylinder", "size": 0.018, "height": 0.18}     # A2: the largest ordinary blocker of the generator's ranges (cylinder 0.013-0.018, height <= 0.18)


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


def movers_of(c):
    """The route construction's minimal repair: blockers cutting a tight feasible grasp (the fewest cuts), in the generator's order."""
    F0 = c["empty_solve"]["feasible_azimuths"]
    cut = {tuple(g["cell"]): set(g["blocks_azimuths"]) for g in c["greedy"]}
    cell_to = {tuple(v): o for o, v in c["cells"].items()}
    n = {a: sum(a in v for v in cut.values()) for a in F0}
    out = []
    for a in F0:
        if n[a] == min(n.values()):
            S = tuple(cell_to[x] for x in cut if a in cut[x])
            if S not in out:
                out.append(S)
    return out, min(n.values())


def chain(c, n_chain, rng, t0, movers):
    """Add exactly n_chain enabling obstacles.  For a mover B (route blockers in order, then depth 2 on chain obstacles): F_B = azimuths whose
    grasp plans B -> its parking cell in the FULL current scene; probe free cells within Chebyshev 2 of B's source with one standard obstacle
    (bd_3dt_plus.PROBE, the smallest intended blocker) and greedily cover F_B with <= the remaining chain budget; then verify with the real
    obstacles: B -> park(B) no longer plans; every new obstacle picks and parks from the original scene; with them parked B plans again.
    -> (objs, cells, {new id: blocked id}, parking) or Reject."""
    A, P = G["A"], G["P"]
    TS = A.env()["TS"]
    objs, cells = list(c["objs"]), {o: list(v) for o, v in c["cells"].items()}
    src, goal = tuple(c["src"]), tuple(c["goal"])
    park = {o: tuple(c["parking"][o][0]) for o in movers}
    avoid = {src, goal} | {(0, k) for k in range(A.GRID["C"])}
    route = set(P.line(src, goal)) | {(r + a, cc + b) for r, cc in P.line(src, goal) for a in (-1, 0, 1) for b in (-1, 0, 1)}
    park_avoid = avoid | P.hand_zone(src) | P.hand_zone(goal) | route          # = the route generator's own parking exclusion (base_avoid)
    blocked_by, left, queue = {}, n_chain, list(movers)

    def scene(extra):
        allo = objs + [x for x, _ in extra]
        cc = {**cells, **{x["id"]: list(p) for x, p in extra}}
        e = A.build(allo, cc); A.settle(e, cc)
        return e

    def azim(e, name, dst, only=None):
        """Feasible azimuths of name -> dst; with `only`, grasps of other azimuths are not planned (bd_3dt_plus.still_feasible's rule)."""
        i = e.obj_id(name); e.objects[i]["pos"] = e.obj_pos(i); q0 = e.q_now(); ok = set()
        for g in TS.grasp_poses(e.objects[i], e.table_z):
            a = g["azimuth_deg"]
            if (only is None or a in only) and a not in ok and e.plan_pick_place(name, tuple(dst), g, q_start=q0)["feasible"]:
                ok.add(a)
        return ok

    def plans(extra, name, dst):
        e = scene(extra)
        return A.query(e, name, list(dst))[0] is not None
    added = []
    occ_all = {tuple(v) for v in cells.values()} | {src, goal}
    for B in list(queue):                                                      # A3: most-constrained parking cell among the generator's alternatives
        alts = [tuple(x) for x in c["alt_parking"].get(B, [])[:3] if tuple(x) not in occ_all and tuple(x) not in {park[o] for o in park if o != B}]
        best = None
        for pB in alts:
            fb = azim(scene([]), B, pB)
            if fb and (best is None or len(fb) < len(best[1])):
                best = (pB, fb)
        if best:
            park[B] = best[0]
    Fm = {B: azim(scene(added), B, park[B]) for B in queue}
    queue.sort(key=lambda B: (len(Fm[B]) == 0, len(Fm[B]), B))                 # amendment A1: most-constrained blocker first
    while left > 0:
        if time.time() - t0 > CHAIN_S:
            raise A.Reject("CHAIN_TIME_CAP")
        if not queue:
            queue = [x["id"] for x, _ in added if x["id"] not in blocked_by.values()]      # depth 2: block a chain obstacle's own pick
            if not queue:
                raise A.Reject("CHAIN_NO_TARGET_LEFT")
        B = queue.pop(0)
        bcell = tuple(cells[B]) if B in cells else next(p for x, p in added if x["id"] == B)
        F = Fm[B] if B in Fm and not added else azim(scene(added), B, park[B])
        if not F:
            continue
        occ = {tuple(v) for v in cells.values()} | {p for _, p in added} | set(park.values()) | avoid
        cand = sorted((x for x in itertools.product(range(A.GRID["R"]), range(A.GRID["C"]))
                       if x not in occ and (1 <= A.cheb(x, bcell) <= 2 or A.cheb(x, park[B]) == 1)),           # A3: pick side or place side
                      key=lambda x: (min(A.cheb(x, bcell), A.cheb(x, park[B])), x))[:14]
        probe = {}
        for x in cand:
            if time.time() - t0 > CHAIN_S:
                raise A.Reject("CHAIN_TIME_CAP")
            pr = {**BIG, "id": "pz", "color": "red"}
            probe[x] = F - azim(scene(added + [(pr, x)]), B, park[B], only=F)
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
            news.append(({"id": nid, "shape": BIG["shape"], "size": BIG["size"], "height": BIG["height"],
                          "color": A.COLORS[(len(objs) + len(added) + j) % len(A.COLORS)]}, x))
        if plans(added + news, B, park[B]):
            continue                                                            # real obstacles do not block B
        occ2 = occ | set(pick)
        pk = {}
        for x, p in news:
            spot = next((q for q in P.parking_cells(p, park_avoid, occ2 | set(pk.values()), 4)
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
    e = A.build(objs, cells); A.settle(e, {**cells, **{o: list(park[o]) for o in park}})   # every mover + enabler parked: target must plan
    if A.query(e, "t0", list(goal))[0] is None:
        raise A.Reject("CHAIN_PARKING_BLOCKS_TARGET")
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
        mv_all, kmin = movers_of(c)
        out["route"] = {"K_by_construction": kmin, "tight_sets": [list(m) for m in mv_all]}
        if kmin != K_b or not mv_all or len(mv_all[0]) != K_b:
            raise A.Reject(f"ROUTE_K_MISMATCH:{kmin}")
        movers = None
        for S in mv_all:                                                       # the generator's own rule: first tight set passing independent()
            if P.independent(c["objs"], c["cells"], {o: c["parking"][o][0] for o in S}, list(S), tuple(c["goal"])):
                movers = list(S); break
        if movers is None:
            raise A.Reject("ROUTE_NO_INDEPENDENT_TIGHT_SET")
        out["route"]["movers"] = movers
        objs, cells, blocked_by, park = chain(c, n_chain, rng, time.time(), movers)
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
            order = [[o, list(park[o])] for o in order_of(movers, blocked_by, alt)]
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
    out.update(code=GEN_CODE, cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1), jobs=G["jobs"] - j0,
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
    """Deterministic attempt list per stratum (fixed seeds); dispatch order interleaves strata.  A2 attempts are numbered from 100."""
    out = {k: [] for k in QUOTA}
    for (K, style) in QUOTA:
        for n in range(300, 500):
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
        if (str(d["K"]), d["style"]) in ptr and "n" in d:
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
                acc[k] += bool(r.get("accepted"))
                print(f"{time.strftime('%H:%M:%S')} {rid} {r.get('reason')} cpu={r.get('cpu_s')} acc={dict((f'{a}{b}', v) for (a, b), v in acc.items())} "
                      f"used={used['layouts']}L/{used['jobs']}J/{used['cpu_s'] / 3600:.2f}h", flush=True)
        allr = [json.loads(l) for l in open(led) if l.strip()]                     # re-read: results of a draining earlier dispatcher count too
        used["cpu_s"] = sum(d.get("cpu_s", 0) for d in allr); used["jobs"] = sum(d.get("jobs", 0) for d in allr); used["layouts"] = len(allr)
        old = os.environ.get("K45_OLD_LOG")
        reserve = float(os.environ.get("K45_OLD_RESERVE_H", "0")) if old and "GEN_DONE" not in open(old).read() else 0.0
        cpu_h = (used["cpu_s"] + sum(time.time() - t for _, _, t in running.values())) / 3600 + reserve   # running wall = CPU upper proxy
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


def assemble(gen_dir, out_dir):
    """LOCAL (laptop): admitted roster = per stratum the ACCEPTED attempts in fixed attempt order, first QUOTA; disjointness vs history and V3.4
    (root id, construction seed, sha256, GEOM_V1 layout fp); private index + roots; public rows via benchmark.public.  No learned model."""
    import shutil
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path.home() / "Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-4-final-benchmark/approach_b_final/scripts"))
    import benchmark as BM
    import contracts as CT
    import v34_geomfp as GF
    gen, out = Path(gen_dir), Path(out_dir)
    (out / "roots").mkdir(parents=True, exist_ok=True)
    led = [json.loads(l) for l in open(gen / "ledger.jsonl") if l.strip()]
    A3 = Path.home() / "abf_v34"
    X = json.loads((A3 / "excl/EXCL3D.json").read_text()); XG = set(json.loads((A3 / "excl/EXCL3D_GEOM.json").read_text())["geom_fp"])
    coh = [json.loads(l) for l in open(A3 / "final/PRIVATE_INDEX.jsonl")]
    hist = {"rid": set(map(str, X["root_ids"])) | {c["root_id"] for c in coh}, "seed": set(map(str, X["seeds"])) | {str(c["construction_seed"]) for c in coh},
            "sha": set(map(str, X["root_sha256"])) | {c["root_sha256"] for c in coh}, "fp": XG | {c["layout_fp"] for c in coh}}
    rows, skip, seen = [], collections.Counter(), set()
    for (K, style), q in QUOTA.items():
        acc = sorted((d for d in led if d.get("accepted") and str(d["K"]) == K and d["style"] == style), key=lambda d: d["n"])
        for d in acc:
            if sum(1 for r in rows if r["K"] == K and r["style"] == style) >= q:
                skip["over_quota"] += 1; continue
            raw = (gen / "roots" / f"{d['root_id']}.json").read_bytes(); rec = json.loads(raw)
            h = hashlib.sha256(raw).hexdigest(); v = CT.view3d(rec); fp = GF.geom_fp(v)
            hit = [k for k, val in (("rid", d["root_id"]), ("seed", str(rec["ids"]["construction_seed"])), ("sha", h), ("fp", fp)) if val in hist[k]] + (["dup_fp"] if fp in seen else [])
            if hit:
                skip["|".join(hit)] += 1; continue
            seen.add(fp)
            shutil.copyfile(gen / "roots" / f"{d['root_id']}.json", out / "roots" / f"{d['root_id']}.json")
            rows.append({"root_id": d["root_id"], "domain": "3d", "K": K, "style": style, "label": rec["k45"]["label"], "path": f"roots/{d['root_id']}.json",
                         "abs_path": str(out / "roots" / f"{d['root_id']}.json"), "root_sha256": h, "layout_fp": fp, "construction_seed": rec["ids"]["construction_seed"],
                         "parent_family_id": rec["ids"]["parent_family_id"], "n_objects": len(rec["objects"]), "attempt": d["n"], "ids": v["ids"]})
    with open(out / "PRIVATE_INDEX.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    BM.public(str(out / "PUBLIC.jsonl"), index=str(out / "PRIVATE_INDEX.jsonl"))
    return {"admitted": len(rows), "by_stratum": dict(collections.Counter(f"K{r['K']}|{r['style']}" for r in rows)), "skipped": dict(skip),
            "labels": dict(collections.Counter(r["label"] for r in rows)), "n_objects": dict(collections.Counter(r["n_objects"] for r in rows))}


import collections  # noqa: E402


# ============================================================================== amendment A4 (owner 2026-11-26): historical-unexposed K4 + derived K5
def parent_info(rec):
    """-> (witness order [[o, [r, c]], ...], ids already chained (blocked by an enabler), enabler ids, family id) for a K4 parent root."""
    if "k45" in rec:                                                            # fresh K45 root
        cb = rec["construction"].get("chain_blocks", {})
        return rec["k45"]["witness"]["order"], set(cb.values()), set(cb), rec["ids"]["parent_family_id"]
    m = next(b for b in rec["labels"]["B"] if b.get("role") == "minimal" and b.get("y") == 1)   # historical: the generator's verified minimal B
    return [[o, list(d)] for o, d in m["sequence"]], set(), set(), rec["ids"].get("parent_family_id") or rec["ids"]["root_id"]


def certify(rec, orders, K, out):
    """Initial target y = 0; continuous witness (first order that verifies X, then its endpoint Y); (K-1)-subset shorter probe."""
    A = G["A"]
    cells = rec["initial_cells"]
    y0 = job_y(rec, cells)
    out["initial"] = {"y": y0.get("y"), "status": y0.get("status"), "resolution": y0.get("resolution"), "kind": initial_kind(rec)}
    if y0.get("resolution") != "EVALUATED" or y0.get("y") != 0:
        raise A.Reject("INITIAL_NOT_INFEASIBLE" if y0.get("y") == 1 else "INITIAL_UNRESOLVED")
    wit = None
    for order in orders:
        x = job_x(rec, order)
        out.setdefault("x_tries", []).append({"order": order, "x": x.get("x"), "status": x.get("status"), "phase": x.get("phase"), "resolution": x.get("resolution")})
        if x.get("x") == 1:
            y = job_y(rec, {**{k: list(v) for k, v in cells.items()}, **{o: d for o, d in order}})
            out["witness_y"] = {"y": y.get("y"), "status": y.get("status"), "resolution": y.get("resolution")}
            if y.get("y") == 1:
                wit = {"order": order, "x_witnesses": x["witnesses"], "y_witnesses": y["witnesses"], "dq_ready": x.get("dq_ready")}
            break
    if wit is None:
        raise A.Reject("NO_VERIFIED_TARGET_LENGTH_WITNESS")
    short = []
    for j in range(K):
        sub = [m for i, m in enumerate(wit["order"]) if i != j]
        y = job_y(rec, {**{k: list(v) for k, v in cells.items()}, **{o: d for o, d in sub}})
        r = {"omit": wit["order"][j][0], "y": y.get("y"), "resolution": y.get("resolution"), "status": y.get("status")}
        if y.get("y") == 1:
            x = job_x(rec, sub); r.update(x=x.get("x"), x_status=x.get("status"))
        short.append(r)
    shorter = any(r.get("y") == 1 and r.get("x") == 1 for r in short)
    return wit, short, shorter


def attempt_x(item):
    """A4 item: kind RECERT (historical K4, re-certified unchanged) or DERIVE (parent K4 + ONE enabler -> witness length 5); FRESH -> attempt()."""
    if item["kind"] == "FRESH":
        return {**attempt(item), "kind": "FRESH"}
    t0, c0 = time.time(), time.process_time(); cnt0 = dict(G["cnt"]); j0 = G["jobs"]
    out = {**item, "accepted": False}
    import numpy as np
    try:
        A, P = G["A"], G["P"]
        rec = json.loads(Path(item["parent_path"]).read_text())
        order, chained, enablers, fam = parent_info(rec)
        if item["kind"] == "RECERT":
            rec = json.loads(json.dumps(rec))
            wit, short, shorter = certify(rec, [order], 4, out)
            K = 4; extra = {"source": "HISTORICAL_UNEXPOSED_K4", "historical_verified_K": rec.get("verified_K")}
        else:
            rng = np.random.default_rng(item["seed"])
            objs, cells = list(rec["objects"]), {o: list(v) for o, v in rec["initial_cells"].items()}
            src, goal = tuple(rec["target_src"]), tuple(rec["goal"])
            park = {o: tuple(d) for o, d in order}
            TS = A.env()["TS"]

            def scene(extra=()):
                cc = {**cells, **{x["id"]: list(p) for x, p in extra}}
                e = A.build(objs + [x for x, _ in extra], cc); A.settle(e, cc); return e

            def azim(e, name, dst, only=None):
                i = e.obj_id(name); e.objects[i]["pos"] = e.obj_pos(i); q0 = e.q_now(); ok = set()
                for g in TS.grasp_poses(e.objects[i], e.table_z):
                    a = g["azimuth_deg"]
                    if (only is None or a in only) and a not in ok and e.plan_pick_place(name, tuple(dst), g, q_start=q0)["feasible"]:
                        ok.add(a)
                return ok
            cand_B = [o for o, _ in order if o not in chained]
            if item.get("mode") == "v2":                                     # A5: attempt j = (blocker j % n, destination (j // n) % 3)
                B = sorted(cand_B)[item["j"] % len(cand_B)]
                occ0 = {tuple(v) for v in cells.values()} | {src, goal} | {park[o] for o in park if o != B}
                alts = [park[B]] + [tuple(x) for x in rec.get("alt_parking", {}).get(B, []) if tuple(x) not in occ0 and tuple(x) != park[B]][:2]
                dk = (item["j"] // len(cand_B)) % 3
                if dk >= len(alts):
                    raise A.Reject("DERIVE_NO_SUCH_DESTINATION")
                park[B] = alts[dk]
                F = {B: azim(scene(), B, park[B])}
                if not F[B]:
                    raise A.Reject("DERIVE_MOVER_INFEASIBLE_AT_DESTINATION")
                order = [[o, list(park[o])] for o, _ in order]
            else:
                F = {B: azim(scene(), B, park[B]) for B in cand_B}
                cand_B = sorted([B for B in cand_B if F[B]], key=lambda B: (len(F[B]), B))
                if not cand_B:
                    raise A.Reject("DERIVE_NO_FEASIBLE_MOVER")
                B = cand_B[item["j"] % len(cand_B)]
            bcell = tuple(cells[B])
            route = set(P.line(src, goal)) | {(r + a, cc + b) for r, cc in P.line(src, goal) for a in (-1, 0, 1) for b in (-1, 0, 1)}
            avoid = {src, goal} | {(0, k) for k in range(A.GRID["C"])}
            park_avoid = avoid | P.hand_zone(src) | P.hand_zone(goal) | route
            occ = {tuple(v) for v in cells.values()} | set(park.values()) | avoid
            cand = sorted((x for x in itertools.product(range(A.GRID["R"]), range(A.GRID["C"])) if x not in occ and (1 <= A.cheb(x, bcell) <= 2 or A.cheb(x, park[B]) == 1)),
                          key=lambda x: (min(A.cheb(x, bcell), A.cheb(x, park[B])), x))[:14]
            nid = f"o{len(objs) - 1:02d}"
            while any(o["id"] == nid for o in objs):
                nid = f"o{int(nid[1:]) + 1:02d}"
            new = {"id": nid, **BIG, "color": A.COLORS[len(objs) % len(A.COLORS)]}
            hit = None
            for x in cand:
                if time.time() - t0 > CHAIN_S:
                    raise A.Reject("DERIVE_TIME_CAP")
                if azim(scene([(new, x)]), B, park[B], only=F[B]):
                    continue                                                    # ONE enabler must cover every feasible azimuth of B
                pk = next((q for q in P.parking_cells(x, park_avoid, occ | {x}, 4) if A.query(scene([(new, x)]), nid, list(q))[0] is not None), None)
                if pk is None:
                    continue
                if A.query(scene([(new, tuple(pk))]), B, list(park[B]))[0] is None:
                    continue
                e = A.build(objs + [new], {**cells, nid: list(x)}); A.settle(e, {**cells, **{o: list(d) for o, d in park.items()}, nid: list(pk)})
                if A.query(e, "t0", list(goal))[0] is None:
                    continue
                hit = (x, tuple(pk)); break
            if hit is None:
                raise A.Reject("DERIVE_NO_SINGLE_COVER")
            x, pk = hit
            objs.append(new); cells[nid] = list(x)
            idx = [o for o, _ in order].index(B)
            o1 = order[:idx] + [[nid, list(pk)]] + order[idx:]
            o2 = [[nid, list(pk)]] + order
            Gm = A.env()
            rec = {**{k: rec[k] for k in ("goal", "target_src") if k in rec}, "ids": {"root_id": item["root_id"], "construction_seed": item["seed"], "parent_family_id": fam,
                   "parent_root_id": rec["ids"]["root_id"], "config_hash": Gm["config_hash"], "teacher_version": A.TEACHER_VERSION, "robot_protocol": Gm["protocol"]},
                   "domain": "3ds66", "objects": objs, "initial_cells": cells, "geometry": Gm["geometry"], "source_files": Gm["source_files"],
                   "construction": {"generator": "K45_DERIVE_V1 (parent K4 + one enabler)", "parent_root_id": rec["ids"]["root_id"], "enabler": nid, "blocks": B,
                                    "enabler_cell": list(x), "enabler_parking": list(pk), "parent_chained": sorted(chained)}}
            wit, short, shorter = certify(rec, [o1, o2] if o2 != o1 else [o1], 5, out)
            K = 5; extra = {"source": "DERIVED_FROM_K4_PARENT", "parent_root_id": rec["construction"]["parent_root_id"]}
        rec["k45"] = {"witness": wit, "initial": out["initial"], "shorter_probe": short, "label": f"SHORTER_WITNESSED_LE_{K - 1}" if shorter else f"WITNESS_LEN_{K}_MIN_UNKNOWN", **extra}
        Path(item["out"], "roots").mkdir(parents=True, exist_ok=True)
        tmp = Path(item["out"], "roots", item["root_id"] + ".json.tmp"); tmp.write_text(json.dumps(rec, default=G["bc"]._jd)); os.replace(tmp, tmp.with_suffix(""))
        out.update(accepted=not shorter, label=rec["k45"]["label"], n_objects=len(rec["objects"]), reason="ACCEPTED" if not shorter else "SHORTER_WITNESSED")
    except Exception as e:  # noqa: BLE001
        out["reason"] = (str(e)[:160] if type(e).__name__ == "Reject" else f"ERROR:{type(e).__name__}:{str(e)[:160]}")
        if type(e).__name__ != "Reject":
            out["trace"] = traceback.format_exc()[-800:]
    out.update(code="K45_GEN_A4", cpu_s=round(time.process_time() - c0, 1), wall_s=round(time.time() - t0, 1), jobs=G["jobs"] - j0,
               planner_calls={k: G["cnt"][k] - cnt0[k] for k in cnt0}, utc=time.strftime("%FT%TZ", time.gmtime()))
    return out


def run_items(items_file, outdir, workers, cpu_lo, cap_h, k5_quota=10):
    """A4 dispatcher for an explicit item list (one host); per-host CPU cap with running-wall headroom; stops DERIVE dispatch at k5_quota."""
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    led = out / "ledger_a4.jsonl"
    done = {json.loads(l)["root_id"] for l in open(led)} if led.exists() else set()
    todo = [it for it in json.loads(Path(items_file).read_text()) if it["root_id"] not in done]
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    pool = mp.get_context("spawn").Pool(int(workers), initializer=boot, initargs=(str(out / "store"),), maxtasksperchild=3)
    running, f, i = {}, open(led, "a"), 0
    while True:
        allr = [json.loads(l) for l in open(led) if l.strip()]
        k5 = sum(1 for d in allr if d.get("accepted") and d["kind"] == "DERIVE")
        k5_quota = int(os.environ.get("K45_K5_NEED", k5_quota))
        for rid, (ar, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(rid)
                f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
                print(f"{time.strftime('%H:%M:%S')} {rid} {r.get('reason')} cpu={r.get('cpu_s')} jobs={r.get('jobs')}", flush=True)
        cpu_h = (sum(d.get("cpu_s", 0) for d in allr) + sum(time.time() - t for _, t in running.values())) / 3600
        if cpu_h >= float(cap_h) - 0.05:
            pool.terminate(); print("A4_DONE CAP_HARD_STOP", flush=True); break
        k4f = sum(1 for d in allr if d.get("accepted") and d["kind"] == "FRESH")
        while i < len(todo) and ((todo[i]["kind"] == "DERIVE" and k5 >= k5_quota) or (todo[i]["kind"] == "FRESH" and k4f >= int(os.environ.get("K45_K4_NEED", "99")))):
            i += 1
        if i < len(todo) and len(running) < int(workers) and cpu_h + (len(running) + 1) * 0.5 < float(cap_h) and not (out / "STOP").exists():
            it = {**todo[i], "out": str(out)}; i += 1
            running[it["root_id"]] = (pool.apply_async(attempt_x, (it,)), time.time()); continue
        if not running:
            print("A4_DONE", "ALL" if i >= len(todo) else "STOP_OR_CAP", f"cpu_h={cpu_h:.2f}", flush=True); break
        time.sleep(5)
    for rid, (_, t) in running.items():
        f.write(json.dumps({"root_id": rid, "kind": "?", "accepted": False, "reason": "CENSORED_AT_CAP", "cpu_s": round(time.time() - t, 1)}) + "\n")
    f.close()


def assemble2(sources, out_dir):
    """A4 roster (LOCAL): K4 = fresh accepted (attempt order) then re-certified historical-unexposed K4 (sha order) up to 10;
    K5 = accepted derived roots, first pass one per parent (fresh parents first, then historical), then fill by (parent order, j), up to 10.
    Checks: never in the 3D TRAIN/VAL/TEST snapshot, never in the V3.4 cohort, distinct root ids / sha / GEOM_V1 fp within the roster."""
    import shutil
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path.home() / "Desktop/boltzmann_lfd/.claude/worktrees/approach-b-v3-4-final-benchmark/approach_b_final/scripts"))
    import benchmark as BM
    import contracts as CT
    import v34_geomfp as GF
    out = Path(out_dir); (out / "roots").mkdir(parents=True, exist_ok=True)
    snap = {json.loads(l)["root_id"] for l in open(Path.home() / "abf_v32/snap_out/snapshot/abf_v32_fb0eef4f5ff433ee/data3d.jsonl")}
    coh = {json.loads(l)["root_id"] for l in open(Path.home() / "abf_v34/final/PRIVATE_INDEX.jsonl")}
    led = []
    for src in sources.split(","):
        d = Path(src)
        for f in ("ledger.jsonl", "ledger_a4.jsonl"):
            if (d / f).exists():
                led += [{**json.loads(l), "_dir": str(d)} for l in open(d / f) if l.strip()]
    acc = [x for x in led if x.get("accepted")]
    fresh = sorted((x for x in acc if x.get("style") == "B2C2" and "kind" not in x), key=lambda x: x["n"])
    hist = sorted((x for x in acc if x.get("kind") == "RECERT"), key=lambda x: hashlib.sha256(("K45_HIST|" + x["root_id"]).encode()).hexdigest())
    porder = [x["root_id"] for x in fresh] + [x["root_id"] for x in hist] + sorted({x["parent_id"] for x in acc if x.get("kind") == "DERIVE"})
    der = [x for x in acc if x.get("kind") == "DERIVE"]
    der.sort(key=lambda x: (porder.index(x["parent_id"]) if x["parent_id"] in porder else 99, x["j"]))
    k5, seenp = [], set()
    for x in der:                                                                # first pass: one child per parent
        if x["parent_id"] not in seenp and len(k5) < 10:
            k5.append(x); seenp.add(x["parent_id"])
    for x in der:
        if x not in k5 and len(k5) < 10:
            k5.append(x)
    picks = [("4", "FRESH", x) for x in fresh][:10]
    picks += [("4", "HISTORICAL_UNEXPOSED", x) for x in hist][:max(0, 10 - len(picks))]
    picks += [("5", "DERIVED", x) for x in k5]
    rows, fps, issues = [], set(), collections.Counter()
    for K, src_kind, x in picks:
        p = Path(x["_dir"]) / "roots" / f"{x['root_id']}.json"
        raw = p.read_bytes(); rec = json.loads(raw); h = hashlib.sha256(raw).hexdigest()
        v = CT.view3d(rec); fp = GF.geom_fp(v)
        if x["root_id"] in snap or x["root_id"] in coh:
            issues["exposed"] += 1; continue
        if fp in fps:
            issues["dup_fp"] += 1
        fps.add(fp)
        shutil.copyfile(p, out / "roots" / p.name)
        rows.append({"root_id": x["root_id"], "domain": "3d", "K": K, "source": src_kind, "label": rec["k45"]["label"], "path": f"roots/{p.name}",
                     "abs_path": str(out / "roots" / p.name), "root_sha256": h, "layout_fp": fp, "parent_family_id": rec["ids"].get("parent_family_id"),
                     "parent_root_id": rec["ids"].get("parent_root_id"), "n_objects": len(rec["objects"]), "ids": v["ids"]})
    with open(out / "PRIVATE_INDEX.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    BM.public(str(out / "PUBLIC.jsonl"), index=str(out / "PRIVATE_INDEX.jsonl"))
    return {"admitted": len(rows), "by_K_source": dict(collections.Counter(f"K{r['K']}|{r['source']}" for r in rows)), "issues": dict(issues),
            "labels": dict(collections.Counter(r["label"] for r in rows)), "n_objects": dict(collections.Counter(r["n_objects"] for r in rows)),
            "k5_parents": dict(collections.Counter(r["parent_root_id"] for r in rows if r["K"] == "5")),
            "available": {"fresh_K4": len(fresh), "recert_K4": len(hist), "derived_K5": len(der)}}


if __name__ == "__main__":
    if sys.argv[1] == "assemble2":
        print(json.dumps(assemble2(sys.argv[2], sys.argv[3]), indent=1))
    elif sys.argv[1] == "run_items":
        run_items(*sys.argv[2:7])
    elif sys.argv[1] == "assemble":
        print(json.dumps(assemble(sys.argv[2], sys.argv[3]), indent=1))
    elif sys.argv[1] == "smoke":                                                 # one layout in-process (counts toward the ledger of OUT)
        boot(str(Path(sys.argv[2]) / "store"))
        it = {**items()[(sys.argv[3], sys.argv[4])][int(sys.argv[5])], "out": sys.argv[2]}
        r = attempt(it)
        with open(Path(sys.argv[2]) / "ledger.jsonl", "a") as f:
            f.write(json.dumps(r) + "\n")
        print(json.dumps({k: v for k, v in r.items() if k not in ("trace",)}, default=str)[:3000])
    else:
        main(*sys.argv[1:4])
