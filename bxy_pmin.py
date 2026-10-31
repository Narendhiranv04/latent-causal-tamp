"""BXY-P10-PREREG: prospective P-min design, plan freezing and resource model. NO teacher query is made by this module (except the
instrumented Y wrapper, which only a later authorized collection may call).

Design (enumerated from the immutable roots and their recorded catalogues only; no outcome selects a query or a root):
  custody   train + val roots of the generator's family-grouped IID split (bxy_data.split_of); the 34 historical test roots are excluded
            (exposed in P7, see 0114 §6.3); a decisive test needs fresh roots later
  classes   y0         Y of the empty edit (one per root)
            complete   X and Y of every nonempty recorded catalogue candidate (the frozen selection catalogue)
            reversal   X of the exact reversed order of every multi-move candidate (shares the candidate's Y: same endpoint)
            omission   X and Y of every single-action omission of a multi-move candidate, recomputed from S0 (methodology §4.4)
            prefix     X and Y of every proper prefix r_1:t, t < m
  phases    PMIN_FULL_CATALOGUE = y0 + complete (0108's P-min shape, restricted to train/val)
            PMIN_DEV_MATCHED    = y0 + complete + reversal + omission (requested next: selection catalogue, order and omission contrasts)
            PREFIX_COMPLETE     = prefix (later; until then every proper prefix is an unobserved, marginalized variable)
  F1        bxy_f1.screen on every query; inadmissible queries are listed with their rule and never sent to the teacher (never a label)
  reuse     queries already observed in BXY_SIDECAR_V2_PILOT with the identical teacher hash are reused, not re-queried
Freezing: freeze() writes PMIN_DESIGN.json + PMIN_LOCK.json (design sha256, semantic source hashes, git HEAD, time) once and refuses any
different rewrite; assert_frozen() is the mandatory pre-launch guard of a collection runner (lock / design / source drift / git / results)."""
from __future__ import annotations

import ast
import collections
import hashlib
import json
import subprocess as sp
import time
from pathlib import Path

import numpy as np

import bd_core as bc
import bxy_data as bd
import bxy_f1 as F1
import bxy_teacher as T

OUT = Path("runs/approach_b/bxy_pmin_v1")
PILOT = Path("runs/approach_b/bxy_teacher_pilot_v1/BXY_SIDECAR_V2_PILOT.json")
SPLITS = ("train", "val")
PHASES = {"PMIN_FULL_CATALOGUE": ("y0", "complete"), "PMIN_DEV_MATCHED": ("y0", "complete", "reversal", "omission"), "PREFIX_COMPLETE": ("prefix",)}
REQUESTED = "PMIN_DEV_MATCHED"
ENTRY = ("bxy_teacher.py", "bxy_f1.py", "bxy_pmin.py", "bxy_data.py", "bxy_pilot.py", "bd_2d.py")
WORKERS = 8                                                     # requested, not authorized (16 physical cores; others stay free)


def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ design (no outcome is read)
def _add(Q, bad, k, rec, side, seq, cls):
    f = F1.screen(rec, seq)
    ok = f["x_ok"] if side == "x" else f["y_ok"]
    key = T.xkey(k, rec, seq) if side == "x" else T.ykey(k, rec, seq)
    if not ok:
        bad.setdefault(key, {"side": side, "seq": [list(a) for a in seq], "classes": [], "f1": f["x_violations"] if side == "x" else f["y_violations"]})
        bad[key]["classes"] = sorted(set(bad[key]["classes"]) | {cls})
        return
    q = Q.setdefault(key, {"side": side, "seq": [list(a) for a in seq], "len": len(seq), "classes": []})
    if side == "x":
        q["parent_y_key"] = T.ykey(k, rec, seq)
    else:
        q["edit"] = bd.endpoint(rec, seq)
    q["classes"] = sorted(set(q["classes"]) | {cls})


def root_design(k, rec) -> dict:
    Q, bad = {}, {}
    _add(Q, bad, k, rec, "y", [], "y0")
    for c in bd.catalogue(rec)[1:]:
        s = [tuple(a) for a in c["seq"]]
        _add(Q, bad, k, rec, "x", s, "complete")
        _add(Q, bad, k, rec, "y", s, "complete")
        if len(s) >= 2:
            _add(Q, bad, k, rec, "x", s[::-1], "reversal")
            for t in range(len(s)):
                om = [a for i, a in enumerate(s) if i != t]
                _add(Q, bad, k, rec, "x", om, "omission")
                _add(Q, bad, k, rec, "y", om, "omission")
            for t in range(1, len(s)):
                _add(Q, bad, k, rec, "x", s[:t], "prefix")
                _add(Q, bad, k, rec, "y", s[:t], "prefix")
    for q in Q.values():
        q["phases"] = sorted(p for p, cl in PHASES.items() if set(q["classes"]) & set(cl))
    return {"split": bd.split_of(rec), "stratum": stratum(rec), "queries": dict(sorted(Q.items())), "f1_screened": dict(sorted(bad.items()))}


