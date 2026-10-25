"""P13 execution: P12 coverage diagnosis (P13-0), the budgeted P12 continuation and new strict TOP1 evaluation (P13-5).
Frozen P12 choices, episode identities and job order are never changed."""
from __future__ import annotations

import collections
from pathlib import Path

import numpy as np

import config as cf
import p12_closure as p12
from p13_pipeline import OUT, rd


def _p12_state():
    man, P = rd(p12.OUT / "p12_5" / "EXEC_JOBS.json"), p12.plans()
    led = {}
    for f in sorted((p12.OUT / "p12_5" / "episodes").glob("*/ledger.json")):
        led |= {k: v | {"_batch": f.parent.name} for k, v in rd(f)["episodes"].items()}
    return man, P, led


def coverage_diagnosis() -> dict:
    """Which P12 roots were fully executed and why: per-batch prefix property of the frozen job order, where each episode ran
    (batch pass vs ordered continuation), pre-outcome root features covered vs uncovered, and outcome / censoring rates by arm."""
    man, P, led = _p12_state()
    removed = set(rd(p12.OUT / "p12_5" / "continuation_removed_placeholders.json")["removed"])
    cont = {l.split()[1].rstrip(":") for l in (p12.OUT / "p12_5" / "episodes_continue.log").read_text().splitlines() if l.startswith("episode ")}
    st = {}
    for k in sorted(P):
        keys = [f"{j['arm']}__{k}" for j in man["jobs"] if j["root"] == k]
        ran = [x for x in keys if led.get(x, {}).get("outcome") not in (None, "NOT_RUN_BUDGET")]
        st[k] = {"jobs": len(keys), "ran": len(ran), "status": "COMPLETE" if len(ran) == len(keys) else "PARTIAL" if ran else "UNTOUCHED",
                 "batch": P[k]["batch"], "family": P[k]["family"], "via_continuation": sum(x in cont for x in keys),
                 "abstaining_arms": sum(1 for key, arms in man["arms"].items() if key == f"{k}::ABSTAIN" for _ in arms)}
    prefix = {}
    for b in sorted({v["batch"] for v in st.values()}):
        order = [k for k in sorted(P) if st[k]["batch"] == b]
        seq = [st[k]["status"] for k in order]
        first_gap = next((i for i, s in enumerate(seq) if s != "COMPLETE"), len(seq))
        prefix[str(b)] = {"roots": len(order), "complete": seq.count("COMPLETE"), "partial": seq.count("PARTIAL"), "untouched": seq.count("UNTOUCHED"),
                          "complete_is_prefix": all(s != "COMPLETE" for s in seq[first_gap:]), "first_incomplete_position": first_gap}
    cov = [k for k, v in st.items() if v["status"] == "COMPLETE"]
    unc = [k for k in st if k not in cov]
    feat = lambda ks, f: float(np.mean([f(k) for k in ks])) if ks else None  # noqa: E731
    out = {"roots": len(P), "complete": len(cov), "partial": sum(v["status"] == "PARTIAL" for v in st.values()),
           "untouched": sum(v["status"] == "UNTOUCHED" for v in st.values()), "per_batch": prefix,
           "continuation_episodes": len(cont), "removed_placeholders": len(removed),
           "pre_outcome_features": {"covered": {"X_share": feat(cov, lambda k: st[k]["family"] == "X_SWEEP_GATE"), "jobs": feat(cov, lambda k: st[k]["jobs"]),
                                                "abstaining_arms": feat(cov, lambda k: st[k]["abstaining_arms"])},
                                    "uncovered": {"X_share": feat(unc, lambda k: st[k]["family"] == "X_SWEEP_GATE"), "jobs": feat(unc, lambda k: st[k]["jobs"]),
                                                  "abstaining_arms": feat(unc, lambda k: st[k]["abstaining_arms"])}},
           "episode_outcomes": dict(collections.Counter(v.get("outcome") for v in led.values())),
           "episode_cpu_by_outcome": {o: float(np.mean([v["cpu_s"] for v in led.values() if v.get("outcome") == o]))
                                      for o in {v.get("outcome") for v in led.values()} if o not in ("NOT_RUN_BUDGET", "ABSTAINED")},
           "batch_guard_cpu_s": {g.stem: rd(g)["cpu_s"] for g in sorted((p12.OUT / "guards").glob("p12_5_exec_*.json"))},
           "untracked_killed_launch": "one launch < 1 min without a guard record (disclosed in 0056); its CPU is not inferred and nothing it produced is counted",
           "per_root": st}
    cf.write_json(OUT / "p13_0" / "P12_EXEC_COVERAGE.json", out)
    return out


