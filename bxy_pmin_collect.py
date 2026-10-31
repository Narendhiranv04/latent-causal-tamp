"""BXY-P-MIN-COLLECT runner (BXY_PMIN_COLLECT_V1): bounded physical teacher collection of the frozen PMIN_DEV_MATCHED design.

The frozen design / lock (bxy_pmin, sha 8f164845...) and the 114 locked semantic sources are never modified; this module is versioned and
hashed on its own and recorded in a separate execution-authorization manifest (AUTHORIZATION_COLLECT_V1.json).
  preflight   design + lock + source drift + git (bxy_pmin.assert_frozen), authorization (limits, design / lock / runner hashes, executing
              commit), live dataset / P9 sidecar / teacher policy / QB / robot profile, query-by-query membership, key re-derivation and F1,
              P9 reuse (never re-queried), exact worklist size
  worker      one process per root, frozen query order, atomic per-query JSON with an .inprogress marker, resume = skip finished files;
              X = bxy_teacher.x_query, Y = bxy_pmin.y_query_counted (unchanged teacher, counters exposed)
  supervisor  RLIMIT_CPU per root (<= per-root cap and <= remaining aggregate minus reservations: hard from the first worker), wall cap
              from the first launch (across resumes), ramp 2 -> 4 -> 8 workers gated by free memory and external load, the after-20-roots
              projection checkpoint (extra early stop only), SIGTERM/SIGINT = safe interruption; unfinished queries -> CENSORED, never 0;
              never-started queries -> NOT_ATTEMPTED
    python3 bxy_pmin_collect.py authorize | preflight | run | worker <root> | status"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import signal
import subprocess as sp
import sys
import time
from pathlib import Path

import bd_2d
import bxy_data as bd
import bxy_f1 as F1
import bxy_pmin as PM
import bxy_teacher as T

VERSION = "BXY_PMIN_COLLECT_V1"
OUT = PM.OUT
PHASE = "PMIN_DEV_MATCHED"
DESIGN_SHA = "8f164845e5804821b8fbf9411c52ca2584f22d6f6f4a0efd19b8c3bcb86ff658"
P9_SHA = "adea6983f1303236b05c41b5755652d0b05dab808dff2951df07a8c26ca2f840"
LIMITS = {"cpu_s": 64000.0, "root_cpu_s": 3300.0, "workers": 8, "wall_s": 13800.0, "roots": 197, "x": 2165, "y": 1807}
QB = {"motion_checks": 150, "online_moves": 8, "goal_plans": 3, "transit_plans": 6}
RAMP = ((0, 2), (4, 4), (12, 8))                     # (finished roots, max concurrent workers)
MIN_ALLOW, MEM_FLOOR_GB, MEM_PER_WORKER_GB, EXT_LOAD = 60.0, 1.5, 0.8, 8.0
AUTH_TEXT = ("I explicitly authorize the collection phase PMIN_DEV_MATCHED under the following hard limits: aggregate worker CPU 64,000 "
             "CPU-seconds; per-root CPU 3,300 CPU-seconds; 8 concurrent workers maximum; collection wall time 13,800 seconds; 197 TRAIN/VAL "
             "roots; 2,165 new X queries; 1,807 new Y queries. The existing per-query teacher budgets must remain unchanged.")
RELAUNCH = ("WALL_CAP", "INTERRUPTED", "ORPHAN_CHARGED_ALLOWANCE")   # exits after which a resumed run may continue the root


class PreflightError(RuntimeError):
    pass


def jw(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    os.replace(tmp, p)


def runner_sha() -> str:
    return PM.sha_file(__file__)


def auth_path(out):
    return Path(out) / "AUTHORIZATION_COLLECT_V1.json"


def design(out=OUT) -> dict:
    return json.loads((Path(out) / "PMIN_DESIGN.json").read_text())


def worklist(D) -> dict:
    return {k: v for k, v in PM.worklist(D, PHASE).items() if v}


# ------------------------------------------------------------------ authorization manifest (separate from the frozen lock)
def authorize(out=OUT) -> dict:
    out = Path(out)
    a = {"version": "BXY_PMIN_COLLECT_AUTH_V1", "phase": PHASE, "limits": LIMITS, "per_query_budget": QB, "design_sha256": DESIGN_SHA,
         "lock_sha256": PM.sha_file(out / "PMIN_LOCK.json"),
         "lock_sources_sha256": hashlib.sha256(json.dumps(json.loads((out / "PMIN_LOCK.json").read_text())["sources"], sort_keys=True).encode()).hexdigest(),
         "historical_lock_authorized_flag": json.loads((out / "PMIN_LOCK.json").read_text())["authorized"],
         "runner": "bxy_pmin_collect.py", "runner_version": VERSION, "runner_sha256": runner_sha(), "executing_commit": PM.git("rev-parse", "HEAD"),
         "authorized_by": "user, BXY-P-MIN-COLLECT instruction message of 2026-10-31", "authorization_text": AUTH_TEXT}
    f = auth_path(out)
    if f.exists():
        old = json.loads(f.read_text())
        if {k: v for k, v in old.items() if k != "created"} != a:
            raise FileExistsError(f"{f} exists and differs")
        return old
    jw(f, a | {"created": time.time()})
    return a


# ------------------------------------------------------------------ preflight
def preflight(out=OUT, check_git=True) -> dict:
    out, bad = Path(out), []
    try:
        lock = PM.assert_frozen(out, check_git=check_git)
    except RuntimeError as e:
        raise PreflightError(f"frozen plan: {e}")
    if lock["design_sha256"] != DESIGN_SHA:
        bad.append("design sha differs from the authorized one")
    f = auth_path(out)
    if not f.exists():
        raise PreflightError("missing execution authorization manifest")
    a = json.loads(f.read_text())
    want = {"phase": PHASE, "limits": LIMITS, "per_query_budget": QB, "design_sha256": DESIGN_SHA, "lock_sha256": PM.sha_file(out / "PMIN_LOCK.json"),
            "runner_sha256": runner_sha()}
    bad += [f"authorization {k} mismatch" for k, v in want.items() if a.get(k) != v]
    if check_git:
        if sp.run(["git", "merge-base", "--is-ancestor", a.get("executing_commit", "x"), "HEAD"], capture_output=True).returncode:
            bad.append("executing commit is not an ancestor of HEAD")
        for p in ("bxy_pmin_collect.py", str(f)):
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                bad.append(f"{p} not committed / not clean")
    D = design(out)
    if bd.data_hash() != D["data_sha256"]:
        bad.append("live dataset hash differs from the design")
    if PM.sha_file(PM.PILOT) != P9_SHA:
        bad.append("P9 sidecar hash differs")
    if T.teacher_hash() != D["teacher_hash"] or T.TEACHER != D["teacher_policy"] or dict(bd_2d.QB) != QB:
        bad.append("teacher hash / policy / per-query budget differs")
    R = bd.roots()
    p9 = json.loads(PM.PILOT.read_text())
    prof = set(p9["manifest"]["robot_profile_hash"])
    if {R[k]["scene"]["robot_profile_hash"] for k in D["root_order"]} != prof:
        bad.append("robot profile differs from P9")
    W = worklist(D)
    nx = sum(q["side"] == "x" for v in W.values() for q in v)
    ny = sum(q["side"] == "y" for v in W.values() for q in v)
    if (nx, ny) != (LIMITS["x"], LIMITS["y"]) or len(W) > LIMITS["roots"]:
        bad.append(f"worklist size {nx} X / {ny} Y / {len(W)} roots differs from the authorization")
    for k, qs in W.items():
        keys = [q["key"] for q in qs]
        if len(keys) != len(set(keys)):
            bad.append(f"duplicate query in {k}")
        for q in qs:
            s = [tuple(x) for x in q["seq"]]
            f1 = F1.screen(R[k], s)
            key = T.xkey(k, R[k], s) if q["side"] == "x" else T.ykey(k, R[k], s)
            if key != q["key"] or not PM.admitted(D, k, q["key"], PHASE) or not (f1["x_ok"] if q["side"] == "x" else f1["y_ok"]):
                bad.append(f"query {q['key']} fails identity / membership / F1")
    obs = {r.get("x_key") or r.get("y_key"): r for r in p9["x_queries"] + p9["y_queries"] if r.get("observed") and r.get("y") in (0, 1)}
    reuse = [(k, key) for k in D["root_order"] for key, q in D["roots"][k]["queries"].items() if q["reuse_p9"] and PHASE in q["phases"]]
    if any(key not in obs or obs[key]["teacher_hash"] != D["teacher_hash"] for _, key in reuse):
        bad.append("a reused query has no matching P9 observation")
    if any(key == q["key"] for k, key in reuse for q in W.get(k, [])):
        bad.append("a reused P9 query is scheduled again")
    if bad:
        raise PreflightError("; ".join(bad[:20]) + (f" (+{len(bad) - 20})" if len(bad) > 20 else ""))
    return {"lock": lock, "auth": a, "design": D, "worklist": W, "reused": len(reuse), "x": nx, "y": ny}


# ------------------------------------------------------------------ worker
def worker(k, out=OUT) -> None:
    import bxy_pilot as BP
    out, D = Path(out), design(out)
    R, E = bd.roots(), T.env()
    rec, qs = R[k], worklist(D)[k]
    S = json.loads(Path("runs/approach_b/bxy/SIDECAR.json").read_text())[k]["y_obs"]      # historical Y: agreement diagnostic only
    cache, d = {}, out / "results" / k
    d.mkdir(parents=True, exist_ok=True)
    for i, q in enumerate(qs):
        f = d / f"{i:04d}.{q['side']}.json"
        if f.exists():
            continue                                                  # resume: a finished (or censored) query is never re-run
        if not PM.admitted(D, k, q["key"], PHASE):
            raise RuntimeError(f"not admitted: {q['key']}")
        m = d / f"{i:04d}.{q['side']}.inprogress"
        jw(m, {"started": time.time(), "key": q["key"]})
        seq = [tuple(a) for a in q["seq"]]
        if q["side"] == "x":
            row = T.x_query(E, k, rec, seq, cache, out, BP.legacy_witnesses(rec, seq))
        else:
            row = PM.y_query_counted(E, k, rec, seq, cache, out, (S.get(bd.ykey(k, rec, seq)) or {}).get("y"))
        if row.get(f"{q['side']}_key") != q["key"]:
            row = {"root": k, "attempted": True, "observed": False, "y": None, "teacher_status": "IDENTITY_MISMATCH", "got": row.get(f"{q['side']}_key")}
        jw(f, row | {"item": i, "side": q["side"], "design_key": q["key"], "classes": q["classes"], "teacher_hash": T.teacher_hash(),
                     "runner": VERSION})
        m.unlink()


# ------------------------------------------------------------------ supervisor
def ledger(out) -> list:
    f = Path(out) / "LEDGER.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def append(out, ev):
    with open(Path(out) / "LEDGER.jsonl", "a") as fh:
        fh.write(json.dumps(ev) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def censor(out, k, reason):
    for f in (Path(out) / "results" / k).glob("*.inprogress"):          # an interrupted query is CENSORED (unobserved), never 0
        i, side = f.name.split(".")[:2]
        jw(f.with_name(f"{i}.{side}.json"), {"root": k, "item": int(i), "side": side, "design_key": json.loads(f.read_text()).get("key"),
                                             "attempted": True, "observed": False, "y": None, "teacher_status": "CENSORED", "censor_reason": reason,
                                             "runner": VERSION})
        f.unlink()


def state(out):
    """Per-root CPU spent, last exit, and orphans (a start without a finish: previous supervisor lost)."""
    spent, last, open_ = {}, {}, {}
    for e in ledger(out):
        if e["event"] == "start":
            open_[e["root"]] = e
        elif e["event"] == "finish":
            open_.pop(e["root"], None)
            spent[e["root"]] = spent.get(e["root"], 0.0) + e["cpu_s"]
            last[e["root"]] = e["exit"]
    return spent, last, open_


def mem_gb() -> float:
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 2 ** 20
    return 0.0


def supervise(out=OUT, roots=None, limits=None, cmd=None, est=None, poll=1.0, ramp=RAMP, gates=True) -> dict:
    """Run the roots (frozen order). limits / cmd / est are injectable for fault-injection tests."""
    out, L = Path(out), dict(limits or LIMITS)
    roots = list(roots if roots is not None else worklist(design(out)))
    cmd = cmd or (lambda k: [sys.executable, "bxy_pmin_collect.py", "worker", k])
    (out / "logs").mkdir(parents=True, exist_ok=True)
    stop = {"why": None}
    old = {s: signal.signal(s, lambda *_: stop.update(why="INTERRUPTED")) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        return _loop(out, L, roots, cmd, est, poll, ramp, gates, stop)
    finally:
        for s, h in old.items():
            signal.signal(s, h)


def _loop(out, L, roots, cmd, est, poll, ramp, gates, stop):
    spent, last, orphan = state(out)
    for k, e in orphan.items():                                        # charge a lost worker its full allowance (conservative)
        censor(out, k, "SUPERVISOR_LOST")
        append(out, {"event": "finish", "root": k, "cpu_s": e["allow"], "wall_s": None, "exit": "ORPHAN_CHARGED_ALLOWANCE", "maxrss_kb": None, "t": time.time()})
        spent[k], last[k] = spent.get(k, 0.0) + e["allow"], "ORPHAN_CHARGED_ALLOWANCE"
    st = out / "COLLECT_STATE.json"
    t_first = json.loads(st.read_text())["t_first_launch"] if st.exists() else None
    todo = [k for k in roots if k not in last or last[k] in RELAUNCH]
    live, env, halted = {}, dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1"), None
    done_clean = lambda: sum(1 for k in last if last[k] is None)  # noqa: E731
    while todo or live:
        now = time.time()
        wall_left = L["wall_s"] - (now - t_first) if t_first else L["wall_s"]
        if (wall_left <= 0 or stop["why"]) and live:
            for k_, a, ts, p in list(live.values()):
                p.kill()
            for pid in list(live):
                _, status, ru = os.wait4(pid, 0)
                finish(out, live.pop(pid), status, ru, "WALL_CAP" if wall_left <= 0 else stop["why"], spent, last)
            halted = "WALL_CAP" if wall_left <= 0 else stop["why"]
            break
        if wall_left <= 0 or stop["why"]:
            halted = "WALL_CAP" if wall_left <= 0 else stop["why"]
            break
        cap_w = min(L["workers"], max(n for f, n in ramp if done_clean() >= f))
        while todo and not halted and len(live) < cap_w:
            if est is not None:
                cp = PM.checkpoint({k: v for k, v in spent.items() if last.get(k) is None}, est, L["cpu_s"])
                if not cp["ok"]:
                    halted = f"PROJECTION_CHECKPOINT({cp['projected']:.0f})"
                    break
            if gates and len(live) >= 2 and (mem_gb() < MEM_FLOOR_GB + MEM_PER_WORKER_GB or os.getloadavg()[0] - len(live) > EXT_LOAD):
                break                                                     # unsafe to add a worker now; retry next poll
            reserved = sum(v[1] for v in live.values())
            k = todo[0]
            allow = min(L["root_cpu_s"] - spent.get(k, 0.0), L["cpu_s"] - sum(spent.values()) - reserved)
            if allow < L.get("min_allow", MIN_ALLOW):
                if L["cpu_s"] - sum(spent.values()) - reserved < L.get("min_allow", MIN_ALLOW):
                    halted = "AGGREGATE_CPU_CAP" if not live else None
                    break
                todo.pop(0)                                               # this root's own cap is exhausted
                continue
            todo.pop(0)
            t_first = t_first or time.time()
            jw(st, {"t_first_launch": t_first, "runner": VERSION})

            def lim(a=int(allow)):
                resource.setrlimit(resource.RLIMIT_CPU, (max(1, a - 2), a))
            p = sp.Popen(cmd(k), env=env, preexec_fn=lim, stdout=open(out / "logs" / f"{k}.log", "a"), stderr=sp.STDOUT)
            append(out, {"event": "start", "root": k, "allow": allow, "pid": p.pid, "t": time.time(), "workers": len(live) + 1})
            live[p.pid] = (k, allow, time.time(), p)
        if not live:
            if todo and not halted:
                halted = halted or "AGGREGATE_CPU_CAP"
            break
        pid, status, ru = os.wait4(-1, os.WNOHANG)
        if pid == 0:
            jw(out / "STATUS.json", {"spent_cpu_s": round(sum(spent.values()), 1), "live": [v[0] for v in live.values()], "todo": len(todo),
                                     "finished": len(last), "wall_s": round(time.time() - t_first, 1), "workers_cap": cap_w, "mem_gb": round(mem_gb(), 2)})
            time.sleep(poll)
            continue
        finish(out, live.pop(pid), status, ru, None, spent, last)
    return {"spent_cpu_s": round(sum(spent.values()), 1), "wall_s": round(time.time() - t_first, 1) if t_first else 0.0, "halted": halted,
            "roots_not_started": todo, "finished": len(last)}


def finish(out, entry, status, ru, why, spent, last):
    k, allow, ts, _ = entry
    sig = os.WIFSIGNALED(status) and os.WTERMSIG(status)
    reason = why or ("CPU_CAP(RLIMIT_CPU)" if sig in (signal.SIGXCPU, signal.SIGKILL) else f"SIGNAL_{sig}" if sig else
                     None if os.WEXITSTATUS(status) == 0 else f"EXIT_{os.WEXITSTATUS(status)}")
    censor(out, k, reason or "worker exited with an unfinished query")
    cpu = ru.ru_utime + ru.ru_stime
    spent[k], last[k] = spent.get(k, 0.0) + cpu, reason
    append(out, {"event": "finish", "root": k, "cpu_s": round(cpu, 3), "wall_s": round(time.time() - ts, 1), "exit": reason,
                 "maxrss_kb": ru.ru_maxrss, "t": time.time()})


# ------------------------------------------------------------------ result rows
def rows(out=OUT, D=None) -> dict:
    """{(root, i, side): row} for the whole worklist; missing -> NOT_ATTEMPTED; unreadable / identity-mismatched -> CORRUPT (unobserved)."""
    out, D = Path(out), D or design(out)
    res = {}
    for k, qs in worklist(D).items():
        for i, q in enumerate(qs):
            f = out / "results" / k / f"{i:04d}.{q['side']}.json"
            base = {"root": k, "item": i, "side": q["side"], "design_key": q["key"], "classes": q["classes"], "attempted": False, "observed": False, "y": None}
            if not f.exists():
                res[(k, i, q["side"])] = base | {"teacher_status": "NOT_ATTEMPTED"}
                continue
            try:
                r = json.loads(f.read_text())
                ok = r.get("design_key") == q["key"] and (not r.get("observed") or r.get(f"{q['side']}_key") == q["key"])
            except (json.JSONDecodeError, OSError):
                r, ok = {}, False
            res[(k, i, q["side"])] = r if ok else base | {"attempted": True, "teacher_status": "CORRUPT_RESULT"}
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "worker":
        worker(a[1])
    elif a[0] == "authorize":
        print(json.dumps(authorize(), indent=1))
    elif a[0] == "preflight":
        p = preflight()
        print(json.dumps({"ok": True, "x": p["x"], "y": p["y"], "roots": len(p["worklist"]), "reused": p["reused"]}))
    elif a[0] == "run":
        preflight()
        est = PM.cost_model(design())["est_root_cpu_s"]
        print(json.dumps(supervise(est=est), indent=1))
    elif a[0] == "status":
        print(Path(OUT / "STATUS.json").read_text())
