#!/usr/bin/env python3
"""R3.1 3B: 2D long-witness development cohort (DEV_ORDER_2D) with the UNCHANGED k3scale generator + frozen BXY teacher (never release_v2).

static   gen_deep.run (GENDEEP3 SA on the sound MINK_STATIC_V2 bound, parking prior) with STRING seeds 'R3COH2D|i' (a namespace disjoint from
         every integer seed of earlier campaigns) -> candidate layouts with K_lb in {4, 5, 6} (proposals only; no teacher call).
witness  witness_v3.job (frozen <= 6-relocation teacher via teacher_long, independent X / Y replay, Y(empty)) on candidates in
         sha256('R3COH|' + fingerprint) order, strata interleaved, N in [9, 15] first; a stratum closes at 10 accepted.
         Accepted = X = 1 and Y = 1 (replayed), Y(empty) = 0, witness length L in {4, 5, 6}; CERTIFIED_MIN_K iff L = K_lb(V1) = K_lb(V2).
Caps (cumulative, incl. static CPU): 400 layouts witnessed, 4,000 teacher queries (each prefix X try, final X, final Y and Y(empty) counted), 24 CPU-h.
    python gen2d.py static I0 N STEPS WORKERS CPU_LO OUT.jsonl
    python gen2d.py witness LAYOUTS.jsonl OUT.jsonl WORKERS CPU_LO [MAXQ=10]"""
from __future__ import annotations

import hashlib, json, os, sys, time
from multiprocessing import get_context
from pathlib import Path

K3S = Path(os.environ.get("K3SCALE", "/home/projects/long-horizon/naren_workspace/k3scale"))
sys.path.insert(0, str(K3S))
TABLE, QCLEAR = K3S / "G1/MINK_TABLE_original.json", K3S / "G1/QCLEAR_original.json"
CAPS = {"layouts": 400, "queries": 4000, "cpu_h": 24.0, "per_L": 10}
LEDGER = Path(os.environ.get("R3_GEN_LEDGER", "/home/projects/long-horizon/naren_workspace/fig3/r3/gen2d_ledger.json"))


def _static(args):
    i, steps = args
    import gen_deep as GD
    T = json.loads(TABLE.read_text()); qc = set(json.loads(QCLEAR.read_text())["cells"])
    c0 = time.process_time()
    _, firsts = GD.run(T, qc, f"R3COH2D|{i}", steps, 6)
    out = []
    for k, L in sorted(firsts.items()):
        if 4 <= k <= 6:
            fp = hashlib.sha256(json.dumps([L["cells0"], L["goal_cell"]]).encode()).hexdigest()[:16]
            out.append({"geom": T["geom"], "seed": f"R3COH2D|{i}", "gen": "GENDEEP3", "root_id": f"R3COH2D-{i:05d}-K{k}", "fingerprint": fp, **L})
    return out, time.process_time() - c0


def static(i0, n, steps, workers, cpu_lo, outp):
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    cpu = 0.0
    with get_context("spawn").Pool(int(workers)) as pool, open(outp, "a") as f:
        for out, c in pool.imap_unordered(_static, [(i, int(steps)) for i in range(int(i0), int(i0) + int(n))]):
            cpu += c
            for L in out:
                f.write(json.dumps(L) + "\n")
            f.flush()
    led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    led["static_cpu_s"] = led.get("static_cpu_s", 0.0) + cpu
    led["static_seeds"] = led.get("static_seeds", 0) + int(n)
    LEDGER.write_text(json.dumps(led, indent=1))
    print("STATIC_DONE", json.dumps(led))


def nq(r):
    return 1 + len(r.get("tries", [])) + sum(1 for t in r.get("tries", []) if t.get("final"))


def accepted(r):
    ok = [t for t in r.get("tries", []) if t.get("final") and t.get("x") == 1 and t.get("y") == 1 and t.get("x_replay") and t.get("y_replay")]
    if not ok or (r.get("Y0") or {}).get("y") != 0:
        return None
    L = len(ok[0]["seq"])
    return L if 4 <= L <= 6 else None


def _wjob(args):
    import witness_v3 as WV
    return WV.job(args)


def witness(layouts, outp, workers, cpu_lo, maxq=10):
    os.sched_setaffinity(0, set(range(int(cpu_lo), int(cpu_lo) + int(workers))))
    T = json.loads(TABLE.read_text())
    Ls = {}
    for l in open(layouts):
        L = json.loads(l)
        Ls.setdefault(L["fingerprint"], L)
    pri = lambda L: (not 9 <= L["n_objects"] <= 15, hashlib.sha256(("R3COH|" + L["fingerprint"]).encode()).hexdigest())  # noqa: E731
    strata = {k: sorted([L for L in Ls.values() if L["K_lb"] == k], key=pri) for k in (4, 5, 6)}
    prior = [json.loads(l) for l in open(outp)] if Path(outp).exists() else []
    done = {r["root_id"] for r in prior}
    led = json.loads(LEDGER.read_text()) if LEDGER.exists() else {}
    used = {"layouts": len(prior), "queries": sum(nq(r) for r in prior), "cpu_s": led.get("static_cpu_s", 0.0) + sum(r.get("cpu_s", 0) for r in prior)}
    acc = {k: sum(1 for r in prior if accepted(r) == k) for k in (4, 5, 6)}
    queue = []
    for i in range(max(len(v) for v in strata.values())):
        for k in (4, 5, 6):
            if i < len(strata[k]) and strata[k][i]["root_id"] not in done:
                queue.append(strata[k][i])
    pool = get_context("spawn").Pool(int(workers), maxtasksperchild=4)
    running, f, qi = {}, open(outp, "a"), 0
    maxq = int(maxq); worst = maxq + 4
    while True:
        for k, (ar, t) in list(running.items()):
            if ar.ready():
                r = ar.get(); running.pop(k)
                f.write(json.dumps(r) + "\n"); f.flush()
                used["layouts"] += 1; used["queries"] += nq(r); used["cpu_s"] += r.get("cpu_s", 0)
                a = accepted(r)
                if a:
                    acc[a] += 1
                print(time.strftime("%H:%M:%S"), r["root_id"], r.get("K_lb"), r.get("verdict"), nq(r), r.get("cpu_s"), "acc", acc, "used", {k: round(v, 1) for k, v in used.items()}, flush=True)
        open_k = {k for k in (4, 5, 6) if acc[k] < CAPS["per_L"]}
        while qi < len(queue) and queue[qi]["K_lb"] not in open_k:
            qi += 1
        room = (used["layouts"] + len(running) < CAPS["layouts"] and used["queries"] + (len(running) + 1) * worst <= CAPS["queries"]
                and (used["cpu_s"] + sum(time.time() - t for _, t in running.values())) / 3600 + (len(running) + 1) * 0.05 < CAPS["cpu_h"])
        if qi < len(queue) and open_k and room and len(running) < int(workers):
            L = queue[qi]; qi += 1
            running[L["root_id"]] = (pool.apply_async(_wjob, ((T, L, 8, int(maxq)),)), time.time()); continue
        if not running:
            break
        time.sleep(2)
    pool.terminate()
    led.update(witness_used=used, accepted=acc, undispatched=len(queue) - qi)
    LEDGER.write_text(json.dumps(led, indent=1))
    print("WITNESS_DONE", json.dumps(led))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "static":
        static(*a[1:7])
    elif a[0] == "witness":
        witness(*a[1:5], *(a[5:6] or [10]))
