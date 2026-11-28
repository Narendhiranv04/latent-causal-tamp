#!/usr/bin/env python3
"""R10.5 TEST_FEAS_3D collection: fresh SHELF66V3 scenes labelled ONLY for initial target feasibility (no repair witnesses).

Prospective protocol (frozen in r10/FEAS_PROTOCOL.json before the first job; no model prediction exists for any of these scenes):
  * templates  = the 8-factor construction templates of ORIGINAL TEST 3D rows (RAW routes; NONE dense/trim routes excluded): held out from
                 every model's TRAIN/VAL (ours and the V4-split baselines), never VAL templates (the V3.4 / R8B ancestry problem).
  * schedule   = a fixed deterministic job list: block pattern K0,K1,K0,K2,K1,K3 over templates sorted by sha256('R10F|'+family+'|'+cycle);
                 name 'r10f', wave = job index, slot = 0  -> new construction seeds / root ids (bd_core.ids).
  * per job    = bd_3dt_plus.construct (unchanged generator, CONSTRUCT_WALL_S cap) then ONE teacher query of the target from the initial
                 scene (bd_3dt.query/label = the dataset's own original-y contract, BD3DS66_TEACHER_V2):
                   y=1                          -> POSITIVE (plan found by the teacher)
                   y=0, negative_kind CERTIFIED -> NEGATIVE_CERTIFIED (every grasp fails a deterministic geometric check)
                   y=0, other kind              -> UNKNOWN (budget / search relative; never a certified negative)
                 construction Reject / wall cap / error -> REJECTED (ledgered).
  * acceptance = every labelled scene of every dispatched job (no class-conditional dropping); exact-geometry collisions with any registered
                 scene are excluded and ledgered.  Dispatch stops when POSITIVE >= 100 and NEGATIVE_CERTIFIED >= 200, or the CPU budget
                 (FEAS_PROTOCOL.json) is spent; in-flight jobs finish.

    $PYG feasgen.py templates OUT.json                      (r10 code env: reads TEST root files for their factor spec only)
    cd <3D generator code dir>; $PY3D feasgen.py run TEMPLATES.json OUT_DIR WORKERS     (resumable; OUT_DIR/STOP drains)
"""
from __future__ import annotations

import hashlib, json, multiprocessing as mp, os, signal, sys, time, traceback
from pathlib import Path

FACT = ("K", "displacement", "distractor_role", "distractors", "mechanism", "parking", "source", "start_pose")
PATTERN = (0, 1, 0, 2, 1, 3)
CONSTRUCT_WALL_S = 2700
TEACH_WALL_S = 900


def H(s):
    return hashlib.sha256(s.encode()).hexdigest()


def templates(out):
    HERE = Path(__file__).resolve().parent
    sys.path[:0] = [str(HERE.parent.parent.parent)]
    import evaluate as EV
    base = Path("/home/projects/long-horizon/naren_workspace/k3abl/abf/snapshot/abf_9de85710c2a7103f")
    T = {}
    for l in open(base / "data3d.jsonl"):
        r = json.loads(l)
        if r["split"] != "test":
            continue
        ns = r["root_id"].split("-")[1] if r["root_id"].startswith("3ds66-") else r["root_id"].split("_")[0]
        if ns.startswith(("lapN", "srvN")):
            continue
        j = json.load(open(EV.path_of("3D", r)))
        spec = {k: j["spec"][k] for k in FACT}
        if "intent" in j["spec"]:
            spec["intent"] = j["spec"]["intent"]
        if not isinstance(spec["K"], int) or spec["K"] > 3:
            continue
        T.setdefault(r["parent_family_id"], {"family": r["parent_family_id"], "spec": spec, "K": spec["K"], "n_test_rows": 0})["n_test_rows"] += 1
    Path(out).write_text(json.dumps(sorted(T.values(), key=lambda t: t["family"]), indent=1))
    print({k: sum(1 for t in T.values() if t["K"] == k) for k in range(4)})


def schedule(T, n):
    by = {k: [t for t in T if t["K"] == k] for k in range(4)}
    cyc, pos, jobs = {k: 0 for k in by}, {k: 0 for k in by}, []
    order = {k: [] for k in by}
    for i in range(n):
        k = PATTERN[i % len(PATTERN)]
        if not order[k]:
            order[k] = sorted(by[k], key=lambda t: H(f"R10F|{t['family']}|{cyc[k]}")); cyc[k] += 1
        jobs.append((i, order[k].pop(0)))
    return jobs


def _alarm(*a):
    raise TimeoutError("wall cap")


