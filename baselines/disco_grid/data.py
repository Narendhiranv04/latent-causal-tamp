#!/usr/bin/env python3
"""DISCO-Grid data loading, split hygiene verification, static action grammar, and Q2 dataset interface.

Enforces the strict learner input boundary (DISCO_plan.md Sections 3 & 5):
- Learner observations use only `row["inputs"]` (object positions, geometry attributes, occupancy/support mask,
  target/goal, fixed/movable flags, moved-object mask, remaining steps, and declared q_ref context).
- Ground-truth blocker IDs, legacy K/NONE labels, X/Y labels, and teacher witnesses never enter learner inputs.
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

ABF_ROOT = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
DISCO_ROOT = Path(os.environ.get("DISCO_ROOT", "/scratch/nav/disco_grid"))
MIRROR = ABF_ROOT / "mirror"
LAPTOP_PREFIX = "/home/naren/Desktop"

BASE_SNAP = ABF_ROOT / "snapshot/abf_9de85710c2a7103f"
V2_SNAP = ABF_ROOT / "snapshot/abf_v2_7d146b53e4b92fe4"
V3_SNAP = Path("/scratch/nav/abf_v3/stores/snapshot/abf_v3_e8a496bc66266fca")

GRID_SHAPE = {"2d": (8, 8), "3d": (6, 6)}
MAX_OBJ = {"2d": 20, "3d": 16}
SPLITS = ("train", "val", "test")


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def map_mirror_path(p: str | Path) -> Path:
    s = str(p)
    if s.startswith(LAPTOP_PREFIX):
        return MIRROR / s[len(LAPTOP_PREFIX) + 1 :]
    return Path(s)


def verify_snapshot_lock(snap_dir: Path = BASE_SNAP) -> dict[str, Any]:
    lock_path = Path(snap_dir) / "data_snapshot.lock.json"
    lock = json.loads(lock_path.read_text())
    file_checks = {}
    for fname, expected_sha in lock["files"].items():
        actual_sha = sha256_file(Path(snap_dir) / fname)
        file_checks[fname] = (actual_sha == expected_sha)
    return {
        "snapshot_id": lock["snapshot_id"],
        "lock_sha256": sha256_file(lock_path),
        "files_ok": file_checks,
        "all_ok": all(file_checks.values()),
        "teachers": lock.get("teachers", {}),
    }


def load_snapshot_rows(dom: str, split: str | None = None, snap_dir: Path = BASE_SNAP) -> list[dict[str, Any]]:
    dom_l = dom.lower()
    assert dom_l in ("2d", "3d"), f"Invalid domain: {dom}"
    jsonl_path = Path(snap_dir) / f"data{dom_l}.jsonl"
    target_split = "val" if split in ("valsub", "valrest") else split
    rows = [
        json.loads(line)
        for line in open(jsonl_path)
        if target_split is None or json.loads(line)["split"] == target_split
    ]
    if split == "valsub":
        out = []
        for k_cls in ("0", "1", "2", "3", "NONE"):
            cls_rows = [r for r in rows if r["K_legacy"] == k_cls]
            cls_rows.sort(key=lambda r: hashlib.sha256(r["root_id"].encode()).hexdigest())
            out.extend(cls_rows[:60])
        return out
    if split == "valrest":
        valsub_ids = {r["root_id"] for r in load_snapshot_rows(dom_l, "valsub", snap_dir)}
        return [r for r in rows if r["root_id"] not in valsub_ids]
    return rows


def check_split_hygiene(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fam_splits: dict[str, set[str]] = collections.defaultdict(set)
    lay_splits: dict[str, set[str]] = collections.defaultdict(set)
    root_splits: dict[str, set[str]] = collections.defaultdict(set)
    for r in rows:
        sp = r["split"]
        root_splits[r["root_id"]].add(sp)
        if r.get("parent_family_id"):
            fam_splits[r["parent_family_id"]].add(sp)
        if r.get("layout_root_id"):
            lay_splits[r["layout_root_id"]].add(sp)
    return {
        "n_roots": len(rows),
        "unique_roots": len(root_splits),
        "root_split_conflicts": sum(len(v) > 1 for v in root_splits.values()),
        "family_split_conflicts": sum(len(v) > 1 for v in fam_splits.values()),
        "layout_split_conflicts": sum(len(v) > 1 for v in lay_splits.values()),
    }


_SEL_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def raw_root_path(dom: str, root_id: str) -> Path:
    dom_u = dom.upper()
    if dom_u not in _SEL_CACHE:
        g_dir = MIRROR / "boltzmann_lfd/final_dataset_generation"
        if dom_u == "2D":
            sel_file = g_dir / "k3_hard/2D_K3_STRENGTH_SELECTION_V3.json"
        else:
            sel_file = g_dir / "FINAL_3D_DATASET_V4/FINAL_3D_SELECTION_MANIFEST.json"
        _SEL_CACHE[dom_u] = {r["root_id"]: r for r in json.loads(sel_file.read_text())["rows"]}
    sel = _SEL_CACHE[dom_u][root_id]
    if dom_u == "2D":
        ds2 = MIRROR / "rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota"
        if sel["source"] == "ORIGINAL_SELECTED":
            return ds2 / "raw/roots" / f"{root_id}.json"
        return map_mirror_path(sel["host_store"]) / "roots" / f"{root_id}.json"
    src3 = MIRROR / "rss3d_final_src"
    p = sel["path"]
    return map_mirror_path(p) if str(p).startswith("/") else src3 / p


# ---------------------------------------------------------------------------
# Static Action Grammar (DISCO_plan.md Section 3.1 & Approach B V3 Section 0.1.8)
# ---------------------------------------------------------------------------

def movable_object_indices(inp: dict[str, Any], dom: str) -> list[int]:
    """Eligible movable non-target object indices (0-based in inp['ids'])."""
    dom_l = dom.lower()
    tid = int(inp["tid"])
    attrs = inp["attrs"]
    out = []
    for i, a in enumerate(attrs):
        if i == tid:
            continue
        is_fixed = bool(a[3]) if (dom_l == "2d" and len(a) >= 4) else False
        if not is_fixed:
            out.append(i)
    return out


def legal_static_destinations(inp: dict[str, Any], current_cells: list[int] | None = None) -> list[int]:
    """D0 = declared_support_cells - occupied_cells_of_original_root - {target_goal_cell},
    minus any cells already used in the current prefix (`current_cells`).
    Never allows reusing a cell vacated by an earlier move (`occ0` always excluded).
    """
    occ0 = {int(c) for c in inp["cells0"]}
    occ_now = {int(c) for c in (current_cells if current_cells is not None else inp["cells0"])}
    goal = int(inp["goal_cell"])
    return [
        int(d)
        for d in inp["legal_cells"]
        if int(d) not in occ0 and int(d) not in occ_now and int(d) != goal
    ]


def legal_actions_at_prefix(
    inp: dict[str, Any],
    dom: str,
    prefix: list[tuple[int, int]],
    include_stop: bool = True,
) -> dict[str, Any]:
    """Return legal (obj_idx, dest_cell) actions and whether STOP is legal at `prefix`."""
    depth = len(prefix)
    moved = {int(o) for o, _ in prefix}
    cells = list(map(int, inp["cells0"]))
    for o, d in prefix:
        cells[int(o)] = int(d)
    if depth >= 3:
        return {
            "eligible_objects": [],
            "legal_destinations": [],
            "relocation_actions": [],
            "can_stop": include_stop,
            "current_cells": cells,
        }
    elig_objs = [o for o in movable_object_indices(inp, dom) if o not in moved]
    leg_dests = legal_static_destinations(inp, cells)
    reloc_actions = [(o, d) for o in elig_objs for d in leg_dests]
    return {
        "eligible_objects": elig_objs,
        "legal_destinations": leg_dests,
        "relocation_actions": reloc_actions,
        "can_stop": include_stop,
        "current_cells": cells,
    }


def validate_repair_sequence(inp: dict[str, Any], dom: str, seq: list[tuple[int, int]]) -> list[str]:
    """Check a complete corrective sequence `[(obj_idx, dest_cell), ...]` (length 0..3) against static grammar.
    Returns list of violation strings ([] means valid).
    """
    if not seq:
        return []
    violations = []
    if len(seq) > 3:
        violations.append("length_gt_3")
    objs = [int(o) for o, _ in seq]
    dests = [int(d) for _, d in seq]
    if len(set(objs)) != len(objs):
        violations.append("object_moved_twice")
    if int(inp["tid"]) in objs:
        violations.append("target_moved")
    mov = set(movable_object_indices(inp, dom))
    if any(o not in mov for o in objs):
        violations.append("fixed_or_invalid_object_moved")
    if len(set(dests)) != len(dests):
        violations.append("shared_destination")
    legal_set = {int(c) for c in inp["legal_cells"]}
    occ0 = {int(c) for c in inp["cells0"]}
    goal = int(inp["goal_cell"])
    if any(d not in legal_set for d in dests):
        violations.append("not_support_cell")
    if any(d in occ0 for d in dests):
        violations.append("initially_occupied_cell_reused")
    if goal in dests:
        violations.append("target_goal_cell_used")
    return violations


# ---------------------------------------------------------------------------
# Q2 Isolated Placement Data Interface
# ---------------------------------------------------------------------------

def load_q2_dataset(dom: str, q2_root: Path | None = None) -> dict[str, Any]:
    dom_l = dom.lower()
    dpath = (q2_root or (ABF_ROOT / "data")) / f"q2_{dom_l}"
    scalers = json.loads((dpath / "scalers.json").read_text())
    rows_meta = json.loads((dpath / "rows.json").read_text())
    npz = np.load(dpath / "features.npz")
    return {
        "domain": dom_l,
        "path": str(dpath),
        "scalers": scalers,
        "roots": rows_meta["roots"],
        "status": rows_meta["status"],
        "block": rows_meta["block"],
        "obj": npz["obj"],
        "mask": npz["mask"],
        "occ": npz["occ"],
        "legal": npz["legal"],
        "split": npz["split"],
        "dest": npz["dest"],
        "label": npz["label"],
        "ctx": npz["ctx"],
        "src": npz["src"],
    }
