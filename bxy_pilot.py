"""BXY-P9 bounded pilot (BXY_P9_TEACHER_PILOT_INSTRUCTIONS §D, §E, §G): predeclared TRAIN-only roster and per-root worklist (fixed before any
new outcome is seen), supervised per-root worker processes (RLIMIT_CPU per root, aggregate CPU / wall guards, 2 workers), atomic resumable
per-query results, censored-not-zero on administrative kills, and the immutable BXY_SIDECAR_V2_PILOT.
    python3 bxy_pilot.py plan | run | sidecar | figures            (worker: python3 bxy_pilot.py worker <root> <cpu_allow_s>)"""
from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

import bd_core as bc
import bxy_data as bd

OUT = Path("runs/approach_b/bxy_teacher_pilot_v1")
CAPS = {"roots": 20, "x": 60, "y": 60, "cpu_s": 3600.0, "wall_s": 3600.0, "workers": 2, "root_cpu_s": 300.0}
PER_ROOT = {"x": 3, "y": 3}
QUOTA = (("K0", 4), ("K1", 6), ("K>=2", None), ("None", 3))
TYPES = ("Y0", "old_success", "reversed_pair", "old_fail", "intermediate_prefix", "omission", "nuisance")


def jw(p, obj):
    """Atomic JSON write."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    os.replace(tmp, p)


def rd(p):
    return json.loads(Path(p).read_text())


# ------------------------------------------------------------------ predeclared roster and worklist (no new outcome is read)
def stratum(rec):
    k = rec["verified_K"]
    return "None" if k is None else "K0" if k == 0 else "K1" if k == 1 else "K>=2"


def roster(R) -> dict:
    tr = sorted((k for k, r in R.items() if bd.split_of(r) == "train"), key=lambda k: bc.sha([k, "BXY_P9_ROSTER"]))
    pick, dev = [], {}
    for s, n in QUOTA:
        pool = [k for k in tr if stratum(R[k]) == s]
        take = pool if n is None else pool[:n]
        pick += take
        if n is not None and len(pool) < n:
            dev[s] = f"only {len(pool)} available"
    rest = sorted((k for k in tr if k not in pick), key=lambda k: (-max([len(b["sequence"]) for b in R[k]["labels"]["B"]] or [0]), bc.sha([k, "BXY_P9_ROSTER"])))
    pick += rest[:CAPS["roots"] - len(pick)]                 # diversity: the longest recorded sequences (5-6 relocations)
    return {"roots": pick[:CAPS["roots"]], "strata": {k: stratum(R[k]) for k in pick}, "deviations": dev,
            "rule": "train only; per stratum sorted by sha([root,'BXY_P9_ROSTER']); 4 K0, 6 K1, all K>=2, 3 None, rest = longest recorded sequences"}


def items_for(k, rec) -> dict:
    """Priority list of query types (B roles and lengths only; never a new outcome); X/Y keys deduplicated; per-root caps 3 X / 3 Y."""
    B = [([(o, int(d)) for o, d in b["sequence"]], b) for b in rec["labels"]["B"]]
    cand = {"Y0": ([], False, True)}
    succ = next((s for s, b in B if b["y"] == 1 and b["role"] == "minimal"), None) or next((s for s, b in B if b["y"] == 1), None)
    if succ:
        cand["old_success"] = (succ, True, True)
        rev = next((s for s, _ in B if s != succ and len(s) == len(succ) and sorted(s) == sorted(succ)), None)
        if rev:
            cand["reversed_pair"] = (rev, True, False)                       # shares the old_success endpoint Y
    fail = next((s for s, b in B if b["y"] == 0 and b["failed_step"] == "target"), None) or next((s for s, b in B if b["y"] == 0), None)
    if fail:
        cand["old_fail"] = (fail, True, True)
    long_ = max((s for s, _ in B if len(s) >= 2), key=len, default=None)
    if long_:
        cand["intermediate_prefix"] = (long_[:-1], True, True)
        cand["omission"] = ([a for i, a in enumerate(long_) if i != 0], True, True)  # omit the first action; recomputed from S0
    nui = next((s for s, b in B if b["role"] in ("noop_irrelevant", "alternative_destination", "wrong_destination")), None)
    if nui:
        cand["nuisance"] = (nui, True, True)
    out, xs, ys, missing = [], set(), set(), []
    for t in TYPES:
        if t not in cand:
            missing.append(f"{t}: not available in this root's catalogue")
            continue
        seq, wx, wy = cand[t]
        xk, yk = bd.xkey(k, seq), bd.ykey(k, rec, seq)
        wx, wy = wx and xk not in xs, wy and yk not in ys
        if not (wx or wy):
            missing.append(f"{t}: duplicate of an earlier query")
            continue
        if wy and len(ys) >= PER_ROOT["y"] and t in ("intermediate_prefix", "omission", "nuisance") and wx and len(xs) < PER_ROOT["x"]:
            wy = False                                                       # X-only contrast with the spare X allowance
            missing.append(f"{t}: Y not queried (per-root Y cap)")
        if (wx and len(xs) >= PER_ROOT["x"]) or (wy and len(ys) >= PER_ROOT["y"]):
            missing.append(f"{t}: per-root cap")
            continue
        xs |= {xk} if wx else set()
        ys |= {yk} if wy else set()
        out.append({"id": f"{len(out):02d}_{t}", "type": t, "seq": [list(a) for a in seq], "x": wx, "y": wy})
    return {"items": out, "missing": missing}


def plan() -> dict:
    R = bd.roots()
    ros = roster(R)
    wl = {k: items_for(k, R[k]) for k in ros["roots"]}
    nx, ny = sum(i["x"] for v in wl.values() for i in v["items"]), sum(i["y"] for v in wl.values() for i in v["items"])
    assert nx <= CAPS["x"] and ny <= CAPS["y"] and all(bd.split_of(R[k]) == "train" for k in ros["roots"])
    ros["hash"], wlh = bc.sha(ros), bc.sha(wl)
    jw(OUT / "ROSTER.json", ros)
    jw(OUT / "WORKLIST.json", {"hash": wlh, "roster_hash": ros["hash"], "caps": CAPS, "per_root": PER_ROOT, "n_x": nx, "n_y": ny, "roots": wl})
    return {"roots": len(ros["roots"]), "strata": ros["strata"], "x": nx, "y": ny, "roster_hash": ros["hash"], "worklist_hash": wlh, "deviations": ros["deviations"]}


# ------------------------------------------------------------------ worker (one root; RLIMIT_CPU set by the supervisor)
def legacy_witnesses(rec, seq):
    """Stored historical relocation witness ids of a recorded B sequence that starts with seq (determinism diagnostic only)."""
    for b in rec["labels"]["B"]:
        s = [(o, int(d)) for o, d in b["sequence"]]
        if s[:len(seq)] == [tuple(a) for a in seq] and b["witnesses"]:
            done = len(s) if b["failed_step"] in (None, "target") else b["failed_step"]
            if done >= len(seq):
                return b["witnesses"][:len(seq)]
    return None


def worker(k) -> None:
    import bxy_teacher as T
    R, E = bd.roots(), T.env()
    rec, wl = R[k], rd(OUT / "WORKLIST.json")["roots"][k]["items"]
    S = rd("runs/approach_b/bxy/SIDECAR.json")[k]["y_obs"]
    cache, d = {}, OUT / "results" / k
    d.mkdir(parents=True, exist_ok=True)
    for it in wl:
        for side in ("x", "y"):
            f = d / f"{it['id']}.{side}.json"
            if not it[side] or f.exists():
                continue                                      # resume: never re-run (never double-charge) a finished query
            jw(d / f"{it['id']}.{side}.inprogress", {"started": time.time()})
            seq = [tuple(a) for a in it["seq"]]
            if side == "x":
                row = T.x_query(E, k, rec, seq, cache, OUT, legacy_witnesses(rec, seq))
            else:
                row = T.y_query(E, k, rec, seq, cache, OUT, (S.get(bd.ykey(k, rec, seq)) or {}).get("y"))
            jw(f, row | {"item": it["id"], "type": it["type"], "teacher_hash": T.teacher_hash()})
            (d / f"{it['id']}.{side}.inprogress").unlink()


# ------------------------------------------------------------------ supervisor
def run() -> dict:
    wl = rd(OUT / "WORKLIST.json")
    led = OUT / "LEDGER.jsonl"
    done = {json.loads(x)["root"] for x in led.read_text().splitlines()} if led.exists() else set()
    spent = sum(json.loads(x)["cpu_s"] for x in led.read_text().splitlines()) if led.exists() else 0.0
    todo, live, t0 = [k for k in wl["roots"] if k not in done], {}, time.time()
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    while todo or live:
        reserved = sum(v[1] for v in live.values())
        while todo and len(live) < CAPS["workers"] and time.time() - t0 < CAPS["wall_s"]:
            allow = min(CAPS["root_cpu_s"], CAPS["cpu_s"] - spent - reserved)
            if allow < 30:                                    # aggregate CPU cap: no new root can be started
                break
            k = todo.pop(0)

            def lim(a=int(allow)):
                resource.setrlimit(resource.RLIMIT_CPU, (a, a + 5))
            p = subprocess.Popen([sys.executable, "bxy_pilot.py", "worker", k], env=env, preexec_fn=lim,
                                 stdout=open(OUT / "logs" / f"{k}.log", "w"), stderr=subprocess.STDOUT)
            live[p.pid] = (k, allow, time.time(), p)
            reserved += allow
        if not live:
            break
        pid, status, ru = os.wait4(-1, os.WNOHANG) if time.time() - t0 < CAPS["wall_s"] else (None, None, None)
        if pid is None:                                       # wall cap: terminate the running roots (their open queries -> censored)
            for k_, a, ts, p in live.values():
                p.kill()
            for pid_ in list(live):
                _, status, ru = os.wait4(pid_, 0)
                finish(live.pop(pid_), status, ru, "WALL_CAP", led)
                spent += ru.ru_utime + ru.ru_stime
            break
        if pid == 0:
            time.sleep(1.0)
            continue
        cpu = ru.ru_utime + ru.ru_stime
        spent += cpu
        finish(live.pop(pid), status, ru, None, led)
    return {"cpu_s": round(spent, 1), "wall_s": round(time.time() - t0, 1), "roots_not_started": todo}


def finish(entry, status, ru, why, led):
    k, allow, ts, _ = entry
    sig = os.WIFSIGNALED(status) and os.WTERMSIG(status)
    reason = why or ("CPU_CAP(RLIMIT_CPU)" if sig in (24, 9) else f"SIGNAL_{sig}" if sig else None if os.WEXITSTATUS(status) == 0 else f"EXIT_{os.WEXITSTATUS(status)}")
    for f in (OUT / "results" / k).glob("*.inprogress"):     # an administratively interrupted query is CENSORED (unobserved), never 0
        item, side = f.name.split(".")[:2]
        jw(f.with_suffix(".json"), {"root": k, "item": item, "attempted": True, "observed": False, "y": None, "teacher_status": "CENSORED",
                                    "censor_reason": reason or "worker exited with an unfinished query"})
        f.unlink()
    with open(led, "a") as fh:
        fh.write(json.dumps({"root": k, "cpu_s": round(ru.ru_utime + ru.ru_stime, 2), "wall_s": round(time.time() - ts, 1), "cpu_allow_s": allow,
                             "exit": reason}) + "\n")


# ------------------------------------------------------------------ immutable sidecar and summary
def rows():
    """{(root, item, side): row}; a predeclared query without a result file was never started (NOT_ATTEMPTED, unobserved)."""
    wl, out = rd(OUT / "WORKLIST.json")["roots"], {}
    for k, v in wl.items():
        for it in v["items"]:
            for side in ("x", "y"):
                if it[side]:
                    f = OUT / "results" / k / f"{it['id']}.{side}.json"
                    out[(k, it["id"], side)] = rd(f) if f.exists() else {"root": k, "item": it["id"], "type": it["type"], "attempted": False,
                                                                          "observed": False, "y": None, "teacher_status": "NOT_ATTEMPTED_BUDGET"}
                    out[(k, it["id"], side)]["type"] = it["type"]
    return out


def sidecar() -> dict:
    import subprocess as sp
    import bxy_teacher as T
    E, Rw, R = T.env(), rows(), bd.roots()
    th = {r["teacher_hash"] for r in Rw.values() if "teacher_hash" in r}
    if len(th) > 1:
        raise ValueError(f"mixed teacher hashes {th}: labels from different teacher versions must never be mixed")
    wl, ros = rd(OUT / "WORKLIST.json"), rd(OUT / "ROSTER.json")
    led = [json.loads(x) for x in (OUT / "LEDGER.jsonl").read_text().splitlines()] if (OUT / "LEDGER.jsonl").exists() else []
    X = [r for (k, i, s), r in sorted(Rw.items()) if s == "x"]
    Y = [r for (k, i, s), r in sorted(Rw.items()) if s == "y"]
    ybk = {r["y_key"]: r for r in Y if "y_key" in r}
    P = [T.pair(E, x, ybk[x["parent_y_key"]], OUT) | {"root": x["root"], "x_type": x["type"], "y_type": ybk[x["parent_y_key"]]["type"]}
         for x in X if x.get("parent_y_key") in ybk]
    man = {"source_branch": sp.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
           "source_commit": sp.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
           "source_data_sha256": bd.data_hash(), "source_label_protocol": "BD_BINARY_BUDGET_V1", "teacher_hash": sorted(th),
           "new_x_teacher_version": T.X_VERSION, "y_teacher_version": T.Y_VERSION, "teacher_policy": T.TEACHER,
           "teacher_sources_sha256": {f: T.file_sha(f) for f in T.SOURCES},
           "robot_profile_hash": sorted({R[k]["scene"]["robot_profile_hash"] for k in ros["roots"]}),
           "reference_state_hash": {k: T.context(k, R[k]) for k in ros["roots"]}, "dataset_split": "train",
           "pilot_roster_hash": ros["hash"], "query_worklist_hash": wl["hash"], "caps": CAPS, "per_root": PER_ROOT,
           "measured": {"aggregate_worker_cpu_s": round(sum(x["cpu_s"] for x in led), 2), "roots_finished": len(led), "ledger": led}}
    sc = {"version": "BXY_SIDECAR_V2_PILOT", "manifest": man, "x_queries": X, "y_queries": Y, "paired": P}
    f = OUT / "BXY_SIDECAR_V2_PILOT.json"
    new = json.dumps(sc, indent=1, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    if f.exists() and f.read_text() != new:
        raise FileExistsError(f"{f} is immutable and differs from the recomputed sidecar")
    f.write_text(new)
    return sc


def summary(sc) -> dict:
    import collections
    import numpy as np
    R = bd.roots()
    X, Y, P = sc["x_queries"], sc["y_queries"], sc["paired"]
    st = lambda rs: dict(collections.Counter(r["teacher_status"] for r in rs))  # noqa: E731
    ox = [r for r in X if r["observed"]]
    reached = [r for r in ox if r.get("final_q_before_connector") is not None]
    four = collections.Counter((p["x"], p["y"]) for p in P if p["matched_protocol"] and p["x"] is not None and p["y"] is not None)
    by = lambda rs, f: {str(k): dict(collections.Counter(r["y"] for r in g)) for k, g in itertools_groupby(rs, f)}  # noqa: E731
    old = {(r["root"], r["item"]): r for r in X if r["type"] == "old_success"}
    legacy_pos = [p for p in P if p["x_type"] == "old_success" and p["full_joint_success"] is not None]
    rev = []
    for r in X:
        if r["type"] == "reversed_pair" and r["observed"]:
            o = next((x for (k, i), x in old.items() if k == r["root"] and x["observed"]), None)
            if o:
                rev.append({"root": r["root"], "order_a": o["ordered_actions"], "x_a": o["y"], "order_b": r["ordered_actions"], "x_b": r["y"],
                            "shared_y_key": o["parent_y_key"] == r["parent_y_key"], "contrast": o["y"] != r["y"]})
    jt = [(p["J_total"], R[p["root"]]) for p in P if p.get("J_total") is not None]
    legacy_J = []
    for p in P:
        if p.get("J_total") is not None:
            seq = next(x["ordered_actions"] for x in X if x["x_key"] == p["x_key"])
            lj = next((b["travel"] for b in R[p["root"]]["labels"]["B"] if [[o, int(d)] for o, d in b["sequence"]] == seq and b["y"] == 1), None)
            legacy_J.append((p["J_total"], lj))
    lj = [(a, b) for a, b in legacy_J if b is not None]
    return {"roots_selected": len({r["root"] for r in X + Y}), "x": {"total": len(X), "attempted": sum(r["attempted"] for r in X), "observed": len(ox),
            "censored": sum(r["teacher_status"] == "CENSORED" for r in X), "status": st(X), "positives": sum(r["y"] == 1 for r in ox),
            "negatives": sum(r["y"] == 0 for r in ox), "by_prefix_len": by(ox, lambda r: len(r["ordered_actions"])),
            "failed_phase": dict(collections.Counter(r.get("failed_phase") for r in ox if r["y"] == 0)),
            "legacy_witness_match": dict(collections.Counter(legacy_close(R, r) for r in ox if r.get("steps")))},
            "y": {"total": len(Y), "attempted": sum(r["attempted"] for r in Y), "observed": sum(r["observed"] for r in Y), "status": st(Y),
                  "positives": sum(r["y"] == 1 for r in Y if r["observed"]), "negatives": sum(r["y"] == 0 for r in Y if r["observed"]),
                  "legacy_agree": dict(collections.Counter(str(r.get("legacy_y") == r["y"]) if r.get("legacy_y") is not None else "no_legacy_label"
                                                           for r in Y if r["observed"]))},
            "connector": {"relocation_prefix_reached": len(reached), "connector_verified": sum(r["y"] == 1 for r in reached),
                          "connector_failed": sum(r.get("failed_phase", "").startswith("connector") for r in reached if r["y"] == 0),
                          "how": dict(collections.Counter(r.get("connector_how") for r in reached))},
            "four_cell_XY": {f"X={a},Y={b}": n for (a, b), n in sorted(four.items())}, "matched_decided_pairs": sum(four.values()),
            "legacy_B_success_satisfying_new_protocol": {"decided": len(legacy_pos), "full_joint_success": sum(p["full_joint_success"] for p in legacy_pos)},
            "reversed_order_pairs": rev, "J_total_witnesses": len(jt),
            "J_total_vs_legacy_travel": {"n": len(lj), "pearson_r": float(np.corrcoef(*zip(*lj))[0, 1]) if len(lj) >= 3 else None, "pairs": lj},
            "by_K": {s: dict(collections.Counter(p["full_joint_success"] for p in P if stratum(R[p["root"]]) == s)) for s in ("K0", "K1", "K>=2", "None")}}


def legacy_close(R, x, tol=1e-12) -> str:
    """Determinism diagnostic: re-planned relocation records vs the stored historical ones of the same recorded B prefix (same shapes,
    every array within tol). 'exact' = identical content hash."""
    import numpy as np
    import bxy_teacher as T
    leg = legacy_witnesses(R[x["root"]], [tuple(a) for a in x["ordered_actions"]])
    if not leg or not x.get("steps"):
        return "no_legacy_record"
    mine = [w for s in x["steps"] for w in s["witness"]]
    if mine == leg[:len(mine)]:
        return "exact"
    for a, b in zip(mine, leg):
        A = T.load_w(OUT, a)
        z = np.load(bd.DATA / "witnesses" / b[:2] / f"{b}.npz")
        if set(A) != set(z.files) or any(np.shape(A[k]) != z[k].shape or (A[k].dtype.kind == "f" and np.max(np.abs(A[k] - z[k]), initial=0) > tol)
                                        or (A[k].dtype.kind != "f" and not np.array_equal(A[k], z[k])) for k in A):
            return "differs"
    return f"within_{tol:g}"


def itertools_groupby(rs, f):
    import itertools
    return itertools.groupby(sorted(rs, key=f), f)


if __name__ == "__main__":
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    cmd = sys.argv[1]
    if cmd == "plan":
        print(json.dumps(plan(), indent=1))
    elif cmd == "worker":
        worker(sys.argv[2])
    elif cmd == "run":
        print(json.dumps(run(), indent=1))
    elif cmd == "sidecar":
        s = summary(sidecar())
        jw(OUT / "SUMMARY.json", s)
        print(json.dumps(s, indent=1, default=str))
    elif cmd == "figures":
        import bxy_pilot_viz as V
        print(V.all_figures())
