#!/usr/bin/env python3
"""DEPSEEK2D_V1 -- dependence-seeking 2D target-task scenes (laptop, namespace D2_LOCAL_*).

Construction (new scenes, original physics and teacher untouched): take a verified movable-only K1 scene whose ONLY minimal clearing set is {B}
(full lattice) and add 1-2 ordinary obstacles next to B so that B cannot be picked until they are moved ("object behind object"):
  K2_CHAIN   A blocks B                         -> expected orders: A,B
  K3_CHAIN   A1 blocks B, A2 blocks A1          -> expected: A2,A1,B
  K3_DOUBLE  A1 and A2 each block B on its own  -> expected: A1,A2,B / A2,A1,B
Every destination is a cell that is free in the ORIGINAL child scene, distinct from every other destination and from every initial cell
(generator's own parking rule: >= 2 from T's start and goal, off T's sweeps, not next to an object; nearest first).  No slot exchange, no
teleport, no reset between moves, no budget / grasp / IK change.  Expected orders are only a construction intent: the label is whatever the
pinned teacher finds.

Per child: bd_2d.teach() (unmodified; fresh labels, verified K = executed minimal repair over the declared pool {B + added}) and then EVERY
order of the minimal assignment executed with the same seq path (perm2d.evaluate).  Accepted = verified K as intended and all orders evaluated.
Outputs (atomic per root, resumable): d2/store/roots/<root>.json, d2/store/witnesses, d2/ledger.jsonl.

  dep2d.py JOBS.json WORKERS      JOBS = [[parent_root_id, kind], ...]"""
import hashlib, itertools, json, math, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent / "order_classification_2d"))
import perm2d as P  # noqa: E402  (pinned-teacher bootstrap + evaluate(); read-only on the dataset)

OUT = H / "d2"
GEN = "BD_GEN_V1+DEPSEEK2D_V1"
KINDS = {"K2_CHAIN": 2, "K3_CHAIN": 3, "K3_DOUBLE": 3, "K2_REPARK": 2, "K3_REPARK": 3}
MAX_REPARK = {"K2_REPARK": 14, "K3_REPARK": 10}
MAX_CAND, MAX_PARK = 8, 3
TEMP_STOP_C = 97
K3_MAXOK = int(os.environ.get("DEP2D_K3_MAXOK", "2"))   # 5 = accept any order-dependent K3 (strength recorded)


def boot():
    P.boot("fastgeom1")
    if "boot_error" not in P._M:
        P._M["store"] = P._M["bc"].Store(OUT / "store")


def root_id(parent, kind):
    return f"D2_LOCAL_{kind}_{hashlib.sha256((parent + kind).encode()).hexdigest()[:10]}"


def job(item):
    parent, kind = item
    rid, t0 = root_id(parent, kind), time.process_time()
    ent = {"root_id": rid, "parent_root_id": parent, "kind": kind, "gen": GEN, "accepted": False}
    try:
        if "boot_error" in P._M:
            raise RuntimeError("boot: " + P._M["boot_error"])
        ent.update(build(parent, kind, rid))
    except Exception as e:  # noqa: BLE001  (infrastructure error: recorded, never a label)
        ent.update(reason=f"ERROR:{type(e).__name__}:{str(e)[:200]}", trace=traceback.format_exc()[-1200:])
    ent["cpu_s"] = round(time.process_time() - t0, 1)
    ent["utc"] = time.strftime("%FT%TZ", time.gmtime())
    return ent


