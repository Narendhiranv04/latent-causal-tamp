"""BXY-P14 execution runner: the 75 frozen P14 runs under their own authorization manifest and hard ceilings.

Reuses the P12 machinery unchanged (bxy_p12_run: the bitwise-tested trainer loop fit_resumable, atomic checkpoints, RLIMIT_CPU caps with
SIGXCPU checkpointing, PDEATHSIG, reservation-based aggregate cap, durable ledger / wall accounting, memory-gated ramp, quarantine of
corrupt outputs, exact-pid orphan handling, immutable RESULT.json with file hashes). P14 only supplies its design / roster / data / arms:
  authorize   AUTHORIZATION.json once (P14 design + hypotheses hashes, parent hashes, limits, sources, runner hash)
  launch      Runner14 = bxy_p12_run.Runner with the P14 roster (no SPLIT / lambda phase) and this file as the worker entry
  worker      one run: bxy_p12_run.fit_resumable under bxy_p14.arm_hooks(arm), predictions on the held-out fold roots
Limits: 45,000 aggregate worker CPU-s incl. a 3,000 CPU-s evaluation reserve, 1,500 CPU-s per run, 4 workers, 21,600 s wall, 75 runs."""
from __future__ import annotations

import json
import os
import signal
import subprocess as sp
import sys
import time
import warnings
from pathlib import Path

import bxy_p12_run as R
import bxy_p14 as H

OUT = H.OUT
AUTH_NAME = "AUTHORIZATION.json"
ENTRY = ("bxy_p14_run.py",)


# ------------------------------------------------------------------ authorization
def auth_values() -> dict:
    import bxy_p11 as P
    import bxy_pmin as PM
    d = H.frozen()
    return {"gate": "BXY-P14", "scope": "75 development runs of the frozen P14 design on the 176 TRAIN roots; no GPU, external API, teacher query, "
            "new data, val21 or test root", "limits": H.LIMITS, "reserve_inside_limits": H.RESERVE, "ramp": list(R.RAMP), "memory_gate": R.MEM,
            "design_sha256": P.sha(OUT / "TRAINING_DESIGN_P14.json"), "hypotheses_sha256": H.HYPOTHESES_SHA, "parents": d["parents"],
            "roster_sha256": R.jsha(d["roster"]), "folds_sha256": R.jsha(d["folds"]), "runs": len(R.check_roster(d["roster"], H.LIMITS["runs"])),
            "sources": PM.sources(ENTRY), "runner_sha256": R.sha("bxy_p14_run.py")}


def authorize(out=OUT) -> dict:
    a = auth_values() | {"authorized": True, "created_at": time.time(), "authorized_by": "user execution contract BXY-P13/P14/P15 (2026-11-01): "
                         "<= 45,000 aggregate CPU-s incl. evaluation, <= 1,500 CPU-s per run, <= 4 memory-gated workers, <= 21,600 s wall"}
    f = Path(out) / AUTH_NAME
    if f.exists():
        raise FileExistsError(f"{f} exists; a changed authorization needs a new versioned manifest")
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
        for p in (str(f), "bxy_p14_run.py", "bxy_p14.py", str(OUT / "TRAINING_DESIGN_P14.json")):
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                raise PermissionError(f"{p} not committed / not clean")
    return a


# ------------------------------------------------------------------ data
def real_data(spec) -> tuple:
    """Like bxy_p12_run.real_data over the P14 folds: scorer views + labels of the run's train / early-stop roots, scorer views only of its
    held-out roots; every root must be an original TRAIN root."""
    import bxy_p11 as P
    s = R.root_sets(spec, H.frozen())
    if set(s["train"]) & set(s["es"]) or (set(s["train"]) | set(s["es"])) & set(s["predict"]):
        raise RuntimeError(f"{spec['id']}: overlapping root sets")
    sc, D, Rr, I = P.load()
    if any(P.bd.split_of(Rr[k]) != "train" for v in s.values() for k in v):
        raise RuntimeError("non-TRAIN root in a P14 run")
    V = {sv["key"]: (sv, lab) for sv, lab, _ in P.build(splits=("train",), sc=sc, D=D, R=Rr, I=I)}
    tr, es, pr = [V[k] for k in s["train"]], [V[k] for k in s["es"]], [V[k][0] for k in s["predict"]]
    del V
    return tr, es, pr, s


def roster(out, synthetic) -> list:
    return json.loads((Path(out) / "SYN_ROSTER.json").read_text()) if synthetic else H.frozen()["roster"]


