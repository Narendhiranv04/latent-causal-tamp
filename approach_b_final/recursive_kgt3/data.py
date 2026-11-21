#!/usr/bin/env python3
"""recursive_kgt3 data layer: path guard, dynamic object padding, hypothetical-scene roots and temporary-target views (AUDIT A1/A2/A11/A12/A14).
Nothing here changes a frozen file: DynPad wraps placement.scene_features; HypoRoot subclasses search.Root; TaskView re-implements the audited
validation_k3/retarget.retarget (naren/k3-postablation-validation e9fa587c3b, 2D branch only) with the original-task reservation mask."""
import copy, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import placement as PL  # noqa: E402
import search as S  # noqa: E402

# ------------------------------------------------------------------ A11 path guard (planner processes only)
FORBID = ("private", "LABELS", "COVERAGE", "witness", "/G4/", "/G5/", "gifs", "g5_", "sel_", "dev_private")


def install_guard(allow):
    """Abort on any file open outside `allow` roots or matching a forbidden pattern (python-level opens incl. numpy/torch)."""
    allow = [str(Path(a).resolve()) for a in allow] + [sys.prefix, sys.base_prefix, "/usr", "/proc", "/sys", "/dev", "/etc", "/tmp/torchinductor"]

    def hook(ev, args):
        if ev != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        p = os.fsdecode(args[0])
        if not os.path.isabs(p):
            p = os.path.abspath(p)
        if any(f in p for f in FORBID):
            raise PermissionError(f"LEAKAGE GUARD: forbidden path {p}")
        if not any(p.startswith(a) for a in allow):
            raise PermissionError(f"LEAKAGE GUARD: path outside allowlist {p}")
    sys.addaudithook(hook)


# ------------------------------------------------------------------ A14 dynamic object padding
_ORIG_SF = PL.scene_features


def _scene_features_dyn(dom, pattr, cd, query, legal, *a, **k):
    n, base = len(cd), PL.MAXOBJ[dom]
    if n <= base:                                    # identical code path for n <= MAXOBJ (byte-identical outputs)
        return _ORIG_SF(dom, pattr, cd, query, legal, *a, **k)
    PL.MAXOBJ[dom] = n
    try:
        return _ORIG_SF(dom, pattr, cd, query, legal, *a, **k)
    finally:
        PL.MAXOBJ[dom] = base


def enable_dynpad():
    PL.scene_features = _scene_features_dyn


# ------------------------------------------------------------------ A12 + A1 temporary-target view
GOAL_IDX_2D = (6, 7)


def retarget2d(inp, tid=None, goal_cell=None):
    """Exactly validation_k3/retarget.retarget for dom='2d' (identity returns the input)."""
    new = copy.deepcopy(inp)
    old = inp["tid"]
    if goal_cell is not None:
        g = int(goal_cell)
        new["goal_cell"] = g
        new["goal"] = list(map(float, inp["cell_xy"][str(g)]))
        i, j = GOAL_IDX_2D
        new["ctx"][i], new["ctx"][j] = new["goal"]
    if tid is not None and int(tid) != old:
        t = int(tid)
        assert t != old and 0 <= t < len(inp["ids"])
        assert not inp["attrs"][t][3], "a fixed object cannot become the target"
        new["attrs"][t][1], new["attrs"][t][2] = 1.0, 0.0
        new["attrs"][old][1], new["attrs"][old][2] = 0.0, 1.0
        new["tid"] = t
    return new


class HypoRoot(S.Root):
    """search.Root for a HYPOTHETICAL scene S_p = Edit(S0, prefix) under task τ = (tid, goal) with the global reservation mask (A1/A2):
    movable  = objects ≠ current task target, ≠ ORIGINAL target T0, not fixed, not already relocated in the global prefix, not reserved
    legal    = declared legal cells − currently occupied − ORIGINALLY occupied (S0, declared grammar) − ORIGINAL goal G0 − current task goal
               − destinations reserved by pending enclosing actions
    The learner inputs are rebased (xy0/cells0 = S_p), i.e. local X/Y semantics start at q_ref in S_p (training-consistent); the ORIGINAL
    task's final Y is never computed here (models.score_Y_endpoint uses S0)."""

    def __init__(self, row0, prefix=(), task=None, reserved=(), rcells=(), tag=""):
        inp0 = row0["inputs"]
        inp = copy.deepcopy(inp0)
        for i, d in prefix:
            inp["cells0"][i] = int(d)
            inp["xy0"][i] = list(map(float, inp0["cell_xy"][str(int(d))]))
        if task is not None:
            inp = retarget2d(inp, task[0], task[1])
        rid = row0["root_id"] + (f"~P{len(prefix)}" if prefix else "") + (f"~TT{task[0]}_{task[1]}" if task else "") + tag
        super().__init__({"root_id": rid, "domain": "2d", "inputs": inp}, "2d")
        self.T0, self.G0 = int(inp0["tid"]), int(inp0["goal_cell"])
        self.occ_S0 = set(int(c) for c in inp0["cells0"])
        self.prefix = [(int(i), int(d)) for i, d in prefix]
        used = {i for i, _ in self.prefix} | set(int(r) for r in reserved)
        self.movable = [i for i in self.movable if i != self.T0 and i not in used]
        self.rcells = set(int(c) for c in rcells)            # destinations of still-pending enclosing actions (reserved)

    def legal_dests(self, cells):
        occ = set(cells)
        return [d for d in self.legal if d not in occ and d not in self.occ_S0 and d != self.G0 and d != self.goal and d not in self.rcells]


def check_sequence(row0, seq, max_len=12):
    """Global legality of a complete ordered sequence on S0 (declared grammar).  -> None or reason."""
    inp = row0["inputs"]
    T0, G0, occ0 = int(inp["tid"]), int(inp["goal_cell"]), set(int(c) for c in inp["cells0"])
    fixed = {i for i, a in enumerate(inp["attrs"]) if a[3]}
    if not 1 <= len(seq) <= max_len:
        return "LENGTH"
    cells = [int(c) for c in inp["cells0"]]
    seen = set()
    for i, d in seq:
        if i == T0:
            return "TARGET_MOVED"
        if i in fixed:
            return "FIXED_MOVED"
        if i in seen:
            return "OBJECT_TWICE"
        if d not in inp["legal_cells"]:
            return "ILLEGAL_CELL"
        if d in occ0:
            return "ORIGINALLY_OCCUPIED"
        if d == G0:
            return "GOAL_CELL"
        if d in cells:
            return "OCCUPIED_NOW"
        seen.add(i); cells[i] = d
    return None


def jl(p):
    return [json.loads(l) for l in open(p)]
