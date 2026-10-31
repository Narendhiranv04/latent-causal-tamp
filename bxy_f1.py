"""Approach B X/Y F1: analytic static endpoint / placement screen (Approach_B_Final_Methodology_2026-10-31 §3.1, §6.2, §6.3 step 1).

Sound, geometry-only rules over the immutable BD_GEN_V1 root record (no planner, no IK, no learned score, no outcome):
  identity    ID_UNKNOWN, ID_TARGET, ID_FIXED (immovable structure), LENGTH (> 6 relocations, bd_core.check_sequence)
  placement   DEST_NOT_LEGAL (outside the supported legal cells), NULL_RELOCATION (destination = the object's current cell),
              DEST_OCCUPIED (the placed disc overlaps any other body - stayed, already relocated, fixed or T - at that moment of the
              IDEAL object prefix; order-specific: A>c, B>c0(A) is legal, B>c0(A), A>c is not)
  endpoint    PAIR_OVERLAP (two discs of the final edited scene overlap; implied by DEST_OCCUPIED for a legal sequence, checked
              independently for Y-only edits)
  task        GOAL_BLOCKED (a relocated or staying body overlaps T's goal pose: the complete task cannot succeed, the scene is legal)
  policy      DUPLICATE_OBJECT (one object relocated twice: outside the declared catalogue scope, not a physical claim)
Scopes: an X query is admissible iff no identity/placement/policy rule fires; a Y query (edited scene) is admissible iff its endpoint is a
legal scene (identity + legal cells + no PAIR_OVERLAP). GOAL_BLOCKED removes a COMPLETE candidate from selection (it cannot succeed under
any motion), but neither query is labelled from it: F1 never creates a teacher label. Motion-specific negatives (planner failure, order
certificates such as ORDER_FIRST_ACTION) are F2 outcomes and are never produced here."""
from __future__ import annotations

import math

import bd_core as bc

X_RULES = ("ID_UNKNOWN", "ID_TARGET", "ID_FIXED", "LENGTH", "DEST_NOT_LEGAL", "NULL_RELOCATION", "DEST_OCCUPIED", "DUPLICATE_OBJECT")
Y_RULES = ("ID_UNKNOWN", "ID_TARGET", "ID_FIXED", "DEST_NOT_LEGAL", "PAIR_OVERLAP")
VERSION = "BXY_F1_V1"


def center(rec, cell):
    L = rec["scene"]["lattice"]
    return ((cell % L["cols"]) + 0.5) * L["pitch_m"], ((cell // L["cols"]) + 0.5) * L["pitch_m"]


def bodies(rec) -> dict:
    """{id: [x, y, radius, kind]} of S0 (stored poses), T included."""
    return {o["id"]: [o["xy_m"][0], o["xy_m"][1], o["radius_m"], o["kind"]] for o in rec["scene"]["objects"]}


def _hits(B, o, xy, r):
    return sorted(i for i, (x, y, ri, _) in B.items() if i != o and math.hypot(x - xy[0], y - xy[1]) < r + ri - 1e-12)


def _ident(rec, B, o):
    if o not in B:
        return "ID_UNKNOWN"
    if B[o][3] == "target" or o == "t0":
        return "ID_TARGET"
    if o in rec["fixed_ids"] or o not in rec["roles"]:
        return "ID_FIXED"
    return None


def _goal(rec, B) -> list:
    t = next(i for i, v in B.items() if v[3] == "target")
    return _hits({i: v for i, v in B.items() if i != t}, t, center(rec, rec["goal_cell"]), B[t][2])


def screen(rec, seq) -> dict:
    """F1 of one ordered prefix: X admissibility (sequential ideal placement), Y admissibility (its endpoint) and the complete-task flag."""
    B, v = bodies(rec), []
    seq = [(o, int(d)) for o, d in seq]
    if len(seq) + 1 > bc.MAX_ACTIONS:
        v.append({"rule": "LENGTH", "step": None})
    seen = set()
    for t, (o, d) in enumerate(seq):
        why = _ident(rec, B, o)
        if why:
            v.append({"rule": why, "step": t})
            continue
        if o in seen:
            v.append({"rule": "DUPLICATE_OBJECT", "step": t})
        seen.add(o)
        if d not in rec["scene"]["legal_cells"]:
            v.append({"rule": "DEST_NOT_LEGAL", "step": t})
            continue
        xy = center(rec, d)
        if math.hypot(B[o][0] - xy[0], B[o][1] - xy[1]) < 1e-9:
            v.append({"rule": "NULL_RELOCATION", "step": t})
        hit = _hits(B, o, xy, B[o][2])
        if hit:
            v.append({"rule": "DEST_OCCUPIED", "step": t, "with": hit})
        B[o][:2] = xy
    e = endpoint(rec, seq)
    return {"version": VERSION, "x_ok": not v, "x_violations": v, "y_ok": e["y_ok"], "y_violations": e["y_violations"],
            "goal_blocked": e["goal_blocked"], "complete_ok": not v and e["y_ok"] and not e["goal_blocked"]}


def endpoint(rec, edit) -> dict:
    """F1 of one edited scene S^q (Y query): final poses only, order-free. edit: [(o, cell)] in order or {o: cell}."""
    B, v = bodies(rec), []
    for o, d in (edit.items() if isinstance(edit, dict) else edit):
        why = _ident(rec, B, o)
        if why or int(d) not in rec["scene"]["legal_cells"]:
            v.append({"rule": why or "DEST_NOT_LEGAL", "object": o})
            continue
        B[o][:2] = center(rec, int(d))
    ids = sorted(B)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if math.hypot(B[a][0] - B[b][0], B[a][1] - B[b][1]) < B[a][2] + B[b][2] - 1e-12:
                v.append({"rule": "PAIR_OVERLAP", "objects": [a, b]})
    return {"y_ok": not v, "y_violations": v, "goal_blocked": _goal(rec, B) if not v else []}
