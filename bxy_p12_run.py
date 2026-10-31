"""BXY-P12 execution runner: the 108 frozen P11 / P11.1 training runs under the committed authorization manifest and hard resource ceilings.

  authorize   writes AUTHORIZATION.json once (P11 design / lock, P11.1 design / lock, P-min evidence, roster hash, source + runner hashes, limits)
  launch      parent scheduler: verifies the manifest (values, git clean), roster identity, then runs workers (one subprocess per run, 1 thread)
  worker      one run: the frozen trainer (fit_resumable == bxy_p11.fit, bitwise) with atomic checkpoints, deterministic resume, predictions
              on its held-out / early-stopping roots, immutable RESULT.json

Resource ceilings (never exceeded to finish a run): aggregate worker CPU (reservation-based: a run launches only if the sum of finished CPU,
the full allowances of running workers, its own remaining per-run allowance and the evaluation reserve fit under the cap), per-run CPU
across resumes (kernel RLIMIT_CPU: SIGXCPU -> checkpoint + exit 76 at allowance - grace, SIGKILL at the allowance), wall time across
sessions (durable ledger), workers (memory-gated 2 -> 4 -> 8 ramp), 1 torch / BLAS thread per worker. A run cut by a ceiling stays
incomplete: no fabricated result is ever written."""
from __future__ import annotations

import copy
import ctypes
import fcntl
import hashlib
import json
import os
import platform
import resource
import shutil
import signal
import subprocess as sp
import sys
import time
import warnings
from pathlib import Path

import numpy as np