def stratum(rec):
    k = rec["verified_K"]
    return "None" if k is None else f"K{k}" if k < 2 else "K>=2"


def p9_observed(path=PILOT) -> dict:
    """{key: teacher_hash} of the pilot's observed queries (labels themselves are not copied into the design)."""
    sc = json.loads(Path(path).read_text())
    th = sc["manifest"]["teacher_hash"][0]
    return {r.get("x_key") or r.get("y_key"): th for r in sc["x_queries"] + sc["y_queries"] if r.get("observed") and r.get("y") in (0, 1)}


def design() -> dict:
    R = bd.roots()
    ks = sorted((k for k, r in R.items() if bd.split_of(r) in SPLITS), key=lambda k: bc.sha([k, "BXY_PMIN_V1"]))
    p9, th = p9_observed(), T.teacher_hash()
    roots = {}
    for k in ks:
        d = root_design(k, R[k])
        for key, q in d["queries"].items():
            q["reuse_p9"] = p9.get(key) == th
        roots[k] = d
    return {"version": "BXY_PMIN_DESIGN_V1", "data_sha256": bd.data_hash(), "teacher_hash": th, "x_teacher": T.X_VERSION, "y_teacher": T.Y_VERSION,
            "teacher_policy": T.TEACHER, "f1": F1.VERSION, "splits": list(SPLITS), "excluded": "historical test split (exposed in P7)",
            "phases": {p: list(c) for p, c in PHASES.items()}, "requested_phase": REQUESTED, "root_order": ks, "roots": roots}


def worklist(D, phase=REQUESTED) -> dict:
    """{root: [query entries to send to the teacher]} for one phase (F1-admissible, not reused from P9), X before Y within a root."""
    return {k: [dict(q, key=key) for key, q in sorted(d["queries"].items(), key=lambda kv: (kv[1]["side"], kv[0]))
                if phase in q["phases"] and not q["reuse_p9"]] for k, d in ((k, D["roots"][k]) for k in D["root_order"])}


def counts(D) -> dict:
    out = {}
    for ph in PHASES:
        c = collections.Counter()
        for k in D["root_order"]:
            d = D["roots"][k]
            for key, q in d["queries"].items():
                if ph in q["phases"]:
                    c[f"{q['side']}_{d['split']}"] += 1
                    c[f"{q['side']}_len{q['len']}"] += 1
                    c[f"{q['side']}_{d['stratum']}"] += 1
                    c[f"{q['side']}_reuse_p9"] += q["reuse_p9"]
                    c[f"{q['side']}_to_query"] += not q["reuse_p9"]
            for key, q in d["f1_screened"].items():
                if set(q["classes"]) & set(PHASES[ph]):
                    c[f"f1_screened_{q['side']}_{q['f1'][0]['rule']}"] += 1
        Xs = {(k, key): q for k in D["root_order"] for key, q in D["roots"][k]["queries"].items() if ph in q["phases"] and q["side"] == "x"}
        Ys = {(k, key) for k in D["root_order"] for key, q in D["roots"][k]["queries"].items() if ph in q["phases"] and q["side"] == "y"}
        c["x_with_matched_y_in_phase"] = sum((k, q["parent_y_key"]) in Ys for (k, _), q in Xs.items())
        sib = collections.Counter((k, q["parent_y_key"]) for (k, _), q in Xs.items() if q["len"] >= 2)
        c["same_endpoint_order_groups"] = sum(v >= 2 for v in sib.values())
        out[ph] = dict(sorted(c.items()))
    return out


# ------------------------------------------------------------------ provenance and freezing
def sources(entry=ENTRY) -> dict:
    """sha256 of every repo-local module transitively imported by the teacher / design / runner entry modules, plus config.toml."""
    seen, todo = set(), list(entry)
    while todo:
        f = todo.pop()
        if f in seen or not Path(f).exists():
            continue
        seen.add(f)
        for n in ast.walk(ast.parse(Path(f).read_text())):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) and n.module else []
            todo += [f"{m.split('.')[0]}.py" for m in names if Path(f"{m.split('.')[0]}.py").exists()]
    return {f: sha_file(f) for f in sorted(seen | {"config.toml"})}


def git(*a) -> str:
    return sp.run(["git", *a], capture_output=True, text=True).stdout.strip()