# ------------------------------------------------------------------ P13-5a: P12 continuation (frozen jobs, frozen order; supplementary)
CONT = OUT / "p12_continuation"
CONT_CAP = {"batch1": 2000.0, "batch3": 3500.0, "batch4": 3500.0}      # 9,000 CPU-s, split by untouched roots (7 / 12 / 12)


def p12_continue(batch) -> None:
    """Run every frozen P12 job of the roots of `batch` that have no executed episode, in the frozen P12 job order, with the identical
    episode identity (arm hash, ranking); outputs only under runs/p13. Identical protocol (strict TOP1, 180 CPU-s / 600 s, no fallback)."""
    import p7_oneshot as po
    man, P, led = _p12_state()
    done = {k for k, v in led.items() if v.get("outcome") not in (None, "NOT_RUN_BUDGET")}
    js = [j for j in man["jobs"] if P[j["root"]]["batch"] == int(batch[5:]) and f"{j['arm']}__{j['root']}" not in done]
    po.CAPS.update({"cpu_s": CONT_CAP[batch], "wall_s": 60000.0, "episode_cpu_s": 180.0, "episode_wall_s": 600.0, "max_episodes": 10 ** 6, "max_rank": 5})
    po.run_episodes(CONT / "episodes" / batch, p12.HOLD / batch / "plan.json", js, lambda m: open(CONT / f"episodes_{batch}.log", "a").write(m + "\n"))


def p12_eval80() -> dict:
    """Final P12 strict-TOP1 table over all 80 roots: P12 ledgers + continuation ledgers; unresolved / not-run = failure (conservative)
    and an adjudicated-only sensitivity; by family, CPU per root and per success."""
    man, P, led = _p12_state()
    for f in sorted((CONT / "episodes").glob("*/ledger.json")):
        led |= {k: v for k, v in rd(f)["episodes"].items() if v.get("outcome") != "NOT_RUN_BUDGET"}
    jm = {f"{j['root']}::{j['choice']}": j for j in man["jobs"]}
    per, cpu, ran = (collections.defaultdict(lambda: collections.defaultdict(list)) for _ in range(3))
    for key, arms in man["arms"].items():
        k, ch = key.split("::", 1)
        e = led.get(f"{jm[key]['arm']}__{k}") if key in jm else None
        for a in arms:
            arm = a if a in ("geometry", "G+M") else a.split("-s")[0].removeprefix("F-")
            per[arm][k].append(float(bool(e) and e.get("outcome") == "SUCCESS"))
            cpu[arm][k].append((e or {}).get("cpu_s", 0.0))
            ran[arm][k].append(ch in ("ABSTAIN", "NOT_RUN") or (e is not None and e.get("outcome") not in (None, "NOT_RUN_BUDGET", "UNRESOLVED_CENSORED")))
    succ = {a: {k: float(np.mean(v)) for k, v in d.items()} for a, d in per.items()}
    full = [k for k in P if all(all(ran[a][k]) for a in ran if k in ran[a])]
    keys = lambda k: [f"{jm[key]['arm']}__{k}" for key in man["arms"] if key.startswith(k + "::") and key in jm]  # noqa: E731
    ex = [k for k in P if all(x in led for x in keys(k))]
    def con(a, b, ks):
        d = [succ[a][k] - succ[b][k] for k in ks]
        p, pos, neg, _ = p12._sign(d)
        return {"roots": len(d), "mean": float(np.mean(d)), "ci95": p12._boot(d), "sign_p": p, "a_better": pos, "b_better": neg}
    out = {"roots_with_every_episode_attempted": len(ex), "roots_without_censoring": len(full),
           "success_all80_conservative": {a: float(np.mean([d[k] for k in P])) for a, d in succ.items()},
           "success_attempted_only": {a: float(np.mean([d[k] for k in ex])) for a, d in succ.items()},
           "by_family": {f: {a: float(np.mean([d[k] for k in P if P[k]["family"] == f])) for a, d in succ.items()} for f in sorted({r["family"] for r in P.values()})},
           "contrasts_all80": {f"{a}-{b}": con(a, b, list(P)) for a, b in (("K-B", "A"), ("K-B", "SF"), ("K-C", "K-B"), ("K-B", "geometry"), ("K-B", "G+M"))},
           "cpu_per_root": {a: float(np.mean([np.mean(v) for v in d.values()])) for a, d in cpu.items()},
           "cpu_per_success": {a: float(sum(np.mean(v) for v in cpu[a].values()) / max(1e-9, sum(succ[a].values()))) for a in cpu},
           "outcomes": dict(collections.Counter(v.get("outcome") for v in led.values()))}
    cf.write_json(OUT / "p13_5" / "P12_FINAL80.json", out) if (OUT / "p13_5").mkdir(parents=True, exist_ok=True) is None else None
    return out


