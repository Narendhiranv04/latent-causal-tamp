"""BXY-P27 bounded lazy search over the universal domain (bxy_fullspace): complete in principle, bounded in practice.

Nodes are ordered sequences; every node is a complete stopping candidate (the empty sequence is the no-op). Expanding a node generates ALL
its children (every movable not yet moved x every destination free at that step), scores them in one batch with the policy's cost (lower is
better; learned or analytic, never a membership test) and keeps every child: nothing is dropped. Expansion order is best-first by cost, and
every `fair`-th expansion takes the oldest unexpanded node instead (breadth-first, canonical), so that with unbounded budget every member
is reached (fair = 0: pure best-first, still complete because the frontier is never truncated). Sound rules only:
  GOAL_BLOCKED      a node whose edited scene has a body on the goal is not a selectable candidate (success 0); it is still expanded
  GOAL_DEAD         a node with a RELOCATED object on the goal is not expanded (every extension is GOAL_BLOCKED; single-move contract);
                    its descendants are counted exactly as pruned_sound
  shared Y          a verified Y = 0 is the label of the ONE Y node every order with that endpoint shares, so no second Y query is made
Never pruned: low cost / probability, Y(prefix) = 0, a terminal-connector failure of a prefix, NO_PLAN_FOUND / TIMEOUT outcomes.
Verification (optional `verify`; synthetic until P29 is authorized) visits the examined candidates in ascending cost: Y of the endpoint
first (shared), then X of the ordered sequence. Terminal status (exactly one):
  FOUND_VERIFIED                   a verified X = 1 and Y = 1 candidate (best verified among EXAMINED candidates, not a global optimum)
  EXHAUSTED_DEFINED_SPACE          every member was examined and every selectable candidate was verified 0 (negative kinds reported)
  VERIFY_BUDGET_EXHAUSTED_UNKNOWN  verification calls ran out; unverified candidates are unknown, never 0
  BUDGET_EXHAUSTED_UNKNOWN         search budget ran out with every examined candidate refuted; the residual frontier is unknown
  TEACHER_CENSORED                 a verification was censored (administrative), so the outcome is unknown
  SELECTED_UNVERIFIED              no verifier: the lowest-cost examined candidate is a prediction only
State is a JSON document with a sha256 seal; resume continues the same search and never repeats a recorded verification call."""
from __future__ import annotations

import hashlib
import heapq
import json
import time
from math import perm
from pathlib import Path

import bxy_fullspace as S

VERSION = "BXY_FULLSEARCH_V1"
STATUSES = ("FOUND_VERIFIED", "EXHAUSTED_DEFINED_SPACE", "VERIFY_BUDGET_EXHAUSTED_UNKNOWN", "BUDGET_EXHAUSTED_UNKNOWN", "TEACHER_CENSORED",
            "SELECTED_UNVERIFIED")


def below(D, m) -> int:
    """Exact number of strict descendants of any member of length m (uniform domains: every step has free0 destinations)."""
    if not S.uniform(D):
        raise ValueError("descendant counts need a uniform domain (every object on a legal cell)")
    n, F, K = len(D["movable"]), S.free0(D), D["K"]
    return sum(perm(n - m, j) * F ** j for j in range(1, K - m + 1))


def new(D, K, fair=4) -> dict:
    D = dict(D, K=K)
    return {"version": VERSION, "D": D, "K": K, "fair": fair, "nodes": {}, "heap": [], "fifo": [], "expanded": 0, "scored": 0,
            "pruned_sound": 0, "goal_dead_nodes": 0, "verify": {"x": {}, "y": {}}, "calls": 0, "cpu_s": 0.0, "trace": [], "root_done": False, "best": None}


def _push(st, seqs, costs):
    for s, c in zip(seqs, costs):
        k = S.xsig(s)
        dead = S.goal_dead(st["D"], s)
        st["nodes"][k] = {"seq": [list(a) for a in s], "m": len(s), "cost": float(c), "dead": dead,
                          "blocked": S.goal_blocked(st["D"], s), "open": len(s) < st["K"] and not dead}
        st["scored"] += 1
        if not st["nodes"][k]["blocked"] and (st["best"] is None or (round(float(c), 12), len(s), k) < tuple(st["best"])):
            st["best"] = [round(float(c), 12), len(s), k]
        if dead:
            st["goal_dead_nodes"] += 1
            st["pruned_sound"] += below(st["D"], len(s)) if len(s) < st["K"] else 0
        if st["nodes"][k]["open"]:
            heapq.heappush(st["heap"], (round(float(c), 12), len(s), k))
            st["fifo"].append(k)


def _pop(st):
    """Next node to expand: every fair-th expansion the oldest open node (breadth-first fallback), else the lowest-cost open node."""
    use_fifo = st["fair"] and st["expanded"] % st["fair"] == st["fair"] - 1
    q = st["fifo"] if use_fifo else st["heap"]
    while q:
        k = q.pop(0) if use_fifo else heapq.heappop(q)[2]
        if st["nodes"][k]["open"]:
            return k
    return _pop_any(st)


def _pop_any(st):
    for q, f in ((st["heap"], lambda x: x[2]), (st["fifo"], lambda x: x)):
        while q:
            k = f(heapq.heappop(q) if q is st["heap"] else q.pop(0))
            if st["nodes"][k]["open"]:
                return k
    return None


