"""P14-A1: natural-mix diagnosis and matched-admission comparisons on FROZEN P13 predictions (exploratory, post-hoc; P13 blind roots stay
test data: no calibrator / threshold is fitted on them). Matched thresholds are derived from validation-only re-inference with the frozen
P13 checkpoints. Later P14-D3 comparison tables and figures are added here."""
from __future__ import annotations

import collections
import math

import numpy as np

import config as cf
from p14_audit import OUT, P13, paired, rd

ARMS = ("K-B", "K-C", "A", "SF", "B-F2", "B-F3pm", "B-F4", "B-F5spm", "B-F5qpm", "B-U", "B-V0", "B-F1off")
GRID = np.round(np.linspace(0.05, 0.99, 95), 3)


def _wilson(k, n):
    if not n:
        return [None, None]
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [c - h, c + h]


def validation_rows() -> None:
    """Validation-only rows (u, m, J_pred, C_d, energy, y) per frozen P13 checkpoint (same scorer as the P13 freeze)."""
    import contextlib
    import copy
    import os
    import torch
    os.environ["P10C_OUT"] = str(P13 / "models")
    import p13_pipeline as pp
    import p9_l3 as l3
    import unique_factor_keyed as ufk
    pc = pp._arms()
    val = [r for r in pp._prepared("trainval") if r["split"] == "validation"]
    out = {}
    for f in sorted((P13 / "models" / "runs").glob("P13-*.json")):
        x = rd(f)
        if x["arm"] not in ARMS:
            continue
        m, keyed = pc.load(x["name"])[0], pc.ARMS[x["arm"]][2]
        rs = pc._v0(copy.deepcopy(val)) if x["arm"] == "B-V0" else val
        with (ufk.installed() if keyed else contextlib.nullcontext()), torch.no_grad():
            ev = [l3.root_eval9(m, r, "factorized" if x["arm"] in ("A", "SF") else "unique")["root"] for r in rs]
        out[x["name"]] = {r["key"]: [{k: c[k] for k in ("query", "u", "m", "J_pred", "C_d", "energy", "y")} for c in e["cands"]] for r, e in zip(rs, ev)}
    (OUT / "calibration").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "calibration" / "VALIDATION_ROWS.json", out)


def _choose(rows, tau, thr, key=("m", "J_pred", "C_d", "energy", "query")):
    adm = [r for r in rows if 1 / (1 + math.exp(-r["u"] / tau)) >= thr]
    return min(adm, key=lambda r: tuple(r[k] for k in key))["query"] if adm else "ABSTAIN"


def _val_curves(vrows, tau):
    """Validation coverage and false admission (chosen candidate labelled infeasible) per threshold."""
    cov, fa = {}, {}
    for t in GRID:
        ch = {k: _choose(rs, tau, t) for k, rs in vrows.items()}
        lab = {k: next((r["y"] for r in vrows[k] if r["query"] == q), None) for k, q in ch.items()}
        cov[float(t)] = float(np.mean([q != "ABSTAIN" for q in ch.values()]))
        fa[float(t)] = float(np.mean([lab[k] == 0 for k, q in ch.items()]))
    return cov, fa


