"""Runner: one committed decision per (root, method, config, seed), benchmark-format predictions + per-root search stats.

    python -m baselines.analytical.run run --domain 2d --public PUB.jsonl --out DIR [--methods em4m,mosegman,msmcts] [--config paper]
           [--seeds 0] [--budget 300] [--part i/k] [--roots a,b] [--limit N]
    python -m baselines.analytical.run cut --out DIR --budget 60        derive the 60 s predictions from the 300 s runs (before sealing)
    python -m baselines.analytical.run merge --domain 2d --public PUB.jsonl --out MERGED PART_DIR...   one file per run, complete

Use python3 for 2D and a MuJoCo-3.16 python (e.g. ~/abf_v3_laptop/env3d/bin/python) for 3D; physics code needs numpy only (no torch,
no scipy).  Environment: ABF_ROOT, FIN3D_CODE, FIN3D_SRC (see eval.sh).  Outputs (all under DIR, append-only, one fsync'd line per
root, resumable):  DIR/<method>_<config>_s<seed>_b<budget>/predictions_<dom>.jsonl  and  .../stats_<dom>.jsonl,  DIR/MANIFEST_<dom>.json.
Inputs are PUBLIC rows only; raw records reach the physics scrubbed of every private key (envs.scrub)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

from . import envs
from .common import Decision
from .contract import legality, prediction, public_row
from .em4m import EM4M
from .mosegman import MOSeGMan
from .msmcts import MSMCTS
from .phys import RealPhys

H = Path(__file__).resolve().parent
METHODS = {"em4m": EM4M, "mosegman": MOSeGMan, "msmcts": MSMCTS}
GRID = json.loads((H / "config/grid.json").read_text())


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def append(p, obj):
    with open(p, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def params(method, config):
    if config == "default":
        return dict(GRID["default"][method])
    e = next(g for g in GRID["grid"][method] if g["name"] == config)
    return {k: v for k, v in e.items() if k != "name"}


def solve_one(E, row, method, cfg, seed, budget, path=None) -> tuple[dict, dict]:
    """-> (prediction line, stats line) for one root.  The env is reset to a cold, scrubbed root first."""
    B = GRID["budget_schedule"]
    envs.load_root(E, row, path)
    ph = RealPhys(E, row, n_ref=B["n_ref"], n_ref_try=B["n_ref_try"], ref_cap_s=B["ref_cap_s"], budget_s=budget,
                  wall_s=B["wall_mult"] * budget, call_cap_s=B["call_cap_s"])
    try:
        d = METHODS[method](ph, seed, **params(method, cfg)).run()
    except Exception as e:  # noqa: BLE001  (recorded; the committed decision is ABSTAIN, termination ERROR)
        import traceback
        d = Decision("ABSTAIN", [], f"{type(e).__name__}: {str(e)[:300]}", "ERROR", {"trace": traceback.format_exc()[-1500:],
                                                                                    "phys": ph.stats()})
    cpu = d.stats["phys"]["cpu_s"]
    if d.kind == "REPAIR" and legality(row["inputs"], row["domain"], d.prefix) is not None:   # never expected (phys rejects illegal)
        d = Decision("ABSTAIN", [], f"illegal plan {d.prefix} withheld", "ERROR", d.stats)
    pred = prediction(row, d.kind, d.prefix, method=f"{method}:{cfg}", seed=seed, budget_cpu_s=budget, termination=d.termination,
                      decided_cpu_s=cpu, timing_s={"total": cpu})
    stats = {"root_id": row["root_id"], "domain": row["domain"], "method": method, "config": cfg, "seed": seed, "budget_cpu_s": budget,
             "decision": d.kind, "prefix": d.prefix, "reason": d.reason, "termination": d.termination, **d.stats,
             "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
    return pred, stats


def manifest(out, dom, args):
    git = lambda *a: subprocess.run(["git", "-C", str(H), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    deps = {str(p): sha(p) for p in (envs.DISCO / "env.py", envs.DISCO / "data.py", envs.NOR / "homotopy.py")}
    m = {"version": GRID["version"], "domain": dom, "argv": sys.argv, "args": vars(args), "commit": git("rev-parse", "HEAD"),
         "dirty": bool(git("status", "--porcelain", "--", ".")), "dependencies_sha256": deps,
         "dependency_commits": {w: subprocess.run(["git", "-C", str(envs.WT / w), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                                for w in ("disco-grid-stage2", "baseline-sorc-grid")},
         "python": sys.version, "env": {k: os.environ.get(k) for k in ("ABF_ROOT", "FIN3D_CODE", "FIN3D_SRC", "OMP_NUM_THREADS")},
         "grid_sha256": sha(H / "config/grid.json"), "started_utc": time.strftime("%FT%TZ", time.gmtime())}
    p = Path(out) / f"MANIFEST_{dom}{'_part' + args.part.replace('/', 'of') if args.part else ''}.json"
    p.write_text(json.dumps(m, indent=1))


def run(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [public_row(r) for r in jl(args.public) if r.get("domain", args.domain) == args.domain]
    rows = [r for r in rows if r["domain"] == args.domain]
    if args.roots:
        keep = set(args.roots.split(","))
        rows = [r for r in rows if r["root_id"] in keep]
    if args.part:
        i, k = map(int, args.part.split("/"))
        rows = [r for r in rows if int(hashlib.sha256(r["root_id"].encode()).hexdigest(), 16) % k == i]
    rows = rows[:args.limit] if args.limit else rows
    paths = json.loads(Path(args.raw_paths).read_text()) if args.raw_paths else {}
    manifest(out, args.domain, args)
    E = envs.make_env(args.domain, str(Path(args.witness_dir or out / f"witnesses_{args.domain}")))
    E.backend.boot()                                                   # boot cost is never charged to a run
    jobs = [(m, args.config, int(s)) for m in args.methods.split(",") for s in str(args.seeds).split(",")]
    for r in rows:
        for m, cfg, seed in jobs:
            d = out / f"{m}_{cfg}_s{seed}_b{int(args.budget)}"
            d.mkdir(exist_ok=True)
            pp, sp = d / f"predictions_{args.domain}.jsonl", d / f"stats_{args.domain}.jsonl"
            if r["root_id"] in {x["root_id"] for x in jl(pp)}:
                continue
            pred, st = solve_one(E, r, m, cfg, seed, float(args.budget), paths.get(r["root_id"]))
            append(sp, st)
            append(pp, pred)                                           # prediction last: a root counts as done only when complete
            print(f"{time.strftime('%H:%M:%S')} {args.domain} {m} {r['root_id']} {pred['decision']} {st['termination']} "
                  f"cpu={st['phys']['cpu_s']} calls={st['phys']['physical_calls']}", flush=True)


def cut(args):
    """Budget cut: a decision taken after `budget` CPU-s becomes ABSTAIN (TIMEOUT); written next to the source run dirs."""
    for d in sorted(Path(args.out).glob("*_b*")):
        if not d.is_dir() or d.name.endswith(f"_b{int(args.budget)}"):
            continue
        src = int(d.name.rsplit("_b", 1)[1])
        if src <= args.budget:
            continue
        nd = d.with_name(d.name.rsplit("_b", 1)[0] + f"_b{int(args.budget)}_cut{src}")
        nd.mkdir(exist_ok=True)
        for p in d.glob("predictions_*.jsonl"):
            with open(nd / p.name, "w") as f:
                for x in jl(p):
                    if x["decision"] != "ABSTAIN" and x["decided_cpu_s"] > args.budget:
                        x = {**x, "decision": "ABSTAIN", "moves": [], "termination": "TIMEOUT_AT_CUT"}
                    f.write(json.dumps({**x, "budget_cpu_s": args.budget, "cut_from_s": src}, sort_keys=True) + "\n")
        print(nd)


def merge(args):
    """Concatenate the per-part prediction / stats files of every run dir into OUT, requiring exactly one prediction per public root."""
    pub = {r["root_id"] for r in jl(args.public) if r["domain"] == args.domain}
    names = sorted({d.name for p in args.parts for d in Path(p).glob("*_b*") if d.is_dir()})
    for name in names:
        preds, stats = {}, {}
        for p in args.parts:
            for x in jl(Path(p) / name / f"predictions_{args.domain}.jsonl"):
                assert x["root_id"] not in preds, f"duplicate prediction {name} {x['root_id']}"
                preds[x["root_id"]] = x
            stats.update({x["root_id"]: x for x in jl(Path(p) / name / f"stats_{args.domain}.jsonl")})
        missing = sorted(pub - set(preds))
        od = Path(args.out) / name
        od.mkdir(parents=True, exist_ok=True)
        for fn, rows in ((f"predictions_{args.domain}.jsonl", preds), (f"stats_{args.domain}.jsonl", stats)):
            with open(od / fn, "w") as f:
                for rid in sorted(rows):
                    f.write(json.dumps(rows[rid], sort_keys=True) + "\n")
        print(json.dumps({"run": name, "n": len(preds), "missing": len(missing), "extra": len(set(preds) - pub)}))
        if missing and not args.allow_missing:
            raise SystemExit(f"{name}: {len(missing)} public roots without a prediction (e.g. {missing[:3]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("run")
    a.add_argument("--domain", required=True, choices=("2d", "3d"))
    a.add_argument("--public", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--methods", default="em4m,mosegman,msmcts")
    a.add_argument("--config", default="paper")
    a.add_argument("--seeds", default="0")
    a.add_argument("--budget", type=float, default=GRID["budget_schedule"]["primary_cpu_budget_s"])
    a.add_argument("--part")
    a.add_argument("--roots")
    a.add_argument("--limit", type=int)
    a.add_argument("--raw-paths", help="optional JSON {root_id: raw root path} (default: DISCO data.raw_root_path)")
    a.add_argument("--witness-dir")
    a = sp.add_parser("cut")
    a.add_argument("--out", required=True)
    a.add_argument("--budget", type=float, required=True)
    a = sp.add_parser("merge")
    a.add_argument("--domain", required=True, choices=("2d", "3d"))
    a.add_argument("--public", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--allow-missing", action="store_true")
    a.add_argument("parts", nargs="+")
    A = ap.parse_args()
    {"run": run, "cut": cut, "merge": merge}[A.cmd](A)
