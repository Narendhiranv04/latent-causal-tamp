#!/usr/bin/env python3
"""V3.4 amendment (2026-11-18): GEOMETRIC layout fingerprint = sorted per-object (cell, shape/size/height | radius/kind flags, rounded 1e-6)
+ target cell + goal cell.  Two roots collide only if they are the same physical scene.  The cell-level fingerprint (cells + target + goal)
stays recorded per cohort root as a flag for the sensitivity analysis.  Historical sources = exactly those of the cell-level set: snapshot rows
(V1-V3.3) and every historical root file under the same directories (incl. the V3.3 pilot).

    v34_geomfp.py EXCL_DIR      -> EXCL_DIR/EXCL{2D,3D}_GEOM.json  {"geom_fp": [...], "n_sources": {...}}"""
import collections, glob, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contracts as CT  # noqa: E402


def geom_fp(v):
    objs = sorted([int(c)] + [round(float(a), 6) for a in at] for c, at in zip(v["cells0"], v["attrs"]))
    return hashlib.sha256(json.dumps([objs, int(v["cells0"][v["tid"]]), int(v["goal_cell"])], separators=(",", ":")).encode()).hexdigest()


def main(excl):
    H = os.path.expanduser("~")
    S = json.loads((Path(excl) / "EXCL_SUMMARY.json").read_text())
    fp, n = {"2d": set(), "3d": set()}, collections.Counter()
    for s in S["snapshots"]:
        for d in ("2d", "3d"):
            f = Path(s) / f"data{d}.jsonl"
            if f.exists():
                for l in open(f):
                    fp[d].add(geom_fp(json.loads(l)["inputs"])); n[f"snapshot_{d}"] += 1
    dirs = set()
    for r in [H + "/Desktop/rss-placement-ready-v2", H + "/Desktop/rss3d_final_src", H + "/Desktop/boltzmann_lfd/final_dataset_generation",
              H + "/Desktop/boltzmann_lfd/order_classification_3d", H + "/abf_v3_laptop", H + "/abf_v33/fresh"]:
        for d in glob.glob(r + "/**/roots", recursive=True):
            if "/.claude/" not in d:
                dirs.add(os.path.realpath(d))
    for d in sorted(dirs):
        for f in glob.glob(d + "/*.json"):
            try:
                rec = json.loads(open(f, "rb").read())
                dom = "2d" if "scene" in rec else "3d" if "initial_cells" in rec else None
                if dom is None:
                    n["skip"] += 1
                    continue
                fp[dom].add(geom_fp(CT.view2d(rec) if dom == "2d" else CT.view3d(rec))); n[f"rootfile_{dom}"] += 1
            except Exception:  # noqa: BLE001
                n["unreadable_or_view_fail"] += 1
    for d in fp:
        (Path(excl) / f"EXCL{d.upper()}_GEOM.json").write_text(json.dumps({"geom_fp": sorted(fp[d]), "n_sources": dict(n), "root_dirs": len(dirs)}))
    print(json.dumps({d: len(fp[d]) for d in fp} | {"sources": dict(n), "root_dirs": len(dirs)}))


if __name__ == "__main__":
    main(sys.argv[1])
