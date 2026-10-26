"""P16 ledger (runs/p16/guards, contract caps, one guarded OS process per job), P16-0 non-mutating source / evidence audit, stage gates,
statistics and manifests. P10-P15 artifacts are read-only; every P16 output is a new file under runs/p16."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import config as cf

OUT = Path("runs/p16")
CAPS = {"audit": 3000.0, "motion": 9000.0, "shared": 10000.0, "b_dev": 10000.0, "d_dev": 10000.0, "data": 55000.0, "training": 20000.0,
        "execution": 38000.0, "final": 6000.0}
JOB = {"cpu_s": 8000.0, "wall_s": 80000.0}
HIST_PATHS = ("runs/p10", "runs/p10b", "runs/p10c", "runs/p11", "runs/p12", "runs/p13", "runs/p14", "runs/p15", "visualizations")
CORE = ("motion.py", "geometry.py", "skill.py", "planner.py", "data.py", "certificates.py", "sector_cert.py", "sector_check.py", "ordered.py",
        "unique_factor.py", "unique_factor_keyed.py", "abc_models.py", "abc7_models.py", "abc7_train.py", "abc8.py", "d_blockers.py",
        "learn_data.py", "p10c_train_eval.py", "p13_factors.py", "p13_pipeline.py", "p14_sweep_index.py", "p14_d_search.py", "p15_retarget.py",
        "p15_lookup.py", "p15_search.py", "p15_bench.py", "config.toml")


def rd(p):
    return json.loads(Path(p).read_text())


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spent(cat=None) -> float:
    return sum(g["cpu_s"] for g in (rd(p) for p in (OUT / "guards").glob("*.json")) if cat is None or g["category"] == cat)


def job(name, call, cpu, module="p16_eval", category="audit", wall=None, env=None) -> dict:
    """One guarded child per OS process, charged to one P16 category; refuses past the cap (fail closed)."""
    import os
    import teacher
    (OUT / "guards").mkdir(parents=True, exist_ok=True)
    cpu = min(cpu, JOB["cpu_s"], CAPS[category] - spent(category))
    if cpu < 5:
        raise SystemExit(f"{category} budget exhausted")
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        g = teacher.guard([sys.executable, "-c", f"import torch; torch.set_num_threads(1); import {module}; {module}.{call}"], cpu,
                          wall or JOB["wall_s"], OUT / f"heartbeat_{name}.txt", 15.0, 0.25, Path("."))
    finally:
        os.environ.clear()
        os.environ.update(old)
    n = 1
    while (OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json").exists():
        n += 1
    rec = {k: g[k] for k in ("stop", "returncode", "cpu_s", "wall_s", "overshoot_s", "stderr_tail")} | \
          {"cpu_cap_s": cpu, "call": f"{module}.{call}", "category": category, "env": env or {}, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    cf.write_json(OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json", rec)
    (OUT / f"heartbeat_{name}.txt").unlink(missing_ok=True)
    print(json.dumps({k: rec[k] for k in ("stop", "returncode", "cpu_s", "wall_s")} | {category: round(spent(category), 1)}))
    return rec


def gate(stage, **kw) -> None:
    cf.write_json(OUT / f"P16_{stage}_GATE.json", {"stage": f"P16-{stage}", **kw, "spend": {c: round(spent(c), 1) for c in CAPS}})


# ------------------------------------------------------------------ P16-0 audit
def _git(*a) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout


def historical_manifest() -> dict:
    """Immutable manifest: git blob ids of every tracked file under the historical paths + P10-P15 reports, plus working-tree state."""
    rows = {}
    for line in _git("ls-files", "-s", "--", *HIST_PATHS, "responses-phases").splitlines():
        meta, path = line.split("\t", 1)
        if path.startswith("responses-phases/") and not any(t in path for t in [f"{n:04d}_" for n in range(22, 82)] + ["DECISION"]):
            continue
        rows[path] = meta.split()[1]
    dirty = [ln for ln in _git("status", "--porcelain", "--", *HIST_PATHS, "responses-phases").splitlines() if not ln.startswith("??")]
    out = {"head": _git("rev-parse", "HEAD").strip(), "files": len(rows), "blobs": rows, "dirty_tracked": dirty,
           "core_sources": {p: sha(p) for p in CORE if Path(p).exists()},
           "checkpoints": {str(p): sha(p) for p in sorted(Path("runs/p13/models/ckpt").glob("*.pt"))}}
    out["hash"] = cf.stable_hash({k: v for k, v in out.items() if k != "hash"})
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "audit" / "HISTORICAL_MANIFEST.json", out)
    return out


def verify_historical() -> list:
    """Paths whose current blob differs from the P16-0 manifest (must stay empty for the whole phase)."""
    m = rd(OUT / "audit" / "HISTORICAL_MANIFEST.json")["blobs"]
    now = {}
    for line in _git("ls-files", "-s", "--", *HIST_PATHS, "responses-phases").splitlines():
        meta, path = line.split("\t", 1)
        now[path] = meta.split()[1]
    dirty = {ln[3:] for ln in _git("status", "--porcelain", "--", *HIST_PATHS, "responses-phases").splitlines() if not ln.startswith("??")}
    return sorted(p for p in m if now.get(p) != m[p] or p in dirty)


def label_audit() -> dict:
    """D label semantics in the frozen P13 datasets: which record types entered the blocker NLL (p10c_train_eval.d_items)."""
    import collections
    import os
    import torch
    os.environ["P10C_OUT"] = "runs/p13/models"
    out = {}
    for name in ("trainval", "test"):
        ds = torch.load(f"runs/p13/models/dataset_{name}.pt", weights_only=False)
        c = collections.Counter()
        for r in ds["roots"]:
            d = r.get("d") or {}
            used = d.get("mask") is not None and d.get("provenance") == "proof_grounded" and d.get("y0") == 0
            c[f"{r['audit'].get('split')}|{d.get('type')}|{d.get('provenance')}|mask_nll={used}"] += 1
        out[name] = dict(sorted(c.items()))
    return out


def privileged_audit() -> dict:
    """Static scan of runtime inputs: where candidate movers / catalogues come from in P15 and the frozen learners."""
    src = {p: Path(p).read_text() for p in ("p15_bench.py", "p15_search.py", "p14_d_search.py", "abc7_train.py", "p10c_train_eval.py")}
    hits = {p: [i + 1 for i, ln in enumerate(s.splitlines()) if "ORDERED_TEACHER" in ln or "root[\"items\"]" in ln or "dl[\"mask\"]" in ln]
            for p, s in src.items()}
    return {"lines": hits,
            "findings": {
                "p15_movers": "p15_bench.run_arm: movers = objects in ORDERED_TEACHER catalogue sequences (constructor-provided): CATALOGUE_RESTRICTED, "
                              "not scene-only. Kept as historical replay protocol; P16 uses p16_common.propose_movers (scene-only).",
                "p15_oracle": "Guide('oracle') reads the teacher blocker mask (declared non-deployable).",
                "b_catalogue": "Frozen B scores the constructor catalogue (root['items'] ORDERED_TEACHER / SCENE_TARGET_ONLY): candidate GENERATION is "
                               "privileged (mechanism-aware constructor) although labels are not read at inference. P16 B scores scene-only candidates.",
                "d_pool": "Frozen D's pool = root['parking'] (constructor lattice objects). P16 D pool = all movable non-target objects (cap) in the scene."}}


def determinism_audit() -> dict:
    import config as c
    cfg = c.load_config("config.toml")
    return {"planner_budget": "planner.plan: RRT-Connect stops at max_nodes (deterministic, seed = call_seed(planner2d.seed, key)) or "
                              f"max_wall_seconds={cfg['planner2d']['max_wall_seconds']} (safety; flagged wall_clock_cut)",
            "p15_cpu_cap": "p15_search.Physics.truncated: per-root process_time cap (150 s soft) -> search frontier depends on CPU speed / contention",
            "hash_seed": "Python str hashing is randomized per process (PYTHONHASHSEED); any order derived from set iteration is process-dependent "
                         "(tested empirically in P16-1)",
            "p15_prospective_replay": "PROSP 053: D re-run plan differed from the benchmark record (P15 0078 section 6); geometry steps equal, travel "
                                      "differed (different witness / online path)"}


def errata() -> dict:
    return {"P15_0080_lean_inference": "0080 section 5 called B-F3pm / B-F5spm / B-F5qpm 'post-hoc inference masks'. They are separately trained, "
                                       "parameter-matched checkpoints (p13_pipeline._arms: removed factor + widened scene head, PM widths 320/641/448). "
                                       "B-F5spm removes generic AND higher-order coupling (abc8 'B-structured'); it is not generic-only.",
            "P15_prospective_CI": "P15 prospective bootstrap CI [0, 0] reflects zero observed discordances; it is not an equivalence interval.",
            "D_no_clearing_set": "d_blockers.minimal_sets returns mask [0]*n for NO_CLEARING_SET_WITHIN_POOL; p10c_train_eval.d_items trained "
                                 "proof-grounded ones as an all-zero blocker mask (P13 train 2, validation 1). P16 D masks these records.",
            "P12_kappa": "P12 kappa endpoint = abs(mean_seed(kappa_hat) - kappa_true) (corrected in P13); always report the kappa==0 baseline."}


def audit() -> dict:
    m = historical_manifest()
    out = {"head": m["head"], "historical_files": m["files"], "historical_dirty_tracked": m["dirty_tracked"], "manifest_hash": m["hash"],
           "labels": label_audit(), "privileged": privileged_audit(), "determinism": determinism_audit(), "errata": errata(),
           "p15_spend": rd("runs/p15/P15_FINAL_MANIFEST.json")["spend_cpu_s"]}
    cf.write_json(OUT / "audit" / "P16_0_AUDIT.json", out)
    return out


def regression(name="regression") -> None:
    """Historical suite + P12-P16 tests + six replays (same harness as P13-P15)."""
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "countcalls.py").write_text(Path("runs/p8/audit/regression/countcalls.py").read_text())
    subprocess.run([sys.executable, "run.py", "g4c-lf-p4-regression", "--out", str(d), "--cpu", "2400", "--wall", "6000"], capture_output=True, text=True)


# ------------------------------------------------------------------ P16-1 determinism / transit experiments (development roots only)
DET_ROOTS = ["p13_2026180003", "p13_2026180009", "p13_2026180012", "p13_2026180024",      # P15 retrospective (historical, development use)
             "p13_2026200000", "p13_2026200002", "p13_2026200040", "p13_2026200053"]      # P15 prospective (now historical, development use)


def hist_roots() -> dict:
    """Plan roots of the P14 test pool and the P15 prospective cohort (scene + goal + fixed metadata are all P16 reads)."""
    import p13_pipeline as pp
    P = {}
    for d in sorted(pp.HOLD.glob("*_b*")):
        P |= rd(d / "plan.json")["roots"]
    return P | rd("runs/p15/prospective/plan.json")["roots"]


def uniform_order(cells, q, moved, cands):
    return cands


def det_run(tag, keys=None, transit="planned", lookup=True, n_max=3, per_obj=1, node_cap=400) -> None:
    import numpy as np
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    P, idx = hist_roots(), pl.index_v2()[0]
    f = OUT / "shared" / f"DET_{tag}.json"
    res = rd(f) if f.exists() else {}
    for k in keys or DET_ROOTS:
        if k in res:
            continue
        c0, w0 = time.process_time(), time.time()
        task = pc.task_from_root(P[k], k)
        phys = pm.DetPhysics(task, idx, transit=transit, use_lookup=lookup)
        cells0 = {o.id: o.cell for o in phys.s0.objects}
        movers, omitted = pc.propose_movers(task, cells0)
        out = pc.search(phys, uniform_order, movers, pc.slot_fn(phys, idx), cells0, phys.s0.robot.q_rad, n_max, per_obj, node_cap)
        rep = pm.replay(phys, out["plan"]) if out["found"] else None
        res[k] = {"found": out["found"], "claim": out["claim"], "replay": rep, "movers": movers, "omitted_movers": omitted,
                  "plan": None if not out["found"] else {"moves": out["plan"]["moves"], "travel": round(out["plan"]["travel"], 9),
                                                         "steps": [(s["object"], s["dest"], s["via"], s.get("transit")) for s in out["plan"]["steps"]],
                                                         "traj": pm.traj_hash(out["plan"]["records"])},
                  "edges": out["log"]["edges"], "goals": out["log"]["goals"], "nodes": out["log"]["nodes"], "node_cap_hit": out["log"]["node_cap_hit"],
                  "used": phys.used, "stats": phys.stats, "flags": out["flags"], "cpu_s": time.process_time() - c0, "wall_s": time.time() - w0,
                  "hashseed": __import__("os").environ.get("PYTHONHASHSEED")}
        (OUT / "shared").mkdir(parents=True, exist_ok=True)
        cf.write_json(f, res)


# ------------------------------------------------------------------ P16-2 data: splits, scene-only labels, physics-only tags
DATA = OUT / "data"
SEED0 = {"dev": 2026210000, "train": 2026220000, "calib": 2026230000, "test": 2026240000}
LABEL_BUDGET = {"motion_checks": 600, "online_moves": 12, "goal_plans": 24, "transit_plans": 12}
DEV_FAMS = ("NAT", "PN_SIMP", "PN_GIMP", "PC_SG", "PR_SIDES", "ORD_CHAIN", "OMIT_OPT", "TRI_OR", "TRI_CTRL", "DENSE")


def build_split(name, counts) -> None:
    """counts {family: n}; seeds SEED0[split] + 1000 * family index + j (disjoint per split). Plans frozen by p10b_dataset.build_plan."""
    import p16_common as pc
    pd = pc.register()
    split = name.split("_")[0]
    fams = sorted(counts)
    specs = [{"family": f, "seed": SEED0[split] + 1000 * i + j, "index": len(fams) * j + i, "wave": 0, "batch": 1, "split": "blind" if split == "test" else "dev"}
             for i, f in enumerate(fams) for j in range(counts[f])]
    if not (DATA / name / "plan.json").exists():
        pd.build_plan(DATA / name, specs, max_attempts=600, root_cpu=300.0)


def label_split(name, keys=None, budget=None, part="") -> None:
    """Scene-only catalogue + deterministic physical labels per root (sealed file for the test split)."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    plan = rd(DATA / name / "plan.json")
    idx = pl.index_v2()[0]
    f = DATA / name / (("sealed_labels" if name.startswith("test") else "labels") + (f"_{part}" if part else "") + ".json")
    res = rd(f) if f.exists() else {}
    for k in keys or sorted(plan["roots"]):
        if k in res:
            continue
        c0 = time.process_time()
        task = pc.task_from_root(plan["roots"][k], k)
        phys = pm.DetPhysics(task, idx, budget=budget or LABEL_BUDGET)
        cat = pc.catalogue(task, phys, idx)
        lab = pc.label(task, phys, cat)
        res[k] = {"family": plan["roots"][k]["family"], "catalogue": {x: cat[x] for x in ("pool", "parking", "movers")}, **lab,
                  "cpu_s": time.process_time() - c0}
        cf.write_json(f, res)


