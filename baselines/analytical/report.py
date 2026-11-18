"""Per-run table: verified outcomes (benchmark.py evaluate results + summarize) and per-root search cost from the stats files.

    python3 -m baselines.analytical.report DIR DOM      -> DIR/REPORT_DOM.md and .json (every DIR/<run>/ with predictions_DOM.jsonl)"""
from __future__ import annotations

import collections
import json
import statistics as stt
import sys
from pathlib import Path


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if Path(p).exists() else []


def q(v, f):
    v = sorted(v)
    return v[min(len(v) - 1, int(f * len(v)))] if v else None


def main(d, dom):
    d, rows = Path(d), []
    for rd in sorted(p.parent for p in d.glob(f"*/predictions_{dom}.jsonl")):
        P, R = jl(rd / f"predictions_{dom}.jsonl"), jl(rd / f"predictions_{dom}_results.jsonl")
        cut = int(rd.name.split("_b")[-1].split("_cut")[0]) if "_cut" in rd.name else None
        S = jl(rd / f"stats_{dom}.jsonl") or jl(rd.with_name(rd.name.split("_cut")[0].rsplit("_b", 1)[0] + "_b" + rd.name.split("_cut")[-1])
                                                 / f"stats_{dom}.jsonl")
        summ = json.loads((rd / f"SUMMARY_{dom}.json").read_text()) if (rd / f"SUMMARY_{dom}.json").exists() else {}
        sm = next(iter(summ.values()), {})
        cpu = [min(x["phys"]["cpu_s"], cut) if cut else x["phys"]["cpu_s"] for x in S]
        mean = lambda k: round(stt.mean(x["phys"].get(k, 0) for x in S), 2) if S else None  # noqa: E731
        rows.append({"run": rd.name, "n": len(P), "decisions": dict(collections.Counter(x["decision"] for x in P)),
                     "outcomes": dict(collections.Counter(x["outcome"] for x in R)),
                     "termination": dict(collections.Counter(x["termination"] for x in P)),
                     "task_rate_ci": (sm.get("task") or {}).get("rate_ci"), "task_by_K": {k: v["rate_ci"][0] for k, v in (sm.get("task_by_K") or {}).items()},
                     "attempted": sm.get("attempted_repair"),
                     "cost_per_root": {"cpu_mean_s": round(stt.mean(cpu), 1) if cpu else None, "cpu_median_s": q(cpu, 0.5), "cpu_p90_s": q(cpu, 0.9),
                                       "physical_calls": mean("physical_calls"), "transition_calls": mean("transition_calls"),
                                       "transition_cache_hits": mean("transition_cache_hits"), "connector_calls": mean("connector_calls"),
                                       "y_calls": mean("y_calls"), "y_cache_hits": mean("y_cache_hits"), "ref_plan_calls": mean("ref_plan_calls"),
                                       "capped_calls": mean("capped_calls"), "wall_mean_s": mean("wall_s")}})
    md = [f"| run ({dom}) | n | decisions | verified outcomes | Task % [95% CI] | by K | CPU mean / median / p90 s | phys calls | transitions | connector | Y | ref plans |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        c = r["cost_per_root"]
        md.append(f"| {r['run']} | {r['n']} | {r['decisions']} | {r['outcomes']} | {r['task_rate_ci']} | {r['task_by_K']} | "
                  f"{c['cpu_mean_s']} / {c['cpu_median_s']} / {c['cpu_p90_s']} | {c['physical_calls']} | {c['transition_calls']} | "
                  f"{c['connector_calls']} | {c['y_calls']} | {c['ref_plan_calls']} |")
    md.append("\nCPU is capped at the cut for `_cut` rows; the call columns of `_cut` rows are those of the full source run (an upper bound).")
    (d / f"REPORT_{dom}.json").write_text(json.dumps(rows, indent=1))
    (d / f"REPORT_{dom}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main(*sys.argv[1:3])
