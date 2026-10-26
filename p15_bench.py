"""P15 ledger (runs/p15/guards, contract caps, one guarded OS process per job), P15-0 source / evidence audit, benchmark runners, summaries,
B closure and figures. P10-P14 artifacts are read-only; every P15 output is a new versioned file under runs/p15."""
from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path

import numpy as np

import config as cf

OUT = Path("runs/p15")
P14 = Path("runs/p14")
CAPS = {"audit": 3000.0, "retarget_probe": 8000.0, "retarget_train": 10000.0, "retarget_teacher": 15000.0, "index": 6000.0,
        "search_dev": 8000.0, "retro24": 27000.0, "prospective": 38000.0, "ablation": 12000.0, "b_diag": 3000.0, "regression": 3000.0}
JOB = {"cpu_s": 3000.0, "wall_s": 40000.0}


def rd(p):
    return json.loads(Path(p).read_text())


def sha(p) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def spent(cat=None) -> float:
    return sum(g["cpu_s"] for g in (rd(p) for p in (OUT / "guards").glob("*.json")) if cat is None or g["category"] == cat)


def job(name, call, cpu, module="p15_bench", category="audit", wall=None) -> dict:
    """One guarded child per OS process (never threads in one parent), charged to one P15 category; refuses past the cap."""
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
    cf.write_json(OUT / f"P15_{stage}_GATE.json", {"stage": f"P15-{stage}", **kw, "spend": {c: round(spent(c), 1) for c in CAPS}})


# ------------------------------------------------------------------ P15-0 audit
def audit() -> dict:
    """Recompute P14 D3 (identical-cohort) and matched-admission tables from stored JSON; verify P14 manifest hashes; claim matrix."""
    import p14_audit as pa
    m = rd(P14 / "P14_FINAL_MANIFEST.json")
    mism = [p for sec in ("P14_A", "P14_D", "sources", "figures") for p, h in m[sec].items() if sha(p) != h]
    runs = {k: rd(P14 / "search" / f"EVAL_{k}.json") for k in ("D", "D-pairless", "geometry", "uninformed", "oracle")}
    common = sorted(set.intersection(*[set(v) for v in runs.values()]))
    ok = lambda v: bool(v.get("found") and (v.get("replay") or {}).get("success"))  # noqa: E731
    d3 = {k: {"success": sum(ok(v[r]) for r in common), "n": len(common), "cpu_mean": float(np.mean([v[r]["cpu_s"] for r in common])),
              "roots_completed": len(v)} for k, v in runs.items()}
    rep = rd(P14 / "eval" / "D3_SUMMARY.json")["methods"]
    d3_agree = all(abs(d3[k]["success"] / d3[k]["n"] - rep[k]["success"]) < 1e-12 for k in d3)
    ma = rd(P14 / "calibration" / "MATCHED_ADMISSION.json")["summary"]
    adm = {k: {"val_coverage_mean": float(np.mean(v["val_coverage"])), "test_admission": v["test_admission"], "executed_success": v["executed_success_lower_bound"]}
           for k, v in ma.items() if k.split("|")[1] == "coverage_matched"}
    claims = {
        "first_certified_witness_only": "p14_d_search._move returns at the first CLEAR candidate: alternative modes / terminal q are dropped; minimum travel over modes NOT established",
        "target_unknown_as_none": "p14_d_search._target returns None for any non-VERIFIED planner outcome: UNKNOWN collapsed with failure; depth_exhaustive is not a physical proof",
        "restricted_graph": "movers from ORDERED_TEACHER tokens, move-once, K slots, depth <= 3: a restricted finite graph",
        "root_variant_goal": "p14 root_variant kept R.goal and the original visual tokens; the physical probe used another destination: unmatched comparison",
        "unnecessary_moves": "counted moves outside the ORIGINAL blocker union; not redundant moves",
        "no_similarity_threshold": "lookup ranks only; no validated minimum-similarity cut",
        "validation_vs_test_admission": "coverage matched on VALIDATION; test admissions differ (see table)"}
    out = {"p14_manifest_mismatches": mism, "replay_fidelity_sample": rd(P14 / "lookup" / "PROVENANCE_AUDIT.json")["trace_fidelity_sample"],
           "d3_common_roots": common, "d3_recomputed": d3, "d3_matches_report": d3_agree, "coverage_matched_admission": adm,
           "index": {"entries": len(rd(P14 / "lookup" / "INDEX.json")["entries"]), "excluded_roots": len(rd(P14 / "eval_roster.json")["excluded_roots"])},
           "p14_roster_primary": rd(P14 / "P14_PREREG.json")["D_track"]["roster_primary"], "claims": claims,
           "historical_hashes": {p: sha(p) for p in ("runs/p14/P14_FINAL_MANIFEST.json", "runs/p14/P14_PREREG.json", "runs/p14/lookup/INDEX.json",
                                                     "runs/p14/eval/D3_SUMMARY.json", "runs/p14/calibration/MATCHED_ADMISSION.json")},
           "p14_spend": {c: round(pa.spent(c), 1) for c in pa.CAPS}}
    (OUT / "audit").mkdir(parents=True, exist_ok=True)
    cf.write_json(OUT / "audit" / "P15_0_AUDIT.json", out)
    return out
