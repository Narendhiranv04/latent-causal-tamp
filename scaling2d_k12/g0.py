#!/usr/bin/env python3
"""G0 forensic locks for the 2D K=4..12 scaling TEST dataset (read-only).
    python g0.py OUT_DIR   -> SOURCE_LOCK.json, TEACHER_LOCK.json, ENV_AUDIT.json, HIST_EXCLUSIONS.json
HIST_EXCLUSIONS holds fingerprints only (historical GEOM_V1 set of every 2D/3D snapshot + historical root file, plus the V3.4 independent
cohort's 2D layout / cell fingerprints).  No outcome label of any historical or cohort root is read."""
import hashlib, json, os, platform, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ABF = Path(os.environ.get("ABF_ROOT", str(Path.home() / "abf_v3_laptop/root")))
CODE2D = ABF / "mirror/rss-placement-ready-v2/gh-yadu-iiith/planar_2d/dataset_bd_classquota/code"
V34 = Path.home() / "abf_v34"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree(d, pat="*.py"):
    return {str(p.relative_to(d)): sha(p) for p in sorted(Path(d).rglob(pat)) if "__pycache__" not in p.parts}


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    git = lambda *a: subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    src = {"repo": {"branch": git("rev-parse", "--abbrev-ref", "HEAD"), "commit": git("rev-parse", "HEAD"), "dirty": git("status", "--porcelain", "approach_b_final")},
           "approach_b_final": {f: sha(REPO / "approach_b_final" / f) for f in ("contracts.py", "placement.py", "search.py", "construct.py", "xy.py",
                                "teacher2d.py", "benchmark.py", "evaluate.py", "exhaustive.py", "scripts/v34_geomfp.py", "scripts/v34_gen.py",
                                "scripts/v34_enrich.py", "scripts/v34_cohort.py", "config/final_protocol.yaml")},
           "frozen_2d_bundle": {f: sha(V34 / "approach_b_bundle/2d" / f) for f in ("sampler.pt", "scorer_s0.pt", "scorer_s1.pt", "scorer_s2.pt", "scalers.json")}}
    teach = {"bxy_teacher.py": sha(ABF / "teacher2d_wt/bxy_teacher.py"), "teacher2d_wt": tree(ABF / "teacher2d_wt"),
             "planar_2d_code": tree(CODE2D), "abf_root": str(ABF),
             "versions": {"X": "BXY_X_TEACHER_V1", "Y": "BXY_Y_TEACHER_V1", "note": "frozen; any K>3 / retarget wrapper is separately versioned"}}
    env = {"host": platform.node(), "python": sys.version.split()[0], "cpus": os.cpu_count(),
           "env2d_python": subprocess.run([str(Path.home() / "abf_v3_laptop/env2d/bin/python"), "-c", "import sys;print(sys.version.split()[0])"],
                                          capture_output=True, text=True).stdout.strip()}
    E = json.loads((V34 / "excl/EXCL2D_GEOM.json").read_text())
    coh = [json.loads(l) for l in open(V34 / "final/PRIVATE_INDEX.jsonl")]
    excl = {"historical_geom_fp": sorted(E["geom_fp"]), "historical_sources": E["n_sources"],
            "v34_cohort_2d_layout_fp": sorted({r["layout_fp"] for r in coh if r["domain"] == "2d"}),
            "v34_cohort_2d_cell_fp": sorted({r["cell_fp"] for r in coh if r["domain"] == "2d"}),
            "fingerprint": "scripts/v34_geomfp.geom_fp (GEOM_V1); cell_fp = cells + target + goal", "labels_read": False}
    for n, obj in (("SOURCE_LOCK.json", src), ("TEACHER_LOCK.json", teach), ("ENV_AUDIT.json", env), ("HIST_EXCLUSIONS.json", excl)):
        (out / n).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"commit": src["repo"]["commit"][:10], "teacher": teach["bxy_teacher.py"][:12], "planar_files": len(teach["planar_2d_code"]),
                      "excl_hist": len(excl["historical_geom_fp"]), "excl_v34_2d": len(excl["v34_cohort_2d_layout_fp"])}))


if __name__ == "__main__":
    main(sys.argv[1])
