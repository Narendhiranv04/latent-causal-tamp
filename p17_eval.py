"""P17 ledger and stage orchestration. No aggregate CPU ceiling (user authorisation, contract 0045 section 8): every job still runs
in its own guarded OS process with a per-job CPU / wall watchdog, a concurrency limit, a disk / memory check and a resumable
per-root checkpoint; every job (completed, censored, killed) is written to runs/p17/guards. P10-P16 artifacts are read-only."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import config as cf

OUT = Path("runs/p17")
HIST = ("runs/p10", "runs/p10b", "runs/p10c", "runs/p11", "runs/p12", "runs/p13", "runs/p14", "runs/p15", "runs/p16", "visualizations")
MAX_JOBS, MIN_FREE_GB, MIN_AVAIL_GB = 18, 6.0, 1.5


def rd(p):
    return json.loads(Path(p).read_text())


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _git(*a) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True).stdout


def spent(cat=None) -> float:
    return sum(g["cpu_s"] for g in (rd(p) for p in (OUT / "guards").glob("*.json")) if cat is None or g["category"] == cat)


def resources() -> dict:
    free = shutil.disk_usage(".").free / 2 ** 30
    avail = next(int(ln.split()[1]) for ln in Path("/proc/meminfo").read_text().splitlines() if ln.startswith("MemAvailable")) / 2 ** 20
    running = len(list((OUT / "running").glob("*.json"))) if (OUT / "running").exists() else 0
    return {"disk_free_gb": round(free, 2), "mem_avail_gb": round(avail, 2), "running_jobs": running}


def job(name, call, cpu, module="p17_eval", category="misc", wall=None, env=None) -> dict:
    """One guarded child process; cpu = per-job watchdog (safety), not an aggregate budget. Refuses to start when disk / memory are low."""
    import teacher
    r = resources()
    if r["disk_free_gb"] < MIN_FREE_GB or r["mem_avail_gb"] < MIN_AVAIL_GB:
        raise SystemExit(f"resource guard: {r}")
    for d in ("guards", "running"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    run = OUT / "running" / f"{name}.json"
    cf.write_json(run, {"pid": os.getpid(), "call": call, "start": time.time()})
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        g = teacher.guard([sys.executable, "-c", f"import torch; torch.set_num_threads(1); import {module}; {module}.{call}"], cpu,
                          wall or 20 * cpu, OUT / f"heartbeat_{name}.txt", 15.0, 0.25, Path("."))
    finally:
        os.environ.clear()
        os.environ.update(old)
        run.unlink(missing_ok=True)
    n = 1
    while (OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json").exists():
        n += 1
    rec = {k: g[k] for k in ("stop", "returncode", "cpu_s", "wall_s", "overshoot_s", "stderr_tail")} | \
          {"cpu_watchdog_s": cpu, "call": f"{module}.{call}", "category": category, "env": env or {}, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "resources_at_start": r}
    cf.write_json(OUT / "guards" / f"{name}{'' if n == 1 else f'_attempt{n}'}.json", rec)
    (OUT / f"heartbeat_{name}.txt").unlink(missing_ok=True)
    return rec


def launch(tag, call, cpu, category, module="p17_eval", env=None) -> None:
    if resources()["running_jobs"] >= MAX_JOBS:
        raise SystemExit("concurrency limit")
    code = f"import p17_eval as p; p.job({tag!r}, {call!r}, {cpu}, module={module!r}, category={category!r}, env={env!r})"
    subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(0.5)


def gate(stage, **kw) -> None:
    cf.write_json(OUT / f"P17_{stage}_GATE.json", {"stage": f"P17-{stage}", **kw, "cpu_by_category": _by_cat(), "resources": resources()})


def _by_cat() -> dict:
    out = {}
    for p in (OUT / "guards").glob("*.json"):
        g = rd(p)
        out[g["category"]] = round(out.get(g["category"], 0.0) + g["cpu_s"], 1)
    return out


# ------------------------------------------------------------------ P17-0 audit
def historical_manifest() -> dict:
    """Git blob ids of every tracked file under runs/p10..p16, visualizations, reports 0022-0089 and decision documents."""
    rows = {}
    for line in _git("ls-files", "-s", "--", *HIST, "responses-phases").splitlines():
        meta, path = line.split("\t", 1)
        if path.startswith("visualizations/p17") or path.startswith("runs/p17"):
            continue
        if path.startswith("responses-phases/") and not (any(f"{n:04d}_" in path for n in range(22, 90)) or "DECISION" in path or "P16_3D" in path):
            continue
        rows[path] = meta.split()[1]
    out = {"head": _git("rev-parse", "HEAD").strip(), "files": len(rows), "blobs": rows,
           "dirty_tracked": [ln for ln in _git("status", "--porcelain", "--", *HIST, "responses-phases").splitlines() if not ln.startswith("??")]}
    out["hash"] = cf.stable_hash({k: v for k, v in out.items() if k != "hash"})
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "audit" / "HISTORICAL_MANIFEST.json", out)
    return out


def verify_historical() -> list:
    m = rd(OUT / "audit" / "HISTORICAL_MANIFEST.json")["blobs"]
    now = {}
    for line in _git("ls-files", "-s", "--", *HIST, "responses-phases").splitlines():
        meta, path = line.split("\t", 1)
        now[path] = meta.split()[1]
    dirty = {ln[3:] for ln in _git("status", "--porcelain", "--", *HIST, "responses-phases").splitlines() if not ln.startswith("??")}
    return sorted(p for p in m if now.get(p) != m[p] or p in dirty)


def regression(name="regression") -> None:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "countcalls.py").write_text(Path("runs/p8/audit/regression/countcalls.py").read_text())
    subprocess.run([sys.executable, "run.py", "g4c-lf-p4-regression", "--out", str(d), "--cpu", "3000", "--wall", "8000"], capture_output=True, text=True)


# ------------------------------------------------------------------ P17-1 greedy vs existential rescan (development roots only)
P17_LABEL_BUDGET = {"motion_checks": 800, "online_moves": 16, "goal_plans": 32, "transit_plans": 16}   # P17_LABEL_BUDGET_V1 (per root)


def rescan(items, part) -> None:
    """items: [(split, root, sig, p16_status, p16_failed_step)]; per root one deterministic provider; existential verification + replay."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_verify as pv
    idx = pl.index_v2()[0]
    f = OUT / "shared" / f"RESCAN_{part}.json"
    res = rd(f) if f.exists() else {}
    by = {}
    for n, k, sig, st, fs in items:
        by.setdefault((n, k), []).append((sig, st, fs))
    for (n, k), seqs in sorted(by.items()):
        if f"{n}|{k}" in res:
            continue
        plan = rd(f"runs/p16/data/{n}/plan.json")
        task = pc.task_from_root(plan["roots"][k], k)
        phys = pm.DetPhysics(task, idx, budget=P17_LABEL_BUDGET)
        out = {}
        for sig, st, fs in seqs:
            seq = [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")]
            c0 = time.process_time()
            r = pv.verify_existential(phys, seq)
            rep = pm.replay(phys, r["plan"]) if r["plan"] else None
            out[sig] = {"p16": [st, fs], "p17": r["status"], "travel": r["plan"]["travel"] if r["plan"] else None,
                        "steps": [(s["object"], s["dest"], s.get("via"), s.get("mode"), s.get("transit")) for s in r["plan"]["steps"]] if r["plan"] else None,
                        "replay": rep, "branches_verified": r.get("branches_verified"), "certificate": r.get("certificate"), "fails": r.get("fails"),
                        "travel_minimal": r.get("travel_minimal_over_alternatives"), "cpu_s": time.process_time() - c0}
        res[f"{n}|{k}"] = {"sequences": out, "used": phys.used}
        (OUT / "shared").mkdir(parents=True, exist_ok=True)
        cf.write_json(f, res)


def greedy_vs_existential(items, part) -> None:
    """Controlled comparison on one fresh provider per (root, sequence), identical budget: greedy P16 verifier first, then existential."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_verify as pv
    idx = pl.index_v2()[0]
    f = OUT / "shared" / f"GREEDY_VS_EXIST_{part}.json"
    res = rd(f) if f.exists() else {}
    for n, k, sig in items:
        if f"{n}|{k}|{sig}" in res:
            continue
        plan = rd(f"runs/p16/data/{n}/plan.json")
        task = pc.task_from_root(plan["roots"][k], k)
        seq = [(a.split(">")[0], int(a.split(">")[1])) for a in sig.split(".")]
        phys = pm.DetPhysics(task, idx, budget=P17_LABEL_BUDGET)
        g = pv.verify_sequence_greedy_P16(phys, seq)
        e = pv.verify_existential(phys, seq)
        rep = pm.replay(phys, e["plan"]) if e["plan"] else None
        res[f"{n}|{k}|{sig}"] = {"greedy": g["status"], "greedy_failed_step": g["failed_step"],
                                 "greedy_steps": [(x["object"], x["dest"], x.get("via"), x.get("mode"), x.get("transit")) for x in g["plan"]["steps"]] if g["plan"] else None,
                                 "existential": e["status"], "existential_steps": [(x["object"], x["dest"], x.get("via"), x.get("mode"), x.get("transit")) for x in e["plan"]["steps"]] if e["plan"] else None,
                                 "existential_travel": e["plan"]["travel"] if e["plan"] else None, "branches_verified": e.get("branches_verified"),
                                 "replay": rep, "fails": e.get("fails")}
        (OUT / "shared").mkdir(parents=True, exist_ok=True)
        cf.write_json(f, res)


def mech_screen(seed0, n, want, gen, part) -> None:
    """Checkpointed per scene (resumable): each scene's outcome is appended before the next one starts."""
    import p17_mech as m
    f = OUT / "mechanisms" / "screen" / f"{want}_{gen}_{part}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    acc = rd(f) if f.exists() else {"stats": {}, "kept": [], "done": 0}
    for i in range(acc["done"], n):
        r = m.screen2(seed0 * 1000 + i, 1, want, 4, gen)
        for k, v in r["stats"].items():
            if isinstance(v, list):
                acc["stats"].setdefault(k, [])
                acc["stats"][k] += v
            elif isinstance(v, dict):
                acc["stats"].setdefault(k, {})
                for kk, vv in v.items():
                    acc["stats"][k][kk] = acc["stats"][k].get(kk, 0) + vv
            else:
                acc["stats"][k] = acc["stats"].get(k, 0) + v
        acc["kept"] += r["kept"]
        acc["done"] = i + 1
        cf.write_json(f, acc)


def m5_mine(items, part) -> None:
    """items: [(split, key)] from P16 dev / train / val / calib plans (development scenes)."""
    import p17_mech as m
    f = OUT / "mechanisms" / f"M5_{part}.json"
    res = rd(f) if f.exists() else {}
    for n, k in items:
        if f"{n}|{k}" in res:
            continue
        c0 = time.process_time()
        root = rd(f"runs/p16/data/{n}/plan.json")["roots"][k]
        out = m.mine_m5(root, k)
        res[f"{n}|{k}"] = out | {"cpu_s": time.process_time() - c0}
        (OUT / "mechanisms").mkdir(parents=True, exist_ok=True)
        cf.write_json(f, res)


# ------------------------------------------------------------------ P17 labelling (B: existential ordered repairs; D: parking + multi-destination lattices)
DATA = OUT / "data"


def _plan(split):
    p = DATA / split / "plan.json"
    return rd(p) if p.exists() else rd(f"runs/p16/data/{split}/plan.json")


def label_roots(split, keys, part, sealed=False, temp=True) -> None:
    """Per root (checkpointed): B catalogue + existential labels (per-sequence budgets, shared exact cache), D lattices under both
    protocols, temporary-target lattices at the original state. Output under runs/p17/data/<split>/ (sealed_* for test splits)."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_b as pb
    import p17_d as pd
    import p17_domain as dm
    idx, plan = pl.index_v2()[0], _plan(split)
    f = DATA / split / (("sealed_labels" if sealed else "labels") + f"_{part}.json")
    res = rd(f) if f.exists() else {}
    for k in keys:
        if k in res or any(k in rd(g) for g in (DATA / split).glob(("sealed_labels" if sealed else "labels") + "_*.json") if g != f):
            continue
        c0 = time.process_time()
        task = pc.task_from_root(plan["roots"][k], k)
        cache = {}
        fac = lambda c: pm.DetPhysics(task, idx, budget=pb.SEQ_BUDGET, cache=c)  # noqa: E731
        phys = fac(cache)
        cat = pb.catalogue(task, phys, idx)
        lab = pb.label(task, fac, cat, idx)
        lphys = pm.DetPhysics(task, idx, budget=P17_LABEL_BUDGET, cache=cache)
        cells0 = {o.id: o.cell for o in lphys.s0.objects}
        sl = dm.slot_fn(lphys, idx, width=4, origin=cells0)
        md = pd.multi_dest_lattice(lphys, cat["pool"], sl, k=2)
        nat = plan["roots"][k].get("family") == "NAT"
        tl = pd.temp_lattice(lphys, cells0, np.asarray(lphys.s0.robot.q_rad, float), cat["pool"], cat["parking"]) if temp and not nat and len(cat["pool"]) >= 2 else []
        res[k] = {"family": plan["roots"][k].get("family"), "catalogue": {x: cat[x] for x in ("pool", "parking", "movers", "edits", "sequences", "generated", "kept", "omitted")},
                  **lab, "multi_dest": {"statuses": {"+".join(S) or "-": v for S, v in md["statuses"].items()}, "k": md["k"]},
                  "temp_lattices": tl, "protocol": {"labels": "P17_EXISTENTIAL_V1", "seq_budget": pb.SEQ_BUDGET, "domain": dm.DOMAIN_VERSION,
                                                     "layout": pb.LAYOUT, "planner_profile": "P16_FAST"}, "cpu_s": time.process_time() - c0}
        (DATA / split).mkdir(parents=True, exist_ok=True)
        cf.write_json(f, res)


def merged(split, kind="labels") -> dict:
    out = {}
    for g in sorted((DATA / split).glob(f"{kind}_*.json")):
        out |= rd(g)
    return out


import numpy as np  # noqa: E402


# ------------------------------------------------------------------ P17 splits (new seeds; P13 grammars + DENSE via build_plan, REACH via p17_mech)
SEED0 = {"p17dev": 2026260000, "p17train": 2026270000, "p17calib": 2026280000, "p17test": 2026290000}


def build_p17_split(name, counts) -> None:
    """counts {family: n}; REACH uses p17_mech.reach_spec (geometry-first; first collision-free start per seed). Writes DATA/name/plan.json."""
    import p16_common as pc
    import p17_mech as m
    pdm = pc.register()
    fams = sorted(f for f in counts if f != "REACH")
    split = "blind" if name.startswith("p17test") else "dev"
    specs = [{"family": f, "seed": SEED0[name] + 1000 * i + j, "index": len(fams) * j + i, "wave": 0, "batch": 1, "split": split}
             for i, f in enumerate(fams) for j in range(counts[f])]
    sub = DATA / name / "grammar"
    if specs and not (sub / "plan.json").exists():
        pdm.build_plan(sub, specs, max_attempts=600, root_cpu=300.0)
    roots = dict(rd(sub / "plan.json")["roots"]) if specs else {}
    reach, att = {}, 0
    j = 0
    while len(reach) < counts.get("REACH", 0) and att < 50 * max(1, counts.get("REACH", 0)):
        att += 1
        spec = m.reach_spec(np.random.default_rng([SEED0[name] + 900000, j]))
        j += 1
        if spec is None:
            continue
        key = f"p17r_{SEED0[name] + 900000 + j}"
        root = m.build_root(spec, key)
        if root is None:
            continue
        reach[key] = {**root, "family": "REACH", "seed": SEED0[name] + 900000 + j, "split": split, "stratum": spec["stratum"]}
    plan = {"roots": {**roots, **reach}, "reach_attempts": att, "counts": counts, "name": name}
    plan["plan_hash"] = cf.stable_hash({k: v for k, v in plan.items()})
    cf.write_json(DATA / name / "plan.json", plan)


def leakage_p17() -> dict:
    import p14_sweep_index as sx
    import p15_lookup as pl
    fp = {}
    for d in list(Path("runs/p16/data").glob("*/plan.json")) + list(DATA.glob("*/plan.json")):
        for k, r in rd(d)["roots"].items():
            fp.setdefault(json.dumps(r["fingerprint"]), []).append((str(d.parent), k))
    idx = pl.index_v2()[0]
    P = sx._plans()
    idx_fp = {pl.json_fp(P[e["root"]]) for es in idx.by_key.values() for e in es}
    dup = {f: v for f, v in fp.items() if len(v) > 1}
    out = {"roots": sum(len(v) for v in fp.values()), "duplicates": dup, "index_overlap": [f for f in fp if f in idx_fp]}
    cf.write_json(DATA / "LEAKAGE.json", out)
    return out


def label_queue(part, sealed=False) -> None:
    """Claim (split, key) pairs atomically from runs/p17/data/label_queue.json; resumable; one provider set per root."""
    q = rd(DATA / ("sealed_label_queue.json" if sealed else "label_queue.json"))
    claims = DATA / ("sealed_claims" if sealed else "label_claims")
    claims.mkdir(parents=True, exist_ok=True)
    for split, k in q:
        try:
            os.close(os.open(claims / f"{split}__{k}.claim", os.O_CREAT | os.O_EXCL))
        except FileExistsError:
            continue
        label_roots(split, [k], part, sealed=sealed)


def det_p17(keys, tag) -> None:
    """P17 determinism: corrected search (uniform order, repeats <= 2, n <= 4) on the given development roots; outcome + trajectory hash."""
    import p15_lookup as pl
    import p16_common as pc
    import p17_exec as ex
    idx = pl.index_v2()[0]
    f = OUT / "shared" / f"DET_P17_{tag}.json"
    res = rd(f) if f.exists() else {}
    for split, k in keys:
        if f"{split}|{k}" in res:
            continue
        task = pc.task_from_root(_plan(split)["roots"][k], k)
        g = ex.d_root(task, idx, ["uniform"], {})["uniform"]
        res[f"{split}|{k}"] = {x: g[x] for x in ("found", "replay", "traj", "claim", "moves", "travel", "used")} | {"nodes": g["log"]["nodes"],
                                                                                                                 "hashseed": os.environ.get("PYTHONHASHSEED")}
        cf.write_json(f, res)


TRAIN_SPLITS, VAL_SPLITS = ("train", "dev", "calib", "p17train"), ("val",)


def build_training_data() -> None:
    """runs/p17/b/TRAIN.pt: {train: P13 train (P13 protocol, tagged) + P17-labelled P16 train / dev / calib + p17train,
    val: P13 validation + P17-labelled P16 val}; runs/p17/d/D_ITEMS.pt: D items (P13: PARKING_LATTICE_V1 masked;
    P16 / P17 roots: MULTI_DEST_LATTICE_V1)."""
    import torch
    import learn_data as ld
    import p17_b as pb
    import p17_d as pd
    os.environ["P10C_OUT"] = "runs/p13/models"
    p13 = torch.load("runs/p13/models/dataset_trainval.pt", weights_only=False)["roots"]
    for r in p13:
        r["audit"]["protocol"] = "P13_TEACHER_CONSTRUCTOR_CATALOGUE"
    dino = ld.dino()
    recs, labs_all, counts = {}, {}, {}
    for s in TRAIN_SPLITS + VAL_SPLITS:
        labs = merged(s)
        plan = _plan(s)["roots"]
        recs[s] = pb.records(plan, labs, "validation" if s in VAL_SPLITS else "train", dino)
        labs_all[s] = labs
        counts[f"p17_{s}"] = len(labs)
    d = {"train": [r for r in p13 if r["audit"]["split"] == "train"] + [r for s in TRAIN_SPLITS for r in recs[s]],
         "val": [r for r in p13 if r["audit"]["split"] == "validation"] + [r for s in VAL_SPLITS for r in recs[s]],
         "counts": counts | {"p13_train": sum(r["audit"]["split"] == "train" for r in p13), "p13_val": sum(r["audit"]["split"] == "validation" for r in p13)}}
    (OUT / "b").mkdir(parents=True, exist_ok=True)
    torch.save(d, OUT / "b" / "TRAIN.pt")
    items = {"train": [], "val": [], "protocols": {"P13": "PARKING_LATTICE_V1 (NO_CLEARING masked)", "P16/P17 roots": "MULTI_DEST_LATTICE_V1"}}
    for part, src in (("train", [r for r in p13 if r["audit"]["split"] == "train"]), ("val", [r for r in p13 if r["audit"]["split"] == "validation"])):
        for r, rec in zip(pb.prepare(src), src):
            dd = dict(rec.get("d") or {})
            if dd.get("y0") is None:
                y0 = next((c["y"] for c in r["cands"] if not c["seq"]), None)
                dd = {"y0": y0, "pool": []} if y0 is not None else dd
            it = pd.item(r["R"], dd)
            if it:
                items[part].append(it)
    for s in TRAIN_SPLITS + VAL_SPLITS:
        part = "val" if s in VAL_SPLITS else "train"
        for r in pb.prepare(recs[s]):
            lab = labs_all[s][r["key"]]
            pool = lab["catalogue"]["pool"]
            st = {tuple(x.split("+")) if x != "-" else (): v for x, v in lab["multi_dest"]["statuses"].items()}
            dlat = pd.lattice_from({S: v for S, v in st.items()}, pool)
            dlat["pool"] = [r["ids"].index(o) for o in pool]
            it = pd.item(r["R"], dlat)
            if it:
                items[part].append(it)
    torch.save(items, OUT / "d" / "D_ITEMS.pt") if (OUT / "d").mkdir(parents=True, exist_ok=True) is None else None
    cf.write_json(OUT / "b" / "TRAIN_COUNTS.json", d["counts"] | {"sha": sha(OUT / "b" / "TRAIN.pt"), "d_items": {k: len(v) for k, v in items.items() if k != "protocols"},
                                                                  "d_masks": {k: sum(b is not None for *_, b in v) for k, v in items.items() if k != "protocols"}})


def rescreen(seed0, idxs, gen, part) -> None:
    """Deterministic re-run of specific screening scenes (seed = seed0 * 1000 + i) with full per-scene recording."""
    import p17_mech as m
    f = OUT / "mechanisms" / "screen" / f"rescreen_{gen}_{part}.json"
    acc = rd(f) if f.exists() else {"kept": [], "scenes": []}
    for i in idxs:
        r = m.screen2(seed0 * 1000 + i, 1, "repeat", 4, gen)
        acc["kept"] += r["kept"]
        acc["scenes"] += r["stats"].get("scenes", [])
        cf.write_json(f, acc)


CAL_FIT, CAL_EVAL = ("train", "dev", "val", "p17train"), ("calib", "p17calib")


def d_calibrate(kinds=("D", "Dp", "Dp16", "Dp17")) -> dict:
    """Per-family temporary-target feasibility calibration (fit on training-side roots, evaluated on held-out calibration-side roots);
    temporary-target blocker-marginal validation on every decided temporary lattice with a defined mask (both sides)."""
    import p17_d as pd
    plans = {s: _plan(s) for s in CAL_FIT + CAL_EVAL}
    probes = {s: pd.probes_from_labels(merged(s), plans[s]["roots"], s) + pd.probes_from_inter(merged(s, "temp_inter"), s) for s in CAL_FIT + CAL_EVAL}
    out = {}
    for kind in kinds:
        if kind == "Dp17" and not (Path("runs/p17/d/ckpt/P17-Dp-l2.0-s0.pt")).exists():
            continue
        fit = pd.score_probes(kind, [p for s in CAL_FIT for p in probes[s]], plans)
        ev = pd.score_probes(kind, [p for s in CAL_EVAL for p in probes[s]], plans)
        cal = pd.fit_calibration(kind, fit)
        a, b = cal["slope"], cal["bias"]
        held = [(1 / (1 + np.exp(-(a * p["logit_raw"] + b))), p["y"]) for p in ev]
        rec = lambda rows, c: float(np.mean([pp >= 0.5 for pp, y in rows if y == c])) if any(y == c for _, y in rows) else None  # noqa: E731
        cal["held_out"] = {"n": len(held), "positives": sum(y for _, y in held), "feasible_recall": rec(held, 1), "infeasible_recall": rec(held, 0),
                           "brier": float(np.mean([(pp - y) ** 2 for pp, y in held])) if held else None}
        masks = [p for p in fit + ev if p["y"] == 0 and p["type"] == "MINIMAL_SETS" and p["mask"] is not None]
        tp = sum(int(m >= 0.5) and b_ for p in masks for m, b_ in zip(p["marg"], p["mask"]))
        fp = sum(int(m >= 0.5) and not b_ for p in masks for m, b_ in zip(p["marg"], p["mask"]))
        fn = sum((m < 0.5) and b_ for p in masks for m, b_ in zip(p["marg"], p["mask"]))
        cal["temp_blocker_marginals"] = {"lattices_with_mask": len(masks), "f1": 2 * tp / max(1, 2 * tp + fp + fn), "tp": tp, "fp": fp, "fn": fn}
        (OUT / "d" / "calibration").mkdir(parents=True, exist_ok=True)
        cf.write_json(OUT / "d" / "calibration" / f"{kind}.json", cal)
        out[kind] = cal
    cf.write_json(OUT / "d" / "CALIBRATION_SUMMARY.json", out | {"probes": {s: len(v) for s, v in probes.items()}})
    return out


def temp_intermediate(split, keys, part) -> None:
    """Temporary-target lattices at INTERMEDIATE states: for a labelled VERIFIED >= 2-move sequence, apply its first relocation with the
    cheapest certified mode (actual terminal q) and build temporary lattices for the remaining pool objects there."""
    import p15_lookup as pl
    import p16_common as pc
    import p16_motion as pm
    import p17_d as pd
    idx, plan, labs = pl.index_v2()[0], _plan(split), merged(split)
    f = DATA / split / f"temp_inter_{part}.json"
    res = rd(f) if f.exists() else {}
    for k in keys:
        if k in res or k not in labs:
            continue
        seqs = [s for s, v in labs[k]["sequences"].items() if v["y"] == 1 and v["len"] >= 2]
        if not seqs:
            res[k] = {"skipped": "no verified >= 2-move sequence"}
            cf.write_json(f, res)
            continue
        task = pc.task_from_root(plan["roots"][k], k)
        phys = pm.DetPhysics(task, idx, budget=P17_LABEL_BUDGET)
        cells0, q0 = {o.id: o.cell for o in phys.s0.objects}, np.asarray(phys.s0.robot.q_rad, float)
        o1, d1 = seqs[0].split(".")[0].split(">")
        outs = [x for x in phys.edges(cells0, q0, o1, int(d1)) if x[0] == pm.V]
        if not outs:
            res[k] = {"skipped": "first move not re-verified"}
            cf.write_json(f, res)
            continue
        e = min(outs, key=lambda x: x[3])
        cells1, q1 = {**cells0, o1: int(d1)}, e[2]
        cat = labs[k]["catalogue"]
        pool = [o for o in cat["pool"] if o != o1]
        dest = {o: cat["parking"][o] for o in pool if cat["parking"][o] not in cells1.values()}
        pool = [o for o in pool if o in dest]
        res[k] = {"sequence": seqs[0], "state": {"cells": cells1, "q": [float(x) for x in q1]},
                  "lattices": pd.temp_lattice(phys, cells1, q1, pool, dest) if len(pool) >= 2 else [], "used": phys.used}
        cf.write_json(f, res)
