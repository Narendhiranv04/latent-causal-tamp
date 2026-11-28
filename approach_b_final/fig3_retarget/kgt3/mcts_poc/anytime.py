#!/usr/bin/env python3
"""Isolated anytime harness: ONE uninterrupted trajectory per (root, arm, seed) under planners.plan's end-to-end semantics; the incumbent plan
and its learned energy are reconstructed at the elapsed budgets (default 5/10/20/30/60/180 s, measured from the start of the plan call, so
proposal generation, the K <= 3 floor, inference, search and final selection are all inside).

GA instrumentation is non-invasive: for the call only, planners.ga is replaced in-process by a wrapper that swaps the sink's candidate list
for a TimedList (a list subclass that timestamps every append / item update) and then calls the ORIGINAL planners.ga unchanged; the floor
callable is wrapped to timestamp its completion.  The 180 s record IS the planners.plan output (identical code path to the production arm).
GA-MCTS uses the same wrapper around mcts_ga.search.

Budget b < horizon: the incumbent = planners.select(candidates completed by t0 + b - r_sel, floor if completed by then) with the production
NOOP gate and tie-break; r_sel = 0.5 s declared anytime selection reserve; overrun_b = max(0, max(t_floor, t0 + b - r_sel) + measured
selection wall - (t0 + b)).  If the search finished before the cut, the incumbent is the final plan.  Selection readouts are cache hits.
    $PYG anytime.py run ROSTER.jsonl CONFIG.json OUT.jsonl --arms GA,GA-MCTS [--seed 0] [--mcfg JSON] [--horizon 180] [--budgets 5,10,...]
                        [--shard i/n] [--roots id1,id2]
ROSTER = public-only jsonl, read through r6.public_roots('r10comp') (R10.1 schema assertions; no private index is read or needed)."""
from __future__ import annotations

import argparse, hashlib, json, math, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KG = HERE.parent
sys.path[:0] = [str(HERE), str(KG), str(KG.parent), str(KG.parent.parent)]
import mcts_ga as MG  # noqa: E402
import planners as PL  # noqa: E402

BUDGETS = (5, 10, 20, 30, 60, 180)
R_SEL = 0.5


class TimedList(list):
    def __init__(self, *a):
        super().__init__(*a)
        self.log = [(time.perf_counter(), [dict(c) for c in self])]

    def _rec(self):
        self.log.append((time.perf_counter(), [dict(c) for c in self]))

    def append(self, x):
        super().append(x); self._rec()

    def __setitem__(self, i, x):
        super().__setitem__(i, x); self._rec()


def timed(fn, rec):
    def wrapped(fz, row0, mode, cfg=None, log=None, sink=None):
        sink["cands"] = TimedList(sink["cands"])
        rec["sink"] = sink
        rec["t_search0"] = time.perf_counter()
        try:
            return fn(fz, row0, mode, cfg, log=log, sink=sink)
        finally:
            rec["t_search1"] = time.perf_counter()
    return wrapped


def timed_floor(f, rec):
    def g(t_end):
        r = f(t_end)
        rec["t_floor"] = time.perf_counter()
        rec["floor"] = {"seq": (r or {}).get("seq")}
        return r
    return g


def emin(cands):
    return min((c["E"] for c in cands if c and c.get("seq")), default=None)


def trajectory(fz, row, arm, floor, pcfg, horizon, budgets, mcfg=None):
    """-> record with the production-identical final plan + reconstructed incumbents at each budget."""
    rec = {}
    t0 = time.perf_counter()
    cfg = {**pcfg, "wall_s": float(horizon), "t_end": t0 + float(horizon)}
    fl = timed_floor(floor, rec) if callable(floor) else floor
    if arm == "GA":
        with MG.search_as_ga(timed(PL.ga, rec)):
            out = PL.plan(fz, row, "GA", fl, cfg)
    elif arm == "GA-MCTS":
        out = MG.plan(fz, row, fl, cfg, mcfg, search_fn=timed(MG.search, rec))
    else:
        raise ValueError(arm)
    log = rec["sink"]["cands"].log if rec.get("sink") is not None and hasattr(rec["sink"]["cands"], "log") else [(t0, [])]
    trace = [[round(t - t0, 4), emin(c)] for t, c in log]
    flo = rec.get("floor") if callable(floor) else floor
    t_floor = rec.get("t_floor", t0)
    sel_wall = out.get("select_wall_s") or 0.0
    t1 = rec.get("t_search1", t0)
    per = {}
    for b in [b for b in budgets if b <= horizon]:
        if b >= horizon:
            per[str(b)] = {"decision": out["decision"], "seq": out["seq"], "partition": out["partition"], "E": out["E"], "kind": out["kind"],
                           "n_cands": out["n_candidates"], "t_state": round(t1 - t0, 4), "overrun_s": out["deadline_overrun_s"], "source": "planners.plan"}
            continue
        cut = t0 + b - R_SEL
        if t1 <= cut:                                                    # search already finished: the final candidate set
            cands, t_state = list(rec["sink"]["cands"]) if rec.get("sink") else [], t1
        else:
            st = [(t, c) for t, c in log if t <= cut]
            t_state, cands = st[-1] if st else (t0, [])
        fl_b = flo                                                       # planners.plan always completes the floor first (overrun if late)
        pick, why, noop = PL.select(fz, row, [dict(c) for c in cands], fl_b, pcfg.get("rule", PL.CFG["rule"]))
        dec = "NOOP" if why == "NOOP" else "REPAIR" if pick else ("TIMEOUT_NO_INCUMBENT" if not cands and not (fl_b and fl_b.get("seq")) and t1 > cut else "ABSTAIN")
        per[str(b)] = {"decision": dec, "seq": pick["seq"] if pick else None, "partition": pick["partition"] if pick else None, "E": pick["E"] if pick else None,
                       "kind": pick["kind"] if pick else None, "n_cands": len(cands), "t_state": round(t_state - t0, 4),
                       "overrun_s": round(max(0.0, max(t_floor, cut) + sel_wall - (t0 + b)), 4), "source": "reconstructed"}
    # consistency: the reconstruction at the end of the trajectory must equal the planners.plan pick
    pick, why, _ = PL.select(fz, row, [dict(c) for c in (rec["sink"]["cands"] if rec.get("sink") else [])], flo, pcfg.get("rule", PL.CFG["rule"]))
    recon_ok = (out["decision"] in ("NOOP",) and why == "NOOP") or (pick is not None and out["seq"] == pick["seq"] and out["partition"] == pick["partition"]) \
        or (pick is None and out["seq"] is None)
    keep = ("arm", "decision", "seq", "partition", "E", "kind", "long", "multi_chunk", "stop", "budget_stop", "wall_s", "floor_wall_s", "search_wall_s",
            "select_wall_s", "deadline_overrun_s", "cap_overrun", "counters", "floor_counters", "selection_readouts", "n_candidates", "incumbent_from_stop", "p_noop")
    fin = {k: out.get(k) for k in keep}
    info = out.get("info") or {}
    fin.update(mode=info.get("mode"), exhausted=info.get("exhausted"), scores=info.get("scores"), per_size=info.get("per_size"),
               n_evals=info.get("n_evals"), iterations=info.get("iterations"), nodes=info.get("nodes"), mcts=info.get("mcts"), timing=info.get("timing"), by_size=info.get("by_size"))
    return {"arm": arm, "horizon": horizon, "budgets": per, "final": fin, "trace": trace, "t_floor_s": round(t_floor - t0, 4),
            "t_search_end_s": round(t1 - t0, 4), "recon_final_ok": bool(recon_ok), "r_sel": R_SEL}


