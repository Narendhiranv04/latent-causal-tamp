#!/usr/bin/env python3
"""FINAL_READINESS_GATE: finalized 2D X/Y for the whole 2D_K3_STRENGTH_SELECTION_V3 (5,000 scenes).  Teacher unchanged:
bxy_teacher (BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1, commit 68183081d) with its built-in independent replay, booted exactly as k3_hard/xy2d.py
(perm2d.boot(<the record's own geometry_impl>) then the approach-b-xy-v1 worktree); one exact DetPhysics cache per root.
Per root (queries listed in the item):
  K0              Y at the empty endpoint (original scene, from q_ref); X of the empty sequence = 1 by definition (no query).
  K1 / K2 / K3    SEL: X for every order of the minimal assignment (1 / 2 / 6), Y once at the shared endpoint.
  K2 / K3         OM (omission Y-negatives, OMISSION_V1 as 3D): omit one mover (sha256(root|omit)), X for every order of the rest, Y there.
  sample          EMPTY: Y at the empty endpoint for a parity sample of K1-K3 / NONE roots (vs labels.original, the same t_goal from q_ref).
  sample          PARITY: re-run of SEL on reused xy2d_all roots (vs k3_hard/xy2d_all.jsonl).
Administrative wall cap per query (1800 s) -> MISSING (never 0).  Append-only, resumable, STOP file, k10temp pause.
  xyfin2d.py build OUT_ITEMS.json
  xyfin2d.py run ITEMS.json OUT.jsonl WORKERS CPU_LO"""
import hashlib, itertools, json, os, random, signal, sys, time, traceback
from pathlib import Path

H = Path(__file__).resolve().parent
G = H.parent.parent
BL = G.parent
DS = Path("/home/naren/Desktop/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota")
SEL = G / "k3_hard/2D_K3_STRENGTH_SELECTION_V3.json"
WT = BL / ".claude/worktrees/approach-b-xy-v1"
WOUT = H.parent / "work/xy2d_witnesses"
WALL = int(os.environ.get("XYFIN2D_WALL", "1800"))     # administrative cap per query (MISSING if hit, never a label)
M = {}


def hh(s):
    return hashlib.sha256(s.encode()).hexdigest()


def rpath(r):
    return DS / "raw/roots" / f"{r['root_id']}.json" if r["source"] == "ORIGINAL_SELECTED" else Path(r["host_store"]) / "roots" / f"{r['root_id']}.json"


def okey(seq):
    return "".join(o[-1] for o, _ in seq)


def build(outp):
    rows = json.loads(SEL.read_text())["rows"]
    reuse = {json.loads(l)["root_id"] for l in open(G / "k3_hard/xy2d_all.jsonl")}
    rng = random.Random(20261112)
    items = []
    for r in rows:
        p = rpath(r)
        rec = json.loads(p.read_text())
        assert rec["ids"]["root_id"] == r["root_id"]
        if r.get("source_sha256"):
            assert hashlib.sha256(p.read_bytes()).hexdigest() == r["source_sha256"], r["root_id"]
        geom = rec.get("geometry_impl") or "original"
        q = []
        if r["K"] == "0":
            q.append({"q": "Y", "role": "EMPTY", "seq": []})
        elif r["K"] in ("1", "2", "3"):
            mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
            assign = [[o, int(d)] for o, d in mini["sequence"]]
            assert len(assign) == int(r["K"]), r["root_id"]
            if r["root_id"] in reuse:
                if rng.random() < 0.075:                                   # parity re-run of a reused xy2d record
                    q += [{"q": "X", "role": "PARITY", "seq": list(s)} for s in itertools.permutations(assign)] + [{"q": "Y", "role": "PARITY", "seq": assign}]
            else:
                q += [{"q": "X", "role": "SEL", "seq": list(s)} for s in itertools.permutations(assign)] + [{"q": "Y", "role": "SEL", "seq": assign}]
            if r["K"] in ("2", "3"):
                movers = sorted(o for o, _ in assign)
                om = movers[int(hh(r["root_id"] + "|omit")[:8], 16) % len(movers)]
                rest = [a for a in assign if a[0] != om]
                q += [{"q": "X", "role": "OM", "omitted": om, "seq": list(s)} for s in itertools.permutations(rest)] + \
                     [{"q": "Y", "role": "OM", "omitted": om, "seq": rest}]
        if r["K"] != "0" and rng.random() < 0.04:                          # parity of labels.original (empty endpoint)
            q.append({"q": "Y", "role": "EMPTY_PARITY", "seq": []})
        if q:
            items.append({"key": f"R2_{r['root_id']}", "root_id": r["root_id"], "K": r["K"], "split": r["split"], "path": str(p), "geom": geom, "queries": q})
    Path(outp).write_text(json.dumps(items))
    import collections as C
    print("items", len(items), C.Counter((it["K"], qq["role"], qq["q"]) for it in items for qq in it["queries"]))


