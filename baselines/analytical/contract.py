"""Common task contract, computed from PUBLIC inputs only (benchmark row {root_id, domain, inputs}).

A decision is REPAIR (ordered <= K_MAX relocations of distinct movable non-target objects, each to a declared legal cell that is free now,
was EMPTY IN THE ORIGINAL SCENE and is not the target's goal cell), NOOP or ABSTAIN.  `legality` gives the same verdict as
approach_b_final/benchmark.legality (tested); `prediction` emits the benchmark prediction line."""
from __future__ import annotations

K_MAX = 3
DECISIONS = ("REPAIR", "NOOP", "ABSTAIN")
PRIVATE_ROW_KEYS = ("K_legacy", "labels", "masks", "meta", "K")      # never needed; scrubbed by public_row


def public_row(row: dict) -> dict:
    """The learner-visible view of a snapshot / public row (drops every private key)."""
    return {"root_id": row["root_id"], "domain": row.get("domain") or ("3d" if row["root_id"].startswith("3d") else "2d"),
            "inputs": row["inputs"]}


def fixed_mask(inp: dict, dom: str) -> list[bool]:
    return [bool(a[3]) for a in inp["attrs"]] if dom == "2d" else [False] * len(inp["ids"])


def movable(inp: dict, dom: str) -> list[int]:
    """Movable non-target object indices (2D attrs[3] = fixed flag; every 3D non-target object is movable)."""
    fx = fixed_mask(inp, dom)
    return [i for i in range(len(inp["ids"])) if i != int(inp["tid"]) and not fx[i]]


def apply(inp: dict, prefix) -> list[int]:
    cells = [int(c) for c in inp["cells0"]]
    for o, d in prefix:
        cells[int(o)] = int(d)
    return cells


def legal_dests(inp: dict, cells) -> list[int]:
    """Declared legal cells that are free now, ORIGINALLY empty (a vacated source cell is never reused) and not the goal cell."""
    occ0, occ, g = {int(c) for c in inp["cells0"]}, {int(c) for c in cells}, int(inp["goal_cell"])
    return [int(d) for d in inp["legal_cells"] if int(d) not in occ0 and int(d) not in occ and int(d) != g]


def eligible(inp: dict, dom: str, prefix) -> list[int]:
    moved = {int(o) for o, _ in prefix}
    return [] if len(prefix) >= K_MAX else [o for o in movable(inp, dom) if o not in moved]


def legality(inp: dict, dom: str, prefix) -> str | None:
    """None if `prefix` is a legal REPAIR (1..K_MAX moves), else the violated rule (benchmark.legality names)."""
    if not 1 <= len(prefix) <= K_MAX:
        return "LENGTH"
    mov, cells, seen = set(movable(inp, dom)), apply(inp, []), set()
    for o, d in prefix:
        o, d = int(o), int(d)
        if not 0 <= o < len(inp["ids"]):
            return "UNKNOWN_OBJECT"
        if o not in mov:
            return "IMMOVABLE_OBJECT"
        if o in seen:
            return "OBJECT_MOVED_TWICE"
        if d not in legal_dests(inp, cells):
            return "ILLEGAL_DESTINATION"
        seen.add(o)
        cells[o] = d
    return None


def prediction(row: dict, decision: str, prefix=(), **extra) -> dict:
    """One benchmark prediction line (approach_b_final/benchmark.py format)."""
    assert decision in DECISIONS
    inp = row["inputs"]
    prefix = [(int(o), int(d)) for o, d in prefix] if decision == "REPAIR" else []
    if decision == "REPAIR":
        err = legality(inp, row["domain"], prefix)
        assert err is None, f"illegal committed repair {prefix}: {err}"
    moves = [{"object_id": inp["ids"][o], "object_index": o, "destination_cell": d} for o, d in prefix]
    return {"root_id": row["root_id"], "domain": row["domain"], "decision": decision, "moves": moves, **extra}
