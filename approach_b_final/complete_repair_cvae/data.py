#!/usr/bin/env python3
"""Complete-repair cVAE data (plan.md 3, 4.1): public encoder inputs per root and TRAIN-only supervision.

Public inputs (learner-visible only, built from the contracts view `inputs`): per-object tokens in ORIGINAL slot order (the frozen sampler's
14 scene_features columns with the target as reference, normalized with the bundle's TRAIN-only scalers, + goal-relative offsets + movable flag),
per-cell features, the static legal destination mask (support cell, not occupied in S0, not the goal) and the global context (S0 occupancy +
placement.task_features for the target).  Nothing here reads K, labels, witnesses or blocker identities.

Supervision (TRAIN only, training loader side):
  * repairs: contracts.positive_assignments + contracts.v3_grammar (identical corpus to the released per-object sampler); every verified X=1
    order of a Y=1 endpoint, deduplicated; weight 1 / (|A_i| |O_iA|) so every root carries total weight 1 (= placement.repair_data);
  * root decision (NOOP / REPAIR / ABSTAIN / masked): see root_label()."""
from __future__ import annotations

import hashlib, json, math, os, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ABF = HERE.parent
if str(ABF) not in sys.path:
    sys.path.insert(0, str(ABF))
import contracts as CT  # noqa: E402
import placement as PL  # noqa: E402
import search as S  # noqa: E402

H = Path.home()
TRAIN_SNAP = Path(os.environ.get("CR_TRAIN_SNAP", H / "abf_v32/snap_out/snapshot/abf_v32_fb0eef4f5ff433ee"))
VAL_SNAP = Path(os.environ.get("CR_VAL_SNAP", H / "abf_v3_laptop/root/snapshot/abf_9de85710c2a7103f"))
BUNDLE = Path(os.environ.get("CR_BUNDLE", H / "abf_v34/approach_b_bundle"))
RUNS = Path(os.environ.get("CR_RUNS", H / "cr_cvae_runs"))           # checkpoints, pools, timing (never committed)
PRIV = Path(os.environ.get("CR_PRIV", H / "cr_cvae_private"))        # private cohort index / labels (evaluator only, never committed)
GRID = {"2d": (8, 8), "3d": (6, 6)}
MAXOBJ = PL.MAXOBJ
KMAX = 3
NTOK, NCELL = 18, 15                                                  # token / cell feature widths
CLASSES = ("NOOP", "REPAIR", "ABSTAIN")
MASKED = -1


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rows(dom, snap, split=None):
    return [r for r in map(json.loads, open(Path(snap) / f"data{dom}.jsonl")) if split is None or r["split"] == split]


def scalers(dom):
    sc_dir = os.environ.get("CR_SCALERS_DIR")                 # R10: canonical-TRAIN Q2 scalers (release q2/q2_<dom>/scalers.json)
    sc = json.loads(((Path(sc_dir) / f"q2_{dom}") if sc_dir else (BUNDLE / dom)).joinpath("scalers.json").read_text())
    return np.array(sc["mean"], np.float32), np.array(sc["std"], np.float32)


# ------------------------------------------------------------------------------------------------ public encoder inputs
def encode(dom, row, mu_sd=None):
    """Public root -> dict of numpy arrays (slot order; padded to MAXOBJ):
    tok [MAXOBJ, NTOK], tmask [MAXOBJ], movable [MAXOBJ], cell [N, NCELL], legal0 [N], glob [N + task_dim]."""
    mu, sd = mu_sd or scalers(dom)
    R, C = GRID[dom]
    N = R * C
    root = S.Root(row, dom)
    inp = row["inputs"]
    n = len(root.ids)
    assert n <= MAXOBJ[dom], (row["root_id"], n)
    cd = {root.ids[i]: c for i, c in enumerate(root.cells0)}
    F, Mk, occ, _ = PL.scene_features(dom, root.pattr, cd, root.ids[root.tid], root.legal)
    F = (F - mu) / sd * Mk[:, None]
    order = [root.tid] + sorted((i for i in range(n) if i != root.tid), key=lambda i: root.ids[i])   # scene_features: query first, sorted ids
    assert [root.ids[i] for i in order] == [root.ids[root.tid]] + sorted(o for o in root.ids if o != root.ids[root.tid])
    g, tc = int(inp["goal_cell"]), root.cells0[root.tid]
    gr, gc, tr, tcc = g // C, g % C, tc // C, tc % C
    tok, tmask, mov = np.zeros((MAXOBJ[dom], NTOK), np.float32), np.zeros(MAXOBJ[dom], bool), np.zeros(MAXOBJ[dom], bool)
    for j, i in enumerate(order):                                         # feature row j belongs to original slot i
        r, c = divmod(root.cells0[i], C)
        tok[i, :14] = F[j]
        tok[i, 14:17] = [(gr - r) / (R - 1), (gc - c) / (C - 1), max(abs(gr - r), abs(gc - c)) / (R - 1)]
        tok[i, 17] = float(i in root.movable)
        tmask[i], mov[i] = True, i in root.movable
    support = np.zeros(N, bool)
    support[root.legal] = True
    legal0 = np.zeros(N, bool)
    legal0[root.legal_dests(root.cells0)] = True                          # support, not occupied in S0, not the goal (static grammar)
    base = (-0.14, 0.32) if dom == "2d" else (0.0, 0.0)
    cell = np.zeros((N, NCELL), np.float32)
    for j in range(N):
        r, c = divmod(j, C)
        x, y = PL.cell_xy(dom, j)
        dx, dy = x - base[0], y - base[1]
        cell[j] = [r / (R - 1), c / (C - 1), (x - mu[6]) / sd[6], (y - mu[7]) / sd[7], (math.hypot(dx, dy) - mu[8]) / sd[8], math.atan2(dy, dx) / math.pi,
                   (gr - r) / (R - 1), (gc - c) / (C - 1), max(abs(gr - r), abs(gc - c)) / (R - 1),
                   (tr - r) / (R - 1), (tcc - c) / (C - 1), max(abs(tr - r), abs(tcc - c)) / (R - 1), float(j == g), occ[j], float(support[j])]
    glob = np.concatenate([occ, PL.task_features(dom, inp, root.cells0, root.tid, True)]).astype(np.float32)
    return {"tok": tok, "tmask": tmask, "movable": mov, "cell": cell, "legal0": legal0, "glob": glob}