OUT = Path("runs/approach_b/bxy_p12_v1")
AUTH_NAME = "AUTHORIZATION.json"
LIMITS = {"aggregate_cpu_s": 110000, "per_run_cpu_s": 3500, "workers": 8, "wall_s": 31200, "runs": 108, "torch_threads": 1}
RESERVE = {"evaluation_cpu_s": 10000, "evaluation_wall_s": 1800}
RAMP = (2, 4, 8)
MEM = {"floor_gb": 2.0, "per_worker_gb": 0.8, "critical_gb": 1.0}
CKPT_EVERY, GRACE, MAX_ATTEMPTS, ATTEMPT_WALL_S, MARGIN_CPU_S = 60, 15, 3, 7200, 5.0
FAILURES = ("crash", "corrupt_output", "timeout", "parent_lost")              # attempt reasons that count toward MAX_ATTEMPTS
EXIT = {"ok": 0, "interrupted": 75, "cpu_cap": 76}
ENTRY = ("bxy_p12_run.py",)
THREAD_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "PYTHONHASHSEED": "0"}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jsha(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()


def safe(rid) -> str:
    return rid.replace("/", "__")


def atomic(p, data) -> None:
    p = Path(p)
    t = p.with_name(p.name + f".tmp{os.getpid()}")
    with open(t, "wb") as f:
        f.write(data if isinstance(data, bytes) else json.dumps(data, indent=1, sort_keys=True, default=str).encode())
        f.flush()
        os.fsync(f.fileno())
    os.replace(t, p)


def atomic_torch(p, obj) -> None:
    import io
    import torch
    b = io.BytesIO()
    torch.save(obj, b)
    atomic(p, b.getvalue())


# ------------------------------------------------------------------ roster, authorization
def design() -> dict:
    import bxy_p11_1 as A
    return json.loads((A.OUT / "TRAINING_DESIGN_P11_1.json").read_text())


def check_roster(runs, n=LIMITS["runs"]) -> list:
    ids = [r["id"] for r in runs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate run ids: {sorted({i for i in ids if ids.count(i) > 1})}")
    if len(ids) != n:
        raise ValueError(f"roster has {len(ids)} runs, authorized {n}")
    return runs


def auth_values() -> dict:
    import bxy_p11 as P
    import bxy_p11_1 as A
    import bxy_pmin as PM
    d = design()
    return {"gate": "BXY-P12", "scope": "development training of the frozen 108-run roster only; no teacher query, fresh data, GPU, independent test "
            "evaluation, PREFIX_COMPLETE, P-full or 3D", "limits": LIMITS, "reserve_inside_limits": RESERVE, "ramp": list(RAMP), "memory_gate": MEM,
            "p11_design_sha256": P.sha(P.OUT / "TRAINING_DESIGN.json"), "p11_lock_sha256": P.sha(P.OUT / "TRAINING_LOCK.json"),
            "p11_1_design_sha256": P.sha(A.OUT / "TRAINING_DESIGN_P11_1.json"), "p11_1_lock_sha256": P.sha(A.OUT / "TRAINING_LOCK_P11_1.json"),
            "evidence_sha256": P.EVIDENCE, "roster_sha256": jsha(d["roster"]), "folds_sha256": jsha(d["folds"]), "runs": len(check_roster(d["roster"])),
            "sources": PM.sources(ENTRY), "runner_sha256": sha("bxy_p12_run.py")}


def authorize(out=OUT) -> dict:
    """The separate, versioned authorization manifest (historical P11 / P11.1 locks keep authorized = false). Written once."""
    import bxy_p11_1 as A
    A.assert_frozen(check_git=True)
    a = auth_values() | {"authorized": True, "authorized_by": "user execution contract BXY-P11.1 + BXY-P12 (2026-10-31): development training under "
                         "the listed absolute ceilings", "created_at": time.time()}
    f = Path(out) / AUTH_NAME
    if f.exists():
        raise FileExistsError(f"{f} exists; a changed authorization needs a new versioned manifest")
    Path(out).mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(a, indent=1, sort_keys=True))
    return a


def verify_auth(out=OUT, check_git=True) -> dict:
    f = Path(out) / AUTH_NAME
    if not f.exists():
        raise PermissionError("no authorization manifest")
    a = json.loads(f.read_text())
    if a.get("authorized") is not True:
        raise PermissionError("manifest does not authorize training")
    now = auth_values()
    bad = [k for k in now if a.get(k) != now[k]]
    if bad:
        raise PermissionError(f"authorization drift: {bad}")
    if check_git:
        import bxy_p11_1 as A
        A.assert_frozen(check_git=True)
        for p in (str(f), "bxy_p12_run.py"):
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                raise PermissionError(f"{p} not committed / not clean")
    return a


# ------------------------------------------------------------------ the frozen trainer with checkpoint / resume (== bxy_p11.fit)
def fit_resumable(arm, seed, tr, es, lam, cfg, state=None, hook=None):
    """bxy_p11.fit, update for update, plus resumable state. hook(u_done, snapshot) after every update that does not end training; a
    truthy return stops training (the caller already saved snapshot()). Returns (model, info) or None when stopped by the hook."""
    import torch
    import bxy_p11 as P
    torch.set_num_threads(cfg["torch_threads"])
    m = P.build_model(arm, seed)
    np.random.seed(seed)
    opt = torch.optim.AdamW(m.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    rng, n = np.random.default_rng(seed), len(tr)
    best, stale, hist, u0 = (float("inf"), copy.deepcopy(m.state_dict()), 0), 0, [], 0
    if state:
        m.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        rng.bit_generator.state = state["rng"]
        np.random.set_state(state["np_global"])
        torch.set_rng_state(state["torch_rng"])
        best, stale, hist, u0 = (state["best"][0], state["best"][1], state["best"][2]), state["stale"], state["hist"], state["u"]
    snap = lambda u: {"model": copy.deepcopy(m.state_dict()), "opt": copy.deepcopy(opt.state_dict()), "rng": rng.bit_generator.state,  # noqa: E731
                      "np_global": np.random.get_state(), "torch_rng": torch.get_rng_state(), "best": best, "stale": stale, "hist": hist, "u": u}
    for u in range(u0, cfg["max_updates"]):
        idx = sorted(rng.choice(n, size=min(cfg["batch_roots"], n), replace=False).tolist())
        opt.zero_grad()
        tot, rec = P.batch_loss(m, [tr[i][0] for i in idx], [tr[i][1] for i in idx], lam)
        if not torch.isfinite(tot):
            hist.append({"update": u, "nonfinite": True})
            break
        tot.backward()
        rec |= {"update": u, "total": float(tot.detach()), "grad_pre": float(torch.nn.utils.clip_grad_norm_(m.parameters(), cfg["clip_norm"]))}
        opt.step()
        if (u + 1) % cfg["eval_every"] == 0:
            with torch.no_grad():
                rec["es_nll"] = float(np.mean([float(P.root_terms(m, s, l)[0]) for s, l in es]))
            if rec["es_nll"] < best[0] * (1 - cfg["rel_tol"]) if np.isfinite(best[0]) else True:
                best, stale = (rec["es_nll"], copy.deepcopy(m.state_dict()), u + 1), 0
            else:
                stale += 1
        hist.append(rec)
        if stale >= cfg["patience_evals"]:
            break
        if hook and u + 1 < cfg["max_updates"] and hook(u + 1, lambda: snap(u + 1)):
            return None
    m.load_state_dict(best[1])
    return m.eval(), {"best_update": best[2], "es_nll": best[0], "updates_run": len(hist), "stopped_early": stale >= cfg["patience_evals"],
                      "params": P.params(m), "lambda_J": lam, "history": hist}


# ------------------------------------------------------------------ run specs and data
def lambda_select(es: dict, lambdas, seeds, rel_tol=1e-3) -> dict:
    """es: {(arm, lam, seed): best early-stopping NLL}. Per J-trained arm: lam* = argmin of the 3-seed mean; within rel_tol of the minimum
    -> the smaller lambda. An arm with any missing seed is BLOCKED (None)."""
    out = {}
    for arm in sorted({a for a, _, _ in es}):
        if any((arm, l, s) not in es for l in lambdas for s in seeds):
            out[arm] = {"lambda": None, "blocked": "missing SPLIT runs"}
            continue
        mean = {l: float(np.mean([es[(arm, l, s)] for s in seeds])) for l in lambdas}
        lo = min(mean.values())
        out[arm] = {"lambda": min(l for l in lambdas if mean[l] - lo <= rel_tol * abs(lo)), "mean_es_nll": {str(l): v for l, v in mean.items()}}
    return out


def roster(out, synthetic) -> list:
    return json.loads((Path(out) / "SYN_ROSTER.json").read_text()) if synthetic else design()["roster"]


def resolved_lambda(spec, out):
    if spec["lambda_J"] != "SELECTED":
        return float(spec["lambda_J"])
    f = Path(out) / "LAMBDA_SELECTION.json"
    if not f.exists():
        raise RuntimeError("lambda* not selected yet")
    lam = json.loads(f.read_text())["selection"][spec["arm"]]["lambda"]
    if lam is None:
        raise RuntimeError(f"lambda* blocked for {spec['arm']}")
    return float(lam)


def root_sets(spec, d) -> dict:
    """train / early-stop / predict root keys of a run from the frozen design (sorted; predict = early-stop (SPLIT) or held-out (CROSSFIT))."""
    if spec["phase"] == "SPLIT":
        return {"train": sorted(d["custody"]["train"]), "es": sorted(d["custody"]["val"]), "predict": sorted(d["custody"]["val"])}
    f = d["folds"]["folds"][int(spec["train"].split(".")[0][4:])]
    return {"train": sorted(f["train"]), "es": sorted(f["early_stop"]), "predict": sorted(f["heldout"])}


def real_data(spec) -> tuple:
    """(tr [(sv, lab)], es [(sv, lab)], pr [sv], sets): the worker keeps scorer views and labels of its own train / early-stop roots and
    scorer views ONLY of its prediction roots; evaluator views and every other label are dropped immediately."""
    import bxy_data as bd
    import bxy_p11 as P
    d = design()
    s = root_sets(spec, d)
    held = set(s["predict"]) if spec["phase"] == "CROSSFIT" else set()
    if set(s["train"]) & set(s["es"]) or (set(s["train"]) | set(s["es"])) & held:
        raise RuntimeError(f"{spec['id']}: overlapping root sets")
    sc, D, R, I = P.load()
    if any(bd.split_of(R[k]) == "test" for v in s.values() for k in v):
        raise RuntimeError("test root in a run")
    V = {sv["key"]: (sv, lab) for sv, lab, _ in P.build(sc=sc, D=D, R=R, I=I)}
    tr, es, pr = [V[k] for k in s["train"]], [V[k] for k in s["es"]], [V[k][0] for k in s["predict"]]
    del V
    return tr, es, pr, s


def synthetic_root(seed):
    """A random synthetic root (NOT real data; runner fault-injection tests only)."""
    import abc_models as am
    rng = np.random.default_rng(seed)
    n = 4
    inp = {"object_xy": rng.uniform(0, 0.64, (n, 2)), "object_radius": np.full(n, 0.024), "is_active_target": np.eye(n)[n - 1],
           "is_obstacle": 1 - np.eye(n)[n - 1], "robot_q": rng.uniform(-2, 2, 3), "goal_xy": rng.uniform(0, 0.64, 2),
           "robot_fk_joints": rng.uniform(0, 0.6, (4, 2)), "visual": rng.normal(size=(n, 384))}
    d = [tuple(rng.uniform(0, 0.64, 2)) for _ in range(2)]
    sv = {"key": f"syn{seed}", "R": am.Root({"inputs": inp}), "y_poses": [{}, {0: d[0], 1: d[1]}], "y0": 0,
          "x_seqs": [[(0, d[0]), (1, d[1])], [(1, d[1]), (0, d[0])], [(0, d[0])]], "parent": [1, 1, 1],
          "cands": [{"sig": "empty", "m": 0, "cd": 0.0, "xi": None, "yi": 0, "admissible": True},
                    {"sig": "o0>1", "m": 1, "cd": 1.0, "xi": 2, "yi": 1, "admissible": True}]}
    lab = {"obs_x": {0: 1, 1: 0}, "obs_y": {0: int(seed % 2), 1: 1}, "succ": {0: 1, 1: 0, None: int(seed % 2)},
           "j": [(0, 1, 3.0)] + ([(None, 0, 0.8)] if seed % 2 else [])}
    return sv, lab


def syn_data(spec) -> tuple:
    tr, es = [synthetic_root(s) for s in range(4)], [synthetic_root(s) for s in (10, 11)]
    pr = [synthetic_root(s)[0] for s in (20, 21)]
    return tr, es, pr, {"train": [x[0]["key"] for x in tr], "es": [x[0]["key"] for x in es], "predict": [x["key"] for x in pr]}


def run_cfg(spec, synthetic) -> dict:
    import bxy_p11 as P
    if not synthetic:
        return dict(P.TRAIN)
    return P.TRAIN | {"max_updates": spec.get("max_updates", 40), "eval_every": 2, "batch_roots": 3, "patience_evals": 10 ** 6}


# ------------------------------------------------------------------ worker
STOP = {"why": None}


def _stop(signum, _):
    STOP["why"] = STOP["why"] or ("cpu_cap" if signum == signal.SIGXCPU else "interrupted")


def cpu_self() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def worker(out, rid, attempt, parent_pid, synthetic=False) -> int:
    out = Path(out)
    if synthetic and out.resolve() == OUT.resolve():
        raise RuntimeError("synthetic mode never writes the real run directory")
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGXCPU):
        signal.signal(s, _stop)
    if os.getppid() != parent_pid:                                          # parent died before PDEATHSIG was armed
        return EXIT["interrupted"]
    if not synthetic:
        verify_auth(out, check_git=False)                                  # hash drift between launch and worker start
    import torch
    import bxy_p11 as P
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    spec = {r["id"]: r for r in roster(out, synthetic)}[rid]
    rd = out / "runs" / safe(rid)
    rd.mkdir(parents=True, exist_ok=True)
    if (rd / "RESULT.json").exists():
        return EXIT["ok"]
    fault = json.loads(os.environ.get("BXY_P12_FAULT", "{}")).get(rid, "") if synthetic and attempt == 1 else ""   # tests only
    lam = resolved_lambda(spec, out)
    tr, es, pr, sets = (syn_data if synthetic else real_data)(spec)
    cfg = run_cfg(spec, synthetic)
    st = torch.load(rd / "state.pt", weights_only=False) if (rd / "state.pt").exists() else None
    if st is not None and st["spec_sha"] != jsha([spec, lam, sets, cfg]):
        raise RuntimeError("checkpoint belongs to a different run spec")
    hb = lambda u, status: atomic(rd / "heartbeat.json", {"rid": rid, "attempt": attempt, "pid": os.getpid(), "cpu": cpu_self(), "update": u,  # noqa: E731
                                                          "status": status, "t": time.time()})

    def hook(u, snapshot):
        kind, _, at = fault.partition("@")
        if fault and int(at or 0) == u:
            if kind == "crash":
                os._exit(13)
            if kind == "term":
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(0.05)
            while kind in ("hang", "spin") and not STOP["why"]:
                time.sleep(0.05) if kind == "hang" else sum(range(10000))
        if STOP["why"] or u % CKPT_EVERY == 0 or (synthetic and u % 4 == 0):
            atomic_torch(rd / "state.pt", snapshot() | {"spec_sha": jsha([spec, lam, sets, cfg])})
            hb(u, STOP["why"] or "running")
        return STOP["why"] is not None

    with warnings.catch_warnings(record=True) as warn:
        warnings.simplefilter("always")
        res = fit_resumable(spec["arm"], spec["seed"], tr, es, lam, cfg, state=st, hook=hook)
    if res is None:
        return EXIT[STOP["why"]]
    m, info = res
    preds = {sv["key"]: predict_root(m, sv) for sv in pr}
    hist = info.pop("history")
    atomic_torch(rd / "best.pt", m.state_dict())
    atomic(rd / "history.json", hist)
    atomic(rd / "predictions.json", preds)
    if fault == "corrupt":
        (rd / "predictions.json").write_text("{}")
    num = {"nonfinite_updates": sum(1 for h in hist if h.get("nonfinite")), "max_grad_pre": max((h.get("grad_pre", 0.0) for h in hist), default=0.0),
           "clipped_updates": sum(1 for h in hist if h.get("grad_pre", 0.0) > cfg["clip_norm"]), "warnings": sorted({str(w.message)[:160] for w in warn})}
    res = {"rid": rid, "spec": spec, "lambda_J": lam, "cfg": cfg, "attempt": attempt, "resumed_from_update": st["u"] if st else 0,
           "info": info, "numerical": num, "roots": {k: len(v) for k, v in sets.items()}, "roots_sha256": jsha(sets),
           "files": {f: sha(rd / f) for f in ("best.pt", "history.json", "predictions.json")} if fault != "corrupt" else
           {"best.pt": sha(rd / "best.pt"), "history.json": sha(rd / "history.json"), "predictions.json": "0" * 64},
           "worker_cpu_s_final_attempt": cpu_self(), "env": {"python": platform.python_version(), "torch": torch.__version__,
                                                              "threads": torch.get_num_threads(), "host_cpus": os.cpu_count()},
           "synthetic": synthetic}
    with open(rd / "RESULT.json", "x") as f:                                # immutable: exclusive create
        json.dump(res, f, indent=1, sort_keys=True, default=str)
    (rd / "state.pt").unlink(missing_ok=True)
    hb(info["updates_run"], "done")
    return EXIT["ok"]


def predict_root(m, sv) -> dict:
    """bxy_p11.predict_all plus the exact coefficients (b, a, w, J, J0) for root-level joint NLL in the evaluation."""
    import torch
    import bxy_p11 as P
    with torch.no_grad():
        c = m.coeffs(sv)
    return P.predict_all(m, sv) | {"coeffs": {k: v.tolist() for k, v in c.items()}}


def valid_result(out, rid) -> bool:
    rd = Path(out) / "runs" / safe(rid)
    try:
        r = json.loads((rd / "RESULT.json").read_text())
        ok = r["rid"] == rid and all(sha(rd / f) == h for f, h in r["files"].items()) and set(r["files"]) == {"best.pt", "history.json", "predictions.json"}
        p = json.loads((rd / "predictions.json").read_text())
        return ok and len(p) == r["roots"]["predict"] and np.isfinite(r["info"]["es_nll"])
    except (OSError, ValueError, KeyError, TypeError):
        return False


# ------------------------------------------------------------------ parent scheduler
def mem_available_gb() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024 ** 2
    return 0.0


def proc_cpu(pid) -> float | None:
    try:
        f = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError):
        return None


