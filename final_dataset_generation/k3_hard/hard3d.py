#!/usr/bin/env python3
"""HARDK3_3D_V1 -- hard-order K3 search on existing verified SHELF66V3 K3 layouts (gvlab; namespace D3H_<HOST>_*).

The 3D twin of hard2d.py: same precedence-targeted greedy re-parking search, on the unmodified BD3DS66_TEACHER_V2 path through
dep3d.py / perm3d.py (Q.evaluate == teach.seq: carried arm state, no return to ready, RRT 5000, seed 0).  Labels come from
dep3d.finish(): bd_3dt.teach from scratch, verified K = 3 with the same assignment, all 6 orders stored.
Layout parent bytes must match Snapshot A (8fe96075) pins.  Atomic per-root outputs (OUT/store), resumable ledger (OUT/ledger.jsonl).

  hard3d.py HOST DATASET_DIR OUT_DIR JOBS.json WORKERS CPUS(a-b)"""
import hashlib, itertools, json, math, os, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import dep3d as D  # noqa: E402
import perm3d as Q  # noqa: E402

GEN = "BD_GEN_V1+ROUTE_V15+SHELF66V3+DEPSEEK3D_V1+HARDK3_3D_V1"
MAXC = int(os.environ.get("HK_MAXC", "14"))
CPU_CAP = float(os.environ.get("HK_CPU_CAP", "6000"))
MAX_TEACH = 2
PAUSE_C, RESUME_C, STOP_C = 88.0, 82.0, 93.0
STOPF = {}


class AdminStop(Exception):
    pass


def guard():
    while True:
        if STOPF["p"].exists():
            raise AdminStop("STOP file")
        t = D.pkg_temp()
        if t is None or t < PAUSE_C:
            return
        while (t := D.pkg_temp()) is not None and t >= RESUME_C:
            if STOPF["p"].exists():
                raise AdminStop("STOP file")
            time.sleep(10)


def boot(host, ds, out, pins):
    STOPF["p"] = Path(out) / "STOP"
    D.boot(host, ds, out, pins)


def akey(assign):
    return json.dumps(sorted([o, list(d)] for o, d in assign))


def job(item):
    t0, w0 = time.process_time(), time.time()
    ent = {"job_id": item["job_id"], "layout": item["layout"], "start_id": item["start_id"], "start_ns": item["start_ns"], "gen": GEN,
           "accepted": False}
    try:
        if "boot_error" in Q._M:
            raise RuntimeError("boot: " + Q._M["boot_error"])
        p = Q.DS / "raw/roots" / f"{item['layout']}.json"
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if D.CFG["pins"].get(item["layout"]) != sha:
            ent["reason"] = "PARENT_HASH_NOT_SNAPSHOT_A"
        else:
            ent.update(search(item, json.loads(p.read_text()), sha))
    except AdminStop as e:
        ent.update(reason=f"ADMIN_STOP:{e}")
    except Exception as e:  # noqa: BLE001
        ent.update(reason=f"ERROR:{type(e).__name__}:{str(e)[:200]}", trace=traceback.format_exc()[-1200:])
    ent["cpu_s"], ent["wall_s"], ent["utc"] = round(time.process_time() - t0, 1), round(time.time() - w0, 1), time.strftime("%FT%TZ", time.gmtime())
    return ent