def freeze(out=OUT, D=None, requested=None) -> dict:
    out = Path(out)
    D = D or design()
    res = out / "results"
    if res.exists() and any(res.rglob("*.json")):
        raise RuntimeError("results already exist: a plan can only be frozen before collection")
    text = json.dumps(D, indent=1, sort_keys=True)
    f = out / "PMIN_DESIGN.json"
    if f.exists() and f.read_text() != text:
        raise FileExistsError(f"{f} is frozen and differs from the recomputed design")
    out.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    lock = {"design_sha256": sha_file(f), "phase": D["requested_phase"], "sources": sources(), "git_head_at_freeze": git("rev-parse", "HEAD"),
            "frozen_at": time.time(), "results_present_at_freeze": False, "authorized": False, "requested_caps": requested}
    lf = out / "PMIN_LOCK.json"
    if lf.exists():
        old = json.loads(lf.read_text())
        if {k: v for k, v in old.items() if k not in ("frozen_at", "git_head_at_freeze")} != {k: v for k, v in lock.items() if k not in ("frozen_at", "git_head_at_freeze")}:
            raise FileExistsError(f"{lf} is frozen and differs")
        return old
    lf.write_text(json.dumps(lock, indent=1, sort_keys=True))
    return lock


def assert_frozen(out=OUT, check_git=True) -> dict:
    """Mandatory pre-launch guard: the design file is the locked one, no semantic source drifted, the plan is committed and clean in git,
    and no result predates the lock. Raises RuntimeError with every problem."""
    out = Path(out)
    lock, bad = json.loads((out / "PMIN_LOCK.json").read_text()), []
    if sha_file(out / "PMIN_DESIGN.json") != lock["design_sha256"]:
        bad.append("design file differs from the lock")
    now = sources()
    bad += [f"source drift: {f}" for f in sorted(set(now) | set(lock["sources"])) if now.get(f) != lock["sources"].get(f)]
    if check_git:
        for f in ("PMIN_DESIGN.json", "PMIN_LOCK.json"):
            p = str(out / f)
            if sp.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode or sp.run(["git", "diff", "--quiet", "HEAD", "--", p]).returncode:
                bad.append(f"{f} not committed / not clean")
    bad += [f"result before lock: {p}" for p in (out / "results").rglob("*.json") if p.stat().st_mtime < lock["frozen_at"]] if (out / "results").exists() else []
    if bad:
        raise RuntimeError("; ".join(bad))
    return lock


def admitted(D, k, key, phase=REQUESTED) -> bool:
    """Per-query runner guard: only a frozen, F1-admissible, phase member, not-reused query may be sent to the teacher."""
    q = D["roots"].get(k, {}).get("queries", {}).get(key)
    return bool(q) and phase in q["phases"] and not q["reuse_p9"]


# ------------------------------------------------------------------ instrumented Y (behaviour-preserving)
def y_query_counted(E, k, rec, seq, cache, out=None, legacy=None) -> dict:
    """bxy_teacher.y_query with the DetPhysics budget counters of the call exposed. bd_2d._phys is wrapped for the call only (same object
    returned, nothing else changed), so the outcome, witness and cache are identical to the unwrapped teacher."""
    import bd_2d
    real, seen = bd_2d._phys, []

    def spy(task, cache_):
        p = real(task, cache_)
        seen.append((p, dict(p.used)))
        return p
    bd_2d._phys = spy
    try:
        row = T.y_query(E, k, rec, seq, cache, out, legacy)
    finally:
        bd_2d._phys = real
    if not seen:
        return row | {"budget_spent": None, "budget_counter_source": "not reached"}
    p, u0 = seen[-1]
    return row | {"budget": dict(p.budget), "budget_spent": {x: p.used[x] - u0.get(x, 0) for x in p.used}, "budget_counter_source": "DetPhysics.used"}


# ------------------------------------------------------------------ resource model (P9 measurements; separate X and Y)
def p9_costs(path=PILOT) -> dict:
    sc, R = json.loads(Path(path).read_text()), bd.roots()
    X = collections.defaultdict(list)
    Y = collections.defaultdict(list)
    for r in sc["x_queries"]:
        if r.get("process_cpu_s") is not None:
            X[min(len(r["ordered_actions"]), 5)].append(r["process_cpu_s"])
    for r in sc["y_queries"]:
        if r.get("process_cpu_s") is not None:
            Y[stratum(R[r["root"]])].append(r["process_cpu_s"])
    led = sc["manifest"]["measured"]["ledger"]
    q = collections.Counter()
    for r in sc["x_queries"] + sc["y_queries"]:
        q[r["root"]] += r.get("process_cpu_s") or 0
    over = [max(0.0, x["cpu_s"] - q[x["root"]]) for x in led]
    return {"x_by_len": {k: sorted(v) for k, v in sorted(X.items())}, "y_by_stratum": {k: sorted(v) for k, v in sorted(Y.items())},
            "root_overhead": sorted(over), "x_all": sorted(sum(X.values(), [])), "y_all": sorted(sum(Y.values(), []))}


