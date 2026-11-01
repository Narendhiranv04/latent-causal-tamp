"""BXY-P23 one-shot collection engine (BXY_ENGINE_P23_V1): the P-min / P20 supervisor semantics (frozen per-root query order, RLIMIT_CPU
per worker, attempted failure = operational 0, interrupted = CENSORED, never started = UNATTEMPTED) hardened against the P20 incident, in
which a supervisor of an earlier session kept running in another PID namespace, was invisible to `ps`, and raced a second supervisor.

  supervisor lock   SUPERVISOR.lock is held with flock(LOCK_EX | LOCK_NB) for the supervisor's lifetime (kernel-level, per inode: visible
                    across PID namespaces sharing the filesystem); SUPERVISOR.json records the owner UUID, manifest sha256 and a heartbeat.
                    A second launch refuses while the lock is held, while a heartbeat is fresh, or while a previous owner never released
                    (stale ownership needs the explicit `recover` step; never a blind restart).
  reservations      reservations/<root>.json is created with O_EXCL by the supervisor before launch; a worker additionally holds
                    locks/<root>.lock and refuses (exit 75, no write) without both, so no two workers can label one root.
  results           one file per query, written once: tmp + fsync + os.link (fails if the file exists) and an embedded sha256 of the row;
                    rows that fail the hash or the frozen design identity are CORRUPT (never re-queried, reported as a custody event).
  recovery          the charge of a lost worker is min(allowance, CPU at its last beat + 2 x wall time since): workers are 1-thread
                    processes that write locks/<root>.beat (getrusage CPU) every HEARTBEAT_S, so the bound holds even if a C call stalls the beat.
  ledger            LEDGER.jsonl, append-only, fsync'd, hash-chained (each event carries the sha256 of the previous line); CPU of every
                    phase (construction, cache, labelling, evaluation) is charged here.
  teacher           injected by name: "mock" (deterministic, for the synthetic smoke tests) or "bxy" (bxy_teacher.x_query /
                    bxy_pmin.y_query_counted with the unchanged per-query budget); no teacher code is imported for "mock".
    python3 bxy_p23_engine.py worker <out> <root> <owner> <teacher> [opts-json] | recover <out> <owner> <note> | audit <out>"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import resource
import signal
import socket
import subprocess as sp
import sys
import time
import uuid
from pathlib import Path

VERSION = "BXY_ENGINE_P23_V1"
EXIT_DUPLICATE, EXIT_IDENTITY = 75, 76
HEARTBEAT_S = float(os.environ.get("BXY_ENGINE_HEARTBEAT_S", 5.0))
STALE_S = float(os.environ.get("BXY_ENGINE_STALE_S", 120.0))
THREAD_BOUND = 2.0                                               # CPU-s per wall-s a 1-thread worker (+ beat thread) can burn after its last beat
RELAUNCH = ("INTERRUPTED", "WALL_CAP", "RECOVERED")             # exits after which a later session may resume the root's unattempted queries


class EngineRefusal(RuntimeError):
    pass


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)).encode()


def sha(obj) -> str:
    return hashlib.sha256(canon(obj)).hexdigest()


def _fsync_dir(d):
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_once(path, row) -> bool:
    """Atomic, no-overwrite write of {"row", "sha256"}; False if the file already exists (the existing file is never touched)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with open(tmp, "wb") as fh:
        fh.write(canon({"row": row, "sha256": sha(row)}))
        fh.flush()
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
        return True
    except FileExistsError:
        return False
    finally:
        tmp.unlink()
        _fsync_dir(path.parent)


def read_row(path, key=None):
    """(status, row): OK / CORRUPT (unreadable, hash mismatch or design-key mismatch) / MISSING."""
    path = Path(path)
    if not path.exists():
        return "MISSING", None
    try:
        d = json.loads(path.read_bytes())
        ok = sha(d["row"]) == d["sha256"] and (key is None or d["row"].get("design_key") == key)
    except (ValueError, KeyError, TypeError, OSError):
        return "CORRUPT", None
    return ("OK", d["row"]) if ok else ("CORRUPT", None)


def jw(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_bytes(canon(obj))
    os.replace(tmp, p)


# ------------------------------------------------------------------ hash-chained ledger
def ledger(out) -> list:
    f = Path(out) / "LEDGER.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def append(out, ev) -> dict:
    f = Path(out) / "LEDGER.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a+b") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        lines = [x for x in fh.read().splitlines() if x.strip()]
        ev = dict(ev, n=len(lines), prev=hashlib.sha256(lines[-1]).hexdigest() if lines else None, t=ev.get("t", time.time()))
        fh.write(canon(ev) + b"\n")
        fh.flush()
        os.fsync(fh.fileno())
        fcntl.flock(fh, fcntl.LOCK_UN)
    return ev