def work(job):
    i, t, out = job
    sys.path.insert(0, str(Path.cwd() / "shelf66_v3"))
    import run_shelf66_full as RUN
    D, A, P = RUN._modules()
    bc = RUN.bc
    G = A.env()
    ids = bc.ids(D.DOMAIN, "r10f", i, 0, t["spec"], G["config_hash"], A.TEACHER_VERSION, G["protocol"])
    e = {"job": i, "root_id": ids["root_id"], "family": ids["parent_family_id"], "template_K": t["K"], "construction_seed": ids["construction_seed"]}
    t0 = time.time()
    signal.signal(signal.SIGALRM, _alarm)
    try:
        signal.alarm(CONSTRUCT_WALL_S)
        c = P.construct(t["spec"], ids["construction_seed"], ids["root_id"])
        signal.alarm(0); e["construct_s"] = round(time.time() - t0, 1)
        store = bc.Store(out)
        signal.alarm(TEACH_WALL_S)
        env = A.build(c["objs"], c["cells"])
        A.settle(env, c["cells"])
        p, info = A.query(env, "t0", c["goal"])
        lab = A.label(p, info, witness=A.witness(store, p) if p else None)
        signal.alarm(0)
        e["status"] = "POSITIVE" if lab["y"] == 1 else "NEGATIVE_CERTIFIED" if lab["negative_kind"] == "CERTIFIED" else "UNKNOWN"
        e["negative_kind"] = lab["negative_kind"]
        rec = {"ids": ids, "domain": D.DOMAIN, "spec": t["spec"], "objects": c["objs"], "initial_cells": c["cells"], "target_src": c["src"],
               "goal": c["goal"], "geometry": G["geometry"], "source_files": G["source_files"], "roles": c["roles"], "parking": c["parking"],
               "intended_blockers": c["intended"], "construction": c.get("construction"), "labels": {"original": lab},
               "r10": {"track": "TEST_FEAS_3D", "label_contract": "BD3DS66_TEACHER_V2 original-y query; CERTIFIED negatives only", "status": e["status"]}}
        (Path(out) / "roots").mkdir(exist_ok=True)
        tmp = Path(out) / "roots" / f".{ids['root_id']}.tmp"
        tmp.write_text(json.dumps(rec, default=bc._jd)); os.replace(tmp, Path(out) / "roots" / f"{ids['root_id']}.json")
    except Exception as ex:  # noqa: BLE001  (Reject / wall cap / error: ledgered, never silently dropped)
        signal.alarm(0)
        e["status"], e["reason"] = "REJECTED", f"{type(ex).__name__}:{str(ex)[:160]}"
        if not type(ex).__name__.endswith(("Reject", "TimeoutError")):
            e["trace"] = traceback.format_exc()[-800:]
    e["wall_s"] = round(time.time() - t0, 1)
    return e


def run(tf, out, workers):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    proto = json.loads((Path(__file__).resolve().parent / "FEAS_PROTOCOL.json").read_text())
    T = json.loads(Path(tf).read_text())
    jobs = schedule(T, proto["max_jobs"])
    led = out / "ledger.jsonl"
    done = {json.loads(l)["job"]: json.loads(l) for l in open(led)} if led.exists() else {}
    cnt = lambda s: sum(1 for e in done.values() if e["status"] == s)  # noqa: E731
    cpu = lambda: sum(e["wall_s"] for e in done.values()) / 3600  # noqa: E731
    pend = [j for j in jobs if j[0] not in done]
    with mp.Pool(workers, maxtasksperchild=1) as pool, open(led, "a") as f:
        it = iter(pend); running = set(); res = {}

        def stop():
            return (out / "STOP").exists() or (cnt("POSITIVE") >= proto["target_pos"] and cnt("NEGATIVE_CERTIFIED") >= proto["target_neg"]) \
                or cpu() >= proto["cpu_h_cap"]
        while True:
            while len(running) < workers and not stop():
                j = next(it, None)
                if j is None:
                    break
                res[j[0]] = pool.apply_async(work, ((j[0], j[1], str(out)),)); running.add(j[0])
            if not running:
                break
            time.sleep(5)
            for k in [k for k in running if res[k].ready()]:
                e = res.pop(k).get(); running.discard(k); done[k] = e
                f.write(json.dumps(e) + "\n"); f.flush()
            (out / "STATUS.json").write_text(json.dumps({"utc": time.strftime("%FT%TZ", time.gmtime()), "done": len(done), "running": len(running),
                "POSITIVE": cnt("POSITIVE"), "NEGATIVE_CERTIFIED": cnt("NEGATIVE_CERTIFIED"), "UNKNOWN": cnt("UNKNOWN"), "REJECTED": cnt("REJECTED"),
                "cpu_h": round(cpu(), 2), "stop": stop()}))
    (out / "DONE").write_text(time.strftime("%FT%TZ", time.gmtime()))


if __name__ == "__main__":
    if sys.argv[1] == "templates":
        templates(sys.argv[2])
    else:
        run(sys.argv[2], sys.argv[3], int(sys.argv[4]))
