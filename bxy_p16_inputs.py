"""BXY-P16 label-free learner-input adapter for V2 (P15 pilot) and V2.1 (P16) roots.

The scorer input of a root is EXACTLY the frozen P-min representation (learn_data.root_record -> data.learner_tensors_v2 + frozen DINOv2-small
patch tokens of the rendered initial scene, area-weighted per instance), computed from four record fields only: scene (objects, robot q,
lattice), goal_cell, q0 and q_ref. Nothing else of a record is read -- not labels, catalogue roles / kinds, minimal / y_full flags,
travel, failed_step, verified_K, teacher outcomes or witnesses, construction intent (spec, K_intent, K_geom, options, harmful cells) or the
root's wave / family. q_ref must equal q0 and the scene robot state (the pinned protocol of every corpus so far); a root with q_ref != q0
is refused rather than silently encoded with q0. The cache key is an outcome-free hash of exactly those fields plus the renderer / DINO /
tensor-layout identity. Zero image embeddings are never substituted for the trained DINOv2 features."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np

READ = ("scene", "goal_cell", "q0", "q_ref")
RENDER_SOURCES = ("learn_data.py", "data.py", "scene.py", "geometry.py", "config.toml")


def identity() -> dict:
    import learn_data as ld
    return {"dino": list(ld.DINO), "image_px": ld.IMAGE_PX, "grid": ld.GRID, "input_keys": list(ld.INPUT_KEYS),
            "sources": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in RENDER_SOURCES}}


def view(rec) -> dict:
    """The only part of a record the adapter may see (deep copy; q_ref defaults to q0 for P-min / P15 records, which pin q_ref = q0)."""
    v = {k: copy.deepcopy(rec[k]) for k in READ if k in rec}
    v.setdefault("q_ref", list(v["q0"]))
    if not (np.allclose(v["q_ref"], v["q0"], atol=0) and np.allclose(v["scene"]["robot"]["q_rad"], v["q0"], atol=0)):
        raise ValueError("q_ref differs from q0 / the scene robot state: the frozen tensors carry only one robot state")
    return v


def key(rec) -> str:
    v = view(rec)
    return "sha256:" + hashlib.sha256(json.dumps({"view": v, "id": identity()}, sort_keys=True).encode()).hexdigest()


_DINO = []


def inputs(root_key, rec, dino=None) -> dict:
    """{"inputs": {tensor: array}, "ids": [object ids in storage order], "anchor_hash", "q_ref", "cache_key"}."""
    import config as cf
    import learn_data as ld
    from scene import scene_from_dict
    if dino is None:
        if not _DINO:
            _DINO.append(ld.dino())
        dino = _DINO[0]
    v = view(rec)
    r = ld.root_record(cf.load_config("config.toml"), *dino, root_key, scene_from_dict(v["scene"]), v["goal_cell"], [], [], {}, "dev", "BXY_P16_ADAPTER")
    return {"inputs": r["inputs"], "ids": r["audit"]["ids"], "anchor_hash": r["audit"]["anchor_hash"], "q_ref": v["q_ref"], "cache_key": key(rec)}


def build(roots: dict, out) -> dict:
    """Cache {root: inputs} for the given records (torch file); returns the manifest."""
    import torch
    rows = {k: inputs(k, r) for k, r in sorted(roots.items())}
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"version": "BXY_P16_INPUTS_V1", "identity": identity(), "roots": rows}, out)
    return {"roots": len(rows), "file": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "identity": identity()}


def privileged_mutation(rec) -> dict:
    """A copy of rec with every non-READ field scrambled (labels, roles, construction intent, catalogue, ids, spec...)."""
    m = copy.deepcopy(rec)
    for k in list(m):
        if k in READ:
            continue
        m[k] = {"scrambled": True, "was": str(type(m[k]).__name__)} if not isinstance(m[k], list) else ["scrambled"]
    m["labels"] = {"original": {"y": 1 - int(bool(rec.get("labels", {}).get("original", {}).get("y", 0)))}}
    m["roles"] = {o: "intended_blocker" for o in rec.get("roles", {})}
    return m


def p_min_equivalence(n=6) -> dict:
    """Recompute the stored P-min RECORDS.pt inputs for n roots through this adapter; max abs difference per tensor."""
    import torch
    import bxy_data as bd
    d = torch.load("runs/approach_b/bd2d_lb_v1/RECORDS.pt", weights_only=False)
    R, out = bd.roots(), {}
    for r0 in d["roots"][:n]:
        k = r0["audit"]["root"]
        x = inputs(k, R[k])
        out[k] = {"max_abs": {a: float(np.abs(np.asarray(r0["inputs"][a]) - np.asarray(x["inputs"][a])).max()) for a in r0["inputs"]},
                  "ids_equal": x["ids"] == r0["audit"]["ids"], "anchor_equal": x["anchor_hash"] == r0["audit"]["anchor_hash"]}
    return out