def build_repark(parent, kind, rid):
    """Same layout as an existing verified K2 / K3 scene; ONE mover gets another destination (generator's own alternative parking cells first,
    then free cells near another mover).  Kept only if executing every order shows a contrast (K2: 1/2; K3: 1/6 or 2/6)."""
    A, bc, pc, np = P._M["A"], P._M["bc"], P._M["pc"], P._M["np"]
    from dataclasses import replace
    from scene import place_scene, scene_to_dict
    G = A.env()
    rec = P.record(parent)
    K = KINDS[kind]
    mini = next((b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if rec.get("fixed_ids") or rec["verified_K"] != K or mini is None:
        return {"reason": "PARENT_NOT_MOVABLE_ONLY_K"}
    objs = rec["scene"]["objects"]
    obst = [o for o in objs if o["id"] != "t0"]
    if [o["id"] for o in obst] != [f"o{i:02d}" for i in range(len(obst))]:
        return {"reason": "PARENT_IDS_NOT_SEQUENTIAL"}
    src, goal, q0 = next(o["cell"] for o in objs if o["id"] == "t0"), rec["goal_cell"], tuple(rec["q0"])
    cell0 = {o["id"]: o["cell"] for o in obst}
    base_assign = [(o, int(d)) for o, d in mini["sequence"]]
    movers = [o for o, _ in base_assign]
    used = set(cell0.values()) | {src, goal} | {v[0]["cell"] for v in rec["parking"].values() if v}
    base = G["robot"].base
    ctr = lambda c: ((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08)  # noqa: E731
    legal = lambda x: x in G["valid"] and x not in used and A.cheb(x, src) >= 2 and A.cheb(x, goal) >= 2  # noqa: E731
    cands = []                                               # (mover, new destination, mechanism), interleaved over movers
    per = {}
    for X in movers:
        alt = [(X, int(c), "ALT_PARKING") for c in (rec.get("alt_parking") or {}).get(X, [])[1:] if legal(int(c))]
        near = sorted({x for Y in movers if Y != X for x in G["valid"] if legal(x) and 1 <= A.cheb(x, cell0[Y]) <= 2}, key=lambda x: (math.dist(ctr(x), base), x))
        per[X] = alt + [(X, x, "NEAR_OTHER_MOVER") for x in near if x not in {a[1] for a in alt}]
    for tup in itertools.zip_longest(*per.values()):
        cands += [x for x in tup if x is not None]
    s0 = place_scene(G["cfg"], rid, "orig", [src], [o["cell"] for o in obst])
    s0 = replace(s0, robot=replace(s0.robot, q_rad=q0))
    task = {"scene": scene_to_dict(s0), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": rid}
    cache, tried, found = {}, 0, None
    for X, d, mech in cands[:MAX_REPARK[kind]]:
        tried += 1
        assign = [(o, d if o == X else p) for o, p in base_assign]
        res, ns, bad = {}, 0, False
        for q in itertools.permutations(assign):
            e = P.evaluate(task, cache, list(q))
            if e.get("y") not in (0, 1):
                bad = True
                break
            res[q] = e
            ns += e["y"]
            if ns > (1 if K == 2 else K3_MAXOK):                    # too many orders work: not the contrast we look for
                break
        if bad or len(res) < math.factorial(K) or not 1 <= ns <= (1 if K == 2 else K3_MAXOK):
            continue
        found = (X, d, mech, assign, res, ns)
        break
    if found is None:
        return {"reason": "NO_CONTRAST_ASSIGNMENT", "candidates_tried": tried}
    X, d, mech, assign, res, ns = found
    seen = {c for v in rec["empty_scene_T_swept"].values() for c in v}
    c = {"scene": s0, "goal": goal, "q0": q0, "fixed_ids": [], "wrong_dest": [], "intended": rec["intended_blockers"], "roles": rec["roles"],
         "parking": {**rec["parking"], X: [{"cell": int(d), "in_target_sweep": d in seen}]}}
    A.POOL_CAP, A.ADMIN_CPU_S = min(len(c["intended"]), max(5, K + 3)), 1500.0          # as the generator sets them for this kind of root
    try:
        t = A.teach(c, P._M["store"], rid)
    except A.AdminCap as e:
        return {"reason": f"AdminCap:{e}", "candidates_tried": tried}
    mini2 = next((b for b in t["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if t["verified_K"] != K or mini2 is None or dict(tuple(x) for x in mini2["sequence"]) != dict(assign):
        return {"reason": f"VERIFIED_K_{t['verified_K']}_OR_ASSIGNMENT_CHANGED", "candidates_tried": tried}
    recd = {tuple(tuple(x) for x in b["sequence"]): b for b in t["labels"]["B"]}
    perms = []
    for q in itertools.permutations(assign):
        if q in recd:
            b = recd[q]
            perms.append({"order": [list(x) for x in q], "source": "teacher", "role": b["role"], "y": b["y"], "reason": b["reason"],
                          "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b["witnesses"]})
        else:
            e = res[q]
            perms.append({"order": [list(x) for x in q], "source": "audit", **{k: e.get(k) for k in
                          ("y", "reason", "failed_step", "negative_kind", "witnesses", "resolution", "error", "cpu_s")}})
    ns = sum(p["y"] for p in perms)
    cls = "ORDER_INDEPENDENT" if ns == len(perms) else "ORDER_DEPENDENT"
    ids = {**rec["ids"], "root_id": rid, "parent_root_id": parent, "generator_version": GEN, "variant_id": "orig",
           "construction_seed": int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)}
    old = dict(base_assign)[X]
    out = {"ids": ids, "domain": "2d", "spec": {**rec["spec"], "intent": "dependence_seeking"}, "scene": scene_to_dict(s0), "goal_cell": goal,
           "q0": list(q0), "start_stratum": rec["start_stratum"], "roles": c["roles"], "fixed_ids": [], "parking": c["parking"],
           "intended_blockers": c["intended"], "n_movable": len(obst), "verified_K": K, "observed": K, "labels": t["labels"],
           "teacher_calls": t["teacher_calls"], "teacher_cpu_s": t["teacher_cpu_s"], "budget": {"per_query": A.QB, "admin_cpu_s": A.ADMIN_CPU_S},
           "geometry_impl": "fastgeom1", "generator_version_plus": GEN, "independent_moves": None,
           "empty_scene_T_swept": rec["empty_scene_T_swept"], "empty_scene_T_witness": rec["empty_scene_T_witness"],
           "construction": {"method": "repark2d", "kind": kind, "mechanism": mech, "parent_root_id": parent, "same_layout_as_parent": True,
                            "parent_sha256": hashlib.sha256((P.DS / "raw/roots" / f"{parent}.json").read_bytes()).hexdigest(),
                            "changed_destination": {"object": X, "from": int(old), "to": int(d)}, "candidates_tried": tried,
                            "destinations_free_distinct_in_original": True},
           "permutations": perms, "order_class": cls, "n_success": ns, "n_orders": len(perms)}
    P._M["store"].save_root(out)
    return {"accepted": True, "verified_K": K, "order_class": cls, "n_success": ns, "n_orders": len(perms), "mechanism": mech,
            "fail_first_step": sum(p["y"] == 0 and p["failed_step"] == 0 for p in perms), "candidates_tried": tried}


def build(parent, kind, rid):
    if kind.endswith("_REPARK"):
        return build_repark(parent, kind, rid)
    A, bc, pc, np = P._M["A"], P._M["bc"], P._M["pc"], P._M["np"]
    from dataclasses import replace
    from scene import place_scene, scene_to_dict
    G = A.env()
    rec = P.record(parent)
    if rec.get("fixed_ids") or rec["verified_K"] != 1:
        return {"reason": "PARENT_NOT_MOVABLE_ONLY_K1"}
    bl = rec["labels"]["blocker"]
    mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
    (B, pB), = [tuple(s) for s in mini["sequence"]]
    if bl.get("minimal_sets") != [[B]]:          # all pool singles are always evaluated for a K1 root
        return {"reason": "PARENT_MINIMAL_SET_NOT_UNIQUE"}
    objs = rec["scene"]["objects"]
    obst = [o for o in objs if o["id"] != "t0"]
    if [o["id"] for o in obst] != [f"o{i:02d}" for i in range(len(obst))]:
        return {"reason": "PARENT_IDS_NOT_SEQUENTIAL"}
    src, goal = next(o["cell"] for o in objs if o["id"] == "t0"), rec["goal_cell"]
    q0 = tuple(rec["q0"])
    qa = np.asarray(q0, float)
    cell0 = {o["id"]: o["cell"] for o in obst}
    park0 = {o: v[0]["cell"] for o, v in rec["parking"].items() if v}
    seen = {c for v in rec["empty_scene_T_swept"].values() for c in v}
    base = G["robot"].base
    ctr = lambda c: ((c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08)  # noqa: E731
    n_new = KINDS[kind] - 1
    new_ids = [f"o{len(obst) + i:02d}" for i in range(n_new)]
    stats = {"edge_queries": 0}

    def scene_of(extra):
        s = place_scene(G["cfg"], rid, "orig", [src], [o["cell"] for o in obst] + list(extra))
        return replace(s, robot=replace(s.robot, q_rad=q0))

    def phys_of(s, tag):
        return A._phys({"scene": scene_to_dict(s), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": f"{rid}:{tag}"}, {})

    def movable(extra, o, d):
        s = scene_of(extra)
        cells = {x.id: x.cell for x in s.objects}
        stats["edge_queries"] += 1
        return pc.best_edge(phys_of(s, "screen").edges(cells, qa, o, int(d))) is not None

    def near_cells(c, extra, taken=()):
        occ = set(cell0.values()) | set(extra) | {src, goal} | set(park0.values()) | set(taken)
        cs = [x for x in G["valid"] if x not in occ and 1 <= A.cheb(x, c) <= 2]      # the planar arm's links sweep the board: 2 rings
        return sorted(cs, key=lambda x: (math.dist(ctr(x), base), x))[:MAX_CAND]      # robot side first

    def park_for(c0, extra, taken):
        occ = set(cell0.values()) | set(extra) | {src, goal} | set(park0.values()) | set(taken)
        near = {x for y in list(cell0.values()) + list(extra) for x in G["valid"] if A.cheb(x, y) == 1}
        ok = lambda x: x not in occ and A.cheb(x, src) >= 2 and A.cheb(x, goal) >= 2  # noqa: E731
        cands = sorted((x for x in G["valid"] if ok(x) and x not in seen and x not in near), key=lambda x: (A.cheb(x, c0), x)) or \
            sorted((x for x in G["valid"] if ok(x)), key=lambda x: (A.cheb(x, c0), x))
        return cands[:MAX_PARK]

    def blocker_for(xid, xcell, pX, extra, taken, also_alone=False):
        """a free cell next to object xid such that xid -> pX has no certified edge from the original state, and the new object can be parked"""
        for c in near_cells(xcell, extra, taken):
            ex = list(extra) + [c]
            if movable(ex, xid, pX):
                continue
            if also_alone and movable([c], B, pB):          # K3_DOUBLE: the second blocker must block B on its own too
                continue
            nid = new_ids[len(extra)]
            for p in park_for(c, ex, taken):
                if movable(ex, nid, p):
                    return c, p
        return None

    extra, parks = [], []
    r = blocker_for(B, cell0[B], pB, extra, parks)
    if r is None:
        return {"reason": "NO_ACCESS_BLOCKER_FOR_B", **stats}
    extra.append(r[0]); parks.append(r[1])
    if kind == "K3_CHAIN":
        r = blocker_for(new_ids[0], extra[0], parks[0], extra, parks)          # A2 blocks A1
        if r is None:
            return {"reason": "NO_ACCESS_BLOCKER_FOR_A1", **stats}
        extra.append(r[0]); parks.append(r[1])
    elif kind == "K3_DOUBLE":
        r = blocker_for(B, cell0[B], pB, extra, parks, also_alone=True)      # A2 blocks B on its own as well
        if r is None:
            return {"reason": "NO_SECOND_BLOCKER_FOR_B", **stats}
        extra.append(r[0]); parks.append(r[1])
    s = scene_of(extra)
    cells_all = {o.id: o.cell for o in s.objects}
    dest = {B: pB, **dict(zip(new_ids, parks))}
    assert len(set(dest.values())) == len(dest) and not set(dest.values()) & set(cells_all.values()), "destination not free / distinct"
    c = {"scene": s, "goal": goal, "q0": q0, "fixed_ids": [], "wrong_dest": [], "intended": [B] + new_ids,
         "roles": {**rec["roles"], **{n: "intended_blocker" for n in new_ids}},
         "parking": {**rec["parking"], **{n: [{"cell": int(p), "in_target_sweep": p in seen}] for n, p in zip(new_ids, parks)}}}
    A.POOL_CAP, A.ADMIN_CPU_S = 1 + n_new, 1200.0               # declared pool = {B + added}; B is the parent's only minimal clearing set
    try:
        t = A.teach(c, P._M["store"], rid)
    except A.AdminCap as e:
        return {"reason": f"AdminCap:{e}", **stats}
    K = t["verified_K"]
    mini2 = next((b for b in t["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if K != KINDS[kind] or mini2 is None or {o for o, _ in mini2["sequence"]} != set(dest):
        return {"reason": f"VERIFIED_K_{K}_NOT_{KINDS[kind]}", "verified_K": K, **stats}
    assign = [tuple(x) for x in mini2["sequence"]]
    assert dict(assign) == {o: int(d) for o, d in dest.items()}
    recd = {tuple(tuple(x) for x in b["sequence"]): b for b in t["labels"]["B"]}
    task = {"scene": scene_to_dict(s), "goal_cell": goal, "fixed_ids": [], "target": "t0", "key": rid}
    cache, perms = {}, []
    for q in itertools.permutations(assign):
        if q in recd:
            b = recd[q]
            perms.append({"order": [list(x) for x in q], "source": "teacher", "role": b["role"], "y": b["y"], "reason": b["reason"],
                          "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b["witnesses"]})
        else:
            e = P.evaluate(task, cache, list(q))
            perms.append({"order": [list(x) for x in q], "source": "audit", **{k: e.get(k) for k in
                          ("y", "reason", "failed_step", "negative_kind", "witnesses", "resolution", "error", "cpu_s")}})
    if any(p["y"] not in (0, 1) for p in perms):
        return {"reason": "PERMUTATION_UNRESOLVED", **stats}
    ns = sum(p["y"] for p in perms)
    cls = "ORDER_INDEPENDENT" if ns == len(perms) else "ORDER_DEPENDENT"
    ids = {**rec["ids"], "root_id": rid, "parent_root_id": parent, "generator_version": GEN, "variant_id": "orig",
           "construction_seed": int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)}
    out = {"ids": ids, "domain": "2d", "spec": {**rec["spec"], "K": KINDS[kind], "intent": "dependence_seeking"}, "scene": scene_to_dict(s),
           "goal_cell": goal, "q0": list(q0), "start_stratum": rec["start_stratum"], "roles": c["roles"], "fixed_ids": [], "parking": c["parking"],
           "intended_blockers": c["intended"], "n_movable": len(obst) + n_new, "verified_K": K, "observed": K, "labels": t["labels"],
           "teacher_calls": t["teacher_calls"], "teacher_cpu_s": t["teacher_cpu_s"], "budget": {"per_query": A.QB, "admin_cpu_s": A.ADMIN_CPU_S},
           "geometry_impl": "fastgeom1", "generator_version_plus": GEN, "independent_moves": None,
           "empty_scene_T_swept": rec["empty_scene_T_swept"], "empty_scene_T_witness": rec["empty_scene_T_witness"],
           "construction": {"method": "depseek2d", "kind": kind, "parent_root_id": parent, "parent_sha256": hashlib.sha256(
               (P.DS / "raw/roots" / f"{parent}.json").read_bytes()).hexdigest(), "added": [{"id": n, "cell": int(cc), "parking": int(p)} for n, cc, p in
                                                                                         zip(new_ids, extra, parks)],
                            "pool": [B] + new_ids, "destinations_free_distinct_in_original": True, **stats},
           "permutations": perms, "order_class": cls, "n_success": ns, "n_orders": len(perms)}
    P._M["store"].save_root(out)
    return {"accepted": True, "verified_K": K, "order_class": cls, "n_success": ns, "n_orders": len(perms),
            "fail_first_step": sum(p["y"] == 0 and p["failed_step"] == 0 for p in perms), **stats}


def temp_c():
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() == "k10temp":
                return int((h / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    jobs, workers = json.loads(Path(sys.argv[1]).read_text()), int(sys.argv[2])
    cpus = sorted(os.sched_getaffinity(0))[:max(workers, 1)]
    os.sched_setaffinity(0, cpus)                               # workers inherit: this project never uses the remaining CPUs
    (OUT / "store").mkdir(parents=True, exist_ok=True)
    led = OUT / "ledger.jsonl"
    done = {json.loads(l)["root_id"] for l in led.read_text().splitlines()} if led.exists() else set()
    todo = [tuple(j) for j in jobs if root_id(*j) not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} dep2d jobs={len(todo)} workers={workers} cpus={cpus[0]}-{cpus[-1]}", flush=True)
    with open(led, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            if i % 20 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)} temp={temp_c()}", flush=True)
            t = temp_c()
            if (OUT / "STOP").exists() or (t is not None and t >= TEMP_STOP_C):
                print(f"STOP (file or temp {t})", flush=True)
                break
