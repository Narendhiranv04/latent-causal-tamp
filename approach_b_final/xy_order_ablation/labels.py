#!/usr/bin/env python3
"""Evaluator-only exact-contract label ledger (plan.md 4.2).  Never imported by planner code (readout.py).

Sources: every finalized-teacher verify cache on this host (index-keyed ordered sequences, 'unchanged finalized teacher' provenance) plus the
finalized snapshot labels.  Keys: X -> (domain, root, exact ordered sequence); Y -> (domain, root, canonical endpoint assignment).
Mapping (CR P0, verified against the runtime):
  2D strict: VERIFIED / EMPTY -> 1, CERTIFIED_INFEASIBLE -> 0, UNKNOWN_PLANNER / UNKNOWN_TRANSIT -> UNKNOWN (stored 0); operational = stored value.
  3D: resolution EVALUATED -> stored value (a 0 is a teacher-BUDGET-defined failure, not an impossibility proof); UNRESOLVED_* -> UNKNOWN.
  Snapshot labels (finalized binary, unresolved already censored) -> source 'snapshot', reported as snapshot-operational.
Decided conflicts on one key quarantine that factor/key (never voted).  Missing is never failure."""
from __future__ import annotations

import collections, glob, hashlib, json, os
from pathlib import Path

H = Path.home()
CACHE_GLOBS = ["abf_v3_laptop/runs", "abf_v31_lapverify/runs", "abf_v32/caches/gvlab", "abf_v32/B_runs/laptop", "abf_v32/E_runs_*", "abf_v32/T_runs",
               "abf_v32/parity_runs/laptop", "abf_v33/parity/laptop_*", "abf_v33/verify_lap_*", "abf_v34/batch?/cache", "analytical_baselines/cache",
               "cr_cvae_runs/p4/cache", "disco_final/eval/cache", "sorc_grid/eval/cache", "fds_private/fds", "mcts_sets_private/*", "xyrr_private/p3_cache"]
# 2D decided statuses: positives + negatives the teacher itself marks negative_kind CERTIFIED (bxy_teacher.py l.231/233); REPLAY_FAILED
# (OTHER_FAILURE), INELIGIBLE and UNKNOWN_* stay unresolved.
STRICT_2D = ("VERIFIED", "EMPTY", "CERTIFIED_INFEASIBLE", "TERMINAL_STATE_NOT_CLEAR", "Q_REF_NOT_CLEAR_IN_EDITED_SCENE")
EXTRA_GLOBS = [os.environ.get("XYO_CACHE", str(H / "xyo_runs/p3/cache"))]


def jl(p):
    out = []
    for l in open(p):
        try:
            out.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    return out


def ekey(seq):
    return json.dumps(sorted([int(o), int(d)] for o, d in seq))


def skey(seq):
    return json.dumps([[int(o), int(d)] for o, d in seq])


def factor(dom, r, kind):
    """-> (strict 0/1/None, operational 0/1/None, raw status)."""
    if not r:
        return None, None, "MISSING"
    v = r.get("x" if kind == "X" else "y")
    v = v if v in (0, 1) else None
    if dom == "2d":
        st = r.get("status") or ""
        return (v if st in STRICT_2D else None), v, st
    res = r.get("resolution", "EVALUATED")
    ok = v if res == "EVALUATED" else None
    return ok, ok, f"{res}:{r.get('status')}"


def cache_files(dom):
    fs = []
    for g in CACHE_GLOBS:
        fs += glob.glob(str(H / g / f"verify_{dom}*.jsonl"))
    for g in EXTRA_GLOBS:
        fs += glob.glob(str(Path(g) / f"verify_{dom}*.jsonl"))
    return sorted(set(fs))


