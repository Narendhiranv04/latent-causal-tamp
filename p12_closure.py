"""P12: ledger (runs/p12/guards, contract caps, one process per job), read-only audit + prereg draft + power (P12-0), prospective
F3 / F5 statistics (P12-4), photometric controls and D attribution (P12-6). P10 / P11 artifacts are read-only."""
from __future__ import annotations

import collections
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

import config as cf

OUT = Path("runs/p12")
CAPS = {"audit": 4000.0, "dev": 5000.0, "teacher": 40000.0, "execution": 12000.0, "secondary": 5000.0, "regression": 2000.0}
JOB = {"cpu_s": 3000.0, "wall_s": 9000.0}
FROZEN_ARMS = ("K-B", "K-C", "A", "SF", "B-F3", "B-F5s", "B-F5q", "B-F2", "B-F4", "B-V0", "B-U")


def _rd(p):
    return json.loads(Path(p).read_text())


def spent(cat=None) -> tuple:
    gs = [_rd(p) for p in (OUT / "guards").glob("*.json")]
    gs = [g for g in gs if cat is None or g["category"] == cat]
    return sum(g["cpu_s"] for g in gs), sum(g["wall_s"] for g in gs)


def job(name, call, cpu, module="p12_closure", category="audit", wall=None) -> dict:
    """Guarded job (process-tree CPU of THIS child only), charged to one P12 category; refuses past the category cap."""
    import teacher
    (OUT / "guards").mkdir(parents=True, exist_ok=True)
    left = CAPS[category] - spent(category)[0]
    cpu = min(cpu, JOB["cpu_s"], left)
    if cpu < 5:
        raise SystemExit(f"{category} budget exhausted")
    g = teacher.guard([sys.executable, "-c", f"import torch; torch.set_num_threads(1); import {module}; {module}.{call}"], cpu,
                      wall or JOB["wall_s"], OUT / f"heartbeat_{name}.txt", 15.0, 0.25, Path("."))
    n = 1
    while (OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json").exists():
        n += 1
    rec = {k: g[k] for k in ("stop", "returncode", "cpu_s", "wall_s", "overshoot_s", "stderr_tail")} | \
          {"cpu_cap_s": cpu, "call": f"{module}.{call}", "category": category, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    cf.write_json(OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json", rec)
    (OUT / f"heartbeat_{name}.txt").unlink(missing_ok=True)
    print(json.dumps({k: rec[k] for k in ("stop", "returncode", "cpu_s", "wall_s")} | {category: round(spent(category)[0], 1)}))
    return rec


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ P12-0: audit + power
def audit() -> None:
    import subprocess
    sh = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    snap = _rd("runs/p10d/predictions.json")
    A = {"head": sh("rev-parse", "HEAD"), "origin": sh("rev-parse", "origin/main"), "tracked_changes": sh("status", "--short", "--untracked-files=no").splitlines(),
         "snapshot_hash_ok": cf.stable_hash({k: v for k, v in snap.items() if k != "hash"}) == snap["hash"], "checkpoints": {}}
    for arm in FROZEN_ARMS:
        for s in (0, 1, 2):
            n = f"F-{arm}-s{s}"
            x = _rd(f"runs/p10c/runs/{n}.json")
            a = snap["arms"][n]
            A["checkpoints"][n] = {"sha_ok": sha(f"runs/p10c/ckpt/{n}.pt").removeprefix("sha256:") == x["checkpoint_sha256"].removeprefix("sha256:"),
                                   "snapshot_sha_match": a["checkpoint_sha256"] == x["checkpoint_sha256"], "tau": a["tau"], "threshold": a["threshold"],
                                   "params": x["params"], "regime": x["regime"], "arm": x["arm"]}
    A["d_frozen"] = {k: snap["baselines"][k] for k in ("D_lambda_B", "D_threshold", "D-pairless_lambda_B", "D-pairless_threshold")}
    A["p11_gates"] = {"final": _rd("runs/p11/P11_FINAL_MANIFEST.json")["gates"]}
    A["all_checkpoints_ok"] = all(v["sha_ok"] and v["snapshot_sha_match"] for v in A["checkpoints"].values())
    (OUT / "p12_0").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "p12_0" / "AUDIT.json", A)


def power(sims=4000, seed=0) -> None:
    """Sensitivity of the two-sided exact sign test (Holm over 2: first test at 0.025) from the DISCLOSED P11 nine-root H1 deltas
    (POST-HOC source, used only to plan N): bootstrap per-root deltas, plus a pessimistic shrunken-effect scenario."""
    from scipy.stats import binomtest
    be = _rd("runs/p10d/BLIND_EVAL.json")["per_root"]["H1"]
    rng, out = np.random.default_rng(seed), {}
    for arm in ("B-F3", "B-F5s"):
        d = np.array([be["K-B"][k] - be[arm][k] for k in sorted(set(be["K-B"]) & set(be[arm]))])   # positive = full B better
        for label, pool in (("observed", d), ("shrunk_50pct_with_25pct_reversals", np.concatenate([d * 0.5, -d[: max(1, len(d) // 4)] * 0.5]))):
            for n in (16, 24, 32, 40, 48):
                hits = 0
                for _ in range(sims):
                    x = rng.choice(pool, n)
                    k, m = int((x > 0).sum()), int((x != 0).sum())
                    hits += m > 0 and binomtest(k, m).pvalue < 0.025
                out[f"{arm}|{label}|N={n}"] = hits / sims
        out[f"{arm}|observed_deltas"] = [float(v) for v in d]
    cf.write_json(OUT / "p12_0" / "POWER.json", out)
