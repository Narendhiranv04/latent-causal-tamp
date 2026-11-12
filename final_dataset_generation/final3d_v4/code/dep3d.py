#!/usr/bin/env python3
"""DEPSEEK3D_V1 -- dependence-seeking 3D SHELF66V3 target-task scenes (servers; namespaces D3_GVLAB_* / D3_BLACKWELL_*).
Same two families as dep2d.py, on the unmodified BD3DS66_TEACHER_V2 (MuJoCo, carried arm state, no return to ready, RRT 5000, seed 0):
  K2_CHAIN / K3_CHAIN / K3_DOUBLE : a verified K1 scene (only minimal clearing set {B}) + 1-2 ordinary obstacles next to B that block its pick
  K2_REPARK / K3_REPARK           : the layout of a verified K2 / K3 scene; ONE mover gets another destination (the generator's alternative
                                    parking cells first, then free cells next to another mover); kept only if executing every order shows a
                                    contrast (K2: 1/2, K3: <= MAX_OK_K3 of 6)
Every destination is free in the original child scene and distinct; no slot exchange; no teleport or reset between moves; no budget change.
Labels: bd_3dt.teach() from scratch + EVERY order executed (perm3d.seq = teach.seq verbatim).  Atomic per-root outputs, resumable.

  dep3d.py HOST DATASET_DIR OUT_DIR JOBS.json WORKERS CPUS(a-b) [repro SAMPLE.json]"""
import hashlib, itertools, json, math, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import perm3d as Q  # noqa: E402

GEN = "BD_GEN_V1+ROUTE_V15+SHELF66V3+DEPSEEK3D_V1"
KINDS = {"K2_CHAIN": 2, "K3_CHAIN": 3, "K3_DOUBLE": 3, "K2_REPARK": 2, "K3_REPARK": 3}
MAX_CAND, MAX_PARK, MAX_REPARK = 6, 3, {"K2_REPARK": 10, "K3_REPARK": 8}
MAX_OK_K3 = int(os.environ.get("DEP3D_K3_MAXOK", "2"))   # 5 = accept any order-dependent K3 (strength recorded)
CFG = {}


def boot(host, ds, out, pins):
    Q.DS, Q.CODE, Q.OUT = Path(ds), Path(ds) / "code", Path(out)
    CFG.update(host=host, pins=pins)
    Q.boot()
    if "boot_error" not in Q._M:
        import run_shelf66_full as RS
        import bd_3dt_plus as P
        Q._M.update(RS=RS, P=P, store=Q._M["bc"].Store(Path(out) / "store"))


def root_id(host, parent, kind):
    return f"D3_{host}_{kind}_{hashlib.sha256((parent + kind).encode()).hexdigest()[:10]}"


def job(item):
    parent, kind = item
    rid, t0, w0 = root_id(CFG.get("host", "?"), parent, kind), time.process_time(), time.time()
    ent = {"root_id": rid, "parent_root_id": parent, "kind": kind, "gen": GEN, "accepted": False}
    try:
        if "boot_error" in Q._M:
            raise RuntimeError("boot: " + Q._M["boot_error"])
        p = Q.DS / "raw/roots" / f"{parent}.json"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if CFG["pins"].get(parent) != sha:
            ent["reason"] = "PARENT_HASH_NOT_SNAPSHOT_A"
        else:
            ent.update((repark if kind.endswith("_REPARK") else chain)(json.loads(p.read_text()), sha, kind, rid))
    except Exception as e:  # noqa: BLE001  (infrastructure error: recorded, never a label)
        ent.update(reason=f"ERROR:{type(e).__name__}:{str(e)[:200]}", trace=traceback.format_exc()[-1200:])
    ent["cpu_s"], ent["wall_s"], ent["utc"] = round(time.process_time() - t0, 1), round(time.time() - w0, 1), time.strftime("%FT%TZ", time.gmtime())
    return ent


