"""P13: ledger (runs/p13/guards, contract caps, one guarded process per job), gates and the final manifest.
P10-P12 artifacts are read-only; every P13 output lives under runs/p13."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import config as cf

OUT = Path("runs/p13")
CAPS = {"audit": 4000.0, "dev": 10000.0, "training": 35000.0, "teacher": 65000.0, "p12_continuation": 9000.0,
        "execution": 22000.0, "analysis": 5000.0}
JOB = {"cpu_s": 4000.0, "wall_s": 12000.0}


def rd(p):
    return json.loads(Path(p).read_text())


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spent(cat=None) -> float:
    gs = [rd(p) for p in (OUT / "guards").glob("*.json")]
    return sum(g["cpu_s"] for g in gs if cat is None or g["category"] == cat)


def job(name, call, cpu, module="p13_factors", category="audit", wall=None) -> dict:
    """Guarded child process (process-tree CPU of this child only), charged to one P13 category; refuses past the cap."""
    import teacher
    (OUT / "guards").mkdir(parents=True, exist_ok=True)
    cpu = min(cpu, JOB["cpu_s"], CAPS[category] - spent(category))
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
    print(json.dumps({k: rec[k] for k in ("stop", "returncode", "cpu_s", "wall_s")} | {category: round(spent(category), 1)}))
    return rec


def gate(stage, **kw) -> None:
    cf.write_json(OUT / f"P13_{stage}_GATE.json", {"stage": f"P13-{stage}", **kw, "spend": {c: round(spent(c), 1) for c in CAPS}})