def alive(pid) -> bool:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
    except (OSError, IndexError):
        return False


def worker_pids(out) -> list:
    """Live runner workers of this output directory (exact pids from /proc; never a pattern kill)."""
    me, tag, res = os.getpid(), str(Path(out).resolve()).encode(), []
    for p in Path("/proc").glob("[0-9]*"):
        try:
            c = (p / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if int(p.name) != me and any(x.endswith(b"bxy_p12_run.py") for x in c) and b"worker" in c and tag in c:
            res.append(int(p.name))
    return res


def failures(r) -> int:
    return sum(1 for a in r["attempts"] if str(a.get("reason")).startswith(FAILURES))


def mem_gate(avail_gb, running, cap) -> bool:
    return running < cap and avail_gb >= MEM["floor_gb"] + MEM["per_worker_gb"] * running


def queue_order(runs) -> list:
    """Fair launch order: SPLIT by seed, then (lambda, arm); CROSSFIT in complete (seed, fold) blocks of all 5 arms with the arm order
    rotated per block, so a partial budget leaves whole matched blocks and no arm is systematically last."""
    sp_ = sorted((r for r in runs if r["phase"] == "SPLIT"), key=lambda r: (r["seed"], str(r["lambda_J"]), r["arm"]))
    arms = sorted({r["arm"] for r in runs})
    cv = sorted((r for r in runs if r["phase"] == "CROSSFIT"),
                key=lambda r: (r["seed"], r["train"], (arms.index(r["arm"]) - r["seed"] - int(r["train"].split(".")[0][4:] or 0)) % len(arms)))
    return [r["id"] for r in sp_ + cv]


class Runner:
    def __init__(self, out=OUT, limits=LIMITS, reserve=RESERVE, synthetic=False, tick=5.0, check_git=True, expected=None, grace=GRACE,
                 attempt_wall=ATTEMPT_WALL_S, mem=mem_available_gb):
        self.out, self.limits, self.reserve, self.syn, self.tick, self.grace = Path(out), limits, reserve, synthetic, tick, grace
        self.attempt_wall, self.mem, self.check_git = attempt_wall, mem, check_git
        self.auth = None if synthetic else verify_auth(out, check_git)
        self.runs = {r["id"]: r for r in check_roster(roster(out, synthetic), limits["runs"])}
        if not synthetic and [r for r in design()["roster"]] != list(self.runs.values()):
            raise ValueError("roster differs from the frozen design")
        self.order = queue_order(list(self.runs.values()))
        self.exp = expected or (design()["budget"]["per_run_expected_cpu_s"] if not synthetic else {})
        self.lf = self.out / "LEDGER.json"
        self.L = json.loads(self.lf.read_text()) if self.lf.exists() else {
            "auth_sha256": None if synthetic else sha(self.out / AUTH_NAME), "limits": limits, "reserve": reserve, "wall_used": 0.0,
            "parent_cpu": 0.0, "sessions": [], "events": [], "runs": {i: {"status": "PENDING", "cpu": 0.0, "attempts": []} for i in self.order}}
        if set(self.L["runs"]) != set(self.runs) or self.L["limits"] != limits:
            raise ValueError("ledger does not match the roster / limits")
        self.live, self.level, self.last_mem_event, self.stop = {}, 0, -1e9, None

    # ---------------------------------------------------------- accounting
    def save(self):
        atomic(self.lf, self.L)

    def event(self, kind, **kw):
        self.L["events"].append({"t": time.time(), "kind": kind, **kw})

    def committed(self) -> float:
        return sum(r["cpu"] for r in self.L["runs"].values()) + sum(w["allowance"] for w in self.live.values())

    def aggregate_live(self) -> float:
        return sum(r["cpu"] for r in self.L["runs"].values()) + sum(w["cpu_live"] for w in self.live.values())

    def charge(self, rid, att, cpu, exit_code, reason):
        att.update(end=time.time(), cpu=cpu, exit=exit_code, reason=reason)
        self.L["runs"][rid]["cpu"] += cpu

    def reconcile(self):
        """A previous session ended uncleanly: terminate its orphan workers by exact pid, charge every unfinished attempt conservatively
        (max of the ledger's live CPU and the worker's last heartbeat, plus a margin) and requeue it."""
        orphans = worker_pids(self.out)
        for pid in orphans:
            c0 = proc_cpu(pid) or 0.0
            os.kill(pid, signal.SIGTERM)
            for _ in range(600):
                if not alive(pid):
                    break
                c0 = max(c0, proc_cpu(pid) or 0.0)
                time.sleep(0.05)
            else:
                os.kill(pid, signal.SIGKILL)
            self.event("orphan_terminated", pid=pid, cpu_seen=c0)
        for rid, r in self.L["runs"].items():
            if r["status"] != "RUNNING":
                continue
            att = r["attempts"][-1]
            hb = self.out / "runs" / safe(rid) / "heartbeat.json"
            h = json.loads(hb.read_text()) if hb.exists() else {}
            cpu = max(att.get("cpu_live", 0.0), h.get("cpu", 0.0) if h.get("attempt") == att["n"] else 0.0) + MARGIN_CPU_S
            self.charge(rid, att, min(cpu, att["allowance"]), None, "parent_lost")
            r["status"] = "DONE" if valid_result(self.out, rid) else "PENDING"
            self.event("reconciled", rid=rid, cpu=cpu, status=r["status"])

    # ---------------------------------------------------------- launching
    def need(self, rid) -> float:
        return self.limits["per_run_cpu_s"] - self.L["runs"][rid]["cpu"]

    def eligible(self, rid) -> bool:
        spec, r = self.runs[rid], self.L["runs"][rid]
        if r["status"] != "PENDING" or failures(r) >= MAX_ATTEMPTS:
            return False
        if spec["phase"] == "CROSSFIT":
            return (self.out / "LAMBDA_SELECTION.json").exists() and all(self.L["runs"][i]["status"] in ("DONE", "INCOMPLETE_CPU_CAP", "FAILED")
                                                                         for i in self.runs if self.runs[i]["phase"] == "SPLIT")
        return True

    def start(self, rid):
        spec, n = self.runs[rid], len(self.L["runs"][rid]["attempts"]) + 1
        allow = self.need(rid)
        soft, hard = max(1, int(allow - self.grace)), max(1, int(allow))

        def pre():
            resource.setrlimit(resource.RLIMIT_CPU, (soft, hard))
            ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM)    # PR_SET_PDEATHSIG: never outlive the parent
        cmd = [sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(self.out.resolve()), "--rid", rid, "--attempt", str(n),
               "--parent", str(os.getpid())] + (["--synthetic"] if self.syn else [])
        log = open(self.out / "runs" / f"{safe(rid)}.attempt{n}.log", "w")
        p = sp.Popen(cmd, env=os.environ | THREAD_ENV, stdout=log, stderr=sp.STDOUT, preexec_fn=pre, cwd=Path(__file__).resolve().parent)
        log.close()
        att = {"n": n, "session": len(self.L["sessions"]), "pid": p.pid, "allowance": allow, "rlimit": [soft, hard], "start": time.time(), "cpu_live": 0.0}
        self.L["runs"][rid]["attempts"].append(att)
        self.L["runs"][rid]["status"] = "RUNNING"
        self.live[rid] = {"p": p, "allowance": allow, "cpu_live": 0.0, "t0": time.monotonic(), "att": att, "term": None}
        self.event("launch", rid=rid, attempt=n, allowance=allow, running=len(self.live))

    def maybe_launch(self, wall_left):
        cap = min(RAMP[self.level], self.limits["workers"])
        for rid in self.order:
            if rid in self.live or not self.eligible(rid):
                continue
            if self.committed() + self.need(rid) > self.limits["aggregate_cpu_s"] - self.reserve["evaluation_cpu_s"]:
                if not self.live:                                           # nothing left to release its reservation: budget exhausted
                    self.stop = self.stop or "aggregate_cpu"
                return
            if wall_left < 1.5 * self.exp.get(self.runs[rid]["arm"], 0.0):
                self.stop = self.stop or "wall"
                return
            if not mem_gate(self.mem(), len(self.live), cap):
                return
            self.start(rid)

    def ramp(self):
        if self.level + 1 < len(RAMP) and time.monotonic() - self.last_mem_event > 300:
            progressed = sum(1 for rid, r in self.L["runs"].items() if r["status"] == "DONE" or (rid in self.live and self.hb_update(rid) >= CKPT_EVERY))
            if progressed >= RAMP[self.level]:
                self.level += 1
                self.event("ramp", workers=RAMP[self.level])

    def hb_update(self, rid) -> int:
        try:
            h = json.loads((self.out / "runs" / safe(rid) / "heartbeat.json").read_text())
            return h["update"] if h["attempt"] == self.live[rid]["att"]["n"] else 0
        except (OSError, ValueError, KeyError):
            return 0

    def terminate(self, rid, why):
        w = self.live[rid]
        if w["term"] is None:
            w["term"] = why
            w["p"].send_signal(signal.SIGTERM)
            self.event("terminate", rid=rid, why=why)

    # ---------------------------------------------------------- reaping
    def reap(self):
        for rid, w in list(self.live.items()):
            pid, status, ru = os.wait4(w["p"].pid, os.WNOHANG)
            if pid == 0:
                c = proc_cpu(w["p"].pid)
                if c is not None:
                    w["cpu_live"] = w["att"]["cpu_live"] = c
                continue
            w["p"].returncode = os.waitstatus_to_exitcode(status)
            cpu, code, r = ru.ru_utime + ru.ru_stime, w["p"].returncode, self.L["runs"][rid]
            del self.live[rid]
            if code == EXIT["ok"] and valid_result(self.out, rid):
                why, r["status"] = "done", "DONE"
            elif code == EXIT["ok"]:
                why = "corrupt_output"
                q = self.out / "quarantine" / f"{safe(rid)}.attempt{w['att']['n']}"
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(self.out / "runs" / safe(rid)), str(q))
                r["status"] = "PENDING"
            elif code == EXIT["cpu_cap"] or (code == -signal.SIGKILL and cpu >= w["allowance"] - 1.0):
                why, r["status"] = "cpu_cap", "INCOMPLETE_CPU_CAP"
            elif code == EXIT["interrupted"] or w["term"]:
                why, r["status"] = w["term"] or "interrupted", "PENDING"
            else:
                why, r["status"] = f"crash({code})", "PENDING"
            self.charge(rid, w["att"], cpu, code, why)
            if r["status"] == "PENDING" and failures(r) >= MAX_ATTEMPTS:
                r["status"] = "FAILED"
            if r["status"] == "PENDING" and self.need(rid) <= 0:
                r["status"] = "INCOMPLETE_CPU_CAP"
            self.event("reap", rid=rid, code=code, why=why, cpu=cpu, status=r["status"])

    def select_lambdas(self):
        f = self.out / "LAMBDA_SELECTION.json"
        sp_ = [s for s in self.runs.values() if s["phase"] == "SPLIT"]
        if f.exists() or any(self.L["runs"][s["id"]]["status"] not in ("DONE", "INCOMPLETE_CPU_CAP", "FAILED") for s in sp_):
            return
        es = {}
        for s in sp_:
            if s["lambda_J"] and self.L["runs"][s["id"]]["status"] == "DONE":
                es[(s["arm"], float(s["lambda_J"]), s["seed"])] = json.loads((self.out / "runs" / safe(s["id"]) / "RESULT.json").read_text())["info"]["es_nll"]
        lams = sorted({float(s["lambda_J"]) for s in sp_ if s["lambda_J"]})
        seeds = sorted({s["seed"] for s in sp_})
        sel = lambda_select(es, lams, seeds) | {a: {"lambda": None, "blocked": "missing SPLIT runs"} for a in
                                                {s["arm"] for s in sp_ if s["lambda_J"]} - {a for a, _, _ in es}}
        with open(f, "x") as fh:
            json.dump({"rule": "per J-trained arm: argmin over lambda of the 3-seed mean best val21 early-stopping NLL; relative difference <= 1e-3 "
                       "to the minimum -> smaller lambda", "selection": sel, "es_nll": {"|".join(map(str, k)): v for k, v in sorted(es.items())},
                       "t": time.time()}, fh, indent=1, sort_keys=True)
        self.event("lambda_selected", selection={a: v["lambda"] for a, v in sel.items()})
        for a, v in sel.items():
            if v["lambda"] is None:
                for s in self.runs.values():
                    if s["arm"] == a and s["lambda_J"] == "SELECTED":
                        self.L["runs"][s["id"]]["status"] = "BLOCKED_LAMBDA"

    # ---------------------------------------------------------- main loop
    def run(self) -> dict:
        (self.out / "runs").mkdir(parents=True, exist_ok=True)
        lk = open(self.out / "RUNNER.lock", "w")
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("another runner session holds the lock")
        self.reconcile()
        self.L["sessions"].append({"start": time.time(), "pid": os.getpid(), "wall_used_at_start": self.L["wall_used"]})
        old = {s: signal.signal(s, lambda *_: setattr(self, "stop", "shutdown")) for s in (signal.SIGTERM, signal.SIGINT)}
        c0, last = resource.getrusage(resource.RUSAGE_SELF), time.monotonic()
        try:
            while True:
                now = time.monotonic()
                self.L["wall_used"] += now - last
                last = now
                self.reap()
                self.select_lambdas()
                wall_left = self.limits["wall_s"] - self.reserve["evaluation_wall_s"] - self.L["wall_used"]
                if self.aggregate_live() > self.limits["aggregate_cpu_s"] - self.reserve["evaluation_cpu_s"]:    # unreachable with reservations
                    for w in self.live.values():
                        w["p"].kill()
                    self.stop = "aggregate_cpu"
                    self.event("aggregate_safety_kill")
                if wall_left <= 0 or self.stop == "shutdown":
                    for rid in list(self.live):
                        self.terminate(rid, "wall" if wall_left <= 0 else "shutdown")
                    self.stop = self.stop or "wall"
                avail = self.mem()
                if avail < MEM["critical_gb"] and self.live and now - self.last_mem_event > 60:
                    newest = max(self.live, key=lambda r: self.live[r]["t0"])
                    self.terminate(newest, "memory")
                    self.level, self.last_mem_event = max(0, self.level - 1), now
                    self.event("memory_pressure", available_gb=avail)
                for rid, w in list(self.live.items()):
                    if now - w["t0"] > self.attempt_wall:
                        self.terminate(rid, "timeout")
                if self.stop is None:
                    self.ramp()
                    self.maybe_launch(wall_left)
                for r in self.L["runs"].values():
                    for a in r["attempts"]:
                        a.setdefault("cpu_live", 0.0)
                self.save()
                if not self.live and (self.stop or not any(self.eligible(i) for i in self.order)):
                    break
                time.sleep(self.tick)
        finally:
            for s, h in old.items():
                signal.signal(s, h)
            c1 = resource.getrusage(resource.RUSAGE_SELF)
            self.L["parent_cpu"] += (c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime)
            self.L["sessions"][-1].update(end=time.time(), wall_used_at_end=self.L["wall_used"], stop=self.stop)
            self.save()
            fcntl.flock(lk, fcntl.LOCK_UN)
            lk.close()
        return self.summary()

    def summary(self) -> dict:
        st = {}
        for rid in self.order:
            s = self.L["runs"][rid]["status"]
            if s == "PENDING" and self.stop in ("aggregate_cpu", "wall"):
                tag = {"aggregate_cpu": "BUDGET", "wall": "WALL"}[self.stop]
                s = f"INCOMPLETE_{tag}" if self.L["runs"][rid]["attempts"] else f"NOT_LAUNCHED_{tag}"
            st[rid] = s
        out = {"statuses": st, "counts": {k: sum(v == k for v in st.values()) for k in sorted(set(st.values()))},
               "aggregate_cpu_s": sum(r["cpu"] for r in self.L["runs"].values()), "wall_used_s": self.L["wall_used"], "parent_cpu_s": self.L["parent_cpu"],
               "stop": self.stop, "limits": self.limits, "max_run_cpu_s": max(r["cpu"] for r in self.L["runs"].values())}
        atomic(self.out / "RUN_STATUS.json", out)
        return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["authorize", "launch", "worker", "verify"])
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--rid")
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--parent", type=int, default=0)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    if a.cmd == "authorize":
        print(json.dumps({k: v for k, v in authorize(a.out).items() if k != "sources"}, indent=1))
    elif a.cmd == "verify":
        print(json.dumps({k: v for k, v in verify_auth(a.out).items() if k != "sources"}, indent=1))
    elif a.cmd == "launch":
        print(json.dumps(Runner(a.out).run(), indent=1, default=str))
    else:
        sys.exit(worker(a.out, a.rid, a.attempt, a.parent, a.synthetic))