class AdminWall(Exception):
    pass


def _alarm(sig, frm):
    raise AdminWall("query wall cap")


def temp():
    for d in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (d / "name").read_text().strip() == "k10temp":
                return int((d / "temp1_input").read_text()) / 1000
        except OSError:
            pass
    return None


def boot(geom):
    sys.path.insert(0, str(BL / "order_classification_2d"))
    import perm2d as P
    P.boot(geom)
    if "boot_error" in P._M:
        M["boot_error"] = P._M["boot_error"]
        return
    sys.path.insert(0, str(WT))
    import bxy_teacher as T
    M.update(T=T, E=T.env())
    signal.signal(signal.SIGALRM, _alarm)


KEEP = ("y", "teacher_status", "negative_kind", "failed_phase", "independent_replay", "replay_why", "x_key", "y_key", "parent_y_key",
        "witness_relocations", "witness_connector", "target_witness", "process_cpu_s", "attempted", "observed", "why")


def job(it):
    out = {"key": it["key"], "root_id": it["root_id"], "K": it["K"], "split": it["split"], "geom": it["geom"], "results": []}
    if "boot_error" in M:
        return {**out, "error": "boot: " + M["boot_error"]}
    t = temp()
    if t is not None and t >= 96:
        while (t := temp()) is not None and t > 92:
            time.sleep(20)
    T, E = M["T"], M["E"]
    rec = json.loads(Path(it["path"]).read_text())
    cache = {}
    c0 = time.process_time()
    for q in it["queries"]:
        w0 = time.time()
        try:
            signal.alarm(WALL)
            fn = T.x_query if q["q"] == "X" else T.y_query
            r = fn(E, it["root_id"], rec, q["seq"], cache, out=str(WOUT))
            signal.alarm(0)
            res = {k: r.get(k) for k in KEEP if k in r}
            res["resolution"] = "EVALUATED" if r.get("y") in (0, 1) or r.get("teacher_status") == "EMPTY_PREFIX_X_IS_1_BY_DEFINITION" else "NOT_ATTEMPTED"
        except AdminWall as e:
            res = {"resolution": "UNRESOLVED_ADMIN", "error": str(e)}
        except Exception as e:  # noqa: BLE001
            signal.alarm(0)
            res = {"resolution": "UNRESOLVED_ERROR", "error": f"{type(e).__name__}: {str(e)[:200]}", "trace": traceback.format_exc()[-600:]}
        out["results"].append({**{k: q[k] for k in q}, **res, "wall_s": round(time.time() - w0, 2)})
    out["cpu_s"] = round(time.process_time() - c0, 1)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build(sys.argv[2]); sys.exit()
    import multiprocessing as mp
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    items, outp, workers, lo = json.loads(Path(sys.argv[2]).read_text()), Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    os.sched_setaffinity(0, set(range(lo, lo + workers)))
    done = {json.loads(l)["key"] for l in outp.read_text().splitlines() if l.strip()} if outp.exists() else set()
    todo = [it for it in items if it["key"] not in done]
    todo.sort(key=lambda it: -len(it["queries"]))                    # long roots first (better packing)
    by = {}
    for it in todo:
        by.setdefault(it["geom"], []).append(it)
    with open(outp, "a", buffering=1) as f:
        for geom, its in sorted(by.items()):
            print(f"{time.strftime('%FT%TZ', time.gmtime())} geom={geom} items={len(its)} workers={workers}", flush=True)
            with mp.get_context("spawn").Pool(workers, initializer=boot, initargs=(geom,), maxtasksperchild=200) as pool:
                for i, r in enumerate(pool.imap_unordered(job, its), 1):
                    f.write(json.dumps(r) + "\n"); f.flush(); os.fsync(f.fileno())
                    if i % 25 == 0 or i == len(its):
                        print(f"{time.strftime('%FT%TZ', time.gmtime())} {geom} {i}/{len(its)} temp={temp()}", flush=True)
                    if (outp.parent / "STOP").exists():
                        print("STOP file: exiting", flush=True); pool.terminate(); sys.exit()