# ------------------------------------------------------------------ P13-5b: new strict TOP1 execution on the P13 blind sets
EXE = OUT / "p13_5"
EXEC_ARMS = ("K-B", "K-C", "A", "SF", "B-F2", "B-F3pm", "B-F4", "B-F5spm")
WORKERS = 8


def exec_jobs() -> None:
    """Frozen job list from the frozen P13 TOP1 choices (every seed; one episode per distinct (root, repair)), geometry-only TOP1 and the
    planner-assisted G+M ranking; roots in one random permutation (seed 13) dealt round-robin to WORKERS (outcome-blind coverage)."""
    import geometry as ge
    import p10d_execute as px
    import p13_pipeline as pp
    snap = rd(pp.HOLD / "PREDICTIONS_FROZEN.json")
    drop = set(rd(OUT / "DEDUP.json")["blind_duplicate_excluded"])
    P = {k: r for d in sorted(pp.HOLD.glob("*_b*")) for k, r in rd(d / "plan.json")["roots"].items() if k not in drop}
    exe = sorted(k for k, r in P.items() if any(it["kind"] == "ORDERED_TEACHER" and it["sequence"] for it in r["items"]))
    cfg = cf.load_config("config.toml")
    robot = ge.make_robot(cfg)
    perm = [exe[i] for i in np.random.default_rng(13).permutation(len(exe))]
    jobs, arms = [], collections.defaultdict(list)
    for w, k in enumerate(perm):
        seqs = {c["query"]: c["sequence"] for c in P[k]["items"] if c["kind"] == "ORDERED_TEACHER"}
        plan = str(next(d for d in pp.HOLD.glob("*_b*") if k in rd(d / "plan.json")["roots"]) / "plan.json")
        ch = {n: a["roots"][k]["top1"] for n, a in snap["arms"].items() if a["arm"] in EXEC_ARMS}
        ch["geometry"] = snap["baselines"]["geometry_top1"][k]
        seen = set()
        for arm, c in ch.items():
            arms[f"{k}::{c}"].append(arm)
            if c not in ("ABSTAIN", "NOT_RUN") and c not in seen:
                seen.add(c)
                jobs.append({"arm": "c" + cf.stable_hash(f"{k}::{c}")[7:19], "root": k, "ranked": [seqs[c]], "choice": c, "worker": w % WORKERS, "plan": plan})
        jobs.append({"arm": "gm" + cf.stable_hash(k)[7:17], "root": k, "ranked": px.gm_rank(cfg, robot, P[k]), "choice": "GM", "worker": w % WORKERS, "plan": plan})
        arms[f"{k}::GM"].append("G+M")
    man = {"jobs": jobs, "arms": arms, "permutation": perm, "predictions": snap["hash"], "workers": WORKERS,
           "protocol": "strict TOP1_COMMIT (one episode per distinct (root, repair), 180 CPU-s / 600 s, no fallback, SAFE_RETREAT); G+M separate"}
    man["hash"] = cf.stable_hash(man)
    EXE.mkdir(parents=True, exist_ok=True)
    cf.write_json(EXE / "EXEC_JOBS.json", man)


def exec_worker(w, cap) -> None:
    """One worker: its jobs strictly in the frozen permutation order, one shared ledger (cap on the ledger's executed CPU)."""
    import p7_oneshot as po
    man = rd(EXE / "EXEC_JOBS.json")
    po.CAPS.update({"cpu_s": cap, "wall_s": 80000.0, "episode_cpu_s": 180.0, "episode_wall_s": 600.0, "max_episodes": 10 ** 6, "max_rank": 5})
    for j in (j for j in man["jobs"] if j["worker"] == w):
        po.run_episodes(EXE / "episodes" / f"w{w}", j["plan"], [j], lambda m: open(EXE / f"episodes_w{w}.log", "a").write(m + "\n"))


