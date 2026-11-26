"""R2.1-A matched object-count perturbations (evaluator side).  Predeclared rule (no outcome-dependent choice):
  * only ADD legal, non-overlapping movable distractor bodies; never remove or move existing bodies (real blockers stay);
  * candidate cells: declared legal support, unoccupied, not the goal, Chebyshev distance >= 2 from every PROTECTED cell (target source, goal,
    every mover source / destination of the family's fixed repair and of its negative control);
  * cells ordered by sha256(root | cell | "R2_N"); variant +k takes the FIRST k cells, so nested variants share distractors (prefix property);
  * 2D body = the root's own obstacle radius (all TRAIN bodies r = 0.024), kind obstacle, movable (roles entry "distractor:added_r2");
    3D body = shape / size / height copied from the root's non-target object that is first in sha256(root | id) order;
  * root id gets a "~N+k" tag (own planner keys / caches); target, goal, robot, q_ref, movers, destinations and order are unchanged.
If fewer than k cells qualify, the variant is NOT built (reported as unsupported) -- high-N examples are never invented."""
from __future__ import annotations

import copy, hashlib

COLS = {"2d": None, "3d": 6}


def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def cheb(dom, a, b, cols):
    ra, ca = divmod(int(a), cols); rb, cb = divmod(int(b), cols)
    return max(abs(ra - rb), abs(ca - cb))


def cells_2d(raw):
    return {o["id"]: int(o["cell"]) for o in raw["scene"]["objects"]}


def cells_3d(raw):
    return {o: int(rc[0]) * 6 + int(rc[1]) for o, rc in raw["initial_cells"].items()}


def candidates(dom, raw, protect):
    if dom == "2d":
        sc = raw["scene"]; cols = sc["lattice"]["cols"]; legal = [int(c) for c in sc["legal_cells"]]; occ = set(cells_2d(raw).values()); goal = int(raw["goal_cell"])
    else:
        cols = 6; legal = list(range(36)); occ = set(cells_3d(raw).values()); goal = int(raw["goal"][0]) * 6 + int(raw["goal"][1])
    rid = raw["ids"]["root_id"]
    ok = [c for c in legal if c not in occ and c != goal and all(cheb(dom, c, p, cols) >= 2 for p in set(protect) | {goal})]
    return sorted(ok, key=lambda c: _h(f"{rid}|{c}|R2_N"))


def add(dom, raw, k, protect):
    """-> (new raw record, added ids) or (None, reason)."""
    cand = candidates(dom, raw, protect)
    if len(cand) < k:
        return None, f"only {len(cand)} qualifying cells < {k}"
    r = copy.deepcopy(raw)
    rid = raw["ids"]["root_id"]
    added = []
    if dom == "2d":
        sc = r["scene"]; pitch, cols = sc["lattice"]["pitch_m"], sc["lattice"]["cols"]
        rad = next(o["radius_m"] for o in sc["objects"] if o["kind"] == "obstacle") if any(o["kind"] == "obstacle" for o in sc["objects"]) else 0.024
        used = {o["id"] for o in sc["objects"]}
        for j, c in enumerate(cand[:k]):
            oid = next(f"o{n:02d}" for n in range(50, 99) if f"o{n:02d}" not in used); used.add(oid)
            sc["objects"].append({"cell": c, "id": oid, "kind": "obstacle", "radius_m": rad, "support": "table",
                                  "xy_m": [round(pitch * (c % cols + 0.5), 10), round(pitch * (c // cols + 0.5), 10)]})
            r["roles"][oid] = "distractor:added_r2"; added.append(oid)
        r["ids"] = {**r["ids"], "root_id": f"{rid}~N+{k}"}
        sc["root_id"] = r["ids"]["root_id"]
    else:
        tmpl = sorted((o for o in r["objects"] if o["id"] != "t0"), key=lambda o: _h(f"{rid}|{o['id']}"))
        if not tmpl:
            return None, "no non-target template body"
        t = tmpl[0]
        used = {o["id"] for o in r["objects"]}
        for c in cand[:k]:
            oid = next(f"o{n:02d}" for n in range(50, 99) if f"o{n:02d}" not in used); used.add(oid)
            r["objects"].append({**{kk: v for kk, v in t.items() if kk != "id"}, "id": oid})
            r["initial_cells"][oid] = [c // 6, c % 6]
            r.setdefault("roles", {})[oid] = "distractor:added_r2"; added.append(oid)
        r["ids"] = {**r["ids"], "root_id": f"{rid}~N+{k}"}
    r["r2_perturbation"] = {"rule": "R2_N_ADD_V1", "k": k, "added": added, "protect": sorted(set(int(p) for p in protect)), "source_root": rid}
    return r, added
