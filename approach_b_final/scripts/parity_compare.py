"""V3.2 cross-host teacher parity: each host's uncached verification of the predeclared sample vs the reference labels (V3.1 gvlab cache).
Compares decided X, Y and (3D) resolution; any mismatch = host quarantined.  usage: parity_compare.py REF_JSON_2D REF_JSON_3D OUTDIR_WITH_<host>_<d>.jsonl"""
import json, sys, glob, os
ref = {d: json.load(open(sys.argv[i])) for d, i in (("2d", 1), ("3d", 2))}
res = {}
for p in sorted(glob.glob(os.path.join(sys.argv[3], "*_?d.jsonl"))):
    host, d = os.path.basename(p)[:-6].rsplit("_", 1)
    got = {}
    for l in open(p):
        v = json.loads(l)
        for x in v["results"]:
            xr, yr = x["x"] or {}, x["y"] or {}
            got[f"{v['root']}|{json.dumps(x['seq'])}"] = [xr.get("x"), yr.get("y"), [xr.get("resolution", "EVALUATED"), yr.get("resolution", "EVALUATED")]]
    cmp = [(k, ref[d][k], got[k]) for k in ref[d] if k in got]
    bad = [c for c in cmp if c[1] != c[2]]
    res[f"{host}_{d}"] = {"reference": len(ref[d]), "compared": len(cmp), "identical": len(cmp) - len(bad), "mismatch": bad[:5],
                          "status": "PASS" if not bad and len(cmp) == len(ref[d]) else ("FAIL" if bad else "INCOMPLETE")}
print(json.dumps(res, indent=1))
