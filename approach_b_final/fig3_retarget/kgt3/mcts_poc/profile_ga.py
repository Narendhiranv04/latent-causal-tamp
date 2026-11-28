#!/usr/bin/env python3
"""GA time profile on DEV roots (exclusive wall per stage, in-process wrappers active only inside planners.ga; planners file untouched).
Stages: proposals (cVAE S1) | assign (construct.assignments) | y_view / y_net / y_post (Y_global readouts) | x_view / x_net / x_post (marginal
X + p11 readouts) | rebase (canonical scenes) | need (Scores bookkeeping) | requests | dp (grouped subset DP incl. cost lookups) |
short (short_options bookkeeping) | ranking_other (residual inside ga: sorting, xproxy, retention, hashing, per-size loops).
    $PYG profile_ga.py ROSTER.jsonl CONFIG.json OUT.jsonl [--horizon 180] [--shard i/n]"""
from __future__ import annotations

import argparse, collections, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]
import anytime as AT  # noqa: E402
import compose as CP  # noqa: E402
import construct as CO  # noqa: E402
import mcts_ga as MG  # noqa: E402
import planners as PL  # noqa: E402


class Prof:
    def __init__(self):
        self.on, self.stack, self.ex, self.n = False, [], collections.Counter(), collections.Counter()

    def wrap(self, name, fn, ctx=False, materialize=False):
        P = self

        def w(*a, **k):
            if not P.on:
                return fn(*a, **k)
            lab = name
            if ctx:                                                      # view / net attributed to the enclosing X or Y readout
                outer = next((s[0] for s in reversed(P.stack) if s[0] in ("x", "y")), "x")
                lab = f"{outer}_{name}"
            t = time.perf_counter()
            P.stack.append([lab, t, 0.0])
            try:
                r = fn(*a, **k)
                return list(r) if materialize else r
            finally:
                lab_, t0, child = P.stack.pop()
                d = time.perf_counter() - t0
                P.ex[lab_] += d - child; P.n[lab_] += 1
                if P.stack:
                    P.stack[-1][2] += d
        return w


def main(a):
    import r53
    import xy as XY
    cfg, fz, fzF, pcfg = AT.load_models(a.config)
    P = Prof()
    XY.make_view = P.wrap("view", XY.make_view, ctx=True)
    XY.collate = P.wrap("view", XY.collate, ctx=True)
    fz.net.coeffs = P.wrap("net", fz.net.coeffs, ctx=True)
    fz.score = P.wrap("x", fz.score)
    fz.y_global = P.wrap("y", fz.y_global)
    fz.proposals = P.wrap("proposals", fz.proposals)
    CO.assignments = P.wrap("assign", CO.assignments, materialize=True)
    CP.grouped_dp = P.wrap("dp", CP.grouped_dp)
    CP.requests = P.wrap("requests", CP.requests)
    CP.Scores.need = P.wrap("need", CP.Scores.need)
    PL.V.rebase = P.wrap("rebase", PL.V.rebase)
    PL.short_options = P.wrap("short", PL.short_options)
    orig = PL.ga

    def ga(*x, **k):
        P.on = True; P.ex.clear(); P.n.clear(); P.stack = [["ranking_other", time.perf_counter(), 0.0]]
        try:
            return orig(*x, **k)
        finally:
            lab, t0, child = P.stack.pop(); d = time.perf_counter() - t0
            P.ex[lab] += d - child; P.n[lab] += 1; P.on = False; P.total = d
    rows = AT.roster(a.roster)
    i_, n_ = (int(x) for x in a.shard.split("/"))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for k_, (rid, row) in enumerate(rows):
            if k_ % n_ != i_:
                continue
            fz.prop_mode = cfg["prop_GA"]
            with MG.search_as_ga(ga):
                o = PL.plan(fz, row, "GA", r53.floor_fn(fzF, row), {**pcfg, "wall_s": a.horizon})
            ex = {k: round(v, 4) for k, v in P.ex.items()}
            r = {"root_id": rid, "ga_wall_s": round(P.total, 3), "plan_wall_s": o["wall_s"], "floor_wall_s": o["floor_wall_s"], "mode": o["info"].get("mode"),
                 "stop": o["stop"], "exclusive_s": ex, "calls": dict(P.n), "per_size": o["info"].get("per_size"), "scores": o["info"].get("scores"),
                 "counters": o["counters"], "seq": o["seq"], "partition": o["partition"], "E": o["E"], "decision": o["decision"]}
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
            print(rid, r["mode"], r["ga_wall_s"], sorted(ex.items(), key=lambda t: -t[1])[:5], flush=True)


GROUPS = {"assignment_construction": ("assign", "proposals"), "xy_inference": ("x_view", "x_net", "x", "y_view", "y_net", "y", "rebase", "need"),
          "candidate_ranking_other": ("ranking_other", "short"), "subset_dp": ("dp", "requests")}


def summarize(paths, out):
    R = [json.loads(l) for p in paths for l in open(p)]
    tot = collections.Counter()
    for r in R:
        tot.update(r["exclusive_s"])
    T = sum(tot.values())
    grp = {g: round(sum(tot[k] for k in ks), 2) for g, ks in GROUPS.items()}
    s = {"n_roots": len(R), "ga_wall_total_s": round(sum(r["ga_wall_s"] for r in R), 2), "exclusive_total_s": round(T, 2),
         "by_stage_s": {k: round(v, 2) for k, v in tot.most_common()}, "by_stage_frac": {k: round(v / T, 4) for k, v in tot.most_common()},
         "by_group_s": grp, "by_group_frac": {g: round(v / T, 4) for g, v in grp.items()},
         "by_mode": {m: {"n": sum(r["mode"] == m for r in R), "ga_wall_mean_s": round(sum(r["ga_wall_s"] for r in R if r["mode"] == m) / max(1, sum(r["mode"] == m for r in R)), 2)}
                     for m in sorted({r["mode"] for r in R})},
         "per_root": [{"root_id": r["root_id"], "mode": r["mode"], "ga_wall_s": r["ga_wall_s"],
                       "group_frac": {g: round(sum(r["exclusive_s"].get(k, 0) for k in ks) / max(1e-9, sum(r["exclusive_s"].values())), 3) for g, ks in GROUPS.items()},
                       "x_unique": (r["scores"] or {}).get("x_unique"), "dp_lookups": (r["scores"] or {}).get("dp_lookups"),
                       "dp_calls": r["calls"].get("dp", 0), "per_size": r["per_size"]} for r in R]}
    s["bottleneck"] = max(grp, key=grp.get)
    Path(out).write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps({k: v for k, v in s.items() if k != "per_root"}, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "summarize":
        summarize(sys.argv[3:], sys.argv[2])
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("roster"); ap.add_argument("config"); ap.add_argument("out")
        ap.add_argument("--horizon", type=float, default=180.0); ap.add_argument("--shard", default="0/1")
        main(ap.parse_args())