def glob_dim(dom):
    return GRID[dom][0] * GRID[dom][1] + PL.task_dim(dom)


def stack(encs):
    """list of encode() dicts -> dict of stacked numpy arrays."""
    return {k: np.stack([e[k] for e in encs]) for k in encs[0]}


# ------------------------------------------------------------------------------------------------ TRAIN / VAL supervision
def verified_orders(row):
    """-> {assignment key: sorted list of distinct verified X=1 orders} over V3-legal Y=1 endpoints (released sampler corpus)."""
    out = {}
    for k, a in CT.positive_assignments(row).items():
        if CT.v3_grammar(row["inputs"], a["assignment"]):
            continue
        out[k] = sorted({json.dumps([[int(o), int(d)] for o, d in s]) for s in a["orders"]})
    return out


def root_label(row, orders):
    """Root decision label from existing finalized labels only (plan 3.2):
    NOOP    verified Y(empty) = 1 (legacy K0);
    REPAIR  verified Y(empty) = 0 and >= 1 verified V3-legal nonempty repair, legacy K in {1, 2, 3};
    ABSTAIN verified Y(empty) = 0, legacy NONE and no verified legal repair (benchmark-relative: legacy teacher scope, not impossibility);
    MASKED  anything else (Y(empty) missing, legacy K / finalized label disagreement, NONE with a verified repair, K0 with Y(empty) = 0)."""
    ye = next((y["y"] for y in row["labels"]["Y"] if not y["edit"]), None)
    K = row["K_legacy"]
    if ye == 1:
        return 0 if K == "0" else MASKED
    if ye != 0:
        return MASKED
    if K in ("1", "2", "3"):
        return 1 if orders else MASKED
    if K == "NONE":
        return 2 if not orders else MASKED
    return MASKED


def supervision(dom, snap, split):
    """-> (root rows, triples [(root idx, seq, weight)], labels [per root]) for one split.  weight = 1 / (|A_i| |O_iA|)."""
    rr = rows(dom, snap, split)
    triples, labels = [], []
    for i, r in enumerate(rr):
        vo = verified_orders(r)
        labels.append(root_label(r, vo))
        for k, os_ in sorted(vo.items()):
            for s in os_:
                triples.append((i, json.loads(s), 1.0 / len(vo) / len(os_)))
    return rr, triples, labels


def seq_arrays(seqs):
    """list of [[obj, cell], ...] (len 1..3) -> obj [B, 3], dst [B, 3], length [B] (padding = 0)."""
    B = len(seqs)
    o, d, n = np.zeros((B, KMAX), np.int64), np.zeros((B, KMAX), np.int64), np.zeros(B, np.int64)
    for b, s in enumerate(seqs):
        assert 1 <= len(s) <= KMAX, s
        n[b] = len(s)
        for t, (oo, dd) in enumerate(s):
            o[b, t], d[b, t] = oo, dd
    return o, d, n


def static_legal(enc, seq):
    """Static grammar of an ordered sequence on encode() arrays -> violated rule or None (mirrors benchmark.legality)."""
    if not 1 <= len(seq) <= KMAX:
        return "LENGTH"
    moved, reserved = set(), set()
    for o, d in seq:
        if not (0 <= o < len(enc["movable"]) and enc["movable"][o]):
            return "IMMOVABLE_OBJECT"
        if o in moved:
            return "OBJECT_MOVED_TWICE"
        if not enc["legal0"][d] or d in reserved:
            return "ILLEGAL_DESTINATION"
        moved.add(o); reserved.add(d)
    return None


def stratum_hash(salt, rid):
    return hashlib.sha256(f"{salt}|{rid}".encode()).hexdigest()