class Ledger:
    """X[(root, seq)] / Y[(root, endpoint)] -> {"strict", "oper", "status", "srcs"}; conflicts recorded and quarantined (value None)."""

    def __init__(self, dom, roots=None, snapshot_rows=()):
        self.dom, self.X, self.Y, self.conflicts, self.files = dom, {}, {}, collections.Counter(), {}
        for f in cache_files(dom):
            n = 0
            for v in jl(f):
                if roots is not None and v.get("root") not in roots:
                    continue
                for x in v.get("results", []):
                    n += 1
                    self.add(v["root"], x["seq"], x.get("x"), x.get("y"), f)
            self.files[f.replace(str(H), "~")] = {"sha256": hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16], "results_used": n}
        for r in snapshot_rows:
            Y = {ekey(y["edit"]): y["y"] for y in r["labels"]["Y"]}
            for k, y in Y.items():
                self._put(self.Y, (r["root_id"], k), (y, y, "SNAPSHOT"), "snapshot", "Y")
            for q in r["labels"]["X"]:
                if q["seq"] and q["x"] in (0, 1):
                    self._put(self.X, (r["root_id"], skey(q["seq"])), (q["x"], q["x"], "SNAPSHOT"), "snapshot", "X")

    def _put(self, D, k, val, src, kind):
        s, o, st = val
        cur = D.get(k)
        if cur is None:
            D[k] = {"strict": s, "oper": o, "status": st, "srcs": [src], "quarantined": False}
            return
        if cur["quarantined"]:
            return
        if cur["strict"] is not None and s is not None and cur["strict"] != s:     # two DECIDED values disagree -> quarantine
            self.conflicts[(kind, "decided")] += 1
            cur.update({"strict": None, "oper": None, "quarantined": True, "status": "CONFLICT"})
            return
        if cur["strict"] is None and s is not None:                         # a decided label upgrades an unresolved one for the same key
            if cur["oper"] is not None and cur["oper"] != s:
                self.conflicts[(kind, "unknown_then_decided_differs_from_stored")] += 1
            cur.update({"strict": s, "oper": s, "status": st})
        elif cur["oper"] is None and o is not None:
            cur["oper"] = o
        if src not in cur["srcs"]:
            cur["srcs"].append(src)

    def add(self, root, seq, xr, yr, src):
        if seq:
            self._put(self.X, (root, skey(seq)), factor(self.dom, xr, "X"), src, "X")
        self._put(self.Y, (root, ekey(seq) if seq else "[]"), factor(self.dom, yr, "Y"), src, "Y")

    def get(self, root, seq, conv="strict"):
        """-> (x, y, z, x_status, y_status) for an ordered sequence; z by logical conjunction (None = UNKNOWN or missing)."""
        Yr = self.Y.get((root, ekey(seq) if seq else "[]"))
        y = Yr[conv] if Yr else None
        if not seq:
            return 1, y, y, "EMPTY", Yr["status"] if Yr else "MISSING"
        Xr = self.X.get((root, skey(seq)))
        x = Xr[conv] if Xr else None
        z = 1 if (x == 1 and y == 1) else 0 if (x == 0 or y == 0) else None
        return x, y, z, (Xr["status"] if Xr else "MISSING"), (Yr["status"] if Yr else "MISSING")

    def queried(self, root, seq):
        return (root, skey(seq)) in self.X and (root, ekey(seq)) in self.Y


def order_groups(led, roots):
    """Same root + same canonical assignment, m = 2 / 3: every labelled order of it -> {(root, endpoint): {"m", "orders": {seq: x}, "y"}}."""
    g = collections.defaultdict(dict)
    for (root, s), r in led.X.items():
        if roots is not None and root not in roots:
            continue
        seq = json.loads(s)
        if len(seq) in (2, 3):
            g[(root, ekey(seq))][s] = r
    out = {}
    for (root, e), orders in g.items():
        Yr = led.Y.get((root, e))
        out[(root, e)] = {"m": len(json.loads(e)), "orders": orders, "y_strict": Yr["strict"] if Yr else None, "y_oper": Yr["oper"] if Yr else None}
    return out