def exec_eval() -> dict:
    """Strict TOP1 executed outcomes on roots whose every frozen job ran (coverage fixed by the frozen permutation); success by arm /
    family / stream, relocations and displaced objects on success, CPU, abstention, and failure attribution from the chosen query's
    teacher label (CERTIFIED kind: ORDER_FIRST_ACTION = wrong order, TARGET_PICK = necessary obstacle left / wrong blocker, empty chosen on
    an infeasible original = wrong feasibility) and the episode outcome (censoring, no relocation witness, target unresolved)."""
    import p13_factors as f13
    man = rd(EXE / "EXEC_JOBS.json")
    snap, P, y, st, cost = f13._p13_blind()
    led = {}
    for f in sorted((EXE / "episodes").glob("*/ledger.json")):
        led |= {k: v for k, v in rd(f)["episodes"].items() if v.get("outcome") != "NOT_RUN_BUDGET"}
    jm = {f"{j['root']}::{j['choice']}": j for j in man["jobs"]}
    cov = [k for k in man["permutation"] if all(f"{jm[key]['arm']}__{k}" in led for key in man["arms"] if key.startswith(k + "::") and key in jm)]
    stat = {q: x for q, x in st.items()}
    per, cpu, mv, why = (collections.defaultdict(lambda: collections.defaultdict(list)) for _ in range(4))
    for key, arms in man["arms"].items():
        k, ch = key.split("::", 1)
        if k not in cov:
            continue
        e = led.get(f"{jm[key]['arm']}__{k}") if key in jm else None
        rp = EXE / "episodes" / f"w{jm[key]['worker']}" / f"{jm[key]['arm']}__{k}" / "result.json" if key in jm else None
        res = rd(rp) if rp is not None and rp.exists() else {}
        for a in arms:
            arm = a if a in ("geometry", "G+M") else a.split("-s")[0].removeprefix("P13-")
            ok = bool(e) and e.get("outcome") == "SUCCESS"
            per[arm][k].append(float(ok))
            cpu[arm][k].append((e or {}).get("cpu_s", 0.0))
            if ok:
                mv[arm][k].append(res.get("moves") or 0)
            if ch in ("ABSTAIN", "NOT_RUN"):
                why[arm]["ABSTAIN"].append(1)
            elif not ok:
                s = stat.get(ch, "UNLABELLED") if ch != "GM" else "GM"
                tag = {"UNRESOLVED_CENSORED": "planner censoring", "NO_REPAIR_WITNESS_WITHIN_BUDGET": "relocation not executable within budget",
                       "TARGET_UNRESOLVED": "target unresolved after repair", "TARGET_CERTIFIED_INFEASIBLE": "target certified infeasible after repair"}.get(e.get("outcome"), e.get("outcome"))
                if s == "CERTIFIED_INFEASIBLE":
                    tag = "chose a CERTIFIED-infeasible repair"
                    if ch.endswith(":empty"):
                        tag += " (empty repair: wrong original feasibility)"
                why[arm][tag].append(1)
            else:
                why[arm]["SUCCESS"].append(1)
    succ = {a: {k: float(np.mean(v)) for k, v in d.items()} for a, d in per.items()}
    def con(a, b, ks):
        ks = [k for k in ks if k in succ[a] and k in succ[b]]
        d = [succ[a][k] - succ[b][k] for k in ks]
        p, pos, neg, _ = p12._sign(d)
        return {"roots": len(d), "mean": float(np.mean(d)) if d else None, "ci95": p12._boot(d), "sign_p": p, "a_better": pos, "b_better": neg}
    fam = lambda k: P[k]["family"]  # noqa: E731
    out = {"coverage": {"executable_roots": len(man["permutation"]), "roots_fully_executed": len(cov), "jobs": len(man["jobs"]),
                        "episodes_executed": len(led)},
           "success": {a: float(np.mean(list(d.values()))) for a, d in succ.items()},
           "by_family": {f: {a: float(np.mean([d[k] for k in cov if fam(k) == f and k in d])) for a, d in succ.items()} for f in sorted({fam(k) for k in cov})},
           "by_stream": {s: {a: float(np.mean([d[k] for k in cov if P[k]["stream"] == s and k in d])) for a, d in succ.items()}
                         for s in ("blind", "natural") if any(P[k]["stream"] == s for k in cov)},
           "contrasts": {f"{a}-{b}": con(a, b, cov) for a, b in (("K-B", "A"), ("K-B", "SF"), ("K-C", "K-B"), ("K-B", "geometry"), ("K-B", "B-F2"),
                                                                   ("K-B", "B-F3pm"), ("K-B", "B-F4"), ("K-B", "B-F5spm"), ("K-B", "G+M"))},
           "contrasts_reversed_order_roots": {f"{a}-{b}": con(a, b, [k for k in cov if fam(k) in ("ORD_CHAIN", "OMIT_OPT")])
                                              for a, b in (("K-B", "B-F2"), ("K-B", "A"), ("K-C", "K-B"), ("K-B", "geometry"))},
           "moves_on_success": {a: float(np.mean([x for v in d.values() for x in v])) if d else None for a, d in mv.items()},
           "cpu_per_root": {a: float(np.mean([np.mean(v) for v in d.values()])) for a, d in cpu.items()},
           "outcomes_and_failure_attribution": {a: {t: len(v) for t, v in d.items()} for a, d in why.items()}}
    cf.write_json(EXE / "EXEC_RESULTS.json", out)
    return out