def cost_model(D, phase=REQUESTED, B=2000, seed=0, workers=WORKERS) -> dict:
    """Bootstrap of the phase worklist's CPU from P9 per-query CPU (X by prefix length, capped at 5; Y by root stratum; per-root process
    overhead), plus a stress scenario (every query at its class 90th percentile). Returns estimates and the REQUESTED caps."""
    C, rng, W = p9_costs(), np.random.default_rng(seed), worklist(D, phase)
    pool = lambda q, k: C["x_by_len"].get(min(q["len"], 5)) or C["x_all"] if q["side"] == "x" else C["y_by_stratum"].get(D["roots"][k]["stratum"]) or C["y_all"]  # noqa: E731
    per_root = {k: [np.asarray(pool(q, k)) for q in qs] for k, qs in W.items() if qs}
    ov = np.asarray(C["root_overhead"])
    tot, root_max = np.zeros(B), np.zeros(B)
    for k, ps in per_root.items():
        s = sum(rng.choice(p, B) for p in ps) + rng.choice(ov, B)
        tot += s
        root_max = np.maximum(root_max, s)
    stress_root = {k: float(sum(np.percentile(p, 90) for p in ps) + ov.max()) for k, ps in per_root.items()}
    stress = sum(stress_root.values())
    nx = sum(q["side"] == "x" for qs in W.values() for q in qs)
    ny = sum(q["side"] == "y" for qs in W.values() for q in qs)
    req_cpu = int(np.ceil(1.5 * np.percentile(tot, 97.5) / 1000) * 1000)                 # aggregate: 1.5 x bootstrap upper bound + checkpoint
    req_root = int(np.ceil(1.5 * max(max(stress_root.values()), np.percentile(root_max, 97.5)) / 100) * 100)   # per root: stress-safe
    est_wall = float(np.mean(tot)) / workers * 1.25
    return {"phase": phase, "roots": len(per_root), "x_queries": nx, "y_queries": ny,
            "p9_rates": {"x_mean_cpu_s": float(np.mean(C["x_all"])), "y_mean_cpu_s": float(np.mean(C["y_all"])), "n_x": len(C["x_all"]), "n_y": len(C["y_all"]),
                         "x_mean_by_len": {k: round(float(np.mean(v)), 2) for k, v in C["x_by_len"].items()},
                         "y_mean_by_stratum": {k: round(float(np.mean(v)), 2) for k, v in C["y_by_stratum"].items()}},
            "cpu_s_mean": float(np.mean(tot)), "cpu_s_95": [float(np.percentile(tot, 2.5)), float(np.percentile(tot, 97.5))], "cpu_s_stress_p90": stress,
            "x_cpu_s_mean": float(sum(np.mean(p) for qs, ps in ((W[k], per_root[k]) for k in per_root) for q, p in zip(qs, ps) if q["side"] == "x")),
            "y_cpu_s_mean": float(sum(np.mean(p) for qs, ps in ((W[k], per_root[k]) for k in per_root) for q, p in zip(qs, ps) if q["side"] == "y")),
            "max_root_cpu_s_95": float(np.percentile(root_max, 97.5)), "max_root_cpu_s_stress": max(stress_root.values()),
            "requested": {"cpu_s": req_cpu, "root_cpu_s": req_root, "workers": workers,
                          "wall_s": int(np.ceil((req_cpu / workers * 1.25 + req_root) / 600) * 600)},
            "est_wall_s_mean": est_wall, "est_root_cpu_s": {k: float(sum(np.mean(p) for p in ps) + ov.mean()) for k, ps in per_root.items()},
            "checkpoint_rule": "after every finished root once 20 have finished: projected = spent / est(finished) * est(all); stop launching "
                               "new roots (never kill a running one) if projected > requested cpu_s, and report"}


def checkpoint(spent, est, cap, min_roots=20) -> dict:
    """Projection guard of the collection runner: spent {root: cpu_s} of finished roots, est {root: expected cpu_s} of every root."""
    if len(spent) < min_roots:
        return {"ok": True, "projected": None}
    proj = sum(spent.values()) / sum(est[k] for k in spent) * sum(est.values())
    return {"ok": proj <= cap, "projected": proj}


if __name__ == "__main__":
    import sys
    D = design()
    if sys.argv[1:] == ["freeze"]:
        print(json.dumps(freeze(D=D, requested=cost_model(D)["requested"]), indent=1)[:2000])
    else:
        print(json.dumps({"counts": counts(D), "cost": {p: cost_model(D, p) for p in PHASES}}, indent=1))
