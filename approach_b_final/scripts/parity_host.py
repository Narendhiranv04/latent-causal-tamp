"""Teacher parity of a new host vs recorded results: re-run the first N (root, sequence) entries of a verify cache with the unchanged teachers."""
import json, os, sys, multiprocessing as mp
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import evaluate as EV, construct as CO
def main():
    dom, cache, n, W = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    EV.SNAP = CO.ABF / "snapshot/abf_9de85710c2a7103f"
    rows = {r["root_id"]: r for r in EV.rows_of(dom, "val")}
    ref = sorted((v for v in map(json.loads, open(cache)) if v["root"] in rows), key=lambda v: v.get("cpu_s", 1e9))[:n]   # cheapest recorded roots (determinism check)
    jobs = []
    for v in ref:
        ids, path = rows[v["root"]]["inputs"]["ids"], EV.path_of(dom, rows[v["root"]])
        geom = "fastgeom1" if dom == "2D" and json.loads(Path(path).read_text()).get("geometry_impl") == "fastgeom1" else "original"
        jobs.append({"dom": dom, "path": str(path), "geom": geom, "seqs": [[(ids[i], c) for i, c in x["seq"]] for x in v["results"]], "ref": v})
    os.environ["FIN3D_STORE"] = str(CO.V3OUT / "parity_store_3d")
    agree = tot = 0
    bad = []
    for geom in sorted({j["geom"] for j in jobs}):
        js = [j for j in jobs if j["geom"] == geom]
        with mp.get_context("spawn").Pool(W, initializer=CO._boot, initargs=(dom, geom)) as pool:
            for j, r in zip(js, pool.map(EV._verify_job, js)):
                for a, b in zip(r["results"], j["ref"]["results"]):
                    for k, f in (("x", "x"), ("y", "y")):
                        tot += 1
                        same = (a[k] or {}).get(f) == (b[k] or {}).get(f)
                        agree += same
                        if not same:
                            bad.append((j["ref"]["root"], k, (a[k] or {}).get(f), (b[k] or {}).get(f)))
    print(json.dumps({"dom": dom, "roots": len(jobs), "labels": tot, "agree": agree, "disagree": bad[:10]}))


if __name__ == "__main__":
    main()