def expand(st, cost, budget) -> bool:
    """Score the root, then expand until the budget (expansions / scored / cpu_s) is spent or nothing is open. True if exhausted."""
    c0 = time.process_time()
    if not st["root_done"]:
        _push(st, [()], cost([()]))
        st["root_done"] = True
    while True:
        if st["expanded"] >= budget.get("expansions", float("inf")) or st["scored"] >= budget.get("scored", float("inf")) or \
                st["cpu_s"] + time.process_time() - c0 >= budget.get("cpu_s", float("inf")):
            break
        k = _pop(st)
        if k is None:
            break
        nd = st["nodes"][k]
        seq = tuple(tuple(a) for a in nd["seq"])
        kids = [seq + (a,) for a in S.actions(st["D"], S.apply(st["D"], seq), {o for o, _ in seq})]
        nd["open"] = False
        st["expanded"] += 1
        if kids:
            _push(st, kids, cost(kids))
        st["trace"].append([st["expanded"], st["scored"], st["best"][0] if st["best"] else None])
    st["cpu_s"] += time.process_time() - c0
    st["fifo"] = [k for k in st["fifo"] if st["nodes"][k]["open"]]           # compaction (order kept)
    return not any(n["open"] for n in st["nodes"].values())


def coverage(st) -> dict:
    D, K = st["D"], st["K"]
    total = sum(S.count(D, K).values())
    residual = sum(below(D, n["m"]) for n in st["nodes"].values() if n["open"])
    ex = len(st["nodes"])
    return {"total": total, "examined": ex, "expanded": st["expanded"], "scored": st["scored"], "open_frontier": sum(n["open"] for n in st["nodes"].values()),
            "pruned_sound": st["pruned_sound"], "unexplored_residual": residual, "balanced": ex + st["pruned_sound"] + residual == total,
            "fraction_examined": ex / total, "distinct_y_examined": len({S.ysig(D, [tuple(a) for a in n["seq"]]) for n in st["nodes"].values()})}


def ranked(st) -> list:
    """Selectable examined candidates (not GOAL_BLOCKED), ascending (cost, m, xsig)."""
    c = [(round(n["cost"], 12), n["m"], k) for k, n in st["nodes"].items() if not n["blocked"]]
    return [k for _, _, k in sorted(c)]


def verify_phase(st, verify, calls) -> dict:
    """Verify ranked candidates until a success or `calls` teacher calls in total; Y (shared endpoint) before X. Recorded calls are reused."""
    D, V = st["D"], st["verify"]
    for k in ranked(st):
        seq = [tuple(a) for a in st["nodes"][k]["seq"]]
        ok = True
        for side, key, q in (("y", S.ysig(D, seq), "Y"), ("x", k, "X")):
            if side == "x" and not seq:
                continue                                                  # the no-op has X = 1 by definition
            if key not in V[side]:
                if st["calls"] >= calls:
                    return {"status": "VERIFY_BUDGET_EXHAUSTED_UNKNOWN", "best_verified": None}
                V[side][key] = verify(q, seq)
                st["calls"] += 1
            r = V[side][key]
            if r is None or r.get("y") is None:
                return {"status": "TEACHER_CENSORED", "best_verified": None, "censored": key}
            if r["y"] == 0:
                ok = False
                break
        if ok:
            return {"status": "FOUND_VERIFIED", "best_verified": k}
    return {"status": None, "best_verified": None}


def run(D, K, cost, budget, verify=None, fair=4, st=None) -> tuple:
    """(state, result). budget: expansions / scored / cpu_s for the search and verify_calls for the teacher."""
    st = st or new(D, K, fair)
    exhausted = expand(st, cost, budget)
    res = {"exhausted": exhausted, "coverage": coverage(st)}
    best = ranked(st)
    if verify is None:
        return st, res | {"status": "SELECTED_UNVERIFIED", "selected": best[0] if best else None, "best_verified": None}
    v = verify_phase(st, verify, budget.get("verify_calls", 0))
    if v["status"] is None:
        v["status"] = "EXHAUSTED_DEFINED_SPACE" if exhausted else "BUDGET_EXHAUSTED_UNKNOWN"
    kinds = {}
    for side in ("x", "y"):
        for r in st["verify"][side].values():
            if r and r.get("y") == 0:
                kinds[r.get("negative_kind") or "UNSPECIFIED"] = kinds.get(r.get("negative_kind") or "UNSPECIFIED", 0) + 1
    return st, res | v | {"selected": best[0] if best else None, "teacher_calls": st["calls"], "negative_kinds": kinds}


# ------------------------------------------------------------------ persistence (hash-sealed, resumable)
def save(st, path) -> str:
    body = json.dumps(st, sort_keys=True)
    h = hashlib.sha256(body.encode()).hexdigest()
    Path(path).write_text(json.dumps({"sha256": h, "state": st}, sort_keys=True))
    return h


def load(path) -> dict:
    d = json.loads(Path(path).read_text())
    if hashlib.sha256(json.dumps(d["state"], sort_keys=True).encode()).hexdigest() != d["sha256"]:
        raise ValueError("search state seal mismatch")
    st = d["state"]
    st["heap"] = [tuple(x) for x in st["heap"]]
    heapq.heapify(st["heap"])
    return st


def exhaustive(D, K, cost) -> list:
    """Mode A reference: every member scored, ascending (cost, m, xsig) - the tiny-domain oracle the search is compared to."""
    seqs = list(S.walk(D, K))
    cs = cost(seqs)
    return sorted(((round(float(c), 12), len(s), S.xsig(s)) for s, c in zip(seqs, cs)))