def finish_checked(rec, sha, rid, c, assign, extra, pre):
    """dep3d.finish (same teach, same record) + a fail-closed consistency gate BEFORE saving: every order the teacher labelled must get
    the same y from the fresh-environment seq evaluation (pre).  bd_3dt.teach reuses one env (settle between queries); seq builds a fresh
    env per order; borderline grasps can differ.  Disagreement -> not accepted (reason TEACHER_FRESH_ENV_DISAGREE)."""
    A, P, bc = Q._M["A"], Q._M["P"], Q._M["bc"]
    t = A.teach(c, Q._M["store"], rid)
    mini = next((b for b in t["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if t["verified_K"] != 3 or mini is None or {o: tuple(d) for o, d in mini["sequence"]} != dict(assign):
        return {"reason": f"VERIFIED_K_{t['verified_K']}_OR_ASSIGNMENT_CHANGED"}
    dis = []
    for b in t["labels"]["B"]:
        q = tuple((o, tuple(d)) for o, d in b["sequence"])
        if q in pre and len(q) == 3 and set(dict(q)) == set(assign) and dict(q) == dict(assign) and pre[q]["y"] != b["y"]:
            dis.append({"order": [o for o, _ in q], "role": b["role"], "teacher_y": b["y"], "fresh_env_y": pre[q]["y"]})
    if dis:
        return {"reason": "TEACHER_FRESH_ENV_DISAGREE", "disagreements": dis}
    G = A.env()
    ids = {**rec["ids"], "root_id": rid, "parent_root_id": rec["ids"]["root_id"], "variant_id": "orig", "config_hash": G["config_hash"],
           "teacher_version": A.TEACHER_VERSION, "robot_protocol": G["protocol"], "construction_seed": int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)}
    out = json.loads(json.dumps(P.record({**rec["spec"], "K": 3, "intent": "hard_order_k3"}, ids, c, t, Q._M["store"]), default=bc._jd))
    perms = D.perms_of(out, [(o, tuple(d)) for o, d in mini["sequence"]], out["labels"]["B"], pre)
    if any(p["y"] not in (0, 1) for p in perms):
        return {"reason": "PERMUTATION_UNRESOLVED"}
    ns = sum(p["y"] for p in perms)
    out.update(generator_version_plus=GEN, independent_moves=None, ledger_observed="3", permutations=perms, n_success=ns, n_orders=6,
               order_class="ORDER_INDEPENDENT" if ns == 6 else "ORDER_DEPENDENT", teacher_vs_fresh_env="ALL_TEACHER_ORDERS_REPRODUCED",
               construction={**extra["construction"], "kind": "K3_HARD", "parent_root_id": rec["ids"]["root_id"], "parent_sha256": sha,
                             "source_commit": "8fe960750b0a2701d76c91d304e0c427cc808d74", "host": D.CFG["host"], "destinations_free_distinct_in_original": True})
    Q._M["store"].save_root(out)
    return {"accepted": True, "verified_K": 3, "order_class": out["order_class"], "n_success": ns, "n_orders": 6,
            "fail_first_step": sum(p["y"] == 0 and p["failed_step"] == 0 for p in perms)}


def search(item, rec, sha):
    A, P, RS = Q._M["A"], Q._M["P"], Q._M["RS"]
    layout = item["layout"]
    mini0 = next((b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1), None)
    if rec["verified_K"] != 3 or mini0 is None:
        return {"reason": "LAYOUT_NOT_K3"}
    c0 = RS.scene_of(rec)
    cells = {o: tuple(v) for o, v in c0["cells"].items()}
    src, goal = tuple(c0["src"]), tuple(c0["goal"])
    orig = {o: tuple(d) for o, d in mini0["sequence"]}
    start = {o: tuple(d) for o, d in item["start_assign"]}
    assert set(start) == set(orig)
    movers = sorted(orig)
    used = set(cells.values()) | {src, goal} | {tuple(v[0]) for v in c0["parking"].values() if v}
    legal0 = set(D.legal_cells(A, used, src, goal))
    tried = set(item.get("known_keys", [])) | {akey(start.items())}
    cur, cur_succ = dict(start), [tuple(o) for o in item["start_succ"]]
    cur_ns = len(cur_succ)
    path, improved, n_cand, n_eval = [], [], 0, 0

    def candidates(dest, succ):
        pairs = {}
        for s in succ:
            for i, U in enumerate(s):
                for V in s[i + 1:]:
                    kills = sum(t.index(V) < t.index(U) for t in succ)
                    if 0 < kills < len(succ):
                        pairs[(U, V)] = kills
        if len(succ) == 6:
            pairs = {(U, V): 3 for U in movers for V in movers if U != V}
        rank = sorted(pairs, key=lambda p: (-pairs[p], dest[p[1]] != orig[p[1]], hashlib.sha256(f"{layout}{p}".encode()).hexdigest()))
        free = legal0 - set(dest.values())
        lists = []
        for U, V in rank:
            ci, du = cells[U], dest[U]
            near_init = sorted((x for x in free if A.cheb(x, ci) == 1), key=lambda x: (x[0], abs(x[1] - ci[1]), x))
            near_dst = sorted((x for x in free if A.cheb(x, du) == 1 and x not in near_init), key=lambda x: (x[0], abs(x[1] - du[1]), x))
            lists.append([(V, x, f"BLOCK_PICK:{U}", pairs[(U, V)]) for x in near_init[:4]] +
                         [(V, x, f"BLOCK_PLACE:{U}", pairs[(U, V)]) for x in near_dst[:2]])
        return [x for tup in itertools.zip_longest(*lists) for x in tup if x is not None]

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
            orders = sorted(itertools.permutations(movers), key=lambda t: (t not in cur_succ, t))
            res, ns, bad = {}, 0, False
            for t in orders:
                e = Q.evaluate(rec, [[o, list(new[o])] for o in t])
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
            path.append({"from_ns": cur_ns, "to_ns": ns, "object": V, "to": list(d), "mechanism": mech, "candidate_no": n_cand})
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
    teach_log = []
    for ns, _, new, res in sorted(improved, key=lambda x: (x[0], -x[1]))[:MAX_TEACH]:
        guard()
        assign = {o: new[o] for o in movers}
        changed = {o: d for o, d in assign.items() if d != orig[o]}
        assert len(set(assign.values())) == 3 and not set(assign.values()) & (set(cells.values()) | {src, goal}), "destination not free/distinct"
        rid = f"D3H_{D.CFG['host']}_{hashlib.sha256((layout + akey(assign.items())).encode()).hexdigest()[:10]}"
        c = {**c0, "parking": {**c0["parking"], **{o: [list(d)] for o, d in changed.items()}}}
        A.POOL_CAP = P.POOL_CAP
        pre = {tuple((o, new[o]) for o in t): e for t, e in res.items()}
        r = finish_checked(rec, sha, rid, c, assign, {"stats": {}, "construction": {
            **c0["construction"], "method": "hardk3_3d", "layout_root_id": layout, "same_layout_as_parent": True, "start_from": item["start_id"],
            "start_ns": item["start_ns"], "changed_destinations": [{"object": o, "from": list(orig[o]), "to": list(d)} for o, d in changed.items()],
            **{k: v for k, v in stats.items() if k != "tried_keys"}}}, pre)
        if r.get("accepted") and 1 <= r["n_success"] <= 5:
            return {**r, "root_id": rid, "search_ns": ns, "teach": teach_log, **stats}
        teach_log.append({"root_id": rid, "ns": ns, "result": r.get("reason") or f"FINAL_NS_{r.get('n_success')}", "disagreements": r.get("disagreements")})
    return {"reason": "TEACH_REJECTED", "teach": teach_log, **stats}


if __name__ == "__main__":
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    host, ds, out, jobs_f, workers, cpus = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4], int(sys.argv[5]), sys.argv[6]
    a, b = map(int, cpus.split("-"))
    os.sched_setaffinity(0, set(range(a, b + 1)))
    pins = json.loads((H / os.environ.get("DEP3D_PINS", "snapshot_a_root_sha256.json")).read_text())
    (out / "store").mkdir(parents=True, exist_ok=True)
    led = out / "ledger.jsonl"
    done = {json.loads(l)["job_id"] for l in led.read_text().splitlines() if '"ADMIN_STOP' not in l} if led.exists() else set()
    todo = [j for j in json.loads(Path(jobs_f).read_text()) if j["job_id"] not in done]
    print(f"{time.strftime('%FT%TZ', time.gmtime())} hard3d host={host} jobs={len(todo)} workers={workers} cpus={cpus}", flush=True)
    with open(led, "a", buffering=1) as f, mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(host, ds, str(out), pins)) as pool:
        for i, r in enumerate(pool.imap_unordered(job, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
            t = D.pkg_temp()
            if i % 5 == 0 or i == len(todo):
                print(f"{time.strftime('%FT%TZ', time.gmtime())} {i}/{len(todo)} temp={t}", flush=True)
            if (out / "STOP").exists() or (t is not None and t >= STOP_C):
                print(f"STOP (file or temp {t})", flush=True)
                break
