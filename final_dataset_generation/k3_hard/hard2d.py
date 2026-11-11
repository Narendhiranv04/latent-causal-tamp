#!/usr/bin/env python3
"""HARDK3_2D_V1 -- hard-order K3 search on existing verified 2D K3 layouts (laptop; namespace D2H_*).

Same pinned teacher and order path as DEPSEEK2D_V1 (perm2d.evaluate == bd_2d seq; bd_2d.teach unmodified, same POOL_CAP/ADMIN rule).
Per layout (an original verified K3 root) we start from the most order-constrained KNOWN assignment of that layout (original or an
accepted DEPSEEK2D child) and run a greedy, precedence-targeted re-parking search:
  * a successful order s and a pair (U before V in s) not yet forced: re-park V's destination next to U's INITIAL cell (blocks U's pick
    if V is parked first -> forces U before V; s stays feasible) or next to U's destination (blocks U's placement).
  * pairs are ranked by how many currently-successful orders the new constraint would remove while keeping >= 1.
  * a candidate is evaluated order by order (currently-successful orders first) and dropped as soon as it cannot improve (n_success >=
    current); an improvement (1 <= ns < current) becomes the new current assignment; stop at ns = 1 or budget.
Rules (asserted): every destination is free in the ORIGINAL scene, distinct, never an initial cell (no slot exchange / occupancy chain),
never within 1 of the target start/goal; the robot state is carried (seq path unchanged); budgets unchanged; unresolved != failure.
The best improved assignment is then labelled from scratch by bd_2d.teach and kept only if verified K = 3 with the same assignment;
all 6 orders are stored.  Atomic per-root outputs (k3_hard/d2/store), resumable ledger (k3_hard/d2/ledger.jsonl).

  hard2d.py JOBS.json WORKERS"""
import hashlib, itertools, json, math, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent.parent / "order_classification_2d"))
import perm2d as P  # noqa: E402

OUT = Path(os.environ.get("HK_OUT", str(H / "d2")))
GEN = "BD_GEN_V1+DEPSEEK2D_V1+HARDK3_2D_V1"
MAXC = int(os.environ.get("HK_MAXC", "30"))            # candidate assignments per job
CPU_CAP = float(os.environ.get("HK_CPU_CAP", "2400"))  # search CPU-s per job (teach excluded)
MAX_TEACH = 2
SAVE_MAX_NS = int(os.environ.get("HK_SAVE_MAX_NS", "4"))   # also save verified intermediate levels <= this
PAUSE_C, RESUME_C, STOP_C = (float(x) for x in os.environ.get("HK_TEMPS", "96,92,99").split(","))


