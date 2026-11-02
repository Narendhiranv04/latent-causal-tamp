"""BXY-P26 universal corrective-action domain (ACTION_DOMAIN_V1): every legal ordered relocation sequence of a supported 2D scene, lazily.

A candidate is r = ((o1, d1), ..., (om, dm)), 0 <= m <= K. The domain is defined from four physical record fields only (READ): the scene
(objects with id / kind / cell / radius, lattice, legal_cells), the goal cell and the immovable structures fixed_ids. It never reads
construction intent (options, intended, K_intent, K_cert, forced_order, neutral / harmful cells), roles VALUES, catalogues, labels,
results or witnesses. Grammar (the existing teacher contract, bxy_teacher.eligible + bxy_f1 X rules):
  objects       M(S0) = every non-target object not in fixed_ids; each relocated at most once; the target and fixed structures never
  destinations  D(S_t, o) = legal cells empty AT STEP t (a cell vacated by an earlier relocation is available), other than o's own cell;
                every such cell is kept: far cells, the goal, the q_ref footprint, access-killing and corridor cells are potential negatives
  length        m <= K (K <= bd_core.MAX_ACTIONS - 1); the empty sequence (no-op) and every shorter stopping length are members
Out-of-domain (never members, reason recorded by classify): UNKNOWN_OBJECT, TARGET_MOVED, FIXED_MOVED, DUPLICATE_OBJECT, NULL_RELOCATION,
DEST_NOT_LEGAL, DEST_OCCUPIED (includes simultaneous swaps), LENGTH. Equal-radius discs at distinct cell centres never overlap
(2 r < pitch, checked), so cell occupancy is exactly bxy_f1's geometric DEST_OCCUPIED.
Identity: the X node is the ordered sequence (xsig); the Y node is the edited endpoint (ysig = sorted moved poses): permutations with one
endpoint share one Y node and have distinct X nodes. Sound terminal screen: GOAL_BLOCKED (a body on the goal cell; success impossible).
Sound subtree rule (success only): a RELOCATED object on the goal can never move again, so every extension is GOAL_BLOCKED too.
    python3 bxy_fullspace.py domain | counts | charge <out_dir> <phase> <note> -- <command...>"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import resource
import subprocess
import sys
import time
from math import perm
from pathlib import Path

VERSION = "BXY_FULLSPACE_V1"
READ = ("scene", "goal_cell", "fixed_ids")
K_MAX = 6                                                   # bd_core.MAX_ACTIONS - 1 relocations (teacher contract)
OUT = Path("runs/approach_b/bxy_p26_fullspace_v1")
REASONS = ("UNKNOWN_OBJECT", "TARGET_MOVED", "FIXED_MOVED", "DUPLICATE_OBJECT", "NULL_RELOCATION", "DEST_NOT_LEGAL", "DEST_OCCUPIED", "LENGTH")


def domain(rec) -> dict:
    """The immutable symbolic domain of one scene (reads READ only)."""
    sc = rec["scene"]
    objs = sc["objects"]
    tg = [o["id"] for o in objs if o["kind"] == "target"]
    if len(tg) != 1:
        raise ValueError("exactly one target expected")
    fixed = set(rec["fixed_ids"])
    L = sc["lattice"]
    if any(o["cell"] is None for o in objs) or len({o["cell"] for o in objs}) != len(objs):
        raise ValueError("every object must rest at its own lattice cell")
    if 2 * max(o["radius_m"] for o in objs) >= L["pitch_m"]:
        raise ValueError("discs at distinct cells could overlap: cell occupancy would not equal geometric overlap")
    return {"version": VERSION, "target": tg[0], "goal": int(rec["goal_cell"]), "n_cells": L["rows"] * L["cols"],
            "legal": tuple(sorted(int(c) for c in sc["legal_cells"])), "cells0": {o["id"]: int(o["cell"]) for o in sorted(objs, key=lambda o: o["id"])},
            "movable": tuple(sorted(o["id"] for o in objs if o["kind"] != "target" and o["id"] not in fixed)),
            "fixed": tuple(sorted(fixed))}


def view(rec) -> dict:
    """The only part of a record the domain may see (deep copy)."""
    return {k: copy.deepcopy(rec[k]) for k in READ}


def apply(D, seq) -> dict:
    c = dict(D["cells0"])
    for o, d in seq:
        c[o] = int(d)
    return c


def actions(D, cells, moved):
    """Canonical (object, destination) actions available in the scene `cells` after relocating `moved`."""
    occ = set(cells.values())
    free = [d for d in D["legal"] if d not in occ]
    for o in D["movable"]:
        if o not in moved:
            for d in free:
                yield (o, d)


def walk(D, K, prefix=()):
    """Every member extending `prefix` up to length K, depth-first in canonical order (prefix itself first). Lazy: O(K) memory."""
    yield prefix
    if len(prefix) >= K:
        return
    cells, moved = apply(D, prefix), {o for o, _ in prefix}
    for a in actions(D, cells, moved):
        yield from walk(D, K, prefix + (a,))


def classify(D, seq, K=K_MAX):
    """None for a member of the domain, else the first out-of-domain reason (never a physical X / Y claim)."""
    if len(seq) > K:
        return "LENGTH"
    cells, moved, legal = dict(D["cells0"]), set(), set(D["legal"])
    for o, d in seq:
        d = int(d)
        if o not in cells:
            return "UNKNOWN_OBJECT"
        if o == D["target"]:
            return "TARGET_MOVED"
        if o not in D["movable"]:
            return "FIXED_MOVED"
        if o in moved:
            return "DUPLICATE_OBJECT"
        if d == cells[o]:
            return "NULL_RELOCATION"
        if d not in legal:
            return "DEST_NOT_LEGAL"
        if d in cells.values():
            return "DEST_OCCUPIED"
        cells[o], moved = d, moved | {o}
    return None


def xsig(seq) -> str:
    return ".".join(f"{o}>{int(d)}" for o, d in seq) or "empty"          # == bxy_data.sig (X node identity)


def endpoint(D, seq) -> dict:
    c = apply(D, seq)
    return {o: v for o, v in sorted(c.items()) if v != D["cells0"][o]}


def ysig(D, seq) -> str:
    return xsig(sorted(endpoint(D, seq).items()))                        # == bxy_data.ykey payload (Y node identity)


def goal_blocked(D, seq) -> bool:
    """Sound terminal F1 rule: some body rests on the goal cell of the edited scene (the target cannot be placed; success = 0)."""
    return D["goal"] in apply(D, seq).values()


def goal_dead(D, seq) -> bool:
    """Sound SUBTREE rule for success: a relocated object rests on the goal; it can never move again, so every extension is goal-blocked."""
    return any(int(d) == D["goal"] for _, d in seq)


# ------------------------------------------------------------------ exact sizes (no enumeration)
def free0(D) -> int:
    return len(set(D["legal"]) - set(D["cells0"].values()))


def uniform(D) -> bool:
    """Every object rests on a legal cell, so each step has exactly free0(D) destinations whatever happened before."""
    return set(D["cells0"].values()) <= set(D["legal"])


def count(D, K) -> dict:
    """{m: number of members of length m}: P(n, m) F^m when every object rests on a legal cell (exact), else by lazy enumeration."""
    if uniform(D):
        n, F = len(D["movable"]), free0(D)
        return {m: perm(n, m) * F ** m for m in range(K + 1)}
    out = {m: 0 for m in range(K + 1)}
    for s in walk(D, K):
        out[len(s)] += 1
    return out


def count_endpoints(D, K) -> dict:
    """{m: number of distinct Y nodes (edited scenes) with m moved objects}: per object subset, each object goes to a cell free in S0 or to
    the S0 cell of another moved object (injective, dependency graph acyclic so that some order is legal); exact."""
    import itertools
    legal, occ0 = set(D["legal"]), set(D["cells0"].values())
    F = len(legal - occ0)
    out = {m: 0 for m in range(K + 1)}
    for m in range(K + 1):
        for S in itertools.combinations(D["movable"], m):
            for ptr in itertools.product([None] + list(range(m)), repeat=m):   # ptr[i] = j: object i goes to S0 cell of object j
                tgt = [j for j in ptr if j is not None]
                if any(j == i for i, j in enumerate(ptr)) or len(tgt) != len(set(tgt)):
                    continue
                if any(D["cells0"][S[j]] not in legal for j in tgt) or _cyclic(ptr):
                    continue
                out[m] += perm(F, sum(j is None for j in ptr))
    return out


def _cyclic(ptr) -> bool:
    for i in range(len(ptr)):
        seen, j = set(), i
        while j is not None and j not in seen:
            seen.add(j)
            j = ptr[j]
        if j is not None:
            return True
    return False


# ------------------------------------------------------------------ toy scenes (tests, figures)
def toy(movable, fixed=(), target=27, goal=29, legal=None, name="toy") -> dict:
    """Minimal record on the 8 x 8 lattice: movable {id: cell}, fixed {id: cell}; roles keys = movables (the teacher's movable set)."""
    def ob(i, c, kind):
        return {"id": i, "kind": kind, "cell": c, "radius_m": 0.024, "support": "table", "xy_m": [(c % 8 + 0.5) * 0.08, (c // 8 + 0.5) * 0.08]}
    objs = [ob("t0", target, "target")] + [ob(i, c, "obstacle") for i, c in {**dict(movable), **dict(fixed)}.items()]
    return {"scene": {"objects": sorted(objs, key=lambda o: o["id"]), "lattice": {"rows": 8, "cols": 8, "pitch_m": 0.08},
                      "legal_cells": sorted(legal if legal is not None else range(64)), "domain_policy": "ALL_SUPPORTED",
                      "robot": {"q_rad": [1.5707963267948966] * 3, "gripper_gap_m": 0.07, "attachment": "free", "attached_id": None},
                      "robot_profile_hash": "toy"},
            "goal_cell": goal, "fixed_ids": sorted(dict(fixed)), "roles": {i: "movable" for i in dict(movable)}, "root": name,
            "q0": [1.5707963267948966] * 3}


# ------------------------------------------------------------------ manifest, CPU ledger
def sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def manifest() -> dict:
    return {"version": VERSION, "reads": list(READ), "never_reads": ["construction (options, intended, K_intent, K_LB, K_cert, forced_order, "
            "neutral_cells, harmful_cells, q_ref_footprint)", "roles values", "spec", "catalogue_v21 / design_v21", "labels", "results", "witnesses"],
            "members": {"objects": "every non-target object not in fixed_ids, each relocated at most once",
                        "destinations": "legal cells empty at that step, other than the object's own cell (vacated cells reusable)",
                        "lengths": "0..K (no-op and every shorter stopping length)", "orders": "all orders the grammar allows",
                        "kept_negatives": ["far cells", "goal cell (GOAL_BLOCKED, success 0)", "q_ref footprint", "access-killing cells",
                                           "reference corridor", "pick-closed / unreachable placements", "useless and harmful edits"]},
            "out_of_domain": list(REASONS), "x_node": "ordered sequence (xsig)", "y_node": "edited endpoint (ysig)",
            "sound_rules": {"terminal": "GOAL_BLOCKED -> success 0 (no teacher label is ever created from it)",
                            "subtree_success": "relocated object on the goal -> every extension GOAL_BLOCKED (single-move contract)",
                            "never_pruned": ["Y(prefix) = 0", "terminal connector failure of a prefix", "low predicted probability",
                                             "planner NO_PLAN_FOUND / TIMEOUT"]},
            "size": "1 + sum_m P(n, m) F^m, F = |legal cells| - |objects| when every object rests on a legal cell", "K_max": K_MAX,
            "code_sha256": sha_file(__file__)}


def charge(out, phase, note, cmd) -> dict:
    """Run cmd as a child and append its CPU (user + sys of children) and wall seconds to out/CPU_LEDGER.jsonl."""
    r0, w0 = resource.getrusage(resource.RUSAGE_CHILDREN), time.time()
    rc = subprocess.call(cmd)
    r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    e = {"t": round(time.time(), 1), "phase": phase, "note": note, "cmd": " ".join(cmd)[:300], "exit": rc,
         "cpu_s": round(r1.ru_utime + r1.ru_stime - r0.ru_utime - r0.ru_stime, 2), "wall_s": round(time.time() - w0, 2)}
    Path(out).mkdir(parents=True, exist_ok=True)
    with open(Path(out) / "CPU_LEDGER.jsonl", "a") as f:
        f.write(json.dumps(e, sort_keys=True) + "\n")
    return e


def spent(out) -> dict:
    f = Path(out) / "CPU_LEDGER.jsonl"
    rows = [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
    return {"cpu_s": round(sum(r["cpu_s"] for r in rows), 1), "wall_s": round(sum(r["wall_s"] for r in rows), 1), "entries": len(rows)}


if __name__ == "__main__":
    if sys.argv[1] == "charge":
        i = sys.argv.index("--")
        e = charge(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[i + 1:])
        print(json.dumps(e), "| total", json.dumps(spent(sys.argv[2])), file=sys.stderr)
        sys.exit(e["exit"])
    if sys.argv[1] == "domain":
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "ACTION_DOMAIN_V1.json").write_text(json.dumps(manifest(), indent=1, sort_keys=True))