def perms_of(child, assign, taught, pre=None):
    recd = {tuple((o, tuple(d)) for o, d in b["sequence"]): b for b in taught}
    out = []
    for q in itertools.permutations(assign):
        if q in recd:
            b = recd[q]
            out.append({"order": [[o, list(d)] for o, d in q], "source": "teacher", "role": b["role"], "y": b["y"], "reason": b["reason"],
                        "failed_step": b["failed_step"], "negative_kind": b["negative_kind"], "witnesses": b.get("witnesses")})
        else:
            e = (pre or {}).get(q) or Q.evaluate(child, [[o, list(d)] for o, d in q])
            out.append({"order": [[o, list(d)] for o, d in q], "source": "audit", **{k: e.get(k) for k in
                        ("y", "reason", "failed_step", "negative_kind", "witnesses", "final_cells", "resolution", "error", "cpu_s")}})
    return out


def finish(rec, sha, kind, rid, c, assign, extra, pre=None):
    A, P, bc = Q._M["A"], Q._M["P"], Q._M["bc"]
    K = KINDS[kind]
    t = A.teach(c, Q._M["store"], rid)
    mini = next((b for b in t["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if t["verified_K"] != K or mini is None or {o: tuple(d) for o, d in mini["sequence"]} != dict(assign):
        return {"reason": f"VERIFIED_K_{t['verified_K']}_OR_ASSIGNMENT_CHANGED", **extra.get("stats", {})}
    G = A.env()
    ids = {**rec["ids"], "root_id": rid, "parent_root_id": rec["ids"]["root_id"], "variant_id": "orig", "config_hash": G["config_hash"],
           "teacher_version": A.TEACHER_VERSION, "robot_protocol": G["protocol"], "construction_seed": int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)}
    out = json.loads(json.dumps(P.record({**rec["spec"], "K": K, "intent": "dependence_seeking"}, ids, c, t, Q._M["store"]), default=bc._jd))
    perms = perms_of(out, [(o, tuple(d)) for o, d in mini["sequence"]], out["labels"]["B"], pre)
    if any(p["y"] not in (0, 1) for p in perms):
        return {"reason": "PERMUTATION_UNRESOLVED", **extra.get("stats", {})}
    ns = sum(p["y"] for p in perms)
    cls = "ORDER_INDEPENDENT" if ns == len(perms) else "ORDER_DEPENDENT"
    out.update(generator_version_plus=GEN, independent_moves=None, ledger_observed=str(K), permutations=perms, order_class=cls, n_success=ns,
               n_orders=len(perms), construction={**extra["construction"], "kind": kind, "parent_root_id": rec["ids"]["root_id"], "parent_sha256": sha,
                                                  "source_commit": "8fe960750b0a2701d76c91d304e0c427cc808d74", "host": CFG["host"],
                                                  "destinations_free_distinct_in_original": True})
    Q._M["store"].save_root(out)
    return {"accepted": True, "verified_K": K, "order_class": cls, "n_success": ns, "n_orders": len(perms),
            "fail_first_step": sum(p["y"] == 0 and p["failed_step"] == 0 for p in perms), **extra.get("stats", {})}


def legal_cells(A, occ, src, goal):
    return [x for x in itertools.product(range(1, A.GRID["R"]), range(A.GRID["C"])) if x not in occ and A.cheb(x, src) >= 2 and A.cheb(x, goal) >= 2]


def chain(rec, sha, kind, rid):
    A, P, RS, np = Q._M["A"], Q._M["P"], Q._M["RS"], Q._M["np"]
    mini = next((b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if rec["verified_K"] != 1 or mini is None or rec["labels"]["blocker"].get("minimal_sets") != [[mini["sequence"][0][0]]]:
        return {"reason": "PARENT_NOT_K1_WITH_UNIQUE_CLEARING_OBJECT"}
    c0 = RS.scene_of(rec)
    B, pB = mini["sequence"][0][0], tuple(mini["sequence"][0][1])
    objs, cells = list(c0["objs"]), {o: list(v) for o, v in c0["cells"].items()}
    src, goal = tuple(c0["src"]), tuple(c0["goal"])
    park0 = {tuple(v[0]) for v in c0["parking"].values() if v}
    rng = np.random.default_rng(int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16))
    tall = max(o["height"] for o in objs)
    n_new = KINDS[kind] - 1
    n0 = len(objs) - 1
    new = []
    for j in range(n_new):                                # ordinary obstacles, the generator's own size ranges; never taller than the tallest
        cyl = bool(rng.integers(2))
        new.append({"id": f"o{n0 + j:02d}", "shape": "cylinder" if cyl else "box", "size": float(rng.uniform(0.013, 0.018) if cyl else rng.uniform(0.012, 0.016)),
                    "height": float(rng.uniform(0.12, min(0.18, tall))), "color": A.COLORS[(n0 + j) % len(A.COLORS)]})
    stats = {"plan_queries": 0}

    def blocked(extra_cells, name, dst, only=None):
        """True if name -> dst does not plan from the initial state with the given added objects"""
        use = [n for n in new if n["id"] in extra_cells and (only is None or n["id"] in only)]
        e = A.build(objs + use, {**cells, **{n["id"]: list(extra_cells[n["id"]]) for n in use}})
        A.settle(e, {**cells, **{n["id"]: list(extra_cells[n["id"]]) for n in use}})
        stats["plan_queries"] += 1
        return A.query(e, name, dst)[0] is None

    def near(cell, taken):
        occ = {tuple(v) for v in cells.values()} | set(taken) | {src, goal} | park0
        cs = [x for x in itertools.product(range(1, A.GRID["R"]), range(A.GRID["C"])) if x not in occ and A.cheb(x, cell) == 1]
        return sorted(cs, key=lambda x: (x[0], abs(x[1] - cell[1]), x))[:MAX_CAND]      # robot side (low rows) first

    def place(j, target, target_cell, target_dst, placed, parks, alone=False):
        nid = new[j]["id"]
        for cc in near(target_cell, list(placed.values()) + parks):
            ex = {**placed, nid: cc}
            if not blocked(ex, target, target_dst):
                continue
            if alone and not blocked(ex, B, pB, only=[nid]):
                continue
            occ = {tuple(v) for v in cells.values()} | set(ex.values())
            avoid = {x for x in itertools.product(range(A.GRID["R"]), range(A.GRID["C"])) if A.cheb(x, src) < 2 or A.cheb(x, goal) < 2} | park0 | set(parks)
            for p in P.parking_cells(cc, avoid, occ, MAX_PARK):
                if not blocked(ex, nid, p):
                    return cc, tuple(p)
        return None

    placed, parks = {}, []
    r = place(0, B, tuple(cells[B]), pB, placed, parks)
    if r is None:
        return {"reason": "NO_ACCESS_BLOCKER_FOR_B", **stats}
    placed[new[0]["id"]] = r[0]; parks.append(r[1])
    if n_new == 2:
        r = (place(1, new[0]["id"], placed[new[0]["id"]], parks[0], placed, parks) if kind == "K3_CHAIN"
             else place(1, B, tuple(cells[B]), pB, placed, parks, alone=True))
        if r is None:
            return {"reason": "NO_SECOND_BLOCKER", **stats}
        placed[new[1]["id"]] = r[0]; parks.append(r[1])
    cells2 = {**cells, **{k: list(v) for k, v in placed.items()}}
    dest = {B: pB, **{n["id"]: p for n, p in zip(new, parks)}}
    assert len(set(dest.values())) == len(dest) and not set(dest.values()) & {tuple(v) for v in cells2.values()}
    c = {**c0, "objs": objs + new, "cells": cells2, "intended": [B] + [n["id"] for n in new],
         "roles": {**c0["roles"], **{n["id"]: "intended_blocker" for n in new}},
         "parking": {**c0["parking"], **{n["id"]: [list(p)] for n, p in zip(new, parks)}},
         "alt_parking": {**c0["alt_parking"], **{n["id"]: [list(p)] for n, p in zip(new, parks)}}}
    A.POOL_CAP = 1 + n_new                                # declared pool = {B + added}; B is the parent's only clearing object
    return finish(rec, sha, kind, rid, c, dest, {"stats": stats, "construction": {**c0["construction"], "method": "depseek3d_chain",
                  "added": [{**n, "cell": list(placed[n["id"]]), "parking": list(p)} for n, p in zip(new, parks)], "pool": [B] + [n["id"] for n in new]}})


def repark(rec, sha, kind, rid):
    A, P, RS = Q._M["A"], Q._M["P"], Q._M["RS"]
    K = KINDS[kind]
    mini = next((b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if rec["verified_K"] != K or mini is None:
        return {"reason": "PARENT_NOT_K"}
    c0 = RS.scene_of(rec)
    cells = {o: tuple(v) for o, v in c0["cells"].items()}
    src, goal = tuple(c0["src"]), tuple(c0["goal"])
    base = [(o, tuple(d)) for o, d in mini["sequence"]]
    movers = [o for o, _ in base]
    used = set(cells.values()) | {src, goal} | {tuple(v[0]) for v in c0["parking"].values() if v}
    legal = set(legal_cells(A, used, src, goal))
    per = {}
    for X in movers:
        alt = [(X, tuple(x), "ALT_PARKING") for x in (c0["alt_parking"].get(X) or [])[1:] if tuple(x) in legal]
        nr = sorted({x for Y in movers if Y != X for x in legal if A.cheb(x, cells[Y]) == 1}, key=lambda x: (x[0], x))
        per[X] = alt + [(X, x, "NEAR_OTHER_MOVER") for x in nr if x not in {a[1] for a in alt}]
    cands = [x for tup in itertools.zip_longest(*per.values()) for x in tup if x is not None]
    lim, tried, found = (1 if K == 2 else MAX_OK_K3), 0, None
    for X, d, mech in cands[:MAX_REPARK[kind]]:
        tried += 1
        assign = [(o, d if o == X else p) for o, p in base]
        res, ns, bad = {}, 0, False
        for q in itertools.permutations(assign):
            e = Q.evaluate(rec, [[o, list(p)] for o, p in q])
            if e.get("y") not in (0, 1):
                bad = True
                break
            res[q] = e
            ns += e["y"]
            if ns > lim:
                break
        if not bad and len(res) == math.factorial(K) and 1 <= ns <= lim:
            found = (X, d, mech, assign, res)
            break
    if found is None:
        return {"reason": "NO_CONTRAST_ASSIGNMENT", "candidates_tried": tried}
    X, d, mech, assign, res = found
    c = {**c0, "parking": {**c0["parking"], X: [list(d)]}}
    A.POOL_CAP = P.POOL_CAP
    return finish(rec, sha, kind, rid, c, dict(assign), {"stats": {"candidates_tried": tried, "mechanism": mech}, "construction": {
        **c0["construction"], "method": "depseek3d_repark", "mechanism": mech, "same_layout_as_parent": True,
        "changed_destination": {"object": X, "from": list(dict(base)[X]), "to": list(d)}, "candidates_tried": tried}}, res)


def pkg_temp():
    for h in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (h / "name").read_text().strip() in ("coretemp", "k10temp"):
                return int((h / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    host, ds, out, jobs_f, workers, cpus = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5]), sys.argv[6]
    a, b = map(int, cpus.split("-"))
    os.sched_setaffinity(0, set(range(a, b + 1)))             # workers inherit: only these CPUs are ever used by this project
    stop_c = float(os.environ.get("DEP3D_TEMP_STOP_C", "93"))
    pins = json.loads((H / os.environ.get("DEP3D_PINS", "snapshot_a_root_sha256.json")).read_text())
    (out / "store").mkdir(parents=True, exist_ok=True)
    init = (host, ds, str(out), pins)
    if len(sys.argv) > 7 and sys.argv[7] == "repro":
        items = [tuple(x) for x in json.loads(Path(sys.argv[8]).read_text())]
        with mp.get_context("spawn").Pool(workers, initializer=boot, initargs=init) as pool, open(out / "repro.jsonl", "a", buffering=1) as f:
            for r in pool.imap_unordered(Q.job_repro, items):
                f.write(json.dumps(r) + "\n")
        sys.exit(0)
    led = out / "ledger.jsonl"
    done = {json.loads(l)["root_id"] for l in led.read_text().splitlines()} if led.exists() else set()
    todo = [tuple(j) for j in json.loads(Path(jobs_f).read_text()) if root_id(host, *j) not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} dep3d host={host} jobs={len(todo)} workers={workers} cpus={cpus}", flush=True)
    with open(led, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, initargs=init) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            t = pkg_temp()
            if i % 10 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)} temp={t}", flush=True)
            if (out / "STOP").exists() or (t is not None and t >= stop_c):
                print(f"STOP (file or temp {t})", flush=True)
                break
