"""Approach D G2b: the AD_PRECOMPILED solver-free motion provider (approachD_G2b_solver_free_provider_instructions_v1_2 §3-§4).

It serves a FINITE, offline-compiled robot-state graph (ad_compile.build_graph):
  nodes       exact joint states (bitwise identity of a stored waypoint; no tolerance clustering, no snapping);
  actions     object actions = the 'core' of a compiled template (approach .. close .. carry .. release .. complete safe retreat), from
              its approach-start node to its retreat-end node, for one absolute (src, dst);
  connectors  free-arm legs (open gripper, nothing held) between nodes: each template's own entry leg (home -> approach start) and
              exit leg (retreat end -> home) and the root ENTRY templates (stratum -> home). Any stored connector between two
              nodes is usable; G2b compiled no extra non-home connectors.
At inference it only looks records up, orders them (finite, deterministic), and certifies the FROZEN arrays in the current scene through
ad_runtime.certify_action / certify_free; a robot-state mismatch is bridged only by a path of stored connectors (<= max_hops). No IK,
planner, connector synthesis, interpolation or snapping is reachable (tests run it under ad_runtime.forbid('raise')). Outcomes are binary
SUCCESS / FAILURE with a reason; a FAILURE is a finite-library outcome, never a proof that no physical motion exists, and nothing here
reuses the historical CERTIFIED_INFEASIBLE semantics."""
from __future__ import annotations

import collections
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

import ad_runtime as ar

VERSION = "AD_PRECOMPILED_V1"
CHECKER = "motion.certify_trajectory+geometry.certify/" + ar.VERSION
ACTION_FAIL = {"RELOCATION": "COLLISION_CURRENT_SCENE", "TARGET": "TARGET_ACTION_COLLISION"}
NO_ACTION = {"RELOCATION": "NO_TEMPLATE", "TARGET": "TARGET_TEMPLATE_UNAVAILABLE"}


PKEYS = {"version", "tiers", "rank", "mode_limit", "per_mode", "action_budget", "max_hops", "prefilter"}


def pcfg(path="approach_d.toml") -> dict:
    """[provider] of the opt-in overlay, exact key set (an unknown key, e.g. an online fallback switch, is an error)."""
    import tomllib
    with open(path, "rb") as f:
        c = tomllib.load(f)["provider"]
    if set(c) != PKEYS or c["version"] != VERSION or c["prefilter"] not in ("OFF", "ADVISORY", "HARD") or \
            not set(c["tiers"]) <= {"exact", "relative", "catalog"} or c["rank"] not in ("patch", "geometry", "random"):
        raise ValueError(f"invalid [provider]: {sorted(set(c) ^ PKEYS)}")
    return c


class Graph:
    """Frozen graph: GRAPH.json (nodes / actions / connectors with provenance) + GRAPH_ARRAYS.npz (waypoint arrays per record id)."""

    def __init__(self, d=Path("runs/approach_d/g2b/catalog"), name="GRAPH"):
        meta = json.loads((Path(d) / f"{name}.json").read_text())
        z = np.load(Path(d) / f"{name}_ARRAYS.npz")
        self.version, self.hash, self.nodes = meta["version"], meta["hash"], meta["nodes"]
        self.actions, self.connectors = meta["actions"], meta["connectors"]
        arr = collections.defaultdict(dict)
        for k in z.files:
            i, f = k.split("__")
            arr[i][f] = z[k]
        self.arrays = dict(arr)
        self.by_pair, self.out = collections.defaultdict(list), collections.defaultdict(list)
        for i, a in self.actions.items():
            self.by_pair[(a["src"], a["dst"])].append(i)
        for i, c in sorted(self.connectors.items(), key=lambda x: (x[1]["rank"], x[0])):
            self.out[c["from"]].append(i)
        self.q = {n: np.asarray(v["q"], float) for n, v in self.nodes.items()}

    def node_of(self, q):
        """Exact node identity of a robot configuration, else None (a configuration outside the graph has no stored transitions)."""
        q = np.asarray(q, float)
        return next((n for n, v in self.q.items() if np.array_equal(v, q)), None)