def matched_admission() -> dict:
    """Per arm and seed: (i) historical threshold; (ii) validation-coverage-matched threshold (coverage of K-B at its own validation
    threshold, per seed); (iii) validation false-admission-constrained threshold (max coverage with false admission <= that of K-B). Test
    choices are scored by teacher label (proof-grounded) and by EXACT executed episode identity (root, repair) where it exists; otherwise
    UNKNOWN (never imputed). Also coverage-risk curves from frozen test scores (labels used only to score, not to choose)."""
    import p13_factors as f13
    snap, P, y, st, cost = f13._p13_blind()
    A = f13._by_arm(snap)
    vr = rd(OUT / "calibration" / "VALIDATION_ROWS.json")
    man = rd(P13 / "p13_5" / "EXEC_JOBS.json")
    led = {}
    for f in sorted((P13 / "p13_5" / "episodes").glob("w*/ledger.json")):
        led |= rd(f)["episodes"]
    ep = {f"{j['root']}::{j['choice']}": led.get(f"{j['arm']}__{j['root']}", {}).get("outcome") for j in man["jobs"]}
    if (OUT / "calibration" / "CF_JOBS.json").exists():                 # P14 counterfactual episodes: exact (root, repair) identity, same protocol
        cl = {}
        for f in sorted((OUT / "calibration" / "episodes").glob("w*/ledger.json")):
            cl |= rd(f)["episodes"]
        for j in rd(OUT / "calibration" / "CF_JOBS.json")["jobs"]:
            o = cl.get(f"{j['arm']}__{j['root']}", {}).get("outcome")
            if o and o != "NOT_RUN_BUDGET":
                ep[f"{j['root']}::{j['choice']}"] = o
    exe = set(man["permutation"])
    target = {s: None for s in (0, 1, 2)}
    res, curves = collections.defaultdict(dict), {}
    for arm in ARMS:
        for s, a in sorted(A[arm].items()):
            cov, fa = _val_curves(vr[f"P13-{arm}-s{s}"], a["tau"])
            if arm == "K-B":
                target[s] = {"coverage": cov[min(cov, key=lambda t: abs(t - a["threshold"]))], "false_admission": fa[min(fa, key=lambda t: abs(t - a["threshold"]))]}
            thr = {"historical": a["threshold"],
                   "coverage_matched": min(cov, key=lambda t: (abs(cov[t] - target[s]["coverage"]), t)),
                   "false_admission_matched": max([t for t in fa if fa[t] <= target[s]["false_admission"] + 1e-12] or [max(GRID)], key=lambda t: (cov[t], -t))}
            for name, t in thr.items():
                ch = {k: _choose(a["roots"][k]["rows"], a["tau"], t) for k in exe}
                out = {k: ("ABSTAIN" if q == "ABSTAIN" else ep.get(f"{k}::{q}") or "UNKNOWN_NOT_EXECUTED") for k, q in ch.items()}
                res[(arm, name)][s] = {"threshold": t, "val_coverage": cov[min(cov, key=lambda u: abs(u - t))], "choices": ch, "outcomes": out}
            if s == 0:
                curves[arm] = [{"t": float(t), "coverage": float(np.mean([_choose(a["roots"][k]["rows"], a["tau"], t) != "ABSTAIN" for k in exe])),
                                "label_correct_given_admitted": float(np.mean([y.get(q) == 1 for k in exe for q in [_choose(a["roots"][k]["rows"], a["tau"], t)] if q != "ABSTAIN"] or [np.nan]))}
                               for t in GRID[::5]]
    summ = {}
    for (arm, name), d in res.items():
        ks = sorted(exe)
        succ = {k: float(np.mean([d[s]["outcomes"][k] == "SUCCESS" for s in d])) for k in ks}
        unk = sum(d[s]["outcomes"][k] == "UNKNOWN_NOT_EXECUTED" for s in d for k in ks)
        lab = {k: float(np.mean([y.get(d[s]["choices"][k]) == 1 for s in d])) for k in ks}
        summ[f"{arm}|{name}"] = {"thresholds": [d[s]["threshold"] for s in sorted(d)], "val_coverage": [d[s]["val_coverage"] for s in sorted(d)],
                                 "test_admission": float(np.mean([d[s]["choices"][k] != "ABSTAIN" for s in d for k in ks])),
                                 "executed_success_lower_bound": float(np.mean(list(succ.values()))), "unknown_not_executed_choices": int(unk),
                                 "label_correct_root_rate": float(np.mean(list(lab.values()))), "_succ": succ, "_lab": lab}
    con = {}
    for name in ("historical", "coverage_matched", "false_admission_matched"):
        for arm in ARMS[1:]:
            a, b = summ[f"K-B|{name}"], summ[f"{arm}|{name}"]
            con[f"{name}|K-B-{arm}"] = {"label_correct": paired(a["_lab"], b["_lab"]), "executed_success_lower_bound": paired(a["_succ"], b["_succ"]),
                                         "unknown_choices_other": b["unknown_not_executed_choices"]}
    for v in summ.values():
        v.pop("_succ"), v.pop("_lab")
    out = {"kb_validation_targets": target, "summary": summ, "contrasts": con, "coverage_risk_test_s0": curves,
           "note": "EXPLORATORY post-hoc; thresholds from validation only; executed success counts only exact (root, repair) episodes, UNKNOWN otherwise"}
    cf.write_json(OUT / "calibration" / "MATCHED_ADMISSION.json", out)
    return out


def cf_jobs() -> None:
    """Frozen list of matched-threshold choices of the core arms never executed in P13 (identical strict TOP1 protocol and episode
    identity 'c' + stable_hash(root::choice)); deterministic sorted order, dealt round-robin to 4 workers."""
    import p13_factors as f13
    snap, P, y, st, cost = f13._p13_blind()
    A = f13._by_arm(snap)
    d = rd(OUT / "calibration" / "MATCHED_ADMISSION.json")
    man = rd(P13 / "p13_5" / "EXEC_JOBS.json")
    done = {f"{j['root']}::{j['choice']}" for j in man["jobs"]}
    plan = {j["root"]: j["plan"] for j in man["jobs"]}
    need = set()
    for name in ("coverage_matched", "false_admission_matched"):
        for arm in ("K-B", "K-C", "A", "SF", "B-F2", "B-F3pm", "B-F4", "B-F5spm"):
            for s, t in zip(sorted(A[arm]), d["summary"][f"{arm}|{name}"]["thresholds"]):
                for k in man["permutation"]:
                    q = _choose(A[arm][s]["roots"][k]["rows"], A[arm][s]["tau"], t)
                    if q != "ABSTAIN" and f"{k}::{q}" not in done:
                        need.add((k, q))
    seqs = {c["query"]: c["sequence"] for k in P for c in P[k]["items"] if c["kind"] == "ORDERED_TEACHER"}
    jobs = [{"arm": "c" + cf.stable_hash(f"{k}::{q}")[7:19], "root": k, "choice": q, "ranked": [seqs[q]], "plan": plan[k], "worker": i % 4}
            for i, (k, q) in enumerate(sorted(need))]
    cf.write_json(OUT / "calibration" / "CF_JOBS.json", {"jobs": jobs, "hash": cf.stable_hash(jobs)})


