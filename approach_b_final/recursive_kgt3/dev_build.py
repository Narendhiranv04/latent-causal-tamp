#!/usr/bin/env python3
"""DEV set construction (evaluator-side; run once, never imported by the planner).  DEV = engineering scenes of the scaling campaign only
(AUDIT A5): the 16 engineering K4-K6 certified layouts (G0 recheck), the 8 certified engineering K9 layouts (G3 k9eng runs) and the engineering
25-object K12 layout ENG12_17ff1743fd83.  None is in release_v2 (novelty filter).  Writes two strictly separated files:
  dev_public/dev_public.jsonl    {root_id, domain, inputs}  -- contracts.view2d of the raw record (the ONLY file the planner may read)
  dev_private/dev_private.jsonl  {root_id, K, n_objects, pair, witness, y0_status, src}  -- evaluator only, after sealing
  dev_private/dev_records/<root_id>.json  raw teacher records (verification)
Run with the teacher env (mink.boot) from the scaling2d_k12 code dir:
    ABF_ROOT=... python dev_build.py SCALING_CODE_DIR SCRATCH_DEV_DIR LAYOUT_SPECS.json"""
import json, sys
from pathlib import Path


def main(code_dir, out_dir, spec_f):
    sys.path.insert(0, str(code_dir))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import mink as MK, witness as W
    out = Path(out_dir); (out / "dev_public").mkdir(parents=True, exist_ok=True); (out / "dev_private/dev_records").mkdir(parents=True, exist_ok=True)
    spec = json.loads(Path(spec_f).read_text())
    pub, priv = [], []
    for grp in spec:
        L = {json.loads(l)["root_id"]: json.loads(l) for f in grp["layouts"] for l in open(f)}
        for f in grp["witness"]:
            for l in open(f):
                w = json.loads(l)
                if w.get("verdict") != "CERTIFIED_MIN_K" or w["root_id"] not in L or any(p["root_id"] == w["root_id"] for p in priv):
                    continue
                lay = L[w["root_id"]]
                MK.boot(lay.get("geom", "original"))
                import contracts as CT
                rec, ids = W.rec_of(lay, lay.get("geom", "original"))
                fin = next((t for t in w["tries"] if t.get("final")), None) or \
                    next((t for t in reversed(w["tries"]) if t.get("x") == 1 and t.get("y") == 1), None) or \
                    max((t for t in w["tries"] if t.get("x") == 1), key=lambda t: len(t["seq"]))
                (out / "dev_private/dev_records" / f"{w['root_id']}.json").write_text(json.dumps(rec))
                pub.append({"root_id": w["root_id"], "domain": "2d", "inputs": CT.view2d(rec)})
                priv.append({"root_id": w["root_id"], "K": w["K_lb"], "n_objects": len(lay["cells0"]), "pair": [lay["cells0"][0], lay["goal_cell"]],
                             "witness": fin["seq"], "y0_status": (w.get("Y0") or {}).get("teacher_status"), "src": grp["name"], "layout": lay})
    pub.sort(key=lambda r: r["root_id"]); priv.sort(key=lambda r: r["root_id"])
    (out / "dev_public/dev_public.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in pub))
    (out / "dev_private/dev_private.jsonl").write_text("".join(json.dumps(r) + "\n" for r in priv))
    import collections
    print(json.dumps({"n": len(pub), "by_K": dict(collections.Counter(p["K"] for p in priv)), "objects": sorted(p["n_objects"] for p in priv)}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