# ------------------------------------------------------------------ worker (bxy_p12_run.worker with the P14 roster / data / arm hooks)
def worker(out, rid, attempt, parent_pid, synthetic=False) -> int:
    out = Path(out)
    if synthetic and out.resolve() == OUT.resolve():
        raise RuntimeError("synthetic mode never writes the real run directory")
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGXCPU):
        signal.signal(s, R._stop)
    if os.getppid() != parent_pid:
        return R.EXIT["interrupted"]
    if not synthetic:
        verify_auth(out, check_git=False)
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    spec = {r["id"]: r for r in roster(out, synthetic)}[rid]
    rd = out / "runs" / R.safe(rid)
    rd.mkdir(parents=True, exist_ok=True)
    if (rd / "RESULT.json").exists():
        return R.EXIT["ok"]
    fault = json.loads(os.environ.get("BXY_P14_FAULT", "{}")).get(rid, "") if synthetic and attempt == 1 else ""   # tests only
    lam = float(spec["lambda_J"])
    tr, es, pr, sets = (R.syn_data if synthetic else real_data)(spec)
    cfg = R.run_cfg(spec, synthetic)
    st = torch.load(rd / "state.pt", weights_only=False) if (rd / "state.pt").exists() else None
    if st is not None and st["spec_sha"] != R.jsha([spec, lam, sets, cfg]):
        raise RuntimeError("checkpoint belongs to a different run spec")
    hb = lambda u, status: R.atomic(rd / "heartbeat.json", {"rid": rid, "attempt": attempt, "pid": os.getpid(), "cpu": R.cpu_self(), "update": u,  # noqa: E731
                                                            "status": status, "t": time.time()})

    def hook(u, snapshot):
        kind, _, at = fault.partition("@")
        if fault and int(at or 0) == u:
            if kind == "crash":
                os._exit(13)
            if kind == "term":
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(0.05)
            while kind in ("hang", "spin") and not R.STOP["why"]:
                time.sleep(0.05) if kind == "hang" else sum(range(10000))
        if R.STOP["why"] or u % R.CKPT_EVERY == 0 or (synthetic and u % 4 == 0):
            R.atomic_torch(rd / "state.pt", snapshot() | {"spec_sha": R.jsha([spec, lam, sets, cfg])})
            hb(u, R.STOP["why"] or "running")
        return R.STOP["why"] is not None

    with warnings.catch_warnings(record=True) as warn, H.arm_hooks(spec["arm"]):
        warnings.simplefilter("always")
        res = R.fit_resumable(spec["arm"], spec["seed"], tr, es, lam, cfg, state=st, hook=hook)
    if res is None:
        return R.EXIT[R.STOP["why"]]
    m, info = res
    preds = {sv["key"]: R.predict_root(m, sv) for sv in pr}
    hist = info.pop("history")
    R.atomic_torch(rd / "best.pt", m.state_dict())
    R.atomic(rd / "history.json", hist)
    R.atomic(rd / "predictions.json", preds)
    if fault == "corrupt":
        (rd / "predictions.json").write_text("{}")
    num = {"nonfinite_updates": sum(1 for h in hist if h.get("nonfinite")), "max_grad_pre": max((h.get("grad_pre", 0.0) for h in hist), default=0.0),
           "clipped_updates": sum(1 for h in hist if h.get("grad_pre", 0.0) > cfg["clip_norm"]), "warnings": sorted({str(w.message)[:160] for w in warn})}
    res = {"rid": rid, "spec": spec, "lambda_J": lam, "cfg": cfg, "attempt": attempt, "resumed_from_update": st["u"] if st else 0, "info": info,
           "numerical": num, "roots": {k: len(v) for k, v in sets.items()}, "roots_sha256": R.jsha(sets),
           "files": {f: R.sha(rd / f) for f in ("best.pt", "history.json", "predictions.json")} | ({"predictions.json": "0" * 64} if fault == "corrupt" else {}),
           "worker_cpu_s_final_attempt": R.cpu_self(),
           "env": {"python": sys.version.split()[0], "torch": torch.__version__, "threads": torch.get_num_threads(), "host_cpus": os.cpu_count()},
           "synthetic": synthetic}
    with open(rd / "RESULT.json", "x") as f:
        json.dump(res, f, indent=1, sort_keys=True, default=str)
    (rd / "state.pt").unlink(missing_ok=True)
    hb(info["updates_run"], "done")
    return R.EXIT["ok"]


def worker_pids(out) -> list:
    me, tag, res = os.getpid(), str(Path(out).resolve()).encode(), []
    for p in Path("/proc").glob("[0-9]*"):
        try:
            c = (p / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if int(p.name) != me and any(x.endswith(b"bxy_p14_run.py") for x in c) and b"worker" in c and tag in c:
            res.append(int(p.name))
    return res


# ------------------------------------------------------------------ scheduler (bxy_p12_run.Runner, P14 roster, no lambda phase)
class Runner14(R.Runner):
    def __init__(self, out=OUT, limits=H.LIMITS, reserve=H.RESERVE, synthetic=False, check_git=True, **kw):
        import contextlib
        with contextlib.ExitStack() as stack:                                   # the base constructor reads its module-level design hooks
            for name, fn in (("verify_auth", lambda o, c: verify_auth(o, c)), ("roster", roster),
                             ("design", lambda: {"roster": roster(out, synthetic), "budget": H.frozen()["budget"] if not synthetic else {}})):
                stack.enter_context(_swap(R, name, fn))
            super().__init__(out, limits, reserve, synthetic, check_git=check_git, **kw)

    def eligible(self, rid) -> bool:
        r = self.L["runs"][rid]
        return r["status"] == "PENDING" and R.failures(r) < R.MAX_ATTEMPTS

    def select_lambdas(self):
        return None

    def reconcile(self):
        with _swap(R, "worker_pids", worker_pids):
            super().reconcile()

    def start(self, rid):
        with _swap(R, "__file__", str(Path(__file__).resolve())):            # the worker entry is this file
            super().start(rid)


class _swap:
    def __init__(self, mod, name, val):
        self.mod, self.name, self.val = mod, name, val

    def __enter__(self):
        self.old = getattr(self.mod, self.name)
        setattr(self.mod, self.name, self.val)

    def __exit__(self, *a):
        setattr(self.mod, self.name, self.old)


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
        print(json.dumps(Runner14(a.out).run(), indent=1, default=str))
    else:
        sys.exit(worker(a.out, a.rid, a.attempt, a.parent, a.synthetic))
