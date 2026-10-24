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


# ------------------------------------------------------------------ P12-2: roster, plans, records, frozen predictions (before ANY confirmation label)
HOLD = OUT / "holdout"
ROSTER_SEED0 = 2026140001


def roster(n=80) -> list:
    import p12_families as pf
    return [{"index": i, "family": pf.FAMS[i % 2], "split": "blind", "seed": ROSTER_SEED0 + i, "wave": 0, "batch": 1 + i // 20} for i in range(n)]


def build_batches(n=80) -> None:
    import p10b_dataset as pd
    import p12_families  # noqa: F401  (registers the family dispatch)
    for b in sorted({s["batch"] for s in roster(n)}):
        d = HOLD / f"batch{b}"
        if not (d / "plan.json").exists():
            pd.build_plan(d, [s for s in roster(n) if s["batch"] == b], max_attempts=400, root_cpu=120.0)


def plans():
    return {k: r for b in sorted(HOLD.glob("batch*/plan.json")) for k, r in _rd(b)["roots"].items()}


def holdout_records() -> None:
    import torch
    import learn_data as ld
    import p10c_train_eval as pc
    cfg, dino, recs = cf.load_config("config.toml"), ld.dino(), []
    for k, r in plans().items():
        ed = [it for it in r["items"] if it.get("edit_kind") in ("A", "B", "A+B")]
        sq = [it for it in r["items"] if it["kind"] == "ORDERED_TEACHER"]
        rec, _ = pc._record(cfg, dino, k, r, {}, "blind", "P12", ed, sq)
        ids = rec["audit"]["ids"]
        rec["audit"]["family"] = r["family"]
        rec["d"] = {"pool": [ids.index(o) for o in r["parking"]], "roles": [{v: kk for kk, v in r["ids"].items()}[o] for o in r["parking"]]}
        recs.append(rec)
    torch.save({"version": "P12_RECORDS_V1", "roots": recs}, HOLD / "records.pt")


def freeze_predictions() -> None:
    """Frozen per-root marginals, kappa_hat, TOP1, ranked rows for all 33 frozen checkpoints; D / heuristic / geometry. 0 physical calls."""
    import contextlib
    import copy
    import torch
    import abc7_train as t7
    import d_blockers as db
    import p10_eval as pe
    import p10_protocol as pp
    import p10c_train_eval as pc
    import p10d_execute as px
    import p9_l3 as l3
    import unique_factor_keyed as ufk
    from scene import scene_from_dict
    if (HOLD / "PREDICTIONS_FROZEN.json").exists() or (HOLD / "UNSEALED").exists():
        raise SystemExit("predictions already frozen or labels unsealed")
    if any((b.parent / "static_admission.json").exists() for b in HOLD.glob("batch*/plan.json")):
        raise SystemExit("teacher outcomes exist: no blind freeze possible")
    cfg, P, snap = cf.load_config("config.toml"), plans(), _rd("runs/p10d/predictions.json")
    ds = torch.load(HOLD / "records.pt", weights_only=False)
    rs = t7.prepare(ds)
    for r, rec in zip(rs, ds["roots"]):
        r["ids"], r["audit"], r["d"] = rec["audit"]["ids"], rec["audit"], rec["d"]
    veto = {r["key"]: frozenset(c["query"] for c in r["cands"] if c["seq"] and pp.static_veto(
        scene_from_dict(P[r["key"]]["scene"]), [(r["ids"][i], l3.cell(d)) for i, d in c["seq"]], P[r["key"]]["goal_cell"], cfg)) for r in rs}
    calls, out = pp.instrument(), {"arms": {}, "d": {}, "baselines": {}}
    for arm in FROZEN_ARMS:
        for s in (0, 1, 2):
            n = f"F-{arm}-s{s}"
            m, a = pc.load(n)[0], snap["arms"][n]
            keyed = pc.ARMS[arm][2]
            ctx = ufk.installed if keyed else contextlib.nullcontext
            per = {}
            for r in rs:
                rr = pc._v0([copy.deepcopy(r)])[0] if arm == "B-V0" else r
                try:
                    with ctx():
                        pm = pe.marginals(m, rr, arm not in ("A", "SF"))
                        rows = l3.root_eval9(m, rr, "unique" if arm not in ("A", "SF") else "factorized")["root"]["cands"]
                    sel = pp.top1(m, rr, a["tau"], a["threshold"], veto[r["key"]], keyed)
                    per[r["key"]] = {"marginals": pm, "top1": sel["choice"], "admitted": sel["admitted"],
                                     "rows": [{k: x[k] for k in ("query", "m", "u", "J_pred", "C_d", "energy")} for x in rows]}
                except Exception as e:                                   # scope / identity failure = coverage failure, never a dropped root
                    per[r["key"]] = {"coverage_failure": f"{type(e).__name__}: {e}"[:300]}
            out["arms"][n] = {"arm": arm, "seed": s, "tau": a["tau"], "threshold": a["threshold"], "checkpoint_sha256": a["checkpoint_sha256"], "roots": per}
    lam = {x: snap["baselines"][f"{x}_lambda_B"] for x in ("D", "D-pairless")}
    for n, x in snap["d"].items():
        if x["lambda_B"] != lam[x["arm"]]:
            continue
        m = db.ModelD(pair=x["arm"] == "D").double()
        m.load_state_dict(torch.load(f"runs/p10c/ckpt/{n}.pt", weights_only=True))
        m.eval()
        out["d"][n] = {"arm": x["arm"], "seed": x["seed"], "lambda_B": x["lambda_B"], "roots": {r["key"]: db.predict(m, r["R"], r["d"]["pool"]) for r in rs}}
    out["baselines"] = {k: snap["baselines"][k] for k in ("D_lambda_B", "D_threshold", "D-pairless_lambda_B", "D-pairless_threshold")} | \
        {"heuristic": {r["key"]: db.heuristic(r["R"], r["d"]["pool"]) for r in rs}, "geometry_top1": {r["key"]: px.geometry_choice(P[r["key"]], r, cfg) for r in rs},
         "static_veto": {k: sorted(v) for k, v in veto.items()}}
    if sum(calls.values()):
        raise RuntimeError(f"physical calls during frozen prediction: {dict(calls)}")
    out |= {"version": "P12_PREDICTIONS_V1", "physical_calls": dict(calls), "records_sha256": sha(HOLD / "records.pt"),
            "plans": {str(b): _rd(b)["plan_hash"] for b in sorted(HOLD.glob("batch*/plan.json"))}}
    out["hash"] = cf.stable_hash(out)
    cf.write_json(HOLD / "PREDICTIONS_FROZEN.json", out)


def scene_manifest() -> None:
    P = plans()
    man = {"roots": {k: {"family": r["family"], "seed": r["seed"], "batch": r["batch"], "scene_hash": r["scene_hash"], "fingerprint": r["fingerprint"],
                         "construction": r["construction"], "role_cells": r["role_cells"], "fixed": r["fixed"], "stratum": r["stratum"],
                         "queries": sorted(it["query"] for it in r["items"])} for k, r in P.items()},
           "unavailable": [u for b in sorted(HOLD.glob("batch*/plan.json")) for u in _rd(b)["unavailable"]],
           "attempts": {str(b): len(_rd(b)["attempts"]) for b in sorted(HOLD.glob("batch*/plan.json"))}}
    man["hash"] = cf.stable_hash(man)
    cf.write_json(HOLD / "SCENE_MANIFEST.json", man)


def sealed_records(batch) -> dict:
    """Adjudicated P12 holdout records; refuses until runs/p12/holdout/UNSEALED exists (written only after the frozen-prediction commit)."""
    import p6_run as p6r
    import operational_teacher as ot
    if not (HOLD / "UNSEALED").exists():
        raise SystemExit("P12 holdout labels are sealed")
    out = HOLD / batch
    plan, static, pol = _rd(out / "plan.json"), _rd(out / "static_admission.json")["certificates"], ot.load_policy("teacher_opneg.toml")
    res = {}
    for k in plan["roots"]:
        pf = out / "sealed" / f"{k}.json"
        done = _rd(pf)["done"] if pf.exists() else {}
        for q in plan["queries"]:
            if q["root"] == k:
                res[q["query"]] = p6r.judge(static, pol, q, done.get(q["query"]))
    return res


def unseal() -> None:
    import subprocess
    h = _rd(HOLD / "PREDICTIONS_FROZEN.json")["hash"]
    remote = subprocess.run(["git", "show", "origin/main:runs/p12/holdout/PREDICTIONS_FROZEN.json"], capture_output=True, text=True).stdout
    if not remote or json.loads(remote)["hash"] != h:
        raise SystemExit("frozen predictions are not on origin/main: refusing to unseal")
    (HOLD / "UNSEALED").write_text(h + "\n")


# ------------------------------------------------------------------ P12-4: prospective F3 / F5 tests and secondary endpoints
def _boot(d, n=2000, seed=0):
    if len(d) < 2:
        return [None, None]
    rng, a = np.random.default_rng(seed), np.asarray(d, float)
    ms = [a[rng.integers(0, len(a), len(a))].mean() for _ in range(n)]
    return [float(np.percentile(ms, 2.5)), float(np.percentile(ms, 97.5))]


def _sign(d):
    from scipy.stats import binomtest
    nz = [x for x in d if x != 0]
    k = sum(x > 0 for x in nz)
    return float(binomtest(k, len(nz)).pvalue) if nz else 1.0, k, len(nz) - k, len(d) - len(nz)


def _holm(ps):
    out, run = {}, 0.0
    for i, k in enumerate(sorted(ps, key=ps.get)):
        run = max(run, min(1.0, (len(ps) - i) * ps[k]))
        out[k] = run
    return out


def factor_tests() -> None:
    snap = _rd(HOLD / "PREDICTIONS_FROZEN.json")
    P, rec = plans(), {}
    for b in sorted(HOLD.glob("batch*/plan.json")):
        rec |= sealed_records(b.parent.name)
    V, C = "VERIFIED_FEASIBLE", "CERTIFIED_INFEASIBLE"
    four = {}
    for k, r in P.items():
        t = {it["token"]: it["query"] for it in r["items"]}
        qs = [t[""], t["edit:A"], t["edit:B"], t["edit:A+B"]]
        st = [rec.get(q, {}).get("teacher_status") for q in qs]
        if all(s in (V, C) for s in st):
            y = [int(s == V) for s in st]
            four[k] = {"q": qs, "kappa": y[3] - y[1] - y[2] + y[0], "y": y}
    def khat(arm, k, s=None):
        vals = []
        for n, a in snap["arms"].items():
            if a["arm"] == arm and (s is None or a["seed"] == s):
                m = a["roots"][k].get("marginals")
                if m is None or any(q not in m for q in four[k]["q"]):
                    return None
                q0, qa, qb, qab = four[k]["q"]
                vals.append(m[qab] - m[qa] - m[qb] + m[q0])
        return vals
    err = {arm: {k: float(np.mean([abs(v - four[k]["kappa"]) for v in khat(arm, k)])) for k in four if khat(arm, k)} for arm in FROZEN_ARMS}
    def contrast(abl):
        ks = sorted(set(err["K-B"]) & set(err[abl]))
        d = [err[abl][k] - err["K-B"][k] for k in ks]
        p, pos, neg, ties = _sign(d)
        seeds = {s: int(sum((float(np.mean([abs(v - four[k]["kappa"]) for v in khat(abl, k, s)])) - float(np.mean([abs(v - four[k]["kappa"]) for v in khat("K-B", k, s)]))) > 0 for k in ks)) for s in (0, 1, 2)}
        fam = {f: float(np.mean([x for k, x in zip(ks, d) if P[k]["family"] == f])) for f in sorted({P[k]["family"] for k in ks}) if any(P[k]["family"] == f for k in ks)}
        return {"roots": len(d), "mean_delta": float(np.mean(d)) if d else None, "ci95": _boot(d), "p_raw": p, "full_B_better": pos, "ablation_better": neg,
                "ties": ties, "effect_size_d": float(np.mean(d) / np.std(d, ddof=1)) if len(d) > 2 and np.std(d) > 0 else None,
                "full_B_better_roots_per_seed": seeds, "per_family_mean_delta": fam}
    prim = {"F3": contrast("B-F3"), "F5s": contrast("B-F5s")}
    h = _holm({k: v["p_raw"] for k, v in prim.items()})
    for k in prim:
        prim[k]["p_holm"] = h[k]
        prim[k]["status"] = ("UNDERPOWERED/NOT_EVALUABLE (< 24 proof-grounded roots)" if prim[k]["roots"] < 24 else
                             "CONFIRMED" if h[k] < 0.05 and prim[k]["mean_delta"] > 0 else "NOT_CONFIRMED")
    sec = {a: contrast(a) for a in ("B-F5q", "B-F2", "B-F4", "B-V0", "B-U", "K-C", "A", "SF")}
    hs = _holm({k: v["p_raw"] for k, v in sec.items()})
    for k in sec:
        sec[k]["p_holm_secondary_family"] = hs[k]
    nll = {}
    for arm in FROZEN_ARMS:
        v = []
        for k in four:
            for n, a in snap["arms"].items():
                if a["arm"] == arm and a["roots"][k].get("marginals"):
                    for q, y in zip(four[k]["q"], four[k]["y"]):
                        p = min(max(a["roots"][k]["marginals"][q], 1e-9), 1 - 1e-9)
                        v.append(-math.log(p if y else 1 - p))
        nll[arm] = float(np.mean(v)) if v else None
    res = {"cohort": {"proof_grounded_four_tuples": len(four), "kappa_classes": dict(collections.Counter(x["kappa"] for x in four.values())),
                      "by_family": dict(collections.Counter(P[k]["family"] for k in four)), "roots_total": len(P)},
           "primary": prim, "secondary": sec, "absolute_kappa_error": {a: float(np.mean(list(v.values()))) if v else None for a, v in err.items()},
           "four_bit_scene_nll": nll, "per_root_kappa": {k: v["kappa"] for k, v in four.items()}}
    (OUT / "p12_4").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "p12_4" / "FACTOR_TESTS.json", res)
