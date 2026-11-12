#!/usr/bin/env python3
"""2D finalized physical X / Y adapter (unchanged teacher): boots the 2D class-quota dataset code with the record's own geometry implementation
(fastgeom1 iff `geometry_impl` says so) and bxy_teacher (BXY_X_TEACHER_V1 / BXY_Y_TEACHER_V1, approach-b-universal-search, identical to the
68183081d teacher used for every 2D label), exactly as final_dataset_generation/k3_hard/xy2d.py.  X = ordered relocations with carried state +
connector to q_ref + independent replay; Y = target from q_ref at the endpoint + independent replay.  One exact DetPhysics cache per root.

    python teacher2d.py parity N      re-run N reused xy2d_all roots and compare (sanity check of this host / paths)"""
from __future__ import annotations

import json, os, sys
from pathlib import Path

ABF = Path(os.environ.get("ABF_ROOT", "/scratch/nav/approachb_final"))
CODE = ABF / "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code"
WT = ABF / "teacher2d_wt"
_M = {}


def boot(geom):
    if _M.get("geom") == geom:
        return
    if "geom" in _M:
        raise RuntimeError("one geometry implementation per process")
    sys.path[:0] = ([str(CODE / "py310_shim")] if sys.version_info < (3, 11) else []) + [str(CODE / "dataset-bd"), str(CODE), str(CODE / "latent-causal-tamp")]
    os.chdir(CODE / "latent-causal-tamp")
    import warnings
    warnings.filterwarnings("ignore")
    if geom == "fastgeom1":
        import fastgeom
        fastgeom.install()
    import bd_2d  # noqa: F401
    sys.path.insert(0, str(WT))
    import bxy_teacher as T
    _M.update(geom=geom, T=T, E=T.env(), wout=str(ABF / "runs/teacher2d_witnesses"))


def query(rec, seq, cache, kind):
    """kind X or Y; seq [(object id, cell)].  -> compact result (y = 0 / 1, status, phase, replay, witness ids)."""
    T, E = _M["T"], _M["E"]
    rid = rec["ids"]["root_id"]
    seq = [(o, int(d)) for o, d in seq]
    if kind == "X":
        r = T.x_query(E, rid, rec, seq, cache, out=_M["wout"])
        return {"x": r.get("y"), "status": r.get("teacher_status"), "phase": r.get("failed_phase"), "replay": r.get("independent_replay"),
                "witnesses": (r.get("witness_relocations") or []) + ([r["witness_connector"]] if r.get("witness_connector") else []),
                "budget_spent": r.get("budget_spent")}
    r = T.y_query(E, rid, rec, seq, cache, out=_M["wout"])
    return {"y": r.get("y"), "status": r.get("teacher_status"), "replay": r.get("independent_replay"), "witness": r.get("target_witness")}


def parity(n):
    G = ABF / "mirror/boltzmann_lfd/final_dataset_generation/k3_hard"
    ref = [json.loads(l) for l in open(G / "xy2d_all.jsonl")][:n]
    boot("fastgeom1")
    import itertools
    agree = tot = 0
    for r in ref:
        p = G / "d2/store/roots" / f"{r['root_id']}.json"
        rec = json.loads((p if p.exists() else G / "d2_gvlab/store/roots" / p.name).read_text())
        mini = next(b for b in rec["labels"]["B"] if b["role"] == "minimal" and b["y"] == 1)
        assign = [(o, int(d)) for o, d in mini["sequence"]]
        cache = {}
        for q in itertools.permutations(assign):
            k = "".join(o[-1] for o, _ in q)
            got = query(rec, list(q), cache, "X")["x"]
            agree += got == r["x"][k]["x"]; tot += 1
        got = query(rec, assign, cache, "Y")["y"]
        agree += got == r["y"]["y"]; tot += 1
    print(json.dumps({"parity_queries": tot, "agree": agree}))


if __name__ == "__main__":
    if sys.argv[1:2] == ["parity"]:
        parity(int(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