def cf_worker(w, cap) -> None:
    import p7_oneshot as po
    po.CAPS.update({"cpu_s": cap, "wall_s": 40000.0, "episode_cpu_s": 180.0, "episode_wall_s": 600.0, "max_episodes": 10 ** 6, "max_rank": 5})
    for j in (j for j in rd(OUT / "calibration" / "CF_JOBS.json")["jobs"] if j["worker"] == w):
        po.run_episodes(OUT / "calibration" / "episodes" / f"w{w}", j["plan"], [j], lambda m: open(OUT / "calibration" / f"cf_w{w}.log", "a").write(m + "\n"))


def natural_diag() -> dict:
    """Synthetic unconditioned (natural) stream and the challenge set from frozen P13 predictions: original-feasibility discrimination,
    feasible / infeasible recall at 0.5, Brier, NLL, 5-bin reliability with Wilson CIs, and joint four-bit NLL by outcome pattern.
    Admission on feasible originals = does the TOP1 rule pick the empty repair (correct) or a relocation / abstain."""
    import p10b_dataset as pd
    import p13_factors as f13
    import p13_pipeline as pp
    snap, P, y, st, cost = f13._p13_blind()
    A = f13._by_arm(snap)
    rec = {}
    for d in sorted(pp.HOLD.glob("*_b*")):
        rec |= pp._sealed(d)
    dl = pd.d_labels({"roots": {k: r for k, r in P.items()}}, rec)
    tg = rd(P13 / "p13_4" / "TARGETED.json")["per_root"]["four"]
    out = {}
    for stream in ("natural", "blind"):
        ks = [k for k in P if P[k]["stream"] == stream and dl[k]["y0"] is not None]
        y0 = {k: dl[k]["y0"] for k in ks}
        res = {"N": len(ks), "feasible": int(sum(y0.values()))}
        prob = {}
        for arm in ARMS:
            prob[arm] = {k: float(np.mean([A[arm][s]["roots"][k]["marginals"][f"seq:{k}:empty"] for s in A[arm]])) for k in ks}
        for arm in ("D", "D-pairless"):
            lam = snap["baselines"][f"{arm}_lambda_B"]
            ds = [x for x in snap["d"].values() if x["arm"] == arm and x["lambda_B"] == lam]
            prob[arm] = {k: float(np.mean([x["roots"][k]["p_feasible"] for x in ds])) for k in ks}
        for arm, pk in prob.items():
            ps, ys = np.array([pk[k] for k in ks]), np.array([y0[k] for k in ks])
            pos, neg = ps[ys == 1], ps[ys == 0]
            auc = float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg])) if len(pos) and len(neg) else None
            bins = []
            for lo in np.linspace(0, 0.8, 5):
                m = (ps >= lo) & (ps < lo + 0.2 + (1e-9 if lo >= 0.8 else 0))
                bins.append({"bin": [round(float(lo), 1), round(float(lo + 0.2), 1)], "n": int(m.sum()), "mean_p": float(ps[m].mean()) if m.any() else None,
                             "observed": float(ys[m].mean()) if m.any() else None, "wilson95": _wilson(int(ys[m].sum()), int(m.sum()))})
            empty = None
            if arm in ARMS and pos.size:
                empty = float(np.mean([a["roots"][k]["top1"] == f"seq:{k}:empty" for s, a in A[arm].items() for k in ks if y0[k] == 1]))
            res[arm] = {"auroc": auc, "feasible_recall": float((pos >= 0.5).mean()) if pos.size else None, "infeasible_recall": float((neg < 0.5).mean()) if neg.size else None,
                        "balanced_accuracy": float(((pos >= 0.5).mean() + (neg < 0.5).mean()) / 2) if pos.size and neg.size else None,
                        "brier": float(np.mean((ps - ys) ** 2)), "nll": float(np.mean(-np.log(np.clip(np.where(ys == 1, ps, 1 - ps), 1e-12, 1)))),
                        "mean_p_feasible_on_feasible": float(pos.mean()) if pos.size else None, "reliability": bins,
                        "TOP1_empty_on_feasible_originals": empty}
        pat = collections.defaultdict(lambda: collections.defaultdict(list))
        for k, f in tg.items():
            if P.get(k, {}).get("stream") != stream:
                continue
            for arm in ARMS:
                qs = [t["query"] for t in P[k]["items"] if t["token"] in ("", "edit:A", "edit:B", "edit:A+B")]
                order = {t["token"]: t["query"] for t in P[k]["items"]}
                qs = [order[x] for x in ("", "edit:A", "edit:B", "edit:A+B")]
                pat[arm][f["pattern"]].append(float(np.mean([f13._nll_joint(A[arm][s]["roots"][k], qs, f["y"]) for s in A[arm]])))
        res["joint4_nll_by_pattern"] = {arm: {p: {"n": len(v), "mean": float(np.mean(v))} for p, v in d.items()} for arm, d in pat.items()}
        out[stream] = res
    cf.write_json(OUT / "calibration" / "NATURAL_DIAG.json", out)
    return out