def verify_ledger(out) -> dict:
    f = Path(out) / "LEDGER.jsonl"
    lines = [x for x in f.read_bytes().splitlines() if x.strip()] if f.exists() else []
    for i, x in enumerate(lines):
        e = json.loads(x)
        if e.get("n") != i or e.get("prev") != (hashlib.sha256(lines[i - 1]).hexdigest() if i else None):
            return {"ok": False, "broken_at": i, "events": len(lines)}
    return {"ok": True, "events": len(lines)}


def charge(out, phase, cpu_s, wall_s, note="") -> dict:
    """Non-worker compute (construction, input cache, prediction, evaluation) charged to the same aggregate budget."""
    return append(out, {"event": "charge", "phase": phase, "cpu_s": round(float(cpu_s), 3), "wall_s": round(float(wall_s), 3), "note": note})


def spent(out) -> dict:
    cpu, roots, first, last_t = 0.0, {}, None, None
    for e in ledger(out):
        if e["event"] in ("finish", "recovery"):
            roots[e["root"]] = roots.get(e["root"], 0.0) + e["cpu_s"]
        if e["event"] in ("finish", "recovery", "charge"):
            cpu += e["cpu_s"]
        if e["event"] == "launch" and first is None:
            first = e["t"]
        last_t = e["t"]
    return {"cpu_s": round(cpu, 3), "per_root": roots, "t_first_launch": first, "t_last": last_t}


# ------------------------------------------------------------------ supervisor ownership
class Supervisor:
    """Exclusive supervisor ownership of `out` (context manager)."""

    def __init__(self, out, manifest_sha="", stale_s=None):
        self.out, self.manifest_sha, self.uuid = Path(out), manifest_sha, uuid.uuid4().hex
        self.stale_s = STALE_S if stale_s is None else stale_s
        self.fd, self.beat = None, 0.0

    def __enter__(self):
        self.out.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.out / "SUPERVISOR.lock", os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise EngineRefusal("DUPLICATE_SUPERVISOR: SUPERVISOR.lock is held by another live process")
        prev = json.loads((self.out / "SUPERVISOR.json").read_text()) if (self.out / "SUPERVISOR.json").exists() else None
        if prev and prev.get("state") == "RUNNING":
            os.close(fd)
            if time.time() - prev["heartbeat"] < self.stale_s:
                raise EngineRefusal(f"LIVE_OWNER_HEARTBEAT: owner {prev['owner']} beat {time.time() - prev['heartbeat']:.0f} s ago")
            raise EngineRefusal(f"STALE_OWNER_REQUIRES_RECOVERY: owner {prev['owner']} never released; run `recover {self.out} {prev['owner']} <note>`")
        if any((self.out / "reservations").glob("*.json")):
            os.close(fd)
            raise EngineRefusal("RESERVATIONS_PRESENT: root reservations without a running owner; explicit recovery required")
        self.fd = fd
        self.heartbeat(state="RUNNING")
        append(self.out, {"event": "supervisor_start", "owner": self.uuid, "manifest_sha256": self.manifest_sha, "pid": os.getpid(), "version": VERSION})
        return self

    def heartbeat(self, state="RUNNING", force=True):
        if not force and time.time() - self.beat < HEARTBEAT_S:
            return
        cur = json.loads((self.out / "SUPERVISOR.json").read_text()) if (self.out / "SUPERVISOR.json").exists() else None
        if cur and cur.get("state") == "RUNNING" and cur["owner"] != self.uuid:
            raise EngineRefusal(f"OWNERSHIP_LOST: SUPERVISOR.json now names {cur['owner']}")
        self.beat = time.time()
        jw(self.out / "SUPERVISOR.json", {"owner": self.uuid, "state": state, "heartbeat": self.beat, "pid": os.getpid(), "host": socket.gethostname(),
                                          "manifest_sha256": self.manifest_sha, "version": VERSION})

    def __exit__(self, *exc):
        self.heartbeat(state="RELEASED")
        append(self.out, {"event": "supervisor_release", "owner": self.uuid})
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        return False