def tag_split(name, keys=None, n_max=4, per_obj=2, node_cap=500, part="") -> None:
    """Physics-only mechanism tags from the scene-only expanded-domain search (uniform order): plan length, repeat move, freed-source
    reuse, and slot conflict (a VERIFIED first move whose subtree contains no plan while another first move leads to one is not observable
    cheaply; recorded instead: number of distinct VERIFIED first moves). Never conditions on any model."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    plan = rd(DATA / name / "plan.json")
    idx = pl.index_v2()[0]
    f = DATA / name / (f"tags_{part}.json" if part else "tags.json")
    res = rd(f) if f.exists() else {}
    for k in keys or sorted(plan["roots"]):
        if k in res:
            continue
        c0 = time.process_time()
        task = pc.task_from_root(plan["roots"][k], k)
        phys = pm.DetPhysics(task, idx)
        cells0 = {o.id: o.cell for o in phys.s0.objects}
        movers, omitted = pc.propose_movers(task, cells0)
        out = pc.search(phys, uniform_order, movers, pc.slot_fn(phys, idx), cells0, phys.s0.robot.q_rad, n_max, per_obj, node_cap)
        steps = out["plan"]["steps"] if out["found"] else []
        objs = [s["object"] for s in steps]
        res[k] = {"family": plan["roots"][k]["family"], "found": out["found"], "claim": out["claim"], "moves": len(steps),
                  "steps": [(s["object"], s["dest"], s["via"]) for s in steps], "repeat_move": len(objs) != len(set(objs)),
                  "freed_source_reuse": any(s["dest"] == cells0.get(p["object"]) for i, s in enumerate(steps) for p in steps[:i]),
                  "first_moves_verified": sum(1 for (o, d) in [(o, d) for o in movers for d in pc.slot_fn(phys, idx)(cells0, o)]
                                             if any(x[0] == pm.V for x in phys.memo.get(("edge", __import__("p15_search").state_key(cells0, phys.s0.robot.q_rad, ()), o, d), []))),
                  "movers": movers, "omitted": omitted, "used": phys.used, "nodes": out["log"]["nodes"], "edges": out["log"]["edges"],
                  "goals": out["log"]["goals"], "replay": pm.replay(phys, out["plan"]) if out["found"] else None, "cpu_s": time.process_time() - c0}
        cf.write_json(f, res)


def merged(name, kind) -> dict:
    """Union of per-worker files (labels / sealed_labels / tags)."""
    out = {}
    for f in sorted((DATA / name).glob(f"{kind}*.json")):
        out |= rd(f)
    return out


def launch(tag, call, cpu, category, env=None) -> None:
    """Fire-and-forget guarded job in its own session (no shell pattern matching involved)."""
    code = f"import p16_eval as p; p.job({tag!r}, {call!r}, {cpu}, category={category!r}, env={env!r})"
    subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