def cf_continue(extra=300.0) -> None:
    """Never-attempted NOT_RUN_BUDGET placeholders are logged and removed; the same frozen order resumes (per worker)."""
    import json as _j
    for f in sorted((OUT / "calibration" / "episodes").glob("w*/ledger.json")):
        led = rd(f)
        rm = [k for k, v in led["episodes"].items() if v.get("outcome") == "NOT_RUN_BUDGET"]
        if rm:
            led["episodes"] = {k: v for k, v in led["episodes"].items() if k not in rm}
            f.write_text(_j.dumps(led, indent=1, default=float))
            cf.write_json(OUT / "calibration" / f"cf_removed_{f.parent.name}.json", {"removed": rm})
            cf_worker(int(f.parent.name[1:]), led["cpu_s"] + extra)


# ------------------------------------------------------------------ P14-D2 / D3: method runs (identical scenes, slots, index, planner, budget)
METHODS = ("D", "D-pairless", "geometry", "uninformed", "oracle")
EVAL_BUDGET = {"motion_checks": 120, "online_moves": 6, "target_checks": 16}


def _roots(split):
    import os
    os.environ["P10C_OUT"] = str(P13 / "models")
    import p13_pipeline as pp
    import p10b_dataset as pd
    if split == "dev":
        rs = {r["key"]: r for r in pp._prepared("trainval") if str(r["audit"].get("source", "")).startswith("P13")}
        dirs = sorted((pp.OUT / "data").glob("*_b*"))
    else:
        rs = {r["key"]: r for r in pp._prepared("test")}
        dirs = sorted(pp.HOLD.glob("*_b*"))
    P, D = {}, {}
    for d in dirs:
        plan = pp.rd(d / "plan.json")
        P |= plan["roots"]
        D |= pd.d_labels(plan, pp._sealed(d))
    return rs, P, D


def run_method(method, split, roots, out_name, lookup="combined", modal_only=False, online=True, budget=None) -> None:
    """One process per (method, variant): runs the search on every listed root, replays each found plan, writes one JSON."""
    import p14_d_search as ds
    rs, P, D = _roots(split)
    ms = ds.d_models(method == "D-pairless") if method in ("D", "D-pairless") else []
    res = {}
    for k in roots:
        cx = ds.Ctx(lookup=lookup, modal_only=modal_only, online=online, budget=budget or EVAL_BUDGET)
        ids = rs[k]["ids"]
        dl = D[k]
        orc = {ids.index(o): m for o, m in zip(dl["pool"], dl["mask"])} if dl.get("mask") else ({ids.index(o): 0 for o in dl["pool"]} if dl.get("y0") == 1 else None)
        g = ds.Guide("geometry" if method == "lookup-only" else method, rs[k]["R"], cx.robot, ms, orc)
        out = ds.search(cx, P[k], rs[k], g, key=f"p14/{split}/{method}/{k}")
        if out["found"]:
            out["replay"] = ds.replay(cx, P[k], out["plan"])
            moved = [s["object"] for s in out["plan"]["steps"]]
            union = {o for o, m in zip(dl["pool"], dl["mask"] or [0] * len(dl["pool"])) if m} if dl.get("mask") or dl.get("y0") == 1 else None
            out["unnecessary_moves"] = None if union is None else sum(o not in union for o in moved)
            out["blockers_displaced"] = None if union is None else sum(o in union for o in moved)
            out["plan"] = {k2: v for k2, v in out["plan"].items() if k2 != "records"} | {"n_records": len(out["plan"]["records"])}
        out |= {"family": P[k]["family"], "y0": dl.get("y0"), "union_mask": dl.get("mask"), "pool": dl.get("pool")}
        res[k] = out
    (OUT / "search").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "search" / f"{out_name}.json", res)
