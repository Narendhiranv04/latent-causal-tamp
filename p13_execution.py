"""P13 execution: P12 coverage diagnosis (P13-0), the budgeted P12 continuation and new strict TOP1 evaluation (P13-5).
Frozen P12 choices, episode identities and job order are never changed."""
from __future__ import annotations

import collections

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