class Precompiled:
    def __init__(self, cfg, robot, scene0, goal_cell, graph, order, action_budget=6, max_hops=2, prefilter="OFF", policy="?"):
        assert prefilter in ("OFF", "ADVISORY", "HARD")
        self.cfg, self.robot, self.s0, self.goal_cell, self.g = cfg, robot, scene0, goal_cell, graph
        self.order, self.budget, self.max_hops, self.prefilter, self.policy = order, action_budget, max_hops, prefilter, policy
        self.cache, self.counts, self.cpu = {}, collections.Counter(), 0.0
        self.cache_key = (VERSION, graph.hash, CHECKER, policy, action_budget, max_hops, prefilter)

    def scene(self, cells):
        objs = tuple(replace(o, cell=cells[o.id], xy_m=self.s0.lattice.center(cells[o.id])) for o in self.s0.objects)
        return replace(self.s0, objects=objs)

    def _cert(self, rid, cells, oid=None):
        """Geometric verdict of one frozen record in the occupancy `cells` (cached on record id + full occupancy + versions)."""
        k = self.cache_key + (rid, tuple(sorted(cells.items())), oid)
        if k in self.cache:
            self.counts["cache_hits"] += 1
            return self.cache[k]
        self.counts["certify_action" if oid else "certify_connector"] += 1
        a = self.g.arrays[rid]
        v = ar.certify_action(self.robot, self.cfg, self.scene(cells), oid, a) if oid else ar.certify_free(self.robot, self.cfg,
                                                                                                             self.scene(cells), a)
        self.cache[k] = v
        return v

    def _paths(self, a, b):
        """Every stored connector path a -> b with at most max_hops connectors (fewest hops first, then connector rank / id)."""
        if a == b:
            return [[]]
        out, frontier = [], [(a, [])]
        for _ in range(self.max_hops):
            nxt = []
            for n, path in frontier:
                for c in self.g.out.get(n, []):
                    t = self.g.connectors[c]["to"]
                    if t == b:
                        out.append(path + [c])
                    elif t not in {self.g.connectors[x]["from"] for x in path} | {a}:
                        nxt.append((t, path + [c]))
            frontier = nxt
        return out

    def _connect(self, cells, q_node, target):
        paths = self._paths(q_node, target)
        if not paths:
            return None, "NO_COMPATIBLE_CONNECTOR", []
        tried = []
        for path in paths:
            bad = next(((c, v) for c in path for v in [self._cert(c, cells)] if not v["ok"]), None)
            if bad is None:
                return path, None, tried
            tried.append({"path": path, "blocked_by": bad[0], "pair": bad[1]["pair"]})
        return None, "CONNECTOR_COLLISION", tried

    def _act(self, cells, q, oid, dst, kind):
        t0 = time.process_time()
        out = {"status": ar.FAILURE, "reason": None, "kind": kind, "object": oid, "dest": dst, "steps": [], "attempts": [], "checks": 0}
        q_node = self.g.node_of(q)
        occ = {c for o, c in cells.items() if o != oid}
        if q_node is None:
            out["reason"] = "NO_COMPATIBLE_Q"
        elif dst in occ:
            out["reason"] = "DESTINATION_OCCUPIED"
        else:
            r = self.s0.get(oid).radius_m
            cand = [i for i in self.g.by_pair.get((cells[oid], dst), []) if abs(self.g.actions[i]["radius"] - r) <= 1e-9]
            if not cand:
                out["reason"] = NO_ACTION[kind]
            for i in (self.order(self, cells, oid, dst, cand) if cand else []):
                if out["checks"] >= self.budget:
                    out["reason"] = "CHECK_BUDGET_EXHAUSTED"
                    break
                A = self.g.actions[i]
                if not self._paths(q_node, A["from"]):          # pure graph lookup first: no certification spent on unreachable actions
                    out["attempts"].append({"action": i, "reason": "NO_COMPATIBLE_CONNECTOR"})
                    continue
                hit = sorted(set(A["swept"]) & occ)
                if hit and self.prefilter == "HARD":
                    out["attempts"].append({"action": i, "reason": "SWEEP_PREFILTER_REJECT", "cells": hit})
                    continue
                out["checks"] += 1
                v = self._cert(i, cells, oid)
                if not v["ok"]:
                    why = "PHASE_INCONSISTENT" if v["verdict"] == "RECORD_INVALID" else ACTION_FAIL[kind]
                    out["attempts"].append({"action": i, "reason": why, "pair": v["pair"], "phase": v["phase"], "prefilter_hit": hit})
                    continue
                path, why, tried = self._connect(cells, q_node, A["from"])
                if path is None:
                    out["attempts"].append({"action": i, "reason": why, "connector_tries": tried, "prefilter_hit": hit})
                    continue
                out.update(status=ar.SUCCESS, reason=None, steps=[("connector", c) for c in path] + [("action", i)], q_end=A["to"],
                           cells={**cells, oid: dst}, prefilter_hit=hit, action=i)
                break
            rs = collections.Counter(a["reason"] for a in out["attempts"])
            out["reason_counts"] = dict(rs)
            if out["status"] == ar.FAILURE and out["reason"] is None:
                out["reason"] = rs.most_common(1)[0][0] if rs else NO_ACTION[kind]
        self.counts[f"{kind.lower()}_{out['status'].lower()}"] += 1
        self.cpu += time.process_time() - t0
        return out

    def edges(self, cells, q, oid, dst):
        """One relocation oid -> dst from the exact robot state q: SUCCESS with stored steps (connectors + action) and the next state, or
        FAILURE with a reason and every attempted record."""
        return self._act(cells, q, oid, dst, "RELOCATION")

    def goal(self, cells, q):
        """The ORIGINAL target T (t0 -> goal cell) with a precompiled target action; never a newly planned trajectory."""
        return self._act(cells, q, "t0", self.goal_cell, "TARGET")

    def verify_plan(self, cells0, q0, steps) -> dict:
        """Independent replay of the concatenated stored records: exact continuity (each record starts bitwise where the previous
        ended), each record re-certified in the occupancy current at its turn (cache bypassed), occupancy and q updated, target last."""
        cells, q, h = dict(cells0), np.asarray(q0, float), hashlib.sha256()
        for j, (kind, rid, oid) in enumerate(steps):
            a = self.g.arrays[rid]
            if not np.array_equal(np.asarray(a["q"][0], float), q):
                return {"status": ar.FAILURE, "reason": "SEQUENCE_DISCONTINUITY", "step": j}
            s = self.scene(cells)
            v = ar.certify_action(self.robot, self.cfg, s, oid, a) if kind == "action" else ar.certify_free(self.robot, self.cfg, s, a)
            if not v["ok"]:
                return {"status": ar.FAILURE, "reason": "REPLAY_REJECTED", "step": j, "verdict": v}
            if kind == "action":
                A = self.g.actions[rid]
                if cells[oid] != A["src"] or np.linalg.norm(np.asarray(a["place_xy"]) - self.s0.lattice.center(A["dst"])) > 1e-6:
                    return {"status": ar.FAILURE, "reason": "PHASE_INCONSISTENT", "step": j}
                cells[oid] = A["dst"]
            q = np.asarray(a["q"][-1], float)
            h.update(np.asarray(a["q"], float).tobytes())
            h.update(np.asarray(a["gap"], float).tobytes())
        ok = cells.get("t0") == self.goal_cell
        return {"status": ar.SUCCESS if ok else ar.FAILURE, "reason": None if ok else "TARGET_NOT_AT_GOAL", "q_end": self.g.node_of(q),
                "cells": cells, "trajectory_hash": h.hexdigest()[:16], "records": len(steps)}

    def stats(self):
        return {"version": VERSION, "graph": self.g.hash, "policy": self.policy, "budget": self.budget, "max_hops": self.max_hops,
                "prefilter": self.prefilter, "counts": dict(self.counts), "cpu_s": self.cpu}