def temp_c():
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() in ("k10temp", "coretemp"):
                return int((h / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


def guard():
    """thermal pause (never a label): sleep while hot; STOP file aborts the job as ADMIN (missing, not failure)"""
    while True:
        if (OUT / "STOP").exists():
            raise AdminStop("STOP file")
        t = temp_c()
        if t is None or t < PAUSE_C:
            return
        while (t := temp_c()) is not None and t >= RESUME_C:
            if (OUT / "STOP").exists():
                raise AdminStop("STOP file")
            time.sleep(10)


class AdminStop(Exception):
    pass


def boot():
    P.boot("fastgeom1")
    if "boot_error" not in P._M:
        P._M["store"] = P._M["bc"].Store(OUT / "store")


def akey(assign):
    return json.dumps(sorted([o, int(d)] for o, d in assign))


def claimed(jid):
    """job ids handed to another host (OUT/claims_other_host.json, written on the laptop at handoff): skipped here, never run twice"""
    try:
        return jid in set(json.loads((OUT / "claims_other_host.json").read_text()))
    except FileNotFoundError:
        return False


def job(item):
    t0 = time.process_time()
    if claimed(item["job_id"]):
        return {"job_id": item["job_id"], "layout": item["layout"], "skipped": "CLAIMED_BY_OTHER_HOST", "accepted": False, "cpu_s": 0.0,
                "utc": time.strftime("%FT%TZ", time.gmtime())}
    ent = {"job_id": item["job_id"], "layout": item["layout"], "start_id": item["start_id"], "start_ns": item["start_ns"], "gen": GEN,
           "accepted": False}
    try:
        if "boot_error" in P._M:
            raise RuntimeError("boot: " + P._M["boot_error"])
        ent.update(search(item))
    except AdminStop as e:
        ent.update(reason=f"ADMIN_STOP:{e}")
    except Exception as e:  # noqa: BLE001  (infrastructure error: recorded, never a label)
        ent.update(reason=f"ERROR:{type(e).__name__}:{str(e)[:200]}", trace=traceback.format_exc()[-1200:])
    ent["cpu_s"] = round(time.process_time() - t0, 1)
    ent["utc"] = time.strftime("%FT%TZ", time.gmtime())
    return ent


def search(item):
    A = P._M["A"]
    from dataclasses import replace
    from scene import place_scene, scene_to_dict
    G = A.env()
    layout = item["layout"]
    rec = P.record(layout)
    mini0 = next((b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if rec.get("fixed_ids") or rec["verified_K"] != 3 or mini0 is None:
        return {"reason": "LAYOUT_NOT_MOVABLE_ONLY_K3"}
    objs = rec["scene"]["objects"]
    obst = [o for o in objs if o["id"] != "t0"]
    src, goal, q0 = next(o["cell"] for o in objs if o["id"] == "t0"), rec["goal_cell"], tuple(rec["q0"])
    cell0 = {o["id"]: o["cell"] for o in obst}
    orig = {o: int(d) for o, d in mini0["sequence"]}
    start = {o: int(d) for o, d in item["start_assign"]}
    assert set(start) == set(orig)
    movers = sorted(orig)
    used = set(cell0.values()) | {src, goal} | {v[0]["cell"] for v in rec["parking"].values() if v}
    base = G["robot"].base
    ctr = lambda c: ((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08)  # noqa: E731
    s0 = place_scene(G["cfg"], f"hk2:{layout}", "orig", [src], [o["cell"] for o in obst])
    s0 = replace(s0, robot=replace(s0.robot, q_rad=q0))
    task = {"scene": scene_to_dict(s0), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": f"hk2:{layout}"}
    cache = {}
    tried = set(item.get("known_keys", [])) | {akey(start.items())}
    cur, cur_succ = dict(start), [tuple(o) for o in item["start_succ"]]          # successful orders as mover-id tuples
    cur_ns = len(cur_succ)
    path, improved, n_cand, n_eval, mech_log = [], [], 0, 0, []

    def legal(x, dest):
        return x in G["valid"] and x not in used and x not in set(dest.values()) and A.cheb(x, src) >= 2 and A.cheb(x, goal) >= 2

    def candidates(dest, succ):
        pairs = {}
        for s in succ:
            for i, U in enumerate(s):
                for V in s[i + 1:]:
                    kills = sum(t.index(V) < t.index(U) for t in succ)
                    if 0 < kills < len(succ):
                        pairs[(U, V)] = kills
        if len(succ) == 6:                                   # unconstrained: every pair removes 3
            pairs = {(U, V): 3 for U in movers for V in movers if U != V}
        # prefer re-parking a mover the lineage has not re-parked yet (its destination may cause the existing constraints)
        rank = sorted(pairs, key=lambda p: (-pairs[p], dest[p[1]] != orig[p[1]], hashlib.sha256(f"{layout}{p}".encode()).hexdigest()))
        lists = []
        for U, V in rank:
            near_init = sorted((x for x in G["valid"] if legal(x, dest) and 1 <= A.cheb(x, cell0[U]) <= 2),
                               key=lambda x: (A.cheb(x, cell0[U]), math.dist(ctr(x), base), x))
            near_dst = sorted((x for x in G["valid"] if legal(x, dest) and A.cheb(x, dest[U]) == 1 and x not in near_init),
                              key=lambda x: (math.dist(ctr(x), base), x))
            lists.append([(V, x, f"BLOCK_PICK:{U}", pairs[(U, V)]) for x in near_init[:5]] +
                         [(V, x, f"BLOCK_PLACE:{U}", pairs[(U, V)]) for x in near_dst[:2]])
        out = []
        for tup in itertools.zip_longest(*lists):            # round-robin over ranked pairs
            out += [x for x in tup if x is not None]
        return out

    t_search = time.process_time()
    while cur_ns > 1 and n_cand < MAXC and time.process_time() - t_search < CPU_CAP:
        moved = False
        for V, d, mech, kills in candidates(cur, cur_succ):
            if n_cand >= MAXC or time.process_time() - t_search >= CPU_CAP:
                break
            new = {**cur, V: d}
            k = akey(new.items())
            if k in tried:
                continue
            tried.add(k)
            n_cand += 1
            guard()
            assign = [(o, new[o]) for o in movers]
            orders = sorted(itertools.permutations(movers), key=lambda t: (t not in cur_succ, t))
            res, ns, bad = {}, 0, False
            for t in orders:
                e = P.evaluate(task, cache, [(o, new[o]) for o in t])
                n_eval += 1
                if e.get("y") not in (0, 1):
                    bad = True
                    break
                res[t] = e
                ns += e["y"]
                if ns >= cur_ns:
                    break
            if bad or len(res) < 6 or not 1 <= ns < cur_ns:
                continue
            mech_log.append(mech)
            path.append({"from_ns": cur_ns, "to_ns": ns, "object": V, "to": int(d), "mechanism": mech, "candidate_no": n_cand})
            improved.append((ns, len(improved), new, res))
            cur, cur_succ, cur_ns = new, [t for t in orders if res[t]["y"] == 1], ns
            moved = True
            break
        if not moved:
            break
    stats = {"candidates_tried": n_cand, "evals": n_eval, "search_cpu_s": round(time.process_time() - t_search, 1), "path": path,
             "tried_keys": sorted(tried - set(item.get("known_keys", [])))}
    if not improved:
        return {"reason": "NO_IMPROVEMENT", **stats}
    seen = {c for v in rec["empty_scene_T_swept"].values() for c in v}
    teach_log, saved = [], []

    def teach_one(ns, new, res):
        guard()
        assign = [(o, new[o]) for o in movers]
        changed = {o: new[o] for o in movers if new[o] != orig[o]}
        dests = list(new.values())
        assert len(set(dests)) == 3 and not set(dests) & (set(cell0.values()) | {src, goal}), "destination not free / distinct"
        rid = f"D2H_{hashlib.sha256((layout + akey(assign)).encode()).hexdigest()[:10]}"
        c = {"scene": s0, "goal": goal, "q0": q0, "fixed_ids": [], "wrong_dest": [], "intended": rec["intended_blockers"], "roles": rec["roles"],
             "parking": {**rec["parking"], **{o: [{"cell": int(d), "in_target_sweep": d in seen}] for o, d in changed.items()}}}
        A.POOL_CAP, A.ADMIN_CPU_S = min(len(c["intended"]), max(5, 6)), 1500.0          # as DEPSEEK2D (K3 roots)
        try:
            t = A.teach(c, P._M["store"], rid)
        except A.AdminCap as e:
            teach_log.append({"root_id": rid, "ns": ns, "result": f"AdminCap:{e}"})
            return None
        mini2 = next((b for b in t["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
        if t["verified_K"] != 3 or mini2 is None or {o: int(d) for o, d in mini2["sequence"]} != dict(assign):
            teach_log.append({"root_id": rid, "ns": ns, "result": f"VERIFIED_K_{t['verified_K']}_OR_ASSIGNMENT_CHANGED"})
            return None
        recd = {tuple(tuple(x) for x in b["sequence"]): b for b in t["labels"]["B"]}
        dis = [{"order": list(tt), "teacher_y": recd[tuple((o, new[o]) for o in tt)]["y"], "search_y": res[tt]["y"]} for tt in res
               if tuple((o, new[o]) for o in tt) in recd and recd[tuple((o, new[o]) for o in tt)]["y"] != res[tt]["y"]]
        if dis:
            teach_log.append({"root_id": rid, "ns": ns, "result": "TEACHER_AUDIT_DISAGREE", "disagreements": dis})
            return None
        perms = []
        for tt in itertools.permutations(movers):
            q = tuple((o, new[o]) for o in tt)
            if q in recd:
                b = recd[q]
                perms.append({"order": [list(x) for x in q], "source": "teacher", "role": b["role"], "y": b["y"], "reason": b["reason"],
                              "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b["witnesses"]})
            else:
                e = res[tt]
                perms.append({"order": [list(x) for x in q], "source": "audit", **{k: e.get(k) for k in
                              ("y", "reason", "failed_step", "negative_kind", "witnesses", "resolution", "error", "cpu_s")}})
        nsf = sum(p["y"] for p in perms)
        if not 1 <= nsf <= 5:
            teach_log.append({"root_id": rid, "ns": ns, "result": f"FINAL_NS_{nsf}"})
            return None
        ids = {**rec["ids"], "root_id": rid, "parent_root_id": layout, "generator_version": GEN, "variant_id": "orig",
               "construction_seed": int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)}
        out = {"ids": ids, "domain": "2d", "spec": {**rec["spec"], "intent": "hard_order_k3"}, "scene": scene_to_dict(s0), "goal_cell": goal,
               "q0": list(q0), "start_stratum": rec["start_stratum"], "roles": c["roles"], "fixed_ids": [], "parking": c["parking"],
               "intended_blockers": c["intended"], "n_movable": len(obst), "verified_K": 3, "observed": 3, "labels": t["labels"],
               "teacher_calls": t["teacher_calls"], "teacher_cpu_s": t["teacher_cpu_s"], "budget": {"per_query": A.QB, "admin_cpu_s": A.ADMIN_CPU_S},
               "geometry_impl": "fastgeom1", "generator_version_plus": GEN, "independent_moves": None,
               "empty_scene_T_swept": rec["empty_scene_T_swept"], "empty_scene_T_witness": rec["empty_scene_T_witness"],
               "construction": {"method": "hardk3_2d", "layout_root_id": layout, "parent_root_id": layout, "same_layout_as_parent": True,
                                "start_from": item["start_id"], "start_ns": item["start_ns"],
                                "parent_sha256": hashlib.sha256((P.DS / "raw/roots" / f"{layout}.json").read_bytes()).hexdigest(),
                                "changed_destinations": [{"object": o, "from": orig[o], "to": int(d)} for o, d in changed.items()],
                                "destinations_free_distinct_in_original": True, **{k: v for k, v in stats.items() if k != "tried_keys"}},
               "permutations": perms, "order_class": "ORDER_DEPENDENT", "n_success": nsf, "n_orders": 6}
        P._M["store"].save_root(out)
        return {"root_id": rid, "n_success": nsf, "search_ns": ns, "teacher_cpu_s": t["teacher_cpu_s"]}

    levels = sorted({x[0] for x in improved if x[0] <= SAVE_MAX_NS}) or [min(x[0] for x in improved)]
    for lv in levels:                                   # one verified assignment per strength level reached (selector needs options)
        for ns, _, new, res in sorted((x for x in improved if x[0] == lv), key=lambda x: -x[1])[:MAX_TEACH]:
            r = teach_one(ns, new, res)
            if r:
                saved.append(r)
                break
    if saved:
        return {"accepted": True, "root_id": saved[0]["root_id"], "n_success": saved[0]["n_success"], "saved": saved, "teach": teach_log, **stats}
    return {"reason": "TEACH_REJECTED", "teach": teach_log, **stats}


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    jobs, workers = json.loads(Path(sys.argv[1]).read_text()), int(sys.argv[2])
    cpus = sorted(os.sched_getaffinity(0))[:max(workers, 1)]
    os.sched_setaffinity(0, cpus)
    (OUT / "store").mkdir(parents=True, exist_ok=True)
    led = OUT / "ledger.jsonl"
    done = {json.loads(l)["job_id"] for l in led.read_text().splitlines() if '"ADMIN_STOP' not in l and 'CLAIMED_BY_OTHER_HOST' not in l} if led.exists() else set()
    todo = [j for j in jobs if j["job_id"] not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} hard2d jobs={len(todo)} workers={workers} cpus={cpus[0]}-{cpus[-1]}", flush=True)
    with open(led, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            t = temp_c()
            if i % 10 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)} temp={t}", flush=True)
            if (OUT / "STOP").exists() or (t is not None and t >= STOP_C):
                print(f"STOP (file or temp {t})", flush=True)
                break