def _root_lock_free(out, k) -> bool:
    f = Path(out) / "locks" / f"{k}.lock"
    if not f.exists():
        return True
    fd = os.open(f, os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return True
    except BlockingIOError:
        return False
    finally:
        os.close(fd)


def recover(out, owner, note) -> dict:
    """Explicit, documented recovery of a stale owner: refuses while any lock is held or the heartbeat is fresh; charges every reserved root
    its full allowance (conservative), censors its in-progress queries, removes the reservations and records the note."""
    out = Path(out)
    cur = json.loads((out / "SUPERVISOR.json").read_text())
    if cur["owner"] != owner or cur["state"] != "RUNNING":
        raise EngineRefusal("RECOVER_OWNER_MISMATCH")
    if time.time() - cur["heartbeat"] < STALE_S:
        raise EngineRefusal("RECOVER_HEARTBEAT_FRESH")
    fd = os.open(out / "SUPERVISOR.lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise EngineRefusal("RECOVER_SUPERVISOR_LOCK_HELD")
    try:
        done = []
        for f in sorted((out / "reservations").glob("*.json")):
            r = json.loads(f.read_text())
            if not _root_lock_free(out, r["root"]):
                raise EngineRefusal(f"RECOVER_WORKER_ALIVE: {r['root']}")
            censor(out, r["root"], "SUPERVISOR_LOST")
            b = Path(out) / "locks" / f"{r['root']}.beat"
            beat = json.loads(b.read_text()) if b.exists() else None
            ok = beat is not None and beat.get("owner") == owner
            cpu = min(r["allow"], beat["cpu_s"] + THREAD_BOUND * (time.time() - beat["t"])) if ok else r["allow"]
            append(out, {"event": "recovery", "root": r["root"], "cpu_s": round(cpu, 3), "owner": owner, "exit": "RECOVERED", "note": note,
                         "bound": "min(allowance, last worker-beat CPU + %.0f x wall since that beat)" % THREAD_BOUND if ok else "full allowance (no beat)"})
            f.unlink()
            done.append(r["root"])
        jw(out / "SUPERVISOR.json", dict(cur, state="RECOVERED", recovered_at=time.time(), note=note))
        append(out, {"event": "recover_owner", "owner": owner, "roots": done, "note": note})
        return {"recovered_roots": done}
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ------------------------------------------------------------------ design, worker
def design(out) -> dict:
    return json.loads((Path(out) / "DESIGN.json").read_text())


def worklist(D) -> dict:
    return {k: [dict(q, key=key) for key, q in sorted(D["roots"][k]["queries"].items(), key=lambda kv: (kv[1]["side"], kv[0]))] for k in D["root_order"]}


def qpath(out, k, i, side) -> Path:
    return Path(out) / "results" / k / f"{i:04d}.{side}.json"


def record_sha(rec) -> str:
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()   # == bd_core.sha


def censor(out, k, reason):
    for m in sorted((Path(out) / "results" / k).glob("*.inprogress")):
        i, side = m.name.split(".")[:2]
        write_once(m.with_name(f"{i}.{side}.json"), {"root": k, "item": int(i), "side": side, "design_key": json.loads(m.read_text()).get("key"),
                                                     "attempted": True, "observed": False, "y": None, "teacher_status": "CENSORED", "censor_reason": reason})
        m.unlink()


def _mock_teacher(opts):
    burn = float(opts.get("burn_s", 0.0))

    def teach(k, rec, q, i):
        if opts.get("crash_at") == i:
            os._exit(3)
        if opts.get("sleep_s"):
            time.sleep(float(opts["sleep_s"]) * (1 + (int(hashlib.sha256(k.encode()).hexdigest()[:2], 16) % 3)))
        t = time.process_time()
        while time.process_time() - t < burn:
            pass
        key = q["key"] if opts.get("wrong_key_at") != i else "WRONG"
        return {"root": k, f"{q['side']}_key": key, "attempted": True, "observed": True, "y": int(hashlib.sha256(q["key"].encode()).hexdigest()[0], 16) % 2,
                "teacher_status": "MOCK"}
    return teach


def _bxy_teacher(out):
    import bxy_pmin as PM
    import bxy_teacher as T
    E, cache = T.env(), {}

    def teach(k, rec, q, i):
        seq = [tuple(a) for a in q["seq"]]
        return T.x_query(E, k, rec, seq, cache, out) if q["side"] == "x" else PM.y_query_counted(E, k, rec, seq, cache, out, None)
    return teach, T.teacher_hash()


def worker(out, k, owner, teacher="mock", opts=None) -> int:
    out = Path(out)
    (out / "locks").mkdir(parents=True, exist_ok=True)
    fd = os.open(out / "locks" / f"{k}.lock", os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return EXIT_DUPLICATE
        res = out / "reservations" / f"{k}.json"
        if not res.exists() or json.loads(res.read_text()).get("owner") != owner:
            return EXIT_DUPLICATE
        return _label(out, k, owner, teacher, opts)
    finally:
        os.close(fd)                                                      # closing the descriptor releases the root lock


def _label(out, k, owner, teacher, opts) -> int:
    import threading

    def beat():
        while True:
            ru = resource.getrusage(resource.RUSAGE_SELF)
            jw(out / "locks" / f"{k}.beat", {"owner": owner, "t": time.time(), "cpu_s": ru.ru_utime + ru.ru_stime})
            time.sleep(HEARTBEAT_S)
    threading.Thread(target=beat, daemon=True).start()
    D = design(out)
    rec = json.loads((out / "roots" / f"{k}.json").read_text())
    if record_sha(rec) != D["roots"][k]["record_sha256"]:
        return EXIT_IDENTITY
    teach, th = (_mock_teacher(opts or {}), "MOCK") if teacher == "mock" else _bxy_teacher(out)
    for i, q in enumerate(worklist(D)[k]):
        f = qpath(out, k, i, q["side"])
        if f.exists():
            continue                                                      # finished, censored or corrupt: never re-queried
        m = f.with_name(f"{i:04d}.{q['side']}.inprogress")
        jw(m, {"started": time.time(), "key": q["key"], "owner": owner})
        row = teach(k, rec, q, i)
        if row.get(f"{q['side']}_key") != q["key"]:
            row = {"root": k, "attempted": True, "observed": False, "y": None, "teacher_status": "IDENTITY_MISMATCH", "got": row.get(f"{q['side']}_key")}
        write_once(f, row | {"item": i, "side": q["side"], "design_key": q["key"], "teacher_hash": th, "engine": VERSION, "owner": owner})
        m.unlink()
    return 0


# ------------------------------------------------------------------ supervision
def supervise(out, limits, teacher="mock", opts=None, manifest_sha="", poll=0.2, roots=None, stop_after=None) -> dict:
    """Label the frozen design under limits {cpu_s, root_cpu_s, workers, wall_s, min_allow}; one owner; returns the halt reason."""
    out = Path(out)
    with Supervisor(out, manifest_sha) as S:
        stop = {"why": None}
        old = {s: signal.signal(s, lambda *_: stop.update(why="INTERRUPTED")) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            return _loop(out, S, dict(limits), teacher, opts, poll, roots, stop, stop_after)
        finally:
            for s, h in old.items():
                signal.signal(s, h)


def _status(out):
    last = {}
    for e in ledger(out):
        if e["event"] in ("finish", "recovery"):
            last[e["root"]] = e["exit"]
    return last


def _loop(out, S, L, teacher, opts, poll, roots, stop, stop_after):
    D = design(out)
    roots = list(roots if roots is not None else D["root_order"])
    last, sp0 = _status(out), spent(out)
    todo = [k for k in roots if k not in last or last[k] in RELAUNCH]
    t_first = sp0["t_first_launch"]
    live, halted, launched = {}, None, 0
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "reservations").mkdir(parents=True, exist_ok=True)
    while todo or live:
        S.heartbeat(force=False)
        wall_left = L["wall_s"] - (time.time() - t_first) if t_first else L["wall_s"]
        if wall_left <= 0 or stop["why"]:
            halted = "WALL_CAP" if wall_left <= 0 else stop["why"]
            for p in [v[3] for v in live.values()]:
                p.send_signal(signal.SIGKILL)
            for pid in list(live):
                _, status, ru = os.wait4(pid, 0)
                _finish(out, live.pop(pid), status, ru, halted)
            break
        sp_ = spent(out)
        while todo and len(live) < L["workers"] and halted is None and (stop_after is None or launched < stop_after):
            k = todo[0]
            reserved = sum(v[1] for v in live.values())
            left = L["cpu_s"] - sp_["cpu_s"] - reserved
            allow = min(L["root_cpu_s"] - sp_["per_root"].get(k, 0.0), left)
            if left < L["min_allow"]:
                halted = "AGGREGATE_CPU_CAP"
                break
            todo.pop(0)
            if allow < L["min_allow"]:
                append(out, {"event": "finish", "root": k, "cpu_s": 0.0, "exit": "ROOT_CAP_EXHAUSTED", "wall_s": 0.0})
                continue
            fd = os.open(out / "reservations" / f"{k}.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            os.write(fd, canon({"root": k, "owner": S.uuid, "allow": allow, "t": time.time()}))
            os.fsync(fd)
            os.close(fd)
            if t_first is None:
                t_first = append(out, {"event": "launch", "owner": S.uuid})["t"]

            def lim(a=int(allow)):
                resource.setrlimit(resource.RLIMIT_CPU, (max(1, a - 1), a))
            cmd = [sys.executable, str(Path(__file__).resolve()), "worker", str(out), k, S.uuid, teacher, json.dumps(opts or {})]
            p = sp.Popen(cmd, env=env, preexec_fn=lim, stdout=open(out / "logs" / f"{k}.log", "a"), stderr=sp.STDOUT, cwd=os.getcwd())
            append(out, {"event": "start", "root": k, "allow": allow, "pid": p.pid, "owner": S.uuid})
            live[p.pid] = (k, allow, time.time(), p)
            launched += 1
        if not live:
            halted = halted or ("STOP_AFTER" if todo else None)
            break
        pid, status, ru = os.wait4(-1, os.WNOHANG)
        if pid == 0:
            time.sleep(poll)
            continue
        why = _finish(out, live.pop(pid), status, ru, None)
        if why in ("DUPLICATE_WORKER_REFUSED", "IDENTITY_MISMATCH"):
            halted = why                                                   # custody event: stop launching, let live workers finish
    if halted and halted != "STOP_AFTER":
        for k in todo:
            append(out, {"event": "not_started", "root": k, "reason": halted})
    sp1 = spent(out)
    return {"halted": halted, "spent_cpu_s": sp1["cpu_s"], "wall_s": round(time.time() - t_first, 1) if t_first else 0.0, "not_started": todo}


def _finish(out, entry, status, ru, why) -> str:
    k, allow, ts, _ = entry
    sig = os.WIFSIGNALED(status) and os.WTERMSIG(status)
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
    reason = why or ("CPU_CAP(RLIMIT_CPU)" if sig in (signal.SIGXCPU, signal.SIGKILL) else f"SIGNAL_{sig}" if sig else
                     None if code == 0 else "DUPLICATE_WORKER_REFUSED" if code == EXIT_DUPLICATE else "IDENTITY_MISMATCH" if code == EXIT_IDENTITY else f"EXIT_{code}")
    censor(out, k, reason or "worker exited with an unfinished query")
    cpu = ru.ru_utime + ru.ru_stime
    append(out, {"event": "finish", "root": k, "cpu_s": round(cpu, 3), "wall_s": round(time.time() - ts, 2), "exit": reason, "maxrss_kb": ru.ru_maxrss})
    (Path(out) / "reservations" / f"{k}.json").unlink(missing_ok=True)
    return reason


# ------------------------------------------------------------------ reconstruction
def rows(out, D=None) -> dict:
    """{(root, i, side): row} for the whole frozen worklist with status OBSERVED / CENSORED / CORRUPT / UNATTEMPTED (+ reason)."""
    out, D = Path(out), D or design(out)
    last = _status(out)
    res = {}
    for k, qs in worklist(D).items():
        for i, q in enumerate(qs):
            st, r = read_row(qpath(out, k, i, q["side"]), q["key"])
            base = {"root": k, "item": i, "side": q["side"], "design_key": q["key"], "attempted": False, "observed": False, "y": None}
            if st == "MISSING":
                res[(k, i, q["side"])] = base | {"status": "UNATTEMPTED", "reason": last.get(k) or "NOT_STARTED"}
            elif st == "CORRUPT":
                res[(k, i, q["side"])] = base | {"attempted": True, "status": "CORRUPT"}
            else:
                obs = bool(r.get("observed")) and r.get("y") in (0, 1)
                res[(k, i, q["side"])] = r | {"status": "OBSERVED" if obs else "CENSORED"}
    return res


def audit(out) -> dict:
    R = rows(out)
    st = {}
    for r in R.values():
        st[r["status"]] = st.get(r["status"], 0) + 1
    leftovers = sorted(str(p.relative_to(out)) for p in Path(out).glob("results/*/*.inprogress"))
    return {"ledger": verify_ledger(out), "status": st, "inprogress_left": leftovers, "reservations_left": sorted(p.stem for p in Path(out).glob("reservations/*.json")),
            "spent": {k: v for k, v in spent(out).items() if k != "per_root"}, "corrupt_is_custody_event": st.get("CORRUPT", 0) > 0}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "worker":
        sys.exit(worker(a[1], a[2], a[3], a[4], json.loads(a[5]) if len(a) > 5 else None))
    elif a[0] == "recover":
        print(json.dumps(recover(a[1], a[2], a[3])))
    elif a[0] == "audit":
        print(json.dumps(audit(a[1]), indent=1))