def load_models(cfg_path):
    import learn as LN
    cfg = json.loads(Path(cfg_path).read_text())["3d"]
    fz, net = LN.load("3d", cfg["spec"]); fz.net = net
    if os.environ.get("R6_FLOOR") == "final":
        fzF, netF = LN.load("3d", cfg["spec"]); fzF.net = netF
    else:
        fzF, base = LN.load("3d", "F0"); fzF.net = base
    pcfg = {"rule": {**PL.CFG["rule"], **({"S2_tau": cfg["S2_tau"], "S2_stat": cfg.get("S2_stat")} if cfg.get("S2_tau") is not None else {})},
            "rec": {**PL.CFG["rec"], "admit_m": cfg.get("admit_m", 0.0), "admit_eta": cfg.get("admit_eta")}}
    return cfg, fz, fzF, pcfg


def roster(path):
    import r6
    os.environ["R10_PUBLIC"] = str(path)
    return r6.public_roots("r10comp")


def run(a):
    import r53
    opened = set()
    if a.audit_open:                                                     # record every file the planning process opens (evaluator-isolation check)
        sys.addaudithook(lambda ev, args: opened.add(str(args[0])) if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)) else None)
    cfg, fz, fzF, pcfg = load_models(a.config)
    rows = roster(a.roster)
    if a.roots:
        want = set(a.roots.split(","))
        rows = [r for r in rows if r[0] in want]
    i_, n_ = (int(x) for x in a.shard.split("/"))
    arms = a.arms.split(",")
    mcfg = {**json.loads(a.mcfg or "{}"), "seed": a.seed}
    budgets = tuple(int(x) for x in a.budgets.split(","))
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["root_id"], r["arm"]) for r in (json.loads(l) for l in open(out))} if out.exists() else set()
    warm = False
    with open(out, "a") as f:
        for k_, (rid, row) in enumerate(rows):
            if k_ % n_ != i_:
                continue
            if not warm:                                                 # untimed CUDA warm-up (one H3-style readout batch), declared
                fz.prop_mode = cfg["prop_GA"]; fz.reset(); fz.caps = {}; fz.p_noop(row); fzF.reset(); fzF.p_noop(row); warm = True
            order = arms if int(hashlib.sha256(f"ANY|{rid}".encode()).hexdigest(), 16) % 2 == 0 else arms[::-1]   # alternate arm order by root
            for arm in order:
                if (rid, arm) in done:
                    continue
                fz.prop_mode = cfg["prop_GA"]
                r = trajectory(fz, row, arm, r53.floor_fn(fzF, row), pcfg, a.horizon, budgets, mcfg if arm == "GA-MCTS" else None)
                fz.prop_mode = "S1"
                r.update(root_id=rid, seed=a.seed if arm == "GA-MCTS" else None, mcfg=mcfg if arm == "GA-MCTS" else None, cfg_id=MG.canon_cfg(mcfg) if arm == "GA-MCTS" else None)
                f.write(json.dumps(r, default=str) + "\n"); f.flush()
                print(rid, arm, {b: (v["decision"], v["E"] and round(v["E"], 3)) for b, v in r["budgets"].items()}, r["final"]["wall_s"], flush=True)
    if a.audit_open:
        Path(a.audit_open).write_text(json.dumps(sorted(opened), indent=0))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("roster"); ap.add_argument("config"); ap.add_argument("out")
    ap.add_argument("--arms", default="GA,GA-MCTS"); ap.add_argument("--seed", type=int, default=0); ap.add_argument("--mcfg", default=None)
    ap.add_argument("--horizon", type=float, default=180.0); ap.add_argument("--budgets", default=",".join(map(str, BUDGETS)))
    ap.add_argument("--shard", default="0/1"); ap.add_argument("--roots", default=None)
    ap.add_argument("--audit-open", default=None)
    a = ap.parse_args()
    {"run": run}[a.cmd](a)