def run_sequence(prov, cells0, q0, seq) -> dict:
    """A candidate repair (ordered (object, dest) list, then the original target T) through the provider: first-valid stored records per
    step from the state the previous step actually left (cells and exact q); then an independent replay of the whole chain."""
    cells, q, steps, log = dict(cells0), np.asarray(q0, float), [], []
    for o, d in list(seq) + [("t0", None)]:
        r = prov.goal(cells, q) if o == "t0" and d is None else prov.edges(cells, q, o, d)
        log.append({k: r[k] for k in ("status", "reason", "kind", "object", "dest", "checks", "attempts")} | {"steps": r["steps"]})
        if r["status"] != ar.SUCCESS:
            return {"status": ar.FAILURE, "reason": r["reason"], "failed_step": len(log) - 1, "log": log}
        steps += [(k, i, o if k == "action" else None) for k, i in r["steps"]]
        cells, q = r["cells"], prov.g.q[r["q_end"]]
    rep = prov.verify_plan(cells0, q0, steps)
    return {"status": rep["status"], "reason": rep["reason"], "failed_step": None if rep["status"] == ar.SUCCESS else "replay", "log": log,
            "steps": steps, "replay": rep}


def repair(prov, cells0, q0, candidates) -> dict:
    """First SUCCESS over a finite, ordered list of candidate sequences (no search beyond the declared list; no optimality claim)."""
    tried = []
    for seq in candidates:
        r = run_sequence(prov, cells0, q0, seq)
        tried.append({"sequence": [list(x) for x in seq], "status": r["status"], "reason": r["reason"], "failed_step": r["failed_step"]})
        if r["status"] == ar.SUCCESS:
            return {**r, "sequence": [list(x) for x in seq], "tried": tried}
    return {"status": ar.FAILURE, "reason": "NO_CANDIDATE_SEQUENCE_ACCEPTED", "tried": tried}
